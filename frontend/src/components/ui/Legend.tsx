import type { CSSProperties } from 'react';

import './Legend.css';

export type LegendShape = 'square' | 'circle' | 'line' | 'dash' | 'empty';

export interface LegendItem {
  /** The name of the series or category. */
  label: string;
  /**
   * The colour of the swatch.
   *
   * The caller passes a resolved colour — a `var(--series-*)` reference or a
   * literal — because only the caller knows which register the colour comes
   * from.
   */
  color?: string;
  /** The shape of the swatch. */
  shape?: LegendShape;
  /** A short explanation of what the entry means. */
  description?: string;
}

export interface LegendProps {
  items: ReadonlyArray<LegendItem>;
  title?: string;
  /**
   * How the entries are laid out.
   *
   * `column` is for a key that stands beside a figure, where the names are
   * read one under the other. `row` is for a short key that sits on the same
   * line as the title of a figure.
   */
  readonly orientation?: 'column' | 'row';
}

/**
 * The key that explains a chart.
 *
 * The swatch repeats the shape the chart uses, so an entry is never carried
 * by colour alone: a dashed series is dashed in the legend too. The colour
 * comes from the caller, because only the caller knows which register it
 * belongs to.
 *
 * The `empty` swatch is an outlined but unfilled square: it is what a chart
 * uses for an absence — a gap, a period that does not exist — so that the
 * absence is drawn and not merely named.
 *
 * States: normal, hover (no visual change).
 */
export function Legend({ items, title, orientation = 'column' }: LegendProps) {
  return (
    <div className={`torne-legend torne-legend--${orientation}`}>
      {title !== undefined && <p className="torne-legend__title">{title}</p>}
      <ul className="torne-legend__items">
        {items.map((item) => {
          const shape = item.shape ?? 'square';
          const color = item.color ?? 'var(--content-secondary)';
          const isLine = shape === 'line' || shape === 'dash';
          const swatchStyle: CSSProperties =
            shape === 'empty'
              ? { borderColor: color }
              : isLine
                ? { borderTopColor: color }
                : { backgroundColor: color };

          return (
            <li className="torne-legend__item" key={item.label}>
              <span
                className={`torne-legend__swatch torne-legend__swatch--${shape}`}
                style={swatchStyle}
                aria-hidden="true"
              />
              <span className="torne-legend__label">{item.label}</span>
              {item.description !== undefined && (
                <span className="torne-legend__description">{item.description}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
