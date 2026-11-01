"""TORNE Explorer API — the published products it serves.

**A published product is served as it is.** The API reads what the repository
has written down, and it serves it: the identity of the product, its lineage,
the bounds it declares, the units it is expressed in, the confrontation that
validated it, and the states it carries. The application never recomputes a
number it has been given, and it never calls a provider.

**An absence stays an absence.** A product that was never published is a `404`,
not an empty series that looks like a measurement. A quantity that the published
payload does not carry — the derived entry of the first day of a series, which
has no previous day — is served as `null`, never as a zero. A cell that was
empty stays empty on the way out.

**Two layers, one product.** The European gas supply publishes a terminal layer
and a storage layer; the API serves each of them, and each of them in its own
right.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

GAS_PRODUCT = "gas-supply-europe"


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from torne.explorer.api import app

    return TestClient(app)


@pytest.fixture(scope="module")
def record():
    """The published record, read from the repository itself."""
    pytest.importorskip("fastapi")
    from torne.knowledge.store import list_products, load_record, records_root

    root = records_root()
    products = list_products(root)
    if GAS_PRODUCT not in products:
        pytest.skip(f"{GAS_PRODUCT} is not published in this checkout")
    return load_record(root, GAS_PRODUCT)


def test_the_products_that_were_published_are_listed(client):
    """The list names the published products, and what each one is."""
    answer = client.get("/api/products")
    assert answer.status_code == 200

    products = answer.json()["products"]
    published = [p for p in products if p["product_id"] == GAS_PRODUCT]
    assert published, "the published product must be listed"

    product = published[0]
    assert product["version"] == "2026-10-31"
    assert product["status"] == "usable"
    assert product["title"]
    assert product["domain_of_validity"]
    assert product["uncertainty"], "a product says what it does not guarantee"
    assert product["payload_digest"], "a published product carries the digest of its payload"


def test_a_product_that_was_never_published_is_not_found(client):
    """An absent product is a 404, not an empty product."""
    answer = client.get("/api/products/no-such-product")

    assert answer.status_code == 404
    assert "error" in answer.json() or "detail" in answer.json()


def test_the_product_serves_its_identity_its_lineage_and_its_bounds(client):
    """What the product is, where it comes from, and what it does not claim."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    detail = answer.json()
    assert detail["product_id"] == GAS_PRODUCT
    assert detail["version"] == "2026-10-31"
    assert detail["status"] == "usable"
    assert detail["nature"] == "reconstructed"
    assert detail["reference_date"] == "2026-10-31"

    assert detail["lineage"], "a product publishes its lineage"
    kinds = {ref["kind"] for ref in detail["lineage"]}
    assert "source" in kinds
    assert "evaluation" in kinds

    assert detail["bounds"], "a product that publishes bounds declares them"
    for bound in detail["bounds"]:
        assert bound["direction"] in ("lower", "upper")
        assert bound["statement"], "a bound says why it is a bound"

    assert detail["payload_files"], "a product names the files it publishes"
    assert detail["units"]["measures"], "a product says in what unit it is expressed"


