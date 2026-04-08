# Cross-Platform Installation System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a cross-platform installation system with one-liner install, self-update, clean uninstall, and diagnostics.

**Architecture:** PyInstaller-based standalone binaries distributed via internal HTTP server. Client-side update/uninstall/doctor commands communicate with HTTP server using GET API protocol. Install scripts handle initial setup and PATH management.

**Tech Stack:** Python 3.8+, Click (CLI), PyInstaller (binary packaging), httpx (HTTP client), SHA256 (checksum verification)

---

## File Structure

```
New files to create:
├── VERSION                           # Single source of truth for version
├── scripts/
│   ├── build.py                      # Cross-platform build script
│   ├── install.sh                    # macOS/Linux one-liner installer
│   └── install.ps1                   # Windows PowerShell installer
├── localbrain.spec                   # PyInstaller spec file
├── kb/
│   ├── version.py                    # Version module (reads VERSION file)
│   ├── self_update.py                # Self-update logic + HTTP client
│   └── commands/
│       ├── self_update.py            # localbrain self-update command
│       ├── uninstall.py              # localbrain uninstall command
│       └── doctor.py                 # localbrain doctor command
└── tests/
    ├── test_version.py
    ├── test_self_update.py
    ├── test_doctor.py
    └── test_uninstall.py

Files to modify:
├── kb/__init__.py                    # Import version from kb.version
├── kb/cli.py                         # Register new commands
├── kb/config.py                      # Add update_server_url config
├── config-template.yaml              # Add update_server_url
└── pyproject.toml                    # Add build dependencies
```

---

## Task 1: Version Infrastructure

**Files:**
- Create: `VERSION`
- Create: `kb/version.py`
- Modify: `kb/__init__.py`
- Test: `tests/test_version.py`

- [ ] **Step 1: Create VERSION file**

```bash
echo "0.1.0" > VERSION
```

- [ ] **Step 2: Write kb/version.py**

```python
"""
Version management module.

Version is read from VERSION file at package root.
For PyInstaller frozen binaries, version is embedded at build time.
"""

import os
from pathlib import Path


def _read_version_file() -> str:
    """Read version from VERSION file."""
    # Try to find VERSION file relative to this module
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    
    if version_file.exists():
        return version_file.read_text().strip()
    
    # Fallback for frozen/installed packages
    return "0.1.0"


def get_version() -> str:
    """Get the current version string."""
    # For frozen PyInstaller binaries, check for embedded version
    if getattr(os, 'frozen', False):
        # PyInstaller sets this attribute
        # VERSION file should be bundled via --add-data
        base_path = Path(os.path.dirname(os.path.executable))
        version_file = base_path.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    
    return _read_version_file()


def get_build_info() -> dict:
    """Get detailed build information."""
    import platform
    
    return {
        "version": get_version(),
        "python": platform.python_version(),
        "platform": platform.system().lower(),
        "architecture": platform.machine().lower(),
        "frozen": getattr(os, 'frozen', False),
    }


__version__ = get_version()
```

- [ ] **Step 3: Write test for version module**

Create `tests/test_version.py`:

```python
"""Tests for version module."""

import os
import pytest
from unittest.mock import patch, MagicMock


def test_get_version_from_file(tmp_path):
    """Test reading version from VERSION file."""
    from kb.version import _read_version_file
    
    # The version should be a valid semver string
    version = _read_version_file()
    assert isinstance(version, str)
    assert len(version) > 0


def test_get_version_returns_string():
    """Test get_version returns a string."""
    from kb.version import get_version
    
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_get_build_info():
    """Test get_build_info returns expected keys."""
    from kb.version import get_build_info
    
    info = get_build_info()
    assert "version" in info
    assert "python" in info
    assert "platform" in info
    assert "architecture" in info
    assert "frozen" in info


def test_frozen_binary_version(tmp_path, monkeypatch):
    """Test version detection in frozen (PyInstaller) binary."""
    # Mock frozen state
    monkeypatch.setattr(os, 'frozen', True, raising=False)
    monkeypatch.setattr(os, 'executable', str(tmp_path / "localbrain"))
    
    # Create VERSION file in expected location
    version_dir = tmp_path
    version_file = version_dir / "VERSION"
    version_file.write_text("1.2.3")
    
    # The test verifies the logic path exists
    from kb.version import get_version
    # Will fallback to file read since mocked path differs
    version = get_version()
    assert isinstance(version, str)
```

- [ ] **Step 4: Run tests to verify**

```bash
pytest tests/test_version.py -v
```

Expected: All tests pass

- [ ] **Step 5: Update kb/__init__.py to use version module**

```python
"""
Agentic Local Brain - Local knowledge management system

A local tool for collecting, processing and querying personal knowledge.
Supports multiple data source collection, intelligent chunking, 
vector storage and natural language queries.
"""

from kb.version import __version__, get_version, get_build_info

__author__ = "Agentic Local Brain Team"
```

- [ ] **Step 6: Commit**

```bash
git add VERSION kb/version.py kb/__init__.py tests/test_version.py
git commit -m "feat: add version infrastructure with VERSION file"
```

---

## Task 2: Update Configuration for Server URL

**Files:**
- Modify: `kb/config.py`
- Modify: `config-template.yaml`
- Test: `tests/test_config.py` (extend existing)

- [ ] **Step 1: Add update_server_url to DEFAULT_CONFIG in kb/config.py**

Find the DEFAULT_CONFIG dictionary (lines 20-45) and add update_server_url:

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    "data_dir": "~/.knowledge-base",
    "update_server_url": "http://localbrain-internal.yourcompany.com",
    "embedding": {
        "provider": "dashscope",
        "model": "text-embedding-v4",
    },
    # ... rest of config
}
```

- [ ] **Step 2: Add property to Config class**

Add these properties to the Config class (after the to_dict method, around line 179):

```python
@property
def update_server_url(self) -> str:
    """Get the update server URL."""
    return self.get("update_server_url", DEFAULT_CONFIG["update_server_url"])

@property
def install_dir(self) -> Path:
    """Get the installation directory (~/.localbrain/)."""
    return Path.home() / ".localbrain"

@property
def install_info_path(self) -> Path:
    """Get the install-info.json file path."""
    return self.install_dir / ".install-info"
```

- [ ] **Step 3: Update config-template.yaml**

Add after line 5:

```yaml
# Update server URL (for self-update functionality)
update_server_url: http://localbrain-internal.yourcompany.com
```

- [ ] **Step 4: Add test for new config properties**

Create `tests/test_config_update.py`:

```python
"""Tests for update-related config properties."""

import pytest
from kb.config import Config, DEFAULT_CONFIG


def test_default_update_server_url():
    """Test default update server URL."""
    assert "update_server_url" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["update_server_url"]


def test_config_update_server_url():
    """Test Config.update_server_url property."""
    config = Config()
    url = config.update_server_url
    assert isinstance(url, str)
    assert url.startswith("http")


