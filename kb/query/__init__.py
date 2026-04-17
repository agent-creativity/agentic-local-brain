"""
查询模块

负责知识的检索和查询，包括：
- 语义搜索（基于向量相似度）
- 关键词搜索（基于文本匹配）
- RAG 查询（检索增强生成）
- v0.7: 多阶段检索流水线
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
