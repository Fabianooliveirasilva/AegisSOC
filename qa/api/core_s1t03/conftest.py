"""Independent QA harness for S1-T03 (core). Black-box: only the public core API is used."""

import io
import json
from collections.abc import Iterator

import pytest
import structlog


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    from aegissoc.core.logging import configure_logging

    stream = io.StringIO()
    configure_logging("DEBUG", stream)
    yield stream
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def log_lines(stream: io.StringIO) -> list[dict[str, object]]:
    text = stream.getvalue()
    assert text == "" or text.endswith("\n")
    out = []
    for line in text.splitlines():
        out.append(json.loads(line))  # every physical line must be a JSON object
    return out
