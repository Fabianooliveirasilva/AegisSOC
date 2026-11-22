"""SR-18 log redaction / log forging, UUIDv7, FrozenClock (QA-written, S1-T03)."""

import io
import json
import re
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
import structlog
from aegissoc.core.clock import FrozenClock, SystemClock
from aegissoc.core.ids import new_id
from aegissoc.core.logging import configure_logging, get_logger, redact_sensitive

from .conftest import log_lines

SENSITIVE = [
    "password",
    "PASSWORD",
    "Password",
    "user_password",
    "passwordHash",
    "secret",
    "client_secret",
    "SECRET_KEY",
    "token",
    "access_token",
    "X-CSRF-Token",
    "csrf_token",
    "session",
    "session_id",
    "sessionid",
    "Authorization",
    "authorization",
    "AUTHORIZATION",
    "proxy-authorization",
    "cookie",
    "Cookie",
    "Set-Cookie",
    "set_cookie",
    "api_key",
    "api-key",
    "apikey",
    "X-Api-Key",
    "x-api-key",
]


def run(d: dict) -> dict:
    return redact_sensitive(None, "info", d)


@pytest.mark.parametrize("key", SENSITIVE)
def test_top_level_keys_dropped(key: str) -> None:
    out = run({"event": "e", key: "LEAK", "keep": 1})
    assert key not in out and out["keep"] == 1


@pytest.mark.parametrize("key", SENSITIVE)
def test_nested_and_list_of_dicts_and_header_dicts(key: str) -> None:
    ev = {
        "event": "e",
        "a": {"b": {"c": [{key: "LEAK", "ok": 1}, [{"deep": {key: "LEAK"}}]]}},
        "headers": {key: "LEAK", "User-Agent": "x"},
        "tup": ({key: "LEAK"},),
    }
    out = run(ev)
    assert "LEAK" not in json.dumps(out, default=str)
    assert out["headers"] == {"User-Agent": "x"}


def test_odd_key_types() -> None:
    out = run(
        {
            "event": "e",
            1: "a",
            ("x", "password"): "LEAK",
            b"password": "LEAK2",
            None: "n",
            3.5: "f",
            "ok": {5: 1, b"token": "LEAK3", frozenset({"t"}): 2},
        }
    )
    assert "LEAK" not in repr(out)


def test_does_not_mutate_input() -> None:
    inner = {"password": "x", "a": 1}
    ev = {"event": "e", "n": inner}
    run(ev)
    assert inner == {"password": "x", "a": 1}


def test_cyclic_structure_does_not_hang_or_crash() -> None:
    d: dict = {"event": "e"}
    d["self"] = d
    lst: list = []
    lst.append(lst)
    d["lst"] = lst
    json.dumps(run(d))  # terminates, serialisable


def test_very_deep_nesting_no_recursion_error_and_no_leak() -> None:
    d: dict = {"password": "LEAK"}
    for _ in range(5000):
        d = {"n": d}
    out = run({"event": "e", "d": d})
    assert "LEAK" not in json.dumps(out)


def test_BUG_QA_S1T03_003_list_of_header_pairs_is_redacted() -> None:
    """ASGI-style headers [(name, value)]: key-based redaction cannot see the pair."""
    out = run(
        {
            "event": "e",
            "headers": [("authorization", "Bearer LEAK"), ("cookie", "s=LEAK")],
        }
    )
    assert "LEAK" not in json.dumps(out)  # QA-S1T03-003 (S3): fails today


def test_known_gap_sets_and_objects_not_traversed() -> None:
    class Box:
        def __repr__(self) -> str:
            return "Box(password='LEAK')"

    out = run({"event": "e", "s": {("password", "LEAK")}, "box": Box()})
    rendered = structlog.processors.JSONRenderer()(None, "info", out)
    assert "LEAK" in rendered  # documented limitation (repr fallback); S4


def _logger_to_stream(level: str = "DEBUG") -> io.StringIO:
    s = io.StringIO()
    configure_logging(level, s)
    return s


def test_end_to_end_redaction_through_configured_logger(
    log_stream: io.StringIO,
) -> None:
    log = get_logger("qa")
    log.info(
        "login",
        password="LEAK1",
        user={"Authorization": "LEAK2", "name": "bob"},
        headers={"Cookie": "LEAK3"},
        items=[{"api_key": "LEAK4"}],
    )
    out = log_stream.getvalue()
    for n in "1234":
        assert f"LEAK{n}" not in out
    rec = json.loads(out)
    assert rec["event"] == "login" and rec["user"] == {"name": "bob"}


