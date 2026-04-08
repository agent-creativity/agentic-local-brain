"""
WebpageCollector 单元测试

测试网页收集器的各项功能，包括：
- 网页抓取
- 内容提取（Readability）
- HTML 到 Markdown 转换
- 元数据生成
- 错误处理
- URL 验证
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kb.collectors import WebpageCollector
from kb.collectors.base import CollectResult


@pytest.fixture
def collector(tmp_path):
    """创建测试用的 WebpageCollector 实例"""
    return WebpageCollector(output_dir=tmp_path)


@pytest.fixture
def sample_html():
    """示例 HTML 内容"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试网页标题</title>
        <meta charset="utf-8">
    </head>
    <body>
        <header>导航栏</header>
        <article>
            <h1>文章标题</h1>
            <p>这是第一段内容，包含重要信息。</p>
            <p>这是第二段内容，继续说明主题。</p>
            <ul>
                <li>要点一</li>
                <li>要点二</li>
                <li>要点三</li>
            </ul>
            <h2>子标题</h2>
            <p>更多内容在这里...</p>
        </article>
        <footer>页脚信息</footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_complex():
    """复杂的示例 HTML 内容"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>复杂网页 - 测试</title>
        <meta property="og:title" content="Open Graph 标题">
    </head>
    <body>
        <nav>导航菜单</nav>
        <div class="content">
            <h1>主要内容标题</h1>
            <p>这是一个包含<a href="https://example.com">链接</a>的段落。</p>
            <blockquote>引用内容</blockquote>
            <code>代码示例: print("hello")</code>
            <table>
                <tr><td>单元格1</td><td>单元格2</td></tr>
            </table>
        </div>
        <aside>侧边栏</aside>
    </body>
    </html>
    """


class TestWebpageCollectorInit:
    """测试 WebpageCollector 初始化"""

    def test_default_output_dir(self):
        """测试默认输出目录"""
        collector = WebpageCollector()
        expected_dir = Path.home() / ".knowledge-base" / "1_collect"
        assert collector.output_dir == expected_dir

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        collector = WebpageCollector(output_dir=tmp_path)
        assert collector.output_dir == tmp_path

    def test_default_timeout(self):
        """测试默认超时设置"""
        collector = WebpageCollector()
        assert collector._timeout == 30

    def test_custom_timeout(self):
        """测试自定义超时设置"""
        collector = WebpageCollector(timeout=60)
        assert collector._timeout == 60

    def test_default_user_agent(self):
        """测试默认 User-Agent"""
        collector = WebpageCollector()
        assert "Mozilla/5.0" in collector._user_agent

    def test_custom_user_agent(self):
        """测试自定义 User-Agent"""
        custom_ua = "MyCustomBot/1.0"
        collector = WebpageCollector(user_agent=custom_ua)
        assert collector._user_agent == custom_ua


class TestURLValidation:
    """测试 URL 验证"""

    def test_valid_http_url(self, collector):
        """测试有效的 HTTP URL"""
        assert collector._is_valid_url("http://example.com") is True

    def test_valid_https_url(self, collector):
        """测试有效的 HTTPS URL"""
        assert collector._is_valid_url("https://example.com/article") is True

    def test_valid_url_with_path(self, collector):
        """测试带路径的 URL"""
        assert collector._is_valid_url("https://example.com/path/to/page") is True

    def test_valid_url_with_query(self, collector):
        """测试带查询参数的 URL"""
        assert collector._is_valid_url("https://example.com/search?q=test") is True

    def test_invalid_url_no_scheme(self, collector):
        """测试无效 URL（无协议）"""
        assert collector._is_valid_url("example.com") is False

    def test_invalid_url_ftp(self, collector):
        """测试无效 URL（FTP 协议）"""
        assert collector._is_valid_url("ftp://example.com") is False

    def test_invalid_url_empty(self, collector):
        """测试空 URL"""
        assert collector._is_valid_url("") is False


class TestFetchHTML:
    """测试 HTML 抓取"""

    @patch("kb.collectors.webpage_collector.httpx.Client")
    def test_fetch_html_success(self, mock_client_class, collector):
        """测试成功抓取 HTML"""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.charset_encoding = "utf-8"
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        html = collector._fetch_html("https://example.com")

        assert html == "<html><body>Test</body></html>"
        mock_client.get.assert_called_once()

    @patch("kb.collectors.webpage_collector.httpx.Client")
    def test_fetch_html_timeout(self, mock_client_class, collector):
        """测试请求超时"""
        import httpx

        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(httpx.TimeoutException):
            collector._fetch_html("https://example.com")

    @patch("kb.collectors.webpage_collector.httpx.Client")
    def test_fetch_html_http_error(self, mock_client_class, collector):
        """测试 HTTP 错误"""
        import httpx

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        )

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(httpx.HTTPStatusError):
            collector._fetch_html("https://example.com/not-found")


