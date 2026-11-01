"""Le decodeur GIE : d'une reponse JSON a un etat physiqueuropeen.

Deux decodeurs, pour deux couches :

- `decoder_agsi` : le **stockage souterrain** (AGSI+), au niveau d'un pays
  ou d'une installation. La source publie le stock et la capacite en
  **TWh**, les flux en **GWh/jour** ; tout est converti en **GWh**, seule
  unite qui permet d'additionner la couche terminals et la couche stockage.
- `decoder_alsi` : le **terminal LNG** (ALSI), au niveau d'une
  installation. La source publie le stock et la capacite en GWh, et le
  **debit sortant** (envoi reseau) en GWh/jour. Le **dechargement des
  cargaisons n'est pas publie** : il n'est pas mis a zero, il est laisse
  inconnu, et se derive ensuite de l'equation du stock.

Unite : le controle par le remplissage
-------------------------------------

Les stocks et les capacites d'AGSI+ sont en TWh alors que les flux sont en
GWh/jour. Le remplissage publie (`full`, en %) est le **controle** de cette
conversion : stock / capacite, avec les deux convertis en GWh, doit
retrouver le pourcentage publie. C'est ce controle qui permet d'affirmer
l'unite au lieu de la supposer.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime

from .gas import STOCKAGE_SOUTERRAIN, TERMINAL_LNG, GasDay

TWH_EN_GWH = 1000.0
"""Les stocks d'AGSI+ sont en TWh ; on travaille en GWh."""


def _nombre(valeur: object) -> float | None:
    """La valeur numerique d'un champ, ou rien."""
    if valeur is None or valeur == "":
        return None
    try:
        return float(valeur)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _jour(valeur: object) -> date | None:
    """Le jour de gaz, tel que la source l'ecrit."""
    if not isinstance(valeur, str):
        return None
    try:
        return date.fromisoformat(valeur[:10])
    except ValueError:
        return None


def _publication(element: Mapping[str, object]) -> datetime:
    """L'instant de publication, deduit de la mise a jour de la source."""
    brut = element.get("updatedAt")
    if isinstance(brut, str):
        for gabarit in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(brut[:19], gabarit).replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime.now(UTC)


def decoder_agsi(element: Mapping[str, object]) -> GasDay | None:
    """Un enregistrement AGSI+, traduit en etat de stockage."""
    jour = _jour(element.get("gasDayStart"))
    stock = _nombre(element.get("gasInStorage"))
    capacite = _nombre(element.get("workingGasVolume"))
    if jour is None or stock is None or capacite is None:
        return None
    return GasDay(
        installation=str(element.get("code") or ""),
        pays=str(element.get("code") or ""),
        couche=STOCKAGE_SOUTERRAIN,
        jour_gaz=jour,
        date_publication=_publication(element),
        stock=stock * TWH_EN_GWH,
        capacite=capacite * TWH_EN_GWH,
        entree=_nombre(element.get("injection")),
        sortie=_nombre(element.get("withdrawal")) or 0.0,
        consommation=_nombre(element.get("consumption")),
        rempli=_nombre(element.get("full")),
        autonomie_publiee=_nombre(element.get("consumptionFull")),
        precision=0.1,
    )


def decoder_alsi(element: Mapping[str, object]) -> GasDay | None:
    """Un enregistrement ALSI, traduit en etat de terminal LNG.

    Le **dechargement** n'est pas publie : l'entree reste inconnue, et
    l'equation du stock la derivera plus tard.
    """
    jour = _jour(element.get("gasDayStart"))
    inventaire = element.get("inventory")
    capacite = element.get("dtmi")
    if not isinstance(inventaire, Mapping) or not isinstance(capacite, Mapping):
        return None
    stock = _nombre(inventaire.get("gwh"))
    volume = _nombre(capacite.get("gwh"))
    if jour is None or stock is None or volume is None:
        return None
    return GasDay(
        installation=str(element.get("code") or ""),
        pays=str(element.get("country") or element.get("code") or "")[:2],
        couche=TERMINAL_LNG,
        jour_gaz=jour,
        date_publication=_publication(element),
        stock=stock,
        capacite=volume,
        entree=None,
        sortie=_nombre(element.get("sendOut")) or 0.0,
        rempli=None,
        autonomie_publiee=None,
        precision=0.1,
    )


def controle_unite(element: Mapping[str, object]) -> float | None:
    """L'ecart au remplissage publie, apres conversion des unites.

    La source publie `full` (en %) et `gasInStorage` / `workingGasVolume`
    (en TWh). Si la conversion est correcte, le quotient retrouve le
    pourcentage publie. L'ecart returned est la **decouverte** ; elle doit
    etre minuscule.
    """
    stock = _nombre(element.get("gasInStorage"))
    capacite = _nombre(element.get("workingGasVolume"))
    publie = _nombre(element.get("full"))
    if stock is None or capacite is None or publie is None or capacite <= 0:
        return None
    calcule = stock / capacite * 100.0
    return abs(calcule - publie)


__all__ = [
    "TWH_EN_GWH",
    "controle_unite",
    "decoder_agsi",
    "decoder_alsi",
]
