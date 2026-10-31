"""Test de Diebold-Mariano apparié et variance de long terme HAC (Newey-West).

Origine
-------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Chemin exact    : `athanor/src/athanor/stats/calibration.py`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/PROGRAMME.md:24-31`) ; la reprise est une réécriture
                   interne et la traçabilité de l'origine est l'unique exigence.
- Code tiers      : aucun en-tête de licence tierce dans le fichier d'origine.
                   Le fichier d'origine appelait `scipy.special.stdtr` pour la
                   loi de Student : c'est un **appel de bibliothèque**, non du
                   code repris. TORNE appelle aujourd'hui `scipy.stats.t.cdf`
                   pour la même primitive, et `scipy` est une dépendance de
                   runtime (`pyproject.toml`). La réimplémentation en
                   bibliothèque standard qui avait été substituée à l'appel
                   (bêta incomplète régulière par fraction continue de Lentz,
                   Numerical Recipes §6.4) est **retirée** : son écart mesuré
                   à `scipy.stats.t.cdf` atteignait 7,9e-10 en valeur absolue
                   sur une grille de (t, ddl), là où SciPy est exact à la
                   précision machine. Reproduire une primitive mathématique
                   disponible et éprouvée n'est pas justifié
                   (`docs/PROGRAMME.md`, règle de réutilisation des
                   bibliothèques scientifiques).
- Dépendances    : `numpy`, `scipy` et la bibliothèque standard.
- Référence       : Diebold & Mariano (1995), « Comparing predictive
                   accuracy », *Journal of Business & Economic Statistics* 13(3),
                   253-263 ; variance de long terme : Newey & West (1987), « A
                   simple, positive semi-definite, heteroskedasticity and
                   autocorrelation consistent covariance matrix », *Econometrica*
                   55(3), 703-708 ; correction de petit échantillon : Harvey,
                   Leybourne & Newbold (1997), « Testing the equality of
                   prediction mean squared errors », *International Journal of
                   Forecasting* 13(2), 281-291.

Portage
-------
Seule la partie « Diebold-Mariano » est reprise : variance HAC, test apparié,
loi de Student. Les scores de calibration de **probabilités** (Brier, log-loss,
ECE, diagramme de fiabilité, ratio de Brier) ne le sont pas : ils servent à
étiqueter des probabilités, ce que la comparaison de prévisions de TORNE ne
fait pas.

Le type `IntArray` est redéfini localement. Dans Athanor il vient de
`athanor.stats.resampling`, module **non repris** : le port le déclare ici pour
qu'aucun module extrait n'importe un module absent de TORNE. L'énumération
`Alternative`, également définie dans `resampling` d'Athanor, est déclarée ici
et importée par `power.py` : elle n'existe donc qu'en un seul endroit dans
TORNE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from statistics import NormalDist

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats

# Type alias redéfini localement (voir « Portage » ci-dessus) : dans Athanor,
# `IntArray` vient de `athanor.stats.resampling`.
IntArray = NDArray[np.int64]

_NORMAL = NormalDist()


class Alternative(StrEnum):
    """Sens de l'alternative d'un test."""

    GREATER = "greater"
    LESS = "less"
    TWO_SIDED = "two-sided"


def newey_west_variance(x: ArrayLike, lag: int) -> float:
    """Variance de long terme de `x` (Newey & West 1987) : gamma_0 + 2 somme_{k=1..lag} (1 - k/(lag+1)) gamma_k, gamma_k en 1/n.

    Poids de Bartlett : la variance reste positive quel que soit le retard.
    """
    v = np.asarray(x, dtype=np.float64)
    if v.ndim != 1 or v.size == 0:
        raise ValueError("vecteur 1D non vide requis")
    if lag < 0:
        raise ValueError(f"lag >= 0 requis (reçu {lag})")
    e = v - v.mean()
    n = e.size
    total = float(e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        total += 2.0 * (1.0 - k / (lag + 1.0)) * float(e[k:] @ e[:-k]) / n
    return total


@dataclass(frozen=True, slots=True)
class DieboldMarianoResult:
    """`d_t = perte_A(t) - perte_B(t)`. Une statistique < 0 signifie « A perd moins que B ».

    `variance` est la variance de long terme de `d` (par observation) ; `df`
    est le nombre de degrés de liberté de la loi de Student employée
    (`None` = loi normale asymptotique) ; `small_sample_factor` est le facteur
    multiplicatif de la correction de Harvey, Leybourne & Newbold (1997)
    effectivement appliqué à la statistique (`1.0` si elle ne l'est pas).

    Le facteur est publié parce que la puissance et l'effet minimal détectable
    du test doivent être exprimés dans la même échelle que la statistique :
    voir `torne.methods.power` et `torne.methods.compare`.
    """

    mean_diff: float
    variance: float
    statistic: float
    p_value: float
    n: int
    lag: int
    df: int | None
    alternative: Alternative
    small_sample_factor: float = 1.0


def diebold_mariano(
    losses_a: ArrayLike,
    losses_b: ArrayLike,
    *,
    alternative: Alternative = Alternative.LESS,
    lag: int = 0,
    small_sample: bool = True,
    clusters: IntArray | None = None,
) -> DieboldMarianoResult:
    """Test de Diebold & Mariano (1995) : H0 `E[perte_A - perte_B] = 0`.

    `alternative LESS` (défaut) : H1 « A perd moins que B » ; `GREATER` :
    l'inverse ; `TWO_SIDED` : l'écart est de signe quelconque.

    Variance de `d̄` :
      - `lag` > 0 : HAC Newey-West (dépendance sérielle ; pour une prévision à
        h pas, `lag = h - 1`) ;
      - `clusters` (indices 0..C-1) : robuste aux grappes,
        Σ_c (Σ_{t∈c} (d_t - d̄))² · C/(C-1) / n². Exclusif de `lag`.
    `small_sample` : correction de Harvey, Leybourne & Newbold (1997),
    statistique * racine((n+1-2h+h(h-1)/n)/n) avec h = `lag` + 1, comparée à une
    Student à n-1 ddl (C-1 avec grappes). Avec `lag = 0` c'est exactement le
    test t apparié ; sans correction, loi normale asymptotique.
    """
    a = np.asarray(losses_a, dtype=np.float64)
    b = np.asarray(losses_b, dtype=np.float64)
    if a.ndim != 1 or b.ndim != 1 or a.size != b.size:
        raise ValueError("deux vecteurs de pertes 1D de même longueur requis")
    n = int(a.size)
    if n < 2:
        raise ValueError("au moins 2 observations requises")
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise ValueError("pertes non finies")
    d = a - b
    mean_d = float(d.mean())
    df: int | None
    if clusters is not None:
        if lag:
            raise ValueError("lag et clusters sont exclusifs")
        if clusters.shape != (n,):
            raise ValueError("clusters doit avoir la longueur des pertes")
        sums = np.bincount(clusters, weights=d - mean_d)
        n_c = int(np.count_nonzero(np.bincount(clusters)))
        if n_c < 2:
            raise ValueError("au moins 2 grappes requises")
        var_mean = float(sums @ sums) * n_c / (n_c - 1) / (n * n)
        variance = var_mean * n
        factor = 1.0
        df = n_c - 1 if small_sample else None
    else:
        variance = newey_west_variance(d, lag)
        var_mean = variance / n
        h = lag + 1
        factor = math.sqrt(max(0.0, (n + 1 - 2 * h + h * (h - 1) / n) / n)) if small_sample else 1.0
        df = n - 1 if small_sample else None
    if var_mean > 0:
        stat = mean_d / math.sqrt(var_mean) * factor
    else:
        stat = 0.0 if mean_d == 0 else math.copysign(math.inf, mean_d)

    def cdf(z: float) -> float:
        return student_t_cdf(z, df) if df is not None else _NORMAL.cdf(z)

    if alternative is Alternative.LESS:
        p = cdf(stat)
    elif alternative is Alternative.GREATER:
        p = 1.0 - cdf(stat)
    else:
        p = 2.0 * (1.0 - cdf(abs(stat)))
    if var_mean <= 0 and mean_d == 0:
        p = 1.0  # prévisions identiques : aucune preuve dans aucun sens
    return DieboldMarianoResult(
        mean_d, variance, stat, min(1.0, max(0.0, p)), n, lag, df, alternative, factor
    )


def student_t_cdf(t: float, df: float) -> float:
    """`P(T <= t)` pour `T` de Student à `df` degrés de liberté (`df` infini = loi normale).

    La primitive vient de `scipy.stats.t.cdf`, l'implémentation de référence de
    l'écosystème : elle est exacte à la précision machine, y compris pour
    `df = 1` (Cauchy), `df = 2` et `df` infini (loi normale). La réimplémentation
    en bibliothèque standard qui existait auparavant (bêta incomplète régulière
    par fraction continue de Lentz, Numerical Recipes §6.4) a été retirée : son
    écart à SciPy atteignait 7,9e-10 en valeur absolue, et reproduire une
    primitive mathématique disponible et éprouvée n'est pas justifié.

    `df` doit être strictement positif ; `t` peut être infini ou `NaN`.
    """
    if df <= 0:
        raise ValueError("df doit être > 0")
    if math.isnan(t):
        return math.nan
    if math.isinf(t):
        return 1.0 if t > 0 else 0.0
    return float(stats.t.cdf(t, df))


__all__ = [
    "Alternative",
    "DieboldMarianoResult",
    "diebold_mariano",
    "newey_west_variance",
    "student_t_cdf",
]
