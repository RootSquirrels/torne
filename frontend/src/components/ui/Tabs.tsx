import { useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import './Tabs.css';

export interface TabItem {
  /** The identity of the tab. It is what `onChange` reports. */
  id: string;
  /** The visible text. */
  label: string;
  disabled?: boolean;
  /** A short trailing note, typically a count. */
  badge?: string;
}

export interface TabsProps {
  tabs: ReadonlyArray<TabItem>;
  /** The id of the selected tab. */
  activeId: string;
  /** Called with the id of the newly selected tab. */
  onChange: (id: string) => void;
  /** The accessible name of the tab list. */
  ariaLabel: string;
  /** The content of the active tab. */
  children?: ReactNode;
}

/**
 * The tab strip, and the panel it opens.
 *
 * This implements the ARIA tabs pattern: a `tablist` of `tab`s with a roving
 * `tabindex`, so the strip is a single stop in the tab order. Arrow keys move
 * between tabs, `Home` and `End` jump to the first and the last, and the
 * selection follows the focus (automatic activation).
 *
 * The strip owns the panel as well. A tab publishes `aria-controls`, and a
 * reference to a panel that does not exist is a broken promise — so the
 * component that makes the promise is the one that keeps it: the panel is
 * rendered here, with the id the tab points at, and with the tab as its
 * label. A caller cannot forget it, because there is nothing to forget.
 */
export function Tabs({ tabs, activeId, onChange, ariaLabel, children }: TabsProps) {
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const focusTab = (id: string) => {
    tabRefs.current.get(id)?.focus();
  };

  const findEnabled = (start: number, step: 1 | -1): TabItem | undefined => {
    const count = tabs.length;
    for (let offset = 0; offset < count; offset += 1) {
      const index = (((start + step * offset) % count) + count) % count;
      const candidate = tabs[index];
      if (candidate !== undefined && candidate.disabled !== true) {
        return candidate;
      }
    }
    return undefined;
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, id: string) => {
    const index = tabs.findIndex((tab) => tab.id === id);
    if (index < 0) {
      return;
    }

    let target: TabItem | undefined;
    switch (event.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        target = findEnabled(index + 1, 1);
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        target = findEnabled(index - 1, -1);
        break;
      case 'Home':
        target = findEnabled(0, 1);
        break;
      case 'End':
        target = findEnabled(tabs.length - 1, -1);
        break;
      default:
        return;
    }

    if (target === undefined) {
      return;
    }
    event.preventDefault();
    onChange(target.id);
    focusTab(target.id);
  };

  return (
    <div className="torne-tabs">
      <div className="torne-tabs__list" role="tablist" aria-label={ariaLabel}>
        {tabs.map((tab) => {
          const selected = tab.id === activeId;
          const classes = [
            'torne-tabs__tab',
            selected ? 'torne-tabs__tab--selected' : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <button
              key={tab.id}
              ref={(node) => {
                if (node === null) {
                  tabRefs.current.delete(tab.id);
                } else {
                  tabRefs.current.set(tab.id, node);
                }
              }}
              type="button"
              role="tab"
              id={`torne-tab-${tab.id}`}
              className={classes}
              aria-selected={selected}
              aria-controls={`torne-tabpanel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              disabled={tab.disabled}
              onClick={() => {
                onChange(tab.id);
              }}
              onKeyDown={(event) => {
                handleKeyDown(event, tab.id);
              }}
            >
              <span className="torne-tabs__label">{tab.label}</span>
              {tab.badge !== undefined && (
                <span className="torne-tabs__badge">{tab.badge}</span>
              )}
            </button>
          );
        })}
      </div>

      {/*
       * The panel the active tab points at. It is focusable, so the keyboard
       * reaches the content without going through the strip a second time.
       */}
      <div
        className="torne-tabs__panel"
        role="tabpanel"
        id={`torne-tabpanel-${activeId}`}
        aria-labelledby={`torne-tab-${activeId}`}
        tabIndex={0}
      >
        {children}
      </div>
    </div>
  );
}
