"""Structured JSON logging with redaction of sensitive keys (SR-18).

One JSON object per line. Untrusted values are JSON-encoded by the renderer, so a newline
in a value cannot forge another log line. Keys that look sensitive are dropped, at any
nesting depth, before anything is rendered. Key names are normalised first (NFKC, format
characters removed) so full-width letters or zero-width characters do not hide a key.

Exceptions are logged as the stack frames plus the exception *type*, never its message:
messages routinely carry submitted values (a Pydantic ``input_value`` for instance).

Limits, accepted and documented:
- redaction works on keys, not on text: never put a secret into the event message;
- look-alike characters from other scripts (a Cyrillic letter drawn like a Latin one) are not
  unified;
- the object walk is bounded (depth and number of nodes); the rest is replaced by
  ``[truncated]``;
- objects that are not dicts, sequences or sets are rendered with ``repr``.
"""

import logging
import re
import sys
import traceback
import unicodedata
from collections.abc import Mapping
from typing import Any, TextIO

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, WrappedLogger

_SENSITIVE_KEY = re.compile(
    r"password|passwd|pwd|secret|token|session|authorization|cookie|api[-_]?key"
    r"|private[-_]?key|credential|dsn|csrf",
    re.IGNORECASE,
)
_MAX_DEPTH = 8
_MAX_NODES = 2000
_TRUNCATED = "[truncated]"


def _is_sensitive(key: Any) -> bool:
    text = key.decode("latin-1") if isinstance(key, bytes) else str(key)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return _SENSITIVE_KEY.search(text) is not None


def _is_named_pair(item: Any) -> bool:
    """A ``(name, value)`` pair such as an ASGI header, with a text or bytes name."""
    return isinstance(item, tuple | list) and len(item) == 2 and isinstance(item[0], str | bytes)


class _Walk:
    """One bounded traversal: a shared node budget stops shared-reference blow-ups."""

    def __init__(self) -> None:
        self.nodes = 0

    def exhausted(self) -> bool:
        return self.nodes >= _MAX_NODES

    def clean(self, value: Any, depth: int) -> Any:
        self.nodes += 1
        if isinstance(value, Mapping):
            return self._mapping(value, depth)
        if isinstance(value, list | tuple | set | frozenset):
            return self._sequence(value, depth)
        return value

    def _mapping(self, value: Mapping[Any, Any], depth: int) -> Any:
        if depth >= _MAX_DEPTH:
            return _TRUNCATED
        cleaned: dict[Any, Any] = {}
        for key, item in value.items():
            if self.exhausted():
                cleaned[_TRUNCATED] = True
                break
            if _is_sensitive(key):
                continue
            cleaned[key] = self.clean(item, depth + 1)
        return cleaned

    def _sequence(self, value: Any, depth: int) -> Any:
        if depth >= _MAX_DEPTH:
            return _TRUNCATED
        cleaned: list[Any] = []
        for item in value:
            if self.exhausted():
                cleaned.append(_TRUNCATED)
                break
            if _is_named_pair(item) and _is_sensitive(item[0]):
                continue
            cleaned.append(self.clean(item, depth + 1))
        return cleaned


def redact_sensitive(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """structlog processor: drop keys matching the sensitive-key pattern (SR-18)."""
    cleaned: EventDict = _Walk().clean(event_dict, 0)
    return cleaned


def render_exception(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """structlog processor: replace ``exc_info`` by the frames and the exception type only."""
    exc_info = event_dict.pop("exc_info", None)
    if not exc_info:
        return event_dict
    if exc_info is True:
        exc_info = sys.exc_info()
    elif isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
    if not (isinstance(exc_info, tuple) and len(exc_info) == 3 and exc_info[0] is not None):
        return event_dict
    exc_type, _value, tb = exc_info
    lines: list[str] = []
    if tb is not None:
        lines.append("Traceback (most recent call last):\n")
        lines.extend(traceback.format_tb(tb))
    module = exc_type.__module__
    lines.append(
        exc_type.__qualname__ if module == "builtins" else f"{module}.{exc_type.__qualname__}"
    )
    event_dict["exception"] = "".join(lines)
    return event_dict


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configure structlog to emit JSON lines to ``stream`` (default: stdout)."""
    numeric = logging.getLevelNamesMapping().get(level.upper())
    if numeric is None:
        raise ValueError(f"unknown log level: {level!r}")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            render_exception,
            redact_sensitive,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        logger_factory=structlog.PrintLoggerFactory(file=stream or sys.stdout),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a lazy logger.

    The name is passed as an initial value, not via ``.bind()``: ``.bind()`` would resolve
    the logger immediately and freeze the configuration at import time, so a module-level
    logger would ignore a later ``configure_logging()`` (and skip redaction).
    """
    logger: FilteringBoundLogger = (
        structlog.get_logger(logger_name=name) if name else structlog.get_logger()
    )
    return logger
