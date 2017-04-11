# -*- coding: utf-8 -*-
# flake8: noqa

"""CLI tool."""


#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import logging
import os
import os.path as op
import sys
from traceback import format_exception

import click
from six import exec_
import glob

from .utils import discover_plugins


#------------------------------------------------------------------------------
# CLI tool
#------------------------------------------------------------------------------

@click.group()
# @click.version_option(version=__version_git__)
@click.help_option('-h', '--help')
@click.pass_context
def expipe(ctx, pdb=None):
    """Add subcommands to 'expipe' with plugins
    using `attach_to_cli()` and the `click` library."""
    pass


#------------------------------------------------------------------------------
# CLI plugins
#------------------------------------------------------------------------------


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
