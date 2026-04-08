"""
Uninstall command for removing localbrain.

Provides clean uninstallation that preserves user data.
"""

import sys
from pathlib import Path
from typing import List

import click


def get_install_dir() -> Path:
    """Get installation directory."""
    return Path.home() / ".localbrain"


def get_data_dir() -> Path:
    """Get data directory."""
    return Path.home() / ".knowledge-base"


def get_shell_config_files() -> List[Path]:
    """Get list of possible shell config files."""
    home = Path.home()
    return [
        home / ".zshrc",
        home / ".zprofile",
        home / ".bashrc",
        home / ".bash_profile",
        home / ".config" / "fish" / "config.fish",
    ]


def remove_path_entry_from_file(config_file: Path, bin_dir: Path) -> bool:
    """
    Remove PATH entry for localbrain from shell config file.
    
    Returns True if file was modified.
    """
    if not config_file.exists():
        return False
    
    content = config_file.read_text()
    lines = content.split("\n")
    
    # Pattern to match: export PATH="$HOME/.localbrain/bin:$PATH"
    # or similar variations
    bin_dir_str = str(bin_dir)
    patterns_to_remove = [
        f'export PATH="{bin_dir_str}:$PATH"',
        f'export PATH="${{HOME}}/.localbrain/bin:$PATH"',
        f'export PATH="$HOME/.localbrain/bin:$PATH"',
        f'set -gx PATH {bin_dir_str} $PATH',  # fish
    ]
    
    new_lines = []
    modified = False
    
    for line in lines:
        stripped = line.strip()
        should_remove = False
        
        for pattern in patterns_to_remove:
            if stripped == pattern:
                should_remove = True
                break
        
        # Also check if line contains the path export
        if not should_remove and ".localbrain/bin" in stripped and "PATH" in stripped:
            # Be careful - use exact match for safety
            for pattern in patterns_to_remove:
                if stripped == pattern:
                    should_remove = True
                    break
        
        if should_remove:
            modified = True
        else:
            new_lines.append(line)
    
    if modified:
        config_file.write_text("\n".join(new_lines))
    
    return modified


@click.command()
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def uninstall(yes: bool):
    """Uninstall localbrain from the system.
    
    Removes the binary but preserves your knowledge base.
    To remove user data, manually delete:
      - ~/.knowledge-base
      - ~/.localbrain/config.yaml
    
    \b
    Examples:
      localbrain uninstall           Remove binary, keep data
      localbrain uninstall -y        Remove without confirmation
    """
    install_dir = get_install_dir()
    data_dir = get_data_dir()
    bin_dir = install_dir / "bin"
    binary_path = bin_dir / "localbrain"
    
    # Check if installed
    if not binary_path.exists():
        click.echo("localbrain is not installed.")
        sys.exit(1)
    
    # Confirmation
    if not yes:
        click.echo("This will remove localbrain from your system.")
        click.echo()
        click.echo("Your knowledge base will be preserved:")
        click.echo(f"  - {data_dir}")
        click.echo(f"  - {install_dir / 'config.yaml'}")
        click.echo()
        click.echo("To completely remove all data, run:")
        click.echo(f"  rm -rf {data_dir} {install_dir}")
        click.echo()
        
        if not click.confirm("Continue?", default=False):
            click.echo("Uninstall cancelled.")
            sys.exit(0)
    
    # Remove binary
    click.echo("Removing binary...")
    if binary_path.exists():
        binary_path.unlink()
    
    # Remove backup
    backup_path = binary_path.with_suffix(".old")
    if backup_path.exists():
        backup_path.unlink()
    
    # Remove install info
    install_info = install_dir / ".install-info"
    if install_info.exists():
        install_info.unlink()
    
    # Remove pending update marker
    pending_path = bin_dir / ".update-pending"
    if pending_path.exists():
        pending_path.unlink()
    
    # Remove from PATH
    click.echo("Removing from PATH...")
    for config_file in get_shell_config_files():
        if config_file.exists():
            remove_path_entry_from_file(config_file, bin_dir)
    
    # Remove empty bin directory
    if bin_dir.exists() and not list(bin_dir.iterdir()):
        bin_dir.rmdir()
    
    # Show preserved files
    click.echo("Preserved:")
    if data_dir.exists():
        click.echo(f"  - {data_dir}")
    config_path = install_dir / "config.yaml"
    if config_path.exists():
        click.echo(f"  - {config_path}")
    
    click.echo()
    click.echo("✓ localbrain has been uninstalled.")
    click.echo()
    click.echo("To completely remove all data, run:")
    click.echo(f"  rm -rf {data_dir} {install_dir}")
