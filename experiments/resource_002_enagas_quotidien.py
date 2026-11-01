"""RESOURCE-002 (correction) — la granularite reelle du suivi quotidien Enagas.

Le bulletin mensuel donne des GWh par plante et par mois. Le **suivi
quotidien du Systeme** donne, **par jour de gaz et par terminal** : les
volumes decharges (en m3 de GNL), la regasification, les chargements de
citerne, et les existences en cuves — initiales, finales, et le
**pourcentage de remplissage**.

Ce script telecharge un jour donne et en extrait la feuille « Resumen ».
La lecture se fait avec la **bibliotheque standard** : le fichier est un
XLSX (un ZIP de XML), malgre son extension `.xls`.

Ce que l'on cherche ici, c'est la **granularite** : existe-t-il des
journees ou un seul methanier decharge dans un terminal donne ? C'est la
condition d'une validation par navire.

Usage :

    uv run python experiments/resource_002_enagas_quotidien.py [date] [sortie]
"""

from __future__ import annotations

import re
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

URL_JOUR = (
    "https://www.enagas.es/content/enagas/es/gestion-tecnica-sistema/energy-data"
    "/parametros-fisicos/capacidades-tecnicas-flujos-fisicos/seguimiento-diario-sistema"
    "/jcr:content/responsiveGrid/dailysystemtracking.dailysystemtrackingdto.xls?date={date}"
)

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

PLANTES = ("BARCELONA", "CARTAGENA", "HUELVA", "BBG", "SAGUNTO", "REGANOSA", "MUSEL")
"""Les sept terminaux du tableau du suivi quotidien."""


def _contexte() -> ssl.SSLContext:
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _telecharger(date: str, sortie: Path) -> Path:
    """Le rapport quotidien d'un jour de gaz."""
    url = URL_JOUR.format(date=date.replace("/", "%2F"))
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-resource-002"})
    with urllib.request.urlopen(demande, timeout=120, context=_contexte()) as reponse:
        corps = reponse.read()
    sortie.mkdir(parents=True, exist_ok=True)
    chemin = sortie / f"quotidien_{date.replace('/', '-')}.xlsx"
    chemin.write_bytes(corps)
    return chemin


def _feuilles(archive: zipfile.ZipFile) -> dict[str, str]:
    """Le nom de chaque feuille et le chemin de son XML."""
    classeur = ET.fromstring(archive.read("xl/workbook.xml"))
    relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    cibles = {
        element.get("Id"): element.get("Target")
        for element in relations.findall("pkg:Relationship", NS)
    }
    feuilles: dict[str, str] = {}
    for feuille in classeur.findall("main:sheets/main:sheet", NS):
        identifiant = feuille.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        cible = cibles.get(identifiant, "")
        if cible and not cible.startswith("xl/"):
            cible = f"xl/{cible.lstrip('/')}"
        feuilles[feuille.get("name")] = cible
    return feuilles


def _chaines(archive: zipfile.ZipFile) -> list[str]:
    """Les chaines partagees du classeur."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    racine = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(noeud.itertext()) for noeud in racine.findall("main:si", NS)]


def _cellules(archive: zipfile.ZipFile, chemin: str, partagees: list[str]) -> list[list[str]]:
    """Les cellules d'une feuille, ligne par ligne."""
    if not chemin or chemin not in archive.namelist():
        return []
    racine = ET.fromstring(archive.read(chemin))
    lignes: list[list[str]] = []
    for ligne in racine.findall("main:sheetData/main:row", NS):
        valeurs: list[str] = []
        for cellule in ligne.findall("main:c", NS):
            type_cellule = cellule.get("t")
            valeur = cellule.find("main:v", NS)
            if valeur is None:
                en_ligne = cellule.find("main:is", NS)
                valeurs.append("".join(en_ligne.itertext()) if en_ligne is not None else "")
                continue
            brut = valeur.text or ""
            if type_cellule == "s":
                index = int(brut)
                valeurs.append(partagees[index] if index < len(partagees) else brut)
            else:
                valeurs.append(brut)
        lignes.append(valeurs)
    return lignes


def main(argv: list[str]) -> int:
    """Un jour, lu."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    date = argv[1] if len(argv) > 1 else "12/09/2025"
    sortie = (
        Path(argv[2]) if len(argv) > 2 else Path(tempfile.mkdtemp(prefix="torne-resource-002-"))
    )
    chemin = _telecharger(date, sortie)
    print("=" * 100)
    print(f"SUIVI QUOTIDIEN DU SYSTEME — jour de gaz {date}")
    print(f"fichier : {chemin} ({chemin.stat().st_size} octets)")
    print()

    with zipfile.ZipFile(chemin) as archive:
        feuilles = _feuilles(archive)
        partagees = _chaines(archive)
        print(f"feuilles : {list(feuilles)}")
        lignes = _cellules(archive, feuilles.get("Resumen", ""), partagees)
        if not lignes:
            lignes = _cellules(archive, next(iter(feuilles.values()), ""), partagees)

    print()
    print("=" * 100)
    print("LES LIGNES QUI PORTENT LES GRANDEURS PHYSIQUES")
    for numero, ligne in enumerate(lignes):
        contenu = " ".join(ligne)
        if re.search(
            r"Descargas GNL|Regasificaci|Exist\.|% llenado|Cargas GNL|Carga Cisternas", contenu
        ):
            propre = [v for v in ligne if v not in ("", "Unnamed: 1")]
            print(f"   [{numero:>3}] {propre[:13]}")

    print()
    print("=" * 100)
    print("LES COLONNES : entete brute des premieres lignes")
    for numero, ligne in enumerate(lignes[:14]):
        print(f"   [{numero:>3}] {ligne[:14]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
