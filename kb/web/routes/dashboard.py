"""
Dashboard routes for Knowledge Base Web API.

Provides endpoints for statistics and recent items.
"""
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
