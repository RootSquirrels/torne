/**
 * The resources the application reads.
 *
 * A resource is declared once, here, where it is defined: the key, the way
 * it is fetched, and how long its value stays fresh. Everywhere else, a
 * component asks for a key and reads a value.
 *
 * The store is a singleton because the state is shared: the map, the entity
 * list, the filter bar and the reading panel all read the same manifest, and
 * they must not fetch it four times.
 */
import { api } from '@/services/api/client';
import { createResourceStore } from '@/services/api/resourceStore';

/** A country boundary, as the prepared GeoJSON describes it. */
export interface GeoJsonFeature {
  readonly id?: string | number;
  readonly properties?: { readonly name?: string };
  readonly geometry:
    | { readonly type: 'Polygon'; readonly coordinates: number[][][] }
    | { readonly type: 'MultiPolygon'; readonly coordinates: number[][][][] };
}

/** The collection of country boundaries. */
export interface GeoJsonCollection {
  readonly features: readonly GeoJsonFeature[];
}

/**
 * The key under which the catalogue is read.
 *
 * The manifest is the one projection the explorer reads: it carries the
 * catalogue, the coverage, the models and the results.
 */
export const MANIFEST = 'manifest';

/**
 * The key under which the country boundaries are read.
 *
 * They are served from the application's own origin: the explorer fetches no
 * third-party resource at runtime. They are a static file that never
 * changes, so their value stays fresh for far longer than the catalogue's.
 */
export const BOUNDARIES = 'boundaries';

/** The shared store. */
export const resources = createResourceStore();

resources.register(
  MANIFEST,
  (signal) => api.manifest(signal),
  // The catalogue changes when a mission is added or a product is published:
  // rarely, and never in the middle of a reading.
  { freshnessMs: 30_000 },
);

resources.register(
  BOUNDARIES,
  async (signal) => {
    const response = await fetch('/data/countries-50m.geo.json', { signal });
    if (!response.ok) {
      throw new Error(`the boundaries answered HTTP ${response.status}`);
    }
    return (await response.json()) as GeoJsonCollection;
  },
  // The file is prepared at build time and never changes.
  { freshnessMs: 600_000 },
);
