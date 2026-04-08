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
