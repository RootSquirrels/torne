"""The catalogue schemas: the manifest and the projections it carries.

The manifest is **derived**, never edited. These schemas describe its shape as
it is served, so that the OpenAPI document and the frontend contract agree on
one definition rather than two.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .asset import Asset
from .common import Ref, StatusEntry
from .mission import Mission
from .model import Model
from .result import Results
from .source import Source

__all__ = [
    "CountryDetail",
    "CountryDomain",
    "CountrySummary",
    "CoverageEntry",
    "Domain",
    "Manifest",
    "MarketIntelligence",
    "PlannedFeature",
    "Region",
    "SurfaceProduct",
]


class Domain(BaseModel):
    """A modality of observation of the physical world."""

    domain_id: str = Field(description="The domain's identifier.")
    title: str = Field(description="The domain's name.")
    semantic_layer: str = Field(
        description="The package that reads this modality into observations."
    )


class CountryDomain(BaseModel):
    """One domain's status in one country, earned by that country's missions."""

    domain_id: str = Field(description="The domain's identifier.")
    title: str = Field(description="The domain's name.")
    status: str | None = Field(
        default=None,
        description=(
            "The highest status this country's missions reached in the domain. Null when no mission "
            "of this country touched it. Region-wide coverage never colours a country."
        ),
    )
    status_rank: int = Field(
        description="The rank of that status, from 1 upwards. Zero when there is none."
    )
    status_from: list[str] = Field(description="The missions that earned the status.")
    mission_ids: list[str] = Field(description="Every mission of this country in the domain.")
    source_ids: list[str] = Field(description="The sources those missions read.")
    model_keys: list[str] = Field(description="The models and methods those missions ran.")
    asset_ids: list[str] = Field(description="The physical assets of this country in the domain.")


class CountrySummary(BaseModel):
    """What one country holds, domain by domain."""

    country: str = Field(description="ISO 3166-1 alpha-2 code of the country.")
    domains: list[CountryDomain] = Field(description="Each domain's status in the country.")
    asset_ids: list[str] = Field(description="The physical assets of the country.")


class Region(BaseModel):
    """A region-wide scope, and the missions that covered it."""

    region: str = Field(description="The region's name.")
    domain_ids: list[str] = Field(description="The domains the region-wide missions touched.")
    status: str = Field(description="The highest status the region's missions reached.")
    mission_ids: list[str] = Field(description="The region's missions.")


class CountryDetail(CountrySummary):
    """A country, with the region-wide coverage that surrounds it."""

    covered: bool = Field(
        description="Whether any mission of this country reached a status. False for a country no mission touched."
    )
    regions: list[Region] = Field(
        description="The region-wide scopes, which are not national statuses."
    )


class CoverageEntry(BaseModel):
    """A period that observations or a product cover."""

    subject_kind: Literal["asset", "surface_product"] = Field(
        description="Whether the period belongs to a physical asset or to a surface product."
    )
    subject_id: str = Field(description="The asset or product collection the period belongs to.")
    title: str = Field(description="The name of the subject.")
    domain_id: str = Field(description="The observation modality the subject belongs to.")
    country: str | None = Field(
        default=None, description="The country, for an asset. Null for a region-wide product."
    )
    start: str | None = Field(
        default=None,
        description=(
            "The first day of the period, as an ISO date, a year, or an ISO instant. "
            "Null when the start is not established."
        ),
    )
    end: str | None = Field(
        default=None,
        description="The last day of the period. Null when the end is not established.",
    )
    open: bool = Field(description="Whether the period is still open, that is, not finished.")
    refs: list[Ref] = Field(description="The evidence for the period.")


class SurfaceProduct(BaseModel):
    """A surface observation product, as the registry declares it."""

    collection: str = Field(description="The collection identifier.")
    title: str = Field(description="The product's name.")
    quantity: str = Field(description="The quantity the product carries.")
    nature: str = Field(description="The nature of the observation.")
    resolution_m: float | None = Field(
        default=None,
        description="The spatial resolution in metres. Null when it is not established.",
    )
    coverage_start: str | None = Field(
        default=None, description="The first day covered, as an ISO instant."
    )
    coverage_end: str | None = Field(
        default=None, description="The last day covered, as an ISO instant."
    )
    open_coverage: bool = Field(description="Whether the coverage is still open.")
    dependence: str = Field(description="The declared meteorological dependence of the product.")
    unit: str | None = Field(
        default=None, description="The unit of the quantity. Null when it is not established."
    )
    unit_established: bool = Field(
        description="Whether the unit is established, as opposed to declared by the producer only."
    )
    publication_delay: str | None = Field(
        default=None, description="The declared publication delay. Null when it is not established."
    )
    instruments: list[str] = Field(description="The instruments the product is built on.")
    refs: list[Ref] = Field(description="The evidence for the registry entry.")


class PlannedFeature(BaseModel):
    """A feature that is planned, and what it would need."""

    feature: str = Field(description="The planned feature.")
    needs: str = Field(description="What the feature would need before it could exist.")


class MarketIntelligence(BaseModel):
    """The state of the market branch of the platform."""

    open: bool = Field(description="Whether the market branch is open. It is not, today.")
    reason: str = Field(description="Why it is closed, or why it is open.")


class Manifest(BaseModel):
    """The whole manifest: one JSON projection of what TORNE can show.

    It is derived from the catalogue, from the surface-product registry and
    from the code itself. Building it computes nothing scientific and calls no
    provider.
    """

    manifest_version: str = Field(description="The version of the manifest's shape.")
    torne_version: str = Field(description="The version of the TORNE package.")
    repository_url: str = Field(description="The repository the references link to.")
    statuses: list[StatusEntry] = Field(
        description="The closed vocabulary of what a mission produced."
    )
    domains: list[Domain] = Field(description="The observation modalities.")
    countries: list[CountrySummary] = Field(description="What each country holds.")
    regions: list[Region] = Field(description="The region-wide scopes.")
    missions: list[Mission] = Field(description="The missions and what they established.")
    assets: list[Asset] = Field(description="The physical assets the missions touched.")
    coverage: list[CoverageEntry] = Field(
        description="The periods observations and products cover."
    )
    sources: list[Source] = Field(description="The sources, and their established behaviour.")
    models: list[Model] = Field(description="The models and methods, and where they ran.")
    surface_products: list[SurfaceProduct] = Field(description="The surface observation products.")
    results: Results = Field(description="What is published, and what was only run.")
    planned: list[PlannedFeature] = Field(description="What is planned and not available.")
    market_intelligence: MarketIntelligence = Field(description="The state of the market branch.")
