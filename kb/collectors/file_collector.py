from __future__ import annotations

"""
文件收集器模块

支持解析 PDF、Markdown、TXT 文件，提取内容并保存到知识库。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.collectors.base import BaseCollector, CollectResult

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


class FileCollector(BaseCollector):
    """
    文件收集器

    支持解析以下格式的文件：
    - PDF: 使用 PyPDF2 提取文本
    - Markdown (.md): 直接读取
    - TXT (.txt): 直接读取

    处理流程：
    1. 检测文件类型
    2. 提取纯文本内容
    3. 生成 YAML Front Matter 元数据
    4. 保存到 ~/.knowledge-base/1_collect/files/ 目录
    5. 返回收集结果
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        初始化文件收集器

        Args:
            output_dir: 输出目录，默认为 ~/.knowledge-base/1_collect/
        """
        super().__init__(output_dir)
        self._sub_dir = "files"

    def collect(
        self,
        source: str | Path,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        skip_existing: bool = False,
        storage=None,
        **kwargs: Any
    ) -> CollectResult:
        """
        收集本地文件

        Args:
            source: 文件路径
            tags: 用户提供的标签列表（可选）
            title: 自定义标题（可选，默认使用文件名）
            skip_existing: 是否跳过已存在的内容（默认 False）
            storage: SQLiteStorage 实例，用于重复检测（可选）
            **kwargs: 额外的参数

        Returns:
            CollectResult: 收集结果

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        file_path = Path(source).resolve()

        # 验证文件存在
        if not file_path.exists():
            return CollectResult(
                success=False,
                error=f"文件不存在: {file_path}"
            )

        # 验证文件格式
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return CollectResult(
                success=False,
                error=f"不支持的文件格式: {file_path.suffix}。支持的格式: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        # Duplicate check (before any heavy processing)
        if skip_existing and storage:
            source_key = str(file_path)
            existing = self._check_duplicate(source=source_key, storage=storage)
            if existing:
                return CollectResult(
                    success=False,
                    error=f"Duplicate: already collected as '{existing['title']}' (id: {existing['id']})"
                )

        try:
            # 提取内容
            content = self._extract_content(file_path)

            # 如果没有提供标题，使用文件名
            if not title:
                title = file_path.stem

            # 生成元数据
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source=file_path,
                tags=tags or [],
                **kwargs
            )

            # 生成安全的文件名
            filename = self._generate_safe_filename("file", title)

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
                error=f"文件处理失败: {str(e)}"
            )

    def _extract_content(self, source: str | Path) -> str:
        """
        从文件提取纯文本内容

        Args:
            source: 文件路径

        Returns:
            str: 提取的纯文本内容

        Raises:
            RuntimeError: 解析失败
        """
        file_path = Path(source)
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext in {".md", ".markdown"}:
            return self._extract_markdown(file_path)
        elif ext == ".txt":
            return self._extract_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _extract_pdf(self, file_path: Path) -> str:
        """
        从 PDF 文件提取文本

        Args:
            file_path: PDF 文件路径

        Returns:
            str: 提取的文本内容

        Raises:
            ImportError: PyPDF2 未安装
            RuntimeError: PDF 解析失败
        """
        if PyPDF2 is None:
            raise ImportError(
                "PyPDF2 未安装。请运行: pip install PyPDF2"
            )

        try:
            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            if not text_parts:
                return f"[PDF 文件: {file_path.name}，未提取到文本内容]"

            return "\n\n".join(text_parts)

        except Exception as e:
            raise RuntimeError(f"PDF 解析失败: {str(e)}")

    def extract_pdf_pages(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        从 PDF 文件按页提取文本，保留页码信息

        Args:
            file_path: PDF 文件路径

        Returns:
            List[Dict]: 每页的数据，包含 page_number 和 text

        Raises:
            ImportError: PyPDF2 未安装
            RuntimeError: PDF 解析失败
        """
        if PyPDF2 is None:
            raise ImportError(
                "PyPDF2 未安装。请运行: pip install PyPDF2"
            )

        try:
            pages = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        pages.append({
                            "page_number": page_num,
                            "text": text,
                        })
            return pages

        except Exception as e:
            raise RuntimeError(f"PDF 页级解析失败: {str(e)}")

    def get_pdf_page_count(self, file_path: Path) -> int:
        """
        获取 PDF 文件的页数

        Args:
            file_path: PDF 文件路径

        Returns:
            int: 页数
        """
        if PyPDF2 is None:
            return 0

        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception:
            return 0

    def _extract_markdown(self, file_path: Path) -> str:
        """
        从 Markdown 文件提取内容（去除 YAML Front Matter）

        Args:
            file_path: Markdown 文件路径

        Returns:
            str: Markdown 正文内容

        Raises:
            RuntimeError: 文件读取失败
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # 移除 YAML Front Matter（如果存在）
            content = self._remove_yaml_front_matter(content)

            return content.strip()

        except Exception as e:
            raise RuntimeError(f"Markdown 文件读取失败: {str(e)}")

    def _extract_txt(self, file_path: Path) -> str:
        """
        从 TXT 文件提取内容

        Args:
            file_path: TXT 文件路径

        Returns:
            str: 文本内容

        Raises:
            RuntimeError: 文件读取失败
        """
        try:
            # 尝试 UTF-8 编码，失败则尝试其他编码
            encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
            for encoding in encodings:
                try:
                    content = file_path.read_text(encoding=encoding)
                    return content.strip()
                except UnicodeDecodeError:
                    continue
            raise RuntimeError(f"无法解码文件，尝试的编码: {', '.join(encodings)}")

        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"TXT 文件读取失败: {str(e)}")

    def _generate_metadata(
        self,
        title: str,
        content: str,
        source: Path,
        tags: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        生成文件元数据

        Args:
            title: 文档标题
            content: 文档内容
            source: 原始文件路径
            tags: 标签列表
            **kwargs: 额外的元数据字段

        Returns:
            Dict[str, Any]: 元数据字典
        """
        # 生成唯一 ID
        timestamp = datetime.now()
        file_id = f"file_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 基础元数据
        metadata = {
            "id": file_id,
            "title": title,
            "source": str(source),
            "content_type": "file",
            "collected_at": timestamp,
            "tags": tags or [],
            "word_count": self._count_words(content),
            "status": "processed",
            "original_filename": source.name,
            "file_extension": source.suffix.lower(),
        }

        # 合并额外的元数据
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _remove_yaml_front_matter(content: str) -> str:
        """
        移除 Markdown 文件中的 YAML Front Matter

        Args:
            content: Markdown 内容

        Returns:
            str: 移除 Front Matter 后的内容
        """
        # 匹配 YAML Front Matter: ---\n...\n---
        pattern = r"^---\s*\n.*?\n---\s*\n"
        return re.sub(pattern, "", content, flags=re.DOTALL)

    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return list(self.SUPPORTED_EXTENSIONS)
