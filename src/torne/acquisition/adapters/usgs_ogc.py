"""The USGS OGC adapter — "Water Data for the Nation", the OGC API Features endpoint.

This adapter asks questions of the USGS **Water Data for the Nation** API and
knows nothing of the domain: it does not know what discharge is, what a flood
stage is, or what a provisional value means. It builds a URL, follows the
server's own pagination link, and says whether what came back answers the
question that was asked.

It replaces `usgs.py`, the adapter aimed at
`waterservices.usgs.gov/nwis/iv/`. That endpoint is on its way out: the USGS
announced the decommissioning of the legacy WaterServices APIs, with the
package migration window closing in November 2026 and the services going away
in February 2027. The OGC API is the replacement target.

What was **verified on the network** (2026-11-01, development machine):

- the base is `https://api.waterdata.usgs.gov/ogcapi/v1`, and an item
  collection lives at `/collections/{collection}/items`;
- the join key of every data collection is `monitoring_location_id`, formed
  as `<agency_code>-<number>` — `USGS-05587450`, never `05587450`;
- pagination is by **cursor**: the response carries an absolute `next` link
  that already carries every filter of the original query. Following it
  verbatim is the only safe thing to do: the cursor encodes the last item
  rendered, and rebuilding the query by hand is how a traversal silently
  changes its question;
- **the end of the traversal is the absence of the `next` link**. The source
  therefore *declares* its exhaustion;
- `limit` is bounded by 50000 (default 10). A full year of 15-minute values
  for a station comes back in a single response of about 23 MB;
- without an explicit `datetime` window the server renders roughly **one
  year** of continuous values. The window is never left implicit;
- `value` is always a **string**, never a JSON number; `daily.time` is a bare
  date (`2024-01-03`) while `continuous.time` is an ISO 8601 instant with an
  explicit offset;
- items are **not** globally sorted by time: `continuous` is grouped by time
  series, `daily` comes in an arbitrary order. Sorting is the reader's job;
- any **undeclared query parameter** is rejected with a 400. Parameters are
  therefore built as a mapping, never concatenated by hand;
- the anonymous quota is 1000 requests per hour, and the rate-limit headers
  only appear on the 429 — never on a 200.

The API key is optional, but it has its own quota bucket: an exhausted
anonymous bucket still answers when a key is supplied. The key is therefore
carried by `credential_ref` — it never enters the recorded request, and the
socle resolves it at the last moment.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from ...contracts.observation import Source
from ..contracts import (
    AcquisitionRequest,
    CritereConformite,
    HttpResponse,
    PaginationStrategy,
    VerdictConformite,
    verdict_from_criteria,
)

BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v1"
"""Base of the OGC API Features endpoint of the USGS."""

STATISTICS_URL = "https://api.waterdata.usgs.gov/statistics/v0"
"""Base of the USGS Water Data Statistics API (v0, beta).

