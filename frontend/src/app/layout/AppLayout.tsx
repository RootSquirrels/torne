/**
 * The application layout: the bar on top, the work below.
 */
import { Outlet } from 'react-router-dom';

import { TopBar } from '@/components/layout/TopBar';
import './AppLayout.css';

export function AppLayout() {
  return (
    <div className="torne-shell">
      <TopBar />
      <main className="torne-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
