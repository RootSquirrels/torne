"""MACRO-002 - screen of French monthly Eurostat series for a weather/energy-driven nowcast.

MACRO-001 failed because its target (industrial production) is smooth once the shock years are removed: the naive estimate,
the last published year-on-year change, had an error of about 2 points and nothing cheap beat it. Rule drawn from it: test the
naive benchmark FIRST. This script screens many series with one protocol and keeps only those where the naive estimate is
poor AND a direct fast indicator exists.

Series (Eurostat, FR, seasonally and calendar adjusted, index 2021 = 100, monthly volume): industry sts_inpr_m: B-D, C, D, B,
C10-C12, C20, C24, C25, C28, C29; construction sts_copr_m: F, F41, F42, F43. Targets are y/y changes in log points.

Fast features available the day after the month ends (same as MACRO-001, plus two weather variables): y/y change of the mean
national consumption (RTE eco2mix via ODRE), of heating and cooling degree days, of the monthly precipitation and of the number
of frost days (daily minimum below 0 degC), means over Paris, Lyon and Toulouse (ERA5 via Open-Meteo), and the change in
working days.

PROTOCOL, fixed before any data was downloaded
    For each series, MACRO-001's protocol: expanding-window least squares on the features, estimated on months whose target was
    published before the forecast date (publication lag 2 months), pseudo-real-time forecasts from January 2018, benchmarks B1
    (latest published y/y) and B2 (mean of the last 12 published y/y), RMSE, moving-block bootstrap over months (blocks of 6,
    2 000 resamples, seed 20261102) of the difference of squared errors model - B1.
    Eligible only if the naive error is large: min(RMSE B1, RMSE B2) >= 2.0 log points over 2022 onwards. Otherwise the series is
    reported as SMOOTH and not scored (a smooth series cannot yield a product, see MACRO-001).
    A series is NOWCAST_VIABLE if: (a) RMSE model <= 0.9 x both benchmarks over the whole test period and over 2022 onwards;
    (b) the one-sided bootstrap bound at level 0.05 / N is below 0, N being the number of eligible series (Bonferroni); (c) the
    model beats both benchmarks in each of 2018-2021 and 2022 onwards. Otherwise NO_NOWCAST.
    Limits stated in advance: the latest vintage of each official index is used for every month; the consolidated consumption
    series is used; no series-specific tuning of the features is allowed.

Usage:

    uv run python experiments/macro_002_screen.py --cache DIR
"""

from __future__ import annotations

import pathlib
import sys
import urllib.parse

import numpy as np
from basin_001_catchment import fetch_json
from macro_001_industry_nowcast import (
    BLOCK,
    CITIES,
    EUROSTAT,
    FIRST_TEST,
    N_BOOTSTRAP,
    PUBLICATION_LAG,
    SEED,
    load_consumption,
    shift,
    working_days,
)
from power_001_golfech import OPEN_METEO, cached

CONSTRUCTION = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_copr_m"
SERIES = [
    ("sts_inpr_m", nace)
    for nace in ("B-D", "C", "D", "B", "C10-C12", "C20", "C24", "C25", "C28", "C29")
] + [("sts_copr_m", nace) for nace in ("F", "F41", "F42", "F43")]
MIN_NAIVE_RMSE = 2.0
MIN_GAIN = 0.9


def load_series(dataset: str, nace: str) -> dict[str, float] | None:
    base = EUROSTAT if dataset == "sts_inpr_m" else CONSTRUCTION
    query = urllib.parse.urlencode(
        {
            "format": "JSON",
            "lang": "EN",
            "freq": "M",
            "indic_bt": "PRD",
            "nace_r2": nace,
            "s_adj": "SCA",
            "unit": "I21",
            "geo": "FR",
        }
    )
    page = fetch_json(f"{base}?{query}", timeout=120.0)
    if not page or not page.get("value"):
        return None
    times = page["dimension"]["time"]["category"]["index"]
    return {t: float(page["value"][str(i)]) for t, i in times.items() if str(i) in page["value"]}


def load_weather() -> dict[str, dict[str, float]]:
    """Month -> mean over three cities of HDD, CDD, precipitation (mm/day) and frost-day share."""
    daily: dict[str, list[list[float]]] = {}
    for lat, lon in CITIES.values():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2012-01-01",
            "end_date": "2026-10-31",
            "daily": "temperature_2m_mean,temperature_2m_min,precipitation_sum",
            "timezone": "Europe/Paris",
        }
        page = fetch_json(f"{OPEN_METEO}?{urllib.parse.urlencode(params)}", timeout=120.0)
        if page is None:
            raise RuntimeError("air archive unavailable")
        d = page["daily"]
        for day, tm, tn, pr in zip(
            d["time"],
            d["temperature_2m_mean"],
            d["temperature_2m_min"],
            d["precipitation_sum"],
            strict=True,
        ):
            if None not in (tm, tn, pr):
                daily.setdefault(day, []).append([tm, tn, pr])
    monthly: dict[str, list[list[float]]] = {}
    for day, rows in daily.items():
        if len(rows) == len(CITIES):
            tm, tn, pr = np.mean(rows, axis=0)
            monthly.setdefault(day[:7], []).append(
                [max(17 - tm, 0), max(tm - 22, 0), pr, float(tn < 0)]
            )
    return {
        m: dict(zip(("hdd", "cdd", "precip", "frost"), np.mean(v, axis=0).tolist(), strict=True))
        for m, v in monthly.items()
    }


