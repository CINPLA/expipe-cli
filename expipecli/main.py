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
from .utils import discover_plugins, IPlugin
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

    return current_root, current_path, yaml_get(current_path)


def load_config(project_id=None):
    # make paths
    cwd = pathlib.Path('').cwd()
    global_root = cwd.home() / '.config' / 'expipe'
    global_config_path = global_root / 'expipe-config.yaml'
    global_config = yaml_get(global_config_path) or {}
    # see if you are in a filesystem project
    local_root, local_path, local_config = load_local_config(cwd)
    if local_root is not None:
        assert project_id is None, 'project_id should not be given if in a filesystem project'
        project_id = local_root.stem
    assert project_id is not None, 'project_id should be given if not in a filesystem project'
    user_root = global_root / project_id
    user_config_path = (user_root / project_id).with_suffix('.yaml')
    user_config = yaml_get(user_config_path) or {}
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
            cwd = os.getcwd()
            root, _, _ = load_local_config(cwd)
            if root is not None:
                print(
                    'Cannot create a project inside a project. ' +
                    'You are currently in "{}"'.format(root)
                )
                return
            path = pathlib.Path(cwd) / project_id
            # server = expipe.load_filesystem(path.parent)
            # project = server.require_project(project_id)
            expipe_module.create_project(path)

        @cli.command('status')
        def status():
            """Print project status."""
            config = load_config()
            if config['local'] == {}:
                print('Unable to locate expipe configurations.')
                return
            assert config['local']['type'] == 'project'
            # server = expipe.load_filesystem(path.parent)
            # project = server.require_project(project_id)
            project = expipe_module.get_project(config['local_root'])
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
        def set(project_id, **kw):
            """Create a project."""
            config = load_config(project_id)
            if config['local'] == {}:
                print('Current location is not recognized as a expipe project, aborting...')
                return
            assert config['local']['type'] == 'project'
            # server = expipe.load_filesystem(path.parent)
            # project = server.require_project(project_id)
            project = expipe_module.get_project(config['local_root'])
            config['user'].update({k: v for k,v in kw.items() if v})
            config['user_root'].mkdir(exist_ok=True)
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
        def set(**kw):
            """Create a project."""
            config = load_config()
            config['global'].update({k: v for k,v in kw.items() if v})
            config['global_root'].mkdir(exist_ok=True)
            yaml_dump(config['global_path'], config['global'])

# ------------------------------------------------------------------------------
# CLI plugins
# ------------------------------------------------------------------------------


def load_cli_plugins(cli, config_dir=None):
    """Load all plugins and attach them to a CLI object."""

    plugins = discover_plugins()
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
load_cli_plugins(expipe)
