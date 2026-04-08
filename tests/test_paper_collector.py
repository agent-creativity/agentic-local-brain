"""
PaperCollector 单元测试

测试学术论文收集器的各项功能，包括：
- arXiv ID 解析
- API 响应解析
- 元数据生成
- Markdown 内容格式化
- 错误处理
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kb.collectors import PaperCollector
from kb.collectors.base import CollectResult


@pytest.fixture
def collector(tmp_path):
    """创建测试用的 PaperCollector 实例"""
    return PaperCollector(output_dir=tmp_path)


@pytest.fixture
def sample_arxiv_xml():
    """示例 arXiv API XML 响应"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query</title>
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Attention Is All You Need: A Survey</title>
    <summary>This paper presents a comprehensive survey of transformer architectures 
    and their applications in natural language processing and computer vision.</summary>
    <author>
      <name>John Doe</name>
    </author>
    <author>
      <name>Jane Smith</name>
    </author>
    <author>
      <name>Bob Johnson</name>
    </author>
    <published>2023-01-15T12:00:00Z</published>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <link href="http://arxiv.org/abs/2301.12345v1" type="text/html"/>
    <link href="http://arxiv.org/pdf/2301.12345v1" type="application/pdf"/>
  </entry>
</feed>"""


@pytest.fixture
def sample_arxiv_xml_old_format():
    """示例 arXiv API XML 响应 (旧格式 ID)"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/cond-mat/0001234v1</id>
    <title>Old Format Paper</title>
    <summary>This is an older arXiv paper with the old ID format.</summary>
    <author>
      <name>Alice Brown</name>
    </author>
    <published>2000-01-15T12:00:00Z</published>
    <category term="cond-mat"/>
    <link href="http://arxiv.org/abs/cond-mat/0001234v1" type="text/html"/>
    <link href="http://arxiv.org/pdf/cond-mat/0001234v1" type="application/pdf"/>
  </entry>
</feed>"""


@pytest.fixture
def sample_arxiv_xml_not_found():
    """示例 arXiv API XML 响应 (论文不存在)"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
