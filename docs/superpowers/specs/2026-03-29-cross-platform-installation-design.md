# Cross-Platform Installation System Design

**Date:** 2026-03-29  
**Author:** AI Assistant  
**Status:** Draft

## Overview

Design a cross-platform installation system for Agentic Local Brain that provides easy installation, clean uninstallation, safe upgrades, and preservation of user data across macOS, Windows, and Linux.

## Goals

1. **Easy Installation** - One-liner install via curl/PowerShell
2. **Clean Uninstallation** - Remove binary without affecting user data
3. **Safe Upgrades** - In-place self-updating without touching knowledge base
4. **Data Preservation** - User data always survives install/uninstall/upgrade cycles
5. **Cross-Platform** - Consistent experience on macOS, Windows, Linux
6. **Enterprise-Friendly** - Works with internal HTTP server and internal Git

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Internal Git Repository                       │
│  (Source Code + CI/CD Pipeline)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Build & Publish
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Internal HTTP Server                          │
│  http://localbrain-internal.yourcompany.com                     │
│  ├── releases/                                                   │
│  │   ├── v0.1.0/                                                 │
│  │   │   ├── localbrain-macos-x64                               │
│  │   │   ├── localbrain-macos-arm64                             │
│  │   │   ├── localbrain-win-x64.exe                             │
│  │   │   ├── localbrain-linux-x64                               │
│  │   │   ├── localbrain-0.1.0.dmg       # Optional              │
│  │   │   ├── localbrain-0.1.0.msi       # Optional              │
│  │   │   └── localbrain_0.1.0_amd64.deb # Optional              │
│  │   ├── v0.2.0/                                                 │
│  │   └── latest → v0.2.0/               # Symlink or redirect   │
│  ├── install.sh                                                  │
│  ├── install.ps1                                                 │
│  └── version.json                        # Latest version info   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Download
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    User Machine                                  │
│  ~/.localbrain/                                                  │
│  ├── bin/localbrain           # Binary location                  │
│  ├── config.yaml              # User configuration               │
│  ├── logs/                    # Application logs                 │
│  └── .install-info            # Version metadata                 │
│  ~/.knowledge-base/          # User data (preserved always)      │
│  ├── db/                                                         │
│  ├── 1_collect/                                                  │
│  └── ...                                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Installation Flow

### One-Liner Install Scripts

**macOS / Linux:**
```bash
curl -fsSL http://localbrain-internal.yourcompany.com/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain-internal.yourcompany.com/install.ps1 | iex
```

### Install Script Steps

1. **Detect OS & Architecture**
   - macOS: x64, arm64 (Apple Silicon)
   - Windows: x64
   - Linux: x64

2. **Download latest binary from HTTP server**
   - GET /releases/latest/localbrain-{os}-{arch}

3. **Install to ~/.localbrain/bin/localbrain**

4. **Add to PATH** (shell config: .zshrc, .bashrc, PowerShell profile)

   **PATH Management Details:**
   - Detect current shell from `$SHELL` environment variable
   - Supported shells: bash, zsh, fish, PowerShell
   - Shell config files:
     - bash: `~/.bashrc`, `~/.bash_profile`
     - zsh: `~/.zshrc`, `~/.zprofile`
     - fish: `~/.config/fish/config.fish`
     - PowerShell: `$PROFILE` (varies by OS)
   - Check for existing PATH entry before adding (avoid duplicates)
   - Entry format: `export PATH="$HOME/.localbrain/bin:$PATH"` (Unix)

5. **Run first-time setup check**
   - `localbrain init --check`

6. **Print success message + next steps**

### Post-Install State

```
~/.localbrain/
├── bin/
│   └── localbrain        # Executable
└── .install-info         # Version metadata (JSON)
```

### .install-info Schema

```json
{
  "version": "0.1.0",
  "install_time": "2026-03-29T10:30:00Z",
  "install_path": "/Users/username/.localbrain/bin/localbrain",
  "source_url": "http://localbrain-internal.yourcompany.com/releases/v0.1.0/localbrain-macos-arm64",
  "platform": "macos",
  "architecture": "arm64",
  "checksum": "sha256:abc123..."
}
```

### version.json Schema (Server-Side)

