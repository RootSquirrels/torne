"""The result routes.

The API exposes what the repository has **published**. A run that produced a
product in memory is listed separately, and never as a published result.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...services import catalogue_service as service
from ..schemas.result import Results

__all__ = ["router"]

router = APIRouter(tags=["results"])


@router.get(
    "/results",
    response_model=Results,
    summary="What is published, and what was only run.",
)
def results() -> dict:
    """The published knowledge products, and the runs that were never persisted."""
    return service.results()
