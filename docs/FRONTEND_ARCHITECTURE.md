# Agentic Second Brain - Frontend Architecture Document

> This document describes the frontend functionality, data models, and API contracts for the Agentic Second Brain knowledge management system. Use this as a reference to build alternative UI experiences.

---

## 1. Project Overview

**Agentic Second Brain** is a personal knowledge management system that helps users:

- **Collect** knowledge from multiple sources (files, webpages, bookmarks, papers, emails, notes)
- **Organize** knowledge with tags and metadata
- **Search** using keyword or semantic similarity
- **Query** using RAG (Retrieval-Augmented Generation) for intelligent Q&A

---

## 2. Core Features & User Flows

### 2.1 Dashboard (Home)

**Purpose**: Provide at-a-glance overview of the knowledge base

**Features**:
| Feature | Description |
|---------|-------------|
| Total Items | Count of all knowledge items |
| Items by Type | Breakdown by content type (file, webpage, bookmark, paper, email, note) |
| Total Tags | Count of unique tags |
| Total Chunks | Count of document chunks for vector search |
| Recent Items | List of recently collected items |

**User Flow**:
```
User opens app → Dashboard loads → Shows stats cards + recent items
                                 → User clicks item → Opens detail modal
```

### 2.2 Knowledge Items (Documents)

**Purpose**: Browse, filter, and manage all collected knowledge

**Features**:
| Feature | Description |
|---------|-------------|
| List View | Paginated table of items with title, type, tags, date |
| Type Filter | Dropdown to filter by content type |
| Item Detail | Modal showing full metadata, summary, and chunks |
| Delete Item | Remove item with confirmation |
| Edit Item | Update title, summary, and tags |

**User Flow**:
```
Documents page → List loads with pagination
              → Filter by type → List updates
              → Click item → Detail modal opens
              → Edit/Delete → Confirmation → List refreshes
```

**Content Types**:
```typescript
type ContentType = 
  | 'file'      // Local files (PDF, MD, TXT)
  | 'webpage'   // Web articles
  | 'bookmark'  // Browser bookmarks
  | 'paper'     // Academic papers (arXiv)
  | 'email'     // Email messages
  | 'note'      // Quick notes
```

### 2.3 Tag Management

**Purpose**: Organize and manage tags across all knowledge items

**Features**:
| Feature | Description |
|---------|-------------|
| Tag Cloud | Visual display of tags with size by frequency |
| Tag List | Table view with tag name and item count |
| View Tagged Items | See all items with specific tag |
| Merge Tags | Combine two tags into one |
| Delete Tag | Remove tag from all items |

**User Flow**:
```
Tags page → Tag cloud + list loads
         → Click tag → Shows items with that tag
         → Merge: Select source + target → Confirm → Tags merged
         → Delete: Select tag → Confirm → Tag removed
```

### 2.4 Search

**Purpose**: Find knowledge using different search methods

**Search Types**:

| Type | Method | Use Case |
|------|--------|----------|
| **Keyword** | Full-text search (FTS5) | Find exact words/phrases |
| **Semantic** | Vector similarity | Find conceptually similar content |
| **RAG** | LLM + semantic search | Ask questions, get synthesized answers |

**User Flow**:
```
Search page → Select search type
           → Enter query → Submit
           → Results display with relevance scores
           → Click result → Item detail modal
```

**RAG Flow**:
```
Enter question → Semantic search finds relevant docs
              → Context sent to LLM
              → LLM generates answer with citations
              → Display answer + source documents
```

### 2.5 RAG Chat (v0.7 Enhanced Retrieval)

**Purpose**: Multi-turn conversational Q&A with advanced retrieval capabilities

