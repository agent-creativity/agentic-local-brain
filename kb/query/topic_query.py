"""
Topic query service for Knowledge Mining.

Provides topic listing, document-by-topic queries, and trend analysis.
Wraps TopicClusterer for read-only query operations.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from kb.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


class TopicQuery:
    """Topic query service for API and CLI."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def get_topics(self) -> List[Dict[str, Any]]:
        """Get all topic clusters, ordered by document count."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, label, description, document_count, created_at, updated_at "
                "FROM topic_clusters ORDER BY document_count DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_topic(self, cluster_id: int) -> Optional[Dict[str, Any]]:
        """Get a single topic cluster by ID."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, label, description, document_count, created_at, updated_at "
                "FROM topic_clusters WHERE id = ?",
                (cluster_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()

    def get_topic_documents(
        self, cluster_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get documents belonging to a topic cluster."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT k.id, k.title, k.content_type, k.collected_at, kt.confidence
                   FROM knowledge_topics kt
                   JOIN knowledge k ON kt.knowledge_id = k.id
                   WHERE kt.cluster_id = ?
                   ORDER BY kt.confidence DESC
                   LIMIT ?""",
                (cluster_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_topic_trend(self, period: str = "monthly") -> List[Dict[str, Any]]:
        """
        Get topic trends over time.

        Groups documents by topic and time period, showing how topics
        grow or shrink over time.

        Args:
            period: 'weekly' or 'monthly' (default 'monthly').

        Returns:
            List of dicts with topic_id, label, period, count.
        """
        if period == "weekly":
            date_format = "%Y-W%W"
        else:
            date_format = "%Y-%m"

        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT tc.id as topic_id, tc.label,
                          strftime(?, k.collected_at) as period,
                          COUNT(*) as count
                   FROM knowledge_topics kt
                   JOIN knowledge k ON kt.knowledge_id = k.id
                   JOIN topic_clusters tc ON kt.cluster_id = tc.id
                   GROUP BY tc.id, period
                   ORDER BY period ASC, count DESC""",
                (date_format,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_timeline_data(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Get documents with their topic assignments for timeline visualization.

        Returns individual documents with collected_at (X-axis) and topic label (Y-axis).

        Args:
            limit: Maximum number of documents to return (default 500).

        Returns:
            List of dicts with document info and topic assignment.
        """
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                """SELECT k.id, k.title, k.content_type, k.collected_at,
                          tc.id as topic_id, tc.label as topic_label,
                          kt.confidence
                   FROM knowledge_topics kt
                   JOIN knowledge k ON kt.knowledge_id = k.id
                   JOIN topic_clusters tc ON kt.cluster_id = tc.id
                   WHERE k.collected_at IS NOT NULL
                   ORDER BY k.collected_at ASC
                   LIMIT ?""",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_topic_stats(self) -> Dict[str, Any]:
        """Get topic clustering statistics."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM topic_clusters")
            total_topics = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM knowledge_topics")
            total_classified = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM knowledge")
            total_docs = cursor.fetchone()[0]

            unclassified = total_docs - total_classified

            return {
                "total_topics": total_topics,
                "total_classified": total_classified,
                "total_documents": total_docs,
                "unclassified": unclassified,
            }
        finally:
            cursor.close()
