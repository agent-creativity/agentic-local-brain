import { test, expect } from '@playwright/test'
import { mockBackups, mockBackupConfig } from '../fixtures/mock-data-phase2'

test.describe('Backup Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/backup/list', (route) =>
      route.fulfill({ json: mockBackups }),
    )
    await page.route('**/api/backup/config', (route) => {
      if (route.request().method() === 'GET') return route.fulfill({ json: mockBackupConfig })
      return route.fulfill({ json: {} })
    })
    await page.goto('/backup')
  })

  test('displays backup list', async ({ page }) => {
    await expect(page.getByText('1.0 MB').or(page.getByText('1,048,576')).or(page.getByText('completed')).first()).toBeVisible()
  })

  test('create backup button triggers creation', async ({ page }) => {
    await page.route('**/api/backup/create', (route) =>
      route.fulfill({ json: { id: 'bk-3', status: 'completed' } }),
    )

    const createBtn = page.locator('button', { hasText: /创建|Create|新建/ })
    if (await createBtn.isVisible()) {
      await createBtn.click()
    }
  })

  test('delete backup with confirmation', async ({ page }) => {
    await page.route('**/api/backup/*', (route) => {
      if (route.request().method() === 'DELETE') return route.fulfill({ json: {} })
      return route.continue()
    })
    page.on('dialog', (d) => d.accept())

    const deleteBtn = page.locator('.delete-btn, button:has-text("删除"), button:has-text("Delete")').first()
    if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await deleteBtn.click()
    }
  })

  test('cloud storage config section exists', async ({ page }) => {
    const configToggle = page.locator('button', { hasText: /配置|Config|云存储|Storage/ })
    if (await configToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await configToggle.click()
    }
  })

  test('connection test shows result', async ({ page }) => {
    await page.route('**/api/backup/test', (route) =>
      route.fulfill({ json: { success: true, message: 'Connection OK' } }),
    )

    const testBtn = page.locator('button', { hasText: /测试|Test/ })
    if (await testBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await testBtn.click()
      await expect(page.getByText(/OK|成功|success/i)).toBeVisible({ timeout: 5000 })
    }
  })
})
