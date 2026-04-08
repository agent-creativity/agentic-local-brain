"""
Phase 2d: 跨文档关系单元测试 + 集成测试

Tests for:
- _cosine_similarity: pure function, no mocks
- DocEmbeddingService: generate_for_document, get_embedding, generate_incremental
- DocRelationBuilder: find_similar_documents, find_shared_entity_relations,
  save_relation, build_relations_for_document
- API validation for GET /api/knowledge/{id}/related
"""

import json
import sqlite3
import struct
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from kb.processors.doc_embedding import DocEmbeddingService
from kb.processors.doc_relation_builder import (
    DocRelationBuilder,
    _cosine_similarity,
    _deserialize_embedding,
    _serialize_embedding,
)

# ---------------------------------------------------------------------------
# Minimal schema (no FK enforcement in-memory for simplicity)
# ---------------------------------------------------------------------------

PHASE2_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    title TEXT,
    content_type TEXT,
    source TEXT,
    collected_at TIMESTAMP,
    summary TEXT,
    word_count INTEGER DEFAULT 0,
    file_path TEXT,
    content_hash TEXT
);
CREATE TABLE IF NOT EXISTS document_embeddings (
    knowledge_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS document_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_knowledge_id TEXT NOT NULL,
    target_knowledge_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    score REAL NOT NULL,
    shared_entities TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_knowledge_id, target_knowledge_id, relation_type)
);
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    display_name TEXT,
    type TEXT NOT NULL,
    description TEXT,
    mention_count INTEGER DEFAULT 1,
    UNIQUE(name, type)
);
CREATE TABLE IF NOT EXISTS entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    knowledge_id TEXT NOT NULL,
    context TEXT,
    UNIQUE(entity_id, knowledge_id)
);
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(PHASE2_SCHEMA_SQL)
    yield conn
    conn.close()


@pytest.fixture
def mock_storage(db):
    storage = MagicMock()
    storage.conn = db
    return storage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_doc(conn, doc_id, title="Test Doc", summary="test summary"):
    conn.execute(
        "INSERT INTO knowledge (id, title, summary, content_type, source, collected_at) "
        "VALUES (?, ?, ?, 'file', 'test', '2026-01-01')",
        (doc_id, title, summary),
    )
    conn.commit()


