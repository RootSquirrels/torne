/**
 * The coverage timeline contract.
 *
 * A coverage timeline shows **what periods exist**, and what is missing from
 * them. It distinguishes:
 *
 * - an *observed* period, established by measurement;
 * - an *estimated* period, reconstructed rather than measured;
 * - a *published* period, made available by a producer;
 * - a *revision*, a later version of a period already covered;
 * - a *gap*, an absence **between** two periods of the same subject.
 *
 * The gap is not a period: it is the absence of one, and it is drawn as such.
 * A timeline that hid the gaps would claim a continuity the data does not
 * have.
 */

import type { ApiRef } from '@/types/api/manifest';

/** What a covered period is. */
export type CoverageKind = 'observed' | 'estimated' | 'published' | 'revision';

/** One covered period. */
export interface CoveragePeriod {
  readonly id: string;
  /** The name of the subject the period belongs to, e.g. a station. */
  readonly subject: string;
  /** What the period is. */
  readonly kind: CoverageKind;
  /** When the period starts, as an ISO instant or an ISO date. Null when unknown. */
  readonly start: string | null;
  /** When the period ends, as an ISO instant or an ISO date. Null when unknown. */
  readonly end: string | null;
  /** Whether the period is still open — still producing, not finished. */
  readonly open: boolean;
  /** The provenance of the period. */
  readonly provenance: readonly ApiRef[];
}

/**
 * The availability of a subject at a given instant, when it is known.
 *
 * The repository distinguishes the instant a datum became *usable* from the
 * instant it was *published*; this contract carries the usable one, which is
 * what a reader asking "what did I know on that day?" needs.
 */
export interface CoverageAvailability {
  /** The subject the availability applies to. */
  readonly subject: string;
  /** The instant the question is asked at. */
  readonly at: string;
  /** Whether the subject's data was available at that instant. Null when unknown. */
  readonly available: boolean | null;
  /** The provenance of the answer. */
  readonly provenance: readonly ApiRef[];
}
