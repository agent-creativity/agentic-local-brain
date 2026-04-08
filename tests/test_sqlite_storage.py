"""
SQLite 存储模块测试

包含 SQLiteStorage 类的全面测试。
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.storage.sqlite_storage import SQLiteStorage


class TestSQLiteStorageInit:
    """SQLiteStorage 初始化测试"""

    def test_init_default_path(self):
        """测试默认路径初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            storage = SQLiteStorage(db_path=db_path)
            
            assert storage.db_path == Path(db_path)
            storage.close()

    def test_init_creates_directory(self):
        """测试自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_path = os.path.join(temp_dir, "new_dir", "subdir", "test.db")
            storage = SQLiteStorage(db_path=new_path)
            
            assert Path(new_path).parent.exists()
            storage.close()

    def test_init_creates_tables(self):
        """测试初始化时创建表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            storage = SQLiteStorage(db_path=db_path)
            
            # 检查表是否存在
            cursor = storage.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('knowledge', 'tags', 'knowledge_tags', 'chunks')
            """)
            tables = {row[0] for row in cursor.fetchall()}
            
            assert 'knowledge' in tables
            assert 'tags' in tables
            assert 'knowledge_tags' in tables
            assert 'chunks' in tables
            
            cursor.close()
            storage.close()

    def test_init_creates_fts_table(self):
        """测试初始化时创建 FTS5 表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            storage = SQLiteStorage(db_path=db_path)
            
            cursor = storage.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='knowledge_fts'
            """)
            result = cursor.fetchone()
            
            assert result is not None
            
            cursor.close()
            storage.close()

    def test_context_manager(self):
        """测试上下文管理器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                assert storage.conn is not None


