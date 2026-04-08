"""
语义搜索模块

基于向量相似度的语义检索功能，支持标签过滤和分数阈值过滤。
"""

import logging
from typing import Any, Dict, List, Optional

from kb.config import Config
from kb.processors.embedder import Embedder
from kb.query.models import SearchResult
from kb.storage.chroma_storage import ChromaStorage

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    语义搜索类

    提供基于向量相似度的语义检索功能。将查询文本向量化后，
    在 Chroma 向量数据库中进行相似度检索，返回最相关的文档。

    使用示例：
        >>> from kb.config import Config
        >>> from kb.query.semantic_search import SemanticSearch
        >>> config = Config()
        >>> search = SemanticSearch(config)
        >>> results = search.search("如何安装 Python", tags=["python"], top_k=5)
        >>> for result in results:
        ...     print(f"ID: {result.id}, Score: {result.score}")
        ...     print(f"Content: {result.content[:100]}...")
    """

    def __init__(self, config: Config) -> None:
        """
        初始化语义搜索器

        从配置中读取嵌入模型和存储配置，创建 Embedder 和 ChromaStorage 实例。

        Args:
            config: 配置对象，包含 embedding 和 storage 配置

        Raises:
            ValueError: 配置无效或缺少必需字段
            ImportError: 依赖包未安装
        """
        self.config = config

        # 获取查询配置
        query_config = config.get("query", {})
        semantic_config = query_config.get("semantic_search", {})

        self.top_k = semantic_config.get("top_k", 5)
        self.score_threshold = semantic_config.get("score_threshold", 0.7)

        # 创建嵌入向量生成器
        try:
            self.embedder = Embedder.from_config(config)
        except Exception as e:
            logger.warning(f"Embedder initialization failed: {e}. "
                          "Semantic search will fall back to keyword search.")
            self.embedder = None

        # 创建向量存储
        try:
            storage_config = config.get("storage", {})
            persist_directory = storage_config.get(
                "persist_directory", "~/.knowledge-base/db/chroma"
            )
            self.storage = ChromaStorage(path=persist_directory)
        except Exception as e:
            logger.error(f"Failed to create storage: {e}")
            raise ValueError(f"Failed to initialize storage: {e}")

        logger.info(
            f"SemanticSearch initialized with top_k={self.top_k}, "
            f"score_threshold={self.score_threshold}"
        )

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        page_number: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        执行语义搜索

        将查询文本向量化，在向量数据库中进行相似度检索，
        可选地按标签过滤，并返回按相似度排序的结果列表。

        Args:
            query: 搜索查询文本
            tags: 标签过滤列表，如果提供则只返回包含这些标签的文档
            top_k: 返回结果数量，如果不提供则使用配置中的默认值
            score_threshold: 分数阈值，只返回分数高于此值的结果，
                           如果不提供则使用配置中的默认值
            page_number: 页码过滤，如果提供则只返回指定页码的文档块

        Returns:
            List[SearchResult]: 搜索结果列表，按相似度降序排列

        Raises:
            ValueError: 查询文本为空
            Exception: 搜索过程中发生错误
        """
        if not query or not query.strip():
            raise ValueError("Query text cannot be empty")

        # 使用配置默认值
        if top_k is None:
            top_k = self.top_k
        if score_threshold is None:
            score_threshold = self.score_threshold

        # Try semantic search first (only if embedder is available)
        if self.embedder is not None:
            try:
                # 1. 将查询文本向量化
                logger.debug(f"Embedding query: {query[:50]}...")
                query_embedding = self._embed_query(query)

                # 2. 构建过滤条件
                where_filter = self._build_filter(tags, page_number=page_number)

                # 3. 执行向量检索
                logger.debug(
                    f"Querying storage with top_k={top_k}, "
                    f"filter={where_filter}"
                )
                raw_results = self.storage.query(
                    embedding=query_embedding,
                    top_k=top_k,
                    where_filter=where_filter,
                )

                # 4. 转换并过滤结果
                results = self._convert_results(raw_results, score_threshold)

                logger.info(
                    f"Search completed: {len(results)} results returned "
                    f"(threshold: {score_threshold})"
                )
                return results

            except Exception as e:
                logger.warning(f"Semantic search failed: {e}. Falling back to keyword search.")
        else:
            logger.info("Embedder not available, using keyword search fallback.")

        # Fallback to keyword search
        try:
            from kb.query.keyword_search import KeywordSearch
            kw_search = KeywordSearch(data_dir=str(self.config.data_dir))
            return kw_search.search(keywords=query, limit=top_k)
        except Exception as kw_err:
            logger.error(f"Keyword search fallback also failed: {kw_err}")
            return []

    def _embed_query(self, query: str) -> List[float]:
        """
        将查询文本转换为向量

        Args:
            query: 查询文本

        Returns:
            List[float]: 查询向量

        Raises:
            Exception: 向量化失败
        """
        try:
            embeddings = self.embedder.embed([query])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Failed to generate embedding")
            return embeddings[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

    def _build_filter(
        self,
        tags: Optional[List[str]] = None,
        page_number: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        构建 Chroma 过滤条件

        Args:
            tags: 标签列表
            page_number: 页码过滤

        Returns:
            Optional[Dict[str, Any]]: 过滤条件字典，如果不需要过滤则返回 None
        """
        conditions = []

        if tags:
            conditions.append({"tags": {"$in": tags}})

        if page_number is not None:
            conditions.append({"page_number": {"$eq": page_number}})

        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _convert_results(
        self, raw_results: Dict[str, Any], score_threshold: float
    ) -> List[SearchResult]:
        """
        将原始检索结果转换为 SearchResult 列表

        Chroma 返回的距离是余弦距离（0-2），需要转换为相似度分数（0-1）。
        余弦相似度 = 1 - (余弦距离 / 2)

        Args:
            raw_results: Chroma 返回的原始结果
            score_threshold: 分数阈值

        Returns:
            List[SearchResult]: 过滤后的搜索结果列表
        """
        results = []

        ids = raw_results.get("ids", [])
        distances = raw_results.get("distances", [])
        metadatas = raw_results.get("metadatas", [])
        documents = raw_results.get("documents", [])

        for i in range(len(ids)):
            # 将距离转换为相似度分数
            distance = distances[i] if i < len(distances) else 1.0
            # 余弦距离范围是 0-2，转换为 0-1 的相似度
            score = 1.0 - (distance / 2.0)

            # 确保分数在 0-1 范围内
            score = max(0.0, min(1.0, score))

            # 过滤低于阈值的结果
            if score < score_threshold:
                continue

            metadata = metadatas[i] if i < len(metadatas) else {}
            content = documents[i] if i < len(documents) else ""

            result = SearchResult(
                id=ids[i],
                content=content,
                metadata=metadata,
                score=score,
            )
            results.append(result)

        return results

    def search_by_page(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        top_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        页级聚合搜索

        执行语义搜索后，按 page_number 聚合结果，返回最相关的页面。
        每个页面包含该页中所有匹配的 chunk 和最高相似度分数。
        仅对含有 page_number metadata 的结果进行聚合。

        Args:
            query: 搜索查询文本
            tags: 标签过滤列表
            top_k: 检索 chunk 数量（聚合前）
            score_threshold: 分数阈值
            top_pages: 返回的最相关页面数量，默认为 3

        Returns:
            List[Dict[str, Any]]: 按页聚合的结果列表，每项包含：
                - page_number: 页码
                - max_score: 该页最高相似度分数
                - chunks: 该页匹配的 SearchResult 列表
                - source: 文档来源（取自第一个 chunk 的 metadata）
        """
        # Use higher top_k for aggregation to get enough chunks across pages
        search_top_k = (top_k or self.top_k) * 3
        results = self.search(
            query=query,
            tags=tags,
            top_k=search_top_k,
            score_threshold=score_threshold,
        )

        # Group by (source, page_number)
        page_groups: Dict[tuple, List[SearchResult]] = {}
        for result in results:
            page_num = result.metadata.get("page_number")
            if page_num is None:
                continue
            source = result.metadata.get("source", "")
            key = (source, page_num)
            if key not in page_groups:
                page_groups[key] = []
            page_groups[key].append(result)

        # Build page-level results
        page_results = []
        for (source, page_num), chunks in page_groups.items():
            max_score = max(c.score for c in chunks)
            page_results.append({
                "page_number": page_num,
                "max_score": max_score,
                "chunks": chunks,
                "source": source,
            })

        # Sort by max_score descending, return top pages
        page_results.sort(key=lambda x: x["max_score"], reverse=True)
        return page_results[:top_pages]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            Dict[str, Any]: 包含文档数量等统计信息
        """
        try:
            count = self.storage.count()
            return {
                "document_count": count,
                "top_k": self.top_k,
                "score_threshold": self.score_threshold,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "document_count": 0,
                "top_k": self.top_k,
                "score_threshold": self.score_threshold,
                "error": str(e),
            }
