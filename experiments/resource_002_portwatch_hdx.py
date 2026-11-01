"""RESOURCE-002 (correction) — le CSV PortWatch de l'Espagne via HDX.

L'API ArcGIS de PortWatch refuse l'extraction terminale. Le **collecteur
public OCHA-DAP** republie en revanche les memes donnees sur le
Humanitarian Data Exchange, sous la forme :

    {country}-daily-port-activity-data-and-shipment-estimates.csv

Ce script verifie que la ressource **Espagne** existe, la telecharge, et
inspecte son schema : colonnes,periode couverte,terminaux presents, et ce
que le fichier porte reellement comme volumes.

Il ne deduit rien de plus que ce que le fichier contient.

Usage :

    uv run python experiments/resource_002_portwatch_hdx.py [repertoire_de_sortie]
"""

from __future__ import annotations

import csv
import io
import json
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HDX_API = "https://data.humdata.org/api/3/action/package_search"
HDX_TELECHARGEMENT = (
    "https://data.humdata.org/dataset/{paquet}/resource/{ressource}/download/{fichier}"
)

PAQUET = "2710946b-f547-47c3-adc4-c66458457905"
"""Le jeu HDX « Spain: Daily Port Activity Data and Shipment Estimates »."""

FICHIER = "spain-daily-port-activity-data-and-shipment-estimates.csv"

TERMINAUX_CIBLES = ("barcelona", "cartagena", "bilbao", "sagunto", "huelva", "mugardos")
"""Les six terminaux de l'echantillon LNG."""


def _contexte() -> ssl.SSLContext:
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _get(url: str, n: int = 40_000_000) -> tuple[int, bytes]:
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-resource-002"})
    try:
        with urllib.request.urlopen(demande, timeout=180, context=_contexte()) as reponse:
            return reponse.status, reponse.read(n)
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.read(600)
    except Exception as erreur:
        return 0, f"{type(erreur).__name__}: {erreur}".encode()


def main(argv: list[str]) -> int:
    """La ressource, telechargee et lue."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = (
        Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-resource-002-"))
    )
    sortie.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("1. la ressource HDX")
    status, corps = _get(f"{HDX_API}?q=spain+port+activity&rows=5")
    adresse = ""
    if status == 200:
        for paquet in json.loads(corps)["result"]["results"]:
            if "Spain" not in (paquet.get("title") or ""):
                continue
            print(f"   titre    : {paquet.get('title')}")
            print(f"   id       : {paquet.get('id')}")
            print(f"   modifie  : {paquet.get('metadata_modified')}")
            for ressource in paquet.get("resources") or []:
                print(f"   ressource: {ressource.get('name')}  ({ressource.get('size')} octets)")
                print(f"              {str(ressource.get('url'))[:130]}")
                if ressource.get("name") == FICHIER:
                    adresse = str(ressource.get("url"))
            break

    print()
    print("=" * 100)
    print("2. le telechargement")
    if not adresse:
        adresse = HDX_TELECHARGEMENT.format(
            paquet=PAQUET, ressource="91448984-7ab9-44cf-85a0-cbf20cf3f799", fichier=FICHIER
        )
    status, corps = _get(adresse)
    print(f"   HTTP {status} · {len(corps)} octets")
    if status != 200:
        print("   ", corps[:200])
        return 1
    chemin = sortie / FICHIER
    chemin.write_bytes(corps)

    print()
    print("=" * 100)
    print("3. le schema")
    texte = corps.decode("utf-8", errors="replace")
    lignes = list(csv.reader(io.StringIO(texte)))
    entete = lignes[0]
    print(f"   colonnes ({len(entete)}) :")
    for i, nom in enumerate(entete):
        print(f"      {i:>2} {nom}")

    index = {nom: i for i, nom in enumerate(entete)}
    date_i = next((i for n, i in index.items() if "date" in n.lower()), None)
    portid_i = next((i for n, i in index.items() if "portid" in n.lower()), None)
    nom_i = next((i for n, i in index.items() if n.lower() == "portname"), None)

    dates = [ligne[date_i] for ligne in lignes[1:] if len(ligne) > date_i and ligne[date_i]]
    ports = sorted({ligne[nom_i] for ligne in lignes[1:] if len(ligne) > nom_i and ligne[nom_i]})
    print()
    print(f"   lignes  : {len(lignes) - 1}")
    print(f"   periode : {min(dates)} -> {max(dates)}" if dates else "   periode : (vide)")
    print(f"   ports distincts : {len(ports)}")
    print("   terminaux de l'echantillon LNG :")
    for cible in TERMINAUX_CIBLES:
        trouves = [
            (ligne[nom_i], ligne[portid_i])
            for ligne in lignes[1:]
            if len(ligne) > nom_i and cible in str(ligne[nom_i]).lower()
        ]
        uniques = sorted(set(trouves))
        print(f"      {cible:<12} -> {uniques[:3] if uniques else 'ABSENT'}")

    print()
    print("   exemple de ligne :")
    print("      ", lignes[1][:16])

    print()
    print(f"   preuve : {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
