import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'

export class DashboardPage extends BasePage {
  readonly statsRow: Locator
  readonly typeGrid: Locator
  readonly recentList: Locator
  readonly loading: Locator

  constructor(page: Page) {
    super(page)
    this.statsRow = page.locator('.stats-row')
    this.typeGrid = page.locator('.type-grid')
    this.recentList = page.locator('.recent-list')
    this.loading = page.locator('.loading')
  }

  async goto() {
    await this.navigateTo('/')
  }

  async getStatCards() {
    return this.statsRow.locator('.stat-card').all()
  }

  async getTypeCards() {
    return this.typeGrid.locator('.type-card').all()
  }

  async getRecentItems() {
    return this.recentList.locator('.recent-item').all()
  }

  async clickTypeCard(index: number) {
    const cards = await this.getTypeCards()
    await cards[index].click()
  }

  async clickRecentItem(index: number) {
    const items = await this.getRecentItems()
    await items[index].click()
  }
}
