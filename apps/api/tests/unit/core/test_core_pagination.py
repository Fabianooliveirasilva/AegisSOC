"""core.pagination: opaque, unsigned, strictly validated cursors (B-2, AC-PLAT-10)."""

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from aegissoc.core.errors import BadRequest
from aegissoc.core.pagination import (
    MAX_CURSOR_LENGTH,
    Cursor,
    Page,
    decode_cursor,
    encode_cursor,
)

ID = uuid.UUID("0190b4f2-7c9e-7a11-8d3e-aabbccddeeff")
INT64_MAX = 2**63 - 1


def _token(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _decode_b64(token: str) -> bytes:
    return base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))


def _forge(payload: Any) -> str:
    return _token(json.dumps(payload, separators=(",", ":")).encode())


def _valid(**overrides: Any) -> dict[str, Any]:
    return {"v": 1, "k": "alpha", "id": str(ID)} | overrides


def _rejected(token: str, key_type: Any = "str") -> BadRequest:
    with pytest.raises(BadRequest) as exc:
        decode_cursor(token, key_type)
    return exc.value


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    ("key", "key_type"),
    [
        ("alpha", "str"),
        ("", "str"),
        ('ünï-çødé ✓ \n quote"', "str"),
        (0, "int"),
        (-5, "int"),
        (INT64_MAX, "int"),
        (-(2**63), "int"),
        (datetime(2026, 11, 21, 12, 30, 45, 123456, tzinfo=UTC), "datetime"),
    ],
)
def test_cursor_round_trips(key: Any, key_type: Any) -> None:
    decoded = decode_cursor(encode_cursor(key, ID), key_type)
    assert decoded == Cursor(key=key, id=ID)


@pytest.mark.req("AC-PLAT-10")
def test_datetime_keys_are_normalised_to_utc() -> None:
    local = datetime(2026, 1, 1, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    decoded = decode_cursor(encode_cursor(local, ID), "datetime")
    assert decoded.key == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.req("AC-PLAT-10")
def test_encoded_cursor_is_unpadded_base64url_json_with_exact_shape() -> None:
    token = encode_cursor("alpha", ID)
    assert token.isascii()
    assert "=" not in token
    assert "+" not in token
    assert "/" not in token
    raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    assert json.loads(raw) == {"v": 1, "k": "alpha", "id": str(ID)}


@pytest.mark.req("AC-PLAT-10")
def test_cursor_is_not_signed_no_secret_involved() -> None:
    assert encode_cursor("alpha", ID) == encode_cursor("alpha", ID)


@pytest.mark.req("AC-PLAT-10")
def test_encode_refuses_what_it_could_not_decode_later() -> None:
    with pytest.raises(ValueError, match="too long"):
        encode_cursor("x" * 600, ID)
    with pytest.raises(ValueError, match="timezone"):
        encode_cursor(datetime(2026, 1, 1), ID)
    with pytest.raises(ValueError, match="64-bit"):
        encode_cursor(INT64_MAX + 1, ID)
    with pytest.raises(ValueError, match="key"):
        encode_cursor(True, ID)  # a bool is not an int sort key
    with pytest.raises(ValueError, match="key"):
        encode_cursor(1.5, ID)  # type: ignore[arg-type]


@pytest.mark.req("AC-PLAT-10")
def test_length_limit_is_512() -> None:
    assert MAX_CURSOR_LENGTH == 512
    # 512 base64 characters hold exactly 384 bytes of JSON.
    overhead = len(json.dumps(_valid(k=""), separators=(",", ":")))
    at_limit = _forge(_valid(k="x" * (384 - overhead)))
    assert len(at_limit) == MAX_CURSOR_LENGTH
    decode_cursor(at_limit, "str")  # valid at exactly the limit
    too_long = _forge(_valid(k="x" * (384 - overhead + 3)))
    assert len(too_long) > MAX_CURSOR_LENGTH
    _rejected(too_long)  # structurally valid, rejected for length alone


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "token",
    [
        "",
        "!!!!",
        "abc+def",
        "abc/def",
        "abcd=",
        "ab cd",
        "abcd\n",
        "abcd\r\n",
        "ünï",
        "a",  # impossible base64 length
        "not-json-but-base64url",
    ],
)
def test_malformed_tokens_are_rejected(token: str) -> None:
    error = _rejected(token)
    assert error.status_code == 400
    assert error.slug == "bad-request"
    assert error.detail == "Invalid cursor"


