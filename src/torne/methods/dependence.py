"""Inference that is robust to dependence between observations.

Purpose
-------
A series of measurements is rarely a set of independent experiments. A river gauge
sampled every hour, a station repeated over days, three basins measured a hundred
thousand times each: the nominal sample size badly overstates the amount of
information actually carried. This module provides the four tools that make the
dependence explicit instead of assuming it away.

- `effective_sample_size` : how many of the `n` observations are effectively
  independent, read from the autocorrelation function with Geyer's initial
  positive sequence rule;
- `block_bootstrap` : a circular (moving) block bootstrap, the resampling
  scheme that keeps the local dependence of a stationary series intact;
- `cluster_bootstrap` : the pairs cluster bootstrap, where a whole cluster
  travels together and the independent unit is the cluster;
- `independent_unit_sensitivity` : the same statistic computed under several
  competing definitions of the independent unit (station, basin, day, season),
  which is the practical guard against the trap of mistaking many measurements
  for many independent experiments.

Methods
-------
**Effective sample size.** The sample autocorrelations `rho_1, rho_2, ...` are
formed with the biased (Fisher-Pearson) estimator, and the sum that defines the
integrated autocorrelation time is truncated by Geyer's initial positive
sequence rule: the lag pairs `(rho_0, rho_1), (rho_2, rho_3), ...` are summed
until the first pair whose sum is non-positive. The retained lag `L` gives
`n_eff = n / (1 + 2 * sum_{lag=1..L} rho_lag)`, clipped to `(1, n]`. The default
`max_lag` is `ceil(10 * log10(n))`, capped at `n - 1`.

**Observations with gaps.** `sample_autocorrelation` takes the integer
positions of the observations on a regular grid. Lag `k` pairs two observations
whose positions differ by exactly `k`; a missing position is absent from the
pairs and is never closed up, and a lag without enough pairs is reported as
unobservable (`NaN`). `effective_sample_size_diagnostics` builds on it and
reports what ended the sum (the positivity rule, the lag cap, or an
unobservable lag) together with the figure at several caps: a figure whose sum
was ended by the cap is a function of the cap, and says so. Nothing here knows
what a position means (a day, an orbit, a sample): that, and the choice of the
cap, belong to the caller.

**Circular block bootstrap.** Blocks of `block_length` consecutive observations
are drawn with replacement from the series, wrapping around its end, until a
series of length `n` is rebuilt; the statistic is recomputed on each resample.
The standard error is the sample standard deviation of the bootstrap replicates
and the confidence interval is the **percentile** interval.

Default block length: the automatic rule of Politis & White (2004) for the
circular bootstrap, computed exactly as in the reference implementation of
Patton, Politis & White: the lag `mhat` is the smallest lag beyond which `Kn`
consecutive autocorrelations are all insignificant, `M = min(2 * mhat, mmax)`,
the flat-top lag window of Politis & Romano (1995) is applied to the
autocovariances, and

    b_star = (2 * Ghat^2 / DCBhat) ** (1/3) * n ** (1/3)

with `Ghat = sum_k lam(k/M) * |k| * R(k)` and
`DCBhat = (4/3) * (sum_k lam(k/M) * R(k))^2`. The block length is
`ceil(b_star)`, capped at `ceil(min(3 * sqrt(n), n / 3))`. When the rule is
undefined (constant series, null spectral density) the fallback is
`ceil(n ** (1/3))`, the classical rule of thumb for the circular block
bootstrap. For independent data the rule selects a block length of one, that
is, the ordinary bootstrap, which is the statistically correct answer.

**Cluster bootstrap.** The clusters are drawn with replacement; the observations
of a drawn cluster travel together, and the resampled series is the
concatenation of the drawn clusters, in cluster order. The statistic therefore
sees a series of the same length `n` when the clusters are balanced (the
design the module targets); with unbalanced clusters the length of a resample
varies with the clusters drawn, and the statistic is applied to the resample as
it comes.

**Independent unit sensitivity.** For a given labelling, the independent unit
is the cluster. Each cluster is reduced to its mean, giving the *unit-level
series*, and the statistic is applied to that series: the estimate is then the
one implied by that definition of the unit (with the mean statistic, the
unweighted mean over units). The uncertainty is obtained by the cluster
bootstrap applied to the unit-level series. Two labellings therefore answer two
genuinely different questions, and the spread between them measures how much
the conclusion depends on the definition of the independent unit.

Conventions
-----------
- Every error message is written in English: the module cites the international
  statistical literature, and the prose follows the sources it cites.
- The global random state is never touched. Every stochastic function takes an
  explicit `seed` keyword argument and builds its own generator
  (`np.random.default_rng(seed)`); a fixed seed gives a fixed result
  (`docs/CONTRACTS_FONDAMENTAUX.md`, INV-35 and INV-36).
- An invalid input (empty series, wrong length, non-finite value, parameter out
  of domain) raises `ValueError` with an explicit message; nothing is silently
  coerced or substituted.

Dependencies
------------
`numpy` and `scipy` (runtime dependencies of the package).

References
----------
- Geyer, C. J. (1992), "On the Estimation of Autocorrelation Functions",
  *Biometrika* 79(3), 527-530.
- Künsch, H. R. (1989), "The Jackknife and the Bootstrap for General Stationary
  Observations", *Annals of Statistics* 17(3), 1217-1241.
- Politis, D. N. & White, H. (2004), "Automatic Block-Length Selection for the
  Dependent Bootstrap", *Econometric Reviews* 23(1), 53-70.
- Politis, D. N. & Romano, J. P. (1995), "Bias-Corrected Nonparametric Spectral
  Estimation", *Journal of Time Series Analysis* 16(1), 1-15.
- Carlstein, B. (1986), "The Bootstrap in Cluster Analysis", *Scandinavian
  Journal of Statistics* 13(4), 290-298.
- Field, C. A. & Welsh, A. H. (2007), "Bootstrapping Imperfect Data", *Journal
  of the Royal Statistical Society: Series B* 69(3), 369-390.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

# `ArrayLike` (input) comes from `numpy.typing`; the two aliases below are the
# concrete array types the module works with internally.
FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

Statistic = Callable[[FloatArray], float]

# Two-sided normal quantile used by the significance test of the
# Politis-White rule (qnorm(0.975)).
_Z_975 = 1.959963984540054


@dataclass(frozen=True, slots=True)
class EffectiveSampleSize:
    """Effective sample size of a stationary series, read from its autocorrelation.

    Attributes
    ----------
    n:
        Number of observations of the series.
    n_eff:
        Effective sample size, in `(1, n]`.
    ratio:
        `n_eff / n`, in `(0, 1]`: the share of the observations that are
        effectively independent.
    truncation_lag:
        Largest lag retained in the autocorrelation sum. It is `0` when no lag
        is retained (constant series, or `max_lag = 0`).
    """

    n: int
    n_eff: float
    ratio: float
    truncation_lag: int


_GEYER_ESTIMATOR = "geyer_initial_positive_sequence"
_STOP_POSITIVITY = "positivity_rule"
_STOP_LAG_CAP = "lag_cap"
_STOP_UNOBSERVABLE = "unobservable_lag"


@dataclass(frozen=True, slots=True)
class Autocorrelation:
    """Sample autocorrelation at explicit lags, with the pairs that support each lag.

    Attributes
    ----------
    lags:
        The lags `0..L`, where `L` is the requested maximum capped at the span
        of the observation positions.
    rho:
        Autocorrelation per lag; `rho[0] == 1`. `NaN` marks an **unobservable**
        lag: fewer than `min_pairs` pairs of observations are separated by it.
    pair_counts:
        Number of observation pairs separated by exactly each lag
        (`pair_counts[0]` is the number of observations).
    normalization, min_pairs:
        The estimator variant and the observability threshold that were used.
    """

    lags: IntArray
    rho: FloatArray
    pair_counts: IntArray
    normalization: str
    min_pairs: int


@dataclass(frozen=True, slots=True)
class CapSensitivity:
    """The effective sample size recomputed at one lag cap."""

    max_lag: int
    n_eff: float
    truncation_lag: int
    stopped_by: str


@dataclass(frozen=True, slots=True)
class EffectiveSampleSizeDiagnostics:
    """An effective sample size, with what produced it.

    Attributes
    ----------
    n, n_eff, ratio:
        As in `EffectiveSampleSize`.
    estimator:
        The estimator's name (`geyer_initial_positive_sequence`).
    normalization, min_pairs:
        The autocorrelation variant and observability threshold used.
    max_lag:
        The cap that was applied to the headline figure.
    truncation_lag:
        The largest lag retained in the sum.
    stopped_by:
        What ended the sum: `positivity_rule` (the data), `lag_cap` (the cap),
        or `unobservable_lag` (gaps left a lag without enough pairs). Only the
        first is a statement about the series; with `lag_cap`, `n_eff` is a
        function of the cap, and `cap_bound` is true.
    sensitivity:
        The figure at several caps, ascending.
    """

    n: int
    n_eff: float
    ratio: float
    estimator: str
    normalization: str
    min_pairs: int
    max_lag: int
    truncation_lag: int
    stopped_by: str
    sensitivity: tuple[CapSensitivity, ...]

    @property
    def cap_bound(self) -> bool:
        """True when the cap, not the data, ended the sum."""
        return self.stopped_by == _STOP_LAG_CAP


@dataclass(frozen=True, slots=True)
class BootstrapReport:
    """Result of a bootstrap resampling.

    Attributes
    ----------
    point_estimate:
        Value of the statistic on the original series.
    standard_error:
        Sample standard deviation of the bootstrap replicates (`ddof=1`).
    ci_lower, ci_upper:
        Bounds of the **percentile** confidence interval at level `1 - alpha`.
    n_bootstrap:
        Number of bootstrap replicates.
    block_length:
        Length of the resampling unit: the number of observations per block for
        the circular block bootstrap, the number of independent units
        (clusters) resampled per replicate for the cluster bootstrap.
    alpha:
        Significance level of the confidence interval.
    """

    point_estimate: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int
    block_length: int
    alpha: float


@dataclass(frozen=True, slots=True)
class SensitivityReport:
    """Result of a sensitivity analysis over several definitions of the unit.

    Attributes
    ----------
    point_estimates:
        Pairs `(label, value)` sorted by label: the estimate of the statistic
        under each definition of the independent unit.
    spread:
        `max(point_estimates) - min(point_estimates)`: how much the estimate
        moves when the definition of the independent unit changes.
    per_label_reports:
        Pairs `(label, report)` sorted by label: the bootstrap report attached
        to each definition of the independent unit.
    """

    point_estimates: tuple[tuple[str, float], ...]
    spread: float
    per_label_reports: tuple[tuple[str, BootstrapReport], ...]


def _as_series(values: ArrayLike, name: str = "x") -> FloatArray:
    """Validate a series and return it as a 1-D float64 array."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a 1-D array (got shape {array.shape})")
    if array.size == 0:
        raise ValueError(f"{name} must be a non-empty array")
    if not bool(np.isfinite(array).all()):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _as_labels(clusters: IntArray, n: int) -> IntArray:
    """Validate cluster labels and return them as a contiguous 0-based int64 array."""
    labels = np.asarray(clusters)
    if labels.ndim != 1:
        raise ValueError(f"cluster labels must be a 1-D array (got shape {labels.shape})")
    if labels.size != n:
        raise ValueError(f"cluster labels must have the same length as x ({n}); got {labels.size}")
    if not np.issubdtype(labels.dtype, np.integer):
        raise ValueError(f"cluster labels must be integers (got dtype {labels.dtype})")
    labels = labels.astype(np.int64, copy=False)
    unique = np.unique(labels)
    if unique.size == 0:
        raise ValueError("cluster labels must not be empty")
    if unique[0] != 0 or not np.array_equal(unique, np.arange(unique.size, dtype=np.int64)):
        raise ValueError(
            f"cluster labels must be contiguous integers starting at 0; got {unique.tolist()}"
        )
    return labels


