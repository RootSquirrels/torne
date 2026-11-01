import { expect, test } from '@playwright/test';

/**
 * The critical journeys of the explorer.
 *
 * These run against the application FastAPI actually serves — the compiled
 * frontend in the Python package — so what is tested is what ships.
 *
 * The journeys are the ones a reader takes: open the explorer, read a
 * country, read a mission, read an asset, and open the component workbench.
 */

test.beforeEach(({ page }) => {
  const failures: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') {
      failures.push(message.text());
    }
  });
  page.on('pageerror', (error) => {
    failures.push(error.message);
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      failures.push(`HTTP ${response.status()} for ${response.url()}`);
    }
  });
  (page as { __failures?: string[] }).__failures = failures;
});

test.afterEach(({ page }) => {
  const failures = (page as { __failures?: string[] }).__failures ?? [];
  expect(failures, `the console reported errors: ${failures.join(' | ')}`).toEqual([]);
});

test('the explorer opens on the overview and shows what the repository holds', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Europe', level: 2 })).toBeVisible();
  await expect(page.getByText('Countries with missions')).toBeVisible();
  await expect(page.getByText('Planned, not available')).toBeVisible();
});

test('a country shows the status its own missions earned', async ({ page }) => {
  await page.goto('/');

  // The map's entity list selects a country; the reading panel opens it.
  // The reader's journey is the one that opens the country.
  const panel = page.getByRole('complementary', { name: 'Reading panel' });
  await panel.getByRole('button', { name: 'France' }).click();

  await expect(page.getByRole('heading', { name: 'France', level: 2 })).toBeVisible();
  await expect(page.getByText('Region-wide, not national')).toBeVisible();
});

test('a mission shows what it produced and what it did not establish', async ({ page }) => {
  await page.goto('/mission/ATMO-001');

  await expect(page.getByRole('heading', { name: 'ATMO-001', level: 2 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Produced' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Not established' })).toBeVisible();
  await expect(page.getByText('Status supported by')).toBeVisible();
});

test('the map lists the entities it draws', async ({ page }) => {
  await page.goto('/');

  const entities = page.getByRole('region', { name: 'Entities' });
  await expect(entities).toBeVisible();
  await expect(entities.getByRole('button').first()).toBeVisible();
});

test('a filter narrows the map and is shareable in the URL', async ({ page }) => {
  await page.goto('/');

  await page.getByLabel('Domain').selectOption('atmosphere');

  await expect(page).toHaveURL(/domain=atmosphere/);
});

test('the workbench declares its data to be synthetic', async ({ page }) => {
  await page.goto('/workbench');

  await expect(page.getByRole('heading', { name: 'Component workbench' })).toBeVisible();
  await expect(page.getByText('Synthetic demo data.', { exact: false }).first()).toBeVisible();
});

test('the market branch stays closed', async ({ page }) => {
  await page.goto('/');

  const market = page.getByText('Market Intelligence');
  await expect(market).toBeVisible();
  await expect(market).toHaveAttribute('aria-disabled', 'true');
});
