"""
Text chunking processor module

Splits long text into smaller chunks for vector embedding and retrieval.
Supports configurable chunk size, overlap, and separators.
"""

import re
from typing import Any, Dict, List, Optional

from kb.processors.base import BaseProcessor, ProcessResult


class Chunker(BaseProcessor):
    """
    Text chunking processor.

    Splits input text into fixed-size chunks with support for overlap between chunks.
    Chunking strategy.:
    1. First try splitting by paragraph separator
    2. If paragraphs are still too large, split by sentence
    3. If sentences are still too large, split by character count
    4. Merge small segments until reaching chunk size
    5. Apply overlap between consecutive chunks

    Usage examples:
        >>> from kb.processors.chunker import Chunker
        >>> chunker = Chunker(chunk_size=500, chunk_overlap=50)
        >>> result = chunker.process("Long text content....")
        >>> if result.success:
        ...     for chunk in result.data:
        ...         print(chunk["content"])
    """

    # Default sentence separators (supports Chinese and English)
    SENTENCE_SEPARATORS = [". ", "。", "!\n", "？\n", "!\n", "?\n", "\n"]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        separator: str = "\n\n",
        **kwargs: Any
    ) -> None:
        """
        Initialize text chunking processor.

        Args:
            chunk_size: Maximum characters per chunk, defaults to 1000.
            chunk_overlap: Overlapping characters between consecutive chunks, defaults to 100.
            separator: Preferred split separator, defaults to paragraph separator "\\n\\n"
            **kwargs: Additional configuration parameters.
        """
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    @classmethod
    def from_config(cls, config: Optional["Config"] = None) -> "Chunker":
        """
        Create chunker processor instance from configuration.

        Args:
            config: Configuration object; uses default configuration if None.

        Returns:
            Chunker: Chunker processor instance.
        """
        if config is None:
            from kb.config import Config
            config = Config()

        chunking_config = config.get("chunking", {})
        chunk_size = chunking_config.get("max_chunk_size", 1000)
        chunk_overlap = chunking_config.get("chunk_overlap", 100)
        separator = chunking_config.get("separator", "\n\n")

        return cls(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator
        )

    def process(self, data: str, **kwargs: Any) -> ProcessResult:
        """
        Process text and split into chunks.

        Args:
            data: Text content to be chunked (string).
            **kwargs: Additional processing parameters.
                - chunk_size: Override default chunk size
                - chunk_overlap: Override default overlap size
                - separator: Override default separator

        Returns:
            ProcessResult: Processing result.
                - success: True indicates processing succeeded
                - data: List of chunks, each containing content, chunk_index, start_char, end_char
                - metadata: Contains total_chunks, chunk_size, chunk_overlap
                - error: Error message (if failed).
        """
        try:
            # Allow overriding parameters via kwargs
            chunk_size = kwargs.get("chunk_size", self.chunk_size)
            chunk_overlap = kwargs.get("chunk_overlap", self.chunk_overlap)
            separator = kwargs.get("separator", self.separator)

            # Handle empty input
            if not data or not data.strip():
                return ProcessResult(
                    success=True,
                    data=[],
                    metadata={
                        "total_chunks": 0,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )

            # Execute chunking
            chunks = self._split_text(
                data,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator=separator
            )

            return ProcessResult(
                success=True,
                data=chunks,
                metadata={
                    "total_chunks": len(chunks),
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                data=None,
                error=str(e)
            )

    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separator: str
    ) -> List[Dict[str, Any]]:
        """
        Core chunking logic.

        Args:
            text: Text to be chunked.
            chunk_size: Chunk size.
            chunk_overlap: Overlap size.
            separator: Separator.

        Returns:
            List[Dict]: List of chunks.
        """
        # If text is less than or equal to chunk size, return as single chunk
        if len(text) <= chunk_size:
            return [{
                "content": text,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(text)
            }]

        # Step 1: Split into paragraphs by separator
        paragraphs = self._split_by_separator(text, separator)

        # Step 2: Handle oversized paragraphs
        segments = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                segments.append(para)
            else:
                # Paragraph too large, split by sentence
                sentences = self._split_by_sentences(para)
                for sent in sentences:
                    if len(sent) <= chunk_size:
                        segments.append(sent)
                    else:
                        # Sentence still too large, split by character
                        char_chunks = self._split_by_chars(sent, chunk_size)
                        segments.extend(char_chunks)

        # Step 3: Merge small segments into chunks
        chunks = self._merge_segments(segments, chunk_size, chunk_overlap, text)

        return chunks

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """
        Split text by separator.

        Args:
            text: Text content.
            separator: Separator.

        Returns:
            List[str]: List of paragraphs after splitting.
        """
        parts = text.split(separator)
        # Filter empty paragraphs and keep non-empty parts
        return [p for p in parts if p.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        Split text by sentence (supports Chinese and English).

        Args:
            text: Text content.

        Returns:
            List[str]: List of sentences.
        """
        # Split by sentence separator using regex
        # Match period, question mark, exclamation mark, etc. followed by space or newline
        pattern = r'(?<=[.。!！?？])\s*(?=\S)'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_chars(self, text: str, chunk_size: int) -> List[str]:
        """
        Split text by character count.

        Args:
            text: Text content.
            chunk_size: Chunk size.

        Returns:
            List[str]: List of text blocks after splitting.
        """
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def _merge_segments(
        self,
        segments: List[str],
        chunk_size: int,
        chunk_overlap: int,
        original_text: str
    ) -> List[Dict[str, Any]]:
        """
        Merge small segments into chunks and apply overlap.

        Args:
            segments: List of paragraphs/sentences.
            chunk_size: Chunk size.
            chunk_overlap: Overlap size.
            original_text: Original text (for position calculation).

        Returns:
            List[Dict]: List of chunks with position information.
        """
        if not segments:
            return []

        chunks = []
        current_chunk = ""
        current_start = 0

        for segment in segments:
            # Check if adding this segment exceeds chunk size
            if current_chunk:
                potential = current_chunk + self.separator + segment
            else:
                potential = segment

            if len(potential) <= chunk_size:
                # Can add to current chunk
                current_chunk = potential
            else:
                # Current chunk is full, save and start new chunk
                if current_chunk:
                    # Calculate position in original text
                    start_pos = original_text.find(current_chunk, current_start)
                    if start_pos == -1:
                        # If exact match fails, use approximate position
                        start_pos = current_start
                    end_pos = start_pos + len(current_chunk)

                    chunks.append({
                        "content": current_chunk,
                        "chunk_index": len(chunks),
                        "start_char": start_pos,
                        "end_char": end_pos
                    })

                    # Apply overlap: take overlap chars from current chunk end
                    if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                        overlap_text = current_chunk[-chunk_overlap:]
                        current_chunk = overlap_text + self.separator + segment
                        current_start = end_pos - chunk_overlap
                    else:
                        current_chunk = segment
                        current_start = end_pos
                else:
                    current_chunk = segment

        # Process the last chunk
        if current_chunk:
            start_pos = original_text.find(current_chunk, current_start)
            if start_pos == -1:
                start_pos = current_start
            end_pos = start_pos + len(current_chunk)

            chunks.append({
                "content": current_chunk,
                "chunk_index": len(chunks),
                "start_char": start_pos,
                "end_char": end_pos
            })

        return chunks

    def _count_tokens(self, text: str) -> int:
        """
        Estimate the token count of text.

        Uses a simple approximation: character count divided by 4.
        For Chinese text, each character is approximately 1-2 tokens.
        For English text, approximately every 4 characters equal 1 token.

        Args:
            text: Text content.

        Returns:
            int: Estimated token count.
        """
        # Simple approximation: character count divided by 4
        return len(text) // 4

    def process_with_pages(
        self,
        pages: List[Dict[str, Any]],
        **kwargs: Any
    ) -> ProcessResult:
        """
        Chunk PDF text by page, preserving page_number metadata.

        Chunks each page's text independently, with page_number in each chunk's metadata.
        When a page's text is smaller than chunk_size, does not merge across pages, preserving page boundaries.

        Args:
            pages: List of pages, each containing page_number (int) and text (str).
            **kwargs: Additional processing parameters (chunk_size, chunk_overlap, separator).

        Returns:
            ProcessResult: Processing result, each chunk in data contains a page_number field.
        """
        try:
            chunk_size = kwargs.get("chunk_size", self.chunk_size)
            chunk_overlap = kwargs.get("chunk_overlap", self.chunk_overlap)
            separator = kwargs.get("separator", self.separator)

            if not pages:
                return ProcessResult(
                    success=True,
                    data=[],
                    metadata={
                        "total_chunks": 0,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )

            all_chunks = []
            global_index = 0

            for page in pages:
                page_number = page.get("page_number", 0)
                text = page.get("text", "")

                if not text or not text.strip():
                    continue

                # Chunk this page independently
                page_chunks = self._split_text(
                    text,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separator=separator
                )

                # Add page_number to each chunk and update global index
                for chunk in page_chunks:
                    chunk["page_number"] = page_number
                    chunk["chunk_index"] = global_index
                    global_index += 1
                    all_chunks.append(chunk)

            return ProcessResult(
                success=True,
                data=all_chunks,
                metadata={
                    "total_chunks": len(all_chunks),
                    "total_pages": len(pages),
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                data=None,
                error=str(e)
            )
