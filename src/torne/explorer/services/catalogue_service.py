"""The catalogue read service.

The service owns the queries the HTTP layer asks for: the cached manifest, the
filters, and the lookups by identifier. It computes nothing scientific, calls
no provider and writes nothing — it reads the projection and answers about
it.

Keeping the queries here rather than in the routers means the HTTP layer only
translates between HTTP and these calls, and the same queries can be reused
by a future consumer that is not HTTP.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..manifest import build_manifest, country_summary

__all__ = [
    "UnknownStatus",
    "countries",
    "country_detail",
    "country_domain",
    "coverage",
    "domains",
    "manifest",
    "mission",
    "missions",
    "model",
    "models",
    "regions",
    "results",
    "source",
    "sources",
    "status_rank",
    "surface_products",
]


class UnknownStatus(ValueError):
    """A status name that is not part of the closed vocabulary."""

    def __init__(self, status: str, known: list[str]) -> None:
        super().__init__(f"unknown status {status!r}; one of {sorted(known)}")
        self.status = status
        self.known = known


@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    """The whole manifest, built once and held in memory."""
    return build_manifest()


def _status_ranks() -> dict[str, int]:
    return {entry["status"]: entry["rank"] for entry in manifest()["statuses"]}


def status_rank(status: str) -> int:
    """The rank of a status in the closed vocabulary.

    Raises `UnknownStatus` for a name outside the vocabulary: the status
    vocabulary is closed, and an unknown name is an error, not a zero.
    """
    ranks = _status_ranks()
    if status not in ranks:
        raise UnknownStatus(status, list(ranks))
    return ranks[status]


def _one(section: str, key: str, value: str) -> dict[str, Any] | None:
    for item in manifest()[section]:
        if item[key] == value:
            return item
    return None


# ------------------------------------------------------------------ catalogue


def domains() -> list[dict[str, Any]]:
    """The observation modalities."""
    return manifest()["domains"]


def countries() -> list[dict[str, Any]]:
    """What each country holds, domain by domain."""
    return manifest()["countries"]


def country_detail(code: str) -> dict[str, Any]:
    """One country, with the region-wide coverage that surrounds it.

    A country no mission touched is not an error: it is a country with no
    status, and the API says so.
    """
    summary = country_summary(code)
    summary["covered"] = any(domain["mission_ids"] for domain in summary["domains"])
    summary["regions"] = manifest()["regions"]
    return summary


def country_domain(code: str, domain_id: str) -> dict[str, Any] | None:
    """One domain's status in one country."""
    for domain in country_summary(code)["domains"]:
        if domain["domain_id"] == domain_id:
            return domain
    return None


def regions() -> list[dict[str, Any]]:
    """The region-wide scopes."""
    return manifest()["regions"]


def coverage(*, domain: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    """The periods observations and products cover."""
    return [
        entry
        for entry in manifest()["coverage"]
        if (domain is None or entry["domain_id"] == domain)
        and (country is None or entry["country"] in (None, country.upper()))
    ]


def surface_products(*, dependence: str | None = None) -> list[dict[str, Any]]:
    """The surface observation products."""
    return [
        product
        for product in manifest()["surface_products"]
        if dependence is None or product["dependence"] == dependence
    ]


# -------------------------------------------------------------------- missions


def missions(
    *,
    country: str | None = None,
    domain: str | None = None,
    min_status: str | None = None,
) -> list[dict[str, Any]]:
    """The missions, filtered by country, domain and minimum status."""
    rank = status_rank(min_status) if min_status is not None else 0
    return [
        entry
        for entry in manifest()["missions"]
        if (country is None or country.upper() in entry["countries"])
        and (domain is None or domain in entry["domain_ids"])
        and entry["status_rank"] >= rank
    ]


def mission(mission_id: str) -> dict[str, Any] | None:
    """One mission."""
    return _one("missions", "mission_id", mission_id)


# ---------------------------------------------------------------------- assets


def assets(
    *,
    country: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    """The physical assets the missions touched."""
    return [
        entry
        for entry in manifest()["assets"]
        if (country is None or entry["country"] == country.upper())
        and (domain is None or entry["domain_id"] == domain)
        and (kind is None or entry["kind"] == kind)
    ]


def asset(asset_id: str) -> dict[str, Any] | None:
    """One asset."""
    return _one("assets", "asset_id", asset_id)


# --------------------------------------------------------------------- sources


def sources(*, domain: str | None = None) -> list[dict[str, Any]]:
    """The sources, and their established behaviour."""
    return [
        entry for entry in manifest()["sources"] if domain is None or entry["domain_id"] == domain
    ]


def source(source_id: str) -> dict[str, Any] | None:
    """One source."""
    return _one("sources", "source_id", source_id)


# ---------------------------------------------------------------------- models


def models(*, executed: bool | None = None) -> list[dict[str, Any]]:
    """The models and methods, and where they ran."""
    return [
        entry
        for entry in manifest()["models"]
        if executed is None or entry["executed_on_real_data"] is executed
    ]


def model(key: str) -> dict[str, Any] | None:
    """One model or method."""
    return _one("models", "key", key)


# --------------------------------------------------------------------- results


def results() -> dict[str, Any]:
    """What is published, and what was only run."""
    return manifest()["results"]
