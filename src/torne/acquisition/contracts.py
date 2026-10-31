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
    """Issue d'une acquisition. Vocabulaire fermé.

    Cet axe porte sur **l'acquisition** : la réponse est-elle arrivée, la page
    a-t-elle été conservée ? Il ne dit **rien** de la conformité de la réponse
    à la question posée — celle-ci a son propre axe (`Conformite`), et son
    propre verdict (`VerdictConformite`).

    Une réponse peut avoir été correctement téléchargée et conservée tout en
    étant non conforme à la requête : les deux faits sont vrais, et ils ne se
    confondent pas.
    """

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

    **La non-conformité n'est pas dans ce vocabulaire, et c'est délibéré.** Une
    réponse non conforme est une réponse **acquise** : elle est arrivée, elle
    est conservée, elle est empreinte. Présenter la non-conformité comme un
    échec d'acquisition rendrait la réussite du transport ambiguë. Elle est
    portée par son propre axe : `Conformite` et `VerdictConformite`.
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


class Exhaustiveness(StrEnum):
    """Ce que l'on sait de l'exhaustivité du parcours d'une source.

    Une réponse HTTP réussie ne prouve **pas** que le fournisseur a rendu
    toutes les observations attendues. Trois situations, à ne pas confondre :

    - `DECLARED_EXHAUSTED` — la source **dit** qu'il n'y a plus rien : le lien
      de page suivante a disparu. C'est une déclaration du fournisseur.
    - `TRUNCATED` — le parcours a été arrêté par notre budget de pages. La
      source avait encore à donner.
    - `UNDECLARED` — la source ne le dit pas : elle a renvoyé ce qu'elle avait
      en une réponse, sans déclarer ce qu'elle aurait pu rendre. C'est le cas
      d'une source sans pagination, et c'est le cas le plus fréquent.
    """

    DECLARED_EXHAUSTED = "declared_exhausted"
    TRUNCATED = "truncated"
    UNDECLARED = "undeclared"


class Conformite(StrEnum):
    """Ce que l'on peut dire de la conformité sémantique d'une page.

    Vocabulaire **propre et fermé**, distinct de l'exhaustivité : l'un parle
    de la *complétude* du parcours, l'autre de la *justesse* de la réponse au
    regard de la question posée.

    - `CONFORME` — la page répond bien à la question posée, et cela a été
      **vérifié** sur ce qui a été reçu.
    - `NON_CONFORME` — la page ne répond pas à la question posée. C'est un
      verdict **bloquant** : elle ne produit aucune observation.
    - `NON_APPLICABLE` — la source ne déclare aucun critère sémantique : il
      n'y a rien à vérifier. Ce n'est **pas** une conformité : une absence
      de critère n'est jamais un critère satisfait.
    """

    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"
    NON_APPLICABLE = "non_applicable"


@dataclass(frozen=True, slots=True)
class CritereConformite:
    """Un critère demandé, et ce que la réponse reçue permet d'en dire.

    Trois états distincts, à ne pas confondre :

    - `verifie=True` — la réponse permet de vérifier le critère. `recu` dit
      ce qui a été trouvé, `conforme` dit si cela correspond ;
    - `verifie=False` — la réponse **ne permet pas** de vérifier le critère :
      le champ correspondant est absent. Le critère est alors consigné comme
      non vérifiable : il n'est jamais confondu avec un critère vérifié et
      satisfait ;
    - `conforme=None` — le critère est vérifié et n'a pas été satisfait.
    """

    demande: str
    verifie: bool
    recu: str | None = None
    conforme: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.demande, str) or not self.demande.strip():
            raise ValueError("CritereConformite.demande est obligatoire et non vide")
        if not isinstance(self.verifie, bool):
            raise TypeError("CritereConformite.verifie doit être un booléen")
        if self.conforme is not None and not self.verifie:
            raise ValueError("un critère non vérifiable ne peut pas être déclaré conforme")
        if self.conforme is not None and self.recu is None:
            raise ValueError("un critère vérifié porte ce qui a été reçu")

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable du critère, pour le journal d'acquisition."""
        return {
            "demande": self.demande,
            "verifie": self.verifie,
            "recu": self.recu,
            "conforme": self.conforme,
        }


