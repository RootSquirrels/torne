# TORNE — Programme

**Situation, next mission, open decisions.**
This document says what the repository can do today, what it cannot yet do, and what must be true for the next
mission to succeed. It does not narrate past work: that is in the Git history and the tests.

## 1. Purpose, and the test every mission must pass

TORNE creates information about the physical world that does not exist in the available sources: in particular,
**states of the world that no single source observes directly** (`README.md`).

Every mission is therefore judged by one question before any other:

> **What does this produce that is not already in one of its inputs?**

A mission that qualifies a source, profiles a series or reproduces a published statistic is useful — it builds
the evidence base — but it is **source qualification**, not new knowledge, and it is reported as such. New
knowledge is a reconstructed state, a derived variable, a relationship or a dynamic that is absent from every
input, comes with quantified uncertainty, and is validated against a reference that does not depend on it.

## 2. Non-negotiable principles

1. Scientific complexity is acceptable. Unjustified organisational complexity is not.
2. A function does not need to become a service. An abstraction must solve a concrete problem.
3. Never confuse documentation, implementation and validation. **A capability is not evidence**: evidence comes
   from an execution on real data whose result is recorded.
4. Raw data and its evidence are never silently overwritten.
5. Every historical reconstruction respects the information actually available at the date considered.
6. **Unknown stays unknown.** A missing metadata field is never filled by an assumption, and an absent observation
   is never replaced by zero. An unreachable source is *unknown*, not *unavailable*.
7. **No dependent judge.** A public product that already provides the target quantity is a reference or a judge,
   never the discovery; a witness derived from the mechanism it must confirm is ruled out.
8. **No confirmatory result without a frozen pre-registration.** Exploration comes first and is allowed; it is
   never presented as confirmation.
9. **A refutation is knowledge.** TORNE must be able to publish that a method does not transfer, without degrading
   what was correctly established elsewhere.
10. **The historical repositories stay intact.** Their building blocks are taken only after explicit
    classification (`docs/CORE_CONTRACTS.md` §5).
11. **One responsibility, one implementation; one owner per shared contract.** Shared contracts
    (`src/torne/contracts/`, `src/torne/acquisition/contracts.py`) and the reference documents are changed by one
    workstream at a time, and the change is recorded in the commit that makes it.
12. **English only** for repository-authored content; source-native names and raw evidence are kept as published.

**Every mission ends with** the changes made, the tests run and their results, the decisions taken, the
limitations found, the work not done, and the associated commit. A mission is never declared validated without
evidence.

## 3. What the repository can do today

Each line has a place in the code and a test suite that checks it. The full suite is green (784 tests).

| Capability | Where | What it guarantees |
|---|---|---|
| Hardened HTTP transport | `acquisition/transport.py` | redirect cap, measured duration, final URL recorded, credentials dropped when a redirect changes host, port or scheme |
| Raw store | `acquisition/store.py` | content deduplicated by digest and never rewritten; an acquisition event journaled for every retrieval |
| Fetcher | `acquisition/fetcher.py` | cursor, offset and header-link pagination; exhaustion qualified per source; widened retry policy for throttling sources |
| Connector contract | `acquisition/contracts.py` | four checks — transport, response structure, conformity to the question asked, exhaustiveness — and a **reasoned** four-state conformity verdict; the gate only opens on a positive verdict |
| Adapters | `acquisition/adapters/` | Hub'EAU v2 (station query and network feed), USGS Water Services and OGC API, Copernicus Data Space OData and STAC, GHCN-Daily, Météo-France (behind a token held by reference) |
| Contracts | `contracts/` | source, raw evidence, observation, surface observation over a footprint and a window, derived variable, knowledge product; three time dimensions, derived `usable_at`, qualified absence, publication classes P/B/C/N; spatial reference, footprint and raster grid |
| Semantic layers | `hydrology/`, `atmosphere/`, `eo/` | reading each source into canonical observations without inventing units, zones or publication instants |
| Methods | `methods/` | Kalman filter with irregular time steps, ML-estimated variances and RTS smoothing; CRPS, Winkler, pinball, PIT and calibration; effective sample size, block and cluster bootstrap; Benjamini–Hochberg, Bonferroni, Romano–Wolf; CR1 regression; CUSUM breaks; power |
| Execution, evaluation, knowledge | `execution/`, `evaluation/`, `knowledge/` | replay from configuration with explicit seed; cumulative temporal splits, baselines, metrics, uncertainty; frozen products with lineage verifiable down to raw evidence |

