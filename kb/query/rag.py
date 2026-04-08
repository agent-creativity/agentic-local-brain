"""
RAG Query Module

Retrieval-Augmented Generation query functionality.
Combines semantic search with large language models for intelligent Q&A.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    import litellm
except ImportError:
    litellm = None

from kb.config import Config
from kb.query.semantic_search import SemanticSearch
from kb.query.models import RAGResult, SearchResult

logger = logging.getLogger(__name__)


# Default system prompt template
DEFAULT_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions based on provided context.
Please follow these principles:
1. Only use the provided context to answer questions
2. If there is not enough information in the context, clearly state so
3. Be accurate, concise, and organized
4. Synthesize information from multiple sources
5. Cite sources at the end of your answer"""

# User prompt template
USER_PROMPT_TEMPLATE = """Context:
{context}

Question: {question}

Please answer the question based on the above context."""


class RAGQuery:
    """
    RAG Query Class

    Implements retrieval-augmented generation query functionality. Workflow:
    1. Retrieve relevant documents using semantic search
    2. Build context from retrieved documents
    3. Call LLM to generate answer
    4. Return result containing answer and source citations

    Usage example:
        >>> from kb.config import Config
        >>> from kb.query.rag import RAGQuery
        >>> config = Config()
        >>> rag = RAGQuery(config)
        >>> result = rag.query("How to install Python?", tags=["python"], top_k=5)
        >>> print(result.answer)
        >>> print(f"Sources: {result.get_source_ids()}")
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize RAG query handler

        Reads LLM and query configuration, creates SemanticSearch instance.
        If LLM or semantic search initialization fails, the object remains
        usable in degraded mode via query_with_fallback().

        Args:
            config: Configuration object containing llm and query settings
        """
        self.config = config

        # Get query configuration
        query_config = config.get("query", {})
        rag_config = query_config.get("rag", {})

        self.top_k = rag_config.get("top_k", 5)
        self.temperature = rag_config.get("temperature", 0.3)
        self.max_tokens = rag_config.get("max_tokens", 1000)
        self.system_prompt = rag_config.get(
            "system_prompt", DEFAULT_SYSTEM_PROMPT
        )

        # Initialize semantic search gracefully
        self.semantic_search = None
        try:
            self.semantic_search = SemanticSearch(config)
        except Exception as e:
            logger.warning(f"Semantic search initialization failed: {e}. "
                          "RAG will operate in degraded mode.")

        # Initialize LLM client gracefully
        self.llm_available = False
        self.llm_provider = None
        self.model = None
        try:
            self._init_llm_client()
            self.llm_available = True
        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}. "
                          "RAG will operate in degraded mode without answer generation.")
            self.llm_available = False
            self.llm_provider = None

        logger.info(
            f"RAGQuery initialized with top_k={self.top_k}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}, "
            f"llm_available={self.llm_available}"
        )

    def _init_llm_client(self) -> None:
        """
        Initialize LLM client

        Supports three provider modes, all using litellm:
        - "litellm": use litellm SDK directly with litellm model format
        - "dashscope": backward-compatible, maps to litellm dashscope/model format
        - "openai_compatible": backward-compatible, maps to litellm openai/model with api_base

        Raises:
            ValueError: Invalid LLM configuration
            ImportError: litellm not installed
        """
        if litellm is None:
            raise ImportError(
                "litellm package is required for LLM. "
                "Install it with: pip install litellm"
            )

        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "dashscope")
        api_key = llm_config.get("api_key", "")

        if not api_key:
            raise ValueError("API key is required in LLM configuration")

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
            logger.info(f"Using litellm for dashscope provider: {self.model}")

        elif provider == "openai_compatible":
            base_url = llm_config.get("base_url", "")
            model = llm_config.get("model", "")
            if not model:
                raise ValueError("Model is required for openai_compatible provider")
            self.model = model if "/" in model else f"openai/{model}"
            self.api_key = api_key
            self.api_base = base_url or None
            self.llm_provider = "litellm"
            logger.info(f"Using litellm for openai_compatible: {self.model} at {base_url}")

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def query(
        self,
        question: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> RAGResult:
        """
        Execute RAG query

        Full RAG query workflow: semantic search → build context → LLM generates answer.

        Args:
            question: User question
            tags: Tag filter list, if provided only search documents with these tags
            top_k: Number of documents to retrieve, uses config default if not provided
            temperature: LLM generation temperature (0-1), controls randomness,
                        uses config default if not provided
            max_tokens: Maximum tokens for LLM generation,
                       uses config default if not provided

        Returns:
            RAGResult: Query result containing answer and source citations

        Raises:
            ValueError: Question is empty or LLM service is unavailable
            Exception: Error during query execution
        """
        if not self.llm_available:
            raise ValueError("LLM service is not available. Use query_with_fallback() for degraded mode.")

        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        # Use config defaults
        if top_k is None:
            top_k = self.top_k
        if temperature is None:
            temperature = self.temperature
        if max_tokens is None:
            max_tokens = self.max_tokens

        try:
            # 1. Semantic search for relevant documents
            logger.debug(f"Searching for: {question[:50]}...")
            search_results = self.semantic_search.search(
                query=question,
                tags=tags,
                top_k=top_k,
            )

            if not search_results:
                logger.warning("No relevant documents found")
                return RAGResult(
                    answer="Sorry, I couldn't find relevant information in the knowledge base to answer this question.",
                    sources=[],
                    context="",
                    question=question,
                )

            # 2. Build context
            context = self._build_context(search_results)

            # 3. Call LLM to generate answer
            logger.debug(f"Generating answer with {len(search_results)} sources")
            answer = self._generate_answer(
                question=question,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 4. Build and return result
            result = RAGResult(
                answer=answer,
                sources=search_results,
                context=context,
                question=question,
            )

            logger.info(
                f"RAG query completed: {len(search_results)} sources used"
            )
            return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise Exception(f"RAG query failed: {e}")

    def _build_context(self, results: List[SearchResult]) -> str:
        """
        Build LLM context from search results

        Args:
            results: List of search results

        Returns:
            str: Formatted context text
        """
        context_parts = []

        for i, result in enumerate(results, 1):
            source_info = f"[Source {i}]"
            if result.metadata.get("source"):
                source_info += f" - {result.metadata['source']}"
            if result.metadata.get("tags"):
                tags = ", ".join(result.metadata["tags"])
                source_info += f" (tags: {tags})"

            context_parts.append(
                f"{source_info}\n{result.content}\n"
            )

        return "\n".join(context_parts)

    def _generate_answer(
        self,
        question: str,
        context: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call LLM to generate answer

        Args:
            question: User question
            context: Retrieved context
            temperature: Generation temperature
            max_tokens: Maximum token count

        Returns:
            str: LLM-generated answer

        Raises:
            Exception: LLM call failed
        """
        try:
            return self._call_litellm(
                question=question,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _call_litellm(
        self,
        question: str,
        context: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call LLM via litellm SDK

        Args:
            question: User question
            context: Retrieved context
            temperature: Generation temperature
            max_tokens: Maximum token count

        Returns:
            str: LLM-generated answer

        Raises:
            Exception: API call failed
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        context=context, question=question
                    ),
                },
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "api_key": self.api_key,
            }
            if self.api_base:
                kwargs["api_base"] = self.api_base

            response = litellm.completion(**kwargs)
            answer = response.choices[0].message.content
            return answer

        except Exception as e:
            logger.error(f"LiteLLM API call failed: {e}")
            raise

    def query_with_fallback(
        self,
        question: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> RAGResult:
        """
        Execute RAG query with progressive fallback

        Progressive degradation: RAG -> semantic only -> keyword only -> error message.
        This method always returns a result, even if all search methods fail.

        Args:
            question: User question
            tags: Tag filter list
            top_k: Number of documents to retrieve

        Returns:
            RAGResult: Query result with progressive fallback
        """
        effective_top_k = top_k or self.top_k

        semantic_error = None
        keyword_error = None
        had_any_search = False

        # Level 1: Full RAG (LLM + semantic search)
        if self.llm_available:
            try:
                return self.query(question, tags, top_k)
            except Exception as e:
                logger.warning(f"RAG query failed: {e}. Trying semantic search fallback.")

        # Level 2: Semantic search only (no LLM answer generation)
        if self.semantic_search is not None:
            try:
                search_results = self.semantic_search.search(question, tags, effective_top_k)
                had_any_search = True
                if search_results:
                    context = self._build_context(search_results)
                    return RAGResult(
                        answer=f"[LLM unavailable] Found {len(search_results)} relevant documents. "
                               f"Showing search results without AI-generated answer.",
                        sources=search_results,
                        context=context,
                        question=question
                    )
            except Exception as e:
                semantic_error = e
                logger.warning(f"Semantic search fallback failed: {e}. Trying keyword search.")

        # Level 3: Keyword search only
        try:
            from kb.query.keyword_search import KeywordSearch
            kw_search = KeywordSearch(data_dir=str(self.config.data_dir))
            search_results = kw_search.search(keywords=question, limit=effective_top_k)
            had_any_search = True
            if search_results:
                return RAGResult(
                    answer=f"[LLM and semantic search unavailable] Found {len(search_results)} "
                           f"documents via keyword search.",
                    sources=search_results,
                    context="",
                    question=question
                )
        except Exception as e:
            keyword_error = e
            logger.warning(f"Keyword search fallback failed: {e}")

        # Searches ran but found nothing
        if had_any_search and semantic_error is None and keyword_error is None:
            return RAGResult(
                answer="No relevant information was found in the knowledge base for this question.",
                sources=[],
                context="",
                question=question
            )

        # Level 4: All search methods truly failed/unavailable
        return RAGResult(
            answer="Query failed: all search methods are unavailable. "
                   "Please check your configuration with 'localbrain test embedding' and 'localbrain test llm'.",
            sources=[],
            context="",
            question=question
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get RAG query handler statistics

        Returns:
            Dict[str, Any]: Configuration and storage statistics
        """
        try:
            search_stats = self.semantic_search.get_stats()
            return {
                "llm_provider": self.llm_provider,
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_k": self.top_k,
                "search_stats": search_stats,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "llm_provider": self.llm_provider,
                "model": self.model,
                "error": str(e),
            }
