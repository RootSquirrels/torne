"""The spatial reference — first-order information, finally structured.

Until now, the repository's observation carried a free `spatial_ref: str`: a
station, a string, "non_spatial" for what was not located. That was right as
long as the repository only read **point measurements**, at a station that is a
point.

Surface observation changes that. A Sentinel-2 image is not a measurement at a
point: it is a **field** over a footprint, in a reference system, with a grid,
a resolution, invalid pixels and masks. The spatial dimension stops being a
label: it becomes **part of the data**.

This module therefore sets the repository's spatial vocabulary. It is
deliberately **minimal**: a reference system, a point, a bounding box, a
footprint, a grid. It is not a geospatial framework — the repository does not
need one, and `docs/PROGRAMME.md` refuses to add one without a demonstrated
need.

Three rules, all verifiable:

1. **No runtime dependency, and no computed projection.** The repository does
   not add `pyproj`, `shapely` or `rasterio`: a dependency is added at its
   first real import (`docs/ARCHITECTURE.md` §8). A point in EPSG:4326 cannot
   be transformed into EPSG:32632 here — and it will not be. Coordinates are
   **kept in the source's own terms**, which is also the repository's rule for
   units.
2. **An absence stays an absence.** An unknown reference system never becomes
   "EPSG:4326" by default; a missing footprint never becomes "the envelope of
   the globe". An empty reference system is refused at construction.
3. **Approximations are named.** The intersection of two footprints is
   evaluated on their **bounding boxes**, not on their polygons. That is an
   approximation: sufficient for a conformity predicate, insufficient for an
   area computation. The code says so rather than letting it be believed.

These objects are **contracts**: they guarantee the shape and internal
consistency of a piece of spatial information, not its correctness. A correct
bounding box still describes badly a product the provider produced badly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Self

__all__ = [
    "BoundingBox",
    "Footprint",
    "Point",
    "RasterGrid",
    "SpatialRef",
]


@dataclass(frozen=True, slots=True)
class SpatialRef:
    """A coordinate reference system, named by its authority.

    The authority and the code are **carried by the data**, never inferred from
    context: a pair of coordinates means nothing without the reference system
    it was produced in. The point observation already carried that requirement
    as a free string (`Observation.spatial_ref`); it becomes structured here,
    because a satellite footprint needs the EPSG code, the origin and the grid
    size, not a name.

    The repository only knows **named** reference systems: it translates none.
    `EPSG:4326` and `EPSG:32632` are two distinct, non-interchangeable systems,
    and nothing here lets one pass from one to the other.
    """

    authority: str
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.authority, str) or not self.authority.strip():
            raise ValueError("SpatialRef.authority is required and non-empty")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("SpatialRef.code is required and non-empty")
        object.__setattr__(self, "authority", self.authority.strip())
        object.__setattr__(self, "code", self.code.strip())

    @classmethod
    def epsg(cls, code: str | int) -> Self:
        """The EPSG reference system designated by its code."""
        return cls(authority="EPSG", code=str(code))

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Read a reference system written "AUTHORITY:CODE"."""
        if not isinstance(value, str) or ":" not in value:
            raise ValueError(f"unreadable spatial reference: {value!r}")
        authority, code = value.split(":", 1)
        return cls(authority=authority, code=code)

    def __str__(self) -> str:
        return f"{self.authority}:{self.code}"


