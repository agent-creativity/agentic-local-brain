"""
Query module

Handles knowledge retrieval and querying, including:
- Semantic search (vector similarity-based)
- Keyword search (text matching-based)
- RAG query (Retrieval Augmented Generation)
- v0.7: Multi-stage retrieval pipeline
"""

from kb.query.models import (
    RAGResult,
    SearchResult,
    # v0.7 Enhanced Retrieval Models
    EntityContext,
    RankedChunk,
    RetrievalContext,
    ConversationTurn,
    ConversationSession,
    EnhancedRAGResult,
)
from kb.query.keyword_search import KeywordSearch
from kb.query.rag import RAGQuery
from kb.query.semantic_search import SemanticSearch
from kb.query.retrieval_pipeline import RetrievalPipeline
from kb.query.reranker import BaseReranker, NoOpReranker, LLMReranker
from kb.query.query_expander import BaseQueryExpander, NoOpQueryExpander, LLMQueryExpander, ExpandedQuery
from kb.query.context_builder import BaseContextBuilder, SimpleContextBuilder, HierarchicalContextBuilder
from kb.query.conversation import ConversationManager
from kb.query.prompt_templates import PromptTemplateManager

__all__ = [
    # Core models
    "SearchResult",
    "RAGResult",
    # v0.7 Enhanced Retrieval Models
    "EntityContext",
    "RankedChunk",
    "RetrievalContext",
    "ConversationTurn",
    "ConversationSession",
    "EnhancedRAGResult",
    # Search classes
    "SemanticSearch",
    "KeywordSearch",
    "RAGQuery",
    # v0.7 Pipeline components
    "RetrievalPipeline",
    "BaseReranker",
    "NoOpReranker",
    "LLMReranker",
    "BaseQueryExpander",
    "NoOpQueryExpander",
    "LLMQueryExpander",
    "ExpandedQuery",
    "BaseContextBuilder",
    "SimpleContextBuilder",
    "HierarchicalContextBuilder",
    # Conversation management
    "ConversationManager",
    # Prompt templates
    "PromptTemplateManager",
]
