"""BASIN-002 - aquifer-first candidate discovery.

BASIN-001 started from gauging stations and found that no catchment held enough long, recent wells of one
aquifer. This script starts from the groundwater monitoring network instead:

1. ``inventory``  - every French piezometer (Hub'Eau ``niveaux_nappes``), the wells that meet the ORIGINAL
   BASIN-001 well criteria, grouped by groundwater body (``codes_masse_eau_edl``), with the spatial
   distribution of each group. No gauge, catchment or correlation is looked at.
2. ``zones``      - inside each qualifying group, the zones where at least ``MIN_WELLS`` wells of the same body lie
   within ``ZONE_RADIUS_KM`` of one another. This is a computational pruning derived from the catchment size
   scope (a catchment of a few hundred km2), NOT a selection criterion and NOT a search radius around a gauge.
3. ``candidates`` - only then, the gauges (original BASIN-001 hydrometric criteria) located in or near those
   zones are delineated on the Sandre BD Topage network and the wells of the group that lie **certainly
   upstream** are counted. A candidate needs ``MIN_WELLS`` of them in ONE groundwater body.

Qualification rules are the BASIN-001 ones and are not weakened: >= 3 000 values, record starting on or before
2005-01-01, ending on or after 2024-01-01. The well count is raised from 3 to 4 as requested. Measures added
here (completeness, quality flags, pairwise distances) are REPORTED and FLAGGED, they never admit a candidate
that the original rules reject.

Discovery only: no correlation between wells and discharge is computed in this script, so nothing observed here
can be mistaken for confirmation.

Usage:

    uv run python experiments/basin_002_aquifer_first.py inventory --cache DIR
    uv run python experiments/basin_002_aquifer_first.py zones --cache DIR
    uv run python experiments/basin_002_aquifer_first.py check-network --cache DIR\n    uv run python experiments/basin_002_aquifer_first.py candidates --cache DIR [--dry] [--limit N] [--workers 8]
    uv run python experiments/basin_002_aquifer_first.py shortlist --cache DIR
"""

from __future__ import annotations

import collections
import concurrent.futures
import datetime as dt
import gzip
import itertools
import json
import math
import pathlib
import statistics
import sys
import urllib.parse

from basin_001_catchment import (
    OUTLET_MAX_TAIL_KM,
    SCREEN_MAX_REACHES,
    contains,
    fetch_json,
    flow_ends,
    haversine_km,
    midpoint,
    point_segment_km,
    polygon_area_km2,
    polygon_parts,
    reach_length_km,
    same_point,
    tail_km,
)
from basin_001_screening import MIN_COMPLETENESS, MIN_DAYS_LAST_YEAR, MIN_YEARS, paged

PIEZO = "https://hubeau.eaufrance.fr/api/v1/niveaux_nappes/stations"
HYDRO = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"
GAUGE_TYPES = ("STD", "DEB")
TODAY = dt.date(2026, 11, 1)

# BASIN-001 well criteria, unchanged.
WELL_MIN_VALUES = 3000
WELL_START_BEFORE = "2005-01-01"
WELL_END_AFTER = "2024-01-01"
# Raised from 3 to 4 by the BASIN-002 brief.
MIN_WELLS = 4
# Computational pruning from the catchment size scope (about 700 km2 if circular): wells of one catchment
# cannot lie farther apart than this, so a group with no such zone cannot yield a candidate.
ZONE_RADIUS_KM = 30.0
# Reporting flags (never admit or reject on their own).
CLUSTERED_MEDIAN_KM = 3.0

DEPARTMENTS = [f"{i:02d}" for i in range(1, 96) if i != 20] + ["2A", "2B"]


def cache_file(cache: pathlib.Path | None, name: str) -> pathlib.Path | None:
    return None if cache is None else cache / name


def load_inventory(cache: pathlib.Path | None) -> list[dict]:
    """All piezometer stations of metropolitan France, one request per department."""
    stations: list[dict] = []
    for department in DEPARTMENTS:
        path = cache_file(cache, f"piezo_{department}.json")
        if path is not None and path.is_file():
            stations.extend(json.loads(path.read_text(encoding="utf-8")))
            continue
        page = fetch_json(f"{PIEZO}?code_departement={department}&size=5000&format=json")
        if page is None:
            raise RuntimeError(f"piezometer inventory unavailable for department {department}")
        if page["count"] > len(page["data"]):
            raise RuntimeError(
                f"department {department} has {page['count']} stations, more than one page"
            )
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(page["data"], ensure_ascii=False), encoding="utf-8")
        stations.extend(page["data"])
        print(f"  department {department}: {len(page['data'])} stations", flush=True)
    return stations


def qualifies(well: dict) -> bool:
    """The original BASIN-001 well criteria, on station metadata."""
    return (
        well.get("x") is not None
        and well.get("y") is not None
        and (well.get("nb_mesures_piezo") or 0) >= WELL_MIN_VALUES
        and (well.get("date_debut_mesure") or "9999") <= WELL_START_BEFORE
        and (well.get("date_fin_mesure") or "") >= WELL_END_AFTER
    )