class TestExtractContent:
    """测试内容提取"""

    def test_extract_content_success(self, collector, sample_html):
        """测试成功提取内容"""
        content_html, title = collector._extract_content(sample_html)

        assert title == "测试网页标题"
        assert len(content_html) > 0
        # 应该包含文章主要内容
        assert "文章标题" in content_html or "第一段内容" in content_html

    def test_extract_content_empty(self, collector):
        """测试空 HTML 内容"""
        # Readability 可能会返回一些默认内容，所以这里只验证返回了内容
        content_html, title = collector._extract_content("<html><body></body></html>")
        # 验证函数正常执行并返回结果
        assert isinstance(content_html, str)
        assert isinstance(title, str)


class TestHTMLToMarkdown:
    """测试 HTML 到 Markdown 转换"""

    def test_html_to_markdown_basic(self, collector):
        """测试基本 HTML 转 Markdown"""
        html = "<h1>标题</h1><p>段落内容</p>"
        markdown = collector._html_to_markdown(html)

        assert "# 标题" in markdown
        assert "段落内容" in markdown

    def test_html_to_markdown_list(self, collector):
        """测试列表转换"""
        html = "<ul><li>项目1</li><li>项目2</li></ul>"
        markdown = collector._html_to_markdown(html)

        assert "- 项目1" in markdown
        assert "- 项目2" in markdown

    def test_html_to_markdown_cleanup(self, collector):
        """测试多余空白清理"""
        html = "<p>段落1</p><p>段落2</p>"
        markdown = collector._html_to_markdown(html)

        # 不应该有多个连续空行
        assert "\n\n\n" not in markdown


class TestExtractTitle:
    """测试标题提取"""

    def test_extract_title_from_tag(self, collector, sample_html):
        """测试从 <title> 标签提取"""
        title = collector._extract_title(sample_html)
        assert title == "测试网页标题"

    def test_extract_title_from_og(self, collector, sample_html_complex):
        """测试从 Open Graph 提取"""
        title = collector._extract_title(sample_html_complex)
        # 应该优先使用 <title> 标签
        assert "复杂网页" in title or "Open Graph 标题" in title

    def test_extract_title_from_h1(self, collector):
        """测试从 h1 标签提取"""
        html = "<html><body><h1>H1 标题</h1></body></html>"
        title = collector._extract_title(html)
        assert title == "H1 标题"

    def test_extract_title_empty(self, collector):
        """测试空 HTML"""
        title = collector._extract_title("<html><body></body></html>")
        assert title == ""


class TestExtractTitleFromURL:
    """测试从 URL 推断标题"""

    def test_extract_from_simple_url(self, collector):
        """测试简单 URL"""
        title = collector._extract_title_from_url("https://example.com/my-article")
        assert "My Article" in title

    def test_extract_from_url_with_extension(self, collector):
        """测试带扩展名的 URL"""
        title = collector._extract_title_from_url("https://example.com/page.html")
        assert "Page" in title

    def test_extract_from_url_with_query(self, collector):
        """测试带查询参数的 URL"""
        title = collector._extract_title_from_url("https://example.com/article?id=123")
        assert "Article" in title

    def test_extract_from_root_url(self, collector):
        """测试根 URL"""
        title = collector._extract_title_from_url("https://example.com/")
        # 从 URL 路径提取的标题应该是 "Example"
        assert "Example" in title or "Untitled" in title


