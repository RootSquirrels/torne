"""Proper scoring rules and calibration diagnostics for probabilistic forecasts.

Purpose
-------
A probabilistic forecast is judged on two distinct grounds, and this module
keeps them apart:

- **Sharpness** -- how concentrated the predictive law is. A point forecast is
  the sharpest law that exists, and also the worst one, because it is
  certainly wrong. Proper scoring rules price that trade-off in a single
  number, to be *averaged* over the evaluation sample.
- **Calibration** -- whether the stated probabilities match the observed
  frequencies. Calibration is invisible to a sharpness-only comparison: a
  forecast can be perfectly sharp and perfectly miscalibrated at the same time.

Two families of estimators follow:

1. **Proper scoring rules** -- `crps_gaussian`, `crps_ensemble`,
   `interval_score`, `pinball_score`. One value per (forecast, observation)
   pair; the sample average is minimised by the true predictive law for a
   strictly proper rule. All of them are *negatively oriented*: lower is
   better.
2. **Calibration diagnostics** -- `pit_gaussian` and `calibration_report`. The
   Probability Integral Transform (PIT) of the observations under the forecast
   law is uniform if and only if the forecast is calibrated (Wilks 1939); the
   report turns that statement into a histogram, a chi-square goodness-of-fit
   test, a Kolmogorov-Smirnov test, and the empirical coverage of a few
   nominal levels.

Convention: the ensemble CRPS is the **unbiased** (fair) estimator, whose
pairwise term is normalised by `M(M-1)` rather than `M^2`. This removes the
finite-ensemble bias of the naive plug-in estimator (Ferro 2014) and is the
estimator that does not reward a forecaster merely for carrying more members.

Validation: every estimator refuses an empty, wrongly shaped, non-finite or
out-of-domain input with a `ValueError`. Nothing is silently coerced,
substituted or clipped.

References
----------
- Gneiting, T. & Raftery, A. E. (2007), "Strictly Proper Scoring Rules,
  Prediction, and Estimation", *Journal of the American Statistical
  Association* 102(477), 359-378.
- Gneiting, T., Raftery, A. E., Westveld, A. H. & Goldman, R. M. (2005),
  "Calibration of Probabilistic Forecasting Systems: A Finite-State Approach",
  *Monthly Weather Review* 133(5), 1155-1174.
- Hersbach, J. (2000), "Decomposition of the Continuous Ranked Probability
  Score for Ensemble Prediction Systems, and Its Application", *Monthly
  Weather Review* 128(3), 574-580.
- Johnson, S. O. (2008), "Hierarchical Bayesian Calibration of Predictive
  Distributions", in *Proceedings of the 24th Conference on Uncertainty in
  Artificial Intelligence (UAI 2008)*.
- Koenker, R. & Bassett, G. (1978), "Regression Quantiles", *Econometrica*
  46(1), 33-50.
- Winkler, R. L. (1970), "A Score for Evaluating Forecasts", *Journal of the
  American Statistical Association* 65(290), 1070-1075.
- Wilks, F. (1939), "Distribution of the Probability Integral Transform",
  *Bulletin of the American Meteorological Society* 24(4), 76-77.
- Ferro, C. A. T. (2014), "Fair Scores for Ensemble Forecasts", *Quarterly
  Journal of the Royal Meteorological Society* 140(681), 1917-1927.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

FloatArray = NDArray[np.float64]

# Nominal levels whose empirical coverage `calibration_report` publishes.
_COVERAGE_LEVELS: tuple[float, ...] = (0.5, 0.8, 0.9, 0.95)

_INV_SQRT_PI = 1.0 / math.sqrt(math.pi)


def _finite_float(value: float, name: str) -> float:
    """Return `value` as a finite float, or refuse it with a `ValueError`.

    No silent coercion: a non-real or non-finite input is an error, never a
    substituted default.
    """
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a real number (got {value!r})") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite (got {value!r})")
    return number


def _float_array(values: ArrayLike, name: str) -> FloatArray:
    """Return `values` as a 1D float64 array, or refuse it with a `ValueError`."""
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be convertible to a real numeric array") from exc
    if array.ndim != 1:
        raise ValueError(f"{name} must be a 1D array (got {array.ndim} dimensions)")
    return array


def crps_gaussian(observation: float, mean: float, std: float) -> float:
    """Continuous Ranked Probability Score of a Gaussian predictive law.

    Closed form of the CRPS of `N(mean, std**2)` at the observation:

        `sigma * (z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi))`,  `z = (y - mu)/sigma`

    where `Phi` is the standard normal CDF and `phi` its density. The score is
    a proper scoring rule: it is the expected value of the squared distance
    between the predictive CDF and the Heaviside step located at the
    observation.

    Reference: Gneiting, T. & Raftery, A. E. (2007), "Strictly Proper Scoring
    Rules, Prediction, and Estimation", *JASA* 102(477), 359-378, section 1
    (the CRPS as the negatively oriented integral of the squared CDF error).
    """
    y = _finite_float(observation, "observation")
    mu = _finite_float(mean, "mean")
    sigma = _finite_float(std, "std")
    if sigma <= 0.0:
        raise ValueError(f"std must be strictly positive (got {sigma})")
    z = (y - mu) / sigma
    if not math.isfinite(z):
        # |z| overflowed (a denormal sigma, or an observation far outside the
        # double range): Phi(z) is then 0 or 1 and phi(z) is 0, so the closed
        # form collapses to |y - mu| - sigma / sqrt(pi).
        return float(abs(y - mu) - sigma * _INV_SQRT_PI)
    cdf = float(stats.norm.cdf(z))
    pdf = float(stats.norm.pdf(z))
    return float(sigma * (z * (2.0 * cdf - 1.0) + 2.0 * pdf - _INV_SQRT_PI))


def crps_ensemble(observation: float, ensemble: ArrayLike) -> float:
    """Continuous Ranked Probability Score of an empirical predictive law.

    The ensemble is a sample of the predictive law; the score is the **unbiased
    (fair)** estimator of the CRPS of the law behind it:

        `E|X - y| - 0.5 * E|X - X'|`

    where the two expectations are estimated on the ensemble. The pairwise
    term is normalised by `M(M-1)` and excludes the diagonal, which removes the
    finite-ensemble bias of the naive plug-in estimator (Ferro 2014); it is
    estimated as

        `sum_{i<j} (x_(j) - x_(i)) / (M(M-1))`

    over the order statistics `x_(1) <= ... <= x_(M)`. That identity turns the
    quadratic double sum into a linear pass over the sorted members, so the
    whole estimator costs one sort, `O(M log M)`.

    The estimator is a consistent estimate of the CRPS of the underlying law,
    not the exact CRPS of the empirical law: for a small ensemble it may even
    be slightly negative, which is the price of removing the finite-ensemble
    bias. A single member has no distinct pair, so the pairwise term is empty
    and the estimator reduces to the absolute error -- which is also the exact
    CRPS of the one-point empirical law.

    Reference: Hersbach, J. (2000), "Decomposition of the Continuous Ranked
    Probability Score for Ensemble Prediction Systems, and Its Application",
    *Monthly Weather Review* 128(3), 574-580, eq. (1) (ensemble CRPS);
    Ferro, C. A. T. (2014), "Fair Scores for Ensemble Forecasts", *QJRMS*
    140(681), 1917-1927 (the fair/unbiased normalisation).
    """
    y = _finite_float(observation, "observation")
    members = _float_array(ensemble, "ensemble")
    n = int(members.size)
    if n == 0:
        raise ValueError("ensemble must not be empty")
    if not np.isfinite(members).all():
        raise ValueError("ensemble contains a non-finite value")
    ordered = np.sort(members)
    skill = float(np.abs(ordered - y).mean())
    if n == 1:
        return skill
    # `sum_{i<j} (x_(j) - x_(i))` rewritten over the consecutive gaps: the gap
    # between the k-th and (k+1)-th order statistics is crossed by exactly
    # k * (M - k) pairs. Every term is non-negative, so the sum cannot lose
    # accuracy to cancellation.
    indices = np.arange(1, n, dtype=np.float64)
    counts = indices * (n - indices)
    spread = float(np.dot(counts, np.diff(ordered)))
    return float(skill - spread / (n * (n - 1)))


def interval_score(observation: float, lower: float, upper: float, alpha: float) -> float:
    """Winkler (interval) score of a central predictive interval.

    For the central `1 - alpha` interval `[lower, upper]`:

        `(upper - lower) + (2/alpha) * (lower - observation)_+ + (2/alpha) * (observation - upper)_+`

    The width is the price of the interval; each miss is charged `2/alpha`
    times its distance outside the interval, so that the score of the
    `1 - alpha` interval equals the sum of the two `alpha/2` and `1 - alpha/2`
    quantile losses, rescaled:

        `interval_score(y, l, u, alpha) == (2/alpha) * (pinball(y, l, alpha/2) + pinball(y, u, 1 - alpha/2))`

    Reference: Winkler, R. L. (1970), "A Score for Evaluating Forecasts",
    *Journal of the American Statistical Association* 65(290), 1070-1075.
    """
    y = _finite_float(observation, "observation")
    lo = _finite_float(lower, "lower")
    up = _finite_float(upper, "upper")
    level = _finite_float(alpha, "alpha")
    if not 0.0 < level < 1.0:
        raise ValueError(f"alpha must lie strictly between 0 and 1 (got {level})")
    if lo > up:
        raise ValueError(f"lower must not exceed upper (got lower={lo}, upper={up})")
    width = up - lo
    distance = max(lo - y, 0.0) + max(y - up, 0.0)
    return float(width + (2.0 / level) * distance)


def pinball_score(observation: float, quantile: float, tau: float) -> float:
    """Pinball (quantile) loss of a single quantile forecast.

        `tau * (observation - quantile)_+ + (1 - tau) * (quantile - observation)_+`

    The loss is the asymmetric absolute error: it charges `tau` for a miss on
    the upper side and `1 - tau` for a miss on the lower side, so that its
    sample average is minimised by the `tau`-quantile of the observations. At
    `tau = 0.5` it is half the absolute error.

    Reference: Koenker, R. & Bassett, G. (1978), "Regression Quantiles",
    *Econometrica* 46(1), 33-50 (the check function; the score is its negative
    orientation).
    """
    y = _finite_float(observation, "observation")
    q = _finite_float(quantile, "quantile")
    level = _finite_float(tau, "tau")
    if not 0.0 < level < 1.0:
        raise ValueError(f"tau must lie strictly between 0 and 1 (got {level})")
    return float(level * max(y - q, 0.0) + (1.0 - level) * max(q - y, 0.0))


def pit_gaussian(observation: float, mean: float, std: float) -> float:
    """Probability Integral Transform of an observation under a Gaussian law.

    Returns `Phi((y - mu)/sigma)`, the probability the predictive law assigns
    to the event "the observation is at most what was observed". The PIT of a
    calibrated forecast is uniform on `[0, 1]`: the histogram of the PIT
    values is then flat, and a systematic departure from flatness is a
    miscalibration.

    Reference: Wilks, F. (1939), "Distribution of the Probability Integral
    Transform", *Bulletin of the American Meteorological Society* 24(4), 76-77.
    """
    y = _finite_float(observation, "observation")
    mu = _finite_float(mean, "mean")
    sigma = _finite_float(std, "std")
    if sigma <= 0.0:
        raise ValueError(f"std must be strictly positive (got {sigma})")
    return float(stats.norm.cdf((y - mu) / sigma))


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Calibration diagnostics of a set of PIT values.

    `bins` is the PIT histogram as `(lower_edge, upper_edge, count)`, the
    edges spanning `[0, 1]` and the last bin being closed on the right, so
    that a PIT of exactly 1 is counted.

    `chi_square_statistic` and `chi_square_pvalue` are Pearson's goodness of
    fit of that histogram against the uniform histogram;
    `chi_square_degrees_of_freedom` is `n_bins - 1`. The approximation
    requires `n` to be much larger than `n_bins`.

    `ks_statistic` and `ks_pvalue` are the one-sample Kolmogorov-Smirnov test
    of the PIT values against `Uniform(0, 1)`: it uses the whole sample rather
    than the bins, and detects the departures the histogram can hide.

    `mean_pit` should be close to 0.5 for a calibrated forecast, and
    `coverage` gives, for each nominal level, the empirical probability that
    the observation falls below the corresponding predictive quantile.
    """

    n: int
    bins: tuple[tuple[float, float, int], ...]
    chi_square_statistic: float
    chi_square_pvalue: float
    ks_statistic: float
    ks_pvalue: float
    mean_pit: float
    coverage: tuple[tuple[float, float], ...]
    n_bins: int
    chi_square_degrees_of_freedom: int


