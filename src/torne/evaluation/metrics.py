"""Métriques d'erreur et décompte exhaustif des points écartés.

Trois métriques d'erreur (RMSE, MAE, biais signé) et une métrique de
calibration (couverture d'intervalle). Elles partagent la même règle de
comptage : **un point écarté est compté et qualifié, jamais perdu**.

Un `MetricReport` porte toujours les cinq compteurs, et l'invariant
`n_used + n_missing + n_invalid + n_out_of_domain == n_total` tient par
construction. Une absence n'est pas un zéro : elle n'entre pas dans le calcul,
et elle ne se confond avec aucun autre état (INV-19).

**L'absence est `None`, jamais un nombre.** L'appelant n'a plus à fabriquer
une valeur numérique pour un point absent : il la laisse absente. Aucun
`0.0` de remplacement, aucune interpolation, aucune estimation : rien de tel
n'entre ici, ni à l'entrée, ni dans le calcul, ni dans le rapport.

La cohérence entre la valeur et l'état déclaré est **exigée, pas tolérée** :

- une valeur absente (`None`) alors que la validité la déclare valide est
  une incohérence : elle est refusée, l'indice nommé ;
- une valeur présente alors que la validité la déclare absente est une
  incohérence aussi : l'absence se déclare par `None`, jamais par une valeur
  inventée.

Sans état déclaré, la présence de la valeur suffit : un point dont l'une des
valeurs manque n'a pas de perte, il n'entre pas dans le calcul et il est
compté comme absent. Avec un état déclaré, l'état qualifie le point écarté ;
un point déclaré valide mais dont une valeur manque est compté comme absent,
car aucune perte ne peut en être tirée.

Chaque métrique porte en outre son **incertitude explicite** : un intervalle
de confiance et la taille effective de l'échantillon qui le fonde
(`torne.evaluation.uncertainty`). Un nombre nu ne dit pas ce qu'il faut de
lui : `SPEC-010:139` exige que les comparaisons portent « incertitude des
métriques, intervalles de confiance ou bootstrap adapté à la dépendance, et
taille effective de l'échantillon ». L'intervalle employé ici est celui de
la variance de long terme HAC (Newey-West) : voir `uncertainty` pour la
méthode exacte et ses limites.

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

    `n_missing` compte les points **sans valeur exploitable** : observation
    absente, prévision absente (le modèle s'est abstenu), intervalle non
    annoncé. Ces points ne sont ni perdus, ni transformés en zéro.

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


def exiger_coherence(
    valeurs: Sequence[float | None],
    validite: Sequence[PointValidity] | None,
) -> None:
    """Exige que la valeur et l'état déclaré disent la même chose.

    Une valeur absente (`None`) ne peut pas être déclarée valide : le point
    serait à la fois absent pour le calcul et présent pour lui. Et une valeur
    présente ne peut pas être déclarée absente : l'appelant aurait fabriqué
    un nombre pour une absence (INV-19). Les deux incohérences sont refusées
    ici, l'indice nommé, plutôt que silencieusement écartées.

    Sans état déclaré, il n'y a rien à confronter : la présence de la valeur
    suffit, et l'absence se déduit d'elle-même.
    """
    if validite is None:
        return
    if len(validite) != len(valeurs):
        raise ValueError(
            f"validity doit porter un état par point : {len(validite)} pour {len(valeurs)}"
        )
    for index, (valeur, etat) in enumerate(zip(valeurs, validite, strict=True)):
        if etat == PointValidity.VALID and valeur is None:
            raise ValueError(
                f"incohérence à l'indice {index} : une valeur absente (None) ne peut pas "
                "être déclarée valide"
            )
        if etat == PointValidity.MISSING and valeur is not None:
            raise ValueError(
                f"incohérence à l'indice {index} : une absence se déclare par None, "
                "jamais par une valeur inventée"
            )


def rmse(
    actual: Sequence[float | None],
    predicted: Sequence[float | None],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur quadratique moyenne sur les seuls points valides.

    `sqrt(mean((actual - predicted)^2))`. Un point absent, invalide ou hors
    domaine n'entre pas dans la moyenne, mais reste compté.

    **Une absence est `None`.** Un point dont l'observation ou la prévision
    manque n'a pas de perte : il est compté comme absent, et sa valeur n'est
    jamais remplacée par un zéro.

    L'incertitude est celle de la moyenne des carrés, ramenée à l'échelle du
    RMSE par la racine : la racine étant croissante, l'image de l'intervalle
    encadre encore la valeur.
    """
    actuals, predictions = _align(actual, predicted)
    exiger_coherence(actuals, validity)
    present = [
        observe is not None and prevu is not None
        for observe, prevu in zip(actuals, predictions, strict=True)
    ]
    kept, missing, invalid, out_of_domain = _retenir(present, validity)
    pertes = [_ecart(actuals[index], predictions[index]) ** 2 for index in kept]
    value = math.sqrt(math.fsum(pertes) / len(kept)) if kept else math.nan
    return _report("rmse", value, kept, missing, invalid, out_of_domain, pertes, _racine)


