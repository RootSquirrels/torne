/**
 * The shared state of the application's resources.
 *
 * The Explorer reads the catalogue from several places at once: the map, the
 * entity list, the filter bar and the reading panel all need the manifest.
 * Without a shared state, each of them fetches it, and the reader watches the
 * same catalogue arrive four times.
 *
 * This store is that shared state. For each resource it holds the last value
 * that arrived and when, the failure of the last attempt, and the request
 * that is in flight.
 *
 * Three rules, and they are the reason this is not a general-purpose cache:
 *
 * 1. **One request per resource.** Two components that ask for the same
 *    resource at the same time share one request. The second is not a slower
 *    version of the first: it *is* the first, waiting.
 * 2. **A value that is still fresh is not fetched again.** Freshness is a
 *    window, not a promise: the value is re-read when the window has passed,
 *    and the value on screen is not taken away while it is re-read.
 * 3. **A failure does not take the value away.** A catalogue that cannot be
 *    re-read is still a catalogue that was read. The reader keeps the last
 *    known state and is told that it could not be refreshed.
 *
 * The store knows nothing about React, and nothing about the API. It is a
 * small, testable thing that owns a map of resources.
 */

/** How a resource is read. The signal lets the store cancel the work. */
export type ResourceLoader<T> = (signal: AbortSignal) => Promise<T>;

/** What the reader is told about a resource. */
export interface ResourceState<T> {
  /** The value, once it has arrived. `null` until then. */
  readonly data: T | null;
  /** The failure of the last attempt, in the words the reader is given. */
  readonly error: string | null;
  /** True while the value is being fetched for the first time. */
  readonly loading: boolean;
  /** True while a value that is already on screen is being refreshed. */
  readonly refreshing: boolean;
}

/** The window during which a value is considered fresh. */
const DEFAULT_FRESHNESS_MS = 30_000;

export interface ResourceRegistration {
  /** How long the value stays fresh. */
  readonly freshnessMs?: number;
}

/**
 * What the store holds for one resource.
 *
 * The value is held as `unknown`: the store is a map of resources, and the
 * type belongs to whoever reads it.
 */
interface Entry {
  loader: ResourceLoader<unknown>;
  freshnessMs: number;
  data: unknown;
  error: string | null;
  loadedAt: number | null;
  request: Promise<void> | null;
  controller: AbortController | null;
  token: symbol | null;
  listeners: Set<() => void>;
  subscribers: number;
  state: ResourceState<unknown>;
}

export interface ResourceStore {
  /**
   * Declare a resource.
   *
   * A resource is declared once, where it is defined, and read by key
   * everywhere else. The declaration is the only place that knows how the
   * resource is fetched.
   */
  register<T>(key: string, loader: ResourceLoader<T>, options?: ResourceRegistration): void;

  /** The state of a resource. The reference is stable until it changes. */
  get<T>(key: string): ResourceState<T>;

  /** Watch a resource. Returns the function that stops watching. */
  subscribe(key: string, listener: () => void): () => void;

  /** Read a resource again, whether or not its value is fresh. */
  invalidate(key: string): void;

  /** Read every resource again. */
  invalidateAll(): void;

  /** Forget everything. For the tests. */
  reset(): void;
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'the request did not answer';
}

function createEntry(loader: ResourceLoader<unknown>, freshnessMs: number): Entry {
  return {
    loader,
    freshnessMs,
    data: null,
    error: null,
    loadedAt: null,
    request: null,
    controller: null,
    token: null,
    listeners: new Set(),
    subscribers: 0,
    state: Object.freeze({
      data: null,
      error: null,
      loading: true,
      refreshing: false,
    }),
  };
}

/**
 * The published state of a resource.
 *
 * The object is replaced — never mutated — when something changes, so that a
 * reader can compare it by identity. `loading` and `refreshing` are read from
 * the request that is in flight, which is what they mean.
 */