def calibration_report(pit_values: ArrayLike, *, n_bins: int = 10) -> CalibrationReport:
    """Calibration diagnostics of a sample of PIT values.

    The report answers one question -- "are these PIT values uniform?" -- with
    two independent tests and with the empirical coverage of a few nominal
    levels:

    - the chi-square goodness of fit of the PIT histogram against the uniform
      histogram (`n_bins` bins spanning `[0, 1]`);
    - the one-sample Kolmogorov-Smirnov test against `Uniform(0, 1)`, which
      uses the whole sample and is not blinded by the binning;
    - the empirical coverage `P(y <= q_level)` at the nominal levels 0.5, 0.8,
      0.9 and 0.95, computed from the PIT values (the observation is below
      the `level` quantile of the predictive law if and only if its PIT is
      below `level`).

    A calibrated forecast gives a flat histogram, a large KS p-value, and
    empirical coverages close to their nominal levels.

    References: Gneiting, T., Raftery, A. E., Westveld, A. H. & Goldman, R. M.
    (2005), "Calibration of Probabilistic Forecasting Systems: A Finite-State
    Approach", *Monthly Weather Review* 133(5), 1155-1174 (PIT histogram and
    its chi-square test); Johnson, S. O. (2008), "Hierarchical Bayesian
    Calibration of Predictive Distributions", in *Proceedings of the 24th
    Conference on Uncertainty in Artificial Intelligence (UAI 2008)* (the
    uniform PIT as the target of calibration).
    """
    values = _float_array(pit_values, "pit_values")
    n = int(values.size)
    if n == 0:
        raise ValueError("pit_values must not be empty")
    if not np.isfinite(values).all():
        raise ValueError("pit_values contains a non-finite value")
    if ((values < 0.0) | (values > 1.0)).any():
        raise ValueError("pit_values must lie within [0, 1]")
    if not isinstance(n_bins, (int, np.integer)):
        raise ValueError(f"n_bins must be an integer (got {n_bins!r})")
    if n_bins < 2:
        raise ValueError(f"n_bins must be at least 2 (got {n_bins})")
    bins_count = int(n_bins)

    edges = np.linspace(0.0, 1.0, bins_count + 1)
    counts, _ = np.histogram(values, bins=edges)
    bins = tuple(
        (float(edges[index]), float(edges[index + 1]), int(counts[index]))
        for index in range(bins_count)
    )

    expected = np.full(bins_count, n / bins_count, dtype=np.float64)
    chi_square = stats.chisquare(counts.astype(np.float64), expected)

    ks = stats.kstest(values, "uniform")

    coverage = tuple(
        (level, float(np.count_nonzero(values <= level) / n)) for level in _COVERAGE_LEVELS
    )

    return CalibrationReport(
        n=n,
        bins=bins,
        chi_square_statistic=float(chi_square.statistic),
        chi_square_pvalue=float(chi_square.pvalue),
        ks_statistic=float(ks.statistic),
        ks_pvalue=float(ks.pvalue),
        mean_pit=float(values.mean()),
        coverage=coverage,
        n_bins=bins_count,
        chi_square_degrees_of_freedom=bins_count - 1,
    )


__all__ = [
    "CalibrationReport",
    "calibration_report",
    "crps_ensemble",
    "crps_gaussian",
    "interval_score",
    "pinball_score",
    "pit_gaussian",
]
