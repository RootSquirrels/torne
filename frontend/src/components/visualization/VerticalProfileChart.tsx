/**
 * The vertical profile chart.
 *
 * A vertical profile is a set of measurements taken along a vertical axis:
 * an oceanographic cast, an atmospheric sounding, a set of model levels.
 *
 * The component is deliberately conservative about the axis, because that is
 * where a chart of this kind usually goes wrong:
 *
 * - **pressure is not depth.** The axis declares its physical nature, its unit
 *   and its reference, and the chart never converts one into the other;
 * - **a model level is not a distance.** A level index is drawn as an index,
 *   with the unit `level`;
 * - **the direction is declared.** Depth grows downward, pressure grows
 *   upward; the profile says which it is, and the chart inverts the axis
 *   accordingly rather than guessing;
 * - **the levels are irregular.** The axis is a value axis, not a category
 *   axis: the levels are placed where they are, at the spacing the source
 *   gave them;
 * - **a missing value is a gap.** The line breaks; nothing is interpolated.
 * - **profiles that do not share an axis are not drawn together.** The chart
 *   says so instead of putting a pressure on a depth axis.
 */
import { useMemo } from 'react';

import { ChartFrame } from '@/components/visualization/ChartFrame';
import { EChart } from '@/components/visualization/EChart';
import { escapeHtml } from '@/components/visualization/html';
import { useChartTokens } from '@/components/visualization/chartTheme';
import {
  axisPointer,
  gridCraft,
  legendChrome,
  tooltipChrome,
  valueAxis,
} from '@/components/visualization/chartCraft';
import type {
  VerticalCoordinateKind,
  VerticalProfile,
  VerticalProfilePoint,
} from '@/types/visualization/verticalProfile';

export interface VerticalProfileChartProps {
  /** The profiles to draw. They must share the same vertical axis. */
  readonly profiles: readonly VerticalProfile[];
  readonly title: string;
  readonly description?: string | null;
  /**
   * The variable to draw on the value axis.
   *
   * When it is not given, the first variable of the first profile is used.
   */
  readonly variableKey?: string;
  readonly height?: number;
  /** Called when a level is activated. */
  readonly onLevelSelect?: (profileId: string, point: VerticalProfilePoint) => void;
}

interface AxisSummary {
  readonly kind: VerticalCoordinateKind;
  readonly unit: string;
  readonly label: string;
  readonly direction: 'increasing-up' | 'increasing-down';
}

function axisOf(profiles: readonly VerticalProfile[]): AxisSummary | null {
  const first = profiles[0];
  if (first === undefined) {
    return null;
  }
  return {
    kind: first.axis.kind,
    unit: first.axis.unit,
    label: first.axis.label,
    direction: first.axis.direction,
  };
}

function shareAxis(profiles: readonly VerticalProfile[], axis: AxisSummary): boolean {
  return profiles.every(
    (profile) =>
      profile.axis.kind === axis.kind &&
      profile.axis.unit === axis.unit &&
      profile.axis.direction === axis.direction,
  );
}

function formatValue(value: number | null, unit: string | null): string {
  if (value === null) {
    return 'no value';
  }
  const rendered = Number.isInteger(value) ? String(value) : value.toPrecision(6);
  return unit === null ? rendered : `${rendered} ${unit}`;
}

