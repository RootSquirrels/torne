"""L'adaptateur NOAA GHCN-Daily — poser la question, et la vérifier.

GHCN-Daily est l'archive quotidienne internationale du réseau historique
climatologique, tenue par le National Centers for Environmental Information
(NOAA). Elle est retenue ici pour une raison précise : **elle est accessible
sans compte, sans clé et sans secret**, et elle porte les **drapeaux de
qualité** de son producteur — ce que la plupart des archives ouvertes ne
publient pas.

Ce module ne sait **rien interpréter**. Il construit une URL, constate qu'il
n'y a rien après, et — c'est son travail propre — **vérifie que ce qui est
revenu répond à la question posée**.

Le piège que cet adaptateur ferme
--------------------------------

Le service d'accès de NCEI répond **HTTP 200 avec une page HTML d'erreur**
quand le fichier demandé n'existe pas (constaté le 1ᵉʳ novembre 2026 sur
`global-hourly/access/2026/`, qui rend un document S3 « All Rights Reserved »
avec le code 200). Un contrôle qui ne regarde que le code HTTP laisse passer
cette page comme si elle était des observations.

LaConformité de cette source est donc vérifiée **sur le contenu** : la
première ligne doit être un en-tête CSV portant les colonnes attendues. Une
réponse 200 qui n'est pas un CSV de données ne rend aucun critère vérifiable,
et le verdict est alors l'abstention — jamais l'accord.

Le second piège : **une valeur de GHCN-D n'a pas de date de publication**.
L'archive est rééditee chaque jour, et le producteur ne dit pas, pour une
valeur donnée, quand elle est devenue publique. C'est écrit dans la
`revision_policy` de la source, et cela signifie que ces observations ne sont
jamais admissibles en reconstitution point-in-time (INV-10) : elles décrivent
le passé, elles ne le rejouent pas.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from typing import Any

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

SOURCE_ID = "noaa.ghcnd.daily"
"""Identifiant de la source, tel qu'il est consigné dans le journal."""

PRODUCTEUR = "NOAA National Centers for Environmental Information (NCEI)"
"""Le producteur de l'archive, tel qu'il le déclare."""

DATASET = "GHCN-Daily"
"""Le jeu de données, tel que NCEI le nomme dans son `readme.txt`."""

ACCESS_POINT = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access"
"""Le point d'accès public, sans authentification."""

LICENCE = "domaine public — œuvre du gouvernement des États-Unis (NOAA/NCEI)"
"""Conditions d'usage déclarées par le producteur."""

REVISION = (
    "GHCN-Daily est réédité quotidiennement ; la version du jeu est lue dans "
    "`ghcnd-version.txt` et consignée avec la preuve. NCEI ne publie aucun "
    "horodatage de publication par valeur : la date de publication d'une "
    "valeur est INCONNUE (classe N), et l'observation n'est donc jamais "
    "admissible en reconstitution point-in-time (INV-10)."
)

COLONNE_STATION = "STATION"
COLONNE_DATE = "DATE"
COLONNES_FIXES = (COLONNE_STATION, COLONNE_DATE, "LATITUDE", "LONGITUDE", "ELEVATION", "NAME")

ELEMENTS_PUBLIES = (
    "TMAX",
    "TMIN",
    "TAVG",
    "PRCP",
    "SNWD",
    "SNOW",
    "AWND",
    "ASLP",
    "ASTP",
    "PSUN",
    "RHAV",
    "RHMN",
    "RHMX",
)
"""Les éléments que TORNE sait demander. La source en publie d'autres ; ce
n'est pas à l'adaptateur d'inventer la grammaire des autres."""


