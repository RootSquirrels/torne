"""The manifest — one JSON projection of what TORNE can show.

The manifest is **derived**, never edited: it is rebuilt from the catalogue
(`explorer.catalogue`), from the surface-product registry (`torne.eo`), and from
the code itself — model identities and versions are read from their modules at
build time. Building it computes nothing scientific and calls no provider.

Rules that shape it:

- **Every status and fact carries its references**, serialised with a link to
  the repository file when it points at one.
- **A country's status is earned by its missions.** A domain's status in a
  country is the highest status among that country's missions in that domain.
  Region-wide coverage (European surface products) never colours a country.
- **Concepts stay distinct**: assets, observation coverage, models and results
  are separate sections, cross-referenced by identifier.
- **The results level says when it is empty.** No knowledge record is
  persisted; runs that produced a product in memory are listed as such, never
  as published results.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .. import __version__
from ..eo import SURFACE_PRODUCTS, SurfaceProduct
from .catalogue import (
    ASSETS,
    DOMAINS,
    MISSIONS,
    MODELS,
    SOURCES,
    Asset,
    Fact,
    Mission,
    ModelEntry,
    Ref,
    RefKind,
    SourceEntry,
    Status,
)

__all__ = [
    "MANIFEST_VERSION",
    "REPOSITORY_URL",
    "build_manifest",
    "country_summary",
    "resolve_implementation",
]

MANIFEST_VERSION = "2"
"""Version of the manifest's shape, for consumers of the API."""

REPOSITORY_URL = "https://github.com/RootSquirrels/torne/blob/main/"
"""Where document and script references link to."""

KNOWLEDGE_RECORDS_GAP = (
    "No knowledge record is persisted: records are built in memory and no record format exists "
    "on disk yet. Runs that produced a product only in memory are listed separately, never as "
    "published results."
)


def resolve_implementation(target: str) -> Any:
    """The object a `module:attribute` reference names. Raises if it does not exist."""
    module_name, _, attribute = target.partition(":")
    return getattr(importlib.import_module(module_name), attribute)


def _ref(ref: Ref) -> dict[str, Any]:
    path = ref.path
    return {
        "kind": ref.kind.value,
        "target": ref.target,
        "url": f"{REPOSITORY_URL}{path}" if path else None,
    }


def _refs(refs: Iterable[Ref]) -> list[dict[str, Any]]:
    return [_ref(ref) for ref in refs]


def _fact(fact: Fact) -> dict[str, Any]:
    return {"text": fact.text, "refs": _refs(fact.refs)}


def _facts(facts: Iterable[Fact]) -> list[dict[str, Any]]:
    return [_fact(fact) for fact in facts]


def _iso(instant: datetime | None) -> str | None:
    return instant.isoformat() if instant is not None else None


def _surface_product(product: SurfaceProduct) -> dict[str, Any]:
    return {
        "collection": product.collection,
        "title": product.title,
        "quantity": product.quantity,
        "nature": product.nature.value,
        "resolution_m": product.resolution_m,
        "coverage_start": _iso(product.coverage_start),
        "coverage_end": _iso(product.coverage_end),
        "open_coverage": product.open_coverage,
        "dependence": product.dependence.value,
        "unit": product.unit,
        "unit_established": product.unit_established,
        "publication_delay": product.publication_delay,
        "instruments": list(product.instruments),
        "refs": _refs([Ref(RefKind.IMPLEMENTATION, "torne.eo.products:SURFACE_PRODUCTS")]),
    }


def _source(source: SourceEntry) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "title": source.title,
        "adapter": source.adapter,
        "adapter_ref": _ref(
            Ref(RefKind.IMPLEMENTATION, f"torne.acquisition.adapters:{source.adapter}")
        ),
        "domain_id": source.domain_id,
        "publication_class": source.publication_class,
        "qualified_in": _ref(source.qualified_in),
        "facts": _facts(source.facts),
        "mission_ids": [m.mission_id for m in MISSIONS if source.source_id in m.source_ids],
    }


def _asset(asset: Asset) -> dict[str, Any]:
    return {
        "asset_id": asset.asset_id,
        "kind": asset.kind.value,
        "name": asset.name,
        "country": asset.country,
        "domain_id": asset.domain_id,
        "source_id": asset.source_id,
        "point": list(asset.point) if asset.point else None,
        "bbox": list(asset.bbox) if asset.bbox else None,
        "location_ref": _ref(asset.location_ref),
        "facts": _facts(asset.facts),
        "mission_ids": [m.mission_id for m in MISSIONS if asset.asset_id in m.asset_ids],
    }


def _coverage() -> list[dict[str, Any]]:
    """Observation coverage: what period each asset or product covers, with evidence."""
    entries: list[dict[str, Any]] = []
    for asset in ASSETS:
        if asset.period is None or asset.period_ref is None:
            continue
        entries.append(
            {
                "subject_kind": "asset",
                "subject_id": asset.asset_id,
                "title": asset.name,
                "domain_id": asset.domain_id,
                "country": asset.country,
                "start": asset.period[0],
                "end": asset.period[1],
                "open": False,
                "refs": _refs([asset.period_ref]),
            }
        )
    for product in SURFACE_PRODUCTS.values():
        entries.append(
            {
                "subject_kind": "surface_product",
                "subject_id": product.collection,
                "title": product.title,
                "domain_id": "earth_observation",
                "country": None,
                "start": _iso(product.coverage_start),
                "end": _iso(product.coverage_end),
                "open": product.open_coverage,
                "refs": _refs([Ref(RefKind.IMPLEMENTATION, "torne.eo.products:SURFACE_PRODUCTS")]),
            }
        )
    return entries