def test_the_product_serves_the_indicators_of_each_of_its_layers(client, record):
    """The indicators are typed, layer by layer."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    indicators = answer.json()["indicators"]
    declared = dict(record.record.summary)["indicators"]

    terminals = indicators["terminals"]
    assert terminals["installations"] == declared["terminals"]["installations"]
    assert terminals["states"] == declared["terminals"]["states"]
    assert terminals["system_coverage_days"] > 0
    assert terminals["concentration"]["herfindahl"] >= 0

    storage = indicators["storage"]
    assert len(storage["coverage"]) == 30
    assert storage["indicators"], "the storage layer publishes what each country holds"
    assert storage["units"]["stock"]


def test_the_window_of_each_layer_is_served_with_its_counts(client, record):
    """The period each layer covers, and what it holds.

    The counts are the ones the published record declares: the API serves the
    product, it does not count it again.
    """
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    windows = answer.json()["windows"]
    declared = dict(record.record.summary)["windows"]

    assert windows["terminals"]["start"] == declared["terminals"]["start"]
    assert windows["terminals"]["end"] == declared["terminals"]["end"]
    assert windows["terminals"]["states"] == declared["terminals"]["states"]
    assert windows["terminals"]["entities"] == declared["terminals"]["installations"]
    assert windows["storage"]["states"] == declared["storage"]["states"]
    assert windows["storage"]["entities"] == declared["storage"]["countries"]
    assert windows["terminals"]["entities"] == 25
    assert windows["storage"]["entities"] == 30


def test_the_confrontation_that_validated_the_product_is_served(client, record):
    """The validation is part of the product, and it is served with it."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    validation = answer.json()["validation"]
    declared = dict(record.record.summary)["validation"]
    assert validation["comparisons"] == declared["comparisons"]
    assert validation["comparisons"] > 0
    assert validation["median_relative_difference"] is not None
    assert validation["max_relative_difference"] is not None
    assert validation["method"], "the confrontation says how it was made"


def test_the_states_of_the_terminal_layer_are_the_last_state_of_every_installation(client, record):
    """Without an entity, the map's states are served: the last one of each."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}/states", params={"layer": "terminals"})
    assert answer.status_code == 200

    body = answer.json()
    assert body["product_id"] == GAS_PRODUCT
    assert body["layer"] == "terminals"

    declared = dict(record.record.summary)["windows"]["terminals"]
    states = body["states"]
    assert len(states) == declared["installations"]
    assert len({state["entity"] for state in states}) == len(states)

    for state in states:
        assert state["gas_day"] == "2026-10-31"
        assert state["country"]
        assert state["label"]
        assert state["values"]["stock_gwh"] is not None
        assert state["latitude"] is not None
        assert state["longitude"] is not None


def test_the_states_of_the_storage_layer_are_the_last_state_of_every_country(client):
    """The second layer is served in its own right.

    Only the countries that published a usable state have states. The platform
    answered for thirty countries; the nineteen that published nothing are
    declared as absences, not served as empty states.
    """
    answer = client.get(f"/api/products/{GAS_PRODUCT}/states", params={"layer": "storage"})
    assert answer.status_code == 200

    states = answer.json()["states"]
    assert len(states) == 19
    assert len({state["entity"] for state in states}) == 19
    assert all(state["values"]["stock_gwh"] is not None for state in states)


def test_the_series_of_a_country_that_published_nothing_is_empty(client):
    """An entity the product knows but that published nothing.

    The series is empty, not absent: the country is part of the product — the
    product declares it among the eleven — and an empty series is the honest
    answer to "what did it publish?". The layer itself, which the product does
    not publish, is a `404`.
    """
    answer = client.get(
        f"/api/products/{GAS_PRODUCT}/states", params={"layer": "storage", "entity": "CH"}
    )
    assert answer.status_code == 200
    assert answer.json()["states"] == []


def test_the_countries_that_published_nothing_are_declared(client):
    """The countries the platform answered for but published nothing are named.

    They are absences, and the product says so: a reader must be able to tell
    "no state was published" from "this country does not exist".
    """
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    storage = answer.json()["indicators"]["storage"]
    assert len(storage["coverage"]) == 30
    without = storage["countries_without_published_state"]
    assert without == [
        "CH",
        "CY",
        "EE",
        "FI",
        "GR",
        "IE",
        "LT",
        "LU",
        "MT",
        "NO",
        "SI",
    ]
    published = {indicator["country"] for indicator in storage["indicators"]}
    assert not set(without) & published, "a country is either published or absent, not both"
    assert set(without) | published == set(storage["coverage"])
    assert len(storage["coverage"]) == len(published) + len(without)


def test_a_country_that_published_nothing_has_no_state(client):
    """The eleven countries that published nothing are absent from the states."""
    states = client.get(f"/api/products/{GAS_PRODUCT}/states", params={"layer": "storage"}).json()[
        "states"
    ]
    published = {state["entity"] for state in states}

    assert "CH" not in published
    assert "SI" not in published
    assert len(published) == 19


def test_the_series_of_one_entity_is_served_in_full(client):
    """With an entity, the whole series of that entity is served."""
    states = client.get(
        f"/api/products/{GAS_PRODUCT}/states", params={"layer": "terminals"}
    ).json()["states"]
    entity = states[0]["entity"]

    answer = client.get(
        f"/api/products/{GAS_PRODUCT}/states",
        params={"layer": "terminals", "entity": entity},
    )
    assert answer.status_code == 200

    series = answer.json()["states"]
    assert len(series) > 1, "a series holds more than its last state"
    assert all(state["entity"] == entity for state in series)
    days = [state["gas_day"] for state in series]
    assert days == sorted(days), "a series is served in chronological order"


def test_a_quantity_that_was_not_published_is_served_as_null_and_not_as_zero(client):
    """The first day of a series has no derived entry: it has no previous day.

    An absence is not a zero, and the API does not turn one into the other.
    """
    states = client.get(
        f"/api/products/{GAS_PRODUCT}/states", params={"layer": "terminals"}
    ).json()["states"]
    entity = states[0]["entity"]

    series = client.get(
        f"/api/products/{GAS_PRODUCT}/states",
        params={"layer": "terminals", "entity": entity},
    ).json()["states"]

    first = series[0]
    assert first["values"]["derived_entry_gwh"] is None, (
        "the first day has no derived entry, and it is served as null, not as zero"
    )
    assert first["values"]["stock_gwh"] is not None, "the stock it published is still there"


def test_the_faces_of_the_confrontation_are_served_day_by_day(client):
    """The confrontation is served as the comparison it is."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}/confrontation")
    assert answer.status_code == 200

    body = answer.json()
    assert body["product_id"] == GAS_PRODUCT
    assert body["comparisons"] == 210
    assert len(body["rows"]) == 210

    row = body["rows"][0]
    assert row["terminal_eic"]
    assert row["alsi_day"]
    assert row["operator_day"]
    assert row["alsi_stock_gwh"] is not None
    assert row["operator_stock_gwh"] is not None