class TestCollect:
    """测试完整的收集流程"""

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_collect_success(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试成功收集"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n内容"

        result = collector.collect("https://example.com/article")

        assert result.success is True
        assert result.title == "测试标题"
        assert result.word_count > 0
        assert result.file_path.exists()
        assert result.file_path.suffix == ".md"

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_collect_with_tags(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试带标签收集"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n内容"

        tags = ["AI", "教程", "技术"]
        result = collector.collect("https://example.com", tags=tags)

        assert result.success is True
        assert result.tags == tags
        # 验证保存的文件包含标签
        content = result.file_path.read_text(encoding="utf-8")
        assert "AI" in content

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_collect_with_custom_title(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试自定义标题"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "原始标题")
        mock_md.return_value = "# 原始标题\n\n内容"

        custom_title = "我的自定义标题"
        result = collector.collect("https://example.com", title=custom_title)

        assert result.success is True
        assert result.title == custom_title

    def test_collect_invalid_url(self, collector):
        """测试无效 URL"""
        result = collector.collect("not-a-valid-url")

        assert result.success is False
        assert "无效的 URL 格式" in result.error

    @patch.object(WebpageCollector, "_fetch_html")
    def test_collect_timeout(self, mock_fetch, collector):
        """测试超时错误"""
        import httpx

        mock_fetch.side_effect = httpx.TimeoutException("Timeout")

        result = collector.collect("https://example.com")

        assert result.success is False
        assert "请求超时" in result.error

    @patch.object(WebpageCollector, "_fetch_html")
    def test_collect_http_error(self, mock_fetch, collector):
        """测试 HTTP 错误"""
        import httpx

        mock_fetch.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        )

        result = collector.collect("https://example.com")

        assert result.success is False
        assert "HTTP 错误" in result.error

    @patch.object(WebpageCollector, "_fetch_html")
    def test_collect_request_error(self, mock_fetch, collector):
        """测试网络请求错误"""
        import httpx

        mock_fetch.side_effect = httpx.RequestError("Connection failed")

        result = collector.collect("https://example.com")

        assert result.success is False
        assert "网络请求失败" in result.error


class TestMetadataGeneration:
    """测试元数据生成"""

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_metadata_structure(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试元数据结构"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n内容"

        result = collector.collect("https://example.com")

        assert "id" in result.metadata
        assert "title" in result.metadata
        assert "source" in result.metadata
        assert "content_type" in result.metadata
        assert "collected_at" in result.metadata
        assert "tags" in result.metadata
        assert "word_count" in result.metadata
        assert "status" in result.metadata
        assert result.metadata["content_type"] == "webpage"
        assert result.metadata["status"] == "processed"

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_metadata_with_extra_kwargs(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试额外的元数据字段"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n内容"

        result = collector.collect(
            "https://example.com",
            custom_field="custom_value",
            another_field=123
        )

        assert result.metadata["custom_field"] == "custom_value"
        assert result.metadata["another_field"] == 123


class TestEncodingDetection:
    """测试编码检测"""

    def test_detect_charset_meta(self, collector):
        """测试从 meta charset 检测"""
        html = '<meta charset="utf-8">'
        encoding = collector._detect_encoding(html)
        assert encoding == "utf-8"

    def test_detect_content_type_meta(self, collector):
        """测试从 Content-Type meta 检测"""
        html = '<meta http-equiv="Content-Type" content="text/html; charset=gbk">'
        encoding = collector._detect_encoding(html)
        assert encoding == "gbk"

    def test_detect_default_encoding(self, collector):
        """测试默认编码"""
        html = "<html><body>test</body></html>"
        encoding = collector._detect_encoding(html)
        assert encoding == "utf-8"


class TestTitleExtractionRegex:
    """测试正则表达式标题提取"""

    def test_extract_title_regex_success(self, collector):
        """测试成功提取"""
        html = "<html><head><title>测试标题</title></head></html>"
        title = collector._extract_title_regex(html)
        assert title == "测试标题"

    def test_extract_title_regex_with_entities(self, collector):
        """测试包含 HTML 实体的标题"""
        html = "<title>Test &amp; Title</title>"
        title = collector._extract_title_regex(html)
        assert "Test" in title

    def test_extract_title_regex_empty(self, collector):
        """测试无标题标签"""
        html = "<html><head></head></html>"
        title = collector._extract_title_regex(html)
        assert title == ""


class TestHTMLToText:
    """测试 HTML 到纯文本转换（降级方案）"""

    def test_html_to_text_basic(self, collector):
        """测试基本转换"""
        html = "<p>段落1</p><p>段落2</p>"
        text = collector._html_to_text(html)
        assert "段落1" in text
        assert "段落2" in text

    def test_html_to_text_remove_scripts(self, collector):
        """测试移除脚本标签"""
        html = "<p>内容</p><script>alert('test')</script>"
        text = collector._html_to_text(html)
        assert "alert" not in text
        assert "内容" in text


class TestSafeFilename:
    """测试安全文件名生成"""

    def test_filename_with_chinese_title(self, collector):
        """测试中文标题的文件名"""
        filename = collector._generate_safe_filename("webpage", "测试网页标题")
        assert filename.endswith(".md")
        assert "_" in filename

    def test_filename_with_special_chars(self, collector):
        """测试特殊字符的文件名"""
        filename = collector._generate_safe_filename("webpage", "Test/URL: With*Special?Chars")
        assert filename.endswith(".md")
        assert "/" not in filename
        assert ":" not in filename

    def test_filename_without_title(self, collector):
        """测试无标题的文件名"""
        filename = collector._generate_safe_filename("webpage")
        assert filename.endswith(".md")
        assert "webpage" in filename


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


class TestSavedFileContent:
    """测试保存的文件内容"""

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_file_contains_yaml_frontmatter(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试文件包含 YAML Front Matter"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n内容"

        result = collector.collect("https://example.com")

        content = result.file_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "id:" in content
        assert "title:" in content
        assert "source:" in content
        assert "content_type: webpage" in content

    @patch.object(WebpageCollector, "_fetch_html")
    @patch.object(WebpageCollector, "_extract_content")
    @patch.object(WebpageCollector, "_html_to_markdown")
    def test_file_contains_markdown_content(
        self,
        mock_md,
        mock_extract,
        mock_fetch,
        collector,
    ):
        """测试文件包含 Markdown 内容"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = ("<p>content</p>", "测试标题")
        mock_md.return_value = "# 测试标题\n\n这是正文内容。"

        result = collector.collect("https://example.com")

        content = result.file_path.read_text(encoding="utf-8")
        assert "# 测试标题" in content
        assert "这是正文内容。" in content


class TestWebpageCollectorDedup:
    """Tests for WebpageCollector dedup functionality."""

    def test_skip_existing_source_match(self, tmp_path):
        """collect() with skip_existing=True returns failure when source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="web1", title="Existing Page",
                              content_type="webpage", source="https://example.com/test",
                              collected_at="2026-01-01")

        collector = WebpageCollector(output_dir=tmp_path)

        # Mock the _fetch_html to avoid actual HTTP call
        with patch.object(collector, '_fetch_html') as mock_fetch:
            mock_fetch.return_value = "<html><body>Test</body></html>"

            result = collector.collect("https://example.com/test", skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_skip_existing_no_match(self, tmp_path):
        """collect() with skip_existing=True proceeds when no duplicate."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        collector = WebpageCollector(output_dir=tmp_path)

        # Mock all the heavy operations
        with patch.object(collector, '_fetch_html') as mock_fetch, \
             patch.object(collector, '_extract_content') as mock_extract, \
             patch.object(collector, '_html_to_markdown') as mock_md:
            mock_fetch.return_value = "<html><body>Test</body></html>"
            mock_extract.return_value = ("<p>content</p>", "Test Title")
            mock_md.return_value = "# Test Title\n\nContent"

            result = collector.collect("https://example.com/new", skip_existing=True, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_skip_existing_false_allows_duplicates(self, tmp_path):
        """collect() with skip_existing=False proceeds even with existing source."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))
        storage.add_knowledge(id="web1", title="Existing Page",
                              content_type="webpage", source="https://example.com/test",
                              collected_at="2026-01-01")

        collector = WebpageCollector(output_dir=tmp_path)

        # Mock all the heavy operations
        with patch.object(collector, '_fetch_html') as mock_fetch, \
             patch.object(collector, '_extract_content') as mock_extract, \
             patch.object(collector, '_html_to_markdown') as mock_md:
            mock_fetch.return_value = "<html><body>Test</body></html>"
            mock_extract.return_value = ("<p>content</p>", "Test Title")
            mock_md.return_value = "# Test Title\n\nContent"

            result = collector.collect("https://example.com/test", skip_existing=False, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_content_hash_in_result(self, tmp_path):
        """collect() returns content_hash in CollectResult."""
        collector = WebpageCollector(output_dir=tmp_path)

        with patch.object(collector, '_fetch_html') as mock_fetch, \
             patch.object(collector, '_extract_content') as mock_extract, \
             patch.object(collector, '_html_to_markdown') as mock_md:
            mock_fetch.return_value = "<html><body>Test</body></html>"
            mock_extract.return_value = ("<p>content</p>", "Test Title")
            mock_md.return_value = "# Test Title\n\nContent"

            result = collector.collect("https://example.com/test")

        assert result.success
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