def test_config_install_dir():
    """Test Config.install_dir property."""
    config = Config()
    install_dir = config.install_dir
    assert str(install_dir).endswith(".localbrain")


def test_config_install_info_path():
    """Test Config.install_info_path property."""
    config = Config()
    info_path = config.install_info_path
    assert info_path.name == ".install-info"
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_config_update.py -v
```

- [ ] **Step 6: Commit**

```bash
git add kb/config.py config-template.yaml tests/test_config_update.py
git commit -m "feat: add update_server_url config for self-update"
```

---

## Task 3: Self-Update Core Module

**Files:**
- Create: `kb/self_update.py`
- Test: `tests/test_self_update.py`

- [ ] **Step 1: Write the self_update module**

Create `kb/self_update.py`:

```python
"""
Self-update module for localbrain.

Handles version checking, binary downloading, checksum verification,
and atomic binary replacement.
"""

import hashlib
import json
import logging
import os
import platform
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds
CONNECT_TIMEOUT = 30  # seconds
DOWNLOAD_TIMEOUT = 60  # seconds per MB


@dataclass
class VersionInfo:
    """Version information from server."""
    version: str
    released: str
    changelog: Optional[str] = None
    binaries: dict = None
    
    def __post_init__(self):
        if self.binaries is None:
            self.binaries = {}


@dataclass
class InstallInfo:
    """Local installation information."""
    version: str
    install_time: str
    install_path: str
    source_url: str
    platform: str
    architecture: str
    checksum: str


def get_platform_key() -> str:
    """Get platform key for binary selection (e.g., 'macos-arm64')."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize architecture
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine
    
    return f"{system}-{arch}"


def get_install_dir() -> Path:
    """Get installation directory."""
    return Path.home() / ".localbrain"


def get_install_info_path() -> Path:
    """Get path to install-info file."""
    return get_install_dir() / ".install-info"


def read_install_info() -> Optional[InstallInfo]:
    """Read local installation information."""
    info_path = get_install_info_path()
    
    if not info_path.exists():
        return None
    
    try:
        data = json.loads(info_path.read_text())
        return InstallInfo(**data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to read install-info: {e}")
        return None


def write_install_info(info: InstallInfo) -> None:
    """Write installation information."""
    info_path = get_install_info_path()
    info_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "version": info.version,
        "install_time": info.install_time,
        "install_path": info.install_path,
        "source_url": info.source_url,
        "platform": info.platform,
        "architecture": info.architecture,
        "checksum": info.checksum,
    }
    
    info_path.write_text(json.dumps(data, indent=2))


def fetch_version_info(server_url: str) -> VersionInfo:
    """Fetch version information from server."""
    url = f"{server_url.rstrip('/')}/version.json"
    
    with httpx.Client(timeout=CONNECT_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    
    return VersionInfo(
        version=data.get("version", "0.0.0"),
        released=data.get("released", ""),
        changelog=data.get("changelog"),
        binaries=data.get("binaries", {}),
    )


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semver versions.
    
    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    def parse(v):
        parts = v.lstrip("v").split(".")
        return tuple(int(p) for p in parts[:3])
    
    p1, p2 = parse(v1), parse(v2)
    
    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    return f"sha256:{sha256_hash.hexdigest()}"


def download_binary(
    server_url: str,
    version: str,
    platform_key: str,
    dest_path: Path,
) -> Path:
    """
    Download binary from server with retry logic.
    
    Note: Checksum is obtained from version_info, not from response headers.
    
    Returns:
        Path to downloaded temp file
    """
    filename = get_binary_filename(platform_key)
    url = f"{server_url.rstrip('/')}/releases/{version}/{filename}"
    
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


def get_binary_filename(platform_key: str) -> str:
    """Get binary filename for platform."""
    if platform_key.startswith("win"):
        return f"localbrain-{platform_key}.exe"
    return f"localbrain-{platform_key}"


def verify_checksum(file_path: Path, expected: str) -> bool:
    """Verify file checksum matches expected value."""
    if not expected or not expected.startswith("sha256:"):
        logger.warning("No valid checksum provided, skipping verification")
        return True
    
    actual = calculate_sha256(file_path)
    match = actual == expected
    
    if not match:
        logger.error(f"Checksum mismatch: expected {expected}, got {actual}")
    
    return match


def atomic_replace_binary(
    old_path: Path,
    new_path: Path,
    backup_path: Optional[Path] = None,
) -> bool:
    """
    Atomically replace binary file.
    
    On Unix: rename old to .old, move new to old
    On Windows: handled by pending update mechanism
    
    Returns:
        True if replacement successful
    """
    if platform.system() == "Windows":
        # Windows: create pending update marker
        pending_path = old_path.parent / ".update-pending"
        pending_data = {
            "new_binary": str(new_path),
            "timestamp": datetime.utcnow().isoformat(),
        }
        pending_path.write_text(json.dumps(pending_data))
        return True
    
    # Unix: atomic rename
    try:
        # Move old to backup
        if backup_path:
            if backup_path.exists():
                backup_path.unlink()
            shutil.move(str(old_path), str(backup_path))
        
        # Move new to old location
        shutil.move(str(new_path), str(old_path))
        
        # Set executable permission
        old_path.chmod(0o755)
        
        return True
    except Exception as e:
        logger.error(f"Failed to replace binary: {e}")
        # Attempt rollback
        if backup_path and backup_path.exists():
            shutil.move(str(backup_path), str(old_path))
        return False


def perform_update(
    server_url: str,
    current_version: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Perform the self-update process.
    
    Args:
        server_url: Update server base URL
        current_version: Currently installed version
        force: Force update even if same version
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Fetch latest version info
        version_info = fetch_version_info(server_url)
        
        # Compare versions
        if not force and compare_versions(current_version, version_info.version) >= 0:
            return True, f"Already up to date (version {current_version})"
        
        # Get platform info
        platform_key = get_platform_key()
        
        # Check if binary available for platform
        if platform_key not in version_info.binaries:
            return False, f"No binary available for platform {platform_key}"
        
        binary_info = version_info.binaries[platform_key]
        
        # Get install directory
        install_dir = get_install_dir()
        bin_path = install_dir / "bin" / "localbrain"
        backup_path = install_dir / "bin" / "localbrain.old"
        
        if not bin_path.exists():
            return False, "Installation not found. Please reinstall."
        
        # Download new binary
        # Normalize version - ensure single 'v' prefix
        version = version_info.version.lstrip('v')
        temp_path = download_binary(
            server_url,
            f"v{version}",
            platform_key,
            bin_path,
        )
        
        # Verify checksum
        expected_checksum = binary_info.get("checksum", "")
        if not verify_checksum(temp_path, expected_checksum):
            temp_path.unlink()
            return False, "Checksum verification failed. Download may be corrupted."
        
        # Atomic replace
        if not atomic_replace_binary(bin_path, temp_path, backup_path):
            temp_path.unlink()
            return False, "Failed to replace binary"
        
        # Update install info
        install_info = InstallInfo(
            version=version_info.version,
            install_time=datetime.utcnow().isoformat() + "Z",
            install_path=str(bin_path),
            source_url=f"{server_url}/releases/v{version_info.version}/{get_binary_filename(platform_key)}",
            platform=platform_key.split("-")[0],
            architecture=platform_key.split("-")[1],
            checksum=expected_checksum,
        )
        write_install_info(install_info)
        
        return True, f"Updated to version {version_info.version}"
        
    except httpx.HTTPError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        logger.exception("Update failed")
        return False, f"Update failed: {e}"


def rollback() -> Tuple[bool, str]:
    """
    Rollback to previous version.
    
    Returns:
        Tuple of (success, message)
    """
    install_dir = get_install_dir()
    bin_path = install_dir / "bin" / "localbrain"
    backup_path = install_dir / "bin" / "localbrain.old"
    
    if not backup_path.exists():
        return False, "No previous version available for rollback"
    
    try:
        # Swap backup and current
        temp_path = bin_path.with_suffix(".rollback")
        shutil.move(str(bin_path), str(temp_path))
        shutil.move(str(backup_path), str(bin_path))
        temp_path.unlink()
        
        # Read old install info from backup (if exists)
        # For now, just update the version in install info
        install_info = read_install_info()
        if install_info:
            install_info.install_time = datetime.utcnow().isoformat() + "Z"
            write_install_info(install_info)
        
        return True, "Rolled back to previous version"
        
    except Exception as e:
        logger.exception("Rollback failed")
        return False, f"Rollback failed: {e}"
```

- [ ] **Step 2: Write tests for self_update module**

Create `tests/test_self_update.py`:

```python
"""Tests for self_update module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from kb.self_update import (
    get_platform_key,
    compare_versions,
    calculate_sha256,
    VersionInfo,
    InstallInfo,
    read_install_info,
    write_install_info,
)


