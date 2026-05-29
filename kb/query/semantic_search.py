"""
Semantic search module

Vector similarity-based semantic retrieval, supporting tag filtering and score threshold filtering.
"""

import logging
from typing import Any, Dict, List, Optional

from kb.config import Config
from kb.processors.embedder import Embedder
from kb.query.models import SearchResult
from kb.storage.chroma_storage import ChromaStorage

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Semantic search class.

    Provides vector similarity-based semantic retrieval. After vectorizing the query text, 
    performs similarity retrieval in the Chroma vector database, returning the most relevant documents.

    Usage examples:
        >>> from kb.config import Config
        >>> from kb.query.semantic_search import SemanticSearch
        >>> config = Config()
        >>> search = SemanticSearch(config)
        >>> results = search.search("how to install Python", tags=["python"], top_k=5)
        >>> for result in results:
        ...     print(f"ID: {result.id}, Score: {result.score}")
        ...     print(f"Content: {result.content[:100]}...")
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize semantic search.

        Reads embedding model and storage configuration, creating Embedder and ChromaStorage instances.

        Args:
            config: Configuration object containing embedding and storage configuration.

        Raises:
            ValueError: Invalid configuration or missing required fields.
            ImportError: Required package not installed.
        """
        self.config = config

        # Get query configuration
        query_config = config.get("query", {})
        semantic_config = query_config.get("semantic_search", {})

        self.top_k = semantic_config.get("top_k", 5)
        self.score_threshold = semantic_config.get("score_threshold", 0.7)

        # Create embedding vector generator
        try:
            self.embedder = Embedder.from_config(config)
        except Exception as e:
            logger.warning(f"Embedder initialization failed: {e}. "
                          "Semantic search will fall back to keyword search.")
            self.embedder = None

        # Create vector storage
        try:
            storage_config = config.get("storage", {})
            persist_directory = storage_config.get(
                "persist_directory", "~/.knowledge-base/db/chroma"
            )
            self.storage = ChromaStorage(path=persist_directory)
        except Exception as e:
            logger.error(f"Failed to create storage: {e}")
            raise ValueError(f"Failed to initialize storage: {e}")

        logger.info(
            f"SemanticSearch initialized with top_k={self.top_k}, "
            f"score_threshold={self.score_threshold}"
        )

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        page_number: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Execute semantic search.

        Vectorizes query text, performs similarity retrieval in vector database, 
        optionally filters by tags, and returns results sorted by similarity.

        Args:
            query: Search query text.
            tags: Tag filter list; if provided, only returns documents containing these tags.
            top_k: Number of results to return; uses config default if not provided.
            score_threshold: Score threshold; only returns results above this value. 
                           Uses config default if not provided.
            page_number: Page number filter; if provided, only returns chunks from this page.

        Returns:
            List[SearchResult]: List of search results, sorted by similarity descending.

        Raises:
            ValueError: Query text is empty.
            Exception: Error occurred during search.
        """
        if not query or not query.strip():
            raise ValueError("Query text cannot be empty")

        # Use config default values
        if top_k is None:
            top_k = self.top_k
        if score_threshold is None:
            score_threshold = self.score_threshold

        # Try semantic search first (only if embedder is available)
        if self.embedder is not None:
            try:
                # 1. Vectorize query text
                logger.debug(f"Embedding query: {query[:50]}...")
                query_embedding = self._embed_query(query)

                # 2. Build filter conditions
                where_filter = self._build_filter(tags, page_number=page_number)

                # 3. Execute vector retrieval
                logger.debug(
                    f"Querying storage with top_k={top_k}, "
                    f"filter={where_filter}"
                )
                raw_results = self.storage.query(
                    embedding=query_embedding,
                    top_k=top_k,
                    where_filter=where_filter,
                )

                # 4. Convert and filter results
                results = self._convert_results(raw_results, score_threshold)

                logger.info(
                    f"Search completed: {len(results)} results returned "
                    f"(threshold: {score_threshold})"
                )
                return results

            except Exception as e:
                logger.warning(f"Semantic search failed: {e}. Falling back to keyword search.")
        else:
            logger.info("Embedder not available, using keyword search fallback.")

        # Fallback to keyword search
        try:
            from kb.query.keyword_search import KeywordSearch
            kw_search = KeywordSearch(data_dir=str(self.config.data_dir))
            return kw_search.search(keywords=query, limit=top_k)
        except Exception as kw_err:
            logger.error(f"Keyword search fallback also failed: {kw_err}")
            return []

    def _embed_query(self, query: str) -> List[float]:
        """
        Convert query text to vector.

        Args:
            query: Query text.

        Returns:
            List[float]: Query vector.

        Raises:
            Exception: Vectorization failed.
        """
        try:
            embeddings = self.embedder.embed([query])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Failed to generate embedding")
            return embeddings[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

    def _build_filter(
        self,
        tags: Optional[List[str]] = None,
        page_number: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build Chroma filter conditions.

        Args:
            tags: Tag list.
            page_number: Page number filter.

        Returns:
            Optional[Dict[str, Any]]: Filter conditions dictionary, or None if no filter needed.
        """
        conditions = []

        if tags:
            conditions.append({"tags": {"$in": tags}})

        if page_number is not None:
            conditions.append({"page_number": {"$eq": page_number}})

        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _convert_results(
        self, raw_results: Dict[str, Any], score_threshold: float
    ) -> List[SearchResult]:
        """
        Convert raw retrieval results to SearchResult list.

        Chroma returns cosine distance (0-2), which needs to be converted to similarity score (0-1).
        Cosine similarity = 1 - (cosine distance / 2).

        Args:
            raw_results: Raw results returned by Chroma.
            score_threshold: Score threshold.

        Returns:
            List[SearchResult]: Filtered list of search results.
        """
        results = []

        ids = raw_results.get("ids", [])
        distances = raw_results.get("distances", [])
        metadatas = raw_results.get("metadatas", [])
        documents = raw_results.get("documents", [])

        for i in range(len(ids)):
            # Convert distance to similarity score
            distance = distances[i] if i < len(distances) else 1.0
            # Cosine distance range is 0-2, convert to 0-1 similarity
            score = 1.0 - (distance / 2.0)

            # Ensure score is in 0-1 range
            score = max(0.0, min(1.0, score))

            # Filter results below threshold
            if score < score_threshold:
                continue

            metadata = metadatas[i] if i < len(metadatas) else {}
            content = documents[i] if i < len(documents) else ""

            result = SearchResult(
                id=ids[i],
                content=content,
                metadata=metadata,
                score=score,
            )
            results.append(result)

        return results

    def search_by_page(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        top_pages: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Page-level aggregated search.

        After executing semantic search, aggregates results by page_number, returning the most relevant pages.
        Each page contains all matching chunks from that page and the highest similarity score.
        Only aggregates results that contain page_number metadata.

        Args:
            query: Search query text.
            tags: Tag filter list.
            top_k: Number of chunks to retrieve (before aggregation).
            score_threshold: Score threshold.
            top_pages: Number of most relevant pages to return, defaults to 3.

        Returns:
            List[Dict[str, Any]]: List of page-aggregated results, each containing:
                - page_number: Page number
                - max_score: Highest similarity score for this page
                - chunks: List of matching SearchResults for this page
                - source: Document source (from the first chunk's metadata)
        """
        # Use higher top_k for aggregation to get enough chunks across pages
        search_top_k = (top_k or self.top_k) * 3
        results = self.search(
            query=query,
            tags=tags,
            top_k=search_top_k,
            score_threshold=score_threshold,
        )

        # Group by (source, page_number)
        page_groups: Dict[tuple, List[SearchResult]] = {}
        for result in results:
            page_num = result.metadata.get("page_number")
            if page_num is None:
                continue
            source = result.metadata.get("source", "")
            key = (source, page_num)
            if key not in page_groups:
                page_groups[key] = []
            page_groups[key].append(result)

        # Build page-level results
        page_results = []
        for (source, page_num), chunks in page_groups.items():
            max_score = max(c.score for c in chunks)
            page_results.append({
                "page_number": page_num,
                "max_score": max_score,
                "chunks": chunks,
                "source": source,
            })

        # Sort by max_score descending, return top pages
        page_results.sort(key=lambda x: x["max_score"], reverse=True)
        return page_results[:top_pages]

    def search_batch(
        self,
        queries: List[str],
        tags: Optional[List[str]] = None,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Batch semantic search.

        Execute semantic search for each query in the list, merge results,
        and deduplicate by document ID (keeping highest score).

        Args:
            queries: List of search query texts
            tags: Tag filter list, if provided only return documents with these tags
            top_k: Number of results to return per query before merging
            score_threshold: Score threshold, if not provided uses config default

        Returns:
            List[SearchResult]: Merged results sorted by score descending,
                               deduplicated by document ID
        """
        if not queries:
            return []

        if score_threshold is None:
            score_threshold = self.score_threshold

        # Track results by document ID, keeping highest score
        results_by_id: Dict[str, SearchResult] = {}

        for query in queries:
            if not query or not query.strip():
                continue

            try:
                query_results = self.search(
                    query=query,
                    tags=tags,
                    top_k=top_k,
                    score_threshold=score_threshold,
                )

                for result in query_results:
                    # Use id as primary, fall back to source from metadata
                    doc_id = result.id or result.metadata.get("source", "")
                    if not doc_id:
                        continue

                    # Keep result with highest score
                    if doc_id not in results_by_id or result.score > results_by_id[doc_id].score:
                        results_by_id[doc_id] = result

            except Exception as e:
                # Log warning but continue with other queries
                logger.warning(f"Batch search query failed for '{query[:50]}...': {e}")
                continue

        # Sort by score descending
        merged_results = sorted(
            results_by_id.values(),
            key=lambda x: x.score,
            reverse=True,
        )

        logger.info(
            f"Batch search completed: {len(queries)} queries, "
            f"{len(merged_results)} unique results"
        )

        return merged_results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict[str, Any]: Statistics including document count.
        """
        try:
            count = self.storage.count()
            return {
                "document_count": count,
                "top_k": self.top_k,
                "score_threshold": self.score_threshold,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "document_count": 0,
                "top_k": self.top_k,
                "score_threshold": self.score_threshold,
                "error": str(e),
            }
