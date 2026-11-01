"""ATMO-001 — reconnaissance des sources météorologiques et atmosphériques.

Ce script **pose des questions** et **consigne ce qui a répondu**. Il ne
tient aucun état de domaine, ne construit aucune observation et ne publie
aucun produit : c'est un *inventaire d'accessibilité*, la première étape du
périmètre ATMO-001.

Pourquoi un inventaire par exécution. Le programme interdit de traiter une
source comme disponible parce qu'elle est *documentée* : une source dont
l'accès n'a pas été vérifié est une source **inconnue**, pas une source
*inaccessible*. Cette sonde tranche, pour chaque candidat, entre quatre états
réellement distincts :

| État | Ce que la sonde a constaté |
|---|---|
| `accessible` | la source a répondu 2xx, et le contenu est exploitable |
| `sur_tunnel` | la source a répondu 401/403 : elle existe, elle exige un compte |
| `absente` | la source a répondu 404 : le point d'accès n'existe pas |
| `injoignable` | le transport a échoué : DNS, délai, réseau |

**Ce que ce script n'est pas.** Ce n'est pas une acquisition : il ne produit
aucune observation et ne franchit la porte de conformité du socle. Les
questions qu'il pose sont des questions de *disponibilité*, et non des
questions scientifiques. Le contenu qu'il reçoit est conservé comme preuve
brute — au sens du socle, un octet reçu est un octet qui existe — mais aucune
observation n'en est tirée ici.

**Chaque appel est petit et explicite** : une URL, un point, une fenêtre. Rien
n'est balayé, rien n'est téléchargé en masse. Les requêtes sont faites par le
transport du dépôt (`urllib`, en-têtes durcis, aucun secret), et le contenu
reçu est conservé sous son empreinte par le magasin brut.

Usage :

    uv run python experiments/atmo_001_sources_probe.py [répertoire_de_sortie]
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from torne.acquisition import FileRawStore, HttpTransport

JOURNAL_SONDE = "sonde_atmo_001.jsonl"
"""Journal propre à la sonde : une ligne JSON par appel, append-only."""


@dataclass(frozen=True, slots=True)
class Candidat:
    """Une source pressentie, et la question qu'on lui pose."""

    cle: str
    famille: str
    quoi: str
    url: str
    params: dict[str, str]
    credentials: str
    """Ce que l'accès exige : ``aucun``, ``compte`` ou ``inconnu``."""
    forme_attendue: str = "texte"
    """La forme que le contenu **doit** avoir pour être exploitable.

    Le service d'accès de NCEI répond HTTP 200 avec une page d'erreur HTML
    quand le fichier demandé n'existe pas : sans cette vérification, un code
    200 ferait passer une page d'erreur pour des observations. La forme
    attendue est donc **vérifiée sur le corps reçu**, pas déduite du code.
    """


