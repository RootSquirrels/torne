"""POWER-001, national level - can weather forecasts predict the GW of nuclear power lost to the environment, and does the
French day-ahead price already react to the part that is predictable but not yet announced?

Context: at Golfech the limitation alert is a function of the weather forecast (``power_001_golfech.py``), and declared
environmental curtailments moved the French day-ahead price only in the extreme summer of 2026 (``power_001_price_link.py``).
The exposure that matters is national. This script asks the two questions that remain.

DATA
    Curtailments: EDF REMIT history, all nuclear units, records whose text declares an environmental external cause, ALL
    versions with their publication time. Realised loss: latest version of each identifier, kept if Active. Loss KNOWN AT
    THE AUCTION for day D: for each identifier the latest version published before 12:00 on D-1 (day-ahead gate), counted
    only if Active, summed over units (largest shortfall per unit and day).
    Weather: ERA5 daily mean temperature (observed) and Open-Meteo previous-runs archived forecasts (the forecast for a day
    issued N days earlier, N = 1..7, from mid-2021) for Paris, Lyon and Toulouse. National temperature = mean of the three.
    Prices: ENTSO-E Transparency Platform, day-ahead, zone FR (token read from ``.env``, never printed); cross-checked
    against the Energy-Charts republication used in ``power_001_price_link.py``.

PROTOCOL, fixed before any new data was downloaded
    Population: summer days (1 June-30 September) of 2022-2026, the years for which archived forecasts exist.

    T1, national model. Lead h in {3, 7}: issued on day d = D - h about day D. Features at issue time: the 7-day mean
    national temperature ending at D, the 7-day mean Lyon temperature ending at D (the Rhone plants dominate the
    exposure), and the 3-day change of the national mean; observed days up to d, forecast days after. Model: least squares
    on sqrt(GW lost) with the three features and the squares of the two means, trained leave-one-season-out on the other
    years of 2018-2026 with perfect forecasts (observed temperature), applied to the test season with real forecasts.
    Baselines: B = same model on the observed national temperature at issue (no forecast); G = the national forecast
    temperature alone (linear and square).
    Metric: AUC for "more than 1 GW lost on day D", pooled over the five seasons, 90 % bootstrap resampling 7-day blocks
    within each season (2 000 resamples, seed 20261102). Also the Spearman correlation with GW lost.
    Verdict NATIONAL_SIGNAL if, at lead 3, the 5 % bound of the model's AUC is above 0.75 AND the 90 % interval of
    AUC(model) - AUC(B) is above 0. The comparison with G is reported, and decides how the signal is read: if the model does
    not beat G, the signal is the temperature forecast.

    T2, "already in the price?". price(D) = a(year, month) + b1 * lost_known(D) + b2 * predicted_GW(D | issued h days
    earlier) + temperature-forecast-for-D (issued D-1, linear and square) + weekend; Newey-West errors (7 lags, inside each
    summer), 90 % intervals, 2022-2026. Reading, fixed now:
      - b2 interval above 0 and b2 >= 1 EUR/MWh per GW: the day-ahead price ALREADY reacts to curtailments that are
        predictable but not yet announced: the information is anticipated, PARK POWER-001.
      - b2 interval containing 0 (or below): the price reacts only to the announced loss. That is NECESSARY for an edge, not
        sufficient: proving it needs forward prices, which are not open. POWER-001 is then at most CONDITIONAL.
    Limits stated in advance: day-ahead prices alone cannot say what the market believed days before D; the exposure outside
    2026 is small, so the power is low; no fuel or carbon price.

Usage:

    uv run python experiments/power_001_national.py --cache DIR
"""

from __future__ import annotations

import collections
import datetime as dt
import pathlib
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import numpy as np
from basin_001_catchment import fetch_json
from power_001_golfech import (
    EDF,
    EDF_HISTORY,
    OPEN_METEO,
    auc,
    cached,
    in_summer,
)
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from torne.acquisition.credentials import lire_fichier_env

