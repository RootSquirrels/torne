"""Ladaptateur du suivi quotidien du systeme gaziste (Enagas).

Le *Seguimiento Diario del Sistema* est le rapport **quotidien** de l'exploitant :
pour un jour de gaz, il donne par terminal les volumes decharges, regasifies,
charges sur citernes, les existances en cuves et le taux de remplissage.

Comme tout adaptateur du depot, celui-ci **pose une question** et
**verifie la forme de ce qu'il a recu** ; il n'interprete rien. La lecture
des grandeurs physiques est le fait du decodeur (`torne.supply.enagas`),
qui fait partie du domaine.

Le point d'acces
-----------------

Le site sert le rapport en **JSON** : `dailysystemtrackingdto.json?date=…`.
C'est le point d'acces que la page elle-meme utilise, et il a un avantage
decisif sur la version tableur : il est **indexe par nom de terminal**. Sur
le tableur, les valeurs sont en colonnes, et il faut retrouver a quel
terminal elles appartiennent ; sur le JSON, la question ne se pose pas.

Le chemin a change : l'URL est desormais sous `/content/enagas/es/…` et
non plus sous `/content/dam/enagas/es/…`. C'est un **changement de source**,
observe par execution le 1er novembre 2026, et il a rendu l'ancienne URL
invalide en quelques heures.
"""

from __future__ import annotations

from datetime import date

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    VerdictConformite,
    verdict_from_criteria,
)

SOURCE_ID = "enagas.seguimiento_diario"
"""Identifiant de la source, tel qu'il est consigne dans le journal."""

PRODUCTEUR = "Enagas"
"""Le producteur du rapport, tel qu'il le declare."""

DATASET = "Seguimiento Diario del Sistema"
"""Le jeu de donnees, tel que l'exploitant le nomme."""

ACCESS_POINT = (
    "https://www.enagas.es/content/enagas/es/gestion-tecnica-sistema/energy-data"
    "/parametros-fisicos/capacidades-tecnicas-flujos-fisicos/seguimiento-diario-sistema"
    "/jcr:content/responsiveGrid/dailysystemtracking.dailysystemtrackingdto.json"
)
"""Le point d'acces public, sans authentification."""

GRANDEURS_ATTENDUES = (
    "tankInitialStocksGWh",
    "tankInitialStocksM3",
    "downloadsGNL",
    "loadsGNL",
    "regasificationGWh",
    "regasificationM3",
    "cisternLoad",
    "tankFinalStocksGwh",
    "tankFinalStocksM3",
    "tankFinalStocksFilling",
)
"""Les grandeurs que le rapport doit porter, sans quoi il ne dit rien."""


class EnagasDailyAdapter:
    """Le rapport quotidien d'**un** jour de gaz.

    La source ne se parcourt pas : elle rend, pour la date demandee, l'etat
    du systeme gaziste. Un rapport par jour, sans pagination.
    """

    def __init__(self, jour_gaz: date, *, source_id: str = SOURCE_ID) -> None:
        self.jour_gaz = jour_gaz
        self._source_id = source_id

    @property
    def source(self) -> Source:
        """La source, telle que le socle la consigne."""
        return Source(
            source_id=self._source_id,
            producer=PRODUCTEUR,
            dataset=DATASET,
            access_point=ACCESS_POINT,
            license="usage interne a verifier",
            revision_policy="quotidien ; le rapport remplace le rapport du meme jour",
            unit="m3 GNL liquide, GWh, pourcentage de remplissage",
            timezone="Europe/Madrid",
            publication_class="operational",
        )

    @property
    def declares_exhaustion(self) -> bool:
        """La source ne declare rien : elle rend un rapport par jour."""
        return False

    def initial_request(self) -> AcquisitionRequest:
        """La question : le rapport du jour de gaz demande.

        Le jour ne va que dans les parametres : le socle les encode, et
        les mettre aussi dans l'URL produirait un parametre en double.
        """
        etiquette = self.jour_gaz.strftime("%d/%m/%Y")
        return AcquisitionRequest(
            source_id=self._source_id,
            url=ACCESS_POINT,
            method="GET",
            params={"date": etiquette},
            label=f"enagas:quotidien:{etiquette}",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """Un rapport par jour : il n'y a pas de suite."""
        del request, response
        return None

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Ce que le rapport contient-il reellement ?

        Trois criteres, tous verifies sur le **corps recu** :

        - le corps est bien du JSON ;
        - il porte l'instant de publication du rapport ;
        - il porte les grandeurs physiques attendues, par terminal.
        """
        del request
        charge = _charge(response.body)
        if charge is None:
            return verdict_from_criteria(
                {
                    "corps": CritereConformite(
                        demande="un corps JSON",
                        verifie=False,
                        recu="corps illisible ou erreur de la source",
                    )
                }
            )
        return verdict_from_criteria(
            {
                "rapport": self._criterion_json(charge),
                "publication": self._criterion_publication(charge),
                "grandeurs": self._criterion_grandeurs(charge),
            }
        )

    # -- les criteres ---------------------------------------------------
    def _criterion_json(self, charge: dict) -> CritereConformite:
        """Le corps est-il bien le rapport attendu ?"""
        demande = "un rapport JSON du suivi quotidien"
        if "gasSystemPPDDataReportPojo" not in charge:
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu="rapport absent",
                conforme=False,
            )
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu="rapport JSON du suivi quotidien",
            conforme=True,
        )

    def _criterion_publication(self, charge: dict) -> CritereConformite:
        """Le rapport porte-t-il son instant de publication ?"""
        demande = "l'instant de publication (lastDate)"
        if not charge.get("lastDate"):
            return CritereConformite(
                demande=demande,
                verifie=False,
                recu="instant de publication absent",
                conforme=None,
            )
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu=str(charge.get("lastDate")),
            conforme=True,
        )

    def _criterion_grandeurs(self, charge: dict) -> CritereConformite:
        """Les grandeurs attendues sont-elles presentes ?"""
        demande = f"les grandeurs {', '.join(GRANDEURS_ATTENDUES)}"
        rapport = charge.get("gasSystemPPDDataReportPojo") or {}
        absentes = [nom for nom in GRANDEURS_ATTENDUES if nom not in rapport]
        if absentes:
            return CritereConformite(
                demande=demande,
                verifie=True,
                recu=f"absentes : {', '.join(absentes)}",
                conforme=False,
            )
        return CritereConformite(
            demande=demande,
            verifie=True,
            recu="toutes les grandeurs attendues",
            conforme=True,
        )


def _charge(corps: bytes) -> dict | None:
    """Le corps, lu comme du JSON — ou rien du tout."""
    import json

    try:
        charge = json.loads(corps.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return charge if isinstance(charge, dict) else None


__all__ = [
    "ACCESS_POINT",
    "DATASET",
    "GRANDEURS_ATTENDUES",
    "PRODUCTEUR",
    "SOURCE_ID",
    "EnagasDailyAdapter",
]
