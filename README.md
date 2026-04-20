# Agentic Local Brain

[English](README.md) | [简体中文](README.zh-CN.md)

> Personal knowledge management system — collect, process, and query knowledge from multiple sources.

## Features

- **Multi-source Collection**: Files (PDF, Markdown, text), webpages, bookmarks, academic papers, emails, and notes
- **Smart Extraction**: 3-tier tag and summary extraction (user-provided → LLM → built-in fallback)
- **Intelligent Search**: Semantic search, keyword search, RAG-based Q&A — with graceful degradation
- **Dual Interface**: CLI (`localbrain`) and REST API (FastAPI)
- **Background Web Server**: Run the web interface as a daemon process
- **Graceful Degradation**: Works without LLM/embedding services using built-in fallback algorithms
- **Cross-Platform**: Flexible installation options — Python package (recommended, no security warnings), standalone binary (no Python required), or install from source
- **Knowledge Mining** (v0.6): Automatic knowledge graph construction, cross-document relationship discovery, topic clustering and trend analysis, smart recommendations based on reading patterns
- **Enhanced Retrieval** (v0.7): Multi-turn RAG chat with query expansion, hybrid retrieval (keyword + semantic fusion via RRF), LLM reranking, knowledge graph context enrichment, configurable prompt templates, and conversation history management
- **LLM Wiki** (v0.7): Auto-generate wiki articles from topic clusters using LLM synthesis, with entity summary cards, wiki-link cross-references (`[[entity-slug]]`), staleness tracking, and automatic recompilation
- **Knowledge Base Backup** (v0.8): Automated backup with multiple storage options (local, Alibaba Cloud OSS, AWS S3), scheduled backups with cron expressions, retention policies, and one-click restore

## Installation

### Option 1: Python Package Install (Recommended)

Works on all platforms without security warnings. Requires Python 3.8+.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

The installer will:
- Check Python 3.8+ is installed
- Create a virtual environment at `~/.localbrain/venv`
- Download and install the wheel package
- Add `localbrain` to your PATH

### Option 2: Binary Install (No Python Required)

For systems without Python. Standalone binary with no dependencies.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**macOS Note:** Binary requires Gatekeeper bypass:
```bash
xattr -cr ~/.localbrain/bin/localbrain
```

### Option 3: Install from Source

For development or custom builds:

```bash
# Clone the repository
git clone <repository-url>
cd agentic-local-brain

# Install in development mode
pip install -e .

# Verify installation
localbrain --version
```

### Post-Installation

After installation, verify and initialize:

```bash
# Check installation
localbrain doctor

# Initialize knowledge base
localbrain init setup
```

### CLI Maintenance Commands

| Command | Description |
|---------|-------------|
| `localbrain --version` | Show installed version |
| `localbrain doctor` | Run system diagnostics and verify configuration |
| `localbrain self-update` | Update to the latest version |
| `localbrain self-update --check` | Check for updates without installing |
| `localbrain self-update --rollback` | Revert to the previous version |
| `localbrain uninstall` | Remove LocalBrain (preserves data) |

## Quick Start

```bash
# Initialize knowledge base
localbrain init

# Collect knowledge
localbrain collect file add ~/documents/paper.pdf
localbrain collect webpage add https://example.com/article
localbrain collect paper add arxiv:2401.12345
localbrain collect email add ~/emails/message.eml
localbrain collect bookmark add https://example.com --tags "reference"
localbrain collect bookmark import --browser chrome
localbrain collect note add "Important insight about ML" --tags "ml" --summary "ML insight note"

# Search
localbrain search semantic "machine learning"
localbrain search keyword "python"
localbrain search rag "What is deep learning?"

# Manage tags
localbrain tag list
localbrain tag merge "ml" "machine-learning"

# Start web interface
localbrain web
localbrain web -b          # background mode
localbrain web --status    # check status
localbrain web --stop      # stop background server
```

## CLI Command Reference

The CLI uses an **object-first (noun-verb) pattern** for consistency. The primary command is `localbrain` (`kb` is available as a backward-compatible alias).

