"""Le fetcher : c'est lui qui transforme une question en preuves conservées.

C'est le cœur du socle transversal. Il ne connaît aucun fournisseur et aucun
domaine : il prend un adaptateur, lui demande la première question, suit la
pagination, conserve chaque page acquise comme **preuve brute**, et rend une
`AcquisitionOutcome` qui dit exactement ce qui a été demandé, ce qui a été
reçu, et ce qui a échoué.

Quatre règles :

1. **Une page acquise est conservée, même si la suivante échoue.** Ce qui a
   été obtenu ne se perd pas : l'issue est alors `PARTIAL`, qui est un
   résultat, pas un échec.
2. **L'échec est consigné.** Une tentative qui rate reste dans le journal,
   avec sa cause (`docs/CONTRATS_FONDAMENTAUX.md` §2.2, INV-03).
3. **Le secret ne passe pas par la demande.** Les identifiants sont résolus
   au dernier moment et appliqués par le transport ; la demande consignée n'en
   garde que la **référence**.
4. **Rien n'est réécrit.** Le magasin brut est adressé par le contenu : deux
   acquisitions du même contenu partagent la même preuve (INV-01, INV-05).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from ..contracts.observation import RawEvidence
from .contracts import (
    AcquisitionAttempt,
    AcquisitionErrorKind,
    AcquisitionOutcome,
    AcquisitionRequest,
    AcquisitionStatus,
    CredentialProvider,
    Exhaustiveness,
    HttpResponse,
    SourceAdapter,
)
from .store import RawStore
from .transport import Transport, TransportError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Quand, et combien de fois, on retente une acquisition.

    Une reprise n'a pas le même sens sur tous les échecs : une coupure
    réseau ou une saturation se retentent, un 404 ne se retente jamais. La
    règle est donc explicite, et non déduite du code de retour.
    """

    max_attempts: int = 3
    initial_delay: float = 0.5
    multiplier: float = 2.0
    max_delay: float = 30.0
    retry_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )
    retry_on_transport_error: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("RetryPolicy.max_attempts doit valoir au moins 1")
        if self.initial_delay < 0:
            raise ValueError("RetryPolicy.initial_delay ne peut pas être négatif")
        if self.multiplier < 1:
            raise ValueError("RetryPolicy.multiplier doit valoir au moins 1")


def classer_statut(status_code: int | None) -> AcquisitionErrorKind | None:
    """La cause d'un échec, déduite du code de retour.

    `None` signifie que la réponse est exploitable. Les codes sont distingués
    parce que leur sens diffère : une authentification refusée ne se reprend
    pas, une saturation si, une absence ne se rattrape pas.
    """
    if status_code is None:
        return AcquisitionErrorKind.TRANSPORT
    if 200 <= status_code < 300:
        return None
    if status_code in (401, 403):
        return AcquisitionErrorKind.AUTHENTICATION
    if status_code == 404:
        return AcquisitionErrorKind.NOT_FOUND
    if status_code == 429:
        return AcquisitionErrorKind.TOO_MANY_REQUESTS
    return AcquisitionErrorKind.HTTP_STATUS


