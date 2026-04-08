"""
Document relation builder for Knowledge Mining.

Discovers cross-document relationships via:
1. Embedding similarity: compares document-level embeddings (title + summary)
2. Shared entities: finds documents that mention the same entities

Results are stored in the document_relations table.
"""
import json
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple

from kb.config import Config
from kb.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _serialize_embedding(embedding: List[float]) -> bytes:
    """Serialize embedding to bytes for SQLite BLOB storage."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _deserialize_embedding(data) -> List[float]:
    """Deserialize embedding from SQLite (JSON string or BLOB)."""
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, bytes):
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            count = len(data) // 4
            return list(struct.unpack(f"{count}f", data))
    raise TypeError(f"Unexpected embedding type: {type(data)}")


class DocRelationBuilder:
    """
    Builds cross-document relationships.

    Two relation types:
    - embedding_similarity: cosine similarity >= threshold
    - shared_entity: documents sharing one or more entities
    """

    def __init__(
        self,
        storage: SQLiteStorage,
        config: Optional[Config] = None,
        similarity_threshold: float = 0.75,
        max_compare_docs: int = 1000,
    ):
        self.storage = storage
        self.config = config
        self.similarity_threshold = similarity_threshold
        self.max_compare_docs = max_compare_docs

    def generate_doc_embedding(
        self, knowledge_id: str, title: str, summary: str
    ) -> Optional[List[float]]:
        """
        Generate and store a document-level embedding from title + summary.

        Args:
            knowledge_id: Document ID.
            title: Document title.
            summary: Document summary (first 500 chars used).

        Returns:
            The embedding vector, or None if embedding fails.
        """
        from kb.processors.embedder import Embedder

        try:
            embedder = Embedder.from_config(self.config)
        except Exception as e:
            logger.warning(f"Cannot create embedder: {e}")
            return None

        text = f"{title}\n{(summary or '')[:500]}".strip()
        if not text:
            return None

        try:
            embeddings = embedder.embed([text])
            if not embeddings or not embeddings[0]:
                return None
            embedding = embeddings[0]

            # Store in document_embeddings table
            cursor = self.storage.conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO document_embeddings (knowledge_id, embedding) VALUES (?, ?)",
                    (knowledge_id, _serialize_embedding(embedding)),
                )
                self.storage.conn.commit()
            finally:
                cursor.close()

            return embedding
        except Exception as e:
            logger.error(f"Failed to generate doc embedding for {knowledge_id}: {e}")
            return None

    def get_doc_embedding(self, knowledge_id: str) -> Optional[List[float]]:
        """Get cached document embedding."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT embedding FROM document_embeddings WHERE knowledge_id = ?",
                (knowledge_id,),
            )
            row = cursor.fetchone()
            if row:
                return _deserialize_embedding(row[0])
            return None
        finally:
            cursor.close()

    def find_similar_documents(
        self, knowledge_id: str, embedding: List[float]
    ) -> List[Tuple[str, float]]:
        """
        Find documents similar to the given one by embedding similarity.

        Args:
            knowledge_id: The source document ID (excluded from results).
            embedding: The source document embedding.

        Returns:
            List of (knowledge_id, similarity_score) tuples above threshold.
        """
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT knowledge_id, embedding FROM document_embeddings "
                "WHERE knowledge_id != ? "
                "ORDER BY created_at DESC LIMIT ?",
                (knowledge_id, self.max_compare_docs),
            )
            results = []
            for row in cursor.fetchall():
                other_id = row[0]
                other_embedding = _deserialize_embedding(row[1])
                sim = _cosine_similarity(embedding, other_embedding)
                if sim >= self.similarity_threshold:
                    results.append((other_id, sim))

            results.sort(key=lambda x: x[1], reverse=True)
            return results
        finally:
            cursor.close()

    def find_shared_entity_relations(
        self, knowledge_id: str
    ) -> List[Tuple[str, float, List[int]]]:
        """
        Find documents sharing entities with the given document.

        Args:
            knowledge_id: The source document ID.

        Returns:
            List of (other_knowledge_id, shared_count, shared_entity_ids) tuples.
        """
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """
                SELECT em2.knowledge_id, COUNT(*) as shared_count,
                       GROUP_CONCAT(em2.entity_id) as entity_ids
                FROM entity_mentions em1
                JOIN entity_mentions em2 ON em1.entity_id = em2.entity_id
                WHERE em1.knowledge_id = ? AND em2.knowledge_id != ?
                GROUP BY em2.knowledge_id
                HAVING shared_count >= 1
                ORDER BY shared_count DESC
                """,
                (knowledge_id, knowledge_id),
            )
            results = []
            for row in cursor.fetchall():
                other_id = row[0]
                shared_count = row[1]
                entity_ids = [int(x) for x in row[2].split(",")]
                results.append((other_id, float(shared_count), entity_ids))
            return results
        finally:
            cursor.close()

    def save_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        score: float,
        shared_entities: Optional[List[int]] = None,
    ) -> None:
        """Save a document relation to the database."""
        cursor = self.storage.conn.cursor()
        try:
            shared_json = json.dumps(shared_entities) if shared_entities else None
            cursor.execute(
                """
                INSERT OR REPLACE INTO document_relations
                (source_knowledge_id, target_knowledge_id, relation_type, score, shared_entities)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, target_id, relation_type, score, shared_json),
            )
            self.storage.conn.commit()
        finally:
            cursor.close()

    def build_relations_for_document(self, knowledge_id: str) -> Dict[str, int]:
        """
        Build all relations for a newly added document (incremental).

        Call this after a document is indexed. It:
        1. Gets or generates the document embedding
        2. Finds similar documents by embedding
        3. Finds shared entity relations
        4. Saves all discovered relations

        Args:
            knowledge_id: The document to build relations for.

        Returns:
            Dict with counts: {"embedding_similarity": N, "shared_entity": M}
        """
        counts = {"embedding_similarity": 0, "shared_entity": 0}

        # Get document info for embedding generation
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT title, summary FROM knowledge WHERE id = ?",
                (knowledge_id,),
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Document {knowledge_id} not found")
                return counts
            title = row[0] or ""
            summary = row[1] or ""
        finally:
            cursor.close()

        # 1. Generate/get embedding
        embedding = self.get_doc_embedding(knowledge_id)
        if embedding is None:
            embedding = self.generate_doc_embedding(knowledge_id, title, summary)

        # 2. Find similar documents by embedding
        if embedding:
            similar_docs = self.find_similar_documents(knowledge_id, embedding)
            for other_id, score in similar_docs:
                self.save_relation(
                    knowledge_id, other_id, "embedding_similarity", score
                )
                counts["embedding_similarity"] += 1

        # 3. Find shared entity relations
        shared_docs = self.find_shared_entity_relations(knowledge_id)
        for other_id, shared_count, entity_ids in shared_docs:
            self.save_relation(
                knowledge_id, other_id, "shared_entity", shared_count, entity_ids
            )
            counts["shared_entity"] += 1

        logger.info(
            f"Built relations for {knowledge_id}: "
            f"{counts['embedding_similarity']} similar, "
            f"{counts['shared_entity']} shared entities"
        )
        return counts

    def rebuild_all_relations(self) -> Dict[str, int]:
        """
        Rebuild all document relations from scratch.

        Clears existing relations and recomputes for all documents.
        Used by `kb graph rebuild` CLI command.

        Returns:
            Total counts of relations built.
        """
        # Clear existing relations
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute("DELETE FROM document_relations")
            self.storage.conn.commit()
        finally:
            cursor.close()

        # Get all document IDs
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute("SELECT id FROM knowledge ORDER BY collected_at DESC")
            doc_ids = [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

        total_counts = {"embedding_similarity": 0, "shared_entity": 0}
        for doc_id in doc_ids:
            counts = self.build_relations_for_document(doc_id)
            total_counts["embedding_similarity"] += counts["embedding_similarity"]
            total_counts["shared_entity"] += counts["shared_entity"]

        logger.info(
            f"Rebuilt all relations: {len(doc_ids)} docs, "
            f"{total_counts['embedding_similarity']} similar, "
            f"{total_counts['shared_entity']} shared entities"
        )
        return total_counts
