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
 */

import { useEffect, useState } from 'react';

export interface ChartTokens {
  /** The categorical palette, in order. */
  readonly series: readonly string[];
  /** The science status ramp, from "nothing" to "knowledge". */
  readonly status: readonly string[];
  readonly axis: string;
  readonly grid: string;
  readonly label: string;
  readonly text: string;
  readonly muted: string;
  readonly surface: string;
  readonly border: string;
  readonly crosshair: string;
  readonly reference: string;
  readonly uncertainty: string;
  readonly uncertaintyForecast: string;
  readonly accent: string;
  /** The paint of the map: its background, its land, its boundary and its markers. */
  readonly mapWater: string;
  readonly mapLand: string;
  readonly mapBoundary: string;
  readonly mapMarker: string;
  readonly mapMarkerSelected: string;
}

const SERIES_VARS = Array.from({ length: 8 }, (_, index) => `--series-${index + 1}`);
const STATUS_VARS = Array.from({ length: 5 }, (_, index) => `--science-status-${index}`);

function read(root: HTMLElement, name: string, fallback: string): string {
  const value = getComputedStyle(root).getPropertyValue(name).trim();
  return value === '' ? fallback : value;
}

/** The chart tokens, read from the document root. */
export function readChartTokens(root: HTMLElement): ChartTokens {
  const series = SERIES_VARS.map((name) => read(root, name, `var(${name})`));
  const status = STATUS_VARS.map((name) => read(root, name, `var(${name})`));
  return {
    series,
    status,
    axis: read(root, '--chart-axis', '#8d939b'),
    grid: read(root, '--chart-grid', '#e6e3db'),
    label: read(root, '--chart-label', '#5d636b'),
    text: read(root, '--content-primary', '#1d1f22'),
    muted: read(root, '--content-secondary', '#5d636b'),
    surface: read(root, '--surface-raised', '#ffffff'),
    border: read(root, '--border-default', '#dcd9d1'),
    crosshair: read(root, '--chart-crosshair', '#b8b4aa'),
    reference: read(root, '--chart-reference', '#6b727b'),
    uncertainty: read(root, '--chart-uncertainty', 'rgba(0,114,178,0.18)'),
    uncertaintyForecast: read(root, '--chart-uncertainty-forecast', 'rgba(181,83,44,0.18)'),
    accent: read(root, '--accent', '#b5532c'),
    mapWater: read(root, '--map-water', '#dfe7ea'),
    mapLand: read(root, '--map-land', '#e8e5dd'),
    mapBoundary: read(root, '--map-boundary', '#c9c4b8'),
    mapMarker: read(root, '--map-marker', '#1d1f22'),
    mapMarkerSelected: read(root, '--map-marker-selected', '#b5532c'),
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

/** The text a legend uses for a series, with its nature spelled out. */
export function legendLabelForNature(
  variable: string,
  nature: 'observation' | 'estimate' | 'forecast' | 'simulation',
): string {
  switch (nature) {
    case 'observation':
      return variable;
    case 'estimate':
      return `${variable} (estimate)`;
    case 'forecast':
      return `${variable} (forecast)`;
    case 'simulation':
      return `${variable} (simulation)`;
  }
}