### Collection Commands

All collection commands support:
- `--tags, -t` — Provide tags manually (multiple allowed)
- `--summary, -s` — Provide a summary manually
- `--auto-extract / --no-auto-extract` — Auto-extract tags and summary (default: enabled)
- `--skip-existing` — Skip if document already collected

| Command | Description |
|---------|-------------|
| `localbrain collect file add <path>` | Add local file (PDF, Markdown, text) |
| `localbrain collect webpage add <url>` | Add webpage |
| `localbrain collect paper add <source>` | Add academic paper (arxiv:ID or URL) |
| `localbrain collect email add <path>` | Add email (.eml or .mbox) |
| `localbrain collect bookmark add <url>` | Add a single bookmark |
| `localbrain collect bookmark import --browser <type>` | Import bookmarks from browser |
| `localbrain collect bookmark import --file <html_file>` | Import bookmarks from HTML export |
| `localbrain collect note add <text>` | Create a knowledge note |

### Search Commands

All search operations are unified under the `search` group:

| Command | Description |
|---------|-------------|
| `localbrain search semantic <query>` | Vector-based semantic search |
| `localbrain search keyword <keywords>` | Text-based keyword search |
| `localbrain search rag <question>` | RAG-based Q&A with AI-generated answer |
| `localbrain search tags -t <tag>` | Find items by tags |

### Management Commands

| Command | Description |
|---------|-------------|
| `localbrain init` | Initialize knowledge base and configuration |
| `localbrain config show` | Display current configuration |
| `localbrain stats` | Show knowledge base statistics |
| `localbrain tag list` | List all tags |
| `localbrain tag merge <source> <target>` | Merge two tags |
| `localbrain tag delete <name>` | Delete a tag |
| `localbrain export` | Export knowledge base (markdown or JSON) |
| `localbrain test embedding` | Test embedding service connectivity |
| `localbrain test llm` | Test LLM service connectivity |
| `localbrain mine run` | Run batch knowledge mining (graph, relations, topics, recommendations) |
| `localbrain graph rebuild` | Rebuild knowledge graph |
| `localbrain graph stats` | Show knowledge graph statistics |
| `localbrain topics rebuild` | Rebuild topic clusters |
| `localbrain topics list` | List all topic clusters |
| `localbrain web` | Start web interface (supports -b for background) |
| `localbrain doctor` | Run system diagnostics |
| `localbrain self-update` | Update to latest version |
| `localbrain self-update --check` | Check for updates |
| `localbrain backup create` | Create manual backup |
| `localbrain backup list` | List all backups |
| `localbrain backup restore <filename>` | Restore from backup |
| `localbrain backup delete <filename>` | Delete a backup |
| `localbrain uninstall` | Remove LocalBrain (preserves data) |

## Knowledge Base Backup (v0.8)

Protect your knowledge base with automated backups to local storage or cloud providers:

**Storage Options:**
- **Local** — Store backups in `~/.localbrain/backups/`
- **Alibaba Cloud OSS** — Upload to OSS bucket with automatic lifecycle management
- **AWS S3** — Upload to S3 bucket with versioning support

**Features:**
- Scheduled automatic backups (cron expressions)
- Configurable retention policies (auto-delete old backups)
- One-click restore from any backup
- Background task execution with progress tracking
- Web UI for backup management and cloud storage configuration

**CLI Commands:**
```bash
# Create manual backup
localbrain backup create                    # local storage (default)
localbrain backup create --cloud oss        # upload to OSS
localbrain backup create --cloud s3         # upload to S3

# List backups
localbrain backup list                      # local backups
localbrain backup list --cloud oss          # OSS backups
localbrain backup list --cloud s3           # S3 backups

# Restore from backup
localbrain backup restore backup-20260420-120000.tar.gz
localbrain backup restore backup-20260420-120000.tar.gz --cloud oss

# Delete backup
localbrain backup delete backup-20260420-120000.tar.gz
localbrain backup delete backup-20260420-120000.tar.gz --cloud oss
```

