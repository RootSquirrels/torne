/**
 * The coverage timeline.
 *
 * It shows what periods exist, and — just as importantly — what is missing
 * between them. Five things are drawn apart:
 *
 * - an **observed** period, established by measurement;
 * - an **estimated** period, reconstructed rather than measured;
 * - a **published** period, made available by a producer;
 * - a **revision**, a later version of a period already covered;
 * - a **gap**, the absence between two periods of the same subject.
 *
 * The gap is not a period: it is the absence of one, and it is drawn as such.
 * A timeline that hid the gaps would claim a continuity the data does not
 * have.
 *
 * Two rules about the bounds:
 *
 * - an **open** period is open. It runs to the edge of the axis and is marked
 *   as still open; it is never closed at "today" by assumption.
 * - an **unknown** end stays unknown. The bar runs to the edge of the axis
 *   with a dashed outline, and the table says the bound is not established.
 */
import { useMemo } from 'react';

import { ChartFrame } from '@/components/visualization/ChartFrame';
import { EChart } from '@/components/visualization/EChart';
import type { ChartOption } from '@/components/visualization/EChart';
import { escapeHtml } from '@/components/visualization/html';
import { useChartTokens } from '@/components/visualization/chartTheme';
import type { ChartTokens } from '@/components/visualization/chartTheme';
import { Legend } from '@/components/ui/Legend';
import type { LegendShape } from '@/components/ui/Legend';
import type { CoverageAvailability, CoverageKind, CoveragePeriod } from '@/types/visualization/coverage';

/**
 * How each kind is drawn. The shape differs as well as the colour.
 *
 * The mark is what the chart draws; the shape is what the legend shows. The
 * second is derived from the first, so the two cannot disagree: a legend that
 * advertises a shape the chart does not draw is a legend that lies.
 *
 * A kind carried by its colour alone would not be carried at all.
 */
export type CoverageMark = 'block' | 'dashed' | 'dot' | 'rule' | 'empty';

/** The swatch that shows a mark in the legend. */
const MARK_SHAPE: Record<CoverageMark, LegendShape> = {
  block: 'square',
  dashed: 'dash',
  dot: 'circle',
  rule: 'line',
  empty: 'empty',
};

/** The mark each kind is drawn with. */
const KIND_MARK: Record<CoverageKind, CoverageMark> = {
  observed: 'block',
  estimated: 'dashed',
  published: 'dot',
  revision: 'rule',
};

/** The colour each kind takes, in the categorical series register. */
const KIND_COLOUR_INDEX: Record<CoverageKind, number> = {
  observed: 0,
  estimated: 1,
  published: 2,
  revision: 3,
};

/**
 * How each kind is drawn: the colour, the mark, and the swatch the legend
 * shows for that mark.
 *
 * The swatch is **derived** from the mark, so the legend cannot advertise a
 * shape the chart does not draw. A kind carried by its colour alone would not
 * be carried at all.
 */
export const KIND_STYLE: Record<
  CoverageKind,
  { colourIndex: number; mark: CoverageMark; shape: LegendShape }
> = (Object.keys(KIND_MARK) as CoverageKind[]).reduce(
  (accumulator, kind) => {
    const mark = KIND_MARK[kind];
    accumulator[kind] = {
      colourIndex: KIND_COLOUR_INDEX[kind],
      mark,
      shape: MARK_SHAPE[mark],
    };
    return accumulator;
  },
  {} as Record<CoverageKind, { colourIndex: number; mark: CoverageMark; shape: LegendShape }>,
);

/** The swatch the legend shows for a gap: outlined, and empty. */
export const GAP_SHAPE: LegendShape = MARK_SHAPE.empty;

const KIND_LABEL: Record<CoverageKind, string> = {
  observed: 'observed',
  estimated: 'estimated',
  published: 'published',
  revision: 'revision',
};

export interface CoverageTimelineProps {
  /** The periods to draw. */
  readonly periods: readonly CoveragePeriod[];
  readonly title: string;
  readonly description?: string | null;
  /** The instant to answer "what was available on that day?" at. */
  readonly availableAt?: string | null;
  /** The availability of each subject at that instant, when it is known. */
  readonly availability?: readonly CoverageAvailability[];
  readonly height?: number;
  /** Called when a period is activated. */
  readonly onPeriodSelect?: (period: CoveragePeriod) => void;
}

interface RenderParams {
  readonly dataIndex: number;
}

interface RenderApi {
  value(index: number): number;
  coord(value: readonly number[]): readonly number[];
  size(value: readonly number[]): readonly number[];
}

interface Bar {
  readonly kind: CoverageKind | 'gap';
  readonly start: number;
  readonly end: number;
  readonly subjectIndex: number;
  readonly subject: string;
  readonly label: string;
  readonly open: boolean;
  readonly unknownEnd: boolean;
  readonly period: CoveragePeriod | null;
}

/** The axis bounds used when no period carries a known bound. */
const FALLBACK_MIN = Date.UTC(2000, 0, 1);
const FALLBACK_MAX = Date.UTC(2001, 0, 1);

