"""The USGS OGC adapter — the questions it asks, and the verdicts it renders.

Every payload here was **recorded** from the live API on 2026-11-01
(development machine). No test touches the network: what is tested is the
adapter, not the provider.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from torne.acquisition.adapters.usgs_ogc import (
    BASE_URL,
    CREDENTIAL_REF,
    STATISTICS_URL,
    UsgsObservationNormalsAdapter,
    UsgsOgcItemsAdapter,
)
from torne.acquisition.contracts import (
    AcquisitionRequest,
    Conformite,
    HttpResponse,
)

STATION = "USGS-05587450"

_ENVELOPPE = {
    "type": "FeatureCollection",
    "numberReturned": 2,
    "timeStamp": "2026-11-01T10:17:59.606698Z",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "time_series_id": "bda68b74ed2e4110902f43f353dcfdd1",
                "monitoring_location_id": STATION,
                "parameter_code": "00060",
                "statistic_id": "00003",
                "time": "2024-01-02",
                "value": "67700",
                "unit_of_measure": "ft^3/s",
                "approval_status": "Approved",
                "qualifier": None,
                "last_modified": "2025-08-28T06:16:44.497456+00:00",
            },
            "id": "024ba6e0-c7b7-4d64-aba8-403e0bc48947",
            "geometry": {"type": "Point", "coordinates": [-90.429, 38.9679722222222]},
        },
        {
            "type": "Feature",
            "properties": {
                "time_series_id": "bda68b74ed2e4110902f43f353dcfdd1",
                "monitoring_location_id": STATION,
                "parameter_code": "00060",
                "statistic_id": "00003",
                "time": "2024-01-03",
                "value": "61000",
                "unit_of_measure": "ft^3/s",
                "approval_status": "Approved",
                "qualifier": None,
                "last_modified": "2025-08-28T06:16:44.497456+00:00",
            },
            "id": "5d2f6a08-4e1e-4a9b-9d9c-0b0a3f1f8c21",
            "geometry": {"type": "Point", "coordinates": [-90.429, 38.9679722222222]},
        },
    ],
    "links": [
        {
            "rel": "next",
            "href": (
                "https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/items"
                "?cursor=YTUyMGE4MGYtMWUwOC00YWU0LWExNTUtMGNjZjIzYTlmNmMx"
                f"&monitoring_location_id={STATION}&limit=2&f=json"
            ),
            "type": "application/geo+json",
            "title": "Items (next)",
        },
        {"rel": "self", "href": "https://example.test/self"},
    ],
}


def _reponse(payload: dict) -> HttpResponse:
    return HttpResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def _adaptateur() -> UsgsOgcItemsAdapter:
    return UsgsOgcItemsAdapter(
        collection="daily",
        monitoring_location_id=STATION,
        parameter_codes=("00060",),
        datetime_range=("2024-01-01", "2024-01-05"),
        limit=2,
    )


# --------------------------------------------------------------------------
# The question
# --------------------------------------------------------------------------


def test_the_first_request_carries_the_station_the_window_and_the_parameters():
    """The request says exactly what was asked, and nothing implicit."""
    demande = _adaptateur().initial_request()

    assert demande.url == f"{BASE_URL}/collections/daily/items"
    assert demande.params["monitoring_location_id"] == STATION
    assert demande.params["parameter_code"] == "00060"
    assert demande.params["datetime"] == "2024-01-01/2024-01-05"
    assert demande.params["f"] == "json"
    assert demande.credential_ref == CREDENTIAL_REF


def test_the_key_never_appears_in_the_recorded_request():
    """The secret leaves at the last moment, and never enters the record."""
    demande = _adaptateur().initial_request()

    assert demande.credential_ref == CREDENTIAL_REF
    assert "api_key" not in demande.params
    assert "DEMO_KEY" not in demande.effective_url


def test_a_station_without_its_agency_code_is_refused():
    """`05587450` alone matches nothing: the agency code is part of the key."""
    with pytest.raises(ValueError, match="agency_code"):
        UsgsOgcItemsAdapter(collection="daily", monitoring_location_id="05587450")


def test_the_limit_is_bounded_by_the_provider():
    """The provider refuses more than 50000 items per request."""
    for limite in (0, 50_001):
        try:
            UsgsOgcItemsAdapter(
                collection="daily",
                monitoring_location_id=STATION,
                limit=limite,
            )
        except ValueError:
            continue
        raise AssertionError(f"limit {limite} must be refused")


# --------------------------------------------------------------------------
# The traversal
# --------------------------------------------------------------------------


def test_the_next_page_is_followed_verbatim():
    """The `next` link is absolute and already carries the filters.

    Rebuilding the query by hand is how a traversal silently changes its
    question: the cursor is the provider's own, and it is followed verbatim.
    """
    adaptateur = _adaptateur()
    demande = adaptateur.initial_request()

    suivante = adaptateur.next_request(demande, _reponse(_ENVELOPPE))

    assert suivante is not None
    assert suivante.url == _ENVELOPPE["links"][0]["href"]
    assert suivante.params == {}
    assert suivante.credential_ref == CREDENTIAL_REF


def test_the_absence_of_a_next_link_ends_the_traversal():
    """The end of the traversal is the absence of the `next` link."""
    payload = dict(_ENVELOPPE)
    payload["links"] = [link for link in _ENVELOPPE["links"] if link["rel"] != "next"]
    adaptateur = _adaptateur()

    suivante = adaptateur.next_request(adaptateur.initial_request(), _reponse(payload))

    assert suivante is None


def test_the_source_declares_its_exhaustion():
    """The provider says when there is nothing left; that is a declaration."""
    assert _adaptateur().declares_exhaustion is True


# --------------------------------------------------------------------------
# The verdict
# --------------------------------------------------------------------------


def test_a_conformant_page_is_conformant():
    """The records received are the ones that were asked for."""
    adaptateur = _adaptateur()

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(_ENVELOPPE),
    )

    assert verdict.conformite is Conformite.CONFORME
    assert verdict.conforme is True
    assert verdict.criteres["monitoring_location_id"].recu == STATION


def test_a_foreign_station_is_non_conformant():
    """A record from another station answers another question."""
    payload = json.loads(json.dumps(_ENVELOPPE))
    payload["features"][0]["properties"]["monitoring_location_id"] = "USGS-07001000"
    adaptateur = _adaptateur()

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(payload),
    )

    assert verdict.conformite is Conformite.NON_CONFORME
    assert "USGS-07001000" in (verdict.motif or "")


def test_a_foreign_parameter_is_non_conformant():
    """A parameter that was not asked for answers another question."""
    payload = json.loads(json.dumps(_ENVELOPPE))
    payload["features"][0]["properties"]["parameter_code"] = "00065"
    adaptateur = _adaptateur()

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(payload),
    )

    assert verdict.conformite is Conformite.NON_CONFORME
    assert "00065" in (verdict.motif or "")


def test_an_empty_page_is_indeterminate():
    """An empty response cannot verify anything.

    The station asked for may hold no data at all — and a verdict that said
    "conformant" would be certifying something nobody saw.
    """
    adaptateur = _adaptateur()
    payload = dict(_ENVELOPPE)
    payload["features"] = []

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(payload),
    )

    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.criteres["monitoring_location_id"].verifie is False


def test_a_missing_field_is_indeterminate():
    """A record that does not carry the fields needed cannot be read."""
    payload = json.loads(json.dumps(_ENVELOPPE))
    del payload["features"][1]["properties"]["value"]
    adaptateur = _adaptateur()

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(payload),
    )

    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.criteres["required_fields"].verifie is False
    assert "value" in (verdict.motif or "")


def test_an_unreadable_response_is_a_format_error():
    """A body that is not JSON is a source failure, not a conformity."""
    adaptateur = _adaptateur()
    reponse = HttpResponse(status_code=200, headers={}, body=b"<html>oops</html>")

    with pytest.raises(ValueError, match="unreadable"):
        adaptateur.verdict_conformite(adaptateur.initial_request(), reponse)


# --------------------------------------------------------------------------
# The independent reference
# --------------------------------------------------------------------------

_NORMALES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-90.429, 38.96797222]},
            "properties": {
                "monitoring_location_id": STATION,
                "monitoring_location_name": "Mississippi River at Grafton, IL",
                "site_type": "Stream",
                "data": [
                    {
                        "parameter_code": "00060",
                        "unit_of_measure": "ft^3/s",
                        "parent_time_series_id": "bda68b74ed2e4110902f43f353dcfdd1",
                        "parent_statistic_id": "00003",
                        "parent_statistic_name": "Mean",
                        "values": [
                            {
                                "time_of_year": "01-02",
                                "time_of_year_type": "day_of_year",
                                "value": "61000",
                                "sample_count": 91,
                                "approval_status": "approved",
                                "computation": "arithmetic_mean",
                            }
                        ],
                    }
                ],
            },
        }
    ],
    "next": None,
}


def test_the_independent_reference_is_asked_at_its_own_address():
    """The statistics live in another service, and it is asked directly."""
    adaptateur = UsgsObservationNormalsAdapter(
        monitoring_location_id=STATION,
        parameter_codes=("00060",),
    )

    demande = adaptateur.initial_request()

    assert demande.url == f"{STATISTICS_URL}/observationNormals"
    assert demande.params["monitoring_location_id"] == STATION
    assert demande.params["parameter_code"] == "00060"


def test_the_independent_reference_is_conformant():
    """The parameter codes are read on the `data` blocks, where they are."""
    adaptateur = UsgsObservationNormalsAdapter(
        monitoring_location_id=STATION,
        parameter_codes=("00060",),
    )

    verdict = adaptateur.verdict_conformite(
        adaptateur.initial_request(),
        _reponse(_NORMALES),
    )

    assert verdict.conformite is Conformite.CONFORME
    assert verdict.criteres["parameter_codes"].recu == "00060"


def test_the_independent_reference_does_not_paginate_further():
    """A `null` `next` ends the traversal of the statistics service."""
    adaptateur = UsgsObservationNormalsAdapter(monitoring_location_id=STATION)

    suivante = adaptateur.next_request(
        adaptateur.initial_request(),
        _reponse(_NORMALES),
    )

    assert suivante is None


def test_the_next_page_token_is_carried_over():
    """The statistics service pages with a token, not with a cursor."""
    payload = dict(_NORMALES)
    payload["next"] = "eyJwYWdlIjoyfQ=="
    adaptateur = UsgsObservationNormalsAdapter(monitoring_location_id=STATION)

    suivante = adaptateur.next_request(
        adaptateur.initial_request(),
        _reponse(payload),
    )

    assert suivante is not None
    assert suivante.params["next_token"] == "eyJwYWdlIjoyfQ=="


# --------------------------------------------------------------------------
# The request that actually goes on the wire
# --------------------------------------------------------------------------


def test_the_effective_url_carries_exactly_the_filters():
    """The URL that goes on the wire carries the question, and it is parsable."""
    demande = _adaptateur().initial_request()

    requete = urlsplit(demande.effective_url)
    params = parse_qs(requete.query)

    assert requete.path == "/ogcapi/v1/collections/daily/items"
    assert params["monitoring_location_id"] == [STATION]
    assert params["datetime"] == ["2024-01-01/2024-01-05"]
    assert params["limit"] == ["2"]


def test_a_request_without_parameters_stays_a_url():
    """A next page whose link is already complete is not re-parameterised."""
    adaptateur = _adaptateur()
    demande = adaptateur.initial_request()
    suivante = adaptateur.next_request(demande, _reponse(_ENVELOPPE))

    assert isinstance(suivante, AcquisitionRequest)
    assert suivante.effective_url == _ENVELOPPE["links"][0]["href"]
