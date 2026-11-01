/**
 * The country boundaries.
 *
 * They are served from the application's own origin: the explorer fetches no
 * third-party resource at runtime.
 */
import { useEffect, useState } from 'react';

export interface GeoJsonFeature {
  readonly id?: string | number;
  readonly properties?: { readonly name?: string };
  readonly geometry:
    | { readonly type: 'Polygon'; readonly coordinates: number[][][] }
    | { readonly type: 'MultiPolygon'; readonly coordinates: number[][][][] };
}

export interface BoundariesState {
  readonly features: readonly GeoJsonFeature[];
  readonly loading: boolean;
  readonly failure: string | null;
}

export function useBoundaries(): BoundariesState {
  const [state, setState] = useState<BoundariesState>({
    features: [],
    loading: true,
    failure: null,
  });

  useEffect(() => {
    let active = true;

    fetch('/data/countries-50m.geo.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json() as Promise<{
          readonly features: readonly GeoJsonFeature[];
        }>;
      })
      .then((collection) => {
        if (active) {
          setState({ features: collection.features, loading: false, failure: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            features: [],
            loading: false,
            failure: error instanceof Error ? error.message : 'the boundaries could not be loaded',
          });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return state;
}
