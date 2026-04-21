---
name: localbrain-collect
version: 0.7.1
description: Collect knowledge from multiple sources (files, webpages, papers, emails, bookmarks, notes) into a local knowledge base powered by Agentic Local Brain. Features smart intent recognition to automatically choose the right collection type, and auto-extraction of tags and summaries.
---

# Knowledge Collect (LocalBrain) v0.6.1

## Overview

This skill enables AI agents to collect, save, and archive knowledge from various sources into a local knowledge base. It supports automatic extraction of tags and summaries using a 3-tier fallback system, making knowledge management effortless.

**Supported Sources:**
- Files (PDF, Markdown, text)
- Webpages
- Academic papers (arXiv or URLs)
- Emails (.eml or .mbox)
- Bookmarks
- Quick notes

**Key Features:**
- Automatic tag extraction and summarization
- Duplicate detection and skip-existing support
- Web interface for browsing collected knowledge
- Statistics dashboard

## Prerequisites

1. **Check if localbrain is installed**

   First, try to find localbrain in PATH:
   ```bash
   # macOS/Linux
   which localbrain
   # Windows (PowerShell)
   Get-Command localbrain -ErrorAction SilentlyContinue
   ```

   - **If found**: localbrain is available. Skip to step 3.

   - **If not found in PATH**: Check the default installation location:
     ```bash
     # macOS/Linux
     test -x "$HOME/.localbrain/bin/localbrain" && echo "found" || echo "not found"
     # Windows (PowerShell)
     Test-Path "$env:USERPROFILE\.localbrain\bin\localbrain.exe"
     ```

     - **If found**: Add it to PATH for the current session and verify:
       ```bash
       # macOS/Linux
       export PATH="$HOME/.localbrain/bin:$PATH"
       localbrain --version
       # Windows (PowerShell)
       $env:PATH = "$env:USERPROFILE\.localbrain\bin;$env:PATH"
       localbrain --version
       ```
       
       > **Note**: This is a common issue with desktop AI agents (OpenClaw, Cursor, etc.) whose subprocess doesn't inherit shell profile PATH settings (`~/.zshrc` on macOS/Linux, User PATH on Windows). The installation exists, but PATH needs to be set manually for this session.

     - **If not found**: Proceed to step 2 to install.

2. **Install localbrain (if not installed)**

   **Recommended: Python one-liner installer** (requires Python 3.8+):
   ```bash
   # macOS/Linux
   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
   # Windows (PowerShell)
   irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
   ```

   This creates a virtual environment at `~/.localbrain/venv` and installs localbrain there.

   **Alternative: Binary installer** (macOS/Linux only, for systems without Python):
   ```bash
   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
   ```

   After installation, add to PATH and verify:
   ```bash
   # macOS/Linux
   export PATH="$HOME/.localbrain/bin:$PATH"
   localbrain --version
   # Windows (PowerShell)
   $env:PATH = "$env:USERPROFILE\.localbrain\bin;$env:PATH"
   localbrain --version
   ```

3. **First-time setup** (run once):
   ```bash
   localbrain init setup
   ```

   Options:
   - `--no-sample` - Skip sample data creation

## Trigger Conditions

Activate this skill when users express intent to:

- Save/collect/archive a file, webpage, article, paper, email, or note
- Save bookmarks to their knowledge base
- Check knowledge base statistics or status
- Start/stop the knowledge base web interface
- Initialize the knowledge base for first-time use
- Save/collect content to their knowledge base (知识库)

**Trigger Keywords/Phrases:**
- "save to knowledge base"
- "collect this"
- "add to local brain"
- "archive this"
- "save bookmark"
- "knowledge base stats"
- "start knowledge base"
- "localbrain"
- "store this for later"
- "保存到知识库" (save to knowledge base)
- "收藏到知识库" (collect to knowledge base)
- "存到知识库"
- "加入知识库"
- "knowledge base"
- "save to kb"

## Intent Recognition (CRITICAL)

When a user's request is ambiguous, use the following decision rules to choose the correct collection type. **The order of evaluation matters — check from top to bottom and use the FIRST match.**

### Decision Flow

```
User Input → Is it a local file path?
               ├─ YES → FILE collection
               └─ NO → Is it a URL/link?
                          ├─ NO → Is it short text (note/thought/idea)?
                          │         ├─ YES → NOTE collection
                          │         └─ NO → Ask user to clarify
                          └─ YES → Is the URL an academic paper?
                                     (arXiv, scholar, .edu papers, etc.)
                                     ├─ YES → PAPER collection
                                     └─ NO → Does user explicitly say "bookmark"?
                                                ├─ YES → BOOKMARK collection
                                                └─ NO → WEBPAGE collection (default for URLs)
```

