"""Multiplicity control for a family of simultaneous hypothesis tests.

Three procedures are implemented, each returning the same typed decision
object so that a decision is auditable after the fact:

- Benjamini-Hochberg step-up: controls the False Discovery Rate (FDR);
- Bonferroni single-step: controls the Family-Wise Error Rate (FWER);
- Romano-Wolf step-down max-t with a multiplier (wild) bootstrap: controls the
  FWER while exploiting the correlation between the test statistics.

This module is an original implementation: it is not a port of an external
codebase. It cites the international statistical literature directly.

Conventions
-----------
- The global random state is never touched. Every stochastic routine builds its
  own generator with `np.random.default_rng(seed)` and never calls
  `np.random.seed` nor the legacy module-level `np.random.*` functions
  (INV-35/INV-36 of `docs/CORE_CONTRACTS.md`). A fixed seed gives a
  fixed result, and the global state is left exactly as it was found.
- Every public procedure validates its inputs and raises `ValueError` with an
  English message when an input is empty, of the wrong shape, not finite, or
  outside its domain. Nothing is silently coerced or substituted.
- `threshold` is the critical value actually applied by the procedure, in the
  scale of the procedure (p-value scale for Benjamini-Hochberg and Bonferroni,
  statistic scale for Romano-Wolf).

References
----------
- Benjamini, Y. & Hochberg, Y. (1995), "Controlling the False Discovery Rate:
  A Practical and Powerful Approach to Multiple Testing", *Journal of the
  Royal Statistical Society, Series B* 57(1), 289-300.
- Bonferroni, C. (1936), "Sulla statistica e le questioni multiple",
  *Atti della Reale Accademia dei Lincei* 7, 33-36.
- Romano, J. P. & Wolf, M. (2005), "Stepwise Multiple Testing as Formalized
  Data Snooping", *Econometrica* 73(4), 1237-1282.
- Westfall, P. H. & Young, S. S. (1993), *Resampling-Based Multiple Testing*,
  Wiley.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

FloatArray = NDArray[np.float64]

_BISECTION_STEPS = 60
_ADJUSTED_P_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class MultiplicityDecision:
    """Outcome of a multiplicity-control procedure.

    `method` names the procedure ("benjamini_hochberg", "bonferroni",
    "romano_wolf_max_t"). `alpha` is the level the procedure was run at.

    `p_values` holds the p-values of the family, in the order in which they
    were submitted; `rejected` holds one flag per hypothesis, in the same
    order. `adjusted_p_values` holds the multiplicity-adjusted p-values
    (Benjamini-Hochberg step-up adjusted values for `benjamini_hochberg`,
    `min(1, p * m)` for `bonferroni`, and the inverted step-down values for
    `romano_wolf_max_t`).

    `threshold` is the critical value the procedure actually used, so that the
    decision can be replayed by hand: for Benjamini-Hochberg it is the
    p-value cut-off (the largest rejected p-value, 0.0 when nothing is
    rejected), for Bonferroni it is `alpha / m`, and for Romano-Wolf it is the
    first-step max-t critical value.

    `n_rejected` and `n_tests` are the size of the rejection set and the size
    of the family.
    """

    method: str
    alpha: float
    p_values: tuple[float, ...]
    rejected: tuple[bool, ...]
    adjusted_p_values: tuple[float, ...]
    threshold: float
    n_rejected: int
    n_tests: int

    def __post_init__(self) -> None:
        if not self.method:
            raise ValueError("method must be a non-empty string")
        if not math.isfinite(self.alpha) or not 0.0 < self.alpha < 1.0:
            raise ValueError(f"alpha must lie strictly between 0 and 1: {self.alpha}")
        n = len(self.p_values)
        if len(self.rejected) != n:
            raise ValueError(
                f"rejected must hold one flag per p-value: {len(self.rejected)} != {n}"
            )
        if len(self.adjusted_p_values) != n:
            raise ValueError(
                f"adjusted_p_values must hold one value per p-value: "
                f"{len(self.adjusted_p_values)} != {n}"
            )
        if self.n_tests != n:
            raise ValueError(f"n_tests must equal the number of p-values: {self.n_tests} != {n}")
        if self.n_rejected != sum(self.rejected):
            raise ValueError(f"n_rejected must equal the number of True flags: {self.n_rejected}")
        for value in self.p_values:
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"p-values must lie in [0, 1]: {value}")
        for value in self.adjusted_p_values:
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"adjusted p-values must lie in [0, 1]: {value}")


def _validated_p_values(p_values: ArrayLike) -> FloatArray:
    """Return `p_values` as a finite 1D float array, or raise `ValueError`."""
    p = np.asarray(p_values, dtype=np.float64)
    if p.ndim != 1:
        raise ValueError(f"p_values must be a one-dimensional array: got ndim {p.ndim}")
    if p.size == 0:
        raise ValueError("p_values must not be empty")
    if not np.isfinite(p).all():
        raise ValueError("p_values must all be finite")
    if (p < 0.0).any() or (p > 1.0).any():
        raise ValueError("p_values must all lie in [0, 1]")
    return p


def _validated_alpha(alpha: float) -> float:
    """Return `alpha` as a float in the open interval (0, 1), or raise `ValueError`."""
    try:
        value = float(alpha)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"alpha must be a real number: {alpha!r}") from exc
    if not math.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError(f"alpha must lie strictly between 0 and 1: {alpha}")
    return value


def _as_float_tuple(values: FloatArray) -> tuple[float, ...]:
    """Return `values` as a tuple of Python floats."""
    return tuple(float(value) for value in values)


def _tail_count(sorted_samples: FloatArray, value: float) -> int:
    """Number of bootstrap draws whose maximum statistic is greater than or equal to `value`.

    `sorted_samples` must be sorted in ascending order. The ratio of this count
    to the number of draws is the empirical upper-tail probability of `value`
    under the bootstrap distribution of the maximum statistic.
    """
    n = int(sorted_samples.size)
    return n - int(np.searchsorted(sorted_samples, value, side="left"))


def _critical_value(sorted_samples: FloatArray, alpha: float) -> float:
    """Critical value whose empirical upper-tail probability does not exceed `alpha`.

    The critical value is the `(-alpha)` upper-tail order statistic of the
    bootstrap sample of the maximum statistic. At `alpha = 1` the whole sample
    is admitted, and the smallest draw is returned.
    """
    n = int(sorted_samples.size)
    allowed = math.floor(alpha * n)
    if allowed >= n:
        return float(sorted_samples[0])
    return float(sorted_samples[n - allowed - 1])


def _bh_adjusted_sorted(p_sorted: FloatArray, m: int) -> FloatArray:
    """Monotone step-up adjusted p-values, computed on ascending p-values.

    `p_sorted` must be sorted in ascending order. The adjusted value of rank
    `i` is `min over j >= i of min(1, m * p_(j) / j)`, which is non-decreasing
    along the ranks.
    """
    ranks = np.arange(1, m + 1, dtype=np.float64)
    raw = m * p_sorted / ranks
    adjusted = np.minimum.accumulate(raw[::-1])[::-1]
    return np.minimum(adjusted, 1.0)


def benjamini_hochberg(p_values: ArrayLike, *, alpha: float = 0.05) -> MultiplicityDecision:
    """Benjamini-Hochberg step-up procedure, controlling the FDR at level `alpha`.

    The p-values are sorted ascending. The procedure finds the largest rank `k`
    such that `p_(k) <= (k / m) * alpha` and rejects every hypothesis of rank
    at most `k`; when no rank satisfies the inequality, nothing is rejected.
    Ties are resolved in favour of rejection: all the hypotheses whose
    p-value is at most the cut-off are rejected.

    The adjusted p-values are the monotone step-up adjusted values
    `p_adj_(i) = min over j >= i of min(1, m * p_(j) / j)`, which are
    non-decreasing in the sorted order and satisfy `p_adj <= alpha` exactly for
    the rejected hypotheses.

    Reference: Benjamini, Y. & Hochberg, Y. (1995), *Journal of the Royal
    Statistical Society, Series B* 57(1), 289-300.
    """
    p = _validated_p_values(p_values)
    level = _validated_alpha(alpha)
    m = int(p.size)

    order = np.argsort(p, kind="stable")
    p_sorted = p[order]
    ranks = np.arange(1, m + 1, dtype=np.float64)

    # Step-up: the largest rank whose p-value does not exceed its own threshold.
    admissible = p_sorted <= (ranks / m) * level
    k_max = int(np.flatnonzero(admissible)[-1]) + 1 if admissible.any() else 0

    # Monotone step-up adjusted p-values, computed on the sorted values.
    adjusted_sorted = _bh_adjusted_sorted(p_sorted, m)

    if k_max:
        threshold = float(p_sorted[k_max - 1])
        rejected = p <= threshold
    else:
        threshold = 0.0
        rejected = np.zeros(m, dtype=bool)

    adjusted = np.empty(m, dtype=np.float64)
    adjusted[order] = adjusted_sorted

    return MultiplicityDecision(
        method="benjamini_hochberg",
        alpha=level,
        p_values=_as_float_tuple(p),
        rejected=tuple(bool(flag) for flag in rejected),
        adjusted_p_values=_as_float_tuple(adjusted),
        threshold=threshold,
        n_rejected=int(rejected.sum()),
        n_tests=m,
    )


def bonferroni(p_values: ArrayLike, *, alpha: float = 0.05) -> MultiplicityDecision:
    """Bonferroni single-step procedure, controlling the FWER at level `alpha`.

    Every hypothesis is rejected when its p-value does not exceed
    `alpha / m`, where `m` is the size of the family. The adjusted p-values
    are `min(1, p * m)`.

    Reference: Bonferroni, C. (1936), *Atti della Reale Accademia dei Lincei*
    7, 33-36.
    """
    p = _validated_p_values(p_values)
    level = _validated_alpha(alpha)
    m = int(p.size)

    threshold = level / m
    rejected = p <= threshold
    adjusted = np.minimum(1.0, p * m)

    return MultiplicityDecision(
        method="bonferroni",
        alpha=level,
        p_values=_as_float_tuple(p),
        rejected=tuple(bool(flag) for flag in rejected),
        adjusted_p_values=_as_float_tuple(adjusted),
        threshold=threshold,
        n_rejected=int(rejected.sum()),
        n_tests=m,
    )


def romano_wolf_max_t(
    statistics: ArrayLike,
    covariance: ArrayLike,
    *,
    alpha: float = 0.05,
    n_bootstrap: int = 1000,
    seed: int | None = None,
) -> MultiplicityDecision:
    """Romano-Wolf step-down max-t procedure with a multiplier (wild) bootstrap.

    The setting is the one of Romano, J. P. & Wolf, M. (2005), *Econometrica*
    73(4), 1237-1282: the `m` test statistics are jointly approximately
    Gaussian under the nulls, with a known covariance.

    Standardization convention
    --------------------------
    `statistics` holds the standardized (studentized) test statistics
    `t_1, ..., t_m`, each of which has null distribution approximately
    `N(0, 1)`, and `covariance` holds their `m` by `m` covariance matrix, that
    is the matrix of the correlations of the standardized statistics.

    The Romano-Wolf multiplier bootstrap draws `v ~ N(0, I_m)`, forms the null
    replicates `t* = chol(covariance) v`, and takes the maximum absolute
    statistic `max_j |t*_j|`. The critical value is the `(1 - alpha)` quantile
    of that sample. When the caller holds raw statistics `T` with asymptotic
    covariance `Omega / n`, the standardized statistics are
    `t_j = sqrt(n) * T_j / sqrt(Omega_jj)` and the covariance of the
    standardized statistics is the correlation matrix of `Omega`; the factor
    `sqrt(n)` of the raw formulation is therefore absorbed by the
    standardization implemented here.

    Step-down
    ---------
    The hypotheses are ordered by decreasing absolute statistic. At each step
    the critical value is re-estimated on the hypotheses that are still
    candidates, using the sub-covariance of that subset, and the procedure
    stops at the first hypothesis that is not rejected. A hypothesis is
    rejected when the bootstrap upper-tail probability of its absolute
    statistic does not exceed `alpha`.

    Adjusted p-values
    -----------------
    The adjusted p-values of a step-down max-t procedure have no closed form.
    They are computed here by inverting the procedure: for each hypothesis,
    the adjusted p-value is the smallest level at which the step-down rejects
    it, found by bisection over the level, the step-down being re-run at each
    trial level. The bootstrap draws are generated once and reused by every
    trial, so the critical value is a well defined function of the level and
    the search is exact up to the bisection tolerance.

    `p_values` reports the marginal two-sided p-values of the standardized
    statistics (each statistic compared to a standard normal); the multiplicity
    adjustment is carried by `adjusted_p_values`.

    Randomness
    ----------
    The bootstrap uses its own generator, `np.random.default_rng(seed)`: the
    global random state is never touched, and a fixed seed gives a fixed
    result (INV-35/INV-36 of `docs/CORE_CONTRACTS.md`).
    """
    t = np.asarray(statistics, dtype=np.float64)
    if t.ndim != 1:
        raise ValueError(f"statistics must be a one-dimensional array: got ndim {t.ndim}")
    if t.size == 0:
        raise ValueError("statistics must not be empty")
    if not np.isfinite(t).all():
        raise ValueError("statistics must all be finite")
    m = int(t.size)

    cov = np.asarray(covariance, dtype=np.float64)
    if cov.ndim != 2:
        raise ValueError(f"covariance must be a two-dimensional array: got ndim {cov.ndim}")
    if cov.shape != (m, m):
        raise ValueError(f"covariance must have shape ({m}, {m}): got {cov.shape}")
    if not np.isfinite(cov).all():
        raise ValueError("covariance must contain only finite values")
    if not np.allclose(cov, cov.T, rtol=1e-10, atol=1e-12):
        raise ValueError("covariance must be symmetric")

    level = _validated_alpha(alpha)
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, (int, np.integer)):
        raise ValueError(f"n_bootstrap must be an integer: {n_bootstrap!r}")
    draws = int(n_bootstrap)
    if draws < 2:
        raise ValueError(f"n_bootstrap must be at least 2: {draws}")

    rng = np.random.default_rng(seed)
    multipliers = rng.standard_normal((draws, m))

    # Order the hypotheses by decreasing absolute statistic. The step-down
    # always rejects in that order, so the chain of candidate subsets is fixed:
    # the subset at step k is the hypotheses of rank k and beyond.
    order = np.argsort(-np.abs(t), kind="stable")
    sorted_samples = np.empty((m, draws), dtype=np.float64)
    for k in range(m):
        subset = order[k:]
        sub_covariance = cov[np.ix_(subset, subset)]
        try:
            cholesky = np.linalg.cholesky(sub_covariance)
        except np.linalg.LinAlgError as exc:
            raise ValueError("covariance must be positive definite") from exc
        replicates = multipliers[:, subset] @ cholesky.T
        sorted_samples[k] = np.sort(np.max(np.abs(replicates), axis=1))

    def step_down(trial_level: float) -> FloatArray:
        """Rejection flags of the step-down run at `trial_level`."""
        rejected = np.zeros(m, dtype=bool)
        allowed = math.floor(trial_level * draws)
        for k in range(m):
            index = int(order[k])
            if _tail_count(sorted_samples[k], abs(float(t[index]))) <= allowed:
                rejected[index] = True
            else:
                break
        return rejected

    rejected = step_down(level)

    def adjusted_p_value(rank: int) -> float:
        """Smallest level at which the hypothesis of rank `rank` is rejected."""
        index = int(order[rank])
        low, high = 0.0, 1.0
        for _ in range(_BISECTION_STEPS):
            middle = 0.5 * (low + high)
            if step_down(middle)[index]:
                high = middle
            else:
                low = middle
            if high - low <= _ADJUSTED_P_TOLERANCE:
                break
        return high

    adjusted = np.empty(m, dtype=np.float64)
    for rank in range(m):
        adjusted[int(order[rank])] = adjusted_p_value(rank)

    marginal = np.minimum(1.0, 2.0 * stats.norm.sf(np.abs(t)))

    return MultiplicityDecision(
        method="romano_wolf_max_t",
        alpha=level,
        p_values=_as_float_tuple(marginal),
        rejected=tuple(bool(flag) for flag in rejected),
        adjusted_p_values=_as_float_tuple(adjusted),
        threshold=_critical_value(sorted_samples[0], level),
        n_rejected=int(rejected.sum()),
        n_tests=m,
    )


def bh_adjusted_p_values(p_values: ArrayLike) -> tuple[float, ...]:
    """Benjamini-Hochberg adjusted p-values, in the order of the input.

    Convenience wrapper for callers that need the adjusted values without the
    full decision object. The values are identical to the
    `adjusted_p_values` of `benjamini_hochberg(p_values)`.
    """
    p = _validated_p_values(p_values)
    m = int(p.size)
    order = np.argsort(p, kind="stable")
    adjusted = np.empty(m, dtype=np.float64)
    adjusted[order] = _bh_adjusted_sorted(p[order], m)
    return _as_float_tuple(adjusted)


__all__ = [
    "MultiplicityDecision",
    "benjamini_hochberg",
    "bh_adjusted_p_values",
    "bonferroni",
    "romano_wolf_max_t",
]
