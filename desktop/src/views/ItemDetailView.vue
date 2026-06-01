<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getItem, updateItem, previewItem, deleteItem } from '../api/items'
import type { KnowledgeItem } from '../api/types'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const itemId = route.params.id as string
const item = ref<KnowledgeItem | null>(null)
const preview = ref('')
const loading = ref(true)
const error = ref('')

const editingTitle = ref(false)
const titleDraft = ref('')
const notesDraft = ref('')
const savingNotes = ref(false)

onMounted(async () => {
  try {
    const [itemData, previewData] = await Promise.all([
      getItem(itemId),
      previewItem(itemId).catch(() => ({ content: '', file_path: '' })),
    ])
    item.value = itemData
    preview.value = previewData.content
    titleDraft.value = itemData.title || ''
    notesDraft.value = itemData.user_notes || ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function saveTitle() {
  if (!item.value) return
  try {
    await updateItem(itemId, { title: titleDraft.value })
    item.value.title = titleDraft.value
    editingTitle.value = false
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

async function saveNotes() {
  if (!item.value) return
  savingNotes.value = true
  try {
    await updateItem(itemId, { user_notes: notesDraft.value })
    item.value.user_notes = notesDraft.value
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  } finally {
    savingNotes.value = false
  }
}

async function removeItem() {
  if (!confirm(t('items.confirmDelete'))) return
  try {
    await deleteItem(itemId)
    router.back()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="page">
    <button class="back-btn" @click="router.back()">← {{ t('items.previous') }}</button>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="item">
      <!-- Title -->
      <div class="title-section">
        <div v-if="!editingTitle" class="title-row">
          <h1 class="page-title" @dblclick="editingTitle = true">{{ item.title || 'Untitled' }}</h1>
          <button class="icon-btn" @click="editingTitle = true" :title="t('items.editTitle')">✏️</button>
        </div>
        <div v-else class="title-edit">
          <input v-model="titleDraft" class="title-input" @keydown.enter="saveTitle" @keydown.escape="editingTitle = false" />
          <button class="save-btn" @click="saveTitle">{{ t('common.save') }}</button>
          <button class="cancel-btn" @click="editingTitle = false">{{ t('common.cancel') }}</button>
        </div>
      </div>

      <!-- Meta -->
      <div class="meta-section">
        <div v-if="item.content_type" class="meta-item">
          <span class="meta-label">{{ t('items.filterByType') }}</span>
          <span class="meta-value type-badge">{{ item.content_type }}</span>
        </div>
        <div v-if="item.source" class="meta-item">
          <span class="meta-label">{{ t('items.source') }}</span>
          <span class="meta-value">{{ item.source }}</span>
        </div>
        <div v-if="item.collected_at" class="meta-item">
          <span class="meta-label">{{ t('items.collectedAt') }}</span>
          <span class="meta-value">{{ formatDate(item.collected_at) }}</span>
        </div>
        <div v-if="item.word_count" class="meta-item">
          <span class="meta-label">{{ t('items.wordCount') }}</span>
          <span class="meta-value">{{ item.word_count }}</span>
        </div>
      </div>

      <!-- Tags -->
      <div v-if="item.tags.length" class="tags-section">
        <span class="meta-label">{{ t('items.tags') }}</span>
        <div class="tags">
          <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>

      <!-- Content preview -->
      <div v-if="preview" class="content-section">
        <div class="content-preview" v-text="preview" />
      </div>
      <div v-else-if="item.summary" class="content-section">
        <div class="content-preview">{{ item.summary }}</div>
      </div>

      <!-- User notes -->
      <div class="notes-section">
        <div class="notes-header">
          <span class="meta-label">{{ t('items.notes') }}</span>
          <button class="save-btn" :disabled="savingNotes" @click="saveNotes">
            {{ savingNotes ? t('common.loading') : t('items.saveNotes') }}
          </button>
        </div>
        <textarea
          v-model="notesDraft"
          class="notes-input"
          rows="4"
          :placeholder="t('items.notes') + '...'"
        />
      </div>

      <!-- Actions -->
      <div class="actions">
        <button class="delete-btn" @click="removeItem">{{ t('common.delete') }}</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 900px; }

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  margin-bottom: 16px;
}

.back-btn:hover { text-decoration: underline; }

.loading, .error {
  padding: 40px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.error { color: #FF3B30; }

.title-section { margin-bottom: 16px; }

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  cursor: default;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
  opacity: 0.5;
  transition: opacity 0.15s;
}

.icon-btn:hover { opacity: 1; }

.title-edit {
  display: flex;
  gap: 8px;
  align-items: center;
}

.title-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  font-size: 18px;
  font-weight: 600;
  outline: none;
  background: transparent;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

@media (prefers-color-scheme: dark) {
  .title-input { color: var(--color-text-primary-dark); }
}

.save-btn {
  padding: 4px 12px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.cancel-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
}

.meta-section {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px 16px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: 16px;
}

@media (prefers-color-scheme: dark) {
  .meta-section { background: var(--color-surface-dark); }
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  font-size: 11px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-value { font-size: 13px; }

.type-badge {
  display: inline-block;
  padding: 1px 8px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

@media (prefers-color-scheme: dark) {
  .type-badge { background: rgba(0, 122, 255, 0.2); }
}

.tags-section {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.tags { display: flex; flex-wrap: wrap; gap: 4px; }

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--color-primary-light);
  color: var(--color-primary);
}

@media (prefers-color-scheme: dark) {
  .tag { background: rgba(0, 122, 255, 0.2); }
}

.content-section { margin-bottom: 24px; }

.content-preview {
  padding: 20px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 600px;
  overflow-y: auto;
}

@media (prefers-color-scheme: dark) {
  .content-preview { background: var(--color-surface-dark); }
}

.notes-section { margin-bottom: 24px; }

.notes-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.notes-input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  resize: vertical;
  outline: none;
}

@media (prefers-color-scheme: dark) {
  .notes-input {
    background: var(--color-surface-dark);
    border-color: var(--color-border-dark);
    color: var(--color-text-primary-dark);
  }
}

.notes-input:focus { border-color: var(--color-primary); }

.actions {
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

@media (prefers-color-scheme: dark) {
  .actions { border-top-color: var(--color-border-dark); }
}

.delete-btn {
  padding: 6px 16px;
  border: 1px solid #FF3B30;
  border-radius: var(--radius-md);
  background: transparent;
  color: #FF3B30;
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.delete-btn:hover {
  background: #FF3B30;
  color: white;
}
</style>
