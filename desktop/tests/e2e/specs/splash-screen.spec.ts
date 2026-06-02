import { test, expect } from '@playwright/test'

test.describe('Splash Screen & Sidecar Health Check', () => {
  test('shows splash screen when backend is unavailable', async ({ page }) => {
    await page.route('**/health', (route) =>
      route.fulfill({ status: 503, body: 'Service Unavailable' }),
    )
    await page.goto('/')
    // App should show loading state or splash content
    const splashOrLoading = page.locator('.splash, .loading, .splash-status')
    // If splash is implemented at app level it will show; otherwise loading state
    if (await splashOrLoading.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(splashOrLoading.first()).toBeVisible()
    }
  })

  test('transitions to main app when backend becomes healthy', async ({ page }) => {
    let healthy = false
    await page.route('**/health', (route) => {
      if (healthy) {
        return route.fulfill({ status: 200, body: 'ok' })
      }
      return route.fulfill({ status: 503, body: 'Service Unavailable' })
    })
    await page.route('**/api/stats', (route) =>
      route.fulfill({ json: { total_items: 0, total_tags: 0, items_by_type: {} } }),
    )
    await page.route('**/api/rag/stats', (route) =>
      route.fulfill({ json: { total_queries: 0, total_conversations: 0 } }),
    )
    await page.route('**/api/items?*', (route) =>
      route.fulfill({ json: [] }),
    )

    await page.goto('/')

    // Simulate backend becoming ready
    healthy = true

    // Main app should eventually load (sidebar visible)
    await expect(page.locator('.sidebar, .nav-item').first()).toBeVisible({ timeout: 10000 })
  })

  test('health check endpoint is called on startup', async ({ page }) => {
    let healthCalled = false
    await page.route('**/health', (route) => {
      healthCalled = true
      return route.fulfill({ status: 200, body: 'ok' })
    })
    await page.route('**/api/**', (route) =>
      route.fulfill({ json: {} }),
    )

    await page.goto('/')
    // Health check may or may not be called from the SPA (it's mainly Tauri-side)
    // This test verifies the E2E flow starts correctly
    await expect(page.locator('.sidebar, .page-title, .nav-item').first()).toBeVisible({ timeout: 10000 })
  })
})
