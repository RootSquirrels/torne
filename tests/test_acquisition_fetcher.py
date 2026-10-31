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
    Conformite,
    CritereConformite,
    Exhaustiveness,
    Fetcher,
    HttpResponse,
    RecordingTransport,
    RetryPolicy,
    TransportError,
    VerdictConformite,
    classer_statut,
)
from torne.contracts.fingerprint import fingerprint_bytes
from torne.contracts.observation import RawEvidence, Source

INSTANT = datetime(2026, 10, 31, 22, 0, tzinfo=UTC)


class MagasinMemoire:
    """Magasin brut de test : conserve les octets et journalise les acquisitions."""

    def __init__(self) -> None:
        self.payloads: list[bytes] = []
        self.keys: list[str] = []
        self.evenements: list[object] = []

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

    def record(self, outcome) -> None:
        self.evenements.append(outcome)


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

    def __init__(
        self,
        source: Source,
        nb_pages: int = 1,
        max_pages: int | None = None,
        declares_exhaustion: bool = False,
        erreur_adaptateur: Exception | None = None,
        verdict: VerdictConformite | None = None,
    ) -> None:
        self._source = source
        self._nb_pages = nb_pages
        self._max_pages = max_pages if max_pages is not None else nb_pages
        self._declares_exhaustion = declares_exhaustion
        self._erreur_adaptateur = erreur_adaptateur
        self._verdict = verdict
        self._emises = 0
        self.demandes: list[AcquisitionRequest] = []

    @property
    def source(self) -> Source:
        return self._source

    @property
    def declares_exhaustion(self) -> bool:
        return self._declares_exhaustion

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
        if self._erreur_adaptateur is not None:
            raise self._erreur_adaptateur
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

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Le verdict rendu par cet adaptateur de test.

        Par défaut, l'adaptateur ne déclare **aucun** critère sémantique : le
        verdict est `non_applicable`, et non « conforme ». Une absence de
        critère n'est pas un critère satisfait.
        """
        if self._verdict is not None:
            return self._verdict
        return VerdictConformite(conformite=Conformite.NON_APPLICABLE)


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
# Exhaustivité : ce que la source déclare, ou ne déclare pas
# --------------------------------------------------------------------------


def test_une_source_qui_declaire_son_epuisement_le_dit():
    """Quand la source dit « il n'y a plus rien », l'issue le dit aussi."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, declares_exhaustion=True))

    assert issue.exhaustiveness is Exhaustiveness.DECLARED_EXHAUSTED


def test_une_source_sans_pagination_ne_declaire_pas_l_exhaustivite():
    """Une réponse réussie ne prouve pas que tout a été rendu.

    C'est le cas le plus fréquent : une source qui renvoie tout d'un coup ne
    dit rien de ce qu'elle aurait pu rendre. L'issue doit le dire, plutôt que
    de laisser croire à un parcours complet.
    """
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, declares_exhaustion=False))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.exhaustiveness is Exhaustiveness.UNDECLARED


def test_un_parcours_tronque_est_declare_tronque():
    """Le budget qui arrête le parcours est une troncature, pas une fin."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, nb_pages=5, max_pages=1, declares_exhaustion=True)
    )

    assert issue.exhaustiveness is Exhaustiveness.TRUNCATED


# --------------------------------------------------------------------------
# Journalisation
# --------------------------------------------------------------------------


def test_l_acquisition_est_journalisee_avant_d_etre_rendue():
    """Une acquisition non journalisée n'a pas eu lieu."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert len(magasin.evenements) == 1
    evenement = magasin.evenements[0]
    assert evenement is issue
    assert evenement.status is AcquisitionStatus.SUCCESS


def test_une_acquisition_echouee_est_elle_aussi_journalisee():
    """L'échec est un résultat : il est journalisé comme le succès."""
    transport = RecordingTransport([_reponse(b"{}", statut=404)])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert len(magasin.evenements) == 1
    evenement = magasin.evenements[0]
    assert evenement is issue
    assert evenement.status is AcquisitionStatus.FAILED
    assert evenement.error_kind is AcquisitionErrorKind.NOT_FOUND


# --------------------------------------------------------------------------
# Erreurs d'adaptateur : une réponse illisible est un échec structuré
# --------------------------------------------------------------------------


def test_une_reponse_illisible_devient_une_issue_structuree():
    """Une réponse malformée ne doit pas faire sortir brutalement l'acquisition.

    L'adaptateur lève en lisant la réponse : c'est un échec de la source, pas
    une fuite. L'acquisition rend une issue, et elle est journalisée.
    """
    transport = RecordingTransport([_reponse(b"pas du json")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, erreur_adaptateur=ValueError("champ « data » absent"))
    )

    assert issue.status is AcquisitionStatus.PARTIAL
    assert issue.error_kind is AcquisitionErrorKind.MALFORMED
    assert "data" in (issue.error_detail or "")
    assert len(magasin.evenements) == 1


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


# --------------------------------------------------------------------------
# Conformité — la porte
# --------------------------------------------------------------------------


