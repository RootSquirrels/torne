"""The surface layer — the registry, the reading, the coverage.

Three things are tested here, and they are the three things that decide whether
the surface layer can be trusted.

**The registry is load-bearing.** A collection that is not registered produces
no observation at all: the repository does not invent a quantity for a product it
has not read. That is what makes the registry a record of decisions rather
than a convenience.

**The reading keeps the catalogue's own times.** `published` is the
publication instant, and the delay between validity and publication is
computed from it — for the Soil Water Index, that delay is over a year, which
is the fact that decides what a point-in-time reconstruction could have known.

**The coverage is not the dependence.** A product can cover the whole period
and still be worthless as independent evidence, and a product can be
independent and cover nothing. The coverage answer and the dependence answer
are separate, and the tests keep them apart.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from torne.contracts.earth_observation import ObservationNature
from torne.contracts.spatial import BoundingBox
from torne.contracts.time import PublicationState
from torne.eo import (
    SURFACE_PRODUCTS,
    InterpretationError,
    known_product,
    observation_from_item,
    publication_latency,
)
from torne.eo.coverage import coverage, dependence_ledger
from torne.eo.products import MeteorologicalDependence

STORED_AT = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def _swi_item() -> dict[str, object]:
    """An element of the Soil Water Index, as the catalogue publishes it.

    Read on 2026-11-01 from
    `GET /v1/search?collections=clms_swi_europe_1km_daily_v1_cog` over the
    Rhine. The product covers Europe as a whole, and its affine transform
    describes the European grid, not a Rhine-sized tile.
    """
    return {
        "id": "CLMS_SWI_Europe_1km_daily_V1_20230630",
        "collection": "clms_swi_europe_1km_daily_v1_cog",
        "datetime": "2023-06-30T12:00:01Z",
        "bbox": [-11.0, 35.0, 50.0, 72.0],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-11.0, 35.0],
                    [50.0, 35.0],
                    [50.0, 72.0],
                    [-11.0, 72.0],
                    [-11.0, 35.0],
                ]
            ],
        },
        "properties": {
            "datetime": "2023-06-30T12:00:01Z",
            "created": "2024-06-12T14:23:31Z",
            "updated": "2026-04-30T09:11:02Z",
            "published": "2025-03-26T00:00:00Z",
            "proj:epsg": 4326,
            "product:type": "soil_water_index",
            "processing:level": "L4",
        },
        "assets": {
            "swi010": {
                "href": "https://example.test/swi010.tif",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data"],
                "file:size": 123456,
                "file:checksum": "d41d8cd98f00b204e9800998ecf8427e",
                "proj:code": "EPSG:4326",
                "proj:shape": [4144, 6832],
                "proj:transform": [
                    0.0089285714285712,
                    0.0,
                    -11.0,
                    0.0,
                    -0.0089285714285694,
                    71.9999999999916,
                ],
                "proj:bbox": [-11.0, 35.0, 50.0, 72.0],
            },
            "Product": {
                "href": "https://example.test/product.zip",
                "type": "application/zip",
                "roles": ["data", "archive"],
                "auth:refs": ["oidc"],
            },
        },
    }


# --------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------


def test_the_registry_holds_the_products_that_were_read():
    assert len(SURFACE_PRODUCTS) == 13
    assert known_product("clms_swi_europe_1km_daily_v1_cog") is not None
    assert known_product("nonexistent-collection") is None


def test_the_evapotranspiration_product_starts_in_november_2025():
    """The ET product exists — and it does not exist before that date.

    It is the product the note put forward as the hydrological variable of the
    reconstruction. Its coverage starts on 2025-11-01: it describes none of
    the years a reconstruction of the Rhine would cover.
    """
    eta = known_product("clms_eta_global_300m_10daily_v1_cog")

    assert eta is not None
    assert eta.coverage_start == datetime(2025, 11, 1, tzinfo=UTC)
    assert eta.coverage_end is None


def test_every_product_declares_its_dependence_exactly_once():
    groups = dependence_ledger(tuple(SURFACE_PRODUCTS.values()))

    total = sum(len(names) for names in groups.values())
    assert total == len(SURFACE_PRODUCTS)


def test_the_dependency_ledger_does_not_put_anything_in_two_classes():
    groups = dependence_ledger(tuple(SURFACE_PRODUCTS.values()))

    for dependence, names in groups.items():
        assert len(set(names)) == len(names), dependence


def test_a_derived_product_is_not_declared_independent_without_an_audit():
    """The Soil Water Index is an index: its inputs were not audited."""
    swi = known_product("clms_swi_europe_1km_daily_v1_cog")

    assert swi.dependence is MeteorologicalDependence.NOT_AUDITED


def test_a_radiometric_retrieval_is_declared_independent():
    ssm = known_product("clms_ssm_europe_1km_daily_v1_cog")

    assert ssm.dependence is MeteorologicalDependence.INDEPENDENT
    assert ssm.instruments == ("csar",)


def test_the_catalogue_publishes_no_unit_and_the_registry_says_so():
    """The unit is the producer's declaration, and it is marked as such."""
    swi = known_product("clms_swi_europe_1km_daily_v1_cog")

    assert swi.unit is not None
    assert swi.unit_established is False


def test_an_open_collection_covers_the_present():
    ssm = known_product("clms_ssm_europe_1km_daily_v1_cog")

    assert ssm.open_coverage is True
    assert ssm.covers_instant(datetime(2030, 1, 1, tzinfo=UTC)) is True
    assert ssm.covers_instant(datetime(2014, 1, 1, tzinfo=UTC)) is False


# --------------------------------------------------------------------------
# The reading
# --------------------------------------------------------------------------


