# AGENTS.md

> This file provides context for AI coding agents working with this codebase.

## Project Overview

**Agentic Local Brain** is a comprehensive personal knowledge management system designed to collect, process, and query knowledge from multiple sources. It features:

- **Multi-source Collection**: Files (PDF, Markdown, text), webpages, bookmarks, academic papers, emails, and notes
- **Intelligent Processing**: LLM-based tagging and vector embedding for semantic search
- **Flexible Retrieval**: Keyword search, semantic search, and RAG-based Q&A
- **Dual Interface**: CLI and REST API

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌─────────────┐              ┌─────────────────────┐   │
│  │    CLI      │              │    Web API (REST)   │   │
│  │  (Click)    │              │     (FastAPI)       │   │
│  └──────┬──────┘              └──────────┬──────────┘   │
└─────────┼────────────────────────────────┼──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Modules                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Collectors  │  │ Processors  │  │     Query       │  │
│  │ - File      │  │ - Chunker   │  │ - Semantic      │  │
│  │ - Webpage   │  │ - Embedder  │  │ - Keyword       │  │
│  │ - Bookmark  │  │ - Tagger    │  │ - RAG           │  │
│  │ - Paper     │  │             │  │                 │  │
│  │ - Email     │  │             │  │                 │  │
│  │ - Note      │  │             │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Storage Layer                         │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │   SQLite Storage    │    │    Chroma Storage       │ │
│  │   (Metadata, Tags)  │    │    (Vector Embeddings)  │ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
kb/
├── __init__.py           # Package init with version
├── cli.py                # CLI entry point (Click framework)
├── config.py             # Configuration management (YAML-based)
├── collectors/           # Data collection modules
│   ├── base.py           # Abstract BaseCollector class
│   ├── file_collector.py # PDF, Markdown, text files
│   ├── webpage_collector.py
│   ├── bookmark_collector.py
│   ├── paper_collector.py
│   ├── email_collector.py
│   └── note_collector.py
├── processors/           # Content processing modules
│   ├── base.py           # Abstract BaseProcessor class
│   ├── chunker.py        # Document chunking
│   ├── embedder.py       # Text vectorization (DashScope/OpenAI)
│   ├── tag_extractor.py  # LLM-based tagging
│   └── wiki_compiler.py  # LLM-powered wiki article compilation (v0.7)
├── query/                # Search and retrieval
│   ├── models.py         # Data models (SearchResult, RAGResult, EnhancedRAGResult, etc.)
│   ├── semantic_search.py
│   ├── keyword_search.py
│   ├── rag.py            # RAG query implementation (v0.6)
│   ├── retrieval_pipeline.py  # Multi-stage retrieval orchestrator (v0.7)
│   ├── query_expander.py      # Query expansion and rewriting (v0.7)
│   ├── reranker.py            # LLM-based result reranking (v0.7)
│   ├── context_builder.py     # Token-aware context assembly (v0.7)
│   ├── conversation.py        # Multi-turn conversation management (v0.7)
│   ├── prompt_templates.py    # Configurable prompt templates (v0.7)
│   ├── graph_query.py         # Knowledge graph traversal (v0.6)
│   ├── topic_query.py         # Topic/cluster queries (v0.6)
│   └── reading_history.py     # Reading pattern tracking (v0.6)
├── storage/              # Data persistence
│   ├── sqlite_storage.py # Metadata and tags
│   └── chroma_storage.py # Vector storage
└── web/                  # REST API
    ├── app.py            # FastAPI application
    ├── dependencies.py   # Shared dependencies
    └── routes/           # API endpoints
        ├── dashboard.py
        ├── items.py
        ├── tags.py
        ├── search.py
        └── wiki.py        # Wiki article API endpoints (v0.7)
```

## Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| CLI Framework | Click | 8.0+ |
| Web Framework | FastAPI | 0.95+ |
| ASGI Server | Uvicorn | 0.20+ |
| Vector Storage | ChromaDB | 0.4+ |
| Metadata Storage | SQLite | Built-in |
| PDF Processing | PyPDF2 | 3.0+ |
| Web Scraping | httpx, readability-lxml | - |
| AI/ML (Embedding) | DashScope (text-embedding-v4) | 1.14+ |
| AI/ML (LLM) | DashScope (qwen-plus/qwen-max) | 1.14+ |
| LLM Integration | litellm | 1.30+ |
| Configuration | PyYAML | 6.0+ |
| Testing | pytest | 7.0+ |

## Entry Points

### CLI (`kb/cli.py`)

Main entry point configured in `pyproject.toml`:

```bash
# Installation creates 'kb' command
pip install -e .

