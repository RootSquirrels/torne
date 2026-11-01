"""Local linear trend state-space filter: irregular time, estimated parameters, smoothing.

The model reconstructs a **latent state** — a level and a slope — from a noisy
observed series, and publishes a one-step-ahead forecast of the next observation
together with its predictive interval.

Model
-----
    y_t         = mu_t + eps_t,             eps_t ~ N(0, R)
    mu_{t+dt}   = mu_t + beta_t * dt + eta_t, eta_t ~ N(0, q_mu * dt)
    beta_{t+dt} = beta_t + zeta_t,           zeta_t ~ N(0, q_beta * dt)

i.e. in matrix form (state `alpha_t = (mu_t, beta_t)`), over an interval of
length `dt`:

    alpha_{t+dt} = F(dt) alpha_t + w_t,  F(dt) = [[1, dt], [0, 1]]
    Q(dt)         = diag(q_mu * dt, q_beta * dt)
    y_t           = Z alpha_t + eps_t,   Z = [1, 0],  H = R

`R` is `measurement_variance`, `q_mu` is `level_process_variance` and `q_beta`
is `slope_process_variance`. The level and slope innovations are independent:
this is an explicit parameterisation convention, chosen so that the three
variances stay separately identifiable.

With `dt = 1` everywhere, this is exactly the classical local linear trend
model of Durbin & Koopman (2012), chapter 3 §3.2.1, filtered by the recursion
of chapter 4 §4.3.

Irregular time
--------------
Physical sources are not sampled on a regular grid: a station may report every
three hours, then skip two days, then go silent for a month. The model
therefore accepts an optional **time series** named `"t"` alongside the
measured series `"y"`, both in `ModelInputs.series`.

The model has **no absolute time scale**: the process variances are expressed
per *typical* interval. The gaps between consecutive timestamps are therefore
divided by their **median**, and the resulting dimensionless ratios `dt` drive
the transition. Two consequences follow, and both are deliberate:

- a regularly spaced series yields `dt = 1` everywhere, so the result is
  **identical** to the same model run without timestamps — the irregular-time
  path is not a different model, it is the same model on a possibly uneven
  grid;
- the model does not silently assume a unit of time. A series sampled in
  seconds and the same series sampled in days give the same answer, because
  only the *relative* spacing enters the dynamics.

The normalisation factor and the raw gap range are reported in the
`diagnostics` of the result, so the transformation is auditable.

Estimated parameters
--------------------
The variances may be imposed by the caller, as in the reference implementation,
or **estimated from the data by maximum likelihood**. Estimation is conditional
on the initialisation convention described below (the initial state is fixed,
not estimated), and it is performed on the **training series only** — the model
never sees anything but the series it is given.

The estimated values are carried in the result: `ModelResult.parameters` holds
the parameters actually used, and `ModelResult.diagnostics` holds them as
numbers. They are therefore part of the published artefact, and a reader can
see which variances produced a given reconstruction instead of having to trust
the caller's defaults.

Reference: Durbin, J. & Koopman, S. J. (2012), *Time Series Analysis by State
Space Methods*, 2nd ed., Oxford University Press — chapter 4 §4.3 (filtering)
and chapter 4 §4.7 (maximum likelihood estimation).

Filtering and smoothing
-----------------------
The **filter** estimates the state from the information available up to that
instant: its output is a real-time estimate and nothing else.

The **smoother** uses the whole series, observations *after* the instant it
estimates. It is a strictly better reconstruction of a historical state — and
it is **not** an estimate that was available at that instant. The two are
therefore never mixed: they are separate outputs, and every smoothed output is
declared in `ModelResult.outputs_using_future`, which is the machine-readable
form of "this uses information from the future".

Reference: Rauch, H. E., Tung, F. & Striebel, H. J. (1965), *A Maximum
Likelihood Ratio Recursive Filter for the Kalman Model*, AIAA Journal 3(6),
1159-1166 ; Durbin & Koopman (2012), chapter 4 §4.3 ("smoothing").

Initialisation
--------------
The initial state is centred on `initial_level` (by default the first
observation) and `initial_slope` (by default 0), with a prior covariance
`diag(R, R)`: the initial state is therefore assumed known to the accuracy of
one measurement. This is an **explicit convention**, not an estimate: it is
documented here, fixed by the reference test, and applied identically on every
run. The innovation at t = 0 is zero by construction (the initial state is
centred on y_0); the filter only learns from t = 1 onwards.

Determinism
-----------
The model draws no random number: `seed` is accepted by the contract signature
and **ignored**. Two runs on the same inputs and the same parameters give
exactly the same result. No global `numpy` state is used. The maximum
likelihood estimation is a deterministic optimisation (Nelder-Mead), not a
stochastic search.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from statistics import NormalDist

import numpy as np
from scipy.optimize import minimize

from ..contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)

# Quantile normal at 97.5 %: bound of the 95 % predictive interval.
_Z_95 = NormalDist().inv_cdf(0.975)

_SERIES_NAME = "y"
_TIME_SERIES_NAME = "t"

# Lower bound of the variances explored by the maximum likelihood estimation.
# Without it, a deterministic series would drive the measurement variance to
# zero: the likelihood of a perfect fit is unbounded. The floor is a numerical
# guard, and it is reported in the diagnostics.
_MIN_VARIANCE = 1e-10


@dataclass(frozen=True, slots=True)
class _Settings:
    """Parameters of one run, once validated."""

    measurement_variance: float
    level_process_variance: float
    slope_process_variance: float
    initial_level: float
    initial_slope: float
    estimate_parameters: bool
    smooth: bool


@dataclass(frozen=True, slots=True)
class _FilterResult:
    """Everything one filtering pass produces."""

    levels: np.ndarray
    slopes: np.ndarray
    state_variances: np.ndarray
    forecasts: np.ndarray
    forecast_variances: np.ndarray
    log_likelihood: float
    filtered_states: np.ndarray
    filtered_covariances: np.ndarray
    predicted_states: np.ndarray
    predicted_covariances: np.ndarray


def _as_float(value: object, name: str) -> float:
    """Converts a parameter to a finite float, or refuses the input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"parameter '{name}' must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"parameter '{name}' must be finite, got {value!r}")
    return number


