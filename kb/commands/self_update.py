"""
Update command for self-updating localbrain.

Provides self-update functionality with version checking,
download, verification, and rollback.
"""

import sys

import click

from kb.config import Config
from kb.version import get_version
from kb.self_update import (
    perform_update,
    rollback,
    fetch_version_info,
    compare_versions,
    read_install_info,
)


@click.command("self-update")
@click.option("--check", is_flag=True, help="Check for update without installing")
@click.option("--rollback", "do_rollback", is_flag=True, help="Rollback to previous version")
def self_update(check: bool, do_rollback: bool):
    """Update localbrain to the latest version.
    
    Always fetches and installs the latest version, even if the local
    version matches. This ensures any corrupted or incomplete installations
    are repaired.
    
    \b
    Examples:
      localbrain self-update           Update to latest version
      localbrain self-update --check   Check if update is available
      localbrain self-update --rollback  Restore previous version
    """
    config = Config()
    server_url = config.update_server_url
    current_version = get_version()
    
    if do_rollback:
        _handle_rollback()
        return
    
    if check:
        _handle_check(server_url, current_version)
        return
    
    # Always force update: fetch and install latest version regardless of version match
    _handle_update(server_url, current_version, force=True)


def _handle_check(server_url: str, current_version: str) -> None:
    """Handle --check flag: just check for updates."""
    try:
        version_info = fetch_version_info(server_url)
        latest_version = version_info.version
        
        comparison = compare_versions(current_version, latest_version)
        
        if comparison < 0:
            click.echo(f"Update available: {current_version} → {latest_version}")
            click.echo(f"Released: {version_info.released}")
            if version_info.changelog:
                click.echo(f"Changelog: {version_info.changelog}")
        elif comparison > 0:
            click.echo(f"You are on a pre-release version: {current_version}")
            click.echo(f"Latest stable: {latest_version}")
        else:
            click.echo(f"Already up to date: {current_version}")
        
    except Exception as e:
        click.echo(f"Failed to check for updates: {e}", err=True)
        sys.exit(1)


def _handle_update(server_url: str, current_version: str, force: bool) -> None:
    """Handle update installation."""
    click.echo(f"Current version: {current_version}")
    
    # Check for pending update on Windows
    import platform
    if platform.system() == "Windows":
        from pathlib import Path
        pending_path = Path.home() / ".localbrain" / "bin" / ".update-pending"
        if pending_path.exists():
            click.echo("A pending update is waiting to be applied.")
            click.echo("Please restart localbrain to complete the update.")
            sys.exit(0)
    
    click.echo("Checking for updates...")
    
    try:
        success, message = perform_update(server_url, current_version, force)
        
        if success:
            click.echo(f"✓ {message}")
        else:
            click.echo(f"✗ {message}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Update failed: {e}", err=True)
        sys.exit(1)


def _handle_rollback() -> None:
    """Handle rollback to previous version."""
    click.echo("Rolling back to previous version...")
    
    success, message = rollback()
    
    if success:
        click.echo(f"✓ {message}")
    else:
        click.echo(f"✗ {message}", err=True)
        sys.exit(1)
