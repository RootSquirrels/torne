"""ATMO-002 - statistical validation of the ATMO-001 GHCN-Daily findings.

Re-derives, on real GHCN-Daily data, the quantities ATMO-001 reported, and
stress-tests them. It publishes no knowledge product and draws no climatic
conclusion: it audits estimators.

Protocol (fixed before the results were inspected)
---------------------------------------------------

Series
    Mean daily temperature (TMAX+TMIN)/2 anomalies against the 1991-2020
    day-of-year climatology, on the local civil day (Europe/Paris), as in
    ATMO-001. Hypothesis tests use anomalies standardized by their
    month-of-year standard deviation (station-specific), because the variance
    of daily anomalies is seasonal.

A. Effective sample size
    Same series, several estimators: the repository's Geyer rule on the
    gap-collapsed series (the ATMO-001 number), a gap-aware pairwise ACF with
    Geyer and Bartlett-taper truncation over a lag grid, and an independent
    batch-means estimator.

B. Persistence beyond daily inertia
    H0: the autocorrelation function is the one of an AR(1) process,
    rho_k = phi ** k. Statistic: E = sum_{k=2..K} (rho_k - phi ** k), K = 10
    (sensitivity K = 30). One-sided p-value from a parametric AR(1) null with
    bootstrapped innovations and the real missingness mask.

C. Cold versus warm regimes
    Regime is defined by the previous day's standardized anomaly: cold
    z <= -1, warm z >= +1 (fixed a priori, not tuned). Statistic: difference
    of the OLS lag-1 slopes (warm - cold). Moving-block bootstrap (blocks of
    30 and 90 days). Bonferroni across the four stations.

D. CUSUM reassessment
    The ATMO-001 statistic, its sensitivity to the long-run-variance lag, and
    a circular block bootstrap null (constant mean, dependence preserved up
    to the block length), with and without a linear trend removed.

E. Spatial consistency
    Common-window correlations, raw versus anomaly, by season.

Usage:

    uv run python experiments/atmo_002_validation.py
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atmo_001_premiere_acquisition import (
    ELEMENTS,
    PERIODE_REFERENCE,
    STATIONS,
    ZONE,
    _acquer,
    _fetcher,
    _lignes,
)

from torne.acquisition.adapters.ghcnd import GhcndDailyAdapter
from torne.acquisition.store import FileRawStore
from torne.atmosphere import (
    anomalies,
    climatologie,
    jour_civil,
    observations,
    structure_temporelle,
    temperature_moyenne,
)
from torne.methods.breaks import cusum_break_test
from torne.methods.multiplicity import bonferroni

SEED = 20261101
N_SIM = 499


# --------------------------------------------------------------------------
# series construction
# --------------------------------------------------------------------------


def day_axis(pairs: list[tuple[date, float]]) -> tuple[np.ndarray, date]:
    """Place (civil day, value) pairs on a regular daily axis; absent days are NaN."""
    pairs = sorted(pairs)
    first = pairs[0][0].toordinal()
    last = pairs[-1][0].toordinal()
    axis = np.full(last - first + 1, np.nan)
    for day, value in pairs:
        axis[day.toordinal() - first] = value
    return axis, pairs[0][0]


def standardize_by_month(axis: np.ndarray, start: date) -> np.ndarray:
    """Divide by the station's month-of-year standard deviation."""
    months = np.array([date.fromordinal(start.toordinal() + i).month for i in range(axis.size)])
    out = axis.copy()
    for month in range(1, 13):
        sel = (months == month) & np.isfinite(axis)
        sd = float(np.std(axis[sel], ddof=1))
        out[months == month] = axis[months == month] / sd
    return out


# --------------------------------------------------------------------------
# A. effective sample size
# --------------------------------------------------------------------------


def acf_pairwise(x: np.ndarray, max_lag: int) -> np.ndarray:
    """Autocorrelation with pairwise-complete lags on a gapped daily axis."""
    present = np.isfinite(x)
    z = np.where(present, x - np.nanmean(x), 0.0)
    w = present.astype(float)
    c0 = float(z @ z) / float(w.sum())
    rho = np.empty(max_lag + 1)
    rho[0] = 1.0
    for k in range(1, max_lag + 1):
        count = float(w[k:] @ w[:-k])
        rho[k] = (float(z[k:] @ z[:-k]) / count) / c0 if count > 0 else np.nan
    return rho


