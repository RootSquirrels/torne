"""RESOURCE-002 — faisabilité d'observation du volume LNG déchargé.

La question de RESOURCE-002 est **bornée** : peut-on reconstruire, à partir de sources ouvertes,
le volume de GNL effectivement déchargé sur un terminal d'importation ?

Cette mission ne construit **ni modèle ni produit**. Elle mesure, et elle rend sa mesure
rejouable.

Les trois sources confrontées
-----------------------------

- **IMF PortWatch** (`Daily_Ports_Data`) : les appels de navires par port et par jour, par type de
  cargaison. C'est la source du **décompte d'escales**.
- **Enagás**, *Boletín Estadístico* mensuel : les **descargas** (GWh déchargés) et le **nombre de
  navires déchargés**, par plante. C'est la **référence indépendante et datée**.
- **Copernicus Data Space** : les acquisitions **Sentinel-1** au-dessus du terminal. C'est la
  mesure de l'**opportunité d'observation** du tirant d'eau.

Les grandeurs que ce script ne mélange jamais
-----------------------------------------------

Un volume déchargé n'est pas un débit sortant, ni un stock, ni un taux d'utilisation :

- la **cargaison déchargée** (ce que la mission cherche) ;
- le **débit de regazéification** (en GWh, dans le bulletin — une autre grandeur) ;
- l'**expédition** (GNL rechargé sur un navire) ;
- le **tirage cisternes** (GNL chargé sur une citerne) ;
- la **capacité** de regazéification (nominale, contractualisée, disponible).

Elles sont reportées **séparément**, et l'objectif de la mission — la cargaison — n'est jamais
inféré d'une autre.

Deux pièges de cette source, paides en chemin
----------------------------------------------

- le champ `date` est un **DateOnly** : la comparaison se fait par `year`/`month`/`day` entiers ;
- les ports sont nommés **« <nom> LNG Terminal »** : un filtre sur « Barcelona » seul ne
  renvoie rien, et un `LIKE` sur la table entière expire.

Usage :

    uv run python experiments/resource_002_faisabilite_lng.py [repertoire_de_sortie]
"""

from __future__ import annotations

import itertools
import json
import ssl
import statistics
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PORTWATCH = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
CDSE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

MOIS = (
    ("2026-04", 2026, 4),
    ("2026-05", 2026, 5),
    ("2026-06", 2026, 6),
)
"""Les trois mois de confrontation."""

RAYON_KM = 12.0
"""Le rayon de recherche autour du terminal."""

# La reference Enagas : releve dans le Boletin Estadistico, page 17
# (« Actividad en planta de Regasificacion »), colonne du mois 2026.
#
# `gwh`    : energie dechargee des navires metaneros, en GWh/mois
# `navires`: nombre de navires metaneros decharges
#
# Source : le « Boletin Estadistico » d'Enagas, edition mensuelle.
# Releves le 1er novembre 2026 sur les PDF d'avril, mai et juin 2026.
ENAGAS: dict[str, dict[str, tuple[float, int]]] = {
    "BARCELONA": {
        "2026-04": (4590.0, 6),
        "2026-05": (2493.0, 3),
        "2026-06": (1559.0, 2),
    },
    "HUELVA": {
        "2026-04": (3182.0, 3),
        "2026-05": (1560.0, 2),
        "2026-06": (2173.0, 2),
    },
    "CARTAGENA": {
        "2026-04": (401.0, 2),
        "2026-05": (2586.0, 3),
        "2026-06": (1882.0, 2),
    },
    "BILBAO": {
        "2026-04": (4417.0, 4),
        "2026-05": (5472.0, 5),
        "2026-06": (3299.0, 3),
    },
    "SAGUNTO": {
        "2026-04": (1869.0, 4),
        "2026-05": (4224.0, 4),
        "2026-06": (1065.0, 1),
    },
    "MUGARDOS": {
        "2026-04": (2192.0, 2),
        "2026-05": (2198.0, 2),
        "2026-06": (2132.0, 2),
    },
}
"""La reference publiee par l'exploitant, par plante et par mois."""