**Web UI Configuration:**

Configure backup settings in the web interface (Settings → Backup):
1. Enable/disable automatic backups
2. Set backup schedule (cron expression, e.g., `0 2 * * *` for daily at 2 AM)
3. Configure retention policy (days to keep backups)
4. Choose storage location (local, OSS, or S3)
5. Configure cloud storage credentials (endpoint, access keys, bucket)

**Configuration Example:**
```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"        # Daily at 2 AM
  retention_days: 30            # Keep backups for 30 days
  storage_location: oss         # local, oss, or s3
  
  # Alibaba Cloud OSS
  oss:
    endpoint: oss-cn-shanghai.aliyuncs.com
    access_key_id: ${OSS_ACCESS_KEY_ID}
    access_key_secret: ${OSS_ACCESS_KEY_SECRET}
    bucket: my-localbrain-backups
  
  # AWS S3
  s3:
    region: us-west-2
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
    bucket: my-localbrain-backups
```

## Smart Extraction

When collecting documents, tags and summary are automatically extracted using a **3-tier fallback strategy**:

```
┌─────────────────────────────────────────────────────┐
│ Tier 1: User-Provided (highest priority)            │
│   --tags "ai,ml" --summary "About ML"               │
│   → Used directly, extraction skipped               │
├─────────────────────────────────────────────────────┤
│ Tier 2: LLM Extraction (DashScope / OpenAI)         │
│   Extracts 3-5 tags + 1-2 sentence summary          │
│   via configurable LLM (qwen-plus, qwen-max, etc.)  │
├─────────────────────────────────────────────────────┤
│ Tier 3: Built-in Extraction (always available)       │
│   Tags: TF-IDF keyword scoring with title boosting   │
│   Summary: Extractive (selects best sentences)       │
│   Zero AI dependencies, works offline                │
└─────────────────────────────────────────────────────┘
```

Disable auto-extraction with `--no-auto-extract`:
```bash
localbrain collect file add paper.pdf --no-auto-extract
```

## Graceful Degradation

The system continues to work when LLM or embedding services are unavailable:

| Scenario | Impact | Fallback |
|----------|--------|----------|
| Embedding unavailable | Semantic search disabled | Falls back to keyword search |
| LLM unavailable | RAG answer generation disabled | Returns search results without AI answer |
| LLM unavailable | Auto-tagging degraded | Uses built-in TF-IDF extraction |
| Both unavailable | Minimal mode | Keyword search + built-in extraction only |

Documents are **always saved** to the filesystem and SQLite, regardless of service availability. Use `localbrain test embedding` and `localbrain test llm` to verify service connectivity.

## Enhanced RAG (v0.7)

The Enhanced RAG system provides a multi-stage retrieval pipeline for more accurate and contextual answers:

```
Query → Query Expansion → Hybrid Retrieval → LLM Reranking → Context Enrichment → Answer Generation
         (rewrite &        (keyword +         (relevance          (entities + topics)
          expand)          semantic RRF)       scoring)
```

**Pipeline Stages:**
1. **Query Expansion** — Rewrites and expands queries for better recall
2. **Hybrid Retrieval** — Combines keyword (FTS5) and semantic search with Reciprocal Rank Fusion (RRF)
3. **LLM Reranking** — Uses LLM to score and reorder results by relevance
4. **Context Enrichment** — Adds entity and topic context from knowledge graph
5. **Context Assembly** — Token-aware context building within budget
6. **Answer Generation** — LLM synthesizes answer with source attribution

**Multi-turn Conversation:**
```bash
# CLI: RAG query (single-turn)
localbrain search rag "What is machine learning?"

# API: Multi-turn chat with session management
POST /api/rag/chat
{
  "query": "Can you elaborate on neural networks?",
  "session_id": "optional-session-id"
}
```

**Configurable Prompt Templates:**
- `general` — Balanced for everyday questions
- `technical` — Optimized for code and technical content
- `academic` — Structured for research topics
- `creative` — Flexible for creative exploration

