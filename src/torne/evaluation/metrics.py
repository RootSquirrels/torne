"""Métriques d'erreur et décompte exhaustif des points écartés.

Trois métriques d'erreur (RMSE, MAE, biais signé) et une métrique de
calibration (couverture d'intervalle). Elles partagent la même règle de
comptage : **un point écarté est compté et qualifié, jamais perdu**.

Un `MetricReport` porte toujours les cinq compteurs, et l'invariant
`n_used + n_missing + n_invalid + n_out_of_domain == n_total` tient par
construction. Une absence n'est pas un zéro : elle n'entre pas dans le calcul,
et elle ne se confond avec aucun autre état (INV-19).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..contracts.validity import PointValidity


@dataclass(frozen=True, slots=True)
class MetricReport:
    """Valeur d'une métrique et décompte des points considérés.

    `n_total` est le nombre de points soumis à la métrique, `n_used` le
    nombre de ceux qui y entrent effectivement ; les trois autres compteurs
    qualifient les points écartés (absent, invalide, hors domaine). L'identité
    des compteurs est vérifiée à la construction.
    """

    name: str
    value: float
    n_total: int
    n_used: int
    n_missing: int
    n_invalid: int
    n_out_of_domain: int

    def __post_init__(self) -> None:
        total = self.n_used + self.n_missing + self.n_invalid + self.n_out_of_domain
        if total != self.n_total:
            raise ValueError(
                "n_used + n_missing + n_invalid + n_out_of_domain doit valoir n_total : "
                f"{self.n_used} + {self.n_missing} + {self.n_invalid} + "
                f"{self.n_out_of_domain} != {self.n_total}"
            )


def rmse(
    actual: Sequence[float],
    predicted: Sequence[float],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur quadratique moyenne sur les seuls points valides.

    `sqrt(mean((actual - predicted)^2))`. Un point absent, invalide ou hors
    domaine n'entre pas dans la moyenne, mais reste compté.
    """
    actuals, predictions = _align(actual, predicted)
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    if kept:
        value = math.sqrt(
            math.fsum((actuals[index] - predictions[index]) ** 2 for index in kept) / len(kept)
        )
    else:
        value = math.nan
    return _report("rmse", value, kept, missing, invalid, out_of_domain)


