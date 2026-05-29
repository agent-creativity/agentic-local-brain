from __future__ import annotations

"""
Bookmark collector module

Collects bookmarks from browser bookmark files or HTML exports,
converts them to Markdown format and saves to the knowledge base.

Features:
- Parse Chrome/Edge/Safari/Firefox browser bookmarks
- Parse HTML export files (Netscape format)
- Preserve bookmark folder structure
- Concurrent processing (default 5 workers)
- Incremental updates (skip already collected bookmarks)
- Failure retry mechanism
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from kb.collectors.base import BaseCollector, CollectResult
from kb.collectors.bookmark_parser import (
    BookmarkItem,
    ChromeBookmarkParser,
    HTMLBookmarkParser,
    SafariBookmarkParser,
)

logger = logging.getLogger(__name__)


class BookmarkCollector(BaseCollector):
    """
    Bookmark collector.

    Collects bookmarks from browser bookmark files or HTML exports,
    extracts URLs and titles, preserves folder structure,
    converts them to Markdown format and saves to the knowledge base.

    Processing flow:
    1. Parse bookmark source (browser or HTML file)
    2. Extract all bookmark items (title, URL, folder path)
    3. Generate metadata (including folder hierarchy info)
    4. Save to ~/.knowledge-base/1_collect/bookmarks/ directory

    Supported bookmark sources:
    - Chrome: JSON format bookmark file
    - Edge: JSON format bookmark file (same as Chrome)
    - Firefox: HTML export file
    - Safari: plist format bookmark file
    - Generic: HTML export file (Netscape format)

    Examples:
        >>> collector = BookmarkCollector()
        >>> # Collect from Chrome
        >>> results = collector.collect_from_browser("chrome")
        >>> # Import from HTML file
        >>> results = collector.collect_from_file("bookmarks.html")
    """

    # Default configuration
    DEFAULT_MAX_CONCURRENT = 5  # Default max concurrency
    DEFAULT_MAX_RETRIES = 3  # Default max retries
    DEFAULT_RETRY_DELAY = 1.0  # Default retry delay (seconds)

    # Supported browser types
    SUPPORTED_BROWSERS = {"chrome", "edge", "firefox", "safari"}

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        max_concurrent: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> None:
        """
        Initialize bookmark collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
            max_concurrent: Max concurrency. Defaults to 5.
            max_retries: Max retries. Defaults to 3.
            retry_delay: Retry delay in seconds. Defaults to 1.0.
        """
        super().__init__(output_dir)
        self._sub_dir = "bookmarks"
        self._max_concurrent = max_concurrent or self.DEFAULT_MAX_CONCURRENT
        self._max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self._retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY

        # Set of collected URLs (for incremental updates)
        self._collected_urls: Set[str] = set()

    def collect(
        self,
        source: str | Path,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        Collect a single bookmark (BaseCollector interface).

        Args:
            source: Bookmark URL.
            tags: User-provided tag list (optional).
            title: Custom title (optional).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters, e.g. folder_path.

        Returns:
            CollectResult: Collection result.
        """
        url = str(source).strip()

        # Duplicate check (before any heavy processing)
        if skip_existing and storage:
            existing = self._check_duplicate(source=url, storage=storage)
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        # Get folder path
        folder_path = kwargs.get("folder_path", [])
        if isinstance(folder_path, str):
            folder_path = [folder_path]

        # Generate title
        if not title:
            title = self._extract_title_from_url(url)

        try:
            # Generate content (bookmark summary)
            content = self._generate_bookmark_content(
                title=title,
                url=url,
                folder_path=folder_path,
            )

            # Generate metadata
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source=url,
                tags=tags or [],
                folder_path=folder_path if folder_path else None,
                **{k: v for k, v in kwargs.items() if k != 'folder_path'},
            )

            # Generate safe filename
            filename = self._generate_safe_filename("bookmark", title)

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
                title=title,
                word_count=word_count,
                tags=tags or [],
                metadata=metadata,
                content_hash=content_hash,
            )

        except Exception as e:
            return CollectResult(
                success=False,
                error=f"书签处理失败: {str(e)}",
            )

    def collect_from_browser(
        self,
        browser: str,
        max_concurrent: Optional[int] = None,
        skip_existing: bool = True,
        storage=None,
    ) -> List[CollectResult]:
        """
        Collect bookmarks from browser.

        Automatically locates and parses browser bookmark files.

        Args:
            browser: Browser type (chrome/edge/firefox/safari).
            max_concurrent: Max concurrency. Defaults to the value set during initialization.
            skip_existing: Whether to skip already collected bookmarks. Defaults to True.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.

        Raises:
            ValueError: Unsupported browser type.
            FileNotFoundError: Browser bookmark file not found.
        """
        browser = browser.lower().strip()

        if browser not in self.SUPPORTED_BROWSERS:
            raise ValueError(
                f"不支持的浏览器类型: {browser}。"
                f"支持的类型: {', '.join(self.SUPPORTED_BROWSERS)}"
            )

        # Locate bookmark file
        bookmark_file = self._locate_browser_bookmark(browser)

        if not bookmark_file or not bookmark_file.exists():
            raise FileNotFoundError(
                f"未找到 {browser} 浏览器的书签文件。"
                f"请确保已安装 {browser} 并导出过书签。"
            )

        # Parse bookmarks
        bookmarks = self._parse_browser_bookmarks(browser, bookmark_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error=f"未在 {browser} 书签文件中找到任何书签",
                )
            ]

        # Concurrently collect bookmarks
        concurrency = max_concurrent or self._max_concurrent
        return self._collect_bookmarks(
            bookmarks=bookmarks,
            max_concurrent=concurrency,
            skip_existing=skip_existing,
            storage=storage,
        )

    def collect_from_file(
        self,
        html_file: str | Path,
        max_concurrent: Optional[int] = None,
        skip_existing: bool = True,
        storage=None,
    ) -> List[CollectResult]:
        """
        Import bookmarks from HTML export file.

        Args:
            html_file: HTML Bookmark file path.
            max_concurrent: Max concurrency. Defaults to the value set during initialization.
            skip_existing: Whether to skip already collected bookmarks. Defaults to True.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.

        Raises:
            FileNotFoundError: File does not exist.
            ValueError: Invalid file format.
        """
        html_file = Path(html_file).resolve()

        if not html_file.exists():
            raise FileNotFoundError(f"HTML 文件不存在: {html_file}")

        # Parse HTML bookmarks
        parser = HTMLBookmarkParser()
        try:
            bookmarks = parser.parse_file(html_file)
        except ValueError as e:
            return [
                CollectResult(
                    success=False,
                    error=str(e),
                )
            ]

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error="未在 HTML 文件中找到任何书签",
                )
            ]

        # Concurrently collect bookmarks
        concurrency = max_concurrent or self._max_concurrent
        return self._collect_bookmarks(
            bookmarks=bookmarks,
            max_concurrent=concurrency,
            skip_existing=skip_existing,
            storage=storage,
        )

    def collect_from_chrome_json(
        self,
        json_file: str | Path,
        max_concurrent: Optional[int] = None,
        skip_existing: bool = True,
        storage=None,
    ) -> List[CollectResult]:
        """
        Collect from Chrome/Edge JSON bookmark file.

        Args:
            json_file: Chrome JSON Bookmark file path.
            max_concurrent: Max concurrency.
            skip_existing: Whether to skip already collected bookmarks.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.
        """
        json_file = Path(json_file).resolve()

        if not json_file.exists():
            raise FileNotFoundError(f"JSON 文件不存在: {json_file}")

        # Parse Chrome bookmarks
        parser = ChromeBookmarkParser()
        bookmarks = parser.parse_file(json_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error="未在 JSON 文件中找到任何书签",
                )
            ]

        # Concurrently collect bookmarks
        concurrency = max_concurrent or self._max_concurrent
        return self._collect_bookmarks(
            bookmarks=bookmarks,
            max_concurrent=concurrency,
            skip_existing=skip_existing,
            storage=storage,
        )

    def collect_from_safari_plist(
        self,
        plist_file: str | Path,
        max_concurrent: Optional[int] = None,
        skip_existing: bool = True,
        storage=None,
    ) -> List[CollectResult]:
        """
        Collect from Safari plist bookmark file.

        Args:
            plist_file: Safari plist Bookmark file path.
            max_concurrent: Max concurrency.
            skip_existing: Whether to skip already collected bookmarks.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.
        """
        plist_file = Path(plist_file).resolve()

        if not plist_file.exists():
            raise FileNotFoundError(f"plist 文件不存在: {plist_file}")

        # Parse Safari bookmarks
        parser = SafariBookmarkParser()
        bookmarks = parser.parse_file(plist_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error="未在 plist 文件中找到任何书签",
                )
            ]

        # Concurrently collect bookmarks
        concurrency = max_concurrent or self._max_concurrent
        return self._collect_bookmarks(
            bookmarks=bookmarks,
            max_concurrent=concurrency,
            skip_existing=skip_existing,
            storage=storage,
        )

    def _collect_bookmarks(
        self,
        bookmarks: List[BookmarkItem],
        max_concurrent: int,
        skip_existing: bool,
        storage=None,
    ) -> List[CollectResult]:
        """
        Collect bookmark list concurrently.

        Args:
            bookmarks: Bookmark list.
            max_concurrent: Max concurrency.
            skip_existing: Whether to skip already collected bookmarks.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.
        """
        # Filter already collected bookmarks
        if skip_existing:
            if storage:
                # Use DB-backed dedup when storage is available
                new_bookmarks = []
                for b in bookmarks:
                    existing = storage.source_exists(b.url, content_type="bookmark")
                    if not existing:
                        new_bookmarks.append(b)
                skipped_count = len(bookmarks) - len(new_bookmarks)
                if skipped_count > 0:
                    print(f"跳过已收集的书签: {skipped_count} 个")
            else:
                # Fall back to file-scan behavior when no storage
                self._load_collected_urls()
                new_bookmarks = [
                    b for b in bookmarks if b.url not in self._collected_urls
                ]
                skipped_count = len(bookmarks) - len(new_bookmarks)
                if skipped_count > 0:
                    print(f"跳过已收集的书签: {skipped_count} 个")
        else:
            new_bookmarks = bookmarks

        if not new_bookmarks:
            print("所有书签都已收集，无需处理")
            return []

        print(f"开始收集 {len(new_bookmarks)} 个书签（并发数: {max_concurrent}）")

        # Use async concurrent processing
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                self._collect_bookmarks_async(new_bookmarks, max_concurrent, storage)
            )
        finally:
            loop.close()

        # Tally results
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        print(f"收集完成: 成功 {success_count} 个，失败 {failed_count} 个")

        return results

    async def _collect_bookmarks_async(
        self,
        bookmarks: List[BookmarkItem],
        max_concurrent: int,
        storage=None,
    ) -> List[CollectResult]:
        """
        Collect bookmarks asynchronously with concurrency.

        Args:
            bookmarks: Bookmark list.
            max_concurrent: Max concurrency.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            List[CollectResult]: List of collection results.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        async def collect_with_retry(bookmark: BookmarkItem) -> CollectResult:
            async with semaphore:
                return await self._collect_single_with_retry(bookmark, storage)

        for bookmark in bookmarks:
            task = collect_with_retry(bookmark)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exception results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    CollectResult(
                        success=False,
                        error=f"收集异常: {str(result)}",
                        title=bookmarks[i].title,
                    )
                )
            else:
                final_results.append(result)
                # Record collected URLs (use in-memory set only when no storage)
                if result.success and bookmarks[i].url and not storage:
                    self._collected_urls.add(bookmarks[i].url)

        return final_results

    async def _collect_single_with_retry(
        self,
        bookmark: BookmarkItem,
        storage=None,
    ) -> CollectResult:
        """
        Collect a single bookmark with retry mechanism.

        Args:
            bookmark: Bookmark item.
            storage: SQLiteStorage instance for duplicate detection (optional).

        Returns:
            CollectResult: Collection result.
        """
        last_error = None

        for attempt in range(self._max_retries):
            try:
                result = self.collect(
                    source=bookmark.url,
                    title=bookmark.title,
                    folder_path=bookmark.folder_path,
                    added_date=bookmark.added_date,
                    storage=storage,
                )

                if result.success:
                    return result

                last_error = result.error

            except Exception as e:
                last_error = str(e)

            # If not the last attempt, wait and retry
            if attempt < self._max_retries - 1:
                delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)

        return CollectResult(
            success=False,
            error=f"重试 {self._max_retries} 次后失败: {last_error}",
            title=bookmark.title,
        )

    def _generate_bookmark_content(
        self,
        title: str,
        url: str,
        folder_path: List[str],
    ) -> str:
        """
        Generate Markdown content for a bookmark.

        Args:
            title: Bookmark title.
            url: Bookmark URL.
            folder_path: Folder path.

        Returns:
            str: Content in Markdown format.
        """
        lines = []

        # Title.
        lines.append(f"# {title}")
        lines.append("")

        # Original link
        lines.append(f"**原始链接:** {url}")
        lines.append("")

        # Folder path.
        if folder_path:
            folder_str = " / ".join(folder_path)
            lines.append(f"**分类路径:** {folder_str}")
            lines.append("")

        # Collection note
        lines.append("---")
        lines.append("")
        lines.append("> 此书签由 BookmarkCollector 自动收集")
        lines.append("")

        return "\n".join(lines)

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: str,
        tags: Optional[List[str]] = None,
        folder_path: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate bookmark metadata.

        Args:
            title: Document title.
            content: Document content.
            source: Original URL.
            tags: Tag list.
            folder_path: Folder path.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        # Generate unique ID
        timestamp = datetime.now()
        bookmark_id = f"bookmark_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Base metadata
        metadata = {
            "id": bookmark_id,
            "title": title,
            "source": source,
            "content_type": "bookmark",
            "collected_at": timestamp,
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
        }

        # Add folder path
        if folder_path:
            metadata["folder_path"] = folder_path

        # Add added date
        if "added_date" in kwargs and kwargs["added_date"]:
            metadata["added_date"] = kwargs["added_date"]

        # Merge additional metadata (exclude already processed fields)
        extra_kwargs = {k: v for k, v in kwargs.items() if k != "added_date"}
        metadata.update(extra_kwargs)

        return metadata

    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """
        Infer title from URL.

        Args:
            url: Web page URL.

        Returns:
            str: Inferred title.
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)

            # Get last path segment
            path = parsed.path.rstrip("/")
            if path:
                last_part = path.split("/")[-1]
                # Remove file extension
                title = last_part.split(".")[0]
                # Replace hyphens and underscores with spaces
                title = title.replace("-", " ").replace("_", " ")
                # Capitalize first letter
                return title.title() if title else parsed.netloc

            return parsed.netloc

        except Exception:
            return "Untitled Bookmark"

    def _locate_browser_bookmark(self, browser: str) -> Optional[Path]:
        """
        Locate browser bookmark file.

        Args:
            browser: Browser type.

        Returns:
            Optional[Path]: Bookmark file path, or None if not found.
        """
        import platform
        from pathlib import Path

        system = platform.system()
        home = Path.home()

        if browser in ("chrome", "edge"):
            if system == "Darwin":  # macOS
                if browser == "chrome":
                    return home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Bookmarks"
                else:  # edge
                    return home / "Library" / "Application Support" / "Microsoft Edge" / "Default" / "Bookmarks"
            elif system == "Windows":
                if browser == "chrome":
                    return home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Bookmarks"
                else:  # edge
                    return home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Bookmarks"
            elif system == "Linux":
                if browser == "chrome":
                    return home / ".config" / "google-chrome" / "Default" / "Bookmarks"
                else:  # edge
                    return home / ".config" / "microsoft-edge" / "Default" / "Bookmarks"

        elif browser == "firefox":
            # Firefox uses HTML export, requires user to manually export
            # Return None here, prompt user to specify file manually
            return None

        elif browser == "safari":
            if system == "Darwin":  # macOS
                return home / "Library" / "Safari" / "Bookmarks.plist"

        return None

    def _parse_browser_bookmarks(
        self,
        browser: str,
        bookmark_file: Path,
    ) -> List[BookmarkItem]:
        """
        Parse browser bookmark file.

        Args:
            browser: Browser type.
            bookmark_file: Bookmark file path.

        Returns:
            List[BookmarkItem]: Bookmark list.
        """
        if browser in ("chrome", "edge"):
            parser = ChromeBookmarkParser()
            return parser.parse_file(bookmark_file)

        elif browser == "safari":
            parser = SafariBookmarkParser()
            return parser.parse_file(bookmark_file)

        else:
            raise ValueError(f"不支持的浏览器类型: {browser}")

    def _load_collected_urls(self) -> None:
        """
        Load collected bookmark URLs (for incremental updates).

        Scans existing bookmark files in the output_dir/bookmarks/ directory,
        extracts their source URLs and records them.
        """
        self._collected_urls.clear()

        bookmark_dir = self.output_dir / self._sub_dir
        if not bookmark_dir.exists():
            return

        # Scan all .md files
        for md_file in bookmark_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # Extract source field
                import re

                match = re.search(r"^source: (.+)$", content, re.MULTILINE)
                if match:
                    url = match.group(1).strip()
                    # Remove possible quotes
                    url = url.strip('"').strip("'")
                    if url:
                        self._collected_urls.add(url)
            except Exception:
                # Ignore files that fail to read
                continue

        if self._collected_urls:
            print(f"已加载 {len(self._collected_urls)} 个已收集的书签 URL")

    def _extract_content(self, source: Any) -> str:
        """
        Extract plain text content (BaseCollector abstract method).

        Args:
            source: Data source. (Bookmark URL.)

        Returns:
            str: Extracted plain text content.
        """
        url = str(source)
        title = self._extract_title_from_url(url)
        return f"# {title}\n\n**链接:** {url}"

    def get_supported_browsers(self) -> List[str]:
        """
        Get list of supported browsers.

        Returns:
            List[str]: List of supported browser names.
        """
        return list(self.SUPPORTED_BROWSERS)

    def collect_single_url(
        self,
        url: str,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        auto_tag: bool = False,
        config=None,
        skip_existing: bool = False,
        storage=None,
    ) -> CollectResult:
        """
        Collect a single bookmark URL with optional LLM auto-tagging.

        Args:
            url: The URL to bookmark.
            tags: Optional list of tags. If provided, auto_tag is skipped.
            title: Optional custom title. If not provided, extracted from page.
            auto_tag: If True and no tags provided, fetch page content and use
                      LLM (TagExtractor) to automatically generate tags.
            config: Optional Config object for TagExtractor initialization.
                    Required if auto_tag=True.
            skip_existing: If True, skip if URL already exists in storage.
            storage: SQLiteStorage instance for duplicate detection.

        Returns:
            CollectResult with bookmark metadata.
        """
        url = url.strip()

        # Validate URL (must be http/https)
        if not self._is_valid_url(url):
            return CollectResult(
                success=False,
                error=f"Invalid URL format: {url}. URL must start with http:// or https://",
            )

        # Duplicate check (before any heavy processing)
        if skip_existing and storage:
            existing = self._check_duplicate(source=url, storage=storage)
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        extracted_title = title
        extracted_tags = tags

        # If auto_tag is True and no tags provided, fetch page for tag extraction
        if auto_tag and not tags:
            if config is None:
                # Log warning but continue without auto-tags
                logger.warning(
                    "auto_tag=True but no config provided. "
                    "Skipping auto-tagging. Provide a Config object to enable LLM tagging."
                )
            else:
                # Fetch page info for title and tag extraction
                page_info = self._fetch_page_info(url)

                # Extract title from page if not provided
                if not extracted_title and page_info.get("title"):
                    extracted_title = page_info["title"]

                # Use TagExtractor to generate tags
                page_content = page_info.get("content", "")
                if page_content:
                    try:
                        # Lazy import to avoid circular dependencies
                        from kb.processors.tag_extractor import TagExtractor

                        extractor = TagExtractor.from_config(config)
                        tag_title = extracted_title or self._extract_title_from_url(url)
                        result = extractor.process(title=tag_title, content=page_content)
                        if result.success:
                            extracted_tags = result.data.get('tags', [])  # Dict with tags and summary
                        else:
                            logger.warning(f"Tag extraction returned error: {result.error}. Continuing without auto-tags.")
                    except ValueError as e:
                        logger.warning(f"Tag extraction skipped (configuration error): {e}")
                    except Exception as e:
                        # Log warning but continue without auto-tags (graceful degradation)
                        logger.warning(f"Tag extraction failed: {e}. Continuing without auto-tags.")

        # If title still not provided, extract from URL path
        if not extracted_title:
            extracted_title = self._extract_title_from_url(url)

        # Call the existing collect() method
        return self.collect(source=url, tags=extracted_tags, title=extracted_title)

    def _fetch_page_info(self, url: str) -> Dict[str, Any]:
        """
        Fetch page title and content for tag extraction.

        This method fetches the page HTML, extracts the title from <title> tag,
        and extracts the main content using readability for LLM tag generation.

        Args:
            url: The URL to fetch.

        Returns:
            Dict with 'title' and 'content' keys (may be empty on failure).
        """
        result: Dict[str, Any] = {"title": "", "content": ""}

        try:
            import httpx

            # Fetch page HTML
            response = httpx.get(
                url,
                timeout=30,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            html = response.text

            # Extract title from <title> tag
            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                result["title"] = title_match.group(1).strip()

            # Extract main content using readability-lxml
            try:
                from readability import Document

                doc = Document(html)
                content_html = doc.summary()

                # Convert HTML to plain text
                result["content"] = self._html_to_plain_text(content_html)

                # Use readability's title if no title found yet
                if not result["title"]:
                    result["title"] = doc.short_title()

            except ImportError:
                logger.warning(
                    "readability-lxml not installed. "
                    "Install with: pip install readability-lxml"
                )
            except Exception as e:
                logger.warning(f"Readability extraction failed: {e}")

        except ImportError:
            logger.warning("httpx not installed. Install with: pip install httpx")
        except Exception as e:
            logger.warning(f"Failed to fetch page info from {url}: {e}")

        return result

    def _html_to_plain_text(self, html: str) -> str:
        """
        Convert HTML to plain text by stripping tags.

        Args:
            html: HTML content.

        Returns:
            Plain text content.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            import re
            text = re.sub(r"\n{3,}", "\n\n", text)

            return text.strip()

        except ImportError:
            # Fallback: simple regex-based tag stripping
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """
        Validate URL format (must start with http:// or https://).

        Args:
            url: The URL to validate.

        Returns:
            True if valid, False otherwise.
        """
        import re
        pattern = r"^https?://"
        return bool(re.match(pattern, url, re.IGNORECASE))
