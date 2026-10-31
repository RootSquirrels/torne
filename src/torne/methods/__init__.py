"""Méthodes scientifiques de TORNE.

Ce paquet regroupe les méthodes exécutables par le contrat « Modèles »
(`docs/ARCHITECTURE.md` §3) : une identité déclarée, des entrées et des
paramètres explicites, un résultat typé. Il ne contient **ni registre, ni
moteur, ni service** : une méthode est une fonction paramétrée, et rien de plus.

Contenu :

- `kalman` : filtre de Kalman en espace d'état, tendance linéaire locale —
  reconstruit un état latent (niveau, pente) et publie une prévision à un pas
  avec son intervalle prédictif ;
- `compare` : comparaison appariée d'une prévision à une référence (test de
  Diebold-Mariano apparié, variance HAC) et recherche d'une rupture de régime
  (CUSUM) ;
- `regression`, `calibration`, `breaks`, `power` : primitives statistiques
  (moindres carrés ordinaires et erreur-type CR1 groupé ; test de
  Diebold-Mariano apparié et variance de long terme HAC ; rupture de moyenne
  par CUSUM ; effet minimal détectable, taille d'échantillon et puissance),
  reprises et réécrites d'un dépôt historique privé du propriétaire
  (`athanor@6dacc87`). L'en-tête de chaque module porte l'origine exacte, le
  commit, le statut de la licence, les dépendances tierces et la référence
  scientifique.
"""

from . import breaks, calibration, power, regression
from .compare import (
    ComparisonReport,
    RegimeChangeReport,
    compare_forecasts,
    detect_regime_change,
    ols_trend_forecast,
)
from .kalman import LocalLinearTrendModel

__all__ = [
    "ComparisonReport",
    "LocalLinearTrendModel",
    "RegimeChangeReport",
    "breaks",
    "calibration",
    "compare_forecasts",
    "detect_regime_change",
    "ols_trend_forecast",
    "power",
    "regression",
]
