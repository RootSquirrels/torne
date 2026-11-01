"""ATMO-001 — première acquisition réelle, et profil exploratoire.

Ce script fait ce que le mandat ATMO-001 demande, sur des **données réelles** :
il acquiert, par le socle, des relevés d'observation de stations françaises,
il les lit comme des observations, il en mesure le contenu, et il en sort un
profil — couverture, lacunes, distribution, structure temporelle — et une
**question scientifique testable**.

Ce qu'il touche
----------------

- **Le réseau**, pour de vrai : NOAA/NCEI, sans compte et sans secret.
- **Le disque**, dans un répertoire temporaire qu'il indique à la fin : la
  preuve brute y est conservée, adressée par son empreinte.

Ce qu'il ne fait pas
--------------------

Il ne publie **aucun produit de connaissance**. Il calcule des grandeurs
calculées, avec leur règle ; il ne produit ni évaluation, ni conclusion, ni
décision. La question qu'il dégage est une **question**, pas un résultat.

La référence indépendante
------------------------

Deux contrôles de cohérence sont faits, et ils sont de nature différente :

1. **La cohérence spatiale** — les anomalies de plusieurs stations françaises
   doivent se ressembler *dans les grandes lignes* (elles décrivent le même
   climat) sans être identiques (elles décrivent des lieux différents). Une
   corrélation quasi nulle entre stations voisines trahirait un problème de
   lecture, pas un fait atmosphérique.
2. **L'écart à la réanalyse** — ERA5, ré-servie par Open-Meteo, est une
   **estimation** produite par un modèle, pas une observation. La comparer à
   la station mesure un écart entre deux productions, et ne dit rien de la
   justesse de l'une ou de l'autre. C'est un contrôle, pas une vérité.

Usage :

    uv run python experiments/atmo_001_premiere_acquisition.py
"""

from __future__ import annotations

import csv
import io
import json
import statistics
import sys
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from torne.acquisition.adapters.ghcnd import GhcndDailyAdapter
from torne.acquisition.contracts import (
    AcquisitionOutcome,
    AcquisitionRequest,
    CritereConformite,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)
from torne.acquisition.fetcher import Fetcher
from torne.acquisition.store import FileRawStore
from torne.acquisition.transport import HttpTransport
from torne.atmosphere import (
    anomalies,
    climatologie,
    coupure_moyenne,
    episodes,
    jour_civil,
    observations,
    profil_variable,
    structure_temporelle,
    temperature_moyenne,
)
from torne.atmosphere.observations import DRAPEAUX_QUALITE, Ligne, ligne_depuis_dictionnaire
from torne.atmosphere.profile import explicer_drapaux

ZONE = ZoneInfo("Europe/Paris")
"""Le fuseau des stations françaises : un argument, jamais une déduction."""

PERIODE_REFERENCE = (date(1991, 1, 1), date(2020, 12, 31))
"""La période de référence climate standard de l'OMM (1991-2020)."""

STATIONS = (
    ("FRE00104040", "Lille-Lesquin"),
    ("FRM00007156", "Paris-Montsouris"),
    ("FR000007630", "Toulouse-Blagnac"),
    ("FR000007650", "Marseille-Marignane"),
)
"""Quatre stations, du nord au sud : le contraste est le sujet."""

ELEMENTS = ("TMAX", "TMIN", "PRCP")

OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
"""Le point d'accès d'ERA5 re-servi. Sans clé, sans secret."""


