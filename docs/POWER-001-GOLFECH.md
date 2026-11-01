# POWER-001 - Golfech: thermal headroom and limitation risk (first computed series)

> **Outcome (2026-11-01).** At Golfech the product is a function of the weather forecast: parked by the pre-declared forecast test
> (section 7); a five-season extension (7.1) finds a gain over the observed air temperature but none over the forecast itself; more
> atmospheric and hydrological variables bring no improvement (7.2). A price link exists but rests on the extreme summer of 2026 (7.3).
> The open question is national, not site-level (section 8). Pending the owner's decision.
>
> **Status: first computed series on one site, validated on one held-out season. Not a market product.** It follows the
> operating rule of 2026-11-01: one site, a defined quantity, accessible data, an executable method, an independent
> reference, and a computed series at the end. The result is mixed and is reported as it is (section 6).

**Evidence labels.** **[FACT]** measured on 2026-11-01. **[INFERENCE]** a reading of facts. **[NOT VERIFIED]** not checked.

**Reproduction.**

```bash
uv run python experiments/power_001_golfech.py data --cache DIR              # what the sources contain
uv run python experiments/power_001_golfech.py run  --cache DIR --out series.csv   # reconstruction, risk, validation
uv run python experiments/power_001_golfech.py forecast --cache DIR            # section 7: real archived forecasts, leads 3 and 7 days
uv run python experiments/power_001_golfech.py seasons  --cache DIR            # section 7.1: leave-one-season-out, 2022-2026
uv run python experiments/power_001_golfech.py extras   --cache DIR            # section 7.2: other atmospheric and hydrological variables
uv run python experiments/power_001_price_link.py --cache DIR                      # section 7.3: price link (Energy-Charts, no token)
```

Live network, key-free, read-only; about two minutes with a warm cache. Not part of the offline test suite.

---

## 1. The five conditions, assessed

| Condition | Verdict | Evidence |
|---|---|---|
| 1. A precisely defined target quantity | **Met** | Daily upstream-temperature allowance and daily probability of an environmental limitation, section 3 |
| 2. Data really accessible | **Met at one site only** | Section 2: Golfech; the plants with most events have no usable river temperature |
| 3. An executable reconstruction method | **Met**, with a weak first stage | Upstream temperature rebuilt with an error of 1.58 degC (target was 1.0) |
| 4. An independent validation reference | **Met, noisy** | EDF REMIT declarations; 17 events kept (18 declared, one withdrawn); the operator does not name the cause |
| 5. An identifiable economic use | **Not demonstrated** | Air temperature alone is as good (section 4); one day ahead is mostly already published by EDF (section 5); no price source was found open |

---

## 2. What the sources really contain [FACT]

| Source | What it gives | Limit found |
|---|---|---|
| EDF thermal limits (`opendata.edf.fr`, licence ouverte 2.0) | 51 rows of limits per plant, season and condition. Golfech: downstream < 28 degC (daily mean); warming < 1.25 degC from 1 June to 30 September, < 2 degC otherwise; 30 degC and 1.25 degC in exceptional climatic conditions | Limits only; the plant's own upstream station is not public |
| EDF unavailability history (REMIT) | 413 289 records since 2015, versioned, with cause, type, dates and available MW | The cause is a free text: "Causes externes liées à l'environnement". It does not say that it is river temperature |
| Environmental records by plant (nuclear, since 2015) | Saint-Alban 780, Bugey 449, Tricastin 299, Blayais 199, Chooz 146, Golfech 99, Fessenheim 73, Gravelines 47 (records, not events: each event has several versions) | |
| RTE (ODRE) | `production-nette-nucleaire`: **national aggregate** only, 224 975 readings since 2013 | No production per unit in open access: the validation uses EDF's declared available power instead |
| Hub'Eau river temperature | 873 stations. On the large cooling rivers only 15 have any data since 2018 | **None on the Rhône near Saint-Alban, Bugey or Tricastin**, the plants with the most events. Golfech: Garonne at Saint-Aignan (21 km upstream), **summers 2019 to 2023 only**, hourly, "non qualifié" |
| Hub'Eau discharge | Garonne at Lamagistère (at the plant), daily, 2018 onwards | Unit is litres per second (magnitudes fit the Garonne regime) |
| Air temperature | Open-Meteo archive (ERA5 reanalysis, ~25 km grid) | A reanalysis, not a site measurement |
| Archived forecasts by lead | Open-Meteo `previous-runs`, hourly `temperature_2m_previous_dayN`, values from mid-2021 | Used in section 7 |
| Electricity prices | Not found open (ODRE offers traded **volumes**) | **[NOT VERIFIED]**: day-ahead prices probably need an ENTSO-E or RTE token |

