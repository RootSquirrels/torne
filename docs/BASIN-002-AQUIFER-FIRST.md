# BASIN-002 - Aquifer-first candidate discovery

> **Decision recorded 2026-11-01 (project owner): the line of work is PARKED.** No pilot, no multi-zone design, no model. What
> follows is the evidence behind that decision; section 8 lists what is reusable if it is ever reopened.
>
> **Status: discovery report.** It searches for French catchments that meet the ORIGINAL BASIN-001 gate G1,
> starting from the groundwater monitoring network instead of the gauges. It builds no model, changes no shared
> contract, and computes **no correlation** between wells and discharge, so nothing in it can be mistaken for
> confirmation. The one rank-correlation test it contains (section 7.1) checks the **economic** premise, not the hydrology,
> with a rule fixed beforehand, run on two basins and reported separately. Its recommendation is at the end (section 8):
> **no single-basin pilot**; the economic question needs a multi-zone design, which is the owner's decision.

**Evidence labels.** **[FACT]** measured by the script on 2026-11-01. **[INFERENCE]** a reading of facts.
**[NOT VERIFIED]** not checked, with the way to check it.

**Reproduction.**

```bash
uv run python experiments/basin_002_aquifer_first.py inventory --cache DIR     # section 3
uv run python experiments/basin_002_aquifer_first.py check-network --cache DIR # section 4: same catchments as BASIN-001
uv run python experiments/basin_002_aquifer_first.py candidates --cache DIR --workers 8
uv run python experiments/basin_002_aquifer_first.py shortlist --cache DIR     # sections 5-6
uv run python experiments/basin_002_restriction_test.py --orders-dir DIR       # section 7.1 (needs the VigiEau yearly files)
uv run python experiments/basin_002_restriction_test.py --orders-dir DIR --case raille   # section 7.2
```

Live network, key-free, read-only. A first run downloads about 880 Sandre tiles (roughly 10 minutes with 8 workers) and
screens 1 377 gauges (about 8 minutes); the delineation itself then takes about 5 minutes. `DIR` caches everything, so a
second run is quick. It is not part of the offline test suite.

---

## 1. Rules, and what was not changed

**Unchanged from BASIN-001 [FACT]:** a well qualifies with at least 3 000 values, a record starting on or before
2005-01-01 and ending on or after 2024-01-01. A gauge qualifies with at least 25 years of daily mean discharge, 90 %
completeness since its first value, and at least 330 days with a value in 2025 (types `STD` and `DEB`, in service).
Catchments come from the Sandre BD Topage network with the BASIN-001 outlet logic; a well counts only when it lies
**certainly upstream** (in a member basin other than the gauge's own, or anywhere in the catchment when the gauge
sits at the outlet of its basin).

**Changed as requested:** at least **4** wells of the **same groundwater body** instead of 3. G1 was not weakened.

**Measures added, reported and flagged only (they never admit a candidate the rules reject):** pairwise distances,
BDLISA agreement, completeness and share of `Correcte` values over the common window, discharge quality flags.
Flag thresholds (80 % complete, 90 % `Correcte`, wells clustered if the median pairwise distance is under 3 km, area
above the 112-480 km2 of BASIN-001) were fixed in the script before the shortlist was produced.

**Two computational limits that shape the scope [FACT], both stated rather than hidden:**

1. **Pruning radius of 30 km.** A gauge is examined only if at least 4 wells of one body lie within 30 km of it. This is
   derived from the size scope (a catchment of a few hundred km2 cannot hold wells farther apart), not a search around a
   gauge for wells. It can only miss very elongated catchments.
2. **Size cap of 1 500 reaches.** Larger catchments are not delineated. This excluded **132 of 391** gauges (34 %),
   which are the large rivers. The brief forbids enlarging catchments to find wells, so these were left out, not rescued.

---

## 2. Sources

| Need | Source |
|---|---|
| Piezometers | Hub'Eau `niveaux_nappes/stations` (all metropolitan departments) and `chroniques` (candidate wells only) |
| Groundwater body | `codes_masse_eau_edl` (a well with exactly one body is used; with several, ambiguous, it is not); `codes_bdlisa` as a cross-check |
| Gauges and discharge | Hub'Eau `hydrometrie/referentiel/stations` and `obs_elab` (`QmnJ`) |
| Catchments | Sandre BD Topage 2022 WFS: reaches (`TronconHydrographique`) and elementary basins (`BassinVersantTopographique`) |

