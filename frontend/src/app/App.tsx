import { RouterProvider } from 'react-router-dom';

import { router } from '@/app/routes';
import { ThemeProvider } from '@/app/providers/ThemeProvider';

/**
 * The application.
 *
 * The theme provider sits above the router: a theme change must repaint the
 * charts as well as the components.
 */
export function App() {
  return (
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}
