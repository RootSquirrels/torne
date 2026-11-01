import type { ReactNode } from 'react';

import './EmptyState.css';

export interface EmptyStateProps {
  /** The headline: what is missing. */
  title: string;
  /** A line that explains what would fill the gap. */
  description?: string;
  /** The action that resolves the gap. */
  action?: ReactNode;
  /** An illustrative glyph. It is decorative. */
  icon?: ReactNode;
}

/**
 * The state of a view that has nothing to show.
 *
 * An empty state is a message, not an error: it says what is missing and,
 * when there is one, what the user can do about it.
 *
 * States: normal, hover (on the action).
 */
export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="torne-empty-state">
      {icon !== undefined && (
        <div className="torne-empty-state__icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <p className="torne-empty-state__title">{title}</p>
      {description !== undefined && (
        <p className="torne-empty-state__description">{description}</p>
      )}
      {action !== undefined && (
        <div className="torne-empty-state__action">{action}</div>
      )}
    </div>
  );
}
