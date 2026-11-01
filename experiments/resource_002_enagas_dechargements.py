"""RESOURCE-002 (correction) — combien de dechargements « un seul navire » par terminal ?

Le suivi quotidien d'Enagas donne, par jour de gaz et par terminal, les
**m3 de GNL decharges**. Une journee ou **un seul** terminal enregistre un
dechargement, et ou ce dechargement est d'un ordre de grandeur compatible
avec un seul methanier, est une journee ou la validation **par navire** est
possible.

Ce script telecharge un mois entier de rapports quotidiens, en extrait la
matrice `Descargas GNL` (m3) par terminal et par jour, et compte :

- les **terminals-jours avec dechargement** ;
- les **dechargements uniques** — un seul terminal decharge dans la journee ;
- la distribution des volumes, pour dire si un dechargement correspond a un
  methanier ou a plusieurs.

Usage :

    uv run python experiments/resource_002_enagas_dechargements.py [AAAA-MM] [sortie]
"""

from __future__ import annotations

import datetime
import ssl
import sys
import tempfile
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
"""Les sept terminaux, dans l'ordre des colonnes du rapport."""

VOLUME_UN_METANIER = (40_000.0, 90_000.0)
"""L'ordre de grandeur du volume d'un dechargement de methanier, en m3.

Bornes **indicatives** : une cargaison de 174 000 m3 a 85 % de remplissage
 represente environ 67 500 t, soit environ 148 000 m3 de GNL a 0 C. La
 borne basse couvre les navires plus petits ou les dechargements partiels.
"""


def _contexte() -> ssl.SSLContext:
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _contenu(date: str) -> bytes:
    """Le rapport quotidien brut."""
    url = URL_JOUR.format(date=date.replace("/", "%2F"))
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-resource-002"})
    with urllib.request.urlopen(demande, timeout=120, context=_contexte()) as reponse:
        return reponse.read()


def _lignes(corps: bytes) -> list[list[str]]:
    """Les cellules de la feuille « Resumen »."""
    import io

    with zipfile.ZipFile(io.BytesIO(corps)) as archive:
        classeur = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        cibles = {
            element.get("Id"): element.get("Target")
            for element in relations.findall("pkg:Relationship", NS)
        }
        chemin = ""
        for feuille in classeur.findall("main:sheets/main:sheet", NS):
            identifiant = feuille.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            if feuille.get("name") == "Resumen":
                cible = cibles.get(identifiant, "")
                chemin = cible if cible.startswith("xl/") else f"xl/{cible.lstrip('/')}"
        if not chemin:
            return []
        partagees: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            racine = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            partagees = ["".join(n.itertext()) for n in racine.findall("main:si", NS)]
        racine = ET.fromstring(archive.read(chemin))
        resultat: list[list[str]] = []
        for ligne in racine.findall("main:sheetData/main:row", NS):
            valeurs: list[str] = []
            for cellule in ligne.findall("main:c", NS):
                valeur = cellule.find("main:v", NS)
                if valeur is None:
                    valeurs.append("")
                    continue
                brut = valeur.text or ""
                if cellule.get("t") == "s":
                    index = int(brut)
                    valeurs.append(partagees[index] if index < len(partagees) else brut)
                else:
                    valeurs.append(brut)
            resultat.append(valeurs)
        return resultat


def _dechargements(lignes: list[list[str]]) -> dict[str, float]:
    """Les m3 decharges, par terminal, pour un jour.

    La mise en page du rapport a change entre 2025 et 2026 : le libelle est
    passe de la colonne 0 a la colonne 1, et les valeurs ont ete decalees.
    On ne suppose donc **aucune** colonne fixe : on lit la ligne d'en-tete
    qui porte les noms des plantes, et on s'y indexe.
    """
    colonnes: dict[str, int] = {}
    for ligne in lignes:
        trouves = {
            str(valeur).strip().upper(): position
            for position, valeur in enumerate(ligne)
            if str(valeur).strip().upper() in PLANTES
        }
        if len(trouves) >= 3:
            colonnes = trouves
            break
    if not colonnes:
        return {}
    for ligne in lignes:
        if not any(str(valeur).strip() == "Descargas GNL" for valeur in ligne):
            continue
        resultat: dict[str, float] = {}
        for plante, position in colonnes.items():
            brut = ligne[position] if position < len(ligne) else "0"
            try:
                resultat[plante] = float(brut or 0)
            except ValueError:
                resultat[plante] = 0.0
        return resultat
    return {}


