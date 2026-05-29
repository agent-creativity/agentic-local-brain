"""
Collectors module

Collects content from various data sources, including:
- Local files
- Web page URL.
- Bookmarks
- Academic papers
- Emails
- Notes
"""

from kb.collectors.base import BaseCollector, CollectResult
from kb.collectors.bookmark_collector import BookmarkCollector
from kb.collectors.email_collector import EmailCollector
from kb.collectors.file_collector import FileCollector
from kb.collectors.note_collector import NoteCollector
from kb.collectors.paper_collector import PaperCollector
from kb.collectors.webpage_collector import WebpageCollector

__all__ = [
    "BaseCollector",
    "CollectResult",
    "FileCollector",
    "WebpageCollector",
    "BookmarkCollector",
    "NoteCollector",
    "PaperCollector",
    "EmailCollector",
]
