"""MARINE-001 — reconnaissance des sources océanographiques et côtières.

Ce script **pose des questions** et **consigne ce qui a répondu**. Comme
ATMO-001, il distingue cinq états d'accessibilité, et il vérifie **la forme
du contenu** plutôt que le seul code HTTP — le service d'accès de NCEI servant
des pages d'erreur HTML avec le code 200, on ne parie pas sur le statut.

Les candidats ne sont pas choisis à l'intuition : ce sont les points d'accès
**documentés** de l'océanographie européenne et atlantique, plus ceux que la
mission doit savoir Closure. La question posée à chacun est la même — *peut-on
obtenir des données, et à quelles conditions ?*

Usage :

    uv run python experiments/marine_001_sources_probe.py [répertoire_de_sortie]
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from torne.acquisition import FileRawStore, HttpTransport

JOURNAL_SONDE = "sonde_marine_001.jsonl"


@dataclass(frozen=True, slots=True)
class Candidat:
    """Une source pressentie, et la question qu'on lui pose."""

    cle: str
    famille: str
    quoi: str
    url: str
    params: dict[str, str]
    credentials: str
    forme_attendue: str = "texte"


CANDIDATS: tuple[Candidat, ...] = (
    # -- Copernicus Marine : l'institutionnel européen --------------------
    Candidat(
        cle="cmems.catalogue.stac",
        famille="Copernicus Marine",
        quoi="catalogue STAC du Data Store (319 produits)",
        url="https://stac.marine.copernicus.eu/metadata/catalog.stac.json",
        params={},
        credentials="aucun",
        forme_attendue="json",
    ),
    Candidat(
        cle="cmems.produit.stac",
        famille="Copernicus Marine",
        quoi="fiche produit d'une reanalyse globale (GLORYS12)",
        url="https://stac.marine.copernicus.eu/metadata/GLOBAL_MULTIYEAR_PHY_001_030"
        "/product.stac.json",
        params={},
        credentials="aucun",
        forme_attendue="json",
    ),
    Candidat(
        cle="cmems.donnees.arco",
        famille="Copernicus Marine",
        quoi="paquet ARCO zarr de la reanalyse globale",
        url="https://s3.waw3-1.cloudferro.com/mdl-arco-time-025/arco/GLOBAL_MULTIYEAR_PHY_001_030"
        "/cmems_mod_glo_phy_my_0.083deg_P1D-m_202311/timeChunked/.zmetadata",
        params={},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="cmems.donnees.natives",
        famille="Copernicus Marine",
        quoi="paquet netCDF natif de la reanalyse globale",
        url="https://s3.waw3-1.cloudferro.com/mdl-native-14/native/GLOBAL_MULTIYEAR_PHY_001_030"
        "/cmems_mod_glo_phy_my_0.083deg_P1D-m_202311",
        params={},
        credentials="compte",
        forme_attendue="texte",
    ),
    Candidat(
        cle="cmems.portail",
        famille="Copernicus Marine",
        quoi="portail de données du Data Store",
        url="https://data.marine.copernicus.eu/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
    # -- Argo : l'in situ mondial ----------------------------------------
    Candidat(
        cle="argo.index.profils",
        famille="Argo (GDAC Ifremer)",
        quoi="index global des profils : fichier, date, latitude, longitude, date de mise à jour",
        url="https://data-argo.ifremer.fr/ar_index_global_prof.txt",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    Candidat(
        cle="argo.index.metadonnees",
        famille="Argo (GDAC Ifremer)",
        quoi="index global des métadonnées de flotteurs",
        url="https://data-argo.ifremer.fr/ar_index_global_meta.txt",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    # -- NOAA NDBC : les bouées ouvertes --------------------------------
    Candidat(
        cle="ndbc.realtime.fiche",
        famille="NOAA / NDBC",
        quoi="relevé temps réel d'une bouée (vent, pression, température)",
        url="https://www.ndbc.noaa.gov/data/realtime2/14049.txt",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    Candidat(
        cle="ndbc.historique.ocean.index",
        famille="NOAA / NDBC",
        quoi="index des archives océanographiques (salinité, turbidité)",
        url="https://www.ndbc.noaa.gov/data/historical/ocean/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="ndbc.historique.ocean.fichier",
        famille="NOAA / NDBC",
        quoi="archive océanographique annuelle d'une bouée",
        url="https://www.ndbc.noaa.gov/data/historical/ocean/44042o2025.txt.gz",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    # -- EMODnet : l'in situ européen -----------------------------------
    # -- Le referentiel des stations, et l'in situ européen ---------------
    Candidat(
        cle="ndbc.referentiel.stations",
        famille="NOAA / NDBC",
        quoi="référentiel des stations actives : position, type, grandeurs rapportées",
        url="https://www.ndbc.noaa.gov/activestations.xml",
        params={},
        credentials="aucun",
        forme_attendue="xml",
    ),
    Candidat(
        cle="argo.profil.netcdf",
        famille="Argo (GDAC Ifremer)",
        quoi="un profil Argo (netCDF), tel que l'index le désigne",
        url="https://data-argo.ifremer.fr/dac/aoml/13857/profiles/D13857_001.nc",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    Candidat(
        cle="emodnet.erddap",
        famille="EMODnet Physics",
        quoi="serveur ERDDAP des observations côtières européennes",
        url="https://erddap.emodnet-physics.eu/erddap/info/index.json",
        params={},
        credentials="aucun",
        forme_attendue="json",
    ),
    # -- Le catalogue national -------------------------------------------
    Candidat(
        cle="data.gouv.fr.api.datasets",
        famille="data.gouv.fr",
        quoi="catalogue national : données maritimes et côtières",
        url="https://www.data.gouv.fr/api/1/datasets/",
        params={"q": "maritime", "page_size": "20"},
        credentials="aucun",
        forme_attendue="json",
    ),
    # -- Ifremer : le portail des données marines -----------------------
    Candidat(
        cle="ifremer.portail.marine",
        famille="Ifremer",
        quoi="portail des données marines (accès aux données, centre de données)",
        url="https://data.ifremer.fr/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
)


def _etat(status: int | None, erreur: str | None, forme_ok: bool | None = None) -> str:
    """L'état d'accessibilité, tel qu'il a été constaté."""
    if erreur is not None:
        return "injoignable"
    assert status is not None
    if 200 <= status < 300:
        if forme_ok is False:
            return "contenu_inattendu"
        return "accessible"
    if status in (401, 403):
        return "sur_tunnel"
    if status == 404:
        return "absente"
    return f"erreur_http_{status}"


def _forme_ok(candidat: Candidat, corps: bytes) -> bool:
    """Le corps a-t-il la forme attendue ?"""
    if not corps:
        return False
    tete = corps[:600].lstrip()
    if tete.upper().startswith(b"STATUS:"):
        return False
    if candidat.forme_attendue == "csv":
        return not tete.startswith(b"<") and b"," in tete
    if candidat.forme_attendue == "json":
        return tete.startswith((b"{", b"["))
    if candidat.forme_attendue == "html":
        return b"<html" in tete.lower() or b"<!doctype" in tete.lower()
    if candidat.forme_attendue == "xml":
        return tete.startswith(b"<?xml")
    if candidat.forme_attendue == "texte":
        return not tete.startswith(b"<")
    return True


def _extrait(corps: bytes, longueur: int = 200) -> str:
    """Un extrait lisible — jamais plus que nécessaire.

    Le corps peut être binaire — une archive gzip, un index de 318 Mo. Les
    caractères illisibles sont donc **écartés** et le résultat est ramené à
    ce que la sortie standard sait encoder : un extrait ne doit jamais faire
    tomber la sonde.
    """
    texte = " ".join(corps[:4000].decode("utf-8", errors="replace").split())
    texte = "".join(c for c in texte if c.isprintable())
    encodage = getattr(sys.stdout, "encoding", None) or "utf-8"
    texte = texte.encode(encodage, errors="replace").decode(encodage, errors="replace")
    return texte[:longueur] + ("…" if len(texte) > longueur else "")


def main(argv: list[str]) -> int:
    """Interroge chaque candidat et consigne ce qui a répondu."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-marine-001-"))
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie)
    transport = HttpTransport(timeout=45.0)

    journal = sortie / JOURNAL_SONDE
    print("TORNE — MARINE-001, reconnaissance des sources océanographiques")
    print(f"sortie     : {sortie}")
    print(f"horodatage : {datetime.now(UTC).isoformat()}")
    print()

    etats: dict[str, int] = {}
    with open(journal, "a", encoding="utf-8", newline="\n") as flux:
        for candidat in CANDIDATS:
            url = candidat.url
            if candidat.params:
                from urllib.parse import urlencode

                separateur = "&" if "?" in url else "?"
                url = f"{url}{separateur}{urlencode(candidat.params)}"

            demande = _demande(candidat, url)
            erreur: str | None = None
            reponse = None
            depart = datetime.now(UTC)
            try:
                reponse = transport.send(demande)
            except Exception as exc:  # un échec de transport est un résultat
                erreur = f"{type(exc).__name__}: {exc}"

            status = reponse.status_code if reponse is not None else None
            forme_ok = _forme_ok(candidat, reponse.body) if reponse is not None else None
            etat = _etat(status, erreur, forme_ok)
            etats[etat] = etats.get(etat, 0) + 1

            media = reponse.content_type if reponse is not None else None
            taille = len(reponse.body) if reponse is not None else 0
            empreinte = None
            if reponse is not None and reponse.body:
                preuve = magasin.put(
                    reponse.body,
                    source_id=candidat.cle,
                    key=f"{candidat.cle}#probe",
                    media_type=media,
                    acquired_at=depart,
                )
                empreinte = preuve.evidence_id

            print(f"[{etat:>14}] {candidat.cle}")
            print(f"               {candidat.famille} — {candidat.quoi}")
            print(
                f"               HTTP {status if status is not None else '—'} · {media or '—'} · {taille} octets"
            )
            if reponse is not None:
                print(f"               extrait : {_extrait(reponse.body)}")
            if erreur is not None:
                print(f"               erreur   : {erreur}")

            flux.write(
                json.dumps(
                    {
                        "at": depart.isoformat(),
                        "cle": candidat.cle,
                        "famille": candidat.famille,
                        "quoi": candidat.quoi,
                        "url": url,
                        "credentials": candidat.credentials,
                        "status": status,
                        "media_type": media,
                        "taille": taille,
                        "empreinte": empreinte,
                        "etat": etat,
                        "erreur": erreur,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print()
    print("Bilan :")
    for etat, nombre in sorted(etats.items(), key=lambda couple: (-couple[1], couple[0])):
        print(f"  {etat:<20} {nombre}")
    print()
    print(f"journal de la sonde : {journal}")
    return 0


def _demande(candidat: Candidat, url: str):
    """La demande d'acquisition, au format du socle."""
    from torne.acquisition import AcquisitionRequest

    return AcquisitionRequest(
        source_id=candidat.cle,
        url=url,
        method="GET",
        label=f"marine-001:probe:{candidat.cle}",
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
