/**
 * Loading the manifest.
 *
 * The manifest is the one projection the explorer reads: it carries the
 * catalogue, the coverage, the models and the results. The application calls
 * the API and nothing else — it never contacts a data provider, and it never
 * computes a scientific quantity.
 *
 * The reading itself is shared: the manifest is fetched once for the whole
 * application, however many components ask for it. This module gives that
 * shared value the shape the explorer expects.
 */
import { MANIFEST } from '@/services/api/registry';
import { useResource } from '@/services/api/useResource';
import type { ApiManifest } from '@/types/api/manifest';

export type ManifestState =
  | { readonly status: 'loading' }
  | {
      readonly status: 'ready';
      readonly manifest: ApiManifest;
      /**
       * Set when the catalogue could not be re-read but a previous reading is
       * on screen. A catalogue that cannot be refreshed is still a catalogue
       * that was read: the reader keeps the last known state and is told why
       * it is not fresher.
       */
      readonly stale: string | null;
    }
  | { readonly status: 'failed'; readonly message: string };

export function useManifest(): ManifestState {
  const { data, error } = useResource<ApiManifest>(MANIFEST);

  if (data !== null) {
    return { status: 'ready', manifest: data, stale: error };
  }
  if (error !== null) {
    return { status: 'failed', message: error };
  }
  return { status: 'loading' };
}
