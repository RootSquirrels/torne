"""La couche des terminaux LNG europeens : l'etat par installation, et ce
qu'on en tire quand l'installation elle-meme ne publie rien.

Ce module complete `torne.supply.gas`, qui decrit l'etat d'une installation ou
d'un pays, pour la couche **terminal**. ALSI publie, pour chaque terminal et
chaque jour de gaz :

- le **stock** en cuves, en GWh (`inventory.gwh`) et en milliers de m3
  (`inventory.lng`) ;
- la **capacite** technique, dans les memes deux unites (`dtmi`) ;
- le **debit sortant** vers le reseau (`sendOut`), en GWh/jour ;
- la **position** du terminal (latitude, longitude) et son **type** (LAND,
  FSRU, ...).

Ce qu'ALSI ne publie pas
-------------------------

**Le dechargement des cargaisons.** L'entree dans les cuves n'est pas une
grandeur publiee : elle n'est ni mise a zero, ni deduite d'un document, elle
n'existe pas dans la source. Elle peut en revanche etre **rederivee** de
l'equation du stock :

    entree(j) = stock(j) - stock(j-1) + sortie(j)

C'est une **reconstruction**, pas une observation : elle est notee comme telle
(voir `dechargement_derive`), et elle ne vaut que si l'echantillon est
consecutif. Elle donne enfin le **flux d'importation par terminal**, que
personne ne publie pour l'Europe.

Les trois natures, tenues separees
----------------------------------

- **observe** : le stock, la capacite, le debit sortant, la position — la
  source les publie ;
- **calcule** : la reserve operationnelle, la marge en jours, le dechargement
  derive, la concentration, la degradation ;
- **simule** : le scenario de perte d'une installation.

La couverture : la meme loi que le produit espagnol
---------------------------------------------------

La loi de la marge est celle du produit `LNG Terminal Intelligence`, reprise
sans changement : la **reserve** — le stock au-dessus du minimum technique —
divisee par le **debit de sortie brut** moyen observe sur la fenetre
traileresse. Le debit est **brut**, jamais net : un terminal qui recoit plus
qu'il ne sort a un solde negatif, et sa couverture de consommation n'a pas
pour autant disparu.

Le minimum technique est un **parametre**, pas une donnee : ici, comme dans le
produit espagnol, il vaut 10 % de la capacite technique.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from .gas import GasDay, concentration_herfindahl, dependance_top

_UN_JOUR = timedelta(days=1)

STOCK_MINI_FRAC = 0.10
"""La part de la capacite technique qui constitue le minimum technique.

Sous ce seuil, le terminal ne regazifie plus dans de bonnes conditions : le
stock n'est plus disponible pour le marche. C'est un **parametre**, declare
comme tel, et il conditionne toute la marge.
"""

FENETRE_JOURS = 30
"""La fenetre traileresse, en jours de gaz, pour le debit de sortie moyen."""

SEUIL_TENSION_JOURS = 3.0
"""Sous ce nombre de jours de couverture, l'installation est en tension."""


def serie_par_installation(jours: Sequence[GasDay]) -> dict[str, list[GasDay]]:
    """Les jours, regroupes par installation et classes par jour de gaz."""
    groupes: dict[str, list[GasDay]] = {}
    for jour in jours:
        groupes.setdefault(jour.installation, []).append(jour)
    for installation in groupes:
        groupes[installation].sort(key=lambda j: j.jour_gaz)
    return groupes


def reserve_operationnelle(
    stock: float,
    capacite: float,
    stock_mini_frac: float = STOCK_MINI_FRAC,
) -> float:
    """La reserve exploitable : ce qui se trouve au-dessus du minimum technique."""
    return max(stock - stock_mini_frac * capacite, 0.0)


def debit_sortie_moyen(
    suite: Sequence[GasDay],
    fenetre: int = FENETRE_JOURS,
    jusqu_a: int | None = None,
) -> tuple[float, int]:
    """Le debit de sortie **brut** moyen sur la fenetre traileresse.

    Rend le debit et le nombre de jours utilises : une fenetre trop courte
    pour etre significative doit se voir, pas se cacher dans une moyenne.
    """
    sorties = [j.sortie for j in suite]
    fin = len(sorties) if jusqu_a is None else min(jusqu_a + 1, len(sorties))
    if fin <= 0:
        return 0.0, 0
    tranche = sorties[max(0, fin - fenetre) : fin]
    if not tranche:
        return 0.0, 0
    return sum(tranche) / len(tranche), len(tranche)


