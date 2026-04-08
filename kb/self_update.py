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
class BinaryInfo:
    """Binary information for a platform."""
    path: str
    sha256: Optional[str] = None


@dataclass
class VersionInfo:
    """Version information from server."""
    version: str
    released: str
    changelog: Optional[str] = None
    binaries: dict = None  # Maps platform key to BinaryInfo
    
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
    install_type: Optional[str] = None  # 'python' or 'binary'
    venv_path: Optional[str] = None  # For Python installations


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
        # Handle missing optional fields with defaults
        return InstallInfo(
            version=data.get("version", ""),
            install_time=data.get("install_time", ""),
            install_path=data.get("install_path", ""),
            source_url=data.get("source_url", ""),
            platform=data.get("platform", ""),
            architecture=data.get("architecture", ""),
            checksum=data.get("checksum", ""),
            install_type=data.get("install_type"),
            venv_path=data.get("venv_path"),
        )
    except (json.JSONDecodeError, TypeError, KeyError) as e:
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

    # Add optional fields if present
    if info.install_type:
        data["install_type"] = info.install_type
    if info.venv_path:
        data["venv_path"] = info.venv_path

    info_path.write_text(json.dumps(data, indent=2))


def fetch_version_info(server_url: str) -> VersionInfo:
    """Fetch version information from server."""
    url = f"{server_url.rstrip('/')}/version.json"
    
    with httpx.Client(timeout=CONNECT_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    
    # Parse platforms/binaries - handle both old and new format
    # Old format: {"platforms": {"darwin-arm64": "path/to/binary"}}
    # New format: {"platforms": {"darwin-arm64": {"path": "...", "sha256": "..."}}}
    binaries = {}
    platforms = data.get("platforms", data.get("binaries", {}))
    for key, value in platforms.items():
        if isinstance(value, str):
            # Old format: just a path string
            binaries[key] = BinaryInfo(path=value)
        elif isinstance(value, dict):
            # New format: object with path and sha256
            binaries[key] = BinaryInfo(
                path=value.get("path", ""),
                sha256=value.get("sha256")
            )
    
    return VersionInfo(
        version=data.get("version", "0.0.0"),
        released=data.get("released", data.get("release_date", "")),
        changelog=data.get("changelog"),
        binaries=binaries,
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
    url = f"{server_url.rstrip('/')}/binary_installer/releases/{version}/{filename}"
    
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


def download_binary_from_info(
    server_url: str,
    binary_info: "BinaryInfo",
    dest_path: Path,
) -> Path:
    """
    Download binary using path from BinaryInfo.
    
    Args:
        server_url: Base server URL
        binary_info: BinaryInfo containing path and optional sha256
        dest_path: Destination path for the binary
        
    Returns:
        Path to downloaded temp file
    """
    url = f"{server_url.rstrip('/')}/{binary_info.path.lstrip('/')}"
    
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
        
        logger.info(f"Installing wheel from {wheel_url}")
        
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
        
        # Download new binary using path from version.json
        temp_path = download_binary_from_info(
            server_url,
            binary_info,
            bin_path,
        )
        
        # Verify checksum
        expected_checksum = binary_info.sha256
        if expected_checksum:
            expected_checksum = f"sha256:{expected_checksum}" if not expected_checksum.startswith("sha256:") else expected_checksum
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
            source_url=f"{server_url}/{binary_info.path}",
            platform=platform_key.split("-")[0],
            architecture=platform_key.split("-")[1],
            checksum=expected_checksum or "",
        )
        write_install_info(install_info)
        
        return True, f"Updated to version {version_info.version}"
        
    except httpx.HTTPError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        logger.exception("Update failed")
        return False, f"Update failed: {e}"


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
