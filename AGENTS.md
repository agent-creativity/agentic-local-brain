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

### Building and Releasing a New Version

When building and releasing a new version, **always use the provided release script**:

```bash
# Build and release using version from VERSION file
./scripts/local-build-release.sh

# Build and release with specific version
./scripts/local-build-release.sh 0.8.2
```

**What the script does**:
1. Builds release artifacts (wheel package)
2. Copies artifacts to publish repository
3. Commits and pushes to publish repository
4. Builds web assets with npm
5. Uploads to OSS (Object Storage Service)

**Before running the script**:
1. Update `VERSION` file with new version number
2. Create release documentation in `docs/releases/vX.Y.Z/`:
   - `release-notes.md` - User-facing release notes
   - `changelog.md` - Detailed changelog
3. Update root `CHANGELOG.md` with summary
4. Commit all changes to git

**Do NOT**:
- Run `python -m build` directly
- Run `pip install build` and build manually
- Use other build tools without the release script

The release script ensures consistent builds and proper deployment to all distribution channels.

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

## Documentation Standards

### Documentation Structure

All project documentation follows a standardized structure under the `docs/` directory:

```
docs/
├── README.md                    # Documentation index and navigation
├── guides/                      # User guides (installation, configuration, usage)
├── architecture/                # Architecture design (system architecture, tech stack)
├── features/                    # Feature documentation (feature descriptions, usage)
├── development/                 # Development docs (setup, coding standards, testing)
├── releases/                    # Version releases (archived by version)
│   └── v0.8.1/
├── design/                      # Design decisions (ADR - Architecture Decision Records)
├── troubleshooting/             # Problem solving (common issues, troubleshooting)
├── blog/                        # Blog articles (technical sharing, project stories)
└── assets/                      # Resource files (images, diagrams)
    └── images/
```

### File Naming Conventions

**General Documents**:
- Use lowercase with hyphens: `quick-start.md`, `api-reference.md`
- ✅ Good: `user-guide.md`, `installation-guide.md`
- ❌ Bad: `UserGuide.md`, `user_guide.md`, `USERGUIDE.md`

**Design Documents (ADR)**:
- Use date prefix: `YYYY-MM-DD-title.md`
- ✅ Good: `2026-04-19-ollama-embedding-fix.md`
- ❌ Bad: `ollama-fix.md`, `2026-04-19_ollama_fix.md`

**Version Documents**:
- Place in `docs/releases/vX.Y.Z/` directory
- Use simple names: `release-notes.md`, `changelog.md`, `migration-guide.md`

### Document Structure

Every documentation file should follow this structure:

```markdown
# Document Title (H1 - only one per document)

Brief introduction or overview (1-2 paragraphs).

## Main Section (H2)

Content for main section.

### Subsection (H3)

Content for subsection.

#### Detail (H4 - use sparingly)

Detailed content.
```

