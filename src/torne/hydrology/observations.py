"""The semantic layer: from a USGS record to an Observation.

Until now the socle could acquire and keep raw evidence, and could say
whether what came back answered the question that was asked. What it could
not do was **say what a number means**: a discharge in ft³/s, on a station of
the Mississippi, for a day of the local civil calendar, with a quality the
provider declared.

This module is that layer. It is deliberately small, and deliberately explicit
about every convention it applies:

- **A civil date is not an instant.** The daily collection publishes a bare
  date (`2024-01-03`); the provider does not say at what instant its day
  starts. The zone is therefore an explicit argument, never guessed from the
  abbreviation the provider publishes — `CST` is not a zone, and the country
  of the station is not a timezone. The convention is named in the method of
  every product built on it.
- **A value is a string.** It is parsed explicitly, and the provider's
  missing-value sentinel is recognised as an absence, never as a number.
- **An absence stays an absence.** A record the provider did not measure
  produces an observation with no value and a qualified reason, never a zero.
- **A quality is a declared quality.** `approval_status` and `qualifier` are
  read as the provider states them; the raw evidence keeps the codes
  verbatim, and the interpretation does not invent a status the provider did
  not give.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, tzinfo
from typing import Any

from ..contracts.observation import Observation, QualityStatus
from ..contracts.time import PublicationState, TemporalStamp, civil_day_to_instant
from ..contracts.validity import MissingReason, PointValidity

MISSING_VALUE = -999999.0
"""The provider's missing-value sentinel.

It is published as a number, like any other, and it means *nothing was
measured*. Reading it as a measurement would put a quarter of a million cubic
feet per second into a record of the Mississippi.
"""

DAY_CONVENTION = "day_start_local"
"""The declared convention for a civil date.

A daily value is attributed to the **start of the civil day in the station's
zone**. The provider does not publish the aggregation window it used; this is
a declared convention of the interpretation layer, it is written into the
method of every product built on it, and it is never assumed silently.
"""


class InterpretationError(ValueError):
    """The record does not say what it must say.

    It is raised rather than guessed around: a record whose time cannot be
    placed, or whose value cannot be read, is refused — and the refusal is
    visible.
    """


@dataclass(frozen=True, slots=True)
class Station:
    """What the provider says about the site itself.

    The fields the provider publishes are the fields it publishes. The unit of
    `drainage_area` is **not** among them: the collection schema declares no
    unit for it, so the number is kept and the unit stays `None` — a
    quantitative claim about a catchment area cannot be made on this.
    """

    monitoring_location_id: str
    name: str
    site_type: str
    state_code: str
    county_code: str
    timezone_abbreviation: str
    uses_daylight_savings: bool
    drainage_area: float | None = None
    drainage_area_unit: str | None = None
    vertical_datum: str | None = None
    altitude: float | None = None
    longitude: float | None = None
    latitude: float | None = None

    @property
    def spatial_ref(self) -> str:
        """The spatial reference of the station, in the provider's own terms."""
        return self.monitoring_location_id

    def as_dict(self) -> dict[str, Any]:
        """A serialisable view of the station."""
        return {
            "monitoring_location_id": self.monitoring_location_id,
            "name": self.name,
            "site_type": self.site_type,
            "state_code": self.state_code,
            "county_code": self.county_code,
            "timezone_abbreviation": self.timezone_abbreviation,
            "uses_daylight_savings": self.uses_daylight_savings,
            "drainage_area": self.drainage_area,
            "drainage_area_unit": self.drainage_area_unit,
            "vertical_datum": self.vertical_datum,
            "altitude": self.altitude,
            "longitude": self.longitude,
            "latitude": self.latitude,
        }


def station_from_feature(feature: Mapping[str, Any]) -> Station:
    """The station, read from a `monitoring-locations` record.

    Everything taken here is taken **verbatim**. The unit of the drainage
    area is left absent because the provider does not publish one.
    """
    properties = _properties(feature)
    identifier = _text(properties, "id")
    geometrie = feature.get("geometry") if isinstance(feature, Mapping) else None
    longitude: float | None = None
    latitude: float | None = None
    if isinstance(geometrie, Mapping):
        coordinates = geometrie.get("coordinates")
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            longitude = _number(coordinates[0])
            latitude = _number(coordinates[1])

    return Station(
        monitoring_location_id=identifier,
        name=_text(properties, "monitoring_location_name"),
        site_type=_text(properties, "site_type"),
        state_code=_text(properties, "state_code"),
        county_code=_text(properties, "county_code"),
        timezone_abbreviation=_text(properties, "time_zone_abbreviation"),
        uses_daylight_savings=_text(properties, "uses_daylight_savings") == "Y",
        drainage_area=_number(properties.get("drainage_area")),
        drainage_area_unit=None,
        vertical_datum=_optional_text(properties.get("vertical_datum")),
        altitude=_number(properties.get("altitude")),
        longitude=longitude,
        latitude=latitude,
    )


