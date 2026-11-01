"""The publication of a knowledge product, and what a reader gets back.

The store is the first half of the chain that makes a product readable by an
application: it writes the record and the payload it points at, and it reads
them back. These tests hold the three rules it declares — a product is never
rewritten, the store computes nothing, and an absent product is an absence
rather than an empty series.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from torne.contracts.knowledge import KnowledgeProduct, ProductStatus, ProvenanceKind, ProvenanceRef
from torne.contracts.model import ResultNature
from torne.contracts.observation import QualityStatus
from torne.knowledge.store import (
    RECORD_FILE,
    RecordExists,
    RecordNotFound,
    list_products,
    list_versions,
    load_record,
    read_record,
    write_record,
)

PAYLOAD = {
    "states.csv": b"entity,day,value\nA,2026-01-01,1.0\n",
    "indicators.json": b'{"total": 1.0}',
}


def build_product(
    product_id: str = "gas-supply-europe",
    version: str = "2026-10-31",
    summary: dict[str, object] | None = None,
) -> KnowledgeProduct:
    return KnowledgeProduct(
        product_id=product_id,
        version=version,
        nature=ResultNature.RECONSTRUCTED,
        produced_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
        status=ProductStatus.USABLE,
        domain_of_validity="The European gas terminals, over the gas day window of the product.",
        uncertainty="The derived entry is a lower bound; the coverage is an upper bound.",
        lineage=(
            ProvenanceRef(
                kind=ProvenanceKind.OBSERVATION,
                identifier="alsi-terminal-states",
                label="The daily terminal states published by GIE.",
            ),
            ProvenanceRef(
                kind=ProvenanceKind.SOURCE,
                identifier="gie-alsi",
                label="GIE ALSI",
            ),
        ),
        summary=summary or {"installations": 25},
        input_statuses={"alsi-terminal-states": QualityStatus.APPROVED},
    )


def test_a_published_record_is_read_back_unchanged(tmp_path: Path) -> None:
    product = build_product()
    write_record(tmp_path, product, PAYLOAD)

    stored = load_record(tmp_path, "gas-supply-europe")

    assert stored.product_id == "gas-supply-europe"
    assert stored.version == "2026-10-31"
    assert stored.record.as_dict() == product.as_dict()
    assert stored.record.lineage == product.lineage
    assert stored.record.input_statuses == product.input_statuses


def test_the_payload_is_written_beside_the_record(tmp_path: Path) -> None:
    write_record(tmp_path, build_product(), PAYLOAD)

    stored = load_record(tmp_path, "gas-supply-europe")

    assert sorted(stored.payload) == ["indicators.json", "states.csv"]
    assert stored.payload["states.csv"].read_bytes() == PAYLOAD["states.csv"]


def test_publishing_twice_changes_nothing(tmp_path: Path) -> None:
    """A publication can be re-run without ceremony."""
    product = build_product()
    write_record(tmp_path, product, PAYLOAD)
    first = load_record(tmp_path, "gas-supply-europe")

    write_record(tmp_path, product, PAYLOAD)
    second = load_record(tmp_path, "gas-supply-europe")

    assert first.payload_digest == second.payload_digest
    assert second.record.as_dict() == product.as_dict()


def test_a_published_product_is_not_rewritten(tmp_path: Path) -> None:
    """INV-31: a correction is a new version, not a rewrite."""
    write_record(tmp_path, build_product(), PAYLOAD)

    with pytest.raises(RecordExists):
        write_record(tmp_path, build_product(), {**PAYLOAD, "states.csv": b"changed"})


def test_a_published_record_is_not_rewritten_either(tmp_path: Path) -> None:
    """The description of a product is part of the product.

    A publisher who changes what a published product says — while its payload
    stays the same — is rewriting it. The store refuses, and says that a
    correction is a new version.
    """
    write_record(tmp_path, build_product(), PAYLOAD)

    corrected = build_product(summary={"installations": 26})
    with pytest.raises(RecordExists):
        write_record(tmp_path, corrected, PAYLOAD)

    stored = load_record(tmp_path, "gas-supply-europe")
    assert stored.record.as_dict() == build_product().as_dict(), (
        "the published record is the one that was published"
    )


def test_publishing_the_same_thing_again_changes_nothing(tmp_path: Path) -> None:
    """The publication is re-runnable: the same product, the same payload."""
    write_record(tmp_path, build_product(), PAYLOAD)
    path = tmp_path / "gas-supply-europe" / "2026-10-31" / RECORD_FILE
    before = path.read_bytes()

    write_record(tmp_path, build_product(), PAYLOAD)

    assert path.read_bytes() == before


def test_a_new_version_sits_beside_the_old_one(tmp_path: Path) -> None:
    write_record(tmp_path, build_product(), PAYLOAD)
    write_record(tmp_path, build_product(version="2026-11-30"), PAYLOAD)

    versions = list_versions(tmp_path, "gas-supply-europe")

    assert versions == ("2026-10-31", "2026-11-30")
    assert load_record(tmp_path, "gas-supply-europe").version == "2026-11-30"
    assert load_record(tmp_path, "gas-supply-europe", "2026-10-31").version == "2026-10-31"


def test_an_absent_product_is_an_absence(tmp_path: Path) -> None:
    with pytest.raises(RecordNotFound):
        load_record(tmp_path, "nothing-published")


def test_an_absent_version_is_an_absence(tmp_path: Path) -> None:
    write_record(tmp_path, build_product(), PAYLOAD)

    with pytest.raises(RecordNotFound):
        load_record(tmp_path, "gas-supply-europe", "1999-01-01")


def test_a_tampered_payload_is_detected(tmp_path: Path) -> None:
    """The payload is the one that was published, or it is nothing."""
    write_record(tmp_path, build_product(), PAYLOAD)
    stored = load_record(tmp_path, "gas-supply-europe")
    stored.payload["states.csv"].write_bytes(b"entity,day,value\nA,2026-01-01,9.9\n")

    with pytest.raises(RecordNotFound):
        load_record(tmp_path, "gas-supply-europe")


def test_a_record_whose_statuses_disagree_is_refused(tmp_path: Path) -> None:
    """The contract's checks run again when the record is read."""
    write_record(tmp_path, build_product(), PAYLOAD)
    path = tmp_path / "gas-supply-europe" / "2026-10-31" / RECORD_FILE

    import json

    document = json.loads(path.read_text(encoding="utf-8"))
    document["product"]["input_statuses"] = {}
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="ne porte pas son statut"):
        read_record(path)


def test_the_products_are_listed_in_name_order(tmp_path: Path) -> None:
    write_record(tmp_path, build_product(product_id="b-product"), PAYLOAD)
    write_record(tmp_path, build_product(product_id="a-product"), PAYLOAD)

    assert list_products(tmp_path) == ("a-product", "b-product")


def test_an_empty_store_lists_nothing(tmp_path: Path) -> None:
    assert list_products(tmp_path) == ()
    assert list_versions(tmp_path, "gas-supply-europe") == ()
