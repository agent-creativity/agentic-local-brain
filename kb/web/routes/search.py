"""
Search routes for Knowledge Base Web API.

Provides endpoints for keyword search, semantic search, and RAG queries.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

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


class RAGChatRequest(BaseModel):
    """Request model for enhanced RAG chat with conversation support."""
    question: str
    session_id: Optional[str] = None
    tags: Optional[List[str]] = None
    top_k: int = 5
    options: Dict[str, Any] = Field(default_factory=lambda: {
        "use_graph": True,
        "use_topics": True,
        "use_reranking": True
    })


class RAGSuggestRequest(BaseModel):
    """Request model for RAG query suggestions."""
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


# =============================================================================
# Enhanced RAG Chat Endpoints (v0.7)
# =============================================================================

@router.post("/rag/chat")
async def rag_chat(request: RAGChatRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Enhanced RAG with multi-turn conversation support.

    Uses the full retrieval pipeline with query expansion, hybrid retrieval,
    reranking, context enrichment, and conversation history.

    Args:
        request: RAGChatRequest with question, optional session_id, tags, top_k, and options.

    Returns:
        Dict containing EnhancedRAGResult fields (answer, sources, confidence, etc.)

    Raises:
        400: Empty question
        503: Pipeline unavailable
        500: Pipeline execution failed
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail={"error": "Question is required"})

    try:
        from kb.web.dependencies import get_retrieval_pipeline, get_reading_history

        pipeline = get_retrieval_pipeline()

        # Run the enhanced pipeline
        result = pipeline.run(
            question=request.question,
            session_id=request.session_id,
            tags=request.tags,
            top_k=request.top_k,
            options=request.options,
        )

        # Record in reading history (background task)
        if background_tasks:
            def _track_rag_chat():
                try:
                    get_reading_history().record_rag_query(request.question)
                except Exception:
                    pass
            background_tasks.add_task(_track_rag_chat)

        return result.to_dict()

    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": f"Pipeline unavailable: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"RAG chat failed: {str(e)}"}
        )


@router.get("/rag/conversations")
async def list_conversations(limit: int = 20) -> Dict[str, Any]:
    """
    List all conversation sessions.

    Args:
        limit: Maximum number of sessions to return (default: 20).

    Returns:
        Dict with sessions list containing session_id, created_at, turn_count, last_question.
    """
    try:
        from kb.web.dependencies import get_conversation_manager

        conversation_manager = get_conversation_manager()
        sessions = conversation_manager.list_sessions(limit=limit)

        return {"sessions": sessions, "total": len(sessions)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to list conversations: {str(e)}"}
        )


@router.get("/rag/conversations/{session_id}")
async def get_conversation(session_id: str) -> Dict[str, Any]:
    """
    Get full conversation by session ID.

    Args:
        session_id: The conversation session ID.

    Returns:
        Dict with session details including all turns.

    Raises:
        404: Session not found
    """
    try:
        from kb.web.dependencies import get_conversation_manager

        conversation_manager = get_conversation_manager()
        session = conversation_manager.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Conversation session not found: {session_id}"}
            )

        return session.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to get conversation: {str(e)}"}
        )


@router.delete("/rag/conversations/{session_id}")
async def delete_conversation(session_id: str) -> Dict[str, Any]:
    """
    Delete a conversation session.

    Args:
        session_id: The conversation session ID to delete.

    Returns:
        Dict with success status.

    Raises:
        404: Session not found
    """
    try:
        from kb.web.dependencies import get_conversation_manager

        conversation_manager = get_conversation_manager()
        deleted = conversation_manager.delete_session(session_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Conversation session not found: {session_id}"}
            )

        return {"success": True, "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to delete conversation: {str(e)}"}
        )


@router.delete("/rag/conversations")
async def delete_all_conversations() -> Dict[str, Any]:
    """
    Delete all conversation sessions (manual bulk cleanup).

    Returns:
        Dict with success status and count of deleted sessions.
    """
    try:
        from kb.web.dependencies import get_conversation_manager

        conversation_manager = get_conversation_manager()
        deleted_count = conversation_manager.cleanup_all()

        return {"success": True, "deleted_count": deleted_count}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to clear conversations: {str(e)}"}
        )


@router.post("/rag/suggest")
async def rag_suggest(request: RAGSuggestRequest) -> Dict[str, Any]:
    """
    Get query suggestions/refinements.

    Uses the query expander to generate alternative phrasings and
    extract entities from the question.

    Args:
        request: RAGSuggestRequest with question.

    Returns:
        Dict with suggestions (rewrites) and entities.

    Raises:
        400: Empty question
        503: Query expansion service unavailable
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail={"error": "Question is required"})

    try:
        from kb.web.dependencies import get_config
        from kb.query.query_expander import LLMQueryExpander, NoOpQueryExpander, ExpandedQuery

        config = get_config()

        # Try to create LLM query expander
        try:
            expander = LLMQueryExpander(config.to_dict())
            if not expander.llm_available:
                expander = NoOpQueryExpander()
        except Exception:
            expander = NoOpQueryExpander()

        # Expand the query
        expanded = expander.expand(request.question)

        return {
            "question": request.question,
            "suggestions": expanded.rewrites,
            "entities": expanded.entities,
            "intent": expanded.intent,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": f"Query expansion service unavailable: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to generate suggestions: {str(e)}"}
        )
