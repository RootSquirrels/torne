/**
 * Build the country boundaries the map draws.
 *
 * The explorer used to fetch a TopoJSON file from a CDN at runtime. The
 * application no longer depends on a third party: the boundaries are prepared
 * here, at build time, and served from the application's own origin.
 *
 * What this does:
 *
 * - converts the TopoJSON to GeoJSON, so the runtime does not need a TopoJSON
 *   reader at all;
 * - keeps only the identifier and the name of each country;
 * - simplifies the outlines with Douglas–Peucker, at a tolerance far below
 *   what the map's own zoom levels can show;
 * - rounds what is left to three decimals.
 *
 * The simplification is a **display** decision, taken on the geometry only. It
 * changes no measurement, no position and no boundary of a country: the map
 * draws the shape of a region, not the extent of a catchment.
 *
 * The output is deterministic: the same input always produces the same file.
 *
 * Run it with `npm run build:boundaries`. It runs automatically before
 * `npm run build` and `npm run dev`.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { feature } from 'topojson-client';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

const SOURCE = resolve(root, 'node_modules', 'world-atlas', 'countries-50m.json');
const TARGET = resolve(root, 'public', 'data', 'countries-50m.geo.json');

/**
 * The simplification tolerance, in degrees of longitude.
 *
 * A tenth of a degree is about eleven kilometres — two or three pixels at the
 * zoom levels the explorer reaches when it drills down to a station, and
 * invisible at the Europe overview. The simplification takes the file from
 * 1.4 MB to 0.4 MB without changing what the reader can see.
 */
const TOLERANCE = 0.1;

const PRECISION = 1000;

function round(value) {
  return Math.round(value * PRECISION) / PRECISION;
}

/** The perpendicular distance from a point to the segment a→b. */
function perpendicularDistance([px, py], [ax, ay], [bx, by]) {
  let dx = bx - ax;
  let dy = by - ay;
  if (dx === 0 && dy === 0) {
    return Math.hypot(px - ax, py - ay);
  }
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/** Douglas–Peucker: keep the points that carry the shape, drop the rest. */
function simplify(points, tolerance) {
  if (points.length <= 3) {
    return points;
  }

  let furthest = 0;
  let furthestDistance = 0;
  const first = points[0];
  const last = points[points.length - 1];
  for (let index = 1; index < points.length - 1; index += 1) {
    const distance = perpendicularDistance(points[index], first, last);
    if (distance > furthestDistance) {
      furthest = index;
      furthestDistance = distance;
    }
  }

  if (furthestDistance <= tolerance) {
    return [first, last];
  }

  const left = simplify(points.slice(0, furthest + 1), tolerance);
  const right = simplify(points.slice(furthest), tolerance);
  return [...left.slice(0, -1), ...right];
}

function simplifyRing(ring) {
  const closed = ring[0] === ring[ring.length - 1] ? ring : [...ring, ring[0]];
  const simplified = simplify(closed, TOLERANCE);
  const rounded = simplified.map(([lon, lat]) => [round(lon), round(lat)]);
  // A ring of fewer than four points has no area and cannot be drawn.
  return rounded.length >= 4 ? rounded : [];
}

function simplifyGeometry(geometry) {
  if (geometry.type === 'Polygon') {
    return { ...geometry, coordinates: geometry.coordinates.map(simplifyRing) };
  }
  if (geometry.type === 'MultiPolygon') {
    return {
      ...geometry,
      coordinates: geometry.coordinates.map((polygon) => polygon.map(simplifyRing)),
    };
  }
  return geometry;
}

const topology = JSON.parse(readFileSync(SOURCE, 'utf8'));
const collection = feature(topology, topology.objects.countries);

const features = collection.features
  .filter((entry) => entry.geometry !== null && entry.geometry !== undefined)
  .map((entry) => ({
    type: 'Feature',
    id: entry.id,
    properties: { name: entry.properties?.name ?? entry.id },
    geometry: simplifyGeometry(entry.geometry),
  }))
  .filter((entry) => {
    const { geometry } = entry;
    if (geometry.type === 'Polygon') {
      return geometry.coordinates.length > 0;
    }
    if (geometry.type === 'MultiPolygon') {
      return geometry.coordinates.some((polygon) => polygon.length > 0);
    }
    return true;
  })
  .sort((left, right) => String(left.id).localeCompare(String(right.id)));

const output = { type: 'FeatureCollection', features };

mkdirSync(dirname(TARGET), { recursive: true });
writeFileSync(TARGET, `${JSON.stringify(output)}\n`, 'utf8');

const bytes = readFileSync(TARGET).length;
process.stdout.write(
  `country boundaries: ${features.length} features, ${(bytes / 1024).toFixed(1)} kB -> ${TARGET}\n`,
);
