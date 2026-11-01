"""TORNE Explorer API — the contract the application promises.

**The API is versioned and says so.** `/api/v1` is canonical: it is the only
prefix the OpenAPI document describes. `/api` still answers, marked as
deprecated and pointing at its successor, so a consumer written against the
previous version keeps working while it migrates.

**Every failure has the same shape.** A response carries `detail` — the field
FastAPI has always returned — and `error`, a stable machine-readable
description. The two never disagree.

**The schemas are declared.** Every route declares the model it serves, so the
OpenAPI document is a description of the API rather than of a guess about it.

**The boundary holds.** The scientific layers never import FastAPI, and the
application exposes reads only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from torne.explorer import build_manifest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from torne.explorer.api import app

    return TestClient(app)


# --------------------------------------------------------------------------
# Versioning
# --------------------------------------------------------------------------


def test_the_canonical_api_answers(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_the_legacy_api_still_answers(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == client.get("/api/v1/health").json()


def test_the_legacy_api_marks_its_answers_as_deprecated(client):
    response = client.get("/api/manifest")

    assert response.headers.get("Deprecation") == "true"
    assert "/api/v1/manifest" in response.headers.get("Link", "")


def test_the_canonical_api_is_not_marked_as_deprecated(client):
    response = client.get("/api/v1/manifest")

    assert "Deprecation" not in response.headers


def test_the_deprecation_rule_is_published(client):
    """The removal of the legacy prefix is announced, not implied.

    A deprecation without a published rule is a side effect waiting to happen:
    the rule has to say what the legacy prefix is, how a consumer migrates,
    and on what ground it goes away.
    """
    document = client.get("/api/v1/openapi.json").json()

    description = document["info"]["description"]

    assert "/api/v1" in description, "the canonical prefix must be named"
    assert "Deprecation" in description, "the header a consumer follows must be named"
    assert "one announced step" in description, "the removal must be a decided step"
    assert "side effect" in description, "the removal must not be an accident"


def test_the_openapi_document_describes_the_canonical_api_only(client):
    document = client.get("/api/v1/openapi.json").json()

    paths = set(document["paths"])
    assert paths, "the document must describe the routes"
    assert all(path.startswith("/api/v1/") for path in paths), paths
    assert not any(path.startswith("/api/") and not path.startswith("/api/v1/") for path in paths)


def test_the_openapi_document_is_valid_json(client):
    document = client.get("/api/v1/openapi.json")

    assert document.status_code == 200
    json.loads(document.text)


# --------------------------------------------------------------------------
# The responses
# --------------------------------------------------------------------------


def test_the_canonical_manifest_is_the_derived_manifest(client):
    response = client.get("/api/v1/manifest")

    assert response.status_code == 200
    assert response.json() == json.loads(json.dumps(build_manifest()))


def test_every_route_declares_the_model_it_serves(client):
    """A route without a response model would leave the document a guess."""
    from fastapi.routing import APIRoute

    from torne.explorer.api import app

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        assert route.response_model is not None, route.path


def test_the_document_describes_the_fields_and_their_meaning(client):
    document = client.get("/api/v1/openapi.json").json()

    mission = document["components"]["schemas"]["Mission"]
    properties = mission["properties"]

    assert properties["status"]["description"]
    assert properties["status_basis"]["description"]
    # A field that is not established stays null: the schema must allow it.
    assert "anyOf" in properties["region"] or "nullable" in properties["region"]


def test_the_api_exposes_no_write_route(client):
    from torne.explorer.api import app

    methods = {
        method for route in app.routes for method in getattr(route, "methods", set()) or set()
    }
    assert methods <= {"GET", "HEAD"}


# --------------------------------------------------------------------------
# The errors
# --------------------------------------------------------------------------


def test_an_unknown_identifier_is_a_not_found(client):
    response = client.get("/api/v1/missions/NOPE")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "unknown mission 'NOPE'"
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == body["detail"]


def test_an_unknown_status_is_refused(client):
    response = client.get("/api/v1/missions", params={"min_status": "validated"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unprocessable_entity"


def test_a_malformed_request_is_a_validation_error(client):
    """The asset kind is a closed vocabulary; anything else is refused."""
    response = client.get("/api/v1/assets", params={"kind": "not-a-kind"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"]


def test_the_legacy_api_returns_the_same_error_shape(client):
    response = client.get("/api/missions/NOPE")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --------------------------------------------------------------------------
# The compiled application
# --------------------------------------------------------------------------

STATIC_DIR = ROOT / "src" / "torne" / "explorer" / "static"

requires_frontend = pytest.mark.skipif(
    not (STATIC_DIR / "index.html").is_file(),
    reason="the compiled frontend is not built",
)


@requires_frontend
def test_the_application_is_served_at_the_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@requires_frontend
@pytest.mark.parametrize("path", ["/country/FR", "/mission/ATMO-001", "/workbench"])
def test_a_client_route_answers_with_the_application(client, path):
    """A route the browser asks for directly must answer with the application.

    The application reads the path and renders the right view. A 404 here
    would break every bookmark, every shared link and every reload.
    """
    response = client.get(path)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@requires_frontend
@pytest.mark.parametrize("path", ["/api/v1/does-not-exist", "/api/does-not-exist"])
def test_an_unknown_endpoint_is_an_error_and_not_a_page(client, path):
    """The API answers an unknown endpoint with an error, never with a page."""
    response = client.get(path)

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == body["detail"]


@requires_frontend
def test_a_missing_asset_is_an_error_and_not_a_page(client):
    """A missing script must fail as a missing script.

    Answering with the application would hand the browser a page where it
    expects a script, and the failure would be reported as a syntax error
    rather than as the missing file it is.
    """
    response = client.get("/assets/does-not-exist.js")

    assert response.status_code == 404
    assert "text/html" not in response.headers["content-type"]


@requires_frontend
def test_an_existing_asset_is_served_as_it_is(client):
    response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]


# --------------------------------------------------------------------------
# The boundary
# --------------------------------------------------------------------------


def test_the_scientific_layers_never_import_fastapi():
    """FastAPI is an application concern; no scientific module may import it."""
    scientific = [
        path
        for path in (ROOT / "src" / "torne").rglob("*.py")
        if "explorer" not in path.relative_to(ROOT / "src" / "torne").parts
    ]
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in scientific
        if "fastapi" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_the_explorer_is_not_imported_by_the_scientific_layers():
    """The socle and the semantic layers must not depend on the application."""
    scientific = [
        path
        for path in (ROOT / "src" / "torne").rglob("*.py")
        if "explorer" not in path.relative_to(ROOT / "src" / "torne").parts
    ]
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in scientific
        if "explorer" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders
