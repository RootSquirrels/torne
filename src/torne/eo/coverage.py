"""What a surface product allows to reconstruct, and from when.

Coverage is not a property of the collection alone: it is a **meeting** between
what the product covers in time and what one wants to reconstruct.

Three questions, three distinct answers:

1. **Is the period covered?** A collection that starts in November 2025 does
   not cover 2014-2025, whatever the quality of its data. It is a geometric
   fact, settled without discussion.

2. **Is the product usable *in a reconstruction*?** A product published several
   months after its validity could not have been known *at the time*. It
   remains usable — retrospectively, and that choice must be written down — but
   it cannot serve a **point-in-time** reconstruction of the period it
   describes.

3. **Does the product bring anything new?** That is the question of
   **dependence**, and coverage does not answer it: the registry
   (`eo.products`) does. A product derived from the reanalysis is not
   independent evidence of the reanalysis, even if it covers exactly the right
   period.

This module answers the first two. The third it **poses**: it makes the
dependence visible, so that it is not forgotten at ablation time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..contracts.spatial import BoundingBox, Footprint, SpatialRef
from .observations import CatalogueTimes
from .products import MeteorologicalDependence, SurfaceProduct

__all__ = [
    "Coverage",
    "coverage",
    "dependence_ledger",
    "max_publication_latency",
    "requested_footprint",
]


@dataclass(frozen=True, slots=True)
class Coverage:
    """What a product allows to reconstruct over a requested period.

    `covered` says whether the requested period lies **entirely** within the
    product's validity coverage. `reconstructable_from` says from when the
    coverage is complete — the instant to retain when sizing a training window.
    """

    product: SurfaceProduct
    requested_start: datetime
    requested_end: datetime
    covered: bool
    reconstructable_from: datetime | None

    @property
    def collection(self) -> str:
        """The collection concerned."""
        return self.product.collection

    @property
    def dependence(self) -> MeteorologicalDependence:
        """What the product owes to the reanalysis — the question it does not settle."""
        return self.product.dependence


def coverage(
    product: SurfaceProduct,
    *,
    start: datetime,
    end: datetime,
) -> Coverage:
    """The coverage of a product over the requested period.

    An **open** product — whose validity end is not published, because it is
    still running — covers indefinitely: the repository does not bound what the
    producer does not bound.

    `reconstructable_from` is the instant from which the product covers the
    requested period. It is `None` when it never does: a collection that stops
    in 2021 does not make a 2014-2025 window reconstructable, even if it covers
    its first half.
    """
    if end < start:
        raise ValueError("the requested period does not run backwards")

    product_start = product.coverage_start
    product_end = product.coverage_end

    reconstructable_from: datetime | None = None
    if product_start is not None and product_start <= end:
        reconstructable_from = product_start

    covered = (
        product_start is not None
        and product_start <= start
        and (product_end is None or product_end >= end)
    )

    return Coverage(
        product=product,
        requested_start=start,
        requested_end=end,
        covered=covered,
        reconstructable_from=reconstructable_from,
    )


def dependence_ledger(
    products: tuple[SurfaceProduct, ...],
) -> dict[MeteorologicalDependence, tuple[str, ...]]:
    """The dependence ledger, grouped by class.

    This is the output an ablation must read **before** comparing anything: for
    each dependence class, it says which products are concerned. A
    `NOT_AUDITED` product is not in the `INDEPENDENT` class: it is **not
    established** as independent either.

    The repository does not decide: it **makes visible**. It is then up to the
    experiment to say what that visibility allows to conclude.
    """
    groups: dict[MeteorologicalDependence, list[str]] = {
        dependence: [] for dependence in MeteorologicalDependence
    }
    for product in products:
        groups[product.dependence].append(product.collection)
    return {dependence: tuple(names) for dependence, names in groups.items()}


def requested_footprint(west: float, south: float, east: float, north: float) -> Footprint:
    """The footprint of a rectangular extent, in the catalogue's reference system.

    A reading shortcut: STAC works in EPSG:4326 for item geometry, and an extent
    requested from the catalogue is almost always a rectangle in degrees.
    """
    return Footprint.from_bounding_box(
        BoundingBox(west=west, south=south, east=east, north=north),
        ref=SpatialRef.epsg("4326"),
    )


def max_publication_latency(
    times: tuple[CatalogueTimes, ...],
) -> timedelta | None:
    """The longest publication delay observed in a batch.

    This is the number that decides whether a point-in-time reconstruction is
    feasible on a given collection: as long as the delay is unknown, one does
    not know what an operator could have known.
    """
    delays = [t.publication_latency for t in times if t.publication_latency is not None]
    if not delays:
        return None
    return max(delays)
