# BASIN-001 - Data readiness, basin candidates and ground truth (lot 1)

> **Status: feasibility dossier, not a protocol and not a result.** It covers fleet 1 (basin, target, hypotheses)
> and fleet 3 (independent ground truth) of the BASIN-001 plan. It contains reconnaissance measurements made on
> 2026-11-01 and an honest assessment of what can and cannot be tested. No model was built. Fleets 2 (Earth
> observation pixels) and 4 (running HYDRO-001) are not covered here.

> **Decision recorded 2026-11-01 (project owner): the reformulated target of section 6 is accepted** - a
> basin-integrated groundwater-anomaly index judged on withheld wells, with no claim on absolute storage or on
> spatial maps. Decisions 2 (primary basin and positive control) and 3 (new `methods/` primitive) of section 8 are
> **still open**.

> **Superseded 2026-11-01: this line of work (groundwater anomaly index judged on withheld wells) is parked.** G1 was not
> passed on 174 gauges here, an aquifer-first search then found six candidates, and the economic pre-test did not support a
> pilot. See `docs/BASIN-002-AQUIFER-FIRST.md`.

**Evidence labels.** **[FACT]** measured on a request or on received bytes. **[INFERENCE]** a reading of facts.
**[NOT VERIFIED]** not checked, with the way to check it.

**Reproduction.**

```bash
uv run python experiments/basin_001_screening.py screen 14 76 60 80 27 10 51   # funnel and candidates
uv run python experiments/basin_001_screening.py redundancy H504062010 I403201001 H760201001
uv run python experiments/basin_001_catchment.py delineate I403201001 H504062010   # gate G1 (slow: one WFS call per reach)
uv run python experiments/basin_001_catchment.py outlets 14 76 60 80 27 10 51 --rows rows.json   # gauges at a basin outlet, then G1
```

Both scripts are live-network, key-free and read-only. They are not part of the offline test suite. The raw API
responses of this reconnaissance were **not** preserved in the raw store (no adapter exists yet for Hub'Eau
`obs_elab` or `niveaux_nappes`); the numbers are reproducible by re-running the scripts, not replayable from stored bytes.

---

## 1. The headline: the problem as first stated is weakly identifiable

Two findings change the problem, and both come from data, not from opinion.

1. **[FACT] Discharge already carries most of the groundwater dynamics at some wells.** At the chalk catchment of the
   Cailly, the monthly anomaly of log10(discharge) correlates with the groundwater-level anomaly of four of six
   nearby wells at Spearman 0.87 to 0.95 (section 4). A reconstruction of "groundwater storage" from
   discharge alone would reproduce, for those wells, what the discharge already says.
2. **[INFERENCE] In the simplest storage model the slow state is a rescaled baseflow.** With a linear aquifer
   reservoir, `Q_slow = S2 / tau2`, so `S2` is `tau2 * Q_slow`. Reconstructing `S2` from `Q` is then baseflow
   separation, a known procedure, not new information. New information can only come from what `Q` does not
   contain: the forcing (precipitation, potential evapotranspiration) and the surface layer seen by soil
   moisture.

Consequence: the target and the claim must be formulated so that the test can *fail* and so that a Q-only baseline
does not trivially win. Section 6 reformulates the target accordingly.

---

## 2. Screening: method and funnel

**Criteria, fixed in `experiments/basin_001_screening.py` before the ranking was produced [FACT]:** at least 25
years of daily mean discharge (`QmnJ`), 90 % completeness since the first value, at least 330 days with a value in
2025, and at least 5 long piezometers (>= 3 000 values, starting <= 2005, ending >= 2024) within 15 km of the
outlet gauge, at least 3 of them in the same aquifer body.

**Limits that matter [FACT / INFERENCE].**
- Seven departments chosen by me for their chalk or limestone aquifers (14, 27, 60, 76, 80, 10, 51). This is not a
  national screen; other basins may qualify.
- **No catchment boundary was available.** "Within 15 km of the outlet" is a proxy: a well 14 km away can lie in
  another catchment. Catchment boundaries exist (Sandre BD Topage topographic basins, shapefile, per a web search;
  **[NOT VERIFIED]** by download) but are not integrated. Hub'Eau's station referential publishes **no catchment
  area**.