def _check_bootstrap_parameters(n_bootstrap: int, alpha: float) -> None:
    """Validate the parameters shared by the two bootstraps."""
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, (int, np.integer)):
        raise ValueError(f"n_bootstrap must be an integer (got {n_bootstrap!r})")
    if n_bootstrap < 2:
        raise ValueError(f"n_bootstrap must be >= 2 (got {n_bootstrap})")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1) (got {alpha})")


def _evaluate_statistic(statistic: Statistic, sample: FloatArray) -> float:
    """Apply the statistic to a sample and check that it returns a finite float."""
    if not callable(statistic):
        raise TypeError("statistic must be callable")
    value = np.asarray(statistic(sample), dtype=np.float64)
    if value.ndim != 0:
        raise ValueError("statistic must return a single float")
    scalar = float(value)
    if not math.isfinite(scalar):
        raise ValueError("statistic returned a non-finite value")
    return scalar


def _autocorrelations(centered: FloatArray, max_lag: int) -> FloatArray:
    """Sample autocorrelations at lags `0..max_lag` (biased estimator).

    The denominator is the same for every lag, which keeps the estimate inside
    `[-1, 1]` and makes the autocovariances `R(k) = rho_k * gamma_0` consistent
    with the autocorrelations.
    """
    denominator = float(centered @ centered)
    rhos = np.zeros(max_lag + 1, dtype=np.float64)
    rhos[0] = 1.0
    if denominator <= 0.0:
        # Constant series: the autocorrelation is not defined, no lag is kept.
        return rhos
    for lag in range(1, max_lag + 1):
        rhos[lag] = float(centered[lag:] @ centered[:-lag]) / denominator
    return rhos


