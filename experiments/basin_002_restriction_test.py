"""BASIN-002 pre-pilot economic test - does the antecedent groundwater state already explain summer restrictions?

The economic gate of ``docs/BASIN-002-AQUIFER-FIRST.md`` rests on one claim: a basin-scale groundwater index
could anticipate, months ahead, the drought-restriction level of the coming summer. Before any pilot, this
script checks the premise with the crudest baselines, with no model.

PROTOCOL, fixed before any result was read (the choices below were made after seeing only the structure of the
order files, never their values against the predictors):

Outcome (per year Y in 2012..2023, summer = 1 June to 30 September)
    D(Y) = number of days with a restriction level of at least "alerte" in at least one alert zone whose name
    contains "Yevre" (accent-insensitive; zones "Yevre amont" and "Yevre aval" of the Cher, department 18).
    Secondary: M(Y) = highest level reached in those zones (vigilance 1, alerte 2, alerte renforcee 3, crise 4).
    Source: VigiEau yearly order files (data.gouv.fr, "Donnee Secheresse - VigiEau"). A year without any order
    for those zones is 0. 2024 is not used: the Cher has no order in that file, so absence cannot be told from
    an incomplete file.

Predictors, known on 31 March of year Y
    W(Y) = mean, over the six wells counted for the Yevre candidate, of the standardized March mean level
           (z-score against that well's own Marches of 2001..2025). Needs >= 20 days of March data per well
           and >= 4 wells.
    Q(Y) = standardized log10 of the March mean of the daily mean discharge of gauge K555230001
           (z-score against its own Marches of 2001..2025). Needs >= 20 days.
    Q is the baseline that matters most: the framework orders fix flow thresholds, so the public gauge is the
    trigger itself.

Statistic
    Spearman rank correlation, expected NEGATIVE (a low March level or flow, a long restriction). Reported as
    s = -rho. 90 % bootstrap interval over years (5 000 resamples, seed 20261101), and a two-sided permutation
    p-value (100 000 permutations, same seed).

Decision rule on s(W, D)
    BASELINE_SUFFICES   the interval's lower end is >= 0.8: the crude baseline already explains the outcome.
    PREMISE_UNSUPPORTED the interval's upper end is < 0.5: the antecedent groundwater state does not predict the
                        outcome, so no index of it can.
    ROOM                0.5 <= s < 0.8 and permutation p < 0.05: a signal exists and is not saturated.
    INCONCLUSIVE        anything else.
    If s(Q, D) >= s(W, D), the public gauge discharge predicts at least as well as the wells: an index would
    have to beat it, not only the wells.

Power. With about 12 summers the interval on a rank correlation is roughly +-0.3. This is a gross check for
redundancy or absence of signal, not a measurement of an effect. Restriction levels also depend on the
framework orders in force (they changed in 2021-2022) and on prefectural decisions, so D(Y) is regulatory as
well as physical.

Added rule (applies to every case, changes nothing for the Yevre): fewer than 9 usable years gives the verdict
NOT_TESTABLE.

CASES. ``yevre`` is the protocol above. ``raille`` is the same test, run once, on the second candidate whose
department restricts on groundwater; it is a different basin and is reported separately, never pooled. Its
choices were fixed after seeing only the STRUCTURE of the Isere order files (zone names, types, years present),
never any level against any predictor:

    Outcome   D(Y) = days from 1 June to 30 September at level "alerte" or above in any zone whose name contains
              "bievre" or "valloire" (any type: groundwater zones carrying that name exist only from 2016, the
              same territory being managed through surface zones before). Years 2012..2024 (the Isere has orders
              in the 2024 file, so a missing year can be read as no restriction). Secondary 1: highest level.
              Secondary 2: D restricted to groundwater (SOU) zones, years 2016..2024 only.
    Wells     the four wells counted for the Raille candidate; >= 3 of them with >= 20 March days.
    Gauge     V342431001. Climatology for the z-scores: 1993..2025.

Usage:

    uv run python experiments/basin_002_restriction_test.py --orders-dir DIR_WITH_arretes-YYYY.csv [--case raille]
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import pathlib
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass

import numpy as np
from basin_001_screening import paged
from scipy.stats import spearmanr

HYDRO = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"
CHRONICLES = "https://hubeau.eaufrance.fr/api/v1/niveaux_nappes/chroniques"


@dataclass(frozen=True)
class Case:
    """One basin: its department, alert-zone name keywords, gauge, wells and years."""

    department: str
    zone_keywords: tuple[str, ...]
    gauge: str
    wells: tuple[str, ...]
    years: range
    climatology_years: range
    min_wells: int
    sou_years: range | None = None  # years of the groundwater-zones-only secondary outcome


CASES = {
    "yevre": Case(
        department="18",
        zone_keywords=("yevre",),
        gauge="K555230001",
        wells=(
            "05471X0070/P1",
            "05205X0013/P",
            "05203X0083/P",
            "05472X0029/P",
            "05202X0099/P",
            "05205X0001/PAEP",
        ),
        years=range(2012, 2024),
        climatology_years=range(2001, 2026),
        min_wells=4,
    ),
    "raille": Case(
        department="38",
        zone_keywords=("bievre", "valloire"),
        gauge="V342431001",
        wells=("07704X0079/S", "07477X0048/F1", "07714X0054/F", "07476X0029/S"),
        years=range(2012, 2025),
        climatology_years=range(1993, 2026),
        min_wells=3,
        sou_years=range(2016, 2025),
    ),
}
CASE = CASES["yevre"]
MIN_YEARS_TESTABLE = 9
MIN_MARCH_DAYS = 20
LEVELS = {"vigilance": 1, "alerte": 2, "alerte_renforcee": 3, "crise": 4}
ALERT = 2
SEED = 20261101
N_BOOTSTRAP = 5000
N_PERMUTATIONS = 100_000


def fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def load_orders(orders_dir: pathlib.Path) -> list[dict]:
    """Orders of the department, deduplicated by id across the yearly files."""
    orders: dict[str, dict] = {}
    for path in sorted(orders_dir.rglob("arretes-20*.csv")):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        for row in csv.DictReader(io.StringIO(text)):
            if row["departement"] == CASE.department:
                orders[row["id"]] = row
    return list(orders.values())


def parse_list(text: str) -> list:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    return value if isinstance(value, list) else []


def daily_levels(
    orders: list[dict], types: tuple[str, ...] | None = None
) -> tuple[dict[dt.date, int], int]:
    """Highest level per day over the case's zones; also the number of orders skipped for unusable dates."""
    levels: dict[dt.date, int] = {}
    skipped = 0
    for order in orders:
        names = parse_list(order["zones_alerte.nom"])
        kinds = parse_list(order["zones_alerte.type"])
        grades = parse_list(order["zones_alerte.niveau_gravite"])
        wanted = [
            LEVELS.get(g, 0)
            for n, k, g in zip(names, kinds, grades, strict=False)
            if any(word in fold(str(n)) for word in CASE.zone_keywords)
            and (types is None or k in types)
        ]
        if not wanted:
            continue
        try:
            start = dt.date.fromisoformat(order["date_debut"])
            end = dt.date.fromisoformat(order["date_fin"])
        except ValueError:
            skipped += 1
            continue
        if not (2000 <= start.year <= 2030) or end < start:
            skipped += 1
            continue
        level = max(wanted)
        day = start
        while day <= end:
            if levels.get(day, 0) < level:
                levels[day] = level
            day += dt.timedelta(days=1)
    return levels, skipped