def n_eff_geyer(rho: np.ndarray, n: int, max_lag: int) -> tuple[float, int]:
    """Geyer initial positive sequence on a precomputed ACF."""
    total, lag = 0.0, 0
    k = 0
    while 2 * k + 1 <= max_lag:
        pair = rho[2 * k] + rho[2 * k + 1]
        if pair <= 0:
            break
        total += pair
        lag = 2 * k + 1
        k += 1
    tau = max(2.0 * total - 1.0, 1.0)
    return min(float(n), n / tau), lag


def n_eff_bartlett(rho: np.ndarray, n: int, m: int) -> float:
    k = np.arange(1, m + 1)
    tau = 1.0 + 2.0 * float(np.sum((1.0 - k / (m + 1.0)) * rho[1 : m + 1]))
    return min(float(n), n / max(tau, 1.0))


def n_eff_batch_means(x: np.ndarray, batch: int) -> float:
    """Independent estimator: n * var(x) / (b * var(batch means))."""
    n_batches = x.size // batch
    means = []
    for i in range(n_batches):
        chunk = x[i * batch : (i + 1) * batch]
        if np.isfinite(chunk).mean() >= 0.8:
            means.append(np.nanmean(chunk))
    means_arr = np.asarray(means)
    n = int(np.isfinite(x).sum())
    sigma_lr2 = batch * float(np.var(means_arr, ddof=1))
    return min(float(n), n * float(np.nanvar(x, ddof=1)) / sigma_lr2)


# --------------------------------------------------------------------------
# B. persistence beyond AR(1)
# --------------------------------------------------------------------------


def excess_statistic(x: np.ndarray, k_max: int) -> tuple[float, float]:
    rho = acf_pairwise(x, k_max)
    phi = float(rho[1])
    excess = float(sum(rho[k] - phi**k for k in range(2, k_max + 1)))
    return excess, phi


def persistence_test(x: np.ndarray, k_max: int, rng: np.random.Generator) -> dict:
    observed, phi = excess_statistic(x, k_max)
    present = np.isfinite(x)
    pairs = present[1:] & present[:-1]
    innov = (x[1:] - phi * x[:-1])[pairs]
    innov = innov - innov.mean()
    simulated = np.empty(N_SIM)
    chunk = 100
    for lo in range(0, N_SIM, chunk):
        size = min(chunk, N_SIM - lo)
        e = rng.choice(innov, size=(x.size, size))
        paths = np.empty_like(e)
        paths[0] = e[0]
        for t in range(1, x.size):  # vectorized across simulations
            paths[t] = phi * paths[t - 1] + e[t]
        paths[~present] = np.nan
        for j in range(size):
            simulated[lo + j], _ = excess_statistic(paths[:, j], k_max)
    p = (1 + int(np.sum(simulated >= observed))) / (1 + N_SIM)
    return {
        "k_max": k_max,
        "phi": phi,
        "excess": observed,
        "null_mean": float(simulated.mean()),
        "null_q95": float(np.quantile(simulated, 0.95)),
        "p_one_sided": p,
    }


# --------------------------------------------------------------------------
# C. regimes
# --------------------------------------------------------------------------


def _slope(x: np.ndarray, y: np.ndarray, sel: np.ndarray) -> float:
    xs, ys = x[sel], y[sel]
    if xs.size < 30:
        return float("nan")
    xc = xs - xs.mean()
    return float(xc @ (ys - ys.mean()) / (xc @ xc))


def slope_difference(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, int, int]:
    ok = np.isfinite(x) & np.isfinite(y)
    cold = ok & (x <= -1.0)
    warm = ok & (x >= 1.0)
    s_cold, s_warm = _slope(x, y, cold), _slope(x, y, warm)
    return s_warm - s_cold, s_cold, s_warm, int(cold.sum()), int(warm.sum())


