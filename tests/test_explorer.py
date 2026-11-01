"""TORNE Explorer — every fact is traceable, and the API only reads.

Three families of checks, all offline.

**Every reference resolves.** Each fact, status, location and coverage period in
the catalogue carries references; documents and scripts must exist, a `§section`
must be a heading of that document, `module:attribute` must import, and mission
references must name a mission. A renamed file or moved constant fails here.

**Declared metadata agrees with the code.** Source identifiers match the adapters,
the STAC publication class matches the adapter's own `Source`, model identities
are read from code, and no mission claims `KNOWLEDGE` without a persisted record.

**The boundary holds.** The API exposes only reads, and the front end calls no
data provider.
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

import torne.acquisition.adapters as adapters
from torne.eo import SURFACE_PRODUCTS
from torne.explorer import ASSETS, MISSIONS, MODELS, SOURCES, Status, build_manifest
from torne.explorer.catalogue import DOMAINS, Fact, Mission, Ref, RefKind
from torne.explorer.manifest import KNOWLEDGE_RECORDS_GAP, country_summary, resolve_implementation
from torne.knowledge.store import read_record

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "src" / "torne" / "explorer" / "static"


def _all_refs() -> list[Ref]:
    refs: list[Ref] = []
    for source in SOURCES:
        refs.append(source.qualified_in)
        refs += [r for f in source.facts for r in f.refs]
    for asset in ASSETS:
        refs.append(asset.location_ref)
        refs += [asset.period_ref] if asset.period_ref else []
        refs += [r for f in asset.facts for r in f.refs]
    for model in MODELS:
        refs.append(model.identity)
        refs += [model.version] if model.version else []
        refs += [r for f in model.runs for r in f.refs]
    for mission in MISSIONS:
        refs += list(mission.status_basis)
        refs += [r for f in mission.produced + mission.not_established for r in f.refs]
        refs += list(mission.knowledge_records)
    return refs


def _all_facts() -> list[Fact]:
    facts: list[Fact] = []
    for source in SOURCES:
        facts += source.facts
    for asset in ASSETS:
        facts += asset.facts
    for model in MODELS:
        facts += model.runs
    for mission in MISSIONS:
        facts += mission.produced + mission.not_established
    return facts


# --------------------------------------------------------------------------
# Every reference resolves
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ref", sorted(set(_all_refs()), key=lambda r: (r.kind, r.target)))
def test_every_reference_resolves(ref):
    if ref.kind in (RefKind.DOCUMENT, RefKind.SCRIPT):
        path = ROOT / ref.path
        assert path.is_file(), ref.target
        if " §" in ref.target:
            section = ref.target.split(" §")[1]
            text = path.read_text(encoding="utf-8")
            pattern = rf"^#+ {re.escape(section)}[ .]"
            assert re.search(pattern, text, flags=re.MULTILINE), (
                f"no section {section} in {path.name}"
            )
    elif ref.kind is RefKind.IMPLEMENTATION:
        resolve_implementation(ref.target)
    elif ref.kind is RefKind.MISSION:
        assert ref.target in {m.mission_id for m in MISSIONS}
    elif ref.kind is RefKind.RECORD:
        path = ROOT / ref.target
        assert path.is_file(), ref.target
        read_record(path)


def test_a_fact_without_evidence_cannot_be_built():
    with pytest.raises(ValueError, match="at least one reference"):
        Fact("unsupported", ())


def test_identifiers_cross_reference_correctly():
    domain_ids = {d.domain_id for d in DOMAINS}
    source_ids = {s.source_id for s in SOURCES}
    asset_ids = {a.asset_id for a in ASSETS}
    model_keys = {m.key for m in MODELS}
    for source in SOURCES:
        assert source.domain_id in domain_ids
    for asset in ASSETS:
        assert asset.domain_id in domain_ids
        assert asset.source_id in source_ids
    for model in MODELS:
        assert set(model.domain_ids) <= domain_ids, model.key
    for mission in MISSIONS:
        assert set(mission.domain_ids) <= domain_ids, mission.mission_id
        assert set(mission.source_ids) <= source_ids, mission.mission_id
        assert set(mission.asset_ids) <= asset_ids, mission.mission_id
        assert set(mission.model_keys) <= model_keys, mission.mission_id


def test_domains_name_their_semantic_layer():
    for domain in DOMAINS:
        importlib.import_module(domain.semantic_layer)


# --------------------------------------------------------------------------
# Declared metadata agrees with the code
# --------------------------------------------------------------------------


def test_every_source_names_an_exported_adapter():
    for source in SOURCES:
        assert source.adapter in adapters.__all__, source.source_id


def test_source_identifiers_appear_in_their_adapter():
    for source in SOURCES:
        module = inspect.getmodule(getattr(adapters, source.adapter))
        constant = getattr(module, "SOURCE_ID", None)
        text = inspect.getsource(module)
        if constant == source.source_id:
            continue
        # Adapters whose identifier is built per request carry it as a literal or a pattern.
        prefix = source.source_id.rsplit(".", 1)[0]
        assert f'"{source.source_id}"' in text or f'"{prefix}.' in text, source.source_id


def test_the_stac_publication_class_matches_the_adapter():
    from torne.acquisition.adapters.copernicus_stac import CopernicusStacAdapter
    from torne.contracts.spatial import BoundingBox

    adapter = CopernicusStacAdapter(
        collections=["sentinel-2-l2a"],
        start=datetime(2023, 1, 1, tzinfo=UTC),
        end=datetime(2023, 2, 1, tzinfo=UTC),
        page_size=1,
        max_pages=1,
        bbox=BoundingBox(west=0.0, south=40.0, east=1.0, north=41.0),
    )
    entry = next(s for s in SOURCES if s.source_id == adapter.source.source_id)

    assert entry.publication_class == adapter.source.publication_class.value


def test_model_identities_are_read_from_code():
    manifest = {m["key"]: m for m in build_manifest()["models"]}
    for model in MODELS:
        identity = resolve_implementation(model.identity.target)
        if isinstance(identity, str):
            assert manifest[model.key]["identity"] == identity
        if model.version:
            assert manifest[model.key]["version"] == resolve_implementation(model.version.target)


def test_effective_sample_size_facts_cite_the_atmo_002_audit():
    """ATMO-002 showed the figure depends on the lag cap: no bare single value may remain."""
    for fact in _all_facts():
        if "effective sample size" in fact.text.lower():
            assert any(r.target == "docs/ATMO-002.md §3.1" for r in fact.refs), fact.text


def test_no_mission_claims_knowledge_without_a_persisted_record():
    with pytest.raises(ValueError, match="persisted knowledge record"):
        Mission(
            mission_id="X",
            title="x",
            status=Status.KNOWLEDGE,
            status_basis=(Ref(RefKind.DOCUMENT, "README.md"),),
            domain_ids=("hydrology",),
            countries=("FR",),
            region=None,
            question="q",
            produced=(),
            not_established=(),
        )
    assert all(m.status is not Status.KNOWLEDGE for m in MISSIONS if m.mission_id != "LNG-002")
    knowledge = [m for m in MISSIONS if m.status is Status.KNOWLEDGE]
    assert [m.mission_id for m in knowledge] == ["LNG-002"]
    assert all(m.knowledge_records for m in knowledge)


def test_a_status_without_evidence_cannot_be_built():
    with pytest.raises(ValueError, match="supporting evidence"):
        Mission(
            mission_id="X",
            title="x",
            status=Status.QUALIFICATION,
            status_basis=(),
            domain_ids=("hydrology",),
            countries=("FR",),
            region=None,
            question="q",
            produced=(),
            not_established=(),
        )


# --------------------------------------------------------------------------
# The manifest
# --------------------------------------------------------------------------


def test_the_manifest_is_json_and_derived_from_the_registry():
    manifest = build_manifest()

    json.dumps(manifest)
    products = [c for c in manifest["coverage"] if c["subject_kind"] == "surface_product"]
    assert len(products) == len(SURFACE_PRODUCTS)
    assert manifest["results"]["gap"]
    branches = {branch["branch_id"]: branch for branch in manifest["branches"]}
    assert branches["supply"]["open"] is True
    assert branches["market"]["open"] is False


def test_runs_that_produced_a_product_are_not_presented_as_published():
    results = build_manifest()["results"]

    assert [r["mission_id"] for r in results["runs_not_persisted"]] == ["mission-002"]
    assert [p["mission_id"] for p in results["persisted"]] == ["LNG-002"]


def test_the_gap_names_the_results_that_are_still_only_in_memory():
    """A persisted record closes the "nothing is persisted" gap.

    The runs that did not persist anything remain listed, and the gap says so:
    publishing one product does not make the others published.
    """
    results = build_manifest()["results"]

    assert results["gap"], "a run that stayed in memory is a gap the manifest names"
    assert results["gap"] != KNOWLEDGE_RECORDS_GAP, (
        "a record is persisted: the gap is not that nothing is persisted"
    )
    assert [r["mission_id"] for r in results["runs_not_persisted"]] == ["mission-002"]


def test_a_country_status_is_the_best_status_of_its_missions():
    france = {d["domain_id"]: d for d in country_summary("fr")["domains"]}

    assert france["hydrology"]["status"] == "qualification"
    assert france["atmosphere"]["status"] == "exploration"
    assert set(france["atmosphere"]["status_from"]) == {"ATMO-001", "ATMO-002"}
    # Region-wide surface products never colour a country by themselves.
    assert france["earth_observation"]["status"] is None


def test_an_uncovered_country_has_no_status():
    summary = country_summary("JP")

    assert all(d["status"] is None for d in summary["domains"])
    assert summary["asset_ids"] == []


def test_a_country_answered_for_carries_the_status_of_its_domain():
    """A mission that covers a country is visible in that country's summary.

    The domain that was answered for says so; the others stay unknown. A
    country is not covered by a mission, and a domain is not covered by
    another domain's work.
    """
    summary = country_summary("DE")

    gas = next(d for d in summary["domains"] if d["domain_id"] == "gas")
    assert gas["status"] == "knowledge"
    assert gas["mission_ids"] == ["LNG-002"]
    assert all(d["status"] is None for d in summary["domains"] if d["domain_id"] != "gas")


def test_every_document_reference_links_to_the_repository():
    manifest = build_manifest()
    for mission in manifest["missions"]:
        for ref in mission["status_basis"]:
            if ref["kind"] in ("document", "script"):
                assert ref["url"].startswith(manifest["repository_url"])


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

    assert {m["mission_id"] for m in french} == {"HYDRO-001", "ATMO-001", "ATMO-002", "LNG-002"}
    assert [m["mission_id"] for m in advanced] == ["mission-002", "LNG-002"]


def test_the_api_refuses_an_unknown_status(client):
    assert client.get("/api/missions", params={"min_status": "validated"}).status_code == 422


def test_the_api_serves_a_country_domain(client):
    atmosphere = client.get("/api/countries/FR/domains/atmosphere").json()

    assert atmosphere["status"] == "exploration"
    assert len(atmosphere["asset_ids"]) == 4
    assert "meteofrance.climatology" in atmosphere["source_ids"]


def test_the_api_separates_models_coverage_and_results(client):
    executed = client.get("/api/models", params={"executed": "true"}).json()
    not_run = client.get("/api/models", params={"executed": "false"}).json()
    coverage = client.get("/api/coverage", params={"domain": "atmosphere"}).json()
    results = client.get("/api/results").json()

    assert "hydrology-rating" in {m["key"] for m in not_run}
    assert "hydrology-rating" not in {m["key"] for m in executed}
    assert {c["subject_id"] for c in coverage} == {
        "FRE00104040",
        "FRM00007156",
        "FR000007630",
        "FR000007650",
    }
    assert [p["mission_id"] for p in results["persisted"]] == ["LNG-002"]


def test_the_api_filters_assets_by_kind_and_country(client):
    stations = client.get("/api/assets", params={"country": "FR", "kind": "station"}).json()

    assert len(stations) == 4
    assert client.get("/api/assets", params={"kind": "catchment"}).json() == []


@pytest.mark.parametrize("path", ["/api/missions/NOPE", "/api/assets/NOPE", "/api/models/NOPE"])
def test_unknown_identifiers_are_404(client, path):
    assert client.get(path).status_code == 404


def test_the_api_exposes_no_write_route(client):
    from torne.explorer.api import app

    methods = {
        method for route in app.routes for method in getattr(route, "methods", set()) or set()
    }
    assert methods <= {"GET", "HEAD"}


def test_the_compiled_frontend_is_served_at_the_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "TORNE Explorer" in response.text
    assert '<div id="root">' in response.text


# --------------------------------------------------------------------------
# The front end
# --------------------------------------------------------------------------

FRONTEND = ROOT / "frontend" / "src"


def _frontend_sources() -> list[Path]:
    return sorted(path for path in FRONTEND.rglob("*.ts*") if path.is_file())


def test_the_front_end_calls_no_data_provider():
    """It reads the API only; it never contacts a data provider."""
    sources = _frontend_sources()
    assert sources, "the frontend sources must be present"
    for path in sources:
        code = path.read_text(encoding="utf-8")
        for provider in (
            "hubeau",
            "usgs.gov",
            "dataspace.copernicus",
            "meteofrance",
            "ncei.noaa",
        ):
            assert provider not in code, f"{provider} in {path.name}"


def test_the_front_end_reads_the_versioned_api():
    code = (FRONTEND / "services" / "api" / "client.ts").read_text(encoding="utf-8")

    assert "/api/v1" in code


def test_the_front_end_has_no_runtime_cdn_dependency():
    """Nothing is fetched from a CDN at runtime: the application is self-contained."""
    for path in _frontend_sources():
        code = path.read_text(encoding="utf-8")
        assert "cdn.jsdelivr.net" not in code, path.name
        assert "cdnjs.cloudflare.com" not in code, path.name


def test_planned_features_are_advertised_rather_than_implemented():
    """The API says what is planned instead of pretending to serve it."""
    manifest = build_manifest()

    features = {entry["feature"] for entry in manifest["planned"]}
    assert features, "the manifest must say what is planned"
    branches = {branch["branch_id"]: branch for branch in manifest["branches"]}
    assert branches["market"]["open"] is False
    assert branches["market"]["reason"], "a closed branch says why it is closed"
