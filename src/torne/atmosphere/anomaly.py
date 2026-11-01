"""Climatologie, anomalies et régimes thermiques.

Ce module répond à une question précise : **qu'est-ce qu'une journée
anormale, à cette station, et à cette place dans l'année ?**

Trois objets, dans cet ordre :

1. **La climatologie** — ce que chaque jour de l'année vaut *habituellement*,
   calculé sur une période de référence observée. Elle porte le **nombre
   d'années** qui ont-console été observées : c'est ce qui dit si la référence
   est épaisse ou mince, et une référence mince ne s_CACHE pas derrière une
   moyenne.
2. **L'anomalie** — l'écart à cette habitude, standardisé par l'écart-type du
   même jour de l'année. Standardiser n'est pas cosmetic : la variabilité
  thermique n'est pas la même en janvier qu'en juillet, et une anomalie en
   degrés n'est pas comparable d'une saison à l'autre.
3. **Le régime** — la classe d'une journée : normale, froide, chaude, ou
   **épisode** quand elle s'enchaîne. Les seuils sont **déclarés**, pas
   découverts : un « jour chaud » défini à +1 écart-type et un défini à +2
   ne racontent pas la même chose, et le seuil employé est écrit dans la
   méthode de tout ce qui en dépend.

Rien ici n'est un résultat : ce sont des **grandeurs calculées**, avec leur
règle de calcul versionnée, que n'importe qui peut recalculer.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, tzinfo
from typing import Any

from ..contracts.observation import Observation, QualityStatus
from ..contracts.validity import PointValidity

METHOD = "day-of-year standardised anomaly index"
"""La règle de calcul. Elle est nommée : un index sans règle n'est pas
reproductible."""

VERSION = "1.0.0"
"""Version de la règle. Une règle qui change sans changer de version rend
tout produit antérieur illisible."""

SEUIL_FROID = -1.0
"""Un jour est *froid* sous ce score d'anomalie standardisé."""

SEUIL_CHAUD = 1.0
"""Un jour est *chaud* au-dessus de ce score d'anomalie standardisé."""

SEUIL_EXTREME = 2.0
"""Au-delà, le jour est *extrême* — chaud ou froid."""

LONGUEUR_MINIMALE_EPISODE = 3
"""Durée minimale d'un épisode, en jours.

Trois jours consécutifs est la définition **usuelle** d'un épisode de chaleur
en climatologie, mais c'est une convention de la discipline, pas une loi de la
nature : elle est déclarée ici, elle est un paramètre de chaque calcul, et
rien dans les résultats ne la présente comme discovered.
"""


def jour_civil(instant: datetime, zone: tzinfo | None = None) -> date:
    """Le **jour civil** d'un instant, dans la zone donnée.

    Ce n'est pas un détail. Une observation de minuit local, en France, est
    un instant du **jour précédent** en UTC : le 2 mars 1945 à 00:00 à Paris
    est le 1ᵉʳ mars 1945 à 23:00 UTC. Indexer une climatologie sur le jour
    UTC comparerait donc chaque journée à l'habitude du jour **précédent** —
    un décalage d'un jour, invisible à la lecture, et qui fausse le signe des
    anomalies en bordure de chaque année.

    Sans zone, le jour UTC est pris : c'est un choix explicite, et il n'est
    correct que si la zone de la station est à l'ouest de Greenwich.
    """
    return (instant.astimezone(zone) if zone is not None else instant).date()


@dataclass(frozen=True, slots=True)
class ClimatologieJour:
    """L'habitude d'un jour de l'année.

    `count` est le nombre d'années où ce jour a été observé : c'est ce qui
    rend la dispersion crédible, et c'est ce qui dit au lecteur à quel point
    la référence est mince.
    """

    month: int
    day: int
    mean: float
    standard_deviation: float
    count: int


@dataclass(frozen=True, slots=True)
class Climatologie:
    """La climatologie journalière d'une période de référence."""

    by_day: Mapping[tuple[int, int], ClimatologieJour]
    reference_start: datetime
    reference_end: datetime
    years: int

    def __len__(self) -> int:
        return len(self.by_day)

    def par(self, month: int, day: int) -> ClimatologieJour | None:
        """L'habitude d'un jour de l'année, quand elle a été observée."""
        return self.by_day.get((month, day))

    def par_jour(self, jour: date) -> ClimatologieJour | None:
        """L'habitude d'un jour civil."""
        return self.by_day.get((jour.month, jour.day))


