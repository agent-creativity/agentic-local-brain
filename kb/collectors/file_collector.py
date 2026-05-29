from __future__ import annotations

"""
File collector module

Supports parsing PDF, Markdown, TXT files, extracting content and saving to the knowledge base.
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
    File collector.

    Supports parsing files in the following formats:
    - PDF: Extract text using PyPDF2
    - Markdown (.md): Read directly
    - TXT (.txt): Read directly

    Processing flow:
    1. Detect file type
    2. Extract plain text content
    3. Generate YAML Front Matter metadata
    4. Save to ~/.knowledge-base/1_collect/files/ directory
    5. Return collection result
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize file collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
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
        Collect local file.

        Args:
            source: File path.
            tags: User-provided tag list (optional).
            title: Custom title (optional, defaults to filename).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.

        Raises:
            FileNotFoundError: File does not exist.
            ValueError: Unsupported file format.
        """
        file_path = Path(source).resolve()

        # Validate file exists
        if not file_path.exists():
            return CollectResult(
                success=False,
                error=f"文件不存在: {file_path}"
            )

        # Validate file format
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
            # Extract content
            content = self._extract_content(file_path)

            # If no title provided, use filename
            if not title:
                title = file_path.stem

            # Generate metadata
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source=file_path,
                tags=tags or [],
                **kwargs
            )

            # Generate safe filename
            filename = self._generate_safe_filename("file", title)

            # Save to file
            saved_path = self._save_to_file(
                content=content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir
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
                content_hash=content_hash
            )

        except Exception as e:
            return CollectResult(
                success=False,
                error=f"文件处理失败: {str(e)}"
            )

    def _extract_content(self, source: str | Path) -> str:
        """
        Extract plain text content from file.

        Args:
            source: File path.

        Returns:
            str: Extracted plain text content.

        Raises:
            RuntimeError: Parsing failed.
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
        Extract text from PDF file.

        Args:
            file_path: PDF file path.

        Returns:
            str: Extracted text content.

        Raises:
            ImportError: PyPDF2 not installed.
            RuntimeError: PDF parsing failed.
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
        Extract text from PDF file by page, preserving page number information.

        Args:
            file_path: PDF file path.

        Returns:
            List[Dict]: Per-page data containing page_number and text.

        Raises:
            ImportError: PyPDF2 not installed.
            RuntimeError: PDF parsing failed.
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
        Get the number of pages in a PDF file.

        Args:
            file_path: PDF file path.

        Returns:
            int: Number of pages.
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
        Extract content from Markdown file (stripping YAML Front Matter).

        Args:
            file_path: Markdown file path.

        Returns:
            str: Markdown body content.

        Raises:
            RuntimeError: File read failed.
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Remove YAML Front Matter (if present)
            content = self._remove_yaml_front_matter(content)

            return content.strip()

        except Exception as e:
            raise RuntimeError(f"Markdown 文件读取失败: {str(e)}")

    def _extract_txt(self, file_path: Path) -> str:
        """
        Extract content from TXT file.

        Args:
            file_path: TXT file path.

        Returns:
            str: Text content.

        Raises:
            RuntimeError: File read failed.
        """
        try:
            # Try UTF-8 encoding, fall back to other encodings
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
        Generate file metadata.

        Args:
            title: Document title.
            content: Document content.
            source: Original file path.
            tags: Tag list.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        # Generate unique ID
        timestamp = datetime.now()
        file_id = f"file_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Base metadata
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

        # Merge additional metadata
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _remove_yaml_front_matter(content: str) -> str:
        """
        Remove YAML Front Matter from Markdown content.

        Args:
            content: Markdown content.

        Returns:
            str: Content with Front Matter removed.
        """
        # Match YAML Front Matter: ---\n...\n---
        pattern = r"^---\s*\n.*?\n---\s*\n"
        return re.sub(pattern, "", content, flags=re.DOTALL)

    def get_supported_formats(self) -> List[str]:
        """
        Get supported file formats.

        Returns:
            List[str]: List of supported file extensions.
        """
        return list(self.SUPPORTED_EXTENSIONS)
