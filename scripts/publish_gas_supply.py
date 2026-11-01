"""Publish the European gas supply product, and check what is published.

The LNG-002 mission produced the European gas supply in two physical layers:
the LNG terminals and the underground storage. Its production output is
written in `data/resource-004/`, which is not versioned: it is a production
output, not a source. This script turns that output into a **knowledge
product** — the record, and the payload it points at.

Two modes, and they are separate:

- without an argument, the script **publishes**: it reads the production
  output, translates it into the published English contract, and writes the
  record with the store;
- with `--check`, it **verifies** what is committed and writes nothing.

The check has two independent halves:

1. **The record and its payload agree** — always runnable, with the committed
   files alone. The store verifies the digest of the payload; this verifies the
   *meaning*: the counts, the windows, the entities the record declares absent,
   and the figures of the confrontation.
2. **The record is the translation of the production output** — runnable only
   where `data/resource-004/` exists. The digest of each production file is
   compared with the digest the record carries, and the summary and the payload
   are rebuilt from the production files and compared with what is committed.
   Where the production output is absent, this half is **skipped**: it is
   reported as skipped, never as passed.

The publication is deterministic. The instant the record is built comes from
the production data — the latest publication date of the terminal states — and
never from the clock, so publishing twice produces the same record and the
store accepts the second run as the same publication.

Usage:

    python scripts/publish_gas_supply.py            # publish
    python scripts/publish_gas_supply.py --check    # verify what is committed
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from torne.contracts.knowledge import KnowledgeProduct, ProductStatus, ProvenanceKind, ProvenanceRef
from torne.contracts.model import ResultNature
from torne.contracts.observation import QualityStatus
from torne.knowledge.store import (
    RECORD_FILE,
    RecordExists,
    RecordNotFound,
    StoredRecord,
    load_record,
    records_root,
    write_record,
)

ROOT = Path(__file__).resolve().parents[1]
"""The root of the repository."""

PRODUCTION_DIRECTORY = ROOT / "data" / "resource-004"
"""Where the production output of the LNG-002 mission is written.

The directory is not versioned: it is a production output, not a source. The
verification of the publication therefore has two halves, and only one of them
needs it.
"""

PRODUCT_ID = "gas-supply-europe"
"""The identifier of the published product."""

VERSION = "2026-10-31"
"""The version of the published product: the reference date of the product."""

TITLE = "European gas supply — LNG terminals and underground storage"
"""The title of the product, in the language of the published contract."""

TERMINAL_STATES_FILE = "europe_lng_terminals.csv"
"""The production file of the terminal states."""

STOCK_STATES_FILE = "europe_stocks.csv"
"""The production file of the storage states."""

CONFRONTATION_FILE = "confrontation_alsi_enagas.csv"
"""The production file of the confrontation between the platform and the operator."""

PERIMETER_FILE = "confrontation_perimetre_alsi_enagas.csv"
"""The production file of the perimeter control, on the month of the confrontation."""

TERMINAL_INDICATORS_FILE = "terminaux_indicateurs.json"
"""The production file of the terminal indicators."""

STORAGE_INDICATORS_FILE = "europe_indicateurs.json"
"""The production file of the storage indicators."""

PRODUCTION_FILES = (
    TERMINAL_STATES_FILE,
    STOCK_STATES_FILE,
    CONFRONTATION_FILE,
    PERIMETER_FILE,
    TERMINAL_INDICATORS_FILE,
    STORAGE_INDICATORS_FILE,
)
"""The production files the published record is built from."""

TERMINAL_PAYLOAD_FILE = "terminals.csv"
"""The published payload of the terminal layer."""

STOCK_PAYLOAD_FILE = "stocks.csv"
"""The published payload of the storage layer."""

CONFRONTATION_PAYLOAD_FILE = "confrontation.csv"
"""The published payload of the confrontation."""

VALIDATION_METHOD = (
    "The seven Spanish terminals, over the same gas days, against an independent "
    "source (the operator's daily series). No conversion is applied: each source's "
    "own published GWh is compared."
)
"""What the validation compares, and how."""

ALIGNED_DAYS = "ALSI day D = operator day D, measured on the offsets -2 to +2"
"""How the gas days of the two sources are aligned."""

RESIDUAL_STATEMENT = (
    "Six terminals out of seven are systematically below in ALSI (median bias "
    "-0.29% to -2.80%): a difference of perimeter or of instant of measurement "
    "between two definitions of the tank stock."
)
"""What the confrontation leaves behind.

The statement is a claim about the data, and the check holds it against the
committed confrontation: six terminals of the seven are below the operator on
every day of the period, and their median bias runs from -0.29 % to -2.80 %.
"""

RESIDUAL_TERMINALS_BELOW = 6
"""The terminals that are below the operator on every day of the period."""

RESIDUAL_BIAS_CLOSEST = -0.29
"""The median bias closest to zero, in percentage points."""

RESIDUAL_BIAS_MOST_NEGATIVE = -2.80
"""The median bias most negative, in percentage points."""

VOLUME_MEDIAN_RELATIVE_DIFFERENCE = 0.0
"""The median relative difference on the volumes, in the published GWh.

