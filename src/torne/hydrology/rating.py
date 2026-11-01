"""The rating relation of a gauging: the stage the agency publishes, and the
discharge it publishes with it.

A hydrometric station does not measure a discharge: it measures a **stage** —
the height of the water — and the discharge is *derived* from it by a relation
the producer calls a rating curve. The producer says so itself: on this
source, the height rows carry the method "Mesurée" (measured) and the
discharge rows carry the method "Calculée" (computed).

This module fits that relation, and nothing else. The fit is an ordinary
least squares on the logarithms of the two published numbers:

    log Q = a + b · log H

which is the power law a rating curve is, written so that the fit is a
straight line. The least squares itself is the primitive the socle already
owns (`torne.methods.regression.ols`): **no new mathematics is introduced
here**.

Two things this module refuses to claim:

- **No unit is invented for the stage.** The source publishes no unit for a
  height, so the relation is expressed in the source's own numbers, and only
  the *shape* of the relation is claimed. The exponent `b` is dimensionless
  and survives any change of unit on the stage; the coefficient `a` does not,
  and is therefore reported as a number of the source's own scale.
- **No relation is claimed outside the fitted window.** The domain of
  validity of the fit is the window it was fitted on, and the published
  product says so.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)
from ..methods.regression import ols

MODEL_ID = "torne.hydrology.rating_curve"
"""The identity of the method: the relation between a stage and a discharge."""


class RatingCurveError(ValueError):
    """The pairs cannot carry a relation.

    It is raised rather than worked around: a stage or a discharge that is
    not strictly positive has no logarithm, and a relation fitted on
    substituted values would be a relation about something else.
    """


@dataclass(frozen=True, slots=True)
class RatingFit:
    """The relation fitted between a published stage and a published discharge.

    `intercept` and `slope` live in the logarithms: the relation is
    `discharge = exp(intercept) · stage ** slope`.
    """

    intercept: float
    slope: float
    slope_se: float
    r2: float
    n: int

    def discharge_of(self, stage: float) -> float:
        """The discharge the relation assigns to a stage."""
        if stage <= 0:
            raise RatingCurveError(f"a stage must be strictly positive, it is {stage}")
        return math.exp(self.intercept + self.slope * math.log(stage))

    def as_dict(self) -> dict[str, float | int]:
        """A serialisable view of the fit."""
        return {
            "intercept": self.intercept,
            "slope": self.slope,
            "slope_se": self.slope_se,
            "r2": self.r2,
            "n": self.n,
        }


def fit_rating_curve(
    stages: Sequence[float],
    discharges: Sequence[float],
) -> RatingFit:
    """Fit the relation between the published stages and discharges.

    The pairs are read as they are published: a stage without a discharge, or
    the other way round, is a pair that does not exist, and the caller is
    expected to have aligned them already.
    """
    if len(stages) != len(discharges):
        raise RatingCurveError(
            f"the pairs do not align: {len(stages)} stage(s) and {len(discharges)} discharge(s)"
        )
    if len(stages) < 3:
        raise RatingCurveError(f"three pairs at least are needed, there are {len(stages)}")

    xs: list[float] = []
    ys: list[float] = []
    for stage, discharge in zip(stages, discharges, strict=True):
        if not math.isfinite(stage) or not math.isfinite(discharge):
            raise RatingCurveError("a stage or a discharge is not a finite number")
        if stage <= 0 or discharge <= 0:
            raise RatingCurveError(
                f"the logarithms need strictly positive values, got {stage} and {discharge}"
            )
        xs.append(math.log(stage))
        ys.append(math.log(discharge))

    result = ols(xs, ys)
    return RatingFit(
        intercept=result.intercept,
        slope=result.slope,
        slope_se=result.slope_se,
        r2=result.r2,
        n=result.n,
    )


class RatingCurveModel:
    """The relation between a published stage and a published discharge.

    The model reads two aligned series — the stages and the discharges — and
    returns the discharge the relation assigns to each stage. It **fits**; it
    never forecasts, because the discharge it returns is the one the relation
    assigns to a stage that has already been measured.
    """

    def __init__(
        self,
        *,
        question: str,
        domain_of_validity: str = "",
        assumptions: Sequence[str] = (),
    ) -> None:
        """Fixes the question the method answers, and what it assumes."""
        self.spec = ModelSpec(
            model_id=MODEL_ID,
            version="1.0.0",
            question=question,
            method=(
                "Least squares on the logarithms of the published stage and the published "
                "discharge (torne.methods.regression.ols)"
            ),
            natures=(ResultNature.ESTIMATED,),
            assumptions=tuple(assumptions),
            domain_of_validity=domain_of_validity,
        )

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        seed: int | None = None,
    ) -> ModelResult:
        """Fits the relation on the pairs it is given.

        `seed` is not used: the fit is deterministic, and a method that draws
        no random number says so rather than pretending to need one.
        """
        stages = inputs.series.get("stage")
        discharges = inputs.series.get("discharge")
        if stages is None or discharges is None:
            raise RatingCurveError("the model reads two series: « stage » and « discharge »")

        fit = fit_rating_curve(stages, discharges)
        estimates = tuple(fit.discharge_of(stage) for stage in stages)

        return ModelResult(
            spec=self.spec,
            nature=ResultNature.ESTIMATED,
            parameters=params,
            produced_at=datetime.now(UTC),
            outputs={"discharge_estimated": estimates},
            diagnostics={
                "slope": fit.slope,
                "intercept": fit.intercept,
                "slope_se": fit.slope_se,
                "r2": fit.r2,
                "n": fit.n,
            },
        )


__all__ = [
    "MODEL_ID",
    "RatingCurveError",
    "RatingCurveModel",
    "RatingFit",
    "fit_rating_curve",
]