TERMINAUX = {
    "barcelone": ("Barcelona", 2.165, 41.350),
    "cartagena": ("Cartagena", -0.950, 37.595),
    "bilbao": ("Bilbao", -3.035, 43.355),
    "sagunto": ("Sagunto", -0.265, 39.680),
    "huelva": ("Huelva", -6.930, 37.200),
    "mugardos": ("Mugardos", -8.255, 43.500),
}
"""Les terminaux etudies : nom Enagas, longitude, latitude."""


def _contexte() -> ssl.SSLContext:
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _url(base: str, parametres: dict[str, str]) -> str:
    """Une URL dont tous les espaces sont encodes.

    Une espace brute fait echouer `urllib` *avant* la requete, et l'erreur
    ressemble a un defaut de la source.
    """
    requete = "&".join(f"{cle}={valeur}" for cle, valeur in parametres.items())
    return f"{base}?{requete.replace(' ', '%20')}"


def _get(url: str, n: int = 20_000_000) -> tuple[int, bytes]:
    demande = urllib.request.Request(url, headers={"User-Agent": "torne-resource-002"})
    try:
        with urllib.request.urlopen(demande, timeout=240, context=_contexte()) as reponse:
            return reponse.status, reponse.read(n)
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.read(600)
    except Exception as erreur:
        return 0, f"{type(erreur).__name__}: {erreur}".encode()


