import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StatusIndicator } from '@/components/ui/StatusIndicator';

describe('StatusIndicator', () => {
  it('shows the status text on the swatch of the science ramp', () => {
    render(<StatusIndicator status="exploration" rank={2} />);

    const swatch = screen.getByText('exploration');
    expect(swatch).toHaveClass('torne-status-indicator__swatch');
    expect(swatch.closest('.torne-status-indicator')).toHaveClass(
      'torne-status-indicator--rank-2',
    );
  });

  it('puts rank 0 on the first step of the ramp', () => {
    render(<StatusIndicator status="not covered" rank={0} />);

    expect(screen.getByText('not covered').closest('.torne-status-indicator')).toHaveClass(
      'torne-status-indicator--rank-0',
    );
  });

  it('puts the highest rank on the last step of the ramp', () => {
    render(<StatusIndicator status="knowledge" rank={4} />);

    expect(screen.getByText('knowledge').closest('.torne-status-indicator')).toHaveClass(
      'torne-status-indicator--rank-4',
    );
  });

  it('keeps the status available to assistive technology when the label is hidden', () => {
    render(<StatusIndicator status="knowledge" rank={4} showLabel={false} />);

    const status = screen.getByText('knowledge');
    expect(status).toHaveClass('torne-visually-hidden');
    expect(status.closest('.torne-status-indicator__swatch')).not.toBeNull();
  });

  it('clamps a rank that falls outside the ramp', () => {
    render(<StatusIndicator status="knowledge" rank={9} />);

    expect(screen.getByText('knowledge').closest('.torne-status-indicator')).toHaveClass(
      'torne-status-indicator--rank-4',
    );
  });
});
