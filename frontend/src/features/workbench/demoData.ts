/**
 * The synthetic demonstration data.
 *
 * **This is synthetic demo data.** Every value here was invented for the
 * workbench: it measures nothing, it comes from no source, and it establishes
 * nothing. It exists to exercise the components and to let the design system
 * evolve independently of the scientific missions.
 *
 * It is imported by the workbench page only. It never reaches the catalogue,
 * the manifest, or a published result — the Python package builds the manifest
 * from the repository's own evidence, and nothing in `src/torne` reads this
 * file.
 */
import type { TimeSeries } from '@/types/visualization/timeSeries';
import type { VerticalProfile } from '@/types/visualization/verticalProfile';
import type { SpatialScene } from '@/types/visualization/spatial';
import type { CoveragePeriod } from '@/types/visualization/coverage';

export const DEMO_NOTICE =
  'Synthetic demo data — invented for the component workbench. It measures nothing and establishes nothing.';

/** A daily series with gaps, an interval, and a forecast that starts mid-way. */
export const demoTimeSeries: readonly TimeSeries[] = [
  {
    id: 'demo-discharge',
    variable: 'Discharge',
    unit: 'm³/s',
    frequency: 'daily',
    reference: { basis: 'civil-day', timeZone: 'Europe/Paris' },
    nature: 'observation',
    estimateFrom: null,
    forecastFrom: '2026-03-01',
    provenance: [],
    points: [
      { t: '2026-01-01', v: 412, lower: 396, upper: 431, missingReason: null, quality: 'declared' },
      { t: '2026-01-02', v: 418, lower: 401, upper: 438, missingReason: null, quality: 'declared' },
      { t: '2026-01-03', v: null, lower: null, upper: null, missingReason: 'not_measured', quality: 'unknown' },
      { t: '2026-01-04', v: null, lower: null, upper: null, missingReason: 'not_measured', quality: 'unknown' },
      { t: '2026-01-05', v: 405, lower: 388, upper: 425, missingReason: null, quality: 'declared' },
      { t: '2026-01-06', v: 431, lower: 412, upper: 452, missingReason: null, quality: 'approved' },
      { t: '2026-01-07', v: 447, lower: 428, upper: 469, missingReason: null, quality: 'approved' },
      { t: '2026-01-08', v: null, lower: null, upper: null, missingReason: 'not_yet_published', quality: 'unknown' },
      { t: '2026-01-09', v: 452, lower: 433, upper: 474, missingReason: null, quality: 'declared' },
      { t: '2026-01-10', v: 468, lower: 448, upper: 490, missingReason: null, quality: 'declared' },
    ],
  },
  {
    id: 'demo-level',
    variable: 'Water level',
    unit: 'm',
    frequency: 'hourly',
    reference: { basis: 'instant', timeZone: null },
    nature: 'estimate',
    estimateFrom: null,
    forecastFrom: null,
    provenance: [],
    points: [
      { t: '2026-01-01T00:00:00Z', v: 2.14, lower: 2.08, upper: 2.2, missingReason: null, quality: 'source_estimated' },
      { t: '2026-01-01T06:00:00Z', v: 2.19, lower: 2.13, upper: 2.25, missingReason: null, quality: 'source_estimated' },
      { t: '2026-01-01T12:00:00Z', v: 2.22, lower: 2.16, upper: 2.28, missingReason: null, quality: 'source_estimated' },
      { t: '2026-01-01T18:00:00Z', v: 2.2, lower: null, upper: null, missingReason: null, quality: 'provisional' },
      { t: '2026-01-02T00:00:00Z', v: 2.17, lower: 2.11, upper: 2.23, missingReason: null, quality: 'source_estimated' },
    ],
  },
];

/** A series with no interval at all, so that no band is drawn for it. */
export const demoSeriesWithoutInterval: readonly TimeSeries[] = [
  {
    id: 'demo-plain',
    variable: 'Stage',
    unit: 'm',
    frequency: 'daily',
    reference: { basis: 'civil-day', timeZone: 'Europe/Paris' },
    nature: 'observation',
    estimateFrom: null,
    forecastFrom: null,
    provenance: [],
    points: [
      { t: '2026-01-01', v: 1.2, lower: null, upper: null, missingReason: null, quality: 'declared' },
      { t: '2026-01-02', v: 1.35, lower: null, upper: null, missingReason: null, quality: 'declared' },
      { t: '2026-01-03', v: null, lower: null, upper: null, missingReason: 'not_measured', quality: 'unknown' },
      { t: '2026-01-04', v: 1.41, lower: null, upper: null, missingReason: null, quality: 'declared' },
    ],
  },
];