CANDIDATS: tuple[Candidat, ...] = (
    # ------------------------------------------------------------------
    # Météo-France — la source institutionnelle française
    # ------------------------------------------------------------------
    Candidat(
        cle="meteofrance.observation.liste_stations",
        famille="Météo-France",
        quoi="API d'observation, 24 h : liste des stations",
        url="https://public-api.meteofrance.fr/public/DPPaquetObs/liste-stations",
        params={},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="meteofrance.observation.paquet_6m",
        famille="Météo-France",
        quoi="API d'observation, 24 h : paquet infra-horaire 6 min, toutes stations",
        url="https://public-api.meteofrance.fr/public/DPPaquetObs/paquet/stations/infrahoraire-6m",
        params={"date": "2026-10-01T18:00:00Z", "format": "geojson"},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="meteofrance.climatologie.webservice",
        famille="Météo-France",
        quoi="webservice climatologique (historique multi-résolutions)",
        url="https://webservice.meteofrance.com/climatologie",
        params={},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="meteofrance.opendata.portail",
        famille="Météo-France",
        quoi="portail de données ouvertes",
        url="https://www.donnees.meteofrance.fr/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="data.gouv.fr.api.datasets",
        famille="data.gouv.fr",
        quoi="catalogue national : recherche de jeux de données météo",
        url="https://www.data.gouv.fr/api/1/datasets/",
        params={"q": "observations meteorologiques", "page_size": "20"},
        credentials="aucun",
        forme_attendue="json",
    ),
    # ------------------------------------------------------------------
    # Réanalyse — ERA5 et ses points d'accès
    # ------------------------------------------------------------------
    Candidat(
        cle="copernicus.cds.era5.execute",
        famille="Copernicus CDS",
        quoi="exécution d'un traitement ERA5 niveau unique",
        url="https://cds.climate.copernicus.eu/api/retrieve/v1/processes"
        "/reanalysis-era5-single-levels/execution",
        params={},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="copernicus.cds.era5.timeseries",
        famille="Copernicus CDS",
        quoi="API de séries temporelles ERA5",
        url="https://cds.climate.copernicus.eu/api/timeseries/v1/collections"
        "/reanalysis-era5-single-levels",
        params={},
        credentials="compte",
        forme_attendue="json",
    ),
    Candidat(
        cle="copernicus.cds.catalogue.collections",
        famille="Copernicus CDS",
        quoi="catalogue des collections CDS (STAC)",
        url="https://cds.climate.copernicus.eu/api/catalogue/v1/collections",
        params={"limit": "3"},
        credentials="inconnu",
        forme_attendue="json",
    ),
    Candidat(
        cle="arco.era5.zarr.metadonnees",
        famille="ARCO-ERA5 (Google Cloud)",
        quoi="métadonnées du paquet ERA5 zoné, sans authentification",
        url="https://storage.googleapis.com/gcp-public-data-arco-era5/ar/full-chunked-zarr-v2.json",
        params={},
        credentials="aucun",
        forme_attendue="json",
    ),
    Candidat(
        cle="openmeteo.archive.era5",
        famille="Open-Meteo",
        quoi="archive ERA5 re-servie, journalière",
        url="https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": "50.62925",
            "longitude": "3.05726",
            "start_date": "2026-10-01",
            "end_date": "2026-10-02",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Europe/Paris",
        },
        credentials="aucun",
        forme_attendue="json",
    ),
    Candidat(
        cle="openmeteo.previous_runs",
        famille="Open-Meteo",
        quoi="archives de prévision : ce qui était connu, et quand",
        url="https://previous-runs-api.open-meteo.com/v1/previous-runs",
        params={
            "latitude": "50.62925",
            "longitude": "3.05726",
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "hourly": "temperature_2m",
            "past_days": "2",
        },
        credentials="aucun",
        forme_attendue="json",
    ),
    # ------------------------------------------------------------------
    # Stations observées — les archives d'observation hors Météo-France
    # ------------------------------------------------------------------
    Candidat(
        cle="noaa.ghcnd_daily.station",
        famille="NOAA / NCEI",
        quoi="relevés quotidiens GHCN-D (Paris-Montsouris)",
        url="https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily"
        "/access/FRM00007156.csv",
        params={},
        credentials="aucun",
        forme_attendue="csv",
    ),
    Candidat(
        cle="noaa.ghcnd_daily.readme",
        famille="NOAA / NCEI",
        quoi="documentation normative : unités et drapeaux",
        url="https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt",
        params={},
        credentials="aucun",
        forme_attendue="texte",
    ),
    Candidat(
        cle="noaa.global_hourly",
        famille="NOAA / NCEI",
        quoi="observations horaires ISD (Lille, WMO 07014)",
        url="https://www.ncei.noaa.gov/data/global-hourly/access/2026/07014099999.csv",
        params={},
        credentials="aucun",
        forme_attendue="csv",
    ),
    Candidat(
        cle="noaa.ghcnd_daily.index",
        famille="NOAA / NCEI",
        quoi="index des fichiers de station GHCN-D",
        url="https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="dwd.opendata.racine",
        famille="DWD",
        quoi="données ouvertes du service météorologique allemand",
        url="https://opendata.dwd.de/weather/",
        params={},
        credentials="aucun",
        forme_attendue="html",
    ),
    Candidat(
        cle="ogimet.synop.lille",
        famille="OGIMET",
        quoi="messages SYNOP horaires (Lille)",
        url="https://www.ogimet.com/cgi-bin/gsynres",
        params={
            "lang": "en",
            "ind": "07014",
            "ind_type": "syn",
            "ano": "2026",
            "mes": "10",
            "day": "1",
            "hora": "0",
            "min": "0",
            "ndays": "1",
            "ano2": "2026",
            "mes2": "10",
            "day2": "1",
            "hora2": "23",
            "min2": "59",
            "send": "send",
            "format": "txt",
        },
        credentials="aucun",
        forme_attendue="texte",
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


def _forme_ok(candidat: Candidat, corps: bytes) -> bool | None:
    """Le corps a-t-il la forme attendue ? `None` quand la forme est indifférente."""
    if not corps:
        return False
    tete = corps[:400].lstrip()
    # Un statut d'erreur écrit **dans** le corps, avec un code 200 : c'est
    # un refus, pas une réponse. OGIMET fait cela, et le service d'accès de
    # NCEI sert de même une page d'erreur HTML avec le code 200.
    if tete.upper().startswith(b"STATUS:"):
        return False
    if candidat.forme_attendue == "csv":
        return not tete.startswith(b"<") and b"," in tete
    if candidat.forme_attendue == "json":
        return tete.startswith((b"{", b"["))
    if candidat.forme_attendue == "html":
        return b"<html" in tete.lower() or b"<!doctype" in tete.lower()
    return True


def _extrait(corps: bytes, longueur: int = 180) -> str:
    """Un extrait lisible du corps reçu — jamais plus que nécessaire."""
    texte = corps.decode("utf-8", errors="replace")
    texte = " ".join(texte.split())
    return texte[:longueur] + ("…" if len(texte) > longueur else "")


def main(argv: list[str]) -> int:
    """Interroge chaque candidat et consigne ce qui a répondu."""
    sortie = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="torne-atmo-001-"))
    sortie.mkdir(parents=True, exist_ok=True)
    magasin = FileRawStore(sortie)
    transport = HttpTransport(timeout=45.0)

    journal = sortie / JOURNAL_SONDE
    print("TORNE — ATMO-001, reconnaissance des sources")
    print(f"sortie       : {sortie}")
    print(f"horodatage   : {datetime.now(UTC).isoformat()}")
    print()

    etats: dict[str, int] = {}
    with open(journal, "a", encoding="utf-8", newline="\n") as flux:
        for candidat in CANDIDATS:
            demande_url = candidat.url
            if candidat.params:
                from urllib.parse import urlencode

                separateur = "&" if "?" in demande_url else "?"
                demande_url = f"{demande_url}{separateur}{urlencode(candidat.params)}"

            demande = _demande(candidat, demande_url)
            erreur: str | None = None
            reponse = None
            depart = datetime.now(UTC)
            try:
                reponse = transport.send(demande)
            except Exception as exc:  # un échec de transport est un résultat, pas un bug
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
            print(f"               {demande_url}")
            print(
                f"               HTTP {status if status is not None else '—'}"
                f" · {media or '—'} · {taille} octets"
                + (f" · {reponse.elapsed_ms} ms" if reponse is not None else "")
            )
            if reponse is not None:
                print(f"               extrait : {_extrait(reponse.body)}")
            if erreur is not None:
                print(f"               erreur   : {erreur}")
            if empreinte is not None:
                print(f"               empreinte : {empreinte[:16]}…")

            flux.write(
                json.dumps(
                    {
                        "at": depart.isoformat(),
                        "cle": candidat.cle,
                        "famille": candidat.famille,
                        "quoi": candidat.quoi,
                        "url": demande_url,
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
        print(f"  {etat:<16} {nombre}")
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
        label=f"atmo-001:probe:{candidat.cle}",
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
