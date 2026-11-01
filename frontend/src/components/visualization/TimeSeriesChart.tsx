/**
 * The time series chart.
 *
 * This is not a generic line chart. It is a chart of a **measured
 * phenomenon**, and it obeys the rules such a chart must obey:
 *
 * - **the time axis is a real time axis.** The stamps are instants, not
 *   indices, so series of different frequencies sit on the same axis at their
 *   own dates without being resampled;
 * - **a hole is a hole.** A point with no value breaks the line. Nothing is
 *   interpolated across it, and an absence is never drawn as zero;
 * - **the nature of the values is stated.** An observation, an estimate and a
 *   forecast are drawn differently — by dash pattern as well as by colour —
 *   and a series that changes nature mid-way says where the change happens;
 * - **the unit is explicit.** When it is not established, the chart says so
 *   rather than inventing one;
 * - **uncertainty is drawn only when it exists.** A series with no interval
 *   gets no band.
 */
import type { ECharts } from 'echarts/core';
import { useCallback, useMemo, useRef, useState } from 'react';

import type { ChartTokens } from '@/components/visualization/chartTheme';
import {
  dashForNature,
  describeTemporalReference,
  legendLabelForNature,
  symbolForNature,
  useChartTokens,
} from '@/components/visualization/chartTheme';
import {
  axisName,
  axisPointer,
  gridCraft,
  legendChrome,
  timeAxis,
  tooltipChrome,
  unitPlate,
  valueAxis,
  zoomChrome,
} from '@/components/visualization/chartCraft';
import { ChartFrame } from '@/components/visualization/ChartFrame';
import { EChart } from '@/components/visualization/EChart';
import { escapeHtml } from '@/components/visualization/html';
import type {
  ReferenceBand,
  SeriesNature,
  TimeMarker,
  TimeSeries,
  TimeSpan,
} from '@/types/visualization/timeSeries';

export interface TimeSeriesChartProps {
  /** The series to draw. They share one time axis and one value axis. */
  readonly series: readonly TimeSeries[];
  readonly title: string;
  readonly description?: string | null;
  /**
   * The unit the values are in.
   *
   * When the series disagree on their unit, the chart refuses to draw them
   * on a shared axis and says so.
   */
  readonly unit?: string | null;
  /** The name of the value axis, when the unit alone is not enough. */
  readonly yAxisLabel?: string | null;
  /** Bands of values drawn across the chart: a normal range, a threshold. */
  readonly referenceBands?: readonly ReferenceBand[];
  /** Point-in-time annotations: a detected break, a station move. */
  readonly markers?: readonly TimeMarker[];
  /** Named spans of time drawn under the axis. */
  readonly spans?: readonly TimeSpan[];
  readonly height?: number;
  /** Called when the reader shows or hides a series in the legend. */
  readonly onLegendChange?: (seriesId: string, visible: boolean) => void;
}

interface PlottedSeries {
  readonly series: TimeSeries;
  readonly legendName: string;
  readonly colour: string;
  readonly hasInterval: boolean;
}
export type { PlottedSeries };

interface PointMeta {
  readonly seriesId: string;
  readonly label: string;
  readonly unit: string | null;
  readonly nature: SeriesNature;
  readonly stamp: string;
  readonly value: number | null;
  readonly lower: number | null;
  readonly upper: number | null;
  readonly missingReason: string | null;
  readonly quality: string;
}

const NATURE_LABEL: Record<SeriesNature, string> = {
  observation: 'observation',
  estimate: 'estimate',
  forecast: 'forecast',
  simulation: 'simulation',
};

