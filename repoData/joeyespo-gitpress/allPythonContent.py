__FILENAME__ = simple
"""\
Simple
Gitpress Example

An example website that uses Gitpress to listen for and serve a blog.
"""

import os
import gitpress


if __name__ == '__main__':
    gitpress.run(port=os.environ.get('PORT'))

########NEW FILE########
__FILENAME__ = building
import os
from .repository import require_repo, presentation_files
from .helpers import copy_files, remove_directory


default_out_directory = '_site'


def build(content_directory=None, out_directory=None):
    """Builds the site from its content and presentation repository."""
    content_directory = content_directory or '.'
    out_directory = os.path.abspath(out_directory or default_out_directory)
    repo = require_repo(content_directory)

    # Prevent user mistakes
    if out_directory == '.':
        raise ValueError('Output directory must be different than the source directory: ' + repr(out_directory))
    if os.path.basename(os.path.relpath(out_directory, content_directory)) == '..':
        raise ValueError('Output directory must not contain the source directory: ' + repr(out_directory))

    # TODO: read config
    # TODO: use virtualenv
    # TODO: init and run plugins
    # TODO: process with active theme

    # Collect and copy static files
    files = presentation_files(repo)
    remove_directory(out_directory)
    copy_files(files, out_directory, repo)

    return out_directory

########NEW FILE########
__FILENAME__ = command
"""\
gitpress.command
~~~~~~~~~~~~~~~~

Implements the command-line interface of Gitpress.


Usage:
  gitpress preview [<directory>] [<address>]
  gitpress build [-q] [--out <dir>] [<directory>]
  gitpress init [-q] [<directory>]
  gitpress themes [use <theme> | install <theme> | uninstall <theme>]
  gitpress plugins [add <plugin> | remove [-f] <plugin>]

Options:
  -h --help         Show this help.
  --version         Show version.
  -o --out <dir>    The directory to output the rendered site.
  -f                Force the command to continue without prompting.
  -q                Quiet mode, suppress all messages except errors.

Notes:
  <address> can take the form <host>[:<port>] or just <port>.
"""

import os
import sys
from docopt import docopt
from path_and_address import resolve, split_address
from .config import ConfigSchemaError
from .repository import init, require_repo, RepositoryAlreadyExistsError, RepositoryNotFoundError
from .previewing import preview
from .building import build
from .themes import list_themes, use_theme, ThemeNotFoundError
from .plugins import list_plugins, add_plugin, remove_plugin, get_plugin_settings
from .helpers import yes_or_no, NotADirectoryError
from . import __version__


def main(argv=None):
    """The entry point of the application."""
    if argv is None:
        argv = sys.argv[1:]
    usage = '\n\n\n'.join(__doc__.split('\n\n\n')[1:])
    version = 'Gitpress ' + __version__

    # Parse options
    args = docopt(usage, argv=argv, version=version)

    # Execute command
    try:
        return execute(args)
    except RepositoryNotFoundError as ex:
        error('No Gitpress repository found at', ex.directory)


