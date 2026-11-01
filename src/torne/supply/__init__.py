"""Le domaine de l'offre physique : ce que TORNE reconstruit, et pour quoi.

Ce paquet ne contient que des **grandeurs de domaine** et des **lois de
calcul**. Il ne sait rien du réseau, des formats de source, ni des
adaptateurs : la séparation est celle que le programme impose — un
connecteur ne connaît que la question à poser, et un module de domaine ne
sait que ce qu'il calcule.

Contenu
-------

- `lng` : l'état physique quotidien des terminaux LNG d'importation, et la
  **marge temporelle** qui en est tirée — la grandeur que personne ne
  publie.
"""

from __future__ import annotations

from .lng import (
    RHO_GNL_LIQUIDE,
    ModelMargeOperationnelle,
    TerminalDay,
    capacite_cuve_estimee,
    debit_sortie_moyen,
    ecart_type_sortie,
    marge_temporelle_jours,
    reserve_operationnelle,
    serie_par_terminal,
    tension,
    tonnes_par_gwh,
)

__all__ = [
    "RHO_GNL_LIQUIDE",
    "ModelMargeOperationnelle",
    "TerminalDay",
    "capacite_cuve_estimee",
    "debit_sortie_moyen",
    "ecart_type_sortie",
    "marge_temporelle_jours",
    "reserve_operationnelle",
    "serie_par_terminal",
    "tension",
    "tonnes_par_gwh",
]
