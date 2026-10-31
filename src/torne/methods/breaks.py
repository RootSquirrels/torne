"""Rupture de moyenne d'une série : test CUSUM (OLS-CUSUM) et variance de long terme.

Origine
-------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Chemin exact    : `athanor/src/athanor/stats/breaks.py`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/CONTRATS_FONDAMENTAUX.md` §5.2) ; la reprise est une réécriture
                   interne et la traçabilité de l'origine est l'unique exigence.
- Code tiers      : aucun en-tête de licence tierce dans le fichier d'origine.
- Dépendances    : `numpy` et la bibliothèque standard uniquement.
- Référence       : Ploberger & Krämer (1992), « The CUSUM test for a change in
                   parameters of a linear regression model », *Econometrica*
                   60(2), 277-309 ; loi de Kolmogorov pour la queue du
                   supremum du pont brownien ; fenêtre de Newey & West (1994),
                   « Automatically generated generalized least squares
                   estimates », *Econometrica* 62(3), 631-653.

Portage
-------
Le module est repris dans son intégralité : il ne dépend d'aucun autre module
d'Athanor (`numpy` et bibliothèque standard seulement) et son comportement est
vérifié par `athanor/tests/test_breaks.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

MIN_OBSERVATIONS = 16


def kolmogorov_sf(x: float) -> float:
    """`P(sup_t |B(t)| > x)` pour un pont brownien `B` (loi de Kolmogorov). Deux séries, toutes deux exactes."""
    if not math.isfinite(x):
        return 0.0 if x > 0 else 1.0
    if x <= 0:
        return 1.0
    if x < 1.0:
        # cdf = sqrt(2 pi) / x · somme exp(-(2j - 1)² pi² / (8 x²)) : converge vite pour x petit
        cdf = (
            math.sqrt(2 * math.pi)
            / x
            * sum(math.exp(-((2 * j - 1) ** 2) * math.pi**2 / (8 * x * x)) for j in range(1, 50))
        )
        return min(1.0, max(0.0, 1.0 - cdf))
    sf = 2.0 * sum((1.0 if j % 2 else -1.0) * math.exp(-2.0 * j * j * x * x) for j in range(1, 100))
    return min(1.0, max(0.0, sf))


def bartlett_lags(n: int) -> int:
    """Fenêtre de Newey & West (1994) : `floor(4 (n / 100)^(2/9))`."""
    return math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))


def long_run_variance(residuals: np.ndarray, lags: int) -> float:
    """Variance de long terme de résidus centrés, noyau de Bartlett (positive par construction)."""
    n = residuals.size
    v = float(residuals @ residuals) / n
    for k in range(1, min(lags, n - 1) + 1):
        v += 2.0 * (1.0 - k / (lags + 1)) * float(residuals[k:] @ residuals[:-k]) / n
    return v


@dataclass(frozen=True, slots=True)
class BreakResult:
    """`statistic` : max |S_k| / (sigma_lr sqrt(n)) ; `break_index` : dernier indice du premier régime.

    `mean_before` / `mean_after` : moyennes de part et d'autre de la rupture la
    plus probable. `NaN` signale un test non applicable (série trop courte,
    constante ou non finie).
    """

    statistic: float
    p_value: float
    break_index: int
    mean_before: float
    mean_after: float
    n_observations: int
    lags: int


def cusum_break_test(xs: ArrayLike, *, lags: int | None = 0) -> BreakResult:
    """OLS-CUSUM d'une moyenne constante (Ploberger & Krämer 1992).

    `NaN` si moins de 16 observations ou série constante. `lags = None` :
    variance de long terme de Bartlett (plus prudente sous autocorrélation).
    """
    x = np.asarray(xs, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("série unidimensionnelle attendue")
    n = x.size
    use_lags = bartlett_lags(n) if lags is None else int(lags)
    if use_lags < 0:
        raise ValueError(f"lags >= 0 requis (reçu {lags})")
    nan = float("nan")
    if n < MIN_OBSERVATIONS or not np.all(np.isfinite(x)):
        return BreakResult(nan, nan, -1, nan, nan, n, use_lags)
    resid = x - x.mean()
    sigma2 = long_run_variance(resid, use_lags)
    if not sigma2 > 0:
        return BreakResult(nan, nan, -1, nan, nan, n, use_lags)
    path = np.cumsum(resid)[:-1]  # S_1 … S_{n-1} (S_n = 0)
    k = int(np.argmax(np.abs(path)))
    stat = float(np.abs(path[k])) / math.sqrt(sigma2 * n)
    return BreakResult(
        stat,
        kolmogorov_sf(stat),
        k,
        float(x[: k + 1].mean()),
        float(x[k + 1 :].mean()),
        n,
        use_lags,
    )


__all__ = ["MIN_OBSERVATIONS", "BreakResult", "bartlett_lags", "cusum_break_test", "kolmogorov_sf"]
