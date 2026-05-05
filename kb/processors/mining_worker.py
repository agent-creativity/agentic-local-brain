"""
Async knowledge mining worker.

Runs entity extraction, embedding generation, and relation discovery
in a background thread when a new document is added.

Topic clustering is NOT triggered per-document (it's a global operation).
Use the /api/topics/rebuild endpoint or `localbrain topics rebuild` for that.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent mining on the same doc
_mining_lock = threading.Lock()


def mine_document_async(
    knowledge_id: str,
    title: str,
    content: str,
    db_path: str,
    config_file: Optional[str] = None,
) -> None:
    """
    Schedule async mining for a single document in a background thread.

    Runs: entity extraction → embedding → relation discovery.
    Each step is independent and failure in one does not block others.
    """
    thread = threading.Thread(
        target=_mine_document,
        args=(knowledge_id, title, content, db_path, config_file),
        daemon=True,
        name=f"mine-{knowledge_id[:8]}",
    )
    thread.start()


def _mine_document(
    knowledge_id: str,
    title: str,
    content: str,
    db_path: str,
    config_file: Optional[str] = None,
) -> None:
    """Run mining pipeline for a single document (called in background thread)."""
    with _mining_lock:
        try:
            from kb.config import Config

            config = Config(config_file) if config_file else Config()

            # Step 1: Entity extraction
            try:
                from kb.processors.entity_extractor import EntityExtractor
                import sqlite3

                extractor = EntityExtractor.from_config(config)
                conn = sqlite3.connect(db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")

                text = content or title or ""
                if text.strip():
                    result = extractor.process(
                        title=title or "",
                        content=text[:3000],
                        knowledge_id=knowledge_id,
                        conn=conn,
                    )
                    if result.success:
                        logger.info(f"[mine] Entities extracted for {knowledge_id[:8]}")
                    else:
                        logger.warning(f"[mine] Entity extraction failed for {knowledge_id[:8]}")
                conn.close()
            except Exception as e:
                logger.error(f"[mine] Entity extraction error for {knowledge_id[:8]}: {e}")

            # Step 2: Document embedding
            try:
                from kb.processors.doc_embedding import DocEmbeddingService

                emb_svc = DocEmbeddingService.from_config(config)
                summary = content[:500] if content else ""
                emb = emb_svc.generate_for_document(knowledge_id, title or "", summary)
                if emb:
                    logger.info(f"[mine] Embedding generated for {knowledge_id[:8]}")
            except Exception as e:
                logger.error(f"[mine] Embedding error for {knowledge_id[:8]}: {e}")

            # Step 3: Cross-document relations
            try:
                from kb.processors.doc_relation_builder import DocRelationBuilder
                from kb.storage.sqlite_storage import SQLiteStorage

                storage = SQLiteStorage(db_path=db_path)
                builder = DocRelationBuilder(storage=storage, config=config)
                counts = builder.build_relations_for_document(knowledge_id)
                storage.close()
                logger.info(
                    f"[mine] Relations built for {knowledge_id[:8]}: "
                    f"{counts['embedding_similarity']} similar, "
                    f"{counts['shared_entity']} shared"
                )
            except Exception as e:
                logger.error(f"[mine] Relation building error for {knowledge_id[:8]}: {e}")

            logger.info(f"[mine] Async mining complete for {knowledge_id[:8]}")

            # Invalidate graph cache since entities/relations may have changed
            try:
                from kb.query.graph_query import invalidate_graph_cache
                invalidate_graph_cache()
            except Exception:
                pass

            # Invalidate pipeline result cache since underlying data has changed
            try:
                from kb.query.retrieval_pipeline import invalidate_pipeline_cache
                invalidate_pipeline_cache()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"[mine] Unexpected error mining {knowledge_id[:8]}: {e}")
