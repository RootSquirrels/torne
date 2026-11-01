import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LoadingState } from '@/components/ui/LoadingState';

describe('LoadingState', () => {
  it('is a polite live status that says it is busy', () => {
    render(<LoadingState />);

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveAttribute('aria-busy', 'true');
  });

  it('carries a default label', () => {
    render(<LoadingState />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading…');
  });

  it('says what is loading', () => {
    render(<LoadingState label="Loading the missions…" />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading the missions…');
  });
});
