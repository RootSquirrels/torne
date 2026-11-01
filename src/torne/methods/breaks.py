"""Rupture de moyenne d'une série : test CUSUM (OLS-CUSUM) et variance de long terme.

Origine
-------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Chemin exact    : `athanor/src/athanor/stats/breaks.py`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/CORE_CONTRACTS.md` §5.2) ; la reprise est une réécriture
                   interne et la traçabilité de l'origine est l'unique exigence.
- Code tiers      : aucun en-tête de licence tierce dans le fichier d'origine.
- Dépendances    : `numpy` et la bibliothèque standard uniquement.
- Référence       : Ploberger & Krämer (1992), « The CUSUM test for a change in
                   parameters of a linear regression model », *Econometrica*
                   60(2), 277-309 ; loi de Kolmogorov pour la queue du
                   supremum du pont brownien ; fenêtre de Newey & West (1994),
                   « Automatically generated generalized least squares
                   estimates », *Econometrica* 62(3), 631-653.

Portage
-------
Le module est repris dans son intégralité : il ne dépend d'aucun autre module
d'Athanor (`numpy` et bibliothèque standard seulement) et son comportement est
vérifié par `athanor/tests/test_breaks.py`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from .dependence import sample_autocorrelation

MIN_OBSERVATIONS = 16


def kolmogorov_sf(x: float) -> float:
    """`P(sup_t |B(t)| > x)` pour un pont brownien `B` (loi de Kolmogorov). Deux séries, toutes deux exactes."""
    if not math.isfinite(x):
        return 0.0 if x > 0 else 1.0
    if x <= 0:
        return 1.0
    if x < 1.0:
        # cdf = sqrt(2 pi) / x · somme exp(-(2j - 1)² pi² / (8 x²)) : converge vite pour x petit
        cdf = (
            math.sqrt(2 * math.pi)
            / x
            * sum(math.exp(-((2 * j - 1) ** 2) * math.pi**2 / (8 * x * x)) for j in range(1, 50))
        )
        return min(1.0, max(0.0, 1.0 - cdf))
    sf = 2.0 * sum((1.0 if j % 2 else -1.0) * math.exp(-2.0 * j * j * x * x) for j in range(1, 100))
    return min(1.0, max(0.0, sf))


def bartlett_lags(n: int) -> int:
    """Fenêtre de Newey & West (1994) : `floor(4 (n / 100)^(2/9))`."""
    return math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))


def long_run_variance(residuals: np.ndarray, lags: int) -> float:
    """Variance de long terme de résidus centrés, noyau de Bartlett (positive par construction)."""
    n = residuals.size
    v = float(residuals @ residuals) / n
    for k in range(1, min(lags, n - 1) + 1):
        v += 2.0 * (1.0 - k / (lags + 1)) * float(residuals[k:] @ residuals[:-k]) / n
    return v


@dataclass(frozen=True, slots=True)
class BreakResult:
    """`statistic` : max |S_k| / (sigma_lr sqrt(n)) ; `break_index` : dernier indice du premier régime.

    `mean_before` / `mean_after` : moyennes de part et d'autre de la rupture la
    plus probable. `NaN` signale un test non applicable (série trop courte,
    constante ou non finie).
    """

    statistic: float
    p_value: float
    break_index: int
    mean_before: float
    mean_after: float
    n_observations: int
    lags: int


def cusum_break_test(xs: ArrayLike, *, lags: int | None = 0) -> BreakResult:
    """OLS-CUSUM d'une moyenne constante (Ploberger & Krämer 1992).

    `NaN` si moins de 16 observations ou série constante. `lags = None` :
    variance de long terme de Bartlett (plus prudente sous autocorrélation).
    """
    x = np.asarray(xs, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("série unidimensionnelle attendue")
    n = x.size
    use_lags = bartlett_lags(n) if lags is None else int(lags)
    if use_lags < 0:
        raise ValueError(f"lags >= 0 requis (reçu {lags})")
    nan = float("nan")
    if n < MIN_OBSERVATIONS or not np.all(np.isfinite(x)):
        return BreakResult(nan, nan, -1, nan, nan, n, use_lags)
    resid = x - x.mean()
    sigma2 = long_run_variance(resid, use_lags)
    if not sigma2 > 0:
        return BreakResult(nan, nan, -1, nan, nan, n, use_lags)
    path = np.cumsum(resid)[:-1]  # S_1 … S_{n-1} (S_n = 0)
    k = int(np.argmax(np.abs(path)))
    stat = float(np.abs(path[k])) / math.sqrt(sigma2 * n)
    return BreakResult(
        stat,
        kolmogorov_sf(stat),
        k,
        float(x[: k + 1].mean()),
        float(x[k + 1 :].mean()),
        n,
        use_lags,
    )


# ---------------------------------------------------------------------------------------------------------------------
# Two additional ways to calibrate the same statistic (opt-in; `cusum_break_test` and `bartlett_lags` are unchanged)
# ---------------------------------------------------------------------------------------------------------------------
#
# Both routes test the same null: *the mean of the series is constant*. Neither removes a trend, a seasonal
# pattern or any other form of non-stationarity: against such a series they reject the null, and that is the
# documented behaviour. Removing structure before the test is a modelling decision that belongs to the caller.
#
# Route A - HAC-studentized. The statistic is `max|S_k| / sqrt(sigma2_lr * n)`, where `sigma2_lr` is a Bartlett-kernel
# long-run variance computed with a window chosen by the CALLER, and the p-value comes from the asymptotic
# Kolmogorov law. It assumes that the window captures all the dependence and that the mean is constant under H0.
# `cusum_hac_sensitivity` returns the whole table over a grid of windows; it selects nothing.
#
# Route B - bootstrap-calibrated. The statistic is NOT studentized: `max|S_k| / sqrt(n)`, in the units of the series,
# so it is only ever compared with its own bootstrap null. The null is generated by a non-circular moving block
# bootstrap of the globally centred series: blocks of a caller-given length are drawn with replacement, each block
# lying entirely inside one contiguous observed run, and placed into slots that reproduce the original layout of
# observed positions. Global centring removes the overall level ONLY. A trend or a mean shift is not removed from the
# blocks: it is re-randomised across blocks (and survives inside each block), so the null encodes the dependence
# up to the block length and treats anything slower as exchangeable. The test therefore asks whether the ORDER of
# the series shows more slow drift than a block-shuffled version of itself - not whether the series is stationary.
# `cusum_block_bootstrap` returns one row per block length; it selects nothing and exposes the p-value resolution.


@dataclass(frozen=True, slots=True)
class HacWindowResult:
    """The HAC-studentized CUSUM at one window.

    `autocorrelation` is the sample autocorrelation at lag `lags` (`NaN` when the lag is not observable); it is
    reported so that the choice of window can be read against the dependence it is meant to cover.
    """

    lags: int
    long_run_variance: float
    statistic: float
    p_value: float
    autocorrelation: float


@dataclass(frozen=True, slots=True)
class HacSensitivity:
    """HAC-studentized CUSUM over a grid of windows. `break_index` does not depend on the window."""

    n_observations: int
    break_index: int
    mean_before: float
    mean_after: float
    rows: tuple[HacWindowResult, ...]


@dataclass(frozen=True, slots=True)
class BlockBootstrapRow:
    """The bootstrap-calibrated CUSUM at one block length.

    `n_source_blocks` is the number of admissible block starts (blocks fully inside an observed run);
    `null_quantile` is the `1 - alpha` quantile of the bootstrap null of the statistic.
    """

    block_length: int
    n_source_blocks: int
    null_quantile: float
    p_value: float


@dataclass(frozen=True, slots=True)
class CusumBootstrapResult:
    """Bootstrap-calibrated CUSUM over a grid of block lengths.

    `statistic` is the unstudentized `max|S_k| / sqrt(n)`. `p_value_resolution` is `1 / (n_bootstrap + 1)`, the
    smallest p-value the procedure can report; a p-value at the resolution means "no replicate reached the
    observed statistic", not "p is zero". `break_position` is the original position of the break when positions
    were supplied. `seed` is the seed given by the caller (`None` if none).
    """

    statistic: float
    break_index: int
    break_position: int | None
    mean_before: float
    mean_after: float
    n_observations: int
    n_runs: int
    longest_run: int
    n_bootstrap: int
    alpha: float
    p_value_resolution: float
    seed: int | None
    rows: tuple[BlockBootstrapRow, ...]


def _prepare_series(xs: ArrayLike) -> np.ndarray:
    x = np.asarray(xs, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"xs must be a 1-D array (got shape {x.shape})")
    if x.size < MIN_OBSERVATIONS:
        raise ValueError(f"at least {MIN_OBSERVATIONS} observations are required (got {x.size})")
    if not bool(np.isfinite(x).all()):
        raise ValueError("xs must contain only finite values")
    if float(np.ptp(x)) == 0.0:
        raise ValueError("xs is constant: the statistic is not defined")
    return x


def _integer_grid(values: object, name: str, minimum: int) -> list[int]:
    if values is None or len(values) == 0:  # type: ignore[arg-type]
        raise ValueError(f"{name} must be a non-empty sequence of integers")
    grid: list[int] = []
    for value in values:  # type: ignore[attr-defined]
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise ValueError(f"{name} must contain integers (got {value!r})")
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum} (got {value})")
        grid.append(int(value))
    return sorted(set(grid))


def _cusum_path_break(x: np.ndarray) -> tuple[np.ndarray, int]:
    path = np.cumsum(x - x.mean())[:-1]
    return path, int(np.argmax(np.abs(path)))


def cusum_hac_sensitivity(xs: ArrayLike, *, lags_grid: Sequence[int]) -> HacSensitivity:
    """HAC-studentized CUSUM of a constant mean, at every window of `lags_grid`.

    This is an additional sensitivity analysis: it does not replace `cusum_break_test` and does not choose a
    window. See the comment block above for the assumptions. Observations are taken as consecutive; for a series
    with gaps use `cusum_block_bootstrap` with `positions`.

    Raises `ValueError` for fewer than 16 observations, non-finite values, a constant series, an empty or invalid
    grid, or a window `>= n`.
    """
    x = _prepare_series(xs)
    n = int(x.size)
    grid = _integer_grid(lags_grid, "lags_grid", 0)
    if grid[-1] >= n:
        raise ValueError(f"every window must be < n = {n} (got {grid[-1]})")
    residuals = x - x.mean()
    path, k = _cusum_path_break(x)
    peak = float(np.abs(path[k]))
    rho = sample_autocorrelation(x, max_lag=grid[-1]).rho
    rows = []
    for lags in grid:
        sigma2 = long_run_variance(residuals, lags)
        if not sigma2 > 0:
            raise ValueError(f"the long-run variance is not positive at window {lags}")
        stat = peak / math.sqrt(sigma2 * n)
        rows.append(
            HacWindowResult(
                lags=lags,
                long_run_variance=sigma2,
                statistic=stat,
                p_value=kolmogorov_sf(stat),
                autocorrelation=float(rho[lags]),
            )
        )
    return HacSensitivity(
        n_observations=n,
        break_index=k,
        mean_before=float(x[: k + 1].mean()),
        mean_after=float(x[k + 1 :].mean()),
        rows=tuple(rows),
    )


def _observed_runs(positions: ArrayLike | None, step: int | None, n: int) -> list[tuple[int, int]]:
    """Maximal contiguous observed runs as `(start index, length)`; one run without positions."""
    if positions is None:
        if step is not None:
            raise ValueError("step is only meaningful together with positions")
        return [(0, n)]
    if step is None:
        raise ValueError("an explicit temporal step is required when positions are supplied")
    if isinstance(step, bool) or not isinstance(step, (int, np.integer)) or step < 1:
        raise ValueError(f"step must be a positive integer (got {step!r})")
    raw = np.asarray(positions)
    if raw.ndim != 1 or raw.size != n:
        raise ValueError(f"positions must be a 1-D array with one entry per value ({n})")
    if not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"positions must be integers (got dtype {raw.dtype})")
    grid = raw.astype(np.int64, copy=False)
    gaps = np.diff(grid)
    if not bool((gaps > 0).all()):
        raise ValueError("positions must be strictly increasing")
    if not bool((gaps % int(step) == 0).all()):
        raise ValueError(f"positions must lie on a grid of step {int(step)}")
    cuts = np.flatnonzero(gaps > int(step)) + 1
    starts = np.concatenate([[0], cuts])
    ends = np.concatenate([cuts, [n]])
    return [(int(s), int(e - s)) for s, e in zip(starts, ends, strict=True)]


def _allowed_block_starts(runs: Sequence[tuple[int, int]], block_length: int) -> np.ndarray:
    """Indices at which a block of `block_length` lies entirely inside one observed run."""
    pieces = [
        np.arange(s, s + length - block_length + 1) for s, length in runs if length >= block_length
    ]
    if not pieces:
        longest = max(length for _, length in runs)
        raise ValueError(
            f"block length {block_length} cannot be supported: the longest contiguous observed run "
            f"has {longest} observations"
        )
    return np.concatenate(pieces)


def _slot_template(
    runs: Sequence[tuple[int, int]], n: int, block_length: int
) -> tuple[np.ndarray, np.ndarray, int]:
    """Block id and within-block offset of each target slot; the layout of the runs is reproduced."""
    block_id = np.empty(n, dtype=np.int64)
    offset = np.empty(n, dtype=np.int64)
    base = 0
    for start, length in runs:
        local = np.arange(length)
        block_id[start : start + length] = base + local // block_length
        offset[start : start + length] = local % block_length
        base += -(-length // block_length)
    return block_id, offset, base


def _unstudentized_stat(x: np.ndarray) -> float:
    path = np.cumsum(x - x.mean())[:-1]
    return float(np.max(np.abs(path)) / math.sqrt(x.size))


def cusum_block_bootstrap(
    xs: ArrayLike,
    *,
    block_lengths: Sequence[int],
    n_bootstrap: int = 999,
    alpha: float = 0.05,
    seed: int | None = None,
    positions: ArrayLike | None = None,
    step: int | None = None,
) -> CusumBootstrapResult:
    """Bootstrap-calibrated CUSUM of a constant mean, at every block length of `block_lengths`.

    The null is a non-circular moving block bootstrap of the globally centred series (see the comment block above
    for exactly what that does and does not remove). With `positions`, `step` is mandatory: observations are
    grouped into contiguous runs (consecutive positions differing by exactly `step`), every source block lies
    entirely within one run, and the resample keeps the original layout of runs, so no block spans a gap and the
    original positions are preserved. A block length that no run can hold raises `ValueError`.

    The p-value is `(1 + #{replicates >= observed}) / (1 + n_bootstrap)`; its resolution is reported. The result
    holds one row per block length and no summary: the caller decides how to read the grid. The random generator
    of each block length is derived from `(seed, block_length)`, so a row does not depend on which other lengths
    were requested. The global random state is never touched.
    """
    x = _prepare_series(xs)
    n = int(x.size)
    lengths = _integer_grid(block_lengths, "block_lengths", 1)
    if (
        isinstance(n_bootstrap, bool)
        or not isinstance(n_bootstrap, (int, np.integer))
        or n_bootstrap < 2
    ):
        raise ValueError(f"n_bootstrap must be an integer >= 2 (got {n_bootstrap!r})")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1) (got {alpha})")
    if seed is not None and (
        isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0
    ):
        raise ValueError(f"seed must be a non-negative integer or None (got {seed!r})")
    runs = _observed_runs(positions, step, n)
    centred = x - x.mean()
    observed = _unstudentized_stat(x)
    _, k = _cusum_path_break(x)
    rows = []
    for length in lengths:
        starts_pool = _allowed_block_starts(runs, length)
        block_id, offset, n_blocks = _slot_template(runs, n, length)
        rng = np.random.default_rng(None if seed is None else [int(seed), length])
        replicates = np.empty(int(n_bootstrap), dtype=np.float64)
        for i in range(int(n_bootstrap)):
            starts = starts_pool[rng.integers(0, starts_pool.size, size=n_blocks)]
            replicates[i] = _unstudentized_stat(centred[starts[block_id] + offset])
        exceed = int(np.sum(replicates >= observed))
        rows.append(
            BlockBootstrapRow(
                block_length=length,
                n_source_blocks=int(starts_pool.size),
                null_quantile=float(np.quantile(replicates, 1.0 - alpha)),
                p_value=(1 + exceed) / (1 + int(n_bootstrap)),
            )
        )
    grid_positions = None if positions is None else np.asarray(positions)
    return CusumBootstrapResult(
        statistic=observed,
        break_index=k,
        break_position=None if grid_positions is None else int(grid_positions[k]),
        mean_before=float(x[: k + 1].mean()),
        mean_after=float(x[k + 1 :].mean()),
        n_observations=n,
        n_runs=len(runs),
        longest_run=max(length for _, length in runs),
        n_bootstrap=int(n_bootstrap),
        alpha=float(alpha),
        p_value_resolution=1.0 / (1 + int(n_bootstrap)),
        seed=None if seed is None else int(seed),
        rows=tuple(rows),
    )


__all__ = [
    "MIN_OBSERVATIONS",
    "BlockBootstrapRow",
    "BreakResult",
    "CusumBootstrapResult",
    "HacSensitivity",
    "HacWindowResult",
    "bartlett_lags",
    "cusum_block_bootstrap",
    "cusum_break_test",
    "cusum_hac_sensitivity",
    "kolmogorov_sf",
]