_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize("padding", range(0, 6))
def test_non_canonical_base64_is_rejected(padding: int) -> None:
    """Same bytes, different last character (non-zero unused bits): not what we emit."""
    token = _forge(_valid(k="a" * padding))
    assert len(token) % 4 in (0, 2, 3)
    decode_cursor(token, "str")  # the canonical form is fine
    if len(token) % 4 == 0:
        return  # no unused bits to flip for this length
    variants = [token[:-1] + c for c in _ALPHABET if c != token[-1]]
    same_bytes = _decode_b64(token)
    decodable = [v for v in variants if _decode_b64(v) == same_bytes]
    assert decodable, "test setup: expected a same-bytes variant"
    for variant in decodable:
        _rejected(variant)


@pytest.mark.req("AC-PLAT-10")
def test_non_canonical_variants_were_actually_exercised() -> None:
    exercised = 0
    for padding in range(0, 6):
        if len(_forge(_valid(k="a" * padding))) % 4 != 0:
            exercised += 1
    assert exercised >= 2


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "payload",
    [
        [],
        [1, "k", str(ID)],
        1,
        "string",
        None,
        True,
        {},
        {"v": 1, "k": "alpha"},
        {"v": 1, "id": str(ID)},
        {"k": "alpha", "id": str(ID)},
        _valid() | {"extra": 1},
        _valid() | {"V": 1},
        {"v": 2, "k": "alpha", "id": str(ID)},
        {"v": 0, "k": "alpha", "id": str(ID)},
        {"v": "1", "k": "alpha", "id": str(ID)},
        {"v": True, "k": "alpha", "id": str(ID)},
        {"v": 1.0, "k": "alpha", "id": str(ID)},
        {"v": None, "k": "alpha", "id": str(ID)},
    ],
)
def test_wrong_structure_or_version_is_rejected(payload: Any) -> None:
    _rejected(_forge(payload))


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "bad_id",
    [
        None,
        1,
        "",
        "not-a-uuid",
        str(ID).upper(),
        "{" + str(ID) + "}",
        str(ID).replace("-", ""),
        "urn:uuid:" + str(ID),
        str(ID) + " ",
        str(ID)[:-1],
        [str(ID)],
    ],
)
def test_ids_must_be_canonical_lowercase_uuids(bad_id: Any) -> None:
    _rejected(_forge(_valid(id=bad_id)))


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    ("key", "key_type"),
    [
        (1, "str"),
        (None, "str"),
        (["a"], "str"),
        ({"a": 1}, "str"),
        ("1", "int"),
        (True, "int"),
        (False, "int"),
        (1.5, "int"),
        (None, "int"),
        (INT64_MAX + 1, "int"),
        (-(2**63) - 1, "int"),
        (10**30, "int"),
        (1, "datetime"),
        ("2026-01-01T00:00:00", "datetime"),  # naive
        ("2026-01-01", "datetime"),
        ("not a date", "datetime"),
        ("2026-01-01T00:00:00Z", "datetime"),  # valid ISO but not the form we emit
        ("2026-01-01T03:00:00+03:00", "datetime"),  # not UTC
        (None, "datetime"),
    ],
)
def test_sort_key_must_match_the_active_sort_field_type(key: Any, key_type: str) -> None:
    _rejected(_forge(_valid(k=key)), key_type)


