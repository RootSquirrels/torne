import { useId } from 'react';
import type { ReactNode } from 'react';

import './Panel.css';

export interface PanelProps {
  /** The section's heading. It names the region. */
  title: string;
  /** A line under the heading. */
  description?: string;
  children: ReactNode;
  /** A footer strip, separated from the body by a rule. */
  footer?: ReactNode;
  /** Whether the body scrolls instead of growing. */
  scrollable?: boolean;
}

/**
 * A titled section of the page.
 *
 * The panel is a `section` named by its heading, so a screen reader can jump
 * straight to it. The heading is a level-two heading: a panel is a region of
 * the page, below the page title and above the cards it holds.
 *
 * States: normal, hover (no visual change), focus (on the content).
 */
export function Panel({
  title,
  description,
  children,
  footer,
  scrollable = false,
}: PanelProps) {
  const headingId = `torne-panel-${useId()}`;
  const bodyClasses = scrollable
    ? 'torne-panel__body torne-panel__body--scrollable'
    : 'torne-panel__body';

  return (
    <section className="torne-panel" aria-labelledby={headingId}>
      <header className="torne-panel__header">
        <h2 className="torne-panel__title" id={headingId}>
          {title}
        </h2>
        {description !== undefined && (
          <p className="torne-panel__description">{description}</p>
        )}
      </header>
      <div className={bodyClasses}>{children}</div>
      {footer !== undefined && (
        <footer className="torne-panel__footer">{footer}</footer>
      )}
    </section>
  );
}
