"""
Retrieval Pipeline - Multi-stage retrieval orchestrator for v0.7 RAG Enhanced Retrieval

This module implements a pluggable retrieval pipeline that orchestrates multiple stages:
1. Query Expansion - Rewrite and expand queries for better recall
2. Hybrid Retrieval - Combine semantic and keyword search
3. Reranking - LLM-based relevance scoring
4. Context Enrichment - Add entity and topic context
5. Context Building - Token-aware context assembly
6. Answer Generation - LLM-based answer synthesis
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from kb.config import Config
from kb.query.models import (
    EnhancedRAGResult,
    EntityContext,
    RankedChunk,
    RetrievalContext,
    SearchResult,
)
from kb.query.semantic_search import SemanticSearch
from kb.query.keyword_search import KeywordSearch
from kb.query.query_expander import ExpandedQuery, BaseQueryExpander, NoOpQueryExpander
from kb.query.reranker import BaseReranker, NoOpReranker
from kb.query.context_builder import BaseContextBuilder, SimpleContextBuilder, HierarchicalContextBuilder
from kb.query.conversation import ConversationManager
from kb.query.prompt_templates import PromptTemplateManager

try:
    import litellm
except ImportError:
    litellm = None

logger = logging.getLogger(__name__)

# Default system prompt for RAG (similar to rag.py)
DEFAULT_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions based on provided context.
Please follow these principles:
1. Only use the provided context to answer questions
2. If there is not enough information in the context, clearly state so
3. Be accurate, concise, and organized
4. Synthesize information from multiple sources
5. Cite sources at the end of your answer"""


