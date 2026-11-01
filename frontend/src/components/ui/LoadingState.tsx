import './LoadingState.css';

export interface LoadingStateProps {
  /** What is being loaded. */
  label?: string;
}

/**
 * The state of a view that is still loading.
 *
 * The region is a polite live status: a screen reader announces that
 * something is happening without interrupting the user, and `aria-busy`
 * tells assistive technology that the content is not ready yet. The spinner
 * is decorative — the label carries the meaning.
 *
 * States: loading.
 */
export function LoadingState({ label = 'Loading…' }: LoadingStateProps) {
  return (
    <div
      className="torne-loading-state"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className="torne-loading-state__spinner" aria-hidden="true" />
      <span className="torne-loading-state__label">{label}</span>
    </div>
  );
}
