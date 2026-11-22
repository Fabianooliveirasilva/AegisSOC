"""Cursor pagination (SPRINT_01 S1-T03, audit finding B-2).

A cursor is opaque to clients: ``base64url(JSON {"v": 1, "k": <last sort key>, "id": <uuid>})``
without padding. It is **not signed and uses no secret**: its values are only ever bound as
SQL parameters under the caller's own permissions, so a forged cursor gains nothing.

Because it is client input, decoding is strict. Anything that is not exactly what
``encode_cursor`` produces is rejected with a 400 ``bad-request`` ("Invalid cursor", never
echoing the cursor): wrong length or alphabet, non-canonical base64, invalid UTF-8,
duplicate or extra keys, wrong version, a UUID that is not canonical lowercase, and a sort
key whose type differs from the active sort field. Only the exact byte form that
``encode_cursor`` emits is accepted (no reordered keys, whitespace or ``\\u`` escapes), and
text keys containing NUL or lone surrogates are refused because the database driver would
reject them later as a 500.
"""

import base64
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from aegissoc.core.errors import BadRequest

MAX_CURSOR_LENGTH = 512
CURSOR_VERSION = 1

CursorKeyType = Literal["str", "int", "datetime"]
CursorKey = str | int | datetime

_ALPHABET = re.compile(r"[A-Za-z0-9_-]+")
_KEY_TYPES = ("str", "int", "datetime")
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1
_EXPECTED_FIELDS = {"v", "k", "id"}


@dataclass(frozen=True)
class Cursor:
    key: CursorKey
    id: uuid.UUID


class Page[T](BaseModel):
    """List response: ``{"items": [...], "next_cursor": "..." | null}``."""

    model_config = ConfigDict(extra="forbid")

    items: list[T]
    next_cursor: str | None = None


def _check_text_key(key: str) -> None:
    """A text key becomes a bound query parameter: NUL and lone surrogates would fail there."""
    if "\x00" in key:
        raise ValueError("cursor key must not contain NUL")
    try:
        key.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("cursor key is not valid Unicode") from None


def _key_to_json(key: CursorKey) -> str | int:
    if isinstance(key, bool) or not isinstance(key, str | int | datetime):
        raise ValueError("unsupported cursor key type")
    if isinstance(key, str):
        _check_text_key(key)
    if isinstance(key, datetime):
        if key.tzinfo is None:
            raise ValueError("cursor datetime key needs a timezone")
        return key.astimezone(UTC).isoformat()
    if isinstance(key, int) and not _INT64_MIN <= key <= _INT64_MAX:
        raise ValueError("cursor integer key does not fit in 64-bit")
    return key


def encode_cursor(key: CursorKey, id_: uuid.UUID) -> str:
    """Encode the last row's sort key and id. Refuses anything ``decode_cursor`` would reject."""
    raw = _canonical_json(_key_to_json(key), str(id_))
    token = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if len(token) > MAX_CURSOR_LENGTH:
        raise ValueError("cursor too long")
    return token


def _canonical_json(key: str | int, id_: str) -> bytes:
    """The one byte form of a cursor payload; the decoder accepts nothing else."""
    payload = {"v": CURSOR_VERSION, "k": key, "id": id_}
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def _decode_key(value: Any, key_type: CursorKeyType) -> CursorKey:
    if key_type == "str":
        if type(value) is not str:
            raise ValueError("key is not a string")
        return value
    if key_type == "int":
        if type(value) is not int or not _INT64_MIN <= value <= _INT64_MAX:
            raise ValueError("key is not a 64-bit integer")
        return value
    if type(value) is not str:
        raise ValueError("key is not a datetime string")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0) or parsed.isoformat() != value:
        raise ValueError("key is not a canonical UTC datetime")
    return parsed


def _decode(token: str, key_type: CursorKeyType) -> Cursor:
    if len(token) > MAX_CURSOR_LENGTH or _ALPHABET.fullmatch(token) is None:
        raise ValueError("bad length or alphabet")
    raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != token:
        raise ValueError("non-canonical base64")
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_no_duplicate_keys,
    )
    if not isinstance(payload, dict) or set(payload) != _EXPECTED_FIELDS:
        raise ValueError("unexpected structure")
    if type(payload["v"]) is not int or payload["v"] != CURSOR_VERSION:
        raise ValueError("unsupported version")
    raw_id = payload["id"]
    if type(raw_id) is not str:
        raise ValueError("id is not a string")
    parsed_id = uuid.UUID(raw_id)
    if str(parsed_id) != raw_id:
        raise ValueError("id is not a canonical UUID")
    key = _decode_key(payload["k"], key_type)
    if isinstance(key, str):
        _check_text_key(key)
    # Exactly the bytes the encoder would produce: no reordering, whitespace or \u escapes.
    if _canonical_json(payload["k"], raw_id) != raw:
        raise ValueError("not in canonical form")
    return Cursor(key=key, id=parsed_id)


def decode_cursor(token: str, key_type: CursorKeyType) -> Cursor:
    """Decode and strictly validate a client-supplied cursor, or raise ``BadRequest``."""
    if key_type not in _KEY_TYPES:
        raise ValueError(f"unknown key_type: {key_type!r}")
    try:
        return _decode(token, key_type)
    except (ValueError, TypeError):
        raise BadRequest("Invalid cursor") from None
