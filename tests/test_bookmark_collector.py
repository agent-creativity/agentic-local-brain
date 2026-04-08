"""
BookmarkCollector 单元测试

测试书签收集器的各项功能，包括：
- Chrome 书签解析
- HTML 书签解析
- Safari 书签解析
- 书签收集流程
- 增量更新
- 并发处理
- 错误处理
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kb.collectors import BookmarkCollector
from kb.collectors.base import CollectResult
from kb.collectors.bookmark_parser import (
    BookmarkItem,
    ChromeBookmarkParser,
    HTMLBookmarkParser,
    SafariBookmarkParser,
)


# ===== 测试数据 fixtures =====


@pytest.fixture
def collector(tmp_path):
    """创建测试用的 BookmarkCollector 实例"""
    return BookmarkCollector(output_dir=tmp_path)


@pytest.fixture
def sample_chrome_bookmarks():
    """示例 Chrome 书签 JSON 数据"""
    return {
        "checksum": "abc123",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "date_added": "13285267200000000",
                        "guid": "guid-1",
                        "id": "1",
                        "name": "Example Site",
                        "type": "url",
                        "url": "https://example.com"
                    },
                    {
                        "children": [
                            {
                                "date_added": "13285267300000000",
                                "guid": "guid-2",
                                "id": "2",
                                "name": "Python Official",
                                "type": "url",
                                "url": "https://python.org"
                            },
                            {
                                "date_added": "13285267400000000",
                                "guid": "guid-3",
                                "id": "3",
                                "name": "GitHub",
                                "type": "url",
                                "url": "https://github.com"
                            }
                        ],
                        "date_added": "13285267100000000",
                        "guid": "guid-folder-1",
                        "id": "4",
                        "name": "Development",
                        "type": "folder"
                    }
                ],
                "date_added": "13285267000000000",
                "guid": "guid-bar",
                "id": "5",
                "name": "书签栏",
                "type": "folder"
            },
            "other": {
                "children": [],
                "date_added": "13285267000000000",
                "guid": "guid-other",
                "id": "6",
                "name": "其他书签",
                "type": "folder"
            },
            "synced": {
                "children": [],
                "date_added": "13285267000000000",
                "guid": "guid-synced",
                "id": "7",
                "name": "移动设备书签",
                "type": "folder"
            }
        },
        "version": 1
    }


@pytest.fixture
def sample_html_bookmarks():
    """示例 HTML 书签内容"""
    return """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 FOLDED>技术</H3>
    <DL><p>
        <DT><A HREF="https://python.org" ADD_DATE="1234567890">Python Official</A>
        <DT><A HREF="https://github.com" ADD_DATE="1234567891">GitHub</A>
    </DL><p>
    <DT><H3>AI 工具</H3>
    <DL><p>
        <DT><A HREF="https://openai.com" ADD_DATE="1234567892">OpenAI</A>
    </DL><p>
    <DT><A HREF="https://example.com" ADD_DATE="1234567893">Example Site</A>
