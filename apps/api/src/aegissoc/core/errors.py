"""Error model: every 4xx/5xx is ``application/problem+json`` (RFC 9457, AC-PLAT-10).

- ``type`` slugs follow API_SPECIFICATION §1.3.
- Every problem carries ``request_id`` and the response carries ``X-Request-ID``.
- ``instance`` is the request path only (no query string, which may hold tokens).
- Validation problems list ``loc``, ``msg`` and ``type`` per field and never the submitted
  value (Pydantic's ``input``/``ctx`` are dropped), so secrets sent in a bad request are
  not reflected (SR-18).
- A 500 never includes a stack trace, exception message or class name. The server log gets
  the exception class and the request id, not the message.
"""

from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from aegissoc.core.ids import new_id
from aegissoc.core.logging import get_logger

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_BASE_URI = "https://aegissoc.local/problems/"

_log = get_logger("aegissoc.errors")

# status -> (slug, title); API_SPECIFICATION §1.3. 409 and 429 default to the first slug.
_STATUS_PROBLEMS: dict[int, tuple[str, str]] = {
    400: ("bad-request", "Bad request"),
    401: ("unauthenticated", "Authentication required"),
    403: ("forbidden", "Forbidden"),
    404: ("not-found", "Not found"),
    409: ("conflict", "Conflict"),
    413: ("payload-too-large", "Payload too large"),
    415: ("unsupported-media-type", "Unsupported media type"),
    422: ("validation-error", "Request validation failed"),
    429: ("rate-limited", "Too many requests"),
    500: ("internal-error", "Internal server error"),
    503: ("unavailable", "Service unavailable"),
}


class FieldError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loc: list[str | int]
    msg: str
    type: str


class ProblemDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
    errors: list[FieldError] | None = None


class DomainError(Exception):
    """Base class for errors raised by services and mapped to a problem type."""

    status_code: ClassVar[int] = 400
    slug: ClassVar[str] = "bad-request"
    title: ClassVar[str] = "Bad request"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.title
        super().__init__(self.detail)


class BadRequest(DomainError):
    status_code = 400
    slug = "bad-request"
    title = "Bad request"


class Forbidden(DomainError):
    status_code = 403
    slug = "forbidden"
    title = "Forbidden"


class NotFound(DomainError):
    status_code = 404
    slug = "not-found"
    title = "Not found"


class Conflict(DomainError):
    status_code = 409
    slug = "conflict"
    title = "Conflict"


class InvalidTransition(DomainError):
    status_code = 409
    slug = "invalid-transition"
    title = "Invalid state transition"


class VersionMismatch(DomainError):
    status_code = 409
    slug = "version-mismatch"
    title = "Version mismatch"


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    return existing if isinstance(existing, str) else str(new_id())


def _problem_response(
    request: Request,
    *,
    status: int,
    slug: str,
    title: str,
    detail: str,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    problem = ProblemDetail(
        type=PROBLEM_BASE_URI + slug,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        request_id=request_id,
        errors=errors,
    )
    response_headers = {**(headers or {}), "X-Request-ID": request_id}
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=response_headers,
    )


def _slug_and_title(status: int) -> tuple[str, str]:
    known = _STATUS_PROBLEMS.get(status)
    if known is not None:
        return known
    return _STATUS_PROBLEMS[400] if status < 500 else _STATUS_PROBLEMS[500]


_BODYLESS_STATUSES = frozenset({204, 205, 304})


async def _handle_http_exception(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    if exc.status_code in _BODYLESS_STATUSES or exc.status_code < 200:
        # These statuses must not carry a body, so no problem document.
        headers = {**(exc.headers or {}), "X-Request-ID": _request_id(request)}
        return Response(status_code=exc.status_code, headers=headers)
    slug, title = _slug_and_title(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail else title
    return _problem_response(
        request,
        status=exc.status_code,
        slug=slug,
        title=title,
        detail=detail,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, DomainError):
        raise exc
    return _problem_response(
        request,
        status=exc.status_code,
        slug=exc.slug,
        title=exc.title,
        detail=exc.detail,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    raw: list[dict[str, Any]] = [dict(e) for e in exc.errors()]
    if any(e.get("type") == "json_invalid" for e in raw):
        slug, title = _STATUS_PROBLEMS[400]
        return _problem_response(
            request, status=400, slug=slug, title=title, detail="Malformed JSON body"
        )
    errors = [
        FieldError(
            loc=[p if isinstance(p, int) else str(p) for p in e["loc"]],
            msg=str(e["msg"]),
            type=str(e["type"]),
        )
        for e in raw
    ]
    count = len(errors)
    detail = "1 field is invalid" if count == 1 else f"{count} fields are invalid"
    slug, title = _STATUS_PROBLEMS[422]
    return _problem_response(
        request, status=422, slug=slug, title=title, detail=detail, errors=errors
    )


async def _handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Class name and request id only: the message may contain data that must not be logged.
    # This handler runs outside RequestIdMiddleware (in ServerErrorMiddleware), after its log
    # context was cleared, so the request id is passed explicitly.
    _log.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        path=request.url.path,
        request_id=_request_id(request),
    )
    slug, title = _STATUS_PROBLEMS[500]
    return _problem_response(
        request,
        status=500,
        slug=slug,
        title=title,
        detail="An internal error occurred.",
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register the problem-details handlers on ``app``."""
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unhandled)
