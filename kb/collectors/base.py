"""
Base collector module

Defines the abstract base class for all collectors, providing a unified interface and data models.
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
    Collection result data class.

    Attributes:
        success: Whether the collection was successful.
        file_path: Path of the saved file.
        title: Document title.
        word_count: Word count.
        tags: List of extracted tags.
        metadata: Additional metadata.
        error: Error message (if failed).
        content_hash: Content hash for duplicate detection.
        summary: Document summary.
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
    Abstract base class for collectors.

    All concrete collectors (file, webpage, bookmark, etc.) should inherit this class
    and implement the unified collection interface.

    Methods that subclasses must implement:
        - collect: Execute the collection operation
        - _extract_content: Extract plain text content
        - _generate_metadata: Generate metadata
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize the collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
        """
        self.output_dir = output_dir or (Path.home() / ".knowledge-base" / "1_collect")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def collect(self, source: Any, **kwargs: Any) -> CollectResult:
        """
        Execute the collection operation.

        Args:
            source: Data source (file path, URL, etc.).
            **kwargs: Additional parameters (e.g., tags, title).

        Returns:
            CollectResult: Collection result.
        """
        pass

    @abstractmethod
    def _extract_content(self, source: Any) -> str:
        """
        Extract plain text content from the data source.

        Args:
            source: Data source.

        Returns:
            str: Extracted plain text content.
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
        Generate document metadata.

        Args:
            title: Document title.
            content: Document content.
            source: Original data source.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
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
        Save content to a Markdown file with YAML Front Matter.

        Args:
            content: Document body content.
            metadata: YAML Front Matter metadata.
            filename: File name.
            sub_dir: Subdirectory name (e.g., files, urls).

        Returns:
            Path: Path of the saved file.
        """
        # Create subdirectory
        target_dir = self.output_dir / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate complete Markdown content
        yaml_header = self._format_yaml(metadata)
        full_content = f"---\n{yaml_header}---\n\n{content}"

        # Write to file
        file_path = target_dir / filename
        file_path.write_text(full_content, encoding="utf-8")

        return file_path

    @staticmethod
    def _format_yaml(metadata: Dict[str, Any]) -> str:
        """
        Format a metadata dictionary as a YAML string.

        Args:
            metadata: Metadata dictionary.

        Returns:
            str: YAML-formatted string.
        """
        lines = []
        for key, value in metadata.items():
            if isinstance(value, list):
                # List type: use YAML list format
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
                # String type: add quotes if special characters present
                str_value = str(value)
                if any(c in str_value for c in [':', '#', '{', '}', '[', ']', ',']):
                    lines.append(f'{key}: "{str_value}"')
                else:
                    lines.append(f"{key}: {str_value}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _generate_safe_filename(prefix: str, title: Optional[str] = None) -> str:
        """
        Generate a safe filename using date + slug.

        Args:
            prefix: File type prefix (e.g., file, url).
            title: Document title (optional).

        Returns:
            str: Safe filename (.md extension).
        """
        import re
        import unicodedata

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        if title:
            # Check if contains CJK characters
            has_cjk = any("\u4e00" <= c <= "\u9fff" for c in title)
            if has_cjk:
                try:
                    from pypinyin import lazy_pinyin
                    slug = "-".join(lazy_pinyin(title))
                except ImportError:
                    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
            else:
                slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
            # Convert to lowercase
            slug = slug.lower()
            # Replace non-alphanumeric characters with hyphens
            slug = re.sub(r"[^a-z0-9]+", "-", slug)
            # Remove leading/trailing hyphens
            slug = slug.strip("-")
            # Limit length
            slug = slug[:50]
            return f"{timestamp}_{slug}.md"
        else:
            return f"{timestamp}_{prefix}.md"

    @staticmethod
    def _count_words(content: str) -> int:
        """
        Count words in text.

        Args:
            content: Text content.

        Returns:
            int: Word count (Chinese characters count as 1 each, English words split by whitespace).
        """
        # Simple count: Chinese characters + English words
        chinese_chars = sum(1 for char in content if "\u4e00" <= char <= "\u9fff")
        # Count English words after removing Chinese characters
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
