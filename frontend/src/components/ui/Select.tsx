import { useId } from 'react';
import type { ChangeEvent } from 'react';

import './Select.css';

export interface SelectOption {
  /** The value submitted with the form and reported by `onChange`. */
  value: string;
  /** The text the user reads. */
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  /** The visible label. It is always rendered and always associated. */
  label: string;
  /** The selected value. */
  value: string;
  options: ReadonlyArray<SelectOption>;
  /** Called with the newly selected value. */
  onChange: (value: string) => void;
  disabled?: boolean;
  /** Explicit id. One is generated when it is omitted. */
  id?: string;
  /** Supporting text, shown below the field when there is no error. */
  hint?: string;
  /** An error message. It replaces the hint and is announced to the user. */
  error?: string;
}

/**
 * A labelled dropdown.
 *
 * A native `<select>` is used on purpose: it is keyboard operable, it works
 * with a screen reader, and it behaves the way the platform expects on touch.
 *
 * States: normal, hover, focus, disabled, invalid (error).
 */
export function Select({
  label,
  value,
  options,
  onChange,
  disabled = false,
  id,
  hint,
  error,
}: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? `torne-select-${generatedId}`;
  const messageId = `${selectId}-message`;

  const hasError = error !== undefined && error !== '';
  const hasHint = hint !== undefined && hint !== '';

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="torne-select" data-state={hasError ? 'error' : 'normal'}>
      <label className="torne-select__label" htmlFor={selectId}>
        {label}
      </label>
      <select
        id={selectId}
        className="torne-select__control"
        value={value}
        onChange={handleChange}
        disabled={disabled}
        aria-invalid={hasError || undefined}
        aria-describedby={hasError || hasHint ? messageId : undefined}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
      {hasError ? (
        <p className="torne-select__error" id={messageId} role="alert">
          {error}
        </p>
      ) : hasHint ? (
        <p className="torne-select__hint" id={messageId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
