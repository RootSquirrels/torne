"""TORNE Explorer API — the caching the catalogue promises.

**The catalogue may be reused.** Every catalogue answer carries an `ETag`,
the hash of the bytes it is made of, and a `Cache-Control` that says for how
long a client may keep it. A client that repeats the `ETag` it was given
receives a `304 Not Modified` with no body: the answer is unchanged, and
nothing is sent again.

**What is not the catalogue is not cached like it.** The health route says
whether the application is up *now*, and is never stored. A failure is never
stored either. The compiled application has its own rules, because its HTML
names the files that carry its assets.

**The two prefixes are the same routes.** The legacy prefix keeps its
deprecation headers and gains the same caching behaviour.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "src" / "torne" / "explorer" / "static"

CATALOGUE_ROUTES = (
    "/api/v1/manifest",
    "/api/v1/domains",
    "/api/v1/countries",
    "/api/v1/missions",
    "/api/v1/assets",
    "/api/v1/sources",
    "/api/v1/models",
    "/api/v1/results",
    "/api/v1/coverage",
    "/api/v1/surface-products",
)


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from torne.explorer.api import app

    return TestClient(app)


@pytest.fixture(scope="module")
def caching():
    """The caching layer, imported where it lives."""
    pytest.importorskip("fastapi")
    import torne.explorer.api.caching as module

    return module


@pytest.fixture(scope="module")
def hashed_asset():
    """The path of a file under `/assets/`, whose name carries a content hash."""
    files = sorted(path for path in (STATIC_DIR / "assets").glob("*") if path.is_file())
    if not files:
        pytest.skip("the compiled frontend is not built")
    return "/" + files[0].relative_to(STATIC_DIR).as_posix()


requires_frontend = pytest.mark.skipif(
    not (STATIC_DIR / "index.html").is_file(),
    reason="the compiled frontend is not built",
)


# --------------------------------------------------------------------------
# The catalogue answers
# --------------------------------------------------------------------------


def test_a_catalogue_answer_carries_an_etag(client):
    response = client.get("/api/v1/manifest")

    assert response.status_code == 200
    etag = response.headers.get("ETag")
    assert etag, "a catalogue answer must say how it is identified"
    assert etag.startswith('"'), etag
    assert etag.endswith('"'), etag
    assert len(etag) == 66, etag


def test_a_catalogue_answer_may_be_reused(client):
    """The catalogue changes rarely, and a slightly old catalogue is harmless."""
    response = client.get("/api/v1/manifest")

    cache_control = response.headers.get("Cache-Control", "")
    assert "public" in cache_control, cache_control
    assert "max-age=" in cache_control, cache_control


@pytest.mark.parametrize("path", CATALOGUE_ROUTES)
def test_every_catalogue_route_may_be_reused(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers.get("ETag"), path
    assert "public" in response.headers.get("Cache-Control", ""), path


def test_a_repeated_request_answers_not_modified(client):
    """A client that holds the answer is told it holds it, and nothing is sent."""
    first = client.get("/api/v1/manifest")
    etag = first.headers["ETag"]

    second = client.get("/api/v1/manifest", headers={"If-None-Match": etag})

    assert second.status_code == 304
    assert second.content == b""
    assert second.headers.get("ETag") == etag


def test_the_etag_is_the_hash_of_the_body(client, caching):
    """The tag identifies the bytes, not the request that asked for them."""
    response = client.get("/api/v1/manifest")

    assert response.headers["ETag"] == caching.compute_etag(response.content)


def test_the_etag_is_stable_across_two_identical_requests(client):
    first = client.get("/api/v1/manifest")
    second = client.get("/api/v1/manifest")

    assert first.headers["ETag"] == second.headers["ETag"]
    assert first.content == second.content


def test_the_etag_differs_when_the_content_differs(client):
    """The coverage is a projection: a filter changes what it holds."""
    hydrology = client.get("/api/v1/coverage", params={"domain": "hydrology"})
    atmosphere = client.get("/api/v1/coverage", params={"domain": "atmosphere"})

    assert hydrology.content != atmosphere.content
    assert hydrology.headers["ETag"] != atmosphere.headers["ETag"]


def test_the_same_content_shares_one_etag(client):
    """The two prefixes are the same routes: the same answer, the same tag."""
    canonical = client.get("/api/v1/manifest")
    legacy = client.get("/api/manifest")

    assert canonical.content == legacy.content
    assert canonical.headers["ETag"] == legacy.headers["ETag"]


# --------------------------------------------------------------------------
# What is not the catalogue
# --------------------------------------------------------------------------


def test_the_health_is_never_cached(client):
    """The health says whether the application is up now."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert "ETag" not in response.headers


