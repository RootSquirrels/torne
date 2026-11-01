"""The manifest — one JSON projection of what TORNE can show.

The manifest is **derived**, never edited: it is rebuilt from the catalogue
(`explorer.catalogue`), from the surface-product registry (`torne.eo`) and from
the adapters the acquisition socle exports. It uses the standard library only,
so that it can be built, tested and inspected without the web stack.

Two rules shape it:

- **A country's status is earned by its missions.** A domain's status in a
  country is the highest status among the missions of that domain in that
  country. Region-wide coverage (the European surface products) is reported as
  such, and never colours a country by itself.
- **The knowledge level says when it is empty.** Knowledge records are not
  persisted by the repository today; the manifest says so instead of showing
  an empty list as if nothing had been asked.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .. import __version__
from ..eo import SURFACE_PRODUCTS, SurfaceProduct
from .catalogue import ASSETS, DOMAINS, MISSIONS, SOURCES, Asset, Mission, Status

__all__ = ["MANIFEST_VERSION", "build_manifest", "country_summary"]

MANIFEST_VERSION = "1"
"""Version of the manifest's shape, for consumers of the API."""

KNOWLEDGE_RECORDS_GAP = (
    "Knowledge records are built in memory and not persisted: no record format exists on disk "
    "yet, so no knowledge product can be listed. See docs/PROGRAMME.md section 6."
)


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
    }


def _asset(asset: Asset) -> dict[str, Any]:
    entry = asdict(asset)
    entry["kind"] = asset.kind.value
    entry["point"] = list(asset.point) if asset.point else None
    entry["bbox"] = list(asset.bbox) if asset.bbox else None
    entry["period"] = list(asset.period) if asset.period else None
    entry["facts"] = list(asset.facts)
    return entry


def _mission(mission: Mission) -> dict[str, Any]:
    return {
        "mission_id": mission.mission_id,
        "title": mission.title,
        "status": mission.status.label,
        "status_rank": int(mission.status),
        "domain_ids": list(mission.domain_ids),
        "countries": list(mission.countries),
        "region": mission.region,
        "question": mission.question,
        "produced": mission.produced,
        "not_established": mission.not_established,
        "records": list(mission.records),
        "asset_ids": list(mission.asset_ids),
        "source_ids": list(mission.source_ids),
        "knowledge_record_ids": list(mission.knowledge_record_ids),
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
        domains.append(
            {
                "domain_id": domain.domain_id,
                "title": domain.title,
                "status": best.label if best is not None else None,
                "status_rank": int(best) if best is not None else 0,
                "mission_ids": [m.mission_id for m in in_domain],
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


def build_manifest(
    *,
    surface_products: Mapping[str, SurfaceProduct] = SURFACE_PRODUCTS,
) -> dict[str, Any]:
    """The whole manifest, as a JSON-serialisable mapping."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "torne_version": __version__,
        "statuses": [{"status": status.label, "rank": int(status)} for status in sorted(Status)],
        "domains": [asdict(domain) for domain in DOMAINS],
        "countries": [country_summary(code) for code in _countries(MISSIONS)],
        "regions": _regions(MISSIONS),
        "missions": [_mission(mission) for mission in MISSIONS],
        "assets": [_asset(asset) for asset in ASSETS],
        "sources": [asdict(source) for source in SOURCES],
        "surface_products": [_surface_product(p) for p in surface_products.values()],
        "knowledge_products": {"persisted": False, "items": [], "gap": KNOWLEDGE_RECORDS_GAP},
        "market_intelligence": {
            "open": False,
            "reason": "Objective B is deferred until the physical engine is validated "
            "(docs/ARCHITECTURE.md section 5).",
        },
    }