@pytest.mark.req("AC-PLAT-10")
def test_unknown_key_type_is_a_programming_error_not_a_400() -> None:
    with pytest.raises(ValueError, match="key_type"):
        decode_cursor(encode_cursor("alpha", ID), "float")  # type: ignore[arg-type]


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "raw",
    [
        b'{"v":1,"v":1,"k":"alpha","id":"' + str(ID).encode() + b'"}',  # duplicate key
        b'{"v":1,"k":NaN,"id":"' + str(ID).encode() + b'"}',
        b'{"v":1,"k":Infinity,"id":"' + str(ID).encode() + b'"}',
        b'{"v":1,"k":"alpha","id":"' + str(ID).encode() + b'"} trailing',
        b'{"v":1,"k":"\xff","id":"' + str(ID).encode() + b'"}',  # invalid UTF-8
        b"\xef\xbb\xbf" + b'{"v":1,"k":"a","id":"' + str(ID).encode() + b'"}',  # BOM
        b"[" * 300 + b"]" * 300,
        b'{"v":1,"k":' + b"[" * 200 + b"]" * 200 + b',"id":"x"}',
    ],
)
def test_hostile_json_is_rejected(raw: bytes) -> None:
    _rejected(_token(raw))


@pytest.mark.req("AC-PLAT-10")
def test_error_never_echoes_the_submitted_cursor() -> None:
    token = _forge({"v": 9, "k": "secret-ish-value", "id": "x"})
    error = _rejected(token)
    assert token not in str(error)
    assert "secret-ish-value" not in error.detail


@pytest.mark.req("AC-PLAT-10")
def test_page_is_a_generic_response_model() -> None:
    page = Page[int](items=[1, 2, 3], next_cursor=encode_cursor(3, ID))
    assert page.model_dump()["items"] == [1, 2, 3]
    assert Page[str](items=[]).next_cursor is None
    with pytest.raises(ValueError, match="valid integer"):
        Page[int](items=["not-an-int"])
    with pytest.raises(ValueError, match="extra"):
        Page[int](items=[], next_cursor=None, total=5)  # type: ignore[call-arg]


def _raw_token(text: str) -> str:
    return _token(text.encode("utf-8"))


_UUID = str(ID)


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "raw_json",
    [
        '{"id":"' + _UUID + '","k":"alpha","v":1}',  # reordered keys
        '{"k":"alpha","v":1,"id":"' + _UUID + '"}',
        '{"v": 1, "k": "alpha", "id": "' + _UUID + '"}',  # extra whitespace
        '{"v":1,"k":"alpha","id":"' + _UUID + '"} ',
        ' {"v":1,"k":"alpha","id":"' + _UUID + '"}',
        '{"v":1,"k":"\\u0061lpha","id":"' + _UUID + '"}',  # \u escape of a plain letter
        '{"v":1,"k":"alp\\u0068a","id":"' + _UUID + '"}',
        '{"v":1.0,"k":"alpha","id":"' + _UUID + '"}',
        '{"v":1e0,"k":"alpha","id":"' + _UUID + '"}',
    ],
)
def test_only_the_exact_form_the_encoder_emits_is_accepted(raw_json: str) -> None:
    _rejected(_raw_token(raw_json))


@pytest.mark.req("AC-PLAT-10")
def test_the_exact_encoder_form_is_accepted() -> None:
    raw = '{"v":1,"k":"alpha","id":"' + _UUID + '"}'
    assert decode_cursor(_raw_token(raw), "str") == Cursor(key="alpha", id=ID)


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "key_json",
    ['"\\u0000"', '"a\\u0000b"', '"\\ud800"', '"\\udfff"', '"ok\\ud83d"'],
)
def test_keys_that_would_break_the_database_driver_are_rejected(key_json: str) -> None:
    raw = '{"v":1,"k":' + key_json + ',"id":"' + _UUID + '"}'
    _rejected(_raw_token(raw))


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize("key", ["\x00", "a\x00b", "\ud800", "ok\udfff"])
def test_encoder_refuses_the_same_keys(key: str) -> None:
    with pytest.raises(ValueError, match="key"):
        encode_cursor(key, ID)


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "key",
    ["tab\there", "line\nbreak", 'quote"d', "back\\slash", "emoji 😀", "日本語", "\x7f", "\x01"],
)
def test_other_unusual_but_storable_keys_still_round_trip(key: str) -> None:
    assert decode_cursor(encode_cursor(key, ID), "str").key == key
