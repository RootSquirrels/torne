"""The hydrology semantic layer — what a number of a stream means.

The records used here were **recorded** from the live API on 2026-11-01.
Nothing in this file touches the network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from torne.contracts.observation import QualityStatus
from torne.contracts.validity import PointValidity
from torne.hydrology import (
    InterpretationError,
    anomaly_index,
    climatology,
    compare_with_published_normals,
    mean_anomaly,
    observation_from_feature,
    published_normals_by_day,
    station_from_feature,
    time_series,
)

ZONE = ZoneInfo("America/Chicago")
STATION = "USGS-05587450"

_SITE = {
    "type": "Feature",
    "properties": {
        "id": STATION,
        "agency_code": "USGS",
        "monitoring_location_number": "05587450",
        "monitoring_location_name": "Mississippi River at Grafton, IL",
        "site_type": "Stream",
        "site_type_code": "ST",
        "state_code": "17",
        "state_name": "Illinois",
        "county_code": "083",
        "drainage_area": 171300.0,
        "contributing_drainage_area": None,
        "time_zone_abbreviation": "CST",
        "uses_daylight_savings": "Y",
        "altitude": 403.32,
        "vertical_datum": "NAVD88",
    },
    "id": STATION,
    "geometry": {"type": "Point", "coordinates": [-90.429, 38.9679722222222]},
}


def _record(
    day: str,
    value: str,
    *,
    approval: str = "Approved",
    qualifier: str | None = None,
    published: str = "2025-08-28T06:16:44.497456+00:00",
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "time_series_id": "bda68b74ed2e4110902f43f353dcfdd1",
            "monitoring_location_id": STATION,
            "parameter_code": "00060",
            "statistic_id": "00003",
            "time": day,
            "value": value,
            "unit_of_measure": "ft^3/s",
            "approval_status": approval,
            "qualifier": qualifier,
            "last_modified": published,
        },
        "id": "024ba6e0-c7b7-4d64-aba8-403e0bc48947",
        "geometry": {"type": "Point", "coordinates": [-90.429, 38.9679722222222]},
    }


def _observation(feature: dict, *, acquis: datetime | None = None):
    station = station_from_feature(_SITE)
    return observation_from_feature(
        feature,
        station=station,
        source_id="usgs.ogc.daily",
        evidence_id="evidence-001",
        zone=ZONE,
        acquired_at=acquis or datetime(2026, 11, 1, 10, 30, tzinfo=UTC),
        quantity="discharge",
        unit="ft^3/s",
    )


# --------------------------------------------------------------------------
# The station
# --------------------------------------------------------------------------


def test_the_station_is_read_as_the_source_publishes_it():
    """Everything taken is taken verbatim."""
    station = station_from_feature(_SITE)

    assert station.monitoring_location_id == STATION
    assert station.name == "Mississippi River at Grafton, IL"
    assert station.site_type == "Stream"
    assert station.timezone_abbreviation == "CST"
    assert station.uses_daylight_savings is True
    assert station.vertical_datum == "NAVD88"
    assert station.drainage_area == 171300.0
    assert station.longitude == pytest.approx(-90.429)
    assert station.latitude == pytest.approx(38.9679722222222)


def test_the_catchment_area_unit_stays_unknown():
    """The provider declares no unit for the drainage area.

    A number without a unit cannot carry a quantitative claim: the unit
    stays absent rather than being guessed.
    """
    station = station_from_feature(_SITE)

    assert station.drainage_area == 171300.0
    assert station.drainage_area_unit is None


def test_the_time_zone_is_not_guessed():
    """`CST` is an abbreviation, not a zone: the zone is an argument."""
    station = station_from_feature(_SITE)

    assert station.timezone_abbreviation == "CST"


# --------------------------------------------------------------------------
# The observation
# --------------------------------------------------------------------------


def test_a_record_becomes_an_observation():
    """The value, the unit, the day and the declared quality are carried over."""
    observation = _observation(_record("2024-01-02", "67700"))

    assert observation.value == 67700.0
    assert observation.unit == "ft^3/s"
    assert observation.quantity == "discharge"
    assert observation.validity is PointValidity.VALID
    assert observation.quality_status is QualityStatus.APPROVED
    assert observation.evidence_id == "evidence-001"
    assert observation.spatial_ref == STATION


def test_the_civil_day_is_placed_in_the_station_zone():
    """A civil date is not an instant: the zone makes it one, explicitly.

    The contract stores instants in UTC, so what the observation carries is
    the UTC form of the local midnight — which is the same instant.
    """
    observation = _observation(_record("2024-01-02", "67700"))

    assert observation.temporal.valid_time == datetime(2024, 1, 2, tzinfo=ZONE)
    assert observation.temporal.valid_time.astimezone(ZONE) == datetime(
        2024, 1, 2, 0, 0, tzinfo=ZONE
    )


def test_an_absent_value_is_never_a_zero():
    """The sentinel `-999999` means nothing was measured.

    Reading it as a measurement would put a quarter of a million cubic feet
    per second into a record of the Mississippi.
    """
    observation = _observation(_record("2024-01-02", "-999999"))

    assert observation.value is None
    assert observation.validity is PointValidity.MISSING
    assert observation.missing_reason is not None
    assert observation.value != 0.0


def test_the_provisional_quality_is_kept():
    """A provisional value is kept, and it keeps its status."""
    observation = _observation(_record("2024-01-02", "67700", approval="Provisional"))

    assert observation.value == 67700.0
    assert observation.quality_status is QualityStatus.PROVISIONAL


def test_the_estimated_qualifier_is_kept():
    """The provider's qualifier is read, not guessed."""
    observation = _observation(
        _record("2024-01-02", "67700", approval="Provisional", qualifier="e")
    )

    assert observation.quality_status is QualityStatus.SOURCE_ESTIMATED


