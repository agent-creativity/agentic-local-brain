"""
FileCollector 单元测试

测试文件收集器的各项功能，包括：
- PDF 文件解析
- Markdown 文件读取
- TXT 文件读取
- 元数据生成
- 文件名安全处理
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kb.collectors import FileCollector
from kb.collectors.base import CollectResult


@pytest.fixture
def collector(tmp_path):
    """创建测试用的 FileCollector 实例"""
    return FileCollector(output_dir=tmp_path)


@pytest.fixture
def sample_txt_file(tmp_path):
    """创建测试用的 TXT 文件"""
    txt_file = tmp_path / "test_document.txt"
    txt_file.write_text(
        "这是一个测试文档。\n"
        "包含多行文本内容。\n"
        "用于测试 TXT 文件收集功能。",
        encoding="utf-8"
    )
    return txt_file


@pytest.fixture
def sample_md_file(tmp_path):
    """创建测试用的 Markdown 文件"""
    md_file = tmp_path / "test_article.md"
    md_file.write_text(
        "---\n"
        "title: 测试文章\n"
        "author: Test Author\n"
        "---\n\n"
        "# 测试文章标题\n\n"
        "这是文章的正文内容。\n\n"
        "## 子标题\n\n"
        "更多内容...",
        encoding="utf-8"
    )
    return md_file


@pytest.fixture
def sample_md_no_frontmatter(tmp_path):
    """创建不带 Front Matter 的 Markdown 文件"""
    md_file = tmp_path / "simple_notes.md"
    md_file.write_text(
        "# 简单笔记\n\n"
        "这是一个没有 YAML Front Matter 的 Markdown 文件。",
        encoding="utf-8"
    )
    return md_file


class TestFileCollectorInit:
    """测试 FileCollector 初始化"""

    def test_default_output_dir(self):
        """测试默认输出目录"""
        collector = FileCollector()
        expected_dir = Path.home() / ".knowledge-base" / "1_collect"
        assert collector.output_dir == expected_dir

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        collector = FileCollector(output_dir=tmp_path)
        assert collector.output_dir == tmp_path


class TestCollectTXT:
    """测试 TXT 文件收集"""

    def test_collect_txt_file(self, collector, sample_txt_file):
        """测试收集 TXT 文件"""
        result = collector.collect(sample_txt_file)

        assert result.success is True
        assert result.title == "test_document"
        assert result.word_count > 0
        assert result.file_path.exists()
        assert result.file_path.suffix == ".md"

    def test_collect_txt_with_tags(self, collector, sample_txt_file):
        """测试带标签收集 TXT 文件"""
        tags = ["测试", "文档", "TXT"]
        result = collector.collect(sample_txt_file, tags=tags)

        assert result.success is True
        assert result.tags == tags
        # 验证保存的文件包含标签
        content = result.file_path.read_text(encoding="utf-8")
        assert "测试" in content

    def test_collect_txt_with_custom_title(self, collector, sample_txt_file):
        """测试自定义标题收集"""
        custom_title = "我的自定义标题"
        result = collector.collect(sample_txt_file, title=custom_title)

        assert result.success is True
        assert result.title == custom_title
        # 验证文件名包含标题的 slug
        assert "wo-de-zi-ding-yi-biao-ti" in result.file_path.name.lower()


class TestCollectMarkdown:
    """测试 Markdown 文件收集"""

    def test_collect_md_with_frontmatter(self, collector, sample_md_file):
        """测试收集带 Front Matter 的 Markdown 文件"""
        result = collector.collect(sample_md_file)

        assert result.success is True
        assert result.title == "test_article"
        assert result.word_count > 0

        # 验证 Front Matter 被移除
        content = result.file_path.read_text(encoding="utf-8")
        # 不应该包含原来的 Front Matter
        body = content.split("---\n\n", 1)[-1]
        assert "author: Test Author" not in body

    def test_collect_md_without_frontmatter(self, collector, sample_md_no_frontmatter):
        """测试收集不带 Front Matter 的 Markdown 文件"""
        result = collector.collect(sample_md_no_frontmatter)

        assert result.success is True
        content = result.file_path.read_text(encoding="utf-8")
        assert "# 简单笔记" in content


class TestCollectPDF:
    """测试 PDF 文件收集"""

    @patch("kb.collectors.file_collector.PyPDF2")
    def test_collect_pdf_file(self, mock_pypdf2, collector, tmp_path):
        """测试收集 PDF 文件"""
        # 创建模拟 PDF
        pdf_file = tmp_path / "test_paper.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        # 模拟 PyPDF2 的行为
        mock_reader = mock_pypdf2.PdfReader.return_value
        mock_page = type("MockPage", (), {"extract_text": lambda self: "PDF 测试内容"})()
        mock_reader.pages = [mock_page]

        result = collector.collect(pdf_file)

        assert result.success is True
        assert result.title == "test_paper"
        assert result.metadata.get("file_extension", "") == ".pdf"

    def test_collect_nonexistent_file(self, collector):
        """测试收集不存在的文件"""
        result = collector.collect("/nonexistent/path/file.pdf")

        assert result.success is False
        assert "文件不存在" in result.error

    def test_collect_unsupported_format(self, collector, tmp_path):
        """测试收集不支持的文件格式"""
        unsupported_file = tmp_path / "test.docx"
        unsupported_file.write_bytes(b"fake docx content")

        result = collector.collect(unsupported_file)

        assert result.success is False
        assert "不支持的文件格式" in result.error


class TestMetadataGeneration:
    """测试元数据生成"""

    def test_metadata_structure(self, collector, sample_txt_file):
        """测试元数据结构"""
        result = collector.collect(sample_txt_file)

        assert "id" in result.metadata
        assert "title" in result.metadata
        assert "source" in result.metadata
        assert "content_type" in result.metadata
        assert "collected_at" in result.metadata
        assert "tags" in result.metadata
        assert "word_count" in result.metadata
        assert "status" in result.metadata
        assert result.metadata["content_type"] == "file"
        assert result.metadata["status"] == "processed"

    def test_metadata_with_extra_kwargs(self, collector, sample_txt_file):
        """测试额外的元数据字段"""
        result = collector.collect(
            sample_txt_file,
            custom_field="custom_value",
            another_field=123
        )

        assert result.metadata["custom_field"] == "custom_value"
        assert result.metadata["another_field"] == 123


class TestSafeFilename:
    """测试安全文件名生成"""

    def test_filename_with_chinese_title(self, collector):
        """测试中文标题的文件名生成"""
        filename = collector._generate_safe_filename("file", "测试文档标题")
        assert filename.endswith(".md")
        # 应该包含时间戳
        assert "_" in filename

    def test_filename_with_special_chars(self, collector):
        """测试特殊字符的文件名生成"""
        filename = collector._generate_safe_filename("file", "Test/Document: With*Special?Chars")
        assert filename.endswith(".md")
        # 不应该包含特殊字符
        assert "/" not in filename
        assert ":" not in filename
        assert "*" not in filename

    def test_filename_without_title(self, collector):
        """测试无标题的文件名生成"""
        filename = collector._generate_safe_filename("file")
        assert filename.endswith(".md")
        assert "file" in filename


class TestWordCount:
    """测试字数统计"""

    def test_count_chinese_words(self, collector):
        """测试中文字数统计"""
        text = "这是一个测试文档"
        count = collector._count_words(text)
        assert count == 8

    def test_count_english_words(self, collector):
        """测试英文字数统计"""
        text = "This is a test document"
        count = collector._count_words(text)
        assert count == 5

    def test_count_mixed_words(self, collector):
        """测试混合文字字数统计"""
        text = "这是一个 test document 测试"
        count = collector._count_words(text)
        # 6 个中文字符 + 2 个英文单词
        assert count == 8


class TestYAMLFormat:
    """测试 YAML 格式化"""

    def test_format_simple_metadata(self, collector):
        """测试简单元数据格式化"""
        metadata = {
            "title": "Test Title",
            "count": 100,
            "tags": ["tag1", "tag2"]
        }
        yaml_str = collector._format_yaml(metadata)

        assert "title: Test Title" in yaml_str
        assert "count: 100" in yaml_str
        assert "tags:" in yaml_str
        assert "- tag1" in yaml_str

    def test_format_datetime(self, collector):
        """测试日期时间格式化"""
        from datetime import datetime

        metadata = {"collected_at": datetime(2026, 3, 24, 14, 30, 0)}
        yaml_str = collector._format_yaml(metadata)

        assert "2026-03-24T14:30:00" in yaml_str


class TestSupportedFormats:
    """测试支持的文件格式"""

    def test_get_supported_formats(self, collector):
        """测试获取支持的文件格式"""
        formats = collector.get_supported_formats()
        assert ".pdf" in formats
        assert ".md" in formats
        assert ".txt" in formats
        assert ".markdown" in formats


class TestBaseCollectorDedup:
    """Tests for BaseCollector dedup utilities."""

    def test_generate_content_hash_deterministic(self):
        """Same content produces same hash."""
        from kb.collectors.base import BaseCollector
        hash1 = BaseCollector._generate_content_hash("test content")
        hash2 = BaseCollector._generate_content_hash("test content")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_generate_content_hash_different_content(self):
        """Different content produces different hash."""
        from kb.collectors.base import BaseCollector
        hash1 = BaseCollector._generate_content_hash("content A")
        hash2 = BaseCollector._generate_content_hash("content B")
        assert hash1 != hash2

    def test_check_duplicate_no_storage(self, tmp_path):
        """_check_duplicate returns None when no storage provided."""
        from kb.collectors.file_collector import FileCollector
        collector = FileCollector(output_dir=tmp_path)
        result = collector._check_duplicate("/some/path", storage=None)
        assert result is None

    def test_check_duplicate_source_match(self, tmp_path):
        """_check_duplicate finds duplicate by source."""
        from kb.collectors.file_collector import FileCollector
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="f1", title="Test File", content_type="file",
                              source="/path/to/file.txt", collected_at="2026-01-01")

        collector = FileCollector(output_dir=tmp_path)
        result = collector._check_duplicate("/path/to/file.txt", storage=storage)
        assert result is not None
        assert result["id"] == "f1"
        storage.close()

    def test_check_duplicate_hash_match(self, tmp_path):
        """_check_duplicate finds duplicate by content hash."""
        from kb.collectors.file_collector import FileCollector
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        content_hash = FileCollector._generate_content_hash("same content")
        storage.add_knowledge(id="f1", title="Test File", content_type="file",
                              source="/different/path.txt", collected_at="2026-01-01",
                              content_hash=content_hash)

        collector = FileCollector(output_dir=tmp_path)
        result = collector._check_duplicate("/new/path.txt", content="same content", storage=storage)
        assert result is not None
        assert result["id"] == "f1"
        storage.close()

    def test_check_duplicate_no_match(self, tmp_path):
        """_check_duplicate returns None when no duplicate exists."""
        from kb.collectors.file_collector import FileCollector
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        collector = FileCollector(output_dir=tmp_path)
        result = collector._check_duplicate("/unique/path.txt", content="unique content", storage=storage)
        assert result is None
        storage.close()

    def test_collect_result_content_hash_field(self):
        """CollectResult has content_hash field."""
        from kb.collectors.base import CollectResult
        result = CollectResult(success=True, content_hash="abc123")
        assert result.content_hash == "abc123"

        result2 = CollectResult(success=True)
        assert result2.content_hash is None


class TestFileCollectorDedup:
    """Tests for FileCollector dedup functionality."""

    def test_skip_existing_source_match(self, tmp_path):
        """collect() with skip_existing=True returns failure when source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test file
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text("Test content for dedup test", encoding="utf-8")

        storage.add_knowledge(id="file1", title="Existing File",
                              content_type="file", source=str(test_file.resolve()),
                              collected_at="2026-01-01")

        collector = FileCollector(output_dir=tmp_path)
        result = collector.collect(test_file, skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_skip_existing_no_match(self, tmp_path):
        """collect() with skip_existing=True proceeds when no duplicate."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test file
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text("Test content for dedup test", encoding="utf-8")

        collector = FileCollector(output_dir=tmp_path)
        result = collector.collect(test_file, skip_existing=True, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_skip_existing_false_allows_duplicates(self, tmp_path):
        """collect() with skip_existing=False proceeds even with existing source."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test file
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text("Test content for dedup test", encoding="utf-8")

        storage.add_knowledge(id="file1", title="Existing File",
                              content_type="file", source=str(test_file.resolve()),
                              collected_at="2026-01-01")

        collector = FileCollector(output_dir=tmp_path)
        result = collector.collect(test_file, skip_existing=False, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_content_hash_in_result(self, tmp_path):
        """collect() returns content_hash in CollectResult."""
        # Create a test file
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text("Test content for hash test", encoding="utf-8")

        collector = FileCollector(output_dir=tmp_path)
        result = collector.collect(test_file)

        assert result.success
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