The production run compared the volume of LNG the platform publishes against
the volume the operator publishes, on the raw evidence of both sources: the two
measurements describe the same tanks, and the median relative difference is
zero. The figure is carried here because it is what the production measured;
it cannot be recomputed from the published payload, which holds the stocks in
GWh only.
"""

UNCERTAINTY = (
    "The derived entry is a lower bound on the real entry into the tanks: the "
    "platform publishes only the network send-out, and the LNG that leaves the "
    "tanks by truck or by ship is not published. The computed coverage is "
    "therefore an upper bound on the real coverage."
)
"""The uncertainty of the product, qualified in clear language."""

IDENTIFIER_REFERENCE = (
    "The list of installations comes from the European Commission's eurogastp "
    "project (Dataproviders.csv); the data come from GIE."
)
"""Where the list of installations comes from."""


@dataclass(frozen=True, slots=True)
class Column:
    """A column of a production file, and the column it is published as."""

    source: str
    published: str


TERMINAL_COLUMNS = (
    Column("terminal_eic", "terminal_eic"),
    Column("nom", "name"),
    Column("pays", "country"),
    Column("jour_gaz", "gas_day"),
    Column("date_publication", "published_at"),
    Column("stock_gwh", "stock_gwh"),
    Column("capacite_gwh", "capacity_gwh"),
    Column("sortie_gwh_j", "send_out_gwh_per_day"),
    Column("marge_jours", "margin_days"),
    Column("tension", "tension"),
    Column("entree_derivee_gwh", "derived_entry_gwh"),
    Column("latitude", "latitude"),
    Column("longitude", "longitude"),
)
"""The published columns of the terminal layer."""

STOCK_COLUMNS = (
    Column("pays", "country"),
    Column("jour_gaz", "gas_day"),
    Column("date_publication", "published_at"),
    Column("stock_gwh", "stock_gwh"),
    Column("capacite_gwh", "capacity_gwh"),
    Column("injection_gwh_j", "injection_gwh_per_day"),
    Column("soutirage_gwh_j", "withdrawal_gwh_per_day"),
    Column("remplissage_publie_pct", "published_fill_pct"),
    Column("autonomie_publiee_jours", "published_autonomy_days"),
    Column("couverture_calculee_jours", "computed_coverage_days"),
    Column(
        "rapport_autonomie_publiee_sur_consommation",
        "published_autonomy_over_consumption_ratio",
    ),
    Column("taux_reconstitution_cap_j", "reconstitution_rate_per_day"),
    Column("pression_prelevement", "drawdown_pressure"),
)
"""The published columns of the storage layer.

The daily series of the published autonomy on consumption is not among them:
the published contract declares the autonomy and its ratio, and the value
computed on consumption stays in the indicators, at the reference day of each
country.
"""

CONFRONTATION_COLUMNS = (
    Column("terminal_enagas", "operator_terminal"),
    Column("terminal_eic", "terminal_eic"),
    Column("jour_alsi", "alsi_day"),
    Column("jour_enagas", "operator_day"),
    Column("stock_alsi_gwh", "alsi_stock_gwh"),
    Column("stock_enagas_gwh", "operator_stock_gwh"),
    Column("ecart_abs_gwh", "absolute_difference_gwh"),
    Column("ecart_rel", "relative_difference"),
)
"""The published columns of the confrontation."""

PERIMETER_COLUMNS = (
    Column("terminal_enagas", "operator_terminal"),
    Column("terminal_eic", "terminal_eic"),
    Column("sendout_alsi_gwh", "send_out_gwh"),
    Column("regas_exploitant_gwh", "operator_regas_gwh"),
    Column("ecart_reseau_pct", "network_flow_difference_pct"),
    Column("citernes_gwh", "truck_outflow_gwh"),
    Column("navires_gwh", "ship_outflow_gwh"),
    Column("decharge_publiee_gwh", "published_discharge_gwh"),
    Column("decharge_derivee_gwh", "derived_discharge_gwh"),
    Column("ecart_decharge_pct", "discharge_difference_pct"),
    Column("sorties_non_publiees_gwh", "unpublished_outflow_gwh"),
)
"""The columns of the perimeter control.

The control is not published as a payload: it is the evidence of the perimeter
of the confrontation, and the record carries its digest.
"""

TERMINAL_INDICATOR_KEYS = {
    "produit": "product",
    "genere_le": "generated_at",
    "fenetre": "window",
    "debut": "start",
    "fin": "end",
    "date_reference": "reference_date",
    "sources": "sources",
    "source_id": "source_id",
    "producteur": "publisher",
    "dataset": "dataset",
    "unites": "units",
    "acces": "access",
    "reference_identifiants": "identifier_reference",
    "concentration": "concentration",
    "herfindahl": "herfindahl",
    "part_premier": "top_share",
    "part_trois": "top_three_share",
    "total_gwh": "total_gwh",
    "concentration_par_pays": "concentration_by_country",
    "dependance_par_pays": "dependency_by_country",
    "stock_gwh": "stock_gwh",
    "capacite_gwh": "capacity_gwh",
    "sortie_gwh_j": "send_out_gwh_per_day",
    "terminaux": "terminals",
    "part_stock": "stock_share",
    "part_capacite": "capacity_share",
    "part_sortie": "send_out_share",
    "controle_somme_agregat": "aggregate_sum_control",
    "pays": "country",
    "terminaux_comptes": "terminals_counted",
    "somme_terminaux_gwh": "terminals_sum_gwh",
    "agregat_publie_gwh": "published_aggregate_gwh",
    "ecart_relatif": "relative_difference",
    "installations_sans_donnee": "installations_without_data",
    "couverture_systeme_jours": "system_coverage_days",
    "reserve_systeme_gwh": "system_reserve_gwh",
    "debit_systeme_gwh_j": "system_flow_gwh_per_day",
    "scenarios_perte": "loss_scenarios",
    "installation": "installation",
    "couverture_avant_jours": "coverage_before_days",
    "couverture_apres_jours": "coverage_after_days",
    "jours_perdus": "days_lost",
    "reserve_perdue_gwh": "reserve_lost_gwh",
    "debit_perdu_gwh_j": "flow_lost_gwh_per_day",
    "part_reserve_perdue": "reserve_share_lost",
    "installations": "installations",
    "etats": "states",
}
"""The published names of the keys of the terminal indicators.

