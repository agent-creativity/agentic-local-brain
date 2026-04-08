"""
嵌入向量生成器测试模块

包含 Embedder、EmbeddingProvider 及其相关类的全面测试。
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.processors.embedder import (
    DashScopeEmbeddingProvider,
    Embedder,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)


class TestEmbeddingProvider:
    """EmbeddingProvider 抽象基类测试"""

    def test_abstract_method_embed(self):
        """测试 embed 抽象方法必须实现"""
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_abstract_property_dimension(self):
        """测试 dimension 抽象属性必须实现"""
        class IncompleteProvider(EmbeddingProvider):
            def embed(self, texts, **kwargs):
                return []

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_concrete_implementation(self):
        """测试完整实现"""
        class TestProvider(EmbeddingProvider):
            def embed(self, texts, **kwargs):
                return [[0.1, 0.2] for _ in texts]

            @property
            def dimension(self):
                return 2

        provider = TestProvider()
        result = provider.embed(["text1", "text2"])
        assert len(result) == 2
        assert provider.dimension == 2


class TestDashScopeEmbeddingProvider:
    """DashScopeEmbeddingProvider 测试"""

    def test_init_missing_package(self):
        """测试缺少 dashscope 包"""
        with patch('kb.processors.embedder.dashscope', None):
            with patch('kb.processors.embedder.TextEmbedding', None):
                with pytest.raises(ImportError) as exc_info:
                    DashScopeEmbeddingProvider(api_key="test_key")
                assert "dashscope package is required" in str(exc_info.value)

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_init_success(self, mock_text_embedding, mock_dashscope):
        """测试成功初始化"""
        provider = DashScopeEmbeddingProvider(
            api_key="test_api_key",
            model="text-embedding-v4"
        )
        assert provider.api_key == "test_api_key"
        assert provider.model == "text-embedding-v4"
        assert provider.dimension == 1536

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_init_custom_dimension(self, mock_text_embedding, mock_dashscope):
        """测试自定义维度"""
        provider = DashScopeEmbeddingProvider(
            api_key="test_api_key",
            model="text-embedding-v4",
            dimension=768
        )
        assert provider.dimension == 768

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_single_text(self, mock_text_embedding, mock_dashscope):
        """测试单文本向量化"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.output = {
            "embeddings": [
                {"embedding": [0.1, 0.2, 0.3]}
            ]
        }
        mock_text_embedding.call.return_value = mock_response

        provider = DashScopeEmbeddingProvider(api_key="test_key")
        result = provider.embed(["test text"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        mock_text_embedding.call.assert_called_once()

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_multiple_texts(self, mock_text_embedding, mock_dashscope):
        """测试多文本向量化"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.output = {
            "embeddings": [
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]},
                {"embedding": [0.5, 0.6]}
            ]
        }
        mock_text_embedding.call.return_value = mock_response

        provider = DashScopeEmbeddingProvider(api_key="test_key")
        result = provider.embed(["text1", "text2", "text3"])

        assert len(result) == 3
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]
        assert result[2] == [0.5, 0.6]

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_with_retries(self, mock_text_embedding, mock_dashscope):
        """测试重试机制"""
        # 第一次失败，第二次成功
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.message = "Internal Server Error"

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.output = {
            "embeddings": [{"embedding": [0.1, 0.2]}]
        }

        mock_text_embedding.call.side_effect = [
            mock_response_fail,
            mock_response_success
        ]

        provider = DashScopeEmbeddingProvider(api_key="test_key")
        result = provider.embed(["test text"], max_retries=3)

        assert len(result) == 1
        assert mock_text_embedding.call.call_count == 2

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_max_retries_exceeded(self, mock_text_embedding, mock_dashscope):
        """测试达到最大重试次数"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.message = "Service Unavailable"
        mock_text_embedding.call.return_value = mock_response

        provider = DashScopeEmbeddingProvider(api_key="test_key")

        with pytest.raises(Exception) as exc_info:
            provider.embed(["test text"], max_retries=2)

        assert "500" in str(exc_info.value)
        assert mock_text_embedding.call.call_count == 2

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_empty_texts(self, mock_text_embedding, mock_dashscope):
        """测试空文本列表"""
        provider = DashScopeEmbeddingProvider(api_key="test_key")

        with pytest.raises(ValueError) as exc_info:
            provider.embed([])

        assert "cannot be empty" in str(exc_info.value)

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_batch_processing(self, mock_text_embedding, mock_dashscope):
        """测试批量处理"""
        # Mock response that returns embeddings based on input size
        def mock_call_side_effect(**kwargs):
            input_texts = kwargs.get('input', [])
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.output = {
                "embeddings": [
                    {"embedding": [0.1 * (i + 1), 0.2 * (i + 1)]}
                    for i in range(len(input_texts))
                ]
            }
            return mock_response

        mock_text_embedding.call.side_effect = mock_call_side_effect

        provider = DashScopeEmbeddingProvider(api_key="test_key")
        # 30 个文本，batch_size=10，应该调用 3 次
        texts = [f"text{i}" for i in range(30)]
        result = provider.embed(texts, batch_size=10)

        assert len(result) == 30
        assert mock_text_embedding.call.call_count == 3

    @patch('kb.processors.embedder.dashscope')
    @patch('kb.processors.embedder.TextEmbedding')
    def test_embed_with_extra_kwargs(self, mock_text_embedding, mock_dashscope):
        """测试额外参数传递"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.output = {"embeddings": [{"embedding": [0.1]}]}
        mock_text_embedding.call.return_value = mock_response

        provider = DashScopeEmbeddingProvider(
            api_key="test_key",
            dimensions=1536
        )
        provider.embed(["test"], text_type="query")

        call_kwargs = mock_text_embedding.call.call_args[1]
        assert call_kwargs.get("text_type") == "query"


class TestOpenAICompatibleEmbeddingProvider:
    """OpenAICompatibleEmbeddingProvider 测试"""

    @patch('kb.processors.embedder.OpenAI', None)
    def test_init_missing_package(self):
        """测试缺少 openai 包"""
        with pytest.raises(ImportError) as exc_info:
            OpenAICompatibleEmbeddingProvider(
                api_key="test_key",
                base_url="http://test.com",
                model="test-model"
            )
        assert "openai package is required" in str(exc_info.value)

    @patch('kb.processors.embedder.OpenAI')
    def test_init_success(self, mock_openai_class):
        """测试成功初始化"""
        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_api_key",
            base_url="http://localhost:11434/v1",
            model="bge-m3"
        )
        assert provider.api_key == "test_api_key"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.model == "bge-m3"

    @patch('kb.processors.embedder.OpenAI')
    def test_init_custom_dimension(self, mock_openai_class):
        """测试自定义维度"""
        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_api_key",
            base_url="http://localhost:11434/v1",
            model="bge-m3",
            dimension=1024
        )
        assert provider.dimension == 1024

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_single_text(self, mock_openai_class):
        """测试单文本向量化"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_data = Mock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_response.data = [mock_data]
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )
        result = provider.embed(["test text"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_multiple_texts(self, mock_openai_class):
        """测试多文本向量化"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_data1 = Mock()
        mock_data1.embedding = [0.1, 0.2]
        mock_data2 = Mock()
        mock_data2.embedding = [0.3, 0.4]
        mock_response.data = [mock_data1, mock_data2]
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )
        result = provider.embed(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_with_retries(self, mock_openai_class):
        """测试重试机制"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # 第一次失败，第二次成功
        mock_client.embeddings.create.side_effect = [
            Exception("Connection error"),
            Mock(data=[Mock(embedding=[0.1, 0.2])])
        ]

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )
        result = provider.embed(["test text"], max_retries=3)

        assert len(result) == 1
        assert mock_client.embeddings.create.call_count == 2

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_max_retries_exceeded(self, mock_openai_class):
        """测试达到最大重试次数"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.embeddings.create.side_effect = Exception("API Error")

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )

        with pytest.raises(Exception) as exc_info:
            provider.embed(["test text"], max_retries=2)

        assert "API Error" in str(exc_info.value)
        assert mock_client.embeddings.create.call_count == 2

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_empty_texts(self, mock_openai_class):
        """测试空文本列表"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )

        with pytest.raises(ValueError) as exc_info:
            provider.embed([])

        assert "cannot be empty" in str(exc_info.value)

    @patch('kb.processors.embedder.OpenAI')
    def test_embed_batch_processing(self, mock_openai_class):
        """测试批量处理"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock response that returns embeddings based on input size
        def mock_create_side_effect(**kwargs):
            input_texts = kwargs.get('input', [])
            mock_response = Mock()
            mock_response.data = [
                Mock(embedding=[0.1 * (i + 1), 0.2 * (i + 1)])
                for i in range(len(input_texts))
            ]
            return mock_response

        mock_client.embeddings.create.side_effect = mock_create_side_effect

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )
        # 30 个文本，batch_size=10，应该调用 3 次
        texts = [f"text{i}" for i in range(30)]
        result = provider.embed(texts, batch_size=10)

        assert len(result) == 30
        assert mock_client.embeddings.create.call_count == 3

    @patch('kb.processors.embedder.OpenAI')
    def test_dimension_auto_update(self, mock_openai_class):
        """测试维度自动更新"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 768)]
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test_key",
            base_url="http://test.com",
            model="test-model"
        )
        assert provider.dimension == 0  # 初始为 0

        provider.embed(["test"])
        assert provider.dimension == 768  # 自动更新


class TestEmbedder:
    """Embedder 测试"""

    def test_init(self):
        """测试初始化"""
        mock_provider = Mock(spec=EmbeddingProvider)
        embedder = Embedder(provider=mock_provider, param1="value1")
        assert embedder.provider == mock_provider
        assert embedder.config == {"param1": "value1"}

    def test_from_config_dashscope(self):
        """测试从配置创建 DashScope 提供者"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "dashscope",
                "dashscope": {
                    "model": "text-embedding-v4",
                    "api_key": "test_api_key"
                }
            }
        }.get(key, default)

        with patch('kb.processors.embedder.DashScopeEmbeddingProvider') as mock_provider:
            embedder = Embedder.from_config(mock_config)
            assert embedder is not None

    def test_from_config_openai_compatible(self):
        """测试从配置创建 OpenAI 兼容提供者"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "openai_compatible",
                "openai_compatible": {
                    "model": "bge-m3",
                    "api_key": "test_api_key",
                    "base_url": "http://localhost:11434/v1"
                }
            }
        }.get(key, default)

        with patch('kb.processors.embedder.OpenAICompatibleEmbeddingProvider') as mock_provider:
            embedder = Embedder.from_config(mock_config)
            assert embedder is not None

    def test_from_config_missing_api_key_dashscope(self):
        """测试 DashScope 缺少 API 密钥"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "dashscope",
                "dashscope": {
                    "model": "text-embedding-v4",
                    "api_key": ""
                }
            }
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            Embedder.from_config(mock_config)
        assert "API key is required" in str(exc_info.value)

    def test_from_config_missing_api_key_openai(self):
        """测试 OpenAI 缺少 API 密钥"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "openai_compatible",
                "openai_compatible": {
                    "model": "bge-m3",
                    "api_key": "",
                    "base_url": "http://localhost:11434/v1"
                }
            }
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            Embedder.from_config(mock_config)
        assert "API key is required" in str(exc_info.value)

    def test_from_config_openai_missing_base_url(self):
        """测试 OpenAI 提供者缺少 base_url"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "openai_compatible",
                "openai_compatible": {
                    "model": "bge-m3",
                    "api_key": "test_key",
                    "base_url": ""
                }
            }
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            Embedder.from_config(mock_config)
        assert "base_url is required" in str(exc_info.value)

    def test_from_config_openai_missing_model(self):
        """测试 OpenAI 提供者缺少 model"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "openai_compatible",
                "openai_compatible": {
                    "model": "",
                    "api_key": "test_key",
                    "base_url": "http://localhost:11434/v1"
                }
            }
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            Embedder.from_config(mock_config)
        assert "model is required" in str(exc_info.value)

    def test_from_config_unsupported_provider(self):
        """测试不支持的提供者"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "unsupported",
            }
        }.get(key, default)

        with pytest.raises(ValueError) as exc_info:
            Embedder.from_config(mock_config)
        assert "Unsupported embedding provider" in str(exc_info.value)

    def test_embed_success(self):
        """测试成功向量化"""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        embedder = Embedder(provider=mock_provider)
        result = embedder.embed(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        mock_provider.embed.assert_called_once()

    def test_embed_empty_texts(self):
        """测试空文本列表"""
        mock_provider = Mock(spec=EmbeddingProvider)
        embedder = Embedder(provider=mock_provider)

        with pytest.raises(ValueError) as exc_info:
            embedder.embed([])

        assert "cannot be empty" in str(exc_info.value)

    def test_embed_with_kwargs(self):
        """测试传递额外参数"""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.embed.return_value = [[0.1, 0.2]]

        embedder = Embedder(provider=mock_provider)
        embedder.embed(["text"], max_retries=5, batch_size=10)

        mock_provider.embed.assert_called_once_with(
            ["text"], max_retries=5, batch_size=10
        )

    def test_dimension_property(self):
        """测试 dimension 属性"""
        mock_provider = Mock(spec=EmbeddingProvider)
        mock_provider.dimension = 1536

        embedder = Embedder(provider=mock_provider)
        assert embedder.dimension == 1536

    def test_create_dashscope_provider(self):
        """测试创建 DashScope 提供者"""
        with patch('kb.processors.embedder.DashScopeEmbeddingProvider') as mock_class:
            Embedder.create_dashscope_provider(
                api_key="test_key",
                model="text-embedding-v4"
            )
            mock_class.assert_called_once_with(
                api_key="test_key",
                model="text-embedding-v4"
            )

    def test_create_openai_provider(self):
        """测试创建 OpenAI 提供者"""
        with patch('kb.processors.embedder.OpenAICompatibleEmbeddingProvider') as mock_class:
            Embedder.create_openai_provider(
                api_key="test_key",
                base_url="http://test.com",
                model="test-model"
            )
            mock_class.assert_called_once_with(
                api_key="test_key",
                base_url="http://test.com",
                model="test-model"
            )


class TestEmbedderIntegration:
    """Embedder 集成测试"""

    @patch('kb.processors.embedder.litellm', new_callable=lambda: MagicMock)
    @patch('kb.processors.embedder.LiteLLMEmbeddingProvider')
    def test_full_workflow_dashscope(self, mock_provider_class, mock_litellm):
        """测试完整 DashScope 工作流程（通过 LiteLLM）"""
        mock_provider = Mock()
        mock_provider.embed.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        mock_provider.dimension = 3
        mock_provider_class.return_value = mock_provider

        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "dashscope",
                "dashscope": {
                    "model": "text-embedding-v4",
                    "api_key": "test_api_key"
                }
            }
        }.get(key, default)

        embedder = Embedder.from_config(mock_config)
        result = embedder.embed(["文档1", "文档2"])

        assert len(result) == 2
        assert embedder.dimension == 3

    @patch('kb.processors.embedder.litellm', new_callable=lambda: MagicMock)
    @patch('kb.processors.embedder.LiteLLMEmbeddingProvider')
    def test_full_workflow_openai(self, mock_provider_class, mock_litellm):
        """测试完整 OpenAI 工作流程（通过 LiteLLM）"""
        mock_provider = Mock()
        mock_provider.embed.return_value = [
            [0.1, 0.2],
            [0.3, 0.4]
        ]
        mock_provider.dimension = 2
        mock_provider_class.return_value = mock_provider

        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "embedding": {
                "provider": "openai_compatible",
                "openai_compatible": {
                    "model": "bge-m3",
                    "api_key": "test_api_key",
                    "base_url": "http://localhost:11434/v1"
                }
            }
        }.get(key, default)

        embedder = Embedder.from_config(mock_config)
        result = embedder.embed(["文档1", "文档2"])

        assert len(result) == 2
        assert embedder.dimension == 2

    def test_env_var_substitution(self, monkeypatch):
        """测试环境变量替换"""
        monkeypatch.setenv("TEST_EMBEDDING_KEY", "env_key_123")

        config_content = """
embedding:
  provider: dashscope
  dashscope:
    model: text-embedding-v4
    api_key: ${TEST_EMBEDDING_KEY}
"""
        config_path = Path("/tmp/test_kb_embedder_config.yaml")
        config_path.write_text(config_content)

        try:
            from kb.config import Config
            config = Config(config_path)
            api_key = config.get("embedding.dashscope.api_key")
            assert api_key == "env_key_123"
        finally:
            config_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
