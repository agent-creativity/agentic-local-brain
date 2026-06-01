import { type Page, type Locator } from '@playwright/test'
import { BasePage } from './BasePage'

export class ItemsPage extends BasePage {
  readonly searchInput: Locator
  readonly searchBtn: Locator
  readonly tagFilter: Locator
  readonly itemsList: Locator
  readonly pagination: Locator
  readonly loading: Locator
  readonly empty: Locator

  constructor(page: Page) {
    super(page)
    this.searchInput = page.locator('.search-input')
    this.searchBtn = page.locator('.search-btn')
    this.tagFilter = page.locator('.tag-filter')
    this.itemsList = page.locator('.items-list')
    this.pagination = page.locator('.pagination')
    this.loading = page.locator('.loading')
    this.empty = page.locator('.empty')
  }

  async goto(type: string) {
    await this.navigateTo(`/items/${type}`)
  }

  async search(query: string) {
    await this.searchInput.fill(query)
    await this.searchBtn.click()
  }

  async selectTag(tagName: string) {
    await this.tagFilter.locator('.tag-btn', { hasText: tagName }).click()
  }

  async getItems() {
    return this.itemsList.locator('.item-row').all()
  }

  async clickItem(index: number) {
    const items = await this.getItems()
    await items[index].click()
  }

  async nextPage() {
    await this.pagination.locator('.page-btn').last().click()
  }

  async prevPage() {
    await this.pagination.locator('.page-btn').first().click()
  }

  async getCurrentPage() {
    return this.pagination.locator('.page-info').textContent()
  }
}
