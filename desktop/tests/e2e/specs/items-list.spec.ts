import { test, expect } from '@playwright/test'
import { mockItems, mockTags } from '../fixtures/mock-data'

test.describe('Items List', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: mockItems }),
    )
    await page.route('**/api/tags', (route) =>
      route.fulfill({ json: mockTags }),
    )
    await page.goto('/items/note')
  })

  test('displays items list with correct count', async ({ page }) => {
    const items = page.locator('.item-row')
    await expect(items).toHaveCount(5)
  })

  test('displays item title, meta, and tags', async ({ page }) => {
    const firstItem = page.locator('.item-row').first()
    await expect(firstItem.locator('.item-title')).toHaveText('Test Item 1')
    await expect(firstItem.locator('.tag')).toHaveCount(2)
  })

  test('search filters items', async ({ page }) => {
    const filteredItems = [mockItems[0]]
    await page.route('**/api/items?*search=Test+Item+1*', (route) =>
      route.fulfill({ json: filteredItems }),
    )

    await page.locator('.search-input').fill('Test Item 1')
    await page.locator('.search-btn').click()

    await expect(page.locator('.item-row')).toHaveCount(1)
  })

  test('tag filter toggles active state', async ({ page }) => {
    const tagBtn = page.locator('.tag-btn').first()
    await tagBtn.click()
    await expect(tagBtn).toHaveClass(/active/)

    await tagBtn.click()
    await expect(tagBtn).not.toHaveClass(/active/)
  })

  test('displays tag filter buttons', async ({ page }) => {
    const tagBtns = page.locator('.tag-btn')
    await expect(tagBtns).toHaveCount(3)
    await expect(tagBtns.first()).toContainText('tag-a')
  })

  test('navigates to item detail on click', async ({ page }) => {
    await page.route('**/api/items/item-1', (route) =>
      route.fulfill({ json: mockItems[0] }),
    )
    await page.route('**/api/items/item-1/preview', (route) =>
      route.fulfill({ json: { content: '', file_path: '' } }),
    )

    await page.locator('.item-row').first().click()
    await expect(page).toHaveURL(/\/items\/detail\/item-1/)
  })

  test('pagination controls work', async ({ page }) => {
    const manyItems = [...mockItems, { ...mockItems[0], id: 'extra' }]
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: manyItems }),
    )
    await page.goto('/items/note')

    await expect(page.locator('.page-info')).toHaveText('1')
  })

  test('shows empty state when no items', async ({ page }) => {
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: [] }),
    )
    await page.goto('/items/note')

    await expect(page.locator('.empty')).toBeVisible()
  })

  test('resets filters when switching content type', async ({ page }) => {
    await page.locator('.search-input').fill('test query')

    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: mockItems }),
    )
    await page.goto('/items/bookmark')

    await expect(page.locator('.search-input')).toHaveValue('')
  })
})
