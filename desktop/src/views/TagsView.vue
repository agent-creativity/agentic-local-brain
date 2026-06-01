<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { listTags, getTagItems, mergeTags, deleteTag } from '../api/tags'
import type { Tag, KnowledgeItem } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref('')

const selectedTag = ref<string | null>(null)
const tagItems = ref<KnowledgeItem[]>([])
const loadingItems = ref(false)

const mergeMode = ref(false)
const mergeSource = ref<string[]>([])
const mergeTarget = ref('')

const searchQuery = ref('')
const filteredTags = computed(() => {
  if (!searchQuery.value) return tags.value
  const q = searchQuery.value.toLowerCase()
  return tags.value.filter((t) => t.name.toLowerCase().includes(q))
})

onMounted(async () => {
  try {
    tags.value = await listTags()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function selectTag(name: string) {
  if (selectedTag.value === name) {
    selectedTag.value = null
    tagItems.value = []
    return
  }
  selectedTag.value = name
  loadingItems.value = true
  try {
    tagItems.value = await getTagItems(name, { limit: 20 })
  } catch {
    tagItems.value = []
  } finally {
    loadingItems.value = false
  }
}

function toggleMergeSource(name: string) {
  const idx = mergeSource.value.indexOf(name)
  if (idx >= 0) mergeSource.value.splice(idx, 1)
  else mergeSource.value.push(name)
}

async function doMerge() {
  if (mergeSource.value.length === 0 || !mergeTarget.value) return
  try {
    await mergeTags({ source_tags: mergeSource.value, target_tag: mergeTarget.value })
    tags.value = await listTags()
    mergeMode.value = false
    mergeSource.value = []
    mergeTarget.value = ''
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

async function removeTag(name: string) {
  if (!confirm(`${t('common.delete')} "${name}"?`)) return
  try {
    await deleteTag(name)
    tags.value = tags.value.filter((t) => t.name !== name)
    if (selectedTag.value === name) {
      selectedTag.value = null
      tagItems.value = []
    }
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">{{ t('nav.tags') }}</h1>
      <button v-if="!mergeMode" class="action-btn" @click="mergeMode = true">合并标签</button>
      <button v-else class="action-btn cancel" @click="mergeMode = false; mergeSource = []">{{ t('common.cancel') }}</button>
    </div>

    <!-- Search -->
    <input v-model="searchQuery" :placeholder="t('common.search') + '...'" class="search-input" />

    <!-- Merge bar -->
    <div v-if="mergeMode" class="merge-bar">
      <span class="merge-label">选择要合并的标签，然后输入目标标签名：</span>
      <div class="merge-controls">
        <span v-if="mergeSource.length" class="merge-selected">已选 {{ mergeSource.length }} 个</span>
        <input v-model="mergeTarget" placeholder="目标标签名" class="merge-input" />
        <button class="action-btn" :disabled="mergeSource.length === 0 || !mergeTarget" @click="doMerge">合并</button>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <!-- Tag cloud -->
      <div class="tag-cloud">
        <button
          v-for="tag in filteredTags"
          :key="tag.name"
          class="tag-pill"
          :class="{ active: selectedTag === tag.name, 'merge-selected-pill': mergeSource.includes(tag.name) }"
          @click="mergeMode ? toggleMergeSource(tag.name) : selectTag(tag.name)"
        >
          <span class="tag-name">{{ tag.name }}</span>
          <span class="tag-count">{{ tag.count }}</span>
          <button v-if="!mergeMode" class="tag-delete" @click.stop="removeTag(tag.name)">×</button>
        </button>
      </div>

      <!-- Selected tag items -->
      <div v-if="selectedTag && !mergeMode" class="tag-items">
        <h2 class="section-title">{{ selectedTag }}</h2>
        <div v-if="loadingItems" class="loading">{{ t('common.loading') }}</div>
        <div v-else-if="tagItems.length === 0" class="empty">{{ t('items.noItemsFound') }}</div>
        <div v-else class="items-list">
          <button
            v-for="item in tagItems"
            :key="item.id"
            class="item-row"
            @click="router.push(`/items/detail/${item.id}`)"
          >
            <span class="item-title">{{ item.title || 'Untitled' }}</span>
            <span class="item-type">{{ item.content_type }}</span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; }

.action-btn {
  padding: 6px 14px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
}
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-btn.cancel { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-secondary); }

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  outline: none;
  margin-bottom: 16px;
}
@media (prefers-color-scheme: dark) {
  .search-input { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); }
}
.search-input:focus { border-color: var(--color-primary); }

.merge-bar {
  padding: 12px 16px;
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}
@media (prefers-color-scheme: dark) { .merge-bar { background: rgba(0, 122, 255, 0.15); } }
.merge-label { font-size: 13px; display: block; margin-bottom: 8px; }
.merge-controls { display: flex; gap: 8px; align-items: center; }
.merge-selected { font-size: 12px; color: var(--color-primary); font-weight: 600; }
.merge-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  outline: none;
  background: var(--color-surface);
  font-family: var(--font-sans);
}
@media (prefers-color-scheme: dark) { .merge-input { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.tag-cloud { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }

.tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 99px;
  background: var(--color-surface);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  transition: all 0.15s;
}
@media (prefers-color-scheme: dark) {
  .tag-pill { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); }
}
.tag-pill:hover { border-color: var(--color-primary); }
.tag-pill.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.tag-pill.merge-selected-pill { border-color: #FF9500; background: rgba(255, 149, 0, 0.1); }

.tag-count { font-size: 11px; opacity: 0.6; }
.tag-delete {
  font-size: 14px;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0;
  transition: opacity 0.15s;
  font-family: var(--font-sans);
}
.tag-pill:hover .tag-delete { opacity: 0.6; }
.tag-pill:hover .tag-delete:hover { opacity: 1; }

.section-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }

.items-list { display: flex; flex-direction: column; gap: 2px; }
.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  text-align: left;
  width: 100%;
  color: var(--color-text-primary);
}
@media (prefers-color-scheme: dark) { .item-row { color: var(--color-text-primary-dark); } }
.item-row:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .item-row:hover { background: rgba(255, 255, 255, 0.06); } }
.item-title { font-weight: 500; }
.item-type { font-size: 11px; color: var(--color-text-secondary); }
</style>
