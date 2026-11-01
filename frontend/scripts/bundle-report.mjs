/**
 * Report the size of the built application.
 *
 * The mission asks for the bundle to be measured, and for the chart library
 * not to be loaded on every page. The report lists each chunk with its
 * compressed size, and fails when the entry chunk has grown past the budget.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join, resolve } from 'node:path';

const root = resolve(process.cwd(), '..', 'src', 'torne', 'explorer', 'static');
const assets = join(root, 'assets');

/** The budget for the entry chunk, compressed. */
const ENTRY_BUDGET_KB = 120;

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

let files;
try {
  files = walk(assets);
} catch {
  process.stdout.write('the application is not built yet: run `npm run build` first.\n');
  process.exit(0);
}

const rows = files
  .map((path) => {
    const content = readFileSync(path);
    return {
      name: path.slice(assets.length + 1),
      raw: content.length / 1024,
      gzip: gzipSync(content).length / 1024,
    };
  })
  .sort((left, right) => right.gzip - left.gzip);

const totalRaw = rows.reduce((sum, row) => sum + row.raw, 0);
const totalGzip = rows.reduce((sum, row) => sum + row.gzip, 0);

process.stdout.write('chunk                                   raw      gzip\n');
for (const row of rows) {
  process.stdout.write(
    `${row.name.padEnd(38)} ${row.raw.toFixed(1).padStart(6)} kB ${row.gzip.toFixed(1).padStart(7)} kB\n`,
  );
}
process.stdout.write(
  `${'TOTAL'.padEnd(38)} ${totalRaw.toFixed(1).padStart(6)} kB ${totalGzip.toFixed(1).padStart(7)} kB\n`,
);

const entry = rows.find((row) => row.name.startsWith('index-') && row.name.endsWith('.js'));
if (entry !== undefined && entry.gzip > ENTRY_BUDGET_KB) {
  process.stderr.write(
    `\nthe entry chunk is ${entry.gzip.toFixed(1)} kB compressed, over the ${ENTRY_BUDGET_KB} kB budget.\n`,
  );
  process.exit(1);
}
