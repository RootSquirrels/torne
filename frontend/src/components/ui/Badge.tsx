import type { ReactNode } from 'react';

import './Badge.css';

export type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';
export type BadgeSize = 'sm' | 'md';

export interface BadgeProps {
  children: ReactNode;
  /** The semantic register the badge belongs to. */
  tone?: BadgeTone;
  size?: BadgeSize;
}

/**
 * A short, coloured label.
 *
 * The tones answer "is this a problem?", never "which series is this?": they
 * map onto the `--semantic-*` tokens, not onto the categorical series
 * palette. A badge is never the only carrier of its meaning — the text
 * inside says the same thing as the colour.
 *
 * States: normal, hover (no visual change), focus (on the parent control).
 */
export function Badge({ children, tone = 'neutral', size = 'md' }: BadgeProps) {
  const classes = [
    'torne-badge',
    `torne-badge--${tone}`,
    `torne-badge--${size}`,
  ].join(' ');

  return <span className={classes}>{children}</span>;
}
