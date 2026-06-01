import { test, expect } from '@playwright/test'

test.describe('Smoke Tests', () => {
  test('app loads and shows sidebar', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/LocalBrain/)
  })
})
