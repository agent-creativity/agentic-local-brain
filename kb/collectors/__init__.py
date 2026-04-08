"""
收集器模块

负责从各种数据源收集内容，包括：
- 本地文件
- 网页 URL
- 书签
- 学术论文
- 邮件
- 笔记
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
