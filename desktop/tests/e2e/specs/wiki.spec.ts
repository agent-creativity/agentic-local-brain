import { test, expect } from '@playwright/test'
import { mockWikiTree, mockWikiStats, mockWikiArticles } from '../fixtures/mock-data-phase2'

test.describe('Wiki', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/wiki/tree', (route) =>
      route.fulfill({ json: mockWikiTree }),
    )
    await page.route('**/api/wiki/stats', (route) =>
      route.fulfill({ json: mockWikiStats }),
    )
    await page.route('**/api/wiki/categories/*/articles*', (route) =>
      route.fulfill({ json: mockWikiArticles }),
    )
    await page.route('**/api/wiki/topics/*/articles*', (route) =>
      route.fulfill({ json: mockWikiArticles }),
    )
    await page.route('**/api/wiki/articles/*', (route) =>
      route.fulfill({ json: mockWikiArticles[0] }),
    )
    await page.route('**/api/wiki/search*', (route) =>
      route.fulfill({ json: mockWikiArticles }),
    )
    await page.goto('/wiki')
  })

  test('displays category navigation', async ({ page }) => {
    await expect(page.getByText('Technology')).toBeVisible()
    await expect(page.getByText('Science')).toBeVisible()
  })

  test('clicking category loads articles', async ({ page }) => {
    await page.getByText('Technology').click()
    await expect(page.getByText('Python Programming')).toBeVisible({ timeout: 5000 })
  })

  test('clicking article shows content', async ({ page }) => {
    await page.getByText('Technology').click()
    await page.getByText('Python Programming').click()
    await expect(page.getByText(/Python is/)).toBeVisible({ timeout: 5000 })
  })

  test('displays wiki stats', async ({ page }) => {
    await expect(page.getByText('25').or(page.getByText('5')).first()).toBeVisible()
  })

  test('topic navigation works', async ({ page }) => {
    await page.getByText('Programming').click()
    await expect(page.getByText('Python Programming')).toBeVisible({ timeout: 5000 })
  })
})
