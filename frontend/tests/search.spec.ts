import { test, expect } from '@playwright/test';

test.describe('Search Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
  });

  test('should allow typing in search bar and rendering results', async ({ page }) => {
    const searchInput = page.locator('.search-input');
    await expect(searchInput).toBeVisible();
    
    await searchInput.fill('space');
    await page.keyboard.press('Enter');

    const resultItem = page.locator('.search-result-item');
    await expect(resultItem.first()).toBeVisible();
  });

  test('should toggle advanced filters panel', async ({ page }) => {
    const toggleButton = page.locator('button[title="Toggle Filters"]');
    await expect(toggleButton).toBeVisible();

    await expect(page.locator('text=Advanced Filters')).not.toBeVisible();

    await toggleButton.click();

    await expect(page.locator('text=Advanced Filters')).toBeVisible();
  });
});
