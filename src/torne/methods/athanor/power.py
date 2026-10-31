"""Puissance : effet minimal détectable, taille d'échantillon requise, puissance d'un test.

Origine
-------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Chemin exact    : `athanor/src/athanor/stats/power.py`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/PROGRAMME.md:24-31`) ; la reprise est une réécriture
                   interne et la traçabilité de l'origine est l'unique exigence.
- Code tiers      : aucun en-tête de licence tierce dans le fichier d'origine.
- Dépendances    : `numpy` et la bibliothèque standard uniquement (les
                   quantiles normaux viennent de `statistics.NormalDist`).
- Référence       : Lehr R. (1992), « Sixteen S-squared over D-squared: a
                   relation for crude sample size estimates », *Statistics in
                   Medicine* 11(10), 1099-1102 ; Kish L. (1965), *Survey
                   Sampling*, Wiley ; approximation normale de la puissance.

Portage
-------
Sont repris : `z_alpha`, `mde_from_se`, `minimum_detectable_effect`,
`required_units`, `power_at`.

Ne sont **pas** repris :
- `estimate_design_effect`, qui repose sur la métrique ratio
  `M = Σ valeur / Σ poids` et sur le bootstrap par grappes d'Athanor
  (`stats/resampling.py`, convention propre à Athanor) : hors périmètre pour
  TORNE, où l'effet de plan se déduit directement de la variance HAC ;
- `eprocess_power`, qui dépend de `athanor.stats.evalues` (non repris).

Le type `FloatArray` (qui venait de `athanor.stats.resampling` dans Athanor)
n'est pas nécessaire ici, puisque `estimate_design_effect` n'est pas repris ;
l'énumération `Alternative` (même module d'origine) est importée de
`.calibration`, où elle est déclarée : elle n'existe donc qu'en un seul endroit
dans TORNE, et aucun module extrait n'importe un module absent de TORNE.
"""

from __future__ import annotations

import math
from statistics import NormalDist

from .calibration import Alternative

_NORMAL = NormalDist()


def _check(alpha: float, power: float | None = None) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha hors de ]0, 1[ : {alpha}")
    if power is not None and not 0.0 < power < 1.0:
        raise ValueError(f"puissance hors de ]0, 1[ : {power}")


def z_alpha(alpha: float = 0.05, alternative: Alternative = Alternative.TWO_SIDED) -> float:
    """Valeur critique du test : z(1 - a/2) en bilatéral, z(1 - a) en unilatéral."""
    _check(alpha)
    tail = alpha / 2.0 if alternative is Alternative.TWO_SIDED else alpha
    return _NORMAL.inv_cdf(1.0 - tail)


def _z_sum(alpha: float, power: float, alternative: Alternative) -> float:
    _check(alpha, power)
    return z_alpha(alpha, alternative) + _NORMAL.inv_cdf(power)


def mde_from_se(
    se: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Alternative = Alternative.TWO_SIDED,
) -> float:
    """Plus petit effet détectable quand l'erreur-type de l'estimateur vaut `se` : (z_alpha + z_beta) * se."""
    if se < 0:
        raise ValueError(f"erreur-type négative : {se}")
    return _z_sum(alpha, power, alternative) * se


def minimum_detectable_effect(
    n: int,
    sd: float,
    *,
    design_effect: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Alternative = Alternative.TWO_SIDED,
) -> float:
    """Effet minimal détectable avec `n` unités : (z_alpha + z_beta) * sigma * racine(deff / n). En valeur absolue."""
    if n <= 0:
        raise ValueError(f"effectif non positif : {n}")
    if sd < 0 or design_effect <= 0:
        raise ValueError(f"écart-type ou effet de plan invalide : sd={sd}, deff={design_effect}")
    return mde_from_se(
        sd * math.sqrt(design_effect / n), alpha=alpha, power=power, alternative=alternative
    )


def required_units(
    effect: float,
    sd: float,
    *,
    design_effect: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Alternative = Alternative.TWO_SIDED,
) -> int:
    """Nombre d'unités pour détecter un effet de taille |effect| : ceil(deff * ((z_alpha + z_beta) * sigma / delta) ** 2).

    `effect` est l'écart à l'hypothèse nulle, lu en valeur absolue ; le sens est
    celui de `alternative`. Le terme de la queue opposée est négligé en bilatéral
    (convention usuelle, conservative de au plus a/2 en puissance).
    """
    if effect == 0 or not math.isfinite(effect):
        raise ValueError(f"effet visé nul ou non fini : {effect}")
    if sd <= 0 or design_effect <= 0:
        raise ValueError(f"écart-type ou effet de plan invalide : sd={sd}, deff={design_effect}")
    n = design_effect * (_z_sum(alpha, power, alternative) * sd / abs(effect)) ** 2
    return max(1, math.ceil(n - 1e-9))


def power_at(
    n: int,
    effect: float,
    sd: float,
    *,
    design_effect: float = 1.0,
    alpha: float = 0.05,
    alternative: Alternative = Alternative.TWO_SIDED,
) -> float:
    """Puissance avec `n` unités contre un effet SIGNÉ (approximation normale, les deux queues en bilatéral).

    `GREATER` : 1 - Phi(z_alpha - lambda) ; `LESS` : Phi(-z_alpha - lambda) ;
    `TWO_SIDED` : Phi(-z_alpha - lambda) + 1 - Phi(z_alpha - lambda), avec lambda = effect / (sigma racine(deff / n)).
    """
    if n <= 0 or sd <= 0 or design_effect <= 0:
        raise ValueError(f"paramètres invalides : n={n}, sd={sd}, deff={design_effect}")
    lam = effect / (sd * math.sqrt(design_effect / n))
    z = z_alpha(alpha, alternative)
    upper = 1.0 - _NORMAL.cdf(z - lam)
    lower = _NORMAL.cdf(-z - lam)
    if alternative is Alternative.GREATER:
        return upper
    if alternative is Alternative.LESS:
        return lower
    return upper + lower


__all__ = [
    "mde_from_se",
    "minimum_detectable_effect",
    "power_at",
    "required_units",
    "z_alpha",
]
