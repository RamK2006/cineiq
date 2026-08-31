import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should render hero movie and details', async ({ page }) => {
    const heroSection = page.locator('.hero-section');
    await expect(heroSection).toBeVisible();

    const heroTitle = page.locator('.hero-title');
    await expect(heroTitle).toBeVisible();
    await expect(heroTitle).not.toBeEmpty();
  });

  test('should render trending rows', async ({ page }) => {
    const trendingSection = page.locator('.trending-section');
    await expect(trendingSection).toBeVisible();

    const movieCards = page.locator('.movie-card');
    await expect(movieCards.first()).toBeVisible();
  });

  test('should navigate to movie details page on click', async ({ page }) => {
    const firstMovieCard = page.locator('.movie-card').first();
    await expect(firstMovieCard).toBeVisible();
    await firstMovieCard.click();

    await expect(page).toHaveURL(/\/movie\/.+/);
  });
});
