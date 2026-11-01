import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Legend } from '@/components/ui/Legend';

describe('Legend', () => {
  it('lists every entry with its label', () => {
    render(
      <Legend
        title="Series"
        items={[
          { label: 'Observed', color: 'var(--series-1)' },
          { label: 'Simulated', color: 'var(--series-2)' },
        ]}
      />,
    );

    expect(screen.getByText('Series')).toBeInTheDocument();
    expect(screen.getByText('Observed')).toBeInTheDocument();
    expect(screen.getByText('Simulated')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('gives each entry the shape the chart uses', () => {
    render(
      <Legend
        items={[
          { label: 'Square', shape: 'square' },
          { label: 'Circle', shape: 'circle' },
          { label: 'Line', shape: 'line' },
          { label: 'Dash', shape: 'dash' },
        ]}
      />,
    );

    const item = screen.getByText('Line').closest('li');
    expect(item?.querySelector('.torne-legend__swatch--line')).not.toBeNull();

    const dash = screen.getByText('Dash').closest('li');
    expect(dash?.querySelector('.torne-legend__swatch--dash')).not.toBeNull();
  });

  it('paints the swatch with the colour the caller passes', () => {
    render(<Legend items={[{ label: 'Observed', color: 'var(--series-1)' }]} />);

    const item = screen.getByText('Observed').closest('li');
    expect(item?.querySelector('.torne-legend__swatch')).toHaveStyle({
      backgroundColor: 'var(--series-1)',
    });
  });

  it('renders the description of an entry when there is one', () => {
    render(<Legend items={[{ label: 'Observed', description: 'Measured by the mission.' }]} />);

    expect(screen.getByText('Measured by the mission.')).toBeInTheDocument();
  });
});