</DL><p>"""


@pytest.fixture
def sample_safari_bookmarks():
    """示例 Safari 书签 plist 数据"""
    return [
        {
            "WebBookmarkType": "WebBookmarkTypeList",
            "Title": "书签栏",
            "Children": [
                {
                    "WebBookmarkType": "WebBookmarkTypeLeaf",
                    "URIDictionary": {"title": "Example Site"},
                    "URLString": "https://example.com",
                    "DateLastVisited": "2024-01-01T00:00:00Z"
                },
                {
                    "WebBookmarkType": "WebBookmarkTypeList",
                    "Title": "Development",
                    "Children": [
                        {
                            "WebBookmarkType": "WebBookmarkTypeLeaf",
                            "URIDictionary": {"title": "Python Official"},
                            "URLString": "https://python.org"
                        },
                        {
                            "WebBookmarkType": "WebBookmarkTypeLeaf",
                            "URIDictionary": {"title": "GitHub"},
                            "URLString": "https://github.com"
                        }
                    ]
                }
            ]
        }
    ]


# ===== ChromeBookmarkParser 测试 =====


class TestChromeBookmarkParser:
    """测试 Chrome 书签解析器"""

    def test_parse_dict_success(self, sample_chrome_bookmarks):
        """测试成功解析 Chrome 书签字典"""
        parser = ChromeBookmarkParser()
        bookmarks = parser.parse_dict(sample_chrome_bookmarks)

        assert len(bookmarks) == 3
        assert bookmarks[0].title == "Example Site"
        assert bookmarks[0].url == "https://example.com"
        # Root level bookmarks have empty folder path
        assert bookmarks[0].folder_path == []
        # Bookmarks in Development folder
        assert bookmarks[1].folder_path == ["Development"]

    def test_parse_file_success(self, sample_chrome_bookmarks, tmp_path):
        """测试成功解析 Chrome 书签文件"""
        # 写入临时文件
        json_file = tmp_path / "Bookmarks"
        json_file.write_text(json.dumps(sample_chrome_bookmarks), encoding="utf-8")

        parser = ChromeBookmarkParser()
        bookmarks = parser.parse_file(json_file)

        assert len(bookmarks) == 3

    def test_parse_file_not_found(self):
        """测试文件不存在"""
        parser = ChromeBookmarkParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/Bookmarks")

    def test_parse_invalid_format(self, tmp_path):
        """测试无效的 JSON 格式"""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text('{"invalid": "data"}', encoding="utf-8")

        parser = ChromeBookmarkParser()
        with pytest.raises(ValueError, match="无效的 Chrome 书签文件格式"):
            parser.parse_file(invalid_file)

    def test_chrome_timestamp_conversion(self):
        """测试 Chrome 时间戳转换"""
        # Chrome 时间戳：从 1601-01-01 开始的微秒数
        timestamp = ChromeBookmarkParser._convert_chrome_timestamp("13285267200000000")
        assert timestamp is not None
        assert "2021" in timestamp or "2022" in timestamp  # 应该在 2021-2022 年左右

    def test_invalid_url_filtering(self):
        """测试无效 URL 过滤"""
        data = {
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {
                            "name": "Valid URL",
                            "type": "url",
                            "url": "https://example.com"
                        },
                        {
                            "name": "Invalid URL",
                            "type": "url",
                            "url": "not-a-valid-url"
                        },
                        {
                            "name": "FTP URL",
                            "type": "url",
                            "url": "ftp://example.com"
                        }
                    ]
                },
                "other": {"children": [], "name": "其他书签", "type": "folder"},
                "synced": {"children": [], "name": "移动设备书签", "type": "folder"}
            }
        }

        parser = ChromeBookmarkParser()
        bookmarks = parser.parse_dict(data)

        # 只应该有有效的 HTTPS URL
        assert len(bookmarks) == 1
        assert bookmarks[0].url == "https://example.com"


# ===== HTMLBookmarkParser 测试 =====


class TestHTMLBookmarkParser:
    """测试 HTML 书签解析器"""

    def test_parse_html_success(self, sample_html_bookmarks):
        """测试成功解析 HTML 书签"""
        parser = HTMLBookmarkParser()
        bookmarks = parser.parse_html(sample_html_bookmarks)

        assert len(bookmarks) == 4
        assert bookmarks[0].title == "Python Official"
        assert bookmarks[0].url == "https://python.org"
        assert bookmarks[0].folder_path == ["技术"]

    def test_parse_file_success(self, sample_html_bookmarks, tmp_path):
        """测试成功解析 HTML 文件"""
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        parser = HTMLBookmarkParser()
        bookmarks = parser.parse_file(html_file)

        assert len(bookmarks) == 4

    def test_parse_file_not_found(self):
        """测试文件不存在"""
        parser = HTMLBookmarkParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/bookmarks.html")

    def test_parse_invalid_html(self):
        """测试无效的 HTML 格式"""
        parser = HTMLBookmarkParser()
        with pytest.raises(ValueError, match="无效的书签 HTML 格式"):
            parser.parse_html("<html><body>No bookmarks</body></html>")

    def test_folder_structure_preserved(self, sample_html_bookmarks):
        """测试文件夹结构保留"""
        parser = HTMLBookmarkParser()
        bookmarks = parser.parse_html(sample_html_bookmarks)

        # 检查不同文件夹的书签
        tech_bookmarks = [b for b in bookmarks if "技术" in b.folder_path]
        ai_bookmarks = [b for b in bookmarks if "AI 工具" in b.folder_path]
        root_bookmarks = [b for b in bookmarks if not b.folder_path]

        assert len(tech_bookmarks) == 2
        assert len(ai_bookmarks) == 1
        assert len(root_bookmarks) == 1

    def test_html_timestamp_conversion(self):
        """测试 HTML 时间戳转换"""
        timestamp = HTMLBookmarkParser._convert_html_timestamp("1234567890")
        assert timestamp is not None
        assert "2009" in timestamp  # Unix 时间戳 1234567890 对应 2009 年


# ===== SafariBookmarkParser 测试 =====


class TestSafariBookmarkParser:
    """测试 Safari 书签解析器"""

    def test_parse_plist_success(self, sample_safari_bookmarks):
        """测试成功解析 Safari plist 数据"""
        parser = SafariBookmarkParser()
        parser._parse_plist(sample_safari_bookmarks)

        assert len(parser._bookmarks) == 3
        urls = [b.url for b in parser._bookmarks]
        assert "https://example.com" in urls
        assert "https://python.org" in urls
        assert "https://github.com" in urls

    def test_folder_structure_preserved(self, sample_safari_bookmarks):
        """测试文件夹结构保留"""
        parser = SafariBookmarkParser()
        parser._parse_plist(sample_safari_bookmarks)

        dev_bookmarks = [b for b in parser._bookmarks if "Development" in b.folder_path]
        assert len(dev_bookmarks) == 2

    def test_parse_file_not_found(self):
        """测试文件不存在"""
        parser = SafariBookmarkParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/Bookmarks.plist")


# ===== BookmarkCollector 测试 =====


class TestBookmarkCollectorInit:
    """测试 BookmarkCollector 初始化"""

    def test_default_output_dir(self):
        """测试默认输出目录"""
        collector = BookmarkCollector()
        expected_dir = Path.home() / ".knowledge-base" / "1_collect"
        assert collector.output_dir == expected_dir

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        collector = BookmarkCollector(output_dir=tmp_path)
        assert collector.output_dir == tmp_path

    def test_default_concurrency(self):
        """测试默认并发数"""
        collector = BookmarkCollector()
        assert collector._max_concurrent == 5

    def test_custom_concurrency(self):
        """测试自定义并发数"""
        collector = BookmarkCollector(max_concurrent=10)
        assert collector._max_concurrent == 10

    def test_default_retries(self):
        """测试默认重试次数"""
        collector = BookmarkCollector()
        assert collector._max_retries == 3

    def test_custom_retries(self):
        """测试自定义重试次数"""
        collector = BookmarkCollector(max_retries=5)
        assert collector._max_retries == 5


class TestBookmarkCollectorCollect:
    """测试 BookmarkCollector 收集功能"""

    def test_collect_single_bookmark(self, collector):
        """测试收集单个书签"""
        result = collector.collect(
            source="https://example.com",
            title="Example Site",
            folder_path=["测试文件夹"]
        )

        assert result.success is True
        assert result.title == "Example Site"
        assert result.word_count > 0
        assert result.file_path.exists()
        assert result.file_path.suffix == ".md"

    def test_collect_with_tags(self, collector):
        """测试带标签收集"""
        tags = ["技术", "示例"]
        result = collector.collect(
            source="https://example.com",
            title="Example Site",
            tags=tags
        )

        assert result.success is True
        assert result.tags == tags

    def test_collect_with_folder_path(self, collector):
        """测试带文件夹路径收集"""
        folder_path = ["技术", "Python"]
        result = collector.collect(
            source="https://python.org",
            title="Python Official",
            folder_path=folder_path
        )

        assert result.success is True
        # 验证保存的文件包含文件夹路径信息
        content = result.file_path.read_text(encoding="utf-8")
        assert "技术 / Python" in content

    def test_collect_metadata_structure(self, collector):
        """测试元数据结构"""
        result = collector.collect(
            source="https://example.com",
            title="Test",
            folder_path=["Folder"]
        )

        assert "id" in result.metadata
        assert "title" in result.metadata
        assert "source" in result.metadata
        assert "content_type" in result.metadata
        assert result.metadata["content_type"] == "bookmark"
        assert "folder_path" in result.metadata


class TestBookmarkCollectorFromFile:
    """测试从文件收集书签"""

    def test_collect_from_html_file(self, sample_html_bookmarks, tmp_path):
        """测试从 HTML 文件收集"""
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path)
        results = collector.collect_from_file(html_file, max_concurrent=2)

        assert len(results) == 4
        success_count = sum(1 for r in results if r.success)
        assert success_count == 4

    def test_collect_from_file_not_found(self, collector):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            collector.collect_from_file("/nonexistent/path/bookmarks.html")

    def test_collect_from_empty_file(self, tmp_path):
        """测试空 HTML 文件"""
        html_file = tmp_path / "empty.html"
        html_file.write_text("<html><body></body></html>", encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path)
        results = collector.collect_from_file(html_file)

        assert len(results) == 1
        assert results[0].success is False


class TestBookmarkCollectorFromChrome:
    """测试从 Chrome JSON 收集书签"""

    def test_collect_from_chrome_json(self, sample_chrome_bookmarks, tmp_path):
        """测试从 Chrome JSON 文件收集"""
        chrome_dir = tmp_path / "chrome_profile"
        chrome_dir.mkdir()
        json_file = chrome_dir / "Bookmarks"
        json_file.write_text(json.dumps(sample_chrome_bookmarks), encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path)
        results = collector.collect_from_chrome_json(json_file, max_concurrent=2)

        assert len(results) == 3
        success_count = sum(1 for r in results if r.success)
        assert success_count == 3

    def test_collect_from_chrome_json_not_found(self, collector):
        """测试 JSON 文件不存在"""
        with pytest.raises(FileNotFoundError):
            collector.collect_from_chrome_json("/nonexistent/path/Bookmarks")


class TestBookmarkCollectorIncremental:
    """测试增量更新功能"""

    def test_skip_existing_bookmarks(self, sample_html_bookmarks, tmp_path):
        """测试跳过已收集的书签"""
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path)

        # 第一次收集
        results1 = collector.collect_from_file(html_file, skip_existing=True)
        assert sum(1 for r in results1 if r.success) == 4

        # 第二次收集（应该跳过所有）
        results2 = collector.collect_from_file(html_file, skip_existing=True)
        assert len(results2) == 0  # 所有都已收集

    def test_no_skip_existing(self, sample_html_bookmarks, tmp_path):
        """测试不跳过已收集的书签"""
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path)

        # 第一次收集
        results1 = collector.collect_from_file(html_file, skip_existing=False)
        assert sum(1 for r in results1 if r.success) == 4

        # 第二次收集（不跳过）
        results2 = collector.collect_from_file(html_file, skip_existing=False)
        assert sum(1 for r in results2 if r.success) == 4


class TestBookmarkCollectorBrowser:
    """测试浏览器书签收集"""

    def test_unsupported_browser(self, collector):
        """测试不支持的浏览器类型"""
        with pytest.raises(ValueError, match="不支持的浏览器类型"):
            collector.collect_from_browser("opera")

    def test_supported_browsers(self, collector):
        """测试支持的浏览器列表"""
        browsers = collector.get_supported_browsers()
        assert "chrome" in browsers
        assert "edge" in browsers
        assert "firefox" in browsers
        assert "safari" in browsers


class TestBookmarkCollectorConcurrency:
    """测试并发处理"""

    def test_concurrent_collection(self, sample_html_bookmarks, tmp_path):
        """测试并发收集"""
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        collector = BookmarkCollector(output_dir=tmp_path, max_concurrent=3)
        results = collector.collect_from_file(html_file, max_concurrent=3)

        # 验证所有书签都被收集
        assert len(results) == 4
        assert all(r.success for r in results)


class TestBookmarkCollectorRetry:
    """测试重试机制"""

    def test_retry_on_failure(self, collector):
        """测试失败重试"""
        # Mock collect 方法，前两次失败，第三次成功
        call_count = [0]

        def mock_collect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return CollectResult(success=False, error="Temporary error")
            return CollectResult(success=True, title="Test")

        with patch.object(collector, 'collect', side_effect=mock_collect):
            bookmark = BookmarkItem(
                title="Test Bookmark",
                url="https://example.com",
                folder_path=[]
            )

            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    collector._collect_single_with_retry(bookmark)
                )
            finally:
                loop.close()

            # 应该重试了 3 次
            assert call_count[0] == 3
            assert result.success is True


class TestBookmarkContentGeneration:
    """测试书签内容生成"""

    def test_generate_bookmark_content(self, collector):
        """测试生成书签内容"""
        content = collector._generate_bookmark_content(
            title="Test Site",
            url="https://example.com",
            folder_path=["技术", "Python"]
        )

        assert "# Test Site" in content
        assert "https://example.com" in content
        assert "技术 / Python" in content
        assert "BookmarkCollector" in content


class TestURLExtraction:
    """测试 URL 标题提取"""

    def test_extract_title_from_simple_url(self, collector):
        """测试从简单 URL 提取标题"""
        title = collector._extract_title_from_url("https://example.com/my-article")
        assert "My Article" in title

    def test_extract_title_from_root_url(self, collector):
        """测试从根 URL 提取标题"""
        title = collector._extract_title_from_url("https://example.com")
        assert "example.com" in title

    def test_extract_title_with_extension(self, collector):
        """测试带扩展名的 URL"""
        title = collector._extract_title_from_url("https://example.com/page.html")
        assert "Page" in title


class TestSavedFileContent:
    """测试保存的文件内容"""

    def test_file_contains_yaml_frontmatter(self, collector):
        """测试文件包含 YAML Front Matter"""
        result = collector.collect(
            source="https://example.com",
            title="Test"
        )

        content = result.file_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "content_type: bookmark" in content
        # source 可能被引号包围
        assert "source:" in content and "https://example.com" in content

    def test_file_contains_bookmark_content(self, collector):
        """测试文件包含书签内容"""
        result = collector.collect(
            source="https://example.com",
            title="Example Site",
            folder_path=["技术"]
        )

        content = result.file_path.read_text(encoding="utf-8")
        assert "# Example Site" in content
        assert "**原始链接:** https://example.com" in content
        assert "**分类路径:** 技术" in content


# ===== collect_single_url 测试 =====


class TestCollectSingleUrl:
    """Tests for collect_single_url method."""

    def test_collect_single_url_basic(self, collector):
        """Test basic single URL collection without auto-tag."""
        result = collector.collect_single_url(
            url="https://example.com/article",
        )

        assert result.success is True
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.title is not None

    def test_collect_single_url_with_tags(self, collector):
        """Test single URL with explicit tags (no LLM call)."""
        tags = ["python", "programming"]
        result = collector.collect_single_url(
            url="https://example.com/python-guide",
            tags=tags,
        )

        assert result.success is True
        assert result.tags == tags
        # Verify tags are in the saved file
        content = result.file_path.read_text(encoding="utf-8")
        assert "python" in content
        assert "programming" in content

    def test_collect_single_url_with_title(self, collector):
        """Test single URL with custom title."""
        custom_title = "My Custom Title"
        result = collector.collect_single_url(
            url="https://example.com/some-page",
            title=custom_title,
        )

        assert result.success is True
        assert result.title == custom_title
        content = result.file_path.read_text(encoding="utf-8")
        assert f"# {custom_title}" in content

    def test_collect_single_url_auto_tag_success(self, collector):
        """Test auto-tagging with mocked HTTP and TagExtractor."""
        sample_html = """
        <html>
        <head><title>Machine Learning Tutorial</title></head>
        <body>
        <article>
        <h1>Introduction to Machine Learning</h1>
        <p>Machine learning is a branch of artificial intelligence that focuses on
        building systems that can learn from data. Deep learning is a subset of
        machine learning that uses neural networks with many layers.</p>
        </article>
        </body>
        </html>
        """

        mock_tags = ["machine-learning", "artificial-intelligence", "deep-learning"]

        # Mock httpx.get
        with patch("httpx.get") as mock_httpx_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_httpx_get.return_value = mock_response

            # Mock TagExtractor
            with patch("kb.processors.tag_extractor.TagExtractor.from_config") as mock_from_config:
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.success = True
                mock_result.data = {'tags': mock_tags, 'summary': ''}
                mock_extractor.process.return_value = mock_result
                mock_from_config.return_value = mock_extractor

                # Mock Config
                mock_config = Mock()

                result = collector.collect_single_url(
                    url="https://example.com/ml-tutorial",
                    auto_tag=True,
                    config=mock_config,
                )

                assert result.success is True
                assert result.tags == mock_tags
                # Verify TagExtractor was called
                mock_from_config.assert_called_once_with(mock_config)
                mock_extractor.process.assert_called_once()

    def test_collect_single_url_auto_tag_fetch_failure(self, collector):
        """Test auto-tag graceful degradation when HTTP fetch fails."""
        # Mock httpx.get to raise an exception
        with patch("httpx.get") as mock_httpx_get:
            mock_httpx_get.side_effect = Exception("Network error")

            mock_config = Mock()

            result = collector.collect_single_url(
                url="https://example.com/unreachable",
                auto_tag=True,
                config=mock_config,
            )

            # Should still save bookmark, just without tags
            assert result.success is True
            assert result.file_path.exists()
            # Tags should be None or empty
            assert result.tags is None or result.tags == []

    def test_collect_single_url_auto_tag_llm_failure(self, collector):
        """Test auto-tag graceful degradation when LLM fails."""
        sample_html = """
        <html>
        <head><title>Test Page</title></head>
        <body><p>Some content here</p></body>
        </html>
        """

        # Mock successful HTTP but TagExtractor returns failure
        with patch("httpx.get") as mock_httpx_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_httpx_get.return_value = mock_response

            with patch("kb.processors.tag_extractor.TagExtractor.from_config") as mock_from_config:
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.success = False
                mock_result.error = "LLM API error"
                mock_extractor.process.return_value = mock_result
                mock_from_config.return_value = mock_extractor

                mock_config = Mock()

                result = collector.collect_single_url(
                    url="https://example.com/llm-fail",
                    auto_tag=True,
                    config=mock_config,
                )

                # Should still save bookmark without tags
                assert result.success is True
                assert result.file_path.exists()

    def test_collect_single_url_auto_tag_no_config(self, collector, caplog):
        """Test auto-tag without config logs appropriate warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = collector.collect_single_url(
                url="https://example.com/no-config",
                auto_tag=True,
                config=None,  # No config provided
            )

            # Should still save bookmark
            assert result.success is True
            # Should log a warning about missing config
            assert "auto_tag=True but no config provided" in caplog.text

    def test_collect_single_url_invalid_url(self, collector):
        """Test with invalid URL."""
        result = collector.collect_single_url(
            url="not-a-valid-url",
        )

        assert result.success is False
        assert "Invalid URL format" in result.error

    def test_collect_single_url_invalid_ftp_url(self, collector):
        """Test with non-HTTP URL (FTP)."""
        result = collector.collect_single_url(
            url="ftp://example.com/file",
        )

        assert result.success is False
        assert "Invalid URL format" in result.error

    def test_collect_single_url_extracts_title_from_page(self, collector):
        """Test that title is extracted from page when not provided."""
        sample_html = """
        <html>
        <head><title>Page Title From HTML</title></head>
        <body><p>Content</p></body>
        </html>
        """

        with patch("httpx.get") as mock_httpx_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_httpx_get.return_value = mock_response

            mock_config = Mock()

            # Mock TagExtractor to avoid LLM call
            with patch("kb.processors.tag_extractor.TagExtractor.from_config") as mock_from_config:
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.success = False
                mock_extractor.process.return_value = mock_result
                mock_from_config.return_value = mock_extractor

                result = collector.collect_single_url(
                    url="https://example.com/page",
                    auto_tag=True,
                    config=mock_config,
                )

                assert result.success is True
                assert result.title == "Page Title From HTML"


