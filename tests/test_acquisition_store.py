"""Tests du magasin brut — le contenu dédupliqué, l'acquisition journalisée.

Chaque test est une question à laquelle le magasin doit répondre par oui ou
par non, et les questions sont celles des invariants : le contenu brut n'est
écrit qu'une fois (INV-01), une version nouvelle ne détruit pas l'ancienne
(INV-02), toute acquisition est consignée (INV-03), et aucun instant n'est
stocké sans fuseau (INV-15).

Le magasin distingue trois niveaux, et les tests les distinguent aussi :

- le **contenu** est dédupliqué par empreinte ;
- l'**événement d'acquisition** ne l'est jamais : deux acquisitions du même
  contenu donnent deux lignes de journal ;
- l'instant porté par le contenu est celui de sa **première conservation**,
  jamais celui d'une récupération plus tardive.
"""

from __future__ import annotations

import inspect
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from torne.acquisition.contracts import (
    AcquisitionAttempt,
    AcquisitionErrorKind,
    AcquisitionOutcome,
    AcquisitionRequest,
    AcquisitionStatus,
    Exhaustiveness,
)
from torne.acquisition.store import FileRawStore, RawStore
from torne.contracts.fingerprint import fingerprint_bytes
from torne.contracts.observation import RawEvidence

SOURCE = "hubeau.hydrometrie.observations_tr"


def _instant(seconde: int = 0) -> datetime:
    """Un instant UTC, décalé de quelques secondes."""
    return datetime(2026, 10, 31, 12, 0, seconde, tzinfo=UTC)


def _demande() -> AcquisitionRequest:
    """La demande qui a produit l'acquisition."""
    return AcquisitionRequest(
        source_id=SOURCE,
        url="https://exemple.test/observations",
        params={"size": "1"},
        credential_ref="api-principale",
        label="observations",
    )


def _issue(
    *,
    status: AcquisitionStatus = AcquisitionStatus.SUCCESS,
    exhaustiveness: Exhaustiveness = Exhaustiveness.DECLARED_EXHAUSTED,
    tentatives: tuple[AcquisitionAttempt, ...] = (),
    preuves: tuple[RawEvidence, ...] = (),
    error_kind: AcquisitionErrorKind | None = None,
    error_detail: str | None = None,
    debut: datetime | None = None,
    fin: datetime | None = None,
) -> AcquisitionOutcome:
    """Une issue d'acquisition, telle que le socle la rend."""
    return AcquisitionOutcome(
        request=_demande(),
        status=status,
        started_at=debut if debut is not None else _instant(0),
        finished_at=fin if fin is not None else _instant(10),
        attempts=tentatives,
        evidence=preuves,
        error_kind=error_kind,
        error_detail=error_detail,
        exhaustiveness=exhaustiveness,
    )


def _acquerir(
    magasin: FileRawStore,
    contenu: bytes,
    *,
    instant: datetime,
    cle: str = "observations#page=0",
) -> RawEvidence:
    """Une acquisition complète : le contenu est conservé, puis journalisé."""
    preuve = magasin.put(
        contenu,
        source_id=SOURCE,
        key=cle,
        media_type="application/json",
        acquired_at=instant,
    )
    magasin.record(_issue(preuves=(preuve,), debut=instant, fin=instant + timedelta(seconds=10)))
    return preuve


def _fichiers_de_contenu(racine: Path) -> list[Path]:
    """Les fichiers de contenu du magasin, le journal mis à part."""
    return [
        chemin
        for chemin in racine.rglob("*")
        if chemin.is_file() and chemin.name != "manifeste.jsonl"
    ]


def test_le_magasin_satisfait_le_contrat_du_fetcher(tmp_path: Path):
    """Le magasin implémente bien le contrat dont le fetcher dépend."""
    magasin = FileRawStore(tmp_path)
    assert isinstance(magasin, RawStore)


