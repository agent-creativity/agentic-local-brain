# Hybrid Distribution System Design

**Date:** 2026-03-29  
**Author:** AI Assistant  
**Status:** Draft

## Overview

Implement a hybrid distribution system for Agentic Local Brain that provides two installation methods: Python-based (recommended, no security warnings) and Binary-based (for systems without Python). This addresses macOS Gatekeeper security warnings for unsigned binaries by making Python installation the primary method.

## Goals

1. **No Security Warnings** - Python installation bypasses Gatekeeper issues entirely
2. **Backward Compatibility** - Keep binary installer for users without Python
3. **Clean Separation** - Distinct directories for each installation method
4. **Consistent UX** - Same one-liner curl install experience for both methods
5. **Single Source** - One wheel file works across all platforms

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Server                                   │
│  http://localbrain.oss-cn-shanghai.aliyuncs.com                          │
│  ├── version.json                                               │
│  ├── binary_installer/                                          │
│  │   ├── install.sh                                             │
│  │   ├── install.ps1                                            │
│  │   └── releases/                                              │
│  │       └── v0.1.0/                                            │
│  │           ├── localbrain-macos-arm64                         │
│  │           ├── localbrain-linux-x64                           │
│  │           └── localbrain-win-x64.exe                         │
│  └── python_installer/                                          │
│      ├── install.sh                                             │
│      ├── install.ps1                                            │
│      └── packages/                                              │
│          ├── localbrain-0.1.0-py3-none-any.whl                  │
│          └── localbrain-0.1.0-py3-none-any.whl.sha256           │
└─────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
scripts/
├── binary_installer/          # Moved from scripts/
│   ├── install.sh
│   └── install.ps1
├── python_installer/          # NEW
│   ├── install.sh
│   └── install.ps1
├── build.py                   # Existing: build binaries
└── build_wheel.py             # NEW: build wheel
```

## Installation Methods

### Method 1: Python Installer (Recommended)

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows:**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

**Requirements:**
- Python 3.8+ installed on system
- Internet access to download wheel

**Installation Flow:**
1. Detect Python 3.8+ installation
2. Create virtual environment at `~/.localbrain/venv`
3. Download wheel from HTTP server
4. Install wheel into venv via pip
5. Create symlink `~/.localbrain/bin/localbrain` → venv binary
6. Add `~/.localbrain/bin` to PATH
7. Run `localbrain doctor` for verification

### Method 2: Binary Installer (Alternative)

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows:**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**Requirements:**
- No Python required
- **macOS Note:** Requires Gatekeeper bypass:
  ```bash
  xattr -cr ~/.localbrain/bin/localbrain
  ```

**Installation Flow:**
1. Detect OS and architecture
2. Download platform-specific binary
3. Install to `~/.localbrain/bin/localbrain`
4. Add to PATH
5. Run `localbrain doctor` for verification

## Python Installer Script Details

### install.sh (macOS/Linux)

```bash
#!/bin/bash
#
# LocalBrain Python Installer for macOS/Linux
#
# Usage:
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh

set -e

# Configuration
SERVER_URL="${LOCALBRAIN_SERVER:-http://localbrain.oss-cn-shanghai.aliyuncs.com}"
VERSION="${LOCALBRAIN_VERSION:-latest}"
INSTALL_DIR="$HOME/.localbrain"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$INSTALL_DIR/bin"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python 3.8+ is required. Please install Python first."
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        error "Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    fi
    
    info "Python $PYTHON_VERSION detected"
}

