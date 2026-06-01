import { test, expect } from '@playwright/test'
import { mockRecommendations, mockReadingHistory } from '../fixtures/mock-data-phase2'

test.describe('Recommendations', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/recommendations*', (route) =>
      route.fulfill({ json: mockRecommendations }),
    )
    await page.route('**/api/reading-history*', (route) =>
      route.fulfill({ json: mockReadingHistory }),
    )
    await page.goto('/recommendations')
  })

  test('displays recommendations with scores', async ({ page }) => {
    await expect(page.getByText('Recommended Article 1')).toBeVisible()
    await expect(page.getByText('95%')).toBeVisible()
    await expect(page.getByText('87%')).toBeVisible()
  })

  test('displays recommendation reasons', async ({ page }) => {
    await expect(page.getByText('Similar to your recent reads')).toBeVisible()
  })

  test('switches to reading history tab', async ({ page }) => {
    await page.getByText('阅读历史').click()
    await expect(page.getByText('view')).toBeVisible()
    await expect(page.getByText('machine learning')).toBeVisible()
  })

  test('clicking recommendation navigates to detail', async ({ page }) => {
    await page.route('**/api/items/rec-1', (route) =>
      route.fulfill({ json: { id: 'rec-1', title: 'Recommended Article 1', content_type: 'webpage', tags: [], user_notes: '' } }),
    )
    await page.route('**/api/items/rec-1/preview', (route) =>
      route.fulfill({ json: { content: '', file_path: '' } }),
    )

    await page.locator('.rec-card').first().click()
    await expect(page).toHaveURL(/\/items\/detail\/rec-1/)
  })

  test('shows empty state when no recommendations', async ({ page }) => {
    await page.route('**/api/recommendations*', (route) =>
      route.fulfill({ json: [] }),
    )
    await page.goto('/recommendations')
    await expect(page.locator('.empty')).toBeVisible()
  })
})
