import { get, put, post } from './client'
import type {
  Settings,
  LlmSettings,
  EmbeddingSettings,
  DoctorResult,
  TestConnectionResult,
  BackupConfig,
} from './types'

export function getSettings() {
  return get<Settings>('/settings')
}

export function updateLlmSettings(settings: LlmSettings) {
  return put<{ message: string }>('/settings/llm', settings)
}

export function updateEmbeddingSettings(settings: EmbeddingSettings) {
  return put<{ message: string }>('/settings/embedding', settings)
}

export function testLlm(settings?: LlmSettings) {
  return post<TestConnectionResult>('/settings/test-llm', settings)
}

export function testEmbedding(settings?: EmbeddingSettings) {
  return post<TestConnectionResult>('/settings/test-embedding', settings)
}

export function runDoctor() {
  return get<DoctorResult>('/settings/doctor')
}

export function getBackupSettings() {
  return get<BackupConfig>('/settings/backup')
}

export function updateBackupSettings(config: BackupConfig) {
  return put<{ message: string }>('/settings/backup', config)
}