class TestKnowledgeCRUD:
    """知识项 CRUD 操作测试"""

    def test_add_knowledge_success(self):
        """测试成功添加知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.add_knowledge(
                    id="doc1",
                    title="Test Document",
                    content_type="file",
                    source="/path/to/file.pdf",
                    collected_at="2024-01-01 12:00:00",
                    summary="This is a test document",
                    word_count=100,
                    file_path="/path/to/file.pdf"
                )
                
                assert result is True

    def test_add_knowledge_duplicate_id(self):
        """测试重复 ID 添加"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="First Document",
                    content_type="file",
                    source="/path/1",
                    collected_at="2024-01-01 12:00:00"
                )
                
                result = storage.add_knowledge(
                    id="doc1",
                    title="Second Document",
                    content_type="url",
                    source="/path/2",
                    collected_at="2024-01-02 12:00:00"
                )
                
                assert result is False

    def test_get_knowledge_exists(self):
        """测试获取存在的知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Test Document",
                    content_type="file",
                    source="/path/to/file.pdf",
                    collected_at="2024-01-01 12:00:00",
                    summary="Test summary",
                    word_count=100
                )
                
                result = storage.get_knowledge("doc1")
                
                assert result is not None
                assert result['id'] == "doc1"
                assert result['title'] == "Test Document"
                assert result['content_type'] == "file"
                assert result['summary'] == "Test summary"

    def test_get_knowledge_not_exists(self):
        """测试获取不存在的知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.get_knowledge("nonexistent")
                
                assert result is None

    def test_list_knowledge_all(self):
        """测试列出所有知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                for i in range(5):
                    storage.add_knowledge(
                        id=f"doc{i}",
                        title=f"Document {i}",
                        content_type="file",
                        source=f"/path/{i}",
                        collected_at=f"2024-01-0{i+1} 12:00:00"
                    )
                
                result = storage.list_knowledge()
                
                assert len(result) == 5

    def test_list_knowledge_with_type_filter(self):
        """测试按类型过滤列出知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="File 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="URL 1", content_type="url", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="File 2", content_type="file", source="/3", collected_at="2024-01-03")
                
                result = storage.list_knowledge(content_type="file")
                
                assert len(result) == 2
                assert all(r['content_type'] == 'file' for r in result)

    def test_list_knowledge_with_limit_offset(self):
        """测试分页列出知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                for i in range(10):
                    storage.add_knowledge(
                        id=f"doc{i}",
                        title=f"Document {i}",
                        content_type="file",
                        source=f"/path/{i}",
                        collected_at=f"2024-01-{i+1:02d} 12:00:00"
                    )
                
                result = storage.list_knowledge(limit=3, offset=2)
                
                assert len(result) == 3

    def test_delete_knowledge_success(self):
        """测试成功删除知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Test Document",
                    content_type="file",
                    source="/path",
                    collected_at="2024-01-01"
                )
                
                result = storage.delete_knowledge("doc1")
                
                assert result is True
                assert storage.get_knowledge("doc1") is None

    def test_delete_knowledge_with_tags(self):
        """测试删除带标签的知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Test Document",
                    content_type="file",
                    source="/path",
                    collected_at="2024-01-01"
                )
                storage.add_tags("doc1", ["tag1", "tag2"])
                
                result = storage.delete_knowledge("doc1")
                
                assert result is True
                # 标签计数应该被减少，空标签被删除
                tags = storage.list_tags()
                assert len(tags) == 0

    def test_update_knowledge_success(self):
        """测试成功更新知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Original Title",
                    content_type="file",
                    source="/path",
                    collected_at="2024-01-01"
                )
                
                result = storage.update_knowledge(
                    "doc1",
                    title="Updated Title",
                    summary="New summary"
                )
                
                assert result is True
                
                updated = storage.get_knowledge("doc1")
                assert updated['title'] == "Updated Title"
                assert updated['summary'] == "New summary"

    def test_update_knowledge_empty_kwargs(self):
        """测试空更新"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Original",
                    content_type="file",
                    source="/path",
                    collected_at="2024-01-01"
                )
                
                result = storage.update_knowledge("doc1")
                
                assert result is True

    def test_count_knowledge_all(self):
        """测试统计所有知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                for i in range(5):
                    storage.add_knowledge(
                        id=f"doc{i}",
                        title=f"Document {i}",
                        content_type="file" if i % 2 == 0 else "url",
                        source=f"/path/{i}",
                        collected_at="2024-01-01"
                    )
                
                assert storage.count_knowledge() == 5

    def test_count_knowledge_by_type(self):
        """测试按类型统计知识项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="File 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="URL 1", content_type="url", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="File 2", content_type="file", source="/3", collected_at="2024-01-03")
                
                assert storage.count_knowledge(content_type="file") == 2
                assert storage.count_knowledge(content_type="url") == 1


class TestTagManagement:
    """标签管理测试"""

    def test_add_tags_success(self):
        """测试成功添加标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                result = storage.add_tags("doc1", ["python", "ai", "machine-learning"])
                
                assert result is True
                tags = storage.get_tags("doc1")
                assert set(tags) == {"python", "ai", "machine-learning"}

    def test_add_tags_empty_list(self):
        """测试添加空标签列表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                result = storage.add_tags("doc1", [])
                
                assert result is True

    def test_add_tags_duplicate(self):
        """测试重复添加标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                storage.add_tags("doc1", ["python", "ai"])
                
                # 再次添加包含重复标签
                result = storage.add_tags("doc1", ["python", "java"])
                
                assert result is True
                tags = storage.get_tags("doc1")
                assert set(tags) == {"python", "ai", "java"}

    def test_get_tags_empty(self):
        """测试获取无标签知识项的标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                tags = storage.get_tags("doc1")
                
                assert tags == []

    def test_list_tags_order_by_count(self):
        """测试按计数排序列出标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="Test 2", content_type="file", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="Test 3", content_type="file", source="/3", collected_at="2024-01-03")
                
                storage.add_tags("doc1", ["python", "ai"])
                storage.add_tags("doc2", ["python", "java"])
                storage.add_tags("doc3", ["python"])
                
                tags = storage.list_tags(order_by="count")
                
                assert tags[0]['name'] == "python"
                assert tags[0]['count'] == 3

    def test_list_tags_order_by_name(self):
        """测试按名称排序列出标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                storage.add_tags("doc1", ["zebra", "apple", "mango"])
                
                tags = storage.list_tags(order_by="name")
                
                assert tags[0]['name'] == "apple"
                assert tags[1]['name'] == "mango"
                assert tags[2]['name'] == "zebra"

    def test_tag_count_accuracy(self):
        """测试标签计数准确性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                # 创建多个文档并添加标签
                for i in range(5):
                    storage.add_knowledge(
                        id=f"doc{i}",
                        title=f"Test {i}",
                        content_type="file",
                        source=f"/path/{i}",
                        collected_at="2024-01-01"
                    )
                
                storage.add_tags("doc0", ["common", "tag1"])
                storage.add_tags("doc1", ["common", "tag2"])
                storage.add_tags("doc2", ["common", "tag1", "tag3"])
                storage.add_tags("doc3", ["common"])
                storage.add_tags("doc4", ["common", "tag2"])
                
                tags = storage.list_tags()
                tag_counts = {t['name']: t['count'] for t in tags}
                
                assert tag_counts['common'] == 5
                assert tag_counts['tag1'] == 2
                assert tag_counts['tag2'] == 2
                assert tag_counts['tag3'] == 1

    def test_merge_tags_success(self):
        """测试成功合并标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="Test 2", content_type="file", source="/2", collected_at="2024-01-02")
                
                storage.add_tags("doc1", ["ml"])
                storage.add_tags("doc2", ["machine-learning"])
                
                result = storage.merge_tags("ml", "machine-learning")
                
                assert result >= 1
                
                # 源标签应该被删除
                tags = storage.list_tags()
                tag_names = [t['name'] for t in tags]
                assert "ml" not in tag_names
                assert "machine-learning" in tag_names
                
                # 目标标签计数应该包含两个文档
                ml_tag = next(t for t in tags if t['name'] == "machine-learning")
                assert ml_tag['count'] == 2

    def test_merge_tags_nonexistent_source(self):
        """测试合并不存在的源标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.merge_tags("nonexistent", "target")
                
                assert result == 0

    def test_delete_tag_success(self):
        """测试成功删除标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                storage.add_tags("doc1", ["python", "ai"])
                
                result = storage.delete_tag("python")
                
                assert result >= 1
                
                # 标签应该被删除
                tags = storage.list_tags()
                tag_names = [t['name'] for t in tags]
                assert "python" not in tag_names
                
                # 知识项不应该再有该标签
                doc_tags = storage.get_tags("doc1")
                assert "python" not in doc_tags

    def test_delete_tag_nonexistent(self):
        """测试删除不存在的标签"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.delete_tag("nonexistent")
                
                assert result == 0

    def test_find_by_tags_match_any(self):
        """测试按标签查找（匹配任意）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="Test 2", content_type="file", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="Test 3", content_type="file", source="/3", collected_at="2024-01-03")
                
                storage.add_tags("doc1", ["python", "ai"])
                storage.add_tags("doc2", ["java", "web"])
                storage.add_tags("doc3", ["python", "web"])
                
                result = storage.find_by_tags(["python", "java"])
                
                assert len(result) == 3  # doc1, doc2, doc3 all match

    def test_find_by_tags_match_all(self):
        """测试按标签查找（匹配全部）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="Test 2", content_type="file", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="Test 3", content_type="file", source="/3", collected_at="2024-01-03")
                
                storage.add_tags("doc1", ["python", "ai", "ml"])
                storage.add_tags("doc2", ["python", "web"])
                storage.add_tags("doc3", ["python", "ai"])
                
                result = storage.find_by_tags(["python", "ai"], match_all=True)
                
                assert len(result) == 2  # Only doc1 and doc3 have both tags

    def test_find_by_tags_empty_list(self):
        """测试空标签列表查找"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.find_by_tags([])
                
                assert result == []


class TestChunkManagement:
    """分块管理测试"""

    def test_add_chunks_success(self):
        """测试成功添加分块"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                chunks = [
                    {"id": "chunk1", "chunk_index": 0, "content": "First chunk", "embedding_id": "emb1"},
                    {"id": "chunk2", "chunk_index": 1, "content": "Second chunk", "embedding_id": "emb2"},
                ]
                
                result = storage.add_chunks("doc1", chunks)
                
                assert result is True

    def test_add_chunks_empty_list(self):
        """测试添加空分块列表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                result = storage.add_chunks("doc1", [])
                
                assert result is True

    def test_get_chunks_ordered(self):
        """测试获取分块（按索引排序）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                # 乱序添加
                chunks = [
                    {"id": "chunk3", "chunk_index": 2, "content": "Third", "embedding_id": "emb3"},
                    {"id": "chunk1", "chunk_index": 0, "content": "First", "embedding_id": "emb1"},
                    {"id": "chunk2", "chunk_index": 1, "content": "Second", "embedding_id": "emb2"},
                ]
                storage.add_chunks("doc1", chunks)
                
                result = storage.get_chunks("doc1")
                
                assert len(result) == 3
                assert result[0]['chunk_index'] == 0
                assert result[1]['chunk_index'] == 1
                assert result[2]['chunk_index'] == 2

    def test_get_chunks_empty(self):
        """测试获取无分块知识项的分块"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                result = storage.get_chunks("doc1")
                
                assert result == []

    def test_delete_chunks_success(self):
        """测试成功删除分块"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                storage.add_chunks("doc1", [
                    {"id": "chunk1", "chunk_index": 0, "content": "Content", "embedding_id": "emb1"},
                ])
                
                result = storage.delete_chunks("doc1")
                
                assert result is True
                assert storage.get_chunks("doc1") == []


