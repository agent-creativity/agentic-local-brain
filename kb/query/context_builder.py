"""
Token-aware context assembly for RAG.

This module provides context building capabilities to assemble
retrieved chunks, entity context, and topic information into
a coherent context string within token budget constraints.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from kb.query.models import EntityContext, RankedChunk, RetrievalContext

logger = logging.getLogger(__name__)


class BaseContextBuilder(ABC):
    """
    Abstract base class for context assembly implementations.

    Context builders take ranked chunks and additional context
    (entities, topics) and assemble them into a coherent context
    string suitable for LLM input, respecting token budgets.
    """

    @abstractmethod
    def build(
        self,
        chunks: List[RankedChunk],
        entities: List[EntityContext],
        topic_context: Optional[str] = None,
        budget: int = 4000,
    ) -> RetrievalContext:
        """
        Assemble context within token budget.

        Args:
            chunks: Ranked chunks to include
            entities: Entity contexts to add
            topic_context: Optional topic context string
            budget: Maximum token budget

        Returns:
            RetrievalContext: Assembled context with token count
        """
        pass


class SimpleContextBuilder(BaseContextBuilder):
    """
    Basic context builder with flat concatenation.

    This implementation provides backward-compatible context building
    by simply concatenating chunks in order. Used as a default when
    hierarchical context building is not needed or available.
    """

    def build(
        self,
        chunks: List[RankedChunk],
        entities: List[EntityContext],
        topic_context: Optional[str] = None,
        budget: int = 4000,
    ) -> RetrievalContext:
        """
        Build context by flat concatenation of chunks.

        Assembles chunks in ranked order with source annotations.
        Simple word-based token estimation for budget tracking.

        Args:
            chunks: Ranked chunks to include
            entities: Entity contexts (included in metadata)
            topic_context: Optional topic context (prepended)
            budget: Maximum token budget (used for estimation)

        Returns:
            RetrievalContext: Assembled context with token count
        """
        context_parts = []

        # Add topic context if available
        if topic_context:
            context_parts.append(f"[Topic Context]\n{topic_context}\n")

        # Add entity context if available
        if entities:
            entity_text = self._format_entities(entities)
            context_parts.append(f"[Entities]\n{entity_text}\n")

        # Add chunks in order
        for i, chunk in enumerate(chunks):
            source_info = f"[Source {i + 1}] - {chunk.source}"
            context_parts.append(f"{source_info}\n{chunk.content}\n")

        context_text = "\n".join(context_parts)

        # Simple token estimation: ~1.3 tokens per word on average
        # This is a rough estimate; actual tokenization depends on the model
        word_count = len(context_text.split())
        token_estimate = int(word_count * 1.3)

        logger.debug(
            f"SimpleContextBuilder: {len(chunks)} chunks, "
            f"~{token_estimate} tokens (budget: {budget})"
        )

        return RetrievalContext(
            chunks=chunks,
            entities=entities,
            topic_context=topic_context,
            token_count=token_estimate,
            budget=budget,
        )

    def _format_entities(self, entities: List[EntityContext]) -> str:
        """Format entity list for context string."""
        lines = []
        for entity in entities:
            entity_line = f"- {entity.name} ({entity.entity_type})"
            if entity.relations:
                relations_str = ", ".join(
                    f"{r.get('type', 'related to')} {r.get('target', '')}"
                    for r in entity.relations[:3]  # Limit relations shown
                )
                entity_line += f" | {relations_str}"
            lines.append(entity_line)
        return "\n".join(lines)


class HierarchicalContextBuilder(BaseContextBuilder):
    """
    Builds hierarchical context with token budget management.

    This implementation provides structured context assembly with:
    - Topic context section (if available)
    - Retrieved sources section (primary content)
    - Related entities section (if available)

    The builder respects token budgets and applies progressive truncation
    to fit within constraints while maximizing information content.
    """

    # Token allocation percentages
    TOPIC_BUDGET_RATIO = 0.025  # ~2.5% for topic (~100 tokens of 4000)
    ENTITY_BUDGET_RATIO = 0.05  # ~5% for entities (~200 tokens of 4000)
    RESERVE_RATIO = 0.15  # Reserve 15% buffer for safety

    def __init__(self, budget: int = 4000):
        """
        Initialize the hierarchical context builder.

        Args:
            budget: Default token budget for context building
        """
        self.budget = budget

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Estimate token count using word-based heuristic.

        Uses a simple heuristic of ~1.3 tokens per word on average.
        This provides a reasonable estimate for budget tracking
        without requiring actual tokenization.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return int(len(text.split()) * 1.3)

    def build(
        self,
        chunks: List[RankedChunk],
        entities: List[EntityContext],
        topic_context: Optional[str] = None,
        budget: int = None,
    ) -> RetrievalContext:
        """
        Assemble context within token budget with hierarchical structure.

        Builds context in priority order:
        1. Topic context (if available, limited budget)
        2. Retrieved sources (primary content, gets most of budget)
        3. Related entities (remaining budget)

        Applies progressive truncation to fit within budget while
        preserving as much information as possible.

        Args:
            chunks: Ranked chunks to include
            entities: Entity contexts to add
            topic_context: Optional topic context string
            budget: Maximum token budget (uses self.budget if None)

        Returns:
            RetrievalContext: Assembled context with token count
        """
        effective_budget = budget or self.budget
        context_parts: List[str] = []
        included_chunks: List[RankedChunk] = []
        included_entities: List[EntityContext] = entities
        total_tokens = 0

        # === Section 1: Topic Context ===
        topic_section = self._build_topic_section(topic_context, effective_budget)
        if topic_section:
            topic_tokens = self._estimate_tokens(topic_section)
            total_tokens += topic_tokens
            context_parts.append(topic_section)
            logger.debug(f"Topic section: {topic_tokens} tokens")

        # Calculate remaining budget after topic
        remaining_budget = effective_budget - total_tokens

        # === Section 2: Retrieved Sources ===
        # Sources get most of the budget (minus reserve for entities)
        source_budget = int(remaining_budget * (1 - self.ENTITY_BUDGET_RATIO - self.RESERVE_RATIO))
        source_section, included_chunks, source_tokens = self._build_source_section(
            chunks, source_budget
        )
        if source_section:
            total_tokens += source_tokens
            context_parts.append(source_section)
            logger.debug(f"Source section: {source_tokens} tokens, {len(included_chunks)} chunks")

        # === Section 3: Related Entities ===
        # Entities get remaining budget
        entity_budget = effective_budget - total_tokens - int(effective_budget * self.RESERVE_RATIO)
        entity_section, included_entities, entity_tokens = self._build_entity_section(
            entities, entity_budget
        )
        if entity_section:
            total_tokens += entity_tokens
            context_parts.append(entity_section)
            logger.debug(f"Entity section: {entity_tokens} tokens, {len(included_entities)} entities")

        # Log summary
        logger.info(
            f"HierarchicalContextBuilder: {total_tokens}/{effective_budget} tokens used, "
            f"{len(included_chunks)}/{len(chunks)} chunks, "
            f"{len(included_entities)}/{len(entities)} entities"
        )

        return RetrievalContext(
            chunks=included_chunks,
            entities=included_entities,
            topic_context=topic_context,
            token_count=total_tokens,
            budget=effective_budget,
        )

    def _build_topic_section(
        self,
        topic_context: Optional[str],
        budget: int,
    ) -> Optional[str]:
        """
        Build the topic context section.

        Args:
            topic_context: Topic context string from enrichment
            budget: Maximum tokens for this section

        Returns:
            Formatted topic section or None if unavailable
        """
        if not topic_context:
            return None

        topic_budget = max(int(budget * self.TOPIC_BUDGET_RATIO), 50)  # At least 50 tokens

        # Format topic section
        section = f"## Topic Context\n{topic_context}"

        # Truncate if needed
        if self._estimate_tokens(section) > topic_budget:
            # Truncate content, keeping header
            max_content_tokens = topic_budget - 20  # Reserve for header
            max_content_words = int(max_content_tokens / 1.3)
            truncated_content = topic_context.split()[:max_content_words]
            section = f"## Topic Context\n{' '.join(truncated_content)}..."
            logger.debug(f"Topic context truncated to {topic_budget} tokens")

        return section

    def _build_source_section(
        self,
        chunks: List[RankedChunk],
        budget: int,
    ) -> tuple[Optional[str], List[RankedChunk], int]:
        """
        Build the retrieved sources section with progressive truncation.

        Adds chunks one by one until budget is ~80% used, then truncates
        the last chunk if needed to fit.

        Args:
            chunks: Ranked chunks to include
            budget: Maximum tokens for this section

        Returns:
            Tuple of (section text, included chunks, tokens used)
        """
        if not chunks:
            return None, [], 0

        included_chunks: List[RankedChunk] = []
        section_parts = ["## Retrieved Sources (ranked by relevance)", ""]
        current_tokens = self._estimate_tokens(section_parts[0]) + 1  # +1 for newline

        for i, chunk in enumerate(chunks):
            # Format chunk header
            tags_str = ", ".join(chunk.metadata.get("tags", [])) if chunk.metadata.get("tags") else "none"
            header = f"[Source {i + 1}] Source: {chunk.source} | Relevance: {chunk.final_score:.2f} | Tags: {tags_str}"
            content = chunk.content

            # Calculate tokens for this chunk
            chunk_text = f"{header}\n{content}\n"
            chunk_tokens = self._estimate_tokens(chunk_text)

            # Check if we can fit the full chunk
            if current_tokens + chunk_tokens <= budget * 0.8:
                # Full chunk fits
                included_chunks.append(chunk)
                section_parts.append(chunk_text)
                current_tokens += chunk_tokens
            elif current_tokens < budget * 0.9:
                # Try to fit a truncated version
                remaining_budget = budget - current_tokens - 10  # Small buffer
                if remaining_budget > 30:  # Need at least 30 tokens for partial content
                    # Reserve tokens for header
                    header_tokens = self._estimate_tokens(header)
                    content_budget = remaining_budget - header_tokens

                    if content_budget > 20:
                        # Truncate content to fit
                        max_words = int(content_budget / 1.3)
                        truncated_content = " ".join(content.split()[:max_words])
                        chunk_text = f"{header}\n{truncated_content}...\n"

                        # Create truncated chunk copy
                        truncated_chunk = RankedChunk(
                            content=truncated_content + "...",
                            source=chunk.source,
                            retrieval_score=chunk.retrieval_score,
                            rerank_score=chunk.rerank_score,
                            final_score=chunk.final_score,
                            metadata=chunk.metadata,
                        )
                        included_chunks.append(truncated_chunk)
                        section_parts.append(chunk_text)
                        current_tokens += self._estimate_tokens(chunk_text)
                        logger.debug(f"Chunk {i + 1} truncated to fit budget")
                break
            else:
                # Budget exhausted, skip remaining chunks
                logger.debug(f"Skipping {len(chunks) - i} chunks due to budget")
                break

        if len(section_parts) <= 2:  # Only header
            return None, [], 0

        section_text = "\n".join(section_parts)
        return section_text, included_chunks, current_tokens

    def _build_entity_section(
        self,
        entities: List[EntityContext],
        budget: int,
    ) -> tuple[Optional[str], List[EntityContext], int]:
        """
        Build the related entities section.

        Formats entities with their types, relations, and mention snippets.
        Truncates or skips entities if budget is exceeded.

        Args:
            entities: Entity contexts to include
            budget: Maximum tokens for this section

        Returns:
            Tuple of (section text, included entities, tokens used)
        """
        if not entities or budget < 30:  # Need at least 30 tokens for minimal section
            return None, [], 0

        section_parts = ["## Related Entities", ""]
        current_tokens = self._estimate_tokens(section_parts[0]) + 1
        included_entities: List[EntityContext] = []

        for entity in entities:
            # Format entity line
            entity_line = f"- {entity.name} ({entity.entity_type})"

            # Add relations if available
            if entity.relations:
                relations_str = ", ".join(
                    f"{r.get('type', 'related to')} {r.get('target', '')}"
                    for r in entity.relations[:3]
                )
                entity_line += f": Related to {relations_str}"

            # Add mention snippet if available and budget allows
            if entity.mentions and len(entity.mentions) > 0:
                mention = entity.mentions[0]
                if len(mention) > 50:
                    mention = mention[:50] + "..."
                entity_line += f'. Mentioned in: "{mention}"'

            entity_tokens = self._estimate_tokens(entity_line)

            # Check budget (with newline)
            if current_tokens + entity_tokens + 1 <= budget:
                included_entities.append(entity)
                section_parts.append(entity_line)
                current_tokens += entity_tokens + 1
            else:
                # Budget exhausted
                logger.debug(
                    f"Entity section stopped at {len(included_entities)}/{len(entities)} entities"
                )
                break

        if len(section_parts) <= 2:  # Only header
            return None, [], 0

        section_text = "\n".join(section_parts)
        return section_text, included_entities, current_tokens
