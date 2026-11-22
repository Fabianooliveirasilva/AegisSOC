"""AC-PLAT-10 / TC-PLAT-08 at unit level (test app installing the core handlers) and
request-id behaviour, from the outside via ASGI (QA-written, S1-T03)."""

import asyncio
import io
import json
import random
import uuid

import httpx
import pytest
import structlog
from aegissoc.core.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    InvalidTransition,
    NotFound,
    VersionMismatch,
    install_error_handlers,
)
from aegissoc.core.logging import get_logger
from aegissoc.core.request_id import RequestIdMiddleware, is_valid_request_id
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from .conftest import log_lines

PROBLEM = "application/problem+json"
SECRET_VALUE = "hunter2-SUBMITTED-VALUE"


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=8)
    severity: int
    when: uuid.UUID | None = None


def make_app(*, middleware_outermost: bool = True) -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    log = get_logger("qa.app")

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        log.info("handler")
        return {"ok": "1"}

    @app.post("/body")
    async def body(b: Body) -> dict[str, str]:
        return {"ok": "1"}

    @app.get("/q")
    async def q(n: int = Query(...)) -> dict[str, int]:
        return {"n": n}

    @app.get("/http/{code}")
    async def http(code: int) -> None:
        raise HTTPException(code, detail="nope", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/http-hdr-dup")
    async def http_dup() -> None:
        raise HTTPException(
            418, detail="x", headers={"x-request-id": "evil", "X-Request-ID": "evil2"}
        )

    @app.get("/http-dictdetail")
    async def http_dd() -> None:
        raise HTTPException(400, detail={"password": "LEAK"})

    @app.get("/dom/{kind}")
    async def dom(kind: str) -> None:
        raise {
            "nf": NotFound,
            "c": Conflict,
            "it": InvalidTransition,
            "vm": VersionMismatch,
            "f": Forbidden,
            "br": BadRequest,
        }[kind]()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError(f"db password={SECRET_VALUE} at /srv/app/secret.py")

    @app.get("/boom-http-subclass")
    async def boom2() -> None:
        raise KeyError(SECRET_VALUE)

    @app.get("/stream-fail")
    async def stream_fail() -> StreamingResponse:
        async def gen():
            yield b"abc"
            raise RuntimeError("late " + SECRET_VALUE)

        return StreamingResponse(gen(), media_type="text/plain")

    @app.get("/stream-ok")
    async def stream_ok() -> StreamingResponse:
        async def gen():
            yield b"abc"

        return StreamingResponse(gen(), headers={"X-Request-ID": "handler-set-id"})

    @app.get("/bg-fail")
    async def bg_fail(bt: BackgroundTasks) -> dict[str, str]:
        def task() -> None:
            raise RuntimeError("bg " + SECRET_VALUE)

        bt.add_task(task)
        return {"ok": "1"}

    @app.get("/handler-sets-header")
    async def hs():
        from fastapi.responses import JSONResponse

        return JSONResponse({}, headers={"X-Request-ID": "handler-set-id"})

    @app.get("/slow/{rid}")
    async def slow(rid: str) -> dict[str, str]:
        log.info("start", mark=rid)
        await asyncio.sleep(random.random() / 50)
        log.info("middle", mark=rid)
        await asyncio.sleep(random.random() / 50)
        log.info("end", mark=rid)
        return {"rid": rid}

    if middleware_outermost:
        app.add_middleware(RequestIdMiddleware)
    return app


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://t",
    )


def assert_problem(r: httpx.Response, status: int) -> dict:
    assert r.status_code == status, r.text
    assert r.headers["content-type"].split(";")[0] == PROBLEM
    b = r.json()
    assert b["status"] == status and b["type"].startswith(
        "https://aegissoc.local/problems/"
    )
    assert b["title"] and b["detail"] and b["instance"].startswith("/")
    assert b["request_id"] == r.headers["x-request-id"]
    assert len(r.headers.get_list("x-request-id")) == 1
    return b


