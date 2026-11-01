"""L'adaptateur Météo-France : la voie officielle, derrière un jeton.

L'API publique de Météo-France sert l'observation des stations sur 24 heures
et l'archive climatologique qualifiée. **Les deux exigent une clé d'API**
(en-tête ``apikey``) : sans identifiants, elles répondent `401` et disent
pourquoi —

    {"code":"900902","message":"Missing Credentials","description":"Invalid
     Credentials. Make sure your API invocation call has a header:
     'Authorization : Bearer ACCESS_TOKEN' …"}

Ce module ne connaît **jamais** la valeur du jeton. La demande porte une
**référence** — ``meteofrance.apikey`` — et c'est le socle qui résout le
secret au dernier moment, à partir de l'environnement ou d'un fichier local
ignoré (INV-41). Ce qui est consigné — journal, manifeste, empreinte — porte
le nom de la référence, jamais le jeton.

**Ce que l'adaptateur vérifie, et ce qu'il ne peut pas encore vérifier.**

Deux critères sont vérifiables sans avoir jamais vu une réponse authentifiée,
et ils sont donc posés d'emblée :

- `authentification` — le corps ne doit pas être l'enveloppe « Missing
  Credentials ». Si elle l'est, le critère est **violé** : la source a dit
  qu'elle n'avait pas reconnu la demande, et c'est un constat, pas une
  abstention.
- `json` — le corps doit être du JSON. Un service qui rend une page d'erreur
  HTML avec un code 200 ne rend aucun critère vérifiable, et le verdict est
  alors l'abstention.

Un troisième critère, `contenu`, porte la **forme attendue de la réponse** :
il n'est posé que si l'appelant en déclare une. Tant que la forme exacte
d'une réponse authentifiée n'a pas été observée, ce critère est **absent** —
on ne devine pas la grammaire d'un fournisseur, et le socle ne rend pas
favorable un verdict qui repose sur une invention.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
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

SOURCE_ID = "meteofrance.observation"
"""Identifiant de la source, tel qu'il est consigné dans le journal."""

CREDENTIAL_REF = "meteofrance.apikey"
"""The **reference** of the secret. It is a name: it is logged, and it is worth
nothing to anyone who does not hold the key. The Météo-France portal issues an
**API key** (``apikey`` header), not an OAuth2 token."""

KEY_HEADER = "apikey"
"""The header in which the portal expects the key, with no scheme (no ``Bearer``)."""

PRODUCTEUR = "Météo-France"
"""Le producteur, tel qu'il se présente."""

DATASET = "API publique Météo-France — observation des stations (24 h)"
"""Le service visé. L'archive climatologique qualifiée relève du même compte,
mais d'un autre hôte."""

BASE_OBSERVATION = "https://public-api.meteofrance.fr/public/DPPaquetObs"
"""La base de l'API d'observation. Elle a changé : la base `DPPaquetV1`
documentée auparavant répond désormais `404` (constaté le 1ᵉʳ novembre 2026)."""

BASE_CLIMATOLOGIE = "https://public-api.meteofrance.fr/public/DPClim/v1"
"""The climatological data API (DPClim), same host as the observation API.
Observed on 2026-11-01: the API key opens the station list (200) and the data
order (202), then the CSV file (201)."""

DAILY_ORDER_PATH = "/commande-station/quotidienne"
"""Order of a daily series for one station and one period."""

ORDER_FILE_PATH = "/commande/fichier"
"""The file of an order, by its identifier."""

LICENCE = "conditions d'utilisation Météo-France (compte personnel)"
"""L'accès est conditionné à un compte ; l'usage est encadré par les CGU du
producteur."""

REVISION = (
    "Les valeurs d'observation portent l'instant de leur publication ; "
    "l'archive climatologique qualifiée expose ses propres métadonnées de "
    "révision. La date de publication est donc **établie** pour l'observation, "
    "et c'est ce qui rend cette source admissible en reconstitution "
    "point-in-time — là où GHCN-Daily ne l'est pas."
)

CHEMIN_STATIONS = "/liste-stations"
"""Le référentiel des stations de l'API d'observation."""

CHEMIN_PAQUET_6M = "/paquet/stations/infrahoraire-6m"
"""Le paquet infra-horaire 6 minutes, toutes stations, pour une date."""

CHEMIN_PAQUET_HORAIRE = "/paquet/stations/horaire"
"""Le paquet horaire, toutes stations, pour une date."""