---

## 3. Aquifer-first inventory [FACT]

| Step | Count |
|---|---|
| Piezometers in metropolitan France | 22 754 |
| Meet the original well criteria | **1 643** |
| ...without a groundwater body | 57 |
| ...with several bodies (ambiguous, not used) | 27 |
| Groundwater bodies holding qualifying wells | 358 |
| **Bodies with at least 4 qualifying wells** | **121** |
| Zones of at least 4 wells of one body within 30 km | 107 |

Spatial coverage, per body: for each of the 121 bodies the script prints the number of wells, the number of zones, the
median and maximum pairwise distance, the BDLISA agreement and the departments. Large bodies span hundreds of
kilometres (the Alsace aquifer: 105 wells, median pairwise 42 km); several are tightly clustered (the Chaîne des Puys
volcanic body: 9 wells, median 2.2 km). Many bodies are **alluvial** (Adour, Durance, Loire, Tarn, Crau), whose water
is exchanged with the river rather than stored apart from it: the rules admit them, and section 5 flags where this matters.

**Reading [INFERENCE].** Starting from the aquifers finds what starting from the gauges could not: 121 bodies have at
least 4 long, recent wells. The binding question moves to whether a **gauged catchment** contains them.

---

## 4. Catchments: the tile-based network reproduces BASIN-001 [FACT]

The per-reach WFS method of BASIN-001 took about 3 minutes per gauge. The script loads the network by 0.25 degree tiles and
traverses it in memory with the same rules. On the five gauges delineated in BASIN-001 it gives **identical** reaches,
basins and areas:

| Gauge | BASIN-001 | BASIN-002 network |
|---|---|---|
| Seulles at Tierceville | 835 / 9 / 264 km2 | same |
| Seulles at Juvigny | 514 / 5 / 133 km2 | same |
| Cailly at Fontaine-le-Bourg | 29 / 1 / 244 km2 | same |
| Aure at Maisons | 453 / 3 / 132 km2 | same |
| Brèche at Nogent-sur-Oise | 531 / 3 / 480 km2 | same |

---

## 5. Gauge funnel and shortlist [FACT]

| Step | Count |
|---|---|
| Gauges in service (`STD`, `DEB`) | 3 900 |
| With at least 4 wells of one body within 30 km | 1 377 |
| Pass the original hydrometric criteria | **391** |
| Delineated | 259 (132 above the size cap) |
| ...of which the gauge sits at its basin outlet (within 1 km) | 18 |
| **Candidates: at least 4 wells of one body certainly upstream** | **6** |
| Unresolved: 4 or more only if the gauge's own basin is taken whole | 5 (not candidates) |

**Delineated areas (upper bounds):** minimum 14, median 239, maximum 2 237 km2.

### 5.1 The six candidates

Sorted by the area upper bound. No candidate has an exact outlet: for all six the stream stayed in the gauge's own basin
for more than 1 km (the walk stops there; the true distance is unknown), so the area is an **upper bound**. The wells
counted are the ones certainly upstream, so qualification does not depend on that.

