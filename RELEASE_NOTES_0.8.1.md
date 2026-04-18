# Release Notes - v0.8.1

**Release Date**: 2026-04-18

## 🐛 Bug Fixes

### Configuration Management
- **Fixed API key masking issue**: API keys are no longer saved in masked format (e.g., `sk-s******3e32`). The system now detects masked keys and preserves the original value.
- **Fixed configuration sections loss**: When updating LLM or embedding settings, other configuration sections (chunking, storage, query, logging, wiki) are now properly preserved.

## ✨ New Features

### Backup Configuration
Added comprehensive backup configuration support:
- Enable/disable automatic backups
- Configure backup schedule (cron format)
- Set retention period
- Choose backup directory
- Select what to backup (database, files)
- Enable/disable compression

**API Endpoints**:
- `GET /api/settings/backup` - Get backup configuration
- `PUT /api/settings/backup` - Update backup configuration

### Configuration Migration
- Automatic detection of missing configuration keys during `localbrain init setup`
- Seamless merging of new configuration options with existing settings
- Zero data loss during upgrades

## 🔧 Improvements

- Enhanced config loading with deep merge support
- Intelligent masked key detection and preservation
- Better configuration file management
- Improved error handling in settings API

## 📦 Installation

### Python Package (Recommended)
```bash
pip install --upgrade localbrain
```

Or download the wheel package:
```bash
wget http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/packages/localbrain-0.8.1-py3-none-any.whl
pip install localbrain-0.8.1-py3-none-any.whl
```

### Quick Install Script
```bash
# Linux/macOS
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | bash

# Windows (PowerShell)
iwr -useb http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

## 🔄 Upgrade Guide

### For Existing Users

1. **Update the package**:
   ```bash
   pip install --upgrade localbrain
   ```

2. **Re-enter API keys** (if previously saved as masked):
   - Open Web UI: `localbrain web`
   - Navigate to Settings
   - Re-enter your actual API keys
   - Save configuration

3. **Run config migration** (optional):
   ```bash
   localbrain init setup
   ```
   This will automatically add new configuration options while preserving your existing settings.

4. **Configure backup** (optional):
   - Open Web UI Settings
   - Navigate to Backup Configuration tab (coming in next release)
   - Or edit `~/.localbrain/config.yaml` directly

### Breaking Changes
None. This release is fully backward compatible.

## 📝 Configuration Changes

New configuration section added to `config.yaml`:
```yaml
backup:
  enabled: false                       # Enable automatic backups
  schedule: "0 2 * * *"                # Cron schedule (daily at 2 AM)
  retention_days: 30                   # Number of days to keep backups
  backup_dir: ~/.knowledge-base/backups  # Backup directory
  include_db: true                     # Include database in backups
  include_files: true                  # Include collected files
  compression: true                    # Compress backup archives
```

## 🧪 Testing

All features have been thoroughly tested:
- ✅ API key masking and preservation
- ✅ Configuration section preservation
- ✅ Configuration migration
- ✅ Backup configuration API
- ✅ Web server integration

See [TEST_REPORT_0.8.1.md](TEST_REPORT_0.8.1.md) for detailed test results.

## 📚 Documentation

- [CHANGELOG_0.8.1.md](CHANGELOG_0.8.1.md) - Complete changelog
- [QUICK_REFERENCE_0.8.1.md](QUICK_REFERENCE_0.8.1.md) - Quick reference guide
- [SETTINGS_UI_REDESIGN.md](SETTINGS_UI_REDESIGN.md) - Settings UI redesign guide

## 🙏 Acknowledgments

Thanks to all users who reported the configuration management issues. Your feedback helps make localbrain better!

## 📞 Support

- GitHub Issues: https://github.com/your-org/agentic-local-brain/issues
- Documentation: http://localbrain.oss-cn-shanghai.aliyuncs.com/docs/

## 🔜 What's Next

- Settings UI redesign with tabbed interface
- Backup execution functionality
- Backup history and restore features
- Enhanced configuration validation

---

**Full Changelog**: [v0.8.0...v0.8.1](https://github.com/your-org/agentic-local-brain/compare/v0.8.0...v0.8.1)
