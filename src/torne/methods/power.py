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
- Dépendances    : `scipy` (loi de Student et loi non centrale de Student) et
                   `statistics.NormalDist` de la bibliothèque standard (quantiles
                   normaux) ; `numpy` n'est pas requis ici.
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

Cohérence avec le test exécuté
-------------------------------
L'approximation normale (route par défaut, `df=None`) suppose que la
statistique du test est normale. Le test de Diebold-Mariano de TORNE est, lui,
un test de Student à `n - 1` degrés de liberté avec la correction de petit
échantillon de Harvey, Leybourne & Newbold (1997). Annoncer la puissance et
l'effet minimal détectable d'un test sous une autre loi que celle du test
exécuté décrit un test qui n'est pas celui qui a été fait : c'est ce que la
route `df` (test de Student, loi non centrale de Student via
`scipy.stats.nct`) corrige.

La route `df` est disponible sur `mde_from_se`, `minimum_detectable_effect` et
`power_at`, qui reçoivent tous la taille d'échantillon ou l'erreur-type.
`required_units` reste sous l'approximation normale : les degrés de liberté
d'un test apparié valent `n - 1`, où `n` est précisément l'effectif recherché
— la grandeur à calculer — et la question de planification n'a pas d'autre
réponse que l'approximation normale. La puissance exacte du test de Student
qui sera ensuite exécuté est donnée par `power_at(..., df=...)`.
"""

from __future__ import annotations

import math
from statistics import NormalDist

from scipy import stats

from .calibration import Alternative

_NORMAL = NormalDist()

_BISECTION_STEPS = 100


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


def _critical_value(alpha: float, alternative: Alternative, df: int | None) -> float:
    """Valeur critique du test : quantile normal si `df` est None, quantile de Student sinon."""
    if df is None:
        return z_alpha(alpha, alternative)
    _check(alpha)
    if df < 1:
        raise ValueError(f"degrés de liberté invalides : {df}")
    tail = alpha / 2.0 if alternative is Alternative.TWO_SIDED else alpha
    return float(stats.t.ppf(1.0 - tail, df))


def _power_student(lam: float, df: int, crit: float, alternative: Alternative) -> float:
    """Puissance d'un test t : `T` suit la loi non centrale de Student (ddl `df`, non-centralité `lam`)."""
    if not math.isfinite(lam) or abs(lam) > 1e12:
        # `scipy.stats.nct` n'est pas défini pour une non-centralité infinie (ni
        # au-delà de 1e12) et rend `NaN`. La limite est pourtant immédiate : la
        # puissance tend vers 1 dans le sens de l'alternative et vers 0 dans
        # l'autre.
        if alternative is Alternative.GREATER:
            return 1.0 if lam > 0 else 0.0
        if alternative is Alternative.LESS:
            return 1.0 if lam < 0 else 0.0
        return 1.0
    if alternative is Alternative.GREATER:
        return float(stats.nct.sf(crit, df, lam))
    if alternative is Alternative.LESS:
        return float(stats.nct.cdf(-crit, df, lam))
    return float(stats.nct.sf(crit, df, lam)) + float(stats.nct.cdf(-crit, df, lam))


def _lambda_for_power(
    power: float, alpha: float, df: int, crit: float, alternative: Alternative
) -> float:
    """Non-centralité signée qui atteint exactement la puissance cible.

    La puissance est monotone en non-centralité : croissante pour `GREATER` et
    `TWO_SIDED`, décroissante pour `LESS` — où la non-centralité cherchée est
    négative. La solution est encadrée par doublement puis affinée par
    dichotomie.
    """
    if power < alpha:
        raise ValueError(f"puissance cible ({power}) inférieure au seuil alpha ({alpha})")
    decroissante = alternative is Alternative.LESS
    if decroissante:
        bas, haut = -1.0, 0.0
        while _power_student(bas, df, crit, alternative) < power:
            bas *= 2.0
            if bas < -1e6:
                raise ValueError(f"puissance cible inatteignable : {power}")
    else:
        bas, haut = 0.0, 1.0
        while _power_student(haut, df, crit, alternative) < power:
            haut *= 2.0
            if haut > 1e6:
                raise ValueError(f"puissance cible inatteignable : {power}")
    for _ in range(_BISECTION_STEPS):
        milieu = 0.5 * (bas + haut)
        if _power_student(milieu, df, crit, alternative) < power:
            if decroissante:
                haut = milieu
            else:
                bas = milieu
        else:
            if decroissante:
                bas = milieu
            else:
                haut = milieu
        if haut - bas <= 1e-13 * max(1.0, abs(haut)):
            break
    return 0.5 * (bas + haut)


