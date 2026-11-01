"""From catalogue to surface observation: reading a STAC item.

The acquisition socle has downloaded and kept the catalogue's response. This
module turns it into an `EarthObservation`: it reads the metadata the producer
publishes, and it **refuses** to complete them when they are missing.

Three refusals, which are this module's value:

1. **An unregistered collection does not become an observation.** The registry
   (`eo.products`) says what a product is: its quantity, its unit, its nature.
   A collection absent from it has no named quantity, and the repository does
   not make up a name for it: `InterpretationError` is raised. That is what
   makes the registry **load-bearing** rather than decorative: adding a
   collection to it is an explicit, dated, revisable act.

2. **An item without time is refused.** A surface product without a time window
   describes no period: it would be neither datable, nor comparable, nor
   reproducible.

3. **An item without geometry is not rejected, but it is marked.** STAC gives
   `bbox` and `geometry`: the bounding box is always present, the outline may
   be missing. The repository then builds the footprint **from the bounding
   box**, and says so — `Footprint.from_bounding_box` carries that caveat.

## The reference system: why EPSG:4326 by default

STAC requires an item's geometry to be in **WGS84** (EPSG:4326) unless stated
otherwise (`proj:code`). This is therefore not an assumption of the repository
but a rule of the specification, applied and documented. The **raster** of an
asset, on the other hand, may be in another reference system — a Sentinel-2
tile is in UTM — and the repository keeps both without converting them (INV-23:
a non-empty reference; §5: no silent conversion).

## Publication: what the catalogue timestamps, and what it does not

Each item carries `published`, `created` and `updated`, distinct from
`datetime` (validity). The publication class of the source was established **by
execution**: it is class `P` (§3.11), and `KNOWN_AT` is `published`.
`publication_latency` derives the delay from it — and that delay is an
**arithmetic consequence** of the observation, not a property of it: it
explains why a point-in-time reconstruction of 2023 could not have used version
1.0.2 of the Soil Water Index, published in March 2025.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..contracts.earth_observation import Asset, EarthObservation
from ..contracts.observation import QualityStatus
from ..contracts.spatial import BoundingBox, Footprint, RasterGrid, SpatialRef
from ..contracts.time import PublicationState, TemporalStamp
from .products import SurfaceProduct, known_product

__all__ = [
    "CatalogueTimes",
    "InterpretationError",
    "catalogue_times",
    "observation_from_item",
    "publication_latency",
]


class InterpretationError(ValueError):
    """The catalogue item does not say what it must say.

    It is refused rather than guessed around: an item whose collection is
    unknown, or whose time window is unreadable, does not become an approximate
    observation. The repository prefers an explicit absence to a false
    observation.
    """


@dataclass(frozen=True, slots=True)
class CatalogueTimes:
    """The instants the catalogue publishes for an item.

    Three distinct moments, not to be confused:

    - `valid_start` / `valid_end` — the **period** the product covers;
    - `published` — the **publication** instant of this version: it is
      `KNOWN_AT`;
    - `created` / `updated` — the life cycle of the **catalogue entry**, which
      is not the product.

    An inconsistency between them is a fact to keep, not to smooth over: an
    `updated` later than `published` means the entry was touched after
    publication, and the repository does not pretend to know what changed.
    """

    valid_start: datetime | None = None
    valid_end: datetime | None = None
    published: datetime | None = None
    created: datetime | None = None
    updated: datetime | None = None

    @property
    def publication_latency(self) -> timedelta | None:
        """The delay between validity and publication.

        `None` when either instant is missing: the repository does not measure a
        delay it cannot establish.
        """
        if self.published is None or self.valid_start is None:
            return None
        return self.published - self.valid_start

    @property
    def window(self) -> tuple[datetime, datetime] | None:
        """The validity window, or `None` if it is unreadable."""
        if self.valid_start is None:
            return None
        return (self.valid_start, self.valid_end or self.valid_start)


def _instant(raw: object) -> datetime | None:
    """The catalogue's RFC 3339 instant, or `None` if it is unreadable."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        instant = datetime.fromisoformat(text)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return None
    return instant.astimezone(UTC)


def catalogue_times(item: Mapping[str, object]) -> CatalogueTimes:
    """The instants the catalogue publishes for this item.

    Instants are read from `properties` first, then from the item's root: STAC
    places them in `properties` for extensions, and at the root for core fields.
    """
    properties = item.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}

    def _read(key: str) -> datetime | None:
        return _instant(properties.get(key)) or _instant(item.get(key))

    start = _read("start_datetime")
    end = _read("end_datetime")
    instant = _read("datetime")
    if start is None and instant is not None:
        start = instant
    if end is None and instant is not None:
        end = instant

    return CatalogueTimes(
        valid_start=start,
        valid_end=end,
        published=_read("published"),
        created=_read("created"),
        updated=_read("updated"),
    )


def publication_latency(observation: EarthObservation) -> timedelta | None:
    """The delay between an observation's validity and its publication.

    This is the number that decides whether an observation can serve a
    **point-in-time** reconstruction: an observation published after the period
    it describes could not have been used at the time.
    """
    if observation.temporal.known_at is None:
        return None
    return observation.temporal.known_at - observation.window_start


def _reference(item: Mapping[str, object]) -> SpatialRef:
    """The reference system of the item's geometry.

    STAC requires WGS84 for an item's geometry unless stated explicitly:
    `proj:code` when present, EPSG:4326 otherwise.
    """
    properties = item.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    code = properties.get("proj:code")
    if isinstance(code, str) and ":" in code:
        try:
            return SpatialRef.from_string(code)
        except ValueError:
            pass
    return SpatialRef.epsg("4326")