class MeteoFranceAdapter:
    """L'API d'observation Météo-France, pour une route et une date.

    `forme_attendue` est la **clé de premier niveau** que la réponse doit
    porter pour être jugée conforme (par exemple ``"features"`` pour du
    GeoJSON, ``"stations"`` pour un référentiel). Elle est un **argument** :
    tant qu'elle n'a pas été observée sur une réponse authentifiée, on ne la
    suppose pas.
    """

    def __init__(
        self,
        *,
        chemin: str = CHEMIN_STATIONS,
        params: Mapping[str, str] | None = None,
        forme_attendue: str | None = None,
        credential_ref: str = CREDENTIAL_REF,
        label: str | None = None,
    ) -> None:
        if not chemin.startswith("/"):
            raise ValueError("le chemin commence par « / »")
        self.chemin = chemin
        self.params = dict(params or {})
        self.forme_attendue = forme_attendue
        self.credential_ref = credential_ref
        self._label = label

    @property
    def source(self) -> Source:
        """La source, telle que le socle la consigne."""
        return Source(
            source_id=SOURCE_ID,
            producer=PRODUCTEUR,
            dataset=DATASET,
            access_point=BASE_OBSERVATION,
            license=LICENCE,
            revision_policy=REVISION,
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """La source ne déclare pas l'épuisement de son parcours."""
        return False

    def initial_request(self) -> AcquisitionRequest:
        """La question — avec une **référence** de secret, jamais le secret."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=f"{BASE_OBSERVATION}{self.chemin}",
            method="GET",
            params=self.params,
            credential_ref=self.credential_ref,
            pagination=PaginationStrategy.NONE,
            max_pages=1,
            label=self._label or f"meteofrance:{self.chemin.strip('/')}",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """Il n'y a pas de page suivante : ces routes rendent tout d'un coup."""
        return None

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """La réponse répond-elle à la question posée ?

        Trois critères, dont deux toujours vérifiables :

        - `authentification` — la source ne doit pas avoir dit « Missing
          Credentials » ;
        - `json` — le corps doit se lire comme du JSON ;
        - `contenu` — la clé attendue doit être présente, **si l'appelant en a
          déclaré une**.
        """
        criteres: dict[str, CritereConformite] = {}

        try:
            charge = json.loads(response.text())
        except json.JSONDecodeError:
            criteres["json"] = CritereConformite(
                demande="a body that reads as JSON",
                verifie=True,
                recu=f"the body is not JSON ({response.content_type or 'unknown type'})",
                conforme=False,
            )
            return verdict_from_criteria(criteres)

        criteres["json"] = CritereConformite(
            demande="a body that reads as JSON",
            verifie=True,
            recu="the body reads as JSON",
            conforme=True,
        )

        raison = _raison_refus(charge)
        criteres["authentification"] = CritereConformite(
            demande="a body that is not a refusal for missing credentials",
            verifie=True,
            recu=raison or "no refusal envelope",
            conforme=raison is None,
        )

        if self.forme_attendue is not None:
            present = isinstance(charge, Mapping) and self.forme_attendue in charge
            criteres["contenu"] = CritereConformite(
                demande=f"a body carrying the key « {self.forme_attendue} »",
                verifie=True,
                recu=(
                    f"the body carries « {self.forme_attendue} »"
                    if present
                    else f"the body carries no « {self.forme_attendue} »"
                ),
                conforme=present,
            )

        return verdict_from_criteria(criteres)


class DailyClimatologyAdapter:
    """The daily series of one station, from the climatological API (DPClim).

    The API works in **two steps**: an order (JSON reply carrying an
    identifier), then the file of that order (CSV, ``;`` separator). The
    adapter chains the two as two pages, and each page has its own verdict.

    The conformity of the second page is checked **on the content**: the
    header must carry ``POSTE`` and ``DATE``, and every row must belong to the
    requested station. An empty file (order not ready) is a violation, not an
    abstention: the source delivered nothing.
    """

    def __init__(
        self,
        *,
        station: str,
        start: str,
        end: str,
        credential_ref: str = CREDENTIAL_REF,
    ) -> None:
        if not station.strip():
            raise ValueError("station is required and must not be empty")
        self.station = station.strip()
        self.start = start
        self.end = end
        self.credential_ref = credential_ref

    @property
    def source(self) -> Source:
        """The source, as the foundation records it."""
        return Source(
            source_id="meteofrance.climatology",
            producer=PRODUCTEUR,
            dataset="Météo-France public API - climatological data (DPClim)",
            access_point=BASE_CLIMATOLOGIE,
            license=LICENCE,
            revision_policy=(
                "The file carries one quality indicator per measure (Q* columns). "
                "No per-value publication date was observed: publication is "
                "UNKNOWN until it is established."
            ),
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """The source does not declare the exhaustion of its traversal."""
        return False

    def initial_request(self) -> AcquisitionRequest:
        """The order, carrying a key **reference**, never the key."""
        return AcquisitionRequest(
            source_id="meteofrance.climatology",
            url=f"{BASE_CLIMATOLOGIE}{DAILY_ORDER_PATH}",
            method="GET",
            params={
                "id-station": self.station,
                "date-deb-periode": self.start,
                "date-fin-periode": self.end,
            },
            credential_ref=self.credential_ref,
            pagination=PaginationStrategy.NONE,
            max_pages=2,
            label=f"meteofrance:climatology:{self.station}:order",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """After the order comes the file; after the file, nothing."""
        order_id = _order_id(response)
        if order_id is None:
            return None
        return AcquisitionRequest(
            source_id=request.source_id,
            url=f"{BASE_CLIMATOLOGIE}{ORDER_FILE_PATH}",
            method="GET",
            params={"id-cmde": order_id},
            credential_ref=self.credential_ref,
            pagination=PaginationStrategy.NONE,
            max_pages=2,
            label=f"meteofrance:climatology:{self.station}:file",
        )

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Is the page the expected order acknowledgement, or the right station's file?"""
        if _order_id(response) is not None:
            return verdict_from_criteria(
                {
                    "order": CritereConformite(
                        demande="an order acknowledgement carrying an identifier",
                        verifie=True,
                        recu="the order identifier is present",
                        conforme=True,
                    )
                }
            )
        return verdict_from_criteria(self._file_criteria(response))

    def _file_criteria(self, response: HttpResponse) -> dict[str, CritereConformite]:
        lines = [line for line in response.text().splitlines() if line.strip()]
        if not lines:
            return {
                "file": CritereConformite(
                    demande="a CSV file with a header and rows",
                    verifie=True,
                    recu="the body is empty (order not ready, or no data)",
                    conforme=False,
                )
            }
        header = lines[0].split(";")
        if "POSTE" not in header or "DATE" not in header:
            return {
                "file": CritereConformite(
                    demande="a CSV header carrying POSTE and DATE",
                    verifie=True,
                    recu=f"the first line is not a climatology header ({lines[0][:60]!r})",
                    conforme=False,
                )
            }
        column = header.index("POSTE")
        others = {
            cells[column]
            for cells in (line.split(";") for line in lines[1:])
            if len(cells) > column and cells[column].strip() != self.station
        }
        return {
            "file": CritereConformite(
                demande="a CSV header carrying POSTE and DATE",
                verifie=True,
                recu="the header carries POSTE and DATE",
                conforme=True,
            ),
            "station": CritereConformite(
                demande=f"only rows of station {self.station}",
                verifie=True,
                recu=(
                    f"every row is station {self.station}"
                    if not others
                    else f"rows of other stations: {', '.join(sorted(others))}"
                ),
                conforme=not others,
            ),
        }


def _order_id(response: HttpResponse) -> str | None:
    """The identifier of an accepted order, if the reply is an acknowledgement."""
    try:
        payload = json.loads(response.text())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    ack = payload.get("elaboreProduitAvecDemandeResponse")
    if isinstance(ack, Mapping) and ack.get("return"):
        return str(ack["return"])
    return None


def _raison_refus(charge: Any) -> str | None:
    """Le motif du refus de la source, si elle en a formulé un.

    Météo-France répond `401` avec un code interne (``900902``) et un message
    (« Missing Credentials »). C'est la source qui parle, et c'est sa parole
    qui fait le constat.
    """
    if not isinstance(charge, Mapping):
        return None
    for champ in ("message", "description"):
        valeur = charge.get(champ)
        if isinstance(valeur, str) and "credential" in valeur.lower():
            code = charge.get("code")
            prefixe = f"[{code}] " if code else ""
            return f"{prefixe}{valeur.strip()}"
    return None


__all__ = [
    "BASE_CLIMATOLOGIE",
    "BASE_OBSERVATION",
    "CREDENTIAL_REF",
    "DATASET",
    "KEY_HEADER",
    "LICENCE",
    "PRODUCTEUR",
    "REVISION",
    "SOURCE_ID",
    "DailyClimatologyAdapter",
    "MeteoFranceAdapter",
]
