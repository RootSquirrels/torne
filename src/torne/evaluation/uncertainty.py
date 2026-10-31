"""Incertitude des métriques : variance HAC de long terme et taille effective.

**La méthode employée, exactement.** L'incertitude d'une métrique est un
intervalle de confiance de la **moyenne de la série de pertes**, calculé par
la **variance de long terme HAC** (Newey & West 1987) avec un **noyau de
Bartlett** et la fenêtre `floor(4 (n/100)^(2/9))` (Newey & West 1994) — la
convention déjà employée par le test apparié de Diebold-Mariano
(`torne.methods.compare`), et non une deuxième. L'erreur type de la moyenne
est `sqrt(variance_hac / n)`, l'intervalle est `moyenne ± z * erreur type`
avec `z = 1,959964` (loi normale, niveau 95 %). La **taille effective** vaut
`n / deff`, où `deff` est le rapport de la variance HAC à la variance IID :
elle dit combien de points indépendants valent réellement les points utilisés.

Les pertes d'une marche avant ne sont pas indépendantes : deux pli voisins
partagent une partie de leur bloc d'entraînement, et les erreurs qui en
ressortent restent autocorrélées. Une variance IID sous-estimerait donc
l'incertitude d'une métrique, et le comparatif paraîtrait plus serré qu'il
ne l'est réellement.

**Pourquoi cette méthode et non un bootstrap par blocs.** `SPEC-010:139`
exige que les comparaisons portent « incertitude des métriques, intervalles de
confiance **ou** bootstrap adapté à la dépendance, et taille effective de
l'échantillon » : l'alternative est ouverte, et l'intervalle de confiance
HAC est l'une des deux voies. `ADR-021` §7 exige que les tests statistiques
respectent « dépendance temporelle/spatiale, autocorrélation, déséquilibre,
événements rares et multiplicité selon le problème » — ce que fait la
variance HAC. Un bootstrap par blocs mobiles serait plus robuste face à une
dépendance mal spécifiée, mais il coûte O(B n) et il introduirait une graine
dans un rapport qui doit rester déterministe et reproductible. **Aucune graine
n'est employée** : le calcul est entièrement déterministe, et deux exécutions
sur la même série de pertes rendent le même intervalle, au bit près.

**Ce que la méthode ne dit pas.** Ses limites sont connues, et elles ne sont
pas masquées :

- c'est une **approximation asymptotique** : elle suppose une série de
  pertes assez longue, et elle est d'autant moins fiable que `n` est petit ;
- elle est **sensible à la fenêtre de Bartlett** : une fenêtre plus large
  ajuste davantage de covariances, au prix d'une variance estimée plus
  bruyante ; la fenêtre employée est une convention, pas un optimum ;
- la **taille effective peut dépasser `n`** quand les erreurs sont
  négativement corrélées : la moyenne est alors plus précise que ne le
  dirait l'indépendance, et c'est la définition (`n / deff`), non une
  anomalie ;
- une série **sans dispersion observée** donne un intervalle dégénéré
  (`low == high == moyenne`) : c'est la lecture honnête d'une série dont les
  pertes observées ne varient pas, et non un intervalle de confiance
  usurpé ;
- l'intervalle ne qualifie que la **dispersion des pertes observées** : il ne
  dit rien de l'incertitude du modèle lui-même, ni de celle des données.

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
    la série des pertes, noyau de Bartlett et fenêtre
    `floor(4 (n/100)^(2/9))`, et l'erreur type de la moyenne est
    `sqrt(variance_hac / n)`. La taille effective vaut `n / deff`, où `deff`
    est le rapport de la variance HAC à la variance IID : elle rend compte de
    l'information perdue du fait de la dépendance temporelle.

    C'est une approximation asymptotique, sensible à la fenêtre de Bartlett,
    et **entièrement déterministe** : aucune graine n'est tirée, deux appels
    sur la même série rendent le même intervalle.

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
