"""
CLI Shared Utilities

Common helper functions and constants used across CLI command modules.
"""

import hashlib
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from kb.config import Config, expand_path

# Configuration directory
CONFIG_DIR = Path.home() / ".localbrain"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Template file path (inside the kb package)
TEMPLATE_FILE = Path(__file__).parent.parent / "config-template.yaml"


def _ensure_config_dir() -> None:
    """Ensure configuration directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _get_sqlite_storage():
    """
    Get SQLiteStorage instance
    
    Build database path using data_dir from config or default path.
    
    Returns:
        SQLiteStorage: SQLite storage instance
    """
    from kb.storage.sqlite_storage import SQLiteStorage
    
    config = Config(CONFIG_FILE)
    data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()
    db_path = str(data_dir / "db" / "metadata.db")
    return SQLiteStorage(db_path=db_path)


def _print_config(config: dict, indent: int = 0) -> None:
    """Recursively print configuration dictionary"""
    for key, value in config.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            click.echo(f"{prefix}{key}:")
            _print_config(value, indent + 1)
        else:
            click.echo(f"{prefix}{key}: {value}")


def _get_pid_file(config: Config) -> Path:
    """Get the PID file path for background web server."""
    pid_dir = CONFIG_DIR / ".runtime"
    pid_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir / "web_server.pid"


def _is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _start_background_server(host: str, port: int, config: Config) -> None:
    """Start the web server in background mode."""
    pid_file = _get_pid_file(config)
    
    # Check if already running
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
            if _is_process_running(existing_pid):
                click.echo(f"⚠️  Web server is already running (PID: {existing_pid})")
                click.echo(f"   Use 'localbrain web --stop' to stop it first.")
                raise SystemExit(1)
            else:
                # Stale PID file, remove it
                pid_file.unlink()
        except ValueError:
            # Invalid PID file, remove it
            pid_file.unlink()
    
    # Setup logging
    log_config = config.get_log_config()
    log_file = log_config["log_dir"] / "web_server.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Start uvicorn as detached process
    cmd = [
        sys.executable, "-m", "uvicorn", "kb.web.app:app",
        "--host", host, "--port", str(port)
    ]
    
    # Open log file for writing
    log_f = open(log_file, "a")
    
    try:
        # Start the process in a new session (detached from terminal)
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True  # detach from terminal
        )
        
        # Write PID to file
        pid_file.write_text(str(proc.pid))
        
        click.echo(f"✓ Web server started in background (PID: {proc.pid})")
        click.echo(f"  Log file: {log_file}")
        click.echo(f"  URL: http://{host}:{port}")
        click.echo(f"  Stop: localbrain web --stop")
        
    except Exception as e:
        log_f.close()
        click.echo(f"✗ Failed to start web server: {e}", err=True)
        raise SystemExit(1)


def _stop_background_server(config: Config) -> None:
    """Stop the background web server."""
    pid_file = _get_pid_file(config)
    
    if not pid_file.exists():
        click.echo("ℹ️  No background web server is running (PID file not found)")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        click.echo("✗ Invalid PID file. Removing it.", err=True)
        pid_file.unlink(missing_ok=True)
        raise SystemExit(1)
    
    if not _is_process_running(pid):
        click.echo(f"ℹ️  Web server process (PID: {pid}) is not running")
        pid_file.unlink(missing_ok=True)
        return
    
    # Send SIGTERM to the process
    try:
        os.kill(pid, signal.SIGTERM)
        click.echo(f"✓ Sent stop signal to web server (PID: {pid})")
        
        # Wait a moment and check if process is still running
        import time
        time.sleep(1)
        
        if _is_process_running(pid):
            click.echo(f"  Process still running, sending SIGKILL...")
            os.kill(pid, signal.SIGKILL)
        
        pid_file.unlink(missing_ok=True)
        click.echo("✓ Web server stopped")
        
    except OSError as e:
        click.echo(f"✗ Failed to stop web server: {e}", err=True)
        raise SystemExit(1)


def _check_server_status(config: Config) -> None:
    """Check the status of the background web server."""
    pid_file = _get_pid_file(config)
    
    if not pid_file.exists():
        click.echo("ℹ️  Web server status: Not running")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        click.echo("⚠️  Web server status: Unknown (invalid PID file)")
        return
    
    if _is_process_running(pid):
        log_config = config.get_log_config()
        log_file = log_config["log_dir"] / "web_server.log"
        click.echo(f"✓ Web server status: Running (PID: {pid})")
        click.echo(f"  Log file: {log_file}")
    else:
        click.echo(f"⚠️  Web server status: Not running (stale PID file: {pid})")


def _generate_content_hash(content: str) -> str:
    """Generate SHA256 hash for content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _index_content_for_search(
    item_id: str,
    content: str,
    title: str,
    tags: Optional[list] = None,
    source: str = "",
    content_type: str = "",
    pdf_pages: Optional[list] = None
) -> bool:
    """
    Index content for semantic search by chunking, embedding, and storing in ChromaDB.

    This function processes content through the full embedding pipeline:
    1. Chunk the content using Chunker
    2. Embed chunks using Embedder
    3. Store embeddings in ChromaDB
    4. Save chunk metadata in SQLite

    Args:
        item_id: Knowledge item ID
        content: Text content to index
        title: Item title (used for metadata)
        tags: List of tags (used for metadata)
        source: Source URL/path (used for metadata)
        content_type: Content type (used for metadata)

    Returns:
        bool: True if indexing succeeded, False otherwise
    """
    from kb.config import Config
    from kb.processors.chunker import Chunker
    from kb.processors.embedder import Embedder
    from kb.storage.chroma_storage import ChromaStorage
    from kb.storage.sqlite_storage import SQLiteStorage
    from pathlib import Path

    config = Config(CONFIG_FILE)
    data_dir = Path(config.get("data_dir", "~/.knowledge-base")).expanduser()

    try:
        # Initialize components
        chunker = Chunker.from_config(config)
        embedder = Embedder.from_config(config)
        chroma_path = str(data_dir / "db" / "chroma")
        chroma = ChromaStorage(path=chroma_path)

        # Chunk the content — use page-aware chunking for PDFs with >10 pages
        if pdf_pages and len(pdf_pages) > 10:
            chunk_result = chunker.process_with_pages(pdf_pages)
        else:
            chunk_result = chunker.process(content)
        if not chunk_result.success or not chunk_result.data:
            return False

        chunks = chunk_result.data

        # Prepare chunk texts and metadata
        chunk_texts = [chunk["content"] for chunk in chunks]
        chunk_ids = [f"{item_id}_chunk_{i}" for i in range(len(chunks))]

        # Embed the chunks
        embeddings = embedder.embed(chunk_texts)

        # Prepare metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "knowledge_id": item_id,
                "title": title,
                "chunk_index": i,
                "source": source,
                "content_type": content_type,
            }
            if tags:
                metadata["tags"] = ",".join(tags)
            if "page_number" in chunk:
                metadata["page_number"] = chunk["page_number"]
            metadatas.append(metadata)

        # Store in ChromaDB
        chroma.add_documents(
            ids=chunk_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=chunk_texts
        )

        # Save chunk metadata in SQLite
        db_path = str(data_dir / "db" / "metadata.db")
        sqlite = SQLiteStorage(db_path=db_path)

        chunk_records = []
        for i, chunk in enumerate(chunks):
            chunk_records.append({
                "id": chunk_ids[i],
                "chunk_index": i,
                "content": chunk["content"],
                "embedding_id": chunk_ids[i]
            })

        sqlite.add_chunks(item_id, chunk_records)
        sqlite.close()

        return True

    except Exception as e:
        # Log error but don't fail the collection
        click.echo(f"  Warning: Failed to index content for search: {e}", err=True)
        return False


