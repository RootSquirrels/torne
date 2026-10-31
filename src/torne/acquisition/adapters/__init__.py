"""Les adaptateurs de source — poser une question, et rien de plus.

Un adaptateur sait **demander** à un fournisseur : il construit une URL, il
dit comment la source se parcourt, et il rend la question suivante ou
`None`. Il ne sait **rien interpréter** : ni hydrologie, ni énergie, ni
logistique. C'est la séparation que le programme impose — « un connecteur ne
doit pas savoir reconstruire un état hydrologique » (`docs/PROGRAMME.md`).

Les trois adaptateurs ici présents ont été choisis pour la **diversité de
leur accès**, non pour la quantité de fournisseurs couverts :

- `hubeau` : API JSON française, pagination **par curseur** ;
- `usgs` : API JSON américaine, **sans pagination** — tout vient en une
  réponse, et les valeurs les plus récentes sont marquées provisoires ;
- `copernicus` : API **OData**, pagination par `$top`/`$skip`, réponse
  imbriquée et lien de page suivante dans le corps.

Cette diversité est le but : elle sert à découvrir ce qu'exige vraiment une
capacité transversale d'acquisition, pas à faire fifty connecteurs.
"""

from __future__ import annotations

from .copernicus import CopernicusProductsAdapter
from .hubeau import HubeauObservationsAdapter
from .usgs import UsgsInstantaneousValuesAdapter

__all__ = [
    "CopernicusProductsAdapter",
    "HubeauObservationsAdapter",
    "UsgsInstantaneousValuesAdapter",
]