def body_of(well: dict) -> tuple[str, str] | None:
    """The groundwater body of a well, only when it is unambiguous (exactly one body)."""
    codes = well.get("codes_masse_eau_edl") or []
    names = well.get("noms_masse_eau_edl") or []
    if len(codes) != 1:
        return None
    return codes[0], (names[0] if names else "?")


def pairwise_km(wells: list[dict]) -> list[float]:
    return [
        haversine_km(a["y"], a["x"], b["y"], b["x"]) for a, b in itertools.combinations(wells, 2)
    ]


def distribution(wells: list[dict]) -> dict:
    distances = pairwise_km(wells)
    if not distances:
        return {"n": len(wells), "min_km": 0.0, "median_km": 0.0, "max_km": 0.0, "clustered": True}
    median = statistics.median(distances)
    return {
        "n": len(wells),
        "min_km": min(distances),
        "median_km": median,
        "max_km": max(distances),
        "clustered": median < CLUSTERED_MEDIAN_KM,
    }


def bdlisa_agreement(wells: list[dict]) -> float:
    """Share of wells carrying the most common BDLISA entity of the group (attribution confidence)."""
    counts = collections.Counter(c for w in wells for c in set(w.get("codes_bdlisa") or []))
    if not counts or not wells:
        return 0.0
    return counts.most_common(1)[0][1] / len(wells)


def group_by_body(stations: list[dict]) -> dict[str, dict]:
    groups: dict[str, dict] = {}
    for well in stations:
        if not qualifies(well):
            continue
        body = body_of(well)
        if body is None:
            continue
        group = groups.setdefault(body[0], {"code": body[0], "name": body[1], "wells": []})
        group["wells"].append(well)
    return groups


def zones_of(wells: list[dict]) -> list[list[dict]]:
    """Connected zones of wells of one body in which every seed has >= MIN_WELLS wells within the radius."""
    neighbours = {
        i: [
            j
            for j, b in enumerate(wells)
            if haversine_km(a["y"], a["x"], b["y"], b["x"]) <= ZONE_RADIUS_KM
        ]
        for i, a in enumerate(wells)
    }
    seeds = [i for i, n in neighbours.items() if len(n) >= MIN_WELLS]
    parent = {i: i for i in seeds}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in seeds:
        for j in neighbours[i]:
            if j in parent:
                parent[find(i)] = find(j)
    zones: dict[int, set[int]] = collections.defaultdict(set)
    for i in seeds:
        zones[find(i)].update(neighbours[i])
    return [[wells[k] for k in sorted(members)] for members in zones.values()]


def run_inventory(cache: pathlib.Path | None) -> dict[str, dict]:
    stations = load_inventory(cache)
    qualifying = [w for w in stations if qualifies(w)]
    unattributed = [w for w in qualifying if not (w.get("codes_masse_eau_edl") or [])]
    ambiguous = [w for w in qualifying if len(w.get("codes_masse_eau_edl") or []) > 1]
    groups = group_by_body(stations)
    big = {c: g for c, g in groups.items() if len(g["wells"]) >= MIN_WELLS}
    print(f"\npiezometers in metropolitan France: {len(stations)}")
    print(f"meet the original well criteria (values, start, end): {len(qualifying)}")
    print(
        f"  without any groundwater body: {len(unattributed)}; with several bodies (ambiguous, not used): {len(ambiguous)}"
    )
    print(f"groundwater bodies holding qualifying wells (one body per well): {len(groups)}")
    print(f"bodies with >= {MIN_WELLS} qualifying wells: {len(big)}")
    zones_total = 0
    for group in big.values():
        group["distribution"] = distribution(group["wells"])
        group["bdlisa_agreement"] = bdlisa_agreement(group["wells"])
        group["departments"] = sorted({w["code_departement"] for w in group["wells"]})
        group["zones"] = zones_of(group["wells"])
        zones_total += len(group["zones"])
    print(
        f"zones with >= {MIN_WELLS} wells of one body within {ZONE_RADIUS_KM:.0f} km: {zones_total}"
    )
    return big


def print_groups(big: dict[str, dict], limit: int = 60) -> None:
    print(
        f"\n{'body':10s} {'wells':>5s} {'zones':>5s} {'median km':>9s} {'max km':>7s} {'bdlisa':>6s} departments / name"
    )
    for code, group in sorted(big.items(), key=lambda kv: -len(kv[1]["wells"]))[:limit]:
        d = group["distribution"]
        print(
            f"{code:10s} {d['n']:5d} {len(group['zones']):5d} {d['median_km']:9.1f} {d['max_km']:7.1f} "
            f"{group['bdlisa_agreement']:6.2f} {','.join(group['departments'])[:22]:22s} {group['name'][:60]}"
        )


