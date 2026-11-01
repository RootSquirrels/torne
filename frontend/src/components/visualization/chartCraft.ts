/**
 * The craft of the canvas.
 *
 * A chart is drawn on a canvas, and a canvas has no stylesheets: everything —
 * the grid, the axes, the ticks, the tooltip, the zoom track — has to be
 * described in options, in concrete values, for every chart.
 *
 * Left to itself, each chart would describe its own furniture, and the four
 * charts would end up looking like four applications. This module is the
 * shared furniture: one set of options, built from the chart tokens, so the
 * Explorer reads as a single instrument with several dials rather than a
 * collage.
 *
 * Two rules run through it:
 *
 * - **The numbers are set in the figures face.** A measured value, an instant
 *   and an identifier are read in columns; the mono face gives them the
 *   columnar rhythm a printed instrument has.
 * - **Nothing is stated twice.** The unit is not written on the axis and in
 *   the caption; it is written once, on the label plate, where it is read.
 */

import type { ChartTokens } from '@/components/visualization/chartTheme';

/**
 * The plot area of a chart.
 *
 * `containLabel` keeps an axis label from being clipped, which matters more
 * than the exact inset: a chart that cuts its own numbers in half is a chart
 * that lies about its data.
 */
export function gridCraft(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    left: 8,
    right: 24,
    top: 52,
    bottom: 44,
    containLabel: true,
    ...overrides,
  };
}

/** A time axis: instants, not indices. */
export function timeAxis(tokens: ChartTokens, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'time',
    axisLine: { show: true, lineStyle: { color: tokens.axis, width: 1 } },
    axisTick: { show: true, length: 4, lineStyle: { color: tokens.axis, width: 1 } },
    axisLabel: {
      color: tokens.label,
      fontSize: 11,
      fontFamily: tokens.fontMono,
      hideOverlap: true,
      margin: 10,
    },
    splitLine: { show: true, lineStyle: { color: tokens.grid, width: 1 } },
    ...extra,
  };
}

/**
 * A value axis.
 *
 * The rule down the left of the plot and the rules across it are the same
 * hairline: the plot reads as a ruled field, not as a stack of boxes.
 */
export function valueAxis(tokens: ChartTokens, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'value',
    axisLine: { show: true, lineStyle: { color: tokens.axis, width: 1 } },
    axisTick: { show: true, length: 4, lineStyle: { color: tokens.axis, width: 1 } },
    axisLabel: {
      color: tokens.label,
      fontSize: 11,
      fontFamily: tokens.fontMono,
      margin: 10,
    },
    splitLine: { show: true, lineStyle: { color: tokens.grid, width: 1 } },
    ...extra,
  };
}

/** A category axis: the names of the subjects a chart draws. */
export function categoryAxis(
  tokens: ChartTokens,
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    type: 'category',
    axisLine: { show: true, lineStyle: { color: tokens.axis, width: 1 } },
    axisTick: { show: false },
    axisLabel: { color: tokens.label, fontSize: 11, fontFamily: tokens.fontSans },
    splitLine: { show: true, lineStyle: { color: tokens.grid, width: 1 } },
    ...extra,
  };
}

/**
 * The floating surface of a chart: the tooltip.
 *
 * It is a panel of the application, not a browser default: the same ground,
 * the same hairline, the same shadow as any other overlay in the Explorer.
 */
export function tooltipChrome(tokens: ChartTokens): Record<string, unknown> {
  return {
    backgroundColor: tokens.overlay,
    borderColor: tokens.border,
    borderWidth: 1,
    padding: [10, 12],
    textStyle: {
      color: tokens.text,
      fontSize: 12,
      fontFamily: tokens.fontSans,
      lineHeight: 18,
    },
    extraCssText: `border-radius:6px;box-shadow:${tokens.shadow};`,
    confine: true,
  };
}

/**
 * The pointer that follows the reader along the axes.
 *
 * It is a hairline, dashed, so it never reads as data; and it carries a
 * little value tag in the accent, which is the instrument's way of saying
 * "here" without covering the line.
 */
export function axisPointer(tokens: ChartTokens, kind: 'line' | 'cross' | 'shadow' = 'cross'): Record<string, unknown> {
  return {
    type: kind,
    lineStyle: { color: tokens.crosshair, width: 1, type: 'dashed' },
    crossStyle: { color: tokens.crosshair, width: 1, type: 'dashed' },
    shadowStyle: { color: tokens.uncertainty },
    label: {
      show: true,
      backgroundColor: tokens.accent,
      color: tokens.accentInk,
      fontFamily: tokens.fontMono,
      fontSize: 10,
      borderRadius: 2,
      padding: [3, 5],
    },
  };
}

/**
 * The legend of a chart.
 *
 * The legend sits above the plot, on its own line, so it can never collide
 * with the axis it explains. The caller gives each entry its own icon, so
 * that a series is carried by its mark as well as by its colour.
 */
export function legendChrome(tokens: ChartTokens): Record<string, unknown> {
  return {
    type: 'scroll',
    top: 0,
    left: 0,
    right: 0,
    itemWidth: 14,
    itemHeight: 8,
    itemGap: 20,
    icon: 'roundRect',
    textStyle: { color: tokens.label, fontSize: 11, fontFamily: tokens.fontSans },
    inactiveColor: tokens.grid,
    pageIconColor: tokens.label,
    pageIconInactiveColor: tokens.grid,
    pageTextStyle: { color: tokens.label, fontSize: 10, fontFamily: tokens.fontSans },
  };
}

/**
 * The zoom: a wheel inside the plot, and a track under it.
 *
 * The track is not a grey bar. It shows the whole range as a faint band and
 * the chosen window as a tinted one, so the reader can see at a glance how
 * much of the record they are looking at.
 */
export function zoomChrome(tokens: ChartTokens): Record<string, unknown>[] {
  return [
    { type: 'inside', filterMode: 'none', zoomOnMouseWheel: 'ctrl' },
    {
      type: 'slider',
      height: 20,
      bottom: 10,
      borderWidth: 0,
      backgroundColor: 'transparent',
      fillerColor: tokens.uncertainty,
      handleStyle: { color: tokens.surface, borderColor: tokens.accent, borderWidth: 1 },
      moveHandleStyle: { color: tokens.accent, opacity: 0.35 },
      // The preview of the whole series is not drawn: it repeats the plot
      // above it, at one pixel of height, and reads as noise. The track
      // shows the window that is chosen, and the axis shows the record.
      dataBackground: {
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      selectedDataBackground: {
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      textStyle: { color: tokens.label, fontSize: 10, fontFamily: tokens.fontMono },
      brushSelect: false,
      showDetail: true,
    },
  ];
}

/**
 * The unit of the values, as the label plate states it.
 *
 * When the series disagree on their unit, the unit is **not established**:
 * the plate says so rather than picking one of them. The unknown stays
 * unknown, and it says so where the reader reads the values.
 */
export function unitPlate(
  unit: string | null,
  conflict: boolean,
): { readonly label: string; readonly established: boolean } {
  if (conflict || unit === null || unit === '') {
    return { label: 'unit not established', established: false };
  }
  return { label: unit, established: true };
}

/**
 * The name of an axis, when there is one to give.
 *
 * An unestablished unit gets no axis name: an axis labelled "unit not
 * established" says nothing a reader can use, and it collides with the
 * legend. The label plate carries the statement instead.
 */
export function axisName(unit: string | null, conflict: boolean): string | undefined {
  const plate = unitPlate(unit, conflict);
  return plate.established ? plate.label : undefined;
}
