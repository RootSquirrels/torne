/**
 * The furniture of a reading page.
 *
 * The anatomy is the explorer's: an eyebrow that names the kind of thing
 * being read, a title, a lede that says what the page shows, and sections
 * whose heading is a quiet eyebrow. The reader navigates by the headings, so
 * they stay real headings.
 */
import type { ReactNode } from 'react';

export interface PageHeaderProps {
  /** What kind of thing is being read. */
  readonly eyebrow: string;
  readonly title: string;
  /** One sentence on what the page shows. */
  readonly lede?: string;
  readonly meta?: ReactNode;
}

/**
 * The header of a page.
 *
 * This block is the only place on the page where a shadow is allowed: it is
 * the one element that lifts off the page it is printed on.
 */
export function PageHeader({ eyebrow, title, lede, meta }: PageHeaderProps) {
  return (
    <header className="torne-supply__page-header">
      <p className="torne-supply__eyebrow">{eyebrow}</p>
      <h2 className="torne-supply__title">{title}</h2>
      {lede !== undefined ? <p className="torne-supply__lede">{lede}</p> : null}
      {meta !== undefined ? <p className="torne-supply__meta">{meta}</p> : null}
    </header>
  );
}

export interface SectionProps {
  /** The heading of the section. */
  readonly title: string;
  /** A quiet note beside the heading: the counts, the period. */
  readonly note?: ReactNode;
  readonly children?: ReactNode;
}

/**
 * A section of the page.
 *
 * The heading is an eyebrow — small, uppercase, quiet — because the reader
 * navigates by it, not by its size.
 */
export function Section({ title, note, children }: SectionProps) {
  return (
    <section className="torne-supply__section">
      <div className="torne-supply__section-heading">
        <h3 className="torne-supply__section-title">{title}</h3>
        {note !== undefined ? <span className="torne-supply__section-note">{note}</span> : null}
      </div>
      {children !== undefined ? (
        <div className="torne-supply__section-body">{children}</div>
      ) : null}
    </section>
  );
}

/**
 * A line of the reading column: a fact, and the value that carries it.
 *
 * The name of the fact is quiet and the value is set in the mono face,
 * because a value is a figure and not a word.
 */
export function Fact({
  name,
  children,
}: {
  readonly name: string;
  readonly children: ReactNode;
}) {
  return (
    <div className="torne-supply__fact">
      <dt className="torne-supply__fact-name">{name}</dt>
      <dd className="torne-supply__fact-value">{children}</dd>
    </div>
  );
}
