"""Schemas shared by every explorer response.

The HTTP schemas are the API's own contract. They are deliberately **not** the
scientific engine's internal contracts: the engine's classes stay inside the
scientific layers, and what crosses HTTP is described here, with its units and
its meaning documented field by field.

A field that is not known is `null`. It is never replaced by a zero, by an
empty string, or by a plausible default.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "ErrorBody",
    "ErrorResponse",
    "Fact",
    "Health",
    "Ref",
    "RefKind",
    "StatusEntry",
]

RefKind = Literal["mission", "document", "script", "implementation", "record"]
"""What a reference points at."""


class Ref(BaseModel):
    """A reference to the evidence behind a fact.

    Every fact, status and coverage period carries references. A reference
    that resolves to a repository file carries its URL; one that resolves to
    an importable name does not.
    """

    kind: RefKind = Field(description="What the reference points at.")
    target: str = Field(
        description=(
            "The reference itself: a mission identifier, a repository path "
            "optionally followed by ' §section', or a 'module:attribute' name."
        )
    )
    url: str | None = Field(
        default=None,
        description="Link to the referenced repository file, when the reference points at one.",
    )


class Fact(BaseModel):
    """A statement and the evidence it rests on."""

    text: str = Field(description="The statement, as the repository records it.")
    refs: list[Ref] = Field(
        description="The evidence. Never empty: a fact without a reference cannot be built."
    )


class StatusEntry(BaseModel):
    """One step of the closed, ordered vocabulary of what a mission produced."""

    status: str = Field(description="The status name, lower case.")
    rank: int = Field(description="The rank of the status in the vocabulary, from 1 upwards.")


class ErrorBody(BaseModel):
    """The structured part of an error response."""

    code: str = Field(description="A stable, machine-readable error code.")
    message: str = Field(description="A human-readable description of what went wrong.")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional context, when there is any."
    )


class ErrorResponse(BaseModel):
    """The body every error carries.

    `detail` keeps the shape FastAPI has always returned, so an existing
    consumer keeps working; `error` adds the structured description.
    """

    detail: str = Field(description="A human-readable description of what went wrong.")
    error: ErrorBody = Field(description="The structured description of the error.")


class Health(BaseModel):
    """Whether the application is up, and which version it serves."""

    status: str = Field(description="`ok` when the application can answer.")
    torne_version: str = Field(description="The version of the TORNE package.")
    manifest_version: str = Field(description="The version of the manifest's shape.")