The site statistics are **not** in the OGC API: the four plausible routes
were all answered with a 404 on 2026-11-01. They live in this separate
service, which is where the independent reference comes from.
"""

CREDENTIAL_REF = "usgs:api_key"
"""Reference of the credential: the USGS API key, sent as `X-Api-Key`."""

LICENSE = "Public domain (U.S. Geological Survey)"

_DATASETS = {
    "continuous": "Water Data for the Nation — continuous values",
    "daily": "Water Data for the Nation — daily values",
    "time-series-metadata": "Water Data for the Nation — time series metadata",
    "monitoring-locations": "Water Data for the Nation — monitoring locations",
    "peaks": "Water Data for the Nation — annual peaks",
}


class UsgsOgcItemsAdapter:
    """The questions to ask of an OGC API Features collection of the USGS.

    The question is always the same shape: *the values of this monitoring
    location, for these parameters, over this window*. The adapter does not
    interpret what comes back; it only says whether it answers the question.
    """

    def __init__(
        self,
        *,
        collection: str,
        monitoring_location_id: str,
        parameter_codes: Sequence[str] = (),
        statistic_ids: Sequence[str] = (),
        datetime_range: tuple[str, str] | None = None,
        limit: int = 10_000,
        max_pages: int = 20,
        required_fields: Sequence[str] = ("time", "value", "unit_of_measure"),
        api_key_ref: str | None = CREDENTIAL_REF,
        location_param: str = "monitoring_location_id",
        location_field: str = "monitoring_location_id",
    ) -> None:
        """Fixes the question to ask.

        `monitoring_location_id` is mandatory and non-empty: a query without a
        station would bring back the whole referential.

        `datetime_range` is a pair of ISO 8601 bounds. It is never left
        implicit: without it, the server renders about one year of continuous
        values, and a silent window is a window nobody asked for.

        `required_fields` names the feature properties the reader needs to
        interpret the page. A page that does not carry them cannot be
        interpreted, and the verdict will say so.

        `location_param` and `location_field` name the station, once in the
        query and once in the answer. They differ for the referential
        itself: the `monitoring-locations` collection is queried by `id`, and
        its records carry `id` — the other collections are queried by
        `monitoring_location_id` and carry it.
        """
        if not collection or not collection.strip():
            raise ValueError("collection is mandatory and non-empty")
        if not monitoring_location_id or not monitoring_location_id.strip():
            raise ValueError("monitoring_location_id is mandatory and non-empty")
        if "-" not in monitoring_location_id:
            raise ValueError(
                "monitoring_location_id must be '<agency_code>-<number>', as in 'USGS-05587450'"
            )
        if limit < 1 or limit > 50_000:
            raise ValueError("limit is bounded by the provider: 1 to 50000")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if datetime_range is not None:
            borne_debut, borne_fin = datetime_range
            if not borne_debut or not borne_fin:
                raise ValueError("datetime_range needs both bounds")

        self._collection = collection
        self._monitoring_location_id = monitoring_location_id
        self._parameter_codes = tuple(parameter_codes)
        self._statistic_ids = tuple(statistic_ids)
        self._datetime_range = datetime_range
        self._limit = limit
        self._max_pages = max_pages
        self._required_fields = tuple(required_fields)
        self._api_key_ref = api_key_ref
        self._location_param = location_param
        self._location_field = location_field

    @property
    def source_id(self) -> str:
        """Stable identifier of the source."""
        return f"usgs.ogc.{self._collection}"

    @property
    def source(self) -> Source:
        """The source being queried: its origin, and the conditions of use."""
        return Source(
            source_id=self.source_id,
            producer="U.S. Geological Survey (USGS)",
            dataset=_DATASETS.get(
                self._collection, f"Water Data for the Nation — {self._collection}"
            ),
            access_point=f"{BASE_URL}/collections/{self._collection}/items",
            license=LICENSE,
            revision_policy=(
                "The most recent values are marked provisional by the provider and may be revised"
            ),
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """This source **declares** its exhaustion.

        The provider publishes the link to the next page while there is one,
        and drops it when there is not. The absence of the `next` link is
        therefore a statement by the provider that the collection has been
        traversed to its end — which is not the same thing as a 200 that
        happens to be short.
        """
        return True

    def initial_request(self) -> AcquisitionRequest:
        """The first question: the window, the station, the parameters."""
        params: dict[str, str] = {
            "f": "json",
            self._location_param: self._monitoring_location_id,
            "limit": str(self._limit),
        }
        if self._parameter_codes:
            params["parameter_code"] = ",".join(self._parameter_codes)
        if self._statistic_ids:
            params["statistic_id"] = ",".join(self._statistic_ids)
        if self._datetime_range is not None:
            start, end = self._datetime_range
            params["datetime"] = f"{start}/{end}"
        return AcquisitionRequest(
            source_id=self.source_id,
            url=f"{BASE_URL}/collections/{self._collection}/items",
            method="GET",
            params=params,
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label=f"usgs:ogc_{self._collection}",
            credential_ref=self._api_key_ref,
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """The next page, exactly as the provider describes it.

        The `next` link is **absolute** and already carries every filter of
        the original query. It is therefore followed verbatim: rebuilding the
        query by hand is how a traversal silently changes its question.
        """
        payload = _load_json(response, "USGS OGC")
        link = _next_link(payload)
        if link is None:
            return None
        return AcquisitionRequest(
            source_id=self.source_id,
            url=link,
            method="GET",
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label=f"usgs:ogc_{self._collection}",
            credential_ref=self._api_key_ref,
        )

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Do the records received answer the question that was asked?

        Three criteria, all carried by the response itself: the **station**,
        the **parameters**, and the **fields** the reader needs. A criterion
        that cannot be checked is not a satisfied criterion: it is recorded
        as unverifiable, and the verdict becomes an abstention.
        """
        payload = _load_json(response, "USGS OGC")
        features = _features(payload)
        criteria = self._criteria(features)
        return verdict_from_criteria(criteria)

    def _criteria(self, features: list[dict[str, Any]]) -> dict[str, CritereConformite]:
        """The criteria, read from the records that came back."""
        criteria: dict[str, CritereConformite] = {
            "monitoring_location_id": _value_criterion(
                features,
                self._location_field,
                self._monitoring_location_id,
            ),
            "required_fields": _fields_criterion(features, self._required_fields),
        }
        if self._parameter_codes:
            criteria["parameter_codes"] = _values_criterion(
                features,
                "parameter_code",
                self._parameter_codes,
            )
        return criteria


