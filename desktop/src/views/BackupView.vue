<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { listBackups, createBackup, deleteBackup, getBackupConfig, updateBackupConfig, testBackupConfig } from '../api/backup'
import type { BackupInfo, BackupConfig } from '../api/types'

const { t } = useI18n()

const backups = ref<BackupInfo[]>([])
const config = ref<BackupConfig | null>(null)
const loading = ref(true)
const error = ref('')
const creating = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const showConfig = ref(false)

onMounted(async () => {
  try {
    const [bl, bc] = await Promise.all([listBackups(), getBackupConfig()])
    backups.value = bl
    config.value = bc
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function doCreate() {
  creating.value = true
  try {
    await createBackup()
    backups.value = await listBackups()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  } finally {
    creating.value = false
  }
}

async function doDelete(id: string) {
  if (!confirm(`${t('common.delete')}?`)) return
  try {
    await deleteBackup(id)
    backups.value = backups.value.filter((b) => b.id !== id)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

async function saveConfig() {
  if (!config.value) return
  try {
    await updateBackupConfig(config.value)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  }
}

async function doTest() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testBackupConfig()
  } catch (e: unknown) {
    testResult.value = { success: false, message: e instanceof Error ? e.message : String(e) }
  } finally {
    testing.value = false
  }
}

function formatSize(bytes?: number) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">{{ t('nav.backup') }}</h1>
      <div class="header-actions">
        <button class="action-btn secondary" @click="showConfig = !showConfig">{{ showConfig ? t('common.close') : '云存储配置' }}</button>
        <button class="action-btn" :disabled="creating" @click="doCreate">{{ creating ? t('common.loading') : '创建备份' }}</button>
      </div>
    </div>

    <!-- Cloud config -->
    <div v-if="showConfig && config" class="config-section">
      <div class="config-row">
        <label class="config-label">自动备份</label>
        <input type="checkbox" v-model="config.enabled" />
      </div>
      <div v-if="config.enabled" class="config-row">
        <label class="config-label">间隔(小时)</label>
        <input type="number" v-model="config.interval_hours" class="config-input short" />
      </div>
      <div class="config-row">
        <label class="config-label">云存储类型</label>
        <select v-model="config.cloud_type" class="config-input">
          <option value="">本地</option>
          <option value="oss">阿里云 OSS</option>
          <option value="s3">AWS S3</option>
        </select>
      </div>
      <div class="config-actions">
        <button class="action-btn secondary" :disabled="testing" @click="doTest">{{ testing ? '测试中...' : '测试连接' }}</button>
        <button class="action-btn" @click="saveConfig">{{ t('common.save') }}</button>
      </div>
      <div v-if="testResult" class="test-result" :class="{ success: testResult.success, fail: !testResult.success }">
        {{ testResult.message }}
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <div v-if="backups.length === 0" class="empty">{{ t('common.noData') }}</div>
      <div v-else class="backup-list">
        <div v-for="backup in backups" :key="backup.id" class="backup-row">
          <div class="backup-main">
            <div class="backup-name">{{ backup.filename }}</div>
            <div class="backup-meta">
              <span>{{ formatDate(backup.created_at) }}</span>
              <span>{{ formatSize(backup.size) }}</span>
              <span v-if="backup.location" class="backup-location">{{ backup.location }}</span>
            </div>
          </div>
          <button class="delete-btn" @click="doDelete(backup.id)">{{ t('common.delete') }}</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; }
.header-actions { display: flex; gap: 8px; }

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
.action-btn.secondary { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-primary); }
@media (prefers-color-scheme: dark) { .action-btn.secondary { border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }

.config-section {
  padding: 16px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: 20px;
}
@media (prefers-color-scheme: dark) { .config-section { background: var(--color-surface-dark); } }

.config-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.config-label { font-size: 13px; min-width: 100px; color: var(--color-text-secondary); }
.config-input {
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-family: var(--font-sans);
  background: transparent;
  color: var(--color-text-primary);
  outline: none;
}
@media (prefers-color-scheme: dark) { .config-input { border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }
.config-input.short { width: 80px; }
.config-input:focus { border-color: var(--color-primary); }
.config-actions { display: flex; gap: 8px; margin-top: 12px; }

.test-result { margin-top: 12px; padding: 8px 12px; border-radius: var(--radius-md); font-size: 13px; }
.test-result.success { background: rgba(52, 199, 89, 0.1); color: #34C759; }
.test-result.fail { background: rgba(255, 59, 48, 0.1); color: #FF3B30; }

.loading, .error, .empty { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.backup-list { display: flex; flex-direction: column; gap: 2px; }
.backup-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: var(--radius-md);
  transition: background 0.15s;
}
.backup-row:hover { background: rgba(0, 0, 0, 0.04); }
@media (prefers-color-scheme: dark) { .backup-row:hover { background: rgba(255, 255, 255, 0.06); } }

.backup-main { flex: 1; }
.backup-name { font-size: 14px; font-weight: 500; margin-bottom: 4px; }
.backup-meta { display: flex; gap: 12px; font-size: 11px; color: var(--color-text-secondary); }
.backup-location { padding: 1px 6px; background: var(--color-primary-light); color: var(--color-primary); border-radius: var(--radius-sm); }
@media (prefers-color-scheme: dark) { .backup-location { background: rgba(0, 122, 255, 0.2); } }

.delete-btn {
  font-size: 11px;
  padding: 4px 10px;
  border: 1px solid #FF3B30;
  border-radius: var(--radius-sm);
  background: transparent;
  color: #FF3B30;
  cursor: pointer;
  font-family: var(--font-sans);
  opacity: 0;
  transition: opacity 0.15s;
}
.backup-row:hover .delete-btn { opacity: 1; }
</style>
