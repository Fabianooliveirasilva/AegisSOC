"""Cursor round-trip and hostile corpus (audit B-2, S1-T03). QA-written."""

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from aegissoc.core.errors import BadRequest
from aegissoc.core.pagination import (
    MAX_CURSOR_LENGTH,
    Cursor,
    Page,
    decode_cursor,
    encode_cursor,
)

UID = "0190a2b4-7c3e-7a11-8b2d-5e6f7a8b9c0d"
SMALL_ID = uuid.UUID(UID)


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def tok(obj: object | None = None, raw: bytes | str | None = None) -> str:
    if raw is None:
        raw = json.dumps(obj, separators=(",", ":")).encode()
    if isinstance(raw, str):
        raw = raw.encode()
    return b64(raw)


def good(k: object = "abc", v: object = 1, id_: object = UID) -> str:
    return tok({"v": v, "k": k, "id": id_})


def rejected(token: str, kt: str = "str") -> None:
    with pytest.raises(BadRequest) as ei:
        decode_cursor(token, kt)  # type: ignore[arg-type]
    assert ei.value.status_code == 400 and ei.value.slug == "bad-request"
    assert len(token) < 8 or token not in str(ei.value.detail)


# ---- round trips ---------------------------------------------------------------
@pytest.mark.parametrize(
    ("kt", "key"),
    [
        ("str", "abc"),
        ("str", ""),
        ("str", 'ünï cødé\n"\\'),
        ("str", "😀" * 10),
        ("int", 0),
        ("int", -1),
        ("int", 2**63 - 1),
        ("int", -(2**63)),
        ("datetime", datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC)),
        ("datetime", datetime(2026, 1, 2, tzinfo=UTC)),
    ],
)
def test_round_trip(kt: str, key: object) -> None:
    t = encode_cursor(key, SMALL_ID)  # type: ignore[arg-type]
    assert len(t) <= MAX_CURSOR_LENGTH and "=" not in t
    c = decode_cursor(t, kt)  # type: ignore[arg-type]
    assert c == Cursor(key=key, id=SMALL_ID)  # type: ignore[arg-type]
    assert type(c.key) is type(key)


def test_round_trip_non_utc_datetime_normalised_to_utc() -> None:
    k = datetime(2026, 1, 2, 5, 0, tzinfo=timezone(timedelta(hours=2)))
    c = decode_cursor(encode_cursor(k, SMALL_ID), "datetime")
    assert c.key == k and c.key.utcoffset() == timedelta(0)  # type: ignore[union-attr]


def test_uuid_v4_and_v7_ids_roundtrip() -> None:
    for u in (uuid.uuid4(), SMALL_ID, uuid.UUID(int=0), uuid.UUID(int=2**128 - 1)):
        assert decode_cursor(encode_cursor("k", u), "str").id == u


