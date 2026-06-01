export const mockStats = {
  total_items: 42,
  total_tags: 15,
  items_by_type: {
    note: 10,
    bookmark: 8,
    webpage: 12,
    paper: 5,
    email: 4,
    file: 3,
  },
}

export const mockRagStats = {
  total_queries: 128,
  total_conversations: 23,
}

export const mockItems = Array.from({ length: 5 }, (_, i) => ({
  id: `item-${i + 1}`,
  title: `Test Item ${i + 1}`,
  content_type: 'note',
  source: `https://example.com/${i + 1}`,
  collected_at: '2026-05-01T10:00:00',
  word_count: 100 + i * 50,
  summary: `Summary for item ${i + 1}`,
  tags: ['tag-a', 'tag-b'],
  user_notes: '',
}))

export const mockTags = [
  { name: 'tag-a', count: 10 },
  { name: 'tag-b', count: 8 },
  { name: 'tag-c', count: 5 },
]

export const mockItemDetail = {
  id: 'item-1',
  title: 'Test Item 1',
  content_type: 'note',
  source: 'https://example.com/1',
  collected_at: '2026-05-01T10:00:00',
  word_count: 150,
  summary: 'Summary for item 1',
  tags: ['tag-a', 'tag-b'],
  user_notes: 'My notes here',
}

export const mockPreview = {
  content: 'Full preview content of the knowledge item...',
  file_path: '',
}
