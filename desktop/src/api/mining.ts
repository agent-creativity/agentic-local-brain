import { get, post } from './client'
import type { MiningRequest, MiningStatus, MiningHistoryEntry } from './types'

export function runMining(request?: MiningRequest) {
  return post<{ task_id: string; message: string }>('/mining/run', request)
}

export function getMiningStatus() {
  return get<MiningStatus>('/mining/status')
}

export function getMiningHistory(params?: { limit?: number }) {
  return get<MiningHistoryEntry[]>('/mining/history', params)
}