def test_a_silent_source_does_not_give_an_approved_status():
    """A source that says nothing is not a source that approves."""
    record = _record("2024-01-02", "67700")
    del record["properties"]["approval_status"]

    observation = _observation(record)

    assert observation.quality_status is QualityStatus.UNKNOWN


def test_an_instant_without_a_zone_is_refused():
    """A publication time without an offset is refused rather than assumed."""
    record = _record("2024-01-02", "67700", published="2025-08-28T06:16:44.497456")

    observation = _observation(record)

    assert observation.temporal.known_at is None
    assert observation.temporal.usable_at is None


def test_an_unreadable_date_is_refused():
    """A record whose day cannot be read is refused, not guessed around."""
    record = _record("02/01/2024", "67700")

    with pytest.raises(InterpretationError, match="civil date"):
        _observation(record)


# --------------------------------------------------------------------------
# The climatology
# --------------------------------------------------------------------------


def _serie(nb_annees: int = 3, *, facteur: float = 1.0):
    """A synthetic daily series: a normal year, then a scaled one."""
    observations = []
    base = datetime(2023, 1, 1, tzinfo=ZONE)
    for annee in range(nb_annees):
        for day in range(365):
            instant = base + timedelta(days=annee * 365 + day)
            value = 1000.0 + 10.0 * ((day % 30) - 15)
            if annee == nb_annees - 1:
                value *= facteur
            observations.append(
                _observation(
                    _record(instant.date().isoformat(), f"{value:.4f}"),
                    acquis=datetime(2026, 11, 1, 10, 30, tzinfo=UTC),
                )
            )
    return observations


def test_the_climatology_groups_by_day_of_year():
    """The reference is the day-of-year mean, with its own count.

    Three years of daily values cover 366 calendar days: 29 February is
    there, and it was observed twice, not three times.
    """
    observations = _serie(nb_annees=3)

    reference = climatology(observations)

    assert len(reference) == 366
    day = reference.pour(1, 1)
    assert day is not None
    assert day.count == 3
    assert day.standard_deviation > 0.0
    bissextile = reference.pour(2, 29)
    assert bissextile is not None
    assert bissextile.count == 1


def test_the_reference_bounds_filter_the_record():
    """`reference_start` / `reference_end` select the years that enter the reference."""
    observations = _serie(nb_annees=3)
    last_year = observations[-1].temporal.valid_time.year

    reference = climatology(observations, reference_start=datetime(last_year, 1, 1, tzinfo=ZONE))

    day = reference.pour(1, 1)
    assert day is not None
    assert day.count == 1
    assert reference.years == 1


def test_the_climatology_keys_on_the_civil_day_of_the_given_zone():
    """East of Greenwich, local midnight is the previous UTC day.

    A Paris daily value for 1 January is stamped at 23:00 UTC on 31 December:
    keyed on the UTC day it would land on the wrong calendar day.
    """
    paris = ZoneInfo("Europe/Paris")
    observation = observation_from_feature(
        _record("2025-01-01", "100.0"),
        station=station_from_feature(_SITE),
        source_id="usgs.ogc.daily",
        evidence_id="evidence-001",
        zone=paris,
        acquired_at=datetime(2026, 11, 1, 10, 30, tzinfo=UTC),
        quantity="discharge",
        unit="ft^3/s",
    )

    assert climatology([observation]).pour(12, 31) is not None
    in_zone = climatology([observation], zone=paris)
    assert in_zone.pour(1, 1) is not None
    assert in_zone.pour(12, 31) is None


def test_a_dry_year_is_negative_and_a_wet_year_positive():
    """The index says what it is meant to say."""
    observations = _serie(nb_annees=3, facteur=0.5)

    reference = climatology(observations)
    fenetre = (
        datetime(2024, 12, 31, tzinfo=ZONE),
        datetime(2025, 12, 31, tzinfo=ZONE),
    )
    series = anomaly_index(
        observations,
        reference,
        variable_id="anomalie:test",
        spatial_ref=STATION,
        computed_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
        fenetre=fenetre,
    )

    assert len(series.values) == 365
    assert sum(series.values) / len(series.values) < -1.0
    mean = mean_anomaly(
        series,
        variable_id="anomalie_moyenne:test",
        computed_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
    )
    assert mean.value is not None
    assert mean.value < -1.0
    assert mean.uncertainty.interval is not None
    bas, haut = mean.uncertainty.interval
    assert bas < mean.value < haut