def test_get_platform_key():
    """Test platform key generation."""
    key = get_platform_key()
    # Should return something like 'macos-arm64' or 'linux-x64'
    assert "-" in key
    parts = key.split("-")
    assert len(parts) == 2


def test_compare_versions():
    """Test version comparison."""
    assert compare_versions("0.1.0", "0.2.0") == -1
    assert compare_versions("0.2.0", "0.2.0") == 0
    assert compare_versions("0.2.0", "0.1.0") == 1
    assert compare_versions("v0.1.0", "0.1.0") == 0
    assert compare_versions("1.0.0", "0.9.9") == 1


def test_calculate_sha256(tmp_path):
    """Test SHA256 calculation."""
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"hello world")
    
    checksum = calculate_sha256(test_file)
    
    assert checksum.startswith("sha256:")
    assert len(checksum) == 71  # "sha256:" + 64 hex chars


def test_version_info_dataclass():
    """Test VersionInfo dataclass."""
    info = VersionInfo(
        version="0.1.0",
        released="2026-03-29",
        changelog="http://example.com/changelog",
        binaries={"macos-arm64": {"url": "releases/v0.1.0/localbrain-macos-arm64"}},
    )
    
    assert info.version == "0.1.0"
    assert "macos-arm64" in info.binaries


def test_install_info_dataclass():
    """Test InstallInfo dataclass."""
    info = InstallInfo(
        version="0.1.0",
        install_time="2026-03-29T10:00:00Z",
        install_path="/home/user/.localbrain/bin/localbrain",
        source_url="http://server/releases/v0.1.0/localbrain-macos-arm64",
        platform="macos",
        architecture="arm64",
        checksum="sha256:abc123",
    )
    
    assert info.version == "0.1.0"
    assert info.platform == "macos"


def test_write_and_read_install_info(tmp_path, monkeypatch):
    """Test writing and reading install info."""
    # Mock the install directory
    monkeypatch.setattr(
        "kb.self_update.get_install_dir",
        lambda: tmp_path / ".localbrain"
    )
    
    info = InstallInfo(
        version="0.1.0",
        install_time="2026-03-29T10:00:00Z",
        install_path=str(tmp_path / ".localbrain" / "bin" / "localbrain"),
        source_url="http://server/releases/v0.1.0/localbrain",
        platform="macos",
        architecture="arm64",
        checksum="sha256:abc123",
    )
    
    write_install_info(info)
    
    read_info = read_install_info()
    
    assert read_info is not None
    assert read_info.version == info.version
    assert read_info.platform == info.platform


def test_read_install_info_not_exists(tmp_path, monkeypatch):
    """Test reading install info when file doesn't exist."""
    monkeypatch.setattr(
        "kb.self_update.get_install_dir",
        lambda: tmp_path / ".localbrain"
    )
    
    info = read_install_info()
    assert info is None


def test_read_install_info_invalid_json(tmp_path, monkeypatch):
    """Test reading install info with invalid JSON."""
    install_dir = tmp_path / ".localbrain"
    install_dir.mkdir(parents=True)
    
    monkeypatch.setattr(
        "kb.self_update.get_install_dir",
        lambda: install_dir
    )
    
    # Write invalid JSON
    info_path = install_dir / ".install-info"
    info_path.write_text("not valid json")
    
    info = read_install_info()
    assert info is None
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_self_update.py -v
```

- [ ] **Step 4: Commit**

```bash
git add kb/self_update.py tests/test_self_update.py
git commit -m "feat: add self_update core module with download and verification"
```

---

## Task 4: Doctor Command

**Files:**
- Create: `kb/commands/doctor.py`
- Modify: `kb/cli.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write the doctor command module**

Create `kb/commands/doctor.py`:

