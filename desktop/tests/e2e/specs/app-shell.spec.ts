import { test, expect } from '@playwright/test'
import { mockStats, mockRagStats, mockItems, mockTags } from '../fixtures/mock-data'

test.describe('App Shell', () => {
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
    await page.route('**/api/tags', (route) =>
      route.fulfill({ json: mockTags }),
    )
    await page.goto('/')
  })

  test('sidebar displays app name', async ({ page }) => {
    await expect(page.locator('.sidebar-name')).toBeVisible()
  })

  test('sidebar contains all navigation groups', async ({ page }) => {
    const navGroups = page.locator('.nav-group')
    await expect(navGroups).toHaveCount(4)
  })

  test('sidebar highlights active route', async ({ page }) => {
    const dashboardLink = page.locator('.nav-item.active')
    await expect(dashboardLink).toHaveCount(1)
  })

  test('navigation to different pages works', async ({ page }) => {
    await page.locator('.nav-item', { hasText: /bookmark/i }).click()
    await expect(page).toHaveURL(/\/items\/bookmark/)
    await expect(page.locator('.nav-item.active')).toHaveCount(1)
  })

  test('sidebar shows all 6 knowledge types', async ({ page }) => {
    const knowledgeGroup = page.locator('.nav-group').nth(1)
    const items = knowledgeGroup.locator('.nav-item')
    await expect(items).toHaveCount(6)
  })

  test('sidebar shows discover section', async ({ page }) => {
    const discoverGroup = page.locator('.nav-group').nth(2)
    const items = discoverGroup.locator('.nav-item')
    await expect(items).toHaveCount(5)
  })

  test('sidebar shows tools section', async ({ page }) => {
    const toolsGroup = page.locator('.nav-group').nth(3)
    const items = toolsGroup.locator('.nav-item')
    await expect(items).toHaveCount(4)
  })
})
