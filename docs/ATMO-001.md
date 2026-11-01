# ATMO-001 — Atmosphere: source inventory and exploratory profile

> **Nature: source qualification and exploration.** This record publishes **no knowledge product** and draws **no
> conclusion** about the French climate. It inventories what is really accessible, measures what the sources contain,
> and lists what the socle had to change. Every measurement was made **by execution on 2026-11-01**, on real data.
>
> **Role in the programme.** ATMO-001 qualifies the **forcing** modality of BASIN-001 (precipitation and
> temperature). The source details are in `docs/SOURCES.md` §4–§5.

**Reproduction.**

```bash
uv run python experiments/atmo_001_sources_probe.py          # accessibility inventory
uv run python experiments/atmo_001_premiere_acquisition.py    # acquisition and profile
uv run python experiments/atmo_001_meteofrance.py             # the institutional route, with or without a token
uv run pytest tests/test_atmosphere.py tests/test_meteofrance.py
```

## 1. What the mission established

1. **The French institutional source is behind a token.** The three documented Météo-France routes answer `401`. The
   adapter and the credential-by-reference code are in place (`acquisition/adapters/meteofrance.py`,
   `acquisition/credentials.py`); with a token in `METEOFRANCE_TOKEN` or a git-ignored `.env`, the same script runs.
2. **A complete, documented observation source is open**: GHCN-Daily (NOAA/NCEI), 109 French stations, 1921–2026, with
   the producer's quality flags. For France its upstream source is **ECA&D**, not Météo-France.
3. **None of these observations is admissible in point-in-time reconstruction.** GHCN-Daily never publishes when a
   value became public: publication class N, `usable_at` is `None`. It is a structural constraint, declared.

## 2. Accessibility inventory

The probe asked 17 access points and classified each answer in distinct states, including `unexpected_content`, added
by this mission because two sources serve an error page with HTTP 200 (NOAA ISD: an Amazon S3 HTML error page of
36 822 bytes; OGIMET: body `Status: 403 Forbidden`). A check that only reads the status code would take those pages
for data; the probe now checks the shape of the content.

| State | Count | Sources |
|---|---|---|
| accessible | 6 | data.gouv.fr catalogue, CDS STAC catalogue, Open-Meteo ERA5 archive, GHCN-Daily (station file, readme, index) |
| behind an account | 3 | Météo-France observation ×2, Météo-France climatology |
| absent | 3 | CDS timeseries API, ARCO-ERA5 object, Open-Meteo previous-runs |
| unreachable | 2 | `donnees.meteofrance.fr` (DNS), DWD (TLS chain; no TLS verification was disabled) |
| unexpected content | 2 | NOAA ISD, OGIMET |
| HTTP 405 | 1 | CDS execution (POST only) |

**Reanalysis.** ERA5 re-served by Open-Meteo answers without a key and returns the **grid cell** coordinates and
altitude: it is a grid estimate, not a station measurement. The CDS catalogue is open; its data routes require an
account.

## 3. Representation in the canonical contracts

| Element | Decision | Basis |
|---|---|---|
| Unit | carried by (element, measurement): `TMAX` → `degC` (÷10), `PRCP` → `mm` (÷10), `SNWD` → `mm`, `ASLP` → `hPa` (÷10); `Source.unit` stays `None` | `readme.txt` v3.35 |
| Space | `spatial_ref` = station identifier; coordinates on the `Station`; datum declared absent | coordinates repeated on each row |
| Time | civil date → start of the local civil day, the zone being an argument | no time zone published |
| Publication | `PublicationState.UNKNOWN`, `known_at = None` → `usable_at is None` | no publication date per value |
| Absence | empty cell → `MISSING` + `NOT_MEASURED`, never zero | |
| Quality | no flag → `DECLARED`; quality flag → `UNKNOWN`, value and flag kept | no "measured, failed a check" state (A1) |
| Conformity | `station` and `elements` verified on the body received | an HTML page served with 200 → abstention |

**The civil day is not the UTC day.** In March 1945 France was at UTC+0: 2 March 1945 00:00 in Paris is 1 March 1945
23:00 UTC. A climatology keyed on the UTC day compares each day with the previous day's normal. `torne.atmosphere`
keys on civil days; the same defect in `torne.hydrology` (A3) is now fixed.

## 4. Exploratory profile (four stations)