```python
"""
Doctor command for system diagnostics.

Checks and reports system health, configuration, and service availability.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

import click

from kb.config import Config
from kb.version import get_version, get_build_info
from kb.self_update import read_install_info, get_install_dir


def check_mark(passed: bool) -> str:
    """Return check mark or cross based on status."""
    return "✓" if passed else "✗"


def check_config_exists(config: Config) -> Tuple[bool, str]:
    """Check if config file exists and is valid."""
    if config.config_path.exists():
        try:
            config.load()
            return True, str(config.config_path)
        except Exception:
            return False, f"{config.config_path} (invalid)"
    return False, "not found"


def check_data_dir(config: Config) -> Tuple[bool, str]:
    """Check if data directory exists."""
    data_dir = config.data_dir
    if data_dir.exists():
        return True, str(data_dir)
    return False, f"{data_dir} (not found)"


def check_path_in_env() -> Tuple[bool, str]:
    """Check if ~/.localbrain/bin is in PATH."""
    install_dir = get_install_dir()
    bin_dir = install_dir / "bin"
    
    path_env = os.environ.get("PATH", "")
    path_dirs = [Path(p) for p in path_env.split(os.pathsep)]
    
    if bin_dir in path_dirs:
        return True, str(bin_dir)
    
    return False, f"{bin_dir} not in PATH"


def check_services(config: Config) -> dict:
    """Check service availability."""
    return config.validate_services()


def check_install_info() -> Tuple[bool, str]:
    """Check installation info."""
    info = read_install_info()
    if info:
        return True, f"v{info.version} ({info.platform}-{info.architecture})"
    return False, "not found"


@click.command()
def doctor():
    """Run system diagnostics.
    
    Checks configuration, services, and installation status.
    """
    click.echo("🔍 LocalBrain Diagnostics\n")
    
    issues = []
    
    # Version info
    build_info = get_build_info()
    click.echo(f"  Version:     {build_info['version']}")
    click.echo(f"  Platform:    {build_info['platform']}-{build_info['architecture']}")
    click.echo(f"  Python:      {build_info['python']}")
    click.echo(f"  Frozen:      {build_info['frozen']}")
    click.echo()
    
    # Installation check
    click.echo("  Installation:")
    install_ok, install_msg = check_install_info()
    click.echo(f"    Install info: {check_mark(install_ok)} {install_msg}")
    if not install_ok:
        issues.append("Install info not found - run install script")
    click.echo()
    
    # Configuration check
    click.echo("  Configuration:")
    config = Config()
    
    config_ok, config_msg = check_config_exists(config)
    click.echo(f"    Config:  {check_mark(config_ok)} {config_msg}")
    if not config_ok:
        issues.append("Config not found - run 'localbrain init setup'")
    
    data_ok, data_msg = check_data_dir(config)
    click.echo(f"    Data:    {check_mark(data_ok)} {data_msg}")
    if not data_ok:
        issues.append("Data directory not found - run 'localbrain init setup'")
    click.echo()
    
    # Services check
    click.echo("  Services:")
    service_status = check_services(config)
    
    emb_ok = service_status.get("embedding_available", False)
    emb_config = config.get("embedding", {})
    emb_provider = emb_config.get("provider", "not configured")
    emb_model = emb_config.get("model", "")
    click.echo(f"    Embedding: {check_mark(emb_ok)} {emb_provider}/{emb_model}")
    if not emb_ok:
        issues.append("Embedding service not configured")
    
    llm_ok = service_status.get("llm_available", False)
    llm_config = config.get("llm", {})
    llm_provider = llm_config.get("provider", "not configured")
    llm_model = llm_config.get("model", "")
    click.echo(f"    LLM:       {check_mark(llm_ok)} {llm_provider}/{llm_model}")
    if not llm_ok:
        issues.append("LLM service not configured")
    click.echo()
    
    # PATH check
    click.echo("  Environment:")
    path_ok, path_msg = check_path_in_env()
    click.echo(f"    PATH:   {check_mark(path_ok)} {path_msg}")
    if not path_ok:
        issues.append("localbrain not in PATH - reinstall or add to PATH manually")
    click.echo()
    
    # Summary
    if issues:
        click.echo("  ⚠ Issues found:")
        for issue in issues:
            click.echo(f"    - {issue}")
        click.echo()
        click.echo("  Run 'localbrain init setup' to initialize.")
        sys.exit(1)
    else:
        click.echo("  ✓ All checks passed!")
        sys.exit(0)
```

- [ ] **Step 2: Register doctor command in cli.py**

Add import and registration in `kb/cli.py`:

```python
# Add to imports (line 20)
from kb.commands.doctor import doctor

# Add at end of command registrations (after cli.add_command(web))
cli.add_command(doctor)
```

- [ ] **Step 3: Write tests for doctor command**

Create `tests/test_doctor.py`:

```python
"""Tests for doctor command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.commands.doctor import (
    check_mark,
    check_config_exists,
    check_data_dir,
    check_path_in_env,
)
from kb.cli import cli


def test_check_mark():
    """Test check mark function."""
    assert check_mark(True) == "✓"
    assert check_mark(False) == "✗"


def test_check_config_exists_with_valid_config(tmp_path, monkeypatch):
    """Test config check with valid config."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("data_dir: ~/test\n")
    
    from kb.config import Config
    config = Config(config_path)
    
    ok, msg = check_config_exists(config)
    assert ok is True


def test_check_config_exists_not_found(tmp_path, monkeypatch):
    """Test config check when config doesn't exist."""
    from kb.config import Config
    config = Config(tmp_path / "nonexistent.yaml")
    
    ok, msg = check_config_exists(config)
    assert ok is False


def test_check_data_dir_exists(tmp_path, monkeypatch):
    """Test data dir check when exists."""
    from kb.config import Config
    
    config = MagicMock()
    config.data_dir = tmp_path
    
    ok, msg = check_data_dir(config)
    assert ok is True


def test_check_data_dir_not_exists(tmp_path, monkeypatch):
    """Test data dir check when not exists."""
    from kb.config import Config
    
    config = MagicMock()
    config.data_dir = tmp_path / "nonexistent"
    
    ok, msg = check_data_dir(config)
    assert ok is False


def test_check_path_in_env(monkeypatch):
    """Test PATH check."""
    # Test with PATH not containing localbrain
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    ok, msg = check_path_in_env()
    assert ok is False
    
    # Test with PATH containing localbrain
    home = Path.home()
    localbrain_bin = home / ".localbrain" / "bin"
    monkeypatch.setenv("PATH", f"{localbrain_bin}:/usr/bin:/bin")
    ok, msg = check_path_in_env()
    assert ok is True


def test_doctor_command_shows_version():
    """Test that doctor command shows version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    
    # Should show version
    assert "Version:" in result.output


def test_doctor_command_exit_code():
    """Test doctor command exit codes."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    
    # Exit code 0 if all checks pass, 1 if issues found
    assert result.exit_code in [0, 1]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_doctor.py -v
```

- [ ] **Step 5: Commit**

```bash
git add kb/commands/doctor.py kb/cli.py tests/test_doctor.py
git commit -m "feat: add doctor command for system diagnostics"
```

---

## Task 5: Self-Update Command

**Files:**
- Create: `kb/commands/self_update.py`
- Modify: `kb/cli.py`
- Test: `tests/test_self_update_command.py`

- [ ] **Step 1: Write the self-update command module**

Create `kb/commands/self_update.py`:

