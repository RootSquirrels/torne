import { cloneElement, useId, useState } from 'react';
import type { FocusEvent, KeyboardEvent, MouseEvent, ReactElement, ReactNode } from 'react';

import './Tooltip.css';

export type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';

/**
 * The props a tooltip trigger must accept.
 *
 * The tooltip clones its child to attach the description and the event
 * handlers; these are the only props it adds.
 */
export interface TooltipTriggerProps {
  'aria-describedby'?: string | undefined;
  onFocus?: ((event: FocusEvent<Element>) => void) | undefined;
  onBlur?: ((event: FocusEvent<Element>) => void) | undefined;
  onMouseEnter?: ((event: MouseEvent<Element>) => void) | undefined;
  onMouseLeave?: ((event: MouseEvent<Element>) => void) | undefined;
  onKeyDown?: ((event: KeyboardEvent<Element>) => void) | undefined;
}

export interface TooltipProps {
  /** The tooltip's text. */
  content: ReactNode;
  /** The single focusable element the tooltip describes. */
  children: ReactElement<TooltipTriggerProps>;
  placement?: TooltipPlacement;
}

/**
 * A description attached to a single focusable element.
 *
 * The tooltip opens on hover *and* on focus, and closes on blur, on pointer
 * leave and on `Escape`. While it is open it is referenced by the child's
 * `aria-describedby`, so a screen reader reads it as the description of the
 * control rather than as loose text on the page.
 *
 * The bubble is positioned absolutely inside a relative wrapper, so it is
 * not taken out of the flow and it is not clipped by the wrapper itself.
 *
 * States: closed (default), open.
 */
export function Tooltip({ content, children, placement = 'top' }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const generatedId = useId();
  const tooltipId = `torne-tooltip-${generatedId}`;

  const child = cloneElement(children, {
    'aria-describedby': open ? tooltipId : undefined,
    onFocus: (event: FocusEvent<Element>) => {
      children.props.onFocus?.(event);
      setOpen(true);
    },
    onBlur: (event: FocusEvent<Element>) => {
      children.props.onBlur?.(event);
      setOpen(false);
    },
    onMouseEnter: (event: MouseEvent<Element>) => {
      children.props.onMouseEnter?.(event);
      setOpen(true);
    },
    onMouseLeave: (event: MouseEvent<Element>) => {
      children.props.onMouseLeave?.(event);
      setOpen(false);
    },
    onKeyDown: (event: KeyboardEvent<Element>) => {
      children.props.onKeyDown?.(event);
      if (event.key === 'Escape') {
        setOpen(false);
      }
    },
  });

  return (
    <span className="torne-tooltip">
      {child}
      {open && (
        <span
          className={`torne-tooltip__bubble torne-tooltip__bubble--${placement}`}
          id={tooltipId}
          role="tooltip"
        >
          {content}
        </span>
      )}
    </span>
  );
}
