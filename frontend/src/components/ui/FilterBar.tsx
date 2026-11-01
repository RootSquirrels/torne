import type { ReactNode } from 'react';

import { Button } from './Button';

import './FilterBar.css';

export interface FilterBarProps {
  /** The filter controls. */
  children: ReactNode;
  /** Called when the reset button is pressed. The button is hidden without it. */
  onReset?: () => void;
  /** The text of the reset button. */
  resetLabel?: string;
}

/**
 * The bar that groups the filters of a view.
 *
 * It is a `search` landmark, so a screen reader can list the places where the
 * user can search, and it is a form, so `Enter` in a field submits the bar
 * rather than the page. The reset button sits at the end of the bar.
 *
 * States: normal, hover, focus, disabled (on the reset button).
 */
export function FilterBar({ children, onReset, resetLabel = 'Reset filters' }: FilterBarProps) {
  return (
    <form
      className="torne-filter-bar"
      role="search"
      aria-label="Filters"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      <div className="torne-filter-bar__controls">{children}</div>
      {onReset !== undefined && (
        <div className="torne-filter-bar__actions">
          <Button variant="ghost" size="sm" onClick={onReset}>
            {resetLabel}
          </Button>
        </div>
      )}
    </form>
  );
}
