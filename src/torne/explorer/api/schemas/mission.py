"""The mission schema.

A mission is what the repository asked of the world and what it established.
Its status says what it **produced**, not what it is about.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Fact, Ref

__all__ = ["Mission"]


class Mission(BaseModel):
    """A mission, the status it reached, and what supports that status."""

    mission_id: str = Field(description="The mission's identifier, stable across versions.")
    title: str = Field(description="A one-line statement of what the mission did.")
    status: str = Field(
        description=(
            "What the mission produced: qualification, exploration, demonstration or knowledge. "
            "A knowledge status requires a persisted record."
        )
    )
    status_rank: int = Field(
        description="The rank of the status in the closed vocabulary, from 1 upwards. Ordered, comparable."
    )
    status_basis: list[Ref] = Field(
        description="The evidence supporting the status. Never empty: a status without evidence cannot be built."
    )
    domain_ids: list[str] = Field(description="The observation modalities the mission touched.")
    countries: list[str] = Field(
        description="ISO 3166-1 alpha-2 codes of the countries the mission concerned. Empty for a region-wide mission."
    )
    region: str | None = Field(
        default=None, description="The region-wide scope, when the mission was not national."
    )
    question: str = Field(description="The scientific question the mission addressed.")
    produced: list[Fact] = Field(description="What the mission established.")
    not_established: list[Fact] = Field(
        description="What the mission explicitly did not establish."
    )
    asset_ids: list[str] = Field(description="The physical assets the mission touched.")
    source_ids: list[str] = Field(description="The sources the mission read.")
    model_keys: list[str] = Field(description="The models and methods the mission ran.")
    knowledge_records: list[Ref] = Field(
        description="The persisted knowledge records. Empty today: no record format exists on disk yet."
    )
