import { get, post, del } from './client'
import type {
  SearchResult,
  SemanticSearchRequest,
  RagRequest,
  RagResponse,
  RagChatRequest,
  RagChatResponse,
  RagConversation,
  RagConversationDetail,
  RagSuggestRequest,
} from './types'

export function search(params: { query: string; limit?: number; content_type?: string }) {
  return get<SearchResult[]>('/search', params)
}

export function semanticSearch(request: SemanticSearchRequest) {
  return post<SearchResult[]>('/search/semantic', request)
}

export function ragQuery(request: RagRequest) {
  return post<RagResponse>('/rag', request)
}

export function ragChat(request: RagChatRequest) {
  return post<RagChatResponse>('/rag/chat', request)
}

export function listConversations() {
  return get<RagConversation[]>('/rag/conversations')
}

export function getConversation(sessionId: string) {
  return get<RagConversationDetail>(`/rag/conversations/${sessionId}`)
}

export function deleteConversation(sessionId: string) {
  return del<{ message: string }>(`/rag/conversations/${sessionId}`)
}

export function deleteAllConversations() {
  return del<{ message: string }>('/rag/conversations')
}

export function ragSuggest(request: RagSuggestRequest) {
  return post<string[]>('/rag/suggest', request)
}
