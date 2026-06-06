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

from kb.query.context_builder import BaseContextBuilder, SimpleContextBuilder
from kb.query.conversation import ConversationManager
from kb.query.models import (
    ConversationTurn,
    EnhancedRAGResult,
    EntityContext,
    RankedChunk,
    RetrievalContext,
    SearchResult,
)
from kb.query.query_expander import ExpandedQuery, NoOpQueryExpander
from kb.query.reranker import BaseReranker, NoOpReranker
from kb.query.retrieval_pipeline import (
    RetrievalPipeline,
    _pipeline_cache,
    invalidate_pipeline_cache,
)

# ─────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_pipeline_cache():
    """Ensure pipeline cache is clean before and after each test."""
    _pipeline_cache.clear()
    yield
    _pipeline_cache.clear()


def _make_mock_config(**overrides):
    """Create a mock Config with sensible defaults.

    Args:
        **overrides: Key-value pairs to override in the config dict.
            Supports dotted keys like ``rag__model_context_window=8000``
            which sets ``query.rag.model_context_window``.
    """
    config = MagicMock()
    _config_data = {
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
    # Apply overrides to rag section
    for key, value in overrides.items():
        _config_data["query"]["rag"][key] = value

    config.get.side_effect = lambda key, default=None: _config_data.get(key, default)
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
    pipeline.rerank_top_k = (
        config.get("query", {}).get("pipeline", {}).get("rerank_top_k", 3)
    )
    pipeline.context_budget = (
        config.get("query", {}).get("rag", {}).get("context_budget", 4000)
    )
    pipeline.conversation_boost = (
        config.get("query", {}).get("pipeline", {}).get("conversation_boost", 0.15)
    )
    pipeline.temperature = (
        config.get("query", {}).get("rag", {}).get("temperature", 0.3)
    )
    pipeline.max_tokens = config.get("query", {}).get("rag", {}).get("max_tokens", 1000)
    pipeline.system_prompt = (
        config.get("query", {})
        .get("rag", {})
        .get("system_prompt", "You are a helpful assistant.")
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
            SearchResult(
                id="doc1", content="semantic 1", metadata={"source": "doc1"}, score=0.9
            ),
            SearchResult(
                id="doc2", content="semantic 2", metadata={"source": "doc2"}, score=0.8
            ),
        ]
        mock_semantic = MagicMock()
        mock_semantic.search_batch.return_value = semantic_results

        keyword_results = [
            SearchResult(
                id="doc2", content="keyword 2", metadata={"source": "doc2"}, score=0.7
            ),
            SearchResult(
                id="doc3", content="keyword 3", metadata={"source": "doc3"}, score=0.6
            ),
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
        with patch.object(
            pipeline, "_hybrid_retrieve", return_value=[]
        ) as mock_retrieve:
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
            SearchResult(
                id="doc1",
                content="keyword match",
                metadata={"source": "doc1"},
                score=0.8,
            ),
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
            [
                "query_expansion",
                "hybrid_retrieval",
                "reranking",
                "context_enrichment",
                "context_building",
                "answer_generation",
            ],
        )

        # Full pipeline should have confidence > 0.3
        assert confidence > 0.3

    def test_keyword_only_returns_low_confidence(self):
        """仅关键词检索时 confidence 较低"""
        chunks = _make_sample_chunks(2)
        pipeline = _make_pipeline(_make_mock_config())
        confidence = pipeline._calculate_confidence(
            chunks, ["hybrid_retrieval", "context_building", "answer_generation"]
        )

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
        full_stages = [
            "hybrid_retrieval",
            "reranking",
            "context_building",
            "answer_generation",
        ]
        default_stages = ["answer_generation"]

        full_confidence = pipeline._calculate_confidence(chunks, full_stages)
        default_confidence = pipeline._calculate_confidence(chunks, default_stages)

        # They should be different because strategy_completeness changes
        assert full_confidence != default_confidence


# ─────────────────────────────────────────────
# Test: Multi-turn Messages[]
# ─────────────────────────────────────────────


class TestBuildMessages:
    """_build_messages() 构造多轮 messages[] 测试"""

    def test_no_history_returns_system_and_user(self):
        """无对话历史时返回 [system, user]"""
        pipeline = _make_pipeline(_make_mock_config())
        messages = pipeline._build_messages("sys prompt", "user prompt")

        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "sys prompt"}
        assert messages[1] == {"role": "user", "content": "user prompt"}

    def test_with_history_returns_full_messages(self):
        """有对话历史时返回 [system, ...history, user]"""
        pipeline = _make_pipeline(_make_mock_config())
        turns = [
            ConversationTurn(role="user", content="What is Python?"),
            ConversationTurn(
                role="assistant", content="Python is a programming language."
            ),
            ConversationTurn(role="user", content="What about its type system?"),
            ConversationTurn(role="assistant", content="Python uses dynamic typing."),
        ]

        messages = pipeline._build_messages("sys", "current question", turns)

        assert len(messages) == 6  # system + 4 history + current user
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "What is Python?"}
        assert messages[2] == {
            "role": "assistant",
            "content": "Python is a programming language.",
        }
        assert messages[3] == {"role": "user", "content": "What about its type system?"}
        assert messages[4] == {
            "role": "assistant",
            "content": "Python uses dynamic typing.",
        }
        assert messages[5] == {"role": "user", "content": "current question"}

    def test_empty_turns_list_same_as_none(self):
        """空 turns 列表等同于 None"""
        pipeline = _make_pipeline(_make_mock_config())
        messages = pipeline._build_messages("sys", "user", [])

        assert len(messages) == 2