def _store_blob_embedding(conn, knowledge_id: str, embedding: List[float]) -> None:
    """Store embedding as BLOB (DocRelationBuilder format)."""
    blob = _serialize_embedding(embedding)
    conn.execute(
        "INSERT OR REPLACE INTO document_embeddings (knowledge_id, embedding) VALUES (?, ?)",
        (knowledge_id, blob),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# TestCosimSimilarity
# ---------------------------------------------------------------------------


class TestCosimSimilarity:
    def test_identical_vectors_return_1(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_0(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors_return_neg_1(self):
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_0(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# TestDocEmbeddingServiceGenerate
# ---------------------------------------------------------------------------


class TestDocEmbeddingServiceGenerate:
    def _make_service(self, embedding=None):
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [embedding or [0.1, 0.2, 0.3]]
        return DocEmbeddingService(embedder=mock_embedder), mock_embedder

    def test_generate_for_document_stores_json(self, db):
        svc, _ = self._make_service()
        result = svc.generate_for_document("doc1", "Title", "Content here", conn=db)

        assert result == [0.1, 0.2, 0.3]
        row = db.execute(
            "SELECT embedding FROM document_embeddings WHERE knowledge_id = ?", ("doc1",)
        ).fetchone()
        assert row is not None
        assert json.loads(row[0]) == [0.1, 0.2, 0.3]

    def test_get_embedding_retrieves_stored_json(self, db):
        svc, _ = self._make_service()
        svc.generate_for_document("doc1", "Title", "Content", conn=db)
        retrieved = svc.get_embedding("doc1", conn=db)
        assert retrieved == [0.1, 0.2, 0.3]

    def test_get_embedding_returns_none_if_missing(self, db):
        svc, _ = self._make_service()
        assert svc.get_embedding("nonexistent", conn=db) is None

    def test_generate_incremental_skips_existing_embedding(self, db):
        svc, mock_embedder = self._make_service()
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        # Pre-seed doc1 with an embedding (using JSON format for DocEmbeddingService)
        db.execute(
            "INSERT INTO document_embeddings (knowledge_id, embedding) VALUES (?, ?)",
            ("doc1", json.dumps([0.9, 0.9, 0.9])),
        )
        db.commit()

        result = svc.generate_incremental(conn=db)
        assert result["processed"] == 1
        mock_embedder.embed.assert_called_once()

    def test_generate_incremental_returns_stats_dict(self, db):
        svc, _ = self._make_service()
        _insert_doc(db, "doc1")
        result = svc.generate_incremental(conn=db)
        assert set(result.keys()) == {"processed", "skipped", "failed"}

    def test_build_embedding_text_truncates_content(self):
        svc, _ = self._make_service()
        svc.max_content_length = 10
        text = svc._build_embedding_text("Title", "X" * 100)
        content_part = text.split("\n")[1]
        assert len(content_part) == 10

    def test_generate_for_document_empty_text_returns_none(self, db):
        svc, _ = self._make_service()
        result = svc.generate_for_document("doc1", "", "", conn=db)
        assert result is None


# ---------------------------------------------------------------------------
# TestDocRelationBuilderEmbeddingSimilarity
# ---------------------------------------------------------------------------


class TestDocRelationBuilderEmbeddingSimilarity:
    def test_finds_similar_docs_above_threshold(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        _insert_doc(db, "doc3")
        _store_blob_embedding(db, "doc2", [1.0, 0.0])   # identical → sim=1.0
        _store_blob_embedding(db, "doc3", [0.0, 1.0])   # orthogonal → sim=0.0

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.75)
        results = builder.find_similar_documents("doc1", [1.0, 0.0])

        ids = [r[0] for r in results]
        assert "doc2" in ids
        assert "doc3" not in ids

    def test_excludes_self_from_results(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _store_blob_embedding(db, "doc1", [1.0, 0.0])

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.0)
        results = builder.find_similar_documents("doc1", [1.0, 0.0])
        assert "doc1" not in [r[0] for r in results]

    def test_results_sorted_by_score_descending(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        _insert_doc(db, "doc3")
        # doc2 and doc3 both above threshold but different scores
        _store_blob_embedding(db, "doc2", [0.9, 0.1])
        _store_blob_embedding(db, "doc3", [0.8, 0.2])

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.0)
        results = builder.find_similar_documents("doc1", [1.0, 0.0])

        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_returns_empty_when_all_below_threshold(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        _store_blob_embedding(db, "doc2", [0.0, 1.0])   # orthogonal → sim=0.0

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.75)
        results = builder.find_similar_documents("doc1", [1.0, 0.0])
        assert results == []


# ---------------------------------------------------------------------------
# TestDocRelationBuilderSharedEntities
# ---------------------------------------------------------------------------


class TestDocRelationBuilderSharedEntities:
    def _add_entity_and_mention(self, db, entity_name, knowledge_id):
        db.execute(
            "INSERT OR IGNORE INTO entities (name, type) VALUES (?, 'concept')",
            (entity_name,),
        )
        db.commit()
        entity_id = db.execute(
            "SELECT id FROM entities WHERE name = ?", (entity_name,)
        ).fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO entity_mentions (entity_id, knowledge_id) VALUES (?, ?)",
            (entity_id, knowledge_id),
        )
        db.commit()
        return entity_id

    def test_finds_docs_with_shared_entity(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        entity_id = self._add_entity_and_mention(db, "python", "doc1")
        self._add_entity_and_mention(db, "python", "doc2")

        builder = DocRelationBuilder(storage=mock_storage)
        results = builder.find_shared_entity_relations("doc1")

        assert len(results) == 1
        other_id, shared_count, entity_ids = results[0]
        assert other_id == "doc2"
        assert shared_count == 1.0
        assert entity_id in entity_ids

    def test_excludes_self_from_shared_entity_results(self, db, mock_storage):
        _insert_doc(db, "doc1")
        self._add_entity_and_mention(db, "python", "doc1")

        builder = DocRelationBuilder(storage=mock_storage)
        results = builder.find_shared_entity_relations("doc1")
        assert "doc1" not in [r[0] for r in results]

    def test_no_shared_entities_returns_empty(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        self._add_entity_and_mention(db, "python", "doc1")
        self._add_entity_and_mention(db, "java", "doc2")

        builder = DocRelationBuilder(storage=mock_storage)
        results = builder.find_shared_entity_relations("doc1")
        assert results == []


# ---------------------------------------------------------------------------
# TestDocRelationBuilderSaveRelation
# ---------------------------------------------------------------------------


class TestDocRelationBuilderSaveRelation:
    def test_save_relation_inserts_row(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")

        builder = DocRelationBuilder(storage=mock_storage)
        builder.save_relation("doc1", "doc2", "embedding_similarity", 0.9)

        row = db.execute(
            "SELECT * FROM document_relations "
            "WHERE source_knowledge_id = 'doc1' AND target_knowledge_id = 'doc2'"
        ).fetchone()
        assert row is not None
        assert row["relation_type"] == "embedding_similarity"
        assert row["score"] == pytest.approx(0.9)

    def test_save_relation_stores_shared_entities_as_json(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")

        builder = DocRelationBuilder(storage=mock_storage)
        builder.save_relation("doc1", "doc2", "shared_entity", 3.0, shared_entities=[10, 20])

        row = db.execute(
            "SELECT shared_entities FROM document_relations WHERE source_knowledge_id = 'doc1'"
        ).fetchone()
        assert json.loads(row[0]) == [10, 20]

    def test_save_relation_upserts_on_conflict(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")

        builder = DocRelationBuilder(storage=mock_storage)
        builder.save_relation("doc1", "doc2", "embedding_similarity", 0.8)
        builder.save_relation("doc1", "doc2", "embedding_similarity", 0.95)

        count = db.execute("SELECT COUNT(*) FROM document_relations").fetchone()[0]
        assert count == 1
        row = db.execute("SELECT score FROM document_relations").fetchone()
        assert row[0] == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# TestDocRelationBuilderBuildRelations
# ---------------------------------------------------------------------------


class TestDocRelationBuilderBuildRelations:
    def test_build_relations_returns_counts_dict(self, db, mock_storage):
        _insert_doc(db, "doc1")

        builder = DocRelationBuilder(storage=mock_storage)
        with patch.object(builder, "generate_doc_embedding", return_value=None):
            result = builder.build_relations_for_document("doc1")

        assert "embedding_similarity" in result
        assert "shared_entity" in result

    def test_build_relations_saves_embedding_similar_docs(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        _store_blob_embedding(db, "doc1", [1.0, 0.0])
        _store_blob_embedding(db, "doc2", [1.0, 0.0])  # identical → sim=1.0

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.75)
        result = builder.build_relations_for_document("doc1")

        assert result["embedding_similarity"] >= 1
        row = db.execute(
            "SELECT * FROM document_relations WHERE relation_type = 'embedding_similarity'"
        ).fetchone()
        assert row is not None

    def test_build_relations_saves_shared_entity_docs(self, db, mock_storage):
        _insert_doc(db, "doc1")
        _insert_doc(db, "doc2")
        db.execute("INSERT INTO entities (name, type) VALUES ('python', 'tool')")
        db.commit()
        entity_id = db.execute("SELECT id FROM entities WHERE name='python'").fetchone()[0]
        db.execute("INSERT INTO entity_mentions (entity_id, knowledge_id) VALUES (?, 'doc1')", (entity_id,))
        db.execute("INSERT INTO entity_mentions (entity_id, knowledge_id) VALUES (?, 'doc2')", (entity_id,))
        db.commit()

        builder = DocRelationBuilder(storage=mock_storage, similarity_threshold=0.75)
        with patch.object(builder, "generate_doc_embedding", return_value=None):
            result = builder.build_relations_for_document("doc1")

        assert result["shared_entity"] == 1

    def test_build_relations_nonexistent_doc_returns_zeros(self, db, mock_storage):
        builder = DocRelationBuilder(storage=mock_storage)
        result = builder.build_relations_for_document("nonexistent")
        assert result == {"embedding_similarity": 0, "shared_entity": 0}


# ---------------------------------------------------------------------------
# TestDocRelationAPIValidation
# ---------------------------------------------------------------------------


class TestDocRelationAPIValidation:
    def test_invalid_relation_type_returns_400(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from kb.web.routes.graph import router

        app = FastAPI()
        app.include_router(router, prefix="/api")

        client = TestClient(app)
        response = client.get("/api/knowledge/doc1/related?relation_type=invalid_type")
        assert response.status_code == 400
        assert "Invalid relation_type" in response.json()["detail"]

    def test_valid_relation_type_embedding_similarity_accepted(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from kb.web.routes.graph import router

        app = FastAPI()
        app.include_router(router, prefix="/api")

        with patch("kb.web.dependencies.get_graph_query") as mock_gq:
            mock_gq.return_value.get_related_documents.return_value = []
            client = TestClient(app)
            response = client.get(
                "/api/knowledge/doc1/related?relation_type=embedding_similarity"
            )
        assert response.status_code == 200

    def test_valid_relation_type_shared_entity_accepted(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from kb.web.routes.graph import router

        app = FastAPI()
        app.include_router(router, prefix="/api")

        with patch("kb.web.dependencies.get_graph_query") as mock_gq:
            mock_gq.return_value.get_related_documents.return_value = []
            client = TestClient(app)
            response = client.get(
                "/api/knowledge/doc1/related?relation_type=shared_entity"
            )
        assert response.status_code == 200
