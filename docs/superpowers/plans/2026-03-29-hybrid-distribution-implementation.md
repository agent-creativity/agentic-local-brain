# Hybrid Distribution System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement hybrid distribution with Python installer (primary) and binary installer (secondary) to avoid macOS Gatekeeper security warnings.

**Architecture:** Reorganize scripts/ into binary_installer/ and python_installer/ directories, add wheel build script, update self-update to detect installation type, and update documentation.

**Tech Stack:** Bash, PowerShell, Python, pip wheel

---

## File Structure

```
scripts/
├── binary_installer/          # NEW directory (move existing)
│   ├── install.sh             # MOVED from scripts/install.sh
│   └── install.ps1            # MOVED from scripts/install.ps1
├── python_installer/          # NEW directory
│   ├── install.sh             # NEW
│   └── install.ps1            # NEW
├── build.py                   # EXISTING (no changes)
└── build_wheel.py             # NEW
```

Files to modify:
- `kb/self_update.py` - Add install type detection
- `README.md` - Update installation section
- `README_zh.md` - Sync Chinese docs

---

## Task 1: Create Directory Structure and Move Binary Installer Scripts

**Files:**
- Create: `scripts/binary_installer/` directory
- Move: `scripts/install.sh` → `scripts/binary_installer/install.sh`
- Move: `scripts/install.ps1` → `scripts/binary_installer/install.ps1`

- [ ] **Step 1: Create binary_installer directory**

```bash
mkdir -p scripts/binary_installer
```