PREVIOUS_RUNS = "https://previous-runs-api.open-meteo.com/v1/forecast"
ENTSOE = "https://web-api.tp.entsoe.eu/api"
FR_DOMAIN = "10YFR-RTE------C"
PARIS_TZ = ZoneInfo("Europe/Paris")
CITIES = {"paris": (48.85, 2.35), "lyon": (45.76, 4.84), "toulouse": (43.60, 1.44)}
TEST_SEASONS = range(2022, 2027)
ALL_YEARS = range(2018, 2027)
LEADS = (3, 7)
GW_EVENT = 1.0
SEED = 20261102
N_BOOTSTRAP = 2000
BLOCK_DAYS = 7
NW_LAGS = 7
START, END = dt.date(2018, 1, 1), dt.date(2026, 10, 31)
FORECAST_FIRST_DAY = dt.date(2021, 6, 1)


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------


def load_observed() -> dict[str, dict[str, float]]:
    out = {}
    for city, (lat, lon) in CITIES.items():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START.isoformat(),
            "end_date": END.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": "Europe/Paris",
        }
        page = fetch_json(f"{OPEN_METEO}?{urllib.parse.urlencode(params)}", timeout=120.0)
        if page is None:
            raise RuntimeError("air archive unavailable")
        out[city] = {
            d: v
            for d, v in zip(
                page["daily"]["time"], page["daily"]["temperature_2m_mean"], strict=True
            )
            if v is not None
        }
    return out


def load_forecasts() -> dict[str, dict[str, dict[str, float]]]:
    """city -> lead -> ISO date -> daily mean of the forecast issued `lead` days earlier."""
    names = ",".join(f"temperature_2m_previous_day{k}" for k in range(1, 8))
    out: dict = {city: {str(k): {} for k in range(1, 8)} for city in CITIES}
    for city, (lat, lon) in CITIES.items():
        for year in range(FORECAST_FIRST_DAY.year, END.year + 1):
            start, end = (
                max(dt.date(year, 1, 1), FORECAST_FIRST_DAY),
                min(dt.date(year, 12, 31), END),
            )
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "hourly": names,
                "timezone": "Europe/Paris",
            }
            page = fetch_json(f"{PREVIOUS_RUNS}?{urllib.parse.urlencode(params)}", timeout=240.0)
            if page is None:
                raise RuntimeError(f"archived forecasts unavailable ({city}, {year})")
            times = page["hourly"]["time"]
            for k in range(1, 8):
                buckets: dict[str, list[float]] = collections.defaultdict(list)
                for stamp, value in zip(
                    times, page["hourly"][f"temperature_2m_previous_day{k}"], strict=True
                ):
                    if value is not None:
                        buckets[stamp[:10]].append(value)
                out[city][str(k)].update(
                    {d: statistics.fmean(v) for d, v in buckets.items() if len(v) >= 20}
                )
    return out


def load_events_all_versions() -> list[dict]:
    q = urllib.parse.quote("environnement")
    qs = urllib.parse.quote('filiere:"Nucléaire"')
    select = (
        "nom,date_de_debut,date_de_fin,date_de_publication,puissance_maximale_mw,puissance_disponible_mw,"
        "numero_de_version,status,identifiant"
    )
    page = fetch_json(
        f"{EDF}/{EDF_HISTORY}/lines?size=10000&q={q}&qs={qs}&select={select}&sort=date_de_debut"
    )
    if page is None:
        raise RuntimeError("EDF history unavailable")
    return page["results"]


def entsoe_token() -> str:
    env = lire_fichier_env(pathlib.Path(__file__).resolve().parent.parent / ".env")
    name = next((k for k in env if "ENTSO" in k.upper()), None)
    if name is None or not env[name]:
        raise RuntimeError("no ENTSO-E variable in .env")
    return env[name]


