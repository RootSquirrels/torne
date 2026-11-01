"""ATMO-001 — la voie Météo-France, quand un jeton est disponible.

Ce script interroge l'API publique de Météo-France — le **point d'entrée
institutionnel** du périmètre atmosphère, celui que la sonde d'inventaire a
trouvé fermé à `401`. Il ne demande **aucun** identifiant à l'utilisateur :
il lit la clé d'API dans l'environnement, ou dans un fichier `.env` local **ignoré
par Git**, et rend compte de ce que la source a répondu.

Le secret ne quitte jamais ce script
------------------------------------

- la demande d'acquisition porte la **référence** ``meteofrance.apikey``, un
  nom — c'est ce qui est consigné dans le journal (INV-41) ;
- la valeur n'est lue qu'au moment de l'envoi, et n'est écrite nulle part ;
- si une redirection changeait d'origine, le transport retirerait l'en-tête
  d'authentification (INV-42).

Où poser la clé
-----------------

1. **Variable d'environnement** (recommandé) — rien n'entre dans le dépôt :

       setx METEOFRANCE_API_KEY "votre-cle"

2. **Fichier `.env` à la racine du dépôt** — committable *non*, il est ignoré
   par `.gitignore` (`.env` et `.env.*` y sont listés) :

       METEOFRANCE_API_KEY=votre-cle

Dans les deux cas, la clé n'est **pas** écrit dans le chat : un message de
conversation est conservé, et un secret collé dans un message est un secret
copié. La variable d'environnement gagne sur le fichier, dans tous les cas.

Usage :

    uv run python experiments/atmo_001_meteofrance.py [date_ISO]
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from torne.acquisition.adapters.meteofrance import (
    CHEMIN_PAQUET_6M,
    CHEMIN_STATIONS,
    CREDENTIAL_REF,
    KEY_HEADER,
    DailyClimatologyAdapter,
    MeteoFranceAdapter,
)
from torne.acquisition.contracts import AcquisitionOutcome
from torne.acquisition.credentials import FichierEnvToken
from torne.acquisition.fetcher import Fetcher
from torne.acquisition.store import FileRawStore
from torne.acquisition.transport import HttpTransport

VARIABLE = "METEOFRANCE_API_KEY"
"""Le nom de la variable d'environnement. Un nom, pas un secret."""

STATION_CLIMATO = "59343001"
"""Lille-Lesquin, in the climatological API's station register."""

RACINE = Path(__file__).resolve().parent.parent
"""La racine du dépôt — pour trouver le `.env` local, s'il existe."""

JOUR_PAR_DEFAUT = "2026-10-01"
"""La date du paquet 6 minutes, sans importance tant qu'aucun jeton n'est là."""


def _racine() -> Path:
    """La racine du dépôt."""
    return Path(__file__).resolve().parent.parent


def _fournisseur() -> FichierEnvToken:
    """Le fournisseur de secret : environnement d'abord, `.env` ensuite."""
    return FichierEnvToken(
        CREDENTIAL_REF,
        variable=VARIABLE,
        chemin=_racine() / ".env",
        header=KEY_HEADER,
        scheme="",
    )


def _fetcher(magasin: FileRawStore) -> Fetcher:
    """Le fetcher du socle, avec son fournisseur de secret."""
    return Fetcher(
        transport=HttpTransport(timeout=60.0),
        store=magasin,
        credentials=_fournisseur(),
    )


def _acquer(fetcher: Fetcher, adaptateur: MeteoFranceAdapter, quoi: str) -> AcquisitionOutcome:
    """Une acquisition, et sa porte."""
    issue = fetcher.acquire(adaptateur)
    etat = issue.conformite.value if issue.verdict_conformite else "aucun verdict"
    print(f"  {quoi} : {issue.status.value}, {issue.page_count} page(s), conformité {etat}")
    if issue.verdict_conformite and issue.verdict_conformite.motif:
        print(f"    motif : {issue.verdict_conformite.motif}")
    for critere in issue.verdict_conformite.criteres.values() if issue.verdict_conformite else []:
        marque = (
            "conforme"
            if critere.conforme
            else ("non vérifiable" if not critere.verifie else "violé")
        )
        print(f"    [{marque}] {critere.demande} → {critere.recu}")
    return issue