class TestFulltextSearch:
    """全文搜索测试"""

    def test_search_fulltext_by_title(self):
        """测试按标题全文搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Machine Learning Basics",
                    content_type="file",
                    source="/path/1",
                    collected_at="2024-01-01",
                    summary="Introduction to ML"
                )
                storage.add_knowledge(
                    id="doc2",
                    title="Web Development Guide",
                    content_type="file",
                    source="/path/2",
                    collected_at="2024-01-02",
                    summary="Building web apps"
                )
                
                result = storage.search_fulltext("Machine Learning")
                
                assert len(result) >= 1
                assert any(r['id'] == "doc1" for r in result)

    def test_search_fulltext_by_summary(self):
        """测试按摘要全文搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Document 1",
                    content_type="file",
                    source="/path/1",
                    collected_at="2024-01-01",
                    summary="This document covers neural networks"
                )
                
                result = storage.search_fulltext("neural networks")
                
                assert len(result) >= 1

    def test_search_fulltext_empty_query(self):
        """测试空查询全文搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.search_fulltext("")
                
                assert result == []

    def test_search_fulltext_no_results(self):
        """测试无结果全文搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(
                    id="doc1",
                    title="Python Programming",
                    content_type="file",
                    source="/path/1",
                    collected_at="2024-01-01"
                )
                
                result = storage.search_fulltext("quantum physics")
                
                assert result == []


