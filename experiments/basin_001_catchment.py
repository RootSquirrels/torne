"""BASIN-001 gate G1 - delineate the catchment of a gauge from the Sandre BD Topage network.

The Sandre WFS publishes elementary topographic basins (between two confluences), not station
catchments, and the reach layer carries no upstream/downstream node codes. This script rebuilds the
upstream network from geometry and assigns each upstream reach to its elementary basin:

1. snap the gauge to the nearest reach (``TronconHydrographique``);
2. walk upstream: a reach flows into another when its downstream end coincides with the upstream end
   of that one (reaches are oriented along their digitisation unless ``SensEcoulementTH`` says otherwise);
3. fetch the elementary basins (``BassinVersantTopographique``) over the extent of the upstream network
   and give each upstream reach to the basin that contains its mid-point;
4. the catchment is the set of basins that received at least one reach.

Approximations, all reported in the output and in ``docs/BASIN-001-FEASIBILITY.md``:

- the basin that contains the gauge is taken **whole**, including the part downstream of the gauge, so the
  area is an **upper bound**;
- basins without any upstream reach (diffuse areas) are not added;
- areas use a local equirectangular approximation (no projection library), good to about 1 %;
- no geometry is clipped: this is a partition by elementary basins, not a DEM delineation.

It adds no dependency: GeoJSON over HTTP, pure Python geometry. The wells are then classified inside or
outside by point-in-polygon, by **geometry only**, never by any value of the series.

Usage:

    uv run python experiments/basin_001_catchment.py delineate H504062010 I403201001
    uv run python experiments/basin_001_catchment.py outlets 14 76 60 80 27 10 51 [--no-delineate] [--rows cache.json]
"""

from __future__ import annotations

import collections
import itertools
import json
import math
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from basin_001_screening import MIN_COMPLETENESS, MIN_DAYS_LAST_YEAR, MIN_YEARS, screen

SANDRE = "https://services.sandre.eaufrance.fr/geo/topage2022"
REACH = "TronconHydrographique_FXX_Topage2022"
BASIN = "BassinVersantTopographique_FXX_Topage2022"
HUBEAU_STATIONS = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/referentiel/stations"
HUBEAU_PIEZO = "https://hubeau.eaufrance.fr/api/v1/niveaux_nappes/stations"
CRS = "urn:ogc:def:crs:OGC:1.3:CRS84"  # axis order lon, lat

SNAP_TOLERANCE_DEG = 0.004  # search window around the gauge, about 400 m
JOIN_TOLERANCE_DEG = 2e-6  # two reach ends are the same node within about 0.2 m
JOIN_WINDOW_DEG = 2e-5
MAX_REACHES = 5000  # stop a runaway traversal
OUTLET_MAX_TAIL_KM = (
    1.0  # a gauge counts as "at the outlet" of its basin within this distance of the exit
)
SCREEN_MAX_REACHES = 1500  # cap for the delineation of gauges found at an outlet (time, not method)
WELL_BBOX_PAD_DEG = 0.01  # wells are looked up over the extent of the catchment, plus this margin
# Same well criteria as experiments/basin_001_screening.py, now applied to wells INSIDE the catchment.
WELL_MIN_VALUES = 3000
WELL_START_BEFORE = "2005-01-01"
WELL_END_AFTER = "2024-01-01"
GATE_MIN_WELLS_SAME_AQUIFER = 3


def fetch_json(url: str, attempts: int = 4, timeout: float = 90.0) -> dict | None:
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                return None
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                return None
        time.sleep(2 * (attempt + 1))
    return None


def wfs(
    layer: str, west: float, south: float, east: float, north: float, count: int = 500
) -> list[dict]:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"sa:{layer}",
        "outputFormat": "geojson",
        "count": str(count),
        "bbox": f"{west},{south},{east},{north},{CRS}",
    }
    page = fetch_json(f"{SANDRE}?{urllib.parse.urlencode(params)}")
    if page is None:
        raise RuntimeError(f"WFS {layer} unavailable for bbox {west},{south},{east},{north}")
    return page["features"]