@pytest.fixture
def app(log_stream: io.StringIO) -> FastAPI:
    return make_app()


async def test_every_error_class_is_problem_json(app: FastAPI) -> None:
    cases = [
        ("GET", "/nope", 404, "not-found"),
        ("POST", "/ok", 405, None),
        ("GET", "/q", 422, "validation-error"),
        ("GET", "/q?n=abc", 422, "validation-error"),
        ("POST", "/body", 422, "validation-error"),
        ("GET", "/dom/nf", 404, "not-found"),
        ("GET", "/dom/c", 409, "conflict"),
        ("GET", "/dom/it", 409, "invalid-transition"),
        ("GET", "/dom/vm", 409, "version-mismatch"),
        ("GET", "/dom/f", 403, "forbidden"),
        ("GET", "/dom/br", 400, "bad-request"),
        ("GET", "/boom", 500, "internal-error"),
        ("GET", "/boom-http-subclass", 500, "internal-error"),
    ]
    async with client(app) as c:
        for method, path, status, slug in cases:
            r = await c.request(
                method, path, json={} if method == "POST" and path == "/body" else None
            )
            b = assert_problem(r, status)
            if slug:
                assert b["type"].endswith("/" + slug), (path, b)


@pytest.mark.parametrize(
    ("code", "slug"),
    [
        (400, "bad-request"),
        (401, "unauthenticated"),
        (403, "forbidden"),
        (404, "not-found"),
        (409, "conflict"),
        (413, "payload-too-large"),
        (415, "unsupported-media-type"),
        (422, "validation-error"),
        (429, "rate-limited"),
        (500, "internal-error"),
        (503, "unavailable"),
    ],
)
async def test_http_exception_slugs_headers_preserved(
    app: FastAPI, code: int, slug: str
) -> None:
    async with client(app) as c:
        r = await c.get(f"/http/{code}")
    b = assert_problem(r, code)
    assert b["type"].endswith("/" + slug)
    assert r.headers["www-authenticate"] == "Bearer"


async def test_http_exception_with_dict_detail_does_not_leak(app: FastAPI) -> None:
    async with client(app) as c:
        r = await c.get("/http-dictdetail")
    assert_problem(r, 400)
    assert "LEAK" not in r.text


async def test_500_has_no_traceback_message_class_or_path(
    app: FastAPI, log_stream: io.StringIO
) -> None:
    async with client(app) as c:
        r = await c.get("/boom", headers={"X-Request-ID": "req-abcdef12"})
    assert_problem(r, 500)
    for needle in (
        SECRET_VALUE,
        "RuntimeError",
        "Traceback",
        "secret.py",
        "/srv",
        'File "',
    ):
        assert needle not in r.text, needle
    assert r.json()["request_id"] == "req-abcdef12"
    logs = log_stream.getvalue()
    assert SECRET_VALUE not in logs  # message not logged
    rec = [x for x in log_lines(log_stream) if x["event"] == "unhandled_exception"]
    assert len(rec) == 1 and rec[0]["request_id"] == "req-abcdef12"
    assert rec[0]["error_type"] == "RuntimeError"


async def test_500_without_middleware_still_problem_json_with_request_id(
    log_stream: io.StringIO,
) -> None:
    async with client(make_app(middleware_outermost=False)) as c:
        r = await c.get("/boom", headers={"X-Request-ID": "client-sent-id1"})
    b = assert_problem(r, 500)
    uuid.UUID(b["request_id"])  # no middleware -> generated, client id not trusted


async def test_validation_errors_never_echo_submitted_values(app: FastAPI) -> None:
    payloads = [
        {"name": SECRET_VALUE, "severity": SECRET_VALUE},
        {"name": "ok!", "severity": 1, "extra_" + "password": SECRET_VALUE},
        {"name": "okok", "severity": {"password": SECRET_VALUE}},
        {"name": "okok", "severity": 1, "when": SECRET_VALUE},
        [SECRET_VALUE],
        SECRET_VALUE,
    ]
    async with client(app) as c:
        for p in payloads:
            r = await c.post("/body", json=p)
            assert_problem(r, 422)
            assert SECRET_VALUE not in r.text, (p, r.text)
        r = await c.get("/q", params={"n": SECRET_VALUE})
        assert SECRET_VALUE not in r.text
        for e in r.json()["errors"]:
            assert set(e) == {"loc", "msg", "type"}


