"""
学术论文收集器模块

支持从 arXiv 收集学术论文，提取元数据和摘要并保存到知识库。
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from kb.collectors.base import BaseCollector, CollectResult


class PaperCollector(BaseCollector):
    """
    学术论文收集器

    支持从 arXiv 收集学术论文：
    - 解析 arXiv ID（支持多种格式）
    - 通过 arXiv API 获取论文元数据
    - 提取标题、作者、摘要、分类等信息
    - 保存为带 YAML Front Matter 的 Markdown 文件

    处理流程：
    1. 解析 arXiv ID
    2. 调用 arXiv API 获取论文信息
    3. 解析 XML 响应
    4. 生成 YAML Front Matter 元数据
    5. 保存到 ~/.knowledge-base/1_collect/papers/ 目录
    6. 返回收集结果

    示例：
        >>> collector = PaperCollector()
        >>> result = collector.collect("arxiv:2301.12345")
        >>> if result.success:
        ...     print(f"成功: {result.title}")
    """

    # arXiv API 配置
    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    DEFAULT_TIMEOUT = 30

    # arXiv ID 格式正则
    # 支持格式: arxiv:2301.12345, 2301.12345, https://arxiv.org/abs/2301.12345
    ARXIV_ID_PATTERNS = [
        r"arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)",  # arxiv:2301.12345
        r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",  # 2301.12345
        r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)",  # URL format
        r"arxiv\.org/pdf/(\d{4}\.\d{4,5}(?:v\d+)?)",  # PDF URL format
        # Old arXiv format: cond-mat/0001234
        r"arxiv:([a-z-]+/\d{7}(?:v\d+)?)",
        r"^([a-z-]+/\d{7}(?:v\d+)?)$",
        r"arxiv\.org/abs/([a-z-]+/\d{7}(?:v\d+)?)",
    ]

    # XML namespaces
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        初始化论文收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
            timeout: HTTP 请求超时时间（秒），默认 30 秒
        """
        super().__init__(output_dir)
        self._sub_dir = "papers"
        self._timeout = timeout or self.DEFAULT_TIMEOUT

    def collect(
        self,
        source: str,
        tags: Optional[List[str]] = None,
        download_pdf: bool = False,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any,
    ) -> CollectResult:
        """
        收集 arXiv 论文

        Args:
            source: arXiv ID 或 URL（支持格式: arxiv:2301.12345, 2301.12345, 或 arXiv URL）
            tags: 用户提供的标签列表（可选）
            download_pdf: 是否下载 PDF（默认 False，暂不实现）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果
        """
        # 解析 arXiv ID
        arxiv_id = self._parse_arxiv_id(source)
        if not arxiv_id:
            return CollectResult(
                success=False, error=f"Invalid arXiv ID format: {source}"
            )

        # Normalize source for dedup
        source_key = f"arxiv:{arxiv_id}"

        # Duplicate check (before any heavy processing)
        if skip_existing and storage:
            existing = self._check_duplicate(source=source_key, storage=storage)
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        try:
            # 从 arXiv API 获取论文信息
            paper_info = self._fetch_paper_info(arxiv_id)
            if not paper_info:
                return CollectResult(
                    success=False, error=f"Paper not found: {arxiv_id}"
                )

            # 提取内容
            content = self._extract_content(paper_info)

            # Use CLI-provided title if available, otherwise use paper title
            final_title = kwargs.pop("title", None) or paper_info["title"]

            # 生成元数据
            metadata = self._generate_metadata(
                title=final_title,
                content=content,
                source=f"arxiv:{arxiv_id}",
                tags=tags or [],
                paper_info=paper_info,
                **kwargs,
            )

            # 生成安全的文件名
            filename = self._generate_safe_filename("paper", final_title)

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
                title=final_title,
                word_count=word_count,
                tags=tags or [],
                metadata=metadata,
                content_hash=content_hash,
            )

        except httpx.TimeoutException:
            return CollectResult(
                success=False, error=f"Request timeout ({self._timeout}s): {arxiv_id}"
            )
        except httpx.RequestError as e:
            return CollectResult(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            return CollectResult(success=False, error=f"Failed to collect paper: {str(e)}")

    def _parse_arxiv_id(self, source: str) -> Optional[str]:
        """
        解析 arXiv ID

        支持多种格式：
        - arxiv:2301.12345
        - 2301.12345
        - https://arxiv.org/abs/2301.12345
        - https://arxiv.org/pdf/2301.12345.pdf

        Args:
            source: 原始输入字符串

        Returns:
            Optional[str]: 解析出的 arXiv ID，解析失败返回 None
        """
        source = source.strip()

        for pattern in self.ARXIV_ID_PATTERNS:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _fetch_paper_info(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        从 arXiv API 获取论文信息

        Args:
            arxiv_id: arXiv ID

        Returns:
            Optional[Dict[str, Any]]: 论文信息字典，失败返回 None
        """
        url = f"{self.ARXIV_API_URL}?id_list={arxiv_id}"

        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            return self._parse_arxiv_response(response.text, arxiv_id)

    def _parse_arxiv_response(
        self, xml_content: str, arxiv_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        解析 arXiv API XML 响应

        Args:
            xml_content: XML 响应内容
            arxiv_id: arXiv ID

        Returns:
            Optional[Dict[str, Any]]: 解析的论文信息
        """
        try:
            root = ET.fromstring(xml_content)

            # 查找 entry 元素
            entry = root.find("atom:entry", self.ATOM_NS)
            if entry is None:
                return None

            # 检查是否有错误（论文不存在的情况）
            title_elem = entry.find("atom:title", self.ATOM_NS)
            if title_elem is None:
                return None

            title = self._clean_text(title_elem.text or "")
            if not title or title.lower() == "error":
                return None

            # 提取作者
            authors = []
            for author_elem in entry.findall("atom:author", self.ATOM_NS):
                name_elem = author_elem.find("atom:name", self.ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            # 提取摘要
            summary_elem = entry.find("atom:summary", self.ATOM_NS)
            abstract = self._clean_text(summary_elem.text or "") if summary_elem is not None else ""

            # 提取分类
            categories = []
            for category_elem in entry.findall("atom:category", self.ATOM_NS):
                term = category_elem.get("term")
                if term:
                    categories.append(term)

            # 提取发布日期
            published_elem = entry.find("atom:published", self.ATOM_NS)
            published_date = ""
            if published_elem is not None and published_elem.text:
                # 格式: 2023-01-15T12:00:00Z
                published_date = published_elem.text[:10]  # 只取日期部分

            # 提取链接
            pdf_url = ""
            arxiv_url = ""
            for link_elem in entry.findall("atom:link", self.ATOM_NS):
                link_type = link_elem.get("type", "")
                link_href = link_elem.get("href", "")
                if link_type == "application/pdf":
                    pdf_url = link_href
                elif link_type == "text/html":
                    arxiv_url = link_href

            # 如果没有找到 HTML 链接，构造默认链接
            if not arxiv_url:
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
            if not pdf_url:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "categories": categories,
                "published_date": published_date,
                "arxiv_id": arxiv_id,
                "pdf_url": pdf_url,
                "arxiv_url": arxiv_url,
            }

        except ET.ParseError:
            return None

    def _extract_content(self, paper_info: Dict[str, Any]) -> str:
        """
        从论文信息生成 Markdown 内容

        Args:
            paper_info: 论文信息字典

        Returns:
            str: Markdown 格式的内容
        """
        lines = []

        # 标题
        lines.append(f"# {paper_info['title']}")
        lines.append("")

        # 作者
        if paper_info["authors"]:
            lines.append("## Authors")
            lines.append(", ".join(paper_info["authors"]))
            lines.append("")

        # 摘要
        if paper_info["abstract"]:
            lines.append("## Abstract")
            lines.append(paper_info["abstract"])
            lines.append("")

        # 分类
        if paper_info["categories"]:
            lines.append("## Categories")
            lines.append(", ".join(paper_info["categories"]))
            lines.append("")

        # 链接
        lines.append("## Links")
        lines.append(f"- [PDF]({paper_info['pdf_url']})")
        lines.append(f"- [arXiv]({paper_info['arxiv_url']})")

        return "\n".join(lines)

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: str,
        tags: Optional[List[str]] = None,
        paper_info: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成论文元数据

        Args:
            title: 论文标题
            content: 文档内容
            source: 原始数据源
            tags: 标签列表
            paper_info: 论文信息字典
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        paper_info = paper_info or {}

        # 生成唯一 ID
        arxiv_id = paper_info.get("arxiv_id", "unknown")
        # 将 / 替换为 _ 以处理旧格式 ID
        safe_arxiv_id = arxiv_id.replace("/", "_")
        paper_id = f"paper_{safe_arxiv_id}"

        timestamp = datetime.now()

        # 基础元数据
        metadata = {
            "id": paper_id,
            "title": title,
            "source": source,
            "content_type": "paper",
            "collected_at": timestamp,
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
            "authors": paper_info.get("authors", []),
            "arxiv_id": arxiv_id,
            "categories": paper_info.get("categories", []),
            "published_date": paper_info.get("published_date", ""),
            "pdf_url": paper_info.get("pdf_url", ""),
        }

        # 合并额外的元数据
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        清理文本（移除多余空白）

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 移除换行符和多余空白
        text = re.sub(r"\s+", " ", text)
        return text.strip()
