"""
智能推荐模块

基于阅读历史和文档 embedding 的内容推荐。
v0.6 简单版：时间衰减加权 embedding 相似推荐。

算法：
1. 取最近 N 次阅读的文档 embedding
2. 计算时间衰减加权均值（越近权重越高）
3. 在 document embedding 中找最相似的、未访问过的文档
4. 同主题 cluster 文档额外加分
"""

import json
import logging
import math
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from kb.config import Config

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    智能推荐引擎。

    基于用户最近的阅读历史，推荐相似但未读的文档。
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        recent_history_count: int = 20,
        time_decay_lambda: float = 0.1,
        topic_bonus: float = 0.1,
        default_limit: int = 5,
    ) -> None:
        self.db_path = db_path
        self.recent_history_count = recent_history_count
        self.time_decay_lambda = time_decay_lambda
        self.topic_bonus = topic_bonus
        self.default_limit = default_limit

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "RecommendationEngine":
        if config is None:
            config = Config()

        from pathlib import Path

        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")

        mining_config = config.get("knowledge_mining", {})
        rec_config = mining_config.get("recommendation", {})

        return cls(
            db_path=db_path,
            recent_history_count=rec_config.get("recent_history_count", 20),
            time_decay_lambda=rec_config.get("time_decay_lambda", 0.1),
            default_limit=rec_config.get("default_limit", 5),
        )

    def recommend(
        self,
        limit: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """
        生成推荐列表。

        Returns:
            [{"knowledge_id": str, "title": str, "reason": str, "score": float}]
        """
        limit = limit or self.default_limit
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            # 1. Get recent reading history
            recent_docs = self._get_recent_history(conn)
            if not recent_docs:
                return self._fallback_recommendations(limit, conn)

            # 2. Get embeddings for recently read documents
            recent_ids = [doc["knowledge_id"] for doc in recent_docs if doc["knowledge_id"]]
            if not recent_ids:
                return self._fallback_recommendations(limit, conn)

            recent_embeddings = self._get_embeddings(recent_ids, conn)
            if not recent_embeddings:
                return self._fallback_recommendations(limit, conn)

            # 3. Compute time-decay weighted average embedding
            now = datetime.now()
            weighted_sum = None
            weight_total = 0.0

            for doc in recent_docs:
                kid = doc["knowledge_id"]
                if kid not in recent_embeddings:
                    continue

                days_ago = max(
                    (now - datetime.fromisoformat(doc["created_at"])).total_seconds()
                    / 86400,
                    0.01,
                )
                weight = math.exp(-self.time_decay_lambda * days_ago)

                emb = np.array(recent_embeddings[kid])
                if weighted_sum is None:
                    weighted_sum = emb * weight
                else:
                    weighted_sum += emb * weight
                weight_total += weight

            if weighted_sum is None or weight_total == 0:
                return self._fallback_recommendations(limit, conn)

            user_profile = weighted_sum / weight_total

            # 4. Get all document embeddings and find most similar unread
            all_embeddings = self._get_all_embeddings(conn)
            recently_read_set = set(recent_ids)

            # 5. Get topic clusters for bonus scoring
            doc_topics = self._get_doc_topics(recent_ids, conn)

            candidates = []
            for doc_id, embedding in all_embeddings.items():
                if doc_id in recently_read_set:
                    continue

                similarity = self._cosine_similarity(
                    user_profile, np.array(embedding)
                )

                # Topic bonus
                doc_topic = self._get_single_doc_topic(doc_id, conn)
                if doc_topic and doc_topic in doc_topics:
                    similarity += self.topic_bonus

                candidates.append((doc_id, similarity))

            # Sort by similarity descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = candidates[:limit]

            # 6. Build result with titles and reasons
            results = []
            for doc_id, score in top_candidates:
                title = self._get_doc_title(doc_id, conn)
                reason = self._generate_reason(
                    doc_id, recent_docs, recent_embeddings, doc_topics, conn
                )
                results.append(
                    {
                        "knowledge_id": doc_id,
                        "title": title,
                        "reason": reason,
                        "score": round(score, 4),
                    }
                )

            return results

        finally:
            if should_close:
                conn.close()

    def record_action(
        self,
        action_type: str,
        knowledge_id: Optional[str] = None,
        query: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Record a user action to reading_history."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO reading_history (knowledge_id, query, action_type)
                   VALUES (?, ?, ?)""",
                (knowledge_id, query, action_type),
            )
            conn.commit()
        finally:
            if should_close:
                conn.close()

    def _get_recent_history(self, conn: sqlite3.Connection) -> List[Dict]:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT knowledge_id, query, action_type, created_at
               FROM reading_history
               WHERE knowledge_id IS NOT NULL
               ORDER BY created_at DESC
               LIMIT ?""",
            (self.recent_history_count,),
        )
        return [
            {
                "knowledge_id": row[0],
                "query": row[1],
                "action_type": row[2],
                "created_at": row[3],
            }
            for row in cursor.fetchall()
        ]

    def _get_embeddings(
        self, knowledge_ids: List[str], conn: sqlite3.Connection
    ) -> Dict[str, List[float]]:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in knowledge_ids)
        cursor.execute(
            f"SELECT knowledge_id, embedding FROM document_embeddings WHERE knowledge_id IN ({placeholders})",
            knowledge_ids,
        )
        result = {}
        for row in cursor.fetchall():
            try:
                result[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                continue
        return result

    def _get_all_embeddings(self, conn: sqlite3.Connection) -> Dict[str, List[float]]:
        cursor = conn.cursor()
        cursor.execute("SELECT knowledge_id, embedding FROM document_embeddings")
        result = {}
        for row in cursor.fetchall():
            try:
                result[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                continue
        return result

    def _get_doc_topics(
        self, knowledge_ids: List[str], conn: sqlite3.Connection
    ) -> set:
        """Get topic cluster IDs for a set of documents."""
        if not knowledge_ids:
            return set()
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in knowledge_ids)
        cursor.execute(
            f"SELECT DISTINCT cluster_id FROM knowledge_topics WHERE knowledge_id IN ({placeholders})",
            knowledge_ids,
        )
        return {row[0] for row in cursor.fetchall()}

    def _get_single_doc_topic(
        self, knowledge_id: str, conn: sqlite3.Connection
    ) -> Optional[int]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cluster_id FROM knowledge_topics WHERE knowledge_id = ? LIMIT 1",
            (knowledge_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_doc_title(self, knowledge_id: str, conn: sqlite3.Connection) -> str:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title FROM knowledge WHERE id = ?", (knowledge_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else ""

    def _generate_reason(
        self,
        doc_id: str,
        recent_docs: List[Dict],
        recent_embeddings: Dict[str, List[float]],
        user_topics: set,
        conn: sqlite3.Connection,
    ) -> str:
        """Generate a natural language reason for the recommendation."""
        # Check if same topic
        doc_topic = self._get_single_doc_topic(doc_id, conn)
        if doc_topic and doc_topic in user_topics:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT label FROM topic_clusters WHERE id = ?", (doc_topic,)
            )
            row = cursor.fetchone()
            if row:
                return f"同属于「{row[0]}」主题"

        # Default: similar to recent reading
        if recent_docs:
            recent_title = self._get_doc_title(
                recent_docs[0]["knowledge_id"], conn
            )
            if recent_title:
                return f"与你最近阅读的《{recent_title}》内容相关"

        return "基于你的阅读历史推荐"

    def _fallback_recommendations(
        self, limit: int, conn: sqlite3.Connection
    ) -> List[Dict[str, Any]]:
        """No reading history: recommend most recent documents."""
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, title FROM knowledge
               ORDER BY collected_at DESC LIMIT ?""",
            (limit,),
        )
        return [
            {
                "knowledge_id": row[0],
                "title": row[1],
                "reason": "最新收录的文档",
                "score": 0.0,
            }
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path:
            raise ValueError("db_path is required")
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
