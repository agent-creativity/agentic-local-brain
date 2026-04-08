"""
SQLite 元数据存储模块

基于 SQLite 的结构化元数据存储实现，支持知识项、标签和分块的存储管理。
提供全文搜索（FTS5）和标签管理功能。
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


class SQLiteStorage:
    """
    SQLite 元数据存储类

    封装 SQLite 数据库，提供知识项、标签和分块的持久化存储。
    支持全文搜索、标签管理和统计功能。

    使用示例：
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
        初始化 SQLite 存储

        Args:
            db_path: 数据库文件路径，默认为 ~/.knowledge-base/db/metadata.db
        """
        if db_path is None:
            db_path = "~/.knowledge-base/db/metadata.db"

        # 展开路径
        expanded_path = os.path.expanduser(db_path)
        self.db_path = Path(expanded_path)

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库连接
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._migrate_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            # 启用外键约束
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """事务上下文管理器"""
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
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """创建数据库表（如果不存在）"""
        with self._transaction() as cursor:
            # 创建 knowledge 表
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

            # 创建 tags 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    count INTEGER DEFAULT 0
                )
            """)

            # 创建 knowledge_tags 关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_tags (
                    knowledge_id TEXT,
                    tag_id INTEGER,
                    PRIMARY KEY (knowledge_id, tag_id),
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # 创建 chunks 表
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

            # 创建 FTS5 虚拟表用于全文搜索
            # 检查是否已存在
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

                # 创建触发器以保持 FTS 表同步
                # 注意: 使用隐式 rowid (integer) 而非 id (text)
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

            # 创建索引以提高查询性能
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

            # 实体表
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

            # 实体-文档关联表
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

            # 实体关系表
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

            # 关系来源表
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

            # 文档级 embedding 缓存
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    knowledge_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
                )
            """)

            # 文档间关系表
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

            # 主题聚类表
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

            # 文档-主题关联表
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

            # 阅读历史表
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
        插入一个知识项

        Args:
            id: 知识项唯一标识
            title: 标题
            content_type: 内容类型 (file/webpage/bookmark/paper/email/note)
            source: 原始来源
            collected_at: 收集时间
            summary: 摘要，可选
            word_count: 字数，可选
            file_path: 文件系统路径，可选
            content_hash: 内容哈希值，可选

        Returns:
            bool: 是否插入成功
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
            # ID 已存在
            return False
        except Exception:
            return False

    def get_knowledge(self, id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取知识项

        Args:
            id: 知识项唯一标识

        Returns:
            Optional[Dict[str, Any]]: 知识项字典，不存在返回 None
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
        列出知识项

        Args:
            content_type: 内容类型过滤，可选
            limit: 返回数量限制
            offset: 偏移量
            tag: 标签过滤，可选
            search: 全文搜索关键词，可选
            sort_by: 排序字段，可选 (collected_at, title, word_count)
            sort_order: 排序方向，可选 (asc, desc)

        Returns:
            List[Dict[str, Any]]: 知识项列表
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
        删除知识项及其关联的标签和分块

        Args:
            id: 知识项唯一标识

        Returns:
            bool: 是否删除成功
        """
        try:
            with self._transaction() as cursor:
                # 先获取关联的标签以更新计数
                cursor.execute("""
                    SELECT tag_id FROM knowledge_tags WHERE knowledge_id = ?
                """, (id,))
                tag_ids = [row[0] for row in cursor.fetchall()]

                # 删除知识项（CASCADE 会自动删除关联的 chunks 和 knowledge_tags）
                cursor.execute("DELETE FROM knowledge WHERE id = ?", (id,))

                # 更新标签计数
                for tag_id in tag_ids:
                    cursor.execute("""
                        UPDATE tags SET count = count - 1 WHERE id = ?
                    """, (tag_id,))

                # 删除计数为0的标签
                cursor.execute("DELETE FROM tags WHERE count <= 0")

            return True
        except Exception:
            return False

    def update_knowledge(self, id: str, **kwargs) -> bool:
        """
        更新知识项字段

        Args:
            id: 知识项唯一标识
            **kwargs: 要更新的字段

        Returns:
            bool: 是否更新成功
        """
        if not kwargs:
            return True

        # 允许更新的字段
        allowed_fields = {
            'title', 'content_type', 'source', 'collected_at',
            'summary', 'word_count', 'file_path'
        }

        # 过滤只允许的字段
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
        统计知识项数量

        Args:
            content_type: 内容类型过滤，可选

        Returns:
            int: 知识项数量
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
        为知识项添加标签

        Args:
            knowledge_id: 知识项 ID
            tags: 标签列表

        Returns:
            bool: 是否添加成功
        """
        if not tags:
            return True

        try:
            with self._transaction() as cursor:
                for tag_name in tags:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue

                    # 获取或创建标签
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

                    # 添加关联（如果不存在）
                    cursor.execute("""
                        INSERT OR IGNORE INTO knowledge_tags (knowledge_id, tag_id)
                        VALUES (?, ?)
                    """, (knowledge_id, tag_id))

                    # 如果成功插入了新关联，更新计数
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
        获取知识项的所有标签

        Args:
            knowledge_id: 知识项 ID

        Returns:
            List[str]: 标签名称列表
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
        列出所有标签及其计数

        Args:
            order_by: 排序方式 ('count' 或 'name')
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 标签列表 [{'name': str, 'count': int}, ...]
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
        合并标签（将 source_tag 合并到 target_tag）

        Args:
            source_tag: 源标签名称
            target_tag: 目标标签名称

        Returns:
            int: 受影响的知识项数量，如果失败返回 0
        """
        if source_tag == target_tag:
            return 0

        try:
            with self._transaction() as cursor:
                # 获取源标签和目标标签 ID
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
                    # 创建目标标签
                    cursor.execute(
                        "INSERT INTO tags (name, count) VALUES (?, 0)",
                        (target_tag,)
                    )
                    target_id = cursor.lastrowid

                # 获取源标签关联的知识项
                cursor.execute("""
                    SELECT knowledge_id FROM knowledge_tags WHERE tag_id = ?
                """, (source_id,))
                knowledge_ids = [row[0] for row in cursor.fetchall()]
                
                # 记录受影响的数量
                affected_count = len(knowledge_ids)

                # 更新关联到目标标签
                for kid in knowledge_ids:
                    # 检查目标标签是否已关联
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
                        # 已存在关联，删除源关联
                        cursor.execute("""
                            DELETE FROM knowledge_tags 
                            WHERE knowledge_id = ? AND tag_id = ?
                        """, (kid, source_id))

                # 删除源标签
                cursor.execute("DELETE FROM tags WHERE id = ?", (source_id,))

            return affected_count
        except Exception:
            return 0

    def delete_tag(self, tag_name: str) -> int:
        """
        删除标签及其所有关联

        Args:
            tag_name: 标签名称

        Returns:
            int: 受影响的知识项数量，如果失败返回 0
        """
        try:
            with self._transaction() as cursor:
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                row = cursor.fetchone()
                if not row:
                    return 0

                tag_id = row[0]
                
                # 获取受影响的知识项数量
                cursor.execute(
                    "SELECT COUNT(*) FROM knowledge_tags WHERE tag_id = ?",
                    (tag_id,)
                )
                affected_count = cursor.fetchone()[0]

                # 删除关联
                cursor.execute(
                    "DELETE FROM knowledge_tags WHERE tag_id = ?",
                    (tag_id,)
                )

                # 删除标签
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
        根据标签查找知识项

        Args:
            tags: 标签列表
            match_all: 是否需要匹配所有标签
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 知识项列表
        """
        if not tags:
            return []

        cursor = self.conn.cursor()
        try:
            placeholders = ",".join(["?" for _ in tags])

            if match_all:
                # 需要匹配所有标签
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
                # 匹配任意标签
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
        查找包含任意指定标签的知识项

        Args:
            tags: 标签列表
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 知识项列表
        """
        return self.find_by_tags(tags, match_all=False, limit=limit)

    def get_by_tags_all(self, tags: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        查找包含所有指定标签的知识项

        Args:
            tags: 标签列表
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 知识项列表
        """
        return self.find_by_tags(tags, match_all=True, limit=limit)

    # ---- Chunk Management ----

    def add_chunks(self, knowledge_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        为知识项添加分块

        Args:
            knowledge_id: 知识项 ID
            chunks: 分块列表，每个分块包含 {id, chunk_index, content, embedding_id}

        Returns:
            bool: 是否添加成功
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
        获取知识项的所有分块

        Args:
            knowledge_id: 知识项 ID

        Returns:
            List[Dict[str, Any]]: 分块列表，按 chunk_index 排序
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
        删除知识项的所有分块

        Args:
            knowledge_id: 知识项 ID

        Returns:
            bool: 是否删除成功
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
        全文搜索

        Args:
            query: 搜索查询
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 匹配的知识项列表
        """
        if not query or not query.strip():
            return []

        cursor = self.conn.cursor()
        try:
            # 使用 FTS5 搜索
            cursor.execute("""
                SELECT k.* FROM knowledge k
                JOIN knowledge_fts fts ON k.rowid = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            # FTS 查询失败时回退到 LIKE 搜索
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
        获取知识项总数

        Returns:
            int: 知识项总数
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def count_by_type(self) -> Dict[str, int]:
        """
        按内容类型统计知识项数量

        Returns:
            Dict[str, int]: {content_type: count} 的字典
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
        获取标签统计信息

        Returns:
            Dict[str, int]: {tag_name: count} 的字典
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
        获取收集时间线统计

        Args:
            days: 返回最近多少天的数据，默认30天

        Returns:
            List[tuple]: [(date, count), ...] 按日期排序
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
        获取所有标签及其计数

        Returns:
            Dict[str, int]: {tag_name: count} 的字典
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
        获取所有知识项，可选按标签过滤

        Args:
            tags: 标签列表，只返回包含这些标签的知识项

        Returns:
            List[Dict[str, Any]]: 知识项列表，包含 tags 字段
        """
        cursor = self.conn.cursor()
        try:
            if tags:
                # 按标签过滤
                placeholders = ",".join(["?" for _ in tags])
                cursor.execute(f"""
                    SELECT DISTINCT k.* FROM knowledge k
                    JOIN knowledge_tags kt ON k.id = kt.knowledge_id
                    JOIN tags t ON kt.tag_id = t.id
                    WHERE t.name IN ({placeholders})
                    ORDER BY k.collected_at DESC
                """, tags)
            else:
                # 获取所有
                cursor.execute("""
                    SELECT * FROM knowledge
                    ORDER BY collected_at DESC
                """)

            rows = cursor.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                # 获取每个知识项的标签
                item['tags'] = self.get_tags(item['id'])
                items.append(item)
            return items
        finally:
            cursor.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict[str, Any]: 统计信息，包括：
                - total_items: 总知识项数
                - items_by_type: 按类型分组的数量
                - total_tags: 总标签数
                - total_chunks: 总分块数
        """
        cursor = self.conn.cursor()
        try:
            # 总知识项数
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            total_items = cursor.fetchone()[0]

            # 按类型分组
            cursor.execute("""
                SELECT content_type, COUNT(*) as count 
                FROM knowledge 
                GROUP BY content_type
            """)
            items_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # 总标签数
            cursor.execute("SELECT COUNT(*) FROM tags")
            total_tags = cursor.fetchone()[0]

            # 总分块数
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

    # ---- Utility ----

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def reset(self) -> bool:
        """
        重置数据库（删除并重新创建所有表）

        Returns:
            bool: 是否重置成功
        """
        try:
            with self._transaction() as cursor:
                # 删除所有表（按依赖顺序）
                cursor.execute("DROP TABLE IF EXISTS knowledge_fts")
                cursor.execute("DROP TABLE IF EXISTS chunks")
                cursor.execute("DROP TABLE IF EXISTS knowledge_tags")
                cursor.execute("DROP TABLE IF EXISTS tags")
                cursor.execute("DROP TABLE IF EXISTS knowledge")

                # 删除触发器
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_ai")
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_ad")
                cursor.execute("DROP TRIGGER IF EXISTS knowledge_au")

            # 重新初始化
            self._init_db()
            return True
        except Exception:
            return False

    def __enter__(self) -> "SQLiteStorage":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.close()