def test_bound_and_contextvar_values_are_redacted_too(log_stream: io.StringIO) -> None:
    structlog.contextvars.bind_contextvars(
        session_id="LEAKCTX", request_id="rid-12345678"
    )
    log = get_logger("qa").bind(token="LEAKBOUND")
    log.info("x")
    out = log_stream.getvalue()
    assert "LEAKCTX" not in out and "LEAKBOUND" not in out and "rid-12345678" in out


def test_module_level_logger_created_before_configure_still_redacts() -> None:
    log = get_logger("early")
    s = _logger_to_stream()
    try:
        log.info("x", password="LEAK")
        assert "LEAK" not in s.getvalue() and s.getvalue().strip()
    finally:
        structlog.reset_defaults()


FORGE = [
    "a\nb",
    "a\r\nb",
    'x"}\n{"event":"forged","level":"critical"}',
    "a b",
    "\x00\x1b[31m",
    "é\u0085x",
    "a\rb",
]


@pytest.mark.parametrize("payload", FORGE)
def test_log_forging_values_stay_on_one_line(
    log_stream: io.StringIO, payload: str
) -> None:
    log = get_logger("qa")
    log.info("evt", user_agent=payload, nested={"k": [payload]})
    lines = log_lines(log_stream)
    assert len(lines) == 1 and lines[0]["user_agent"] == payload
    assert log_stream.getvalue().count("\n") == 1


@pytest.mark.parametrize("payload", FORGE)
def test_log_forging_in_message_and_keys(log_stream: io.StringIO, payload: str) -> None:
    log = get_logger("qa")
    log.info(payload, **{payload: 1})
    assert len(log_lines(log_stream)) == 1


def test_exception_logging_single_line_json_no_secret_key(
    log_stream: io.StringIO,
) -> None:
    log = get_logger("qa")
    try:
        raise RuntimeError("boom\nforged")
    except RuntimeError:
        log.exception("failed", password="LEAK")
    lines = log_lines(log_stream)
    assert len(lines) == 1 and "LEAK" not in log_stream.getvalue()


def test_level_filter_and_bad_level() -> None:
    s = io.StringIO()
    configure_logging("warning", s)
    try:
        get_logger("q").info("hidden")
        get_logger("q").warning("shown")
        assert [r["event"] for r in log_lines(s)] == ["shown"]
        with pytest.raises(ValueError):
            configure_logging("nope")
    finally:
        structlog.reset_defaults()


def test_non_serialisable_values_do_not_crash(log_stream: io.StringIO) -> None:
    get_logger("q").info(
        "x", o=object(), s={1, 2}, b=b"\xff", d=datetime.now(UTC), u=uuid.uuid4()
    )
    assert len(log_lines(log_stream)) == 1


# ---- ids -------------------------------------------------------------------
def test_uuid7_shape_and_ordering() -> None:
    ids = [new_id() for _ in range(20000)]
    assert all(
        type(i) is uuid.UUID and i.version == 7 and i.variant == uuid.RFC_4122
        for i in ids
    )
    assert len({*ids}) == len(ids)
    assert [i.int for i in ids] == sorted(
        i.int for i in ids
    )  # time-ordered within a process
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        str(ids[0]),
    )


def test_uuid7_embeds_current_time() -> None:
    before = int(datetime.now(UTC).timestamp() * 1000)
    ms = new_id().int >> 80
    after = int(datetime.now(UTC).timestamp() * 1000)
    assert before - 1 <= ms  # never in the past
    assert after >= before  # upper bound intentionally absent: see burst-skew test


def test_uuid7_burst_skew_documented() -> None:
    """QA-S1T03-006 (S4): uuid6.uuid7 advances the embedded ms by 1 per id when called faster
    than 1/ms, so a burst of N ids ends ~N ms in the future. Order stays strictly monotonic."""
    for _ in range(3000):
        last = new_id()
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    assert (
        last.int >> 80
    ) - now_ms > 1000  # flip to `<= 5` if the generator is changed


# ---- clock -----------------------------------------------------------------
def test_frozen_clock_behaviour() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    c = FrozenClock(start)
    assert c.now() == start and c.now() is c.now()
    c.advance(timedelta(seconds=90))
    assert c.now() == start + timedelta(seconds=90)
    c.advance(timedelta(seconds=-90))
    assert c.now() == start
    with pytest.raises(ValueError):
        FrozenClock(datetime(2026, 1, 1))
    c2 = FrozenClock(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))))
    assert c2.now().utcoffset() == timedelta(hours=2)


def test_system_clock_is_aware_utc_and_monotone_enough() -> None:
    a = SystemClock().now()
    assert a.tzinfo is not None and a.utcoffset() == timedelta(0)
    assert abs((datetime.now(UTC) - a).total_seconds()) < 5