def test_a_layer_that_the_product_does_not_publish_is_not_found(client):
    """An unknown layer is an absence, not an empty list of states."""
    answer = client.get(f"/api/products/{GAS_PRODUCT}/states", params={"layer": "coal"})

    assert answer.status_code == 404


def test_the_api_serves_the_published_payload_and_not_a_recomputation(client, record):
    """The numbers the API serves are the numbers the record carries.

    The application does not round, adjust or recompute: it reads what was
    published and serves it.
    """
    answer = client.get(f"/api/products/{GAS_PRODUCT}")
    assert answer.status_code == 200

    detail = answer.json()
    assert detail["payload_digest"] == record.payload_digest
    assert detail["version"] == record.record.version
    assert detail["status"] == record.record.status.value
    assert detail["domain_of_validity"] == record.record.domain_of_validity
    assert detail["uncertainty"] == record.record.uncertainty

    summary = dict(record.record.summary)
    assert detail["title"] == summary["title"]
    assert (
        detail["indicators"]["terminals"]["states"] == summary["indicators"]["terminals"]["states"]
    )
    assert len(detail["indicators"]["storage"]["indicators"]) == len(
        summary["indicators"]["storage"]["indicators"]
    )


def test_the_published_record_is_part_of_the_repository(client):
    """The record is a file of the repository, not a build artefact of the API."""
    path = ROOT / "src" / "torne" / "knowledge" / "records" / GAS_PRODUCT / "2026-10-31"
    assert (path / "record.json").exists()
    assert (path / "terminals.csv").exists()
    assert (path / "stocks.csv").exists()
    assert (path / "confrontation.csv").exists()
