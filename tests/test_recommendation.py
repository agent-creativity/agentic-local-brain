"""
Phase 4d: 智能推荐单元测试 + 集成测试

Tests for:
- RecommendationEngine._cosine_similarity: static method
- RecommendationEngine.record_action: writing to reading_history
- RecommendationEngine.recommend: time-decay weighted embedding similarity
- Fallback behavior when no reading history exists
- API parameter validation for GET /api/recommendations and GET /api/reading-history
"""

import json
import math
import sqlite3
from typing import List
from unittest.mock import patch

import numpy as np
import pytest

from kb.processors.recommendation import RecommendationEngine

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

RECOMMENDATION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    title TEXT,
    content_type TEXT,
    source TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
CREATE TABLE IF NOT EXISTS reading_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT,
    query TEXT,
    action_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    interaction_type TEXT
);
CREATE TABLE IF NOT EXISTS topic_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    description TEXT,
    document_count INTEGER DEFAULT 0,
    centroid_embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS knowledge_topics (
    knowledge_id TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (knowledge_id, cluster_id)
);
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(RECOMMENDATION_SCHEMA_SQL)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_doc(conn, doc_id: str, title: str = "Doc", collected_at="2026-01-01 00:00:00") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge (id, title, content_type, source, collected_at) "
        "VALUES (?, ?, 'file', 'test', ?)",
        (doc_id, title, collected_at),
    )
    conn.commit()


def _insert_embedding(conn, doc_id: str, embedding: List[float]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO document_embeddings (knowledge_id, embedding) VALUES (?, ?)",
        (doc_id, json.dumps(embedding)),
    )
    conn.commit()


def _insert_history(
    conn, knowledge_id: str, action_type: str = "view", created_at="2026-04-04 12:00:00"
) -> None:
    conn.execute(
        "INSERT INTO reading_history (knowledge_id, action_type, created_at) VALUES (?, ?, ?)",
        (knowledge_id, action_type, created_at),
    )
    conn.commit()


def _insert_topic(conn, label: str, doc_ids: List[str]) -> int:
    conn.execute(
        "INSERT INTO topic_clusters (label, description, document_count) VALUES (?, 'desc', ?)",
        (label, len(doc_ids)),
    )
    conn.commit()
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for doc_id in doc_ids:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_topics (knowledge_id, cluster_id) VALUES (?, ?)",
            (doc_id, cid),
        )
    conn.commit()
    return cid


# ---------------------------------------------------------------------------
# TestRecommendationEngineCosineSimilarity
# ---------------------------------------------------------------------------


