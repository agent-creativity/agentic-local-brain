import { test, expect } from '@playwright/test'
import { mockItemDetail, mockPreview } from '../fixtures/mock-data'

test.describe('Item Detail', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/items/item-1', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ json: mockItemDetail })
      }
      return route.fulfill({ json: { ...mockItemDetail, ...JSON.parse(route.request().postData() || '{}') } })
    })
    await page.route('**/api/items/item-1/preview', (route) =>
      route.fulfill({ json: mockPreview }),
    )
    await page.goto('/items/detail/item-1')
  })

  test('displays item title', async ({ page }) => {
    await expect(page.locator('.page-title')).toHaveText('Test Item 1')
  })

  test('displays metadata section', async ({ page }) => {
    const metaSection = page.locator('.meta-section')
    await expect(metaSection).toBeVisible()
    await expect(metaSection.locator('.meta-item')).toHaveCount(4)
  })

  test('displays tags', async ({ page }) => {
    const tags = page.locator('.tags-section .tag')
    await expect(tags).toHaveCount(2)
    await expect(tags.first()).toHaveText('tag-a')
  })

  test('displays content preview', async ({ page }) => {
    await expect(page.locator('.content-preview')).toContainText('Full preview content')
  })

  test('edit title via button click', async ({ page }) => {
    await page.route('**/api/items/item-1', (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ json: { ...mockItemDetail, title: 'Updated Title' } })
      }
      return route.fulfill({ json: mockItemDetail })
    })

    await page.locator('.icon-btn').click()
    await expect(page.locator('.title-input')).toBeVisible()

    await page.locator('.title-input').fill('Updated Title')
    await page.locator('.title-edit .save-btn').click()

    await expect(page.locator('.page-title')).toHaveText('Updated Title')
  })

  test('cancel title edit', async ({ page }) => {
    await page.locator('.icon-btn').click()
    await page.locator('.title-input').fill('Should Not Save')
    await page.locator('.cancel-btn').click()

    await expect(page.locator('.page-title')).toHaveText('Test Item 1')
  })

  test('edit title via double-click', async ({ page }) => {
    await page.locator('.page-title').dblclick()
    await expect(page.locator('.title-input')).toBeVisible()
  })

  test('displays and edits user notes', async ({ page }) => {
    await expect(page.locator('.notes-input')).toHaveValue('My notes here')
  })

  test('back button navigates away', async ({ page }) => {
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: [] }),
    )
    await page.route('**/api/tags', (route) =>
      route.fulfill({ json: [] }),
    )

    await page.goto('/items/note')
    await page.goto('/items/detail/item-1')
    await page.locator('.back-btn').click()

    await expect(page).toHaveURL(/\/items\/note/)
  })
})
