"""Le magasin brut — la preuve brute, conservée telle qu'elle a été reçue.

Ce module tient deux promesses distinctes, et la revue a montré qu'il n'en
tenait qu'une.

1. **Le contenu brut est conservé tel quel.** Les octets d'une réponse sont
   écrits sous un chemin dérivé de leur empreinte (`<racine>/ab/cdef0123...`) :
   deux acquisitions du même contenu partagent le même fichier, et un contenu
   n'est jamais réécrit (INV-01).
2. **L'événement d'acquisition est conservé à chaque récupération.** Ce qui
   est dédupliqué, c'est le *contenu* ; ce qui ne l'est pas, c'est
   l'*acquisition*. Si TORNE récupère la même valeur chaque jour pendant six
   mois, le fichier brut peut rester unique — mais les six mois
   d'acquisitions, eux, doivent rester traçables.

Trois niveaux, à ne pas confondre :

| Niveau | Ce que c'est | Écrit par |
|---|---|---|
| le contenu | les octets reçus, adressés par empreinte | `put()` |
| l'événement d'acquisition | une ligne de journal par récupération | `record()` |
| la tentative | un appel au fournisseur, réussi ou non | `record()` |

**L'instant de première conservation.** L'identité d'un contenu est son
empreinte ; sa date de connaissance est la **première fois qu'il a été vu**.
Récupérer le même contenu plus tard ne le rend pas plus récent : le second
`put` rend donc le même `acquired_at` que le premier, et c'est cet instant —
le `known_at` du contenu — que le journal porte. L'**événement
d'acquisition**, lui, porte l'instant de *cette* récupération. Les deux ne se
confondent jamais.

Le journal est **append-only** : une ligne JSON par acquisition, jamais
modifiée, jamais réordonnée. Il est rejouable (`read_manifest()`), et c'est
lui qui permet de relire ce qui a été demandé, ce qui a été reçu, et ce qui
a échoué (INV-03).

L'index des instants de première conservation est **en mémoire** : il est
reconstruit une fois depuis le journal, puis tenu à jour. Un seul fichier sur
le disque : aucun index séparé.

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
from .contracts import AcquisitionOutcome

NOM_MANIFESTE = "manifeste.jsonl"
"""Nom du journal d'acquisition, à la racine du magasin."""


@runtime_checkable
class RawStore(Protocol):
    """Le contrat du magasin brut : garder des octets, journaliser une acquisition.

    Deux méthodes, deux responsabilités : `put` garde le **contenu**,
    `record` garde l'**événement**. La distinction est celle de la revue —
    un contenu se déduplique par empreinte, une acquisition jamais.
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

        L'instant rendu est l'instant de **première conservation** du
        contenu : le récupérer plus tard ne le change pas.
        """
        ...

    def record(self, outcome: AcquisitionOutcome) -> None:
        """Conserve l'événement d'acquisition : le journal, append-only."""
        ...