**Site choice.** Golfech is the only site that combines a cooling river with a public upstream temperature series, a public
discharge at the plant and a meaningful number of events (17 active events kept out of 18 declared, 2018-2026, of which 4 in the temperature window).

---

## 3. Quantities and protocol

**Quantities.** (1) `T_up_hat(d)`: upstream temperature **reconstructed** where there is no sensor (2018, 2024-2026, the cold
season), by least squares on the mean air temperature over 1, 7 and 21 days and the log discharge. (2) Allowance
`A(d) = min(warming limit, 28 - T_up_hat)` in degC. (3) Risk `R(d)`: probability that day `d` is a limitation day (logistic
regression), and the expected power at risk, `R(d)` times the mean power lost on a limitation day (1 067 MW in training summers).
A **limitation day** is a day covered by an event whose latest version is Active and whose text declares an environmental cause.

**Protocol, fixed in the script header before any model result was read:** stage 1 fits on 2019-2023, validated leave-one-year-out,
success if RMSE <= 1.0 degC in summer and better than climatology. Stage 2 trains on summers 2018-2025 and **tests on summer 2026**
(held out; 44 limitation days), with a 7-day moving-block bootstrap. If stage 1 fails, the primary features are the air temperature
and the discharge directly. Decision: GAIN if the 90 % interval of AUC(model) - max(AUC discharge, AUC air) is above 0.

**Deviations, recorded.**
1. The first run fed stage 2 with the reconstructed temperature although stage 1 had failed, against the protocol. It was corrected;
   the protocol branch (air and discharge directly) is the primary result, and the reconstructed-temperature models are reported as variants.
2. The lead-time test (section 4.3) was added **after** seeing the results. It is exploratory.
3. The output column for discharge was first mislabelled (litres per second shown as m3/s); fixed in the output only, the models are unaffected.

---

## 4. Results

### 4.1 Reconstruction of the upstream temperature [FACT]

Leave-one-year-out over 2019-2023, 1 June to 30 September: **RMSE 1.58 degC**, climatology baseline 2.13 degC, R2 0.586.
The pre-declared criterion (RMSE <= 1.0) is **not met**. The headroom is therefore uncertain by about +-1.6 degC.

### 4.2 Risk of a limitation day, held-out summer 2026 (122 days, 44 limitation days) [FACT]

| Predictor | AUC | 90 % block interval | Brier |
|---|---|---|---|
| **Model: air (7-day mean, 3-day change) + log discharge (primary)** | **0.961** | [0.904, 0.990] | 0.172 |
| Air temperature alone | **0.966** | [0.913, 0.993] | 0.165 |
| Discharge alone | 0.651 | [0.479, 0.786] | 0.300 |
| Seasonal frequency (day of year) | 0.815 | [0.648, 0.921] | 0.314 |
| Variant: reconstructed upstream temperature + discharge | 0.970 | [0.923, 0.994] | 0.164 |
| Variant: reconstructed upstream temperature alone | 0.962 | [0.909, 0.990] | 0.171 |

AUC(model) minus max(AUC discharge, AUC air) = -0.005, 90 % interval [-0.015, +0.002]: **NO_DEMONSTRATED_GAIN**. The model **is** a
useful signal (its own lower bound is 0.90, far above 0.5): the limitation days are the hot, low-flow days. **But the air
temperature alone gives the same ranking.** Nothing observed here is added by the river, the reconstruction or the regulatory physics.

