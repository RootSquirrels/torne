import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Badge } from '@/components/ui/Badge';

describe('Badge', () => {
  it('renders its content in the neutral tone by default', () => {
    render(<Badge>Open</Badge>);

    const badge = screen.getByText('Open');
    expect(badge).toHaveClass('torne-badge', 'torne-badge--neutral', 'torne-badge--md');
  });

  it('maps every tone onto a semantic variant', () => {
    render(
      <>
        <Badge tone="info">Info</Badge>
        <Badge tone="success">Success</Badge>
        <Badge tone="warning">Warning</Badge>
        <Badge tone="danger">Danger</Badge>
      </>,
    );

    expect(screen.getByText('Info')).toHaveClass('torne-badge--info');
    expect(screen.getByText('Success')).toHaveClass('torne-badge--success');
    expect(screen.getByText('Warning')).toHaveClass('torne-badge--warning');
    expect(screen.getByText('Danger')).toHaveClass('torne-badge--danger');
  });

  it('honours the small size', () => {
    render(<Badge size="sm">Open</Badge>);

    expect(screen.getByText('Open')).toHaveClass('torne-badge--sm');
  });
});
