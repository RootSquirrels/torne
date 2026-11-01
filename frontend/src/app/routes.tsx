/**
 * The route table.
 *
 * The navigation is extensible and every important state is in the URL: what
 * is being read, and which filters narrow it. A reader can therefore share a
 * link to exactly what they are looking at, and the browser's back button
 * behaves the way they expect.
 */
import { createBrowserRouter } from 'react-router-dom';
import { lazy, Suspense } from 'react';

import { AppLayout } from '@/app/layout/AppLayout';
import { ErrorPage } from '@/app/pages/ErrorPage';
import { BRANCH_ID } from '@/features/supply/branch';
import { ExplorerRoute } from '@/features/explorer/ExplorerRoute';
import { WorkbenchRoute } from '@/features/workbench/WorkbenchRoute';
import { LoadingState } from '@/components/ui/LoadingState';

/**
 * The branch routes are loaded on demand.
 *
 * A branch carries its own map and its own charts, and a reader who never
 * opens one should not download them.
 */
const LazySupplyRoute = lazy(() =>
  import('@/features/supply/SupplyRoute').then((module) => ({
    default: module.SupplyRoute,
  })),
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <ExplorerRoute /> },
      { path: 'country/:code', element: <ExplorerRoute /> },
      { path: 'country/:code/domain/:domainId', element: <ExplorerRoute /> },
      { path: 'mission/:missionId', element: <ExplorerRoute /> },
      { path: 'asset/:assetId', element: <ExplorerRoute /> },
      { path: 'source/:sourceId', element: <ExplorerRoute /> },
      { path: 'models', element: <ExplorerRoute /> },
      { path: 'models/:key', element: <ExplorerRoute /> },
      { path: 'coverage', element: <ExplorerRoute /> },
      { path: 'results', element: <ExplorerRoute /> },
      { path: 'workbench', element: <WorkbenchRoute /> },
      {
        path: BRANCH_ID,
        element: (
          <Suspense fallback={<LoadingState label="Loading the branch…" />}>
            <LazySupplyRoute />
          </Suspense>
        ),
      },
    ],
  },
]);