def test_the_derived_variable_cites_its_inputs():
    """The lineage is the verifiable form of the claim."""
    observations = _serie(nb_annees=2)
    reference = climatology(observations)

    series = anomaly_index(
        observations,
        reference,
        variable_id="anomalie:test",
        spatial_ref=STATION,
        computed_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
    )

    assert series.nature.value == "derived"
    assert series.method
    assert series.method_version
    assert len(series.inputs) == len(series.values)
    assert len(series.transitive_observations) == len(series.values)
    assert series.parameters.as_dict()["reference_annees"] == reference.years


def test_a_day_absent_from_the_reference_is_not_scored():
    """A day the reference never observed is scored against nothing."""
    observations = _serie(nb_annees=1)
    reference = climatology(observations[:10])

    with pytest.raises(ValueError, match="no observation"):
        anomaly_index(
            observations,
            reference,
            variable_id="anomalie:test",
            spatial_ref=STATION,
            computed_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
        )


# --------------------------------------------------------------------------
# The independent reference
# --------------------------------------------------------------------------

_NORMALES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "monitoring_location_id": STATION,
                "data": [
                    {
                        "parameter_code": "00060",
                        "unit_of_measure": "ft^3/s",
                        "values": [
                            {
                                "time_of_year": "01-01",
                                "time_of_year_type": "day_of_year",
                                "value": "1000.0",
                                "sample_count": 91,
                                "computation": "arithmetic_mean",
                            },
                            {
                                "time_of_year": "01-02",
                                "time_of_year_type": "day_of_year",
                                "value": "1010.0",
                                "sample_count": 91,
                                "computation": "arithmetic_mean",
                            },
                            {
                                "time_of_year": "01-01",
                                "time_of_year_type": "day_of_year",
                                "value": "900.0",
                                "sample_count": 91,
                                "computation": "median",
                            },
                        ],
                    }
                ],
            },
        }
    ],
    "next": None,
}


def test_the_published_normals_are_read_by_day():
    """Only the arithmetic mean is read: the others are other statistics."""
    published_normals = published_normals_by_day(_NORMALES)

    assert published_normals == {(1, 1): 1000.0, (1, 2): 1010.0}


def test_the_comparison_with_the_independent_reference_is_quantified():
    """The provider's statistics and ours are put side by side."""
    observations = _serie(nb_annees=2)
    reference = climatology(observations)

    published_normals = {
        day: jour_reference.mean for day, jour_reference in reference.by_day.items()
    }

    gap = compare_with_published_normals(reference, published_normals, acquired_years=2)

    assert gap.days_compared == 366
    assert gap.median_relative_gap == pytest.approx(0.0, abs=1e-9)
    assert gap.correlation == pytest.approx(1.0, abs=1e-9)
    assert gap.concordant is True
    assert gap.acquired_years == 2


def test_a_different_published_statistic_is_reported():
    """A gap with the reference is reported, not hidden.

    The relative difference is measured against the **published** value: a
    published mean twice ours is a 50% difference, not a 100% one.
    """
    observations = _serie(nb_annees=2)
    reference = climatology(observations)
    published_normals = {
        day: jour_reference.mean * 2.0 for day, jour_reference in reference.by_day.items()
    }

    gap = compare_with_published_normals(reference, published_normals, acquired_years=2)

    assert gap.median_relative_gap == pytest.approx(0.5, abs=1e-6)
    assert gap.concordant is False


def test_a_time_series_is_ordered():
    """The provider does not sort its records: the chronology is established here.

    The daily collection was observed returning 1 January, 3 January,
    2 January, 5 January. A filter that expects an increasing series refuses
    anything else, and a reader that assumes the order reads a series that
    does not exist.
    """
    station = station_from_feature(_SITE)
    dans_le_desordre = [
        observation_from_feature(
            _record(day, "1000"),
            station=station,
            source_id="usgs.ogc.daily",
            evidence_id="evidence-001",
            zone=ZONE,
            acquired_at=datetime(2026, 11, 1, 10, 30, tzinfo=UTC),
            quantity="discharge",
            unit="ft^3/s",
        )
        for day in ("2024-01-01", "2024-01-03", "2024-01-02", "2024-01-05")
    ]

    series = time_series(dans_le_desordre)

    assert [observation.temporal.valid_time.date().isoformat() for observation in series] == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-05",
    ]


def test_a_civil_date_is_never_degraded_without_a_zone():
    """The contract's refusal stands here too: no implicit zone.

    The wording of the message is the contract's, and the contract is being
    translated: what is matched here is the reference to the rule, not the
    sentence that states it.
    """
    from torne.contracts.time import civil_day_to_instant

    with pytest.raises(ValueError, match=r"3\.3"):
        civil_day_to_instant(date(2024, 1, 2), None)
