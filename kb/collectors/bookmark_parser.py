"""
Bookmark parser module

Supports parsing multiple browser bookmark formats:
- Chrome/Edge: JSON format
- HTML export: Netscape Bookmark File format
- Safari: plist format (optional)
"""

from __future__ import annotations

import json
import plistlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class BookmarkItem:
    """
    Bookmark data item.

    Attributes:
        title: Bookmark title.
        url: Bookmark URL.
        folder_path: Folder path hierarchy, e.g. ["Tech", "Python"].
        added_date: Date added (timestamp or ISO format string).
        metadata: Additional metadata.
    """

    title: str
    url: str
    folder_path: List[str] = field(default_factory=list)
    added_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"BookmarkItem(title={self.title}, url={self.url}, folder={self.folder_path})"


class ChromeBookmarkParser:
    """
    Chrome/Edge bookmark parser.

    Chrome and Edge store bookmarks in JSON format files.
    """

    def __init__(self) -> None:
        """Initialize Chrome bookmark parser."""
        self._bookmarks: List[BookmarkItem] = []

    def parse_file(self, file_path: str | Path) -> List[BookmarkItem]:
        """Parse Chrome bookmark file."""
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"书签文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "roots" not in data:
            raise ValueError("无效的 Chrome 书签文件格式：缺少 'roots' 字段")

        self._bookmarks = []

        roots = data["roots"]
        for root_name in ["bookmark_bar", "other", "synced"]:
            if root_name in roots:
                root_folder = roots[root_name]
                children = root_folder.get("children", [])
                for child in children:
                    self._parse_node(child, folder_path=[])

        return self._bookmarks

    def parse_dict(self, data: Dict[str, Any]) -> List[BookmarkItem]:
        """Parse bookmark dictionary data."""
        if "roots" not in data:
            raise ValueError("无效的 Chrome 书签数据格式")

        self._bookmarks = []

        roots = data["roots"]
        for root_name in ["bookmark_bar", "other", "synced"]:
            if root_name in roots:
                root_folder = roots[root_name]
                children = root_folder.get("children", [])
                for child in children:
                    self._parse_node(child, folder_path=[])

        return self._bookmarks

    def _parse_node(
        self,
        node: Dict[str, Any],
        folder_path: List[str],
    ) -> None:
        """Recursively parse bookmark nodes."""
        if node.get("type") == "url":
            bookmark = BookmarkItem(
                title=node.get("name", "无标题"),
                url=node.get("url", ""),
                folder_path=folder_path.copy(),
                added_date=self._convert_chrome_timestamp(node.get("date_added")),
                metadata={
                    "date_modified": self._convert_chrome_timestamp(node.get("date_modified")),
                },
            )
            if bookmark.url and self._is_valid_url(bookmark.url):
                self._bookmarks.append(bookmark)

        elif node.get("type") == "folder":
            folder_name = node.get("name", "未命名文件夹")
            new_folder_path = folder_path + [folder_name]

            children = node.get("children", [])
            for child in children:
                self._parse_node(child, folder_path=new_folder_path)

    @staticmethod
    def _convert_chrome_timestamp(timestamp: Optional[str]) -> Optional[str]:
        """Convert Chrome timestamp to ISO format."""
        if not timestamp:
            return None

        try:
            from datetime import datetime, timezone, timedelta

            chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
            microseconds = int(timestamp)
            delta = timedelta(microseconds=microseconds)
            dt = chrome_epoch + delta
            local_dt = dt.astimezone()

            return local_dt.isoformat()

        except (ValueError, TypeError, OverflowError):
            return None

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False


