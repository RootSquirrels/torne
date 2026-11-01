"""Multiplicity control: Benjamini-Hochberg, Bonferroni, Romano-Wolf step-down max-t.

Every public function is covered three times over: the nominal case, the
refusal case (an invalid input must raise `ValueError` and never be silently
coerced), and a reference-value check against a value that can be recomputed
by hand or taken from the statistical literature.

The Romano-Wolf checks compare the procedure against two references: the
exact critical value of the maximum of `m` independent standard normals,
`Phi^{-1}((1 + (1 - alpha)^{1/m}) / 2)`, and the Bonferroni procedure applied
to the marginal p-values of the same statistics.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from torne.methods.multiplicity import (
    MultiplicityDecision,
    benjamini_hochberg,
    bh_adjusted_p_values,
    bonferroni,
    romano_wolf_max_t,
)

# Five hypotheses with a clear separation between the significant ones and the
# rest: the two-sided marginal p-value of |t| = 2.9 is 0.0037, that of
# |t| = 2.4 is 0.0164, and the Bonferroni threshold for m = 5 is
# z_{1 - alpha / (2m)} = 2.576.
_STATISTICS = (2.9, 2.4, 0.3, 0.1, 0.0)


def _marginal_p_values(statistics: tuple[float, ...]) -> tuple[float, ...]:
    """Two-sided marginal p-values of the standardized statistics."""
    return tuple(float(2.0 * stats.norm.sf(abs(value))) for value in statistics)


def _equicorrelated_covariance(m: int, rho: float) -> np.ndarray:
    """Correlation matrix of `m` equicorrelated standard normals."""
    covariance = np.full((m, m), rho, dtype=np.float64)
    np.fill_diagonal(covariance, 1.0)
    return covariance


def _random_state_unchanged(left: tuple, right: tuple) -> bool:
    """Compare two `np.random.get_state()` tuples."""
    if left[0] != right[0]:
        return False
    if not np.array_equal(left[1], right[1]):
        return False
    return left[2:] == right[2:]


# =====================================================================================================================
# Benjamini-Hochberg
# =====================================================================================================================


def test_benjamini_hochberg_hand_computed_example():
    """Step-up on four hand-checked p-values.

    The rank thresholds are k/m * alpha = 0.0125, 0.025, 0.0375 and 0.05, so
    the three smallest p-values pass and the fourth does not: the largest
    admissible rank is k = 3 and the rejection set is the three first
    hypotheses. The adjusted p-values are m * p_(j) / j made monotone:
    0.04, 0.04, 0.04 and 0.9 (the value of `stats::p.adjust(method = "BH")`).
    """
    decision = benjamini_hochberg([0.01, 0.02, 0.03, 0.9], alpha=0.05)

    assert decision.method == "benjamini_hochberg"
    assert decision.alpha == pytest.approx(0.05)
    assert decision.n_tests == 4
    assert decision.n_rejected == 3
    assert decision.rejected == (True, True, True, False)
    assert decision.threshold == pytest.approx(0.03)
    assert decision.adjusted_p_values == pytest.approx((0.04, 0.04, 0.04, 0.9))


def test_benjamini_hochberg_keeps_the_submission_order():
    """The rejection flags follow the input order, not the sorted order."""
    decision = benjamini_hochberg([0.9, 0.03, 0.01, 0.02], alpha=0.05)

    assert decision.p_values == (0.9, 0.03, 0.01, 0.02)
    assert decision.rejected == (False, True, True, True)
    assert decision.adjusted_p_values == pytest.approx((0.9, 0.04, 0.04, 0.04))


def test_benjamini_hochberg_adjusted_p_values_are_monotone_and_bounded():
    """The adjusted p-values are non-decreasing along the sorted p-values."""
    p_values = [0.9, 0.03, 0.01, 0.02, 0.2]
    decision = benjamini_hochberg(p_values, alpha=0.05)

    order = np.argsort(p_values)
    adjusted = np.asarray(decision.adjusted_p_values)[order]

    assert np.all(np.diff(adjusted) >= 0.0)
    assert np.all(adjusted >= 0.0)
    assert np.all(adjusted <= 1.0)


def test_benjamini_hochberg_rejects_nothing():
    """Degenerate case: no p-value reaches its rank threshold."""
    decision = benjamini_hochberg([0.5, 0.6, 0.7, 0.8], alpha=0.05)

    assert decision.rejected == (False, False, False, False)
    assert decision.n_rejected == 0
    assert decision.threshold == 0.0
    assert decision.adjusted_p_values == pytest.approx((0.8, 0.8, 0.8, 0.8))


def test_benjamini_hochberg_rejects_everything():
    """Degenerate case: every p-value reaches its rank threshold."""
    decision = benjamini_hochberg([0.0001, 0.0002, 0.0003], alpha=0.05)

    assert decision.rejected == (True, True, True)
    assert decision.n_rejected == 3
    assert decision.threshold == pytest.approx(0.0003)
    assert decision.adjusted_p_values == pytest.approx((0.0003, 0.0003, 0.0003))


def test_benjamini_hochberg_breaks_ties_in_favour_of_rejection():
    """Tied p-values at the cut-off are all rejected."""
    decision = benjamini_hochberg([0.02, 0.02, 0.02], alpha=0.05)

    assert decision.rejected == (True, True, True)
    assert decision.n_rejected == 3
    assert decision.adjusted_p_values == pytest.approx((0.02, 0.02, 0.02))


def test_benjamini_hochberg_is_less_conservative_than_bonferroni():
    """On a mixed family, BH rejects at least one hypothesis Bonferroni keeps.

    The Bonferroni threshold is alpha/m = 0.01, so only the p-value 0.001 is
    rejected; the Benjamini-Hochberg rank thresholds are 0.01, 0.02, 0.03,
    0.04 and 0.05, so the three smallest p-values are rejected.
    """
    p_values = [0.001, 0.012, 0.02, 0.5, 0.9]

    bh = benjamini_hochberg(p_values, alpha=0.05)
    bonf = bonferroni(p_values, alpha=0.05)

    assert bh.n_rejected == 3
    assert bonf.n_rejected == 1
    assert bh.n_rejected >= bonf.n_rejected + 1


@pytest.mark.parametrize(
    ("p_values", "alpha", "message"),
    [
        ([], 0.05, "must not be empty"),
        ([0.1, float("nan")], 0.05, "must all be finite"),
        ([0.1, float("inf")], 0.05, "must all be finite"),
        ([0.1, 1.5], 0.05, "must all lie in"),
        ([0.1, -0.5], 0.05, "must all lie in"),
        ([0.1, 0.2], 0.0, "alpha must lie"),
        ([0.1, 0.2], 1.0, "alpha must lie"),
        ([0.1, 0.2], -0.1, "alpha must lie"),
        ([[0.1, 0.2]], 0.05, "one-dimensional"),
    ],
)
def test_benjamini_hochberg_refuses_invalid_inputs(p_values, alpha, message):
    """An invalid input is refused, never coerced."""
    with pytest.raises(ValueError, match=message):
        benjamini_hochberg(p_values, alpha=alpha)


# =====================================================================================================================
# Bonferroni
# =====================================================================================================================


def test_bonferroni_threshold_and_adjusted_p_values():
    """Hand-checked vector: threshold alpha/m, adjusted p-values min(1, p * m)."""
    decision = bonferroni([0.01, 0.02, 0.5], alpha=0.05)

    assert decision.method == "bonferroni"
    assert decision.alpha == pytest.approx(0.05)
    assert decision.n_tests == 3
    assert decision.n_rejected == 1
    assert decision.threshold == pytest.approx(0.05 / 3)
    assert decision.rejected == (True, False, False)
    assert decision.adjusted_p_values == pytest.approx((0.03, 0.06, 1.0))


def test_bonferroni_rejects_the_threshold_itself():
    """A p-value exactly equal to alpha/m is rejected."""
    decision = bonferroni([0.0125, 0.0126, 0.9, 0.95], alpha=0.05)

    assert decision.threshold == pytest.approx(0.0125)
    assert decision.rejected == (True, False, False, False)


def test_bonferroni_caps_the_adjusted_p_values_at_one():
    """min(1, p * m): a large p-value is capped at one."""
    decision = bonferroni([0.5, 0.9, 1.0], alpha=0.05)

    assert decision.adjusted_p_values == pytest.approx((1.0, 1.0, 1.0))
    assert decision.rejected == (False, False, False)
    assert decision.n_rejected == 0


@pytest.mark.parametrize(
    ("p_values", "alpha", "message"),
    [
        ([], 0.05, "must not be empty"),
        ([0.1, float("nan")], 0.05, "must all be finite"),
        ([0.1, 2.0], 0.05, "must all lie in"),
        ([0.1, 0.2], 1.0, "alpha must lie"),
        ([0.1, 0.2], 0.0, "alpha must lie"),
        ([[0.1, 0.2]], 0.05, "one-dimensional"),
    ],
)
def test_bonferroni_refuses_invalid_inputs(p_values, alpha, message):
    """An invalid input is refused, never coerced."""
    with pytest.raises(ValueError, match=message):
        bonferroni(p_values, alpha=alpha)


# =====================================================================================================================
# Benjamini-Hochberg adjusted p-values (convenience wrapper)
# =====================================================================================================================


def test_bh_adjusted_p_values_matches_the_decision():
    """The wrapper returns exactly the adjusted p-values of the decision."""
    p_values = [0.9, 0.03, 0.01, 0.02]

    decision = benjamini_hochberg(p_values, alpha=0.05)
    adjusted = bh_adjusted_p_values(p_values)

    assert adjusted == decision.adjusted_p_values
    assert adjusted == pytest.approx((0.9, 0.04, 0.04, 0.04))


def test_bh_adjusted_p_values_reference_values():
    """Reference values of the step-up adjusted p-values."""
    assert bh_adjusted_p_values([0.01, 0.02, 0.03, 0.9]) == pytest.approx((0.04, 0.04, 0.04, 0.9))
    assert bh_adjusted_p_values([0.5, 0.6, 0.7, 0.8]) == pytest.approx((0.8, 0.8, 0.8, 0.8))
    assert bh_adjusted_p_values([0.0001, 0.0002, 0.0003]) == pytest.approx((0.0003, 0.0003, 0.0003))


def test_bh_adjusted_p_values_is_sorted_and_bounded():
    """The adjusted p-values are non-decreasing along the sorted p-values."""
    p_values = [0.9, 0.03, 0.01, 0.02, 0.2]
    order = np.argsort(p_values)
    adjusted = np.asarray(bh_adjusted_p_values(p_values))[order]

    assert np.all(np.diff(adjusted) >= 0.0)
    assert np.all(adjusted >= 0.0)
    assert np.all(adjusted <= 1.0)


@pytest.mark.parametrize(
    ("p_values", "message"),
    [
        ([], "must not be empty"),
        ([0.1, float("nan")], "must all be finite"),
        ([0.1, 1.5], "must all lie in"),
        ([[0.1, 0.2]], "one-dimensional"),
    ],
)
def test_bh_adjusted_p_values_refuses_invalid_inputs(p_values, message):
    """An invalid input is refused, never coerced."""
    with pytest.raises(ValueError, match=message):
        bh_adjusted_p_values(p_values)


# =====================================================================================================================
# Romano-Wolf step-down max-t
# =====================================================================================================================


def test_romano_wolf_independent_hypotheses_match_the_exact_max_t_value():
    """With identity covariance the critical value is the exact max-t value.

    For `m` independent standard normals the critical value of the maximum
    absolute statistic at level `alpha` is the solution of
    `(2 Phi(c) - 1)^m = 1 - alpha`, that is
    `Phi^{-1}((1 + (1 - alpha)^{1/m}) / 2)`.
    """
    m = 5
    alpha = 0.05
    decision = romano_wolf_max_t(
        _STATISTICS, np.eye(m), alpha=alpha, n_bootstrap=4000, seed=20240101
    )

    exact = float(stats.norm.ppf((1.0 + (1.0 - alpha) ** (1.0 / m)) / 2.0))

    assert decision.method == "romano_wolf_max_t"
    assert decision.threshold == pytest.approx(exact, abs=0.1)

    # The procedure rejects what Bonferroni rejects on the same statistics.
    bonf = bonferroni(_marginal_p_values(_STATISTICS), alpha=alpha)
    assert decision.rejected == bonf.rejected
    assert decision.n_rejected == bonf.n_rejected == 1


def test_romano_wolf_is_less_conservative_than_bonferroni_under_correlation():
    """With positively correlated hypotheses, at least one extra rejection."""
    m = 5
    alpha = 0.05
    covariance = _equicorrelated_covariance(m, rho=0.8)

    decision = romano_wolf_max_t(_STATISTICS, covariance, alpha=alpha, n_bootstrap=1000, seed=11)
    bonf = bonferroni(_marginal_p_values(_STATISTICS), alpha=alpha)

    assert decision.n_rejected >= bonf.n_rejected + 1
    assert decision.n_rejected == 2
    assert bonf.n_rejected == 1


def test_romano_wolf_single_hypothesis_reduces_to_the_normal_test():
    """With one hypothesis the procedure is the usual two-sided normal test."""
    alpha = 0.05
    decision = romano_wolf_max_t([2.0], [[1.0]], alpha=alpha, n_bootstrap=4000, seed=3)

    assert decision.n_tests == 1
    assert decision.rejected == (True,)
    assert decision.threshold == pytest.approx(float(stats.norm.ppf(0.975)), abs=0.02)
    assert decision.adjusted_p_values[0] == pytest.approx(
        float(2.0 * stats.norm.sf(2.0)), abs=0.002
    )


def test_romano_wolf_adjusted_p_values_agree_with_the_rejections():
    """A rejected hypothesis has an adjusted p-value at most alpha."""
    m = 5
    covariance = _equicorrelated_covariance(m, rho=0.8)
    decision = romano_wolf_max_t(_STATISTICS, covariance, alpha=0.05, n_bootstrap=1000, seed=5)

    assert decision.n_rejected == 2
    for rejected, adjusted in zip(decision.rejected, decision.adjusted_p_values, strict=True):
        assert 0.0 <= adjusted <= 1.0
        if rejected:
            assert adjusted <= decision.alpha
        else:
            assert adjusted > decision.alpha


def test_romano_wolf_is_deterministic_for_a_fixed_seed():
    """Same seed, same result (INV-36)."""
    covariance = _equicorrelated_covariance(5, rho=0.8)

    first = romano_wolf_max_t(_STATISTICS, covariance, alpha=0.05, n_bootstrap=500, seed=99)
    second = romano_wolf_max_t(_STATISTICS, covariance, alpha=0.05, n_bootstrap=500, seed=99)

    assert first.rejected == second.rejected
    assert first.adjusted_p_values == second.adjusted_p_values
    assert first.threshold == second.threshold
    assert first.p_values == second.p_values


def test_romano_wolf_does_not_touch_the_global_random_state():
    """The global random state is left exactly as it was found (INV-35)."""
    state_before = np.random.get_state()

    romano_wolf_max_t(
        _STATISTICS,
        _equicorrelated_covariance(5, rho=0.8),
        alpha=0.05,
        n_bootstrap=200,
        seed=7,
    )

    state_after = np.random.get_state()
    assert _random_state_unchanged(state_before, state_after)


@pytest.mark.parametrize(
    ("statistics", "covariance", "alpha", "n_bootstrap", "message"),
    [
        ([], [[]], 0.05, 100, "statistics must not be empty"),
        ([1.0, 2.0], [[1.0]], 0.05, 100, "covariance must have shape"),
        ([1.0, 2.0], np.ones((2, 3)), 0.05, 100, "covariance must have shape"),
        ([1.0, 2.0], [[1.0, 0.5], [0.2, 1.0]], 0.05, 100, "must be symmetric"),
        ([1.0, 2.0], [[1.0, 1.0], [1.0, 1.0]], 0.05, 100, "must be positive definite"),
        ([1.0, float("nan")], [[1.0]], 0.05, 100, "statistics must all be finite"),
        ([1.0], [[float("nan")]], 0.05, 100, "covariance must contain only finite"),
        ([[1.0]], [[1.0]], 0.05, 100, "statistics must be a one-dimensional"),
        ([1.0], [[1.0]], 0.0, 100, "alpha must lie"),
        ([1.0], [[1.0]], 1.0, 100, "alpha must lie"),
        ([1.0], [[1.0]], 0.05, 1, "n_bootstrap must be at least 2"),
        ([1.0], [[1.0]], 0.05, 1.5, "n_bootstrap must be an integer"),
    ],
)
def test_romano_wolf_refuses_invalid_inputs(statistics, covariance, alpha, n_bootstrap, message):
    """An invalid input is refused, never coerced."""
    with pytest.raises(ValueError, match=message):
        romano_wolf_max_t(statistics, covariance, alpha=alpha, n_bootstrap=n_bootstrap, seed=1)


# =====================================================================================================================
# The decision object
# =====================================================================================================================


def test_multiplicity_decision_reports_a_consistent_decision():
    """A consistent decision is accepted and reports its own counts."""
    decision = MultiplicityDecision(
        method="benjamini_hochberg",
        alpha=0.05,
        p_values=(0.01, 0.5),
        rejected=(True, False),
        adjusted_p_values=(0.02, 0.5),
        threshold=0.01,
        n_rejected=1,
        n_tests=2,
    )

    assert decision.n_rejected == 1
    assert decision.n_tests == 2
    assert decision.rejected == (True, False)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "alpha": 0.05,
                "p_values": (0.01, 0.5),
                "rejected": (True,),
                "adjusted_p_values": (0.02, 0.5),
                "n_rejected": 1,
                "n_tests": 2,
            },
            "rejected must hold one flag per p-value",
        ),
        (
            {
                "alpha": 0.05,
                "p_values": (0.01, 0.5),
                "rejected": (True, False),
                "adjusted_p_values": (0.02,),
                "n_rejected": 1,
                "n_tests": 2,
            },
            "adjusted_p_values must hold one value per p-value",
        ),
        (
            {
                "alpha": 0.05,
                "p_values": (0.01, 0.5),
                "rejected": (True, False),
                "adjusted_p_values": (0.02, 1.5),
                "n_rejected": 1,
                "n_tests": 2,
            },
            "adjusted p-values must lie in",
        ),
        (
            {
                "alpha": 0.05,
                "p_values": (0.01, 0.5),
                "rejected": (True, False),
                "adjusted_p_values": (0.02, 0.5),
                "n_rejected": 1,
                "n_tests": 3,
            },
            "n_tests must equal the number of p-values",
        ),
        (
            {
                "alpha": 0.05,
                "p_values": (0.01, 0.5),
                "rejected": (True, False),
                "adjusted_p_values": (0.02, 0.5),
                "n_rejected": 2,
                "n_tests": 2,
            },
            "n_rejected must equal the number of True flags",
        ),
        (
            {
                "alpha": 1.5,
                "p_values": (0.01, 0.5),
                "rejected": (True, False),
                "adjusted_p_values": (0.02, 0.5),
                "n_rejected": 1,
                "n_tests": 2,
            },
            "alpha must lie strictly between",
        ),
    ],
)
def test_multiplicity_decision_refuses_inconsistent_fields(kwargs, message):
    """An inconsistent decision is refused."""
    with pytest.raises(ValueError, match=message):
        MultiplicityDecision(method="bonferroni", threshold=0.01, **kwargs)


# =====================================================================================================================
# Cross-procedure properties
# =====================================================================================================================


@pytest.mark.parametrize(
    "p_values",
    [
        [0.001, 0.01, 0.02, 0.5, 0.9],
        [0.04, 0.04, 0.04, 0.2],
        [0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
        [0.0001, 0.5],
    ],
)
def test_bonferroni_rejection_set_is_contained_in_the_benjamini_hochberg_one(p_values):
    """Bonferroni is never more liberal than Benjamini-Hochberg."""
    bh = benjamini_hochberg(p_values, alpha=0.05)
    bonf = bonferroni(p_values, alpha=0.05)

    assert bh.n_rejected >= bonf.n_rejected
    for rejected_bh, rejected_bonf in zip(bh.rejected, bonf.rejected, strict=True):
        if rejected_bonf:
            assert rejected_bh


def test_every_procedure_reports_the_same_family():
    """The three procedures agree on the size of the family and on the input."""
    p_values = [0.001, 0.02, 0.4, 0.7]

    for decision in (
        benjamini_hochberg(p_values),
        bonferroni(p_values),
        romano_wolf_max_t(
            [2.9, 2.0, 0.3, 0.1],
            np.eye(4),
            alpha=0.05,
            n_bootstrap=500,
            seed=2,
        ),
    ):
        assert decision.n_tests == len(decision.rejected)
        assert decision.n_rejected == sum(decision.rejected)
        assert len(decision.adjusted_p_values) == decision.n_tests