class FileRawStore:
    """Un magasin brut sur disque, adressé par le contenu.

    Disposition sous la racine :

    - `<racine>/ab/cdef0123...` : les octets bruts, un fichier par empreinte ;
    - `<racine>/manifeste.jsonl` : le journal d'acquisition, append-only.

    Une même empreinte est toujours écrite au même endroit : le chemin se
    déduit de l'empreinte seule, sans index à tenir à jour.

    L'index des instants de première conservation vit **en mémoire** : il est
    rechargé une fois depuis le journal, puis tenu à jour. Aucun second
    fichier n'est écrit sur le disque.
    """

    def __init__(self, root: Path | str, *, manifest_name: str = NOM_MANIFESTE) -> None:
        self._racine = Path(root)
        self._nom_manifeste = manifest_name
        self._index: dict[str, datetime] | None = None

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

        Le **contenu** est dédupliqué par empreinte : même contenu, même
        fichier, jamais réécrit. L'**acquisition**, elle, ne l'est pas : c'est
        `record()` qui la consigne, une ligne par récupération.

        L'instant rendu est l'instant de **première conservation** de ce
        contenu — son `known_at`. Le premier `put` d'un contenu inconnu rend
        l'instant courant ; les suivants rendent l'instant du premier, car
        récupérer un contenu déjà connu ne le rend pas plus récent.

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

        return RawEvidence(
            evidence_id=empreinte,
            source_id=source_id,
            acquired_at=self._instant_de_premiere_conservation(empreinte, instant),
            media_type=media_type,
            content_sha256=empreinte,
            key=key,
        )

    def record(self, outcome: AcquisitionOutcome) -> None:
        """Conserve l'événement d'acquisition : une ligne de journal, jamais deux.

        L'événement porte l'instant de l'acquisition, la source, la clé, la
        demande, le statut, l'exhaustivité, l'erreur éventuelle, **toutes**
        les tentatives — y compris celles qui ont échoué — et la liste des
        empreintes des pages acquises.

        Rien n'est dédupliqué : deux acquisitions du même contenu donnent deux
        lignes. C'est ce qui rend traçable une série d'acquisitions
        identiques.

        L'instant porté par chaque page est celui de la **première
        conservation** de son contenu, pas celui de cette récupération : le
        magasin est l'autorité de cette date. À défaut de la connaître — une
        preuve qui n'est pas passée par ce magasin — l'instant de la preuve
        est repris tel quel.
        """
        if not isinstance(outcome, AcquisitionOutcome):
            raise TypeError("l'issue d'acquisition doit être une AcquisitionOutcome")

        index = self._charger_index()
        pages: list[dict[str, object]] = []
        empreintes: list[str] = []
        for piece in outcome.evidence:
            empreinte = piece.content_sha256 or piece.evidence_id
            connu = index.get(empreinte)
            if connu is None:
                connu = piece.acquired_at
                index[empreinte] = connu
            pages.append(
                {
                    "evidence_id": piece.evidence_id,
                    "content_sha256": empreinte,
                    "known_at": connu.isoformat(),
                    "acquired_at": connu.isoformat(),
                    "key": piece.key,
                    "media_type": piece.media_type,
                    "size": self._taille_du_contenu(empreinte),
                }
            )
            empreintes.append(empreinte)

        evenement = outcome.as_dict()
        evenement.pop("evidence", None)
        evenement["event"] = "acquisition"
        evenement["request_id"] = _identifiant_demande(outcome)
        evenement["acquired_at"] = outcome.finished_at.isoformat()
        evenement["key"] = outcome.request.label or outcome.request.url
        evenement["pages"] = pages
        evenement["content_sha256"] = empreintes
        evenement["size"] = sum(int(page["size"] or 0) for page in pages)
        evenement["media_type"] = _type_commun(pages)

        self._ajouter_au_manifeste(evenement)

    def read_manifest(self) -> list[dict[str, object]]:
        """Relit le journal d'acquisition, dans l'ordre des écritures.

        Le journal est relu depuis le disque, à chaque fois : le magasin ne
        tient en mémoire que l'index des instants de première conservation,
        et deux processus qui acquièrent sur la même racine voient le même
        journal.

        Une ligne illisible est **signalée**, jamais ignorée en silence :
        un manifeste abimé se voit.
        """
        entrees = self._lire_le_journal()
        if self._index is not None:
            for entree in entrees:
                _absorber_evenement(self._index, entree)
        return entrees

    def _chemin_contenu(self, empreinte: str) -> Path:
        """Le chemin du fichier de contenu, dérivé de l'empreinte."""
        return self._racine / empreinte[:2] / empreinte

    def _instant_de_premiere_conservation(self, empreinte: str, instant: datetime) -> datetime:
        """L'instant de première conservation de ce contenu.

        C'est son `known_at` : l'identité du contenu est son empreinte, sa
        date de connaissance est la première fois qu'il a été vu. Reprendre
        le même contenu plus tard ne le rend pas plus récent.
        """
        index = self._charger_index()
        connu = index.get(empreinte)
        if connu is None:
            index[empreinte] = instant
            return instant
        return connu

    def _charger_index(self) -> dict[str, datetime]:
        """L'index des instants de première conservation, chargé une fois.

        Il est reconstruit depuis le journal — le seul fichier du magasin —
        puis tenu à jour en mémoire. Le relire à chaque écriture serait hors
        de prix : un journal de six mois se relit une fois, pas à chaque
        page.
        """
        if self._index is None:
            index: dict[str, datetime] = {}
            self._index = index
            for entree in self._lire_le_journal():
                _absorber_evenement(index, entree)
        return self._index

    def _taille_du_contenu(self, empreinte: str) -> int | None:
        """La taille du contenu conservé, si le fichier est là."""
        try:
            return self._chemin_contenu(empreinte).stat().st_size
        except OSError:
            return None

    def _lire_le_journal(self) -> list[dict[str, object]]:
        """Les lignes du journal, lues depuis le disque."""
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

    def _ajouter_au_manifeste(self, entree: dict[str, object]) -> None:
        """Ajoute une ligne au journal, sans jamais modifier ce qui existe."""
        chemin = self.manifest_path
        chemin.parent.mkdir(parents=True, exist_ok=True)
        ligne = json.dumps(entree, ensure_ascii=False, sort_keys=True) + "\n"
        with open(chemin, "a", encoding="utf-8", newline="\n") as flux:
            flux.write(ligne)
            flux.flush()
            os.fsync(flux.fileno())


def _absorber_evenement(index: dict[str, datetime], entree: dict[str, object]) -> None:
    """Inscrit dans l'index les contenus d'un événement relu du journal.

    Seul le **premier** passage d'un contenu compte : c'est lui qui porte
    l'instant de première conservation.
    """
    pages = entree.get("pages")
    if not isinstance(pages, list):
        return
    for page in pages:
        if not isinstance(page, dict):
            continue
        empreinte = page.get("content_sha256")
        instant = page.get("known_at")
        if not isinstance(empreinte, str) or not isinstance(instant, str):
            continue
        if empreinte in index:
            continue
        try:
            index[empreinte] = to_utc(datetime.fromisoformat(instant), name="known_at")
        except ValueError:
            continue


def _identifiant_demande(outcome: AcquisitionOutcome) -> str:
    """Un identifiant déterministe de l'acquisition, rejouable.

    Il est dérivé de ce qui identifie l'acquisition — source, question,
    instants, statut, empreintes acquises — et non d'un compteur ou d'un
    aléa : rejouer la même acquisition redonne le même identifiant, et deux
    acquisitions distinctes ne peuvent pas le partager.
    """
    elements = "|".join(
        [
            outcome.request.source_id,
            outcome.request.label or outcome.request.url,
            outcome.started_at.isoformat(),
            outcome.finished_at.isoformat(),
            outcome.status.value,
            outcome.exhaustiveness.value,
            ",".join(piece.content_sha256 or "" for piece in outcome.evidence),
        ]
    )
    return f"acq-{fingerprint_bytes(elements.encode('utf-8'))[:16]}"


def _type_commun(pages: list[dict[str, object]]) -> str | None:
    """Le type déclaré, quand toutes les pages acquises le portent.

    Une acquisition sans page n'a pas de type ; une acquisition dont les
    pages diffèrent n'en a pas davantage : le détail est dans les pages.
    """
    types = {page.get("media_type") for page in pages}
    if len(types) != 1:
        return None
    seul = types.pop()
    return seul if isinstance(seul, str) else None


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
