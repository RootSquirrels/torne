"""The French hydrometry: reading a Hub'Eau row as an Observation.

These tests pin the three decisions the semantic layer declares, and the two
refusals it must never make: no manufactured station, no manufactured value.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from torne.acquisition.adapters.hubeau_feed import (
    SOURCE_ID,
    URL_OBSERVATIONS_TR,
    HubeauFeedAdapter,
)
from torne.acquisition.contracts import (
    Conformite,
    HttpResponse,
    PaginationStrategy,
)
from torne.contracts.observation import QualityStatus
from torne.contracts.time import PublicationState
from torne.contracts.validity import MissingReason, PointValidity
from torne.hydrology.hubeau import (
    DISCHARGE_UNIT,
    STAGE_UNIT,
    InterpretationError,
    StationCriteria,
    observation_from_row,
    observations_from_rows,
    profile_stations,
    quality_from_row,
    select_station,
    series_of,
    station_from_row,
)

ACQUIRED_AT = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _row(**overrides) -> dict:
    """A row of the hydrometric feed, as the source publishes it."""
    row = {
        "code_site": "A4050620",
        "code_station": "A405062001",
        "grandeur_hydro": "Q",
        "date_debut_serie": "2026-11-01T00:05:00Z",
        "date_fin_serie": "2026-11-01T11:40:00Z",
        "code_systeme_alti_serie": 31,
        "date_obs": "2026-11-01T11:40:00Z",
        "resultat_obs": 1180.0,
        "code_methode_obs": 8,
        "libelle_methode_obs": "Calculée",
        "code_qualification_obs": 16,
        "libelle_qualification_obs": "Non qualifiée",
        "longitude": 6.685918446,
        "latitude": 47.909444585,
        "code_statut": 4,
        "libelle_statut": "Brute",
        "code_continuite": 0,
        "libelle_continuite": "Continue",
    }
    row.update(overrides)
    return row


def _observation(row: dict | None = None):
    the_row = row if row is not None else _row()
    station = station_from_row(the_row)
    return observation_from_row(
        the_row,
        station=station,
        source_id=SOURCE_ID,
        evidence_id="evidence-1",
        acquired_at=ACQUIRED_AT,
    )


# --------------------------------------------------------------------------
# The unit of the quantity
# --------------------------------------------------------------------------


def test_the_discharge_carries_the_unit_of_its_quantity():
    observation = _observation()
    assert observation.quantity == "discharge"
    assert observation.unit == DISCHARGE_UNIT


def test_the_stage_carries_no_unit_the_source_does_not_publish():
    observation = _observation(_row(grandeur_hydro="H", resultat_obs=428.0))
    assert observation.quantity == "stage"
    assert observation.unit == STAGE_UNIT
    assert STAGE_UNIT != "m"
    assert STAGE_UNIT != "cm"


def test_an_unknown_quantity_is_refused_rather_than_read_as_another():
    with pytest.raises(InterpretationError):
        _observation(_row(grandeur_hydro="Z"))


# --------------------------------------------------------------------------
# The publication instant
# --------------------------------------------------------------------------


def test_the_publication_is_bounded_by_the_instant_of_the_observation():
    observation = _observation()
    assert observation.temporal.publication is PublicationState.BOUNDED
    assert observation.temporal.publication_lower_bound == observation.temporal.valid_time
    assert observation.temporal.known_at is None


def test_the_ingestion_is_the_acquisition_and_never_the_measurement():
    observation = _observation()
    assert observation.temporal.ingested_at == ACQUIRED_AT
    assert observation.temporal.ingested_at != observation.temporal.valid_time


# --------------------------------------------------------------------------
# What the source did not measure
# --------------------------------------------------------------------------


def test_a_missing_value_stays_missing_and_is_never_a_zero():
    observation = _observation(_row(resultat_obs=None))
    assert observation.value is None
    assert observation.validity is PointValidity.MISSING
    assert observation.missing_reason is MissingReason.NOT_MEASURED
    assert observation.value != 0.0


def test_a_row_without_a_station_code_has_no_station():
    row = _row(code_station=None)
    with pytest.raises(InterpretationError):
        station_from_row(row)


def test_a_row_without_a_station_code_is_refused_and_counted():
    rows = [_row(), _row(code_station=None, code_site="B1111110"), _row(date_obs=None)]
    stations = {
        station.code_station: station
        for station in (station_from_row(row) for row in rows if row.get("code_station"))
    }
    observations, refused = observations_from_rows(
        rows,
        stations=stations,
        source_id=SOURCE_ID,
        evidence_id="evidence-1",
        acquired_at=ACQUIRED_AT,
    )
    assert len(observations) == 1
    assert refused == 2


def test_the_source_native_key_keeps_the_source_names():
    observation = _observation()
    assert observation.key == "A4050620_A405062001_Q_2026-11-01T11:40:00Z"


def test_the_observation_identifier_does_not_depend_on_the_order_of_the_rows():
    first = _observation()
    second = _observation()
    assert first.observation_id == second.observation_id
    assert first.observation_id == "A405062001:Q:2026-11-01T11:40:00+00:00"


# --------------------------------------------------------------------------
# The quality the agency declares
# --------------------------------------------------------------------------


def test_a_validated_value_is_approved():
    assert quality_from_row(_row(libelle_statut="Validée")) is QualityStatus.APPROVED


def test_a_raw_value_is_provisional():
    assert quality_from_row(_row(libelle_statut="Brute")) is QualityStatus.PROVISIONAL


def test_an_unreadable_label_is_unknown_and_never_approved():
    assert quality_from_row(_row(libelle_statut="Surbruge")) is QualityStatus.UNKNOWN
    assert quality_from_row(_row(libelle_statut=None)) is QualityStatus.UNKNOWN
    assert quality_from_row({}) is QualityStatus.UNKNOWN


# --------------------------------------------------------------------------
# The chronology
# --------------------------------------------------------------------------


def test_the_series_are_put_in_chronological_order():
    late = _observation(_row(date_obs="2026-11-01T11:40:00Z"))
    early = _observation(_row(date_obs="2026-11-01T11:35:00Z"))
    middle = _observation(_row(date_obs="2026-11-01T11:37:30Z"))
    places = series_of((late, early, middle), quantity="discharge")
    assert [instant for instant, _ in places] == [
        datetime(2026, 11, 1, 11, 35, tzinfo=UTC),
        datetime(2026, 11, 1, 11, 37, 30, tzinfo=UTC),
        datetime(2026, 11, 1, 11, 40, tzinfo=UTC),
    ]


def test_a_missing_observation_is_not_part_of_a_series():
    valid = _observation()
    missing = _observation(_row(resultat_obs=None))
    places = series_of((valid, missing), quantity="discharge")
    assert len(places) == 1


# --------------------------------------------------------------------------
# The profile of a station
# --------------------------------------------------------------------------


def _station_rows(code: str = "A405062001", instants: int = 4) -> list[dict]:
    """The rows of one station: a height and a discharge every five minutes."""
    rows: list[dict] = []
    depart = datetime(2026, 11, 1, 11, 0, tzinfo=UTC)
    for index in range(instants):
        instant = (depart + timedelta(minutes=5 * index)).isoformat().replace("+00:00", "Z")
        rows.append(_row(code_station=code, date_obs=instant, grandeur_hydro="H"))
        rows.append(_row(code_station=code, date_obs=instant, grandeur_hydro="Q"))
    return rows


def test_the_profile_counts_the_instants_and_the_missing_values():
    rows = _station_rows()
    rows.append(_row(code_station="A405062001", grandeur_hydro="Q", resultat_obs=None))
    profiles = profile_stations(rows)
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.code_station == "A405062001"
    assert profile.instants_by_quantity == {"H": 4, "Q": 4}
    assert profile.missing_by_quantity == {"Q": 1}
    assert profile.paired_instants == 4
    assert profile.sampling_interval_seconds == 300.0
    assert profile.completeness is not None


def test_a_row_without_a_station_code_does_not_create_a_station():
    profiles = profile_stations([_row(code_station=None)])
    assert profiles == ()


def test_the_selection_refuses_when_no_station_meets_the_criteria():
    profiles = profile_stations(_station_rows(instants=2))
    with pytest.raises(ValueError, match="no station meets the declared criteria"):
        select_station(profiles, StationCriteria(minimum_paired_instants=10))


def test_the_selection_keeps_the_station_with_the_longest_paired_record():
    rows = _station_rows("A405062001", instants=4) + _station_rows("B111111001", instants=6)
    profiles = profile_stations(rows)
    chosen = select_station(profiles, StationCriteria(minimum_paired_instants=2))
    assert chosen.code_station == "B111111001"


def test_the_selection_is_broken_by_the_code_and_not_by_the_values():
    rows = _station_rows("A405062001", instants=4) + _station_rows("B111111001", instants=4)
    profiles = profile_stations(rows)
    chosen = select_station(profiles, StationCriteria(minimum_paired_instants=2))
    assert chosen.code_station == "A405062001"


def test_a_station_with_a_missing_value_is_refused_when_the_criteria_say_so():
    rows = _station_rows()
    rows.append(_row(code_station="A405062001", grandeur_hydro="Q", resultat_obs=None))
    profiles = profile_stations(rows)
    with pytest.raises(ValueError, match="no station meets the declared criteria"):
        select_station(profiles, StationCriteria(require_no_missing_value=True))


# --------------------------------------------------------------------------
# The adapter of the network feed
# --------------------------------------------------------------------------


def _page(rows: list[dict], *, next_url: str | None = None) -> HttpResponse:
    payload = {
        "count": 24537488,
        "api_version": "2.0.1",
        "data": rows,
    }
    if next_url is not None:
        payload["next"] = next_url
    return HttpResponse(
        status_code=206,
        body=json.dumps(payload).encode("utf-8"),
        url=URL_OBSERVATIONS_TR,
    )


def test_the_first_question_asks_for_the_quantity_and_for_nothing_else():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    request = adapter.initial_request()
    assert request.url == URL_OBSERVATIONS_TR
    assert request.params["grandeur_hydro"] == "Q"
    assert request.params["size"] == "2000"
    assert request.pagination is PaginationStrategy.CURSOR
    # The source does not apply these filters: asking for them would be
    # asking a question the source does not answer.
    assert "code_station" not in request.params
    assert "date_debut" not in request.params
    assert "date_fin" not in request.params


def test_the_walk_follows_the_next_link():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    following = f"{URL_OBSERVATIONS_TR}?format=json&size=2000&grandeur_hydro=Q&cursor=abc"
    response = _page([_row()], next_url=following)
    request = adapter.next_request(adapter.initial_request(), response)
    assert request is not None
    assert request.params["cursor"] == "abc"


def test_the_walk_is_over_when_the_provider_gives_no_next_link():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    response = _page([_row()])
    assert adapter.next_request(adapter.initial_request(), response) is None


def test_an_empty_page_ends_the_walk():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    response = _page([], next_url=f"{URL_OBSERVATIONS_TR}?cursor=abc")
    assert adapter.next_request(adapter.initial_request(), response) is None


def test_the_verdict_is_rendered_from_the_rows_that_came_back():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    response = _page([_row(grandeur_hydro="Q"), _row(grandeur_hydro="Q")])
    verdict = adapter.verdict_conformite(adapter.initial_request(), response)
    assert verdict.conformite is Conformite.CONFORME
    assert verdict.criteres["grandeur_hydro"].verifie is True


def test_a_page_that_carries_another_quantity_is_not_conforme():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    response = _page([_row(grandeur_hydro="H")])
    verdict = adapter.verdict_conformite(adapter.initial_request(), response)
    assert verdict.conformite is Conformite.NON_CONFORME


def test_a_page_without_the_quantity_cannot_be_verified():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    response = _page([{"code_station": "A405062001"}])
    verdict = adapter.verdict_conformite(adapter.initial_request(), response)
    assert verdict.conformite is Conformite.INDETERMINATE


def test_the_adapter_declares_the_exhaustion_of_its_walk():
    adapter = HubeauFeedAdapter(grandeur_hydro="Q", page_size=2000, max_pages=5)
    assert adapter.declares_exhaustion is True
