/**
 * The coverage timeline.
 *
 * The gap is the point of the component: a timeline that hid the gaps would
 * claim a continuity the data does not have.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { CoverageTimeline, buildCoverageBars, GAP_SHAPE, KIND_STYLE } from '@/components/visualization/CoverageTimeline';
import type { CoverageKind } from '@/types/visualization/coverage';
import type { CoveragePeriod } from '@/types/visualization/coverage';

const MIN = Date.UTC(2020, 0, 1);
const MAX = Date.UTC(2026, 0, 1);

function period(overrides: Partial<CoveragePeriod> = {}): CoveragePeriod {
  return {
    id: 'p1',
    subject: 'Demo station',
    kind: 'observed',
    start: '2024-01-01',
    end: '2024-12-31',
    open: false,
    provenance: [],
    ...overrides,
  };
}

describe('the coverage bars builder', () => {
  it('draws a gap between two periods of the same subject', () => {
    const { bars } = buildCoverageBars(
      [
        period({ id: 'p1', start: '2024-01-01', end: '2024-06-30' }),
        period({ id: 'p2', start: '2024-09-01', end: '2024-12-31' }),
      ],
      MIN,
      MAX,
    );

    expect(bars.filter((bar) => bar.kind === 'gap')).toHaveLength(1);
  });

  it('draws no gap between two contiguous periods', () => {
    const { bars } = buildCoverageBars(
      [
        period({ id: 'p1', start: '2024-01-01', end: '2024-06-30' }),
        period({ id: 'p2', start: '2024-06-30', end: '2024-12-31' }),
      ],
      MIN,
      MAX,
    );

    expect(bars.filter((bar) => bar.kind === 'gap')).toHaveLength(0);
  });

  it('runs an open period to the edge of the axis and marks it as open', () => {
    const { bars } = buildCoverageBars(
      [period({ id: 'p1', start: '2024-01-01', end: null, open: true })],
      MIN,
      MAX,
    );
    const bar = bars.find((entry) => entry.kind === 'observed');

    expect(bar?.open).toBe(true);
    expect(bar?.end).toBe(MAX);
  });

  it('leaves an unknown end unknown rather than closing it', () => {
    const { bars } = buildCoverageBars(
      [period({ id: 'p1', start: '2024-01-01', end: null, open: false })],
      MIN,
      MAX,
    );
    const bar = bars.find((entry) => entry.kind === 'observed');

    expect(bar?.unknownEnd).toBe(true);
    expect(bar?.open).toBe(false);
  });

  it('gives each subject its own row', () => {
    const { subjects } = buildCoverageBars(
      [
        period({ id: 'p1', subject: 'Alpha' }),
        period({ id: 'p2', subject: 'Beta' }),
      ],
      MIN,
      MAX,
    );

    expect(subjects).toEqual(['Alpha', 'Beta']);
  });
});


describe('the kinds of the coverage timeline', () => {
  it('gives every kind a swatch of its own, so none is carried by colour alone', () => {
    const shapes = (Object.keys(KIND_STYLE) as CoverageKind[]).map((kind) => KIND_STYLE[kind].shape);

    expect(new Set(shapes).size).toBe(shapes.length);
  });

  it('shows the gap as an empty swatch, not a filled one', () => {
    // A gap is the absence of a period. A filled swatch would show a pale
    // period where there is none.
    expect(GAP_SHAPE).toBe('empty');
  });
});

/** The values are behind a disclosure: open it, the way a reader would. */
async function openTable(): Promise<void> {
  const summary = screen.getByText('Show the values as a table');
  await userEvent.click(summary);
}

describe('the coverage timeline', () => {
  it('names the kinds in its legend', () => {
    render(<CoverageTimeline title="Demo coverage" periods={[period()]} />);

    expect(screen.getAllByText('observed').length).toBeGreaterThan(0);
    expect(screen.getAllByText('estimated').length).toBeGreaterThan(0);
    expect(screen.getAllByText('published').length).toBeGreaterThan(0);
    expect(screen.getAllByText('revision').length).toBeGreaterThan(0);
    expect(screen.getAllByText('gap').length).toBeGreaterThan(0);
  });

  it('writes an open period as still open, and an unknown end as not established', async () => {
    render(
      <CoverageTimeline
        title="Demo coverage"
        periods={[
          period({ id: 'p1', subject: 'Alpha', start: '2024-01-01', end: null, open: true }),
          period({ id: 'p2', subject: 'Beta', start: '2024-01-01', end: null, open: false }),
        ]}
      />,
    );
    await openTable();

    expect(screen.getByText('still open')).toBeVisible();
    expect(screen.getByText('not established')).toBeVisible();
  });

  it('answers an availability question only when it is known', () => {
    render(
      <CoverageTimeline
        title="Demo coverage"
        periods={[period()]}
        availableAt="2024-06-01"
        availability={[
          { subject: 'Demo station', at: '2024-06-01', available: null, provenance: [] },
        ]}
      />,
    );

    expect(screen.getByText(/not known/)).toBeVisible();
  });
});
