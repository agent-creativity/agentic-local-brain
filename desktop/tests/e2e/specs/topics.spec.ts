import { test, expect } from '@playwright/test'
import { mockTopicClusters, mockTopicDocuments } from '../fixtures/mock-data-phase2'

test.describe('Topics & Clustering', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/topics', (route) =>
      route.fulfill({ json: mockTopicClusters }),
    )
    await page.route('**/api/topics/*/documents*', (route) =>
      route.fulfill({ json: mockTopicDocuments }),
    )
    await page.goto('/topics')
  })

  test('displays topic clusters', async ({ page }) => {
    await expect(page.getByText('AI & Machine Learning')).toBeVisible()
    await expect(page.getByText('Web Development')).toBeVisible()
  })

  test('shows cluster keywords and document count', async ({ page }) => {
    await expect(page.getByText('12').first()).toBeVisible()
  })

  test('clicking cluster shows associated documents', async ({ page }) => {
    await page.getByText('AI & Machine Learning').click()
    await expect(page.getByText('Intro to ML')).toBeVisible({ timeout: 5000 })
  })

  test('rebuild topics button exists', async ({ page }) => {
    await page.route('**/api/topics/rebuild', (route) =>
      route.fulfill({ json: { status: 'started' } }),
    )
    await page.route('**/api/topics/rebuild/status', (route) =>
      route.fulfill({ json: { status: 'completed', message: 'Done' } }),
    )

    const rebuildBtn = page.locator('button', { hasText: /重建|Rebuild/ })
    await expect(rebuildBtn).toBeVisible()
  })

  test('toggle cluster deselects it', async ({ page }) => {
    await page.getByText('AI & Machine Learning').click()
    await expect(page.getByText('Intro to ML')).toBeVisible({ timeout: 5000 })

    await page.getByText('AI & Machine Learning').click()
    await expect(page.getByText('Intro to ML')).not.toBeVisible()
  })
})