class GhcndDailyAdapter:
    """Les relevés quotidiens d'**une** station GHCN.

    La source ne se parcourt pas : elle rend la période de record complète de
    la station en une seule réponse. L'adaptateur le dit (`declares_exhaustion`
    vaut `False`), et la conformité est donc vérifiée page par page — sur une
    page unique.
    """

    def __init__(
        self,
        station_id: str,
        *,
        elements: Sequence[str] = ("TMAX", "TMIN", "PRCP"),
        label: str | None = None,
    ) -> None:
        if not isinstance(station_id, str) or not station_id.strip():
            raise ValueError("station_id est obligatoire et non vide")
        inconnus = sorted(set(elements) - set(ELEMENTS_PUBLIES))
        if inconnus:
            raise ValueError(f"élément(s) non publié(e)s par la source : {inconnus}")

        self.station_id = station_id.strip().upper()
        self.elements = tuple(elements)
        self._label = label

    # ------------------------------------------------------------------
    # Ce que l'adaptateur sait de la source
    # ------------------------------------------------------------------

    @property
    def source(self) -> Source:
        """La source, telle que le socle la consigne."""
        return Source(
            source_id=SOURCE_ID,
            producer=PRODUCTEUR,
            dataset=DATASET,
            access_point=ACCESS_POINT,
            license=LICENCE,
            revision_policy=REVISION,
            unit=None,
            timezone=None,
            quality_status=None,
        )
        """L'unité est laissée absente : GHCN-Daily publie des températures en
        dixièmes de degré, des précipitations en dixièmes de millimètre et des
        pressions en dixièmes de hectopascal — **une seule source, plusieurs
        unités**. L'unité appartient au couple (élément, mesure), pas à la
        source, et elle est donc portée par la couche sémantique."""

    @property
    def declares_exhaustion(self) -> bool:
        """La source ne déclare rien : elle rend tout d'un coup.

        Une réponse réussie ne prouve donc pas que NCEI avait tout à rendre.
        """
        return False

    # ------------------------------------------------------------------
    # Les questions
    # ------------------------------------------------------------------

    def initial_request(self) -> AcquisitionRequest:
        """La question : le fichier de la station."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=f"{ACCESS_POINT}/{self.station_id}.csv",
            method="GET",
            pagination=PaginationStrategy.NONE,
            max_pages=1,
            label=self._label or f"ghcnd:{self.station_id}",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """Il n'y a pas de page suivante : la source en rend une seule."""
        return None

    # ------------------------------------------------------------------
    # La conformité : ce qui a été demandé, ce qui a été reçu
    # ------------------------------------------------------------------

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """La page répond-elle à la question posée ?

        Deux critères sont posés, et chacun est **vérifié sur le contenu
        reçu** :

        - `station` — chaque ligne porte l'identifiant de la station demandée ;
        - `elements` — l'en-tête porte une colonne pour chaque élément demandé.

        Il n'y a **pas** de critère de fenêtre, et c'est un choix : le point
        d'accès de NCEI rend toujours la période de record complète, il ne
        sait pas borner une période. Un adaptateur qui prometrait une
        fenêtre à la source prometrait une violation : c'est vérifié le
        1ᵉʳ novembre 2026, où une demande 2015-2025 a rendu 1944-2026 et a
        été refusée comme non conforme. La fenêtre est donc un **filtre
        appliqué après coup**, sur les observations, et jamais une promesse
        faite à la source.

        Un critère dont le champ correspondant est absent du corps de la
        réponse n'est pas « violé » : il est **non vérifiable**, et il produit
        une abstention. C'est ce qui arrive d'une page d'erreur HTML servie
        avec un code 200.
        """
        criteres: dict[str, CritereConformite] = {}

        lignes, entete = _lire_csv(response.text())
        if entete is None:
            return verdict_from_criteria(
                {
                    "contenu": CritereConformite(
                        demande="a body whose first line is the expected CSV header",
                        verifie=False,
                        recu="the body does not begin with a CSV header: it is not data",
                    )
                }
            )

        criteres["station"] = self._criterion_station(lignes)
        criteres["elements"] = self._criterion_elements(entete)

        return verdict_from_criteria(criteres)

    # -- les trois critères ----------------------------------------------

    def _criterion_station(self, lignes: list[dict[str, str]]) -> CritereConformite:
        """Toutes les lignes portent-elles la station demandée ?"""
        demande = f"records of the station {self.station_id} only"
        if not lignes:
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu="the file carries a header but no record",
            )
        autres = sorted(
            {
                ligne.get(COLONNE_STATION, "").strip()
                for ligne in lignes
                if ligne.get(COLONNE_STATION, "").strip() != self.station_id
            }
        )
        if autres:
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu=f"records of station(s) {', '.join(autres)}",
                conforme=False,
            )
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=f"{len(lignes)} records, all of station {self.station_id}",
            conforme=True,
        )

    def _criterion_elements(self, entete: list[str]) -> CritereConformite:
        """L'en-tête porte-t-il une colonne pour chaque élément demandé ?"""
        demande = f"a column for each requested element ({', '.join(self.elements)})"
        absents = [element for element in self.elements if element not in entete]
        if absents:
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu=f"the header carries no column for {', '.join(absents)}",
            )
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=f"the header carries {', '.join(self.elements)}",
            conforme=True,
        )

    def _criterion_fenetre(self, lignes: list[dict[str, str]]) -> CritereConformite:
        """Les lignes tombent-elles dans la fenêtre demandée ?

        Inutilisé par GHCN-Daily : le point d'accès rend toujours la période
        de record complète, et l'adaptateur ne promet donc pas de fenêtre
        qu'il ne pourrait pas vérifier.
        """
        raise NotImplementedError(
            "le point d'accès de GHCN-Daily ne sait pas borner une période : "
            "la fenêtre se filtre après coup, sur les observations"
        )


def _lire_csv(texte: str) -> tuple[list[dict[str, str]], list[str] | None]:
    """Le corps, lu comme un CSV GHCN-Daily — ou rien du tout.

    Une page d'erreur HTML servie avec un code 200 n'a **pas** d'en-tête
    CSV : elle est ici refusée comme non-conforme, au lieu d'être lue comme
    une absence de données.
    """
    if not texte.strip():
        return [], None
    premiere = texte.lstrip().splitlines()[0]
    if not premiere.startswith(f"{COLONNE_STATION},") and COLONNE_STATION not in premiere:
        return [], None
    lecteur = csv.DictReader(io.StringIO(texte))
    entete = list(lecteur.fieldnames or [])
    lignes = [dict(ligne) for ligne in lecteur]
    return lignes, entete


def ligne_brute(ligne: dict[str, Any], element: str) -> tuple[str | None, str | None]:
    """La valeur brute et les drapeaux bruts d'un élément dans une ligne.

    Les drapeaux sont rendus **tels quels**, dans l'ordre que NCEI publie :
    drapeau de mesure, drapeau de qualité, drapeau de source.
    """
    valeur = (ligne.get(element) or "").strip() or None
    attributs = (ligne.get(f"{element}_ATTRIBUTES") or "").strip()
    parties = attributs.split(",") if attributs else []
    while len(parties) < 3:
        parties.append("")
    return valeur, ",".join(parties[:3])


__all__ = [
    "ACCESS_POINT",
    "DATASET",
    "ELEMENTS_PUBLIES",
    "LICENCE",
    "PRODUCTEUR",
    "REVISION",
    "SOURCE_ID",
    "GhcndDailyAdapter",
    "ligne_brute",
]