def regime_test(z: np.ndarray, block: int, rng: np.random.Generator) -> dict:
    x, y = z[:-1], z[1:]
    n = x.size
    diff, s_cold, s_warm, n_cold, n_warm = slope_difference(x, y)
    n_blocks = math.ceil(n / block)
    offsets = np.arange(block)
    reps = np.empty(N_SIM)
    for i in range(N_SIM):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        reps[i] = slope_difference(x[idx], y[idx])[0]
    reps = reps[np.isfinite(reps)]
    p = min(1.0, 2.0 * min(float(np.mean(reps <= 0)), float(np.mean(reps >= 0))))
    return {
        "block": block,
        "slope_cold": s_cold,
        "slope_warm": s_warm,
        "n_cold_pairs": n_cold,
        "n_warm_pairs": n_warm,
        "difference_warm_minus_cold": diff,
        "ci95": [float(np.quantile(reps, 0.025)), float(np.quantile(reps, 0.975))],
        "p_two_sided": max(p, 1.0 / (len(reps) + 1)),
    }


# --------------------------------------------------------------------------
# D. CUSUM
# --------------------------------------------------------------------------


def raw_cusum(x: np.ndarray) -> float:
    r = x - x.mean()
    return float(np.max(np.abs(np.cumsum(r)[:-1])) / math.sqrt(x.size))


def cusum_null(x: np.ndarray, block: int, rng: np.random.Generator) -> dict:
    """Circular block bootstrap of the centered series: constant mean, local dependence kept."""
    n = x.size
    centered = x - x.mean()
    n_blocks = math.ceil(n / block)
    offsets = np.arange(block)
    observed = raw_cusum(x)
    reps = np.empty(N_SIM)
    for i in range(N_SIM):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        reps[i] = raw_cusum(centered[idx])
    return {
        "block": block,
        "observed": observed,
        "null_q95": float(np.quantile(reps, 0.95)),
        "p": (1 + int(np.sum(reps >= observed))) / (1 + N_SIM),
    }


def detrend_axis(x: np.ndarray) -> np.ndarray:
    """Remove a linear trend from a gapped daily axis (fitted on present days only)."""
    t = np.arange(x.size, dtype=float)
    ok = np.isfinite(x)
    slope, intercept = np.polyfit(t[ok], x[ok], 1)
    return x - (slope * t + intercept)


