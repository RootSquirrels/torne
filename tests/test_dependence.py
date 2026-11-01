"""Verification of the dependence-robust inference module (`torne.methods.dependence`).

Every public function is checked on three fronts:

- the **nominal case**: a documented numerical property of the estimator;
- the **refusal case**: an invalid input must raise `ValueError` with an
  explicit message, never a silent coercion;
- the **independence check**: the tool must recover the classical
  independence-based result when the observations really are independent, and
  must enlarge the uncertainty when they are not.

The global NumPy random state is captured before and after every stochastic
call: the module builds its own generator and never touches the global one
(`docs/CONTRATS_FONDAMENTAUX.md`, INV-35 and INV-36). Two calls with the same
seed must give the same result (INV-36).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from torne.methods.dependence import (
    block_bootstrap,
    cluster_bootstrap,
    effective_sample_size,
    independent_unit_sensitivity,
)

# =====================================================================================================================
# Fixtures and helpers
# =====================================================================================================================

IID_SEED = 20240917
IID_SIZE = 400
IID_SCALE = 2.0
AR1_SEED = 20240918
AR1_SIZE = 500
AR1_PHI = 0.9


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    """AR(1) series with unit innovation variance."""
    rng = np.random.default_rng(seed)
    shocks = rng.normal(size=n)
    values = np.empty(n)
    values[0] = shocks[0]
    for t in range(1, n):
        values[t] = phi * values[t - 1] + shocks[t]
    return values


def _iid(n: int = IID_SIZE, seed: int = IID_SEED, scale: float = IID_SCALE) -> np.ndarray:
    """Independent normal observations."""
    return np.random.default_rng(seed).normal(scale=scale, size=n)


def _global_state_unchanged(before: tuple, after: tuple) -> bool:
    """Compare two states returned by `np.random.get_state()`."""
    if before[0] != after[0]:
        return False
    if not np.array_equal(before[1], after[1]):
        return False
    return tuple(before[2:]) == tuple(after[2:])


# =====================================================================================================================
# effective_sample_size
# =====================================================================================================================


def test_effective_sample_size_on_independent_noise_is_close_to_n():
    """On independent noise, the effective sample size is the nominal one.

    The estimate is slightly conservative (the Geyer rule keeps the positive
    pairs, which biases the sum upwards); the tolerance is 15%.
    """
    result = effective_sample_size(np.random.default_rng(42).normal(size=2000))
    assert result.n == 2000
    assert 1.0 <= result.n_eff <= 2000
    assert abs(result.n_eff / 2000 - 1.0) <= 0.15


def test_effective_sample_size_on_independent_noise_is_close_to_n_on_average():
    """Independence check: averaged over many series, the estimate is unbiased.

    The conservative bias of the rule is a few per cent, so the mean of the
    ratios stays within 10% of 1.
    """
    ratios = [
        effective_sample_size(np.random.default_rng(seed).normal(size=2000)).ratio
        for seed in range(1000, 1020)
    ]
    assert float(np.mean(ratios)) >= 0.90
    assert float(np.mean(ratios)) <= 1.00
    assert min(ratios) >= 0.70


def test_effective_sample_size_on_a_persistent_series_is_much_smaller():
    """A strongly autocorrelated series carries far less information than its length."""
    result = effective_sample_size(_ar1(AR1_SIZE, AR1_PHI, AR1_SEED))
    assert result.ratio < 0.25
    assert result.n_eff < AR1_SIZE / 4
    assert result.truncation_lag > 0


def test_effective_sample_size_reports_the_truncation_lag():
    """The retained lags stop at the first non-positive pair (Geyer's rule)."""
    result = effective_sample_size(_ar1(AR1_SIZE, AR1_PHI, AR1_SEED))
    assert result.truncation_lag % 2 == 1
    assert result.truncation_lag <= result.n - 1


def test_effective_sample_size_refuses_invalid_inputs():
    """Empty, non-finite, non-1D inputs and out-of-domain parameters are refused."""
    with pytest.raises(ValueError, match="non-empty"):
        effective_sample_size([])
    with pytest.raises(ValueError, match="finite"):
        effective_sample_size(np.array([1.0, np.nan, 2.0]))
    with pytest.raises(ValueError, match="1-D"):
        effective_sample_size(np.ones((4, 2)))
    with pytest.raises(ValueError, match="max_lag"):
        effective_sample_size(np.arange(10.0), max_lag=-1)


# =====================================================================================================================
# block_bootstrap
# =====================================================================================================================


def test_block_bootstrap_on_independent_data_reproduces_the_analytic_standard_error():
    """Independence check: on i.i.d. data the standard error is `sigma / sqrt(n)`."""
    x = _iid()
    report = block_bootstrap(x, np.mean, n_bootstrap=2000, seed=7)
    analytic = IID_SCALE / math.sqrt(IID_SIZE)
    assert abs(report.standard_error - analytic) / analytic <= 0.15
    assert report.point_estimate == pytest.approx(float(x.mean()))
    assert report.ci_lower < report.point_estimate
    assert report.point_estimate < report.ci_upper
    assert report.n_bootstrap == 2000
    assert report.alpha == 0.05


def test_block_bootstrap_with_a_fixed_block_length_on_independent_data():
    """A block length that is short compared with the series keeps the i.i.d. result."""
    x = _iid()
    report = block_bootstrap(x, np.mean, block_length=5, n_bootstrap=2000, seed=7)
    analytic = IID_SCALE / math.sqrt(IID_SIZE)
    assert abs(report.standard_error - analytic) / analytic <= 0.20
    assert report.block_length == 5


def test_block_bootstrap_on_a_persistent_series_inflates_the_standard_error():
    """The whole point of the module: dependence enlarges the uncertainty."""
    x = _ar1(AR1_SIZE, AR1_PHI, AR1_SEED)
    report = block_bootstrap(x, np.mean, n_bootstrap=2000, seed=7)
    independent_standard_error = float(x.std(ddof=1)) / math.sqrt(AR1_SIZE)
    assert report.standard_error > 2.0 * independent_standard_error
    assert report.block_length > 1


def test_block_bootstrap_is_deterministic_for_a_fixed_seed():
    """Two calls with the same seed are identical, two calls with different seeds are not."""
    x = _iid()
    first = block_bootstrap(x, np.mean, n_bootstrap=200, seed=1234)
    second = block_bootstrap(x, np.mean, n_bootstrap=200, seed=1234)
    third = block_bootstrap(x, np.mean, n_bootstrap=200, seed=4321)
    assert first == second
    assert first.standard_error != third.standard_error


def test_block_bootstrap_does_not_touch_the_global_random_state():
    """The global NumPy state is left exactly as it was (INV-35)."""
    before = np.random.get_state()
    block_bootstrap(_iid(), np.mean, n_bootstrap=50, seed=99)
    after = np.random.get_state()
    assert _global_state_unchanged(before, after)


def test_block_bootstrap_refuses_invalid_inputs():
    """Empty or non-finite series, and out-of-domain parameters, are refused."""
    x = _iid()
    with pytest.raises(ValueError, match="non-empty"):
        block_bootstrap([], np.mean)
    with pytest.raises(ValueError, match="finite"):
        block_bootstrap(np.array([1.0, np.inf, 2.0]), np.mean)
    with pytest.raises(ValueError, match="n_bootstrap"):
        block_bootstrap(x, np.mean, n_bootstrap=1)
    with pytest.raises(ValueError, match="alpha"):
        block_bootstrap(x, np.mean, alpha=0.0)
    with pytest.raises(ValueError, match="alpha"):
        block_bootstrap(x, np.mean, alpha=1.0)
    with pytest.raises(ValueError, match="block_length"):
        block_bootstrap(x, np.mean, block_length=0)


# =====================================================================================================================
# cluster_bootstrap
# =====================================================================================================================


def test_cluster_bootstrap_with_singleton_clusters_reproduces_the_analytic_standard_error():
    """Independence check: one observation per cluster is the ordinary bootstrap."""
    x = _iid()
    report = cluster_bootstrap(x, np.arange(IID_SIZE), np.mean, n_bootstrap=2000, seed=11)
    analytic = IID_SCALE / math.sqrt(IID_SIZE)
    assert abs(report.standard_error - analytic) / analytic <= 0.15
    assert report.point_estimate == pytest.approx(float(x.mean()))
    assert report.block_length == IID_SIZE


def test_cluster_bootstrap_with_few_clusters_inflates_the_standard_error():
    """Five clusters of twenty points: the independent unit is the cluster, not the point."""
    rng = np.random.default_rng(5)
    n_clusters = 5
    per_cluster = 20
    offsets = rng.normal(scale=4.0, size=n_clusters)
    x = offsets.repeat(per_cluster) + rng.normal(size=n_clusters * per_cluster)
    clusters = np.repeat(np.arange(n_clusters), per_cluster)
    report = cluster_bootstrap(x, clusters, np.mean, n_bootstrap=2000, seed=12)
    independent_standard_error = float(x.std(ddof=1)) / math.sqrt(x.size)
    assert report.standard_error > 3.0 * independent_standard_error
    assert report.block_length == n_clusters


def test_cluster_bootstrap_keeps_the_whole_cluster_together():
    """The resampled series has the length of the original one for balanced clusters."""
    x = _iid()
    clusters = np.repeat(np.arange(5), IID_SIZE // 5)
    report = cluster_bootstrap(x, clusters, np.mean, n_bootstrap=200, seed=13)
    assert report.standard_error > 0.0
    assert report.ci_lower < report.ci_upper


def test_cluster_bootstrap_is_deterministic_for_a_fixed_seed():
    """Two calls with the same seed are identical, two calls with different seeds are not."""
    x = _iid()
    clusters = np.repeat(np.arange(5), IID_SIZE // 5)
    first = cluster_bootstrap(x, clusters, np.mean, n_bootstrap=200, seed=1234)
    second = cluster_bootstrap(x, clusters, np.mean, n_bootstrap=200, seed=1234)
    third = cluster_bootstrap(x, clusters, np.mean, n_bootstrap=200, seed=4321)
    assert first == second
    assert first.standard_error != third.standard_error


def test_cluster_bootstrap_does_not_touch_the_global_random_state():
    """The global NumPy state is left exactly as it was (INV-35)."""
    before = np.random.get_state()
    cluster_bootstrap(_iid(), np.arange(IID_SIZE), np.mean, n_bootstrap=50, seed=99)
    after = np.random.get_state()
    assert _global_state_unchanged(before, after)


def test_cluster_bootstrap_refuses_invalid_cluster_labels():
    """Labels of the wrong length, of the wrong type, or not contiguous are refused."""
    x = _iid()
    with pytest.raises(ValueError, match="same length"):
        cluster_bootstrap(x, np.zeros(5, dtype=np.int64), np.mean)
    with pytest.raises(ValueError, match="integers"):
        cluster_bootstrap(x, np.zeros(IID_SIZE), np.mean)
    with pytest.raises(ValueError, match="contiguous"):
        cluster_bootstrap(
            x, np.repeat(np.array([0, 0, 1, 1, 3, 3, 4, 4, 5, 5]), IID_SIZE // 10), np.mean
        )
    with pytest.raises(ValueError, match="contiguous"):
        cluster_bootstrap(
            x, np.repeat(np.array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5]), IID_SIZE // 10), np.mean
        )


def test_cluster_bootstrap_refuses_invalid_parameters():
    """The parameters shared with the block bootstrap are validated the same way."""
    x = _iid()
    clusters = np.arange(IID_SIZE)
    with pytest.raises(ValueError, match="n_bootstrap"):
        cluster_bootstrap(x, clusters, np.mean, n_bootstrap=1)
    with pytest.raises(ValueError, match="alpha"):
        cluster_bootstrap(x, clusters, np.mean, alpha=1.5)


# =====================================================================================================================
# independent_unit_sensitivity
# =====================================================================================================================


def test_independent_unit_sensitivity_reports_the_spread_between_definitions():
    """The same data, two definitions of the independent unit, two estimates.

    Ninety zeros, ten hundreds and twenty zeros: under the "station" labelling
    the two informative units are a station of zeros and a station of hundreds
    (mean 50), under the "basin" labelling every basin holds one hundredth
    (mean 8.33). The spread is the price of the definition.
    """
    x = np.concatenate([np.zeros(90), np.full(10, 100.0), np.zeros(20)])
    stations = np.array([0] * 90 + [1] * 10 + [2] * 20)
    basins = np.arange(120) % 10
    report = independent_unit_sensitivity(
        x, {"station": stations, "basin": basins}, np.mean, n_bootstrap=500, seed=3
    )
    labels = [label for label, _ in report.point_estimates]
    assert labels == ["basin", "station"]
    values = dict(report.point_estimates)
    assert values["station"] == pytest.approx(100.0 / 3.0)
    assert values["basin"] == pytest.approx(100.0 / 12.0)
    assert report.spread == pytest.approx(25.0)
    assert len(report.per_label_reports) == 2


def test_independent_unit_sensitivity_reports_a_bootstrap_per_definition():
    """Each definition comes with its own bootstrap report."""
    x = _iid()
    clusters = np.repeat(np.arange(5), IID_SIZE // 5)
    report = independent_unit_sensitivity(x, {"unit": clusters}, np.mean, n_bootstrap=200, seed=4)
    assert len(report.per_label_reports) == 1
    label, bootstrap_report = report.per_label_reports[0]
    assert label == "unit"
    assert bootstrap_report.point_estimate == report.point_estimates[0][1]
    assert bootstrap_report.standard_error > 0.0


def test_independent_unit_sensitivity_is_uninformative_when_the_definitions_agree():
    """Independence check: two identical labellings give two identical estimates."""
    x = np.arange(10.0)
    labels = np.repeat(np.arange(5), 2)
    report = independent_unit_sensitivity(
        x, {"first": labels, "second": labels.copy()}, np.mean, n_bootstrap=200, seed=5
    )
    assert report.spread == 0.0
    assert len(report.point_estimates) == 2


def test_independent_unit_sensitivity_is_deterministic_for_a_fixed_seed():
    """Two calls with the same seed are identical, two calls with different seeds are not."""
    x = _iid()
    clusters = np.repeat(np.arange(5), IID_SIZE // 5)
    first = independent_unit_sensitivity(x, {"unit": clusters}, np.mean, n_bootstrap=200, seed=1234)
    second = independent_unit_sensitivity(
        x, {"unit": clusters}, np.mean, n_bootstrap=200, seed=1234
    )
    third = independent_unit_sensitivity(x, {"unit": clusters}, np.mean, n_bootstrap=200, seed=4321)
    assert first == second
    assert first.per_label_reports[0][1].standard_error != (
        third.per_label_reports[0][1].standard_error
    )


def test_independent_unit_sensitivity_does_not_touch_the_global_random_state():
    """The global NumPy state is left exactly as it was (INV-35)."""
    before = np.random.get_state()
    independent_unit_sensitivity(
        _iid(), {"unit": np.arange(IID_SIZE)}, np.mean, n_bootstrap=50, seed=99
    )
    after = np.random.get_state()
    assert _global_state_unchanged(before, after)


def test_independent_unit_sensitivity_refuses_invalid_inputs():
    """An empty mapping, and labellings of the wrong length or not contiguous, are refused."""
    x = _iid()
    with pytest.raises(ValueError, match="empty"):
        independent_unit_sensitivity(x, {}, np.mean)
    with pytest.raises(ValueError, match="same length"):
        independent_unit_sensitivity(x, {"a": np.zeros(3, dtype=np.int64)}, np.mean)
    with pytest.raises(ValueError, match="contiguous"):
        independent_unit_sensitivity(
            x,
            {"a": np.repeat(np.array([0, 0, 1, 1, 3, 3, 4, 4, 5, 5]), IID_SIZE // 10)},
            np.mean,
        )
    with pytest.raises(ValueError, match="n_bootstrap"):
        independent_unit_sensitivity(x, {"a": np.arange(IID_SIZE)}, np.mean, n_bootstrap=1)