/** Two casts with irregular pressure levels. */
export const demoVerticalProfiles: readonly VerticalProfile[] = [
  {
    id: 'demo-cast-a',
    name: 'Cast A (synthetic)',
    axis: { kind: 'pressure', unit: 'dbar', label: 'Pressure', direction: 'increasing-down' },
    variables: [
      { key: 'temperature', label: 'Temperature', unit: '°C' },
      { key: 'salinity', label: 'Salinity', unit: 'PSU' },
    ],
    points: [
      {
        coordinate: { kind: 'pressure', value: 0, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 18.4, salinity: 34.1 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 7.3, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 18.1, salinity: 34.2 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 19.6, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: null, salinity: 34.5 },
        validity: 'missing',
        quality: 'unknown',
        missingReason: 'not_measured',
      },
      {
        coordinate: { kind: 'pressure', value: 41.8, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 11.2, salinity: 34.9 },
        validity: 'valid',
        quality: 'provisional',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 88.5, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 6.9, salinity: 35.1 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
    ],
    provenance: [],
  },
  {
    id: 'demo-cast-b',
    name: 'Cast B (synthetic)',
    axis: { kind: 'pressure', unit: 'dbar', label: 'Pressure', direction: 'increasing-down' },
    variables: [
      { key: 'temperature', label: 'Temperature', unit: '°C' },
      { key: 'salinity', label: 'Salinity', unit: 'PSU' },
    ],
    points: [
      {
        coordinate: { kind: 'pressure', value: 0, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 17.9, salinity: 34.0 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 12.1, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 16.4, salinity: 34.3 },
        validity: 'valid',
        quality: 'declared',
        missingReason: null,
      },
      {
        coordinate: { kind: 'pressure', value: 33.4, unit: 'dbar', reference: 'sea surface' },
        values: { temperature: 12.8, salinity: 34.7 },
        validity: 'valid',
        quality: 'approved',
        missingReason: null,
      },
    ],
    provenance: [],
  },
];

/** A scene with points, a zone, and a grid. */
export const demoSpatialScene: SpatialScene = {
  layers: [
    { id: 'demo-stations', label: 'Demo stations', visible: true, kind: 'point', description: 'Invented positions.' },
    { id: 'demo-zone', label: 'Demo basin', visible: true, kind: 'area', description: 'An invented outline.' },
    { id: 'demo-grid', label: 'Demo grid', visible: true, kind: 'grid', description: 'An invented 1 km grid.' },
  ],
  points: [
    {
      id: 'demo-station-1',
      label: 'Demo station Alpha',
      position: [3.05, 50.57],
      kind: 'station',
      layerId: 'demo-stations',
      properties: { country: 'FR', depth_m: 12 },
    },
    {
      id: 'demo-station-2',
      label: 'Demo station Beta',
      position: [2.33, 48.82],
      kind: 'station',
      layerId: 'demo-stations',
      properties: { country: 'FR', depth_m: 4 },
    },
    {
      id: 'demo-station-3',
      label: 'Demo station Gamma',
      position: [-0.57, 44.84],
      kind: 'station',
      layerId: 'demo-stations',
      properties: { country: 'FR', depth_m: null },
    },
  ],
  areas: [
    {
      id: 'demo-basin',
      label: 'Demo basin',
      layerId: 'demo-zone',
      rings: [
        [
          [1.4, 49.6],
          [4.6, 49.6],
          [4.6, 51.4],
          [1.4, 51.4],
          [1.4, 49.6],
        ],
      ],
      fill: 'var(--series-3)',
      fillOpacity: 0.35,
      properties: { area_km2: 8400 },
    },
  ],
  grids: [
    {
      id: 'demo-grid-1',
      label: 'Demo grid',
      layerId: 'demo-grid',
      extent: { west: 2.0, south: 48.5, east: 4.0, north: 50.0 },
      resolutionM: 1000,
      crs: 'EPSG:4326',
    },
  ],
  provenance: [],
};

/** Coverage periods: the four kinds, a gap and an open period. */
export const demoCoveragePeriods: readonly CoveragePeriod[] = [
  {
    id: 'demo-coverage-1',
    subject: 'Demo station Alpha',
    kind: 'observed',
    start: '2024-01-01',
    end: '2025-06-30',
    open: false,
    provenance: [],
  },
  {
    id: 'demo-coverage-2',
    subject: 'Demo station Alpha',
    kind: 'observed',
    start: '2025-09-01',
    end: null,
    open: true,
    provenance: [],
  },
  {
    id: 'demo-coverage-5',
    subject: 'Demo product Beta',
    kind: 'estimated',
    start: '2022-01-01',
    end: '2023-04-01',
    open: false,
    provenance: [],
  },
  {
    id: 'demo-coverage-3',
    subject: 'Demo product Beta',
    kind: 'published',
    start: '2023-04-01',
    end: '2026-02-01',
    open: false,
    provenance: [],
  },
  {
    id: 'demo-coverage-4',
    subject: 'Demo product Beta',
    kind: 'revision',
    start: '2026-02-01',
    end: null,
    open: true,
    provenance: [],
  },
];