async def test_validation_loc_echoes_attacker_key_names_documented(
    app: FastAPI,
) -> None:
    """Field *names* chosen by the caller are reflected in `loc` (values are not). S4 note."""
    async with client(app) as c:
        r = await c.post(
            "/body", json={"name": "okok", "severity": 1, "zz_attacker_key": 1}
        )
    assert r.status_code == 422 and "zz_attacker_key" in r.text


async def test_malformed_json_is_400_bad_request(app: FastAPI) -> None:
    async with client(app) as c:
        for raw in (b"{", b"", b"\xff\xfe", b'{"a":1,}', b"nul\x00l"):
            r = await c.post(
                "/body", content=raw, headers={"content-type": "application/json"}
            )
            if (
                r.status_code == 422
            ):  # empty body is a "missing" error in FastAPI; accept 422 only for b""
                assert raw == b""
                continue
            b = assert_problem(r, 400)
            assert b["type"].endswith("/bad-request")
            assert raw.decode("latin-1") not in b["detail"] or raw == b""


async def test_instance_has_no_query_string(app: FastAPI) -> None:
    async with client(app) as c:
        r = await c.get("/q", params={"n": "x", "access_token": "TOPSECRETQS"})
    assert "TOPSECRETQS" not in r.text and r.json()["instance"] == "/q"


async def test_handler_cannot_cause_duplicate_request_id_headers(app: FastAPI) -> None:
    async with client(app) as c:
        for path in ("/http-hdr-dup", "/stream-ok", "/handler-sets-header"):
            r = await c.get(path)
            ids = r.headers.get_list("x-request-id")
            assert len(ids) == 1 and ids[0] not in (
                "evil",
                "evil2",
                "handler-set-id",
            ), path


async def test_head_and_options(app: FastAPI) -> None:
    async with client(app) as c:
        h = await c.head("/ok")
        assert h.status_code == 405 or h.status_code == 200
        assert len(h.headers.get_list("x-request-id")) == 1
        h404 = await c.head("/nope")
        assert h404.status_code == 404 and h404.content == b""
        assert h404.headers["content-type"].startswith(PROBLEM)
        assert h404.headers["x-request-id"]
        o = await c.options("/ok", headers={"X-Request-ID": "optid-12345"})
        assert o.status_code == 405
        assert o.headers["content-type"].startswith(PROBLEM)
        assert (
            o.headers["x-request-id"] == "optid-12345"
            and o.json()["request_id"] == "optid-12345"
        )
        assert o.headers.get("allow")


# ---- request id validation ---------------------------------------------------
VALID = [
    "a" * 8,
    "A" * 64,
    "0123456789",
    "a-b-c-d-e-f",
    "-" * 8,
    "0" * 63,
    "f" * 64,
    "9f1c2b3a-1111-4222-8333-444455556666",
]
INVALID = [
    "a" * 7,
    "a" * 65,
    "a" * 63 + "\n",
    "a" * 8 + "\n",
    "abcdefgh\r\nSet-Cookie: x=1",
    "abcdefgh ",
    " abcdefgh",
    "abcd_efgh",
    "abcdéfgh",
    "ｆｕｌｌｗｉｄｔｈｉｄ",
    "abcdefg\x00h",
    "٠١٢٣٤٥٦٧٨٩",
    "abcdefgh\t",
    "a" * 4000,
    "",
    "abc.defgh",
    "../../etc/passwd",
]


@pytest.mark.parametrize("rid", VALID)
def test_validator_accepts(rid: str) -> None:
    assert is_valid_request_id(rid)