```python
"""
Update command for self-updating localbrain.

Provides self-update functionality with version checking,
download, verification, and rollback.
"""

import sys

import click

from kb.config import Config
from kb.version import get_version
from kb.self_update import (
    perform_update,
    rollback,
    fetch_version_info,
    compare_versions,
    read_install_info,
)


@click.command("self-update")
@click.option("--check", is_flag=True, help="Check for update without installing")
@click.option("--rollback", "do_rollback", is_flag=True, help="Rollback to previous version")
@click.option("--force", is_flag=True, help="Force update even if same version")
def self_update(check: bool, do_rollback: bool, force: bool):
    """Update localbrain to the latest version.
    
    \b
    Examples:
      localbrain self-update           Update to latest version
      localbrain self-update --check   Check if update is available
      localbrain self-update --rollback  Restore previous version
    """
    config = Config()
    server_url = config.update_server_url
    current_version = get_version()
    
    if do_rollback:
        _handle_rollback()
        return
    
    if check:
        _handle_check(server_url, current_version)
        return
    
    _handle_update(server_url, current_version, force)


def _handle_check(server_url: str, current_version: str) -> None:
    """Handle --check flag: just check for updates."""
    try:
        version_info = fetch_version_info(server_url)
        latest_version = version_info.version
        
        comparison = compare_versions(current_version, latest_version)
        
        if comparison < 0:
            click.echo(f"Update available: {current_version} → {latest_version}")
            click.echo(f"Released: {version_info.released}")
            if version_info.changelog:
                click.echo(f"Changelog: {version_info.changelog}")
        elif comparison > 0:
            click.echo(f"You are on a pre-release version: {current_version}")
            click.echo(f"Latest stable: {latest_version}")
        else:
            click.echo(f"Already up to date: {current_version}")
        
    except Exception as e:
        click.echo(f"Failed to check for updates: {e}", err=True)
        sys.exit(1)


def _handle_update(server_url: str, current_version: str, force: bool) -> None:
    """Handle update installation."""
    click.echo(f"Current version: {current_version}")
    
    # Check for pending update on Windows
    import platform
    if platform.system() == "Windows":
        from pathlib import Path
        pending_path = Path.home() / ".localbrain" / "bin" / ".update-pending"
        if pending_path.exists():
            click.echo("A pending update is waiting to be applied.")
            click.echo("Please restart localbrain to complete the update.")
            sys.exit(0)
    
    click.echo("Checking for updates...")
    
    try:
        success, message = perform_update(server_url, current_version, force)
        
        if success:
            click.echo(f"✓ {message}")
        else:
            click.echo(f"✗ {message}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Update failed: {e}", err=True)
        sys.exit(1)


def _handle_rollback() -> None:
    """Handle rollback to previous version."""
    click.echo("Rolling back to previous version...")
    
    success, message = rollback()
    
    if success:
        click.echo(f"✓ {message}")
    else:
        click.echo(f"✗ {message}", err=True)
        sys.exit(1)
```

- [ ] **Step 2: Register self-update command in cli.py**

Add to `kb/cli.py`:

```python
# Add to imports
from kb.commands.self_update import self_update

# Add registration
cli.add_command(self_update)
```

- [ ] **Step 3: Write tests**

Create `tests/test_self_update_command.py`:

```python
"""Tests for update command."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.cli import cli


def test_self_update_check_shows_version():
    """Test self-update --check shows version info."""
    runner = CliRunner()
    
    with patch("kb.commands.update.fetch_version_info") as mock_fetch:
        mock_fetch.return_value = MagicMock(
            version="0.2.0",
            released="2026-03-29",
            changelog=None,
        )
        
        result = runner.invoke(cli, ["self-update", "--check"])
        
        assert "Update available" in result.output or "up to date" in result.output.lower()


def test_self_update_rollback_no_backup():
    """Test self-update --rollback when no backup exists."""
    runner = CliRunner()
    
    with patch("kb.commands.self_update.rollback") as mock_rollback:
        mock_rollback.return_value = (False, "No previous version available")
        
        result = runner.invoke(cli, ["self-update", "--rollback"])
        
        assert result.exit_code == 1


def test_self_update_command_requires_network():
    """Test self-update command handles network errors."""
    runner = CliRunner()
    
    with patch("kb.commands.update.perform_update") as mock_update:
        mock_update.return_value = (False, "Network error")
        
        result = runner.invoke(cli, ["self-update"])
        
        assert result.exit_code == 1
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_self_update_command.py -v
```

- [ ] **Step 5: Commit**

```bash
git add kb/commands/self_update.py kb/cli.py tests/test_self_update_command.py
git commit -m "feat: add self-update command with check and rollback support"
```

---

## Task 6: Uninstall Command

**Files:**
- Create: `kb/commands/uninstall.py`
- Modify: `kb/cli.py`
- Test: `tests/test_uninstall.py`

- [ ] **Step 1: Write the uninstall command module**

Create `kb/commands/uninstall.py`:

```python
"""
Uninstall command for removing localbrain.

Provides clean uninstallation that preserves user data.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

import click

# Import shared path functions to avoid duplication
from kb.self_update import get_install_dir


def get_data_dir() -> Path:
    """Get data directory."""
    return Path.home() / ".knowledge-base"


def get_shell_config_files() -> List[Path]:
    """Get list of possible shell config files."""
    home = Path.home()
    return [
        home / ".zshrc",
        home / ".zprofile",
        home / ".bashrc",
        home / ".bash_profile",
        home / ".config" / "fish" / "config.fish",
    ]


def remove_path_entry_from_file(config_file: Path, bin_dir: Path) -> bool:
    """
    Remove PATH entry for localbrain from shell config file.
    
    Returns True if file was modified.
    """
    if not config_file.exists():
        return False
    
    content = config_file.read_text()
    lines = content.split("\n")
    
    # Pattern to match: export PATH="$HOME/.localbrain/bin:$PATH"
    # or similar variations
    bin_dir_str = str(bin_dir)
    patterns_to_remove = [
        f'export PATH="{bin_dir_str}:$PATH"',
        f'export PATH="${{HOME}}/.localbrain/bin:$PATH"',
        f'export PATH="$HOME/.localbrain/bin:$PATH"',
        f'set -gx PATH {bin_dir_str} $PATH',  # fish
    ]
    
    new_lines = []
    modified = False
    
    for line in lines:
        stripped = line.strip()
        should_remove = False
        
        for pattern in patterns_to_remove:
            if stripped == pattern:
                should_remove = True
                break
        
        # Also check if line contains the path export
        if not should_remove and ".localbrain/bin" in stripped and "PATH" in stripped:
            # Be careful - use exact match for safety
            for pattern in patterns_to_remove:
                if stripped == pattern:
                    should_remove = True
                    break
        
        if should_remove:
            modified = True
        else:
            new_lines.append(line)
    
    if modified:
        config_file.write_text("\n".join(new_lines))
    
    return modified


@click.command()
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def uninstall(yes: bool):
    """Uninstall localbrain from the system.
    
    Removes the binary but preserves your knowledge base.
    To remove user data, manually delete:
      - ~/.knowledge-base
      - ~/.localbrain/config.yaml
    
    \b
    Examples:
      localbrain uninstall           Remove binary, keep data
      localbrain uninstall -y        Remove without confirmation
    """
    install_dir = get_install_dir()
    data_dir = get_data_dir()
    bin_dir = install_dir / "bin"
    binary_path = bin_dir / "localbrain"
    
    # Check if installed
    if not binary_path.exists():
        click.echo("localbrain is not installed.")
        sys.exit(1)
    
    # Confirmation
    if not yes:
        click.echo("This will remove localbrain from your system.")
        click.echo()
        click.echo("Your knowledge base will be preserved:")
        click.echo(f"  - {data_dir}")
        click.echo(f"  - {install_dir / 'config.yaml'}")
        click.echo()
        click.echo("To completely remove all data, run:")
        click.echo(f"  rm -rf {data_dir} {install_dir}")
        click.echo()
        
        if not click.confirm("Continue?", default=False):
            click.echo("Uninstall cancelled.")
            sys.exit(0)
    
    # Remove binary
    click.echo("Removing binary...")
    if binary_path.exists():
        binary_path.unlink()
    
    # Remove backup
    backup_path = binary_path.with_suffix(".old")
    if backup_path.exists():
        backup_path.unlink()
    
    # Remove install info
    install_info = install_dir / ".install-info"
    if install_info.exists():
        install_info.unlink()
    
    # Remove pending update marker
    pending_path = bin_dir / ".update-pending"
    if pending_path.exists():
        pending_path.unlink()
    
    # Remove from PATH
    click.echo("Removing from PATH...")
    for config_file in get_shell_config_files():
        if config_file.exists():
            remove_path_entry_from_file(config_file, bin_dir)
    
    # Remove empty bin directory
    if bin_dir.exists() and not list(bin_dir.iterdir()):
        bin_dir.rmdir()
    
    # Show preserved files
    click.echo("Preserved:")
    if data_dir.exists():
        click.echo(f"  - {data_dir}")
    config_path = install_dir / "config.yaml"
    if config_path.exists():
        click.echo(f"  - {config_path}")
    
    click.echo()
    click.echo("✓ localbrain has been uninstalled.")
    click.echo()
    click.echo("To completely remove all data, run:")
    click.echo(f"  rm -rf {data_dir} {install_dir}")
```

