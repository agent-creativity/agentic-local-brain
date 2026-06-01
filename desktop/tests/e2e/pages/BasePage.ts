import { type Page, type Locator } from '@playwright/test'

export class BasePage {
  readonly page: Page
  readonly sidebar: Locator

  constructor(page: Page) {
    this.page = page
    this.sidebar = page.locator('[data-testid="app-sidebar"]')
  }

  async navigateTo(path: string) {
    await this.page.goto(path)
    await this.page.waitForLoadState('networkidle')
  }

  async getSidebarLinks(): Promise<string[]> {
    const links = this.sidebar.locator('a')
    return links.allTextContents()
  }
}