def flow_ends(feature: dict) -> tuple[tuple[float, float], tuple[float, float], bool]:
    """(upstream end, downstream end, direction_known) of a reach."""
    coordinates = feature["geometry"]["coordinates"]
    first, last = tuple(coordinates[0][:2]), tuple(coordinates[-1][:2])
    sense = str(feature["properties"].get("SensEcoulementTH") or "")
    if "inverse" in sense.lower() or "oppos" in sense.lower():
        return last, first, True
    return first, last, "direction" in sense.lower()


def same_point(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= JOIN_TOLERANCE_DEG and abs(a[1] - b[1]) <= JOIN_TOLERANCE_DEG


def point_segment_km(
    px: float, py: float, ax: float, ay: float, bx: float, by: float, lat0: float
) -> float:
    kx = 111.32 * math.cos(math.radians(lat0))
    ky = 110.57
    x, y = px * kx, py * ky
    x1, y1, x2, y2 = ax * kx, ay * ky, bx * kx, by * ky
    dx, dy = x2 - x1, y2 - y1
    t = (
        0.0
        if dx == dy == 0
        else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    )
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def snap(lon: float, lat: float) -> tuple[dict, float]:
    d = SNAP_TOLERANCE_DEG
    best, best_km = None, float("inf")
    for feature in wfs(REACH, lon - d, lat - d, lon + d, lat + d):
        coordinates = feature["geometry"]["coordinates"]
        for (ax, ay), (bx, by) in itertools.pairwise(coordinates):
            km = point_segment_km(lon, lat, ax, ay, bx, by, lat)
            if km < best_km:
                best, best_km = feature, km
    if best is None:
        raise RuntimeError("no reach near the gauge")
    return best, best_km


def tail_km(feature: dict, lon: float, lat: float) -> float:
    """Distance along the reach from the gauge's projection to the reach's downstream end."""
    _, down, _ = flow_ends(feature)
    line = [(c[0], c[1]) for c in feature["geometry"]["coordinates"]]
    if not same_point(line[-1], down):
        line.reverse()
    kx, ky = 111.32 * math.cos(math.radians(lat)), 110.57
    walked, best, along = 0.0, float("inf"), 0.0
    for (ax, ay), (bx, by) in itertools.pairwise(line):
        dx, dy = (bx - ax) * kx, (by - ay) * ky
        length = math.hypot(dx, dy)
        px, py = (lon - ax) * kx, (lat - ay) * ky
        t = 0.0 if length == 0 else max(0.0, min(1.0, (px * dx + py * dy) / (length * length)))
        distance = math.hypot(px - t * dx, py - t * dy)
        if distance < best:
            best, along = distance, walked + t * length
        walked += length
    return walked - along


def basin_at(x: float, y: float) -> dict | None:
    d = 0.002
    for basin in wfs(BASIN, x - d, y - d, x + d, y + d, count=20):
        if contains(basin["geometry"], x, y):
            return basin
    return None


def reach_length_km(feature: dict, lat: float) -> float:
    kx, ky = 111.32 * math.cos(math.radians(lat)), 110.57
    line = feature["geometry"]["coordinates"]
    return sum(
        math.hypot((bx - ax) * kx, (by - ay) * ky)
        for (ax, ay), (bx, by) in itertools.pairwise([(c[0], c[1]) for c in line])
    )


def downstream_reaches(reach: dict) -> list[dict]:
    """The reaches that start where ``reach`` ends."""
    _, down, _ = flow_ends(reach)
    w = JOIN_WINDOW_DEG
    code = reach["properties"]["CdOH"]
    return [
        c
        for c in wfs(REACH, down[0] - w, down[1] - w, down[0] + w, down[1] + w, count=60)
        if c["properties"]["CdOH"] != code and same_point(flow_ends(c)[0], down)
    ]


def outlet_of_reach(reach: dict, lon: float, lat: float) -> dict:
    """Is the gauge, on ``reach``, close to the exit of its elementary basin?

    Walks downstream from the gauge, reach by reach, while the next reach still lies in the same
    elementary basin, and adds up the distance along the stream. The gauge is "at the outlet" when the
    stream leaves the basin within ``OUTLET_MAX_TAIL_KM``: then the whole elementary basin drains to the
    gauge up to that short tail, and the area is no longer a loose upper bound. The walk stops, and the
    gauge is NOT declared at the outlet, on a bifurcation, on an unstated flow direction, or beyond the
    distance limit.
    """
    _, _, known = flow_ends(reach)
    own = basin_at(*midpoint(reach))
    own_gid = own["properties"]["gid"] if own else None
    distance = tail_km(reach, lon, lat)
    exited, stop, current = False, "distance_limit", reach
    for _ in range(50):
        if own_gid is None:
            stop = "no_basin"
            break
        if distance > OUTLET_MAX_TAIL_KM:
            break
        following = downstream_reaches(current)
        if not following:
            exited, stop = True, "terminal_reach"
            break
        if len(following) > 1:
            # A diffluence: follow the arm the network calls "principal" when it is the only one.
            principal = [f for f in following if f["properties"].get("BrasTH") == "principal"]
            if len(principal) != 1:
                stop = "bifurcation"
                break
            following = principal
        other = basin_at(*midpoint(following[0]))
        if other is None or other["properties"]["gid"] != own_gid:
            exited, stop = True, "exit_basin"
            break
        distance += reach_length_km(following[0], lat)
        current = following[0]
    return {
        "direction_stated": known,
        "distance_to_exit_km": distance,
        "own_basin": own["properties"]["TopoOH"] if own else None,
        "leaves_basin": exited,
        "stop": stop,
        "at_outlet": bool(known and exited and distance <= OUTLET_MAX_TAIL_KM),
    }


def upstream_reaches(
    start: dict, max_reaches: int = MAX_REACHES
) -> tuple[dict[str, dict], dict[str, int]]:
    """Every reach upstream of ``start`` (included), keyed by ``CdOH``."""
    reaches: dict[str, dict] = {start["properties"]["CdOH"]: start}
    notes: collections.Counter = collections.Counter()
    queue = [start]
    while queue:
        current = queue.pop()
        upstream_end, _, known = flow_ends(current)
        if not known:
            notes["direction_not_stated"] += 1
        x, y = upstream_end
        w = JOIN_WINDOW_DEG
        for candidate in wfs(REACH, x - w, y - w, x + w, y + w, count=60):
            code = candidate["properties"]["CdOH"]
            if code in reaches:
                continue
            _, downstream_end, _ = flow_ends(candidate)
            if same_point(downstream_end, upstream_end):
                reaches[code] = candidate
                queue.append(candidate)
                if len(reaches) > max_reaches:
                    raise RuntimeError(f"upstream traversal exceeded {max_reaches} reaches")
    return reaches, dict(notes)


def ring_contains(ring: list, x: float, y: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def polygon_parts(geometry: dict) -> list[list]:
    return (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else list(geometry["coordinates"])
    )


def contains(geometry: dict, x: float, y: float) -> bool:
    for rings in polygon_parts(geometry):
        if ring_contains(rings[0], x, y) and not any(
            ring_contains(hole, x, y) for hole in rings[1:]
        ):
            return True
    return False


def ring_area_km2(ring: list, lat0: float) -> float:
    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
    area = 0.0
    for (x1, y1), (x2, y2) in itertools.pairwise(ring):
        area += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(area) / 2.0


def polygon_area_km2(geometry: dict, lat0: float) -> float:
    return sum(
        ring_area_km2(rings[0], lat0) - sum(ring_area_km2(hole, lat0) for hole in rings[1:])
        for rings in polygon_parts(geometry)
    )


def midpoint(feature: dict) -> tuple[float, float]:
    coordinates = feature["geometry"]["coordinates"]
    x, y = coordinates[len(coordinates) // 2][:2]
    return x, y


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def delineate(code: str, max_reaches: int = MAX_REACHES) -> dict:
    reference = fetch_json(f"{HUBEAU_STATIONS}?code_station={code}&format=json")
    if not reference or not reference["data"]:
        raise RuntimeError(f"unknown gauge {code}")
    gauge = reference["data"][0]
    lon, lat = gauge["longitude_station"], gauge["latitude_station"]
    start, snap_km = snap(lon, lat)
    outlet = outlet_of_reach(start, lon, lat)
    reaches, notes = upstream_reaches(start, max_reaches)
    xs = [c[0] for r in reaches.values() for c in r["geometry"]["coordinates"]]
    ys = [c[1] for r in reaches.values() for c in r["geometry"]["coordinates"]]
    pad = 0.01
    basins = wfs(BASIN, min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad, count=2000)
    members: dict[int, dict] = {}
    unassigned = 0
    sx, sy = midpoint(start)
    gauge_basin = next((b for b in basins if contains(b["geometry"], sx, sy)), None)
    for reach in reaches.values():
        x, y = midpoint(reach)
        owner = next((b for b in basins if contains(b["geometry"], x, y)), None)
        if owner is None:
            unassigned += 1
            continue
        members.setdefault(owner["properties"]["gid"], owner)
    area = sum(polygon_area_km2(b["geometry"], lat) for b in members.values())
    return {
        "gauge": gauge,
        "lon": lon,
        "lat": lat,
        "snap_km": snap_km,
        "reaches": len(reaches),
        "reach_notes": notes,
        "reaches_unassigned": unassigned,
        "basins": list(members.values()),
        "gauge_basin_gid": gauge_basin["properties"]["gid"] if gauge_basin else None,
        "outlet": outlet,
        "area_km2_upper_bound": area,
    }


def classify_wells(result: dict) -> list[dict]:
    """Wells over the extent of the catchment, classified by geometry only.

    A well in a member basin other than the gauge's own is certainly upstream. A well in the gauge's own
    basin is certainly upstream only when the gauge sits at that basin's outlet; otherwise it may lie
    downstream of the gauge (the basin is taken whole).
    """
    xs = [
        c[0] for b in result["basins"] for rings in polygon_parts(b["geometry"]) for c in rings[0]
    ]
    ys = [
        c[1] for b in result["basins"] for rings in polygon_parts(b["geometry"]) for c in rings[0]
    ]
    pad = WELL_BBOX_PAD_DEG
    box = f"{min(xs) - pad},{min(ys) - pad},{max(xs) + pad},{max(ys) + pad}"
    page = fetch_json(f"{HUBEAU_PIEZO}?bbox={box}&size=5000&format=json")
    if page is None:
        return []
    classified = []
    for well in page["data"]:
        if well.get("y") is None or well.get("x") is None:
            continue
        owners = [b for b in result["basins"] if contains(b["geometry"], well["x"], well["y"])]
        in_other = any(b["properties"]["gid"] != result["gauge_basin_gid"] for b in owners)
        certain = in_other or (bool(owners) and result["outlet"]["at_outlet"])
        classified.append({"well": well, "inside": bool(owners), "certain": certain})
    return classified


def report(result: dict) -> None:
    """Print the delineation and the gate G1 verdict for one gauge."""
    gauge = result["gauge"]
    outlet = result["outlet"]
    print(f"\n=== {gauge['libelle_station']} ({gauge['code_station']})", flush=True)
    print(f"  gauge snapped to a reach {result['snap_km'] * 1000:.0f} m away")
    print(
        f"  at the outlet of its elementary basin: {outlet['at_outlet']} "
        f"(distance to the basin exit {outlet['distance_to_exit_km']:.2f} km, stop: {outlet['stop']}, "
        f"direction stated {outlet['direction_stated']})"
    )
    print(
        f"  upstream reaches: {result['reaches']}  (unassigned to a basin: {result['reaches_unassigned']})  "
        f"notes: {result['reach_notes']}"
    )
    print(
        f"  elementary basins: {len(result['basins'])}   area: {result['area_km2_upper_bound']:.0f} km2"
        f" ({'minus the tail, almost exact' if outlet['at_outlet'] else 'UPPER BOUND'})"
    )
    wells = classify_wells(result)
    inside = [entry["well"] for entry in wells if entry["inside"]]
    long_inside = [w for w in inside if (w.get("nb_mesures_piezo") or 0) >= WELL_MIN_VALUES]
    qualifying = [
        w
        for w in long_inside
        if (w.get("date_debut_mesure") or "9999") <= WELL_START_BEFORE
        and (w.get("date_fin_mesure") or "") >= WELL_END_AFTER
    ]
    sure = {e["well"]["code_bss"] for e in wells if e["certain"]}
    print(
        f"  wells over the catchment extent: {len(wells)}; inside: {len(inside)}; "
        f"long (>= {WELL_MIN_VALUES} values): {len(long_inside)}; "
        f"also starting <= {WELL_START_BEFORE[:4]} and ending >= {WELL_END_AFTER[:4]}: {len(qualifying)}"
    )
    for well in long_inside:
        mark = "*" if well in qualifying else " "
        where = "upstream" if well["code_bss"] in sure else "gauge basin (may be downstream)"
        body = (well.get("noms_masse_eau_edl") or ["(no aquifer body)"])[0]
        print(
            f"   {mark} {well['code_bss']:16s} {well.get('date_debut_mesure')}.."
            f"{well.get('date_fin_mesure')} n={well.get('nb_mesures_piezo')} {body} [{where}]"
        )
    every = collections.Counter(a for w in qualifying for a in (w.get("noms_masse_eau_edl") or []))
    certain = collections.Counter(
        a for w in qualifying if w["code_bss"] in sure for a in (w.get("noms_masse_eau_edl") or [])
    )
    top_all = every.most_common(1)[0] if every else None
    top_certain = certain.most_common(1)[0] if certain else None
    if top_certain is not None and top_certain[1] >= GATE_MIN_WELLS_SAME_AQUIFER:
        verdict = "PASS (wells certainly upstream)"
    elif top_all is not None and top_all[1] >= GATE_MIN_WELLS_SAME_AQUIFER:
        verdict = "PASS ONLY AS AN UPPER BOUND (wells of the gauge's own basin may be downstream)"
    else:
        verdict = "FAIL"
    print(
        f"  GATE G1 ({GATE_MIN_WELLS_SAME_AQUIFER}+ qualifying wells in one aquifer body): {verdict}"
    )
    print(f"     all inside: {top_all}; certainly upstream: {top_certain}", flush=True)


def run_delineate(codes: list[str], max_reaches: int) -> None:
    for code in codes:
        try:
            report(delineate(code, max_reaches))
        except RuntimeError as error:
            print(f"\n=== {code}\n  NOT DELINEATED: {error}", flush=True)


def run_outlets(departments: list[str], delineate_found: bool, rows_path: str | None) -> None:
    """Find the gauges that sit at the outlet of an elementary basin, then delineate them.

    ``rows_path`` caches the discharge screening (slow): read when the file exists, written otherwise.
    """
    if rows_path and pathlib.Path(rows_path).is_file():
        screened = json.loads(pathlib.Path(rows_path).read_text(encoding="utf-8"))
    else:
        screened = screen(departments)
        if rows_path:
            pathlib.Path(rows_path).write_text(
                json.dumps(screened, ensure_ascii=False), encoding="utf-8"
            )
    rows = [
        r
        for r in screened
        if r["years"] >= MIN_YEARS
        and r["completeness"] >= MIN_COMPLETENESS
        and (r["days_last_year"] or 0) >= MIN_DAYS_LAST_YEAR
    ]
    print(
        f"\n{len(rows)} gauges pass the discharge criteria; testing which sit at a basin outlet",
        flush=True,
    )
    found = []
    for row in rows:
        reference = fetch_json(f"{HUBEAU_STATIONS}?code_station={row['code']}&format=json")
        if not reference or not reference["data"]:
            continue
        gauge = reference["data"][0]
        lon, lat = gauge["longitude_station"], gauge["latitude_station"]
        try:
            reach, _ = snap(lon, lat)
            outlet = outlet_of_reach(reach, lon, lat)
        except RuntimeError as error:
            print(f"  {row['code']} {row['name'][:36]:36s} NOT TESTED: {error}", flush=True)
            continue
        flag = "OUTLET" if outlet["at_outlet"] else "-"
        print(
            f"  {row['code']} {row['name'][:36]:36s} {row['years']:5.1f} y to exit {outlet['distance_to_exit_km']:5.2f} km {outlet['stop']:14s} "
            f"dir {outlet['direction_stated']!s:5} {flag}",
            flush=True,
        )
        if outlet["at_outlet"]:
            found.append(row)
    print(
        f"\n{len(found)} of {len(rows)} gauges sit at the outlet of an elementary basin", flush=True
    )
    if delineate_found:
        found.sort(key=lambda r: -r["years"])
        run_delineate([r["code"] for r in found], SCREEN_MAX_REACHES)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 3 or argv[1] not in ("delineate", "outlets"):
        print(__doc__)
        return 2
    if argv[1] == "delineate":
        run_delineate(argv[2:], MAX_REACHES)
    else:
        rest = argv[2:]
        rows_path = rest[rest.index("--rows") + 1] if "--rows" in rest else None
        departments = [a for a in rest if not a.startswith("--") and a != rows_path]
        run_outlets(departments, "--no-delineate" not in rest, rows_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