@dataclass(frozen=True, slots=True)
class Episode:
    """Une suite de jours consécutifs d'un même régime."""

    regime: str
    debut: date
    fin: date
    longueur: int
    moyenne: float

    def as_dict(self) -> dict[str, Any]:
        """Une vue sérialisable de l'épisode."""
        return {
            "regime": self.regime,
            "debut": self.debut.isoformat(),
            "fin": self.fin.isoformat(),
            "longueur": self.longueur,
            "moyenne": self.moyenne,
        }


def climatologie(
    observations: Iterable[Observation],
    *,
    reference_start: date | datetime | None = None,
    reference_end: date | datetime | None = None,
    minimum_count: int = 1,
    zone: tzinfo | None = None,
) -> Climatologie:
    """La climatologie journalière d'un enregistrement observé.

    Seules les observations valides entrent dans le calcul : un jour que la
    source n'a pas mesuré n'est pas un jour à la moyenne. Le jour retenu est
    le **jour civil local** de l'observation : `zone` le définit, et sans
    zone le jour UTC est pris — ce qui n'est correct que pour une station à
    l'ouest de Greenwich.

    La période de référence s'exprime en **jours civils** : c'est le même
    calendrier que celui des clés de la climatologie, et un jour civil ne
    peut pas à la fois entrer dans la fenêtre et être indexé ailleurs. Un
    `datetime` est accepté et converti dans la zone donnée.

    Quand une période de référence est donnée, **seules les observations de
    cette période entrent dans la climatologie**. La période de référence est
    un filtre, pas une étiquette : une climatologie « 1991-2020 » calculée
    sur toute la série ne serait pas une climatologie de 1991-2020, et
    l'écart entre les deux n'est pas une détail d'écriture — c'est ce qui
    décide du signe des anomalies.

    `minimum_count` permet d'exiger une référence d'une épaisseur donnée :
    par défaut, un jour observé une seule fois entre dans la climatologie, et
    la dispersion qu'on en dérive est alors nulle — ce qui est un fait, pas
    une erreur, mais un fait qui doit être visible.
    """
    debut_civil = _borne_civil(reference_start, zone)
    fin_civil = _borne_civil(reference_end, zone)

    groupes: dict[tuple[int, int], list[float]] = {}
    for observation in observations:
        if observation.validity is not PointValidity.VALID or observation.value is None:
            continue
        instant = observation.temporal.valid_time
        if instant is None:
            continue
        jour = jour_civil(instant, zone)
        if debut_civil is not None and jour < debut_civil:
            continue
        if fin_civil is not None and jour > fin_civil:
            continue
        groupes.setdefault((jour.month, jour.day), []).append(float(observation.value))

    par_jour: dict[tuple[int, int], ClimatologieJour] = {}
    for (mois, jour), valeurs in groupes.items():
        if len(valeurs) < minimum_count:
            continue
        par_jour[(mois, jour)] = ClimatologieJour(
            month=mois,
            day=jour,
            mean=statistics.fmean(valeurs),
            standard_deviation=statistics.stdev(valeurs) if len(valeurs) > 1 else 0.0,
            count=len(valeurs),
        )

    instants = [
        observation.temporal.valid_time
        for observation in observations
        if observation.temporal.valid_time is not None
    ]
    debut = reference_start or (min(instants) if instants else None)
    fin = reference_end or (max(instants) if instants else None)
    annees = _annees(debut, fin)

    return Climatologie(
        by_day=par_jour,
        reference_start=_instant(debut),
        reference_end=_instant(fin),
        years=annees,
    )


