"""Primitives statistiques reprises d'`athanor@6dacc87`.

Ce paquet contient des **réécritures** de primitives d'Athanor, pas une copie
de répertoire et pas une dépendance : le dépôt d'origine n'est pas importé par
TORNE.

Origine commune
---------------
- Dépôt d'origine : `athanor` — dépôt privé du propriétaire.
- Commit          : `6dacc87`.
- Propriétaire    : le propriétaire de TORNE.
- Licence        : dépôt privé, réutilisable sans réserve de licence
                   (`docs/PROGRAMME.md:24-31`). La reprise est un acte de
                   réécriture interne ; la seule exigence est la traçabilité
                   de l'origine, portée par l'en-tête de chaque module.
- Code tiers      : aucun en-tête de licence tierce n'a été trouvé dans les
                   modules d'origine repris (relecture des en-têtes et du
                   corps des fichiers). La seule dépendance externe du code
                   d'origine était `scipy` (`scipy.special.stdtr`, dans
                   `calibration.py`), **remplacée** ici par une implémentation
                   en bibliothèque standard : voir l'en-tête de
                   `calibration.py`.

Modules repris
--------------
- `regression` : moindres carrés ordinaires et erreur-type CR1 par grappes.
- `calibration` : test de Diebold-Mariano apparié et variance de long terme
  HAC (Newey-West).
- `breaks` : rupture de moyenne par CUSUM (Ploberger & Krämer).
- `power` : effet minimal détectable, taille d'échantillon, puissance.

Modules d'Athanor **non** repris : `resampling` (métrique ratio et bootstrap
par grappes, convention propre à Athanor), `evalues`, `online_fdr`,
`multiplicity`, `overfitting`, `intervals`, `scoring`, `variance_reduction`,
`spreads` — le motif est indiqué dans le rapport de mission 001.
"""

from . import breaks, calibration, power, regression

__all__ = ["breaks", "calibration", "power", "regression"]
