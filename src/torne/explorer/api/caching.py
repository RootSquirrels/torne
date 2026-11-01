"""The caching layer of the read-only catalogue.

The catalogue is a projection of the repository: it is built when the
application starts, held in memory, and read from there. It changes when the
repository changes — that is, when a new version is deployed — and not
otherwise. Two consequences shape this module:

- a client that already holds an answer can be told so, and receives it again
  as a `304 Not Modified` with no body at all;
- a client may reuse an answer for a short while without asking.

The rules live here and nowhere else. The routers that serve the catalogue
declare that they serve it, and this module decides what a client may keep.
The health route is not part of the catalogue and is never cached; the
compiled application has its own rules, in `static.py`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute, APIRouter

__all__ = [
    "CATALOGUE_CACHE_CONTROL",
    "CATALOGUE_MAX_AGE",
    "NO_STORE",
    "CatalogueRoute",
    "CatalogueRouter",
    "apply_catalogue_cache",
    "compute_etag",
    "if_none_match_matches",
]

CATALOGUE_MAX_AGE = 300
"""How long a client may reuse a catalogue answer without asking again.

The answer to a given URL is a deterministic function of the repository
state: the manifest is built once, at startup, and read from memory
afterwards. It therefore only changes when a new version is deployed. The
window of five minutes is not a guess about the deployment rhythm: it bounds
the only staleness a client can suffer, namely the delay between a
deployment and the moment a newly established mission becomes visible. Five
minutes is short enough for that delay to be imperceptible to a reader, and
long enough for a browsing session — which asks for the manifest again on
every page load — to ask for it once per window instead of once per
navigation. A stale catalogue is never wrong: it says what had been
established a few minutes earlier.
"""

CATALOGUE_CACHE_CONTROL = f"public, max-age={CATALOGUE_MAX_AGE}"
"""The directive that tells a client how long it may keep a catalogue answer.

`public` because the answer is the same for every client and carries nothing
private; the catalogue is a public document.
"""

NO_STORE = "no-store"
"""The directive for an answer that must never be reused by anybody."""


def compute_etag(body: bytes) -> str:
    """The strong ETag of a body.

    The tag is the hash of the bytes and nothing else: it does not depend on
    the request, on the time, or on the process, so the same content always
    gives the same tag, and a different content always gives a different one.
    """
    return '"' + hashlib.sha256(body).hexdigest() + '"'


def if_none_match_matches(header: str, etag: str) -> bool:
    """Whether an `If-None-Match` header matches an ETag.

    The comparison is the weak one of RFC 9110: `W/"x"` matches `"x"`, and a
    list of tags matches as soon as one of them does. `*` matches any
    representation the server holds.
    """
    target = _opaque_tag(etag)
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if _opaque_tag(candidate) == target:
            return True
    return False


def _opaque_tag(tag: str) -> str:
    """The opaque part of a tag, without the weakness marker."""
    tag = tag.strip()
    if tag[:2] in {"W/", "w/"}:
        tag = tag[2:]
    return tag


def apply_catalogue_cache(request: Request, response: Response) -> Response:
    """Give a catalogue answer its ETag, and its cache directive.

    When the client already holds the answer — it repeats the ETag it was
    given — the answer is not sent again: a `304` carries the ETag and no
    body, which is what the client asked for.
    """
    body = getattr(response, "body", None)
    if response.status_code != 200 or not isinstance(body, bytes):
        # A failure, or a body that is not a buffer, is not a catalogue
        # answer: it is not given a tag, and it is not reused.
        return response
    etag = compute_etag(body)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CATALOGUE_CACHE_CONTROL
    if if_none_match_matches(request.headers.get("if-none-match", ""), etag):
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": CATALOGUE_CACHE_CONTROL},
        )
    return response


class CatalogueRoute(APIRoute):
    """A route whose answer is a catalogue answer, and may be reused."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            response = await original(request)
            return apply_catalogue_cache(request, response)

        return handler


class CatalogueRouter(APIRouter):
    """A router whose routes all serve the catalogue, and may be reused."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("route_class", CatalogueRoute)
        super().__init__(*args, **kwargs)
