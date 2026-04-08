"""
Tags routes for Knowledge Base Web API.

Provides endpoints for tag management operations.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MergeTagsRequest(BaseModel):
    """Request model for merging tags."""
    source_tag: str
    target_tag: str


class TagResponse(BaseModel):
    """Response model for a tag."""
    name: str
    count: int


@router.get("/tags")
async def list_tags(
    limit: int = 100,
    order_by: str = "count"
) -> List[Dict[str, Any]]:
    """
    List all tags.
    
    Args:
        limit: Maximum number of tags to return (default: 100).
        order_by: Sort order - 'count' (default) or 'name'.
    
    Returns:
        List of tags with their counts.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        tags = storage.list_tags(order_by=order_by, limit=limit)
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tags: {str(e)}")


@router.get("/tags/{tag_name}/items")
async def get_tag_items(
    tag_name: str,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get items with a specific tag.
    
    Args:
        tag_name: The tag name to search for.
        limit: Maximum number of items to return (default: 50).
    
    Returns:
        Dict containing the tag name and list of items.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        items = storage.find_by_tags(tags=[tag_name], match_all=True, limit=limit)
        
        # Fetch all tags for each item
        for item in items:
            item["tags"] = storage.get_tags(item["id"])
        
        return {
            "tag": tag_name,
            "items": items,
            "total": len(items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tag items: {str(e)}")


@router.post("/tags/merge")
async def merge_tags(request: MergeTagsRequest) -> Dict[str, str]:
    """
    Merge two tags.
    
    Merges source_tag into target_tag. All items with source_tag
    will be updated to have target_tag instead, and source_tag
    will be deleted.
    
    Args:
        request: MergeTagsRequest with source_tag and target_tag.
    
    Returns:
        Success message.
        
    Raises:
        400: Source and target tags are the same.
        404: Source tag not found.
    """
    if request.source_tag == request.target_tag:
        raise HTTPException(
            status_code=400,
            detail="Source and target tags cannot be the same"
        )
    
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        success = storage.merge_tags(
            source_tag=request.source_tag,
            target_tag=request.target_tag
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Source tag not found: {request.source_tag}"
            )
        
        return {
            "message": f"Successfully merged '{request.source_tag}' into '{request.target_tag}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge tags: {str(e)}")


@router.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str) -> Dict[str, str]:
    """
    Delete a tag.
    
    Removes the tag from all items and deletes it from the system.
    
    Args:
        tag_name: The tag name to delete.
    
    Returns:
        Success message.
        
    Raises:
        404: Tag not found.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        success = storage.delete_tag(tag_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Tag not found: {tag_name}")
        
        return {"message": f"Tag '{tag_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tag: {str(e)}")