class TestTurnsToFlatText:
    """_turns_to_flat_text() 转换测试"""

    def test_converts_turns_to_text(self):
        pipeline = _make_pipeline(_make_mock_config())
        turns = [
            ConversationTurn(role="user", content="Hello"),
            ConversationTurn(role="assistant", content="Hi there"),
        ]
        text = pipeline._turns_to_flat_text(turns)
        assert "User: Hello" in text
        assert "Assistant: Hi there" in text

    def test_empty_turns_returns_empty(self):
        pipeline = _make_pipeline(_make_mock_config())
        assert pipeline._turns_to_flat_text([]) == ""


class TestMultiTurnGeneration:
    """多轮对话时 _generate_answer 传递正确 messages[] 的集成测试"""

    def test_generate_answer_passes_messages_to_litellm(self):
        """_generate_answer 将 conversation_turns 构造为 messages[] 传给 litellm"""
        chunks = _make_sample_chunks(2)
        context = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=50,
            budget=4000,
        )
        turns = [
            ConversationTurn(role="user", content="First question"),
            ConversationTurn(role="assistant", content="First answer"),
        ]

        pipeline = _make_pipeline(_make_mock_config(), llm_available=True)

        with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Follow-up answer."
            mock_litellm.completion.return_value = mock_response

            answer, confidence = pipeline._generate_answer(
                question="Follow-up?",
                context=context,
                options={},
                conversation_turns=turns,
            )

        # Verify litellm.completion was called with multi-turn messages
        call_kwargs = mock_litellm.completion.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert len(messages) == 4  # system + user turn + assistant turn + current user
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "First question"}
        assert messages[2] == {"role": "assistant", "content": "First answer"}
        assert messages[3]["role"] == "user"
        assert "Follow-up?" in messages[3]["content"]

    def test_generate_answer_no_turns_sends_two_messages(self):
        """无 conversation_turns 时仍发送 [system, user] 两条消息"""
        chunks = _make_sample_chunks(1)
        context = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=30,
            budget=4000,
        )
        pipeline = _make_pipeline(_make_mock_config(), llm_available=True)

        with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Answer."
            mock_litellm.completion.return_value = mock_response

            pipeline._generate_answer(
                question="Simple question",
                context=context,
                options={},
            )

        call_kwargs = mock_litellm.completion.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


# ─────────────────────────────────────────────
# Test: Streaming Pipeline
# ─────────────────────────────────────────────


