<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { listItems, deleteItem } from '../api/items'
import { listTags } from '../api/tags'
import type { KnowledgeItem, Tag } from '../api/types'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const contentType = computed(() => (route.params.type as string) || '')
const items = ref<KnowledgeItem[]>([])
const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref('')

const searchQuery = ref('')
const selectedTag = ref('')
const page = ref(0)
const pageSize = 20
const hasMore = ref(false)

async function fetchItems() {
  loading.value = true
  error.value = ''
  try {
    const result = await listItems({
      content_type: contentType.value || undefined,
      limit: pageSize + 1,
      offset: page.value * pageSize,
      search: searchQuery.value || undefined,
      tag: selectedTag.value || undefined,
    })
    hasMore.value = result.length > pageSize
    items.value = result.slice(0, pageSize)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function fetchTags() {
  try {
    tags.value = await listTags()
  } catch {
    // non-critical
  }
}

onMounted(() => {
  fetchItems()
  fetchTags()
})

watch(contentType, () => {
  page.value = 0
  searchQuery.value = ''
  selectedTag.value = ''
  fetchItems()
})

function onSearch() {
  page.value = 0
  fetchItems()
}

function onTagFilter(tag: string) {
  selectedTag.value = selectedTag.value === tag ? '' : tag
  page.value = 0
  fetchItems()
}

function prevPage() {
  if (page.value > 0) {
    page.value--
    fetchItems()
  }
}

function nextPage() {
  if (hasMore.value) {
    page.value++
    fetchItems()
  }
}

function viewItem(id: string) {
  router.push(`/items/detail/${id}`)
}

async function removeItem(id: string) {
  if (!confirm(t('items.confirmDelete'))) return
  try {
    await deleteItem(id)
    items.value = items.value.filter((i) => i.id !== id)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function truncate(text: string | null, len: number) {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '...' : text
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ contentType ? t(`nav.${contentType}`) : t('nav.allItems') }}</h1>

    <!-- Search and filter bar -->
    <div class="filter-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          :placeholder="t('items.searchPlaceholder')"
          class="search-input"
          @keydown.enter="onSearch"
        />
        <button class="search-btn" @click="onSearch">{{ t('items.search') }}</button>
      </div>
    </div>

    <!-- Tag filter -->
    <div v-if="tags.length" class="tag-filter">
      <button
        v-for="tag in tags.slice(0, 20)"
        :key="tag.name"
        class="tag-btn"
        :class="{ active: selectedTag === tag.name }"
        @click="onTagFilter(tag.name)"
      >
        {{ tag.name }}
        <span class="tag-count">{{ tag.count }}</span>
      </button>
    </div>

    <!-- Items list -->
    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="items.length === 0" class="empty">{{ t('items.noItemsFound') }}</div>
    <div v-else class="items-list">
      <div v-for="item in items" :key="item.id" class="item-row" @click="viewItem(item.id)">
        <div class="item-main">
          <div class="item-title">{{ item.title || 'Untitled' }}</div>
          <div class="item-meta">
            <span v-if="item.source" class="item-source">{{ truncate(item.source, 60) }}</span>
            <span class="item-date">{{ formatDate(item.collected_at) }}</span>
            <span v-if="item.word_count" class="item-words">{{ item.word_count }} {{ t('items.wordCount') }}</span>
          </div>
          <div v-if="item.summary" class="item-summary">{{ truncate(item.summary, 120) }}</div>
        </div>
        <div class="item-side">
          <div v-if="item.tags.length" class="item-tags">
            <span v-for="tag in item.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <button class="delete-btn" @click.stop="removeItem(item.id)">{{ t('common.delete') }}</button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="items.length > 0" class="pagination">
      <button class="page-btn" :disabled="page === 0" @click="prevPage">{{ t('items.previous') }}</button>
      <span class="page-info">{{ page + 1 }}</span>
      <button class="page-btn" :disabled="!hasMore" @click="nextPage">{{ t('items.next') }}</button>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 16px; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.search-box {
  display: flex;
  flex: 1;
  gap: 8px;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  outline: none;
}

@media (prefers-color-scheme: dark) {
  .search-input {
    background: var(--color-surface-dark);
    border-color: var(--color-border-dark);
    color: var(--color-text-primary-dark);
  }
}

.search-input:focus { border-color: var(--color-primary); }

.search-btn {
  padding: 8px 16px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.search-btn:hover { background: var(--color-primary-hover); }

.tag-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.tag-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: 99px;
  background: transparent;
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}

@media (prefers-color-scheme: dark) {
  .tag-btn { border-color: var(--color-border-dark); }
}

.tag-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.tag-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.tag-count { font-size: 10px; opacity: 0.7; }

.loading, .error, .empty {
  padding: 40px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.error { color: #FF3B30; }

.items-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.15s;
}

.item-row:hover {
  background: rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .item-row:hover { background: rgba(255, 255, 255, 0.06); }
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (prefers-color-scheme: dark) {
  .item-title { color: var(--color-text-primary-dark); }
}

.item-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.item-summary {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.item-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 16px;
}

.item-tags {
  display: flex;
  gap: 4px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  white-space: nowrap;
}

@media (prefers-color-scheme: dark) {
  .tag { background: rgba(0, 122, 255, 0.2); }
}

.delete-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid #FF3B30;
  border-radius: var(--radius-sm);
  background: transparent;
  color: #FF3B30;
  cursor: pointer;
  font-family: var(--font-sans);
  opacity: 0;
  transition: opacity 0.15s;
}

.item-row:hover .delete-btn { opacity: 1; }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px 0;
}

.page-btn {
  padding: 6px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
}

@media (prefers-color-scheme: dark) {
  .page-btn {
    border-color: var(--color-border-dark);
    color: var(--color-text-primary-dark);
  }
}

.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn:not(:disabled):hover { border-color: var(--color-primary); color: var(--color-primary); }

.page-info { font-size: 13px; color: var(--color-text-secondary); }
</style>
