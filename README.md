# Agentic Local Brain

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
| `localbrain uninstall` | Remove LocalBrain (preserves data) |

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

## Web API

Start the web server:
```bash
localbrain web                    # foreground
localbrain web -b                 # background (daemon)
localbrain web -b -p 9090         # custom port, background
localbrain web --stop             # stop background server
localbrain web --status           # check server status
```

API endpoints (default: http://localhost:8080):

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

API docs available at `http://localhost:8080/docs` when server is running.

## Configuration

Configuration file: `~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base

# Update server (for self-update functionality)
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

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

logging:
  level: INFO
  max_bytes: 10485760    # 10MB
  backup_count: 5
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
