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
