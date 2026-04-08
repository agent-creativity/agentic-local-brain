from __future__ import annotations

"""
书签收集器模块

从浏览器书签或 HTML 导出文件中收集书签，
转换为 Markdown 格式并保存到知识库。

支持功能：
- 解析 Chrome/Edge/Safari/Firefox 浏览器书签
- 解析 HTML 导出文件（Netscape 格式）
- 保留书签文件夹结构
- 并发处理（默认 5 个并发）
- 增量更新（跳过已收集的书签）
- 失败重试机制
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
    书签收集器

    从浏览器书签或 HTML 导出文件中收集书签，
    提取 URL 和标题，保留文件夹结构，
    转换为 Markdown 格式并保存到知识库。

    处理流程：
    1. 解析书签源（浏览器或 HTML 文件）
    2. 提取所有书签项（标题、URL、文件夹路径）
    3. 生成元数据（包含文件夹层级信息）
    4. 保存到 ~/.knowledge-base/1_collect/bookmarks/ 目录

    支持的书签源：
    - Chrome: JSON 格式书签文件
    - Edge: JSON 格式书签文件（与 Chrome 相同）
    - Firefox: HTML 导出文件
    - Safari: plist 格式书签文件
    - 通用: HTML 导出文件（Netscape 格式）

    示例：
        >>> collector = BookmarkCollector()
        >>> # 从 Chrome 收集
        >>> results = collector.collect_from_browser("chrome")
        >>> # 从 HTML 文件导入
        >>> results = collector.collect_from_file("bookmarks.html")
    """

    # 默认配置
    DEFAULT_MAX_CONCURRENT = 5  # 默认最大并发数
    DEFAULT_MAX_RETRIES = 3  # 默认最大重试次数
    DEFAULT_RETRY_DELAY = 1.0  # 默认重试延迟（秒）

    # 支持的浏览器类型
    SUPPORTED_BROWSERS = {"chrome", "edge", "firefox", "safari"}

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        max_concurrent: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> None:
        """
        初始化书签收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
            max_concurrent: 最大并发数，默认 5
            max_retries: 最大重试次数，默认 3
            retry_delay: 重试延迟（秒），默认 1.0
        """
        super().__init__(output_dir)
        self._sub_dir = "bookmarks"
        self._max_concurrent = max_concurrent or self.DEFAULT_MAX_CONCURRENT
        self._max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self._retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY

        # 已收集的 URL 集合（用于增量更新）
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
        收集单个书签（兼容 BaseCollector 接口）

        Args:
            source: 书签 URL
            tags: 用户提供的标签列表（可选）
            title: 自定义标题（可选）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数，支持 folder_path 等

        Returns:
            CollectResult: 收集结果
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

        # 获取文件夹路径
        folder_path = kwargs.get("folder_path", [])
        if isinstance(folder_path, str):
            folder_path = [folder_path]

        # 生成标题
        if not title:
            title = self._extract_title_from_url(url)

        try:
            # 生成内容（书签摘要）
            content = self._generate_bookmark_content(
                title=title,
                url=url,
                folder_path=folder_path,
            )

            # 生成元数据
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source=url,
                tags=tags or [],
                folder_path=folder_path if folder_path else None,
                **{k: v for k, v in kwargs.items() if k != 'folder_path'},
            )

            # 生成安全的文件名
            filename = self._generate_safe_filename("bookmark", title)

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
        从浏览器收集书签

        自动定位浏览器书签文件并解析。

        Args:
            browser: 浏览器类型（chrome/edge/firefox/safari）
            max_concurrent: 最大并发数，默认使用初始化时的设置
            skip_existing: 是否跳过已收集的书签，默认 True
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表

        Raises:
            ValueError: 不支持的浏览器类型
            FileNotFoundError: 未找到浏览器书签文件
        """
        browser = browser.lower().strip()

        if browser not in self.SUPPORTED_BROWSERS:
            raise ValueError(
                f"不支持的浏览器类型: {browser}。"
                f"支持的类型: {', '.join(self.SUPPORTED_BROWSERS)}"
            )

        # 定位书签文件
        bookmark_file = self._locate_browser_bookmark(browser)

        if not bookmark_file or not bookmark_file.exists():
            raise FileNotFoundError(
                f"未找到 {browser} 浏览器的书签文件。"
                f"请确保已安装 {browser} 并导出过书签。"
            )

        # 解析书签
        bookmarks = self._parse_browser_bookmarks(browser, bookmark_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error=f"未在 {browser} 书签文件中找到任何书签",
                )
            ]

        # 并发收集书签
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
        从 HTML 导出文件导入书签

        Args:
            html_file: HTML 书签文件路径
            max_concurrent: 最大并发数，默认使用初始化时的设置
            skip_existing: 是否跳过已收集的书签，默认 True
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不正确
        """
        html_file = Path(html_file).resolve()

        if not html_file.exists():
            raise FileNotFoundError(f"HTML 文件不存在: {html_file}")

        # 解析 HTML 书签
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

        # 并发收集书签
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
        从 Chrome/Edge JSON 书签文件收集

        Args:
            json_file: Chrome JSON 书签文件路径
            max_concurrent: 最大并发数
            skip_existing: 是否跳过已收集的书签
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表
        """
        json_file = Path(json_file).resolve()

        if not json_file.exists():
            raise FileNotFoundError(f"JSON 文件不存在: {json_file}")

        # 解析 Chrome 书签
        parser = ChromeBookmarkParser()
        bookmarks = parser.parse_file(json_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error="未在 JSON 文件中找到任何书签",
                )
            ]

        # 并发收集书签
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
        从 Safari plist 书签文件收集

        Args:
            plist_file: Safari plist 书签文件路径
            max_concurrent: 最大并发数
            skip_existing: 是否跳过已收集的书签
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表
        """
        plist_file = Path(plist_file).resolve()

        if not plist_file.exists():
            raise FileNotFoundError(f"plist 文件不存在: {plist_file}")

        # 解析 Safari 书签
        parser = SafariBookmarkParser()
        bookmarks = parser.parse_file(plist_file)

        if not bookmarks:
            return [
                CollectResult(
                    success=False,
                    error="未在 plist 文件中找到任何书签",
                )
            ]

        # 并发收集书签
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
        并发收集书签列表

        Args:
            bookmarks: 书签列表
            max_concurrent: 最大并发数
            skip_existing: 是否跳过已收集的书签
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表
        """
        # 过滤已收集的书签
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

        # 使用异步并发处理
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                self._collect_bookmarks_async(new_bookmarks, max_concurrent, storage)
            )
        finally:
            loop.close()

        # 统计结果
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
        异步并发收集书签

        Args:
            bookmarks: 书签列表
            max_concurrent: 最大并发数
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            List[CollectResult]: 收集结果列表
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

        # 处理异常结果
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
                # 记录已收集的 URL（仅当没有 storage 时使用内存集合）
                if result.success and bookmarks[i].url and not storage:
                    self._collected_urls.add(bookmarks[i].url)

        return final_results

    async def _collect_single_with_retry(
        self,
        bookmark: BookmarkItem,
        storage=None,
    ) -> CollectResult:
        """
        收集单个书签（带重试机制）

        Args:
            bookmark: 书签项
            storage: SQLiteStorage 实例，用于重复检测（可选）

        Returns:
            CollectResult: 收集结果
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

            # 如果不是最后一次尝试，等待后重试
            if attempt < self._max_retries - 1:
                delay = self._retry_delay * (2 ** attempt)  # 指数退避
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
        生成书签的 Markdown 内容

        Args:
            title: 书签标题
            url: 书签 URL
            folder_path: 文件夹路径

        Returns:
            str: Markdown 格式的内容
        """
        lines = []

        # 标题
        lines.append(f"# {title}")
        lines.append("")

        # 原始链接
        lines.append(f"**原始链接:** {url}")
        lines.append("")

        # 文件夹路径
        if folder_path:
            folder_str = " / ".join(folder_path)
            lines.append(f"**分类路径:** {folder_str}")
            lines.append("")

        # 收集说明
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
        生成书签元数据

        Args:
            title: 文档标题
            content: 文档内容
            source: 原始 URL
            tags: 标签列表
            folder_path: 文件夹路径
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        # 生成唯一 ID
        timestamp = datetime.now()
        bookmark_id = f"bookmark_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 基础元数据
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

        # 添加文件夹路径
        if folder_path:
            metadata["folder_path"] = folder_path

        # 添加添加日期
        if "added_date" in kwargs and kwargs["added_date"]:
            metadata["added_date"] = kwargs["added_date"]

        # 合并额外的元数据（排除已经处理的字段）
        extra_kwargs = {k: v for k, v in kwargs.items() if k != "added_date"}
        metadata.update(extra_kwargs)

        return metadata

    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """
        从 URL 推断标题

        Args:
            url: 网页 URL

        Returns:
            str: 推断的标题
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)

            # 获取路径最后一段
            path = parsed.path.rstrip("/")
            if path:
                last_part = path.split("/")[-1]
                # 移除文件扩展名
                title = last_part.split(".")[0]
                # 将连字符和下划线替换为空格
                title = title.replace("-", " ").replace("_", " ")
                # 首字母大写
                return title.title() if title else parsed.netloc

            return parsed.netloc

        except Exception:
            return "Untitled Bookmark"

    def _locate_browser_bookmark(self, browser: str) -> Optional[Path]:
        """
        定位浏览器书签文件

        Args:
            browser: 浏览器类型

        Returns:
            Optional[Path]: 书签文件路径，未找到返回 None
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
            # Firefox 使用 HTML 导出，需要用户手动导出
            # 这里返回 None，提示用户手动指定文件
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
        解析浏览器书签文件

        Args:
            browser: 浏览器类型
            bookmark_file: 书签文件路径

        Returns:
            List[BookmarkItem]: 书签列表
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
        加载已收集的书签 URL（用于增量更新）

        从 output_dir/bookmarks/ 目录扫描已有的书签文件，
        提取其中的 source URL 并记录。
        """
        self._collected_urls.clear()

        bookmark_dir = self.output_dir / self._sub_dir
        if not bookmark_dir.exists():
            return

        # 扫描所有 .md 文件
        for md_file in bookmark_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # 提取 source 字段
                import re

                match = re.search(r"^source: (.+)$", content, re.MULTILINE)
                if match:
                    url = match.group(1).strip()
                    # 移除可能的引号
                    url = url.strip('"').strip("'")
                    if url:
                        self._collected_urls.add(url)
            except Exception:
                # 忽略读取失败的文件
                continue

        if self._collected_urls:
            print(f"已加载 {len(self._collected_urls)} 个已收集的书签 URL")

    def _extract_content(self, source: Any) -> str:
        """
        从数据源提取纯文本内容（实现 BaseCollector 抽象方法）

        Args:
            source: 数据源（书签 URL）

        Returns:
            str: 提取的纯文本内容
        """
        url = str(source)
        title = self._extract_title_from_url(url)
        return f"# {title}\n\n**链接:** {url}"

    def get_supported_browsers(self) -> List[str]:
        """
        获取支持的浏览器列表

        Returns:
            List[str]: 支持的浏览器名称列表
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
