<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getStats, getRecentItems, getRagStats } from '../api/dashboard'
import type { Stats, RagStats, KnowledgeItem } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const stats = ref<Stats | null>(null)
const ragStats = ref<RagStats | null>(null)
const recentItems = ref<KnowledgeItem[]>([])
const loading = ref(true)
const error = ref('')

const typeCards = computed(() => {
  if (!stats.value) return []
  const types = [
    { key: 'note', icon: '📝', route: '/items/note' },
    { key: 'bookmark', icon: '🔖', route: '/items/bookmark' },
    { key: 'webpage', icon: '🌐', route: '/items/webpage' },
    { key: 'paper', icon: '📄', route: '/items/paper' },
    { key: 'email', icon: '✉️', route: '/items/email' },
    { key: 'file', icon: '📁', route: '/items/file' },
  ]
  return types.map((t) => ({
    ...t,
    count: stats.value!.items_by_type[t.key] || 0,
  }))
})

onMounted(async () => {
  try {
    const [s, r, ri] = await Promise.all([
      getStats(),
      getRagStats(),
      getRecentItems({ limit: 10 }),
    ])
    stats.value = s
    ragStats.value = r
    recentItems.value = ri
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

function formatDate(dateStr: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('dashboard.title') }}</h1>
    <p class="page-subtitle">{{ t('dashboard.subtitle') }}</p>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <!-- Stats overview -->
      <div class="stats-row">
        <div class="stat-card stat-card--primary">
          <div class="stat-label">{{ t('dashboard.totalItems') }}</div>
          <div class="stat-value">{{ stats?.total_items ?? 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('dashboard.totalTags') }}</div>
          <div class="stat-value">{{ stats?.total_tags ?? 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">RAG</div>
          <div class="stat-value">{{ ragStats?.total_queries ?? 0 }}</div>
          <div class="stat-sub">{{ ragStats?.total_conversations ?? 0 }} {{ t('dashboard.sessions') }}</div>
        </div>
      </div>

      <!-- Type cards -->
      <h2 class="section-title">{{ t('items.filterByType') }}</h2>
      <div class="type-grid">
        <button
          v-for="tc in typeCards"
          :key="tc.key"
          class="type-card"
          @click="navigateTo(tc.route)"
        >
          <span class="type-icon">{{ tc.icon }}</span>
          <span class="type-label">{{ t(`dashboard.${tc.key}s`) }}</span>
          <span class="type-count">{{ tc.count }}</span>
        </button>
      </div>

      <!-- Recent items -->
      <h2 class="section-title">{{ t('dashboard.recentItems') }}</h2>
      <div class="recent-list">
        <button
          v-for="item in recentItems"
          :key="item.id"
          class="recent-item"
          @click="navigateTo(`/items/detail/${item.id}`)"
        >
          <div class="recent-item-main">
            <span class="recent-item-title">{{ item.title || 'Untitled' }}</span>
            <span class="recent-item-meta">
              {{ item.content_type }} · {{ formatDate(item.collected_at) }}
            </span>
          </div>
          <div v-if="item.tags.length" class="recent-item-tags">
            <span v-for="tag in item.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </button>
        <div v-if="recentItems.length === 0" class="empty">{{ t('items.noItemsFound') }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.loading, .error, .empty {
  padding: 40px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.error { color: #FF3B30; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

@media (prefers-color-scheme: dark) {
  .stat-card {
    background: var(--color-surface-dark);
  }
}

.stat-card--primary {
  background: var(--color-primary);
  color: white;
}

.stat-card--primary .stat-label {
  color: rgba(255, 255, 255, 0.8);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-sub {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}

.type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 8px;
  background: var(--color-surface);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-sans);
}

@media (prefers-color-scheme: dark) {
  .type-card {
    background: var(--color-surface-dark);
  }
}

.type-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card-hover);
}

.type-icon { font-size: 24px; }
.type-label { font-size: 12px; color: var(--color-text-secondary); }
.type-count { font-size: 18px; font-weight: 700; }

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
  text-align: left;
  font-family: var(--font-sans);
  width: 100%;
}

.recent-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .recent-item:hover {
    background: rgba(255, 255, 255, 0.06);
  }
}

.recent-item-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.recent-item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (prefers-color-scheme: dark) {
  .recent-item-title {
    color: var(--color-text-primary-dark);
  }
}

.recent-item-meta {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.recent-item-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
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
  .tag {
    background: rgba(0, 122, 255, 0.2);
  }
}
</style>
