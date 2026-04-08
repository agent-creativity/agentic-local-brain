"""
CLI Command Modules

This package contains the refactored CLI command groups:
- init: Initialization commands
- collect: Collection commands (file, webpage, paper, email, bookmark, note)
- search: Search commands (semantic, keyword, rag, tags)
- manage: Management commands (config, stats, tag, export, test, web)
"""

from kb.commands.init import init
from kb.commands.collect import collect
from kb.commands.search import search
from kb.commands.manage import config, stats, tag, export, test, web

__all__ = ["init", "collect", "search", "config", "stats", "tag", "export", "test", "web"]
