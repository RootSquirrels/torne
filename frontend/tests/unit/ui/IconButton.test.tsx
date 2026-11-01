import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { IconButton } from '@/components/ui/IconButton';

describe('IconButton', () => {
  it('names the button after its label and reacts to a click', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<IconButton icon={<span>x</span>} label="Open mission" onClick={onClick} />);

    const button = screen.getByRole('button', { name: 'Open mission' });
    expect(button).toHaveAttribute('title', 'Open mission');

    await user.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('is a square icon-only button and hides the glyph from assistive technology', () => {
    render(<IconButton icon={<span>*</span>} label="Filter" />);

    const button = screen.getByRole('button', { name: 'Filter' });
    expect(button).toHaveClass('torne-icon-button', 'torne-icon-button--secondary', 'torne-icon-button--md');
    expect(button.querySelector('[aria-hidden="true"]')).not.toBeNull();
  });

  it('blocks the click when it is disabled', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<IconButton icon={<span>x</span>} label="Delete" onClick={onClick} disabled />);

    const button = screen.getByRole('button', { name: 'Delete' });
    expect(button).toBeDisabled();

    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('exposes its pressed state as a toggle', () => {
    render(<IconButton icon={<span>x</span>} label="Pin" pressed />);

    expect(screen.getByRole('button', { name: 'Pin' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('does not claim to be a toggle when no pressed state is given', () => {
    render(<IconButton icon={<span>x</span>} label="Pin" />);

    expect(screen.getByRole('button', { name: 'Pin' })).not.toHaveAttribute('aria-pressed');
  });
});