class TestFetchPageInfo:
    """Tests for _fetch_page_info helper method."""

    def test_fetch_page_info_success(self, collector):
        """Test _fetch_page_info with mocked response."""
        sample_html = """
        <html>
        <head><title>Test Title</title></head>
        <body>
        <article>
        <h1>Main Content</h1>
        <p>This is the main content of the page.</p>
        </article>
        </body>
        </html>
        """

        with patch("httpx.get") as mock_httpx_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_httpx_get.return_value = mock_response

            result = collector._fetch_page_info("https://example.com/test")

            assert result["title"] == "Test Title"
            assert "content" in result
            # Content should have some text extracted
            assert len(result["content"]) > 0

    def test_fetch_page_info_failure(self, collector):
        """Test _fetch_page_info graceful failure."""
        with patch("httpx.get") as mock_httpx_get:
            mock_httpx_get.side_effect = Exception("Connection refused")

            result = collector._fetch_page_info("https://example.com/unreachable")

            # Should return empty dict on failure
            assert result["title"] == ""
            assert result["content"] == ""

    def test_fetch_page_info_no_title(self, collector):
        """Test _fetch_page_info when page has no title tag."""
        sample_html = """
        <html>
        <head></head>
        <body><p>Content without title</p></body>
        </html>
        """

        with patch("httpx.get") as mock_httpx_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_httpx_get.return_value = mock_response

            result = collector._fetch_page_info("https://example.com/no-title")

            # Title should be empty or extracted from readability
            assert "title" in result