def _flat_top_window(m: int) -> FloatArray:
    """Flat-top lag window of Politis & Romano (1995) on the lags `-m..m`."""
    absolute = np.arange(-m, m + 1, dtype=np.float64)
    scaled = np.abs(absolute) / m
    return np.where(scaled < 0.5, 1.0, np.where(scaled <= 1.0, 2.0 * (1.0 - scaled), 0.0))


def _politis_white_block_length(series: FloatArray) -> int:
    """Automatic block length for the circular block bootstrap.

    Implements the rule of Politis & White (2004) as distributed in the
    reference implementation of Patton, Politis & White: the lag `mhat` beyond
    which `Kn` consecutive autocorrelations are all insignificant, the flat-top
    window of Politis & Romano (1995), and the cube-root formula of the paper.
    The fallback `ceil(n ** (1/3))` applies when the rule is undefined.
    """
    n = int(series.size)
    fallback = max(1, math.ceil(n ** (1.0 / 3.0)))
    if n < 8:
        return fallback
    kn = max(5, math.ceil(math.log10(n)))
    mmax = min(math.ceil(math.sqrt(n)) + kn, n - 1)
    centered = series - series.mean()
    variance_sum = float(centered @ centered)
    if variance_sum <= 0.0:
        return fallback
    rhos = _autocorrelations(centered, mmax)
    criterion = _Z_975 * math.sqrt(math.log10(n) / n)
    insignificant = np.abs(rhos[1:]) <= criterion
    mhat = 0
    for start in range(max(0, mmax - kn + 1)):
        if bool(insignificant[start : start + kn].all()):
            mhat = start + 1
            break
    if mhat == 0:
        significant = np.flatnonzero(np.abs(rhos[1:]) > criterion) + 1
        if significant.size == 0:
            mhat = 1
        elif significant.size == 1:
            mhat = int(significant[0])
        else:
            mhat = int(significant.max())
    m = min(2 * mhat, mmax)
    autocovariances = rhos * (variance_sum / n)
    window = _flat_top_window(m)
    symmetric = np.concatenate([autocovariances[m:0:-1], autocovariances[: m + 1]])
    g_hat = float(np.sum(window * np.abs(np.arange(-m, m + 1)) * symmetric))
    d_cb = (4.0 / 3.0) * float(np.sum(window * symmetric)) ** 2
    if d_cb <= 0.0 or not math.isfinite(d_cb) or g_hat == 0.0:
        return fallback
    b_star = (2.0 * g_hat**2 / d_cb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    if not math.isfinite(b_star) or b_star <= 0.0:
        return fallback
    b_max = math.ceil(min(3.0 * math.sqrt(n), n / 3.0))
    return int(max(1, min(math.ceil(b_star), b_max)))


def _percentile_interval(values: FloatArray, alpha: float) -> tuple[float, float]:
    """Percentile confidence interval of the bootstrap replicates."""
    lower, upper = np.quantile(values, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lower), float(upper)


def effective_sample_size(x: ArrayLike, *, max_lag: int | None = None) -> EffectiveSampleSize:
    """Effective sample size of a stationary series, from its autocorrelation.

    The autocorrelations are summed with Geyer's initial positive sequence
    rule: the lag pairs `(rho_0, rho_1), (rho_2, rho_3), ...` are accumulated
    until the first pair whose sum is non-positive. The retained lag `L` gives
    `n_eff = n / (1 + 2 * sum_{lag=1..L} rho_lag)`, clipped to `(1, n]`.

    A constant series carries no dependence information: no lag is retained and
    `n_eff` falls back to `n`.

    Parameters
    ----------
    x:
        Non-empty 1-D series of finite observations.
    max_lag:
        Largest lag used in the autocorrelation sum. `None` (default) means
        `ceil(10 * log10(n))`. The value is capped at `n - 1`, the largest lag
        the series can support.

    Returns
    -------
    EffectiveSampleSize
    """
    if max_lag is not None:
        if isinstance(max_lag, bool) or not isinstance(max_lag, (int, np.integer)):
            raise ValueError(f"max_lag must be an integer (got {max_lag!r})")
        if max_lag < 0:
            raise ValueError(f"max_lag must be >= 0 (got {max_lag})")
    series = _as_series(x)
    n = int(series.size)
    if max_lag is None:
        lag_limit = 0 if n <= 1 else min(n - 1, math.ceil(10.0 * math.log10(n)))
    else:
        lag_limit = min(int(max_lag), n - 1)
    centered = series - series.mean()
    rhos = _autocorrelations(centered, lag_limit)
    retained, truncation_lag, _ = _geyer_sum(rhos, lag_limit)
    n_eff = _n_eff_from_sum(n, retained)
    return EffectiveSampleSize(
        n=n,
        n_eff=n_eff,
        ratio=n_eff / n,
        truncation_lag=truncation_lag,
    )


def _geyer_sum(rhos: FloatArray, lag_limit: int) -> tuple[float, int, str]:
    """Geyer's initial positive sequence: `(retained sum, truncation lag, stop reason)`.

    The stop reason says what ended the sum: `"positivity_rule"` (a lag pair
    summed to a non-positive value: the data decided), `"lag_cap"` (the cap was
    reached while the pairs were still positive: **the cap decided**), or
    `"unobservable_lag"` (a lag of the pair had too few observed pairs to be
    estimated).
    """
    retained = 0.0
    truncation_lag = 0
    pair_index = 0
    stopped_by = _STOP_LAG_CAP
    while 2 * pair_index + 1 <= lag_limit:
        first, second = rhos[2 * pair_index], rhos[2 * pair_index + 1]
        if not (math.isfinite(first) and math.isfinite(second)):
            stopped_by = _STOP_UNOBSERVABLE
            break
        pair = float(first + second)
        if pair <= 0.0:
            stopped_by = _STOP_POSITIVITY
            break
        retained += pair
        truncation_lag = 2 * pair_index + 1
        pair_index += 1
    return retained, truncation_lag, stopped_by


def _n_eff_from_sum(n: int, retained: float) -> float:
    """Effective sample size from the retained sum (which includes `rho_0 = 1`)."""
    # `retained` sums rho_0 (= 1) and the retained lags: the integrated
    # autocorrelation time is 1 + 2 * sum_{lag=1..L} rho_lag.
    integrated_time = 2.0 * retained - 1.0
    if not math.isfinite(integrated_time) or integrated_time <= 0.0:
        integrated_time = 1.0
    return min(float(n), max(1.0, n / integrated_time))


def _as_positions(positions: ArrayLike | None, n: int) -> IntArray:
    """Validate observation positions: strictly increasing integers, one per value."""
    if positions is None:
        return np.arange(n, dtype=np.int64)
    raw = np.asarray(positions)
    if raw.ndim != 1 or raw.size != n:
        raise ValueError(f"positions must be a 1-D array with one entry per value ({n})")
    if not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"positions must be integers on a regular grid (got dtype {raw.dtype})")
    grid = raw.astype(np.int64, copy=False)
    if n > 1 and not bool((np.diff(grid) > 0).all()):
        raise ValueError("positions must be strictly increasing")
    return grid


