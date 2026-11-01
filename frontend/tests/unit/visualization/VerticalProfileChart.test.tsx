/**
 * The vertical profile chart.
 *
 * The delicate part is the axis: a pressure is not a depth, and a model level
 * is not a distance. The component refuses to draw profiles that do not share
 * one, rather than putting them on a common axis.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { VerticalProfileChart } from '@/components/visualization/VerticalProfileChart';
import type { VerticalProfile } from '@/types/visualization/verticalProfile';

function profile(overrides: Partial<VerticalProfile> = {}): VerticalProfile {
  return {
    id: 'cast-a',
    name: 'Cast A',
    axis: { kind: 'pressure', unit: 'dbar', label: 'Pressure', direction: 'increasing-down' },
    variables: [{ key: 'temperature', label: 'Temperature', unit: '°C' }],
    points: [
      {
        coordinate: { kind: 'pressure', value: 0, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 18.4 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 41.8, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: null },
        validity: 'missing',
        quality: 'unknown',
        missingReason: 'not_measured',
      },
    ],
    provenance: [],
    ...overrides,
  };
}


/** The values are behind a disclosure: open it, the way a reader would. */
async function openTable(): Promise<void> {
  const summary = screen.getByText('Show the values as a table');
  await userEvent.click(summary);
}

describe('the vertical profile chart', () => {
  it('refuses to draw profiles that do not share a vertical axis', () => {
    const depth = profile({
      id: 'cast-b',
      name: 'Cast B',
      axis: { kind: 'depth', unit: 'm', label: 'Depth', direction: 'increasing-down' },
    });

    render(<VerticalProfileChart title="Demo casts" profiles={[profile(), depth]} />);

    expect(screen.getByText(/a pressure is not a depth/)).toBeVisible();
  });

  it('keeps an absent value absent in the table', async () => {
    render(<VerticalProfileChart title="Demo casts" profiles={[profile()]} />);
    await openTable();

    expect(screen.getByText('no value')).toBeVisible();
  });

  it('shows the vertical unit of the levels', async () => {
    render(<VerticalProfileChart title="Demo casts" profiles={[profile()]} />);
    await openTable();

    expect(screen.getAllByText(/dbar/).length).toBeGreaterThan(0);
  });

  it('shows the quality the source declared', async () => {
    render(<VerticalProfileChart title="Demo casts" profiles={[profile()]} />);
    await openTable();

    expect(screen.getAllByText('declared').length).toBeGreaterThan(0);
    expect(screen.getAllByText('unknown').length).toBeGreaterThan(0);
  });
});
