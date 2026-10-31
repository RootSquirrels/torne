"""Contrats du socle transversal d'acquisition.

Ce module fixe **ce qu'est une demande d'acquisition** et **ce qu'est son
issue**. Il ne sait rien.fetch, rien écrire, rien interpréter : il ne fait que
nommer, pour que le socle transversal, les adaptateurs de source et les
couches supérieures parlent la même langue.

Trois règles structurantes :

1. **Le secret ne fait jamais partie de la demande.** `AcquisitionRequest`
   porte une **référence** de identifiant (`credential_ref`), jamais la valeur.
   Ce qui est consigné — journal, manifeste, empreinte — ne peut donc pas
   contenir le secret, par construction et non par prudence du codeur.
2. **Ce qui a été demandé est conservé.** La demande et chaque tentative
   portent l'URL, les paramètres, l'instant et le code retour : une
   acquisition doit être rejouable et auditable, et l'audit commence par la
   question posée.
3. **L'échec est un résultat.** Une acquisition qui rate est **consignée**
   comme telle, avec sa cause (`AcquisitionErrorKind`), jamais avalée ni
   transformée en « rien à signaler » (`docs/CONTRATS_FONDAMENTAUX.md` §2.2,
   INV-03).

Le socle est **transversal** : il ne connaît aucun domaine. Un adaptateur de
source sait poser une question à un fournisseur ; il ne sait ni interpréter la
réponse, ni reconstruire un état physique. C'est la séparation que la
programme impose : « Un connecteur ne doit pas savoir reconstruire un état
hydrologique » (`docs/PROGRAMME.md`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from ..contracts.observation import RawEvidence, Source
from ..contracts.time import to_utc


class AcquisitionStatus(StrEnum):
    """Issue d'une acquisition. Vocabulaire fermé."""

    SUCCESS = "success"
    """Toutes les pages attendues ont été acquises."""

    PARTIAL = "partial"
    """Des pages ont été acquises, et la pagination s'est interrompue avant la
    fin : c'est un résultat partiel, et non un succès."""

    FAILED = "failed"
    """Aucune page n'a pu être acquise."""


class AcquisitionErrorKind(StrEnum):
    """Pourquoi une acquisition a échoué. Vocabulaire fermé.

    `TRANSPORT` est le seul cas où l'on ne sait pas si le fournisseur a reçu
    la demande : la distinction importe, parce qu'une reprise n'a pas le même
    sens sur une erreur de transport que sur un refus explicite.
    """

    TRANSPORT = "transport"
    """Le réseau a échoué : délai dépassé, connexion coupée, résolution DNS."""

    HTTP_STATUS = "http_status"
    """Le fournisseur a répondu par un code d'erreur."""

    AUTHENTICATION = "authentication"
    """Les identifiants sont absents, refusés ou expirés."""

    NOT_FOUND = "not_found"
    """La ressource demandée n'existe pas (404)."""

    TOO_MANY_REQUESTS = "too_many_requests"
    """Le fournisseur a demandé de ralentir (429)."""

    MALFORMED = "malformed"
    """La réponse a été reçue mais n'a pas pu être comprise par l'adaptateur."""

    UNKNOWN = "unknown"
    """Cause non determined. Elle est signalée, jamais masquée."""


class PaginationStrategy(StrEnum):
    """Comment une source se parcourt page après page. Vocabulaire fermé."""

    NONE = "none"
    """Une seule requête : la source renvoie tout en une fois."""

    OFFSET = "offset"
    """Un numéro ou un décalage de page est renvoyé dans la requête."""

    CURSOR = "cursor"
    """La réponse indique le jeton de la page suivante."""

    LINK_HEADER = "link_header"
    """L'en-tête `Link` indique l'URL de la page suivante (RFC 8288)."""


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    """Une demande d'acquisition : à qui, quoi, comment.

    Elle porte **les paramètres de la question**, jamais sa réponse. Le
    `credential_ref` est un nom, pas un secret : c'est ce qui permet de
    consigner la demande sans rien divulguer (INV-03, INV-26).
    """

    source_id: str
    url: str
    method: str = "GET"
    params: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    credential_ref: str | None = None
    pagination: PaginationStrategy = PaginationStrategy.NONE
    max_pages: int = 1
    label: str | None = None
    """Clé stable de la demande dans sa source : elle permet de retrouver la
    même question dans le journal, même si l'URL a changé."""

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("AcquisitionRequest.source_id est obligatoire et non vide")
        if not isinstance(self.url, str) or not self.url.strip():
            raise ValueError("AcquisitionRequest.url est obligatoire et non vide")
        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("AcquisitionRequest.method est obligatoire et non vide")
        if self.max_pages < 1:
            raise ValueError("AcquisitionRequest.max_pages doit valoir au moins 1")
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @property
    def effective_url(self) -> str:
        """URL avec les paramètres encodés, telle qu'elle sera demandée."""
        if not self.params:
            return self.url
        from urllib.parse import quote, urlencode

        query = urlencode(
            [(cle, str(valeur)) for cle, valeur in sorted(self.params.items())],
            quote_via=quote,
        )
        separateur = "&" if "?" in self.url else "?"
        return f"{self.url}{separateur}{query}"


@dataclass(frozen=True, slots=True)
class AcquisitionAttempt:
    """Une tentative : ce qui a été demandé, ce qui a été reçu, ce qui a échoué.

    Une tentative est conservée même quand elle échoue : c'est l'audit du
    dialogue avec la source, et il est sans valeur sans les échecs.
    """

    page_index: int
    requested_at: datetime
    url: str
    status_code: int | None = None
    media_type: str | None = None
    content_length: int | None = None
    elapsed_ms: int = 0
    error_kind: AcquisitionErrorKind | None = None
    error_detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requested_at",
            to_utc(self.requested_at, name="AcquisitionAttempt.requested_at"),
        )

    @property
    def succeeded(self) -> bool:
        """La tentative a-t-elle produit une réponse exploitable ?"""
        return self.error_kind is None and self.status_code is not None


