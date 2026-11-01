/**
 * The time series contract.
 *
 * A time series here is **not** a list of numeric pairs. It carries what makes
 * the numbers mean something: the variable, the unit, the temporal frequency,
 * the temporal reference, the nature of the values, and the provenance.
 *
 * Three rules the components rely on:
 *
 * 1. **A hole is a hole.** A point with no value breaks the line. Nothing is
 *    interpolated across it, and an absence is never drawn as zero.
 * 2. **A nature is a nature.** An observation is not an estimate and not a
 *    forecast, and the chart says which it is — by dash pattern as well as by
 *    colour, so the distinction survives a colourblind reader.
 * 3. **An unknown unit is unknown.** The chart says "unit not established"
 *    rather than inventing one.
 */

import type { ApiRef } from '@/types/api/manifest';
import type { MissingReason, QualityStatus } from '@/types/visualization/vocabulary';

/** What the values of a series are. */
export type SeriesNature = 'observation' | 'estimate' | 'forecast' | 'simulation';

/** How often a series is measured. */
export type TemporalFrequency =
  | 'sub-minute'
  | 'minute'
  | 'hourly'
  | 'daily'
  | 'weekly'
  | 'monthly'
  | 'quarterly'
  | 'annual'
  | 'irregular';

/**
 * The temporal reference the instants are taken in.
 *
 * A civil-day series is not an instant series: the day is a calendar day in a
 * named zone. The chart must know which it has.
 */
export interface TemporalReference {
  /** Whether the stamps are instants or civil days. */
  readonly basis: 'instant' | 'civil-day';
  /** The time zone the civil day is taken in. Null when the basis is an instant. */
  readonly timeZone: string | null;
}

/** One observation of a series. */
export interface TimeSeriesPoint {
  /** The instant, as an ISO 8601 string, or the civil day as an ISO date. */
  readonly t: string;
  /** The value, or null when the measurement is absent. */
  readonly v: number | null;
  /** The lower bound of the uncertainty, when one is established. Null otherwise. */
  readonly lower: number | null;
  /** The upper bound of the uncertainty, when one is established. Null otherwise. */
  readonly upper: number | null;
  /** Why the value is absent. Null when the value is present. */
  readonly missingReason: MissingReason | null;
  /** The quality the source declared. `unknown` when the source said nothing. */
  readonly quality: QualityStatus;
}

/** A series of values over time, with everything needed to read them. */
export interface TimeSeries {
  /** A stable identity, unique within its chart. */
  readonly id: string;
  /** The name of the variable, e.g. "Discharge". */
  readonly variable: string;
  /** The unit of the values, or null when it is not established. */
  readonly unit: string | null;
  /** How often the series is measured. */
  readonly frequency: TemporalFrequency;
  /** The temporal reference the instants are taken in. */
  readonly reference: TemporalReference;
  /** What the values are. */
  readonly nature: SeriesNature;
  /**
   * For a mixed series: the instant from which the values are an estimate
   * rather than an observation. Null when the series has a single nature.
   */
  readonly estimateFrom: string | null;
  /**
   * For a mixed series: the instant from which the values are a forecast
   * rather than an observation. Null when the series has a single nature.
   */
  readonly forecastFrom: string | null;
  /** The values, in time order. */
  readonly points: readonly TimeSeriesPoint[];
  /** The provenance of the series. */
  readonly provenance: readonly ApiRef[];
}

/**
 * A band of values, drawn across the chart: a climatological normal, a
 * threshold, a regulatory limit.
 */
export interface ReferenceBand {
  readonly id: string;
  readonly label: string;
  /** The lower bound of the band. Null when the band is unbounded below. */
  readonly lower: number | null;
  /** The upper bound of the band. Null when the band is unbounded above. */
  readonly upper: number | null;
  /** When the band starts. Null when it spans the whole axis. */
  readonly start: string | null;
  /** When the band ends. Null when it spans the whole axis. */
  readonly end: string | null;
  readonly tone: 'neutral' | 'info' | 'warning' | 'danger';
}

/** A point-in-time annotation: a detected break, a station move, a publication. */
export interface TimeMarker {
  readonly id: string;
  readonly label: string;
  /** The instant of the marker. */
  readonly at: string;
  readonly tone: 'neutral' | 'info' | 'warning' | 'danger';
}

/** A named span of time, drawn under the axis: a period of record, an epoch. */
export interface TimeSpan {
  readonly id: string;
  readonly label: string;
  /** When the span starts. Null when it is open at the start. */
  readonly start: string | null;
  /** When the span ends. Null when it is open at the end. */
  readonly end: string | null;
}