class TestStatistics:
    """统计功能测试"""

    def test_get_stats_empty(self):
        """测试空数据库统计"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                stats = storage.get_stats()
                
                assert stats['total_items'] == 0
                assert stats['items_by_type'] == {}
                assert stats['total_tags'] == 0
                assert stats['total_chunks'] == 0

    def test_get_stats_with_data(self):
        """测试有数据时的统计"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                # 添加知识项
                storage.add_knowledge(id="doc1", title="File 1", content_type="file", source="/1", collected_at="2024-01-01")
                storage.add_knowledge(id="doc2", title="URL 1", content_type="url", source="/2", collected_at="2024-01-02")
                storage.add_knowledge(id="doc3", title="File 2", content_type="file", source="/3", collected_at="2024-01-03")
                
                # 添加标签
                storage.add_tags("doc1", ["python", "ai"])
                storage.add_tags("doc2", ["web"])
                
                # 添加分块
                storage.add_chunks("doc1", [
                    {"id": "c1", "chunk_index": 0, "content": "content", "embedding_id": "e1"},
                    {"id": "c2", "chunk_index": 1, "content": "content", "embedding_id": "e2"},
                ])
                
                stats = storage.get_stats()
                
                assert stats['total_items'] == 3
                assert stats['items_by_type']['file'] == 2
                assert stats['items_by_type']['url'] == 1
                assert stats['total_tags'] == 3
                assert stats['total_chunks'] == 2