def _footprint(item: Mapping[str, object], ref: SpatialRef) -> Footprint:
    """The item's footprint: its outline if it has one, its bounding box otherwise."""
    geometry = item.get("geometry")
    if isinstance(geometry, Mapping) and geometry.get("type") == "Polygon":
        return Footprint.from_geojson_polygon(dict(geometry), ref=ref)

    box = item.get("bbox")
    if isinstance(box, (list, tuple)) and len(box) >= 4:
        try:
            return Footprint.from_bounding_box(
                BoundingBox.from_sequence([float(v) for v in box[:4]]), ref=ref
            )
        except (TypeError, ValueError) as error:
            raise InterpretationError(f"the item's bounding box is unreadable: {error}") from error

    raise InterpretationError(
        "the item carries neither geometry nor bounding box: it cannot be located"
    )


def _grid(asset: Mapping[str, object]) -> RasterGrid | None:
    """An asset's grid, read from its affine transform.

    The catalogue publishes on each asset the affine transform in GDAL format
    (`proj:transform`), the raster shape (`proj:shape`) and its reference system
    (`proj:code`). Those three give the grid, without any raster library.
    """
    transform = asset.get("proj:transform")
    shape = asset.get("proj:shape")
    code = asset.get("proj:code")
    if not isinstance(transform, (list, tuple)) or len(transform) != 6:
        return None
    if not isinstance(shape, (list, tuple)) or len(shape) != 2:
        return None
    if not isinstance(code, str) or ":" not in code:
        return None
    try:
        return RasterGrid.from_transform(
            ref=SpatialRef.from_string(code),
            transform=[float(v) for v in transform],
            shape=[int(v) for v in shape],
        )
    except (TypeError, ValueError):
        return None


def _assets(item: Mapping[str, object]) -> tuple[Asset, ...]:
    """The item's assets.

    An asset that declares an authentication requirement (`auth:refs`) is marked
    as such: the repository holds no secret and therefore never presents a
    protected asset as downloadable.
    """
    raw = item.get("assets")
    if not isinstance(raw, Mapping):
        return ()

    assets: list[Asset] = []
    for key, value in sorted(raw.items()):
        if not isinstance(value, Mapping):
            continue
        href = value.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        roles = value.get("roles")
        size = value.get("file:size")
        checksum = value.get("file:checksum")
        auth_refs = value.get("auth:refs")

        bbox = None
        proj_bbox = value.get("proj:bbox")
        if isinstance(proj_bbox, (list, tuple)) and len(proj_bbox) >= 4:
            try:
                bbox = BoundingBox.from_sequence([float(v) for v in proj_bbox[:4]])
            except (TypeError, ValueError):
                bbox = None

        assets.append(
            Asset(
                key=str(key),
                href=href,
                media_type=value.get("type") if isinstance(value.get("type"), str) else None,
                roles=tuple(str(r) for r in roles) if isinstance(roles, (list, tuple)) else (),
                requires_authentication=bool(auth_refs),
                size_bytes=int(size) if isinstance(size, int) else None,
                checksum=str(checksum) if isinstance(checksum, str) else None,
                grid=_grid(value),
                bbox=bbox,
            )
        )
    return tuple(assets)


def observation_from_item(
    item: Mapping[str, object],
    *,
    source_id: str,
    evidence_id: str,
    ingested_at: datetime | None = None,
) -> EarthObservation:
    """The surface observation a catalogue item describes.

    `ingested_at` is the instant the raw evidence was **stored**: the repository
    does not guess it, and an observation whose storage instant is unknown is
    not admissible in a point-in-time reconstruction (`usable_at` is `None`,
    INV-08).
    """
    if not isinstance(item, Mapping):
        raise InterpretationError("a catalogue item is a JSON object")

    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise InterpretationError("the item carries no identifier")

    collection = item.get("collection")
    if not isinstance(collection, str) or not collection.strip():
        raise InterpretationError(f"item {identifier} carries no collection")

    product: SurfaceProduct | None = known_product(collection)
    if product is None:
        raise InterpretationError(
            f"collection {collection!r} is not in the registry: the repository does not "
            "name a quantity it does not know"
        )

    times = catalogue_times(item)
    window = times.window
    if window is None:
        raise InterpretationError(f"item {identifier} carries no time window")

    properties = item.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    product_type = properties.get("product:type")
    level = properties.get("processing:level")

    assets = _assets(item)
    if not assets:
        raise InterpretationError(f"item {identifier} carries no asset")

    grid = next((a.grid for a in assets if a.grid is not None), None)

    return EarthObservation(
        observation_id=identifier,
        source_id=source_id,
        quantity=product.quantity,
        unit=product.unit or "1",
        temporal=TemporalStamp(
            valid_time=window[0],
            known_at=times.published,
            ingested_at=ingested_at,
            publication=(
                PublicationState.ESTABLISHED
                if times.published is not None
                else PublicationState.UNKNOWN
            ),
        ),
        evidence_id=evidence_id,
        footprint=_footprint(item, _reference(item)),
        window_start=window[0],
        window_end=window[1],
        assets=assets,
        grid=grid,
        quality_status=QualityStatus.UNKNOWN,
        nature=product.nature,
        product_type=product_type if isinstance(product_type, str) else None,
        processing_level=level if isinstance(level, str) else None,
        key=identifier,
    )