def test_an_element_becomes_an_observation():
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.observation_id == "CLMS_SWI_Europe_1km_daily_V1_20230630"
    assert observation.quantity == "soil_water_index"
    assert observation.nature is ObservationNature.DERIVED
    assert observation.product_type == "soil_water_index"
    assert observation.processing_level == "L4"
    assert observation.key == observation.observation_id


def test_the_reading_keeps_the_catalogue_publication_instant():
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.temporal.publication is PublicationState.ESTABLISHED
    assert observation.temporal.known_at == datetime(2025, 3, 26, tzinfo=UTC)


def test_the_lateness_of_publication_is_over_a_year_for_the_soil_water_index():
    """This is the fact that decides what a point-in-time reconstruction could know."""
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    latency = publication_latency(observation)

    assert latency is not None
    assert latency > timedelta(days=600)


def test_an_element_without_a_publication_stays_unusable_for_a_point_in_time_rendering():
    element = _swi_item()
    del element["properties"]["published"]

    observation = observation_from_item(
        element,
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.temporal.publication is PublicationState.UNKNOWN
    assert observation.is_usable is False


def test_an_unregistered_collection_produces_no_observation():
    element = _swi_item()
    element["collection"] = "nonexistent-collection"

    with pytest.raises(InterpretationError):
        observation_from_item(
            element,
            source_id="copernicus.dataspace.stac",
            evidence_id="ev-1",
            ingested_at=STORED_AT,
        )


def test_an_element_without_a_window_is_refused():
    element = _swi_item()
    del element["datetime"]
    del element["properties"]["datetime"]

    with pytest.raises(InterpretationError):
        observation_from_item(
            element,
            source_id="copernicus.dataspace.stac",
            evidence_id="ev-1",
            ingested_at=STORED_AT,
        )


def test_an_element_without_an_asset_is_refused():
    element = _swi_item()
    element["assets"] = {}

    with pytest.raises(InterpretationError):
        observation_from_item(
            element,
            source_id="copernicus.dataspace.stac",
            evidence_id="ev-1",
            ingested_at=STORED_AT,
        )


def test_the_reading_takes_the_footprint_from_the_geometry():
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.footprint.bbox.as_tuple() == (-11.0, 35.0, 50.0, 72.0)
    assert observation.spatial_ref == "EPSG:4326"


def test_the_reading_falls_back_to_the_enclosure_when_the_geometry_is_missing():
    element = _swi_item()
    del element["geometry"]

    observation = observation_from_item(
        element,
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.footprint.bbox.as_tuple() == (-11.0, 35.0, 50.0, 72.0)


def test_the_reading_reads_the_grid_out_of_the_affine_transform():
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    assert observation.grid is not None
    assert observation.grid.width == 6832
    assert observation.grid.height == 4144


def test_an_asset_protected_by_a_credential_is_declared_as_such():
    observation = observation_from_item(
        _swi_item(),
        source_id="copernicus.dataspace.stac",
        evidence_id="ev-1",
        ingested_at=STORED_AT,
    )

    protected = [a for a in observation.assets if a.requires_authentication]
    assert [a.key for a in protected] == ["Product"]


# --------------------------------------------------------------------------
# The coverage
# --------------------------------------------------------------------------


def test_a_product_that_starts_in_2025_does_not_cover_2014():
    eta = known_product("clms_eta_global_300m_10daily_v1_cog")

    result = coverage(
        eta,
        start=datetime(2014, 1, 1, tzinfo=UTC),
        end=datetime(2025, 12, 31, tzinfo=UTC),
    )

    assert result.covered is False
    assert result.reconstructable_from == datetime(2025, 11, 1, tzinfo=UTC)


def test_a_product_that_stopped_in_2021_does_not_cover_the_period_after_it():
    ndvi = known_product("clms_ndvi_global_300m_10daily_v1_cog")

    result = coverage(
        ndvi,
        start=datetime(2014, 1, 1, tzinfo=UTC),
        end=datetime(2025, 12, 31, tzinfo=UTC),
    )

    assert result.covered is False
    assert result.reconstructable_from == datetime(2014, 1, 1, tzinfo=UTC)


def test_a_covering_product_covers_the_whole_period():
    ssm = known_product("clms_ssm_europe_1km_daily_v1_cog")

    result = coverage(
        ssm,
        start=datetime(2015, 1, 1, tzinfo=UTC),
        end=datetime(2025, 12, 31, tzinfo=UTC),
    )

    assert result.covered is True
    assert result.reconstructable_from == datetime(2014, 10, 4, tzinfo=UTC)


def test_the_coverage_does_not_say_anything_about_the_dependence():
    """Coverage and independence are two answers, and the second one is separate."""
    eta = known_product("clms_eta_global_300m_10daily_v1_cog")

    result = coverage(
        eta,
        start=datetime(2025, 11, 1, tzinfo=UTC),
        end=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert result.covered is True
    assert result.dependence is MeteorologicalDependence.NOT_AUDITED


def test_a_requested_period_that_runs_backwards_is_refused():
    ssm = known_product("clms_ssm_europe_1km_daily_v1_cog")

    with pytest.raises(ValueError, match="does not run backwards"):
        coverage(
            ssm,
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_the_enclosure_helper_reads_a_rectangle_in_the_catalogue_reference():
    from torne.eo.coverage import requested_footprint

    footprint = requested_footprint(5.5, 43.5, 10.5, 51.0)

    assert str(footprint.ref) == "EPSG:4326"
    assert footprint.bbox == BoundingBox(west=5.5, south=43.5, east=10.5, north=51.0)
