"""
EmailCollector 单元测试

测试邮件收集器的各项功能，包括：
- EML 文件解析
- MBOX 文件解析
- 邮件正文提取（纯文本和 HTML）
- 邮件头解码
- 元数据生成
- 错误处理
"""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kb.collectors import EmailCollector
from kb.collectors.base import CollectResult


@pytest.fixture
def collector(tmp_path):
    """创建测试用的 EmailCollector 实例"""
    return EmailCollector(output_dir=tmp_path)


@pytest.fixture
def sample_eml_content():
    """示例 EML 文件内容"""
    return b"""From: sender@example.com
To: recipient@example.com, cc@example.com
Subject: Test Email Subject
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

This is the email body content.
It has multiple lines.

Best regards,
Sender
"""


@pytest.fixture
def sample_eml_html_content():
    """示例 HTML 邮件内容"""
    return b"""From: sender@example.com
To: recipient@example.com
Subject: HTML Email Test
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <html123@example.com>
Content-Type: text/html; charset="utf-8"

<html>
<body>
<h1>Hello</h1>
<p>This is an HTML email.</p>
<p>With <b>bold</b> and <i>italic</i> text.</p>
</body>
</html>
"""


@pytest.fixture
def sample_eml_multipart():
    """示例多部分邮件内容"""
    return b"""From: sender@example.com
To: recipient@example.com
Subject: Multipart Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <multi123@example.com>
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset="utf-8"

This is the plain text version.

--boundary123
Content-Type: text/html; charset="utf-8"

<html><body><p>This is the HTML version.</p></body></html>

--boundary123--
"""


@pytest.fixture
def sample_eml_encoded_subject():
    """示例编码主题邮件"""
    return b"""From: sender@example.com
To: recipient@example.com
Subject: =?UTF-8?B?5rWL6K+V6YKu5Lu25Li76aKY?=
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <encoded123@example.com>
Content-Type: text/plain; charset="utf-8"

Email body
"""


@pytest.fixture
def sample_eml_file(tmp_path, sample_eml_content):
    """创建示例 EML 文件"""
    eml_file = tmp_path / "test.eml"
    eml_file.write_bytes(sample_eml_content)
    return eml_file


@pytest.fixture
def sample_mbox_file(tmp_path):
    """创建示例 MBOX 文件"""
    mbox_content = b"""From sender@example.com Mon Jan 15 10:30:00 2024
From: sender1@example.com
To: recipient@example.com
Subject: First Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <msg1@example.com>

First email body.

From sender2@example.com Mon Jan 15 11:30:00 2024
From: sender2@example.com
To: recipient@example.com
Subject: Second Email
Date: Mon, 15 Jan 2024 11:30:00 +0000
Message-ID: <msg2@example.com>

Second email body.

"""
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_bytes(mbox_content)
    return mbox_file


class TestEmailCollectorInit:
    """测试 EmailCollector 初始化"""

    def test_default_output_dir(self):
        """测试默认输出目录"""
        collector = EmailCollector()
        expected_dir = Path.home() / ".knowledge-base" / "1_collect"
        assert collector.output_dir == expected_dir

    def test_custom_output_dir(self, tmp_path):
        """测试自定义输出目录"""
        collector = EmailCollector(output_dir=tmp_path)
        assert collector.output_dir == tmp_path


class TestEMLParsing:
    """测试 EML 文件解析"""

    def test_collect_eml_file(self, collector, sample_eml_file):
        """测试收集 EML 文件"""
        result = collector.collect(sample_eml_file)

        assert result.success is True
        assert result.title == "Test Email Subject"
        assert result.word_count > 0
        assert result.file_path.exists()
        assert result.file_path.suffix == ".md"

    def test_collect_eml_metadata(self, collector, sample_eml_file):
        """测试 EML 元数据提取"""
        result = collector.collect(sample_eml_file)

        assert result.metadata["sender"] == "sender@example.com"
        assert "recipient@example.com" in result.metadata["recipients"]
        assert result.metadata["message_id"] == "<test123@example.com>"
        assert result.metadata["content_type"] == "email"

    def test_collect_eml_with_tags(self, collector, sample_eml_file):
        """测试带标签收集 EML"""
        tags = ["work", "important"]
        result = collector.collect(sample_eml_file, tags=tags)

        assert result.success is True
        assert result.tags == tags