</feed>"""


class TestPaperCollectorInit:
    """测试 PaperCollector 初始化"""

    def test_default_output_dir(self):
        """测试默认输出目录"""
        collector = PaperCollector()
        expected_dir = Path.home() / ".knowledge-base" / "1_collect"
        assert collector.output_dir == expected_dir

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        collector = PaperCollector(output_dir=tmp_path)
        assert collector.output_dir == tmp_path

    def test_default_timeout(self):
        """测试默认超时设置"""
        collector = PaperCollector()
        assert collector._timeout == 30

    def test_custom_timeout(self):
        """测试自定义超时设置"""
        collector = PaperCollector(timeout=60)
        assert collector._timeout == 60


class TestArxivIdParsing:
    """测试 arXiv ID 解析"""

    def test_parse_arxiv_colon_format(self, collector):
        """测试 arxiv: 前缀格式"""
        assert collector._parse_arxiv_id("arxiv:2301.12345") == "2301.12345"

    def test_parse_bare_id(self, collector):
        """测试纯 ID 格式"""
        assert collector._parse_arxiv_id("2301.12345") == "2301.12345"

    def test_parse_id_with_version(self, collector):
        """测试带版本号的 ID"""
        assert collector._parse_arxiv_id("arxiv:2301.12345v2") == "2301.12345v2"
        assert collector._parse_arxiv_id("2301.12345v3") == "2301.12345v3"

    def test_parse_abs_url(self, collector):
        """测试 abs URL 格式"""
        assert collector._parse_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"
        assert collector._parse_arxiv_id("http://arxiv.org/abs/2301.12345v1") == "2301.12345v1"

    def test_parse_pdf_url(self, collector):
        """测试 PDF URL 格式"""
        assert collector._parse_arxiv_id("https://arxiv.org/pdf/2301.12345") == "2301.12345"
        assert collector._parse_arxiv_id("https://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"

    def test_parse_old_format_id(self, collector):
        """测试旧格式 ID"""
        assert collector._parse_arxiv_id("arxiv:cond-mat/0001234") == "cond-mat/0001234"
        assert collector._parse_arxiv_id("cond-mat/0001234") == "cond-mat/0001234"

    def test_parse_invalid_id(self, collector):
        """测试无效 ID"""
        assert collector._parse_arxiv_id("invalid-id") is None
        assert collector._parse_arxiv_id("") is None
        assert collector._parse_arxiv_id("12345") is None
        assert collector._parse_arxiv_id("https://example.com/paper") is None


class TestArxivResponseParsing:
    """测试 arXiv API 响应解析"""

    def test_parse_valid_response(self, collector, sample_arxiv_xml):
        """测试解析有效响应"""
        result = collector._parse_arxiv_response(sample_arxiv_xml, "2301.12345")

        assert result is not None
        assert result["title"] == "Attention Is All You Need: A Survey"
        assert len(result["authors"]) == 3
        assert result["authors"][0] == "John Doe"
        assert "transformer" in result["abstract"].lower()
        assert "cs.CL" in result["categories"]
        assert "cs.AI" in result["categories"]
        assert result["published_date"] == "2023-01-15"
        assert result["arxiv_id"] == "2301.12345"

    def test_parse_old_format_response(self, collector, sample_arxiv_xml_old_format):
        """测试解析旧格式响应"""
        result = collector._parse_arxiv_response(sample_arxiv_xml_old_format, "cond-mat/0001234")

        assert result is not None
        assert result["title"] == "Old Format Paper"
        assert len(result["authors"]) == 1

    def test_parse_not_found_response(self, collector, sample_arxiv_xml_not_found):
        """测试解析论文不存在的响应"""
        result = collector._parse_arxiv_response(sample_arxiv_xml_not_found, "9999.99999")
        assert result is None

    def test_parse_invalid_xml(self, collector):
        """测试解析无效 XML"""
        result = collector._parse_arxiv_response("not valid xml", "2301.12345")
        assert result is None


class TestContentExtraction:
    """测试内容提取"""

    def test_extract_content_format(self, collector):
        """测试提取的内容格式"""
        paper_info = {
            "title": "Test Paper Title",
            "authors": ["Author One", "Author Two"],
            "abstract": "This is the abstract text.",
            "categories": ["cs.AI", "cs.LG"],
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "arxiv_url": "https://arxiv.org/abs/2301.12345",
        }

        content = collector._extract_content(paper_info)

        assert "# Test Paper Title" in content
        assert "## Authors" in content
        assert "Author One, Author Two" in content
        assert "## Abstract" in content
        assert "This is the abstract text." in content
        assert "## Categories" in content
        assert "cs.AI, cs.LG" in content
        assert "## Links" in content
        assert "[PDF](" in content
        assert "[arXiv](" in content


class TestMetadataGeneration:
    """测试元数据生成"""

    def test_metadata_structure(self, collector):
        """测试元数据结构"""
        paper_info = {
            "title": "Test Paper",
            "authors": ["Author One"],
            "abstract": "Abstract text",
            "categories": ["cs.AI"],
            "arxiv_id": "2301.12345",
            "published_date": "2023-01-15",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
        }

        metadata = collector._generate_metadata(
            title="Test Paper",
            content="Test content",
            source="arxiv:2301.12345",
            tags=["AI", "ML"],
            paper_info=paper_info,
        )

        assert metadata["id"] == "paper_2301.12345"
        assert metadata["title"] == "Test Paper"
        assert metadata["source"] == "arxiv:2301.12345"
        assert metadata["content_type"] == "paper"
        assert metadata["tags"] == ["AI", "ML"]
        assert metadata["authors"] == ["Author One"]
        assert metadata["arxiv_id"] == "2301.12345"
        assert metadata["categories"] == ["cs.AI"]
        assert metadata["published_date"] == "2023-01-15"
        assert metadata["status"] == "processed"

    def test_metadata_old_format_id(self, collector):
        """测试旧格式 ID 的元数据生成"""
        paper_info = {
            "title": "Old Paper",
            "authors": [],
            "abstract": "",
            "categories": [],
            "arxiv_id": "cond-mat/0001234",
            "published_date": "",
            "pdf_url": "",
        }

        metadata = collector._generate_metadata(
            title="Old Paper",
            content="Content",
            source="arxiv:cond-mat/0001234",
            paper_info=paper_info,
        )

        # 旧格式 ID 中的 / 应该被替换为 _
        assert metadata["id"] == "paper_cond-mat_0001234"


class TestCollect:
    """测试完整的收集流程"""

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_collect_success(self, mock_fetch, collector):
        """测试成功收集"""
        mock_fetch.return_value = {
            "title": "Test Paper Title",
            "authors": ["Author One", "Author Two"],
            "abstract": "This is the abstract.",
            "categories": ["cs.AI"],
            "arxiv_id": "2301.12345",
            "published_date": "2023-01-15",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "arxiv_url": "https://arxiv.org/abs/2301.12345",
        }

        result = collector.collect("arxiv:2301.12345", tags=["AI"])

        assert result.success is True
        assert result.title == "Test Paper Title"
        assert result.word_count > 0
        assert result.file_path.exists()
        assert result.file_path.suffix == ".md"
        assert result.tags == ["AI"]

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_collect_with_url(self, mock_fetch, collector):
        """测试使用 URL 收集"""
        mock_fetch.return_value = {
            "title": "Test Paper",
            "authors": ["Author"],
            "abstract": "Abstract",
            "categories": ["cs.AI"],
            "arxiv_id": "2301.12345",
            "published_date": "2023-01-15",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "arxiv_url": "https://arxiv.org/abs/2301.12345",
        }

        result = collector.collect("https://arxiv.org/abs/2301.12345")

        assert result.success is True

    def test_collect_invalid_id(self, collector):
        """测试无效 ID"""
        result = collector.collect("invalid-paper-id")

        assert result.success is False
        assert "Invalid arXiv ID format" in result.error

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_collect_paper_not_found(self, mock_fetch, collector):
        """测试论文不存在"""
        mock_fetch.return_value = None

        result = collector.collect("arxiv:9999.99999")

        assert result.success is False
        assert "Paper not found" in result.error

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_collect_timeout(self, mock_fetch, collector):
        """测试超时错误"""
        import httpx

        mock_fetch.side_effect = httpx.TimeoutException("Timeout")

        result = collector.collect("arxiv:2301.12345")

        assert result.success is False
        assert "timeout" in result.error.lower()

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_collect_network_error(self, mock_fetch, collector):
        """测试网络错误"""
        import httpx

        mock_fetch.side_effect = httpx.RequestError("Connection failed")

        result = collector.collect("arxiv:2301.12345")

        assert result.success is False
        assert "Network error" in result.error


class TestSavedFileContent:
    """测试保存的文件内容"""

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_file_contains_yaml_frontmatter(self, mock_fetch, collector):
        """测试文件包含 YAML Front Matter"""
        mock_fetch.return_value = {
            "title": "Test Paper",
            "authors": ["Author One"],
            "abstract": "Abstract text",
            "categories": ["cs.AI"],
            "arxiv_id": "2301.12345",
            "published_date": "2023-01-15",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "arxiv_url": "https://arxiv.org/abs/2301.12345",
        }

        result = collector.collect("arxiv:2301.12345")

        content = result.file_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "id:" in content
        assert "title:" in content
        assert "content_type: paper" in content
        assert "arxiv_id: 2301.12345" in content
        assert "authors:" in content

    @patch.object(PaperCollector, "_fetch_paper_info")
    def test_file_contains_markdown_content(self, mock_fetch, collector):
        """测试文件包含 Markdown 内容"""
        mock_fetch.return_value = {
            "title": "Transformer Architecture",
            "authors": ["Author One", "Author Two"],
            "abstract": "This paper introduces a new architecture.",
            "categories": ["cs.AI", "cs.CL"],
            "arxiv_id": "2301.12345",
            "published_date": "2023-01-15",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "arxiv_url": "https://arxiv.org/abs/2301.12345",
        }

        result = collector.collect("arxiv:2301.12345")

        content = result.file_path.read_text(encoding="utf-8")
        assert "# Transformer Architecture" in content
        assert "## Authors" in content
        assert "## Abstract" in content
        assert "## Links" in content
        assert "[PDF]" in content
        assert "[arXiv]" in content


class TestCleanText:
    """测试文本清理"""

    def test_clean_text_removes_extra_whitespace(self, collector):
        """测试移除多余空白"""
        text = "This   is\n\na    test"
        cleaned = collector._clean_text(text)
        assert cleaned == "This is a test"

    def test_clean_text_strips(self, collector):
        """测试去除首尾空白"""
        text = "  Test text  "
        cleaned = collector._clean_text(text)
        assert cleaned == "Test text"


class TestPaperCollectorDedup:
    """Tests for PaperCollector dedup functionality."""

    def test_skip_existing_source_match(self, tmp_path):
        """collect() with skip_existing=True returns failure when source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="paper1", title="Existing Paper",
                              content_type="paper", source="arxiv:2301.12345",
                              collected_at="2026-01-01")

        collector = PaperCollector(output_dir=tmp_path)

        # Mock _fetch_paper_info to avoid actual HTTP call
        with patch.object(collector, '_fetch_paper_info') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.AI"],
                "arxiv_id": "2301.12345",
                "published_date": "2023-01-15",
                "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
                "arxiv_url": "https://arxiv.org/abs/2301.12345",
            }

            result = collector.collect("arxiv:2301.12345", skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_skip_existing_no_match(self, tmp_path):
        """collect() with skip_existing=True proceeds when no duplicate."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        collector = PaperCollector(output_dir=tmp_path)

        with patch.object(collector, '_fetch_paper_info') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.AI"],
                "arxiv_id": "2301.12345",
                "published_date": "2023-01-15",
                "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
                "arxiv_url": "https://arxiv.org/abs/2301.12345",
            }

            result = collector.collect("arxiv:2301.12345", skip_existing=True, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_skip_existing_false_allows_duplicates(self, tmp_path):
        """collect() with skip_existing=False proceeds even with existing source."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="paper1", title="Existing Paper",
                              content_type="paper", source="arxiv:2301.12345",
                              collected_at="2026-01-01")

        collector = PaperCollector(output_dir=tmp_path)

        with patch.object(collector, '_fetch_paper_info') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.AI"],
                "arxiv_id": "2301.12345",
                "published_date": "2023-01-15",
                "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
                "arxiv_url": "https://arxiv.org/abs/2301.12345",
            }

            result = collector.collect("arxiv:2301.12345", skip_existing=False, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_content_hash_in_result(self, tmp_path):
        """collect() returns content_hash in CollectResult."""
        collector = PaperCollector(output_dir=tmp_path)

        with patch.object(collector, '_fetch_paper_info') as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.AI"],
                "arxiv_id": "2301.12345",
                "published_date": "2023-01-15",
                "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
                "arxiv_url": "https://arxiv.org/abs/2301.12345",
            }

            result = collector.collect("arxiv:2301.12345")

        assert result.success
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
