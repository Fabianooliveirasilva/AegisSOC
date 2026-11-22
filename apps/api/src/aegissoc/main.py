"""Application factory. Routers are wired here by later tasks (S1-T05 onward)."""

from fastapi import FastAPI

from aegissoc import __version__


def create_app() -> FastAPI:
    """Build the FastAPI application.

    OpenAPI/Swagger UIs are disabled: the contract is exported with
    `make openapi` (S1-T10) and not served by the application.
    """
    return FastAPI(
        title="AegisSOC",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
