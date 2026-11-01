import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Card } from '@/components/ui/Card';

describe('Card', () => {
  it('renders a title, a subtitle, the actions and the footer', () => {
    render(
      <Card
        title="Coverage by country"
        subtitle="Produced by the mission, not derived from it."
        actions={<button type="button">Export</button>}
        footer="Updated on the last run."
        padded
      >
        <p>Body of the card.</p>
      </Card>,
    );

    expect(screen.getByRole('heading', { name: 'Coverage by country' })).toBeInTheDocument();
    expect(
      screen.getByText('Produced by the mission, not derived from it.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export' })).toBeInTheDocument();
    expect(screen.getByText('Updated on the last run.')).toBeInTheDocument();
    expect(screen.getByText('Body of the card.')).toBeInTheDocument();
  });

  it('omits the header when there is no title, subtitle or action', () => {
    render(
      <Card>
        <p>Body of the card.</p>
      </Card>,
    );

    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.getByText('Body of the card.')).toBeInTheDocument();
  });

  it('renders the children inside an article', () => {
    render(
      <Card title="Coverage">
        <p>Body of the card.</p>
      </Card>,
    );

    const article = screen.getByRole('article');
    expect(article).toHaveClass('torne-card');
    expect(article).toContainElement(screen.getByText('Body of the card.'));
  });
});
