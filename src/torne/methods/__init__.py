"""Scientific methods of TORNE.

This package holds the methods the "Models" contract can execute
(`docs/ARCHITECTURE.md` §3): a declared identity, explicit inputs and
parameters, a typed result. It contains **no registry, no engine and no
service**: a method is a parameterised function, and nothing more.

Contents
--------
- `kalman` : a state-space Kalman filter with a local linear trend — it
  reconstructs a latent state (level, slope) and publishes a one-step forecast
  with its predictive interval. It accepts irregularly spaced observations, can
  estimate its own variances on the training history, and separates the filtered
  state from the Rauch-Tung-Striebel smoothed state;
- `compare` : paired comparison of a forecast against a reference (paired
  Diebold-Mariano test, HAC variance) and search for a regime break (CUSUM);
- `scores` : strictly proper scores for probabilistic forecasts — CRPS for a
  Gaussian law and for an ensemble, the Winkler interval score, the pinball
  (quantile) score, the PIT and its calibration diagnostics;
- `dependence` : inference that survives dependence — effective sample size,
  block bootstrap, cluster bootstrap, and sensitivity to the choice of the
  independent unit;
- `multiplicity` : control of multiplicity — Benjamini-Hochberg, Bonferroni and
  the Romano-Wolf step-down max-t procedure;
- `regression`, `calibration`, `breaks`, `power` : statistical primitives
  (ordinary least squares with the CR1 clustered standard error; paired
  Diebold-Mariano test with the HAC long-run variance; mean break by CUSUM;
  minimum detectable effect, sample size and power).

The last four are taken from, and rewritten from, a historical private
repository of the owner (`athanor@6dacc87`); the header of each module carries
the exact origin, the commit, the licence status, the third-party dependencies
and the scientific reference. The first five are original implementations
written against the international statistical literature, which they cite.

Every stochastic routine in this package takes an explicit `seed` and builds its
own generator: the global random state is never touched (INV-35/INV-36 of
`docs/CORE_CONTRACTS.md`).
"""

from . import breaks, calibration, dependence, multiplicity, power, regression, scores
from .compare import (
    ComparisonReport,
    RegimeChangeReport,
    compare_forecasts,
    detect_regime_change,
    ols_trend_forecast,
)
from .dependence import (
    BootstrapReport,
    EffectiveSampleSize,
    SensitivityReport,
    block_bootstrap,
    cluster_bootstrap,
    effective_sample_size,
    independent_unit_sensitivity,
)
from .kalman import LocalLinearTrendModel
from .multiplicity import (
    MultiplicityDecision,
    benjamini_hochberg,
    bh_adjusted_p_values,
    bonferroni,
    romano_wolf_max_t,
)
from .scores import (
    CalibrationReport,
    calibration_report,
    crps_ensemble,
    crps_gaussian,
    interval_score,
    pinball_score,
    pit_gaussian,
)

__all__ = [
    "BootstrapReport",
    "CalibrationReport",
    "ComparisonReport",
    "EffectiveSampleSize",
    "LocalLinearTrendModel",
    "MultiplicityDecision",
    "RegimeChangeReport",
    "SensitivityReport",
    "benjamini_hochberg",
    "bh_adjusted_p_values",
    "block_bootstrap",
    "bonferroni",
    "breaks",
    "calibration",
    "calibration_report",
    "cluster_bootstrap",
    "compare_forecasts",
    "crps_ensemble",
    "crps_gaussian",
    "dependence",
    "detect_regime_change",
    "effective_sample_size",
    "independent_unit_sensitivity",
    "interval_score",
    "multiplicity",
    "ols_trend_forecast",
    "pinball_score",
    "pit_gaussian",
    "power",
    "regression",
    "romano_wolf_max_t",
    "scores",
]
