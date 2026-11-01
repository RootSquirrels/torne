"""The asset schema.

An asset is a physical object a mission actually touched: a station, a
catchment, a raster coverage. The three kinds are never merged into one type.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import Fact, Ref

__all__ = ["Asset", "AssetKind"]

AssetKind = Literal["station", "catchment", "raster_coverage"]
"""The kind of physical asset."""


class Asset(BaseModel):
    """A physical object, where it is, and what was measured there."""

    asset_id: str = Field(description="The asset's identifier, as the source names it.")
    kind: AssetKind = Field(description="The kind of physical asset.")
    name: str = Field(description="The name of the asset.")
    country: str | None = Field(
        default=None, description="ISO 3166-1 alpha-2 code of the country the asset is in."
    )
    domain_id: str = Field(description="The observation modality the asset belongs to.")
    source_id: str = Field(description="The source the asset was read from.")
    point: tuple[float, float] | None = Field(
        default=None,
        description="The position of the asset, as (longitude, latitude) in the source's own reference frame.",
    )
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description=(
            "The extent of the asset, as (west, south, east, north) in the source's own reference frame."
        ),
    )
    location_ref: Ref = Field(description="The evidence for where the asset is.")
    facts: list[Fact] = Field(description="What was measured at the asset.")
    mission_ids: list[str] = Field(description="The missions that touched the asset.")
