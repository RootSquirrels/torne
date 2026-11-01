"""L'approvisionnement gazier europeen : l'etat physique, et les indicateurs qui en decoulent.

Ce module est le **coeur de domaine** du produit `TORNE · LNG Terminal
Intelligence`, etendue a l'Europe (LNG-002). Il ne connait ni le reseau, ni
le format des sources : il ne connait que des **etats quotidiens observes**
et des **lois de calcul**.

Deux couches physiques
----------------------

- les **terminaux LNG** : stock de LNG, reception des cargaisons, regazification,
  expeditions, capacite ;
- les **stockages souterrains** : stock, injection, soutirage, capacite technique.

Les deux se lisent dans la meme unite — le **GWh** — ce qui permet de les
additionner, et donc de raisonner sur l'approvisionnement d'un pays plutot
que sur une installation.

Ce qui n'est pas publie, et que ce module produit
---------------------------------------------------

L'exploitant publie l'**etat** : le stock, le remplissage, et — pour le
stockage souterrain — l'**autonomie equivalente** en jours. Ce qu'il ne
publie pas, c'est la **concentration** de la reserve (ou se trouve-t-elle ?),
la **dependance** a une installation (que se passe-t-il si elle tombe ?), ni
la **degradation** (la situation se degrade-t-elle plus vite que d'habitude ?).

Ces trois grandeurs sont des **scenarios** ou des **concentrations**, pas des
observations : elles sont donc marquees comme telles, et jamais melangees aux
donnees observees.

La separation des trois natures
------------------------------

Trois natures se distinguent, et le module les tient separees :

- **observe** : le stock, les flux, la capacite, le remplissage — la source les
  publie ;
- **calcule** : le buffer en jours, le taux de reconstitution, la pression de
  prelevement, la concentration, la degradation ;
- **simule** : la resilience, c'est-a-dire ce que cobertura reste-t-il si une
  installation disparait.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

TERMINAL_LNG = "terminal_lng"
"""La couche des terminaux d'importation de GNL."""

STOCKAGE_SOUTERRAIN = "stockage_souterrain"
"""La couche des stockages souterrains."""


@dataclass(frozen=True, slots=True)
class GasDay:
    """L'etat physique d'une installation ou d'un pays, un jour de gaz.

    Toutes les grandeurs sont en **GWh**. Les champs `remplissage` et
    `autonomie_publiee` sont ceux que **la source** publie : ils servent de
    reference, et le produit les compare a ce qu'il calcule.
    """

    installation: str
    """Le code de l'installation, ou du pays quand la source ne dit pas plus."""

    pays: str
    couche: str
    jour_gaz: date
    date_publication: datetime
    stock: float
    """Le stock en fin de journee de gaz (GWh)."""
    capacite: float
    """La capacite technique (GWh)."""
    entree: float | None
    """Ce qui entre dans l'installation (GWh/jour) : injection, reception, regazification.

    `None` quand la source **ne publie pas** l'entree — c'est le cas des
    terminaux LNG, ou le dechargement des cargaisons n'est pas une grandeur
    publiee mais se **deduit** de l'equation du stock. Une entree non
    publiee ne vaut pas zero : elle ne vaut rien, et se derive.
    """
    sortie: float
    """Ce qui en sort (GWh/jour) : soutirage, envoi reseau, chargement citernes."""
    consommation: float | None = None
    """La consommation **publiee** par la source (GWh/jour).

    Elle n'est pas le meme chose que le soutirage : c'est une donnee de la
    source, et c'est sur elle que la source fonde son autonomie publiee.
    """
    rempli: float | None = None
    """Le taux de remplissage **publie** par la source (%)."""
    autonomie_publiee: float | None = None
    """L'autonomie equivalente **publiee** par la source (jours)."""
    precision: float = 0.01
    """La precision annoncee par la source, en unites absolues."""
    nom: str = ""
    """Le nom de l'installation, tel que la source le publie."""
    latitude: float | None = None
    longitude: float | None = None
    """La position de l'installation, en degres -- elle permet la
    concentration geographique et le scenario de perte."""

    @property
    def taux_remplissage(self) -> float:
        """Le remplissage calcule, en fraction."""
        return self.stock / self.capacite if self.capacite > 0 else 0.0

    @property
    def solde(self) -> float | None:
        """Le solde du jour : ce qui entre moins ce qui sort.

        `None` quand l'entree n'est pas publiee : on ne comble pas le trou
        par un zero, on le signale.
        """
        if self.entree is None:
            return None
        return self.entree - self.sortie


