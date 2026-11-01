"""BASIN-001 data readiness - basin screening and groundwater/discharge redundancy.

Two read-only reconnaissance commands on public, key-free APIs (Hub'Eau). They publish nothing and
interpret nothing physical: they count what exists and measure how redundant two published series are.

``screen``
    For every gauge in service of the given departments, applies the screening criteria below. The
    criteria are constants of this file so that the ranking cannot be tuned after the fact. Catchment
    boundaries are NOT available to this script: "near" means within ``RADIUS_KM`` of the outlet gauge,
    which is a proxy and not the catchment (see ``docs/BASIN-001-FEASIBILITY.md``).

``redundancy``
    For given gauges, downloads the full daily mean discharge (``QmnJ``) and the long piezometric
    series within ``RADIUS_KM``, and reports the Spearman correlation between the deseasonalized
    monthly anomalies of log10(Q) and of the groundwater level. A high value means that the discharge
    already carries most of the groundwater dynamics seen at that well. It is a diagnostic, never a
    criterion for choosing wells (that would be selection on the outcome).

Usage:

    uv run python experiments/basin_001_screening.py screen 14 76 60
    uv run python experiments/basin_001_screening.py redundancy H504062010 I403201001
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from scipy.stats import spearmanr

HYDRO = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"
PIEZO = "https://hubeau.eaufrance.fr/api/v1/niveaux_nappes"

# Screening criteria, declared before the ranking was produced.
MIN_YEARS = 25.0
MIN_COMPLETENESS = 0.90  # observed days / days since the first observation
MIN_DAYS_LAST_YEAR = 330  # days with a value in 2025
MIN_PIEZOMETERS = 5
MIN_SAME_AQUIFER = 3
RADIUS_KM = 15.0
PIEZO_MIN_VALUES = 3000
PIEZO_START_BEFORE = "2005-01-01"
PIEZO_END_AFTER = "2024-01-01"
TODAY = dt.date(2026, 11, 1)
GAUGE_TYPES = ("STD", "DEB")
MIN_MONTH_DAYS = 10  # days with a value for a month to be kept


def get(url: str, attempts: int = 4, timeout: float = 120.0) -> dict | None:
    """GET a JSON document, retrying transient failures. ``None`` when it never answered."""
    request = urllib.request.Request(url, headers={"accept": "application/json"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                return None
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                return None
        time.sleep(2 * (attempt + 1))
    return None


def paged(url: str) -> list[dict]:
    """Follow the ``next`` links of a Hub'Eau collection."""
    rows: list[dict] = []
    while url:
        page = get(url)
        if page is None:
            raise RuntimeError(f"no answer from {url}")
        rows.extend(page["data"])
        url = page.get("next")
    return rows


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def long_piezometers(department: str) -> list[dict]:
    page = get(f"{PIEZO}/stations?code_departement={department}&size=5000&format=json")
    if page is None:
        return []
    return [
        p
        for p in page["data"]
        if p.get("y") is not None
        and (p.get("nb_mesures_piezo") or 0) >= PIEZO_MIN_VALUES
        and (p.get("date_debut_mesure") or "9999") <= PIEZO_START_BEFORE
        and (p.get("date_fin_mesure") or "") >= PIEZO_END_AFTER
    ]


def near(piezometers: list[dict], lat: float, lon: float) -> list[dict]:
    return [p for p in piezometers if haversine_km(lat, lon, p["y"], p["x"]) <= RADIUS_KM]


