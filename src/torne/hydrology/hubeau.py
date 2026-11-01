"""The French hydrometry: a Hub'Eau row, read as an Observation.

Hub'Eau's `observations_tr` access point publishes one row per observation, and
each row carries the observation's own coordinates, its measurement status, its
method and its qualification. Reading such a row into TORNE's canonical
observation takes three decisions that the source does not make for us. They are
**declared here**, written into the method of every product built on them, and
never assumed silently.

1. **The discharge carries the unit of its quantity; the stage does not.**
   The source publishes no unit field. `grandeur_hydro = "Q"` designates the
   *débit*, whose unit is the cubic metre per second by the definition of the
   SI derived quantity — so that unit is declared. `grandeur_hydro = "H"`
   designates a height, and a height has no unit of its own: it may be
   published in metres, centimetres or millimetres, and this source says
   nothing about which. The stage is therefore carried with its unit
   **undeclared**, and every statement this layer supports about a stage is a
   statement about the number the source published, not about a length.

2. **The publication instant is unknown, and that is a bound, not a hole.**
   The source never says when a value was made public. It does say when the
   value was observed, and a value cannot have been published before it was
   observed: the publication is therefore **bounded** below by the instant of
   the observation. The canonical contract refuses an unknown publication
   (INV-10, INV-30) — and the bound is exactly what makes these observations
   admissible, without ever claiming to know the publication lag.

3. **Half of the discharge rows carry no station code.** A row without a
   station keeps its site code, its coordinates and its value; it cannot be
   attributed to a station. Nothing is manufactured to fill the gap. Such a row
   is either refused, or kept with its site as its spatial reference, and the
   caller is told which of the two happened.

Every source-native field stays in the raw evidence, verbatim and under its own
name. This module translates at the boundary, and nowhere else.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any

from ..contracts.observation import Observation, QualityStatus
from ..contracts.time import PublicationState, TemporalStamp
from ..contracts.validity import MissingReason, PointValidity

DISCHARGE_UNIT = "m3/s"
"""The unit of the discharge.

The source publishes no unit field. The cubic metre per second is not an
assumption about this source: it is the unit of the quantity the source's own
`grandeur_hydro = "Q"` designates.
"""

STAGE_UNIT = "not declared by the source"
"""The unit of the stage.

The source publishes a number and the name of the quantity, and nothing else.
A height has no unit of its own, so no unit is invented here. The consequence
is stated rather than hidden: no dimensional claim about a stage is admissible
on this source — only claims about the published number.
"""

QUANTITIES: Mapping[str, tuple[str, str]] = {
    "Q": ("discharge", DISCHARGE_UNIT),
    "H": ("stage", STAGE_UNIT),
}
"""The quantity and the unit each published quantity designates."""

_STATUS_LABELS: Mapping[str, QualityStatus] = {
    "validée": QualityStatus.APPROVED,
    "validee": QualityStatus.APPROVED,
    "pré-validée": QualityStatus.PROVISIONAL,
    "pre-validee": QualityStatus.PROVISIONAL,
    "brute": QualityStatus.PROVISIONAL,
}
"""How the agency's own validation label is read.

