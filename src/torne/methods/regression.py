"""Moindres carrés ordinaires et erreur-type robuste aux grappes (CR1).

Origine
-------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Chemin exact    : `athanor/src/athanor/stats/regression.py`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/CORE_CONTRACTS.md` §5.2) ; la reprise est une réécriture
                   interne et la traçabilité de l'origine est l'unique exigence.
- Code tiers      : aucun. Le fichier d'origine ne porte ni en-tête de licence
                   tierce, ni mention de code emprunté à une autre bibliothèque.
- Dépendances    : `numpy` et la bibliothèque standard uniquement.
- Référence       : moindres carrés ordinaires (méthode de Gauss-Markov) ;
                   erreur-type CR1 par grappes : Cameron, Gelbach & Miller
                   (2011), « Robust inference with cluster-robust standard
                   errors », *Review of Economics and Statistics* 93(2),
                   414-427.

Portage
-------
`hedge_ratio` n'est pas repris : il estime le bêta d'une couverture de marché
financier, hors du périmètre de TORNE.

Le type `IntArray` est redéfini localement. Dans Athanor il vient de
`athanor.stats.resampling`, module **non repris** : le port le déclare ici pour
qu'aucun module extrait n'importe un module absent de TORNE. La dépendance
croisée d'origine est donc résolue dans le port, et non laissée en suspens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

# Type alias redéfini localement (voir « Portage » ci-dessus) : dans Athanor,
# `IntArray` vient de `athanor.stats.resampling`.
IntArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class OLSResult:
    """Résultat d'une régression `y = a + b x`.

    `slope_se` est l'erreur-type de la pente : homoscédastique si aucune
    grappe n'est donnée, CR1 (cluster-robust) sinon. `NaN` signale une
    régression non estimable (moins de trois points, ou `x` sans variance).
    """

    intercept: float
    slope: float
    slope_se: float
    r2: float
    n: int


def ols(x: ArrayLike, y: ArrayLike, *, clusters: IntArray | None = None) -> OLSResult:
    """Moindres carrés ordinaires de `y` sur `x`.

    `slope_se` est homoscédastique par défaut ; avec `clusters` (indices de
    grappes 0..C-1), elle est robuste aux grappes (CR1).
    """
    xv = np.asarray(x, dtype=np.float64)
    yv = np.asarray(y, dtype=np.float64)
    n = xv.size
    nan = float("nan")
    if n != yv.size:
        raise ValueError("x et y de tailles différentes")
    if n < 3 or float(np.var(xv)) == 0.0:
        return OLSResult(nan, nan, nan, nan, n)
    xm, ym = float(xv.mean()), float(yv.mean())
    sxx = float(((xv - xm) ** 2).sum())
    slope = float(((xv - xm) * (yv - ym)).sum()) / sxx
    intercept = ym - slope * xm
    resid = yv - intercept - slope * xv
    sst = float(((yv - ym) ** 2).sum())
    r2 = 1.0 - float((resid**2).sum()) / sst if sst > 0 else nan
    if clusters is None:
        se = math.sqrt(float((resid**2).sum()) / (n - 2) / sxx)
    else:
        c = np.asarray(clusters, dtype=np.int64)
        g = int(c.max()) + 1 if c.size else 0
        scores = np.zeros(g)
        np.add.at(scores, c, (xv - xm) * resid)
        correction = g / (g - 1) * (n - 1) / (n - 2) if g > 1 else nan
        se = math.sqrt(correction * float((scores**2).sum())) / sxx if g > 1 else nan
    return OLSResult(intercept, slope, se, r2, n)


__all__ = ["OLSResult", "ols"]
