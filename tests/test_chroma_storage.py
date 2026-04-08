"""
Chroma 存储模块测试模块

包含 ChromaStorage 类的全面测试。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb.storage.chroma_storage import ChromaStorage


class TestChromaStorageInit:
    """ChromaStorage 初始化测试"""

    def test_init_missing_package(self):
        """测试缺少 chromadb 包"""
        with patch('kb.storage.chroma_storage.chromadb', None):
            with patch('kb.storage.chroma_storage.Settings', None):
                with pytest.raises(ImportError) as exc_info:
                    ChromaStorage(path="/tmp/test_chroma")
                assert "chromadb package is required" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_init_success(self, mock_settings, mock_chromadb):
        """测试成功初始化"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            assert storage.path == Path(temp_dir)
            assert storage.collection_name == "knowledge"
            mock_chromadb.PersistentClient.assert_called_once()
            mock_client.get_or_create_collection.assert_called_once()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_init_custom_collection_name(self, mock_settings, mock_chromadb):
        """测试自定义集合名称"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(
                path=temp_dir,
                collection_name="custom_collection"
            )

            assert storage.collection_name == "custom_collection"
            mock_client.get_or_create_collection.assert_called_once_with(
                name="custom_collection",
                metadata={"hnsw:space": "cosine"}
            )

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_init_creates_directory(self, mock_settings, mock_chromadb):
        """测试创建目录"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            new_path = Path(temp_dir) / "new_dir" / "chroma_db"
            storage = ChromaStorage(path=str(new_path))

            assert new_path.exists()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_init_expands_user_path(self, mock_settings, mock_chromadb):
        """测试展开用户路径"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch('pathlib.Path.mkdir'):
            storage = ChromaStorage(path="~/test_chroma")

            assert str(storage.path).startswith(os.path.expanduser("~"))


class TestChromaStorageAddDocuments:
    """ChromaStorage 添加文档测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_success(self, mock_settings, mock_chromadb):
        """测试成功添加文档"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.add_documents(
                ids=["doc1", "doc2"],
                embeddings=[[0.1, 0.2], [0.3, 0.4]],
                metadatas=[{"source": "file1"}, {"source": "file2"}],
                documents=["文本1", "文本2"]
            )

            assert result is True
            mock_collection.add.assert_called_once()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_minimal(self, mock_settings, mock_chromadb):
        """测试最小参数添加"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.add_documents(
                ids=["doc1"],
                embeddings=[[0.1, 0.2]]
            )

            assert result is True

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_empty_ids(self, mock_settings, mock_chromadb):
        """测试空 ID 列表"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.add_documents(
                    ids=[],
                    embeddings=[]
                )

            assert "cannot be empty" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_empty_embeddings(self, mock_settings, mock_chromadb):
        """测试空向量列表"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.add_documents(
                    ids=["doc1"],
                    embeddings=[]
                )

            assert "cannot be empty" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_length_mismatch(self, mock_settings, mock_chromadb):
        """测试长度不匹配"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.add_documents(
                    ids=["doc1", "doc2"],
                    embeddings=[[0.1, 0.2]]
                )

            assert "same length" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_metadata_length_mismatch(self, mock_settings, mock_chromadb):
        """测试元数据长度不匹配"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.add_documents(
                    ids=["doc1", "doc2"],
                    embeddings=[[0.1, 0.2], [0.3, 0.4]],
                    metadatas=[{"source": "file1"}]
                )

            assert "must match" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_add_documents_exception(self, mock_settings, mock_chromadb):
        """测试添加异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Add failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.add_documents(
                    ids=["doc1"],
                    embeddings=[[0.1, 0.2]]
                )

            assert "Failed to add documents" in str(exc_info.value)


class TestChromaStorageQuery:
    """ChromaStorage 查询测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_query_success(self, mock_settings, mock_chromadb):
        """测试成功查询"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"source": "file1"}, {"source": "file2"}]],
            "documents": [["文本1", "文本2"]]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.query(
                embedding=[0.15, 0.25],
                top_k=2
            )

            assert len(result["ids"]) == 2
            assert result["ids"] == ["doc1", "doc2"]
            assert result["distances"] == [0.1, 0.2]
            assert len(result["metadatas"]) == 2
            assert len(result["documents"]) == 2

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_query_with_filter(self, mock_settings, mock_chromadb):
        """测试带过滤条件的查询"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "file1"}]],
            "documents": [["文本1"]]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.query(
                embedding=[0.15, 0.25],
                top_k=5,
                where_filter={"source": "file1"}
            )

            mock_collection.query.assert_called_once()
            call_kwargs = mock_collection.query.call_args[1]
            assert call_kwargs["where"] == {"source": "file1"}

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_query_empty_embedding(self, mock_settings, mock_chromadb):
        """测试空查询向量"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.query(embedding=[])

            assert "cannot be empty" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_query_exception(self, mock_settings, mock_chromadb):
        """测试查询异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.side_effect = Exception("Query failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.query(embedding=[0.1, 0.2])

            assert "Failed to query documents" in str(exc_info.value)


class TestChromaStorageDelete:
    """ChromaStorage 删除测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_delete_success(self, mock_settings, mock_chromadb):
        """测试成功删除"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.delete(ids=["doc1", "doc2"])

            assert result is True
            mock_collection.delete.assert_called_once_with(ids=["doc1", "doc2"])

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_delete_empty_ids(self, mock_settings, mock_chromadb):
        """测试空 ID 列表"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.delete(ids=[])

            assert "cannot be empty" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_delete_exception(self, mock_settings, mock_chromadb):
        """测试删除异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.delete.side_effect = Exception("Delete failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.delete(ids=["doc1"])

            assert "Failed to delete documents" in str(exc_info.value)


class TestChromaStorageCount:
    """ChromaStorage 统计测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_count_success(self, mock_settings, mock_chromadb):
        """测试成功统计"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 42
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            count = storage.count()

            assert count == 42
            mock_collection.count.assert_called_once()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_count_exception(self, mock_settings, mock_chromadb):
        """测试统计异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.side_effect = Exception("Count failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.count()

            assert "Failed to count documents" in str(exc_info.value)


class TestChromaStorageGet:
    """ChromaStorage 获取文档测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_get_success(self, mock_settings, mock_chromadb):
        """测试成功获取文档"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": ["doc1", "doc2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"source": "file1"}, {"source": "file2"}],
            "documents": ["文本1", "文本2"]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.get(ids=["doc1", "doc2"])

            assert len(result["ids"]) == 2
            assert len(result["embeddings"]) == 2
            assert len(result["metadatas"]) == 2
            assert len(result["documents"]) == 2

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_get_with_filter(self, mock_settings, mock_chromadb):
        """测试带过滤条件获取"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "embeddings": [[0.1, 0.2]],
            "metadatas": [{"source": "file1"}],
            "documents": ["文本1"]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.get(
                where_filter={"source": "file1"},
                limit=10
            )

            mock_collection.get.assert_called_once()
            call_kwargs = mock_collection.get.call_args[1]
            assert call_kwargs["where"] == {"source": "file1"}
            assert call_kwargs["limit"] == 10

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_get_exception(self, mock_settings, mock_chromadb):
        """测试获取异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.side_effect = Exception("Get failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.get()

            assert "Failed to get documents" in str(exc_info.value)


class TestChromaStorageUpdate:
    """ChromaStorage 更新测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_update_success(self, mock_settings, mock_chromadb):
        """测试成功更新"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.update(
                ids=["doc1"],
                embeddings=[[0.5, 0.6]],
                metadatas=[{"source": "updated"}],
                documents=["更新文本"]
            )

            assert result is True
            mock_collection.update.assert_called_once()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_update_empty_ids(self, mock_settings, mock_chromadb):
        """测试空 ID 列表"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(ValueError) as exc_info:
                storage.update(ids=[])

            assert "cannot be empty" in str(exc_info.value)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_update_exception(self, mock_settings, mock_chromadb):
        """测试更新异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.update.side_effect = Exception("Update failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.update(ids=["doc1"])

            assert "Failed to update documents" in str(exc_info.value)


class TestChromaStoragePeek:
    """ChromaStorage 预览测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_peek_success(self, mock_settings, mock_chromadb):
        """测试成功预览"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.peek.return_value = {
            "ids": ["doc1", "doc2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"source": "file1"}, {"source": "file2"}],
            "documents": ["文本1", "文本2"]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.peek(limit=10)

            assert len(result["ids"]) == 2
            mock_collection.peek.assert_called_once_with(limit=10)

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_peek_exception(self, mock_settings, mock_chromadb):
        """测试预览异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.peek.side_effect = Exception("Peek failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.peek()

            assert "Failed to peek documents" in str(exc_info.value)


class TestChromaStorageReset:
    """ChromaStorage 重置测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_reset_success(self, mock_settings, mock_chromadb):
        """测试成功重置"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)
            result = storage.reset()

            assert result is True
            mock_client.delete_collection.assert_called_once()
            mock_client.create_collection.assert_called_once()

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_reset_exception(self, mock_settings, mock_chromadb):
        """测试重置异常"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.delete_collection.side_effect = Exception("Reset failed")
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            with pytest.raises(Exception) as exc_info:
                storage.reset()

            assert "Failed to reset collection" in str(exc_info.value)


class TestChromaStorageIntegration:
    """ChromaStorage 集成测试"""

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_full_workflow(self, mock_settings, mock_chromadb):
        """测试完整工作流程"""
        mock_client = Mock()
        mock_collection = Mock()

        # Mock count
        mock_collection.count.return_value = 0

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "file1", "category": "tech"}]],
            "documents": [["机器学习入门"]]
        }

        # Mock get results
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "embeddings": [[0.1, 0.2, 0.3]],
            "metadatas": [{"source": "file1", "category": "tech"}],
            "documents": ["机器学习入门"]
        }

        # Mock peek results
        mock_collection.peek.return_value = {
            "ids": ["doc1"],
            "embeddings": [[0.1, 0.2]],
            "metadatas": [{"source": "file1"}],
            "documents": ["机器学习入门"]
        }

        # Mock get results
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "embeddings": [[0.1, 0.2, 0.3]],
            "metadatas": [{"source": "file1", "category": "tech"}],
            "documents": ["机器学习入门"]
        }

        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            # 初始化
            storage = ChromaStorage(path=temp_dir)
            assert storage.count() == 0

            # 添加文档
            result = storage.add_documents(
                ids=["doc1", "doc2", "doc3"],
                embeddings=[
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6],
                    [0.7, 0.8, 0.9]
                ],
                metadatas=[
                    {"source": "file1", "category": "tech"},
                    {"source": "file2", "category": "science"},
                    {"source": "file3", "category": "tech"}
                ],
                documents=["机器学习入门", "深度学习基础", "神经网络原理"]
            )
            assert result is True

            # 查询（带过滤）
            query_result = storage.query(
                embedding=[0.15, 0.25, 0.35],
                top_k=2,
                where_filter={"category": "tech"}
            )
            assert len(query_result["ids"]) == 1

            # 获取文档
            get_result = storage.get(
                where_filter={"source": "file1"}
            )
            assert len(get_result["ids"]) == 1

            # 更新文档
            update_result = storage.update(
                ids=["doc1"],
                metadatas=[{"source": "file1_updated"}]
            )
            assert update_result is True

            # 删除文档
            delete_result = storage.delete(ids=["doc1"])
            assert delete_result is True

            # 预览
            peek_result = storage.peek(limit=5)
            assert "ids" in peek_result

    @patch('kb.storage.chroma_storage.chromadb')
    @patch('kb.storage.chroma_storage.Settings')
    def test_complex_filter_query(self, mock_settings, mock_chromadb):
        """测试复杂过滤查询"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "file1", "category": "tech", "year": 2024}]],
            "documents": [["文档1"]]
        }
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ChromaStorage(path=temp_dir)

            # 复杂过滤条件
            complex_filter = {
                "$and": [
                    {"source": "file1"},
                    {"category": "tech"}
                ]
            }

            result = storage.query(
                embedding=[0.1, 0.2],
                where_filter=complex_filter
            )

            assert len(result["ids"]) == 1
            mock_collection.query.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
