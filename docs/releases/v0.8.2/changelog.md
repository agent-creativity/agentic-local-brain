# Changelog - v0.8.2

All notable changes in version 0.8.2.

## [0.8.2] - 2026-04-19

### Added

#### Documentation
- **Documentation Organization Script** (`scripts/organize-docs.sh`)
  - Automated script to organize documentation structure
  - Creates backups before reorganization
  - Moves files to appropriate subdirectories
  - Creates documentation index
  - Cleans up temporary files

- **Documentation Standards in AGENTS.md**
  - Comprehensive documentation structure guidelines
  - File naming conventions (lowercase + hyphens, date prefixes for ADR)
  - Document structure standards (heading hierarchy)
  - Creating new documentation workflow
  - Version release documentation requirements
  - Design Decision Records (ADR) template
  - Troubleshooting documentation template
  - Link conventions (relative vs absolute)
  - Code example standards
  - Documentation maintenance guidelines
  - Pre-commit checklist

- **Documentation Index** (`docs/README.md`)
  - Central navigation for all documentation
  - Organized by category (guides, architecture, features, etc.)
  - Quick links to all major documents

- **Unified CHANGELOG.md**
  - Root-level changelog following Keep a Changelog format
  - Links to detailed version-specific changelogs

- **Ollama Troubleshooting Documentation**
  - `docs/troubleshooting/ollama-embedding.md` - Problem description and solution
  - `docs/troubleshooting/ollama-embedding-analysis.md` - Technical deep dive
  - `docs/troubleshooting/ollama-web-ui-config.md` - Web UI configuration updates

- **Meta Documentation** (new `docs/meta/` directory)
  - Documentation organization plan
  - Documentation organization report
  - Quick start guide for documentation organization
  - AGENTS.md documentation update summary

#### Testing
- **Ollama Embedding Test** (`tests/test_ollama_embedding_fix.py`)
  - Tests for Ollama parameter filtering
  - Tests for OpenAI parameter preservation
  - Tests for DashScope parameter preservation
  - Validates dual-layer filtering mechanism

### Changed

#### Documentation Structure
- **Reorganized Root Directory**
  - Before: 14 markdown files
  - After: 6 core files (README.md, README_zh.md, CHANGELOG.md, AGENTS.md, requirements.txt, RELEASE_NOTES.md)
  - Moved 9 files to appropriate subdirectories

- **Reorganized docs/ Directory**
  - Before: 14 files in root
  - After: 1 file in root (README.md), all others in subdirectories
  - Created 9 subdirectories: guides/, architecture/, features/, development/, releases/, design/, troubleshooting/, blog/, meta/

- **File Naming Standardization**
  - Converted UPPERCASE.md to lowercase-with-hyphens.md
  - Added date prefixes to design documents (YYYY-MM-DD-title.md)
  - Organized version documents into releases/vX.Y.Z/ directories

#### Code
- **Enhanced Embedder Parameter Handling** (`kb/processors/embedder.py`)
  - Added dual-layer filtering for Ollama models
  - Configuration layer: Filter at provider initialization (line 556-560)
  - API call layer: Filter before litellm call (line 468-477)
  - Automatic detection of `ollama/` prefix
  - Preserves `encoding_format` for other providers (OpenAI, DashScope)

- **Web UI Ollama Configuration** (`kb/web/static/index.html`)
  - Updated LLM configuration default URL: `http://localhost:11434` (removed `/v1`)
  - Updated Embedding configuration default URL: `http://localhost:11434` (removed `/v1`)
  - Updated placeholder text for both English and Chinese
  - Lines changed: 4826, 4830, 4945, 4949

- **Configuration Template** (`kb/config-template.yaml`)
  - Updated Ollama example to use `ollama/` prefix
  - Changed base_url from `http://localhost:11434/v1` to `http://localhost:11434`
  - Added note about encoding_format not being supported by Ollama

- **Documentation HTML Files**
  - `kb/web/static/docs/configuration.html` - Updated Ollama URLs
  - `kb/web/static/docs/config-reference.html` - Updated Ollama URLs

### Fixed

#### Ollama Embedding Integration
- **encoding_format Parameter Conflict**
  - Issue: litellm was passing `encoding_format: 'float'` to Ollama, which doesn't support this parameter
  - Root cause: litellm defaults to sending encoding_format even when not needed
  - Solution: Implemented dual-layer filtering mechanism
  - Impact: Ollama embedding now works correctly without manual configuration changes

- **Web UI Default Configuration**
  - Issue: Web UI showed incorrect default URL for Ollama (`http://localhost:11434/v1`)
  - Solution: Updated to correct URL (`http://localhost:11434`)
  - Impact: Users get correct configuration by default

