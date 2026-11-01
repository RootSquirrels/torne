/**
 * The top bar: the brand, the spaces, and the theme.
 */
import { NavLink } from 'react-router-dom';

import { useTheme } from '@/app/providers/ThemeProvider';
import type { ThemePreference } from '@/app/providers/ThemeProvider';
import './TopBar.css';

const THEMES: ReadonlyArray<{ value: ThemePreference; label: string }> = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
];

/**
 * The mark of the Explorer: a reticle.
 *
 * It is the instrument the whole application is a reading of — a sight
 * centred on a place — and it is drawn in CSS so that it costs nothing and
 * stays sharp at any size.
 */
export function TopBar() {
  const { preference, setPreference } = useTheme();

  return (
    <header className="torne-topbar">
      <div className="torne-topbar__brand">
        <span className="torne-topbar__mark" aria-hidden="true" />
        <span className="torne-topbar__names">
          <span className="torne-topbar__name">TORNE</span>
          <span className="torne-topbar__product">Explorer</span>
        </span>
        <span className="torne-topbar__subtitle">what the system has really established</span>
      </div>

      <nav className="torne-topbar__spaces" aria-label="Spaces">
        <NavLink to="/" className="torne-topbar__space" end>
          World Intelligence
        </NavLink>
        <span
          className="torne-topbar__space torne-topbar__space--closed"
          aria-disabled="true"
          title="Deferred until the physical engine is validated (docs/ARCHITECTURE.md §5)."
        >
          Market Intelligence <span className="torne-topbar__soon">deferred</span>
        </span>
      </nav>

      <div className="torne-topbar__tools">
        <div className="torne-topbar__theme" role="group" aria-label="Theme">
          {THEMES.map((theme) => (
            <button
              key={theme.value}
              type="button"
              className="torne-topbar__theme-button"
              aria-pressed={preference === theme.value}
              onClick={() => setPreference(theme.value)}
            >
              {theme.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
