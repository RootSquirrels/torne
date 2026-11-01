"""MACRO-001 - nowcast of French industrial production from electricity demand, about 40 days before the official figure.

Knowledge product. Target: year-on-year change of the French industrial production index (Eurostat sts_inpr_m, NACE B-D,
seasonally and calendar adjusted, FR), published about 40 days after the end of the month. Input: the national electricity
consumption (RTE eco2mix via ODRE), known the day after, corrected for temperature and for the number of working days. Output:
a monthly estimate available on the first day of the next month. The independent reference is the official figure, published
later: every nowcast can be scored.

Five conditions. Target: defined. Data: three open sources, no key. Method: regression, executable below. Reference: Eurostat
release. Economic use: macro and credit desks wait for the official figure; a better estimate 40 days earlier is the product.
Not yet known to be differentiating: electricity as an activity proxy is a published idea, so the test is whether it beats the
trivial estimate at this lead in France.

PROTOCOL, fixed before any data was downloaded
    Months: January 2013 - the last month available in both sources. Target y(t) = 100 * (log IP(t) - log IP(t-12)).
    Features at the first day of month t+1: x1 = 100 * (log C(t) - log C(t-12)) with C the monthly mean consumption; x2 = change
    over 12 months of the mean heating degree days (base 17 degC, mean of Paris, Lyon, Toulouse); x3 = same for cooling degree
    days (base 22 degC); x4 = change over 12 months of the number of working days (Monday-Friday minus French public holidays).
    Model: least squares of y on x1..x4, expanding window, estimated only on months whose target was published before the
    forecast date (target of month t-2 and earlier, since the official figure of month t-2 appears about 40 days after its end).
    Test: pseudo-real-time forecasts for every month from January 2018.
    Benchmarks: B1 = the latest published y/y (month t-2), B2 = the mean of the past 12 published y/y.
    Metric: RMSE. Moving-block bootstrap over months (blocks of 6, 2 000 resamples, seed 20261102) of the difference of squared
    errors, model minus benchmark.
    Decision NOWCAST_VIABLE only if: (a) RMSE(model) <= 0.9 * RMSE(B1) and <= 0.9 * RMSE(B2); (b) the 90 % interval of the mean
    difference of squared errors against B1 is below 0; (c) the same holds in both halves, 2018-2021 and 2022 onwards, by
    point estimate (model RMSE below both benchmarks in each half). Otherwise NO_NOWCAST.
    Sensitivity, declared now and not part of the decision: the same excluding March 2020 - June 2021.
    Limits stated in advance: the consumption series is the consolidated one, which can differ slightly from the figure available
    on the first day; no data revision of the official index is tracked (the latest vintage is used for all months).

Usage:

    uv run python experiments/macro_001_industry_nowcast.py --cache DIR
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import urllib.parse
import urllib.request

import numpy as np
from basin_001_catchment import fetch_json
from power_001_golfech import OPEN_METEO, cached

EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_inpr_m"
ODRE = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/records"
CITIES = {"paris": (48.85, 2.35), "lyon": (45.76, 4.84), "toulouse": (43.60, 1.44)}
SEED = 20261102
N_BOOTSTRAP = 2000
BLOCK = 6
FIRST_TEST = "2018-01"
PUBLICATION_LAG = (
    2  # the official figure of month t-2 is the latest known at the start of month t+1
)
MIN_GAIN = 0.9


def load_production() -> dict[str, float]:
    query = urllib.parse.urlencode(
        {
            "format": "JSON",
            "lang": "EN",
            "freq": "M",
            "indic_bt": "PRD",
            "nace_r2": "B-D",
            "s_adj": "SCA",
            "unit": "I21",
            "geo": "FR",
        }
    )
    page = fetch_json(f"{EUROSTAT}?{query}", timeout=120.0)
    if page is None:
        raise RuntimeError("Eurostat unavailable")
    times = page["dimension"]["time"]["category"]["index"]
    return {t: float(page["value"][str(i)]) for t, i in times.items() if str(i) in page["value"]}


def load_consumption() -> dict[str, float]:
    """Month -> mean national consumption (MW), only months with at least 95 % of their half-hours."""
    month_key = "date_format(date_heure,'yyyy-MM')"
    result = {}
    for offset in (0, 100):
        url = (
            f"{ODRE}?select={urllib.parse.quote('avg(consommation) as c, count(*) as n, ' + month_key + ' as m')}"
            f"&group_by={urllib.parse.quote(month_key)}&limit=100&offset={offset}"
        )
        with urllib.request.urlopen(url, timeout=180) as response:
            page = json.loads(response.read())
        for r in page["results"]:
            month = r[month_key]
            if month is None:
                continue
            year, m = int(month[:4]), int(month[5:])
            days = (dt.date(year + (m == 12), m % 12 + 1, 1) - dt.date(year, m, 1)).days
            if r["c"] is not None and r["n"] >= 0.95 * 96 * days:
                result[month] = float(r["c"])
    return result


def load_temperature() -> dict[str, list[float]]:
    total: dict[str, list[float]] = {}
    for lat, lon in CITIES.values():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2012-01-01",
            "end_date": "2026-10-31",
            "daily": "temperature_2m_mean",
            "timezone": "Europe/Paris",
        }
        page = fetch_json(f"{OPEN_METEO}?{urllib.parse.urlencode(params)}", timeout=120.0)
        if page is None:
            raise RuntimeError("air archive unavailable")
        for day, value in zip(
            page["daily"]["time"], page["daily"]["temperature_2m_mean"], strict=True
        ):
            if value is not None:
                total.setdefault(day, []).append(value)
    return {d: v for d, v in total.items() if len(v) == len(CITIES)}


def easter(year: int) -> dt.date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def holidays(year: int) -> set[dt.date]:
    e = easter(year)
    fixed = [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)]
    return {dt.date(year, m, d) for m, d in fixed} | {e + dt.timedelta(days=n) for n in (1, 39, 50)}


def working_days(month: str) -> int:
    year, m = int(month[:4]), int(month[5:])
    day, count, off = dt.date(year, m, 1), 0, holidays(year)
    while day.month == m:
        count += day.weekday() < 5 and day not in off
        day += dt.timedelta(days=1)
    return count


def shift(month: str, k: int) -> str:
    year, m = int(month[:4]), int(month[5:]) - 1 - k
    return f"{year + m // 12}-{m % 12 + 1:02d}"


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    production = cached(cache, "ip_fr.json.gz", load_production)
    consumption = cached(cache, "conso_monthly.json.gz", load_consumption)
    temperature = cached(cache, "temp_cities.json.gz", load_temperature)
    hdd: dict[str, list[float]] = {}
    cdd: dict[str, list[float]] = {}
    for day, values in temperature.items():
        t = float(np.mean(values))
        hdd.setdefault(day[:7], []).append(max(17.0 - t, 0.0))
        cdd.setdefault(day[:7], []).append(max(t - 22.0, 0.0))
    hdd_m = {m: float(np.mean(v)) for m, v in hdd.items()}
    cdd_m = {m: float(np.mean(v)) for m, v in cdd.items()}
    months = sorted(set(production) & set(consumption))
    print(
        f"production months {len(production)} ({min(production)}..{max(production)}); consumption months {len(consumption)} ({min(consumption)}..{max(consumption)})"
    )
    y, x = {}, {}
    for m in months:
        p = shift(m, 12)
        if p in production and p in consumption and m in hdd_m and p in hdd_m:
            y[m] = 100 * (np.log(production[m]) - np.log(production[p]))
            x[m] = [
                100 * (np.log(consumption[m]) - np.log(consumption[p])),
                hdd_m[m] - hdd_m[p],
                cdd_m[m] - cdd_m[p],
                float(working_days(m) - working_days(p)),
            ]
    usable = sorted(y)
    print(f"usable months {len(usable)} ({usable[0]}..{usable[-1]})")
    rows = []
    for m in usable:
        if m < FIRST_TEST:
            continue
        known_until = shift(m, PUBLICATION_LAG)
        train = [k for k in usable if k <= known_until]
        if len(train) < 36:
            continue
        a = np.column_stack([np.ones(len(train)), np.array([x[k] for k in train])])
        beta = np.linalg.lstsq(a, np.array([y[k] for k in train]), rcond=None)[0]
        forecast = float(np.concatenate([[1.0], x[m]]) @ beta)
        past = [y[k] for k in usable if k <= known_until][-12:]
        rows.append((m, y[m], forecast, y.get(known_until, past[-1]), float(np.mean(past))))
    months_t = [r[0] for r in rows]
    actual = np.array([r[1] for r in rows])
    err = {
        "model": np.array([r[2] for r in rows]) - actual,
        "B1": np.array([r[3] for r in rows]) - actual,
        "B2": np.array([r[4] for r in rows]) - actual,
    }

    def report(mask: np.ndarray, label: str) -> dict:
        rmse = {k: float(np.sqrt(np.mean(v[mask] ** 2))) for k, v in err.items()}
        print(
            f"  {label:34s} n = {int(mask.sum()):3d}  RMSE model {rmse['model']:.2f}  B1 {rmse['B1']:.2f}  B2 {rmse['B2']:.2f}  (points of y/y)"
        )
        return rmse

    print(f"\nPseudo-real-time forecasts, {months_t[0]}..{months_t[-1]}")
    full = np.ones(len(rows), bool)
    first_half = np.array([m < "2022-01" for m in months_t])
    rmse = report(full, "all months")
    r1, r2 = report(first_half, "2018-2021"), report(~first_half, "2022 onwards")
    covid = np.array([not ("2020-03" <= m <= "2021-06") for m in months_t])
    report(covid, "excluding 2020-03..2021-06 (sens.)")
    rng = np.random.default_rng(SEED)
    n = len(rows)
    diffs = []
    d_obs = err["model"] ** 2 - err["B1"] ** 2
    for _ in range(N_BOOTSTRAP):
        starts = rng.integers(0, n - BLOCK + 1, size=int(np.ceil(n / BLOCK)))
        idx = (starts[:, None] + np.arange(BLOCK)[None, :]).reshape(-1)[:n]
        diffs.append(d_obs[idx].mean())
    lo, hi = np.quantile(diffs, [0.05, 0.95])
    print(
        f"\nmean difference of squared errors, model - B1: {d_obs.mean():+.2f}  90% interval [{lo:+.2f}, {hi:+.2f}]"
    )
    a = rmse["model"] <= MIN_GAIN * rmse["B1"] and rmse["model"] <= MIN_GAIN * rmse["B2"]
    b = hi < 0
    c = all(r["model"] < r["B1"] and r["model"] < r["B2"] for r in (r1, r2))
    print(
        f"DECISION: (a) RMSE <= 0.9 x both benchmarks: {a}; (b) interval below 0: {b}; (c) better than both in each half: {c}"
    )
    print("  ->", "NOWCAST_VIABLE" if (a and b and c) else "NO_NOWCAST")
    last = rows[-1]
    print(f"last nowcast ({last[0]}): y/y {last[2]:+.2f} points; official {last[1]:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