@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    """Le résultat d'une acquisition : ce qui a été acquis, et comment.

    Il porte **les pages acquises** (chacune une preuve brute identifiable),
    **les tentatives** (y compris celles qui ont échoué), et **la demande**
    qui a produit le tout.
    """

    request: AcquisitionRequest
    status: AcquisitionStatus
    started_at: datetime
    finished_at: datetime
    attempts: tuple[AcquisitionAttempt, ...] = ()
    evidence: tuple[RawEvidence, ...] = ()
    error_kind: AcquisitionErrorKind | None = None
    error_detail: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AcquisitionStatus):
            raise TypeError("AcquisitionOutcome.status doit être un AcquisitionStatus")
        object.__setattr__(
            self,
            "started_at",
            to_utc(self.started_at, name="AcquisitionOutcome.started_at"),
        )
        object.__setattr__(
            self,
            "finished_at",
            to_utc(self.finished_at, name="AcquisitionOutcome.finished_at"),
        )
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(self, "evidence", tuple(self.evidence))

    @property
    def succeeded(self) -> bool:
        """L'acquisition a-t-elle abouti, même partiellement ?"""
        return self.status in (AcquisitionStatus.SUCCESS, AcquisitionStatus.PARTIAL)

    @property
    def page_count(self) -> int:
        """Nombre de pages effectivement acquises."""
        return len(self.evidence)

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable : elle ne contient aucun secret.

        La demande est reprise telle quelle, avec sa `credential_ref` — un
        nom, pas une valeur. C'est la garantie que le journal d'acquisition
        peut être publié sans l'exposer.
        """
        return {
            "source_id": self.request.source_id,
            "label": self.request.label,
            "url": self.request.url,
            "method": self.request.method,
            "params": dict(sorted(self.request.params.items())),
            "credential_ref": self.request.credential_ref,
            "pagination": self.request.pagination.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "error_kind": self.error_kind.value if self.error_kind else None,
            "error_detail": self.error_detail,
            "attempts": [
                {
                    "page_index": tentative.page_index,
                    "requested_at": tentative.requested_at.isoformat(),
                    "url": tentative.url,
                    "status_code": tentative.status_code,
                    "media_type": tentative.media_type,
                    "content_length": tentative.content_length,
                    "elapsed_ms": tentative.elapsed_ms,
                    "error_kind": (tentative.error_kind.value if tentative.error_kind else None),
                    "error_detail": tentative.error_detail,
                }
                for tentative in self.attempts
            ],
            "evidence": [
                {
                    "evidence_id": piece.evidence_id,
                    "source_id": piece.source_id,
                    "acquired_at": piece.acquired_at.isoformat(),
                    "media_type": piece.media_type,
                    "content_sha256": piece.content_sha256,
                    "key": piece.key,
                }
                for piece in self.evidence
            ],
        }


class CredentialProvider(Protocol):
    """Fournisseur d'identifiants, résolus **au moment de l'appel**.

    Le contrat ne dit pas comment le secret est stocké : il dit seulement
    qu'il sort d'ici, au dernier moment, et qu'il ne doit jamais revenir dans
    un objet consigné.
    """

    def credentials_for(self, credential_ref: str) -> Mapping[str, str]:
        """En-têtes (et paramètres) d'authentification pour cette référence."""
        ...


class SourceAdapter(Protocol):
    """Ce qu'un adaptateur de source sait faire : poser des questions.

    Il ne sait **rien interpréter**. Il ne connaît ni hydrologie, ni énergie,
    ni logistique : il sait construire une URL, dire comment la source se
    parcourt, et reconnaître ses formats. La compréhension d'un relevé est
    l'affaire de la couche sémantique, pas de l'adaptateur.
    """

    @property
    def source(self) -> Source:
        """La source à laquelle cet adaptateur s'adresse."""
        ...

    def initial_request(self) -> AcquisitionRequest:
        """La première question à poser."""
        ...

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """La question suivante, ou `None` si la pagination est épuisée.

        `response` est la réponse **brute** de la page précédente : l'adaptateur
        s'en sert pour lire un jeton ou un lien, pas pour en tirer du sens.
        """
        ...


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Une réponse HTTP brute : statut, en-têtes, corps.

    Elle ne porte **aucune interprétation** : c'est un transport, pas un
    modèle. Le `content_type` est l'en-tête déclaré par le fournisseur, pas
    un type deviné.
    """

    status_code: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""
    url: str = ""
    elapsed_ms: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @property
    def content_type(self) -> str | None:
        """Le type de contenu déclaré, sans son paramètre de charset."""
        brut = self.headers.get("content-type") or self.headers.get("Content-Type")
        if not brut:
            return None
        return brut.split(";", 1)[0].strip().lower()

    def header(self, name: str) -> str | None:
        """Un en-tête, sought sans se soucier de sa casse."""
        cible = name.lower()
        for cle, valeur in self.headers.items():
            if cle.lower() == cible:
                return valeur
        return None

    def text(self, encoding: str | None = None) -> str:
        """Le corps décodé en texte. `encoding` par défaut : UTF-8."""
        if not self.body:
            return ""
        return self.body.decode(encoding or "utf-8", errors="replace")


__all__ = [
    "AcquisitionAttempt",
    "AcquisitionErrorKind",
    "AcquisitionOutcome",
    "AcquisitionRequest",
    "AcquisitionStatus",
    "CredentialProvider",
    "HttpResponse",
    "PaginationStrategy",
    "SourceAdapter",
]
