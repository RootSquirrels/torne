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
   transformée en « rien à signaler » (`docs/CORE_CONTRACTS.md` §2.2,
   INV-03).

Le socle est **transversal** : il ne connaît aucun domaine. Un adaptateur de
source sait poser une question à un fournisseur ; il ne sait ni interpréter la
réponse, ni reconstruire un état physique. C'est la séparation que la
programme impose : « Un connecteur ne doit pas savoir reconstruire un état
hydrologique » (`docs/PROGRAMME.md`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
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

    La table de vérité est celle de l'axe d'applicabilité des produits de
    connaissance (`docs/RESEARCH_AND_VALIDATION.md` §12.1) : **la même règle,
    au même mot, à deux étages.**

    | Ce que porte le verdict | Verdict |
    |---|---|
    | tous les critères vérifiés et satisfaits | `CONFORME` |
    | au moins un critère vérifié et violé | `NON_CONFORME` |
    | aucun critère violé, au moins un demandé mais non vérifiable | `INDETERMINATE` |
    | la source ne fournit aucun prédicat | `NON_APPLICABLE` |

    - `CONFORME` — la page répond bien à la question posée, et cela a été
      **vérifié** sur ce qui a été reçu.
    - `NON_CONFORME` — au moins un critère demandé a été **violé**. C'est un
      constat : la réponse ne répond pas à la question posée.
    - `INDETERMINATE` — aucun critère n'a été violé, mais au moins un critère
      **demandé n'a pas pu être vérifié**. C'est une **abstention** : la
      conformité n'est établie ni dans un sens ni dans l'autre. Elle n'est pas
      exploitable, et elle n'est pas non plus un constat.
    - `NON_APPLICABLE` — la source ne fournit **aucun prédicat** : il n'y a
      rien à vérifier, et donc aucune contrainte à enfreindre.

    > **Non-contamination : un critère n'est jamais « violé » par la seule
    > absence de vérification.** Un prédicat non applicable ne fait pas un
    > constat d'inapplicabilité ; il fait une abstention.

    **The gate.** Only one of these four verdicts authorises use: `CONFORME`.
    The three others are an abstention (`INDETERMINATE`, `NON_APPLICABLE`) or
    a finding of non-conformity (`NON_CONFORME`), and observations are never
    built on an abstention. That is the rule carried by
    `AcquisitionOutcome.exploitable`, and it holds for every verdict,
    whichever adapter produced it.
    """

    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"
    INDETERMINATE = "indeterminate"
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
        if self.conformite is Conformite.INDETERMINATE and not self.motif:
            raise ValueError(
                "an abstention carries its motif: it must say what could not be verified"
            )
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


def verdict_from_criteria(criteria: Mapping[str, CritereConformite]) -> VerdictConformite:
    """Applies the truth table to the criteria collected by an adapter.

    The **socle** decides, not each adapter: the rule is the same everywhere
    and it is written exactly once. An adapter **collects** criteria — what
    the request asked for, what the response allowed to be verified — it does
    not decide the verdict. That is what prevents an adapter from forgetting
    a case and opening the gate on a conformity that was never established.

    | Collected criteria | Verdict |
    |---|---|
    | none | `NON_APPLICABLE` — the source declares no predicate |
    | at least one violated | `NON_CONFORME` — a criterion was explicitly violated |
    | none violated, at least one not verifiable | `INDETERMINATE` — conformity is not established |
    | all verified and satisfied | `CONFORME` |

    The order of the branches is not arbitrary: **a finding always beats an
    abstention**. When one criterion is violated *and* another remains
    unknown, the verdict is `NON_CONFORME`: that is an established fact,
    where the other is merely silence.

    The motif always states **what was asked, what was received, and what
    could not be verified**: a verdict without a motif is not auditable.
    """
    if not criteria:
        return VerdictConformite(
            conformite=Conformite.NON_APPLICABLE,
            motif="the source declares no semantic criterion: there is nothing to verify",
        )

    violations = [name for name, criterion in criteria.items() if criterion.conforme is False]
    unverifiable = [name for name, criterion in criteria.items() if not criterion.verifie]

    if violations:
        details = " ; ".join(
            f"{name} requested « {criteria[name].demande} », received « {criteria[name].recu} »"
            for name in violations
        )
        return VerdictConformite(
            conformite=Conformite.NON_CONFORME,
            motif=(f"the source returned records that are not the ones requested: {details}"),
            criteres=criteria,
        )

    if unverifiable:
        details = " ; ".join(
            f"{name} requested « {criteria[name].demande} », not verifiable ({criteria[name].recu})"
            for name in unverifiable
        )
        return VerdictConformite(
            conformite=Conformite.INDETERMINATE,
            motif=f"conformity cannot be established: {details}",
            criteres=criteria,
        )

    return VerdictConformite(conformite=Conformite.CONFORME, criteres=criteria)


_SEVERITE_CONFORMITE = {
    Conformite.CONFORME: 0,
    Conformite.NON_APPLICABLE: 1,
    Conformite.INDETERMINATE: 2,
    Conformite.NON_CONFORME: 3,
}
"""Severity order of the verdicts, from least to most severe.

A more severe verdict **overwrites** a less severe one: a single page whose
conformity is not established is enough to prevent the whole acquisition from
being exploited. That is the "worst wins" rule, and it holds page by page as
well as for the issue as a whole.
"""


def worst_verdict(
    verdicts: Iterable[VerdictConformite],
) -> VerdictConformite | None:
    """The most severe of the verdicts rendered, or `None` if there is none.

    A traversal spans several pages, and each of them is checked. The issue
    carries the **most unfavourable** verdict: an acquisition cannot be
    declared conformant on the strength of its last page alone, if a page in
    the middle failed to be certified.

    This is the counterpart, on the conformity axis, of the raw-evidence
    rule: **what is acquired is kept**, even when what is acquired cannot be
    used.
    """
    worst: VerdictConformite | None = None
    for verdict in verdicts:
        if worst is None:
            worst = verdict
            continue
        if _SEVERITE_CONFORMITE[verdict.conformite] > _SEVERITE_CONFORMITE[worst.conformite]:
            worst = verdict
    return worst


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
        """What is known about the conformity of the response to the question asked.

        `INDETERMINATE` when no verdict could be rendered — a transport
        failure, for instance. The absence of a check is never a conformity;
        it is not an inapplicability either: it is an **abstention**, and
        that is the only exact word for it.
        """
        if self.verdict_conformite is None:
            return Conformite.INDETERMINATE
        return self.verdict_conformite.conformite

    @property
    def exploitable(self) -> bool:
        """Can the outcome be turned into observations?

        **This is the gate**, and it is the only question to ask before
        building observations.

        It opens on an **established** verdict only: `CONFORME`, and nothing
        else. It stays shut on `NON_CONFORME` (a criterion was violated), on
        `INDETERMINATE` (nothing violated, but at least one criterion could
        not be verified) and on `NON_APPLICABLE` (the source declares no
        predicate): an abstention is not a certification, and observations
        are never built on an abstention. A source whose conformity has not
        been **established** is not a conformant source.

        It is false **without taking anything away from the evidence**: the
        non-conformant response is still received, kept, hashed and
        journalled. What does not happen is the use.
        """
        return self.conformite is Conformite.CONFORME

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

        The predicate knows what the source **exposes** in its response, and
        what the request **asked for**: it is up to it to confront the two. It
        does not say what the data mean — it only says whether what arrived
        answers what was asked.

        The predicate **collects** criteria and renders a verdict. So that the
        truth table stays the same everywhere, it builds its verdict with
        `verdict_from_criteria`: the socle decides, and the adapter only says
        what it asked for and what it received.

        Four verdicts are possible: `CONFORME` (the only one that opens the
        gate), `NON_CONFORME` (blocking), `INDETERMINATE` (conformity could
        not be established) and `NON_APPLICABLE` (this source declares no
        semantic criterion). A source that returns the records of another
        station renders a `NON_CONFORME` verdict.
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
    "verdict_from_criteria",
    "worst_verdict",
]