- The first screening pass printed wrong "last date" values because Hub'Eau `obs_elab` ignores `sort`
  (always ascending). Depth was then measured with `count` and a 2025 window. Findings on that API:
  `code_entite` and date-window filters are **honoured**, `sort` is **ignored**, `count` is per station.

**Catchment geometry, what was checked after the first draft [FACT].** The Sandre WFS
`https://services.sandre.eaufrance.fr/geo/topage2022` answers key-free; with `outputFormat=geojson` and a bbox
(axis order `lat,lon` with `urn:ogc:def:crs:EPSG::4326`, or `lon,lat` with `urn:ogc:def:crs:OGC:1.3:CRS84`) it returns
small polygons, so no national file has to be downloaded. **But the topographic basins are elementary, between
confluences** (for example "La Seulles du confluent de la Thue (exclu) au confluent de la Mue (exclu)"), with
`CdOH`, `CdExutoire_1`, `CdBH` and no area or upstream link. A gauge's catchment is the union of the upstream
elementary basins plus the part of its own basin above the gauge. The same service exposes the hydrographic network
(`TronconHydrographique`, `NoeudHydrographique`, `CoursEau`, `SurfaceElementaire`), so an upstream traversal needs no
new dependency, but it is real work and the split at the gauge is an approximation.

**Gate G1 result (`experiments/basin_001_catchment.py`, Route chosen: Topage network traversal) [FACT].** The
upstream network is rebuilt from reach geometry (835 reaches for the Seulles, 29 for the Cailly), each reach is given to
its elementary basin, wells are classified by point-in-polygon (geometry only). The basin containing the gauge is taken
whole, so areas are **upper bounds** and a well in that basin is only "possibly upstream".

| | Seulles at Tierceville | Cailly at Fontaine-le-Bourg |
|---|---|---|
| Upstream reaches / elementary basins | 835 / 9 | 29 / **1** |
| Area (upper bound) | 264 km2 | 244 km2 (the whole Cailly down to its mouth: the gauge is well upstream of it) |
| Long wells inside (>= 3 000 values) | 4 | 6 |
| ...that also start <= 2005 and end >= 2024 | **1** (`01192X0043/S1`) | 4 (3 in the same altered-chalk body) |
| Wells in a basin other than the gauge's own (**certainly upstream**) | **0** | **0** |
| **Gate G1** | **FAIL** | **pass only as an upper bound** |

**All seven screened gauges [FACT].**

| Gauge | Upstream reaches / basins | Area (upper bound) | Qualifying wells inside | Gate G1 |
|---|---|---|---|---|
| Seulles at Tierceville | 835 / 9 | 264 km2 | 1 | FAIL |
| Cailly at Fontaine-le-Bourg | 29 / 1 | 244 km2 | 4 (3 in one body) | upper bound only |
| Cailly at Cailly | 2 / 1 | 244 km2 (same polygon, but the gauge is near the source) | 4 (3 in one body) | upper bound only, **meaningless** |
| Aure at Maisons | 453 / 3 | 132 km2 | 1 | FAIL |
| Drôme at Sully | 1 311 / 5 | 277 km2 | 0 | FAIL |
| Brèche at Nogent-sur-Oise | 531 / 3 | 480 km2 | 1 | FAIL |
| Orne at May-sur-Orne | not delineated: the traversal exceeded 5 000 reaches | - | - | not evaluated |

The two Cailly gauges give the same 244 km2 with 29 and 2 upstream reaches: the elementary basin is the whole Cailly,
so the bound can be several times too large. Of the seven screened candidates, none passes G1 cleanly.

**Screening for gauges whose catchment is exact (`basin_001_catchment.py outlets`) [FACT].** A gauge whose stream leaves
its elementary basin within 1 km has an almost exact catchment (the whole basin and all its upstream basins, minus a
short tail). Walking downstream reach by reach (following the arm the network calls "principal" at a diffluence) on the
93 of the 174 gauges that pass the discharge criteria:

