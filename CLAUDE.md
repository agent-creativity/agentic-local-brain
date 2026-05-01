# CLAUDE.md

> AI coding agent context for Agentic Local Brain

## Project

Personal knowledge management system — collect, process, query knowledge from files, webpages, bookmarks, papers, emails, notes. CLI (Click) + REST API (FastAPI).

## Tech Stack

- **CLI**: Click | **Web**: FastAPI + Uvicorn
- **Storage**: SQLite (metadata) + ChromaDB (vectors)
- **AI/ML**: DashScope (embedding + LLM), LiteLLM for provider abstraction
- **Config**: YAML at `~/.localbrain/config.yaml`
- **Format**: Black (line 88), isort, mypy, Google-style docstrings

## Directory Layout

```
kb/
├── cli.py                # CLI entry point (thin, delegates to commands/)
├── config.py             # YAML config management
├── config-template.yaml  # Config template with defaults
├── version.py            # Version string
├── self_update.py        # Self-update mechanism
├── collectors/           # BaseCollector → file/webpage/bookmark/paper/email/note
│   └── bookmark_parser.py
├── commands/             # CLI subcommands (collect, search, wiki, mine, backup, doctor, init, manage, topics, self_update, uninstall)
├── processors/           # chunker, embedder, tag_extractor, wiki_compiler, topic_clusterer, entity_extractor, mining_runner/worker, doc_embedding, doc_relation_builder, recommendation, builtin_extractor
├── query/                # keyword/semantic/rag search, retrieval_pipeline, reranker, query_expander, context_builder, conversation, graph_query, topic_query, reading_history, prompt_templates, models
├── scheduler/            # backup_scheduler
├── storage/              # sqlite_storage, chroma_storage
└── web/                  # FastAPI app + routes (dashboard, items, tags, search, wiki, topics, graph, mining, backup, recommendations, settings)
```

## Common Commands

```bash
pytest                          # All tests
pytest tests/test_xxx.py        # Specific test
black kb/ && isort kb/          # Format
mypy kb/                        # Type check
```

## Key Patterns

- **Collectors**: inherit `BaseCollector`, implement `collect()`, `_extract_content()`
- **Processors**: `Embedder`/`TagExtractor` support multi-provider (dashscope, openai, litellm)
- **Results**: dataclasses with `success`, `error`, metadata fields
- **Config**: env vars `DASHSCOPE_API_KEY`, `OPENAI_API_KEY`, `KB_CONFIG_PATH`

## Release

Always use `./scripts/local-build-release.sh` for building/releasing — never run `python -m build` directly.
Before release: update `VERSION`, create `docs/releases/vX.Y.Z/` with release-notes.md + changelog.md, update root CHANGELOG.md.

## Documentation Standards

- All docs under `docs/`: guides/, architecture/, features/, development/, releases/, design/, troubleshooting/
- File naming: lowercase-hyphenated (`quick-start.md`), ADRs use `YYYY-MM-DD-title.md`
- One H1 per doc, logical H2/H3 nesting, relative links, proper syntax highlighting in code blocks
- Root directory: only README.md, README_zh.md, CHANGELOG.md, AGENTS.md, CONTRIBUTING.md, LICENSE
