"""The model schema.

A model is an implementation with an identity read from the code. Its runs say
on which real data it was executed; an empty list means implemented and tested,
never executed on real data.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Fact, Ref

__all__ = ["Model"]


class Model(BaseModel):
    """A model or method implemented in the repository, and where it ran."""

    key: str = Field(description="The model's stable key.")
    title: str = Field(description="What the model does.")
    kind: str = Field(
        description="Whether the model produces a result (model) or tests a series (diagnostic)."
    )
    domain_ids: list[str] = Field(description="The observation modalities the model applies to.")
    identity: str = Field(description="The identity of the implementation, read from the code.")
    identity_ref: Ref = Field(description="The importable name of the implementation.")
    version: str | None = Field(
        default=None, description="The version of the implementation, when the module exposes one."
    )
    version_ref: Ref | None = Field(
        default=None, description="The importable name holding the version, when there is one."
    )
    executed_on_real_data: bool = Field(
        description="Whether the model was executed on real data, as recorded by evidence."
    )
    runs: list[Fact] = Field(description="The recorded runs, with their evidence.")
    mission_ids: list[str] = Field(description="The missions that ran the model.")