def mae(
    actual: Sequence[float | None],
    predicted: Sequence[float | None],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur absolue moyenne sur les seuls points valides.

    `mean(|actual - predicted|)`. L'erreur absolue ne porte pas de signe :
    c'est le biais qui le porte.

    **Une absence est `None`** : un point sans observation ou sans prévision
    n'a pas d'erreur absolue, il est compté comme absent.
    """
    actuals, predictions = _align(actual, predicted)
    exiger_coherence(actuals, validity)
    present = [
        observe is not None and prevu is not None
        for observe, prevu in zip(actuals, predictions, strict=True)
    ]
    kept, missing, invalid, out_of_domain = _retenir(present, validity)
    pertes = [abs(_ecart(actuals[index], predictions[index])) for index in kept]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("mae", value, kept, missing, invalid, out_of_domain, pertes, _non_negative)


def bias(
    actual: Sequence[float | None],
    predicted: Sequence[float | None],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Erreur moyenne signée sur les seuls points valides.

    `mean(actual - predicted)` : la valeur est **négative** quand le modèle
    sur-prédit, **positive** quand il sous-prédit. Le signe est celui de
    l'erreur signée `actual - predicted`, énoncé ici pour qu'il ne soit
    jamais supposé.

    **Une absence est `None`** : un point sans observation ou sans prévision
    n'a pas d'erreur signée, il est compté comme absent.
    """
    actuals, predictions = _align(actual, predicted)
    exiger_coherence(actuals, validity)
    present = [
        observe is not None and prevu is not None
        for observe, prevu in zip(actuals, predictions, strict=True)
    ]
    kept, missing, invalid, out_of_domain = _retenir(present, validity)
    pertes = [_ecart(actuals[index], predictions[index]) for index in kept]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("bias", value, kept, missing, invalid, out_of_domain, pertes)


def coverage(
    actual: Sequence[float | None],
    intervals: Sequence[tuple[float, float] | None],
    validity: Sequence[PointValidity] | None = None,
) -> MetricReport:
    """Fréquence à laquelle l'intervalle annoncé contient l'observation.

    Un intervalle est le couple `(borne_basse, borne_haute)` ; il est fermé, les
    bornes sont incluses. La valeur est la part des points valides couverts.
    C'est la vérification de calibration au sens de
    `docs/RESEARCH_AND_VALIDATION.md` §6 : une incertitude annoncée doit
    contenir l'observation à la fréquence promise.

    **Une absence est `None`** : un point sans observation n'a rien à
    vérifier, et un point sans intervalle annoncé non plus. L'un et l'autre
    sont comptés comme absents, jamais comme couverts.
    """
    actuals = _finite(tuple(actual), "actual")
    bornes = _bounds(intervals, len(actuals))
    exiger_coherence(actuals, validity)
    present = [
        observe is not None and borne is not None
        for observe, borne in zip(actuals, bornes, strict=True)
    ]
    kept, missing, invalid, out_of_domain = _retenir(present, validity)
    pertes = [_couvert(actuals[index], bornes[index]) for index in kept]
    value = math.fsum(pertes) / len(kept) if kept else math.nan
    return _report("coverage", value, kept, missing, invalid, out_of_domain, pertes, _proportion)


def evaluate_all(
    actual: Sequence[float | None],
    predicted: Sequence[float | None],
    intervals: Sequence[tuple[float, float] | None] | None = None,
    validity: Sequence[PointValidity] | None = None,
) -> dict[str, MetricReport]:
    """Calcule les métriques d'erreur, et la couverture si des intervalles sont fournis.

    L'ordre des clés est stable : `rmse`, `mae`, `bias`, puis `coverage`. Deux
    évaluations identiques donnent deux dictionnaires identiques.

    Les séries admettent des absences (`None`) : un point absent n'entre dans
    aucun calcul et reste compté comme absent.
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
    actual: Sequence[float | None], predicted: Sequence[float | None]
) -> tuple[tuple[float | None, ...], tuple[float | None, ...]]:
    """Aligne les deux séries point à point, ou refuse des longueurs différentes."""
    if len(actual) != len(predicted):
        raise ValueError(
            "actual et predicted doivent porter un point chacun : "
            f"{len(actual)} et {len(predicted)}"
        )
    return _finite(tuple(actual), "actual"), _finite(tuple(predicted), "predicted")


def _finite(values: tuple[float | None, ...], name: str) -> tuple[float | None, ...]:
    """Refuse une valeur non finie : elle n'est pas une mesure.

    Un `NaN` ou un infini n'est ni une observation, ni une prévision : la
    métrique qui l'accueillerait rendrait `NaN` en silence, et une
    défaillance passerait pour un résultat.

    `None` n'est pas une valeur non finie : c'est une absence, et elle est
    traitée comme telle — jamais convertie en zéro.
    """
    for index, valeur in enumerate(values):
        if valeur is None:
            continue
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
    intervals: Sequence[tuple[float, float] | None], expected: int
) -> tuple[tuple[float, float] | None, ...]:
    """Valide les intervalles : un couple par point, bornes ordonnées et finies.

    `None` est admis : un point sans intervalle annoncé n'a rien à vérifier,
    il est compté comme absent.
    """
    if len(intervals) != expected:
        raise ValueError(
            f"intervals doit porter un intervalle par point : {len(intervals)} pour {expected}"
        )
    bounds: list[tuple[float, float] | None] = []
    for interval in intervals:
        if interval is None:
            bounds.append(None)
            continue
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


def _retenir(
    present: Sequence[bool],
    validity: Sequence[PointValidity] | None,
) -> tuple[list[int], int, int, int]:
    """Sépare les points retenus des points écartés, et qualifie chaque écart.

    Renvoie les indices des points retenus, puis les compteurs absent, invalide
    et hors domaine. Un état inconnu est refusé : il ne doit jamais être
    rangé par défaut dans une catégorie.

    Sans état déclaré, la présence des valeurs décide : un point incomplet est
    compté comme absent. Avec un état déclaré, l'état qualifie le point
    écarté ; un point déclaré valide mais incomplet est compté comme absent,
    car aucune perte ne peut en être tirée.
    """
    total = len(present)
    if validity is None:
        states: Sequence[PointValidity] | None = None
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
    for index in range(total):
        if states is None:
            if present[index]:
                kept.append(index)
            else:
                missing += 1
            continue
        state = states[index]
        if state == PointValidity.VALID:
            if present[index]:
                kept.append(index)
            else:
                missing += 1
        elif state == PointValidity.MISSING:
            missing += 1
        elif state == PointValidity.INVALID:
            invalid += 1
        elif state == PointValidity.OUT_OF_DOMAIN:
            out_of_domain += 1
        else:
            raise ValueError(f"état de validité inconnu : {state!r}")
    return kept, missing, invalid, out_of_domain


def _ecart(actual: float | None, predicted: float | None) -> float:
    """Écart signé entre l'observation et la prévision d'un point retenu.

    Un point retenu porte toujours ses deux valeurs : `_retenir` l'a vérifié.
    Le garde-fou reste là pour qu'une régression future ne transforme pas
    une absence en zéro sans le dire.
    """
    if actual is None or predicted is None:  # pragma: no cover - impossible par construction
        raise ValueError("un point retenu porte toujours ses deux valeurs")
    return actual - predicted


def _couvert(actual: float | None, interval: tuple[float, float] | None) -> float:
    """Vaut 1.0 si l'intervalle contient l'observation, 0.0 sinon.

    Les bornes sont incluses : l'égalité est une couverture.
    """
    if actual is None or interval is None:  # pragma: no cover - impossible par construction
        raise ValueError("un point retenu porte toujours son observation et son intervalle")
    low, high = interval
    return 1.0 if low <= actual <= high else 0.0


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
    "exiger_coherence",
    "mae",
    "rmse",
]
