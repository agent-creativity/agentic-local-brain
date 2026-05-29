"""
Note collector module

Provides quick note collection, supporting:
- Quickly recording ideas and inspirations
- Automatically generating title and unique ID
- Adding tag classification
- Saving as Markdown files with YAML Front Matter
"""

import random
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.collectors.base import BaseCollector, CollectResult


class NoteCollector(BaseCollector):
    """
    Note collector.

    Used for quickly collecting user notes, ideas, and inspirations. Notes are saved as Markdown files 
    with YAML Front Matter metadata.

    Features:
    - Auto-generate title (based on first 20 characters of content)
    - Generate unique note ID (format: note_YYYYMMDD_HHMMSS_XXX)
    - Support custom tags
    - Save to 1_collect/notes/ directory

    Usage examples:
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
        Initialize note collector.

        Args:
            config: Configuration dictionary, optional. Supports the following config items:
                - output_dir: Output directory path, defaults to ~/.knowledge-base/1_collect/
                - auto_title_length: Number of characters used for auto-generated title (default 20)
        """
        # Get output directory from configuration
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
        Collect note.

        Args:
            text: Note content.
            title: Note title (optional, auto-generated if not provided).
            tags: Tag list (optional).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.

        Raises:
            ValueError: When note content is empty.
        """
        # Validate content
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
            # If no title provided, auto-generate
            if not title:
                title = self._generate_title(content)

            # Generate unique ID
            note_id = self._generate_note_id()

            # Generate metadata
            metadata = self._generate_metadata(
                title=title,
                content=content,
                source="manual_input",
                note_id=note_id,
                tags=tags or [],
                **kwargs
            )

            # Generate filename
            filename = self._generate_filename(note_id, title)

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
                error=f"笔记保存失败: {str(e)}"
            )

    def _extract_content(self, source: Any) -> str:
        """
        Extract plain text content from the data source.

        For note collector, source is the text content itself.

        Args:
            source: Text content.

        Returns:
            str: Extracted plain text content.
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
        Generate note metadata.

        Args:
            title: Note title.
            content: Note content.
            source: Source identifier.
            note_id: Note unique ID.
            tags: Tag list.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
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

        # Merge additional metadata
        metadata.update(kwargs)

        return metadata

    def _generate_title(self, content: str) -> str:
        """
        Auto-generate title based on content.

        Uses the first N characters of content as title (N configured by auto_title_length).
        If content has fewer than N characters, uses all content.

        Args:
            content: Note content.

        Returns:
            str: Generated title.
        """
        # Get first N characters
        title = content[:self._auto_title_length].strip()

        # If title ends with punctuation, remove it
        while title and title[-1] in "，。！？,.!?;；：":
            title = title[:-1]

        # If content is empty (should not happen), return default title
        if not title:
            title = "未命名笔记"

        return title

    def _generate_note_id(self) -> str:
        """
        Generate unique note ID.

        Format: note_YYYYMMDD_HHMMSS_XXX
        where XXX is a 3-digit random number to avoid conflicts when generating multiple notes within the same second.

        Returns:
            str: Unique note ID.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Generate 3-digit random number
        suffix = "".join(random.choices(string.digits, k=3))
        return f"note_{timestamp}_{suffix}"

    def _generate_filename(self, note_id: str, title: str) -> str:
        """
        Generate note filename.

        Uses combination of note ID and title slug as filename.

        Args:
            note_id: Note unique ID.
            title: Note title.

        Returns:
            str: Filename (.md extension).
        """
        import re
        import unicodedata

        # Convert title to slug
        slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        slug = slug.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        slug = slug[:50]  # Limit length

        if slug:
            return f"{note_id}_{slug}.md"
        else:
            return f"{note_id}.md"
