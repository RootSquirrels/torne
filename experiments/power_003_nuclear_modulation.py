"""POWER-003 - daily volume of French nuclear modulation (capacity available but not produced).

Knowledge product. Target quantity: for each day, the energy (GWh) that the reactors that were running could have delivered at
their declared available power and did not, i.e. the load-following / modulation volume. No public source publishes it. It is
measurable from two open sources already used in POWER-002: actual output per unit (ENTSO-E A73, 15 minutes) and the declared
unavailabilities (EDF REMIT). The expected use is market analysis: modulation is the nuclear fleet's response to low or negative
prices, so its volume says how much of the fleet's flexibility is being used and how close it is to its floor.

DATA. Output: ENTSO-E A73 per unit, 1 Nov 2025 - 31 Oct 2026 (cached by POWER-002). Declarations: EDF REMIT, latest version of
each identifier kept if Active, records with ``puissance_maximale_mw`` = 0 ignored, the declared available power of a unit being
Pmax minus the largest loss declared at that slot. Prices: Energy-Charts FR day-ahead (CC BY 4.0), used only as the independent
check below. Days are UTC days.

DEFINITION. Slot (unit u, 15 min): u is "running" if output >= F * Pmax (F = 0.2); the modulation of the slot is
max(declared available power - output, 0) if running, else 0 (units below F * Pmax are shutdowns, trips or ramps, not
modulation). The daily value is the sum of slot modulations x 0.25 h, in GWh. Holes of the output series are filled with the
last value (as in POWER-002).

PROTOCOL, fixed before any result was computed
    Independent check (the market response the quantity is meant to track):
    (a) coverage: the series exists for at least 95 % of the days of the period;
    (b) Spearman correlation between the daily modulation and the number of hours with a negative day-ahead price that day is at
        least 0.5;
    (c) weekend days have a higher median modulation than weekdays (one-sided Mann-Whitney, p < 0.01), an ex-ante known pattern of
        the fleet's behaviour;
    (d) robustness: with F = 0.3 the correlation of (b) stays at least 0.4.
    Decision PRODUCT_VIABLE if (a)-(d) hold. Otherwise NO_PRODUCT.
    Reported, not tested: the annual total in TWh, the monthly totals, and the share of the days with more than 20 GWh.
    Limits stated in advance: end-of-cycle power coast-down (stretch-out) and fuel-saving reductions that are not declared in REMIT
    would be counted as modulation; the check on prices cannot separate them. The result is a measurement, not a forecast.

Usage:

    uv run python experiments/power_003_nuclear_modulation.py --cache DIR
"""

from __future__ import annotations

import collections
import datetime as dt
import pathlib
import statistics
import sys

import numpy as np
from power_001_golfech import cached
from power_001_price_link import fetch_month
from power_002_declared_vs_realised import (
    N_SLOTS,
    START,
    load_declarations,
    load_output,
    normal,
    parse_time,
    slot_range,
)
from scipy.stats import mannwhitneyu, spearmanr

FRACTIONS = (0.2, 0.3)
MIN_CORRELATION, MIN_CORRELATION_ROBUST = 0.5, 0.4
SLOTS_PER_DAY = 96


def build(output: dict, records: list[dict]):
    latest: dict[str, dict] = {}
    for r in records:
        k = r["identifiant"]
        if k not in latest or r["numero_de_version"] > latest[k]["numero_de_version"]:
            latest[k] = r
    pmax: dict[str, float] = {}
    for r in records:
        pmax[normal(r["nom"])] = max(pmax.get(normal(r["nom"]), 0.0), r["puissance_maximale_mw"])
    out, avail = {}, {}
    for u, series in output.items():
        g = np.array([np.nan if v is None else v for v in series])
        if np.isnan(g).all():
            continue
        if np.isnan(g).any():
            index = np.where(~np.isnan(g), np.arange(N_SLOTS), 0)
            np.maximum.accumulate(index, out=index)
            g = g[index]
        out[u] = g
        avail[u] = np.full(N_SLOTS, pmax.get(u, 1300.0))
    for r in latest.values():
        u = normal(r["nom"])
        if r["status"] != "Active" or u not in out or r["puissance_maximale_mw"] <= 0:
            continue
        slots = slot_range(parse_time(r["date_de_debut"]), parse_time(r["date_de_fin"]))
        if slots:
            declared = max(
                pmax[u] - (r["puissance_maximale_mw"] - r["puissance_disponible_mw"]), 0.0
            )
            sel = np.arange(slots.start, slots.stop)
            avail[u][sel] = np.minimum(avail[u][sel], declared)
    return out, avail, pmax


