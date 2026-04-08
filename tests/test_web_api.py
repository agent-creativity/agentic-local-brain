"""
Tests for the Knowledge Base Web API.

Uses FastAPI's TestClient and mocks storage dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from kb.web.app import app

client = TestClient(app)


# ---- Test Fixtures ----

@pytest.fixture
def mock_sqlite_storage():
    """Create a mock SQLite storage instance."""
    storage = MagicMock()
    storage.get_stats.return_value = {
        "total_items": 100,
        "items_by_type": {"file": 50, "url": 30, "note": 20},
        "total_tags": 25,
        "total_chunks": 500
    }
    storage.list_knowledge.return_value = [
        {
            "id": "item1",
            "title": "Test Item 1",
            "content_type": "file",
            "source": "/path/to/file.pdf",
            "collected_at": "2024-01-01 12:00:00",
            "summary": "Test summary 1",
            "word_count": 100,
            "file_path": "/path/to/file.pdf"
        },
        {
            "id": "item2",
            "title": "Test Item 2",
            "content_type": "url",
            "source": "https://example.com",
            "collected_at": "2024-01-02 12:00:00",
            "summary": "Test summary 2",
            "word_count": 200,
            "file_path": ""
        }
    ]
    storage.get_knowledge.return_value = {
        "id": "item1",
        "title": "Test Item 1",
        "content_type": "file",
        "source": "/path/to/file.pdf",
        "collected_at": "2024-01-01 12:00:00",
        "summary": "Test summary 1",
        "word_count": 100,
        "file_path": "/path/to/file.pdf"
    }
    storage.get_tags.return_value = ["python", "tutorial"]
    storage.get_chunks.return_value = [
        {"id": "chunk1", "knowledge_id": "item1", "chunk_index": 0, "content": "Chunk 1 content"}
    ]
    storage.list_tags.return_value = [
        {"name": "python", "count": 10},
        {"name": "tutorial", "count": 5}
    ]
    storage.find_by_tags.return_value = [
        {
            "id": "item1",
            "title": "Test Item 1",
            "content_type": "file",
            "source": "/path/to/file.pdf",
            "collected_at": "2024-01-01 12:00:00"
        }
    ]
    storage.search_fulltext.return_value = [
        {
            "id": "item1",
            "title": "Test Item 1",
            "content_type": "file",
            "source": "/path/to/file.pdf",
            "collected_at": "2024-01-01 12:00:00",
            "summary": "Test summary with search term"
        }
    ]
    storage.update_knowledge.return_value = True
    storage.delete_knowledge.return_value = True
    storage.add_tags.return_value = True
    storage.merge_tags.return_value = True
    storage.delete_tag.return_value = True
    return storage


@pytest.fixture
def mock_chroma_storage():
    """Create a mock Chroma storage instance."""
    storage = MagicMock()
    storage.delete.return_value = True
    return storage


# ---- Root and Health Tests ----

def test_root_returns_html():
    """Test that root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Agentic Local Brain" in response.text


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_accessible():
    """Test that OpenAPI docs are accessible at /api/docs."""
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json():
    """Test that OpenAPI JSON schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Knowledge Base"


# ---- Dashboard Tests ----

def test_get_stats(mock_sqlite_storage):
    """Test GET /api/stats returns statistics."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 100
        assert data["items_by_type"]["file"] == 50
        assert data["total_tags"] == 25
        assert data["total_chunks"] == 500


def test_get_recent_items(mock_sqlite_storage):
    """Test GET /api/recent returns recent items with tags."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/recent?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "item1"
        assert "tags" in data[0]


# ---- Items Tests ----

def test_list_items(mock_sqlite_storage):
    """Test GET /api/items returns paginated items."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/items?limit=20&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


def test_list_items_with_content_type_filter(mock_sqlite_storage):
    """Test GET /api/items with content_type filter."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/items?content_type=file")
        assert response.status_code == 200


def test_get_item(mock_sqlite_storage):
    """Test GET /api/items/{id} returns a single item."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/items/item1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "item1"
        assert data["title"] == "Test Item 1"
        assert "tags" in data
        assert "chunks" in data


def test_get_item_not_found(mock_sqlite_storage):
    """Test GET /api/items/{id} returns 404 for missing item."""
    mock_sqlite_storage.get_knowledge.return_value = None
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/items/nonexistent")
        assert response.status_code == 404


def test_update_item(mock_sqlite_storage):
    """Test PUT /api/items/{id} updates an item."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.put(
            "/api/items/item1",
            json={"title": "Updated Title", "summary": "Updated summary"}
        )
        assert response.status_code == 200
        mock_sqlite_storage.update_knowledge.assert_called_once()


def test_update_item_with_tags(mock_sqlite_storage):
    """Test PUT /api/items/{id} updates tags."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.put(
            "/api/items/item1",
            json={"tags": ["new-tag1", "new-tag2"]}
        )
        assert response.status_code == 200
        mock_sqlite_storage.add_tags.assert_called()


def test_update_item_not_found(mock_sqlite_storage):
    """Test PUT /api/items/{id} returns 404 for missing item."""
    mock_sqlite_storage.get_knowledge.return_value = None
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.put("/api/items/nonexistent", json={"title": "New Title"})
        assert response.status_code == 404


