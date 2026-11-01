"""The rating relation: fitting it, and refusing what cannot be fitted."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from torne.contracts.model import ModelInputs, ModelParameters
from torne.execution.runner import execute
from torne.hydrology.rating import (
    MODEL_ID,
    RatingCurveError,
    RatingCurveModel,
    fit_rating_curve,
)

PARAMETERS = ModelParameters(values={})


def _relation(stages: list[float], *, exponent: float, coefficient: float) -> list[float]:
    """The discharges a power law assigns to the stages."""
    return [coefficient * stage**exponent for stage in stages]


def test_the_fit_recovers_the_relation_it_was_given():
    stages = [100.0, 120.0, 140.0, 160.0, 180.0, 200.0]
    discharges = _relation(stages, exponent=1.5, coefficient=2.0)
    fit = fit_rating_curve(stages, discharges)
    assert fit.slope == pytest.approx(1.5, abs=1e-9)
    assert math.exp(fit.intercept) == pytest.approx(2.0, rel=1e-9)
    assert fit.r2 == pytest.approx(1.0, abs=1e-9)
    assert fit.n == len(stages)


def test_the_fit_assigns_a_discharge_to_a_stage():
    stages = [100.0, 150.0, 200.0]
    discharges = _relation(stages, exponent=2.0, coefficient=0.5)
    fit = fit_rating_curve(stages, discharges)
    assert fit.discharge_of(200.0) == pytest.approx(discharges[-1], rel=1e-9)


def test_a_stage_that_is_not_positive_is_refused_rather_than_logged():
    with pytest.raises(RatingCurveError, match="strictly positive"):
        fit_rating_curve([100.0, 0.0, 200.0], [10.0, 0.0, 40.0])


def test_a_discharge_that_is_not_positive_is_refused():
    with pytest.raises(RatingCurveError, match="strictly positive"):
        fit_rating_curve([100.0, 150.0, 200.0], [10.0, -1.0, 40.0])


def test_pairs_that_do_not_align_are_refused():
    with pytest.raises(RatingCurveError, match="do not align"):
        fit_rating_curve([100.0, 150.0], [10.0])


def test_too_few_pairs_are_refused():
    with pytest.raises(RatingCurveError, match="three pairs at least"):
        fit_rating_curve([100.0, 150.0], [10.0, 20.0])


def test_the_model_returns_the_discharge_the_relation_assigns():
    stages = [100.0, 120.0, 140.0, 160.0]
    discharges = _relation(stages, exponent=1.2, coefficient=3.0)
    model = RatingCurveModel(question="Is the published discharge a function of the height?")
    outcome = execute(
        model,
        ModelInputs(series={"stage": tuple(stages), "discharge": tuple(discharges)}),
        PARAMETERS,
        now=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
    )
    assert outcome.result.spec.model_id == MODEL_ID
    assert outcome.result.outputs["discharge_estimated"] == pytest.approx(
        tuple(discharges), rel=1e-9
    )
    assert outcome.result.diagnostics["slope"] == pytest.approx(1.2, abs=1e-9)
    assert outcome.result.diagnostics["n"] == len(stages)


def test_the_model_refuses_to_run_without_the_two_series():
    model = RatingCurveModel(question="Is the published discharge a function of the height?")
    with pytest.raises(RatingCurveError, match="two series"):
        execute(
            model,
            ModelInputs(series={"stage": (100.0, 120.0)}),
            PARAMETERS,
            now=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
        )
