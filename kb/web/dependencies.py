"""
Shared dependencies for FastAPI routes.

Provides dependency injection for storage and configuration instances.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from kb.config import Config

# Cache for singleton instances
_sqlite_storage_instance = None
_chroma_storage_instance = None
_pipeline_instance = None
_conversation_manager_instance = None

CONFIG_FILE = Path.home() / ".localbrain" / "config.yaml"


@lru_cache()
def get_config() -> Config:
    """
    Get cached configuration instance.
    
    Returns:
        Config: Configuration object loaded from default config file.
    """
    return Config(CONFIG_FILE)


def get_sqlite_storage():
    """
    Get SQLite storage instance (singleton).
    
    Returns:
        SQLiteStorage: Storage instance for metadata operations.
    """
    global _sqlite_storage_instance
    
    if _sqlite_storage_instance is None:
        from kb.storage.sqlite_storage import SQLiteStorage
        
        config = get_config()
        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "metadata.db")
        _sqlite_storage_instance = SQLiteStorage(db_path=db_path)
    
    return _sqlite_storage_instance


def get_chroma_storage():
    """
    Get ChromaDB storage instance (singleton).
    
    Returns:
        ChromaStorage: Storage instance for vector operations.
    """
    global _chroma_storage_instance
    
    if _chroma_storage_instance is None:
        from kb.storage.chroma_storage import ChromaStorage
        
        config = get_config()
        persist_dir = config.get("storage.persist_directory", "~/.knowledge-base/db/chroma")
        persist_dir = str(Path(persist_dir).expanduser())
        _chroma_storage_instance = ChromaStorage(path=persist_dir)
    
    return _chroma_storage_instance


def get_keyword_search():
    """
    Get keyword search instance.
    
    Returns:
        KeywordSearch: Search instance for keyword-based queries.
        
    Raises:
        ValueError: If data directory doesn't exist.
    """
    from kb.query.keyword_search import KeywordSearch
    
    config = get_config()
    data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
    return KeywordSearch(data_dir=str(data_dir))


def get_semantic_search():
    """
    Get semantic search instance.
    
    Returns:
        SemanticSearch: Search instance for semantic queries.
        
    Raises:
        ValueError: If embedding provider is not configured.
    """
    from kb.query.semantic_search import SemanticSearch
    
    config = get_config()
    return SemanticSearch(config)


def get_rag_query():
    """
    Get RAG query instance.

    Returns:
        RAGQuery: Query instance for RAG-based Q&A.

    Raises:
        ValueError: If LLM provider is not configured.
    """
    from kb.query.rag import RAGQuery

    config = get_config()
    return RAGQuery(config)


def get_graph_query():
    """
    Get graph query instance.

    Returns:
        GraphQuery: Query instance for knowledge graph queries.
    """
    from kb.query.graph_query import GraphQuery

    storage = get_sqlite_storage()
    return GraphQuery(storage=storage)


def get_topic_query():
    """
    Get topic query instance.

    Returns:
        TopicQuery: Query instance for topic cluster queries.
    """
    from kb.query.topic_query import TopicQuery

    storage = get_sqlite_storage()
    return TopicQuery(storage=storage)


def get_reading_history():
    """
    Get reading history instance.

    Returns:
        ReadingHistory: Instance for recording and querying user interactions.
    """
    from kb.query.reading_history import ReadingHistory

    storage = get_sqlite_storage()
    return ReadingHistory(storage=storage)


def get_conversation_manager():
    """
    Get or create the conversation manager.

    Returns:
        ConversationManager: Instance for managing multi-turn conversation sessions.
    """
    global _conversation_manager_instance

    if _conversation_manager_instance is None:
        from kb.query.conversation import ConversationManager

        config = get_config()
        data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
        db_path = str(data_dir / "db" / "conversations.db")
        _conversation_manager_instance = ConversationManager(db_path=db_path)

    return _conversation_manager_instance


def get_retrieval_pipeline():
    """
    Get or create the enhanced retrieval pipeline.

    Creates the full RetrievalPipeline with all its components using graceful
    degradation - if some components (graph, topics) aren't available, the
    pipeline is created without them.

    Returns:
        RetrievalPipeline: The enhanced retrieval pipeline instance.

    Raises:
        ValueError: If required configuration is missing.
    """
    global _pipeline_instance

    if _pipeline_instance is None:
        from kb.query.retrieval_pipeline import RetrievalPipeline
        from kb.query.query_expander import LLMQueryExpander, NoOpQueryExpander
        from kb.query.reranker import LLMReranker, NoOpReranker
        from kb.query.context_builder import HierarchicalContextBuilder

        config = get_config()

        # Get or create search components
        try:
            semantic_search = get_semantic_search()
        except Exception as e:
            semantic_search = None

        try:
            keyword_search = get_keyword_search()
        except Exception as e:
            keyword_search = None

        # Create query expander with graceful degradation
        try:
            query_expander = LLMQueryExpander(config.to_dict())
            if not query_expander.llm_available:
                query_expander = NoOpQueryExpander()
        except Exception as e:
            query_expander = NoOpQueryExpander()

        # Create reranker with graceful degradation
        try:
            reranker = LLMReranker(config.to_dict())
            if not reranker.llm_available:
                reranker = NoOpReranker()
        except Exception as e:
            reranker = NoOpReranker()

        # Create context builder
        context_budget = config.get("query", {}).get("rag", {}).get("context_budget", 4000)
        context_builder = HierarchicalContextBuilder(budget=context_budget)

        # Get optional enrichment components with graceful degradation
        try:
            graph_query = get_graph_query()
        except Exception as e:
            graph_query = None

        try:
            topic_query = get_topic_query()
        except Exception as e:
            topic_query = None

        try:
            reading_history = get_reading_history()
        except Exception as e:
            reading_history = None

        try:
            conversation_manager = get_conversation_manager()
        except Exception as e:
            conversation_manager = None

        # Create the pipeline with all components
        _pipeline_instance = RetrievalPipeline(
            config=config,
            semantic_search=semantic_search,
            keyword_search=keyword_search,
            query_expander=query_expander,
            reranker=reranker,
            context_builder=context_builder,
            graph_query=graph_query,
            topic_query=topic_query,
            reading_history=reading_history,
            conversation_manager=conversation_manager,
        )

    return _pipeline_instance