def _charge(corps: bytes) -> dict | None:
    try:
        charge = json.loads(corps.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return charge if isinstance(charge, dict) else None


def _noms_de_ports() -> dict[str, str]:
    """Les noms exacts des ports dans PortWatch.

    On passe par le **referentiel des ports** (2 065 entrees, petite table) et
    non par la table des appels : interroger celle-ci par nom force un
    balayage de 1,85 M lignes, qui expire.

    Le referentiel nomme les terminaux « <nom> LNG Terminal » ; c'est la
    premiere cause d'un resultat vide.
    """
    base = f"{PORTWATCH}/PortWatch_ports_database/FeatureServer/0/query"
    parametres = {
        "where": "1=1",
        "outFields": "portid,portname,country",
        "resultRecordCount": "2500",
        "returnGeometry": "false",
        "f": "json",
    }
    code, corps = _get(_url(base, parametres))
    if code != 200:
        return {}
    charge = _charge(corps)
    if charge is None:
        return {}
    ports = [
        str(ligne.get("attributes", {}).get("portname") or "")
        for ligne in charge.get("features") or []
    ]
    trouves: dict[str, str] = {}
    for recherche in TERMINAUX.values():
        for nom in ports:
            if recherche[0].lower() in nom.lower():
                trouves[recherche[0]] = nom
                break
    return trouves


_CACHE_MOIS: dict[tuple[int, int], list[dict]] = {}
"""Un mois de PortWatch ne se demande qu'une fois, pour tous les terminaux."""


def _mois_portwatch(annee: int, mois: int) -> list[dict]:
    """Toutes les lignes d'un mois, une seule requete."""
    cle = (annee, mois)
    if cle in _CACHE_MOIS:
        return _CACHE_MOIS[cle]
    base = f"{PORTWATCH}/Daily_Ports_Data/FeatureServer/0/query"
    parametres = {
        "where": f"year={annee} AND month={mois}",
        "outFields": "date,portname,portcalls,portcalls_cargo,portcalls_tanker,import_tanker,export_tanker",
        "resultRecordCount": "4000",
        "returnGeometry": "false",
        "f": "json",
    }
    code, corps = _get(_url(base, parametres))
    lignes: list[dict] = []
    if code == 200:
        charge = _charge(corps)
        if charge is not None and "error" not in charge:
            lignes = [ligne.get("attributes", {}) for ligne in charge.get("features") or []]
    _CACHE_MOIS[cle] = lignes
    return lignes


def _appels(nom_port: str, annee: int, mois: int) -> tuple[dict | None, str]:
    """Les appels de navires d'un port sur un mois.

    On interroge **le mois entier**, sans filtre de port, puis on ne garde que
    les lignes du terminal. Filtrer par nom de port force un balayage de
    1,85 M lignes, qui expire ; le mois entier en renvoie ~2 000.
    """
    lignes = [
        attributs
        for attributs in _mois_portwatch(annee, mois)
        if str(attributs.get("portname") or "") == nom_port
    ]
    totaux = {
        "jours": len(lignes),
        "appels": 0,
        "appels_cargo": 0,
        "appels_tanker": 0,
        "import_tanker": 0,
        "export_tanker": 0,
        "periode": "",
    }
    for attributs in lignes:
        totaux["appels"] += int(attributs.get("portcalls") or 0)
        totaux["appels_cargo"] += int(attributs.get("portcalls_cargo") or 0)
        totaux["appels_tanker"] += int(attributs.get("portcalls_tanker") or 0)
        totaux["import_tanker"] += int(attributs.get("import_tanker") or 0)
        totaux["export_tanker"] += int(attributs.get("export_tanker") or 0)
    if lignes:
        dates = sorted(str(attributs.get("date") or "") for attributs in lignes)
        totaux["periode"] = f"{dates[0]} -> {dates[-1]}"
    return totaux, "ok"


def _acquisitions(
    longitude: float, latitude: float, annee: int, mois: int
) -> tuple[list[datetime], int]:
    """Les passages Sentinel-1 au-dessus du terminal, et le volume a telecharger.

    Un **meme passage** est decoupe en plusieurs produits dont les
    horodatages different de quelques **millisecondes** : 1er avril,
    06:01:19.988 / 06:01:22.346 / 06:01:23.686. Compter les produits
    comme des passages surestime l'opportunite d'un facteur quatre.
    On regroupe donc les instants a moins de cinq minutes.
    """
    delta = RAYON_KM / 111.0
    ouest, est = longitude - delta, longitude + delta
    sud, nord = latitude - delta, latitude + delta
    polygone = f"POLYGON(({ouest} {sud},{est} {sud},{est} {nord},{ouest} {nord},{ouest} {sud}))"
    debut = f"{annee:04d}-{mois:02d}-01"
    fin = f"{annee:04d}-{mois + 1:02d}-01"
    filtre = (
        "Collection/Name eq 'SENTINEL-1' and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{polygone}') and "
        f"ContentDate/Start gt {debut}T00:00:00.000Z and "
        f"ContentDate/Start lt {fin}T00:00:00.000Z"
    )
    code, corps = _get(
        _url(
            CDSE,
            {"$filter": filtre, "$count": "true", "$top": "1000"},
        )
    )
    if code != 200:
        return [], 0
    charge = _charge(corps)
    if charge is None:
        return [], 0
    produits = charge.get("value") or []
    octets = sum(int(produit.get("ContentLength") or 0) for produit in produits)
    instants = sorted(
        datetime.fromisoformat(str(contenu["Start"]).replace("Z", "+00:00"))
        for produit in produits
        if (contenu := produit.get("ContentDate") or {}).get("Start")
    )
    groupes: list[datetime] = []
    for instant in instants:
        if groupes and (instant - groupes[-1]).total_seconds() < 300:
            continue
        groupes.append(instant)
    return groupes, octets


def _couverture(instants: list[datetime], duree_h: float) -> tuple[float, float]:
    """La probabilite qu'une escale contienne une image, puis deux images *distinctes*.

    Deux images distinctes doivent etre espacees d'au moins `ecart_min_h` : deux
    passages quasi simultanes ne mesurent pas le tirant d'eau avant et apres
    dechargement, ils ne le font qu'une fois.
    """
    if len(instants) < 2:
        return 0.0, 0.0
    debut, fin = instants[0], instants[-1]
    total = (fin - debut).total_seconds()
    if total <= 0:
        return 0.0, 0.0
    fenetre = duree_h * 3600
    echantillons = 2000
    une = deux = 0
    for index in range(echantillons):
        position = debut.timestamp() + total * index / echantillons
        dans = [i for i in instants if position <= i.timestamp() <= position + fenetre]
        if dans:
            une += 1
        if len(dans) >= 2 and (dans[-1] - dans[0]).total_seconds() >= 12 * 3600:
            deux += 1
    return une / echantillons, deux / echantillons


def main(argv: list[str]) -> int:
    """La mesure, et la confrontation."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = (
        Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-resource-002-"))
    )
    sortie.mkdir(parents=True, exist_ok=True)

    print("TORNE — RESOURCE-002, faisabilite d'observation du volume LNG decharge")
    print("PortWatch (escales) · Enagas (reference datee) · Copernicus (opportunite SAR)")
    print()

    noms = _noms_de_ports()
    print("0. Les noms exacts dans PortWatch")
    for cle, (recherche, _longitude, _latitude) in TERMINAUX.items():
        trouve = noms.get(recherche)
        print(f"   {cle:<12} -> {trouve if trouve else 'INTROUVABLE'}")
    print()

    resultats: list[dict] = []
    print("1. Les escales, terminal par terminal et mois par mois")
    for cle, (recherche, longitude, latitude) in TERMINAUX.items():
        nom_port = noms.get(recherche)
        entree: dict = {"terminal": cle, "nom_portwatch": nom_port, "mois": {}}
        print(f"--- {cle} ({nom_port})")
        for etiquette, annee, mois in MOIS:
            totaux, note = (
                _appels(nom_port, annee, mois) if nom_port else (None, "terminal introuvable")
            )
            reference = ENAGAS.get(recherche.upper(), {}).get(etiquette, (0.0, 0))
            instants, octets = _acquisitions(longitude, latitude, annee, mois)
            if len(instants) >= 2:
                ecarts = [(b - a).total_seconds() / 3600 for a, b in itertools.pairwise(instants)]
                median = statistics.median(ecarts)
            else:
                median = float("nan")
            une24, deux24 = _couverture(instants, 24.0)
            une48, _ = _couverture(instants, 48.0)
            entree["mois"][etiquette] = {
                "portwatch": totaux,
                "note": note,
                "enagas_gwh": reference[0],
                "enagas_navires": reference[1],
                "sar": len(instants),
                "sar_octets": octets,
                "sar_octets_par_passage": octets // max(len(instants), 1),
                "sar_ecart_median_h": median,
                "sar_p_une_24h": une24,
                "sar_p_deux_24h": deux24,
                "sar_p_une_48h": une48,
            }
            print(f"    {etiquette}  PortWatch : {note}")
            if totaux:
                print(
                    f"        tanker={totaux['appels_tanker']}  cargo={totaux['appels_cargo']}  "
                    f"total={totaux['appels']}  ({totaux['periode']})"
                )
            print(f"        Enagas : {reference[1]} navire(s), {reference[0]:.0f} GWh decharges")
            print(
                f"        SAR    : {len(instants)} passages · ecart median {median:.2f} h · "
                f"P(1 image/24 h) {une24 * 100:.0f} % · P(2 images distinctes/24 h) "
                f"{deux24 * 100:.0f} % · P(1 image/48 h) {une48 * 100:.0f} %"
            )
            print(
                f"        cout   : {octets / 1e9:.0f} Go de produits Sentinel-1 "
                f"({octets // max(len(instants), 1) // 1_000_000} Mo par passage)"
            )
        resultats.append(entree)

    fichier = sortie / "faisabilite_lng.json"
    fichier.write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 108)
    print("LA CONFRONTATION PHYSIQUE : escales PortWatch contre navires charges, par Enagas")
    print(
        f"{'terminal':<12} {'mois':<9} {'PW tanker':>10} {'PW cargo':>9} {'Enagas':>8}  {'ecart':>6}  lecture"
    )
    for entree in resultats:
        for etiquette, valeurs in entree["mois"].items():
            totaux = valeurs["portwatch"] or {}
            tankers = totaux.get("appels_tanker")
            cargo = totaux.get("appels_cargo")
            navires = valeurs["enagas_navires"]
            if tankers is None:
                lecture = "PortWatch muet"
                ecart = "-"
            elif navires == 0:
                lecture = "aucune reference Enagas relevee"
                ecart = "-"
            else:
                ecart = str(tankers - navires)
                if tankers == navires:
                    lecture = "IDENTIQUE"
                elif tankers > navires:
                    lecture = "PortWatch compte plus (tous petroleiers)"
                else:
                    lecture = "PortWatch EN COMPTE MOINS"
            print(
                f"{entree['terminal']:<12} {etiquette:<9} {tankers!s:>10} {cargo!s:>9} "
                f"{navires:>8}  {ecart:>6}  {lecture}"
            )
    print()
    print(f"preuve : {fichier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
