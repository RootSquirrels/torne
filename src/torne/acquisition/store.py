"""Le magasin brut — la preuve brute, conservée telle qu'elle a été reçue.

Ce module tient une seule promesse : **ce qui a été reçu est conservé, et
l'on peut dire ce qui a été reçu, quand, et par quelle question**.

Le magasin est **adressé par le contenu**. Les octets d'une réponse sont
écrits sous un chemin dérivé de leur empreinte
(`<racine>/ab/cdef0123...`) : deux acquisitions du même contenu partagent le
même fichier, et un contenu n'est jamais réécrit (INV-01). Une version
nouvelle d'une même clé crée un fichier nouveau, et laisse l'ancien intact
(INV-02).

Le **manifeste** est un journal *append-only* : une ligne JSON par
acquisition, jamais modifiée, jamais réordonnée. Il porte la source, la clé,
l'empreinte, le type déclaré, l'instant d'acquisition (normalisé en UTC) et
la taille. La clé est le lien vers la demande : c'est par elle qu'on retrouve
la requête qui a produit la preuve (INV-03).

L'écriture des octets est **atomique** : le contenu passe par un fichier
temporaire, puis est renommé. Un fichier écrit à moitié ne laisse donc
jamais de trace exploitable : soit le contenu est complet sous son
empreinte, soit il n'y a rien.

Ce module ne connaît aucun domaine, et ne fait aucun réseau : il ne sait
qu'écrire, lire et nommer.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..contracts.fingerprint import fingerprint_bytes
from ..contracts.observation import RawEvidence
from ..contracts.time import to_utc

NOM_MANIFESTE = "manifeste.jsonl"
"""Nom du journal d'acquisition, à la racine du magasin."""


@runtime_checkable
class RawStore(Protocol):
    """Le contrat du magasin brut : écrire des octets, rendre une preuve.

    La forme de `put` est celle dont le fetcher a besoin : le contenu brut
    d'une réponse, et les quatre informations qui font d'une écriture une
    **acquisition** — la source, la clé, le type déclaré et l'instant.
    """

    def put(
        self,
        payload: bytes,
        *,
        source_id: str,
        key: str,
        media_type: str | None,
        acquired_at: datetime,
    ) -> RawEvidence:
        """Conserve `payload` et rend la preuve brute correspondante.

        L'empreinte du contenu brut est l'`evidence_id` rendu : c'est elle
        qui relie une observation à la preuve qui l'a produite (INV-25).
        """
        ...