def entsoe_month(token: str, year: int, month: int) -> dict[str, list[float]]:
    """Day-ahead prices of one month: local ISO date -> list of prices (hourly or quarter-hourly)."""
    start = dt.datetime(year, month, 1) - dt.timedelta(days=1)
    end = dt.datetime(year + (month == 12), month % 12 + 1, 1) + dt.timedelta(days=1)
    params = {
        "documentType": "A44",
        "in_Domain": FR_DOMAIN,
        "out_Domain": FR_DOMAIN,
        "periodStart": start.strftime("%Y%m%d0000"),
        "periodEnd": end.strftime("%Y%m%d0000"),
        "securityToken": token,
    }
    url = f"{ENTSOE}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        # never echo the URL: it carries the token
        raise RuntimeError(f"ENTSO-E answered HTTP {error.code} for {year}-{month:02d}") from None
    except urllib.error.URLError:
        raise RuntimeError(f"ENTSO-E unreachable for {year}-{month:02d}") from None
    root = ET.fromstring(body)
    ns = {"m": root.tag.split("}")[0].strip("{")}
    out: dict[str, list[float]] = collections.defaultdict(list)
    for period in root.iterfind(".//m:Period", ns):
        begin = dt.datetime.fromisoformat(
            period.find("m:timeInterval/m:start", ns).text.replace("Z", "+00:00")
        )
        resolution = period.find("m:resolution", ns).text
        step = {"PT60M": 60, "PT30M": 30, "PT15M": 15}[resolution]
        for point in period.iterfind("m:Point", ns):
            position = int(point.find("m:position", ns).text)
            price = float(point.find("m:price.amount", ns).text)
            moment = (begin + dt.timedelta(minutes=step * (position - 1))).astimezone(PARIS_TZ)
            out[moment.date().isoformat()].append(price)
    return dict(out)


def load_prices() -> dict[str, float]:
    token = entsoe_token()
    daily: dict[str, list[float]] = {}
    for year in range(2022, 2027):
        for month in (5, 6, 7, 8, 9):
            for day, values in entsoe_month(token, year, month).items():
                # the request overlaps the neighbouring months: keep the most complete copy of a day
                if len(values) > len(daily.get(day, [])):
                    daily[day] = values
    return {d: statistics.fmean(v) for d, v in daily.items() if len(v) >= 23}


# --------------------------------------------------------------------------
# curtailments
# --------------------------------------------------------------------------


def shortfall_by_unit_day(events: list[dict]) -> dict[dt.date, float]:
    per_unit: dict[tuple[str, dt.date], float] = {}
    for e in events:
        start = dt.datetime.fromisoformat(e["date_de_debut"]).date()
        end = dt.datetime.fromisoformat(e["date_de_fin"]).date()
        lost = e["puissance_maximale_mw"] - e["puissance_disponible_mw"]
        day = start
        while day <= end:
            key = (e["nom"], day)
            per_unit[key] = max(per_unit.get(key, 0.0), lost)
            day += dt.timedelta(days=1)
    total: dict[dt.date, float] = collections.defaultdict(float)
    for (_, day), lost in per_unit.items():
        total[day] += lost / 1000.0
    return dict(total)


def realised_loss(records: list[dict]) -> dict[dt.date, float]:
    best: dict[str, dict] = {}
    for r in records:
        k = r["identifiant"]
        if k not in best or r["numero_de_version"] > best[k]["numero_de_version"]:
            best[k] = r
    return shortfall_by_unit_day([r for r in best.values() if r["status"] == "Active"])


def known_loss(records: list[dict], days: list[dt.date]) -> dict[dt.date, float]:
    """Loss for each day D as published before 12:00 on D-1 (latest version per identifier, if Active)."""
    by_id: dict[str, list[dict]] = collections.defaultdict(list)
    for r in records:
        by_id[r["identifiant"]].append(r)
    for versions in by_id.values():
        versions.sort(key=lambda r: r["numero_de_version"])
    out = {}
    for day in days:
        cutoff = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(12, 0))
        chosen = []
        for versions in by_id.values():
            published = [
                v
                for v in versions
                if dt.datetime.fromisoformat(v["date_de_publication"]).replace(tzinfo=None)
                <= cutoff
            ]
            if published and published[-1]["status"] == "Active":
                chosen.append(published[-1])
        out[day] = shortfall_by_unit_day(chosen).get(day, 0.0)
    return out


# --------------------------------------------------------------------------
# features and models
# --------------------------------------------------------------------------


