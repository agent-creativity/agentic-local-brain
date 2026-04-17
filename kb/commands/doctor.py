"""
Doctor command for system diagnostics.

Checks and reports system health, configuration, and service availability.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

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


def run_diagnostics() -> Dict[str, Any]:
    """Run system diagnostics and return structured results.
    
    Returns:
        Dict with version info, checks, issues, and overall status.
    """
    issues = []
    build_info = get_build_info()
    
    # Installation check
    install_ok, install_msg, install_type = check_install_info()
    install_path = ""
    if install_ok:
        if install_type == "python":
            install_path = str(get_install_dir() / "venv")
        elif install_type == "binary":
            install_path = str(get_install_dir() / "bin" / "localbrain")
    
    if not install_ok:
        issues.append("Install info not found - run install script")
    
    # Configuration check
    config = Config()
    config_ok, config_msg = check_config_exists(config)
    if not config_ok:
        issues.append("Config not found - run 'localbrain init setup'")
    
    data_ok, data_msg = check_data_dir(config)
    if not data_ok:
        issues.append("Data directory not found - run 'localbrain init setup'")
    
    # Services check
    service_status = check_services(config)
    emb_config = config.get("embedding", {})
    emb_provider = emb_config.get("provider", "not configured")
    emb_model = emb_config.get("model", "")
    emb_ok = service_status.get("embedding_available", False)
    if not emb_ok:
        issues.append("Embedding service not configured")
    
    llm_config = config.get("llm", {})
    llm_provider = llm_config.get("provider", "not configured")
    llm_model = llm_config.get("model", "")
    llm_ok = service_status.get("llm_available", False)
    if not llm_ok:
        issues.append("LLM service not configured")
    
    # PATH check
    path_ok, path_msg = check_path_in_env()
    if not path_ok:
        issues.append("localbrain not in PATH - reinstall or add to PATH manually")
    
    return {
        "version": build_info["version"],
        "platform": f"{build_info['platform']}-{build_info['architecture']}",
        "python_version": build_info["python"],
        "frozen": build_info["frozen"],
        "checks": {
            "installation": {
                "passed": install_ok,
                "message": install_msg,
                "install_type": "Python (venv)" if install_type == "python" else "Binary" if install_type == "binary" else "unknown",
                "path": install_path
            },
            "config": {
                "passed": config_ok,
                "message": config_msg
            },
            "data_dir": {
                "passed": data_ok,
                "message": data_msg
            },
            "embedding": {
                "passed": emb_ok,
                "message": f"{emb_provider}/{emb_model}" if emb_model else emb_provider
            },
            "llm": {
                "passed": llm_ok,
                "message": f"{llm_provider}/{llm_model}" if llm_model else llm_provider
            },
            "path_env": {
                "passed": path_ok,
                "message": path_msg
            }
        },
        "issues": issues,
        "all_passed": len(issues) == 0
    }


@click.command()
def doctor():
    """Run system diagnostics.
    
    Checks configuration, services, and installation status.
    """
    results = run_diagnostics()
    
    click.echo("🔍 LocalBrain Diagnostics\n")
    
    # Version info
    click.echo(f"  Version:     {results['version']}")
    click.echo(f"  Platform:    {results['platform']}")
    click.echo(f"  Python:      {results['python_version']}")
    click.echo(f"  Frozen:      {results['frozen']}")
    click.echo()
    
    # Installation check
    click.echo("  Installation:")
    install_check = results['checks']['installation']
    click.echo(f"    Install info: {check_mark(install_check['passed'])} {install_check['message']}")
    if install_check['passed'] and install_check['path']:
        if install_check['install_type'] == 'Python (venv)':
            click.echo(f"    Venv:         {install_check['path']}")
        elif install_check['install_type'] == 'Binary':
            click.echo(f"    Binary:       {install_check['path']}")
    click.echo()
    
    # Configuration check
    click.echo("  Configuration:")
    config_check = results['checks']['config']
    click.echo(f"    Config:  {check_mark(config_check['passed'])} {config_check['message']}")
    
    data_check = results['checks']['data_dir']
    click.echo(f"    Data:    {check_mark(data_check['passed'])} {data_check['message']}")
    click.echo()
    
    # Services check
    click.echo("  Services:")
    emb_check = results['checks']['embedding']
    click.echo(f"    Embedding: {check_mark(emb_check['passed'])} {emb_check['message']}")
    
    llm_check = results['checks']['llm']
    click.echo(f"    LLM:       {check_mark(llm_check['passed'])} {llm_check['message']}")
    click.echo()
    
    # PATH check
    click.echo("  Environment:")
    path_check = results['checks']['path_env']
    click.echo(f"    PATH:   {check_mark(path_check['passed'])} {path_check['message']}")
    click.echo()
    
    # Summary
    if results['issues']:
        click.echo("  ⚠ Issues found:")
        for issue in results['issues']:
            click.echo(f"    - {issue}")
        click.echo()
        click.echo("  Run 'localbrain init setup' to initialize.")
        sys.exit(1)
    else:
        click.echo("  ✓ All checks passed!")
        sys.exit(0)
