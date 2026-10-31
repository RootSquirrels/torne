"""Métriques d'erreur et décompte exhaustif des points écartés.

Trois métriques d'erreur (RMSE, MAE, biais signé) et une métrique de
calibration (couverture d'intervalle). Elles partagent la même règle de
comptage : **un point écarté est compté et qualifié, jamais perdu**.

Un `MetricReport` porte toujours les cinq compteurs, et l'invariant
`n_used + n_missing + n_invalid + n_out_of_domain == n_total` tient par
construction. Une absence n'est pas un zéro : elle n'entre pas dans le calcul,
et elle ne se confond avec aucun autre état (INV-19).

Chaque métrique porte en outre son **incertitude explicite** : un intervalle
de confiance et la taille effective de l'échantillon qui le fonde
(`torne.evaluation.uncertainty`). Un nombre nu ne dit pas ce qu'il faut de
lui : `SPEC-010:139` exige que les comparaisons portent l'incertitude des
métriques et la taille effective de l'échantillon.

Enfin, une valeur non finie n'est pas une mesure : elle est refusée, comme
les entrées non finies le sont dans l'exécution. Une métrique muette qui
renverrait `NaN` confondrait une défaillance et un résultat.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..contracts.derived import Uncertainty
from ..contracts.validity import PointValidity
from .uncertainty import NIVEAU, confidence_interval


@dataclass(frozen=True, slots=True)
class MetricReport:
    """Valeur d'une métrique, décompte des points considérés et incertitude.

    `n_total` est le nombre de points soumis à la métrique, `n_used` le
    nombre de ceux qui y entrent effectivement ; les trois autres compteurs
    qualifient les points écartés (absent, invalide, hors domaine). L'identité
    des compteurs est vérifiée à la construction.

    `uncertainty` qualifie la valeur : c'est l'objet d'incertitude du contrat
    (`torne.contracts.derived.Uncertainty`), et il porte l'intervalle de
    confiance de la valeur. `n_effective` est la taille effective de
    l'échantillon qui fonde cet intervalle — le nombre de points
    indépendants équivalents aux points utilisés. Les deux valent `None`
    quand l'intervalle n'est pas définissable, c'est-à-dire quand moins de
    deux points entrent dans la métrique.
    """

    name: str
    value: float
    n_total: int
    n_used: int
    n_missing: int
    n_invalid: int
    n_out_of_domain: int
    uncertainty: Uncertainty | None = None
    n_effective: float | None = None

    def __post_init__(self) -> None:
        total = self.n_used + self.n_missing + self.n_invalid + self.n_out_of_domain
        if total != self.n_total:
            raise ValueError(
                "n_used + n_missing + n_invalid + n_out_of_domain doit valoir n_total : "
                f"{self.n_used} + {self.n_missing} + {self.n_invalid} + "
                f"{self.n_out_of_domain} != {self.n_total}"
            )
        if self.uncertainty is None and self.n_effective is not None:
            raise ValueError(
                "n_effective sans incertitude : la taille effective accompagne l'intervalle"
            )
        if self.uncertainty is not None and self.n_effective is None:
            raise ValueError(
                "une incertitude sans taille effective : l'intervalle doit dire sur quoi"
            )


def rmse(
    actual: Sequence[float],
    predicted: Sequence[float],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur quadratique moyenne sur les seuls points valides.

    `sqrt(mean((actual - predicted)^2))`. Un point absent, invalide ou hors
    domaine n'entre pas dans la moyenne, mais reste compté.

    L'incertitude est celle de la moyenne des carrés, ramenée à l'échelle du
    RMSE par la racine : la racine étant croissante, l'image de l'intervalle
    encadre encore la valeur.
    """
    actuals, predictions = _align(actual, predicted)
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    pertes = [(actuals[index] - predictions[index]) ** 2 for index in kept]
    value = math.sqrt(math.fsum(pertes) / len(kept)) if kept else math.nan
    return _report("rmse", value, kept, missing, invalid, out_of_domain, pertes, _racine)


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
    pertes = [abs(actuals[index] - predictions[index]) for index in kept]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("mae", value, kept, missing, invalid, out_of_domain, pertes, _non_negative)


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
    pertes = [actuals[index] - predictions[index] for index in kept]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("bias", value, kept, missing, invalid, out_of_domain, pertes)


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
    actuals = _finite(tuple(actual), "actual")
    bounds = _bounds(intervals, len(actuals))
    kept, missing, invalid, out_of_domain = _keep(validity, len(actuals))
    pertes = [
        1.0 if bounds[index][0] <= actuals[index] <= bounds[index][1] else 0.0 for index in kept
    ]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("coverage", value, kept, missing, invalid, out_of_domain, pertes, _proportion)


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
    return _finite(tuple(actual), "actual"), _finite(tuple(predicted), "predicted")


