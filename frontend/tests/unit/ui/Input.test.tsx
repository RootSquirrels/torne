import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Input } from '@/components/ui/Input';

/** The field is controlled, so the harness has to hold the value. */
function Harness({ onChange }: { onChange: (value: string) => void }) {
  const [value, setValue] = useState('');

  return (
    <Input
      label="Mission name"
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

describe('Input', () => {
  it('associates the label with the control and reports every edit', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<Harness onChange={onChange} />);

    const input = screen.getByLabelText('Mission name');
    expect(input).toHaveValue('');

    await user.type(input, 'SWOT');
    expect(onChange).toHaveBeenLastCalledWith('SWOT');
    expect(input).toHaveValue('SWOT');
  });

  it('announces an error, marks the field invalid and replaces the hint', () => {
    render(
      <Input
        label="Mission name"
        value="SWOT"
        onChange={() => undefined}
        hint="The name as it is published."
        error="A mission with this name already exists."
      />,
    );

    const input = screen.getByLabelText('Mission name');
    expect(input).toHaveAttribute('aria-invalid', 'true');

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('A mission with this name already exists.');
    expect(screen.queryByText('The name as it is published.')).not.toBeInTheDocument();
  });

  it('describes the field with the hint when there is no error', () => {
    render(
      <Input
        label="Mission name"
        value=""
        onChange={() => undefined}
        hint="The name as it is published."
      />,
    );

    const input = screen.getByLabelText('Mission name');
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).toHaveAccessibleDescription('The name as it is published.');
  });

  it('is not editable when it is disabled or read-only', () => {
    const { rerender } = render(
      <Input label="Mission name" value="SWOT" onChange={() => undefined} disabled />,
    );

    expect(screen.getByLabelText('Mission name')).toBeDisabled();

    rerender(<Input label="Mission name" value="SWOT" onChange={() => undefined} readOnly />);

    const input = screen.getByLabelText('Mission name');
    expect(input).toHaveAttribute('readonly');
    expect(input).not.toBeDisabled();
  });
});
