"""Lsupply physique des terminaux LNG : l'état quotidien, et la marge qui en est tirée.

Ce module est le **cœur de domaine** du produit `TORNE · LNG Terminal
Intelligence`. Il ne sait rien du réseau, du format de la source, ni de la
manière de télécharger quoi que ce soit : il ne connaît que des **états
quotidiens observés** et une **loi de calcul**.

Ce que le produit cherche
-------------------------

L'exploitant publie chaque jour, par terminal, l'état physique de ses cuves
et ses flux. Il ne publie **pas** la **marge** : le nombre de jours pendant
lequel le terminal pourrait continuer à fonctionner sans nouvelle réception.
C'est cette grandeur, et elle seule, qui est reconstruite ici.

Trois notions, tenues séparées
------------------------------

- l'**entrée** (`entrees_m3`) : le GNL déchargé des navires ;
- la **sortie** (`regas_m3` + `sorties_citernes_m3`) : ce qui quitte les cuves
  vers le réseau et vers les camions ;
- le **stock** (`stock_final_m3`) : ce qui reste en cuve.

Le débit retenu pour la marge est le débit **brut** : la marge répond à
« combien de jours de couverture, au rythme de sortie observé », et non
« combien de jours avant que le stock ne cesse de croître ». Un terminal qui
reçoit plus qu'il ne sort a un débit net négatif ; sa marge de couverture est
grande, et c'est le **niveau de remplissage** qui dit que le stock monte.
Confondre les deux serait refaire l'erreur que la mission a déjà commise une
fois.

Unités
------

Toutes les grandeurs physiques sont exprimées en **m³ de GNL liquide** et
en **tonnes**, jamais en GWh : la conversion énergie-masse dépend de la
convention de l'exploitant, et elle est **mesurée** par le script qui
construit la série, pas supposée. Voir `tonnes_par_gwh`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from ..contracts.model import (
    ModelInputs,
    ModelParameters,
    ModelResult,
    ModelSpec,
    ResultNature,
)

RHO_GNL_LIQUIDE = 0.456
"""Densite du GNL **liquide** en cuves, en tonnes par metre cube (vers -162 C).

C'est le volume que l'exploitant publie (`Exist.Tanques` en `m3 GNL`), et
c'est la seule base sur laquelle la masse est incontestable.
"""

TONNES_PAR_M3 = RHO_GNL_LIQUIDE * 1000.0
"""La meme densite, en kilogrammes par metre cube."""


def tonnes_par_gwh(gwh_par_m3: float) -> float:
    """Les tonnes de GNL qu'un GWh represente, pour une conversion donnee.

    Le facteur `gwh_par_m3` — les metres cubes liquides par GWh — se
    **mesure** sur la source : le rapport quotidien publie la meme grandeur
    en GWh et en m3, et leur rapport ne depend pas du terminal.
    """
    return gwh_par_m3 * RHO_GNL_LIQUIDE


@dataclass(frozen=True, slots=True)
class TerminalDay:
    """L'etat physique d'un terminal, un jour de gaz.

    Tout ce qui figure ici est **observe** : la source publie ces
    grandeurs. Ce qui est **reconstruit** — la marge, la tension — sort
    de ce module, jamais de la source.
    """

    terminal: str
    jour_gaz: date
    date_publication: datetime
    entrees_m3: float
    """Le GNL decharge des navires (m3 liquides)."""
    regas_m3: float
    """Le GNL regazifie vers le reseau (m3 liquides)."""
    sorties_citernes_m3: float
    """Le GNL charge sur des citernes routieres (m3 liquides)."""
    reexport_m3: float
    """Le GNL reexpédie sur un navire (m3 liquides)."""
    stock_initial_m3: float
    stock_final_m3: float
    remplissage: float
    """Le taux de remplissage des cuves, tel que la source le publie."""
    stock_initial_gwh: float = 0.0
    stock_final_gwh: float = 0.0
    entrees_gwh: float = 0.0
    regas_gwh: float = 0.0
    sorties_citernes_gwh: float = 0.0

    @property
    def sortie_m3(self) -> float:
        """Ce qui quitte les cuves : vers le reseau et vers les camions."""
        return self.regas_m3 + self.sorties_citernes_m3

    @property
    def solde_m3(self) -> float:
        """Le solde du jour : ce qui entre moins ce qui sort."""
        return self.entrees_m3 + self.reexport_m3 - self.sortie_m3

    @property
    def stock_final_t(self) -> float:
        """Le stock final, en tonnes."""
        return self.stock_final_m3 * RHO_GNL_LIQUIDE

    @property
    def capacite_cuve_m3(self) -> float | None:
        """La capacite des cuves, **deduite** du remplissage publie.

        Le taux de remplissage et le stock sont deux grandeurs publiees par
        la meme source : leur quotient est la capacite totale en cuves. Ce
        n'est pas une donnee declaree, c'est une derive que l'on peut
        verifier — elle doit etre stable dans le temps.
        """
        if self.remplissage <= 0:
            return None
        return self.stock_final_m3 / self.remplissage

    @property
    def delai_publication_heures(self) -> float:
        """Le decalage entre l'evenement et sa publication, en heures."""
        evenement = datetime.combine(self.jour_gaz, time.min, tzinfo=self.date_publication.tzinfo)
        return (self.date_publication - evenement).total_seconds() / 3600.0


