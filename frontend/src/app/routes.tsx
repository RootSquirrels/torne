/**
 * The route table.
 *
 * The navigation is extensible and every important state is in the URL: what
 * is being read, and which filters narrow it. A reader can therefore share a
 * link to exactly what they are looking at, and the browser's back button
 * behaves the way they expect.
 */
import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from '@/app/layout/AppLayout';
import { ErrorPage } from '@/app/pages/ErrorPage';
import { ExplorerRoute } from '@/features/explorer/ExplorerRoute';
import { WorkbenchRoute } from '@/features/workbench/WorkbenchRoute';

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
    ],
  },
]);
