/**
 * Report the size of the built application, and gate the entry chunk.
 *
 * The mission asks for the bundle to be measured, and for the chart library
 * not to be loaded on every page. The report lists each chunk with its
 * compressed size, and fails when the entry chunk has grown past the budget.
 *
 * The decision itself lives in `bundle-budget.mjs`, which the build and this
 * report both read: the numbers the build fails on are the numbers printed
 * here, so the two cannot drift apart.
 */
import {
  assetsRoot,
  budgetKb,
  collectChunks,
  evaluateBudget,
  formatReport,
} from './bundle-budget.mjs';

const directory = assetsRoot();
const limit = budgetKb();

let chunks;
try {
  chunks = collectChunks(directory);
} catch {
  process.stdout.write('the application is not built yet: run `npm run build` first.\n');
  process.exit(0);
}

const decision = evaluateBudget(chunks, limit);

process.stdout.write(`${formatReport(chunks, decision)}\n`);

if (!decision.ok) {
  process.stderr.write(`\nthe bundle budget is not met: ${decision.reason}.\n`);
  process.exit(1);
}