class HTMLBookmarkParser:
    """
    HTML bookmark file parser.

    Parses Netscape Bookmark File format HTML export files.
    Uses regex parsing since this HTML format is typically non-standard.
    """

    def __init__(self) -> None:
        """Initialize HTML bookmark parser."""
        self._bookmarks: List[BookmarkItem] = []

    def parse_file(self, file_path: str | Path) -> List[BookmarkItem]:
        """Parse HTML bookmark file."""
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"书签文件不存在: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self.parse_html(content)

    def parse_html(self, html_content: str) -> List[BookmarkItem]:
        """Parse HTML content."""
        self._bookmarks = []

        # Check if DL tag is present
        if "<DL>" not in html_content.upper():
            raise ValueError("无效的书签 HTML 格式：未找到 <DL> 元素")

        # Parse using regex
        self._parse_html_regex(html_content, folder_path=[])

        return self._bookmarks

    def _parse_html_regex(
        self,
        html_content: str,
        folder_path: List[str],
    ) -> None:
        """Recursively parse HTML bookmarks using regex."""
        # Use simple string search method
        pos = 0
        html_upper = html_content.upper()
        
        while pos < len(html_content):
            # Find next <DT>
            dt_start = html_upper.find('<DT>', pos)
            if dt_start == -1:
                break
            
            # Find current <DT>'s end boundary: next <DT> or </DL>
            search_from = dt_start + 4
            next_dt = html_upper.find('<DT>', search_from)
            next_dl_close = html_upper.find('</DL>', search_from)

            candidates = [c for c in (next_dt, next_dl_close) if c != -1]
            dt_end = min(candidates) if candidates else len(html_content)

            dt_content = html_content[dt_start + 4:dt_end]
            pos = dt_end
            
            # Check if it's a folder
            h3_start = dt_content.upper().find('<H3')
            if h3_start != -1:
                # It's a folder
                h3_end = dt_content.upper().find('</H3>', h3_start)
                if h3_end != -1:
                    folder_name = dt_content[h3_start:h3_end + 5]
                    # Extract folder name
                    import re
                    folder_match = re.search(r'<H3[^>]*>(.*?)</H3>', folder_name, re.IGNORECASE | re.DOTALL)
                    if folder_match:
                        folder_name = folder_match.group(1).strip()
                        new_folder_path = folder_path + [folder_name]
                        
                        # Find DL following H3 (search in original html after </H3>)
                        h3_abs_end = dt_start + 4 + h3_end + 5
                        remaining = html_content[h3_abs_end:]
                        dl_start = remaining.upper().find('<DL>')
                        if dl_start != -1:
                            # Find matching </DL>
                            dl_content_start = dl_start + 4
                            dl_depth = 1
                            dl_pos = dl_content_start
                            while dl_pos < len(remaining) and dl_depth > 0:
                                next_open = remaining.upper().find('<DL>', dl_pos)
                                next_close = remaining.upper().find('</DL>', dl_pos)
                                
                                if next_close == -1:
                                    break
                                
                                if next_open != -1 and next_open < next_close:
                                    dl_depth += 1
                                    dl_pos = next_open + 4
                                else:
                                    dl_depth -= 1
                                    if dl_depth == 0:
                                        dl_content = remaining[dl_content_start:next_close]
                                        self._parse_html_regex(dl_content, folder_path=new_folder_path)
                                        # Skip the entire </DL> tag
                                        pos = h3_abs_end + next_close + 5
                                        break
                                    dl_pos = next_close + 5
                continue
            
            # Check if it's a bookmark
            a_start = dt_content.upper().find('<A ')
            if a_start != -1:
                import re
                bookmark_match = re.search(
                    r'<A\s+HREF=["\']([^"\']*)["\'][^>]*>(.*?)</A>',
                    dt_content,
                    re.IGNORECASE | re.DOTALL
                )
                if bookmark_match:
                    url = bookmark_match.group(1).strip()
                    title = bookmark_match.group(2).strip()
                    
                    # Extract ADD_DATE
                    add_date = None
                    add_date_match = re.search(r'ADD_DATE=["\']?(\d+)["\']?', dt_content, re.IGNORECASE)
                    if add_date_match:
                        add_date = add_date_match.group(1)
                    
                    bookmark = BookmarkItem(
                        title=title,
                        url=url,
                        folder_path=folder_path.copy(),
                        added_date=self._convert_html_timestamp(add_date),
                    )
                    if self._is_valid_url(bookmark.url):
                        self._bookmarks.append(bookmark)

    @staticmethod
    def _convert_html_timestamp(timestamp: Optional[str]) -> Optional[str]:
        """Convert HTML timestamp (Unix) to ISO format."""
        if not timestamp:
            return None

        try:
            from datetime import datetime, timezone

            ts = int(timestamp)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            local_dt = dt.astimezone()
            return local_dt.isoformat()

        except (ValueError, TypeError, OverflowError, OSError):
            return None

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False


class SafariBookmarkParser:
    """
    Safari bookmark parser (optional).

    Safari stores bookmarks in plist format (binary or XML).
    """

    def __init__(self) -> None:
        """Initialize Safari bookmark parser."""
        self._bookmarks: List[BookmarkItem] = []

    def parse_file(self, file_path: str | Path) -> List[BookmarkItem]:
        """Parse Safari bookmarks plist file."""
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"书签文件不存在: {file_path}")

        try:
            with open(file_path, "rb") as f:
                data = plistlib.load(f)
        except Exception as e:
            raise ValueError(f"无法解析 plist 文件: {str(e)}")

        self._bookmarks = []
        self._parse_plist(data)

        return self._bookmarks

    def _parse_plist(
        self,
        data: Any,
        folder_path: Optional[List[str]] = None,
    ) -> None:
        """Recursively parse plist data."""
        if folder_path is None:
            folder_path = []

        if isinstance(data, dict):
            if data.get("WebBookmarkType") == "WebBookmarkTypeLeaf":
                title = data.get("URIDictionary", {}).get("title", "无标题")
                url = data.get("URLString", "")

                bookmark = BookmarkItem(
                    title=title,
                    url=url,
                    folder_path=folder_path.copy(),
                    added_date=data.get("DateLastVisited"),
                )
                if self._is_valid_url(bookmark.url):
                    self._bookmarks.append(bookmark)

            elif data.get("WebBookmarkType") == "WebBookmarkTypeList":
                folder_name = data.get("Title", "未命名文件夹")
                new_folder_path = folder_path + [folder_name]

                children = data.get("Children", [])
                for child in children:
                    self._parse_plist(child, folder_path=new_folder_path)

        elif isinstance(data, list):
            for item in data:
                self._parse_plist(item, folder_path=folder_path)

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False