### Detailed Rules

#### 1. FILE — Local filesystem paths
- **Trigger**: Any local filesystem path (absolute or relative), including files generated by the agent during the conversation
- **Examples**: `/Users/me/doc.pdf`, `./output.md`, `~/Downloads/report.txt`, agent-generated files like `/tmp/analysis.md`
- **Key signal**: The source is a path on disk, NOT a URL

#### 2. WEBPAGE — Default for URLs (extract & save content)
- **Trigger**: Any URL/link where the user wants to save/collect/archive the **content**
- **This is the DEFAULT for all URLs** unless a more specific type applies
- **Behavior**: Fetches the page, extracts content, saves as markdown file
- **Examples**:
  - "save this article" + URL → WEBPAGE
  - "collect this" + URL → WEBPAGE  
  - "archive this page" + URL → WEBPAGE
  - "extract content from this link" → WEBPAGE
  - Any URL without further qualification → WEBPAGE

##### Restricted URL Fallback Strategy

Some URLs (e.g., WeChat/微信公众号 articles, Twitter/X posts, pages behind authentication or anti-scraping walls) may fail when `localbrain collect webpage add` tries to fetch them directly. When this happens, the agent SHOULD attempt alternative methods to obtain the page content before giving up:

1. **Use the agent's own browser/fetch capabilities first**: If the agent has access to a browser tool or fetch tool (e.g., `mcp_fetch_fetch`, `agent-browser`, or similar), use it to retrieve the page content directly.
2. **Save the fetched content as a local file, then collect as FILE**: 
   - Fetch/render the page content using the agent's tools
   - Save the content to a temporary markdown file (e.g., `/tmp/webpage_title.md`)
   - Use `localbrain collect file add /tmp/webpage_title.md --title "Original Page Title"` to collect it
3. **Ask the user to provide the content**: If all automated methods fail, ask the user to paste the article text, then save it as a note or file.

**Example workflow for a restricted WeChat article:**
```bash
# Step 1: Agent tries localbrain directly (may fail)
localbrain collect webpage add https://mp.weixin.qq.com/s/xxxxx

# Step 2: If failed, agent uses its own fetch tool to get content
# (agent fetches content via mcp_fetch_fetch or browser tool)

# Step 3: Agent saves fetched content to a temp file
# (agent writes content to /tmp/wechat_article.md)

# Step 4: Collect the local file instead
localbrain collect file add /tmp/wechat_article.md --title "WeChat Article Title"
```

**Key principle**: The goal is to get the content into the knowledge base. If the primary `webpage add` command fails due to access restrictions, fall back to fetching content through the agent's own capabilities and collecting it as a file.

#### 3. PAPER — Academic papers only
- **Trigger**: URL is clearly an academic paper source
- **Key signals**: arXiv URLs (`arxiv.org`), arXiv IDs (`arxiv:2301.12345`), Google Scholar links, `.edu` paper pages, user says "paper" or "论文"
- **Examples**:
  - `https://arxiv.org/abs/2301.12345` → PAPER
  - `https://arxiv.org/pdf/1706.03762` → PAPER
  - "save this paper" + academic URL → PAPER
  - "收藏这篇论文" → PAPER
- **Note**: If unsure whether a URL is a paper, default to WEBPAGE

#### 4. NOTE — Short text, explicit intent only
- **Trigger**: User explicitly says they want to save a "note", "thought" (想法), "idea" (点子), or "memo"
- **Content**: Must be plain text, relatively short (similar to a tweet/weibo post — a few sentences, not a full article)
- **NOT a note if**: Content is long (multiple paragraphs), contains a URL to collect, or is a file path
- **Examples**:
  - "记一个想法：Python的列表推导式比for循环快" → NOTE
  - "save this note: always use type hints in Python" → NOTE
  - "I had an idea: we should refactor the auth module" → NOTE
- **Counter-examples** (NOT notes):
  - "save this" + URL → WEBPAGE (not a note)
  - "remember this article" + URL → WEBPAGE (not a note)
  - Long multi-paragraph text without "note/thought/idea" keyword → Ask user or default to FILE