def screen(departments: list[str]) -> list[dict]:
    rows: list[dict] = []
    for department in departments:
        referential = get(
            f"{HYDRO}/referentiel/stations?code_departement={department}&format=json&size=200"
        )
        if referential is None:
            print(f"department {department}: referential unavailable", flush=True)
            continue
        gauges = [
            g
            for g in referential["data"]
            if g.get("en_service") and g.get("type_station") in GAUGE_TYPES
        ]
        piezometers = long_piezometers(department)
        print(
            f"department {department}: {len(gauges)} gauges, {len(piezometers)} long piezometers",
            flush=True,
        )
        for gauge in gauges:
            code = gauge["code_station"]
            first_page = get(f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ&size=1")
            recent = get(
                f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ"
                "&date_debut_obs_elab=2025-01-01&date_fin_obs_elab=2025-12-31&size=1"
            )
            if not first_page or not first_page.get("data"):
                continue
            first = first_page["data"][0]["date_obs_elab"][:10]
            n_days = first_page["count"]
            expected = (TODAY - dt.date.fromisoformat(first)).days
            wells = near(piezometers, gauge["latitude_station"], gauge["longitude_station"])
            aquifers = collections.Counter(
                a for p in wells for a in (p.get("noms_masse_eau_edl") or [])
            )
            rows.append(
                {
                    "department": department,
                    "code": code,
                    "name": gauge["libelle_station"],
                    "first": first,
                    "years": round(n_days / 365.25, 1),
                    "completeness": round(n_days / max(expected, 1), 3),
                    "days_last_year": recent["count"] if recent else None,
                    "piezometers": len(wells),
                    "top_aquifer": aquifers.most_common(1)[0] if aquifers else None,
                    "local_influence_code": gauge.get("influence_locale_station"),
                }
            )
    return rows


def passes(row: dict) -> bool:
    return (
        row["years"] >= MIN_YEARS
        and row["completeness"] >= MIN_COMPLETENESS
        and (row["days_last_year"] or 0) >= MIN_DAYS_LAST_YEAR
        and row["piezometers"] >= MIN_PIEZOMETERS
        and row["top_aquifer"] is not None
        and row["top_aquifer"][1] >= MIN_SAME_AQUIFER
    )


def monthly_means(dates: list[str], values: list[float]) -> dict[str, float]:
    bucket: dict[str, list[float]] = collections.defaultdict(list)
    for day, value in zip(dates, values, strict=True):
        bucket[day[:7]].append(value)
    return {month: float(np.mean(v)) for month, v in bucket.items() if len(v) >= MIN_MONTH_DAYS}


def deseasonalize(series: dict[str, float]) -> dict[str, float]:
    by_calendar_month: dict[str, list[float]] = collections.defaultdict(list)
    for month, value in series.items():
        by_calendar_month[month[5:7]].append(value)
    means = {m: float(np.mean(v)) for m, v in by_calendar_month.items()}
    return {month: value - means[month[5:7]] for month, value in series.items()}


def redundancy(codes: list[str]) -> None:
    for code in codes:
        reference = get(f"{HYDRO}/referentiel/stations?code_station={code}&format=json")
        if not reference or not reference["data"]:
            print(f"{code}: unknown gauge")
            continue
        gauge = reference["data"][0]
        lat, lon = gauge["latitude_station"], gauge["longitude_station"]
        discharge = paged(f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ&size=5000")
        usable = [
            (r["date_obs_elab"][:10], r["resultat_obs_elab"])
            for r in discharge
            if (r["resultat_obs_elab"] or 0) > 0
        ]
        q_anomaly = deseasonalize(
            {
                m: math.log10(v)
                for m, v in monthly_means([d for d, _ in usable], [v for _, v in usable]).items()
            }
        )
        print(
            f"\n=== {gauge['libelle_station']} ({code}) {discharge[0]['date_obs_elab'][:10]}..{discharge[-1]['date_obs_elab'][:10]}"
        )
        print(
            "  qualification:",
            dict(collections.Counter(r["libelle_qualification"] for r in discharge)),
        )
        print(
            "  method:       ", dict(collections.Counter(r["libelle_methode"] for r in discharge))
        )
        print("  null values:  ", sum(r["resultat_obs_elab"] is None for r in discharge))
        wells = near(long_piezometers(gauge["code_departement"]), lat, lon)
        for well in sorted(wells, key=lambda p: haversine_km(lat, lon, p["y"], p["x"])):
            quoted = urllib.parse.quote(well["code_bss"])
            rows = paged(f"{PIEZO}/chroniques?code_bss={quoted}&size=5000&sort=asc")
            kept = [
                (r["date_mesure"], r["niveau_nappe_eau"])
                for r in rows
                if r.get("niveau_nappe_eau") is not None
            ]
            if len(kept) < 200:
                continue
            h_anomaly = deseasonalize(monthly_means([d for d, _ in kept], [v for _, v in kept]))
            common = sorted(set(h_anomaly) & set(q_anomaly))
            rho = (
                spearmanr([h_anomaly[m] for m in common], [q_anomaly[m] for m in common]).statistic
                if len(common) > 60
                else float("nan")
            )
            steps = (
                np.diff([np.datetime64(d) for d, _ in kept]).astype("timedelta64[D]").astype(int)
            )
            flags = dict(collections.Counter(r.get("qualification") for r in rows))
            print(
                f"  {well['code_bss']:16s} {haversine_km(lat, lon, well['y'], well['x']):4.1f} km "
                f"n={len(kept):6d} max gap {int(steps.max()):6d} d  common months {len(common):3d}  "
                f"spearman={rho:5.2f}  {(well.get('noms_masse_eau_edl') or ['?'])[0]}  flags {flags}"
            )


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 3 or argv[1] not in ("screen", "redundancy"):
        print(__doc__)
        return 2
    if argv[1] == "screen":
        rows = screen(argv[2:])
        passing = [r for r in rows if passes(r)]
        print(f"\n{len(rows)} gauges screened, {len(passing)} pass")
        for row in sorted(passing, key=lambda r: (-r["piezometers"], -r["years"])):
            print(
                f"  {row['department']} {row['code']} {row['name'][:40]:40s} {row['first']} {row['years']:5.1f} y "
                f"completeness {row['completeness']:.2f} wells {row['piezometers']} {row['top_aquifer']}"
            )
    else:
        redundancy(argv[2:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