def summer_outcomes(levels: dict[dt.date, int], years: range) -> dict[int, tuple[int, int]]:
    out = {}
    for year in years:
        days = [levels.get(dt.date(year, 6, 1) + dt.timedelta(days=i), 0) for i in range(122)]
        out[year] = (sum(1 for v in days if v >= ALERT), max(days))
    return out


def march_means(dates: list[str], values: list[float]) -> dict[int, float]:
    by_year: dict[int, list[float]] = {}
    for day, value in zip(dates, values, strict=True):
        if day[5:7] == "03":
            by_year.setdefault(int(day[:4]), []).append(value)
    return {y: float(np.mean(v)) for y, v in by_year.items() if len(v) >= MIN_MARCH_DAYS}


def zscores(series: dict[int, float]) -> dict[int, float]:
    base = [v for y, v in series.items() if y in CASE.climatology_years]
    mean, sd = float(np.mean(base)), float(np.std(base, ddof=1))
    return {y: (v - mean) / sd for y, v in series.items()}


def well_predictor() -> dict[int, float]:
    per_well = []
    for code in CASE.wells:
        rows = paged(f"{CHRONICLES}?code_bss={urllib.parse.quote(code)}&size=5000&sort=asc")
        kept = [
            (r["date_mesure"], r["niveau_nappe_eau"])
            for r in rows
            if r.get("niveau_nappe_eau") is not None and r.get("qualification") != "Incorrecte"
        ]
        per_well.append(zscores(march_means([d for d, _ in kept], [v for _, v in kept])))
    result = {}
    for year in CASE.years:
        values = [w[year] for w in per_well if year in w]
        if len(values) >= CASE.min_wells:
            result[year] = float(np.mean(values))
    return result


def discharge_predictor() -> dict[int, float]:
    rows = paged(f"{HYDRO}/obs_elab?code_entite={CASE.gauge}&grandeur_hydro_elab=QmnJ&size=5000")
    usable = [
        (r["date_obs_elab"][:10], r["resultat_obs_elab"])
        for r in rows
        if (r["resultat_obs_elab"] or 0) > 0
    ]
    means = march_means([d for d, _ in usable], [math.log10(v) for _, v in usable])
    z = zscores(means)
    return {y: z[y] for y in CASE.years if y in z}