def test_put_suit_la_forme_attendue_par_le_fetcher():
    """La signature de `put` est celle dont le fetcher a besoin.

    Le contenu est passé en positionnel, tout le reste en mot-clé : c'est
    ce que le fetcher appelle, et rien d'autre n'est admis.
    """
    parametres = inspect.signature(FileRawStore.put).parameters

    assert list(parametres) == ["self", "payload", "source_id", "key", "media_type", "acquired_at"]
    assert parametres["payload"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for nom in ("source_id", "key", "media_type", "acquired_at"):
        assert parametres[nom].kind is inspect.Parameter.KEYWORD_ONLY


def test_record_suit_la_forme_attendue_par_le_fetcher():
    """`record` prend l'issue d'acquisition, et rien d'autre.

    C'est tout ce dont le socle dispose pour écrire l'événement : l'issue
    porte la demande, les tentatives, les pages acquises et l'issue elle-même.
    """
    parametres = inspect.signature(FileRawStore.record).parameters

    assert list(parametres) == ["self", "outcome"]
    assert parametres["outcome"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_put_rend_une_preuve_brute_empreinte_du_contenu(tmp_path: Path):
    """L'empreinte du contenu brut est l'identifiant de la preuve."""
    magasin = FileRawStore(tmp_path)
    contenu = b'{"data": []}'

    preuve = magasin.put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )

    empreinte = fingerprint_bytes(contenu)
    assert preuve.evidence_id == empreinte
    assert preuve.content_sha256 == empreinte
    assert preuve.source_id == SOURCE
    assert preuve.key == "page=1"
    assert preuve.media_type == "application/json"
    assert preuve.acquired_at == _instant()


def test_le_contenu_est_ecrit_sous_un_chemin_derive_de_son_empreinte(tmp_path: Path):
    """Le chemin du fichier se déduit de l'empreinte, sans index."""
    magasin = FileRawStore(tmp_path)
    contenu = b"octets bruts"

    preuve = magasin.put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type=None,
        acquired_at=_instant(),
    )

    fichier = tmp_path / preuve.evidence_id[:2] / preuve.evidence_id
    assert fichier.exists()
    assert fichier.read_bytes() == contenu
    assert magasin.content_path(preuve.evidence_id) == fichier


def test_deux_acquisitions_du_meme_contenu_partagent_le_meme_fichier(tmp_path: Path):
    """INV-01 : le même contenu n'est écrit qu'une fois, et n'est pas réécrit."""
    magasin = FileRawStore(tmp_path)
    contenu = b'{"data": []}'

    premiere = magasin.put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )
    fichier = magasin.content_path(premiere.evidence_id)
    avant = fichier.stat().st_mtime_ns

    seconde = magasin.put(
        contenu,
        source_id="usgs.nwis.iv",
        key="fenetre=P7D",
        media_type="application/json",
        acquired_at=_instant(),
    )

    assert seconde.evidence_id == premiere.evidence_id
    assert len(_fichiers_de_contenu(tmp_path)) == 1
    assert fichier.read_bytes() == contenu
    assert fichier.stat().st_mtime_ns == avant


def test_le_contenu_est_deduplique_mais_chaque_acquisition_est_journalisee(tmp_path: Path):
    """Le contenu se déduplique ; l'acquisition, jamais.

    C'est le cœur de la correction : deux récupérations du même contenu
    laissent **un** fichier, mais **deux** événements de journal. Sans cela,
    six mois d'acquisitions identiques disparaissent dans un seul inventaire.
    """
    magasin = FileRawStore(tmp_path)
    contenu = b'{"data": []}'

    _acquerir(magasin, contenu, instant=_instant(0))
    _acquerir(magasin, contenu, instant=_instant(30))

    assert len(_fichiers_de_contenu(tmp_path)) == 1
    assert len(magasin.read_manifest()) == 2


def test_l_instant_de_premiere_conservation_ne_bouge_pas(tmp_path: Path):
    """Reprendre un contenu ne le rend pas plus récent.

    L'instant d'un contenu est celui de sa **première** conservation : le
    second `put` rend donc le même `acquired_at` que le premier, et le
    journal porte cet instant-là — pas celui de la dernière récupération.
    """
    magasin = FileRawStore(tmp_path)
    contenu = b'{"data": []}'

    premiere = _acquerir(magasin, contenu, instant=_instant(0))
    seconde = _acquerir(magasin, contenu, instant=_instant(30))

    assert premiere.acquired_at == _instant(0)
    assert seconde.acquired_at == premiere.acquired_at

    evenements = magasin.read_manifest()
    assert evenements[0]["pages"][0]["known_at"] == "2026-10-31T12:00:00+00:00"
    assert evenements[1]["pages"][0]["known_at"] == "2026-10-31T12:00:00+00:00"
    # L'événement, lui, porte l'instant de CETTE acquisition.
    assert evenements[0]["acquired_at"] == "2026-10-31T12:00:10+00:00"
    assert evenements[1]["acquired_at"] == "2026-10-31T12:00:40+00:00"


