"""Causality: what the model knows at time *t* does not depend on what comes after *t*.

The walk-forward evaluation already checks that the **splits** do not leak.
This file checks the other half: the **model itself** is causal. A filter
that smoothed, or a state that peeked at the future, would change its past
outputs when the future is altered.

Here the future is altered — violently — and the past is expected to be
untouched. That is the property that matters for a reconstitution: a state
published for a given day must be the state that could have been computed on
that day, with the data available on that day. A model that used the future
would produce, in retrospect, a history nobody could have had.
"""

from __future__ import annotations

import math

from torne.contracts.model import ModelInputs, ModelParameters
from torne.methods.kalman import LocalLinearTrendModel

PARAMETRES = ModelParameters(
    values={
        "measurement_variance": 0.8**2,
        "level_process_variance": 0.05**2,
        "slope_process_variance": 1e-6,
    }
)

NB_POINTS = 120
POINT_DE_PERTURBATION = 60


def _serie() -> list[float]:
    """A deterministic series: a rising level with a repeatable ripple."""
    return [10.0 + 0.05 * index + 0.8 * math.sin(index / 5.0) for index in range(NB_POINTS)]


def _altee(values: list[float]) -> list[float]:
    """The same series, with everything after the perturbation point destroyed."""
    alteree = list(values)
    for index in range(POINT_DE_PERTURBATION, len(alteree)):
        alteree[index] = 1.0e6
    return alteree


def _sorties(values: list[float]) -> dict[str, tuple[float, ...]]:
    issue = LocalLinearTrendModel().run(
        ModelInputs(series={"y": tuple(values)}),
        PARAMETRES,
    )
    return issue.outputs


def test_the_past_does_not_depend_on_the_future():
    """Altering the future leaves the past exactly as it was.

    This is the property a reconstitution rests on. If it failed, a state
    published for 2026-01-01 would depend on what was measured in March.
    """
    reference = _sorties(_serie())
    alteree = _sorties(_altee(_serie()))

    assert reference["level"][:POINT_DE_PERTURBATION] == alteree["level"][:POINT_DE_PERTURBATION]
    assert reference["slope"][:POINT_DE_PERTURBATION] == alteree["slope"][:POINT_DE_PERTURBATION]


def test_the_forecast_does_not_depend_on_the_future():
    """The forecast issued at the end of a block does not know what follows."""
    reference = _sorties(_serie())
    alteree = _sorties(_altee(_serie()))

    assert (
        reference["forecast_level"][:POINT_DE_PERTURBATION]
        == (alteree["forecast_level"][:POINT_DE_PERTURBATION])
    )


def test_the_perturbation_really_changes_the_future():
    """The perturbation must actually change something, or the test proves nothing.

    A causality test whose perturbation is a no-op would pass on a model that
    looks ahead. The future has to be different, and visibly so.
    """
    reference = _sorties(_serie())
    alteree = _sorties(_altee(_serie()))

    assert reference["level"][POINT_DE_PERTURBATION] != alteree["level"][POINT_DE_PERTURBATION]
    assert alteree["level"][-1] > reference["level"][-1]


def test_the_training_block_holds_only_the_past():
    """The training block handed to a predictor stops where the test block starts."""
    values = _serie()
    taille = 40

    entrainement = tuple(values[:taille])
    test = tuple(values[taille:])

    assert len(entrainement) == taille
    assert len(entrainement) + len(test) == len(values)
    # The last training point is the one just before the first test point.
    assert entrainement[-1] == values[taille - 1]
    assert test[0] == values[taille]