def anomalies(
    observations: Sequence[Observation],
    reference: Climatologie,
    *,
    zone: tzinfo | None = None,
) -> list[tuple[Observation, float]]:
    """Les anomalies standardisées des observations, contre la référence.

    Un jour dont la climatologie est inconnue — un jour jamais observé sur la
    période de référence — n'est **pas** noté : il serait noté contre rien.
    Un jour à dispersion nulle non plus : l'écart normalisé y est indéfini.

    `zone` définit le jour civil auquel la climatologie est indexée : sans
    zone, le jour UTC est pris, et la note porte alors sur le jour civil
    **précédent** pour une station à l'est de Greenwich.
    """
    notes: list[tuple[Observation, float]] = []
    for observation in observations:
        if observation.validity is not PointValidity.VALID or observation.value is None:
            continue
        instant = observation.temporal.valid_time
        if instant is None:
            continue
        jour = reference.par(*_mois_jour(jour_civil(instant, zone)))
        if jour is None or jour.standard_deviation <= 0.0:
            continue
        notes.append(
            (observation, (float(observation.value) - jour.mean) / jour.standard_deviation)
        )
    return notes


def regimes(
    notes: Sequence[tuple[Observation, float]],
    *,
    seuil_froid: float = SEUIL_FROID,
    seuil_chaud: float = SEUIL_CHAUD,
    seuil_extreme: float = SEUIL_EXTREME,
) -> list[tuple[Observation, str]]:
    """Le régime de chaque journée notée.

    `normal`, `froid`, `chaud`, et les quatre classes extrêmes
    (`tres_froid`, `tres_chaud`). Les seuils sont des **arguments** : la
    fonction ne décide pas de ce qu'est un jour chaud.
    """
    classes: list[tuple[Observation, str]] = []
    for observation, score in notes:
        classes.append((observation, _classe(score, seuil_froid, seuil_chaud, seuil_extreme)))
    return classes


def episodes(
    notes: Sequence[tuple[Observation, float]],
    *,
    regime: str,
    seuil_froid: float = SEUIL_FROID,
    seuil_chaud: float = SEUIL_CHAUD,
    seuil_extreme: float = SEUIL_EXTREME,
    longueur_minimale: int = LONGUEUR_MINIMALE_EPISODE,
    zone: tzinfo | None = None,
) -> tuple[Episode, ...]:
    """Les épisodes d'un régime : suites de jours **consécutifs**.

    La consécutivité est vérifiée sur les **jours civils**, pas sur l'ordre
    des enregistrements : deux jours notés à un jour d'écart ne forment pas
    un épisode de deux jours si le jour intermédiaire n'a pas été noté.

    Les scores sont conservés : la moyenne d'un épisode est la moyenne de ses
    anomalies, pas un zéro de remplissage.
    """
    retenus = [
        (observation, score)
        for observation, score in notes
        if _classe(score, seuil_froid, seuil_chaud, seuil_extreme) == regime
    ]
    retenus.sort(key=lambda paire: paire[0].temporal.valid_time or datetime.min)

    episodes_trouves: list[Episode] = []
    courante: list[tuple[Observation, float]] = []
    for observation, score in retenus:
        instant = observation.temporal.valid_time
        if instant is None:
            continue
        if courante:
            precedent = courante[-1][0].temporal.valid_time
            if precedent is not None:
                ecart = (jour_civil(instant, zone) - jour_civil(precedent, zone)).days
                if ecart != 1:
                    episodes_trouves.extend(_fermer(courante, regime, longueur_minimale, zone))
                    courante = []
        courante.append((observation, score))
    episodes_trouves.extend(_fermer(courante, regime, longueur_minimale, zone))
    return tuple(episodes_trouves)


def _classe(
    score: float,
    seuil_froid: float = SEUIL_FROID,
    seuil_chaud: float = SEUIL_CHAUD,
    seuil_extreme: float = SEUIL_EXTREME,
) -> str:
    """La classe d'un score d'anomalie."""
    if score <= -seuil_extreme:
        return "tres_froid"
    if score >= seuil_extreme:
        return "tres_chaud"
    if score <= seuil_froid:
        return "froid"
    if score >= seuil_chaud:
        return "chaud"
    return "normal"


