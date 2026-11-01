import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The accessibility gate.
 *
 * The explorer is careful about semantics — `aria-current` on the entity
 * that is being read, a named region for the map's list, one activation on
 * the list, a visible focus ring, a reduced-motion preference honoured. None
 * of that is a guarantee. This gate is the guarantee: it opens the pages a
 * reader actually opens, and asks axe whether the rendered page is one a
 * reader can use.
 *
 * The rules are the WCAG 2.0 and 2.1 A and AA rules. The `best-practice` tag
 * is deliberately **not** included: it reports things that are not
 * violations, and a gate that cries wolf is a gate nobody reads.
 *
 * Every violation must be accounted for. The ones that have been examined
 * and accepted are in `axe-allowlist.json`, each with a written reason. The
 * ones that are real defects are not: they fail this gate until they are
 * fixed. A gate that passes because it was weakened is worse than no gate.
 *
 * The audit runs on Chromium only. Axe judges the DOM, and the DOM is the
 * same tree in every engine — the three engines were measured and agree on
 * every finding. But the colour-contrast rule reads *resolved* colours, and
 * WebKit settles the `light-dark()` tokens of a theme change later than the
 * other two: measured, a WebKit audit can catch the application mid-change,
 * with the ink of one skin on the paper of the other. That verdict would be
 * about when the audit ran, not about the application.
 */

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] as const;

const SKINS = ['light', 'dark'] as const;
type Skin = (typeof SKINS)[number];

/**
 * The surface each skin paints, and the colour it paints it with.
 *
 * The served HTML hard-codes the light skin, and the application applies the
 * stored preference once it mounts. Waiting for the resolved surface — not
 * only for the attribute — is what makes the audit measure the skin it was
 * asked to measure.
 */
const SKIN_SURFACE: Record<Skin, string> = {
  light: 'rgb(245, 243, 239)',
  dark: 'rgb(11, 13, 17)',
};

interface PageTarget {
  /** What the page is, in the words of the reader. */
  readonly name: string;
  /** Where it lives. */
  readonly path: string;
  /** The heading that says the page has finished loading. */
  readonly heading: { readonly name: string; readonly level: number };
  /** Whether the page draws the map, which is drawn after the data arrives. */
  readonly map: boolean;
}

const PAGES: readonly PageTarget[] = [
  { name: 'the overview', path: '/', heading: { name: 'Europe', level: 2 }, map: true },
  { name: 'a country', path: '/country/FR', heading: { name: 'France', level: 2 }, map: true },
  {
    name: 'a mission',
    path: '/mission/ATMO-001',
    heading: { name: 'ATMO-001', level: 2 },
    map: true,
  },
  {
    name: 'the workbench',
    path: '/workbench',
    heading: { name: 'Component workbench', level: 1 },
    map: false,
  },
];

// --------------------------------------------------------------- the allowlist

interface AllowlistEntry {
  readonly rule: string;
  readonly pattern: string;
  readonly reason: string;
}

interface Allowlist {
  readonly entries: readonly AllowlistEntry[];
}

const here = dirname(fileURLToPath(import.meta.url));

function isAllowlistEntry(value: unknown): value is AllowlistEntry {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (['rule', 'pattern', 'reason'] as const).every(
    (field) => typeof candidate[field] === 'string' && candidate[field].trim() !== '',
  );
}

/** A type guard that keeps `any` out of the allowlist. */
function isUnknownArray(value: unknown): value is readonly unknown[] {
  return Array.isArray(value);
}

function readAllowlist(): Allowlist {
  return parseAllowlist(readFileSync(join(here, 'axe-allowlist.json'), 'utf8'));
}

/**
 * Read an allowlist from its text.
 *
 * An entry that does not carry a reason is refused outright: the allowlist
 * must not be able to silence a violation quietly.
 */
function parseAllowlist(text: string): Allowlist {
  const parsed: unknown = JSON.parse(text);
  if (typeof parsed !== 'object' || parsed === null || !('entries' in parsed)) {
    throw new Error('axe-allowlist.json must hold an "entries" array');
  }
  const raw = parsed.entries;
  if (!isUnknownArray(raw)) {
    throw new Error('axe-allowlist.json must hold an "entries" array');
  }
  const entries: AllowlistEntry[] = [];
  for (const entry of raw) {
    if (!isAllowlistEntry(entry)) {
      throw new Error(
        'every allowlist entry must carry a rule, a pattern and a reason that says why the violation is accepted',
      );
    }
    entries.push(entry);
  }
  return { entries };
}

const ALLOWLIST = readAllowlist();

/** An allowlist entry, with its pattern compiled. */
interface CompiledEntry {
  readonly rule: string;
  readonly expression: RegExp;
  readonly reason: string;
}

function compile(list: Allowlist): readonly CompiledEntry[] {
  return list.entries.map((entry) => ({
    rule: entry.rule,
    expression: new RegExp(entry.pattern),
    reason: entry.reason,
  }));
}