class TestHTMLEmailParsing:
    """测试 HTML 邮件解析"""

    def test_collect_html_email(self, collector, tmp_path, sample_eml_html_content):
        """测试收集 HTML 邮件"""
        eml_file = tmp_path / "html.eml"
        eml_file.write_bytes(sample_eml_html_content)

        result = collector.collect(eml_file)

        assert result.success is True
        # HTML 标签应该被移除
        content = result.file_path.read_text(encoding="utf-8")
        assert "<h1>" not in content
        assert "<p>" not in content
        assert "Hello" in content


class TestMultipartEmailParsing:
    """测试多部分邮件解析"""

    def test_collect_multipart_email(self, collector, tmp_path, sample_eml_multipart):
        """测试收集多部分邮件"""
        eml_file = tmp_path / "multipart.eml"
        eml_file.write_bytes(sample_eml_multipart)

        result = collector.collect(eml_file)

        assert result.success is True
        # 应该优先使用纯文本版本
        content = result.file_path.read_text(encoding="utf-8")
        assert "plain text version" in content


class TestEncodedHeaders:
    """测试编码邮件头"""

    def test_decode_encoded_subject(self, collector, tmp_path, sample_eml_encoded_subject):
        """测试解码编码主题"""
        eml_file = tmp_path / "encoded.eml"
        eml_file.write_bytes(sample_eml_encoded_subject)

        result = collector.collect(eml_file)

        assert result.success is True
        assert result.title == "测试邮件主题"


class TestMBOXParsing:
    """测试 MBOX 文件解析"""

    def test_collect_mbox_file(self, collector, sample_mbox_file):
        """测试收集 MBOX 文件"""
        result = collector.collect(sample_mbox_file)

        assert result.success is True
        assert result.metadata.get("collected_count", 0) >= 1

    def test_collect_mbox_with_max_emails(self, collector, sample_mbox_file):
        """测试限制最大邮件数"""
        result = collector.collect(sample_mbox_file, max_emails=1)

        assert result.success is True
        assert result.metadata.get("collected_count", 0) == 1

    def test_collect_mbox_metadata(self, collector, sample_mbox_file):
        """测试 MBOX 批量收集元数据"""
        result = collector.collect(sample_mbox_file)

        assert "total_emails" in result.metadata
        assert "collected_count" in result.metadata
        assert "failed_count" in result.metadata


class TestBodyExtraction:
    """测试邮件正文提取"""

    def test_extract_plain_text_body(self, collector):
        """测试提取纯文本正文"""
        msg = MIMEText("This is plain text content.", "plain", "utf-8")

        body = collector._extract_content(msg)

        assert body == "This is plain text content."

    def test_extract_html_body(self, collector):
        """测试提取 HTML 正文"""
        msg = MIMEText("<p>This is HTML content.</p>", "html", "utf-8")

        body = collector._extract_content(msg)

        assert "This is HTML content." in body
        assert "<p>" not in body

    def test_prefer_plain_text_over_html(self, collector):
        """测试优先纯文本"""
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("Plain text version", "plain", "utf-8"))
        msg.attach(MIMEText("<p>HTML version</p>", "html", "utf-8"))

        body = collector._extract_content(msg)

        assert "Plain text version" in body


class TestHeaderDecoding:
    """测试邮件头解码"""

    def test_decode_plain_header(self, collector):
        """测试解码普通邮件头"""
        header = "Simple Subject"
        decoded = collector._decode_header(header)
        assert decoded == "Simple Subject"

    def test_decode_utf8_header(self, collector):
        """测试解码 UTF-8 邮件头"""
        # =?UTF-8?B?5rWL6K+V?= is "测试" in Base64 encoded UTF-8
        header = "=?UTF-8?B?5rWL6K+V?="
        decoded = collector._decode_header(header)
        assert decoded == "测试"

    def test_decode_empty_header(self, collector):
        """测试解码空邮件头"""
        decoded = collector._decode_header("")
        assert decoded == ""

    def test_decode_none_header(self, collector):
        """测试解码 None 邮件头"""
        decoded = collector._decode_header(None)
        assert decoded == ""