@dataclass(frozen=True, slots=True)
class VerdictConformite:
    """Le verdict de conformité d'une page, et ce qui l'étaye.

    Il porte le **motif** — en clair, en une phrase — et le détail des
    **critères** : ce qui a été demandé, ce qui a été reçu, ce qui n'a pas pu
    être vérifié. Un verdict sans motif ni critère est un verdict qu'on ne
    peut pas auditer : il n'est pas accepté ici.
    """

    conformite: Conformite
    motif: str | None = None
    criteres: Mapping[str, CritereConformite] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.conformite, Conformite):
            raise TypeError("VerdictConformite.conformite doit être un Conformite")
        object.__setattr__(self, "criteres", MappingProxyType(dict(self.criteres)))
        if self.conformite is Conformite.NON_CONFORME and not self.motif:
            raise ValueError("un verdict non conforme porte son motif")
        for nom, critere in self.criteres.items():
            if not isinstance(critere, CritereConformite):
                raise TypeError(f"le critère « {nom} » n'est pas un CritereConformite")

    @property
    def conforme(self) -> bool:
        """Le verdict est-il favorable ? Un critère non applicable ne l'est pas."""
        return self.conformite is Conformite.CONFORME

    def as_dict(self) -> dict[str, object]:
        """Vue sérialisable du verdict, pour le journal d'acquisition."""
        return {
            "conformite": self.conformite.value,
            "motif": self.motif,
            "criteres": {nom: critere.as_dict() for nom, critere in self.criteres.items()},
        }


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

    **Deux axes, une porte.** L'axe de l'**acquisition** — `status`,
    `succeeded`, `error_kind` — dit si la réponse est arrivée et conservée.
    L'axe de la **conformité** — `conformite`, `verdict_conformite` — dit si
    elle répond à la question posée. Les deux sont vrais indépendamment : une
    réponse peut avoir été correctement téléchargée et conservée tout en
    étant non conforme à la requête.

    Pour savoir si l'on peut **traiter** le contenu, il n'y a qu'une
    question à poser : `exploitable`. C'est la porte.
    """

    request: AcquisitionRequest
    status: AcquisitionStatus
    started_at: datetime
    finished_at: datetime
    attempts: tuple[AcquisitionAttempt, ...] = ()
    evidence: tuple[RawEvidence, ...] = ()
    error_kind: AcquisitionErrorKind | None = None
    error_detail: str | None = None
    exhaustiveness: Exhaustiveness = Exhaustiveness.UNDECLARED
    verdict_conformite: VerdictConformite | None = None
    """Le verdict de conformité de la réponse à la question posée.

    Il est `None` lorsqu'aucun contrôle n'a pu être rendu — une panne de
    transport, par exemple. Il ne l'est jamais pour dire que tout va bien :
    un verdict absent n'est pas un verdict favorable.
    """

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
        if self.verdict_conformite is not None and not isinstance(
            self.verdict_conformite, VerdictConformite
        ):
            raise TypeError("AcquisitionOutcome.verdict_conformite doit être un VerdictConformite")

    @property
    def succeeded(self) -> bool:
        """L'**acquisition** a-t-elle abouti, même partiellement ?

        C'est l'axe de l'acquisition : la réponse est-elle arrivée, la page
        a-t-elle été conservée ? Une acquisition **non conforme a bien
        abouti** — c'est sa *conformité* qui a échoué, pas son transport, et
        les deux faits doivent rester lisibles séparément.

        Cette propriété ne dit **rien** de l'exploitabilité : une acquisition
        non conforme a abouti et n'est pas exploitable. Pour cela, c'est
        `exploitable` qu'il faut regarder — c'est là qu'est la porte.
        """
        return self.status in (AcquisitionStatus.SUCCESS, AcquisitionStatus.PARTIAL)

    @property
    def conformite(self) -> Conformite:
        """Ce que l'on sait de la conformité de la réponse à la question posée.

        `NON_APPLICABLE` quand aucun verdict n'a pu être rendu : une absence
        de contrôle n'est jamais une conformité.
        """
        if self.verdict_conformite is None:
            return Conformite.NON_APPLICABLE
        return self.verdict_conformite.conformite

    @property
    def exploitable(self) -> bool:
        """L'issue peut-elle être transformée en observations ?

        **C'est la porte**, et c'est la seule question à poser avant de
        construire des observations. Elle est fausse dès que la réponse n'est
        pas conforme : une source qui renvoie les lignes d'une autre station
        ne crée aucune observation.

        Elle est fausse **sans rien retirer à la preuve** : la réponse non
        conforme reste reçue, conservée, empreinte et journalisée. Ce qui ne
        se fait pas, c'est l'usage.
        """
        return self.succeeded and self.conformite is not Conformite.NON_CONFORME

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
            "exhaustiveness": self.exhaustiveness.value,
            "conformite": self.conformite.value,
            "motif_conformite": (
                self.verdict_conformite.motif if self.verdict_conformite else None
            ),
            "criteres_conformite": (
                {
                    nom: critere.as_dict()
                    for nom, critere in self.verdict_conformite.criteres.items()
                }
                if self.verdict_conformite
                else {}
            ),
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

    @property
    def declares_exhaustion(self) -> bool:
        """La source **déclare-t-elle** l'épuisement de son parcours ?

        Vrai pour une source paginée dont le lien de page suivante disparaît :
        la source dit alors elle-même « il n'y a plus rien à prendre ». Faux
        pour une source qui renvoie tout d'un coup : alors une réponse
        réussie ne prouve pas que le fournisseur a rendu toutes les
        observations attendues, et l'issue doit le dire.
        """
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

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Le verdict : cette page répond-elle bien à la question posée ?

        C'est le **quatrième contrôle**, et le seul dont le prédicat soit
        propre à la source. Les trois autres sont du ressort du socle
        (transport), de l'adaptateur (structure de la réponse) et du socle
        (exhaustivité). Le socle **orcestre** celui-ci : il appelle le
        prédicat, enregistre le verdict, et bloque quand il est défavorable.

        Le prédicat connaît ce que la source **expose** dans sa réponse, et
        ce que la demande a **demandé** : c'est à lui de confronter les
        deux. Il ne dit pas ce que les données signifient — il dit seulement
        si ce qui est arrivé répond à ce qui a été demandé.

        Trois états sont possibles : `CONFORME`, `NON_CONFORME` (bloquant) et
        `NON_APPLICABLE` (cette source ne déclare aucun critère sémantique).
        Une source qui renvoie les lignes d'une autre station rend un verdict
        `NON_CONFORME`.
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
    "Conformite",
    "CredentialProvider",
    "CritereConformite",
    "Exhaustiveness",
    "HttpResponse",
    "PaginationStrategy",
    "SourceAdapter",
    "VerdictConformite",
]