```json
{
  "version": "0.1.0",
  "released": "2026-03-29",
  "changelog": "https://your-git-server/project/blob/main/CHANGELOG.md",
  "binaries": {
    "macos-x64": {
      "url": "releases/v0.1.0/localbrain-macos-x64",
      "checksum": "sha256:abc123..."
    },
    "macos-arm64": {
      "url": "releases/v0.1.0/localbrain-macos-arm64",
      "checksum": "sha256:def456..."
    },
    "win-x64": {
      "url": "releases/v0.1.0/localbrain-win-x64.exe",
      "checksum": "sha256:ghi789..."
    },
    "linux-x64": {
      "url": "releases/v0.1.0/localbrain-linux-x64",
      "checksum": "sha256:jkl012..."
    }
  }
}
```

**Note:** User data (`~/.knowledge-base/`, `~/.localbrain/config.yaml`) is NOT created during install — only when user runs `localbrain init`.

### First-Run Initialization

After installation, the user must run `localbrain init` to:
1. Create `~/.localbrain/config.yaml` with default configuration
2. Create `~/.knowledge-base/` directory structure
3. Prompt for optional API keys (DashScope, OpenAI)

**`localbrain init --check` vs `localbrain init`:**

| Command | Purpose |
|---------|--------|
| `localbrain init` | Full initialization - creates config, directories, prompts for API keys |
| `localbrain init --check` | Verification only - checks if already initialized, exits with error code if not |

The install script runs `localbrain init --check` to verify system readiness without modifying anything.

The `localbrain doctor` command can verify this initialization has been completed.

## Upgrade Flow

### In-Place Self-Updating

```bash
localbrain self-update
```

### Update Process

1. **Check current version** - Read `~/.localbrain/.install-info`

2. **Query server for latest version**
   ```
   GET /version.json
   { "version": "0.2.0", "released": "2026-03-29" }
   ```

3. **Compare versions**
   - If latest > current: proceed
   - If up to date: print "Already up to date" and exit

4. **Download new binary to temp location**
   ```
   GET /releases/v{version}/localbrain-{os}-{arch}
   ```

5. **Verify download (checksum)**
   ```
   GET /releases/v{version}/checksums.sha256
   ```

6. **Atomic replace**
   - Move old binary to `~/.localbrain/bin/localbrain.old`
   - Move new binary to `~/.localbrain/bin/localbrain`
   - Delete `.old` on success

7. **Update .install-info**

8. **Print changelog summary**

### Rollback

```bash
localbrain self-update --rollback   # Restore previous version from .old
```

### Key Design Principle

**User data is NEVER touched during upgrade** — `~/.knowledge-base/` and `~/.localbrain/config.yaml` remain intact. Only the binary in `~/.localbrain/bin/` is replaced.

### Platform-Specific Binary Replacement

**macOS / Linux:**
- Rename running binary to `.old` (works even while in use on Unix)
- Move new binary into place
- Set executable permission (`chmod +x`)
- `.old` file can be cleaned up on next run

**Windows:**
- Windows locks running executables - cannot replace directly
- **Update Mechanism:**
  1. Download new binary as `localbrain.new` to temp location
  2. Create `.update-pending` marker file containing path to new binary
  3. On next `localbrain` launch:
     - Check for `.update-pending` file
     - If exists: rename `localbrain` → `localbrain.old`, rename `localbrain.new` → `localbrain`
     - Delete `.update-pending` and `localbrain.old`
     - Continue with requested command
  4. If update fails: rollback by keeping `.old` file

**Wrapper Script Alternative (Optional):**
- Create `localbrain.bat` wrapper that checks for updates before running
- More complex but provides seamless updates
- Not required if `.update-pending` mechanism is implemented

### Rollback Limitations

- Only ONE previous version is kept (`.old` file)
- After successful update, `.old` is deleted
- Rollback is only available until the NEXT update completes
- For enterprise environments, consider keeping multiple versions

## Uninstall Flow

### Clean Uninstall

```bash
localbrain uninstall
```

### Uninstall Process

1. **Confirm with user**
   ```
   "This will remove localbrain from your system."
   "Your knowledge base (~/.knowledge-base) will be preserved. Continue? [y/N]"
   ```

