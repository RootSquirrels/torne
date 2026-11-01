"""L'adaptateur Météo-France : la voie officielle, derrière un jeton.

L'API publique de Météo-France sert l'observation des stations sur 24 heures
et l'archive climatologique qualifiée. **Les deux exigent un jeton OAuth2** :
sans identifiants, elles répondent `401` et disent pourquoi —

    {"code":"900902","message":"Missing Credentials","description":"Invalid
     Credentials. Make sure your API invocation call has a header:
     'Authorization : Bearer ACCESS_TOKEN' …"}

Ce module ne connaît **jamais** la valeur du jeton. La demande porte une
**référence** — ``meteofrance.oauth2`` — et c'est le socle qui résout le
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

CREDENTIAL_REF = "meteofrance.oauth2"
"""La **référence** du secret. C'est un nom : il est consigné, et il ne vaut
rien pour quiconque ne possède pas le jeton."""

PRODUCTEUR = "Météo-France"
"""Le producteur, tel qu'il se présente."""

DATASET = "API publique Météo-France — observation des stations (24 h)"
"""Le service visé. L'archive climatologique qualifiée relève du même compte,
mais d'un autre hôte."""

BASE_OBSERVATION = "https://public-api.meteofrance.fr/public/DPPaquetObs"
"""La base de l'API d'observation. Elle a changé : la base `DPPaquetV1`
documentée auparavant répond désormais `404` (constaté le 1ᵉʳ novembre 2026)."""

BASE_CLIMATOLOGIE = "https://webservice.meteofrance.com/climatologie"
"""Le webservice climatologique : autre hôte, donc autre origine — et donc
autre référence de secret (INV-42)."""

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
    "LICENCE",
    "PRODUCTEUR",
    "REVISION",
    "SOURCE_ID",
    "MeteoFranceAdapter",
]
