"""
Embedding vector generator module

Text vectorization based on multiple providers (DashScope, OpenAI-compatible API).
Supports batch vectorization and error retry mechanism.
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
    """Abstract base class for embedding vector providers."""

    @abstractmethod
    def embed(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        Convert a list of texts to a list of vectors.

        Args:
            texts: List of texts to vectorize.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: List of vectors, each vector is a list of floats.

        Raises:
            Exception: API call failed or max retries reached.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get the vector dimension.

        Returns:
            int: Vector dimension.
        """
        pass


class DashScopeEmbeddingProvider(EmbeddingProvider):
    """
    DashScope (Alibaba Cloud Bailian) embedding vector provider.

    Uses the text-embedding-v4 model for text vectorization.
    """

    # Default dimension (for text-embedding-v4)
    DEFAULT_DIMENSION = 1536

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v4",
        dimension: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize DashScope embedding vector provider.

        Args:
            api_key: DashScope API key.
            model: Model name, defaults to text-embedding-v4.
            dimension: Vector dimension; uses model default if not specified.
            **kwargs: Additional configuration parameters.
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
        Get the vector dimension.

        Returns:
            int: Vector dimension.
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
        Call DashScope API to generate text vectors.

        Args:
            texts: List of texts to vectorize.
            max_retries: Maximum number of retries, defaults to 3.
            batch_size: Batch processing size, defaults to 25.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: List of vectors.

        Raises:
            Exception: API call failed or max retries reached.
            ValueError: Input text list is empty.
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        all_embeddings: List[List[float]] = []
        last_error: Optional[Exception] = None

        # Process in batches
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
        Process a single batch of vectorization.

        Args:
            texts: Batch text list.
            max_retries: Maximum number of retries.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: Batch vector list.

        Raises:
            Exception: API call failed.
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

            # Exponential backoff retry
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)

        raise last_error or Exception(
            "DashScope API call failed after maximum retries"
        )


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI-compatible API embedding vector provider.

    Supports any service compatible with the OpenAI API format (e.g., vLLM, Ollama).
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
        Initialize OpenAI-compatible embedding vector provider.

        Args:
            api_key: API key.
            base_url: API base URL.
            model: Model name.
            dimension: Vector dimension; obtained via API if not specified.
            **kwargs: Additional configuration parameters.
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
        Get the vector dimension.

        Returns:
            int: Vector dimension.
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
        Call OpenAI-compatible API to generate text vectors.

        Args:
            texts: List of texts to vectorize.
            max_retries: Maximum number of retries, defaults to 3.
            batch_size: Batch processing size, defaults to 25.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: List of vectors.

        Raises:
            Exception: API call failed or max retries reached.
            ValueError: Input text list is empty.
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        all_embeddings: List[List[float]] = []
        last_error: Optional[Exception] = None

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_embeddings = self._embed_batch(
                    batch, max_retries, **kwargs
                )
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                last_error = e
                # If this is the last batch, raise the exception
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
        Process a single batch of vectorization.

        Args:
            texts: Batch text list.
            max_retries: Maximum number of retries.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: Batch vector list.

        Raises:
            Exception: API call failed.
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

                # Update dimension info
                if embeddings and not self._dimension:
                    self._dimension = len(embeddings[0])

                return embeddings

            except Exception as e:
                last_error = e

            # Exponential backoff retry
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
    LiteLLM embedding vector provider.

    Uses litellm.embedding() to uniformly call various embedding APIs.
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
        Initialize LiteLLM embedding vector provider.

        Args:
            model: LiteLLM model name (e.g., "openai/text-embedding-v4").
            api_key: API key.
            api_base: API base URL, optional.
            dimension: Vector dimension.
            batch_size: Batch processing size, DashScope defaults to 10, others to 25.
            **kwargs: Additional configuration parameters (e.g., encoding_format).
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
        Call litellm embedding API to generate text vectors.

        Args:
            texts: List of texts to vectorize.
            max_retries: Maximum number of retries.
            batch_size: Batch processing size; uses instance batch_size if None.
            **kwargs: Additional generation parameters.

        Returns:
            List[List[float]]: List of vectors.
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

                # Handle encoding_format based on provider
                # Ollama doesn't support encoding_format parameter
                if self.model.startswith("ollama/"):
                    # Remove encoding_format for ollama
                    call_kwargs.pop("encoding_format", None)
                elif "encoding_format" not in call_kwargs or call_kwargs.get("encoding_format") is None:
                    # Prevent litellm from sending encoding_format=None (rejected by some providers like DashScope)
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
    Embedding vector generator.

    Wraps embedding vector providers to offer a unified vectorization interface.
    Supports creation from configuration, batch vectorization, etc.

    Usage examples:
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
        Initialize embedding vector generator.

        Args:
            provider: Embedding vector provider instance.
            **kwargs: Additional configuration parameters.
        """
        self.provider = provider
        self.config = kwargs

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "Embedder":
        """
        Create an embedding vector generator instance from configuration.

        Args:
            config: Configuration object; uses default configuration if None.

        Returns:
            Embedder: Embedding vector generator instance.

        Raises:
            ValueError: Invalid configuration or missing required fields.
        """
        if config is None:
            config = Config()

        embedding_config = config.get("embedding", {})
        provider_name = embedding_config.get("provider", "dashscope")

        # Create the appropriate instance based on provider type
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

            # Ollama doesn't support encoding_format parameter
            # Only add encoding_format for providers that support it
            if encoding_format and not model.startswith("ollama/"):
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
        Create a DashScope embedding vector provider.

        Args:
            api_key: DashScope API key.
            model: Model name.
            **kwargs: Additional configuration parameters.

        Returns:
            DashScopeEmbeddingProvider: DashScope provider instance.
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
        Create an OpenAI-compatible embedding vector provider.

        Args:
            api_key: API key.
            base_url: API base URL.
            model: Model name.
            **kwargs: Additional configuration parameters.

        Returns:
            OpenAICompatibleEmbeddingProvider: OpenAI-compatible provider instance.
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
        Convert a list of texts to a list of vectors.

        Args:
            texts: List of texts to vectorize.
            **kwargs: Additional processing parameters.
                - max_retries: Maximum number of retries, defaults to 3.
                - batch_size: Batch processing size, defaults to 25.

        Returns:
            List[List[float]]: List of vectors.

        Raises:
            ValueError: Input text list is empty.
            Exception: Vectorization failed.
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        return self.provider.embed(texts, **kwargs)

    @property
    def dimension(self) -> int:
        """
        Get the vector dimension.

        Returns:
            int: Vector dimension.
        """
        return self.provider.dimension
