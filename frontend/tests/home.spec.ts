import { test, expect } from '@playwright/test';

/**
 * Home Page End-to-End Test Suite
 * Verifies critical user workflows on the landing page including:
 * - Hero movie rendering and interactions
 * - Trending rows visibility and navigation
 * - Global navigation link functionality
 * - Mobile responsive adjustments
 */
test.describe('Home Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the home page before each test
    await page.goto('/');
    // Wait for the main content to be fully loaded
    await page.waitForSelector('#main-content', { state: 'visible' });
  });

  test('should render the hero movie section correctly with all interactive elements', async ({ page }) => {
    // Verify hero section is visible and properly structured
    const heroSection = page.locator('section[data-testid="hero-movie"]');
    await expect(heroSection).toBeVisible({ timeout: 10000 });

    // Verify hero movie title is present and not empty
    const heroTitle = heroSection.locator('h1, h2');
    await expect(heroTitle).toBeVisible();
    const titleText = await heroTitle.textContent();
    expect(titleText?.trim().length).toBeGreaterThan(0);

    // Verify overview/description text exists
    const heroOverview = heroSection.locator('p');
    await expect(heroOverview.first()).toBeVisible();

    // Verify primary action buttons exist in hero section
    const playButton = heroSection.locator('button[aria-label*="Play" i], button:has-text("Play")');
    await expect(playButton).toBeVisible();

    const moreInfoButton = heroSection.locator('button[aria-label*="More Info" i], button:has-text("More Info")');
    await expect(moreInfoButton).toBeVisible();
  });

  test('should render trending movie rows and allow navigation to detail page', async ({ page }) => {
    // Verify trending section exists
    const trendingSection = page.locator('section[data-testid="trending-movies"], section:has-text("Trending")');
    await expect(trendingSection).toBeVisible({ timeout: 10000 });

    // Verify at least one movie card is rendered in trending
    const movieCards = trendingSection.locator('div[data-testid="movie-card"], a[href^="/movie/"]');
    await expect(movieCards.first()).toBeVisible({ timeout: 10000 });

    // Verify we can click on a movie card and navigate
    const firstMovieCard = movieCards.first();
    const movieHref = await firstMovieCard.getAttribute('href');

    if (movieHref) {
      await firstMovieCard.click();
      // Verify navigation to movie detail page
      await expect(page).toHaveURL(/^\/movie\//);
      await page.goBack();
      await page.waitForLoadState('networkidle');
    }
  });

  test('should navigate to search page when search link is clicked', async ({ page }) => {
    // Locate the search navigation link in the global header
    const searchLink = page.locator('a[href="/search"], nav a:has-text("Search")');
    await expect(searchLink).toBeVisible();

    // Click the search link
    await searchLink.click();

    // Verify navigation to search page
    await expect(page).toHaveURL('/search');

    // Verify search page specific elements are present
    const searchHeading = page.locator('h1:has-text("Search"), h2:has-text("Search")');
    await expect(searchHeading).toBeVisible();

    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    await expect(searchInput).toBeVisible();
  });

  test('should navigate to profile page when profile link is clicked', async ({ page }) => {
    // Locate the profile navigation link
    const profileLink = page.locator('a[href="/profile"], nav a:has-text("Profile")');

    // If profile link is present in DOM and visible, click it
    if (await profileLink.isVisible()) {
      await profileLink.click();
      // Verify navigation to profile page
      await expect(page).toHaveURL('/profile');
    }
  });

  test('should handle responsive layout correctly on mobile viewport', async ({ page }) => {
    // Simulate mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Verify hero section adapts to mobile
    const heroSection = page.locator('section[data-testid="hero-movie"]');
    await expect(heroSection).toBeVisible();

    // Verify navigation collapses or adapts (e.g., hamburger menu)
    const mobileMenuButton = page.locator('button[aria-label="Open menu"], button:has-text("Menu")');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click();
      const mobileNav = page.locator('nav[role="navigation"], div[role="dialog"]');
      await expect(mobileNav).toBeVisible();
    }
  });
});
