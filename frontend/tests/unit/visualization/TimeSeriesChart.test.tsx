/**
 * The time series chart.
 *
 * The scientific rules are enforced in a pure function, so they are tested
 * directly — and the rendered frame is tested for what a reader without the
 * canvas can still read.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { buildTimeSeriesSeries } from '@/components/visualization/TimeSeriesChart';
import type { PlottedSeries } from '@/components/visualization/TimeSeriesChart';
import { TimeSeriesChart } from '@/components/visualization/TimeSeriesChart';
import { readChartTokens } from '@/components/visualization/chartTheme';
import type { TimeSeries } from '@/types/visualization/timeSeries';

const tokens = readChartTokens(document.documentElement);

function series(overrides: Partial<TimeSeries> = {}): TimeSeries {
  return {
    id: 's1',
    variable: 'Discharge',
    unit: 'm³/s',
    frequency: 'daily',
    reference: { basis: 'civil-day', timeZone: 'Europe/Paris' },
    nature: 'observation',
    estimateFrom: null,
    forecastFrom: null,
    points: [
      { t: '2026-01-01', v: 10, lower: null, upper: null, missingReason: null, quality: 'declared' },
      { t: '2026-01-02', v: null, lower: null, upper: null, missingReason: 'not_measured', quality: 'unknown' },
      { t: '2026-01-03', v: 12, lower: null, upper: null, missingReason: null, quality: 'declared' },
    ],
    provenance: [],
    ...overrides,
  };
}

function plotted(entry: TimeSeries, hasInterval: boolean): PlottedSeries {
  return { series: entry, legendName: entry.variable, colour: '#0072b2', hasInterval };
}

describe('the time series series builder', () => {
  it('draws no uncertainty band when no interval is provided', () => {
    const built = buildTimeSeriesSeries([plotted(series(), false)], tokens, [], []);

    expect(built.some((entry) => String(entry['id']).endsWith('-band'))).toBe(false);
  });

  it('draws an uncertainty band when an interval is provided', () => {
    const withInterval = series({
      points: [
        { t: '2026-01-01', v: 10, lower: 9, upper: 11, missingReason: null, quality: 'declared' },
      ],
    });

    const built = buildTimeSeriesSeries([plotted(withInterval, true)], tokens, [], []);

    expect(built.some((entry) => String(entry['id']).endsWith('-band'))).toBe(true);
  });

  it('never connects the line across a gap', () => {
    const built = buildTimeSeriesSeries([plotted(series(), false)], tokens, [], []);
    const line = built.find((entry) => entry['id'] === 's1');

    expect(line?.['connectNulls']).toBe(false);
  });

  it('keeps an absent value absent, rather than turning it into a zero', () => {
    const built = buildTimeSeriesSeries([plotted(series(), false)], tokens, [], []);
    const line = built.find((entry) => entry['id'] === 's1');
    const data = line?.['data'] as [number, number | null][];

    expect(data[1]?.[1]).toBeNull();
  });

  it('distinguishes a forecast by its dash pattern', () => {
    const forecast = series({ nature: 'forecast' });

    const built = buildTimeSeriesSeries([plotted(forecast, false)], tokens, [], []);
    const line = built.find((entry) => entry['id'] === 's1');
    const lineStyle = line?.['lineStyle'] as { type?: string };

    expect(lineStyle.type).not.toBe('solid');
  });
});


/** The values are behind a disclosure: open it, the way a reader would. */
async function openTable(): Promise<void> {
  const summary = screen.getByText('Show the values as a table');
  await userEvent.click(summary);
}

describe('the time series chart', () => {
  it('names the figure and gives the chart an accessible name', () => {
    render(<TimeSeriesChart title="Demo discharge" series={[series()]} unit="m³/s" />);

    expect(screen.getByText('Demo discharge')).toBeVisible();
    expect(screen.getByRole('img', { name: /Demo discharge/ })).toBeVisible();
  });

  it('shows the values as a table, with an absence written as an absence', async () => {
    render(<TimeSeriesChart title="Demo discharge" series={[series()]} unit="m³/s" />);
    await openTable();

    expect(screen.getByText('no value')).toBeVisible();
    expect(screen.queryByText('0 m³/s')).toBeNull();
  });

  it('shows the unit of the values in the table', async () => {
    render(<TimeSeriesChart title="Demo discharge" series={[series()]} unit="m³/s" />);
    await openTable();

    expect(screen.getByText('10 m³/s')).toBeVisible();
  });
});