@pytest.mark.parametrize(
    "key",
    [
        True,
        1.5,
        None,
        b"x",
        [1],
        {"a": 1},
        2**63,
        -(2**63) - 1,
        datetime(2026, 1, 1),
        "x" * 600,
    ],
)
def test_encode_refuses_what_decode_would_reject(key: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        encode_cursor(key, SMALL_ID)  # type: ignore[arg-type]


def test_page_model() -> None:
    p = Page[int](items=[1, 2])
    assert p.model_dump() == {"items": [1, 2], "next_cursor": None}
    assert Page[int](items=[], next_cursor="x").next_cursor == "x"
    with pytest.raises(ValueError):
        Page[int](items=["a"])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        Page[int](items=[1], extra=1)  # type: ignore[call-arg]


# ---- hostile corpus ----------------------------------------------------------------
LENGTH_ALPHABET = [
    "",
    " ",
    "A" * 513,
    "A" * 600,
    "A" * 100_000,
    "a=",
    "abc=",
    good() + "=",
    good() + "==",
    "ab cd",
    "abc\n",
    good() + "\n",
    "\n" + good(),
    good() + "\r\n",
    good()[:10] + "\x00" + good()[10:],
    "ab+/",
    good().replace("-", "+") + "+",
    "é" * 8,
    "ＡＢＣＤ",
    good() + " ",
    " " + good(),
    "٣" * 8,
    good() + "\u200b",
    "a" * 1,
    "a" * 5,
    "a" * 9,
    "%41%41",
    "====",
]


@pytest.mark.parametrize("t", LENGTH_ALPHABET, ids=lambda t: repr(t)[:30])
def test_length_alphabet(t: str) -> None:
    rejected(t)


def test_boundary_512_and_513() -> None:
    def token_with_len(n: int) -> str:  # smallest token with length >= n
        # grow a JSON padding-free payload until the base64url length is exactly n
        for k in range(600):
            raw = json.dumps(
                {"v": 1, "k": "k" * k, "id": UID}, separators=(",", ":")
            ).encode()
            if len(b64(raw)) >= n:
                return b64(raw)
        raise AssertionError(n)

    t512 = token_with_len(512)
    assert len(t512) == 512
    assert decode_cursor(t512, "str").key.startswith("k")  # type: ignore[union-attr]
    t513 = token_with_len(513)
    assert len(t513) in (514, 515)
    rejected(t513)
    rejected("A" * 513)


def test_non_canonical_base64() -> None:
    t = good("k")
    n = len(t) % 4
    # flip padding bits in the last char: decodes to the same bytes but is not what encode makes
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    last = alphabet.index(t[-1])
    if n in (2, 3):
        mask = 0b1111 if n == 2 else 0b11
        alt = (
            alphabet[last ^ 1]
            if (last & mask) == (last ^ 1) & mask
            else alphabet[(last & ~mask) | ((last ^ 1) & mask)]
        )
        mutated = t[:-1] + alt
        assert base64.urlsafe_b64decode(
            mutated + "=" * (-len(mutated) % 4)
        ) == base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))
        rejected(mutated)
    else:
        pytest.skip("token length multiple of 4: choose another key")


def test_non_canonical_base64_all_key_lengths() -> None:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    seen = set()
    for n in range(1, 30):
        t = good("k" * n)
        r = len(t) % 4
        if r == 0 or r in seen:
            continue
        seen.add(r)
        mask = 0b1111 if r == 2 else 0b11
        i = alphabet.index(t[-1])
        j = i ^ 1 if (i & mask) == 0 else i & ~mask  # set a padding bit
        if (i & mask) == 0:
            j = i | 1
        mutated = t[:-1] + alphabet[j]
        assert mutated != t
        rejected(mutated)
    assert seen == {2, 3}


def test_standard_base64_alphabet_rejected() -> None:
    raw = json.dumps(
        {"v": 1, "k": "\xff\xfe??>>", "id": UID}, ensure_ascii=False
    ).encode()
    std = base64.b64encode(raw).rstrip(b"=").decode()
    if "+" in std or "/" in std:
        rejected(std)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{",
        b"null",
        b"[]",
        b"1",
        b'"s"',
        b"true",
        b"{}",
        b"\xef\xbb\xbf" + json.dumps({"v": 1, "k": "a", "id": UID}).encode(),
        b"\xff\xfe\xfd",
        b"\xc3\x28",
        b'{"v":1,"k":"\xff","id":"' + UID.encode() + b'"}',
        b"\x00",
        json.dumps({"v": 1, "k": "a", "id": UID}).encode().decode().encode("utf-16"),
        b'{"v":1,"k":"a","id":"' + UID.encode() + b'"}garbage',
        b'{"v":1,"k":"a","id":"' + UID.encode() + b'"} {}',
        b'{"v":1,"v":1,"k":"a","id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":"a","k":"b","id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":"a","id":"' + UID.encode() + b'","id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":NaN,"id":"' + UID.encode() + b'"}',
        b'{"v":NaN,"k":"a","id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":Infinity,"id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":-Infinity,"id":"' + UID.encode() + b'"}',
        b'{"v":1,"k":"a","id":"' + UID.encode() + b'",}',
        b"{'v':1}",
    ],
)
def test_malformed_payloads(raw: bytes) -> None:
    for kt in ("str", "int", "datetime"):
        rejected(b64(raw), kt)