**Coverage.** Lille-Lesquin 1944-12 → 2026-09, 29 889 days, complete. Toulouse-Blagnac 1947-01 → 2026-09, 29 128 days,
complete. Marseille-Marignane 1921-01 → 2026-09, 97.9 %, one 793-day gap (1943-07-01 → 1945-08-31, the Second World
War; the reason is an inference, the gap is treated as missing data). Paris-Montsouris 1983-12 → 2026-10, 62.4 %, a
2 638-day gap (1992-01 → 1999-03, reason not in any metadata read).

**Temporal structure — the result that changes the power of every test.** Daily mean-temperature anomalies against a
1991–2020 climatology:

| Station | Autocorrelation (lags 1, 2, 3) | Effective size | Ratio |
|---|---|---|---|
| Lille-Lesquin | 0.783 · 0.584 · 0.454 | 2 028 | 6.8 % |
| Paris-Montsouris | 0.709 · 0.484 · 0.348 | 914 | 11.3 % |
| Toulouse-Blagnac | 0.773 · 0.569 · 0.437 | 2 017 | 6.9 % |
| Marseille-Marignane | 0.770 · 0.601 · 0.488 | 2 023 | 5.3 % |

About 29 900 daily values carry about **2 000 independent days**: a test treating them as independent overstates its
power about fourteen-fold. Every later computation is sized by the effective size.

**A mean break at every station.** OLS-CUSUM (Bartlett long-run variance) on the anomalies: p from 5 × 10⁻¹⁰ (Paris)
to 5.5 × 10⁻⁸⁸ (Marseille), same sign and order (~0.5 σ, from about −0.45 to +0.06). The most economical reading is the
warming over the period (inference); attributing it to a forcing rather than a station or instrument change
**requires a homogeneity check that was not done**.

**Regimes.** With declared thresholds (|anomaly| ≥ 1, episodes ≥ 3 consecutive civil days), cold episodes outnumber
warm ones — an effect of the 1991–2020 reference against series starting in the 1940s, not a property of the climate.

**Consistency checks.** Correlations between station anomalies 0.54–0.88 (Lille–Paris 0.877). Against ERA5
(Open-Meteo, 2015–2025): Lille bias +0.78 °C, correlation 0.919; Marseille +1.49 °C, 0.943. ERA5 is a model estimate:
this measures a gap between two productions and validates neither.

## 5. The question that came out of the profile, and its status

> Are daily temperature anomalies persistent beyond daily inertia, and does that persistence differ between cold and
> warm regimes?

The question is sized by the effective size (≈ 8 000 independent days over four stations). It describes the temporal
structure of one source and would not, on its own, produce information absent from its inputs. It is **deferred**:
BASIN-001 uses the atmosphere modality as forcing, and the homogeneity and multiplicity requirements below carry over.

Requirements recorded for any later confirmatory use: an independent normals reference (Météo-France 1991–2020, once a
token is provided); a homogeneity check before any climatic attribution; tests sized by effective size; Holm
correction across stations and regimes; replication with a moving reference to rule out an artefact of the reference
period.

## 6. Adaptations the mission required of the socle

| # | Adaptation | Status |
|---|---|---|
| A1 | A quality state "measured, failed a producer check" | deferred (`docs/PROGRAMME.md` §6); values kept as `UNKNOWN` with their flag |
| A2 | An **upper** bound on publication (an archive version bounds publication from above) | deferred |
| A3 | Civil-day keying in `torne.hydrology` | **done** — `hydrology.anomaly` 1.1.0, `zone` argument |
| A4 | Reference-period filter in `torne.hydrology` (bounds were recorded but ignored) | **done** — `hydrology.anomaly` 1.1.0 |
| A5 | An adapter that promises no window, since GHCN-Daily always returns the period of record | done in the adapter |
| A6 | `tzdata` as a runtime dependency (no IANA database on Windows without it) | deferred: requires `uv lock` |
| A7 | Export of the GHCN-Daily adapter | **done** |
| A8 | GHCN-Daily entry in `docs/SOURCES.md` | **done** (§4) |
| A9 | Keep the body of a `4xx` refusal as evidence | deferred |
| A10 | Export of the Météo-France adapter | **done** |

## 7. What could not be verified

- the Météo-France observation and climatology APIs (token required);
- the `donnees.meteofrance.fr` portal (DNS does not resolve from the development machine);
- the CDS timeseries API, the ARCO-ERA5 object and Open-Meteo previous-runs (404 on the tested routes);
- NOAA ISD hourly observations and OGIMET SYNOP messages (routes out of service or refusing);
- DWD open data (TLS chain not verifiable);
- the provenance chain ECA&D → Météo-France, and the instrumental homogeneity of the series.
