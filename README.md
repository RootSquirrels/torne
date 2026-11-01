# TORNE

**TORNE creates information about the physical world that does not exist in any available source.**

It takes existing evidence — gauges, stations, satellites, reanalyses, maps — as input, and derives from it new
variables, estimates, relationships and dynamics: in particular, **reconstructed states of the world that are not
directly observable in any single source**. The objective is not to collect, aggregate or republish public data.
It is to produce new, scientifically defensible information, with traceable methods, quantified uncertainty and
validation.

> **No scientific result is established yet.** The repository acquires real data, keeps the raw evidence, reads it
> into canonical observations, runs and evaluates models, and publishes knowledge products with a verifiable
> lineage. It has not yet produced a piece of information that is demonstrably new with respect to its sources.
> That is the next mission: [`docs/PROGRAMME.md`](docs/PROGRAMME.md).

## What TORNE is, and what it is not

Three things must not be confused:

| | What it is | Example |
|---|---|---|
| **TORNE, the capability** | acquiring, qualifying, aligning, reconstructing and documenting information about the physical world | the acquisition socle, the contracts, the lineage |
| **The domains** | the physics through which the capability is developed and demonstrated: hydrology, atmosphere, Earth observation | what a domain defines as objects, units, references, relations |
| **The missions** | particular questions TORNE answers from its data and models | BASIN-001: the water state of one real catchment |

Hydrology, atmospheric science and Earth observation are **modalities of observation of one physical system**, not
separate platforms. A mission that only describes one source in its own terms has not yet produced new
information; the value lies in what the combination of sources makes knowable that none of them says alone.

## Two objectives, measured separately

**A — Physical intelligence (current).** Reconstruct physical states, create variables that are absent from the
sources, quantify their uncertainty, and validate them against independent references. This is the engine, and
it is an asset on its own.

