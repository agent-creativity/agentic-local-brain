"""
主题聚类模块

基于 HDBSCAN 的文档主题自动发现，支持增量分类和 centroid 更新。

聚类流程：
1. 获取所有文档的 document embedding
2. HDBSCAN 无监督聚类
3. LLM 为每个 cluster 生成主题标签和描述
4. 结果写入 topic_clusters + knowledge_topics 表
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from kb.config import Config
from kb.processors.tag_extractor import LLMProvider, LiteLLMProvider

logger = logging.getLogger(__name__)

try:
    from sklearn.cluster import HDBSCAN
except ImportError:
    HDBSCAN = None


class TopicClusterer:
    """
    主题聚类服务。

    使用 HDBSCAN 对文档级 embedding 做无监督聚类，
    LLM 生成主题标签，支持增量分类和 centroid 更新。
    """

    LABEL_PROMPT = """Based on the following document titles from a knowledge base cluster, generate a concise topic label and description.

Document titles:
{titles}

Requirements:
- Topic label: 2-6 words, captures the common theme
- Description: 1 sentence explaining what this topic covers
- Use the same language as the document titles

Return ONLY a JSON object:
{{"label": "topic label", "description": "one sentence description"}}"""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        db_path: Optional[str] = None,
        min_cluster_size: int = 5,
        similarity_threshold: float = 0.7,
    ) -> None:
        if HDBSCAN is None:
            raise ImportError(
                "scikit-learn is required for topic clustering. "
                "Install it with: pip install scikit-learn>=1.3"
            )
        self.provider = provider
        self.db_path = db_path
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold

    @classmethod
    def from_config(cls, config: Optional[Config] = None) -> "TopicClusterer":
        if config is None:
            config = Config()

        # LLM provider for label generation
        llm_config = config.get("llm", {})
        provider_name = llm_config.get("provider", "dashscope")
        model = llm_config.get("model", "qwen-plus")
        api_key = llm_config.get("api_key", "")

        provider = None
        if api_key:
            if provider_name == "litellm":
                provider = LiteLLMProvider(api_key=api_key, model=model)
            elif provider_name == "dashscope":
                litellm_model = model if "/" in model else f"dashscope/{model}"
                provider = LiteLLMProvider(api_key=api_key, model=litellm_model)
            elif provider_name == "openai_compatible":
                base_url = llm_config.get("base_url", "")
                litellm_model = model if "/" in model else f"openai/{model}"
                provider = LiteLLMProvider(
                    api_key=api_key, model=litellm_model, api_base=base_url
                )

        mining_config = config.get("knowledge_mining", {})
        topic_config = mining_config.get("topic_clustering", {})

        from pathlib import Path
        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")

        return cls(
            provider=provider,
            db_path=db_path,
            min_cluster_size=topic_config.get("min_cluster_size", 5),
        )

    def cluster_all(
        self,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """
        全量聚类：对所有文档 embedding 做 HDBSCAN 聚类。

        Returns:
            {"clusters": int, "classified": int, "noise": int}
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            # Load all document embeddings
            cursor = conn.cursor()
            cursor.execute(
                """SELECT de.knowledge_id, de.embedding, k.title
                   FROM document_embeddings de
                   JOIN knowledge k ON de.knowledge_id = k.id"""
            )
            rows = cursor.fetchall()

            if len(rows) < self.min_cluster_size:
                logger.warning(
                    f"Not enough documents ({len(rows)}) for clustering "
                    f"(min_cluster_size={self.min_cluster_size})"
                )
                return {"clusters": 0, "classified": 0, "noise": len(rows)}

            doc_ids = []
            embeddings = []
            titles = {}
            for row in rows:
                try:
                    embedding = json.loads(row[1])
                    doc_ids.append(row[0])
                    embeddings.append(embedding)
                    titles[row[0]] = row[2] or ""
                except (json.JSONDecodeError, TypeError):
                    continue

            if len(embeddings) < self.min_cluster_size:
                return {"clusters": 0, "classified": 0, "noise": len(embeddings)}

            X = np.array(embeddings)

            # Run HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                metric="euclidean",
            )
            labels = clusterer.fit_predict(X)

            # Clear existing clusters
            cursor.execute("DELETE FROM knowledge_topics")
            cursor.execute("DELETE FROM topic_clusters")
            conn.commit()

            # Group documents by cluster
            clusters = {}
            noise_count = 0
            for doc_id, label, embedding in zip(doc_ids, labels, embeddings):
                if label == -1:
                    noise_count += 1
                    continue
                if label not in clusters:
                    clusters[label] = {"doc_ids": [], "embeddings": [], "titles": []}
                clusters[label]["doc_ids"].append(doc_id)
                clusters[label]["embeddings"].append(embedding)
                clusters[label]["titles"].append(titles.get(doc_id, ""))

            classified = 0
            for label, cluster_data in clusters.items():
                cluster_embeddings = np.array(cluster_data["embeddings"])
                centroid = cluster_embeddings.mean(axis=0).tolist()

                # Generate topic label
                topic_label, description = self._generate_label(
                    cluster_data["titles"][:5]
                )

                # Save cluster
                cursor.execute(
                    """INSERT INTO topic_clusters
                       (label, description, document_count, centroid_embedding)
                       VALUES (?, ?, ?, ?)""",
                    (
                        topic_label,
                        description,
                        len(cluster_data["doc_ids"]),
                        json.dumps(centroid),
                    ),
                )
                cluster_id = cursor.lastrowid

                # Save document-cluster associations
                skipped = 0
                for doc_id in cluster_data["doc_ids"]:
                    # Verify document exists before inserting
                    cursor.execute(
                        "SELECT 1 FROM knowledge WHERE id = ?",
                        (doc_id,)
                    )
                    if cursor.fetchone() is None:
                        logger.warning(f"Skipping non-existent document {doc_id} in cluster {label}")
                        skipped += 1
                        continue

                    cursor.execute(
                        """INSERT INTO knowledge_topics (knowledge_id, cluster_id, confidence)
                           VALUES (?, ?, 1.0)""",
                        (doc_id, cluster_id),
                    )
                    classified += 1

                if skipped > 0:
                    logger.info(f"Skipped {skipped} non-existent documents in cluster {label}")

            conn.commit()
            return {
                "clusters": len(clusters),
                "classified": classified,
                "noise": noise_count,
            }

        finally:
            if should_close:
                conn.close()

    def classify_document(
        self,
        knowledge_id: str,
        embedding: List[float],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[int]:
        """
        增量分类：将新文档分配到最近的 cluster，并更新 centroid。

        Args:
            knowledge_id: 文档 ID
            embedding: 文档 embedding
            conn: SQLite 连接

        Returns:
            分配的 cluster_id，或 None（无匹配）
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, centroid_embedding, document_count FROM topic_clusters"
            )
            clusters = cursor.fetchall()

            if not clusters:
                return None

            doc_vec = np.array(embedding)
            best_cluster_id = None
            best_similarity = -1.0

            for cluster_id, centroid_json, doc_count in clusters:
                try:
                    centroid = np.array(json.loads(centroid_json))
                    similarity = self._cosine_similarity(doc_vec, centroid)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_cluster_id = cluster_id
                        best_doc_count = doc_count
                        best_centroid = centroid
                except (json.JSONDecodeError, TypeError):
                    continue

            if best_similarity < self.similarity_threshold:
                return None

            # Verify document exists before assigning to cluster
            cursor.execute("SELECT 1 FROM knowledge WHERE id = ?", (knowledge_id,))
            if cursor.fetchone() is None:
                logger.warning(f"Cannot classify non-existent document {knowledge_id}")
                return None

            # Assign document to cluster
            cursor.execute(
                """INSERT OR REPLACE INTO knowledge_topics
                   (knowledge_id, cluster_id, confidence)
                   VALUES (?, ?, ?)""",
                (knowledge_id, best_cluster_id, float(best_similarity)),
            )

            # Update centroid with running average
            new_centroid = (
                (best_centroid * best_doc_count + doc_vec) / (best_doc_count + 1)
            ).tolist()

            cursor.execute(
                """UPDATE topic_clusters
                   SET centroid_embedding = ?,
                       document_count = document_count + 1,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (json.dumps(new_centroid), best_cluster_id),
            )

            conn.commit()
            return best_cluster_id

        finally:
            if should_close:
                conn.close()

    def get_topics(
        self, conn: Optional[sqlite3.Connection] = None
    ) -> List[Dict[str, Any]]:
        """Get all topic clusters."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, label, description, document_count, created_at
                   FROM topic_clusters ORDER BY document_count DESC"""
            )
            return [
                {
                    "id": row[0],
                    "label": row[1],
                    "description": row[2],
                    "document_count": row[3],
                    "created_at": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            if should_close:
                conn.close()

    def get_topic_documents(
        self,
        cluster_id: int,
        limit: int = 20,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """Get documents in a topic cluster."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT k.id, k.title, k.content_type, k.collected_at, kt.confidence
                   FROM knowledge_topics kt
                   JOIN knowledge k ON kt.knowledge_id = k.id
                   WHERE kt.cluster_id = ?
                   ORDER BY kt.confidence DESC
                   LIMIT ?""",
                (cluster_id, limit),
            )
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "content_type": row[2],
                    "collected_at": row[3],
                    "confidence": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            if should_close:
                conn.close()

    def _generate_label(self, titles: List[str]) -> Tuple[str, str]:
        """Generate a topic label using LLM, or fallback to simple heuristic."""
        if self.provider:
            try:
                import re
                prompt = self.LABEL_PROMPT.format(
                    titles="\n".join(f"- {t}" for t in titles if t)
                )
                response = self.provider.generate(
                    prompt=prompt, temperature=0.1, max_retries=2
                )
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                data = json.loads(cleaned)
                return (
                    data.get("label", f"Topic ({len(titles)} docs)"),
                    data.get("description", ""),
                )
            except Exception as e:
                logger.warning(f"LLM label generation failed: {e}")

        # Fallback: use first title
        label = titles[0][:30] if titles else "Unknown Topic"
        return label, f"Cluster of {len(titles)} documents"

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
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