def main(argv: list[str]) -> int:
    """Un mois de dechargements."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mois = argv[1] if len(argv) > 1 else "2026-06"
    sortie = (
        Path(argv[2]) if len(argv) > 2 else Path(tempfile.mkdtemp(prefix="torne-resource-002-"))
    )
    sortie.mkdir(parents=True, exist_ok=True)

    annee, mois_num = (int(x) for x in mois.split("-"))
    premier = datetime.date(annee, mois_num, 1)
    nombre_jours = (
        datetime.date(annee + (mois_num == 12), 1 if mois_num == 12 else mois_num + 1, 1) - premier
    ).days

    print("=" * 100)
    print(f"LES DECHARGEMENTS DE GNL — {mois} ({nombre_jours} jours de gaz)")
    print()

    matrice: dict[str, dict[str, float]] = {}
    echecs = 0
    for jour in range(nombre_jours):
        date = premier + datetime.timedelta(days=jour)
        etiquette = date.strftime("%d/%m/%Y")
        try:
            corps = _contenu(etiquette)
        except Exception as erreur:
            echecs += 1
            print(f"   {etiquette} : ECHEC {type(erreur).__name__}")
            continue
        (sortie / f"quotidien_{date.isoformat()}.xlsx").write_bytes(corps)
        lignes = _lignes(corps)
        valeurs = _dechargements(lignes)
        if not valeurs:
            echecs += 1
            continue
        matrice[etiquette] = valeurs
        if jour < 3:
            nonzero = {k: v for k, v in valeurs.items() if v > 0}
            print(f"   {etiquette} : {nonzero if nonzero else 'aucun dechargement'}")

    print()
    print("=" * 100)
    print("1. LES JOURNEES AVEC DECHARGEMENT")
    par_jour = []
    for etiquette, valeurs in sorted(matrice.items()):
        actifs = {k: v for k, v in valeurs.items() if v > 0}
        if actifs:
            par_jour.append((etiquette, actifs))
    print(f"   jours avec au moins un dechargement : {len(par_jour)} / {len(matrice)}")
    uniques = [(j, a) for j, a in par_jour if len(a) == 1]
    print(f"   jours a DECHARGEMENT UNIQUE (un seul terminal) : {len(uniques)}")
    print()
    for etiquette, actifs in par_jour:
        marque = "  <<< un seul navire" if len(actifs) == 1 else ""
        print(
            f"   {etiquette} : "
            + " | ".join(f"{k} {v:,.0f} m3" for k, v in actifs.items())
            + marque
        )

    print()
    print("=" * 100)
    print("2. LA TAILLE DES DECHARGEMENTS")
    volumes = [v for _, actifs in par_jour for v in actifs.values()]
    if volumes:
        volumes_tries = sorted(volumes)
        print(f"   dechargements : {len(volumes)}")
        print(f"   volume min : {volumes_tries[0]:,.0f} m3")
        print(f"   volume median : {volumes_tries[len(volumes_tries) // 2]:,.0f} m3")
        print(f"   volume max : {volumes_tries[-1]:,.0f} m3")
        dans = [v for v in volumes if VOLUME_UN_METANIER[0] <= v <= VOLUME_UN_METANIER[1]]
        print(
            f"   dans la fourchette d'un seul methanier ({VOLUME_UN_METANIER[0]:,.0f} - "
            f"{VOLUME_UN_METANIER[1]:,.0f} m3) : {len(dans)} / {len(volumes)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
