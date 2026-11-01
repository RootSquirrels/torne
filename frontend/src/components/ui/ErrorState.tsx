import { Button } from './Button';

import './ErrorState.css';

export interface ErrorStateProps {
  /** The headline: what went wrong. */
  title?: string;
  /** The detail. It is shown verbatim, whatever it says. */
  message: string;
  /** Called when the retry button is pressed. The button is hidden without it. */
  onRetry?: () => void;
  /** The text of the retry button. */
  retryLabel?: string;
}

/**
 * The state of a view that failed.
 *
 * The region is an alert: the failure is announced as soon as it happens,
 * because the user asked for the content and did not get it. The message is
 * never paraphrased — it comes from the API and it is the truth.
 *
 * States: error, hover and focus (on the retry button), disabled (on it).
 */
export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryLabel = 'Retry',
}: ErrorStateProps) {
  return (
    <div className="torne-error-state" role="alert">
      <p className="torne-error-state__title">{title}</p>
      <p className="torne-error-state__message">{message}</p>
      {onRetry !== undefined && (
        <div className="torne-error-state__action">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
