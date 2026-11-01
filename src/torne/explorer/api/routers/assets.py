"""The asset routes: the physical objects the missions touched."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from ...services import catalogue_service as service
from ..caching import CatalogueRouter
from ..errors import not_found
from ..schemas.asset import Asset, AssetKind

__all__ = ["router"]

router = CatalogueRouter(tags=["assets"])


@router.get(
    "/assets",
    response_model=list[Asset],
    summary="The physical assets the missions touched.",
)
def assets(
    country: Annotated[str | None, Query(description="ISO 3166-1 alpha-2 code.")] = None,
    domain: Annotated[str | None, Query(description="The observation modality.")] = None,
    kind: Annotated[AssetKind | None, Query(description="The kind of physical asset.")] = None,
) -> list[dict]:
    """The assets, filtered by country, domain and kind."""
    return service.assets(country=country, domain=domain, kind=kind)


@router.get(
    "/assets/{asset_id}",
    response_model=Asset,
    summary="One physical asset.",
)
def asset(asset_id: str) -> dict:
    """One asset: where it is, and what was measured there."""
    found = service.asset(asset_id)
    if found is None:
        raise not_found("asset", asset_id)
    return found
