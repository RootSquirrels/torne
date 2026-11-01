# ATMO-002 - Official data access, statistical validation, temporal integrity

> **Status: partial, by design.** This document reports what was **measured** on 2026-11-01. It
> publishes no knowledge product and draws no climatic conclusion. Items that were not done are
> listed in section 7, not hidden.

**Evidence labels.** **[FACT]** observed on a request or on received bytes. **[INFERENCE]** a
plausible reading of a fact. **[NOT VERIFIED]** not checked, with the way to check it.

**Reproduction.**

```bash
uv run python experiments/atmo_001_meteofrance.py      # Météo-France climatological route (needs METEOFRANCE_API_KEY)
uv run python experiments/atmo_002_validation.py       # GHCN-Daily validation (network, no secret), seeded
uv run pytest tests/test_meteofrance.py                # offline
```

The validation script is live-network and deliberately **not** part of the offline test suite.

---

## 1. Repository state and the ATMO-001 adaptations

**[FACT]** At the start of this pass `main` was at `abde888` ("Resolve ATMO-001 shared items A3,
A4, A7 and A10"). The working tree also held **uncommitted changes that are not ATMO's**
(`README.md`, `docs/ARCHITECTURE.md`, `docs/PROGRAMME.md`, `docs/RESEARCH_AND_VALIDATION.md`,
`docs/SOURCES.md`, `experiments/README.md`, `docs/PRE-REGISTRATION-HYDRO-001.md`), apparently
from the HYDRO workstream. **None of them was touched.** The only files modified by ATMO work are
`meteofrance.py`, `test_meteofrance.py`, `atmo_001_meteofrance.py` and the two new files
(`atmo_002_validation.py`, this document). The test suite passes (792 tests) after these
changes; a separate pre-change baseline was not recorded.

| # | Problem | Scope | Compatibility with HYDRO | Decision |
|---|---|---|---|---|
| A1 | Quality vocabulary has no "measured, check failed" state (5 closed values) | cross-domain (`contracts/observation.py`, persisted) | `src/torne/hydrology` does not reference `QualityStatus` members (grep) | **Defer, evidence strengthened**: Météo-France DPClim also carries per-value quality flags (`Q*` columns, values `1` and `9` seen). Additive enum value is the likely shape; needs the integration owner to confirm persisted-schema tolerance |
| A2 | Contract carries a publication *lower* bound only; GHCN-Daily gives an *upper* bound (archive version) | cross-domain (`contracts/time.py`) | no hydrology reference to `publication_lower_bound` / `PublicationState` (grep) | **Redesign before accepting.** No consumer needs it yet; section 5 gives a TORNE-side prospective bound instead. Also worth asking the contract owner how a lower-bound-only value is meant to become admissible (I did not re-read contract section 3.9) |
| A3 | Hydrology keyed on UTC day while documenting civil day | cross-domain | it *is* the hydrology module | **Resolved** in `abde888` |
| A4 | `reference_start/end` ignored in hydrology climatology | cross-domain | same | **Resolved** in `abde888` |
| A5 | Adapter must not promise a window the endpoint ignores | domain-local | none | **Accepted, applied** |
| A6 | `tzdata` not declared; `zoneinfo` fails on Windows without it | cross-domain (`pyproject.toml`) | needed by any civil-day computation | **Accept** (one line). Not applied: shared file, integration owner decides |
| A7 | Adapters not exported | cross-domain | - | **Resolved** in `abde888` for the existing adapters. `DailyClimatologyAdapter` (new) is **not** yet exported |
| A8 | No GHCN-Daily entry in `docs/SOURCES.md` | cross-domain doc | file has uncommitted HYDRO edits | **Accept, not applied**: wait for HYDRO's edits to land |
| A9 | The body of a 4xx reply is not retained | cross-domain (acquisition) | affects all adapters | **Accept as opt-in** (the 403 reply below is exactly the case) |
| A10 | Exports of new modules | cross-domain | - | **Resolved** in `abde888` for existing modules |

The integration owner arbitrates every "cross-domain" line.

---

## 2. Météo-France climatological API

**Authentication [FACT].** The portal issues an **API key**, sent in the `apikey` header, not an
OAuth2 bearer token. The credential reference is now `meteofrance.apikey`; the variable is
`METEOFRANCE_API_KEY`; the value is read at send time only and never logged. `EnvironmentToken`
and `FichierEnvToken` already accept any header/scheme, so a bearer token
(`Authorization: Bearer ...`) works by configuration alone; **[NOT VERIFIED]** this was not
exercised. The OAuth2 client-credentials flow and token renewal were **not investigated**.

**Reconnaissance, all on 2026-11-01 with the subscribed key [FACT].**

| Item | Result |
|---|---|
| Base | `https://public-api.meteofrance.fr/public/DPClim/v1` |
| Station metadata | `GET /liste-stations/quotidienne?id-departement=59&parametre=temperature` -> 200, JSON list of 35 stations (10 open). Fields: `id`, `nom`, `lon`, `lat`, `alt`, `posteOuvert`, `postePublic`, `typePoste` (0, 1, 2, 4 seen). `/liste-stations/horaire` also answers 200 |
| Daily data | two steps: `GET /commande-station/quotidienne?id-station=...&date-deb-periode=...&date-fin-periode=...` -> **202** `{"elaboreProduitAvecDemandeResponse":{"return":"<order id>"}}`, then `GET /commande/fichier?id-cmde=<id>` -> **201** `text/csv`, available immediately in every attempt |
| Format | `;`-separated, 136 columns, `POSTE;DATE;RR;QRR;...;TN;QTN;HTN;QHTN;TX;QTX;HTX;...;TM;QTM`, date `YYYYMMDD`. **Decimal comma** (`-2,9`): any future parser must handle it |
| Coverage | Lille-Lesquin (`59343001`) returned a full month for 1950-01, 1990-01 and 2026-09. Earlier years were not probed |
| Quality flags | `Q*` columns: `1` everywhere in the three months, `9` on `QHTN` (2026-09-01). **Meaning not verified here**: needs the provider documentation |
| Units | not in the file. **[NOT VERIFIED]** (documentation) |
| Time basis of the daily aggregates | not stated in the file; `HTN`/`HTX` are hour-of-extremum fields whose basis (UTC or local) is **[NOT VERIFIED]** |
| Publication metadata | none: the only response headers of interest are `X-Request-Id` and `Date`. Publication time is therefore **unknown** |
| Rate limits | no rate-limit header observed. **[NOT VERIFIED]** quota (portal documentation) |
| Reference data / normals | `/normales`, `/liste-stations/normales`, `/liste-stations/mensuelle`, `/liste-stations/decadaire` -> 404 "No matching resource". **No normals were found through this API**; only these paths were tried |
| Observation API | `DPPaquetObs` routes -> **403** with this key: not part of the subscription. This is the "missing subscription" case, distinct from ATMO-001's 401 "Missing Credentials" and from a 404 "No matching resource" (wrong path) |

**What exists in code.** `DailyClimatologyAdapter` (order then file, two pages, conformity checked
on the content: header must carry `POSTE` and `DATE`, every row must be the requested station, an
empty body is a violation). It does **not** parse the CSV into observations: the provider contract
(units, flags, time basis) is not established, so a broader adapter is deliberately not built.

---

## 3. GHCN-Daily statistical validation

All numbers below come from `experiments/atmo_002_validation.py` (seed `20261101`, 499
simulations or resamples, so the smallest reportable p-value is 0.002). Series: mean daily
temperature anomalies against 1991-2020, civil day in Europe/Paris, four stations.

**Protocol caveat.** The regime threshold (|z| >= 1, previous day) and the AR(1) null were fixed
in the script before its results were read, but ATMO-001 had already printed regime counts, so
this is **not** a clean pre-registration. Treat it as a second exploratory pass with a stated
protocol.

### 3.1 Effective sample size

**Estimator in the repository [FACT].** Geyer's initial positive sequence on the biased sample
ACF, `n_eff = n / (1 + 2 * sum rho_k)`, lag cap `ceil(10 * log10 n)` = 45 for n ~ 30 000.

**Reproduced [FACT].** ATMO-001's 2,028 (Lille) is reproduced as **2,027** by an independent,
gap-aware pairwise implementation with the same cap.

**But the figure is set by the cap, not by the data [FACT].** The retained lag equals the cap
(45) at all three complete stations, i.e. the positive-sequence rule never stopped the sum.
Lille-Lesquin, same series:

| Estimator | n_eff |
|---|---|
| Geyer, cap 10 / 20 / **45** / 90 / 180 / 365 | 3,868 / 3,003 / **2,027** / 1,374 / 874 / 505 |
| Bartlett taper, M = 14 / 45 / 90 / 180 / 365 | 4,733 / 2,941 / 2,096 / 1,401 / 872 |
| Batch means (independent estimator), 30 / 90 / 180 / 365 days | 3,551 / 2,136 / 1,413 / 951 |

The other complete stations behave the same way (Toulouse 2,016 at cap 45 and 508 at 365;
Marseille 2,021 and 513). **Consequence:** "29,889 days carry about 2,000 independent days, a
power overstatement of 14" is one point on a curve that runs from about 8x to about 59x. The
honest statement is a **range** (roughly 500-3,900 for Lille), and the lower values are likely
inflated by the slowly varying mean (trend), which section 3.4 shows is present.

**Missing values [FACT].** The repository helper (`structure_temporelle`) computes the ACF on the
gap-collapsed series: neighbours across a gap are treated as adjacent days. Paris-Montsouris
(8,057 scored days over 15,605 calendar days): the module gives 914, the gap-aware estimator
736 at the same cap (20 % lower). **[INFERENCE]** the lag-1 autocorrelation ATMO-001 reported for
Paris (0.709) is depressed by this; the gap-aware value on standardized anomalies is 0.805
(different series, so not an isolated test).

### 3.2 Persistence beyond daily inertia

**Operationalization.** H0: the ACF is that of an AR(1), `rho_k = phi^k`. Statistic
`E = sum_{k=2..K} (rho_k - phi^k)`; null by parametric AR(1) simulation with bootstrapped
innovations and the real missingness mask; one-sided; standardized by month-of-year SD.

| Station | raw K=10 | raw K=30 | linear-detrended K=10 | detrended K=30 |
|---|---|---|---|---|
| Lille | p = 0.002 | 0.002 | **0.272** | 0.002 |
| Paris | 1.000 | 0.326 | 1.000 | 0.730 |
| Toulouse | 0.002 | 0.002 | **0.434** | 0.002 |
| Marseille | 0.002 | 0.002 | 0.002 | 0.002 |

Bonferroni over the four stations (raw K=10): 0.008, 1, 0.008, 0.008. **Reading [FACT +
INFERENCE]:** at lags up to 10, the apparent excess persistence at Lille and Toulouse is
**explained by the linear trend**; at lags up to 30 it survives detrending at the three complete
stations; Paris is inconclusive (7,500 missing days). The surviving excess at lags 11-30 is
compatible with low-frequency variability or a non-linear trend; this analysis cannot tell which.

### 3.3 Cold versus warm regimes

Regime = previous-day standardized anomaly, cold `z <= -1`, warm `z >= +1`. Statistic: warm
minus cold OLS lag-1 slope (a slope, not a correlation, to avoid truncation bias). Moving-block
bootstrap, 90-day blocks (30-day blocks gave the same conclusions).

| Station | cold slope | warm slope | difference | 95 % CI | p | detrended difference (p) |
|---|---|---|---|---|---|---|
| Lille | 0.791 | 0.660 | -0.131 | -0.211, -0.048 | 0.002 | -0.103 (0.002) |
| Paris | 0.777 | 0.734 | -0.043 | -0.173, 0.109 | 0.661 | -0.057 (0.505) |
| Toulouse | 0.786 | 0.738 | -0.048 | -0.130, 0.040 | 0.248 | -0.103 (**0.008**) |
| Marseille | 0.743 | 0.585 | -0.158 | -0.240, -0.087 | 0.002 | -0.121 (0.002) |

**Reading.** The sign is the same at all four stations (cold regimes are more persistent). After
Bonferroni (raw): Lille 0.016, Marseille 0.008, Toulouse and Paris not significant. Toulouse
becomes significant after detrending, which shows the trend can mask as well as mimic an effect.
This is **station-heterogeneous, moderate evidence**, not a pooled result. Not controlled:
season (cold regimes concentrate in winter; only a monthly SD standardization is applied) and
non-linearity of the dynamics. No physical interpretation is offered.

### 3.4 Structural change (CUSUM)

ATMO-001 used the repository's OLS-CUSUM with a Bartlett long-run variance of
`floor(4 (n/100)^(2/9))` = 14 lags at n ~ 30 000, while the effective-sample-size cap is 45 and
the ACF is still far from zero at lag 14. **[FACT]** the reported p-values (1e-57 ... 1e-88)
are artefacts of that short window:

| Station | ATMO-001 p (lags) | p at 365 lags | block-bootstrap p (b = 45 / 90 / 180) | detrended, block-bootstrap p | break date | linear trend |
|---|---|---|---|---|---|---|
| Lille | 1.2e-57 (14) | 5.3e-11 | 0.002 / 0.002 / 0.002 | 0.002 | 1988-11-08 | 0.105 C/decade |
| Paris | 5.1e-10 (10) | 2.8e-03 | 0.002 / 0.002 / 0.002 | **0.492** | 2013-07-05 | 0.270 |
| Toulouse | 1.4e-58 (14) | 3.5e-11 | 0.002 / 0.002 / 0.002 | 0.020 | 1987-08-10 | 0.112 |
| Marseille | 5.5e-88 (14) | 7.5e-15 | 0.002 / 0.002 / 0.002 | 0.058 | 1988-09-22 | 0.105 |

(0.002 is the resolution limit of 499 resamples; observed statistics are 4-5x the 95 % null
quantile at the three complete stations, e.g. Lille 21.7 vs 5.3, and 1.8x at Paris.)

**Reading.** A constant mean is rejected at every station under a dependence-preserving null,
so the *existence* of a non-constant mean survives; the *precision* of ATMO-001's p-values does
not. Once a linear trend is removed the evidence for a **step** is weak (Paris none, Marseille
borderline, Toulouse modest, Lille retained). Three stations from different series place the
maximum CUSUM within 1987-1988, **[INFERENCE]** more consistent with a shared regional signal
than with three independent instrument changes. **No attribution is made.** Not done: station
history/relocation metadata, instrument and protocol changes, seasonal-block sensitivity. The
Paris break date (2013) is computed on a series with 7,500 missing days and should not be read.

### 3.5 Spatial consistency

Common window 1984-02-04 to 2026-09-30, days present at both stations. **[FACT]**

| Pair | raw | anomaly | anomaly by season (DJF/MAM/JJA/SON) |
|---|---|---|---|
| Lille-Paris | 0.976 | 0.877 | 0.89 / 0.89 / 0.88 / 0.86 |
| Lille-Toulouse | 0.894 | 0.600 | 0.57 / 0.62 / 0.62 / 0.58 |
| Lille-Marseille | 0.892 | 0.536 | 0.56 / 0.55 / 0.48 / 0.57 |
| Paris-Toulouse | 0.925 | 0.682 | 0.63 / 0.71 / 0.71 / 0.67 |
| Paris-Marseille | 0.912 | 0.579 | 0.61 / 0.60 / 0.51 / 0.61 |
| Toulouse-Marseille | 0.947 | 0.747 | 0.80 / 0.73 / 0.69 / 0.78 |

Raw correlations (0.89-0.98) mostly measure the shared seasonal cycle; anomaly correlations
(0.54-0.88) are the meaningful ones and are stable across seasons. ERA5 was **not** re-evaluated
in this pass; the ATMO-001 comparison stands as a consistency check, not ground truth.

---

## 4. Cross-domain temporal semantics

**What the shared contract carries [FACT].** `TemporalStamp` has `valid_time` (one UTC instant),
`known_at`, `ingested_at`, a publication state (`ESTABLISHED` / `BOUNDED` / `UNKNOWN`) and a
lower bound; `usable_at` is derived and is `None` when publication is unknown.
`civil_day_to_instant(day, zone)` requires an explicit zone and returns **the start of the civil
day** in that zone.

**Atmosphere and hydrology [FACT].** Atmosphere: `valid_time` = start of the civil day in the
caller's zone; climatology and episodes keyed on the civil day. Hydrology, since `abde888`: the
day key is the civil day in a caller-given zone and the product records the convention used.
**The two are now compatible on the day key.**

**What neither represents.** A daily value is an *interval*, stored as an *instant*:

| Wanted distinction | Today |
|---|---|
| source observation date | implicit in `valid_time` |
| observation time basis (local civil, UTC, source-defined) | **not recorded**; supplied as an argument |
| physical support interval | **not recorded** (a day's start stands in for it) |
| source publication time | `known_at` / state (correct, `UNKNOWN` for GHCN-D and DPClim) |
| first observation by TORNE | `ingested_at` |
| acquisition time | `AcquisitionOutcome.started_at` / evidence `acquired_at` |
| point-in-time usability | `usable_at` (correct) |

**Proposal (not applied).** Add **optional, additive** fields to the observation temporal data:
`time_basis` (enum: `local_civil`, `utc`, `source_defined`, `unknown`, plus the zone name when
local) and `support_start` / `support_end` (UTC, nullable). All default to `None`, so existing
data, persisted records and tests are unchanged; only the schema version and fingerprints that
include the stamp need a bump. `usable_at = None` stays valid. Providers differ (Météo-France
daily aggregates do not all share one window; GHCN-D declares none), so each adapter fills the
fields **only from the provider's documentation**, never by default. This touches
`contracts/time.py` and `contracts/observation.py`, which belong to the integration owner.

---

## 5. Prospective availability history (proposal)

ATMO-001's conclusion stands: neither GHCN-Daily nor DPClim gives a historical publication time,
so no historical point-in-time reconstruction is possible. TORNE can only build its **own**
first-seen history from now on.

**Smallest mechanism compatible with the architecture.** The file store already keeps content
by SHA-256 and a journal event per acquisition with `content_sha256` per page. A pure function
over that journal can, for a fixed `(source_id, request key)`, order captures by `acquired_at`,
report the first capture of each distinct hash, and classify consecutive captures as added /
modified / removed. No new storage and no new contract: the result is labelled **TORNE first-seen**
and is never written to `known_at`. **Not implemented** in this pass; it needs a design check
against the journal format first.

---

## 6. Integration proposal

1. Integration owner arbitrates A1, A2, A6, A8, A9 (section 1) after HYDRO's uncommitted edits land.
2. Export `DailyClimatologyAdapter` through `acquisition/adapters/__init__.py` (one line).
3. Add the GHCN-Daily and Météo-France climatological entries to `docs/SOURCES.md`.
4. Decide the time-semantics proposal of section 4; if accepted, ship it with a migration note
   and fingerprint/schema version bump.
5. Before anything is published as knowledge: obtain the DPClim documentation for units, flag
   semantics and time basis, then build the parser (decimal comma).

---

## 7. Not done in this pass

- Station history, relocations and instrument/protocol changes (needed before any attribution).
- ERA5 re-evaluation.
- OAuth2 client-credentials flow and bearer-token path (`METEOFRANCE_ACCESS_TOKEN`).
- Official normals: not found through the subscribed API; other products not searched.
- Rate-limit and quota documentation; history before 1950.
- The prospective first-seen mechanism (section 5) and any change to shared contracts.
- Translation of the ATMO-001 files (French) to English; only files written or changed in this
  pass were made English. `CritereConformite` keeps its existing French field names.
- Dedicated unit tests for the statistics in `atmo_002_validation.py` (it is a live experiment,
  not library code).
