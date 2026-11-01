"""The composition root: where the application is assembled.

`create_app()` wires the routers to the read service, installs the error
handlers, and serves the compiled frontend. Nothing else assembles the
application, so the shape of the API is readable in one place.
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from ..services import catalogue_service as service
from .config import DEFAULT_SETTINGS, ExplorerSettings
from .errors import install_error_handlers
from .routers import assets, catalogue, health, missions, models, results, sources
from .static import mount_frontend

__all__ = ["app", "create_app", "main"]

_ROUTERS = (
    health.router,
    catalogue.router,
    missions.router,
    assets.router,
    sources.router,
    models.router,
    results.router,
)


def create_app(settings: ExplorerSettings | None = None) -> FastAPI:
    """The explorer application: the API under `/api/v1`, the frontend at `/`.

    The API is served under two prefixes during the transition:

    - `/api/v1` is the canonical one, and the only one the OpenAPI document
      describes;
    - `/api` is kept for the consumers written against the previous version.
      It answers the same questions and marks its answers as deprecated.

    The application exposes reads only: it has no `POST`, `PUT` or `DELETE`.
    """
    settings = settings or DEFAULT_SETTINGS

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        # The manifest is built once, when the first request needs it, and
        # held in memory afterwards. Building it computes nothing scientific.
        service.manifest()
        yield

    application = FastAPI(
        title=settings.title,
        version=service.manifest()["manifest_version"],
        description=settings.description,
        lifespan=lifespan,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )

    install_error_handlers(application)

    for router in _ROUTERS:
        application.include_router(router, prefix=settings.api_prefix)
    for router in _ROUTERS:
        application.include_router(
            router,
            prefix=settings.legacy_api_prefix,
            include_in_schema=False,
        )

    _install_deprecation_marker(application, settings)

    mount_frontend(
        application,
        settings.static_dir,
        api_prefixes=(settings.api_prefix, settings.legacy_api_prefix),
    )
    return application


def _install_deprecation_marker(application: FastAPI, settings: ExplorerSettings) -> None:
    """Mark the answers of the legacy prefix as deprecated.

    The legacy routes keep working, but they say what replaces them. A client
    that follows the `Link` header has migrated itself.
    """
    legacy = settings.legacy_api_prefix
    canonical = settings.api_prefix

    @application.middleware("http")
    async def _mark_legacy(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        path = request.url.path
        if path.startswith(f"{legacy}/") and not path.startswith(f"{canonical}/"):
            successor = f"{canonical}{path[len(legacy) :]}"
            response.headers["Deprecation"] = "true"
            response.headers["Link"] = f'<{successor}>; rel="successor-version"'
        return response


app = create_app()


def main(argv: list[str] | None = None) -> None:
    """Serve the explorer locally."""
    import uvicorn

    parser = argparse.ArgumentParser(prog="torne-explorer", description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    uvicorn.run(app, host=args.host, port=args.port)
