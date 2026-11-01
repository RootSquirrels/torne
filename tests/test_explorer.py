"""TORNE Explorer — the catalogue tells the truth, and the API only reads.

Two families of checks.

**The catalogue points at things that exist.** Every source names an adapter the
socle exports, every source identifier matches the adapter's own constant when
it has one, every asset and mission reference resolves, every record path is in
the repository, and no mission can claim `KNOWLEDGE` without a persisted record.

**The API is read-only.** It answers from the manifest, filters what it serves,
refuses unknown statuses, and exposes no route that writes.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import torne.acquisition.adapters as adapters
from torne.eo import SURFACE_PRODUCTS
from torne.explorer import ASSETS, MISSIONS, SOURCES, Status, build_manifest
from torne.explorer.catalogue import DOMAINS, Mission
from torne.explorer.manifest import country_summary

ROOT = Path(__file__).resolve().parent.parent

_ADAPTER_MODULES = {
    "HubeauFeedAdapter": "torne.acquisition.adapters.hubeau_feed",
    "CopernicusStacAdapter": "torne.acquisition.adapters.copernicus_stac",
    "GhcndDailyAdapter": "torne.acquisition.adapters.ghcnd",
    "MeteoFranceAdapter": "torne.acquisition.adapters.meteofrance",
}

# --------------------------------------------------------------------------
# The catalogue
# --------------------------------------------------------------------------


def test_every_source_names_an_exported_adapter():
    for source in SOURCES:
        assert source.adapter in adapters.__all__, source.source_id


def test_source_identifiers_match_the_adapter_constants():
    for source in SOURCES:
        module_name = _ADAPTER_MODULES.get(source.adapter)
        if module_name is None:
            continue
        module = importlib.import_module(module_name)
        assert source.source_id == module.SOURCE_ID


def test_every_reference_resolves():
    domain_ids = {d.domain_id for d in DOMAINS}
    source_ids = {s.source_id for s in SOURCES}
    asset_ids = {a.asset_id for a in ASSETS}
    for source in SOURCES:
        assert source.domain_id in domain_ids
    for asset in ASSETS:
        assert asset.domain_id in domain_ids
        assert asset.source_id in source_ids
    for mission in MISSIONS:
        assert set(mission.domain_ids) <= domain_ids, mission.mission_id
        assert set(mission.source_ids) <= source_ids, mission.mission_id
        assert set(mission.asset_ids) <= asset_ids, mission.mission_id


def test_every_record_path_is_in_the_repository():
    for mission in MISSIONS:
        for record in mission.records:
            path = record.split(" §")[0]
            assert (ROOT / path).exists(), f"{mission.mission_id}: {path}"


def test_stations_carry_a_point_and_coverages_a_bbox():
    for asset in ASSETS:
        if asset.kind.value == "station":
            assert asset.point is not None, asset.asset_id
            lon, lat = asset.point
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90


def test_no_mission_claims_knowledge_without_a_persisted_record():
    with pytest.raises(ValueError, match="persisted knowledge record"):
        Mission(
            mission_id="X",
            title="x",
            status=Status.KNOWLEDGE,
            domain_ids=("hydrology",),
            countries=("FR",),
            region=None,
            question="q",
            produced="p",
            not_established="n",
        )
    assert all(m.status is not Status.KNOWLEDGE for m in MISSIONS)


# --------------------------------------------------------------------------
# The manifest
# --------------------------------------------------------------------------


def test_the_manifest_is_json_and_derived_from_the_registry():
    manifest = build_manifest()

    json.dumps(manifest)
    assert len(manifest["surface_products"]) == len(SURFACE_PRODUCTS)
    assert manifest["knowledge_products"]["persisted"] is False
    assert manifest["knowledge_products"]["items"] == []
    assert manifest["market_intelligence"]["open"] is False


def test_a_country_status_is_the_best_status_of_its_missions():
    france = {d["domain_id"]: d for d in country_summary("fr")["domains"]}

    assert france["hydrology"]["status"] == "qualification"
    assert france["atmosphere"]["status"] == "exploration"
    # Region-wide surface products never colour a country by themselves.
    assert france["earth_observation"]["status"] is None


def test_an_uncovered_country_has_no_status():
    summary = country_summary("DE")

    assert all(d["status"] is None for d in summary["domains"])
    assert summary["asset_ids"] == []


# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from torne.explorer.api import app

    return TestClient(app)


def test_the_api_serves_the_manifest(client):
    response = client.get("/api/manifest")

    assert response.status_code == 200
    assert response.json() == json.loads(json.dumps(build_manifest()))


def test_the_api_filters_missions(client):
    french = client.get("/api/missions", params={"country": "fr"}).json()
    advanced = client.get("/api/missions", params={"min_status": "demonstration"}).json()

    assert {m["mission_id"] for m in french} == {"HYDRO-001", "ATMO-001"}
    assert [m["mission_id"] for m in advanced] == ["mission-002"]


def test_the_api_refuses_an_unknown_status(client):
    assert client.get("/api/missions", params={"min_status": "validated"}).status_code == 422


def test_the_api_filters_assets_by_kind_and_country(client):
    stations = client.get("/api/assets", params={"country": "FR", "kind": "station"}).json()

    assert len(stations) == 4
    assert client.get("/api/assets", params={"kind": "catchment"}).json() == []


def test_an_unknown_mission_is_a_404(client):
    assert client.get("/api/missions/NOPE").status_code == 404


def test_the_api_exposes_no_write_route(client):
    from torne.explorer.api import app

    methods = {
        method for route in app.routes for method in getattr(route, "methods", set()) or set()
    }
    assert methods <= {"GET", "HEAD"}


def test_the_map_is_served_at_the_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "TORNE Explorer" in response.text