def serie_par_terminal(jours: Sequence[TerminalDay]) -> dict[str, list[TerminalDay]]:
    """Les jours, regroupes par terminal et classes par date."""
    groupes: dict[str, list[TerminalDay]] = {}
    for jour in jours:
        groupes.setdefault(jour.terminal, []).append(jour)
    for terminal in groupes:
        groupes[terminal].sort(key=lambda j: j.jour_gaz)
    return groupes


def moyenne_fenetre(valeurs: Sequence[float], fenetre: int, jusqu_a: int) -> float:
    """La moyenne sur la fenetre traileresse."""
    debut = max(0, jusqu_a + 1 - fenetre)
    tranche = valeurs[debut : jusqu_a + 1]
    if not tranche:
        return 0.0
    return sum(tranche) / len(tranche)


def ecart_type_fenetre(valeurs: Sequence[float], fenetre: int, jusqu_a: int) -> float:
    """La dispersion sur la fenetre traileresse."""
    debut = max(0, jusqu_a + 1 - fenetre)
    tranche = list(valeurs[debut : jusqu_a + 1])
    if len(tranche) < 2:
        return 0.0
    moyenne = sum(tranche) / len(tranche)
    variance = sum((v - moyenne) ** 2 for v in tranche) / (len(tranche) - 1)
    return variance**0.5


def debit_sortie_moyen(
    terminal: Sequence[TerminalDay], fenetre: int, jusqu_a: int | None = None
) -> tuple[float, int]:
    """Le debit de sortie **brut** moyen, et le nombre de jours utilises."""
    sorties = [j.sortie_m3 for j in terminal]
    fin = len(sorties) if jusqu_a is None else min(jusqu_a + 1, len(sorties))
    if fin <= 0:
        return 0.0, 0
    debut = max(0, fin - fenetre)
    tranche = sorties[debut:fin]
    return (sum(tranche) / len(tranche), len(tranche)) if tranche else (0.0, 0)


def ecart_type_sortie(
    terminal: Sequence[TerminalDay], fenetre: int, jusqu_a: int | None = None
) -> float:
    """La dispersion du debit de sortie sur la fenetre traileresse."""
    sorties = [j.sortie_m3 for j in terminal]
    fin = len(sorties) if jusqu_a is None else min(jusqu_a + 1, len(sorties))
    if fin <= 0:
        return 0.0
    return ecart_type_fenetre(sorties, fenetre, fin - 1)


