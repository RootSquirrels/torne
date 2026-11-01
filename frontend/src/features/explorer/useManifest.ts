/**
 * Loading the manifest.
 *
 * The manifest is the one projection the explorer reads: it carries the
 * catalogue, the coverage, the models and the results. The application calls
 * the API and nothing else — it never contacts a data provider, and it never
 * computes a scientific quantity.
 */
import { useEffect, useState } from 'react';

import { api } from '@/services/api/client';
import type { ApiManifest } from '@/types/api/manifest';

export type ManifestState =
  | { readonly status: 'loading' }
  | { readonly status: 'ready'; readonly manifest: ApiManifest }
  | { readonly status: 'failed'; readonly message: string };

export function useManifest(): ManifestState {
  const [state, setState] = useState<ManifestState>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    api
      .manifest(controller.signal)
      .then((manifest) => {
        if (active) {
          setState({ status: 'ready', manifest });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error ? error.message : 'the explorer API did not answer';
        setState({ status: 'failed', message });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  return state;
}
