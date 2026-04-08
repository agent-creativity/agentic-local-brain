"""
Doctor command for system diagnostics.

Checks and reports system health, configuration, and service availability.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

import click

from kb.config import Config
from kb.version import get_version, get_build_info
from kb.self_update import read_install_info, get_install_dir, get_install_type


def check_mark(passed: bool) -> str:
    """Return check mark or cross based on status."""
    return "✓" if passed else "✗"


def check_config_exists(config: Config) -> Tuple[bool, str]:
    """Check if config file exists and is valid."""
    if config.config_path.exists():
        try:
            config.load()
            return True, str(config.config_path)
        except Exception:
            return False, f"{config.config_path} (invalid)"
    return False, "not found"


def check_data_dir(config: Config) -> Tuple[bool, str]:
    """Check if data directory exists."""
    data_dir = config.data_dir
    if data_dir.exists():
        return True, str(data_dir)
    return False, f"{data_dir} (not found)"


def check_path_in_env() -> Tuple[bool, str]:
    """Check if ~/.localbrain/bin is in PATH."""
    install_dir = get_install_dir()
    bin_dir = install_dir / "bin"
    
    path_env = os.environ.get("PATH", "")
    path_dirs = [Path(p) for p in path_env.split(os.pathsep)]
    
    if bin_dir in path_dirs:
        return True, str(bin_dir)
    
    return False, f"{bin_dir} not in PATH"


def check_services(config: Config) -> dict:
    """Check service availability."""
    return config.validate_services()


def check_install_info() -> Tuple[bool, str, str]:
    """Check installation info and detect install type.
    
    Returns:
        Tuple of (found, message, install_type)
    """
    info = read_install_info()
    install_type = get_install_type()
    
    if info:
        # Build message with install type
        type_label = "Python (venv)" if install_type == "python" else "Binary"
        msg = f"v{info.version} ({type_label})"
        return True, msg, install_type
    return False, "not found", "unknown"


@click.command()
def doctor():
    """Run system diagnostics.
    
    Checks configuration, services, and installation status.
    """
    click.echo("🔍 LocalBrain Diagnostics\n")
    
    issues = []
    
    # Version info
    build_info = get_build_info()
    click.echo(f"  Version:     {build_info['version']}")
    click.echo(f"  Platform:    {build_info['platform']}-{build_info['architecture']}")
    click.echo(f"  Python:      {build_info['python']}")
    click.echo(f"  Frozen:      {build_info['frozen']}")
    click.echo()
    
    # Installation check
    click.echo("  Installation:")
    install_ok, install_msg, install_type = check_install_info()
    click.echo(f"    Install info: {check_mark(install_ok)} {install_msg}")
    if not install_ok:
        issues.append("Install info not found - run install script")
    else:
        # Show install type specific info
        if install_type == "python":
            venv_path = get_install_dir() / "venv"
            click.echo(f"    Venv:         {venv_path}")
        elif install_type == "binary":
            bin_path = get_install_dir() / "bin" / "localbrain"
            click.echo(f"    Binary:       {bin_path}")
    click.echo()
    
    # Configuration check
    click.echo("  Configuration:")
    config = Config()
    
    config_ok, config_msg = check_config_exists(config)
    click.echo(f"    Config:  {check_mark(config_ok)} {config_msg}")
    if not config_ok:
        issues.append("Config not found - run 'localbrain init setup'")
    
    data_ok, data_msg = check_data_dir(config)
    click.echo(f"    Data:    {check_mark(data_ok)} {data_msg}")
    if not data_ok:
        issues.append("Data directory not found - run 'localbrain init setup'")
    click.echo()
    
    # Services check
    click.echo("  Services:")
    service_status = check_services(config)
    
    emb_ok = service_status.get("embedding_available", False)
    emb_config = config.get("embedding", {})
    emb_provider = emb_config.get("provider", "not configured")
    emb_model = emb_config.get("model", "")
    click.echo(f"    Embedding: {check_mark(emb_ok)} {emb_provider}/{emb_model}")
    if not emb_ok:
        issues.append("Embedding service not configured")
    
    llm_ok = service_status.get("llm_available", False)
    llm_config = config.get("llm", {})
    llm_provider = llm_config.get("provider", "not configured")
    llm_model = llm_config.get("model", "")
    click.echo(f"    LLM:       {check_mark(llm_ok)} {llm_provider}/{llm_model}")
    if not llm_ok:
        issues.append("LLM service not configured")
    click.echo()
    
    # PATH check
    click.echo("  Environment:")
    path_ok, path_msg = check_path_in_env()
    click.echo(f"    PATH:   {check_mark(path_ok)} {path_msg}")
    if not path_ok:
        issues.append("localbrain not in PATH - reinstall or add to PATH manually")
    click.echo()
    
    # Summary
    if issues:
        click.echo("  ⚠ Issues found:")
        for issue in issues:
            click.echo(f"    - {issue}")
        click.echo()
        click.echo("  Run 'localbrain init setup' to initialize.")
        sys.exit(1)
    else:
        click.echo("  ✓ All checks passed!")
        sys.exit(0)
