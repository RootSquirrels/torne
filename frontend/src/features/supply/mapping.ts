/**
 * The mapping from the API's product to what the page shows.
 *
 * The product is read, never interpreted: every number the page shows comes
 * from the payload, every label comes from the product's own vocabulary, and
 * every unit comes from the units the product declares. Two rules shape the
 * whole module:
 *
 * - **an absence stays an absence.** A measure the product did not establish
 *   is `null` here and stays `null` all the way to the screen: it is never
 *   turned into a zero, a series that has a hole in it keeps the hole, and an
 *   entity that published nothing is an absence, not a missing row;
 * - **a flag is not a value.** A flag says what is true of a state, and it is
 *   kept apart from the measures, so that the two are never mixed up in a
 *   table, in a chart or in a colour.
 *
 * The module is pure: it reads the API's shapes and returns the shapes the
 * page draws. That is what makes it testable without a browser.
 */
import type { ApiProductDetail, ApiProductState } from '@/types/api/manifest';
import type { TimeSeries, TimeSeriesPoint } from '@/types/visualization/timeSeries';

/** What the page writes when a value was not established. */
export const NOT_ESTABLISHED = 'not established';

/** What the page writes when an entity published no state at all. */
export const NO_STATE_PUBLISHED = 'no state published';

/** A measure the layer publishes, with the unit the product declares for it. */
export interface SupplyMeasure {
  /** The column the value is read from. */
  readonly column: string;
  /** The label the product gives the measure. */
  readonly label: string;
  /** The unit the product declares, or null when it declares none. */
  readonly unit: string | null;
}

/** A flag the layer publishes: what is true of a state, apart from its values. */
export interface SupplyFlag {
  readonly column: string;
  readonly label: string;
}

/** The period a layer covers. */
export interface SupplyWindow {
  readonly start: string | null;
  readonly end: string | null;
  readonly states: number | null;
  readonly entities: number | null;
}

/** One layer of the product: what it holds, and the columns it is made of. */
export interface SupplyLayer {
  readonly id: string;
  readonly title: string;
  readonly file: string | null;
  readonly window: SupplyWindow;
  readonly measures: readonly SupplyMeasure[];
  readonly flags: readonly SupplyFlag[];
  /** Whether the layer places its entities on the map. */
  readonly positioned: boolean;
  readonly entityColumn: string;
  readonly labelColumn: string;
  readonly countryColumn: string;
  readonly dayColumn: string;
}

/** One published state, with its values and its flags kept apart. */
export interface SupplyState {
  readonly entity: string;
  readonly label: string;
  readonly country: string;
  readonly day: string;
  readonly publishedAt: string | null;
  /** The values, with null where the product established nothing. */
  readonly values: Readonly<Record<string, number | null>>;
  /** The flags, with null where the product said nothing. */
  readonly flags: Readonly<Record<string, boolean | null>>;
  readonly latitude: number | null;
  readonly longitude: number | null;
}

// ------------------------------------------------------------------ narrowing

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function asText(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asCount(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asTextList(value: unknown): readonly string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === 'string');
}

/**
 * A value, or its absence.
 *
 * Anything that is not a number is an absence: a value the product did not
 * establish is `null`, and it is never read as a zero.
 */
