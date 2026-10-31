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
- `athanor` : primitives statistiques reprises et réécrites d'`athanor@6dacc87`
  (dépôt privé du propriétaire). L'en-tête de chaque module porte l'origine
  exacte, le commit, le statut de la licence et la référence scientifique.
"""

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
    "compare_forecasts",
    "detect_regime_change",
    "ols_trend_forecast",
]