def capacite_cuve_estimee(terminal: Sequence[TerminalDay]) -> float | None:
    """La capacite des cuves, deduite du remplissage publie.

    On en prend la **mediane** : un remplissage aberrant (cuves vides,
    rapport partiel) ne doit pas entrainer la capacite.
    """
    valeurs = sorted(c for c in (j.capacite_cuve_m3 for j in terminal) if c is not None and c > 0)
    if not valeurs:
        return None
    milieu = len(valeurs) // 2
    if len(valeurs) % 2:
        return valeurs[milieu]
    return (valeurs[milieu - 1] + valeurs[milieu]) / 2


def reserve_operationnelle(stock_final_m3: float, stock_mini_m3: float) -> float:
    """La reserve exploitable : ce qui se trouve au-dessus du minimum technique."""
    return max(stock_final_m3 - stock_mini_m3, 0.0)


def marge_temporelle_jours(reserve_m3: float, debit_sortie_m3_j: float) -> float | None:
    """La marge : combien de jours de couverture au debit de sortie observe.

    `None` quand le terminal ne sort rien : la question n'a alors pas de
    reponse, et non pas une reponse infinie.
    """
    if debit_sortie_m3_j <= 0:
        return None
    return reserve_m3 / debit_sortie_m3_j


def tension(marge_jours: float | None, seuil_jours: float) -> int:
    """L'indicateur de tension : 1 si la marge passe sous le seuil."""
    if marge_jours is None:
        return 0
    return 1 if marge_jours < seuil_jours else 0


