"""The source schema.

A source is a producer or holder of information. The explorer shows how each
source behaves, and what it is qualified to provide.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Fact, Ref

__all__ = ["Source"]


class Source(BaseModel):
    """A source, the adapter that reads it, and its established behaviour."""

    source_id: str = Field(description="The source's identifier, as the adapter declares it.")
    title: str = Field(description="The name of the source.")
    adapter: str = Field(description="The adapter class that reads the source.")
    adapter_ref: Ref = Field(description="The importable name of the adapter.")
    domain_id: str = Field(description="The observation modality the source feeds.")
    publication_class: str | None = Field(
        default=None,
        description=(
            "The publication class of the source: p, b, c or n. Null when it is not established."
        ),
    )
    qualified_in: Ref = Field(description="Where the source is qualified.")
    facts: list[Fact] = Field(description="The behaviour of the source, as established.")
    mission_ids: list[str] = Field(description="The missions that read the source.")
