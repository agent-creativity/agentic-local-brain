"""
Webpage collector module

Fetches web page content using httpx, extracts main content via Readability,
converts them to Markdown format and saves to the knowledge base.

Features:
- Asynchronous web page fetching
- Readability main content extraction
- HTML to Markdown conversion
- LLM automatic tag extraction (optional)
- Custom User-Agent
- Comprehensive error handling
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from readability import Document

from kb.collectors.base import BaseCollector, CollectResult


class WebpageCollector(BaseCollector):
    """
    Webpage collector.

    Fetches web page content from a URL, extracts main content,
    and converts it to Markdown format.

    Processing flow:
    1. Fetch web page HTML using httpx
    2. Extract main content using Readability
    3. Convert to Markdown using markdownify
    4. Generate metadata (title, tags, etc.)
    5. Save to ~/.knowledge-base/1_collect/webpages/ directory

    Dependencies:
    - httpx: Async HTTP client
    - readability-lxml: Python implementation of Mozilla Readability
    - markdownify: HTML to Markdown conversion
    - beautifulsoup4: HTML parsing support

    Examples:
        >>> collector = WebpageCollector()
        >>> result = collector.collect("https://example.com/article")
        >>> if result.success:
        ...     print(f"成功: {result.title}")
    """

    # Default configuration
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        timeout: Optional[int] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Initialize webpage collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
            timeout: HTTP request timeout in seconds, defaults to 30 seconds.
            user_agent: Custom User-Agent string.
        """
        super().__init__(output_dir)
        self._sub_dir = "webpages"
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._user_agent = user_agent or self.DEFAULT_USER_AGENT

    def collect(
        self,
        source: str,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        Collect web page content.

        Executes the complete web page collection flow:
        1. Validate URL format
        2. Fetch web page HTML
        3. Extract main content
        4. Convert to Markdown
        5. Generate metadata and save

        Args:
            source: Web page URL.
            tags: User-provided tag list (optional).
            title: Custom title (optional, defaults to extracted page title).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.

        Raises:
            ValueError: Invalid URL format.
        """
        url = source.strip()

        # Validate URL format
        if not self._is_valid_url(url):
            return CollectResult(
                success=False,
                error=f"无效的 URL 格式: {url}"
            )

        # Duplicate check (before any heavy processing)
        if skip_existing and storage:
            existing = self._check_duplicate(source=url, storage=storage)
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        try:
            # Fetch HTML
            html = self._fetch_html(url)

            # Extract main content
            content_html, extracted_title = self._extract_content(html)

            # Convert HTML to Markdown
            markdown_content = self._html_to_markdown(content_html)

            # Use extracted title if no custom title provided
            if not title:
                title = extracted_title or self._generate_title_from_content(markdown_content) or self._extract_title_from_url(url)

            # Generate metadata
            metadata = self._generate_metadata(
                title=title,
                content=markdown_content,
                source=url,
                tags=tags or [],
                **kwargs
            )

            # Generate safe filename
            filename = self._generate_safe_filename("webpage", title)

            # Save to file
            saved_path = self._save_to_file(
                content=markdown_content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir
            )

            # Count words
            word_count = self._count_words(markdown_content)

            # Generate content hash
            content_hash = self._generate_content_hash(markdown_content)

            return CollectResult(
                success=True,
                file_path=saved_path,
                title=title,
                word_count=word_count,
                tags=tags or [],
                metadata=metadata,
                content_hash=content_hash
            )

        except httpx.TimeoutException:
            return CollectResult(
                success=False,
                error=f"请求超时（{self._timeout}秒）: {url}\n"
                      f"提示：localbrain collect webpage 异常，请尝试用本地技能（如 mcp_fetch_fetch 或 agent-browser）获取网页的 markdown 内容和标题，"
                      f"然后通过 localbrain collect file add <本地文件路径> --title \"<标题>\" 收藏到知识库。"
            )
        except httpx.HTTPStatusError as e:
            return CollectResult(
                success=False,
                error=f"HTTP 错误 {e.response.status_code}: {url}\n"
                      f"提示：localbrain collect webpage 异常，请尝试用本地技能（如 mcp_fetch_fetch 或 agent-browser）获取网页的 markdown 内容和标题，"
                      f"然后通过 localbrain collect file add <本地文件路径> --title \"<标题>\" 收藏到知识库。"
            )
        except httpx.RequestError as e:
            return CollectResult(
                success=False,
                error=f"网络请求失败: {str(e)}\n"
                      f"提示：localbrain collect webpage 异常，请尝试用本地技能（如 mcp_fetch_fetch 或 agent-browser）获取网页的 markdown 内容和标题，"
                      f"然后通过 localbrain collect file add <本地文件路径> --title \"<标题>\" 收藏到知识库。"
            )
        except Exception as e:
            return CollectResult(
                success=False,
                error=f"网页处理失败: {str(e)}\n"
                      f"提示：localbrain collect webpage 异常，请尝试用本地技能（如 mcp_fetch_fetch 或 agent-browser）获取网页的 markdown 内容和标题，"
                      f"然后通过 localbrain collect file add <本地文件路径> --title \"<标题>\" 收藏到知识库。"
            )

    def _fetch_html(self, url: str) -> str:
        """
        Fetch web page HTML content.

        Uses httpx synchronous client to send a GET request
        with custom User-Agent and timeout settings.

        Args:
            url: Target web page URL.

        Returns:
            str: Web page HTML content.

        Raises:
            httpx.TimeoutException: Request timed out.
            httpx.HTTPStatusError: HTTP error status code.
            httpx.RequestError: Network request failed.
        """
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        with httpx.Client(
            timeout=self._timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = client.get(url)
            response.raise_for_status()

            # Detect encoding (must be set before accessing response.text)
            charset = response.charset_encoding
            if charset:
                # Sanitize: some servers return malformed charset like "utf-8, text/html"
                charset = charset.split(",")[0].split(";")[0].strip()
                response.encoding = charset
            else:
                # Try to detect encoding from HTML meta tags
                # Use response.content instead of response.text to avoid encoding issues
                encoding = self._detect_encoding(response.content.decode("utf-8", errors="ignore"))
                response.encoding = encoding

            return response.text

    def _extract_content(self, html: str) -> tuple[str, str]:
        """
        Extract webpage main content using Readability.

        Readability removes navigation bars, ads, sidebars and other
        irrelevant content, keeping only the main body text.

        Args:
            html: Web page HTML content.

        Returns:
            tuple[str, str]: (main content HTML, page title).

        Raises:
            RuntimeError: Content extraction failed.
        """
        try:
            doc = Document(html)

            # Extract main content HTML
            content_html = doc.summary()

            # Extract title
            title = doc.short_title()

            if not content_html or not content_html.strip():
                raise RuntimeError("无法提取网页正文内容，可能是动态加载的页面")

            return content_html, title

        except Exception as e:
            raise RuntimeError(f"Readability 内容提取失败: {str(e)}")

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML content to Markdown format.

        Uses the markdownify library for conversion,
        preserving headings, paragraphs, lists, links, images, etc.

        Args:
            html: HTML content.

        Returns:
            str: Content in Markdown format.
        """
        try:
            from markdownify import markdownify as md

            # Convert HTML to Markdown
            markdown = md(
                html,
                heading_style="ATX",  # Use # style headings
                bullets="-",  # Use - as list bullet
                strip=["script", "style", "nav", "footer", "header"],
            )

            # Clean up excessive blank lines
            markdown = re.sub(r"\n{3,}", "\n\n", markdown)

            return markdown.strip()

        except ImportError:
            raise ImportError(
                "markdownify 未安装。请运行: pip install markdownify"
            )
        except Exception as e:
            # If conversion fails, return cleaned plain text as fallback
            return self._html_to_text(html)

    def _extract_title(self, html: str) -> str:
        """
        Extract page title from HTML.

        Prioritizes extraction from the <title> tag,
        falls back to Open Graph meta or HTML content.

        Args:
            html: Web page HTML content.

        Returns:
            str: Page title.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Try to get from <title> tag
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                return title_tag.string.strip()

            # Try to get from Open Graph meta
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                return og_title["content"].strip()

            # Try to get from <h1> tag
            h1_tag = soup.find("h1")
            if h1_tag and h1_tag.get_text():
                return h1_tag.get_text().strip()

            return ""

        except ImportError:
            # If beautifulsoup4 is not available, use regex
            return self._extract_title_regex(html)
        except Exception:
            return ""

    @staticmethod
    def _generate_title_from_content(content: str, max_length: int = 50) -> str:
        """
        Generate a title from content body.

        Takes the first N characters of the body text as the title,
        truncating at sentence boundaries (period, newline, comma).

        Args:
            content: Markdown body content.
            max_length: Maximum title length.

        Returns:
            str: Generated title, or empty string if content is empty.
        """
        if not content or not content.strip():
            return ""

        # Remove markdown markup, get plain text
        text = re.sub(r"[#*`\[\]()>]", "", content).strip()
        if not text:
            return ""

        # Take first max_length characters
        title = text[:max_length].strip()

        # Try to truncate at natural sentence boundaries
        for sep in ["\n", "。", ".", "！", "!", "？", "?"]:
            idx = title.find(sep)
            if 0 < idx < len(title):
                title = title[:idx]
                break

        # Clean trailing punctuation
        while title and title[-1] in "，,；;：:、 ":
            title = title[:-1]

        return title.strip()

    def _extract_title_from_url(self, url: str) -> str:
        """
        Infer a title from the URL path.

        Used as a fallback when the title cannot be extracted from the page.
        Uses the last segment of the URL path as the title.

        Args:
            url: Web page URL.

        Returns:
            str: Inferred title.
        """
        # Remove query parameters and fragments
        url_path = url.split("?")[0].split("#")[0]

        # Get the last path segment
        parts = url_path.rstrip("/").split("/")
        if parts:
            last_part = parts[-1]
            # Remove file extension
            title = last_part.split(".")[0]
            # Replace hyphens and underscores with spaces
            title = title.replace("-", " ").replace("_", " ")
            # Capitalize first letter of each word
            return title.title()

        return "Untitled Page"

    def _save_to_markdown(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> Path:
        """
        Save content as a Markdown file with YAML Front Matter.

        Args:
            content: Markdown body content.
            metadata: YAML Front Matter metadata.
            filename: File name.

        Returns:
            Path: Path of the saved file.
        """
        # Create subdirectory
        target_dir = self.output_dir / self._sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate complete Markdown content
        yaml_header = self._format_yaml(metadata)
        full_content = f"---\n{yaml_header}---\n\n{content}"

        # Write to file
        file_path = target_dir / filename
        file_path.write_text(full_content, encoding="utf-8")

        return file_path

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: str,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate webpage metadata.

        Args:
            title: Document title.
            content: Document content.
            source: Original URL.
            tags: Tag list.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        # Generate unique ID
        timestamp = datetime.now()
        page_id = f"webpage_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Base metadata
        metadata = {
            "id": page_id,
            "title": title,
            "source": source,
            "content_type": "webpage",
            "collected_at": timestamp,
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
        }

        # Merge additional metadata
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """
        Validate whether a URL format is valid.

        Args:
            url: URL to validate.

        Returns:
            bool: Whether the URL is valid.
        """
        # Simple URL format validation
        pattern = r"^https?://"
        return bool(re.match(pattern, url, re.IGNORECASE))

    @staticmethod
    def _detect_encoding(html: str) -> str:
        """
        Detect character encoding from HTML content.

        Attempts to extract charset information from meta tags.

        Args:
            html: HTML content.

        Returns:
            str: Detected encoding, defaults to utf-8.
        """
        # Try to match <meta charset="...">
        match = re.search(r'<meta\s+charset=["\']?([^"\'>\s]+)', html, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try to match <meta http-equiv="Content-Type" content="...; charset=...">
        match = re.search(
            r'<meta\s+http-equiv=["\']?Content-Type["\']?\s+content=["\']?[^"\']*charset=([^"\'>\s]+)',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        return "utf-8"

    @staticmethod
    def _extract_title_regex(html: str) -> str:
        """
        Extract page title from HTML using regex.

        Args:
            html: HTML content.

        Returns:
            str: Page title.
        """
        # Match <title> tag
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # Remove possible HTML entities
            title = re.sub(r"&[^;]+;", "", title)
            return title

        return ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text (fallback method).

        Used as a fallback when markdownify is not available.

        Args:
            html: HTML content.

        Returns:
            str: Plain text content.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator="\n", strip=True)

            # Clean blank lines
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text

        except ImportError:
            # Simplest fallback: remove HTML tags
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text

    async def collect_batch(
        self,
        urls: List[str],
        tags: Optional[List[str]] = None,
        max_concurrent: int = 3,
    ) -> List[CollectResult]:
        """
        Batch collect web pages (async).

        Uses asynchronous concurrency to fetch multiple web pages for efficiency.

        Args:
            urls: List of URLs.
            tags: Common tag list (optional).
            max_concurrent: Maximum concurrency, defaults to 3.

        Returns:
            List[CollectResult]: List of collection results.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        async def collect_with_semaphore(url: str) -> CollectResult:
            async with semaphore:
                # Run synchronous method in event loop executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.collect, url, tags
                )

        for url in urls:
            task = collect_with_semaphore(url)
            tasks.append(task)

        return await asyncio.gather(*tasks)
