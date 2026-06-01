import { get } from './client'
import type { GraphData, GraphStats, Entity, KnowledgeItem } from './types'

export function getGraph(params?: {
  entity_types?: string
  min_relations?: number
  limit?: number
}) {
  return get<GraphData>('/graph', params)
}

export function searchGraph(params: { query: string; limit?: number }) {
  return get<GraphData>('/graph/search', params)
}

export function getGraphStats() {
  return get<GraphStats>('/graph/stats')
}

export function getEntity(entityId: string) {
  return get<Entity>(`/graph/entity/${entityId}`)
}

export function getKnowledgeEntities(knowledgeId: string) {
  return get<Entity[]>(`/knowledge/${knowledgeId}/entities`)
}

export function getKnowledgeRelated(knowledgeId: string, params?: { limit?: number }) {
  return get<KnowledgeItem[]>(`/knowledge/${knowledgeId}/related`, params)
}