function toMillis(stamp: string | null): number | null {
  if (stamp === null) {
    return null;
  }
  const parsed = Date.parse(stamp);
  return Number.isNaN(parsed) ? null : parsed;
}

/**
 * The bars of the timeline: the periods, and the gaps between them.
 *
 * A pure function, so that the rules it enforces can be tested without a
 * canvas.
 */
export function buildCoverageBars(
  periods: readonly CoveragePeriod[],
  axisMin: number,
  axisMax: number,
): { bars: Bar[]; subjects: string[] } {
  const subjects: string[] = [];
  for (const period of periods) {
    if (!subjects.includes(period.subject)) {
      subjects.push(period.subject);
    }
  }

  const bars: Bar[] = [];

  for (const subject of subjects) {
    const own = periods
      .filter((period) => period.subject === subject)
      .map((period) => {
        const start = toMillis(period.start);
        const end = toMillis(period.end);
        return {
          period,
          start: start ?? axisMin,
          end: period.open || end === null ? axisMax : end,
          knownStart: start !== null,
          unknownEnd: !period.open && end === null,
        };
      })
      .sort((left, right) => left.start - right.start);

    for (const entry of own) {
      bars.push({
        kind: entry.period.kind,
        start: entry.start,
        end: entry.end,
        subjectIndex: subjects.indexOf(subject),
        subject,
        label: KIND_LABEL[entry.period.kind],
        open: entry.period.open,
        unknownEnd: entry.unknownEnd,
        period: entry.period,
      });
    }

    // The gaps: the absence between two periods of the same subject.
    for (let index = 0; index < own.length - 1; index += 1) {
      const current = own[index];
      const next = own[index + 1];
      if (current === undefined || next === undefined) {
        continue;
      }
      if (next.start > current.end) {
        bars.push({
          kind: 'gap',
          start: current.end,
          end: next.start,
          subjectIndex: subjects.indexOf(subject),
          subject,
          label: 'gap',
          open: false,
          unknownEnd: false,
          period: null,
        });
      }
    }
  }

  return { bars, subjects };
}