| Gauge | Area (ub) | Body | Wells | Pairwise km (min/med/max) | Common window | Wells >= 4 simultaneously | Well completeness | Discharge |
|---|---|---|---|---|---|---|---|---|
| **Thur at Pulversheim** (A146020302) | 449 km2 | Alsace aquifer (CG101) | 4 | 3.4 / 12.3 / 17.6 | 1982-2025, 42.6 y | 52 % | 0.58-0.63 | 25.0 y, 4.9 % doubtful |
| **Raille at Beaufort** (V342431001) | 634 km2 | Bièvre-Valloire alluvium (DG303) | 4 | 9.6 / 14.3 / 27.8 | 1992-2026, 34.3 y | 58 % | 0.74-0.81 | 47 y, 4.8 % doubtful |
| **Yèvre at Savigny-en-Septaine** (K555230001) | 722 km2 | Upper-Jurassic limestone, Yèvre (GG077) | 6 | 4.0 / 15.1 / 25.1 | 2000-2026, 25.9 y | **99 %** | **0.95-0.99** | 30 y, 1.6 % doubtful, 99 null |
| **Bresle at Ponts-et-Marais** (G017042010) | 752 km2 | Chalk, Eaulne-Bresle (HG204) | 4 | 4.6 / 16.1 / 31.8 | 1974-2026, 52.8 y | 35 % | 0.39-0.53 | 27 y, 4.0 % doubtful |
| **Bédat at Saint-Laure** (K277312001) | 804 km2 | Chaîne des Puys volcanic (GG099) | 8 | 0.2 / 2.3 / 11.2 | 1995-2026, 31.4 y | 59 % | 0.55-0.77 | 26 y, 7.1 % doubtful, 47 % validated |
| **Conie at Conie-Molitard** (M107302001) | 1 480 km2 | Séno-Turonian chalk and Beauce limestone, free (GG092) | 7 | 6.4 / 23.9 / 42.8 | 1994-2026, 32.0 y | 91 % | 0.74-0.94 | 30 y, 0.5 % doubtful |

### 5.2 Assessment, candidate by candidate [INFERENCE from the flags]

- **Yèvre at Savigny-en-Septaine - best on data quality.** Six wells of one limestone body, spread over 4 to 25 km, 95-99 %
  complete, at least 4 observed together on 99 % of the days over 25.9 years; discharge 30 years, 97 % complete, 1.6 % doubtful,
  but 99 null values. Weaknesses: area 722 km2 (an upper bound); the common window starts in 2000, so the record is
  shorter than in the chalk basins.
- **Conie at Conie-Molitard - strongest economic setting, weakest hydrology.** Seven wells, good coverage and quality,
  best discharge. But the basin has **127 reaches over 1 480 km2** (0.09 per km2; 1 to 2.5 elsewhere): a plateau with
  almost no surface network, in the Beauce aquifer, where the topographic catchment is a poor proxy for the groundwater
  catchment. Regarded as high risk, not as a first pilot.
- **Raille at Beaufort.** Four wells of an **alluvial** body, 74-81 % complete, long discharge (47 years). River-aquifer
  exchange dominates; the 4.8 % doubtful discharge and the 634 km2 bound are further limits.
- **Thur at Pulversheim.** The Alsace aquifer is a large, intensively managed alluvial system; wells 58-63 % complete in the
  window, barely 25 years of discharge, the gauge sits in a regulated plain. Weak.
- **Bresle at Ponts-et-Marais.** Chalk, 52.8-year window, but the wells are only 39-53 % complete and simultaneous
  coverage is 35 %; local-influence code 2 (meaning not verified). Weak on quality.
- **Bédat at Saint-Laure.** Volcanic aquifer, eight wells but **clustered** (median 2.3 km), one well with only 54 % `Correcte`
  values, discharge with 7.1 % doubtful and only 47 % validated. Weak.

### 5.3 The five unresolved cases

La Boutonne at Saint-Séverin (1 certain, 4 possible), Le Thérain at Beauvais (3 + 1), La Selle at Plachy-Buyon (0 + 4), L'Essonne at
Boulancourt (2 + 2), Le Bédat at Cébazat (0 + 6). They reach 4 only if the part of the gauge's own basin downstream of the gauge
is counted, which cannot be established. They are **not** candidates.

---

## 6. Uncertainties and selection effects

- **Area is an upper bound for all six.** No candidate gauge sits at the exit of its elementary basin; the true catchment is smaller.
  Five of the six exceed the 480 km2 maximum of BASIN-001, though the brief does not allow enlarging catchments to gain wells; they
  were not enlarged, they were found at this size.
- **Topographic is not hydrogeological.** The catchment is surface drainage. For karstic, plateau or alluvial settings (Conie, Raille,
  Thur) the groundwater basin can differ markedly. This is the main scientific risk.
- **Size cap removes the large rivers (132 gauges).** A conclusion "no candidate" would not have meant no basin: the scope is catchments
  below roughly 1 500 reaches.
