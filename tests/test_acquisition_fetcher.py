"""Tests du socle d'acquisition : transport, pagination, reprises, provenance.

Aucun test de ce fichier ne touche le réseau : le transport est remplacé par
un transport d'enregistrement, et l'horloge et la somnolence sont injectées.
C'est ce qui rend le socle testable **et** rejouable.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from torne.acquisition import (
    AcquisitionErrorKind,
    AcquisitionRequest,
    AcquisitionStatus,
    Fetcher,
    HttpResponse,
    RecordingTransport,
    RetryPolicy,
    TransportError,
    classer_statut,
)
from torne.contracts.fingerprint import fingerprint_bytes
from torne.contracts.observation import RawEvidence, Source

INSTANT = datetime(2026, 10, 31, 22, 0, tzinfo=UTC)


class MagasinMemoire:
    """Magasin brut de test : conserve les octets et rend leur empreinte."""

    def __init__(self) -> None:
        self.payloads: list[bytes] = []
        self.keys: list[str] = []

    def put(
        self,
        payload: bytes,
        *,
        source_id: str,
        key: str,
        media_type: str | None,
        acquired_at: datetime,
    ) -> RawEvidence:
        self.payloads.append(payload)
        self.keys.append(key)
        empreinte = fingerprint_bytes(payload)
        return RawEvidence(
            evidence_id=empreinte,
            source_id=source_id,
            acquired_at=acquired_at,
            media_type=media_type,
            content_sha256=empreinte,
            key=key,
        )


class Horloge:
    """Horloge de test : chaque appel avance d'une seconde."""

    def __init__(self) -> None:
        self.appels = 0

    def __call__(self) -> datetime:
        self.appels += 1
        return INSTANT.replace(second=self.appels)


class AdapteurFixe:
    """Adaptateur de test : un nombre de pages décidé à l'avance.

    Il rend `next_request` `None` à la dernière page : c'est ainsi qu'un
    adaptateur signale que la pagination est épuisée.
    """

    def __init__(self, source: Source, nb_pages: int = 1, max_pages: int | None = None) -> None:
        self._source = source
        self._nb_pages = nb_pages
        self._max_pages = max_pages if max_pages is not None else nb_pages
        self._emises = 0
        self.demandes: list[AcquisitionRequest] = []

    @property
    def source(self) -> Source:
        return self._source

    def initial_request(self) -> AcquisitionRequest:
        self._emises = 1
        demande = AcquisitionRequest(
            source_id=self._source.source_id,
            url="https://exemple.test/observations",
            params={"size": "2"},
            label="observations",
            max_pages=self._max_pages,
        )
        self.demandes.append(demande)
        return demande

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        if self._emises >= self._nb_pages:
            return None
        self._emises += 1
        suivante = AcquisitionRequest(
            source_id=request.source_id,
            url=f"{request.url}?page={self._emises}",
            params=request.params,
            label=request.label,
            max_pages=request.max_pages,
        )
        self.demandes.append(suivante)
        return suivante


SOURCE = Source(
    source_id="src-test",
    producer="Institut de test",
    dataset="observations de test",
    access_point="https://exemple.test/observations",
)


def _reponse(
    corps: bytes, statut: int = 200, en_tetes: dict[str, str] | None = None
) -> HttpResponse:
    return HttpResponse(
        status_code=statut,
        headers={"content-type": "application/json", **(en_tetes or {})},
        body=corps,
        url="https://exemple.test/observations",
    )


def _fetcher(transport: RecordingTransport, magasin: MagasinMemoire, **kwargs) -> Fetcher:
    return Fetcher(
        transport=transport,
        store=magasin,
        clock=Horloge(),
        sleeper=lambda _secondes: None,
        **kwargs,
    )


# --------------------------------------------------------------------------
# Une page acquise
# --------------------------------------------------------------------------


def test_une_page_acquise_est_consignee_avec_son_empreinte():
    """Ce qui est reçu est conservé, et nommé par l'empreinte de son contenu."""
    corps = b'{"valeurs": [1, 2]}'
    transport = RecordingTransport([_reponse(corps)])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.page_count == 1
    assert magasin.payloads == [corps]
    assert issue.evidence[0].evidence_id == fingerprint_bytes(corps)
    assert issue.evidence[0].content_sha256 == issue.evidence[0].evidence_id


def test_la_page_consignee_porte_les_parametres_de_la_demande():
    """La demande est conservée : une acquisition doit être rejouable."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert issue.request.source_id == "src-test"
    assert issue.request.params == {"size": "2"}
    assert issue.request.label == "observations"
    assert magasin.keys == ["observations#page=0"]


def test_une_acquisition_renseigne_ses_tentatives():
    """La tentative est consignée, avec l'instant et le code retour."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert len(issue.attempts) == 1
    tentative = issue.attempts[0]
    assert tentative.succeeded
    assert tentative.status_code == 200
    assert tentative.media_type == "application/json"
    assert tentative.requested_at.tzinfo is not None


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------


def test_la_pagination_suit_les_pages_jusqu_a_epuisement():
    """Les pages s'enchaînent jusqu'à ce que l'adaptateur dise stop."""
    transport = RecordingTransport(
        [_reponse(b'{"page": 1}'), _reponse(b'{"page": 2}'), _reponse(b'{"page": 3}')]
    )
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, nb_pages=3))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.page_count == 3
    assert len(transport.requests) == 3
    assert len(magasin.payloads) == 3


