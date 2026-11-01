/**
 * The top bar: the brand, the spaces, and the theme.
 *
 * The spaces are not written here: they are read from the manifest, which is
 * the catalogue's own account of the branches the platform serves. An open
 * branch is a place the reader may go; a closed one says that it is closed
 * and carries the reason the catalogue gives, in the bar itself, so that a
 * reader learns *why* without opening a developer tool.
 *
 * When the manifest cannot be read, the bar still shows the first space. A
 * catalogue that cannot be read must not take the navigation away.
 */
import { NavLink } from 'react-router-dom';

import { useTheme } from '@/app/providers/ThemeProvider';
import type { ThemePreference } from '@/app/providers/ThemeProvider';
import { MANIFEST } from '@/services/api/registry';
import { useResource } from '@/services/api/useResource';
import type { ApiManifest } from '@/types/api/manifest';
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
  const { data: manifest } = useResource<ApiManifest>(MANIFEST);
  const branches = manifest?.branches ?? [];

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
        {branches.map((branch) =>
          branch.open ? (
            <NavLink key={branch.branch_id} to={`/${branch.branch_id}`} className="torne-topbar__space">
              {branch.title}
            </NavLink>
          ) : (
            <span
              key={branch.branch_id}
              className="torne-topbar__space torne-topbar__space--closed"
              aria-disabled="true"
              title={branch.reason}
            >
              {branch.title} <span className="torne-topbar__soon">closed</span>
              <span className="torne-topbar__closed-reason">{branch.reason}</span>
            </span>
          ),
        )}
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
