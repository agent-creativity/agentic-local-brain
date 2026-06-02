import { get } from './client'
import { cached } from './cache'
import type { Stats, RagStats, KnowledgeItem } from './types'

const TTL = 30_000

export function getStats() {
  return cached('stats', TTL, () => get<Stats>('/stats'))
}

export function getRecentItems(params?: { limit?: number; content_type?: string }) {
  const key = `recent:${params?.content_type || 'all'}:${params?.limit || 20}`
  return cached(key, TTL, () => get<KnowledgeItem[]>('/recent', params))
}

export function getRagStats() {
  return cached('rag-stats', TTL, () => get<RagStats>('/rag-stats'))
}
