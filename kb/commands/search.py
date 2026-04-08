"""
CLI Search Commands

Search commands: semantic, keyword, rag, tags.
"""

from typing import Optional

import click

from kb.commands.utils import CONFIG_FILE
from kb.config import Config


@click.group()
def search():
    """Search and query your knowledge base."""
    pass


@search.command("semantic")
@click.argument("question")
@click.option("--tags", "-t", multiple=True, help="Filter by tags")
@click.option("--top-k", "-k", type=int, default=5, help="Number of results to return (default: 5)")
def search_semantic(question: str, tags: tuple, top_k: int) -> None:
    """Semantic search: retrieve relevant documents based on vector similarity"""
    from kb.query.semantic_search import SemanticSearch

    click.echo(f"Searching: {question}")
    if tags:
        click.echo(f"Tag filter: {', '.join(tags)}")

    try:
        config = Config(CONFIG_FILE)
        
        # Validate services and warn user if not configured
        service_status = config.validate_services()
        if not service_status.get("embedding_available"):
            click.echo(click.style("Warning: ", fg="yellow") + "Embedding service not configured. Semantic search will fail.")
        
        search = SemanticSearch(config)

        results = search.search(
            query=question,
            tags=list(tags) if tags else None,
            top_k=top_k,
        )

        if not results:
            click.echo("\nNo relevant results found.")
            return

        click.echo(f"\nFound {len(results)} relevant results:\n")
        for i, result in enumerate(results, 1):
            click.echo(f"[{i}] Similarity: {result.score:.3f}")
            click.echo(f"    ID: {result.id}")
            if result.metadata.get("source"):
                click.echo(f"    Source: {result.metadata['source']}")
            if result.metadata.get("tags"):
                click.echo(f"    Tags: {', '.join(result.metadata['tags'])}")
            click.echo(f"    Content: {result.content[:200]}...")
            click.echo()

    except Exception as e:
        click.echo(f"\nSearch failed: {e}")
        raise SystemExit(1)


@search.command("keyword")
@click.argument("keywords")
@click.option("--type", "-t", "content_type", type=str, help="Filter by content type")
@click.option("--limit", "-l", type=int, default=10, help="Number of results to return (default: 10)")
def search_keyword(keywords: str, content_type: Optional[str], limit: int) -> None:
    """Keyword search: retrieve files based on text matching"""
    from kb.query.keyword_search import KeywordSearch

    click.echo(f"Searching keywords: {keywords}")
    if content_type:
        click.echo(f"Type filter: {content_type}")

    try:
        config = Config(CONFIG_FILE)
        search = KeywordSearch(str(config.data_dir))

        results = search.search(
            keywords=keywords,
            content_type=content_type,
            limit=limit,
        )

        if not results:
            click.echo("\nNo results found.")
            return

        click.echo(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            click.echo(f"[{i}] Score: {result.score:.3f}")
            click.echo(f"    ID: {result.id}")
            click.echo(f"    Title: {result.metadata.get('title', 'N/A')}")
            if result.metadata.get("source"):
                click.echo(f"    Source: {result.metadata['source']}")
            if result.metadata.get("tags"):
                click.echo(f"    Tags: {', '.join(result.metadata['tags'])}")
            click.echo(f"    Content: {result.content[:200]}...")
            click.echo()

    except Exception as e:
        click.echo(f"\nSearch failed: {e}")
        raise SystemExit(1)


@search.command("rag")
@click.argument("question")
@click.option("--tags", "-t", multiple=True, help="Filter by tags")
@click.option("--top-k", "-k", type=int, default=5, help="Number of context documents (default: 5)")
def search_rag(question: str, tags: tuple, top_k: int) -> None:
    """RAG query: get AI-generated answer based on your knowledge base"""
    from kb.query.rag import RAGQuery

    click.echo(f"Question: {question}")
    if tags:
        click.echo(f"Tag filter: {', '.join(tags)}")

    try:
        config = Config(CONFIG_FILE)
        
        # Validate services and warn user if not configured
        service_status = config.validate_services()
        if not service_status.get("embedding_available"):
            click.echo(click.style("Warning: ", fg="yellow") + "Embedding service not configured. RAG will use keyword fallback.")
        if not service_status.get("llm_available"):
            click.echo(click.style("Warning: ", fg="yellow") + "LLM service not configured. RAG will return search results without AI answer.")
        
        rag = RAGQuery(config)

        result = rag.query(
            question=question,
            tags=list(tags) if tags else None,
            top_k=top_k,
        )

        click.echo("\n" + "=" * 60)
        click.echo("ANSWER:")
        click.echo("=" * 60)
        if result.answer:
            click.echo(result.answer)
        else:
            click.echo("No answer generated (LLM service not available)")

        click.echo("\n" + "=" * 60)
        click.echo(f"SOURCES ({len(result.sources)}):")
        click.echo("=" * 60)
        for i, source in enumerate(result.sources, 1):
            click.echo(f"\n[{i}] {source.title}")
            if source.metadata.get("source"):
                click.echo(f"    Source: {source.metadata['source']}")
            if source.metadata.get("tags"):
                click.echo(f"    Tags: {', '.join(source.metadata['tags'])}")
            click.echo(f"    Content: {source.content[:200]}...")

    except Exception as e:
        click.echo(f"\nQuery failed: {e}")
        raise SystemExit(1)


@search.command("tags")
@click.option("--tags", "-t", multiple=True, required=True, help="Tags to search for")
@click.option("--match", type=click.Choice(["any", "all"]), default="any",
              help="Match any tag or all tags (default: any)")
@click.option("--limit", "-l", type=int, default=20, help="Number of results to return (default: 20)")
def search_tags(tags: tuple, match: str, limit: int) -> None:
    """Search items by tags"""
    from kb.storage.sqlite_storage import SQLiteStorage

    tag_list = list(tags)
    click.echo(f"Searching by tags: {', '.join(tag_list)}")
    click.echo(f"Match mode: {match}")

    try:
        storage = _get_sqlite_storage()

        if match == "all":
            results = storage.get_by_tags_all(tag_list, limit=limit)
        else:
            results = storage.get_by_tags_any(tag_list, limit=limit)

        if not results:
            click.echo("\nNo items found with these tags.")
            return

        click.echo(f"\nFound {len(results)} items:\n")
        for i, item in enumerate(results, 1):
            click.echo(f"[{i}] {item['title']}")
            click.echo(f"    ID: {item['id']}")
            click.echo(f"    Type: {item['content_type']}")
            if item.get('source'):
                click.echo(f"    Source: {item['source']}")
            if item.get('tags'):
                click.echo(f"    Tags: {', '.join(item['tags'])}")
            click.echo()

    except Exception as e:
        click.echo(f"\nSearch failed: {e}")
        raise SystemExit(1)
    finally:
        storage.close()


def _get_sqlite_storage():
    """Get SQLiteStorage instance"""
    from kb.storage.sqlite_storage import SQLiteStorage
    
    config = Config(CONFIG_FILE)
    data_dir = __import__('pathlib').Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
    db_path = str(data_dir / "db" / "metadata.db")
    return SQLiteStorage(db_path=db_path)
