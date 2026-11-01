/**
 * The country boundaries.
 *
 * They are served from the application's own origin: the explorer fetches no
 * third-party resource at runtime. They are read once for the whole
 * application, like every other resource.
 */
import { BOUNDARIES } from '@/services/api/registry';
import type { GeoJsonCollection, GeoJsonFeature } from '@/services/api/registry';
import { useResource } from '@/services/api/useResource';

export type { GeoJsonFeature } from '@/services/api/registry';

export interface BoundariesState {
  readonly features: readonly GeoJsonFeature[];
  readonly loading: boolean;
  /** Set when the boundaries could not be read and none are on screen. */
  readonly failure: string | null;
  /** Set when the boundaries could not be re-read but some are on screen. */
  readonly stale: string | null;
}

export function useBoundaries(): BoundariesState {
  const { data, error, loading } = useResource<GeoJsonCollection>(BOUNDARIES);
  const features = data?.features ?? [];

  return {
    features,
    loading,
    failure: features.length === 0 ? error : null,
    stale: features.length > 0 ? error : null,
  };
}