**Layout**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│  RAG Chat                                                                 │
├────────────────┬─────────────────────────────────┬───────────────────────┤
│  Conversations  │  Chat Area                      │  Sources              │
│                │                                 │                       │
│  [+ New Chat]  │  User: What is RAG?             │  Used in last answer: │
│                │                                 │                       │
│  ▸ RAG Basics  │  AI: RAG stands for Retrieval-  │  ┌─────────────────┐ │
│    (12 msgs)   │  Augmented Generation...        │  │ 📄 RAG Paper     │ │
│                │                                 │  │ Score: 0.92     │ │
│  ▸ Vector DBs  │  User: How does it differ from  │  └─────────────────┘ │
│    (5 msgs)    │  fine-tuning?                   │                       │
│                │                                 │  ┌─────────────────┐ │
│                │  AI: Unlike fine-tuning...      │  │ 🌐 RAG Guide     │ │
│                │                                 │  │ Score: 0.87     │ │
│                │  ─────────────────────────────  │  └─────────────────┘ │
│                │  💡 Confidence: 85%             │                       │
│                │  🏷️ rag, llm, retrieval         │                       │
│                │  ─────────────────────────────  │  Entity Chips:        │
│                │  [📎 3 sources] [🔍 Similar]    │  [RAG] [Fine-tuning]  │
│                │                                 │  [Vector Store]       │
├────────────────┴─────────────────────────────────┴───────────────────────┤
│  [🔗 Use Graph] [📊 Use Topics] │ [Type a follow-up...        ] [Send] │
└──────────────────────────────────────────────────────────────────────────┘
```

**User Flow**:
```
RAG Chat page → Click "+ New Chat" or select existing conversation
              → Enter question in chat input
              → System processes:
                 1. Query expansion (optional)
                 2. Multi-source retrieval (semantic + graph + topics)
                 3. Reranking by relevance
                 4. Context assembly with token budget
                 5. LLM generation with enriched context
              → Display answer with:
                 - Markdown formatted response
                 - Confidence badge
                 - Source cards with scores
                 - Entity chips (clickable for more info)
              → Ask follow-up questions (conversation context maintained)
              → Toggle graph/topic enrichment for enhanced retrieval
```

**Features**:
| Feature | Description |
|---------|-------------|
| Multi-turn Chat | Conversation context maintained across messages |
| Source Panel | Shows documents used in current answer |
| Confidence Badge | AI-generated confidence score (0-100%) |
| Entity Chips | Extracted entities clickable for exploration |
| Graph Enrichment | Toggle to include knowledge graph relationships |
| Topic Enrichment | Toggle to include topic cluster context |
| Conversation History | Sidebar shows past conversations |
| Suggested Questions | Auto-generated follow-up suggestions |

---

## 3. Data Models

### 3.1 Knowledge Item

```typescript
interface KnowledgeItem {
  id: string                    // Unique identifier (UUID)
  title: string | null          // Item title
  content_type: ContentType     // Type of content
  source: string               // Original source (URL, file path, etc.)
  collected_at: string         // ISO timestamp
  summary: string | null       // AI-generated or manual summary
  word_count: number           // Character/word count
  file_path: string | null     // Path to stored markdown file
  tags: string[]               // Associated tags
}
```

### 3.2 Knowledge Item Detail (with chunks)

```typescript
interface KnowledgeItemDetail extends KnowledgeItem {
  chunks: Chunk[]              // Document chunks for vector search
}

interface Chunk {
  id: string
  chunk_index: number
  content: string
  embedding_id: string | null  // Reference to vector store
}
```

### 3.3 Tag

```typescript
interface Tag {
  name: string                 // Tag name (unique)
  count: number                // Number of items with this tag
}
```

### 3.4 Search Result

```typescript
interface SearchResult {
  id: string
  content: string              // Matched content/snippet
  metadata: {
    title?: string
    content_type?: string
    source?: string
    file_path?: string
    [key: string]: any
  }
  score: number                // Relevance score (0-1)
  tags?: string[]
}
```

### 3.5 RAG Result

```typescript
interface RAGResult {
  answer: string               // LLM-generated answer
  sources: SearchResult[]      // Source documents used
  question: string             // Original question
}
```

### 3.6 Statistics

```typescript
interface Stats {
  total_items: number
  items_by_type: {
    [type: string]: number     // e.g., { "webpage": 50, "file": 30 }
  }
  total_tags: number
  total_chunks: number
}
```

---

## 4. API Reference

### 4.1 Dashboard APIs

#### Get Statistics
```http
GET /api/stats
```

**Response**:
```json
{
  "total_items": 150,
  "items_by_type": {
    "webpage": 80,
    "file": 30,
    "bookmark": 25,
    "note": 10,
    "paper": 5
  },
  "total_tags": 45,
  "total_chunks": 1200
}
```

#### Get Recent Items
```http
GET /api/recent?limit=10
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | integer | 20 | Maximum items to return |

