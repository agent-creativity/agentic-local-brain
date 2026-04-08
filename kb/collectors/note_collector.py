"""
笔记收集器模块

提供快速笔记收集功能，支持：
- 快速记录想法和灵感
- 自动生成标题和唯一 ID
- 添加标签分类
- 保存为带 YAML Front Matter 的 Markdown 文件
"""

import random
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.collectors.base import BaseCollector, CollectResult


class NoteCollector(BaseCollector):
    """
    笔记收集器

    用于快速收集用户的笔记、想法和灵感。笔记会被保存为 Markdown 文件，
    包含 YAML Front Matter 元数据。

    特性：
    - 自动生成标题（基于内容前 20 个字符）
    - 生成唯一的笔记 ID（格式：note_YYYYMMDD_HHMMSS_XXX）
    - 支持自定义标签
    - 保存到 1_collect/notes/ 目录

    使用示例：
        >>> collector = NoteCollector()
        >>> result = collector.collect(
        ...     text="考虑使用混合检索(向量 + BM25)来提高召回率",
        ...     title="RAG 优化思路",
        ...     tags=["RAG", "想法"]
        ... )
        >>> print(result.success)
        True
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化笔记收集器

        Args:
            config: 配置字典，可选。支持以下配置项：
                - output_dir: 输出目录路径，默认为 ~/.knowledge-base/1_collect/
                - auto_title_length: 自动生成标题时使用的字符数（默认 20）
        """
        # 从配置中获取输出目录
        output_dir = None
        if config and "output_dir" in config:
            output_dir = Path(config["output_dir"])

        super().__init__(output_dir)
        self._sub_dir = "notes"
        self._auto_title_length = (
            config.get("auto_title_length", 20) if config else 20
        )

    def collect(
        self,
        text: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any
    ) -> CollectResult:
        """
        收集笔记

        Args:
            text: 笔记内容
            title: 笔记标题（可选，如果未提供则自动生成）
            tags: 标签列表（可选）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果

        Raises:
            ValueError: 当笔记内容为空时
        """
        # 验证内容
        if not text or not text.strip():
            return CollectResult(
                success=False,
                error="笔记内容不能为空"
            )

        # Clean content for hash check
        content = text.strip()

        # Duplicate check by content hash (before any heavy processing)
        if skip_existing and storage:
            content_hash = self._generate_content_hash(content)
            existing = storage.hash_exists(content_hash, content_type="note")
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        try:
            # 如果没有提供标题，自动生成
            if not title:
                title = self._generate_title(content)

            # 生成唯一 ID
            note_id = self._generate_note_id()

            # 生成元数据
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source="manual_input",
                note_id=note_id,
                tags=tags or [],
                **kwargs
            )

            # 生成文件名
            filename = self._generate_filename(note_id, title)

            # 保存到文件
            saved_path = self._save_to_file(
                content=content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir
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
                content_hash=content_hash
            )

        except Exception as e:
            return CollectResult(
                success=False,
                error=f"笔记保存失败: {str(e)}"
            )

    def _extract_content(self, source: Any) -> str:
        """
        从数据源提取纯文本内容

        对于笔记收集器，source 就是文本内容本身。

        Args:
            source: 文本内容

        Returns:
            str: 提取的纯文本内容
        """
        if isinstance(source, str):
            return source.strip()
        return str(source).strip()

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: str,
        note_id: str,
        tags: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        生成笔记元数据

        Args:
            title: 笔记标题
            content: 笔记内容
            source: 来源标识
            note_id: 笔记唯一 ID
            tags: 标签列表
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        timestamp = datetime.now()

        metadata = {
            "id": note_id,
            "title": title,
            "content_type": "note",
            "collected_at": timestamp,
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
        }

        # 合并额外的元数据
        metadata.update(kwargs)

        return metadata

    def _generate_title(self, content: str) -> str:
        """
        根据内容自动生成标题

        使用内容的前 N 个字符作为标题（N 由 auto_title_length 配置）。
        如果内容不足 N 个字符，则使用全部内容。

        Args:
            content: 笔记内容

        Returns:
            str: 生成的标题
        """
        # 获取前 N 个字符
        title = content[:self._auto_title_length].strip()

        # 如果标题以标点符号结尾，移除它
        while title and title[-1] in "，。！？,.!?;；：":
            title = title[:-1]

        # 如果内容为空（理论上不应该发生），返回默认标题
        if not title:
            title = "未命名笔记"

        return title

    def _generate_note_id(self) -> str:
        """
        生成唯一的笔记 ID

        格式：note_YYYYMMDD_HHMMSS_XXX
        其中 XXX 是 3 位随机数字，用于避免同一秒内生成多个笔记时的冲突。

        Returns:
            str: 唯一的笔记 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 生成 3 位随机数字
        suffix = "".join(random.choices(string.digits, k=3))
        return f"note_{timestamp}_{suffix}"

    def _generate_filename(self, note_id: str, title: str) -> str:
        """
        生成笔记文件名

        使用笔记 ID 和标题的 slug 组合作为文件名。

        Args:
            note_id: 笔记唯一 ID
            title: 笔记标题

        Returns:
            str: 文件名（.md 后缀）
        """
        import re
        import unicodedata

        # 将标题转换为 slug
        slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        slug = slug.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        slug = slug[:50]  # 限制长度

        if slug:
            return f"{note_id}_{slug}.md"
        else:
            return f"{note_id}.md"
