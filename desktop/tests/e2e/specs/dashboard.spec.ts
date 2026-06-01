import { test, expect } from '@playwright/test'
import { mockStats, mockRagStats, mockItems } from '../fixtures/mock-data'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/stats', (route) =>
      route.fulfill({ json: mockStats }),
    )
    await page.route('**/api/rag/stats', (route) =>
      route.fulfill({ json: mockRagStats }),
    )
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: mockItems }),
    )
    await page.goto('/')
  })

  test('displays stats cards with correct data', async ({ page }) => {
    const statsRow = page.locator('.stats-row')
    await expect(statsRow).toBeVisible()

    const cards = statsRow.locator('.stat-card')
    await expect(cards).toHaveCount(3)

    await expect(cards.nth(0).locator('.stat-value')).toHaveText('42')
    await expect(cards.nth(1).locator('.stat-value')).toHaveText('15')
    await expect(cards.nth(2).locator('.stat-value')).toHaveText('128')
  })

  test('displays 6 type cards with counts', async ({ page }) => {
    const typeCards = page.locator('.type-card')
    await expect(typeCards).toHaveCount(6)

    await expect(typeCards.nth(0).locator('.type-count')).toHaveText('10')
    await expect(typeCards.nth(2).locator('.type-count')).toHaveText('12')
  })

  test('navigates to items list when clicking type card', async ({ page }) => {
    await page.locator('.type-card').first().click()
    await expect(page).toHaveURL(/\/items\/note/)
  })

  test('displays recent items list', async ({ page }) => {
    const recentItems = page.locator('.recent-item')
    await expect(recentItems).toHaveCount(5)

    await expect(recentItems.first().locator('.recent-item-title')).toHaveText('Test Item 1')
  })

  test('navigates to detail when clicking recent item', async ({ page }) => {
    await page.route('**/api/items/item-1', (route) =>
      route.fulfill({ json: mockItems[0] }),
    )
    await page.route('**/api/items/item-1/preview', (route) =>
      route.fulfill({ json: { content: '', file_path: '' } }),
    )

    await page.locator('.recent-item').first().click()
    await expect(page).toHaveURL(/\/items\/detail\/item-1/)
  })

  test('shows loading state initially', async ({ page }) => {
    await page.route('**/api/stats', (route) =>
      new Promise((resolve) => setTimeout(() => resolve(route.fulfill({ json: mockStats })), 2000)),
    )
    await page.goto('/')
    await expect(page.locator('.loading')).toBeVisible()
  })
})