# Fetch version info
fetch_version() {
    if [ "$VERSION" = "latest" ]; then
        VERSION_JSON=$(curl -fsSL "$SERVER_URL/version.json")
        VERSION=$(echo "$VERSION_JSON" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        info "Latest version: $VERSION"
    fi
}

# Create virtual environment
create_venv() {
    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at $VENV_DIR"
        info "Removing existing venv for clean install"
        rm -rf "$VENV_DIR"
    fi
    
    info "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
}

# Download and install wheel
install_wheel() {
    WHEEL_URL="$SERVER_URL/python_installer/packages/localbrain-$VERSION-py3-none-any.whl"
    
    info "Downloading wheel from $WHEEL_URL"
    
    # Activate venv and install
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install "$WHEEL_URL"
    deactivate
    
    info "Wheel installed successfully"
}

# Create symlink
create_symlink() {
    mkdir -p "$BIN_DIR"
    
    ln -sf "$VENV_DIR/bin/localbrain" "$BIN_DIR/localbrain"
    chmod +x "$BIN_DIR/localbrain"
    
    info "Created symlink: $BIN_DIR/localbrain"
}

# Add to PATH
add_to_path() {
    # Same logic as binary installer
    # ... (detect shell, add to rc file)
}

# Run verification
run_check() {
    if [ -x "$BIN_DIR/localbrain" ]; then
        info "Running installation check..."
        "$BIN_DIR/localbrain" doctor || true
    fi
}

# Main
main() {
    info "Installing LocalBrain (Python method)..."
    
    check_python
    fetch_version
    create_venv
    install_wheel
    create_symlink
    add_to_path
    run_check
    
    echo ""
    echo -e "${GREEN}✓ LocalBrain installed successfully!${NC}"
    echo ""
    echo "Run 'source ~/.zshrc' or start a new terminal"
    echo "Then run 'localbrain init setup' to initialize"
}

main "$@"
```

### install.ps1 (Windows)

```powershell
#
# LocalBrain Python Installer for Windows
#

param()

$ErrorActionPreference = "Stop"

$ServerUrl = if ($env:LOCALBRAIN_SERVER) { $env:LOCALBRAIN_SERVER } else { "http://localbrain.oss-cn-shanghai.aliyuncs.com" }
$Version = if ($env:LOCALBRAIN_VERSION) { $env:LOCALBRAIN_VERSION } else { "latest" }
$InstallDir = "$env:USERPROFILE\.localbrain"
$VenvDir = "$InstallDir\venv"
$BinDir = "$InstallDir\bin"

function Write-Info($message) { Write-Host "[INFO] $message" -ForegroundColor Green }
function Write-Err($message) { Write-Host "[ERROR] $message" -ForegroundColor Red; exit 1 }

# Check Python
function Check-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Err "Python 3.8+ is required. Please install Python first."
    }
    
    $pythonVersion = (python --version 2>&1).Split()[1]
    Write-Info "Python $pythonVersion detected"
}

# Fetch version
function Fetch-Version {
    if ($Version -eq "latest") {
        $response = Invoke-RestMethod -Uri "$ServerUrl/version.json"
        $script:Version = $response.version
        Write-Info "Latest version: $Version"
    }
}

# Create venv
function Create-Venv {
    if (Test-Path $VenvDir) {
        Write-Info "Removing existing venv..."
        Remove-Item -Recurse -Force $VenvDir
    }
    
    Write-Info "Creating virtual environment..."
    python -m venv $VenvDir
}

# Install wheel
function Install-Wheel {
    $wheelUrl = "$ServerUrl/python_installer/packages/localbrain-$Version-py3-none-any.whl"
    
    Write-Info "Downloading and installing wheel..."
    
    & "$VenvDir\Scripts\Activate.ps1"
    pip install --upgrade pip
    pip install $wheelUrl
    deactivate
}

# Create symlink (Windows: copy)
function Create-BinLink {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Copy-Item "$VenvDir\Scripts\localbrain.exe" "$BinDir\localbrain.exe" -Force
    Write-Info "Binary ready at $BinDir\localbrain.exe"
}

# Add to PATH
function Add-ToPath {
    $path = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($path -notlike "*$BinDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$path", "User")
        Write-Info "Added to PATH"
    }
}

# Main
Write-Info "Installing LocalBrain (Python method)..."

Check-Python
Fetch-Version
Create-Venv
Install-Wheel
Create-BinLink
Add-ToPath

