"""The mission routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from ...services import catalogue_service as service
from ...services.catalogue_service import UnknownStatus
from ..caching import CatalogueRouter
from ..errors import not_found, unprocessable
from ..schemas.mission import Mission

__all__ = ["router"]

router = CatalogueRouter(tags=["missions"])


@router.get(
    "/missions",
    response_model=list[Mission],
    summary="The missions, and what each established.",
)
def missions(
    country: Annotated[str | None, Query(description="ISO 3166-1 alpha-2 code.")] = None,
    domain: Annotated[str | None, Query(description="The observation modality.")] = None,
    min_status: Annotated[
        str | None,
        Query(
            description=(
                "The lowest status to include. One of qualification, exploration, demonstration, knowledge."
            )
        ),
    ] = None,
) -> list[dict]:
    """The missions, filtered by country, domain and minimum status.

    The status vocabulary is closed: a name outside it is a 422, not an
    empty result.
    """
    try:
        return service.missions(country=country, domain=domain, min_status=min_status)
    except UnknownStatus as error:
        raise unprocessable(str(error)) from error


@router.get(
    "/missions/{mission_id}",
    response_model=Mission,
    summary="One mission.",
)
def mission(mission_id: str) -> dict:
    """One mission, with the evidence behind its status."""
    found = service.mission(mission_id)
    if found is None:
        raise not_found("mission", mission_id)
    return found
