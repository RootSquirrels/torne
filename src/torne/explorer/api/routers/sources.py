"""The source routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from ...services import catalogue_service as service
from ..caching import CatalogueRouter
from ..errors import not_found
from ..schemas.source import Source

__all__ = ["router"]

router = CatalogueRouter(tags=["sources"])


@router.get(
    "/sources",
    response_model=list[Source],
    summary="The sources, and their established behaviour.",
)
def sources(
    domain: Annotated[str | None, Query(description="The observation modality.")] = None,
) -> list[dict]:
    """The sources, optionally filtered by domain."""
    return service.sources(domain=domain)


@router.get(
    "/sources/{source_id}",
    response_model=Source,
    summary="One source.",
)
def source(source_id: str) -> dict:
    """One source: how it behaves, and where it is qualified."""
    found = service.source(source_id)
    if found is None:
        raise not_found("source", source_id)
    return found
