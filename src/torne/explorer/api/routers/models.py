"""The model routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ...services import catalogue_service as service
from ..errors import not_found
from ..schemas.model import Model

__all__ = ["router"]

router = APIRouter(tags=["models"])


@router.get(
    "/models",
    response_model=list[Model],
    summary="The models and methods, and where they ran.",
)
def models(
    executed: Annotated[
        bool | None,
        Query(description="Whether the model was executed on real data, as recorded by evidence."),
    ] = None,
) -> list[dict]:
    """The models, optionally filtered by whether they ran on real data."""
    return service.models(executed=executed)


@router.get(
    "/models/{key}",
    response_model=Model,
    summary="One model or method.",
)
def model(key: str) -> dict:
    """One model: its identity, read from the code, and its recorded runs."""
    found = service.model(key)
    if found is None:
        raise not_found("model", key)
    return found
