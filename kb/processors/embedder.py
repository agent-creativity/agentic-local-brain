"""
嵌入向量生成器模块

基于多种提供者（DashScope、OpenAI 兼容 API）的文本向量化功能。
支持批量向量化和错误重试机制。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import at module level for proper mocking
try:
    import dashscope
    from dashscope import TextEmbedding
except ImportError:
    dashscope = None
    TextEmbedding = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import litellm
except ImportError:
    litellm = None

from kb.config import Config


class EmbeddingProvider(ABC):
    """嵌入向量提供者抽象基类"""

    @abstractmethod
    def embed(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        将文本列表转换为向量列表

        Args:
            texts: 待向量化的文本列表
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 向量列表，每个向量是一个浮点数列表

        Raises:
            Exception: API 调用失败或达到最大重试次数
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        获取向量维度

        Returns:
            int: 向量维度
        """
        pass


class DashScopeEmbeddingProvider(EmbeddingProvider):
    """
    DashScope (阿里云百炼) 嵌入向量提供者

    使用 text-embedding-v4 模型进行文本向量化。
    """

    # 默认维度（text-embedding-v4 的维度）
    DEFAULT_DIMENSION = 1536

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v4",
        dimension: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        初始化 DashScope 嵌入向量提供者

        Args:
            api_key: DashScope API 密钥
            model: 模型名称，默认为 text-embedding-v4
            dimension: 向量维度，如果不指定则使用模型默认维度
            **kwargs: 额外的配置参数
        """
        if dashscope is None or TextEmbedding is None:
            raise ImportError(
                "dashscope package is required. Install it with: pip install dashscope"
            )

        self.dashscope = dashscope
        self.TextEmbedding = TextEmbedding
        self.api_key = api_key
        self.model = model
        self._dimension = dimension or self.DEFAULT_DIMENSION
        self.dashscope.api_key = api_key
        self.extra_kwargs = kwargs

    @property
    def dimension(self) -> int:
        """
        获取向量维度

        Returns:
            int: 向量维度
        """
        return self._dimension

    def embed(
        self,
        texts: List[str],
        max_retries: int = 3,
        batch_size: int = 25,
        **kwargs: Any
    ) -> List[List[float]]:
        """
        调用 DashScope API 生成文本向量

        Args:
            texts: 待向量化的文本列表
            max_retries: 最大重试次数，默认为 3
            batch_size: 批量处理大小，默认为 25
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 向量列表

        Raises:
            Exception: API 调用失败或达到最大重试次数
            ValueError: 输入文本列表为空
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        all_embeddings: List[List[float]] = []
        last_error: Optional[Exception] = None

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._embed_batch(
                batch, max_retries, **kwargs
            )
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _embed_batch(
        self,
        texts: List[str],
        max_retries: int,
        **kwargs: Any
    ) -> List[List[float]]:
        """
        处理单个批次的向量化

        Args:
            texts: 批次文本列表
            max_retries: 最大重试次数
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 批次向量列表

        Raises:
            Exception: API 调用失败
        """
        for attempt in range(max_retries):
            try:
                response = self.TextEmbedding.call(
                    model=self.model,
                    input=texts,
                    **{**self.extra_kwargs, **kwargs}
                )

                if response.status_code == 200:
                    embeddings = []
                    for item in response.output["embeddings"]:
                        embeddings.append(item["embedding"])
                    return embeddings
                else:
                    last_error = Exception(
                        f"DashScope API error: {response.status_code} - {response.message}"
                    )

            except Exception as e:
                last_error = e

            # 指数退避重试
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)

        raise last_error or Exception(
            "DashScope API call failed after maximum retries"
        )


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI 兼容 API 嵌入向量提供者

    支持任何兼容 OpenAI API 格式的服务（如 vLLM、Ollama 等）。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimension: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        初始化 OpenAI 兼容嵌入向量提供者

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            dimension: 向量维度，如果不指定则通过 API 获取
            **kwargs: 额外的配置参数
        """
        if OpenAI is None:
            raise ImportError(
                "openai package is required. Install it with: pip install openai"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._dimension = dimension
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.extra_kwargs = kwargs

    @property
    def dimension(self) -> int:
        """
        获取向量维度

        Returns:
            int: 向量维度
        """
        return self._dimension or 0

    def embed(
        self,
        texts: List[str],
        max_retries: int = 3,
        batch_size: int = 25,
        **kwargs: Any
    ) -> List[List[float]]:
        """
        调用 OpenAI 兼容 API 生成文本向量

        Args:
            texts: 待向量化的文本列表
            max_retries: 最大重试次数，默认为 3
            batch_size: 批量处理大小，默认为 25
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 向量列表

        Raises:
            Exception: API 调用失败或达到最大重试次数
            ValueError: 输入文本列表为空
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        all_embeddings: List[List[float]] = []
        last_error: Optional[Exception] = None

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_embeddings = self._embed_batch(
                    batch, max_retries, **kwargs
                )
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                last_error = e
                # 如果是最后一批，则抛出异常
                if i + batch_size >= len(texts):
                    raise last_error

        return all_embeddings

    def _embed_batch(
        self,
        texts: List[str],
        max_retries: int,
        **kwargs: Any
    ) -> List[List[float]]:
        """
        处理单个批次的向量化

        Args:
            texts: 批次文本列表
            max_retries: 最大重试次数
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 批次向量列表

        Raises:
            Exception: API 调用失败
        """
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    **{**self.extra_kwargs, **kwargs}
                )

                embeddings = []
                for item in response.data:
                    embeddings.append(item.embedding)

                # 更新维度信息
                if embeddings and not self._dimension:
                    self._dimension = len(embeddings[0])

                return embeddings

            except Exception as e:
                last_error = e

            # 指数退避重试
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)

        raise last_error or Exception(
            "OpenAI-compatible API call failed after maximum retries"
        )


