"""
CLI Wiki Commands

Commands for LLM Wiki generation and management.
Compiles topic clusters into wiki articles using LLM.
"""

import click

from kb.commands.utils import CONFIG_FILE, _get_sqlite_storage
from kb.config import Config


@click.group()
def wiki() -> None:
    """LLM Wiki generation and management."""
    pass


@wiki.command("compile")
@click.option("--force", is_flag=True, help="Regenerate all articles, ignoring staleness")
@click.option("--stale-only", is_flag=True, default=True, help="Only recompile changed topics (default)")
def wiki_compile(force, stale_only):
    """Compile topic clusters into wiki articles."""
    from kb.processors.wiki_compiler import WikiCompiler
    
    config = Config(CONFIG_FILE)
    compiler = WikiCompiler.from_config(config)
    
    click.echo("Compiling wiki articles...")
    result = compiler.compile_all(
        force=force,
        progress_callback=lambda msg: click.echo(f"  {msg}")
    )
    
    click.echo(f"\nDone! Compiled: {result.get('compiled', 0)}, "
               f"Skipped: {result.get('skipped', 0)}, "
               f"Errors: {result.get('errors', 0)}")
    if result.get('entity_cards', 0) > 0:
        click.echo(f"Entity cards: {result.get('entity_cards', 0)}")
    if result.get('categories', 0) > 0:
        click.echo(f"Categories: {result.get('categories', 0)}")


@wiki.command("list")
@click.option("--type", "article_type", type=click.Choice(["topic", "entity", "all"]), default="all", help="Filter by article type")
@click.option("--flat", is_flag=True, help="Show flat list instead of hierarchical view")
def wiki_list(article_type, flat):
    """List compiled wiki articles."""
    storage = _get_sqlite_storage()
    try:
        type_filter = None if article_type == "all" else article_type
        
        if flat:
            # Flat list view (original behavior)
            articles = storage.list_wiki_articles(article_type=type_filter)
            
            if not articles:
                click.echo("No wiki articles found. Run 'localbrain wiki compile' or 'localbrain mine' to generate articles.")
                return
            
            for article in articles:
                type_badge = f"[{article.get('article_type', 'topic')}]"
                title = article.get('title', 'Untitled')
                words = article.get('word_count', 0)
                version = article.get('version', 1)
                click.echo(f"  {type_badge:10s} {title} ({words} words, v{version})")
            
            click.echo(f"\nTotal: {len(articles)} articles")
        else:
            # Hierarchical view
            categories = storage.list_wiki_categories()
            
            if not categories:
                # Fall back to flat view if no categories
                articles = storage.list_wiki_articles(article_type=type_filter)
                
                if not articles:
                    click.echo("No wiki articles found. Run 'localbrain wiki compile' or 'localbrain mine' to generate articles.")
                    return
                
                for article in articles:
                    type_badge = f"[{article.get('article_type', 'topic')}]"
                    title = article.get('title', 'Untitled')
                    words = article.get('word_count', 0)
                    version = article.get('version', 1)
                    click.echo(f"  {type_badge:10s} {title} ({words} words, v{version})")
                
                click.echo(f"\nTotal: {len(articles)} articles")
                return
            
            total_articles = 0
            for category in categories:
                cat_name = category.get('name', 'Uncategorized')
                cat_id = category.get('id')
                click.echo(f"\n📁 {cat_name}")
                
                # Get articles in this category
                cat_articles = storage.list_wiki_articles(category_id=cat_id, article_type=type_filter)
                for article in cat_articles:
                    type_badge = f"[{article.get('article_type', 'topic')}]"
                    title = article.get('title', 'Untitled')
                    words = article.get('word_count', 0)
                    version = article.get('version', 1)
                    click.echo(f"    {type_badge:10s} {title} ({words} words, v{version})")
                    total_articles += 1
            
            # Show uncategorized articles
            uncategorized = storage.list_wiki_articles(category_id=None, article_type=type_filter)
            if uncategorized:
                click.echo(f"\n📁 Uncategorized")
                for article in uncategorized:
                    type_badge = f"[{article.get('article_type', 'topic')}]"
                    title = article.get('title', 'Untitled')
                    words = article.get('word_count', 0)
                    version = article.get('version', 1)
                    click.echo(f"    {type_badge:10s} {title} ({words} words, v{version})")
                    total_articles += 1
            
            click.echo(f"\nTotal: {len(categories)} categories, {total_articles} articles")
    finally:
        storage.close()


@wiki.command("show")
@click.argument("slug")
def wiki_show(slug):
    """Display a wiki article in the terminal."""
    from pathlib import Path
    
    config = Config(CONFIG_FILE)
    storage = _get_sqlite_storage()
    try:
        article = storage.get_wiki_article(slug)
        if not article:
            click.echo(f"Article '{slug}' not found.")
            return
        
        # Read the markdown file
        wiki_dir = config.get_wiki_dir()
        file_path = article.get('file_path', '')
        if file_path:
            full_path = Path(file_path)
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                click.echo(content)
            else:
                click.echo(f"Article file not found at: {full_path}")
        else:
            click.echo(f"Title: {article.get('title', 'Untitled')}")
            click.echo("(No file path recorded)")
    finally:
        storage.close()
