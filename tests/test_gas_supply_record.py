"""The published European gas supply record, and what it commits to.

The record is a publication: it is committed, and it is read back by whatever
consumes what this repository has produced. These tests hold it against the
payload it points at — the counts, the windows, the entities it declares
absent, the figures of the confrontation — and against the script that
published it.

The tests that compare the publication with the production output are skipped
where the production output is absent: `data/` holds a production output, it is
not versioned, and a test that needs it says so rather than pretending to have
checked something it could not check.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import pytest

from torne.contracts.knowledge import ProductStatus
from torne.contracts.model import ResultNature
from torne.contracts.observation import QualityStatus
from torne.knowledge.store import RECORD_FILE, StoredRecord, load_record, records_root

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_gas_supply.py"
PRODUCTION = ROOT / "data" / "resource-004"
PRODUCT_ID = "gas-supply-europe"
VERSION = "2026-10-31"


@pytest.fixture(scope="module")
def stored() -> StoredRecord:
    """The committed record, read back by the store."""
    return load_record(records_root(), PRODUCT_ID, VERSION)


def _rows(path: Path) -> list[dict[str, str]]:
    """The rows of a payload file, as they are published."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _next_day(day: str) -> str:
    """The day after a gas day."""
    return (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()


def test_the_committed_record_loads_with_the_store(stored: StoredRecord) -> None:
    """The record is published, and the store reads it back unchanged."""
    assert stored.product_id == PRODUCT_ID
    assert stored.version == VERSION
    assert stored.record.nature is ResultNature.RECONSTRUCTED
    assert stored.record.status is ProductStatus.USABLE
    assert stored.record.produced_at == datetime(2026, 11, 1, 16, 20, 25, tzinfo=UTC)


def test_the_record_carries_the_digest_of_the_payload_it_points_at(
    stored: StoredRecord,
) -> None:
    """The store verifies the payload against the digest; the record carries it."""
    document = json.loads((stored.directory / RECORD_FILE).read_text(encoding="utf-8"))

    assert document["payload_digest"] == stored.payload_digest


def test_the_declared_windows_are_the_windows_of_the_payload(stored: StoredRecord) -> None:
    """What the record declares covers exactly what the payload holds."""
    summary = stored.record.summary
    terminals = _rows(stored.payload["terminals.csv"])
    stocks = _rows(stored.payload["stocks.csv"])
    terminal_window = summary["windows"]["terminals"]
    storage_window = summary["windows"]["storage"]

    terminal_days = sorted({row["gas_day"] for row in terminals})
    assert terminal_days[0] == terminal_window["start"]
    assert terminal_days[-1] == terminal_window["end"]
    assert len(terminals) == terminal_window["states"]

    storage_days = sorted({row["gas_day"] for row in stocks})
    assert storage_days[0] == storage_window["start"]
    assert storage_days[-1] == storage_window["end"]
    assert len(stocks) == storage_window["states"]


def test_the_declared_counts_are_the_counts_of_the_payload(stored: StoredRecord) -> None:
    """The states, the installations and the countries are the ones published."""
    summary = stored.record.summary
    terminals = _rows(stored.payload["terminals.csv"])
    stocks = _rows(stored.payload["stocks.csv"])

    assert (
        len({row["terminal_eic"] for row in terminals})
        == summary["windows"]["terminals"]["installations"]
    )
    assert (
        len({row["terminal_eic"] for row in terminals})
        == summary["indicators"]["terminals"]["installations"]
    )
    assert summary["indicators"]["terminals"]["states"] == summary["windows"]["terminals"]["states"]
    assert sum(entry["days"] for entry in summary["indicators"]["storage"]["indicators"]) == len(
        stocks
    )


def test_the_summary_carries_the_two_layers(stored: StoredRecord) -> None:
    """The two layers of the product, and the payload each of them names."""
    layers = stored.record.summary["layers"]

    assert sorted(layers) == ["storage", "terminals"]
    assert layers["terminals"]["file"] == "terminals.csv"
    assert layers["terminals"]["entity_column"] == "terminal_eic"
    assert layers["storage"]["file"] == "stocks.csv"
    assert layers["storage"]["entity_column"] == "country"


def test_the_countries_without_a_published_state_are_named(stored: StoredRecord) -> None:
    """The countries that published nothing are named, not silently absent."""
    storage = stored.record.summary["indicators"]["storage"]
    coverage = set(storage["coverage"])
    published = {entry["country"] for entry in storage["indicators"]}
    without_state = list(storage["countries_without_published_state"])
    stocks = _rows(stored.payload["stocks.csv"])

    assert without_state == ["CH", "CY", "EE", "FI", "GR", "IE", "LT", "LU", "MT", "NO", "SI"]
    assert len(coverage) == len(published) + len(without_state)
    assert published.isdisjoint(without_state)
    assert published | set(without_state) == coverage
    assert {row["country"] for row in stocks} == published
    assert set(without_state).isdisjoint({row["country"] for row in stocks})


def test_the_validation_figures_are_the_ones_the_confrontation_contains(
    stored: StoredRecord,
) -> None:
    """The declared deviations are the ones the committed confrontation holds."""
    validation = stored.record.summary["validation"]
    rows = _rows(stored.payload["confrontation.csv"])
    relatives = sorted(float(row["relative_difference"]) for row in rows)

    assert validation["comparisons"] == len(rows)
    assert validation["median_relative_difference"] == round(relatives[len(relatives) // 2], 4)
    assert validation["max_relative_difference"] == round(relatives[-1], 4)
    assert validation["file"] == "confrontation.csv"


def test_the_residual_holds_on_the_committed_confrontation(stored: StoredRecord) -> None:
    """Six terminals of the seven are below the operator, on every day."""
    rows = _rows(stored.payload["confrontation.csv"])
    biases: dict[str, list[float]] = {}
    for row in rows:
        reference = float(row["operator_stock_gwh"])
        bias = (float(row["alsi_stock_gwh"]) - reference) / reference
        biases.setdefault(row["operator_terminal"], []).append(bias)

    below = [sorted(values) for values in biases.values() if all(value < 0 for value in values)]

    assert len(biases) == 7
    assert len(below) == 6
    medians = [series[len(series) // 2] * 100 for series in below]
    assert round(max(medians), 2) == -0.29
    assert round(min(medians), 2) == -2.80


def test_the_installations_without_data_are_absent_from_the_payload(
    stored: StoredRecord,
) -> None:
    """The six installations the production declared without data are not published."""
    summary = stored.record.summary
    without_data = summary["indicators"]["terminals"]["installations_without_data"]
    terminals = _rows(stored.payload["terminals.csv"])
    entities = {row["terminal_eic"] for row in terminals}

    assert len(without_data) == 6
    assert entities.isdisjoint(without_data)


def test_the_payload_carries_exactly_the_entities_the_record_declares(
    stored: StoredRecord,
) -> None:
    """No entity is published that the record does not declare."""
    summary = stored.record.summary
    terminals = _rows(stored.payload["terminals.csv"])
    stocks = _rows(stored.payload["stocks.csv"])

    terminal_entities = {row["terminal_eic"] for row in terminals}
    assert len(terminal_entities) == summary["windows"]["terminals"]["installations"]
    assert len(terminal_entities) == summary["indicators"]["terminals"]["installations"]

    storage_entities = {row["country"] for row in stocks}
    declared_countries = {
        entry["country"] for entry in summary["indicators"]["storage"]["indicators"]
    }
    assert storage_entities == declared_countries
    assert summary["windows"]["storage"]["countries"] == len(
        summary["indicators"]["storage"]["coverage"]
    )


def test_the_published_terminal_states_keep_their_empty_cells(stored: StoredRecord) -> None:
    """A derived entry is absent when the day before it is unknown.

    The derived entry is the difference between two stocks and the withdrawal
    of the day: it needs the previous day. The first day of a series has no
    previous day, and the day after a gap in the series has none either. Both
    are absent, and neither is a zero.
    """
    terminals = _rows(stored.payload["terminals.csv"])
    by_installation: dict[str, list[dict[str, str]]] = {}
    for row in terminals:
        by_installation.setdefault(row["terminal_eic"], []).append(row)

    assert len(by_installation) == 25
    for rows in by_installation.values():
        rows.sort(key=lambda row: row["gas_day"])
        assert rows[0]["derived_entry_gwh"] == "", "the first day has no previous day"
        for previous, row in pairwise(rows):
            consecutive = _next_day(previous["gas_day"]) == row["gas_day"]
            if consecutive:
                assert row["derived_entry_gwh"] != "", (
                    "the day after a known day has a derived entry"
                )
            else:
                assert row["derived_entry_gwh"] == "", (
                    "the day after a gap has no derived entry: its previous day is unknown"
                )


def test_a_gap_in_a_series_is_a_gap_and_not_a_zero(stored: StoredRecord) -> None:
    """A series that skips days says so in its days, and keeps its other values.

    Two installations do not publish every day of the window. The days they
    do publish are complete: the stock, the capacity and the withdrawal of
    those days are there. What is missing is the missing.
    """
    terminals = _rows(stored.payload["terminals.csv"])
    by_installation: dict[str, list[dict[str, str]]] = {}
    for row in terminals:
        by_installation.setdefault(row["terminal_eic"], []).append(row)

    gaps = 0
    for rows in by_installation.values():
        rows.sort(key=lambda row: row["gas_day"])
        for previous, row in pairwise(rows):
            if _next_day(previous["gas_day"]) != row["gas_day"]:
                gaps += 1
                assert row["stock_gwh"] != "", "the days that are published carry their stock"
                assert row["capacity_gwh"] != ""

    assert gaps > 0, "the publication holds at least one series with a gap"


@pytest.mark.skipif(not PRODUCTION.exists(), reason="the production output is not versioned")
def test_the_published_terminal_states_are_the_production_states(
    stored: StoredRecord,
) -> None:
    """Every production row is published, and an empty cell stays empty."""
    production = _rows(PRODUCTION / "europe_lng_terminals.csv")
    published = _rows(stored.payload["terminals.csv"])

    assert len(production) == len(published)
    for source, target in zip(production, published, strict=True):
        assert target["terminal_eic"] == source["terminal_eic"]
        assert target["gas_day"] == source["jour_gaz"]
        assert target["name"] == source["nom"]
        assert target["country"] == source["pays"]
        assert (target["derived_entry_gwh"] == "") == (source["entree_derivee_gwh"] == "")


def test_the_record_cites_its_inputs_with_their_quality_status(
    stored: StoredRecord,
) -> None:
    """The lineage is complete, and the observations it consumes are approved."""
    record = stored.record

    assert {ref.identifier for ref in record.lineage} == {
        "gie-alsi",
        "gie-agsi",
        "enagas",
        "alsi-terminal-states",
        "agsi-storage-states",
        "enagas-daily-series",
        "confrontation-alsi-enagas-2026-06",
        "torne.supply.terminals",
    }
    assert record.input_statuses == {
        "alsi-terminal-states": QualityStatus.APPROVED,
        "agsi-storage-states": QualityStatus.APPROVED,
        "enagas-daily-series": QualityStatus.APPROVED,
    }


def test_the_uncertainty_qualifies_the_bounded_quantities(stored: StoredRecord) -> None:
    """The bounded quantities are bounded in the summary, and said in clear words."""
    record = stored.record
    bounds = record.summary["bounds"]

    assert {bound["quantity"]: bound["direction"] for bound in bounds} == {
        "derived entry": "lower",
        "computed coverage": "upper",
    }
    assert "lower bound" in record.uncertainty
    assert "upper bound" in record.uncertainty


def test_the_publication_script_check_passes_on_the_committed_record() -> None:
    """The script that published the record agrees with what is committed."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "the published record does not agree with what is committed; "
        f"run scripts/publish_gas_supply.py --check\n{result.stdout}{result.stderr}"
    )