#### 5. BOOKMARK — Explicit request only, saves link not content
- **Trigger**: User EXPLICITLY says "bookmark" (书签/收藏夹) and wants to save just the link reference, NOT extract page content
- **This is a rare case** — most URL saves should use WEBPAGE
- **Key difference**: Bookmark saves the URL as a reference; Webpage extracts and saves the full page content
- **Examples**:
  - "bookmark this link" → BOOKMARK
  - "add to my bookmarks" → BOOKMARK
  - "加个书签" → BOOKMARK
- **Counter-examples** (use WEBPAGE instead):
  - "save this page" + URL → WEBPAGE
  - "collect this article" + URL → WEBPAGE
  - "archive this" + URL → WEBPAGE

### Ambiguity Resolution

| User says | Correct type | Reasoning |
|-----------|-------------|-----------|
| "save this" + URL | WEBPAGE | Default for URLs is content extraction |
| "collect this" + URL | WEBPAGE | Default for URLs |
| "save this" + file path | FILE | Local path = file |
| "save this paper" + arXiv URL | PAPER | Academic paper signal |
| "save this" + arXiv URL (no "paper" keyword) | PAPER | arXiv domain is strong paper signal |
| "remember this: short text" | NOTE | Short text + "remember" |
| "save a note: short text" | NOTE | Explicit "note" keyword |
| "save this article" + URL | WEBPAGE | "article" = web content |
| "bookmark this" + URL | BOOKMARK | Explicit "bookmark" |
| "save this link" + URL | WEBPAGE | "save link" ≠ "bookmark", extract content |
| "add to bookmarks" + URL | BOOKMARK | Explicit "bookmarks" |
| Agent generated `/tmp/report.md` | FILE | Local file path |
| "保存到知识库" + URL | WEBPAGE | "知识库" triggers skill, URL defaults to webpage |
| "收藏这个到知识库" + file path | FILE | "知识库" triggers skill, local path = file |
| "把这篇文章存到知识库" + URL | WEBPAGE | Article + URL = webpage content extraction |

## Tags and Summary Strategy (CRITICAL)

This skill uses a **hybrid 3-tier approach** for tags and summaries. Understanding this is essential for correct usage.

### Default Behavior: Let Auto-Extraction Handle It

**DO NOT pass `--tags` or `--summary` flags by default.** The system has built-in smart extraction:

1. **Tier 1**: If user explicitly provided tags/summary → use them
2. **Tier 2**: If LLM service (DashScope) is configured → use LLM extraction
3. **Tier 3**: If LLM unavailable → use built-in TF-IDF keyword extraction and extractive summarization

### When to Pass Tags/Summary

Only pass these flags when the user **explicitly provides** specific tags or a summary:

| User Request | Action |
|--------------|--------|
| "save this with tags AI, research" | Pass `--tags AI --tags research` |
| "add this article, tag it as python tutorial" | Pass `--tags python --tags tutorial` |
| "save this with summary: A guide to async Python" | Pass `--summary "A guide to async Python"` |
| "save this webpage" (no tags mentioned) | **DO NOT pass --tags**, let auto-extract handle it |
| "archive this paper" | **DO NOT pass --tags or --summary** |

### Disabling Auto-Extraction

Use `--no-auto-extract` only when the user explicitly wants NO tags/summary:

```bash
localbrain collect file add document.pdf --no-auto-extract
```

## Command Reference

### Initialization

```bash
# First-time setup
localbrain init setup

# Setup without sample data
localbrain init setup --no-sample
```

### File Collection

Add local files (PDF, Markdown, text, code files).

```bash
# Basic usage - let auto-extraction handle tags/summary
localbrain collect file add /path/to/document.pdf

# With explicit tags (only when user provides them)
localbrain collect file add /path/to/document.pdf --tags AI --tags research

# With explicit title and summary
localbrain collect file add /path/to/document.pdf --title "My Document" --summary "A summary"

# Skip if already exists
localbrain collect file add /path/to/document.pdf --skip-existing

# Disable auto-extraction
localbrain collect file add /path/to/document.pdf --no-auto-extract
```

**Options:**
- `--tags/-t` (multiple) - Explicit tags (only if user provides)
- `--title` - Custom title
- `--summary/-s` - Explicit summary (only if user provides)
- `--auto-extract/--no-auto-extract` - Enable/disable auto-extraction (default: enabled)
- `--skip-existing` - Skip if item already exists

### Webpage Collection

Add webpages by URL.

