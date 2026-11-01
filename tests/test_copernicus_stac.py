"""The Copernicus STAC adapter — the questions, and the conformity gate.

The adapter poses questions to the catalogue and renders one verdict per page.
These tests exercise both halves.

The **question** half checks that what is asked is what the server is asked:
the collections, the RFC 3339 window — which the catalogue rejects when it is
written as a bare date — the extent, and the pagination, whose `next` link is
an absolute URL carrying a token that must be decoded back into parameters
rather than pasted into a string.

The **verdict** half checks the gate itself. Three behaviours matter, and they
are the ones a lazy predicate gets wrong:

- an item from another collection is a **violation**;
- an item whose field cannot be read is an **abstention**, not a violation
  — the source did not break the request, nobody can say it did;
- an empty page is a **complete answer** ("there is none"), not a failure to
  verify.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from torne.acquisition.adapters.copernicus_stac import (
    SOURCE_ID,
    URL_SEARCH,
    CopernicusStacAdapter,
)
from torne.acquisition.contracts import Conformite, HttpResponse, PaginationStrategy
from torne.contracts.observation import PublicationClass
from torne.contracts.spatial import BoundingBox

START = datetime(2023, 1, 1, tzinfo=UTC)
END = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)
RHINE = BoundingBox(west=5.5, south=43.5, east=10.5, north=51.0)


def _adapter(**kwargs) -> CopernicusStacAdapter:
    defaults = {
        "collections": ["clms_swi_europe_1km_daily_v1_cog"],
        "start": START,
        "end": END,
        "page_size": 10,
        "max_pages": 5,
        "bbox": RHINE,
    }
    defaults.update(kwargs)
    return CopernicusStacAdapter(**defaults)


def _item(
    *,
    identifier: str = "item-1",
    collection: str = "clms_swi_europe_1km_daily_v1_cog",
    datetime_: str = "2023-06-30T12:00:01Z",
    bbox: list[float] | None = None,
    published: str | None = "2025-03-26T00:00:00Z",
) -> dict[str, object]:
    item: dict[str, object] = {
        "id": identifier,
        "collection": collection,
        "datetime": datetime_,
        "bbox": bbox if bbox is not None else [-11.0, 35.0, 50.0, 72.0],
        "properties": {},
        "assets": {},
    }
    if published is not None:
        item["properties"] = {"published": published}
    return item


def _response(items: list[dict[str, object]], *, next_link: str | None = None) -> HttpResponse:
    payload: dict[str, object] = {"features": items, "links": []}
    if next_link is not None:
        payload["links"] = [{"rel": "next", "href": next_link, "type": "application/geo+json"}]
    return HttpResponse(
        status_code=200,
        headers={"content-type": "application/geo+json"},
        body=json.dumps(payload).encode("utf-8"),
    )


# --------------------------------------------------------------------------
# The question
# --------------------------------------------------------------------------


def test_the_question_carries_the_collections_the_extent_and_the_window():
    request = _adapter().initial_request()

    assert request.source_id == SOURCE_ID
    assert request.url == URL_SEARCH
    assert request.pagination is PaginationStrategy.CURSOR
    assert request.params["collections"] == "clms_swi_europe_1km_daily_v1_cog"
    assert request.params["bbox"] == "5.5,43.5,10.5,51.0"
    assert request.params["limit"] == "10"


def test_the_window_is_written_the_way_the_catalogue_accepts_it():
    """The catalogue rejects a bare date: the separator and the hour are required."""
    request = _adapter().initial_request()

    assert request.params["datetime"] == "2023-01-01T00:00:00Z/2023-12-31T23:59:59Z"


def test_several_collections_are_asked_for_in_one_question():
    request = _adapter(collections=["a", "b"]).initial_request()

    assert request.params["collections"] == "a,b"


def test_a_question_without_an_extent_is_refused():
    """A search without an extent is not a search on a basin."""
    with pytest.raises(ValueError, match="an extent is required"):
        _adapter(bbox=None)


def test_a_question_without_collections_is_refused():
    with pytest.raises(ValueError, match="collections is required"):
        _adapter(collections=[])


def test_a_question_with_the_same_collection_twice_is_refused():
    with pytest.raises(ValueError, match="duplicate"):
        _adapter(collections=["a", "a"])


def test_a_polygon_replaces_the_envelope_in_the_question():
    polygon = {
        "type": "Polygon",
        "coordinates": [[[7.0, 47.0], [8.0, 47.0], [8.0, 48.0], [7.0, 48.0], [7.0, 47.0]]],
    }

    request = _adapter(bbox=None, geometry=polygon).initial_request()

    assert "bbox" not in request.params
    assert json.loads(request.params["intersects"])["type"] == "Polygon"


# --------------------------------------------------------------------------
# The pagination
# --------------------------------------------------------------------------


def test_the_next_page_is_read_from_the_link_the_catalogue_gives():
    link = f"{URL_SEARCH}?collections=a&token=abc123&limit=10"

    following = _adapter().next_request(
        _adapter().initial_request(), _response([_item()], next_link=link)
    )

    assert following is not None
    assert following.url == URL_SEARCH
    assert following.params["token"] == "abc123"


def test_no_link_means_no_next_question():
    assert _adapter().next_request(_adapter().initial_request(), _response([])) is None


def test_a_link_pointing_elsewhere_is_refused():
    link = "https://elsewhere.test/v1/search?token=abc"

    with pytest.raises(ValueError, match="points elsewhere"):
        _adapter().next_request(_adapter().initial_request(), _response([], next_link=link))


# --------------------------------------------------------------------------
# The verdict
# --------------------------------------------------------------------------


def test_a_page_of_the_requested_collection_is_conformant():
    verdict = _adapter().verdict_conformite(_adapter().initial_request(), _response([_item()]))

    assert verdict.conformite is Conformite.CONFORME
    assert verdict.conforme is True


def test_an_empty_page_is_a_complete_answer():
    """Zero items answers the question: there is none. It is not a failure."""
    verdict = _adapter().verdict_conformite(_adapter().initial_request(), _response([]))

    assert verdict.conformite is Conformite.CONFORME


def test_an_item_of_another_collection_violates_the_request():
    verdict = _adapter().verdict_conformite(
        _adapter().initial_request(),
        _response([_item(collection="sentinel-1-grd")]),
    )

    assert verdict.conformite is Conformite.NON_CONFORME
    assert verdict.motif is not None
    assert "sentinel-1-grd" in (verdict.criteres["collections"].recu or "")


def test_an_item_outside_the_requested_extent_violates_the_request():
    verdict = _adapter().verdict_conformite(
        _adapter().initial_request(),
        _response([_item(bbox=[-160.0, -20.0, -150.0, -10.0])]),
    )

    assert verdict.conformite is Conformite.NON_CONFORME


def test_an_item_outside_the_requested_window_violates_the_request():
    verdict = _adapter().verdict_conformite(
        _adapter().initial_request(),
        _response([_item(datetime_="2019-01-01T00:00:00Z")]),
    )

    assert verdict.conformite is Conformite.NON_CONFORME


def test_an_item_whose_bbox_cannot_be_read_makes_the_criterion_unverifiable():
    """The non-contamination rule: an unreadable field is an abstention."""
    item = _item()
    del item["bbox"]

    verdict = _adapter().verdict_conformite(_adapter().initial_request(), _response([item]))

    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.criteres["footprint"].verifie is False


def test_an_item_whose_instant_cannot_be_read_makes_the_criterion_unverifiable():
    item = _item()
    del item["datetime"]

    verdict = _adapter().verdict_conformite(_adapter().initial_request(), _response([item]))

    assert verdict.conformite is Conformite.INDETERMINATE
    assert verdict.criteres["window"].verifie is False


def test_a_violation_beats_an_abstention():
    """An established fact outweighs silence."""
    item = _item(collection="sentinel-1-grd")
    del item["bbox"]

    verdict = _adapter().verdict_conformite(_adapter().initial_request(), _response([item]))

    assert verdict.conformite is Conformite.NON_CONFORME


def test_an_unreadable_page_is_refused_rather_than_judged():
    adapter = _adapter()
    unreadable = HttpResponse(status_code=200, body=b"not json")

    with pytest.raises(ValueError, match="unreadable STAC response"):
        adapter.verdict_conformite(adapter.initial_request(), unreadable)


# --------------------------------------------------------------------------
# The source
# --------------------------------------------------------------------------


def test_the_source_declares_its_publication_class_as_established_by_execution():
    """Each item carries its own `published`: the catalogue timestamps its entries."""
    source = _adapter().source

    assert source.publication_class is PublicationClass.TIMESTAMPED
    assert source.source_id == SOURCE_ID


def test_the_source_declares_that_it_exhausts_its_own_traversal():
    assert _adapter().declares_exhaustion is True
