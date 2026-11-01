/**
 * The world map of the explorer.
 *
 * The map colours a country by the **highest status its own missions
 * reached**. A region-wide mission never colours a country: the European
 * surface products cover Germany without Germany having a mission, and that
 * coverage is not a German status.
 *
 * The boundaries come from the application's own origin: the application
 * fetches no third-party resource at runtime.
 */
import { useMemo } from 'react';

import { SpatialMap } from '@/components/visualization/SpatialMap';
import { countryRank } from '@/features/explorer/filters';
import { ISO_NUMERIC_TO_ALPHA } from '@/features/explorer/countryCodes';
import type { ExplorerFilters } from '@/features/explorer/filters';
import type { GeoJsonFeature } from '@/features/explorer/useBoundaries';
import type { ApiAsset, ApiManifest } from '@/types/api/manifest';
import type { SpatialArea, SpatialPoint, SpatialScene } from '@/types/visualization/spatial';

/** The Europe view the map opens on. */
export const EUROPE_BOUNDS: readonly (readonly [number, number])[] = [
  [35, -12],
  [70, 35],
];

/**
 * A ring that crosses the antimeridian spans more than 180° of longitude,
 * and a map draws it across the whole world. Shifting its western points by
 * 360° keeps it one shape.
 */
function unwrapRing(
  ring: readonly (readonly [number, number])[],
): readonly (readonly [number, number])[] {
  const longitudes = ring.map(([longitude]) => longitude);
  if (Math.max(...longitudes) - Math.min(...longitudes) <= 180) {
    return ring;
  }
  return ring.map(([longitude, latitude]) => [longitude < 0 ? longitude + 360 : longitude, latitude]);
}

function toRing(raw: readonly number[]): readonly [number, number] {
  return [raw[0] ?? 0, raw[1] ?? 0];
}

function toAreas(
  features: readonly GeoJsonFeature[],
  manifest: ApiManifest,
  filters: ExplorerFilters,
): SpatialArea[] {
  const areas: SpatialArea[] = [];

  for (const feature of features) {
    const numeric = String(feature.id ?? '');
    const alpha = ISO_NUMERIC_TO_ALPHA[numeric];
    if (alpha === undefined) {
      continue;
    }

    const rings: readonly (readonly (readonly [number, number])[])[] =
      feature.geometry.type === 'Polygon'
        ? feature.geometry.coordinates.map((ring) => unwrapRing(ring.map(toRing)))
        : feature.geometry.coordinates.flatMap((polygon) =>
            polygon.map((ring) => unwrapRing(ring.map(toRing))),
          );

    const rank = countryRank(alpha, manifest.missions, filters, manifest.statuses);

    areas.push({
      id: alpha,
      label: feature.properties?.name ?? alpha,
      rings,
      layerId: 'countries',
      fill: `var(--science-status-${rank})`,
      fillOpacity: 1,
      properties: {
        country: alpha,
        status:
          manifest.statuses.find((entry) => entry.rank === rank)?.status ?? 'not covered',
      },
    });
  }

  return areas;
}

function toPoints(assets: readonly ApiAsset[]): SpatialPoint[] {
  return assets
    .filter((asset) => asset.point !== null)
    .map((asset) => ({
      id: asset.asset_id,
      label: asset.name,
      position: asset.point as readonly [number, number],
      kind: asset.kind,
      layerId: 'stations',
      properties: {
        source: asset.source_id,
        domain: asset.domain_id,
        country: asset.country,
      },
    }));
}

export interface WorldMapProps {
  readonly manifest: ApiManifest;
  readonly filters: ExplorerFilters;
  readonly features: readonly GeoJsonFeature[];
  readonly selectedId?: string | null;
  readonly onSelectCountry?: (code: string) => void;
  readonly onSelectAsset?: (assetId: string) => void;
  readonly legend?: React.ReactNode;
}

export function WorldMap({
  manifest,
  filters,
  features,
  selectedId = null,
  onSelectCountry,
  onSelectAsset,
  legend,
}: WorldMapProps) {
  const scene = useMemo<SpatialScene>(() => {
    const areas = toAreas(features, manifest, filters);
    const stations = manifest.assets.filter(
      (asset) => asset.kind === 'station' && asset.point !== null,
    );

    return {
      layers: [
        {
          id: 'countries',
          label: 'Countries',
          visible: true,
          kind: 'area',
          description: 'Coloured by the highest status the country’s own missions reached.',
        },
        {
          id: 'stations',
          label: 'Stations',
          visible: true,
          kind: 'point',
          description: 'The physical assets a mission actually touched.',
        },
      ],
      areas,
      points: toPoints(stations),
      grids: [],
      provenance: [],
    };
  }, [features, manifest, filters]);

  return (
    <SpatialMap
      scene={scene}
      title="Where the missions reached"
      description="A country is coloured by the status its own missions earned. Region-wide coverage is not a national status."
      height={600}
      fitTo={{ label: 'Europe', bounds: EUROPE_BOUNDS }}
      selectedId={selectedId}
      onSelect={(selection) => {
        if (selection === null) {
          return;
        }
        if (selection.kind === 'area') {
          onSelectCountry?.(selection.id);
        } else if (selection.kind === 'point') {
          onSelectAsset?.(selection.id);
        }
      }}
      onNavigate={(selection) => {
        if (selection.kind === 'area') {
          onSelectCountry?.(selection.id);
        } else if (selection.kind === 'point') {
          onSelectAsset?.(selection.id);
        }
      }}
      legend={legend}
    />
  );
}