def temperature_moyenne(
    maximums: Sequence[Observation],
    minimums: Sequence[Observation],
    *,
    quantity: str = "temperature_moyenne",
    zone: tzinfo | None = None,
) -> tuple[Observation, ...]:
    """La température moyenne du jour, appariée jour par jour.

    L'appariement se fait sur le **jour civil** : une journée sans maximum
    ou sans minimum n'a pas de moyenne, et n'est pas comblée par une des
    deux valeurs disponibles.

    La moyenne est une **observation dérivée** : elle est datée comme les
    deux observations dont elle provient, et elle porte la **qualité la plus
    défavorable** des deux — une moyenne calculée sur une valeur que le
    producteur a signalée comme douteuse n'est pas plus sûre que cette
    valeur.
    """
    par_jour_max = _par_jour(maximums, zone)
    par_jour_min = _par_jour(minimums, zone)
    resultat: list[Observation] = []
    for jour in sorted(set(par_jour_max) & set(par_jour_min)):
        observation_max, valeur_max = par_jour_max[jour]
        observation_min, valeur_min = par_jour_min[jour]
        resultat.append(
            Observation(
                observation_id=f"{observation_max.observation_id}:mean",
                source_id=observation_max.source_id,
                quantity=quantity,
                unit=observation_max.unit,
                temporal=observation_max.temporal,
                evidence_id=observation_max.evidence_id,
                value=(valeur_max + valeur_min) / 2.0,
                validity=PointValidity.VALID,
                spatial_ref=observation_max.spatial_ref,
                quality_status=_qualite_pire(
                    observation_max.quality_status, observation_min.quality_status
                ),
            )
        )
    return tuple(resultat)


def _qualite_pire(premier: QualityStatus, second: QualityStatus) -> QualityStatus:
    """La qualité la plus défavorable de deux observations."""
    from ..contracts.observation import QualityStatus

    if QualityStatus.UNKNOWN in (premier, second):
        return QualityStatus.UNKNOWN
    if QualityStatus.PROVISIONAL in (premier, second):
        return QualityStatus.PROVISIONAL
    if QualityStatus.SOURCE_ESTIMATED in (premier, second):
        return QualityStatus.SOURCE_ESTIMATED
    if QualityStatus.APPROVED in (premier, second):
        return QualityStatus.APPROVED
    return QualityStatus.DECLARED


def _par_jour(
    observations: Sequence[Observation],
    zone: tzinfo | None = None,
) -> dict[date, tuple[Observation, float]]:
    """Les observations, indexées par jour civil."""
    table: dict[date, tuple[Observation, float]] = {}
    for observation in observations:
        instant = observation.temporal.valid_time
        if instant is None or observation.value is None:
            continue
        if observation.validity is not PointValidity.VALID:
            continue
        table[jour_civil(instant, zone)] = (observation, float(observation.value))
    return table


def _mois_jour(jour: date) -> tuple[int, int]:
    """Le couple (mois, jour) d'une date."""
    return jour.month, jour.day


def _borne_civil(valeur: date | datetime | None, zone: tzinfo | None) -> date | None:
    """La borne d'une période de référence, exprimée en jour civil."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur.astimezone(zone).date() if zone is not None else valeur.date()
    return valeur


def _fermer(
    courante: list[tuple[Observation, float]],
    regime: str,
    longueur_minimale: int,
    zone: tzinfo | None = None,
) -> list[Episode]:
    """Un groupe de jours consécutifs devient un épisode s'il est assez long."""
    if len(courante) < longueur_minimale:
        return []
    instants = [observation.temporal.valid_time for observation, _ in courante]
    valides = [instant for instant in instants if instant is not None]
    if not valides:
        return []
    jours = [jour_civil(instant, zone) for instant in valides]
    scores = [score for _, score in courante]
    return [
        Episode(
            regime=regime,
            debut=min(jours),
            fin=max(jours),
            longueur=len(courante),
            moyenne=statistics.fmean(scores) if scores else 0.0,
        )
    ]


def _annees(debut: date | datetime | None, fin: date | datetime | None) -> int:
    """Le nombre d'années couvert par une période."""
    if debut is None or fin is None:
        return 0
    return fin.year - debut.year + 1


def _instant(valeur: date | datetime | None) -> datetime:
    """Une date, ramenée à un instant UTC pour la lecture."""
    if valeur is None:
        return datetime.min
    if isinstance(valeur, datetime):
        return valeur
    return datetime.combine(valeur, datetime.min.time(), UTC)


__all__ = [
    "LONGUEUR_MINIMALE_EPISODE",
    "METHOD",
    "SEUIL_CHAUD",
    "SEUIL_EXTREME",
    "SEUIL_FROID",
    "VERSION",
    "Climatologie",
    "ClimatologieJour",
    "Episode",
    "anomalies",
    "climatologie",
    "episodes",
    "regimes",
    "temperature_moyenne",
]
