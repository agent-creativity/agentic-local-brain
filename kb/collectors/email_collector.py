"""
邮件收集器模块

支持解析 MBOX 和 EML 邮件文件，提取内容并保存到知识库。
"""

import email
import hashlib
import mailbox
import re
from datetime import datetime
from email import policy
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser, Parser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from kb.collectors.base import BaseCollector, CollectResult


class EmailCollector(BaseCollector):
    """
    邮件收集器

    支持解析以下格式的邮件文件：
    - MBOX: 包含多封邮件的归档文件
    - EML: 单封邮件文件

    处理流程：
    1. 检测文件类型（MBOX 或 EML）
    2. 解析邮件内容
    3. 提取邮件正文（优先纯文本，降级到 HTML）
    4. 生成 YAML Front Matter 元数据
    5. 保存到 ~/.knowledge-base/1_collect/emails/ 目录
    6. 返回收集结果

    示例：
        >>> collector = EmailCollector()
        >>> result = collector.collect("inbox.mbox", max_emails=50)
        >>> if result.success:
        ...     print(f"成功收集 {result.metadata['collected_count']} 封邮件")
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        初始化邮件收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
        """
        super().__init__(output_dir)
        self._sub_dir = "emails"

    def collect(
        self,
        source: Union[str, Path],
        tags: Optional[List[str]] = None,
        max_emails: int = 100,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        收集邮件文件

        Args:
            source: 邮件文件路径（.mbox 或 .eml）
            tags: 用户提供的标签列表（可选）
            max_emails: 最大收集邮件数（仅对 MBOX 文件有效，默认 100）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果。对于 MBOX 文件，返回批量收集结果
        """
        file_path = Path(source).resolve()

        # 验证文件存在
        if not file_path.exists():
            return CollectResult(success=False, error=f"File not found: {file_path}")

        ext = file_path.suffix.lower()

        try:
            if ext == ".mbox":
                return self._collect_mbox(file_path, tags=tags, max_emails=max_emails,
                                          skip_existing=skip_existing, storage=storage, **kwargs)
            elif ext == ".eml":
                return self._collect_eml(file_path, tags=tags,
                                         skip_existing=skip_existing, storage=storage, **kwargs)
            else:
                return CollectResult(
                    success=False,
                    error=f"Unsupported file format: {ext}. Supported: .mbox, .eml",
                )
        except Exception as e:
            return CollectResult(success=False, error=f"Failed to collect emails: {str(e)}")

    def _collect_mbox(
        self,
        file_path: Path,
        tags: Optional[List[str]] = None,
        max_emails: int = 100,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        收集 MBOX 文件中的邮件

        Args:
            file_path: MBOX 文件路径
            tags: 标签列表
            max_emails: 最大收集邮件数
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 批量收集结果
        """
        mbox = mailbox.mbox(str(file_path))
        collected_count = 0
        failed_count = 0
        skipped_count = 0
        results: List[CollectResult] = []

        for i, msg in enumerate(mbox):
            if i >= max_emails:
                break

            result = self.collect_single(msg, tags=tags, source_file=str(file_path),
                                         skip_existing=skip_existing, storage=storage, **kwargs)
            results.append(result)

            if result.success:
                collected_count += 1
            elif result.error and "Duplicate" in result.error:
                skipped_count += 1
            else:
                failed_count += 1

        mbox.close()

        # 返回批量收集结果
        if collected_count > 0 or skipped_count > 0:
            # Include individual results for CLI to register to database
            individual_results = [r for r in results if r.success]
            return CollectResult(
                success=True,
                title=f"MBOX: {file_path.name}",
                word_count=sum(r.word_count for r in results if r.success),
                tags=tags or [],
                metadata={
                    "source_file": str(file_path),
                    "total_emails": collected_count + failed_count + skipped_count,
                    "collected_count": collected_count,
                    "failed_count": failed_count,
                    "skipped_count": skipped_count,
                    "individual_results": individual_results,  # Include for DB registration
                },
            )
        else:
            return CollectResult(
                success=False,
                error=f"Failed to collect any emails from {file_path.name}",
                metadata={
                    "source_file": str(file_path),
                    "total_emails": failed_count,
                    "collected_count": 0,
                    "failed_count": failed_count,
                    "skipped_count": skipped_count,
                },
            )

    def _collect_eml(
        self,
        file_path: Path,
        tags: Optional[List[str]] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        收集单个 EML 文件

        Args:
            file_path: EML 文件路径
            tags: 标签列表
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果
        """
        try:
            with open(file_path, "rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)
            return self.collect_single(msg, tags=tags, source_file=str(file_path),
                                       skip_existing=skip_existing, storage=storage, **kwargs)
        except Exception as e:
            return CollectResult(success=False, error=f"Failed to parse EML file: {str(e)}")

    def collect_single(
        self,
        msg: Message,
        tags: Optional[List[str]] = None,
        source_file: Optional[str] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        收集单封邮件

        Args:
            msg: email.message.Message 对象
            tags: 标签列表
            source_file: 源文件路径
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果
        """
        try:
            # 提取邮件头信息
            subject = self._decode_header(msg.get("Subject", ""))
            sender = self._decode_header(msg.get("From", ""))
            recipients = self._parse_recipients(msg)
            message_id = msg.get("Message-ID", "")
            email_date = self._parse_date(msg.get("Date", ""))

            # 如果没有主题，使用占位符
            if not subject:
                subject = "(No Subject)"

            # Build source key for dedup
            # For .eml files, use the file path directly
            # For mbox entries, use mbox:file_path:message_id format
            file_path = Path(source_file) if source_file else None
            if file_path and file_path.suffix.lower() == ".eml":
                source_key = str(file_path.resolve())
            elif source_file and message_id:
                source_key = f"mbox:{source_file}:{message_id}"
            elif source_file:
                source_key = str(source_file)
            else:
                source_key = message_id or "email"

            # Duplicate check (before any heavy processing)
            if skip_existing and storage:
                existing = self._check_duplicate(source=source_key, storage=storage)
                if existing:
                    return CollectResult(
                        success=False,
                        error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                    )

            # 提取正文
            body = self._extract_content(msg)

            # 生成内容
            content = self._format_email_content(
                subject=subject,
                sender=sender,
                recipients=recipients,
                email_date=email_date,
                body=body,
            )

            # Filter out 'title' from kwargs to avoid conflict with subject
            # Email collectors always use subject as title
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'title'}

            # 生成元数据
            metadata = self._generate_metadata(
                title=subject,
                content=content,
                source=source_file or "email",
                tags=tags,
                sender=sender,
                recipients=recipients,
                email_date=email_date,
                message_id=message_id,
                **filtered_kwargs,
            )

            # 生成安全的文件名
            filename = self._generate_safe_filename("email", subject)

            # 保存到文件
            saved_path = self._save_to_file(
                content=content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir,
            )

            # 统计字数
            word_count = self._count_words(content)

            # 生成内容哈希
            content_hash = self._generate_content_hash(content)

            return CollectResult(
                success=True,
                file_path=saved_path,
                title=subject,
                word_count=word_count,
                tags=tags or [],
                metadata=metadata,
                content_hash=content_hash,
            )

        except Exception as e:
            return CollectResult(success=False, error=f"Failed to process email: {str(e)}")

    def _extract_content(self, msg: Message) -> str:
        """
        从邮件中提取正文内容

        优先提取纯文本，如果没有则提取 HTML 并去除标签

        Args:
            msg: email.message.Message 对象

        Returns:
            str: 提取的文本内容
        """
        text_content = ""
        html_content = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # 跳过附件
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    text_content = self._decode_payload(part)
                elif content_type == "text/html" and not text_content:
                    html_content = self._decode_payload(part)
        else:
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                text_content = self._decode_payload(msg)
            elif content_type == "text/html":
                html_content = self._decode_payload(msg)

        # 优先使用纯文本
        if text_content:
            return text_content.strip()

        # 降级到 HTML（去除标签）
        if html_content:
            return self._strip_html_tags(html_content).strip()

        return ""

    def _decode_payload(self, part: Message) -> str:
        """
        解码邮件部分的内容

        Args:
            part: 邮件部分

        Returns:
            str: 解码后的文本
        """
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""

            # 尝试不同的编码
            charset = part.get_content_charset() or "utf-8"
            encodings = [charset, "utf-8", "latin-1", "gb2312", "gbk"]

            for encoding in encodings:
                try:
                    return payload.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    continue

            # 最后的降级方案
            return payload.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _decode_header(self, header: str) -> str:
        """
        解码邮件头

        Args:
            header: 原始邮件头

        Returns:
            str: 解码后的字符串
        """
        if not header:
            return ""

        try:
            decoded_parts = decode_header(header)
            result = []
            for content, charset in decoded_parts:
                if isinstance(content, bytes):
                    charset = charset or "utf-8"
                    try:
                        result.append(content.decode(charset))
                    except (UnicodeDecodeError, LookupError):
                        result.append(content.decode("utf-8", errors="replace"))
                else:
                    result.append(content)
            return "".join(result)
        except Exception:
            return str(header)

    def _parse_recipients(self, msg: Message) -> List[str]:
        """
        解析收件人列表

        Args:
            msg: 邮件消息

        Returns:
            List[str]: 收件人列表
        """
        recipients = []

        for header in ["To", "Cc"]:
            value = msg.get(header, "")
            if value:
                decoded = self._decode_header(value)
                # 分割多个地址
                for addr in decoded.split(","):
                    addr = addr.strip()
                    if addr:
                        recipients.append(addr)

        return recipients

    def _parse_date(self, date_str: str) -> str:
        """
        解析邮件日期

        Args:
            date_str: 日期字符串

        Returns:
            str: 格式化的日期字符串
        """
        if not date_str:
            return ""

        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return date_str

    def _strip_html_tags(self, html: str) -> str:
        """
        去除 HTML 标签

        Args:
            html: HTML 内容

        Returns:
            str: 纯文本内容
        """
        # 移除脚本和样式
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # 移除 HTML 标签
        text = re.sub(r"<[^>]+>", " ", html)

        # 处理 HTML 实体
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", '"', text)

        # 清理多余空白
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _format_email_content(
        self,
        subject: str,
        sender: str,
        recipients: List[str],
        email_date: str,
        body: str,
    ) -> str:
        """
        格式化邮件内容为 Markdown

        Args:
            subject: 主题
            sender: 发件人
            recipients: 收件人列表
            email_date: 日期
            body: 正文

        Returns:
            str: Markdown 格式的内容
        """
        lines = []

        # 标题
        lines.append(f"# {subject}")
        lines.append("")

        # 邮件头信息
        lines.append(f"**From:** {sender}")
        if recipients:
            lines.append(f"**To:** {', '.join(recipients)}")
        if email_date:
            lines.append(f"**Date:** {email_date}")
        lines.append("")

        # 分隔线
        lines.append("---")
        lines.append("")

        # 正文
        lines.append(body)

        return "\n".join(lines)

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: Any,
        tags: Optional[List[str]] = None,
        sender: str = "",
        recipients: Optional[List[str]] = None,
        email_date: str = "",
        message_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成邮件元数据

        Args:
            title: 邮件主题
            content: 文档内容
            source: 原始数据源
            tags: 标签列表
            sender: 发件人
            recipients: 收件人列表
            email_date: 邮件日期
            message_id: 邮件 ID
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        # 生成唯一 ID
        if message_id:
            # 使用 message_id 的哈希作为 ID
            id_hash = hashlib.md5(message_id.encode()).hexdigest()[:12]
            email_id = f"email_{id_hash}"
        else:
            timestamp = datetime.now()
            email_id = f"email_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 基础元数据
        metadata = {
            "id": email_id,
            "title": title,
            "source": str(source),
            "content_type": "email",
            "collected_at": datetime.now(),
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
            "sender": sender,
            "recipients": recipients or [],
            "email_date": email_date,
            "message_id": message_id,
        }

        # 合并额外的元数据
        metadata.update(kwargs)

        return metadata
