import { expect, test } from '@playwright/test';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The bundle budget gate.
 *
 * The budget is a number in a script; what makes it a gate is that the build
 * fails when the number is broken. This spec exercises that decision through
 * the script itself — it runs the script as a process, the way the build
 * runs it, and reads its verdict — rather than importing the function, so
 * what is tested is the gate and not an implementation detail.
 *
 * The assets it measures are synthetic and are written to a temporary
 * directory: the decision must be shown to depend on the size of the entry
 * chunk and on nothing else, and the application's own build must not be
 * what the test leans on.
 *
 * The decision is not an end-to-end concern, so it is not tested in the unit
 * suite: `tests/unit/` belongs to another author. It is tested here because
 * this is where the script is run from.
 */

const here = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(here, '..', '..', 'scripts', 'bundle-report.mjs');

/**
 * Text that does not compress.
 *
 * A repeated character would gzip to almost nothing, and the budget would
 * then be measured against a fiction. This is deterministic, so the sizes
 * are the same on every run.
 */
function noise(length: number): string {
  let text = '';
  let seed = 42;
  for (let index = 0; index < length; index += 1) {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    text += String.fromCharCode(33 + (seed % 94));
  }
  return text;
}

/** A directory of built assets: one entry chunk, one other chunk. */
function builtAssets(): string {
  const directory = mkdtempSync(join(tmpdir(), 'torne-bundle-'));
  writeFileSync(join(directory, 'index-aaaaaaaaaaaa.js'), noise(60_000), 'utf8');
  writeFileSync(join(directory, 'vendor-bbbbbbbbbbbb.js'), noise(120_000), 'utf8');
  return directory;
}

interface Verdict {
  readonly status: number | null;
  readonly stdout: string;
  readonly stderr: string;
}

function measure(assets: string, budget?: string): Verdict {
  const result = spawnSync(process.execPath, [SCRIPT], {
    encoding: 'utf8',
    env: {
      ...process.env,
      TORNE_BUNDLE_ASSETS: assets,
      ...(budget === undefined ? {} : { TORNE_BUNDLE_BUDGET_KB: budget }),
    },
  });
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

test('the build fails when the entry chunk is over the budget', () => {
  const assets = builtAssets();

  const verdict = measure(assets, '1');

  expect(verdict.status, verdict.stderr).toBe(1);
  expect(verdict.stderr).toContain('the bundle budget is not met');
  expect(verdict.stderr).toContain('over the 1 kB budget');
  // The entry chunk is the one that is named: it is the chunk the gate is about.
  expect(verdict.stderr).toContain('index-aaaaaaaaaaaa.js');
});

test('the build passes when the entry chunk is within the budget', () => {
  const assets = builtAssets();

  const verdict = measure(assets, '1000');

  expect(verdict.status, verdict.stderr).toBe(0);
  expect(verdict.stdout).toContain('within the 1000 kB budget');
});

test('the other chunks are reported but not gated', () => {
  const assets = builtAssets();

  // The vendor chunk is larger than the entry chunk. The budget is the
  // entry chunk's alone: the chart library is lazy, and a reader pays for it
  // only on the page that draws a chart.
  const verdict = measure(assets, '1000');

  expect(verdict.status, verdict.stderr).toBe(0);
  expect(verdict.stdout).toContain('vendor-bbbbbbbbbbbb.js');
  expect(verdict.stdout).toContain('the other chunks are reported only');
});

test('the budget is 120 kB unless it is said otherwise', () => {
  const assets = builtAssets();

  const verdict = measure(assets);

  expect(verdict.status, verdict.stderr).toBe(0);
  expect(verdict.stdout).toContain('gated at 120 kB');
});
