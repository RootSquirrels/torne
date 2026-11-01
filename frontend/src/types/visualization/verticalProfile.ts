/**
 * The vertical profile contract.
 *
 * A vertical profile is a set of measurements taken along a vertical axis:
 * oceanographic casts, atmospheric soundings, model levels.
 *
 * The axis is the delicate part, and the contract keeps it honest:
 *
 * - **pressure is never depth.** A coordinate declares its physical nature,
 *   its unit and its reference, and the component never converts one into the
 *   other;
 * - **a model level is never a distance.** A level index is carried as an
 *   index, with the unit `level`;
 * - **the axis direction is declared, not guessed.** Depth grows downward and
 *   pressure grows upward; the profile says which it is, and the component
 *   inverts the axis accordingly.
 */

import type { ApiRef } from '@/types/api/manifest';
import type { MissingReason, PointValidity, QualityStatus } from '@/types/visualization/vocabulary';

/** The physical nature of a vertical coordinate. */
export type VerticalCoordinateKind = 'pressure' | 'depth' | 'model-level';

/**
 * One position on the vertical axis.
 *
 * The value is expressed in the unit the coordinate declares, and the
 * reference says what it is measured against — sea surface, sea water,
 * standard atmosphere, or a model.
 */
export interface VerticalCoordinate {
  readonly kind: VerticalCoordinateKind;
  /** The value, in the coordinate's own unit. */
  readonly value: number;
  /** The unit of the value: `dbar`, `m`, or `level` for a model level. */
  readonly unit: string;
  /** What the value is measured against. */
  readonly reference: string;
}

/** The vertical axis of a profile. */
export interface VerticalAxis {
  readonly kind: VerticalCoordinateKind;
  /** The unit of the axis. */
  readonly unit: string;
  /** The name of the axis, as it is written on the chart. */
  readonly label: string;
  /** Whether the axis grows upward or downward. */
  readonly direction: 'increasing-up' | 'increasing-down';
}

/** A variable measured along the profile. */
export interface VerticalVariable {
  /** A stable key, used to address the variable in a point. */
  readonly key: string;
  /** The name of the variable, e.g. "Temperature". */
  readonly label: string;
  /** The unit of the variable, or null when it is not established. */
  readonly unit: string | null;
}

/** One level of a profile. */
export interface VerticalProfilePoint {
  /** Where on the vertical axis this level sits. */
  readonly coordinate: VerticalCoordinate;
  /**
   * The values measured at this level, keyed by variable.
   *
   * A variable that was not measured at this level is absent from the record,
   * or present with a null value: either way it is not a zero.
   */
  readonly values: Readonly<Record<string, number | null>>;
  /** Whether the level holds a usable value. */
  readonly validity: PointValidity;
  /** The quality the source declared for this level. */
  readonly quality: QualityStatus;
  /** Why the level is absent, when it is. Null when the level was measured. */
  readonly missingReason: MissingReason | null;
}

/** A vertical profile: a set of levels and the variables measured on them. */
export interface VerticalProfile {
  /** A stable identity, unique within its chart. */
  readonly id: string;
  /** The name of the profile, e.g. "Cast 2026-04-11". */
  readonly name: string;
  /** The vertical axis. Every level of the profile must use the same kind. */
  readonly axis: VerticalAxis;
  /** The variables measured along the profile. */
  readonly variables: readonly VerticalVariable[];
  /** The levels, in the order the source gave them. */
  readonly points: readonly VerticalProfilePoint[];
  /** The provenance of the profile. */
  readonly provenance: readonly ApiRef[];
}