def _as_bool(value: object, name: str) -> bool:
    """Converts a parameter to a boolean, or refuses the input."""
    if not isinstance(value, bool):
        raise ValueError(f"parameter '{name}' must be a boolean, got {value!r}")
    return value


def _steps_from_times(times: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Turns timestamps into the dimensionless steps that drive the transition.

    Two step arrays are needed, and they are not the same:

    - `transition_steps[t]` is the interval that leads **into** observation `t`
      (the transition from `t-1` to `t`);
    - `forecast_steps[t]` is the interval that leads **out of** observation `t`
      (the horizon of the forecast of the next observation).

    On a regular grid both are 1, and the model is exactly the classical one.

    Returns the two step arrays, the normalisation factor (the median gap),
    and the smallest and largest raw gap.
    """
    gaps = np.diff(times)
    if np.any(gaps <= 0.0):
        raise ValueError("the time series 't' must be strictly increasing")
    scale = float(np.median(gaps))
    if scale <= 0.0:
        raise ValueError("the time series 't' must have a strictly positive median gap")
    normalised = gaps / scale

    n = int(times.size)
    transition_steps = np.ones(n, dtype=np.float64)
    transition_steps[1:] = normalised
    forecast_steps = np.ones(n, dtype=np.float64)
    forecast_steps[: n - 1] = normalised
    return transition_steps, forecast_steps, scale, float(gaps.min()), float(gaps.max())


def _filter(
    y: np.ndarray,
    *,
    steps: np.ndarray,
    forecast_steps: np.ndarray,
    settings: _Settings,
) -> _FilterResult:
    """Kalman filtering recursion, on a possibly uneven grid.

    Returns the filtered levels, slopes and state variances, the one-step
    forecasts and their predictive variances, the log-likelihood, and the
    filtered and predicted states and covariances the smoother needs.
    """
    r = settings.measurement_variance
    observation = np.array([1.0, 0.0])
    identity = np.eye(2)

    state = np.array([settings.initial_level, settings.initial_slope])
    covariance = np.diag([r, r])

    n = int(y.size)
    levels = np.empty(n, dtype=np.float64)
    slopes = np.empty(n, dtype=np.float64)
    state_variances = np.empty(n, dtype=np.float64)
    forecasts = np.empty(n, dtype=np.float64)
    forecast_variances = np.empty(n, dtype=np.float64)
    filtered_states = np.empty((n, 2), dtype=np.float64)
    filtered_covariances = np.empty((n, 2, 2), dtype=np.float64)
    predicted_states = np.empty((n, 2), dtype=np.float64)
    predicted_covariances = np.empty((n, 2, 2), dtype=np.float64)
    log_likelihood = 0.0

    for t in range(n):
        step = float(steps[t])
        transition = np.array([[1.0, step], [0.0, 1.0]])
        process = np.diag(
            [settings.level_process_variance * step, settings.slope_process_variance * step]
        )

        # Prediction: the state advances over the interval, the process noise
        # is added.
        predicted_state = transition @ state
        predicted_covariance = transition @ covariance @ transition.T + process
        predicted_states[t] = predicted_state
        predicted_covariances[t] = predicted_covariance

        # Update: the observation corrects the predicted state.
        innovation = float(y[t] - observation @ predicted_state)
        innovation_variance = float(observation @ predicted_covariance @ observation.T) + r
        gain = (predicted_covariance @ observation) / innovation_variance
        state = predicted_state + gain * innovation
        covariance = (identity - np.outer(gain, observation)) @ predicted_covariance

        levels[t] = float(state[0])
        slopes[t] = float(state[1])
        # Variance of the **filtered state**: the uncertainty of the
        # reconstructed state, distinct from the variance of the observation
        # (which also carries the measurement noise). It is what makes an
        # interval on the reconstructed state meaningful.
        state_variances[t] = float(covariance[0, 0])
        filtered_states[t] = state
        filtered_covariances[t] = covariance

        # One-step-ahead forecast: mean and predictive variance of the next
        # observation. The horizon is the interval that actually separates the
        # current observation from the next one.
        horizon = float(forecast_steps[t])
        next_transition = np.array([[1.0, horizon], [0.0, 1.0]])
        next_process = np.diag(
            [
                settings.level_process_variance * horizon,
                settings.slope_process_variance * horizon,
            ]
        )
        next_state = next_transition @ state
        next_covariance = next_transition @ covariance @ next_transition.T + next_process
        forecasts[t] = float(observation @ next_state)
        forecast_variances[t] = float(observation @ next_covariance @ observation.T) + r

        log_likelihood += -0.5 * (
            math.log(2.0 * math.pi * innovation_variance)
            + innovation * innovation / innovation_variance
        )

    return _FilterResult(
        levels=levels,
        slopes=slopes,
        state_variances=state_variances,
        forecasts=forecasts,
        forecast_variances=forecast_variances,
        log_likelihood=log_likelihood,
        filtered_states=filtered_states,
        filtered_covariances=filtered_covariances,
        predicted_states=predicted_states,
        predicted_covariances=predicted_covariances,
    )


def _smooth(
    result: _FilterResult,
    *,
    steps: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Rauch-Tung-Striebel backward smoothing pass.

    Returns the smoothed states (n x 2) and their covariances (n x 2 x 2).

    The smoothed state at time t uses every observation of the series,
    including the ones that come **after** t. It is therefore a strictly better
    reconstruction of the historical state — and it is not an estimate that was
    available at time t.
    """
    n = result.filtered_states.shape[0]
    smoothed_states = result.filtered_states.copy()
    smoothed_covariances = result.filtered_covariances.copy()

    for t in range(n - 1, 0, -1):
        step = float(steps[t])
        transition = np.array([[1.0, step], [0.0, 1.0]])
        gain = (
            result.filtered_covariances[t - 1]
            @ transition.T
            @ np.linalg.inv(result.predicted_covariances[t])
        )
        smoothed_states[t - 1] = result.filtered_states[t - 1] + gain @ (
            smoothed_states[t] - result.predicted_states[t]
        )
        smoothed_covariances[t - 1] = (
            result.filtered_covariances[t - 1]
            + gain @ (smoothed_covariances[t] - result.predicted_covariances[t]) @ gain.T
        )

    # The backward pass is numerically stable, but the diagonal of the
    # smoothed covariance can end up a hair below zero on an ill-conditioned
    # series. A variance is not negative: the round-off is clamped, so that
    # the interval built on it is a real interval.
    for t in range(n):
        for i in range(2):
            smoothed_covariances[t, i, i] = max(float(smoothed_covariances[t, i, i]), 0.0)

    return smoothed_states, smoothed_covariances


def _estimate_variances(
    y: np.ndarray,
    *,
    steps: np.ndarray,
    forecast_steps: np.ndarray,
    settings: _Settings,
) -> tuple[float, float, float]:
    """Estimates the three variances by maximum likelihood.

    The optimisation runs on the logarithms of the variances, so they stay
    positive, and it is deterministic (Nelder-Mead). The result is conditional
    on the initialisation convention: the initial state is fixed, not
    estimated.
    """
    start = np.array(
        [
            settings.measurement_variance,
            settings.level_process_variance,
            settings.slope_process_variance,
        ],
        dtype=np.float64,
    )

    def negative_log_likelihood(theta: np.ndarray) -> float:
        variances = np.exp(theta)
        settings_ = replace(
            settings,
            measurement_variance=float(variances[0]),
            level_process_variance=float(variances[1]),
            slope_process_variance=float(variances[2]),
        )
        try:
            filtered = _filter(y, steps=steps, forecast_steps=forecast_steps, settings=settings_)
        except (FloatingPointError, np.linalg.LinAlgError, ValueError):
            return math.inf
        value = -filtered.log_likelihood
        return value if math.isfinite(value) else math.inf

    optimum = minimize(
        negative_log_likelihood,
        x0=np.log(np.maximum(start, _MIN_VARIANCE)),
        method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 2000, "maxfev": 4000},
    )
    if not np.all(np.isfinite(optimum.x)):
        return (
            settings.measurement_variance,
            settings.level_process_variance,
            settings.slope_process_variance,
        )
    estimated = np.exp(optimum.x)
    floor = _MIN_VARIANCE * max(float(np.var(y)), 1.0)
    return (
        float(max(estimated[0], floor)),
        float(max(estimated[1], floor)),
        float(max(estimated[2], floor)),
    )