### 4.3 Calibration and power at risk [FACT]

The ranking transfers; the **probabilities do not**. The base rate was 4.3 % of summer days in training and **36 %** in 2026.
Predicted risk against observed frequency by quartile: 0.00 to 0.00, 0.01 to 0.03, 0.10 to 0.50, **0.49 to 0.93**. Expected power
at risk in 2026: **159 MW/day against 472 observed**, an underestimate by a factor of three. Limitations at Golfech are also
increasingly frequent (limitation days: 4 in 2018, 9 in 2024, 15 in 2025, 44 in 2026), which is a change of regime or of operating
practice that a model trained on 2018-2025 cannot know.

### 4.4 The regulatory rule is not what binds [FACT]

With the rule encoded (downstream below 28 degC, warming below 1.25 degC), the allowance is below 1.25 degC on only **12 of 1 098
summer days (1.1 %)** and on only **7 of the 86 limitation days**. On limitation days the median reconstructed upstream temperature is
25.3 degC (21.1 degC on other summer days) and the median discharge 73 m3/s (107 m3/s). Limitations begin well before the headroom
formula signals anything: **[INFERENCE]** the plant's own heating, which depends on the flow, and the operator's anticipation, dominate,
and neither is observable from public data. The "Nuclear Cooling Constraint Headroom" as a rule-based margin is **not validated**.

### 4.5 Exploratory: onsets one to seven days ahead (not pre-declared) [FACT]

Among test days with no limitation active, the AUC for announcing a limitation `h` days later is 0.86 (h = 1, 4 onsets), 0.93
(h = 3, 11) and 0.87 (h = 7, 20). These onsets come from three to five episodes, are strongly autocorrelated, are not compared with
a baseline, and use the **observed** air temperature instead of a forecast: they are an upper bound and a reason to test further,
not a result.

---

## 5. Is it already known? EDF's own announcements [FACT]

Time between the first publication of a planned environmental limitation and its start, Golfech, 15 planned events among the 18 declared (one of them later withdrawn):
**median 23.8 hours**, maximum 54.5 hours, 7 of 15 published at least 24 hours ahead, **none at 72 hours or more**, three published
at or after the start. So:
- a **one-day-ahead** warning is mostly already public;
- a **three-to-seven-day** warning is not, and that is the only window where information could be new.

---

## 6. Reading and decision

**What holds.** A first computed series exists (3 206 days, 2018-2026: reconstructed upstream temperature, allowance, discharge,
limitation day, power lost, and the risk out of sample for 2026). The ranking of risky days generalises to a season never seen, with
a 90 % lower bound of 0.90.

**What does not.** (1) No gain over air temperature. (2) The probabilities and the MW at risk are badly calibrated under a regime
change. (3) The rule-based headroom does not explain the limitations. (4) Only one plant is observable with public data, and only
four of its seventeen kept events fall in the temperature window. (5) The link to prices is untested, and no open price source was found.

**Honest differentiation.** Today the product is "weather forecast mapped to a limitation likelihood". Traders and EDF already
use temperature forecasts, so the added value can only be a calibrated, earlier-than-EDF alert in the 3 to 7 day window, and it
depends entirely on the quality of real forecasts, which section 7 then tested.

The step proposed here was then run (section 7).

---

## 7. The real-forecast test (command `forecast`) [FACT]

**Protocol, fixed in the script header before any archived forecast was downloaded.** Alerts issued on day `d` about day `d + h`,
`h` = 3 and 7, with the Open-Meteo `previous-runs` archive (the forecast for a day, issued N days earlier; 1 958 days per lead
available from mid-2021). Population: issue days with no limitation active, so that persistence of an announced limitation cannot help.
Model: the logistic regression trained on 2018-2025 with perfect forecasts, applied in 2026 to the real-forecast features.
Baselines: observed air temperature at the time of issue (what is known without any forecast), and the seasonal frequency.
**GO at lead 3 days only if** (a) the model's own AUC bound is above 0.5, (b) the 90 % interval of AUC(model) minus AUC(baseline) is
above 0, (c) at least 3 of the 5 events of 2026 are alerted before EDF's first publication.

