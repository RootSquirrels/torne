"""Two additional calibrations of the CUSUM test: HAC sensitivity table and block bootstrap.

Pinned here: existing defaults are unchanged; both routes return full grids and select nothing; the bootstrap
never builds a block across a gap, requires an explicit step with positions, and is reproducible; its empirical
size is controlled on a series with a constant mean, its power is high on a mean shift, and a linear trend is
rejected (documented behaviour: neither route removes a trend). Everything is synthetic, seeded and offline.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from torne.methods.breaks import (
    BreakResult,
    _allowed_block_starts,
    _slot_template,
    bartlett_lags,
    cusum_block_bootstrap,
    cusum_break_test,
    cusum_hac_sensitivity,
)

SEED = 20261103


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    shocks = rng.normal(size=n)
    values = np.empty(n)
    values[0] = shocks[0]
    for t in range(1, n):
        values[t] = phi * values[t - 1] + shocks[t]
    return values


# --------------------------------------------------------------------------
# existing contracts are untouched
# --------------------------------------------------------------------------


def test_break_result_fields_are_unchanged():
    assert [f.name for f in dataclasses.fields(BreakResult)] == [
        "statistic",
        "p_value",
        "break_index",
        "mean_before",
        "mean_after",
        "n_observations",
        "lags",
    ]


def test_default_window_rule_and_defaults_are_unchanged():
    assert bartlett_lags(100) == 4
    assert bartlett_lags(16) == 2
    x = _ar1(400, 0.5, 1)
    assert cusum_break_test(x, lags=None).lags == bartlett_lags(400)
    assert cusum_break_test(x).lags == 0


# --------------------------------------------------------------------------
# Route A - HAC sensitivity table
# --------------------------------------------------------------------------


def test_hac_table_has_one_row_per_window_and_matches_the_existing_test():
    x = _ar1(500, 0.6, 2)
    table = cusum_hac_sensitivity(x, lags_grid=[0, 5, 20, 5])
    assert [row.lags for row in table.rows] == [0, 5, 20]
    for row in table.rows:
        reference = cusum_break_test(x, lags=row.lags)
        assert row.statistic == pytest.approx(reference.statistic, rel=1e-12)
        assert row.p_value == pytest.approx(reference.p_value, rel=1e-12)
    assert table.break_index == cusum_break_test(x, lags=0).break_index
    assert table.rows[0].autocorrelation == 1.0


def test_hac_p_value_grows_with_the_window_on_a_persistent_series():
    x = _ar1(2000, 0.9, 3)
    table = cusum_hac_sensitivity(x, lags_grid=[0, 10, 50, 200])
    p = [row.p_value for row in table.rows]
    assert p == sorted(p)
    assert p[0] < p[-1]


def test_hac_selects_nothing_and_exposes_no_summary():
    table = cusum_hac_sensitivity(_ar1(200, 0.3, 4), lags_grid=[0, 3])
    assert {f.name for f in dataclasses.fields(table)} == {
        "n_observations",
        "break_index",
        "mean_before",
        "mean_after",
        "rows",
    }


@pytest.mark.parametrize(
    ("xs", "grid"),
    [
        (np.arange(10.0), [0]),
        (np.ones(50), [0]),
        (np.r_[np.arange(30.0), np.nan], [0]),
        (np.arange(50.0), []),
        (np.arange(50.0), [-1]),
        (np.arange(50.0), [50]),
        (np.arange(50.0), [1.5]),
    ],
)
def test_hac_refuses_invalid_input(xs, grid):
    with pytest.raises(
        ValueError, match=r"observations|finite|constant|lags_grid|window|integers|>="
    ):
        cusum_hac_sensitivity(xs, lags_grid=grid)


# --------------------------------------------------------------------------
# Route B - structure of the bootstrap
# --------------------------------------------------------------------------


def test_blocks_never_cross_a_gap_and_the_layout_is_reproduced():
    # Runs of 20, 7 and 25 observations: positions 0..19, 40..46, 100..124.
    positions = np.r_[np.arange(0, 20), np.arange(40, 47), np.arange(100, 125)]
    runs = [(0, 20), (20, 7), (27, 25)]
    block = 8
    starts = _allowed_block_starts(runs, block)
    for start in starts:
        owner = next(r for r in runs if r[0] <= start < r[0] + r[1])
        assert start + block <= owner[0] + owner[1]
    assert not any(20 <= s < 27 for s in starts)  # the 7-long run cannot hold a block of 8
    block_id, _offset, n_blocks = _slot_template(runs, 52, block)
    assert block_id.size == 52
    assert n_blocks == 3 + 1 + 4
    # Slots of different target runs never share a block id: the layout is preserved.
    assert set(block_id[:20]).isdisjoint(block_id[20:27])
    assert set(block_id[20:27]).isdisjoint(block_id[27:])
    assert positions.size == 52


def test_unsupported_block_length_fails_explicitly():
    x = _ar1(40, 0.2, 5)
    positions = np.r_[np.arange(0, 20), np.arange(50, 70)]
    with pytest.raises(ValueError, match="cannot be supported"):
        cusum_block_bootstrap(x, block_lengths=[25], positions=positions, step=1, seed=1)
    cusum_block_bootstrap(
        x, block_lengths=[20], positions=positions, step=1, seed=1, n_bootstrap=19
    )


def test_positions_require_an_explicit_step():
    x = _ar1(40, 0.2, 6)
    with pytest.raises(ValueError, match="explicit temporal step"):
        cusum_block_bootstrap(x, block_lengths=[5], positions=np.arange(40))
    with pytest.raises(ValueError, match="only meaningful"):
        cusum_block_bootstrap(x, block_lengths=[5], step=1)


def test_positions_off_the_step_grid_are_refused():
    x = _ar1(20, 0.2, 7)
    positions = np.arange(20) * 2
    positions[10:] += 1
    with pytest.raises(ValueError, match="grid of step 2"):
        cusum_block_bootstrap(x, block_lengths=[3], positions=positions, step=2)


def test_a_gapped_series_is_not_treated_like_its_compressed_version():
    # Two regimes in two runs separated by a long gap: with positions the break is placed at the gap and no
    # block mixes the two regimes; the layout statistics are reported.
    rng = np.random.default_rng(SEED)
    x = np.r_[rng.normal(0, 1, 60), rng.normal(3, 1, 60)]
    positions = np.r_[np.arange(60), np.arange(500, 560)]
    result = cusum_block_bootstrap(
        x, block_lengths=[5], positions=positions, step=1, n_bootstrap=199, seed=8
    )
    assert result.n_runs == 2
    assert result.longest_run == 60
    assert result.break_position in (59, 500)
    assert result.rows[0].p_value <= 0.05


def test_result_exposes_resolution_and_all_parameters_and_selects_nothing():
    x = _ar1(100, 0.3, 9)
    result = cusum_block_bootstrap(x, block_lengths=[3, 10, 3], n_bootstrap=99, alpha=0.1, seed=3)
    assert [row.block_length for row in result.rows] == [3, 10]
    assert result.p_value_resolution == pytest.approx(1 / 100)
    assert result.n_bootstrap == 99
    assert result.alpha == 0.1
    assert result.seed == 3
    assert all(row.p_value >= result.p_value_resolution for row in result.rows)
    assert all(row.n_source_blocks == 100 - row.block_length + 1 for row in result.rows)
    names = {f.name for f in dataclasses.fields(result)}
    assert "p_value" not in names


# --------------------------------------------------------------------------
# Route B - reproducibility
# --------------------------------------------------------------------------


def test_same_seed_same_result_and_global_state_untouched():
    x = _ar1(150, 0.5, 10)
    before = np.random.get_state()
    first = cusum_block_bootstrap(x, block_lengths=[4, 12], n_bootstrap=99, seed=11)
    second = cusum_block_bootstrap(x, block_lengths=[4, 12], n_bootstrap=99, seed=11)
    after = np.random.get_state()
    assert first == second
    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert tuple(before[2:]) == tuple(after[2:])


def test_a_row_does_not_depend_on_the_other_requested_lengths():
    x = _ar1(150, 0.5, 12)
    alone = cusum_block_bootstrap(x, block_lengths=[8], n_bootstrap=99, seed=5)
    grid = cusum_block_bootstrap(x, block_lengths=[3, 8, 20], n_bootstrap=99, seed=5)
    assert grid.rows[1] == alone.rows[0]


def test_different_seeds_change_the_replicates():
    x = _ar1(150, 0.5, 13)
    a = cusum_block_bootstrap(x, block_lengths=[8], n_bootstrap=99, seed=1)
    b = cusum_block_bootstrap(x, block_lengths=[8], n_bootstrap=99, seed=2)
    assert a.rows[0].null_quantile != b.rows[0].null_quantile


# --------------------------------------------------------------------------
# Route B - size, power, trend
# --------------------------------------------------------------------------


def _rejection_rate(make, block: int, runs: int = 120) -> float:
    rejected = 0
    for i in range(runs):
        result = cusum_block_bootstrap(
            make(i), block_lengths=[block], n_bootstrap=99, seed=1000 + i
        )
        rejected += result.rows[0].p_value <= 0.05
    return rejected / runs


def test_empirical_size_on_independent_noise_is_controlled():
    rate = _rejection_rate(lambda i: np.random.default_rng(i).normal(size=200), block=4)
    assert rate <= 0.12


def test_empirical_size_on_a_persistent_constant_mean_series_is_controlled():
    rate = _rejection_rate(lambda i: _ar1(300, 0.5, 5000 + i), block=15)
    assert rate <= 0.15


def test_power_on_a_mean_shift_is_high():
    def shifted(i: int) -> np.ndarray:
        rng = np.random.default_rng(9000 + i)
        return np.r_[rng.normal(0, 1, 100), rng.normal(1.0, 1, 100)]

    assert _rejection_rate(shifted, block=4, runs=60) >= 0.9


def test_a_linear_trend_is_rejected_and_its_detrended_version_is_not():
    rng = np.random.default_rng(SEED)
    t = np.arange(400)
    noise = rng.normal(size=400)
    trended = 0.02 * t + noise
    detrended = trended - np.polyval(np.polyfit(t, trended, 1), t)
    on_trend = cusum_block_bootstrap(trended, block_lengths=[10], n_bootstrap=499, seed=1)
    on_flat = cusum_block_bootstrap(detrended, block_lengths=[10], n_bootstrap=499, seed=1)
    assert on_trend.rows[0].p_value == on_trend.p_value_resolution
    assert on_flat.rows[0].p_value > 0.05


def test_sensitivity_to_the_block_length_is_visible_on_a_persistent_series():
    x = _ar1(600, 0.9, 14) + 0.004 * np.arange(600)
    result = cusum_block_bootstrap(x, block_lengths=[2, 10, 50], n_bootstrap=199, seed=2)
    quantiles = [row.null_quantile for row in result.rows]
    assert quantiles[0] < quantiles[-1]


# --------------------------------------------------------------------------
# Route B - refusals
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"block_lengths": []},
        {"block_lengths": [0]},
        {"block_lengths": [2.5]},
        {"block_lengths": [3], "n_bootstrap": 1},
        {"block_lengths": [3], "alpha": 1.5},
        {"block_lengths": [3], "seed": -1},
        {"block_lengths": [500]},
    ],
)
def test_bootstrap_refuses_invalid_parameters(kwargs):
    with pytest.raises(
        ValueError, match=r"block_lengths|n_bootstrap|alpha|seed|cannot be supported"
    ):
        cusum_block_bootstrap(_ar1(100, 0.2, 15), **kwargs)


def test_bootstrap_refuses_short_constant_or_non_finite_series():
    with pytest.raises(ValueError, match="observations"):
        cusum_block_bootstrap(np.arange(10.0), block_lengths=[2])
    with pytest.raises(ValueError, match="constant"):
        cusum_block_bootstrap(np.ones(50), block_lengths=[2])
    with pytest.raises(ValueError, match="finite"):
        cusum_block_bootstrap(np.r_[np.arange(30.0), np.inf], block_lengths=[2])
