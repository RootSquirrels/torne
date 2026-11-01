import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { FilterBar } from '@/components/ui/FilterBar';

describe('FilterBar', () => {
  it('is a named search landmark that groups the filters', () => {
    render(
      <FilterBar>
        <label htmlFor="domain">Domain</label>
        <input id="domain" type="search" />
      </FilterBar>,
    );

    expect(screen.getByRole('search', { name: 'Filters' })).toBeInTheDocument();
    expect(screen.getByLabelText('Domain')).toBeInTheDocument();
  });

  it('offers a reset button when a handler is given', async () => {
    const user = userEvent.setup();
    const onReset = vi.fn();

    render(
      <FilterBar onReset={onReset}>
        <input aria-label="Domain" type="search" />
      </FilterBar>,
    );

    await user.click(screen.getByRole('button', { name: 'Reset filters' }));
    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it('labels the reset button as the caller wants it', () => {
    render(
      <FilterBar onReset={() => undefined} resetLabel="Clear all">
        <input aria-label="Domain" type="search" />
      </FilterBar>,
    );

    expect(screen.getByRole('button', { name: 'Clear all' })).toBeInTheDocument();
  });

  it('hides the reset button when there is nothing to reset', () => {
    render(
      <FilterBar>
        <input aria-label="Domain" type="search" />
      </FilterBar>,
    );

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
