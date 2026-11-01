/**
 * The bundle budget.
 *
 * The bundle report prints the size of every chunk; this module holds the
 * *decision* behind it: which chunk is the entry, what it weighs compressed,
 * and whether that weight is within the budget.
 *
 * The two live in separate files so the decision can be exercised without the
 * report's presentation, and so the report and the build gate cannot drift
 * apart: the build gate reads the same numbers the report prints.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The budget for the entry chunk, compressed.
 *
 * The entry chunk is what every reader pays for, on every page, before any
 * lazy chunk is fetched: the shell, the router, the design system and the
 * explorer's own code. It is currently around 19 kB, so this budget is wide.
 * The point of the number is not to be tight — it is that a regression has
 * somewhere to land.
 */
export const ENTRY_BUDGET_KB = 120;

/**
 * Where the built application lands.
 *
 * The path is resolved from this file rather than from the working directory,
 * so the budget is the same whether the script is run by npm, by the build, or
 * by a test from another directory.
 */
export const STATIC_ROOT = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'src',
  'torne',
  'explorer',
  'static',
);

/**
 * The directory the built assets live in.
 *
 * `TORNE_BUNDLE_ASSETS` points the measurement somewhere else. The build gate
 * never sets it; it exists so the decision can be exercised against a known
 * set of assets rather than against whatever happens to be on disk.
 */
export function assetsRoot(env = process.env) {
  const override = env['TORNE_BUNDLE_ASSETS'];
  return override !== undefined && override !== '' ? resolve(override) : join(STATIC_ROOT, 'assets');
}

/**
 * The budget in kilobytes.
 *
 * `TORNE_BUNDLE_BUDGET_KB` lowers or raises it. It is how the gate is
 * demonstrated — a budget of one kilobyte fails on the real build — without
 * editing the budget itself, which would make the demonstration a lie.
 */
export function budgetKb(env = process.env) {
  const override = Number(env['TORNE_BUNDLE_BUDGET_KB']);
  return Number.isFinite(override) && override > 0 ? override : ENTRY_BUDGET_KB;
}

/** Every file below a directory. */
function walk(directory) {
  const entries = [];
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) {
      entries.push(...walk(path));
    } else {
      entries.push(path);
    }
  }
  return entries;
}

/**
 * The chunks of a built application, with their raw and compressed weight.
 *
 * Sorted by compressed weight, heaviest first: the chunk that would break the
 * budget is the one worth seeing.
 */
export function collectChunks(directory) {
  const files = walk(directory);
  return files
    .map((path) => {
      const content = readFileSync(path);
      return {
        name: path.slice(directory.length + 1).split('\\').join('/'),
        raw: content.length / 1024,
        gzip: gzipSync(content).length / 1024,
      };
    })
    .sort((left, right) => right.gzip - left.gzip);
}

/**
 * The entry chunk: the one the browser downloads first, on every page.
 */
export function entryChunk(chunks) {
  return chunks.find((chunk) => chunk.name.startsWith('index-') && chunk.name.endsWith('.js'));
}

/**
 * The decision.
 *
 * Only the entry chunk is gated. The other chunks — the chart library above
 * all — are reported, because a change that moves code out of the entry and
 * into a lazy chunk is a change worth seeing, but a lazy chunk is paid for by
 * the reader who opens the one page that needs it, and that is the chart
 * library's own bargain.
 */
export function evaluateBudget(chunks, limit) {
  const entry = entryChunk(chunks);
  if (entry === undefined) {
    return { ok: false, entry: null, limit, reason: 'no entry chunk was found' };
  }
  const ok = entry.gzip <= limit;
  return {
    ok,
    entry,
    limit,
    reason: ok
      ? `the entry chunk ${entry.name} is ${entry.gzip.toFixed(1)} kB compressed, within the ${limit} kB budget`
      : `the entry chunk ${entry.name} is ${entry.gzip.toFixed(1)} kB compressed, over the ${limit} kB budget`,
  };
}

/** The report the reader sees: every chunk, and what the gate decided. */
export function formatReport(chunks, decision) {
  const totalRaw = chunks.reduce((sum, chunk) => sum + chunk.raw, 0);
  const totalGzip = chunks.reduce((sum, chunk) => sum + chunk.gzip, 0);

  const lines = [];
  lines.push('chunk                                   raw      gzip');
  for (const chunk of chunks) {
    const entry = decision.entry !== null && decision.entry.name === chunk.name ? '  <- entry' : '';
    lines.push(
      `${chunk.name.padEnd(38)} ${chunk.raw.toFixed(1).padStart(6)} kB ${chunk.gzip
        .toFixed(1)
        .padStart(7)} kB${entry}`,
    );
  }
  lines.push(
    `${'TOTAL'.padEnd(38)} ${totalRaw.toFixed(1).padStart(6)} kB ${totalGzip
      .toFixed(1)
      .padStart(7)} kB`,
  );
  lines.push('');
  lines.push(`the entry chunk is gated at ${decision.limit} kB compressed; the other chunks are reported only.`);
  lines.push(decision.reason);
  return lines.join('\n');
}