- **Groundwater-body attribution.** Wells with several bodies (27 nationally) were excluded; attribution confidence is reported as BDLISA
  agreement (0.75-1.0 on the candidates). A body is an administrative (EDL) unit, not a guarantee of hydraulic continuity.
- **Qualification is on metadata for the national pass** (value count, first and last date), then on the actual series for the
  candidates; between the two, a well can have a long record with long internal gaps (Bresle: 39-53 % complete).
- **Gauge-side bias.** The 391 are those with 25 years and 90 % completeness: long-lived, well-maintained gauges.
- **Discovery, not confirmation.** The candidates were selected on counts, geometry and data quality only. No correlation between wells
  and discharge was computed. Correlations seen in BASIN-001 concern other basins and must not be read as support for these ones.

---

## 7. Economic relevance gate

A scientifically feasible pilot is not justified by feasibility alone. The chain, with what each link would need:

```
groundwater observations (wells of the candidate)
  -> basin-scale groundwater anomaly index G(t)
  -> expected groundwater availability and low-flow state for the coming weeks or months
  -> the water-resource constraint (drought alert level, restriction of withdrawals)
  -> affected activity: irrigation, industrial abstraction, drinking-water supply
```

**What exists already [per web search; sources not read in full, so NOT VERIFIED in detail]:**

- A **standardized piezometric indicator (IPS)** is used in regional drought and low-water bulletins (DREAL, with the BRGM). Whether a
  national open monthly series exists was not established.
- **Restrictions are triggered by observed thresholds.** The framework orders (arrêtés-cadres) fix flow thresholds and piezometric levels at
  designated reference stations and wells, in four levels (vigilance, alert, reinforced alert, crisis); the restriction orders follow, and
  VigiEau displays them. The trigger **is already a public groundwater observation**, so a reconstructed index adds nothing at the moment of
  decision.
- **Who is exposed:** withdrawal data (BNPE) show irrigation, industry and drinking water, but the sources found disagree on the shares
  (irrigation 7 % to about 10 % of volumes, about half of the withdrawal points); no usable share is stated here.

**Added value, if any, can only be:**
1. **Lead time** before the public thresholds are crossed: groundwater has memory (BASIN-001 measured about 22 to 75 independent months in
   40-50 years of monthly series), so an index at the end of winter recharge could estimate the risk of an alert level months ahead. That is
   the economically useful quantity (irrigation planning, crop choice, supply contracts), and it is what is **not** published.
2. **Spatial coverage** where no reference well exists: unproven, and limited by the 4-well design.
3. **A quantity rather than a threshold:** translating level into available volume needs the specific yield, which the matrix of BASIN-001 found
   unavailable. Not offered.

### 7.1 The pre-pilot test was run [FACT]

**Data.** The VigiEau yearly order files `arretes-2012.csv` to `arretes-2024.csv` and `arretes-cadre.csv` (14 files, 8 504 773 bytes,
data.gouv.fr "Donnée Sécheresse - VigiEau", licence ouverte 2.0), downloaded with the owner's approval into the session's temporary
folder, outside the repository. History is available for 2012-2024 as yearly CSV files; the framework orders' numeric thresholds are in
PDFs and are **not** in the CSV.

**What the data show before any statistic.** In the **Cher (department 18), every alert zone is a surface-water zone**: 1 121 `SUP` entries
and a single `SOU` entry ("zone not covered by the framework order", 2019). Restrictions there are triggered by flows, **not by
groundwater levels**. Groundwater zones exist elsewhere: Isère 452 entries over 11 years, Loiret 145 over 6, Seine-Maritime 53, Somme
41, Puy-de-Dôme 31, and almost none in Eure-et-Loir (5) and Haut-Rhin (1).

**Protocol, fixed in `experiments/basin_002_restriction_test.py` before any result was read.** Outcome: days between 1 June and
30 September at level "alerte" or above in the Yèvre alert zones, 2012-2023 (12 summers). Predictors known on 31 March: the mean
standardized March level of the six counted wells (W), and the standardized March discharge of the Yèvre gauge (Q). Statistic:
s = -Spearman rho, 90 % bootstrap interval, permutation p-value. Decision rule: baseline suffices if the interval's lower end is >= 0.8;
premise unsupported if its upper end is < 0.5; room if 0.5 <= s < 0.8 with p < 0.05; otherwise inconclusive.