def test_deep_nesting_and_huge_ints_and_floats() -> None:
    for depth in (100, 1000, 100_000):
        deep = "[" * depth + "]" * depth
        rejected(tok(raw=('{"v":1,"k":' + deep + ',"id":"' + UID + '"}')))
        rejected(tok(raw=('{"v":1,"k":"a","id":"' + UID + '","x":' + deep + "}")))
        rejected(tok(raw=("[" * depth)))
    for n in (2**63, -(2**63) - 1, 10**20, 10**400, 10**5000):
        if abs(n) < 10**400:
            rejected(good(k=n), "int")
        digits = "1" + "0" * 5000 if n == 10**5000 else str(n)
        rejected(tok(raw='{"v":1,"k":' + digits + ',"id":"' + UID + '"}'), "int")
    rejected(tok(raw='{"v":1,"k":1e2,"id":"' + UID + '"}'), "int")
    rejected(tok(raw='{"v":1,"k":1.0,"id":"' + UID + '"}'), "int")
    rejected(tok(raw='{"v":1,"k":1E400,"id":"' + UID + '"}'), "int")
    rejected(tok(raw='{"v":1,"k":-0.0,"id":"' + UID + '"}'), "int")


@pytest.mark.parametrize(
    ("k", "kt"),
    [
        (1, "str"),
        (True, "int"),
        (False, "int"),
        (None, "str"),
        (None, "int"),
        (None, "datetime"),
        ([], "str"),
        ({}, "str"),
        ("1", "int"),
        ("x", "int"),
        (1.5, "int"),
        (1.0, "int"),
        (["a"], "int"),
        (1, "datetime"),
        ("not-a-date", "datetime"),
        ("2026-01-01T00:00:00Z", "datetime"),
        ("2026-01-01T00:00:00", "datetime"),
        ("2026-01-01", "datetime"),
        ("2026-01-01T00:00:00+02:00", "datetime"),
        ("2026-01-01 00:00:00+00:00", "datetime"),
        ("2026-01-01T00:00:00.000000+00:00", "datetime"),
        ("20260101T000000+0000", "datetime"),
        ("2026-W01-1T00:00:00+00:00", "datetime"),
        ("0000-01-01T00:00:00+00:00", "datetime"),
        ("2026-13-01T00:00:00+00:00", "datetime"),
        ("2026-01-01T24:00:00+00:00", "datetime"),
        ("2026-01-01T00:00:00+00:00\n", "datetime"),
        (" 2026-01-01T00:00:00+00:00", "datetime"),
        ("2026-01-01t00:00:00+00:00", "datetime"),
        ("٢٠٢٦-01-01T00:00:00+00:00", "datetime"),
        ("", "datetime"),
        (10**30, "datetime"),
    ],
)
def test_wrong_key_type(k: object, kt: str) -> None:
    rejected(good(k=k), kt)


def test_cross_type_matrix() -> None:
    """A token valid for one active sort field is rejected for the others."""
    samples = {"str": "abc", "int": 5, "datetime": "2026-01-01T00:00:00+00:00"}
    for have, val in samples.items():
        for want in samples:
            if have == want:
                decode_cursor(good(k=val), want)  # type: ignore[arg-type]
            elif not (
                have == "datetime" and want == "str"
            ):  # a datetime string is a legal str
                rejected(good(k=val), want)


@pytest.mark.parametrize(
    "v",
    [0, 2, -1, 1.0, True, "1", None, [1], {"a": 1}, 2**64, 10**30, "v1", 1.5, False],
)
def test_bad_version(v: object) -> None:
    rejected(good(v=v))