class ModelMargeOperationnelle:
    """La marge temporelle d'un terminal LNG, et l'indicateur de tension.

    La loi est simple et declaree : la **reserve** (stock au-dessus du
    minimum technique) divisee par le **debit de sortie brut** observe sur
    une fenetre traileresse. Ce qui n'est pas dans les sources, c'est
    precisement le resultat ; ce qui y est, y reste.
    """

    @property
    def spec(self) -> ModelSpec:
        """L'identite du modele : ce qu'il repond, et dans quel domaine."""
        return ModelSpec(
            model_id="torne.supply.lng.marge_operationnelle",
            version="1.0.0",
            question=(
                "Combien de jours un terminal LNG peut-il encore fonctionner "
                "au rythme de sortie observe, sans nouvelle reception ?"
            ),
            method=(
                "reserve operationnelle divisee par le debit de sortie brut "
                "moyen observe sur la fenetre traileresse"
            ),
            natures=(ResultNature.DERIVED,),
            assumptions=(
                "le minimum technique des cuves est une fraction de la capacite "
                "deduite du taux de remplissage publie",
                "le debit de sortie de la fenetre traileresse se prolonge : "
                "aucune reception future n'est supposee",
                "le volume publie par l'exploitant est du GNL liquide en cuves",
            ),
            domain_of_validity=(
                "terminaux LNG d'importation du systeme gaziste espagnol, "
                "a l'echelle du jour de gaz"
            ),
        )

    def run(
        self,
        inputs: ModelInputs,
        params: ModelParameters,
        *,
        now: datetime | None = None,
        seed: int | None = None,
    ) -> ModelResult:
        """La marge, jour par jour."""
        del now, seed  # la loi est deterministe

        stock = inputs.series["stock_final_m3"]
        regas = inputs.series["regas_m3"]
        citernes = inputs.series["sorties_citernes_m3"]
        remplissage = inputs.series["remplissage"]
        entrees = inputs.series.get("entrees_m3", (0.0,) * len(stock))
        if not (len(stock) == len(regas) == len(citernes) == len(remplissage) == len(entrees)):
            raise ValueError("les series doivent avoir la meme longueur")

        fenetre = int(params.values.get("fenetre_jours", 30) or 30)
        seuil = float(params.values.get("seuil_tension_jours", 3.0) or 3.0)
        fraction_mini = float(params.values.get("stock_mini_frac", 0.10) or 0.10)
        incertitude_mini = float(params.values.get("stock_mini_incertitude", 0.05) or 0.05)
        incertitude_debit = float(params.values.get("debit_incertitude_k", 1.0) or 1.0)

        capacite = capacite_cuve_m3(stock, remplissage)
        stock_mini = capacite * fraction_mini if capacite is not None else 0.0

        sorties = [r + c for r, c in zip(regas, citernes, strict=True)]
        marges: list[float] = []
        reserves: list[float] = []
        tensions: list[float] = []
        taux_nets: list[float] = []
        intervalles: list[tuple[float, float]] = []

        for index in range(len(stock)):
            fenetre_effective = moyenne_fenetre(sorties, fenetre, index)
            reserve = reserve_operationnelle(stock[index], stock_mini)
            taux_nets.append(
                moyenne_fenetre(
                    [e - s for e, s in zip(entrees, sorties, strict=True)], fenetre, index
                )
            )
            if fenetre_effective <= 0:
                marges.append(0.0)
                intervalles.append((0.0, 0.0))
                tensions.append(0)
                reserves.append(reserve)
                continue
            dispersion = ecart_type_fenetre(sorties, fenetre, index)
            marge = reserve / fenetre_effective
            # La reserve est incertaine (minimum technique) et le debit aussi
            # (dispersion de la fenetre) : les deux bornes se propagent.
            mini_haut = stock_mini * (1 + incertitude_mini)
            mini_bas = stock_mini * (1 - incertitude_mini)
            debit_haut = fenetre_effective + incertitude_debit * dispersion
            debit_bas = max(fenetre_effective - incertitude_debit * dispersion, 1e-9)
            borne_haut = max(reserve_operationnelle(stock[index], mini_bas), 0.0) / debit_bas
            borne_bas = max(reserve_operationnelle(stock[index], mini_haut), 0.0) / debit_haut
            marges.append(marge)
            intervalles.append((min(borne_bas, borne_haut), max(borne_bas, borne_haut)))
            tensions.append(tension(marge, seuil))
            reserves.append(reserve)

        return ModelResult(
            spec=self.spec,
            nature=ResultNature.DERIVED,
            parameters=params,
            produced_at=datetime.now(UTC),
            outputs={
                "reserve_m3": tuple(reserves),
                "marge_jours": tuple(marges),
                "tension": tuple(float(t) for t in tensions),
                "taux_net_m3_j": tuple(taux_nets),
            },
            intervals={"marge_jours": tuple(intervalles)},
            output_natures={
                "reserve_m3": ResultNature.DERIVED,
                "marge_jours": ResultNature.DERIVED,
                "tension": ResultNature.DERIVED,
                "taux_net_m3_j": ResultNature.DERIVED,
            },
            diagnostics={
                "jours": float(len(stock)),
                "capacilite_cuve_m3": capacite or 0.0,
                "stock_mini_m3": stock_mini,
                "debit_sortie_moyen_m3_j": (sum(sorties) / len(sorties)) if sorties else 0.0,
                "jours_en_tension": float(sum(tensions)),
                "marge_mediane_jours": (sorted(marges)[len(marges) // 2] if marges else 0.0),
            },
        )


def capacite_cuve_m3(stock: Sequence[float], remplissage: Sequence[float]) -> float | None:
    """La capacite des cuves, deduite du remplissage publie (mediane)."""
    valeurs = sorted(s / r for s, r in zip(stock, remplissage, strict=True) if r > 0 and s > 0)
    if not valeurs:
        return None
    milieu = len(valeurs) // 2
    if len(valeurs) % 2:
        return valeurs[milieu]
    return (valeurs[milieu - 1] + valeurs[milieu]) / 2


__all__ = [
    "RHO_GNL_LIQUIDE",
    "TONNES_PAR_M3",
    "ModelMargeOperationnelle",
    "TerminalDay",
    "capacite_cuve_estimee",
    "capacite_cuve_m3",
    "debit_sortie_moyen",
    "ecart_type_fenetre",
    "ecart_type_sortie",
    "marge_temporelle_jours",
    "moyenne_fenetre",
    "reserve_operationnelle",
    "serie_par_terminal",
    "tension",
    "tonnes_par_gwh",
]