class RetrievalPipeline:
    """
    Multi-stage retrieval pipeline orchestrator.

    This class coordinates all retrieval stages and allows for pluggable
    implementations of each stage. The pipeline can be called end-to-end
    even with no-op/default implementations for stages not yet implemented.

    Usage example:
        >>> from kb.config import Config
        >>> from kb.query.retrieval_pipeline import RetrievalPipeline
        >>> config = Config()
        >>> pipeline = RetrievalPipeline(config)
        >>> result = pipeline.run("What is machine learning?", top_k=5)
        >>> print(result.answer)
    """

    def __init__(
        self,
        config: Config,
        semantic_search: Optional[SemanticSearch] = None,
        keyword_search: Optional[KeywordSearch] = None,
        query_expander: Optional[BaseQueryExpander] = None,
        reranker: Optional[BaseReranker] = None,
        context_builder: Optional[BaseContextBuilder] = None,
        graph_query: Optional[Any] = None,
        topic_query: Optional[Any] = None,
        reading_history: Optional[Any] = None,
        conversation_manager: Optional[ConversationManager] = None,
        prompt_template_manager: Optional[PromptTemplateManager] = None,
    ) -> None:
        """
        Initialize the retrieval pipeline.

        Args:
            config: Configuration object
            semantic_search: Optional pre-configured SemanticSearch instance
            keyword_search: Optional pre-configured KeywordSearch instance
            query_expander: Optional query expander for query rewriting
            reranker: Optional reranker for result reranking
            context_builder: Optional context builder for LLM context assembly
            graph_query: Optional GraphQuery instance for entity enrichment
            topic_query: Optional TopicQuery instance for topic enrichment
            reading_history: Optional ReadingHistory instance for personalization
            prompt_template_manager: Optional manager for configurable prompt templates
        """
        self.config = config

        # Initialize search components
        self.semantic_search = semantic_search
        self.keyword_search = keyword_search

        # Initialize search if not provided
        if self.semantic_search is None:
            try:
                self.semantic_search = SemanticSearch(config)
                logger.debug("SemanticSearch initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize SemanticSearch: {e}")

        if self.keyword_search is None:
            try:
                self.keyword_search = KeywordSearch(data_dir=str(config.data_dir))
                logger.debug("KeywordSearch initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize KeywordSearch: {e}")

        # Pipeline components
        self.query_expander = query_expander
        self.reranker = reranker
        self.context_builder = context_builder

        # v0.7 knowledge-aware enrichment components
        self.graph_query = graph_query
        self.topic_query = topic_query
        self.reading_history = reading_history

        # Conversation manager for multi-turn support
        self.conversation_manager = conversation_manager

        # Prompt template manager for configurable templates
        if prompt_template_manager is None:
            try:
                self.prompt_template_manager = PromptTemplateManager(config.to_dict())
            except Exception as e:
                logger.warning(f"Failed to initialize PromptTemplateManager: {e}")
                self.prompt_template_manager = None
        else:
            self.prompt_template_manager = prompt_template_manager

        # Get pipeline configuration
        pipeline_config = config.get("query", {}).get("pipeline", {})
        self.default_top_k = pipeline_config.get("top_k", 10)
        self.rerank_top_k = pipeline_config.get("rerank_top_k", 5)
        self.context_budget = pipeline_config.get("context_budget", 4000)

        # Get RAG config for LLM generation
        rag_config = config.get("query", {}).get("rag", {})
        self.temperature = rag_config.get("temperature", 0.3)
        self.max_tokens = rag_config.get("max_tokens", 1000)
        self.system_prompt = rag_config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        
        # LLM configuration
        self.llm_available = False
        self._init_llm_config(config)

        logger.info(
            f"RetrievalPipeline initialized with top_k={self.default_top_k}, "
            f"rerank_top_k={self.rerank_top_k}, budget={self.context_budget}, "
            f"llm_available={self.llm_available}"
        )

    def _init_llm_config(self, config: Config) -> None:
        """Initialize LLM configuration from config.
        
        Args:
            config: Configuration object
        """
        if litellm is None:
            logger.warning("litellm not installed, LLM generation unavailable")
            return
        
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "dashscope")
        api_key = llm_config.get("api_key", "")
        
        if not api_key:
            logger.warning("No LLM API key configured")
            return
        
        try:
            if provider == "litellm":
                self.llm_model = llm_config.get("model", "dashscope/qwen-plus")
                self.llm_api_key = api_key
                self.llm_api_base = llm_config.get("base_url", None)
                self.llm_available = True
            elif provider == "dashscope":
                model = llm_config.get("model", "qwen-plus")
                self.llm_model = model if "/" in model else f"dashscope/{model}"
                self.llm_api_key = api_key
                self.llm_api_base = None
                self.llm_available = True
            elif provider == "openai_compatible":
                base_url = llm_config.get("base_url", "")
                model = llm_config.get("model", "")
                if model:
                    self.llm_model = model if "/" in model else f"openai/{model}"
                    self.llm_api_key = api_key
                    self.llm_api_base = base_url or None
                    self.llm_available = True
            else:
                logger.warning(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM config: {e}")

    def run(
        self,
        question: str,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        conversation_context: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> EnhancedRAGResult:
        """
        Execute the full retrieval pipeline.

        Runs all stages in sequence and returns an enhanced RAG result.
        Stages with no-op implementations will pass through defaults.

        If session_id is provided and conversation_manager is available,
        the pipeline will load conversation history and save new turns.
        If no session_id is provided but conversation_manager is available,
        a new session will be created automatically.

        Args:
            question: User question to answer
            session_id: Optional conversation session ID for multi-turn
            tags: Optional tag filters for retrieval
            top_k: Number of documents to retrieve (defaults to config)
            conversation_context: Optional context from previous conversation turns
            options: Optional dict of stage-specific options

        Returns:
            EnhancedRAGResult: Complete result with answer and metadata
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        effective_top_k = top_k or self.default_top_k
        options = options or {}
        pipeline_start = time.time()

        logger.info(f"Starting retrieval pipeline for: {question[:50]}...")
        stages_fired = []

        # Handle conversation session management
        is_new_session = False
        effective_session_id = session_id
        conversation_history = None
        history_turns = 0

        if self.conversation_manager is not None:
            # Create new session if no session_id provided
            if not effective_session_id:
                effective_session_id = self.conversation_manager.create_session()
                is_new_session = True
                logger.debug(f"Created new conversation session: {effective_session_id}")
            
            # Get conversation history for context injection
            try:
                rag_config = self.config.get("query", {}).get("rag", {})
                conv_config = rag_config.get("conversation", {})
                max_history_turns = conv_config.get("history_turns_in_context", 5)
                
                conversation_history = self.conversation_manager.format_history_for_prompt(
                    effective_session_id, max_turns=max_history_turns
                )
                
                # Count turns for turn_number
                session = self.conversation_manager.get_session(effective_session_id)
                if session:
                    history_turns = len(session.turns)
                
                if conversation_history:
                    logger.debug(f"Loaded {history_turns} turns of conversation history")
            except Exception as e:
                logger.warning(f"Failed to load conversation history: {e}")

        try:
            # Stage 1: Query Expansion (with conversation context if available)
            expansion_context = conversation_context or conversation_history
            expanded_query = self._expand_query(question, expansion_context)
            if expanded_query.rewrites or expanded_query.entities:
                stages_fired.append("query_expansion")
                logger.debug(
                    f"Query expanded: {len(expanded_query.rewrites)} rewrites, "
                    f"{len(expanded_query.entities)} entities"
                )

            # Stage 2: Hybrid Retrieval
            # Retrieve more candidates than final top_k for downstream reranking
            retrieval_top_k = max(effective_top_k * 2, 20)
            chunks = self._hybrid_retrieve(
                expanded_query=expanded_query,
                tags=tags,
                top_k=retrieval_top_k,
            )
            if chunks:
                stages_fired.append("hybrid_retrieval")
                logger.debug(f"Retrieved {len(chunks)} chunks via hybrid search")

            if not chunks:
                result = self._empty_result(question, effective_session_id)
                result.turn_number = history_turns // 2 + 1 if is_new_session else None
                return result

            # Stage 3: Reranking
            reranked_chunks = self._rerank(question, chunks, options)
            if reranked_chunks != chunks:
                stages_fired.append("reranking")
                logger.debug(f"Reranked to {len(reranked_chunks)} chunks")

            # Stage 4: Context Enrichment (entities, topics)
            entities, topic_context, enriched_chunks = self._enrich_context(
                question=question,
                chunks=reranked_chunks,
                options=options,
            )
            # Use enriched chunks (potentially boosted by reading history)
            reranked_chunks = enriched_chunks
            if entities or topic_context:
                stages_fired.append("context_enrichment")

            # Stage 5: Context Building
            retrieval_context = self._build_context(
                chunks=reranked_chunks,
                entities=entities,
                topic_context=topic_context,
                budget=self.context_budget,
                options=options,
            )
            stages_fired.append("context_building")

            # Stage 6: Answer Generation (with conversation history)
            answer, confidence = self._generate_answer(
                question=question,
                context=retrieval_context,
                options=options,
                conversation_history=conversation_history,
            )
            stages_fired.append("answer_generation")

            # Convert top chunks to SearchResult for result.sources
            top_chunks = reranked_chunks[:self.rerank_top_k]
            search_results = self._chunks_to_results(top_chunks)

            # Calculate turn number
            turn_number = (history_turns // 2) + 1 if effective_session_id else None

            # Build result
            result = EnhancedRAGResult(
                answer=answer,
                question=question,
                sources=search_results,
                context=self._context_to_string(retrieval_context),
                confidence=confidence,
                retrieval_strategy=",".join(stages_fired),
                reranked_sources=reranked_chunks[:self.rerank_top_k],
                entity_context=[e.__dict__ for e in entities] if entities else None,
                topic_context=topic_context,
                session_id=effective_session_id,
                turn_number=turn_number,
            )

            # Save conversation turns if conversation_manager is available
            if self.conversation_manager is not None and effective_session_id:
                try:
                    # Store full source data for conversation persistence
                    source_dicts = [s.to_dict() for s in search_results]
                    
                    # Add user turn
                    self.conversation_manager.add_turn(
                        session_id=effective_session_id,
                        role="user",
                        content=question,
                        sources=None
                    )
                    
                    # Add assistant turn
                    self.conversation_manager.add_turn(
                        session_id=effective_session_id,
                        role="assistant",
                        content=answer,
                        sources=source_dicts if source_dicts else None
                    )
                    
                    logger.debug(f"Saved conversation turns for session {effective_session_id}")
                except Exception as e:
                    logger.warning(f"Failed to save conversation turns: {e}")

            elapsed = time.time() - pipeline_start
            logger.info(f"Pipeline completed in {elapsed*1000:.1f}ms with stages: {stages_fired}")
            return result

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise

    def _expand_query(
        self,
        question: str,
        conversation_context: Optional[str] = None,
    ) -> ExpandedQuery:
        """
        Stage 1: Expand query for improved recall.

        Uses query expander to rewrite queries, extract entities,
        and add context from conversation history.

        Args:
            question: Original user question
            conversation_context: Optional context from previous conversation turns

        Returns:
            ExpandedQuery: The expanded query with rewrites and entities
        """
        if self.query_expander is None or isinstance(self.query_expander, NoOpQueryExpander):
            logger.debug("No query expander configured, using original query")
            return ExpandedQuery(original=question)

        try:
            start_time = time.time()
            expanded = self.query_expander.expand(question, conversation_context)
            elapsed = time.time() - start_time
            
            logger.debug(
                f"Query expansion completed in {elapsed*1000:.1f}ms: "
                f"{len(expanded.rewrites)} rewrites, {len(expanded.entities)} entities"
            )
            return expanded
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}, using original")
            return ExpandedQuery(original=question)

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[SearchResult]],
        k: int = 60,
    ) -> Dict[str, float]:
        """
        Compute Reciprocal Rank Fusion scores across multiple ranked lists.

        RRF combines multiple ranked lists by computing a fused score:
        RRF_score(d) = sum(1 / (k + rank_i(d))) for each ranker i

        This method favors documents that appear in multiple lists and
        appear at higher ranks, providing a robust fusion method.

        Args:
            result_lists: List of ranked result lists from different retrievers
            k: RRF constant (default 60, common in literature)

        Returns:
            Dict mapping document ID to RRF score
        """
        scores: Dict[str, float] = {}

        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                # Get document ID from result
                doc_id = result.id or result.metadata.get("source", "")
                if not doc_id:
                    continue

                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += 1.0 / (k + rank)

        return scores

    def _hybrid_retrieve(
        self,
        expanded_query: ExpandedQuery,
        tags: Optional[List[str]] = None,
        top_k: int = 20,
    ) -> List[RankedChunk]:
        """
        Stage 2: Hybrid retrieval combining semantic and keyword search.

        Combines results from both search methods using Reciprocal Rank Fusion
        for robust result merging. Retrieves more candidates than needed for
        downstream reranking.

        Args:
            expanded_query: The expanded query with original, rewrites, and entities
            tags: Optional tag filters
            top_k: Number of results to return (should be larger than final top_k
                   to allow for reranking)

        Returns:
            List[RankedChunk]: Combined and deduplicated results with RRF scores
        """
        start_time = time.time()
        result_lists: List[List[SearchResult]] = []

        # Step 1: Collect all query variants for semantic search
        query_variants = [expanded_query.original] + expanded_query.rewrites
        
        # Step 2: Run semantic search batch on all query variants
        if self.semantic_search:
            try:
                semantic_results = self.semantic_search.search_batch(
                    queries=query_variants,
                    tags=tags,
                    top_k=top_k,
                )
                if semantic_results:
                    result_lists.append(semantic_results)
                    logger.debug(f"Semantic search found {len(semantic_results)} results")
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")

        # Step 3: Run keyword search on original query + entities
        if self.keyword_search:
            try:
                # Combine original query with extracted entities for keyword search
                keyword_query_parts = [expanded_query.original]
                if expanded_query.entities:
                    keyword_query_parts.extend(expanded_query.entities)
                keyword_query = " ".join(keyword_query_parts)

                keyword_results = self.keyword_search.search(
                    keywords=keyword_query,
                    limit=top_k,
                )
                if keyword_results:
                    result_lists.append(keyword_results)
                    logger.debug(f"Keyword search found {len(keyword_results)} results")
            except Exception as e:
                logger.warning(f"Keyword search failed: {e}")

        # Handle case where no search methods returned results
        if not result_lists:
            logger.warning("No results from any search method")
            return []

        # Step 4: Apply Reciprocal Rank Fusion
        rrf_scores = self._reciprocal_rank_fusion(result_lists)

        # Step 5: Build result map for deduplication
        result_map: Dict[str, SearchResult] = {}
        for results in result_lists:
            for result in results:
                doc_id = result.id or result.metadata.get("source", "")
                if doc_id and doc_id not in result_map:
                    result_map[doc_id] = result

        # Step 6: Convert to RankedChunks with RRF scores
        chunks: List[RankedChunk] = []
        for doc_id, rrf_score in rrf_scores.items():
            if doc_id not in result_map:
                continue
            result = result_map[doc_id]
            chunk = RankedChunk(
                content=result.content,
                source=doc_id,
                retrieval_score=rrf_score,
                rerank_score=0.0,
                final_score=rrf_score,
                metadata=result.metadata,
            )
            chunks.append(chunk)

        # Step 7: Sort by final_score (RRF score) descending
        chunks.sort(key=lambda x: x.final_score, reverse=True)

        elapsed = time.time() - start_time
        logger.info(
            f"Hybrid retrieval completed in {elapsed*1000:.1f}ms: "
            f"{len(chunks)} results from {len(result_lists)} retrievers"
        )

        return chunks[:top_k]

    def _rerank(
        self,
        question: str,
        chunks: List[RankedChunk],
        options: Dict[str, Any],
    ) -> List[RankedChunk]:
        """
        Stage 3: Rerank chunks by relevance to question.

        Uses LLM-based reranker to reorder chunks by actual
        relevance to the specific question. If reranking is disabled
        or fails, returns chunks in original order.

        Args:
            question: User question
            chunks: List of chunks to rerank
            options: Stage-specific options

        Returns:
            List[RankedChunk]: Reranked chunks
        """
        # Check per-request toggle
        if not options.get('use_reranking', True):
            logger.debug("Reranking disabled via request options")
            return chunks

        if self.reranker is None:
            logger.debug("No reranker configured, returning original order")
            return chunks

        # Check if reranker is NoOpReranker (disabled)
        if isinstance(self.reranker, NoOpReranker):
            logger.debug("Reranking disabled (NoOpReranker), returning original order")
            return chunks

        # Get top_k from options or config
        rerank_top_k = options.get("rerank_top_k", self.rerank_top_k)

        start_time = time.time()
        try:
            reranked = self.reranker.rerank(question, chunks, rerank_top_k)
            elapsed = time.time() - start_time

            # Log reranking results
            if reranked and len(reranked) > 0:
                top_scores = [f"{c.final_score:.3f}" for c in reranked[:3]]
                logger.info(
                    f"Reranking completed in {elapsed*1000:.1f}ms: "
                    f"{len(reranked)} chunks, top scores: {top_scores}"
                )
            return reranked

        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(
                f"Reranking failed after {elapsed*1000:.1f}ms: {e}, "
                "returning original order"
            )
            return chunks

    def _enrich_context(
        self,
        question: str,
        chunks: List[RankedChunk],
        options: Dict[str, Any],
    ) -> Tuple[List[EntityContext], Optional[str], List[RankedChunk]]:
        """
        Stage 4: Enrich context with entities and topics.

        Extracts entities from chunks and adds topic context
        for better answer generation. Also applies reading history
        personalization by boosting chunks from recently viewed documents.

        Args:
            question: User question
            chunks: Retrieved chunks
            options: Stage-specific options
                - use_graph: Whether to use graph enrichment (default True)
                - use_topics: Whether to use topic enrichment (default True)
                - use_reading_history: Whether to apply reading history boost (default True)

        Returns:
            Tuple of (entity list, topic context string, potentially boosted chunks)
        """
        entities: List[EntityContext] = []
        topic_context: Optional[str] = None
        enriched_chunks = chunks  # Start with original chunks

        if not chunks:
            return entities, topic_context, enriched_chunks

        # Extract document IDs from chunks
        document_ids = list(set(chunk.source for chunk in chunks if chunk.source))

        if not document_ids:
            return entities, topic_context, enriched_chunks

        # === Graph Enrichment ===
        if options.get("use_graph", True) and self.graph_query is not None:
            try:
                entity_data = self.graph_query.get_entities_for_context(document_ids)
                if entity_data:
                    for ent in entity_data:
                        entity = EntityContext(
                            name=ent.get("display_name") or ent.get("name", ""),
                            entity_type=ent.get("type", "unknown"),
                            mentions=ent.get("mentions", []),
                            relations=[
                                {
                                    "type": r.get("relation_type"),
                                    "entity": r.get("related_entity", {}).get("name", ""),
                                }
                                for r in ent.get("relations", [])
                            ],
                        )
                        entities.append(entity)
                    logger.debug(
                        f"Enriched with {len(entities)} entities from knowledge graph"
                    )
            except Exception as e:
                logger.warning(f"Graph enrichment failed: {e}")

        # === Topic Enrichment ===
        if options.get("use_topics", True) and self.topic_query is not None:
            try:
                # Query topic assignments for the documents
                topic_counts: Dict[int, int] = {}
                topic_info: Dict[int, Dict[str, Any]] = {}

                # Get topics from storage via topic_query
                cursor = self.topic_query.storage.conn.cursor()
                try:
                    placeholders = ",".join("?" for _ in document_ids)
                    cursor.execute(
                        f"""SELECT kt.knowledge_id, kt.cluster_id, kt.confidence,
                                  tc.label, tc.description
                           FROM knowledge_topics kt
                           JOIN topic_clusters tc ON kt.cluster_id = tc.id
                           WHERE kt.knowledge_id IN ({placeholders})""",
                        document_ids,
                    )
                    for row in cursor.fetchall():
                        cluster_id = row["cluster_id"]
                        topic_counts[cluster_id] = topic_counts.get(cluster_id, 0) + 1
                        if cluster_id not in topic_info:
                            topic_info[cluster_id] = {
                                "label": row["label"],
                                "description": row["description"],
                            }
                finally:
                    cursor.close()

                # Find dominant topic (most frequent among retrieved docs)
                if topic_counts:
                    dominant_topic_id = max(topic_counts.keys(), key=lambda tid: topic_counts[tid])
                    info = topic_info.get(dominant_topic_id, {})
                    label = info.get("label", "")
                    description = info.get("description", "")
                    if label:
                        topic_context = f"Topic: {label}"
                        if description:
                            topic_context += f" - {description}"
                        logger.debug(f"Enriched with topic context: '{label}'")
            except Exception as e:
                logger.warning(f"Topic enrichment failed: {e}")

        # === Reading History Personalization ===
        if options.get("use_reading_history", True) and self.reading_history is not None:
            try:
                # Get recent document views
                recent_views = self.reading_history.get_recent_views(limit=20)
                if recent_views:
                    recently_viewed_ids = {
                        view["knowledge_id"] for view in recent_views if view.get("knowledge_id")
                    }

                    # Check if any retrieved chunks' documents overlap
                    boosted = False
                    for chunk in enriched_chunks:
                        if chunk.source in recently_viewed_ids:
                            # Boost the chunk's final_score by +0.1 (cap at 1.0)
                            chunk.final_score = min(1.0, chunk.final_score + 0.1)
                            boosted = True

                    if boosted:
                        # Re-sort chunks by final_score
                        enriched_chunks = sorted(
                            enriched_chunks, key=lambda c: c.final_score, reverse=True
                        )
                        logger.debug("Applied reading history personalization boost")
            except Exception as e:
                logger.warning(f"Reading history personalization failed: {e}")

        # Log what enrichment was applied
        enrichment_parts = []
        if entities:
            enrichment_parts.append(f"{len(entities)} entities")
        if topic_context:
            enrichment_parts.append(f"topic: '{topic_context.split(':')[1].split('-')[0].strip() if '-' in topic_context else topic_context.split(':')[1].strip()}'")
        if enriched_chunks != chunks:
            enrichment_parts.append("personalized boost")

        if enrichment_parts:
            logger.info(f"Context enrichment: {', '.join(enrichment_parts)}")

        return entities, topic_context, enriched_chunks

    def _build_context(
        self,
        chunks: List[RankedChunk],
        entities: List[EntityContext],
        topic_context: Optional[str],
        budget: int,
        options: Dict[str, Any],
    ) -> RetrievalContext:
        """
        Stage 5: Build token-aware context for LLM.

        Assembles the final context string from chunks, entities,
        and topic info within the token budget. Uses configured
        context format (hierarchical or flat) and budget.

        Args:
            chunks: Ranked chunks to include
            entities: Entity context to add
            topic_context: Topic context string
            budget: Token budget limit
            options: Stage-specific options

        Returns:
            RetrievalContext: Assembled context
        """
        # Get context configuration from query.rag section
        rag_config = self.config.get("query", {}).get("rag", {})
        context_budget = rag_config.get("context_budget", budget)
        context_format = rag_config.get("context_format", "hierarchical")

        # Determine which builder to use
        builder = self.context_builder
        if builder is None:
            if context_format == "flat":
                builder = SimpleContextBuilder()
                logger.debug("Using SimpleContextBuilder (flat format)")
            else:
                builder = HierarchicalContextBuilder(budget=context_budget)
                logger.debug(f"Using HierarchicalContextBuilder (hierarchical format) with budget {context_budget}")

        try:
            result = builder.build(
                chunks=chunks,
                entities=entities,
                topic_context=topic_context,
                budget=context_budget,
            )

            # Log token usage
            logger.info(
                f"Context built: {result.token_count}/{context_budget} tokens "
                f"({result.token_count / context_budget * 100:.1f}% of budget)"
            )

            return result

        except Exception as e:
            logger.warning(f"Context building failed: {e}, using empty context")
            return RetrievalContext(
                chunks=chunks,
                entities=entities,
                topic_context=topic_context,
                token_count=0,
                budget=context_budget,
            )

    def _calculate_confidence(
        self,
        chunks: List[RankedChunk],
        stages_fired: List[str],
    ) -> float:
        """Calculate answer confidence score (0-1).

        Formula: 0.5 * avg_rerank_score + 0.3 * source_coverage + 0.2 * strategy_completeness

        - avg_rerank_score: average of top chunks' rerank scores (or retrieval scores if no reranking)
        - source_coverage: min(num_sources / 3, 1.0) -- having 3+ sources = full coverage
        - strategy_completeness: 1.0 if full pipeline, 0.7 if no reranking, 0.4 if keyword-only

        Args:
            chunks: List of ranked chunks used to generate the answer
            stages_fired: List of pipeline stages that were executed

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not chunks:
            return 0.0

        # Calculate average score from top chunks
        # Use rerank_score if available (from reranking stage), else use final_score
        if "reranking" in stages_fired:
            scores = [c.rerank_score for c in chunks[:5] if c.rerank_score > 0]
            if not scores:  # Fallback if rerank scores are 0
                scores = [c.final_score for c in chunks[:5]]
        else:
            scores = [c.final_score for c in chunks[:5]]

        avg_score = sum(scores) / len(scores) if scores else 0.0
        # Normalize scores to 0-1 range if they might be unnormalized
        if avg_score > 1.0:
            avg_score = min(avg_score / 10.0, 1.0)  # Assume max around 10 for RRF scores

        # Source coverage: how many unique sources
        unique_sources = set(c.source for c in chunks)
        source_coverage = min(len(unique_sources) / 3.0, 1.0)

        # Strategy completeness
        if "reranking" in stages_fired and "hybrid_retrieval" in stages_fired:
            strategy_completeness = 1.0
        elif "hybrid_retrieval" in stages_fired:
            strategy_completeness = 0.7
        else:
            strategy_completeness = 0.4

        # Weighted combination
        confidence = (
            0.5 * avg_score +
            0.3 * source_coverage +
            0.2 * strategy_completeness
        )

        # Clamp to 0-1 range
        return max(0.0, min(1.0, confidence))

    def _generate_answer(
        self,
        question: str,
        context: RetrievalContext,
        options: Dict[str, Any],
        conversation_history: Optional[str] = None,
        template_name: Optional[str] = None,
    ) -> tuple[str, float]:
        """
        Stage 6: Generate answer using LLM with context and optional conversation history.

        Calls the LLM with the assembled context to generate
        the final answer with confidence score. If conversation_history
        is provided, includes it in the prompt for multi-turn context.

        Args:
            question: User question
            context: Assembled retrieval context
            options: Stage-specific options
                - template_name: Name of prompt template to use
            conversation_history: Optional formatted conversation history
            template_name: Optional prompt template name to use

        Returns:
            Tuple of (answer string, confidence score)
        """
        context_text = self._context_to_string(context)
        
        if not context_text:
            return "No relevant information found in the knowledge base.", 0.0

        # If LLM is not available, return a fallback response
        if not self.llm_available or litellm is None:
            logger.warning("LLM not available, returning fallback response")
            source_titles = []
            for chunk in context.chunks[:5]:
                title = chunk.metadata.get("title", chunk.source) if chunk.metadata else chunk.source
                source_titles.append(title)
            
            fallback = "Based on the retrieved sources, here are the relevant documents:\n\n"
            for i, title in enumerate(source_titles, 1):
                fallback += f"{i}. {title}\n"
            return fallback, 0.5

        # Get template name from options or parameter
        effective_template = template_name or options.get("template_name")

        # Format entity context if available
        entity_context_str = ""
        if context.entities:
            entity_lines = []
            for entity in context.entities:
                entity_lines.append(f"- {entity.name} ({entity.entity_type})")
                if entity.mentions:
                    entity_lines.append(f"  Mentions: {', '.join(entity.mentions[:3])}")
            entity_context_str = "\n".join(entity_lines)

        # Try to use PromptTemplateManager if available
        if self.prompt_template_manager is not None:
            try:
                user_prompt = self.prompt_template_manager.render(
                    template_name=effective_template,
                    context=context_text,
                    question=question,
                    conversation_history=conversation_history or "",
                    entity_context=entity_context_str,
                    topic_context=context.topic_context or "",
                )
                # Use a minimal system prompt since template contains the instructions
                system_prompt = "You are a helpful assistant."
            except Exception as e:
                logger.warning(f"Failed to render template: {e}, using fallback prompt")
                system_prompt = self.system_prompt
                if conversation_history:
                    system_prompt += (
                        "\n\nPrevious conversation:\n{history}\n\n"
                        "Continue the conversation based on the above context."
                    ).format(history=conversation_history)
                user_prompt = f"""Context:
{context_text}

Question: {question}

Please answer the question based on the above context."""
        else:
            # Fallback to legacy prompt construction
            system_prompt = self.system_prompt
            if conversation_history:
                system_prompt += (
                    "\n\nPrevious conversation:\n{history}\n\n"
                    "Continue the conversation based on the above context."
                ).format(history=conversation_history)
            user_prompt = f"""Context:
{context_text}

Question: {question}

Please answer the question based on the above context."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs = {
                "model": self.llm_model,
                "messages": messages,
                "temperature": options.get("temperature", self.temperature),
                "max_tokens": options.get("max_tokens", self.max_tokens),
                "api_key": self.llm_api_key,
            }
            if self.llm_api_base:
                kwargs["api_base"] = self.llm_api_base

            response = litellm.completion(**kwargs)
            answer = response.choices[0].message.content

            # Calculate confidence using the structured method
            # Get stages from options if available (passed by run())
            stages_fired = options.get("stages_fired", ["answer_generation"])
            confidence = self._calculate_confidence(context.chunks, stages_fired)

            logger.debug(f"Generated answer with {len(answer)} chars, confidence={confidence:.2f}")
            return answer, confidence

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")

            # Graceful degradation: return source list
            source_titles = []
            for chunk in context.chunks[:5]:
                title = chunk.metadata.get("title", chunk.source) if chunk.metadata else chunk.source
                source_titles.append(title)

            fallback = "Based on the retrieved sources, here are the relevant documents:\n\n"
            for i, title in enumerate(source_titles, 1):
                fallback += f"{i}. {title}\n"
            return fallback, 0.5

    def _results_to_chunks(self, results: List[SearchResult]) -> List[RankedChunk]:
        """Convert SearchResult list to RankedChunk list."""
        chunks = []
        for r in results:
            chunk = RankedChunk(
                content=r.content,
                source=r.metadata.get("source", r.id),
                retrieval_score=r.score,
                rerank_score=0.0,
                final_score=r.score,
                metadata=r.metadata,
            )
            chunks.append(chunk)
        return chunks

    def _chunks_to_results(self, chunks: List[RankedChunk]) -> List[SearchResult]:
        """
        Convert RankedChunk list to SearchResult list.

        Used to convert pipeline results back to SearchResult format
        for compatibility with EnhancedRAGResult.sources.

        Args:
            chunks: List of RankedChunks to convert

        Returns:
            List[SearchResult]: Converted search results
        """
        results = []
        for chunk in chunks:
            result = SearchResult(
                id=chunk.source,
                content=chunk.content,
                metadata=chunk.metadata,
                score=chunk.final_score,
            )
            results.append(result)
        return results

    def _context_to_string(self, context: RetrievalContext) -> str:
        """Convert RetrievalContext to string for LLM input."""
        parts = []
        for i, chunk in enumerate(context.chunks, 1):
            parts.append(f"[Source {i}] - {chunk.source}\n{chunk.content}\n")
        return "\n".join(parts)

    def _empty_result(
        self,
        question: str,
        session_id: Optional[str],
    ) -> EnhancedRAGResult:
        """Return an empty result when no documents are found."""
        return EnhancedRAGResult(
            answer="No relevant information found in the knowledge base.",
            question=question,
            sources=[],
            context="",
            confidence=0.0,
            retrieval_strategy="no_results",
            session_id=session_id,
        )
