"""
Query expansion for improved retrieval recall.

This module provides query expansion capabilities to rewrite and
enrich user queries before retrieval, improving recall for
complex or ambiguous questions.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import litellm
except ImportError:
    litellm = None

logger = logging.getLogger(__name__)


@dataclass
class ExpandedQuery:
    """
    Result of query expansion.

    Contains the original query along with any rewrites, extracted
    entities, and identified intent for improved retrieval.

    Attributes:
        original: The original user query
        rewrites: List of rewritten query variants
        entities: List of extracted entity names
        intent: Optional identified query intent
    """

    original: str
    rewrites: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    intent: Optional[str] = None


class BaseQueryExpander(ABC):
    """
    Abstract base class for query expansion implementations.

    Query expanders analyze and enrich user questions to improve
    retrieval recall. This can include:
    - Query rewriting for clarity
    - Entity extraction for focused search
    - Intent classification for routing
    - Synonym expansion for broader matching
    """

    @abstractmethod
    def expand(
        self,
        question: str,
        conversation_context: Optional[str] = None,
    ) -> ExpandedQuery:
        """
        Expand a query for improved retrieval.

        Args:
            question: The user question to expand
            conversation_context: Optional context from previous turns

        Returns:
            ExpandedQuery: The expansion result with rewrites and entities
        """
        pass


class NoOpQueryExpander(BaseQueryExpander):
    """
    Pass-through expander that returns the original query.

    Used as a default when LLM-based expansion is not available
    or disabled. Returns the query unchanged without enrichment.
    """

    def expand(
        self,
        question: str,
        conversation_context: Optional[str] = None,
    ) -> ExpandedQuery:
        """
        Return the original query without expansion.

        Args:
            question: The user question
            conversation_context: Optional context (unused)

        Returns:
            ExpandedQuery: Result containing only the original query
        """
        logger.debug("NoOpQueryExpander returning original query unchanged")
        return ExpandedQuery(original=question)


class LLMQueryExpander(BaseQueryExpander):
    """
    LLM-based query expander for intelligent query enrichment.

    Uses an LLM to analyze queries and extract:
    - Key entities (people, tools, technologies, concepts)
    - Core search intent
    - Alternative phrasings for better recall

    Implements graceful degradation: if LLM call fails or returns
    unparseable response, falls back to returning the original query.

    Usage example:
        >>> from kb.config import Config
        >>> from kb.query.query_expander import LLMQueryExpander
        >>> config = Config()
        >>> expander = LLMQueryExpander(config.to_dict())
        >>> result = expander.expand("How do I configure it?",
        ...                          conversation_context="Previous: User asked about Docker")
        >>> print(result.entities)  # ['Docker', 'configuration']
        >>> print(result.rewrites)  # Alternative phrasings
    """

    # Prompt template for query expansion
    EXPANSION_PROMPT_TEMPLATE = """Given this question: "{question}"
{context_section}
Analyze the query and extract:
1. Key entities (people, tools, technologies, concepts mentioned)
2. The core search intent in one sentence
3. Two alternative phrasings that might match different documents

Respond ONLY with valid JSON:
{{"entities": ["entity1", "entity2"], "intent": "the core intent", "rewrites": ["alternative phrasing 1", "alternative phrasing 2"]}}"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize LLM query expander.

        Args:
            config: Configuration dictionary containing llm settings.
                   Should have 'llm' key with provider, model, api_key, etc.
        """
        self.config = config
        self.llm_available = False
        self.model = None
        self.api_key = None
        self.api_base = None
        self.temperature = 0.3
        self.max_tokens = 300

        try:
            self._init_llm_client()
            self.llm_available = True
        except Exception as e:
            logger.warning(f"LLM query expander initialization failed: {e}. "
                          "Will operate in degraded mode (no-op fallback).")
            self.llm_available = False

    def _init_llm_client(self) -> None:
        """
        Initialize LLM client using litellm.

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
                "litellm package is required for LLM query expansion. "
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

        elif provider == "dashscope":
            model = llm_config.get("model", "qwen-plus")
            self.model = model if "/" in model else f"dashscope/{model}"
            self.api_key = api_key
            self.api_base = None
            logger.info(f"LLMQueryExpander using litellm for dashscope: {self.model}")

        elif provider == "openai_compatible":
            base_url = llm_config.get("base_url", "")
            model = llm_config.get("model", "")
            if not model:
                raise ValueError("Model is required for openai_compatible provider")
            self.model = model if "/" in model else f"openai/{model}"
            self.api_key = api_key
            self.api_base = base_url or None
            logger.info(f"LLMQueryExpander using litellm for openai_compatible: {self.model}")

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def expand(
        self,
        question: str,
        conversation_context: Optional[str] = None,
    ) -> ExpandedQuery:
        """
        Expand a query using LLM for improved retrieval.

        Analyzes the query to extract entities, intent, and generates
        alternative phrasings. If conversation context is provided,
        includes it for coreference resolution (e.g., resolving "it",
        "that paper" to actual entities).

        Args:
            question: The user question to expand
            conversation_context: Optional context from previous turns
                                 for coreference resolution

        Returns:
            ExpandedQuery: The expansion result with rewrites, entities,
                          and intent. Falls back to original query only
                          if LLM is unavailable or call fails.
        """
        if not self.llm_available:
            logger.debug("LLM not available, returning original query")
            return ExpandedQuery(original=question)

        if not question or not question.strip():
            logger.warning("Empty question provided to expander")
            return ExpandedQuery(original=question)

        try:
            # Build the expansion prompt
            prompt = self._build_prompt(question, conversation_context)

            # Call LLM for expansion
            response = self._call_llm(prompt)

            # Parse the response
            expansion_data = self._parse_response(response)

            # Build and return ExpandedQuery
            return ExpandedQuery(
                original=question,
                rewrites=expansion_data.get("rewrites", []),
                entities=expansion_data.get("entities", []),
                intent=expansion_data.get("intent"),
            )

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}. Returning original query.")
            return ExpandedQuery(original=question)

    def _build_prompt(
        self,
        question: str,
        conversation_context: Optional[str] = None,
    ) -> str:
        """
        Build the expansion prompt.

        Args:
            question: The user question
            conversation_context: Optional conversation context

        Returns:
            str: The formatted prompt
        """
        context_section = ""
        if conversation_context:
            context_section = f"\nPrevious conversation context:\n{conversation_context}\n"

        return self.EXPANSION_PROMPT_TEMPLATE.format(
            question=question,
            context_section=context_section,
        )

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM via litellm SDK.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            str: LLM response text

        Raises:
            Exception: If the API call fails
        """
        try:
            messages = [
                {"role": "user", "content": prompt},
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "api_key": self.api_key,
            }
            if self.api_base:
                kwargs["api_base"] = self.api_base

            response = litellm.completion(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LiteLLM API call failed: {e}")
            raise

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM JSON response.

        Args:
            response: Raw LLM response text

        Returns:
            Dict with 'entities', 'intent', 'rewrites' keys

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Clean up the response - extract JSON if wrapped in markdown
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            raise

        # Validate expected fields
        result = {
            "entities": data.get("entities", []),
            "intent": data.get("intent"),
            "rewrites": data.get("rewrites", []),
        }

        # Ensure lists are actually lists
        if not isinstance(result["entities"], list):
            result["entities"] = []
        if not isinstance(result["rewrites"], list):
            result["rewrites"] = []

        return result
