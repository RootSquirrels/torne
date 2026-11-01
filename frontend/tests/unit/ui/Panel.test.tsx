import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Panel } from '@/components/ui/Panel';

describe('Panel', () => {
  it('names the region after its heading', () => {
    render(
      <Panel title="Missions" description="Every mission of the catalogue.">
        <p>Content of the panel.</p>
      </Panel>,
    );

    const region = screen.getByRole('region', { name: 'Missions' });
    expect(region.tagName).toBe('SECTION');
    expect(region).toContainElement(screen.getByText('Content of the panel.'));
    expect(screen.getByText('Every mission of the catalogue.')).toBeInTheDocument();
  });

  it('renders a footer when one is given', () => {
    render(
      <Panel title="Missions" footer="12 missions">
        <p>Content of the panel.</p>
      </Panel>,
    );

    expect(screen.getByText('12 missions')).toBeInTheDocument();
  });

  it('does not render a footer when none is given', () => {
    render(
      <Panel title="Missions">
        <p>Content of the panel.</p>
      </Panel>,
    );

    expect(screen.getByRole('region', { name: 'Missions' }).querySelector('footer')).toBeNull();
  });

  it('makes the body scrollable on demand', () => {
    render(
      <Panel title="Missions" scrollable>
        <p>Content of the panel.</p>
      </Panel>,
    );

    expect(
      screen.getByRole('region', { name: 'Missions' }).querySelector('.torne-panel__body--scrollable'),
    ).not.toBeNull();
  });
});
