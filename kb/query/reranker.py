"""
LLM-based reranking for retrieval results.

This module provides reranking capabilities to improve the relevance
of retrieved chunks before passing them to answer generation.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

try:
    import litellm
except ImportError:
    litellm = None

from kb.query.models import RankedChunk

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """
    Abstract base class for reranking implementations.

    Rerankers reorder and rescore retrieved chunks based on their
    relevance to a specific question, improving precision over
    the initial retrieval scores.
    """

    @abstractmethod
    def rerank(
        self,
        question: str,
        chunks: List[RankedChunk],
        top_k: int = 5,
    ) -> List[RankedChunk]:
        """
        Rerank chunks by relevance to the question.

        Args:
            question: The user question
            chunks: List of chunks to rerank
            top_k: Number of top chunks to return

        Returns:
            List[RankedChunk]: Reranked chunks with updated scores
        """
        pass


class NoOpReranker(BaseReranker):
    """
    Pass-through reranker that returns chunks unchanged.

    Used as a default when LLM-based reranking is not available
    or disabled. Maintains the original order and scores.
    """

    def rerank(
        self,
        question: str,
        chunks: List[RankedChunk],
        top_k: int = 5,
    ) -> List[RankedChunk]:
        """
        Return chunks unchanged, limited to top_k.

        Args:
            question: The user question (unused)
            chunks: List of chunks to pass through
            top_k: Number of chunks to return

        Returns:
            List[RankedChunk]: Input chunks limited to top_k
        """
        logger.debug(f"NoOpReranker returning top {top_k} chunks unchanged")
        return chunks[:top_k]


class LLMReranker(BaseReranker):
    """
    LLM-based reranker that scores chunk relevance.

    Uses an LLM to score the relevance of each chunk to the question,
    then combines the LLM score with the original retrieval score
    for final ranking.

    Graceful degradation: if LLM scoring fails, returns chunks with
    neutral rerank_score (0.5) and recalculated final_score.
    """

    # Default weights for score combination
    DEFAULT_WEIGHT_RETRIEVAL = 0.4
    DEFAULT_WEIGHT_RERANK = 0.6

    # Truncation limit for chunk content in prompts
    CHUNK_TRUNCATE_LEN = 500

    # LLM parameters for consistent scoring
    LLM_TEMPERATURE = 0.1
    LLM_MAX_TOKENS = 200

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM reranker with config dict.

        Uses the 'llm' section for provider/model info and
        'query.rag.reranking' section for weights.

        Args:
            config: Configuration dictionary with 'llm' and optional
                   'query.rag.reranking' sections.
        """
        self.llm_available = False
        self.model: Optional[str] = None
        self.api_key: Optional[str] = None
        self.api_base: Optional[str] = None
        self.llm_provider: Optional[str] = None

        # Get reranking weights from config
        reranking_config = config.get("query", {}).get("rag", {}).get("reranking", {})
        self.weight_retrieval = reranking_config.get(
            "weight_retrieval", self.DEFAULT_WEIGHT_RETRIEVAL
        )
        self.weight_rerank = reranking_config.get(
            "weight_rerank", self.DEFAULT_WEIGHT_RERANK
        )

        # Validate weights
        if self.weight_retrieval + self.weight_rerank == 0:
            logger.warning(
                "Both reranking weights are 0, using defaults"
            )
            self.weight_retrieval = self.DEFAULT_WEIGHT_RETRIEVAL
            self.weight_rerank = self.DEFAULT_WEIGHT_RERANK

        # Initialize LLM client
        try:
            self._init_llm_client(config)
            self.llm_available = True
            logger.info(
                f"LLMReranker initialized with model={self.model}, "
                f"weights=(retrieval={self.weight_retrieval}, rerank={self.weight_rerank})"
            )
        except Exception as e:
            logger.warning(
                f"LLM reranker initialization failed: {e}. "
                "Reranking will use fallback behavior."
            )
            self.llm_available = False

    def _init_llm_client(self, config: Dict[str, Any]) -> None:
        """
        Initialize LLM client using the same pattern as rag.py.

        Supports three provider modes via litellm:
        - "litellm": use litellm SDK directly with litellm model format
        - "dashscope": backward-compatible, maps to litellm dashscope/model format
        - "openai_compatible": backward-compatible, maps to litellm openai/model with api_base

        Args:
            config: Configuration dict containing 'llm' section

        Raises:
            ValueError: Invalid LLM configuration
            ImportError: litellm not installed
        """
        if litellm is None:
            raise ImportError(
                "litellm package is required for LLM reranking. "
                "Install it with: pip install litellm"
            )

        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "dashscope")
        api_key = llm_config.get("api_key", "")

        if not api_key:
            raise ValueError("API key is required in LLM configuration for reranking")

        if provider == "litellm":
            self.model = llm_config.get("model", "dashscope/qwen-plus")
            self.api_key = api_key
            self.api_base = llm_config.get("base_url", None)
            self.llm_provider = "litellm"

        elif provider == "dashscope":
            model = llm_config.get("model", "qwen-plus")
            self.model = model if "/" in model else f"dashscope/{model}"
            self.api_key = api_key
            self.api_base = None
            self.llm_provider = "litellm"
            logger.debug(f"Using litellm for dashscope provider: {self.model}")

        elif provider == "openai_compatible":
            base_url = llm_config.get("base_url", "")
            model = llm_config.get("model", "")
            if not model:
                raise ValueError("Model is required for openai_compatible provider")
            self.model = model if "/" in model else f"openai/{model}"
            self.api_key = api_key
            self.api_base = base_url or None
            self.llm_provider = "litellm"
            logger.debug(
                f"Using litellm for openai_compatible: {self.model} at {base_url}"
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def rerank(
        self,
        question: str,
        chunks: List[RankedChunk],
        top_k: int = 5,
    ) -> List[RankedChunk]:
        """
        Rerank chunks using LLM relevance scoring.

        Uses batch scoring for efficiency, with fallback to individual
        scoring if batch fails. Gracefully degrades if all scoring fails.

        Args:
            question: The user question
            chunks: List of chunks to rerank
            top_k: Number of top chunks to return

        Returns:
            List[RankedChunk]: Reranked chunks with updated scores
        """
        if not chunks:
            return chunks

        if not self.llm_available:
            logger.debug("LLM not available, returning original order")
            return chunks[:top_k]

        start_time = time.time()

        try:
            # Try batch scoring first
            scores = self._batch_score(question, chunks)
        except Exception as e:
            logger.warning(f"Batch scoring failed: {e}, trying individual scoring")
            try:
                # Fallback to individual scoring
                scores = self._individual_score(question, chunks)
            except Exception as e2:
                logger.warning(
                    f"Individual scoring also failed: {e2}, "
                    "using neutral scores as fallback"
                )
                scores = [0.5] * len(chunks)

        # Apply scores and calculate final scores
        reranked_chunks = []
        for i, chunk in enumerate(chunks):
            rerank_score = scores[i] if i < len(scores) else 0.5
            final_score = (
                self.weight_retrieval * chunk.retrieval_score
                + self.weight_rerank * rerank_score
            )

            # Create new chunk with updated scores
            reranked_chunk = RankedChunk(
                content=chunk.content,
                source=chunk.source,
                retrieval_score=chunk.retrieval_score,
                rerank_score=rerank_score,
                final_score=final_score,
                metadata=chunk.metadata,
            )
            reranked_chunks.append(reranked_chunk)

        # Sort by final_score descending
        reranked_chunks.sort(key=lambda x: x.final_score, reverse=True)

        elapsed = time.time() - start_time
        logger.info(
            f"LLMReranker completed in {elapsed*1000:.1f}ms, "
            f"reranked {len(chunks)} chunks, returning top {top_k}"
        )

        return reranked_chunks[:top_k]

    def _batch_score(
        self, question: str, chunks: List[RankedChunk]
    ) -> List[float]:
        """
        Score all chunks in a single LLM call.

        More efficient than individual calls but may fail with
        long prompts.

        Args:
            question: The user question
            chunks: List of chunks to score

        Returns:
            List[float]: Normalized scores (0-1) for each chunk

        Raises:
            Exception: LLM call failed
        """
        # Build prompt with truncated chunks
        passages = []
        for i, chunk in enumerate(chunks, 1):
            truncated = chunk.content[: self.CHUNK_TRUNCATE_LEN]
            passages.append(f"Passage {i}: {truncated}")

        prompt = f"""Rate the relevance of each passage to the question on a scale of 0-10.

Question: {question}

{chr(10).join(passages)}

Respond ONLY with valid JSON: {{"scores": [score1, score2, ...]}}

Scores should be integers from 0 to 10, where:
- 0: Completely irrelevant
- 5: Moderately relevant
- 10: Highly relevant"""

        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.LLM_TEMPERATURE,
            "max_tokens": self.LLM_MAX_TOKENS,
            "api_key": self.api_key,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content

        # Parse JSON response
        return self._parse_scores(content, len(chunks))

    def _individual_score(
        self, question: str, chunks: List[RankedChunk]
    ) -> List[float]:
        """
        Score each chunk individually as fallback.

        Less efficient but more reliable for long content.

        Args:
            question: The user question
            chunks: List of chunks to score

        Returns:
            List[float]: Normalized scores (0-1) for each chunk
        """
        scores = []
        for chunk in chunks:
            truncated = chunk.content[: self.CHUNK_TRUNCATE_LEN]
            prompt = f"""Rate the relevance of this passage to the question on a scale of 0-10.

Question: {question}

Passage: {truncated}

Respond ONLY with a single integer from 0 to 10. No other text."""

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.LLM_TEMPERATURE,
                "max_tokens": 10,
                "api_key": self.api_key,
            }
            if self.api_base:
                kwargs["api_base"] = self.api_base

            response = litellm.completion(**kwargs)
            content = response.choices[0].message.content.strip()

            # Parse single score
            try:
                score = int(content)
                scores.append(max(0, min(10, score)) / 10.0)
            except ValueError:
                logger.warning(f"Failed to parse score '{content}', using 0.5")
                scores.append(0.5)

        return scores

    def _parse_scores(self, content: str, expected_count: int) -> List[float]:
        """
        Parse LLM JSON response into normalized scores.

        Args:
            content: Raw LLM response text
            expected_count: Expected number of scores

        Returns:
            List[float]: Normalized scores (0-1)

        Raises:
            ValueError: Parsing failed
        """
        # Try to extract JSON from response
        content = content.strip()

        # Handle potential markdown code blocks
        if "```" in content:
            # Extract content between code block markers
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if match:
                content = match.group(1)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nContent: {content}")

        if "scores" not in data:
            raise ValueError(f"Missing 'scores' key in response: {data}")

        raw_scores = data["scores"]

        if not isinstance(raw_scores, list):
            raise ValueError(f"'scores' is not a list: {raw_scores}")

        # Normalize and validate scores
        normalized = []
        for i, score in enumerate(raw_scores):
            try:
                val = float(score)
                # Clamp to 0-10 range then normalize to 0-1
                normalized.append(max(0.0, min(1.0, max(0.0, min(10.0, val)) / 10.0)))
            except (ValueError, TypeError):
                logger.warning(f"Invalid score at index {i}: {score}, using 0.5")
                normalized.append(0.5)

        # Pad or truncate to expected count
        while len(normalized) < expected_count:
            normalized.append(0.5)
        return normalized[:expected_count]
