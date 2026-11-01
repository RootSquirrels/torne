"""MARINE-001 — première acquisition réelle, sur une source ouverte.

La reconnaissance a établi que la source institutionnelle océanographique
européenne (Copernicus Marine) est **derrière un compte**, exactement comme
Météo-France. La source ouverte qui répond sans secret est l'archive
**océanographique** de NOAA/NDBC : du texte, gzipippé, avec **salinité,
température de l'eau, turbidité et profondeur**.

Ce script l'acquiert **par le socle** — preuve brute conservée, conformité
vérifiée sur le contenu — puis en mesure le contenu. Il ne produit aucun
produit de connaissance : il produit un **profil**, et la question que ce
profil autorise à poser.

Ce que le profil regarde
------------------------

- **La couverture** : le nombre d'instants observés, et ce que la série ne
  couvre pas. Une bouée oceanographique ne mesure pas en continu : elle
  mesure par salves, et son absence n'est pas une panne, c'est un protocole.
- **Les valeurs manquantes** : l'archive NDBC n'a pas une sentinelle unique.
  Sur le fichier de la station 44042 (estuaire du Potomac, 18 ans), la
  colonne `COND` ne contient que `999.00`, `O2%` que `999.0`, `SAL` que des
  mesures réelles, `TURB` que `99` : **la sentinelle dépend de la colonne**.
  Elle est donc reconnue **par colonne**, et le profil **compte** ce qui a
  été traité comme absent — pour que la règle soit auditable.
- **Le cycle saisonnier de la salinité** : sur une station influencée par un
  fleuve, c'est la signature du cycle hydrologique.
- **Les épisodes de dessalement** : les baisses de salinité les plus fortes
  sur 24 h. C'est la signature d'un **panache** — d'une crue, d'un front.

Usage :

    uv run python experiments/marine_001_premier_acquisition.py [station] [année]
"""

from __future__ import annotations

import gzip
import itertools
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from torne.acquisition import AcquisitionRequest, FileRawStore, HttpTransport
from torne.acquisition.contracts import (
    Conformite,
    CritereConformite,
    HttpResponse,
    verdict_from_criteria,
)

SOURCE_ID = "noaa.ndbc.ocean"
PRODUCTEUR = "NOAA National Data Buoy Center (NDBC)"

SENTINELLES = (99.0, 999.0)
"""Les valeurs par lesquelles NDBC déclare une absence.

Observé dans les archives océanographiques : la colonne `COND` ne contient que
`999.00`, `O2%` que `999.0`, `O2PPM`, `TURB`, `PH` et `EH` que `99` ou
`99.00`, et `SAL` des mesures réelles. **La sentinelle dépend donc de la
colonne** : `99` et `999` sont tous deux utilisés, et les traiter comme des
mesures mettrait 999 °C et 999 psu dans une série marine.

> [NON VÉRIFIÉ] La table officielle des valeurs manquantes n'a pas été
> trouvée : la page « Measurement Descriptions and Units » du guide NDBC
> répond 404. La règle ci-dessus est **observée**, pas documentée.
"""

COLONNES = (
    "annee",
    "mois",
    "jour",
    "heure",
    "minute",
    "profondeur",
    "temperature_eau",
    "conductivite",
    "salinite",
    "o2_pct",
    "o2_ppm",
    "nuage",
    "turbidite",
    "ph",
    "eh",
)

INDICES = {
    "profondeur": 5,
    "temperature_eau": 6,
    "salinite": 8,
    "turbidite": 12,
}


@dataclass(frozen=True, slots=True)
class Mesure:
    """Un instant mesuré par la bouée."""

    instant: datetime
    profondeur: float | None
    temperature: float | None
    salinite: float | None
    turbidite: float | None

    @property
    def exploitable(self) -> bool:
        """L'instant porte-t-il au moins une grandeur exploitable ?"""
        return any(
            valeur is not None
            for valeur in (self.profondeur, self.temperature, self.salinite, self.turbidite)
        )