The table applies at every depth: a key of a list of objects is translated like
any other.
"""

STORAGE_INDICATOR_KEYS = {
    "periode": "period",
    "debut": "start",
    "fin": "end",
    "couverture": "coverage",
    "refus": "refusals",
    "indicateurs": "indicators",
    "pays": "country",
    "jours": "days",
    "stock_gwh": "stock_gwh",
    "capacite_gwh": "capacity_gwh",
    "remplissage_publie_pct": "published_fill_pct",
    "couverture_calculee_jours": "computed_coverage_days",
    "autonomie_publiee_jours": "published_autonomy_days",
    "couverture_sur_consommation_publiee_jours": "published_autonomy_on_consumption_days",
    "rapport_autonomie_publiee_sur_consommation": "published_autonomy_over_consumption_ratio",
    "ecart_avec_la_publiee_jours": "difference_with_published_days",
    "taux_reconstitution_cap_j": "reconstitution_rate_per_day",
    "degradation_jours_par_jour": "degradation_days_per_day",
    "date_publication": "published_at",
    "concentration": "concentration",
    "herfindahl": "herfindahl",
    "part_premier_pays": "top_country_share",
    "part_trois_premiers_pays": "top_three_countries_share",
    "unites": "units",
    "stocks": "stock",
    "flux": "flow",
    "provenance": "provenance",
    "source": "source",
    "attribution": "attribution",
    "api": "api",
    "cle": "credential",
}
"""The published names of the keys of the storage indicators."""

LAYERS: Mapping[str, object] = {
    "terminals": {
        "title": "LNG terminals",
        "file": TERMINAL_PAYLOAD_FILE,
        "entity_column": "terminal_eic",
        "label_column": "name",
        "country_column": "country",
        "day_column": "gas_day",
        "published_column": "published_at",
        "position_columns": ["latitude", "longitude"],
        "measures": {
            "stock_gwh": {"label": "Stock", "unit": "GWh"},
            "capacity_gwh": {"label": "Capacity", "unit": "GWh"},
            "send_out_gwh_per_day": {"label": "Send-out", "unit": "GWh/day"},
            "margin_days": {"label": "Margin", "unit": "days"},
            "derived_entry_gwh": {"label": "Derived entry (lower bound)", "unit": "GWh"},
        },
        "flags": {"tension": {"label": "In tension"}},
    },
    "storage": {
        "title": "Underground storage",
        "file": STOCK_PAYLOAD_FILE,
        "entity_column": "country",
        "label_column": "country",
        "country_column": "country",
        "day_column": "gas_day",
        "published_column": "published_at",
        "measures": {
            "stock_gwh": {"label": "Stock", "unit": "GWh"},
            "capacity_gwh": {"label": "Capacity", "unit": "GWh"},
            "injection_gwh_per_day": {"label": "Injection", "unit": "GWh/day"},
            "withdrawal_gwh_per_day": {"label": "Withdrawal", "unit": "GWh/day"},
            "published_fill_pct": {"label": "Published fill", "unit": "%"},
            "published_autonomy_days": {"label": "Published autonomy", "unit": "days"},
            "computed_coverage_days": {"label": "Computed coverage (upper bound)", "unit": "days"},
        },
        "flags": {},
    },
}
"""The two layers of the product, and the vocabulary of their measures."""

MEASURE_UNITS: Mapping[str, Mapping[str, str]] = {
    "terminals": {
        "stock_gwh": "GWh",
        "capacity_gwh": "GWh",
        "send_out_gwh_per_day": "GWh/day",
        "margin_days": "days",
        "derived_entry_gwh": "GWh",
        "latitude": "degrees",
        "longitude": "degrees",
    },
    "storage": {
        "stock_gwh": "GWh",
        "capacity_gwh": "GWh",
        "injection_gwh_per_day": "GWh/day",
        "withdrawal_gwh_per_day": "GWh/day",
        "published_fill_pct": "%",
        "published_autonomy_days": "days",
        "computed_coverage_days": "days",
    },
}
"""The unit of every measure the two layers publish."""


@dataclass(frozen=True, slots=True)
class Production:
    """The production output of the mission, read as it is written."""

    directory: Path
    terminals: tuple[Mapping[str, str], ...]
    stocks: tuple[Mapping[str, str], ...]
    confrontation: tuple[Mapping[str, str], ...]
    perimeter: tuple[Mapping[str, str], ...]
    terminal_indicators: Mapping[str, object]
    storage_indicators: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ConfrontationFigures:
    """What the confrontation between the platform and the operator measures."""

    comparisons: int
    terminals: int
    median_relative_difference: float
    max_relative_difference: float
    terminals_below_every_day: int
    bias_closest_to_zero: float
    bias_most_negative: float


@dataclass(frozen=True, slots=True)
class Check:
    """One verification, and what it found."""

    status: str
    name: str
    detail: str


def _read_rows(path: Path, columns: Sequence[Column]) -> list[dict[str, str]]:
    """The rows of a production file, under the published names of their columns.

    The values stay text: a number is never read back, so a value the
    production wrote is published as the production wrote it.
    """
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [column.source for column in columns if column.source not in header]
        if missing:
            raise ValueError(f"{path} does not carry the columns {missing}")
        return [{column.published: row[column.source] for column in columns} for row in reader]


def _read_published_rows(path: Path, columns: Sequence[Column]) -> list[dict[str, str]]:
    """The rows of a published payload, under the names they were published with."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [column.published for column in columns if column.published not in header]
        if missing:
            raise ValueError(f"{path} does not carry the columns {missing}")
        return [{column.published: row[column.published] for column in columns} for row in reader]


