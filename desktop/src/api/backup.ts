import { get, post, del } from './client'
import type { BackupInfo, BackupConfig, BackupStatus } from './types'

export function createBackup(params?: { type?: string }) {
  return post<{ task_id: string; message: string }>('/backup/create', params)
}

export function listBackups() {
  return get<BackupInfo[]>('/backup/list')
}

export function getBackupTaskStatus(taskId: string) {
  return get<BackupStatus>(`/backup/status/${taskId}`)
}

export function getBackupStatus() {
  return get<BackupStatus>('/backup/status')
}

export function deleteBackup(backupId: string) {
  return del<{ message: string }>(`/backup/${backupId}`)
}

export function getBackupConfig() {
  return get<BackupConfig>('/backup/config')
}

export function updateBackupConfig(config: BackupConfig) {
  return post<{ message: string }>('/backup/config', config)
}

export function testBackupConfig() {
  return post<{ success: boolean; message: string }>('/backup/config/test')
}