# Common commands
kb init                          # Initialize knowledge base
kb collect file <path>           # Collect from file
kb collect webpage <url>         # Collect from webpage
kb bookmark collect              # Import browser bookmarks
kb query "search query"          # Semantic search
kb search "keyword"              # Keyword search
kb rag "question"                # RAG-based Q&A
kb tags list                     # List all tags
kb web                           # Start web server
kb test embedding                # Test embedding service
kb test llm                      # Test LLM service
kb wiki compile                  # Compile wiki articles from topics
kb wiki list                     # List compiled articles
kb wiki show <article_id>        # Show article content
```

### Web API (`kb/web/app.py`)

REST API endpoints:

- `GET /api/dashboard/stats` - Statistics
- `GET /api/items` - List knowledge items
- `GET /api/items/{id}` - Get item by ID
- `GET /api/tags` - List all tags
- `POST /api/search/keyword` - Keyword search
- `POST /api/search/semantic` - Semantic search
- `POST /api/search/rag` - RAG query

Enhanced RAG (v0.7):
- `POST /api/rag/chat` - Multi-turn RAG with conversation support
- `GET /api/rag/conversations` - List conversation sessions
- `GET /api/rag/conversations/{session_id}` - Get full conversation
- `DELETE /api/rag/conversations/{session_id}` - Delete conversation
- `POST /api/rag/suggest` - Query suggestions
- `GET /api/dashboard/rag-stats` - RAG analytics

Wiki (v0.7):
- `GET /api/wiki/tree` - Wiki structure tree
- `GET /api/wiki/articles` - List articles
- `GET /api/wiki/articles/{article_id}` - Get article
- `GET /api/wiki/search` - Search wiki
- `GET /api/wiki/categories/{category_id}/articles` - Articles by category
- `GET /api/wiki/topics/{topic_id}/articles` - Articles by topic
- `GET /api/wiki/entities` - Entity cards
- `GET /api/wiki/entities/{entity_id}` - Get entity card
- `GET /api/wiki/stats` - Wiki statistics

API docs available at `http://localhost:11201/docs` when server is running.

### Configuration (`kb/config.py`)

Configuration file: `~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base
embedding:
  provider: dashscope
  model: text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
llm:
  provider: dashscope
  model: qwen-plus
  api_key: ${DASHSCOPE_API_KEY}
chunking:
  max_chunk_size: 1000
  overlap: 100
wiki:
  enabled: true
  compilation:
    max_article_length: 3000
    min_cluster_size: 2
```

## Key Design Patterns

### 1. Abstract Base Classes

All collectors inherit from `BaseCollector`:

```python
class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> CollectResult:
        """Implement collection logic"""
        pass
    
    @abstractmethod
    def _extract_content(self) -> str:
        """Extract content from source"""
        pass
```

### 2. Data Classes for Results

```python
@dataclass
class CollectResult:
    success: bool
    file_path: Optional[str]
    title: Optional[str]
    word_count: int
    tags: List[str]
    metadata: Dict[str, Any]
    error: Optional[str]
```

### 3. Provider Pattern

Embedder and TagExtractor support multiple providers:

```python
# DashScope provider
embedder = Embedder(provider="dashscope", api_key="...")

# OpenAI-compatible provider (Ollama, vLLM)
embedder = Embedder(provider="openai", base_url="http://localhost:11434/v1")
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file_collector.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=kb
```

### Test Organization

Tests mirror the module structure:

- `tests/test_file_collector.py` → `kb/collectors/file_collector.py`
- `tests/test_embedder.py` → `kb/processors/embedder.py`
- `tests/test_sqlite_storage.py` → `kb/storage/sqlite_storage.py`
- `tests/test_web_api.py` → `kb/web/`

### Integration Tests

```bash
# Test model service connectivity
python tests/test_model_services_integration.py
```

## Common Development Tasks

### Adding a New Collector

1. Create `kb/collectors/new_collector.py`
2. Inherit from `BaseCollector`
3. Implement `collect()`, `_extract_content()`, `_generate_metadata()`
4. Export in `kb/collectors/__init__.py`
5. Add CLI command in `kb/cli.py`
6. Add tests in `tests/test_new_collector.py`

### Adding a New API Endpoint

1. Create route file in `kb/web/routes/`
2. Define FastAPI router and endpoints
3. Register router in `kb/web/app.py`
4. Add tests in `tests/test_web_api.py`

### Modifying Configuration

1. Update defaults in `kb/config.py`
2. Update `config-template.yaml`
3. Document in README.md

## Data Flow

### Collection Pipeline

```
Source → Collector → Markdown File (with YAML front matter)
                   ↓
           SQLite (metadata) + Chroma (embeddings)
```

### Wiki Compilation Pipeline

```
Topic Clusters → Wiki Compiler → LLM → Wiki Articles (SQLite)
```

### Query Pipeline

```
User Query → Embedding → Chroma Similarity Search → Ranked Results
         or
User Query → SQLite FTS5 → Matched Documents
         or
User Question → Query Expansion → Hybrid Retrieval (Semantic + Keyword RRF)
              → LLM Reranking → Entity/Topic Enrichment
              → Context Assembly → LLM → Answer + Sources
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | Alibaba DashScope API key for embeddings and LLM |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI provider) |
| `KB_CONFIG_PATH` | Custom config file path (optional) |

## File Conventions

- **Knowledge Items**: Stored as Markdown files with YAML front matter
- **Database**: SQLite at `~/.knowledge-base/db/metadata.db`
- **Vector Store**: Chroma at `~/.knowledge-base/db/chroma/`
- **Raw Data**: `~/.knowledge-base/1_collect/{type}/`

## Code Style

- **Formatter**: Black (line length 88)
- **Import Sorting**: isort
- **Type Checking**: mypy
- **Docstrings**: Google style

```bash
# Format code
black kb/
isort kb/

# Type check
mypy kb/
```