| Predictor | Outcome | s | 90 % interval | p (permutation) | Verdict |
|---|---|---|---|---|---|
| **W (wells)** | **days at or above alerte (primary)** | **+0.42** | [-0.15, +0.88] | 0.178 | **INCONCLUSIVE** |
| W (wells) | highest level reached | +0.53 | [+0.10, +0.84] | 0.075 | inconclusive |
| Q (gauge) | days at or above alerte | +0.39 | [-0.19, +0.84] | 0.203 | inconclusive |
| Q (gauge) | highest level reached | +0.51 | [+0.09, +0.80] | 0.090 | inconclusive |

**Reading.**
- The **primary verdict is INCONCLUSIVE**. Twelve summers cannot separate a moderate relation (s of about 0.4 to 0.5) from a strong one
  (the interval reaches 0.88) nor from none (it reaches -0.15). The lead-time premise is **neither confirmed nor refuted**.
- **The wells add nothing visible beyond the public gauge.** The two predictors rank the 12 years almost identically
  (Spearman 0.99), and the gauge predicts as well as the wells (0.39 against 0.42; 0.51 against 0.53). At this annual resolution an
  index of the same state would have to beat the public March discharge, not only a well.
- **The summers that matter are not announced by March.** 2017 (69 days at alert) and 2020 (77 days) followed ordinary March levels
  (z of +0.33 and +0.58), while 2016 (z of +1.43) had no restriction at all. Summer weather and regulation drive the outcome as well as
  the stored water.
- **Caveats:** 12 points; the 2021-2022 reform changed the framework orders and zone codes; the outcome is regulatory as well as
  physical; 2024 is excluded because the Cher has no order in that file, so absence cannot be told from an incomplete file; the outcome
  is for the Yèvre zones of the Cher only.

**Gate verdict (updated).** *Not met for the Yèvre.* The chain is explicit and the exposed activities exist, but in the Cher the
restriction trigger is surface flow, the wells carry no information that the public gauge does not, and the one test possible on the
available history is inconclusive. The economic case for a pilot is **not supported**.

### 7.2 The Isère (Raille at Beaufort), a second test on a department that restricts on groundwater [FACT]

**Protocol.** The same test and the same decision rule, run **once**, on the one candidate department where groundwater zones exist. The
choices below were fixed in `experiments/basin_002_restriction_test.py` (case `raille`) after seeing only the **structure** of the
Isère files (zone names, types, years present), never a level against a predictor:
- Outcome: days between 1 June and 30 September at level "alerte" or above in any zone whose name contains "Bièvre" or "Valloire",
  of any type (groundwater zones carry that name only from 2016; before, the same territory was managed through surface zones).
  Years 2012-2024 (13 summers; the Isère has orders in the 2024 file, so a missing year can be read as no restriction).
  A secondary outcome restricted to groundwater (`SOU`) zones, 2016-2024.
- Predictors: the four wells counted for the Raille candidate (at least 3 with data), and the March discharge of gauge V342431001;
  z-scores against 1993-2025.
- One rule added for every case: fewer than 9 usable years gives NOT_TESTABLE. The Yèvre case was re-run after the change and
  reproduces its numbers exactly.

| Predictor | Outcome | s | 90 % interval | p (permutation) | Verdict |
|---|---|---|---|---|---|
| **W (wells)** | **days at or above alerte (primary)** | **+0.61** | [+0.17, +0.86] | **0.030** | **ROOM** |
| W (wells) | highest level reached | +0.65 | [+0.22, +0.90] | 0.018 | room |
| Q (gauge) | days at or above alerte | **+0.70** | [+0.35, +0.92] | 0.010 | room |
| Q (gauge) | highest level reached | +0.66 | [+0.22, +0.91] | 0.015 | room |
| W (wells) | days, groundwater zones only (n = 9) | +0.61 | [+0.08, +0.95] | 0.085 | inconclusive |
| Q (gauge) | days, groundwater zones only (n = 9) | +0.41 | [-0.21, +0.86] | 0.270 | inconclusive |