| Lead | Predictor | AUC, summer 2026 | 90 % block interval |
|---|---|---|---|
| **3 days** (78 issue days, 11 limitation targets) | **Model, real forecasts** | **0.953** | [0.897, 1.000] |
| | Model, perfect forecasts (upper bound) | 0.948 | [0.891, 1.000] |
| | Baseline: observed air at issue | 0.939 | [0.857, 0.990] |
| | Seasonal | 0.837 | [0.663, 0.954] |
| **7 days** (78 issue days, 20 limitation targets) | **Model, real forecasts** | **0.969** | [0.908, 1.000] |
| | Model, perfect forecasts (upper bound) | 0.985 | [0.952, 1.000] |
| | Baseline: observed air at issue | 0.869 | [0.737, 0.982] |
| | Seasonal | 0.859 | [0.672, 0.971] |

- **Lead 3:** AUC(model) - AUC(baseline) = +0.014, 90 % interval [-0.040, +0.084]: **(b) fails**. (a) holds (0.897). (c) holds: 4 of
  the 5 events were alerted before EDF's first publication (the fifth is not evaluable because a limitation was already active on the
  issue day).
- **Lead 7:** +0.100, interval [-0.040, +0.250]. Positive, not distinguishable from zero. It is not decisive by protocol.
- **The alert is selective, not a permanent warning** (descriptive, added after the results): at lead 3 it fires on 16 of 78 issue days and
  catches 10 of the 11 limitation targets (precision 0.62); at lead 7 it fires on 23 of 78 and catches 17 of 20 (precision 0.74).
- Real forecasts cost almost nothing against perfect ones at lead 3 (0.953 against 0.948) and a little at lead 7 (0.969 against 0.985).

**Pre-declared decision: PARK.** The forecast-based alert is accurate and does precede EDF, but at three days it is not better than
**watching the observed air temperature**, which everyone has. At seven days it may be better; one season and three episodes cannot say.

### 7.1 Five-season extension (post-hoc, requested after the PARK) [FACT]

Command `seasons`. Its protocol was fixed in the script header before it was run and it cannot overturn the lead-3 decision above:
leave-one-season-out over the summers 2022 to 2026 (train on every other year of 2018-2026, apply to the test season with real
forecasts; this checks generalisation across seasons, it is not a causal forecasting setup). Decision at lead 7: **REAL** if the 90 %
interval of the pooled AUC(model) - AUC(observed-air baseline) is above 0 **and** the difference is positive in at least 4 of 5 seasons.

| Lead | Season | Targets | AUC model | AUC observed-air baseline | Difference |
|---|---|---|---|---|---|
| 7 days | 2022 | 3 | 0.882 | 0.520 | +0.362 |
| | 2023 | 7 | 0.960 | 0.946 | +0.015 |
| | 2024 | 9 | 0.976 | 0.893 | +0.083 |
| | 2025 | 14 | 0.987 | 0.916 | +0.071 |
| | 2026 | 20 | 0.969 | 0.869 | +0.100 |
| | **pooled** | | **0.931** | **0.785** | **+0.146, 90 % interval [+0.080, +0.232]**, positive in 5 of 5 seasons |
| 3 days | **pooled** | | **0.932** | **0.844** | **+0.088, 90 % interval [+0.043, +0.152]**, positive in 5 of 5 seasons |

**Pre-declared verdict at lead 7: REAL.** Real forecasts beat the observed air temperature at the time of issue in every season.
The gain is not carried by 2022 alone (without it the lead-7 differences are +0.015 to +0.100; at lead 3 they are +0.010 to +0.111).
Alerts for 2022-2026: 14 events, 12 evaluable (the others had a limitation already active), 10 alerted at lead 3 and 9 at lead 7,
**all of them before EDF's first publication** (descriptive).