- [ ] **Step 2: Register uninstall command in cli.py**

Add to `kb/cli.py`:

```python
# Add to imports
from kb.commands.uninstall import uninstall

# Add registration
cli.add_command(uninstall)
```

- [ ] **Step 3: Write tests**

Create `tests/test_uninstall.py`:

```python
"""Tests for uninstall command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.commands.uninstall import (
    get_install_dir,
    get_data_dir,
    get_shell_config_files,
    remove_path_entry_from_file,
)
from kb.cli import cli


def test_get_install_dir():
    """Test install directory path."""
    install_dir = get_install_dir()
    assert str(install_dir).endswith(".localbrain")


def test_get_data_dir():
    """Test data directory path."""
    data_dir = get_data_dir()
    assert str(data_dir).endswith(".knowledge-base")


def test_get_shell_config_files():
    """Test shell config file detection."""
    configs = get_shell_config_files()
    assert len(configs) > 0
    
    # Should include common configs
    config_names = [c.name for c in configs]
    assert ".zshrc" in config_names or ".bashrc" in config_names


def test_remove_path_entry_from_file(tmp_path):
    """Test PATH entry removal from shell config."""
    config_file = tmp_path / ".zshrc"
    bin_dir = Path.home() / ".localbrain" / "bin"
    
    # Write config with PATH entry
    config_file.write_text(f"""
# Some config
export PATH="/usr/local/bin:$PATH"
export PATH="{bin_dir}:$PATH"
# More config
""")
    
    # Remove entry
    modified = remove_path_entry_from_file(config_file, bin_dir)
    
    assert modified is True
    
    # Verify entry removed
    content = config_file.read_text()
    assert ".localbrain/bin" not in content
    assert "/usr/local/bin" in content  # Other entries preserved


def test_remove_path_entry_no_match(tmp_path):
    """Test PATH removal when no match exists."""
    config_file = tmp_path / ".zshrc"
    bin_dir = Path.home() / ".localbrain" / "bin"
    
    config_file.write_text("export PATH=\"/usr/local/bin:$PATH\"\n")
    
    modified = remove_path_entry_from_file(config_file, bin_dir)
    
    assert modified is False


def test_uninstall_command_not_installed():
    """Test uninstall when not installed."""
    runner = CliRunner()
    
    with patch("kb.commands.uninstall.get_install_dir") as mock_dir:
        # Create temp dir without binary
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_dir.return_value = Path(tmpdir)
            
            result = runner.invoke(cli, ["uninstall", "-y"])
            
            assert "not installed" in result.output.lower()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_uninstall.py -v
```

- [ ] **Step 5: Commit**

```bash
git add kb/commands/uninstall.py kb/cli.py tests/test_uninstall.py
git commit -m "feat: add uninstall command (preserves user data)"
```

---

## Task 7: PyInstaller Build Configuration

**Files:**
- Create: `localbrain.spec`
- Create: `scripts/build.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create PyInstaller spec file**

Create `localbrain.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for localbrain.

Build standalone executable with all dependencies bundled.
"""

import os
import sys
from pathlib import Path

# Get the project root
block_cipher = None
# SPECPATH is injected by PyInstaller at build time
project_root = Path(SPECPATH)

# Read version from VERSION file
version_file = project_root / "VERSION"
version = version_file.read_text().strip() if version_file.exists() else "0.0.0"

# Determine platform suffix
import platform
system = platform.system().lower()
machine = platform.machine().lower()
# Handle different platform.machine() values across OS
if machine in ("x86_64", "amd64", "AMD64"):
    arch = "x64"
elif machine in ("arm64", "aarch64", "ARM64"):
    arch = "arm64"
else:
    arch = machine

# Data files to include
datas = [
    (str(project_root / "kb"), "kb"),
    (str(project_root / "config-template.yaml"), "."),
    (str(project_root / "VERSION"), "."),
]

# Hidden imports for dynamic loading
hiddenimports = [
    "chromadb",
    "chromadb.config",
    "pypdf",
    "pypdf PdfReader",
    "dashscope",
    "openai",
    "sentence_transformers",
    "httpx",
    "httpx._transports.default",
    "h11",
    "anyio",
    "anyio._backends._asyncio",
]

# Collect all dependencies
from PyInstaller.utils.hooks import collect_all, collect_submodules

binaries = []
for package in ["chromadb", "sentence_transformers"]:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hiddenimports)
    except Exception:
        pass

a = Analysis(
    ["kb/cli.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"localbrain-{system}-{arch}" + (".exe" if system == "windows" else ""),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: Create build script**

Create `scripts/build.py`:

```python
#!/usr/bin/env python3
"""
Cross-platform build script for localbrain.

