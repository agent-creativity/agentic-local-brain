<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { listTopics, getTopicDocuments, rebuildTopics, getRebuildStatus } from '../api/topics'
import type { TopicCluster, TopicDocument } from '../api/types'

const { t } = useI18n()
const router = useRouter()

const clusters = ref<TopicCluster[]>([])
const loading = ref(true)
const error = ref('')

const selectedCluster = ref<TopicCluster | null>(null)
const documents = ref<TopicDocument[]>([])
const loadingDocs = ref(false)

const rebuilding = ref(false)
const rebuildMsg = ref('')

onMounted(async () => {
  try {
    clusters.value = await listTopics()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function selectCluster(cluster: TopicCluster) {
  if (selectedCluster.value?.cluster_id === cluster.cluster_id) {
    selectedCluster.value = null
    documents.value = []
    return
  }
  selectedCluster.value = cluster
  loadingDocs.value = true
  try {
    documents.value = await getTopicDocuments(cluster.cluster_id, { limit: 30 })
  } catch {
    documents.value = []
  } finally {
    loadingDocs.value = false
  }
}

async function doRebuild() {
  if (!confirm('重建主题聚类？这可能需要几分钟。')) return
  rebuilding.value = true
  rebuildMsg.value = '正在重建...'
  try {
    await rebuildTopics()
    const poll = setInterval(async () => {
      try {
        const status = await getRebuildStatus()
        rebuildMsg.value = status.message || status.status
        if (status.status === 'completed' || status.status === 'idle') {
          clearInterval(poll)
          rebuilding.value = false
          clusters.value = await listTopics()
        }
      } catch {
        clearInterval(poll)
        rebuilding.value = false
      }
    }, 3000)
  } catch (e: unknown) {
    rebuildMsg.value = e instanceof Error ? e.message : String(e)
    rebuilding.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">{{ t('nav.topics') }}</h1>
      <button class="action-btn" :disabled="rebuilding" @click="doRebuild">{{ rebuilding ? rebuildMsg : '重建聚类' }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="clusters.length === 0" class="empty">{{ t('common.noData') }}</div>
    <template v-else>
      <div class="cluster-grid">
        <button
          v-for="cluster in clusters"
          :key="cluster.cluster_id"
          class="cluster-card"
          :class="{ active: selectedCluster?.cluster_id === cluster.cluster_id }"
          @click="selectCluster(cluster)"
        >
          <div class="cluster-label">{{ cluster.label }}</div>
          <div class="cluster-keywords">
            <span v-for="kw in cluster.keywords.slice(0, 5)" :key="kw" class="keyword">{{ kw }}</span>
          </div>
          <div class="cluster-count">{{ cluster.document_count }} 篇文档</div>
        </button>
      </div>

      <div v-if="selectedCluster" class="docs-section">
        <h2 class="section-title">{{ selectedCluster.label }} — 关联文档</h2>
        <div v-if="loadingDocs" class="loading">{{ t('common.loading') }}</div>
        <div v-else-if="documents.length === 0" class="empty">{{ t('common.noData') }}</div>
        <div v-else class="docs-list">
          <button
            v-for="doc in documents"
            :key="doc.id"
            class="doc-row"
            @click="router.push(`/items/detail/${doc.id}`)"
          >
            <span class="doc-title">{{ doc.title }}</span>
            <span class="doc-meta">
              <span class="doc-type">{{ doc.content_type }}</span>
              <span class="doc-score">{{ Math.round(doc.score * 100) }}%</span>
            </span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; }

.action-btn { padding: 6px 14px; background: var(--color-primary); color: white; border: none; border-radius: var(--radius-md); font-size: 13px; cursor: pointer; font-family: var(--font-sans); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.cluster-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 24px; }

.cluster-card {
  padding: 16px;
  background: var(--color-surface);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-family: var(--font-sans);
  width: 100%;
}
@media (prefers-color-scheme: dark) { .cluster-card { background: var(--color-surface-dark); } }
.cluster-card:hover { border-color: var(--color-primary); box-shadow: var(--shadow-card-hover); }
.cluster-card.active { border-color: var(--color-primary); }

.cluster-label { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.cluster-keywords { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.keyword { font-size: 11px; padding: 2px 8px; background: var(--color-primary-light); color: var(--color-primary); border-radius: 99px; }
@media (prefers-color-scheme: dark) { .keyword { background: rgba(0, 122, 255, 0.2); } }
.cluster-count { font-size: 12px; color: var(--color-text-secondary); }

.section-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }

.docs-list { display: flex; flex-direction: column; gap: 2px; }
.doc-row {
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
@media (prefers-color-scheme: dark) { .doc-row { color: var(--color-text-primary-dark); } }
.doc-row:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .doc-row:hover { background: rgba(255, 255, 255, 0.06); } }
.doc-title { font-weight: 500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { display: flex; gap: 8px; flex-shrink: 0; margin-left: 12px; }
.doc-type { font-size: 11px; color: var(--color-text-secondary); }
.doc-score { font-size: 11px; color: var(--color-primary); font-weight: 600; }
</style>