| Stop reason | Gauges |
|---|---|
| stream distance to the basin exit > 1 km | 87 |
| **exit within 1 km** | **3** |
| unresolved bifurcation | 2 |
| terminal reach | 1 |

The three gauges at an outlet, each delineated and put through G1 with wells looked up over the real catchment extent
(Hub'Eau `bbox`):

| Gauge | Reaches / basins | Area | Long wells inside | Qualifying (start <= 2005, end >= 2024) | G1 |
|---|---|---|---|---|---|
| Seulles at Juvigny-sur-Seulles | 514 / 5 | 133 km2 | 0 | 0 | FAIL |
| Souleuvre at Carville | 650 / 5 | 119 km2 | 1 | 1 (basement of the upper Vire) | FAIL |
| Ante at Châtrices | 456 / 1 | 112 km2 | 0 | 0 | FAIL |

**Result.** Of 174 gauges in seven departments, 93 have enough discharge, 3 have an exact catchment, and none of those
3 has the three long wells in one aquifer body that gate G1 demands. This is a result about the data, not a failure of
the method: catchments of 100 to 300 km2 contain too few long, recent, labelled wells. The requested design (several
withheld wells per basin) cannot be set up on these seven departments.

**Reading [INFERENCE].** Of the seven Seulles wells within 15 km that looked usable in section 4, only one lies in the
catchment, and the three others inside it ended their records in 1990-2001 (and carry no aquifer-body label), so
they cannot serve a chronological hold-out. The wells with the highest discharge correlation were
inside a 15 km disc and not necessarily inside the catchment: the redundancy table of section 4 must be read
as a property of the *disc*, not of the basin. For the Cailly the elementary basin is far larger than the true
catchment, so "inside" is not established for any well. The Cailly passes the gate only if the gauge's own basin may be
trusted whole, which it cannot be. **Neither candidate is cleared.** What separates them is not data quality but the
geometry source: the Topage elementary basins cannot split a basin at a gauge.

**Funnel [FACT].** 174 gauges in service (types `STD` and `DEB`) in the seven departments:

| Criterion | Gauges passing |
|---|---|
| >= 25 years of daily discharge | 102 |
| >= 90 % complete | 151 |
| >= 330 days in 2025 | 155 |
| >= 5 long piezometers within 15 km | 20 |
| **all criteria, incl. >= 3 wells in one aquifer** | **7** |

The Somme basins, my first idea, **do not pass**: the gauges that have 25 years of discharge have fewer than 5
qualifying wells within 15 km (for example the Authie at Dompierre: 63 years, 2 wells), and the gauges with 5 or
more wells have shorter records (for example the Somme canal gauges at Abbeville, which are also canalised).

---

## 3. Candidate basins

The seven gauges that pass: Seulles at Tierceville (14), La Brèche at Nogent-sur-Oise (60), Cailly at
Fontaine-le-Bourg (76), Orne at May-sur-Orne (14), Cailly at Cailly (76), Aure at Maisons (14), Drôme at Sully (14).
The three best by the declared ordering (wells, then years) are kept:

| | Seulles at Tierceville | Cailly at Fontaine-le-Bourg | Brèche at Nogent-sur-Oise |
|---|---|---|---|
| Gauge code | `I403201001` | `H504062010` | `H760201001` |
| Daily discharge | 1971-09 to now, 55 y, 20 108 values | 1980-10 to now, 46 y, 16 820 values | 1969-01 to now, 55 y, 20 058 values |
| Discharge quality flags | 'Douteuse' 1.1 %, 2 null | 'Douteuse' 1.5 % | 'Douteuse' **5.7 %**, **276 null**, 'Calculée' 5.6 % |
| Aquifer near the gauge | Bathonian-Bajocian limestone (7 wells) | altered chalk, Seine estuary (4 of 6 wells) | Eocene of the Valois (3), chalk (3) |
| Long wells <= 15 km | 7 | 6 | 6 |
| Well series | daily, gaps <= 149 d | daily, gaps <= 108 d | daily, **gaps of 18 to 47 years** in 4 wells |
| Gauge `influence_locale_station` code | 1 | 1 | 1 |

The influence code's meaning (0 to 3) is **[NOT VERIFIED]**; it is shown raw. The discharge unit is not in the
payload (`resultat_obs_elab`, e.g. 1 474 at the Seulles median): **[NOT VERIFIED]**, Hub'Eau documentation
(litres per second expected). Precipitation: DPClim has open stations with records back to at least 1960
(Abbeville, Doullens) in the Somme; stations near these three basins were **not** checked.

---

## 4. Groundwater vs discharge: how redundant are they? [FACT]

Spearman correlation between deseasonalized monthly anomalies of log10(Q) and of the well level, common months only
(`experiments/basin_001_screening.py redundancy`). Wells are listed nearest first and **were not selected on this
value**.

| Basin | Wells (nearest -> farthest), Spearman | Reading |
|---|---|---|
| Seulles | 0.21, 0.67, 0.63, 0.46, 0.44, 0.46, 0.04 | moderate and **heterogeneous** |
| Cailly | 0.64, 0.88, 0.95, 0.87, 0.12, 0.91 | **high** at 4 of 6 wells |
| Brèche | -0.36, 0.79, 0.69, 0.67, -0.16, 0.66 | 0.66 to 0.79 at 4 wells, **negative** at the 2 Eocene wells, whose series have gaps of 35 to 39 years |

**Reading [INFERENCE].** Where correlations are 0.9 (Cailly), a Q-only baseline sits near the ceiling: an ablation
cannot show the benefit of forcing or satellite data there. Where they are low and scattered (Seulles), either the
wells are not representative of the catchment (some may be outside it: **geometry decides**), or the discharge
misses part of the groundwater signal (room for gain). The data alone cannot say which; the catchment boundary can.

**Effective sample size of these monthly series [FACT]** (`effective_sample_size_diagnostics`, positions = month
index, `min_pairs=20`): Cailly log10 Q anomaly 553 months -> **27**; Cailly well 366 months -> **22**; Seulles Q 661
-> **75**; Seulles well 659 -> **46**. The sum is ended by the positivity rule from cap 24-48 on, so the figures
are stable and not cap-bound beyond that. **Consequence:** about 22 to 75 independent months. At `n_eff` = 46 and a
correlation near 0.5 the standard error is about 0.11: only an improvement of roughly 0.2 or more in correlation is
detectable per well. Small gains cannot be claimed.

---

## 5. Independent ground-truth matrix (fleet 3)

| Reference | Availability | Independent of the inputs? | Resolution | Coverage | Uncertainty given | Leakage risks | Verdict |
|---|---|---|---|---|---|---|---|
| **Piezometry** (Hub'Eau `niveaux_nappes`, ADES) | **open, no key** [FACT] | measurement chain independent of discharge (other producers: BRGM / regional geological services); **hydrologically coupled** through baseflow | point; **head, not storage** (specific yield unknown); daily | 1966-2026, 37 long wells in the Somme alone [FACT] | flags only: `qualification` (Correcte, Incertaine, Incorrecte, Non qualifié), `statut`, `mode_obtention`; no numeric uncertainty | choosing wells by correlation with Q; using Q-derived baseflow as both input and judge; wells outside the catchment | **usable as a judge of dynamics** (anomaly, rank), **not of magnitudes** |
| **In-situ soil moisture** (SMOSMANIA, via ISMN) | free **after registration** [per web search]; registration is a user action | independent of Q and P; the EO soil-moisture product is itself validated against ISMN, so independence from EO is **[NOT VERIFIED]** | point, several depths 5-30 cm, 12-min | since 2007, **south-west France** only | per-sensor, ISMN quality flags | station reprocessing after sensor changes | **not applicable to the three candidates** (northern France); applicable only to a south-west basin |
| **Other hydrometric stations** (nested gauges) | open | **not independent**: same water balance | point | long | Hub'Eau flags | conservation links gauges | useful for a spatial consistency check, **not a judge of storage** |
| **GRACE / GRACE-FO** | not investigated | independent of the inputs | hundreds of kilometres | 2002- | yes | none | **[NOT VERIFIED]**; resolution is expected to be far too coarse for catchments of 10^2-10^3 km^2 |
| **ERA5-Land / SIM soil and groundwater** | not investigated | **no**: models forced by the same meteorology | grid | long | model | circular if used as a judge | comparator only |
| **CLMS SSM / SWI** (EO) | catalogue only; pixels need OIDC | SSM independent of meteorology (registry), SWI not audited | 1 km, daily; from 2014-10 | 2014-10- | product flags | it is an *input* of the reconstruction; cannot judge itself | input, not judge; fleet 2 |
| **CAMELS-FR** | per web search: exists, built on Hydroportail | - | catchment | long | - | - | **prior art and benchmark**; check overlap with the candidates and whether it holds any storage variable |
| Cosmic-ray neutron sensors, flux towers, lysimeters | not investigated | - | - | - | - | - | **[NOT VERIFIED]** |

### 5.1 What the matrix concludes (and what it refuses to validate)

- **Not validable with the references found:** the **absolute catchment storage in mm**. Wells give heads, the
  conversion factor is unknown, and no areal observation of storage exists at this scale.
- **Not validable:** a **map of zones that accumulate or lose water** inside the basin. Six or seven point wells and
  one outlet cannot confirm a spatial pattern. A spatial claim would be unsupported; this restricts the
  Explorer-visible product to a **basin-integrated time series with its uncertainty**.
- **Validable, partially:** the **timing and relative amplitude (rank, anomaly) of the groundwater state**, on wells
  that were **withheld from the fit**.

---

## 6. Target, hypotheses and candidate equations

**Reformulated target (proposal).** A **basin-integrated groundwater-storage anomaly index** `G(t)` (standardized,
no unit claimed), estimated from precipitation, potential evapotranspiration and discharge, optionally from satellite
soil moisture, and **judged only on withheld wells**. Physical interest: antecedent state for floods and droughts,
groundwater-sustained low flows. Not published by any input: discharge gives the outflow, wells give point heads,
satellites give the top centimetres.

**Candidate state-space (to be argued, not frozen).** Two linear reservoirs with potential-evapotranspiration forcing:

```
dS1/dt = P - a * PET * (S1 / S1max) - S1/tau1 - S1/tau12      (soil / fast layer)
dS2/dt = S1/tau12 - S2/tau2                                    (aquifer / slow layer)
Q      = S1/tau1 + S2/tau2          (observed, log-space noise)
SSM    = alpha + beta * S1          (optional, observed)
h_j    = c_j + d_j * S2             (wells; NOT used in estimation)
```

The ET term makes it non-linear in `S1`; a linearized or extended Kalman filter is a candidate, and the existing
filter and smoother are the building blocks. **Identifiability warning:** with `Q` alone `S2` is a rescaled baseflow
(section 1). The model earns its place only if `P`/`PET` (and `SSM` for `S1`) improve the prediction of withheld wells
beyond baseflow-based baselines.

**Hypotheses (draft).**

- **H1 - forcing adds information to discharge.** On withheld wells, `G` estimated from `{P, PET, Q}` has a higher
  anomaly correlation than `G` from `Q` alone, **by at least a pre-declared margin sized by the effective sample
  size** (section 4: ~0.2 is the order of magnitude detectable).
- **H2 - satellite soil moisture adds information.** Same comparison with `SSM`, over 2015-2025 only (SSM starts
  2014-10). Requires fleet 2 and an input that is not a judge.
- **H3 - the uncertainty is honest.** The stated predictive interval of `G` at withheld wells covers at its nominal
  rate (to be tested with block-bootstrap, given strong dependence).
- **Refutation.** If H1's margin is not met, the conclusion is "the forcing adds no detectable information about
  groundwater beyond discharge on this basin", which is a result. A basin where a Q-only baseline is near the
  ceiling (Cailly) is expected to *refute* H1 for lack of room, not for lack of merit; it is better used as a
  **positive control** for the pipeline than as the test of H1.

**Prior art risk.** Baseflow separation, SAFRAN-ISBA-MODCOU (SIM) and CAMELS-FR are established. "New information"
must be argued against them; whether the reconstruction beats them is **[NOT VERIFIED]** and is part of the protocol.

---

## 7. Draft pre-registrable protocol (unfrozen)

1. **Gate G1 - geometry (before any model). Not passed.** Keep wells **inside** the catchment boundary only;
   selection by geometry and data quality, **never by correlation**. Pass if >= 3 long wells in one aquifer body lie
   **certainly upstream**. The Topage network traversal (`experiments/basin_001_catchment.py`) did not clear any of the
   seven screened gauges (section 2): the elementary basins cannot be split at a gauge. A boundary that is exact at the
   gauge is required (a DEM-based delineation, or published station catchments), or a gauge sitting at the outlet of an
   elementary basin. The fallback "Cailly as positive control" of the first draft **no longer stands**: its wells are
   only "inside" under an upper bound.
2. **Gate G2 - forcing.** At least 2 open DPClim precipitation stations with >= 25 years within 25 km (the CSV must
   first be parsed: units, flag meaning, time basis not established). One order covers at most one year, so 25 years
   is 25 orders.
3. **Data usage.** Discharge, precipitation, PET (formula declared in advance) for the fit. Wells **never** enter the
   fit.
4. **Splits.** Leave-one-well-out and a chronological hold-out (fit on the first part of 1980-2026, test after);
   the split dates and the wells' roles are fixed in the document.
5. **Baselines (single-source).** Baseflow-filtered discharge; antecedent precipitation index; well climatology.
6. **Metrics.** Spearman correlation of monthly anomalies at each withheld well; improvement over each baseline.
7. **Inference.** Gains sized by the effective sample size with its cap sensitivity
   (`effective_sample_size_diagnostics`), block bootstrap with positions for gapped wells
   (`cusum_block_bootstrap` is for breaks; a paired block bootstrap of correlation differences is **not yet in
   `methods/`** and would be the one method to add), Bonferroni across wells.
8. **Decision rule and verdicts** written before the run: supported, not supported, inconclusive (power). Power is
   stated in terms of `n_eff` (about 22 to 75 independent months per series on the candidates).
9. **Leakage rules.** No well in the fit; no Q-derived baseflow used as both input and judge; EO products audited on
   the dependence ledger first; discharge-stage dependence at the gauge is HYDRO-001's finding and is read, not
   assumed.

---

## 8. What is missing, and decisions requested

**Not done in lot 1:** catchment boundaries; raw-evidence capture of Hub'Eau `obs_elab` / piezometry through the
acquisition foundation (no adapter); the DPClim CSV parser; precipitation stations near the candidates; EO pixel
values (fleet 2); the HYDRO-001 run (fleet 4); a national screen beyond seven departments; Hydroportail for the
catchment area and the discharge unit.

**Decisions for you.**
1. **Reformulation.** Accept the target as a basin-integrated *groundwater-anomaly index judged on withheld wells*,
   with no claim on absolute storage or on spatial maps (section 5.1)? Otherwise the Explorer deliverable
   ("click a basin, see zones that gain or lose water") has no available judge.
2. **Primary basin - gate G1 not passed on the 174 gauges.** Route (c) of the previous draft was executed: three
   gauges have an exact catchment and none has enough wells (section 3). The binding constraint is now the **wells**,
   not the geometry. Options, to be chosen by you: (a) **invert the search**: find where >= 4 long, recent wells of one
   aquifer body are clustered, then look for a gauge whose catchment contains them (this may point to departments
   outside the seven screened); (b) **extend the screen** to every department with a chalk or limestone aquifer
   (mechanical, slow); (c) **relax G1** (for example to 2 wells), which must be declared as a deviation because it is
   decided after seeing the data; (d) accept **larger catchments** (more wells inside, but heterogeneous aquifers and
   a heavier traversal). Brèche stays dropped (quality, fragmented wells).
3. **One new `methods/` primitive** (paired block bootstrap of a correlation difference) when the protocol is frozen.
4. **Third-party registration** for ISMN is a user action and only useful for a south-west basin; not requested now.
