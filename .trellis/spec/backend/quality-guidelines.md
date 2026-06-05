# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Code quality is enforced through automated tooling configured in `pyproject.toml`:

- **Black** (line-length=88) — Code formatting
- **isort** (profile=black) — Import sorting
- **mypy** (python_version=3.8) — Static type checking
- **pytest** — Test runner with custom markers

Target Python version: **3.8+** (no walrus operator, no `dict | dict` syntax).

---

## Forbidden Patterns

| Pattern | Why Forbidden | Alternative |
|---------|--------------|-------------|
| `from module import *` | Pollutes namespace, breaks static analysis | Import specific names |
| Bare `except:` (without specific type) | Hides bugs, catches SystemExit/KeyboardInterrupt | `except Exception:` or specific types |
| `print()` for operational output | Not captured by log infrastructure | `logger.info()` / `click.echo()` |
| Hardcoded API keys or secrets | Security risk, no environment separation | Config file or environment variables |
| f-strings in SQL queries | SQL injection vulnerability | Parameterized queries (`?` placeholders) |
| `type: ignore` without explanation | Hides real type errors | Fix the type or add `# type: ignore[specific-code]` |
| Mutable default arguments | Shared state across calls | `field(default_factory=list)` or `None` + init |

---

## Required Patterns

| Pattern | Where | Example |
|---------|-------|---------|
| Type annotations on all public functions | All modules | `def search(self, query: str, top_k: int = 10) -> List[SearchResult]:` |
| Google-style docstrings | All public classes and methods | See format below |
| `@dataclass` for data containers | Models, results | `CollectResult`, `SearchResult`, `RAGResult` |
| Abstract base classes for extension points | Plugin interfaces | `BaseCollector`, `BaseProcessor`, `BaseReranker` |
| `contextmanager` for resource management | DB transactions, temp files | `_transaction()` |

**Docstring format (Google-style):**

```python
def add_documents(self, ids: List[str], embeddings: List[List[float]]) -> bool:
    """
    Add documents to the collection.

    Args:
        ids: List of document IDs.
        embeddings: List of embedding vectors.

    Returns:
        bool: Whether the operation succeeded.

    Raises:
        ValueError: If ids or embeddings are empty.
    """
```

---

## Testing Requirements

### Configuration (from pyproject.toml)

```toml
# source: pyproject.toml:90-98
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
markers = [
    "integration: marks tests as integration tests (run separately)",
    "slow: marks tests as slow running",
]
```

### Test organization

- Test files mirror source structure: `kb/storage/sqlite_storage.py` → `tests/test_sqlite_storage.py`
- Test classes group related tests: `class TestSQLiteStorageInit:`
- Use `tempfile.TemporaryDirectory()` for isolation — no test writes to real data paths
- Fixtures via `pytest` fixtures or class-level setup

### What needs tests

- All public methods on storage/query/processor classes
- All CLI commands (via Click test runner)
- All API routes (via FastAPI TestClient)
- Edge cases: empty inputs, missing config, unavailable services

### Running tests

```bash
pytest                           # Standard run (excludes integration)
pytest -m integration            # Integration tests only
pytest -m slow                   # Slow tests only
pytest --ignore=tests/test_model_services_integration.py  # Default (in addopts)
```

---

## Code Review Checklist

1. **Formatting** — `black --check .` and `isort --check .` pass
2. **Types** — `mypy kb/` passes (warn_return_any=true, warn_unused_configs=true)
3. **Tests** — New functionality has corresponding test coverage
4. **Docstrings** — Public APIs have Google-style docstrings with Args/Returns/Raises
5. **Error handling** — Follows patterns from `error-handling.md` (Result dataclass or raise ValueError)
6. **Security** — No hardcoded secrets, parameterized SQL, no raw user input in commands
7. **Compatibility** — No Python 3.9+ syntax (no `X | Y` type unions, no walrus `:=`)

---

## Tooling Configuration Reference

```toml
# source: pyproject.toml:77-87
[tool.black]
line-length = 88
target-version = ["py38"]

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
```

---

## Common Mistakes

1. **Using Python 3.9+ features** — The project targets 3.8. Use `Optional[X]` not `X | None`, `List[str]` not `list[str]`, `Dict[str, Any]` not `dict[str, Any]`.

2. **Skipping type annotations on internal helpers** — Even private methods (`_method`) should have return type annotations. mypy checks the full codebase.

3. **Writing tests that depend on external services** — Tests must work offline. Mock external APIs (DashScope, OpenAI) and use temp directories for storage. Mark tests requiring real services with `@pytest.mark.integration`.

4. **Inconsistent import ordering** — Let isort handle it. If manually adding imports, follow: stdlib → third-party → local (`from kb.xxx import`), matching isort's black profile.
