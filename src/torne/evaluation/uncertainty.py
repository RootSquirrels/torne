"""Incertitude des métriques : intervalle HAC et taille effective de l'échantillon.

Les pertes d'une marche avant ne sont pas indépendantes : deux pli voisins
partagent une partie de leur bloc d'entraînement, et les erreurs qui en
ressortent restent autocorrélées. Une variance IID sous-estimerait donc
l'incertitude d'une métrique, et le comparatif paraîtrait plus serré qu'il
ne l'est réellement.

L'incertitude est donc calculée par **variance de long terme HAC**
(Newey & West 1987, noyau de Bartlett), avec la fenêtre automatique
`floor(4 (n/100)^(2/9))` : c'est la convention déjà employée par le test
apparié de Diebold-Mariano (`torne.methods.compare`), et non une deuxième.

Deux grandeurs en sortent :

- l'**intervalle de confiance** de la moyenne de la série de pertes ;
- la **taille effective** de l'échantillon, `n / deff`, où `deff` est le
  facteur d'inflation de la variance dû à la dépendance : elle dit combien de
  points indépendants valent réellement les points utilisés.

Pourquoi la variance HAC plutôt qu'un bootstrap par blocs mobiles : le
bootstrap serait plus robuste, mais il coûte O(B n) et il introduirait une
graine dans un rapport qui doit rester déterministe et reproductible. La
variance HAC est déjà disponible dans le dépôt, elle est déterministe, et elle
mesure la dépendance temporelle — ce qu'exige `SPEC-010:139` (« incertitude
des métriques, intervalles de confiance ou bootstrap adapté à la dépendance, et
taille effective de l'échantillon »).

Ce module ne calcule aucune métrique : il qualifie une série de pertes déjà
construite. Les métriques restent dans `metrics`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

from ..methods.breaks import bartlett_lags
from ..methods.calibration import newey_west_variance

NIVEAU = 0.95
"""Niveau de confiance des intervalles : 95 %."""


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """Intervalle de confiance d'une moyenne, et taille effective de l'échantillon.

    `low` et `high` encadrent la moyenne de la série ; `n_effective` est le
    nombre de points indépendants équivalents à la série utilisée.
    """

    low: float
    high: float
    n_effective: float


def confidence_interval(
    losses: Sequence[float],
    *,
    level: float = NIVEAU,
) -> ConfidenceInterval | None:
    """Intervalle de confiance de la moyenne d'une série de pertes.

    La variance employée est la variance de long terme HAC (Newey & West) de
    la série des pertes, et l'erreur type de la moyenne est
    `sqrt(variance_hac / n)`. La taille effective vaut `n / deff`, où `deff`
    est le rapport de la variance HAC à la variance IID : elle rend compte de
    l'information perdue du fait de la dépendance temporelle.

    `None` est rendu quand l'intervalle n'est pas définissable, c'est-à-dire
    quand la série compte moins de deux points : la qualification est alors
    absente, et jamais une valeur inventée.

    Une série sans dispersion observée donne un intervalle dégénéré
    (`low == high == moyenne`) : c'est la lecture honnête d'une série dont les
    pertes observées ne varient pas.
    """
    if not 0.0 < level < 1.0:
        raise ValueError(f"level doit appartenir à l'intervalle ]0, 1[, il vaut {level}")

    values = tuple(float(valeur) for valeur in losses)
    n = len(values)
    if n < 2:
        return None

    moyenne = math.fsum(values) / n
    variance_iid = newey_west_variance(values, 0)
    variance_hac = max(newey_west_variance(values, bartlett_lags(n)), 0.0)

    quantile = NormalDist().inv_cdf(1.0 - (1.0 - level) / 2.0)
    erreur = quantile * math.sqrt(variance_hac / n)

    facteur = _facteur_inflation(variance_iid, variance_hac, moyenne)
    n_effective = n / facteur if facteur > 0.0 else float(n)

    return ConfidenceInterval(
        low=moyenne - erreur,
        high=moyenne + erreur,
        n_effective=n_effective,
    )


def _facteur_inflation(variance_iid: float, variance_hac: float, moyenne: float) -> float:
    """Rapport de la variance HAC à la variance IID : inflation due à la dépendance.

    Une série sans dispersion observée — à la précision des flottants près —
    ne permet pas de mesurer une inflation : le rapport des deux variances
    n'y serait que du bruit de calcul. Le facteur vaut alors 1, et la taille
    effective reste le nombre de points.

    Le facteur peut être inférieur à 1 : les erreurs négativement corrélées
    rendent la moyenne plus précise que ne le dirait l'indépendance, et la
    taille effective dépasse alors le nombre de points. C'est la définition
    (`n / facteur`), non une anomalie.
    """
    echelle = max(1.0, abs(moyenne))
    if math.sqrt(variance_iid) <= 1e-12 * echelle:
        return 1.0
    if variance_iid <= 0.0:
        return 1.0
    return variance_hac / variance_iid


__all__ = ["NIVEAU", "ConfidenceInterval", "confidence_interval"]
