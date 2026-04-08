"""
文档级 embedding 生成模块

为每篇文档生成一个基于 title + 摘要的文档级 embedding，
用于跨文档关系发现和主题聚类。

设计决策：使用 title + 前 500 字内容（而非 chunk embedding 均值），
语义更集中，且只需一次 embedding 调用。
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kb.config import Config
from kb.processors.embedder import Embedder

logger = logging.getLogger(__name__)


class DocEmbeddingService:
    """
    文档级 embedding 生成服务。

    为每篇文档生成基于 title + 摘要的 embedding，存储在 document_embeddings 表。
    支持增量计算（跳过已有 embedding 的文档）和批量重算。
    """

    def __init__(
        self,
        embedder: Embedder,
        db_path: Optional[str] = None,
        max_content_length: int = 500,
    ) -> None:
        self.embedder = embedder
        self.db_path = db_path
        self.max_content_length = max_content_length

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "DocEmbeddingService":
        if config is None:
            config = Config()

        embedder = Embedder.from_config(config)

        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")

        return cls(embedder=embedder, db_path=db_path)

    def generate_for_document(
        self,
        knowledge_id: str,
        title: str,
        content: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[List[float]]:
        """
        为单篇文档生成并存储 embedding。

        Args:
            knowledge_id: 文档 ID
            title: 文档标题
            content: 文档内容
            conn: SQLite 连接（可选，用于测试）

        Returns:
            生成的 embedding 向量，失败返回 None
        """
        text = self._build_embedding_text(title, content)
        if not text.strip():
            return None

        try:
            embeddings = self.embedder.embed([text])
            if not embeddings:
                return None

            embedding = embeddings[0]
            self._save_embedding(knowledge_id, embedding, conn)
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding for {knowledge_id}: {e}")
            return None

    def generate_incremental(
        self,
        conn: Optional[sqlite3.Connection] = None,
        batch_size: int = 10,
    ) -> Dict[str, int]:
        """
        增量生成：为所有缺少 document embedding 的文档生成 embedding。

        Returns:
            {"processed": int, "skipped": int, "failed": int}
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            # Find documents without embeddings
            cursor = conn.cursor()
            cursor.execute(
                """SELECT k.id, k.title, k.summary
                   FROM knowledge k
                   LEFT JOIN document_embeddings de ON k.id = de.knowledge_id
                   WHERE de.knowledge_id IS NULL"""
            )
            docs = cursor.fetchall()

            processed = 0
            failed = 0

            # Process in batches
            for i in range(0, len(docs), batch_size):
                batch = docs[i : i + batch_size]
                texts = []
                ids = []

                for doc in batch:
                    doc_id = doc[0]
                    title = doc[1] or ""
                    summary = doc[2] or ""
                    # Use summary as content stand-in; if no summary, read from file
                    text = self._build_embedding_text(title, summary)
                    if text.strip():
                        texts.append(text)
                        ids.append(doc_id)

                if not texts:
                    continue

                try:
                    embeddings = self.embedder.embed(texts)
                    for doc_id, embedding in zip(ids, embeddings):
                        self._save_embedding(doc_id, embedding, conn)
                        processed += 1
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(texts)

            return {
                "processed": processed,
                "skipped": len(docs) - processed - failed,
                "failed": failed,
            }
        finally:
            if should_close:
                conn.close()

    def generate_all(
        self,
        conn: Optional[sqlite3.Connection] = None,
        batch_size: int = 10,
    ) -> Dict[str, int]:
        """
        全量重算：为所有文档重新生成 embedding。

        Returns:
            {"processed": int, "failed": int}
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            # Clear existing embeddings
            cursor.execute("DELETE FROM document_embeddings")
            conn.commit()

            cursor.execute("SELECT id, title, summary FROM knowledge")
            docs = cursor.fetchall()

            processed = 0
            failed = 0

            for i in range(0, len(docs), batch_size):
                batch = docs[i : i + batch_size]
                texts = []
                ids = []

                for doc in batch:
                    doc_id = doc[0]
                    title = doc[1] or ""
                    summary = doc[2] or ""
                    text = self._build_embedding_text(title, summary)
                    if text.strip():
                        texts.append(text)
                        ids.append(doc_id)

                if not texts:
                    continue

                try:
                    embeddings = self.embedder.embed(texts)
                    for doc_id, embedding in zip(ids, embeddings):
                        self._save_embedding(doc_id, embedding, conn)
                        processed += 1
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    failed += len(texts)

            return {"processed": processed, "failed": failed}
        finally:
            if should_close:
                conn.close()

    def get_embedding(
        self, knowledge_id: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[List[float]]:
        """Get stored document embedding."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT embedding FROM document_embeddings WHERE knowledge_id = ?",
                (knowledge_id,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None
        finally:
            if should_close:
                conn.close()

    def get_all_embeddings(
        self, conn: Optional[sqlite3.Connection] = None
    ) -> List[Tuple[str, List[float]]]:
        """Get all document embeddings as (knowledge_id, embedding) pairs."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT knowledge_id, embedding FROM document_embeddings")
            results = []
            for row in cursor.fetchall():
                try:
                    embedding = json.loads(row[1])
                    results.append((row[0], embedding))
                except (json.JSONDecodeError, TypeError):
                    continue
            return results
        finally:
            if should_close:
                conn.close()

    def _build_embedding_text(self, title: str, content: str) -> str:
        """Build text for embedding: title + truncated content."""
        parts = []
        if title and title.strip():
            parts.append(title.strip())
        if content and content.strip():
            truncated = content.strip()[: self.max_content_length]
            parts.append(truncated)
        return "\n".join(parts)

    def _save_embedding(
        self,
        knowledge_id: str,
        embedding: List[float],
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Save embedding to document_embeddings table."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            embedding_json = json.dumps(embedding)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO document_embeddings (knowledge_id, embedding)
                   VALUES (?, ?)
                   ON CONFLICT(knowledge_id) DO UPDATE SET
                       embedding = excluded.embedding,
                       created_at = CURRENT_TIMESTAMP""",
                (knowledge_id, embedding_json),
            )
            conn.commit()
        finally:
            if should_close:
                conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection."""
        if not self.db_path:
            raise ValueError("db_path is required")
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
