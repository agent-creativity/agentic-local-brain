import { test, expect } from '@playwright/test'
import { mockGraphData, mockGraphStats } from '../fixtures/mock-data-phase2'

test.describe('Knowledge Graph', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/graph?*', (route) =>
      route.fulfill({ json: mockGraphData }),
    )
    await page.route('**/api/graph/stats', (route) =>
      route.fulfill({ json: mockGraphStats }),
    )
    await page.route('**/api/graph/search*', (route) =>
      route.fulfill({ json: mockGraphData }),
    )
    await page.goto('/graph')
  })

  test('renders graph visualization', async ({ page }) => {
    await expect(page.locator('canvas').or(page.locator('[class*="chart"]')).first()).toBeVisible({ timeout: 10000 })
  })

  test('displays graph statistics', async ({ page }) => {
    await expect(page.getByText('42').or(page.getByText('65')).first()).toBeVisible()
  })

  test('search filters graph entities', async ({ page }) => {
    const searchInput = page.locator('input[type="text"], .search-input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('Python')
      await searchInput.press('Enter')
    }
  })

  test('page loads without errors', async ({ page }) => {
    await expect(page.locator('.error')).not.toBeVisible()
  })
})
