# -*- coding: utf-8 -*-
# flake8: noqa

"""CLI tool."""


#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import os
import os.path as op
import sys
import click
import pathlib
from .utils import discover_plugins, IPlugin
import expipe as expipe_module


# ------------------------------------------------------------------------------
# CLI tool
# ------------------------------------------------------------------------------

@click.group()
# @click.version_option(version=__version_git__)
@click.help_option('-h', '--help')
@click.pass_context
def expipe(ctx):
    """Add subcommands to 'expipe' with plugins
    using `attach_to_cli()` and the `click` library.

    Note that you can get help from a COMMAND by "expipe COMMAND --help"
    """
    pass
    #TODO discovery
    #


class Default(IPlugin):
    def attach_to_cli(self, cli):
        @cli.command('create')
        @click.argument(
            'project-id', type=click.STRING
        )
        def init(project_id):
            """Create a project."""
            cwd = os.getcwd()
            path = pathlib.Path(cwd) / project_id
            # server = expipe.load_filesystem(path.parent)
            # project = server.require_project(project_id)
            expipe_module.create_project(path)


# ------------------------------------------------------------------------------
# CLI plugins
# ------------------------------------------------------------------------------


def load_cli_plugins(cli, config_dir=None):
    """Load all plugins and attach them to a CLI object."""

    plugins = discover_plugins()
    for plugin in plugins:
        if not hasattr(plugin, 'attach_to_cli'):  # pragma: no cover
            continue
        # NOTE: plugin is a class, so we need to instantiate it.
        try:
            plugin().attach_to_cli(cli)
        except Exception as e:  # pragma: no cover
            print("Error when loading plugin `%s`" % plugin)
            raise e


# Load all plugins when importing this module.
load_cli_plugins(expipe)
