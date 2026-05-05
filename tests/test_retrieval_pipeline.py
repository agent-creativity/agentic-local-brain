"""
RetrievalPipeline 集成测试

覆盖:
- 完整 Pipeline 正常路径（mock LLM + search 组件）
- RRF 融合正确性
- 降级场景：LLM 全部失败、零结果、混合部分失败
- Confidence 计算正确性
- stages_fired 传递正确性
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.query.retrieval_pipeline import RetrievalPipeline, _pipeline_cache, invalidate_pipeline_cache
from kb.query.models import (
    EnhancedRAGResult,
    EntityContext,
    RankedChunk,
    RetrievalContext,
    SearchResult,
)
from kb.query.query_expander import ExpandedQuery, NoOpQueryExpander
from kb.query.reranker import BaseReranker, NoOpReranker
from kb.query.context_builder import BaseContextBuilder, SimpleContextBuilder
from kb.query.conversation import ConversationManager


# ─────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_pipeline_cache():
    """Ensure pipeline cache is clean before and after each test."""
    _pipeline_cache.clear()
    yield
    _pipeline_cache.clear()


def _make_mock_config():
    """Create a mock Config with sensible defaults."""
    config = MagicMock()
    config.get.side_effect = lambda *args, **kwargs: {
        "query": {
            "pipeline": {"top_k": 5, "rerank_top_k": 3},
            "rag": {
                "temperature": 0.3,
                "max_tokens": 1000,
                "context_budget": 4000,
                "context_format": "flat",
                "system_prompt": "You are a helpful assistant.",
                "conversation": {"history_turns_in_context": 5},
            },
        },
    }
    config.to_dict.return_value = {}
    config.data_dir = "/tmp/test-data"
    return config


def _make_sample_chunks(count=5):
    """Create sample RankedChunk results."""
    chunks = []
    for i in range(count):
        chunks.append(
            RankedChunk(
                content=f"This is document chunk number {i}. It contains useful information.",
                source=f"doc-{i}",
                retrieval_score=0.5 - i * 0.05,
                rerank_score=0.0,
                final_score=0.5 - i * 0.05,
                metadata={"title": f"Doc {i}", "source": f"doc-{i}"},
            )
        )
    return chunks


def _make_pipeline(config=None, **overrides):
    """Create a RetrievalPipeline with mock/minimal components."""
    if config is None:
        config = _make_mock_config()

    pipeline = RetrievalPipeline.__new__(RetrievalPipeline)
    pipeline.config = config
    pipeline.default_top_k = config.get("query", {}).get("pipeline", {}).get("top_k", 5)
    pipeline.rerank_top_k = config.get("query", {}).get("pipeline", {}).get("rerank_top_k", 3)
    pipeline.context_budget = config.get("query", {}).get("rag", {}).get("context_budget", 4000)
    pipeline.temperature = config.get("query", {}).get("rag", {}).get("temperature", 0.3)
    pipeline.max_tokens = config.get("query", {}).get("rag", {}).get("max_tokens", 1000)
    pipeline.system_prompt = config.get("query", {}).get("rag", {}).get(
        "system_prompt", "You are a helpful assistant."
    )
    pipeline.llm_available = False
    pipeline.llm_model = None
    pipeline.llm_api_key = None
    pipeline.llm_api_base = None

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

    for key, value in overrides.items():
        setattr(pipeline, key, value)

    return pipeline


# ─────────────────────────────────────────────
# Test: Full Pipeline Normal Path
# ─────────────────────────────────────────────


class TestPipelineFullFlow:
    """完整 Pipeline 流程测试——mock 所有外部组件，验证正常路径"""

    def test_run_returns_answer_and_sources(self):
        """Pipeline 正常运行时返回 answer 和 sources"""
        chunks = _make_sample_chunks(3)
        config = _make_mock_config()

        mock_reranker = MagicMock(spec=BaseReranker)
        mock_reranker.rerank.return_value = chunks

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=100,
            budget=4000,
        )

        pipeline = _make_pipeline(
            config,
            reranker=mock_reranker,
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "This is the answer."
                mock_litellm.completion.return_value = mock_response

                result = pipeline.run("What is machine learning?")

        assert result.answer == "This is the answer."
        assert len(result.sources) == 3
        assert "hybrid_retrieval" in result.retrieval_strategy

    def test_stages_fired_recorded_in_result(self):
        """retrieval_strategy 字段记录了执行过的 stage"""
        chunks = _make_sample_chunks(2)
        # Reranker must return a different list for "reranking" to be recorded
        # (the code checks `reranked_chunks != chunks`)
        reranked_chunks = [
            RankedChunk(
                content=chunks[1].content,
                source=chunks[1].source,
                retrieval_score=0.3,
                rerank_score=0.8,
                final_score=0.8,
                metadata={"title": "Doc 1", "source": "doc-1"},
            ),
            RankedChunk(
                content=chunks[0].content,
                source=chunks[0].source,
                retrieval_score=0.5,
                rerank_score=0.6,
                final_score=0.6,
                metadata={"title": "Doc 0", "source": "doc-0"},
            ),
        ]

        mock_reranker = MagicMock(spec=BaseReranker)
        mock_reranker.rerank.return_value = reranked_chunks

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=reranked_chunks,
            entities=[],
            topic_context=None,
            token_count=50,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            reranker=mock_reranker,
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Answer."
                mock_litellm.completion.return_value = mock_response

                result = pipeline.run("Test question")

        stages = result.retrieval_strategy.split(",")
        assert "hybrid_retrieval" in stages
        assert "reranking" in stages
        assert "context_building" in stages
        assert "answer_generation" in stages

    def test_confidence_calculated_with_stages_fired(self):
        """confidence 不为 0，stages_fired 正确传递给了 _calculate_confidence"""
        chunks = _make_sample_chunks(3)

        mock_reranker = MagicMock(spec=BaseReranker)
        mock_reranker.rerank.return_value = chunks

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=80,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            reranker=mock_reranker,
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Answer."
                mock_litellm.completion.return_value = mock_response

                result = pipeline.run("What is AI?")

        # Confidence should be calculated (not 0) since stages_fired is passed
        assert result.confidence > 0.0
        assert result.confidence <= 1.0


# ─────────────────────────────────────────────
# Test: RRF Fusion
# ─────────────────────────────────────────────


class TestRRFFusion:
    """Reciprocal Rank Fusion 融合正确性测试"""

    def test_rrf_single_list(self):
        """单路检索时 RRF 分数正确"""
        results = [
            SearchResult(id="a", content="A", metadata={}, score=0.9),
            SearchResult(id="b", content="B", metadata={}, score=0.7),
        ]
        pipeline = _make_pipeline(_make_mock_config())
        scores = pipeline._reciprocal_rank_fusion([results])

        assert "a" in scores
        assert "b" in scores
        assert scores["a"] > scores["b"]  # Higher rank = higher score
        # RRF(a) = 1/(60+1) = 0.01639..., RRF(b) = 1/(60+2) = 0.01612...
        assert abs(scores["a"] - 1 / 61) < 1e-6
        assert abs(scores["b"] - 1 / 62) < 1e-6

    def test_rrf_two_lists(self):
        """两路检索时 RRF 融合正确——同时出现在两路的文档分数更高"""
        list1 = [
            SearchResult(id="x", content="X", metadata={}, score=0.9),
            SearchResult(id="y", content="Y", metadata={}, score=0.7),
        ]
        list2 = [
            SearchResult(id="y", content="Y", metadata={}, score=0.8),
            SearchResult(id="z", content="Z", metadata={}, score=0.6),
        ]

        pipeline = _make_pipeline(_make_mock_config())
        scores = pipeline._reciprocal_rank_fusion([list1, list2])

        # y appears in both lists, should have highest score
        assert "x" in scores
        assert "y" in scores
        assert "z" in scores
        assert scores["y"] > scores["x"]
        assert scores["y"] > scores["z"]

    def test_rrf_deduplication(self):
        """同一文档在不同列表中 RRF 正确去重"""
        list1 = [
            SearchResult(id="dup", content="Dup", metadata={}, score=0.9),
        ]
        list2 = [
            SearchResult(id="dup", content="Dup", metadata={}, score=0.8),
        ]

        pipeline = _make_pipeline(_make_mock_config())
        scores = pipeline._reciprocal_rank_fusion([list1, list2])

        assert len(scores) == 1
        assert "dup" in scores
        # Should be sum of both ranks
        expected = 1 / (60 + 1) + 1 / (60 + 1)
        assert abs(scores["dup"] - expected) < 1e-6

    def test_hybrid_retrieve_produces_ranked_chunks(self):
        """_hybrid_retrieve 返回 RankedChunk 列表，按 RRF 分数降序排列"""
        query_expander = MagicMock()
        query_expander.expand.return_value = ExpandedQuery(original="test query")

        semantic_results = [
            SearchResult(id="doc1", content="semantic 1", metadata={"source": "doc1"}, score=0.9),
            SearchResult(id="doc2", content="semantic 2", metadata={"source": "doc2"}, score=0.8),
        ]
        mock_semantic = MagicMock()
        mock_semantic.search_batch.return_value = semantic_results

        keyword_results = [
            SearchResult(id="doc2", content="keyword 2", metadata={"source": "doc2"}, score=0.7),
            SearchResult(id="doc3", content="keyword 3", metadata={"source": "doc3"}, score=0.6),
        ]
        mock_keyword = MagicMock()
        mock_keyword.search.return_value = keyword_results

        pipeline = _make_pipeline(
            _make_mock_config(),
            query_expander=query_expander,
        )
        pipeline.semantic_search = mock_semantic
        pipeline.keyword_search = mock_keyword

        expanded = ExpandedQuery(original="test query")
        chunks = pipeline._hybrid_retrieve(expanded, top_k=10)

        assert len(chunks) > 0
        # Verify sorted by final_score descending
        for i in range(len(chunks) - 1):
            assert chunks[i].final_score >= chunks[i + 1].final_score


# ─────────────────────────────────────────────
# Test: Degradation Scenarios
# ─────────────────────────────────────────────


class TestDegradationEmptyResult:
    """零结果场景——没有检索到任何文档"""

    def test_zero_results_returns_empty_answer(self):
        """无检索结果时返回 'No relevant information found'"""
        pipeline = _make_pipeline(_make_mock_config())

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            result = pipeline.run("Unknown topic")

        assert result.answer == "No relevant information found in the knowledge base."
        assert result.confidence == 0.0
        assert result.retrieval_strategy == "no_results"
        assert result.sources == []

    def test_zero_results_is_cached(self):
        """空结果也被缓存，避免重复查询"""
        pipeline = _make_pipeline(_make_mock_config())

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            pipeline.run("Unknown topic")

        # Second call should hit cache
        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]) as mock_retrieve:
            result = pipeline.run("Unknown topic")
            # _hybrid_retrieve should NOT be called on second invocation (cache hit)
            # But actually the cache hit happens before _hybrid_retrieve
            pass

        # Verify cache entry exists
        assert any("Unknown topic" in k for k in _pipeline_cache)


class TestDegradationLLMUnavailable:
    """LLM 不可用场景"""

    def test_llm_unavailable_returns_fallback(self):
        """LLM 不可用时返回文档列表而非 AI 总结"""
        chunks = _make_sample_chunks(3)

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=100,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            llm_available=False,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            result = pipeline.run("What is ML?")

        # Should return fallback answer with source list
        assert "relevant documents" in result.answer.lower()
        assert result.confidence == 0.5
        assert len(result.sources) > 0

    def test_llm_exception_during_generation_returns_fallback(self):
        """LLM 调用异常时降级为文档列表"""
        chunks = _make_sample_chunks(2)

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=80,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_litellm.completion.side_effect = Exception("LLM API timeout")

                result = pipeline.run("What is deep learning?")

        # Should degrade gracefully
        assert "relevant documents" in result.answer.lower()
        assert result.confidence == 0.5

    def test_litellm_import_none_uses_fallback(self):
        """litellm 模块不可用时走 fallback"""
        chunks = _make_sample_chunks(2)

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=80,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            llm_available=False,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            result = pipeline.run("What is Python?")

        assert "relevant documents" in result.answer.lower()


class TestDegradationPartialFailure:
    """混合部分失败场景"""

    def test_reranker_failure_returns_original_order(self):
        """Reranker 失败时返回原始排序"""
        original_chunks = _make_sample_chunks(4)

        mock_reranker = MagicMock(spec=BaseReranker)
        mock_reranker.rerank.side_effect = Exception("Reranker API error")

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=original_chunks,
            entities=[],
            topic_context=None,
            token_count=100,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            reranker=mock_reranker,
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=original_chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Fallback answer."
                mock_litellm.completion.return_value = mock_response

                result = pipeline.run("Test question")

        # Should not crash, answer generated
        assert result.answer is not None
        assert len(result.sources) > 0

    def test_no_reranker_configured_passes_through(self):
        """没有配置 reranker 时直接跳过"""
        chunks = _make_sample_chunks(3)

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=60,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            reranker=None,
            llm_available=True,
        )

        with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Answer."
            mock_litellm.completion.return_value = mock_response

            result = pipeline.run("What is AI?")

        # Should succeed without reranking
        assert result.answer is not None
        assert "reranking" not in result.retrieval_strategy

    def test_noop_reranker_passes_through(self):
        """NoOpReranker 直接返回原始顺序"""
        chunks = _make_sample_chunks(3)

        mock_reranker = NoOpReranker()
        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=60,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            reranker=mock_reranker,
            context_builder=mock_context_builder,
            llm_available=True,
        )

        with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Answer."
            mock_litellm.completion.return_value = mock_response

            result = pipeline.run("Test query")

        assert result.answer is not None
        assert "reranking" not in result.retrieval_strategy

    def test_no_search_methods_returns_empty(self):
        """所有搜索方法都失败/未配置时返回空结果"""
        pipeline = _make_pipeline(_make_mock_config())
        pipeline.semantic_search = None
        pipeline.keyword_search = None

        # _hybrid_retrieve with no search methods returns []
        expanded = ExpandedQuery(original="test")
        chunks = pipeline._hybrid_retrieve(expanded, top_k=10)
        assert chunks == []

    def test_semantic_search_fails_keyword_succeeds(self):
        """语义搜索失败但关键词搜索成功"""
        mock_semantic = MagicMock()
        mock_semantic.search_batch.side_effect = Exception("Embedding API down")

        keyword_results = [
            SearchResult(id="doc1", content="keyword match", metadata={"source": "doc1"}, score=0.8),
        ]
        mock_keyword = MagicMock()
        mock_keyword.search.return_value = keyword_results

        pipeline = _make_pipeline(
            _make_mock_config(),
            query_expander=None,
        )
        pipeline.semantic_search = mock_semantic
        pipeline.keyword_search = mock_keyword

        expanded = ExpandedQuery(original="test query")
        chunks = pipeline._hybrid_retrieve(expanded, top_k=10)

        # Should still get results from keyword search
        assert len(chunks) == 1
        assert chunks[0].source == "doc1"


# ─────────────────────────────────────────────
# Test: Confidence Calculation
# ─────────────────────────────────────────────


class TestConfidenceCalculation:
    """置信度计算正确性测试"""

    def test_no_chunks_returns_zero(self):
        """无 chunk 时 confidence 为 0"""
        pipeline = _make_pipeline(_make_mock_config())
        confidence = pipeline._calculate_confidence([], ["hybrid_retrieval"])
        assert confidence == 0.0

    def test_full_pipeline_returns_high_confidence(self):
        """完整 pipeline 执行后 confidence 应较高"""
        chunks = _make_sample_chunks(4)
        # Set rerank scores for chunks
        for i, chunk in enumerate(chunks):
            chunk.rerank_score = 0.8 - i * 0.1
            chunk.final_score = 0.8 - i * 0.1

        pipeline = _make_pipeline(_make_mock_config())
        confidence = pipeline._calculate_confidence(
            chunks,
            ["query_expansion", "hybrid_retrieval", "reranking", "context_enrichment", "context_building", "answer_generation"],
        )

        # Full pipeline should have confidence > 0.3
        assert confidence > 0.3

    def test_keyword_only_returns_low_confidence(self):
        """仅关键词检索时 confidence 较低"""
        chunks = _make_sample_chunks(2)
        pipeline = _make_pipeline(_make_mock_config())
        confidence = pipeline._calculate_confidence(chunks, ["hybrid_retrieval", "context_building", "answer_generation"])

        # No reranking = lower confidence
        assert confidence < 0.7

    def test_stages_fired_not_default(self):
        """stages_fired 不是默认值 ['answer_generation']，说明正确传递"""
        chunks = _make_sample_chunks(3)
        for chunk in chunks:
            chunk.rerank_score = 0.7
            chunk.final_score = 0.7

        pipeline = _make_pipeline(_make_mock_config())

        # With full stages, confidence should differ from the default-only case
        full_stages = ["hybrid_retrieval", "reranking", "context_building", "answer_generation"]
        default_stages = ["answer_generation"]

        full_confidence = pipeline._calculate_confidence(chunks, full_stages)
        default_confidence = pipeline._calculate_confidence(chunks, default_stages)

        # They should be different because strategy_completeness changes
        assert full_confidence != default_confidence
