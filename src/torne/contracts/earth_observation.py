"""Surface observation — when the data is a **field**, not a value.

`Observation` (contract §2.3) says what a source measured or reported "at this
instant and in its own terms". It says it well, all the way through: INV-19
requires **either** a value **or** a qualified reason for its absence.

A surface product fits neither case. A soil moisture index is not absent: it is
**present**, and it covers a surface. Its value is not a scalar — it is a field,
over a footprint, on a grid, with invalid pixels, quality masks and a time
window of integration.

Reducing such a product to an `Observation` would tell one of two lies: either
there is no value (while the product exists), or there is a scalar value (while
there is one per pixel). That is why `EarthObservation` **does not replace**
`Observation`: it extends it to what it cannot say.

This class adds no responsibility to the socle: it **reuses** the existing
contracts — `Source`, `RawEvidence`, `TemporalStamp`, `QualityStatus`,
`SpatialRef`, `Footprint`, `RasterGrid` — and reimplements none of them. The
acquisition socle still knows nothing of the domain; the semantic layer
(`src/torne/eo/`) reads a catalogue item and turns it into an
`EarthObservation`.

Two deliberate choices:

1. **Publication is carried by the data, not by convention.**
   `temporal.publication` and `temporal.known_at` say what the source exposes.
   A source whose publication class has not been established by execution
   (§3.11) produces an observation that is **not admitted** in a point-in-time
   reconstruction (INV-10) — and the repository does not fill that absence
   with an assumption.

2. **The window keeps two time dimensions.** `window_start` is the validity
   instant of the observation; `window_end` the end of the period the product
   integrates (a ten-day composite integrates ten days). Confusing them would
   mean that a product dated 30 June 2023 describes 30 June 2023, while it
   describes the ten days that end on it.

References (cited per module, as `docs/CORE_CONTRACTS.md` §5.2 requires
for modules written against the literature):

- **STAC 1.1.0** (OGC SpatioTemporal Asset Catalog) — item structure: `assets`,
  `properties`, `datetime`/`start_datetime`/`end_datetime`, `bbox`, `geometry`;
  <https://github.com/radiantearth/stac-spec/blob/v1.1.0/item-spec/item-spec.md>;
- **OGC API - Features, Part 1: Core** (ISO 19168-1) — collections core;
- **GeoJSON RFC 7946** — geometries and axis order;
- **GDAL affine transform convention** — `[a, b, c, d, e, f]`, read by
  `RasterGrid.from_transform`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .observation import QualityStatus
from .spatial import BoundingBox, Footprint, RasterGrid
from .time import TemporalStamp, to_utc

__all__ = ["Asset", "EarthObservation", "ObservationNature"]


class ObservationNature(StrEnum):
    """What the quantity is, from the point of view of **what produced it**.

    This is **not** the `QualityStatus` of contract §3.7: that one describes
    what the producer **declares** about a value ("provisional", "approved",
    "estimated by the source"). This one describes the **physical nature** of
    the quantity, independently of what the producer says about it.

    - `OBSERVED` — a quantity measured directly by the instrument;
    - `DERIVED` — a quantity computed by the producer from other observations;
    - `ESTIMATED` — a quantity estimated, that is, reconstructed by a model from
      input data.

    The distinction is what allows reasoning about the **dependence** between
    data families: a quantity derived from the same model and the same inputs
    as that model is not independent evidence of that model. A source and a
    product therefore carry **both**: `QualityStatus` on the observation,
    `ObservationNature` on the product.
    """

    OBSERVED = "observed"
    DERIVED = "derived"
    ESTIMATED = "estimated"


@dataclass(frozen=True, slots=True)
class Asset:
    """An asset of a surface product: the file, or the band, to fetch.

    An asset carries its address, its media type, its roles, and — essentially
    — the **authentication requirement** that protects it. The repository holds
    no secret: it only knows a **reference** (`docs/CORE_CONTRACTS.md`
    §4.9, INV-41). An asset that requires a token is therefore declared as
    such, and never presented as downloadable.

    `grid` and `bbox` describe **this asset's raster**, in the provider's
    reference system. They may differ from the reference system of the item's
    footprint: a Sentinel-2 tile is described in EPSG:4326 by the footprint and
    in UTM by its raster. The repository **does not convert** — it keeps both,
    and says so.
    """

    key: str
    href: str
    media_type: str | None = None
    roles: tuple[str, ...] = ()
    requires_authentication: bool = False
    size_bytes: int | None = None
    checksum: str | None = None
    grid: RasterGrid | None = None
    bbox: BoundingBox | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("Asset.key is required and non-empty")
        if not isinstance(self.href, str) or not self.href.strip():
            raise ValueError("Asset.href is required and non-empty")
        if not isinstance(self.roles, tuple):
            raise TypeError("Asset.roles is a tuple")
        for role in self.roles:
            if not isinstance(role, str) or not role.strip():
                raise ValueError("Asset.roles contains only non-empty roles")
        if self.size_bytes is not None:
            if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
                raise TypeError("Asset.size_bytes must be an integer or None")
            if self.size_bytes < 0:
                raise ValueError("Asset.size_bytes cannot be negative")
        if self.grid is not None and not isinstance(self.grid, RasterGrid):
            raise TypeError("Asset.grid must be a RasterGrid or None")
        if self.bbox is not None and not isinstance(self.bbox, BoundingBox):
            raise TypeError("Asset.bbox must be a BoundingBox or None")


@dataclass(frozen=True, slots=True)
class EarthObservation:
    """What a satellite observed of the surface, over a footprint, over a window.

    The invariants enforced at construction, all verifiable:

    - the identity, the quantity, the unit and the raw evidence are non-empty
      (INV-23, INV-25);
    - `window_start` and `window_end` carry a time zone (INV-15) and their order
      is checked: a window does not run backwards;
    - `temporal.valid_time` is present and **equal** to `window_start`: there is
      only one truth about the validity instant, and the window cannot
      contradict it;
    - there is **at least one asset**: a surface product without an asset is
      not a product, it is a promise;
    - `revision_of` differs from `observation_id`: an observation is not a
      revision of itself.

    What this class does **not** do:

    - it does not record the value: the raster content is a file, not a number,
      and the repository does not read pixels;
    - it does not qualify the quality status in the producer's place: `UNKNOWN`
      by default, which is the safe choice (contract §3.7);
    - it converts neither the unit, nor the reference system, nor the grid.
    """

    observation_id: str
    source_id: str
    quantity: str
    unit: str
    temporal: TemporalStamp
    evidence_id: str
    footprint: Footprint
    window_start: datetime
    window_end: datetime
    assets: tuple[Asset, ...] = ()
    grid: RasterGrid | None = None
    quality_status: QualityStatus = QualityStatus.UNKNOWN
    nature: ObservationNature | None = None
    """What the quantity is, from the point of view of what produced it.

    `None` — the default — means "unclassified". The contract classifies
    nothing on its own: the semantic layer (`src/torne/eo/`) reads the product
    registry and assigns the class. The repository prefers the absence of a
    class to a guessed one.
    """
    product_type: str | None = None
    processing_level: str | None = None
    key: str | None = None
    revision_of: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("observation_id", self.observation_id),
            ("source_id", self.source_id),
            ("quantity", self.quantity),
            ("unit", self.unit),
            ("evidence_id", self.evidence_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"EarthObservation.{name} is required and non-empty")

        if not isinstance(self.temporal, TemporalStamp):
            raise TypeError("EarthObservation.temporal must be a TemporalStamp")
        if not isinstance(self.quality_status, QualityStatus):
            raise TypeError("EarthObservation.quality_status must be a QualityStatus")
        if self.nature is not None and not isinstance(self.nature, ObservationNature):
            raise TypeError("EarthObservation.nature must be an ObservationNature or None")
        if not isinstance(self.footprint, Footprint):
            raise TypeError("EarthObservation.footprint must be a Footprint")
        if not isinstance(self.assets, tuple):
            raise TypeError("EarthObservation.assets is a tuple")
        for asset in self.assets:
            if not isinstance(asset, Asset):
                raise TypeError("EarthObservation.assets contains only Asset")
        if self.grid is not None and not isinstance(self.grid, RasterGrid):
            raise TypeError("EarthObservation.grid must be a RasterGrid or None")

        object.__setattr__(
            self, "window_start", to_utc(self.window_start, name="EarthObservation.window_start")
        )
        object.__setattr__(
            self, "window_end", to_utc(self.window_end, name="EarthObservation.window_end")
        )
        if self.window_end < self.window_start:
            raise ValueError("the window of an observation does not run backwards")

        if self.temporal.valid_time is None:
            raise ValueError("a surface observation carries its validity instant (INV-07)")
        if self.temporal.valid_time != self.window_start:
            raise ValueError(
                "the validity instant and the window start say the same thing: they cannot diverge"
            )

        if not self.assets:
            raise ValueError(
                "a surface product carries at least one asset: without it, it cannot be "
                "acquired, and a promise is not an observation"
            )

        if self.revision_of is not None:
            if not isinstance(self.revision_of, str) or not self.revision_of.strip():
                raise ValueError("EarthObservation.revision_of is non-empty when present")
            if self.revision_of == self.observation_id:
                raise ValueError("an observation cannot be a revision of itself")

    @property
    def spatial_ref(self) -> str:
        """The spatial reference, in the source's terms.

        The same notion as `Observation.spatial_ref`, but **structured** when
        the footprint is known: the repository does not keep a string when it
        knows the reference system. The string remains for point observations,
        whose reference is a station.
        """
        return str(self.footprint.ref)

    @property
    def is_usable(self) -> bool:
        """Is the observation admissible, at any instant at all?

        The rule is that of `TemporalStamp.usable_at`: it is `None` for an
        unknown publication (INV-10) or for a temporal inconsistency.
        """
        return self.temporal.is_usable()

    def covers_instant(self, instant: datetime) -> bool:
        """Does the instant fall inside the integration window?

        A surface observation describes a **period**, not an instant: the
        question "does this observation apply to *t*" is asked of the window,
        not of the validity instant.
        """
        target = to_utc(instant, name="instant")
        return self.window_start <= target <= self.window_end