def national_value(
    obs, fc, d: dt.date, t: dt.date, perfect: bool, cities=("paris", "lyon", "toulouse")
):
    values = []
    for city in cities:
        if perfect or t <= d:
            v = obs[city].get(t.isoformat())
        else:
            lead = (t - d).days
            v = fc[city].get(str(lead), {}).get(t.isoformat()) if lead <= 7 else None
        if v is None:
            return None
        values.append(v)
    return statistics.fmean(values)


def features(obs, fc, d: dt.date, h: int, perfect: bool):
    target = d + dt.timedelta(days=h)

    def mean_ending(end: dt.date, cities):
        vals = [
            national_value(obs, fc, d, end - dt.timedelta(days=i), perfect, cities)
            for i in range(7)
        ]
        return None if any(v is None for v in vals) else float(np.mean(vals))

    nat, lyon = mean_ending(target, ("paris", "lyon", "toulouse")), mean_ending(target, ("lyon",))
    before = mean_ending(target - dt.timedelta(days=3), ("paris", "lyon", "toulouse"))
    if None in (nat, lyon, before):
        return None
    return [nat, lyon, nat - before]


def design(raw: np.ndarray, columns: str) -> np.ndarray:
    nat, lyon, change = raw[:, 0], raw[:, 1], raw[:, 2]
    if columns == "full":
        return np.column_stack([nat, lyon, change, nat**2, lyon**2])
    return np.column_stack([nat, nat**2])  # G and B use the national temperature only


def ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y, rcond=None)[0]


def ols_predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ beta


def within(x: np.ndarray, groups: np.ndarray) -> np.ndarray:
    out = x.astype(float).copy()
    for g in np.unique(groups):
        mask = groups == g
        out[mask] -= out[mask].mean(axis=0)
    return out