class FileRawStore:
    """Un magasin brut sur disque, adressé par le contenu.

    Disposition sous la racine :

    - `<racine>/ab/cdef0123...` : les octets bruts, un fichier par empreinte ;
    - `<racine>/manifeste.jsonl` : le journal d'acquisition, append-only.

    Une même empreinte est toujours écrite au même endroit : le chemin se
    déduit de l'empreinte seule, sans index à tenir à jour.
    """

    def __init__(self, root: Path | str, *, manifest_name: str = NOM_MANIFESTE) -> None:
        self._racine = Path(root)
        self._nom_manifeste = manifest_name

    @property
    def root(self) -> Path:
        """La racine du magasin."""
        return self._racine

    @property
    def manifest_path(self) -> Path:
        """Le chemin du journal d'acquisition."""
        return self._racine / self._nom_manifeste

    def content_path(self, evidence_id: str) -> Path:
        """Le chemin du fichier qui porte le contenu de `evidence_id`.

        Le chemin est *déduit* de l'empreinte : il n'est pas indexé, il est
        calculé. Un fichier absent signifie que ce contenu n'a jamais été
        acquis.
        """
        return self._chemin_contenu(evidence_id)

    def put(
        self,
        payload: bytes,
        *,
        source_id: str,
        key: str,
        media_type: str | None,
        acquired_at: datetime,
    ) -> RawEvidence:
        """Conserve `payload` et rend la preuve brute correspondante.

        L'opération est **idempotente** : même contenu, même source, même
        clé ne produisent qu'une seule ligne de manifeste et un seul
        fichier. Le contenu n'est jamais réécrit : s'il est déjà là, il y
        reste, intact.

        L'instant est refusé s'il est naïf (INV-15), et le refus vient
        **avant** toute écriture : une acquisition refusée ne laisse rien
        derrière elle.
        """
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError("le contenu brut doit être une suite d'octets")
        if not isinstance(acquired_at, datetime):
            raise TypeError("l'instant d'acquisition doit être un instant")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id est obligatoire et non vide")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key est obligatoire et non vide")

        instant = to_utc(acquired_at, name="acquired_at")
        donnees = bytes(payload)
        empreinte = fingerprint_bytes(donnees)

        chemin = self._chemin_contenu(empreinte)
        if not chemin.exists():
            _ecrire_atomique(chemin, donnees)

        if not self._deja_consigne(source_id=source_id, key=key, empreinte=empreinte):
            self._ajouter_au_manifeste(
                {
                    "acquired_at": instant.isoformat(),
                    "blob": f"{empreinte[:2]}/{empreinte}",
                    "content_sha256": empreinte,
                    "key": key,
                    "media_type": media_type,
                    "size": len(donnees),
                    "source_id": source_id,
                }
            )

        return RawEvidence(
            evidence_id=empreinte,
            source_id=source_id,
            acquired_at=instant,
            media_type=media_type,
            content_sha256=empreinte,
            key=key,
        )

    def read_manifest(self) -> list[dict[str, object]]:
        """Relit le journal d'acquisition, dans l'ordre des écritures.

        Le journal est relu depuis le disque, à chaque fois : le magasin ne
        tient aucun index en mémoire, et deux processus qui acquisitions sur
        la même racine voient le même journal.

        Une ligne illisible est **signalée**, jamais ignorée en silence :
        un manifeste abimé se voit.
        """
        chemin = self.manifest_path
        if not chemin.exists():
            return []
        entrees: list[dict[str, object]] = []
        with open(chemin, encoding="utf-8") as flux:
            for numero, ligne in enumerate(flux, start=1):
                texte = ligne.strip()
                if not texte:
                    continue
                try:
                    entree = json.loads(texte)
                except json.JSONDecodeError as erreur:
                    raise ValueError(
                        f"manifeste illisible : ligne {numero} n'est pas du JSON ({erreur})"
                    ) from erreur
                if not isinstance(entree, dict):
                    raise ValueError(f"manifeste illisible : ligne {numero} n'est pas un objet")
                entrees.append(entree)
        return entrees

    def _chemin_contenu(self, empreinte: str) -> Path:
        """Le chemin du fichier de contenu, dérivé de l'empreinte."""
        return self._racine / empreinte[:2] / empreinte

    def _deja_consigne(self, *, source_id: str, key: str, empreinte: str) -> bool:
        """Cette acquisition (source, clé, contenu) est-elle déjà journalisée ?"""
        for entree in self.read_manifest():
            if (
                entree.get("source_id") == source_id
                and entree.get("key") == key
                and entree.get("content_sha256") == empreinte
            ):
                return True
        return False

    def _ajouter_au_manifeste(self, entree: dict[str, object]) -> None:
        """Ajoute une ligne au journal, sans jamais modifier ce qui existe."""
        chemin = self.manifest_path
        chemin.parent.mkdir(parents=True, exist_ok=True)
        ligne = json.dumps(entree, ensure_ascii=False, sort_keys=True) + "\n"
        with open(chemin, "a", encoding="utf-8", newline="\n") as flux:
            flux.write(ligne)
            flux.flush()
            os.fsync(flux.fileno())


def _ecrire_atomique(chemin: Path, donnees: bytes) -> None:
    """Écrit `donnees` dans `chemin` sans jamais laisser de trace partielle.

    Le contenu est d'abord écrit dans un fichier temporaire **du même
    répertoire** — donc sur le même système de fichiers — puis renommé à
    destination. Le renommage est atomique : le contenu n'apparaît à sa
    place finale que complet.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    descripteur, nom_temporaire = tempfile.mkstemp(
        dir=str(chemin.parent), prefix=".tmp-", suffix=".part"
    )
    try:
        with os.fdopen(descripteur, "wb") as flux:
            flux.write(donnees)
            flux.flush()
            os.fsync(flux.fileno())
        os.replace(nom_temporaire, chemin)
    except BaseException:
        Path(nom_temporaire).unlink(missing_ok=True)
        raise


__all__ = ["NOM_MANIFESTE", "FileRawStore", "RawStore"]