def mde_from_se(
    se: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Alternative = Alternative.TWO_SIDED,
    df: int | None = None,
) -> float:
    """Plus petit effet détectable quand l'erreur-type de l'estimateur vaut `se`.

    Approximation normale (`df=None`) : (z_alpha + z_beta) * se.

    Test de Student (`df` donné) : la plus petite non-centralité qui atteint la
    puissance `power` au seuil `alpha`, multipliée par `se`. La loi non
    centrale de Student est calculée par `scipy.stats.nct` ; la puissance cible
    doit être au moins égale à `alpha`, sans quoi aucun effet ne peut la
    atteindre dans le sens de l'alternative.
    """
    if se < 0:
        raise ValueError(f"erreur-type négative : {se}")
    if df is None:
        return _z_sum(alpha, power, alternative) * se
    crit = _critical_value(alpha, alternative, df)
    return abs(_lambda_for_power(power, alpha, df, crit, alternative)) * se


def minimum_detectable_effect(
    n: int,
    sd: float,
    *,
    design_effect: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    alternative: Alternative = Alternative.TWO_SIDED,
    df: int | None = None,
) -> float:
    """Effet minimal détectable avec `n` unités. En valeur absolue.

    Approximation normale (`df=None`) : (z_alpha + z_beta) * sigma * racine(deff / n).

    Test de Student (`df` donné) : même formule, la non-centralité étant
    remplacée par la solution exacte de la puissance d'un test t.
    """
    if n <= 0:
        raise ValueError(f"effectif non positif : {n}")
    if sd < 0 or design_effect <= 0:
        raise ValueError(f"écart-type ou effet de plan invalide : sd={sd}, deff={design_effect}")
    return mde_from_se(
        sd * math.sqrt(design_effect / n),
        alpha=alpha,
        power=power,
        alternative=alternative,
        df=df,
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

    La planification se fait sous l'approximation normale : les degrés de liberté
    d'un test apparié valent `n - 1`, où `n` est l'effectif recherché.
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
    df: int | None = None,
) -> float:
    """Puissance avec `n` unités contre un effet SIGNÉ (les deux queues en bilatéral).

    Approximation normale (`df=None`) : `GREATER` : 1 - Phi(z_alpha - lambda) ;
    `LESS` : Phi(-z_alpha - lambda) ; `TWO_SIDED` : Phi(-z_alpha - lambda) +
    1 - Phi(z_alpha - lambda), avec lambda = effect / (sigma racine(deff / n)).

    Test de Student (`df` donné) : la loi non centrale de Student remplace la loi
    normale, avec la valeur critique de Student au seuil `alpha` ; `lambda` a la
    même définition. La puissance est alors exacte, et non approchée.
    """
    if n <= 0 or sd <= 0 or design_effect <= 0:
        raise ValueError(f"paramètres invalides : n={n}, sd={sd}, deff={design_effect}")
    lam = effect / (sd * math.sqrt(design_effect / n))
    if df is None:
        z = z_alpha(alpha, alternative)
        upper = 1.0 - _NORMAL.cdf(z - lam)
        lower = _NORMAL.cdf(-z - lam)
        if alternative is Alternative.GREATER:
            return upper
        if alternative is Alternative.LESS:
            return lower
        return upper + lower
    crit = _critical_value(alpha, alternative, df)
    return _power_student(lam, df, crit, alternative)


__all__ = [
    "mde_from_se",
    "minimum_detectable_effect",
    "power_at",
    "required_units",
    "z_alpha",
]
