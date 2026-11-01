/**
 * Reading a resource from the shared state.
 */
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { createResourceStore } from '@/services/api/resourceStore';
import { ResourceStoreProvider, useResource } from '@/services/api/useResource';

function wrapperFor(store: ReturnType<typeof createResourceStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <ResourceStoreProvider store={store}>{children}</ResourceStoreProvider>;
  };
}

describe('useResource', () => {
  it('reads a resource and gives it to the reader', async () => {
    const store = createResourceStore();
    store.register('thing', () => Promise.resolve('the catalogue'), { freshnessMs: 60_000 });

    const { result } = renderHook(() => useResource<string>('thing'), {
      wrapper: wrapperFor(store),
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => {
      expect(result.current.data).toBe('the catalogue');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('reads it again when the reader asks', async () => {
    const store = createResourceStore();
    const loader = vi.fn(() => Promise.resolve(`read ${loader.mock.calls.length}`));
    store.register('thing', loader, { freshnessMs: 60_000 });

    const { result } = renderHook(() => useResource<string>('thing'), {
      wrapper: wrapperFor(store),
    });

    await waitFor(() => {
      expect(result.current.data).toBe('read 1');
    });

    result.current.refetch();

    await waitFor(() => {
      expect(result.current.data).toBe('read 2');
    });

    expect(loader).toHaveBeenCalledTimes(2);
  });

  it('tells the reader when the resource did not answer', async () => {
    const store = createResourceStore();
    store.register('thing', () => Promise.reject(new Error('the catalogue did not answer')));

    const { result } = renderHook(() => useResource<string>('thing'), {
      wrapper: wrapperFor(store),
    });

    await waitFor(() => {
      expect(result.current.error).toBe('the catalogue did not answer');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });
});
