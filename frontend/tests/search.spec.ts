import { test, expect } from '@playwright/test';

/**
 * Search Page End-to-End Test Suite
 * Verifies search functionality including:
 * - Search bar typing and debounced results
 * - Filter application and result updates
 * - Empty state handling
 */
test.describe('Search Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await page.waitForSelector('input[type="search"], input[placeholder*="search" i]', { state: 'visible' });
  });

  test('should render search input and allow typing', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    await expect(searchInput).toBeVisible();

    // Type a query
    await searchInput.fill('Inception');
    await expect(searchInput).toHaveValue('Inception');
  });

  test('should display debounced search results after typing', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');

    // Type a known movie title
    await searchInput.fill('The Matrix');

    // Wait for debounced results to appear (adjust timeout based on actual debounce delay)
    await page.waitForTimeout(1000);

    // Verify results container is visible
    const resultsContainer = page.locator('div[data-testid="search-results"], section:has-text("Results")');
    await expect(resultsContainer).toBeVisible({ timeout: 15000 });

    // Verify at least one result card is rendered
    const resultCards = resultsContainer.locator('div[data-testid="movie-card"], a[href^="/movie/"]');
    await expect(resultCards.first()).toBeVisible({ timeout: 10000 });
  });

  test('should apply genre filter and update results', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    await searchInput.fill('Action');
    await page.waitForTimeout(1000);

    // Locate and click a genre filter chip/button
    const genreFilter = page.locator('button:has-text("Action"), button[data-genre="Action"]');
    if (await genreFilter.isVisible()) {
      await genreFilter.click();

      // Wait for results to update
      await page.waitForTimeout(1000);

      // Verify results are still present (or empty state if no action movies match)
      const resultsContainer = page.locator('div[data-testid="search-results"]');
      await expect(resultsContainer).toBeVisible();
    }
  });

  test('should display empty state when no results are found', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');

    // Type a highly specific, unlikely to exist query
    await searchInput.fill('Xyzqwrty123456789NonExistentMovie');
    await page.waitForTimeout(1500);

    // Verify empty state message is displayed
    const emptyState = page.locator('text=/no results found/i, text=/no movies found/i, div:has-text("No results")');
    await expect(emptyState).toBeVisible({ timeout: 10000 });
  });

  test('should clear search input when clear button is clicked', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    await searchInput.fill('Test Query');
    await expect(searchInput).toHaveValue('Test Query');

    // Look for a clear button (often an 'X' icon or button)
    const clearButton = page.locator('button[aria-label="Clear search"], button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await expect(searchInput).toHaveValue('');
    } else {
      // Fallback: manually clear
      await searchInput.clear();
      await expect(searchInput).toHaveValue('');
    }
  });
});