2. **Remove binary**
   - `rm ~/.localbrain/bin/localbrain`
   - `rm ~/.localbrain/bin/localbrain.old` (if exists)

3. **Remove PATH entry from shell config**
   - Detect which shell config was modified during install
   - Safe removal algorithm:
     1. Read shell config file
     2. Find line matching: `export PATH="$HOME/.localbrain/bin:$PATH"` or similar
     3. Use exact string match (not regex) to avoid false positives
     4. Remove only the matching line
     5. Write updated config
   - Handle cases where entry doesn't exist (already removed manually)

4. **Remove install metadata**
   - `rm ~/.localbrain/.install-info`

5. **Leave user data untouched**
   - `~/.knowledge-base/` ← PRESERVED
   - `~/.localbrain/config.yaml` ← PRESERVED
   - `~/.localbrain/logs/` ← PRESERVED

6. **Print summary**
   ```
   "localbrain has been uninstalled."
   "Your knowledge base is preserved at:"
   "  - ~/.knowledge-base/"
   "  - ~/.localbrain/config.yaml"
   "To completely remove, run: rm -rf ~/.knowledge-base"
   ```

### Complete Removal (including user data)

For users who want to completely remove all data, manually run:

```bash
rm -rf ~/.knowledge-base ~/.localbrain
```

## Build Pipeline

### PyInstaller Build Configuration

```
Build Machine (macOS, Windows, Linux)

1. Checkout source code
2. Set up Python 3.8+
3. Install dependencies
   pip install -r requirements.txt
   pip install pyinstaller

4. Build with PyInstaller
   pyinstaller --onefile \
     --name localbrain \
     --add-data "kb:kb" \
     --hidden-import chromadb \
     --hidden-import pypdf \
     --hidden-import dashscope \
     --hidden-import openai \
     --collect-all chromadb \
     --collect-all sentence_transformers \
     --define VERSION=$(cat VERSION) \
     kb/cli.py

   **Resources to Embed:**
   - `kb/` package (all Python modules)
   - `config-template.yaml` (default config template)
   - `VERSION` file (version string)

5. Generate checksum
   sha256sum localbrain-{os}-{arch} > checksums.sha256

6. Upload to HTTP server
   releases/v{version}/localbrain-{os}-{arch}
   releases/v{version}/checksums.sha256
```

### Build Artifacts per Release

```
releases/
└── v0.1.0/
    ├── localbrain-macos-x64
    ├── localbrain-macos-arm64
    ├── localbrain-win-x64.exe
    ├── localbrain-linux-x64
    ├── localbrain-0.1.0.dmg        # Optional: macOS installer
    ├── localbrain-0.1.0.msi        # Optional: Windows installer
    ├── localbrain_0.1.0_amd64.deb  # Optional: Linux installer
    └── checksums.sha256
```

### version.json (at server root)

This is the canonical schema - same as defined in the Installation Flow section:

```json
{
  "version": "0.1.0",
  "released": "2026-03-29",
  "changelog": "https://your-git-server/project/blob/main/CHANGELOG.md",
  "binaries": {
    "macos-x64": {
      "url": "releases/v0.1.0/localbrain-macos-x64",
      "checksum": "sha256:abc123..."
    },
    "macos-arm64": {
      "url": "releases/v0.1.0/localbrain-macos-arm64",
      "checksum": "sha256:def456..."
    },
    "win-x64": {
      "url": "releases/v0.1.0/localbrain-win-x64.exe",
      "checksum": "sha256:ghi789..."
    },
    "linux-x64": {
      "url": "releases/v0.1.0/localbrain-linux-x64",
      "checksum": "sha256:jkl012..."
    }
  }
}
```

**Note:** The checksums.sha256 file in each release directory is kept for manual verification only. The canonical checksums are embedded in version.json.

## New CLI Commands

### Commands to Add

```bash
# Version info
localbrain --version              # Show version and build info

# Self-update
localbrain self-update                 # Update to latest version
localbrain self-update --check         # Check if update available (don't install)
localbrain self-update --rollback      # Rollback to previous version

# Uninstall
localbrain uninstall              # Remove binary, preserve data
# To remove all data: rm -rf ~/.knowledge-base ~/.localbrain

# Diagnostics
localbrain doctor                 # Check system health, PATH, config validity
```