def _finite(values: tuple[float, ...], name: str) -> tuple[float, ...]:
    """Refuse une valeur non finie : elle n'est pas une mesure.

    Un `NaN` ou un infini n'est ni une observation, ni une prévision : la
    métrique qui l'accueillerait rendrait `NaN` en silence, et une
    défaillance passerait pour un résultat.
    """
    for index, valeur in enumerate(values):
        try:
            finie = math.isfinite(valeur)
        except TypeError as exc:
            raise ValueError(
                f"{name} : la valeur à l'indice {index} n'est pas un nombre ({valeur!r})"
            ) from exc
        if not finie:
            raise ValueError(f"{name} : la valeur à l'indice {index} n'est pas finie ({valeur!r})")
    return values


def _bounds(
    intervals: Sequence[tuple[float, float]], expected: int
) -> tuple[tuple[float, float], ...]:
    """Valide les intervalles : un couple par point, bornes ordonnées et finies."""
    if len(intervals) != expected:
        raise ValueError(
            f"intervals doit porter un intervalle par point : {len(intervals)} pour {expected}"
        )
    bounds: list[tuple[float, float]] = []
    for interval in intervals:
        if len(interval) != 2:
            raise ValueError("un intervalle de couverture est un couple (borne_basse, borne_haute)")
        low, high = float(interval[0]), float(interval[1])
        if not math.isfinite(low) or not math.isfinite(high):
            raise ValueError(f"un intervalle de coverage exige des bornes finies : ({low}, {high})")
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


def _racine(valeur: float) -> float:
    """Racine carrée d'une borne : le RMSE est la racine de la moyenne des carrés."""
    return math.sqrt(max(valeur, 0.0))


def _non_negative(valeur: float) -> float:
    """Une moyenne de pertes non négatives ne peut pas être négative."""
    return max(valeur, 0.0)


def _proportion(valeur: float) -> float:
    """Une proportion de points couverts est comprise entre 0 et 1."""
    return min(max(valeur, 0.0), 1.0)


def _report(
    name: str,
    value: float,
    kept: list[int],
    missing: int,
    invalid: int,
    out_of_domain: int,
    pertes: Sequence[float] = (),
    transformation: Callable[[float], float] | None = None,
) -> MetricReport:
    """Construit le rapport : les compteurs décrivent tous les points vus.

    `pertes` est la série des pertes point à point des points retenus : sa
    moyenne est la grandeur estimée (la racine pour le RMSE), et c'est sur elle
    que porte l'intervalle de confiance. `transformation` ramène les bornes de
    cet intervalle à l'échelle de la métrique ; elle est croissante, donc
    l'intervalle transformé encadre encore la valeur.
    """
    interval = confidence_interval(pertes)
    uncertainty = None
    n_effective = None
    if interval is not None:
        bas = interval.low if transformation is None else transformation(interval.low)
        haut = interval.high if transformation is None else transformation(interval.high)
        n_effective = interval.n_effective
        uncertainty = Uncertainty.from_interval(
            statement=(
                f"intervalle de confiance à {int(NIVEAU * 100)} % de « {name} » ; "
                f"variance HAC (Newey-West) sur {len(pertes)} pertes ; "
                f"taille effective {n_effective:.1f} points"
            ),
            bounds=(bas, haut),
        )
    return MetricReport(
        name=name,
        value=value,
        n_total=len(kept) + missing + invalid + out_of_domain,
        n_used=len(kept),
        n_missing=missing,
        n_invalid=invalid,
        n_out_of_domain=out_of_domain,
        uncertainty=uncertainty,
        n_effective=n_effective,
    )


__all__ = [
    "MetricReport",
    "bias",
    "coverage",
    "evaluate_all",
    "mae",
    "rmse",
]