## LLM Wiki (v0.7)

The LLM Wiki feature synthesizes collected knowledge into readable wiki articles:

**What it does:**
- **Topic Articles** — LLM synthesizes documents from topic clusters into coherent reference articles
- **Entity Summary Cards** — Concise summaries of entities appearing across multiple documents
- **Wiki-link Cross-references** — Articles link to related entities using `[[entity-slug]]` syntax
- **Staleness Tracking** — Automatically detects when source documents change and flags articles for recompilation

**CLI Commands:**
```bash
# Compile wiki articles from topic clusters
localbrain wiki compile                 # compile stale articles only
localbrain wiki compile --force         # recompile all articles

# List compiled articles
localbrain wiki list                    # hierarchical view (default)
localbrain wiki list --flat             # flat list view
localbrain wiki list --type entity      # entity cards only

# View article
localbrain wiki show <article-slug>     # display article content
```

**Web UI:** Browse the wiki through the web interface at the Wiki page, with hierarchical navigation by topic and category.

**Integration with Mining Pipeline:** Wiki compilation is integrated as Step 5 of `localbrain mine run`. Skip with `--skip-wiki` if needed.

## Web API

Start the web server:
```bash
localbrain web                    # foreground
localbrain web -b                 # background (daemon)
localbrain web -b -p 9090         # custom port, background
localbrain web --stop             # stop background server
localbrain web --status           # check server status
```

