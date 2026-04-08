"""
Topic routes for Knowledge Base Web API.

Provides endpoints for topic listing, document-by-topic queries,
topic trend analysis, and topic rebuild trigger.
"""
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()

# Track rebuild state
_rebuild_state = {"running": False, "last_result": None, "last_error": None}


@router.get("/topics")
async def get_topics() -> Dict[str, Any]:
    """
    Get all topic clusters.

    Returns:
        Dict with list of topics and stats.
    """
    try:
        from kb.web.dependencies import get_topic_query

        tq = get_topic_query()
        topics = tq.get_topics()
        stats = tq.get_topic_stats()
        return {"topics": topics, "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Topic query failed: {str(e)}"
        )


@router.get("/topics/{cluster_id}/documents")
async def get_topic_documents(
    cluster_id: int, limit: int = 20
) -> Dict[str, Any]:
    """
    Get documents in a topic cluster.

    Args:
        cluster_id: Topic cluster ID.
        limit: Maximum number of documents (default 20).

    Returns:
        Dict with topic info and documents.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400, detail="limit must be between 1 and 100"
        )

    try:
        from kb.web.dependencies import get_topic_query

        tq = get_topic_query()
        topic = tq.get_topic(cluster_id)
        if topic is None:
            raise HTTPException(status_code=404, detail="Topic not found")

        documents = tq.get_topic_documents(cluster_id, limit=limit)
        return {"topic": topic, "documents": documents}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Topic documents query failed: {str(e)}",
        )


@router.get("/topics/timeline")
async def get_topic_timeline(limit: int = 500) -> Dict[str, Any]:
    """
    Get timeline data: documents with topic assignments over time.

    Returns individual documents with collected_at (time) and topic label,
    for use in a scatter/timeline chart.

    Args:
        limit: Maximum number of documents (default 500).

    Returns:
        Dict with timeline data and topic list for Y-axis.
    """
    if limit < 1 or limit > 2000:
        raise HTTPException(
            status_code=400, detail="limit must be between 1 and 2000"
        )

    try:
        from kb.web.dependencies import get_topic_query

        tq = get_topic_query()
        documents = tq.get_timeline_data(limit=limit)
        topics = tq.get_topics()
        return {
            "documents": documents,
            "topics": [{"id": t["id"], "label": t["label"]} for t in topics],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Timeline query failed: {str(e)}",
        )


@router.get("/topics/trend")
async def get_topic_trend(period: str = "monthly") -> Dict[str, Any]:
    """
    Get topic trends over time.

    Args:
        period: Time period granularity ('weekly' or 'monthly').

    Returns:
        Dict with trend data grouped by topic and period.
    """
    valid_periods = {"weekly", "monthly"}
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    try:
        from kb.web.dependencies import get_topic_query

        tq = get_topic_query()
        trend = tq.get_topic_trend(period=period)
        return {"period": period, "trend": trend}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Topic trend query failed: {str(e)}",
        )


@router.post("/topics/rebuild")
async def rebuild_topics() -> Dict[str, Any]:
    """
    Trigger a full topic clustering rebuild.

    Runs HDBSCAN clustering on all document embeddings and
    generates LLM topic labels. Returns immediately if already running.
    """
    if _rebuild_state["running"]:
        return {"status": "already_running", "message": "Topic rebuild is already in progress."}

    _rebuild_state["running"] = True
    _rebuild_state["last_result"] = None
    _rebuild_state["last_error"] = None

    try:
        result = await asyncio.to_thread(_run_rebuild)
        _rebuild_state["last_result"] = result
        return {"status": "success", "result": result}
    except Exception as e:
        _rebuild_state["last_error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Topic rebuild failed: {str(e)}")
    finally:
        _rebuild_state["running"] = False


def _run_rebuild() -> Dict[str, Any]:
    """Run topic clustering in a thread (blocking)."""
    from kb.processors.topic_clusterer import TopicClusterer

    clusterer = TopicClusterer.from_config()
    return clusterer.cluster_all()


@router.get("/topics/rebuild/status")
async def rebuild_status() -> Dict[str, Any]:
    """Get the current state of topic rebuild."""
    return {
        "running": _rebuild_state["running"],
        "last_result": _rebuild_state["last_result"],
        "last_error": _rebuild_state["last_error"],
    }
