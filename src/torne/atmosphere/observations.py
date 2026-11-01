"""La couche sémantique atmosphérique : de la ligne GHCN-Daily à l'observation.

Ce que NCEI publie, et ce que TORNE en fait
--------------------------------------------

GHCN-Daily publie, pour chaque station et chaque jour, des **valeurs entières**
et des **drapeaux de mesure, de qualité et de source**. Trois conversions sont
nécessaires, et chacune est une décision — jamais une évidence :

- **L'échelle.** Une température est publiée en dixièmes de degré Celsius
  (`173` = 17,3 °C), une précipitation en dixièmes de millimètre, une pression
  en dixièmes de hectopascal. L'échelle de chaque élément est celle du
  `readme.txt` de GHCN-Daily (version 3.35), reproduite ici ; un élément dont
  l'échelle n'est pas connue est refusé plutôt que supposé.
- **Le jour.** La source publie une **date civile**, jamais un instant. La
  conversion en instant exige un fuseau, et le fuseau est un **argument** :
  NCEI ne publie aucun fuseau, et l'abréviation du pays de la station n'en est
  pas un.
- **La publication.** La source ne dit **jamais** quand une valeur est
  devenue publique. Elle ne dit même pas qu'elle l'a été : elle réédite
  l'archive chaque jour, et une valeur peut avoir été corrigée entre deux
  versions sans que la date de la correction soit connue.

Les drapeaux ne sont **jamais interprétés à la volée** : ils sont conservés
tels quels dans la mesure (`Measurement`), et la lecture qu'en fait la couche
sémantique est explicite et documentée. C'est important, parce que le
vocabulaire de qualité du socle est **fermé** (cinq états) et que le vocabulaire
de NCEI en compte bien davantage : voir `QUALITE_INCONNUE`.

La qualité : ce que le vocabulaire fermé ne sait pas dire
----------------------------------------------------------

NCEI signale les valeurs **mesurées mais refusées** par ses contrôles
(drapeau de qualité non vide : « failed spatial consistency check », « failed
climatological outlier check »…). Ces valeurs **sont** des mesures : elles ne
sont pas nulles, et elles ne sont pas absentes. Mais le socle ne sait dire
que cinq choses — `DECLARED`, `SOURCE_ESTIMATED`, `PROVISIONAL`, `APPROVED`,
`UNKNOWN` — et aucune ne veut dire « mesurée, et le contrôle a échoué ».

La mesure est donc conservée, le drapeau conservé, et la qualité canonique
est `UNKNOWN` : le socle **ne prétend pas** que la valeur est approuvée.
Ce n'est pas un défaut du décodeur, c'est une **limite du vocabulaire**, et
elle est consignée comme telle dans le dossier ATMO-001 (`docs/ATMO-001.md`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, tzinfo
from typing import Any

from ..contracts.observation import Observation, QualityStatus
from ..contracts.time import PublicationState, TemporalStamp, civil_day_to_instant
from ..contracts.validity import MissingReason, PointValidity

DAY_CONVENTION = "day_start_local"
"""La convention retenue pour une date civile GHCN-Daily.

La valeur d'un jour est attribuée au **début du jour civil local** de la
station. NCEI ne publie pas la fenêtre d'agrégation qu'il a employée : cette
convention est donc une convention **déclarée** de la couche d'interprétation,
écrite dans la méthode de tout produit qui l'emploie, et jamais supposée en
silence.
"""

MISSING_VALUE = -9999
"""La sentinelle de valeur manquante de GHCN-Daily.

