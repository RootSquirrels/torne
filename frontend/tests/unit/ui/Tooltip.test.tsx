import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { Tooltip } from '@/components/ui/Tooltip';

describe('Tooltip', () => {
  it('opens on hover and describes its trigger', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="The rank of the mission on the science ramp.">
        <button type="button">Rank</button>
      </Tooltip>,
    );

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    await user.hover(screen.getByRole('button', { name: 'Rank' }));

    const tooltip = screen.getByRole('tooltip');
    expect(tooltip).toHaveTextContent('The rank of the mission on the science ramp.');
    expect(screen.getByRole('button', { name: 'Rank' })).toHaveAttribute(
      'aria-describedby',
      tooltip.id,
    );
  });

  it('opens on focus, so a keyboard user reaches it too', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Explains the symbol.">
        <button type="button">Symbol</button>
      </Tooltip>,
    );

    await user.tab();

    expect(screen.getByRole('tooltip')).toHaveTextContent('Explains the symbol.');
    expect(screen.getByRole('button', { name: 'Symbol' })).toHaveFocus();
  });

  it('closes on blur', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Explains the symbol.">
        <button type="button">Symbol</button>
      </Tooltip>,
    );

    await user.tab();
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    await user.tab();
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Explains the symbol.">
        <button type="button">Symbol</button>
      </Tooltip>,
    );

    await user.tab();
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('keeps the handler of its trigger', async () => {
    const user = userEvent.setup();
    let clicks = 0;

    render(
      <Tooltip content="Explains the symbol.">
        <button type="button" onClick={() => { clicks += 1; }}>
          Symbol
        </button>
      </Tooltip>,
    );

    await user.click(screen.getByRole('button', { name: 'Symbol' }));
    expect(clicks).toBe(1);
  });
});
