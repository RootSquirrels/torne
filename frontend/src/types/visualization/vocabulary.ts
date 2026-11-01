/**
 * The vocabularies the displayable data carries.
 *
 * These mirror the closed vocabularies of the scientific engine
 * (`torne.contracts.validity`, `torne.contracts.time`,
 * `torne.contracts.observation`). They are **not** a second definition of the
 * physics: they are the representation contract for what the API exposes. The
 * words are the engine's, so a value read here and a value read in Python
 * mean the same thing.
 *
 * The rules they encode:
 *
 * - an absent value is absent, never zero;
 * - an absence always carries its reason;
 * - a value that the source says nothing about is `unknown`, not `approved`.
 */

/**
 * Whether a point holds a usable value.
 *
 * `missing` means the measurement was not made; `invalid` means it was made
 * and does not hold; `out_of_domain` means it falls outside what the method
 * applies to.
 */
export type PointValidity = 'valid' | 'missing' | 'invalid' | 'out_of_domain';

/** Why a value is absent. */
export type MissingReason = 'not_measured' | 'not_yet_published' | 'not_attempted';

/**
 * What the source declared about the quality of a value.
 *
 * `unknown` is the safe choice: a source that says nothing is not a source
 * that approves.
 */
export type QualityStatus =
  | 'declared'
  | 'source_estimated'
  | 'provisional'
  | 'approved'
  | 'unknown';

/** Whether the instant at which a datum became available is established. */
export type PublicationState = 'established' | 'bounded' | 'unknown';
