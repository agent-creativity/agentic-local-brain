"""
网页收集器模块

使用 httpx 抓取网页内容，通过 Readability 提取正文，
转换为 Markdown 格式并保存到知识库。

支持功能：
- 异步网页抓取
- Readability 正文提取
- HTML 到 Markdown 转换
- LLM 自动标签提取（可选）
- 自定义 User-Agent
- 完善的错误处理
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
    网页收集器

    从 URL 抓取网页内容，提取正文并转换为 Markdown 格式。

    处理流程：
    1. 使用 httpx 抓取网页 HTML
    2. 使用 Readability 提取正文内容
    3. 使用 markdownify 转换为 Markdown
    4. 生成元数据（标题、标签等）
    5. 保存到 ~/.knowledge-base/1_collect/webpages/ 目录

    依赖库：
    - httpx: 异步 HTTP 客户端
    - readability-lxml: Mozilla Readability 的 Python 实现
    - markdownify: HTML 到 Markdown 转换
    - beautifulsoup4: HTML 解析支持

    示例：
        >>> collector = WebpageCollector()
        >>> result = collector.collect("https://example.com/article")
        >>> if result.success:
        ...     print(f"成功: {result.title}")
    """

    # 默认配置
    DEFAULT_TIMEOUT = 30  # 秒
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
        初始化网页收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
            timeout: HTTP 请求超时时间（秒），默认 30 秒
            user_agent: 自定义 User-Agent 字符串
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
        收集网页内容

        执行完整的网页收集流程：
        1. 验证 URL 格式
        2. 抓取网页 HTML
        3. 提取正文内容
        4. 转换为 Markdown
        5. 生成元数据并保存

        Args:
            source: 网页 URL
            tags: 用户提供的标签列表（可选）
            title: 自定义标题（可选，默认使用网页标题）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果

        Raises:
            ValueError: URL 格式无效
        """
        url = source.strip()

        # 验证 URL 格式
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
            # 抓取 HTML
            html = self._fetch_html(url)

            # 提取正文内容
            content_html, extracted_title = self._extract_content(html)

            # HTML 转 Markdown
            markdown_content = self._html_to_markdown(content_html)

            # 如果没有提供标题，使用提取的标题
            if not title:
                title = extracted_title or self._generate_title_from_content(markdown_content) or self._extract_title_from_url(url)

            # 生成元数据
            metadata = self._generate_metadata(
                title=title,
                content=markdown_content,
                source=url,
                tags=tags or [],
                **kwargs
            )

            # 生成安全的文件名
            filename = self._generate_safe_filename("webpage", title)

            # 保存到文件
            saved_path = self._save_to_file(
                content=markdown_content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir
            )

            # 统计字数
            word_count = self._count_words(markdown_content)

            # 生成内容哈希
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
        抓取网页 HTML 内容

        使用 httpx 同步客户端发起 GET 请求，
        携带自定义 User-Agent 和超时设置。

        Args:
            url: 目标网页 URL

        Returns:
            str: 网页 HTML 内容

        Raises:
            httpx.TimeoutException: 请求超时
            httpx.HTTPStatusError: HTTP 错误状态码
            httpx.RequestError: 网络请求失败
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

            # 检测编码（必须在访问 response.text 之前设置）
            charset = response.charset_encoding
            if charset:
                # Sanitize: some servers return malformed charset like "utf-8, text/html"
                charset = charset.split(",")[0].split(";")[0].strip()
                response.encoding = charset
            else:
                # 尝试从 HTML meta 标签检测编码
                # 使用 response.content 而不是 response.text 来避免 encoding 设置问题
                encoding = self._detect_encoding(response.content.decode("utf-8", errors="ignore"))
                response.encoding = encoding

            return response.text

    def _extract_content(self, html: str) -> tuple[str, str]:
        """
        使用 Readability 提取网页正文内容

        Readability 会移除导航栏、广告、侧边栏等无关内容，
        只保留主要正文部分。

        Args:
            html: 网页 HTML 内容

        Returns:
            tuple[str, str]: (正文 HTML, 网页标题)

        Raises:
            RuntimeError: 内容提取失败
        """
        try:
            doc = Document(html)

            # 提取正文 HTML
            content_html = doc.summary()

            # 提取标题
            title = doc.short_title()

            if not content_html or not content_html.strip():
                raise RuntimeError("无法提取网页正文内容，可能是动态加载的页面")

            return content_html, title

        except Exception as e:
            raise RuntimeError(f"Readability 内容提取失败: {str(e)}")

    def _html_to_markdown(self, html: str) -> str:
        """
        将 HTML 内容转换为 Markdown 格式

        使用 markdownify 库进行转换，
        保留标题、段落、列表、链接、图片等常见元素。

        Args:
            html: HTML 内容

        Returns:
            str: Markdown 格式的内容
        """
        try:
            from markdownify import markdownify as md

            # 转换 HTML 到 Markdown
            markdown = md(
                html,
                heading_style="ATX",  # 使用 # 风格的标题
                bullets="-",  # 使用 - 作为列表符号
                strip=["script", "style", "nav", "footer", "header"],
            )

            # 清理多余的空白行
            markdown = re.sub(r"\n{3,}", "\n\n", markdown)

            return markdown.strip()

        except ImportError:
            raise ImportError(
                "markdownify 未安装。请运行: pip install markdownify"
            )
        except Exception as e:
            # 如果转换失败，返回清理后的纯文本
            return self._html_to_text(html)

    def _extract_title(self, html: str) -> str:
        """
        从 HTML 中提取网页标题

        优先从 <title> 标签提取，
        如果没有则从 Open Graph 或 HTML 内容推断。

        Args:
            html: 网页 HTML 内容

        Returns:
            str: 网页标题
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # 尝试从 <title> 标签获取
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                return title_tag.string.strip()

            # 尝试从 Open Graph 获取
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                return og_title["content"].strip()

            # 尝试从 h1 标签获取
            h1_tag = soup.find("h1")
            if h1_tag and h1_tag.get_text():
                return h1_tag.get_text().strip()

            return ""

        except ImportError:
            # 如果没有 beautifulsoup4，使用正则表达式
            return self._extract_title_regex(html)
        except Exception:
            return ""

    @staticmethod
    def _generate_title_from_content(content: str, max_length: int = 50) -> str:
        """
        从正文内容生成标题

        取正文前 N 个字符作为标题，在句号、换行或逗号处截断。

        Args:
            content: Markdown 正文内容
            max_length: 标题最大长度

        Returns:
            str: 生成的标题，如果内容为空返回空字符串
        """
        if not content or not content.strip():
            return ""

        # 移除 markdown 标记，取纯文本
        text = re.sub(r"[#*`\[\]()>]", "", content).strip()
        if not text:
            return ""

        # 取前 max_length 个字符
        title = text[:max_length].strip()

        # 尝试在自然断句处截断（句号、换行、问号、感叹号）
        for sep in ["\n", "。", ".", "！", "!", "？", "?"]:
            idx = title.find(sep)
            if 0 < idx < len(title):
                title = title[:idx]
                break

        # 清理尾部标点
        while title and title[-1] in "，,；;：:、 ":
            title = title[:-1]

        return title.strip()

    def _extract_title_from_url(self, url: str) -> str:
        """
        从 URL 路径推断标题

        当无法从网页提取标题时，使用 URL 的最后一段作为标题。

        Args:
            url: 网页 URL

        Returns:
            str: 推断的标题
        """
        # 移除查询参数和片段
        url_path = url.split("?")[0].split("#")[0]

        # 获取最后一段路径
        parts = url_path.rstrip("/").split("/")
        if parts:
            last_part = parts[-1]
            # 移除文件扩展名
            title = last_part.split(".")[0]
            # 将连字符和下划线替换为空格
            title = title.replace("-", " ").replace("_", " ")
            # 首字母大写
            return title.title()

        return "Untitled Page"

    def _save_to_markdown(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> Path:
        """
        保存内容为 Markdown 文件（带 YAML Front Matter）

        Args:
            content: Markdown 正文内容
            metadata: YAML Front Matter 元数据
            filename: 文件名

        Returns:
            Path: 保存的文件路径
        """
        # 创建子目录
        target_dir = self.output_dir / self._sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # 生成完整的 Markdown 内容
        yaml_header = self._format_yaml(metadata)
        full_content = f"---\n{yaml_header}---\n\n{content}"

        # 写入文件
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
        生成网页元数据

        Args:
            title: 文档标题
            content: 文档内容
            source: 原始 URL
            tags: 标签列表
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        # 生成唯一 ID
        timestamp = datetime.now()
        page_id = f"webpage_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 基础元数据
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

        # 合并额外的元数据
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """
        验证 URL 格式是否有效

        Args:
            url: 待验证的 URL

        Returns:
            bool: URL 是否有效
        """
        # 简单的 URL 格式验证
        pattern = r"^https?://"
        return bool(re.match(pattern, url, re.IGNORECASE))

    @staticmethod
    def _detect_encoding(html: str) -> str:
        """
        从 HTML 内容检测字符编码

        尝试从 meta 标签中提取 charset 信息。

        Args:
            html: HTML 内容

        Returns:
            str: 检测到的编码，默认 utf-8
        """
        # 尝试匹配 <meta charset="...">
        match = re.search(r'<meta\s+charset=["\']?([^"\'>\s]+)', html, re.IGNORECASE)
        if match:
            return match.group(1)

        # 尝试匹配 <meta http-equiv="Content-Type" content="...; charset=...">
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
        使用正则表达式从 HTML 提取标题

        Args:
            html: HTML 内容

        Returns:
            str: 网页标题
        """
        # 匹配 <title> 标签
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # 移除可能的 HTML 实体
            title = re.sub(r"&[^;]+;", "", title)
            return title

        return ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        将 HTML 转换为纯文本（降级方案）

        当 markdownify 不可用时的备用方案。

        Args:
            html: HTML 内容

        Returns:
            str: 纯文本内容
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 获取文本
            text = soup.get_text(separator="\n", strip=True)

            # 清理空白行
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text

        except ImportError:
            # 最简单的降级方案：移除 HTML 标签
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
        批量收集网页（异步）

        使用异步并发抓取多个网页，提高效率。

        Args:
            urls: URL 列表
            tags: 通用标签列表（可选）
            max_concurrent: 最大并发数，默认 3

        Returns:
            List[CollectResult]: 收集结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        async def collect_with_semaphore(url: str) -> CollectResult:
            async with semaphore:
                # 在事件循环中运行同步方法
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.collect, url, tags
                )

        for url in urls:
            task = collect_with_semaphore(url)
            tasks.append(task)

        return await asyncio.gather(*tasks)