def detrend(x: np.ndarray) -> np.ndarray:
    t = np.arange(x.size, dtype=float)
    slope, intercept = np.polyfit(t, x, 1)
    return x - (slope * t + intercept)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def build_station(fetcher, store, station_id: str, name: str) -> dict:
    adapter = GhcndDailyAdapter(station_id, elements=ELEMENTS, label=f"ghcnd:{station_id}")
    issue = _acquer(fetcher, adapter, f"{name} ({station_id})")
    lines = _lignes(issue, store, station_id)
    kwargs = {
        "source_id": adapter.source.source_id,
        "evidence_id": issue.evidence[0].evidence_id,
        "zone": ZONE,
        "acquired_at": issue.evidence[0].acquired_at,
    }
    tmax = observations(lines, "TMAX", **kwargs)
    tmin = observations(lines, "TMIN", **kwargs)
    mean = temperature_moyenne(tmax, tmin, zone=ZONE)
    reference = climatologie(
        mean,
        reference_start=PERIODE_REFERENCE[0],
        reference_end=PERIODE_REFERENCE[1],
        zone=ZONE,
    )
    notes = anomalies(mean, reference, zone=ZONE)
    anomaly_pairs = [
        (jour_civil(o.temporal.valid_time, ZONE), float(score))
        for o, score in notes
        if o.temporal.valid_time is not None
    ]
    raw_pairs = [
        (jour_civil(o.temporal.valid_time, ZONE), float(o.value))
        for o in mean
        if o.temporal.valid_time is not None and o.value is not None
    ]
    return {"notes": notes, "anomaly_pairs": anomaly_pairs, "raw_pairs": raw_pairs}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(tempfile.mkdtemp(prefix="torne-atmo-002-"))
    print(f"raw evidence: {root}")
    store = FileRawStore(root)
    fetcher = _fetcher(store)
    rng = np.random.default_rng(SEED)
    report: dict = {"at": datetime.now(UTC).isoformat(), "seed": SEED, "stations": {}}

    data = {}
    for station_id, name in STATIONS:
        data[station_id] = build_station(fetcher, store, station_id, name)

    persistence_p, regime_p = [], []
    for station_id, name in STATIONS:
        built = data[station_id]
        axis, start = day_axis(built["anomaly_pairs"])
        collapsed = np.array([s for _, s in sorted(built["anomaly_pairs"])])
        n = int(np.isfinite(axis).sum())
        z = standardize_by_month(axis, start)
        print(f"\n=== {name} ({station_id}) : {n} anomaly days over {axis.size} calendar days")
        entry: dict = {"n": n, "calendar_days": int(axis.size)}

        # A
        _, module_size = structure_temporelle(built["notes"], lags=10)
        rho = acf_pairwise(axis, 400)
        grid = {}
        for max_lag in (10, 20, 45, 90, 180, 365):
            eff, lag = n_eff_geyer(rho, n, max_lag)
            grid[f"geyer_maxlag_{max_lag}"] = {"n_eff": eff, "retained_lag": lag}
        for m in (14, 45, 90, 180, 365):
            grid[f"bartlett_taper_{m}"] = {"n_eff": n_eff_bartlett(rho, n, m)}
        for batch in (30, 90, 180, 365):
            grid[f"batch_means_{batch}"] = {"n_eff": n_eff_batch_means(axis, batch)}
        entry["n_eff"] = {
            "module_gap_collapsed": {
                "n_eff": module_size.n_eff,
                "retained_lag": module_size.truncation_lag,
            }
            if module_size
            else None,
            "gap_aware": grid,
            "rho_1_3_gap_aware": [float(r) for r in rho[1:4]],
            "rho_lags_14_45_90": [float(rho[14]), float(rho[45]), float(rho[90])],
        }
        print(
            f"A. module (gap-collapsed): n_eff={module_size.n_eff:.0f} "
            f"lag={module_size.truncation_lag}"
        )
        for key, value in grid.items():
            print(f"   {key:24s} n_eff={value['n_eff']:.0f}")

        # B
        entry["persistence"] = [persistence_test(z, k, rng) for k in (10, 30)]
        persistence_p.append(entry["persistence"][0]["p_one_sided"])
        for r in entry["persistence"]:
            print(
                f"B. K={r['k_max']}: phi={r['phi']:.3f} excess={r['excess']:.3f} "
                f"null95={r['null_q95']:.3f} p={r['p_one_sided']:.3f}"
            )

        zd = detrend_axis(z)
        entry["persistence_detrended"] = [persistence_test(zd, k, rng) for k in (10, 30)]
        for r in entry["persistence_detrended"]:
            print(
                f"B'. detrended K={r['k_max']}: phi={r['phi']:.3f} excess={r['excess']:.3f} "
                f"null95={r['null_q95']:.3f} p={r['p_one_sided']:.3f}"
            )
        entry["regimes_detrended"] = [regime_test(zd, 90, rng)]
        r = entry["regimes_detrended"][0]
        print(
            f"C'. detrended block=90: cold={r['slope_cold']:.3f} warm={r['slope_warm']:.3f} "
            f"diff={r['difference_warm_minus_cold']:.3f} "
            f"CI={r['ci95'][0]:.3f}..{r['ci95'][1]:.3f} p={r['p_two_sided']:.3f}"
        )

        # C
        entry["regimes"] = [regime_test(z, b, rng) for b in (30, 90)]
        regime_p.append(entry["regimes"][0]["p_two_sided"])
        for r in entry["regimes"]:
            print(
                f"C. block={r['block']}: slope cold={r['slope_cold']:.3f} "
                f"warm={r['slope_warm']:.3f} diff={r['difference_warm_minus_cold']:.3f} "
                f"CI={r['ci95'][0]:.3f}..{r['ci95'][1]:.3f} p={r['p_two_sided']:.3f}"
            )

        # D
        sorted_pairs = sorted(built["anomaly_pairs"])
        atmo1 = cusum_break_test(collapsed, lags=None)
        entry["cusum"] = {
            "atmo001_lags": atmo1.lags,
            "atmo001_p": atmo1.p_value,
            "break_date": sorted_pairs[atmo1.break_index][0].isoformat(),
            "mean_before": atmo1.mean_before,
            "mean_after": atmo1.mean_after,
            "bartlett_lags_sensitivity": {
                str(m): cusum_break_test(collapsed, lags=m).p_value for m in (14, 45, 90, 180, 365)
            },
            "block_null": [cusum_null(collapsed, b, rng) for b in (45, 90, 180)],
            "block_null_detrended": [cusum_null(detrend(collapsed), b, rng) for b in (90,)],
            "linear_trend_per_decade": float(np.polyfit(np.arange(collapsed.size), collapsed, 1)[0])
            * 3652.5,
        }
        print(
            f"D. ATMO-001 lags={atmo1.lags} p={atmo1.p_value:.2g} break={entry['cusum']['break_date']}"
        )
        print(f"   p by Bartlett lag: {entry['cusum']['bartlett_lags_sensitivity']}")
        for r in entry["cusum"]["block_null"]:
            print(
                f"   block null b={r['block']}: obs={r['observed']:.2f} q95={r['null_q95']:.2f} p={r['p']:.3f}"
            )
        r = entry["cusum"]["block_null_detrended"][0]
        print(f"   detrended b=90: obs={r['observed']:.2f} q95={r['null_q95']:.2f} p={r['p']:.3f}")
        print(f"   linear trend: {entry['cusum']['linear_trend_per_decade']:.3f} degC/decade")
        report["stations"][station_id] = {"name": name, **entry}

    family_a = bonferroni(persistence_p)
    family_b = bonferroni(regime_p)
    report["multiplicity"] = {
        "persistence_bonferroni_adjusted": list(family_a.adjusted_p_values),
        "regime_bonferroni_adjusted": list(family_b.adjusted_p_values),
    }
    print("\nBonferroni persistence:", [round(p, 3) for p in family_a.adjusted_p_values])
    print("Bonferroni regime:     ", [round(p, 3) for p in family_b.adjusted_p_values])

    # E. spatial consistency on the common window
    print("\nE. spatial consistency (common window)")
    axes = {}
    for station_id, _ in STATIONS:
        a, start = day_axis(data[station_id]["anomaly_pairs"])
        r, start_r = day_axis(data[station_id]["raw_pairs"])
        axes[station_id] = (a, start, r, start_r)
    first = max(v[1].toordinal() for v in axes.values())
    last = min(v[1].toordinal() + v[0].size - 1 for v in axes.values())

    def window(station_id: str, which: int) -> np.ndarray:
        arr, start = (
            (axes[station_id][0], axes[station_id][1])
            if which == 0
            else (
                axes[station_id][2],
                axes[station_id][3],
            )
        )
        lo = first - start.toordinal()
        return arr[lo : lo + (last - first + 1)]

    ids = [s for s, _ in STATIONS]
    months = np.array([date.fromordinal(first + i).month for i in range(last - first + 1)])
    seasons = {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11)}
    spatial = {}
    for i, a_id in enumerate(ids):
        for b_id in ids[i + 1 :]:
            row = {}
            for label, which in (("raw", 1), ("anomaly", 0)):
                x, y = window(a_id, which), window(b_id, which)
                ok = np.isfinite(x) & np.isfinite(y)
                row[label] = float(np.corrcoef(x[ok], y[ok])[0, 1])
                row[f"{label}_days"] = int(ok.sum())
            x, y = window(a_id, 0), window(b_id, 0)
            for season, ms in seasons.items():
                ok = np.isfinite(x) & np.isfinite(y) & np.isin(months, ms)
                row[f"anomaly_{season}"] = float(np.corrcoef(x[ok], y[ok])[0, 1])
            spatial[f"{a_id}|{b_id}"] = row
            print(
                f"  {a_id}|{b_id}: raw={row['raw']:.3f} anomaly={row['anomaly']:.3f} "
                + " ".join(f"{s}={row[f'anomaly_{s}']:.2f}" for s in seasons)
            )
    report["spatial"] = {
        "window": [date.fromordinal(first).isoformat(), date.fromordinal(last).isoformat()],
        "pairs": spatial,
    }
    print(f"  window: {report['spatial']['window']}")

    out = root / "report_atmo_002.json"
    out.write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    print(f"\nreport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
