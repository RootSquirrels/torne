import type { ReactNode } from 'react';

import './IconButton.css';

export type IconButtonVariant = 'secondary' | 'ghost' | 'danger';
export type IconButtonSize = 'sm' | 'md';

export interface IconButtonProps {
  /** The glyph to render. It is decorative: the accessible name is `label`. */
  icon: ReactNode;
  /** The accessible name and the tooltip text. Never empty. */
  label: string;
  onClick?: () => void;
  /** Visual weight. `danger` is reserved for destructive actions. */
  variant?: IconButtonVariant;
  size?: IconButtonSize;
  disabled?: boolean;
  /**
   * Marks the button as a toggle and reflects its state.
   *
   * When it is `undefined` the button is an ordinary action button and no
   * `aria-pressed` attribute is emitted at all.
   */
  pressed?: boolean;
  type?: 'button' | 'submit';
}

/**
 * A square, icon-only button.
 *
 * The icon never carries the name: `label` is required and becomes both the
 * accessible name and the native tooltip, so the control is usable with a
 * screen reader and discoverable with a mouse.
 *
 * States: normal, hover, focus, pressed (toggle), disabled.
 */
export function IconButton({
  icon,
  label,
  onClick,
  variant = 'secondary',
  size = 'md',
  disabled = false,
  pressed,
  type = 'button',
}: IconButtonProps) {
  const classes = [
    'torne-icon-button',
    `torne-icon-button--${variant}`,
    `torne-icon-button--${size}`,
  ].join(' ');

  return (
    <button
      type={type}
      className={classes}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={pressed}
      title={label}
    >
      <span className="torne-icon-button__icon" aria-hidden="true">
        {icon}
      </span>
    </button>
  );
}