class TestHTMLStripping:
    """测试 HTML 标签移除"""

    def test_strip_basic_html(self, collector):
        """测试移除基本 HTML 标签"""
        html = "<p>Hello <b>World</b></p>"
        text = collector._strip_html_tags(html)
        assert "Hello" in text
        assert "World" in text
        assert "<p>" not in text
        assert "<b>" not in text

    def test_strip_script_tags(self, collector):
        """测试移除脚本标签"""
        html = "<p>Content</p><script>alert('test')</script>"
        text = collector._strip_html_tags(html)
        assert "Content" in text
        assert "alert" not in text

    def test_strip_style_tags(self, collector):
        """测试移除样式标签"""
        html = "<style>.test{color:red}</style><p>Text</p>"
        text = collector._strip_html_tags(html)
        assert "Text" in text
        assert "color" not in text

    def test_convert_html_entities(self, collector):
        """测试转换 HTML 实体"""
        html = "&lt;test&gt; &amp; &quot;quoted&quot;"
        text = collector._strip_html_tags(html)
        assert "<test>" in text
        assert "&" in text
        assert '"quoted"' in text


class TestDateParsing:
    """测试日期解析"""

    def test_parse_valid_date(self, collector):
        """测试解析有效日期"""
        date_str = "Mon, 15 Jan 2024 10:30:00 +0000"
        parsed = collector._parse_date(date_str)
        assert "2024-01-15" in parsed
        assert "10:30:00" in parsed

    def test_parse_empty_date(self, collector):
        """测试解析空日期"""
        parsed = collector._parse_date("")
        assert parsed == ""

    def test_parse_invalid_date(self, collector):
        """测试解析无效日期"""
        # 无效日期返回原始字符串
        parsed = collector._parse_date("not a date")
        assert parsed == "not a date"


class TestRecipientParsing:
    """测试收件人解析"""

    def test_parse_single_recipient(self, collector):
        """测试解析单个收件人"""
        msg = email.message.Message()
        msg["To"] = "recipient@example.com"

        recipients = collector._parse_recipients(msg)

        assert "recipient@example.com" in recipients

    def test_parse_multiple_recipients(self, collector):
        """测试解析多个收件人"""
        msg = email.message.Message()
        msg["To"] = "to1@example.com, to2@example.com"
        msg["Cc"] = "cc@example.com"

        recipients = collector._parse_recipients(msg)

        assert len(recipients) == 3
        assert "to1@example.com" in recipients
        assert "to2@example.com" in recipients
        assert "cc@example.com" in recipients


class TestMetadataGeneration:
    """测试元数据生成"""

    def test_metadata_structure(self, collector, sample_eml_file):
        """测试元数据结构"""
        result = collector.collect(sample_eml_file)

        assert "id" in result.metadata
        assert "title" in result.metadata
        assert "source" in result.metadata
        assert "content_type" in result.metadata
        assert "collected_at" in result.metadata
        assert "tags" in result.metadata
        assert "word_count" in result.metadata
        assert "status" in result.metadata
        assert "sender" in result.metadata
        assert "recipients" in result.metadata
        assert "email_date" in result.metadata
        assert "message_id" in result.metadata
        assert result.metadata["content_type"] == "email"
        assert result.metadata["status"] == "processed"

    def test_metadata_id_from_message_id(self, collector, sample_eml_file):
        """测试从 Message-ID 生成元数据 ID"""
        result = collector.collect(sample_eml_file)

        # ID 应该基于 message_id 的哈希
        assert result.metadata["id"].startswith("email_")


class TestErrorHandling:
    """测试错误处理"""

    def test_collect_nonexistent_file(self, collector):
        """测试收集不存在的文件"""
        result = collector.collect("/nonexistent/path/email.eml")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_collect_unsupported_format(self, collector, tmp_path):
        """测试收集不支持的格式"""
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_text("Not an email")

        result = collector.collect(unsupported_file)

        assert result.success is False
        assert "Unsupported" in result.error


