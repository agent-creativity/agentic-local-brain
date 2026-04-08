"""
CLI Management Commands

Management commands: config, stats, tag, export, test, web.
These commands are registered at the top level of the CLI.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

from kb.commands.utils import (
    CONFIG_DIR,
    CONFIG_FILE,
    TEMPLATE_FILE,
    _check_server_status,
    _ensure_config_dir,
    _get_pid_file,
    _get_sqlite_storage,
    _is_process_running,
    _print_config,
    _start_background_server,
    _stop_background_server,
)
from kb.config import Config


@click.group()
def config() -> None:
    """Configuration management"""
    pass


@config.command("show")
def config_show() -> None:
    """Show current configuration"""
    config_obj = Config(CONFIG_FILE)
    config_dict = config_obj.to_dict()

    click.echo("Current configuration:")
    click.echo("-" * 40)
    _print_config(config_dict, indent=0)


@click.command()
def stats() -> None:
    """Show knowledge base statistics"""
    storage = _get_sqlite_storage()
    
    try:
        # Get total counts
        total_items = storage.count_all()
        
        # Get counts by type
        type_stats = storage.count_by_type()
        
        # Get tag statistics
        tag_stats = storage.get_tag_statistics()
        
        # Get collection timeline
        timeline = storage.get_collection_timeline()
        
        click.echo("Knowledge Base Statistics")
        click.echo("=" * 50)
        click.echo(f"Total items: {total_items}")
        click.echo()
        
        click.echo("Items by type:")
        for content_type, count in type_stats.items():
            click.echo(f"  {content_type}: {count}")
        click.echo()
        
        click.echo(f"Total tags: {len(tag_stats)}")
        if tag_stats:
            click.echo("Top 10 tags:")
            sorted_tags = sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            for tag, count in sorted_tags:
                click.echo(f"  {tag}: {count}")
        click.echo()
        
        if timeline:
            click.echo("Collection timeline:")
            for date, count in timeline[:7]:  # Show last 7 days
                click.echo(f"  {date}: {count} items")
        
    except Exception as e:
        click.echo(f"Failed to get statistics: {e}", err=True)
        raise SystemExit(1)
    finally:
        storage.close()


@click.group()
def tag() -> None:
    """Tag management"""
    pass


@tag.command("list")
@click.option("--limit", "-l", type=int, default=50, help="Number of tags to show (default: 50)")
def tag_list(limit: int) -> None:
    """List all tags"""
    storage = _get_sqlite_storage()
    
    try:
        tags = storage.get_all_tags()
        
        if not tags:
            click.echo("No tags found.")
            return
        
        click.echo(f"All tags ({len(tags)}):")
        click.echo("-" * 40)
        
        # Sort by usage count
        sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        for tag, count in sorted_tags:
            click.echo(f"  {tag} ({count} items)")
        
        if len(tags) > limit:
            click.echo(f"\n... and {len(tags) - limit} more tags")
    
    except Exception as e:
        click.echo(f"Failed to list tags: {e}", err=True)
        raise SystemExit(1)
    finally:
        storage.close()


@tag.command("merge")
@click.argument("source_tag")
@click.argument("target_tag")
def tag_merge(source_tag: str, target_tag: str) -> None:
    """Merge source tag into target tag"""
    storage = _get_sqlite_storage()
    
    try:
        count = storage.merge_tags(source_tag, target_tag)
        if count > 0:
            click.echo(f"✓ Merged {count} items from '{source_tag}' to '{target_tag}'")
        else:
            click.echo(f"ℹ️  No items to merge (source tag '{source_tag}' not found or has no items)")
    except Exception as e:
        click.echo(f"Failed to merge tags: {e}", err=True)
        raise SystemExit(1)
    finally:
        storage.close()


@tag.command("delete")
@click.argument("tag_name")
def tag_delete(tag_name: str) -> None:
    """Delete a tag"""
    storage = _get_sqlite_storage()
    
    try:
        count = storage.delete_tag(tag_name)
        if count > 0:
            click.echo(f"✓ Deleted tag '{tag_name}' from {count} items")
        else:
            click.echo(f"ℹ️  Tag '{tag_name}' not found or has no items")
    except Exception as e:
        click.echo(f"Failed to delete tag: {e}", err=True)
        raise SystemExit(1)
    finally:
        storage.close()


@click.command()
@click.option("--format", "-f", "export_format", type=click.Choice(["markdown", "json"]),
              default="markdown", help="Export format (default: markdown)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--tags", "-t", multiple=True, help="Filter by tags")
def export(export_format: str, output: Optional[str], tags: tuple) -> None:
    """Export knowledge base"""
    storage = _get_sqlite_storage()
    
    try:
        # Get all items
        tag_list = list(tags) if tags else None
        items = storage.get_all_knowledge(tags=tag_list)
        
        if not items:
            click.echo("No items to export.")
            return
        
        if export_format == "json":
            export_json(items, output)
        else:
            export_markdown(items, output)
        
        click.echo(f"✓ Exported {len(items)} items")
        if output:
            click.echo(f"  Saved to: {output}")
    
    except Exception as e:
        click.echo(f"Failed to export: {e}", err=True)
        raise SystemExit(1)
    finally:
        storage.close()


def export_json(items: list, output: Optional[str]) -> None:
    """Export to JSON format"""
    data = {
        "version": "1.0",
        "exported_at": __import__('datetime').datetime.now().isoformat(),
        "items": items
    }
    
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    if output:
        Path(output).write_text(json_str, encoding="utf-8")
    else:
        click.echo(json_str)


def export_markdown(items: list, output: Optional[str]) -> None:
    """Export to Markdown format"""
    lines = []
    lines.append("# Knowledge Base Export")
    lines.append(f"\nExported at: {__import__('datetime').datetime.now().isoformat()}")
    lines.append(f"\nTotal items: {len(items)}\n")
    
    for item in items:
        lines.append(f"## {item['title']}")
        lines.append(f"\n- **ID**: {item['id']}")
        lines.append(f"- **Type**: {item['content_type']}")
        if item.get('source'):
            lines.append(f"- **Source**: {item['source']}")
        if item.get('tags'):
            lines.append(f"- **Tags**: {', '.join(item['tags'])}")
        if item.get('summary'):
            lines.append(f"- **Summary**: {item['summary']}")
        lines.append(f"\n{item.get('content', '')}")
        lines.append("\n---\n")
    
    content = "\n".join(lines)
    
    if output:
        Path(output).write_text(content, encoding="utf-8")
    else:
        click.echo(content)


@click.group("test")
def test() -> None:
    """Test service connectivity"""
    pass


@test.command("embedding")
def test_embedding() -> None:
    """Test embedding service connectivity"""
    from kb.processors.embedder import Embedder
    
    try:
        config = Config(CONFIG_FILE)
        
        click.echo("Testing embedding service...")
        click.echo(f"  Provider: {config.get('embedding.provider', 'unknown')}")
        click.echo(f"  Model: {config.get('embedding.dashscope.model', 'unknown')}")
        
        embedder = Embedder.from_config(config)
        
        # Test with a simple text
        test_text = "This is a test sentence for embedding."
        vectors = embedder.embed([test_text])
        
        if vectors and len(vectors) > 0:
            click.echo(f"✓ Embedding service is working!")
            click.echo(f"  Vector dimension: {len(vectors[0])}")
            click.echo(f"  Sample values: {vectors[0][:5]}...")
        else:
            click.echo("✗ Embedding service returned empty result")
            raise SystemExit(1)
    
    except Exception as e:
        click.echo(f"✗ Embedding service test failed: {e}")
        raise SystemExit(1)


@test.command("llm")
def test_llm() -> None:
    """Test LLM service connectivity"""
    from kb.processors.tag_extractor import TagExtractor
    
    try:
        config = Config(CONFIG_FILE)
        
        click.echo("Testing LLM service...")
        click.echo(f"  Provider: {config.get('llm.provider', 'unknown')}")
        click.echo(f"  Model: {config.get('llm.model', 'unknown')}")
        
        extractor = TagExtractor.from_config(config)
        
        # Test with a simple text
        test_title = "Test"
        test_content = "Machine learning is a subset of artificial intelligence."
        result = extractor.process(title=test_title, content=test_content)

        if result.success and result.data and len(result.data.get("tags", [])) > 0:
            click.echo(f"✓ LLM service is working!")
            click.echo(f"  Extracted tags: {', '.join(result.data['tags'])}")
            if result.data.get("summary"):
                click.echo(f"  Summary: {result.data['summary']}")
        else:
            click.echo(f"✗ LLM service returned empty result: {result.error or 'No tags extracted'}")
            raise SystemExit(1)
    
    except Exception as e:
        click.echo(f"✗ LLM service test failed: {e}")
        raise SystemExit(1)


@click.command()
@click.option("--host", "-h", default=None, help="Host to bind to (default: 127.0.0.1)")
@click.option("--port", "-p", default=None, type=int, help="Port to bind to (default: 8080)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("-b", "--background", is_flag=True, default=False, help="Run web server in background (daemon mode)")
@click.option("--stop", is_flag=True, default=False, help="Stop the background web server")
@click.option("--status", is_flag=True, default=False, help="Check if background web server is running")
def web(host: str, port: int, reload: bool, background: bool, stop: bool, status: bool) -> None:
    """Start the Local Brain web interface."""
    # Load config for defaults
    config = Config(CONFIG_FILE)
    
    # Validate services and warn user if not configured
    service_status = config.validate_services()
    if not service_status.get("embedding_available"):
        click.echo(click.style("Warning: ", fg="yellow") + "Embedding service not configured. Semantic search will use keyword fallback.")
    if not service_status.get("llm_available"):
        click.echo(click.style("Warning: ", fg="yellow") + "LLM service not configured. RAG and auto-tagging will be unavailable.")
    
    # Handle status check
    if status:
        _check_server_status(config)
        return
    
    # Handle stop
    if stop:
        _stop_background_server(config)
        return
    
    # Use command line args or config or defaults
    bind_host = host or config.get("web.host", "127.0.0.1")
    bind_port = port or int(config.get("web.port", 8080))
    
    # Handle background mode
    if background:
        _start_background_server(bind_host, bind_port, config)
        return
    
    # Foreground mode (normal)
    try:
        import uvicorn
    except ImportError:
        click.echo("✗ Web UI requires additional dependencies.", err=True)
        click.echo("  Install them with: pip install fastapi uvicorn", err=True)
        raise SystemExit(1)
    
    click.echo(f"Starting Local Brain Web UI...")
    click.echo(f"  URL: http://{bind_host}:{bind_port}")
    click.echo(f"  API Docs: http://{bind_host}:{bind_port}/docs")
    click.echo()
    click.echo("Press Ctrl+C to stop the server.")
    click.echo()
    
    uvicorn.run(
        "kb.web.app:app",
        host=bind_host,
        port=bind_port,
        reload=reload,
    )
