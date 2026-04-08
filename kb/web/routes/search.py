"""
Search routes for Knowledge Base Web API.

Provides endpoints for keyword search, semantic search, and RAG queries.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str
    tags: Optional[List[str]] = None
    top_k: int = 5


class SemanticSearchResponse(BaseModel):
    """Response model for semantic search results."""
    results: List[Dict[str, Any]]
    query: str


class RAGRequest(BaseModel):
    """Request model for RAG query."""
    question: str
    tags: Optional[List[str]] = None
    top_k: int = 5


class RAGResponse(BaseModel):
    """Response model for RAG query results."""
    answer: str
    sources: List[Dict[str, Any]]
    question: str


@router.get("/search")
async def keyword_search(
    q: str,
    content_type: Optional[str] = None,
    limit: int = 20,
    background_tasks: BackgroundTasks = None,
) -> Dict[str, Any]:
    """
    Keyword search across knowledge base.
    
    Uses full-text search (FTS5) for efficient keyword matching.
    
    Args:
        q: Search query string.
        content_type: Filter by content type (optional).
        limit: Maximum number of results (default: 20).
    
    Returns:
        Dict containing search results.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query string is required")
    
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        
        # Use full-text search
        results = storage.search_fulltext(query=q, limit=limit)
        
        # Filter by content type if specified
        if content_type:
            results = [r for r in results if r.get("content_type") == content_type]
        
        # Fetch tags for each result
        for item in results:
            item["tags"] = storage.get_tags(item["id"])

        # Track search event
        if background_tasks:
            def _track_search():
                try:
                    from kb.web.dependencies import get_reading_history
                    get_reading_history().record_search(q)
                except Exception:
                    pass
            background_tasks.add_task(_track_search)

        return {
            "query": q,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/semantic")
async def semantic_search(request: SemanticSearchRequest, background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
    """
    Semantic similarity search.
    
    Uses embedding vectors for semantic similarity matching.
    Requires embedding API to be configured.
    
    Args:
        request: SemanticSearchRequest with query, optional tags, and top_k.
    
    Returns:
        Dict containing semantic search results with similarity scores.
        
    Raises:
        503: Embedding service not configured.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string is required")
    
    try:
        from kb.web.dependencies import get_semantic_search
        
        search = get_semantic_search()
        results = search.search(
            query=request.query,
            tags=request.tags,
            top_k=request.top_k
        )
        
        # Convert SearchResult objects to dicts
        results_dicts = [result.to_dict() for result in results]

        # Track search event
        if background_tasks:
            def _track_semantic():
                try:
                    from kb.web.dependencies import get_reading_history
                    get_reading_history().record_search(request.query)
                except Exception:
                    pass
            background_tasks.add_task(_track_semantic)

        return {
            "query": request.query,
            "results": results_dicts,
            "total": len(results_dicts)
        }
    except ValueError as e:
        # Configuration error (e.g., no API key)
        raise HTTPException(
            status_code=503,
            detail=f"Semantic search service not available: {str(e)}. "
                   "Please configure embedding API in config.yaml"
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Required dependencies not installed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.post("/rag")
async def rag_query(request: RAGRequest, background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
    """
    RAG-based question answering.
    
    Uses retrieval-augmented generation to answer questions
    based on knowledge base content.
    Requires both embedding and LLM APIs to be configured.
    
    Args:
        request: RAGRequest with question, optional tags, and top_k.
    
    Returns:
        Dict containing answer and source references.
        
    Raises:
        503: RAG service not configured.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        from kb.web.dependencies import get_rag_query
        
        rag = get_rag_query()
        result = rag.query_with_fallback(
            question=request.question,
            tags=request.tags,
            top_k=request.top_k
        )

        # Track RAG query event
        if background_tasks:
            def _track_rag():
                try:
                    from kb.web.dependencies import get_reading_history
                    get_reading_history().record_rag_query(request.question)
                except Exception:
                    pass
            background_tasks.add_task(_track_rag)

        return result.to_dict()
    except ValueError as e:
        # Configuration error (e.g., no API key)
        raise HTTPException(
            status_code=503,
            detail=f"RAG service not available: {str(e)}. "
                   "Please configure embedding and LLM APIs in config.yaml"
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Required dependencies not installed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")