def _update_markdown_frontmatter(
    file_path: Path,
    tags: Optional[list] = None,
    summary: Optional[str] = None
) -> bool:
    """
    Update the YAML frontmatter in a markdown file.
    
    Reads a markdown file with YAML frontmatter, updates the tags and/or summary
    fields, and writes it back.
    
    Args:
        file_path: Path to the markdown file
        tags: List of tags to set (optional)
        summary: Summary text to set (optional)
        
    Returns:
        bool: True if update succeeded, False otherwise
    """
    import re
    
    if not file_path or not file_path.exists():
        return False
    
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Check if file has YAML frontmatter
        if not content.startswith("---"):
            return False
        
        # Find the end of the frontmatter
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            return False
        
        yaml_content = match.group(1)
        body_content = match.group(2)
        
        # Parse and update YAML content line by line
        yaml_lines = yaml_content.split('\n')
        updated_lines = []
        tags_updated = False
        summary_updated = False
        
        for line in yaml_lines:
            # Update tags
            if line.startswith('tags:'):
                if tags is not None:
                    if tags:
                        updated_lines.append('tags:')
                        for tag in tags:
                            updated_lines.append(f'  - {tag}')
                    else:
                        updated_lines.append('tags: []')
                    tags_updated = True
                else:
                    updated_lines.append(line)
            # Update summary
            elif line.startswith('summary:'):
                if summary is not None:
                    if summary:
                        # Escape special characters in summary
                        safe_summary = summary.replace('"', '\\"')
                        updated_lines.append(f'summary: "{safe_summary}"')
                    else:
                        updated_lines.append('summary: ""')
                    summary_updated = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add tags if not present and provided
        if not tags_updated and tags is not None:
            if tags:
                updated_lines.append('tags:')
                for tag in tags:
                    updated_lines.append(f'  - {tag}')
            else:
                updated_lines.append('tags: []')
        
        # Add summary if not present and provided
        if not summary_updated and summary is not None:
            if summary:
                safe_summary = summary.replace('"', '\\"')
                updated_lines.append(f'summary: "{safe_summary}"')
            else:
                updated_lines.append('summary: ""')
        
        # Reconstruct the file
        new_content = '---\n' + '\n'.join(updated_lines) + '\n---\n' + body_content
        file_path.write_text(new_content, encoding="utf-8")
        
        return True
        
    except Exception as e:
        click.echo(f"  Warning: Failed to update frontmatter: {e}", err=True)
        return False
