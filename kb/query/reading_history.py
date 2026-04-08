"""
Reading history tracker for Knowledge Mining.

Records user interaction events (view, search, rag_query) for
smart recommendation and usage analytics.
"""
import logging
from typing import Any, Dict, List, Optional

from kb.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


class ReadingHistory:
    """Records and queries user interaction history."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def record_view(self, knowledge_id: str) -> None:
        """Record a document view event."""
        self._record("view", knowledge_id=knowledge_id)

    def record_search(self, query: str) -> None:
        """Record a search event."""
        self._record("search", query=query)

    def record_rag_query(self, query: str) -> None:
        """Record a RAG query event."""
        self._record("rag_query", query=query)

    def _record(
        self,
        action_type: str,
        knowledge_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> None:
        """Insert a reading history record."""
        try:
            cursor = self.storage.conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO reading_history (knowledge_id, query, action_type) "
                    "VALUES (?, ?, ?)",
                    (knowledge_id, query, action_type),
                )
                self.storage.conn.commit()
            finally:
                cursor.close()
        except Exception as e:
            logger.warning(f"Failed to record reading history: {e}")

    def get_recent_views(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently viewed documents."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT rh.knowledge_id, k.title, rh.created_at, rh.action_type
                   FROM reading_history rh
                   LEFT JOIN knowledge k ON rh.knowledge_id = k.id
                   WHERE rh.action_type = 'view' AND rh.knowledge_id IS NOT NULL
                   ORDER BY rh.created_at DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_recent_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent search and RAG queries."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT query, action_type, created_at
                   FROM reading_history
                   WHERE action_type IN ('search', 'rag_query') AND query IS NOT NULL
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_view_history_embeddings(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recently viewed document IDs with timestamps for recommendation.

        Returns unique knowledge_ids ordered by most recent view.
        """
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT DISTINCT rh.knowledge_id, MAX(rh.created_at) as last_viewed
                   FROM reading_history rh
                   WHERE rh.action_type = 'view' AND rh.knowledge_id IS NOT NULL
                   GROUP BY rh.knowledge_id
                   ORDER BY last_viewed DESC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get reading history statistics."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT action_type, COUNT(*) as count FROM reading_history "
                "GROUP BY action_type ORDER BY count DESC"
            )
            by_type = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) FROM reading_history")
            total = cursor.fetchone()[0]

            return {"total": total, "by_type": by_type}
        finally:
            cursor.close()
