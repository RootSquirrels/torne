"""The published products, as the Explorer serves them.

The service reads what is on disk. It never computes an indicator, never calls
a provider, and never presents a derived quantity as something the source
published: the numbers it serves are the numbers the published record carries,
and the absences are the absences the published payload carries.

Two rules shape it:

- **A field that is not known is `null`.** A cell that was empty stays empty.
  The first day of a series has no derived entry because it has no previous
  day, and the API says so with a null — never with a zero.
- **The application does not modify the product.** A product that is not
  published is a 404, not an empty series. An application that fails does not
  call a valid product into question, and it certainly does not repair one.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ...knowledge.store import (
    RecordNotFound,
    StoredRecord,
    list_products,
    load_record,
    records_root,
)

__all__ = [
    "confrontation",
    "product",
    "products",
    "states",
]


def _root() -> Path:
    return records_root()


def _load(product_id: str) -> StoredRecord:
    """The published product.

    A product that was never published is an absence, and it raises: the
    router turns it into a 404, never into an empty series.
    """
    return load_record(_root(), product_id)


def _number(text: str) -> float | None:
    """A published quantity. An empty cell is an absence, not a zero."""
    value = text.strip()
    if value == "":
        return None
    return float(value)


def _flag(text: str) -> bool | None:
    value = text.strip()
    if value == "":
        return None
    return value not in ("0", "false", "False")


def _rows(stored: StoredRecord, name: str) -> list[dict[str, str]]:
    path = stored.payload.get(name)
    if path is None:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _layer(summary: dict[str, Any], layer_id: str) -> dict[str, Any]:
    layers = summary.get("layers", {})
    layer = layers.get(layer_id)
    if not isinstance(layer, dict):
        return {}
    return layer


def products() -> list[dict]:
    """The products the repository has published."""
    listed: list[dict] = []
    for product_id in list_products(_root()):
        try:
            stored = _load(product_id)
        except RecordNotFound:
            continue
        record = stored.record
        summary = dict(record.summary)
        listed.append(
            {
                "product_id": record.product_id,
                "version": record.version,
                "title": str(summary.get("title", record.product_id)),
                "status": record.status.value,
                "nature": record.nature.value,
                "produced_at": record.produced_at.isoformat(),
                "domain_of_validity": record.domain_of_validity,
                "uncertainty": record.uncertainty,
                "payload_digest": stored.payload_digest,
            }
        )
    return listed


def product(product_id: str) -> dict:
    """One published product, in full.

    The identity, the lineage, the bounds it declares, and the indicators of
    each of its layers — served as the published record carries them.
    """
    stored = _load(product_id)

    record = stored.record
    summary = dict(record.summary)
    windows = {
        layer_id: _window(window)
        for layer_id, window in dict(summary.get("windows", {})).items()
        if isinstance(window, dict)
    }
    layers = {
        layer_id: {"id": layer_id, **layer}
        for layer_id, layer in dict(summary.get("layers", {})).items()
        if isinstance(layer, dict)
    }
    indicators = dict(summary.get("indicators", {}))
    units = dict(summary.get("units", {}))

    return {
        "product_id": record.product_id,
        "version": record.version,
        "title": str(summary.get("title", record.product_id)),
        "nature": record.nature.value,
        "produced_at": record.produced_at.isoformat(),
        "generated_at": str(summary["generated_at"]) if summary.get("generated_at") else None,
        "reference_date": (
            str(summary["reference_date"]) if summary.get("reference_date") else None
        ),
        "status": record.status.value,
        "domain_of_validity": record.domain_of_validity,
        "uncertainty": record.uncertainty,
        "lineage": [
            {
                "kind": ref.kind.value,
                "identifier": ref.identifier,
                "label": ref.label,
                "revision": ref.revision,
            }
            for ref in record.lineage
        ],
        "input_statuses": {
            identifier: status.value for identifier, status in record.input_statuses.items()
        },
        "provisional_inputs": list(record.provisional_inputs),
        "payload_digest": stored.payload_digest,
        "payload_files": sorted(stored.payload),
        "windows": windows,
        "layers": layers,
        "bounds": list(summary.get("bounds", [])),
        "units": {
            "measures": dict(units.get("measures", {})),
            "published": dict(units.get("published", {})),
        },
        "validation": dict(summary.get("validation", {})),
        "provenance": dict(summary.get("provenance", {})),
        "indicators": indicators,
    }


def _window(window: dict[str, Any]) -> dict[str, Any]:
    """The period a layer covers, with the entities it counts.

    A count that the published window does not carry stays null. A layer that
    publishes its period without counting its states says so, rather than
    claiming it holds none.
    """
    entities = window.get("entities")
    if entities is None:
        entities = window.get("installations", window.get("countries"))
    states = window.get("states")
    return {
        "start": str(window.get("start", "")),
        "end": str(window.get("end", "")),
        "states": int(states) if states is not None else None,
        "entities": int(entities) if entities is not None else None,
    }


def states(product_id: str, layer_id: str, entity: str | None = None) -> list[dict] | None:
    """The states of one layer, and of one entity when one is asked for.

    Without an entity, the **last published state** of every entity is
    served: that is what a map draws, and what a reader reads first.

    `None` means the layer is not one the product publishes.
    """
    stored = _load(product_id)

    summary = dict(stored.record.summary)
    layer = _layer(summary, layer_id)
    if not layer:
        return None

    rows = _rows(stored, str(layer.get("file", "")))
    entity_column = str(layer.get("entity_column", "entity"))
    label_column = str(layer.get("label_column", entity_column))
    country_column = str(layer.get("country_column", "country"))
    day_column = str(layer.get("day_column", "gas_day"))
    published_column = str(layer.get("published_column", "published_at"))
    measures = dict(layer.get("measures", {}))
    flags = dict(layer.get("flags", {}))
    positions = list(layer.get("position_columns", []))

    if entity is not None:
        rows = [row for row in rows if row.get(entity_column) == entity]
        if not rows:
            return []
    else:
        latest: dict[str, dict[str, str]] = {}
        for row in rows:
            key = row.get(entity_column, "")
            known = latest.get(key)
            if known is None or row.get(day_column, "") > known.get(day_column, ""):
                latest[key] = row
        rows = [latest[key] for key in sorted(latest)]

    served: list[dict] = []
    for row in rows:
        state: dict[str, Any] = {
            "entity": row.get(entity_column, ""),
            "label": row.get(label_column, ""),
            "country": row.get(country_column, ""),
            "gas_day": row.get(day_column, ""),
            "published_at": row.get(published_column, ""),
            "values": {name: _number(row.get(name, "")) for name in measures if name in row},
            "flags": {name: _flag(row.get(name, "")) for name in flags if name in row},
        }
        for position in positions:
            if position in ("latitude", "longitude"):
                state[position] = _number(row.get(position, ""))
        served.append(state)
    return served


def confrontation(product_id: str) -> list[dict]:
    """The confrontation that validated the product, day by day."""
    stored = _load(product_id)

    summary = dict(stored.record.summary)
    validation = dict(summary.get("validation", {}))
    name = str(validation.get("file", ""))
    rows = _rows(stored, name)
    return [
        {
            "operator_terminal": row.get("operator_terminal", ""),
            "terminal_eic": row.get("terminal_eic", ""),
            "alsi_day": row.get("alsi_day", ""),
            "operator_day": row.get("operator_day", ""),
            "alsi_stock_gwh": _number(row.get("alsi_stock_gwh", "")),
            "operator_stock_gwh": _number(row.get("operator_stock_gwh", "")),
            "absolute_difference_gwh": _number(row.get("absolute_difference_gwh", "")),
            "relative_difference": _number(row.get("relative_difference", "")),
        }
        for row in rows
    ]
