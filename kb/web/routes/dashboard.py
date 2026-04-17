"""
Dashboard routes for Knowledge Base Web API.

Provides endpoints for statistics and recent items.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Get knowledge base statistics.
    
    Returns statistics including total items, items by type, 
    total tags, total chunks, and version info.
    
    Returns:
        Dict with stats: total_items, items_by_type, total_tags, total_chunks, version
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        from kb.version import get_version
        
        storage = get_sqlite_storage()
        stats = storage.get_stats()
        stats["version"] = get_version()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/recent")
async def get_recent_items(
    limit: int = 20,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recently collected items.
    
    Args:
        limit: Maximum number of items to return (default: 20)
        content_type: Filter by content type (optional)
    
    Returns:
        List of recent knowledge items with their tags.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        items = storage.list_knowledge(
            limit=limit,
            content_type=content_type
        )
        
        # Fetch tags for each item
        for item in items:
            item["tags"] = storage.get_tags(item["id"])
        
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent items: {str(e)}")


@router.get("/rag-stats")
async def get_rag_stats() -> Dict[str, Any]:
    """
    Get RAG-specific analytics.

    Returns statistics about RAG usage including total queries,
    conversation sessions, and recent activity.

    Returns:
        Dict with:
        - total_queries: Total number of RAG queries recorded
        - total_conversations: Total number of conversation sessions
        - avg_turns_per_session: Average turns per conversation session
        - recent_queries: List of recent RAG queries
        - queries_today: Number of queries today
        - queries_this_week: Number of queries in the last 7 days
    """
    try:
        from kb.web.dependencies import get_sqlite_storage

        storage = get_sqlite_storage()
        conn = storage.conn
        cursor = conn.cursor()

        # Initialize result with defaults
        result = {
            "total_queries": 0,
            "total_conversations": 0,
            "avg_turns_per_session": 0.0,
            "recent_queries": [],
            "queries_today": 0,
            "queries_this_week": 0,
        }

        # Check if reading_history table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'"
        )
        if cursor.fetchone():
            # Get total RAG queries
            cursor.execute(
                "SELECT COUNT(*) FROM reading_history WHERE action_type = 'rag_query'"
            )
            result["total_queries"] = cursor.fetchone()[0]

            # Get queries today
            cursor.execute(
                """SELECT COUNT(*) FROM reading_history
                   WHERE action_type = 'rag_query'
                   AND date(created_at) = date('now')"""
            )
            result["queries_today"] = cursor.fetchone()[0]

            # Get queries this week
            cursor.execute(
                """SELECT COUNT(*) FROM reading_history
                   WHERE action_type = 'rag_query'
                   AND created_at >= datetime('now', '-7 days')"""
            )
            result["queries_this_week"] = cursor.fetchone()[0]

            # Get recent queries
            cursor.execute(
                """SELECT query, created_at
                   FROM reading_history
                   WHERE action_type = 'rag_query' AND query IS NOT NULL
                   ORDER BY created_at DESC
                   LIMIT 10"""
            )
            result["recent_queries"] = [
                {"query": row[0], "timestamp": row[1]}
                for row in cursor.fetchall()
            ]

        # Check if rag_conversations table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rag_conversations'"
        )
        if cursor.fetchone():
            # Get total conversation sessions
            cursor.execute("SELECT COUNT(*) FROM rag_conversations")
            result["total_conversations"] = cursor.fetchone()[0]

            # Get average turns per session
            cursor.execute(
                """SELECT AVG(turn_count) FROM (
                    SELECT COUNT(*) as turn_count
                    FROM rag_conversation_turns
                    GROUP BY session_id
                )"""
            )
            avg_turns = cursor.fetchone()[0]
            result["avg_turns_per_session"] = round(avg_turns, 2) if avg_turns else 0.0

        cursor.close()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get RAG stats: {str(e)}")
