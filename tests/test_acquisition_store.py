"""Tests du magasin brut — la conservation adressée par le contenu.

Chaque test est une question à laquelle le magasin doit répondre par oui ou
par non, et les questions sont celles des invariants : le contenu brut n'est
écrit qu'une fois (INV-01), une version nouvelle ne détruit pas l'ancienne
(INV-02), toute acquisition est consignée (INV-03), et aucun instant n'est
stocké sans fuseau (INV-15).
"""

from __future__ import annotations

import inspect
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from torne.acquisition.store import FileRawStore, RawStore
from torne.contracts.fingerprint import fingerprint_bytes

SOURCE = "hubeau.hydrometrie.observations_tr"


def _instant() -> datetime:
    return datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def _fichiers_de_contenu(racine: Path) -> list[Path]:
    """Les fichiers de contenu du magasin, le manifeste mis à part."""
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


def test_put_est_idempotent_pour_le_meme_triplet(tmp_path: Path):
    """Même contenu, même source, même clé : une seule ligne de manifeste."""
    magasin = FileRawStore(tmp_path)
    contenu = b"idem"

    premiere = magasin.put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )
    seconde = magasin.put(
        contenu,
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )

    assert premiere == seconde
    assert len(magasin.read_manifest()) == 1
    assert len(_fichiers_de_contenu(tmp_path)) == 1


def test_un_contenu_modifie_cree_une_version_nouvelle_sans_toucher_l_ancienne(tmp_path: Path):
    """INV-02 : une version nouvelle laisse l'ancienne lisible et inchangée."""
    magasin = FileRawStore(tmp_path)

    ancienne = magasin.put(
        b"version 1",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )
    nouvelle = magasin.put(
        b"version 2",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )

    assert nouvelle.evidence_id != ancienne.evidence_id
    assert magasin.content_path(ancienne.evidence_id).read_bytes() == b"version 1"
    assert magasin.content_path(nouvelle.evidence_id).read_bytes() == b"version 2"
    assert len(magasin.read_manifest()) == 2


def test_le_manifeste_est_append_only(tmp_path: Path):
    """Le journal ne se réécrit pas : une ligne ajoutée ne touche pas les autres."""
    magasin = FileRawStore(tmp_path)

    magasin.put(
        b"premiere",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )
    avant = magasin.manifest_path.read_bytes()

    magasin.put(
        b"seconde",
        source_id=SOURCE,
        key="page=2",
        media_type="application/json",
        acquired_at=_instant(),
    )
    apres = magasin.manifest_path.read_bytes()

    assert apres.startswith(avant)
    assert len(apres.splitlines()) == 2


def test_le_manifeste_est_rejouable(tmp_path: Path):
    """Le journal se relit, et dit ce qui a été acquis, quand, et par quelle clé."""
    magasin = FileRawStore(tmp_path)

    magasin.put(
        b"premiere",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )
    magasin.put(
        b"seconde",
        source_id="usgs.nwis.iv",
        key="fenetre=P7D",
        media_type=None,
        acquired_at=_instant(),
    )

    entrees = magasin.read_manifest()
    assert len(entrees) == 2
    assert entrees[0]["source_id"] == SOURCE
    assert entrees[0]["key"] == "page=1"
    assert entrees[0]["content_sha256"] == fingerprint_bytes(b"premiere")
    assert entrees[0]["media_type"] == "application/json"
    assert entrees[0]["size"] == len(b"premiere")
    assert entrees[0]["acquired_at"] == "2026-10-31T12:00:00+00:00"
    assert entrees[1]["source_id"] == "usgs.nwis.iv"
    assert entrees[1]["media_type"] is None


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

    entree = magasin.read_manifest()[0]
    assert preuve.acquired_at == datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    assert entree["acquired_at"] == "2026-10-31T12:00:00+00:00"


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

    preuve = magasin.put(
        b"",
        source_id=SOURCE,
        key="page=1",
        media_type="application/json",
        acquired_at=_instant(),
    )

    assert preuve.evidence_id == fingerprint_bytes(b"")
    assert magasin.content_path(preuve.evidence_id).read_bytes() == b""
    assert magasin.read_manifest()[0]["size"] == 0


def test_un_manifeste_illisible_est_signale(tmp_path: Path):
    """Un manifeste abimé se voit : il n'est jamais ignoré en silence."""
    magasin = FileRawStore(tmp_path)
    magasin.manifest_path.write_text("ceci n'est pas du json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="manifeste illisible"):
        magasin.read_manifest()
