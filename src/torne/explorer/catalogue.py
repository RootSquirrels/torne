"""The established facts the explorer shows, each with the evidence behind it.

Every fact here is already recorded elsewhere — in a mission record, in
`docs/SOURCES.md`, or in the code. It is written once more only in typed form,
and **only with references**: a fact, a status or a coverage period without a
`Ref` cannot be built. `tests/test_explorer.py` resolves every reference against
the repository (documents and scripts exist, `module:attribute` imports), so a
renamed file or a moved constant breaks the build instead of leaving the
explorer silently wrong.

What the code already states is **not** restated here: model identities and
versions are read from their modules, surface products from `torne.eo`, adapter
source identifiers are checked against the adapters.

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

No entry may claim `KNOWLEDGE` without naming the persisted record that supports
it, and no record is persisted today.

## Distinct concepts

Countries, domains, physical assets, observation coverage, models and results
are kept apart. A station, a catchment and a raster coverage are three asset
kinds with their own geometry; a model is an implementation with an identity
read from code; a result is only "published" when a record is persisted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

__all__ = [
    "ASSETS",
    "DOMAINS",
    "MISSIONS",
    "MODELS",
    "SOURCES",
    "Asset",
    "AssetKind",
    "Domain",
    "Fact",
    "Mission",
    "ModelEntry",
    "Ref",
    "RefKind",
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


class RefKind(StrEnum):
    """What a reference points at. Each kind is resolved by the tests."""

    MISSION = "mission"
    """A mission of this catalogue, by identifier."""
    DOCUMENT = "document"
    """A repository file, optionally followed by ` §section`."""
    SCRIPT = "script"
    """A repository script that produced the evidence."""
    IMPLEMENTATION = "implementation"
    """`package.module:attribute`, importable."""
    RECORD = "record"
    """A persisted knowledge record, by its repository path."""


@dataclass(frozen=True, slots=True)
class Ref:
    kind: RefKind
    target: str

    @property
    def path(self) -> str | None:
        """The repository path a document, script or record reference points at."""
        if self.kind in (RefKind.DOCUMENT, RefKind.SCRIPT):
            return self.target.split(" §")[0]
        if self.kind is RefKind.RECORD:
            return self.target
        return None


def mission(target: str) -> Ref:
    return Ref(RefKind.MISSION, target)


def doc(target: str) -> Ref:
    return Ref(RefKind.DOCUMENT, target)


def script(target: str) -> Ref:
    return Ref(RefKind.SCRIPT, target)


def impl(target: str) -> Ref:
    return Ref(RefKind.IMPLEMENTATION, target)


@dataclass(frozen=True, slots=True)
class Fact:
    """A statement and the evidence it rests on."""

    text: str
    refs: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not self.refs:
            raise ValueError(f"a fact needs at least one reference: {self.text!r}")


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
    """The adapter class, exported by `torne.acquisition.adapters`."""
    domain_id: str
    publication_class: str | None
    """`p`, `b`, `c`, `n`, or `None` when not established (contract §3.11)."""
    facts: tuple[Fact, ...]
    qualified_in: Ref


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
    location_ref: Ref
    point: tuple[float, float] | None = None
    bbox: tuple[float, float, float, float] | None = None
    period: tuple[str, str] | None = None
    """First and last day observed (ISO dates, or years when only years are recorded)."""
    period_ref: Ref | None = None
    facts: tuple[Fact, ...] = ()

    def __post_init__(self) -> None:
        if self.period is not None and self.period_ref is None:
            raise ValueError(f"{self.asset_id}: an observed period needs its reference")


@dataclass(frozen=True, slots=True)
class ModelEntry:
    """A model or method implemented in the repository, and where it ran.

    Its identity and version are **read from code** (`identity`, `version`), not
    written here. `runs` says, with evidence, on which real data it was executed;
    an empty `runs` means implemented and tested, never executed on real data.
    """

    key: str
    title: str
    kind: str
    """`model` (produces a result with a nature) or `diagnostic` (tests a series)."""
    domain_ids: tuple[str, ...]
    identity: Ref
    """`module:attribute` holding the identity (method name or model id)."""
    version: Ref | None
    """`module:attribute` holding the version, when the module exposes one."""
    runs: tuple[Fact, ...] = ()


@dataclass(frozen=True, slots=True)
class Mission:
    """A mission, the status it reached, and what supports that status."""

    mission_id: str
    title: str
    status: Status
    status_basis: tuple[Ref, ...]
    domain_ids: tuple[str, ...]
    countries: tuple[str, ...]
    """ISO 3166-1 alpha-2 codes. Empty for a region-wide mission."""
    region: str | None
    """A region-wide scope such as `europe`, when the mission is not national."""
    question: str
    produced: tuple[Fact, ...]
    not_established: tuple[Fact, ...]
    asset_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    model_keys: tuple[str, ...] = ()
    knowledge_records: tuple[Ref, ...] = field(default=())
    """Persisted knowledge records; required for `KNOWLEDGE`."""

    def __post_init__(self) -> None:
        if not self.status_basis:
            raise ValueError(f"{self.mission_id}: a status needs its supporting evidence")
        if self.status is Status.KNOWLEDGE and not self.knowledge_records:
            raise ValueError(
                f"{self.mission_id}: a KNOWLEDGE status requires a persisted knowledge record"
            )
        if not self.countries and self.region is None:
            raise ValueError(f"{self.mission_id}: a mission has countries or a region")


# ------------------------------------------------------------------ domains

DOMAINS: tuple[Domain, ...] = (
    Domain("hydrology", "Hydrology", "torne.hydrology"),
    Domain("atmosphere", "Atmosphere", "torne.atmosphere"),
    Domain("earth_observation", "Earth observation", "torne.eo"),
    Domain("gas", "Gas supply", "torne.supply"),
)

# ------------------------------------------------------------------ sources

_ATMO1 = doc("docs/ATMO-001.md")
_ATMO2 = doc("docs/ATMO-002.md")

SOURCES: tuple[SourceEntry, ...] = (
    SourceEntry(
        source_id="hubeau.hydrometrie.observations_tr",
        title="Hub'EAU v2 — real-time hydrometry",
        adapter="HubeauFeedAdapter",
        domain_id="hydrology",
        publication_class=None,
        qualified_in=doc("docs/SOURCES.md §1"),
        facts=(
            Fact(
                "Station and window filters are accepted and ignored; only the quantity "
                "filter is applied.",
                (doc("docs/SOURCES.md §1.1"),),
            ),
            Fact(
                "Discharge rows are declared computed from stage: the two are not "
                "independent evidence.",
                (doc("docs/SOURCES.md §1.3"),),
            ),
        ),
    ),
    SourceEntry(
        source_id="usgs.ogc.daily",
        title="USGS Water Data for the Nation — OGC API, daily values",
        adapter="UsgsOgcItemsAdapter",
        domain_id="hydrology",
        publication_class=None,
        qualified_in=doc("docs/SOURCES.md §2"),
        facts=(
            Fact(
                "Filters are applied; the end of the walk is declared by the absence of `next`.",
                (doc("docs/SOURCES.md §2"),),
            ),
        ),
    ),
    SourceEntry(
        source_id="copernicus.dataspace.stac",
        title="Copernicus Data Space — STAC surface observations",
        adapter="CopernicusStacAdapter",
        domain_id="earth_observation",
        publication_class="p",
        qualified_in=doc("docs/SOURCES.md §3.2"),
        facts=(
            Fact(
                "Every item carries `published`, distinct from its validity time.",
                (doc("docs/SOURCES.md §3.2"), impl("torne.eo.observations:catalogue_times")),
            ),
            Fact(
                "Data assets require OIDC authentication: pixel values are not read.",
                (doc("docs/SOURCES.md §3.2"),),
            ),
        ),
    ),
    SourceEntry(
        source_id="noaa.ghcnd.daily",
        title="NOAA GHCN-Daily station records",
        adapter="GhcndDailyAdapter",
        domain_id="atmosphere",
        publication_class="n",
        qualified_in=doc("docs/SOURCES.md §4"),
        facts=(
            Fact(
                "No publication date per value: no observation is admissible point-in-time.",
                (doc("docs/SOURCES.md §4"), _ATMO1),
            ),
            Fact(
                "The access point always returns the period of record; French values are "
                "redistributed from ECA&D.",
                (doc("docs/SOURCES.md §4"),),
            ),
        ),
    ),
    SourceEntry(
        source_id="meteofrance.climatology",
        title="Météo-France climatological API (DPClim), daily series",
        adapter="DailyClimatologyAdapter",
        domain_id="atmosphere",
        publication_class="n",
        qualified_in=doc("docs/SOURCES.md §5"),
        facts=(
            Fact(
                "Answers with an API key: an order, then a CSV file; Lille-Lesquin (59343001) "
                "returned full months for 1950-01, 1990-01 and 2026-09.",
                (doc("docs/ATMO-002.md §2"),),
            ),
            Fact(
                "No publication metadata; units, flag meanings and the time basis of daily "
                "aggregates are not established. The CSV is not parsed into observations.",
                (doc("docs/ATMO-002.md §2"),),
            ),
        ),
    ),
    SourceEntry(
        source_id="meteofrance.observation",
        title="Météo-France observation API",
        adapter="MeteoFranceAdapter",
        domain_id="atmosphere",
        publication_class=None,
        qualified_in=doc("docs/SOURCES.md §5"),
        facts=(
            Fact(
                "Answers 403 with the subscribed key: the observation product is not part "
                "of the subscription.",
                (doc("docs/ATMO-002.md §2"),),
            ),
        ),
    ),
)

# ------------------------------------------------------------------- assets

_ESS = doc("docs/ATMO-002.md §3.1")
_PROFILE = doc("docs/ATMO-001.md §4")

ASSETS: tuple[Asset, ...] = (
    Asset(
        asset_id="USGS-05587450",
        kind=AssetKind.STATION,
        name="Mississippi River at Grafton, IL",
        country="US",
        domain_id="hydrology",
        source_id="usgs.ogc.daily",
        location_ref=script("tests/test_hydrology.py"),
        point=(-90.429, 38.9679722222222),
        period=("1933", "2026"),
        period_ref=doc("docs/PROGRAMME.md §3"),
        facts=(
            Fact("33 481 daily discharge values acquired.", (doc("docs/PROGRAMME.md §3"),)),
            Fact(
                "The day-of-year climatology reproduces the agency's published statistics to a "
                "median 0.11 %.",
                (doc("docs/PROGRAMME.md §3"), script("experiments/mission_002_real_world.py")),
            ),
        ),
    ),
    Asset(
        asset_id="FRE00104040",
        kind=AssetKind.STATION,
        name="Lille-Lesquin",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        location_ref=doc("docs/SOURCES.md §4"),
        point=(3.0975, 50.5700),
        period=("1944-12-01", "2026-09-30"),
        period_ref=_PROFILE,
        facts=(
            Fact("29 889 days, no gap.", (_PROFILE,)),
            Fact(
                "Effective sample size from about 500 to 3 900 depending on the lag cap; "
                "ATMO-001's 2 028 is the value at a cap of 45.",
                (_ESS,),
            ),
            Fact(
                "Constant mean rejected under a dependence-preserving null; a step survives "
                "detrending; maximum CUSUM on 1988-11-08. No attribution.",
                (doc("docs/ATMO-002.md §3.4"),),
            ),
        ),
    ),
    Asset(
        asset_id="FRM00007156",
        kind=AssetKind.STATION,
        name="Paris-Montsouris",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        location_ref=doc("docs/SOURCES.md §4"),
        point=(2.3378, 48.8217),
        period=("1983-12-18", "2026-10-25"),
        period_ref=_PROFILE,
        facts=(
            Fact("62.4 % coverage, with a 2 638-day gap from 1992 to 1999.", (_PROFILE,)),
            Fact(
                "Gap-aware effective sample size 736 (914 when gaps are collapsed).",
                (_ESS,),
            ),
            Fact(
                "No step once a linear trend is removed; the 2013 break date is not readable "
                "on this incomplete series.",
                (doc("docs/ATMO-002.md §3.4"),),
            ),
        ),
    ),
    Asset(
        asset_id="FR000007630",
        kind=AssetKind.STATION,
        name="Toulouse-Blagnac",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        location_ref=doc("docs/SOURCES.md §4"),
        point=(1.3789, 43.6208),
        period=("1947-01-01", "2026-09-30"),
        period_ref=_PROFILE,
        facts=(
            Fact("29 128 days, no gap.", (_PROFILE,)),
            Fact("Effective sample size 2 016 at a lag cap of 45, 508 at 365.", (_ESS,)),
        ),
    ),
    Asset(
        asset_id="FR000007650",
        kind=AssetKind.STATION,
        name="Marseille-Marignane",
        country="FR",
        domain_id="atmosphere",
        source_id="noaa.ghcnd.daily",
        location_ref=doc("docs/SOURCES.md §4"),
        point=(5.2158, 43.4378),
        period=("1921-01-01", "2026-09-30"),
        period_ref=_PROFILE,
        facts=(
            Fact("97.9 % coverage, with a 793-day gap from 1943 to 1945.", (_PROFILE,)),
            Fact("Effective sample size 2 021 at a lag cap of 45, 513 at 365.", (_ESS,)),
        ),
    ),
)

# ------------------------------------------------------------------- models

MODELS: tuple[ModelEntry, ...] = (
    ModelEntry(
        key="hydrology-anomaly",
        title="Day-of-year standardised discharge anomaly",
        kind="model",
        domain_ids=("hydrology",),
        identity=impl("torne.hydrology.anomaly:METHOD"),
        version=impl("torne.hydrology.anomaly:VERSION"),
        runs=(
            Fact(
                "Executed in mission 002 on 33 481 Grafton values, with version 1.0.0; the "
                "current version has not been re-run on real data.",
                (script("experiments/mission_002_real_world.py"), mission("mission-002")),
            ),
        ),
    ),
    ModelEntry(
        key="hydrology-rating",
        title="Stage-discharge rating relation (log-log least squares)",
        kind="model",
        domain_ids=("hydrology",),
        identity=impl("torne.hydrology.rating:MODEL_ID"),
        version=None,
    ),
    ModelEntry(
        key="atmosphere-anomaly",
        title="Day-of-year temperature climatology and anomaly (civil day)",
        kind="model",
        domain_ids=("atmosphere",),
        identity=impl("torne.atmosphere.anomaly:METHOD"),
        version=impl("torne.atmosphere.anomaly:VERSION"),
        runs=(
            Fact(
                "Executed on four GHCN-Daily stations against 1991-2020.",
                (mission("ATMO-001"), mission("ATMO-002")),
            ),
        ),
    ),
    ModelEntry(
        key="kalman-local-linear-trend",
        title="State-space Kalman filter, local linear trend, RTS smoothing",
        kind="model",
        domain_ids=(),
        identity=impl("torne.methods.kalman:LocalLinearTrendModel"),
        version=None,
        runs=(
            Fact(
                "Executed in mission 002: state reconstructed on the Grafton record, walk-forward "
                "evaluation over the last three years. No performance is established.",
                (script("experiments/mission_002_real_world.py"), mission("mission-002")),
            ),
        ),
    ),
    ModelEntry(
        key="effective-sample-size",
        title="Effective sample size and its sensitivity to the lag cap",
        kind="diagnostic",
        domain_ids=("atmosphere",),
        identity=impl("torne.methods.dependence:effective_sample_size_diagnostics"),
        version=None,
        runs=(Fact("Applied to four GHCN-Daily stations.", (_ESS, mission("ATMO-002"))),),
    ),
    ModelEntry(
        key="cusum-block-bootstrap",
        title="CUSUM mean break with a block-bootstrap null",
        kind="diagnostic",
        domain_ids=("atmosphere",),
        identity=impl("torne.methods.breaks:cusum_block_bootstrap"),
        version=None,
        runs=(
            Fact(
                "Applied to four GHCN-Daily stations, with and without a linear trend.",
                (doc("docs/ATMO-002.md §3.4"), mission("ATMO-002")),
            ),
        ),
    ),
    ModelEntry(
        key="gas-supply-terminal-layer",
        title="European LNG terminal layer: reserve, margin, derived entry, concentration, loss scenario",
        kind="model",
        domain_ids=("gas",),
        identity=impl("torne.supply.terminals:serie_par_installation"),
        version=None,
        runs=(
            Fact(
                "Executed by the LNG-002 mission on 3 765 terminal states — 25 installations in "
                "12 countries — and confronted with an independent source on the seven Spanish "
                "terminals over June 2026.",
                (script("experiments/lng_002_lng_terminals.py"), mission("LNG-002")),
            ),
        ),
    ),
    ModelEntry(
        key="gas-supply-storage-layer",
        title="European underground storage: fill, coverage, reconstitution, concentration",
        kind="model",
        domain_ids=("gas",),
        identity=impl("torne.supply.gas:buffer_jours"),
        version=None,
        runs=(
            Fact(
                "Executed by the LNG-002 mission on 570 storage states — the 19 countries that "
                "published them, among the 30 the platform answered for. The autonomy the "
                "platform publishes was found to be a deterministic function of the stock and "
                "the consumption it also publishes.",
                (script("experiments/lng_002_european_gas.py"), mission("LNG-002")),
            ),
        ),
    ),
)

# ----------------------------------------------------------------- missions

_GAS_RECORD = Ref(
    RefKind.RECORD,
    "src/torne/knowledge/records/gas-supply-europe/2026-10-31/record.json",
)
"""The published record of the European gas supply.

