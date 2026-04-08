"""
PageIndex feature tests

Tests for page-aware PDF chunking and indexing:
- Chunker.process_with_pages() — page-level chunking
- FileCollector.extract_pdf_pages() / get_pdf_page_count() — PDF page extraction
- _index_content_for_search() with pdf_pages — page_number metadata propagation
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kb.processors.chunker import Chunker
from kb.processors.base import ProcessResult


# ---------------------------------------------------------------------------
# Chunker.process_with_pages tests
# ---------------------------------------------------------------------------

class TestChunkerProcessWithPages:
    """Tests for Chunker.process_with_pages()"""

    def test_empty_pages(self):
        """Empty page list returns empty result."""
        chunker = Chunker(chunk_size=500)
        result = chunker.process_with_pages([])

        assert result.success is True
        assert result.data == []
        assert result.metadata["total_chunks"] == 0

    def test_single_page_short_text(self):
        """Single page with short text produces one chunk with page_number."""
        chunker = Chunker(chunk_size=500)
        pages = [{"page_number": 1, "text": "This is page one content."}]

        result = chunker.process_with_pages(pages)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["page_number"] == 1
        assert result.data[0]["chunk_index"] == 0
        assert "page one content" in result.data[0]["content"]

    def test_multiple_pages_preserve_boundaries(self):
        """Multiple pages are chunked independently — no cross-page merging."""
        chunker = Chunker(chunk_size=500, chunk_overlap=0)
        pages = [
            {"page_number": 1, "text": "Content of page one."},
            {"page_number": 2, "text": "Content of page two."},
            {"page_number": 3, "text": "Content of page three."},
        ]

        result = chunker.process_with_pages(pages)

        assert result.success is True
        assert len(result.data) == 3
        # Verify page_number is preserved correctly
        assert result.data[0]["page_number"] == 1
        assert result.data[1]["page_number"] == 2
        assert result.data[2]["page_number"] == 3
        # Verify global chunk_index is sequential
        assert result.data[0]["chunk_index"] == 0
        assert result.data[1]["chunk_index"] == 1
        assert result.data[2]["chunk_index"] == 2

    def test_long_page_produces_multiple_chunks(self):
        """A page longer than chunk_size produces multiple chunks, all with same page_number."""
        chunker = Chunker(chunk_size=50, chunk_overlap=0)
        long_text = "Word " * 30  # ~150 chars
        pages = [{"page_number": 5, "text": long_text}]

        result = chunker.process_with_pages(pages)

        assert result.success is True
        assert len(result.data) > 1
        # All chunks should have the same page_number
        for chunk in result.data:
            assert chunk["page_number"] == 5

    def test_empty_page_text_skipped(self):
        """Pages with empty or whitespace-only text are skipped."""
        chunker = Chunker(chunk_size=500)
        pages = [
            {"page_number": 1, "text": "Valid content."},
            {"page_number": 2, "text": ""},
            {"page_number": 3, "text": "   \n  "},
            {"page_number": 4, "text": "More content."},
        ]

        result = chunker.process_with_pages(pages)

        assert result.success is True
        assert len(result.data) == 2
        page_numbers = [c["page_number"] for c in result.data]
        assert 1 in page_numbers
        assert 4 in page_numbers
        assert 2 not in page_numbers
        assert 3 not in page_numbers

    def test_metadata_includes_total_pages(self):
        """Result metadata includes total_pages count."""
        chunker = Chunker(chunk_size=500)
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"},
        ]

        result = chunker.process_with_pages(pages)

        assert result.metadata["total_pages"] == 2
        assert result.metadata["total_chunks"] == 2

    def test_kwargs_override(self):
        """chunk_size can be overridden via kwargs."""
        chunker = Chunker(chunk_size=1000)
        long_text = "A" * 200
        pages = [{"page_number": 1, "text": long_text}]

        result = chunker.process_with_pages(pages, chunk_size=50)

        assert result.success is True
        assert len(result.data) > 1
        assert result.metadata["chunk_size"] == 50

    def test_global_index_across_pages(self):
        """chunk_index is globally sequential across multiple pages."""
        chunker = Chunker(chunk_size=30, chunk_overlap=0)
        pages = [
            {"page_number": 1, "text": "A" * 80},  # should produce multiple chunks
            {"page_number": 2, "text": "B" * 80},  # more chunks
        ]

        result = chunker.process_with_pages(pages)

        assert result.success is True
        indices = [c["chunk_index"] for c in result.data]
        assert indices == list(range(len(result.data)))


# ---------------------------------------------------------------------------
# FileCollector PDF page extraction tests
# ---------------------------------------------------------------------------

class TestFileCollectorPdfPages:
    """Tests for FileCollector.extract_pdf_pages() and get_pdf_page_count()"""

    @patch("kb.collectors.file_collector.PyPDF2")
    def test_extract_pdf_pages(self, mock_pypdf2, tmp_path):
        """extract_pdf_pages returns per-page data with page_number and text."""
        from kb.collectors.file_collector import FileCollector

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        # Mock PyPDF2 reader with 3 pages
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page one text."
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page two text."
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "  "  # empty page

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_pypdf2.PdfReader.return_value = mock_reader

        collector = FileCollector(output_dir=tmp_path)
        pages = collector.extract_pdf_pages(pdf_file)

        # Only non-empty pages
        assert len(pages) == 2
        assert pages[0]["page_number"] == 1
        assert pages[0]["text"] == "Page one text."
        assert pages[1]["page_number"] == 2
        assert pages[1]["text"] == "Page two text."

    @patch("kb.collectors.file_collector.PyPDF2")
    def test_get_pdf_page_count(self, mock_pypdf2, tmp_path):
        """get_pdf_page_count returns correct page count."""
        from kb.collectors.file_collector import FileCollector

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        mock_reader = MagicMock()
        mock_reader.pages = [Mock(), Mock(), Mock(), Mock(), Mock()]
        mock_pypdf2.PdfReader.return_value = mock_reader

        collector = FileCollector(output_dir=tmp_path)
        count = collector.get_pdf_page_count(pdf_file)

        assert count == 5

    @patch("kb.collectors.file_collector.PyPDF2", None)
    def test_get_pdf_page_count_no_pypdf2(self, tmp_path):
        """get_pdf_page_count returns 0 when PyPDF2 is not installed."""
        from kb.collectors.file_collector import FileCollector

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        collector = FileCollector(output_dir=tmp_path)
        count = collector.get_pdf_page_count(pdf_file)

        assert count == 0


# ---------------------------------------------------------------------------
# _index_content_for_search with pdf_pages tests
# ---------------------------------------------------------------------------

class TestIndexContentPageNumber:
    """Tests for page_number propagation in _index_content_for_search."""

    @patch("kb.storage.sqlite_storage.SQLiteStorage")
    @patch("kb.storage.chroma_storage.ChromaStorage")
    @patch("kb.processors.embedder.Embedder")
    @patch("kb.processors.chunker.Chunker")
    @patch("kb.config.Config")
    def test_page_number_in_metadata(
        self, MockConfig, MockChunker, MockEmbedder, MockChroma, MockSqlite
    ):
        """When pdf_pages is provided, page_number appears in Chroma metadata."""
        from kb.commands.utils import _index_content_for_search

        # Setup config mock
        mock_config = MockConfig.return_value
        mock_config.get.return_value = "~/.knowledge-base"

        # Setup chunker to return chunks with page_number
        mock_chunker = MockChunker.from_config.return_value
        mock_chunker.process_with_pages.return_value = ProcessResult(
            success=True,
            data=[
                {"content": "chunk from page 1", "chunk_index": 0, "start_char": 0, "end_char": 17, "page_number": 1},
                {"content": "chunk from page 2", "chunk_index": 1, "start_char": 0, "end_char": 17, "page_number": 2},
            ]
        )

        # Setup embedder
        mock_embedder = MockEmbedder.from_config.return_value
        mock_embedder.embed.return_value = [[0.1] * 10, [0.2] * 10]

        # Setup chroma
        mock_chroma_inst = MockChroma.return_value

        # Setup sqlite
        mock_sqlite_inst = MockSqlite.return_value

        pdf_pages = [
            {"page_number": i, "text": f"chunk from page {i}"}
            for i in range(1, 13)  # 12 pages, > 10 threshold
        ]

        result = _index_content_for_search(
            item_id="test_item",
            content="full content",
            title="Test Doc",
            tags=["test"],
            source="/path/to/doc.pdf",
            content_type="file",
            pdf_pages=pdf_pages
        )

        assert result is True

        # Verify process_with_pages was called (not process)
        mock_chunker.process_with_pages.assert_called_once_with(pdf_pages)
        mock_chunker.process.assert_not_called()

        # Verify page_number in metadata passed to ChromaDB
        call_args = mock_chroma_inst.add_documents.call_args
        metadatas = call_args[1]["metadatas"] if "metadatas" in call_args[1] else call_args[0][2]
        # Check that at least two chunks have page_number
        page_numbers_in_meta = [m["page_number"] for m in metadatas if "page_number" in m]
        assert 1 in page_numbers_in_meta
        assert 2 in page_numbers_in_meta

    @patch("kb.storage.sqlite_storage.SQLiteStorage")
    @patch("kb.storage.chroma_storage.ChromaStorage")
    @patch("kb.processors.embedder.Embedder")
    @patch("kb.processors.chunker.Chunker")
    @patch("kb.config.Config")
    def test_no_pdf_pages_uses_normal_process(
        self, MockConfig, MockChunker, MockEmbedder, MockChroma, MockSqlite
    ):
        """When pdf_pages is None, uses chunker.process() as before."""
        from kb.commands.utils import _index_content_for_search

        mock_config = MockConfig.return_value
        mock_config.get.return_value = "~/.knowledge-base"

        mock_chunker = MockChunker.from_config.return_value
        mock_chunker.process.return_value = ProcessResult(
            success=True,
            data=[
                {"content": "regular chunk", "chunk_index": 0, "start_char": 0, "end_char": 13},
            ]
        )

        mock_embedder = MockEmbedder.from_config.return_value
        mock_embedder.embed.return_value = [[0.1] * 10]

        mock_chroma_inst = MockChroma.return_value
        mock_sqlite_inst = MockSqlite.return_value

        result = _index_content_for_search(
            item_id="test_item",
            content="regular chunk",
            title="Test Doc",
        )

        assert result is True

        # Verify process was called (not process_with_pages)
        mock_chunker.process.assert_called_once_with("regular chunk")
        mock_chunker.process_with_pages.assert_not_called()

        # Verify no page_number in metadata
        call_args = mock_chroma_inst.add_documents.call_args
        metadatas = call_args[1]["metadatas"] if "metadatas" in call_args[1] else call_args[0][2]
        assert "page_number" not in metadatas[0]

    @patch("kb.storage.sqlite_storage.SQLiteStorage")
    @patch("kb.storage.chroma_storage.ChromaStorage")
    @patch("kb.processors.embedder.Embedder")
    @patch("kb.processors.chunker.Chunker")
    @patch("kb.config.Config")
    def test_short_pdf_uses_normal_process(
        self, MockConfig, MockChunker, MockEmbedder, MockChroma, MockSqlite
    ):
        """When pdf_pages has <=10 pages, uses chunker.process() instead."""
        from kb.commands.utils import _index_content_for_search

        mock_config = MockConfig.return_value
        mock_config.get.return_value = "~/.knowledge-base"

        mock_chunker = MockChunker.from_config.return_value
        mock_chunker.process.return_value = ProcessResult(
            success=True,
            data=[
                {"content": "content", "chunk_index": 0, "start_char": 0, "end_char": 7},
            ]
        )

        mock_embedder = MockEmbedder.from_config.return_value
        mock_embedder.embed.return_value = [[0.1] * 10]

        MockChroma.return_value
        MockSqlite.return_value

        # 10 pages — should NOT trigger page-aware chunking
        pdf_pages = [{"page_number": i, "text": f"Page {i}"} for i in range(1, 11)]

        _index_content_for_search(
            item_id="test_item",
            content="content",
            title="Test",
            pdf_pages=pdf_pages
        )

        mock_chunker.process.assert_called_once()
        mock_chunker.process_with_pages.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
