import { test, expect } from '@playwright/test';

test.describe('OpenClipPro', () => {
  test.describe('Landing Page', () => {
    test('should display hero section', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('h1')).toContainText('AI-Powered Video');
      await expect(page.locator('text=Get Started Free')).toBeVisible();
    });

    test('should display features section', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('text=Multi-AI Analysis')).toBeVisible();
      await expect(page.locator('text=Viral Score Engine')).toBeVisible();
      await expect(page.locator('text=Smart Auto-Crop')).toBeVisible();
    });

    test('should navigate to about page', async ({ page }) => {
      await page.goto('/');
      await page.click('text=About');
      await expect(page.locator('h1')).toContainText('About OpenClipPro');
    });

    test('should navigate to pricing page', async ({ page }) => {
      await page.goto('/');
      await page.click('text=Pricing');
      await expect(page.locator('h1')).toContainText('Simple Pricing');
    });
  });

  test.describe('Pricing Page', () => {
    test('should display all plans', async ({ page }) => {
      await page.goto('/pricing');
      await expect(page.locator('text=Free')).toBeVisible();
      await expect(page.locator('text=Pro')).toBeVisible();
      await expect(page.locator('text=Enterprise')).toBeVisible();
    });

    test('should highlight Pro as most popular', async ({ page }) => {
      await page.goto('/pricing');
      await expect(page.locator('text=Most Popular')).toBeVisible();
    });
  });

  test.describe('About Page', () => {
    test('should explain how it works', async ({ page }) => {
      await page.goto('/about');
      await expect(page.locator('text=How It Works')).toBeVisible();
      await expect(page.locator('text=Board of Advisors')).toBeVisible();
      await expect(page.locator('text=Privacy First')).toBeVisible();
    });
  });

  test.describe('Authentication', () => {
    test('should redirect unauthenticated users from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      await page.waitForURL('/');
    });

    test('should redirect unauthenticated users from settings', async ({ page }) => {
      await page.goto('/settings');
      await page.waitForURL('/');
    });
  });

  test.describe('Navigation', () => {
    test('should have logo linking home', async ({ page }) => {
      await page.goto('/about');
      await page.click('text=OpenClipPro');
      await expect(page).toHaveURL('/');
    });

    test('should catch-all redirect to home', async ({ page }) => {
      await page.goto('/nonexistent-page');
      await page.waitForURL('/');
    });
  });

  test.describe('Responsive Design', () => {
    test('should be responsive on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto('/');
      await expect(page.locator('h1')).toBeVisible();
    });
  });
});
