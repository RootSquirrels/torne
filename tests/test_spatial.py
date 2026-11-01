"""The spatial vocabulary — the shapes the surface layer speaks.

These tests exercise the **contracts** of the spatial dimension: a reference, a
box, a footprint, a grid. They check two things at once.

First, the **invariants**: what the repository refuses to build. A degenerate box,
an open ring, a rotated grid — each is refused rather than repaired in silence.

Second, the **agreement with the published definitions**. The grid test is not
a self-consistency check: it reads the affine transform, the shape and the
bounding box that the Copernicus catalogue publishes for the Soil Water Index
of Europe, and it checks that the grid built from them covers exactly the
declared extent. A grid that disagreed with the catalogue's own numbers would
place every pixel in the wrong place — and nothing downstream would notice.
"""

from __future__ import annotations

import math

import pytest

from torne.contracts.spatial import (
    BoundingBox,
    Footprint,
    Point,
    RasterGrid,
    SpatialRef,
)

# --------------------------------------------------------------------------
# The reference
# --------------------------------------------------------------------------


def test_a_reference_needs_an_authority_and_a_code():
    with pytest.raises(ValueError, match="authority is required"):
        SpatialRef(authority="", code="4326")
    with pytest.raises(ValueError, match="code is required"):
        SpatialRef(authority="EPSG", code="  ")


def test_a_reference_reads_back_from_its_written_form():
    assert SpatialRef.from_string("EPSG:4326") == SpatialRef.epsg("4326")
    assert str(SpatialRef.epsg(4326)) == "EPSG:4326"


def test_an_unreadable_reference_is_refused():
    with pytest.raises(ValueError, match="unreadable spatial reference"):
        SpatialRef.from_string("EPSG 4326")


# --------------------------------------------------------------------------
# The point and the box
# --------------------------------------------------------------------------


def test_a_point_refuses_a_non_finite_coordinate():
    with pytest.raises(ValueError, match="is not finite"):
        Point(x=math.inf, y=0.0)
    with pytest.raises(ValueError, match="is not finite"):
        Point(x=0.0, y=math.nan)


def test_a_box_refuses_a_degenerate_ordering():
    """A box that does not order its bounds is not a box."""
    with pytest.raises(ValueError, match="requires west < east"):
        BoundingBox(west=10.0, south=0.0, east=5.0, north=1.0)
    with pytest.raises(ValueError, match="requires south < north"):
        BoundingBox(west=0.0, south=10.0, east=1.0, north=5.0)


def test_a_box_reads_back_from_the_stac_order():
    box = BoundingBox.from_sequence((5.5, 43.5, 10.5, 51.0))

    assert box.as_tuple() == (5.5, 43.5, 10.5, 51.0)
    assert box.width == pytest.approx(5.0)
    assert box.height == pytest.approx(7.5)


def test_a_box_reads_back_from_a_wrong_number_count():
    with pytest.raises(ValueError, match="four numbers"):
        BoundingBox.from_sequence((5.5, 43.5, 10.5))


def test_two_boxes_intersect_when_they_share_ground():
    """Touching at the edge counts as overlapping, and that is deliberate."""
    first = BoundingBox(west=0.0, south=0.0, east=1.0, north=1.0)
    second = BoundingBox(west=1.0, south=0.0, east=2.0, north=1.0)
    distant = BoundingBox(west=1.5, south=0.0, east=2.5, north=1.0)

    assert first.intersects(second)
    assert not first.intersects(distant)


def test_a_box_contains_a_point_it_encloses():
    box = BoundingBox(west=5.5, south=43.5, east=10.5, north=51.0)

    assert box.contains(Point(x=7.5, y=48.0))
    assert not box.contains(Point(x=12.0, y=48.0))


def test_two_boxes_unite_into_their_common_envelope():
    first = BoundingBox(west=0.0, south=0.0, east=1.0, north=1.0)
    second = BoundingBox(west=0.5, south=-0.5, east=2.0, north=0.5)

    assert first.union(second) == BoundingBox(west=0.0, south=-0.5, east=2.0, north=1.0)


# --------------------------------------------------------------------------
# The footprint
# --------------------------------------------------------------------------


def _rhine_polygon() -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [[[7.0, 47.0], [8.0, 47.0], [8.0, 48.0], [7.0, 48.0], [7.0, 47.0]]],
    }


def test_a_footprint_reads_a_geojson_polygon():
    footprint = Footprint.from_geojson_polygon(_rhine_polygon(), ref=SpatialRef.epsg("4326"))

    assert footprint.bbox.as_tuple() == (7.0, 47.0, 8.0, 48.0)
    assert footprint.ring[0] == footprint.ring[-1]


def test_a_footprint_refuses_an_open_ring():
    open_ring = {
        "type": "Polygon",
        "coordinates": [[[7.0, 47.0], [8.0, 47.0], [8.0, 48.0], [7.0, 49.0]]],
    }

    with pytest.raises(ValueError, match="is not closed"):
        Footprint.from_geojson_polygon(open_ring, ref=SpatialRef.epsg("4326"))


def test_a_footprint_refuses_a_geometry_it_does_not_understand():
    with pytest.raises(ValueError, match="unsupported geometry"):
        Footprint.from_geojson_polygon(
            {"type": "Point", "coordinates": [7.0, 47.0]}, ref=SpatialRef.epsg("4326")
        )


def test_a_footprint_needs_three_distinct_vertices():
    with pytest.raises(ValueError, match="three distinct vertices"):
        Footprint(
            ref=SpatialRef.epsg("4326"),
            bbox=BoundingBox(west=0.0, south=0.0, east=1.0, north=1.0),
            ring=(
                Point(x=0.0, y=0.0),
                Point(x=1.0, y=0.0),
                Point(x=0.0, y=0.0),
                Point(x=0.0, y=0.0),
            ),
        )