**B — Economic consequence (deferred).** Use that knowledge to anticipate a real economic consequence and test
whether it is priced late or incompletely. B remains a research objective, but it comes **after** the physical
engine: a financial application that succeeds does not retroactively validate the physical models it consumes
([`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5). If B fails, A keeps its qualified data, models and
variables. The two are never merged into one score.

## The next mission: BASIN-001 — integrated catchment intelligence

One real catchment, three observation modalities, a first reconstruction of its physical state.

1. Observed discharge (Hub'EAU).
2. Historical precipitation and temperature.
3. Soil moisture and evapotranspiration from Earth observation.
4. Land cover and catchment geometry.
5. A first spatio-temporal reconstruction of the catchment's water state.

**Expected result:** a knowledge product that carries **demonstrable additional information with respect to each
source taken separately**. The scope, the existing building blocks and the open decisions are in
[`docs/PROGRAMME.md`](docs/PROGRAMME.md) §4. BASIN-001 is not started: it begins once its pre-registration is
written.

## Current state

| In place | Not yet |
|---|---|
| Acquisition socle: hardened transport, content-addressed raw store, paginated fetcher, connector contract with a four-state conformity verdict that blocks non-conforming responses while keeping their evidence | No reconstruction combining several sources |
| Adapters exercised on the network: Hub'EAU v2 (two access patterns), USGS (Water Services and OGC API), Copernicus Data Space (OData and STAC), GHCN-Daily, Météo-France (verified up to the authentication refusal) | Météo-France data itself: an OAuth2 token is required |
| Contracts: source, raw evidence, observation, surface observation over a footprint, derived variable, knowledge product; three time dimensions, derived `usable_at`, qualified absence, publication classes | Land cover and catchment geometry: no source integrated |
| Semantic layers: `hydrology/` (USGS daily values, Hub'EAU feed, climatology and anomaly, rating relation), `atmosphere/` (GHCN-Daily), `eo/` (registry of 13 Copernicus surface products with their declared dependence) | One day-of-year climatology per domain: the duplication is recorded, not yet resolved (`docs/PROGRAMME.md` §6) |
| Methods: state-space Kalman filter with RTS smoothing and estimated variances, strictly proper scores and calibration, inference under dependence, multiplicity control, CR1 regression, CUSUM breaks, power | No performance established on a physical question |
| Replayable execution, cumulative temporal splits, baselines, metrics, uncertainty, knowledge products with verified lineage | No prospective evidence: pre-registrations are written by hand, not tooled |
| 784 tests; CI builds, installs and runs the package | The repository licence is not chosen — an owner decision |

## Reference documents

One responsibility each.

| Document | What it fixes |
|---|---|
| [`README.md`](README.md) | what TORNE is, and where to find what |
| [`docs/PROGRAMME.md`](docs/PROGRAMME.md) | the situation, the next mission, the open decisions — **what** comes next |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | boundaries, responsibilities, layers — **where** each thing goes |
| [`docs/CORE_CONTRACTS.md`](docs/CORE_CONTRACTS.md) | objects, temporality, invariants — **what** must remain true |
| [`docs/RESEARCH_AND_VALIDATION.md`](docs/RESEARCH_AND_VALIDATION.md) | the doctrine of evidence — **how** a claim is tested |
| [`docs/SOURCES.md`](docs/SOURCES.md) | the integrated sources — **what** each one gives, and does not give |

Mission records: [`docs/PRE-REGISTRATION-HYDRO-001.md`](docs/PRE-REGISTRATION-HYDRO-001.md) and
[`docs/ATMO-001.md`](docs/ATMO-001.md) (exploration report). [`experiments/README.md`](experiments/README.md)
explains what belongs in `experiments/`.

## Install and verify

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
```

Python 3.12, `uv` pinned by CI. The `torne` console entry point reports the package state.

## TORNE Explorer

A read-only map of what TORNE has really established: countries, domains, missions and the status each one earned
(qualification, exploration, demonstration, knowledge), the physical assets touched, the sources read, and the
knowledge products — none yet, and the explorer says why.

```bash
uv sync --extra explorer
uv run torne-explorer        # http://127.0.0.1:8765 — API under /api, docs at /docs
```

The explorer computes nothing and calls no provider; it serves a manifest derived from the repository
(`src/torne/explorer/`). Market Intelligence has a place in its navigation and stays closed while objective B is
deferred.

## Repository layout

```text
src/torne/
  acquisition/    cross-cutting socle: transport, fetcher, raw store, connector contract, adapters, credentials
  contracts/      objects and temporality: source, raw evidence, observation, spatial, derived variable, product
  methods/        scientific layer: Kalman, scores, dependence, multiplicity, regression, breaks, power
  evaluation/     temporal splits, baselines, metrics, uncertainty, report
  execution/      replayable model execution
  knowledge/      knowledge product records and lineage verification
  hydrology/      semantic layer: discharge and stage observations, climatology, anomaly, rating relation
  atmosphere/     semantic layer: station temperature and precipitation, climatology, regimes, profile
  eo/             semantic layer: surface products, their coverage and their dependence
  explorer/       read-only application: manifest, FastAPI API and the map front end
docs/             reference documents and mission records
tests/            the test suite
experiments/      exploratory scripts
```

## Limits and non-goals

TORNE does not try to build: a universal model of the world; a universal causal engine; a proprietary mathematical
engine reimplementing the scientific ecosystem; a knowledge graph that claims to explain a system by the mere
presence of relations; a microservice architecture, event bus, plugin framework or general workflow system; a
uniform validation imposing the same metrics on every model; a trading tool with physical data bolted on. Each of
these may be reconsidered **only in the presence of a demonstrated need**.

**Existing systems.** TORNE is new and independent. It does not modify, migrate or merge the historical
repositories, which stay read-only research references. What is taken from them is rewritten, with its origin
declared at the top of the module ([`docs/CORE_CONTRACTS.md`](docs/CORE_CONTRACTS.md) §5).

**Language.** All repository-authored content is in English. Source-native names (`débit`, `Calculée`,
`code_station`) and raw evidence are kept as published. Some modules written before this rule still carry French
identifiers and docstrings; they are translated when next touched (`docs/PROGRAMME.md` §6).

## Licence

**Not chosen.** The repository is hosted publicly on GitHub; intellectual property policy is handled by the owner,
separately.