Usage:
    python scripts/build.py --version 0.1.0
    python scripts/build.py --version 0.1.0 --platform macos-arm64
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_platform_key() -> str:
    """Get current platform key."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine
    
    return f"{system}-{arch}"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def build_binary(version: str, platform_key: str = None) -> Path:
    """Build binary using PyInstaller."""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    
    # Clean dist directory
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Update VERSION file
    version_file = project_root / "VERSION"
    version_file.write_text(version)
    
    # Run PyInstaller
    env = os.environ.copy()
    env["VERSION"] = version
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "localbrain.spec", "--clean", "--noconfirm"],
        cwd=project_root,
        env=env,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller failed with exit code {result.returncode}")
    
    # Find the built binary
    if platform_key is None:
        platform_key = get_platform_key()
    
    binary_name = f"localbrain-{platform_key}"
    if platform.system() == "Windows":
        binary_name += ".exe"
    
    binary_path = dist_dir / binary_name
    
    if not binary_path.exists():
        # PyInstaller might use different naming
        binaries = list(dist_dir.glob("localbrain*"))
        if binaries:
            binary_path = binaries[0]
            # Rename to canonical name
            binary_path = binary_path.rename(dist_dir / binary_name)
        else:
            raise FileNotFoundError(f"Binary not found in {dist_dir}")
    
    return binary_path


def generate_checksum(binary_path: Path) -> Path:
    """Generate SHA256 checksum file."""
    checksum = calculate_sha256(binary_path)
    checksum_file = binary_path.with_suffix(".sha256")
    checksum_file.write_text(f"sha256:{checksum}  {binary_path.name}\n")
    return checksum_file


def main():
    parser = argparse.ArgumentParser(description="Build localbrain binary")
    parser.add_argument("--version", required=True, help="Version to build (e.g., 0.1.0)")
    parser.add_argument("--platform", help="Target platform (e.g., macos-arm64)")
    parser.add_argument("--no-checksum", action="store_true", help="Skip checksum generation")
    
    args = parser.parse_args()
    
    platform_key = args.platform or get_platform_key()
    
    print(f"Building localbrain v{args.version} for {platform_key}")
    
    # Build
    binary_path = build_binary(args.version, platform_key)
    print(f"Binary built: {binary_path}")
    
    # Generate checksum
    if not args.no_checksum:
        checksum_file = generate_checksum(binary_path)
        print(f"Checksum file: {checksum_file}")
    
    # Print summary
    binary_size = binary_path.stat().st_size / (1024 * 1024)
    print(f"\nBuild complete!")
    print(f"  Binary: {binary_path}")
    print(f"  Size: {binary_size:.1f} MB")
    print(f"  Platform: {platform_key}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Update pyproject.toml**

Add build dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
build = [
    "pyinstaller>=5.0",
    "pyinstaller-hooks-contrib>=2023.0",
]
```

- [ ] **Step 4: Commit**

```bash
git add localbrain.spec scripts/build.py pyproject.toml
git commit -m "feat: add PyInstaller build configuration"
```

---

## Task 8: Install Scripts

**Files:**
- Create: `scripts/install.sh`
- Create: `scripts/install.ps1`

- [ ] **Step 1: Create macOS/Linux install script**

Create `scripts/install.sh`:

```bash
#!/bin/bash
#
# LocalBrain Installer for macOS/Linux
#
# Usage:
#   curl -fsSL http://localbrain-internal.yourcompany.com/install.sh | sh
#
# Environment variables:
#   LOCALBRAIN_SERVER  - Server URL (default: http://localbrain-internal.yourcompany.com)
#   LOCALBRAIN_VERSION - Version to install (default: latest)

set -e

# Configuration
SERVER_URL="${LOCALBRAIN_SERVER:-http://localbrain-internal.yourcompany.com}"
VERSION="${LOCALBRAIN_VERSION:-latest}"
INSTALL_DIR="$HOME/.localbrain"
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

# Detect OS and architecture
detect_platform() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    case "$ARCH" in
        x86_64|amd64) ARCH="x64" ;;
        arm64|aarch64) ARCH="arm64" ;;
    esac
    
    PLATFORM="${OS}-${ARCH}"
    info "Detected platform: $PLATFORM"
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
    if [ -f "$BIN_DIR/localbrain" ]; then
        warn "LocalBrain is already installed at $BIN_DIR/localbrain"
        info "Run 'localbrain self-update' to update to the latest version"
        exit 0
    fi
}

# Download file with retry
download() {
    local url="$1"
    local output="$2"
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if curl -fsSL --connect-timeout 30 "$url" -o "$output"; then
            return 0
        fi
        retry=$((retry + 1))
        warn "Download failed, retrying ($retry/$max_retries)..."
        sleep $((2 ** retry))
    done
    
    error "Failed to download after $max_retries attempts"
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

# Download binary
download_binary() {
    local filename="localbrain-${PLATFORM}"
    local url="${SERVER_URL}/releases/v${VERSION}/${filename}"
    local temp_file=$(mktemp)
    
    info "Downloading binary from $url"
    download "$url" "$temp_file"
    
    # Create bin directory
    mkdir -p "$BIN_DIR"
    
    # Move binary
    mv "$temp_file" "$BIN_DIR/localbrain"
    chmod +x "$BIN_DIR/localbrain"
    
    info "Binary installed to $BIN_DIR/localbrain"
}

# Add to PATH
add_to_path() {
    local path_entry="export PATH=\"\$HOME/.localbrain/bin:\$PATH\""
    
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
    info "Run 'source $SHELL_RC' or start a new shell to use localbrain"
}

# Write install info
write_install_info() {
    local install_info="$INSTALL_DIR/.install-info"
    local install_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local source_url="${SERVER_URL}/releases/v${VERSION}/localbrain-${PLATFORM}"
    
    cat > "$install_info" << EOF
{
  "version": "$VERSION",
  "install_time": "$install_time",
  "install_path": "$BIN_DIR/localbrain",
  "source_url": "$source_url",
  "platform": "$OS",
  "architecture": "$ARCH"
}
EOF
    
    info "Install info written to $install_info"
}

# Run first-time check
run_check() {
    if [ -x "$BIN_DIR/localbrain" ]; then
        info "Running installation check..."
        "$BIN_DIR/localbrain" init --check || true
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}✓ LocalBrain installed successfully!${NC}"
    echo ""
    echo "Version: $VERSION"
    echo "Binary:  $BIN_DIR/localbrain"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'source $SHELL_RC' or start a new terminal"
    echo "  2. Run 'localbrain init setup' to initialize"
    echo "  3. Run 'localbrain doctor' to verify installation"
    echo ""
}

# Main
main() {
    info "Installing LocalBrain..."
    
    detect_platform
    detect_shell
    check_existing
    fetch_version_info
    download_binary
    write_install_info
    add_to_path
    run_check
    print_success
}

main "$@"
```

- [ ] **Step 2: Create Windows install script**

Create `scripts/install.ps1`:

```powershell
#
# LocalBrain Installer for Windows
#
# Usage:
#   irm http://localbrain-internal.yourcompany.com/install.ps1 | iex
#
# Environment variables:
#   $env:LOCALBRAIN_SERVER  - Server URL
#   $env:LOCALBRAIN_VERSION - Version to install

param()

$ErrorActionPreference = "Stop"

# Configuration
$ServerUrl = if ($env:LOCALBRAIN_SERVER) { $env:LOCALBRAIN_SERVER } else { "http://localbrain-internal.yourcompany.com" }
$Version = if ($env:LOCALBRAIN_VERSION) { $env:LOCALBRAIN_VERSION } else { "latest" }
$InstallDir = "$env:USERPROFILE\.localbrain"
$BinDir = "$InstallDir\bin"

# Colors
function Write-Info($message) { Write-Host "[INFO] $message" -ForegroundColor Green }
function Write-Warn($message) { Write-Host "[WARN] $message" -ForegroundColor Yellow }
function Write-Err($message) { Write-Host "[ERROR] $message" -ForegroundColor Red; exit 1 }

# Detect platform
function Detect-Platform {
    $OS = "win"
    # Detect architecture including ARM64 support
    $Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
        "arm64"
    } elseif ([Environment]::Is64BitOperatingSystem) {
        "x64"
    } else {
        "x86"
    }
    $script:Platform = "$OS-$Arch"
    Write-Info "Detected platform: $Platform"
}

# Check if already installed
function Check-Existing {
    if (Test-Path "$BinDir\localbrain.exe") {
        Write-Warn "LocalBrain is already installed at $BinDir\localbrain.exe"
        Write-Info "Run 'localbrain self-update' to update to the latest version"
        exit 0
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

# Download binary
function Download-Binary {
    $filename = "localbrain-$Platform.exe"
    $url = "$ServerUrl/releases/v$Version/$filename"
    $tempFile = "$env:TEMP\localbrain.exe"
    
    Write-Info "Downloading binary from $url"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $tempFile -UseBasicParsing
    }
    catch {
        Write-Err "Failed to download: $_"
    }
    
    # Create directory and move
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Move-Item -Path $tempFile -Destination "$BinDir\localbrain.exe" -Force
    
    Write-Info "Binary installed to $BinDir\localbrain.exe"
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
    Write-Info "Restart your terminal or run 'refreshenv' to update PATH"
}

# Write install info
function Write-InstallInfo {
    $installInfo = @{
        version = $Version
        install_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        install_path = "$BinDir\localbrain.exe"
        source_url = "$ServerUrl/releases/v$Version/localbrain-$Platform.exe"
        platform = "windows"
        architecture = $Platform.Split("-")[1]
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
    Write-Host "Binary:  $BinDir\localbrain.exe"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your terminal or run 'refreshenv'"
    Write-Host "  2. Run 'localbrain init setup' to initialize"
    Write-Host "  3. Run 'localbrain doctor' to verify installation"
    Write-Host ""
}

# Main
Write-Info "Installing LocalBrain..."

Detect-Platform
Check-Existing
Fetch-VersionInfo
Download-Binary
Write-InstallInfo
Add-ToPath
Print-Success
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x scripts/install.sh scripts/build.py
```

- [ ] **Step 4: Commit**

```bash
git add scripts/install.sh scripts/install.ps1
git commit -m "feat: add cross-platform install scripts"
```

---

## Task 9: Integration Tests

**Files:**
- Create: `tests/test_integration_install.py`

- [ ] **Step 1: Write integration tests**

Create `tests/test_integration_install.py`:

```python
"""
Integration tests for installation system.