def test_a_footprint_refuses_a_ring_that_is_not_closed():
    with pytest.raises(ValueError, match="ring is closed"):
        Footprint(
            ref=SpatialRef.epsg("4326"),
            bbox=BoundingBox(west=0.0, south=0.0, east=1.0, north=1.0),
            ring=(
                Point(x=0.0, y=0.0),
                Point(x=1.0, y=0.0),
                Point(x=1.0, y=1.0),
                Point(x=0.0, y=1.0),
            ),
        )


def test_two_footprints_intersect_when_their_boxes_do():
    first = Footprint.from_geojson_polygon(_rhine_polygon(), ref=SpatialRef.epsg("4326"))
    other = Footprint.from_geojson_polygon(
        {
            "type": "Polygon",
            "coordinates": [[[7.5, 47.5], [9.0, 47.5], [9.0, 48.5], [7.5, 48.5], [7.5, 47.5]]],
        },
        ref=SpatialRef.epsg("4326"),
    )
    far = Footprint.from_geojson_polygon(
        {
            "type": "Polygon",
            "coordinates": [[[20.0, 10.0], [21.0, 10.0], [21.0, 11.0], [20.0, 11.0], [20.0, 10.0]]],
        },
        ref=SpatialRef.epsg("4326"),
    )

    assert first.intersects(other)
    assert not first.intersects(far)
    assert first.contains_point(Point(x=7.5, y=47.5))


def test_a_footprint_built_from_a_box_is_the_enclosing_rectangle():
    """The repository does not claim to have read a contour it never read."""
    box = BoundingBox(west=5.5, south=43.5, east=10.5, north=51.0)

    footprint = Footprint.from_bounding_box(box, ref=SpatialRef.epsg("4326"))

    assert footprint.bbox == box
    assert len(footprint.ring) == 5
    assert footprint.ring[0] == footprint.ring[-1]


# --------------------------------------------------------------------------
# The grid
# --------------------------------------------------------------------------

# The values the Copernicus catalogue publishes for the Soil Water Index of
# Europe, 1 km, daily (collection `clms_swi_europe_1km_daily_v1_cog`),
# read on 2026-11-01: the affine transform, the raster shape, and the
# declared extent.
TRANSFORM_SWI = [0.0089285714285712, 0.0, -11.0, 0.0, -0.0089285714285694, 71.9999999999916]
SHAPE_SWI = [4144, 6832]
BBOX_SWI = (-11.0, 35.0, 50.0, 72.0)


def test_a_grid_reads_the_catalogue_affine_transform():
    grid = RasterGrid.from_transform(
        ref=SpatialRef.epsg("4326"), transform=TRANSFORM_SWI, shape=SHAPE_SWI
    )

    assert grid.width == 6832
    assert grid.height == 4144
    assert grid.pixel_size_x == pytest.approx(0.0089285714285712)
    assert grid.pixel_size_y == pytest.approx(-0.0089285714285694)


def test_the_grid_covers_exactly_the_extent_the_catalogue_declares():
    """The grid and the catalogue must agree on where Europe is.

    A grid built from the transform that disagreed with the declared
    `proj:bbox` would place every pixel in the wrong place, and nothing
    downstream would notice.
    """
    grid = RasterGrid.from_transform(
        ref=SpatialRef.epsg("4326"), transform=TRANSFORM_SWI, shape=SHAPE_SWI
    )

    west, south, east, north = grid.bbox().as_tuple()

    assert west == pytest.approx(BBOX_SWI[0], abs=1e-6)
    assert south == pytest.approx(BBOX_SWI[1], abs=1e-6)
    assert east == pytest.approx(BBOX_SWI[2], abs=1e-6)
    assert north == pytest.approx(BBOX_SWI[3], abs=1e-6)


def test_a_grid_counts_its_cells():
    grid = RasterGrid.from_transform(
        ref=SpatialRef.epsg("4326"), transform=TRANSFORM_SWI, shape=SHAPE_SWI
    )

    assert grid.cell_count() == 4144 * 6832


def test_a_rotated_transform_is_refused_rather_than_misread():
    """A turned grid is not a grid: reading it straight would falsify the origin."""
    with pytest.raises(ValueError, match="non-axis-aligned transform"):
        RasterGrid.from_transform(
            ref=SpatialRef.epsg("4326"),
            transform=[0.0, 0.008, -11.0, 0.008, 0.0, 72.0],
            shape=SHAPE_SWI,
        )


def test_a_transform_of_the_wrong_length_is_refused():
    with pytest.raises(ValueError, match="six numbers"):
        RasterGrid.from_transform(
            ref=SpatialRef.epsg("4326"), transform=[1.0, 0.0, 0.0], shape=SHAPE_SWI
        )


def test_a_grid_refuses_an_empty_dimension():
    with pytest.raises(ValueError, match="width must be at least 1"):
        RasterGrid(
            ref=SpatialRef.epsg("4326"),
            width=0,
            height=10,
            pixel_size_x=1.0,
            pixel_size_y=1.0,
            origin_x=0.0,
            origin_y=0.0,
        )


def test_a_grid_refuses_a_null_pixel_size():
    """A null step is not a resolution, and reading it would divide by zero."""
    with pytest.raises(ValueError, match="finite, non-zero number"):
        RasterGrid(
            ref=SpatialRef.epsg("4326"),
            width=10,
            height=10,
            pixel_size_x=0.0,
            pixel_size_y=1.0,
            origin_x=0.0,
            origin_y=0.0,
        )