Dans les fichiers `.dly` elle vaut `-9999` ; dans les CSV de station, une
valeur absente est une **cellule vide**. Les deux sont traitées comme des
absences, jamais comme des mesures.
"""

#: L'échelle de chaque élément, d'après le `readme.txt` de GHCN-Daily v3.35.
#: `diviseur` vaut 1 quand l'unité est déjà celle du socle.
ELEMENT_UNITES: Mapping[str, tuple[str, float]] = {
    "TMAX": ("degC", 10.0),
    "TMIN": ("degC", 10.0),
    "TAVG": ("degC", 10.0),
    "PRCP": ("mm", 10.0),
    "SNOW": ("mm", 1.0),
    "SNWD": ("mm", 1.0),
    "AWND": ("m/s", 10.0),
    "ASLP": ("hPa", 10.0),
    "ASTP": ("hPa", 10.0),
    "PSUN": ("percent", 1.0),
    "RHAV": ("percent", 1.0),
    "RHMN": ("percent", 1.0),
    "RHMX": ("percent", 1.0),
}
"""Ce que NCEI publie pour chaque élément : l'unité du socle, et le diviseur
à appliquer à la valeur brute. Un élément absent de cette table n'a pas
d'échelle connue : il est refusé."""

#: Les drapeaux de mesure que NCEI publie (extraits du `readme.txt` v3.35).
DRAPEAUX_MESURE: Mapping[str, str] = {
    "": "no measurement information applicable",
    "A": "precipitation total from one report of 6-hour precipitation amount",
    "B": "precipitation total summed from two 12-hour totals",
    "C": "precipitation total summed from 3 reports of 6-hour precipitation amount",
    "D": "precipitation total summed from four six-hour totals",
    "E": "precipitation total from 1 report of 12-hour precipitation amount",
    "F": "precipitation total from the summation of 2 reports of 12-hour totals",
    "G": "precipitation from 1 report of 24-hour precipitation amount",
    "H": "for TMAX/TMIN/TAVG, highest or lowest hourly temperature",
    "I": "station did not report precipitation data and noted no precipitation",
    "K": "converted from knots",
    "L": "temperature appears to be lagged with respect to reported hour",
    "O": "converted from oktas",
    "P": "identified as 'missing presumed zero' in DSI 3200 and 3206",
    "T": "trace of precipitation, snowfall, or snow depth",
    "W": "converted from 16-point WBAN code",
}

#: Les drapeaux de qualité que NCEI publie (extraits du `readme.txt` v3.35).
DRAPEAUX_QUALITE: Mapping[str, str] = {
    "": "did not fail any quality assurance check",
    "D": "failed duplicate check",
    "G": "failed gap check",
    "I": "failed internal consistency check",
    "K": "failed streak/frequent-value check",
    "L": "failed check on length of multiday period",
    "M": "failed megaconsistency check",
    "N": "failed naught check",
    "O": "failed climatological outlier check",
    "R": "failed lagged range check",
    "S": "failed spatial consistency check",
    "T": "failed temporal consistency check",
    "W": "temperature too warm for snow",
    "X": "failed bounds check",
    "Z": "flagged as a result of an official Datzilla investigation",
}

QUALITE_INCONNUE = QualityStatus.UNKNOWN
"""La qualité canonique d'une valeur dont le contrôle a échoué.

Le vocabulaire du socle ne dit pas « mesurée et refusée ». `UNKNOWN` est la
seule réponse qui ne **prétend** rien : la valeur est conservée, son drapeau
l'est aussi, et l'analyse downstream peut l'écarter sur cette base.
"""


class InterpretationError(ValueError):
    """La ligne ne dit pas ce qu'elle doit dire.

    Elle est refusée plutôt que devinée : une ligne dont la date ne se lit
    pas, ou dont la station n'est pas celle attendue, ne produit pas
    d'observation — elle produit une erreur visible.
    """


@dataclass(frozen=True, slots=True)
class Station:
    """Ce que la source dit du site lui-même.

    Les coordonnées sont en degrés décimaux ; NCEI ne publie **aucun datum**
    dans son `readme.txt` : il est donc déclaré absent plutôt que supposé
    être WGS 84.
    """

    station_id: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    datum: str | None = None

    @property
    def spatial_ref(self) -> str:
        """Le référentiel spatial : la station, dans les termes de la source."""
        return self.station_id

    def as_dict(self) -> dict[str, Any]:
        """Une vue sérialisable de la station."""
        return {
            "station_id": self.station_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "datum": self.datum,
        }


