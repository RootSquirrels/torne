/**
 * The shared state of the resources.
 *
 * These tests are about behaviour a reader would notice: the catalogue
 * arriving once and not four times, the value staying on screen while it is
 * refreshed, a failed refresh not taking the value away, and the work being
 * cancelled when nobody is waiting for it.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { createResourceStore } from '@/services/api/resourceStore';

/** Let the pending promises settle. */
async function settle(): Promise<void> {
  for (let turn = 0; turn < 8; turn += 1) {
    await Promise.resolve();
  }
}

afterEach(() => {
  vi.useRealTimers();
});

describe('the resource store', () => {
  it('reads a resource once for the whole application', async () => {
    const store = createResourceStore();
    const loader = vi.fn(() => Promise.resolve('the catalogue'));
    store.register('thing', loader, { freshnessMs: 60_000 });

    const first = vi.fn();
    const second = vi.fn();
    store.subscribe('thing', first);
    store.subscribe('thing', second);

    expect(loader).toHaveBeenCalledTimes(1);

    await settle();

    expect(store.get<string>('thing').data).toBe('the catalogue');
    expect(first).toHaveBeenCalled();
    expect(second).toHaveBeenCalled();
  });

  it('does not read a fresh value again', async () => {
    const store = createResourceStore();
    const loader = vi.fn(() => Promise.resolve('the catalogue'));
    store.register('thing', loader, { freshnessMs: 60_000 });

    store.subscribe('thing', () => {});
    await settle();
    expect(loader).toHaveBeenCalledTimes(1);

    // Another component mounts and asks for the same resource.
    store.subscribe('thing', () => {});
    await settle();

    expect(loader).toHaveBeenCalledTimes(1);
  });

  it('re-reads a value that has gone stale, without taking it away', async () => {
    vi.useFakeTimers();
    const store = createResourceStore();
    const loader = vi.fn(() => Promise.resolve(`read ${loader.mock.calls.length}`));
    store.register('thing', loader, { freshnessMs: 1_000 });

    store.subscribe('thing', () => {});
    await settle();
    expect(store.get<string>('thing').data).toBe('read 1');

    vi.advanceTimersByTime(2_000);
    store.subscribe('thing', () => {});

    // The re-read has started, and the value that was on screen is still there.
    expect(loader).toHaveBeenCalledTimes(2);
    expect(store.get<string>('thing').data).toBe('read 1');
    expect(store.get<string>('thing').refreshing).toBe(true);

    await settle();

    expect(store.get<string>('thing').data).toBe('read 2');
    expect(store.get<string>('thing').refreshing).toBe(false);
  });

  it('keeps the last value when a refresh fails', async () => {
    const store = createResourceStore();
    let attempt = 0;
    const loader = vi.fn(() => {
      attempt += 1;
      if (attempt === 1) {
        return Promise.resolve('the catalogue');
      }
      return Promise.reject(new Error('the catalogue did not answer'));
    });
    store.register('thing', loader, { freshnessMs: 60_000 });

    store.subscribe('thing', () => {});
    await settle();
    expect(store.get<string>('thing').data).toBe('the catalogue');

    store.invalidate('thing');
    await settle();

    // A catalogue that cannot be re-read is still a catalogue that was read.
    expect(store.get<string>('thing').data).toBe('the catalogue');
    expect(store.get<string>('thing').error).toBe('the catalogue did not answer');
    expect(store.get<string>('thing').loading).toBe(false);
  });

  it('says so when a resource was never declared', async () => {
    const store = createResourceStore();

    store.subscribe('missing', () => {});
    await settle();

    expect(store.get<string>('missing').error).toContain('is not declared');
    expect(store.get<string>('missing').data).toBeNull();
  });

  it('cancels the work when nobody is waiting for it any more', () => {
    const store = createResourceStore();
    let aborted = false;
    const loader = vi.fn((signal: AbortSignal) => {
      signal.addEventListener('abort', () => {
        aborted = true;
      });
      return new Promise<string>(() => {});
    });
    store.register('thing', loader);

    const unsubscribe = store.subscribe('thing', () => {});
    expect(loader).toHaveBeenCalledTimes(1);

    unsubscribe();

    expect(aborted).toBe(true);
  });

  it('keeps the work when another reader is still waiting', () => {
    const store = createResourceStore();
    let aborted = false;
    const loader = vi.fn((signal: AbortSignal) => {
      signal.addEventListener('abort', () => {
        aborted = true;
      });
      return new Promise<string>(() => {});
    });
    store.register('thing', loader);

    const unsubscribeFirst = store.subscribe('thing', () => {});
    const unsubscribeSecond = store.subscribe('thing', () => {});

    unsubscribeFirst();

    expect(aborted).toBe(false);

    unsubscribeSecond();

    expect(aborted).toBe(true);
  });

  it('reads a resource again when it is invalidated', async () => {
    const store = createResourceStore();
    const loader = vi.fn(() => Promise.resolve(`read ${loader.mock.calls.length}`));
    store.register('thing', loader, { freshnessMs: 60_000 });

    store.subscribe('thing', () => {});
    await settle();
    expect(loader).toHaveBeenCalledTimes(1);

    store.invalidate('thing');
    await settle();

    expect(loader).toHaveBeenCalledTimes(2);
    expect(store.get<string>('thing').data).toBe('read 2');
  });

  it('publishes a state that does not change when nothing changed', async () => {
    const store = createResourceStore();
    store.register('thing', () => Promise.resolve('the catalogue'), { freshnessMs: 60_000 });

    const before = store.get<string>('thing');
    expect(store.get<string>('thing')).toBe(before);

    store.subscribe('thing', () => {});
    await settle();

    const after = store.get<string>('thing');
    expect(after.data).toBe('the catalogue');
    expect(store.get<string>('thing')).toBe(after);
  });
});
