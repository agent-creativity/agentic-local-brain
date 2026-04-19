# Release Notes - v0.8.2

**Release Date**: 2026-04-19  
**Type**: Minor Release - Documentation & Bug Fixes

## Overview

Version 0.8.2 focuses on documentation reorganization and fixing Ollama embedding integration issues. This release significantly improves project maintainability and resolves a critical configuration issue for Ollama users.

## 🎯 Highlights

### 📚 Complete Documentation Reorganization

We've completely restructured the project documentation to improve discoverability and maintainability:

- **Root Directory Cleanup**: Reduced from 14 files to 6 core files
- **Structured Organization**: 9 well-organized subdirectories
- **Documentation Standards**: Comprehensive guidelines added to AGENTS.md
- **Automated Tools**: Created documentation organization script

**New Documentation Structure**:
```
docs/
├── README.md              # Documentation index
├── guides/                # User guides
├── architecture/          # Architecture design
├── features/              # Feature documentation
├── development/           # Development docs
├── releases/              # Version releases
├── design/                # Design decisions (ADR)
├── troubleshooting/       # Problem solving
├── blog/                  # Blog articles
└── meta/                  # Meta documentation
```

### 🔧 Ollama Embedding Fix

Fixed a critical issue where litellm was passing unsupported `encoding_format` parameter to Ollama:

- **Dual-Layer Filtering**: Implemented filtering at both configuration and API call layers
- **Smart Detection**: Automatically detects `ollama/` prefix and removes incompatible parameters
- **Web UI Update**: Updated default Ollama URL (removed `/v1` suffix)
- **Comprehensive Documentation**: Added detailed technical analysis and troubleshooting guides

**Before**:
```yaml
embedding:
  model: openai/nomic-embed-text
  base_url: http://localhost:11434/v1
  encoding_format: float  # ❌ Causes error with Ollama
```

**After**:
```yaml
embedding:
  model: ollama/nomic-embed-text  # ✅ Use ollama/ prefix
  base_url: http://localhost:11434  # ✅ No /v1 suffix
  # encoding_format automatically filtered
```

## 📦 What's New

### Documentation

- ✅ Reorganized all documentation into structured directories
- ✅ Created comprehensive documentation standards in AGENTS.md
- ✅ Added documentation organization script (`scripts/organize-docs.sh`)
- ✅ Created documentation index with clear navigation
- ✅ Added meta documentation directory for documentation-about-documentation

### Bug Fixes

- ✅ Fixed Ollama embedding `encoding_format` parameter conflict
- ✅ Updated Web UI Ollama configuration defaults
- ✅ Corrected configuration template examples

### Improvements

- ✅ Enhanced embedder.py with provider-specific parameter handling
- ✅ Added comprehensive Ollama troubleshooting documentation
- ✅ Improved configuration validation and error messages

### Testing

- ✅ Added test cases for Ollama embedding parameter filtering
- ✅ Verified parameter handling for different providers (OpenAI, DashScope, Ollama)

## 🔄 Changes by Category

### Added

- Documentation organization script (`scripts/organize-docs.sh`)
- Comprehensive documentation standards in AGENTS.md
- Ollama embedding troubleshooting guides
- Test cases for embedding parameter filtering
- Unified CHANGELOG.md
- Documentation index (docs/README.md)

### Changed

- Reorganized all documentation into structured directories
- Updated Ollama default URL in Web UI (removed `/v1`)
- Enhanced embedder parameter filtering logic
- Improved configuration template with correct Ollama examples

### Fixed

- Ollama embedding `encoding_format` parameter conflict
- Documentation structure and organization
- Configuration template inconsistencies

## 📝 Documentation

### New Documentation

- [Documentation Organization Plan](../meta/documentation-organization-plan.md)
- [Ollama Embedding Troubleshooting](../../troubleshooting/ollama-embedding.md)
- [Ollama Embedding Technical Analysis](../../troubleshooting/ollama-embedding-analysis.md)
- [Web UI Ollama Configuration](../../troubleshooting/ollama-web-ui-config.md)

### Updated Documentation

- [AGENTS.md](../../../AGENTS.md) - Added comprehensive documentation standards
- [Configuration Template](../../../kb/config-template.yaml) - Updated Ollama examples
- [README.md](../../../README.md) - Updated links and structure

## 🔧 Technical Details

### Ollama Embedding Fix Implementation

The fix implements a dual-layer filtering mechanism:

**Layer 1: Configuration Reading** (`embedder.py:556-560`)
```python
# Only add encoding_format for providers that support it
if encoding_format and not model.startswith("ollama/"):
    extra_kwargs["encoding_format"] = encoding_format
```

**Layer 2: API Call** (`embedder.py:468-477`)
```python
# Remove encoding_format for ollama at API call time
if self.model.startswith("ollama/"):
    call_kwargs.pop("encoding_format", None)
elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
    call_kwargs["encoding_format"] = "float"
```

This ensures that even if `encoding_format` is specified in configuration, it will be automatically filtered out for Ollama models.

## 🚀 Upgrade Guide

### From v0.8.1 to v0.8.2

This is a **non-breaking** release. No migration steps required.

#### Optional: Update Ollama Configuration

If you're using Ollama for embeddings, update your configuration:

```yaml
# Old configuration (still works, but not optimal)
embedding:
  provider: litellm
  model: openai/nomic-embed-text
  base_url: http://localhost:11434/v1

# New recommended configuration
embedding:
  provider: litellm
  model: ollama/nomic-embed-text  # Use ollama/ prefix
  base_url: http://localhost:11434  # Remove /v1 suffix
```

The system will automatically filter incompatible parameters regardless of your configuration.

## 📊 Statistics

- **Commits**: 2 major commits
- **Files Changed**: 52 files
- **Lines Added**: 2,688+
- **Lines Removed**: 19
- **Documentation Files**: 29 files reorganized
- **New Directories**: 9 documentation subdirectories

## 🙏 Acknowledgments

Special thanks to all contributors who helped identify and resolve the Ollama embedding issue.

## 📅 Next Steps

Looking ahead to v0.8.3:
- Continue improving documentation
- Add more provider-specific optimizations
- Enhance error messages and validation

## 🔗 Links

- [Full Changelog](changelog.md)
- [GitHub Release](https://github.com/agent-creativity/agentic-local-brain/releases/tag/v0.8.2)
- [Documentation](../../README.md)
- [Issue Tracker](https://github.com/agent-creativity/agentic-local-brain/issues)

---

**Installation**:
```bash
pip install --upgrade localbrain
```

**Verify Version**:
```bash
kb --version
```