def execute(args):
    """Executes the command indicated by the specified parsed arguments."""

    def info(*message):
        """Displays a message unless -q was specified."""
        if not args['-q']:
            print ' '.join(map(str, message))

    if args['init']:
        try:
            repo = init(args['<directory>'])
            info('Initialized Gitpress repository in', repo)
        except RepositoryAlreadyExistsError as ex:
            info('Gitpress repository already exists in', ex.repo)
        return 0

    if args['preview']:
        directory, address = resolve(args['<directory>'], args['<address>'])
        host, port = split_address(address)
        if address and not host and not port:
            error('Invalid address', repr(address))
        return preview(directory, host=host, port=port)

    if args['build']:
        require_repo(args['<directory>'])
        info('Building site', os.path.abspath(args['<directory>'] or '.'))
        try:
            out_directory = build(args['<directory>'], args['--out'])
        except NotADirectoryError as ex:
            error(ex)
        info('Site built in', os.path.abspath(out_directory))
        return 0

    if args['themes']:
        theme = args['<theme>']
        if args['use']:
            try:
                switched = use_theme(theme)
            except ConfigSchemaError as ex:
                error('Could not modify config:', ex)
                return 1
            except ThemeNotFoundError as ex:
                error('Theme %s is not currently installed.' % repr(theme))
                return 1
            info('Switched to theme %s' if switched else 'Already using %s' % repr(theme))
        elif args['install']:
            # TODO: implement
            raise NotImplementedError()
        elif args['uninstall']:
            # TODO: implement
            raise NotImplementedError()
        else:
            themes = list_themes()
            if themes:
                info('Installed themes:')
                info('  ' + '\n  '.join(themes))
            else:
                info('No themes installed.')
        return 0

    if args['plugins']:
        plugin = args['<plugin>']
        if args['add']:
            try:
                added = add_plugin(plugin)
            except ConfigSchemaError as ex:
                error('Could not modify config:', ex)
                return 1
            info(('Added plugin %s' if added else
                'Plugin %s has already been added.') % repr(plugin))
        elif args['remove']:
            settings = get_plugin_settings(plugin)
            if not args['-f'] and settings and isinstance(settings, dict):
                warning = 'Plugin %s contains settings. Remove?' % repr(plugin)
                if not yes_or_no(warning):
                    return 0
            try:
                removed = remove_plugin(plugin)
            except ConfigSchemaError as ex:
                error('Error: Could not modify config:', ex)
            info(('Removed plugin %s' if removed else
                'Plugin %s has already been removed.') % repr(plugin))
        else:
            plugins = list_plugins()
            info('Installed plugins:\n  ' + '\n  '.join(plugins) if plugins else
                'No plugins installed.')
        return 0

    return 1


def error(*message):
    sys.exit('Error: ' + ' '.join(map(str, message)))


def gpp(argv=None):
    """Shortcut function for running the previewing command."""
    if argv is None:
        argv = sys.argv[1:]
    argv.insert(0, 'preview')
    return main(argv)

########NEW FILE########
__FILENAME__ = config
import os
import errno
from collections import OrderedDict
try:
    import simplejson as json
except ImportError:
    import json


config_file = '_config.json'


class ConfigSchemaError(Exception):
    """Indicates the config does not conform to the expected types."""
    pass


def read_config(repo_directory):
    """Returns the configuration from the presentation repository."""
    return read_config_file(os.path.join(repo_directory, config_file))


def read_config_file(path):
    """Returns the configuration from the specified file."""
    try:
        with open(path, 'r') as f:
            return json.load(f, object_pairs_hook=OrderedDict)
    except IOError as ex:
        if ex != errno.ENOENT:
            raise
    return {}


def write_config(repo_directory, config):
    """Writes the specified configuration to the presentation repository."""
    return write_config_file(os.path.join(repo_directory, config_file), config)


def write_config_file(path, config):
    """Writes the specified configuration to the specified file."""
    contents = json.dumps(config, indent=4, separators=(',', ': ')) + '\n'
    try:
        with open(path, 'w') as f:
            f.write(contents)
        return True
    except IOError as ex:
        if ex != errno.ENOENT:
            raise
    return False


def get_value(repo_directory, key, expect_type=None):
    """Gets the value of the specified key in the config file."""
    config = read_config(repo_directory)
    value = config.get(key)
    if expect_type and value is not None and not isinstance(value, expect_type):
        raise ConfigSchemaError('Expected config variable %s to be type %s, got %s'
            % (repr(key), repr(expect_type), repr(type(value))))
    return value


def set_value(repo_directory, key, value, strict=True):
    """Sets the value of a particular key in the config file. This has no effect when setting to the same value."""
    if value is None:
        raise ValueError('Argument "value" must not be None.')

    # Read values and do nothing if not making any changes
    config = read_config(repo_directory)
    old = config.get(key)
    if old == value:
        return old

    # Check schema
    if strict and old is not None and not isinstance(old, type(value)):
        raise ConfigSchemaError('Expected config variable %s to be type %s, got %s'
            % (repr(key), repr(type(value)), repr(type(old))))

    # Set new value and save results
    config[key] = value
    write_config(repo_directory, config)
    return old

