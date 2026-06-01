<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSettings, updateLlmSettings, updateEmbeddingSettings, testLlm, testEmbedding, runDoctor } from '../api/settings'
import type { Settings, LlmSettings, EmbeddingSettings, TestConnectionResult, DoctorResult } from '../api/types'

const { t } = useI18n()

const settings = ref<Settings | null>(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref<'llm' | 'embedding' | 'doctor'>('llm')

const llmDraft = ref<LlmSettings>({ provider: '', model: '' })
const embeddingDraft = ref<EmbeddingSettings>({ provider: '', model: '' })
const saving = ref(false)

const testingLlm = ref(false)
const llmTestResult = ref<TestConnectionResult | null>(null)
const testingEmbedding = ref(false)
const embeddingTestResult = ref<TestConnectionResult | null>(null)

const doctorLoading = ref(false)
const doctorResult = ref<DoctorResult | null>(null)

onMounted(async () => {
  try {
    settings.value = await getSettings()
    llmDraft.value = { ...settings.value.llm }
    embeddingDraft.value = { ...settings.value.embedding }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function saveLlm() {
  saving.value = true
  try {
    await updateLlmSettings(llmDraft.value)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function saveEmbedding() {
  saving.value = true
  try {
    await updateEmbeddingSettings(embeddingDraft.value)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function doTestLlm() {
  testingLlm.value = true
  llmTestResult.value = null
  try {
    llmTestResult.value = await testLlm(llmDraft.value)
  } catch (e: unknown) {
    llmTestResult.value = { success: false, message: e instanceof Error ? e.message : String(e) }
  } finally {
    testingLlm.value = false
  }
}

async function doTestEmbedding() {
  testingEmbedding.value = true
  embeddingTestResult.value = null
  try {
    embeddingTestResult.value = await testEmbedding(embeddingDraft.value)
  } catch (e: unknown) {
    embeddingTestResult.value = { success: false, message: e instanceof Error ? e.message : String(e) }
  } finally {
    testingEmbedding.value = false
  }
}

async function doDoctor() {
  doctorLoading.value = true
  doctorResult.value = null
  try {
    doctorResult.value = await runDoctor()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : String(e))
  } finally {
    doctorLoading.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1 class="page-title">{{ t('nav.settings') }}</h1>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'llm' }" @click="activeTab = 'llm'">LLM 模型</button>
      <button class="tab" :class="{ active: activeTab === 'embedding' }" @click="activeTab = 'embedding'">Embedding 模型</button>
      <button class="tab" :class="{ active: activeTab === 'doctor' }" @click="activeTab = 'doctor'">系统诊断</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <!-- LLM Settings -->
      <div v-if="activeTab === 'llm'" class="settings-form">
        <div class="form-row">
          <label class="form-label">Provider</label>
          <input v-model="llmDraft.provider" class="form-input" placeholder="dashscope / openai / ollama" />
        </div>
        <div class="form-row">
          <label class="form-label">Model</label>
          <input v-model="llmDraft.model" class="form-input" placeholder="qwen-plus / gpt-4o" />
        </div>
        <div class="form-row">
          <label class="form-label">API Key</label>
          <input v-model="llmDraft.api_key" type="password" class="form-input" placeholder="sk-..." />
        </div>
        <div class="form-row">
          <label class="form-label">API Base URL</label>
          <input v-model="llmDraft.api_base" class="form-input" placeholder="https://..." />
        </div>
        <div class="form-actions">
          <button class="action-btn secondary" :disabled="testingLlm" @click="doTestLlm">{{ testingLlm ? '测试中...' : '测试连接' }}</button>
          <button class="action-btn" :disabled="saving" @click="saveLlm">{{ t('common.save') }}</button>
        </div>
        <div v-if="llmTestResult" class="test-result" :class="{ success: llmTestResult.success, fail: !llmTestResult.success }">
          {{ llmTestResult.message }}
          <span v-if="llmTestResult.latency_ms" class="latency">{{ llmTestResult.latency_ms }}ms</span>
        </div>
      </div>

      <!-- Embedding Settings -->
      <div v-if="activeTab === 'embedding'" class="settings-form">
        <div class="form-row">
          <label class="form-label">Provider</label>
          <input v-model="embeddingDraft.provider" class="form-input" placeholder="dashscope / openai" />
        </div>
        <div class="form-row">
          <label class="form-label">Model</label>
          <input v-model="embeddingDraft.model" class="form-input" placeholder="text-embedding-v3" />
        </div>
        <div class="form-row">
          <label class="form-label">API Key</label>
          <input v-model="embeddingDraft.api_key" type="password" class="form-input" placeholder="sk-..." />
        </div>
        <div class="form-row">
          <label class="form-label">API Base URL</label>
          <input v-model="embeddingDraft.api_base" class="form-input" placeholder="https://..." />
        </div>
        <div class="form-actions">
          <button class="action-btn secondary" :disabled="testingEmbedding" @click="doTestEmbedding">{{ testingEmbedding ? '测试中...' : '测试连接' }}</button>
          <button class="action-btn" :disabled="saving" @click="saveEmbedding">{{ t('common.save') }}</button>
        </div>
        <div v-if="embeddingTestResult" class="test-result" :class="{ success: embeddingTestResult.success, fail: !embeddingTestResult.success }">
          {{ embeddingTestResult.message }}
          <span v-if="embeddingTestResult.latency_ms" class="latency">{{ embeddingTestResult.latency_ms }}ms</span>
        </div>
      </div>

      <!-- Doctor -->
      <div v-if="activeTab === 'doctor'" class="doctor-section">
        <button class="action-btn" :disabled="doctorLoading" @click="doDoctor">{{ doctorLoading ? '诊断中...' : '运行诊断' }}</button>
        <div v-if="doctorResult" class="doctor-results">
          <div v-for="check in doctorResult.checks" :key="check.name" class="doctor-check">
            <span class="doctor-status" :class="check.status">
              {{ check.status === 'ok' ? '✓' : check.status === 'warning' ? '⚠' : '✗' }}
            </span>
            <span class="doctor-name">{{ check.name }}</span>
            <span class="doctor-message">{{ check.message }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 800px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 16px; }

.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--color-border); }
@media (prefers-color-scheme: dark) { .tabs { border-bottom-color: var(--color-border-dark); } }
.tab { padding: 8px 16px; border: none; background: transparent; font-size: 13px; font-family: var(--font-sans); color: var(--color-text-secondary); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }

.loading, .error { padding: 40px; text-align: center; color: var(--color-text-secondary); font-size: 14px; }
.error { color: #FF3B30; }

.settings-form { padding: 20px; background: var(--color-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); }
@media (prefers-color-scheme: dark) { .settings-form { background: var(--color-surface-dark); } }

.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.form-label { font-size: 13px; min-width: 120px; color: var(--color-text-secondary); }
.form-input { flex: 1; padding: 8px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); background: transparent; color: var(--color-text-primary); outline: none; }
@media (prefers-color-scheme: dark) { .form-input { border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }
.form-input:focus { border-color: var(--color-primary); }

.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }
.action-btn { padding: 6px 14px; background: var(--color-primary); color: white; border: none; border-radius: var(--radius-md); font-size: 13px; cursor: pointer; font-family: var(--font-sans); }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-btn.secondary { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-primary); }
@media (prefers-color-scheme: dark) { .action-btn.secondary { border-color: var(--color-border-dark); color: var(--color-text-primary-dark); } }

.test-result { margin-top: 16px; padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; display: flex; align-items: center; justify-content: space-between; }
.test-result.success { background: rgba(52, 199, 89, 0.1); color: #34C759; }
.test-result.fail { background: rgba(255, 59, 48, 0.1); color: #FF3B30; }
.latency { font-size: 11px; opacity: 0.7; }

.doctor-section { }
.doctor-results { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.doctor-check { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: var(--color-surface); border-radius: var(--radius-md); box-shadow: var(--shadow-card); }
@media (prefers-color-scheme: dark) { .doctor-check { background: var(--color-surface-dark); } }
.doctor-status { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; }
.doctor-status.ok { color: #34C759; }
.doctor-status.warning { color: #FF9500; }
.doctor-status.error { color: #FF3B30; }
.doctor-name { font-size: 13px; font-weight: 500; min-width: 150px; }
.doctor-message { font-size: 12px; color: var(--color-text-secondary); flex: 1; }
</style>