API endpoints (default: http://localhost:11201):

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Knowledge base statistics |
| GET | `/api/items` | List knowledge items |
| GET | `/api/items/{id}` | Get item by ID |
| GET | `/api/tags` | List all tags |
| POST | `/api/search/keyword` | Keyword search |
| POST | `/api/search/semantic` | Semantic search |
| POST | `/api/search/rag` | RAG query |
| GET | `/api/graph` | Knowledge graph data |
| GET | `/api/knowledge/{id}/related` | Related documents |
| GET | `/api/topics` | Topic clusters |
| GET | `/api/topics/{id}/documents` | Documents in topic |
| GET | `/api/topics/trend` | Topic trends |
| GET | `/api/recommendations` | Smart recommendations |
| POST | `/api/rag/chat` | Enhanced RAG with multi-turn conversation |
| GET | `/api/rag/conversations` | List conversation sessions |
| GET | `/api/rag/conversations/{session_id}` | Get full conversation |
| DELETE | `/api/rag/conversations/{session_id}` | Delete conversation |
| POST | `/api/rag/suggest` | Query suggestions |
| GET | `/api/dashboard/rag-stats` | RAG analytics |
| GET | `/api/wiki/tree` | Wiki structure tree |
| GET | `/api/wiki/articles` | List articles (params: article_type, limit, offset) |
| GET | `/api/wiki/articles/{article_id}` | Get article content |
| GET | `/api/wiki/search` | Search wiki articles |
| GET | `/api/wiki/categories/{category_id}/articles` | Articles by category |
| GET | `/api/wiki/topics/{topic_id}/articles` | Articles by topic |
| GET | `/api/wiki/entities` | List entity cards |
| GET | `/api/wiki/entities/{entity_id}` | Get entity card |
| GET | `/api/wiki/stats` | Wiki statistics |

API docs available at `http://localhost:11201/docs` when server is running.

## Configuration

Configuration file: `~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base

# Update server URL (for self-update functionality)
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float

llm:
  provider: litellm
  model: dashscope/qwen-plus
  api_key: ${DASHSCOPE_API_KEY}

chunking:
  max_chunk_size: 1000
  chunk_overlap: 100

storage:
  type: chroma
  persist_directory: ~/.knowledge-base/db/chroma

query:
  rag:
    top_k: 5
    temperature: 0.3
    max_tokens: 1000
    context_budget: 4000
    context_format: hierarchical
    reranking:
      enabled: true
      top_n_candidates: 20
      weight_retrieval: 0.4
      weight_rerank: 0.6
    conversation:
      max_turns: 20
      session_timeout_minutes: 30
      history_turns_in_context: 5
    templates:
      default: general
  pipeline:
    top_k: 10
    rerank_top_k: 5
    context_budget: 4000

logging:
  log_dir: ""
  level: INFO
  max_bytes: 10485760
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

wiki:
  enabled: true
  max_source_tokens_per_topic: 8000
  entity_card_threshold: 3
  temperature: 0.3
  model: null
  max_article_words: 3000
  max_subcategories: 5
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | Alibaba DashScope API key for embeddings and LLM |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI provider) |
| `KB_CONFIG_PATH` | Custom config file path (optional, defaults to `~/.localbrain/config.yaml`) |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌──────────────┐              ┌─────────────────────┐  │
│  │ CLI (Click)  │              │  Web API (FastAPI)   │  │
│  │ localbrain   │              │  REST + Dashboard    │  │
│  └──────┬───────┘              └──────────┬──────────┘  │
└─────────┼────────────────────────────────┼──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Modules                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Collectors  │  │  Processors  │  │     Query      │  │
│  │ - File      │  │ - Chunker    │  │ - Semantic     │  │
│  │ - Webpage   │  │ - Embedder   │  │ - Keyword      │  │
│  │ - Bookmark  │  │ - TagExtract │  │ - RAG          │  │
│  │ - Paper     │  │ - BuiltinExt │  │ - Graph        │  │
│  │ - Email     │  │ - EntityExt  │  │ - Topics       │  │
│  │ - Note      │  │ - TopicClust │  │ - Recommend    │  │
│  │             │  │ - DocRelation│  │                │  │
│  │             │  │ - Recommend  │  │                │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Storage Layer                         │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │   SQLite Storage    │    │    ChromaDB Storage      │ │
│  │ (Metadata + Tags)   │    │  (Vector Embeddings)     │ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Development

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd agentic-local-brain
```

### Building Python Wheel

Build the Python wheel package for distribution:

```bash
# Build wheel for current version
python scripts/build_wheel.py --version 0.5.0

# Output:
# dist/localbrain-0.5.0-py3-none-any.whl
# dist/localbrain-0.5.0-py3-none-any.whl.sha256
```

The wheel can be installed with:

```bash
pip install dist/localbrain-0.5.0-py3-none-any.whl
```

### Building Binaries

Build standalone binaries for distribution:

```bash
# Build for current platform
python scripts/build_binary.py --version 0.5.0

# Build for specific platform
python scripts/build_binary.py --version 0.5.0 --platform macos-arm64
python scripts/build_binary.py --version 0.5.0 --platform linux-x64
python scripts/build_binary.py --version 0.5.0 --platform win-x64
```

Built binaries are placed in `dist/` directory with SHA256 checksums.

### Building Complete Release

Build the complete release package ready for deployment:

```bash
# Build everything (wheel + current platform binary)
python scripts/build_release.py --version 0.5.0

# Build only Python wheel
python scripts/build_release.py --version 0.5.0 --wheel-only

# Build only binary for specific platform
python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64
```

### Release Structure

The `dist/` directory is organized for easy deployment to your web server:

```
dist/
├── version.json                      # Version info for update checks
├── python_installer/
│   ├── install.sh                    # macOS/Linux Python installer
│   ├── install.ps1                   # Windows PowerShell installer
│   └── packages/
│       ├── localbrain-0.5.0-py3-none-any.whl
│       └── localbrain-0.5.0-py3-none-any.whl.sha256
└── binary_installer/
    ├── install.sh                    # macOS/Linux binary installer
    ├── install.ps1                   # Windows binary installer
    └── releases/
        └── v0.5.0/
            ├── localbrain-macos-arm64
            ├── localbrain-macos-arm64.sha256
            ├── localbrain-macos-x64
            ├── localbrain-linux-arm64
            ├── localbrain-linux-x64
            ├── localbrain-win-x64.exe
            └── ...
```

**Deployment:** Copy the entire `dist/` directory to your web server. Installers download files based on relative paths from `version.json`.

## License

MIT