function publish(entry: Entry): void {
  const inFlight = entry.request !== null;
  const next: ResourceState<unknown> = Object.freeze({
    data: entry.data,
    error: entry.error,
    loading: inFlight && entry.data === null,
    refreshing: inFlight && entry.data !== null,
  });

  const current = entry.state;
  if (
    current.data === next.data &&
    current.error === next.error &&
    current.loading === next.loading &&
    current.refreshing === next.refreshing
  ) {
    return;
  }

  entry.state = next;
  for (const listener of [...entry.listeners]) {
    listener();
  }
}

/**
 * Create a store.
 *
 * A store is a module-level singleton in the application, and a fresh one in
 * each test.
 */
export function createResourceStore(): ResourceStore {
  const entries = new Map<string, Entry>();

  function entryFor(key: string): Entry {
    const existing = entries.get(key);
    if (existing !== undefined) {
      return existing;
    }
    // A resource that was never declared must say so rather than hang.
    const created = createEntry(
      () => Promise.reject(new Error(`the resource "${key}" is not declared`)),
      DEFAULT_FRESHNESS_MS,
    );
    entries.set(key, created);
    return created;
  }

  function start(entry: Entry): void {
    if (entry.request !== null) {
      return;
    }

    const controller = new AbortController();
    const token = Symbol('request');
    entry.controller = controller;
    entry.token = token;

    entry.request = (async () => {
      try {
        const data = await entry.loader(controller.signal);
        if (entry.token !== token) {
          return;
        }
        entry.data = data;
        entry.error = null;
        entry.loadedAt = Date.now();
      } catch (error) {
        if (entry.token !== token) {
          return;
        }
        // A cancelled request is not a failure: nobody is waiting for it.
        if (!controller.signal.aborted) {
          entry.error = messageOf(error);
        }
      } finally {
        if (entry.token === token) {
          entry.request = null;
          entry.controller = null;
          entry.token = null;
          publish(entry);
        }
      }
    })();

    publish(entry);
  }

  function maybeStart(entry: Entry): void {
    if (entry.request !== null) {
      return;
    }
    if (entry.data === null) {
      start(entry);
      return;
    }
    if (entry.loadedAt === null || Date.now() - entry.loadedAt >= entry.freshnessMs) {
      start(entry);
    }
  }

  return {
    register<T>(key: string, loader: ResourceLoader<T>, options?: ResourceRegistration): void {
      const freshnessMs = options?.freshnessMs ?? DEFAULT_FRESHNESS_MS;
      const existing = entries.get(key);
      if (existing === undefined) {
        entries.set(key, createEntry(loader, freshnessMs));
        return;
      }
      // A declared resource replaces the placeholder of an undeclared one,
      // but never a resource that has already produced something.
      if (existing.data === null && existing.loadedAt === null) {
        existing.loader = loader;
        existing.freshnessMs = freshnessMs;
      }
    },

    get<T>(key: string): ResourceState<T> {
      return entryFor(key).state as ResourceState<T>;
    },

    subscribe(key: string, listener: () => void): () => void {
      const entry = entryFor(key);
      entry.listeners.add(listener);
      entry.subscribers += 1;
      maybeStart(entry);

      return () => {
        entry.listeners.delete(listener);
        entry.subscribers -= 1;
        if (entry.subscribers === 0 && entry.request !== null && entry.data === null) {
          // Nobody is waiting for this any more, and it has produced nothing:
          // the work is cancelled rather than left to run for no reader.
          entry.controller?.abort();
        }
      };
    },

    invalidate(key: string): void {
      const entry = entries.get(key);
      if (entry === undefined) {
        return;
      }
      if (entry.request !== null) {
        // A request is already in flight; it will produce a fresh value.
        return;
      }
      start(entry);
    },

    invalidateAll(): void {
      for (const key of [...entries.keys()]) {
        this.invalidate(key);
      }
    },

    reset(): void {
      for (const entry of entries.values()) {
        entry.controller?.abort();
      }
      entries.clear();
    },
  };
}