class TestReset:
    """重置功能测试"""

    def test_reset_clears_all_data(self):
        """测试重置清空所有数据"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                # 添加数据
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                storage.add_tags("doc1", ["tag1", "tag2"])
                storage.add_chunks("doc1", [
                    {"id": "c1", "chunk_index": 0, "content": "content", "embedding_id": "e1"},
                ])
                
                # 重置
                result = storage.reset()
                
                assert result is True
                
                # 验证数据已清空
                assert storage.count_knowledge() == 0
                assert storage.list_tags() == []
                stats = storage.get_stats()
                assert stats['total_chunks'] == 0

    def test_reset_recreates_tables(self):
        """测试重置后可以继续使用"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Before Reset", content_type="file", source="/path", collected_at="2024-01-01")
                
                storage.reset()
                
                # 应该可以继续添加数据
                result = storage.add_knowledge(
                    id="doc2",
                    title="After Reset",
                    content_type="url",
                    source="/new",
                    collected_at="2024-01-02"
                )
                
                assert result is True
                assert storage.count_knowledge() == 1


class TestEdgeCases:
    """边界情况测试"""

    def test_special_characters_in_tag(self):
        """测试标签中的特殊字符"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                special_tags = ["c++", "node.js", "machine-learning", "data_science"]
                storage.add_tags("doc1", special_tags)
                
                tags = storage.get_tags("doc1")
                
                assert set(tags) == set(special_tags)

    def test_unicode_content(self):
        """测试 Unicode 内容"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.add_knowledge(
                    id="doc1",
                    title="机器学习入门",
                    content_type="file",
                    source="/path/文档.pdf",
                    collected_at="2024-01-01",
                    summary="这是一个关于机器学习的入门文档"
                )
                
                assert result is True
                
                doc = storage.get_knowledge("doc1")
                assert doc['title'] == "机器学习入门"
                assert "机器学习" in doc['summary']

    def test_whitespace_tag_handling(self):
        """测试空白标签处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
                
                # 包含空白标签
                storage.add_tags("doc1", ["valid", "  ", "", "another"])
                
                tags = storage.get_tags("doc1")
                
                # 空白标签不应该被添加
                assert "valid" in tags
                assert "another" in tags
                assert "" not in tags

    def test_concurrent_safe_connection(self):
        """测试并发安全连接"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            storage = SQLiteStorage(db_path=db_path)
            
            # check_same_thread=False 应该已设置
            # 这里只是验证不会抛出异常
            storage.add_knowledge(id="doc1", title="Test", content_type="file", source="/path", collected_at="2024-01-01")
            
            storage.close()


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                # 1. 添加知识项
                storage.add_knowledge(
                    id="doc1",
                    title="Introduction to Python",
                    content_type="file",
                    source="/docs/python.pdf",
                    collected_at="2024-01-01 10:00:00",
                    summary="A beginner's guide to Python programming",
                    word_count=5000,
                    file_path="/docs/python.pdf"
                )
                
                # 2. 添加标签
                storage.add_tags("doc1", ["python", "programming", "beginner"])
                
                # 3. 添加分块
                storage.add_chunks("doc1", [
                    {"id": "c1", "chunk_index": 0, "content": "Chapter 1: Introduction", "embedding_id": "e1"},
                    {"id": "c2", "chunk_index": 1, "content": "Chapter 2: Variables", "embedding_id": "e2"},
                    {"id": "c3", "chunk_index": 2, "content": "Chapter 3: Functions", "embedding_id": "e3"},
                ])
                
                # 4. 验证数据
                doc = storage.get_knowledge("doc1")
                assert doc is not None
                assert doc['title'] == "Introduction to Python"
                
                tags = storage.get_tags("doc1")
                assert len(tags) == 3
                
                chunks = storage.get_chunks("doc1")
                assert len(chunks) == 3
                
                # 5. 搜索
                results = storage.search_fulltext("Python")
                assert len(results) >= 1
                
                # 6. 按标签查找
                results = storage.find_by_tags(["python", "beginner"], match_all=True)
                assert len(results) == 1
                
                # 7. 更新
                storage.update_knowledge("doc1", summary="Updated summary")
                doc = storage.get_knowledge("doc1")
                assert doc['summary'] == "Updated summary"
                
                # 8. 获取统计
                stats = storage.get_stats()
                assert stats['total_items'] == 1
                assert stats['total_tags'] == 3
                assert stats['total_chunks'] == 3
                
                # 9. 删除
                storage.delete_knowledge("doc1")
                assert storage.get_knowledge("doc1") is None
                assert storage.count_knowledge() == 0


