import { useRef } from 'react';
import type { KeyboardEvent } from 'react';

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
}

/**
 * The tab strip.
 *
 * This implements the ARIA tabs pattern: a `tablist` of `tab`s with a roving
 * `tabindex`, so the strip is a single stop in the tab order. Arrow keys move
 * between tabs, `Home` and `End` jump to the first and the last, and the
 * selection follows the focus (automatic activation).
 *
 * The tab *panels* belong to the caller: this component only renders the
 * strip. It publishes the identifiers a panel needs — the tab carries
 * `id="torne-tab-<id>"` and `aria-controls="torne-tabpanel-<id>"` — so a
 * caller renders its panel as
 * `<div role="tabpanel" id="torne-tabpanel-<id>" aria-labelledby="torne-tab-<id>">`.
 *
 * States: normal, hover, focus, selected, disabled.
 */
export function Tabs({ tabs, activeId, onChange, ariaLabel }: TabsProps) {
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
    </div>
  );
}