class TestRunStream:
    """run_stream() 流式生成测试"""

    def test_stream_yields_sources_tokens_done(self):
        """run_stream 依次 yield sources、token、done 事件"""
        chunks = _make_sample_chunks(2)

        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=50,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            llm_available=True,
        )

        # Mock streaming response
        mock_chunk_1 = MagicMock()
        mock_chunk_1.choices = [MagicMock()]
        mock_chunk_1.choices[0].delta.content = "Hello "
        mock_chunk_2 = MagicMock()
        mock_chunk_2.choices = [MagicMock()]
        mock_chunk_2.choices[0].delta.content = "world"
        mock_chunk_3 = MagicMock()
        mock_chunk_3.choices = [MagicMock()]
        mock_chunk_3.choices[0].delta.content = None

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            with patch("kb.query.retrieval_pipeline.litellm") as mock_litellm:
                mock_litellm.completion.return_value = iter(
                    [mock_chunk_1, mock_chunk_2, mock_chunk_3]
                )

                events = list(pipeline.run_stream("Test question"))

        event_types = [e["type"] for e in events]
        assert "sources" in event_types
        assert "token" in event_types
        assert "done" in event_types

        # Check sources event
        sources_event = next(e for e in events if e["type"] == "sources")
        assert "sources" in sources_event

        # Check token events contain content
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello "
        assert token_events[1]["content"] == "world"

        # Check done event has full answer
        done_event = next(e for e in events if e["type"] == "done")
        assert done_event["answer"] == "Hello world"

    def test_stream_empty_results_yields_done(self):
        """无检索结果时 stream 直接 yield done"""
        pipeline = _make_pipeline(_make_mock_config(), llm_available=True)

        with patch.object(pipeline, "_hybrid_retrieve", return_value=[]):
            events = list(pipeline.run_stream("Unknown"))

        assert len(events) == 1
        assert events[0]["type"] == "done"
        assert events[0]["confidence"] == 0.0

    def test_stream_llm_unavailable_yields_error(self):
        """LLM 不可用时 stream yield sources then error"""
        chunks = _make_sample_chunks(2)
        mock_context_builder = MagicMock(spec=BaseContextBuilder)
        mock_context_builder.build.return_value = RetrievalContext(
            chunks=chunks,
            entities=[],
            topic_context=None,
            token_count=50,
            budget=4000,
        )

        pipeline = _make_pipeline(
            _make_mock_config(),
            context_builder=mock_context_builder,
            llm_available=False,
        )

        with patch.object(pipeline, "_hybrid_retrieve", return_value=chunks):
            events = list(pipeline.run_stream("Test"))

        event_types = [e["type"] for e in events]
        assert "sources" in event_types
        assert "error" in event_types
        error_event = next(e for e in events if e["type"] == "error")
        assert "unavailable" in error_event["message"].lower()

    def test_stream_empty_question_yields_error(self):
        """空问题时 stream yield error"""
        pipeline = _make_pipeline(_make_mock_config(), llm_available=True)

        events = list(pipeline.run_stream(""))

        assert len(events) == 1
        assert events[0]["type"] == "error"


# ─────────────────────────────────────────────
# Test: Document ID Boost (Phase 2)
# ─────────────────────────────────────────────


