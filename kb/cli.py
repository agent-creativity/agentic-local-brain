"""
CLI Entry Module

Command-line interface entry point using the Click framework.
This module serves as the main entry point and imports command groups from submodules.

Refactored structure:
- kb/commands/init.py: Initialization commands
- kb/commands/collect.py: Collection commands (file, webpage, paper, email, bookmark, note)
- kb/commands/search.py: Search commands (semantic, keyword, rag, tags)
- kb/commands/manage.py: Management commands (config, stats, tag, export, test, web)
"""

import click

from kb import __version__
from kb.commands.init import init
from kb.commands.collect import collect
from kb.commands.search import search
from kb.commands.manage import config, stats, tag, export, test, web
from kb.commands.topics import topics
from kb.commands.mine import mine
from kb.commands.uninstall import uninstall
from kb.commands.doctor import doctor
from kb.commands.self_update import self_update


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="localbrain")
@click.pass_context
def cli(ctx):
    """Local Brain - Personal knowledge management system.

    Collect, process, and query knowledge from multiple sources.

    \b
    Examples:
      localbrain init setup                          Initialize knowledge base
      localbrain collect file add paper.pdf          Add a file
      localbrain collect webpage add <url>           Add a webpage
      localbrain search semantic "machine learning"  Semantic search
      localbrain stats                               Show statistics
      localbrain web                                 Start web interface
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register command groups
cli.add_command(init)
cli.add_command(collect)
cli.add_command(search)

# Register management commands at top level
cli.add_command(config)
cli.add_command(stats)
cli.add_command(tag)
cli.add_command(export)
cli.add_command(test)
cli.add_command(web)
cli.add_command(topics)
cli.add_command(mine)
cli.add_command(uninstall)
cli.add_command(doctor)
cli.add_command(self_update)


# Backward compatibility: keep old command names as aliases
# These will be deprecated in future versions


if __name__ == "__main__":
    cli()

