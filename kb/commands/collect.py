"""
CLI Collect Commands

Collection commands for different knowledge sources: file, webpage, paper, email, bookmark, note.
"""

from pathlib import Path
from typing import List, Optional

import click

from kb.commands.utils import CONFIG_FILE, _get_sqlite_storage, _index_content_for_search, _update_markdown_frontmatter
from kb.config import Config


def _split_tags(tags_tuple: tuple) -> List[str]:
    """Split comma-separated tags from CLI input.
    
    Click's multiple=True option allows --tags a --tags b, but users may also
    pass --tags a,b,c which needs to be split into individual tags.
    
    Args:
        tags_tuple: Tuple of tag strings from Click option.
        
    Returns:
        List of individual tag strings.
    """
    result = []
    for tag_str in tags_tuple:
        # Split by comma and strip whitespace
        for part in tag_str.split(','):
            part = part.strip()
            if part:
                result.append(part)
    return result


@click.group()
def collect() -> None:
    """Collect knowledge from various sources."""
    pass


@collect.group()
def file() -> None:
    """Manage local files."""
    pass


@file.command("add")
@click.argument("path", type=click.Path(exists=True))
@click.option("--tags", "-t", multiple=True, help="Add tags (comma-separated or multiple -t)")
@click.option("--title", help="Custom title (default: use filename)")
@click.option("--summary", "-s", default=None, help="Provide a summary for this document")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def file_add(path: str, tags: tuple, title: Optional[str], summary: Optional[str], auto_extract: bool, skip_existing: bool) -> None:
    """Add a local file to the knowledge base."""
    from kb.collectors import FileCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime

    # Split comma-separated tags
    tags = _split_tags(tags)
    
    file_path = Path(path).resolve()
    click.echo(f"Collecting file: {file_path}")

    # Create file collector
    collector = FileCollector()

    # Get storage
    storage = _get_sqlite_storage()

    # Execute collection
    result = collector.collect(
        source=file_path,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )

    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        if auto_extract and result.file_path:
            try:
                with open(result.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            if content:
                config = Config(CONFIG_FILE)
                extraction = TagExtractor.smart_extract(
                    config=config,
                    title=result.title or "",
                    content=content,
                    user_tags=tags if tags else None,
                    user_summary=summary
                )
                final_tags = extraction["tags"]
                final_summary = extraction["summary"]
                # Write extracted tags and summary back to markdown file
                _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
        
        # Save to database
        item_id = result.metadata.get("id") if result.metadata else None
        if item_id:
            storage.add_knowledge(
                id=item_id,
                title=result.title or "Untitled",
                content_type="file",
                source=str(file_path),
                collected_at=datetime.now().isoformat(),
                summary=final_summary,
                word_count=result.word_count,
                file_path=str(result.file_path),
                content_hash=result.content_hash
            )
            if final_tags:
                storage.add_tags(item_id, final_tags)
            
            # Index content for semantic search
            if result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # For PDF files with many pages, use page-aware indexing
                    pdf_pages = None
                    if file_path.suffix.lower() == ".pdf":
                        page_count = collector.get_pdf_page_count(file_path)
                        if page_count > 10:
                            pdf_pages = collector.extract_pdf_pages(file_path)
                    indexed = _index_content_for_search(
                        item_id=item_id,
                        content=content,
                        title=result.title or "Untitled",
                        tags=final_tags,
                        source=str(file_path),
                        content_type="file",
                        pdf_pages=pdf_pages
                    )
                    if indexed:
                        click.echo("  Indexed for semantic search")
                except Exception:
                    pass  # Indexing failure shouldn't break collection

        click.echo("\n✓ Collection successful!")
        click.echo(f"  Title: {result.title}")
        click.echo(f"  Word count: {result.word_count}")
        click.echo(f"  Saved to: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"\n✗ Collection failed: {result.error}")
        raise SystemExit(1)


@collect.group()
def webpage() -> None:
    """Manage webpage content."""
    pass


@webpage.command("add")
@click.argument("url")
@click.option("--tags", "-t", multiple=True, help="Add tags (comma-separated or multiple -t)")
@click.option("--title", help="Custom title (default: use webpage title)")
@click.option("--summary", "-s", default=None, help="Provide a summary for this document")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def webpage_add(url: str, tags: tuple, title: Optional[str], summary: Optional[str], auto_extract: bool, skip_existing: bool) -> None:
    """Add a webpage to the knowledge base."""
    from kb.collectors import WebpageCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime

    # Split comma-separated tags
    tags = _split_tags(tags)
    
    click.echo(f"Collecting webpage: {url}")

    # Create webpage collector
    collector = WebpageCollector()

    # Get storage
    storage = _get_sqlite_storage()

    # Execute collection
    result = collector.collect(
        source=url,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )

    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        if auto_extract and result.file_path:
            try:
                with open(result.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            if content:
                config = Config(CONFIG_FILE)
                extraction = TagExtractor.smart_extract(
                    config=config,
                    title=result.title or "",
                    content=content,
                    user_tags=tags if tags else None,
                    user_summary=summary
                )
                final_tags = extraction["tags"]
                final_summary = extraction["summary"]
                # Write extracted tags and summary back to markdown file
                _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
        
        # Save to database
        item_id = result.metadata.get("id") if result.metadata else None
        if item_id:
            storage.add_knowledge(
                id=item_id,
                title=result.title or "Untitled",
                content_type="webpage",
                source=url,
                collected_at=datetime.now().isoformat(),
                summary=final_summary,
                word_count=result.word_count,
                file_path=str(result.file_path),
                content_hash=result.content_hash
            )
            if final_tags:
                storage.add_tags(item_id, final_tags)
            
            # Index content for semantic search
            if result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    indexed = _index_content_for_search(
                        item_id=item_id,
                        content=content,
                        title=result.title or "Untitled",
                        tags=final_tags,
                        source=url,
                        content_type="webpage"
                    )
                    if indexed:
                        click.echo("  Indexed for semantic search")
                except Exception:
                    pass  # Indexing failure shouldn't break collection
        
        click.echo("\n✓ Collection successful!")
        click.echo(f"  Title: {result.title}")
        click.echo(f"  Word count: {result.word_count}")
        click.echo(f"  Saved to: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"\n✗ Collection failed: {result.error}")
        raise SystemExit(1)


@collect.group()
def paper() -> None:
    """Manage academic papers."""
    pass


@paper.command("add")
@click.argument("source")
@click.option("--tags", "-t", multiple=True, help="Add tags (comma-separated or multiple -t)")
@click.option("--title", help="Custom title (default: use paper title)")
@click.option("--summary", "-s", default=None, help="Provide a summary for this document")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def paper_add(source: str, tags: tuple, title: Optional[str], summary: Optional[str], auto_extract: bool, skip_existing: bool) -> None:
    """Add an academic paper (arxiv:ID or URL)."""
    from kb.collectors import PaperCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime

    # Split comma-separated tags
    tags = _split_tags(tags)
    
    click.echo(f"Collecting paper: {source}")

    # Create paper collector
    collector = PaperCollector()

    # Get storage
    storage = _get_sqlite_storage()

    # Execute collection
    result = collector.collect(
        source=source,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )

    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        if auto_extract and result.file_path:
            try:
                with open(result.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            if content:
                config = Config(CONFIG_FILE)
                extraction = TagExtractor.smart_extract(
                    config=config,
                    title=result.title or "",
                    content=content,
                    user_tags=tags if tags else None,
                    user_summary=summary
                )
                final_tags = extraction["tags"]
                final_summary = extraction["summary"]
                # Write extracted tags and summary back to markdown file
                _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
        
        # Save to database
        item_id = result.metadata.get("id") if result.metadata else None
        if item_id:
            storage.add_knowledge(
                id=item_id,
                title=result.title or "Untitled",
                content_type="paper",
                source=source,
                collected_at=datetime.now().isoformat(),
                summary=final_summary,
                word_count=result.word_count,
                file_path=str(result.file_path),
                content_hash=result.content_hash
            )
            if final_tags:
                storage.add_tags(item_id, final_tags)
            
            # Index content for semantic search
            if result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    indexed = _index_content_for_search(
                        item_id=item_id,
                        content=content,
                        title=result.title or "Untitled",
                        tags=final_tags,
                        source=source,
                        content_type="paper"
                    )
                    if indexed:
                        click.echo("  Indexed for semantic search")
                except Exception:
                    pass  # Indexing failure shouldn't break collection
        
        click.echo("\n✓ Collection successful!")
        click.echo(f"  Title: {result.title}")
        click.echo(f"  Word count: {result.word_count}")
        click.echo(f"  Saved to: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"\n✗ Collection failed: {result.error}")
        raise SystemExit(1)


@collect.group()
def email() -> None:
    """Manage emails."""
    pass


@email.command("add")
@click.argument("path", type=click.Path(exists=True))
@click.option("--tags", "-t", multiple=True, help="Add tags (comma-separated or multiple -t)")
@click.option("--title", help="Custom title (default: use email subject)")
@click.option("--summary", "-s", default=None, help="Provide a summary for this document")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def email_add(path: str, tags: tuple, title: Optional[str], summary: Optional[str], auto_extract: bool, skip_existing: bool) -> None:
    """Add from email file (.eml or .mbox)."""
    from kb.collectors import EmailCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime

    # Split comma-separated tags
    tags = _split_tags(tags)
    
    email_path = Path(path).resolve()
    click.echo(f"Collecting email: {email_path}")

    # Create email collector
    collector = EmailCollector()

    # Get storage
    storage = _get_sqlite_storage()

    # Execute collection
    result = collector.collect(
        source=email_path,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )

    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        # Check if this is a batch MBOX collection
        individual_results = result.metadata.get("individual_results", [])
        if individual_results:
            # MBOX batch collection - register each email to database
            for single_result in individual_results:
                single_id = single_result.metadata.get("id") if single_result.metadata else None
                if single_id:
                    storage.add_knowledge(
                        id=single_id,
                        title=single_result.title or "Untitled",
                        content_type="email",
                        source=str(email_path),
                        collected_at=datetime.now().isoformat(),
                        summary=final_summary,
                        word_count=single_result.word_count,
                        file_path=str(single_result.file_path),
                        content_hash=single_result.content_hash
                    )
                    if final_tags:
                        storage.add_tags(single_id, final_tags)
                    
                    # Index content for semantic search
                    if single_result.file_path:
                        try:
                            with open(single_result.file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            _index_content_for_search(
                                item_id=single_id,
                                content=content,
                                title=single_result.title or "Untitled",
                                tags=final_tags,
                                source=str(email_path),
                                content_type="email"
                            )
                        except Exception:
                            pass  # Indexing failure shouldn't break collection
        else:
            # Single email collection
            if auto_extract and result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    content = ""
                
                if content:
                    config = Config(CONFIG_FILE)
                    extraction = TagExtractor.smart_extract(
                        config=config,
                        title=result.title or "",
                        content=content,
                        user_tags=tags if tags else None,
                        user_summary=summary
                    )
                    final_tags = extraction["tags"]
                    final_summary = extraction["summary"]
                    # Write extracted tags and summary back to markdown file
                    _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
            # Save to database
            item_id = result.metadata.get("id") if result.metadata else None
            if item_id:
                storage.add_knowledge(
                    id=item_id,
                    title=result.title or "Untitled",
                    content_type="email",
                    source=str(email_path),
                    collected_at=datetime.now().isoformat(),
                    summary=final_summary,
                    word_count=result.word_count,
                    file_path=str(result.file_path),
                    content_hash=result.content_hash
                )
                if final_tags:
                    storage.add_tags(item_id, final_tags)
                
                # Index content for semantic search
                if result.file_path:
                    try:
                        with open(result.file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        indexed = _index_content_for_search(
                            item_id=item_id,
                            content=content,
                            title=result.title or "Untitled",
                            tags=final_tags,
                            source=str(email_path),
                            content_type="email"
                        )
                        if indexed:
                            click.echo("  Indexed for semantic search")
                    except Exception:
                        pass  # Indexing failure shouldn't break collection
        
        click.echo("\n✓ Collection successful!")
        click.echo(f"  Title: {result.title}")
        click.echo(f"  Word count: {result.word_count}")
        click.echo(f"  Saved to: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"\n✗ Collection failed: {result.error}")
        raise SystemExit(1)


@collect.group()
def bookmark() -> None:
    """Manage bookmarks."""
    pass


@bookmark.command("add")
@click.argument("url")
@click.option("--tags", "-t", multiple=True, help="Add tags (comma-separated or multiple -t)")
@click.option("--title", default=None, help="Custom title")
@click.option("--summary", "-s", default=None, help="Provide a summary for this bookmark")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def bookmark_add(url, tags, title, summary, auto_extract, skip_existing):
    """Add a single bookmark with optional auto-extraction."""
    from kb.collectors import BookmarkCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime
    
    # Split comma-separated tags
    tags = _split_tags(tags)
    
    config = Config(CONFIG_FILE)
    output_dir = config.get("storage.base_dir", None)
    collector = BookmarkCollector(output_dir=output_dir)
    
    # Get storage
    storage = _get_sqlite_storage()
    
    result = collector.collect_single_url(
        url=url,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )
    
    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        if auto_extract and result.file_path:
            try:
                with open(result.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            if content:
                extraction = TagExtractor.smart_extract(
                    config=config,
                    title=result.title or "",
                    content=content,
                    user_tags=tags if tags else None,
                    user_summary=summary
                )
                final_tags = extraction["tags"]
                final_summary = extraction["summary"]
                # Write extracted tags and summary back to markdown file
                _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
        
        # Save to database
        item_id = result.metadata.get("id") if result.metadata else None
        if item_id:
            storage.add_knowledge(
                id=item_id,
                title=result.title or "Untitled",
                content_type="bookmark",
                source=url,
                collected_at=datetime.now().isoformat(),
                summary=final_summary,
                word_count=result.word_count,
                file_path=str(result.file_path),
                content_hash=result.content_hash
            )
            if final_tags:
                storage.add_tags(item_id, final_tags)
            
            # Index content for semantic search
            if result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    indexed = _index_content_for_search(
                        item_id=item_id,
                        content=content,
                        title=result.title or "Untitled",
                        tags=final_tags,
                        source=url,
                        content_type="bookmark"
                    )
                    if indexed:
                        click.echo("  Indexed for semantic search")
                except Exception:
                    pass  # Indexing failure shouldn't break collection
        
        click.echo(f"Bookmark added: {result.title}")
        click.echo(f"  File: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"Failed to add bookmark: {result.error}", err=True)
        raise SystemExit(1)


@bookmark.command("import")
@click.option("--browser", type=click.Choice(["chrome", "edge", "firefox", "safari"]),
              help="Browser to import bookmarks from")
@click.option("--file", "-f", "bookmark_file", type=click.Path(exists=True),
              help="Import from HTML bookmark export file")
@click.option("--tags", "-t", multiple=True, help="Add tags to all imported bookmarks (comma-separated or multiple -t)")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def bookmark_import(browser, bookmark_file, tags, auto_extract, skip_existing):
    """Import bookmarks from browser or HTML file."""
    from kb.collectors import BookmarkCollector
    from kb.processors.tag_extractor import TagExtractor
    from datetime import datetime
    
    # Split comma-separated tags
    tags = _split_tags(tags)
    
    if not browser and not bookmark_file:
        click.echo("Error: Please specify --browser or --file", err=True)
        raise SystemExit(1)
    
    config = Config(CONFIG_FILE)
    output_dir = config.get("storage.base_dir", None)
    collector = BookmarkCollector(output_dir=output_dir)
    
    # Get storage
    storage = _get_sqlite_storage()
    
    if bookmark_file:
        click.echo(f"Importing bookmarks from file: {bookmark_file}")
        results = collector.collect_from_file(
            html_file=bookmark_file,
            skip_existing=skip_existing,
            storage=storage
        )
    else:
        click.echo(f"Collecting bookmarks from {browser}...")
        results = collector.collect_from_browser(
            browser=browser,
            skip_existing=skip_existing,
            storage=storage
        )
    
    # Save each successful result to database
    for result in results:
        if result.success:
            final_tags = tags if tags else []
            final_summary = ""
            
            if auto_extract and result.file_path:
                try:
                    with open(result.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if content:
                        extraction = TagExtractor.smart_extract(
                            config=config,
                            title=result.title or "",
                            content=content,
                            user_tags=tags if tags else None,
                            user_summary=None
                        )
                        final_tags = extraction["tags"]
                        final_summary = extraction["summary"]
                        # Write extracted tags and summary back to markdown file
                        _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
                except Exception:
                    pass
            
            # Save to database
            item_id = result.metadata.get("id") if result.metadata else None
            if item_id:
                storage.add_knowledge(
                    id=item_id,
                    title=result.title or "Untitled",
                    content_type="bookmark",
                    source=result.metadata.get("url", ""),
                    collected_at=datetime.now().isoformat(),
                    summary=final_summary,
                    word_count=result.word_count,
                    file_path=str(result.file_path),
                    content_hash=result.content_hash
                )
                if final_tags:
                    storage.add_tags(item_id, final_tags)
                
                # Index content for semantic search
                if result.file_path:
                    try:
                        with open(result.file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        _index_content_for_search(
                            item_id=item_id,
                            content=content,
                            title=result.title or "Untitled",
                            tags=final_tags,
                            source=result.metadata.get("url", ""),
                            content_type="bookmark"
                        )
                    except Exception:
                        pass  # Indexing failure shouldn't break collection
    
    success_count = sum(1 for r in results if r.success)
    click.echo(f"\n✓ Imported {success_count}/{len(results)} bookmarks")


@collect.group()
def note() -> None:
    """Manage notes."""
    pass


@note.command("add")
@click.argument("text")
@click.option("--title", "-t", help="Note title (auto-generated by default)")
@click.option("--tags", "-T", multiple=True, help="Add tags (comma-separated or multiple -T)")
@click.option("--summary", "-s", default=None, help="Provide a summary for this note")
@click.option("--auto-extract/--no-auto-extract", default=True,
              help="Auto-extract tags and summary if not provided (default: enabled)")
@click.option("--skip-existing", is_flag=True, default=False, help="Skip if already collected")
def note_add(text: str, title: Optional[str], tags: tuple, summary: Optional[str], auto_extract: bool, skip_existing: bool) -> None:
    """Add a note to the knowledge base."""
    from kb.collectors import NoteCollector
    from kb.processors.tag_extractor import TagExtractor
    
    # Split comma-separated tags
    tags = _split_tags(tags)
    
    click.echo("Saving note...")

    # Create note collector
    collector = NoteCollector()

    # Get storage
    storage = _get_sqlite_storage()

    # Execute collection
    result = collector.collect(
        text=text,
        tags=tags if tags else None,
        title=title,
        skip_existing=skip_existing,
        storage=storage
    )

    if result.success:
        # Smart extraction: user-provided > LLM > built-in
        final_tags = tags if tags else []
        final_summary = summary or ""
        
        if auto_extract:
            config = Config(CONFIG_FILE)
            extraction = TagExtractor.smart_extract(
                config=config,
                title=result.title or "",
                content=text,
                user_tags=tags if tags else None,
                user_summary=summary
            )
            final_tags = extraction["tags"]
            final_summary = extraction["summary"]
            # Write extracted tags and summary back to markdown file
            _update_markdown_frontmatter(result.file_path, final_tags, final_summary)
        
        # Save to database
        from datetime import datetime
        note_id = result.metadata.get("id") if result.metadata else None
        if note_id:
            storage.add_knowledge(
                id=note_id,
                title=result.title or "Untitled",
                content_type="note",
                source="manual_input",
                collected_at=datetime.now().isoformat(),
                summary=final_summary,
                word_count=result.word_count,
                file_path=str(result.file_path),
                content_hash=result.content_hash
            )
            if final_tags:
                storage.add_tags(note_id, final_tags)
            
            # Index content for semantic search
            indexed = _index_content_for_search(
                item_id=note_id,
                content=text,
                title=result.title or "Untitled",
                tags=final_tags,
                source="manual_input",
                content_type="note"
            )
            if indexed:
                click.echo("  Indexed for semantic search")
        
        click.echo("\n✓ Note saved successfully!")
        click.echo(f"  Title: {result.title}")
        click.echo(f"  Word count: {result.word_count}")
        click.echo(f"  Saved to: {result.file_path}")
        if final_tags:
            click.echo(f"  Tags: {', '.join(final_tags)}")
        if final_summary:
            click.echo(f"  Summary: {final_summary}")
    else:
        # Handle duplicate case gracefully
        if "Duplicate" in result.error:
            click.echo(f"Skipped (duplicate): {result.error}")
            return
        click.echo(f"\n✗ Failed to save note: {result.error}")
        raise SystemExit(1)
