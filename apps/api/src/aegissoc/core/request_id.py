"""Request ID middleware (AC-PLAT-10).

A client-supplied ``X-Request-ID`` is used only if it matches ``^[A-Za-z0-9-]{8,64}$``;
anything else is replaced by a fresh UUIDv7 and never echoed. The id is stored on
``request.state.request_id``, bound to the structlog context for the duration of the
request (restoring any outer binding afterwards), and set on the response, replacing any
header a handler set itself.

Pure ASGI on purpose: no ``BaseHTTPMiddleware``, so context variables and exceptions
behave predictably.
"""

import re

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aegissoc.core.ids import new_id

HEADER_NAME = b"x-request-id"
_VALID = re.compile(r"[A-Za-z0-9-]{8,64}")


def is_valid_request_id(value: str) -> bool:
    """True if ``value`` is an acceptable client request id.

    ``fullmatch`` on purpose: ``$`` would accept a trailing newline.
    """
    return _VALID.fullmatch(value) is not None


def _incoming_id(scope: Scope) -> str | None:
    for name, raw in scope.get("headers", []):
        if name == HEADER_NAME:
            candidate: str = raw.decode("latin-1")
            return candidate if is_valid_request_id(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_id(scope) or str(new_id())
        scope.setdefault("state", {})["request_id"] = request_id
        # Tokens restore whatever an outer layer had bound; only our own binding is undone.
        tokens = structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != HEADER_NAME
                ]
                headers.append((HEADER_NAME, request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            structlog.contextvars.reset_contextvars(**tokens)
