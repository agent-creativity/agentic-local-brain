export interface KnowledgeItem {
  id: string
  title: string | null
  content_type: string | null
  source: string | null
  collected_at: string | null
  summary: string | null
  word_count: number | null
  file_path: string | null
  tags: string[]
  user_notes: string | null
  content?: string
  chunks?: Chunk[]
}

export interface Chunk {
  id: string
  knowledge_id: string
  chunk_index: number
  content: string
  token_count?: number
}

export interface ItemUpdate {
  title?: string
  summary?: string
  tags?: string[]
  user_notes?: string
}

export interface ItemPreview {
  content: string
  file_path: string
}

export interface Stats {
  total_items: number
  items_by_type: Record<string, number>
  total_tags: number
  total_chunks: number
  version: string
}

export interface RagStats {
  total_queries: number
  total_conversations: number
  avg_turns_per_session: number
  recent_queries: Array<{ query: string; timestamp: string }>
  queries_today: number
  queries_this_week: number
}

export interface Tag {
  name: string
  count: number
}

export interface TagMergeRequest {
  source_tags: string[]
  target_tag: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphNode {
  id: number
  name: string
  display_name: string
  type: string
  description?: string
  mention_count?: number
}

export interface GraphEdge {
  id: number
  source_entity_id: number
  target_entity_id: number
  relation_type: string
  weight?: number
}

export interface GraphStats {
  total_entities: number
  total_relations: number
  total_doc_relations?: number
  total_mentions?: number
  type_distribution?: Array<{ type: string; count: number }>
  relation_distribution?: Array<{ relation_type: string; count: number }>
  top_entities?: Array<{ id: number; name: string; display_name: string; type: string; mention_count: number }>
}

export interface Entity {
  id: string
  name: string
  type: string
  description?: string
  properties?: Record<string, unknown>
  relations?: EntityRelation[]
}

export interface EntityRelation {
  target_id: string
  target_name: string
  target_type: string
  relation: string
}

export interface TopicCluster {
  cluster_id: number
  label: string
  keywords: string[]
  document_count: number
  representative_docs?: string[]
}

export interface TopicDocument {
  id: string
  title: string
  content_type: string
  score: number
}

export interface TopicTimeline {
  date: string
  clusters: Array<{
    cluster_id: number
    label: string
    count: number
  }>
}

export interface TopicTrend {
  cluster_id: number
  label: string
  data: Array<{ date: string; count: number }>
}

export interface WikiTree {
  categories: WikiCategory[]
  topics: WikiTopic[]
}

export interface WikiCategory {
  id: string
  name: string
  article_count: number
  children?: WikiCategory[]
}

export interface WikiTopic {
  id: string
  name: string
  article_count: number
}

export interface WikiArticle {
  id: string
  title: string
  content: string
  category_id?: string
  topic_id?: string
  entities?: WikiEntityRef[]
  created_at?: string
  updated_at?: string
}

export interface WikiEntityRef {
  id: string
  name: string
  type: string
}

export interface WikiEntity {
  id: string
  name: string
  type: string
  description?: string
  articles?: Array<{ id: string; title: string }>
}

export interface WikiStats {
  total_articles: number
  total_categories: number
  total_entities: number
}

export interface SearchResult {
  id: string
  title: string
  content_type: string
  source?: string
  summary?: string
  score?: number
  highlights?: string[]
  tags?: string[]
}

export interface SemanticSearchRequest {
  query: string
  limit?: number
  content_type?: string
}

export interface RagRequest {
  query: string
  limit?: number
  content_type?: string
}

export interface RagResponse {
  answer: string
  sources: RagSource[]
  query: string
}

export interface RagChatRequest {
  query: string
  session_id?: string
  limit?: number
}

export interface RagChatResponse {
  answer: string
  sources: RagSource[]
  session_id: string
  turn_number: number
}

export interface RagSource {
  id: string
  title: string
  content_type?: string
  chunk_content?: string
  score?: number
}

export interface RagConversation {
  session_id: string
  title?: string
  created_at: string
  updated_at: string
  turn_count: number
}

export interface RagConversationDetail {
  session_id: string
  title?: string
  created_at: string
  turns: RagTurn[]
}

export interface RagTurn {
  turn_number: number
  query: string
  answer: string
  sources: RagSource[]
  created_at: string
}

export interface RagSuggestRequest {
  query: string
  limit?: number
}

export interface Recommendation {
  id: string
  title: string
  content_type: string
  source?: string
  score: number
  reason?: string
}

export interface ReadingHistoryEntry {
  id: string
  knowledge_id: string
  action_type: string
  created_at: string
  query?: string
}

export interface BackupInfo {
  id: string
  filename: string
  created_at: string
  size?: number
  type?: string
  location?: string
}

export interface BackupConfig {
  enabled: boolean
  interval_hours?: number
  cloud_type?: string
  cloud_config?: Record<string, string>
}

export interface BackupStatus {
  task_id: string
  status: string
  progress?: number
  message?: string
}

export interface Settings {
  llm: LlmSettings
  embedding: EmbeddingSettings
}

export interface LlmSettings {
  provider: string
  model: string
  api_key?: string
  api_base?: string
  [key: string]: unknown
}

export interface EmbeddingSettings {
  provider: string
  model: string
  api_key?: string
  api_base?: string
  [key: string]: unknown
}

export interface DoctorResult {
  checks: Array<{
    name: string
    status: 'ok' | 'warning' | 'error'
    message: string
  }>
}

export interface TestConnectionResult {
  success: boolean
  message: string
  latency_ms?: number
}

export interface MiningRequest {
  pipeline?: string[]
  content_type?: string
}

export interface MiningStatus {
  running: boolean
  current_step?: string
  progress?: number
  started_at?: string
}

export interface MiningHistoryEntry {
  id: string
  pipeline: string[]
  status: string
  started_at: string
  completed_at?: string
  items_processed?: number
}
