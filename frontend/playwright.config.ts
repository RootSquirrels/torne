import { defineConfig, devices } from '@playwright/test';

/**
 * Browser tests run against the application FastAPI actually serves: the
 * compiled frontend in the Python package, not a Vite dev server. What is
 * tested is therefore what ships.
 */
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
      use: { ...devices['Desktop Chrome'] },
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
