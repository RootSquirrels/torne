"""Références simples : le seuil qu'un modèle doit franchir pour être lu.

Une performance sans référence n'est pas interprétable
(`docs/RESEARCH_AND_VALIDATION.md` §6). Trois références, volontairement
naïves et déterministes :

- **persistance** — la dernière valeur *observée* est reconduite ;
- **moyenne** — la moyenne des valeurs *observées* est reconduite ;
- **dérive** — la dernière valeur observée est reconduite en lui ajoutant la
  pente moyenne de l'historique.

Chacune s'ajuste **uniquement** sur le bloc d'entraînement qu'elle reçoit :
la période test ne l'atteint pas. Aucune de ces références ne lit le futur.

**Une absence n'est pas un zéro.** Un bloc d'entraînement peut porter des
absences (`None`) : une référence s'ajuste alors sur ses seules valeurs
observées, et elle ne comble rien. La dérive est la seule qui tienne compte
du temps : sa pente est rapportée à l'écart d'**indice** entre la première
et la dernière valeur observée, non au nombre de valeurs observées — sans
quoi un simple trou dans la série gonflerait la pente.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def persistence_forecast(train: Sequence[float | None], horizon: int) -> tuple[float, ...]:
    """Reconduit la dernière valeur observée de l'entraînement sur l'horizon demandé.

    Une absence ne devient pas un zéro : c'est la dernière valeur **observée**
    qui est reconduite, et l'appelant ignore où elle se trouve.
    """
    values, _, steps = _prepare(train, horizon)
    return (values[-1],) * steps


def mean_forecast(train: Sequence[float | None], horizon: int) -> tuple[float, ...]:
    """Reconduit la moyenne des valeurs observées de l'entraînement.

    La moyenne porte sur les seules valeurs observées : une absence n'y
    entre pas, et n'y entre pas non plus comme un zéro.
    """
    values, _, steps = _prepare(train, horizon)
    return (math.fsum(values) / len(values),) * steps


def drift_forecast(train: Sequence[float | None], horizon: int) -> tuple[float, ...]:
    """Reconduit la dernière valeur observée en lui ajoutant la pente moyenne.

    La pente est `(dernière - première) / (écart d'indice)`, et la prévision
    à l'échéance `h` vaut `dernière + h * pente`. L'écart d'indice est la
    distance temporelle entre la première et la dernière valeur observée :
    c'est lui qui rend la pente comparable d'une série à l'autre. Deux points
    observés au moins sont exigés : sans eux, aucune dérive n'est estimable,
    et la référence le dit au lieu de rendre une valeur fausse.
    """
    values, indices, steps = _prepare(train, horizon)
    if len(values) < 2:
        raise ValueError(
            f"la dérive exige au moins deux points d'entraînement, elle en a {len(values)}"
        )
    slope = (values[-1] - values[0]) / (indices[-1] - indices[0])
    return tuple(values[-1] + slope * (step + 1) for step in range(steps))


def _prepare(
    train: Sequence[float | None], horizon: int
) -> tuple[tuple[float, ...], tuple[int, ...], int]:
    """Valide l'historique et l'horizon, et isole les valeurs observées.

    Renvoie les valeurs observées, leurs indices d'origine, et l'horizon.
    Les indices d'origine sont conservés : ils disent où les valeurs se
    trouvent, et la dérive en a besoin pour rapporter la pente au temps.
    """
    if horizon < 1:
        raise ValueError(f"horizon doit valoir au moins 1, il vaut {horizon}")
    values = tuple(train)
    if not values:
        raise ValueError("une référence ne s'ajuste pas sur un bloc d'entraînement vide")
    observes = tuple((index, valeur) for index, valeur in enumerate(values) if valeur is not None)
    if not observes:
        raise ValueError(
            "une référence ne s'ajuste pas sur un bloc d'entraînement sans valeur observée"
        )
    return (
        tuple(valeur for _, valeur in observes),
        tuple(index for index, _ in observes),
        horizon,
    )


__all__ = ["drift_forecast", "mean_forecast", "persistence_forecast"]
