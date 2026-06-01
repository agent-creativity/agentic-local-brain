<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getRecommendations, getReadingHistory } from '../api/recommendations'
import type { Recommendation, ReadingHistoryEntry } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const recommendations = ref<Recommendation[]>([])
const history = ref<ReadingHistoryEntry[]>([])
const loading = ref(true)
const error = ref('')
const activeTab = ref<'recommendations' | 'history'>('recommendations')

onMounted(async () => {
  try {
    const [recs, hist] = await Promise.all([
      getRecommendations({ limit: 20 }),
      getReadingHistory({ limit: 30 }),
    ])
    recommendations.value = recs
    history.value = hist
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('nav.recommendations') }}</h1>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'recommendations' }" @click="activeTab = 'recommendations'">推荐内容</button>
      <button class="tab" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">阅读历史</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <!-- Recommendations -->
      <div v-if="activeTab === 'recommendations'" class="list">
        <div v-if="recommendations.length === 0" class="empty">{{ t('common.noData') }}</div>
        <button
          v-for="rec in recommendations"
          :key="rec.id"
          class="rec-card"
          @click="router.push(`/items/detail/${rec.id}`)"
        >
          <div class="rec-main">
            <div class="rec-title">{{ rec.title }}</div>
            <div class="rec-meta">
              <span class="rec-type">{{ rec.content_type }}</span>
              <span v-if="rec.reason" class="rec-reason">{{ rec.reason }}</span>
            </div>
          </div>
          <div class="rec-score">{{ Math.round(rec.score * 100) }}%</div>
        </button>
      </div>

      <!-- Reading history -->
      <div v-if="activeTab === 'history'" class="list">
        <div v-if="history.length === 0" class="empty">{{ t('common.noData') }}</div>
        <button
          v-for="entry in history"
          :key="entry.id"
          class="history-row"
          @click="router.push(`/items/detail/${entry.knowledge_id}`)"
        >
          <span class="history-action">{{ entry.action_type }}</span>
          <span v-if="entry.query" class="history-query">{{ entry.query }}</span>
          <span class="history-date">{{ formatDate(entry.created_at) }}</span>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 16px; }

.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--color-border); }
@media (prefers-color-scheme: dark) { .tabs { border-bottom-color: var(--color-border-dark); } }
.tab {
  padding: 8px 16px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.list { display: flex; flex-direction: column; gap: 2px; }

.rec-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  text-align: left;
  width: 100%;
  transition: background 0.15s;
}
.rec-card:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .rec-card:hover { background: rgba(255, 255, 255, 0.06); } }

.rec-main { flex: 1; min-width: 0; }
.rec-title { font-size: 14px; font-weight: 500; color: var(--color-text-primary); margin-bottom: 4px; }
@media (prefers-color-scheme: dark) { .rec-title { color: var(--color-text-primary-dark); } }
.rec-meta { display: flex; gap: 12px; font-size: 11px; color: var(--color-text-secondary); }
.rec-type { padding: 1px 6px; background: var(--color-primary-light); color: var(--color-primary); border-radius: var(--radius-sm); }
@media (prefers-color-scheme: dark) { .rec-type { background: rgba(0, 122, 255, 0.2); } }
.rec-score { font-size: 14px; font-weight: 600; color: var(--color-primary); flex-shrink: 0; margin-left: 16px; }

.history-row {
  display: flex;
  align-items: center;
  gap: 12px;
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
@media (prefers-color-scheme: dark) { .history-row { color: var(--color-text-primary-dark); } }
.history-row:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .history-row:hover { background: rgba(255, 255, 255, 0.06); } }
.history-action { font-size: 11px; padding: 2px 6px; background: rgba(0, 0, 0, 0.05); border-radius: var(--radius-sm); flex-shrink: 0; }
@media (prefers-color-scheme: dark) { .history-action { background: rgba(255, 255, 255, 0.1); } }
.history-query { flex: 1; color: var(--color-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-date { font-size: 11px; color: var(--color-text-secondary); flex-shrink: 0; }
</style>
