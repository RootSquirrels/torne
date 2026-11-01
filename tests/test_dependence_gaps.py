"""Autocorrelation with explicit positions, and effective sample size diagnostics.

What is pinned here:

- on a regular series the new primitives reproduce the historical estimator
  exactly (same assumptions, same numbers);
- a gap is never closed up: pairs are formed from real positions, and a lag
  with no pair is reported as unobservable;
- the effective sample size says what ended its sum, and how the figure moves
  with the cap;
- invalid inputs are refused, nothing is coerced.

Everything is synthetic, seeded and offline. No position is a day, a station or
a river: the primitives know nothing about what a position means.
"""

from __future__ import annotations

import numpy as np
import pytest

from torne.methods.dependence import (
    _autocorrelations,
    effective_sample_size,
    effective_sample_size_diagnostics,
    sample_autocorrelation,
)

SEED = 20261102


def _ar1(n: int, phi: float, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    shocks = rng.normal(size=n)
    values = np.empty(n)
    values[0] = shocks[0]
    for t in range(1, n):
        values[t] = phi * values[t - 1] + shocks[t]
    return values


def _brute_force(x: np.ndarray, positions: np.ndarray, lag: int, normalization: str) -> float:
    """Reference implementation: explicit double loop over pairs."""
    n = x.size
    z = x - x.mean()
    index = {int(p): i for i, p in enumerate(positions)}
    products = [
        z[i] * z[index[int(p) + lag]] for i, p in enumerate(positions) if int(p) + lag in index
    ]
    total = float(z @ z)
    if normalization == "biased":
        return float(sum(products)) / total
    return (float(sum(products)) / len(products)) / (total / n)


# --------------------------------------------------------------------------
# regular series keep the historical numbers
# --------------------------------------------------------------------------


def test_regular_series_reproduce_the_historical_autocorrelation_exactly():
    x = _ar1(600, 0.8)
    result = sample_autocorrelation(x, max_lag=40)
    expected = _autocorrelations(x - x.mean(), 40)
    assert np.array_equal(result.rho, expected)
    assert np.array_equal(
        result.pair_counts, 600 - np.arange(41) + np.where(np.arange(41) == 0, 0, 0)
    )


def test_shifted_consecutive_positions_are_regular():
    x = _ar1(300, 0.7)
    base = sample_autocorrelation(x, max_lag=20)
    shifted = sample_autocorrelation(x, max_lag=20, positions=np.arange(300) + 1000)
    assert np.array_equal(base.rho, shifted.rho)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_diagnostics_match_the_historical_effective_sample_size_on_regular_series(seed):
    x = _ar1(800, 0.85, seed)
    historical = effective_sample_size(x)
    diagnostics = effective_sample_size_diagnostics(x)
    assert diagnostics.n_eff == historical.n_eff
    assert diagnostics.truncation_lag == historical.truncation_lag
    assert diagnostics.n == historical.n
    assert diagnostics.estimator == "geyer_initial_positive_sequence"


# --------------------------------------------------------------------------
# gaps are never closed up
# --------------------------------------------------------------------------


@pytest.mark.parametrize("normalization", ["biased", "pairs"])
def test_gapped_autocorrelation_matches_a_brute_force_pair_count(normalization):
    rng = np.random.default_rng(SEED)
    full = _ar1(400, 0.75)
    keep = np.sort(rng.choice(400, size=260, replace=False))
    x, positions = full[keep], keep
    result = sample_autocorrelation(x, max_lag=12, positions=positions, normalization=normalization)
    for lag in range(1, 13):
        assert result.rho[lag] == pytest.approx(
            _brute_force(x, positions, lag, normalization), rel=1e-12
        )


def test_a_long_gap_does_not_make_distant_observations_consecutive():
    # Two blocks of an AR(1) separated by a gap much longer than the memory.
    left, right = _ar1(300, 0.8, 11), _ar1(300, 0.8, 12)
    positions = np.concatenate([np.arange(300), np.arange(300) + 600])
    result = sample_autocorrelation(np.concatenate([left, right]), max_lag=5, positions=positions)
    # The compressed series would pair the last of `left` with the first of
    # `right` at lag 1; the real pair count is 2 * 299, not 599.
    assert result.pair_counts[1] == 2 * 299
    compressed = sample_autocorrelation(np.concatenate([left, right]), max_lag=5)
    assert compressed.pair_counts[1] == 599


def test_lags_without_pairs_are_unobservable_and_not_relabelled():
    # Observed only on even positions: odd lags have no pair at all.
    full = _ar1(8000, 0.8)
    positions = np.arange(0, 8000, 2)
    x = full[positions]
    gapped = sample_autocorrelation(x, max_lag=6, positions=positions)
    assert gapped.pair_counts[1] == 0
    assert np.isnan(gapped.rho[1])
    assert gapped.pair_counts[2] > 0
    assert gapped.rho[2] == pytest.approx(0.8**2, abs=0.05)
    # The compressed series would present the lag-2 correlation as lag 1.
    compressed = sample_autocorrelation(x, max_lag=6)
    assert compressed.rho[1] == pytest.approx(0.8**2, abs=0.05)


def test_min_pairs_marks_poorly_supported_lags_unobservable():
    x = _ar1(50, 0.5)
    result = sample_autocorrelation(x, max_lag=49, min_pairs=10)
    assert np.isfinite(result.rho[:41]).all()
    assert np.isnan(result.rho[41:]).all()


def test_pairs_normalization_equals_biased_rescaled_on_regular_series():
    x = _ar1(500, 0.6)
    biased = sample_autocorrelation(x, max_lag=30)
    pairs = sample_autocorrelation(x, max_lag=30, normalization="pairs")
    lags = np.arange(1, 31)
    assert np.allclose(pairs.rho[1:], biased.rho[1:] * 500 / (500 - lags))


def test_constant_series_keeps_the_historical_convention():
    result = sample_autocorrelation(np.full(40, 3.0), max_lag=5)
    assert np.array_equal(result.rho, _autocorrelations(np.zeros(40), 5))


# --------------------------------------------------------------------------
# effective sample size diagnostics
# --------------------------------------------------------------------------


def test_independent_noise_is_stopped_by_the_data_and_close_to_n():
    x = np.random.default_rng(SEED).normal(size=3000)
    result = effective_sample_size_diagnostics(x)
    assert result.stopped_by == "positivity_rule"
    assert not result.cap_bound
    assert result.ratio > 0.7


def test_a_persistent_series_with_a_small_cap_is_reported_as_cap_bound():
    x = _ar1(5000, 0.95)
    result = effective_sample_size_diagnostics(x, max_lag=3)
    assert result.cap_bound
    assert result.stopped_by == "lag_cap"
    assert result.max_lag == 3
    assert result.truncation_lag == 3


def test_sensitivity_table_exposes_the_cap_dependence():
    x = _ar1(5000, 0.95)
    result = effective_sample_size_diagnostics(x, max_lag=20, sensitivity_caps=[5, 20, 80, 320])
    caps = [row.max_lag for row in result.sensitivity]
    assert caps == [5, 20, 80, 320]
    values = [row.n_eff for row in result.sensitivity]
    assert values == sorted(values, reverse=True)
    assert values[0] > 3 * values[-1]
    assert result.sensitivity[0].stopped_by == "lag_cap"
    # The headline figure is one row of the table.
    assert result.n_eff == result.sensitivity[1].n_eff


def test_a_gap_that_leaves_lag_one_unobservable_is_flagged_not_hidden():
    full = _ar1(6000, 0.8)
    positions = np.arange(0, 6000, 2)
    result = effective_sample_size_diagnostics(full[positions], positions=positions, max_lag=8)
    assert result.stopped_by == "unobservable_lag"
    assert result.truncation_lag == 0
    assert result.n_eff == result.n


def test_diagnostics_are_deterministic():
    x = _ar1(1000, 0.9)
    assert effective_sample_size_diagnostics(x) == effective_sample_size_diagnostics(x)


def test_gapped_effective_sample_size_runs_on_irregular_positions():
    rng = np.random.default_rng(SEED)
    keep = np.sort(rng.choice(3000, size=2000, replace=False))
    x = _ar1(3000, 0.9)[keep]
    result = effective_sample_size_diagnostics(x, positions=keep, max_lag=40, min_pairs=10)
    assert 1.0 < result.n_eff < result.n
    assert result.n == 2000


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"positions": [0, 1, 1, 2]},
        {"positions": [0, 2, 1, 3]},
        {"positions": [0.0, 1.0, 2.0, 3.0]},
        {"positions": [0, 1, 2]},
        {"max_lag": -1},
        {"normalization": "other"},
        {"min_pairs": 0},
    ],
)
def test_invalid_inputs_are_refused(kwargs):
    arguments = {"max_lag": 2}
    arguments.update(kwargs)
    with pytest.raises(ValueError, match=r"positions|max_lag|normalization|min_pairs"):
        sample_autocorrelation([1.0, 2.0, 3.0, 4.0], **arguments)


def test_missing_values_must_be_expressed_as_absent_positions():
    with pytest.raises(ValueError, match="finite"):
        sample_autocorrelation([1.0, float("nan"), 3.0], max_lag=1)


def test_invalid_diagnostic_caps_are_refused():
    with pytest.raises(ValueError, match="sensitivity caps"):
        effective_sample_size_diagnostics(_ar1(50, 0.5), sensitivity_caps=[-1])
    with pytest.raises(ValueError, match="max_lag"):
        effective_sample_size_diagnostics(_ar1(50, 0.5), max_lag=-2)
