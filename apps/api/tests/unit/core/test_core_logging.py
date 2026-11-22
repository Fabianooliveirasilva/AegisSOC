"""core.logging: structlog JSON output and the SR-18 redaction processor."""

import io
import json
from typing import Any

import pytest
import structlog

from aegissoc.core.logging import configure_logging, get_logger, redact_sensitive


def _redact(event: dict[str, Any]) -> dict[str, Any]:
    return dict(redact_sensitive(None, "info", event))


@pytest.mark.req("SR-18")
@pytest.mark.parametrize(
    "key",
    [
        "password",
        "PASSWORD",
        "new_password",
        "db_password_file_value",
        "secret",
        "client_secret",
        "token",
        "csrf_token",
        "X-CSRF-Token",
        "session",
        "session_id",
        "Authorization",
        "authorization_header",
        "Cookie",
        "Set-Cookie",
        "x-api-key",
        "api_key",
        "apiKey",
    ],
)
def test_sensitive_keys_are_dropped(key: str) -> None:
    result = _redact({"event": "login", key: "value-that-must-not-be-logged"})
    assert key not in result
    assert "value-that-must-not-be-logged" not in json.dumps(result)
    assert result["event"] == "login"


@pytest.mark.req("SR-18")
def test_harmless_keys_and_values_are_kept() -> None:
    event = {"event": "request", "path": "/api/v1/alerts", "status": 200, "user_id": "u1"}
    assert _redact(event) == event


@pytest.mark.req("SR-18")
def test_nested_dicts_lists_and_tuples_are_cleaned() -> None:
    event = {
        "event": "request",
        "headers": {"Authorization": "Bearer x", "Accept": "json", "inner": {"cookie": "c"}},
        "items": [{"token": "t", "ok": 1}, ("a", {"password": "p"})],
    }
    result = _redact(event)
    dumped = json.dumps(result)
    for leaked in ("Bearer x", '"c"', '"t"', '"p"'):
        assert leaked not in dumped
    assert result["headers"]["Accept"] == "json"
    assert result["items"][0] == {"ok": 1}


@pytest.mark.req("SR-18")
def test_redaction_does_not_mutate_its_input() -> None:
    event = {"event": "x", "headers": {"Authorization": "a"}}
    _redact(event)
    assert event["headers"] == {"Authorization": "a"}


@pytest.mark.req("SR-18")
def test_very_deep_structures_do_not_crash_logging() -> None:
    deep: dict[str, Any] = {}
    cursor = deep
    for _ in range(5000):
        cursor["a"] = {}
        cursor = cursor["a"]
    cursor["password"] = "deep-secret"  # noqa: S105 - fake secret, must never be logged
    result = _redact({"event": "x", "payload": deep})
    assert "deep-secret" not in json.dumps(result, default=repr)[:100000]


def _logger_output(log: Any, stream: io.StringIO) -> list[dict[str, Any]]:
    del log
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.mark.req("SR-18")
def test_output_is_one_json_object_per_line_with_standard_fields() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    get_logger("test").info("hello", answer=42)
    (record,) = _logger_output(None, stream)
    assert record["event"] == "hello"
    assert record["answer"] == 42
    assert record["level"] == "info"
    assert record["timestamp"].endswith("Z")


@pytest.mark.req("SR-18")
def test_newlines_in_untrusted_values_cannot_forge_log_lines() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    forged = 'ok"}\n{"event":"admin.login","level":"info"'
    get_logger("test").info("request", user_agent=forged)
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["user_agent"] == forged


@pytest.mark.req("SR-18")
def test_secrets_never_reach_the_output() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    get_logger("test").info(
        "login",
        username="ana",
        password="hunter2",  # noqa: S106 - fake value, must never be logged
        cookie="sid=abc",
    )
    output = stream.getvalue()
    assert "hunter2" not in output
    assert "sid=abc" not in output
    assert json.loads(output)["username"] == "ana"


@pytest.mark.req("AC-PLAT-10")
def test_bound_context_variables_are_included() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-12345678")
    try:
        get_logger("test").info("inside request")
    finally:
        structlog.contextvars.clear_contextvars()
    (record,) = _logger_output(None, stream)
    assert record["request_id"] == "req-12345678"


@pytest.mark.req("SR-18")
def test_level_filtering_applies() -> None:
    stream = io.StringIO()
    configure_logging(level="WARNING", stream=stream)
    get_logger("test").info("dropped")
    get_logger("test").warning("kept")
    assert [r["event"] for r in _logger_output(None, stream)] == ["kept"]


@pytest.mark.req("SR-18")
def test_exceptions_are_rendered_as_text_in_the_json_record() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        get_logger("test").exception("failed")
    (record,) = _logger_output(None, stream)
    assert "RuntimeError: boom" in record["exception"]


_IMPORT_TIME_LOGGER = get_logger("created.at.import.time")


@pytest.mark.req("SR-18")
def test_logger_created_before_configuration_still_uses_the_configured_json_output() -> None:
    """Module-level loggers (created at import) must honour a later configure_logging()."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    _IMPORT_TIME_LOGGER.info("late", password="must-not-appear")  # noqa: S106 - fake
    (record,) = _logger_output(None, stream)
    assert record["event"] == "late"
    assert record["logger_name"] == "created.at.import.time"
    assert "must-not-appear" not in stream.getvalue()


@pytest.mark.req("SR-18")
def test_deeply_nested_lists_are_truncated_not_recursed_forever() -> None:
    deep: Any = ["leaf-with-secret-context"]
    for _ in range(5000):
        deep = [deep]
    result = _redact({"event": "x", "payload": deep})
    assert "leaf-with-secret-context" not in json.dumps(result, default=repr)[:100000]


@pytest.mark.req("SR-18")
def test_unknown_log_level_is_a_configuration_error() -> None:
    with pytest.raises(ValueError, match="unknown log level"):
        configure_logging(level="LOUD")


@pytest.mark.req("SR-18")
def test_log_level_names_are_case_insensitive() -> None:
    stream = io.StringIO()
    configure_logging(level="warning", stream=stream)
    get_logger("test").info("dropped")
    get_logger("test").warning("kept")
    assert [r["event"] for r in _logger_output(None, stream)] == ["kept"]
