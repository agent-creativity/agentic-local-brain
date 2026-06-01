export const mockTagsList = [
  { name: 'machine-learning', count: 15 },
  { name: 'javascript', count: 12 },
  { name: 'python', count: 10 },
  { name: 'database', count: 7 },
  { name: 'testing', count: 5 },
]

export const mockTagItems = [
  { id: 'ti-1', title: 'ML Basics', content_type: 'note', source: '', collected_at: '2026-05-01T10:00:00', word_count: 200, summary: '', tags: ['machine-learning'], user_notes: '' },
  { id: 'ti-2', title: 'Deep Learning', content_type: 'paper', source: '', collected_at: '2026-05-02T10:00:00', word_count: 500, summary: '', tags: ['machine-learning'], user_notes: '' },
]

export const mockRecommendations = [
  { id: 'rec-1', title: 'Recommended Article 1', content_type: 'webpage', score: 0.95, reason: 'Similar to your recent reads' },
  { id: 'rec-2', title: 'Recommended Article 2', content_type: 'paper', score: 0.87, reason: 'Trending in your topics' },
]

export const mockReadingHistory = [
  { id: 'rh-1', knowledge_id: 'item-1', action_type: 'view', query: '', created_at: '2026-05-30T14:00:00' },
  { id: 'rh-2', knowledge_id: 'item-2', action_type: 'search', query: 'machine learning', created_at: '2026-05-30T13:00:00' },
]

export const mockBackups = [
  { id: 'bk-1', created_at: '2026-05-28T10:00:00', size: 1048576, status: 'completed' },
  { id: 'bk-2', created_at: '2026-05-20T10:00:00', size: 524288, status: 'completed' },
]

export const mockBackupConfig = {
  provider: 'local',
  bucket: '',
  prefix: 'localbrain-backups',
  endpoint: '',
  access_key: '',
  secret_key: '',
}

export const mockGraphData = {
  nodes: [
    { id: 'n1', name: 'Python', type: 'technology', weight: 10 },
    { id: 'n2', name: 'Machine Learning', type: 'concept', weight: 8 },
    { id: 'n3', name: 'TensorFlow', type: 'technology', weight: 6 },
  ],
  links: [
    { source: 'n1', target: 'n2', weight: 5 },
    { source: 'n2', target: 'n3', weight: 3 },
  ],
}

export const mockGraphStats = {
  total_entities: 42,
  total_relations: 65,
  entity_types: { technology: 15, concept: 12, person: 8, organization: 7 },
}

export const mockTopicClusters = [
  { cluster_id: 'c1', label: 'AI & Machine Learning', keywords: ['ml', 'ai', 'neural'], document_count: 12 },
  { cluster_id: 'c2', label: 'Web Development', keywords: ['react', 'vue', 'css'], document_count: 8 },
]

export const mockTopicDocuments = [
  { id: 'td-1', title: 'Intro to ML', content_type: 'note', score: 0.92 },
  { id: 'td-2', title: 'Neural Networks', content_type: 'paper', score: 0.88 },
]

export const mockWikiTree = {
  categories: [
    { id: 'cat-1', name: 'Technology', article_count: 10 },
    { id: 'cat-2', name: 'Science', article_count: 5 },
  ],
  topics: [
    { id: 'top-1', name: 'Programming', article_count: 8 },
  ],
}

export const mockWikiStats = { total_articles: 25, total_categories: 5, total_topics: 3 }

export const mockWikiArticles = [
  { id: 'wa-1', title: 'Python Programming', category: 'Technology', content: '# Python\nPython is...', entities: ['Python'] },
  { id: 'wa-2', title: 'JavaScript Basics', category: 'Technology', content: '# JavaScript\nJS is...', entities: ['JavaScript'] },
]

export const mockConversations = [
  { session_id: 'sess-1', title: 'About ML', created_at: '2026-05-30T10:00:00', turn_count: 3 },
  { session_id: 'sess-2', title: 'Code review', created_at: '2026-05-29T10:00:00', turn_count: 1 },
]

export const mockConversationDetail = {
  session_id: 'sess-1',
  turns: [
    { turn_number: 1, query: 'What is ML?', answer: 'Machine learning is...', sources: [{ id: 'src-1', title: 'ML Guide', score: 0.9 }], created_at: '2026-05-30T10:00:00' },
  ],
}

export const mockSettings = {
  llm: { provider: 'dashscope', model: 'qwen-max' },
  embedding: { provider: 'dashscope', model: 'text-embedding-v2' },
}

export const mockDoctorResult = {
  checks: [
    { name: 'database', status: 'ok', message: 'SQLite connected' },
    { name: 'vectordb', status: 'ok', message: 'ChromaDB connected' },
    { name: 'llm', status: 'ok', message: 'LLM available' },
  ],
}