**The decisive descriptive check, added after the results.** The baseline in the protocol had no forecast, whereas anyone can read
the weather forecast. A baseline made of **the forecast temperature alone** (7-day mean, same training) gives a pooled AUC of 0.941
(lead 3) and 0.940 (lead 7). AUC(model) - AUC(forecast temperature alone) = **-0.009**, 90 % interval [-0.023, +0.002] at lead 3 and
[-0.016, -0.004] at lead 7; the model is ahead in 1 season of 5. **The REAL verdict is therefore a statement about the weather forecast,
not about the model**: discharge and the 3-day change add nothing, and slightly hurt.

### 7.2 Can our other atmospheric and hydrological variables beat the temperature? (command `extras`) [FACT]

An upper-bound test, fixed before it was run: observed variables (perfect forecasts), every summer day 2018-2026, leave-one-season-out,
reference model G = the 7-day mean air temperature alone. Candidates: A adds the wet-bulb temperature (the plant has cooling towers);
B adds wind and shortwave radiation; C replaces them with hydrology (log discharge, its 7-day change, its 30-day mean, and the
temperature x discharge interaction); D has everything. Decision on D only.

| Season (targets) | G air | A + wet bulb | B + wind, radiation | C + hydrology | D everything |
|---|---|---|---|---|---|
| 2018 (4) | 0.996 | 0.996 | 0.996 | 0.996 | 0.996 |
| 2020 (4) | 0.983 | 0.985 | 0.987 | 0.970 | 0.975 |
| 2022 (3) | 0.835 | 0.843 | 0.849 | 0.913 | 0.947 |
| 2023 (7) | 1.000 | 0.998 | 0.996 | 0.995 | 0.991 |
| 2024 (9) | 0.999 | 1.000 | 1.000 | 0.993 | 0.997 |
| 2025 (15) | 0.989 | 0.989 | 0.989 | 0.983 | 0.992 |
| 2026 (44) | 0.966 | 0.938 | 0.948 | 0.953 | 0.950 |
| **Pooled** | **0.943** | 0.946 | 0.946 | 0.936 | **0.960** |
| **Pooled - G, 90 % interval, seasons better** | | +0.002 [-0.026, +0.025], 4/7 | +0.003 [-0.025, +0.024], 4/7 | **-0.008** [-0.017, +0.002], 1/7 | **+0.017 [+0.002, +0.033], 2/7** |

**Pre-declared verdict on D: NO_IMPROVEMENT** (the interval is just above 0, but D is better in only 2 of the 7 seasons that hold
limitation days; the rule needed 5). Within a season the temperature alone already ranks the days almost perfectly (AUC 0.97 to 1.00 in
six seasons of seven): **there is no room left for more variables**. The wet bulb, wind and radiation add nothing; hydrology alone
slightly hurts. The pooled gain of D comes mostly from 2022 (3 limitation days), not from a consistent improvement.

### 7.3 Do environmental curtailments move the French day-ahead price? (`power_001_price_link.py`) [FACT]

**Data.** Day-ahead prices, zone FR, hourly, from the Energy-Charts API (licence returned by the API: **CC BY 4.0, Bundesnetzagentur
| SMARD.de**, to be credited if published). The ENTSO-E token was **not found in `.env`** (no variable of that name), so this open
republication was used. Curtailments: every nuclear unit with an environmental cause in the EDF REMIT history (564 active events kept),
summed per day in GW. Control: mean air temperature of Paris, Lyon and Toulouse.

**Protocol, fixed before any price was downloaded.** Summers 2018-2026; price = year-month fixed effect + b x GW lost + temperature +
weekend; Newey-West errors (7 lags). PRICE_LINK only if the 90 % interval of b is above 0, b >= 1 EUR/MWh per GW, and a placebo (the
curtailment 7 days later) has an interval containing 0.