class TestIsValidUrl:
    """Tests for _is_valid_url helper method."""

    def test_valid_http_url(self, collector):
        """Test valid HTTP URL."""
        assert collector._is_valid_url("http://example.com") is True

    def test_valid_https_url(self, collector):
        """Test valid HTTPS URL."""
        assert collector._is_valid_url("https://example.com/path") is True

    def test_invalid_ftp_url(self, collector):
        """Test invalid FTP URL."""
        assert collector._is_valid_url("ftp://example.com") is False

    def test_invalid_no_protocol(self, collector):
        """Test invalid URL without protocol."""
        assert collector._is_valid_url("example.com") is False

    def test_invalid_empty_string(self, collector):
        """Test invalid empty string."""
        assert collector._is_valid_url("") is False


class TestBookmarkCollectorDedup:
    """Tests for BookmarkCollector dedup functionality."""

    def test_skip_existing_source_match(self, tmp_path):
        """collect() with skip_existing=True returns failure when source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="bm1", title="Existing Bookmark",
                              content_type="bookmark", source="https://example.com/test",
                              collected_at="2026-01-01")

        collector = BookmarkCollector(output_dir=tmp_path)
        result = collector.collect("https://example.com/test", skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_skip_existing_no_match(self, tmp_path):
        """collect() with skip_existing=True proceeds when no duplicate."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        collector = BookmarkCollector(output_dir=tmp_path)
        result = collector.collect("https://example.com/new", title="New Bookmark",
                                   skip_existing=True, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_skip_existing_false_allows_duplicates(self, tmp_path):
        """collect() with skip_existing=False proceeds even with existing source."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="bm1", title="Existing Bookmark",
                              content_type="bookmark", source="https://example.com/test",
                              collected_at="2026-01-01")

        collector = BookmarkCollector(output_dir=tmp_path)
        result = collector.collect("https://example.com/test", title="Test Bookmark",
                                   skip_existing=False, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_content_hash_in_result(self, tmp_path):
        """collect() returns content_hash in CollectResult."""
        collector = BookmarkCollector(output_dir=tmp_path)
        result = collector.collect("https://example.com/test", title="Test Bookmark")

        assert result.success
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex length

    def test_collect_single_url_skip_existing(self, tmp_path):
        """collect_single_url() with skip_existing=True returns failure when source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="bm1", title="Existing Bookmark",
                              content_type="bookmark", source="https://example.com/test",
                              collected_at="2026-01-01")

        collector = BookmarkCollector(output_dir=tmp_path)
        result = collector.collect_single_url("https://example.com/test", skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_batch_collect_with_storage_dedup(self, tmp_path, sample_html_bookmarks):
        """Batch collection uses storage for dedup when available."""
        from kb.storage.sqlite_storage import SQLiteStorage

        # Create HTML file with bookmarks
        html_file = tmp_path / "bookmarks.html"
        html_file.write_text(sample_html_bookmarks, encoding="utf-8")

        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Pre-add one bookmark to storage
        storage.add_knowledge(id="bm1", title="Python Official",
                              content_type="bookmark", source="https://python.org",
                              collected_at="2026-01-01")

        collector = BookmarkCollector(output_dir=tmp_path)
        results = collector.collect_from_file(html_file, skip_existing=True, storage=storage)

        # Should have 3 results (4 total - 1 duplicate)
        assert len(results) == 3
        storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