- **Configuration Template**
  - Issue: Template showed incorrect Ollama configuration
  - Solution: Updated to use `ollama/` prefix and correct base_url
  - Impact: Users following template get working configuration

### Documentation Changes

#### Moved to docs/design/
- `2026-03-24-knowledge-base-design.md`
- `2026-04-05-v0.6-knowledge-mining-design.md`
- `2026-04-15-backup-design.md`
- `2026-04-16-phase1-delivery-report.md`
- `2026-04-18-config-cleanup.md` (from CONFIG_CLEANUP_SUMMARY.md)
- `2026-04-18-settings-ui-redesign.md` (from SETTINGS_UI_REDESIGN.md)

#### Moved to docs/development/
- `implementation-summary.md` (from IMPLEMENTATION_SUMMARY.md)
- `model-service-test-report.md` (from MODEL_SERVICE_TEST_REPORT.md)
- `test-data-summary.md` (from TEST_DATA_SUMMARY.md)
- `todos.md` (from TODOS.md)

#### Moved to docs/guides/
- `configuration-template.md` (from CONFIG_TEMPLATE.md)

#### Moved to docs/architecture/
- `frontend.md` (from FRONTEND_ARCHITECTURE.md)

#### Moved to docs/features/
- `backup.md` (from backup-feature-design.md)

#### Moved to docs/blog/
- `two-weekends-ai-team.md` (from article-two-weekends-ai-team.md)

#### Moved to docs/releases/v0.8.1/
- `changelog.md` (from CHANGELOG_0.8.1.md)
- `development-summary.md` (from DEVELOPMENT_SUMMARY_0.8.1.md)
- `final-summary.md` (from FINAL_SUMMARY_0.8.1.md)
- `quick-reference.md` (from QUICK_REFERENCE_0.8.1.md)
- `release-notes.md` (from RELEASE_NOTES_0.8.1.md)
- `release-summary.md` (from RELEASE_SUMMARY_0.8.1.md)
- `test-report.md` (from TEST_REPORT_0.8.1.md)

#### Moved to docs/assets/images/screenshots/
- All 7 screenshot files from docs/screenshots/

### Removed

- `docs/.DS_Store` - Temporary macOS file

## Technical Details

### Ollama Embedding Fix

The fix addresses the issue where litellm automatically adds `encoding_format: 'float'` parameter when calling embedding APIs. Ollama's `/api/embed` endpoint doesn't support this parameter, causing errors.

**Implementation**:

1. **Configuration Layer** (`kb/processors/embedder.py:556-560`):
   ```python
   # Only add encoding_format for providers that support it
   if encoding_format and not model.startswith("ollama/"):
       extra_kwargs["encoding_format"] = encoding_format
   ```

2. **API Call Layer** (`kb/processors/embedder.py:468-477`):
   ```python
   # Handle encoding_format based on provider
   if self.model.startswith("ollama/"):
       # Remove encoding_format for ollama
       call_kwargs.pop("encoding_format", None)
   elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
       # Prevent litellm from sending encoding_format=None
       call_kwargs["encoding_format"] = "float"
   ```

**Why Dual-Layer?**
- Configuration layer: Prevents unnecessary parameter passing
- API call layer: Safety net to catch any encoding_format that slips through

### Documentation Organization

The documentation reorganization follows these principles:

1. **Separation of Concerns**: Different types of documents in different directories
2. **Naming Consistency**: Lowercase with hyphens, date prefixes for design docs
3. **Discoverability**: Clear directory names and comprehensive index
4. **Maintainability**: Standards documented in AGENTS.md for AI agents and developers
5. **Scalability**: Room for growth in each category

## Migration Notes

### For Users

No action required. This is a non-breaking release.

**Optional**: If using Ollama, update your configuration to the recommended format:
```yaml
embedding:
  provider: litellm
  model: ollama/nomic-embed-text  # Use ollama/ prefix
  base_url: http://localhost:11434  # Remove /v1 suffix
```

### For Developers

If you have documentation to add:
1. Read the documentation standards in AGENTS.md
2. Place files in appropriate subdirectories
3. Update docs/README.md index
4. Follow naming conventions

## Statistics

- **Total Commits**: 2
- **Files Changed**: 52
- **Insertions**: 2,688+
- **Deletions**: 19
- **Documentation Files Reorganized**: 29
- **New Test Files**: 1
- **New Scripts**: 1

## Contributors

- Claude Opus 4.6 (1M context)

## References

- [Release Notes](release-notes.md)
- [Documentation Organization Plan](../../meta/documentation-organization-plan.md)
- [Ollama Embedding Fix](../../troubleshooting/ollama-embedding.md)
- [GitHub Commits](https://github.com/agent-creativity/agentic-local-brain/compare/v0.8.1...v0.8.2)
