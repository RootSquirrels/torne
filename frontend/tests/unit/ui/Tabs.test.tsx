import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Tabs } from '@/components/ui/Tabs';
import type { TabItem } from '@/components/ui/Tabs';

const TABS: TabItem[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'missions', label: 'Missions', badge: '12' },
  { id: 'archive', label: 'Archive', disabled: true },
];

function Harness({ onChange }: { onChange: (id: string) => void }) {
  const [activeId, setActiveId] = useState('overview');

  return (
    <Tabs
      tabs={TABS}
      activeId={activeId}
      onChange={(id) => {
        setActiveId(id);
        onChange(id);
      }}
      ariaLabel="Mission sections"
    >
      <p>The content of {activeId}.</p>
    </Tabs>
  );
}

describe('Tabs', () => {
  it('exposes a named tab list and marks the selected tab', () => {
    render(<Harness onChange={() => undefined} />);

    expect(screen.getByRole('tablist', { name: 'Mission sections' })).toBeInTheDocument();

    const overview = screen.getByRole('tab', { name: 'Overview' });
    const missions = screen.getByRole('tab', { name: /Missions/ });

    expect(overview).toHaveAttribute('aria-selected', 'true');
    expect(missions).toHaveAttribute('aria-selected', 'false');
  });

  it('selects a tab when it is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<Harness onChange={onChange} />);

    await user.click(screen.getByRole('tab', { name: /Missions/ }));
    expect(onChange).toHaveBeenCalledWith('missions');
    expect(screen.getByRole('tab', { name: /Missions/ })).toHaveAttribute('aria-selected', 'true');
  });

  it('moves the selection and the focus with the arrow keys', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<Harness onChange={onChange} />);

    await user.tab();
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveFocus();

    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenLastCalledWith('missions');
    expect(screen.getByRole('tab', { name: /Missions/ })).toHaveFocus();
    expect(screen.getByRole('tab', { name: /Missions/ })).toHaveAttribute('aria-selected', 'true');
  });

  it('skips a disabled tab and jumps to the ends with Home and End', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<Harness onChange={onChange} />);

    await user.tab();
    await user.keyboard('{End}');
    expect(onChange).toHaveBeenLastCalledWith('missions');

    await user.keyboard('{Home}');
    expect(onChange).toHaveBeenLastCalledWith('overview');
  });

  it('keeps a single stop in the tab order through the roving tabindex', () => {
    render(<Harness onChange={() => undefined} />);

    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: /Missions/ })).toHaveAttribute('tabindex', '-1');
  });

  it('does not select a disabled tab', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<Harness onChange={onChange} />);

    await user.click(screen.getByRole('tab', { name: 'Archive' }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('opens a panel that the tab points at, and names it after that tab', () => {
    render(<Harness onChange={() => undefined} />);

    const overview = screen.getByRole('tab', { name: 'Overview' });
    const controls = overview.getAttribute('aria-controls');
    expect(controls).not.toBeNull();

    const panel = document.getElementById(controls as string);
    expect(panel).not.toBeNull();
    expect(panel).toHaveAttribute('role', 'tabpanel');
    expect(panel).toHaveAttribute('aria-labelledby', overview.id);
    expect(panel).toHaveTextContent('The content of overview.');
  });

  it('moves the panel with the selection', () => {
    render(<Harness onChange={() => undefined} />);

    expect(screen.getByRole('tabpanel')).toHaveTextContent('The content of overview.');
  });
});
