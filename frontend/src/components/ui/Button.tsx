import type { ButtonHTMLAttributes, ReactNode } from 'react';

import './Button.css';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  /** Visual weight. `primary` is the single affirmative action of a view. */
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner and blocks interaction without changing the button width. */
  loading?: boolean;
  /** Stretch to the width of the container. */
  block?: boolean;
  /** Leading icon, decorative by default. */
  icon?: ReactNode;
  /** Trailing icon, decorative by default. */
  trailingIcon?: ReactNode;
  /** The accessible name, when the visible label does not carry it. */
  ariaLabel?: string;
}

/**
 * The button.
 *
 * A button in a loading state keeps its label in the accessibility tree and
 * sets `aria-busy`, so a screen reader announces that the action is running
 * rather than that the control disappeared.
 */
export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  block = false,
  icon,
  trailingIcon,
  ariaLabel,
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  const classes = [
    'torne-button',
    `torne-button--${variant}`,
    `torne-button--${size}`,
    block ? 'torne-button--block' : '',
    loading ? 'torne-button--loading' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      {...rest}
      type={type}
      className={classes}
      disabled={disabled === true || loading}
      aria-busy={loading || undefined}
      aria-label={ariaLabel}
      data-loading={loading || undefined}
    >
      {loading ? <span className="torne-button__spinner" aria-hidden="true" /> : icon}
      {children !== undefined && <span className="torne-button__label">{children}</span>}
      {trailingIcon}
    </button>
  );
}
