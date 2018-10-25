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
    global_config_path = global_root / 'expipe-config.yaml'
    global_config = yaml_get(global_config_path) or {}
    return global_root, global_config_path, global_config


def load_user_config(project_id):
    user_root = pathlib.Path.home() / '.config' / 'expipe' / project_id
    user_config_path = (user_root / project_id).with_suffix('.yaml')
    user_config = yaml_get(user_config_path) or {}
    return user_root, user_config_path, user_config


def load_config(project_id=None):
    # make paths
    cwd = pathlib.Path.cwd()
    global_root, global_config_path, global_config = load_global_config()

    # see if you are in a filesystem project
    local_root, local_path, local_config = load_local_config(cwd)
    if local_root is not None:
        assert project_id is None, 'project_id should not be given if in a filesystem project'
        project_id = local_root.stem
    assert project_id is not None, 'project_id should be given if not in a filesystem project'
    user_root, user_config_path, user_config = load_user_config(project_id)
    config = {
        'global': global_config,
        'global_path': global_config_path,
        'global_root': global_root,
        'user': user_config,
        'user_path': user_config_path,
        'user_root': user_root,
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
            server = expipe_module.load_file_system(root=cwd)
            server.create_project(project_id)

        @cli.command('status') # TODO add project id and spcialize firebase printing to not reveal confidential info
        def status():
            """Print project status."""
            config = load_config()
            if config['local_root'] is None:
                print('Unable to locate expipe configurations.')
                return
            assert config['local']['type'] == 'project'
            server = expipe_module.load_file_system(root=config['local_root'].parent)
            server.get_project(config['local_root'].stem)
            print('Local configuration:')
            for k, v in config['local'].items():
                print('\t{}: {}'.format(k, v))
            print()
            print('User configuration:')
            for k, v in config['user'].items():
                print('\t{}: {}'.format(k, v))
            print()
            print('Global configuration:')
            for k, v in config['global'].items():
                print('\t{}: {}'.format(k, v))

        @cli.command('set')
        @click.option(
            '--project-id', type=click.STRING,
        )
        @click.option(
            '--user', type=click.STRING,
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
        def set_user(project_id, plugin, **kw):
            """Set local user info."""
            config = load_config(project_id)
            if len(plugin) > 0:
                plugins = [p for p in plugin]
                kw['plugins'] = list(set(plugins))
            config['user'].update({k: v for k,v in kw.items() if v})
            config['user_root'].mkdir(exist_ok=True)
            yaml_dump(config['user_path'], config['user'])

        @cli.command('update')
        @click.option(
            '--project-id', type=click.STRING,
        )
        @click.option(
            '--plugin', '-p', type=click.STRING, multiple=True
        )
        def set_user(project_id, plugin, **kw):
            """Update local user info."""
            config = load_config(project_id)
            if len(plugin) > 0:
                current_plugins = config['user'].get('plugins') or []
                plugins = [p for p in plugin] + current_plugins
                kw['plugins'] = list(set(plugins))
            config['user'].update({k: v for k,v in kw.items() if v})
            yaml_dump(config['user_path'], config['user'])

        @cli.command('set-global')
        @click.option(
            '--user', type=click.STRING,
        )
        @click.option(
            '--email', type=click.STRING,
        )
        @click.option(
            '--location', type=click.STRING,
        )
        @click.option(
            '--plugin', '-p', type=click.Path(exists=True), multiple=True
        )
        def set_global(plugin, **kw):
            """Set global user info."""
            config = load_config()
            config['global'].update({k: v for k,v in kw.items() if v})
            config['global_root'].mkdir(exist_ok=True)
            yaml_dump(config['global_path'], config['global'])

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
        user_root, user_config_path, user_config = load_user_config(local_root.stem)
        user_plugins = user_config.get('plugins') or []
    else:
        user_plugins = []
    global_plugins = global_config.get('plugins') or []
    return global_plugins + user_plugins

load_cli_plugins(expipe, list_plugins())
