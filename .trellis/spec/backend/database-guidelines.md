# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The project uses a **dual-storage architecture**:

- **SQLite** (`kb/storage/sqlite_storage.py`) — Structured metadata, relationships, full-text search (FTS5)
- **ChromaDB** (`kb/storage/chroma_storage.py`) — Vector embeddings for semantic similarity search

Both are accessed through dedicated storage classes. There is no ORM — all SQLite queries use raw `sqlite3` with parameterized SQL. ChromaDB is accessed through its Python client SDK.

---

## Query Patterns

### SQLite: Transaction Context Manager

All write operations must use the `_transaction()` context manager:

```python
# source: kb/storage/sqlite_storage.py:72-83
@contextmanager
def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
    """Transaction context manager."""
    cursor = self.conn.cursor()
    try:
        yield cursor
        self.conn.commit()
    except Exception:
        self.conn.rollback()
        raise
    finally:
        cursor.close()
```

Usage pattern:

```python
with self._transaction() as cursor:
    cursor.execute(
        "INSERT INTO knowledge (id, title, content_type) VALUES (?, ?, ?)",
        (id, title, content_type)
    )
```

### SQLite: Read Queries

Read queries use `self.conn.execute()` directly (no transaction needed):

```python
row = self.conn.execute(
    "SELECT * FROM knowledge WHERE id = ?", (knowledge_id,)
).fetchone()
```

### ChromaDB: Collection Operations

ChromaDB uses a single collection with cosine similarity:

```python
# source: kb/storage/chroma_storage.py:84-88
self.collection = self.client.get_or_create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"}
)
```

Document operations use batch APIs:

```python
self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
results = self.collection.query(query_embeddings=[embedding], n_results=top_k)
```

---

## Migrations

Schema migrations use the **try-ALTER-TABLE-catch** pattern. Each migration is idempotent:

```python
# source: kb/storage/sqlite_storage.py:85-100
def _migrate_schema(self) -> None:
    """Add new columns to existing databases."""
    cursor = self.conn.cursor()
    try:
        cursor.execute("ALTER TABLE knowledge ADD COLUMN content_hash TEXT")
        self.conn.commit()
    except Exception:
        pass  # Column already exists
    finally:
        cursor.close()
```

**Rules for new migrations:**
1. Each `ALTER TABLE` must be wrapped in its own try/except (one statement per block)
2. The except clause catches silently — the column/table may already exist
3. All schema creation uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`
4. Migrations run on every startup via `_migrate_schema()` called from `__init__`

> ⚠️ TODO: No migration version tracking exists. As the schema grows, consider a migration registry to avoid re-running all ALTER statements on every startup.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | `snake_case`, plural or domain noun | `knowledge`, `tags`, `chunks`, `entities` |
| Association tables | `{table1}_{table2}` | `knowledge_tags`, `entity_mentions` |
| Columns | `snake_case` | `content_type`, `collected_at`, `knowledge_id` |
| Foreign keys | `{referenced_table_singular}_id` | `knowledge_id`, `tag_id`, `entity_id` |
| Indexes | `idx_{table}_{column(s)}` | `idx_knowledge_content_type`, `idx_entity_relations_composite` |
| FTS tables | `{source_table}_fts` | `knowledge_fts` |
| Triggers | `{table}_{ai/ad/au}` (after insert/delete/update) | `knowledge_ai`, `knowledge_ad`, `knowledge_au` |

---

## FTS5 Full-Text Search

The project uses SQLite FTS5 with content-sync triggers:

```python
# source: kb/storage/sqlite_storage.py:160-166
CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    title,
    summary,
    content='knowledge',
    content_rowid='rowid'
)
```

**Key patterns:**
- FTS table is synced via INSERT/DELETE/UPDATE triggers (not manual rebuild)
- Uses `content=` table reference for external content mode
- Query with `MATCH` operator and `bm25()` for ranking

---

## Connection Configuration

```python
# source: kb/storage/sqlite_storage.py:62-69
self._conn = sqlite3.connect(
    str(self.db_path),
    check_same_thread=False  # Required: accessed from multiple threads (CLI + web)
)
self._conn.row_factory = sqlite3.Row  # Dict-like row access
self._conn.execute("PRAGMA foreign_keys = ON")  # Enforce FK constraints
```

---

## Common Mistakes

1. **Forgetting parameterized queries** — Never use f-strings or `.format()` in SQL. Always use `?` placeholders:
   ```python
   # WRONG
   cursor.execute(f"SELECT * FROM knowledge WHERE id = '{id}'")
   # CORRECT
   cursor.execute("SELECT * FROM knowledge WHERE id = ?", (id,))
   ```

2. **Writing without `_transaction()`** — All INSERT/UPDATE/DELETE must use the transaction context manager for proper rollback on failure.

3. **Calling `self.conn.commit()` outside `_transaction()`** — Commit is handled by the context manager. Manual commits bypass rollback safety.

4. **Using `check_same_thread=True` (default)** — The app serves both CLI and web API, so the connection must allow multi-thread access.

5. **Adding a migration without idempotency** — Every ALTER TABLE must be wrapped in try/except. Never assume the column doesn't exist.