@dataclass(frozen=True, slots=True)
class Measurement:
    """Une mesure lue dans une ligne : la valeur, et ce que la source dit d'elle.

    Les trois drapeaux sont conservés **tels quels**. Leur lecture
    (`qualite`, `raison_absence`) est explicite et versionnée avec le code ;
    leur conservation, elle, est brute.
    """

    element: str
    valeur: float | None
    unite: str | None
    drapeau_mesure: str | None
    drapeau_qualite: str | None
    drapeau_source: str | None

    @property
    def mesuree(self) -> bool:
        """La source a-t-elle mesuré quelque chose ce jour-là ?"""
        return self.valeur is not None

    @property
    def qualite(self) -> QualityStatus:
        """La qualité canonique, dans le vocabulaire fermé du socle."""
        if not self.mesuree:
            return QualityStatus.UNKNOWN
        if self.drapeau_qualite:
            return QUALITE_INCONNUE
        return QualityStatus.DECLARED

    @property
    def qualite_declaree(self) -> str | None:
        """Ce que NCEI dit du contrôle, en clair, s'il l'a dit."""
        if not self.drapeau_qualite:
            return None
        return DRAPEAUX_QUALITE.get(self.drapeau_qualite_normalise(), "")

    def drapeau_qualite_normalise(self) -> str:
        """Le drapeau de qualité, normalisé (vide si absent)."""
        return (self.drapeau_qualite or "").strip()


@dataclass(frozen=True, slots=True)
class Ligne:
    """Une ligne du CSV de station, lue."""

    station: Station
    jour: date
    elements: Mapping[str, Measurement]


def _texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None


def _nombre(valeur: Any) -> float | None:
    if valeur is None or isinstance(valeur, bool):
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip()
    if not texte:
        return None
    try:
        return float(texte)
    except ValueError:
        return None


def station_depuis_ligne(ligne: Mapping[str, Any], *, station_id: str) -> Station:
    """La station, lue de la ligne elle-même.

    NCEI répète les coordonnées sur **chaque** ligne : la station est donc
    connue sans avoir à télécharger le référentiel des stations, et l'on peut
    vérifier que la ligne appartient bien à la station demandée.
    """
    identifiant = _texte(ligne.get("STATION")) or station_id
    return Station(
        station_id=identifiant,
        name=_texte(ligne.get("NAME")) or identifiant,
        latitude=_nombre(ligne.get("LATITUDE")),
        longitude=_nombre(ligne.get("LONGITUDE")),
        elevation_m=_nombre(ligne.get("ELEVATION")),
        datum=None,
    )


def ligne_depuis_dictionnaire(
    ligne: Mapping[str, Any],
    *,
    station_id: str,
    elements: Sequence[str],
) -> Ligne:
    """Une ligne du CSV, lue comme une journée de mesures.

    Une date illisible, ou un jour qui ne se laisse pas lire comme une date
    civile, est **refusé** : la ligne ne produit pas d'observation.
    """
    station = station_depuis_ligne(ligne, station_id=station_id)
    if station.station_id.upper() != station_id.upper():
        raise InterpretationError(
            f"the record belongs to station {station.station_id}, not to {station_id}"
        )

    brute = _texte(ligne.get("DATE"))
    if brute is None:
        raise InterpretationError("the record carries no date")
    try:
        jour = date.fromisoformat(brute)
    except ValueError as erreur:
        raise InterpretationError(f"'DATE' is not a civil date: {brute}") from erreur

    mesures: dict[str, Measurement] = {}
    for element in elements:
        mesure, _unite = _mesure(ligne, element)
        mesures[element] = mesure
    return Ligne(station=station, jour=jour, elements=mesures)


