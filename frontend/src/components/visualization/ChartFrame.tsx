/**
 * The chart frame.
 *
 * A chart is drawn on a canvas, and a canvas is invisible to a screen reader.
 * The frame therefore does three things:
 *
 * - it gives the chart a caption that names what is shown and in what unit;
 * - it gives the canvas an accessible name;
 * - it offers the data as a table, so that the chart is not the only way to
 *   read the numbers.
 *
 * The table is visually hidden by default and can be revealed, which keeps it
 * available to assistive technology without cluttering the page.
 *
 * The frame is the **bezel** of the instrument: the caption above, the well
 * the plot sits in, the disclosure below. The unit travels on a *label
 * plate* beside the title — the place where a reader looks for it — and the
 * axis does not repeat it.
 */
import type { ReactNode } from 'react';

import './ChartFrame.css';

export interface ChartPlate {
  /** What the plate states. */
  readonly label: string;
  /**
   * The tone of the plate.
   *
   * `warning` is for a statement that is true but not established — a unit
   * the series disagree on. It is worth a warning, not an alarm.
   */
  readonly tone?: 'neutral' | 'warning';
}

export interface ChartFrameProps {
  /** The title of the figure. */
  readonly title: string;
  /** What the figure shows, in one sentence. */
  readonly description?: string | null;
  /** The accessible name of the canvas. */
  readonly ariaLabel: string;
  /** The chart itself. */
  readonly children: ReactNode;
  /**
   * The data as an accessible table.
   *
   * When it is absent, the chart has no readable equivalent: the frame says
   * so rather than pretending otherwise.
   */
  readonly table?: ReactNode;
  /** A note under the figure, e.g. the source of the values. */
  readonly footnote?: ReactNode;
  /** Actions shown beside the title. */
  readonly actions?: ReactNode;
  /** The plate beside the title: the unit, or the fact that it is not established. */
  readonly plate?: ChartPlate | null;
}

export function ChartFrame({
  title,
  description,
  ariaLabel,
  children,
  table,
  footnote,
  actions,
  plate = null,
}: ChartFrameProps) {
  return (
    <figure className="torne-chart-frame">
      <figcaption className="torne-chart-frame__caption">
        <span className="torne-chart-frame__titles">
          <span className="torne-chart-frame__head">
            <span className="torne-chart-frame__title">{title}</span>
            {plate !== null ? (
              <span className="torne-chart-frame__plate" data-tone={plate.tone ?? 'neutral'}>
                {plate.label}
              </span>
            ) : null}
          </span>
          {description !== null && description !== undefined ? (
            <span className="torne-chart-frame__description">{description}</span>
          ) : null}
        </span>
        {actions !== undefined ? (
          <span className="torne-chart-frame__actions">{actions}</span>
        ) : null}
      </figcaption>

      <div className="torne-chart-frame__plot" role="img" aria-label={ariaLabel}>
        {children}
      </div>

      {table !== undefined ? (
        <details className="torne-chart-frame__table">
          <summary>Show the values as a table</summary>
          <div className="torne-chart-frame__table-body">{table}</div>
        </details>
      ) : null}

      {footnote !== undefined ? (
        <p className="torne-chart-frame__footnote">{footnote}</p>
      ) : null}
    </figure>
  );
}