**Heading Guidelines**:
- Use only one H1 (`#`) per document - the document title
- Use H2 (`##`) for main sections
- Use H3 (`###`) for subsections
- Avoid H4 (`####`) unless absolutely necessary
- Never skip heading levels (don't go from H2 to H4)

### Creating New Documentation

When creating new documentation, follow these steps:

**1. Determine Document Type**

Choose the appropriate directory based on content:

| Type | Directory | Example |
|------|-----------|---------|
| User Guide | `docs/guides/` | Installation, configuration, quick start |
| Architecture | `docs/architecture/` | System design, data flow, tech decisions |
| Feature | `docs/features/` | Feature descriptions, usage instructions |
| Development | `docs/development/` | Dev setup, coding standards, API reference |
| Design Decision | `docs/design/` | ADR documents with date prefix |
| Troubleshooting | `docs/troubleshooting/` | Common issues, error solutions |
| Blog | `docs/blog/` | Technical articles, project stories |

**2. Create the Document**

```bash
# Example: Creating a new feature document
touch docs/features/knowledge-mining.md

# Example: Creating a design decision
touch docs/design/2026-04-19-feature-name.md
```

**3. Add Document Metadata (Optional)**

For better organization, add frontmatter at the top:

```markdown
---
title: Feature Name
date: 2026-04-19
author: AI Team
tags: [feature, knowledge-mining]
status: active
---
```

**4. Update Documentation Index**

Add the new document to `docs/README.md`:

```markdown
### ✨ Feature Documentation
- [Knowledge Mining](features/knowledge-mining.md) - Automatic knowledge extraction
- [Your New Feature](features/your-feature.md) - Brief description
```

### Version Release Documentation

When releasing a new version, create a complete documentation set:

**1. Create Version Directory**

```bash
mkdir -p docs/releases/v0.9.0
```

**2. Required Documents**

Each version release should include:

- `release-notes.md` - User-facing release notes
- `changelog.md` - Detailed change log
- `migration-guide.md` - Upgrade instructions (if breaking changes)
- `test-report.md` - Testing summary (optional)

**3. Update Root CHANGELOG**

Update the root `CHANGELOG.md` with a summary and link to detailed notes:

```markdown
## [0.9.0] - 2026-05-01

See [v0.9.0 Release Notes](docs/releases/v0.9.0/release-notes.md) for details.

### Added
- New feature X
- New feature Y

### Changed
- Updated component Z

### Fixed
- Bug fix A
```

### Design Decision Records (ADR)

When making significant architectural or design decisions, document them using ADR format:

**File Name**: `docs/design/YYYY-MM-DD-decision-title.md`

**Template**:

```markdown
# Decision Title

**Date**: 2026-04-19
**Status**: Accepted | Proposed | Deprecated | Superseded
**Deciders**: Team members involved

## Context

What is the issue we're trying to solve? What are the constraints?

## Decision

What is the change we're proposing or have agreed to?

## Consequences

### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Trade-off 2

### Neutral
- Other consideration 1

## Alternatives Considered

### Alternative 1
- Description
- Why not chosen

### Alternative 2
- Description
- Why not chosen

## Implementation

How will this be implemented? What are the steps?

## References

- Link to related issues
- Link to related PRs
- External references
```

### Troubleshooting Documentation

When documenting solutions to problems:

**File Name**: `docs/troubleshooting/problem-name.md`

**Template**:

```markdown
# Problem Name

## Problem Description

Clear description of the issue and symptoms.

## Root Cause

Technical analysis of why this problem occurs.

## Solution

Step-by-step solution with code examples.

### Quick Fix

```bash
# Commands to fix the issue
```

### Detailed Steps

1. Step 1
2. Step 2
3. Step 3

## Verification

How to verify the fix worked:

```bash
# Verification commands
```

## Prevention

How to prevent this issue in the future.

## Related Issues

- Link to GitHub issues
- Link to related documentation
```

### Link Conventions

**Use Relative Links** (Preferred):

```markdown
# From docs/features/backup.md to docs/guides/configuration.md
[Configuration Guide](../guides/configuration.md)

# From docs/design/2026-04-19-feature.md to docs/features/feature.md
[Feature Documentation](../features/feature.md)
```

**Avoid Absolute Links**:

```markdown
# ❌ Bad - breaks when repo is forked or moved
[Configuration](/docs/guides/configuration.md)

# ✅ Good - works everywhere
[Configuration](../guides/configuration.md)
```

### Code Examples in Documentation

When including code examples:

**1. Use Proper Syntax Highlighting**

```markdown
```python
def example_function():
    return "Hello, World!"
```
```

**2. Include Context**

```markdown
# Example: Configuring Ollama embedding

```yaml
embedding:
  provider: litellm
  model: ollama/nomic-embed-text
  api_key: not-needed
  base_url: http://localhost:11434
```
```

**3. Show Complete Examples**

Provide working examples that users can copy and run:

```markdown
# Complete example of using the embedder

```python
from kb.processors.embedder import Embedder

# Initialize embedder
embedder = Embedder.from_config()

# Generate embeddings
texts = ["Example text 1", "Example text 2"]
embeddings = embedder.embed(texts)

print(f"Generated {len(embeddings)} embeddings")
```
```

### Documentation Maintenance

**Regular Tasks**:

1. **Review and Update**: Quarterly review of all documentation for accuracy
2. **Link Checking**: Verify all internal and external links work
3. **Version Cleanup**: Archive old version documentation after 1 year
4. **Index Updates**: Keep `docs/README.md` current with all documents

**Tools**:

```bash
# Check markdown formatting
markdownlint docs/**/*.md

# Check links
markdown-link-check docs/**/*.md

# Generate documentation site (optional)
mkdocs serve
```

### Documentation Checklist

Before committing documentation changes, verify:

- [ ] File is in the correct directory
- [ ] File name follows naming conventions
- [ ] Document has proper heading structure (one H1, logical H2/H3)
- [ ] Code examples are complete and tested
- [ ] Links use relative paths
- [ ] `docs/README.md` index is updated
- [ ] No spelling or grammar errors
- [ ] Markdown formatting is correct

### Root Directory Files

Keep the root directory clean. Only these documentation files should exist in root:

- `README.md` - Project overview and quick start (English)
- `README_zh.md` - Project overview and quick start (Chinese)
- `CHANGELOG.md` - Unified changelog (links to detailed version docs)
- `AGENTS.md` - This file - context for AI agents
- `CONTRIBUTING.md` - Contribution guidelines (if exists)
- `LICENSE` - Project license

**All other documentation** should be in the `docs/` directory.

### Documentation Organization Script

Use the provided script to organize documentation:

```bash
# Run documentation organization script
./scripts/organize-docs.sh

# This will:
# - Create backup of current state
# - Move files to appropriate directories
# - Create documentation index
# - Clean up temporary files
```

For detailed information, see:
- [Documentation Organization Plan](docs/documentation-organization-plan.md)
- [Quick Start Guide](docs/QUICK_START_DOCS_ORGANIZATION.md)

### Examples

**Good Documentation Structure**:

```
✅ docs/guides/installation.md
✅ docs/features/backup.md
✅ docs/design/2026-04-19-ollama-fix.md
✅ docs/troubleshooting/common-errors.md
✅ docs/releases/v0.8.1/release-notes.md
```

**Bad Documentation Structure**:

```
❌ ROOT/INSTALLATION_GUIDE.md
❌ ROOT/backup_feature_v2.md
❌ docs/ollama-fix.md (missing date prefix for design doc)
❌ docs/errors.md (should be in troubleshooting/)
❌ ROOT/RELEASE_NOTES_0.8.1.md (should be in releases/)
```

### Summary

Following these documentation standards ensures:

- ✅ Consistent structure and naming across all documentation
- ✅ Easy navigation and discovery of information
- ✅ Clear separation between different types of documentation
- ✅ Proper version control and archiving
- ✅ Professional appearance and maintainability
- ✅ Better collaboration between team members and AI agents

When in doubt, refer to existing documentation in the `docs/` directory as examples, or consult the [Documentation Organization Plan](docs/documentation-organization-plan.md).