@pytest.mark.parametrize("rid", INVALID)
def test_validator_rejects(rid: str) -> None:
    assert not is_valid_request_id(rid)


@pytest.mark.parametrize("rid", VALID)
async def test_valid_id_echoed_and_logged(
    app: FastAPI, rid: str, log_stream: io.StringIO
) -> None:
    async with client(app) as c:
        r = await c.get("/ok", headers={"X-Request-ID": rid})
    assert (
        r.headers["x-request-id"] == rid
        and len(r.headers.get_list("x-request-id")) == 1
    )
    handler_logs = [x for x in log_lines(log_stream) if x["event"] == "handler"]
    assert handler_logs and handler_logs[0]["request_id"] == rid


@pytest.mark.parametrize(
    "raw",
    [
        b"a" * 7,
        b"a" * 65,
        b"a" * 8 + b"\n",
        b"abcd_efgh",
        b"abc\xc3\xa9defgh",
        b"abc\xe9defgh",
        b"",
        b"\t\x01abcdefgh",
        b"a" * 8000,
    ],
)
async def test_invalid_raw_header_replaced_by_uuid7_never_echoed(
    app: FastAPI, raw: bytes
) -> None:
    """Raw header bytes sent over ASGI scope so we control the exact wire value."""
    async with client(app) as c:
        r = await c.request("GET", "/ok", headers=[(b"x-request-id", raw)])  # type: ignore[arg-type]
    echoed = r.headers["x-request-id"]
    u = uuid.UUID(echoed)
    assert u.version == 7 and echoed != raw.decode("latin-1")


async def test_duplicate_incoming_headers_first_wins_or_generated(app: FastAPI) -> None:
    async with client(app) as c:
        r = await c.get(
            "/ok",
            headers=[
                ("X-Request-ID", "first-id-1234"),
                ("X-Request-ID", "second-id-5678"),
            ],
        )
    assert r.headers["x-request-id"] in ("first-id-1234",) or uuid.UUID(
        r.headers["x-request-id"]
    )
    assert len(r.headers.get_list("x-request-id")) == 1


async def test_each_request_without_header_gets_distinct_id(app: FastAPI) -> None:
    async with client(app) as c:
        ids = {(await c.get("/ok")).headers["x-request-id"] for _ in range(50)}
    assert len(ids) == 50


async def test_no_contextvar_leak_after_request(
    app: FastAPI, log_stream: io.StringIO
) -> None:
    async with client(app) as c:
        await c.get("/ok", headers={"X-Request-ID": "leak-check-1"})
        await c.get("/ok")
    recs = [x for x in log_lines(log_stream) if x["event"] == "handler"]
    assert (
        recs[0]["request_id"] == "leak-check-1"
        and recs[1]["request_id"] != "leak-check-1"
    )
    assert "request_id" not in structlog.contextvars.get_contextvars()


async def test_concurrent_requests_each_log_line_carries_its_own_id(
    app: FastAPI, log_stream: io.StringIO
) -> None:
    ids = [f"conc-{i:05d}-{uuid.uuid4().hex[:8]}" for i in range(300)]
    async with client(app) as c:
        rs = await asyncio.gather(
            *[c.get(f"/slow/{i}", headers={"X-Request-ID": i}) for i in ids]
        )
    for i, r in zip(ids, rs, strict=True):
        assert r.headers["x-request-id"] == i and r.json() == {"rid": i}
    marks = [x for x in log_lines(log_stream) if "mark" in x]
    assert len(marks) == 900
    assert all(x["request_id"] == x["mark"] for x in marks)


async def test_concurrent_errors_carry_own_request_id(app: FastAPI) -> None:
    ids = [f"err-{i:05d}-{uuid.uuid4().hex[:8]}" for i in range(100)]
    async with client(app) as c:
        rs = await asyncio.gather(
            *[
                c.get(
                    random.choice(["/boom", "/nope", "/dom/c", "/q"]),
                    headers={"X-Request-ID": i},
                )
                for i in ids
            ]
        )
    for i, r in zip(ids, rs, strict=True):
        assert r.json()["request_id"] == i == r.headers["x-request-id"]