# DashScope embedding API base URL for litellm compatibility
DASHSCOPE_EMBEDDING_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LiteLLMEmbeddingProvider(EmbeddingProvider):
    """
    LiteLLM 嵌入向量提供者

    使用 litellm.embedding() 统一调用各种 embedding API。
    """

    DEFAULT_DIMENSION = 1536
    # DashScope has a hard limit of 10 chunks per batch
    DASHSCOPE_BATCH_SIZE = 10
    DEFAULT_BATCH_SIZE = 25

    def __init__(
        self,
        model: str,
        api_key: str,
        api_base: Optional[str] = None,
        dimension: Optional[int] = None,
        batch_size: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        初始化 LiteLLM 嵌入向量提供者

        Args:
            model: litellm 模型名称（如 "openai/text-embedding-v4"）
            api_key: API 密钥
            api_base: API 基础 URL，可选
            dimension: 向量维度
            batch_size: 批量处理大小，DashScope defaults to 10, others to 25
            **kwargs: 额外的配置参数（如 encoding_format）
        """
        if litellm is None:
            raise ImportError(
                "litellm package is required. "
                "Install it with: pip install litellm"
            )

        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self._dimension = dimension or self.DEFAULT_DIMENSION
        
        # Auto-detect batch size based on provider
        if batch_size is not None:
            self.batch_size = batch_size
        elif api_base and "dashscope" in api_base.lower():
            self.batch_size = self.DASHSCOPE_BATCH_SIZE
        else:
            self.batch_size = self.DEFAULT_BATCH_SIZE
        
        self.extra_kwargs = kwargs

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(
        self,
        texts: List[str],
        max_retries: int = 3,
        batch_size: Optional[int] = None,
        **kwargs: Any
    ) -> List[List[float]]:
        """
        调用 litellm embedding API 生成文本向量

        Args:
            texts: 待向量化的文本列表
            max_retries: 最大重试次数
            batch_size: 批量处理大小，如果为 None 则使用实例的 batch_size
            **kwargs: 额外的生成参数

        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Use instance batch_size if not specified
        effective_batch_size = batch_size if batch_size is not None else self.batch_size
        
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), effective_batch_size):
            batch = texts[i:i + effective_batch_size]
            batch_embeddings = self._embed_batch(batch, max_retries, **kwargs)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _embed_batch(
        self,
        texts: List[str],
        max_retries: int,
        **kwargs: Any
    ) -> List[List[float]]:
        last_error = None

        for attempt in range(max_retries):
            try:
                call_kwargs = {
                    "model": self.model,
                    "input": texts,
                    "api_key": self.api_key,
                    **self.extra_kwargs,
                    **kwargs,
                }
                if self.api_base:
                    call_kwargs["api_base"] = self.api_base

                # Prevent litellm from sending encoding_format=None (rejected by some providers like DashScope)
                if "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
                    call_kwargs["encoding_format"] = "float"

                response = litellm.embedding(**call_kwargs)

                embeddings = [item["embedding"] for item in response.data]

                if embeddings and not self._dimension:
                    self._dimension = len(embeddings[0])

                return embeddings

            except Exception as e:
                last_error = e
                logger.warning(
                    f"LiteLLM embedding attempt {attempt + 1}/{max_retries} failed: {e}"
                )

            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)

        raise last_error or Exception(
            "LiteLLM embedding call failed after maximum retries"
        )


