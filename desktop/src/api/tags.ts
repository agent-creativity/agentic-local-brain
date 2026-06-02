import { get, post, del } from './client'
import { cached, invalidate } from './cache'
import type { Tag, KnowledgeItem, TagMergeRequest } from './types'

export function listTags() {
  return cached('tags', 30_000, () => get<Tag[]>('/tags'))
}

export function getTagItems(tagName: string, params?: { limit?: number; offset?: number }) {
  return get<KnowledgeItem[]>(`/tags/${encodeURIComponent(tagName)}/items`, params)
}

export function mergeTags(request: TagMergeRequest) {
  return post<{ message: string }>('/tags/merge', request).then((r) => {
    invalidate('tags')
    return r
  })
}

export function deleteTag(tagName: string) {
  return del<{ message: string }>(`/tags/${encodeURIComponent(tagName)}`).then((r) => {
    invalidate('tags')
    return r
  })
}