def _model(model: ModelEntry) -> dict[str, Any]:
    identity = resolve_implementation(model.identity.target)
    version = resolve_implementation(model.version.target) if model.version else None
    return {
        "key": model.key,
        "title": model.title,
        "kind": model.kind,
        "domain_ids": list(model.domain_ids),
        "identity": identity if isinstance(identity, str) else model.identity.target,
        "identity_ref": _ref(model.identity),
        "version": version,
        "version_ref": _ref(model.version) if model.version else None,
        "executed_on_real_data": bool(model.runs),
        "runs": _facts(model.runs),
        "mission_ids": [m.mission_id for m in MISSIONS if model.key in m.model_keys],
    }


def _mission(mission: Mission) -> dict[str, Any]:
    return {
        "mission_id": mission.mission_id,
        "title": mission.title,
        "status": mission.status.label,
        "status_rank": int(mission.status),
        "status_basis": _refs(mission.status_basis),
        "domain_ids": list(mission.domain_ids),
        "countries": list(mission.countries),
        "region": mission.region,
        "question": mission.question,
        "produced": _facts(mission.produced),
        "not_established": _facts(mission.not_established),
        "asset_ids": list(mission.asset_ids),
        "source_ids": list(mission.source_ids),
        "model_keys": list(mission.model_keys),
        "knowledge_records": _refs(mission.knowledge_records),
    }


def _countries(missions: Iterable[Mission]) -> list[str]:
    return sorted({country for mission in missions for country in mission.countries})


def country_summary(country: str, missions: Iterable[Mission] = MISSIONS) -> dict[str, Any]:
    """Each domain's status in one country, earned by that country's missions."""
    code = country.upper()
    national = [m for m in missions if code in m.countries]
    domains = []
    for domain in DOMAINS:
        in_domain = [m for m in national if domain.domain_id in m.domain_ids]
        best = max((m.status for m in in_domain), default=None)
        supporting = [m.mission_id for m in in_domain if m.status == best]
        domains.append(
            {
                "domain_id": domain.domain_id,
                "title": domain.title,
                "status": best.label if best is not None else None,
                "status_rank": int(best) if best is not None else 0,
                "status_from": supporting,
                "mission_ids": [m.mission_id for m in in_domain],
                "source_ids": sorted({s for m in in_domain for s in m.source_ids}),
                "model_keys": sorted({k for m in in_domain for k in m.model_keys}),
                "asset_ids": [
                    a.asset_id
                    for a in ASSETS
                    if a.country == code and a.domain_id == domain.domain_id
                ],
            }
        )
    return {
        "country": code,
        "domains": domains,
        "asset_ids": [a.asset_id for a in ASSETS if a.country == code],
    }


def _regions(missions: Iterable[Mission]) -> list[dict[str, Any]]:
    regions: dict[str, list[Mission]] = {}
    for mission in missions:
        if mission.region is not None:
            regions.setdefault(mission.region, []).append(mission)
    return [
        {
            "region": region,
            "domain_ids": sorted({d for m in members for d in m.domain_ids}),
            "status": max(m.status for m in members).label,
            "mission_ids": [m.mission_id for m in members],
        }
        for region, members in sorted(regions.items())
    ]


def _results() -> dict[str, Any]:
    persisted = [
        {"mission_id": m.mission_id, "records": _refs(m.knowledge_records)}
        for m in MISSIONS
        if m.knowledge_records
    ]
    in_memory = [
        {
            "mission_id": m.mission_id,
            "status": m.status.label,
            "produced": _facts(m.produced),
        }
        for m in MISSIONS
        if m.status >= Status.DEMONSTRATION and not m.knowledge_records
    ]
    return {
        "persisted": persisted,
        "runs_not_persisted": in_memory,
        "gap": KNOWLEDGE_RECORDS_GAP if not persisted else None,
    }


def build_manifest(
    *,
    surface_products: Mapping[str, SurfaceProduct] = SURFACE_PRODUCTS,
) -> dict[str, Any]:
    """The whole manifest, as a JSON-serialisable mapping."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "torne_version": __version__,
        "repository_url": REPOSITORY_URL,
        "statuses": [{"status": status.label, "rank": int(status)} for status in sorted(Status)],
        "domains": [asdict(domain) for domain in DOMAINS],
        "countries": [country_summary(code) for code in _countries(MISSIONS)],
        "regions": _regions(MISSIONS),
        "missions": [_mission(mission) for mission in MISSIONS],
        "assets": [_asset(asset) for asset in ASSETS],
        "coverage": _coverage(),
        "sources": [_source(source) for source in SOURCES],
        "models": [_model(model) for model in MODELS],
        "surface_products": [_surface_product(p) for p in surface_products.values()],
        "results": _results(),
        "planned": [
            {"feature": "period filter", "needs": "persisted knowledge records"},
            {"feature": "uncertainty filter", "needs": "persisted knowledge records"},
            {"feature": "catchments", "needs": "BASIN-001 catchment geometry source"},
            {"feature": "raster coverages on the map", "needs": "pixel access to surface products"},
        ],
        "market_intelligence": {
            "open": False,
            "reason": "Objective B is deferred until the physical engine is validated "
            "(docs/ARCHITECTURE.md section 5).",
        },
    }