export function VerticalProfileChart({
  profiles,
  title,
  description = null,
  variableKey,
  height = 360,
  onLevelSelect,
}: VerticalProfileChartProps) {
  const tokens = useChartTokens();

  const axis = axisOf(profiles);
  const compatible = axis !== null && shareAxis(profiles, axis);

  const variable = useMemo(() => {
    const first = profiles[0];
    if (first === undefined) {
      return null;
    }
    const chosen = variableKey ?? first.variables[0]?.key;
    if (chosen === undefined) {
      return null;
    }
    return first.variables.find((entry) => entry.key === chosen) ?? null;
  }, [profiles, variableKey]);

  const option = useMemo(() => {
    if (axis === null || variable === null || !compatible) {
      return null;
    }

    const seriesOptions = profiles.map((profile, index) => {
      const colour = tokens.series[index % tokens.series.length] ?? tokens.accent;

      // The levels are drawn where they are. The order the source gave them
      // is not necessarily the order of the axis, so the points are placed by
      // their coordinate, never by their index.
      const points = [...profile.points].sort((left, right) =>
        left.coordinate.value === right.coordinate.value
          ? 0
          : left.coordinate.value < right.coordinate.value
            ? -1
            : 1,
      );

      const flagged = points.filter(
        (point) => point.validity === 'invalid' || point.validity === 'out_of_domain',
      );

      return {
        id: profile.id,
        name: profile.name,
        type: 'line',
        data: points.map((point) => [point.values[variable.key] ?? null, point.coordinate.value]),
        connectNulls: false,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 1.5, color: colour },
        itemStyle: { color: colour },
        emphasis: { focus: 'series' },
        ...(flagged.length === 0
          ? {}
          : {
              markPoint: {
                symbol: 'circle',
                symbolSize: 9,
                itemStyle: { color: 'transparent', borderColor: tokens.reference, borderWidth: 1.5 },
                label: { show: false },
                data: flagged.map((point) => ({
                  name: point.quality,
                  xAxis: point.values[variable.key] ?? null,
                  yAxis: point.coordinate.value,
                })),
              },
            }),
      };
    });

    const coordinates = profiles.flatMap((profile) =>
      profile.points.map((point) => point.coordinate.value),
    );

    return {
      animation: false,
      backgroundColor: tokens.well,
      grid: gridCraft({ top: 56, bottom: 56 }),
      legend: {
        ...legendChrome(tokens),
        data: profiles.map((profile) => ({ name: profile.name, icon: 'circle' })),
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
            const profile = profiles[record.seriesIndex ?? 0];
            if (profile === undefined) {
              continue;
            }
            const point = profile.points[record.dataIndex ?? -1];
            if (point === undefined) {
              continue;
            }
            const raw = record.value;
            const value: unknown = Array.isArray(raw) ? raw[0] : null;
            const numberValue = typeof value === 'number' ? value : null;
            blocks.push(
              `<div style="font-weight:600">${escapeHtml(profile.name)}</div>` +
                `<div style="font-size:11px;opacity:.7">${escapeHtml(axis.label)}: ${escapeHtml(String(point.coordinate.value))} ${escapeHtml(point.coordinate.unit)}</div>` +
                `<div>${escapeHtml(variable.label)}: ${escapeHtml(formatValue(numberValue, variable.unit))}</div>` +
                `<div style="font-size:11px;opacity:.7">quality: ${escapeHtml(point.quality)}${point.missingReason === null ? '' : ` · absent: ${escapeHtml(point.missingReason.replaceAll('_', ' '))}`}</div>`,
            );
          }
          return blocks.join('');
        },
      },
      xAxis: valueAxis(tokens, {
        name: variable.unit === null ? variable.label : `${variable.label} (${variable.unit})`,
        nameLocation: 'middle',
        nameGap: 32,
        nameTextStyle: {
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
        },
      }),
      yAxis: valueAxis(tokens, {
        name: `${axis.label} (${axis.unit})`,
        nameLocation: 'end',
        nameGap: 12,
        nameTextStyle: {
          color: tokens.label,
          fontSize: 10,
          fontFamily: tokens.fontMono,
          align: 'left',
        },
        inverse: axis.direction === 'increasing-down',
        min: coordinates.length > 0 ? Math.min(...coordinates) : undefined,
        max: coordinates.length > 0 ? Math.max(...coordinates) : undefined,
      }),
      series: seriesOptions,
    };
  }, [axis, compatible, profiles, tokens, variable]);

  const onEvents = useMemo(
    () => ({
      click: (rawParams: unknown) => {
        if (typeof rawParams !== 'object' || rawParams === null) {
          return;
        }
        const record = rawParams as { seriesIndex?: number; dataIndex?: number };
        const profile = profiles[record.seriesIndex ?? -1];
        const point = profile?.points[record.dataIndex ?? -1];
        if (profile !== undefined && point !== undefined) {
          onLevelSelect?.(profile.id, point);
        }
      },
    }),
    [profiles, onLevelSelect],
  );

  const table = (
    <table>
      <thead>
        <tr>
          <th scope="col">Profile</th>
          <th scope="col">{axis?.label ?? 'Level'}</th>
          <th scope="col">{variable?.label ?? 'Value'}</th>
          <th scope="col">Quality</th>
        </tr>
      </thead>
      <tbody>
        {profiles.flatMap((profile) =>
          profile.points.map((point) => (
            <tr key={`${profile.id}-${point.coordinate.value}`}>
              <td>{profile.name}</td>
              <td>
                {point.coordinate.value} {point.coordinate.unit}
              </td>
              <td>{formatValue(point.values[variable?.key ?? ''] ?? null, variable?.unit ?? null)}</td>
              <td>{point.quality}</td>
            </tr>
          )),
        )}
      </tbody>
    </table>
  );

  if (!compatible) {
    return (
      <ChartFrame
        title={title}
        description={description}
        ariaLabel={`${title}. The profiles do not share a vertical axis.`}
        table={table}
      >
        <p className="torne-profile__refusal">
          These profiles do not share the same vertical axis, so they cannot be drawn on one
          chart: a pressure is not a depth, and a model level is not a distance. Draw them
          separately, or restate them in a common axis — a scientific decision, not a
          display one.
        </p>
      </ChartFrame>
    );
  }

  return (
    <ChartFrame
      title={title}
      description={description}
      ariaLabel={`${title}. ${profiles.length} profiles, ${profiles.reduce((sum, profile) => sum + profile.points.length, 0)} levels.`}
      table={table}
    >
      {option === null ? (
        <p className="torne-profile__refusal">There is nothing to draw: no variable was given.</p>
      ) : (
        <EChart option={option} height={height} onEvents={onEvents} />
      )}
    </ChartFrame>
  );
}