def main(argv: list[str]) -> int:
    """La voie Météo-France, et ce qu'elle rend — ou ce qu'elle refuse."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    jour = argv[1] if len(argv) > 1 else JOUR_PAR_DEFAUT
    racine = Path(tempfile.mkdtemp(prefix="torne-atmo-001-mf-"))
    print(f"preuve brute : {racine}")
    magasin = FileRawStore(racine)
    fetcher = _fetcher(magasin)

    fournisseur = _fournisseur()
    tete = fournisseur.credentials_for(CREDENTIAL_REF)
    if tete:
        print(f"jeton : présent (variable {VARIABLE}), jamais écrit")
    else:
        print(
            f"jeton : ABSENT — ni la variable {VARIABLE}, ni .env à la racine.\n"
            "        La source va le dire elle-même ; c'est le comportement attendu."
        )

    print("\n1. le référentiel des stations")
    issue_stations = _acquer(
        fetcher,
        MeteoFranceAdapter(chemin=CHEMIN_STATIONS, label="meteofrance:stations"),
        "liste des stations",
    )

    print(f"\n2. le paquet infra-horaire 6 min du {jour}")
    issue_paquet = _acquer(
        fetcher,
        MeteoFranceAdapter(
            chemin=CHEMIN_PAQUET_6M,
            params={"date": f"{jour}T18:00:00Z", "format": "geojson"},
            label="meteofrance:paquet-6m",
        ),
        "paquet 6 min",
    )

    print(f"\n3. the daily series of station {STATION_CLIMATO} (climatological API)")
    issue_climatology = _acquer(
        fetcher,
        DailyClimatologyAdapter(
            station=STATION_CLIMATO,
            start=f"{jour[:7]}-01T00:00:00Z",
            end=f"{jour}T00:00:00Z",
        ),
        "daily series",
    )
    if issue_climatology.evidence:
        piece = issue_climatology.evidence[-1]
        texte = magasin.content_path(piece.evidence_id).read_text(encoding="utf-8")
        lignes = [ligne for ligne in texte.splitlines() if ligne.strip()]
        print(f"  file: {max(len(lignes) - 1, 0)} data row(s) ({piece.media_type})")

    exploitable = issue_stations.exploitable and issue_paquet.exploitable
    if issue_climatology.exploitable:
        print("\nThe climatological route delivered: raw evidence kept, conformity established.")
    if not exploitable:
        print()
        print("The observation API (DPPaquetObs) did not deliver: nothing is interpreted.")
        print("It refuses the key (401/403): the key opens the climatological API; observation")
        print(f"belongs to another subscription. ({VARIABLE})")
    else:
        _decrire(issue_stations, issue_paquet, magasin)

    print(f"\npreuve brute : {racine}")
    print(f"journal : {racine}")
    return 0


def _decrire(
    issue_stations: AcquisitionOutcome,
    issue_paquet: AcquisitionOutcome,
    magasin: FileRawStore,
) -> None:
    """Ce que les deux réponses portent, une fois le jeton passé.

    Le contenu est relu **depuis la preuve conservée**, jamais depuis la
    mémoire de l'appel : c'est la règle du dépôt, et c'est ce qui permet de
    rejouer l'analyse sur les octets reçus.
    """
    for issue, quoi in ((issue_stations, "stations"), (issue_paquet, "paquet")):
        if not issue.evidence:
            continue
        piece = issue.evidence[0]
        print(f"\n{quoi} : {piece.evidence_id[:16]}… ({piece.media_type})")
        print(f"  empreinte : {str(piece.content_sha256)[:16]}…")
        texte = magasin.content_path(piece.evidence_id).read_text(encoding="utf-8")
        try:
            charge = json.loads(texte)
        except json.JSONDecodeError:
            print(f"  {len(texte)} octets, illisibles comme du JSON")
            continue
        if isinstance(charge, dict):
            cles = sorted(charge)
            print(f"  clés de premier niveau : {', '.join(cles[:8])}")
            entites = charge.get("features")
            if isinstance(entites, list):
                print(f"  entités : {len(entites)}")
            stations = charge.get("stations")
            if isinstance(stations, list):
                print(f"  stations : {len(stations)}")
        else:
            print(f"  {len(texte)} octets, tableau de {len(charge)} éléments")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