class UsgsObservationNormalsAdapter:
    """The questions to ask of the USGS Water Data Statistics API.

    This is the **independent reference**: the provider's own statistics for
    a site, computed over its period of record. It is not used to build
    anything — it is used to *check* what was built.

    The service is in beta, and it pages with `next_token` rather than a
    cursor: the envelope carries a `next` token instead of a `next` link.
    """

    def __init__(
        self,
        *,
        monitoring_location_id: str,
        parameter_codes: Sequence[str] = (),
        page_size: int = 100,
        max_pages: int = 20,
        api_key_ref: str | None = CREDENTIAL_REF,
    ) -> None:
        if not monitoring_location_id or not monitoring_location_id.strip():
            raise ValueError("monitoring_location_id is mandatory and non-empty")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        self._monitoring_location_id = monitoring_location_id
        self._parameter_codes = tuple(parameter_codes)
        self._page_size = page_size
        self._max_pages = max_pages
        self._api_key_ref = api_key_ref

    @property
    def source_id(self) -> str:
        """Stable identifier of the source."""
        return "usgs.statistics.observation_normals"

    @property
    def source(self) -> Source:
        """The source being queried: its origin, and the conditions of use."""
        return Source(
            source_id=self.source_id,
            producer="U.S. Geological Survey (USGS)",
            dataset="USGS Water Data Statistics API — observation normals",
            access_point=f"{STATISTICS_URL}/observationNormals",
            license=LICENSE,
            revision_policy=(
                "The statistics are recomputed by the provider as the period of "
                "record grows; they are a versioned product, not a frozen one"
            ),
            unit=None,
            timezone=None,
            quality_status=None,
        )

    @property
    def declares_exhaustion(self) -> bool:
        """This source declares its exhaustion: a `null` `next` ends the traversal."""
        return True

    def initial_request(self) -> AcquisitionRequest:
        """The first question: the site, and the parameters."""
        params: dict[str, str] = {
            "monitoring_location_id": self._monitoring_location_id,
            "page_size": str(self._page_size),
        }
        if self._parameter_codes:
            params["parameter_code"] = ",".join(self._parameter_codes)
        return AcquisitionRequest(
            source_id=self.source_id,
            url=f"{STATISTICS_URL}/observationNormals",
            method="GET",
            params=params,
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="usgs:statistics_observation_normals",
            credential_ref=self._api_key_ref,
        )

    def next_request(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> AcquisitionRequest | None:
        """The next page, from the `next` token of the envelope."""
        payload = _load_json(response, "USGS statistics")
        jeton = payload.get("next")
        if not jeton:
            return None
        params = dict(request.params)
        params["next_token"] = str(jeton)
        return AcquisitionRequest(
            source_id=self.source_id,
            url=f"{STATISTICS_URL}/observationNormals",
            method="GET",
            params=params,
            pagination=PaginationStrategy.CURSOR,
            max_pages=self._max_pages,
            label="usgs:statistics_observation_normals",
            credential_ref=self._api_key_ref,
        )

    def verdict_conformite(
        self,
        request: AcquisitionRequest,
        response: HttpResponse,
    ) -> VerdictConformite:
        """Do the statistics received answer the question that was asked?

        The station is read on the feature, the parameters on the `data`
        blocks it carries — the shape of this service is not the shape of the
        OGC one, and the criterion is read where the provider puts it.
        """
        payload = _load_json(response, "USGS statistics")
        features = _features(payload)
        criteria: dict[str, CritereConformite] = {
            "monitoring_location_id": _value_criterion(
                features,
                "monitoring_location_id",
                self._monitoring_location_id,
            ),
            "required_fields": _fields_criterion(features, ("data",)),
        }
        if self._parameter_codes:
            criteria["parameter_codes"] = _block_values_criterion(
                features,
                "parameter_code",
                self._parameter_codes,
            )
        return verdict_from_criteria(criteria)


# --------------------------------------------------------------------------
# Reading the response
# --------------------------------------------------------------------------


def _load_json(response: HttpResponse, name: str) -> dict[str, Any]:
    """The body of the response, read as a JSON object."""
    try:
        payload = json.loads(response.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise ValueError(f"unreadable {name} response: {erreur}") from erreur
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected {name} response: the root is not a JSON object")
    return payload


def _features(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """The features of the envelope, as a list of property mappings."""
    features = payload.get("features")
    if features is None:
        features = []
    if not isinstance(features, list):
        raise ValueError("unexpected USGS response: 'features' is not a list")
    properties: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("unexpected USGS response: a feature is not an object")
        bloc = feature.get("properties")
        properties.append(bloc if isinstance(bloc, dict) else {})
    return properties


def _next_link(payload: dict[str, Any]) -> str | None:
    """The absolute URL of the next page, or `None` when there is none."""
    liens = payload.get("links")
    if not isinstance(liens, list):
        return None
    for link in liens:
        if not isinstance(link, dict):
            continue
        if link.get("rel") != "next":
            continue
        href = link.get("href")
        if isinstance(href, str) and href.strip():
            return href
    return None


def _value_criterion(
    features: list[dict[str, Any]],
    field: str,
    expected: str,
) -> CritereConformite:
    """The criterion "this field holds the value that was asked for".

    An empty page cannot verify anything: the criterion is then recorded as
    unverifiable, and the verdict becomes an abstention rather than a
    conformity.
    """
    if not features:
        return CritereConformite(demande=expected, verifie=False, recu="empty response")

    received_values: list[str] = []
    without = 0
    for properties in features:
        value = properties.get(field)
        if value is None:
            without += 1
            continue
        texte = str(value)
        if texte not in received_values:
            received_values.append(texte)

    if not received_values:
        return CritereConformite(
            demande=expected,
            verifie=False,
            recu=f"{without} record(s) without '{field}'",
        )
    deviations = [value for value in received_values if value != expected]
    received = ", ".join(received_values)
    if without:
        received = f"{received} (+{without} without '{field}')"
    return CritereConformite(
        demande=expected,
        verifie=True,
        recu=received,
        conforme=not deviations and not without,
    )


def _values_criterion(
    features: list[dict[str, Any]],
    field: str,
    expected: tuple[str, ...],
) -> CritereConformite:
    """The criterion "these fields hold only the values that were asked for"."""
    if not features:
        return CritereConformite(
            demande=", ".join(expected),
            verifie=False,
            recu="empty response",
        )

    received_values: list[str] = []
    without = 0
    for properties in features:
        value = properties.get(field)
        if value is None:
            without += 1
            continue
        texte = str(value)
        if texte not in received_values:
            received_values.append(texte)

    if not received_values:
        return CritereConformite(
            demande=", ".join(expected),
            verifie=False,
            recu=f"{without} record(s) without '{field}'",
        )
    deviations = [value for value in received_values if value not in expected]
    received = ", ".join(received_values)
    if without:
        received = f"{received} (+{without} without '{field}')"
    return CritereConformite(
        demande=", ".join(expected),
        verifie=True,
        recu=received,
        conforme=not deviations and not without,
    )


def _block_values_criterion(
    features: list[dict[str, Any]],
    field: str,
    expected: tuple[str, ...],
) -> CritereConformite:
    """The same criterion, read on the `data` blocks of the statistics service."""
    if not features:
        return CritereConformite(
            demande=", ".join(expected),
            verifie=False,
            recu="empty response",
        )

    received_values: list[str] = []
    without = 0
    for properties in features:
        blocks = properties.get("data")
        if not isinstance(blocks, list):
            without += 1
            continue
        for bloc in blocks:
            if not isinstance(bloc, dict):
                continue
            value = bloc.get(field)
            if value is None:
                continue
            texte = str(value)
            if texte not in received_values:
                received_values.append(texte)

    if not received_values:
        return CritereConformite(
            demande=", ".join(expected),
            verifie=False,
            recu=f"{without} feature(s) without a usable 'data' block",
        )
    deviations = [value for value in received_values if value not in expected]
    received = ", ".join(received_values)
    return CritereConformite(
        demande=", ".join(expected),
        verifie=True,
        recu=received,
        conforme=not deviations,
    )


def _fields_criterion(
    features: list[dict[str, Any]],
    champs: Sequence[str],
) -> CritereConformite:
    """The criterion "the records carry the fields the reader needs".

    A record that does not carry them cannot be interpreted. That is not a
    violation: it is a point left in the dark, and the verdict says so. The
    criterion is checked on **every** record: a page where only some records
    are interpretable is a page that cannot be interpreted as a whole.
    """
    if not features:
        return CritereConformite(
            demande=", ".join(champs),
            verifie=False,
            recu="empty response",
        )

    missing_fields: list[str] = []
    incomplete_records = 0
    for properties in features:
        absences = [field for field in champs if properties.get(field) is None]
        if absences:
            incomplete_records += 1
            for field in absences:
                if field not in missing_fields:
                    missing_fields.append(field)
    if missing_fields:
        return CritereConformite(
            demande=", ".join(champs),
            verifie=False,
            recu=f"{incomplete_records} record(s) missing: {', '.join(missing_fields)}",
        )
    return CritereConformite(
        demande=", ".join(champs),
        verifie=True,
        recu=f"{len(features)} record(s) with the required fields",
        conforme=True,
    )


__all__ = [
    "BASE_URL",
    "CREDENTIAL_REF",
    "LICENSE",
    "STATISTICS_URL",
    "UsgsObservationNormalsAdapter",
    "UsgsOgcItemsAdapter",
]