```bash
# Basic usage
localbrain collect webpage add https://example.com/article

# With explicit tags
localbrain collect webpage add https://example.com/article --tags tutorial --tags python

# With custom title
localbrain collect webpage add https://example.com/article --title "Python Tutorial"
```

**Options:** Same as file collection

### Paper Collection

Add academic papers from arXiv or direct URLs.

```bash
# From arXiv ID
localbrain collect paper add arxiv:2401.12345

# From arXiv URL
localbrain collect paper add https://arxiv.org/abs/2401.12345

# From PDF URL
localbrain collect paper add https://example.com/paper.pdf

# With tags
localbrain collect paper add arxiv:2401.12345 --tags deep-learning --tags nlp
```

**Options:** Same as file collection

### Email Collection

Add emails from .eml or .mbox files.

```bash
# Single .eml file
localbrain collect email add /path/to/email.eml

# Mbox file (multiple emails)
localbrain collect email add /path/to/mailbox.mbox

# With tags
localbrain collect email add /path/to/email.eml --tags work --tags important
```

**Options:** Same as file collection

### Bookmark Collection

Add single bookmarks by URL.

```bash
# Basic usage
localbrain collect bookmark add https://example.com

# With title and tags
localbrain collect bookmark add https://example.com --title "Example Site" --tags reference
```

**Options:** Same as file collection

### Note Collection

Add quick text notes.

```bash
# Basic note
localbrain collect note add "This is a quick note"

# With title
localbrain collect note add "Meeting notes from today" --title "Meeting Notes"

# With tags (note: uppercase -T for tags in note command)
localbrain collect note add "Python tips" --title "Python Tips" --tags python --tags tips

# With summary
localbrain collect note add "Important concept" --summary "Key concept to remember"
```

**Options:**
- `--title/-t` - Note title
- `--tags/-T` (multiple) - Tags (note: uppercase T)
- `--summary/-s` - Summary
- `--auto-extract/--no-auto-extract` - Enable/disable auto-extraction
- `--skip-existing` - Skip if note already exists

## Stats and Web Interface

### View Statistics

```bash
# Show knowledge base statistics
localbrain stats
```

Displays:
- Total items in knowledge base
- Items by type (file, webpage, paper, email, bookmark, note)
- Top tags
- Collection timeline

### Web Interface

```bash
# Start web UI (foreground)
localbrain web

# Start on custom port
localbrain web --port 11201

# Start on custom host
localbrain web --host 0.0.0.0

# Start in background (daemon mode)
localbrain web --background
# or
localbrain web -b

# Check web server status
localbrain web --status

# Stop background server
localbrain web --stop

# Enable auto-reload (development)
localbrain web --reload
```

Access the web UI at `http://127.0.0.1:11201` (or your configured port).

## Web API Reference

When the web server is running, the following REST API endpoints are available:

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Get knowledge base statistics |
| GET | `/api/recent` | Get recent items |

### Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items` | List all items (supports pagination) |
| GET | `/api/items/{id}` | Get item by ID |
| PUT | `/api/items/{id}` | Update item |
| DELETE | `/api/items/{id}` | Delete item |

### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tags` | List all tags |
| GET | `/api/tags/{name}/items` | Get items by tag |
| POST | `/api/tags/merge` | Merge tags |
| DELETE | `/api/tags/{name}` | Delete tag |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=...` | Quick search |
| POST | `/api/search/semantic` | Semantic search |
| POST | `/api/rag` | RAG-based Q&A |

### Example

```bash
# Get statistics
curl http://127.0.0.1:11201/api/stats

# Search for items
curl "http://127.0.0.1:11201/api/search?q=python"

# Semantic search
curl -X POST http://127.0.0.1:11201/api/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 10}'
```

## Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Command not found: localbrain` | localbrain not installed or not in PATH | Check `~/.localbrain/bin/` (macOS/Linux) or `%USERPROFILE%\.localbrain\bin\` (Windows). If found, add to PATH: `export PATH="$HOME/.localbrain/bin:$PATH"` (macOS/Linux) or `$env:PATH = "$env:USERPROFILE\.localbrain\bin;$env:PATH"` (Windows). If not found, install via Prerequisites step 2. |
| `Knowledge base not initialized` | First-time use without init | Run `localbrain init setup` |
| `File not found` | Incorrect file path | Verify the file path is correct and accessible |
| `Invalid URL` | Malformed URL | Check the URL format (must include http:// or https://) |
| `Embedding service error` | LLM/embedding service not configured | Set `DASHSCOPE_API_KEY` environment variable |
| `Item already exists` | Duplicate content | Use `--skip-existing` to skip duplicates |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | API key for embeddings and LLM (required for Tier 2 extraction) |
| `KB_CONFIG_PATH` | Custom config file path (optional, defaults to `~/.localbrain/config.yaml`) |

## Troubleshooting and Maintenance

### System Diagnostics

```bash
# Run system diagnostics
localbrain doctor
```

Checks:
- Configuration file status
- Service connectivity (embedding/LLM)
- Installation integrity
- Knowledge base health

### Version Management

```bash
# Update to latest version
localbrain self-update