export function CoverageTimeline({
  periods,
  title,
  description = null,
  availableAt = null,
  availability = [],
  height = 260,
  onPeriodSelect,
}: CoverageTimelineProps) {
  const tokens = useChartTokens();

  const { bars, subjects } = useMemo(() => {
    const known = periods
      .flatMap((period) => [toMillis(period.start), toMillis(period.end)])
      .filter((value): value is number => value !== null);
    // A deterministic fallback: the axis must not depend on the clock, so a
    // chart of the same data always looks the same.
    const min = known.length > 0 ? Math.min(...known) : FALLBACK_MIN;
    const max = known.length > 0 ? Math.max(...known) : FALLBACK_MAX;
    const pad = Math.max((max - min) * 0.02, 86_400_000);
    return buildCoverageBars(periods, min - pad, max + pad);
  }, [periods]);

  const colours = useMemo(() => {
    const map = new Map<string, string>();
    map.set('gap', tokens.muted);
    for (const kind of Object.keys(KIND_STYLE) as CoverageKind[]) {
      const index = KIND_STYLE[kind].colourIndex;
      map.set(kind, tokens.series[index % tokens.series.length] ?? tokens.accent);
    }
    return map;
  }, [tokens]);

  const option = useMemo<ChartOption>(() => {
    return {
      animation: false,
      grid: { left: 120, right: 28, top: 24, bottom: 48 },
      legend: { show: false },
      tooltip: {
        trigger: 'item',
        backgroundColor: tokens.surface,
        borderColor: tokens.border,
        textStyle: { color: tokens.text, fontSize: 12 },
        formatter: (rawParams: unknown) => {
          const record = rawParams as { dataIndex?: number } | null;
          const bar = record?.dataIndex === undefined ? undefined : bars[record.dataIndex];
          if (bar === undefined) {
            return '';
          }
          const from = new Date(bar.start).toISOString().slice(0, 10);
          const to = new Date(bar.end).toISOString().slice(0, 10);
          if (bar.kind === 'gap') {
            return `<strong>gap</strong><br/>${escapeHtml(bar.subject)}<br/>${from} → ${to}<br/>no coverage`;
          }
          const end = bar.open
            ? 'still open'
            : bar.unknownEnd
              ? 'end not established'
              : to;
          return `<strong>${KIND_LABEL[bar.kind]}</strong><br/>${escapeHtml(bar.subject)}<br/>${from} → ${end}`;
        },
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: tokens.border } },
        axisLabel: { color: tokens.label, fontSize: 11, hideOverlap: true },
        splitLine: { lineStyle: { color: tokens.grid } },
      },
      yAxis: {
        type: 'category',
        data: subjects,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: tokens.label, fontSize: 11 },
      },
      series: [
        {
          type: 'custom',
          data: bars.map((bar) => ({ value: [bar.start, bar.end, bar.subjectIndex] })),
          encode: { x: [0, 1], y: 2 },
          renderItem: (params: RenderParams, api: RenderApi) => {
            const bar = bars[params.dataIndex];
            if (bar === undefined) {
              return { type: 'group', children: [] };
            }
            const start = api.coord([api.value(0), api.value(2)]);
            const end = api.coord([api.value(1), api.value(2)]);
            const startX = start[0] ?? 0;
            const startY = start[1] ?? 0;
            const endX = end[0] ?? 0;
            const height = (api.size([0, 1])[1] ?? 0) * 0.42;
            const left = Math.min(startX, endX);
            const width = Math.max(Math.abs(endX - startX), 2);
            const colour = colours.get(bar.kind) ?? tokens.accent;
            const isGap = bar.kind === 'gap';
            const mark: CoverageMark = isGap ? 'empty' : KIND_STYLE[bar.kind].mark;
            const dashed = mark === 'dashed' || mark === 'empty' || bar.unknownEnd;

            const children: Record<string, unknown>[] = [
              {
                type: 'rect',
                shape: { x: left, y: startY - height / 2, width, height },
                style: {
                  fill: colour,
                  // The fill is what carries the kind's colour; the outline
                  // carries its mark. A gap has no fill at all: it is the
                  // absence of a period, not a pale period.
                  fillOpacity: isGap ? 0 : 0.85,
                  stroke: colour,
                  strokeOpacity: 1,
                  lineWidth: dashed ? 1.5 : 0,
                  lineDash:
                    mark === 'empty' ? [3, 3] : mark === 'dashed' || bar.unknownEnd ? [4, 3] : undefined,
                },
              },
            ];

            // The mark the legend promises: a dot for a published period, a
            // rule for a revision. Both are cut in the surface colour, so they
            // read on any of the four fills.
            if (mark === 'dot') {
              children.push({
                type: 'circle',
                shape: { cx: left + width / 2, cy: startY, r: 4 },
                style: { fill: tokens.surface },
              });
            }
            if (mark === 'rule') {
              children.push({
                type: 'line',
                shape: { x1: left + 3, y1: startY, x2: left + width - 3, y2: startY },
                style: { stroke: tokens.surface, lineWidth: 2 },
              });
            }

            // An open period ends with a chevron: it has not finished.
            if (bar.open) {
              children.push({
                type: 'polygon',
                shape: {
                  points: [
                    [left + width, startY - height / 2],
                    [left + width + 7, startY],
                    [left + width, startY + height / 2],
                  ],
                },
                style: { fill: colour },
              });
            }

            return { type: 'group', children };
          },
        },
      ],
    };
  }, [bars, subjects, tokens, colours]);

  const onEvents = useMemo(
    () => ({
      click: (rawParams: unknown) => {
        const record = rawParams as { dataIndex?: number } | null;
        const bar = record?.dataIndex === undefined ? undefined : bars[record.dataIndex];
        if (bar?.period !== null && bar?.period !== undefined) {
          onPeriodSelect?.(bar.period);
        }
      },
    }),
    [bars, onPeriodSelect],
  );

  const legendItems = useMemo(
    () => [
      ...(Object.keys(KIND_STYLE) as CoverageKind[]).map((kind) => ({
        label: KIND_LABEL[kind],
        color: colours.get(kind) ?? tokens.accent,
        shape: KIND_STYLE[kind].shape,
      })),
      { label: 'gap', color: colours.get('gap') ?? tokens.muted, shape: GAP_SHAPE },
    ],
    [colours, tokens],
  );

  const table = (
    <table>
      <thead>
        <tr>
          <th scope="col">Subject</th>
          <th scope="col">Kind</th>
          <th scope="col">Start</th>
          <th scope="col">End</th>
        </tr>
      </thead>
      <tbody>
        {bars.map((bar, index) => (
          <tr key={`${bar.subject}-${bar.kind}-${index}`}>
            <td>{bar.subject}</td>
            <td>{bar.kind === 'gap' ? 'gap' : KIND_LABEL[bar.kind]}</td>
            <td>{new Date(bar.start).toISOString().slice(0, 10)}</td>
            <td>
              {bar.open ? 'still open' : bar.unknownEnd ? 'not established' : new Date(bar.end).toISOString().slice(0, 10)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const availabilityNote =
    availableAt === null
      ? null
      : availability.length === 0
        ? `Availability at ${availableAt}: not known.`
        : availability
            .map((entry) => {
              const verdict =
                entry.available === null
                  ? 'not known'
                  : entry.available
                    ? 'available'
                    : 'not available';
              return `${entry.subject} at ${entry.at}: ${verdict}.`;
            })
            .join(' ');

  return (
    <ChartFrame
      title={title}
      description={description}
      ariaLabel={`${title}. ${subjects.length} subjects, ${bars.length} periods and gaps.`}
      table={table}
      footnote={availabilityNote}
      actions={<Legend title="What the kinds mean" items={legendItems} />}
    >
      <EChart option={option} height={height} onEvents={onEvents} />
    </ChartFrame>
  );
}

export type { ChartTokens };