@pytest.mark.parametrize(
    "i",
    [
        None,
        1,
        True,
        [],
        {},
        "",
        "not-a-uuid",
        UID.upper(),
        UID.replace("-", ""),
        "{" + UID + "}",
        "urn:uuid:" + UID,
        UID + "\n",
        " " + UID,
        UID[:-1],
        UID + "0",
        "0190a2b4-7c3e-7a11-8b2d-5e6f7a8b9c0g",
        "٠" * 36,
        "0190a2b4-7c3e-7a11-8b2d-5e6f7a8b9c0d" * 2,
        UID.replace("-", "_"),
        "00000000-0000-0000-0000-00000000000",
    ],
)
def test_bad_ids(i: object) -> None:
    rejected(good(id_=i))


@pytest.mark.parametrize(
    "obj",
    [
        {"v": 1, "k": "a"},
        {"v": 1, "id": UID},
        {"k": "a", "id": UID},
        {"v": 1, "k": "a", "id": UID, "x": 1},
        {"v": 1, "k": "a", "id": UID, "sig": "abc"},
        {"V": 1, "k": "a", "id": UID},
        {"v": 1, "K": "a", "id": UID},
        {"v": 1, "k": "a", "ID": UID},
        {"v": 1, "k": "a", "id ": UID},
        {},
        [],
        [1, "a", UID],
        {"v": 1, "k": "a", "id": UID, "__proto__": {}},
    ],
)
def test_extra_missing_wrong_case_keys(obj: object) -> None:
    rejected(tok(obj))


def test_non_canonical_byte_forms_are_rejected() -> None:
    """Fix of QA-S1T03-007: only the exact bytes encode_cursor emits are accepted."""
    reordered = tok(raw=f'{{"id":"{UID}","k":"a","v":1}}')
    spaced = tok(raw=f'{{ "v": 1, "k": "a", "id": "{UID}" }}')
    escaped = tok(raw=f'{{"v":1,"k":"\\u0061","id":"{UID}"}}')
    for t in (reordered, spaced, escaped):
        rejected(t)
    assert decode_cursor(tok(raw=f'{{"v":1,"k":"a","id":"{UID}"}}'), "str").key == "a"


@pytest.mark.parametrize("esc", ["\\ud800", "\\u0000"])
def test_BUG_QA_S1T03_002_str_key_with_unbindable_characters_is_400(esc: str) -> None:
    """Lone surrogate / NUL in a str key cannot be bound as a Postgres text parameter; they
    must be rejected as 400 here, otherwise they become a 500 downstream."""
    rejected(tok(raw=f'{{"v":1,"k":"{esc}","id":"{UID}"}}'))


def test_invalid_key_type_argument_is_programmer_error_not_400() -> None:
    with pytest.raises(ValueError) as ei:
        decode_cursor(good(), "float")  # type: ignore[arg-type]
    assert not isinstance(ei.value, BadRequest)


def test_fuzz_never_anything_but_cursor_or_badrequest() -> None:
    import random

    rnd = random.Random(1234)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    base = good("abc")
    for _ in range(20000):
        kind = rnd.randrange(3)
        if kind == 0:
            t = "".join(rnd.choice(alphabet) for _ in range(rnd.randrange(0, 80)))
        elif kind == 1:
            i = rnd.randrange(len(base))
            t = base[:i] + rnd.choice(alphabet) + base[i + 1 :]
        else:
            raw = bytes(rnd.randrange(256) for _ in range(rnd.randrange(0, 60)))
            t = b64(raw)
        for kt in ("str", "int", "datetime"):
            try:
                c = decode_cursor(t, kt)  # type: ignore[arg-type]
            except BadRequest:
                continue
            # anything accepted must re-encode to a token that decodes identically
            assert decode_cursor(encode_cursor(c.key, c.id), kt) == c  # type: ignore[arg-type]