def observation_from_feature(
    feature: Mapping[str, Any],
    *,
    station: Station,
    source_id: str,
    evidence_id: str,
    zone: tzinfo,
    acquired_at: datetime,
    quantity: str,
    unit: str,
) -> Observation:
    """One observation, read from one record of the values collection.

    `zone` is the station's local zone. It is an argument, not a guess: the
    provider publishes an abbreviation (`CST`) and a daylight-saving flag,
    and neither of them is a zone.
    """
    properties = _properties(feature)
    day = _day_from_properties(properties)
    instant = civil_day_to_instant(day, zone, name="observation day")

    published = _instant_from_properties(properties, "last_modified")
    value = _value_from_properties(properties)
    status = _quality_from_properties(properties)

    if value is None:
        return Observation(
            observation_id=_identifier(properties, station, day),
            source_id=source_id,
            quantity=quantity,
            unit=unit,
            temporal=TemporalStamp(
                valid_time=instant,
                known_at=published,
                ingested_at=acquired_at,
                publication=PublicationState.ESTABLISHED if published else PublicationState.UNKNOWN,
            ),
            evidence_id=evidence_id,
            value=None,
            validity=PointValidity.MISSING,
            missing_reason=MissingReason.NOT_MEASURED,
            spatial_ref=station.spatial_ref,
            quality_status=status,
        )

    return Observation(
        observation_id=_identifier(properties, station, day),
        source_id=source_id,
        quantity=quantity,
        unit=unit,
        temporal=TemporalStamp(
            valid_time=instant,
            known_at=published,
            ingested_at=acquired_at,
            publication=PublicationState.ESTABLISHED if published else PublicationState.UNKNOWN,
        ),
        evidence_id=evidence_id,
        value=value,
        validity=PointValidity.VALID,
        spatial_ref=station.spatial_ref,
        quality_status=status,
    )


def continuous_observation(
    feature: Mapping[str, Any],
    *,
    station: Station,
    source_id: str,
    evidence_id: str,
    zone: tzinfo,
    acquired_at: datetime,
    quantity: str,
    unit: str,
) -> Observation:
    """One observation, read from one record of the continuous collection.

    The continuous collection publishes an **instant** with an explicit
    offset, not a civil date: the zone is therefore not applied to the time
    itself. It is still required, because the day a measurement belongs to is
    what the day-of-year climatology is keyed on — and that day is a local
    civil day, not a UTC one.
    """
    properties = _properties(feature)
    instant = _continuous_instant(properties)
    local = instant.astimezone(zone)
    day = local.date()

    published = _instant_from_properties(properties, "last_modified")
    value = _value_from_properties(properties)
    status = _quality_from_properties(properties)

    if value is None:
        return Observation(
            observation_id=_identifier(properties, station, day),
            source_id=source_id,
            quantity=quantity,
            unit=unit,
            temporal=TemporalStamp(
                valid_time=instant,
                known_at=published,
                ingested_at=acquired_at,
                publication=PublicationState.ESTABLISHED if published else PublicationState.UNKNOWN,
            ),
            evidence_id=evidence_id,
            value=None,
            validity=PointValidity.MISSING,
            missing_reason=MissingReason.NOT_MEASURED,
            spatial_ref=station.spatial_ref,
            quality_status=status,
        )

    return Observation(
        observation_id=_identifier(properties, station, day),
        source_id=source_id,
        quantity=quantity,
        unit=unit,
        temporal=TemporalStamp(
            valid_time=instant,
            known_at=published,
            ingested_at=acquired_at,
            publication=PublicationState.ESTABLISHED if published else PublicationState.UNKNOWN,
        ),
        evidence_id=evidence_id,
        value=value,
        validity=PointValidity.VALID,
        spatial_ref=station.spatial_ref,
        quality_status=status,
    )


# --------------------------------------------------------------------------
# Reading a record
# --------------------------------------------------------------------------


def _properties(feature: Mapping[str, Any]) -> Mapping[str, Any]:
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        raise InterpretationError("the record has no 'properties' mapping")
    return properties


