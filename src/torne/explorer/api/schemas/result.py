"""The result schemas.

A result is only *published* when a record is persisted. No record format
exists on disk yet, so the published list is empty — and the API says so
rather than presenting runs in memory as published knowledge.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Fact, Ref

__all__ = ["PersistedResult", "Results", "RunNotPersisted"]


class PersistedResult(BaseModel):
    """A knowledge product backed by a persisted record."""

    mission_id: str = Field(description="The mission that produced the product.")
    records: list[Ref] = Field(description="The persisted records themselves.")


class RunNotPersisted(BaseModel):
    """A run that produced a product in memory only."""

    mission_id: str = Field(description="The mission that ran.")
    status: str = Field(description="The status the mission reached.")
    produced: list[Fact] = Field(description="What the run produced.")


class Results(BaseModel):
    """What the repository has published, and what it has only run."""

    persisted: list[PersistedResult] = Field(
        description="The published knowledge products. Empty today: no record is persisted."
    )
    runs_not_persisted: list[RunNotPersisted] = Field(
        description="The runs that produced a product in memory, and were never persisted."
    )
    gap: str | None = Field(
        default=None,
        description="Why the published list is empty, when it is. Null once a record is persisted.",
    )
