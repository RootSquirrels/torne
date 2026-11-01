"""The catalogue routes: the manifest and the projections it carries.

These are the routes that describe the *shape* of what the repository holds:
its domains, its countries, its regions, the periods it covers, and the
surface products it knows.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...services import catalogue_service as service
from ..errors import not_found
from ..schemas.catalogue import (
    CountryDetail,
    CountryDomain,
    CountrySummary,
    CoverageEntry,
    Domain,
    Manifest,
    Region,
    SurfaceProduct,
)

__all__ = ["router"]

router = APIRouter(tags=["catalogue"])


@router.get(
    "/manifest",
    response_model=Manifest,
    summary="The whole manifest — one JSON projection of what TORNE can show.",
)
def manifest() -> dict:
    """The manifest, derived from the catalogue and from the code itself."""
    return service.manifest()


@router.get(
    "/domains",
    response_model=list[Domain],
    summary="The observation modalities of the physical world.",
)
def domains() -> list[dict]:
    """The domains: hydrology, atmosphere, earth observation."""
    return service.domains()


@router.get(
    "/countries",
    response_model=list[CountrySummary],
    summary="What each country holds, domain by domain.",
)
def countries() -> list[dict]:
    """The countries that hold a mission."""
    return service.countries()


@router.get(
    "/countries/{code}",
    response_model=CountryDetail,
    summary="One country, with the region-wide coverage that surrounds it.",
)
def country(code: str) -> dict:
    """One country.

    A country no mission touched is not an error: it is a country with no
    status, and the API says so.
    """
    return service.country_detail(code)


@router.get(
    "/countries/{code}/domains/{domain_id}",
    response_model=CountryDomain,
    summary="One domain's status in one country.",
)
def country_domain(code: str, domain_id: str) -> dict:
    """The status one domain reached in one country."""
    found = service.country_domain(code, domain_id)
    if found is None:
        raise not_found("domain", domain_id)
    return found


@router.get(
    "/regions",
    response_model=list[Region],
    summary="The region-wide scopes, which are not national statuses.",
)
def regions() -> list[dict]:
    """The regions covered by region-wide missions."""
    return service.regions()


@router.get(
    "/coverage",
    response_model=list[CoverageEntry],
    summary="The periods observations and products cover.",
)
def coverage(
    domain: str | None = None,
    country: str | None = None,
) -> list[dict]:
    """The observation coverage: what period each asset or product covers."""
    return service.coverage(domain=domain, country=country)


@router.get(
    "/surface-products",
    response_model=list[SurfaceProduct],
    summary="The surface observation products, as the registry declares them.",
)
def surface_products(dependence: str | None = None) -> list[dict]:
    """The surface products, optionally filtered by their declared dependence."""
    return service.surface_products(dependence=dependence)
