/**
 * The spatial contract.
 *
 * Positions are **(longitude, latitude)**, in the reference frame the source
 * uses — the explorer does not project, and neither does this contract. A
 * layer declares its own reference so that the map can say what it is
 * showing.
 */

import type { ApiRef } from '@/types/api/manifest';

/** A geographic extent. */
export interface SpatialExtent {
  readonly west: number;
  readonly south: number;
  readonly east: number;
  readonly north: number;
}

/** A point on the map: a station, a borehole, a mooring. */
export interface SpatialPoint {
  readonly id: string;
  readonly label: string;
  /** (longitude, latitude). */
  readonly position: readonly [number, number];
  /** The kind of entity, e.g. "station". */
  readonly kind: string;
  /** The layer the point belongs to. */
  readonly layerId: string;
  /** The values shown in the pop-up. */
  readonly properties: Readonly<Record<string, string | number | boolean | null>>;
}

/** A closed ring of positions. */
export type SpatialRing = readonly (readonly [number, number])[];

/** An area: a catchment, a basin, a footprint. */
export interface SpatialArea {
  readonly id: string;
  readonly label: string;
  /** The rings of the area: the first is the outer boundary, the others are holes. */
  readonly rings: readonly SpatialRing[];
  /** The layer the area belongs to. */
  readonly layerId: string;
  /**
   * The colour the area is filled with, when it is coloured by a value.
   *
   * Null when the area carries no value: it is then drawn in the neutral
   * land colour. A colour is never invented to fill a gap.
   */
  readonly fill: string | null;
  /** The opacity of the fill, when the area is filled. */
  readonly fillOpacity: number | null;
  /** The values shown in the pop-up. */
  readonly properties: Readonly<Record<string, string | number | boolean | null>>;
}

/** A raster grid: an extent and a resolution. */
export interface SpatialGrid {
  readonly id: string;
  readonly label: string;
  readonly layerId: string;
  readonly extent: SpatialExtent;
  /** The resolution in metres, or null when it is not established. */
  readonly resolutionM: number | null;
  /** The reference frame of the grid, e.g. "EPSG:4326". */
  readonly crs: string;
}

/** A layer of the map. */
export interface SpatialLayer {
  readonly id: string;
  readonly label: string;
  /** Whether the layer is shown. */
  readonly visible: boolean;
  readonly kind: 'point' | 'area' | 'grid';
  readonly description: string | null;
}

/** Everything the map draws. */
export interface SpatialScene {
  readonly layers: readonly SpatialLayer[];
  readonly points: readonly SpatialPoint[];
  readonly areas: readonly SpatialArea[];
  readonly grids: readonly SpatialGrid[];
  readonly provenance: readonly ApiRef[];
}

/** The action the map asks for when an entity is activated. */
export interface SpatialSelection {
  readonly kind: 'point' | 'area' | 'grid';
  readonly id: string;
}
