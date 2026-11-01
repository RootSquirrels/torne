/**
 * Generate the frontend's types from the API's OpenAPI document.
 *
 * The document is committed at `src/types/api/openapi.json` and is written by
 * the application itself; the types are written from that document by
 * `scripts/generate_types.py`, in the repository root.
 *
 *   npm run generate:types   # write the types
 *   npm run check:types      # fail when they are out of date
 *
 * The wrapper exists only to find the interpreter: the generator itself, and
 * the gate that checks it, live with the rest of the repository's tooling, in
 * one language.
 */
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const GENERATOR = resolve(ROOT, 'scripts', 'generate_types.py');

/** The interpreters the repository's virtual environment may live in. */
const CANDIDATES = [
  resolve(ROOT, '.venv', 'Scripts', 'python.exe'),
  resolve(ROOT, '.venv', 'bin', 'python'),
];

/**
 * The interpreter.
 *
 * The repository's own environment first, because the generator must see the
 * same application the document was written from; the system interpreter is
 * the fallback, and it only needs the standard library.
 */
function interpreter() {
  for (const candidate of CANDIDATES) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return 'python';
}

function main() {
  const check = process.argv.includes('--check');
  const args = check ? ['--check'] : [];
  execFileSync(interpreter(), [GENERATOR, ...args], { cwd: ROOT, stdio: 'inherit' });
  return 0;
}

process.exit(main());
