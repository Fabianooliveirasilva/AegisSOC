"""core.errors: RFC 9457 problem details for every error (AC-PLAT-10, TC-PLAT-08, SR-18)."""

import io
import json
import uuid
from typing import Literal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from aegissoc.core.errors import (
    BadRequest,
    Conflict,
    DomainError,
    Forbidden,
    InvalidTransition,
    NotFound,
    ProblemDetail,
    VersionMismatch,
    install_error_handlers,
)
from aegissoc.core.logging import configure_logging
from aegissoc.core.request_id import RequestIdMiddleware

PROBLEM = "application/problem+json"
BASE = "https://aegissoc.local/problems/"


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["low", "high"]
    count: int


class WrongShape(BaseModel):
    must_be_int: int


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    @app.get("/http/{status}")
    async def raise_http(status: int) -> None:
        raise HTTPException(status_code=status, detail="because", headers={"Retry-After": "7"})

    @app.post("/validate")
    async def validate(payload: Payload) -> Payload:
        return payload

    @app.get("/domain/{kind}")
    async def domain(kind: str) -> None:
        errors: dict[str, DomainError] = {
            "bad": BadRequest("bad cursor"),
            "forbidden": Forbidden("nope"),
            "missing": NotFound("incident not found"),
            "conflict": Conflict("duplicate name"),
            "transition": InvalidTransition("closed -> new"),
            "version": VersionMismatch("stale"),
            "default": NotFound(),
        }
        raise errors[kind]

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("internal-detail-xyz: /etc/passwd password=hunter2")

    @app.get("/bad-response", response_model=WrongShape)
    async def bad_response() -> dict[str, str]:
        return {"must_be_int": "not an int"}

    return app


def _client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    ("status", "slug"),
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
        (503, "unavailable"),
        (500, "internal-error"),
    ],
)
def test_http_exceptions_become_problem_details(status: int, slug: str) -> None:
    response = _client().get(f"/http/{status}")
    body = response.json()
    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM)
    assert body["type"] == BASE + slug
    assert body["status"] == status
    assert body["detail"] == "because"
    assert body["instance"] == f"/http/{status}"
    assert body["title"]


@pytest.mark.req("AC-PLAT-10")
def test_http_exception_headers_are_preserved() -> None:
    assert _client().get("/http/429").headers["retry-after"] == "7"


@pytest.mark.req("AC-PLAT-10")
def test_unknown_route_is_a_problem_detail_404() -> None:
    response = _client().get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)
    assert response.json()["type"] == BASE + "not-found"


@pytest.mark.req("AC-PLAT-10")
def test_other_client_errors_fall_back_to_bad_request() -> None:
    response = _client().post("/http/418")  # 405: GET-only route
    assert response.status_code == 405
    assert response.json()["type"] == BASE + "bad-request"


@pytest.mark.req("AC-PLAT-10")
def test_every_problem_carries_request_id_matching_the_header() -> None:
    response = _client().get("/nope", headers={"X-Request-ID": "client-id-12345"})
    assert response.json()["request_id"] == "client-id-12345"
    assert response.headers["x-request-id"] == "client-id-12345"


@pytest.mark.req("AC-PLAT-10")
def test_problem_has_no_null_errors_key_when_there_are_no_field_errors() -> None:
    assert "errors" not in _client().get("/nope").json()


@pytest.mark.req("AC-PLAT-10")
def test_instance_is_the_path_without_the_query_string() -> None:
    response = _client().get("/nope?token=abc123&x=1")
    assert response.json()["instance"] == "/nope"
    assert "abc123" not in response.text


@pytest.mark.req("AC-PLAT-10")
def test_validation_errors_are_422_with_field_errors() -> None:
    response = _client().post("/validate", json={"severity": "urgent", "count": "x"})
    body = response.json()
    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM)
    assert body["type"] == BASE + "validation-error"
    assert body["detail"] == "2 fields are invalid"
    assert {tuple(e["loc"]) for e in body["errors"]} == {("body", "severity"), ("body", "count")}
    assert all(set(e) == {"loc", "msg", "type"} for e in body["errors"])