def print_zones(big: dict[str, dict]) -> None:
    print(f"\n{'body':10s} {'zone':>4s} {'wells':>5s} {'median km':>9s} {'max km':>7s} name")
    for code, group in sorted(big.items(), key=lambda kv: -len(kv[1]["wells"])):
        for index, zone in enumerate(group["zones"], start=1):
            d = distribution(zone)
            flag = "  CLUSTERED" if d["clustered"] else ""
            print(
                f"{code:10s} {index:4d} {d['n']:5d} {d['median_km']:9.1f} {d['max_km']:7.1f} "
                f"{group['name'][:60]}{flag}"
            )


# --------------------------------------------------------------------------
# Sandre BD Topage network, loaded by tiles and traversed in memory
# --------------------------------------------------------------------------

TILE_DEG = 0.25
EDGE_MARGIN_DEG = 3e-4
SANDRE = "https://services.sandre.eaufrance.fr/geo/topage2022"
REACH_LAYER = "TronconHydrographique_FXX_Topage2022"
BASIN_LAYER = "BassinVersantTopographique_FXX_Topage2022"
CRS = "urn:ogc:def:crs:OGC:1.3:CRS84"
NODE_CELL = 1e5  # node index resolution (about 1 m); neighbours are probed, tolerance is 2e-6 deg
SNAP_WINDOW_DEG = 0.004
SNAP_CELL_DEG = 0.01


def node_key(point: tuple[float, float]) -> tuple[int, int]:
    return round(point[0] * NODE_CELL), round(point[1] * NODE_CELL)


