import { test, expect } from '@playwright/test';

test.describe('Movie Detail Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/movie/1');
  });

  test('should render movie details', async ({ page }) => {
    const titleLocator = page.locator('h1');
    await expect(titleLocator).toBeVisible();
    await expect(titleLocator).not.toBeEmpty();
  });

  test('should render emotional arc chart section', async ({ page }) => {
    const emotionalJourneyHeader = page.locator('text=Emotional Journey');
    await expect(emotionalJourneyHeader).toBeVisible();
  });

  test('should render reviews section', async ({ page }) => {
    const reviewsHeading = page.locator('#reviews-heading');
    await expect(reviewsHeading).toBeVisible();
    await expect(reviewsHeading).toHaveText('Ratings & Reviews');
  });
});