**Reading.**
- **The premise holds here, modestly.** A low March level (wells or flow) goes with more summer days under restriction: s of about
  0.6 to 0.7, intervals that exclude zero. The pre-declared primary verdict is **ROOM**: a signal exists and is not saturated.
  Caution on the p-value: 0.030 is for one test; two basins were tested in total (Yèvre, Isère), which gives about 0.06 after a
  Bonferroni correction.
- **The public gauge predicts at least as well as the wells** (0.70 against 0.61). The signal is real and is already carried by
  the March discharge that anyone can read. "Room" means the crude well baseline does not saturate, not that an index adds anything.
- **Here the two predictors differ** (rank correlation 0.50, against 0.99 in the Cher). The disagreements are informative: in 2018
  the wells were the lowest of the 13 years but the flow was above the median (49 days at alert); in 2022 the wells were above the
  median and the flow among the lowest (120 days). A combination might carry more than either, but 13 summers cannot test that.
- **The summers that matter are the recent, heavily restricted ones:** 2022 (120 days) and 2023 (122 days) dominate the outcome; the
  framework orders and zone codes were reorganised in 2022-2023.
- **Caveats:** 13 points; 2013 and 2014 have no order at all and are read as zero (both had high March levels, so plausible, but
  absence cannot be told from missing data); the aquifer is alluvial; the catchment area is an upper bound.

**Gate verdict (updated).** *Partly met for the Isère, not met as an increment.* The lead-time premise is supported in the one
department where groundwater is a trigger, but a public indicator already carries it. The open history (2012-2024) is **13 summers**,
so no single-basin pilot could confirm that an index improves on the March gauge or the March reference well: with an interval of about
+-0.35, an improvement of 0.1 to 0.2 in s is not detectable.

---

## 8. Recommendation

**Do not build a model and do not open a single-basin pilot. Decide whether to change the design, or park the line.**

1. **Park the Yèvre pilot.** The Cher restricts on surface flow, the wells add nothing visible to the public gauge, and the test is
   inconclusive on 12 summers (section 7.1).
2. **Do not open a pilot on the Raille either.** The Isère supports the premise (s of about 0.6 to 0.7), but the public March gauge
   predicts at least as well as the wells, the science is weaker (alluvial aquifer, wells 74-81 % complete, 634 km2 upper bound,
   4.8 % doubtful discharge), and the 13 summers of open history can never confirm an increment over the gauge (section 7.2).
3. **The only design that could settle the economic question is multi-zone, and it is a different project.** Groundwater alert zones
   exist in several departments (Isère 452 `SOU` entries, Loiret 145, Seine-Maritime 53, Somme 41, Puy-de-Dôme 31). Taking each zone
   and year as a unit would give on the order of a hundred points instead of 13, enough to test whether a reconstructed index beats the
   March gauge and the March reference well. It needs the alert-zone geometries (Sandre), wells and gauges assigned per zone, and a
   protocol written before any result. It is not authorised by this brief ("do not expand the search"), so it is the owner's decision.
4. **The Conie is the strongest economic setting but not a pilot.** Its topographic catchment has 0.09 reaches per km2 on a karstic
   plateau; the Loiret has groundwater zones, Eure-et-Loir almost none.
5. **If the line is parked,** BASIN-002 leaves reusable assets: the national well inventory by groundwater body, the tile-based
   Topage network that reproduces the BASIN-001 catchments, and a restriction-history test harness. None of it is a result about
   groundwater, and no model or shared contract was touched.

---

## 9. Files changed by this task

- `experiments/basin_002_aquifer_first.py` (new)
- `experiments/basin_002_restriction_test.py` (new; run with `--orders-dir` pointing to the VigiEau yearly files)
- `docs/BASIN-002-AQUIFER-FIRST.md` (new)

The 14 downloaded VigiEau files live in the session's temporary folder, not in the repository.

No existing file was modified. `experiments/basin_001_catchment.py` and `experiments/basin_001_screening.py` are imported, not edited.
Nothing was staged or committed.
