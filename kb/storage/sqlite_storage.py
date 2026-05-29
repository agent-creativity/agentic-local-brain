"""
SQLite metadata storage module

SQLite-based structured metadata storage supporting knowledge items, tags, and chunk management.
Provides full-text search (FTS5) and tag management.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


class SQLiteStorage:
    """
    SQLite metadata storage class.

    Wraps the SQLite database, providing persistent storage for knowledge items, tags, and chunks.
    Supports full-text search, tag management, and statistics.

    Usage examples:
        >>> from kb.storage.sqlite_storage import SQLiteStorage
        >>> storage = SQLiteStorage(db_path="~/.knowledge-base/db/metadata.db")
        >>> storage.add_knowledge(
        ...     id="doc1",
        ...     title="Example Document",
        ...     content_type="file",
        ...     source="/path/to/file.pdf",
        ...     collected_at="2024-01-01 12:00:00"
        ... )
        >>> result = storage.get_knowledge("doc1")
    """

    def __init__(self, db_path: str = None) -> None:
        """
        Initialize SQLite storage.

        Args:
            db_path: Database file path. Defaults to ~/.knowledge-base/db/metadata.db.
        """
        if db_path is None:
            db_path = "~/.knowledge-base/db/metadata.db"

        # Expand path
        expanded_path = os.path.expanduser(db_path)
        self.db_path = Path(expanded_path)

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database connection
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._migrate_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Transaction context manager."""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def _migrate_schema(self) -> None:
        """Add new columns to existing databases."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN content_hash TEXT")
            self.conn.commit()
        except Exception:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE knowledge ADD COLUMN user_notes TEXT DEFAULT ''")
            self.conn.commit()
        except Exception:
            pass  # Column already exists
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        with self._transaction() as cursor:
            # Create knowledge table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content_type TEXT,
                    source TEXT,
                    collected_at TIMESTAMP,
                    summary TEXT,
                    word_count INTEGER DEFAULT 0,
                    file_path TEXT,
                    content_hash TEXT
                )
            """)

            # Create tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    count INTEGER DEFAULT 0
                )
            """)

            # Create knowledge_tags association table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_tags (
                    knowledge_id TEXT,
                    tag_id INTEGER,
                    PRIMARY KEY (knowledge_id, tag_id),
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # Create chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    knowledge_id TEXT,
                    chunk_index INTEGER,
                    content TEXT,
                    embedding_id TEXT,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
                )
            """)

            # Create FTS5 virtual table for full-text search
            # Check if it already exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='knowledge_fts'
            """)
            if cursor.fetchone() is None:
                cursor.execute("""
                    CREATE VIRTUAL TABLE knowledge_fts USING fts5(
                        title, 
                        summary,
                        content='knowledge',
                        content_rowid='rowid'
                    )
                """)

                # Create triggers to keep FTS table in sync
                # Note: uses implicit rowid (integer) instead of id (text)
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
                        INSERT INTO knowledge_fts(rowid, title, summary)
                        VALUES (NEW.rowid, NEW.title, NEW.summary);
                    END
                """)

                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary)
                        VALUES ('delete', OLD.rowid, OLD.title, OLD.summary);
                    END
                """)

                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary)
                        VALUES ('delete', OLD.rowid, OLD.title, OLD.summary);
                        INSERT INTO knowledge_fts(rowid, title, summary)
                        VALUES (NEW.rowid, NEW.title, NEW.summary);
                    END
                """)

            # Create indexes to improve query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_content_type 
                ON knowledge(content_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_collected_at 
                ON knowledge(collected_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_knowledge_id 
                ON chunks(knowledge_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags_name 
                ON tags(name)
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge(source, content_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_content_hash ON knowledge(content_hash)")

            # ---- Knowledge Mining tables (v0.6) ----

            # Entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    mention_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, type)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")

            # Entity-document association table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    knowledge_id TEXT NOT NULL,
                    context TEXT,
                    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    UNIQUE(entity_id, knowledge_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_mentions_knowledge ON entity_mentions(knowledge_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_mentions_entity ON entity_mentions(entity_id)")

            # Entity relations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity_id INTEGER NOT NULL,
                    target_entity_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                    UNIQUE(source_entity_id, target_entity_id, relation_type)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_source ON entity_relations(source_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_target ON entity_relations(target_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_relations_composite ON entity_relations(source_entity_id, target_entity_id)")

            # Relation sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_relation_sources (
                    relation_id INTEGER NOT NULL,
                    knowledge_id TEXT NOT NULL,
                    context TEXT,
                    PRIMARY KEY (relation_id, knowledge_id),
                    FOREIGN KEY (relation_id) REFERENCES entity_relations(id) ON DELETE CASCADE,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
                )
            """)

            # Document-level embedding cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    knowledge_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
                )
            """)

            # Document relations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_knowledge_id TEXT NOT NULL,
                    target_knowledge_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    score REAL NOT NULL,
                    shared_entities TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    UNIQUE(source_knowledge_id, target_knowledge_id, relation_type)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_relations_source ON document_relations(source_knowledge_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_relations_target ON document_relations(target_knowledge_id)")

            # Topic clusters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topic_clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    description TEXT,
                    document_count INTEGER DEFAULT 0,
                    centroid_embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Document-topic association table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_topics (
                    knowledge_id TEXT NOT NULL,
                    cluster_id INTEGER NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    PRIMARY KEY (knowledge_id, cluster_id),
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    FOREIGN KEY (cluster_id) REFERENCES topic_clusters(id) ON DELETE CASCADE
                )
            """)

            # Reading history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    knowledge_id TEXT,
                    query TEXT,
                    action_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER,
                    interaction_type TEXT,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reading_history_time ON reading_history(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reading_history_knowledge ON reading_history(knowledge_id)")

            # ---- Wiki Articles table (v0.8) ----
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wiki_articles (
                    article_id TEXT PRIMARY KEY,
                    article_type TEXT NOT NULL,
                    topic_id TEXT,
                    title TEXT NOT NULL,
                    file_path TEXT,
                    source_doc_ids TEXT,
                    entity_refs TEXT,
                    compiled_at DATETIME,
                    version INTEGER DEFAULT 1,
                    word_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wiki_articles_type ON wiki_articles(article_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wiki_articles_topic ON wiki_articles(topic_id)")

            # ---- Wiki Categories table (v0.8) ----
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wiki_categories (
                    category_id TEXT PRIMARY KEY,
                    topic_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    doc_ids TEXT,
                    article_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (topic_id) REFERENCES topic_clusters(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wiki_categories_topic ON wiki_categories(topic_id)")

            # Migration: add category_id to wiki_articles if not exists
            try:
                cursor.execute("SELECT category_id FROM wiki_articles LIMIT 1")
            except Exception:
                cursor.execute("ALTER TABLE wiki_articles ADD COLUMN category_id TEXT REFERENCES wiki_categories(category_id)")

    # ---- Knowledge CRUD ----

    def add_knowledge(
        self,
        id: str,
        title: str,
        content_type: str,
        source: str,
        collected_at: str,
        summary: str = "",
        word_count: int = 0,
        file_path: str = "",
        content_hash: str = None
    ) -> bool:
        """
        Insert a knowledge item.

        Args:
            id: Unique knowledge item ID.
            title: Title.
            content_type: Content type (file/webpage/bookmark/paper/email/note).
            source: Original source.
            collected_at: Collection time.
            summary: Summary (optional).
            word_count: Word count (optional).
            file_path: File system path (optional).
            content_hash: Content hash (optional).

        Returns:
            bool: Whether insertion was successful.
        """
        try:
            with self._transaction() as cursor:
                cursor.execute("""
                    INSERT INTO knowledge
                    (id, title, content_type, source, collected_at, summary, word_count, file_path, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (id, title, content_type, source, collected_at, summary, word_count, file_path, content_hash))

            # Trigger async mining in background thread
            try:
                from kb.processors.mining_worker import mine_document_async
                mine_document_async(
                    knowledge_id=id,
                    title=title,
                    content=summary or "",
                    db_path=str(self.db_path),
                )
            except Exception:
                pass  # Never block document save for mining failures

            return True
        except sqlite3.IntegrityError:
            # ID already exists
            return False
        except Exception:
            return False

    def get_knowledge(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Get a knowledge item by ID.

        Args:
            id: Unique knowledge item ID.

        Returns:
            Optional[Dict[str, Any]]: Knowledge item dictionary, or None if not found.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM knowledge WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            cursor.close()

    def list_knowledge(
        self,
        content_type: str = None,
        limit: int = 50,
        offset: int = 0,
        tag: str = None,
        search: str = None,
        sort_by: str = "collected_at",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        List knowledge items.

        Args:
            content_type: Content type filter (optional).
            limit: Limit on number of results.
            offset: Offset.
            tag: Tag filter (optional).
            search: Full-text search keywords (optional).
            sort_by: Sort field (optional: collected_at, title, word_count).
            sort_order: Sort direction (optional: asc, desc).

        Returns:
            List[Dict[str, Any]]: List of knowledge items.
        """
        # Whitelist allowed sort columns to prevent SQL injection
        allowed_sort_columns = {"collected_at", "title", "word_count", "source"}
        if sort_by not in allowed_sort_columns:
            sort_by = "collected_at"
        
        # Validate sort_order
        if sort_order.lower() not in {"asc", "desc"}:
            sort_order = "desc"
        
        cursor = self.conn.cursor()
        try:
            # Build the base query
            base_query = "SELECT DISTINCT k.* FROM knowledge k"
            where_conditions = []
            params = []
            
            # Add tag join if tag filter is specified
            if tag:
                base_query += """
                    JOIN knowledge_tags kt ON k.id = kt.knowledge_id
                    JOIN tags t ON kt.tag_id = t.id
                """
                where_conditions.append("t.name = ?")
                params.append(tag)
            
            # Add content_type filter
            if content_type:
                where_conditions.append("k.content_type = ?")
                params.append(content_type)
            
            # Add search filter (search in title, source, summary)
            if search:
                search_pattern = f"%{search}%"
                where_conditions.append("(k.title LIKE ? OR k.source LIKE ? OR k.summary LIKE ?)")
                params.extend([search_pattern, search_pattern, search_pattern])
            
            # Build WHERE clause
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            
            # Add ORDER BY clause
            base_query += f" ORDER BY k.{sort_by} {sort_order.upper()}"
            
            # Add LIMIT and OFFSET
            base_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(base_query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def delete_knowledge(self, id: str) -> bool:
        """
        Delete a knowledge item and its associated tags and chunks.

        Args:
            id: Unique knowledge item ID.

        Returns:
            bool: Whether deletion was successful.
        """
        try:
            with self._transaction() as cursor:
                # First get associated tags to update counts
                cursor.execute("""
                    SELECT tag_id FROM knowledge_tags WHERE knowledge_id = ?
                """, (id,))
                tag_ids = [row[0] for row in cursor.fetchall()]

                # Delete knowledge item (CASCADE auto-deletes associated chunks and knowledge_tags)
                cursor.execute("DELETE FROM knowledge WHERE id = ?", (id,))

                # Update tag counts
                for tag_id in tag_ids:
                    cursor.execute("""
                        UPDATE tags SET count = count - 1 WHERE id = ?
                    """, (tag_id,))

                # Delete tags with zero count
                cursor.execute("DELETE FROM tags WHERE count <= 0")

            return True
        except Exception:
            return False

    def update_knowledge(self, id: str, **kwargs) -> bool:
        """
        Update knowledge item fields.

        Args:
            id: Unique knowledge item ID.
            **kwargs: Fields to update.

        Returns:
            bool: Whether update was successful.
        """
        if not kwargs:
            return True

        # Allowed fields for update
        allowed_fields = {
            'title', 'content_type', 'source', 'collected_at',
            'summary', 'word_count', 'file_path', 'user_notes'
        }

        # Filter to only allowed fields
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not update_fields:
            return True

        try:
            set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
            values = list(update_fields.values()) + [id]

            with self._transaction() as cursor:
                cursor.execute(
                    f"UPDATE knowledge SET {set_clause} WHERE id = ?",
                    values
                )
            return True
        except Exception:
            return False

    def count_knowledge(self, content_type: str = None) -> int:
        """
        Count knowledge items.

        Args:
            content_type: Content type filter (optional).

        Returns:
            int: Number of knowledge items.
        """
        cursor = self.conn.cursor()
        try:
            if content_type:
                cursor.execute(
                    "SELECT COUNT(*) FROM knowledge WHERE content_type = ?",
                    (content_type,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM knowledge")
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def source_exists(self, source: str, content_type: str = None) -> Optional[Dict]:
        """Check if a source already exists in the knowledge base.

        Args:
            source: Source URL or file path to check.
            content_type: Optional content type filter (e.g., 'webpage', 'file').

        Returns:
            Dict with existing record info (id, title, source, content_type) or None.
        """
        cursor = self.conn.cursor()
        try:
            if content_type:
                cursor.execute(
                    "SELECT id, title, source, content_type FROM knowledge WHERE source = ? AND content_type = ?",
                    (source, content_type)
                )
            else:
                cursor.execute(
                    "SELECT id, title, source, content_type FROM knowledge WHERE source = ?",
                    (source,)
                )
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "title": row[1], "source": row[2], "content_type": row[3]}
            return None
        finally:
            cursor.close()

    def hash_exists(self, content_hash: str, content_type: str = None) -> Optional[Dict]:
        """Check if content with the same hash already exists.

        Args:
            content_hash: SHA-256 hash of content.
            content_type: Optional content type filter.

        Returns:
            Dict with existing record info or None.
        """
        cursor = self.conn.cursor()
        try:
            if content_type:
                cursor.execute(
                    "SELECT id, title, source, content_type FROM knowledge WHERE content_hash = ? AND content_type = ?",
                    (content_hash, content_type)
                )
            else:
                cursor.execute(
                    "SELECT id, title, source, content_type FROM knowledge WHERE content_hash = ?",
                    (content_hash,)
                )
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "title": row[1], "source": row[2], "content_type": row[3]}
            return None
        finally:
            cursor.close()

    # ---- Tag Management ----

    def add_tags(self, knowledge_id: str, tags: List[str]) -> bool:
        """
        Add tags to a knowledge item.

        Args:
            knowledge_id: Knowledge item ID.
            tags: Tag list.

        Returns:
            bool: Whether addition was successful.
        """
        if not tags:
            return True

        try:
            with self._transaction() as cursor:
                for tag_name in tags:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue

                    # Get or create tag
                    cursor.execute(
                        "SELECT id FROM tags WHERE name = ?",
                        (tag_name,)
                    )
                    row = cursor.fetchone()

                    if row:
                        tag_id = row[0]
                    else:
                        cursor.execute(
                            "INSERT INTO tags (name, count) VALUES (?, 0)",
                            (tag_name,)
                        )
                        tag_id = cursor.lastrowid

                    # Add association (if not exists)
                    cursor.execute("""
                        INSERT OR IGNORE INTO knowledge_tags (knowledge_id, tag_id)
                        VALUES (?, ?)
                    """, (knowledge_id, tag_id))

                    # If a new association was successfully inserted, update count
                    if cursor.rowcount > 0:
                        cursor.execute(
                            "UPDATE tags SET count = count + 1 WHERE id = ?",
                            (tag_id,)
                        )

            return True
        except Exception:
            return False

    def get_tags(self, knowledge_id: str) -> List[str]:
        """
        Get all tags for a knowledge item.

        Args:
            knowledge_id: Knowledge item ID.

        Returns:
            List[str]: List of tag names.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT t.name FROM tags t
                JOIN knowledge_tags kt ON t.id = kt.tag_id
                WHERE kt.knowledge_id = ?
                ORDER BY t.name
            """, (knowledge_id,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_tags(
        self,
        order_by: str = "count",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all tags with counts.

        Args:
            order_by: Sort method ('count' or 'name').
            limit: Limit on number of results.

        Returns:
            List[Dict[str, Any]]: Tag list. [{'name': str, 'count': int}, ...]
        """
        cursor = self.conn.cursor()
        try:
            order_clause = "count DESC" if order_by == "count" else "name ASC"
            cursor.execute(f"""
                SELECT name, count FROM tags
                ORDER BY {order_clause}
                LIMIT ?
            """, (limit,))
            return [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
        finally:
            cursor.close()

    def merge_tags(self, source_tag: str, target_tag: str) -> int:
        """
        Merge tags (merge source_tag into target_tag).

        Args:
            source_tag: Source tag name.
            target_tag: Target tag name.

        Returns:
            int: Number of affected knowledge items, 0 on failure.
        """
        if source_tag == target_tag:
            return 0

        try:
            with self._transaction() as cursor:
                # Get source and target tag IDs
                cursor.execute("SELECT id FROM tags WHERE name = ?", (source_tag,))
                source_row = cursor.fetchone()
                if not source_row:
                    return 0
                source_id = source_row[0]

                cursor.execute("SELECT id FROM tags WHERE name = ?", (target_tag,))
                target_row = cursor.fetchone()

                if target_row:
                    target_id = target_row[0]
                else:
                    # Create target tag
                    cursor.execute(
                        "INSERT INTO tags (name, count) VALUES (?, 0)",
                        (target_tag,)
                    )
                    target_id = cursor.lastrowid

                # Get knowledge items associated with source tag
                cursor.execute("""
                    SELECT knowledge_id FROM knowledge_tags WHERE tag_id = ?
                """, (source_id,))
                knowledge_ids = [row[0] for row in cursor.fetchall()]
                
                # Record the affected count
                affected_count = len(knowledge_ids)

                # Update associations to target tag
                for kid in knowledge_ids:
                    # Check if target tag is already associated
                    cursor.execute("""
                        SELECT 1 FROM knowledge_tags 
                        WHERE knowledge_id = ? AND tag_id = ?
                    """, (kid, target_id))

                    if not cursor.fetchone():
                        cursor.execute("""
                            UPDATE knowledge_tags 
                            SET tag_id = ? 
                            WHERE knowledge_id = ? AND tag_id = ?
                        """, (target_id, kid, source_id))
                        cursor.execute(
                            "UPDATE tags SET count = count + 1 WHERE id = ?",
                            (target_id,)
                        )
                    else:
                        # Association already exists, delete source association
                        cursor.execute("""
                            DELETE FROM knowledge_tags 
                            WHERE knowledge_id = ? AND tag_id = ?
                        """, (kid, source_id))

                # Delete source tag
                cursor.execute("DELETE FROM tags WHERE id = ?", (source_id,))

            return affected_count
        except Exception:
            return 0

    def delete_tag(self, tag_name: str) -> int:
        """
        Delete a tag and all its associations.

        Args:
            tag_name: Tag name.

        Returns:
            int: Number of affected knowledge items, 0 on failure.
        """
        try:
            with self._transaction() as cursor:
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                row = cursor.fetchone()
                if not row:
                    return 0

                tag_id = row[0]
                
                # Get the number of affected knowledge items
                cursor.execute(
                    "SELECT COUNT(*) FROM knowledge_tags WHERE tag_id = ?",
                    (tag_id,)
                )
                affected_count = cursor.fetchone()[0]

                # Delete associations
                cursor.execute(
                    "DELETE FROM knowledge_tags WHERE tag_id = ?",
                    (tag_id,)
                )

                # Delete tag
                cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))

            return affected_count
        except Exception:
            return 0

    def find_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find knowledge items by tags.

        Args:
            tags: Tag list.
            match_all: Whether to match all tags.
            limit: Limit on number of results.

        Returns:
            List[Dict[str, Any]]: List of knowledge items.
        """
        if not tags:
            return []

        cursor = self.conn.cursor()
        try:
            placeholders = ",".join(["?" for _ in tags])

            if match_all:
                # Must match all tags
                cursor.execute(f"""
                    SELECT k.* FROM knowledge k
                    JOIN knowledge_tags kt ON k.id = kt.knowledge_id
                    JOIN tags t ON kt.tag_id = t.id
                    WHERE t.name IN ({placeholders})
                    GROUP BY k.id
                    HAVING COUNT(DISTINCT t.name) = ?
                    LIMIT ?
                """, tags + [len(tags), limit])
            else:
                # Match any tag
                cursor.execute(f"""
                    SELECT DISTINCT k.* FROM knowledge k
                    JOIN knowledge_tags kt ON k.id = kt.knowledge_id
                    JOIN tags t ON kt.tag_id = t.id
                    WHERE t.name IN ({placeholders})
                    LIMIT ?
                """, tags + [limit])

            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_by_tags_any(self, tags: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find knowledge items containing any of the specified tags.

        Args:
            tags: Tag list.
            limit: Limit on number of results.

        Returns:
            List[Dict[str, Any]]: List of knowledge items.
        """
        return self.find_by_tags(tags, match_all=False, limit=limit)

    def get_by_tags_all(self, tags: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find knowledge items containing all specified tags.

        Args:
            tags: Tag list.
            limit: Limit on number of results.

        Returns:
            List[Dict[str, Any]]: List of knowledge items.
        """
        return self.find_by_tags(tags, match_all=True, limit=limit)

    # ---- Chunk Management ----

    def add_chunks(self, knowledge_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Add chunks for a knowledge item.

        Args:
            knowledge_id: Knowledge item ID.
            chunks: List of chunks, each containing {id, chunk_index, content, embedding_id}.

        Returns:
            bool: Whether addition was successful.
        """
        if not chunks:
            return True

        try:
            with self._transaction() as cursor:
                for chunk in chunks:
                    cursor.execute("""
                        INSERT OR REPLACE INTO chunks 
                        (id, knowledge_id, chunk_index, content, embedding_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        chunk.get('id'),
                        knowledge_id,
                        chunk.get('chunk_index', 0),
                        chunk.get('content', ''),
                        chunk.get('embedding_id', '')
                    ))
            return True
        except Exception:
            return False

    def get_chunks(self, knowledge_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a knowledge item.

        Args:
            knowledge_id: Knowledge item ID.

        Returns:
            List[Dict[str, Any]]: List of chunks, sorted by chunk_index.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM chunks 
                WHERE knowledge_id = ?
                ORDER BY chunk_index
            """, (knowledge_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def delete_chunks(self, knowledge_id: str) -> bool:
        """
        Delete all chunks for a knowledge item.

        Args:
            knowledge_id: Knowledge item ID.

        Returns:
            bool: Whether deletion was successful.
        """
        try:
            with self._transaction() as cursor:
                cursor.execute(
                    "DELETE FROM chunks WHERE knowledge_id = ?",
                    (knowledge_id,)
                )
            return True
        except Exception:
            return False

    # ---- Full-text Search ----

    def search_fulltext(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Full-text search.

        Args:
            query: Search query.
            limit: Limit on number of results.

        Returns:
            List[Dict[str, Any]]: List of matching knowledge items.
        """
        if not query or not query.strip():
            return []

        cursor = self.conn.cursor()
        try:
            # Use FTS5 search
            cursor.execute("""
                SELECT k.* FROM knowledge k
                JOIN knowledge_fts fts ON k.rowid = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            # Fall back to LIKE search when FTS query fails
            like_query = f"%{query}%"
            cursor.execute("""
                SELECT * FROM knowledge
                WHERE title LIKE ? OR summary LIKE ?
                LIMIT ?
            """, (like_query, like_query, limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    # ---- Statistics ----

    def count_all(self) -> int:
        """
        Get total number of knowledge items.

        Returns:
            int: Total number of knowledge items.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def count_by_type(self) -> Dict[str, int]:
        """
        Count knowledge items by content type.

        Returns:
            Dict[str, int]: Dictionary of {content_type: count}.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT content_type, COUNT(*) as count 
                FROM knowledge 
                GROUP BY content_type
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            cursor.close()

    def get_tag_statistics(self) -> Dict[str, int]:
        """
        Get tag statistics.

        Returns:
            Dict[str, int]: Dictionary of {tag_name: count}.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT t.name, COUNT(kt.knowledge_id) as count
                FROM tags t
                JOIN knowledge_tags kt ON t.id = kt.tag_id
                GROUP BY t.id, t.name
                ORDER BY count DESC
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            cursor.close()

    def get_collection_timeline(self, days: int = 30) -> List[tuple]:
        """
        Get collection timeline statistics.

        Args:
            days: Number of recent days to return, defaults to 30.

        Returns:
            List[tuple]: [(date, count), ...] sorted by date.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT DATE(collected_at) as date, COUNT(*) as count
                FROM knowledge
                WHERE collected_at >= DATE('now', '-{} days')
                GROUP BY DATE(collected_at)
                ORDER BY date DESC
            """.format(days))
            return [(row[0], row[1]) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_all_tags(self) -> Dict[str, int]:
        """
        Get all tags with counts.

        Returns:
            Dict[str, int]: Dictionary of {tag_name: count}.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT t.name, t.count
                FROM tags t
                ORDER BY t.name
            """)
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            cursor.close()

    def get_all_knowledge(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get all knowledge items, optionally filtered by tags.

        Args:
            tags: Tag list, only return knowledge items containing these tags.

        Returns:
            List[Dict[str, Any]]: List of knowledge items, including tags field.
        """
        cursor = self.conn.cursor()
        try:
            if tags:
                # Filter by tags
                placeholders = ",".join(["?" for _ in tags])
                cursor.execute(f"""
                    SELECT DISTINCT k.* FROM knowledge k
                    JOIN knowledge_tags kt ON k.id = kt.knowledge_id
                    JOIN tags t ON kt.tag_id = t.id
                    WHERE t.name IN ({placeholders})
                    ORDER BY k.collected_at DESC
                """, tags)
            else:
                # Get all
                cursor.execute("""
                    SELECT * FROM knowledge
                    ORDER BY collected_at DESC
                """)

            rows = cursor.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                # Get tags for each knowledge item
                item['tags'] = self.get_tags(item['id'])
                items.append(item)
            return items
        finally:
            cursor.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics.

        Returns:
            Dict[str, Any]: Statistics including:
                - total_items: Total knowledge items.
                - items_by_type: Count grouped by type.
                - total_tags: Total tags.
                - total_chunks: Total chunks.
        """
        cursor = self.conn.cursor()
        try:
            # Total knowledge items.
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            total_items = cursor.fetchone()[0]

            # Group by type
            cursor.execute("""
                SELECT content_type, COUNT(*) as count 
                FROM knowledge 
                GROUP BY content_type
            """)
            items_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # Total tags.
            cursor.execute("SELECT COUNT(*) FROM tags")
            total_tags = cursor.fetchone()[0]

            # Total chunks.
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]

            return {
                'total_items': total_items,
                'items_by_type': items_by_type,
                'total_tags': total_tags,
                'total_chunks': total_chunks
            }
        finally:
            cursor.close()

    # ---- Wiki Articles Management (v0.8) ----

    def save_wiki_article(
        self,
        article_id: str,
        article_type: str,
        topic_id: str,
        title: str,
        file_path: str,
        source_doc_ids: List[str],
        entity_refs: List[str],
        word_count: int = 0,
        category_id: str = None
    ) -> bool:
        """
        Save or update a wiki article

        Args:
            article_id: Unique article identifier
            article_type: "topic" or "entity"
            topic_id: Associated topic ID (for topic articles)
            title: Article title
            file_path: Path to the generated markdown file
            source_doc_ids: List of source document IDs
            entity_refs: List of referenced entity names
            word_count: Word count of the article
            category_id: Optional category ID for the article

        Returns:
            bool: True if saved successfully
        """
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            source_doc_ids_json = json.dumps(source_doc_ids or [])
            entity_refs_json = json.dumps(entity_refs or [])

            with self._transaction() as cursor:
                # Check if article exists (for version increment)
                cursor.execute(
                    "SELECT version FROM wiki_articles WHERE article_id = ?",
                    (article_id,)
                )
                existing = cursor.fetchone()
                version = (existing[0] + 1) if existing else 1

                cursor.execute("""
                    INSERT OR REPLACE INTO wiki_articles
                    (article_id, article_type, topic_id, title, file_path,
                     source_doc_ids, entity_refs, compiled_at, version, word_count, category_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, article_type, topic_id, title, file_path,
                    source_doc_ids_json, entity_refs_json, now, version, word_count, category_id
                ))
            return True
        except Exception:
            return False

    def get_wiki_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a wiki article by ID

        Args:
            article_id: Article identifier

        Returns:
            Dict with article data or None if not found
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM wiki_articles WHERE article_id = ?",
                (article_id,)
            )
            row = cursor.fetchone()
            if row:
                article = dict(row)
                # Parse JSON fields back to lists
                article['source_doc_ids'] = json.loads(article.get('source_doc_ids', '[]'))
                article['entity_refs'] = json.loads(article.get('entity_refs', '[]'))
                return article
            return None
        finally:
            cursor.close()

    def list_wiki_articles(
        self,
        article_type: str = None,
        category_id: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List wiki articles with optional type filter

        Args:
            article_type: Filter by "topic" or "entity", optional
            category_id: Filter by category ID, optional
            limit: Max results to return
            offset: Offset for pagination

        Returns:
            List of article dicts ordered by compiled_at DESC
        """
        cursor = self.conn.cursor()
        try:
            if article_type and category_id:
                cursor.execute("""
                    SELECT * FROM wiki_articles
                    WHERE article_type = ? AND category_id = ?
                    ORDER BY compiled_at DESC
                    LIMIT ? OFFSET ?
                """, (article_type, category_id, limit, offset))
            elif article_type:
                cursor.execute("""
                    SELECT * FROM wiki_articles
                    WHERE article_type = ?
                    ORDER BY compiled_at DESC
                    LIMIT ? OFFSET ?
                """, (article_type, limit, offset))
            elif category_id:
                cursor.execute("""
                    SELECT * FROM wiki_articles
                    WHERE category_id = ?
                    ORDER BY compiled_at DESC
                    LIMIT ? OFFSET ?
                """, (category_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM wiki_articles
                    ORDER BY compiled_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

            articles = []
            for row in cursor.fetchall():
                article = dict(row)
                article['source_doc_ids'] = json.loads(article.get('source_doc_ids', '[]'))
                article['entity_refs'] = json.loads(article.get('entity_refs', '[]'))
                articles.append(article)
            return articles
        finally:
            cursor.close()

    def get_wiki_stats(self) -> Dict[str, Any]:
        """
        Get wiki article statistics

        Returns:
            Dict with topic_count, entity_count, total_count, last_compiled, total_words, category_count
        """
        cursor = self.conn.cursor()
        try:
            # Total count
            cursor.execute("SELECT COUNT(*) FROM wiki_articles")
            total_count = cursor.fetchone()[0]

            # Count by type
            cursor.execute("""
                SELECT article_type, COUNT(*)
                FROM wiki_articles
                GROUP BY article_type
            """)
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            topic_count = type_counts.get('topic', 0)
            entity_count = type_counts.get('entity', 0)

            # Last compiled time
            cursor.execute("SELECT MAX(compiled_at) FROM wiki_articles")
            last_compiled = cursor.fetchone()[0]

            # Total words
            cursor.execute("SELECT COALESCE(SUM(word_count), 0) FROM wiki_articles")
            total_words = cursor.fetchone()[0]

            # Category count
            cursor.execute("SELECT COUNT(*) FROM wiki_categories")
            category_count = cursor.fetchone()[0]

            return {
                'topic_count': topic_count,
                'entity_count': entity_count,
                'total_count': total_count,
                'last_compiled': last_compiled,
                'total_words': total_words,
                'category_count': category_count
            }
        finally:
            cursor.close()

    def search_wiki_articles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search wiki articles by title

        Args:
            query: Search query
            limit: Max results to return

        Returns:
            List of matching articles
        """
        if not query or not query.strip():
            return []

        cursor = self.conn.cursor()
        try:
            like_query = f"%{query}%"
            cursor.execute("""
                SELECT * FROM wiki_articles
                WHERE title LIKE ?
                ORDER BY compiled_at DESC
                LIMIT ?
            """, (like_query, limit))

            articles = []
            for row in cursor.fetchall():
                article = dict(row)
                article['source_doc_ids'] = json.loads(article.get('source_doc_ids', '[]'))
                article['entity_refs'] = json.loads(article.get('entity_refs', '[]'))
                articles.append(article)
            return articles
        finally:
            cursor.close()

    def delete_wiki_article(self, article_id: str) -> bool:
        """
        Delete a wiki article

        Args:
            article_id: Article identifier

        Returns:
            bool: True if deleted successfully
        """
        try:
            with self._transaction() as cursor:
                cursor.execute(
                    "DELETE FROM wiki_articles WHERE article_id = ?",
                    (article_id,)
                )
            return True
        except Exception:
            return False

    def get_wiki_compiled_at(self, topic_id: str) -> Optional[str]:
        """
        Get the compiled_at timestamp for a topic's wiki article

        Args:
            topic_id: Topic identifier

        Returns:
            Compiled timestamp string or None if not found
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT compiled_at FROM wiki_articles
                WHERE topic_id = ? AND article_type = 'topic'
            """, (topic_id,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()

    # ---- Wiki Categories Management (v0.8) ----

    def save_wiki_category(
        self,
        category_id: str,
        topic_id: int,
        name: str,
        description: str = None,
        doc_ids: List[str] = None
    ) -> bool:
        """
        Save or update a wiki category

        Args:
            category_id: Unique category identifier
            topic_id: Associated topic ID
            name: Category name
            description: Category description
            doc_ids: List of document IDs in this category

        Returns:
            bool: True if saved successfully
        """
        try:
            doc_ids_json = json.dumps(doc_ids or [])
            article_count = len(doc_ids) if doc_ids else 0

            with self._transaction() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO wiki_categories
                    (category_id, topic_id, name, description, doc_ids, article_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    category_id, topic_id, name, description, doc_ids_json, article_count
                ))
            return True
        except Exception:
            return False

    def list_wiki_categories(
        self,
        topic_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        List wiki categories with optional topic filter

        Args:
            topic_id: Filter by topic ID, optional

        Returns:
            List of category dicts ordered by created_at DESC
        """
        cursor = self.conn.cursor()
        try:
            if topic_id:
                cursor.execute("""
                    SELECT * FROM wiki_categories
                    WHERE topic_id = ?
                    ORDER BY created_at DESC
                """, (topic_id,))
            else:
                cursor.execute("""
                    SELECT * FROM wiki_categories
                    ORDER BY created_at DESC
                """)

            categories = []
            for row in cursor.fetchall():
                category = dict(row)
                category['doc_ids'] = json.loads(category.get('doc_ids', '[]'))
                categories.append(category)
            return categories
        finally:
            cursor.close()

    def get_wiki_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a wiki category by ID

        Args:
            category_id: Category identifier

        Returns:
            Dict with category data or None if not found
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM wiki_categories WHERE category_id = ?",
                (category_id,)
            )
            row = cursor.fetchone()
            if row:
                category = dict(row)
                category['doc_ids'] = json.loads(category.get('doc_ids', '[]'))
                return category
            return None
        finally:
            cursor.close()

    def delete_wiki_categories_by_topic(self, topic_id: int) -> bool:
        """
        Delete all wiki categories for a topic (for recompilation)

        Args:
            topic_id: Topic identifier

        Returns:
            bool: True if deleted successfully
        """
        try:
            with self._transaction() as cursor:
                cursor.execute(
                    "DELETE FROM wiki_categories WHERE topic_id = ?",
                    (topic_id,)
                )
            return True
        except Exception:
            return False

    # ---- Utility ----

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def reset(self) -> bool:
        """
        Reset database (delete and recreate all tables).

        Returns:
            bool: Whether reset was successful.
        """
        try:
            with self._transaction() as cursor:
                # Drop all tables (in dependency order)
                cursor.execute("DROP TABLE IF EXISTS knowledge_fts")
                cursor.execute("DROP TABLE IF EXISTS chunks")
                cursor.execute("DROP TABLE IF EXISTS knowledge_tags")
                cursor.execute("DROP TABLE IF EXISTS tags")
                cursor.execute("DROP TABLE IF EXISTS knowledge")

                # Drop triggers
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_ai")
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_ad")
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_au")

            # Reinitialize
            self._init_db()
            return True
        except Exception:
            return False

    def __enter__(self) -> "SQLiteStorage":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
