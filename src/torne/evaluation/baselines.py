"""Références simples : le seuil qu'un modèle doit franchir pour être lu.

Une performance sans référence n'est pas interprétable
(`docs/RESEARCH_AND_VALIDATION.md` §6). Trois références, volontairement
naïves et déterministes :

- **persistance** — la dernière valeur observée est reconduite ;
- **moyenne** — la moyenne de l'historique est reconduite ;
- **dérive** — la dernière valeur est reconduite en lui ajoutant la pente
  moyenne de l'historique.

Chacune s'ajuste **uniquement** sur le bloc d'entraînement qu'elle reçoit :
la période test ne l'atteint pas. Aucune de ces références ne lit le futur.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def persistence_forecast(train: Sequence[float], horizon: int) -> tuple[float, ...]:
    """Reconduit la dernière valeur de l'entraînement sur l'horizon demandé."""
    values, steps = _prepare(train, horizon)
    return (values[-1],) * steps


def mean_forecast(train: Sequence[float], horizon: int) -> tuple[float, ...]:
    """Reconduit la moyenne de l'entraînement sur l'horizon demandé."""
    values, steps = _prepare(train, horizon)
    return (math.fsum(values) / len(values),) * steps


def drift_forecast(train: Sequence[float], horizon: int) -> tuple[float, ...]:
    """Reconduit la dernière valeur en lui ajoutant la pente moyenne.

    La pente est `(dernier - premier) / (n - 1)`, et la prévision à l'échéance
    `h` vaut `dernier + h * pente`. Deux points au moins sont exigés : sans
    eux, aucune dérive n'est estimable, et la référence le dit au lieu de
    rendre une valeur fausse.
    """
    values, steps = _prepare(train, horizon)
    if len(values) < 2:
        raise ValueError(
            f"la dérive exige au moins deux points d'entraînement, elle en a {len(values)}"
        )
    slope = (values[-1] - values[0]) / (len(values) - 1)
    return tuple(values[-1] + slope * (step + 1) for step in range(steps))


def _prepare(train: Sequence[float], horizon: int) -> tuple[tuple[float, ...], int]:
    """Valide l'historique et l'horizon, et renvoie l'historique figé."""
    if horizon < 1:
        raise ValueError(f"horizon doit valoir au moins 1, il vaut {horizon}")
    values = tuple(train)
    if not values:
        raise ValueError("une référence ne s'ajuste pas sur un bloc d'entraînement vide")
    return values, horizon


__all__ = ["drift_forecast", "mean_forecast", "persistence_forecast"]