def _read_json(path: Path) -> Mapping[str, object]:
    """A JSON object of the production output."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError(f"{path} is not a JSON object")
    return document


def _render_csv(rows: Sequence[Mapping[str, str]], columns: Sequence[Column]) -> bytes:
    """The payload of a layer: the production values under the published names.

    An empty cell stays empty. A value the production did not publish is not
    published as a zero.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([column.published for column in columns])
    for row in rows:
        writer.writerow([row[column.published] for column in columns])
    return buffer.getvalue().encode("utf-8")


def _translate(value: object, keys: Mapping[str, str]) -> object:
    """A production value, with its keys translated into the published names.

    The translation applies at every depth: a key of a list of objects is
    translated like any other. The values are never touched — the production
    writes them, the publication carries them.
    """
    if isinstance(value, Mapping):
        return {keys.get(str(key), str(key)): _translate(item, keys) for key, item in value.items()}
    if isinstance(value, list):
        return [_translate(item, keys) for item in value]
    return value


def _translated(value: Mapping[str, object], keys: Mapping[str, str]) -> Mapping[str, object]:
    """A production object, with its keys translated."""
    translated = _translate(dict(value), keys)
    if not isinstance(translated, Mapping):
        raise TypeError("the translation of an object is an object")
    return translated


def _mapping(value: object) -> Mapping[str, object]:
    """A mapping, or the failure of the contract that says there is one."""
    if not isinstance(value, Mapping):
        raise TypeError(f"a mapping is expected, not {type(value).__name__}")
    return value


def _sequence(mapping: Mapping[str, object], key: str) -> list[object]:
    """The list a mapping holds under a key, or the failure of the contract."""
    value = mapping.get(key)
    if not isinstance(value, list):
        raise TypeError(f"the mapping does not hold a list under {key!r}")
    return value


def _at(mapping: Mapping[str, object], *path: str) -> object:
    """The value at a path in the summary of the record."""
    value: object = mapping
    for key in path:
        if not isinstance(value, Mapping):
            raise TypeError(f"{key} is not reached: the summary does not hold a mapping")
        value = value[key]
    return value


