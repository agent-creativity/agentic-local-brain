<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getRecentItems } from '../api/dashboard'
import type { KnowledgeItem } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const items = ref<KnowledgeItem[]>([])
const loading = ref(true)
const error = ref('')

interface TimelineGroup {
  date: string
  items: KnowledgeItem[]
}

const groups = ref<TimelineGroup[]>([])

onMounted(async () => {
  try {
    items.value = await getRecentItems({ limit: 100 })
    const map = new Map<string, KnowledgeItem[]>()
    for (const item of items.value) {
      const date = item.collected_at ? new Date(item.collected_at).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }) : '未知日期'
      if (!map.has(date)) map.set(date, [])
      map.get(date)!.push(item)
    }
    groups.value = Array.from(map.entries()).map(([date, items]) => ({ date, items }))
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

function formatTime(dateStr: string | null) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const typeIcons: Record<string, string> = { note: '📝', bookmark: '🔖', webpage: '🌐', paper: '📄', email: '✉️', file: '📁' }
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('nav.timeline') }}</h1>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="groups.length === 0" class="empty">{{ t('common.noData') }}</div>
    <div v-else class="timeline">
      <div v-for="group in groups" :key="group.date" class="timeline-group">
        <div class="timeline-date">{{ group.date }}</div>
        <div class="timeline-items">
          <button
            v-for="item in group.items"
            :key="item.id"
            class="timeline-item"
            @click="router.push(`/items/detail/${item.id}`)"
          >
            <div class="timeline-dot">{{ typeIcons[item.content_type || ''] || '📄' }}</div>
            <div class="timeline-content">
              <div class="timeline-item-title">{{ item.title || 'Untitled' }}</div>
              <div class="timeline-item-meta">
                <span>{{ item.content_type }}</span>
                <span>{{ formatTime(item.collected_at) }}</span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 800px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.timeline { position: relative; padding-left: 24px; }
.timeline::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}
@media (prefers-color-scheme: dark) { .timeline::before { background: var(--color-border-dark); } }

.timeline-group { margin-bottom: 24px; }
.timeline-date {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  position: relative;
}
.timeline-date::before {
  content: '';
  position: absolute;
  left: -19px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
}

.timeline-items { display: flex; flex-direction: column; gap: 4px; }
.timeline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  text-align: left;
  width: 100%;
  color: var(--color-text-primary);
  transition: background 0.15s;
}
@media (prefers-color-scheme: dark) { .timeline-item { color: var(--color-text-primary-dark); } }
.timeline-item:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .timeline-item:hover { background: rgba(255, 255, 255, 0.06); } }

.timeline-dot { font-size: 16px; flex-shrink: 0; }
.timeline-content { flex: 1; min-width: 0; }
.timeline-item-title { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.timeline-item-meta { display: flex; gap: 8px; font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }
</style>