def daily_modulation(out: dict, avail: dict, pmax: dict, fraction: float) -> np.ndarray:
    total = np.zeros(N_SLOTS)
    for u, g in out.items():
        running = g >= fraction * pmax.get(u, 1300.0)
        total += np.where(running, np.maximum(avail[u] - g, 0.0), 0.0)
    return total.reshape(-1, SLOTS_PER_DAY).sum(axis=1) * 0.25 / 1000.0  # GWh per UTC day


def load_prices() -> dict[str, float]:
    """UTC date -> hours with a negative day-ahead price."""
    hours: dict[str, float] = collections.defaultdict(float)
    counts: dict[str, int] = collections.defaultdict(int)
    negatives: dict[str, int] = collections.defaultdict(int)
    first = START
    while first < START + dt.timedelta(days=366):
        prices, stamps, _ = fetch_month(first.year, first.month)
        for value, stamp in zip(prices, stamps, strict=True):
            if value is None:
                continue
            day = dt.datetime.fromtimestamp(stamp, dt.UTC).date().isoformat()
            counts[day] += 1
            negatives[day] += value < 0
        first = (first + dt.timedelta(days=32)).replace(day=1)
    for day, n in counts.items():
        if n >= 23:
            hours[day] = 24.0 * negatives[day] / n
    return dict(hours)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    output = cached(cache, "a73_output.json.gz", load_output)
    records = cached(cache, "remit_all.json.gz", load_declarations)
    negative_hours = cached(cache, "negative_hours.json.gz", load_prices)
    out, avail, pmax = build(output, records)
    days = [(START + dt.timedelta(days=i)).date() for i in range(N_SLOTS // SLOTS_PER_DAY)]
    series = {f: daily_modulation(out, avail, pmax, f) for f in FRACTIONS}
    mod = series[0.2]

    covered = sum(1 for d in days if d.isoformat() in negative_hours)
    coverage = len(days) / (N_SLOTS // SLOTS_PER_DAY)
    print(
        f"units {len(out)}; days in the series {len(days)} (coverage {coverage:.0%}); days with a price check {covered}"
    )
    print(
        f"total modulation over the year: {mod.sum() / 1000:.1f} TWh; median day {np.median(mod):.1f} GWh; days > 20 GWh {np.mean(mod > 20):.0%}"
    )
    print(
        "monthly totals (TWh): "
        + ", ".join(
            f"{m}: {sum(v for d, v in zip(days, mod, strict=True) if d.strftime('%Y-%m') == m) / 1000:.2f}"
            for m in sorted({d.strftime("%Y-%m") for d in days})
        )
    )

    def correlation(values: np.ndarray) -> float:
        pairs = [
            (v, negative_hours[d.isoformat()])
            for d, v in zip(days, values, strict=True)
            if d.isoformat() in negative_hours
        ]
        return float(spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic)

    rho, rho_robust = correlation(series[0.2]), correlation(series[0.3])
    weekend = np.array([d.weekday() >= 5 for d in days])
    test = mannwhitneyu(mod[weekend], mod[~weekend], alternative="greater")
    print(f"\n(b) Spearman(modulation, negative-price hours), F = 0.2: {rho:+.2f}")
    print(
        f"(c) median modulation weekend {np.median(mod[weekend]):.1f} vs weekday {np.median(mod[~weekend]):.1f} GWh; Mann-Whitney p = {test.pvalue:.4f}"
    )
    print(f"(d) Spearman with F = 0.3: {rho_robust:+.2f}")
    a, b, c, d = (
        coverage >= 0.95,
        rho >= MIN_CORRELATION,
        test.pvalue < 0.01,
        rho_robust >= MIN_CORRELATION_ROBUST,
    )
    print(
        f"\nDECISION: (a) coverage {a}; (b) correlation >= {MIN_CORRELATION}: {b}; (c) weekend higher: {c}; (d) robust: {d}"
    )
    print("  ->", "PRODUCT_VIABLE" if all((a, b, c, d)) else "NO_PRODUCT")
    if cache is not None:
        with open(cache / "nuclear_modulation_daily.csv", "w", encoding="utf-8") as handle:
            handle.write("date_utc,modulation_gwh,negative_price_hours\n")
            for day, value in zip(days, mod, strict=True):
                handle.write(f"{day},{value:.2f},{negative_hours.get(day.isoformat(), '')}\n")
    _ = statistics
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
