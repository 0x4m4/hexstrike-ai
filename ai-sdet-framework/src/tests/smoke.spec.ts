import { test, expect } from '@playwright/test';
import { ConfigLoader } from '../core/configLoader';
import { BasePage } from '../core/basePage';

test.describe('Universal SDET Framework Smoke Tests', () => {
  let config = ConfigLoader.loadConfig('example');

  test('Basic navigation and element verification', async ({ page }) => {
    const basePage = new BasePage(page, config);

    await basePage.navigate();

    const titleLocator = basePage.getLocator('home', 'title');
    await expect(titleLocator).toBeVisible();
    await expect(titleLocator).toHaveText('Example Domain');

    const moreInfoLocator = basePage.getLocator('home', 'moreInfoLink');
    await expect(moreInfoLocator).toBeVisible();
    await expect(moreInfoLocator).toHaveAttribute('href', 'https://iana.org/domains/example');
  });
});
