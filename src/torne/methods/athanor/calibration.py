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
                   code repris, et TORNE n'a pas scipy comme dépendance runtime
                   (`pyproject.toml` : `numpy` seul). La loi de Student est donc
                   réimplémentée ici en bibliothèque standard, par la voie de la
                   bêta incomplète régulière (fraction continue de Lentz
                   modifiée, Numerical Recipes §6.4) — exactement l'oracle pur
                   d'Athanor lui-même, `athanor/tests/special_reference.py`,
                   que le projet Athanor a conservé et vérifié contre
                   `scipy.special.stdtr` à 5e-12 sur une grille
                   (`athanor/tests/test_calibration.py:176-182`).
- Dépendances    : `numpy` et la bibliothèque standard uniquement.
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

# Type alias redéfini localement (voir « Portage » ci-dessus) : dans Athanor,
# `IntArray` vient de `athanor.stats.resampling`.
IntArray = NDArray[np.int64]

_NORMAL = NormalDist()

_CF_MAX_ITER = 10_000
_CF_EPS = 1e-15
_CF_TINY = 1e-300


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
    (`None` = loi normale asymptotique).
    """

    mean_diff: float
    variance: float
    statistic: float
    p_value: float
    n: int
    lag: int
    df: int | None
    alternative: Alternative


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
        mean_d, variance, stat, min(1.0, max(0.0, p)), n, lag, df, alternative
    )


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Fraction continue de Lentz modifiée (Numerical Recipes §6.4) pour la bêta incomplète."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > _CF_TINY else _CF_TINY)
    h = d
    for m in range(1, _CF_MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _CF_TINY else _CF_TINY)
        c = 1.0 + aa / c
        c = c if abs(c) > _CF_TINY else _CF_TINY
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _CF_TINY else _CF_TINY)
        c = 1.0 + aa / c
        c = c if abs(c) > _CF_TINY else _CF_TINY
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _CF_EPS:
            return h
    raise ArithmeticError(f"bêta incomplète : pas de convergence (a={a}, b={b}, x={x})")


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Bêta incomplète régularisée `I_x(a, b)`, par fraction continue (Numerical Recipes §6.4)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: float) -> float:
    """`P(T <= t)` pour `T` de Student à `df` degrés de liberté (`df` infini = loi normale).

    Voie retenue : `P(|T| > |t|) = I_{df/(df+t²)}(df/2, 1/2)`, la bêta incomplète
    régulière étant calculée par fraction continue de Lentz modifiée. C'est la
    réimplémentation en bibliothèque standard de `scipy.special.stdtr` utilisée
    par Athanor, dont l'exactitude est vérifiée par
    `athanor/tests/test_calibration.py:161-182`.
    """
    if df <= 0:
        raise ValueError("df doit être > 0")
    if math.isnan(t):
        return math.nan
    if math.isinf(t):
        return 1.0 if t > 0 else 0.0
    if math.isinf(df):
        return _NORMAL.cdf(t)
    tail = 0.5 * _regularized_incomplete_beta(df / (df + t * t), df / 2.0, 0.5)
    return 1.0 - tail if t > 0 else tail


__all__ = [
    "Alternative",
    "DieboldMarianoResult",
    "diebold_mariano",
    "newey_west_variance",
    "student_t_cdf",
]