**Response**:
```json
[
  {
    "id": "abc123",
    "title": "Machine Learning Basics",
    "content_type": "webpage",
    "source": "https://example.com/ml-basics",
    "collected_at": "2024-03-25T10:30:00Z",
    "summary": "Introduction to ML concepts...",
    "word_count": 1500,
    "file_path": "/data/raw/webpages/ml-basics.md",
    "tags": ["machine-learning", "tutorial"]
  }
]
```

---

### 4.2 Items APIs

#### List Items
```http
GET /api/items?limit=20&offset=0&content_type=webpage
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | integer | 20 | Items per page |
| offset | integer | 0 | Pagination offset |
| content_type | string | null | Filter by type |

**Response**:
```json
{
  "items": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

#### Get Item Detail
```http
GET /api/items/{item_id}
```

**Response**:
```json
{
  "id": "abc123",
  "title": "Machine Learning Basics",
  "content_type": "webpage",
  "source": "https://example.com/ml-basics",
  "collected_at": "2024-03-25T10:30:00Z",
  "summary": "Introduction to ML concepts...",
  "word_count": 1500,
  "file_path": "/data/raw/webpages/ml-basics.md",
  "tags": ["machine-learning", "tutorial"],
  "chunks": [
    {
      "id": "chunk1",
      "chunk_index": 0,
      "content": "First section of the document...",
      "embedding_id": "vec_001"
    }
  ]
}
```

**Error**: `404 Not Found` if item doesn't exist

#### Update Item
```http
PUT /api/items/{item_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "summary": "Updated summary...",
  "tags": ["new-tag", "another-tag"]
}
```

**Request Body** (all fields optional):
```typescript
interface ItemUpdate {
  title?: string
  summary?: string
  tags?: string[]
}
```

#### Delete Item
```http
DELETE /api/items/{item_id}
```

**Response**:
```json
{
  "message": "Item deleted successfully"
}
```

---

### 4.3 Tags APIs

#### List Tags
```http
GET /api/tags?limit=100&order_by=count
```

**Parameters**:
| Name | Type | Default | Options | Description |
|------|------|---------|---------|-------------|
| limit | integer | 100 | - | Maximum tags |
| order_by | string | "count" | count, name | Sort order |

**Response**:
```json
[
  { "name": "python", "count": 45 },
  { "name": "machine-learning", "count": 32 },
  { "name": "tutorial", "count": 28 }
]
```

#### Get Items by Tag
```http
GET /api/tags/{tag_name}/items
```

**Response**:
```json
{
  "tag": "machine-learning",
  "items": [...],
  "total": 32
}
```

#### Merge Tags
```http
POST /api/tags/merge
Content-Type: application/json

{
  "source_tag": "ml",
  "target_tag": "machine-learning"
}
```

**Response**:
```json
{
  "message": "Tag 'ml' merged into 'machine-learning'",
  "affected_items": 15
}
```

#### Delete Tag
```http
DELETE /api/tags/{tag_name}
```

**Response**:
```json
{
  "message": "Tag 'deprecated-tag' deleted",
  "affected_items": 8
}
```

---

### 4.4 Search APIs

#### Keyword Search
```http
GET /api/search?q=machine+learning&content_type=webpage&limit=20
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| q | string | required | Search query |
| content_type | string | null | Filter by type |
| limit | integer | 20 | Max results |

**Response**:
```json
{
  "query": "machine learning",
  "results": [
    {
      "id": "abc123",
      "content": "...machine learning is a subset of AI...",
      "metadata": {
        "title": "ML Basics",
        "content_type": "webpage"
      },
      "score": 0.95,
      "tags": ["machine-learning"]
    }
  ],
  "total": 15
}
```

#### Semantic Search
```http
POST /api/search/semantic
Content-Type: application/json

{
  "query": "How does neural network training work?",
  "tags": ["deep-learning"],
  "top_k": 5
}
```

**Request Body**:
```typescript
interface SemanticSearchRequest {
  query: string           // Natural language query
  tags?: string[]         // Optional tag filter
  top_k?: number          // Default: 5
}
```

**Response**:
```json
{
  "query": "How does neural network training work?",
  "results": [
    {
      "id": "xyz789",
      "content": "Neural networks learn through backpropagation...",
      "metadata": {...},
      "score": 0.89
    }
  ]
}
```

**Error**: `503 Service Unavailable` if embedding service not configured

#### RAG Query
```http
POST /api/rag
Content-Type: application/json

{
  "question": "What are the main components of a transformer model?",
  "tags": ["deep-learning", "nlp"],
  "top_k": 5
}
```

**Request Body**:
```typescript
interface RAGRequest {
  question: string        // Question to answer
  tags?: string[]         // Optional tag filter
  top_k?: number          // Documents to retrieve (default: 5)
}
```

**Response**:
```json
{
  "question": "What are the main components of a transformer model?",
  "answer": "A transformer model consists of several key components:\n\n1. **Self-Attention Mechanism**: Allows the model to weigh the importance of different parts of the input...\n\n2. **Multi-Head Attention**: Runs multiple attention operations in parallel...\n\n3. **Feed-Forward Networks**: Applied after attention layers...\n\n4. **Positional Encoding**: Adds position information since transformers don't inherently understand order...",
  "sources": [
    {
      "id": "paper_001",
      "content": "The Transformer architecture was introduced in...",
      "metadata": {
        "title": "Attention Is All You Need",
        "content_type": "paper"
      },
      "score": 0.92
    }
  ]
}
```

**Error**: `503 Service Unavailable` if LLM service not configured

---

## 5. UI Component Specifications

### 5.1 Navigation

```
┌─────────────────────────────────────────────────────────┐
│  🧠 Second Brain                                         │
├─────────────────────────────────────────────────────────┤
│  📊 Dashboard        ← Current page indicator           │
│  📄 Documents                                            │
│  🏷️ Tags                                                 │
│  🔍 Search                                               │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  Statistics                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │   150   │  │   45    │  │  1200   │  │ webpage │    │
│  │  Items  │  │  Tags   │  │ Chunks  │  │  (80)   │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
├─────────────────────────────────────────────────────────┤
│  Recent Items                                            │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 📄 Machine Learning Basics     webpage  3h ago      ││
│  │ 📑 Python Best Practices       file     5h ago      ││
│  │ 🔖 Awesome Resources           bookmark 1d ago      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 5.3 Documents List

```
┌─────────────────────────────────────────────────────────┐
│  Documents                    [Filter: All Types ▼]     │
├─────────────────────────────────────────────────────────┤
│  Title              Type      Tags           Date    ⋮  │
│  ─────────────────────────────────────────────────────  │
│  ML Basics          webpage   ml, tutorial   Mar 25  ⋮  │
│  Python Guide       file      python, guide  Mar 24  ⋮  │
│  Research Paper     paper     research, ai   Mar 23  ⋮  │
├─────────────────────────────────────────────────────────┤
│  [← Prev]  Page 1 of 8  [Next →]                        │
└─────────────────────────────────────────────────────────┘
```

### 5.4 Search Interface

```
┌─────────────────────────────────────────────────────────┐
│  Search                                                  │
│  ┌─────────────────────────────────────────────────────┐│
│  │ [🔍 Enter your query...                           ] ││
│  └─────────────────────────────────────────────────────┘│
│  [○ Keyword] [● Semantic] [○ RAG Q&A]                   │
│  [Filter: All Types ▼]                                   │
├─────────────────────────────────────────────────────────┤
│  Results (15 found)                                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 📄 Machine Learning Introduction        Score: 95%  ││
│  │    "...machine learning enables computers to..."    ││
│  │    🏷️ ml  tutorial                                  ││
│  ├─────────────────────────────────────────────────────┤│
│  │ 📑 Deep Learning Fundamentals           Score: 87%  ││
│  │    "...neural networks are the foundation of..."    ││
│  │    🏷️ deep-learning  neural-networks               ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 5.5 RAG Answer Display

```
┌─────────────────────────────────────────────────────────┐
│  ❓ What is backpropagation?                            │
├─────────────────────────────────────────────────────────┤
│  💡 Answer                                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Backpropagation is an algorithm used to train       ││
│  │ neural networks by calculating gradients of the     ││
│  │ loss function with respect to the weights.          ││
│  │                                                      ││
│  │ Key steps:                                           ││
│  │ 1. Forward pass - compute predictions               ││
│  │ 2. Calculate loss                                    ││
│  │ 3. Backward pass - compute gradients                ││
│  │ 4. Update weights                                    ││
│  └─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│  📚 Sources                                              │
│  • Deep Learning Fundamentals (paper) - 92% match      │
│  • Neural Network Training Guide (webpage) - 87% match │
└─────────────────────────────────────────────────────────┘
```

### 5.6 Tag Management

```
┌─────────────────────────────────────────────────────────┐
│  Tags                                                    │
├─────────────────────────────────────────────────────────┤
│  Tag Cloud                                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │    python(45)  machine-learning(32)  tutorial(28)   ││
│  │  deep-learning(25)   api(20)   javascript(18)      ││
│  │     web(15)  database(12)  docker(10)  git(8)      ││
│  └─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│  Merge Tags                                              │
│  [Source Tag ▼] → [Target Tag ▼]  [Merge]              │
├─────────────────────────────────────────────────────────┤
│  All Tags                                                │
│  Tag Name              Count    Actions                 │
│  python                45       [View] [Delete]         │
│  machine-learning      32       [View] [Delete]         │
│  tutorial              28       [View] [Delete]         │
└─────────────────────────────────────────────────────────┘
```

### 5.7 Item Detail Modal

```
┌─────────────────────────────────────────────────────────┐
│  📄 Machine Learning Basics                    [×]      │
├─────────────────────────────────────────────────────────┤
│  Type:      webpage                                      │
│  Source:    https://example.com/ml-basics               │
│  Collected: March 25, 2024, 10:30 AM                    │
│  Words:     1,500                                        │
│  ─────────────────────────────────────────────────────  │
│  Tags:                                                   │
│  [machine-learning] [tutorial] [beginner]               │
│  ─────────────────────────────────────────────────────  │
│  Summary:                                                │
│  This article provides an introduction to machine       │
│  learning concepts including supervised learning,       │
│  unsupervised learning, and reinforcement learning.     │
│  ─────────────────────────────────────────────────────  │
│  Chunks (12):                                            │
│  ┌─────────────────────────────────────────────────────┐│
│  │ [1] Machine learning is a subset of artificial...   ││
│  │ [2] Supervised learning involves training a model...││
│  │ [3] Unsupervised learning discovers patterns...     ││
│  └─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│  [Edit] [Open Source] [Delete]                          │
└─────────────────────────────────────────────────────────┘
```

---

## 6. State Management

### 6.1 Global Application State

```typescript
interface AppState {
  // Navigation
  currentPage: 'dashboard' | 'documents' | 'tags' | 'search'
  
  // Dashboard
  stats: Stats | null
  recentItems: KnowledgeItem[]
  
  // Documents
  items: KnowledgeItem[]
  itemsTotal: number
  itemsOffset: number
  itemsLimit: number
  contentTypeFilter: ContentType | null
  
  // Tags
  tags: Tag[]
  selectedTag: string | null
  tagItems: KnowledgeItem[]
  
  // Search
  searchQuery: string
  searchType: 'keyword' | 'semantic' | 'rag'
  searchResults: SearchResult[]
  ragAnswer: RAGResult | null
  
  // RAG Chat (v0.7)
  ragMessages: RAGChatMessage[]
  ragCurrentSessionId: string | null
  ragConversations: RAGConversation[]
  ragUseGraph: boolean
  ragUseTopics: boolean
  
  // UI State
  loading: {
    stats: boolean
    items: boolean
    tags: boolean
    search: boolean
  }
  
  // Modals
  modals: {
    itemDetail: { visible: boolean; item: KnowledgeItemDetail | null }
    tagItems: { visible: boolean; tag: string | null }
    deleteConfirm: { visible: boolean; type: 'item' | 'tag'; id: string }
    editItem: { visible: boolean; item: KnowledgeItem | null }
  }
  
  // Notifications
  toasts: Toast[]
}

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}
```

### 6.2 Actions

```typescript
// Dashboard
fetchStats(): Promise<void>
fetchRecentItems(limit?: number): Promise<void>