class TestSavedFileContent:
    """测试保存的文件内容"""

    def test_file_contains_yaml_frontmatter(self, collector, sample_eml_file):
        """测试文件包含 YAML Front Matter"""
        result = collector.collect(sample_eml_file)

        content = result.file_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "id:" in content
        assert "title:" in content
        assert "content_type: email" in content
        assert "sender:" in content

    def test_file_contains_email_headers(self, collector, sample_eml_file):
        """测试文件包含邮件头信息"""
        result = collector.collect(sample_eml_file)

        content = result.file_path.read_text(encoding="utf-8")
        assert "**From:**" in content
        assert "**To:**" in content
        assert "**Date:**" in content

    def test_file_contains_body(self, collector, sample_eml_file):
        """测试文件包含邮件正文"""
        result = collector.collect(sample_eml_file)

        content = result.file_path.read_text(encoding="utf-8")
        assert "email body content" in content


class TestEmailContentFormatting:
    """测试邮件内容格式化"""

    def test_format_email_content(self, collector):
        """测试格式化邮件内容"""
        content = collector._format_email_content(
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            email_date="2024-01-15 10:30:00",
            body="Email body text.",
        )

        assert "# Test Subject" in content
        assert "**From:** sender@example.com" in content
        assert "**To:** recipient@example.com" in content
        assert "**Date:** 2024-01-15 10:30:00" in content
        assert "---" in content
        assert "Email body text." in content


class TestEmailCollectorDedup:
    """Tests for EmailCollector dedup functionality."""

    def test_skip_existing_source_match_eml(self, tmp_path):
        """collect() with skip_existing=True returns failure when EML source exists."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test EML file
        eml_content = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

Test email body.
"""
        eml_file = tmp_path / "test.eml"
        eml_file.write_bytes(eml_content)

        storage.add_knowledge(id="email1", title="Existing Email",
                              content_type="email", source=str(eml_file.resolve()),
                              collected_at="2026-01-01")

        collector = EmailCollector(output_dir=tmp_path)
        result = collector.collect(eml_file, skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()

    def test_skip_existing_no_match_eml(self, tmp_path):
        """collect() with skip_existing=True proceeds when no duplicate."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test EML file
        eml_content = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

Test email body.
"""
        eml_file = tmp_path / "test.eml"
        eml_file.write_bytes(eml_content)

        collector = EmailCollector(output_dir=tmp_path)
        result = collector.collect(eml_file, skip_existing=True, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_skip_existing_false_allows_duplicates_eml(self, tmp_path):
        """collect() with skip_existing=False proceeds even with existing source."""
        from kb.storage.sqlite_storage import SQLiteStorage
        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Create a test EML file
        eml_content = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

Test email body.
"""
        eml_file = tmp_path / "test.eml"
        eml_file.write_bytes(eml_content)

        storage.add_knowledge(id="email1", title="Existing Email",
                              content_type="email", source=str(eml_file.resolve()),
                              collected_at="2026-01-01")

        collector = EmailCollector(output_dir=tmp_path)
        result = collector.collect(eml_file, skip_existing=False, storage=storage)

        assert result.success
        assert result.file_path.exists()
        storage.close()

    def test_content_hash_in_result_eml(self, tmp_path):
        """collect() returns content_hash in CollectResult for EML."""
        # Create a test EML file
        eml_content = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 15 Jan 2024 10:30:00 +0000
Message-ID: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

Test email body.
"""
        eml_file = tmp_path / "test.eml"
        eml_file.write_bytes(eml_content)

        collector = EmailCollector(output_dir=tmp_path)
        result = collector.collect(eml_file)

        assert result.success
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex length

    def test_collect_single_message_id_dedup(self, tmp_path):
        """collect_single() dedups by message_id in mbox format."""
        from kb.storage.sqlite_storage import SQLiteStorage
        from email.message import Message
        from email.mime.text import MIMEText

        db_path = tmp_path / "test.db"
        storage = SQLiteStorage(str(db_path))

        # Pre-add a message with the same message_id
        storage.add_knowledge(id="email1", title="Existing Email",
                              content_type="email", source="mbox:/path/to/test.mbox:<msg1@example.com>",
                              collected_at="2026-01-01")

        # Create a message with the same message_id
        msg = MIMEText("Test body", "plain", "utf-8")
        msg["Subject"] = "Test Subject"
        msg["From"] = "sender@example.com"
        msg["Message-ID"] = "<msg1@example.com>"

        collector = EmailCollector(output_dir=tmp_path)
        result = collector.collect_single(msg, source_file="/path/to/test.mbox",
                                          skip_existing=True, storage=storage)

        assert not result.success
        assert "Duplicate" in result.error
        storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
