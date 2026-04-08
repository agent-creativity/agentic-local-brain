"""
Version management module.

Version is read from VERSION file at package root.
For PyInstaller frozen binaries, version is embedded at build time.
"""

import sys
from pathlib import Path

try:
    from importlib.metadata import version as get_pkg_version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version as get_pkg_version, PackageNotFoundError


def _read_version_file() -> str:
    """Read version from VERSION file or package metadata."""
    # Try to find VERSION file relative to this module (dev/source mode)
    version_file = Path(__file__).parent.parent / "VERSION"
    
    if version_file.exists():
        return version_file.read_text().strip()
    
    # Fallback: try importlib.metadata for pip-installed packages
    try:
        return get_pkg_version("localbrain")
    except PackageNotFoundError:
        pass
    
    # Absolute last resort
    return "0.1.0"


def get_version() -> str:
    """Get the current version string."""
    # For frozen PyInstaller binaries, check for embedded version
    if getattr(sys, 'frozen', False):
        # PyInstaller sets this attribute
        # VERSION file should be bundled via --add-data
        base_path = Path(sys.executable).parent
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
        "frozen": getattr(sys, 'frozen', False),
    }


__version__ = get_version()
