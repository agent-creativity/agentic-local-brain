import { get, post } from './client'
import type { TopicCluster, TopicDocument, TopicTimeline, TopicTrend } from './types'

export function listTopics() {
  return get<TopicCluster[]>('/topics')
}

export function getTopicDocuments(clusterId: number, params?: { limit?: number; offset?: number }) {
  return get<TopicDocument[]>(`/topics/${clusterId}/documents`, params)
}

export function getTopicTimeline(params?: { days?: number }) {
  return get<TopicTimeline[]>('/topics/timeline', params)
}

export function getTopicTrend(params?: { days?: number; cluster_ids?: string }) {
  return get<TopicTrend[]>('/topics/trend', params)
}

export function rebuildTopics() {
  return post<{ task_id: string; message: string }>('/topics/rebuild')
}

export function getRebuildStatus() {
  return get<{ status: string; progress?: number; message?: string }>('/topics/rebuild/status')
}