class LocalLinearTrendModel:
    """Local linear trend model (state-space filtering by the Kalman filter).

    The model runs through `run`; it holds no state between two runs.
    """

    required_parameters: tuple[str, ...] = (
        "measurement_variance",
        "level_process_variance",
        "slope_process_variance",
    )
    optional_parameters: tuple[str, ...] = (
        "initial_level",
        "initial_slope",
        "estimate_parameters",
        "smooth",
    )

    @property
    def spec(self) -> ModelSpec:
        """Identity, question, assumptions and domain of validity of the model."""
        return ModelSpec(
            model_id="torne.methods.kalman.local_linear_trend",
            version="0.2.0",
            question="What is the latent state (level and slope) of an observed series, and what "
            "value can be forecast for the next observation?",
            method="Kalman filter in state space, local linear trend "
            "(Durbin & Koopman 2012, ch. 3 §3.2.1 and ch. 4 §4.3), with Rauch-Tung-Striebel "
            "smoothing (Rauch, Tung & Striebel 1965) and maximum likelihood estimation of the "
            "variances (Durbin & Koopman 2012, ch. 4 §4.7)",
            natures=(ResultNature.RECONSTRUCTED, ResultNature.PREDICTED),
            assumptions=(
                "The latent system follows a local linear trend: the level advances by the "
                "current slope over the interval, and the slope drifts randomly.",
                "The observation noise is Gaussian, with a constant variance (measurement variance).",
                "The level and slope innovations are independent and Gaussian.",
                "The variances may be imposed by the caller or estimated by maximum likelihood on "
                "the training series; the estimation is conditional on the initialisation "
                "convention, the initial state being fixed rather than estimated.",
                "The observations may be irregularly spaced: the time series 't' is optional, and "
                "the intervals enter the transition as a ratio to the median interval.",
                "A smoothed output uses the observations that follow the instant it estimates: it "
                "is never a real-time estimate, and it is declared as such.",
            ),
            domain_of_validity="Scalar numerical series, regularly or irregularly spaced, of "
            "sufficient length (at least 2 observations); the latent state is assumed smooth and "
            "slowly drifting. The model says nothing about a break regime: it absorbs it into the "
            "slope.",
        )

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        """Runs the filter on the series `y`.

        `seed` is accepted to honour the contract signature and **ignored**: the
        model is entirely deterministic.

        The result is of nature `RECONSTRUCTED`: the filtered level and slope
        **reconstruct** the latent state of the observed series, from
        observations and a state-space model — they are not an observation,
        which has its own object and its own quality status. `forecast_level` is
        the **predictive mean** of the next observation, qualified by
        `intervals["forecast_level"]`; the `PREDICTED` nature is declared by the
        spec, which announces the two natures this model produces, and each
        output carries its own.
        """
        del seed  # the model draws no randomness: the seed has nothing to drive.
        series = inputs.series.get(_SERIES_NAME)
        if series is None:
            raise ValueError(
                f"the series '{_SERIES_NAME}' is missing from the inputs "
                f"(series present: {sorted(inputs.series)})"
            )
        if len(series) == 0:
            raise ValueError(f"the series '{_SERIES_NAME}' is empty")
        y = np.asarray(series, dtype=np.float64)
        if not np.isfinite(y).all():
            raise ValueError(f"the series '{_SERIES_NAME}' contains a non-finite value")

        settings = self._settings(params, default_initial_level=float(y[0]))
        steps, forecast_steps, time_scale, gap_min, gap_max = self._steps(inputs, y)

        measurement_variance = settings.measurement_variance
        level_process_variance = settings.level_process_variance
        slope_process_variance = settings.slope_process_variance
        estimated = False
        if settings.estimate_parameters:
            (
                measurement_variance,
                level_process_variance,
                slope_process_variance,
            ) = _estimate_variances(
                y,
                steps=steps,
                forecast_steps=forecast_steps,
                settings=replace(
                    settings,
                    measurement_variance=measurement_variance,
                    level_process_variance=level_process_variance,
                    slope_process_variance=slope_process_variance,
                ),
            )
            estimated = True

        effective = replace(
            settings,
            measurement_variance=measurement_variance,
            level_process_variance=level_process_variance,
            slope_process_variance=slope_process_variance,
        )
        filtered = _filter(y, steps=steps, forecast_steps=forecast_steps, settings=effective)

        intervals = tuple(
            (forecast - _Z_95 * math.sqrt(variance), forecast + _Z_95 * math.sqrt(variance))
            for forecast, variance in zip(
                filtered.forecasts, filtered.forecast_variances, strict=True
            )
        )
        # Confidence interval on the **reconstructed state**: it carries the
        # variance of the filtered state, not that of the observation. It does
        # not contain the observation itself — it contains the latent state.
        state_intervals = tuple(
            (level - _Z_95 * math.sqrt(variance), level + _Z_95 * math.sqrt(variance))
            for level, variance in zip(filtered.levels, filtered.state_variances, strict=True)
        )

        outputs: dict[str, tuple[float, ...]] = {
            "level": tuple(float(value) for value in filtered.levels),
            "slope": tuple(float(value) for value in filtered.slopes),
            "forecast_level": tuple(float(value) for value in filtered.forecasts),
        }
        output_natures = {
            "level": ResultNature.RECONSTRUCTED,
            "slope": ResultNature.RECONSTRUCTED,
            "forecast_level": ResultNature.PREDICTED,
        }
        all_intervals: dict[str, tuple[tuple[float, float], ...]] = {
            "forecast_level": intervals,
            "level": state_intervals,
        }
        outputs_using_future: tuple[str, ...] = ()

        if settings.smooth:
            smoothed_states, smoothed_covariances = _smooth(filtered, steps=steps)
            smoothed_levels = smoothed_states[:, 0]
            smoothed_slopes = smoothed_states[:, 1]
            smoothed_variances = smoothed_covariances[:, 0, 0]
            outputs["smoothed_level"] = tuple(float(value) for value in smoothed_levels)
            outputs["smoothed_slope"] = tuple(float(value) for value in smoothed_slopes)
            output_natures["smoothed_level"] = ResultNature.RECONSTRUCTED
            output_natures["smoothed_slope"] = ResultNature.RECONSTRUCTED
            all_intervals["smoothed_level"] = tuple(
                (level - _Z_95 * math.sqrt(variance), level + _Z_95 * math.sqrt(variance))
                for level, variance in zip(smoothed_levels, smoothed_variances, strict=True)
            )
            all_intervals["smoothed_slope"] = tuple(
                (slope - _Z_95 * math.sqrt(variance), slope + _Z_95 * math.sqrt(variance))
                for slope, variance in zip(
                    smoothed_slopes, smoothed_covariances[:, 1, 1], strict=True
                )
            )
            # The smoothed outputs use the observations that follow the instant
            # they estimate. They are declared, not merely named.
            outputs_using_future = ("smoothed_level", "smoothed_slope")

        diagnostics: dict[str, float | int | str | bool] = {
            "n": int(y.size),
            "log_likelihood": float(filtered.log_likelihood),
            "initial_level": settings.initial_level,
            "initial_slope": settings.initial_slope,
            "irregular_time": bool(time_scale is not None),
            "parameters_estimated": estimated,
        }
        if time_scale is not None:
            diagnostics["time_scale"] = float(time_scale)
            diagnostics["min_gap"] = float(gap_min)
            diagnostics["max_gap"] = float(gap_max)
        if estimated:
            diagnostics["estimated_measurement_variance"] = float(measurement_variance)
            diagnostics["estimated_level_process_variance"] = float(level_process_variance)
            diagnostics["estimated_slope_process_variance"] = float(slope_process_variance)

        used_parameters = ModelParameters(
            values={
                **params.as_dict(),
                "measurement_variance": float(measurement_variance),
                "level_process_variance": float(level_process_variance),
                "slope_process_variance": float(slope_process_variance),
            }
        )

        return ModelResult(
            spec=self.spec,
            nature=ResultNature.RECONSTRUCTED,
            parameters=used_parameters,
            produced_at=datetime.now(UTC),
            outputs=outputs,
            output_natures=output_natures,
            intervals=all_intervals,
            diagnostics=diagnostics,
            outputs_using_future=outputs_using_future,
        )

    def _steps(
        self,
        inputs: ModelInputs,
        y: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, float | None, float, float]:
        """The transition steps, and the time information they come from."""
        raw_times = inputs.series.get(_TIME_SERIES_NAME)
        if raw_times is None:
            ones = np.ones(y.size, dtype=np.float64)
            return ones, ones.copy(), None, 0.0, 0.0
        if len(raw_times) != y.size:
            raise ValueError(
                f"the time series '{_TIME_SERIES_NAME}' has {len(raw_times)} values "
                f"but the measured series has {y.size}"
            )
        times = np.asarray(raw_times, dtype=np.float64)
        if not np.isfinite(times).all():
            raise ValueError(f"the time series '{_TIME_SERIES_NAME}' contains a non-finite value")
        return _steps_from_times(times)

    def _settings(self, params: ModelParameters, *, default_initial_level: float) -> _Settings:
        """Validates the parameters: presence, type, domain of validity.

        `initial_level` defaults to the first observation, `initial_slope` to 0.
        """
        values = params.as_dict()
        known = set(self.required_parameters) | set(self.optional_parameters)
        unknown = sorted(set(values) - known)
        if unknown:
            raise ValueError(
                f"unknown parameter(s) for model {self.spec.model_id}: {', '.join(unknown)}; "
                f"accepted parameters: {', '.join(sorted(known))}"
            )
        missing = [name for name in self.required_parameters if name not in values]
        if missing:
            raise ValueError(f"missing required parameter(s): {', '.join(missing)}")

        measurement_variance = _as_float(values["measurement_variance"], "measurement_variance")
        if measurement_variance <= 0.0:
            raise ValueError(
                f"'measurement_variance' must be strictly positive (got {measurement_variance!r})"
            )
        level_process_variance = _as_float(
            values["level_process_variance"], "level_process_variance"
        )
        if level_process_variance < 0.0:
            raise ValueError(
                f"'level_process_variance' must be positive or zero (got {level_process_variance!r})"
            )
        slope_process_variance = _as_float(
            values["slope_process_variance"], "slope_process_variance"
        )
        if slope_process_variance < 0.0:
            raise ValueError(
                f"'slope_process_variance' must be positive or zero (got {slope_process_variance!r})"
            )

        initial_level = (
            _as_float(values["initial_level"], "initial_level")
            if "initial_level" in values
            else default_initial_level
        )
        initial_slope = (
            _as_float(values["initial_slope"], "initial_slope")
            if "initial_slope" in values
            else 0.0
        )
        estimate_parameters = (
            _as_bool(values["estimate_parameters"], "estimate_parameters")
            if "estimate_parameters" in values
            else False
        )
        smooth = _as_bool(values["smooth"], "smooth") if "smooth" in values else False
        return _Settings(
            measurement_variance=measurement_variance,
            level_process_variance=level_process_variance,
            slope_process_variance=slope_process_variance,
            initial_level=initial_level,
            initial_slope=initial_slope,
            estimate_parameters=estimate_parameters,
            smooth=smooth,
        )


__all__ = ["LocalLinearTrendModel"]
