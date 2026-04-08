"""
Shared dependencies for FastAPI routes.

Provides dependency injection for storage and configuration instances.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from kb.config import Config

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
    Get SQLite storage instance.
    
    Returns:
        SQLiteStorage: Storage instance for metadata operations.
    """
    from kb.storage.sqlite_storage import SQLiteStorage
    
    config = get_config()
    data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
    db_path = str(data_dir / "db" / "metadata.db")
    return SQLiteStorage(db_path=db_path)


def get_chroma_storage():
    """
    Get ChromaDB storage instance.
    
    Returns:
        ChromaStorage: Storage instance for vector operations.
    """
    from kb.storage.chroma_storage import ChromaStorage
    
    config = get_config()
    persist_dir = config.get("storage.persist_directory", "~/.knowledge-base/db/chroma")
    persist_dir = str(Path(persist_dir).expanduser())
    return ChromaStorage(path=persist_dir)


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