| Summer | Days with a curtailment | Mean GW lost | Max GW | Mean day-ahead price (EUR/MWh) |
|---|---|---|---|---|
| 2018 | 23 / 122 | 0.17 | 2.2 | 53.5 |
| 2019 | 20 / 122 | 0.19 | 3.8 | 34.0 |
| 2020 | 36 / 122 | 0.28 | 2.0 | 35.8 |
| 2021 | 1 / 122 | 0.01 | 0.7 | 90.9 |
| 2022 | 26 / 122 | 0.20 | 2.5 | 385.1 |
| 2023 | 8 / 122 | 0.09 | 1.8 | 87.1 |
| 2024 | 12 / 122 | 0.21 | 3.0 | 47.8 |
| 2025 | 30 / 122 | 0.37 | 3.3 | 47.1 |
| **2026** | **87 / 122** | **4.22** | **12.9** | **106.9** |

| Specification | b (EUR/MWh per GW) | 90 % interval |
|---|---|---|
| **All summers (decision)** | **+2.49** | **[+0.15, +4.82]** |
| Placebo: curtailment 7 days after | -1.72 | [-3.75, +0.31] |
| All summers, quadratic temperature (after the result) | +2.48 | [+0.11, +4.85] |
| Without 2026 (after the result) | **-5.15** | [-11.72, +1.42] |
| 2026 only (after the result) | **+3.16** | [+0.98, +5.34] |

**Pre-declared verdict: PRICE_LINK.** **But it rests entirely on summer 2026**, in which the curtailments were 10 to 40 times the usual
level (87 of 122 days, 4.2 GW on average, 12.9 GW at the peak). In the eight other summers the estimate is negative and
indistinguishable from zero. In 2026 the implied effect is about 13 EUR/MWh on average (12 % of the 106.9 mean price) and about 41
EUR/MWh at the peak. This is a **contemporaneous** effect: the day-ahead price already contains what had been announced, and nothing
here says whether the market anticipated it. No gas or carbon price was available; the fixed effects absorb only their monthly mean.

### 7.4 National model and "already in the price?" (`experiments/power_001_national.py`) [FACT]

Protocol fixed in the script docstring before any new data was downloaded. Summers 2022-2026, three cities (Paris, Lyon,
Toulouse), archived forecasts, leave-one-season-out, prices from ENTSO-E (cross-checked with Energy-Charts: median absolute
difference 0.00 EUR/MWh over 563 days, one day differing by 33.85).

**T1, can the GW lost per day be predicted from public forecasts?** Event = more than 1 GW lost.

| Lead | AUC model | AUC no forecast (B) | AUC forecast temperature alone (G) | model - B (90 %) | model - G (90 %) |
|---|---|---|---|---|---|
| 3 days | 0.759 | 0.750 | 0.772 | +0.009 [-0.016, +0.028] | -0.014 [-0.026, -0.006] |
| 7 days | 0.707 | 0.591 | 0.730 | +0.116 [+0.055, +0.190] | -0.023 [-0.036, -0.014] |

The model's own 5 % bound at lead 3 is 0.670, under the 0.75 required. **Pre-declared verdict: NO_NATIONAL_SIGNAL.** The three-city
model does not beat the national forecast temperature alone (G) at either lead: the forecast adds to a no-forecast baseline at
7 days, but a plain temperature forecast does at least as well as the model. Per season the AUC is very uneven (0.55 in 2022,
0.98-0.99 in 2023-2024), because the events are few outside 2026.

**T2, does the price react to the predictable but unannounced part?** Price on the loss announced before the auction (known) and
on the loss predicted h days earlier (pred), year-month fixed effects, Newey-West, n = 563.

| Lead | known (EUR/MWh per GW) | pred (EUR/MWh per GW) |
|---|---|---|
| 3 days | +3.44 [-2.22, +9.10] | +1.71 [-9.18, +12.59] |
| 7 days | +3.67 [-2.00, +9.34] | +0.23 [-9.03, +9.49] |

The pre-declared label is "not anticipated", but the intervals are so wide (about +/-10 EUR/MWh per GW) that the test **cannot tell**
"not priced" from "priced": it has almost no power. Even the announced loss is not distinguishable from zero once the temperature
forecast is controlled. This is a null by lack of power, not a demonstration.

