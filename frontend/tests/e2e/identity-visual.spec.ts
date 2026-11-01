import { expect, test } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

/**
 * The visual regression gate.
 *
 * The identity is one design system over two skins: a dark *cockpit* and a
 * light *journal*. It was judged by eye, which means a colour or a spacing
 * drift passed every existing test. This gate is the judgement, made
 * repeatable.
 *
 * It runs on Chromium only, in its own project. Pixel output is
 * engine-specific: a Chromium baseline compared against Firefox pixels would
 * mean nothing, and a baseline that only holds on one engine is not a gate
 * but a rumour.
 *
 * Stability is the hard part, and it is the whole of the work:
 *
 * - the viewport and the device scale factor are pinned in the project, so a
 *   baseline is measured in fixed pixels;
 * - the skin is set on the root element directly, so the shot never depends
 *   on a click landing;
 * - the map is waited for, and then waited for again until it stops moving:
 *   Leaflet re-fits its extent when its container is measured, and a shot
 *   between the first fit and the second would show the wrong zoom;
 * - the charts are waited for by their pixels. A canvas is not in the DOM in
 *   a way a screenshot waits for, so the signal is that the canvas holds at
 *   least one opaque pixel — that is, that the chart has actually been
 *   drawn;
 * - animations are disabled, both by the screenshot and by the application's
 *   own charts, which already render with `animation: false`.
 */

/**
 * How every shot is taken.
 *
 * `animations: 'disabled'` finishes the transitions that are running and
 * waits for them. `caret: 'hide'` keeps a blinking text cursor out of the
 * picture. `scale: 'css'` measures in CSS pixels, so the picture does not
 * depend on the pixel density of the machine that took it. No tolerance at
 * all: a drift is a drift.
 */
const SHOT = {
  animations: 'disabled',
  caret: 'hide',
  scale: 'css',
  maxDiffPixelRatio: 0,
} as const;

const SKINS = {
  light: 'rgb(245, 243, 239)',
  dark: 'rgb(11, 13, 17)',
} as const;

type Skin = keyof typeof SKINS;

/**
 * Open a page in a skin.
 *
 * The theme is applied on the root element directly — `data-theme` is how
 * the application expresses it — and the stored preference is seeded to the
 * same value, so the application agrees with the shot and cannot flip the
 * skin underneath it.
 */
async function openInSkin(page: Page, path: string, skin: Skin): Promise<void> {
  await page.addInitScript((value) => {
    window.localStorage.setItem('torne.theme', value);
  }, skin);

  await page.goto(path);

  await page.evaluate((value) => {
    document.documentElement.setAttribute('data-theme', value);
  }, skin);

  await expect(page.locator('html')).toHaveAttribute('data-theme', skin);

  // The attribute is not enough: the tokens are resolved from it. The
  // resolved surface is what the reader sees, and it is what is shot.
  await expect
    .poll(async () => await page.evaluate(() => getComputedStyle(document.body).backgroundColor))
    .toBe(SKINS[skin]);

  // Fonts change the pixels. They must be loaded before the picture is taken.
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
}

/**
 * Wait until the map has stopped moving.
 *
 * Leaflet draws its extent once the container has been measured, and again if
 * the container is measured again. The wait is for stability, not for a
 * duration: two consecutive readings of the same extent mean the map has
 * settled.
 */
async function mapSettled(page: Page): Promise<void> {
  const map = page.getByRole('application', { name: 'Where the missions reached' });
  await expect(map.locator('svg path').first()).toBeVisible();

  const extent = async () =>
    await map.locator('svg').first().evaluate((svg) => svg.getAttribute('viewBox') ?? '');

  await expect
    .poll(
      async () => {
        const first = await extent();
        await page.waitForTimeout(120);
        const second = await extent();
        return first === second;
      },
      { timeout: 15_000, intervals: [200, 200, 300, 500, 500, 500] },
    )
    .toBe(true);
}

/**
 * Wait until a chart has been painted.
 *
 * The chart is a canvas, and the canvas is not in the DOM in a way a
 * screenshot waits for. The reliable signal is the pixels themselves: the
 * chart has been drawn when the canvas holds at least one opaque pixel.
 */
async function chartPainted(figure: Locator): Promise<void> {
  await expect
    .poll(
      async () =>
        await figure.locator('canvas').evaluateAll((canvases) =>
          canvases.filter((canvas) => {
            const element = canvas as HTMLCanvasElement;
            if (element.width === 0 || element.height === 0) {
              return false;
            }
            const context = element.getContext('2d');
            if (context === null) {
              return false;
            }
            const pixels = context.getImageData(0, 0, element.width, element.height).data;
            for (let index = 3; index < pixels.length; index += 4) {
              if (pixels[index] !== 0) {
                return true;
              }
            }
            return false;
          }).length,
        ),
      { timeout: 15_000 },
    )
    .toBeGreaterThan(0);
}

test.describe('the identity', () => {
  /**
   * The shots are serial. Two pictures taken at the same time compete for the
   * machine, and a machine that is busy paints later — which is exactly the
   * kind of difference a pixel gate must not report.
   */
  test.describe.configure({ mode: 'serial' });

  test('the overview in the cockpit skin', async ({ page }) => {
    await openInSkin(page, '/', 'dark');
    await expect(page.getByRole('heading', { name: 'Europe', level: 2 })).toBeVisible();
    await mapSettled(page);

    await expect(page).toHaveScreenshot('overview-dark.png', SHOT);
  });

  test('the overview in the journal skin', async ({ page }) => {
    await openInSkin(page, '/', 'light');
    await expect(page.getByRole('heading', { name: 'Europe', level: 2 })).toBeVisible();
    await mapSettled(page);

    await expect(page).toHaveScreenshot('overview-light.png', SHOT);
  });

  test('a country in the cockpit skin', async ({ page }) => {
    await openInSkin(page, '/country/FR', 'dark');
    await expect(page.getByRole('heading', { name: 'France', level: 2 })).toBeVisible();
    await mapSettled(page);

    await expect(page).toHaveScreenshot('country-dark.png', SHOT);
  });

  test('the workbench scientific charts in the cockpit skin', async ({ page }) => {
    await openInSkin(page, '/workbench', 'dark');
    await expect(page.getByRole('heading', { name: 'Component workbench' })).toBeVisible();

    await page.getByRole('tab', { name: 'Scientific charts' }).click();

    // The time series: two series of different frequencies, with gaps, an
    // interval, and a forecast that starts mid-way.
    const series = page.getByRole('figure').filter({ hasText: 'Discharge and water level' });
    await expect(series).toBeVisible();
    await chartPainted(series);
    await expect(series).toHaveScreenshot('workbench-time-series-dark.png', SHOT);

    // The coverage: observed, published and revised periods, and the gaps
    // between them. The chart whose colours carry the status ramp.
    const coverage = page.getByRole('figure').filter({ hasText: 'Synthetic coverage' });
    await expect(coverage).toBeVisible();
    await chartPainted(coverage);
    await expect(coverage).toHaveScreenshot('workbench-coverage-dark.png', SHOT);
  });
});
