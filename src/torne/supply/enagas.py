"""Le decodeur du suivi quotidien : du rapport JSON a un etat de terminal.

C'est ici que le rapport de l'exploitant devient un **etat physique** : des
volumes de GNL liquide, un stock en cuve, un taux de remplissage, et les
deux dates — celle de l'evenement et celle de la publication.

Trois proprietes de la source qui rendent le travail possible
-------------------------------------------------------------

1. Le rapport est **indexe par nom de terminal** : il n'y a pas de
   colonnes a aligner. C'est la difference avec la version tableur, ou une
   ligne decalee d'une colonne attribuait un volume au mauvais terminal —
   une derive que rien ne signalait.

2. La meme grandeur est publiee **deux fois**, en GWh et en m3 liquides.
   Leur rapport se **mesure** sur le document : c'est la conversion
   energie-masse, lue chez l'exploitant, et non supposee.

3. Le rapport porte son **instant de publication** (`lastDate`). C'est ce
   qui permet de dire, pour chaque observation, a la fois *quand
   l'evenement a eu lieu* et *quand on a pu le savoir* — la deuxieme date
   est ce qui fait la valeur d'une donnee en avance.

Le controle qui reste
---------------------

Chaque grandeur porte une cle `Total Plantas`, qui doit etre la somme des
sept terminaux. L'ecart maximal est conserve : sans lui, une erreur de
saisie chez l'exploitant passerait inapercue.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .lng import TerminalDay

TOLERANCE = 1e-3
"""L'ecart relatif admis entre un total et la somme des terminaux."""

CLE_TOTAL = "Total Plantas"
"""La cle du total, dans chaque grandeur du rapport."""


@dataclass(frozen=True, slots=True)
class LectureJour:
    """Ce qu'un jour de rapport porte."""

    jour_gaz: date
    date_publication: datetime
    terminaux: tuple[TerminalDay, ...]
    facteur_m3_par_gwh: float
    """Les metres cubes liquides par GWh, mesures sur le document."""
    ecart_controle: float
    """Le plus grand ecart relatif entre un total et la somme des terminaux."""


def _nombres(valeurs: Mapping[str, str]) -> dict[str, float]:
    """Les valeurs numeriques d'une grandeur, par terminal."""
    resultat: dict[str, float] = {}
    for cle, brut in valeurs.items():
        try:
            resultat[cle] = float(brut)
        except (TypeError, ValueError):
            continue
    return resultat


def _ter_minaux(rapport: Mapping[str, object]) -> tuple[str, ...]:
    """Les terminaux, dans l'ordre du rapport."""
    grandeurs = [
        valeur for valeur in rapport.values() if isinstance(valeur, dict) and CLE_TOTAL in valeur
    ]
    if not grandeurs:
        return ()
    return tuple(cle for cle in grandeurs[0] if cle != CLE_TOTAL)


GRANDEUR_NON_ADDITIVE = ("tankFinalStocksFilling",)
"""Les grandeurs dont le total n'est **pas** une somme.

Le taux de remplissage est une moyenne ponderee : son `Total Plantas` ne
s'additionne pas. Le control par le total ne doit donc pas s'y appliquer.
"""


def _controle(rapport: Mapping[str, object]) -> float:
    """Le plus grand ecart relatif entre un total et la somme des terminaux."""
    ecart = 0.0
    for nom, valeur in rapport.items():
        if nom in GRANDEUR_NON_ADDITIVE:
            continue
        if not isinstance(valeur, dict) or CLE_TOTAL not in valeur:
            continue
        nombres = _nombres(valeur)
        total = nombres.get(CLE_TOTAL)
        if total is None:
            continue
        somme = sum(v for cle, v in nombres.items() if cle != CLE_TOTAL)
        if total == 0 and somme == 0:
            continue
        ecart = max(ecart, abs(total - somme) / max(abs(total), 1e-9))
    return ecart


def _facteur(rapport: Mapping[str, object]) -> float:
    """Les metres cubes liquides par GWh, mesures sur le document."""
    paires = (
        ("tankInitialStocksGWh", "tankInitialStocksM3"),
        ("tankFinalStocksGwh", "tankFinalStocksM3"),
        ("regasificationGWh", "regasificationM3"),
    )
    facteurs: list[float] = []
    for cle_gwh, cle_m3 in paires:
        gauche = rapport.get(cle_gwh)
        droite = rapport.get(cle_m3)
        if not isinstance(gauche, dict) or not isinstance(droite, dict):
            continue
        gwh = _nombres(gauche)
        m3 = _nombres(droite)
        for terminal, valeur in gwh.items():
            if terminal == CLE_TOTAL or valeur <= 0:
                continue
            cible = m3.get(terminal)
            if cible is not None:
                facteurs.append(cible / valeur)
    return sum(facteurs) / len(facteurs) if facteurs else 0.0


def _instant_publication(charge: Mapping[str, object]) -> datetime:
    """L'instant de publication, tel que le rapport le declare."""
    texte = str(charge.get("lastDate") or "").strip()
    trouve = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", texte)
    if not trouve:
        return datetime.now(UTC)
    return datetime(
        int(trouve.group(3)),
        int(trouve.group(2)),
        int(trouve.group(1)),
        int(trouve.group(4)),
        int(trouve.group(5)),
        tzinfo=UTC,
    )


def decoder_json(charge: Mapping[str, object], jour_gaz: date) -> LectureJour | None:
    """Le rapport JSON, decode en etats de terminaux.

    Rend `None` si le rapport ne porte pas ce qu'il doit porter — y compris
    si un total ne correspond pas a la somme des terminaux.
    """
    rapport = charge.get("gasSystemPPDDataReportPojo")
    if not isinstance(rapport, dict):
        return None
    terminaux = _ter_minaux(rapport)
    if not terminaux:
        return None
    ecart = _controle(rapport)
    if ecart > TOLERANCE:
        return None
    facteur = _facteur(rapport)

    def valeur(cle: str, terminal: str, defaut: float = 0.0) -> float:
        bloc = rapport.get(cle)
        if not isinstance(bloc, dict):
            return defaut
        return _nombres(bloc).get(terminal, defaut)

    publication = _instant_publication(charge)
    etats: list[TerminalDay] = []
    for terminal in terminaux:
        remplissage = valeur("tankFinalStocksFilling", terminal)
        etats.append(
            TerminalDay(
                terminal=terminal,
                jour_gaz=jour_gaz,
                date_publication=publication,
                entrees_m3=valeur("downloadsGNL", terminal),
                regas_m3=valeur("regasificationM3", terminal),
                sorties_citernes_m3=valeur("cisternLoad", terminal) * facteur,
                reexport_m3=valeur("loadsGNL", terminal),
                stock_initial_m3=valeur("tankInitialStocksM3", terminal),
                stock_final_m3=valeur("tankFinalStocksM3", terminal),
                # La source publie un pourcentage, pas une fraction.
                remplissage=remplissage / 100.0,
                entrees_gwh=0.0,
                regas_gwh=valeur("regasificationGWh", terminal),
                sorties_citernes_gwh=valeur("cisternLoad", terminal),
                stock_initial_gwh=valeur("tankInitialStocksGWh", terminal),
                stock_final_gwh=valeur("tankFinalStocksGwh", terminal),
            )
        )
    return LectureJour(
        jour_gaz=jour_gaz,
        date_publication=publication,
        terminaux=tuple(etats),
        facteur_m3_par_gwh=facteur,
        ecart_controle=ecart,
    )


__all__ = [
    "CLE_TOTAL",
    "TOLERANCE",
    "LectureJour",
    "decoder_json",
]