def test_l_instant_de_premiere_conservation_survit_a_un_redemarrage(tmp_path: Path):
    """Un magasin neuf retrouve la date de connaissance d'un contenu connu.

    L'index des instants de première conservation est reconstruit depuis le
    journal : il n'y a pas de second fichier à maintenir, et le magasin
    reste juste après un redémarrage.
    """
    contenu = b'{"data": []}'
    _acquerir(FileRawStore(tmp_path), contenu, instant=_instant(0))

    preuve = FileRawStore(tmp_path).put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(30),
    )

    assert preuve.acquired_at == _instant(0)


def test_un_contenu_modifie_cree_une_version_nouvelle_sans_toucher_l_ancienne(tmp_path: Path):
    """INV-02 : une version nouvelle laisse l'ancienne lisible et inchangée."""
    magasin = FileRawStore(tmp_path)

    ancienne = _acquerir(magasin, b"version 1", instant=_instant(0))
    nouvelle = _acquerir(magasin, b"version 2", instant=_instant(0))

    assert nouvelle.evidence_id != ancienne.evidence_id
    assert magasin.content_path(ancienne.evidence_id).read_bytes() == b"version 1"
    assert magasin.content_path(nouvelle.evidence_id).read_bytes() == b"version 2"
    assert len(magasin.read_manifest()) == 2


def test_le_manifeste_est_append_only(tmp_path: Path):
    """Le journal ne se réécrit pas : une ligne ajoutée ne touche pas les autres."""
    magasin = FileRawStore(tmp_path)

    _acquerir(magasin, b"premiere", instant=_instant(0))
    avant = magasin.manifest_path.read_bytes()

    _acquerir(magasin, b"seconde", instant=_instant(0))
    apres = magasin.manifest_path.read_bytes()

    assert apres.startswith(avant)
    assert len(apres.splitlines()) == 2


def test_le_manifeste_est_rejouable(tmp_path: Path):
    """Le journal se relit, et dit ce qui a été acquis, quand, et par quelle clé."""
    magasin = FileRawStore(tmp_path)

    _acquerir(magasin, b"premiere", instant=_instant(0))
    _acquerir(magasin, b"seconde", instant=_instant(0), cle="observations#page=1")

    entrees = magasin.read_manifest()
    assert len(entrees) == 2
    assert entrees[0]["source_id"] == SOURCE
    assert entrees[0]["key"] == "observations"
    assert entrees[0]["status"] == "success"
    assert entrees[0]["exhaustiveness"] == "declared_exhausted"
    assert entrees[0]["content_sha256"] == [fingerprint_bytes(b"premiere")]
    assert entrees[0]["pages"][0]["content_sha256"] == fingerprint_bytes(b"premiere")
    assert entrees[0]["pages"][0]["media_type"] == "application/json"
    assert entrees[0]["pages"][0]["size"] == len(b"premiere")
    assert entrees[0]["pages"][0]["key"] == "observations#page=0"
    assert entrees[0]["acquired_at"] == "2026-10-31T12:00:10+00:00"
    assert entrees[1]["pages"][0]["key"] == "observations#page=1"
    assert entrees[1]["content_sha256"] == [fingerprint_bytes(b"seconde")]


def test_le_manifeste_normalise_l_instant_en_utc(tmp_path: Path):
    """L'instant consigné est en UTC, jamais l'heure locale de l'exécutant."""
    magasin = FileRawStore(tmp_path)
    instant = datetime(2026, 10, 31, 14, 0, tzinfo=timezone(timedelta(hours=2)))

    preuve = magasin.put(
        b"contenu",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=instant,
    )
    magasin.record(_issue(preuves=(preuve,)))

    entree = magasin.read_manifest()[0]
    assert preuve.acquired_at == datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    assert entree["pages"][0]["known_at"] == "2026-10-31T12:00:00+00:00"


