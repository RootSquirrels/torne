"""MARINE-001 — l'atlas des stations NOAA/NDBC : qui mesure quoi, et où.

La question posée à une source n'est pas « la source répond-elle ? » mais
« **qu'est-ce qu'elle permet d'observer, et où ?** ». NOAA/NDBC répond à la
première question par un simple oui. C'est la seconde qui décide de la
mission : une archive océanographique ouverte n'est exploitable que si elle
porte la grandeur cherchée, sur la zone cherchée.

Ce script répond donc à cette question **par l'exécution**, sur deux
fichiers que NDBC sert sans secret :

- `activestations.xml` — le **référentiel des stations actives** : position,
  type, et **les grandeurs que chaque station rapporte**. Ce n'est pas une
  carte de ce qui *pourrait* être mesuré, mais de ce qui l'est.

- `data/historical/ocean/` — l'**index des archives océanographiques** : les
  stations qui ont un historique de salinité, de turbidité, d'oxygène.

Les deux sont croisés. Le résultat est une **carte de capacité** : où se
trouve la salinité mesurée en Europe, et où elle ne se trouve pas.

Usage :

    uv run python experiments/marine_001_atlas_stations.py [répertoire_de_sortie]
"""

from __future__ import annotations

import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from torne.acquisition import AcquisitionRequest, FileRawStore, HttpTransport

REGISTRE_URL = "https://www.ndbc.noaa.gov/activestations.xml"
INDEX_OCEAN_URL = "https://www.ndbc.noaa.gov/data/historical/ocean/"

ATLANTIQUE_NE = (43.0, 52.0, -20.0, 0.0)
"""Le carré qui borne l'Atlantique Nord-Est (Gironde → mer du Nord).

Latitude 43-52 °N, longitude 20 °O-0 °E. C'est la zone où se pose la
question de la mission - et c'est la seule que la comparaison avec les
archives américaines rend comparable.
"""

GRANDEURS = ("met", "currents", "waterquality", "dart")
"""Les capacités déclarées par le référentiel, telles qu'il les nomme."""


def _telecharger(transport: HttpTransport, magasin: FileRawStore, cle: str, url: str) -> bytes:
    """Le corps de la réponse, et sa preuve brute."""
    demande = AcquisitionRequest(
        source_id="noaa.ndbc",
        url=url,
        method="GET",
        label=f"marine-001:atlas:{cle}",
    )
    reponse = transport.send(demande)
    if reponse.status_code != 200 or not reponse.body:
        raise SystemExit(f"{cle} : HTTP {reponse.status_code} — l'atlas ne peut pas être établi")
    magasin.put(
        reponse.body,
        source_id="noaa.ndbc",
        key=f"{cle}#atlas",
        media_type=reponse.content_type,
        acquired_at=datetime.now(UTC),
    )
    return reponse.body


def _stations(corps: bytes) -> list[dict[str, str]]:
    """Les stations du référentiel, comme éléments XML."""
    racine = ET.fromstring(corps)
    return [dict(element.attrib) for element in racine.findall("station")]


def _stations_archive(corps: bytes) -> set[str]:
    """Les identifiants de station cités par l'index des archives."""
    texte = corps.decode("utf-8", errors="replace")
    trouves = re.findall(r'href="([^"]*?o\d{4}\.txt\.gz)"', texte)
    return {
        nom[: -len("o0000.txt.gz")]
        if nom.endswith("o0000.txt.gz")
        else re.sub(r"o\d{4}\.txt\.gz$", "", nom)
        for nom in trouves
    }


def _dans_le_carre(station: dict[str, str], carre: tuple[float, float, float, float]) -> bool:
    """La station est-elle dans le carré donné ?"""
    lat_min, lat_max, lon_min, lon_max = carre
    try:
        lat = float(station["lat"])
        lon = float(station["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def main(argv: list[str]) -> int:
    """L'atlas : qui mesure quoi, et où."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-marine-001-"))
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie)
    transport = HttpTransport(timeout=90.0)

    print("TORNE — MARINE-001, l'atlas des stations NOAA/NDBC")
    print(f"preuve brute : {sortie}")
    print()

    stations = _stations(_telecharger(transport, magasin, "activestations", REGISTRE_URL))
    archive = _stations_archive(_telecharger(transport, magasin, "index-ocean", INDEX_OCEAN_URL))

    print("1. le référentiel des stations actives")
    print(f"  stations déclarées : {len(stations)}")
    types = Counter(station.get("type", "?") for station in stations)
    for type_, nombre in types.most_common():
        print(f"    {type_:<10} {nombre}")
    for grandeur in GRANDEURS:
        nombre = sum(1 for station in stations if station.get(grandeur) == "y")
        print(f"  rapportent {grandeur:<14} {nombre}")

    oceanographiques = [
        station
        for station in stations
        if station.get("waterquality") == "y" or station.get("currents") == "y"
    ]
    print(f"\n  stations mesurant l'eau (courants ou qualité de l'eau) : {len(oceanographiques)}")
    proprietaires = Counter(station.get("owner", "?") for station in oceanographiques)
    for proprietaire, nombre in proprietaires.most_common(6):
        print(f"    {nombre:>4}  {proprietaire}")

    print("\n2. l'Atlantique Nord-Est")
    carre = ATLANTIQUE_NE
    locales = [station for station in stations if _dans_le_carre(station, carre)]
    print(f"  stations du registre dans le carré : {len(locales)}")
    for station in sorted(locales, key=lambda s: s["id"]):
        print(
            f"    {station['id']}  {station.get('lat', '?'):>9}N {station.get('lon', '?'):>9}E  "
            f"{station.get('type', '?'):<7} met={station.get('met', '?')} "
            f"courants={station.get('currents', '?')} eau={station.get('waterquality', '?')}  "
            f"| {station.get('name', '')} ({station.get('owner', '')})"
        )
    dans_archive = [station for station in locales if station["id"] in archive]
    print(f"  dont celles qui ont une archive océanographique : {len(dans_archive)}")

    print("\n3. l'archive océanographique")
    print(f"  stations citées par l'index : {len(archive)}")
    connues = [station for station in stations if station["id"] in archive]
    print(f"  dont encore au référentiel des stations actives : {len(connues)}")
    orphelines = sorted(archive - {station["id"] for station in stations})
    print(f"  retirées du référentiel (archives conservées) : {len(orphelines)}")
    archive_ue = [station for station in connues if _dans_le_carre(station, carre)]
    print(f"  stations de l'archive situées dans le carré Atlantique NE : {len(archive_ue)}")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