def test_the_legacy_health_is_never_cached_either(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"


def test_a_failure_carries_no_etag_and_is_never_cached(client):
    """A failure says what went wrong when it was asked for."""
    response = client.get("/api/v1/missions/NOPE")

    assert response.status_code == 404
    assert "ETag" not in response.headers
    assert response.headers.get("Cache-Control") == "no-store"


def test_a_refused_request_is_never_cached(client):
    response = client.get("/api/v1/missions", params={"min_status": "validated"})

    assert response.status_code == 422
    assert "ETag" not in response.headers
    assert response.headers.get("Cache-Control") == "no-store"


# --------------------------------------------------------------------------
# The compiled application
# --------------------------------------------------------------------------


@requires_frontend
def test_the_application_is_not_cached_like_the_catalogue(client, caching):
    """The HTML names the files that carry the application: it is revalidated."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") != caching.CATALOGUE_CACHE_CONTROL
    assert "max-age" not in response.headers.get("Cache-Control", "")
    assert response.headers.get("ETag") != caching.compute_etag(response.content)


@requires_frontend
def test_a_page_of_the_application_is_revalidated(client):
    response = client.get("/country/FR")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-cache"


@requires_frontend
def test_a_hashed_asset_is_kept_for_a_long_time(client, hashed_asset):
    """The name of an asset carries a hash of its content: it never changes."""
    response = client.get(hashed_asset)

    assert response.status_code == 200
    cache_control = response.headers.get("Cache-Control", "")
    assert "public" in cache_control, cache_control
    assert "immutable" in cache_control, cache_control
    assert "max-age=31536000" in cache_control, cache_control


# --------------------------------------------------------------------------
# The legacy prefix
# --------------------------------------------------------------------------


def test_the_legacy_prefix_keeps_its_headers_and_gains_the_cache(client):
    """The legacy prefix answers the same, and says it is deprecated."""
    response = client.get("/api/manifest")

    assert response.status_code == 200
    assert response.headers.get("Deprecation") == "true"
    assert "/api/v1/manifest" in response.headers.get("Link", "")
    assert response.headers.get("ETag"), "the legacy prefix is cached like the canonical one"
    assert "public" in response.headers.get("Cache-Control", "")


def test_the_legacy_prefix_answers_not_modified_too(client):
    first = client.get("/api/manifest")
    etag = first.headers["ETag"]

    second = client.get("/api/manifest", headers={"If-None-Match": etag})

    assert second.status_code == 304
    assert second.content == b""
    assert second.headers.get("ETag") == etag
    assert second.headers.get("Deprecation") == "true"
    assert "/api/v1/manifest" in second.headers.get("Link", "")


# --------------------------------------------------------------------------
# The helpers
# --------------------------------------------------------------------------


def test_the_etag_is_a_hash_of_the_bytes(caching):
    """A hash, not the built-in one: it must survive the process."""
    assert caching.compute_etag(b"torne") == '"' + hashlib.sha256(b"torne").hexdigest() + '"'
    assert caching.compute_etag(b"torne") == caching.compute_etag(b"torne")
    assert caching.compute_etag(b"torne") != caching.compute_etag(b"torne ")


def test_a_weak_tag_matches_a_strong_one(caching):
    """The comparison is the weak one of RFC 9110."""
    assert caching.if_none_match_matches('W/"abc"', '"abc"')
    assert caching.if_none_match_matches('"abc"', 'W/"abc"')
    assert not caching.if_none_match_matches('"abc"', '"abd"')


def test_a_list_of_tags_matches_as_soon_as_one_does(caching):
    assert caching.if_none_match_matches('"x", "abc", "y"', '"abc"')
    assert not caching.if_none_match_matches('"x", "y"', '"abc"')


def test_the_star_matches_any_representation(caching):
    assert caching.if_none_match_matches("*", '"abc"')


def test_an_absent_header_matches_nothing(caching):
    assert not caching.if_none_match_matches("", '"abc"')