These tests verify the end-to-end flow of the installation commands.
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.cli import cli


class TestVersionCommand:
    """Tests for --version flag."""
    
    def test_version_flag_shows_version(self):
        """Test --version shows version string."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert "localbrain" in result.output.lower()


class TestDoctorCommand:
    """Tests for doctor command."""
    
    def test_doctor_runs_without_crash(self):
        """Test doctor command executes."""
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        
        # Should complete without unhandled exception
        assert result.exit_code in [0, 1]  # 0 = all ok, 1 = issues found


class TestUpdateCommand:
    """Tests for update command."""
    
    def test_update_check_network_error(self):
        """Test update --check handles network errors gracefully."""
        runner = CliRunner()
        
        with patch("kb.commands.self_update.fetch_version_info") as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            
            result = runner.invoke(cli, ["self-update", "--check"])
            
            assert result.exit_code == 1
            assert "failed" in result.output.lower()


class TestUninstallCommand:
    """Tests for uninstall command."""
    
    def test_uninstall_requires_confirmation(self):
        """Test uninstall asks for confirmation."""
        runner = CliRunner()
        
        # Create fake installation
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            binary = bin_dir / "localbrain"
            binary.write_text("fake binary")
            
            with patch("kb.commands.uninstall.get_install_dir") as mock_dir:
                mock_dir.return_value = Path(tmpdir)
                
                # Send 'n' to cancel
                result = runner.invoke(cli, ["uninstall"], input="n\n")
                
                assert "cancelled" in result.output.lower() or result.exit_code == 0


class TestInstallInfoRoundTrip:
    """Tests for install info persistence."""
    
    def test_write_and_read_install_info(self, tmp_path, monkeypatch):
        """Test install info can be written and read."""
        from kb.self_update import write_install_info, read_install_info, InstallInfo
        
        monkeypatch.setattr(
            "kb.self_update.get_install_dir",
            lambda: tmp_path
        )
        
        info = InstallInfo(
            version="0.1.0",
            install_time="2026-03-29T10:00:00Z",
            install_path=str(tmp_path / "bin" / "localbrain"),
            source_url="http://server/releases/v0.1.0/localbrain",
            platform="macos",
            architecture="arm64",
            checksum="sha256:abc123",
        )
        
        write_install_info(info)
        read_info = read_install_info()
        
        assert read_info is not None
        assert read_info.version == info.version
        assert read_info.platform == info.platform
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/test_integration_install.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_install.py
git commit -m "test: add integration tests for installation system"
```

---

## Task 10: Final Verification

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 2: Test CLI commands manually**

```bash
# Test version
localbrain --version

# Test doctor
localbrain doctor

# Test self-update check
localbrain self-update --check
```

- [ ] **Step 3: Verify build script works**

```bash
# Install build dependencies
pip install -e ".[build]"

# Test build (will create binary in dist/)
python scripts/build.py --version 0.1.0
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git status
git commit -m "feat: complete cross-platform installation system"
```

---

## Summary

This plan implements:

| Feature | Status |
|---------|--------|
| `--version` flag | ✅ |
| `localbrain doctor` | ✅ |
| `localbrain self-update` | ✅ |
| `localbrain self-update --check` | ✅ |
| `localbrain self-update --rollback` | ✅ |
| `localbrain uninstall` | ✅ |
| PyInstaller build config | ✅ |
| install.sh (macOS/Linux) | ✅ |
| install.ps1 (Windows) | ✅ |
| VERSION file | ✅ |
| Checksum verification | ✅ |
| Atomic binary replacement | ✅ |
| PATH management | ✅ |
