"""
Chroma 向量存储模块

基于 ChromaDB 的向量存储实现，支持文档的增删改查操作。
提供向量相似度检索和元数据过滤功能。
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None


class ChromaStorage:
    """
    Chroma 向量存储类

    封装 ChromaDB 客户端，提供文档的持久化存储和检索功能。
    支持向量相似度搜索、元数据过滤和文档管理。

    使用示例：
        >>> from kb.storage.chroma_storage import ChromaStorage
        >>> storage = ChromaStorage(path="~/.knowledge-base/db/chroma")
        >>> storage.add_documents(
        ...     ids=["doc1", "doc2"],
        ...     embeddings=[[0.1, 0.2], [0.3, 0.4]],
        ...     metadatas=[{"source": "file1"}, {"source": "file2"}],
        ...     documents=["文本1", "文本2"]
        ... )
        >>> results = storage.query(
        ...     embedding=[0.15, 0.25],
        ...     top_k=2
        ... )
    """

    def __init__(
        self,
        path: str,
        collection_name: str = "knowledge",
        **kwargs: Any
    ) -> None:
        """
        初始化 Chroma 存储客户端

        Args:
            path: Chroma 数据库持久化路径
            collection_name: 集合名称，默认为 "knowledge"
            **kwargs: 额外的配置参数

        Raises:
            ImportError: chromadb 包未安装
            ValueError: 路径无效
        """
        if chromadb is None or Settings is None:
            raise ImportError(
                "chromadb package is required. Install it with: pip install chromadb"
            )

        # 展开路径
        expanded_path = os.path.expanduser(path)
        self.path = Path(expanded_path)

        # 确保目录存在
        self.path.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.extra_kwargs = kwargs

        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=str(self.path),
            settings=Settings(
                anonymized_telemetry=False,
                **kwargs
            )
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        **kwargs: Any
    ) -> bool:
        """
        添加文档到 Chroma 集合

        Args:
            ids: 文档 ID 列表
            embeddings: 文档向量列表
            metadatas: 文档元数据列表，可选
            documents: 文档原始文本列表，可选
            **kwargs: 额外的添加参数

        Returns:
            bool: 是否添加成功

        Raises:
            ValueError: 参数无效或长度不匹配
            Exception: 添加失败
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        if not embeddings:
            raise ValueError("Embeddings list cannot be empty")

        if len(ids) != len(embeddings):
            raise ValueError(
                f"IDs and embeddings must have the same length. "
                f"Got {len(ids)} IDs and {len(embeddings)} embeddings"
            )

        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                f"Metadatas length must match IDs length. "
                f"Got {len(metadatas)} metadatas and {len(ids)} IDs"
            )

        if documents is not None and len(documents) != len(ids):
            raise ValueError(
                f"Documents length must match IDs length. "
                f"Got {len(documents)} documents and {len(ids)} IDs"
            )

        try:
            # 确保 metadatas 不为 None
            final_metadatas = metadatas if metadatas is not None else [{} for _ in ids]

            # 确保 documents 不为 None
            final_documents = documents if documents is not None else ["" for _ in ids]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=final_metadatas,
                documents=final_documents,
                **kwargs
            )
            return True

        except Exception as e:
            raise Exception(f"Failed to add documents: {str(e)}")

    def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        向量相似度检索

        Args:
            embedding: 查询向量
            top_k: 返回最相似的文档数量，默认为 5
            where_filter: 元数据过滤条件，可选
                示例：{"source": "file1", "category": "tech"}
            **kwargs: 额外的查询参数

        Returns:
            Dict[str, Any]: 查询结果，包含以下字段：
                - ids: 匹配的文档 ID 列表
                - distances: 距离列表
                - metadatas: 元数据列表
                - documents: 文档文本列表

        Raises:
            ValueError: 查询向量为空
            Exception: 查询失败
        """
        if not embedding:
            raise ValueError("Query embedding cannot be empty")

        try:
            query_params: Dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": top_k,
            }

            if where_filter is not None:
                query_params["where"] = where_filter

            query_params.update(kwargs)

            results = self.collection.query(**query_params)

            # 格式化返回结果
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to query documents: {str(e)}")

    def delete(self, ids: List[str], **kwargs: Any) -> bool:
        """
        删除文档

        Args:
            ids: 要删除的文档 ID 列表
            **kwargs: 额外的删除参数

        Returns:
            bool: 是否删除成功

        Raises:
            ValueError: ID 列表为空
            Exception: 删除失败
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        try:
            self.collection.delete(ids=ids, **kwargs)
            return True

        except Exception as e:
            raise Exception(f"Failed to delete documents: {str(e)}")

    def count(self) -> int:
        """
        获取集合中文档数量

        Returns:
            int: 文档数量

        Raises:
            Exception: 查询失败
        """
        try:
            return self.collection.count()
        except Exception as e:
            raise Exception(f"Failed to count documents: {str(e)}")

    def get(
        self,
        ids: Optional[List[str]] = None,
        where_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        获取文档（不进行向量检索）

        Args:
            ids: 文档 ID 列表，可选
            where_filter: 元数据过滤条件，可选
            limit: 返回结果数量限制，可选
            **kwargs: 额外的查询参数

        Returns:
            Dict[str, Any]: 查询结果，包含以下字段：
                - ids: 文档 ID 列表
                - embeddings: 向量列表
                - metadatas: 元数据列表
                - documents: 文档文本列表

        Raises:
            Exception: 查询失败
        """
        try:
            get_params: Dict[str, Any] = {}

            if ids is not None:
                get_params["ids"] = ids

            if where_filter is not None:
                get_params["where"] = where_filter

            if limit is not None:
                get_params["limit"] = limit

            get_params.update(kwargs)

            results = self.collection.get(**get_params)

            return {
                "ids": results["ids"] if results["ids"] else [],
                "embeddings": results["embeddings"] if results["embeddings"] else [],
                "metadatas": results["metadatas"] if results["metadatas"] else [],
                "documents": results["documents"] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to get documents: {str(e)}")

    def update(
        self,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        **kwargs: Any
    ) -> bool:
        """
        更新文档

        Args:
            ids: 文档 ID 列表
            embeddings: 新的向量列表，可选
            metadatas: 新的元数据列表，可选
            documents: 新的文档文本列表，可选
            **kwargs: 额外的更新参数

        Returns:
            bool: 是否更新成功

        Raises:
            ValueError: 参数无效或长度不匹配
            Exception: 更新失败
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        try:
            update_params: Dict[str, Any] = {
                "ids": ids,
            }

            if embeddings is not None:
                update_params["embeddings"] = embeddings

            if metadatas is not None:
                update_params["metadatas"] = metadatas

            if documents is not None:
                update_params["documents"] = documents

            update_params.update(kwargs)

            self.collection.update(**update_params)
            return True

        except Exception as e:
            raise Exception(f"Failed to update documents: {str(e)}")

    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """
        预览集合中的文档

        Args:
            limit: 预览数量，默认为 10

        Returns:
            Dict[str, Any]: 预览结果

        Raises:
            Exception: 查询失败
        """
        try:
            results = self.collection.peek(limit=limit)

            return {
                "ids": results["ids"] if results["ids"] else [],
                "embeddings": results["embeddings"] if results["embeddings"] else [],
                "metadatas": results["metadatas"] if results["metadatas"] else [],
                "documents": results["documents"] if results["documents"] else [],
            }

        except Exception as e:
            raise Exception(f"Failed to peek documents: {str(e)}")

    def reset(self) -> bool:
        """
        重置集合（删除所有文档）

        Returns:
            bool: 是否重置成功

        Raises:
            Exception: 重置失败
        """
        try:
            # 删除并重新创建集合
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True

        except Exception as e:
            raise Exception(f"Failed to reset collection: {str(e)}")
