import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MetricCard } from '@/components/data/MetricCard';
import type { ApiRef } from '@/types/api/manifest';

const SOURCE: ApiRef = {
  kind: 'document',
  target: 'docs/missions/swot.md',
  url: 'https://example.org/docs/missions/swot.md',
};

describe('MetricCard', () => {
  it('shows the value next to its unit', () => {
    render(<MetricCard label="Spatial resolution" value="1 000" unit="m" />);

    expect(screen.getByText('Spatial resolution')).toBeInTheDocument();
    expect(screen.getByText('1 000')).toBeInTheDocument();
    expect(screen.getByText('m')).toBeInTheDocument();
  });

  it('carries the direction of a delta as a word, not only as a colour', () => {
    render(
      <MetricCard
        label="Coverage"
        value="42"
        unit="countries"
        delta={{ value: '+12 %', direction: 'up', label: 'since the last run' }}
      />,
    );

    expect(screen.getByText('+12 %')).toBeInTheDocument();
    expect(screen.getByText('increase')).toBeInTheDocument();
    expect(screen.getByText('since the last run')).toBeInTheDocument();
    expect(screen.getByText('▲')).toBeInTheDocument();
  });

  it('names the direction of a decrease and of a flat delta', () => {
    const { rerender } = render(
      <MetricCard label="Coverage" value="42" delta={{ value: '-3', direction: 'down' }} />,
    );

    expect(screen.getByText('decrease')).toBeInTheDocument();
    expect(screen.getByText('▼')).toBeInTheDocument();

    rerender(<MetricCard label="Coverage" value="42" delta={{ value: '0', direction: 'flat' }} />);

    expect(screen.getByText('no change')).toBeInTheDocument();
    expect(screen.getByText('→')).toBeInTheDocument();
  });

  it('renders the provenance as links to the evidence', () => {
    render(<MetricCard label="Coverage" value="42" provenance={[SOURCE]} />);

    const link = screen.getByRole('link', { name: 'docs/missions/swot.md' });
    expect(link).toHaveAttribute('href', 'https://example.org/docs/missions/swot.md');
  });

  it('renders no provenance when there is none', () => {
    render(<MetricCard label="Coverage" value="42" />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('shows the hint that qualifies the number', () => {
    render(
      <MetricCard label="Coverage" value="42" hint="Counted over the open catalogue." />,
    );

    expect(screen.getByText('Counted over the open catalogue.')).toBeInTheDocument();
  });
});
