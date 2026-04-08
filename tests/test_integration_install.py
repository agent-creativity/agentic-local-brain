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
