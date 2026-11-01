import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ProvenanceLink } from '@/components/ui/ProvenanceLink';
import type { ApiRef } from '@/types/api/manifest';

const DOCUMENT: ApiRef = {
  kind: 'document',
  target: 'docs/missions/swot.md',
  url: 'https://example.org/docs/missions/swot.md',
};

describe('ProvenanceLink', () => {
  it('renders a document as a link that opens in a new tab', () => {
    render(<ProvenanceLink reference={DOCUMENT} />);

    const link = screen.getByRole('link', { name: 'docs/missions/swot.md' });
    expect(link).toHaveAttribute('href', 'https://example.org/docs/missions/swot.md');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(link.getAttribute('title')).toContain('Document');
  });

  it('renders a document without a URL as plain text, not as a broken link', () => {
    render(<ProvenanceLink reference={{ kind: 'document', target: 'docs/unknown.md', url: null }} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('docs/unknown.md')).toBeInTheDocument();
  });

  it('navigates to a mission when it is activated', async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    render(<ProvenanceLink reference={{ kind: 'mission', target: 'swot', url: null }} onNavigate={onNavigate} />);

    await user.click(screen.getByRole('button', { name: 'swot' }));
    expect(onNavigate).toHaveBeenCalledWith('swot');
  });

  it('renders a mission without a handler as plain text', () => {
    render(<ProvenanceLink reference={{ kind: 'mission', target: 'swot', url: null }} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByText('swot')).toBeInTheDocument();
  });

  it('renders an implementation as code', () => {
    render(
      <ProvenanceLink reference={{ kind: 'implementation', target: 'build_manifest', url: null }} />,
    );

    const code = screen.getByText('build_manifest');
    expect(code.tagName).toBe('CODE');
    expect(code.getAttribute('title')).toContain('Implementation');
  });

  it('renders a record as plain text', () => {
    render(<ProvenanceLink reference={{ kind: 'record', target: 'record-42', url: null }} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('record-42')).toBeInTheDocument();
  });
});
