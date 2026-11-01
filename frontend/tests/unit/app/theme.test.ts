import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * The skin is decided twice: once by the browser, before anything is drawn,
 * and once by the application, when it mounts.
 *
 * The first decides prevents a flash — the wrong skin on the way in. The
 * second decides what the reader chose. They have to agree, and they agree
 * only if they use the same key. This test holds them together, because a
 * key that drifts apart is a flash that nobody notices until it happens.
 */
const ROOT = resolve(process.cwd());

const indexHtml = readFileSync(`${ROOT}/index.html`, 'utf8');
const provider = readFileSync(`${ROOT}/src/app/providers/ThemeProvider.tsx`, 'utf8');

describe('the skin', () => {
  it('is not forced in the markup', () => {
    expect(indexHtml).not.toMatch(/<html[^>]*data-theme/);
  });

  it('is decided before the application is loaded', () => {
    const head = indexHtml.indexOf('<head>');
    const inline = indexHtml.indexOf('localStorage.getItem');
    const module = indexHtml.indexOf('src="/src/main.tsx"');

    expect(head).toBeGreaterThan(-1);
    expect(inline).toBeGreaterThan(head);
    expect(module).toBeGreaterThan(inline);
  });

  it('is read from the key the provider writes', () => {
    const key = provider.match(/STORAGE_KEY\s*=\s*'([^']+)'/);
    expect(key).not.toBeNull();

    expect(indexHtml).toContain(`localStorage.getItem('${key![1]}')`);
  });

  it('is only forced when the reader chose a skin', () => {
    expect(indexHtml).toContain("stored === 'light' || stored === 'dark'");
  });
});