@pytest.mark.req("SR-18")
def test_validation_errors_never_echo_submitted_values() -> None:
    response = _client().post(
        "/validate", json={"severity": "hunter2-secret-value", "count": 1, "password": "p4ss"}
    )
    assert response.status_code == 422
    assert "hunter2-secret-value" not in response.text
    assert "p4ss" not in response.text


@pytest.mark.req("AC-PLAT-10")
def test_single_invalid_field_uses_singular_detail() -> None:
    response = _client().post("/validate", json={"severity": "low", "count": "x"})
    assert response.json()["detail"] == "1 field is invalid"


@pytest.mark.req("AC-PLAT-10")
def test_malformed_json_is_400_bad_request() -> None:
    response = _client().post(
        "/validate", content='{"severity": ', headers={"Content-Type": "application/json"}
    )
    body = response.json()
    assert response.status_code == 400
    assert body["type"] == BASE + "bad-request"
    assert "errors" not in body


@pytest.mark.req("AC-PLAT-10")
@pytest.mark.parametrize(
    ("kind", "status", "slug", "detail"),
    [
        ("bad", 400, "bad-request", "bad cursor"),
        ("forbidden", 403, "forbidden", "nope"),
        ("missing", 404, "not-found", "incident not found"),
        ("conflict", 409, "conflict", "duplicate name"),
        ("transition", 409, "invalid-transition", "closed -> new"),
        ("version", 409, "version-mismatch", "stale"),
    ],
)
def test_domain_errors_map_to_their_problem_types(
    kind: str, status: int, slug: str, detail: str
) -> None:
    response = _client().get(f"/domain/{kind}")
    body = response.json()
    assert response.status_code == status
    assert body["type"] == BASE + slug
    assert body["detail"] == detail


@pytest.mark.req("AC-PLAT-10")
def test_domain_error_without_detail_uses_its_title() -> None:
    body = _client().get("/domain/default").json()
    assert body["detail"] == body["title"]


@pytest.mark.req("AC-PLAT-10")
def test_domain_errors_are_exceptions_with_a_message() -> None:
    assert str(NotFound("x")) == "x"
    assert isinstance(NotFound(), DomainError)


@pytest.mark.req("AC-PLAT-10")
def test_unhandled_exception_is_a_500_problem_without_internals() -> None:
    response = _client().get("/boom", headers={"X-Request-ID": "client-id-12345"})
    body = response.json()
    assert response.status_code == 500
    assert response.headers["content-type"].startswith(PROBLEM)
    assert body["type"] == BASE + "internal-error"
    assert body["request_id"] == "client-id-12345"
    assert response.headers["x-request-id"] == "client-id-12345"
    for forbidden in ("Traceback", "RuntimeError", "/etc/passwd", "hunter2", "internal-detail-xyz"):
        assert forbidden not in response.text


@pytest.mark.req("AC-PLAT-10")
def test_response_validation_failure_is_also_a_clean_500() -> None:
    response = _client().get("/bad-response")
    assert response.status_code == 500
    assert response.json()["type"] == BASE + "internal-error"
    assert "must_be_int" not in response.text


@pytest.mark.req("SR-18")
def test_500_is_logged_with_request_id_and_type_but_not_message_or_traceback() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    _client().get("/boom", headers={"X-Request-ID": "client-id-12345"})
    (record,) = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert record["request_id"] == "client-id-12345"
    assert record["error_type"] == "RuntimeError"
    assert record["level"] == "error"
    assert "hunter2" not in stream.getvalue()
    assert "Traceback" not in stream.getvalue()


@pytest.mark.req("AC-PLAT-10")
def test_problem_detail_model_forbids_unknown_fields() -> None:
    fields = {
        "type": BASE + "x",
        "title": "t",
        "status": 400,
        "detail": "d",
        "instance": "/",
        "request_id": str(uuid.uuid4()),
    }
    ProblemDetail(**fields)
    with pytest.raises(ValueError, match="extra"):
        ProblemDetail(**fields, stack_trace="no")  # type: ignore[call-arg]
