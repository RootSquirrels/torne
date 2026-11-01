"""Hub'Eau v2 — the hydrometric feed of one quantity, for the whole network.

This adapter asks the question this access point is **able** to answer:

    *every observation of this quantity, over the whole network.*

It deliberately asks for **no station and no time window**. What was measured
on the network on 2026-11-01, on this instance:

- `grandeur_hydro` **is** applied: the rows of a `Q` page all carry `Q`, and
  the rows of an `H` page all carry `H`;
- `code_station`, `code_cours_eau`, `date_debut` and `date_fin` are **echoed
  and ignored**. The proof is not the reported `count` — which is attached to
  the collection and is the same for an existing station, a non-existent one
  and a two-year window — it is the **rows themselves**: a request carrying
  `code_station=O919001001` returns rows of `A402061001`, `A405062001` and
  `P846251001`, and a request carrying a two-year window returns the most
  recent instants of the day;
- every alternative spelling of those filters (`station`, `codeStation`,
  `station_code`, `codes_station`, `date_obs`, `date_obs_start`, `debut`,
  `start_date`) is ignored in exactly the same way;
- `page` and `index` are accepted and ignored: the page requested with
  `page=2` is the page returned with `page=1`, and every `index` returns the
  first page;
- the only working pagination is the **`next` link**, which carries a seek
  key. The key is a signed framing around the identity of the last row
  (`code_site`, `code_station`, `grandeur_hydro`, `date_obs`); a forged key
  is refused with a 500, so the collection can only be walked from its
  beginning;
- the collection is ordered by **descending observation instant**: the first
  page holds the most recent instants, and the stations are interleaved
  within each five-minute slice;
- `size` is honoured up to 10 000 (50 000 is refused with a 400), and the
  instance throttles: it answers 503 when too much is asked too quickly.

A question the source does not answer is not asked here. Asking for a station
would guarantee a non-conformity — and the conformity gate is right to close
on it. The selection of a station inside the acquired feed is therefore a
**transformation**, declared and verified by the layer that performs it
(`torne.hydrology.hubeau`), never a filter the provider is trusted to apply.

This adapter is **not** the station-scoped one (`torne.acquisition.adapters
.hubeau`): the two ask the source two different questions, and the source
answers only one of them.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

URL_OBSERVATIONS_TR = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr"
"""The Hub'Eau v2 access point of the hydrometric observations."""

SOURCE_ID = "hubeau.hydrometrie.observations_tr"
"""The identifier of the source: stable and unambiguous."""

GRANDEURS = ("H", "Q", "M", "Z")
"""The quantities this access point publishes.

Only the height (`H`) and the discharge (`Q`) are used by TORNE; the others
are listed because the source publishes them and an unknown quantity is
refused rather than read as one of these.
"""


