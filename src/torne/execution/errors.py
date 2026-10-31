"""Erreurs de l'exécution d'un modèle.

Une seule hiérarchie, plate et lisible : `ExecutionError` est la base, et les
trois erreurs spécialisées disent *ce qui* ne va pas.

| Erreur | Cause |
|---|---|
| `InvalidInputError` | les entrées sont inexploitables (série vide, valeur non finie) |
| `InvalidParameterError` | les paramètres ne correspondent pas au domaine déclaré par le modèle |
| `ConfigurationMismatchError` | la configuration ne décrit plus le modèle, les entrées ou les paramètres courants |

Ces erreurs sont *du runner* : elles qualifient un refus de la couche
d'exécution. Les erreurs du modèle (une exception de calcul, par exemple) ne
sont jamais transformées en `ExecutionError` : elles remontent intactes, parce
qu'un échec de modèle n'est pas un échec de l'exécution.
"""

from __future__ import annotations


class ExecutionError(RuntimeError):
    """Erreur de l'exécution : l'aboutissement « entrées → résultat » échoue."""


class InvalidInputError(ExecutionError):
    """Les entrées sont inexploitables : série vide, `NaN` ou infini."""


class InvalidParameterError(ExecutionError):
    """Les paramètres ne correspondent pas au domaine déclaré par le modèle."""


class ConfigurationMismatchError(ExecutionError):
    """La configuration ne décrit plus le modèle, les entrées ou les paramètres."""


__all__ = [
    "ConfigurationMismatchError",
    "ExecutionError",
    "InvalidInputError",
    "InvalidParameterError",
]
