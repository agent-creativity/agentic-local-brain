"""
标签提取器测试模块

包含 TagExtractor 及其相关类的全面测试。
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.processors.base import BaseProcessor, ProcessResult
from kb.processors.tag_extractor import (
    LLMProvider,
    LiteLLMProvider,
    TagExtractor,
)


class TestProcessResult:
    """ProcessResult 数据类测试"""

    def test_success_result_repr(self):
        """测试成功结果的字符串表示"""
        result = ProcessResult(
            success=True,
            data=["tag1", "tag2"],
            metadata={"tag_count": 2}
        )
        repr_str = repr(result)
        assert "success=True" in repr_str
        assert "metadata=" in repr_str

    def test_failure_result_repr(self):
        """测试失败结果的字符串表示"""
        result = ProcessResult(
            success=False,
            error="Test error"
        )
        repr_str = repr(result)
        assert "success=False" in repr_str
        assert "error=" in repr_str

    def test_default_values(self):
        """测试默认值"""
        result = ProcessResult(success=True)
        assert result.data is None
        assert result.metadata == {}
        assert result.error is None


class TestBaseProcessor:
    """BaseProcessor 基类测试"""

    def test_abstract_method(self):
        """测试抽象方法必须实现"""
        with pytest.raises(TypeError):
            BaseProcessor()

    def test_concrete_implementation(self):
        """测试具体实现"""
        class TestProcessor(BaseProcessor):
            def process(self, data, **kwargs):
                return ProcessResult(success=True, data=data)

        processor = TestProcessor(param1="value1")
        assert processor.config == {"param1": "value1"}
        result = processor.process("test_data")
        assert result.success is True
        assert result.data == "test_data"


class TestLLMProvider:
    """LLMProvider 抽象基类测试"""

    def test_abstract_method(self):
        """测试抽象方法必须实现"""
        with pytest.raises(TypeError):
            LLMProvider()


class TestTagExtractor:
    """TagExtractor 测试"""

    def test_init(self):
        """测试初始化"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(
            provider=mock_provider,
            min_tags=2,
            max_tags=4
        )
        assert extractor.provider == mock_provider
        assert extractor.min_tags == 2
        assert extractor.max_tags == 4

    def test_from_config_dashscope(self):
        """测试从配置创建 DashScope 提供者（向后兼容，实际创建 LiteLLMProvider）"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "dashscope",
                "model": "qwen-plus",
                "api_key": "test_api_key"
            },
            "tag_extraction": {
                "min_tags": 3,
                "max_tags": 5
            }
        }.get(key, default)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_provider_class:
            mock_provider_class.return_value = Mock(spec=LiteLLMProvider)
            extractor = TagExtractor.from_config(mock_config)
            mock_provider_class.assert_called_once_with(
                api_key="test_api_key",
                model="dashscope/qwen-plus"
            )
            assert extractor.min_tags == 3
            assert extractor.max_tags == 5

    def test_from_config_openai_compatible(self):
        """测试从配置创建 OpenAI 兼容提供者（向后兼容，实际创建 LiteLLMProvider）"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "openai_compatible",
                "model": "qwen-plus",
                "api_key": "test_api_key",
                "base_url": "http://localhost:11434/v1"
            },
            "tag_extraction": {}
        }.get(key, default)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_provider_class:
            mock_provider_class.return_value = Mock(spec=LiteLLMProvider)
            extractor = TagExtractor.from_config(mock_config)
            mock_provider_class.assert_called_once_with(
                api_key="test_api_key",
                model="openai/qwen-plus",
                api_base="http://localhost:11434/v1"
            )
            assert extractor is not None

    def test_from_config_litellm(self):
        """测试 provider: litellm 直通路径"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "litellm",
                "model": "anthropic/claude-3-haiku",
                "api_key": "test_api_key"
            },
            "tag_extraction": {}
        }.get(key, default)

        with patch('kb.processors.tag_extractor.LiteLLMProvider') as mock_provider_class:
            mock_provider_class.return_value = Mock(spec=LiteLLMProvider)
            extractor = TagExtractor.from_config(mock_config)
            mock_provider_class.assert_called_once_with(
                api_key="test_api_key",
                model="anthropic/claude-3-haiku"
            )
            assert extractor is not None

    def test_from_config_missing_api_key(self):
        """测试缺少 API 密钥"""
        mock_config = Mock()
        mock_config.get.return_value = {
            "provider": "dashscope",
            "model": "qwen-plus",
            "api_key": ""
        }

        with pytest.raises(ValueError) as exc_info:
            TagExtractor.from_config(mock_config)
        assert "API key is required" in str(exc_info.value)

    def test_from_config_unsupported_provider(self):
        """测试不支持的提供者"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "unsupported",
                "api_key": "test_key"
            },
            "tag_extraction": {}
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            TagExtractor.from_config(mock_config)
        assert "Unsupported LLM provider" in str(exc_info.value)

    def test_from_config_openai_missing_base_url(self):
        """测试 OpenAI 提供者缺少 base_url"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "openai_compatible",
                "api_key": "test_key",
                "model": "test-model"
            },
            "tag_extraction": {}
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            TagExtractor.from_config(mock_config)
        assert "base_url is required" in str(exc_info.value)

    def test_process_empty_title(self):
        """测试空标题"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor.process(title="", content="test content")
        assert result.success is False
        assert "Title cannot be empty" in result.error

    def test_process_empty_content(self):
        """测试空内容"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor.process(title="Test Title", content="")
        assert result.success is False
        assert "Content cannot be empty" in result.error

    def test_process_success(self):
        """测试成功提取标签"""
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.generate.return_value = "机器学习,人工智能,深度学习,算法"

        extractor = TagExtractor(provider=mock_provider)
        result = extractor.process(
            title="机器学习入门指南",
            content="机器学习是人工智能的一个重要分支，涉及算法和数据分析。"
        )

        assert result.success is True
        assert isinstance(result.data, dict)
        assert 'tags' in result.data
        assert len(result.data['tags']) >= 3
        assert "tag_count" in result.metadata

    def test_process_with_temperature(self):
        """测试自定义温度参数"""
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.generate.return_value = "标签1,标签2,标签3"

        extractor = TagExtractor(provider=mock_provider)
        result = extractor.process(
            title="Test",
            content="Test content",
            temperature=0.7
        )

        assert result.success is True
        mock_provider.generate.assert_called_once()
        call_kwargs = mock_provider.generate.call_args[1]
        assert call_kwargs['temperature'] == 0.7

    def test_parse_response_comma_separated(self):
        """测试解析逗号分隔的标签"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor._parse_response("机器学习,人工智能,深度学习")
        assert result['tags'] == ["机器学习", "人工智能", "深度学习"]

    def test_parse_response_json_format(self):
        """测试解析 JSON 格式的标签"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor._parse_response('["机器学习", "人工智能", "深度学习"]')
        assert result['tags'] == ["机器学习", "人工智能", "深度学习"]

    def test_parse_response_with_quotes(self):
        """测试解析带引号的标签"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor._parse_response('"机器学习","人工智能","深度学习"')
        assert result['tags'] == ["机器学习", "人工智能", "深度学习"]

    def test_parse_response_deduplication(self):
        """测试标签去重"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor._parse_response("机器学习,人工智能,机器学习,深度学习,人工智能")
        assert result['tags'] == ["机器学习", "人工智能", "深度学习"]

    def test_parse_response_filter_short(self):
        """测试过滤过短的标签"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider)

        result = extractor._parse_response("机器学习,a,人工智能,b,深度学习")
        # 单字符标签应该被过滤
        assert "a" not in result['tags']
        assert "b" not in result['tags']

    def test_pad_tags_from_title(self):
        """测试从标题补充标签"""
        mock_provider = Mock(spec=LLMProvider)
        extractor = TagExtractor(provider=mock_provider, min_tags=3)

        tags = extractor._pad_tags(["机器学习"], "人工智能与深度学习入门")
        # Should have at least 2 tags (机器学习 + extracted from title)
        assert len(tags) >= 2
        assert "机器学习" in tags

    def test_process_truncates_long_content(self):
        """测试长内容截断"""
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.generate.return_value = "标签1,标签2,标签3"

        extractor = TagExtractor(provider=mock_provider)
        long_content = "x" * 5000

        result = extractor.process(title="Test", content=long_content)
        assert result.success is True

        # 验证调用时内容被截断
        call_args = mock_provider.generate.call_args
        prompt = call_args[1]['prompt']
        assert len(prompt) < 3000  # 标题500 + 内容2000 + 提示词

    def test_process_handles_exception(self):
        """测试异常处理"""
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.generate.side_effect = Exception("API Error")

        extractor = TagExtractor(provider=mock_provider)
        result = extractor.process(title="Test", content="Test content")

        assert result.success is False
        assert "API Error" in result.error