# ---- after response started / streaming / background ----------------------------
async def test_streaming_failure_after_start(app: FastAPI) -> None:
    async with client(app) as c:
        r = await c.get("/stream-fail", headers={"X-Request-ID": "stream-id-123"})
    # headers were already sent: 200, single request id, no traceback/secret in what the client got
    assert r.headers["x-request-id"] == "stream-id-123"
    assert SECRET_VALUE not in r.text and "Traceback" not in r.text


async def test_background_task_failure_does_not_break_response(app: FastAPI) -> None:
    async with client(app) as c:
        r = await c.get("/bg-fail", headers={"X-Request-ID": "bg-task-id-1"})
    assert r.status_code == 200 and r.headers["x-request-id"] == "bg-task-id-1"
    assert len(r.headers.get_list("x-request-id")) == 1


# ---- middleware ordering ------------------------------------------------------
async def test_with_basehttpmiddleware_inside_and_outside(
    log_stream: io.StringIO,
) -> None:
    app = make_app(middleware_outermost=False)

    class Inner(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            get_logger("inner").info("inner_mw")
            resp = await call_next(request)
            resp.headers["X-Extra"] = "1"
            return resp

    app.add_middleware(Inner)  # Inner wraps app
    app.add_middleware(RequestIdMiddleware)  # outermost of the two
    async with client(app) as c:
        r = await c.get("/ok", headers={"X-Request-ID": "order-test-123"})
        r500 = await c.get("/boom", headers={"X-Request-ID": "order-test-456"})
    assert r.headers["x-request-id"] == "order-test-123"
    inner = [x for x in log_lines(log_stream) if x["event"] in ("inner_mw", "handler")]
    assert all(x["request_id"] == "order-test-123" for x in inner[:2])
    assert_problem(r500, 500)


async def test_request_id_innermost_documented_behaviour(
    log_stream: io.StringIO,
) -> None:
    """RequestIdMiddleware added FIRST (innermost): outer middleware log lines have no id."""
    app = make_app(middleware_outermost=True)

    class Outer(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            get_logger("outer").info("outer_mw")
            return await call_next(request)

    app.add_middleware(Outer)
    async with client(app) as c:
        await c.get("/ok", headers={"X-Request-ID": "order-test-789"})
    outer = [x for x in log_lines(log_stream) if x["event"] == "outer_mw"]
    assert outer and "request_id" not in outer[0]


async def test_outer_bound_contextvars_survive_request_id_middleware(
    log_stream: io.StringIO,
) -> None:
    """Fixed QA-S1T03-005: context bound by an outer layer is kept and restored."""
    app = make_app(middleware_outermost=False)

    class Outer:
        def __init__(self, inner):
            self.inner = inner

        async def __call__(self, scope, receive, send):
            structlog.contextvars.bind_contextvars(client_ip="198.51.100.7")
            await self.inner(scope, receive, send)

    wrapped = Outer(RequestIdMiddleware(app))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=wrapped), base_url="http://t"
    ) as c:
        await c.get("/ok")
    h = next(x for x in log_lines(log_stream) if x["event"] == "handler")
    assert h["client_ip"] == "198.51.100.7"
    assert "request_id" in h


async def test_websocket_scope_passes_through() -> None:
    seen = []

    async def inner(scope, receive, send):
        seen.append(scope["type"])

    await RequestIdMiddleware(inner)({"type": "websocket", "headers": []}, None, None)
    await RequestIdMiddleware(inner)({"type": "lifespan"}, None, None)
    assert seen == ["websocket", "lifespan"]


async def test_unhandled_error_message_with_newline_does_not_forge_log(
    app: FastAPI, log_stream: io.StringIO
) -> None:
    async with client(app) as c:
        await c.get("/boom", headers={"X-Request-ID": "forge-test-123"})
    for line in log_stream.getvalue().splitlines():
        json.loads(line)
