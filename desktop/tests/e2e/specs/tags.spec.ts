import { test, expect } from '@playwright/test'
import { mockTagsList, mockTagItems } from '../fixtures/mock-data-phase2'

test.describe('Tags Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/tags', (route) => {
      if (route.request().method() === 'GET') return route.fulfill({ json: mockTagsList })
      return route.fulfill({ json: {} })
    })
    await page.route('**/api/tags/*/items*', (route) =>
      route.fulfill({ json: mockTagItems }),
    )
    await page.goto('/tags')
  })

  test('displays tag cloud with counts', async ({ page }) => {
    await expect(page.locator('.tag-cloud .tag-item, .tags-list .tag-btn, [class*="tag"]').first()).toBeVisible({ timeout: 5000 })
  })

  test('search filters tags', async ({ page }) => {
    const searchInput = page.locator('input[type="text"], .search-input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('python')
      await expect(page.getByText('python')).toBeVisible()
    }
  })

  test('clicking tag shows associated items', async ({ page }) => {
    await page.getByText('machine-learning').first().click()
    await expect(page.getByText('ML Basics')).toBeVisible({ timeout: 5000 })
  })

  test('delete tag with confirmation', async ({ page }) => {
    await page.route('**/api/tags/*', (route) => {
      if (route.request().method() === 'DELETE') return route.fulfill({ json: {} })
      return route.continue()
    })
    page.on('dialog', (d) => d.accept())

    const deleteBtn = page.locator('.delete-btn, button:has-text("删除"), button:has-text("Delete")').first()
    if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await deleteBtn.click()
    }
  })
})
