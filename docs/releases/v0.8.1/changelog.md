# Changelog for v0.8.1

## New Features

### Backup Configuration
- Added backup configuration section to system settings
- New configuration options:
  - `backup.enabled`: Enable/disable automatic backups
  - `backup.schedule`: Cron schedule for automatic backups (default: daily at 2 AM)
  - `backup.retention_days`: Number of days to keep backups (default: 30)
  - `backup.backup_dir`: Backup directory path
  - `backup.include_db`: Include database in backups
  - `backup.include_files`: Include collected files in backups
  - `backup.compression`: Enable compression for backup archives

### Settings UI Redesign
- Redesigned settings page with tabbed interface:
  - **Model Configuration**: LLM and Embedding settings
  - **Backup Configuration**: Backup settings
  - **System Diagnostics**: System health checks
- Improved organization and navigation
- Better user experience with clear separation of concerns

### Configuration Migration
- Added automatic config migration during `localbrain init setup`
- Detects missing configuration keys and merges them from defaults
- Ensures upgrades don't lose new configuration options
- Preserves existing user settings while adding new keys

## Bug Fixes

### Configuration Management

#### 1. Fixed API Key Masking Issue
**Problem**: When saving configuration through the Web UI, API keys were being saved in masked format (e.g., `sk-s******************************3e32`) instead of the actual key value.

**Root Cause**: 
- The Web UI displays masked API keys for security
- After saving, the frontend updates its local state with the masked key from the server response
- On subsequent saves, the masked key was sent to the backend and saved to the config file

**Solution**:
- Added `_is_masked_key()` function to detect if an incoming API key contains asterisks
- Modified `update_llm_settings()` and `update_embedding_settings()` to preserve the existing API key when a masked key is received
- This allows users to update other settings (provider, model, base_url) without needing to re-enter the API key

**Files Changed**:
- `kb/web/routes/settings.py`: Added masked key detection and preservation logic

#### 2. Fixed Configuration Section Loss
**Problem**: When updating LLM or embedding settings via Web UI, other configuration sections (chunking, storage, query, logging, wiki) were being lost from the config file.

**Root Cause**:
- `_load_raw_config()` only loaded the existing config file without merging with default configuration
- If the config file was incomplete (missing sections), those sections would be lost when saving

**Solution**:
- Modified `_load_raw_config()` to merge the file config with `DEFAULT_CONFIG`
- Added `_deep_merge_dict()` helper function for proper nested dictionary merging
- Modified `update_llm_settings()` and `update_embedding_settings()` to use `.update()` instead of replacing the entire config section

**Files Changed**:
- `kb/web/routes/settings.py`: Enhanced config loading and merging logic

## API Changes

### New Endpoints
- `GET /api/settings/backup` - Get current backup configuration
- `PUT /api/settings/backup` - Update backup configuration

### Request/Response Models
- Added `BackupConfigRequest` model for backup configuration updates
- Backup settings response includes all backup configuration fields

## Files Modified

### Backend
- `kb/config.py`: Added backup configuration to DEFAULT_CONFIG
- `kb/config-template.yaml`: Added backup configuration section
- `kb/web/routes/settings.py`: 
  - Fixed API key masking and config preservation
  - Added backup configuration endpoints
  - Enhanced config loading with default merging
- `kb/commands/init.py`: Added config migration logic

### Frontend
- `kb/web/static/index.html`: Settings UI redesign (see SETTINGS_UI_REDESIGN.md for implementation guide)

### Documentation
- `SETTINGS_UI_REDESIGN.md`: Detailed implementation guide for settings UI changes
- `CHANGELOG_0.8.1.md`: This file

## Upgrade Notes

### For Users with Existing Installations

1. **API Key Issue**: If you have already saved masked API keys in your config file:
   - Update to v0.8.1
   - Open the Web UI settings page
   - Re-enter your actual API keys
   - Save the configuration
   - The system will now properly preserve the real API key for future updates

2. **Configuration Migration**: When you run `localbrain init setup` after upgrading:
   - The system will automatically detect missing configuration keys
   - New configuration options (like backup settings) will be added
   - Your existing settings will be preserved

3. **Backup Configuration**: The new backup feature is disabled by default:
   - Navigate to Settings → Backup Configuration tab
   - Enable automatic backups if desired
   - Configure schedule and retention settings

### For Developers

1. **Config Loading**: Always use `_load_raw_config()` which now merges with defaults
2. **API Key Handling**: Use `_is_masked_key()` to detect masked keys before saving
3. **Config Updates**: Use `.update()` on existing config sections instead of replacing them
4. **Migration**: Add new config keys to `DEFAULT_CONFIG` in `kb/config.py`

## Testing

A test script has been added to verify:
- API key masking works correctly
- Environment variables (${VAR_NAME}) are preserved without masking
- Masked keys are properly detected
- Short keys are fully masked

## Breaking Changes

None. This release is fully backward compatible.

## Known Issues

None.

## Contributors

- Configuration management fixes
- Backup configuration feature
- Settings UI redesign
- Config migration system
