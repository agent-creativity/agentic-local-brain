"""Tests for self-update command."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.cli import cli


def test_self_update_check_shows_version():
    """Test self-update --check shows version info."""
    runner = CliRunner()
    
    with patch("kb.commands.self_update.fetch_version_info") as mock_fetch:
        mock_fetch.return_value = MagicMock(
            version="0.2.0",
            released="2026-03-29",
            changelog=None,
        )
        
        result = runner.invoke(cli, ["self-update", "--check"])
        
        # Check for any of the possible version messages
        assert ("Update available" in result.output or 
                "up to date" in result.output.lower() or
                "pre-release version" in result.output)


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
    
    with patch("kb.commands.self_update.perform_update") as mock_update:
        mock_update.return_value = (False, "Network error")
        
        result = runner.invoke(cli, ["self-update"])
        
        assert result.exit_code == 1


def test_self_update_check_network_error():
    """Test self-update --check handles network errors."""
    runner = CliRunner()
    
    with patch("kb.commands.self_update.fetch_version_info") as mock_fetch:
        mock_fetch.side_effect = Exception("Connection refused")
        
        result = runner.invoke(cli, ["self-update", "--check"])
        
        assert result.exit_code == 1
        assert "failed" in result.output.lower()
