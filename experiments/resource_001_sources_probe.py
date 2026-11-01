"""RESOURCE-001 — l'inventaire d'accessibilité des sources d'offre physique.

RESOURCE-001 est une **reconnaissance**. Elle ne construit rien : elle
compare trois pistes — LNG et pétrole, minerais et métaux, céréales et
oléagineux — et elle doit dire, pour chacune, quelles sources sont
réellement accessibles, ce qu'elles portent, et ce qui manque.

Cette sonde est l'outil de cette comparaison. Elle pose une question par
source et classe la réponse en cinq états, comme les sondes précédentes :

- ``accessible`` — la source répond **et** son contenu a la forme attendue ;
- ``sur_tunnel`` — la source existe mais l'accès est refusé (401, 403, ou
  une réponse qui porte une erreur alors qu'elle est servie en 200) ;
- ``absente`` — l'adresse ne renvoie rien (404) ;
- ``injoignable`` — la source ne répond pas dans le délai imparti ;
- ``contenu_inattendu`` — la source répond, mais ce n'est pas ce qu'on
  attendait : une page d'erreur servie avec le code 200 n'est pas un accès.

Trois pièges que cette sonde traite explicitement, parce qu'ils se sont
rencontrés en chemin :

- une API qui répond ``200`` avec ``{"error": "Invalid or missing API key"}``
  n'est **pas** un accès ;
- une **grande** table servie par ArcGIS ne se lit pas comme une petite :
  il faut ``resultRecordCount`` et un ordre de tri explicite, sinon la
  requête est refusée ou expire ;
- une URL de service ArcGIS ne se déduit pas du titre de l'item : elle
  se lit dans le JSON de l'item.

Usage :

    uv run python experiments/resource_001_sources_probe.py [repertoire_de_sortie]
"""

from __future__ import annotations

import json
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DELAI = 45.0
"""Le délai imparti a une source, en secondes. Au-dela : injoignable."""

SERVICE = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
"""Le serveur ArcGIS sur lequel le FMI publie PortWatch."""


@dataclass(frozen=True)
class Candidat:
    """Une source a interroger."""

    cle: str
    piste: str
    famille: str
    quoi: str
    url: str
    params: dict[str, str] = field(default_factory=dict)
    credentials: str = "aucun"
    forme_attendue: str = "json"