// Items
fetchItems(limit?: number, offset?: number, contentType?: string): Promise<void>
viewItem(id: string): Promise<void>
updateItem(id: string, data: ItemUpdate): Promise<void>
deleteItem(id: string): Promise<void>

// Tags
fetchTags(limit?: number, orderBy?: string): Promise<void>
viewTagItems(tagName: string): Promise<void>
mergeTags(source: string, target: string): Promise<void>
deleteTag(tagName: string): Promise<void>

// Search
performKeywordSearch(query: string, contentType?: string, limit?: number): Promise<void>
performSemanticSearch(query: string, tags?: string[], topK?: number): Promise<void>
performRAGQuery(question: string, tags?: string[], topK?: number): Promise<void>

// RAG Chat (v0.7)
startNewRAGChat(): Promise<void>
loadRAGConversation(sessionId: string): Promise<void>
sendRAGMessage(message: string, useGraph?: boolean, useTopics?: boolean): Promise<void>
deleteRAGConversation(sessionId: string): Promise<void>
fetchRAGSuggestions(sessionId: string): Promise<string[]>

// UI
showToast(type: string, message: string): void
openModal(modalType: string, data?: any): void
closeModal(modalType: string): void
navigateTo(page: string): void
```

---

## 7. Design Tokens

### 7.1 Colors

```css
/* Primary */
--color-primary: #3B82F6;        /* Blue - main actions */
--color-primary-hover: #2563EB;
--color-primary-light: #DBEAFE;

