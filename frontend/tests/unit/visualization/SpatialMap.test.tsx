/**
 * The spatial map.
 *
 * The map is not the only way to read it: the component also renders the
 * layers and the entities as a list, so the content survives a browser
 * without a canvas.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SpatialMap } from '@/components/visualization/SpatialMap';
import type { SpatialScene } from '@/types/visualization/spatial';

const scene: SpatialScene = {
  layers: [
    { id: 'stations', label: 'Demo stations', visible: true, kind: 'point', description: 'Invented.' },
    { id: 'basin', label: 'Demo basin', visible: true, kind: 'area', description: null },
  ],
  points: [
    {
      id: 'alpha',
      label: 'Demo station Alpha',
      position: [3.05, 50.57],
      kind: 'station',
      layerId: 'stations',
      properties: { country: 'FR' },
    },
  ],
  areas: [
    {
      id: 'basin-1',
      label: 'Demo basin',
      layerId: 'basin',
      rings: [
        [
          [1.4, 49.6],
          [4.6, 49.6],
          [4.6, 51.4],
          [1.4, 51.4],
          [1.4, 49.6],
        ],
      ],
      fill: 'var(--series-3)',
      fillOpacity: 0.35,
      properties: {},
    },
  ],
  grids: [],
  provenance: [],
};

describe('the spatial map', () => {
  it('lists the layers it draws', () => {
    render(<SpatialMap scene={scene} title="Demo scene" />);

    expect(screen.getByRole('region', { name: 'Layers' })).toBeVisible();
    expect(screen.getAllByText('Demo stations').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Demo basin').length).toBeGreaterThan(0);
  });

  it('lists the entities it draws', () => {
    render(<SpatialMap scene={scene} title="Demo scene" />);

    expect(screen.getByRole('region', { name: 'Entities' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Demo station Alpha' })).toBeVisible();
  });

  it('reports the selection of an entity', () => {
    const seen: (string | null)[] = [];

    render(
      <SpatialMap
        scene={scene}
        title="Demo scene"
        onSelect={(selection) => seen.push(selection?.id ?? null)}
      />,
    );

    screen.getByRole('button', { name: 'Demo station Alpha' }).click();

    expect(seen).toEqual(['alpha']);
  });

  it('gives the map an accessible name', () => {
    render(<SpatialMap scene={scene} title="Demo scene" />);

    expect(screen.getByRole('application', { name: 'Demo scene' })).toBeVisible();
  });

  it('shows the legend it is given', () => {
    render(
      <SpatialMap
        scene={scene}
        title="Demo scene"
        legend={<span>What the colours mean</span>}
      />,
    );

    expect(screen.getByText('What the colours mean')).toBeVisible();
  });
});