The **label** is read, not the code: the code is an internal numbering whose
meaning differs between producers, while the label is the statement the agency
publishes about the value. A value the agency has not validated is carried as
provisional — it exists, the agency says so, and it is not established. Any
label this table does not know is carried as `UNKNOWN`: a source that says
something this layer cannot read is not a source that approves.
"""


class InterpretationError(ValueError):
    """The row does not say what it must say.

    It is raised rather than guessed around: a row whose instant cannot be
    placed, or whose value cannot be read, is refused — and the refusal is
    visible.
    """


@dataclass(frozen=True, slots=True)
class HubeauStation:
    """What the source says about the site of a measurement.

    Every field is read verbatim. The station identity is the station code; the
    site code is the reach the station sits on, and the vertical datum is the
    reference the source says the heights are measured against.
    """

    code_station: str
    code_site: str
    latitude: float | None = None
    longitude: float | None = None
    altitude_system: int | None = None

    @property
    def spatial_ref(self) -> str:
        """The spatial reference of the station: its own code."""
        return self.code_station

    def as_dict(self) -> dict[str, Any]:
        """A serialisable view of the station."""
        return {
            "code_station": self.code_station,
            "code_site": self.code_site,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_system": self.altitude_system,
        }


def station_from_row(row: Mapping[str, Any]) -> HubeauStation:
    """The station a row belongs to, read from that row alone.

    A row without a station code has no station: it belongs to a site, and
    the caller is told so by the refusal of `observation_from_row`, which
    requires a station.
    """
    code_station = _text(row, "code_station")
    return HubeauStation(
        code_station=code_station,
        code_site=_text(row, "code_site"),
        latitude=_number(row.get("latitude")),
        longitude=_number(row.get("longitude")),
        altitude_system=_integer(row.get("code_systeme_alti_serie")),
    )


def observation_from_row(
    row: Mapping[str, Any],
    *,
    station: HubeauStation,
    source_id: str,
    evidence_id: str,
    acquired_at: datetime,
) -> Observation:
    """One observation, read from one row of the hydrometric feed.

    `acquired_at` is the instant the raw evidence was acquired: it is the
    `INGESTED_AT` dimension, and it is never the instant of the measurement.
    """
    grandeur = _text(row, "grandeur_hydro")
    if grandeur not in QUANTITIES:
        raise InterpretationError(f"the row carries an unknown quantity: {grandeur!r}")
    quantity, unit = QUANTITIES[grandeur]

    instant = _instant(row, "date_obs")
    value = _value(row)

    temporal = TemporalStamp(
        valid_time=instant,
        known_at=None,
        ingested_at=acquired_at,
        publication=PublicationState.BOUNDED,
        # A value cannot have been published before it was observed: the bound
        # is a fact, not a guess about the publication lag.
        publication_lower_bound=instant,
    )

    if value is None:
        return Observation(
            observation_id=_identifier(row, station, instant),
            source_id=source_id,
            quantity=quantity,
            unit=unit,
            temporal=temporal,
            evidence_id=evidence_id,
            value=None,
            validity=PointValidity.MISSING,
            missing_reason=MissingReason.NOT_MEASURED,
            spatial_ref=station.spatial_ref,
            key=_source_key(row),
            quality_status=quality_from_row(row),
        )

    return Observation(
        observation_id=_identifier(row, station, instant),
        source_id=source_id,
        quantity=quantity,
        unit=unit,
        temporal=temporal,
        evidence_id=evidence_id,
        value=value,
        validity=PointValidity.VALID,
        spatial_ref=station.spatial_ref,
        key=_source_key(row),
        quality_status=quality_from_row(row),
    )


def quality_from_row(row: Mapping[str, Any]) -> QualityStatus:
    """The quality the agency declares for the value, read from its label.

    The source-native label stays in the raw evidence; this is its translation
    into the closed vocabulary of the contract (§3.7). A label this layer does
    not know yields `UNKNOWN`: the safe choice, because a source that says
    something unreadable is not a source that approves.
    """
    label = row.get("libelle_statut")
    if not isinstance(label, str):
        return QualityStatus.UNKNOWN
    return _STATUS_LABELS.get(label.strip().lower(), QualityStatus.UNKNOWN)


def row_instant(row: Mapping[str, Any]) -> datetime:
    """The instant the row observes, in UTC."""
    return _instant(row, "date_obs")


def row_value(row: Mapping[str, Any]) -> float | None:
    """The measured value, or `None` when the source measured nothing."""
    return _value(row)


def _source_key(row: Mapping[str, Any]) -> str:
    """The source-native identity of a row, under the source's own names.

    It keeps the station code — even when the row does not carry one, where
    the site code stands in its place — so that a reader can go back to the
    exact record the observation was read from.
    """
    return "_".join(
        (
            str(row.get("code_site") or "-"),
            str(row.get("code_station") or "-"),
            str(row.get("grandeur_hydro") or "-"),
            str(row.get("date_obs") or "-"),
        )
    )


def _identifier(row: Mapping[str, Any], station: HubeauStation, instant: datetime) -> str:
    """A stable identifier for the observation.

    It is derived from what identifies the observation — the station, the
    quantity, the instant — and not from the order in which the rows came.
    """
    grandeur = _text(row, "grandeur_hydro")
    return f"{station.code_station}:{grandeur}:{instant.isoformat()}"


def _text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InterpretationError(f"the row does not carry '{field}'")
    return value.strip()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _integer(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _instant(row: Mapping[str, Any], field: str) -> datetime:
    raw = row.get(field)
    if not isinstance(raw, str) or not raw.strip():
        raise InterpretationError(f"the row does not carry '{field}'")
    text = raw.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        instant = datetime.fromisoformat(text)
    except ValueError as erreur:
        raise InterpretationError(f"'{field}' is not an ISO 8601 instant: {raw}") from erreur
    if instant.tzinfo is None:
        raise InterpretationError(
            f"'{field}' has no offset: {raw}. An instant without a zone is refused (INV-15)"
        )
    return instant.astimezone(UTC)


def _value(row: Mapping[str, Any]) -> float | None:
    """The measured value, or `None` when the source published no value.

    A missing value stays missing: it is never a zero, and never an
    interpolation.
    """
    raw = row.get("resultat_obs")
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise InterpretationError("'resultat_obs' is not a number")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError as erreur:
            raise InterpretationError(f"'resultat_obs' is not a number: {raw}") from erreur
    raise InterpretationError(f"'resultat_obs' is not a number: {raw!r}")


def observations_from_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    stations: Mapping[str, HubeauStation],
    source_id: str,
    evidence_id: str,
    acquired_at: datetime,
) -> tuple[tuple[Observation, ...], int]:
    """The observations of the rows, and how many rows were refused.

    A row is refused when it cannot be attributed to a station, or when it does
    not say what it must say. The refusal is counted, never hidden: a
    dataset's completeness is a fact about the dataset.
    """
    observations: list[Observation] = []
    refused = 0
    for row in rows:
        code = row.get("code_station")
        if not isinstance(code, str) or not code.strip():
            refused += 1
            continue
        station = stations.get(code.strip())
        if station is None:
            refused += 1
            continue
        try:
            observations.append(
                observation_from_row(
                    row,
                    station=station,
                    source_id=source_id,
                    evidence_id=evidence_id,
                    acquired_at=acquired_at,
                )
            )
        except (InterpretationError, ValueError):
            refused += 1
    return tuple(observations), refused


def series_of(
    observations: Sequence[Observation],
    *,
    quantity: str,
) -> tuple[tuple[datetime, float], ...]:
    """The valid observations of one quantity, in chronological order.

    The provider does not sort its rows: the feed returns them in the order of
    the collection, which is the reverse chronology of the measurement. The
    chronology is established here, once, rather than assumed by each consumer.
    """
    places = [
        (observation.temporal.valid_time, float(observation.value))
        for observation in observations
        if observation.quantity == quantity
        and observation.validity is PointValidity.VALID
        and observation.value is not None
        and observation.temporal.valid_time is not None
    ]
    places.sort(key=lambda place: place[0])
    return tuple(places)


# --------------------------------------------------------------------------
# What the acquired evidence says about a station
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StationProfile:
    """What the acquired evidence says about one station.

    Everything here is counted on the rows the source published. A station
    that cannot be described is a station that cannot be selected: the
    profile is what the selection reasons on, and it says what it found.
    """

    code_station: str
    code_site: str
    latitude: float | None
    longitude: float | None
    altitude_systems: tuple[int, ...]
    statuses: tuple[str, ...]
    methods: tuple[str, ...]
    qualifiers: tuple[str, ...]
    instants_by_quantity: Mapping[str, int]
    missing_by_quantity: Mapping[str, int]
    paired_instants: int
    sampling_interval_seconds: float | None
    expected_instants: int
    series_start: datetime | None
    series_end: datetime | None

    @property
    def sampling_interval_minutes(self) -> float | None:
        """The sampling interval, in minutes."""
        if self.sampling_interval_seconds is None:
            return None
        return self.sampling_interval_seconds / 60.0

    @property
    def completeness(self) -> float | None:
        """The share of the expected instants that carry a value.

        The expectation is built from the **modal gap** between the observed
        instants: the source does not publish a sampling interval, and the
        interval it is evidently using is read from its own rows rather than
        assumed. A station with a single instant has no expectation, and
        therefore no completeness.

        The completeness of the station is the **worst** of its quantities: a
        station whose stage is complete and whose discharge is not is not a
        complete station.
        """
        values = [
            value
            for value in (self.completeness_of(quantity) for quantity in self.instants_by_quantity)
            if value is not None
        ]
        if not values:
            return None
        return min(values)

    def completeness_of(self, quantity: str) -> float | None:
        """The completeness of one quantity of the station."""
        observed = self.instants_by_quantity.get(quantity)
        if observed is None or self.expected_instants <= 0:
            return None
        return min(1.0, observed / self.expected_instants)

    def as_dict(self) -> dict[str, Any]:
        """A serialisable view of the profile."""
        return {
            "code_station": self.code_station,
            "code_site": self.code_site,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_systems": list(self.altitude_systems),
            "statuses": list(self.statuses),
            "methods": list(self.methods),
            "qualifiers": list(self.qualifiers),
            "instants_by_quantity": dict(self.instants_by_quantity),
            "missing_by_quantity": dict(self.missing_by_quantity),
            "paired_instants": self.paired_instants,
            "sampling_interval_seconds": self.sampling_interval_seconds,
            "expected_instants": self.expected_instants,
            "series_start": None if self.series_start is None else self.series_start.isoformat(),
            "series_end": None if self.series_end is None else self.series_end.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class StationCriteria:
    """The conditions a station must meet to be selected.

    They are **declared**, and they are read on the metadata and on the
    completeness of the record — never on the values the station published.
    A station whose discharge looks interesting is not a selected station.
    """

    minimum_paired_instants: int = 20
    minimum_completeness: float = 0.9
    require_single_datum: bool = True
    require_coordinates: bool = True
    require_no_missing_value: bool = True
    require_single_status: bool = True

    def as_dict(self) -> dict[str, Any]:
        """A serialisable view of the criteria."""
        return {
            "minimum_paired_instants": self.minimum_paired_instants,
            "minimum_completeness": self.minimum_completeness,
            "require_single_datum": self.require_single_datum,
            "require_coordinates": self.require_coordinates,
            "require_no_missing_value": self.require_no_missing_value,
            "require_single_status": self.require_single_status,
        }


def profile_stations(rows: Iterable[Mapping[str, Any]]) -> tuple[StationProfile, ...]:
    """The profile of every station the rows mention.

    A row without a station code has no station and is left out: it is not
    attributed to a neighbour, and it is not counted as a station.
    """
    by_station: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        code = row.get("code_station")
        if not isinstance(code, str) or not code.strip():
            continue
        by_station.setdefault(code.strip(), []).append(row)

    profiles: list[StationProfile] = []
    for code, station_rows in sorted(by_station.items()):
        profiles.append(_profile_of(code, station_rows))
    return tuple(profiles)


def select_station(
    profiles: Sequence[StationProfile],
    criteria: StationCriteria,
) -> StationProfile:
    """The station the criteria select.

    The tie-break is on **coverage** and then on the station code, both of
    which are properties of the record and not of its values: among the
    stations that meet the criteria, the one with the longest paired record
    is the one whose relation is the best determined, and the code breaks the
    remaining ties so that the selection is reproducible.
    """
    eligible = [
        profile
        for profile in profiles
        if profile.paired_instants >= criteria.minimum_paired_instants
        and (profile.completeness or 0.0) >= criteria.minimum_completeness
        and (not criteria.require_single_datum or len(profile.altitude_systems) <= 1)
        and (
            not criteria.require_coordinates
            or (profile.latitude is not None and profile.longitude is not None)
        )
        and (not criteria.require_no_missing_value or not any(profile.missing_by_quantity.values()))
        and (not criteria.require_single_status or len(profile.statuses) <= 1)
    ]
    if not eligible:
        raise ValueError(
            "no station meets the declared criteria: "
            f"{criteria.as_dict()} over {len(profiles)} profile(s)"
        )
    eligible.sort(key=lambda profile: (-profile.paired_instants, profile.code_station))
    return eligible[0]


def _profile_of(code: str, rows: Sequence[Mapping[str, Any]]) -> StationProfile:
    """The profile of one station, counted on its rows."""
    sites = sorted({str(row.get("code_site")) for row in rows if row.get("code_site")})
    latitudes = [row.get("latitude") for row in rows if row.get("latitude") is not None]
    longitudes = [row.get("longitude") for row in rows if row.get("longitude") is not None]
    datums = sorted(
        {
            int(row["code_systeme_alti_serie"])
            for row in rows
            if isinstance(row.get("code_systeme_alti_serie"), (int, float))
            and not isinstance(row.get("code_systeme_alti_serie"), bool)
        }
    )
    statuses = sorted({str(row.get("libelle_statut")) for row in rows if row.get("libelle_statut")})
    methods = sorted(
        {str(row.get("libelle_methode_obs")) for row in rows if row.get("libelle_methode_obs")}
    )
    qualifiers = sorted(
        {
            str(row.get("libelle_qualification_obs"))
            for row in rows
            if row.get("libelle_qualification_obs")
        }
    )

    instants: dict[str, set[datetime]] = {}
    missing: dict[str, int] = {}
    for row in rows:
        grandeur = str(row.get("grandeur_hydro"))
        if row.get("resultat_obs") is None:
            missing[grandeur] = missing.get(grandeur, 0) + 1
            continue
        instant = _parse_instant(row.get("date_obs"))
        if instant is None:
            continue
        instants.setdefault(grandeur, set()).add(instant)

    all_instants = sorted({instant for values in instants.values() for instant in values})
    paired = 0
    if len(instants) >= 2:
        quantities = sorted(instants)
        reference = instants[quantities[0]]
        for other in quantities[1:]:
            reference = reference & instants[other]
        paired = len(reference)

    gaps = [(later - earlier).total_seconds() for earlier, later in pairwise(all_instants)]
    interval = _modal(gaps)

    expected = 0
    if interval and len(all_instants) >= 2:
        span = (all_instants[-1] - all_instants[0]).total_seconds()
        expected = round(span / interval) + 1

    series_starts = [row.get("date_debut_serie") for row in rows if row.get("date_debut_serie")]
    series_ends = [row.get("date_fin_serie") for row in rows if row.get("date_fin_serie")]

    return StationProfile(
        code_station=code,
        code_site=sites[0] if sites else "",
        latitude=float(latitudes[0]) if latitudes else None,
        longitude=float(longitudes[0]) if longitudes else None,
        altitude_systems=tuple(datums),
        statuses=tuple(statuses),
        methods=tuple(methods),
        qualifiers=tuple(qualifiers),
        instants_by_quantity={name: len(values) for name, values in sorted(instants.items())},
        missing_by_quantity=dict(sorted(missing.items())),
        paired_instants=paired,
        sampling_interval_seconds=interval,
        expected_instants=expected,
        series_start=_first_instant(series_starts),
        series_end=_last_instant(series_ends),
    )


def _modal(values: Sequence[float]) -> float | None:
    """The most frequent value, and among the frequent ones the smallest."""
    if not values:
        return None
    counts: dict[float, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    best = max(counts.values())
    return min(value for value, count in counts.items() if count == best)


def _first_instant(values: Sequence[Any]) -> datetime | None:
    instants = [_parse_instant(value) for value in values]
    instants = [instant for instant in instants if instant is not None]
    return min(instants) if instants else None


def _last_instant(values: Sequence[Any]) -> datetime | None:
    instants = [_parse_instant(value) for value in values]
    instants = [instant for instant in instants if instant is not None]
    return max(instants) if instants else None


def _parse_instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        instant = datetime.fromisoformat(text)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return None
    return instant.astimezone(UTC)


__all__ = [
    "DISCHARGE_UNIT",
    "QUANTITIES",
    "STAGE_UNIT",
    "HubeauStation",
    "InterpretationError",
    "StationCriteria",
    "StationProfile",
    "observation_from_row",
    "observations_from_rows",
    "profile_stations",
    "quality_from_row",
    "row_instant",
    "row_value",
    "select_station",
    "series_of",
    "station_from_row",
]
