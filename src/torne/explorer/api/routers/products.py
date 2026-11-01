"""The published product routes.

The API exposes what the repository has **published**. A product that is
published on disk is served as it is — its identity, its lineage, its bounds,
its indicators and its states. A product that is not published is a `404`, and
never an empty series that looks like a measurement.
"""

from __future__ import annotations

from ....knowledge.store import RecordNotFound
from ...services import products_service as service
from ..caching import CatalogueRouter
from ..errors import not_found
from ..schemas.products import (
    ConfrontationRows,
    ProductDetail,
    ProductList,
    ProductStates,
)

__all__ = ["router"]

router = CatalogueRouter(tags=["products"])


@router.get(
    "/products",
    response_model=ProductList,
    summary="The knowledge products the repository has published.",
)
def products() -> dict:
    """The published products, with what each one is and where it holds."""
    return {"products": service.products()}


@router.get(
    "/products/{product_id}",
    response_model=ProductDetail,
    summary="One published product, in full.",
)
def product(product_id: str) -> dict:
    """One published product: its identity, its lineage, its bounds, its indicators."""
    try:
        return service.product(product_id)
    except RecordNotFound as error:
        raise not_found("product", product_id) from error


@router.get(
    "/products/{product_id}/states",
    response_model=ProductStates,
    summary="The states of one layer of a published product.",
)
def states(product_id: str, layer: str, entity: str | None = None) -> dict:
    """The states of a layer.

    Without an entity, the last published state of every entity of the layer
    is served — what a map draws. With one, the whole series of that entity
    is served — what a chart draws.
    """
    try:
        found = service.states(product_id, layer, entity)
    except RecordNotFound as error:
        raise not_found("product", product_id) from error
    if found is None:
        raise not_found("layer", layer)
    return {"product_id": product_id, "layer": layer, "states": found}


@router.get(
    "/products/{product_id}/confrontation",
    response_model=ConfrontationRows,
    summary="The confrontation that validated a published product.",
)
def confrontation(product_id: str) -> dict:
    """The day-by-day confrontation of the product with an independent source."""
    try:
        rows = service.confrontation(product_id)
    except RecordNotFound as error:
        raise not_found("product", product_id) from error
    return {"product_id": product_id, "comparisons": len(rows), "rows": rows}
