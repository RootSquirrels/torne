"""Sémantique temporelle — exécution de `docs/CONTRATS_FONDAMENTAUX.md` §3.

Trois dimensions **indépendantes et non interchangeables** :

| Dimension | Question |
|---|---|
| `VALID_TIME` | quand le fait est vrai ? |
| `KNOWN_AT` | quand la source l'a-t-elle rendu public ? |
| `INGESTED_AT` | quand TORNE l'a-t-il acquis ? |

`usable_at` est une **fonction dérivée** : `max(KNOWN_AT, INGESTED_AT)`. Elle
n'est jamais stockée (INV-08, INV-09).

Trois états de la connaissance de publication (contrat §3.9), et une seule règle
d'admission :

- `ESTABLISHED` — l'instant de publication initial est connu ;
- `BOUNDED` — seule une borne inférieure est connue : admissible **à partir**
  de la borne, pas avant ;
- `UNKNOWN` — ni instant ni borne : **jamais** admissible en reconstitution
  point-in-time.

La publication inconnue n'est jamais remplacée par la date d'ingestion : ce
serait un comblement par supposition, interdit par `docs/CONTRATS_FONDAMENTAUX.md` §3.9.

Aucun instant n'est stocké sans fuseau : le refus est à l'entrée (INV-15). Une
date civile n'est jamais dégradée en instant par défaut (§3.3) : la conversion
exige un fuseau explicite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, tzinfo
from enum import StrEnum


class PublicationState(StrEnum):
    """Ce que l'on sait de la date de publication dans la source (§3.9)."""

    ESTABLISHED = "established"
    BOUNDED = "bounded"
    UNKNOWN = "unknown"


class AcquisitionKind(StrEnum):
    """Origine de l'acquisition d'une observation (§3.10, INV-14)."""

    ACQUIRED = "acquired"
    ARCHIVE_REIMPORT = "archive_reimport"


class ReplayMode(StrEnum):
    """Lecture temporelle du corpus (§3.10)."""

    OPERATIONAL = "operational"
    PUBLIC = "public"
    DESCRIPTIVE = "descriptive"


def to_utc(value: datetime, *, name: str = "instant") -> datetime:
    """Renvoie `value` en UTC. Refuse un instant sans fuseau (INV-15)."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{name} : un instant sans fuseau est refusé à l'entrée (INV-15)")
    return value.astimezone(UTC)


def civil_day_to_instant(day: date, zone: tzinfo, *, name: str = "date civile") -> datetime:
    """Convertit une date civile en instant, à fuseau explicite.

    Le contrat §3.3 refuse qu'une date civile se dégrade en instant par
    défaut : le fuseau est un paramètre de la décision, jamais une convention
    implicite de l'exécutant.
    """
    if not isinstance(day, date) or isinstance(day, datetime):
        raise TypeError(f"{name} : une date civile est attendue, pas un instant")
    if zone is None:
        raise ValueError(f"{name} : le fuseau est un paramètre explicite (§3.3)")
    return datetime.combine(day, time.min, tzinfo=zone)


@dataclass(frozen=True, slots=True)
class TemporalStamp:
    """Les trois dimensions temporelles d'un fait, et son état de publication.

    `publication` vaut `UNKNOWN` par défaut : l'ignorance est le choix sûr, et
    une publication jamais établie reste non admissible en reconstitution
    point-in-time (INV-10).
    """

    valid_time: datetime | None = None
    known_at: datetime | None = None
    ingested_at: datetime | None = None
    publication: PublicationState = PublicationState.UNKNOWN
    publication_lower_bound: datetime | None = None
    acquisition: AcquisitionKind = AcquisitionKind.ACQUIRED

    def __post_init__(self) -> None:
        object.__setattr__(self, "valid_time", _utc_optional(self.valid_time, "valid_time"))
        object.__setattr__(self, "known_at", _utc_optional(self.known_at, "known_at"))
        object.__setattr__(self, "ingested_at", _utc_optional(self.ingested_at, "ingested_at"))
        object.__setattr__(
            self,
            "publication_lower_bound",
            _utc_optional(self.publication_lower_bound, "publication_lower_bound"),
        )

        if self.publication is PublicationState.ESTABLISHED and self.known_at is None:
            raise ValueError(
                "publication « établie » exige l'instant de publication initial (KNOWN_AT)"
            )
        if self.publication is PublicationState.BOUNDED:
            if self.publication_lower_bound is None:
                raise ValueError("publication « bornée » exige une borne inférieure")
            if self.known_at is not None:
                raise ValueError("publication « bornée » et publication établie sont exclusives")
        if self.publication is PublicationState.UNKNOWN and (
            self.known_at is not None or self.publication_lower_bound is not None
        ):
            raise ValueError("publication « inconnue » ne peut porter ni instant ni borne (INV-10)")

    @property
    def has_temporal_incoherence(self) -> bool:
        """`INGESTED_AT` antérieur à `KNOWN_AT` : l'une des deux dates est fausse.

        §3.2 : c'est un cas d'erreur, pas un cas d'exploit. La donnée n'est pas
        refusée à la construction — elle est **signalée** par cette propriété, et
        elle n'est jamais exploitable (`usable_at` vaut alors `None`).
        """
        if self.known_at is None or self.ingested_at is None:
            return False
        return self.ingested_at < self.known_at

    @property
    def usable_at(self) -> datetime | None:
        """Instant d'utilisabilité : fonction dérivée, jamais stockée (INV-08).

        `max(KNOWN_AT, INGESTED_AT)` quand la publication est établie,
        `max(borne, INGESTED_AT)` quand elle est bornée, et `None` quand elle
        est inconnue — une information dont la publication est inconnue n'est
        jamais admissible en reconstitution point-in-time.

        Une incohérence temporelle (`INGESTED_AT < KNOWN_AT`) donne également
        `None` : la donnée est douteuse, donc signalée et non exploitée (§3.2).
        """
        if self.ingested_at is None:
            return None
        if self.has_temporal_incoherence:
            return None
        if self.publication is PublicationState.ESTABLISHED:
            return max(self.known_at, self.ingested_at)
        if self.publication is PublicationState.BOUNDED:
            return max(self.publication_lower_bound, self.ingested_at)
        return None

    def is_visible_at(self, asof: datetime, *, mode: ReplayMode = ReplayMode.PUBLIC) -> bool:
        """L'information était-elle admissible à l'instant `asof` ?

        En `OPERATIONAL`, un réimport d'archive est exclu : il porte la date
        d'acquisition d'origine et ne se présente pas comme acquis par TORNE
        au moment du réimport (INV-14).
        """
        if mode is ReplayMode.OPERATIONAL and self.acquisition is AcquisitionKind.ARCHIVE_REIMPORT:
            return False
        usable = self.usable_at
        return usable is not None and usable <= to_utc(asof, name="asof")

    def is_usable(self) -> bool:
        """L'information est-elle admissible, à quelque instant que ce soit ?"""
        return self.usable_at is not None


def _utc_optional(value: datetime | None, name: str) -> datetime | None:
    return None if value is None else to_utc(value, name=name)


__all__ = [
    "AcquisitionKind",
    "PublicationState",
    "ReplayMode",
    "TemporalStamp",
    "civil_day_to_instant",
    "to_utc",
]
