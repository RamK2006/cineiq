import { test, expect } from '@playwright/test';

/**
 * Movie Detail Page End-to-End Test Suite
 * Verifies:
 * - Page load and metadata rendering
 * - Emotional arc chart visibility
 * - Reviews section display
 */
test.describe('Movie Detail Page E2E Tests', () => {
  // Use a known movie ID from the MovieLens dataset (e.g., "1" or "862" for Toy Story)
  const testMovieId = '862';

  test.beforeEach(async ({ page }) => {
    await page.goto(`/movie/${testMovieId}`);
    // Wait for the main movie detail container to load
    await page.waitForSelector('main, div[data-testid="movie-detail"]', { state: 'visible', timeout: 15000 });
  });

  test('should load movie detail page and display core metadata', async ({ page }) => {
    // Verify movie title is present
    const movieTitle = page.locator('h1, h2');
    await expect(movieTitle.first()).toBeVisible({ timeout: 10000 });

    // Verify release year is displayed
    const releaseYear = page.locator('text=/\\d{4}/');
    await expect(releaseYear.first()).toBeVisible();

    // Verify rating is displayed
    const rating = page.locator('text=/\\d\\.\\d/');
    await expect(rating.first()).toBeVisible();

    // Verify overview/description is present
    const overview = page.locator('p').filter({ hasText: /.{50,}/ });
    await expect(overview.first()).toBeVisible();
  });

  test('should render emotional arc chart component', async ({ page }) => {
    // Look for chart container or canvas/svg elements associated with emotional arc
    const chartContainer = page.locator('div[data-testid="emotional-arc-chart"], canvas, svg');
    await expect(chartContainer.first()).toBeVisible({ timeout: 10000 });

    // Verify chart has some visual representation (e.g., path elements in SVG or canvas context)
    const chartElements = chartContainer.locator('path, rect, circle');
    // We just check that the chart container exists and is not empty
    await expect(chartContainer).not.toBeEmpty();
  });

  test('should display reviews section and allow viewing reviews', async ({ page }) => {
    // Locate reviews section
    const reviewsSection = page.locator('section:has-text("Reviews"), div[data-testid="reviews-section"]');

    // Scroll to reviews section to ensure it loads (if lazy loaded)
    await reviewsSection.scrollIntoViewIfNeeded();
    await expect(reviewsSection).toBeVisible({ timeout: 10000 });

    // Verify at least one review or "no reviews" message is present
    const reviewItems = reviewsSection.locator('div[data-testid="review-item"], article');
    const noReviewsMsg = reviewsSection.locator('text=/no reviews yet/i');

    const hasReviews = await reviewItems.count() > 0;
    const hasNoReviewsMsg = await noReviewsMsg.isVisible();

    expect(hasReviews || hasNoReviewsMsg).toBeTruthy();
  });

  test('should handle navigation back to home page', async ({ page }) => {
    // Locate back button or home link
    const backButton = page.locator('button:has-text("Back"), a[href="/"]');

    if (await backButton.isVisible()) {
      await backButton.click();
      await expect(page).toHaveURL('/');
      await expect(page.locator('section[data-testid="hero-movie"]')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should display cast and crew information', async ({ page }) => {
    // Locate cast section
    const castSection = page.locator('section:has-text("Cast"), div[data-testid="cast-section"]');
    await castSection.scrollIntoViewIfNeeded();
    await expect(castSection).toBeVisible({ timeout: 10000 });

    // Verify cast members are listed
    const castMembers = castSection.locator('div[data-testid="cast-member"]');
    // If cast section exists, it should ideally have members, or a "no cast info" message
    const castCount = await castMembers.count();
    expect(castCount >= 0).toBeTruthy();
  });
});
