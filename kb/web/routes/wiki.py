"""
Wiki routes for Knowledge Base Web API.

Provides endpoints for browsing and searching wiki articles,
including topic articles and entity cards.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _read_article_content(file_path: str, wiki_dir: Path) -> Optional[str]:
    """
    Read article content from disk, stripping YAML front matter if present.

    Args:
        file_path: Relative path to the article file (from wiki_articles table)
        wiki_dir: Base wiki directory path

    Returns:
        Article content as string (with front matter stripped), or None if file not found
    """
    if not file_path:
        return None

    # file_path from database is relative to wiki directory
    full_path = wiki_dir / file_path

    try:
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            return _strip_yaml_front_matter(content)
    except Exception:
        return None

    return None


def _strip_yaml_front_matter(content: str) -> str:
    """
    Strip YAML front matter from markdown content.

    YAML front matter is delimited by '---' at the start and end:
    ---
    key: value
    ---

    Args:
        content: Raw file content potentially containing YAML front matter

    Returns:
        Content with YAML front matter removed
    """
    if not content:
        return content

    lines = content.split("\n")

    # Check if content starts with '---'
    if lines and lines[0].strip() == "---":
        # Find the closing '---'
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                # Return everything after the closing '---', skipping the blank line if present
                remaining_lines = lines[i + 1:]
                # Strip leading empty lines
                while remaining_lines and remaining_lines[0].strip() == "":
                    remaining_lines.pop(0)
                return "\n".join(remaining_lines)

    # No front matter found, return original content
    return content


@router.get("/wiki/tree")
async def get_wiki_tree() -> Dict[str, Any]:
    """
    Get the full two-level tree structure for the wiki sidebar/index.

    Returns:
        Dict with topics list (each containing categories) and stats
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        conn = storage.conn
        cursor = conn.cursor()

        # Get all topic clusters that have wiki categories
        cursor.execute("""
            SELECT DISTINCT tc.id, tc.label, tc.description
            FROM topic_clusters tc
            WHERE tc.id IN (SELECT DISTINCT topic_id FROM wiki_categories)
            ORDER BY tc.document_count DESC
        """)
        topics_rows = cursor.fetchall()

        topics = []
        for topic_row in topics_rows:
            topic_id = topic_row[0]
            topic_label = topic_row[1]
            topic_description = topic_row[2]

            # Get categories for this topic
            categories = storage.list_wiki_categories(topic_id=topic_id)

            # Build category list with article count, filter out empty categories
            category_list = []
            for cat in categories:
                # Count articles in this category
                article_count = cat.get('article_count', 0)
                if article_count > 0:
                    category_list.append({
                        "category_id": cat['category_id'],
                        "name": cat['name'],
                        "description": cat.get('description'),
                        "article_count": article_count
                    })

        # Only include topics that have categories with articles
            if category_list:
                topics.append({
                    "topic_id": topic_id,
                    "label": topic_label,
                    "description": topic_description,
                    "categories": category_list
                })

        # Get stats
        stats = storage.get_wiki_stats()

        cursor.close()

        return {
            "topics": topics,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wiki tree: {str(e)}")


@router.get("/wiki/categories/{category_id}/articles")
async def get_category_articles(category_id: str) -> Dict[str, Any]:
    """
    Get articles belonging to a specific category.

    Args:
        category_id: The unique identifier of the category.

    Returns:
        Dict with category info and articles list.

    Raises:
        404: Category not found.
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()

        # Special handling for uncategorized articles
        if category_id == "__uncategorized__":
            conn = storage.conn
            cursor = conn.cursor()
            cursor.execute("""
                SELECT article_id, article_type, topic_id, title, file_path,
                       source_doc_ids, entity_refs, compiled_at, version, word_count, category_id
                FROM wiki_articles
                WHERE category_id IS NULL
                ORDER BY compiled_at DESC
                LIMIT 500
            """)
            import json
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    "article_id": row[0],
                    "article_type": row[1],
                    "topic_id": row[2],
                    "title": row[3],
                    "file_path": row[4],
                    "source_doc_ids": json.loads(row[5] or "[]"),
                    "entity_refs": json.loads(row[6] or "[]"),
                    "compiled_at": row[7],
                    "version": row[8],
                    "word_count": row[9],
                    "category_id": row[10]
                })
            cursor.close()

            return {
                "category": {
                    "category_id": "__uncategorized__",
                    "name": "Uncategorized Articles",
                    "description": "Articles compiled before category system was implemented",
                    "topic_id": "__uncategorized__",
                    "topic_label": "Uncategorized",
                    "article_count": len(articles)
                },
                "articles": articles,
                "total": len(articles)
            }

        # Get category info
        category = storage.get_wiki_category(category_id)
        if category is None:
            raise HTTPException(status_code=404, detail=f"Category not found: {category_id}")

        # Get articles for this category
        articles = storage.list_wiki_articles(category_id=category_id, limit=500, offset=0)

        # Get topic label for breadcrumb
        topic_label = None
        topic_id = category.get('topic_id')
        if topic_id:
            conn = storage.conn
            cursor = conn.cursor()
            cursor.execute("SELECT label FROM topic_clusters WHERE id = ?", (topic_id,))
            row = cursor.fetchone()
            if row:
                topic_label = row[0]
            cursor.close()

        return {
            "category": {
                "category_id": category['category_id'],
                "name": category['name'],
                "description": category.get('description'),
                "topic_id": topic_id,
                "topic_label": topic_label,
                "article_count": len(articles)
            },
            "articles": articles,
            "total": len(articles)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category articles: {str(e)}")


@router.get("/wiki/topics/{topic_id}/articles")
async def get_topic_articles(topic_id: str) -> Dict[str, Any]:
    """
    Get all wiki articles for a given topic (across all its categories).

    Args:
        topic_id: The topic ID (e.g., "1" or "cluster_001")

    Returns:
        Dict with topic info and list of articles
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        conn = storage.conn
        cursor = conn.cursor()

        # Get topic label and numeric ID
        topic_label = None
        topic_id_numeric = None
        try:
            # Try to parse as integer first
            topic_id_numeric = int(topic_id)
            cursor.execute("SELECT label FROM topic_clusters WHERE id = ?", (topic_id_numeric,))
            row = cursor.fetchone()
            if row:
                topic_label = row[0]
        except ValueError:
            # If not an integer, it might already be in cluster_xxx format
            # Extract numeric part for label lookup
            if topic_id.startswith("cluster_"):
                try:
                    topic_id_numeric = int(topic_id.split("_")[1])
                    cursor.execute("SELECT label FROM topic_clusters WHERE id = ?", (topic_id_numeric,))
                    row = cursor.fetchone()
                    if row:
                        topic_label = row[0]
                except (ValueError, IndexError):
                    pass

        # Convert numeric topic_id to cluster_xxx format for wiki_articles lookup
        # wiki_articles stores topic_id as "cluster_001", "cluster_002", etc.
        if topic_id_numeric is not None:
            topic_id_for_query = f"cluster_{topic_id_numeric:03d}"
        else:
            topic_id_for_query = topic_id

        # Get all articles for this topic with category names
        cursor.execute("""
            SELECT wa.article_id, wa.article_type, wa.topic_id, wa.title, wa.file_path,
                   wa.source_doc_ids, wa.entity_refs, wa.compiled_at, wa.version, wa.word_count, wa.category_id,
                   wc.name as category_name
            FROM wiki_articles wa
            LEFT JOIN wiki_categories wc ON wa.category_id = wc.category_id
            WHERE wa.topic_id = ?
            ORDER BY wa.compiled_at DESC
        """, (topic_id_for_query,))

        import json
        articles = []
        for row in cursor.fetchall():
            articles.append({
                "article_id": row[0],
                "article_type": row[1],
                "topic_id": row[2],
                "title": row[3],
                "file_path": row[4],
                "source_doc_ids": json.loads(row[5] or "[]"),
                "entity_refs": json.loads(row[6] or "[]"),
                "compiled_at": row[7],
                "version": row[8],
                "word_count": row[9],
                "category_id": row[10],
                "category_name": row[11]
            })
        cursor.close()

        return {
            "topic": {
                "topic_id": topic_id,
                "topic_label": topic_label or topic_id,
                "article_count": len(articles)
            },
            "articles": articles,
            "total": len(articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topic articles: {str(e)}")


@router.get("/wiki/articles")
async def list_wiki_articles(
    article_type: Optional[str] = Query(None, description="Filter by type: topic or entity"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List all wiki articles, optionally filtered by type.

    Args:
        article_type: Filter by "topic" or "entity", optional
        limit: Maximum number of articles to return (default: 100, max: 500)
        offset: Offset for pagination (default: 0)

    Returns:
        Dict with items list and total count
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        articles = storage.list_wiki_articles(article_type=article_type, limit=limit, offset=offset)

        # Get total count (simple approach - get all and count)
        # For large datasets, consider adding a count method to storage
        all_articles = storage.list_wiki_articles(article_type=article_type, limit=10000, offset=0)
        total = len(all_articles)

        return {"items": articles, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list wiki articles: {str(e)}")


@router.get("/wiki/articles/{article_id}")
async def get_wiki_article(article_id: str) -> Dict[str, Any]:
    """
    Get a single wiki article with full content.

    Args:
        article_id: The unique identifier of the article.

    Returns:
        Article metadata with content field containing the full markdown.
        Enriched with category_name, topic_label, source_documents, and entity_details.

    Raises:
        404: Article not found.
    """
    from kb.web.dependencies import get_sqlite_storage, get_config

    try:
        storage = get_sqlite_storage()
        article = storage.get_wiki_article(article_id)

        if article is None:
            raise HTTPException(status_code=404, detail=f"Article not found: {article_id}")

        # Read the actual markdown file content from disk
        config = get_config()
        wiki_dir = config.get_wiki_dir()

        content = _read_article_content(article.get("file_path", ""), wiki_dir)
        if content:
            article["content"] = content
        else:
            article["content"] = None

        # Enrich with breadcrumb navigation info
        conn = storage.conn
        cursor = conn.cursor()

        # Get category_name and topic_label for breadcrumb
        category_name = None
        topic_label = None
        category_id = article.get("category_id")
        if category_id:
            cursor.execute(
                "SELECT name, topic_id FROM wiki_categories WHERE category_id = ?",
                (category_id,)
            )
            cat_row = cursor.fetchone()
            if cat_row:
                category_name = cat_row[0]
                topic_id = cat_row[1]
                if topic_id:
                    cursor.execute(
                        "SELECT label FROM topic_clusters WHERE id = ?",
                        (topic_id,)
                    )
                    topic_row = cursor.fetchone()
                    if topic_row:
                        topic_label = topic_row[0]

        article["category_name"] = category_name
        article["topic_label"] = topic_label

        # Enrich source_documents with titles and content types
        source_documents = []
        if article.get("source_doc_ids"):
            for doc_id in article["source_doc_ids"]:
                cursor.execute(
                    "SELECT id, title, content_type FROM knowledge WHERE id = ?",
                    (doc_id,)
                )
                row = cursor.fetchone()
                if row:
                    source_documents.append({"id": row[0], "title": row[1], "source_type": row[2]})
        article["source_documents"] = source_documents

        # Enrich entity_details with names and types
        entity_details = []
        if article.get("entity_refs"):
            for slug in article["entity_refs"]:
                cursor.execute(
                    "SELECT id, name, type FROM entities WHERE id = ? OR name = ?",
                    (slug, slug)
                )
                row = cursor.fetchone()
                if row:
                    entity_details.append({
                        "entity_id": row[0],
                        "name": row[1],
                        "entity_type": row[2],
                        "slug": slug
                    })
        article["entity_details"] = entity_details

        cursor.close()

        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wiki article: {str(e)}")


@router.get("/wiki/entities")
async def list_wiki_entities(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List all entity cards.

    Args:
        limit: Maximum number of entities to return (default: 100, max: 500)
        offset: Offset for pagination (default: 0)

    Returns:
        Dict with items list and total count
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        entities = storage.list_wiki_articles(article_type="entity", limit=limit, offset=offset)

        # Get total count
        all_entities = storage.list_wiki_articles(article_type="entity", limit=10000, offset=0)
        total = len(all_entities)

        return {"items": entities, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list wiki entities: {str(e)}")


@router.get("/wiki/entities/{entity_id}")
async def get_wiki_entity(entity_id: str) -> Dict[str, Any]:
    """
    Get a single entity card with full content.

    Args:
        entity_id: The unique identifier of the entity.

    Returns:
        Entity metadata with content field containing the full markdown.

    Raises:
        404: Entity not found.
    """
    from kb.web.dependencies import get_sqlite_storage, get_config

    try:
        storage = get_sqlite_storage()
        entity = storage.get_wiki_article(entity_id)

        if entity is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Verify it's an entity type
        if entity.get("article_type") != "entity":
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Read the actual markdown file content from disk
        config = get_config()
        wiki_dir = config.get_wiki_dir()

        content = _read_article_content(entity.get("file_path", ""), wiki_dir)
        if content:
            entity["content"] = content
        else:
            entity["content"] = None

        return entity
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wiki entity: {str(e)}")


@router.get("/wiki/stats")
async def get_wiki_stats() -> Dict[str, Any]:
    """
    Get wiki statistics.

    Returns:
        Dict with topic_count, entity_count, total_count, last_compiled, total_words
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        stats = storage.get_wiki_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wiki stats: {str(e)}")


@router.get("/wiki/search")
async def search_wiki(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Search wiki articles by title.

    Args:
        q: Search query string (required, min length: 1)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        Dict with items list and total count
    """
    from kb.web.dependencies import get_sqlite_storage

    try:
        storage = get_sqlite_storage()
        articles = storage.search_wiki_articles(query=q, limit=limit)

        return {"items": articles, "total": len(articles), "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search wiki: {str(e)}")
