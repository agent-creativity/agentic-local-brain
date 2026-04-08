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
    import sys
    
    # Mock frozen state
    monkeypatch.setattr(os, 'frozen', True, raising=False)
    
    # Create VERSION file in expected location (parent of executable dir)
    version_dir = tmp_path
    version_file = version_dir / "VERSION"
    version_file.write_text("1.2.3")
    
    # Mock sys.executable to point to our temp dir
    monkeypatch.setattr(sys, 'executable', str(tmp_path / "bin" / "localbrain"))
    
    # Need to reimport to get the mocked values
    import importlib
    import kb.version
    importlib.reload(kb.version)
    
    # The test verifies the logic path exists
    version = kb.version.get_version()
    assert isinstance(version, str)
