"""
Items routes for Knowledge Base Web API.

Provides CRUD endpoints for knowledge items.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _parse_yaml_front_matter(content: str) -> Dict[str, Any]:
    """
    Parse YAML front matter from markdown content.
    
    Args:
        content: Markdown file content
        
    Returns:
        Dict containing the parsed YAML metadata
    """
    # Match YAML front matter: ---\n...\n---
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return {}
    
    yaml_content = match.group(1)
    metadata = {}
    
    # Simple YAML parsing for basic types
    for line in yaml_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Handle list items (indentation based)
        if line.startswith('- '):
            continue
            
        # Parse key: value pairs
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Try to parse as integer
            if value.isdigit():
                value = int(value)
            
            metadata[key] = value
    
    return metadata


def _read_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Read metadata from a markdown file's YAML front matter.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dict containing the file metadata
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {}
        
        content = path.read_text(encoding='utf-8')
        return _parse_yaml_front_matter(content)
    except Exception:
        return {}


class ItemUpdate(BaseModel):
    """Request model for updating a knowledge item."""
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    user_notes: Optional[str] = None


class ItemResponse(BaseModel):
    """Response model for a knowledge item."""
    id: str
    title: Optional[str] = None
    content_type: Optional[str] = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    summary: Optional[str] = None
    word_count: Optional[int] = None
    file_path: Optional[str] = None
    tags: List[str] = []
    user_notes: Optional[str] = None


@router.get("/items")
async def list_items(
    limit: int = 20,
    offset: int = 0,
    content_type: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "collected_at",
    sort_order: Optional[str] = "desc"
) -> List[Dict[str, Any]]:
    """
    List knowledge items with pagination and filtering.
    
    Args:
        limit: Maximum number of items to return (default: 20)
        offset: Number of items to skip (default: 0)
        content_type: Filter by content type (optional)
        tag: Filter by tag name (optional)
        search: Full-text search in title, source, summary (optional)
        sort_by: Sort field (default: collected_at)
        sort_order: Sort direction - asc or desc (default: desc)
    
    Returns:
        List of knowledge items with their tags.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        items = storage.list_knowledge(
            content_type=content_type,
            limit=limit,
            offset=offset,
            tag=tag,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Fetch tags for each item
        for item in items:
            item["tags"] = storage.get_tags(item["id"])
            
            # For notes, read and include the full content
            if item.get("content_type") == "note" and item.get("file_path"):
                try:
                    path = Path(item["file_path"])
                    if path.exists():
                        file_content = path.read_text(encoding="utf-8")
                        # Extract content after YAML front matter
                        content = file_content
                        front_matter_match = re.match(r"^---\s*\n.*?\n---\s*\n", file_content, re.DOTALL)
                        if front_matter_match:
                            content = file_content[front_matter_match.end():]
                        item["content"] = content.strip()
                except Exception:
                    pass
        
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list items: {str(e)}")


@router.get("/items/{item_id}")
async def get_item(item_id: str, background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
    """
    Get a specific knowledge item.
    
    Args:
        item_id: The unique identifier of the item.
    
    Returns:
        The knowledge item with its tags, chunks, and full metadata from file.
        
    Raises:
        404: Item not found.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        item = storage.get_knowledge(item_id)
        
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
        
        # Fetch tags and chunks
        item["tags"] = storage.get_tags(item_id)
        item["chunks"] = storage.get_chunks(item_id)
        
        # Read full metadata from file if file_path exists
        if item.get("file_path"):
            file_metadata = _read_file_metadata(item["file_path"])
            # Merge file metadata with database fields (file takes precedence for extra fields)
            for key, value in file_metadata.items():
                if key not in item or item[key] is None or item[key] == "":
                    item[key] = value

        # Record view event in background
        if background_tasks:
            def _track_view():
                try:
                    from kb.web.dependencies import get_reading_history
                    rh = get_reading_history()
                    rh.record_view(item_id)
                except Exception:
                    pass
            background_tasks.add_task(_track_view)

        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get item: {str(e)}")


@router.put("/items/{item_id}")
async def update_item(item_id: str, update: ItemUpdate) -> Dict[str, Any]:
    """
    Update a knowledge item.
    
    Args:
        item_id: The unique identifier of the item.
        update: Fields to update (title, summary, tags).
    
    Returns:
        The updated knowledge item.
        
    Raises:
        404: Item not found.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        
        # Check if item exists
        item = storage.get_knowledge(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
        
        # Update fields if provided
        update_fields = {}
        if update.title is not None:
            update_fields["title"] = update.title
        if update.summary is not None:
            update_fields["summary"] = update.summary
        if update.user_notes is not None:
            update_fields["user_notes"] = update.user_notes
        
        if update_fields:
            success = storage.update_knowledge(item_id, **update_fields)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update item")
        
        # Update tags if provided
        if update.tags is not None:
            # Get current tags and remove them
            current_tags = storage.get_tags(item_id)
            for tag in current_tags:
                # We need to manually remove tags (there's no direct method)
                # For now, we'll just add the new tags
                pass
            
            # Add new tags
            storage.add_tags(item_id, update.tags)
        
        # Return updated item
        updated_item = storage.get_knowledge(item_id)
        updated_item["tags"] = storage.get_tags(item_id)
        
        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update item: {str(e)}")


@router.get("/items/{item_id}/preview")
async def preview_item(item_id: str) -> Dict[str, str]:
    """
    Get the markdown content preview of a knowledge item.
    
    Args:
        item_id: The unique identifier of the item.
    
    Returns:
        Dict with content and file_path of the markdown file.
        
    Raises:
        404: Item not found or file doesn't exist.
    """
    try:
        from kb.web.dependencies import get_sqlite_storage
        
        storage = get_sqlite_storage()
        
        # Get the item to find its file_path
        item = storage.get_knowledge(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
        
        file_path = item.get("file_path")
        content = None
        
        # If file_path exists, try to read from file
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                # File doesn't exist, fall back to summary
                pass
            except UnicodeDecodeError:
                # Try with different encoding if UTF-8 fails
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                except Exception:
                    # Failed to read file, fall back to summary
                    pass
        
        # Parse and reformat YAML front matter for better preview display
        if content:
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if front_matter_match:
                yaml_text = front_matter_match.group(1)
                body = content[front_matter_match.end():]
                
                # Parse YAML front matter into formatted metadata lines
                meta_lines = []
                skip_fields = {'status'}
                current_key = None
                list_items = []
                
                for line in yaml_text.split('\n'):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith('- ') and current_key:
                        # List item for current key
                        list_items.append(stripped[2:].strip())
                    else:
                        # Flush previous list items
                        if current_key and list_items:
                            meta_lines.append(f"**{current_key}:** {', '.join(list_items)}")
                            list_items = []
                            current_key = None
                        
                        if ':' in stripped:
                            key, _, value = stripped.partition(':')
                            key = key.strip()
                            value = value.strip()
                            
                            if key.lower() in skip_fields:
                                current_key = None
                                continue
                            
                            # Remove quotes from value
                            if value and ((value.startswith('"') and value.endswith('"')) or 
                                          (value.startswith("'") and value.endswith("'"))):
                                value = value[1:-1]
                            
                            if value:
                                # Capitalize the field name nicely
                                display_key = key.replace('_', ' ').title()
                                meta_lines.append(f"**{display_key}:** {value}")
                            else:
                                # This might be a list field (value on next lines)
                                current_key = key.replace('_', ' ').title()
                
                # Flush any remaining list items
                if current_key and list_items:
                    meta_lines.append(f"**{current_key}:** {', '.join(list_items)}")
                
                # Rebuild content with formatted metadata
                if meta_lines:
                    content = '\n\n'.join(meta_lines) + '\n\n---\n\n' + body.lstrip()
                else:
                    content = body.lstrip()
        
        # If no content from file, use summary as fallback
        if content is None:
            summary = item.get("summary", "")
            title = item.get("title", "Untitled")
            source = item.get("source", "")
            content_type = item.get("content_type", "unknown")
            
            if summary:
                # Build a simple markdown representation from the summary
                content_parts = [f"# {title}", ""]
                
                # Add metadata section
                content_parts.append(f"**Type:** {content_type}")
                if source:
                    content_parts.append(f"**Source:** {source}")
                content_parts.append("")
                
                # Add content
                content_parts.append("## Content")
                content_parts.append("")
                content_parts.append(summary)
                
                content = "\n".join(content_parts)
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No preview content available for this item. The file may have been deleted or the item was created without content."
                )
        
        return {
            "content": content,
            "file_path": file_path or ""
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview item: {str(e)}")


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, delete_file: bool = False) -> Dict[str, str]:
    """
    Delete a knowledge item.
    
    Args:
        item_id: The unique identifier of the item.
        delete_file: Whether to also delete the associated file. Defaults to False.
    
    Returns:
        Success message.
        
    Raises:
        404: Item not found.
    """
    try:
        import os
        from kb.web.dependencies import get_sqlite_storage, get_chroma_storage
        
        storage = get_sqlite_storage()
        
        # Check if item exists
        item = storage.get_knowledge(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")
        
        # Get file path before deletion if delete_file is requested
        file_path = item.get("file_path") if delete_file else None
        
        # Get chunks to delete from vector storage
        chunks = storage.get_chunks(item_id)
        chunk_ids = [chunk["id"] for chunk in chunks if chunk.get("id")]
        
        # Delete from SQLite (CASCADE will handle chunks and tags)
        success = storage.delete_knowledge(item_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete item from SQLite")
        
        # Delete from ChromaDB if there are chunks
        if chunk_ids:
            try:
                chroma = get_chroma_storage()
                chroma.delete(ids=chunk_ids)
            except Exception as e:
                # Log but don't fail - SQLite deletion was successful
                pass
        
        # Delete associated file if requested and file exists
        if delete_file and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log but don't fail - metadata deletion was successful
                pass
        
        return {"message": f"Item {item_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")
