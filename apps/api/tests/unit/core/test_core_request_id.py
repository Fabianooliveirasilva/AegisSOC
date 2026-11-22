"""core.request_id: X-Request-ID validation, echo and log-context binding (AC-PLAT-10)."""

import io
import json
import uuid
from typing import Any

import pytest
import structlog
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from aegissoc.core.logging import configure_logging, get_logger
from aegissoc.core.request_id import RequestIdMiddleware, is_valid_request_id


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/id")
    async def read_id(request: Request) -> dict[str, str]:
        get_logger("test").info("inside handler")
        return {"request_id": request.state.request_id}

    @app.get("/own-header")
    async def own_header() -> Any:
        from fastapi.responses import JSONResponse

        return JSONResponse({}, headers={"X-Request-ID": "handler-chosen-id"})

    return app


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "value",
    ["abcd1234", "A" * 64, "0190b4f2-7c9e-7a11-8d3e-aabbccddeeff", "req-ABC-123-xyz"],
)
def test_valid_ids_are_accepted(value: str) -> None:
    assert is_valid_request_id(value)


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    "value",
    [
        "",
        "short",
        "A" * 7,
        "A" * 65,
        "abcd1234\n",
        "abcd\n1234",
        "abcd 1234",
        'abcd"1234',
        "abcd_1234",
        "abcd.1234",
        "abcd/1234",
        "abcd1234\r\nX-Injected: 1",
        "ábcd1234",
        "abcd1234\x00",
    ],
)
def test_invalid_ids_are_rejected(value: str) -> None:
    assert not is_valid_request_id(value)


@pytest.mark.req("AC-PLAT-10")
def test_valid_incoming_id_is_used_and_echoed() -> None:
    response = TestClient(_app()).get("/id", headers={"X-Request-ID": "client-id-12345"})
    assert response.headers["x-request-id"] == "client-id-12345"
    assert response.json()["request_id"] == "client-id-12345"


@pytest.mark.req("AC-PLAT-10")
def test_missing_id_is_generated_as_uuid7() -> None:
    response = TestClient(_app()).get("/id")
    generated = response.headers["x-request-id"]
    assert uuid.UUID(generated).version == 7
    assert response.json()["request_id"] == generated


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize("bad", ["short", "x" * 65, "has space in it", "bad_underscore_id"])
def test_invalid_incoming_id_is_replaced_not_echoed(bad: str) -> None:
    response = TestClient(_app()).get("/id", headers={"X-Request-ID": bad})
    replaced = response.headers["x-request-id"]
    assert replaced != bad
    assert uuid.UUID(replaced).version == 7


@pytest.mark.req("AC-PLAT-10")
def test_exactly_one_response_header_even_if_handler_sets_its_own() -> None:
    response = TestClient(_app()).get("/own-header", headers={"X-Request-ID": "client-id-12345"})
    values = response.headers.get_list("x-request-id")
    assert values == ["client-id-12345"]


@pytest.mark.req("AC-PLAT-10")
def test_request_id_is_bound_to_the_log_context_during_the_request() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    TestClient(_app()).get("/id", headers={"X-Request-ID": "client-id-12345"})
    (record,) = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert record["request_id"] == "client-id-12345"


@pytest.mark.req("AC-PLAT-10")
def test_log_context_does_not_leak_after_the_request() -> None:
    TestClient(_app()).get("/id", headers={"X-Request-ID": "client-id-12345"})
    assert "request_id" not in structlog.contextvars.get_contextvars()


@pytest.mark.req("AC-PLAT-10")
def test_non_http_scopes_pass_through() -> None:
    with TestClient(_app()):  # runs the lifespan scope through the middleware
        pass


async def _noop_receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _collect(messages: list[dict[str, Any]]) -> Any:
    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    return send


def _scope(request_id: bytes | None = b"client-id-12345") -> dict[str, Any]:
    headers = [(b"x-request-id", request_id)] if request_id else []
    return {"type": "http", "method": "GET", "path": "/", "headers": headers}


@pytest.mark.req("AC-PLAT-10")
async def test_outer_log_context_is_preserved_and_only_request_id_is_removed() -> None:
    seen: dict[str, Any] = {}

    async def app(scope: Any, receive: Any, send: Any) -> None:
        seen.update(structlog.contextvars.get_contextvars())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(client_ip="10.0.0.1")
    try:
        send = await _collect([])
        await RequestIdMiddleware(app)(_scope(), _noop_receive, send)
        assert seen == {"client_ip": "10.0.0.1", "request_id": "client-id-12345"}
        assert structlog.contextvars.get_contextvars() == {"client_ip": "10.0.0.1"}
    finally:
        structlog.contextvars.clear_contextvars()


@pytest.mark.req("AC-PLAT-10")
async def test_an_outer_request_id_is_restored_after_the_request() -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="outer-request-id")
    try:
        send = await _collect([])
        await RequestIdMiddleware(app)(_scope(), _noop_receive, send)
        assert structlog.contextvars.get_contextvars() == {"request_id": "outer-request-id"}
    finally:
        structlog.contextvars.clear_contextvars()


@pytest.mark.req("AC-PLAT-10")
async def test_context_is_restored_even_when_the_application_raises() -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        raise RuntimeError("application failure")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(client_ip="10.0.0.1")
    try:
        send = await _collect([])
        with pytest.raises(RuntimeError, match="application failure"):
            await RequestIdMiddleware(app)(_scope(), _noop_receive, send)
        assert structlog.contextvars.get_contextvars() == {"client_ip": "10.0.0.1"}
    finally:
        structlog.contextvars.clear_contextvars()
