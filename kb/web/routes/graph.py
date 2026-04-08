"""
Graph routes for Knowledge Base Web API.

Provides endpoints for knowledge graph queries, entity details,
and document relationship discovery.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/graph")
async def get_graph(
    entity_type: Optional[str] = None,
    depth: int = 2,
    limit: int = 100,
    entity_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get knowledge graph data for visualization.

    Returns nodes (entities) and edges (relations) suitable for
    rendering with ECharts force-directed graph.

    Args:
        entity_type: Filter by entity type (person/concept/tool/project/organization).
        depth: Relationship traversal depth (default 2, used with entity_id).
        limit: Maximum number of nodes (default 100).
        entity_id: Center graph on this entity (optional).

    Returns:
        Dict with nodes, edges, and stats.
    """
    valid_types = {"person", "concept", "tool", "project", "organization"}
    if entity_type and entity_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type. Must be one of: {', '.join(valid_types)}",
        )
    if depth < 1 or depth > 5:
        raise HTTPException(status_code=400, detail="depth must be between 1 and 5")
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")

    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        return gq.get_graph(
            entity_type=entity_type,
            depth=depth,
            limit=limit,
            entity_id=entity_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")


@router.get("/graph/search")
async def search_entities(q: str, limit: int = 20) -> Dict[str, Any]:
    """
    Search entities by name.

    Args:
        q: Search query string.
        limit: Maximum number of results (default 20).

    Returns:
        Dict with matching entities.
    """
    if not q or len(q.strip()) == 0:
        return {"results": []}
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        results = gq.search_entities(q=q.strip(), limit=limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Entity search failed: {str(e)}"
        )


@router.get("/graph/stats")
async def get_graph_stats() -> Dict[str, Any]:
    """
    Get knowledge graph statistics.

    Returns:
        Dict with entity counts, relation counts, type distributions.
    """
    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        return gq.get_graph_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Graph stats query failed: {str(e)}"
        )


@router.get("/graph/entity/{entity_id}")
async def get_entity(entity_id: int) -> Dict[str, Any]:
    """
    Get entity details including mentions and relations.

    Args:
        entity_id: Entity ID.

    Returns:
        Entity details with mentions and relations.
    """
    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        entity = gq.get_entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity query failed: {str(e)}")


@router.get("/knowledge/{knowledge_id}/entities")
async def get_document_entities(knowledge_id: str) -> Dict[str, Any]:
    """
    Get entities and relations for a specific document.

    Args:
        knowledge_id: Document ID.

    Returns:
        Dict with nodes and edges for the document's entity subgraph.
    """
    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        return gq.get_document_entities(knowledge_id=knowledge_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document entities query failed: {str(e)}",
        )


@router.get("/knowledge/{knowledge_id}/related")
async def get_related_documents(
    knowledge_id: str,
    limit: int = 10,
    relation_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get documents related to the specified document.

    Args:
        knowledge_id: Source document ID.
        limit: Maximum number of related documents (default 10).
        relation_type: Filter by relation type (embedding_similarity/shared_entity).

    Returns:
        Dict with list of related documents.
    """
    valid_relation_types = {"embedding_similarity", "shared_entity"}
    if relation_type and relation_type not in valid_relation_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation_type. Must be one of: {', '.join(valid_relation_types)}",
        )

    try:
        from kb.web.dependencies import get_graph_query

        gq = get_graph_query()
        relations = gq.get_related_documents(
            knowledge_id=knowledge_id,
            limit=limit,
            relation_type=relation_type,
        )
        return {"knowledge_id": knowledge_id, "relations": relations}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Related documents query failed: {str(e)}"
        )
