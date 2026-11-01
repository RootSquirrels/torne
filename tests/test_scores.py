"""Verification of the proper scoring rules and calibration diagnostics.

Every estimator is confronted with an **independent reference**:

- the closed forms are recomputed with `scipy.stats` primitives and compared
  with hand-computed constants;
- the ensemble CRPS is confronted with the naive `O(n^2)` double sum of the
  unbiased estimator, and must be invariant to the order of the members;
- the interval score is confronted with the two quantile losses it is built
  from, and with hand-computed constants;
- the calibration report is confronted with a hand-computed chi-square
  statistic and a hand-computed Kolmogorov-Smirnov statistic, and is exercised
  on a perfectly calibrated sample and on clearly miscalibrated ones.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from torne.methods.scores import (
    CalibrationReport,
    calibration_report,
    crps_ensemble,
    crps_gaussian,
    interval_score,
    pinball_score,
    pit_gaussian,
)

# CRPS of the standard normal law at its own mean: 2 * phi(0) - 1 / sqrt(pi),
# with phi(0) = 1 / sqrt(2 pi).
CRPS_STANDARD_NORMAL_AT_MEAN = 2.0 / math.sqrt(2.0 * math.pi) - 1.0 / math.sqrt(math.pi)


def _stratified(low: float, high: float, n: int) -> np.ndarray:
    """`n` deterministic points, uniform on `[low, high]` (one per stratum)."""
    return low + (high - low) * (np.arange(n, dtype=np.float64) + 0.5) / n


def _naive_unbiased_crps(observation: float, members: np.ndarray) -> float:
    """Naive `O(n^2)` double sum of the unbiased ensemble CRPS."""
    n = members.size
    skill = float(np.abs(members - observation).mean())
    distances = np.abs(members[:, None] - members[None, :])
    pairwise = float(distances.sum() - np.trace(distances))
    return float(skill - 0.5 * pairwise / (n * (n - 1)))


def _manual_ks_statistic(values: np.ndarray) -> float:
    """Two-sided one-sample Kolmogorov-Smirnov statistic, computed by hand."""
    ordered = np.sort(values)
    n = ordered.size
    ranks = np.arange(1, n + 1, dtype=np.float64)
    upper = float(np.max(ranks / n - ordered))
    lower = float(np.max(ordered - (ranks - 1.0) / n))
    return max(upper, lower)


# =====================================================================================================================
# crps_gaussian
# =====================================================================================================================


def test_crps_gaussian_reproduces_the_closed_form_computed_independently():
    """The score matches the closed form recomputed from `scipy.stats`."""
    for observation, mean, std in ((0.0, 0.0, 1.0), (0.5, 0.0, 1.0), (-2.0, 1.0, 0.5)):
        z = (observation - mean) / std
        reference = std * (
            z * (2.0 * stats.norm.cdf(z) - 1.0) + 2.0 * stats.norm.pdf(z) - 1.0 / math.sqrt(math.pi)
        )
        assert crps_gaussian(observation, mean, std) == pytest.approx(reference, rel=1e-12)


def test_crps_gaussian_at_the_mean_equals_the_hand_computed_constant():
    """At the mean, the score of a standard normal law is `2 phi(0) - 1/sqrt(pi)`."""
    assert crps_gaussian(0.0, 0.0, 1.0) == pytest.approx(CRPS_STANDARD_NORMAL_AT_MEAN, rel=1e-12)
    assert crps_gaussian(3.0, 3.0, 2.0) == pytest.approx(
        2.0 * CRPS_STANDARD_NORMAL_AT_MEAN, rel=1e-12
    )


def test_crps_gaussian_is_location_and_scale_equivariant():
    """Translating the forecast translates the observation; scaling scales the score."""
    assert crps_gaussian(1.5, 1.0, 2.0) == pytest.approx(crps_gaussian(0.5, 0.0, 2.0), rel=1e-12)
    assert crps_gaussian(1.5, 1.0, 2.0) == pytest.approx(
        2.0 * crps_gaussian(0.75, 0.5, 1.0), rel=1e-12
    )


def test_crps_gaussian_refuses_an_invalid_standard_deviation():
    """A non-positive or non-finite standard deviation is refused."""
    with pytest.raises(ValueError, match="std must be strictly positive"):
        crps_gaussian(0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="std must be strictly positive"):
        crps_gaussian(0.0, 0.0, -1.0)
    with pytest.raises(ValueError, match="std must be finite"):
        crps_gaussian(0.0, 0.0, math.inf)


def test_crps_gaussian_refuses_a_non_finite_observation_or_mean():
    """A non-finite observation or mean is refused."""
    with pytest.raises(ValueError, match="observation must be finite"):
        crps_gaussian(math.nan, 0.0, 1.0)
    with pytest.raises(ValueError, match="mean must be finite"):
        crps_gaussian(0.0, math.inf, 1.0)


# =====================================================================================================================
# crps_ensemble
# =====================================================================================================================


def test_crps_ensemble_matches_the_naive_double_sum_of_the_unbiased_estimator():
    """The `O(n log n)` implementation reproduces the naive `O(n^2)` double sum."""
    members = np.array([0.0, 1.0, 2.0, 4.0, 7.0, 11.0])
    observation = 3.0
    assert crps_ensemble(observation, members) == pytest.approx(
        _naive_unbiased_crps(observation, members), rel=1e-12, abs=1e-12
    )


def test_crps_ensemble_equals_the_hand_computed_constants():
    """Two hand-computed values of the unbiased estimator."""
    # Members 0, 1, 2 and observation 0: skill = 1, pairwise = 8/6 = 4/3.
    assert crps_ensemble(0.0, [0.0, 1.0, 2.0]) == pytest.approx(1.0 / 3.0, rel=1e-12)
    # Two members symmetric around the observation: the pairwise term cancels
    # the skill term exactly.
    assert crps_ensemble(0.5, [0.0, 1.0]) == pytest.approx(0.0, abs=1e-12)


def test_crps_ensemble_is_invariant_to_the_order_of_the_members():
    """Permuting the ensemble does not change the score."""
    members = [0.0, 1.0, 2.0, 4.0, 7.0, 11.0]
    reference = crps_ensemble(3.0, members)
    for permutation in (
        [11.0, 7.0, 4.0, 2.0, 1.0, 0.0],
        [2.0, 11.0, 0.0, 4.0, 1.0, 7.0],
        [7.0, 0.0, 11.0, 2.0, 4.0, 1.0],
    ):
        assert crps_ensemble(3.0, permutation) == pytest.approx(reference, rel=1e-12, abs=1e-12)


def test_crps_ensemble_of_a_single_member_is_the_absolute_error():
    """With no distinct pair, the pairwise term is empty and the score is |x - y|."""
    assert crps_ensemble(2.0, [5.0]) == pytest.approx(3.0, rel=1e-12)


def test_crps_ensemble_refuses_an_empty_or_non_finite_ensemble():
    """An empty ensemble and a non-finite member are refused."""
    with pytest.raises(ValueError, match="ensemble must not be empty"):
        crps_ensemble(0.0, [])
    with pytest.raises(ValueError, match="ensemble contains a non-finite value"):
        crps_ensemble(0.0, [0.0, math.nan])
    with pytest.raises(ValueError, match="ensemble contains a non-finite value"):
        crps_ensemble(0.0, [0.0, math.inf])


def test_crps_ensemble_refuses_a_non_finite_observation():
    """A non-finite observation is refused."""
    with pytest.raises(ValueError, match="observation must be finite"):
        crps_ensemble(math.nan, [0.0, 1.0])


def test_crps_gaussian_and_crps_ensemble_agree_on_a_large_gaussian_sample():
    """A large ensemble from the same Gaussian law reproduces the closed form."""
    rng = np.random.default_rng(20241105)
    members = rng.standard_normal(20000)
    observation = 0.5
    analytic = crps_gaussian(observation, 0.0, 1.0)
    empirical = crps_ensemble(observation, members)
    assert empirical == pytest.approx(analytic, abs=0.02)
    # The agreement is far better than the scale of the score itself.
    assert abs(empirical - analytic) < 0.1 * analytic


# =====================================================================================================================
# interval_score
# =====================================================================================================================


def test_interval_score_charges_the_width_when_the_observation_is_inside():
    """An observation inside the interval costs exactly the width of the interval."""
    assert interval_score(0.5, 0.0, 1.0, 0.1) == pytest.approx(1.0, rel=1e-12)
    assert interval_score(-3.0, -4.0, -2.0, 0.05) == pytest.approx(2.0, rel=1e-12)


def test_interval_score_charges_twice_over_alpha_per_unit_of_miss():
    """A miss outside the interval is charged `2/alpha` times its distance."""
    assert interval_score(2.0, 0.0, 1.0, 0.1) == pytest.approx(1.0 + 20.0 * 1.0, rel=1e-12)
    assert interval_score(-1.0, 0.0, 1.0, 0.2) == pytest.approx(1.0 + 10.0 * 1.0, rel=1e-12)


def test_interval_score_is_the_rescaled_sum_of_its_two_quantile_losses():
    """The interval score is `(2/alpha)` times the sum of the two quantile losses."""
    for observation, lower, upper, alpha in (
        (0.5, 0.0, 1.0, 0.1),
        (2.0, 0.0, 1.0, 0.1),
        (-1.0, 0.0, 1.0, 0.2),
        (0.25, -1.0, 3.0, 0.05),
    ):
        expected = (2.0 / alpha) * (
            pinball_score(observation, lower, alpha / 2.0)
            + pinball_score(observation, upper, 1.0 - alpha / 2.0)
        )
        assert interval_score(observation, lower, upper, alpha) == pytest.approx(
            expected, rel=1e-12
        )


def test_interval_score_refuses_an_out_of_domain_alpha():
    """`alpha` must lie strictly between 0 and 1."""
    with pytest.raises(ValueError, match="alpha must lie strictly between 0 and 1"):
        interval_score(0.0, 0.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="alpha must lie strictly between 0 and 1"):
        interval_score(0.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="alpha must lie strictly between 0 and 1"):
        interval_score(0.0, 0.0, 1.0, -0.2)


def test_interval_score_refuses_inverted_or_non_finite_bounds():
    """`lower` must not exceed `upper`, and every input must be finite."""
    with pytest.raises(ValueError, match="lower must not exceed upper"):
        interval_score(0.0, 1.0, 0.0, 0.1)
    with pytest.raises(ValueError, match="upper must be finite"):
        interval_score(0.0, 0.0, math.inf, 0.1)
    with pytest.raises(ValueError, match="observation must be finite"):
        interval_score(math.nan, 0.0, 1.0, 0.1)


# =====================================================================================================================
# pinball_score
# =====================================================================================================================


def test_pinball_score_matches_the_hand_computed_constants():
    """Above the quantile the loss is `tau` times the gap; below, `1 - tau` times."""
    assert pinball_score(3.0, 2.0, 0.8) == pytest.approx(0.8, rel=1e-12)
    assert pinball_score(1.0, 2.0, 0.8) == pytest.approx(0.2, rel=1e-12)
    assert pinball_score(2.0, 2.0, 0.3) == pytest.approx(0.0, abs=1e-12)


def test_pinball_score_at_the_median_is_half_the_absolute_error():
    """`tau = 0.5` gives the symmetric loss."""
    assert pinball_score(3.0, 1.0, 0.5) == pytest.approx(1.0, rel=1e-12)
    assert pinball_score(-3.0, 1.0, 0.5) == pytest.approx(2.0, rel=1e-12)


def test_pinball_score_matches_an_independent_vectorised_computation():
    """The loss is recomputed with `numpy.maximum`."""
    for observation, quantile, tau in ((3.0, 2.0, 0.8), (-1.0, 2.0, 0.25), (0.0, 0.0, 0.9)):
        reference = tau * np.maximum(observation - quantile, 0.0) + (1.0 - tau) * np.maximum(
            quantile - observation, 0.0
        )
        assert pinball_score(observation, quantile, tau) == pytest.approx(
            float(reference), rel=1e-12
        )


def test_pinball_score_refuses_an_out_of_domain_tau():
    """`tau` must lie strictly between 0 and 1."""
    with pytest.raises(ValueError, match="tau must lie strictly between 0 and 1"):
        pinball_score(0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="tau must lie strictly between 0 and 1"):
        pinball_score(0.0, 0.0, 1.0)
    with pytest.raises(ValueError, match="tau must lie strictly between 0 and 1"):
        pinball_score(0.0, 0.0, 1.5)


def test_pinball_score_refuses_a_non_finite_input():
    """Every input must be finite."""
    with pytest.raises(ValueError, match="quantile must be finite"):
        pinball_score(0.0, math.nan, 0.5)
    with pytest.raises(ValueError, match="observation must be finite"):
        pinball_score(math.inf, 0.0, 0.5)


# =====================================================================================================================
# pit_gaussian
# =====================================================================================================================


def test_pit_gaussian_reproduces_the_normal_cdf():
    """The PIT is the standard normal CDF of the standardised observation."""
    for observation, mean, std in ((0.0, 0.0, 1.0), (0.5, 0.0, 1.0), (-2.0, 1.0, 0.5)):
        assert pit_gaussian(observation, mean, std) == pytest.approx(
            float(stats.norm.cdf((observation - mean) / std)), rel=1e-12
        )


def test_pit_gaussian_is_half_at_the_median_and_antisymmetric():
    """The PIT of the median is 0.5, and the law is symmetric about it."""
    assert pit_gaussian(0.0, 0.0, 1.0) == pytest.approx(0.5, rel=1e-12)
    assert pit_gaussian(1.0, 0.0, 1.0) + pit_gaussian(-1.0, 0.0, 1.0) == pytest.approx(
        1.0, rel=1e-12
    )


def test_pit_gaussian_refuses_an_invalid_standard_deviation_or_a_non_finite_input():
    """A non-positive standard deviation and a non-finite observation are refused."""
    with pytest.raises(ValueError, match="std must be strictly positive"):
        pit_gaussian(0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="observation must be finite"):
        pit_gaussian(math.nan, 0.0, 1.0)


# =====================================================================================================================
# calibration_report
# =====================================================================================================================


def test_calibration_report_on_a_perfectly_calibrated_sample():
    """A perfectly uniform sample gives a flat histogram and a centred mean."""
    values = _stratified(0.0, 1.0, 2000)
    report = calibration_report(values, n_bins=10)

    assert isinstance(report, CalibrationReport)
    assert report.n == 2000
    assert report.n_bins == 10
    assert report.chi_square_degrees_of_freedom == 9
    assert report.mean_pit == pytest.approx(0.5, abs=1e-12)
    assert report.chi_square_statistic == pytest.approx(0.0, abs=1e-12)
    assert report.chi_square_pvalue == pytest.approx(1.0, abs=1e-12)
    assert report.ks_statistic == pytest.approx(1.0 / (2.0 * 2000), rel=1e-9)
    assert report.ks_pvalue > 0.5


def test_calibration_report_counts_every_pit_value_in_the_histogram():
    """The bin counts sum to `n`, the edges span `[0, 1]`, and the last bin is closed."""
    values = _stratified(0.0, 1.0, 1000)
    report = calibration_report(values, n_bins=10)

    assert sum(count for _, _, count in report.bins) == report.n
    assert report.bins[0][0] == pytest.approx(0.0)
    assert report.bins[-1][1] == pytest.approx(1.0)
    edges = [edge for edge, _, _ in report.bins]
    assert edges == sorted(edges)
    assert report.bins[-1][0] == pytest.approx(0.9)

    # A PIT of exactly 1 belongs to the last bin, which is closed on the right.
    with_edge = calibration_report(np.array([0.05, 0.95, 1.0]), n_bins=10)
    assert with_edge.bins[0][2] == 1
    assert with_edge.bins[9][2] == 2
    assert sum(count for _, _, count in with_edge.bins) == 3


def test_calibration_report_chi_square_matches_a_hand_computation():
    """The chi-square statistic and its p-value are recomputed by hand."""
    values = _stratified(0.0, 1.0, 1000)
    report = calibration_report(values, n_bins=10)

    counts = np.array([count for _, _, count in report.bins], dtype=np.float64)
    expected = np.full(10, 100.0)
    statistic = float(np.sum((counts - expected) ** 2 / expected))
    assert report.chi_square_statistic == pytest.approx(statistic, abs=1e-12)
    assert report.chi_square_pvalue == pytest.approx(float(stats.chi2.sf(statistic, 9)), abs=1e-12)


def test_calibration_report_ks_statistic_matches_a_hand_computation():
    """The Kolmogorov-Smirnov statistic is recomputed by hand."""
    values = _stratified(0.0, 1.0, 1000)
    report = calibration_report(values, n_bins=10)
    assert report.ks_statistic == pytest.approx(_manual_ks_statistic(values), abs=1e-12)


def test_calibration_report_detects_miscalibration_monotonically():
    """A sample shifted away from the uniform law is detected, and increasingly so."""
    calibrated = calibration_report(_stratified(0.0, 1.0, 2000), n_bins=10)
    mildly = calibration_report(_stratified(0.2, 1.0, 2000), n_bins=10)
    badly = calibration_report(_stratified(0.85, 0.95, 2000), n_bins=10)

    assert calibrated.mean_pit == pytest.approx(0.5, abs=1e-12)
    assert mildly.mean_pit == pytest.approx(0.6, abs=1e-12)
    assert badly.mean_pit == pytest.approx(0.9, abs=1e-12)

    assert calibrated.chi_square_statistic < mildly.chi_square_statistic
    assert mildly.chi_square_statistic < badly.chi_square_statistic
    assert calibrated.ks_statistic < mildly.ks_statistic
    assert mildly.ks_statistic < badly.ks_statistic

    assert calibrated.chi_square_pvalue > 0.05
    assert badly.chi_square_pvalue < 1e-6
    assert badly.ks_pvalue < 1e-6


def test_calibration_report_reports_the_empirical_coverage_of_each_nominal_level():
    """The empirical coverage is the fraction of PIT values below the level."""
    values = _stratified(0.0, 1.0, 2000)
    report = calibration_report(values, n_bins=10)

    assert [level for level, _ in report.coverage] == [0.5, 0.8, 0.9, 0.95]
    for level, empirical in report.coverage:
        assert empirical == pytest.approx(float(np.mean(values <= level)), abs=1e-12)
    # A calibrated forecast covers at its nominal levels.
    for level, empirical in report.coverage:
        assert empirical == pytest.approx(level, abs=1e-12)


def test_calibration_report_shows_under_coverage_on_a_miscalibrated_sample():
    """Observations systematically too high under-cover the upper levels."""
    report = calibration_report(_stratified(0.85, 0.95, 2000), n_bins=10)
    coverage = dict(report.coverage)

    assert coverage[0.5] == pytest.approx(0.0, abs=1e-12)
    assert coverage[0.8] == pytest.approx(0.0, abs=1e-12)
    assert coverage[0.9] == pytest.approx(0.5, abs=1e-12)
    assert coverage[0.95] == pytest.approx(1.0, abs=1e-12)
    # Under-covered below 0.9, over-covered above: the signature of a forecast
    # whose observations are systematically higher than it predicted.
    assert coverage[0.5] < 0.5
    assert coverage[0.8] < 0.8
    assert coverage[0.9] < 0.9
    assert coverage[0.95] > 0.95


def test_calibration_report_refuses_an_empty_or_invalid_sample():
    """An empty, non-finite or out-of-range sample is refused."""
    with pytest.raises(ValueError, match="pit_values must not be empty"):
        calibration_report([])
    with pytest.raises(ValueError, match="pit_values contains a non-finite value"):
        calibration_report([0.1, math.nan])
    with pytest.raises(ValueError, match="pit_values must lie within"):
        calibration_report([0.1, 1.2])
    with pytest.raises(ValueError, match="pit_values must lie within"):
        calibration_report([-0.1, 0.5])


def test_calibration_report_refuses_too_few_bins():
    """At least two bins are required."""
    with pytest.raises(ValueError, match="n_bins must be at least 2"):
        calibration_report([0.1, 0.5, 0.9], n_bins=1)
    with pytest.raises(ValueError, match="n_bins must be an integer"):
        calibration_report([0.1, 0.5, 0.9], n_bins=2.5)