def test_delete_item(mock_sqlite_storage, mock_chroma_storage):
    """Test DELETE /api/items/{id} deletes an item."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        with patch("kb.web.dependencies.get_chroma_storage", return_value=mock_chroma_storage):
            response = client.delete("/api/items/item1")
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]


def test_delete_item_not_found(mock_sqlite_storage):
    """Test DELETE /api/items/{id} returns 404 for missing item."""
    mock_sqlite_storage.get_knowledge.return_value = None
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.delete("/api/items/nonexistent")
        assert response.status_code == 404


# ---- Tags Tests ----

def test_list_tags(mock_sqlite_storage):
    """Test GET /api/tags returns tags."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "python"
        assert data[0]["count"] == 10


def test_list_tags_with_order(mock_sqlite_storage):
    """Test GET /api/tags with order_by parameter."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/tags?order_by=name&limit=50")
        assert response.status_code == 200


def test_get_tag_items(mock_sqlite_storage):
    """Test GET /api/tags/{name}/items returns items with tag."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/tags/python/items")
        assert response.status_code == 200
        data = response.json()
        assert data["tag"] == "python"
        assert len(data["items"]) >= 1


def test_merge_tags(mock_sqlite_storage):
    """Test POST /api/tags/merge merges tags."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.post(
            "/api/tags/merge",
            json={"source_tag": "py", "target_tag": "python"}
        )
        assert response.status_code == 200
        assert "merged" in response.json()["message"]


def test_merge_tags_same_tag(mock_sqlite_storage):
    """Test POST /api/tags/merge returns 400 for same tags."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.post(
            "/api/tags/merge",
            json={"source_tag": "python", "target_tag": "python"}
        )
        assert response.status_code == 400


def test_merge_tags_not_found(mock_sqlite_storage):
    """Test POST /api/tags/merge returns 404 for missing source tag."""
    mock_sqlite_storage.merge_tags.return_value = False
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.post(
            "/api/tags/merge",
            json={"source_tag": "nonexistent", "target_tag": "python"}
        )
        assert response.status_code == 404


def test_delete_tag(mock_sqlite_storage):
    """Test DELETE /api/tags/{name} deletes a tag."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.delete("/api/tags/python")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]


def test_delete_tag_not_found(mock_sqlite_storage):
    """Test DELETE /api/tags/{name} returns 404 for missing tag."""
    mock_sqlite_storage.delete_tag.return_value = False
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.delete("/api/tags/nonexistent")
        assert response.status_code == 404


# ---- Search Tests ----

def test_keyword_search(mock_sqlite_storage):
    """Test GET /api/search performs keyword search."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert "results" in data
        assert "total" in data


def test_keyword_search_empty_query():
    """Test GET /api/search returns 400 for empty query."""
    response = client.get("/api/search?q=")
    assert response.status_code == 400


def test_keyword_search_with_content_type(mock_sqlite_storage):
    """Test GET /api/search with content_type filter."""
    with patch("kb.web.dependencies.get_sqlite_storage", return_value=mock_sqlite_storage):
        response = client.get("/api/search?q=test&content_type=file")
        assert response.status_code == 200


def test_semantic_search_service_unavailable():
    """Test POST /api/search/semantic returns appropriate response."""
    # Without mocking, this should either work if configured or return error
    response = client.post(
        "/api/search/semantic",
        json={"query": "test query", "top_k": 5}
    )
    # Accepts 200 (if service configured) or 500/503 (if not configured)
    assert response.status_code in [200, 500, 503]


def test_semantic_search_empty_query():
    """Test POST /api/search/semantic returns 400 for empty query."""
    response = client.post(
        "/api/search/semantic",
        json={"query": "", "top_k": 5}
    )
    assert response.status_code == 400


def test_rag_query_service_unavailable():
    """Test POST /api/rag returns appropriate response."""
    response = client.post(
        "/api/rag",
        json={"question": "What is Python?", "top_k": 5}
    )
    # Accepts 200 (if service configured) or 500/503 (if not configured)
    assert response.status_code in [200, 500, 503]


def test_rag_query_empty_question():
    """Test POST /api/rag returns 400 for empty question."""
    response = client.post(
        "/api/rag",
        json={"question": "", "top_k": 5}
    )
    assert response.status_code == 400


# ---- Mock Semantic Search Tests ----

def test_semantic_search_with_mock():
    """Test POST /api/search/semantic with mocked semantic search."""
    mock_search = MagicMock()
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "id": "doc1",
        "content": "Test content",
        "metadata": {},
        "score": 0.95
    }
    mock_search.search.return_value = [mock_result]
    
    with patch("kb.web.dependencies.get_semantic_search", return_value=mock_search):
        response = client.post(
            "/api/search/semantic",
            json={"query": "test query", "tags": ["python"], "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test query"
        assert len(data["results"]) == 1


def test_rag_query_with_mock():
    """Test POST /api/rag with mocked RAG query."""
    mock_rag = MagicMock()
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "answer": "Python is a programming language.",
        "sources": [],
        "context": "",
        "question": "What is Python?"
    }
    mock_rag.query_with_fallback.return_value = mock_result
    
    with patch("kb.web.dependencies.get_rag_query", return_value=mock_rag):
        response = client.post(
            "/api/rag",
            json={"question": "What is Python?", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is Python?"
        assert "answer" in data
