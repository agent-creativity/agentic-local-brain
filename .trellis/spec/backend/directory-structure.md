# Directory Structure

> How backend code is organized in this project.

---

## Overview

The project uses a single top-level Python package `kb/` organized by functional responsibility. Each subpackage owns one concern (collection, processing, storage, querying, CLI, web API). Cross-cutting utilities live at the package root level (`config.py`, `cli.py`).

---

## Directory Layout

```
kb/
├── __init__.py              # Package init, exports version
├── cli.py                   # Click CLI entry point (group registration)
├── config.py                # YAML config loading, path resolution, defaults
├── version.py               # Version management (git tag + VERSION file)
├── self_update.py           # Self-update from remote
├── collectors/              # Content collection from external sources
│   ├── base.py              # BaseCollector ABC + CollectResult dataclass
│   ├── file_collector.py    # Local file ingestion
│   ├── webpage_collector.py # URL content extraction
│   ├── bookmark_collector.py
│   ├── bookmark_parser.py   # Browser bookmark file parsing
│   ├── note_collector.py    # Freeform note capture
│   ├── paper_collector.py   # Academic paper ingestion
│   └── email_collector.py   # Email content collection
├── commands/                # Click CLI command groups
│   ├── init.py              # `kb init` — first-run setup
│   ├── collect.py           # `kb collect` — file/webpage/paper/email/bookmark/note
│   ├── search.py            # `kb search` — semantic/keyword/rag/tags
│   ├── manage.py            # `kb config/stats/tag/export/test/web`
│   └── backup.py            # `kb backup` — create/list/status/restore
├── processors/              # Content transformation pipeline
│   ├── base.py              # BaseProcessor ABC + ProcessResult
│   ├── chunker.py           # Text splitting into chunks
│   ├── embedder.py          # Embedding vector generation (DashScope/OpenAI)
│   ├── tag_extractor.py     # LLM-based tag extraction
│   ├── doc_embedding.py     # Batch document embedding service
│   ├── builtin_extractor.py # Rule-based metadata extraction
│   ├── entity_extractor.py  # Named entity recognition
│   ├── topic_clusterer.py   # Topic clustering (scikit-learn)
│   ├── mining_worker.py     # Background mining orchestration
│   ├── wiki_compiler.py     # Wiki page generation
│   ├── recommendation.py    # Content recommendation engine
│   └── doc_relation_builder.py # Document relationship graph
├── query/                   # Knowledge retrieval and querying
│   ├── models.py            # Data models (SearchResult, RAGResult, RankedChunk, etc.)
│   ├── semantic_search.py   # Vector similarity search via ChromaDB
│   ├── keyword_search.py    # FTS5 text matching
│   ├── rag.py               # Retrieval Augmented Generation
│   ├── retrieval_pipeline.py # Multi-stage retrieval orchestration
│   ├── reranker.py          # Result reranking (NoOp / LLM)
│   ├── query_expander.py    # Query expansion (NoOp / LLM)
│   ├── context_builder.py   # Context assembly for LLM prompts
│   ├── conversation.py      # Multi-turn conversation management
│   ├── prompt_templates.py  # Prompt template registry
│   ├── reading_history.py   # User reading history tracking
│   ├── graph_query.py       # Knowledge graph queries
│   └── topic_query.py       # Topic-based retrieval
├── scheduler/               # Background task scheduling
│   └── backup_scheduler.py  # Cron-based backup (schedule + croniter)
├── storage/                 # Persistent data storage
│   ├── sqlite_storage.py    # SQLite metadata + FTS5 full-text search
│   └── chroma_storage.py    # ChromaDB vector storage
└── web/                     # FastAPI web API + frontend
    ├── app.py               # Application factory, middleware, lifespan
    ├── dependencies.py      # FastAPI Depends injection
    ├── routes/              # API route handlers (one file per domain)
    │   ├── items.py         # CRUD for knowledge items
    │   ├── search.py        # Search API endpoints
    │   ├── tags.py          # Tag management
    │   ├── dashboard.py     # Dashboard stats
    │   ├── settings.py      # User settings
    │   ├── backup.py        # Backup operations
    │   ├── mining.py        # Knowledge mining triggers
    │   ├── graph.py         # Knowledge graph visualization
    │   ├── recommendations.py # Content recommendations
    │   ├── topics.py        # Topic browsing
    │   └── wiki.py          # Wiki pages
    └── static/              # Frontend assets (JS, templates, docs)
        ├── js/pages/        # Page-specific JavaScript
        └── templates/pages/ # Jinja2 HTML templates
```

---

## Module Organization

**New feature placement rules:**

1. **New data source** → add a collector in `collectors/` inheriting `BaseCollector`
2. **New content transformation** → add a processor in `processors/` inheriting `BaseProcessor`
3. **New retrieval strategy** → add to `query/` following the pipeline component pattern (see `reranker.py`)
4. **New CLI command** → add to the appropriate command group in `commands/`
5. **New API endpoint** → add a route file in `web/routes/` and register in `app.py`
6. **New background job** → add to `scheduler/`

**Layering rule:** Dependencies flow downward: `commands/` → `collectors/` / `query/` → `processors/` → `storage/`. The `storage/` layer has no internal dependencies on other `kb/` subpackages.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python files | `snake_case.py` | `topic_clusterer.py` |
| Classes | `PascalCase` | `TopicClusterer`, `BaseCollector` |
| Abstract base classes | `Base` prefix | `BaseCollector`, `BaseProcessor`, `BaseReranker` |
| Result dataclasses | `*Result` suffix | `CollectResult`, `ProcessResult` |
| Test files | `test_*.py` | `test_sqlite_storage.py` |
| Route files | Domain noun (singular or plural) | `items.py`, `search.py`, `tags.py` |
| Config files | `*.yaml` | `config-template.yaml` |

---

## Examples

**Well-structured collector** — `kb/collectors/base.py`:
- Defines `BaseCollector` ABC with `collect()` and `_extract_content()` abstract methods
- Defines `CollectResult` dataclass as the standard return type
- All concrete collectors inherit and implement the interface

**Well-structured route module** — `kb/web/routes/items.py`:
- One file per API domain
- Router instance at module level
- Dependencies injected via `Depends()`

---

## Common Mistakes

1. **Putting business logic in `commands/`** — CLI commands should only parse arguments and delegate to `collectors/`, `query/`, or `processors/`. Logic in command files cannot be reused by the web API.

2. **Importing across sibling packages at the same level** — e.g., a collector importing from `query/`. This creates circular dependency risk. If shared, extract to a utility at package root or `storage/`.

3. **Adding files to `kb/` root instead of the appropriate subpackage** — Root-level files should be limited to cross-cutting concerns (config, CLI entry, version). Feature code belongs in a subpackage.