class _AdaptateurNdbcOcean:
    """L'archive océanographique d'une bouée, pour une année.

    L'archive est un **fichier gzippé unique** : pas de pagination, et
    l'exhaustivité est **indéclarée** — la source ne dit pas ce qu'elle
    aurait pu rendre.
    """

    def __init__(self, station: str, annee: str) -> None:
        self.station = station
        self.annee = annee

    @property
    def source(self):
        from torne.contracts.observation import Source

        return Source(
            source_id=SOURCE_ID,
            producer=PRODUCTEUR,
            dataset=f"NDBC oceanographic archive — station {self.station}, {self.annee}",
            access_point="https://www.ndbc.noaa.gov/data/historical/ocean/",
            license="domaine public — œuvre du gouvernement des États-Unis (NOAA/NDBC)",
            revision_policy=(
                "Les archives sont rééditées et les contrôles de qualité de "
                "NOAA s'y appliquent ; aucune date de publication par valeur "
                "n'est publiée : la publication est INCONNUE (classe N)."
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
        """La question : l'archive de la bouée pour l'année demandée."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=(
                "https://www.ndbc.noaa.gov/data/historical/ocean/"
                f"{self.station}o{self.annee}.txt.gz"
            ),
            method="GET",
            label=f"ndbc:ocean:{self.station}:{self.annee}",
        )

    def next_request(self, request: AcquisitionRequest, response: HttpResponse):
        """Pas de page suivante."""
        return None

    def verdict_conformite(self, request: AcquisitionRequest, response: HttpResponse):
        """Le corps est-il bien l'archive annoncée ?

        Deux critères : le format **gzip** (signature `1f 8b`) et la présence
        de l'en-tête de colonnes attendu. Un index de répertoire servi avec
        le code 200 ne passe pas le premier.
        """
        criteres: dict[str, CritereConformite] = {}
        if response.body[:2] == b"\x1f\x8b":
            criteres["gzip"] = CritereConformite(
                demande="a gzip archive",
                verifie=True,
                recu="the body starts with the gzip signature",
                conforme=True,
            )
        else:
            criteres["gzip"] = CritereConformite(
                demande="a gzip archive",
                verifie=True,
                recu=f"the body starts with {response.body[:8]!r}, not with the gzip signature",
                conforme=False,
            )
        try:
            texte = gzip.decompress(response.body).decode("utf-8", errors="replace")
        except OSError as erreur:
            criteres["gzip"] = CritereConformite(
                demande="a gzip archive that can be decompressed",
                verifie=True,
                recu=f"the body is not decompressible: {erreur}",
                conforme=False,
            )
            return verdict_from_criteria(criteres)

        entete = next(
            (ligne for ligne in texte.splitlines() if ligne.startswith("#") and "DEPTH" in ligne),
            "",
        )
        criteres["colonnes"] = CritereConformite(
            demande="a header naming the measured columns",
            verifie=True,
            recu=" ".join(entete.split())[:120]
            if entete
            else "the archive carries no column header",
            conforme=bool(entete),
        )
        return verdict_from_criteria(criteres)


def _nombre(brut: str) -> float | None:
    """La valeur, ou `None` quand elle est la sentinelle d'absence."""
    try:
        valeur = float(brut)
    except ValueError:
        return None
    if valeur in SENTINELLES:
        return None
    return valeur


def _lire(texte: str) -> tuple[list[Mesure], dict[str, int]]:
    """Les mesures de l'archive, et le compte de ce qui a été traité absent."""
    mesures: list[Mesure] = []
    absents: Counter[str] = Counter()
    for ligne in texte.splitlines():
        if not ligne or ligne.startswith("#"):
            continue
        morceaux = ligne.split()
        if len(morceaux) < 13:
            continue
        try:
            instant = datetime(
                int(morceaux[0]),
                int(morceaux[1]),
                int(morceaux[2]),
                int(morceaux[3]),
                int(morceaux[4]),
                tzinfo=UTC,
            )
        except ValueError:
            continue
        valeurs: dict[str, float | None] = {}
        for nom, index in INDICES.items():
            if index < len(morceaux):
                valeurs[nom] = _nombre(morceaux[index])
                if valeurs[nom] is None:
                    absents[nom] += 1
        mesures.append(
            Mesure(
                instant=instant,
                profondeur=valeurs.get("profondeur"),
                temperature=valeurs.get("temperature_eau"),
                salinite=valeurs.get("salinite"),
                turbidite=valeurs.get("turbidite"),
            )
        )
    return mesures, dict(absents)


def main(argv: list[str]) -> int:
    """L'acquisition, la lecture, le profil."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    station = argv[1] if len(argv) > 1 else "44042"
    annee = argv[2] if len(argv) > 2 else "2025"

    racine = Path(tempfile.mkdtemp(prefix="torne-marine-001-"))
    print(f"preuve brute : {racine}")
    magasin = FileRawStore(racine)
    transport = HttpTransport(timeout=90.0)

    adaptateur = _AdaptateurNdbcOcean(station, annee)
    demande = adaptateur.initial_request()
    reponse = transport.send(demande)
    verdict = adaptateur.verdict_conformite(demande, reponse)
    print(
        f"  {station} {annee} : HTTP {reponse.status_code} · "
        f"{reponse.content_type} · {len(reponse.body)} octets · "
        f"conformité {verdict.conformite.value}"
    )
    if verdict.motif:
        print(f"    motif : {verdict.motif}")
    if verdict.conformite is not Conformite.CONFORME:
        raise SystemExit("l'archive n'est pas conforme : rien n'est lu")

    piece = magasin.put(
        reponse.body,
        source_id=SOURCE_ID,
        key=f"{station}o{annee}.txt.gz",
        media_type=reponse.content_type,
        acquired_at=datetime.now(UTC),
    )
    print(f"  preuve : {piece.evidence_id[:16]}… ({str(piece.content_sha256)[:16]}…)")

    texte = gzip.decompress(reponse.body).decode("utf-8", errors="replace")
    mesures, absents = _lire(texte)
    if not mesures:
        raise SystemExit("aucune mesure lue")
    mesures.sort(key=lambda mesure: mesure.instant)

    instants = sorted({mesure.instant for mesure in mesures})
    premier, dernier = instants[0], instants[-1]
    ecarts = [
        (suivant - precedent).total_seconds() for precedent, suivant in itertools.pairwise(instants)
    ]
    cadence = statistics.median(ecarts) if ecarts else 0.0
    avec_salinite = [m for m in mesures if m.salinite is not None]
    avec_temperature = [m for m in mesures if m.temperature is not None]

    print("\n1. la couverture")
    print(f"  {len(mesures)} lignes · {len(instants)} instants distincts")
    print(f"  du {premier.isoformat()} au {dernier.isoformat()}")
    print(
        f"  cadence observée : une mesure toutes les {cadence / 60:.1f} min "
        f"(médiane ; {len(instants)} instants sur "
        f"{(dernier - premier).total_seconds() / 86400:.1f} jours)"
    )
    print("  valeurs traitées comme absentes, par grandeur :")
    for nom, nombre in sorted(absents.items()):
        print(f"    {nom:<16} {nombre}")

    if avec_salinite:
        print("\n2. la salinité")
        salinites = [m.salinite for m in avec_salinite]
        print(
            f"  min {min(salinites):.2f} · max {max(salinites):.2f} · "
            f"médiane {statistics.median(salinites):.2f} psu · n = {len(salinites)}"
        )
        par_mois: dict[int, list[float]] = defaultdict(list)
        for mesure in avec_salinite:
            par_mois[mesure.instant.month].append(mesure.salinite)
        cycle = " · ".join(
            f"{mois:02d}:{statistics.fmean(valeurs):.2f}"
            for mois, valeurs in sorted(par_mois.items())
        )
        print(f"  cycle mensuel moyen (psu) : {cycle}")

        print("\n3. les dessalements les plus forts sur 24 h")
        par_jour = {m.instant.date(): m.salinite for m in avec_salinite}
        baisses: list[tuple[float, object, object]] = []
        jours = sorted(par_jour)
        for avant, apres in itertools.pairwise(jours):
            if (apres - avant).days != 1:
                continue
            baisses.append((par_jour[apres] - par_jour[avant], avant, apres))
        baisses.sort()
        for delta, avant, apres in baisses[:5]:
            print(f"  {avant} → {apres} : {delta:+.2f} psu")

    if avec_temperature:
        temperatures = [m.temperature for m in avec_temperature]
        print("\n4. la température de l'eau")
        print(
            f"  min {min(temperatures):.2f} · max {max(temperatures):.2f} · "
            f"médiane {statistics.median(temperatures):.2f} °C"
        )

    if avec_salinite and avec_temperature:
        par_inst_sal = {m.instant: m.salinite for m in avec_salinite}
        par_inst_temp = {m.instant: m.temperature for m in avec_temperature}
        communs = sorted(set(par_inst_sal) & set(par_inst_temp))
        if len(communs) > 30:
            xs = [par_inst_sal[i] for i in communs]
            ys = [par_inst_temp[i] for i in communs]
            correlation = _correlation(xs, ys)
            print(
                f"\n5. salinité et température : corrélation {correlation:+.3f} "
                f"sur {len(communs)} instants appariés"
            )

    print(f"\npreuve brute : {racine}")
    return 0


def _correlation(xs: list[float], ys: list[float]) -> float:
    """La corrélation de Pearson, calculée sans dépendance."""
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    numerateur = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0.0 or dy == 0.0:
        return 0.0
    return numerateur / (dx * dy)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
