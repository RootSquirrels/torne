/**
 * The chart theme.
 *
 * A chart is drawn on a canvas, so it cannot use CSS custom properties the
 * way a component can: the colours have to be read as concrete values. This
 * module reads them from the design tokens, and re-reads them when the theme
 * changes, so a chart and the components around it always agree.
 *
 * The three colour registers stay separate, exactly as in the tokens:
 * `--series-*` for data, `--science-status-*` for the ordinal status ramp,
 * `--accent-*` for interaction only.
 *
 * The **fonts** are read as well, and they matter as much as the colours: a
 * canvas that falls back to its own default type looks like a different
 * application from the one around it. The values read here are the very
 * stacks the DOM uses, so a chart and the page it sits on are set in the same
 * letterforms.
 */

import { useEffect, useState } from 'react';

import type { SeriesNature, TemporalFrequency, TemporalReference } from '@/types/visualization/timeSeries';

/** What the nature of a series adds to its name. */
const NATURE_SUFFIX: Record<SeriesNature, string> = {
  observation: '',
  estimate: ' (estimate)',
  forecast: ' (forecast)',
  simulation: ' (simulation)',
};

export interface ChartTokens {
  /** The categorical palette, in order. */
  readonly series: readonly string[];
  /** The science status ramp, from "nothing" to "knowledge". */
  readonly status: readonly string[];
  /** The ground the plot is drawn on: the well of the instrument. */
  readonly well: string;
  /** A raised surface: the body of a panel around the plot. */
  readonly surface: string;
  /** A floating surface: a tooltip. */
  readonly overlay: string;
  readonly axis: string;
  readonly grid: string;
  readonly label: string;
  readonly text: string;
  readonly muted: string;
  readonly border: string;
  readonly crosshair: string;
  readonly reference: string;
  readonly uncertainty: string;
  readonly uncertaintyForecast: string;
  readonly accent: string;
  /** The ink that sits on the accent. */
  readonly accentInk: string;
  /** The shadow a floating element casts, read as a concrete value. */
  readonly shadow: string;
  /** The text face, as the page uses it. */
  readonly fontSans: string;
  /** The figures face: identifiers, instants, measured values. */
  readonly fontMono: string;
  /** The paint of the map: its background, its land, its boundary and its markers. */
  readonly mapWater: string;
  readonly mapLand: string;
  readonly mapBoundary: string;
  readonly mapMarker: string;
  readonly mapMarkerSelected: string;
  /**
   * The attention colour: a state that must be seen.
   *
   * It belongs to the semantic register, not to the series: it says "this is
   * in tension", never "this is the third series".
   */
  readonly warning: string;
}

/**
 * The order in which the register is handed out.
 *
 * The hues are the ones the tokens declare; the *order* is not. Okabe-Ito
 * keeps its eight hues apart for a reader with normal colour vision, but two
 * of them can still converge under a dichromacy, so the register is dealt out
 * in an order that was chosen by measuring it: every prefix of this list
 * keeps every pair apart under protanopia, deuteranopia and tritanopia, in
 * both skins, by at least 11 units of CIE dE.
 *
 * The practical consequence is that a chart with up to eight series is
 * separable by colour for a reader who cannot use colour, and a chart with
 * fewer series is separable by a wider margin. The test that holds this
 * order is `tests/test_frontend_series_palette.py`.
 */
const SERIES_VARS = [
  '--series-1',
  '--series-2',
  '--series-8',
  '--series-6',
  '--series-3',
  '--series-4',
  '--series-7',
  '--series-5',
];
const STATUS_VARS = Array.from({ length: 5 }, (_, index) => `--science-status-${index}`);

function read(root: HTMLElement, name: string, fallback: string): string {
  const value = getComputedStyle(root).getPropertyValue(name).trim();
  if (value === '') {
    return fallback;
  }
  // A custom property keeps its own white space, and a font stack declared
  // over several lines comes back with the line break in it. The canvas wants
  // a single line, so the space is normalised here.
  return value.replace(/\s+/g, ' ');
}