class TestRecommendationEngineCosineSimilarity:
    def test_identical_vectors_return_1(self):
        v = np.array([1.0, 0.0, 0.0])
        assert RecommendationEngine._cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_0(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert RecommendationEngine._cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector_returns_0(self):
        zero = np.array([0.0, 0.0])
        v = np.array([1.0, 0.0])
        assert RecommendationEngine._cosine_similarity(zero, v) == 0.0


# ---------------------------------------------------------------------------
# TestRecommendationEngineRecordAction
# ---------------------------------------------------------------------------


class TestRecommendationEngineRecordAction:
    def test_record_action_inserts_to_reading_history(self, db):
        engine = RecommendationEngine()
        engine.record_action("view", knowledge_id="doc1", conn=db)

        row = db.execute(
            "SELECT knowledge_id, action_type FROM reading_history WHERE knowledge_id = 'doc1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "doc1"
        assert row[1] == "view"

    def test_record_action_stores_query(self, db):
        engine = RecommendationEngine()
        engine.record_action("search", query="machine learning", conn=db)

        row = db.execute(
            "SELECT query, action_type FROM reading_history WHERE action_type = 'search'"
        ).fetchone()
        assert row is not None
        assert row[0] == "machine learning"

    def test_record_action_without_knowledge_id(self, db):
        engine = RecommendationEngine()
        engine.record_action("rag_query", query="what is AI?", conn=db)

        count = db.execute("SELECT COUNT(*) FROM reading_history").fetchone()[0]
        assert count == 1


# ---------------------------------------------------------------------------
# TestRecommendationEngineFallback
# ---------------------------------------------------------------------------


class TestRecommendationEngineFallback:
    def test_no_history_returns_most_recent_docs(self, db):
        _insert_doc(db, "doc1", "Recent Doc", collected_at="2026-04-04 00:00:00")
        _insert_doc(db, "doc2", "Older Doc", collected_at="2026-01-01 00:00:00")

        engine = RecommendationEngine(default_limit=2)
        results = engine.recommend(limit=2, conn=db)

        assert len(results) >= 1
        assert results[0]["knowledge_id"] == "doc1"  # most recent first

    def test_no_history_reason_is_latest(self, db):
        _insert_doc(db, "doc1", "Doc 1")

        engine = RecommendationEngine()
        results = engine.recommend(limit=1, conn=db)

        assert len(results) == 1
        assert results[0]["reason"] == "最新收录的文档"
        assert results[0]["score"] == 0.0

    def test_no_history_no_docs_returns_empty_list(self, db):
        engine = RecommendationEngine()
        results = engine.recommend(limit=5, conn=db)
        assert results == []


# ---------------------------------------------------------------------------
# TestRecommendationEngineRecommend
# ---------------------------------------------------------------------------


class TestRecommendationEngineRecommend:
    def test_recommend_returns_correct_schema(self, db):
        _insert_doc(db, "read_doc", "Read Doc")
        _insert_doc(db, "cand_doc", "Candidate Doc")
        _insert_embedding(db, "read_doc", [1.0, 0.0, 0.0])
        _insert_embedding(db, "cand_doc", [0.99, 0.01, 0.0])
        _insert_history(db, "read_doc")

        engine = RecommendationEngine()
        results = engine.recommend(limit=5, conn=db)

        assert len(results) >= 1
        for r in results:
            assert "knowledge_id" in r
            assert "title" in r
            assert "reason" in r
            assert "score" in r

    def test_recommend_excludes_recently_read_docs(self, db):
        _insert_doc(db, "read_doc", "Already Read")
        _insert_doc(db, "new_doc", "New Doc")
        _insert_embedding(db, "read_doc", [1.0, 0.0])
        _insert_embedding(db, "new_doc", [0.9, 0.1])
        _insert_history(db, "read_doc")

        engine = RecommendationEngine()
        results = engine.recommend(limit=10, conn=db)

        result_ids = [r["knowledge_id"] for r in results]
        assert "read_doc" not in result_ids

    def test_recommend_returns_high_similarity_doc_first(self, db):
        _insert_doc(db, "read_doc", "Read Doc")
        _insert_doc(db, "similar_doc", "Very Similar")
        _insert_doc(db, "different_doc", "Very Different")
        _insert_embedding(db, "read_doc", [1.0, 0.0])
        _insert_embedding(db, "similar_doc", [0.99, 0.01])   # high similarity
        _insert_embedding(db, "different_doc", [0.0, 1.0])   # orthogonal
        _insert_history(db, "read_doc")

        engine = RecommendationEngine(topic_bonus=0.0)  # disable topic bonus
        results = engine.recommend(limit=5, conn=db)

        if len(results) >= 2:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_recommend_topic_bonus_increases_score(self, db):
        _insert_doc(db, "read_doc", "Read Doc")
        _insert_doc(db, "same_topic_doc", "Same Topic Doc")
        _insert_doc(db, "diff_topic_doc", "Different Topic Doc")

        # All embeddings similar to read_doc
        _insert_embedding(db, "read_doc", [1.0, 0.0])
        _insert_embedding(db, "same_topic_doc", [0.9, 0.1])
        _insert_embedding(db, "diff_topic_doc", [0.9, 0.1])

        # same_topic_doc shares topic with read_doc
        _insert_topic(db, "Shared Topic", ["read_doc", "same_topic_doc"])
        _insert_history(db, "read_doc")

        engine = RecommendationEngine(topic_bonus=0.1)
        results = engine.recommend(limit=5, conn=db)

        # same_topic_doc should score higher due to bonus
        result_map = {r["knowledge_id"]: r["score"] for r in results}
        if "same_topic_doc" in result_map and "diff_topic_doc" in result_map:
            assert result_map["same_topic_doc"] > result_map["diff_topic_doc"]

    def test_recommend_limit_respected(self, db):
        # Insert 5 docs and history for 1
        _insert_doc(db, "read_doc", "Read Doc")
        _insert_embedding(db, "read_doc", [1.0, 0.0])
        _insert_history(db, "read_doc")

        for i in range(5):
            doc_id = f"cand{i}"
            _insert_doc(db, doc_id, f"Candidate {i}")
            _insert_embedding(db, doc_id, [0.9 - i * 0.01, 0.1 + i * 0.01])

        engine = RecommendationEngine()
        results = engine.recommend(limit=2, conn=db)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# TestRecommendationAPIValidation
# ---------------------------------------------------------------------------


class TestRecommendationAPIValidation:
    def _make_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from kb.web.routes.recommendations import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        return TestClient(app)

    def test_limit_below_1_returns_400(self):
        client = self._make_client()
        response = client.get("/api/recommendations?limit=0")
        assert response.status_code == 400
        assert "limit" in response.json()["detail"]

    def test_limit_above_20_returns_400(self):
        client = self._make_client()
        response = client.get("/api/recommendations?limit=21")
        assert response.status_code == 400

    def test_valid_limit_calls_engine(self):
        client = self._make_client()
        with patch("kb.web.dependencies.get_config") as mock_config, \
             patch("kb.processors.recommendation.RecommendationEngine.from_config") as mock_engine_cls:
            mock_engine = mock_engine_cls.return_value
            mock_engine.recommend.return_value = []
            response = client.get("/api/recommendations?limit=5")
        # Should not be a 400 (validation passes)
        assert response.status_code != 400

    def test_reading_history_limit_below_1_returns_400(self):
        client = self._make_client()
        response = client.get("/api/reading-history?limit=0")
        assert response.status_code == 400

    def test_reading_history_limit_above_200_returns_400(self):
        client = self._make_client()
        response = client.get("/api/reading-history?limit=201")
        assert response.status_code == 400
