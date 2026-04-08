"""
处理模块

负责内容的处理和转换，包括：
- 文本分块
- 嵌入向量生成
- 内容清洗
- 元数据提取
- 标签提取
"""

from kb.processors.base import BaseProcessor, ProcessResult
from kb.processors.tag_extractor import (
    LLMProvider,
    LiteLLMProvider,
    TagExtractor,
)
from kb.processors.embedder import (
    DashScopeEmbeddingProvider,
    Embedder,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from kb.processors.chunker import Chunker
from kb.processors.builtin_extractor import BuiltinExtractor
from kb.processors.entity_extractor import EntityExtractor
from kb.processors.doc_embedding import DocEmbeddingService
from kb.processors.topic_clusterer import TopicClusterer
from kb.processors.recommendation import RecommendationEngine

__all__ = [
    "BaseProcessor",
    "ProcessResult",
    "LLMProvider",
    "LiteLLMProvider",
    "TagExtractor",
    "EmbeddingProvider",
    "DashScopeEmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "Embedder",
    "Chunker",
    "BuiltinExtractor",
    "EntityExtractor",
    "DocEmbeddingService",
    "TopicClusterer",
    "RecommendationEngine",
]