def evaluate(
    production: dict[str, float],
    consumption: dict[str, float],
    weather: dict[str, dict[str, float]],
):
    y, x = {}, {}
    for m in sorted(set(production) & set(consumption)):
        p = shift(m, 12)
        if p in production and p in consumption and m in weather and p in weather:
            y[m] = 100 * (np.log(production[m]) - np.log(production[p]))
            x[m] = [
                100 * (np.log(consumption[m]) - np.log(consumption[p])),
                *(weather[m][k] - weather[p][k] for k in ("hdd", "cdd", "precip", "frost")),
                float(working_days(m) - working_days(p)),
            ]
    usable = sorted(y)
    rows = []
    for m in usable:
        if m < FIRST_TEST:
            continue
        known = shift(m, PUBLICATION_LAG)
        train = [k for k in usable if k <= known]
        if len(train) < 36:
            continue
        a = np.column_stack([np.ones(len(train)), np.array([x[k] for k in train])])
        beta = np.linalg.lstsq(a, np.array([y[k] for k in train]), rcond=None)[0]
        past = [y[k] for k in train][-12:]
        rows.append(
            (
                m,
                y[m],
                float(np.concatenate([[1.0], x[m]]) @ beta),
                y[train[-1]],
                float(np.mean(past)),
            )
        )
    return rows


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    consumption = cached(cache, "conso_monthly.json.gz", load_consumption)
    weather = cached(cache, "weather_monthly.json.gz", load_weather)
    results = []
    for dataset, nace in SERIES:
        production = cached(
            cache, f"{dataset}_{nace}.json.gz", lambda d=dataset, n=nace: load_series(d, n) or {}
        )
        if len(production) < 100:
            print(f"{dataset} {nace:8s} not available")
            continue
        rows = evaluate(production, consumption, weather)
        months = [r[0] for r in rows]
        actual = np.array([r[1] for r in rows])
        err = {
            "model": np.array([r[2] for r in rows]) - actual,
            "B1": np.array([r[3] for r in rows]) - actual,
            "B2": np.array([r[4] for r in rows]) - actual,
        }
        late = np.array([m >= "2022-01" for m in months])
        rm = lambda e, mask: float(np.sqrt(np.mean(e[mask] ** 2)))  # noqa: E731
        every = np.ones(len(rows), bool)
        naive_late = min(rm(err["B1"], late), rm(err["B2"], late))
        results.append((dataset, nace, rows, err, late, every, naive_late))
    eligible = [r for r in results if r[6] >= MIN_NAIVE_RMSE]
    n_tests = max(len(eligible), 1)
    level = 0.05 / n_tests
    rng = np.random.default_rng(SEED)
    print(
        f"\n{len(results)} series loaded; eligible (naive RMSE >= {MIN_NAIVE_RMSE} from 2022): {len(eligible)}; bootstrap level {level:.4f}"
    )
    print(
        f"{'series':16s} {'naive22+':>8s} {'model22+':>8s} {'model all':>9s} {'naive all':>9s}  verdict"
    )
    for dataset, nace, rows, err, late, every, naive_late in results:
        n = len(rows)
        rm = lambda e, mask: float(np.sqrt(np.mean(e[mask] ** 2)))  # noqa: E731
        line = f"{dataset[4:8]} {nace:10s} {naive_late:8.2f} {rm(err['model'], late):8.2f} {rm(err['model'], every):9.2f} {min(rm(err['B1'], every), rm(err['B2'], every)):9.2f}"
        if naive_late < MIN_NAIVE_RMSE:
            print(f"{line}  SMOOTH (not scored)")
            continue
        d_obs = err["model"] ** 2 - err["B1"] ** 2
        diffs = []
        for _ in range(N_BOOTSTRAP):
            starts = rng.integers(0, n - BLOCK + 1, size=int(np.ceil(n / BLOCK)))
            idx = (starts[:, None] + np.arange(BLOCK)[None, :]).reshape(-1)[:n]
            diffs.append(d_obs[idx].mean())
        upper = float(np.quantile(diffs, 1 - level))
        early = ~late
        a = all(
            rm(err["model"], mask) <= MIN_GAIN * min(rm(err["B1"], mask), rm(err["B2"], mask))
            for mask in (every, late)
        )
        c = all(
            rm(err["model"], mask) < min(rm(err["B1"], mask), rm(err["B2"], mask))
            for mask in (early, late)
        )
        verdict = "NOWCAST_VIABLE" if (a and upper < 0 and c) else "NO_NOWCAST"
        print(f"{line}  {verdict}  (a={a}, upper bound {upper:+.1f}, c={c})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
