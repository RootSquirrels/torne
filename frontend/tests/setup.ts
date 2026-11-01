import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * The test environment shims.
 *
 * jsdom implements neither `matchMedia` nor `ResizeObserver`, and the
 * components use both: the theme follows the operating system's preference,
 * and the charts and the map follow the size of their container. The shims
 * are the smallest thing that makes those code paths run.
 */
if (typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverStub implements ResizeObserver {
    observe(): void {
      // The container never changes size in a test.
    }
    unobserve(): void {
      // Nothing to stop observing.
    }
    disconnect(): void {
      // Nothing to stop observing.
    }
  }
  globalThis.ResizeObserver = ResizeObserverStub;
}

afterEach(() => {
  cleanup();
});
