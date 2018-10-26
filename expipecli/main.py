# -*- coding: utf-8 -*-

"""CLI tool."""


#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import os
import os.path as op
import sys
import click
import pathlib
from .utils import load_plugins, IPlugin
import expipe as expipe_module
try:
    import ruamel.yaml as yaml
except ImportError:
    import ruamel_yaml as yaml


def yaml_dump(f, data):
    assert f.suffix == '.yaml'
    with f.open("w", encoding="utf-8") as fh:
        yaml.dump(
            data, fh,
            default_flow_style=False,
            allow_unicode=True,
            Dumper=yaml.RoundTripDumper
        )


def yaml_get(path):
    if not path.exists():
        return None
    with path.open('r', encoding='utf-8') as f:
        result = yaml.load(f, Loader=yaml.Loader)
    return result

# TODO move to expipe
def load_local_config(path):
    current_root = pathlib.Path(path)
    current_path = current_root / "expipe.yaml"
    if not current_path.exists():
        if current_root.match(current_path.root):
            return None, None, {}

        return load_local_config(current_root.parent)
    current_config = yaml_get(current_path) or {}
    return current_root, current_path, current_config


def load_global_config():
    global_root = pathlib.Path.home() / '.config' / 'expipe'
    global_config_path = global_root / 'config.yaml'
    global_config = yaml_get(global_config_path) or {}
    return global_root, global_config_path, global_config


def load_project_config(project_id=None):
    if project_id is None:
        return None, None, {}
    project_root = pathlib.Path.home() / '.config' / 'expipe' / project_id
    project_config_path = (project_root / project_id).with_suffix('.yaml')
    project_config = yaml_get(project_config_path) or {}
    return project_root, project_config_path, project_config


def load_config(project_id=None):
    # make paths
    global_root, global_config_path, global_config = load_global_config()
    # see if you are in a filesystem project
    local_root, local_path, local_config = load_local_config(pathlib.Path.cwd())
    if local_root is not None:
        assert project_id is None, '"project-id" should not be given if in a filesystem project'
        project_id = local_root.stem
    project_root, project_config_path, project_config = load_project_config(project_id)
    config = {
        'global': global_config,
        'global_path': global_config_path,
        'global_root': global_root,
        'project': project_config,
        'project_path': project_config_path,
        'project_root': project_root,
        'local': local_config,
        'local_path': local_path,
        'local_root': local_root,
    }

    return config

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


class Default(IPlugin):
    def attach_to_cli(self, cli):
        @cli.command('create')
        @click.argument(
            'project-id', type=click.STRING
        )
        def create(project_id):
            """Create a project."""
            cwd = pathlib.Path.cwd()
            root, _, _ = load_local_config(cwd)
            if root is not None:
                print(
                    'Cannot create a project inside a project. ' +
                    'You are currently in "{}"'.format(root)
                )
                return
            expipe_module.load_project(path=cwd / project_id)

        @cli.command('status') # TODO add project id and spcialize firebase printing to not reveal confidential info
        def status():
            """Print project status."""
            config = load_config()
            if config['local_root'] is None:
                print('Unable to locate expipe configurations.')
                return
            assert config['local']['type'] == 'project'
            server = expipe_module.load_project(path=config['local_root'])
            print('Local configuration:')
            for k, v in config['local'].items():
                print('\t{}: {}'.format(k, v))
            print()
            print('project configuration:')
            for k, v in config['project'].items():
                print('\t{}: {}'.format(k, v))
            print()
            print('Global configuration:')
            for k, v in config['global'].items():
                print('\t{}: {}'.format(k, v))

        @cli.command('list')
        @click.argument(
            'object-type', type=click.Choice(['actions', 'entities', 'modules'])
        )
        def list_stuff(object_type):
            """Print project objects."""
            config = load_config()
            if config['local_root'] is None:
                print('Unable to locate expipe configurations.')
                return
            assert config['local']['type'] == 'project'
            project = expipe_module.load_project(path=config['local_root'])
            for object in getattr(project, object_type):
                print(object)


        @cli.command('config') # TODO add stuff
        @click.argument(
            'target', type=click.Choice(['global', 'project', 'local'])
        )
        @click.option(
            '--project-id', type=click.STRING,
        )
        @click.option(
            '--username', type=click.STRING,
        )
        @click.option(
            '--email', type=click.STRING,
        )
        @click.option(
            '--location', type=click.STRING,
        )
        @click.option(
            '--plugin', '-p', type=click.STRING, multiple=True
        )
        def set_config(project_id, plugin, target, **kw):
            """Set config info."""
            config = load_config(project_id)
            if config[target + '_root'] is None:
                print(
                    'Unable to load config, move into a project or ' +
                    'give "project-id" explicitly.')
                return
            if len(plugin) > 0:
                plugins = [p for p in plugin]
                kw['plugins'] = list(set(plugins))
            config[target].update({k: v for k,v in kw.items() if v})
            config[target + '_root'].mkdir(exist_ok=True)
            yaml_dump(config[target + '_path'], config[target])


# ------------------------------------------------------------------------------
# CLI plugins
# ------------------------------------------------------------------------------

def load_cli_plugins(cli, modules=None):
    """Load all plugins and attach them to a CLI object."""
    modules = modules or []
    plugins = load_plugins(modules)
    for plugin in plugins:
        if not hasattr(plugin, 'attach_to_cli'):
            continue
        # NOTE: plugin is a class, so we need to instantiate it.
        try:
            plugin().attach_to_cli(cli)
        except Exception as e:
            print("Error when loading plugin `%s`" % plugin)
            raise e


# Load all plugins when importing this module.

def list_plugins():
    cwd = pathlib.Path.cwd()
    global_root, global_config_path, global_config = load_global_config()
    # see if you are in a filesystem project
    local_root, local_path, local_config = load_local_config(cwd)
    if local_root is not None:
        project_root, project_config_path, project_config = load_project_config(local_root.stem)
        project_plugins = project_config.get('plugins') or []
    else:
        project_plugins = []
    global_plugins = global_config.get('plugins') or []
    return global_plugins + project_plugins

load_cli_plugins(expipe, list_plugins())