class Network:
    """Reaches and elementary basins loaded tile by tile (bulk WFS, cached), with in-memory traversal.

    The BASIN-001 delineation (``basin_001_catchment.py``) asks the WFS once per reach, which is exact but
    too slow for hundreds of gauges. This class loads each 0.25 degree tile once and applies the SAME
    rules: reaches join at coinciding ends, flow follows the digitisation unless stated otherwise, a
    diffluence follows the "principal" arm, and the gauge's own elementary basin is taken whole.
    """

    def __init__(self, cache: pathlib.Path | None) -> None:
        self.cache = cache
        self.loaded: set[tuple[int, int]] = set()
        self.reaches: dict[str, dict] = {}
        self.meta: dict[str, dict] = {}
        self.by_up: dict[tuple[int, int], list[str]] = collections.defaultdict(list)
        self.by_down: dict[tuple[int, int], list[str]] = collections.defaultdict(list)
        self.grid: dict[tuple[int, int], set[str]] = collections.defaultdict(set)
        self.basins: dict[int, dict] = {}
        self.basin_box: dict[int, tuple[float, float, float, float]] = {}
        self.tile_requests = 0

    # -- loading ----------------------------------------------------------

    def _fetch_layer(self, layer: str, i: int, j: int) -> list[dict]:
        short = "reach" if layer == REACH_LAYER else "basin"
        path = cache_file(self.cache, f"tiles/{short}_{i}_{j}.json.gz")
        if path is not None and path.is_file():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                return json.load(handle)
        west, south = i * TILE_DEG, j * TILE_DEG
        features: list[dict] = []
        while True:
            params = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": f"sa:{layer}",
                "outputFormat": "geojson",
                "count": "2000",
                "startIndex": str(len(features)),
                "sortBy": "gid",
                "bbox": f"{west},{south},{west + TILE_DEG},{south + TILE_DEG},{CRS}",
            }
            page = fetch_json(f"{SANDRE}?{urllib.parse.urlencode(params)}", timeout=180.0)
            if page is None:
                raise RuntimeError(f"WFS {layer} tile ({i},{j}) unavailable")
            if not page["features"]:
                break
            features.extend(page["features"])
        self.tile_requests += 1
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(features, handle)
        return features

    def load_tile(self, i: int, j: int) -> None:
        if (i, j) in self.loaded:
            return
        for feature in self._fetch_layer(REACH_LAYER, i, j):
            code = feature["properties"]["CdOH"]
            if code in self.reaches:
                continue
            up, down, known = flow_ends(feature)
            coords = [(c[0], c[1]) for c in feature["geometry"]["coordinates"]]
            lat = coords[len(coords) // 2][1]
            self.reaches[code] = feature
            self.meta[code] = {
                "up": up,
                "down": down,
                "known": known,
                "mid": midpoint(feature),
                "length_km": reach_length_km(feature, lat),
            }
            self.by_up[node_key(up)].append(code)
            self.by_down[node_key(down)].append(code)
            xs, ys = [c[0] for c in coords], [c[1] for c in coords]
            for gx in range(
                math.floor(min(xs) / SNAP_CELL_DEG), math.floor(max(xs) / SNAP_CELL_DEG) + 1
            ):
                for gy in range(
                    math.floor(min(ys) / SNAP_CELL_DEG), math.floor(max(ys) / SNAP_CELL_DEG) + 1
                ):
                    self.grid[(gx, gy)].add(code)
        for feature in self._fetch_layer(BASIN_LAYER, i, j):
            gid = feature["properties"]["gid"]
            if gid in self.basins:
                continue
            xs = [c[0] for rings in polygon_parts(feature["geometry"]) for c in rings[0]]
            ys = [c[1] for rings in polygon_parts(feature["geometry"]) for c in rings[0]]
            self.basins[gid] = feature
            self.basin_box[gid] = (min(xs), min(ys), max(xs), max(ys))
        self.loaded.add((i, j))

    def ensure(self, x: float, y: float) -> None:
        """Make sure the tile of a point, and the neighbour tiles it is close to, are loaded."""
        i, j = math.floor(x / TILE_DEG), math.floor(y / TILE_DEG)
        self.load_tile(i, j)
        di = (
            -1
            if x - i * TILE_DEG < EDGE_MARGIN_DEG
            else (1 if (i + 1) * TILE_DEG - x < EDGE_MARGIN_DEG else 0)
        )
        dj = (
            -1
            if y - j * TILE_DEG < EDGE_MARGIN_DEG
            else (1 if (j + 1) * TILE_DEG - y < EDGE_MARGIN_DEG else 0)
        )
        for a, b in {(di, 0), (0, dj), (di, dj)} - {(0, 0)}:
            self.load_tile(i + a, j + b)

    # -- lookups ----------------------------------------------------------

    def _at(self, index: dict, point: tuple[float, float]) -> list[str]:
        kx, ky = node_key(point)
        out: list[str] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(index.get((kx + dx, ky + dy), ()))
        return out

    def reaches_ending_at(self, point: tuple[float, float]) -> list[str]:
        return [c for c in self._at(self.by_down, point) if same_point(self.meta[c]["down"], point)]

    def reaches_starting_at(self, point: tuple[float, float]) -> list[str]:
        return [c for c in self._at(self.by_up, point) if same_point(self.meta[c]["up"], point)]

    def basin_at(self, x: float, y: float) -> dict | None:
        self.ensure(x, y)
        for gid, (west, south, east, north) in self.basin_box.items():
            if (
                west <= x <= east
                and south <= y <= north
                and contains(self.basins[gid]["geometry"], x, y)
            ):
                return self.basins[gid]
        return None

    def snap(self, lon: float, lat: float) -> tuple[dict, float]:
        self.ensure(lon, lat)
        gx, gy = math.floor(lon / SNAP_CELL_DEG), math.floor(lat / SNAP_CELL_DEG)
        span = math.ceil(SNAP_WINDOW_DEG / SNAP_CELL_DEG)
        candidates: set[str] = set()
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                candidates |= self.grid.get((gx + dx, gy + dy), set())
        best, best_km = None, float("inf")
        for code in candidates:
            coordinates = self.reaches[code]["geometry"]["coordinates"]
            for (ax, ay), (bx, by) in itertools.pairwise([(c[0], c[1]) for c in coordinates]):
                km = point_segment_km(lon, lat, ax, ay, bx, by, lat)
                if km < best_km:
                    best, best_km = code, km
        if best is None or best_km > SNAP_WINDOW_DEG * 111.0:
            raise RuntimeError("no reach near the gauge")
        return self.reaches[best], best_km

    # -- rules shared with basin_001_catchment ----------------------------

    def outlet(self, start: dict, lon: float, lat: float) -> dict:
        """Distance along the stream from the gauge to the exit of its elementary basin (see BASIN-001)."""
        code = start["properties"]["CdOH"]
        own = self.basin_at(*self.meta[code]["mid"])
        own_gid = own["properties"]["gid"] if own else None
        distance = tail_km(start, lon, lat)
        exited, stop, current = False, "distance_limit", code
        for _ in range(50):
            if own_gid is None:
                stop = "no_basin"
                break
            if distance > OUTLET_MAX_TAIL_KM:
                break
            self.ensure(*self.meta[current]["down"])
            following = [
                c for c in self.reaches_starting_at(self.meta[current]["down"]) if c != current
            ]
            if not following:
                exited, stop = True, "terminal_reach"
                break
            if len(following) > 1:
                principal = [
                    c
                    for c in following
                    if self.reaches[c]["properties"].get("BrasTH") == "principal"
                ]
                if len(principal) != 1:
                    stop = "bifurcation"
                    break
                following = principal
            other = self.basin_at(*self.meta[following[0]]["mid"])
            if other is None or other["properties"]["gid"] != own_gid:
                exited, stop = True, "exit_basin"
                break
            distance += self.meta[following[0]]["length_km"]
            current = following[0]
        return {
            "direction_stated": self.meta[code]["known"],
            "distance_to_exit_km": distance,
            "own_basin": own["properties"]["TopoOH"] if own else None,
            "leaves_basin": exited,
            "stop": stop,
            "at_outlet": bool(
                self.meta[code]["known"] and exited and distance <= OUTLET_MAX_TAIL_KM
            ),
        }

    def upstream(self, start: dict, max_reaches: int) -> set[str]:
        root = start["properties"]["CdOH"]
        found = {root}
        queue = [root]
        while queue:
            current = queue.pop()
            point = self.meta[current]["up"]
            self.ensure(*point)
            for code in self.reaches_ending_at(point):
                if code not in found:
                    found.add(code)
                    queue.append(code)
                    if len(found) > max_reaches:
                        raise RuntimeError(f"upstream traversal exceeded {max_reaches} reaches")
        return found

    def delineate(self, lon: float, lat: float, max_reaches: int) -> dict:
        start, snap_km = self.snap(lon, lat)
        outlet = self.outlet(start, lon, lat)
        reaches = self.upstream(start, max_reaches)
        gauge_basin = self.basin_at(*self.meta[start["properties"]["CdOH"]]["mid"])
        members: dict[int, dict] = {}
        unassigned = 0
        for code in reaches:
            owner = self.basin_at(*self.meta[code]["mid"])
            if owner is None:
                unassigned += 1
                continue
            members.setdefault(owner["properties"]["gid"], owner)
        area = sum(polygon_area_km2(b["geometry"], lat) for b in members.values())
        return {
            "snap_km": snap_km,
            "reaches": len(reaches),
            "reaches_unassigned": unassigned,
            "basins": list(members.values()),
            "gauge_basin_gid": gauge_basin["properties"]["gid"] if gauge_basin else None,
            "outlet": outlet,
            "area_km2_upper_bound": area,
        }


# --------------------------------------------------------------------------
# gauges
# --------------------------------------------------------------------------


def load_gauges(cache: pathlib.Path | None) -> list[dict]:
    """Gauges in service of metropolitan France (types STD and DEB), one request per department."""
    gauges: list[dict] = []
    for department in DEPARTMENTS:
        path = cache_file(cache, f"gauges_{department}.json")
        if path is not None and path.is_file():
            gauges.extend(json.loads(path.read_text(encoding="utf-8")))
            continue
        page = fetch_json(
            f"{HYDRO}/referentiel/stations?code_departement={department}&format=json&size=1000"
        )
        if page is None:
            raise RuntimeError(f"gauge inventory unavailable for department {department}")
        kept = [
            {
                "code": g["code_station"],
                "name": g["libelle_station"],
                "department": department,
                "lat": g["latitude_station"],
                "lon": g["longitude_station"],
                "river": g.get("libelle_cours_eau"),
                "influence": g.get("influence_locale_station"),
            }
            for g in page["data"]
            if g.get("en_service")
            and g.get("type_station") in GAUGE_TYPES
            and g.get("latitude_station") is not None
        ]
        if path is not None:
            path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
        gauges.extend(kept)
    return gauges


def gauges_near_bodies(gauges: list[dict], big: dict[str, dict]) -> list[dict]:
    """Gauges with >= MIN_WELLS qualifying wells of ONE body within ZONE_RADIUS_KM (necessary under the size scope)."""
    kept = []
    for gauge in gauges:
        near = {}
        for code, group in big.items():
            count = sum(
                1
                for w in group["wells"]
                if haversine_km(gauge["lat"], gauge["lon"], w["y"], w["x"]) <= ZONE_RADIUS_KM
            )
            if count >= MIN_WELLS:
                near[code] = count
        if near:
            kept.append({**gauge, "near": near})
    return kept


def hydrometric(gauge: dict) -> dict | None:
    """The original BASIN-001 hydrometric measures for one gauge."""
    code = gauge["code"]
    first = fetch_json(f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ&size=1")
    recent = fetch_json(
        f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ"
        "&date_debut_obs_elab=2025-01-01&date_fin_obs_elab=2025-12-31&size=1"
    )
    if not first or not first.get("data") or recent is None:
        return None
    start = first["data"][0]["date_obs_elab"][:10]
    expected = (TODAY - dt.date.fromisoformat(start)).days
    return {
        "first": start,
        "years": round(first["count"] / 365.25, 1),
        "completeness": round(first["count"] / max(expected, 1), 3),
        "days_last_year": recent["count"],
    }


def hydro_ok(metrics: dict | None) -> bool:
    return (
        metrics is not None
        and metrics["years"] >= MIN_YEARS
        and metrics["completeness"] >= MIN_COMPLETENESS
        and metrics["days_last_year"] >= MIN_DAYS_LAST_YEAR
    )


def evaluate_gauge(
    gauge: dict, big: dict[str, dict], cache: pathlib.Path | None, network: Network
) -> dict:
    """Delineate one gauge and count, per body, the wells certainly upstream and the ones only possibly so."""
    path = cache_file(cache, f"catchment_{gauge['code']}.json")
    if path is not None and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    out: dict = {"code": gauge["code"], "name": gauge["name"], "department": gauge["department"]}
    try:
        result = network.delineate(gauge["lon"], gauge["lat"], SCREEN_MAX_REACHES)
    except (RuntimeError, KeyError, ValueError) as error:
        out["error"] = str(error)[:200]
    else:
        basins = result["basins"]
        own = result["gauge_basin_gid"]
        exact = result["outlet"]["at_outlet"]
        per_body: dict[str, dict[str, list[str]]] = {}
        for code in gauge["near"]:
            for well in big[code]["wells"]:
                owners = [b for b in basins if contains(b["geometry"], well["x"], well["y"])]
                if not owners:
                    continue
                certain = exact or any(b["properties"]["gid"] != own for b in owners)
                bucket = per_body.setdefault(code, {"certain": [], "possible": []})
                bucket["certain" if certain else "possible"].append(well["code_bss"])
        out.update(
            {
                "area_km2": round(result["area_km2_upper_bound"], 1),
                "reaches": result["reaches"],
                "basins": len(basins),
                "outlet": {
                    k: result["outlet"][k] for k in ("at_outlet", "distance_to_exit_km", "stop")
                },
                "bodies": per_body,
            }
        )
    if path is not None:
        path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def prefetch_tiles(
    network: Network, gauges: list[dict], workers: int, pad_lon: float = 0.3, pad_lat: float = 0.3
) -> None:
    """Download, in parallel, the tiles around every gauge (disk cache only; loading stays sequential).

    A catchment that reaches beyond this margin falls back to the lazy, sequential loading.
    """
    wanted: set[tuple[int, int]] = set()
    for gauge in gauges:
        for i in range(
            math.floor((gauge["lon"] - pad_lon) / TILE_DEG),
            math.floor((gauge["lon"] + pad_lon) / TILE_DEG) + 1,
        ):
            for j in range(
                math.floor((gauge["lat"] - pad_lat) / TILE_DEG),
                math.floor((gauge["lat"] + pad_lat) / TILE_DEG) + 1,
            ):
                wanted.add((i, j))
    print(f"prefetching {len(wanted)} tiles with {workers} workers", flush=True)

    def fetch(tile: tuple[int, int]) -> None:
        network._fetch_layer(REACH_LAYER, *tile)
        network._fetch_layer(BASIN_LAYER, *tile)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for count, _ in enumerate(pool.map(fetch, sorted(wanted)), start=1):
            if count % 50 == 0:
                print(f"  tiles ready: {count}/{len(wanted)}", flush=True)


def run_candidates(cache: pathlib.Path | None, dry: bool, workers: int, limit: int | None) -> None:
    big = run_inventory(cache)
    gauges = load_gauges(cache)
    near = gauges_near_bodies(gauges, big)
    print(
        f"\ngauges in service: {len(gauges)}; with >= {MIN_WELLS} wells of one body within {ZONE_RADIUS_KM:.0f} km: {len(near)}"
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        metrics = list(pool.map(hydrometric, near))
    passing = [{**g, "hydro": m} for g, m in zip(near, metrics, strict=True) if hydro_ok(m)]
    print(f"pass the original hydrometric criteria: {len(passing)} of {len(near)}")
    if dry:
        return
    if limit is not None:
        passing = passing[:limit]
    done: list[dict] = []
    network = Network(cache)
    prefetch_tiles(network, passing, workers)
    # Neighbouring gauges share tiles: process them in geographic order.
    passing.sort(key=lambda g: (math.floor(g["lon"] / TILE_DEG), math.floor(g["lat"] / TILE_DEG)))
    for gauge in passing:
        result = evaluate_gauge(gauge, big, cache, network)
        result["hydro"] = gauge["hydro"]
        done.append(result)
        note = (
            result.get("error")
            or f"{result['area_km2']:.0f} km2, exact={result['outlet']['at_outlet']}"
        )
        print(
            f"  [{len(done)}/{len(passing)}] {gauge['code']} {gauge['name'][:36]:36s} {note}  "
            f"(tiles fetched {network.tile_requests})",
            flush=True,
        )
    summarise(done)


# Delineations produced by the one-request-per-reach method of basin_001_catchment.py (documented in
# docs/BASIN-001-FEASIBILITY.md), used to check that the tile-based network gives the same catchments.
KNOWN_CATCHMENTS = {
    "I403201001": (835, 9, 264),
    "I402201001": (514, 5, 133),
    "H504062010": (29, 1, 244),
    "I532151001": (453, 3, 132),
    "H760201001": (531, 3, 480),
}


def run_check_network(cache: pathlib.Path | None) -> None:
    network = Network(cache)
    for code, (reaches, basins, area) in KNOWN_CATCHMENTS.items():
        reference = fetch_json(f"{HYDRO}/referentiel/stations?code_station={code}&format=json")
        gauge = reference["data"][0]
        result = network.delineate(gauge["longitude_station"], gauge["latitude_station"], 5000)
        got = (result["reaches"], len(result["basins"]), round(result["area_km2_upper_bound"]))
        status = "SAME" if got == (reaches, basins, area) else "DIFFERENT"
        print(f"  {code} expected {(reaches, basins, area)} got {got} {status}", flush=True)


# --------------------------------------------------------------------------
# shortlist: qualify the candidates found by `candidates`
# --------------------------------------------------------------------------

REPORT_MIN_WELL_COMPLETENESS = 0.80  # reporting flag only
REPORT_MIN_CORRECT_SHARE = 0.90  # reporting flag only
LARGE_AREA_KM2 = 500.0  # reporting flag only: BASIN-001 catchments were 112 to 480 km2
CHRONICLES = "https://hubeau.eaufrance.fr/api/v1/niveaux_nappes/chroniques"


def well_series(code_bss: str) -> dict:
    """Daily levels of one well: usable days (value present, not flagged 'Incorrecte') and flag counts."""
    rows = paged(f"{CHRONICLES}?code_bss={urllib.parse.quote(code_bss)}&size=5000&sort=asc")
    flags = collections.Counter(r.get("qualification") for r in rows)
    days = sorted(
        {
            dt.date.fromisoformat(r["date_mesure"]).toordinal()
            for r in rows
            if r.get("niveau_nappe_eau") is not None and r.get("qualification") != "Incorrecte"
        }
    )
    return {"days": days, "flags": dict(flags), "rows": len(rows)}


def discharge_quality(code: str) -> dict:
    rows = paged(f"{HYDRO}/obs_elab?code_entite={code}&grandeur_hydro_elab=QmnJ&size=5000")
    n = len(rows)
    return {
        "values": n,
        "null": sum(r["resultat_obs_elab"] is None for r in rows),
        "doubtful_share": round(sum(r["libelle_qualification"] == "Douteuse" for r in rows) / n, 3),
        "calculated_share": round(sum(r["libelle_methode"] == "Calculée" for r in rows) / n, 3),
        "validated_share": round(sum(r["libelle_statut"] == "Donnée validée" for r in rows) / n, 3),
    }


def qualify_candidate(entry: dict, gauge: dict, big: dict[str, dict]) -> dict:
    code, body = entry["code"], entry["body"]
    by_code = {w["code_bss"]: w for w in big[body]["wells"]}
    wells = [by_code[c] for c in entry["certain"]]
    series = {w["code_bss"]: well_series(w["code_bss"]) for w in wells}
    start = max(s["days"][0] for s in series.values())
    end = min(s["days"][-1] for s in series.values())
    window = max(end - start + 1, 0)
    per_well = {}
    present = []
    for c, s in series.items():
        inside = [d for d in s["days"] if start <= d <= end]
        per_well[c] = {
            "completeness": round(len(inside) / window, 3) if window else 0.0,
            "correct_share": round(s["flags"].get("Correcte", 0) / max(s["rows"], 1), 3),
        }
        present.append(set(inside))
    simultaneous = collections.Counter(d for p in present for d in p)
    joint = sum(1 for n in simultaneous.values() if n >= MIN_WELLS)
    q = discharge_quality(code)
    distance = distribution(wells)
    bdlisa = bdlisa_agreement(wells)
    notes = []
    if entry["area_km2"] > LARGE_AREA_KM2:
        notes.append(
            f"area {entry['area_km2']:.0f} km2 (an upper bound) exceeds the 112-480 km2 of BASIN-001"
        )
    if not entry["outlet"]["at_outlet"]:
        notes.append(
            f"gauge is {entry['outlet']['distance_to_exit_km']:.1f}+ km from the exit of its own basin: "
            "area is an upper bound, wells of that basin are not counted"
        )
    if distance["clustered"]:
        notes.append(f"wells are clustered (median pairwise {distance['median_km']:.1f} km)")
    if any(v["completeness"] < REPORT_MIN_WELL_COMPLETENESS for v in per_well.values()):
        notes.append("at least one well is under 80 % complete in the common window")
    if any(v["correct_share"] < REPORT_MIN_CORRECT_SHARE for v in per_well.values()):
        notes.append("at least one well has under 90 % 'Correcte' values")
    if bdlisa < 0.75:
        notes.append(
            f"weak aquifer attribution: only {bdlisa:.0%} of the wells share one BDLISA entity"
        )
    if gauge.get("influence") not in (0, 1, None):
        notes.append(f"gauge local-influence code {gauge['influence']} (meaning not verified)")
    if q["doubtful_share"] > 0.03 or q["null"] > 0:
        notes.append(f"discharge quality: {q['doubtful_share']:.1%} doubtful, {q['null']} null")
    return {
        "gauge": code,
        "name": gauge["name"],
        "river": gauge.get("river"),
        "lat": gauge["lat"],
        "lon": gauge["lon"],
        "area_km2_upper_bound": entry["area_km2"],
        "reaches": entry["reaches"],
        "outlet": entry["outlet"],
        "body": body,
        "body_name": big[body]["name"],
        "wells": len(wells),
        "wells_possible_not_counted": entry["possible"],
        "well_distribution": distance,
        "bdlisa_agreement": round(bdlisa, 2),
        "common_window": [
            dt.date.fromordinal(start).isoformat(),
            dt.date.fromordinal(end).isoformat(),
        ]
        if window
        else None,
        "common_window_years": round(window / 365.25, 1),
        "days_with_all_counted_wells_ge_min": round(joint / window, 3) if window else 0.0,
        "per_well": per_well,
        "discharge": {**entry["hydro"], **q},
        "notes": notes,
    }


def run_shortlist(cache: pathlib.Path | None) -> None:
    big = run_inventory(cache)
    gauges = {g["code"]: g for g in load_gauges(cache)}
    results = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((cache / "").glob("catchment_*.json"))
    ]
    errors = collections.Counter(
        "size cap (> 1500 reaches)" if "exceeded" in r["error"] else "other failure"
        for r in results
        if "error" in r
    )
    ok = [r for r in results if "error" not in r]
    areas = sorted(r["area_km2"] for r in ok)
    print(
        f"\ngauges evaluated: {len(results)}; delineated: {len(ok)}; not delineated: {dict(errors)}"
    )
    if areas:
        print(
            f"delineated areas (upper bounds): min {areas[0]:.0f}, median {statistics.median(areas):.0f}, "
            f"max {areas[-1]:.0f} km2; exact outlets: {sum(1 for r in ok if r['outlet']['at_outlet'])}"
        )
    shortlist = []
    for r in ok:
        for body, wells in r["bodies"].items():
            if len(wells["certain"]) >= MIN_WELLS:
                hydro = hydrometric({**gauges[r["code"]], "code": r["code"]})
                shortlist.append(
                    {
                        **r,
                        "body": body,
                        "certain": wells["certain"],
                        "possible": len(wells["possible"]),
                        "hydro": hydro,
                    }
                )
    detailed = [qualify_candidate(s, gauges[s["code"]], big) for s in shortlist]
    detailed.sort(key=lambda d: d["area_km2_upper_bound"])
    for d in detailed:
        w = d["well_distribution"]
        print(
            f"\n=== {d['name']} ({d['gauge']})  {d['river']}  {d['area_km2_upper_bound']:.0f} km2"
        )
        print(
            f"  body {d['body']} {d['body_name'][:70]}  wells {d['wells']} (+{d['wells_possible_not_counted']} possible, not counted)  bdlisa agreement {d['bdlisa_agreement']}"
        )
        print(
            f"  wells: pairwise min {w['min_km']:.1f} / median {w['median_km']:.1f} / max {w['max_km']:.1f} km"
        )
        print(
            f"  outlet: exact={d['outlet']['at_outlet']} ({d['outlet']['distance_to_exit_km']:.1f} km, {d['outlet']['stop']}); reaches {d['reaches']}"
        )
        print(
            f"  common window {d['common_window']} = {d['common_window_years']} y; days with >= {MIN_WELLS} wells: {d['days_with_all_counted_wells_ge_min']:.0%}"
        )
        print(f"  per well: {d['per_well']}")
        print(f"  discharge: {d['discharge']}")
        for note in d["notes"]:
            print(f"  ! {note}")
    out = cache_file(cache, "shortlist.json")
    if out is not None:
        out.write_text(json.dumps(detailed, ensure_ascii=False, indent=1), encoding="utf-8")


def summarise(done: list[dict]) -> None:
    failed = [d for d in done if "error" in d]
    ok = [d for d in done if "error" not in d]
    candidates, unresolved = [], []
    for d in ok:
        for body, wells in d["bodies"].items():
            if len(wells["certain"]) >= MIN_WELLS:
                candidates.append((d, body, wells))
            elif len(wells["certain"]) + len(wells["possible"]) >= MIN_WELLS:
                unresolved.append((d, body, wells))
    print(f"\ndelineated: {len(ok)}; not delineated (size cap or failure): {len(failed)}")
    print(
        f"exact catchments (gauge at its basin outlet): {sum(1 for d in ok if d['outlet']['at_outlet'])}"
    )
    print(f"CANDIDATES (>= {MIN_WELLS} wells of one body certainly upstream): {len(candidates)}")
    for d, body, wells in candidates:
        print(
            f"  {d['code']} {d['name'][:40]:40s} {d['area_km2']:6.0f} km2 body {body} certain {len(wells['certain'])} possible {len(wells['possible'])}"
        )
    print(
        f"UNRESOLVED (>= {MIN_WELLS} only if the gauge's own basin is taken whole): {len(unresolved)}"
    )
    for d, body, wells in unresolved:
        print(
            f"  {d['code']} {d['name'][:40]:40s} {d['area_km2']:6.0f} km2 body {body} certain {len(wells['certain'])} possible {len(wells['possible'])}"
        )


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2 or argv[1] not in (
        "inventory",
        "zones",
        "candidates",
        "check-network",
        "shortlist",
    ):
        print(__doc__)
        return 2
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    if argv[1] == "shortlist":
        run_shortlist(cache)
        return 0
    if argv[1] == "check-network":
        run_check_network(cache)
        return 0
    if argv[1] == "candidates":
        workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 4
        limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
        run_candidates(cache, "--dry" in argv, workers, limit)
        return 0
    big = run_inventory(cache)
    if argv[1] == "inventory":
        print_groups(big)
    else:
        print_zones(big)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
