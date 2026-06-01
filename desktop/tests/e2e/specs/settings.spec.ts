import { test, expect } from '@playwright/test'
import { mockSettings, mockDoctorResult } from '../fixtures/mock-data-phase2'

test.describe('System Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/settings', (route) =>
      route.fulfill({ json: mockSettings }),
    )
    await page.route('**/api/settings/llm', (route) =>
      route.fulfill({ json: {} }),
    )
    await page.route('**/api/settings/embedding', (route) =>
      route.fulfill({ json: {} }),
    )
    await page.route('**/api/settings/test/llm', (route) =>
      route.fulfill({ json: { success: true, message: 'Connected', latency_ms: 120 } }),
    )
    await page.route('**/api/settings/test/embedding', (route) =>
      route.fulfill({ json: { success: true, message: 'Connected', latency_ms: 80 } }),
    )
    await page.route('**/api/settings/doctor', (route) =>
      route.fulfill({ json: mockDoctorResult }),
    )
    await page.goto('/settings')
  })

  test('displays LLM settings with current values', async ({ page }) => {
    await expect(page.getByDisplayValue('dashscope').or(page.getByText('dashscope')).first()).toBeVisible()
    await expect(page.getByDisplayValue('qwen-max').or(page.getByText('qwen-max')).first()).toBeVisible()
  })

  test('LLM connection test shows result', async ({ page }) => {
    const testBtn = page.locator('button', { hasText: /测试|Test/ }).first()
    await testBtn.click()
    await expect(page.getByText(/Connected|成功|120/)).toBeVisible({ timeout: 5000 })
  })

  test('switches to embedding tab', async ({ page }) => {
    const embeddingTab = page.locator('button', { hasText: /Embedding|向量/ })
    if (await embeddingTab.isVisible()) {
      await embeddingTab.click()
      await expect(page.getByDisplayValue('text-embedding-v2').or(page.getByText('text-embedding-v2')).first()).toBeVisible()
    }
  })

  test('switches to doctor tab and runs diagnostics', async ({ page }) => {
    const doctorTab = page.locator('button', { hasText: /Doctor|诊断/ })
    if (await doctorTab.isVisible()) {
      await doctorTab.click()
      const runBtn = page.locator('button', { hasText: /运行|Run|诊断/ }).first()
      if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await runBtn.click()
        await expect(page.getByText(/SQLite|database|ok/).first()).toBeVisible({ timeout: 5000 })
      }
    }
  })

  test('page loads without errors', async ({ page }) => {
    await expect(page.locator('.error')).not.toBeVisible()
  })
})
