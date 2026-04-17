"""
Tests for the `kb web` CLI command.
"""

import sys
from unittest.mock import patch, MagicMock
from types import ModuleType

import pytest
from click.testing import CliRunner

from kb.cli import cli

runner = CliRunner()


def create_uvicorn_mock():
    """Create a proper uvicorn mock module."""
    uvicorn_mock = ModuleType("uvicorn")
    uvicorn_mock.run = MagicMock()
    return uvicorn_mock


class TestWebCommandHelp:
    """Test `kb web --help` output."""
    
    def test_help_shows_options(self):
        """Test that --help shows host, port, and reload options."""
        result = runner.invoke(cli, ["web", "--help"])
        
        assert result.exit_code == 0
        assert "--host" in result.output or "-h" in result.output
        assert "--port" in result.output or "-p" in result.output
        assert "--reload" in result.output
        assert "Start the Local Brain web interface" in result.output


class TestWebCommandDefaults:
    """Test `kb web` with default settings."""
    
    def test_web_with_defaults(self):
        """Test that uvicorn.run is called with correct defaults."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                # Return default when key not found (second param is default)
                mock_config.get.side_effect = lambda key, default=None: default
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web"])
        
        # Check output contains expected messages
        assert "Starting Local Brain Web UI" in result.output
        assert "127.0.0.1" in result.output
        assert "11201" in result.output
        assert "/docs" in result.output
        
        # Verify uvicorn.run was called with defaults
        uvicorn_mock.run.assert_called_once_with(
            "kb.web.app:app",
            host="127.0.0.1",
            port=11201,
            reload=False,
        )


class TestWebCommandCustomOptions:
    """Test `kb web` with custom host/port."""
    
    def test_web_with_custom_host_port(self):
        """Test that custom host/port are passed to uvicorn."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config.get.return_value = None
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web", "--host", "0.0.0.0", "--port", "3000"])
        
        # Check output shows custom values
        assert "0.0.0.0" in result.output
        assert "3000" in result.output
        
        # Verify uvicorn.run was called with custom values
        uvicorn_mock.run.assert_called_once_with(
            "kb.web.app:app",
            host="0.0.0.0",
            port=3000,
            reload=False,
        )


class TestWebCommandReload:
    """Test `kb web --reload` option."""
    
    def test_web_with_reload_flag(self):
        """Test that --reload flag is passed to uvicorn."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                # Return default when key not found (second param is default)
                mock_config.get.side_effect = lambda key, default=None: default
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web", "--reload"])
        
        # Verify uvicorn.run was called with reload=True
        uvicorn_mock.run.assert_called_once_with(
            "kb.web.app:app",
            host="127.0.0.1",
            port=11201,
            reload=True,
        )


class TestWebCommandMissingUvicorn:
    """Test `kb web` when uvicorn is not installed."""
    
    def test_web_missing_uvicorn_shows_install_instructions(self):
        """Test that missing uvicorn shows install instructions and exits with code 1."""
        # Create a mock that raises ImportError when accessed
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == "uvicorn":
                raise ImportError("No module named 'uvicorn'")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, "__import__", side_effect=mock_import):
            result = runner.invoke(cli, ["web"])
        
        # Should exit with code 1
        assert result.exit_code == 1
        
        # Should show error message and install instructions
        assert "Web UI requires additional dependencies" in result.output
        assert "pip install fastapi uvicorn" in result.output


class TestWebCommandOutput:
    """Test `kb web` output messages."""
    
    def test_output_contains_url_and_docs(self):
        """Test that output contains URL and API docs URL."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                # Return default when key not found (second param is default)
                mock_config.get.side_effect = lambda key, default=None: default
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web"])
        
        # Check output messages
        assert "Starting Local Brain Web UI" in result.output
        assert "URL: http://127.0.0.1:11201" in result.output
        assert "API Docs: http://127.0.0.1:11201/docs" in result.output
        assert "Press Ctrl+C to stop the server" in result.output


class TestWebCommandConfigValues:
    """Test `kb web` uses config values when available."""
    
    def test_web_uses_config_values(self):
        """Test that config values are used when no CLI args provided."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config.get.side_effect = lambda key, default=None: {
                    "web.host": "192.168.1.100",
                    "web.port": 9000,
                }.get(key, default)
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web"])
        
        # Verify uvicorn.run was called with config values
        uvicorn_mock.run.assert_called_once_with(
            "kb.web.app:app",
            host="192.168.1.100",
            port=9000,
            reload=False,
        )


class TestWebCommandCLIOverridesConfig:
    """Test that CLI args override config values."""
    
    def test_cli_args_override_config(self):
        """Test that CLI arguments take precedence over config values."""
        uvicorn_mock = create_uvicorn_mock()
        
        with patch.dict("sys.modules", {"uvicorn": uvicorn_mock}):
            with patch("kb.commands.manage.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config.get.side_effect = lambda key, default=None: {
                    "web.host": "192.168.1.100",
                    "web.port": 9000,
                }.get(key, default)
                mock_config.validate_services.return_value = {}
                mock_config_class.return_value = mock_config
                
                result = runner.invoke(cli, ["web", "--host", "localhost", "--port", "5000"])
        
        # Verify CLI args override config
        uvicorn_mock.run.assert_called_once_with(
            "kb.web.app:app",
            host="localhost",
            port=5000,
            reload=False,
        )