def buffer_jours(stock: float, capacite: float, sortie_moyenne: float) -> float | None:
    """La reserve disponible, en jours de couverture au rythme de sortie observe.

    La reserve est ce qui se trouve au-dessus d'un minimum technique ; sans
    ce minimum, on mesure la **couverture brute**, qui est un majorant.

    `None` quand rien ne sort : la question n'a alors pas de reponse, et non
    pas une reponse infinie.
    """
    if sortie_moyenne <= 0:
        return None
    return max(stock - 0.0, 0.0) / sortie_moyenne


def taux_reconstitution(jours: Sequence[GasDay]) -> float | None:
    """La vitesse a laquelle la reserve se reconstitue, en fraction de la capacite par jour."""
    if len(jours) < 2:
        return None
    premier, dernier = jours[0], jours[-1]
    ecart = (dernier.jour_gaz - premier.jour_gaz).days
    if ecart <= 0 or dernier.capacite <= 0:
        return None
    return (dernier.stock - premier.stock) / dernier.capacite / ecart


def pression_prelevement(sortie: float, sortie_moyenne: float) -> float | None:
    """La pression de prelevement : la sortie d'aujourd'hui rapportee a sa moyenne.

    Au-dessus de 1, le systeme consomme plus vite qu'il ne l'a fait
    récemment ; en dessous de 1, il se reconstitue.
    """
    if sortie_moyenne <= 0:
        return None
    return sortie / sortie_moyenne


def concentration_herfindahl(partitions: Sequence[float]) -> float:
    """La concentration de la reserve, par les parts de Herfindahl.

    0 = la reserve est repartie uniformement ; 1 = elle est tout en un seul
    endroit. C'est la mesure de la **concentration geographique**, et elle
    n'est publiee nulle part.
    """
    total = sum(partitions)
    if total <= 0:
        return 0.0
    return sum((p / total) ** 2 for p in partitions)


def dependance_top(partitions: Sequence[float], nombre: int = 1) -> float:
    """La part de la reserve portee par les `nombre` plus gros contributeurs."""
    total = sum(partitions)
    if total <= 0:
        return 0.0
    return sum(sorted(partitions, reverse=True)[:nombre]) / total


def degradation(marges: Sequence[float]) -> float | None:
    """La degradation : la pente de la marge, en jours de couverture par jour.

    Negative quand la couverture se reserre. C'est la question « la situation
    se degrade-t-elle plus vite que prevu ? ».
    """
    if len(marges) < 2:
        return None
    pas = (marges[-1] - marges[0]) / (len(marges) - 1)
    return pas


def resilience_perte(
    couvertures: Mapping[str, float],
):
    """Ce qu'il reste de couverture si une installation disparait.

    **Scenario**, pas observation : on simule la perte d'une installation et
    on recalcule la couverture du systeme. Le resultat est le nombre de
    jours de couverture restants, ou `None` si la couverture n'est plus
    definie (personne ne sort).

    On rend le **pire cas** : la perte de l'installation dont la disparition
    fait perdre le plus de couverture.
    """
    if not couvertures:
        return None
    total = sum(v for v in couvertures.values() if v is not None)
    pire: tuple[str, float, float] | None = None
    for nom, couverture in couvertures.items():
        if couverture is None:
            continue
        restant = total - couverture
        if pire is None or restant < pire[2]:
            pire = (nom, restant, restant)
    if pire is None:
        return None
    return pire[2]


def couverture_par_installation(
    jours: Mapping[str, Sequence[GasDay]], fenetre: int = 30
) -> dict[str, float]:
    """La couverture en jours, par installation, sur la fenetre traileresse.

    Le debit de sortie retenu est la **moyenne brute** sur la fenetre : c'est
    le rythme auquel l'installation consomme reellement.
    """
    couvertures: dict[str, float] = {}
    for installation, suite in jours.items():
        if not suite:
            continue
        tranche = list(suite)[-fenetre:]
        sorties = [j.sortie for j in tranche]
        moyenne = sum(sorties) / len(sorties) if sorties else 0.0
        couverture = buffer_jours(tranche[-1].stock, tranche[-1].capacite, moyenne)
        couvertures[installation] = couverture if couverture is not None else 0.0
    return couvertures


__all__ = [
    "STOCKAGE_SOUTERRAIN",
    "TERMINAL_LNG",
    "GasDay",
    "buffer_jours",
    "concentration_herfindahl",
    "couverture_par_installation",
    "degradation",
    "dependance_top",
    "pression_prelevement",
    "resilience_perte",
    "taux_reconstitution",
]
