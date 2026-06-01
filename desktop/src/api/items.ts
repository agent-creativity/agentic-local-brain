import { get, put, del } from './client'
import type { KnowledgeItem, ItemUpdate, ItemPreview } from './types'

export function listItems(params?: {
  limit?: number
  offset?: number
  content_type?: string
  tag?: string
  search?: string
  sort_by?: string
  sort_order?: string
}) {
  return get<KnowledgeItem[]>('/items', params)
}

export function getItem(id: string) {
  return get<KnowledgeItem>(`/items/${id}`)
}

export function updateItem(id: string, update: ItemUpdate) {
  return put<KnowledgeItem>(`/items/${id}`, update)
}

export function previewItem(id: string) {
  return get<ItemPreview>(`/items/${id}/preview`)
}

export function deleteItem(id: string, deleteFile = false) {
  return del<{ message: string }>(`/items/${id}?delete_file=${deleteFile}`)
}
