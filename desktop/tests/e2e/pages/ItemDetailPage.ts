import { type Page, type Locator } from '@playwright/test'
import { BasePage } from './BasePage'

export class ItemDetailPage extends BasePage {
  readonly backBtn: Locator
  readonly pageTitle: Locator
  readonly editTitleBtn: Locator
  readonly titleInput: Locator
  readonly saveBtn: Locator
  readonly cancelBtn: Locator
  readonly metaSection: Locator
  readonly tagsSection: Locator
  readonly contentPreview: Locator
  readonly notesInput: Locator
  readonly deleteBtn: Locator
  readonly loading: Locator

  constructor(page: Page) {
    super(page)
    this.backBtn = page.locator('.back-btn')
    this.pageTitle = page.locator('.page-title')
    this.editTitleBtn = page.locator('.icon-btn')
    this.titleInput = page.locator('.title-input')
    this.saveBtn = page.locator('.title-edit .save-btn')
    this.cancelBtn = page.locator('.cancel-btn')
    this.metaSection = page.locator('.meta-section')
    this.tagsSection = page.locator('.tags-section')
    this.contentPreview = page.locator('.content-preview')
    this.notesInput = page.locator('.notes-input')
    this.deleteBtn = page.locator('.actions .delete-btn')
    this.loading = page.locator('.loading')
  }

  async goto(id: string) {
    await this.navigateTo(`/items/detail/${id}`)
  }

  async startEditTitle() {
    await this.editTitleBtn.click()
  }

  async editTitle(newTitle: string) {
    await this.startEditTitle()
    await this.titleInput.fill(newTitle)
    await this.saveBtn.click()
  }

  async editNotes(notes: string) {
    await this.notesInput.fill(notes)
    await this.page.locator('.notes-header .save-btn').click()
  }

  async goBack() {
    await this.backBtn.click()
  }

  async getMetaItems() {
    return this.metaSection.locator('.meta-item').all()
  }

  async getTags() {
    return this.tagsSection.locator('.tag').allTextContents()
  }
}