Write-Host ""
Write-Host "✓ LocalBrain installed successfully!" -ForegroundColor Green
Write-Host "Restart your terminal and run 'localbrain init setup'"
```

## Build Wheel Script

### scripts/build_wheel.py

```python
#!/usr/bin/env python3
"""
Build wheel for localbrain.

Usage:
    python scripts/build_wheel.py --version 0.1.0
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_wheel(version: str) -> Path:
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    # Clean dist
    if dist_dir.exists():
        for f in dist_dir.glob("*.whl"):
            f.unlink()
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    
    # Build wheel
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"],
        cwd=project_root,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Wheel build failed with exit code {result.returncode}")
    
    # Find wheel
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No wheel found in dist/")
    
    wheel_path = wheels[0]
    
    # Rename to canonical name
    canonical_name = f"localbrain-{version}-py3-none-any.whl"
    canonical_path = dist_dir / canonical_name
    
    if wheel_path.name != canonical_name:
        wheel_path = wheel_path.rename(canonical_path)
    
    return wheel_path


def generate_checksum(wheel_path: Path) -> Path:
    checksum = calculate_sha256(wheel_path)
    checksum_file = wheel_path.with_suffix(".whl.sha256")
    checksum_file.write_text(f"sha256:{checksum}  {wheel_path.name}\n")
    return checksum_file


def main():
    parser = argparse.ArgumentParser(description="Build localbrain wheel")
    parser.add_argument("--version", required=True, help="Version (e.g., 0.1.0)")
    
    args = parser.parse_args()
    
    print(f"Building localbrain v{args.version} wheel...")
    
    wheel_path = build_wheel(args.version)
    print(f"Wheel built: {wheel_path}")
    
    checksum_file = generate_checksum(wheel_path)
    print(f"Checksum: {checksum_file}")
    
    wheel_size = wheel_path.stat().st_size / 1024
    print(f"Size: {wheel_size:.1f} KB")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Self-Update Integration

The existing `localbrain self-update` command needs to detect installation type:

```python
def get_install_type() -> str:
    """Detect whether installed via Python or binary."""
    install_dir = Path.home() / ".localbrain"
    
    # Check for venv
    if (install_dir / "venv").exists():
        return "python"
    
    # Check for standalone binary
    if (install_dir / "bin" / "localbrain").exists():
        return "binary"
    
    return "unknown"
```

**Update behavior:**
- **Python install:** Re-download wheel, reinstall into venv
- **Binary install:** Re-download binary (existing behavior)

## README Updates

```markdown
## Installation

### Option 1: Python Install (Recommended)

Works on all platforms without security warnings. Requires Python 3.8+.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows:**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

### Option 2: Binary Install (No Python Required)

For systems without Python. Note: macOS requires Gatekeeper bypass.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows:**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**macOS Gatekeeper Bypass:**
```bash
xattr -cr ~/.localbrain/bin/localbrain
```
```

## Implementation Tasks

1. **Create directories**
   - `scripts/binary_installer/`
   - `scripts/python_installer/`

2. **Move existing scripts**
   - Move `scripts/install.sh` → `scripts/binary_installer/install.sh`
   - Move `scripts/install.ps1` → `scripts/binary_installer/install.ps1`

3. **Create Python installer scripts**
   - `scripts/python_installer/install.sh`
   - `scripts/python_installer/install.ps1`

4. **Create build_wheel.py**

5. **Update self-update logic**
   - Detect installation type
   - Update accordingly

6. **Update README.md and README_zh.md**
   - Document both installation methods
   - Python as recommended

7. **Update existing install scripts**
   - Update URL paths to `binary_installer/`

## Testing

1. **Python installer tests**
   - Fresh installation on clean system
   - Installation over existing venv
   - Version upgrade
   - PATH configuration

2. **Binary installer tests**
   - Existing tests remain valid
   - URL path updates

3. **Self-update tests**
   - Update from Python → Python
   - Update from Binary → Binary

## Migration Path

Existing users with binary installation:
- Continue using `localbrain self-update`
- Or reinstall via Python installer for better experience

No breaking changes for existing installations.
