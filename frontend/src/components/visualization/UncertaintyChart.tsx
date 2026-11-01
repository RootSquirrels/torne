/**
 * The uncertainty chart.
 *
 * It shows an estimate with the uncertainty that qualifies it: a central
 * interval, quantiles, an envelope, and the separation between what was
 * observed, what was estimated and what is forecast.
 *
 * The rule that gives the component its meaning:
 *
 * - **no band without uncertainty.** When no point of a series carries an
 *   interval, the series gets **no band at all**. A band of zero width would
 *   look like a statement while saying nothing, and a band drawn at the
 *   central value would be a lie about the precision of the estimate.
 *
 * The other rules are the ones the whole system obeys: a hole in the
 * measurements stays a hole, the nature of the values is carried by the dash
 * pattern as well as by the legend text, and the unit is explicit or declared
 * unknown.
 */
import { useMemo } from 'react';

import { ChartFrame } from '@/components/visualization/ChartFrame';
import { EChart } from '@/components/visualization/EChart';
import type { ChartOption } from '@/components/visualization/EChart';
import { escapeHtml } from '@/components/visualization/html';
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
} from '@/components/visualization/chartCraft';
import type { ChartTokens } from '@/components/visualization/chartTheme';
import type { SeriesNature, TimeSeries } from '@/types/visualization/timeSeries';

export interface UncertaintyChartProps {
  /** The series to draw. */
  readonly series: readonly TimeSeries[];
  readonly title: string;
  readonly description?: string | null;
  /** The unit the values are in, or null when it is not established. */
  readonly unit?: string | null;
  readonly height?: number;
  /** Called when the reader shows or hides a series in the legend. */
  readonly onLegendChange?: (seriesId: string, visible: boolean) => void;
}

interface UncertainSeries {
  readonly series: TimeSeries;
  readonly legendName: string;
  readonly colour: string;
  readonly hasInterval: boolean;
}

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
 * The ECharts series of the uncertainty chart.
 *
 * A pure function, so that the rules it enforces can be tested without a
 * canvas.
 */
export function buildUncertaintySeries(
  plotted: readonly UncertainSeries[],
  tokens: ChartTokens,
): Record<string, unknown>[] {
  const seriesOptions: Record<string, unknown>[] = [];

  for (const entry of plotted) {
    const points = entry.series.points;

    // The envelope exists only when the series carries an interval.
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

    seriesOptions.push({
      id: entry.series.id,
      name: entry.legendName,
      type: 'line',
      data: points.map((point) => [toMillis(point.t), point.v]),
      connectNulls: false,
      showSymbol: true,
      symbol: symbolForNature(entry.series.nature),
      symbolSize: 4,
      lineStyle: {
        width: 2,
        color: entry.colour,
        type: dashForNature(entry.series.nature) ?? 'solid',
      },
      itemStyle: { color: entry.colour },
      emphasis: { focus: 'series' },
      z: 5,
    });
  }

  return seriesOptions;
}

export function UncertaintyChart({
  series,
  title,
  description = null,
  unit = null,
  height = 300,
  onLegendChange,
}: UncertaintyChartProps) {
  const tokens = useChartTokens();

  const plotted = useMemo<UncertainSeries[]>(
    () =>
      series.map((entry, index) => ({
        series: entry,
        legendName: legendLabelForNature(entry.variable, entry.nature, entry.frequency),
        colour: tokens.series[index % tokens.series.length] ?? tokens.accent,
        hasInterval: entry.points.some((point) => point.lower !== null && point.upper !== null),
      })),
    [series, tokens],
  );

  /**
   * The label plate: the unit of the values.
   *
   * When the series disagree on their unit, the unit is not established, and
   * the plate says so rather than picking one of them.
   */
  const plate = useMemo(() => {
    const declared = new Set(
      series.map((entry) => entry.unit).filter((value): value is string => value !== null),
    );
    const conflict = declared.size > 1;
    const resolved = unit ?? (declared.size === 1 ? ([...declared][0] ?? null) : null);
    return unitPlate(resolved, conflict);
  }, [series, unit]);

  const option = useMemo<ChartOption>(() => {
    const seriesOptions = buildUncertaintySeries(plotted, tokens);

    return {
      animation: false,
      backgroundColor: tokens.well,
      color: [...tokens.series],
      grid: gridCraft(),
      legend: {
        ...legendChrome(tokens),
        data: plotted.map((entry) => ({
          name: entry.legendName,
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
            const record = item as { seriesIndex?: number; dataIndex?: number };
            const entry = plotted[record.seriesIndex ?? 0];
            if (entry === undefined) {
              continue;
            }
            const point = entry.series.points[record.dataIndex ?? -1];
            if (point === undefined) {
              continue;
            }
            const interval =
              point.lower !== null && point.upper !== null
                ? ` (${formatValue(point.lower, null)} – ${formatValue(point.upper, null)})`
                : '';
            const missing =
              point.v === null && point.missingReason !== null
                ? ` · absent: ${point.missingReason.replaceAll('_', ' ')}`
                : '';
            blocks.push(
              `<div style="font-weight:600">${escapeHtml(entry.legendName)}</div>` +
                `<div style="font-family:var(--font-mono);font-size:11px;opacity:.7">${escapeHtml(formatStamp(point.t))}</div>` +
                `<div>${escapeHtml(formatValue(point.v, entry.series.unit))}${escapeHtml(interval)}${escapeHtml(missing)}</div>` +
                `<div style="font-size:11px;opacity:.7">quality: ${escapeHtml(point.quality)}</div>`,
            );
          }
          return blocks.join('');
        },
      },
      xAxis: timeAxis(tokens),
      yAxis: valueAxis(tokens, {
        name: axisName(plate.established ? plate.label : null, false),
        nameLocation: 'end',
        nameGap: 12,
        nameTextStyle: {
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
          align: 'left',
        },
      }),
      dataZoom: [{ type: 'inside', filterMode: 'none', zoomOnMouseWheel: 'ctrl' }],
      series: seriesOptions,
    };
  }, [plotted, tokens, plate]);

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
    }),
    [plotted, onLegendChange],
  );

  const table = (
    <table>
      <thead>
        <tr>
          <th scope="col">Instant</th>
          <th scope="col">Series</th>
          <th scope="col">Value</th>
          <th scope="col">Lower</th>
          <th scope="col">Upper</th>
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
              <td>{point.quality}</td>
              <td>{describeTemporalReference(entry.series.reference)}</td>
            </tr>
          )),
        )}
      </tbody>
    </table>
  );

  const withoutInterval = plotted.filter((entry) => !entry.hasInterval).map((entry) => entry.legendName);

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
        withoutInterval.length === 0 && timeNote === null ? undefined : (
          <>
            {timeNote === null ? null : <span>{timeNote} </span>}
            {withoutInterval.length === 0 ? null : (
              <span>
                No uncertainty band is drawn for {withoutInterval.join(', ')}: no interval is provided
                for it.
              </span>
            )}
          </>
        )
      }
    >
      <EChart option={option} height={height} onEvents={onEvents} />
    </ChartFrame>
  );
}

export type { SeriesNature };
