"""
Graph query service for Knowledge Mining.

Provides graph traversal, entity queries, and document relation queries
using SQLite recursive CTEs for N-hop relationship discovery.
"""
import logging
from typing import Any, Dict, List, Optional

from kb.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


class GraphQuery:
    """Knowledge graph query service."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    def get_graph(
        self,
        entity_type: Optional[str] = None,
        depth: int = 2,
        limit: int = 100,
        entity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get graph data (nodes + edges) for visualization.

        Args:
            entity_type: Filter by entity type (person/concept/tool/project/organization).
            depth: Max relationship depth for traversal (default 2).
            limit: Max number of nodes to return (default 100).
            entity_id: If provided, return subgraph centered on this entity.

        Returns:
            Dict with nodes, edges, and stats.
        """
        cursor = self.storage.conn.cursor()
        try:
            if entity_id is not None:
                return self._get_subgraph(cursor, entity_id, depth, limit)
            else:
                return self._get_full_graph(cursor, entity_type, limit)
        finally:
            cursor.close()

    def _get_full_graph(
        self,
        cursor,
        entity_type: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        """Get full graph or filtered by entity type."""
        if entity_type:
            cursor.execute(
                "SELECT id, name, display_name, type, description, mention_count "
                "FROM entities WHERE type = ? ORDER BY mention_count DESC LIMIT ?",
                (entity_type, limit),
            )
        else:
            cursor.execute(
                "SELECT id, name, display_name, type, description, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT ?",
                (limit,),
            )
        nodes = [dict(row) for row in cursor.fetchall()]
        node_ids = {n["id"] for n in nodes}

        # Get edges between visible nodes
        if node_ids:
            placeholders = ",".join("?" for _ in node_ids)
            cursor.execute(
                f"SELECT id, source_entity_id, target_entity_id, relation_type, weight "
                f"FROM entity_relations "
                f"WHERE source_entity_id IN ({placeholders}) "
                f"AND target_entity_id IN ({placeholders})",
                list(node_ids) + list(node_ids),
            )
            edges = [dict(row) for row in cursor.fetchall()]
        else:
            edges = []

        # Stats
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entity_relations")
        total_relations = cursor.fetchone()[0]

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_entities": total_entities,
                "total_relations": total_relations,
                "displayed_nodes": len(nodes),
                "displayed_edges": len(edges),
            },
        }

    def _get_subgraph(
        self,
        cursor,
        entity_id: int,
        depth: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Get subgraph centered on a specific entity using recursive CTE."""
        # Find all related entity IDs within N hops
        cursor.execute(
            """
            WITH RECURSIVE related(entity_id, depth) AS (
                SELECT ?, 0
                UNION ALL
                SELECT CASE
                    WHEN er.source_entity_id = r.entity_id THEN er.target_entity_id
                    ELSE er.source_entity_id
                END, r.depth + 1
                FROM entity_relations er
                JOIN related r ON (er.source_entity_id = r.entity_id OR er.target_entity_id = r.entity_id)
                WHERE r.depth < ?
            )
            SELECT DISTINCT entity_id FROM related LIMIT ?
            """,
            (entity_id, depth, limit),
        )
        related_ids = [row[0] for row in cursor.fetchall()]

        if not related_ids:
            return {"nodes": [], "edges": [], "stats": {"total_entities": 0, "total_relations": 0, "displayed_nodes": 0, "displayed_edges": 0}}

        placeholders = ",".join("?" for _ in related_ids)

        # Get nodes
        cursor.execute(
            f"SELECT id, name, display_name, type, description, mention_count "
            f"FROM entities WHERE id IN ({placeholders})",
            related_ids,
        )
        nodes = [dict(row) for row in cursor.fetchall()]

        # Get edges between these nodes
        cursor.execute(
            f"SELECT id, source_entity_id, target_entity_id, relation_type, weight "
            f"FROM entity_relations "
            f"WHERE source_entity_id IN ({placeholders}) "
            f"AND target_entity_id IN ({placeholders})",
            related_ids + related_ids,
        )
        edges = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM entity_relations")
        total_relations = cursor.fetchone()[0]

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_entities": total_entities,
                "total_relations": total_relations,
                "displayed_nodes": len(nodes),
                "displayed_edges": len(edges),
            },
        }

    def get_entity(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get a single entity with its mentions and relations."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, name, display_name, type, description, mention_count, created_at "
                "FROM entities WHERE id = ?",
                (entity_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            entity = dict(row)

            # Get document mentions
            cursor.execute(
                "SELECT em.context, k.id as knowledge_id, k.title "
                "FROM entity_mentions em "
                "JOIN knowledge k ON k.id = em.knowledge_id "
                "WHERE em.entity_id = ?",
                (entity_id,),
            )
            entity["mentions"] = [dict(r) for r in cursor.fetchall()]

            # Get relations
            cursor.execute(
                "SELECT er.id, er.relation_type, er.weight, "
                "e.id as related_id, e.name as related_name, e.display_name as related_display_name, e.type as related_type "
                "FROM entity_relations er "
                "JOIN entities e ON e.id = er.target_entity_id "
                "WHERE er.source_entity_id = ? "
                "UNION ALL "
                "SELECT er.id, er.relation_type, er.weight, "
                "e.id as related_id, e.name as related_name, e.display_name as related_display_name, e.type as related_type "
                "FROM entity_relations er "
                "JOIN entities e ON e.id = er.source_entity_id "
                "WHERE er.target_entity_id = ?",
                (entity_id, entity_id),
            )
            entity["relations"] = [dict(r) for r in cursor.fetchall()]

            return entity
        finally:
            cursor.close()

    def get_related_documents(
        self,
        knowledge_id: str,
        limit: int = 10,
        relation_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get documents related to the given document.

        Args:
            knowledge_id: The source document ID.
            limit: Max number of related documents.
            relation_type: Filter by relation type (embedding_similarity/shared_entity).

        Returns:
            List of related documents with scores and reasons.
        """
        cursor = self.storage.conn.cursor()
        try:
            query = (
                "SELECT dr.target_knowledge_id as knowledge_id, "
                "k.title, dr.relation_type, dr.score, dr.shared_entities "
                "FROM document_relations dr "
                "JOIN knowledge k ON k.id = dr.target_knowledge_id "
                "WHERE dr.source_knowledge_id = ? "
            )
            params: list = [knowledge_id]

            if relation_type:
                query += "AND dr.relation_type = ? "
                params.append(relation_type)

            # Also check reverse direction
            query += (
                "UNION ALL "
                "SELECT dr.source_knowledge_id as knowledge_id, "
                "k.title, dr.relation_type, dr.score, dr.shared_entities "
                "FROM document_relations dr "
                "JOIN knowledge k ON k.id = dr.source_knowledge_id "
                "WHERE dr.target_knowledge_id = ? "
            )
            params.append(knowledge_id)

            if relation_type:
                query += "AND dr.relation_type = ? "
                params.append(relation_type)

            query += "ORDER BY score DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc["relation_type"] == "embedding_similarity":
                    doc["reason"] = "内容高度相似"
                elif doc["relation_type"] == "shared_entity":
                    doc["reason"] = "共享相关实体"
                else:
                    doc["reason"] = "相关文档"
                results.append(doc)

            return results
        finally:
            cursor.close()

    def search_entities(
        self, q: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search entities by name (case-insensitive LIKE)."""
        cursor = self.storage.conn.cursor()
        try:
            pattern = f"%{q}%"
            cursor.execute(
                "SELECT id, name, display_name, type, mention_count "
                "FROM entities "
                "WHERE name LIKE ? OR display_name LIKE ? "
                "ORDER BY mention_count DESC LIMIT ?",
                (pattern, pattern, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_document_entities(
        self, knowledge_id: str
    ) -> Dict[str, Any]:
        """Get entities and their relations for a specific document."""
        cursor = self.storage.conn.cursor()
        try:
            # Get entities mentioned in this document
            cursor.execute(
                "SELECT e.id, e.name, e.display_name, e.type, e.description, e.mention_count "
                "FROM entities e "
                "JOIN entity_mentions em ON em.entity_id = e.id "
                "WHERE em.knowledge_id = ?",
                (knowledge_id,),
            )
            nodes = [dict(row) for row in cursor.fetchall()]
            node_ids = [n["id"] for n in nodes]

            edges = []
            if len(node_ids) > 1:
                placeholders = ",".join("?" for _ in node_ids)
                cursor.execute(
                    f"SELECT id, source_entity_id, target_entity_id, relation_type, weight "
                    f"FROM entity_relations "
                    f"WHERE source_entity_id IN ({placeholders}) "
                    f"AND target_entity_id IN ({placeholders})",
                    node_ids + node_ids,
                )
                edges = [dict(row) for row in cursor.fetchall()]

            return {
                "knowledge_id": knowledge_id,
                "nodes": nodes,
                "edges": edges,
            }
        finally:
            cursor.close()

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get overall graph statistics."""
        cursor = self.storage.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM entity_relations")
            total_relations = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM document_relations")
            total_doc_relations = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM entity_mentions")
            total_mentions = cursor.fetchone()[0]

            # Entity type distribution
            cursor.execute(
                "SELECT type, COUNT(*) as count FROM entities GROUP BY type ORDER BY count DESC"
            )
            type_distribution = [dict(row) for row in cursor.fetchall()]

            # Relation type distribution
            cursor.execute(
                "SELECT relation_type, COUNT(*) as count FROM entity_relations GROUP BY relation_type ORDER BY count DESC"
            )
            relation_distribution = [dict(row) for row in cursor.fetchall()]

            # Top entities by mention count
            cursor.execute(
                "SELECT id, name, display_name, type, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT 10"
            )
            top_entities = [dict(row) for row in cursor.fetchall()]

            return {
                "total_entities": total_entities,
                "total_relations": total_relations,
                "total_doc_relations": total_doc_relations,
                "total_mentions": total_mentions,
                "type_distribution": type_distribution,
                "relation_distribution": relation_distribution,
                "top_entities": top_entities,
            }
        finally:
            cursor.close()

    def get_entities_for_context(
        self, document_ids: List[str], max_entities: int = 10
    ) -> List[Dict[str, Any]]:
        """Get entity context for RAG enrichment from a list of document IDs.

        For each document, fetches mentioned entities and their 1-hop relations.
        Returns deduplicated entities with their mentions and relations,
        prioritized by frequency across documents.

        Args:
            document_ids: List of knowledge item IDs
            max_entities: Maximum entities to return

        Returns:
            List of dicts with: name, type, mentions (context snippets), relations
        """
        if not document_ids:
            return []

        cursor = self.storage.conn.cursor()
        try:
            # Collect entities across all documents with their mentions
            entity_data: Dict[int, Dict[str, Any]] = {}
            entity_frequency: Dict[int, int] = {}

            for doc_id in document_ids:
                # Get entities mentioned in this document
                cursor.execute(
                    """SELECT e.id, e.name, e.display_name, e.type, e.description, em.context
                       FROM entities e
                       JOIN entity_mentions em ON em.entity_id = e.id
                       WHERE em.knowledge_id = ?""",
                    (doc_id,),
                )

                for row in cursor.fetchall():
                    entity_id = row["id"]
                    if entity_id not in entity_data:
                        entity_data[entity_id] = {
                            "name": row["name"],
                            "display_name": row["display_name"],
                            "type": row["type"],
                            "description": row["description"],
                            "mentions": [],
                        }
                        entity_frequency[entity_id] = 0

                    # Add mention context if available
                    if row["context"]:
                        entity_data[entity_id]["mentions"].append(row["context"])
                    entity_frequency[entity_id] += 1

            if not entity_data:
                return []

            # Sort entities by frequency across documents
            sorted_entity_ids = sorted(
                entity_frequency.keys(),
                key=lambda eid: entity_frequency[eid],
                reverse=True,
            )

            # Take top entities
            top_entity_ids = sorted_entity_ids[:max_entities]

            # Fetch 1-hop relations for top entities
            result = []
            for entity_id in top_entity_ids:
                entity = entity_data[entity_id].copy()
                entity["entity_id"] = entity_id

                # Get 1-hop relations
                cursor.execute(
                    """SELECT er.relation_type, er.weight,
                              e.id as related_id, e.name as related_name,
                              e.display_name as related_display_name, e.type as related_type
                       FROM entity_relations er
                       JOIN entities e ON e.id = er.target_entity_id
                       WHERE er.source_entity_id = ?
                       UNION ALL
                       SELECT er.relation_type, er.weight,
                              e.id as related_id, e.name as related_name,
                              e.display_name as related_display_name, e.type as related_type
                       FROM entity_relations er
                       JOIN entities e ON e.id = er.source_entity_id
                       WHERE er.target_entity_id = ?""",
                    (entity_id, entity_id),
                )

                relations = []
                for row in cursor.fetchall():
                    relations.append({
                        "relation_type": row["relation_type"],
                        "weight": row["weight"],
                        "related_entity": {
                            "id": row["related_id"],
                            "name": row["related_name"],
                            "display_name": row["related_display_name"],
                            "type": row["related_type"],
                        },
                    })

                entity["relations"] = relations
                entity["frequency"] = entity_frequency[entity_id]
                result.append(entity)

            logger.debug(
                f"Retrieved {len(result)} entities for context from {len(document_ids)} documents"
            )
            return result

        except Exception as e:
            logger.warning(f"Failed to get entities for context: {e}")
            return []
        finally:
            cursor.close()
