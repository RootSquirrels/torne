import { useId } from 'react';
import type { ChangeEvent } from 'react';

import './Input.css';

export type InputType = 'text' | 'number' | 'date' | 'search';

export interface InputProps {
  /** The visible label. It is always rendered and always associated. */
  label: string;
  /** The controlled value of the field. */
  value: string;
  /** Called with the new value on every edit. */
  onChange: (value: string) => void;
  type?: InputType;
  placeholder?: string;
  /** Supporting text, shown below the field when there is no error. */
  hint?: string;
  /** An error message. It replaces the hint and is announced to the user. */
  error?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  /** Explicit id. One is generated when it is omitted. */
  id?: string;
  autoComplete?: string;
}

/**
 * A labelled text field.
 *
 * The label is always visible and always associated with the control, so the
 * field is named for everyone. When `error` is set the field becomes invalid,
 * the message is announced through a live region, and the hint is replaced:
 * the two are never shown at once.
 *
 * States: normal, hover, focus, disabled, read-only, invalid (error).
 */
export function Input({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  hint,
  error,
  disabled = false,
  readOnly = false,
  required = false,
  id,
  autoComplete,
}: InputProps) {
  const generatedId = useId();
  const inputId = id ?? `torne-input-${generatedId}`;
  const messageId = `${inputId}-message`;

  const hasError = error !== undefined && error !== '';
  const hasHint = hint !== undefined && hint !== '';

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="torne-input" data-state={hasError ? 'error' : 'normal'}>
      <label className="torne-input__label" htmlFor={inputId}>
        {label}
        {required && (
          <span className="torne-input__required" aria-hidden="true">
            *
          </span>
        )}
      </label>
      <input
        id={inputId}
        className="torne-input__control"
        type={type}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        readOnly={readOnly}
        required={required}
        autoComplete={autoComplete}
        aria-invalid={hasError || undefined}
        aria-describedby={hasError || hasHint ? messageId : undefined}
      />
      {hasError ? (
        <p className="torne-input__error" id={messageId} role="alert">
          {error}
        </p>
      ) : hasHint ? (
        <p className="torne-input__hint" id={messageId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
