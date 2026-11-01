"""The registry of known surface products, and their dependence.

This module is the **address book** of the surface-observation semantic layer:
it says what each collection of the Copernicus Data Space catalogue is, what it
covers, what it measures, and — the delicate point — **what it depends on**.

The facts it carries were **verified on the network on 2026-11-01** by querying
the STAC catalogue (`GET /v1/collections/<id>`). The fields carry the data as
the catalogue publishes it: nothing is completed, converted or assumed.

## Three things this registry refuses to do

**It does not fill in units.** The catalogue **publishes no unit** on its bands
(verified on 2026-11-01 on the bands `swi010`, `ssm`, `et_std`, `lai`, `ndvi`).
The unit carried here is therefore a **producer declaration**, and the field
`unit_established` is `False` until it has been established by execution. The
repository does not convert units anyway: it keeps them in the source's terms.

**It does not assume independence.** This is the core of the registry. A
surface product is not independent evidence of the meteorological model: it may
be computed from the same inputs. Three values, with three strictly distinct
meanings:

- `INDEPENDENT` — the quantity is a **radiometric measurement** of the
  instrument, with no temporal recomposition: scatterometry (ASCAT), radar
  (Sentinel-1), optics (Sentinel-2, Sentinel-3);
- `DEPENDENT` — the quantity is **computed from meteorological inputs**, and is
  therefore not independent evidence of the reanalysis;
- `NOT_AUDITED` — the quantity is **derived**, but the provenance of its
  computation inputs has not been audited by execution.

`NOT_AUDITED` is not a convenient bucket: it is the **honest** state of most
derived products. It does not allow a conclusion; it requires an audit before
one. That is the registry's reason to exist: without it, a "one data family at
a time" ablation would not compare independent families, but products whose
shared inputs are unknown.

**It does not confuse coverage with dependence.** A product can be perfectly
independent and cover only three months, or cover twenty years and depend on
the reanalysis. The two columns are separate, and one never compensates for the
other.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from ..contracts.earth_observation import ObservationNature

__all__ = [
    "SURFACE_PRODUCTS",
    "MeteorologicalDependence",
    "SurfaceProduct",
    "known_product",
]


class MeteorologicalDependence(StrEnum):
    """What the product owes to the meteorological reanalysis.

    Closed vocabulary; each value has a scope it does not exceed.
    """

    INDEPENDENT = "independent"
    """The quantity is a radiometric measurement of the instrument.

    It cannot be a function of ERA5-Land: nobody measures soil moisture by radar
    by injecting a reanalysis into it. Mind the scope: the **index** may be,
    even when the **measurement** is not.
    """

    DEPENDENT = "dependent"
    """The quantity is computed from meteorological inputs.

    It is therefore **not** independent evidence of the reanalysis: comparing it
    to an atmospheric reconstruction amounts to comparing a thing with itself.
    """

    NOT_AUDITED = "not_audited"
    """The quantity is derived, and the provenance of its inputs is not established.

    This is the default state of every derived product. It allows no
    conclusion: it requires an **audit** before an ablation is interpreted.
    """


@dataclass(frozen=True, slots=True)
class SurfaceProduct:
    """What the repository knows about a surface product, and what it does not.

    `coverage_start` and `coverage_end` are the **temporal validity bounds** the
    catalogue publishes for the collection. They say nothing about the
    publication delay: a product can be valid since 2014 and have been
    published only in 2025 — the case of Soil Water Index V1, whose version
    1.0.2 was published on 26 March 2025 for days of 2023. That delay is a
    **property of the observations**, not of the collection: it is read on each
    item, and computed by `eo.observations.publication_latency`.
    """

    collection: str
    title: str
    quantity: str
    nature: ObservationNature
    resolution_m: float | None
    crs: str | None
    coverage_start: datetime | None
    coverage_end: datetime | None
    instruments: tuple[str, ...]
    dependence: MeteorologicalDependence
    unit: str | None = None
    unit_established: bool = False
    publication_delay: str | None = None
    providers: tuple[str, ...] = ()
    dependence_note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.collection, str) or not self.collection.strip():
            raise ValueError("SurfaceProduct.collection is required and non-empty")
        if not isinstance(self.quantity, str) or not self.quantity.strip():
            raise ValueError("SurfaceProduct.quantity is required and non-empty")
        if not isinstance(self.nature, ObservationNature):
            raise TypeError("SurfaceProduct.nature must be an ObservationNature")
        if not isinstance(self.dependence, MeteorologicalDependence):
            raise TypeError("SurfaceProduct.dependence must be a MeteorologicalDependence")
        if (
            self.coverage_start is not None
            and self.coverage_end is not None
            and self.coverage_end < self.coverage_start
        ):
            raise ValueError("the coverage of a product does not run backwards")

    def covers_instant(self, instant: datetime) -> bool:
        """Is the product valid at this instant?

        An **open** collection — one whose end is not published, because it is
        still running — is valid indefinitely. The repository does not bound
        what the producer does not bound.
        """
        return not (
            (self.coverage_start is not None and instant < self.coverage_start)
            or (self.coverage_end is not None and instant > self.coverage_end)
        )

    @property
    def open_coverage(self) -> bool:
        """Is the collection still running, with no published validity end?"""
        return self.coverage_end is None


_JRC_VITO = ("European Commission JRC", "VITO", "CloudFerro")
_ESA = ("ESA", "European Commission", "CloudFerro")


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


SURFACE_PRODUCTS: Mapping[str, SurfaceProduct] = MappingProxyType(
    {
        p.collection: p
        for p in (
            SurfaceProduct(
                collection="clms_swi_europe_1km_daily_v1_cog",
                title="CLMS Soil Water Index (SWI) Europe 1km daily V1 (COG)",
                quantity="soil_water_index",
                nature=ObservationNature.DERIVED,
                resolution_m=1000.0,
                crs="EPSG:4326",
                coverage_start=_at("2014-12-31T12:00:01+00:00"),
                coverage_end=_at("2025-07-12T12:00:00+00:00"),
                instruments=("ascat", "csar"),
                dependence=MeteorologicalDependence.NOT_AUDITED,
                unit="1 (standardised index 0-100)",
                publication_delay="P2D",
                providers=_JRC_VITO,
                dependence_note=(
                    "The declared instruments are radiometric (ASCAT scatterometer, "
                    "Sentinel-1 radar): the measurement does not depend on ERA5. But the "
                    "SWI is an **index** — windows of 2 to 100 days, and local per-pixel "
                    'bounds (classes 241/242 "exceeding local pixel\'s dry/wet extreme"): '
                    "its temporal recomposition may use inputs not declared in the "
                    "catalogue. Provenance not audited by execution."
                ),
            ),
            SurfaceProduct(
                collection="clms_swi_europe_1km_daily_v2_cog",
                title="CLMS Soil Water Index (SWI) Europe 1km daily V2 (COG)",
                quantity="soil_water_index",
                nature=ObservationNature.DERIVED,
                resolution_m=1000.0,
                crs="EPSG:4326",
                coverage_start=_at("2025-07-12T12:00:01+00:00"),
                coverage_end=None,
                instruments=("ascat", "csar"),
                dependence=MeteorologicalDependence.NOT_AUDITED,
                unit="1 (standardised index 0-100)",
                publication_delay="P2D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Continuation of V1: same instruments, same derived nature, same "
                    "unaudited provenance. V2 does not backfill V1's history — it extends "
                    "it, and the repository keeps both rather than merging them."
                ),
            ),
            SurfaceProduct(
                collection="clms_ssm_europe_1km_daily_v1_cog",
                title="CLMS Surface Soil Moisture (SSM) Europe 1km daily v1 (COG)",
                quantity="surface_soil_moisture",
                nature=ObservationNature.ESTIMATED,
                resolution_m=1000.0,
                crs="EPSG:4326",
                coverage_start=_at("2014-10-04T00:00:00+00:00"),
                coverage_end=None,
                instruments=("csar",),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="m3/m3",
                publication_delay="P1D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Daily radar retrieval, with no temporal aggregation: the declared "
                    'instrument is the Sentinel-1 SAR, and the product exposes a "noise" '
                    "uncertainty band. The measurement is radiometric; retrieving the "
                    "water volume from backscatter is an inversion model whose inputs are "
                    "soil properties, not the reanalysis."
                ),
            ),
            SurfaceProduct(
                collection="clms_eta_global_300m_10daily_v1_cog",
                title="CLMS Evapotranspiration (ETA) Global 300m 10-daily V1 (COG)",
                quantity="evapotranspiration",
                nature=ObservationNature.ESTIMATED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2025-11-01T00:00:00+00:00"),
                coverage_end=None,
                instruments=("olci", "slstr"),
                dependence=MeteorologicalDependence.NOT_AUDITED,
                unit="mm/decade",
                publication_delay="P2D",
                providers=("European Environment Agency", "European Commission JRC", "CloudFerro"),
                dependence_note=(
                    "**Doubly constrained coverage.** The collection starts only on "
                    "1 November 2025: it covers no year of a multi-year reconstruction, "
                    "and using it retrospectively over 2014-2025 would be a projection, "
                    "not an observation. **Full dependence question**: the catalogue "
                    'itself says "ET modelled normally", "ET not modelled - cloud, snow, '
                    'or model non-convergence", and exposes a "Gap-filling distance" '
                    "band: it is a **model output with gap filling**, and its "
                    "meteorological forcing has not been audited by execution."
                ),
            ),
            SurfaceProduct(
                collection="clms_lai_global_300m_10daily_v1_cog",
                title="CLMS Leaf Area Index (LAI) Global 300m 10-daily V1 (COG)",
                quantity="leaf_area_index",
                nature=ObservationNature.DERIVED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2013-10-16T00:00:00+00:00"),
                coverage_end=_at("2026-02-28T23:59:59+00:00"),
                instruments=("olci", "vegetation"),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="m2/m2",
                publication_delay="P5D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Radiometric property of vegetation, measured optically. No "
                    "meteorological recomposition: LAI is an optical quantity, not an "
                    "atmospheric one."
                ),
            ),
            SurfaceProduct(
                collection="clms_fapar_global_300m_10daily_v1_cog",
                title=(
                    "CLMS Fraction of Absorbed Photosynthetically Active Radiation (FAPAR) "
                    "Global 300m 10-daily V1 (COG)"
                ),
                quantity="fapar",
                nature=ObservationNature.DERIVED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2013-10-16T00:00:00+00:00"),
                coverage_end=_at("2026-02-28T23:59:59+00:00"),
                instruments=("olci", "vegetation"),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="1",
                publication_delay="P5D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Fraction of absorbed radiation: an optical quantity. The absorbed "
                    "light fraction is measured, not inferred from a reanalysis."
                ),
            ),
            SurfaceProduct(
                collection="clms_ndvi_global_300m_10daily_v1_cog",
                title="CLMS Normalized Difference Vegetation Index (NDVI) Global 300m 10-daily V1 (COG)",
                quantity="ndvi",
                nature=ObservationNature.DERIVED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2014-01-01T00:00:00+00:00"),
                coverage_end=_at("2021-01-10T23:59:59+00:00"),
                instruments=("vegetation",),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="1",
                publication_delay="P3D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Radiometric vegetation index, computed from two reflectance bands. "
                    "**Coverage stopped in 2021**: this collection cannot serve a "
                    "reconstruction that goes beyond 2021; the DMP and LAI collections "
                    "cover the following period."
                ),
            ),
            SurfaceProduct(
                collection="clms_dmp_global_300m_10daily_v1_cog",
                title="CLMS Dry Matter Productivity (DMP) Global 300m 10-daily V1 (COG)",
                quantity="dry_matter_productivity",
                nature=ObservationNature.DERIVED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2014-01-01T00:00:00+00:00"),
                coverage_end=_at("2026-02-28T23:59:59+00:00"),
                instruments=("olci", "vegetation"),
                dependence=MeteorologicalDependence.NOT_AUDITED,
                unit="kg/m2/decade",
                publication_delay="P5D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Dry matter productivity is computed from absorbed radiation **and** "
                    "evapotranspiration: it depends on the radiative forcing and the "
                    "water balance. Provenance not audited by execution."
                ),
            ),
            SurfaceProduct(
                collection="clms_gpp_global_300m_10daily_v1_cog",
                title="CLMS Gross Primary Production (GPP) Global 300m 10-daily V1 (COG)",
                quantity="gross_primary_production",
                nature=ObservationNature.DERIVED,
                resolution_m=300.0,
                crs="EPSG:4326",
                coverage_start=_at("2023-06-21T00:00:00+00:00"),
                coverage_end=_at("2026-02-28T23:59:59+00:00"),
                instruments=("olci",),
                dependence=MeteorologicalDependence.NOT_AUDITED,
                unit="gC/m2/decade",
                publication_delay="P5D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Gross primary production is a photosynthesis model forced by "
                    "radiation and air temperature: the meteorological contribution cannot "
                    "be separated from the catalogue alone. Provenance not audited by "
                    "execution."
                ),
            ),
            SurfaceProduct(
                collection="clms_sce_europe_500m_daily_v1_cog",
                title="CLMS Snow Cover Extent (SCE) Europe 500m daily V1 (COG)",
                quantity="snow_cover_extent",
                nature=ObservationNature.OBSERVED,
                resolution_m=500.0,
                crs="EPSG:4326",
                coverage_start=_at("2017-03-01T06:35:00+00:00"),
                coverage_end=None,
                instruments=("modis", "viirs"),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="1",
                publication_delay="P1D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Snow cover measured by passive optics. The decision tree for the snow "
                    "class uses surface temperature, which is a surface quantity rather "
                    "than an atmospheric one — a distinction to keep in mind, not settled "
                    "here."
                ),
            ),
            SurfaceProduct(
                collection="clms_wl-rivers_global_vector_daily_v2_geojson",
                title="CLMS Water Level (WL) Rivers Global vector daily V2 (GeoJSON)",
                quantity="river_water_level",
                nature=ObservationNature.OBSERVED,
                resolution_m=None,
                crs="EPSG:4326",
                coverage_start=_at("2008-07-12T01:58:00+00:00"),
                coverage_end=None,
                instruments=("slstr",),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="m",
                publication_delay="P3D",
                providers=_JRC_VITO,
                dependence_note=(
                    "Water surface elevation from **satellite altimetry**, measured against "
                    "the geoid: a measured quantity, not derived from a reanalysis. "
                    "**Nature caveat**: it is a **water level**, not a discharge, and one "
                    "does not follow from the other without a local relation the catalogue "
                    "does not establish. **Metadata caveat**: the STAC item carries a "
                    "`datetime` that does not match the observation date — that date is "
                    "**inside the GeoJSON**."
                ),
            ),
            SurfaceProduct(
                collection="sentinel-1-grd",
                title="Sentinel-1 Ground Range Detected (GRD)",
                quantity="sar_backscatter",
                nature=ObservationNature.OBSERVED,
                resolution_m=None,
                crs=None,
                coverage_start=_at("2014-10-04T03:12:47+00:00"),
                coverage_end=None,
                instruments=("sar",),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="1 (calibrated amplitude)",
                publication_delay="PT24H",
                providers=_ESA,
                dependence_note=(
                    "Radar backscatter: a raw measurement, independent of any reanalysis. "
                    "Items carry a `published` **one hour after acquisition**: the shortest "
                    "publication delay of the whole family, which is what makes surface "
                    "observation usable in near real time."
                ),
            ),
            SurfaceProduct(
                collection="sentinel-2-l2a",
                title="Sentinel-2 Level-2A",
                quantity="surface_reflectance",
                nature=ObservationNature.OBSERVED,
                resolution_m=10.0,
                crs=None,
                coverage_start=_at("2015-06-27T10:25:31+00:00"),
                coverage_end=None,
                instruments=("msi",),
                dependence=MeteorologicalDependence.INDEPENDENT,
                unit="1 (surface reflectance)",
                publication_delay="PT24H",
                providers=_ESA,
                dependence_note=(
                    "Surface reflectance, measured optically. **Geometry caveat**: the "
                    "item footprint is in EPSG:4326, but the raster is in UTM per MGRS "
                    "tile — both reference systems coexist in the source and the "
                    "repository does not convert."
                ),
            ),
        )
    }
)
"""The known surface products, by collection identifier.

Key: the STAC collection identifier, which is the **exact** identifier the
catalogue publishes. The repository builds no abbreviated identifier: an
abbreviation would be a second vocabulary to maintain alongside the first.
"""


def known_product(collection: str) -> SurfaceProduct | None:
    """The known product for this collection, or `None`.

    `None` does not mean "unknown" in the sense of "does not exist": a
    collection can be perfectly real and not yet be in the registry. The
    registry is an **address book**, not an exhaustive catalogue.
    """
    return SURFACE_PRODUCTS.get(collection)
