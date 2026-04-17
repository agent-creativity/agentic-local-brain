"""
Phase 3d: 主题聚类单元测试 + 集成测试

Tests for:
- TopicClusterer._cosine_similarity: pure numpy static method
- TopicClusterer.cluster_all: HDBSCAN with fixed embedding fixture (reproducibility)
- TopicClusterer.classify_document: incremental classification + centroid update
- TopicClusterer.get_topics / get_topic_documents: read queries
- TopicClusterer._generate_label: LLM mock and fallback
- TopicQuery service: get_topics, get_topic, get_topic_documents, get_topic_stats, get_topic_trend
"""

import json
import sqlite3
from typing import List
from unittest.mock import MagicMock

import numpy as np
import pytest

from kb.processors.topic_clusterer import TopicClusterer
from kb.query.topic_query import TopicQuery

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

TOPIC_SCHEMA_SQL = """
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
    conn.executescript(TOPIC_SCHEMA_SQL)
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


def _insert_doc_with_embedding(
    conn, doc_id: str, title: str, embedding: List[float], collected_at="2026-01-01"
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge (id, title, content_type, source, collected_at) "
        "VALUES (?, ?, 'file', 'test', ?)",
        (doc_id, title, collected_at),
    )
    # cluster_all reads embeddings with json.loads — store as JSON string
    conn.execute(
        "INSERT OR REPLACE INTO document_embeddings (knowledge_id, embedding) VALUES (?, ?)",
        (doc_id, json.dumps(embedding)),
    )
    conn.commit()


def _insert_cluster(
    conn, label: str, centroid: List[float], doc_count: int = 0
) -> int:
    conn.execute(
        "INSERT INTO topic_clusters (label, description, document_count, centroid_embedding) "
        "VALUES (?, 'test description', ?, ?)",
        (label, doc_count, json.dumps(centroid)),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_doc(conn, doc_id: str, title: str = "Doc", collected_at="2026-01-01") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge (id, title, content_type, source, collected_at) "
        "VALUES (?, ?, 'file', 'test', ?)",
        (doc_id, title, collected_at),
    )
    conn.commit()


# Fixed embeddings for two well-separated clusters.
# Cluster A: near [1,0,0,0], Cluster B: near [0,0,1,0].
# Using min_cluster_size=2 ensures HDBSCAN groups them.
_CLUSTER_A = [
    [0.99, 0.01, 0.00, 0.00],
    [0.98, 0.02, 0.00, 0.00],
    [0.97, 0.03, 0.00, 0.00],
]
_CLUSTER_B = [
    [0.00, 0.00, 0.99, 0.01],
    [0.00, 0.00, 0.98, 0.02],
    [0.00, 0.00, 0.97, 0.03],
]


# ---------------------------------------------------------------------------
# TestTopicClustererCosineSimilarity
# ---------------------------------------------------------------------------


class TestTopicClustererCosineSimilarity:
    def test_identical_vectors_return_1(self):
        v = np.array([1.0, 0.0, 0.0])
        assert TopicClusterer._cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_0(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert TopicClusterer._cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector_returns_0(self):
        zero = np.array([0.0, 0.0])
        v = np.array([1.0, 0.0])
        assert TopicClusterer._cosine_similarity(zero, v) == 0.0


# ---------------------------------------------------------------------------
# TestTopicClustererClusterAll
# ---------------------------------------------------------------------------


class TestTopicClustererClusterAll:
    def _seed_two_clusters(self, db) -> None:
        all_embeddings = _CLUSTER_A + _CLUSTER_B
        for i, emb in enumerate(all_embeddings):
            _insert_doc_with_embedding(db, f"doc{i}", f"Document {i}", emb)

    def test_cluster_all_returns_stats_dict(self, db):
        self._seed_two_clusters(db)
        clusterer = TopicClusterer(min_cluster_size=2)
        result = clusterer.cluster_all(conn=db)
        assert "clusters" in result
        assert "classified" in result
        assert "noise" in result

    def test_cluster_all_creates_at_least_one_cluster(self, db):
        self._seed_two_clusters(db)
        clusterer = TopicClusterer(min_cluster_size=2)
        result = clusterer.cluster_all(conn=db)
        count = db.execute("SELECT COUNT(*) FROM topic_clusters").fetchone()[0]
        assert count == result["clusters"]
        assert result["clusters"] >= 1

    def test_cluster_all_knowledge_topics_count_matches_classified(self, db):
        self._seed_two_clusters(db)
        clusterer = TopicClusterer(min_cluster_size=2)
        result = clusterer.cluster_all(conn=db)
        kt_count = db.execute("SELECT COUNT(*) FROM knowledge_topics").fetchone()[0]
        assert kt_count == result["classified"]

    def test_cluster_all_clears_existing_clusters_on_rerun(self, db):
        self._seed_two_clusters(db)
        clusterer = TopicClusterer(min_cluster_size=2)
        clusterer.cluster_all(conn=db)
        first_count = db.execute("SELECT COUNT(*) FROM topic_clusters").fetchone()[0]

        # Re-run — should clear and produce same count
        clusterer.cluster_all(conn=db)
        second_count = db.execute("SELECT COUNT(*) FROM topic_clusters").fetchone()[0]
        assert second_count == first_count

    def test_cluster_all_too_few_docs_returns_zero_clusters(self, db):
        # Only 2 docs but min_cluster_size=10
        _insert_doc_with_embedding(db, "doc1", "Doc 1", [1.0, 0.0])
        _insert_doc_with_embedding(db, "doc2", "Doc 2", [0.0, 1.0])
        clusterer = TopicClusterer(min_cluster_size=10)
        result = clusterer.cluster_all(conn=db)
        assert result["clusters"] == 0
        assert result["classified"] == 0


# ---------------------------------------------------------------------------
# TestTopicClustererClassifyDocument
# ---------------------------------------------------------------------------


class TestTopicClustererClassifyDocument:
    def test_classify_assigns_to_most_similar_cluster(self, db):
        clusterer = TopicClusterer(min_cluster_size=2, similarity_threshold=0.5)
        cid_a = _insert_cluster(db, "Cluster A", [1.0, 0.0, 0.0], doc_count=3)
        cid_b = _insert_cluster(db, "Cluster B", [0.0, 1.0, 0.0], doc_count=3)
        _insert_doc(db, "new_doc")

        result = clusterer.classify_document("new_doc", [0.99, 0.01, 0.0], conn=db)
        assert result == cid_a

    def test_classify_returns_none_below_threshold(self, db):
        clusterer = TopicClusterer(min_cluster_size=2, similarity_threshold=0.99)
        _insert_cluster(db, "Cluster A", [1.0, 0.0], doc_count=3)
        _insert_doc(db, "new_doc")

        # Orthogonal embedding → similarity = 0.0 < 0.99
        result = clusterer.classify_document("new_doc", [0.0, 1.0], conn=db)
        assert result is None

    def test_classify_returns_none_when_no_clusters_exist(self, db):
        clusterer = TopicClusterer(min_cluster_size=2)
        _insert_doc(db, "new_doc")
        result = clusterer.classify_document("new_doc", [1.0, 0.0], conn=db)
        assert result is None

    def test_classify_increments_document_count(self, db):
        clusterer = TopicClusterer(min_cluster_size=2, similarity_threshold=0.5)
        cid = _insert_cluster(db, "Cluster A", [1.0, 0.0, 0.0], doc_count=3)
        _insert_doc(db, "new_doc")

        clusterer.classify_document("new_doc", [0.99, 0.01, 0.0], conn=db)

        row = db.execute(
            "SELECT document_count FROM topic_clusters WHERE id = ?", (cid,)
        ).fetchone()
        assert row[0] == 4

    def test_classify_updates_centroid_running_average(self, db):
        clusterer = TopicClusterer(min_cluster_size=2, similarity_threshold=0.5)
        # centroid=[1.0, 0.0], doc_count=1
        cid = _insert_cluster(db, "Cluster A", [1.0, 0.0], doc_count=1)
        _insert_doc(db, "new_doc")

        clusterer.classify_document("new_doc", [0.9, 0.1], conn=db)

        centroid_json = db.execute(
            "SELECT centroid_embedding FROM topic_clusters WHERE id = ?", (cid,)
        ).fetchone()[0]
        centroid = json.loads(centroid_json)
        # Running avg: (1.0*1 + 0.9) / 2 = 0.95, (0.0*1 + 0.1) / 2 = 0.05
        assert centroid[0] == pytest.approx(0.95)
        assert centroid[1] == pytest.approx(0.05)

    def test_classify_creates_knowledge_topics_record(self, db):
        clusterer = TopicClusterer(min_cluster_size=2, similarity_threshold=0.5)
        cid = _insert_cluster(db, "Cluster A", [1.0, 0.0, 0.0], doc_count=3)
        _insert_doc(db, "new_doc")

        clusterer.classify_document("new_doc", [0.99, 0.01, 0.0], conn=db)

        row = db.execute(
            "SELECT cluster_id, confidence FROM knowledge_topics WHERE knowledge_id = 'new_doc'"
        ).fetchone()
        assert row is not None
        assert row[0] == cid
        assert row[1] > 0.9


# ---------------------------------------------------------------------------
# TestTopicClustererGetTopics
# ---------------------------------------------------------------------------


class TestTopicClustererGetTopics:
    def test_get_topics_returns_list_of_dicts(self, db):
        clusterer = TopicClusterer(min_cluster_size=2)
        _insert_cluster(db, "AI Research", [1.0, 0.0], doc_count=5)
        topics = clusterer.get_topics(conn=db)
        assert len(topics) == 1
        assert topics[0]["label"] == "AI Research"
        assert topics[0]["document_count"] == 5

    def test_get_topics_ordered_by_doc_count_desc(self, db):
        clusterer = TopicClusterer(min_cluster_size=2)
        _insert_cluster(db, "Small", [1.0, 0.0], doc_count=2)
        _insert_cluster(db, "Big", [0.0, 1.0], doc_count=10)

        topics = clusterer.get_topics(conn=db)
        counts = [t["document_count"] for t in topics]
        assert counts == sorted(counts, reverse=True)

    def test_get_topics_empty_returns_empty_list(self, db):
        clusterer = TopicClusterer(min_cluster_size=2)
        assert clusterer.get_topics(conn=db) == []


# ---------------------------------------------------------------------------
# TestTopicClustererLabelGeneration
# ---------------------------------------------------------------------------


class TestTopicClustererLabelGeneration:
    def test_generate_label_uses_llm_response(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = (
            '{"label": "Machine Learning", "description": "ML techniques."}'
        )
        clusterer = TopicClusterer(provider=mock_provider, min_cluster_size=2)
        label, description = clusterer._generate_label(["Intro to ML", "Deep Learning"])
        assert label == "Machine Learning"
        assert description == "ML techniques."

    def test_generate_label_fallback_when_no_provider(self):
        clusterer = TopicClusterer(min_cluster_size=2)
        label, description = clusterer._generate_label(["My First Title", "Another"])
        assert "My First Title" in label
        assert description  # non-empty

    def test_generate_label_fallback_on_llm_error(self):
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = Exception("API error")
        clusterer = TopicClusterer(provider=mock_provider, min_cluster_size=2)
        label, description = clusterer._generate_label(["Fallback Title"])
        assert "Fallback Title" in label


# ---------------------------------------------------------------------------
# TestTopicQueryService
# ---------------------------------------------------------------------------


class TestTopicQueryService:
    def test_get_topics_returns_correct_schema(self, db, mock_storage):
        _insert_cluster(db, "AI Topic", [1.0, 0.0], doc_count=3)
        query = TopicQuery(storage=mock_storage)
        topics = query.get_topics()
        assert len(topics) == 1
        t = topics[0]
        assert t["label"] == "AI Topic"
        assert t["document_count"] == 3
        assert "id" in t and "description" in t

    def test_get_topic_returns_none_for_missing_id(self, db, mock_storage):
        query = TopicQuery(storage=mock_storage)
        assert query.get_topic(9999) is None

    def test_get_topic_returns_correct_cluster(self, db, mock_storage):
        cid = _insert_cluster(db, "Python", [1.0, 0.0], doc_count=5)
        query = TopicQuery(storage=mock_storage)
        topic = query.get_topic(cid)
        assert topic is not None
        assert topic["label"] == "Python"

    def test_get_topic_documents_sorted_by_confidence(self, db, mock_storage):
        cid = _insert_cluster(db, "Cluster A", [1.0, 0.0], doc_count=2)
        for doc_id, conf in [("doc1", 0.6), ("doc2", 0.9)]:
            _insert_doc(db, doc_id, f"Title {doc_id}")
            db.execute(
                "INSERT INTO knowledge_topics (knowledge_id, cluster_id, confidence) "
                "VALUES (?, ?, ?)",
                (doc_id, cid, conf),
            )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        docs = query.get_topic_documents(cid)
        confidences = [d["confidence"] for d in docs]
        assert confidences == sorted(confidences, reverse=True)

    def test_get_topic_stats_returns_expected_keys(self, db, mock_storage):
        query = TopicQuery(storage=mock_storage)
        stats = query.get_topic_stats()
        assert set(stats.keys()) == {
            "total_topics",
            "total_classified",
            "total_documents",
            "unclassified",
        }

    def test_get_topic_stats_unclassified_count(self, db, mock_storage):
        cid = _insert_cluster(db, "Cluster A", [1.0, 0.0], doc_count=1)
        _insert_doc(db, "classified_doc")
        _insert_doc(db, "unclassified_doc")
        db.execute(
            "INSERT INTO knowledge_topics (knowledge_id, cluster_id) VALUES ('classified_doc', ?)",
            (cid,),
        )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        stats = query.get_topic_stats()
        assert stats["total_documents"] == 2
        assert stats["total_classified"] == 1
        assert stats["unclassified"] == 1

    def test_get_topic_trend_returns_list(self, db, mock_storage):
        cid = _insert_cluster(db, "AI Topic", [1.0, 0.0], doc_count=1)
        _insert_doc(db, "doc1", collected_at="2026-01-15")
        db.execute(
            "INSERT INTO knowledge_topics (knowledge_id, cluster_id, confidence) VALUES ('doc1', ?, 0.9)",
            (cid,),
        )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        trend = query.get_topic_trend(period="monthly")
        assert isinstance(trend, list)
        assert len(trend) >= 1
        assert trend[0]["topic_id"] == cid
        assert trend[0]["label"] == "AI Topic"
        assert "period" in trend[0] and "count" in trend[0]


# ---------------------------------------------------------------------------
# TestTopicQueryTimeline
# ---------------------------------------------------------------------------


class TestTopicQueryTimeline:
    def test_get_timeline_data_returns_correct_schema(self, db, mock_storage):
        cid = _insert_cluster(db, "ML", [1.0, 0.0], doc_count=1)
        _insert_doc(db, "doc1", title="Deep Learning", collected_at="2026-03-01")
        db.execute(
            "INSERT INTO knowledge_topics (knowledge_id, cluster_id, confidence) VALUES ('doc1', ?, 0.9)",
            (cid,),
        )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        data = query.get_timeline_data()

        assert len(data) == 1
        row = data[0]
        assert row["id"] == "doc1"
        assert row["title"] == "Deep Learning"
        assert row["topic_label"] == "ML"
        assert row["collected_at"] == "2026-03-01"
        assert "confidence" in row

    def test_get_timeline_data_sorted_by_collected_at_asc(self, db, mock_storage):
        cid = _insert_cluster(db, "Topic A", [1.0, 0.0], doc_count=2)
        _insert_doc(db, "doc_old", collected_at="2026-01-01")
        _insert_doc(db, "doc_new", collected_at="2026-06-01")
        for doc_id in ["doc_old", "doc_new"]:
            db.execute(
                "INSERT INTO knowledge_topics (knowledge_id, cluster_id) VALUES (?, ?)",
                (doc_id, cid),
            )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        data = query.get_timeline_data()

        assert data[0]["id"] == "doc_old"
        assert data[1]["id"] == "doc_new"

    def test_get_timeline_data_excludes_docs_without_topic(self, db, mock_storage):
        cid = _insert_cluster(db, "AI", [1.0, 0.0], doc_count=1)
        _insert_doc(db, "classified_doc", collected_at="2026-01-01")
        _insert_doc(db, "unclassified_doc", collected_at="2026-02-01")
        db.execute(
            "INSERT INTO knowledge_topics (knowledge_id, cluster_id) VALUES ('classified_doc', ?)",
            (cid,),
        )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        data = query.get_timeline_data()

        ids = [r["id"] for r in data]
        assert "classified_doc" in ids
        assert "unclassified_doc" not in ids

    def test_get_timeline_data_empty_returns_empty_list(self, db, mock_storage):
        query = TopicQuery(storage=mock_storage)
        assert query.get_timeline_data() == []

    def test_get_timeline_data_limit_respected(self, db, mock_storage):
        cid = _insert_cluster(db, "Topic", [1.0, 0.0], doc_count=5)
        for i in range(5):
            doc_id = f"doc{i}"
            _insert_doc(db, doc_id, collected_at=f"2026-0{i+1}-01")
            db.execute(
                "INSERT INTO knowledge_topics (knowledge_id, cluster_id) VALUES (?, ?)",
                (doc_id, cid),
            )
        db.commit()

        query = TopicQuery(storage=mock_storage)
        data = query.get_timeline_data(limit=3)
        assert len(data) <= 3


# ---------------------------------------------------------------------------
# TestTimelineAPIValidation
# ---------------------------------------------------------------------------


class TestTimelineAPIValidation:
    def _make_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from kb.web.routes.topics import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        return TestClient(app)

    def test_limit_below_1_returns_400(self):
        client = self._make_client()
        response = client.get("/api/topics/timeline?limit=0")
        assert response.status_code == 400

    def test_limit_above_2000_returns_400(self):
        client = self._make_client()
        response = client.get("/api/topics/timeline?limit=2001")
        assert response.status_code == 400

    def test_valid_limit_accepted(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch("kb.web.dependencies.get_topic_query") as mock_tq:
            mock_tq.return_value.get_timeline_data.return_value = []
            mock_tq.return_value.get_topics.return_value = []
            response = client.get("/api/topics/timeline?limit=100")
        assert response.status_code == 200