def _check_normalization(normalization: str, min_pairs: int) -> None:
    if normalization not in ("biased", "pairs"):
        raise ValueError(f"normalization must be 'biased' or 'pairs' (got {normalization!r})")
    if isinstance(min_pairs, bool) or not isinstance(min_pairs, (int, np.integer)) or min_pairs < 1:
        raise ValueError(f"min_pairs must be an integer >= 1 (got {min_pairs!r})")


def sample_autocorrelation(
    x: ArrayLike,
    *,
    max_lag: int,
    positions: ArrayLike | None = None,
    normalization: str = "biased",
    min_pairs: int = 1,
) -> Autocorrelation:
    """Sample autocorrelation of a series observed at explicit grid positions.

    `positions` are the integer coordinates of the observations on a regular
    grid (for example the day number of each observation). Lag `k` pairs two
    observations whose positions differ by exactly `k`: a missing position is
    **absent from the pairs**, never closed up. Two observations separated by a
    ten-position gap are therefore never treated as consecutive, and a lag
    with no pair is reported as unobservable (`NaN`, `pair_counts[k] == 0`)
    rather than estimated from something else.

    With `positions=None` (or consecutive positions) and
    `normalization="biased"` the result is, bit for bit, the estimator that
    `effective_sample_size` has always used.

    Parameters
    ----------
    x:
        1-D series of finite observations. Missing values are expressed by
        absent positions, not by `NaN`.
    max_lag:
        Largest lag requested, capped at the span of the positions.
    positions:
        Strictly increasing integer coordinates, one per value. `None` means
        `0..n-1`.
    normalization:
        `"biased"` (default): every lag-`k` sum of products is divided by the
        same total sum of squares, the historical estimator (bounded in
        `[-1, 1]`, conservative with gaps because missing pairs shrink the
        lag). `"pairs"`: the lag-`k` mean product over the pairs that exist is
        divided by the variance, which removes that shrinkage but is not
        guaranteed positive semi-definite.
    min_pairs:
        A lag with fewer pairs is reported as unobservable (`NaN`).

    Returns
    -------
    Autocorrelation
    """
    if isinstance(max_lag, bool) or not isinstance(max_lag, (int, np.integer)) or max_lag < 0:
        raise ValueError(f"max_lag must be a non-negative integer (got {max_lag!r})")
    _check_normalization(normalization, min_pairs)
    series = _as_series(x)
    n = int(series.size)
    grid = _as_positions(positions, n)
    span = int(grid[-1] - grid[0])
    lag_limit = min(int(max_lag), span)
    centered = series - series.mean()
    denominator = float(centered @ centered)
    rho = np.full(lag_limit + 1, np.nan, dtype=np.float64)
    counts = np.zeros(lag_limit + 1, dtype=np.int64)
    rho[0] = 1.0
    counts[0] = n
    regular = span == n - 1
    if regular:
        biased = _autocorrelations(centered, lag_limit)
        for lag in range(1, lag_limit + 1):
            counts[lag] = n - lag
            if counts[lag] < min_pairs:
                continue
            if normalization == "biased" or denominator <= 0.0:
                rho[lag] = biased[lag]
            else:
                rho[lag] = biased[lag] * n / counts[lag]
    else:
        for lag in range(1, lag_limit + 1):
            target = grid + lag
            found = np.searchsorted(grid, target)
            clipped = np.minimum(found, n - 1)
            hit = (found < n) & (grid[clipped] == target)
            count = int(hit.sum())
            counts[lag] = count
            if count < min_pairs:
                continue
            if denominator <= 0.0:
                rho[lag] = 0.0
                continue
            product = float(centered[hit] @ centered[clipped[hit]])
            if normalization == "biased":
                rho[lag] = product / denominator
            else:
                rho[lag] = (product / count) / (denominator / n)
    return Autocorrelation(
        lags=np.arange(lag_limit + 1, dtype=np.int64),
        rho=rho,
        pair_counts=counts,
        normalization=normalization,
        min_pairs=int(min_pairs),
    )


