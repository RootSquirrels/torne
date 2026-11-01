"""POWER-001 economic gate - do environmental nuclear curtailments move the French day-ahead price?

The Golfech tests (``power_001_golfech.py``) showed that a limitation alert is a function of the weather forecast. The
question left for the economic gate is different: when nuclear power is declared lost for environmental reasons, does the
French day-ahead price react, beyond the weather and the season?

DATA
    Prices: Energy-Charts API (``api.energy-charts.info/price``, bidding zone FR, hourly day-ahead, EUR/MWh), no key. Daily
    mean needs at least 23 hourly values. The ENTSO-E token was not found in ``.env`` (no variable of that name), so this
    open republication was used; the licence text the API returns is printed.
    Curtailment: EDF REMIT history, all nuclear units, records whose text declares an environmental external cause; latest
    version of each identifier kept only if Active; the power lost on a day is the sum over units of the largest declared
    shortfall that day (GW).
    Weather control: mean daily air temperature of Paris, Lyon and Toulouse (ERA5 via Open-Meteo), a demand proxy.

PROTOCOL, fixed before any price was downloaded
    Population: days from 1 June to 30 September, 2018-2026.
    Model: price(d) = a(year, month) + b * lost_GW(d) + c * temperature(d) + e * weekend(d) + error, a(year, month) being
    a fixed effect that absorbs the gas-price regime and the season (within-month estimator). Newey-West standard errors
    (7 lags, computed inside each summer).
    Decision PRICE_LINK only if (a) the 90 % interval of b is above 0, (b) b >= 1 EUR/MWh per GW, and (c) the placebo, the
    same model with lost_GW(d + 7) in place of lost_GW(d), has a 90 % interval that contains 0 (a future curtailment cannot
    move today's price). Otherwise NO_PRICE_LINK.
    Limits stated in advance: no gas or carbon price is available here (the fixed effects only absorb their monthly mean);
    the day-ahead price already includes the curtailments announced before the auction, so a null result may mean "priced
    in" as much as "no effect"; the curtailments are mostly small against a fleet of about 60 GW.

Usage:

    uv run python experiments/power_001_price_link.py --cache DIR
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from basin_001_catchment import fetch_json
from power_001_golfech import (
    EDF,
    EDF_HISTORY,
    OPEN_METEO,
    cached,
    in_summer,
    latest_active,
    lost_power_by_day,
)

ENERGY_CHARTS = "https://api.energy-charts.info/price"
YEARS = range(2018, 2027)
CITIES = {"Paris": (48.85, 2.35), "Lyon": (45.76, 4.84), "Toulouse": (43.60, 1.44)}
MIN_EFFECT_EUR_PER_GW = 1.0
NW_LAGS = 7


def fetch_month(year: int, month: int) -> tuple[list[float], list[int], str]:
    last = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)).day
    url = f"{ENERGY_CHARTS}?bzn=FR&start={year}-{month:02d}-01&end={year}-{month:02d}-{last:02d}"
    for attempt in range(8):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"accept": "application/json"}), timeout=90
            ) as response:
                page = json.loads(response.read())
            return page["price"], page["unix_seconds"], str(page.get("license_info", ""))
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 7:
                raise
            time.sleep(6 * (attempt + 1))
    raise RuntimeError("unreachable")


def load_prices() -> dict[str, float]:
    """ISO date -> daily mean day-ahead price (EUR/MWh), summers only."""
    out: dict[str, float] = {}
    licence = ""
    for year in YEARS:
        for month in (6, 7, 8, 9):
            prices, stamps, licence = fetch_month(year, month)
            buckets: dict[str, list[float]] = collections.defaultdict(list)
            for value, stamp in zip(prices, stamps, strict=True):
                if value is not None:
                    day = dt.datetime.fromtimestamp(stamp, dt.UTC) + dt.timedelta(
                        hours=2
                    )  # summer time, CEST
                    buckets[day.date().isoformat()].append(value)
            out.update({d: statistics.fmean(v) for d, v in buckets.items() if len(v) >= 23})
            time.sleep(2.5)
    out["__license__"] = licence  # type: ignore[assignment]
    return out


def load_national_events() -> list[dict]:
    q = urllib.parse.quote("environnement")
    qs = urllib.parse.quote('filiere:"Nucléaire"')
    select = "nom,date_de_debut,date_de_fin,puissance_maximale_mw,puissance_disponible_mw,numero_de_version,status,identifiant"
    page = fetch_json(
        f"{EDF}/{EDF_HISTORY}/lines?size=10000&q={q}&qs={qs}&select={select}&sort=date_de_debut"
    )
    if page is None:
        raise RuntimeError("EDF history unavailable")
    return page["results"]


def load_temperature() -> dict[str, float]:
    total: dict[str, list[float]] = collections.defaultdict(list)
    for lat, lon in CITIES.values():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2018-01-01",
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
                total[day].append(value)
    return {d: statistics.fmean(v) for d, v in total.items() if len(v) == len(CITIES)}


def within(x: np.ndarray, groups: np.ndarray) -> np.ndarray:
    out = x.astype(float).copy()
    for g in np.unique(groups):
        mask = groups == g
        out[mask] -= out[mask].mean(axis=0)
    return out


def fit(rows: list[dict], lost_key: str, squared_temperature: bool = False) -> dict:
    y = np.array([r["price"] for r in rows])
    columns = [[r[lost_key] for r in rows], [r["temp"] for r in rows], [r["weekend"] for r in rows]]
    if squared_temperature:
        columns.append([r["temp"] ** 2 for r in rows])
    x = np.column_stack(columns).astype(float)
    groups = np.array([r["fe"] for r in rows])
    seasons = np.array([r["year"] for r in rows])
    yw, xw = within(y, groups), within(x, groups)
    xtx_inv = np.linalg.inv(xw.T @ xw)
    beta = xtx_inv @ xw.T @ yw
    resid = yw - xw @ beta
    scores = xw * resid[:, None]
    meat = np.zeros((x.shape[1], x.shape[1]))
    for season in np.unique(seasons):
        s = scores[seasons == season]
        meat += s.T @ s
        for lag in range(1, NW_LAGS + 1):
            weight = 1 - lag / (NW_LAGS + 1)
            gamma = s[lag:].T @ s[:-lag]
            meat += weight * (gamma + gamma.T)
    se = np.sqrt(np.diag(xtx_inv @ meat @ xtx_inv))
    z = 1.6449
    return {
        "b": float(beta[0]),
        "lo": float(beta[0] - z * se[0]),
        "hi": float(beta[0] + z * se[0]),
        "se": float(se[0]),
        "temp": float(beta[1]),
        "n": len(rows),
    }


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    prices = cached(cache, "prices_fr.json.gz", load_prices)
    print(
        "price licence text returned by the API:",
        prices.pop("__license__")[:160].replace("\n", " "),
    )
    temperature = cached(cache, "temperature_3cities.json.gz", load_temperature)
    events = latest_active(cached(cache, "national_events.json.gz", load_national_events))
    lost = lost_power_by_day(events)
    print(
        f"daily prices (summers): {len(prices)}; active national environmental events kept: {len(events)}"
    )
    rows = []
    for iso, price in sorted(prices.items()):
        day = dt.date.fromisoformat(iso)
        if not in_summer(day) or iso not in temperature:
            continue
        rows.append(
            {
                "day": day,
                "year": day.year,
                "fe": day.year * 100 + day.month,
                "price": price,
                "temp": temperature[iso],
                "weekend": float(day.weekday() >= 5),
                "lost": lost.get(day, 0.0) / 1000.0,
                "lost_future": lost.get(day + dt.timedelta(days=7), 0.0) / 1000.0,
            }
        )
    print(f"days in the regression: {len(rows)}")
    print("\nnational curtailment for an environmental cause (GW lost per day, summers):")
    for year in YEARS:
        values = [r["lost"] for r in rows if r["year"] == year]
        print(
            f"  {year}: days with a curtailment {sum(1 for v in values if v > 0):>3d}/{len(values)}; mean {np.mean(values):.2f} GW; max {max(values):.2f} GW"
        )
    main_fit, placebo = fit(rows, "lost"), fit(rows, "lost_future")
    print("\nOLS with year-month fixed effects, Newey-West 7 lags, 90 % intervals")
    print(
        f"  b (price per GW curtailed today):      {main_fit['b']:+.2f} EUR/MWh per GW  [{main_fit['lo']:+.2f}, {main_fit['hi']:+.2f}]  (n = {main_fit['n']})"
    )
    print(f"  temperature (EUR/MWh per degC):        {main_fit['temp']:+.2f}")
    print(
        f"  placebo: curtailment 7 days AFTER:     {placebo['b']:+.2f} EUR/MWh per GW  [{placebo['lo']:+.2f}, {placebo['hi']:+.2f}]"
    )
    a = main_fit["lo"] > 0
    b = main_fit["b"] >= MIN_EFFECT_EUR_PER_GW
    c = placebo["lo"] <= 0 <= placebo["hi"]
    print(
        f"\nDECISION: (a) interval of b above 0: {a}; (b) b >= {MIN_EFFECT_EUR_PER_GW} EUR/MWh per GW: {b}; (c) placebo interval contains 0: {c}"
    )
    print("  ->", "PRICE_LINK" if (a and b and c) else "NO_PRICE_LINK")

    # ROBUSTNESS, added after the result and NOT part of the decision: the 2026 summer carries almost all of the exposure.
    print("\nROBUSTNESS (descriptive, added after the result)")
    cases = {
        "all summers, quadratic temperature": (rows, True),
        "without 2026": ([r for r in rows if r["year"] != 2026], False),
        "without 2026, quadratic temperature": ([r for r in rows if r["year"] != 2026], True),
        "2026 only": ([r for r in rows if r["year"] == 2026], False),
        "2026 only, quadratic temperature": ([r for r in rows if r["year"] == 2026], True),
    }
    for label, (subset, squared) in cases.items():
        result = fit(subset, "lost", squared)
        print(
            f"  {label:38s} b = {result['b']:+6.2f} EUR/MWh per GW  [{result['lo']:+6.2f}, {result['hi']:+6.2f}]  n = {result['n']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
