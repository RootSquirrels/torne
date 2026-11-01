"""Copernicus Data Space adapter — the STAC catalogue of surface products.

This adapter **asks questions** of the Copernicus Data Space STAC catalogue and
knows nothing of the domain: it knows neither Sentinel, nor the soil moisture
index, nor the surface of a basin. It builds a URL, asks a spatial and temporal
question, says how the catalogue is walked, and returns the next question or
`None`.

It complements the OData adapter (`copernicus.py`), which queries the catalogue
**of products**: this one queries the catalogue **of surface observations**
(STAC). The two do not overlap — the STAC catalogue exposes 428 collections,
including the Copernicus Land Monitoring Service surface products, absent from
the OData catalogue.

What was **verified on the network** (2026-11-01, development machine):

- the access point is a **STAC 1.1.0** API (OGC API - Features): search is
  `GET /v1/search`, with parameters `collections`, `bbox`, `intersects`,
  `datetime` and `limit`;
- `datetime` requires a **full RFC 3339** form: `2023-01-01/2023-12-31` is
  refused by the server ("Invalid RFC3339 datetime"),
  `2023-01-01T00:00:00Z/2023-12-31T23:59:59Z` is accepted. The adapter
  therefore builds the interval itself, in the form the server accepts;
- the spatial filter **is applied**: an extent that meets no product returns
  nothing, where the OData catalogue returned its whole content regardless.
  The predicate nevertheless **verifies** it on what was received, without
  trusting the URL;
- the temporal filter **is applied** in the same way;
- a non-existent collection is refused by the server (`HTTP 400`): that is an
  acquisition failure, not a non-conformity;
- pagination is carried by a `next` relation link, whose URL is **absolute** and
  carries a `token`: the adapter decodes it and carries its parameters into the
  next request, so that parameters are always carried by the request and never
  concatenated by hand;
- **the disappearance of the `next` link is the only declaration of
  exhaustion**: the response carries no `numberMatched`, so the repository does
  not pretend to know in advance how many products it will return.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from ...contracts.observation import PublicationClass, Source
from ...contracts.spatial import BoundingBox
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

URL_SEARCH = "https://stac.dataspace.copernicus.eu/v1/search"
"""Search access point of the Copernicus Data Space STAC catalogue."""

SOURCE_ID = "copernicus.dataspace.stac"
"""Source identifier, stable and unambiguous."""


def _rfc3339(instant: datetime) -> str:
    """The instant in the RFC 3339 form, in UTC, that the server requires.

    The catalogue refuses a bare date ("Invalid RFC3339 datetime"): the
    date-time separator is mandatory, and the time must be complete. The adapter
    therefore builds the string itself rather than letting the caller guess it.
    """
    return instant.strftime("%Y-%m-%dT%H:%M:%SZ")


class CopernicusStacAdapter:
    """The questions to ask the Copernicus Data Space STAC catalogue.

    The question is **spatial and temporal**: which surface observations, of
    which collections, over which extent and which window.

    `bbox` and `geometry` are not equivalent: the first requests an
    **envelope**, the second a **polygon**. The server applies the polygon more
    finely than the envelope — that is what STAC does — and the predicate then
    compares what it received to the **envelope** of the requested polygon. That
    comparison is therefore an **approximation**: it cannot detect an item that
    touches the polygon only at a corner. It is documented in the predicate, and
    the gap is without consequence for a surface product whose grid is much
    finer than the requested envelope.
    """

    def __init__(
        self,
        *,
        collections: Sequence[str],
        start: datetime,
        end: datetime,
        page_size: int,
        max_pages: int,
        bbox: BoundingBox | None = None,
        geometry: Mapping[str, object] | None = None,
    ) -> None:
        """Set the question to ask.

        `collections`, `page_size` and `max_pages` have no default: a missing
        collection would bring back the whole catalogue, and page size and depth
        are choices, not conventions. At least one of the two extents — `bbox`
        or `geometry` — is required: a search without an extent would not be a
        search over a basin.
        """
        if not isinstance(collections, Sequence) or isinstance(collections, (str, bytes)):
            raise TypeError("collections must be a sequence of strings")
        cleaned = [c.strip() for c in collections if isinstance(c, str) and c.strip()]
        if not cleaned:
            raise ValueError("collections is required and non-empty")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("collections contains no duplicate")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if bbox is None and geometry is None:
            raise ValueError("an extent is required: bbox or geometry")
        if bbox is not None and not isinstance(bbox, BoundingBox):
            raise TypeError("bbox must be a BoundingBox")
        if geometry is not None and not isinstance(geometry, Mapping):
            raise TypeError("geometry must be a GeoJSON object")

        self._collections = tuple(cleaned)
        self._start = start
        self._end = end
        self._page_size = page_size
        self._max_pages = max_pages
        self._bbox = bbox
        self._geometry = dict(geometry) if geometry is not None else None

    @property
    def collections(self) -> tuple[str, ...]:
        """The requested collections, in request order."""
        return self._collections

    @property
    def source(self) -> Source:
        """The source queried: its origin, and its terms of use.

        The **publication class** is `P` — timestamped publication — and the
        class is **established by execution**, not assumed: every catalogue item
        carries its own `published` field, distinct from `datetime` (validity),
        `created` and `updated` (life cycle of the entry). That is what allows
        `KNOWN_AT` to be set without assumption (INV-10, §3.11).

        It nevertheless carries a caveat, about the **root** of the class rather
        than the items: what the catalogue timestamps is its entry. The
        satellite file itself is served by the same ecosystem, with its own
        delay (`product:timeliness`). The caveat is written here so that nobody
        infers that the publication of a pixel is timestamped at its item's
        instant.
        """
        return Source(
            source_id=SOURCE_ID,
            producer="European Space Agency — Copernicus Data Space Ecosystem",
            dataset="STAC catalogue of surface collections",
            access_point=URL_SEARCH,
            license=(
                "Free and anonymous access for browsing the catalogue; downloading "
                "products requires OIDC authentication specific to each asset"
            ),
            revision_policy=(
                "Each item carries its publication, creation and modification instants "
                "(published, created, updated); the catalogue serves the current "
                "version and does not keep previous versions"
            ),
            unit=None,
            timezone="UTC",
            quality_status=None,
            publication_class=PublicationClass.TIMESTAMPED,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """This source **declares** the exhaustion of its walk.

        The catalogue itself indicates the next page through a `next` relation
        link: when the link disappears, it says it has nothing more to give. A
        200 response here therefore means "the walk is finished", not "I
        returned everything I had": it is a declaration, and the socle can
        record it as such.
        """
        return True

    def initial_request(self) -> AcquisitionRequest:
        """The first question: the first page of the search."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=URL_SEARCH,
            method="GET",
            params=self._query_params(),
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="copernicus:stac:search",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """The next question, or `None` when there is none.

        The catalogue itself indicates the next page through the `next` relation
        link. There is none left when it gives no link.

        The page **budget** is not carried by this adapter: the socle stops the
        walk and records a `partial` acquisition — not a complete one. An adapter
        that stopped itself could no longer tell "the source is exhausted" from
        "the walk was truncated".
        """
        following = self._read_next_link(response)
        if following is None:
            return None

        url, params = _split_url(following)
        if url != URL_SEARCH:
            raise ValueError(f"the next link points elsewhere than the access point: {url}")
        return AcquisitionRequest(
            source_id=request.source_id,
            url=url,
            method="GET",
            params=params,
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label=request.label,
        )

    def _query_params(self) -> dict[str, str]:
        """The query parameters, carried by the request and nothing else."""
        params: dict[str, str] = {
            "collections": ",".join(self._collections),
            "datetime": f"{_rfc3339(self._start)}/{_rfc3339(self._end)}",
            "limit": str(self._page_size),
        }
        if self._bbox is not None:
            params["bbox"] = ",".join(str(v) for v in self._bbox.as_tuple())
        if self._geometry is not None:
            params["intersects"] = json.dumps(self._geometry, separators=(",", ":"))
        return params

    def _read_next_link(self, response: HttpResponse) -> str | None:
        """The next-page link given by the catalogue, if any."""
        payload = self._read_payload(response)
        links = payload.get("links")
        if links is None:
            return None
        if not isinstance(links, list):
            raise ValueError("unexpected STAC response: 'links' is not a list")
        for link in links:
            if not isinstance(link, Mapping):
                raise ValueError("unexpected STAC response: a link is not an object")
            if link.get("rel") == "next":
                target = link.get("href")
                if not isinstance(target, str) or not target.strip():
                    raise ValueError("unexpected STAC response: the 'next' link has no URL")
                return target
        return None

    def _read_payload(self, response: HttpResponse) -> dict[str, object]:
        """The response payload, checked to be a JSON object."""
        try:
            payload = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"unreadable STAC response: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError("unexpected STAC response: the root is not a JSON object")
        return payload

    def _read_items(self, response: HttpResponse) -> list[object]:
        """The items of the page."""
        payload = self._read_payload(response)
        items = payload.get("features")
        if items is None:
            raise ValueError("unexpected STAC response: the 'features' field is missing")
        if not isinstance(items, list):
            raise ValueError("unexpected STAC response: 'features' is not a list")
        return items

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Are the items received the ones that were requested?

        Predicate specific to this source. It confronts what the request asked
        for with what the response returned, **on three criteria**: collection,
        footprint, time window.

        It does not trust the URL: a filter applied by the server shows in what
        it returned, not in what it was asked. A criterion that **cannot be
        verified** — an item without `bbox`, a response without usable
        `features` — gives an abstention, never conformity by default.

        An **empty** page is a special case, treated as such: zero items is a
        **complete** answer to "which items of this collection, over this
        extent, in this window?" — the answer is "none". The criteria are
        therefore verified and satisfied, and the reason says there was nothing
        to verify. That is what allows establishing a useful negative fact: "the
        basin has no Sentinel-2 coverage before 2015".
        """
        items = self._read_items(response)
        criteria: dict[str, CritereConformite] = {
            "collections": self._criterion_collections(items),
            "footprint": self._criterion_footprint(items),
            "window": self._criterion_window(items),
        }
        return verdict_from_criteria(criteria)

    def _criterion_collections(self, items: list[object]) -> CritereConformite:
        """The collection criterion, from the items received."""
        requested = f"collections={','.join(self._collections)}"
        if not items:
            return CritereConformite(
                demande=requested,
                verifie=True,
                recu="no item received: the response is empty",
                conforme=True,
            )

        expected = set(self._collections)
        seen: list[str] = []
        unreadable = 0
        unexpected: list[str] = []
        for item in items:
            if not isinstance(item, Mapping):
                unreadable += 1
                continue
            collection = item.get("collection")
            if not isinstance(collection, str) or not collection:
                unreadable += 1
                continue
            if collection not in expected:
                unexpected.append(collection)
            if collection not in seen:
                seen.append(collection)

        received = ", ".join(seen[:3])
        if len(seen) > 3:
            received = f"{received} (+{len(seen) - 3} others)"
        if unexpected:
            return CritereConformite(
                demande=requested,
                verifie=True,
                recu=f"{received}; collection(s) not requested: {', '.join(unexpected[:3])}",
                conforme=False,
            )
        if unreadable:
            # Same rule as everywhere else: an item whose collection cannot be
            # read makes the criterion **unverifiable**, not violated.
            return CritereConformite(
                demande=requested,
                verifie=False,
                recu=f"{received} (+{unreadable} without 'collection')",
            )
        return CritereConformite(demande=requested, verifie=True, recu=received, conforme=True)

    def _criterion_footprint(self, items: list[object]) -> CritereConformite:
        """The footprint criterion, from the items received.

        **Documented approximation**: the comparison is made on the items'
        **bounding boxes**, not on their polygons. An item whose polygon touches
        the requested extent only at a corner may be counted as overlapping. The
        gap has no effect here: the surface products compared have a grid much
        finer than the requested envelope, and the server has already filtered on
        the exact geometry when a polygon was requested.
        """
        envelope = self._requested_envelope()
        requested = (
            f"footprint={envelope.as_tuple()}"
            if self._bbox is not None
            else "footprint=requested polygon (compared to its bounding box)"
        )
        if not items:
            return CritereConformite(
                demande=requested,
                verifie=True,
                recu="no item received: the response is empty",
                conforme=True,
            )

        outside: list[str] = []
        unreadable = 0
        for item in items:
            if not isinstance(item, Mapping):
                unreadable += 1
                continue
            box = item.get("bbox")
            if not isinstance(box, (list, tuple)) or len(box) < 4:
                unreadable += 1
                continue
            try:
                item_bbox = BoundingBox.from_sequence([float(v) for v in box[:4]])
            except (TypeError, ValueError):
                unreadable += 1
                continue
            if not item_bbox.intersects(envelope):
                outside.append(str(item.get("id", "?")))

        received = f"{len(items)} item(s) received"
        if outside:
            received = f"{received}; {len(outside)} outside the footprint: {', '.join(outside[:3])}"
            return CritereConformite(demande=requested, verifie=True, recu=received, conforme=False)
        if unreadable:
            # A missing field is an **abstention**, never a violation: the source
            # did not break the request, nobody can say it did.
            return CritereConformite(
                demande=requested,
                verifie=False,
                recu=f"{received}; {unreadable} without a readable 'bbox'",
            )
        return CritereConformite(demande=requested, verifie=True, recu=received, conforme=True)

    def _criterion_window(self, items: list[object]) -> CritereConformite:
        """The time-window criterion, from the items received.

        An item's coverage is the interval it **covers**, not the instant it
        carries: a product whose validity starts before the requested window and
        ends inside it overlaps the window, and is concerned by the question.
        """
        requested = f"datetime={_rfc3339(self._start)}/{_rfc3339(self._end)}"
        if not items:
            return CritereConformite(
                demande=requested,
                verifie=True,
                recu="no item received: the response is empty",
                conforme=True,
            )

        outside: list[str] = []
        unreadable = 0
        for item in items:
            if not isinstance(item, Mapping):
                unreadable += 1
                continue
            start, end = _temporal_coverage(item)
            if start is None:
                unreadable += 1
                continue
            if end < self._start or start > self._end:
                outside.append(str(item.get("id", "?")))

        received = f"{len(items)} item(s) received"
        if outside:
            received = f"{received}; {len(outside)} outside the window: {', '.join(outside[:3])}"
            return CritereConformite(demande=requested, verifie=True, recu=received, conforme=False)
        if unreadable:
            # An item whose instant cannot be read does not violate the window:
            # it makes the window **unverifiable** for that item.
            return CritereConformite(
                demande=requested,
                verifie=False,
                recu=f"{received}; {unreadable} without a readable instant",
            )
        return CritereConformite(demande=requested, verifie=True, recu=received, conforme=True)

    def _requested_envelope(self) -> BoundingBox:
        """The envelope of the requested extent.

        When a polygon was requested, the envelope is **derived from it**: that
        is the approximation the predicate assumes, named here so it is not
        mistaken for a requested extent.
        """
        if self._bbox is not None:
            return self._bbox
        geometry = self._geometry or {}
        points = geometry.get("coordinates")
        if geometry.get("type") != "Polygon" or not isinstance(points, list) or not points:
            raise ValueError("unreadable requested geometry: a polygon is expected")
        vertices = [p for p in points[0] if isinstance(p, (list, tuple)) and len(p) >= 2]
        if len(vertices) < 3:
            raise ValueError("unreadable requested geometry: fewer than three vertices")
        xs = [float(p[0]) for p in vertices]
        ys = [float(p[1]) for p in vertices]
        return BoundingBox(west=min(xs), south=min(ys), east=max(xs), north=max(ys))


def _utc_instant(raw: object) -> datetime | None:
    """The ISO 8601/RFC 3339 instant published by the catalogue, or `None`.

    The catalogue writes its instants in RFC 3339, with a trailing `Z`. The `Z`
    is replaced by its explicit offset before parsing, as the Hub'EAU adapter
    does: the time zone must never be **assumed**, and its absence must stay
    readable as an absence.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        instant = datetime.fromisoformat(text)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return None
    return instant.astimezone(UTC)