########NEW FILE########
__FILENAME__ = helpers
import os
import shutil


class NotADirectoryError(Exception):
    """Indicates a file was found when a directory was expected."""
    def __init__(self, directory, message=None):
        super(NotADirectoryError, self).__init__(
            'Expected a directory, found a file instead at ' + directory)
        self.directory = os.path.abspath(directory)


def remove_directory(directory, show_warnings=True):
    """Deletes a directory and its contents.
    Returns a list of errors in form (function, path, excinfo)."""
    errors = []

    def onerror(function, path, excinfo):
        if show_warnings:
            print 'Cannot delete %s: %s' % (os.path.relpath(directory), excinfo[1])
        errors.append((function, path, excinfo))

    if os.path.exists(directory):
        if not os.path.isdir(directory):
            raise NotADirectoryError(directory)
        shutil.rmtree(directory, onerror=onerror)

    return errors


def copy_files(source_files, target_directory, source_directory=None):
    """Copies a list of files to the specified directory.
    If source_directory is provided, it will be prepended to each source file."""
    try:
        os.makedirs(target_directory)
    except:     # TODO: specific exception?
        pass
    for f in source_files:
        source = os.path.join(source_directory, f) if source_directory else f
        target = os.path.join(target_directory, f)
        shutil.copy2(source, target)


def yes_or_no(message):
    """Gets user input and returns True for yes and False for no."""
    while True:
        print message, '(yes/no)',
        line = raw_input()
        if line is None:
            return None
        line = line.lower()
        if line == 'y' or line == 'ye' or line == 'yes':
            return True
        if line == 'n' or line == 'no':
            return False

########NEW FILE########
__FILENAME__ = plugins
from .config import get_value, set_value
from .repository import require_repo


def list_plugins(directory=None):
    """Gets a list of the installed themes."""
    repo = require_repo(directory)
    plugins = get_value(repo, 'plugins')
    if not plugins or not isinstance(plugins, dict):
        return None
    return plugins.keys()


def add_plugin(plugin, directory=None):
    """Adds the specified plugin. This returns False if it was already added."""
    repo = require_repo(directory)
    plugins = get_value(repo, 'plugins', expect_type=dict)
    if plugin in plugins:
        return False

    plugins[plugin] = {}
    set_value(repo, 'plugins', plugins)
    return True


def remove_plugin(plugin, directory=None):
    """Removes the specified plugin."""
    repo = require_repo(directory)
    plugins = get_value(repo, 'plugins', expect_type=dict)
    if plugin not in plugins:
        return False

    del plugins[plugin]
    set_value(repo, 'plugins', plugins)
    return True


def get_plugin_settings(plugin, directory=None):
    """Gets the settings for the specified plugin."""
    repo = require_repo(directory)
    plugins = get_value(repo, 'plugins')
    return plugins.get(plugin) if isinstance(plugins, dict) else None

########NEW FILE########
__FILENAME__ = previewing
import os
import SocketServer
import SimpleHTTPServer
from .building import build


def preview(directory=None, host=None, port=None, watch=True):
    """Runs a local server to preview the working directory of a repository."""
    directory = directory or '.'
    host = host or '127.0.0.1'
    port = port or 5000

    # TODO: admin interface

    # TODO: use cache_only to keep from modifying output directly
    out_directory = build(directory)

    # Serve generated site
    os.chdir(out_directory)
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer((host, port), Handler)
    print ' * Serving on http://%s:%s/' % (host, port)
    httpd.serve_forever()

########NEW FILE########
__FILENAME__ = repository
import os
import re
import shutil
import fnmatch
import subprocess


repo_dir = '.gitpress'
templates_path = os.path.join(os.path.dirname(__file__), 'templates')
default_template_path = os.path.join(templates_path, 'default')
specials = ['.*', '_*']
specials_re = re.compile('|'.join([fnmatch.translate(x) for x in specials]))