def mae(
    actual: Sequence[float],
    predicted: Sequence[float],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur absolue moyenne sur les seuls points valides.

    `mean(|actual - predicted|)`. L'erreur absolue ne porte pas de signe :
    c'est le biais qui le porte.
    """
    actuals, predictions = _align(actual, predicted)
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    if kept:
        value = math.fsum(abs(actuals[index] - predictions[index]) for index in kept) / len(kept)
    else:
        value = math.nan
    return _report("mae", value, kept, missing, invalid, out_of_domain)


def bias(
    actual: Sequence[float],
    predicted: Sequence[float],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur moyenne signée sur les seuls points valides.

    `mean(actual - predicted)` : la valeur est **négative** quand le modèle
    sur-prédit, **positive** quand il sous-prédit. Le signe est celui de
    l'erreur signée `actual - predicted`, énoncé ici pour qu'il ne soit
    jamais supposé.
    """
    actuals, predictions = _align(actual, predicted)
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    if kept:
        value = math.fsum(actuals[index] - predictions[index] for index in kept) / len(kept)
    else:
        value = math.nan
    return _report("bias", value, kept, missing, invalid, out_of_domain)


def coverage(
    actual: Sequence[float],
    intervals: Sequence[tuple[float, float]],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Fréquence à laquelle l'intervalle annoncé contient l'observation.

    Un intervalle est le couple `(borne_basse, borne_haute)` ; il est fermé, les
    bornes sont incluses. La valeur est la part des points valides couverts.
    C'est la vérification de calibration au sens de
    `docs/RESEARCH_AND_VALIDATION.md` §6 : une incertitude annoncée doit
    contenir l'observation à la fréquence promise.
    """
    actuals = tuple(actual)
    bounds = _bounds(intervals, len(actuals))
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    if kept:
        covered = math.fsum(
            1 for index in kept if bounds[index][0] <= actuals[index] <= bounds[index][1]
        )
        value = covered / len(kept)
    else:
        value = math.nan
    return _report("coverage", value, kept, missing, invalid, out_of_domain)


def evaluate_all(
    actual: Sequence[float],
    predicted: Sequence[float],
    intervals: Sequence[tuple[float, float]] | None = None,
    validity: Sequence[PointValidity] | None = None,
) -> dict[str, MetricReport]:
    """Calcule les métriques d'erreur, et la couverture si des intervalles sont fournis.

    L'ordre des clés est stable : `rmse`, `mae`, `bias`, puis `coverage`. Deux
    évaluations identiques donnent deux dictionnaires identiques.
    """
    reports = {
        "rmse": rmse(actual, predicted, validity),
        "mae": mae(actual, predicted, validity),
        "bias": bias(actual, predicted, validity),
    }
    if intervals is not None:
        reports["coverage"] = coverage(actual, intervals, validity)
    return reports


def _align(
    actual: Sequence[float], predicted: Sequence[float]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Aligne les deux séries point à point, ou refuse des longueurs différentes."""
    if len(actual) != len(predicted):
        raise ValueError(
            "actual et predicted doivent porter un point chacun : "
            f"{len(actual)} et {len(predicted)}"
        )
    return tuple(actual), tuple(predicted)


def _bounds(
    intervals: Sequence[tuple[float, float]], expected: int
) -> tuple[tuple[float, float], ...]:
    """Valide les intervalles : un couple par point, bornes ordonnées."""
    if len(intervals) != expected:
        raise ValueError(
            f"intervals doit porter un intervalle par point : {len(intervals)} pour {expected}"
        )
    bounds: list[tuple[float, float]] = []
    for interval in intervals:
        if len(interval) != 2:
            raise ValueError("un intervalle de couverture est un couple (borne_basse, borne_haute)")
        low, high = float(interval[0]), float(interval[1])
        if low > high:
            raise ValueError(
                f"un intervalle de couverture exige borne_basse <= borne_haute : ({low}, {high})"
            )
        bounds.append((low, high))
    return tuple(bounds)


def _keep(validity: Sequence[PointValidity] | None, total: int) -> tuple[list[int], int, int, int]:
    """Sépare les points retenus des points écartés, et qualifie chaque écart.

    Renvoie les indices des points valides, puis les compteurs absent, invalide
    et hors domaine. Un état inconnu est refusé : il ne doit jamais être
    rangé par défaut dans une catégorie.
    """
    if validity is None:
        states: Sequence[PointValidity] = (PointValidity.VALID,) * total
    else:
        if len(validity) != total:
            raise ValueError(
                f"validity doit porter un état par point : {len(validity)} pour {total}"
            )
        states = validity

    kept: list[int] = []
    missing = 0
    invalid = 0
    out_of_domain = 0
    for index, state in enumerate(states):
        if state == PointValidity.VALID:
            kept.append(index)
        elif state == PointValidity.MISSING:
            missing += 1
        elif state == PointValidity.INVALID:
            invalid += 1
        elif state == PointValidity.OUT_OF_DOMAIN:
            out_of_domain += 1
        else:
            raise ValueError(f"état de validité inconnu : {state!r}")
    return kept, missing, invalid, out_of_domain


def _report(
    name: str,
    value: float,
    kept: list[int],
    missing: int,
    invalid: int,
    out_of_domain: int,
) -> MetricReport:
    """Construit le rapport : les compteurs décrivent tous les points vus."""
    return MetricReport(
        name=name,
        value=value,
        n_total=len(kept) + missing + invalid + out_of_domain,
        n_used=len(kept),
        n_missing=missing,
        n_invalid=invalid,
        n_out_of_domain=out_of_domain,
    )


__all__ = [
    "MetricReport",
    "bias",
    "coverage",
    "evaluate_all",
    "mae",
    "rmse",
]