def effective_sample_size_diagnostics(
    x: ArrayLike,
    *,
    positions: ArrayLike | None = None,
    max_lag: int | None = None,
    sensitivity_caps: Sequence[int] | None = None,
    normalization: str = "biased",
    min_pairs: int = 10,
) -> EffectiveSampleSizeDiagnostics:
    """Effective sample size with its estimator, its stopping reason and its cap sensitivity.

    Same estimator as `effective_sample_size` (Geyer's initial positive
    sequence), but it says **what ended the sum** and how the answer moves when
    the cap moves. When `stopped_by == "lag_cap"`, the figure is a function of
    the cap and not an estimate of the series: read the `sensitivity` table.

    The default cap is `ceil(10 * log10(n))`, in position units; when gaps
    stretch the span, pass `max_lag` explicitly. `n_eff` counts observed
    values, and with gaps it is the information carried by those values on the
    positions where they exist.

    Parameters
    ----------
    x, positions, normalization, min_pairs:
        See `sample_autocorrelation`. `min_pairs` defaults to 10 here: a lag
        estimated from fewer pairs is not allowed to extend the sum.
    max_lag:
        The cap of the headline figure. `None` means the default above.
    sensitivity_caps:
        Caps at which the figure is recomputed. `None` means half the headline
        cap, the cap, and twice, four and eight times the cap (those beyond the
        span of the series are dropped).
    """
    if max_lag is not None and (
        isinstance(max_lag, bool) or not isinstance(max_lag, (int, np.integer)) or max_lag < 0
    ):
        raise ValueError(f"max_lag must be a non-negative integer (got {max_lag!r})")
    series = _as_series(x)
    n = int(series.size)
    default_cap = 0 if n <= 1 else math.ceil(10.0 * math.log10(n))
    cap = default_cap if max_lag is None else int(max_lag)
    if sensitivity_caps is None:
        caps = {max(1, cap // 2), cap, 2 * cap, 4 * cap, 8 * cap}
    else:
        for value in sensitivity_caps:
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
                raise ValueError(f"sensitivity caps must be non-negative integers (got {value!r})")
        caps = {int(value) for value in sensitivity_caps}
    acf = sample_autocorrelation(
        series,
        max_lag=max(caps | {cap}),
        positions=positions,
        normalization=normalization,
        min_pairs=min_pairs,
    )
    available = int(acf.lags[-1])

    def evaluate(limit: int) -> tuple[float, int, str]:
        limit = min(limit, available)
        retained, truncation_lag, stopped_by = _geyer_sum(acf.rho, limit)
        return _n_eff_from_sum(n, retained), truncation_lag, stopped_by

    n_eff, truncation_lag, stopped_by = evaluate(cap)
    table = tuple(
        CapSensitivity(max_lag=limit, n_eff=value, truncation_lag=lag, stopped_by=reason)
        for limit in sorted(c for c in caps if c <= available)
        for value, lag, reason in (evaluate(limit),)
    )
    return EffectiveSampleSizeDiagnostics(
        n=n,
        n_eff=n_eff,
        ratio=n_eff / n,
        estimator=_GEYER_ESTIMATOR,
        normalization=normalization,
        min_pairs=int(min_pairs),
        max_lag=min(cap, available),
        truncation_lag=truncation_lag,
        stopped_by=stopped_by,
        sensitivity=table,
    )


def block_bootstrap(
    x: ArrayLike,
    statistic: Statistic,
    *,
    block_length: int | None = None,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int | None = None,
) -> BootstrapReport:
    """Circular (moving) block bootstrap of a stationary series.

    Blocks of `block_length` consecutive observations are drawn with replacement
    from the series, wrapping around its end, until a series of length `n` is
    rebuilt; the statistic is recomputed on each resample. The standard error is
    the sample standard deviation of the replicates and the confidence interval
    is the **percentile** interval.

    The default block length follows the automatic rule of Politis & White
    (2004) for the circular bootstrap; the fallback `ceil(n ** (1/3))` applies
    when the rule is undefined (see the module documentation).

    Parameters
    ----------
    x:
        Non-empty 1-D series of finite observations.
    statistic:
        Callable taking a 1-D float array and returning a single float.
    block_length:
        Length of the blocks. `None` (default) selects the automatic rule.
    n_bootstrap:
        Number of bootstrap replicates (at least 2).
    alpha:
        Significance level of the confidence interval, in `(0, 1)`.
    seed:
        Seed of the generator built by this call. The global random state is
        never touched.

    Returns
    -------
    BootstrapReport
    """
    series = _as_series(x)
    _check_bootstrap_parameters(n_bootstrap, alpha)
    if block_length is None:
        length = _politis_white_block_length(series)
    else:
        if isinstance(block_length, bool) or not isinstance(block_length, (int, np.integer)):
            raise ValueError(f"block_length must be an integer (got {block_length!r})")
        length = int(block_length)
        if length < 1:
            raise ValueError(f"block_length must be >= 1 (got {length})")
    n = int(series.size)
    rng = np.random.default_rng(seed)
    point_estimate = _evaluate_statistic(statistic, series)
    replicates = np.empty(int(n_bootstrap), dtype=np.float64)
    n_blocks = math.ceil(n / length)
    offsets = np.arange(length)
    for replicate in range(int(n_bootstrap)):
        starts = rng.integers(0, n, size=n_blocks)
        indices = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        replicates[replicate] = _evaluate_statistic(statistic, series[indices])
    lower, upper = _percentile_interval(replicates, alpha)
    return BootstrapReport(
        point_estimate=point_estimate,
        standard_error=float(np.std(replicates, ddof=1)),
        ci_lower=lower,
        ci_upper=upper,
        n_bootstrap=int(n_bootstrap),
        block_length=int(length),
        alpha=float(alpha),
    )


def cluster_bootstrap(
    x: ArrayLike,
    clusters: IntArray,
    statistic: Statistic,
    *,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int | None = None,
) -> BootstrapReport:
    """Pairs cluster bootstrap: the whole cluster travels together.

    The clusters are drawn with replacement among the clusters of the design;
    the observations of a drawn cluster keep their relative order, and the
    resampled series is the concatenation of the drawn clusters, in cluster
    order. The statistic therefore sees a series of the same length `n` when the
    clusters are balanced; with unbalanced clusters the length of a resample
    varies with the clusters drawn, and the statistic is applied to the resample
    as it comes.

    The standard error is the sample standard deviation of the replicates and
    the confidence interval is the **percentile** interval.

    Parameters
    ----------
    x:
        Non-empty 1-D series of finite observations.
    clusters:
        Integer labelling of the same length as `x`, giving the cluster of each
        observation. The labels must be contiguous integers starting at 0.
    statistic:
        Callable taking a 1-D float array and returning a single float.
    n_bootstrap:
        Number of bootstrap replicates (at least 2).
    alpha:
        Significance level of the confidence interval, in `(0, 1)`.
    seed:
        Seed of the generator built by this call. The global random state is
        never touched.

    Returns
    -------
    BootstrapReport
        `block_length` reports the number of clusters of the design, that is the
        number of independent units resampled per replicate.
    """
    series = _as_series(x)
    labels = _as_labels(clusters, int(series.size))
    _check_bootstrap_parameters(n_bootstrap, alpha)
    n_clusters = int(np.unique(labels).size)
    if n_clusters < 2:
        raise ValueError("at least 2 clusters are required (got 1)")
    rng = np.random.default_rng(seed)
    point_estimate = _evaluate_statistic(statistic, series)
    order = np.argsort(labels, kind="stable")
    boundaries = np.searchsorted(labels[order], np.arange(n_clusters + 1))
    replicates = np.empty(int(n_bootstrap), dtype=np.float64)
    for replicate in range(int(n_bootstrap)):
        drawn = np.sort(rng.integers(0, n_clusters, size=n_clusters))
        indices = np.concatenate([order[boundaries[c] : boundaries[c + 1]] for c in drawn])
        replicates[replicate] = _evaluate_statistic(statistic, series[indices])
    lower, upper = _percentile_interval(replicates, alpha)
    return BootstrapReport(
        point_estimate=point_estimate,
        standard_error=float(np.std(replicates, ddof=1)),
        ci_lower=lower,
        ci_upper=upper,
        n_bootstrap=int(n_bootstrap),
        block_length=n_clusters,
        alpha=float(alpha),
    )


def independent_unit_sensitivity(
    x: ArrayLike,
    clusterings: Mapping[str, IntArray],
    statistic: Statistic,
    *,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int | None = None,
) -> SensitivityReport:
    """Same statistic under several competing definitions of the independent unit.

    For a given labelling, the independent unit is the cluster: each cluster is
    reduced to its mean, giving the unit-level series, and the statistic is
    applied to that series. The estimate is therefore the one implied by that
    definition of the unit (with the mean statistic, the unweighted mean over
    units), and its uncertainty comes from the cluster bootstrap applied to the
    unit-level series.

    This is the practical guard against the trap of mistaking many
    measurements for many independent experiments: a hundred thousand
    measurements taken on three basins do not give a hundred thousand
    independent experiments, and the estimate itself moves when the definition
    of the unit changes.

    Parameters
    ----------
    x:
        Non-empty 1-D series of finite observations.
    clusterings:
        Non-empty mapping from a label (for example "station", "basin", "day")
        to a labelling of the observations. Every labelling must have the same
        length as `x` and must be contiguous from 0.
    statistic:
        Callable taking a 1-D float array and returning a single float.
    n_bootstrap:
        Number of bootstrap replicates (at least 2).
    alpha:
        Significance level of the confidence intervals, in `(0, 1)`.
    seed:
        Seed of the generator built by this call. The global random state is
        never touched.

    Returns
    -------
    SensitivityReport
    """
    series = _as_series(x)
    if not isinstance(clusterings, Mapping):
        raise ValueError("clusterings must be a mapping from a label to cluster labels")
    if len(clusterings) == 0:
        raise ValueError("clusterings must not be empty")
    _check_bootstrap_parameters(n_bootstrap, alpha)
    labels = sorted(clusterings)
    for label in labels:
        if not isinstance(label, str):
            raise ValueError(f"clustering labels must be strings (got {label!r})")
        _as_labels(clusterings[label], int(series.size))
    # One generator per labelling, all derived from the seed of this call: the
    # analysis is reproducible, and the labellings do not share their draws.
    children = np.random.SeedSequence(seed).spawn(len(labels))
    point_estimates: list[tuple[str, float]] = []
    per_label_reports: list[tuple[str, BootstrapReport]] = []
    for label, child in zip(labels, children, strict=True):
        unit_labels = _as_labels(clusterings[label], int(series.size))
        n_units = int(np.unique(unit_labels).size)
        sums = np.bincount(unit_labels, weights=series, minlength=n_units)
        counts = np.bincount(unit_labels, minlength=n_units)
        unit_means = sums / counts
        report = cluster_bootstrap(
            unit_means,
            np.arange(n_units, dtype=np.int64),
            statistic,
            n_bootstrap=n_bootstrap,
            alpha=alpha,
            seed=child,
        )
        point_estimates.append((label, report.point_estimate))
        per_label_reports.append((label, report))
    values = [value for _, value in point_estimates]
    return SensitivityReport(
        point_estimates=tuple(point_estimates),
        spread=max(values) - min(values),
        per_label_reports=tuple(per_label_reports),
    )


__all__ = [
    "Autocorrelation",
    "BootstrapReport",
    "CapSensitivity",
    "EffectiveSampleSize",
    "EffectiveSampleSizeDiagnostics",
    "SensitivityReport",
    "block_bootstrap",
    "cluster_bootstrap",
    "effective_sample_size",
    "effective_sample_size_diagnostics",
    "independent_unit_sensitivity",
    "sample_autocorrelation",
]