def _text(properties: Mapping[str, Any], field: str) -> str:
    value = properties.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InterpretationError(f"the record does not carry '{field}'")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    return value or None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _day_from_properties(properties: Mapping[str, Any]) -> date:
    """The civil day of a daily record.

    The provider publishes `2024-01-03`: a date, not an instant. A date that
    cannot be read as a date is refused.
    """
    raw = properties.get("time")
    if not isinstance(raw, str) or not raw.strip():
        raise InterpretationError("the record does not carry 'time'")
    try:
        return date.fromisoformat(raw)
    except ValueError as erreur:
        raise InterpretationError(f"'time' is not a civil date: {raw}") from erreur


def _continuous_instant(properties: Mapping[str, Any]) -> datetime:
    """The instant of a continuous record, with its own offset."""
    raw = properties.get("time")
    if not isinstance(raw, str) or not raw.strip():
        raise InterpretationError("the record does not carry 'time'")
    try:
        instant = datetime.fromisoformat(raw)
    except ValueError as erreur:
        raise InterpretationError(f"'time' is not an ISO 8601 instant: {raw}") from erreur
    if instant.tzinfo is None:
        raise InterpretationError(
            f"'time' has no offset: {raw}. An instant without a zone is refused (INV-15)"
        )
    return instant.astimezone(UTC)


def _instant_from_properties(properties: Mapping[str, Any], field: str) -> datetime | None:
    """An instant published by the provider, or `None` when it publishes none."""
    raw = properties.get(field)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        instant = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if instant.tzinfo is None:
        # The provider publishes this field without an offset on some
        # collections. An instant without a zone is refused rather than
        # assumed: the publication time of a value is what makes it usable,
        # and guessing it would guess the usability.
        return None
    return instant.astimezone(UTC)


def _value_from_properties(properties: Mapping[str, Any]) -> float | None:
    """The measured value, or `None` when the provider measured nothing.

    The sentinel `-999999` is an absence, not a measurement.
    """
    raw = properties.get("value")
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            value = float(raw)
        except ValueError as erreur:
            raise InterpretationError(f"'value' is not a number: {raw}") from erreur
    elif isinstance(raw, bool):
        raise InterpretationError("'value' is not a number")
    elif isinstance(raw, (int, float)):
        value = float(raw)
    else:
        raise InterpretationError(f"'value' is not a number: {raw!r}")
    if value == MISSING_VALUE:
        return None
    return value


def _quality_from_properties(properties: Mapping[str, Any]) -> QualityStatus:
    """The quality the provider declares, read from what it publishes.

    The vocabulary is closed (§3.7): a source that says nothing is not a
    source that approves.
    """
    approval = properties.get("approval_status")
    qualifier = properties.get("qualifier")

    if isinstance(qualifier, str) and qualifier.strip():
        code = qualifier.strip().lower()
        if code == "e":
            return QualityStatus.SOURCE_ESTIMATED
        if code == "p":
            return QualityStatus.PROVISIONAL

    if isinstance(approval, str):
        status = approval.strip().lower()
        if status == "approved":
            return QualityStatus.APPROVED
        if status == "provisional":
            return QualityStatus.PROVISIONAL
        if status == "estimated":
            return QualityStatus.SOURCE_ESTIMATED

    return QualityStatus.UNKNOWN


def _identifier(
    properties: Mapping[str, Any],
    station: Station,
    day: date,
) -> str:
    """A stable identifier for the observation.

    It is derived from what identifies the observation — the station, the
    series, the day — and not from the order in which the records came.
    """
    series = properties.get("time_series_id")
    suffix = str(series) if series else "series-inconnue"
    return f"{station.monitoring_location_id}:{suffix}:{day.isoformat()}"


def time_series(observations: Iterable[Observation]) -> tuple[Observation, ...]:
    """The observations in chronological order.

    The provider does **not** sort its records: the daily collection returns
    them in an arbitrary order — measured on 2026-11-01, the first records
    came 1 January, 3 January, 2 January, 5 January. A time series is
    ordered by time, and the order is established here, once, rather than
    assumed by each consumer: a filter that expects an increasing series
    refuses anything else, and a reader that assumes the order reads a series
    that does not exist.

    The observations without a valid time are dropped: they cannot be placed
    in a chronology, and inventing a place for them would be inventing a
    date.
    """
    places = [
        (observation.temporal.valid_time, index, observation)
        for index, observation in enumerate(observations)
        if observation.temporal.valid_time is not None
    ]
    places.sort(key=lambda place: (place[0], place[1]))
    return tuple(place[2] for place in places)


__all__ = [
    "DAY_CONVENTION",
    "MISSING_VALUE",
    "InterpretationError",
    "Station",
    "continuous_observation",
    "observation_from_feature",
    "station_from_feature",
    "time_series",
]
