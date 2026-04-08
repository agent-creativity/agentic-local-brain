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
