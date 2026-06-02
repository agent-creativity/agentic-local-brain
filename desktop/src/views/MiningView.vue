<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { runMining, getMiningStatus, getMiningHistory } from '../api/mining'
import type { MiningStatus, MiningHistoryEntry } from '../api/types'

const { t } = useI18n()

const status = ref<MiningStatus | null>(null)
const history = ref<MiningHistoryEntry[]>([])
const loading = ref(true)
const error = ref('')
const running = ref(false)
const mode = ref<'incremental' | 'full'>('incremental')

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await fetchAll()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function fetchAll() {
  loading.value = true
  try {
    const [s, h] = await Promise.all([
      getMiningStatus(),
      getMiningHistory({ limit: 20 }),
    ])
    status.value = s
    history.value = Array.isArray(h) ? h : (h as any).records || []
    running.value = s.running
    if (running.value) startPolling()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function startMining() {
  if (running.value) return
  const confirmFull = mode.value === 'full'
    ? confirm('全量重建将清除所有挖掘数据，确认继续？')
    : true
  if (!confirmFull) return

  try {
    await runMining({
      pipeline: undefined,
      content_type: undefined,
    })
    running.value = true
    startPolling()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    try {
      const s = await getMiningStatus()
      status.value = s
      running.value = s.running
      if (!s.running) {
        if (pollTimer) clearInterval(pollTimer)
        pollTimer = null
        const h = await getMiningHistory({ limit: 20 })
        history.value = Array.isArray(h) ? h : (h as any).records || []
      }
    } catch {
      // ignore poll errors
    }
  }, 3000)
}

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('nav.mining') }}</h1>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <!-- Status -->
      <div class="status-card" :class="{ 'status-running': running }">
        <div class="status-header">
          <span class="status-label">{{ running ? '运行中' : '空闲' }}</span>
          <span v-if="status?.current_step" class="status-step">{{ status.current_step }}</span>
        </div>
        <div v-if="status?.progress !== undefined && running" class="progress-bar">
          <div class="progress-fill" :style="{ width: (status.progress || 0) + '%' }"></div>
        </div>
      </div>

      <!-- Actions -->
      <div class="actions">
        <select v-model="mode" class="mode-select">
          <option value="incremental">增量挖掘</option>
          <option value="full">全量重建</option>
        </select>
        <button class="run-btn" :disabled="running" @click="startMining">
          {{ running ? '运行中...' : '开始挖掘' }}
        </button>
      </div>

      <!-- History -->
      <h2 class="section-title">历史记录</h2>
      <div v-if="history.length === 0" class="empty">{{ t('common.noData') }}</div>
      <div v-else class="history-list">
        <div v-for="entry in history" :key="entry.id" class="history-item">
          <div class="history-main">
            <span class="history-status" :class="entry.status">{{ entry.status }}</span>
            <span class="history-pipeline">{{ entry.pipeline?.join(' → ') || '-' }}</span>
          </div>
          <div class="history-meta">
            <span>{{ formatDate(entry.started_at) }}</span>
            <span v-if="entry.items_processed">{{ entry.items_processed }} 条</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 900px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 16px; }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.status-card {
  padding: 20px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: 16px;
}
@media (prefers-color-scheme: dark) { .status-card { background: var(--color-surface-dark); } }

.status-running { border-left: 3px solid var(--color-primary); }

.status-header { display: flex; align-items: center; gap: 12px; }
.status-label { font-size: 14px; font-weight: 600; }
.status-step { font-size: 12px; color: var(--color-text-secondary); }

.progress-bar {
  margin-top: 12px;
  height: 4px;
  background: rgba(0,0,0,0.1);
  border-radius: 2px;
  overflow: hidden;
}
@media (prefers-color-scheme: dark) { .progress-bar { background: rgba(255,255,255,0.1); } }

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s;
}

.actions {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.mode-select {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
}
@media (prefers-color-scheme: dark) {
  .mode-select { background: var(--color-surface-dark); border-color: var(--color-border-dark); color: var(--color-text-primary-dark); }
}

.run-btn {
  padding: 8px 20px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
}
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.run-btn:not(:disabled):hover { background: var(--color-primary-hover); }

.section-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }

.history-list { display: flex; flex-direction: column; gap: 2px; }

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  transition: background 0.15s;
}
.history-item:hover { background: rgba(0,0,0,0.04); }
@media (prefers-color-scheme: dark) { .history-item:hover { background: rgba(255,255,255,0.06); } }

.history-main { display: flex; align-items: center; gap: 10px; }
.history-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.history-status.completed { background: #E8F5E9; color: #2E7D32; }
.history-status.failed { background: #FFEBEE; color: #C62828; }
.history-status.running { background: #E3F2FD; color: #1565C0; }
@media (prefers-color-scheme: dark) {
  .history-status.completed { background: rgba(46,125,50,0.2); }
  .history-status.failed { background: rgba(198,40,40,0.2); }
  .history-status.running { background: rgba(21,101,192,0.2); }
}

.history-pipeline { font-size: 13px; }
.history-meta { display: flex; gap: 12px; font-size: 11px; color: var(--color-text-secondary); }
</style>
