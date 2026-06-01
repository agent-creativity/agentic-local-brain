import { get } from './client'
import type { Recommendation, ReadingHistoryEntry } from './types'

export function getRecommendations(params?: { limit?: number }) {
  return get<Recommendation[]>('/recommendations', params)
}

export function getReadingHistory(params?: { limit?: number; offset?: number }) {
  return get<ReadingHistoryEntry[]>('/reading-history', params)
}