def _temporal_coverage(item: Mapping[str, object]) -> tuple[datetime | None, datetime | None]:
    """The temporal coverage interval of a STAC item.

    STAC gives `datetime` for an instantaneous item, and `start_datetime` /
    `end_datetime` for an item covering a period. Both forms are read here. The
    order of the instants is normalised: an item whose `end_datetime` precedes
    its `start_datetime` is returned in order, and the inconsistency stays
    visible in the raw data.
    """
    properties = item.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}

    def _read(source: Mapping[str, object], key: str) -> datetime | None:
        value = source.get(key)
        if not isinstance(value, str) or not value.strip():
            return None
        return _utc_instant(value)

    start = _read(properties, "start_datetime") or _read(item, "start_datetime")
    end = _read(properties, "end_datetime") or _read(item, "end_datetime")
    instant = _read(properties, "datetime") or _read(item, "datetime")
    if instant is None:
        # No validity instant at all. `published` is deliberately **not** used
        # as a fallback: the publication instant is not the moment the product
        # describes, and borrowing it would place an item in a window it never
        # covered.
        return None, None
    if start is None:
        start = instant
    if end is None:
        end = instant
    if end < start:
        start, end = end, start
    return start, end


def _split_url(url: str) -> tuple[str, dict[str, str]]:
    """Split an absolute URL into base and parameters.

    The provider's link is rewritten as base + parameters: parameters stay
    carried by the request, never concatenated by hand into the URL.
    """
    parts = urlsplit(url)
    base = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    return base, params


__all__ = ["SOURCE_ID", "URL_SEARCH", "CopernicusStacAdapter"]