class Fetcher:
    """Acquiert les pages d'une source et les conserve comme preuves brutes.

    Il est construit une fois et réutilisé : le transport, le magasin et
    l'horloge sont injectés, ce qui rend l'acquisition **testable hors
    ligne** et **rejouable**.
    """

    def __init__(
        self,
        *,
        transport: Transport,
        store: RawStore,
        clock: Callable[[], datetime] | None = None,
        credentials: CredentialProvider | None = None,
        retry: RetryPolicy | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._transport = transport
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._credentials = credentials
        self._retry = retry or RetryPolicy()
        self._sleeper = sleeper or time.sleep

    def acquire(self, adapter: SourceAdapter) -> AcquisitionOutcome:
        """Acquiert toutes les pages de la source et rend l'issue complète."""
        demande = adapter.initial_request()
        demande_initiale = demande
        declare_exhaustion = bool(getattr(adapter, "declares_exhaustion", False))
        started_at = self._clock()
        tentatives: list[AcquisitionAttempt] = []
        preuves: list[RawEvidence] = []
        erreur: AcquisitionErrorKind | None = None
        detail: str | None = None
        page = 0
        tronque = False

        while True:
            if page >= demande.max_pages:
                tronque = True
                break

            reponse, tentatives_page = self._envoyer(demande, page)
            tentatives.extend(tentatives_page)
            tentative = tentatives_page[-1]

            if tentative.error_kind is not None:
                erreur = tentative.error_kind
                detail = tentative.error_detail
                break

            reponse_effective = reponse
            preuve = self._conserver(demande, reponse_effective, page)
            preuves.append(preuve)
            page += 1

            # La poursuite dépend de la réponse reçue : une réponse
            # malformée est un **échec de la source**, pas une fuite. Elle
            # devient une issue structurée, jamais une exception qui sort
            # de l'acquisition sans que rien ne soit consigné.
            try:
                suivante = adapter.next_request(demande, reponse_effective)
            except (ValueError, KeyError) as erreur_adaptateur:
                erreur = AcquisitionErrorKind.MALFORMED
                detail = f"la source a renvoyé une réponse illisible : {erreur_adaptateur}"
                break
            if suivante is None:
                break
            demande = suivante

        finished_at = self._clock()

        if not preuves:
            statut = AcquisitionStatus.FAILED
        elif tronque or erreur is not None:
            statut = AcquisitionStatus.PARTIAL
        else:
            statut = AcquisitionStatus.SUCCESS

        if tronque:
            exhaustivite = Exhaustiveness.TRUNCATED
        elif erreur is not None:
            exhaustivite = Exhaustiveness.UNDECLARED
        elif declare_exhaustion:
            exhaustivite = Exhaustiveness.DECLARED_EXHAUSTED
        else:
            exhaustivite = Exhaustiveness.UNDECLARED

        issue = AcquisitionOutcome(
            request=demande_initiale,
            status=statut,
            started_at=started_at,
            finished_at=finished_at,
            attempts=tuple(tentatives),
            evidence=tuple(preuves),
            error_kind=erreur,
            error_detail=detail,
            exhaustiveness=exhaustivite,
        )

        # L'événement d'acquisition est journalisé **avant** que l'issue ne
        # soit rendue : une acquisition non journalisée n'a pas eu lieu.
        # Si l'écriture du journal échoue, l'erreur remonte — une panne du
        # magasin ne doit pas se déguiser en acquisition réussie.
        self._store.record(issue)
        return issue

    def _envoyer(
        self,
        demande: AcquisitionRequest,
        page: int,
    ) -> tuple[HttpResponse, list[AcquisitionAttempt]]:
        """Envoie une page, avec reprises si la politique l'y autorise.

        Rends **toutes** les tentatives, y compris celles qui ont échoué :
        une reprise qui n'est pas journalisée est une reprise invisible.
        """
        identifiants = self._identifiants(demande)
        retard = self._retry.initial_delay
        journal: list[AcquisitionAttempt] = []

        for essai in range(1, self._retry.max_attempts + 1):
            instant = self._clock()
            try:
                reponse = self._transport.send(demande, credentials=identifiants)
            except TransportError as erreur:
                journal.append(
                    AcquisitionAttempt(
                        page_index=page,
                        requested_at=instant,
                        url=demande.effective_url,
                        error_kind=erreur.kind,
                        error_detail=erreur.detail,
                    )
                )
                if not self._retry.retry_on_transport_error or essai >= self._retry.max_attempts:
                    return HttpResponse(status_code=0, url=demande.effective_url), journal
                self._sleeper(retard)
                retard = min(retard * self._retry.multiplier, self._retry.max_delay)
                continue

            cause = classer_statut(reponse.status_code)
            journal.append(
                AcquisitionAttempt(
                    page_index=page,
                    requested_at=instant,
                    url=demande.effective_url,
                    status_code=reponse.status_code,
                    media_type=reponse.content_type,
                    content_length=len(reponse.body),
                    elapsed_ms=reponse.elapsed_ms,
                    error_kind=cause,
                    error_detail=None if cause is None else f"HTTP {reponse.status_code}",
                )
            )
            if cause is None:
                return reponse, journal
            if (
                cause is not AcquisitionErrorKind.TOO_MANY_REQUESTS
                and reponse.status_code not in self._retry.retry_statuses
            ):
                return reponse, journal
            if essai >= self._retry.max_attempts:
                return reponse, journal
            self._sleeper(self._delai_avant_reprise(reponse, retard))
            retard = min(retard * self._retry.multiplier, self._retry.max_delay)

        return HttpResponse(status_code=0, url=demande.effective_url), journal

    def _delai_avant_reprise(self, reponse: HttpResponse, par_defaut: float) -> float:
        """Le délai à respecter avant de retenter.

        Quand le fournisseur l'a dit — en-tête `Retry-After` — c'est sa
        demande qui fait foi, pas notre impatience.
        """
        indication = reponse.header("retry-after")
        if indication:
            try:
                return max(0.0, min(float(indication), self._retry.max_delay))
            except ValueError:
                return par_defaut
        return par_defaut

    def _identifiants(self, demande: AcquisitionRequest) -> Mapping[str, str]:
        """Les identifiants à appliquer, résolus au dernier moment.

        Ils ne sont jamais ajoutés à la demande : ce qui est consigné garde
        seulement la référence, et le secret ne sort pas d'ici.
        """
        if demande.credential_ref is None or self._credentials is None:
            return MappingProxyType({})
        return MappingProxyType(dict(self._credentials.credentials_for(demande.credential_ref)))

    def _conserver(
        self,
        demande: AcquisitionRequest,
        reponse: HttpResponse,
        page: int,
    ) -> RawEvidence:
        """Conserve la page et rend la preuve brute qui la nomme."""
        cle = f"{demande.label or demande.url}#page={page}"
        return self._store.put(
            reponse.body,
            source_id=demande.source_id,
            key=cle,
            media_type=reponse.content_type,
            acquired_at=self._clock(),
        )


__all__ = ["Fetcher", "RawStore", "RetryPolicy", "classer_statut"]