class Embedder:
    """
    嵌入向量生成器

    封装嵌入向量提供者，提供统一的向量化接口。
    支持从配置创建、批量向量化等功能。

    使用示例：
        >>> from kb.processors.embedder import Embedder
        >>> embedder = Embedder.from_config()
        >>> embeddings = embedder.embed(["文本1", "文本2"])
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        **kwargs: Any
    ) -> None:
        """
        初始化嵌入向量生成器

        Args:
            provider: 嵌入向量提供者实例
            **kwargs: 额外的配置参数
        """
        self.provider = provider
        self.config = kwargs

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "Embedder":
        """
        从配置创建嵌入向量生成器实例

        Args:
            config: 配置对象，如果为 None 则使用默认配置

        Returns:
            Embedder: 嵌入向量生成器实例

        Raises:
            ValueError: 配置无效或缺少必需字段
        """
        if config is None:
            config = Config()

        embedding_config = config.get("embedding", {})
        provider_name = embedding_config.get("provider", "dashscope")

        # 根据提供者类型创建相应的实例
        if provider_name == "litellm":
            # Direct litellm mode
            if litellm is None:
                raise ImportError(
                    "litellm package is required. "
                    "Install it with: pip install litellm"
                )
            api_key = embedding_config.get("api_key", "")
            model = embedding_config.get("model", "")
            api_base = embedding_config.get("base_url", None)
            extra_kwargs = {}
            encoding_format = embedding_config.get("encoding_format")
            if encoding_format:
                extra_kwargs["encoding_format"] = encoding_format

            if not api_key:
                raise ValueError("API key is required for litellm embedding provider")
            if not model:
                raise ValueError("Model is required for litellm embedding provider")

            provider = LiteLLMEmbeddingProvider(
                model=model,
                api_key=api_key,
                api_base=api_base,
                **extra_kwargs,
            )

        elif provider_name == "dashscope":
            dashscope_config = embedding_config.get("dashscope", {})
            api_key = dashscope_config.get("api_key", "")
            model = dashscope_config.get("model", "text-embedding-v4")

            if not api_key:
                raise ValueError("DashScope API key is required in configuration")

            if litellm is not None:
                # Prefer litellm: map dashscope embedding to openai-compatible mode
                provider = LiteLLMEmbeddingProvider(
                    model=f"openai/{model}",
                    api_key=api_key,
                    api_base=DASHSCOPE_EMBEDDING_API_BASE,
                    encoding_format="float",
                    batch_size=LiteLLMEmbeddingProvider.DASHSCOPE_BATCH_SIZE,
                )
                logger.info(f"Using litellm for dashscope embedding: openai/{model} (batch_size=10)")
            else:
                # Fallback to native dashscope SDK
                provider = DashScopeEmbeddingProvider(
                    api_key=api_key,
                    model=model
                )
                logger.info(f"Using native dashscope SDK for embedding: {model}")

        elif provider_name == "openai_compatible":
            openai_config = embedding_config.get("openai_compatible", {})
            api_key = openai_config.get("api_key", "")
            base_url = openai_config.get("base_url", "")
            model = openai_config.get("model", "")

            if not api_key:
                raise ValueError("OpenAI-compatible API key is required in configuration")
            if not base_url:
                raise ValueError("base_url is required for openai_compatible provider")
            if not model:
                raise ValueError("model is required for openai_compatible provider")

            if litellm is not None:
                # Use litellm with openai-compatible endpoint
                provider = LiteLLMEmbeddingProvider(
                    model=f"openai/{model}",
                    api_key=api_key,
                    api_base=base_url,
                )
                logger.info(f"Using litellm for openai_compatible embedding: openai/{model} at {base_url}")
            else:
                provider = OpenAICompatibleEmbeddingProvider(
                    api_key=api_key,
                    base_url=base_url,
                    model=model
                )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_name}")

        return cls(provider=provider)

    @staticmethod
    def create_dashscope_provider(
        api_key: str,
        model: str = "text-embedding-v4",
        **kwargs: Any
    ) -> DashScopeEmbeddingProvider:
        """
        创建 DashScope 嵌入向量提供者

        Args:
            api_key: DashScope API 密钥
            model: 模型名称
            **kwargs: 额外的配置参数

        Returns:
            DashScopeEmbeddingProvider: DashScope 提供者实例
        """
        return DashScopeEmbeddingProvider(
            api_key=api_key,
            model=model,
            **kwargs
        )

    @staticmethod
    def create_openai_provider(
        api_key: str,
        base_url: str,
        model: str,
        **kwargs: Any
    ) -> OpenAICompatibleEmbeddingProvider:
        """
        创建 OpenAI 兼容嵌入向量提供者

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            **kwargs: 额外的配置参数

        Returns:
            OpenAICompatibleEmbeddingProvider: OpenAI 兼容提供者实例
        """
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            **kwargs
        )

    def embed(
        self,
        texts: List[str],
        **kwargs: Any
    ) -> List[List[float]]:
        """
        将文本列表转换为向量列表

        Args:
            texts: 待向量化的文本列表
            **kwargs: 额外的处理参数
                - max_retries: 最大重试次数，默认为 3
                - batch_size: 批量处理大小，默认为 25

        Returns:
            List[List[float]]: 向量列表

        Raises:
            ValueError: 输入文本列表为空
            Exception: 向量化失败
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        return self.provider.embed(texts, **kwargs)

    @property
    def dimension(self) -> int:
        """
        获取向量维度

        Returns:
            int: 向量维度
        """
        return self.provider.dimension