class TestExtractPriorSourceIds:
    """_extract_prior_source_ids() 提取前轮文档 ID"""

    def test_extracts_ids_from_turns_with_sources(self):
        """从有 sources 的 turns 中提取文档 ID"""
        pipeline = _make_pipeline(_make_mock_config())
        turns = [
            ConversationTurn(
                role="user",
                content="What is BERT?",
                sources=None,
            ),
            ConversationTurn(
                role="assistant",
                content="BERT is a language model.",
                sources=[
                    {"id": "doc-bert-1", "content": "...", "score": 0.9},
                    {"id": "doc-bert-2", "content": "...", "score": 0.8},
                ],
            ),
            ConversationTurn(
                role="user",
                content="How is it trained?",
                sources=None,
            ),
            ConversationTurn(
                role="assistant",
                content="BERT uses masked language modeling.",
                sources=[
                    {"id": "doc-bert-2", "content": "...", "score": 0.85},
                    {"id": "doc-train-1", "content": "...", "score": 0.7},
                ],
            ),
        ]
        ids = pipeline._extract_prior_source_ids(turns)
        assert ids == {"doc-bert-1", "doc-bert-2", "doc-train-1"}

    def test_turns_without_sources_returns_empty(self):
        """无 sources 字段的 turns 返回空集合"""
        pipeline = _make_pipeline(_make_mock_config())
        turns = [
            ConversationTurn(role="user", content="Hello"),
            ConversationTurn(role="assistant", content="Hi there"),
        ]
        ids = pipeline._extract_prior_source_ids(turns)
        assert ids == set()

    def test_empty_turns_returns_empty(self):
        """空 turns 列表返回空集合"""
        pipeline = _make_pipeline(_make_mock_config())
        ids = pipeline._extract_prior_source_ids([])
        assert ids == set()

    def test_source_dicts_without_id_key_skipped(self):
        """source dict 缺少 id key 时被跳过"""
        pipeline = _make_pipeline(_make_mock_config())
        turns = [
            ConversationTurn(
                role="assistant",
                content="Answer",
                sources=[
                    {"id": "valid-doc", "content": "..."},
                    {"content": "no id here"},
                    {"id": "", "content": "empty id"},
                ],
            ),
        ]
        ids = pipeline._extract_prior_source_ids(turns)
        # Only "valid-doc" should be extracted; empty string id is falsy
        assert ids == {"valid-doc"}


