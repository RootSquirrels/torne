import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Select } from '@/components/ui/Select';

const OPTIONS = [
  { value: 'all', label: 'All domains' },
  { value: 'hydrology', label: 'Hydrology' },
  { value: 'atmosphere', label: 'Atmosphere', disabled: true },
];

describe('Select', () => {
  it('associates the label with the control and reports the chosen value', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <Select
        label="Domain"
        value="all"
        options={OPTIONS}
        onChange={onChange}
      />,
    );

    const select = screen.getByLabelText('Domain');
    expect(select).toHaveValue('all');

    await user.selectOptions(select, 'hydrology');
    expect(onChange).toHaveBeenCalledWith('hydrology');
  });

  it('renders every option and keeps a disabled one unselectable', () => {
    render(
      <Select label="Domain" value="all" options={OPTIONS} onChange={() => undefined} />,
    );

    const select = screen.getByLabelText('Domain');
    expect(select).toHaveDisplayValue('All domains');
    expect(screen.getByRole('option', { name: 'Atmosphere' })).toBeDisabled();
  });

  it('announces an error and marks the control invalid', () => {
    render(
      <Select
        label="Domain"
        value="all"
        options={OPTIONS}
        onChange={() => undefined}
        error="Pick a domain."
      />,
    );

    expect(screen.getByLabelText('Domain')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('Pick a domain.');
  });

  it('cannot be opened when it is disabled', () => {
    render(
      <Select
        label="Domain"
        value="all"
        options={OPTIONS}
        onChange={() => undefined}
        disabled
      />,
    );

    expect(screen.getByLabelText('Domain')).toBeDisabled();
  });
});
