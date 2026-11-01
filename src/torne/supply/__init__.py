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
- `gas` : l'approvisionnement gazier européen, en deux couches — terminaux
  LNG et stockages souterrains — et les indicateurs de résilience.
- `terminals` : la couche **terminal** européenne : l'état par installation,
  la concentration de la réserve, la dépendance, le scénario de perte.
- `gie` : le décodage des plateformes de transparence de GIE (AGSI+, ALSI).
"""

from __future__ import annotations

from .gas import (
    STOCKAGE_SOUTERRAIN,
    TERMINAL_LNG,
    GasDay,
    buffer_jours,
    concentration_herfindahl,
    couverture_par_installation,
    degradation,
    dependance_top,
    pression_prelevement,
    resilience_perte,
    taux_reconstitution,
)
from .lng import (
    RHO_GNL_LIQUIDE,
    ModelMargeOperationnelle,
    TerminalDay,
    capacite_cuve_estimee,
    debit_sortie_moyen,
    ecart_type_fenetre,
    ecart_type_sortie,
    marge_temporelle_jours,
    reserve_operationnelle,
    serie_par_terminal,
    tension,
    tonnes_par_gwh,
)
from .terminals import (
    concentration_geographique,
    concentration_reserve,
    couverture_systeme,
    dechargement_derive,
    degradation_installation,
    dependance_pays,
    etats_reference,
    jours_en_tension,
    marge_installation,
    scenario_perte,
    serie_par_installation,
)

__all__ = [
    "RHO_GNL_LIQUIDE",
    "STOCKAGE_SOUTERRAIN",
    "TERMINAL_LNG",
    "GasDay",
    "ModelMargeOperationnelle",
    "TerminalDay",
    "buffer_jours",
    "capacite_cuve_estimee",
    "concentration_geographique",
    "concentration_herfindahl",
    "concentration_reserve",
    "couverture_par_installation",
    "couverture_systeme",
    "debit_sortie_moyen",
    "dechargement_derive",
    "degradation",
    "degradation_installation",
    "dependance_pays",
    "dependance_top",
    "ecart_type_fenetre",
    "ecart_type_sortie",
    "etats_reference",
    "jours_en_tension",
    "marge_installation",
    "marge_temporelle_jours",
    "pression_prelevement",
    "reserve_operationnelle",
    "resilience_perte",
    "scenario_perte",
    "serie_par_installation",
    "serie_par_terminal",
    "taux_reconstitution",
    "tension",
    "tonnes_par_gwh",
]
