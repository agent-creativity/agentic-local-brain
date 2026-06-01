import { get } from './client'
import type { WikiTree, WikiArticle, WikiEntity, WikiStats, SearchResult } from './types'

export function getWikiTree() {
  return get<WikiTree>('/wiki/tree')
}

export function getCategoryArticles(categoryId: string, params?: { limit?: number; offset?: number }) {
  return get<WikiArticle[]>(`/wiki/categories/${categoryId}/articles`, params)
}

export function getTopicArticles(topicId: string, params?: { limit?: number; offset?: number }) {
  return get<WikiArticle[]>(`/wiki/topics/${topicId}/articles`, params)
}

export function listArticles(params?: { limit?: number; offset?: number; search?: string }) {
  return get<WikiArticle[]>('/wiki/articles', params)
}

export function getArticle(articleId: string) {
  return get<WikiArticle>(`/wiki/articles/${articleId}`)
}

export function listEntities(params?: { limit?: number; offset?: number; type?: string }) {
  return get<WikiEntity[]>('/wiki/entities', params)
}

export function getWikiEntity(entityId: string) {
  return get<WikiEntity>(`/wiki/entities/${entityId}`)
}

export function getWikiStats() {
  return get<WikiStats>('/wiki/stats')
}

export function searchWiki(params: { query: string; limit?: number }) {
  return get<SearchResult[]>('/wiki/search', params)
}