@dataclass(frozen=True, slots=True)
class Point:
    """A point, in the coordinates of its reference system.

    The axes are not named: the reference system carries the order (`x` then
    `y`, the repository's implicit convention). A point without a reference
    system cannot be located — which is why `Footprint` and `RasterGrid` always
    carry theirs.
    """

    x: float
    y: float

    def __post_init__(self) -> None:
        for name, value in (("x", self.x), ("y", self.y)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"Point.{name} must be a number")
            if not math.isfinite(float(value)):
                raise ValueError(f"Point.{name} is not finite: it is not a coordinate")

    def as_tuple(self) -> tuple[float, float]:
        """The coordinate pair, in axis order."""
        return (float(self.x), float(self.y))


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A bounding box, in the coordinates of its reference system.

    The order is that of STAC and GeoJSON: `west, south, east, north`. A
    **degenerate** box (west == east) is refused: it describes no surface, and
    accepting it would pass an absence off as a measurement of zero size.
    """

    west: float
    south: float
    east: float
    north: float

    def __post_init__(self) -> None:
        for name, value in (
            ("west", self.west),
            ("south", self.south),
            ("east", self.east),
            ("north", self.north),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"BoundingBox.{name} must be a number")
            if not math.isfinite(float(value)):
                raise ValueError(f"BoundingBox.{name} is not finite")
        if not self.west < self.east:
            raise ValueError("a bounding box requires west < east: the order is not negotiable")
        if not self.south < self.north:
            raise ValueError("a bounding box requires south < north: the order is not negotiable")

    @classmethod
    def from_sequence(cls, values: tuple[float, ...] | list[float]) -> Self:
        """Read a bounding box written `west, south, east, north`."""
        if len(values) != 4:
            raise ValueError("a bounding box is written as four numbers: west, south, east, north")
        return cls(
            west=float(values[0]),
            south=float(values[1]),
            east=float(values[2]),
            north=float(values[3]),
        )

    def as_tuple(self) -> tuple[float, float, float, float]:
        """The bounding box, in STAC order."""
        return (float(self.west), float(self.south), float(self.east), float(self.north))

    @property
    def width(self) -> float:
        """The west-east extent, in the units of the reference system."""
        return float(self.east) - float(self.west)

    @property
    def height(self) -> float:
        """The south-north extent, in the units of the reference system."""
        return float(self.north) - float(self.south)

    def intersects(self, other: BoundingBox) -> bool:
        """Do the two bounding boxes overlap?

        The intersection is evaluated on the **boxes**, boundaries included:
        two boxes that only touch along an edge are considered overlapping. For
        a conformity predicate on surface products, the error margin is far
        below the resolution of a product; it would not be acceptable for an
        area computation, which is not done here.
        """
        return not (
            self.east < other.west
            or other.east < self.west
            or self.north < other.south
            or other.north < self.south
        )

    def contains(self, point: Point) -> bool:
        """Is the point inside the bounding box?"""
        return self.west <= point.x <= self.east and self.south <= point.y <= self.north

    def union(self, other: BoundingBox) -> BoundingBox:
        """The envelope common to both bounding boxes."""
        return BoundingBox(
            west=min(self.west, other.west),
            south=min(self.south, other.south),
            east=max(self.east, other.east),
            north=max(self.north, other.north),
        )


@dataclass(frozen=True, slots=True)
class Footprint:
    """The footprint of a surface product: an outline and its bounding box.

    The ring is **closed** — the last point repeats the first — as in GeoJSON,
    and it has at least three distinct vertices: a degenerate ring describes no
    surface.

    The bounding box is not derived from the outline: it is **carried** by the
    data, because it is the one the provider declares, and the one that will be
    compared to the requested envelope. The two can diverge; the finding itself
    is then what is useful.
    """

    ref: SpatialRef
    bbox: BoundingBox
    ring: tuple[Point, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.ref, SpatialRef):
            raise TypeError("Footprint.ref must be a SpatialRef")
        if not isinstance(self.bbox, BoundingBox):
            raise TypeError("Footprint.bbox must be a BoundingBox")
        if not isinstance(self.ring, tuple) or len(self.ring) < 4:
            raise ValueError("a footprint requires a closed ring of at least four points")
        for point in self.ring:
            if not isinstance(point, Point):
                raise TypeError("Footprint.ring contains only Point")
        if self.ring[0].as_tuple() != self.ring[-1].as_tuple():
            raise ValueError("a ring is closed: the last point repeats the first")
        distinct = {point.as_tuple() for point in self.ring[:-1]}
        if len(distinct) < 3:
            raise ValueError("a footprint requires at least three distinct vertices")

    @classmethod
    def from_geojson_polygon(
        cls,
        geometry: dict[str, object],
        *,
        ref: SpatialRef,
    ) -> Self:
        """Read a GeoJSON geometry of type `Polygon`.

        The order of the points is kept as is: the repository does not reorient
        a ring, and does not close it either if it is open — an open geometry is
        **refused**, not silently repaired.
        """
        if not isinstance(geometry, dict):
            raise TypeError("a geometry is a JSON object")
        if geometry.get("type") != "Polygon":
            raise ValueError(f"unsupported geometry: {geometry.get('type')!r}")
        rings = geometry.get("coordinates")
        if not isinstance(rings, list) or not rings:
            raise ValueError("geometry without a ring")
        points = []
        for pair in rings[0]:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                raise ValueError("unreadable polygon vertex")
            points.append(Point(x=float(pair[0]), y=float(pair[1])))
        if len(points) < 2 or points[0].as_tuple() != points[-1].as_tuple():
            raise ValueError("open geometry: the ring is not closed")
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        bbox = BoundingBox(west=min(xs), south=min(ys), east=max(xs), north=max(ys))
        return cls(ref=ref, bbox=bbox, ring=tuple(points))

    @classmethod
    def from_bounding_box(cls, bbox: BoundingBox, *, ref: SpatialRef) -> Self:
        """The **enclosing** footprint of a bounding box.

        It is a **rectangle**, not an outline: when the source only publishes a
        bounding box, the footprint is the smallest figure that contains it, and
        it **overestimates** the real surface of the product. The repository
        does not pretend to have read an outline it did not read — it says so,
        and any estimate drawn from it is an upper bound.

        This is the case of catalogue items whose geometry is missing: the
        repository then builds the footprint from the bounding box, and the
        intersections it computes afterwards are upper bounds.
        """
        if not isinstance(bbox, BoundingBox):
            raise TypeError("from_bounding_box expects a BoundingBox")
        if not isinstance(ref, SpatialRef):
            raise TypeError("from_bounding_box expects a SpatialRef")
        south_west = Point(x=bbox.west, y=bbox.south)
        south_east = Point(x=bbox.east, y=bbox.south)
        north_east = Point(x=bbox.east, y=bbox.north)
        north_west = Point(x=bbox.west, y=bbox.north)
        return cls(
            ref=ref,
            bbox=bbox,
            ring=(south_west, south_east, north_east, north_west, south_west),
        )

    def intersects(self, other: Footprint) -> bool:
        """Do the two footprints overlap?

        **Documented approximation**: the answer is that of their **bounding
        boxes**, not of their polygons. A footprint can therefore be declared
        overlapping while the polygons do not touch — the price of a
        computation without a geospatial dependency. For a conformity predicate,
        where surface products far larger than the grid cell are compared, the
        margin is negligible; for an area, it would not be.
        """
        return self.bbox.intersects(other.bbox)

    def contains_point(self, point: Point) -> bool:
        """Is the point inside the footprint's bounding box?

        **Documented approximation**: like `intersects`, the answer is that of
        the bounding box, not of the polygon.
        """
        return self.bbox.contains(point)


@dataclass(frozen=True, slots=True)
class RasterGrid:
    """The grid of a raster product: reference system, origin, cell, dimensions.

    The grid is described in the provider's terms: the cell size is the one it
    declares, in **its** units. The repository does not convert it — any more
    than it converts a discharge unit. A grid in EPSG:4326 therefore has a cell
    expressed in degrees, whatever the `gsd` in metres the provider publishes
    next to it says: both numbers coexist in the source without the repository
    confusing them.

    `from_transform` reads the affine transform in GDAL format
    (`[a, b, c, d, e, f]`), which the satellite catalogue publishes on every
    asset: that is where the origin and the cell size come from, without a
    dependency on a raster library.
    """

    ref: SpatialRef
    width: int
    height: int
    pixel_size_x: float
    pixel_size_y: float
    origin_x: float
    origin_y: float

    def __post_init__(self) -> None:
        if not isinstance(self.ref, SpatialRef):
            raise TypeError("RasterGrid.ref must be a SpatialRef")
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width < 1:
            raise ValueError("RasterGrid.width must be at least 1")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height < 1:
            raise ValueError("RasterGrid.height must be at least 1")
        for name, value in (
            ("pixel_size_x", self.pixel_size_x),
            ("pixel_size_y", self.pixel_size_y),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"RasterGrid.{name} must be a number")
            if not math.isfinite(float(value)) or float(value) == 0.0:
                raise ValueError(f"RasterGrid.{name} must be a finite, non-zero number")
        for name, value in (("origin_x", self.origin_x), ("origin_y", self.origin_y)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"RasterGrid.{name} must be a number")
            if not math.isfinite(float(value)):
                raise ValueError(f"RasterGrid.{name} is not finite")

    @classmethod
    def from_transform(
        cls,
        *,
        ref: SpatialRef,
        transform: tuple[float, ...] | list[float],
        shape: tuple[int, int] | list[int],
    ) -> Self:
        """Read a grid from its affine transform and its shape.

        `transform` is the affine transform in GDAL format: `[a, b, c, d, e, f]`,
        where `x = a·column + b·row + c` and `y = d·column + e·row + f`.
        `shape` is `[rows, columns]`, in GDAL order.

        Only **axis-aligned** transforms (`b = d = 0`) are read: a rotated grid
        read crooked would produce a wrong origin — hence a wrong bounding box,
        hence a wrong conformity. It is refused rather than approximated.
        """
        if len(transform) != 6:
            raise ValueError("an affine transform has six numbers")
        if len(shape) != 2:
            raise ValueError("a shape has two numbers: rows and columns")
        a, b, c, d, e, f = (float(v) for v in transform)
        if b != 0.0 or d != 0.0:
            raise ValueError("non-axis-aligned transform: the grid would not be read correctly")
        rows, columns = int(shape[0]), int(shape[1])
        return cls(
            ref=ref,
            width=columns,
            height=rows,
            pixel_size_x=a,
            pixel_size_y=e,
            origin_x=c,
            origin_y=f,
        )

    def bbox(self) -> BoundingBox:
        """The bounding box covered by the grid."""
        x_max = self.origin_x + self.pixel_size_x * self.width
        y_min = self.origin_y + self.pixel_size_y * self.height
        return BoundingBox(
            west=min(self.origin_x, x_max),
            south=min(self.origin_y, y_min),
            east=max(self.origin_x, x_max),
            north=max(self.origin_y, y_min),
        )

    def cell_count(self) -> int:
        """The number of cells in the grid."""
        return int(self.width) * int(self.height)
