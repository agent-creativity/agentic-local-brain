import { test, expect } from '@playwright/test'
import { mockConversations, mockConversationDetail } from '../fixtures/mock-data-phase2'

test.describe('RAG Chat', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/rag/conversations', (route) => {
      if (route.request().method() === 'GET') return route.fulfill({ json: mockConversations })
      return route.fulfill({ json: {} })
    })
    await page.route('**/api/rag/conversations/*', (route) => {
      if (route.request().method() === 'GET') return route.fulfill({ json: mockConversationDetail })
      if (route.request().method() === 'DELETE') return route.fulfill({ json: {} })
      return route.continue()
    })
    await page.route('**/api/rag/chat', (route) =>
      route.fulfill({
        json: {
          answer: 'Machine learning is a subset of AI.',
          session_id: 'sess-new',
          sources: [{ id: 'src-1', title: 'ML Guide', score: 0.9 }],
        },
      }),
    )
    await page.goto('/rag')
  })

  test('displays conversation sidebar', async ({ page }) => {
    await expect(page.getByText('About ML')).toBeVisible()
    await expect(page.getByText('Code review')).toBeVisible()
  })

  test('loads conversation history on click', async ({ page }) => {
    await page.getByText('About ML').click()
    await expect(page.getByText('What is ML?')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Machine learning is...')).toBeVisible()
  })

  test('send message and receive response', async ({ page }) => {
    const input = page.locator('input[type="text"], textarea, .chat-input').first()
    await input.fill('What is deep learning?')

    const sendBtn = page.locator('button', { hasText: /发送|Send/ }).or(page.locator('button[type="submit"]')).first()
    await sendBtn.click()

    await expect(page.getByText('Machine learning is a subset of AI.')).toBeVisible({ timeout: 5000 })
  })

  test('new conversation button clears chat', async ({ page }) => {
    await page.getByText('About ML').click()
    await expect(page.getByText('What is ML?')).toBeVisible({ timeout: 5000 })

    const newBtn = page.locator('button', { hasText: /新建|New|新对话/ })
    if (await newBtn.isVisible()) {
      await newBtn.click()
      await expect(page.getByText('What is ML?')).not.toBeVisible()
    }
  })

  test('sources are displayed with chat response', async ({ page }) => {
    await page.getByText('About ML').click()
    await expect(page.getByText('ML Guide').or(page.getByText('src-1')).first()).toBeVisible({ timeout: 5000 })
  })
})