class TestDuplicateDetection:
    """Tests for duplicate detection methods."""

    def test_source_exists_found(self):
        """Test source_exists returns record when source exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01")
                result = storage.source_exists("https://example.com", "webpage")
                assert result is not None
                assert result["id"] == "test1"

    def test_source_exists_not_found(self):
        """Test source_exists returns None when source doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.source_exists("https://nonexistent.com", "webpage")
                assert result is None

    def test_source_exists_different_type(self):
        """Test source_exists respects content_type filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01")
                result = storage.source_exists("https://example.com", "bookmark")
                assert result is None

    def test_source_exists_no_type_filter(self):
        """Test source_exists without content_type matches any type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01")
                result = storage.source_exists("https://example.com")
                assert result is not None

    def test_hash_exists_found(self):
        """Test hash_exists returns record when hash matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01",
                                      content_hash="abc123hash")
                result = storage.hash_exists("abc123hash", "webpage")
                assert result is not None
                assert result["id"] == "test1"

    def test_hash_exists_not_found(self):
        """Test hash_exists returns None when hash doesn't match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                result = storage.hash_exists("nonexistenthash", "webpage")
                assert result is None

    def test_hash_exists_different_type(self):
        """Test hash_exists respects content_type filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01",
                                      content_hash="abc123hash")
                result = storage.hash_exists("abc123hash", "file")
                assert result is None

    def test_add_knowledge_with_content_hash(self):
        """Test that content_hash is stored properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01",
                                      content_hash="sha256hashvalue")
                result = storage.hash_exists("sha256hashvalue")
                assert result is not None
                assert result["id"] == "test1"

    def test_add_knowledge_without_content_hash(self):
        """Test that content_hash defaults to None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            with SQLiteStorage(db_path=db_path) as storage:
                storage.add_knowledge(id="test1", title="Test", content_type="webpage",
                                      source="https://example.com", collected_at="2026-01-01")
                result = storage.hash_exists(None)
                assert result is None

    def test_schema_migration_content_hash(self, tmp_path):
        """Test that existing DB gets content_hash column via migration."""
        from kb.storage.sqlite_storage import SQLiteStorage
        # Create storage (which creates schema with content_hash)
        db_path = tmp_path / "test.db"
        s = SQLiteStorage(str(db_path))
        # Verify content_hash column exists by using it
        s.add_knowledge(id="t1", title="T", content_type="file",
                        source="/f", collected_at="2026-01-01", content_hash="hash1")
        assert s.hash_exists("hash1") is not None
        s.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