**What has been shown on real data.** Mission 002 acquired 33 481 daily discharge values of the Mississippi at
Grafton (USGS-05587450, 1933–2026), reproduced the agency's published day-of-year statistics to a median 0.11 %,
and published a standardised anomaly index with a verified lineage. That demonstrates the pipeline end to end. It
does not demonstrate new knowledge: an anomaly against the station's own climatology is a re-expression of one
source.

## 4. The next mission: BASIN-001 — integrated catchment intelligence

### 4.1 Definition

One real catchment, three observation modalities, a first reconstruction of its physical state.

| # | Input | Role in the reconstruction | Building blocks in place | Gap |
|---|---|---|---|---|
| 1 | Observed discharge (Hub'EAU) | integrated response of the catchment; the outlet constraint | `hubeau_feed` adapter, `hydrology.hubeau` station selection, HYDRO-001 qualification | station selection depends on the basin |
| 2 | Historical precipitation and temperature | forcing | `ghcnd` adapter and `atmosphere/` (point stations, publication class N) | Météo-France needs an OAuth2 token; ERA5 is reachable only through Open-Meteo's re-serving; a gridded or catchment-averaged forcing is not built |
| 3 | Soil moisture and evapotranspiration (EO) | the storage state the outlet does not show | `copernicus_stac` adapter and `eo/` registry: SSM (Sentinel-1, independent, from 2014-10), SWI (index, not audited) | **CLMS evapotranspiration starts on 2025-11-01**: it covers no historical year; pixel values are not read (assets require OIDC authentication) |
| 4 | Land cover and catchment geometry | the spatial support of the state | `contracts/spatial.py` (footprint, grid; no projection) | no land-cover or catchment-boundary source is integrated |
| 5 | Spatio-temporal reconstruction of the water state | the knowledge product | Kalman filter and smoother, evaluation, knowledge records | the state-space formulation linking 1–4 is not written |

### 4.2 What "new information" must mean here

The expected result is a knowledge product that carries **demonstrable additional information with respect to
each source taken separately**. Before the pre-registration is frozen, that is made operational:

- the reconstructed quantity (for example the catchment water storage, or soil moisture where no pixel is valid)
  is **not published by any input**;
- the reconstruction, evaluated on withheld data, **outperforms every single-source baseline** on the same target
  — the ablation "one data family at a time" — with the gain sized by the effective sample size, not the number of
  days;
- the ablation reads the **dependence ledger** first (`eo.coverage.dependence_ledger`): a product derived from the
  same meteorological inputs as the forcing is not independent evidence, and the published discharge is a function
  of the published stage at the same station (HYDRO-001);
- the reference used to validate the reconstruction does not depend on it.

### 4.3 Decisions required before BASIN-001 starts

1. **The catchment.** A French catchment is required by Hub'EAU; its size must be large enough for 1 km surface
   products and small enough for one outlet gauge to integrate it.
2. **The forcing source.** Météo-France (token to provide, through `METEOFRANCE_TOKEN` or a git-ignored `.env`),
   ERA5 through a stable path, or GHCN-Daily stations alone.
3. **Evapotranspiration.** Either accept that EO evapotranspiration is unavailable before 2025-11 and reconstruct it,
   or restrict the period. Reading pixel values requires a Copernicus account.
4. **Land cover and geometry sources**, and whether reading rasters justifies its first geospatial dependency
   (`docs/ARCHITECTURE.md` §8).

BASIN-001 starts when these four are decided and its pre-registration is written.

## 5. Mission records

| Record | Nature | Status | What it contributes to BASIN-001 |
|---|---|---|---|
| Mission 002 (`experiments/mission_002_real_world.py`) | end-to-end pipeline on real data | done | the pipeline and the anomaly product |
| HYDRO-001 (`docs/PRE-REGISTRATION-HYDRO-001.md`, `experiments/mission_003_hydro001.py`) | **source qualification**: is Hub'EAU's published discharge a deterministic function of its published stage? | protocol and code written; no run is recorded in the repository | the Hub'EAU access pattern that works (`hubeau_feed`), and the dependence of Q on H |
| ATMO-001 (`docs/ATMO-001.md`) | source inventory and exploratory profile of four French stations | exploration done; no product | the forcing sources and their limits; effective sample size ≈ 7 % of the number of days |
| Surface observation (no mission document) | registry of 13 Copernicus surface products, their coverage and declared dependence | code integrated | the EO modality and its dependence ledger |

## 6. Open decisions and known limits

None of these is an oversight; each is recorded so that it is not smoothed over.

**Owner decisions**

1. **The repository licence** is not chosen.
2. **Commit history** before 2026-11-01 is in French and is not rewritten (it is pushed); every later commit is in
   English.

**Recorded duplication and translation debt**

3. **Two day-of-year climatologies.** `hydrology.anomaly` and `atmosphere.anomaly` both implement a day-of-year
   climatology and anomaly. Both now honour the reference bounds and key on the civil day of a given zone. One owner
   must be chosen — the natural candidate is a single domain-neutral implementation used by both — when BASIN-001
   first needs a climatology across modalities.
4. **French identifiers and docstrings** remain in modules written before the English rule (`acquisition/`,
   `contracts/` core modules, `atmosphere/`, `methods/`, tests, experiments `atmo_001_*`). Shared contract
   identifiers such as `CritereConformite`, `verdict_conformite`, `Conformite` are part of the API; translating them
   is one dedicated change, not a side effect of feature work.

**Contract extensions identified, deferred (ATMO-001 §7)**

5. **A1** — a quality state "measured, failed a producer check" (GHCN-Daily publishes 14 quality flags; today such
   values are kept as `UNKNOWN` with their flag).
6. **A2** — an **upper** bound on publication (an archive version bounds publication from above; `TemporalStamp`
   only carries a lower bound).
7. **A6** — `tzdata` is not a declared runtime dependency, while civil-day computations need it on Windows. Adding
   it requires `uv lock` to update `uv.lock`.
8. **A9** — the body of a `4xx` refusal is not kept as evidence, so a source's explanation of its refusal is lost
   from the audit trail.

**Inherited limits**

9. Quality statuses of sources are not systematically mapped to the closed vocabulary (`docs/CORE_CONTRACTS.md`
   §3.7), and the `missing_reason` values met in practice are not inventoried.
10. No conservative per-source bound when publication is unknown; no common granularity rule between sources; the
    revision history can only be reconstructed for sources that date their revisions.
11. Determinism is verified in a single-process run only; the global seed is passed explicitly but not yet
    recorded in the manifest.
12. **A source can accept a filter and not apply it** (Hub'EAU `observations_tr`, `docs/SOURCES.md` §I.1). The
    `hubeau_feed` adapter asks only what the source can answer and selects stations after acquisition.

## 7. Mathematical capabilities, by priority

Ranked by importance, not by academic novelty. "Done" means a module executed, tested, and checked against the
published reference it cites.

| Priority | Item | Status |
|---|---|---|
| 1 | Untested guarantees corrected (end-to-end anti-leakage test now recomputes from the modified series) | done |
| 2 | Kalman filter as a reconstruction tool: irregular time steps, ML-estimated variances on the training history only, RTS smoothing published separately and declared as using the future (INV-44, INV-45) | done; multi-series correlated states and time-varying variances are not justified by data yet — BASIN-001 is the first case that may need them |
| 3 | Uncertainty and calibration: latent-state and forecast uncertainty, HAC metric uncertainty, CRPS (Gaussian and fair ensemble), Winkler, pinball, PIT with χ² and Kolmogorov–Smirnov | partly done; parameter uncertainty, misspecification, regime-conditional coverage and recalibration for dependent series remain. No generic conformal method: naive split-conformal on time series gives misleading coverage |
| 4 | Statistical practice: multiplicity (BH, Bonferroni, Romano–Wolf), validation under dependence (effective size, Politis–White block bootstrap, cluster bootstrap) | done; sequential inference (e-values, confidence sequences) not done |

Not taken: financial backtesting metrics (PBO, Deflated Sharpe) as generic TORNE tools.

## 8. What is not added now

- generic models (TabPFN, TabICL, pre-trained temporal transformers) because they were state of the art elsewhere;
- a global Bayesian framework; a validation, simulation or selection engine;
- a library of hydrological models before BASIN-001 defines its physical problem.

For BASIN-001, serious candidates include conceptual water-balance models, state-space reconstructions, and
spatio-temporal models where several gauges matter. **The choice follows from the available data and the quantity
to reconstruct**, not from algorithmic fashion.

## 9. Deferred material, kept in history

These documents were removed from the reference set because they prepare objective B or a research track that
BASIN-001 supersedes. They are not lost; they are in the history at commit `0fc3ad9`:

| Material | Where to read it | Why deferred |
|---|---|---|
| Qualification of Mississippi economic sources (USDA/AMS barge freight, grain movements, barge counts, USACE LPMS) | `git show 0fc3ad9:docs/SOURCES.md`, Part II | objective B, which follows the physical engine |
| `TORNE-EXP-001`, inter-agency coherence of the Rhine's hydrological state, with a financial branch | `git show 0fc3ad9:docs/PRE-ENREGISTREMENT-001.md` | a planned, unfrozen research track; its physical question can be revisited once BASIN-001 has a reconstruction to compare across agencies |
