"""
RetrievalPipeline 结果缓存测试

覆盖:
- 缓存命中：相同查询 60s 内直接返回
- 缓存失效：TTL 过期后重新执行 pipeline
- 缓存跳过：session_id / conversation_context 场景不走缓存
- 缓存隔离：不同 question / tags / top_k 产生不同缓存条目
- invalidate_pipeline_cache() 清空缓存
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.query.retrieval_pipeline import (
    RetrievalPipeline,
    _pipeline_cache,
    _PIPELINE_CACHE_TTL,
    invalidate_pipeline_cache,
)
from kb.query.models import EnhancedRAGResult, SearchResult


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


def _make_pipeline():
    """Create a pipeline with all heavy components mocked out."""
    config = MagicMock()
    config.get.return_value = {}
    config.to_dict.return_value = {}
    config.data_dir = "/tmp/test"

    pipeline = RetrievalPipeline.__new__(RetrievalPipeline)
    pipeline.config = config
    pipeline.semantic_search = None
    pipeline.keyword_search = None
    pipeline.query_expander = None
    pipeline.reranker = None
    pipeline.context_builder = None
    pipeline.graph_query = None
    pipeline.topic_query = None
    pipeline.reading_history = None
    pipeline.conversation_manager = None
    pipeline.prompt_template_manager = None
    pipeline.default_top_k = 10
    pipeline.rerank_top_k = 5
    pipeline.context_budget = 4000
    pipeline.temperature = 0.3
    pipeline.max_tokens = 1000
    pipeline.system_prompt = "test"
    pipeline.llm_available = False
    return pipeline


def _fake_result(question: str = "test") -> EnhancedRAGResult:
    return EnhancedRAGResult(
        answer="cached answer",
        question=question,
        sources=[],
        context="",
        confidence=0.8,
        retrieval_strategy="hybrid_retrieval,context_building,answer_generation",
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure cache is clean before and after each test."""
    _pipeline_cache.clear()
    yield
    _pipeline_cache.clear()


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────


class TestPipelineCacheHit:
    """相同查询在 TTL 内应命中缓存，不再执行 pipeline。"""

    def test_second_call_returns_cached_result(self):
        pipeline = _make_pipeline()
        result1 = _fake_result("What is ML?")

        # Seed cache
        tags_key = ()
        cache_key = f"pipeline:What is ML?:{tags_key}:10"
        _pipeline_cache[cache_key] = (result1, time.monotonic() + _PIPELINE_CACHE_TTL)

        # run() should return cached result without calling any pipeline stage
        with patch.object(pipeline, "_expand_query") as mock_expand:
            result = pipeline.run("What is ML?")
            mock_expand.assert_not_called()

        assert result is result1
        assert result.answer == "cached answer"

    def test_cache_hit_with_tags(self):
        pipeline = _make_pipeline()
        result1 = _fake_result("test")

        tags = ["python", "ml"]
        tags_key = tuple(sorted(tags))
        cache_key = f"pipeline:test:{tags_key}:10"
        _pipeline_cache[cache_key] = (result1, time.monotonic() + _PIPELINE_CACHE_TTL)

        with patch.object(pipeline, "_expand_query") as mock_expand:
            result = pipeline.run("test", tags=tags)
            mock_expand.assert_not_called()

        assert result is result1


class TestPipelineCacheExpiry:
    """TTL 过期后缓存不应命中。"""

    def test_expired_entry_triggers_pipeline(self):
        pipeline = _make_pipeline()
        result1 = _fake_result("expired query")

        # Seed cache with already-expired entry
        cache_key = "pipeline:expired query:():10"
        _pipeline_cache[cache_key] = (result1, time.monotonic() - 1)

        # Pipeline should execute — _hybrid_retrieve returns empty → _empty_result
        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("expired query")

        assert result is not result1
        assert result.answer == "No relevant information found in the knowledge base."
        # A fresh entry should have been stored with a future expiry
        assert cache_key in _pipeline_cache
        _, expires_at = _pipeline_cache[cache_key]
        assert expires_at > time.monotonic()


class TestPipelineCacheSkip:
    """session_id 或 conversation_context 时不走缓存。"""

    def test_session_id_skips_cache(self):
        pipeline = _make_pipeline()
        result1 = _fake_result("test")
        cache_key = "pipeline:test:():10"
        _pipeline_cache[cache_key] = (result1, time.monotonic() + _PIPELINE_CACHE_TTL)

        # With session_id, pipeline should execute (not use cache)
        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("test", session_id="session-123")

        assert result is not result1

    def test_conversation_context_skips_cache(self):
        pipeline = _make_pipeline()
        result1 = _fake_result("test")
        cache_key = "pipeline:test:():10"
        _pipeline_cache[cache_key] = (result1, time.monotonic() + _PIPELINE_CACHE_TTL)

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("test", conversation_context="prior context")

        assert result is not result1


class TestPipelineCacheIsolation:
    """不同参数组合产生不同缓存条目。"""

    def test_different_questions_isolated(self):
        pipeline = _make_pipeline()
        r1 = _fake_result("q1")
        r2 = _fake_result("q2")

        _pipeline_cache["pipeline:q1:():10"] = (r1, time.monotonic() + _PIPELINE_CACHE_TTL)
        _pipeline_cache["pipeline:q2:():10"] = (r2, time.monotonic() + _PIPELINE_CACHE_TTL)

        with patch.object(pipeline, "_expand_query") as mock:
            assert pipeline.run("q1") is r1
            assert pipeline.run("q2") is r2
            mock.assert_not_called()

    def test_different_top_k_isolated(self):
        pipeline = _make_pipeline()
        r1 = _fake_result("q")

        _pipeline_cache["pipeline:q:():10"] = (r1, time.monotonic() + _PIPELINE_CACHE_TTL)

        # top_k=5 should NOT hit the top_k=10 cache
        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("q", top_k=5)

        assert result is not r1

    def test_different_tags_isolated(self):
        pipeline = _make_pipeline()
        r1 = _fake_result("q")

        _pipeline_cache["pipeline:q:('python',):10"] = (r1, time.monotonic() + _PIPELINE_CACHE_TTL)

        # No tags should NOT hit the tags=('python',) cache
        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("q")

        assert result is not r1


class TestInvalidatePipelineCache:
    """invalidate_pipeline_cache() 应清空所有缓存。"""

    def test_invalidate_clears_all(self):
        _pipeline_cache["k1"] = ("v1", time.monotonic() + 100)
        _pipeline_cache["k2"] = ("v2", time.monotonic() + 100)

        invalidate_pipeline_cache()

        assert len(_pipeline_cache) == 0

    def test_cache_miss_after_invalidate(self):
        pipeline = _make_pipeline()
        r1 = _fake_result("q")
        _pipeline_cache["pipeline:q:():10"] = (r1, time.monotonic() + _PIPELINE_CACHE_TTL)

        invalidate_pipeline_cache()

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("q")

        assert result is not r1


class TestPipelineCacheStore:
    """Pipeline 执行完成后结果应被缓存。"""

    def test_result_stored_in_cache(self):
        pipeline = _make_pipeline()

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            pipeline.run("store test")

        # A cache entry should exist for this query
        cache_key = "pipeline:store test:():10"
        assert cache_key in _pipeline_cache
        cached_result, expires_at = _pipeline_cache[cache_key]
        assert cached_result.question == "store test"
        assert expires_at > time.monotonic()

    def test_session_id_result_not_stored(self):
        pipeline = _make_pipeline()

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            pipeline.run("no store", session_id="s1")

        # Should NOT have been cached
        assert not any("no store" in k for k in _pipeline_cache)
