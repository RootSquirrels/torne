import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EmptyState } from '@/components/ui/EmptyState';

describe('EmptyState', () => {
  it('states what is missing and offers the way out', () => {
    render(
      <EmptyState
        title="No mission covers this country"
        description="Nothing of the catalogue reaches this country yet."
        action={<button type="button">Browse the missions</button>}
      />,
    );

    expect(screen.getByText('No mission covers this country')).toBeInTheDocument();
    expect(
      screen.getByText('Nothing of the catalogue reaches this country yet.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Browse the missions' })).toBeInTheDocument();
  });

  it('renders only the title when there is nothing else', () => {
    render(<EmptyState title="Nothing to show" />);

    expect(screen.getByText('Nothing to show')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('hides the illustration from assistive technology', () => {
    render(<EmptyState title="Nothing to show" icon={<svg />} />);

    expect(screen.getByText('Nothing to show').closest('.torne-empty-state')).not.toBeNull();
    expect(
      screen.getByText('Nothing to show').closest('.torne-empty-state')?.querySelector('[aria-hidden="true"]'),
    ).not.toBeNull();
  });
});