def test_une_pagination_interrompue_donne_un_resultat_partiel():
    """Une troncature est un résultat partiel — jamais un succès complet."""
    transport = RecordingTransport([_reponse(b'{"page": 1}')])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, nb_pages=5, max_pages=1))

    assert issue.status is AcquisitionStatus.PARTIAL
    assert issue.page_count == 1


def test_la_source_epuisee_donne_un_succes_et_non_un_partiel():
    """Ce qui s'arrête parce que la source n'a plus n'est pas une troncature.

    La distinction est celle de l'honnêteté du rapport : « j'ai tout pris » et
    « j'ai pris ce que le budget me permettait de prendre » ne se confondent
    pas.
    """
    transport = RecordingTransport([_reponse(b'{"page": 1}')])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, nb_pages=1, max_pages=5))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.page_count == 1


# --------------------------------------------------------------------------
# Échecs
# --------------------------------------------------------------------------


def test_un_404_est_classe_et_refuse():
    """Une ressource absente ne se rattrape pas : elle est signalée."""
    transport = RecordingTransport([_reponse(b"{}", statut=404)])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert issue.status is AcquisitionStatus.FAILED
    assert issue.error_kind is AcquisitionErrorKind.NOT_FOUND
    assert issue.page_count == 0
    assert len(transport.requests) == 1


def test_un_echec_de_transport_est_classe():
    """Une coupure réseau est distinguishable d'un refus du fournisseur."""

    class TransportCasse:
        def send(self, request, *, credentials=None):
            raise TransportError("connexion coupée")

    magasin = MagasinMemoire()
    fetcher = Fetcher(
        transport=TransportCasse(),
        store=magasin,
        clock=Horloge(),
        sleeper=lambda _secondes: None,
        retry=RetryPolicy(max_attempts=2),
    )

    issue = fetcher.acquire(AdapteurFixe(SOURCE))

    assert issue.status is AcquisitionStatus.FAILED
    assert issue.error_kind is AcquisitionErrorKind.TRANSPORT
    assert len(issue.attempts) == 2


def test_une_erreur_temporaire_est_reprise():
    """Une saturation se retente, et la reprise est consignée."""
    transport = RecordingTransport([_reponse(b"{}", 503), _reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert len(issue.attempts) == 2
    assert issue.attempts[0].error_kind is AcquisitionErrorKind.HTTP_STATUS
    assert issue.attempts[1].succeeded
    assert issue.page_count == 1


def test_le_delai_annonce_par_le_fournisseur_est_respecte():
    """Quand le fournisseur dit d'attendre, c'est sa demande qui fait foi."""
    delais: list[float] = []
    transport = RecordingTransport([_reponse(b"{}", 429, {"retry-after": "7"}), _reponse(b"{}")])
    magasin = MagasinMemoire()
    fetcher = Fetcher(
        transport=transport,
        store=magasin,
        clock=Horloge(),
        sleeper=delais.append,
        retry=RetryPolicy(initial_delay=0.5),
    )

    issue = fetcher.acquire(AdapteurFixe(SOURCE))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert delais == [7.0]


@pytest.mark.parametrize(
    ("statut", "attendu"),
    [
        (200, None),
        (204, None),
        (401, AcquisitionErrorKind.AUTHENTICATION),
        (403, AcquisitionErrorKind.AUTHENTICATION),
        (404, AcquisitionErrorKind.NOT_FOUND),
        (429, AcquisitionErrorKind.TOO_MANY_REQUESTS),
        (500, AcquisitionErrorKind.HTTP_STATUS),
    ],
)
def test_les_codes_de_retour_sont_classes(statut: int, attendu: AcquisitionErrorKind | None):
    """Chaque cause d'échec a son nom : « rien à signaler » n'existe pas."""
    assert classer_statut(statut) is attendu


# --------------------------------------------------------------------------
# Secrets
# --------------------------------------------------------------------------


class FournisseurFictif:
    """Fournisseur d'identifiants de test."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def credentials_for(self, credential_ref: str) -> dict[str, str]:
        return {"authorization": f"Bearer {self._secret}"}


def test_le_secret_arrive_au_transport_mais_nentre_dans_la_demande():
    """Les identifiants sont appliqués au dernier moment, et ne sont pas consignés.

    C'est la garantie qu'un journal d'acquisition peut être publié : la
    demande consignée porte une **référence**, jamais une valeur.
    """
    secret = "jeton-confidentiel-000"
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()
    fetcher = _fetcher(transport, magasin, credentials=FournisseurFictif(secret))
    adaptateur = AdapteurFixe(SOURCE)
    demande_initiale = adaptateur.initial_request()
    demande_avec_secret = AcquisitionRequest(
        source_id=demande_initiale.source_id,
        url=demande_initiale.url,
        params=demande_initiale.params,
        credential_ref="api-principale",
        label=demande_initiale.label,
    )
    adaptateur.initial_request = lambda: demande_avec_secret

    issue = fetcher.acquire(adaptateur)

    # Le secret est bien parti sur le réseau.
    assert transport.credentials_seen[0]["authorization"] == f"Bearer {secret}"
    # Mais il n'est nulle part dans ce qui est consigné.
    assert secret not in repr(issue.as_dict())
    assert issue.request.credential_ref == "api-principale"
    assert "credential_ref" in issue.as_dict()


def test_une_demande_sans_reference_ne_recoit_aucun_identifiant():
    """Sans référence, rien n'est appliqué : le silence est le défaut."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert transport.credentials_seen[0] == {}
