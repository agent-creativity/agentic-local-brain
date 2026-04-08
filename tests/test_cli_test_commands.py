"""
Tests for CLI test commands (kb test embedding/llm).

Tests service connectivity commands with mocked API calls.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from kb.cli import cli
from kb.processors.base import ProcessResult


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestTestCommandGroup:
    """Tests for the test command group."""

    def test_test_help_shows_subcommands(self, runner):
        """Verify kb test --help shows both subcommands."""
        result = runner.invoke(cli, ["test", "--help"])
        
        assert result.exit_code == 0
        assert "embedding" in result.output
        assert "llm" in result.output
        assert "Test service connectivity" in result.output


class TestTestEmbeddingCommand:
    """Tests for kb test embedding command."""

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_success(self, mock_from_config, mock_config_class, runner):
        """Test embedding command success case."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding.provider": "dashscope",
            "embedding.dashscope.model": "text-embedding-v4",
        }.get(key, default)
        mock_config_class.return_value = mock_config
        
        # Setup mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1, 0.2, 0.3] * 512]  # 1536 dimension vector
        mock_from_config.return_value = mock_embedder
        
        result = runner.invoke(cli, ["test", "embedding"])
        
        assert result.exit_code == 0
        assert "Testing embedding service" in result.output
        assert "Provider: dashscope" in result.output
        assert "Model: text-embedding-v4" in result.output
        assert "Vector dimension: 1536" in result.output
        assert "✓ Embedding service is working!" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_empty_result(self, mock_from_config, mock_config_class, runner):
        """Test embedding command with empty result."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock embedder returning empty result
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = []
        mock_from_config.return_value = mock_embedder
        
        result = runner.invoke(cli, ["test", "embedding"])
        
        assert result.exit_code == 1
        assert "✗ Embedding service returned empty result" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_exception(self, mock_from_config, mock_config_class, runner):
        """Test embedding command handles exceptions."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock embedder to raise exception
        mock_from_config.side_effect = ValueError("API key is missing")
        
        result = runner.invoke(cli, ["test", "embedding"])
        
        assert result.exit_code == 1
        assert "✗ Embedding service test failed" in result.output
        assert "API key is missing" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_api_error(self, mock_from_config, mock_config_class, runner):
        """Test embedding command handles API errors."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.side_effect = Exception("API rate limit exceeded")
        mock_from_config.return_value = mock_embedder
        
        result = runner.invoke(cli, ["test", "embedding"])
        
        assert result.exit_code == 1
        assert "✗ Embedding service test failed" in result.output
        assert "API rate limit exceeded" in result.output


class TestTestLLMCommand:
    """Tests for kb test llm command."""

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_success(self, mock_from_config, mock_config_class, runner):
        """Test LLM command success case."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm.provider": "dashscope",
            "llm.model": "qwen-plus",
        }.get(key, default)
        mock_config_class.return_value = mock_config
        
        # Setup mock tag extractor
        mock_extractor = MagicMock()
        mock_result = ProcessResult(
            success=True,
            data={"tags": ["machine-learning", "AI", "data-science"]},
            metadata={"tag_count": 3}
        )
        mock_extractor.process.return_value = mock_result
        mock_from_config.return_value = mock_extractor
        
        result = runner.invoke(cli, ["test", "llm"])
        
        assert result.exit_code == 0
        assert "Testing LLM service" in result.output
        assert "Provider: dashscope" in result.output
        assert "Model: qwen-plus" in result.output
        assert "Extracted tags:" in result.output
        assert "machine-learning" in result.output
        assert "✓ LLM service is working!" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_failure_result(self, mock_from_config, mock_config_class, runner):
        """Test LLM command with failed ProcessResult."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock tag extractor returning failure
        mock_extractor = MagicMock()
        mock_result = ProcessResult(
            success=False,
            data=None,
            error="Content too short"
        )
        mock_extractor.process.return_value = mock_result
        mock_from_config.return_value = mock_extractor
        
        result = runner.invoke(cli, ["test", "llm"])
        
        assert result.exit_code == 1
        assert "✗ LLM service returned empty result" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_empty_data(self, mock_from_config, mock_config_class, runner):
        """Test LLM command with empty data in result."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock tag extractor returning empty data
        mock_extractor = MagicMock()
        mock_result = ProcessResult(
            success=True,
            data={"tags": []},  # Empty tags list
            error=None
        )
        mock_extractor.process.return_value = mock_result
        mock_from_config.return_value = mock_extractor
        
        result = runner.invoke(cli, ["test", "llm"])
        
        assert result.exit_code == 1
        assert "✗ LLM service returned empty result" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_exception(self, mock_from_config, mock_config_class, runner):
        """Test LLM command handles exceptions."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock to raise exception
        mock_from_config.side_effect = ValueError("LLM API key is required")
        
        result = runner.invoke(cli, ["test", "llm"])
        
        assert result.exit_code == 1
        assert "✗ LLM service test failed" in result.output
        assert "LLM API key is required" in result.output

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_api_error(self, mock_from_config, mock_config_class, runner):
        """Test LLM command handles API errors during processing."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        # Setup mock tag extractor
        mock_extractor = MagicMock()
        mock_extractor.process.side_effect = Exception("Connection timeout")
        mock_from_config.return_value = mock_extractor
        
        result = runner.invoke(cli, ["test", "llm"])
        
        assert result.exit_code == 1
        assert "✗ LLM service test failed" in result.output
        assert "Connection timeout" in result.output


class TestExitCodes:
    """Tests to verify correct exit codes."""

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_success_exit_code_0(self, mock_from_config, mock_config_class, runner):
        """Verify exit code is 0 on embedding success."""
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 1536]
        mock_from_config.return_value = mock_embedder
        
        result = runner.invoke(cli, ["test", "embedding"])
        assert result.exit_code == 0

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.embedder.Embedder.from_config")
    def test_embedding_failure_exit_code_1(self, mock_from_config, mock_config_class, runner):
        """Verify exit code is 1 on embedding failure."""
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        mock_from_config.side_effect = Exception("Test error")
        
        result = runner.invoke(cli, ["test", "embedding"])
        assert result.exit_code == 1

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_success_exit_code_0(self, mock_from_config, mock_config_class, runner):
        """Verify exit code is 0 on LLM success."""
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        mock_extractor = MagicMock()
        mock_extractor.process.return_value = ProcessResult(
            success=True, data={"tags": ["tag1", "tag2", "tag3"]}
        )
        mock_from_config.return_value = mock_extractor
        
        result = runner.invoke(cli, ["test", "llm"])
        assert result.exit_code == 0

    @patch("kb.commands.manage.Config")
    @patch("kb.processors.tag_extractor.TagExtractor.from_config")
    def test_llm_failure_exit_code_1(self, mock_from_config, mock_config_class, runner):
        """Verify exit code is 1 on LLM failure."""
        mock_config = MagicMock()
        mock_config.get.return_value = "dashscope"
        mock_config_class.return_value = mock_config
        
        mock_from_config.side_effect = Exception("Test error")
        
        result = runner.invoke(cli, ["test", "llm"])
        assert result.exit_code == 1