def rank_statistic(x: list[float], y: list[float]) -> float:
    """s = -Spearman rho (expected positive)."""
    return -float(spearmanr(x, y).statistic)


def assess(x: list[float], y: list[float], rng: np.random.Generator) -> dict:
    n = len(x)
    s = rank_statistic(x, y)
    boot = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, size=n)
        xs, ys = [x[i] for i in idx], [y[i] for i in idx]
        if len(set(xs)) > 1 and len(set(ys)) > 1:
            boot.append(rank_statistic(xs, ys))
    low, high = np.quantile(boot, [0.05, 0.95])
    ranks_y = np.argsort(np.argsort(y))
    hits = 0
    for _ in range(N_PERMUTATIONS):
        shuffled = rng.permutation(ranks_y)
        if abs(float(spearmanr(x, shuffled).statistic)) >= abs(s) - 1e-12:
            hits += 1
    return {
        "n": n,
        "s": s,
        "ci90": (float(low), float(high)),
        "p_perm": (hits + 1) / (N_PERMUTATIONS + 1),
    }


def verdict(result: dict) -> str:
    if result["n"] < MIN_YEARS_TESTABLE:
        return "NOT_TESTABLE"
    low, high = result["ci90"]
    if low >= 0.8:
        return "BASELINE_SUFFICES"
    if high < 0.5:
        return "PREMISE_UNSUPPORTED"
    if 0.5 <= result["s"] < 0.8 and result["p_perm"] < 0.05:
        return "ROOM"
    return "INCONCLUSIVE"


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--orders-dir" not in argv:
        print(__doc__)
        return 2
    global CASE
    name = argv[argv.index("--case") + 1] if "--case" in argv else "yevre"
    if name not in CASES:
        print(f"unknown case {name!r}; known: {', '.join(CASES)}")
        return 2
    CASE = CASES[name]
    orders = load_orders(pathlib.Path(argv[argv.index("--orders-dir") + 1]))
    levels, skipped = daily_levels(orders)
    outcomes = summer_outcomes(levels, CASE.years)
    wells = well_predictor()
    flow = discharge_predictor()
    years = [y for y in CASE.years if y in wells and y in flow]
    print(f"case {name}")
    print(
        f"orders of department {CASE.department}: {len(orders)}; skipped for unusable dates: {skipped}"
    )
    print(f"years used: {years}\n")
    print(
        f"{'year':>4s} {'days>=alerte':>12s} {'max level':>9s} {'W (wells z)':>12s} {'Q (flow z)':>11s}"
    )
    for y in years:
        print(
            f"{y:>4d} {outcomes[y][0]:>12d} {outcomes[y][1]:>9d} {wells[y]:>12.2f} {flow[y]:>11.2f}"
        )
    days = [outcomes[y][0] for y in years]
    top = [outcomes[y][1] for y in years]
    rng = np.random.default_rng(SEED)
    print()
    results = {}
    for label, predictor in (("W wells", wells), ("Q gauge", flow)):
        for target, name in ((days, "days>=alerte"), (top, "max level")):
            r = assess([predictor[y] for y in years], target, rng)
            results[(label, name)] = r
            print(
                f"s({label}, {name}) = {r['s']:+.2f}  90% CI [{r['ci90'][0]:+.2f}, {r['ci90'][1]:+.2f}]  "
                f"p_perm = {r['p_perm']:.3f}  n = {r['n']}  -> {verdict(r)}"
            )
    primary = results[("W wells", "days>=alerte")]
    q = results[("Q gauge", "days>=alerte")]
    print(f"\nPRIMARY VERDICT (wells, days at or above alerte): {verdict(primary)}")
    print(
        f"gauge discharge predicts {'at least as well as' if q['s'] >= primary['s'] else 'less well than'} the wells"
    )
    if CASE.sou_years is not None:
        # Secondary 2, declared in the docstring: groundwater zones only, drawn after the four above so that
        # adding it leaves every other random draw unchanged.
        sou_levels, _ = daily_levels(orders, types=("SOU",))
        sou = summer_outcomes(sou_levels, CASE.sou_years)
        sou_years = [y for y in CASE.sou_years if y in wells and y in flow]
        print(f"\nsecondary 2 - groundwater (SOU) zones only, years {sou_years}")
        print(f"{'year':>4s} {'days>=alerte (SOU)':>19s}")
        for y in sou_years:
            print(f"{y:>4d} {sou[y][0]:>19d}")
        for label, predictor in (("W wells", wells), ("Q gauge", flow)):
            r = assess([predictor[y] for y in sou_years], [sou[y][0] for y in sou_years], rng)
            print(
                f"s({label}, SOU days>=alerte) = {r['s']:+.2f}  90% CI [{r['ci90'][0]:+.2f}, {r['ci90'][1]:+.2f}]  "
                f"p_perm = {r['p_perm']:.3f}  n = {r['n']}  -> {verdict(r)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
