"""POWER-002 - declared against realised nuclear availability in France.

Question. REMIT obliges the operator to publish unavailabilities of 100 MW or more. ENTSO-E A73 gives the actual output of each
reactor every 15 minutes. How much nuclear capacity is offline without being declared at that moment, how late are the
declarations, and does the declared availability match what the units actually deliver? The product is a daily series of
"invisible" offline capacity (GW), which no public source publishes, with a lag distribution.

DATA
    Output: ENTSO-E Transparency Platform, A73 (actual generation per unit), process A16, zone FR, nuclear units (psrType B14),
    15-minute grid in UTC, 1 November 2025 - 31 October 2026 (token read from ``.env``, never printed).
    Declarations: EDF REMIT history (Data Fair), nuclear, all causes, every version of every record overlapping the period; a
    unit is matched to A73 by name with spaces and case removed. Record times without a zone are read as UTC (checked and
    printed at run time).
    Independent reference: RTE eco2mix national consolidated nuclear output (ODRE), compared with the sum of units.
    Pmax of a unit = largest ``puissance_maximale_mw`` of its records.

PROTOCOL, fixed before any data was downloaded
    Offline slot: output < 5 % of Pmax. Offline event: at least 24 consecutive offline slots (6 h) not starting in the first slot
    of the period. Declared at slot t: some record version known as latest Active for its identifier with
    ``puissance_disponible_mw`` < 0.9 Pmax covers t. For a record, the time it became visible is the publication time of the FIRST
    version of its identifier.
    Q0 validation. Daily sum of unit outputs against ODRE nuclear; share of days within 3 %.
    Q1 coverage. Share of offline events never declared by any record during the event.
    Q2 lag. For each declared event, first publication time of a covering record minus the start of the event; shares published
    more than 1 h and more than 24 h after the start.
    Q3 invisible capacity. For each 15-min slot, the sum over units that are offline and whose covering record, if any, had not
    yet been published (visible time > slot time). Daily mean in GW; the share of days above 0.2 GW.
    Q4 over-delivery. Slots where output exceeds declared availability by more than max(50 MW, 5 % Pmax) for at least 2 h
    consecutively; number of events per month.
    Decision KNOWLEDGE_PRODUCT_VIABLE only if (a) Q0: at least 95 % of compared days within 3 %; (b) Q2: at least 5 % of declared
    events are published more than 1 h after their start OR Q1 above 5 %; (c) Q3: invisible capacity above 0.2 GW on at least 10 %
    of days. Otherwise NO_GAP.
    DEVIATIONS after a first complete run (the run was invalid and its decision is void): (1) the ODRE loader used wrong field
    names (``date_heure`` is the field), so no day was compared; fixed. (2) Records with ``puissance_maximale_mw`` = 0 (daily
    placeholder notices, not outages) were read as full outages; they are now ignored, and a record's declared loss is read as
    ``puissance_maximale_mw - puissance_disponible_mw`` subtracted from the unit's Pmax. The decision thresholds were not changed.
    (3) Visibility. The protocol read the time a record became visible as the publication of the FIRST version of its identifier.
    That is wrong: identifiers are rescheduled up to dozens of times (a planned outage first published in 2022 shifted to 2026),
    which gave "declaration lags" of years for outages of a few hours. Visibility is now the earliest publication of any version
    (not cancelled, identifier still Active at its latest version) whose dates cover the slot. A diagnostic of the lag by event
    duration and a variant with ``--declared-fraction 0.5`` were also added after seeing results; neither enters the decision.
    Limits stated in advance: a trip or a shutdown for a few hours may be declared with the reactor's own notice rules; Q3 is a
    measurement of the visibility gap, not a price signal; no price link is tested here (low power was shown in POWER-001).

Usage:

    uv run python experiments/power_002_declared_vs_realised.py --cache DIR
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import pathlib
import statistics
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np
from power_001_golfech import EDF, EDF_HISTORY, cached

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from torne.acquisition.credentials import lire_fichier_env

# The period can be moved with TORNE_A73_START / TORNE_A73_END (ISO dates, UTC); POWER-003 uses it to compute calendar 2025.
START = dt.datetime.fromisoformat(os.environ.get("TORNE_A73_START", "2025-11-01")).replace(
    tzinfo=dt.UTC
)
END = dt.datetime.fromisoformat(os.environ.get("TORNE_A73_END", "2026-11-01")).replace(
    tzinfo=dt.UTC
)
STEP = dt.timedelta(minutes=15)
N_SLOTS = int((END - START) / STEP)
ENTSOE = "https://web-api.tp.entsoe.eu/api"
ODRE = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets"
OFFLINE_FRACTION, DECLARED_FRACTION = 0.05, 0.9
# POST HOC variant (added after the second run, not part of the decision): a record only "covers" an outage if it leaves less
# than this share of Pmax available; the pre-declared 0.9 lets an old 10 % derating count as the declaration of a trip.
if "--declared-fraction" in sys.argv:
    DECLARED_FRACTION = float(sys.argv[sys.argv.index("--declared-fraction") + 1])
MIN_EVENT_SLOTS, OVER_SLOTS = 24, 8
WINDOW_DAYS = 1  # A73 refuses windows longer than one day


def normal(name: str) -> str:
    return name.upper().replace(" ", "")


def entsoe_token() -> str:
    env = lire_fichier_env(pathlib.Path(__file__).resolve().parent.parent / ".env")
    name = next((k for k in env if "ENTSO" in k.upper()), None)
    if name is None or not env[name]:
        raise RuntimeError("no ENTSO-E variable in .env")
    return env[name]


def load_output() -> dict[str, list[float | None]]:
    token = entsoe_token()
    out: dict[str, list[float | None]] = {}
    start = START
    while start < END:
        end = min(start + dt.timedelta(days=WINDOW_DAYS), END)
        params = {
            "documentType": "A73",
            "processType": "A16",
            "in_Domain": "10YFR-RTE------C",
            "periodStart": start.strftime("%Y%m%d%H%M"),
            "periodEnd": end.strftime("%Y%m%d%H%M"),
            "securityToken": token,
        }
        url = f"{ENTSOE}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=300) as response:
                root = ET.fromstring(response.read())
        except Exception as error:  # never echo the URL: it carries the token
            raise RuntimeError(
                f"ENTSO-E A73 failed for {start:%Y-%m-%d}: {type(error).__name__}"
            ) from None
        ns = {"m": root.tag.split("}")[0].strip("{")}
        for ts in root.iterfind("m:TimeSeries", ns):
            if ts.findtext(".//m:MktPSRType/m:psrType", namespaces=ns) != "B14":
                continue
            name = normal(ts.findtext(".//m:PowerSystemResources/m:name", namespaces=ns) or "")
            series = out.setdefault(name, [None] * N_SLOTS)
            for period in ts.iterfind("m:Period", ns):
                begin = dt.datetime.fromisoformat(
                    period.findtext("m:timeInterval/m:start", namespaces=ns).replace("Z", "+00:00")
                )
                minutes = {"PT60M": 60, "PT30M": 30, "PT15M": 15}[
                    period.findtext("m:resolution", namespaces=ns)
                ]
                for point in period.iterfind("m:Point", ns):
                    first = begin + dt.timedelta(
                        minutes=minutes * (int(point.findtext("m:position", namespaces=ns)) - 1)
                    )
                    value = float(point.findtext("m:quantity", namespaces=ns))
                    for k in range(minutes // 15):
                        index = int((first + k * STEP - START) / STEP)
                        if 0 <= index < N_SLOTS:
                            series[index] = value
        print(f"  A73 {start:%Y-%m-%d} done, units so far {len(out)}", flush=True)
        start = end
    return out


def load_declarations() -> list[dict]:
    select = (
        "nom,date_de_debut,date_de_fin,date_de_publication,puissance_maximale_mw,puissance_disponible_mw,"
        "numero_de_version,status,identifiant"
    )
    qs = urllib.parse.quote('filiere:"Nucléaire"')
    seen: dict[tuple[str, int], dict] = {}
    month = START.replace(day=1) - dt.timedelta(days=60)  # records that began before the period
    while month < END:
        nxt = (month + dt.timedelta(days=32)).replace(day=1)
        url = (
            f"{EDF}/{EDF_HISTORY}/lines?size=10000&qs={qs}&select={urllib.parse.quote(select, safe=',')}"
            f"&date_de_debut_lte={nxt.date().isoformat()}&date_de_fin_gte={month.date().isoformat()}"
        )
        with urllib.request.urlopen(url, timeout=180) as response:
            page = json.loads(response.read())
        for r in page["results"]:
            seen[(r["identifiant"], r["numero_de_version"])] = r
        month = nxt
    return list(seen.values())


def load_odre() -> dict[str, float]:
    """ISO date -> daily mean nuclear output (MW) from the eco2mix consolidated dataset, with the number of slots."""
    out: dict[str, list[float]] = collections.defaultdict(list)
    for dataset in ("eco2mix-national-cons-def", "eco2mix-national-tr"):
        offset = 0
        while offset < 9900:
            where = urllib.parse.quote(
                f"date_heure >= '{START:%Y-%m-%dT%H:%M:%S}' AND date_heure < '{END:%Y-%m-%dT%H:%M:%S}'"
            )
            url = (
                f"{ODRE}/{dataset}/records?select=date_heure,nucleaire&where={where}"
                f"&order_by=date_heure&limit=100&offset={offset}"
            )
            with urllib.request.urlopen(url, timeout=120) as response:
                page = json.loads(response.read())
            for r in page.get("results", []):
                if r.get("nucleaire") is not None:
                    out[f"{dataset}|{r['date_heure'][:10]}"].append(r["nucleaire"])
            offset += 100
            if len(page.get("results", [])) < 100:
                break
    best: dict[str, list[float]] = {}
    for key, values in out.items():
        day = key.split("|")[1]
        if day not in best or len(values) > len(best[day]):
            best[day] = values
    return {d: statistics.fmean(v) for d, v in best.items() if len(v) >= 40}


def parse_time(text: str) -> dt.datetime:
    moment = dt.datetime.fromisoformat(text)
    return moment.replace(tzinfo=dt.UTC) if moment.tzinfo is None else moment.astimezone(dt.UTC)


def slot_range(start: dt.datetime, end: dt.datetime) -> range:
    lo = max(int(np.ceil((start - START) / STEP)), 0)
    hi = min(int((end - START) / STEP), N_SLOTS)
    return range(lo, max(hi, lo))


def runs(mask: np.ndarray, minimum: int):
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        if (not flag or i == len(mask) - 1) and start is not None:
            end = i + 1 if flag else i
            if end - start >= minimum:
                yield start, end
            start = None


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    output = cached(cache, "a73_output.json.gz", load_output)
    records = cached(cache, "remit_all.json.gz", load_declarations)
    odre = cached(cache, "odre_nuclear.json.gz", load_odre)
    print(
        f"units in A73: {len(output)}; REMIT record versions: {len(records)}; ODRE days: {len(odre)}"
    )
    sample = records[0]
    print(
        f"record time format check: {sample['date_de_debut']!r} / published {sample['date_de_publication']!r}"
    )

    latest: dict[str, dict] = {}
    first_published: dict[str, dt.datetime] = {}
    for r in records:
        k = r["identifiant"]
        if k not in latest or r["numero_de_version"] > latest[k]["numero_de_version"]:
            latest[k] = r
        published = parse_time(r["date_de_publication"])
        if k not in first_published or published < first_published[k]:
            first_published[k] = published
    pmax: dict[str, float] = {}
    for r in records:
        pmax[normal(r["nom"])] = max(pmax.get(normal(r["nom"]), 0.0), r["puissance_maximale_mw"])
    unmatched = sorted(set(output) - set(pmax))
    print(f"A73 units without any REMIT record to read Pmax from: {unmatched}")

    inf = np.inf
    availability = {u: np.full(N_SLOTS, pmax.get(u, 1300.0)) for u in output}
    visible = {
        u: np.full(N_SLOTS, inf) for u in output
    }  # seconds since START at which a covering record appeared
    for r in latest.values():
        u = normal(r["nom"])
        if r["status"] != "Active" or u not in output or r["puissance_maximale_mw"] <= 0:
            continue
        slots = slot_range(parse_time(r["date_de_debut"]), parse_time(r["date_de_fin"]))
        if not slots:
            continue
        sel = np.arange(slots.start, slots.stop)
        declared = max(
            pmax.get(u, 1300.0) - (r["puissance_maximale_mw"] - r["puissance_disponible_mw"]), 0.0
        )
        availability[u][sel] = np.minimum(availability[u][sel], declared)

    # Visibility, by vintage: the time at which ANY version that places the loss on these slots was published (an outage
    # identifier is rescheduled many times, so the first version of an identifier says nothing about when this window was announced).
    for r in records:
        if latest[r["identifiant"]]["status"] != "Active" or r["status"] in (
            "Annulée",
            "Supprimée",
        ):
            continue
        u = normal(r["nom"])
        if u not in output or r["puissance_maximale_mw"] <= 0:
            continue
        declared = max(
            pmax.get(u, 1300.0) - (r["puissance_maximale_mw"] - r["puissance_disponible_mw"]), 0.0
        )
        slots = slot_range(parse_time(r["date_de_debut"]), parse_time(r["date_de_fin"]))
        if slots and declared < DECLARED_FRACTION * pmax.get(u, 1300.0):
            sel = np.arange(slots.start, slots.stop)
            published = (parse_time(r["date_de_publication"]) - START).total_seconds()
            visible[u][sel] = np.minimum(visible[u][sel], published)

    # Q0
    sums = np.zeros(N_SLOTS)
    for series in output.values():
        sums += np.array([0.0 if v is None else v for v in series])
    days = [START + dt.timedelta(days=i) for i in range((END - START).days)]
    close, compared = 0, 0
    for i, day in enumerate(days):
        key = day.date().isoformat()
        if key in odre:
            compared += 1
            ours = sums[i * 96 : (i + 1) * 96].mean()
            close += abs(ours - odre[key]) <= 0.03 * odre[key]
    share0 = close / compared if compared else float("nan")
    print(
        f"\nQ0 validation: {compared} days compared with ODRE; within 3 %: {close} ({share0:.1%})"
    )

    # Q1, Q2, Q3, Q4
    lags, durations, undeclared, n_events = [], [], 0, 0
    undeclared_list: list[tuple] = []
    invisible_total = np.zeros(N_SLOTS)
    over_by_month: collections.Counter = collections.Counter()
    for u, series in output.items():
        g = np.array([np.nan if v is None else v for v in series])
        # A73 leaves holes in the series: carry the last value across them, otherwise one hole cuts an outage in two
        if np.isnan(g).any():
            index = np.where(~np.isnan(g), np.arange(N_SLOTS), 0)
            np.maximum.accumulate(index, out=index)
            g = g[index]
        p = pmax.get(u, 1300.0)
        offline = np.nan_to_num(g, nan=p) < OFFLINE_FRACTION * p
        for s, e in runs(offline, MIN_EVENT_SLOTS):
            if s == 0:
                continue
            n_events += 1
            t_start = (s * STEP).total_seconds()
            seen_times = visible[u][s:e]
            first = seen_times.min()
            if not np.isfinite(first):
                undeclared += 1
                undeclared_list.append(
                    (u, START + s * STEP, (e - s) / 4.0, float(availability[u][s:e].mean()))
                )
            else:
                lags.append((first - t_start) / 3600.0)
                durations.append((e - s) / 4.0)
            slot_seconds = np.arange(s, e) * STEP.total_seconds()
            invisible_total[s:e] += (seen_times > slot_seconds) * (p / 1000.0)
        over = np.nan_to_num(g, nan=0.0) > availability[u] + max(50.0, 0.05 * p)
        for s, _ in runs(over, OVER_SLOTS):
            over_by_month[(START + s * STEP).strftime("%Y-%m")] += 1
    q1 = undeclared / n_events if n_events else float("nan")
    print(
        "never-declared offline events (post hoc listing): unit, start, hours, mean declared availability MW"
    )
    for u, begin, hours, avail in sorted(undeclared_list, key=lambda x: -x[2])[:12]:
        print(
            f"  {u:14s} {begin:%Y-%m-%d %H:%M} {hours:7.1f} h  declared availability {avail:7.0f}"
        )
    lags_a = np.array(lags)
    # POST HOC diagnostic, not part of the decision: the lag by event duration
    for label, mask in (
        ("< 2 days", np.array(durations) < 48),
        ("2-14 days", (np.array(durations) >= 48) & (np.array(durations) < 336)),
        (">= 14 days", np.array(durations) >= 336),
    ):
        if mask.any():
            sub = lags_a[mask]
            print(
                f"  lag by duration {label:10s} n = {mask.sum():4d}: percentiles 10/50/90 = "
                f"{np.quantile(sub, 0.1):+.1f} / {np.median(sub):+.1f} / {np.quantile(sub, 0.9):+.1f} h; "
                f"after start {np.mean(sub > 0):.1%}, > 1 h after {np.mean(sub > 1):.1%}"
            )
    late1 = float((lags_a > 1).mean()) if lags_a.size else float("nan")
    late24 = float((lags_a > 24).mean()) if lags_a.size else float("nan")
    print(f"\nQ1 offline events >= 6 h: {n_events}; never declared: {undeclared} ({q1:.1%})")
    if lags_a.size:
        print(
            f"Q2 declared events: {lags_a.size}; lag median {np.median(lags_a):+.1f} h, 10th/90th percentile "
            f"{np.quantile(lags_a, 0.1):+.1f} / {np.quantile(lags_a, 0.9):+.1f} h; published > 1 h after start {late1:.1%}; > 24 h {late24:.1%}"
        )
    daily = invisible_total.reshape(-1, 96).mean(axis=1)
    share3 = float((daily > 0.2).mean())
    print(
        f"Q3 invisible offline capacity: mean {daily.mean():.2f} GW, 90th percentile {np.quantile(daily, 0.9):.2f} GW, "
        f"max {daily.max():.2f} GW; days above 0.2 GW: {share3:.1%}"
    )
    print(
        "Q4 over-delivery events per month: "
        + ", ".join(f"{m}: {n}" for m, n in sorted(over_by_month.items()))
    )
    a = share0 >= 0.95
    b = (late1 >= 0.05) or (q1 > 0.05)
    c = share3 >= 0.10
    print(
        f"\nDECISION: (a) validation >= 95 %: {a}; (b) lag or coverage gap: {b}; (c) invisible capacity above 0.2 GW on >= 10 % of days: {c}"
    )
    print("  ->", "KNOWLEDGE_PRODUCT_VIABLE" if (a and b and c) else "NO_GAP")
    if cache is not None:
        np.savetxt(
            cache / "invisible_daily.csv",
            daily,
            fmt="%.3f",
            header="invisible_GW_daily_mean_from_2025-11-01",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
