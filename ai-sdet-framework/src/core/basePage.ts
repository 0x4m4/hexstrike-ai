import { Page, Locator } from '@playwright/test';
import { AppConfig } from './configLoader';

export class BasePage {
  protected page: Page;
  protected config: AppConfig;

  constructor(page: Page, config: AppConfig) {
    this.page = page;
    this.config = config;
  }

  async navigate(path: string = '/') {
    await this.page.goto(`${this.config.baseUrl}${path}`);
  }

  getSelector(pageName: string, elementKey: string): string {
    const selector = this.config.selectors[pageName]?.[elementKey];
    if (!selector) {
      throw new Error(`Selector not found for ${pageName}.${elementKey}`);
    }
    return selector;
  }

  getLocator(pageName: string, elementKey: string): Locator {
    return this.page.locator(this.getSelector(pageName, elementKey));
  }

  async click(pageName: string, elementKey: string) {
    await this.getLocator(pageName, elementKey).click();
  }

  async fill(pageName: string, elementKey: string, value: string) {
    await this.getLocator(pageName, elementKey).fill(value);
  }
}
