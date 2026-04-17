"""
查询相关的数据模型

定义查询模块中使用的所有数据类，包括搜索结果和 RAG 查询结果。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """
    搜索结果数据类

    表示单次检索操作返回的单个结果项，包含文档内容、元数据和相似度分数。

    Attributes:
        id: 文档的唯一标识符
        content: 文档的文本内容
        metadata: 文档的元数据信息（如来源、标签、创建时间等）
        score: 相似度分数（0-1 之间，越高表示越相似）
    """

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def __post_init__(self) -> None:
        """验证分数范围"""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """
        从字典创建 SearchResult 实例

        Args:
            data: 包含搜索结果字段的字典

        Returns:
            SearchResult: 搜索结果实例

        Raises:
            ValueError: 缺少必需字段
        """
        required_fields = ["id", "content"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        return cls(
            id=data["id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            score=data.get("score", 0.0),
        )


@dataclass
class RAGResult:
    """
    RAG 查询结果数据类

    表示基于检索增强生成（RAG）的查询结果，包含 LLM 生成的回答和引用来源。

    Attributes:
        answer: LLM 生成的回答文本
        sources: 引用来源列表（SearchResult 对象）
        context: 用于生成回答的完整上下文文本
        question: 原始问题文本
    """

    answer: str
    sources: List[SearchResult] = field(default_factory=list)
    context: str = ""
    question: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return {
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
            "context": self.context,
            "question": self.question,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGResult":
        """
        从字典创建 RAGResult 实例

        Args:
            data: 包含 RAG 结果字段的字典

        Returns:
            RAGResult: RAG 查询结果实例

        Raises:
            ValueError: 缺少必需字段
        """
        if "answer" not in data:
            raise ValueError("Missing required field: answer")

        sources_data = data.get("sources", [])
        sources = [SearchResult.from_dict(s) for s in sources_data]

        return cls(
            answer=data["answer"],
            sources=sources,
            context=data.get("context", ""),
            question=data.get("question", ""),
        )

    def get_source_ids(self) -> List[str]:
        """
        获取所有引用来源的 ID 列表

        Returns:
            List[str]: 来源 ID 列表
        """
        return [source.id for source in self.sources]

    def get_source_contents(self) -> List[str]:
        """
        获取所有引用来源的内容列表

        Returns:
            List[str]: 来源内容列表
        """
        return [source.content for source in self.sources]


# =============================================================================
# v0.7 RAG Enhanced Retrieval Data Models
# =============================================================================


@dataclass
class EntityContext:
    """
    Entity information for context enrichment

    Represents an extracted entity with its context for RAG enrichment.

    Attributes:
        name: The entity name/identifier
        entity_type: Type of entity (person, organization, concept, etc.)
        mentions: Context snippets where the entity appears
        relations: Related entities with their relation types
    """

    name: str
    entity_type: str
    mentions: List[str] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class RankedChunk:
    """
    A chunk with multi-stage scoring

    Represents a document chunk that has been through multiple
    retrieval pipeline stages with different scoring mechanisms.

    Attributes:
        content: The chunk text content
        source: Source document identifier
        retrieval_score: Score from initial retrieval (0-1)
        rerank_score: Score from reranker (0-1)
        final_score: Combined weighted score
        metadata: Additional chunk metadata
    """

    content: str
    source: str
    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            'content': self.content,
            'source': self.source,
            'retrieval_score': self.retrieval_score,
            'rerank_score': self.rerank_score,
            'final_score': self.final_score,
            'metadata': self.metadata,
        }


@dataclass
class RetrievalContext:
    """
    Enriched context for LLM generation

    Assembled context ready for LLM consumption, containing
    ranked chunks, entity context, and token budget info.

    Attributes:
        chunks: List of ranked chunks
        entities: Extracted entity contexts
        topic_context: Related topic information
        token_count: Estimated token count
        budget: Token budget limit
    """

    chunks: List[RankedChunk] = field(default_factory=list)
    entities: List[EntityContext] = field(default_factory=list)
    topic_context: Optional[str] = None
    token_count: int = 0
    budget: int = 4000

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            'chunks': [c.to_dict() for c in self.chunks],
            'entities': [{'name': e.name, 'type': e.entity_type, 'mentions': e.mentions, 'relations': e.relations} for e in self.entities],
            'topic_context': self.topic_context,
            'token_count': self.token_count,
            'budget': self.budget,
        }


@dataclass
class ConversationTurn:
    """
    Single turn in multi-turn conversation

    Represents one exchange in a conversation session.

    Attributes:
        role: Either 'user' or 'assistant'
        content: The message content
        sources: Optional list of source dicts (with id, metadata, score, content)
                 or legacy list of source IDs (strings) for backward compatibility
        timestamp: ISO format timestamp
    """

    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            'role': self.role,
            'content': self.content,
            'sources': self.sources,
            'timestamp': self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """
        Create ConversationTurn from dictionary

        Args:
            data: Dictionary containing turn data

        Returns:
            ConversationTurn: New instance
        """
        return cls(
            role=data['role'],
            content=data['content'],
            sources=data.get('sources'),
            timestamp=data.get('timestamp'),
        )


@dataclass
class ConversationSession:
    """
    Multi-turn conversation state

    Maintains the complete state of a conversation session.

    Attributes:
        session_id: Unique session identifier
        turns: List of conversation turns
        created_at: ISO format creation timestamp
        updated_at: ISO format last update timestamp
    """

    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: str = ""
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            'session_id': self.session_id,
            'turns': [t.to_dict() for t in self.turns],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class EnhancedRAGResult:
    """
    Extended RAG result with v0.7 enhanced retrieval fields

    Represents the complete result from the enhanced retrieval pipeline,
    including reranking, entity context, and multi-turn support.

    Attributes:
        answer: LLM generated answer text
        question: Original question text
        sources: List of search result sources
        context: Full context text used for generation
        confidence: Answer confidence score (0-1)
        retrieval_strategy: Description of pipeline stages that fired
        reranked_sources: Optional list of reranked chunks
        entity_context: Optional entity context information
        topic_context: Optional topic context string
        session_id: Optional conversation session ID
        turn_number: Optional turn number in conversation
    """

    answer: str
    question: str
    sources: List[SearchResult] = field(default_factory=list)
    context: str = ""
    confidence: float = 0.0
    retrieval_strategy: str = ""
    reranked_sources: Optional[List[RankedChunk]] = None
    entity_context: Optional[List[Dict]] = None
    topic_context: Optional[str] = None
    session_id: Optional[str] = None
    turn_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        result = {
            'answer': self.answer,
            'question': self.question,
            'sources': [s.to_dict() for s in self.sources],
            'context': self.context,
            'confidence': self.confidence,
            'retrieval_strategy': self.retrieval_strategy,
            'session_id': self.session_id,
            'turn_number': self.turn_number,
        }
        if self.reranked_sources:
            result['reranked_sources'] = [r.to_dict() for r in self.reranked_sources]
        if self.entity_context:
            result['entity_context'] = self.entity_context
            result['entities'] = self.entity_context
        if self.topic_context:
            result['topic_context'] = self.topic_context
        return result
