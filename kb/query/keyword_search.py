"""
Keyword search module

Keyword-based text matching search, supporting ripgrep or glob + file content matching.
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
    Keyword search class.

    Provides keyword-based text matching search. Supports fast search using ripgrep, 
    or glob + file content matching as a fallback.

    Usage examples:
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
        Initialize keyword search.

        Args:
            data_dir: Data directory path; search will be performed in this directory and subdirectories.
            use_ripgrep: Whether to use ripgrep for search, defaults to True.
            limit: Default result count limit, defaults to 10.

        Raises:
            ValueError: Data directory does not exist.
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
        Check if ripgrep is available.

        Returns:
            bool: Returns True if ripgrep is available.
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
        Execute keyword search.

        Searches for files containing the specified keywords in the data directory, returning matching file paths and content summaries.

        Args:
            keywords: Search keywords, supports multiple keywords (space-separated).
            content_type: Content type filter, optional values:
                         - "files": Search files only
                         - "urls": Search web content only
                         - "bookmarks": Search bookmarks only
                         - "notes": Search notes only
                         - None: Search all types
            limit: Result count limit; uses default value if not provided.

        Returns:
            List[SearchResult]: List of search results, each containing file path and content summary.

        Raises:
            ValueError: Keywords are empty.
            Exception: Error occurred during search.
        """
        if not keywords or not keywords.strip():
            raise ValueError("Keywords cannot be empty")

        if limit is None:
            limit = self.default_limit

        try:
            # Determine search directory
            search_dir = self._get_search_directory(content_type)

            # Execute search
            if self.use_ripgrep:
                raw_results = self._search_with_ripgrep(keywords, search_dir, limit)
            else:
                raw_results = self._search_with_glob(keywords, search_dir, limit)

            # Convert to SearchResult
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
        Get search directory based on content type.

        Args:
            content_type: Content type.

        Returns:
            Path: Search directory path.
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

        # If specified type does not exist, fall back to entire data directory
        return self.data_dir

    def _search_with_ripgrep(
        self, keywords: str, search_dir: Path, limit: int
    ) -> List[Dict[str, str]]:
        """
        Execute search using ripgrep.

        Args:
            keywords: Search keywords.
            search_dir: Search directory.
            limit: Result limit.

        Returns:
            List[Dict[str, str]]: List of raw search results.
        """
        try:
            # Build ripgrep command
            # --json: Output in JSON format
            # --max-count: Max matches per file
            # --no-heading: Don't show heading
            # --with-filename: Show filename
            cmd = [
                "rg",
                "--json",
                "--max-count",
                "3",  # Max 3 matches per file
                "--no-heading",
                "--with-filename",
                "--ignore-case",
                "--glob",
                "!*.json",  # Ignore JSON metadata files
                keywords,
                str(search_dir),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode not in [0, 1]:  # 0=match found, 1=no match found
                logger.warning(
                    f"ripgrep returned code {result.returncode}: {result.stderr}"
                )
                return []

            # Parse JSON output
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
        Parse ripgrep JSON output.

        Args:
            output: JSON output from ripgrep.
            limit: Result limit.

        Returns:
            List[Dict[str, str]]: Parsed search results.
        """
        results = []
        seen_files = set()

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            try:
                data = json.loads(line)

                # Only process matching lines
                if data.get("type") != "match":
                    continue

                match_data = data.get("data", {})
                file_path = match_data.get("path", {}).get("text", "")
                text = match_data.get("lines", {}).get("text", "")

                # Deduplicate
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
        Execute search using glob + file content matching (fallback).

        Args:
            keywords: Search keywords.
            search_dir: Search directory.
            limit: Result limit.

        Returns:
            List[Dict[str, str]]: List of raw search results.
        """
        results = []
        seen_files = set()

        # Split keywords into list
        keyword_list = keywords.lower().split()

        try:
            # Recursively search all text files
            for file_path in search_dir.rglob("*"):
                if len(results) >= limit:
                    break

                # Only process text files
                if not file_path.is_file():
                    continue

                # Skip binary files and metadata files
                if file_path.suffix in [".json", ".db", ".lock"]:
                    continue

                if file_path.name.startswith("."):
                    continue

                try:
                    # Read file content
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    # Check if contains all keywords
                    content_lower = content.lower()
                    if all(kw in content_lower for kw in keyword_list):
                        if str(file_path) not in seen_files:
                            seen_files.add(str(file_path))

                            # Extract context containing keywords
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
        Extract context containing keywords from file content.

        Args:
            content: Complete file content.
            keywords: List of keywords.
            context_lines: Number of context lines.

        Returns:
            str: Context text containing keywords.
        """
        lines = content.split("\n")
        context_parts = []

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if contains any keyword
            if any(kw in line_lower for kw in keywords):
                # Get context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)

                context = "\n".join(lines[start:end])
                context_parts.append(context)

                # Only return the first 3 matching contexts
                if len(context_parts) >= 3:
                    break

        if context_parts:
            return "\n...\n".join(context_parts)

        # If no specific context found, return beginning portion
        return content[:500] + "..." if len(content) > 500 else content

    def _convert_to_search_results(
        self, raw_results: List[Dict[str, str]]
    ) -> List[SearchResult]:
        """
        Convert raw search results to SearchResult list.

        Args:
            raw_results: List of raw search results.

        Returns:
            List[SearchResult]: List of converted search results.
        """
        results = []

        for i, raw in enumerate(raw_results):
            file_path = raw.get("file_path", "")
            content = raw.get("content", "")

            # Create relative path as ID
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
                score=1.0 - (i * 0.1),  # Simple scoring: higher rank = higher score
            )
            results.append(result)

        return results

    def _detect_content_type(self, file_path: str) -> str:
        """
        Detect content type based on file path.

        Args:
            file_path: File path.

        Returns:
            str: Content type.
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