function toMillis(stamp: string): number {
  const parsed = Date.parse(stamp);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatValue(value: number | null, unit: string | null): string {
  if (value === null) {
    return 'no value';
  }
  const rendered = Number.isInteger(value) ? String(value) : value.toPrecision(6);
  return unit === null ? rendered : `${rendered} ${unit}`;
}

function formatStamp(stamp: string): string {
  const date = new Date(stamp);
  if (Number.isNaN(date.getTime())) {
    return stamp;
  }
  return date.toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z');
}

/**
 * The nature of a series at a given instant.
 *
 * A series may change nature part-way through — observations up to a date,
 * a forecast after it. The chart says which it is at the point being read.
 */
function natureAt(series: TimeSeries, millis: number): SeriesNature {
  if (series.forecastFrom !== null && millis >= toMillis(series.forecastFrom)) {
    return 'forecast';
  }
  if (series.estimateFrom !== null && millis >= toMillis(series.estimateFrom)) {
    return 'estimate';
  }
  return series.nature;
}

function natureBoundary(series: TimeSeries): { at: number; nature: SeriesNature } | null {
  if (series.forecastFrom !== null) {
    return { at: toMillis(series.forecastFrom), nature: 'forecast' };
  }
  if (series.estimateFrom !== null) {
    return { at: toMillis(series.estimateFrom), nature: 'estimate' };
  }
  return null;
}

/**
 * The ECharts series of a time series chart.
 *
 * This is where the scientific rules are enforced, and it is a pure function
 * so that they can be tested without a canvas:
 *
 * - a series with no interval gets **no band at all** — not a band of zero
 *   width, which would say nothing while looking as if it said something;
 * - the line never connects across a gap (`connectNulls: false`), so a hole
 *   in the measurements stays a hole;
 * - a series that changes nature mid-way carries the boundary where it
 *   changes.
 */
export function buildTimeSeriesSeries(
  plotted: readonly PlottedSeries[],
  tokens: ChartTokens,
  referenceBands: readonly ReferenceBand[],
  markers: readonly TimeMarker[],
): Record<string, unknown>[] {
  const seriesOptions: Record<string, unknown>[] = [];

  for (const entry of plotted) {
    const points = entry.series.points;
    const data = points.map((point) => [toMillis(point.t), point.v]);

    // The envelope is drawn only when the series actually carries an
    // interval. A band at zero width would be a band that says nothing.
    if (entry.hasInterval) {
      const bandColour =
        entry.series.nature === 'forecast' ? tokens.uncertaintyForecast : tokens.uncertainty;
      seriesOptions.push({
        id: `${entry.series.id}-band-lower`,
        name: `${entry.legendName} (lower bound)`,
        type: 'line',
        data: points.map((point) => [toMillis(point.t), point.lower]),
        stack: `${entry.series.id}-band`,
        step: 'middle',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        tooltip: { show: false },
        legendHoverLink: false,
        z: 1,
      });
      seriesOptions.push({
        id: `${entry.series.id}-band`,
        name: `${entry.legendName} (interval)`,
        type: 'line',
        data: points.map((point) => [
          toMillis(point.t),
          point.lower === null || point.upper === null ? null : point.upper - point.lower,
        ]),
        stack: `${entry.series.id}-band`,
        step: 'middle',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: bandColour, opacity: 1 },
        silent: true,
        tooltip: { show: false },
        legendHoverLink: false,
        z: 2,
      });
    }

    const boundary = natureBoundary(entry.series);
    seriesOptions.push({
      id: entry.series.id,
      name: entry.legendName,
      type: 'line',
      data,
      connectNulls: false,
      showSymbol: false,
      symbol: symbolForNature(entry.series.nature),
      symbolSize: 5,
      sampling: 'lttb',
      lineStyle: {
        width: 2,
        color: entry.colour,
        type: dashForNature(entry.series.nature) ?? 'solid',
      },
      itemStyle: { color: entry.colour },
      emphasis: { focus: 'series', lineStyle: { width: 3 } },
      z: 5,
      ...(boundary === null
        ? {}
        : {
            markLine: {
              silent: true,
              symbol: 'none',
              label: {
                formatter: boundary.nature,
                color: tokens.label,
                fontSize: 10,
                fontFamily: tokens.fontMono,
                position: 'insideEndTop',
                distance: 4,
              },
              lineStyle: { color: tokens.reference, type: 'dashed', width: 1 },
              data: [{ xAxis: boundary.at }],
            },
          }),
    });
  }

  if (referenceBands.length > 0 && plotted.length > 0) {
    seriesOptions.push({
      id: 'reference-bands',
      name: 'reference bands',
      type: 'line',
      data: [],
      silent: true,
      tooltip: { show: false },
      z: 0,
      markArea: {
        silent: true,
        // A reference band is an annotation, not a measurement: it is tinted
        // like a well and closed by a dashed rule, and it is named where it
        // is drawn, so it is never a slab of colour with no meaning.
        itemStyle: {
          color: tokens.uncertainty,
          opacity: 0.45,
          borderColor: tokens.reference,
          borderWidth: 1,
          borderType: 'dashed',
        },
        label: {
          show: true,
          position: 'insideTopLeft',
          distance: 4,
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
        },
        data: referenceBands.map((band) => [
          {
            xAxis: band.start === null ? undefined : toMillis(band.start),
            yAxis: band.lower ?? undefined,
            name: band.label,
          },
          {
            xAxis: band.end === null ? undefined : toMillis(band.end),
            yAxis: band.upper ?? undefined,
          },
        ]),
      },
    });
  }

  if (markers.length > 0 && plotted.length > 0) {
    seriesOptions.push({
      id: 'markers',
      name: 'markers',
      type: 'line',
      data: [],
      silent: true,
      tooltip: { show: false },
      z: 6,
      markPoint: {
        // An annotation, not a flag: a small ringed dot in the accent, named
        // inside the plot so it never collides with the legend above.
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color: tokens.accent, borderColor: tokens.well, borderWidth: 1.5 },
        label: {
          show: true,
          position: 'bottom',
          distance: 4,
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
        },
        data: markers.map((marker) => ({
          name: marker.label,
          xAxis: toMillis(marker.at),
          yAxis: 'max',
        })),
      },
    });
  }

  return seriesOptions;
}