def _verdict_non_conforme() -> VerdictConformite:
    """Le verdict d'une source qui a renvoyé les lignes d'une autre station."""
    return VerdictConformite(
        conformite=Conformite.NON_CONFORME,
        motif=(
            "la source a renvoyé des lignes qui ne sont pas celles demandées : "
            "code_station demandé « O919001001 », reçu « O509252003 »"
        ),
        criteres={
            "code_station": CritereConformite(
                demande="O919001001",
                verifie=True,
                recu="O509252003",
                conforme=False,
            )
        },
    )


def test_une_source_qui_renvoie_les_lignes_d_une_autre_station_ne_cree_aucune_observation():
    """La porte : un verdict défavorable bloque, et la porte est explicite.

    C'est le test central de la conformité d'acquisition : la réponse a été
    reçue, et elle **ne produit aucune observation**.
    """
    transport = RecordingTransport([_reponse(b'{"data": []}')])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, verdict=_verdict_non_conforme())
    )

    assert issue.conformite is Conformite.NON_CONFORME
    assert issue.exploitable is False


def test_la_reussite_du_transport_reste_lisible_quand_la_conformite_echoue():
    """Les deux axes sont distincts : l'acquisition a abouti, la conformité non.

    L'arbitrage est explicite : présenter la non-conformité comme un échec
    d'acquisition rendrait ambiguë la réussite du transport. La réponse est
    arrivée, elle est conservée, et son contenu n'est pas exploitable. Aucun
    statut ni aucune cause ne prétend le contraire.
    """
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, verdict=_verdict_non_conforme())
    )

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.succeeded is True
    assert issue.error_kind is None
    assert issue.conformite is Conformite.NON_CONFORME
    assert issue.exploitable is False


def test_la_reponse_brute_est_conservee_malgre_la_non_conformite():
    """Une réponse qui a répondu à côté est une preuve : elle est conservée.

    La preuve brute est écrite **avant** toute interprétation, et elle reste
    là même quand le verdict est défavorable : c'est elle qui dit ce que le
    fournisseur a réellement répondu.
    """
    corps = b'{"data": [{"code_station": "O509252003"}]}'
    transport = RecordingTransport([_reponse(corps)])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, verdict=_verdict_non_conforme())
    )

    assert magasin.payloads == [corps]
    assert len(issue.evidence) == 1
    assert issue.evidence[0].content_sha256 == fingerprint_bytes(corps)


def test_le_verdict_est_consigne_dans_issue_et_journal():
    """Le verdict est consigné : motif et critères, pas seulement un statut."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, verdict=_verdict_non_conforme())
    )

    consignee = issue.as_dict()
    assert consignee["conformite"] == "non_conforme"
    assert "O509252003" in consignee["motif_conformite"]
    assert consignee["criteres_conformite"]["code_station"]["conforme"] is False
    assert len(magasin.evenements) == 1


def test_la_porte_arrete_le_parcours():
    """Demander la page suivante d'une source qui a répondu à côté n'apporte rien."""
    transport = RecordingTransport([_reponse(b"{}"), _reponse(b"{}"), _reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, nb_pages=3, verdict=_verdict_non_conforme())
    )

    assert len(transport.requests) == 1
    assert issue.page_count == 1
    assert issue.status is AcquisitionStatus.PARTIAL


def test_une_exhaustivite_indeclaree_accompagne_un_verdict_non_conforme():
    """La porte arrête le parcours : on ne sait donc plus ce qu'il restait.

    Une source qui a répondu à côté n'a pas déclaré avoir été épuisée, et le
    parcours s'est arrêté avant sa fin : l'exhaustivité est **indéclarée**.
    """
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(
        AdapteurFixe(SOURCE, declares_exhaustion=True, verdict=_verdict_non_conforme())
    )

    assert issue.exhaustiveness is Exhaustiveness.UNDECLARED


def test_une_absence_de_verdict_n_est_pas_une_conformite():
    """Pas de verdict, pas de conformité : l'absence de contrôle ne passe pas."""
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE))

    assert issue.conformite is Conformite.NON_APPLICABLE
    assert issue.verdict_conformite is not None
    assert issue.verdict_conformite.conforme is False


def test_une_conformite_verifiee_laisse_l_issue_exploitable():
    """Une source qui répond à la question n'est pas bloquée."""
    verdict = VerdictConformite(
        conformite=Conformite.CONFORME,
        criteres={
            "code_station": CritereConformite(
                demande="O919001001",
                verifie=True,
                recu="O919001001",
                conforme=True,
            )
        },
    )
    transport = RecordingTransport([_reponse(b"{}")])
    magasin = MagasinMemoire()

    issue = _fetcher(transport, magasin).acquire(AdapteurFixe(SOURCE, verdict=verdict))

    assert issue.status is AcquisitionStatus.SUCCESS
    assert issue.conformite is Conformite.CONFORME
    assert issue.exploitable is True


def test_un_verdict_non_conforme_sans_motif_est_refuse():
    """Un verdict qui ne dit pas pourquoi n'est pas un verdict acceptable."""
    with pytest.raises(ValueError, match="motif"):
        VerdictConformite(conformite=Conformite.NON_CONFORME)


def test_un_critere_non_verifiable_ne_peut_pas_etre_donne_conforme():
    """Ce qui n'a pas pu être vérifié ne peut pas être déclaré conforme."""
    with pytest.raises(ValueError, match="non vérifiable"):
        CritereConformite(demande="code_cours_eau", verifie=False, conforme=True)