/* Content Types */
--color-file: #10B981;           /* Green */
--color-webpage: #3B82F6;        /* Blue */
--color-bookmark: #F59E0B;       /* Amber */
--color-paper: #8B5CF6;          /* Purple */
--color-email: #EF4444;          /* Red */
--color-note: #6B7280;           /* Gray */

/* Semantic */
--color-success: #10B981;
--color-warning: #F59E0B;
--color-error: #EF4444;
--color-info: #3B82F6;

/* Neutral */
--color-bg: #FFFFFF;
--color-bg-secondary: #F3F4F6;
--color-text: #111827;
--color-text-secondary: #6B7280;
--color-border: #E5E7EB;
```

### 7.2 Typography

```css
/* Font Family */
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* Font Sizes */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
```

### 7.3 Spacing

```css
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
```

### 7.4 Content Type Icons

| Type | Icon | Color |
|------|------|-------|
| file | 📄 / FileText | Green |
| webpage | 🌐 / Globe | Blue |
| bookmark | 🔖 / Bookmark | Amber |
| paper | 📑 / FileText | Purple |
| email | ✉️ / Mail | Red |
| note | 📝 / StickyNote | Gray |

---

## 8. Responsive Breakpoints

```css
/* Mobile First */
--screen-sm: 640px;    /* Small devices */
--screen-md: 768px;    /* Tablets */
--screen-lg: 1024px;   /* Laptops */
--screen-xl: 1280px;   /* Desktops */
```

### Layout Adaptations

| Breakpoint | Sidebar | Content | Cards |
|------------|---------|---------|-------|
| < 768px | Hidden/Drawer | Full width | Stack |
| 768-1024px | Collapsed icons | Fluid | 2 columns |
| > 1024px | Full (240px) | Fluid | 4 columns |

---

## 9. Error Handling

### 9.1 HTTP Error Codes

| Code | Meaning | User Message |
|------|---------|--------------|
| 400 | Bad Request | "Invalid request. Please check your input." |
| 404 | Not Found | "Item not found. It may have been deleted." |
| 500 | Server Error | "Something went wrong. Please try again." |
| 503 | Service Unavailable | "Service not configured. Check settings." |

### 9.2 Service Availability

| Feature | Required Service | Fallback |
|---------|------------------|----------|
| Keyword Search | None | Always available |
| Semantic Search | Embedding API | Show 503 error |
| RAG Query | Embedding + LLM API | Show 503 error |

---

## 10. Accessibility Guidelines

- All interactive elements must be keyboard accessible
- Color is not the only means of conveying information
- Minimum contrast ratio: 4.5:1 for text
- Focus indicators visible on all interactive elements
- ARIA labels for icons and non-text elements
- Screen reader announcements for dynamic content updates

---

## 11. Future Features (Roadmap)

| Feature | Priority | Description |
|---------|----------|-------------|
| Bulk Operations | High | Select multiple items for tag/delete |
| Import/Export | High | Backup and restore knowledge base |
| Collections | Medium | Group items into named collections |
| Reading List | Medium | Mark items as to-read/read |
| Highlights | Medium | Save highlighted excerpts |
| Sharing | Low | Share items via public links |
| Collaboration | Low | Multi-user knowledge bases |

---

## 12. API Base Configuration

```typescript
const API_CONFIG = {
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
}

// For external deployments
const API_CONFIG_EXTERNAL = {
  baseURL: 'http://localhost:11201/api',
  // ... same as above
}
```

---

*Last updated: March 2026*