def fe_ols(rows: list[dict], names: list[str]) -> dict[str, tuple[float, float, float]]:
    y = np.array([r["price"] for r in rows])
    x = np.column_stack([[r[n] for r in rows] for n in names]).astype(float)
    groups, seasons = np.array([r["fe"] for r in rows]), np.array([r["year"] for r in rows])
    yw, xw = within(y, groups), within(x, groups)
    inv = np.linalg.inv(xw.T @ xw)
    beta = inv @ xw.T @ yw
    scores = xw * (yw - xw @ beta)[:, None]
    meat = np.zeros((x.shape[1], x.shape[1]))
    for season in np.unique(seasons):
        s = scores[seasons == season]
        meat += s.T @ s
        for lag in range(1, NW_LAGS + 1):
            g = s[lag:].T @ s[:-lag]
            meat += (1 - lag / (NW_LAGS + 1)) * (g + g.T)
    se = np.sqrt(np.diag(inv @ meat @ inv))
    return {
        n: (float(b), float(b - 1.6449 * s), float(b + 1.6449 * s))
        for n, b, s in zip(names, beta, se, strict=True)
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cache = pathlib.Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else None
    obs = cached(cache, "obs_cities.json.gz", load_observed)
    fc = cached(cache, "fc_cities.json.gz", load_forecasts)
    records = cached(cache, "events_versions.json.gz", load_events_all_versions)
    realised = realised_loss(records)
    all_days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
    known = known_loss(records, [d for d in all_days if in_summer(d)])
    print(
        f"REMIT records: {len(records)}; summer days with a realised loss > 0: {sum(1 for d, v in realised.items() if in_summer(d) and v > 0)}"
    )
    print(
        "realised vs known-at-auction loss, mean GW per summer: "
        + ", ".join(
            f"{y}: {np.mean([realised.get(d, 0) for d in all_days if d.year == y and in_summer(d)]):.2f}/{np.mean([known[d] for d in known if d.year == y]):.2f}"
            for y in ALL_YEARS
        )
    )

    rng = np.random.default_rng(SEED)
    predictions: dict[int, dict[dt.date, float]] = {}
    verdicts = {}
    for h in LEADS:
        rows = []
        for d in all_days:
            target = d + dt.timedelta(days=h)
            if d.year not in ALL_YEARS or target.year != d.year or not in_summer(target):
                continue
            perfect = features(obs, fc, d, h, True)
            real = features(obs, fc, d, h, False) if d.year in TEST_SEASONS else None
            if perfect is None:
                continue
            observed_issue = national_value(obs, fc, d, d, True)
            rows.append(
                {
                    "d": d,
                    "t": target,
                    "year": d.year,
                    "perfect": perfect,
                    "real": real,
                    "issue": observed_issue,
                    "y": realised.get(target, 0.0),
                }
            )
        store = {k: [] for k in ("model", "B", "G")}
        labels, seasons, gw_pred = [], [], {}
        per_season = {}
        for year in TEST_SEASONS:
            train = [r for r in rows if r["year"] != year]
            test = [r for r in rows if r["year"] == year and r["real"] is not None]
            if not test:
                continue
            ytr = np.sqrt([r["y"] for r in train])
            xtr_raw = np.array([r["perfect"] for r in train])
            mu, sd = (
                design(xtr_raw, "full").mean(axis=0),
                design(xtr_raw, "full").std(axis=0) + 1e-9,
            )
            beta = ols((design(xtr_raw, "full") - mu) / sd, ytr)
            xte_raw = np.array([r["real"] for r in test])
            pred_model = (
                np.maximum(ols_predict(beta, (design(xte_raw, "full") - mu) / sd), 0.0) ** 2
            )
            g_mu, g_sd = design(xtr_raw, "G").mean(axis=0), design(xtr_raw, "G").std(axis=0) + 1e-9
            beta_g = ols((design(xtr_raw, "G") - g_mu) / g_sd, ytr)
            pred_g = np.maximum(ols_predict(beta_g, (design(xte_raw, "G") - g_mu) / g_sd), 0.0) ** 2
            b_tr = np.array([[r["issue"], r["issue"] ** 2] for r in train])
            b_te = np.array([[r["issue"], r["issue"] ** 2] for r in test])
            bm, bs = b_tr.mean(axis=0), b_tr.std(axis=0) + 1e-9
            beta_b = ols((b_tr - bm) / bs, ytr)
            pred_b = np.maximum(ols_predict(beta_b, (b_te - bm) / bs), 0.0) ** 2
            y = np.array([r["y"] for r in test])
            store["model"].append(pred_model)
            store["B"].append(pred_b)
            store["G"].append(pred_g)
            labels.append(y)
            seasons.append(np.full(len(y), year))
            for r, p in zip(test, pred_model, strict=True):
                gw_pred[r["t"]] = float(p)
            per_season[year] = (
                auc(pred_model, (y > GW_EVENT).astype(float)),
                auc(pred_b, (y > GW_EVENT).astype(float)),
                auc(pred_g, (y > GW_EVENT).astype(float)),
                int((y > GW_EVENT).sum()),
                len(y),
            )
        predictions[h] = gw_pred
        y_all, season_all = np.concatenate(labels), np.concatenate(seasons)
        event = (y_all > GW_EVENT).astype(float)
        scores = {k: np.concatenate(v) for k, v in store.items()}
        print(
            f"\nT1 LEAD {h} DAYS - national model, leave-one-season-out {TEST_SEASONS.start}-{TEST_SEASONS.stop - 1}"
        )
        print(f"  {'season':6s} {'days >1GW':>9s} {'AUC model':>10s} {'AUC B':>7s} {'AUC G':>7s}")
        for year, (a_m, a_b, a_g, n_ev, n) in per_season.items():
            fmt = lambda v: f"{v:7.3f}" if v == v else "    n/a"  # noqa: E731
            print(f"  {year:<6d} {n_ev:>5d}/{n:<3d} {fmt(a_m):>10s} {fmt(a_b)} {fmt(a_g)}")
        diffs_b, diffs_g, own = [], [], []
        for _ in range(N_BOOTSTRAP):
            parts = []
            for year in per_season:
                where = np.flatnonzero(season_all == year)
                n = where.size
                starts = rng.integers(
                    0, max(n - BLOCK_DAYS + 1, 1), size=int(np.ceil(n / BLOCK_DAYS))
                )
                local = (starts[:, None] + np.arange(BLOCK_DAYS)[None, :]).reshape(-1)[:n]
                parts.append(where[np.minimum(local, n - 1)])
            idx = np.concatenate(parts)
            if event[idx].min() == event[idx].max():
                continue
            a_m = auc(scores["model"][idx], event[idx])
            diffs_b.append(a_m - auc(scores["B"][idx], event[idx]))
            diffs_g.append(a_m - auc(scores["G"][idx], event[idx]))
            own.append(a_m)
        pooled = {k: auc(v, event) for k, v in scores.items()}
        lo_b, hi_b = np.quantile(diffs_b, [0.05, 0.95])
        lo_g, hi_g = np.quantile(diffs_g, [0.05, 0.95])
        own_lo = float(np.quantile(own, 0.05))
        rho = spearmanr(scores["model"], y_all).statistic
        print(
            f"  pooled AUC (>1 GW): model {pooled['model']:.3f}, B {pooled['B']:.3f}, G {pooled['G']:.3f}; Spearman(model, GW) {rho:.3f}"
        )
        print(
            f"  AUC(model) - AUC(B) = {pooled['model'] - pooled['B']:+.3f} [{lo_b:+.3f}, {hi_b:+.3f}]; own 5 % bound {own_lo:.3f}"
        )
        print(
            f"  AUC(model) - AUC(G) = {pooled['model'] - pooled['G']:+.3f} [{lo_g:+.3f}, {hi_g:+.3f}]  (G = forecast temperature alone)"
        )
        verdicts[h] = own_lo > 0.75 and lo_b > 0
    print(f"\nT1 VERDICT (lead 3): {'NATIONAL_SIGNAL' if verdicts[3] else 'NO_NATIONAL_SIGNAL'}")

    # ---- T2 --------------------------------------------------------------
    prices = cached(cache, "prices_entsoe.json.gz", load_prices)
    ec = (
        cached(cache, "../p2cache/prices_fr.json.gz", dict)
        if cache is not None and (cache.parent / "p2cache" / "prices_fr.json.gz").is_file()
        else {}
    )
    if ec:
        common = [d for d in prices if d in ec and d != "__license__"]
        diffs = [abs(prices[d] - ec[d]) for d in common]
        print(
            f"\nprice cross-check ENTSO-E vs Energy-Charts on {len(common)} common days: median |difference| {statistics.median(diffs):.2f} EUR/MWh, max {max(diffs):.2f}"
        )
    t_fc1 = {}
    for d in all_days:
        v = national_value(obs, fc, d - dt.timedelta(days=1), d, False)
        if v is not None:
            t_fc1[d] = v
    for h in LEADS:
        rows = []
        for iso, price in sorted(prices.items()):
            day = dt.date.fromisoformat(iso)
            if (
                day.year not in TEST_SEASONS
                or not in_summer(day)
                or day not in predictions[h]
                or day not in t_fc1
            ):
                continue
            rows.append(
                {
                    "year": day.year,
                    "fe": day.year * 100 + day.month,
                    "price": price,
                    "known": known.get(day, 0.0),
                    "pred": predictions[h][day],
                    "tfc": t_fc1[day],
                    "tfc2": t_fc1[day] ** 2,
                    "weekend": float(day.weekday() >= 5),
                }
            )
        names = ["known", "pred", "tfc", "tfc2", "weekend"]
        fit = fe_ols(rows, names)
        print(
            f"\nT2 LEAD {h} DAYS - price(D) on announced loss and on the loss predicted {h} days earlier (n = {len(rows)})"
        )
        for n in ("known", "pred"):
            b, lo, hi = fit[n]
            print(f"  {n:6s} {b:+7.2f} EUR/MWh per GW  90% interval [{lo:+.2f}, {hi:+.2f}]")
        b, lo, hi = fit["pred"]
        reading = (
            "ANTICIPATED: the price already reacts to the predictable loss"
            if (lo > 0 and b >= 1.0)
            else "NOT anticipated in the day-ahead price (necessary for an edge; proof needs forward prices)"
        )
        print(f"  -> {reading}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