- [ ] **Step 2: Move install.sh to binary_installer/**

```bash
mv scripts/install.sh scripts/binary_installer/install.sh
```

- [ ] **Step 3: Move install.ps1 to binary_installer/**

```bash
mv scripts/install.ps1 scripts/binary_installer/install.ps1
```

- [ ] **Step 4: Update URL references in binary_installer/install.sh**

Change the URL in the Usage comment from:
```bash
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/install.sh | sh
```
to:
```bash
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

Also update the download URL in `download_binary()` function from:
```bash
local url="${SERVER_URL}/releases/v${VERSION}/${filename}"
```
to:
```bash
local url="${SERVER_URL}/binary_installer/releases/v${VERSION}/${filename}"
```

- [ ] **Step 5: Update URL references in binary_installer/install.ps1**

Change the URL in the Usage comment from:
```powershell
#   irm http://localbrain.oss-cn-shanghai.aliyuncs.com/install.ps1 | iex
```
to:
```powershell
#   irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

Also update the download URL in `Download-Binary` function from:
```powershell
$url = "$ServerUrl/releases/v$Version/$filename"
```
to:
```powershell
$url = "$ServerUrl/binary_installer/releases/v$Version/$filename"
```

- [ ] **Step 6: Verify directory structure**

```bash
ls -la scripts/binary_installer/
```

Expected output:
```
install.sh
install.ps1
```

- [ ] **Step 7: Commit binary installer reorganization**

```bash
git add scripts/binary_installer/
git rm scripts/install.sh scripts/install.ps1
git commit -m "refactor: move binary installer scripts to binary_installer directory"
```

---

## Task 2: Create Python Installer Directory

**Files:**
- Create: `scripts/python_installer/` directory
- Create: `scripts/python_installer/install.sh`
- Create: `scripts/python_installer/install.ps1`

- [ ] **Step 1: Create python_installer directory**

```bash
mkdir -p scripts/python_installer
```

- [ ] **Step 2: Write python_installer/install.sh**

Create the file with complete installer script for macOS/Linux:

```bash
#!/bin/bash
#
# LocalBrain Python Installer for macOS/Linux
#
# Usage:
#   curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
#
# Environment variables:
#   LOCALBRAIN_SERVER  - Server URL (default: http://localbrain.oss-cn-shanghai.aliyuncs.com)
#   LOCALBRAIN_VERSION - Version to install (default: latest)

set -e

# Configuration
SERVER_URL="${LOCALBRAIN_SERVER:-http://localbrain.oss-cn-shanghai.aliyuncs.com}"
VERSION="${LOCALBRAIN_VERSION:-latest}"
INSTALL_DIR="$HOME/.localbrain"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$INSTALL_DIR/bin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
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

# Detect shell and config file
detect_shell() {
    SHELL_NAME=$(basename "$SHELL")
    
    case "$SHELL_NAME" in
        zsh) SHELL_RC="$HOME/.zshrc" ;;
        bash) SHELL_RC="$HOME/.bashrc" ;;
        fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
        *) SHELL_RC="$HOME/.profile" ;;
    esac
    
    info "Detected shell: $SHELL_NAME ($SHELL_RC)"
}

# Check if already installed
check_existing() {
    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at $VENV_DIR"
        info "Removing existing venv for clean install"
        rm -rf "$VENV_DIR"
    fi
}

# Fetch version info
fetch_version_info() {
    local url="$SERVER_URL/version.json"
    info "Fetching version info from $url"
    
    VERSION_JSON=$(curl -fsSL "$url")
    
    if [ -z "$VERSION_JSON" ]; then
        error "Failed to fetch version info"
    fi
    
    if [ "$VERSION" = "latest" ]; then
        # Extract version - prefer jq if available, fallback to grep
        if command -v jq &> /dev/null; then
            VERSION=$(echo "$VERSION_JSON" | jq -r '.version')
        else
            VERSION=$(echo "$VERSION_JSON" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
        fi
        info "Latest version: $VERSION"
    fi
}

# Create virtual environment
create_venv() {
    info "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    info "Virtual environment created"
}

# Download and install wheel
install_wheel() {
    WHEEL_URL="$SERVER_URL/python_installer/packages/localbrain-$VERSION-py3-none-any.whl"
    
    info "Downloading wheel from $WHEEL_URL"
    
    # Activate venv and install
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip --quiet
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
    local path_entry="export PATH=\"$HOME/.localbrain/bin:\$PATH\""
    
    # Check if already in PATH
    if echo "$PATH" | grep -q ".localbrain/bin"; then
        info "Already in PATH"
        return
    fi
    
    # Check if entry exists in shell config
    if [ -f "$SHELL_RC" ] && grep -q ".localbrain/bin" "$SHELL_RC"; then
        info "PATH entry already in $SHELL_RC"
        return
    fi
    
    # Add to shell config
    echo "" >> "$SHELL_RC"
    echo "# LocalBrain" >> "$SHELL_RC"
    echo "$path_entry" >> "$SHELL_RC"
    
    info "Added to PATH in $SHELL_RC"
}

# Write install info
write_install_info() {
    local install_info="$INSTALL_DIR/.install-info"
    local install_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > "$install_info" << EOF
{
  "version": "$VERSION",
  "install_time": "$install_time",
  "install_path": "$BIN_DIR/localbrain",
  "install_type": "python",
  "source_url": "$SERVER_URL/python_installer/packages/localbrain-$VERSION-py3-none-any.whl",
  "venv_path": "$VENV_DIR"
}
EOF
    
    info "Install info written to $install_info"
}

# Run first-time check
run_check() {
    if [ -x "$BIN_DIR/localbrain" ]; then
        info "Running installation check..."
        "$BIN_DIR/localbrain" doctor || true
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}✓ LocalBrain installed successfully!${NC}"
    echo ""
    echo "Version: $VERSION"
    echo "Type:    Python (venv)"
    echo "Binary:  $BIN_DIR/localbrain"
    echo "Venv:    $VENV_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'source $SHELL_RC' or start a new terminal"
    echo "  2. Run 'localbrain init setup' to initialize"
    echo "  3. Run 'localbrain doctor' to verify installation"
    echo ""
}

# Main
main() {
    info "Installing LocalBrain (Python method)..."
    
    check_python
    detect_shell
    check_existing
    fetch_version_info
    create_venv
    install_wheel
    create_symlink
    write_install_info
    add_to_path
    run_check
    print_success
}

main "$@"
```

- [ ] **Step 3: Make install.sh executable**

```bash
chmod +x scripts/python_installer/install.sh
```

- [ ] **Step 4: Write python_installer/install.ps1**

Create the Windows PowerShell installer:

```powershell
#
# LocalBrain Python Installer for Windows
#
# Usage:
#   irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
#
# Environment variables:
#   $env:LOCALBRAIN_SERVER  - Server URL
#   $env:LOCALBRAIN_VERSION - Version to install

param()

$ErrorActionPreference = "Stop"

# Configuration
$ServerUrl = if ($env:LOCALBRAIN_SERVER) { $env:LOCALBRAIN_SERVER } else { "http://localbrain.oss-cn-shanghai.aliyuncs.com" }
$Version = if ($env:LOCALBRAIN_VERSION) { $env:LOCALBRAIN_VERSION } else { "latest" }
$InstallDir = "$env:USERPROFILE\.localbrain"
$VenvDir = "$InstallDir\venv"
$BinDir = "$InstallDir\bin"

# Colors
function Write-Info($message) { Write-Host "[INFO] $message" -ForegroundColor Green }
function Write-Warn($message) { Write-Host "[WARN] $message" -ForegroundColor Yellow }
function Write-Err($message) { Write-Host "[ERROR] $message" -ForegroundColor Red; exit 1 }

# Check Python
function Check-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Err "Python 3.8+ is required. Please install Python first."
    }
    
    $versionOutput = python --version 2>&1
    $pythonVersion = $versionOutput.ToString().Split()[1]
    Write-Info "Python $pythonVersion detected"
}

# Check existing
function Check-Existing {
    if (Test-Path $VenvDir) {
        Write-Warn "Virtual environment already exists at $VenvDir"
        Write-Info "Removing existing venv for clean install"
        Remove-Item -Recurse -Force $VenvDir
    }
}

# Fetch version info
function Fetch-VersionInfo {
    $url = "$ServerUrl/version.json"
    Write-Info "Fetching version info from $url"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        if ($Version -eq "latest") {
            $script:Version = $response.version
            Write-Info "Latest version: $Version"
        }
    }
    catch {
        Write-Err "Failed to fetch version info: $_"
    }
}

# Create venv
function Create-Venv {
    Write-Info "Creating virtual environment at $VenvDir"
    python -m venv $VenvDir
    Write-Info "Virtual environment created"
}

# Install wheel
function Install-Wheel {
    $wheelUrl = "$ServerUrl/python_installer/packages/localbrain-$Version-py3-none-any.whl"
    
    Write-Info "Downloading and installing wheel from $wheelUrl"
    
    & "$VenvDir\Scripts\Activate.ps1"
    pip install --upgrade pip --quiet
    pip install $wheelUrl
    deactivate
    
    Write-Info "Wheel installed successfully"
}

# Create bin link (Windows: copy)
function Create-BinLink {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Copy-Item "$VenvDir\Scripts\localbrain.exe" "$BinDir\localbrain.exe" -Force
    Write-Info "Binary ready at $BinDir\localbrain.exe"
}

# Add to PATH
function Add-ToPath {
    $path = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($path -like "*$BinDir*") {
        Write-Info "Already in PATH"
        return
    }
    
    [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$path", "User")
    Write-Info "Added to PATH"
}

# Write install info
function Write-InstallInfo {
    $installInfo = @{
        version = $Version
        install_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        install_path = "$BinDir\localbrain.exe"
        install_type = "python"
        source_url = "$ServerUrl/python_installer/packages/localbrain-$Version-py3-none-any.whl"
        venv_path = $VenvDir
    }
    
    $infoPath = "$InstallDir\.install-info"
    $installInfo | ConvertTo-Json | Set-Content -Path $infoPath
    
    Write-Info "Install info written to $infoPath"
}

# Print success
function Print-Success {
    Write-Host ""
    Write-Host "✓ LocalBrain installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Version: $Version"
    Write-Host "Type:    Python (venv)"
    Write-Host "Binary:  $BinDir\localbrain.exe"
    Write-Host "Venv:    $VenvDir"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your terminal or run 'refreshenv'"
    Write-Host "  2. Run 'localbrain init setup' to initialize"
    Write-Host "  3. Run 'localbrain doctor' to verify installation"
    Write-Host ""
}

# Main
Write-Info "Installing LocalBrain (Python method)..."

Check-Python
Check-Existing
Fetch-VersionInfo
Create-Venv
Install-Wheel
Create-BinLink
Write-InstallInfo
Add-ToPath
Print-Success
```

- [ ] **Step 5: Verify directory structure**

```bash
ls -la scripts/python_installer/
```

Expected output:
```
install.sh
install.ps1
```

- [ ] **Step 6: Commit Python installer**

```bash
git add scripts/python_installer/
git commit -m "feat: add Python installer for hybrid distribution"
```

---

## Task 3: Create Build Wheel Script

**Files:**
- Create: `scripts/build_wheel.py`

- [ ] **Step 1: Write scripts/build_wheel.py**

```python
#!/usr/bin/env python3
"""
Build wheel for localbrain.

Usage:
    python scripts/build_wheel.py --version 0.1.0
    
The script:
1. Updates VERSION file
2. Builds wheel using pip wheel
3. Renames to canonical format: localbrain-{version}-py3-none-any.whl
4. Generates SHA256 checksum file
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_wheel(version: str) -> Path:
    """Build wheel and return path to wheel file."""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    # Ensure dist directory exists
    dist_dir.mkdir(exist_ok=True)
    
    # Clean existing wheels
    for f in dist_dir.glob("*.whl"):
        f.unlink()
        print(f"Removed old wheel: {f}")
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    print(f"Updated VERSION file to {version}")
    
    # Build wheel
    print(f"Building wheel for localbrain v{version}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"Wheel build failed with exit code {result.returncode}")
    
    # Find built wheel
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No wheel found in dist/")
    
    wheel_path = wheels[0]
    print(f"Built wheel: {wheel_path.name}")
    
    # Rename to canonical name (handle version normalization)
    canonical_name = f"localbrain-{version}-py3-none-any.whl"
    canonical_path = dist_dir / canonical_name
    
    if wheel_path.name != canonical_name:
        wheel_path = wheel_path.rename(canonical_path)
        print(f"Renamed to: {canonical_name}")
    
    return wheel_path


def generate_checksum(wheel_path: Path) -> Path:
    """Generate SHA256 checksum file for wheel."""
    checksum = calculate_sha256(wheel_path)
    checksum_file = wheel_path.with_suffix(".whl.sha256")
    checksum_file.write_text(f"sha256:{checksum}  {wheel_path.name}\n")
    return checksum_file


def main():
    parser = argparse.ArgumentParser(
        description="Build localbrain wheel for distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/build_wheel.py --version 0.1.0
    python scripts/build_wheel.py --version 0.2.0 --output ./release/
        """,
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version number (e.g., 0.1.0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: dist/)",
    )
    
    args = parser.parse_args()
    
    # Build wheel
    print(f"\n{'='*50}")
    print(f"Building localbrain v{args.version} wheel")
    print(f"{'='*50}\n")
    
    wheel_path = build_wheel(args.version)
    
    # Generate checksum
    checksum_file = generate_checksum(wheel_path)
    print(f"Generated checksum: {checksum_file.name}")
    
    # Copy to output directory if specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(wheel_path, args.output / wheel_path.name)
        shutil.copy(checksum_file, args.output / checksum_file.name)
        print(f"Copied to: {args.output}")
    
    # Print summary
    wheel_size = wheel_path.stat().st_size / 1024
    print(f"\n{'='*50}")
    print("Build complete!")
    print(f"{'='*50}")
    print(f"Wheel:    {wheel_path}")
    print(f"Checksum: {checksum_file}")
    print(f"Size:     {wheel_size:.1f} KB")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make build_wheel.py executable**

```bash
chmod +x scripts/build_wheel.py
```

- [ ] **Step 3: Test wheel build (optional, requires dependencies)**

```bash
cd /Users/xudonglai/AliDrive/Work/agentic-local-brain
python3 scripts/build_wheel.py --version 0.1.0
```

Expected output:
```
Building localbrain v0.1.0 wheel...
Wheel built: dist/localbrain-0.1.0-py3-none-any.whl
Checksum: dist/localbrain-0.1.0-py3-none-any.whl.sha256
Size: XX.X KB
```

- [ ] **Step 4: Commit build_wheel.py**

```bash
git add scripts/build_wheel.py
git commit -m "feat: add build_wheel.py for wheel distribution"
```

---

## Task 4: Update Self-Update Module

**Files:**
- Modify: `kb/self_update.py`

- [ ] **Step 1: Add install type detection function**

Add this function after the `get_platform_key()` function (around line 71):

```python
def get_install_type() -> str:
    """
    Detect whether installed via Python (venv) or binary.
    
    Returns:
        'python' if installed via Python installer
        'binary' if installed via binary installer
        'unknown' if installation type cannot be determined
    """
    install_dir = get_install_dir()
    
    # Check for Python installation (venv exists)
    venv_path = install_dir / "venv"
    if venv_path.exists() and venv_path.is_dir():
        return "python"
    
    # Check for binary installation
    bin_path = install_dir / "bin" / "localbrain"
    if bin_path.exists():
        return "binary"
    
    return "unknown"
```

- [ ] **Step 2: Add wheel download function**

Add this function after the `download_binary()` function (around line 207):

```python
def download_wheel(
    server_url: str,
    version: str,
    dest_path: Path,
) -> Path:
    """
    Download wheel from server with retry logic.
    
    Returns:
        Path to downloaded temp file
    """
    url = f"{server_url.rstrip('/')}/python_installer/packages/localbrain-{version}-py3-none-any.whl"
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Downloading {url} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Write to temp file
                temp_path = dest_path.with_suffix(".download")
                temp_path.write_bytes(response.content)
                
                return temp_path
                
        except httpx.HTTPError as e:
            logger.warning(f"Download failed: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Failed to download after {MAX_RETRIES} attempts: {e}")
    
    raise RuntimeError("Download failed")
```

- [ ] **Step 3: Add Python update function**

Add this function after the `download_wheel()` function:

```python
def perform_python_update(
    server_url: str,
    current_version: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Perform update for Python installation.
    
    Args:
        server_url: Update server base URL
        current_version: Currently installed version
        force: Force update even if same version
    
    Returns:
        Tuple of (success, message)
    """
    import subprocess
    
    try:
        # Fetch latest version info
        version_info = fetch_version_info(server_url)
        
        # Compare versions
        if not force and compare_versions(current_version, version_info.version) >= 0:
            return True, f"Already up to date (version {current_version})"
        
        # Get venv path
        install_dir = get_install_dir()
        venv_path = install_dir / "venv"
        
        if not venv_path.exists():
            return False, "Python installation not found. Please reinstall."
        
        # Download wheel
        version = version_info.version.lstrip('v')
        wheel_url = f"{server_url.rstrip('/')}/python_installer/packages/localbrain-{version}-py3-none-any.whl"
        
        logger.info(f"Downloading wheel from {wheel_url}")
        
        # Install wheel directly via pip
        pip_path = venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = venv_path / "Scripts" / "pip.exe"  # Windows
        
        result = subprocess.run(
            [str(pip_path), "install", "--upgrade", wheel_url],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"pip install failed: {result.stderr}")
            return False, f"Failed to install wheel: {result.stderr}"
        
        # Update install info
        bin_path = install_dir / "bin" / "localbrain"
        install_info = InstallInfo(
            version=version_info.version,
            install_time=datetime.utcnow().isoformat() + "Z",
            install_path=str(bin_path),
            source_url=wheel_url,
            platform="python",
            architecture="any",
            checksum="",
        )
        write_install_info(install_info)
        
        return True, f"Updated to version {version_info.version}"
        
    except httpx.HTTPError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        logger.exception("Python update failed")
        return False, f"Update failed: {e}"
```

- [ ] **Step 4: Update perform_update function to dispatch by install type**

Modify the `perform_update()` function to check install type and dispatch accordingly. Replace the existing function (starting around line 278) with:

```python
def perform_update(
    server_url: str,
    current_version: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Perform the self-update process.
    
    Detects installation type (Python or binary) and performs appropriate update.
    
    Args:
        server_url: Update server base URL
        current_version: Currently installed version
        force: Force update even if same version
    
    Returns:
        Tuple of (success, message)
    """
    install_type = get_install_type()
    
    if install_type == "python":
        logger.info("Detected Python installation, using wheel update")
        return perform_python_update(server_url, current_version, force)
    elif install_type == "binary":
        logger.info("Detected binary installation, using binary update")
        return perform_binary_update(server_url, current_version, force)
    else:
        return False, "Unknown installation type. Please reinstall."
```

- [ ] **Step 5: Rename original perform_update to perform_binary_update**

Rename the existing `perform_update()` function (the one with binary download logic) to `perform_binary_update()`:

```python
def perform_binary_update(
    server_url: str,
    current_version: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Perform update for binary installation.
    
    Args:
        server_url: Update server base URL
        current_version: Currently installed version
        force: Force update even if same version
    
    Returns:
        Tuple of (success, message)
    """
    # ... (keep the existing binary update logic)
```

Also update the download URL in `download_binary()` to use `binary_installer/releases/`:
```python
url = f"{server_url.rstrip('/')}/binary_installer/releases/{version}/{filename}"
```

- [ ] **Step 6: Run tests to verify changes**

```bash
cd /Users/xudonglai/AliDrive/Work/agentic-local-brain
python3 -c "from kb.self_update import get_install_type; print(get_install_type())"
```

Expected output:
```
unknown
```

- [ ] **Step 7: Commit self_update changes**

```bash
git add kb/self_update.py
git commit -m "feat: add Python installation type detection and update support"
```

---

## Task 5: Update Doctor Command

**Files:**
- Modify: `kb/commands/doctor.py`
- Modify: `kb/self_update.py` (add import)

- [ ] **Step 1: Update check_install_info function in doctor.py**

Replace the existing `check_install_info()` function (lines 62-67) with:

```python
def check_install_info() -> Tuple[bool, str, str]:
    """Check installation info and detect install type.
    
    Returns:
        Tuple of (found, message, install_type)
    """
    info = read_install_info()
    install_type = get_install_type()
    
    if info:
        # Build message with install type
        type_label = "Python (venv)" if install_type == "python" else "Binary"
        msg = f"v{info.version} ({type_label})"
        return True, msg, install_type
    return False, "not found", "unknown"
```

- [ ] **Step 2: Update doctor command to display install type**

Update the Installation section in `doctor()` function (lines 88-94):

```python
    # Installation check
    click.echo("  Installation:")
    install_ok, install_msg, install_type = check_install_info()
    click.echo(f"    Install info: {check_mark(install_ok)} {install_msg}")
    if not install_ok:
        issues.append("Install info not found - run install script")
    else:
        # Show install type specific info
        if install_type == "python":
            venv_path = get_install_dir() / "venv"
            click.echo(f"    Venv:         {venv_path}")
        elif install_type == "binary":
            bin_path = get_install_dir() / "bin" / "localbrain"
            click.echo(f"    Binary:       {bin_path}")
    click.echo()
```

- [ ] **Step 3: Add import for get_install_type**

Update the import statement at the top of doctor.py:

```python
from kb.self_update import read_install_info, get_install_dir, get_install_type
```

- [ ] **Step 4: Test doctor command output**

```bash
# Test the doctor command
python -m kb.commands.doctor
# or after installation:
localbrain doctor
```

Expected output should show:
```
  Installation:
    Install info: ✓ v0.1.0 (Python (venv))
    Venv:         /Users/xxx/.localbrain/venv
```

or for binary:
```
  Installation:
    Install info: ✓ v0.1.0 (Binary)
    Binary:       /Users/xxx/.localbrain/bin/localbrain
```

- [ ] **Step 5: Commit doctor changes**

```bash
git add kb/commands/doctor.py
git commit -m "feat: doctor command shows install type (Python/Binary)"
```

---

## Task 6: Update README Documentation

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`

- [ ] **Step 1: Update README.md Installation section**

Replace the existing Installation section (lines 15-73) with:

```markdown
## Installation

### Option 1: Python Install (Recommended)

Works on all platforms without security warnings. Requires Python 3.8+.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

The installer will:
- Check Python 3.8+ is installed
- Create a virtual environment at `~/.localbrain/venv`
- Download and install the wheel package
- Add `localbrain` to your PATH

### Option 2: Binary Install (No Python Required)

For systems without Python. Standalone binary with no dependencies.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**macOS Note:** Binary requires Gatekeeper bypass:
```bash
xattr -cr ~/.localbrain/bin/localbrain
```

### Option 3: Install from Source

For development or custom builds:

```bash
# Clone the repository
git clone <repository-url>
cd agentic-local-brain

# Install in development mode
pip install -e .

# Verify installation
localbrain --version
```

### Post-Installation

After installation, verify and initialize:

```bash
# Check installation
localbrain doctor

# Initialize knowledge base
localbrain init setup
```
```

- [ ] **Step 2: Update README.md CLI Maintenance Commands section**

The CLI Maintenance Commands table (lines 74-84) remains unchanged.

- [ ] **Step 3: Update README_zh.md with Chinese translation**

Sync the Chinese documentation with the same structure, translating the new installation section.

- [ ] **Step 4: Commit README updates**

```bash
git add README.md README_zh.md
git commit -m "docs: update installation documentation for hybrid distribution"
```

---

## Task 7: Update Memory and Final Verification

- [ ] **Step 1: Update project_build_configuration memory**

Record the new directory structure for binary_installer and python_installer.

- [ ] **Step 2: Run final verification**

```bash
# Check directory structure
ls -la scripts/

# Check binary_installer
ls -la scripts/binary_installer/

# Check python_installer
ls -la scripts/python_installer/

# Check build_wheel.py
python3 scripts/build_wheel.py --help
```

- [ ] **Step 3: Create final commit with all changes**

```bash
git status
git add -A
git commit -m "feat: implement hybrid distribution system

- Move binary installer scripts to scripts/binary_installer/
- Add Python installer scripts in scripts/python_installer/
- Add build_wheel.py for wheel distribution
- Update self_update.py to detect installation type
- Update README documentation for both install methods

Python installer is now the recommended method to avoid
macOS Gatekeeper security warnings for unsigned binaries."
```

---

## Summary

After completing all tasks:

1. **Binary Installer**: Moved to `scripts/binary_installer/`, URLs updated to `binary_installer/` path
2. **Python Installer**: New scripts in `scripts/python_installer/`, creates venv and installs wheel
3. **Build Wheel**: `scripts/build_wheel.py` for building distributable wheels
4. **Self-Update**: Detects install type and performs appropriate update
5. **Documentation**: README updated to show Python as recommended, binary as alternative

**HTTP Server Structure Required:**
```
localbrain.io.alibaba-inc.com/
├── version.json
├── binary_installer/
│   ├── install.sh
│   ├── install.ps1
│   └── releases/v0.1.0/localbrain-{platform}
└── python_installer/
    ├── install.sh
    ├── install.ps1
    └── packages/localbrain-{version}-py3-none-any.whl
```