### `localbrain doctor` Output Example

```
🔍 LocalBrain Diagnostics

  Version:     0.1.0
  Install:     ~/.localbrain/bin/localbrain
  Config:      ~/.localbrain/config.yaml ✓
  Data Dir:    ~/.knowledge-base ✓
  
  Services:
    Embedding:  DashScope (text-embedding-v4) ✓
    LLM:        DashScope (qwen-plus) ✓
  
  PATH:        ~/.localbrain/bin is in PATH ✓
  
  All checks passed!
```

## Files to Create

### 1. Install Scripts

| File | Purpose |
|------|---------|
| `scripts/install.sh` | macOS/Linux one-liner installer |
| `scripts/install.ps1` | Windows PowerShell installer |

### 2. Build Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Update with PyInstaller build config |
| `scripts/build.py` | Cross-platform build script |
| `localbrain.spec` | PyInstaller spec file |

### 3. CLI Modules

| File | Purpose |
|------|---------|
| `kb/commands/self_update.py` | `localbrain self-update` command |
| `kb/commands/uninstall.py` | `localbrain uninstall` command |
| `kb/commands/doctor.py` | `localbrain doctor` command |

### 4. Version Management

| File | Purpose |
|------|---------|
| `kb/version.py` | Version info embedded in binary |
| `kb/self_update.py` | Self-updating logic |

## Security Considerations

1. **Checksum Verification** - All downloads verified against SHA256 checksums embedded in version.json
2. **HTTPS Recommended** - Use HTTPS for the internal HTTP server if possible
3. **Atomic Replacements** - Binary replacements use atomic operations to prevent corruption
4. **Rollback Support** - Previous version kept as `.old` for quick rollback

## Network Resilience

### Download Retry Logic

- Maximum 3 retry attempts
- Exponential backoff: 1s, 2s, 4s between retries
- Connection timeout: 30 seconds
- Read timeout: 60 seconds per MB

### Partial Download Handling

- Download to temp file first (`localbrain.download`)
- Verify checksum before moving to final location
- Resume not supported (full re-download on failure)

### Server Unavailable

- Print clear error message: "Cannot reach update server"
- Exit with non-zero status code
- Suggest checking network connectivity
- Log server URL for debugging

## Error Handling

### Pre-Flight Checks

Before any installation/update operation:

1. **Disk Space**: Verify at least 200MB free in `~/.localbrain/`
2. **Write Permissions**: Test write access to target directory
3. **Network Connectivity**: Ping server before download
4. **Corrupted Installation**: Check if `.install-info` is valid JSON

### Recovery Procedures

| Scenario | Recovery Action |
|----------|---------------|
| Corrupted `.install-info` | Re-download and reinstall via install script |
| Incomplete download | Delete temp file, retry download |
| Permission denied | Print instructions to fix permissions |
| Binary corrupted | Re-download via `localbrain self-update --force` |
| `.old` file exists from failed update | Prompt to rollback or continue |

### Concurrency Handling

- Use file lock (`~/.localbrain/.lock`) during updates
- Lock file format:
  ```json
  {
    "pid": 12345,
    "started_at": "2026-03-29T10:30:00Z",
    "operation": "update"
  }
  ```
- If lock exists:
  1. Read PID from lock file
  2. Check if process is still running (OS-specific)
  3. If process dead: remove stale lock and proceed
  4. If process alive: wait up to 30 seconds, then exit with message
- Timeout behavior: After 30s, print "Another update in progress, please wait" and exit
- Lock is always removed after operation completes (success or failure)

## Platform-Specific Considerations

### macOS

**Codesigning:**
- Binaries should be codesigned with a developer certificate
- Required for Gatekeeper on macOS Big Sur+
- Command: `codesign --deep --force --verify --sign "Developer ID" localbrain`

**Notarization:**
- Submit binary to Apple for notarization
- Required for distribution outside App Store
- Process can take minutes to hours

**Workaround for Internal Distribution:**
- Users run: `xattr -cr ~/.localbrain/bin/localbrain`
- Or: System Preferences → Privacy → "Open Anyway"

### Windows