def _sha256(path: Path) -> str:
    """The digest of a file, read as it is written."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _instant(value: str) -> datetime:
    """A publication date, read as the instant it carries."""
    return datetime.fromisoformat(value)


def read_production(directory: Path) -> Production:
    """Read the production output of the mission."""
    return Production(
        directory=directory,
        terminals=tuple(_read_rows(directory / TERMINAL_STATES_FILE, TERMINAL_COLUMNS)),
        stocks=tuple(_read_rows(directory / STOCK_STATES_FILE, STOCK_COLUMNS)),
        confrontation=tuple(_read_rows(directory / CONFRONTATION_FILE, CONFRONTATION_COLUMNS)),
        perimeter=tuple(_read_rows(directory / PERIMETER_FILE, PERIMETER_COLUMNS)),
        terminal_indicators=_read_json(directory / TERMINAL_INDICATORS_FILE),
        storage_indicators=_read_json(directory / STORAGE_INDICATORS_FILE),
    )


def _confrontation_figures(rows: Sequence[Mapping[str, str]]) -> ConfrontationFigures:
    """The figures of the confrontation, read from its rows.

    The median is the one the production used — the upper median of the ordered
    series — so the published figure is the figure the production measured.
    The bias of a terminal is signed: negative means the platform is below the
    operator.
    """
    relatives = sorted(float(row["relative_difference"]) for row in rows)
    biases: dict[str, list[float]] = {}
    for row in rows:
        reference = float(row["operator_stock_gwh"])
        bias = (float(row["alsi_stock_gwh"]) - reference) / reference
        biases.setdefault(str(row["operator_terminal"]), []).append(bias)
    below: list[float] = []
    for values in biases.values():
        series = sorted(values)
        if all(value < 0 for value in series):
            below.append(series[len(series) // 2] * 100)
    return ConfrontationFigures(
        comparisons=len(rows),
        terminals=len(biases),
        median_relative_difference=round(relatives[len(relatives) // 2], 4),
        max_relative_difference=round(relatives[-1], 4),
        terminals_below_every_day=len(below),
        bias_closest_to_zero=max(below),
        bias_most_negative=min(below),
    )


def _network_flow_median(rows: Sequence[Mapping[str, str]]) -> float:
    """The median relative difference on the network flow.

    The platform publishes the send-out to the network; the operator publishes
    the regasification. The perimeter control compares them on the month of the
    confrontation, and the median of the per-terminal gaps is the figure the
    production published.
    """
    values = sorted(abs(float(row["network_flow_difference_pct"])) / 100 for row in rows)
    return round(values[len(values) // 2], 3)


def build_payload(production: Production) -> dict[str, bytes]:
    """The payload of the product: the two layers and the confrontation."""
    return {
        TERMINAL_PAYLOAD_FILE: _render_csv(production.terminals, TERMINAL_COLUMNS),
        STOCK_PAYLOAD_FILE: _render_csv(production.stocks, STOCK_COLUMNS),
        CONFRONTATION_PAYLOAD_FILE: _render_csv(production.confrontation, CONFRONTATION_COLUMNS),
    }


def build_summary(production: Production) -> Mapping[str, object]:
    """The summary of the record, built from the production output.

    Everything the summary declares is read from the production files: the
    counts, the windows, the instant, the figures of the confrontation. Nothing
    is asserted that the production data does not carry.
    """
    terminal_indicators = _translated(production.terminal_indicators, TERMINAL_INDICATOR_KEYS)
    storage_indicators = dict(_translated(production.storage_indicators, STORAGE_INDICATOR_KEYS))

    # The countries the platform answered for, and the ones that published no
    # usable state. The absence is named, so a reader can tell it apart from a
    # country that was never asked about.
    storage_countries = {row["country"] for row in production.stocks}
    covered_countries = {str(country) for country in _sequence(storage_indicators, "coverage")}
    storage_indicators["countries_without_published_state"] = sorted(
        covered_countries - storage_countries
    )

    terminal_days = sorted({row["gas_day"] for row in production.terminals})
    storage_days = sorted({row["gas_day"] for row in production.stocks})
    terminal_entities = sorted({row["terminal_eic"] for row in production.terminals})

    publications = [_instant(row["published_at"]) for row in production.terminals]
    publications += [_instant(row["published_at"]) for row in production.stocks]
    generated_at = max(publications)

    figures = _confrontation_figures(production.confrontation)

    sources = terminal_indicators["sources"]
    if not isinstance(sources, list):
        raise TypeError("the terminal indicators do not carry a list of sources")

    summary: dict[str, object] = {
        "title": TITLE,
        "generated_at": generated_at.isoformat(),
        "reference_date": str(terminal_indicators["reference_date"]),
        "windows": {
            "terminals": {
                "start": terminal_days[0],
                "end": terminal_days[-1],
                "states": len(production.terminals),
                "installations": len(terminal_entities),
            },
            "storage": {
                "start": storage_days[0],
                "end": storage_days[-1],
                "states": len(production.stocks),
                "countries": len(_sequence(storage_indicators, "coverage")),
            },
        },
        "layers": copy.deepcopy(dict(LAYERS)),
        "indicators": {
            "terminals": terminal_indicators,
            "storage": storage_indicators,
        },
        "bounds": [
            {
                "quantity": "derived entry",
                "direction": "lower",
                "statement": (
                    "The derived entry is a lower bound on the real entry into the tanks: "
                    "the platform publishes only the network send-out, and the LNG that "
                    "leaves the tanks by truck or by ship is not published."
                ),
            },
            {
                "quantity": "computed coverage",
                "direction": "upper",
                "statement": (
                    "The computed coverage is an upper bound on the real coverage, for "
                    "the same reason: the real outflow of the tanks is at least the "
                    "published network send-out."
                ),
            },
        ],
        "validation": {
            "method": VALIDATION_METHOD,
            "comparisons": figures.comparisons,
            "median_relative_difference": figures.median_relative_difference,
            "max_relative_difference": figures.max_relative_difference,
            "median_relative_difference_volume": VOLUME_MEDIAN_RELATIVE_DIFFERENCE,
            "median_relative_difference_network_flow": _network_flow_median(production.perimeter),
            "aligned_days": ALIGNED_DAYS,
            "residual": RESIDUAL_STATEMENT,
            "file": CONFRONTATION_PAYLOAD_FILE,
        },
        "provenance": {
            "sources": copy.deepcopy(sources),
            "identifier_reference": IDENTIFIER_REFERENCE,
            "production_digests": {
                name: _sha256(production.directory / name) for name in PRODUCTION_FILES
            },
        },
        "units": {
            # The units of the measures the layers publish, and the units the
            # production publishes. A unit is a label of the published
            # contract: it is written in the language of the contract. The
            # description the sources give of their own units is carried as it
            # is written.
            "measures": copy.deepcopy(dict(MEASURE_UNITS)),
            "published": {
                "terminals": {
                    "sources": [
                        str(source["units"])
                        for source in sources
                        if isinstance(source, Mapping) and "units" in source
                    ]
                },
                "storage": {
                    "stock": "GWh",
                    "flow": "GWh/day",
                },
            },
        },
    }
    return summary


def build_product(summary: Mapping[str, object], production: Production) -> KnowledgeProduct:
    """The published product, built from the summary and the production output."""
    publications = [_instant(row["published_at"]) for row in production.terminals]
    produced_at = max(publications)
    evaluation_revision = str(production.terminal_indicators["genere_le"])[:10]
    operator_days = sorted({row["operator_day"] for row in production.confrontation})
    terminal_days = sorted({row["gas_day"] for row in production.terminals})
    storage_days = sorted({row["gas_day"] for row in production.stocks})
    terminal_countries = sorted({row["country"] for row in production.terminals})

    return KnowledgeProduct(
        product_id=PRODUCT_ID,
        version=VERSION,
        nature=ResultNature.RECONSTRUCTED,
        produced_at=produced_at,
        status=ProductStatus.USABLE,
        domain_of_validity=_domain_of_validity(
            summary, terminal_days, storage_days, terminal_countries
        ),
        uncertainty=UNCERTAINTY,
        lineage=_lineage(evaluation_revision, terminal_days, storage_days, operator_days),
        summary=summary,
        input_statuses={
            "alsi-terminal-states": QualityStatus.APPROVED,
            "agsi-storage-states": QualityStatus.APPROVED,
            "enagas-daily-series": QualityStatus.APPROVED,
        },
    )


def _domain_of_validity(
    summary: Mapping[str, object],
    terminal_days: Sequence[str],
    storage_days: Sequence[str],
    terminal_countries: Sequence[str],
) -> str:
    """What the product covers, and where it was validated."""
    terminal_window = _mapping(_at(summary, "windows", "terminals"))
    storage_indicators = _mapping(_at(summary, "indicators", "storage"))
    covered = len(_sequence(storage_indicators, "coverage"))
    published = len(_sequence(storage_indicators, "indicators"))
    installations = int(terminal_window["installations"])
    return (
        f"European gas supply at the reference date {VERSION}: {installations} LNG terminal "
        f"installations in {len(terminal_countries)} countries, over the gas days "
        f"{terminal_days[0]} to {terminal_days[-1]}, and the underground storage of the "
        f"{covered} countries the platform answered for — {published} of them published "
        f"usable states — over {storage_days[0]} to {storage_days[-1]}. "
        f"The validation is the confrontation with the operator's daily series: it covers the "
        f"seven Spanish terminals over June 2026 only, so the other "
        f"{installations - 7} European installations are produced but are not validated that way."
    )


def _lineage(
    evaluation_revision: str,
    terminal_days: Sequence[str],
    storage_days: Sequence[str],
    operator_days: Sequence[str],
) -> tuple[ProvenanceRef, ...]:
    """The lineage of the product: what it consumes, and what produced it."""
    return (
        ProvenanceRef(
            kind=ProvenanceKind.SOURCE,
            identifier="gie-alsi",
            label="GIE ALSI Transparency Platform",
        ),
        ProvenanceRef(
            kind=ProvenanceKind.SOURCE,
            identifier="gie-agsi",
            label="GIE AGSI+ Transparency Platform",
        ),
        ProvenanceRef(
            kind=ProvenanceKind.SOURCE,
            identifier="enagas",
            label="Enagas — Seguimiento Diario del Sistema",
        ),
        ProvenanceRef(
            kind=ProvenanceKind.OBSERVATION,
            identifier="alsi-terminal-states",
            label="The daily terminal states published by GIE",
            revision=terminal_days[-1],
        ),
        ProvenanceRef(
            kind=ProvenanceKind.OBSERVATION,
            identifier="agsi-storage-states",
            label="The daily storage states published by GIE",
            revision=storage_days[-1],
        ),
        ProvenanceRef(
            kind=ProvenanceKind.OBSERVATION,
            identifier="enagas-daily-series",
            label="The operator's daily system tracking series",
            revision=operator_days[-1],
        ),
        ProvenanceRef(
            kind=ProvenanceKind.EVALUATION,
            identifier="confrontation-alsi-enagas-2026-06",
            label="The confrontation of the platform and the operator, over the Spanish terminals",
            revision=evaluation_revision,
        ),
        ProvenanceRef(
            kind=ProvenanceKind.MODEL,
            identifier="torne.supply.terminals",
            label="The terminal layer of the supply models",
            revision="0.1.0",
        ),
    )


def _normalize_record_file(directory: Path) -> None:
    """Write the record with the line endings of the repository.

    The store writes the record with the line endings of the platform; the
    repository is written with LF. The record is normalized here, so that the
    published file is the same file whatever the platform.
    """
    path = directory / RECORD_FILE
    content = path.read_bytes()
    normalized = content.replace(b"\r\n", b"\n")
    if normalized != content:
        path.write_bytes(normalized)


def publish(production_directory: Path, record_root: Path) -> int:
    """Publish the product: build it from the production output, and write it.

    A version that is already published is not rewritten: the store refuses it,
    and the refusal is reported rather than raised. A correction is a new
    version.
    """
    if not production_directory.exists():
        print(f"the production output is absent: {production_directory}")
        return 1
    production = read_production(production_directory)
    summary = build_summary(production)
    product = build_product(summary, production)
    payload = build_payload(production)
    try:
        directory = write_record(record_root, product, payload)
    except RecordExists as error:
        print(f"the version is already published: {error}")
        return 1
    _normalize_record_file(directory)
    print(f"published {product.product_id} {product.version} -> {directory}")
    return 0


def _expect(condition: bool, name: str, detail: str) -> Check:
    """The outcome of a verification."""
    return Check("passed" if condition else "failed", name, detail)


def _check_committed(stored: StoredRecord) -> list[Check]:
    """The committed record, against the committed payload it points at."""
    checks: list[Check] = []
    summary = stored.record.summary
    terminals = _read_published_rows(stored.payload[TERMINAL_PAYLOAD_FILE], TERMINAL_COLUMNS)
    stocks = _read_published_rows(stored.payload[STOCK_PAYLOAD_FILE], STOCK_COLUMNS)
    confrontation = _read_published_rows(
        stored.payload[CONFRONTATION_PAYLOAD_FILE], CONFRONTATION_COLUMNS
    )

    checks.append(
        Check(
            "passed",
            "the committed record loads",
            f"the payload digest {stored.payload_digest} is the one the record carries",
        )
    )

    terminal_window = _mapping(_at(summary, "windows", "terminals"))
    storage_window = _mapping(_at(summary, "windows", "storage"))
    terminal_indicators = _mapping(_at(summary, "indicators", "terminals"))
    storage_indicators = _mapping(_at(summary, "indicators", "storage"))
    validation = _mapping(_at(summary, "validation"))

    checks.append(
        _expect(
            len(terminals) == int(terminal_window["states"]),
            "the terminals payload carries the declared states",
            f"{len(terminals)} states published, {terminal_window['states']} declared",
        )
    )
    terminal_entities = {row["terminal_eic"] for row in terminals}
    checks.append(
        _expect(
            len(terminal_entities) == int(terminal_window["installations"]),
            "the terminals payload carries the declared installations",
            f"{len(terminal_entities)} installations published, "
            f"{terminal_window['installations']} declared",
        )
    )
    terminal_days = sorted({row["gas_day"] for row in terminals})
    checks.append(
        _expect(
            terminal_days[0] == terminal_window["start"]
            and terminal_days[-1] == terminal_window["end"],
            "the terminals payload covers the declared window",
            f"the gas days {terminal_days[0]} to {terminal_days[-1]}, "
            f"declared {terminal_window['start']} to {terminal_window['end']}",
        )
    )

    without_data = terminal_indicators["installations_without_data"]
    if not isinstance(without_data, list):
        raise TypeError("the terminal indicators do not carry a list of installations")
    absent = sorted(str(entity) for entity in without_data)
    present = sorted(entity for entity in absent if entity in terminal_entities)
    checks.append(
        _expect(
            not present,
            "the installations without data are absent from the payload",
            f"{len(absent)} declared without data, {len(present)} of them published",
        )
    )

    checks.append(
        _expect(
            len(stocks) == int(storage_window["states"]),
            "the storage payload carries the declared states",
            f"{len(stocks)} states published, {storage_window['states']} declared",
        )
    )
    storage_entities = {row["country"] for row in stocks}
    declared_countries = {
        str(_at(_mapping(entry), "country"))
        for entry in _sequence(storage_indicators, "indicators")
    }
    checks.append(
        _expect(
            storage_entities == declared_countries,
            "the storage payload carries exactly the declared countries",
            f"{len(storage_entities)} countries published, "
            f"{len(declared_countries)} countries declared with states",
        )
    )
    coverage = {str(country) for country in _sequence(storage_indicators, "coverage")}
    checks.append(
        _expect(
            int(storage_window["countries"]) == len(coverage),
            "the declared storage coverage is the covered countries",
            f"{storage_window['countries']} countries declared, {len(coverage)} covered by the platform",
        )
    )
    without_state_value = storage_indicators.get("countries_without_published_state")
    without_state = (
        {str(country) for country in without_state_value}
        if isinstance(without_state_value, list)
        else set()
    )
    checks.append(
        _expect(
            len(coverage) == len(declared_countries) + len(without_state),
            "the storage coverage reconciles with the countries it holds",
            f"{len(coverage)} countries covered, {len(declared_countries)} with a published state, "
            f"{len(without_state)} without",
        )
    )
    checks.append(
        _expect(
            declared_countries.isdisjoint(without_state)
            and declared_countries | without_state == coverage,
            "the covered countries are the ones with a state and the ones without",
            f"{len(declared_countries | without_state)} countries accounted for, "
            f"{len(declared_countries & without_state)} counted twice",
        )
    )
    storage_days = sorted({row["gas_day"] for row in stocks})
    checks.append(
        _expect(
            storage_days[0] == storage_window["start"]
            and storage_days[-1] == storage_window["end"],
            "the storage payload covers the declared window",
            f"the gas days {storage_days[0]} to {storage_days[-1]}, "
            f"declared {storage_window['start']} to {storage_window['end']}",
        )
    )

    figures = _confrontation_figures(confrontation)
    checks.append(
        _expect(
            figures.comparisons == int(validation["comparisons"]),
            "the confrontation carries the declared comparisons",
            f"{figures.comparisons} comparisons published, {validation['comparisons']} declared",
        )
    )
    checks.append(
        _expect(
            figures.median_relative_difference == float(validation["median_relative_difference"]),
            "the confrontation carries the declared median relative difference",
            f"{figures.median_relative_difference} measured, "
            f"{validation['median_relative_difference']} declared",
        )
    )
    checks.append(
        _expect(
            figures.max_relative_difference == float(validation["max_relative_difference"]),
            "the confrontation carries the declared maximum relative difference",
            f"{figures.max_relative_difference} measured, "
            f"{validation['max_relative_difference']} declared",
        )
    )
    aligned = all(row["alsi_day"] == row["operator_day"] for row in confrontation)
    checks.append(
        _expect(
            aligned,
            "the confrontation aligns the days it declares",
            f"ALSI day D = operator day D on {len(confrontation)} comparisons",
        )
    )
    checks.append(
        _expect(
            figures.terminals_below_every_day == RESIDUAL_TERMINALS_BELOW,
            "the residual holds: the terminals below the operator",
            f"{figures.terminals_below_every_day} terminals are below the operator on every "
            f"day, {RESIDUAL_TERMINALS_BELOW} declared",
        )
    )
    checks.append(
        _expect(
            round(figures.bias_closest_to_zero, 2) == RESIDUAL_BIAS_CLOSEST,
            "the residual holds: the bias closest to zero",
            f"{figures.bias_closest_to_zero:.2f}% measured, {RESIDUAL_BIAS_CLOSEST}% declared",
        )
    )
    checks.append(
        _expect(
            round(figures.bias_most_negative, 2) == RESIDUAL_BIAS_MOST_NEGATIVE,
            "the residual holds: the bias most negative",
            f"{figures.bias_most_negative:.2f}% measured, {RESIDUAL_BIAS_MOST_NEGATIVE}% declared",
        )
    )
    return checks


def _check_production(production_directory: Path, stored: StoredRecord) -> list[Check]:
    """The committed record, against the production output it was built from."""
    checks: list[Check] = []
    production = read_production(production_directory)
    digests = _mapping(_at(stored.record.summary, "provenance", "production_digests"))

    for name, digest in sorted(digests.items()):
        path = production_directory / str(name)
        if not path.exists():
            checks.append(Check("failed", f"the digest of {name}", f"{path} is absent"))
            continue
        measured = _sha256(path)
        checks.append(
            _expect(
                measured == str(digest),
                f"the digest of {name}",
                f"{measured} measured, {digest} recorded",
            )
        )

    rebuilt = build_summary(production)
    committed = stored.record.summary
    different = [
        key for key in set(rebuilt) | set(committed) if rebuilt.get(key) != committed.get(key)
    ]
    checks.append(
        _expect(
            not different,
            "the committed summary is the translation of the production output",
            "the summary is rebuilt and identical"
            if not different
            else f"the keys that differ: {sorted(different)}",
        )
    )

    payload = build_payload(production)
    published = {name: path.read_bytes() for name, path in stored.payload.items()}
    checks.append(
        _expect(
            payload == published,
            "the committed payload is the translation of the production files",
            f"{len(payload)} payload files, "
            + ("identical" if payload == published else "different from the production"),
        )
    )
    return checks


def check(record_root: Path, production_directory: Path) -> int:
    """Verify what is committed, and write nothing."""
    try:
        stored = load_record(record_root, PRODUCT_ID, VERSION)
    except (RecordNotFound, ValueError) as error:
        print(f"the product {PRODUCT_ID} {VERSION} is not published: {error}")
        return 1

    checks = _check_committed(stored)
    if production_directory.exists():
        checks += _check_production(production_directory, stored)
    else:
        checks.append(
            Check(
                "skipped",
                "the committed record is the translation of the production output",
                f"{production_directory} is absent: the production files cannot be compared",
            )
        )

    failures = 0
    for entry in checks:
        print(f"  [{entry.status}] {entry.name}: {entry.detail}")
        if entry.status == "failed":
            failures += 1
    skipped = sum(1 for entry in checks if entry.status == "skipped")
    print(
        f"{len(checks) - failures - skipped} check(s) passed, {failures} failed, {skipped} skipped"
    )
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    """The entry point of the script."""
    parser = argparse.ArgumentParser(
        description="Publish the European gas supply product, or check what is published."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify what is committed, and write nothing",
    )
    parser.add_argument(
        "--production",
        type=Path,
        default=PRODUCTION_DIRECTORY,
        help="the production output of the mission",
    )
    parser.add_argument(
        "--records",
        type=Path,
        default=None,
        help="the store the record is written to (default: the records of the package)",
    )
    arguments = parser.parse_args(argv)
    record_root = records_root() if arguments.records is None else arguments.records
    if arguments.check:
        return check(record_root, arguments.production)
    return publish(arguments.production, record_root)


if __name__ == "__main__":
    raise SystemExit(main())