It is the first record the repository persists: the `KNOWLEDGE` status of
LNG-002 rests on it, and the Explorer serves it as it is.
"""

MISSIONS: tuple[Mission, ...] = (
    Mission(
        mission_id="mission-002",
        title="Mississippi at Grafton — end-to-end pipeline on real data",
        status=Status.DEMONSTRATION,
        status_basis=(script("experiments/mission_002_real_world.py"), doc("docs/PROGRAMME.md §3")),
        domain_ids=("hydrology",),
        countries=("US",),
        region=None,
        question="Can the pipeline acquire, read, evaluate and publish a lineage-verified product?",
        produced=(
            Fact(
                "A standardised discharge anomaly index with a verified lineage, produced "
                "during the run.",
                (script("experiments/mission_002_real_world.py"),),
            ),
        ),
        not_established=(
            Fact(
                "New information: the anomaly re-expresses one source.",
                (doc("docs/PROGRAMME.md §3"),),
            ),
            Fact(
                "A persisted product: the record lived in memory and the evidence in a "
                "temporary directory.",
                (doc("docs/PROGRAMME.md §6"),),
            ),
        ),
        asset_ids=("USGS-05587450",),
        source_ids=("usgs.ogc.daily",),
        model_keys=("hydrology-anomaly", "kalman-local-linear-trend"),
    ),
    Mission(
        mission_id="HYDRO-001",
        title="Hub'EAU — is published discharge a function of published stage?",
        status=Status.QUALIFICATION,
        status_basis=(doc("docs/SOURCES.md §1"), doc("docs/PRE-REGISTRATION-HYDRO-001.md")),
        domain_ids=("hydrology",),
        countries=("FR",),
        region=None,
        question="Is the discharge Hub'EAU publishes a deterministic function of its stage?",
        produced=(
            Fact(
                "The Hub'EAU access pattern that works (network feed, verified selection).",
                (doc("docs/SOURCES.md §1.2"), impl("torne.hydrology.hubeau:select_station")),
            ),
            Fact(
                "A pre-registered protocol and the script that implements it.",
                (
                    doc("docs/PRE-REGISTRATION-HYDRO-001.md"),
                    script("experiments/mission_003_hydro001.py"),
                ),
            ),
        ),
        not_established=(
            Fact(
                "The protocol has not been run: no station selected, no result recorded.",
                (doc("docs/PROGRAMME.md §5"),),
            ),
        ),
        source_ids=("hubeau.hydrometrie.observations_tr",),
        model_keys=("hydrology-rating",),
    ),
    Mission(
        mission_id="ATMO-001",
        title="Atmosphere — source inventory and profile of four French stations",
        status=Status.EXPLORATION,
        status_basis=(_ATMO1, script("experiments/atmo_001_premiere_acquisition.py")),
        domain_ids=("atmosphere",),
        countries=("FR",),
        region=None,
        question="Which atmospheric sources are reachable, and what do their series contain?",
        produced=(
            Fact("An accessibility inventory of 17 atmospheric access points.", (_ATMO1,)),
            Fact("An exploratory profile of four GHCN-Daily stations.", (_PROFILE,)),
        ),
        not_established=(
            Fact(
                "Its effective sample sizes and CUSUM p-values: ATMO-002 showed them to depend "
                "on estimator settings.",
                (_ESS, doc("docs/ATMO-002.md §3.4")),
            ),
        ),
        asset_ids=("FRE00104040", "FRM00007156", "FR000007630", "FR000007650"),
        source_ids=("noaa.ghcnd.daily", "meteofrance.observation"),
        model_keys=("atmosphere-anomaly",),
    ),
    Mission(
        mission_id="ATMO-002",
        title="Atmosphere — official data access and validation of ATMO-001",
        status=Status.EXPLORATION,
        status_basis=(_ATMO2, script("experiments/atmo_002_validation.py")),
        domain_ids=("atmosphere",),
        countries=("FR",),
        region=None,
        question="Do ATMO-001's estimates survive scrutiny, and is the official source reachable?",
        produced=(
            Fact(
                "The effective sample size is a range set by the lag cap, not a single value.",
                (_ESS,),
            ),
            Fact(
                "ATMO-001's CUSUM p-values were artefacts of a short long-run-variance window; "
                "a non-constant mean survives, a step mostly does not once detrended.",
                (doc("docs/ATMO-002.md §3.4"),),
            ),
            Fact(
                "Cold regimes are more persistent than warm ones at all four stations; "
                "significant at two after correction.",
                (doc("docs/ATMO-002.md §3.3"),),
            ),
            Fact(
                "The Météo-France daily climatological route works with an API key.",
                (doc("docs/ATMO-002.md §2"),),
            ),
        ),
        not_established=(
            Fact(
                "A confirmatory result: the protocol was fixed after ATMO-001 had shown regime "
                "counts, so this is a second exploratory pass.",
                (doc("docs/ATMO-002.md §3"),),
            ),
            Fact(
                "Any attribution of the mean change: station history and homogeneity are not "
                "checked.",
                (doc("docs/ATMO-002.md §7"),),
            ),
        ),
        asset_ids=("FRE00104040", "FRM00007156", "FR000007630", "FR000007650"),
        source_ids=("noaa.ghcnd.daily", "meteofrance.climatology", "meteofrance.observation"),
        model_keys=("atmosphere-anomaly", "effective-sample-size", "cusum-block-bootstrap"),
    ),
    Mission(
        mission_id="EO-registry",
        title="Surface observation — registry of Copernicus surface products",
        status=Status.QUALIFICATION,
        status_basis=(doc("docs/SOURCES.md §3.2"), impl("torne.eo.products:SURFACE_PRODUCTS")),
        domain_ids=("earth_observation",),
        countries=(),
        region="europe",
        question="Which surface products exist, what do they cover, and what do they depend on?",
        produced=(
            Fact(
                "A registry of surface products with coverage and declared meteorological "
                "dependence.",
                (impl("torne.eo.products:SURFACE_PRODUCTS"),),
            ),
        ),
        not_established=(
            Fact(
                "Any pixel value, and the dependence of derived products (not audited).",
                (doc("docs/SOURCES.md §3.2"),),
            ),
        ),
        source_ids=("copernicus.dataspace.stac",),
    ),
    Mission(
        mission_id="LNG-002",
        title="European gas supply — LNG terminals and underground storage",
        status=Status.KNOWLEDGE,
        status_basis=(
            doc("docs/LNG-002.md"),
            script("experiments/lng_002_european_gas.py"),
            script("experiments/lng_002_lng_terminals.py"),
            _GAS_RECORD,
        ),
        domain_ids=("gas",),
        countries=(
            "AT",
            "BE",
            "BG",
            "CH",
            "CY",
            "CZ",
            "DE",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "GR",
            "HR",
            "HU",
            "IE",
            "IT",
            "LT",
            "LU",
            "LV",
            "MT",
            "NL",
            "NO",
            "PL",
            "PT",
            "RO",
            "SE",
            "SI",
            "SK",
            "UA",
        ),
        region=None,
        question=(
            "Does the European gas supply carry information that its sources do not publish — "
            "at the level of the installation?"
        ),
        produced=(
            Fact(
                "The concentration of the reserve, which no platform publishes: a Herfindahl "
                "index of 0.0649 among the installations and 0.2413 among the countries, with "
                "the first country carrying 42.5 % of the European reserve.",
                (doc("docs/LNG-002.md §2.3"), _GAS_RECORD),
            ),
            Fact(
                "The state of the terminal system: 25 783 GWh of exploitable reserve and "
                "3 564 GWh per day of send-out — 7.2 days of coverage if no cargo arrived, on "
                "the tanks alone, without underground storage.",
                (doc("docs/LNG-002.md §2.3"), _GAS_RECORD),
            ),
            Fact(
                "The validation: the seven Spanish terminals, over the same gas days, against an "
                "independent source — a median relative difference of 1.16 % on the stock and "
                "0.00 % on the volumes, over 210 comparisons, the days aligned D to D.",
                (doc("docs/LNG-002.md §4"), _GAS_RECORD),
            ),
            Fact(
                "What the loss of an installation costs the system: the most critical one costs "
                "0.7 day of coverage, and the three worst cases are Spanish.",
                (doc("docs/LNG-002.md §2.3"), _GAS_RECORD),
            ),
        ),
        not_established=(
            Fact(
                "Any new country-level autonomy: the autonomy the platform publishes is a "
                "deterministic function of the stock and the consumption it also publishes, and "
                "the ratio is 0.100 for the nineteen countries that publish both.",
                (doc("docs/LNG-002.md §3"),),
            ),
            Fact(
                "The absolute entry into the tanks: the platform publishes the network injection "
                "only, so the entry derived from the stock equation is a lower bound, and the "
                "coverage computed from it an upper bound.",
                (doc("docs/LNG-002.md §4.1"), _GAS_RECORD),
            ),
            Fact(
                "The validation of the eighteen installations outside Spain: they are produced, "
                "but they were not confronted with an independent source.",
                (doc("docs/LNG-002.md §6"), _GAS_RECORD),
            ),
        ),
        model_keys=("gas-supply-terminal-layer", "gas-supply-storage-layer"),
        knowledge_records=(_GAS_RECORD,),
    ),
)