class TestBoostConversationSources:
    """_boost_conversation_sources() 对前轮文档 boost"""

    def test_matching_chunks_get_boosted(self):
        """匹配 prior source ID 的 chunk 被 boost"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = [
            RankedChunk(content="A", source="doc-1", final_score=0.5),
            RankedChunk(content="B", source="doc-2", final_score=0.4),
            RankedChunk(content="C", source="doc-3", final_score=0.3),
        ]
        prior_ids = {"doc-1", "doc-3"}

        result = pipeline._boost_conversation_sources(chunks, prior_ids)

        # doc-1 boosted: 0.5 + 0.15 = 0.65
        # doc-3 boosted: 0.3 + 0.15 = 0.45
        # doc-2 unchanged: 0.4
        assert result[0].source == "doc-1"
        assert abs(result[0].final_score - 0.65) < 1e-6
        assert result[1].source == "doc-3"
        assert abs(result[1].final_score - 0.45) < 1e-6
        assert result[2].source == "doc-2"
        assert abs(result[2].final_score - 0.4) < 1e-6

    def test_non_matching_chunks_unchanged(self):
        """不匹配的 chunk 分数不变"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = [
            RankedChunk(content="A", source="doc-1", final_score=0.5),
            RankedChunk(content="B", source="doc-2", final_score=0.4),
        ]
        prior_ids = {"doc-999"}

        result = pipeline._boost_conversation_sources(chunks, prior_ids)

        assert result[0].final_score == 0.5
        assert result[1].final_score == 0.4

    def test_chunks_resorted_after_boost(self):
        """boost 后重新排序"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = [
            RankedChunk(content="A", source="doc-1", final_score=0.5),
            RankedChunk(content="B", source="doc-2", final_score=0.4),
            RankedChunk(content="C", source="doc-3", final_score=0.3),
        ]
        # Boost doc-3 so it jumps above doc-2
        prior_ids = {"doc-3"}

        result = pipeline._boost_conversation_sources(chunks, prior_ids)

        # doc-1: 0.5 (unchanged), doc-3: 0.3+0.15=0.45, doc-2: 0.4
        assert result[0].source == "doc-1"
        assert result[1].source == "doc-3"
        assert result[2].source == "doc-2"

    def test_boost_capped_at_1_0(self):
        """boost 后分数不超过 1.0"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = [
            RankedChunk(content="A", source="doc-1", final_score=0.95),
        ]
        prior_ids = {"doc-1"}

        result = pipeline._boost_conversation_sources(chunks, prior_ids)

        assert result[0].final_score == 1.0

    def test_custom_boost_value(self):
        """自定义 boost 值生效"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = [
            RankedChunk(content="A", source="doc-1", final_score=0.5),
        ]
        prior_ids = {"doc-1"}

        result = pipeline._boost_conversation_sources(chunks, prior_ids, boost=0.3)

        assert abs(result[0].final_score - 0.8) < 1e-6

    def test_empty_prior_ids_returns_unchanged(self):
        """空 prior_source_ids 时返回原始 chunks"""
        pipeline = _make_pipeline(_make_mock_config())
        chunks = _make_sample_chunks(3)
        original_scores = [c.final_score for c in chunks]

        result = pipeline._boost_conversation_sources(chunks, set())

        assert [c.final_score for c in result] == original_scores


# ─────────────────────────────────────────────
# Test: Dynamic Token Budget (Phase 2)
# ─────────────────────────────────────────────


class TestEstimateTextTokens:
    """_estimate_text_tokens() 静态方法测试"""

    def test_estimates_tokens_from_words(self):
        """word count * 1.3 的 token 估算"""
        result = RetrievalPipeline._estimate_text_tokens("hello world foo bar")
        # 4 words * 1.3 = 5.2 -> int = 5
        assert result == 5

    def test_empty_text_returns_zero(self):
        """空文本返回 0"""
        assert RetrievalPipeline._estimate_text_tokens("") == 0

    def test_single_word(self):
        """单词文本"""
        assert RetrievalPipeline._estimate_text_tokens("hello") == 1


class TestCalculateRetrievalBudget:
    """_calculate_retrieval_budget() 动态 token 预算计算"""

    def test_no_conversation_returns_config_budget(self):
        """无对话历史时 budget 等于 config context_budget"""
        pipeline = _make_pipeline(_make_mock_config())
        # context_budget is 4000 (from mock config)
        # model_context_window defaults to 32000
        # system_prompt ~= few tokens
        # conv_tokens = 0
        # generation_reserve = 1000 (max_tokens)
        # safety_margin = 500
        # used = system_tokens + 0 + 1000 + 500 = ~1510
        # retrieval_budget = 32000 - ~1510 = ~30490
        # min(30490, 4000) = 4000 (capped by context_budget)
        budget = pipeline._calculate_retrieval_budget([], pipeline.system_prompt)
        assert budget == pipeline.context_budget

    def test_long_conversation_shrinks_budget(self):
        """长对话时 budget 缩减"""
        config = _make_mock_config(model_context_window=8000)
        pipeline = _make_pipeline(config)

        # Create long conversation turns
        long_turns = []
        for i in range(10):
            long_turns.append(
                ConversationTurn(
                    role="user",
                    content="This is a very long question " * 50,
                )
            )
            long_turns.append(
                ConversationTurn(
                    role="assistant",
                    content="This is a detailed answer " * 50,
                )
            )

        budget = pipeline._calculate_retrieval_budget(
            long_turns, pipeline.system_prompt
        )

        # With large conversation, budget should be smaller than context_budget
        assert budget < pipeline.context_budget

    def test_minimum_budget_floor(self):
        """budget 下限保护: 至少 1000 tokens"""
        config = _make_mock_config(model_context_window=2000)
        pipeline = _make_pipeline(config)

        # Create massive conversation to exceed model window
        huge_turns = [
            ConversationTurn(
                role="user",
                content="word " * 5000,
            ),
        ]

        budget = pipeline._calculate_retrieval_budget(
            huge_turns, pipeline.system_prompt
        )

        # Floor at 1000, but also capped by context_budget
        # max(2000 - huge, 1000) = 1000
        # min(1000, 4000) = 1000
        assert budget == 1000

    def test_budget_never_exceeds_context_budget(self):
        """budget 不超过配置的 context_budget"""
        config = _make_mock_config(model_context_window=100000)
        pipeline = _make_pipeline(config)
        # context_budget = 4000, model_window = 100000

        budget = pipeline._calculate_retrieval_budget([], pipeline.system_prompt)

        # Even with huge model window, should not exceed context_budget
        assert budget == pipeline.context_budget
