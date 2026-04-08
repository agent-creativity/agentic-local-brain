"""
收集器基类模块

定义所有收集器的抽象基类，提供统一的接口和数据模型。
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CollectResult:
    """
    收集结果数据类

    Attributes:
        success: 是否收集成功
        file_path: 保存的文件路径
        title: 文档标题
        word_count: 字数统计
        tags: 提取的标签列表
        metadata: 额外的元数据信息
        error: 错误信息（如果失败）
        content_hash: 内容哈希值（用于重复检测）
        summary: 文档摘要
    """

    success: bool
    file_path: Optional[Path] = None
    title: Optional[str] = None
    word_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    content_hash: Optional[str] = None  # SHA-256 hash of content for duplicate detection
    summary: Optional[str] = None  # Document summary

    def __repr__(self) -> str:
        if self.success:
            return (
                f"CollectResult(success=True, file={self.file_path}, "
                f"title={self.title}, words={self.word_count})"
            )
        return f"CollectResult(success=False, error={self.error})"


class BaseCollector(ABC):
    """
    收集器抽象基类

    所有具体的收集器（文件、网页、书签等）都应继承此类，
    实现统一的收集接口。

    子类需要实现的方法：
        - collect: 执行收集操作
        - _extract_content: 提取纯文本内容
        - _generate_metadata: 生成元数据
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        初始化收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
        """
        self.output_dir = output_dir or (Path.home() / ".knowledge-base" / "1_collect")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def collect(self, source: Any, **kwargs: Any) -> CollectResult:
        """
        执行收集操作

        Args:
            source: 数据源（文件路径、URL 等）
            **kwargs: 额外的参数（如 tags, title 等）

        Returns:
            CollectResult: 收集结果
        """
        pass

    @abstractmethod
    def _extract_content(self, source: Any) -> str:
        """
        从数据源提取纯文本内容

        Args:
            source: 数据源

        Returns:
            str: 提取的纯文本内容
        """
        pass

    @abstractmethod
    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        生成文档元数据

        Args:
            title: 文档标题
            content: 文档内容
            source: 原始数据源
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        pass

    def _save_to_file(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
        sub_dir: str
    ) -> Path:
        """
        保存内容到 Markdown 文件（带 YAML Front Matter）

        Args:
            content: 文档正文内容
            metadata: YAML Front Matter 元数据
            filename: 文件名
            sub_dir: 子目录名称（如 files, urls 等）

        Returns:
            Path: 保存的文件路径
        """
        # 创建子目录
        target_dir = self.output_dir / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # 生成完整的 Markdown 内容
        yaml_header = self._format_yaml(metadata)
        full_content = f"---\n{yaml_header}---\n\n{content}"

        # 写入文件
        file_path = target_dir / filename
        file_path.write_text(full_content, encoding="utf-8")

        return file_path

    @staticmethod
    def _format_yaml(metadata: Dict[str, Any]) -> str:
        """
        将元数据字典格式化为 YAML 字符串

        Args:
            metadata: 元数据字典

        Returns:
            str: YAML 格式的字符串
        """
        lines = []
        for key, value in metadata.items():
            if isinstance(value, list):
                # 列表类型：使用 YAML 列表格式
                if value:
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"{key}: []")
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            elif isinstance(value, datetime):
                lines.append(f"{key}: {value.isoformat()}")
            elif value is None:
                lines.append(f"{key}: null")
            else:
                # 字符串类型：如果有特殊字符，添加引号
                str_value = str(value)
                if any(c in str_value for c in [':', '#', '{', '}', '[', ']', ',']):
                    lines.append(f'{key}: "{str_value}"')
                else:
                    lines.append(f"{key}: {str_value}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _generate_safe_filename(prefix: str, title: Optional[str] = None) -> str:
        """
        生成安全的文件名（使用日期 + slug）

        Args:
            prefix: 文件类型前缀（如 file, url 等）
            title: 文档标题（可选）

        Returns:
            str: 安全的文件名（.md 后缀）
        """
        import re
        import unicodedata

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        if title:
            # 检查是否包含 CJK 字符
            has_cjk = any("\u4e00" <= c <= "\u9fff" for c in title)
            if has_cjk:
                try:
                    from pypinyin import lazy_pinyin
                    slug = "-".join(lazy_pinyin(title))
                except ImportError:
                    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
            else:
                slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
            # 转换为小写
            slug = slug.lower()
            # 替换非字母数字字符为连字符
            slug = re.sub(r"[^a-z0-9]+", "-", slug)
            # 移除首尾连字符
            slug = slug.strip("-")
            # 限制长度
            slug = slug[:50]
            return f"{timestamp}_{slug}.md"
        else:
            return f"{timestamp}_{prefix}.md"

    @staticmethod
    def _count_words(content: str) -> int:
        """
        统计文本字数

        Args:
            content: 文本内容

        Returns:
            int: 字数（中文字符按 1 个计，英文单词按空格分隔）
        """
        # 简单统计：中文字符 + 英文单词
        chinese_chars = sum(1 for char in content if "\u4e00" <= char <= "\u9fff")
        # 移除中文字符后统计英文单词
        english_text = "".join(
            " " if "\u4e00" <= char <= "\u9fff" else char for char in content
        )
        english_words = len(english_text.split())
        return chinese_chars + english_words

    @staticmethod
    def _generate_content_hash(content: str) -> str:
        """Generate SHA-256 hash of content for duplicate detection.

        Args:
            content: Text content to hash.

        Returns:
            Hex-encoded SHA-256 hash string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _check_duplicate(self, source: str, content: str = None,
                         storage=None) -> Optional[Dict]:
        """Check for duplicate by source, then by content hash.

        Args:
            source: Source identifier (URL, file path, etc.)
            content: Optional text content for hash-based dedup.
            storage: SQLiteStorage instance. If None, skip dedup check.

        Returns:
            Dict with existing record info if duplicate found, None otherwise.
        """
        if storage is None:
            return None

        # Check by source first (exact match)
        content_type = getattr(self, '_content_type', None)
        existing = storage.source_exists(source, content_type)
        if existing:
            return existing

        # Check by content hash if content provided
        if content:
            content_hash = self._generate_content_hash(content)
            existing = storage.hash_exists(content_hash, content_type)
            if existing:
                return existing

        return None
