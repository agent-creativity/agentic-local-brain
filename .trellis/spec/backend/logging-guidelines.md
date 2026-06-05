# Logging Guidelines

> How logging is done in this project.

---

## Overview

The project uses Python's standard `logging` module. Every module that logs creates a module-level logger:

```python
import logging
logger = logging.getLogger(__name__)
```

There is no structured logging (JSON), no custom log formatters, and no centralized log aggregation. Logs go to stderr by default. CLI user-facing output uses `click.echo()` separately from logging.

---

## Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Internal operation details useful only during development | `logger.debug(f"Searching for: {question[:50]}...")` |
| `INFO` | Successful completion of significant operations, configuration choices | `logger.info(f"Using litellm for dashscope provider: {self.model}")` |
| `WARNING` | Degraded operation, fallback activated, non-fatal issues | `logger.warning(f"[降级] RAG LLM 生成失败: {e}，降级到纯语义搜索模式")` |
| `ERROR` | Operation failed, but the process continues | `logger.error(f"Failed to generate embedding for {knowledge_id}: {e}")` |
| `CRITICAL` | Not used in this project | — |

**Key distinction: WARNING vs ERROR**
- `WARNING` = the system recovered (fallback worked, retried successfully)
- `ERROR` = the specific operation failed and the caller must handle it

---

## Logger Initialization

Every module follows the same pattern. No exceptions:

```python
# At module level, after imports
import logging

logger = logging.getLogger(__name__)
```

- Always use `__name__` — this produces hierarchical logger names like `kb.query.rag`
- Never use hardcoded strings like `logging.getLogger("rag")`
- Never create loggers inside functions or classes

---

## What to Log

| Event | Level | What to Include |
|-------|-------|----------------|
| Service initialization choices | INFO | Provider name, model name |
| Fallback/degradation activated | WARNING | What failed, what fallback is used |
| External API call failure | ERROR | Error message, which service |
| Search with no results | WARNING | Query (truncated), reason |
| Batch operation progress | INFO | Count processed, total count |
| Configuration loaded | DEBUG | Config path, key settings |

**Logging format conventions:**
- Use f-strings for log messages: `logger.info(f"Processing {count} items")`
- Prefix degradation messages with `[降级]`: `logger.warning(f"[降级] LLM 不可用...")`
- Truncate user content in logs: `question[:50]`, `question[:80]`

---

## What NOT to Log

| Content | Why | Alternative |
|---------|-----|-------------|
| API keys / tokens | Security — keys in logs get leaked | Log the provider name only |
| Full document content | Size — a single log line could be megabytes | Log title or first N chars |
| User PII (emails, names) | Privacy compliance | Log anonymized IDs |
| Passwords or credentials | Security | Never log, never store in plaintext |
| Full embedding vectors | Size — each is 1536+ floats | Log vector dimension and ID |
| Raw HTTP request/response bodies | Size + potential secrets | Log status code and content length |

---

## CLI Output vs Logging

The project separates **user-facing output** from **operational logging**:

| Channel | Tool | Audience | Example |
|---------|------|----------|---------|
| CLI output | `click.echo()` / `click.secho()` | End user in terminal | Progress bars, results, status |
| Logging | `logger.*()` | Developer/operator | Diagnostics, errors, performance |

```python
# CLI layer (commands/): user-facing output
click.echo(f"✅ Collected {result.title} ({result.word_count} words)")

# Business layer (collectors/, query/): operational logging
logger.info(f"Collection completed: {result.file_path}")
```

**Rule:** Code inside `collectors/`, `processors/`, `query/`, `storage/`, `web/` must NEVER use `click.echo()`. Only `commands/` talks to the terminal.

---

## Common Mistakes

1. **Using `print()` instead of `logger` or `click.echo()`** — `print()` bypasses both logging infrastructure and Click's output handling. Use `logger.*()` for operational info or `click.echo()` for user-facing output.

2. **Logging full user content** — Never `logger.info(f"Processing: {full_document_text}")`. Truncate: `logger.info(f"Processing: {text[:100]}...")`.

3. **Using `logging.getLogger("custom_name")` instead of `__name__`** — This breaks the hierarchical logger tree and makes it impossible to filter logs by module.

4. **Logging at the wrong level** — A successful fallback is WARNING (not ERROR). A failed operation that the caller handles is ERROR (not CRITICAL). If the process must exit, that's the only CRITICAL.

5. **Logging inside tight loops without rate limiting** — If processing 10,000 items, don't log each one at INFO. Log batch progress: `logger.info(f"Processed {i}/{total}")` at intervals.
