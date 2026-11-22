"""Structured JSON logging with redaction of sensitive keys (SR-18).

One JSON object per line. Untrusted values are JSON-encoded by the renderer, so a newline
in a value cannot forge another log line. Keys that look sensitive are dropped, at any
nesting depth, before anything is rendered.

Limit: redaction works on keys, not on text. Never put a secret into the event message.
"""

import logging
import re
import sys
from collections.abc import Mapping
from typing import Any, TextIO

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, WrappedLogger

_SENSITIVE_KEY = re.compile(
    r"password|secret|token|session|authorization|cookie|api[-_]?key",
    re.IGNORECASE,
)
_MAX_DEPTH = 8
_TRUNCATED = "[truncated]"


def _clean(value: Any, depth: int) -> Any:
    if isinstance(value, Mapping):
        if depth >= _MAX_DEPTH:
            return _TRUNCATED
        return {
            key: _clean(item, depth + 1)
            for key, item in value.items()
            if not _SENSITIVE_KEY.search(str(key))
        }
    if isinstance(value, list | tuple):
        if depth >= _MAX_DEPTH:
            return _TRUNCATED
        return [_clean(item, depth + 1) for item in value]
    return value


def redact_sensitive(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """structlog processor: drop keys matching the sensitive-key pattern (SR-18)."""
    cleaned: EventDict = _clean(event_dict, 0)
    return cleaned


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
            redact_sensitive,
            structlog.processors.format_exc_info,
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