/** The chart tokens, read from the document root. */
export function readChartTokens(root: HTMLElement): ChartTokens {
  const series = SERIES_VARS.map((name) => read(root, name, `var(${name})`));
  const status = STATUS_VARS.map((name) => read(root, name, `var(${name})`));
  return {
    series,
    status,
    well: read(root, '--chart-well', '#faf9f6'),
    surface: read(root, '--surface-raised', '#ffffff'),
    overlay: read(root, '--surface-overlay', '#ffffff'),
    axis: read(root, '--chart-axis', '#b3ad9f'),
    grid: read(root, '--chart-grid', '#e9e5dc'),
    label: read(root, '--chart-label', '#6a717a'),
    text: read(root, '--content-primary', '#1a1c20'),
    muted: read(root, '--content-secondary', '#565c65'),
    border: read(root, '--border-default', '#d6d1c6'),
    crosshair: read(root, '--chart-crosshair', '#8b8578'),
    reference: read(root, '--chart-reference', '#6a717a'),
    uncertainty: read(root, '--chart-uncertainty', 'rgba(0,114,178,0.16)'),
    uncertaintyForecast: read(root, '--chart-uncertainty-forecast', 'rgba(164,72,31,0.16)'),
    accent: read(root, '--accent', '#a4481f'),
    accentInk: read(root, '--accent-ink', '#ffffff'),
    shadow: read(root, '--shadow-3', 'none'),
    fontSans: read(root, '--font-sans', 'system-ui, sans-serif'),
    fontMono: read(root, '--font-mono', 'ui-monospace, monospace'),
    mapWater: read(root, '--map-water', '#e2e9ec'),
    mapLand: read(root, '--map-land', '#eae6dd'),
    mapBoundary: read(root, '--map-boundary', '#c6c0b3'),
    mapMarker: read(root, '--map-marker', '#1a1c20'),
    mapMarkerSelected: read(root, '--map-marker-selected', '#a4481f'),
    warning: read(root, '--semantic-warning', '#8a6100'),
  };
}

/**
 * The chart tokens, kept in step with the theme.
 *
 * The theme can change in three ways: an explicit `data-theme` on the root
 * element, the operating system's preference, or neither. The observer and
 * the media query listener cover all three.
 */
export function useChartTokens(): ChartTokens {
  const [tokens, setTokens] = useState<ChartTokens>(() =>
    readChartTokens(document.documentElement),
  );

  useEffect(() => {
    const update = () => setTokens(readChartTokens(document.documentElement));

    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'class', 'style'],
    });

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    media.addEventListener('change', update);

    return () => {
      observer.disconnect();
      media.removeEventListener('change', update);
    };
  }, []);

  return tokens;
}

/**
 * The dash pattern that carries the nature of a series.
 *
 * The nature of a series — observation, estimate, forecast — is a *state*, not
 * a series colour. It is carried by the dash pattern as well as by the legend
 * text, so it survives a reader who cannot tell the colours apart.
 */
export function dashForNature(nature: 'observation' | 'estimate' | 'forecast' | 'simulation'): number[] | undefined {
  switch (nature) {
    case 'observation':
      return undefined;
    case 'estimate':
      return [8, 4];
    case 'forecast':
      return [2, 4];
    case 'simulation':
      return [10, 3, 2, 3];
  }
}

/** The symbol that carries the nature of a series in a legend. */
export function symbolForNature(
  nature: 'observation' | 'estimate' | 'forecast' | 'simulation',
): 'circle' | 'rect' | 'diamond' | 'triangle' {
  switch (nature) {
    case 'observation':
      return 'circle';
    case 'estimate':
      return 'rect';
    case 'forecast':
      return 'diamond';
    case 'simulation':
      return 'triangle';
  }
}

/**
 * The text a legend uses for a series, with its nature spelled out.
 */
export function legendLabelForNature(
  variable: string,
  nature: SeriesNature,
  frequency?: TemporalFrequency | null,
): string {
  const base = `${variable}${NATURE_SUFFIX[nature]}`;
  return frequency === undefined || frequency === null ? base : `${base} · ${frequency}`;
}

/**
 * How a series states the reference its stamps are taken in.
 *
 * A stamp is not a number: `2026-01-01` may be a civil day in Paris — a whole
 * day, averaged or accumulated — or an instant. Two series on one axis that
 * mean different things must say so, or the reader compares what cannot be
 * compared.
 */
export function describeTemporalReference(reference: TemporalReference): string {
  if (reference.basis === 'civil-day') {
    return reference.timeZone === null ? 'civil day' : `civil day (${reference.timeZone})`;
  }
  return 'instant';
}
