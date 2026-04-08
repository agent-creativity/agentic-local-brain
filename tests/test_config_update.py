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