class TestTagExtractorIntegration:
    """TagExtractor 集成测试"""

    @patch('kb.processors.tag_extractor.LiteLLMProvider')
    def test_full_workflow(self, mock_provider_class):
        """测试完整工作流程"""
        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = "机器学习,人工智能,深度学习,神经网络,算法优化"
        mock_provider_class.return_value = mock_provider

        # 创建提取器
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "llm": {
                "provider": "dashscope",
                "model": "qwen-plus",
                "api_key": "test_api_key"
            },
            "tag_extraction": {
                "min_tags": 3,
                "max_tags": 5
            }
        }.get(key, default)

        extractor = TagExtractor.from_config(mock_config)

        # 执行提取
        result = extractor.process(
            title="深度学习在自然语言处理中的应用",
            content="""
            深度学习是机器学习的一个子领域，使用多层神经网络来学习数据的层次表示。
            在自然语言处理中，深度学习模型如 Transformer 和 BERT 已经取得了显著的成果。
            这些模型能够理解语言的复杂模式，实现文本分类、情感分析、机器翻译等任务。
            """
        )

        # 验证结果
        assert result.success is True
        assert isinstance(result.data, dict)
        assert 'tags' in result.data
        assert 3 <= len(result.data['tags']) <= 5
        assert all(isinstance(tag, str) for tag in result.data['tags'])
        assert "tag_count" in result.metadata

    def test_env_var_substitution(self, monkeypatch):
        """测试环境变量替换"""
        monkeypatch.setenv("TEST_API_KEY", "env_api_key_123")

        # 创建临时配置文件
        config_content = """
llm:
  provider: dashscope
  model: qwen-plus
  api_key: ${TEST_API_KEY}
"""
        config_path = Path("/tmp/test_kb_config.yaml")
        config_path.write_text(config_content)

        try:
            from kb.config import Config
            config = Config(config_path)
            api_key = config.get("llm.api_key")
            assert api_key == "env_api_key_123"
        finally:
            config_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