class RepositoryAlreadyExistsError(Exception):
    """Indicates 'repo_dir' already exists while attempting to create a new one."""
    def __init__(self, directory=None, repo=None):
        super(RepositoryAlreadyExistsError, self).__init__()
        self.directory = os.path.abspath(directory if directory else os.getcwd())
        self.repo = os.path.abspath(repo or repo_path(self.directory))


class RepositoryNotFoundError(Exception):
    """Indicates an existing 'present_dir' is required, but was not found."""
    def __init__(self, directory=None):
        super(RepositoryNotFoundError, self).__init__()
        self.directory = os.path.abspath(directory if directory else os.getcwd())


def require_repo(directory=None):
    """Checks for a presentation repository and raises an exception if not found."""
    if directory and not os.path.isdir(directory):
        raise ValueError('Directory not found: ' + repr(directory))
    repo = repo_path(directory)
    if not os.path.isdir(repo):
        raise RepositoryNotFoundError(directory)
    return repo


def repo_path(directory=None):
    """Gets the presentation repository from the specified directory."""
    return os.path.join(directory, repo_dir) if directory else repo_dir


def init(directory=None):
    """Initializes a Gitpress presentation repository at the specified directory."""
    repo = repo_path(directory)
    if os.path.isdir(repo):
        raise RepositoryAlreadyExistsError(directory, repo)

    # Initialize repository with default template
    shutil.copytree(default_template_path, repo)

    message = '"Default presentation content."'
    subprocess.call(['git', 'init', '-q', repo])
    subprocess.call(['git', 'add', '.'], cwd=repo)
    subprocess.call(['git', 'commit', '-q', '-m', message], cwd=repo)

    return repo


def presentation_files(path=None, excludes=None, includes=None):
    """Gets a list of the repository presentation files relative to 'path',
    not including themes. Note that 'includes' take priority."""
    return list(iterate_presentation_files(path, excludes, includes))


def iterate_presentation_files(path=None, excludes=None, includes=None):
    """Iterates the repository presentation files relative to 'path',
    not including themes. Note that 'includes' take priority."""

    # Defaults
    if includes is None:
        includes = []
    if excludes is None:
        excludes = []

    # Transform glob patterns to regular expressions
    includes_pattern = r'|'.join([fnmatch.translate(x) for x in includes]) or r'$.'
    excludes_pattern = r'|'.join([fnmatch.translate(x) for x in excludes]) or r'$.'
    includes_re = re.compile(includes_pattern)
    excludes_re = re.compile(excludes_pattern)

    def included(root, name):
        """Returns True if the specified file is a presentation file."""
        full_path = os.path.join(root, name)
        # Explicitly included files takes priority
        if includes_re.match(full_path):
            return True
        # Ignore special and excluded files
        return (not specials_re.match(name)
            and not excludes_re.match(full_path))

    # Get a filtered list of paths to be built
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if included(root, d)]
        files = [f for f in files if included(root, f)]
        for f in files:
            yield os.path.relpath(os.path.join(root, f), path)

########NEW FILE########
__FILENAME__ = themes
import os
from .repository import require_repo
from .config import set_value


themes_dir = '_themes'
default_theme = 'default'


class ThemeNotFoundError(Exception):
    """Indicates the requested theme was not found."""
    def __init__(self, theme):
        super(ThemeNotFoundError, self).__init__()
        self.theme = theme


def list_themes(directory=None):
    """Gets a list of the installed themes."""
    repo = require_repo(directory)
    path = os.path.join(repo, themes_dir)
    return os.listdir(path) if os.path.isdir(path) else None


def use_theme(theme, directory=None):
    """Switches to the specified theme. This returns False if switching to the already active theme."""
    repo = require_repo(directory)
    if theme not in list_themes(directory):
        raise ThemeNotFoundError(theme)

    old_theme = set_value(repo, 'theme', theme)
    return old_theme != theme

########NEW FILE########