**PowerShell Execution Policy:**
- Install script may fail due to execution policy
- Solution: Run with `-ExecutionPolicy Bypass`
- Or: Sign the script with a code signing certificate

**File Locking:**
- Executables cannot be replaced while running
- Use the pending update mechanism described above

**Windows Defender:**
- May flag unsigned binaries
- Add exception for `~/.localbrain/bin/`

### Linux

**Executable Permission:**
- Install script must set `chmod +x` on binary
- Check if user has execute permission on parent directories

**SELinux/AppArmor:**
- May block execution from `~/.localbrain/`
- Users may need to adjust security context

## Internal HTTP Server API Protocol

The internal HTTP server is implemented in a separate repository. This section defines the **GET request API protocol** that the server must support for client downloads.

**Server URL:** `http://localbrain-internal.yourcompany.com` (enterprise internal network)

**Authentication:** None required for download operations (internal network access only)

### API Endpoints

#### 1. Get Version Info

```
GET /version.json
```

Returns current version information.

**Response:**
```json
{
  "version": "0.1.0",
  "released": "2026-03-29",
  "changelog": "https://your-git-server/project/blob/main/CHANGELOG.md",
  "binaries": {
    "macos-x64": {
      "url": "releases/v0.1.0/localbrain-macos-x64",
      "checksum": "sha256:abc123..."
    },
    "macos-arm64": {
      "url": "releases/v0.1.0/localbrain-macos-arm64",
      "checksum": "sha256:def456..."
    },
    "win-x64": {
      "url": "releases/v0.1.0/localbrain-win-x64.exe",
      "checksum": "sha256:ghi789..."
    },
    "linux-x64": {
      "url": "releases/v0.1.0/localbrain-linux-x64",
      "checksum": "sha256:jkl012..."
    }
  }
}
```

#### 2. Download Release Binary

```
GET /releases/{version}/{filename}
```

Download a specific release binary.

**Parameters:**
- `version`: Release version (e.g., `v0.1.0`, `latest`)
- `filename`: Binary filename

**Supported Platforms:**
| Platform | Filename |
|----------|----------|
| macOS Intel | `localbrain-macos-x64` |
| macOS Apple Silicon | `localbrain-macos-arm64` |
| Windows | `localbrain-win-x64.exe` |
| Linux | `localbrain-linux-x64` |

**Response:** Binary file download (`application/octet-stream`)

**Example:**
```
GET /releases/v0.1.0/localbrain-macos-arm64
GET /releases/latest/localbrain-linux-x64
```

#### 3. Download Install Script (macOS/Linux)

```
GET /install.sh
```

Download the bash install script for macOS and Linux.

**Response:** Shell script (`text/x-shellscript`)

#### 4. Download Install Script (Windows)

```
GET /install.ps1
```

Download the PowerShell install script for Windows.

**Response:** PowerShell script (`application/octet-stream`)

#### 5. Health Check (Optional)

```
GET /health
```

Returns server health status.

**Response:**
```json
{
  "status": "healthy"
}
```

### Server Directory Structure

The server should serve files from this directory structure:

```
server-root/
├── version.json                    # Current version info
├── install.sh                      # macOS/Linux installer
├── install.ps1                     # Windows installer
└── releases/
    ├── v0.1.0/
    │   ├── localbrain-macos-x64
    │   ├── localbrain-macos-arm64
    │   ├── localbrain-win-x64.exe
    │   ├── localbrain-linux-x64
    │   └── checksums.sha256
    ├── v0.2.0/
    │   └── ...
    └── latest/ -> v0.2.0/          # Symlink or redirect to latest
```

### Client-Side HTTP Headers

Clients should send these headers:

```
User-Agent: LocalBrain/0.1.0 (macos-arm64)
Accept: application/octet-stream
```

### Error Responses

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 404 | File or version not found |
| 500 | Server error |

**Error Response Body:**
```json
{
  "detail": "Version v0.0.1 not found"
}
```

## Implementation Order

1. Add `--version` flag to CLI
2. Create PyInstaller spec file and test builds
3. Implement `localbrain doctor` command
4. Implement `localbrain self-update` command
5. Implement `localbrain uninstall` command
6. Create install scripts (install.sh, install.ps1)
7. Document the release process