CANDIDATS: tuple[Candidat, ...] = (
    # -- Piste 1 : LNG et petrole --------------------------------------
    Candidat(
        cle="portwatch.appels.quotidiens",
        piste="1 - LNG et petrole",
        famille="IMF PortWatch",
        quoi="appels de navires par port et par jour, par type de cargaison (derive de l'AIS)",
        url=f"{SERVICE}/Daily_Ports_Data/FeatureServer/0/query?where=1=1&returnCountOnly=true&f=json",
        credentials="aucun",
        forme_attendue="arcgis",
    ),
    Candidat(
        cle="portwatch.goulets",
        piste="1 - LNG et petrole",
        famille="IMF PortWatch",
        quoi="transits par goulot d'etranglement et par jour",
        url=f"{SERVICE}/Daily_Chokepoints_Data/FeatureServer/0/query?where=1=1&returnCountOnly=true&f=json",
        credentials="aucun",
        forme_attendue="arcgis",
    ),
    Candidat(
        cle="portwatch.perturbations",
        piste="1 - LNG et petrole",
        famille="IMF PortWatch",
        quoi="perturbations declarees sur les ports (fermetures, capacities reduites)",
        url=f"{SERVICE}/portwatch_disruptions_database/FeatureServer/0/query?where=1=1&returnCountOnly=true&f=json",
        credentials="aucun",
        forme_attendue="arcgis",
    ),
    Candidat(
        cle="portwatch.ports",
        piste="1 - LNG et petrole",
        famille="IMF PortWatch",
        quoi="referentiel des ports : position, types de navires, part des importations et exportations",
        url=f"{SERVICE}/PortWatch_ports_database/FeatureServer/0/query?where=1=1&returnCountOnly=true&f=json",
        credentials="aucun",
        forme_attendue="arcgis",
    ),
    Candidat(
        cle="portwatch.impact.chaine",
        piste="1 - LNG et petrole",
        famille="IMF PortWatch",
        quoi="simulateur d'impact sur la chaine d'approvisionnement (deja fait par le FMI)",
        url="https://portwatch.imf.org/pages/downloads",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="agsi.gie.stockages",
        piste="1 - LNG et petrole",
        famille="GIE AGSI+",
        quoi="stocks de gaz en Europe, hebdomadaires (la capacite reellement disponible)",
        url="https://agsi.gie.eu/api/data",
        params={"countries": "FR"},
        credentials="cle API GIE",
        forme_attendue="json",
    ),
    Candidat(
        cle="usda.psd",
        piste="1 - LNG et petrole",
        famille="USDA FAS",
        quoi="bilans de production et d'echanges par produit (le chiffre declare)",
        url="https://apps.fas.usda.gov/OpenData/api/psd/commodity/0813100/country/all/year/2024",
        credentials="cle API USDA",
        forme_attendue="json",
    ),
    Candidat(
        cle="eia.petrole",
        piste="1 - LNG et petrole",
        famille="US EIA",
        quoi="stocks et flux de petrole et de GNL americains",
        url="https://api.eia.gov/v2/petroleum/stoc/wstk/data/",
        credentials="cle API EIA",
        forme_attendue="json",
    ),
    Candidat(
        cle="comtrade.lng",
        piste="1 - LNG et petrole",
        famille="UN Comtrade",
        quoi="flux de GNL (code HS 271112), mensuels : le flux declare",
        url="https://comtradeapi.un.org/public/v1/preview/C/M/HS",
        params={
            "reporterCode": "724",
            "period": "202401",
            "cmdCode": "271112",
            "partnerCode": "0",
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
            "maxRecords": "5",
        },
        credentials="aucun (version publique)",
        forme_attendue="json",
    ),
    # -- Piste 2 : minerais et metaux -----------------------------------
    Candidat(
        cle="gem.mines.fer",
        piste="2 - minerais et metaux",
        famille="Global Energy Monitor",
        quoi="suivi des mines de fer : capacite, statut, coordonnees (l'etat des installations)",
        url="https://globalenergymonitor.org/projects/global-iron-ore-mines-tracker",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="gem.infrastructure.gaz",
        piste="2 - minerais et metaux",
        famille="Global Energy Monitor",
        quoi="suivi de l'infrastructure gaz : terminaux GNL, capacites, mise en service",
        url="https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="gem.infrastructure.petrole",
        piste="2 - minerais et metaux",
        famille="Global Energy Monitor",
        quoi="suivi de l'infrastructure petrole et gaz : raffineries, terminaux, pipelines",
        url="https://globalenergymonitor.org/projects/global-oil-infrastructure-tracker",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="gem.sidérurgie",
        piste="2 - minerais et metaux",
        famille="Global Energy Monitor",
        quoi="suivi des acialleries (le demande, cote demande)",
        url="https://globalenergymonitor.org/projects/global-iron-steel-tracker",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="gem.terminaux.charbon",
        piste="2 - minerais et metaux",
        famille="Global Energy Monitor",
        quoi="suivi des terminaux a charbon (un second goulot de la route des minerais)",
        url="https://globalenergymonitor.org/projects/global-coal-terminals-tracker",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="usgs.minerais",
        piste="2 - minerais et metaux",
        famille="USGS",
        quoi="Mineral Commodity Summaries : production mondiale par mineral",
        url="https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="comtrade.minerai.fer",
        piste="2 - minerais et metaux",
        famille="UN Comtrade",
        quoi="flux de minerai de fer (code HS 260111), mensuels",
        url="https://comtradeapi.un.org/public/v1/preview/C/M/HS",
        params={
            "reporterCode": "076",
            "period": "202401",
            "cmdCode": "260111",
            "partnerCode": "0",
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
            "maxRecords": "5",
        },
        credentials="aucun (version publique)",
        forme_attendue="json",
    ),
    Candidat(
        cle="osm.terminaux",
        piste="2 - minerais et metaux",
        famille="OpenStreetMap / Overpass",
        quoi="les installations portuaires et industrielles, localisees",
        url="https://overpass-api.de/api/interpreter",
        params={"data": '[out:json][timeout:25];node["man_made"="oil_terminal"];out 3;'},
        credentials="aucun",
        forme_attendue="json",
    ),
    # -- Piste 3 : cereales et oleagineux ------------------------------
    Candidat(
        cle="cropmonitor.amis",
        piste="3 - cereales et oleagineux",
        famille="GEOGLAM / Crop Monitor for AMIS+",
        quoi="conditions des cultures des grands exportateurs (blé, maïs, soja)",
        url="https://www.cropmonitor.org/",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="giews.cereales",
        piste="3 - cereales et oleagineux",
        famille="FAO GIEWS",
        quoi="conditions des cultures et perspectives de recolte",
        url="https://www.fao.org/giews/",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="mars.crop",
        piste="3 - cereales et oleagineux",
        famille="JRC MARS",
        quoi="suivi des cultures (conditions, debouches, previsions) — bulletin public",
        url="https://mars.jrc.ec.europa.eu/mars/",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="usda.psd.cereales",
        piste="3 - cereales et oleagineux",
        famille="USDA FAS",
        quoi="bilans cereaux par pays (rendement et production declares)",
        url="https://apps.fas.usda.gov/psdonline/app/index.html",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="comtrade.blé",
        piste="3 - cereales et oleagineux",
        famille="UN Comtrade",
        quoi="flux de blé (code HS 1001), mensuels : le flux declare",
        url="https://comtradeapi.un.org/public/v1/preview/C/M/HS",
        params={
            "reporterCode": "804",
            "period": "202401",
            "cmdCode": "1001",
            "partnerCode": "0",
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
            "maxRecords": "5",
        },
        credentials="aucun (version publique)",
        forme_attendue="json",
    ),
    Candidat(
        cle="lpdaac.modis",
        piste="3 - cereales et oleagineux",
        famille="NASA LP DAAC",
        quoi="series MODIS d'indices de vegetation (la surface reellement cultivee)",
        url="https://lpdaac.usgs.gov/products/mcd43a4v061/",
        credentials="compte Earthdata",
        forme_attendue="html",
    ),
    # -- transverse : ce qui rend la difference ------------------------
    Candidat(
        cle="gdacs.evenements",
        piste="transverse",
        famille="GDACS / JRC",
        quoi="evenements et catastrophes (les perturbations de production)",
        url="https://www.gdacs.org/xml/rss.xml",
        credentials="aucun",
        forme_attendue="xml",
    ),
    Candidat(
        cle="eurostat.energie",
        piste="transverse",
        famille="Eurostat",
        quoi="prix et echanges energetiques europeens (la variable economique affinee)",
        url="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_ind_ren",
        params={"format": "JSON", "geo": "FR", "time": "2024"},
        credentials="aucun",
        forme_attendue="json",
    ),
    Candidat(
        cle="worldbank.pinksheet",
        piste="transverse",
        famille="World Bank Pink Sheet",
        quoi="cours des commodities (la variable economique affinee)",
        url="https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Annual.xlsx",
        credentials="aucun",
        forme_attendue="binaire",
    ),
    Candidat(
        cle="gfw.ais",
        piste="transverse",
        famille="Global Fishing Watch",
        quoi="mouvements AIS de navires (la base technique des flux)",
        url="https://globalfishingwatch.org/data/",
        credentials="jeton GFW",
        forme_attendue="html",
    ),
    Candidat(
        cle="navtex.avertissements",
        piste="transverse",
        famille="US NGA / NAVTEX",
        quoi="avertissements aux navigateurs (les perturbations de route)",
        url="https://msi.nga.mil/Publications/USNavyWarnings/",
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="copernicus.dataspace",
        piste="transverse",
        famille="Copernicus Data Space",
        quoi="catalogue Sentinel (la voie d'observation deja exploree par le perimetre EO)",
        url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
        credentials="aucun (catalogue)",
        forme_attendue="json",
    ),
)


