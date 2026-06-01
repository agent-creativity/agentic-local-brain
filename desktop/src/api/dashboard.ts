import { get } from './client'
import type { Stats, RagStats, KnowledgeItem } from './types'

export function getStats() {
  return get<Stats>('/stats')
}

export function getRecentItems(params?: { limit?: number; content_type?: string }) {
  return get<KnowledgeItem[]>('/recent', params)
}

export function getRagStats() {
  return get<RagStats>('/rag-stats')
}