def marge_installation(
    suite: Sequence[GasDay],
    fenetre: int = FENETRE_JOURS,
    stock_mini_frac: float = STOCK_MINI_FRAC,
) -> list[float]:
    """La marge, jour par jour : la reserve divisee par le debit de sortie moyen.

    La meme loi que le produit espagnol (`torne.supply.lng`), reprise telle
    quelle : la reserve exploitable divisee par le debit **brut** observe sur
    la fenetre traileresse. Aucun prix, aucune hypothese de marche : la seule
    question posee est « combien de jours, au rythme observe ».

    Une installation qui ne sort rien donne une couverture nulle : la question
    n'a pas de reponse, et non pas une reponse infinie.
    """
    marges: list[float] = []
    for index in range(len(suite)):
        debit, _ = debit_sortie_moyen(suite, fenetre, index)
        if debit <= 0:
            marges.append(0.0)
            continue
        reserve = reserve_operationnelle(suite[index].stock, suite[index].capacite, stock_mini_frac)
        marges.append(reserve / debit)
    return marges


def jours_en_tension(marges: Sequence[float], seuil: float = SEUIL_TENSION_JOURS) -> int:
    """Le nombre de jours ou la couverture est tombee sous le seuil."""
    return sum(1 for marge in marges if marge < seuil)


def degradation_installation(suite: Sequence[GasDay], fenetre: int = FENETRE_JOURS) -> float | None:
    """La degradation de la couverture, en jours par jour.

    Negative quand la couverture se resserre : c'est la question « la situation
    se degrade-t-elle plus vite que prevu ? », posee au niveau de
    l'installation et non du pays.
    """
    marges = marge_installation(suite, fenetre)
    if len(marges) < 2:
        return None
    pas = (marges[-1] - marges[0]) / (len(marges) - 1)
    return pas


def dechargement_derive(suite: Sequence[GasDay]) -> list[float | None]:
    """Le dechargement des cargaisons, **derive** de l'equation du stock.

        entree(j) = stock(j) - stock(j-1) + sortie(j)

    Le premier jour n'a pas de jour precedent : il n'a donc pas de dechargement
    derive, et ne vaut pas zero.

    La grandeur est une **reconstruction**, pas une observation : elle herite
    du bruit de la source, et elle suppose que le stock publie est bien le
    stock de fin de journee de gaz. Elle est donc notee comme derivee, et
    elle ne remplace jamais l'entree publiee quand la source en donne une.
    """
    resultat: list[float | None] = []
    for index in range(len(suite)):
        if index == 0:
            resultat.append(None)
            continue
        if suite[index].jour_gaz - suite[index - 1].jour_gaz != _UN_JOUR:
            resultat.append(None)
            continue
        resultat.append(suite[index].stock - suite[index - 1].stock + suite[index].sortie)
    return resultat


def etats_reference(
    jours: Mapping[str, Sequence[GasDay]],
) -> tuple[date, dict[str, GasDay], dict[str, int]]:
    """L'etat de reference de chaque installation, et sa fraicheur.

    La date de reference est le jour de gaz le plus recent **connu** de
    l'ensemble. Chaque installation est prise a son dernier etat anterieur ou
    egal a cette date, et l'ecart en jours est rendu : une installation
    dont la donnee est vieille de huit jours n'est pas une installation
    holding de la meme facon qu'une autre — et le produit doit le dire.
    """
    tous = [j for suite in jours.values() for j in suite]
    if not tous:
        raise ValueError("aucun etat : la reference n'a pas de sens")
    reference = max(j.jour_gaz for j in tous)
    etats: dict[str, GasDay] = {}
    fraicheur: dict[str, int] = {}
    for installation, suite in jours.items():
        eligibles = [j for j in suite if j.jour_gaz <= reference]
        if not eligibles:
            continue
        dernier = max(eligibles, key=lambda j: j.jour_gaz)
        etats[installation] = dernier
        fraicheur[installation] = (reference - dernier.jour_gaz).days
    return reference, etats, fraicheur


def concentration_reserve(etats: Mapping[str, GasDay]) -> dict[str, float]:
    """La concentration de la reserve, au niveau des installations.

    Le Herfindahl des parts de stock : 0 = reserve repartie uniformement,
    1 = toute la reserve en un seul terminal. La part du premier et des trois
    premiers complete la lecture — ce sont les deux chiffres qu'un exploitant
    regarde, et qu'aucune source ne publie.
    """
    stocks = [e.stock for e in etats.values() if e.stock > 0]
    if not stocks:
        return {"herfindahl": 0.0, "part_premier": 0.0, "part_trois": 0.0, "total_gwh": 0.0}
    return {
        "herfindahl": concentration_herfindahl(stocks),
        "part_premier": dependance_top(stocks, 1),
        "part_trois": dependance_top(stocks, 3),
        "total_gwh": sum(stocks),
    }


