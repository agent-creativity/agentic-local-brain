"""
Academic paper collector module

Supports collecting academic papers from arXiv, extracting metadata and abstracts, and saving to the knowledge base.
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
    Academic paper collector.

    Supports collecting academic papers from arXiv:
    - Parse arXiv ID (supports multiple formats)
    - Retrieve paper metadata via arXiv API
    - Extract title, authors, abstract, categories, etc.
    - Save as Markdown files with YAML Front Matter

    Processing flow:
    1. Parse arXiv ID
    2. Call arXiv API to get paper information
    3. Parse XML response
    4. Generate YAML Front Matter metadata
    5. Save to ~/.knowledge-base/1_collect/papers/ directory
    6. Return collection result

    Examples:
        >>> collector = PaperCollector()
        >>> result = collector.collect("arxiv:2301.12345")
        >>> if result.success:
        ...     print(f"成功: {result.title}")
    """

    # arXiv API Configuration.
    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    DEFAULT_TIMEOUT = 30

    # arXiv ID format regex
    # Supported formats: arxiv:2301.12345, 2301.12345, https://arxiv.org/abs/2301.12345
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
        Initialize paper collector.

        Args:
            output_dir: Output directory. Defaults to ~/.knowledge-base/1_collect/.
            timeout: HTTP request timeout in seconds, defaults to 30.
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
        Collect arXiv paper.

        Args:
            source: arXiv ID or URL (supported formats: arxiv:2301.12345, 2301.12345, or arXiv URL).
            tags: User-provided tag list (optional).
            download_pdf: Whether to download PDF (defaults to False, not yet implemented).
            skip_existing: Whether to skip existing content (default False).
            storage: SQLiteStorage instance for duplicate detection (optional).
            **kwargs: Additional parameters.

        Returns:
            CollectResult: Collection result.
        """
        # Parse arXiv ID
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
            # Fetch paper info from arXiv API
            paper_info = self._fetch_paper_info(arxiv_id)
            if not paper_info:
                return CollectResult(
                    success=False, error=f"Paper not found: {arxiv_id}"
                )

            # Extract content
            content = self._extract_content(paper_info)

            # Use CLI-provided title if available, otherwise use paper title
            final_title = kwargs.pop("title", None) or paper_info["title"]

            # Generate metadata
            metadata = self._generate_metadata(
                title=final_title,
                content=content,
                source=f"arxiv:{arxiv_id}",
                tags=tags or [],
                paper_info=paper_info,
                **kwargs,
            )

            # Generate safe filename
            filename = self._generate_safe_filename("paper", final_title)

            # Save to file
            saved_path = self._save_to_file(
                content=content,
                metadata=metadata,
                filename=filename,
                sub_dir=self._sub_dir,
            )

            # Count words
            word_count = self._count_words(content)

            # Generate content hash
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
        Parse arXiv ID.

        Supports multiple formats:
        - arxiv:2301.12345
        - 2301.12345
        - https://arxiv.org/abs/2301.12345
        - https://arxiv.org/pdf/2301.12345.pdf

        Args:
            source: Original input string.

        Returns:
            Optional[str]: Parsed arXiv ID, or None on failure.
        """
        source = source.strip()

        for pattern in self.ARXIV_ID_PATTERNS:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _fetch_paper_info(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch paper information from arXiv API.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Optional[Dict[str, Any]]: Paper info dictionary, or None on failure.
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
        Parse arXiv API XML response.

        Args:
            xml_content: XML response content.
            arxiv_id: arXiv ID

        Returns:
            Optional[Dict[str, Any]]: Parsed paper information.
        """
        try:
            root = ET.fromstring(xml_content)

            # Find entry element
            entry = root.find("atom:entry", self.ATOM_NS)
            if entry is None:
                return None

            # Check for errors (paper not found case)
            title_elem = entry.find("atom:title", self.ATOM_NS)
            if title_elem is None:
                return None

            title = self._clean_text(title_elem.text or "")
            if not title or title.lower() == "error":
                return None

            # Extract authors
            authors = []
            for author_elem in entry.findall("atom:author", self.ATOM_NS):
                name_elem = author_elem.find("atom:name", self.ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            # Extract abstract
            summary_elem = entry.find("atom:summary", self.ATOM_NS)
            abstract = self._clean_text(summary_elem.text or "") if summary_elem is not None else ""

            # Extract categories
            categories = []
            for category_elem in entry.findall("atom:category", self.ATOM_NS):
                term = category_elem.get("term")
                if term:
                    categories.append(term)

            # Extract publication date
            published_elem = entry.find("atom:published", self.ATOM_NS)
            published_date = ""
            if published_elem is not None and published_elem.text:
                # Format: 2023-01-15T12:00:00Z
                published_date = published_elem.text[:10]  # Take date part only

            # Extract links
            pdf_url = ""
            arxiv_url = ""
            for link_elem in entry.findall("atom:link", self.ATOM_NS):
                link_type = link_elem.get("type", "")
                link_href = link_elem.get("href", "")
                if link_type == "application/pdf":
                    pdf_url = link_href
                elif link_type == "text/html":
                    arxiv_url = link_href

            # If no HTML link found, construct default link
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
        Generate Markdown content from paper information.

        Args:
            paper_info: Paper information dictionary.

        Returns:
            str: Content in Markdown format.
        """
        lines = []

        # Title.
        lines.append(f"# {paper_info['title']}")
        lines.append("")

        # Authors
        if paper_info["authors"]:
            lines.append("## Authors")
            lines.append(", ".join(paper_info["authors"]))
            lines.append("")

        # Abstract
        if paper_info["abstract"]:
            lines.append("## Abstract")
            lines.append(paper_info["abstract"])
            lines.append("")

        # Categories
        if paper_info["categories"]:
            lines.append("## Categories")
            lines.append(", ".join(paper_info["categories"]))
            lines.append("")

        # Links
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
        Generate paper metadata.

        Args:
            title: Paper title.
            content: Document content.
            source: Original data source.
            tags: Tag list.
            paper_info: Paper information dictionary.
            **kwargs: Additional metadata fields.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        paper_info = paper_info or {}

        # Generate unique ID
        arxiv_id = paper_info.get("arxiv_id", "unknown")
        # Replace / with _ to handle old format IDs
        safe_arxiv_id = arxiv_id.replace("/", "_")
        paper_id = f"paper_{safe_arxiv_id}"

        timestamp = datetime.now()

        # Base metadata
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

        # Merge additional metadata
        metadata.update(kwargs)

        return metadata

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text (remove excessive whitespace).

        Args:
            text: Original text.

        Returns:
            str: Cleaned text.
        """
        # Remove newlines and excessive whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