export function numberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** A flag, or the fact that the product said nothing about it. */
export function booleanOrNull(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

// --------------------------------------------------------------------- layers

function readMeasures(
  layerId: string,
  rawMeasures: unknown,
  rawUnits: unknown,
): readonly SupplyMeasure[] {
  const measures = asRecord(rawMeasures);
  const units = asRecord(asRecord(rawUnits)[layerId]);

  return Object.entries(measures).map(([column, raw]) => {
    const measure = asRecord(raw);
    // The label comes from the layer; the unit comes from the product's
    // units, which is where the product declares it once and for all.
    const unit = asText(units[column]);
    return {
      column,
      label: asText(measure['label']) ?? column,
      unit,
    };
  });
}

function readFlags(rawFlags: unknown): readonly SupplyFlag[] {
  return Object.entries(asRecord(rawFlags)).map(([column, raw]) => {
    const flag = asRecord(raw);
    return { column, label: asText(flag['label']) ?? column };
  });
}

function readWindow(rawWindow: unknown): SupplyWindow {
  const window = asRecord(rawWindow);
  return {
    start: asText(window['start']),
    end: asText(window['end']),
    states: asCount(window['states']),
    entities: asCount(window['entities']),
  };
}

/**
 * The layers the product publishes.
 *
 * The layers are read from the product's own map: nothing here decides which
 * layers exist, and nothing is hardcoded. A layer that cannot be read is
 * left out rather than shown empty.
 */
export function readLayers(detail: ApiProductDetail): readonly SupplyLayer[] {
  const layers = asRecord(detail.layers);
  const windows = asRecord(detail.windows);
  const units = asRecord(detail.units)['measures'];

  const result: SupplyLayer[] = [];
  for (const [id, raw] of Object.entries(layers)) {
    const layer = asRecord(raw);
    const title = asText(layer['title']);
    if (title === null) {
      continue;
    }
    result.push({
      id: asText(layer['id']) ?? id,
      title,
      file: asText(layer['file']),
      window: readWindow(windows[id]),
      measures: readMeasures(id, layer['measures'], units),
      flags: readFlags(layer['flags']),
      positioned: asTextList(layer['position_columns']).length > 0,
      entityColumn: asText(layer['entity_column']) ?? 'entity',
      labelColumn: asText(layer['label_column']) ?? 'label',
      countryColumn: asText(layer['country_column']) ?? 'country',
      dayColumn: asText(layer['day_column']) ?? 'day',
    });
  }
  return result;
}

/** The layer that places its entities on the map, when the product has one. */
export function positionedLayer(layers: readonly SupplyLayer[]): SupplyLayer | null {
  return layers.find((layer) => layer.positioned) ?? null;
}

// --------------------------------------------------------------------- states

/**
 * The published states, read.
 *
 * The values are narrowed one by one: what is not a number is an absence,
 * and what is not a boolean is a flag the product did not declare.
 */
export function readStates(states: readonly ApiProductState[]): readonly SupplyState[] {
  return states.map((state) => {
    const values: Record<string, number | null> = {};
    for (const [column, value] of Object.entries(state.values)) {
      values[column] = numberOrNull(value);
    }
    const flags: Record<string, boolean | null> = {};
    for (const [column, value] of Object.entries(state.flags)) {
      flags[column] = booleanOrNull(value);
    }
    return {
      entity: state.entity,
      label: state.label,
      country: state.country,
      day: state.gas_day,
      publishedAt: state.published_at,
      values,
      flags,
      latitude: numberOrNull(state.latitude),
      longitude: numberOrNull(state.longitude),
    };
  });
}

// ------------------------------------------------------------------- absences

/**
 * The names the indicators use for the entities that published no state.
 *
 * The two layers do not name them the same way: one of them counts
 * installations, the other counts countries. Both names are read, and the
 * list a layer actually carries is the one that is returned.
 */
const ABSENCE_NAMES = ['countries_without_published_state', 'installations_without_data'] as const;

/**
 * The entities a layer declares as having published no state.
 *
 * A layer that publishes states for some of the entities it covers says which
 * ones it did not. They are declared absences: they are shown, and they are
 * never shown as zeros.
 */
export function declaredAbsences(detail: ApiProductDetail, layerId: string): readonly string[] {
  const indicators = asRecord(asRecord(detail.indicators)[layerId]);
  for (const name of ABSENCE_NAMES) {
    const absences = asTextList(indicators[name]);
    if (absences.length > 0) {
      return absences;
    }
  }
  return [];
}

/** The entities a layer covers, whether they published a state or not. */
export function declaredCoverage(detail: ApiProductDetail, layerId: string): readonly string[] {
  const indicators = asRecord(asRecord(detail.indicators)[layerId]);
  return asTextList(indicators['coverage']);
}

// --------------------------------------------------------------------- series

/**
 * The series of one measure, for one entity.
 *
 * A day the product did not establish keeps its hole: the point's value is
 * `null` and the chart breaks the line there. Nothing is interpolated, and
 * nothing is drawn as a zero.
 */
export function toSeries(
  states: readonly SupplyState[],
  measure: SupplyMeasure,
  entity: string,
): TimeSeries {
  const points: TimeSeriesPoint[] = states.map((state) => {
    const value = state.values[measure.column] ?? null;
    return {
      t: state.day,
      v: value,
      lower: null,
      upper: null,
      missingReason: value === null ? 'not_measured' : null,
      quality: 'declared',
    };
  });

  return {
    id: `${entity}:${measure.column}`,
    variable: measure.label,
    unit: measure.unit,
    frequency: 'daily',
    reference: { basis: 'civil-day', timeZone: 'UTC' },
    nature: 'observation',
    estimateFrom: null,
    forecastFrom: null,
    points,
    provenance: [],
  };
}

// ------------------------------------------------------------------- formatting

/**
 * A value as the page writes it.
 *
 * An absent value is written as an absence; it is never written as a zero.
 */
export function formatValue(value: number | null): string {
  if (value === null) {
    return NOT_ESTABLISHED;
  }
  if (Number.isInteger(value)) {
    return String(value);
  }
  return String(Number(value.toPrecision(6)));
}

/**
 * A relative difference, as the percentage it is.
 *
 * The product publishes a fraction; a percentage is the same quantity in
 * another unit, not another measurement.
 */
export function formatRelative(value: number | null): string {
  if (value === null) {
    return NOT_ESTABLISHED;
  }
  return `${(value * 100).toFixed(2)} %`;
}