def _mesure(ligne: Mapping[str, Any], element: str) -> tuple[Measurement, str | None]:
    """La mesure d'un élément dans une ligne, et son unité."""
    echelle = ELEMENT_UNITES.get(element)
    if echelle is None:
        raise InterpretationError(
            f"the scale of element {element} is unknown: it is not read as a measurement"
        )
    unite, diviseur = echelle

    brute = _texte(ligne.get(element))
    attributs = _texte(ligne.get(f"{element}_ATTRIBUTES")) or ""
    parties = attributs.split(",")
    while len(parties) < 3:
        parties.append("")
    drapeau_mesure, drapeau_qualite, drapeau_source = (p.strip() or None for p in parties[:3])

    if brute is None:
        return (
            Measurement(
                element=element,
                valeur=None,
                unite=unite,
                drapeau_mesure=drapeau_mesure,
                drapeau_qualite=drapeau_qualite,
                drapeau_source=drapeau_source,
            ),
            unite,
        )

    try:
        nombre = float(brute)
    except ValueError as erreur:
        raise InterpretationError(f"the value of {element} is not a number: {brute}") from erreur
    if nombre == MISSING_VALUE:
        return (
            Measurement(
                element=element,
                valeur=None,
                unite=unite,
                drapeau_mesure=drapeau_mesure,
                drapeau_qualite=drapeau_qualite,
                drapeau_source=drapeau_source,
            ),
            unite,
        )

    return (
        Measurement(
            element=element,
            valeur=nombre / diviseur,
            unite=unite,
            drapeau_mesure=drapeau_mesure,
            drapeau_qualite=drapeau_qualite,
            drapeau_source=drapeau_source,
        ),
        unite,
    )


def observation_depuis_ligne(
    ligne: Ligne,
    element: str,
    *,
    source_id: str,
    evidence_id: str,
    zone: tzinfo,
    acquired_at: datetime,
) -> Observation:
    """L'observation d'un élément, pour un jour, dans une station.

    `zone` est un **argument** : NCEI ne publie aucun fuseau, et la date
    civile qu'il publie n'en est pas un.
    """
    mesure = ligne.elements.get(element)
    if mesure is None:
        raise InterpretationError(f"the record does not carry the element {element}")

    instant = civil_day_to_instant(ligne.jour, zone, name="observation day")
    identifiant = f"{ligne.station.station_id}:{element}:{ligne.jour.isoformat()}"

    if not mesure.mesuree:
        return Observation(
            observation_id=identifiant,
            source_id=source_id,
            quantity=element,
            unit=mesure.unite or "unknown",
            temporal=TemporalStamp(
                valid_time=instant,
                known_at=None,
                ingested_at=acquired_at,
                publication=PublicationState.UNKNOWN,
            ),
            evidence_id=evidence_id,
            value=None,
            validity=PointValidity.MISSING,
            missing_reason=MissingReason.NOT_MEASURED,
            spatial_ref=ligne.station.spatial_ref,
            quality_status=QualityStatus.UNKNOWN,
        )

    return Observation(
        observation_id=identifiant,
        source_id=source_id,
        quantity=element,
        unit=mesure.unite or "unknown",
        temporal=TemporalStamp(
            valid_time=instant,
            known_at=None,
            ingested_at=acquired_at,
            publication=PublicationState.UNKNOWN,
        ),
        evidence_id=evidence_id,
        value=mesure.valeur,
        validity=PointValidity.VALID,
        spatial_ref=ligne.station.spatial_ref,
        quality_status=mesure.qualite,
    )


def observations(
    lignes: Iterable[Ligne],
    element: str,
    *,
    source_id: str,
    evidence_id: str,
    zone: tzinfo,
    acquired_at: datetime,
) -> tuple[Observation, ...]:
    """Toutes les observations d'un élément, dans l'ordre du temps.

    Le fichier de NCEI n'est **pas** garanti trié par date : l'ordre du temps
    est établi ici, une fois, plutôt que supposé par chaque consommateur.
    """
    poses = [
        (
            ligne.jour,
            observation_depuis_ligne(
                ligne,
                element,
                source_id=source_id,
                evidence_id=evidence_id,
                zone=zone,
                acquired_at=acquired_at,
            ),
        )
        for ligne in lignes
    ]
    poses.sort(key=lambda pose: pose[0])
    return tuple(observation for _, observation in poses)


__all__ = [
    "DAY_CONVENTION",
    "DRAPEAUX_MESURE",
    "DRAPEAUX_QUALITE",
    "ELEMENT_UNITES",
    "MISSING_VALUE",
    "QUALITE_INCONNUE",
    "InterpretationError",
    "Ligne",
    "Measurement",
    "Station",
    "ligne_depuis_dictionnaire",
    "observation_depuis_ligne",
    "observations",
    "station_depuis_ligne",
]
