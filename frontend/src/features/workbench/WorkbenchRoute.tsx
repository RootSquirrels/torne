/**
 * The route to the component workbench.
 *
 * The workbench is an internal page: it shows the design system and the
 * scientific charts on synthetic data, so they can evolve independently of
 * the missions.
 */
import { ComponentWorkbench } from '@/dev/ComponentWorkbench';

export function WorkbenchRoute() {
  return <ComponentWorkbench />;
}
