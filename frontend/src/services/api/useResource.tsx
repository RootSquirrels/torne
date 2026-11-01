/**
 * Reading a resource from the shared state.
 *
 * The hook is a thin binding: the state lives in the store, and this is how
 * React learns that it changed. It uses `useSyncExternalStore`, so a
 * component that mounts while a request is already in flight is served the
 * same request rather than starting another one.
 */
import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';

import { resources as defaultResources } from '@/services/api/registry';
import type { ResourceState, ResourceStore } from '@/services/api/resourceStore';

/** What a reader gets of a resource. */
export interface Resource<T> extends ResourceState<T> {
  /** Read it again, by hand. */
  readonly refetch: () => void;
}

const ResourceStoreContext = createContext<ResourceStore>(defaultResources);

export interface ResourceStoreProviderProps {
  readonly store: ResourceStore;
  readonly children: ReactNode;
}

/**
 * Give a subtree its own store.
 *
 * The application uses the shared one; the tests use their own, so that one
 * test cannot leave a value behind for the next.
 */
export function ResourceStoreProvider({ store, children }: ResourceStoreProviderProps) {
  return <ResourceStoreContext.Provider value={store}>{children}</ResourceStoreContext.Provider>;
}

/** The store this subtree reads from. */
export function useResourceStore(): ResourceStore {
  return useContext(ResourceStoreContext);
}

/**
 * Read a resource.
 *
 * The key names a resource that was declared in the registry. The returned
 * value is stable: it changes when the resource does, and not otherwise.
 */
export function useResource<T>(key: string): Resource<T> {
  const store = useResourceStore();

  const subscribe = useCallback(
    (listener: () => void) => store.subscribe(key, listener),
    [store, key],
  );
  const getSnapshot = useCallback(() => store.get<T>(key), [store, key]);

  const state = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const refetch = useCallback(() => {
    store.invalidate(key);
  }, [store, key]);

  return useMemo(() => ({ ...state, refetch }), [state, refetch]);
}