def test_l_ecriture_est_atomique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Un fichier écrit à moitié ne laisse pas de trace exploitable."""

    def _renommage_echoue(source: str, cible: str) -> None:
        raise OSError("le renommage a échoué")

    monkeypatch.setattr(os, "replace", _renommage_echoue)
    magasin = FileRawStore(tmp_path)

    with pytest.raises(OSError, match="renommage"):
        magasin.put(
            b"contenu",
            source_id=SOURCE,
            key="page=1",
            media_type="application/json",
            acquired_at=_instant(),
        )

    assert not [chemin for chemin in tmp_path.rglob("*") if chemin.is_file()]
    assert not magasin.manifest_path.exists()


def test_un_instant_naif_est_refuse_sans_ecrire(tmp_path: Path):
    """INV-15 : un instant sans fuseau est refusé à l'entrée, et rien n'est écrit."""
    magasin = FileRawStore(tmp_path)

    with pytest.raises(ValueError, match="sans fuseau"):
        magasin.put(
            b"contenu",
            source_id=SOURCE,
            key="page=1",
            media_type="application/json",
            acquired_at=datetime(2026, 10, 31, 12, 0),
        )

    assert not list(tmp_path.rglob("*"))


def test_un_contenu_vide_est_consigne(tmp_path: Path):
    """Une réponse vide est une acquisition comme une autre : elle est consignée."""
    magasin = FileRawStore(tmp_path)

    preuve = _acquerir(magasin, b"", instant=_instant(0))

    assert preuve.evidence_id == fingerprint_bytes(b"")
    assert magasin.content_path(preuve.evidence_id).read_bytes() == b""
    assert magasin.read_manifest()[0]["pages"][0]["size"] == 0


def test_un_manifeste_illisible_est_signale(tmp_path: Path):
    """Un manifeste abimé se voit : il n'est jamais ignoré en silence."""
    magasin = FileRawStore(tmp_path)
    magasin.manifest_path.write_text("ceci n'est pas du json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="manifeste illisible"):
        magasin.read_manifest()


# --------------------------------------------------------------------------
# L'événement d'acquisition
# --------------------------------------------------------------------------


def test_record_porte_le_statut_et_lexhaustivite(tmp_path: Path):
    """L'issue dit ce qui s'est passé, et ce que l'on sait de l'exhaustivité."""
    magasin = FileRawStore(tmp_path)

    magasin.record(
        _issue(
            status=AcquisitionStatus.PARTIAL,
            exhaustiveness=Exhaustiveness.TRUNCATED,
            error_kind=AcquisitionErrorKind.TRANSPORT,
            error_detail="connexion coupée",
        )
    )

    evenement = magasin.read_manifest()[0]
    assert evenement["event"] == "acquisition"
    assert evenement["status"] == "partial"
    assert evenement["exhaustiveness"] == "truncated"
    assert evenement["error_kind"] == "transport"
    assert evenement["error_detail"] == "connexion coupée"
    assert evenement["source_id"] == SOURCE
    assert evenement["label"] == "observations"
    assert evenement["url"] == "https://exemple.test/observations"
    assert evenement["request_id"].startswith("acq-")


def test_record_conserve_les_tentatives_echouees_autant_que_les_reussies(tmp_path: Path):
    """Une reprise qui échoue reste dans le journal : c'est l'audit du dialogue.

    Une tentative qui rate est un résultat : sans elle, on ne sait pas que la
    page a été demandée, ni ce qu'elle a répondu.
    """
    magasin = FileRawStore(tmp_path)
    preuve = magasin.put(
        b'{"data": []}',
        source_id=SOURCE,
        key="observations#page=0",
        media_type="application/json",
        acquired_at=_instant(0),
    )

    magasin.record(
        _issue(
            status=AcquisitionStatus.PARTIAL,
            exhaustiveness=Exhaustiveness.UNDECLARED,
            preuves=(preuve,),
            tentatives=(
                AcquisitionAttempt(
                    page_index=0,
                    requested_at=_instant(1),
                    url="https://exemple.test/observations",
                    status_code=503,
                    error_kind=AcquisitionErrorKind.HTTP_STATUS,
                    error_detail="HTTP 503",
                ),
                AcquisitionAttempt(
                    page_index=0,
                    requested_at=_instant(2),
                    url="https://exemple.test/observations",
                    status_code=200,
                    media_type="application/json",
                    content_length=12,
                    elapsed_ms=41,
                ),
            ),
        )
    )

    tentatives = magasin.read_manifest()[0]["attempts"]
    assert len(tentatives) == 2
    assert tentatives[0]["page_index"] == 0
    assert tentatives[0]["requested_at"] == "2026-10-31T12:00:01+00:00"
    assert tentatives[0]["url"] == "https://exemple.test/observations"
    assert tentatives[0]["status_code"] == 503
    assert tentatives[0]["error_kind"] == "http_status"
    assert tentatives[0]["error_detail"] == "HTTP 503"
    assert tentatives[1]["status_code"] == 200
    assert tentatives[1]["error_kind"] is None


def test_une_acquisition_echouee_est_journalisee(tmp_path: Path):
    """L'échec est un résultat : il est journalisé comme le succès."""
    magasin = FileRawStore(tmp_path)

    magasin.record(
        _issue(
            status=AcquisitionStatus.FAILED,
            exhaustiveness=Exhaustiveness.UNDECLARED,
            error_kind=AcquisitionErrorKind.NOT_FOUND,
            error_detail="HTTP 404",
            tentatives=(
                AcquisitionAttempt(
                    page_index=0,
                    requested_at=_instant(1),
                    url="https://exemple.test/observations",
                    status_code=404,
                    error_kind=AcquisitionErrorKind.NOT_FOUND,
                    error_detail="HTTP 404",
                ),
            ),
        )
    )

    evenement = magasin.read_manifest()[0]
    assert evenement["status"] == "failed"
    assert evenement["error_kind"] == "not_found"
    assert evenement["pages"] == []
    assert evenement["content_sha256"] == []
    assert evenement["attempts"][0]["status_code"] == 404


def test_record_ne_deduplique_pas(tmp_path: Path):
    """Deux issues identiques donnent deux lignes : une acquisition, une ligne."""
    magasin = FileRawStore(tmp_path)
    issue = _issue()

    magasin.record(issue)
    magasin.record(issue)

    assert len(magasin.read_manifest()) == 2


def test_record_refuse_autre_chose_qu_une_issue(tmp_path: Path):
    """Seule une issue d'acquisition peut être journalisée."""
    magasin = FileRawStore(tmp_path)

    with pytest.raises(TypeError, match="AcquisitionOutcome"):
        magasin.record({"source_id": SOURCE})


def test_le_journal_ne_conserve_qu_une_reference_de_secret(tmp_path: Path):
    """La demande consignée porte une référence, jamais la valeur du secret.

    C'est la garantie qu'un journal d'acquisition peut être publié sans
    exposer les identifiants.
    """
    magasin = FileRawStore(tmp_path)

    magasin.record(_issue())

    evenement = magasin.read_manifest()[0]
    assert evenement["credential_ref"] == "api-principale"
    assert "authorization" not in evenement


def test_le_journal_n_est_pas_relu_a_chaque_ecriture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """L'index des dates de connaissance est chargé une fois, pas à chaque page.

    Relire un journal de six mois à chaque écriture serait hors de prix :
    l'index est reconstruit une fois, puis tenu à jour en mémoire.
    """
    magasin = FileRawStore(tmp_path)
    lectures: list[int] = []
    original = FileRawStore._lire_le_journal

    def _compte(self: FileRawStore) -> list[dict[str, object]]:
        lectures.append(1)
        return original(self)

    monkeypatch.setattr(FileRawStore, "_lire_le_journal", _compte)

    for numero in range(5):
        magasin.put(
            f"contenu {numero}".encode(),
            source_id=SOURCE,
            key=f"page={numero}",
            media_type="application/json",
            acquired_at=_instant(numero),
        )

    assert len(lectures) == 1