class HubeauFeedAdapter:
    """The questions to ask about the network-wide feed of one quantity.

    `page_size` and `max_pages` have no default value: the size of a page and
    the depth of the walk are choices, not conventions. The budget belongs to
    the socle, which stops the walk and knows that it truncated it.
    """

    def __init__(
        self,
        *,
        grandeur_hydro: str,
        page_size: int,
        max_pages: int,
    ) -> None:
        """Fixes the question to ask.

        `grandeur_hydro` is the quantity to ask for: it is the only filter
        this instance applies, and it is the one the conformity check can
        verify on the rows that come back.
        """
        if not isinstance(grandeur_hydro, str) or not grandeur_hydro.strip():
            raise ValueError("grandeur_hydro is required and not empty")
        if grandeur_hydro not in GRANDEURS:
            raise ValueError(f"unknown quantity: {grandeur_hydro!r}")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        self._grandeur_hydro = grandeur_hydro
        self._page_size = page_size
        self._max_pages = max_pages

    @property
    def source(self) -> Source:
        """The source queried: the origin, and the conditions of its use."""
        return Source(
            source_id=SOURCE_ID,
            producer="Eaufrance (Hub'EAU)",
            dataset="Hydrometric observations (water height and discharge)",
            access_point=URL_OBSERVATIONS_TR,
            license="Open Licence 2.0 (Etalab)",
            revision_policy=(
                "Each observation carries its own measurement status, method and "
                "qualification (libelle_statut, libelle_methode_obs, "
                "libelle_qualification_obs)"
            ),
            unit=None,
            timezone="UTC",
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """This source **declares** the exhaustion of its walk.

        The pagination is carried by the `next` link: when it disappears, the
        provider says there is nothing left to take. The socle can record
        that as a declaration, and can tell it apart from a walk stopped by
        our own page budget.
        """
        return True

    def initial_request(self) -> AcquisitionRequest:
        """The first question: the first page, with the quantity chosen."""
        return AcquisitionRequest(
            source_id=SOURCE_ID,
            url=URL_OBSERVATIONS_TR,
            method="GET",
            params={
                "format": "json",
                "size": str(self._page_size),
                "grandeur_hydro": self._grandeur_hydro,
            },
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="hubeau:observations_tr:feed",
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """The next question, or `None` when there is none.

        The pagination of this source is carried by the `next` link: it is
        followed as the provider gave it. The walk is exhausted when the page
        is empty, or when the provider gives no next link.
        """
        data, following = self._read_page(response)
        if not data:
            return None
        if following is None:
            return None

        url, params = _split_url(following)
        if url != URL_OBSERVATIONS_TR:
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

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Do the received rows carry the quantity that was asked for?

        This is the one criterion this source can satisfy, and it is checked
        on the **rows that came back**, not on what the request asked for. A
        page that carries another quantity is a page that does not answer the
        question.

        No criterion is invented for what the source does not expose: the
        station and the window are not asked for, and a criterion nobody asked
        for is not a criterion.
        """
        rows, _ = self._read_page(response)
        criteria: dict[str, CritereConformite] = {}

        if not rows:
            criteria["grandeur_hydro"] = CritereConformite(
                demande=self._grandeur_hydro,
                verifie=False,
                recu="(no row to verify)",
            )
        else:
            received: list[str] = []
            without = 0
            for row in rows:
                if not isinstance(row, dict):
                    without += 1
                    continue
                value = row.get("grandeur_hydro")
                if value is None:
                    without += 1
                    continue
                text = str(value)
                if text not in received:
                    received.append(text)
            if not received:
                criteria["grandeur_hydro"] = CritereConformite(
                    demande=self._grandeur_hydro,
                    verifie=False,
                    recu=f"{without} row(s) without « grandeur_hydro »",
                )
            else:
                received_text = ", ".join(received)
                if without:
                    received_text = f"{received_text} (+{without} without « grandeur_hydro »)"
                criteria["grandeur_hydro"] = CritereConformite(
                    demande=self._grandeur_hydro,
                    verifie=True,
                    recu=received_text,
                    conforme=received == [self._grandeur_hydro] and not without,
                )

        # The truth table is the socle's: the adapter collects the criteria,
        # it does not decide the verdict.
        return verdict_from_criteria(criteria)

    def _read_page(self, response: HttpResponse) -> tuple[list[Any], str | None]:
        """The observations of the page, and the link to the next page."""
        payload = _load_json(response, "Hub'EAU")
        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("unexpected Hub'EAU response: the « data » field is not a list")
        following = payload.get("next")
        if following is not None and not isinstance(following, str):
            raise ValueError("unexpected Hub'EAU response: the « next » field is not a URL")
        return data, following


def _load_json(response: HttpResponse, name: str) -> dict[str, Any]:
    """The body of the response, read as a JSON object."""
    try:
        payload = json.loads(response.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"unreadable {name} response: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected {name} response: the root is not a JSON object")
    return payload


def _split_url(url: str) -> tuple[str, dict[str, str]]:
    """Splits an absolute URL into a base and its parameters.

    The provider's link is rewritten as base + parameters: the parameters
    stay carried by the request, never concatenated by hand into the URL.
    """
    parts = urlsplit(url)
    base = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    return base, params


__all__ = ["GRANDEURS", "SOURCE_ID", "URL_OBSERVATIONS_TR", "HubeauFeedAdapter"]
