import './StatusIndicator.css';

export interface StatusIndicatorProps {
  /** The status in words, as the API spells it. */
  status: string;
  /** The rank of the status on the ordinal science ramp: 0 is "not covered". */
  rank: number;
  /** Whether the status text is visible next to the swatch. */
  showLabel?: boolean;
}

/** The ramp has five steps; anything outside is clamped onto its ends. */
function clampRank(rank: number): number {
  if (!Number.isFinite(rank)) {
    return 0;
  }
  return Math.min(4, Math.max(0, Math.round(rank)));
}

/**
 * The mission status, on the ordinal science ramp.
 *
 * The ramp is sequential by construction — one hue, rising lightness — so the
 * colour says *how far along* a mission is, and never *which* mission. The
 * rank selects a modifier class, and that class paints the swatch with the
 * `--science-status-<rank>` token and the text written on it with the
 * matching `--science-status-<rank>-ink` token, which is the only pairing
 * that stays legible across the ramp.
 *
 * The status text is always present for assistive technology; `showLabel`
 * only decides whether a sighted user reads it too.
 *
 * States: normal, hover (no visual change).
 */
export function StatusIndicator({
  status,
  rank,
  showLabel = true,
}: StatusIndicatorProps) {
  const step = clampRank(rank);

  return (
    <span className={`torne-status-indicator torne-status-indicator--rank-${step}`} data-rank={step}>
      <span className="torne-status-indicator__swatch">
        {showLabel ? (
          status
        ) : (
          <span className="torne-visually-hidden">{status}</span>
        )}
      </span>
    </span>
  );
}
