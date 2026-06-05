# Error Handling

> How errors are handled in this project.

---

## Overview

The project uses two primary error handling patterns:

1. **Result dataclass pattern** — For collector/processor operations that may partially succeed. Errors are captured in a `success`/`error` field pair, never raised.
2. **Exception raising** — For parameter validation and unrecoverable failures. Uses standard Python exceptions (`ValueError`, `ImportError`), no custom exception hierarchy.

There is no global exception hierarchy. The project relies on standard library exceptions and dataclass-based result types.

---

## Error Types

The project does **not** define custom Exception subclasses. Standard exceptions used:

| Exception | When Used | Example Location |
|-----------|-----------|-----------------|
| `ValueError` | Invalid arguments, empty inputs, unsupported config | `query/rag.py`, `query/keyword_search.py` |
| `ImportError` | Optional dependency not installed | `storage/chroma_storage.py`, `query/rag.py` |
| `Exception` | Wrapped operation failures (re-raised with context) | `query/rag.py:261` |
| `HTTPException` | FastAPI route error responses | `web/routes/*.py` |

---

## Error Handling Patterns

### Pattern 1: Result Dataclass (Collectors/Processors)

Operations that can partially succeed return a result object instead of raising:

```python
# source: kb/collectors/base.py:16-40
@dataclass
class CollectResult:
    success: bool
    file_path: Optional[Path] = None
    title: Optional[str] = None
    word_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None  # Error message if success=False
    content_hash: Optional[str] = None
    summary: Optional[str] = None
```

Callers check `result.success` rather than catching exceptions:

```python
result = collector.collect(source)
if not result.success:
    logger.error(f"Collection failed: {result.error}")
    return
# proceed with result.file_path, result.title, etc.
```

### Pattern 2: Raise on Validation (Query/Storage Layer)

Input validation raises immediately:

```python
# source: kb/query/keyword_search.py:56-59
if not self.data_dir.exists():
    raise ValueError(f"Data directory does not exist: {self.data_dir}")
if not self.data_dir.is_dir():
    raise ValueError(f"Data path is not a directory: {self.data_dir}")
```

### Pattern 3: Progressive Fallback (RAG Query)

For operations with multiple strategies, use progressive degradation:

```python
# source: kb/query/rag.py:374-423
def query_with_fallback(self, question, tags=None, top_k=None) -> RAGResult:
    """Progressive degradation: RAG -> semantic only -> keyword only -> error message."""
    # Level 1: Full RAG (LLM + semantic search)
    if self.llm_available:
        try:
            return self.query(question, tags, top_k)
        except Exception as e:
            logger.warning(f"[降级] RAG LLM 生成失败: {e}，降级到纯语义搜索模式")

    # Level 2: Semantic search only (no LLM answer generation)
    if self.semantic_search is not None:
        try:
            search_results = self.semantic_search.search(question, tags, effective_top_k)
            # ...return results without AI summary
        except Exception as e:
            semantic_error = e

    # Level 3: Keyword search fallback
    # Level 4: Return error message (never raise)
```

---

## API Error Responses

FastAPI routes use `HTTPException` with two patterns:

**Validation errors (400):**
```python
# source: kb/web/routes/mining.py:41
raise HTTPException(status_code=400, detail="mode must be 'incremental' or 'full'")
```

**Internal failures (500):**
```python
# source: kb/web/routes/dashboard.py:34
raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
```

**Convention:** The `detail` field is a human-readable string. No structured error codes or error body schema is used.

> ⚠️ TODO: Consider a structured error response format (e.g., `{"error": {"code": "...", "message": "..."}}`) for API consumers.

---

## When to Raise vs Return Result

| Context | Pattern | Rationale |
|---------|---------|-----------|
| Collector/Processor operations | Return `*Result` dataclass | Partial success possible; caller decides how to handle |
| Input validation (bad args) | `raise ValueError` | Fail fast, caller has a bug |
| Missing dependency | `raise ImportError` | Unrecoverable at runtime |
| FastAPI routes | `raise HTTPException` | Framework convention |
| Multi-strategy operations | Progressive fallback | Always return something useful |

---

## Common Mistakes

1. **Raising exceptions in collectors** — Collectors must return `CollectResult(success=False, error="...")` instead of raising. The CLI/web layer iterates multiple sources and must continue on individual failures.

2. **Bare `except:` without re-raise** — Only acceptable in migration code (`_migrate_schema`) where the exception means "already migrated". Everywhere else, catch specific exceptions or re-raise.

3. **Swallowing errors silently** — When catching exceptions in fallback paths, always `logger.warning()` or `logger.error()` before falling through. Silent failures make debugging impossible.

4. **Using generic `Exception` as flow control** — The migration pattern (`try: ALTER TABLE; except: pass`) is an exception to the rule, not a general pattern. For normal code, check state before acting.

5. **Exposing internal errors to API consumers** — Route handlers wrap internal exceptions in `HTTPException`. Never let raw tracebacks reach the client.