class _OpenMeteoArchiveAdapter:
    """Un adaptateur provisoire pour l'archive ERA5 re-servie.

    Il est **provisoire** : il vit dans une expérience, et n'entre dans
    `src/torne/` que s'il survit à la relecture — c'est la règle du dépôt
    pour les expériences.
    """

    def __init__(self, latitude: float, longitude: float, *, debut: date, fin: date) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.debut = debut
        self.fin = fin

    @property
    def source(self):
        from torne.contracts.observation import Source

        return Source(
            source_id="openmeteo.archive.era5",
            producer="Open-Meteo (ré-servit ERA5, Copernicus C3S / ECMWF)",
            dataset="ERA5 reanalysis archive",
            access_point=OPEN_METEO,
            license="CC BY 4.0 (Open-Meteo) ; ERA5 : Copernicus licence",
            revision_policy=(
                "L'archive est un produit ré-servi : elle ne publie aucun "
                "horodatage de publication par valeur. La date de publication "
                "est INCONNUE (classe N)."
            ),
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """La source rend tout d'un coup, sans rien déclarer."""
        return False

    def initial_request(self) -> AcquisitionRequest:
        """La question : les maxima et minima quotidiens sur la fenêtre."""
        return AcquisitionRequest(
            source_id=self.source.source_id,
            url=OPEN_METEO,
            method="GET",
            params={
                "latitude": f"{self.latitude}",
                "longitude": f"{self.longitude}",
                "start_date": self.debut.isoformat(),
                "end_date": self.fin.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Europe/Paris",
            },
            pagination=PaginationStrategy.NONE,
            max_pages=1,
            label=f"era5:{self.latitude},{self.longitude}",
        )

    def next_request(self, request, response):
        """Pas de page suivante."""
        return None

    def verdict_conformite(self, request, response) -> VerdictConformite:
        """La réponse porte-t-elle les champs quotidiens demandés ?"""
        try:
            charge = json.loads(response.text())
        except json.JSONDecodeError:
            return verdict_from_criteria(
                {
                    "charge": CritereConformite(
                        demande="a JSON body",
                        verifie=False,
                        recu="the body is not JSON",
                    )
                }
            )
        quotidien = charge.get("daily")
        if not isinstance(quotidien, dict):
            return verdict_from_criteria(
                {
                    "charge": CritereConformite(
                        demande="a 'daily' object",
                        verifie=False,
                        recu="the body carries no 'daily' object",
                    )
                }
            )
        absents = [
            champ
            for champ in ("time", "temperature_2m_max", "temperature_2m_min")
            if champ not in quotidien
        ]
        if absents:
            return verdict_from_criteria(
                {
                    "champs": CritereConformite(
                        demande="the daily fields time, temperature_2m_max, temperature_2m_min",
                        verifie=False,
                        recu=f"missing {', '.join(absents)}",
                    )
                }
            )
        return verdict_from_criteria(
            {
                "champs": CritereConformite(
                    demande="the daily fields time, temperature_2m_max, temperature_2m_min",
                    verifie=True,
                    recu=f"{len(quotidien.get('time') or [])} daily records",
                    conforme=True,
                )
            }
        )


def _fetcher(magasin: FileRawStore) -> Fetcher:
    """Le fetcher du socle. Aucun secret n'est nécessaire ici."""
    return Fetcher(transport=HttpTransport(timeout=120.0), store=magasin, credentials=None)


def _acquer(fetcher: Fetcher, adaptateur, quoi: str) -> AcquisitionOutcome:
    """Une acquisition, et sa porte : ce qui n'est pas exploitable arrête le script."""
    issue = fetcher.acquire(adaptateur)
    etat = issue.conformite.value if issue.verdict_conformite else "aucun verdict"
    print(
        f"  {quoi} : {issue.status.value}, {issue.page_count} page(s), "
        f"conformité {etat}, exploitable {issue.exploitable}"
    )
    if not issue.exploitable:
        motif = issue.verdict_conformite.motif if issue.verdict_conformite else "aucun motif"
        raise SystemExit(f"la réponse à « {quoi} » n'est pas exploitable : {motif}")
    return issue


def _lignes(issue: AcquisitionOutcome, magasin: FileRawStore, station_id: str) -> list[Ligne]:
    """Les lignes du CSV de station, lues depuis la preuve conservée."""
    if not issue.evidence:
        raise SystemExit("aucune preuve acquise")
    chemin = magasin.content_path(issue.evidence[0].evidence_id)
    texte = chemin.read_text(encoding="utf-8", errors="replace")
    lecteur = csv.reader(io.StringIO(texte))
    entete = next(lecteur, None)
    if entete is None:
        return []
    lignes: list[Ligne] = []
    for morceaux in lecteur:
        if not any(morceau.strip() for morceau in morceaux):
            continue
        champs = dict(zip(entete, morceaux, strict=False))
        lignes.append(ligne_depuis_dictionnaire(champs, station_id=station_id, elements=ELEMENTS))
    return lignes


def main() -> int:
    """L'acquisition, le profil, et la question qui en sort."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    racine = Path(tempfile.mkdtemp(prefix="torne-atmo-001-"))
    print(f"preuve brute : {racine}")
    magasin = FileRawStore(racine)
    fetcher = _fetcher(magasin)

    rapport: dict[str, object] = {
        "at": datetime.now(UTC).isoformat(),
        "periode_reference": [PERIODE_REFERENCE[0].isoformat(), PERIODE_REFERENCE[1].isoformat()],
        "stations": {},
    }
    anomalies_par_station: dict[str, dict[str, float]] = {}

    # -- 1. les stations ------------------------------------------------
    print("\n1. les stations")
    for station_id, nom in STATIONS:
        adaptateur = GhcndDailyAdapter(station_id, elements=ELEMENTS, label=f"ghcnd:{station_id}")
        issue = _acquer(fetcher, adaptateur, f"{nom} ({station_id})")
        lignes = _lignes(issue, magasin, station_id)
        if not lignes:
            print(f"  {nom} : aucune ligne lue")
            continue

        acquired_at = issue.evidence[0].acquired_at
        evidence_id = issue.evidence[0].evidence_id

        # -- 2. le profil de chaque variable ----------------------------
        profils = {element: profil_variable(lignes, element).as_dict() for element in ELEMENTS}
        tmax = observations(
            lignes,
            "TMAX",
            source_id=adaptateur.source.source_id,
            evidence_id=evidence_id,
            zone=ZONE,
            acquired_at=acquired_at,
        )
        tmin = observations(
            lignes,
            "TMIN",
            source_id=adaptateur.source.source_id,
            evidence_id=evidence_id,
            zone=ZONE,
            acquired_at=acquired_at,
        )
        moyennes = temperature_moyenne(tmax, tmin, zone=ZONE)

        # -- 3. la climatologie de référence et les anomalies ------------
        reference = climatologie(
            moyennes,
            reference_start=PERIODE_REFERENCE[0],
            reference_end=PERIODE_REFERENCE[1],
            zone=ZONE,
        )
        notes = anomalies(moyennes, reference, zone=ZONE)
        chauds = episodes(notes, regime="chaud", zone=ZONE)
        froids = episodes(notes, regime="froid", zone=ZONE)
        auto, taille = structure_temporelle(notes, lags=10)
        coupure = coupure_moyenne(notes)

        couverture = profils["TMAX"]["couverture"]
        print(f"  {nom} : {lignes[0].station.name.strip()}")
        print(
            f"    période {couverture['debut']} → {couverture['fin']} · "
            f"{couverture['jours_observes']} jours observés "
            f"({couverture['taux']:.1%} de {couverture['jours_attendus']})"
        )
        print(
            f"    TMAX : min {profils['TMAX']['minimum']} °C · "
            f"max {profils['TMAX']['maximum']} °C · "
            f"médiane {profils['TMAX']['mediane']} °C"
        )
        lacunes = profils["TMAX"]["lacunes"]
        if lacunes:
            plus_longue = max(lacunes, key=lambda lacune: lacune["longueur"])
            print(
                f"    {len(lacunes)} lacune(s) · la plus longue : "
                f"{plus_longue['debut']} → {plus_longue['fin']} "
                f"({plus_longue['longueur']} j)"
            )
        print(f"    climatologie de référence : {len(reference)} jours · {reference.years} années")
        print(
            f"    anomalies notées : {len(notes)} · épisodes froids : {len(froids)} · "
            f"épisodes chauds : {len(chauds)}"
        )
        if auto:
            print(
                f"    autocorrélation (retards 1-3) : {auto[0]:.3f}, {auto[1]:.3f}, {auto[2]:.3f}"
            )
        if taille is not None:
            print(
                f"    taille effective : {taille.n_eff:.0f} "
                f"({taille.ratio:.1%} de {taille.n} jours, "
                f"troncature au retard {taille.truncation_lag})"
            )
        if coupure is not None:
            print(
                f"    rupture de moyenne (CUSUM) : p = {coupure.p_value:.2g}, "
                f"moyenne {coupure.mean_before:.3f} → {coupure.mean_after:.3f}"
            )

        rapport["stations"][station_id] = {
            "nom": nom,
            "station": lignes[0].station.as_dict(),
            "profils": profils,
            "drapeaux_expliques": {
                element: explicer_drapaux(profils[element]["drapeaux_qualite"], DRAPEAUX_QUALITE)
                for element in ELEMENTS
            },
            "reference": {
                "jours": len(reference),
                "annees": reference.years,
            },
            "anomalies": {
                "nombre": len(notes),
                "episodes_chauds": len(chauds),
                "episodes_froids": len(froids),
                "duree_max_chaud": max((e.longueur for e in chauds), default=0),
                "duree_max_froid": max((e.longueur for e in froids), default=0),
            },
            "autocorrelation": list(auto),
            "taille_effective": (
                {
                    "n": taille.n,
                    "n_eff": taille.n_eff,
                    "ratio": taille.ratio,
                    "troncature": taille.truncation_lag,
                }
                if taille is not None
                else None
            ),
            "coupure": (
                {
                    "p_value": coupure.p_value,
                    "mean_before": coupure.mean_before,
                    "mean_after": coupure.mean_after,
                }
                if coupure is not None
                else None
            ),
        }

        anomalies_par_station[station_id] = {
            jour_civil(observation.temporal.valid_time, ZONE).isoformat(): score
            for observation, score in notes
            if observation.temporal.valid_time is not None
        }

    # -- 4. la cohérence spatiale ----------------------------------------
    print("\n2. cohérence spatiale des anomalies")
    correlations = _coherence(anomalies_par_station)
    for (a, b), valeur in correlations.items():
        print(f"  corr({a}, {b}) = {valeur:.3f}")
    rapport["coherence_spatiale"] = {f"{a}|{b}": v for (a, b), v in correlations.items()}

    # -- 5. l'écart à la réanalyse ---------------------------------------
    print("\n3. écart à la réanalyse ERA5 (contrôle, pas vérité)")
    ecarts = _ecart_reanalyse(fetcher, magasin)
    for cle, valeurs in ecarts.items():
        print(
            f"  {cle} : biais moyen {valeurs['biais']:+.2f} °C · "
            f"corrélation des anomalies {valeurs['correlation']:.3f} · "
            f"{valeurs['jours']} jours"
        )
    rapport["ecart_reanalyse"] = ecarts

    # -- 6. la question --------------------------------------------------
    print("\n4. ce que le profil authorizes à demander")
    question = _question(rapport)
    print(f"  {question}")
    rapport["question_testable"] = question

    chemin = racine / "rapport_atmo_001.json"
    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nrapport : {chemin}")
    print(f"preuve brute : {racine}")
    return 0


def _coherence(anomalies_par_station: dict[str, dict[str, float]]) -> dict[tuple[str, str], float]:
    """La corrélation des anomalies entre stations, sur la période commune."""
    resultat: dict[tuple[str, str], float] = {}
    identifiants = sorted(anomalies_par_station)
    for i, premier in enumerate(identifiants):
        for second in identifiants[i + 1 :]:
            commun = sorted(
                set(anomalies_par_station[premier]) & set(anomalies_par_station[second])
            )
            if len(commun) < 30:
                continue
            x = [anomalies_par_station[premier][jour] for jour in commun]
            y = [anomalies_par_station[second][jour] for jour in commun]
            resultat[(premier, second)] = float(np.corrcoef(x, y)[0, 1])
    return resultat


def _ecart_reanalyse(fetcher: Fetcher, magasin: FileRawStore) -> dict[str, dict[str, float]]:
    """L'écart entre la station et ERA5, sur la période récente.

    Contrôle, pas vérité : ERA5 est une **estimation**. L'écart mesuré est un
    écart entre deux productions, et il sert à voir si la série de station est
    cohérente avec le champ atmosphérique — pas à valider l'une des deux.
    """
    debut = date(2015, 1, 1)
    fin = date(2025, 12, 31)
    stations = (
        ("FRE00104040", "Lille-Lesquin", 50.5700, 3.0975),
        ("FR000007650", "Marseille-Marignane", 43.4378, 5.2158),
    )
    resultat: dict[str, dict[str, float]] = {}
    for station_id, nom, latitude, longitude in stations:
        # La source ne sait pas borner une période : elle rend toujours la
        # période de record complète. La fenêtre est donc appliquée **après**,
        # sur les observations, et l'adaptateur ne prétend pas le contraire.
        adaptateur = GhcndDailyAdapter(
            station_id, elements=("TMAX",), label=f"ghcnd:{station_id}:recent"
        )
        issue = _acquer(fetcher, adaptateur, f"{nom} ({station_id}, période de record)")
        lignes = _lignes(issue, magasin, station_id)
        if not lignes:
            continue
        acquired_at = issue.evidence[0].acquired_at
        obs = observations(
            lignes,
            "TMAX",
            source_id=adaptateur.source.source_id,
            evidence_id=issue.evidence[0].evidence_id,
            zone=ZONE,
            acquired_at=acquired_at,
        )
        par_jour = {
            o.temporal.valid_time.date().isoformat(): o.value
            for o in obs
            if o.temporal.valid_time is not None
            and o.value is not None
            and debut <= o.temporal.valid_time.date() <= fin
        }

        adaptateur_era5 = _OpenMeteoArchiveAdapter(latitude, longitude, debut=debut, fin=fin)
        issue_era5 = _acquer(fetcher, adaptateur_era5, f"ERA5 au-dessus de {nom}")
        charge = json.loads(
            magasin.content_path(issue_era5.evidence[0].evidence_id).read_text(encoding="utf-8")
        )
        quotidien = charge["daily"]
        couples = []
        for jour, maximum in zip(quotidien["time"], quotidien["temperature_2m_max"], strict=False):
            if maximum is None:
                continue
            mesure = par_jour.get(jour)
            if mesure is None:
                continue
            couples.append((float(mesure), float(maximum)))
        if len(couples) < 30:
            continue
        station_valeurs = [c[0] for c in couples]
        era5_valeurs = [c[1] for c in couples]
        bia = statistics.fmean([a - b for a, b in couples])
        resultat[f"{nom} ({station_id})"] = {
            "biais": bia,
            "correlation": float(np.corrcoef(station_valeurs, era5_valeurs)[0, 1]),
            "jours": len(couples),
            "ecart_type_ecart": float(np.std([a - b for a, b in couples], ddof=1)),
        }
    return resultat


def _question(rapport: dict) -> str:
    """La question que le profil autorise à poser.

    Elle est **formulée à partir de ce qui a été mesuré** : elle ne prétend
    rien, et elle est testable sur des données déjà acquises.
    """
    stations = rapport.get("stations", {})
    tailles = [
        s["taille_effective"]["ratio"] for s in stations.values() if s.get("taille_effective")
    ]
    ratio = min(tailles) if tailles else 0.0
    return (
        "Les anomalies thermiques quotidiennes sont-elles persistantes — "
        "c'est-à-dire autocorrélées au-delà du seul effet de l'inertie "
        "quotidienne — et cette persistance diffère-t-elle entre les régime "
        "froids et les régimes chauds ? "
        f"(lecture {len(stations)} station(s), taille effective minimale "
        f"{ratio:.0%} des jours : la question est dimensionnée par ce "
        "chiffre, pas par le nombre de jours)"
    )


if __name__ == "__main__":
    raise SystemExit(main())
