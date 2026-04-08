"""
Recommendation routes for Knowledge Base Web API.

Provides endpoints for smart content recommendations
and reading history queries.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/recommendations")
async def get_recommendations(limit: int = 5) -> Dict[str, Any]:
    """
    Get personalized document recommendations.

    Based on reading history with time-decay weighted embedding similarity.

    Args:
        limit: Maximum number of recommendations (default 5).

    Returns:
        Dict with list of recommended documents.
    """
    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=400, detail="limit must be between 1 and 20"
        )

    try:
        from kb.web.dependencies import get_config

        from kb.processors.recommendation import RecommendationEngine

        config = get_config()
        engine = RecommendationEngine.from_config(config)
        results = engine.recommend(limit=limit)
        return {"recommendations": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}",
        )


@router.get("/reading-history")
async def get_reading_history(
    action_type: Optional[str] = None, limit: int = 50
) -> Dict[str, Any]:
    """
    Get reading history.

    Args:
        action_type: Filter by action type (view/search/rag_query).
        limit: Maximum number of records (default 50).

    Returns:
        Dict with recent views, queries, and stats.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400, detail="limit must be between 1 and 200"
        )

    try:
        from kb.web.dependencies import get_reading_history

        rh = get_reading_history()

        result: Dict[str, Any] = {"stats": rh.get_stats()}

        if action_type == "view" or action_type is None:
            result["recent_views"] = rh.get_recent_views(limit=limit)
        if action_type == "search" or action_type == "rag_query" or action_type is None:
            result["recent_queries"] = rh.get_recent_queries(limit=limit)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reading history query failed: {str(e)}",
        )