const COMPILED = compile(ALLOWLIST);

// ------------------------------------------------------------------ the report

interface Offence {
  readonly rule: string;
  readonly impact: string;
  readonly help: string;
  readonly target: string;
  readonly summary: string;
}

function describeTarget(target: unknown): string {
  if (!Array.isArray(target)) {
    return String(target);
  }
  return target
    .map((frame) => (Array.isArray(frame) ? frame.join(' ') : String(frame)))
    .join(' ');
}

function format(offences: readonly Offence[]): string {
  return offences
    .map(
      (offence) =>
        `[${offence.impact}] ${offence.rule} — ${offence.target}\n    ${offence.help}\n    ${offence.summary.replace(/\n/g, ' ')}`,
    )
    .join('\n');
}

/**
 * Whether a violation has been accounted for.
 *
 * Only the rule and the element matter. A rule that is not named is not
 * accepted, and an element the pattern does not match is not accepted: the
 * allowlist accepts what it says it accepts, and nothing else.
 */
function isAccepted(entries: readonly CompiledEntry[], offence: Offence): boolean {
  return entries.some(
    (entry) => entry.rule === offence.rule && entry.expression.test(offence.target),
  );
}

// --------------------------------------------------------------------- the gate

async function openInSkin(page: Page, target: PageTarget, skin: Skin) {
  await page.addInitScript((value) => {
    window.localStorage.setItem('torne.theme', value);
  }, skin);
  await page.goto(target.path);

  await expect(
    page.getByRole('heading', { name: target.heading.name, level: target.heading.level }),
  ).toBeVisible();

  // The map is drawn after the boundaries arrive; an audit that caught it
  // half-drawn would be auditing a page no reader ever sees.
  if (target.map) {
    const map = page.getByRole('application', { name: 'Where the missions reached' });
    await expect(map.locator('svg path').first()).toBeVisible();
  }

  await expect(page.locator('html')).toHaveAttribute('data-theme', skin);
  await expect
    .poll(async () => await page.evaluate(() => getComputedStyle(document.body).backgroundColor))
    .toBe(SKIN_SURFACE[skin]);
}

/**
 * The allowlist itself.
 *
 * A gate that accepts everything is not a gate, and a gate that accepts
 * nothing cannot be used. These two tests say which of the two it is: the
 * allowlist accepts exactly what it names, and it refuses an entry that does
 * not say why.
 */
test.describe('the allowlist', () => {
  test('refuses an entry that does not say why the violation is accepted', () => {
    const withoutReason = JSON.stringify({
      entries: [{ rule: 'color-contrast', pattern: '.*', reason: '   ' }],
    });
    expect(() => parseAllowlist(withoutReason)).toThrow(/reason/);

    const withoutRule = JSON.stringify({
      entries: [{ pattern: '.*', reason: 'because' }],
    });
    expect(() => parseAllowlist(withoutRule)).toThrow(/rule/);
  });

  test('accepts only the violations it names', () => {
    const list = parseAllowlist(
      JSON.stringify({
        entries: [
          {
            rule: 'color-contrast',
            pattern: '^\\.torne-topbar__subtitle$',
            reason: 'the subtitle is not information the reader must be able to read',
          },
        ],
      }),
    );
    const entries = compile(list);

    const named = {
      rule: 'color-contrast',
      impact: 'serious',
      help: '',
      target: '.torne-topbar__subtitle',
      summary: '',
    };
    expect(isAccepted(entries, named)).toBe(true);

    // Another element, the same rule: not named, not accepted.
    expect(isAccepted(entries, { ...named, target: '.torne-legend__title' })).toBe(false);

    // The same element, another rule: not named, not accepted.
    expect(isAccepted(entries, { ...named, rule: 'aria-valid-attr-value' })).toBe(false);
  });
});

for (const skin of SKINS) {
  test.describe(`in the ${skin} skin`, () => {
    for (const target of PAGES) {
      test(`${target.name} has no unaccounted accessibility violation`, async ({ page }) => {
        await openInSkin(page, target, skin);

        const results = await new AxeBuilder({ page }).withTags([...TAGS]).analyze();

        const offences: Offence[] = [];
        for (const violation of results.violations) {
          for (const node of violation.nodes) {
            const offence: Offence = {
              rule: violation.id,
              impact: violation.impact ?? 'unknown',
              help: violation.help,
              target: describeTarget(node.target),
              summary: node.failureSummary ?? '',
            };
            const accepted = isAccepted(COMPILED, offence);
            if (!accepted) {
              offences.push(offence);
            }
          }
        }

        expect(
          offences,
          [
            `${offences.length} accessibility violation(s) on ${target.path} in the ${skin} skin are not accounted for.`,
            'Each one must be fixed, or examined and accepted in tests/e2e/axe-allowlist.json with a written reason.',
            '',
            format(offences),
          ].join('\n'),
        ).toEqual([]);
      });
    }
  });
}
