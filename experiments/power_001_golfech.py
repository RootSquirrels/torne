"""POWER-001 - first computed series: thermal headroom and limitation risk at the Golfech nuclear plant.

First Knowledge Product attempt under the "production" rule: one site, a defined quantity, accessible data, an
executable method, an independent reference. It ends with computed daily series and a validation, not a dossier.

SITE AND RULES
    Golfech (2 units, 1 310 MW each, cooling towers), on the Garonne. Rules from the regulatory dataset published by
    EDF ("Seuils et limites des rejets thermiques"): downstream temperature below 28 degC (daily mean), warming
    below 1.25 degC from 1 June to 30 September and below 2 degC from 1 October to 31 May; 30 degC and 1.25 degC
    under "exceptional climatic conditions".

DATA, as found (this shaped the protocol)
    Upstream water temperature: Hub'Eau 05152000 "La Garonne a St-Aignan", ~21 km upstream of the plant. It exists
    ONLY for the summers 2019 to 2023 (hourly, "non qualifie"). The plant's own upstream station is not public.
    Discharge: Hub'Eau O614001001 "La Garonne a Lamagistere", at the plant, 2018 onwards.
    Air temperature: Open-Meteo archive (ERA5 reanalysis, ~25 km grid), 2018 onwards.
    Reference: EDF REMIT unavailability history; a LIMITATION DAY is a day covered by an event whose text declares an
    environmental external cause, taking the latest version of each identifier and keeping it only if that version is
    Active (an Inactive latest version is a withdrawn event). The operator does not say that the cause is river
    temperature: the label is INDEPENDENT of the inputs but NOISY.

QUANTITIES
    1. T_up_hat(d): upstream temperature RECONSTRUCTED where there is no sensor (2018, 2024-2026 and the cold
       season), by OLS on the mean air temperature over 1, 7 and 21 days and the log discharge.
    2. Allowance A(d) = min(warming limit(d), 28 - T_up_hat(d)) in degC: the warming the plant may add that day.
    3. Risk R(d) = probability that day d is a limitation day, from T_up_hat(d), its 3-day change and log discharge
       (logistic regression), and the expected power at risk R(d) x mean power lost on limitation days.

PRE-DECLARED PROTOCOL (fixed after seeing only what data exist, before any model result)
    Stage 1, reconstruction. Fit on 2019-2023 (all days with a measurement). Leave-one-year-out (LOYO) over those five
    years. Success: LOYO RMSE <= 1.0 degC on 1 June-30 September AND lower than the day-of-year climatology of the other
    years. If it fails, stage 2 uses air temperature and discharge directly and says so.
    Stage 2, risk. If stage 1 fails, the PRIMARY features are the 7-day mean air temperature, its 3-day change and the
    log discharge, used directly; the variant fed by T_up_hat is then reported as a secondary line. Population: days from 1 June to 30 September. Training years 2018-2025; TEST YEAR 2026 (held out; it
    holds 44 limitation days, the largest season on record). T_up_hat for the training years comes from the LOYO
    predictions where a measurement exists, from the full fit elsewhere.
    Baselines: S = share of limitation days in a +-15 day window of the same date, other years; Q = logistic on log
    discharge alone; air = logistic on the 7-day mean air temperature alone.
    Metrics on 2026: AUC and Brier score. Intervals: 90 % moving-block bootstrap (7-day blocks, 2 000 resamples,
    seed 20261102) on the test days.
    Decision: GAIN if the 90 % interval of AUC(model) - max(AUC(Q), AUC(air)) is above 0; otherwise NO_DEMONSTRATED_GAIN.
    The model is USEFUL AS A SIGNAL if the 90 % interval of its own AUC is above 0.5.
    Honest limits: one test season (days are strongly autocorrelated, hence the block bootstrap); 18 events in all;
    air temperature is the observed one (no archived forecast), so any lead-time reading is an UPPER BOUND.

FORECAST TEST (command ``forecast``; protocol fixed on 2026-11-01 before any archived forecast was downloaded)
    Question: with REAL archived weather forecasts instead of observed air, does an alert issued 3 or 7 days ahead
    beat what is known at the time of issue, and does it precede EDF's own publication?
    Forecasts: Open-Meteo previous-runs, hourly temperature_2m_previous_dayN (the forecast for a day, issued N days
    earlier), N = 1..7, averaged to daily means (at least 20 hourly values), from mid-2021.
    Issue day d, target day D = d + h, h in {3, 7}. Features at issue time: the 7-day mean air temperature ending at D
    and its change over 3 days (observed days up to d, forecast days after d), and the log discharge observed on d
    (persistence). Population: issue days d with no limitation active on d and D in 1 June-30 September of the same
    year, so that persistence of an announced limitation cannot help.
    Model: the logistic regression trained on 2018-2025 with PERFECT forecasts (observed air at every date), then applied
    to the real-forecast features of 2026 (the held-out season). Baselines: B = logistic on the observed 7-day mean air
    temperature on the issue day alone (what is known without any forecast); S = seasonal frequency of the target date;
    O = the same model with perfect forecasts (the upper bound seen before).
    Metrics on 2026: AUC, 90 % moving-block bootstrap (7-day blocks, 2 000 resamples, seed 20261102).
    Alert rule: risk >= the 90th percentile of the model's training scores for that lead. For each 2026 event the alert
    is checked on the issue day d = (start date) - h and compared with the FIRST PUBLICATION time of that event by EDF.
    DECISION, lead 3 days. GO only if (a) the 5 % bound of the model's own AUC is above 0.5, (b) the 90 % interval of
    AUC(model) - AUC(B) is above 0, and (c) at least 3 of the 5 events of 2026 have an alert issued before EDF's first
    publication. Otherwise PARK. Lead 7 days is reported, not decisive. One test season: this is stated, not hidden.

FIVE-SEASON TEST (command ``seasons``): a POST-HOC extension, requested after the forecast test had said PARK; its protocol
is fixed here before it was run, and it cannot overturn the lead-3 decision above.
    Question: is the 7-day gain of real forecasts over the observed-air baseline (+0.10 in 2026, interval including 0)
    real across seasons?
    Seasons tested: summers 2022, 2023, 2024, 2025, 2026 (the archive of forecasts starts in mid-2021). For each test
    season, the model and the baseline are trained on every OTHER year of 2018-2026 (leave-one-season-out: this checks
    generalisation across seasons, it is not a causal forecasting setup, since some training years follow the test
    year) and applied to the test season with real forecasts. Same population, features, models and baselines as the
    forecast test. Leads 3 and 7.
    Pooled metric: AUC over the five seasons together. Interval: 90 % bootstrap that resamples 7-day blocks WITHIN each
    season, keeping the five-season structure, 2 000 resamples, seed 20261102.
    DECISION, lead 7 days. REAL if (a) the 90 % interval of pooled AUC(model) - AUC(baseline) is above 0, and (b) the
    difference is positive in at least 4 of the 5 seasons (a season in which the AUC is undefined counts as not
    positive). Otherwise NOT_REAL, and POWER-001 stays parked for good at Golfech. Lead 3 is reported, not decisive.
    Descriptive and not decisive: alert rate and precision, and how many of the 2022-2026 events are alerted before EDF.

EXTRA-VARIABLES TEST (command ``extras``): can our other atmospheric and hydrological information beat the temperature?
Fixed on 2026-11-01 before it was run. It is an UPPER-BOUND test: all variables are the observed ones (perfect
forecasts, lead 0). If more variables do not beat the temperature with perfect information, they cannot with forecasts.
    Target: limitation day, as before. Population: every day from 1 June to 30 September, 2018-2026.
    Validation: leave-one-season-out over the nine summers; per-season AUC where the season holds limitation days (seven
    of nine do), pooled AUC over all seasons; 90 % bootstrap resampling 7-day blocks within each season (2 000 resamples).
    Reference model G: the 7-day mean air temperature alone.
    Candidate models (logistic regression, standardised inputs):
      A  air7 + wet-bulb temperature (7-day mean; the plant has cooling towers, whose limit is the wet bulb);
      B  A + 7-day mean wind speed + 7-day mean shortwave radiation (river and tower heating);
      C  air7 + hydrology: log discharge, its 7-day change, its 30-day mean (memory of the low flow), and the
         air7 x log-discharge interaction;
      D  everything above (air7, wet bulb, wind, radiation, hydrology, interaction).
    The wet bulb comes from the daily mean temperature and relative humidity (Stull 2011), which is an approximation of
    the mean of the hourly wet bulb.
    DECISION on D only (A, B, C are descriptive, so that no choice is made after seeing results): IMPROVEMENT if the 90 %
    interval of pooled AUC(D) - AUC(G) is above 0 AND the difference is positive in at least 5 of the 7 seasons with
    limitation days. Otherwise NO_IMPROVEMENT, and the weather mapping is complete for this purpose.

Usage:

    uv run python experiments/power_001_golfech.py data --cache DIR
    uv run python experiments/power_001_golfech.py run --cache DIR [--out series.csv]
    uv run python experiments/power_001_golfech.py forecast --cache DIR
    uv run python experiments/power_001_golfech.py seasons --cache DIR
    uv run python experiments/power_001_golfech.py extras --cache DIR
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import json
import pathlib
import statistics
import sys
import urllib.parse

import numpy as np
from basin_001_catchment import fetch_json
from basin_001_screening import paged

EDF = "https://opendata.edf.fr/data-fair/api/v1/datasets"
EDF_HISTORY = "historique-des-indisponibilites-des-moyens-de-production-de-edf-sa-depuis-2015"
HUB_TEMPERATURE = "https://hubeau.eaufrance.fr/api/v1/temperature/chronique"
HUB_HYDRO = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/obs_elab"
OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"

PLANT = "GOLFECH"
PLANT_LAT, PLANT_LON = 44.107, 0.845  # approximate, only used to fetch the air temperature
TEMPERATURE_STATION = "05152000"  # La Garonne a St-Aignan, upstream
DISCHARGE_STATION = (
    "O614001001"  # La Garonne a Lamagistere, at the plant (QmnJ, in litres per second)
)
LIMIT_DOWNSTREAM_C = 28.0
WARMING_SUMMER_C, WARMING_OTHER_C = 1.25, 2.0
START, END = dt.date(2018, 1, 1), dt.date(2026, 10, 31)
FIT_YEARS = range(2019, 2024)
TRAIN_YEARS = range(2018, 2026)
TEST_YEAR = 2026
SEED = 20261102
N_BOOTSTRAP = 2000
BLOCK_DAYS = 7


def cache_path(cache: pathlib.Path | None, name: str) -> pathlib.Path | None:
    return None if cache is None else cache / name


def cached(cache: pathlib.Path | None, name: str, produce):
    """Run ``produce()`` once and keep its JSON result in the cache directory."""
    path = cache_path(cache, name)
    if path is not None and path.is_file():
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    value = produce()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(value, handle)
    return value


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------


def load_temperature() -> dict[dt.date, float]:
    """Daily mean upstream temperature; a day needs at least 12 readings."""
    # Hub'Eau refuses page * size > 20 000, so the series is read one year at a time.
    buckets: dict[dt.date, list[float]] = collections.defaultdict(list)
    for year in range(START.year, END.year + 1):
        url = (
            f"{HUB_TEMPERATURE}?code_station={TEMPERATURE_STATION}"
            f"&date_debut_mesure={year}-01-01&date_fin_mesure={year}-12-31&size=5000&format=json"
        )
        for row in paged(url):
            if row.get("resultat") is not None and row.get("date_mesure_temp"):
                buckets[dt.date.fromisoformat(row["date_mesure_temp"][:10])].append(
                    float(row["resultat"])
                )
    return {d: statistics.fmean(v) for d, v in buckets.items() if len(v) >= 12}


def load_discharge() -> dict[dt.date, float]:
    rows = paged(
        f"{HUB_HYDRO}?code_entite={DISCHARGE_STATION}&grandeur_hydro_elab=QmnJ"
        f"&date_debut_obs_elab={START.isoformat()}&size=5000"
    )
    return {
        dt.date.fromisoformat(r["date_obs_elab"][:10]): float(r["resultat_obs_elab"])
        for r in rows
        if (r.get("resultat_obs_elab") or 0) > 0
    }


def load_air() -> dict[dt.date, float]:
    """Daily mean air temperature (ERA5 re-served by Open-Meteo)."""
    params = {
        "latitude": PLANT_LAT,
        "longitude": PLANT_LON,
        "start_date": START.isoformat(),
        "end_date": END.isoformat(),
        "daily": "temperature_2m_mean",
        "timezone": "Europe/Paris",
    }
    page = fetch_json(f"{OPEN_METEO}?{urllib.parse.urlencode(params)}", timeout=120.0)
    if page is None:
        raise RuntimeError("air temperature archive unavailable")
    daily = page["daily"]
    return {
        dt.date.fromisoformat(day): value
        for day, value in zip(daily["time"], daily["temperature_2m_mean"], strict=True)
        if value is not None
    }


def load_events() -> list[dict]:
    """Every record of the plant whose text declares an environmental external cause."""
    qs = urllib.parse.quote(f"nom:{PLANT}*")
    q = urllib.parse.quote("environnement")
    select = (
        "nom,type,cause,date_de_debut,date_de_fin,puissance_maximale_mw,puissance_disponible_mw,"
        "numero_de_version,status,identifiant"
    )
    page = fetch_json(
        f"{EDF}/{EDF_HISTORY}/lines?size=1000&q={q}&qs={qs}&select={select}&sort=date_de_debut"
    )
    if page is None:
        raise RuntimeError("EDF unavailability history unavailable")
    return page["results"]


def latest_active(records: list[dict]) -> list[dict]:
    """The highest version of each identifier, kept only if that version is Active."""
    best: dict[str, dict] = {}
    for record in records:
        key = record["identifiant"]
        if key not in best or record["numero_de_version"] > best[key]["numero_de_version"]:
            best[key] = record
    return sorted(
        (r for r in best.values() if r["status"] == "Active"), key=lambda r: r["date_de_debut"]
    )


def lost_power_by_day(events: list[dict]) -> dict[dt.date, float]:
    """Day -> power lost (MW), summed over units: for each unit the largest shortfall declared that day."""
    per_unit: dict[tuple[str, dt.date], float] = {}
    for event in events:
        start = dt.datetime.fromisoformat(event["date_de_debut"]).date()
        end = dt.datetime.fromisoformat(event["date_de_fin"]).date()
        lost = event["puissance_maximale_mw"] - event["puissance_disponible_mw"]
        day = start
        while day <= end:
            key = (event["nom"], day)
            per_unit[key] = max(per_unit.get(key, 0.0), lost)
            day += dt.timedelta(days=1)
    total: dict[dt.date, float] = collections.defaultdict(float)
    for (_, day), lost in per_unit.items():
        total[day] += lost
    return dict(total)


# --------------------------------------------------------------------------
# numerics (numpy only)
# --------------------------------------------------------------------------


def auc(score: np.ndarray, label: np.ndarray) -> float:
    """Area under the ROC curve (Mann-Whitney), ties counted as one half."""
    positive, negative = score[label == 1], score[label == 0]
    if positive.size == 0 or negative.size == 0:
        return float("nan")
    order = np.argsort(np.concatenate([positive, negative]), kind="mergesort")
    values = np.concatenate([positive, negative])[order]
    ranks = np.empty(values.size)
    i = 0
    while i < values.size:
        j = i
        while j + 1 < values.size and values[j + 1] == values[i]:
            j += 1
        ranks[i : j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    rank_of = np.empty(values.size)
    rank_of[order] = ranks
    return float(
        (rank_of[: positive.size].sum() - positive.size * (positive.size + 1) / 2)
        / (positive.size * negative.size)
    )


def fit_logistic(x: np.ndarray, y: np.ndarray, ridge: float = 1e-3) -> np.ndarray:
    """Logistic regression by Newton steps; features are standardised by the caller, intercept is added here."""
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(design.shape[1])
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30, 30)))
        gradient = design.T @ (p - y) + penalty @ beta
        hessian = (
            design.T @ (design * (p * (1 - p))[:, None]) + penalty + 1e-9 * np.eye(design.shape[1])
        )
        step = np.linalg.solve(hessian, gradient)
        beta -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def predict_logistic(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    return 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30, 30)))


def block_bootstrap(
    score_sets: dict[str, np.ndarray], label: np.ndarray, rng: np.random.Generator
) -> list[dict[str, float]]:
    """AUC of each score set on moving-block resamples of the test days."""
    n = label.size
    blocks = int(np.ceil(n / BLOCK_DAYS))
    offsets = np.arange(BLOCK_DAYS)
    out = []
    for _ in range(N_BOOTSTRAP):
        starts = rng.integers(0, n - BLOCK_DAYS + 1, size=blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n]
        if label[idx].min() == label[idx].max():
            continue
        out.append({name: auc(scores[idx], label[idx]) for name, scores in score_sets.items()})
    return out


# --------------------------------------------------------------------------
# data command
# --------------------------------------------------------------------------


def load_all(cache: pathlib.Path | None):
    temperature = cached(
        cache,
        "temperature.json.gz",
        lambda: {d.isoformat(): v for d, v in load_temperature().items()},
    )
    discharge = cached(
        cache,
        "discharge.json.gz",
        lambda: {d.isoformat(): v for d, v in load_discharge().items()},
    )
    air = cached(
        cache, "air_mean.json.gz", lambda: {d.isoformat(): v for d, v in load_air().items()}
    )
    records = cached(cache, "events.json.gz", load_events)
    iso = dt.date.fromisoformat
    return (
        {iso(k): v for k, v in temperature.items()},
        {iso(k): v for k, v in discharge.items()},
        {iso(k): v for k, v in air.items()},
        records,
    )


def run_data(cache: pathlib.Path | None) -> None:
    temperature, discharge, air, records = load_all(cache)
    print(f"upstream temperature (St-Aignan): {len(temperature)} daily means")
    print(
        f"discharge (Lamagistere): {len(discharge)} daily values; air temperature: {len(air)} days"
    )
    summer = collections.Counter(d.year for d in temperature if 6 <= d.month <= 9)
    print("summer days with an upstream temperature, by year:", dict(sorted(summer.items())))
    events = latest_active(records)
    lost = lost_power_by_day(events)
    print(f"\nenvironmental records: {len(records)}; active events (latest version): {len(events)}")
    print(
        "limitation days by year:", dict(sorted(collections.Counter(d.year for d in lost).items()))
    )
    for e in events:
        a, b = (
            dt.datetime.fromisoformat(e["date_de_debut"]),
            dt.datetime.fromisoformat(e["date_de_fin"]),
        )
        print(
            f"  {e['nom']:10s} {a:%Y-%m-%d %H:%M} -> {b:%Y-%m-%d %H:%M} {e['type']:10s} "
            f"{e['puissance_disponible_mw']:>6.0f}/{e['puissance_maximale_mw']:.0f} MW"
        )


# --------------------------------------------------------------------------
# run command
# --------------------------------------------------------------------------


def window_mean(series: dict[dt.date, float], day: dt.date, length: int) -> float | None:
    values = [series.get(day - dt.timedelta(days=i)) for i in range(length)]
    return None if any(v is None for v in values) else float(np.mean(values))


def reconstruction_features(
    day: dt.date, air: dict[dt.date, float], discharge: dict[dt.date, float]
) -> list[float] | None:
    a1, a7, a21 = (window_mean(air, day, n) for n in (1, 7, 21))
    q = discharge.get(day)
    if None in (a1, a7, a21) or q is None:
        return None
    return [a1, a7, a21, float(np.log10(q))]


def ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    return np.linalg.lstsq(design, y, rcond=None)[0]


def ols_predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ beta


def in_summer(day: dt.date) -> bool:
    return 6 <= day.month <= 9


def run_pipeline(cache: pathlib.Path | None, out: pathlib.Path | None) -> None:
    temperature, discharge, air, records = load_all(cache)
    events = latest_active(records)
    lost = lost_power_by_day(events)
    days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
    feats = {d: reconstruction_features(d, air, discharge) for d in days}

    # ---- stage 1: reconstruct the upstream temperature ------------------
    fit_days = [
        d for d in days if d.year in FIT_YEARS and d in temperature and feats[d] is not None
    ]
    x_all = np.array([feats[d] for d in fit_days])
    y_all = np.array([temperature[d] for d in fit_days])
    years = np.array([d.year for d in fit_days])
    loyo: dict[dt.date, float] = {}
    for year in FIT_YEARS:
        beta = ols(x_all[years != year], y_all[years != year])
        mask = years == year
        for d, value in zip(np.array(fit_days)[mask], ols_predict(beta, x_all[mask]), strict=True):
            loyo[d] = float(value)
    beta_full = ols(x_all, y_all)
    summer_days = [d for d in fit_days if in_summer(d)]
    err = np.array([loyo[d] - temperature[d] for d in summer_days])
    rmse = float(np.sqrt(np.mean(err**2)))
    climatology = collections.defaultdict(list)
    for d in fit_days:
        climatology[(d.month, d.day)].append((d.year, temperature[d]))
    base_err = []
    for d in summer_days:
        others = [v for y, v in climatology[(d.month, d.day)] if y != d.year]
        if others:
            base_err.append(statistics.fmean(others) - temperature[d])
    base_rmse = float(np.sqrt(np.mean(np.square(base_err))))
    ss_res = float(np.sum(err**2))
    ss_tot = float(
        np.sum(
            (
                np.array([temperature[d] for d in summer_days])
                - np.mean([temperature[d] for d in summer_days])
            )
            ** 2
        )
    )
    print("STAGE 1 - reconstruction of the upstream temperature (leave-one-year-out, 2019-2023)")
    print(
        f"  coefficients [intercept, air1, air7, air21, log10 Q]: {np.round(beta_full, 3).tolist()}"
    )
    print(
        f"  RMSE 1 Jun-30 Sep: {rmse:.2f} degC   climatology baseline RMSE: {base_rmse:.2f} degC   R2: {1 - ss_res / ss_tot:.3f}"
    )
    stage1_ok = rmse <= 1.0 and rmse < base_rmse
    print(
        f"  success criterion (RMSE <= 1.0 and better than climatology): {'MET' if stage1_ok else 'NOT MET'}"
    )

    # ---- series ----------------------------------------------------------
    t_hat: dict[dt.date, float] = {}
    for d in days:
        if d in loyo:
            t_hat[d] = loyo[d]
        elif feats[d] is not None:
            t_hat[d] = float(ols_predict(beta_full, np.array([feats[d]]))[0])
    rows = []
    for d in days:
        if d not in t_hat:
            continue
        warming = WARMING_SUMMER_C if in_summer(d) else WARMING_OTHER_C
        rows.append(
            {
                "date": d.isoformat(),
                "t_up_hat_c": round(t_hat[d], 2),
                "t_up_measured_c": round(temperature[d], 2) if d in temperature else "",
                # Hub'Eau publishes QmnJ in litres per second (magnitudes fit the Garonne regime).
                "discharge_m3s": round(discharge[d] / 1000.0, 1) if d in discharge else "",
                "allowance_c": round(min(warming, LIMIT_DOWNSTREAM_C - t_hat[d]), 2),
                "limitation_day": int(d in lost),
                "power_lost_mw": round(lost.get(d, 0.0), 0),
            }
        )

    # ---- stage 2: risk ---------------------------------------------------
    # Stage 1 decides the branch. When it is NOT MET (as protocol), the PRIMARY features are the air temperature and
    # the discharge, used directly; the variant fed by T_up_hat is reported as a secondary line.
    def table(years_range):
        out = []
        for d in days:
            if (
                d.year not in years_range
                or not in_summer(d)
                or d not in t_hat
                or d not in discharge
            ):
                continue
            prev_t, prev_a = (
                t_hat.get(d - dt.timedelta(days=3)),
                window_mean(air, d - dt.timedelta(days=3), 7),
            )
            a7 = window_mean(air, d, 7)
            if prev_t is None or prev_a is None or a7 is None:
                continue
            out.append(
                {
                    "day": d,
                    "t_hat": t_hat[d],
                    "t_hat_change": t_hat[d] - prev_t,
                    "air7": a7,
                    "air7_change": a7 - prev_a,
                    "logq": float(np.log10(discharge[d])),
                    "y": int(d in lost),
                }
            )
        return out

    train, test = table(TRAIN_YEARS), table([TEST_YEAR])
    print(
        f"\nSTAGE 2 - risk of a limitation day; training days {len(train)}, test days {len(test)} (year {TEST_YEAR})"
    )
    ytr = np.array([r["y"] for r in train], float)
    yte = np.array([r["y"] for r in test], float)
    print(
        f"  limitation days: training {int(ytr.sum())}/{len(ytr)}, test {int(yte.sum())}/{len(yte)}"
    )

    def matrix(rows_, cols):
        return np.array([[r[c] for c in cols] for r in rows_], float)

    def standardise(train_x, test_x):
        mu, sd = train_x.mean(axis=0), train_x.std(axis=0) + 1e-9
        return (train_x - mu) / sd, (test_x - mu) / sd

    primary_cols = (
        ("air7", "air7_change", "logq") if not stage1_ok else ("t_hat", "t_hat_change", "logq")
    )
    sets = {
        "model": primary_cols,
        "Q only": ("logq",),
        "air only": ("air7",),
        "variant: T_up_hat model": ("t_hat", "t_hat_change", "logq"),
        "variant: T_up_hat only": ("t_hat",),
    }
    scores = {}
    for name, cols in sets.items():
        xtr, xte = standardise(matrix(train, cols), matrix(test, cols))
        scores[name] = predict_logistic(fit_logistic(xtr, ytr), xte)
    by_doy = collections.defaultdict(list)
    for r in train:
        by_doy[r["day"].timetuple().tm_yday].append(r["y"])
    seasonal = []
    for r in test:
        doy = r["day"].timetuple().tm_yday
        window = [v for k, vs in by_doy.items() if abs(k - doy) <= 15 for v in vs]
        seasonal.append(statistics.fmean(window) if window else float(ytr.mean()))
    scores["seasonal S"] = np.array(seasonal)

    rng = np.random.default_rng(SEED)
    boot = block_bootstrap(scores, yte, rng)
    print(f"  primary model features: {primary_cols}")
    print(f"  {'predictor':26s} {'AUC':>6s} {'90% block interval':>20s} {'Brier':>7s}")
    for name, s in scores.items():
        values = [b[name] for b in boot]
        lo, hi = np.quantile(values, [0.05, 0.95])
        print(
            f"  {name:26s} {auc(s, yte):6.3f}   [{lo:5.3f}, {hi:5.3f}]    {float(np.mean((s - yte) ** 2)):7.4f}"
        )
    diff = [b["model"] - max(b["Q only"], b["air only"]) for b in boot]
    lo, hi = np.quantile(diff, [0.05, 0.95])
    own_lo = np.quantile([b["model"] for b in boot], 0.05)
    point = auc(scores["model"], yte) - max(
        auc(scores["Q only"], yte), auc(scores["air only"], yte)
    )
    print(
        f"  AUC(model) - max(AUC(Q), AUC(air)): {point:+.3f}  90% interval [{lo:+.3f}, {hi:+.3f}]"
    )
    verdict = "GAIN" if lo > 0 else "NO_DEMONSTRATED_GAIN"
    signal = "USEFUL" if own_lo > 0.5 else "NOT DEMONSTRATED"
    print(f"  VERDICT: {verdict}; model {signal} AS A SIGNAL (own 5 % bound {own_lo:.3f})")

    # power at risk and calibration on the test season
    mean_loss = statistics.fmean([lost[d] for d in lost if d.year in TRAIN_YEARS and in_summer(d)])
    expected = scores["model"] * mean_loss
    observed = np.array([lost.get(r["day"], 0.0) for r in test])
    print(
        f"\n  mean power lost on a limitation day, training summers: {mean_loss:.0f} MW (plant total 2 620 MW)"
    )
    print(
        f"  test season: observed mean lost {observed.mean():.0f} MW/day, expected from the model {expected.mean():.0f} MW/day"
    )
    order = np.argsort(scores["model"])
    for part in np.array_split(order, 4):
        print(
            f"    predicted risk {scores['model'][part].mean():5.2f} -> observed frequency {yte[part].mean():5.2f} (n={part.size})"
        )

    # ---- EXPLORATORY (added after the results above, NOT pre-declared): anticipation of onsets ----------
    print(
        "\nEXPLORATORY - can the model announce a limitation before it starts? (onsets, test year only)"
    )
    full = {r["day"]: r for r in train + test}
    xtr, _ = standardise(matrix(train, primary_cols), matrix(test, primary_cols))
    mu = matrix(train, primary_cols).mean(axis=0)
    sd = matrix(train, primary_cols).std(axis=0) + 1e-9
    for h in (1, 3, 7):
        # train: predict E(d+h) from the features of day d, for days with no limitation active on day d
        def pairs(years_range, h=h):
            xs, ys = [], []
            for d, r in full.items():
                if (
                    d.year in years_range
                    and d not in lost
                    and (d + dt.timedelta(days=h)).year == d.year
                ):
                    xs.append([r[c] for c in primary_cols])
                    ys.append(int((d + dt.timedelta(days=h)) in lost))
            return np.array(xs, float), np.array(ys, float)

        xa, ya = pairs(TRAIN_YEARS)
        xb, yb = pairs([TEST_YEAR])
        beta = fit_logistic((xa - mu) / sd, ya)
        sb = predict_logistic(beta, (xb - mu) / sd)
        persistence_note = (
            "persistence is undefined here: no limitation is active on day d by construction"
        )
        print(
            f"  h={h}d: test onsets {int(yb.sum())}/{len(yb)} days without active limitation; "
            f"AUC {auc(sb, yb):.3f}  ({persistence_note})"
        )

    # The risk is published only where it is out of sample: the held-out season.
    risk_by_day = {
        r["day"].isoformat(): float(p) for r, p in zip(test, scores["model"], strict=True)
    }
    for row in rows:
        row["risk_out_of_sample"] = (
            round(risk_by_day[row["date"]], 3) if row["date"] in risk_by_day else ""
        )

    if out is not None:
        with out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nseries written: {out} ({len(rows)} days)")


# --------------------------------------------------------------------------
# forecast command: real archived forecasts, leads 3 and 7 days
# --------------------------------------------------------------------------

OPEN_METEO_PREVIOUS = "https://previous-runs-api.open-meteo.com/v1/forecast"
FORECAST_FIRST_DAY = dt.date(2021, 6, 1)
LEADS = (3, 7)
ALERT_QUANTILE = 0.90
GO_MIN_EVENTS = 3


def load_forecasts() -> dict[str, dict[str, float]]:
    """Daily mean of the forecast made N days earlier, for N = 1..7 (key N as text, then ISO date)."""
    names = ",".join(f"temperature_2m_previous_day{k}" for k in range(1, 8))
    out: dict[str, dict[str, float]] = {str(k): {} for k in range(1, 8)}
    for year in range(FORECAST_FIRST_DAY.year, END.year + 1):
        start = max(dt.date(year, 1, 1), FORECAST_FIRST_DAY)
        end = min(dt.date(year, 12, 31), END)
        params = {
            "latitude": PLANT_LAT,
            "longitude": PLANT_LON,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": names,
            "timezone": "Europe/Paris",
        }
        page = fetch_json(f"{OPEN_METEO_PREVIOUS}?{urllib.parse.urlencode(params)}", timeout=240.0)
        if page is None:
            raise RuntimeError(f"archived forecasts unavailable for {year}")
        times = page["hourly"]["time"]
        for k in range(1, 8):
            buckets: dict[str, list[float]] = collections.defaultdict(list)
            for stamp, value in zip(
                times, page["hourly"][f"temperature_2m_previous_day{k}"], strict=True
            ):
                if value is not None:
                    buckets[stamp[:10]].append(value)
            out[str(k)].update(
                {day: statistics.fmean(v) for day, v in buckets.items() if len(v) >= 20}
            )
    return out


def load_first_publications() -> dict[str, str]:
    """Identifier -> ISO time of the first publication of the event."""
    qs = urllib.parse.quote(f"nom:{PLANT}*")
    q = urllib.parse.quote("environnement")
    page = fetch_json(
        f"{EDF}/{EDF_HISTORY}/lines?size=1000&q={q}&qs={qs}"
        "&select=identifiant,date_de_publication,numero_de_version"
    )
    if page is None:
        raise RuntimeError("EDF unavailability history unavailable")
    first: dict[str, str] = {}
    for row in page["results"]:
        key = row["identifiant"]
        if key not in first or row["date_de_publication"] < first[key]:
            first[key] = row["date_de_publication"]
    return first


def issue_features(
    d: dt.date,
    h: int,
    air: dict[dt.date, float],
    forecast: dict[int, dict[dt.date, float]] | None,
    discharge: dict[dt.date, float],
) -> list[float] | None:
    """Features known on day d about target day d + h; ``forecast=None`` means perfect forecasts (observed air)."""
    target = d + dt.timedelta(days=h)

    def value(t: dt.date) -> float | None:
        if forecast is None or t <= d:
            return air.get(t)
        lead = (t - d).days
        return forecast.get(lead, {}).get(t) if lead <= 7 else None

    def mean_ending(end: dt.date) -> float | None:
        values = [value(end - dt.timedelta(days=i)) for i in range(7)]
        return None if any(v is None for v in values) else float(np.mean(values))

    now, before = mean_ending(target), mean_ending(target - dt.timedelta(days=3))
    q = discharge.get(d)
    if now is None or before is None or q is None:
        return None
    return [now, now - before, float(np.log10(q))]


def run_forecast(cache: pathlib.Path | None) -> None:
    _, discharge, air, records = load_all(cache)
    events = latest_active(records)
    lost = lost_power_by_day(events)
    raw = cached(cache, "forecasts.json.gz", load_forecasts)
    forecast = {
        int(k): {dt.date.fromisoformat(day): v for day, v in vs.items()} for k, vs in raw.items()
    }
    published = cached(cache, "first_publications.json.gz", load_first_publications)
    print(
        "archived forecast days available by lead:",
        {k: len(v) for k, v in sorted(forecast.items())},
    )
    rng = np.random.default_rng(SEED)
    verdicts = {}
    for h in LEADS:

        def pairs(years_range, h=h):
            out = []
            for d in sorted(discharge):
                target = d + dt.timedelta(days=h)
                if (
                    d.year in years_range
                    and target.year == d.year
                    and in_summer(target)
                    and d not in lost
                ):
                    out.append((d, target))
            return out

        train_pairs, test_pairs = pairs(TRAIN_YEARS), pairs([TEST_YEAR])
        keep_train, xo_tr, yb_tr, y_tr = [], [], [], []
        for d, t in train_pairs:
            perfect = issue_features(d, h, air, None, discharge)
            a7_obs = window_mean(air, d, 7)
            if perfect is not None and a7_obs is not None:
                keep_train.append((d, t))
                xo_tr.append(perfect)
                yb_tr.append([a7_obs])
                y_tr.append(int(t in lost))
        keep_test, xf, xo, xb, y_te = [], [], [], [], []
        for d, t in test_pairs:
            f = issue_features(d, h, air, forecast, discharge)
            o = issue_features(d, h, air, None, discharge)
            a7_obs = window_mean(air, d, 7)
            if f is not None and o is not None and a7_obs is not None:
                keep_test.append((d, t))
                xf.append(f)
                xo.append(o)
                xb.append([a7_obs])
                y_te.append(int(t in lost))
        xo_tr, yb_tr, y_tr = np.array(xo_tr), np.array(yb_tr), np.array(y_tr, float)
        xf, xo, xb, y_te = np.array(xf), np.array(xo), np.array(xb), np.array(y_te, float)

        mu, sd = xo_tr.mean(axis=0), xo_tr.std(axis=0) + 1e-9
        beta = fit_logistic((xo_tr - mu) / sd, y_tr)
        bmu, bsd = yb_tr.mean(axis=0), yb_tr.std(axis=0) + 1e-9
        beta_b = fit_logistic((yb_tr - bmu) / bsd, y_tr)
        by_doy = collections.defaultdict(list)
        for (_, t), y in zip(keep_train, y_tr, strict=True):
            by_doy[t.timetuple().tm_yday].append(y)
        seasonal = np.array(
            [
                statistics.fmean(
                    [
                        v
                        for k, vs in by_doy.items()
                        if abs(k - t.timetuple().tm_yday) <= 15
                        for v in vs
                    ]
                )
                for _, t in keep_test
            ]
        )
        scores = {
            "F model (real forecasts)": predict_logistic(beta, (xf - mu) / sd),
            "O model (perfect forecasts)": predict_logistic(beta, (xo - mu) / sd),
            "B baseline (observed air at issue)": predict_logistic(beta_b, (xb - bmu) / bsd),
            "S seasonal": seasonal,
        }
        boot = block_bootstrap(scores, y_te, rng)
        print(
            f"\nLEAD {h} DAYS - issue days {len(keep_test)} in 2026, targets that are limitation days: {int(y_te.sum())}"
        )
        print(f"  {'predictor':36s} {'AUC':>6s} {'90% block interval':>20s}")
        for name, s in scores.items():
            lo, hi = np.quantile([b[name] for b in boot], [0.05, 0.95])
            print(f"  {name:36s} {auc(s, y_te):6.3f}   [{lo:5.3f}, {hi:5.3f}]")
        key_f, key_b = "F model (real forecasts)", "B baseline (observed air at issue)"
        diff = [b[key_f] - b[key_b] for b in boot]
        dlo, dhi = np.quantile(diff, [0.05, 0.95])
        own_lo = float(np.quantile([b[key_f] for b in boot], 0.05))
        print(
            f"  AUC(F) - AUC(B) = {auc(scores[key_f], y_te) - auc(scores[key_b], y_te):+.3f}  90% interval [{dlo:+.3f}, {dhi:+.3f}]; "
            f"own 5 % bound of AUC(F): {own_lo:.3f}"
        )

        # alert rule and precedence over EDF's first publication
        threshold = float(np.quantile(predict_logistic(beta, (xo_tr - mu) / sd), ALERT_QUANTILE))
        index = {d: i for i, (d, _) in enumerate(keep_test)}
        ahead = 0
        print(f"  alert threshold (90th percentile of training scores): {threshold:.3f}")
        # Descriptive, added after the results (not part of the decision): how often does the alert fire?
        fired = scores[key_f] >= threshold
        hits = int(np.sum(fired & (y_te == 1)))
        print(
            f"  [descriptive] alert fires on {int(fired.sum())} of {len(fired)} issue days; "
            f"hits {hits} of {int(y_te.sum())} limitation targets; precision {hits / max(int(fired.sum()), 1):.2f}"
        )
        print(
            f"  {'event start':12s} {'issue day':10s} {'risk':>6s} {'alert':>6s} {'EDF first publication':>22s} {'alert before EDF':>17s}"
        )
        for event in events:
            start = dt.datetime.fromisoformat(event["date_de_debut"]).date()
            if start.year != TEST_YEAR:
                continue
            issue = start - dt.timedelta(days=h)
            published_at = dt.datetime.fromisoformat(published[event["identifiant"]]).replace(
                tzinfo=None
            )
            if issue in index:
                risk = float(scores[key_f][index[issue]])
                alert = risk >= threshold
                before = alert and dt.datetime.combine(issue, dt.time()) < published_at
                ahead += int(before)
                print(
                    f"  {start!s:12s} {issue!s:10s} {risk:6.3f} {alert!s:>6s} {published_at:%Y-%m-%d %H:%M}   {before!s:>17s}"
                )
            else:
                print(
                    f"  {start!s:12s} {issue!s:10s} {'n/a':>6s} {'n/a':>6s} {published_at:%Y-%m-%d %H:%M}   {'not evaluable':>17s}"
                )
        verdicts[h] = (own_lo > 0.5, dlo > 0, ahead)
        print(
            f"  events alerted before EDF's first publication: {ahead} of {sum(1 for e in events if dt.datetime.fromisoformat(e['date_de_debut']).year == TEST_YEAR)}"
        )

    a, b, c = verdicts[3]
    print(
        f"\nDECISION (lead 3 days): (a) own AUC bound > 0.5: {a}; (b) AUC(F) - AUC(B) interval above 0: {b}; (c) >= {GO_MIN_EVENTS} events alerted before EDF: {c >= GO_MIN_EVENTS} ({c})"
    )
    print("  ->", "GO" if (a and b and c >= GO_MIN_EVENTS) else "PARK")


# --------------------------------------------------------------------------
# seasons command: leave-one-season-out over 2022-2026 (post-hoc extension)
# --------------------------------------------------------------------------

TEST_SEASONS = range(2022, 2027)
ALL_YEARS = range(2018, 2027)
REAL_MIN_POSITIVE_SEASONS = 4


def run_seasons(cache: pathlib.Path | None) -> None:
    _, discharge, air, records = load_all(cache)
    events = latest_active(records)
    lost = lost_power_by_day(events)
    raw = cached(cache, "forecasts.json.gz", load_forecasts)
    forecast = {
        int(k): {dt.date.fromisoformat(day): v for day, v in vs.items()} for k, vs in raw.items()
    }
    published = cached(cache, "first_publications.json.gz", load_first_publications)
    rng = np.random.default_rng(SEED)
    final = {}
    for h in LEADS:
        rows = []
        for d in sorted(discharge):
            target = d + dt.timedelta(days=h)
            if (
                d.year not in ALL_YEARS
                or target.year != d.year
                or not in_summer(target)
                or d in lost
            ):
                continue
            perfect = issue_features(d, h, air, None, discharge)
            a7_obs = window_mean(air, d, 7)
            if perfect is None or a7_obs is None:
                continue
            real = (
                issue_features(d, h, air, forecast, discharge) if d.year in TEST_SEASONS else None
            )
            rows.append(
                {
                    "d": d,
                    "t": target,
                    "year": d.year,
                    "perfect": perfect,
                    "real": real,
                    "base": [a7_obs],
                    "y": int(target in lost),
                }
            )

        scores_f, scores_b, scores_s, labels, seasons, days_ = [], [], [], [], [], []
        scores_g: list[
            np.ndarray
        ] = []  # descriptive baseline added after the results: the forecast temperature alone
        per_season_g: dict[int, float] = {}
        per_season = {}
        alert_rows = []
        for year in TEST_SEASONS:
            train = [r for r in rows if r["year"] != year]
            test = [r for r in rows if r["year"] == year and r["real"] is not None]
            if not test:
                continue
            xtr = np.array([r["perfect"] for r in train])
            btr = np.array([r["base"] for r in train])
            ytr = np.array([r["y"] for r in train], float)
            mu, sd = xtr.mean(axis=0), xtr.std(axis=0) + 1e-9
            bmu, bsd = btr.mean(axis=0), btr.std(axis=0) + 1e-9
            beta = fit_logistic((xtr - mu) / sd, ytr)
            beta_b = fit_logistic((btr - bmu) / bsd, ytr)
            fmu, fsd = xtr[:, :1].mean(axis=0), xtr[:, :1].std(axis=0) + 1e-9
            beta_g = fit_logistic((xtr[:, :1] - fmu) / fsd, ytr)
            by_doy = collections.defaultdict(list)
            for r in train:
                by_doy[r["t"].timetuple().tm_yday].append(r["y"])
            f = predict_logistic(beta, (np.array([r["real"] for r in test]) - mu) / sd)
            b = predict_logistic(beta_b, (np.array([r["base"] for r in test]) - bmu) / bsd)
            g = predict_logistic(beta_g, (np.array([r["real"] for r in test])[:, :1] - fmu) / fsd)
            s = np.array(
                [
                    statistics.fmean(
                        [
                            v
                            for k, vs in by_doy.items()
                            if abs(k - r["t"].timetuple().tm_yday) <= 15
                            for v in vs
                        ]
                    )
                    for r in test
                ]
            )
            y = np.array([r["y"] for r in test], float)
            per_season[year] = (auc(f, y), auc(b, y), int(y.sum()), len(y))
            per_season_g[year] = auc(g, y)
            scores_f.append(f)
            scores_b.append(b)
            scores_g.append(g)
            scores_s.append(s)
            labels.append(y)
            seasons.append(np.full(len(y), year))
            days_.extend(r["d"] for r in test)
            threshold = float(np.quantile(predict_logistic(beta, (xtr - mu) / sd), ALERT_QUANTILE))
            index = {r["d"]: i for i, r in enumerate(test)}
            for event in events:
                start = dt.datetime.fromisoformat(event["date_de_debut"]).date()
                if start.year != year:
                    continue
                issue = start - dt.timedelta(days=h)
                published_at = dt.datetime.fromisoformat(published[event["identifiant"]]).replace(
                    tzinfo=None
                )
                if issue in index:
                    alert = bool(f[index[issue]] >= threshold)
                    alert_rows.append(
                        (alert, alert and dt.datetime.combine(issue, dt.time()) < published_at)
                    )
                else:
                    alert_rows.append((None, None))

        f_all, b_all, s_all = (
            np.concatenate(scores_f),
            np.concatenate(scores_b),
            np.concatenate(scores_s),
        )
        y_all, season_all = np.concatenate(labels), np.concatenate(seasons)
        print(
            f"\nLEAD {h} DAYS - leave-one-season-out over {TEST_SEASONS.start}-{TEST_SEASONS.stop - 1}"
        )
        print(
            f"  {'season':6s} {'targets':>8s} {'issue days':>11s} {'AUC model':>10s} {'AUC base':>9s} {'difference':>11s}"
        )
        positive = 0
        for year, (af, ab, n_pos, n) in per_season.items():
            diff = af - ab
            positive += int(diff > 0) if diff == diff else 0
            print(f"  {year:<6d} {n_pos:>8d} {n:>11d} {af:>10.3f} {ab:>9.3f} {diff:>+11.3f}")
        pooled = {
            "model": auc(f_all, y_all),
            "baseline": auc(b_all, y_all),
            "seasonal": auc(s_all, y_all),
        }

        g_all = np.concatenate(scores_g)
        diffs, own, diffs_g = [], [], []
        for _ in range(N_BOOTSTRAP):
            idx_parts = []
            for year in per_season:
                where = np.flatnonzero(season_all == year)
                n = where.size
                blocks = int(np.ceil(n / BLOCK_DAYS))
                starts = rng.integers(0, max(n - BLOCK_DAYS + 1, 1), size=blocks)
                local = (starts[:, None] + np.arange(BLOCK_DAYS)[None, :]).reshape(-1)[:n]
                idx_parts.append(where[np.minimum(local, n - 1)])
            idx = np.concatenate(idx_parts)
            if y_all[idx].min() == y_all[idx].max():
                continue
            a_f, a_b = auc(f_all[idx], y_all[idx]), auc(b_all[idx], y_all[idx])
            diffs.append(a_f - a_b)
            own.append(a_f)
            diffs_g.append(a_f - auc(g_all[idx], y_all[idx]))
        lo, hi = np.quantile(diffs, [0.05, 0.95])
        own_lo = float(np.quantile(own, 0.05))
        print(
            f"  pooled AUC: model {pooled['model']:.3f}, baseline {pooled['baseline']:.3f}, seasonal {pooled['seasonal']:.3f}"
        )
        print(
            f"  pooled AUC(model) - AUC(baseline) = {pooled['model'] - pooled['baseline']:+.3f}  90% interval [{lo:+.3f}, {hi:+.3f}]; own 5 % bound {own_lo:.3f}"
        )
        print(f"  seasons with a positive difference: {positive} of {len(per_season)}")
        glo, ghi = np.quantile(diffs_g, [0.05, 0.95])
        positive_g = sum(1 for yr, (af, _, _, _) in per_season.items() if af - per_season_g[yr] > 0)
        print(
            "  [descriptive, added after the results] baseline G = the forecast temperature alone (what anyone reads): "
            f"pooled AUC {auc(g_all, y_all):.3f}; AUC(model) - AUC(G) = {pooled['model'] - auc(g_all, y_all):+.3f} "
            f"90% interval [{glo:+.3f}, {ghi:+.3f}]; positive in {positive_g} of {len(per_season)} seasons"
        )
        evaluated = [a for a in alert_rows if a[0] is not None]
        print(
            f"  [descriptive] events of {TEST_SEASONS.start}-{TEST_SEASONS.stop - 1}: {len(alert_rows)}; evaluable {len(evaluated)}; "
            f"alerted {sum(1 for a in evaluated if a[0])}; alerted before EDF's first publication {sum(1 for a in evaluated if a[1])}"
        )
        final[h] = (lo > 0 and positive >= REAL_MIN_POSITIVE_SEASONS, lo, positive)

    real, lo, positive = final[7]
    print(
        f"\nDECISION (lead 7 days): (a) pooled interval above 0: {lo > 0} (lower end {lo:+.3f}); (b) positive in >= {REAL_MIN_POSITIVE_SEASONS} of 5 seasons: {positive >= REAL_MIN_POSITIVE_SEASONS} ({positive})"
    )
    print("  ->", "REAL" if real else "NOT_REAL")


# --------------------------------------------------------------------------
# extras command: do other atmospheric and hydrological variables beat the temperature? (upper bound)
# --------------------------------------------------------------------------

EXTRA_YEARS = range(2018, 2027)
IMPROVEMENT_MIN_POSITIVE = 5


def load_air_extra() -> dict[str, list[float]]:
    """Daily mean temperature, relative humidity, wind speed and shortwave radiation sum (ERA5, Open-Meteo)."""
    params = {
        "latitude": PLANT_LAT,
        "longitude": PLANT_LON,
        "start_date": START.isoformat(),
        "end_date": END.isoformat(),
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_mean,shortwave_radiation_sum",
        "timezone": "Europe/Paris",
    }
    page = fetch_json(f"{OPEN_METEO}?{urllib.parse.urlencode(params)}", timeout=120.0)
    if page is None:
        raise RuntimeError("air archive unavailable")
    daily = page["daily"]
    out = {}
    for i, day in enumerate(daily["time"]):
        values = [
            daily[k][i]
            for k in (
                "temperature_2m_mean",
                "relative_humidity_2m_mean",
                "wind_speed_10m_mean",
                "shortwave_radiation_sum",
            )
        ]
        if all(v is not None for v in values):
            out[day] = values
    return out


def wet_bulb(temperature: float, humidity: float) -> float:
    """Stull (2011) wet-bulb temperature, degC, from temperature (degC) and relative humidity (%)."""
    t, rh = temperature, humidity
    return float(
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * np.arctan(0.023101 * rh)
        - 4.686035
    )


def run_extras(cache: pathlib.Path | None) -> None:
    _, discharge, _, records = load_all(cache)
    lost = lost_power_by_day(latest_active(records))
    raw = cached(cache, "air_extra.json.gz", load_air_extra)
    extra = {dt.date.fromisoformat(k): v for k, v in raw.items()}
    wb = {d: wet_bulb(v[0], v[1]) for d, v in extra.items()}
    temp = {d: v[0] for d, v in extra.items()}
    wind = {d: v[2] for d, v in extra.items()}
    rad = {d: v[3] for d, v in extra.items()}
    logq = {d: float(np.log10(q)) for d, q in discharge.items()}

    rows = []
    for d in sorted(extra):
        if d.year not in EXTRA_YEARS or not in_summer(d):
            continue
        feats = {
            "air7": window_mean(temp, d, 7),
            "wb7": window_mean(wb, d, 7),
            "wind7": window_mean(wind, d, 7),
            "rad7": window_mean(rad, d, 7),
            "logq": logq.get(d),
            "logq_prev": logq.get(d - dt.timedelta(days=7)),
            "logq30": window_mean(logq, d, 30),
        }
        if any(v is None for v in feats.values()):
            continue
        rows.append(
            {
                "d": d,
                "year": d.year,
                "y": int(d in lost),
                "air7": feats["air7"],
                "wb7": feats["wb7"],
                "wind7": feats["wind7"],
                "rad7": feats["rad7"],
                "logq": feats["logq"],
                "dlogq7": feats["logq"] - feats["logq_prev"],
                "logq30": feats["logq30"],
            }
        )
    air_mean = float(np.mean([r["air7"] for r in rows]))
    q_mean = float(np.mean([r["logq"] for r in rows]))
    for r in rows:
        r["inter"] = (r["air7"] - air_mean) * (r["logq"] - q_mean)

    models = {
        "G  air7": ("air7",),
        "A  + wet bulb": ("air7", "wb7"),
        "B  + wind, radiation": ("air7", "wb7", "wind7", "rad7"),
        "C  + hydrology": ("air7", "logq", "dlogq7", "logq30", "inter"),
        "D  everything": ("air7", "wb7", "wind7", "rad7", "logq", "dlogq7", "logq30", "inter"),
    }
    print(
        f"summer days used: {len(rows)} over {len(EXTRA_YEARS)} seasons; limitation days {sum(r['y'] for r in rows)}"
    )
    per_year = {}
    store = {name: [] for name in models}
    labels, years = [], []
    for year in EXTRA_YEARS:
        train = [r for r in rows if r["year"] != year]
        test = [r for r in rows if r["year"] == year]
        if not test:
            continue
        ytr = np.array([r["y"] for r in train], float)
        y = np.array([r["y"] for r in test], float)
        labels.append(y)
        years.append(np.full(len(y), year))
        per_year[year] = {}
        for name, cols in models.items():
            xtr = np.array([[r[c] for c in cols] for r in train])
            xte = np.array([[r[c] for c in cols] for r in test])
            mu, sd = xtr.mean(axis=0), xtr.std(axis=0) + 1e-9
            s = predict_logistic(fit_logistic((xtr - mu) / sd, ytr), (xte - mu) / sd)
            store[name].append(s)
            per_year[year][name] = auc(s, y)
    y_all, year_all = np.concatenate(labels), np.concatenate(years)
    pooled_scores = {name: np.concatenate(v) for name, v in store.items()}

    print(f"\n{'season':6s} {'targets':>8s} " + " ".join(f"{n.split()[0]:>6s}" for n in models))
    defined = []
    for year, aucs in per_year.items():
        n_pos = int(sum(r["y"] for r in rows if r["year"] == year))
        cells = " ".join(
            f"{aucs[n]:6.3f}" if aucs[n] == aucs[n] else f"{'n/a':>6s}" for n in models
        )
        print(f"{year:<6d} {n_pos:>8d} {cells}")
        if n_pos:
            defined.append(year)
    reference = "G  air7"
    rng = np.random.default_rng(SEED)
    diffs = {name: [] for name in models if name != reference}
    for _ in range(N_BOOTSTRAP):
        idx_parts = []
        for year in per_year:
            where = np.flatnonzero(year_all == year)
            n = where.size
            blocks = int(np.ceil(n / BLOCK_DAYS))
            starts = rng.integers(0, max(n - BLOCK_DAYS + 1, 1), size=blocks)
            local = (starts[:, None] + np.arange(BLOCK_DAYS)[None, :]).reshape(-1)[:n]
            idx_parts.append(where[np.minimum(local, n - 1)])
        idx = np.concatenate(idx_parts)
        if y_all[idx].min() == y_all[idx].max():
            continue
        base = auc(pooled_scores[reference][idx], y_all[idx])
        for name in diffs:
            diffs[name].append(auc(pooled_scores[name][idx], y_all[idx]) - base)
    print(
        "\npooled AUC, leave-one-season-out: "
        + ", ".join(f"{n.split()[0]} {auc(pooled_scores[n], y_all):.3f}" for n in models)
    )
    print(f"{'model':22s} {'pooled - G':>11s} {'90% interval':>20s} {'seasons positive':>17s}")
    verdict_row = None
    for name in diffs:
        lo, hi = np.quantile(diffs[name], [0.05, 0.95])
        point = auc(pooled_scores[name], y_all) - auc(pooled_scores[reference], y_all)
        positive = sum(1 for y in defined if per_year[y][name] > per_year[y][reference])
        print(
            f"{name:22s} {point:>+11.3f} [{lo:+.3f}, {hi:+.3f}] {positive:>10d} of {len(defined)}"
        )
        if name.startswith("D"):
            verdict_row = (lo, positive)
    lo, positive = verdict_row
    print(
        f"\nDECISION on D: (a) interval of pooled AUC(D) - AUC(G) above 0: {lo > 0} (lower end {lo:+.3f}); "
        f"(b) positive in >= {IMPROVEMENT_MIN_POSITIVE} of {len(defined)} seasons: {positive >= IMPROVEMENT_MIN_POSITIVE} ({positive})"
    )
    print(
        "  ->",
        "IMPROVEMENT" if lo > 0 and positive >= IMPROVEMENT_MIN_POSITIVE else "NO_IMPROVEMENT",
    )


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2 or argv[1] not in ("data", "run", "forecast", "seasons", "extras"):
        print(__doc__)
        return 2
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    if argv[1] == "extras":
        run_extras(cache)
    elif argv[1] == "seasons":
        run_seasons(cache)
    elif argv[1] == "forecast":
        run_forecast(cache)
    elif argv[1] == "data":
        run_data(cache)
    else:
        out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
        run_pipeline(cache, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
