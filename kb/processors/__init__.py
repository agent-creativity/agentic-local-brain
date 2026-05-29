"""
Processors module

Handles content processing and transformation, including:
- Text chunking
- Embedding vector generation
- Content cleaning
- Metadata extraction
- Tag extraction
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