**Verdict.** The stop rule was: if the predicted GW does not explain the price beyond the announced curtailments and the temperature
forecast, park POWER-001 for good. It does not. There is no national forecast signal beyond the public temperature forecast, and
the price test cannot show an edge. Proof of any edge would in any case need forward prices, which are not open.

---

## 8. Decision and what it teaches

**POWER-001 at Golfech stays parked**, pending the owner's confirmation. Two readings, both true, and the second decides:
1. *Against the protocol's baseline* (no forecast), real forecasts give a real, consistent gain: pooled +0.146 at 7 days, positive in
   5 of 5 seasons, verdict REAL (section 7.1).
2. *Against the weather forecast itself*, which anyone reads, the model adds nothing and slightly loses (-0.009, interval entirely
   below 0 at 7 days). The signal generalises across five seasons and it is **the weather**, not the river, the discharge or the
   regulatory physics. A product that is a monotone function of a public forecast is not differentiating.

What remains of value is the **mapping**: which forecast temperature level goes with a limitation at Golfech, and how that level has
moved (4, 9, 15 and 44 limitation days in 2018, 2024, 2025 and 2026). It is a calibration of a public variable, not new information, and
it is not stable (the base rate rose ninefold).

**What the two later tests add (sections 7.2 and 7.3).**
- *Can our hydrological and atmospheric information improve it?* **No, at Golfech.** The temperature already ranks the days of a season
  almost perfectly (AUC 0.97 to 1.00); wet bulb, wind, radiation and hydrology add nothing (NO_IMPROVEMENT). There is no room left in the
  within-season ranking. What is left to improve is the **level** (calibration drift) and the **scale**.
- *Is there an economic link?* **Yes, in one summer.** Declared environmental curtailments moved the day-ahead price by about 3 EUR/MWh
  per GW in 2026 (about 13 EUR/MWh on average, 41 at the peak), and by an undetectable amount in the eight other summers, when the
  curtailments were small. The link exists where the exposure is large.

**Where this leaves the product.** The exposure that moves prices is **national** (several GW, mostly the Rhône plants), not
Golfech's 2.6 GW. And because a limitation is a function of the weather forecast, a national alert does **not** need a river
temperature, which the Rhône plants lack: it needs the weather forecast, the plants' own history of limitation days, and the
price. So the next question, if one is asked, is not "a better Golfech model" but:

1. *National model:* predict the GW lost per day at lead 3 to 7 days from the public weather forecasts, pooled across plants,
   leave-one-season-out (many more events than Golfech's 17).
2. *Priced in?* Does that predicted GW, issued 3 to 7 days before, explain the day-ahead price **beyond** what is already announced
   (REMIT messages, median lead 24 h) and beyond the temperature forecast? That is the only place where information could be new and
   still unpriced. Exposure outside 2026 is weak, so the power of this test is limited and must be stated before it is run.

**Stop rule proposed.** If the predicted GW does not explain the price beyond the announced curtailments and the temperature forecast,
park POWER-001 for good: the product would be a function of public information, with a real price effect only in extreme summers.

**Lesson for the next mission.** Before choosing a target, ask what in it is **not** already a function of a public variable.
Here the answer was "very little", and it could have been seen in one hour: the limitation days were the hot, low-flow days.

## 9. Not done

The national model and the "priced in" test (section 8); a plume or mixing model of the plant's heat discharge (its heat flux to the
river is unknown); production per unit; the Opportunity Detector. Gas and carbon prices were not available, so the price regressions
cannot separate a curtailment effect from a fuel-price effect inside a month. The plant coordinates used to fetch the air temperature
are approximate (+-0.02 degrees).

## 10. Files

- `experiments/power_001_golfech.py` (new): commands `data`, `run`, `forecast`, `seasons`, `extras`
- `experiments/power_001_price_link.py` (new)
- `docs/POWER-001-GOLFECH.md` (new)

The computed series is written by the script to the path given with `--out`; it is not stored in the repository. No existing file was modified.
