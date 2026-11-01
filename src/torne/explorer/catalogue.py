"""The established facts the explorer shows, and nothing it could only promise.

Every fact here is already recorded elsewhere — in a mission record, in
`docs/SOURCES.md`, or in the code — and is written once more only in typed form,
so that the explorer reads a structure rather than prose. The tests check that
each entry points at code that exists (`tests/test_explorer.py`).

## The status vocabulary

A mission's status says what it **produced**, not what it is about. It is a
closed, ordered vocabulary:

- `QUALIFICATION` — a source's behaviour is established (access, filters,
  publication class); no data series is profiled;
- `EXPLORATION` — real data is acquired and profiled; no knowledge product;
- `DEMONSTRATION` — a knowledge product was produced end to end, but it
  re-expresses a single source: it is not new information;
- `KNOWLEDGE` — a knowledge product carries information absent from each of its
  inputs, validated against an independent reference
  (`docs/RESEARCH_AND_VALIDATION.md` §1.1). It requires a persisted record.

No entry may claim `KNOWLEDGE` without naming the record that supports it, and
no record is persisted today: the explorer shows that gap rather than hiding it.

## Asset kinds

A station, a catchment and a raster coverage are three different objects. They
are presented side by side, but never reduced to one abstraction: each kind
keeps its own geometry (a point, an outline, a bounding box).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

__all__ = [
    "ASSETS",
    "DOMAINS",
    "MISSIONS",
    "SOURCES",
    "Asset",
    "AssetKind",
    "Domain",
    "Mission",
    "SourceEntry",
    "Status",
]


class Status(IntEnum):
    """What a mission produced, ordered from the least to the most."""

    QUALIFICATION = 1
    EXPLORATION = 2
    DEMONSTRATION = 3
    KNOWLEDGE = 4

    @property
    def label(self) -> str:
        return self.name.lower()


class AssetKind(StrEnum):
    """The kind of physical asset — never merged into one type."""

    STATION = "station"
    CATCHMENT = "catchment"
    RASTER_COVERAGE = "raster_coverage"


@dataclass(frozen=True, slots=True)
class Domain:
    """A modality of observation of the physical world."""

    domain_id: str
    title: str
    semantic_layer: str
    """The package that reads this modality into observations."""


@dataclass(frozen=True, slots=True)
class SourceEntry:
    """A source queried by an adapter, as qualified in `docs/SOURCES.md`."""

    source_id: str
    title: str
    adapter: str
    """The adapter class name, exported by `torne.acquisition.adapters`."""
    domain_id: str
    publication_class: str | None
    """`p`, `b`, `c`, `n`, or `None` when not established (contract §3.11)."""
    access: str
    limit: str
    docs: str


@dataclass(frozen=True, slots=True)
class Asset:
    """A physical object a mission actually touched.

    `point` is `(longitude, latitude)` for a station; `bbox` is
    `(west, south, east, north)` for a coverage. Coordinates are in the
    source's terms, EPSG:4326 unless stated; the explorer does not project.
    """

    asset_id: str
    kind: AssetKind
    name: str
    country: str | None
    domain_id: str
    source_id: str
    point: tuple[float, float] | None = None
    bbox: tuple[float, float, float, float] | None = None
    period: tuple[str, str] | None = None
    """First and last day observed (ISO dates, or years when only years are recorded)."""
    facts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Mission:
    """A mission, the status it reached, and what supports that status."""

    mission_id: str
    title: str
    status: Status
    domain_ids: tuple[str, ...]
    countries: tuple[str, ...]
    """ISO 3166-1 alpha-2 codes. Empty for a region-wide mission."""
    region: str | None
    """A region-wide scope such as `europe`, when the mission is not national."""
    question: str
    produced: str
    not_established: str
    records: tuple[str, ...] = ()
    """Documents and scripts that hold the evidence."""
    asset_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    knowledge_record_ids: tuple[str, ...] = field(default=())
    """Persisted knowledge records; required for `KNOWLEDGE`."""

    def __post_init__(self) -> None:
        if self.status is Status.KNOWLEDGE and not self.knowledge_record_ids:
            raise ValueError(
                f"{self.mission_id}: a KNOWLEDGE status requires a persisted knowledge record"
            )
        if not self.countries and self.region is None:
            raise ValueError(f"{self.mission_id}: a mission has countries or a region")


DOMAINS: tuple[Domain, ...] = (
    Domain("hydrology", "Hydrology", "torne.hydrology"),
    Domain("atmosphere", "Atmosphere", "torne.atmosphere"),
    Domain("earth_observation", "Earth observation", "torne.eo"),
)

SOURCES: tuple[SourceEntry, ...] = (
    SourceEntry(
        source_id="hubeau.hydrometrie.observations_tr",
        title="Hub'EAU v2 — real-time hydrometry",
        adapter="HubeauFeedAdapter",
        domain_id="hydrology",
        publication_class=None,
        access="open, no key",
        limit="station and window filters are ignored; discharge is computed from stage",
        docs="docs/SOURCES.md §1",
    ),
    SourceEntry(
        source_id="usgs.ogc.daily",
        title="USGS Water Data for the Nation — OGC API, daily values",
        adapter="UsgsOgcItemsAdapter",
        domain_id="hydrology",
        publication_class=None,
        access="open; optional API key beyond 1 000 requests per hour",
        limit="publication class not established",
        docs="docs/SOURCES.md §2",
    ),
    SourceEntry(
        source_id="copernicus.dataspace.stac",
        title="Copernicus Data Space — STAC surface observations",
        adapter="CopernicusStacAdapter",
        domain_id="earth_observation",
        publication_class="p",
        access="catalogue open; assets require OIDC authentication",
        limit="no unit published; pixel values not read",
        docs="docs/SOURCES.md §3.2",
    ),
    SourceEntry(
        source_id="noaa.ghcnd.daily",
        title="NOAA GHCN-Daily station records",
        adapter="GhcndDailyAdapter",
        domain_id="atmosphere",
        publication_class="n",
        access="open, no key",
        limit="always returns the period of record; French values come from ECA&D",
        docs="docs/SOURCES.md §4",
    ),
    SourceEntry(
        source_id="meteofrance.observation",
        title="Météo-France observation API",
        adapter="MeteoFranceAdapter",
        domain_id="atmosphere",
        publication_class=None,
        access="credential required",
        limit="verified up to the authentication refusal only",
        docs="docs/SOURCES.md §5",
    ),
)

ASSETS: tuple[Asset, ...] = (
    Asset(
        asset_id="USGS-05587450",
        kind=AssetKind.STATION,
        name="Mississippi River at Grafton, IL",
        country="US",
        domain_id="hydrology",
        source_id="usgs.ogc.daily",
        point=(-90.429, 38.9679722222222),
        period=("1933", "2026"),
        facts=(
            "33 481 daily discharge values acquired",
            "day-of-year climatology reproduces the agency's published statistics "
            "to a median 0.11 %",
        ),
    ),
    Asset(
        asset_id="FRE00104040",
        kind=AssetKind.STATION,
        name="Lille-Lesquin",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        point=(3.0975, 50.5700),
        period=("1944-12-01", "2026-09-30"),
        facts=("29 889 days, complete", "effective sample size 2 028 (6.8 %)"),
    ),
    Asset(
        asset_id="FRM00007156",
        kind=AssetKind.STATION,
        name="Paris-Montsouris",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        point=(2.3378, 48.8217),
        period=("1983-12-18", "2026-10-25"),
        facts=("62.4 % coverage, 2 638-day gap 1992-1999", "effective sample size 914 (11.3 %)"),
    ),
    Asset(
        asset_id="FR000007630",
        kind=AssetKind.STATION,
        name="Toulouse-Blagnac",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        point=(1.3789, 43.6208),
        period=("1947-01-01", "2026-09-30"),
        facts=("29 128 days, complete", "effective sample size 2 017 (6.9 %)"),
    ),
    Asset(
        asset_id="FR000007650",
        kind=AssetKind.STATION,
        name="Marseille-Marignane",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        point=(5.2158, 43.4378),
        period=("1921-01-01", "2026-09-30"),
        facts=("97.9 % coverage, 793-day gap 1943-1945", "effective sample size 2 023 (5.3 %)"),
    ),
)

MISSIONS: tuple[Mission, ...] = (
    Mission(
        mission_id="mission-002",
        title="Mississippi at Grafton — end-to-end pipeline on real data",
        status=Status.DEMONSTRATION,
        domain_ids=("hydrology",),
        countries=("US",),
        region=None,
        question="Can the pipeline acquire, read, evaluate and publish a lineage-verified product?",
        produced="a standardised discharge anomaly index with a verified lineage",
        not_established="new information: the anomaly re-expresses one source",
        records=("experiments/mission_002_real_world.py",),
        asset_ids=("USGS-05587450",),
        source_ids=("usgs.ogc.daily",),
    ),
    Mission(
        mission_id="HYDRO-001",
        title="Hub'EAU — is published discharge a function of published stage?",
        status=Status.QUALIFICATION,
        domain_ids=("hydrology",),
        countries=("FR",),
        region=None,
        question="Is the discharge Hub'EAU publishes a deterministic function of its stage?",
        produced="the Hub'EAU access pattern that works, and the pre-registered protocol",
        not_established="the protocol has not been run; no result is recorded",
        records=("docs/PRE-REGISTRATION-HYDRO-001.md", "experiments/mission_003_hydro001.py"),
        source_ids=("hubeau.hydrometrie.observations_tr",),
    ),
    Mission(
        mission_id="ATMO-001",
        title="Atmosphere — source inventory and profile of four French stations",
        status=Status.EXPLORATION,
        domain_ids=("atmosphere",),
        countries=("FR",),
        region=None,
        question="Which atmospheric sources are reachable, and what do their series contain?",
        produced="a source inventory and an exploratory profile (effective size, mean breaks)",
        not_established="no knowledge product; homogeneity of the series not checked",
        records=("docs/ATMO-001.md", "experiments/atmo_001_premiere_acquisition.py"),
        asset_ids=("FRE00104040", "FRM00007156", "FR000007630", "FR000007650"),
        source_ids=("noaa.ghcnd.daily", "meteofrance.observation"),
    ),
    Mission(
        mission_id="EO-registry",
        title="Surface observation — registry of Copernicus surface products",
        status=Status.QUALIFICATION,
        domain_ids=("earth_observation",),
        countries=(),
        region="europe",
        question="Which surface products exist, what do they cover, and what do they depend on?",
        produced="a registry of 13 products with coverage and declared meteorological dependence",
        not_established="no pixel value read; dependence of derived products not audited",
        records=("src/torne/eo/products.py", "docs/SOURCES.md §3.2"),
        source_ids=("copernicus.dataspace.stac",),
    ),
)
