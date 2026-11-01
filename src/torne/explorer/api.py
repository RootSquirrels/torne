"""The explorer API — read-only, built on the manifest, nothing else.

Every route answers from the manifest (`explorer.manifest`). No route computes a
scientific quantity, reaches a data provider, or writes anything: the API has no
`POST`, `PUT` or `DELETE`. The map front end is served from `static/` by the same
application.

Run it with the `explorer` extra installed::

    uv sync --extra explorer
    uv run torne-explorer            # http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from .catalogue import AssetKind, Status
from .manifest import build_manifest, country_summary

__all__ = ["app", "create_app", "main"]

STATIC_DIR = Path(__file__).resolve().parent / "static"

_STATUS_NAMES = {status.label: status for status in Status}


@lru_cache(maxsize=1)
def _manifest() -> dict[str, Any]:
    return build_manifest()


def _min_rank(status: str | None) -> int:
    if status is None:
        return 0
    if status not in _STATUS_NAMES:
        raise HTTPException(
            status_code=422, detail=f"unknown status {status!r}; one of {sorted(_STATUS_NAMES)}"
        )
    return int(_STATUS_NAMES[status])


def create_app() -> FastAPI:
    """The explorer application: the API under `/api`, the map at `/`."""
    application = FastAPI(
        title="TORNE Explorer",
        version=_manifest()["manifest_version"],
        description="Read-only view of what TORNE has really established.",
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "torne_version": _manifest()["torne_version"]}

    @application.get("/api/manifest")
    def manifest() -> dict[str, Any]:
        return _manifest()

    @application.get("/api/domains")
    def domains() -> list[dict[str, Any]]:
        return _manifest()["domains"]

    @application.get("/api/countries")
    def countries() -> list[dict[str, Any]]:
        return _manifest()["countries"]

    @application.get("/api/countries/{code}")
    def country(code: str) -> dict[str, Any]:
        summary = country_summary(code)
        regions = _manifest()["regions"]
        if not summary["asset_ids"] and not any(d["mission_ids"] for d in summary["domains"]):
            summary["covered"] = False
        else:
            summary["covered"] = True
        summary["regions"] = regions
        return summary

    @application.get("/api/regions")
    def regions() -> list[dict[str, Any]]:
        return _manifest()["regions"]

    @application.get("/api/missions")
    def missions(
        country: str | None = None,
        domain: str | None = None,
        min_status: str | None = Query(default=None, description="lowest status to include"),
    ) -> list[dict[str, Any]]:
        rank = _min_rank(min_status)
        return [
            m
            for m in _manifest()["missions"]
            if (country is None or country.upper() in m["countries"])
            and (domain is None or domain in m["domain_ids"])
            and m["status_rank"] >= rank
        ]

    @application.get("/api/missions/{mission_id}")
    def mission(mission_id: str) -> dict[str, Any]:
        for m in _manifest()["missions"]:
            if m["mission_id"] == mission_id:
                return m
        raise HTTPException(status_code=404, detail=f"unknown mission {mission_id!r}")

    @application.get("/api/assets")
    def assets(
        country: str | None = None,
        domain: str | None = None,
        kind: AssetKind | None = None,
    ) -> list[dict[str, Any]]:
        return [
            a
            for a in _manifest()["assets"]
            if (country is None or a["country"] == country.upper())
            and (domain is None or a["domain_id"] == domain)
            and (kind is None or a["kind"] == kind.value)
        ]

    @application.get("/api/sources")
    def sources(domain: str | None = None) -> list[dict[str, Any]]:
        return [s for s in _manifest()["sources"] if domain is None or s["domain_id"] == domain]

    @application.get("/api/surface-products")
    def surface_products(dependence: str | None = None) -> list[dict[str, Any]]:
        return [
            p
            for p in _manifest()["surface_products"]
            if dependence is None or p["dependence"] == dependence
        ]

    @application.get("/api/knowledge-products")
    def knowledge_products() -> dict[str, Any]:
        return _manifest()["knowledge_products"]

    if STATIC_DIR.is_dir():
        application.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return application


app = create_app()


def main(argv: list[str] | None = None) -> None:
    """Serve the explorer locally."""
    import uvicorn

    parser = argparse.ArgumentParser(prog="torne-explorer", description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    uvicorn.run(app, host=args.host, port=args.port)
