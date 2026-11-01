/**
 * The uncertainty chart.
 *
 * The rule that gives the component its meaning: no band without
 * uncertainty.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { readChartTokens } from '@/components/visualization/chartTheme';
import { UncertaintyChart, buildUncertaintySeries } from '@/components/visualization/UncertaintyChart';
import type { TimeSeries } from '@/types/visualization/timeSeries';

const tokens = readChartTokens(document.documentElement);

function series(overrides: Partial<TimeSeries> = {}): TimeSeries {
  return {
    id: 's1',
    variable: 'Discharge',
    unit: 'm³/s',
    frequency: 'daily',
    reference: { basis: 'instant', timeZone: null },
    nature: 'observation',
    estimateFrom: null,
    forecastFrom: null,
    points: [
      { t: '2026-01-01', v: 10, lower: null, upper: null, missingReason: null, quality: 'declared' },
    ],
    provenance: [],
    ...overrides,
  };
}

describe('the uncertainty series builder', () => {
  it('draws no band when the series carries no interval', () => {
    const built = buildUncertaintySeries(
      [{ series: series(), legendName: 'Discharge', colour: '#0072b2', hasInterval: false }],
      tokens,
    );

    expect(built.some((entry) => String(entry['id']).endsWith('-band'))).toBe(false);
  });

  it('draws the envelope when the series carries an interval', () => {
    const withInterval = series({
      points: [
        { t: '2026-01-01', v: 10, lower: 9, upper: 11, missingReason: null, quality: 'declared' },
      ],
    });

    const built = buildUncertaintySeries(
      [{ series: withInterval, legendName: 'Discharge', colour: '#0072b2', hasInterval: true }],
      tokens,
    );

    expect(built.some((entry) => String(entry['id']) === 's1-band')).toBe(true);
    expect(built.some((entry) => String(entry['id']) === 's1-band-lower')).toBe(true);
  });

  it('never connects the line across a gap', () => {
    const built = buildUncertaintySeries(
      [{ series: series(), legendName: 'Discharge', colour: '#0072b2', hasInterval: false }],
      tokens,
    );
    const line = built.find((entry) => entry['id'] === 's1');

    expect(line?.['connectNulls']).toBe(false);
  });
});


/** The values are behind a disclosure: open it, the way a reader would. */
async function openTable(): Promise<void> {
  const summary = screen.getByText('Show the values as a table');
  await userEvent.click(summary);
}

describe('the uncertainty chart', () => {
  it('says when no band is drawn, and why', () => {
    render(<UncertaintyChart title="Demo" series={[series()]} unit="m³/s" />);

    expect(screen.getByText(/No uncertainty band is drawn/)).toBeVisible();
  });

  it('keeps an absent value absent in the table', async () => {
    const withGap = series({
      points: [
        { t: '2026-01-01', v: 10, lower: null, upper: null, missingReason: null, quality: 'declared' },
        { t: '2026-01-02', v: null, lower: null, upper: null, missingReason: 'not_measured', quality: 'unknown' },
      ],
    });

    render(<UncertaintyChart title="Demo" series={[withGap]} unit="m³/s" />);
    await openTable();

    expect(screen.getByText('no value')).toBeVisible();
  });
});