def dependance_pays(etats: Mapping[str, GasDay]) -> dict[str, dict[str, float]]:
    """La dependance du systeme a chaque pays.

    Pour chaque pays : la part de la reserve qu'il porte, la part de la
    capacite, la part du debit sortant. Un pays qui detient 40 % de la
    reserve mais ne fait sortir que 5 % du flux est un pays qui **stocke**
    plutot qu'il ne sert : c'est une dependance, et elle n'est dans aucune
    publication.
    """
    total_stock = sum(e.stock for e in etats.values())
    total_capacite = sum(e.capacite for e in etats.values())
    total_sortie = sum(e.sortie for e in etats.values())
    par_pays: dict[str, dict[str, float]] = {}
    for etat in etats.values():
        bloc = par_pays.setdefault(
            etat.pays,
            {"stock_gwh": 0.0, "capacite_gwh": 0.0, "sortie_gwh_j": 0.0, "terminaux": 0.0},
        )
        bloc["stock_gwh"] += etat.stock
        bloc["capacite_gwh"] += etat.capacite
        bloc["sortie_gwh_j"] += etat.sortie
        bloc["terminaux"] += 1
    for bloc in par_pays.values():
        bloc["part_stock"] = bloc["stock_gwh"] / total_stock if total_stock > 0 else 0.0
        bloc["part_capacite"] = bloc["capacite_gwh"] / total_capacite if total_capacite > 0 else 0.0
        bloc["part_sortie"] = bloc["sortie_gwh_j"] / total_sortie if total_sortie > 0 else 0.0
    return par_pays


def concentration_geographique(par_pays: Mapping[str, Mapping[str, float]]) -> float:
    """La concentration **geographique** : le Herfindahl des parts par pays.

    Distincte de la concentration par installation : une reserve portee par
    trois terminaux d'un seul pays est peu concentree au sens du terminal, et
    tres concentree au sens du pays — c'est cette seconde lecture qui parle de
    dependance politique.
    """
    parts = [bloc["part_stock"] for bloc in par_pays.values()]
    return concentration_herfindahl(parts)


def couverture_systeme(
    jours: Mapping[str, Sequence[GasDay]],
    fenetre: int = FENETRE_JOURS,
    stock_mini_frac: float = STOCK_MINI_FRAC,
) -> tuple[float, float, float]:
    """La couverture du systeme entier : la reserve totale, le debit total, et
    les jours de couverture qui en resulted.

    Le systeme ne se regazifie pas tout seul : la couverture du systeme est
    la reserve totale divisee par le debit total **brut**. Elle est le
    referentiel du scenario de perte.
    """
    _, etats, _ = etats_reference(jours)
    if not etats:
        return 0.0, 0.0, 0.0
    reserve = sum(
        reserve_operationnelle(e.stock, e.capacite, stock_mini_frac) for e in etats.values()
    )
    debit = 0.0
    for installation, suite in jours.items():
        if installation not in etats:
            continue
        index = max(
            (i for i, j in enumerate(suite) if j.jour_gaz == etats[installation].jour_gaz),
            default=None,
        )
        if index is None:
            continue
        moyenne, _ = debit_sortie_moyen(suite, fenetre, index)
        debit += moyenne
    couverture = reserve / debit if debit > 0 else 0.0
    return reserve, debit, couverture


def scenario_perte(
    jours: Mapping[str, Sequence[GasDay]],
    installation: str,
    fenetre: int = FENETRE_JOURS,
    stock_mini_frac: float = STOCK_MINI_FRAC,
) -> dict[str, float] | None:
    """Ce qu'il reste si une installation tombe.

    **Scenario**, pas observation : on simule la disparition d'un terminal et
    on recalcule la couverture du systeme. Le resultat dit ce que la perte
    coute en jours de couverture — et non pas ce qu'elle coute en GWh, que
    tout le monde sait deja lire.

    `None` si l'installation n'existe pas dans la serie.
    """
    if installation not in jours:
        return None
    _, etats, _ = etats_reference(jours)
    if installation not in etats:
        return None
    reserve, debit, couverture = couverture_systeme(jours, fenetre, stock_mini_frac)
    etat = etats[installation]
    reserve_perdue = reserve_operationnelle(etat.stock, etat.capacite, stock_mini_frac)
    suite = jours[installation]
    index = max(
        (i for i, j in enumerate(suite) if j.jour_gaz == etat.jour_gaz),
        default=None,
    )
    debit_perdu = 0.0
    if index is not None:
        debit_perdu, _ = debit_sortie_moyen(suite, fenetre, index)
    debit_restant = max(debit - debit_perdu, 0.0)
    reserve_restante = max(reserve - reserve_perdue, 0.0)
    couverture_apres = reserve_restante / debit_restant if debit_restant > 0 else 0.0
    return {
        "installation": installation,
        "couverture_avant_jours": couverture,
        "couverture_apres_jours": couverture_apres,
        "jours_perdus": couverture - couverture_apres,
        "reserve_perdue_gwh": reserve_perdue,
        "debit_perdu_gwh_j": debit_perdu,
        "part_reserve_perdue": (reserve_perdue / reserve if reserve > 0 else 0.0),
    }


__all__ = [
    "FENETRE_JOURS",
    "SEUIL_TENSION_JOURS",
    "STOCK_MINI_FRAC",
    "concentration_geographique",
    "concentration_reserve",
    "couverture_systeme",
    "debit_sortie_moyen",
    "dechargement_derive",
    "degradation_installation",
    "dependance_pays",
    "etats_reference",
    "jours_en_tension",
    "marge_installation",
    "reserve_operationnelle",
    "scenario_perte",
    "serie_par_installation",
]