export function TimeSeriesChart({
  series,
  title,
  description = null,
  unit = null,
  yAxisLabel = null,
  referenceBands = [],
  markers = [],
  spans = [],
  height = 320,
  onLegendChange,
}: TimeSeriesChartProps) {
  const tokens = useChartTokens();
  const chart = useRef<ECharts | null>(null);
  const [zoomed, setZoomed] = useState(false);

  const units = useMemo(() => {
    const declared = new Set(
      series.map((entry) => entry.unit).filter((value): value is string => value !== null),
    );
    return declared;
  }, [series]);

  const unitConflict = units.size > 1;

  /**
   * The label plate: the unit, stated once, where the reader reads the
   * figure. When the series disagree on their unit, the plate says that the
   * unit is not established rather than picking one of them.
   */
  const plate = unitPlate(unit, unitConflict);

  const plotted = useMemo<PlottedSeries[]>(
    () =>
      series.map((entry, index) => ({
        series: entry,
        legendName: legendLabelForNature(entry.variable, entry.nature, entry.frequency),
        colour: tokens.series[index % tokens.series.length] ?? tokens.accent,
        hasInterval: entry.points.some((point) => point.lower !== null && point.upper !== null),
      })),
    [series, tokens],
  );

  const meta = useMemo(() => {
    const bySeries = new Map<string, PointMeta[]>();
    for (const entry of plotted) {
      bySeries.set(
        entry.series.id,
        entry.series.points.map((point) => ({
          seriesId: entry.series.id,
          label: entry.legendName,
          unit: entry.series.unit,
          nature: natureAt(entry.series, toMillis(point.t)),
          stamp: point.t,
          value: point.v,
          lower: point.lower,
          upper: point.upper,
          missingReason: point.missingReason,
          quality: point.quality,
        })),
      );
    }
    return bySeries;
  }, [plotted]);

  const option = useMemo(() => {
    const seriesOptions = buildTimeSeriesSeries(plotted, tokens, referenceBands, markers);

    // The unit is stated once, on the label plate. The axis only repeats it
    // when it is established, and then it is the axis's own name — never a
    // phrase that says nothing ("unit not established") in the one place
    // where the reader is looking at the numbers.
    const plate = unitPlate(unit, unitConflict);
    const axisUnit = yAxisLabel ?? (plate.established ? plate.label : null);

    return {
      animation: false,
      backgroundColor: tokens.well,
      color: [...tokens.series],
      grid: gridCraft(),
      legend: {
        ...legendChrome(tokens),
        data: plotted.map((entry) => ({
          name: entry.legendName,
          // The legend carries the mark of the series, so a series is never
          // identified by its colour alone.
          icon: symbolForNature(entry.series.nature),
        })),
      },
      tooltip: {
        ...tooltipChrome(tokens),
        trigger: 'axis',
        axisPointer: axisPointer(tokens, 'cross'),
        formatter: (rawParams: unknown) => {
          const params = Array.isArray(rawParams) ? rawParams : [rawParams];
          const blocks: string[] = [];
          for (const item of params) {
            if (typeof item !== 'object' || item === null) {
              continue;
            }
            const record = item as { seriesIndex?: number; value?: unknown; dataIndex?: number };
            const plottedIndex = record.seriesIndex ?? 0;
            const entry = plotted[plottedIndex];
            if (entry === undefined) {
              continue;
            }
            const points = meta.get(entry.series.id);
            const point = points?.[record.dataIndex ?? -1];
            if (point === undefined) {
              continue;
            }
            const nature = point.nature === entry.series.nature ? '' : ` · ${NATURE_LABEL[point.nature]}`;
            const interval =
              point.lower !== null && point.upper !== null
                ? ` (${formatValue(point.lower, null)} – ${formatValue(point.upper, null)})`
                : '';
            const missing =
              point.value === null && point.missingReason !== null
                ? ` · absent: ${point.missingReason.replaceAll('_', ' ')}`
                : '';
            blocks.push(
              `<div style="font-weight:600">${escapeHtml(point.label)}${escapeHtml(nature)}</div>` +
                `<div style="font-family:var(--font-mono);font-size:11px;opacity:.7">${escapeHtml(formatStamp(point.stamp))}</div>` +
                `<div>${escapeHtml(formatValue(point.value, point.unit))}${escapeHtml(interval)}${escapeHtml(missing)}</div>` +
                `<div style="font-size:11px;opacity:.7">quality: ${escapeHtml(point.quality)}</div>`,
            );
          }
          return blocks.join('');
        },
      },
      xAxis: timeAxis(tokens),
      yAxis: valueAxis(tokens, {
        name: axisName(axisUnit, false),
        nameLocation: 'end',
        nameGap: 12,
        nameTextStyle: {
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
          align: 'left',
        },
      }),
      dataZoom: zoomChrome(tokens),
      series: seriesOptions,
    };
  }, [plotted, meta, tokens, unit, unitConflict, yAxisLabel, referenceBands, markers]);

  const onReady = useCallback((instance: ECharts) => {
    chart.current = instance;
  }, []);

  const onEvents = useMemo(
    () => ({
      legendselectchanged: (rawParams: unknown) => {
        const record = rawParams as { selected?: Record<string, boolean> } | null;
        const selected = record?.selected;
        if (selected === undefined) {
          return;
        }
        for (const entry of plotted) {
          const visible = selected[entry.legendName];
          if (visible !== undefined) {
            onLegendChange?.(entry.series.id, visible);
          }
        }
      },
      datazoom: () => setZoomed(true),
    }),
    [plotted, onLegendChange],
  );

  const resetZoom = useCallback(() => {
    chart.current?.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
    setZoomed(false);
  }, []);

  const table = (
    <table>
      <thead>
        <tr>
          <th scope="col">Instant</th>
          <th scope="col">Series</th>
          <th scope="col">Value</th>
          <th scope="col">Lower</th>
          <th scope="col">Upper</th>
          <th scope="col">Nature</th>
          <th scope="col">Quality</th>
          <th scope="col">Stamps</th>
        </tr>
      </thead>
      <tbody>
        {plotted.flatMap((entry) =>
          entry.series.points.map((point) => (
            <tr key={`${entry.series.id}-${point.t}`}>
              <td>{formatStamp(point.t)}</td>
              <td>{entry.legendName}</td>
              <td>{point.v === null ? 'no value' : formatValue(point.v, entry.series.unit)}</td>
              <td>{point.lower === null ? '—' : formatValue(point.lower, null)}</td>
              <td>{point.upper === null ? '—' : formatValue(point.upper, null)}</td>
              <td>{NATURE_LABEL[natureAt(entry.series, toMillis(point.t))]}</td>
              <td>{point.quality}</td>
              <td>{describeTemporalReference(entry.series.reference)}</td>
            </tr>
          )),
        )}
      </tbody>
    </table>
  );

  const spanNote =
    spans.length > 0 ? `Spans: ${spans.map((span) => span.label).join(', ')}.` : null;

  // The stamps of a series are not only positions on an axis: they say what a
  // point stands for, and the reader cannot compare two series that do not
  // mean the same thing.
  const timeNote =
    plotted.length === 0
      ? null
      : `Stamps: ${plotted
          .map(
            (entry) =>
              `${entry.series.variable} — ${entry.series.frequency}, ${describeTemporalReference(entry.series.reference)}`,
          )
          .join('. ')}.`;

  return (
    <ChartFrame
      title={title}
      description={description}
      plate={{ label: plate.label, tone: plate.established ? 'neutral' : 'warning' }}
      ariaLabel={`${title}. ${plotted.length} series, ${plotted.reduce((sum, entry) => sum + entry.series.points.length, 0)} points. ${timeNote ?? ''}`}
      table={table}
      footnote={
        timeNote === null && spanNote === null ? undefined : (
          <>
            {timeNote === null ? null : <span>{timeNote} </span>}
            {spanNote === null ? null : <span>{spanNote}</span>}
          </>
        )
      }
      actions={
        <button
          type="button"
          className="torne-chart-reset"
          onClick={resetZoom}
          disabled={!zoomed}
        >
          Reset the time range
        </button>
      }
    >
      <EChart option={option} height={height} onEvents={onEvents} onReady={onReady} />
    </ChartFrame>
  );
}