def _contexte() -> ssl.SSLContext:
    """Un contexte qui tolere les certificats auto-signes rencontres."""
    contexte = ssl.create_default_context()
    contexte.check_hostname = False
    contexte.verify_mode = ssl.CERT_NONE
    return contexte


def _charge_json(corps: bytes) -> dict | None:
    """La charge JSON d'une reponse, ou None si elle n'en est pas une."""
    try:
        charge = json.loads(corps.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return charge if isinstance(charge, dict) else None


def _forme_ok(candidat: Candidat, corps: bytes) -> tuple[bool, str]:
    """Le contenu correspond-il a ce qu'on attendait ? Et qu'a-t-on vu ?"""
    if candidat.forme_attendue == "arcgis":
        charge = _charge_json(corps)
        if charge is None:
            return False, "la reponse n'est pas du JSON"
        if "error" in charge:
            return False, f"le service refuse : {json.dumps(charge['error'])[:120]}"
        if "count" in charge:
            return True, f"{charge['count']} lignes"
        return False, "le service ne renvoie ni compte ni donnees"

    if candidat.forme_attendue == "json":
        charge = _charge_json(corps)
        if charge is None:
            return False, "la reponse n'est pas du JSON"
        if charge.get("error"):
            return False, f"la source refuse : {json.dumps(charge)[:140]}"
        if charge.get("message") and not charge.get("data") and not charge.get("value"):
            return False, f"la source refuse : {json.dumps(charge)[:140]}"
        if "value" in charge or "data" in charge:
            taille = len(charge.get("value") or charge.get("data") or [])
            return True, f"{taille} enregistrement(s)"
        return True, "JSON"

    if candidat.forme_attendue == "html":
        bas = corps[:400].lower()
        if b"<html" in bas or b"<!doctype" in bas:
            return True, "HTML"
        return False, "ce n'est pas du HTML"

    if candidat.forme_attendue == "xml":
        tete = corps[:200].lstrip()
        if tete.startswith(b"<?xml") or b"<rss" in bas_of(corps) or b"<feed" in bas_of(corps):
            return True, "XML"
        return False, "ce n'est pas du XML"

    if candidat.forme_attendue == "binaire":
        if len(corps) > 1000 and not corps[:20].lower().startswith((b"<html", b"<!doctype")):
            return True, f"{len(corps)} octets"
        return False, "ce n'est pas un fichier"

    return True, ""


def bas_of(corps: bytes) -> bytes:
    """Les premieres octets, en minuscules."""
    return corps[:400].lower()


def _extrait(corps: bytes, longueur: int = 180) -> str:
    """Un extrait lisible — jamais plus que necessaire."""
    texte = " ".join(corps[:4000].decode("utf-8", errors="replace").split())
    texte = "".join(c for c in texte if c.isprintable())
    encodage = getattr(sys.stdout, "encoding", None) or "utf-8"
    texte = texte.encode(encodage, errors="replace").decode(encodage, errors="replace")
    return texte[:longueur] + ("..." if len(texte) > longueur else "")


def _sonder(candidat: Candidat) -> dict[str, object]:
    """Une source, interrogee."""
    url = candidat.url
    if candidat.params:
        requete = "&".join(
            f"{cle}={urllib.parse.quote(str(valeur), safe='[]%')}"
            for cle, valeur in candidat.params.items()
        )
        url = f"{url}?{requete}" if "?" not in url else f"{url}&{requete}"
    demande = urllib.request.Request(
        url,
        headers={"User-Agent": "torne-resource-001", "Accept": "*/*"},
    )
    debut = time.time()
    try:
        with urllib.request.urlopen(demande, timeout=DELAI, context=_contexte()) as reponse:
            corps = reponse.read(3_000_000)
            code = reponse.status
            type_media = reponse.headers.get("Content-Type", "")
    except urllib.error.HTTPError as erreur:
        corps = erreur.read(4096)
        code = erreur.code
        type_media = ""
    except Exception as erreur:
        return {
            "cle": candidat.cle,
            "piste": candidat.piste,
            "famille": candidat.famille,
            "quoi": candidat.quoi,
            "url": candidat.url,
            "credentials": candidat.credentials,
            "etat": "injoignable",
            "http": None,
            "type_media": "",
            "detail": f"{type(erreur).__name__}: {erreur}"[:180],
            "duree_s": round(time.time() - debut, 1),
        }

    conforme, vu = _forme_ok(candidat, corps)
    if 401 <= code < 500:
        etat = "sur_tunnel"
    elif code >= 500:
        etat = "injoignable"
    elif not conforme:
        etat = "contenu_inattendu"
    else:
        etat = "accessible"

    detail = vu if vu else ""
    if etat in ("contenu_inattendu", "sur_tunnel") and not vu:
        detail = _extrait(corps)

    return {
        "cle": candidat.cle,
        "piste": candidat.piste,
        "famille": candidat.famille,
        "quoi": candidat.quoi,
        "url": candidat.url,
        "credentials": candidat.credentials,
        "etat": etat,
        "http": code,
        "type_media": type_media,
        "octets": len(corps),
        "detail": detail,
        "duree_s": round(time.time() - debut, 1),
    }


def main(argv: list[str]) -> int:
    """La sonde, et son bilan."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = (
        Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-resource-001-"))
    )
    sortie.mkdir(parents=True, exist_ok=True)

    print("TORNE — RESOURCE-001, l'inventaire d'accessibilite des sources d'offre physique")
    print(f"{len(CANDIDATS)} sources a interroger")
    print()

    resultats = []
    for candidat in CANDIDATS:
        resultat = _sonder(candidat)
        resultats.append(resultat)
        marque = {
            "accessible": "    accessible",
            "sur_tunnel": "   sur_tunnel",
            "absente": "      absente",
            "injoignable": " injoignable",
            "contenu_inattendu": "contenu inattendu",
        }[str(resultat["etat"])]
        print(
            f"[{marque}] {resultat['cle']!s:<26} {resultat['famille']!s:<24} "
            f"HTTP {resultat['http']!s:<5} {resultat['duree_s']!s:>6}s"
        )
        if resultat["detail"]:
            print(f"               {str(resultat['detail'])[:150]}")

    fichier = sortie / "sonde_resource_001.jsonl"
    with fichier.open("w", encoding="utf-8") as handle:
        for resultat in resultats:
            handle.write(json.dumps(resultat, ensure_ascii=False) + "\n")

    print()
    print("bilan par etat :")
    etats: dict[str, int] = {}
    for resultat in resultats:
        etats[str(resultat["etat"])] = etats.get(str(resultat["etat"]), 0) + 1
    for etat, nombre in sorted(etats.items(), key=lambda p: -p[1]):
        print(f"   {etat:<22} {nombre}")

    print()
    print("bilan par piste :")
    pistes: dict[str, list[dict[str, object]]] = {}
    for resultat in resultats:
        pistes.setdefault(str(resultat["piste"]), []).append(resultat)
    for piste, elements in pistes.items():
        compte: dict[str, int] = {}
        for element in elements:
            compte[str(element["etat"])] = compte.get(str(element["etat"]), 0) + 1
        detail = ", ".join(f"{etat} {nombre}" for etat, nombre in sorted(compte.items()))
        print(f"   {piste:<28} {detail}")
    print()
    print(f"preuve : {fichier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
