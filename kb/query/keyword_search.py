"""
关键词搜索模块

基于关键词的文本匹配搜索功能，支持使用 ripgrep 或 glob + 文件内容匹配。
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.query.models import SearchResult

logger = logging.getLogger(__name__)


class KeywordSearch:
    """
    关键词搜索类

    提供基于关键词的文本匹配搜索功能。支持使用 ripgrep 进行快速搜索，
    或使用 glob + 文件内容匹配作为备选方案。

    使用示例：
        >>> from kb.query.keyword_search import KeywordSearch
        >>> search = KeywordSearch(data_dir="~/.knowledge-base")
        >>> results = search.search("Python 安装", content_type="files", limit=10)
        >>> for result in results:
        ...     print(f"File: {result.metadata.get('file_path')}")
        ...     print(f"Content: {result.content[:100]}...")
    """

    def __init__(
        self,
        data_dir: str,
        use_ripgrep: bool = True,
        limit: int = 10,
    ) -> None:
        """
        初始化关键词搜索器

        Args:
            data_dir: 数据目录路径，搜索将在此目录及其子目录中进行
            use_ripgrep: 是否使用 ripgrep 进行搜索，默认为 True
            limit: 默认返回结果数量限制，默认为 10

        Raises:
            ValueError: 数据目录不存在
        """
        self.data_dir = Path(os.path.expanduser(data_dir))

        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")

        if not self.data_dir.is_dir():
            raise ValueError(f"Data path is not a directory: {self.data_dir}")

        self.use_ripgrep = use_ripgrep and self._check_ripgrep_available()
        self.default_limit = limit

        logger.info(
            f"KeywordSearch initialized with data_dir={self.data_dir}, "
            f"use_ripgrep={self.use_ripgrep}, limit={limit}"
        )

    def _check_ripgrep_available(self) -> bool:
        """
        检查 ripgrep 是否可用

        Returns:
            bool: 如果 ripgrep 可用则返回 True
        """
        try:
            result = subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def search(
        self,
        keywords: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        执行关键词搜索

        在数据目录中搜索包含指定关键词的文件，返回匹配的文件路径和内容摘要。

        Args:
            keywords: 搜索关键词，支持多个关键词（空格分隔）
            content_type: 内容类型过滤，可选值：
                         - "files": 只搜索文件
                         - "urls": 只搜索网页内容
                         - "bookmarks": 只搜索书签
                         - "notes": 只搜索笔记
                         - None: 搜索所有类型
            limit: 返回结果数量限制，如果不提供则使用默认值

        Returns:
            List[SearchResult]: 搜索结果列表，每个结果包含文件路径和内容摘要

        Raises:
            ValueError: 关键词为空
            Exception: 搜索过程中发生错误
        """
        if not keywords or not keywords.strip():
            raise ValueError("Keywords cannot be empty")

        if limit is None:
            limit = self.default_limit

        try:
            # 确定搜索目录
            search_dir = self._get_search_directory(content_type)

            # 执行搜索
            if self.use_ripgrep:
                raw_results = self._search_with_ripgrep(keywords, search_dir, limit)
            else:
                raw_results = self._search_with_glob(keywords, search_dir, limit)

            # 转换为 SearchResult
            results = self._convert_to_search_results(raw_results)

            logger.info(
                f"Keyword search completed: {len(results)} results found "
                f"for '{keywords}'"
            )
            return results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            raise Exception(f"Keyword search failed: {e}")

    def _get_search_directory(self, content_type: Optional[str]) -> Path:
        """
        根据内容类型获取搜索目录

        Args:
            content_type: 内容类型

        Returns:
            Path: 搜索目录路径
        """
        if content_type is None:
            return self.data_dir

        type_mapping = {
            "files": "1_collect/files",
            "urls": "1_collect/urls",
            "bookmarks": "1_collect/bookmarks",
            "notes": "1_collect/notes",
            "papers": "1_collect/papers",
            "emails": "1_collect/emails",
        }

        relative_path = type_mapping.get(content_type)
        if relative_path:
            search_dir = self.data_dir / relative_path
            if search_dir.exists():
                return search_dir

        # 如果指定类型不存在，回退到整个数据目录
        return self.data_dir

    def _search_with_ripgrep(
        self, keywords: str, search_dir: Path, limit: int
    ) -> List[Dict[str, str]]:
        """
        使用 ripgrep 执行搜索

        Args:
            keywords: 搜索关键词
            search_dir: 搜索目录
            limit: 结果数量限制

        Returns:
            List[Dict[str, str]]: 原始搜索结果列表
        """
        try:
            # 构建 ripgrep 命令
            # --json: 输出 JSON 格式
            # --max-count: 每个文件最大匹配数
            # --no-heading: 不显示标题
            # --with-filename: 显示文件名
            cmd = [
                "rg",
                "--json",
                "--max-count",
                "3",  # 每个文件最多 3 个匹配
                "--no-heading",
                "--with-filename",
                "--ignore-case",
                "--glob",
                "!*.json",  # 忽略 JSON 元数据文件
                keywords,
                str(search_dir),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode not in [0, 1]:  # 0=找到匹配, 1=未找到匹配
                logger.warning(
                    f"ripgrep returned code {result.returncode}: {result.stderr}"
                )
                return []

            # 解析 JSON 输出
            matches = self._parse_ripgrep_output(result.stdout, limit)
            return matches

        except subprocess.TimeoutExpired:
            logger.warning("ripgrep search timed out")
            return []
        except Exception as e:
            logger.error(f"ripgrep search failed: {e}")
            return []

    def _parse_ripgrep_output(
        self, output: str, limit: int
    ) -> List[Dict[str, str]]:
        """
        解析 ripgrep JSON 输出

        Args:
            output: ripgrep 的 JSON 输出
            limit: 结果数量限制

        Returns:
            List[Dict[str, str]]: 解析后的搜索结果
        """
        results = []
        seen_files = set()

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            try:
                data = json.loads(line)

                # 只处理匹配行
                if data.get("type") != "match":
                    continue

                match_data = data.get("data", {})
                file_path = match_data.get("path", {}).get("text", "")
                text = match_data.get("lines", {}).get("text", "")

                # 去重
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)

                results.append(
                    {
                        "file_path": file_path,
                        "content": text.strip(),
                    }
                )

                if len(results) >= limit:
                    break

            except json.JSONDecodeError:
                continue

        return results

    def _search_with_glob(
        self, keywords: str, search_dir: Path, limit: int
    ) -> List[Dict[str, str]]:
        """
        使用 glob + 文件内容匹配执行搜索（备选方案）

        Args:
            keywords: 搜索关键词
            search_dir: 搜索目录
            limit: 结果数量限制

        Returns:
            List[Dict[str, str]]: 原始搜索结果列表
        """
        results = []
        seen_files = set()

        # 将关键词分割为列表
        keyword_list = keywords.lower().split()

        try:
            # 递归搜索所有文本文件
            for file_path in search_dir.rglob("*"):
                if len(results) >= limit:
                    break

                # 只处理文本文件
                if not file_path.is_file():
                    continue

                # 跳过二进制文件和元数据文件
                if file_path.suffix in [".json", ".db", ".lock"]:
                    continue

                if file_path.name.startswith("."):
                    continue

                try:
                    # 读取文件内容
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    # 检查是否包含所有关键词
                    content_lower = content.lower()
                    if all(kw in content_lower for kw in keyword_list):
                        if str(file_path) not in seen_files:
                            seen_files.add(str(file_path))

                            # 提取包含关键词的上下文
                            context = self._extract_context(content, keyword_list)

                            results.append(
                                {
                                    "file_path": str(file_path),
                                    "content": context,
                                }
                            )

                except (PermissionError, UnicodeDecodeError) as e:
                    logger.debug(f"Skipping file {file_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Glob search failed: {e}")

        return results

    def _extract_context(self, content: str, keywords: List[str], context_lines: int = 2) -> str:
        """
        从文件内容中提取包含关键词的上下文

        Args:
            content: 文件完整内容
            keywords: 关键词列表
            context_lines: 上下文行数

        Returns:
            str: 包含关键词的上下文文本
        """
        lines = content.split("\n")
        context_parts = []

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # 检查是否包含任意关键词
            if any(kw in line_lower for kw in keywords):
                # 获取上下文
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)

                context = "\n".join(lines[start:end])
                context_parts.append(context)

                # 只返回前 3 个匹配上下文
                if len(context_parts) >= 3:
                    break

        if context_parts:
            return "\n...\n".join(context_parts)

        # 如果没有找到具体上下文，返回开头部分
        return content[:500] + "..." if len(content) > 500 else content

    def _convert_to_search_results(
        self, raw_results: List[Dict[str, str]]
    ) -> List[SearchResult]:
        """
        将原始搜索结果转换为 SearchResult 列表

        Args:
            raw_results: 原始搜索结果列表

        Returns:
            List[SearchResult]: 转换后的搜索结果列表
        """
        results = []

        for i, raw in enumerate(raw_results):
            file_path = raw.get("file_path", "")
            content = raw.get("content", "")

            # 创建相对路径作为 ID
            try:
                rel_path = Path(file_path).relative_to(self.data_dir)
                doc_id = str(rel_path)
            except ValueError:
                doc_id = file_path

            metadata = {
                "file_path": file_path,
                "content_type": self._detect_content_type(file_path),
            }

            result = SearchResult(
                id=doc_id,
                content=content,
                metadata=metadata,
                score=1.0 - (i * 0.1),  # 简单评分：越靠前分数越高
            )
            results.append(result)

        return results

    def _detect_content_type(self, file_path: str) -> str:
        """
        根据文件路径检测内容类型

        Args:
            file_path: 文件路径

        Returns:
            str: 内容类型
        """
        path_lower = file_path.lower()

        if "/files/" in path_lower or "\\files\\" in path_lower:
            return "files"
        elif "/urls/" in path_lower or "\\urls\\" in path_lower:
            return "urls"
        elif "/bookmarks/" in path_lower or "\\bookmarks\\" in path_lower:
            return "bookmarks"
        elif "/notes/" in path_lower or "\\notes\\" in path_lower:
            return "notes"
        elif "/papers/" in path_lower or "\\papers\\" in path_lower:
            return "papers"
        elif "/emails/" in path_lower or "\\emails\\" in path_lower:
            return "emails"
        else:
            return "unknown"
