import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Breadcrumbs } from '@/components/ui/Breadcrumbs';

describe('Breadcrumbs', () => {
  it('renders a breadcrumb landmark with an ordered list', () => {
    render(
      <Breadcrumbs
        items={[{ label: 'Explorer' }, { label: 'Missions' }, { label: 'SWOT' }]}
      />,
    );

    const nav = screen.getByRole('navigation', { name: 'Breadcrumb' });
    expect(nav).toBeInTheDocument();
    expect(nav.querySelector('ol')).not.toBeNull();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });

  it('marks the last item as the current page and does not link it', () => {
    render(
      <Breadcrumbs
        items={[{ label: 'Explorer', href: '/explorer' }, { label: 'SWOT', href: '/swot' }]}
      />,
    );

    const current = screen.getByText('SWOT');
    expect(current).toHaveAttribute('aria-current', 'page');
    expect(current.tagName).not.toBe('A');
  });

  it('renders an item with an href as a link', () => {
    render(
      <Breadcrumbs items={[{ label: 'Explorer', href: '/explorer' }, { label: 'Missions' }]} />,
    );

    expect(screen.getByRole('link', { name: 'Explorer' })).toHaveAttribute('href', '/explorer');
  });

  it('renders an item with only a handler as a button', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <Breadcrumbs items={[{ label: 'Back', onClick }, { label: 'SWOT' }]} />,
    );

    const button = screen.getByRole('button', { name: 'Back' });
    await user.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders an item with neither a link nor a handler as plain text', () => {
    render(<Breadcrumbs items={[{ label: 'Explorer' }]} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByText('Explorer')).toBeInTheDocument();
  });
});
