import { defineConfig, devices } from '@playwright/test';

/**
 * Browser tests run against the application FastAPI actually serves: the
 * compiled frontend in the Python package, not a Vite dev server. What is
 * tested is therefore what ships.
 */

/**
 * The gates that are not journeys.
 *
 * The three functional projects keep running the functional suite, unchanged.
 * The gates live in their own projects, because each one answers to a
 * different engine and a different rule:
 *
 * - `audit` runs the accessibility audit. Axe judges the DOM and the resolved
 *   colours. The DOM is the same tree in every engine, and the three engines
 *   were measured to agree on every finding; but the colour-contrast rule
 *   reads *resolved* colours, and WebKit settles the `light-dark()` tokens of
 *   a theme change later than the other two, so its contrast verdict depends
 *   on when the audit runs rather than on the application. One engine, then:
 *   the finding that matters, measured the same way every time.
 * - `identity` runs the visual regression gate. Pixel output is
 *   engine-specific, so a Chromium baseline compared against Firefox pixels
 *   would mean nothing.
 * - `budget` runs the bundle budget gate. The budget is a property of the
 *   build, not of a browser, so it runs once and needs no browser at all.
 */
const GATE_SPECS = /accessibility\.spec\.ts|identity-visual\.spec\.ts|bundle-budget\.spec\.ts/;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env['CI']),
  retries: process.env['CI'] ? 2 : 0,
  reporter: [['list']],
  timeout: 30_000,
  expect: { timeout: 7_000 },
  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      testIgnore: GATE_SPECS,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      testIgnore: GATE_SPECS,
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      testIgnore: GATE_SPECS,
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'audit',
      testMatch: /accessibility\.spec\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'identity',
      testMatch: /identity-visual\.spec\.ts$/,
      use: {
        ...devices['Desktop Chrome'],
        /*
         * A screenshot is only comparable with another screenshot when the
         * viewport and the pixel density are the same. They are pinned here
         * rather than left to the device, so a baseline stays valid.
         */
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 1,
      },
    },
    {
      name: 'budget',
      testMatch: /bundle-budget\.spec\.ts$/,
    },
  ],
  webServer: {
    command:
      'npm --prefix frontend run build && .venv\\Scripts\\python.exe -m uvicorn torne.explorer.api:app --host 127.0.0.1 --port 8765',
    cwd: '..',
    url: 'http://127.0.0.1:8765/api/v1/health',
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
  },
});
