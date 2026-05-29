"""
Email collector module

Supports parsing MBOX and EML email files, extracting content and saving to the knowledge base.
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
    Email collector.

    Supports parsing the following email file formats:
    - MBOX: Archive file containing multiple emails
    - EML: Single email file

    Processing flow:
    1. Detect file type (MBOX or EML)
    2. Parse email content
    3. Extract email body (prefer plain text, fall back to HTML)
    4. Generate YAML Front Matter metadata.
    5. Save to ~/.knowledge-base/1_collect/emails/ directory.
    6. Return collection result.

    Examples:
        >>> collector = EmailCollector()
        >>> result = collector.collect("inbox.mbox", max_emails=50)
        >>> if result.success:
        ...     print(f"成功收集 {result.metadata['collected_count']} 封Emails")
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize email collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
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
        Collect email file.

        Args:
            source: Email file path (.mbox or .eml).
            tags: User-provided tag list (optional).
            max_emails: Maximum number of emails to collect (for MBOX files only, defaults to 100).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result. For MBOX files, returns batch collection result.
        """
        file_path = Path(source).resolve()

        # Validate file exists
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
        Collect emails from MBOX file.

        Args:
            file_path: MBOX file path.
            tags: Tag list.
            max_emails: Maximum number of emails to collect.
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Batch collection result.
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

        # Return batch collection result
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
        Collect a single EML file.

        Args:
            file_path: EML file path.
            tags: Tag list.
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.
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
        Collect a single email.

        Args:
            msg: email.message.Message object.
            tags: Tag list.
            source_file: Source file path.
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.
        """
        try:
            # Extract email header info.
            subject = self._decode_header(msg.get("Subject", ""))
            sender = self._decode_header(msg.get("From", ""))
            recipients = self._parse_recipients(msg)
            message_id = msg.get("Message-ID", "")
            email_date = self._parse_date(msg.get("Date", ""))

            # If no subject, use placeholder
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

            # Extract body
            body = self._extract_content(msg)

            # Generate content
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

            # Generate metadata
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

            # Generate safe filename
            filename = self._generate_safe_filename("email", subject)

            # Save to file
            saved_path = self._save_to_file(
                content=content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir,
            )

            # Count words
            word_count = self._count_words(content)

            # Generate content hash
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
        Extract body content from email.

        Prioritizes plain text; if unavailable, extracts HTML and strips tags.

        Args:
            msg: email.message.Message object.

        Returns:
            str: Extracted text content.
        """
        text_content = ""
        html_content = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
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

        # Prefer plain text
        if text_content:
            return text_content.strip()

        # Fall back to HTML (strip tags)
        if html_content:
            return self._strip_html_tags(html_content).strip()

        return ""

    def _decode_payload(self, part: Message) -> str:
        """
        Decode email part content.

        Args:
            part: Email part.

        Returns:
            str: Decoded text.
        """
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""

            # Try different encodings
            charset = part.get_content_charset() or "utf-8"
            encodings = [charset, "utf-8", "latin-1", "gb2312", "gbk"]

            for encoding in encodings:
                try:
                    return payload.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    continue

            # Last resort fallback
            return payload.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _decode_header(self, header: str) -> str:
        """
        Decode email header.

        Args:
            header: Raw email header.

        Returns:
            str: Decoded string.
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
        Parse recipient list.

        Args:
            msg: Email message.

        Returns:
            List[str]: List of recipients.
        """
        recipients = []

        for header in ["To", "Cc"]:
            value = msg.get(header, "")
            if value:
                decoded = self._decode_header(value)
                # Split multiple addresses
                for addr in decoded.split(","):
                    addr = addr.strip()
                    if addr:
                        recipients.append(addr)

        return recipients

    def _parse_date(self, date_str: str) -> str:
        """
        Parse email date.

        Args:
            date_str: Date string.

        Returns:
            str: Formatted date string.
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
        Strip HTML tags.

        Args:
            html: HTML content.

        Returns:
            str: Plain text content.
        """
        # Remove scripts and styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Handle HTML entities
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", '"', text)

        # Clean up excessive whitespace
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
        Format email content as Markdown.

        Args:
            subject: Subject.
            sender: Sender.
            recipients: List of recipients.
            email_date: Date.
            body: Body text.

        Returns:
            str: Content in Markdown format.
        """
        lines = []

        # Title.
        lines.append(f"# {subject}")
        lines.append("")

        # Email header information
        lines.append(f"**From:** {sender}")
        if recipients:
            lines.append(f"**To:** {', '.join(recipients)}")
        if email_date:
            lines.append(f"**Date:** {email_date}")
        lines.append("")

        # Separator line
        lines.append("---")
        lines.append("")

        # Body
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
        Generate email metadata.

        Args:
            title: Email subject.
            content: Document content.
            source: Original data source.
            tags: Tag list.
            sender: Sender.
            recipients: List of recipients.
            email_date: Email date.
            message_id: Emails ID
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        # Generate unique ID
        if message_id:
            # Use hash of message_id as ID
            id_hash = hashlib.md5(message_id.encode()).hexdigest()[:12]
            email_id = f"email_{id_hash}"
        else:
            timestamp = datetime.now()
            email_id = f"email_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Base metadata
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

        # Merge additional metadata
        metadata.update(kwargs)

        return metadata
