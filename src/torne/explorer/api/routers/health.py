"""The health route.

It answers whether the application is up, and which version of the repository
it is serving. It reads the manifest, so it cannot answer while the manifest
cannot be built.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...services import catalogue_service as service
from ..schemas.common import Health

__all__ = ["router"]

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=Health,
    summary="Is the explorer up, and which version is it serving?",
)
def health() -> Health:
    """The health of the application and the version it serves."""
    manifest = service.manifest()
    return Health(
        status="ok",
        torne_version=manifest["torne_version"],
        manifest_version=manifest["manifest_version"],
    )
