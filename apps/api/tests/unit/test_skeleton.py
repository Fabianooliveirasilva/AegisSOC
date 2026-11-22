"""Skeleton smoke tests (S1-T02). Real behaviour is tested from S1-T03 onward."""

import pytest
from fastapi import FastAPI

from aegissoc import __version__
from aegissoc.cli import main
from aegissoc.main import create_app


@pytest.mark.req("AC-QA-07")
def test_create_app_returns_fastapi_without_public_docs() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


@pytest.mark.req("AC-QA-07")
def test_create_app_returns_independent_instances() -> None:
    assert create_app() is not create_app()


@pytest.mark.req("AC-QA-07")
def test_cli_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"aegissoc {__version__}"


@pytest.mark.req("AC-QA-07")
def test_cli_without_arguments_returns_zero() -> None:
    assert main([]) == 0