# Check for updates without installing
localbrain self-update --check

# Rollback to previous version
localbrain self-update --rollback
```

## Common Workflows

### Workflow 1: Save a Web Article

```bash
# User: "Save this article about Python async"
localbrain collect webpage add https://example.com/python-async

# System auto-extracts tags like: python, async, programming
```

### Workflow 2: Archive a PDF with Custom Tags

```bash
# User: "Save this research paper with tags AI and ML"
localbrain collect file add ~/Downloads/research-paper.pdf --tags AI --tags ML
```

### Workflow 3: Quick Note Taking

```bash
# User: "Remember this: Python list comprehensions are faster than for loops"
localbrain collect note add "Python list comprehensions are faster than for loops" --title "Python Performance Tip"
```

### Workflow 4: Start Web Interface

```bash
# User: "Start the knowledge base web interface"
localbrain web --background

# Check it's running
localbrain web --status
```

### Workflow 5: Collection Pipeline

```bash
# User: "Archive these resources: a PDF, a webpage, and a bookmark"

# Step 1: Initialize if needed
localbrain init setup

# Step 2: Collect file
localbrain collect file add ~/docs/important.pdf

# Step 3: Collect webpage
localbrain collect webpage add https://example.com/article

# Step 4: Add bookmark
localbrain collect bookmark add https://example.com/resource --title "Useful Resource"

# Step 5: Check stats
localbrain stats

# Step 6: Start web UI to browse
localbrain web
```

## Related Commands

The following commands are available in localbrain but are managed by other workflows:

### Search Commands

```bash
# Semantic search (requires embedding API)
localbrain search semantic "query" --limit 10

# Keyword search (always available)
localbrain search keyword "term" --limit 10

# RAG-based Q&A (requires embedding AND LLM APIs)
localbrain search rag "question"

# Tag search (always available)
localbrain search tags "python" --limit 20
localbrain search tags "python" "ai" --limit 20  # Multiple tags
```

### Tag Management

```bash
localbrain tag list
localbrain tag merge <source> <target>
localbrain tag delete <tag>
```

### Export

```bash
localbrain export --format json --output items.json
```

### Service Tests

```bash
localbrain test embedding
localbrain test llm
```

### Service Dependencies

| Feature | Embedding API | LLM API |
|---------|---------------|---------|
| Keyword search | Not required | Not required |
| Tag search | Not required | Not required |
| Semantic search | Required | Not required |
| RAG | Required | Required |
| Auto-tag extraction (Tier 2) | Not required | Required |

## Best Practices

1. **Let auto-extraction work**: Don't pass `--tags` or `--summary` unless the user explicitly provides them
2. **Use `--skip-existing` for batch operations**: Prevents duplicates when re-running imports
3. **Initialize once**: Run `localbrain init setup` only for first-time setup
4. **Check stats periodically**: Use `localbrain stats` to monitor knowledge base growth
5. **Use background mode for web**: `localbrain web -b` keeps the server running without blocking the terminal

## Quick Reference Card

```
INIT:
  localbrain init setup [--no-sample]

COLLECT:
  localbrain collect file add <path> [options]
  localbrain collect webpage add <url> [options]
  localbrain collect paper add <source> [options]
  localbrain collect email add <path> [options]
  localbrain collect bookmark add <url> [options]
  localbrain collect note add "<text>" [options]

OPTIONS (for collect commands):
  --tags/-t <tag>       # Only if user provides tags
  --title <title>       # Custom title
  --summary/-s <text>   # Only if user provides summary
  --skip-existing       # Skip duplicates
  --no-auto-extract     # Disable auto-extraction

STATS & WEB:
  localbrain stats
  localbrain web [-b/--background] [--port N] [--host X]
  localbrain web --status
  localbrain web --stop

MAINTENANCE:
  localbrain doctor                        # System diagnostics
  localbrain self-update [--check|--rollback]  # Version management
```
