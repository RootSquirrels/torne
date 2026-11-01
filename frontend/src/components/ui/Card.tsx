import type { ReactNode } from 'react';

import './Card.css';

export interface CardProps {
  /** The card's heading. */
  title?: string;
  /** A line under the heading. */
  subtitle?: string;
  /** Controls shown at the top right of the card. */
  actions?: ReactNode;
  children: ReactNode;
  /** Whether the body is inset from the card edges. */
  padded?: boolean;
  /** A footer strip, separated from the body by a rule. */
  footer?: ReactNode;
}

/**
 * A surface with an optional header and footer.
 *
 * The card is an `article`: it is a self-contained piece of content, not a
 * region of the page. Its heading is a level-three heading, so a card sits
 * below the title of the page or section that contains it.
 *
 * States: normal, hover (the surface lifts slightly), focus (on the actions).
 */
export function Card({
  title,
  subtitle,
  actions,
  children,
  padded = false,
  footer,
}: CardProps) {
  const hasHeader = title !== undefined || subtitle !== undefined || actions !== undefined;
  const bodyClasses = padded
    ? 'torne-card__body torne-card__body--padded'
    : 'torne-card__body';

  return (
    <article className="torne-card">
      {hasHeader && (
        <header className="torne-card__header">
          <div className="torne-card__heading">
            {title !== undefined && <h3 className="torne-card__title">{title}</h3>}
            {subtitle !== undefined && (
              <p className="torne-card__subtitle">{subtitle}</p>
            )}
          </div>
          {actions !== undefined && (
            <div className="torne-card__actions">{actions}</div>
          )}
        </header>
      )}
      <div className={bodyClasses}>{children}</div>
      {footer !== undefined && <footer className="torne-card__footer">{footer}</footer>}
    </article>
  );
}
