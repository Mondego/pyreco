__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.config
-------------------

Global configuration handling
"""

from __future__ import unicode_literals
import copy
import os

import yaml

from .exceptions import ConfigDoesNotExistException
from .utils import unicode_open
from .exceptions import InvalidConfiguration


DEFAULT_CONFIG = {
    'cookiecutters_dir': os.path.expanduser('~/.cookiecutters/'),
    'default_context': {}
}


def get_config(config_path):
    """
    Retrieve the config from the specified path, returning it as a config dict.
    """

    if not os.path.exists(config_path):
        raise ConfigDoesNotExistException

    print("config_path is {0}".format(config_path))
    with unicode_open(config_path) as file_handle:
        try:
            yaml_dict = yaml.safe_load(file_handle)
        except yaml.scanner.ScannerError:
            raise InvalidConfiguration(
                "%s is no a valid YAML file" % config_path)

    config_dict = copy.copy(DEFAULT_CONFIG)
    config_dict.update(yaml_dict)

    return config_dict


def get_user_config():
    """
    Retrieve config from the user's ~/.cookiecutterrc, if it exists.
    Otherwise, return None.
    """

    # TODO: test on windows...
    USER_CONFIG_PATH = os.path.expanduser('~/.cookiecutterrc')

    if os.path.exists(USER_CONFIG_PATH):
        return get_config(USER_CONFIG_PATH)
    return copy.copy(DEFAULT_CONFIG)

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.exceptions
-----------------------

All exceptions used in the Cookiecutter code base are defined here.
"""


class CookiecutterException(Exception):
    """
    Base exception class. All Cookiecutter-specific exceptions should subclass
    this class.
    """


class NonTemplatedInputDirException(CookiecutterException):
    """
    Raised when a project's input dir is not templated.
    The name of the input directory should always contain a string that is
    rendered to something else, so that input_dir != output_dir.
    """

class UnknownTemplateDirException(CookiecutterException):
    """
    Raised when Cookiecutter cannot determine which directory is the project
    template, e.g. more than one dir appears to be a template dir.
    """

class MissingProjectDir(CookiecutterException):
    """
    Raised during cleanup when remove_repo() can't find a generated project
    directory inside of a repo.
    """

class ConfigDoesNotExistException(CookiecutterException):
    """
    Raised when get_config() is passed a path to a config file, but no file
    is found at that path.
    """

class InvalidConfiguration(CookiecutterException):
    """
    Raised if the global configuration file is not valid YAML or is
    badly contructed.
    """

class UnknownRepoType(CookiecutterException):
    """
    Raised if a repo's type cannot be determined.
    """

########NEW FILE########
__FILENAME__ = find
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.find
-----------------

Functions for finding Cookiecutter templates and other components.
"""

import logging
import os

from .exceptions import NonTemplatedInputDirException


def find_template(repo_dir):
    """
    Determines which child directory of `repo_dir` is the project template.
    
    :param repo_dir: Local directory of newly cloned repo.
    :returns project_template: Relative path to project template.
    """

    logging.debug('Searching {0} for the project template.'.format(repo_dir))
    
    repo_dir_contents = os.listdir(repo_dir)

    project_template = None
    for item in repo_dir_contents:
        if 'cookiecutter' in item and \
            '{{' in item and \
            '}}' in item:
            project_template = item
            break

    if project_template:
        project_template = os.path.join(repo_dir, project_template)
        logging.debug('The project template appears to be {0}'.format(project_template))
        return project_template
    else:
        raise NonTemplatedInputDirException
########NEW FILE########
__FILENAME__ = generate
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.generate
---------------------

Functions for generating a project from a project template.
"""
from __future__ import unicode_literals
import logging
import os
import shutil
import sys

from jinja2 import FileSystemLoader, Template
from jinja2.environment import Environment
from jinja2.exceptions import TemplateSyntaxError
from binaryornot.check import is_binary

from .exceptions import NonTemplatedInputDirException
from .find import find_template
from .utils import make_sure_path_exists, unicode_open, work_in
from .hooks import run_hook


if sys.version_info[:2] < (2, 7):
    import simplejson as json
    from ordereddict import OrderedDict
else:
    import json
    from collections import OrderedDict


def generate_context(context_file='cookiecutter.json', default_context=None):
    """
    Generates the context for a Cookiecutter project template.
    Loads the JSON file as a Python object, with key being the JSON filename.

    :param context_file: JSON file containing key/value pairs for populating
        the cookiecutter's variables.
    :param config_dict: Dict containing any config to take into account.
    """

    context = {}

    file_handle = open(context_file)
    obj = json.load(file_handle, encoding='utf-8', object_pairs_hook=OrderedDict)

    # Add the Python object to the context dictionary
    file_name = os.path.split(context_file)[1]
    file_stem = file_name.split('.')[0]
    context[file_stem] = obj

    # Overwrite context variable defaults with the default context from the
    # user's global config, if available
    if default_context:
        obj.update(default_context)

    logging.debug('Context generated is {0}'.format(context))
    return context


def generate_file(project_dir, infile, context, env):
    """
    1. Render the filename of infile as the name of outfile.
    2. Deal with infile appropriately:

        a. If infile is a binary file, copy it over without rendering.
        b. If infile is a text file, render its contents and write the
           rendered infile to outfile.

    Precondition:

        When calling `generate_file()`, the root template dir must be the
        current working directory. Using `utils.work_in()` is the recommended
        way to perform this directory change.

    :param project_dir: Absolute path to the resulting generated project.
    :param infile: Input file to generate the file from. Relative to the root
        template dir.
    :param context: Dict for populating the cookiecutter's variables.
    :param env: Jinja2 template execution environment.
    """

    logging.debug("Generating file {0}".format(infile))

    # Render the path to the output file (not including the root project dir)
    outfile_tmpl = Template(infile)
    outfile = os.path.join(project_dir, outfile_tmpl.render(**context))
    logging.debug("outfile is {0}".format(outfile))

    # Just copy over binary files. Don't render.
    logging.debug("Check {0} to see if it's a binary".format(infile))
    if is_binary(infile):
        logging.debug("Copying binary {0} to {1} without rendering"
                      .format(infile, outfile))
        shutil.copyfile(infile, outfile)
    else:
        # Force fwd slashes on Windows for get_template
        # This is a by-design Jinja issue
        infile_fwd_slashes = infile.replace(os.path.sep, '/')

        # Render the file
        try:
            tmpl = env.get_template(infile_fwd_slashes)
        except TemplateSyntaxError as exception:
            # Disable translated so that printed exception contains verbose
            # information about syntax error location
            exception.translated = False
            raise
        rendered_file = tmpl.render(**context)

        logging.debug("Writing {0}".format(outfile))

        with unicode_open(outfile, 'w') as fh:
            fh.write(rendered_file)

    # Apply file permissions to output file
    shutil.copymode(infile, outfile)


def render_and_create_dir(dirname, context, output_dir):
    """
    Renders the name of a directory, creates the directory, and returns its path.
    """

    name_tmpl = Template(dirname)
    rendered_dirname = name_tmpl.render(**context)
    logging.debug('Rendered dir {0} must exist in output_dir {1}'.format(
        rendered_dirname,
        output_dir
    ))
    dir_to_create = os.path.normpath(
        os.path.join(output_dir, rendered_dirname)
    )
    make_sure_path_exists(dir_to_create)
    return dir_to_create


def ensure_dir_is_templated(dirname):
    """
    Ensures that dirname is a templated directory name.
    """
    if '{{' in dirname and \
        '}}' in dirname:
        return True
    else:
        raise NonTemplatedInputDirException


def generate_files(repo_dir, context=None, output_dir="."):
    """
    Renders the templates and saves them to files.

    :param repo_dir: Project template input directory.
    :param context: Dict for populating the template's variables.
    :param output_dir: Where to output the generated project dir into.
    """

    template_dir = find_template(repo_dir)
    logging.debug('Generating project from {0}...'.format(template_dir))
    context = context or {}

    unrendered_dir = os.path.split(template_dir)[1]
    ensure_dir_is_templated(unrendered_dir)
    project_dir = render_and_create_dir(unrendered_dir, context, output_dir)

    # We want the Jinja path and the OS paths to match. Consequently, we'll:
    #   + CD to the template folder
    #   + Set Jinja's path to "."
    #
    #  In order to build our files to the correct folder(s), we'll use an
    # absolute path for the target folder (project_dir)

    project_dir = os.path.abspath(project_dir)
    logging.debug("project_dir is {0}".format(project_dir))

    # run pre-gen hook from repo_dir
    with work_in(repo_dir):
        run_hook('pre_gen_project', project_dir)

    with work_in(template_dir):
        env = Environment()
        env.loader = FileSystemLoader(".")

        for root, dirs, files in os.walk("."):
            for d in dirs:
                unrendered_dir = os.path.join(project_dir, os.path.join(root, d))
                render_and_create_dir(unrendered_dir, context, output_dir)

            for f in files:
                infile = os.path.join(root, f)
                logging.debug("f is {0}".format(f))
                generate_file(project_dir, infile, context, env)

    # run post-gen hook from repo_dir
    with work_in(repo_dir):
        run_hook('post_gen_project', project_dir)

########NEW FILE########
__FILENAME__ = hooks
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.hooks
------------------

Functions for discovering and executing various cookiecutter hooks.
"""

import logging
import os
import subprocess
import sys

from .utils import make_sure_path_exists, unicode_open, work_in

_HOOKS = [
    'pre_gen_project',
    'post_gen_project',
    # TODO: other hooks should be listed here
]

def find_hooks():
    '''
    Must be called with the project template as the current working directory.
    Returns a dict of all hook scripts provided.
    Dict's key will be the hook/script's name, without extension, while
    values will be the absolute path to the script.
    Missing scripts will not be included in the returned dict.
    '''
    hooks_dir = 'hooks'
    r = {}
    logging.debug("hooks_dir is {0}".format(hooks_dir))
    if not os.path.isdir(hooks_dir):
        logging.debug("No hooks/ dir in template_dir")
        return r
    for f in os.listdir(hooks_dir):
        basename = os.path.splitext(os.path.basename(f))[0]
        if basename in _HOOKS:
            r[basename] = os.path.abspath(os.path.join(hooks_dir, f))
    return r


def _run_hook(script_path, cwd='.'):
    '''
    Run a sigle external script located at `script_path` (path should be
    absolute).
    If `cwd` is provided, the script will be run from that directory.
    '''
    run_thru_shell = sys.platform.startswith('win')
    if script_path.endswith('.py'):
        script_command = [sys.executable, script_path]
    else:
        script_command = [script_path]
    proc = subprocess.Popen(
        script_command,
        shell=run_thru_shell,
        cwd=cwd
    )
    proc.wait()

def run_hook(hook_name, project_dir):
    '''
    Try and find a script mapped to `hook_name` in the current working directory,
    and execute it from `project_dir`.
    '''
    script = find_hooks().get(hook_name)
    if script is None:
        logging.debug("No hooks found")
        return
    return _run_hook(script, project_dir)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.main
-----------------

Main entry point for the `cookiecutter` command.

The code in this module is also a good example of how to use Cookiecutter as a
library rather than a script.
"""

from __future__ import unicode_literals
import argparse
import logging
import os
import sys

from . import __version__
from .config import get_user_config
from .prompt import prompt_for_config
from .generate import generate_context, generate_files
from .vcs import clone

logger = logging.getLogger(__name__)


def cookiecutter(input_dir, checkout=None, no_input=False):
    """
    API equivalent to using Cookiecutter at the command line.

    :param input_dir: A directory containing a project template dir,
        or a URL to git repo.
    :param checkout: The branch, tag or commit ID to checkout after clone
    """

    # Get user config from ~/.cookiecutterrc or equivalent
    # If no config file, sensible defaults from config.DEFAULT_CONFIG are used
    config_dict = get_user_config()

    # TODO: find a better way to tell if it's a repo URL
    if "git@" in input_dir or "https://" in input_dir:
        repo_dir = clone(
            repo_url=input_dir,
            checkout=checkout,
            clone_to_dir=config_dict['cookiecutters_dir']
        )
    else:
        # If it's a local repo, no need to clone or copy to your cookiecutters_dir
        repo_dir = input_dir

    context_file = os.path.join(repo_dir, 'cookiecutter.json')
    logging.debug('context_file is {0}'.format(context_file))

    context = generate_context(
        context_file=context_file,
        default_context=config_dict['default_context']
    )

    # prompt the user to manually configure at the command line.
    # except when 'no-input' flag is set
    if not no_input:
        cookiecutter_dict = prompt_for_config(context)
        context['cookiecutter'] = cookiecutter_dict

    # Create project from local context and project template.
    generate_files(
        repo_dir=repo_dir,
        context=context
    )


def _get_parser():
    parser = argparse.ArgumentParser(
        description='Create a project from a Cookiecutter project template.'
    )
    parser.add_argument(
        '--no-input',
        action="store_true",
        help='Do not prompt for parameters and only use cookiecutter.json '
             'file content')
    parser.add_argument(
        'input_dir',
        help='Cookiecutter project dir, e.g. cookiecutter-pypackage/'
    )
    parser.add_argument(
        '-c', '--checkout',
        help='branch, tag or commit to checkout after git clone'
    )
    cookiecutter_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument(
        '-V', '--version',
        help="Show version information and exit.",
        action='version',
        version='Cookiecutter %s from %s (Python %s)' % (
            __version__,
            cookiecutter_pkg_dir,
            sys.version[:3]
        )
    )
    parser.add_argument(
        '-v', '--verbose',
        help='Print debug information',
        action='store_true', default=False
    )

    return parser

def parse_cookiecutter_args(args):
    """ Parse the command-line arguments to Cookiecutter. """
    parser = _get_parser()
    return parser.parse_args(args)


def main():
    """ Entry point for the package, as defined in setup.py. """

    args = parse_cookiecutter_args(sys.argv[1:])

    if args.verbose:
        logging.basicConfig(format='%(levelname)s %(filename)s: %(message)s', level=logging.DEBUG)
    else:
        # Log info and above to console
        logging.basicConfig(
            format='%(levelname)s: %(message)s',
            level=logging.INFO
        )

    cookiecutter(args.input_dir, args.checkout, args.no_input)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = prompt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.prompt
---------------------

Functions for prompting the user for project info.
"""

from __future__ import unicode_literals
import sys

PY3 = sys.version > '3'
if PY3:
    iteritems = lambda d: iter(d.items())
else:
    input = raw_input
    iteritems = lambda d: d.iteritems()


def prompt_for_config(context):
    """
    Prompts the user to enter new config, using context as a source for the
    field names and sample values.
    """
    cookiecutter_dict = {}

    for key, val in iteritems(context['cookiecutter']):
        prompt = "{0} (default is \"{1}\")? ".format(key, val)

        if PY3:
            new_val = input(prompt.encode('utf-8'))
        else:
            new_val = input(prompt.encode('utf-8')).decode('utf-8')

        new_val = new_val.strip()

        if new_val == '':
            new_val = val

        cookiecutter_dict[key] = new_val
    return cookiecutter_dict


def query_yes_no(question, default="yes"):
    """
    Ask a yes/no question via `raw_input()` and return their answer.

    :param question: A string that is presented to the user.
    :param default: The presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".

    Adapted from
    http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
    http://code.activestate.com/recipes/577058/

    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()

        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.utils
------------------

Helper functions used throughout Cookiecutter.
"""

from __future__ import unicode_literals
import errno
import logging
import os
import sys
import contextlib


PY3 = sys.version > '3'
if PY3:
    pass
else:
    import codecs


def make_sure_path_exists(path):
    """
    Ensures that a directory exists.
    :param path: A directory path.
    """
    
    logging.debug("Making sure path exists: {0}".format(path))
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            return False
    return True


def unicode_open(filename, *args, **kwargs):
    """
    Opens a file as usual on Python 3, and with UTF-8 encoding on Python 2.
    :param filename: Name of file to open.
    """
    kwargs['encoding'] = "utf-8"
    if PY3:
        return open(filename, *args, **kwargs)
    return codecs.open(filename, *args, **kwargs)


@contextlib.contextmanager
def work_in(dirname=None):
    """
    Context manager version of os.chdir. When exited, returns to the working
    directory prior to entering.
    """
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)

########NEW FILE########
__FILENAME__ = vcs
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.vcs
----------------

Helper functions for working with version control systems.
"""

from __future__ import unicode_literals
import logging
import os
import shutil
import subprocess
import sys

from .exceptions import UnknownRepoType
from .prompt import query_yes_no
from .utils import make_sure_path_exists


def prompt_and_delete_repo(repo_dir):
    """
    Asks the user whether it's okay to delete the previously-cloned repo.
    If yes, deletes it. Otherwise, Cookiecutter exits.
    :param repo_dir: Directory of previously-cloned repo.
    """

    ok_to_delete = query_yes_no("You've cloned {0} before. "
        "Is it okay to delete and re-clone it?".format(repo_dir),
        default="yes"
    )
    if ok_to_delete:
        shutil.rmtree(repo_dir)
    else:
        sys.exit()


def identify_repo(repo_url):
    """
    Determines if `repo_url` should be treated as a URL to a git or hg repo.
    :param repo_url: Repo URL of unknown type.
    :returns: "git", "hg", or None.
    """
    
    if "git" in repo_url:
        return "git"
    elif "bitbucket" in repo_url:
        return "hg"
    else:
        raise UnknownRepoType


def clone(repo_url, checkout=None, clone_to_dir="."):
    """
    Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone
    """

    # Ensure that clone_to_dir exists
    clone_to_dir = os.path.expanduser(clone_to_dir)
    make_sure_path_exists(clone_to_dir)
    
    repo_type = identify_repo(repo_url)
    
    tail = os.path.split(repo_url)[1]
    if repo_type == "git":
        repo_dir = os.path.normpath(os.path.join(clone_to_dir, tail.rsplit('.git')[0]))
    elif repo_type == "hg":
        repo_dir = os.path.normpath(os.path.join(clone_to_dir, tail))
    logging.debug('repo_dir is {0}'.format(repo_dir))

    if os.path.isdir(repo_dir):
        prompt_and_delete_repo(repo_dir)

    if repo_type in ["git", "hg"]:
        subprocess.check_call([repo_type, 'clone', repo_url], cwd=clone_to_dir)
        if checkout is not None:
            subprocess.check_call([repo_type, 'checkout', checkout], cwd=repo_dir)

    return repo_dir

########NEW FILE########
__FILENAME__ = ccext
# -*- coding: utf-8 -*-
import sys
from cookiecutter import main
from docutils import nodes
from docutils.parsers import rst
from docutils.statemachine import ViewList


class CcCommandLineOptions(rst.Directive):
    def _format_action(self, action):
        bookmark_line = ".. _`%s`:" % action.dest
        line = ".. option:: "
        line += ", ".join(action.option_strings)
        opt_help = action.help.replace('%default', str(action.default))

        # fix paths with sys.prefix
        opt_help = opt_help.replace(sys.prefix, "<sys.prefix>")

        return [bookmark_line, "", line, "", " %s" % opt_help, ""]

    def process_actions(self):
        parser = main._get_parser()
        for action in parser._actions:
            if not action.option_strings:
                continue
            for line in self._format_action(action):
                self.view_list.append(line, "")

    def run(self):
        node = nodes.paragraph()
        node.document = self.state.document
        self.view_list = ViewList()
        self.process_actions()
        self.state.nested_parse(self.view_list, 0, node)
        return [node]


def setup(app):
    app.add_directive('cc-command-line-options', CcCommandLineOptions)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# cookiecutter documentation build configuration file, created by
# sphinx-quickstart on Thu Jul 11 11:31:49 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# For building docs in foreign environments where we don't have all our
# dependencies (like readthedocs), mock out imports that cause sphinx to fail.
# see: https://docs.readthedocs.org/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules

import sys

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            mockType = type(name, (), {})
            mockType.__module__ = __name__
            return mockType
        else:
            return Mock()

MOCK_MODULES = ['yaml']
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()


# Add parent dir to path
cwd = os.getcwd()
parent = os.path.dirname(cwd)
sys.path.append(parent)

import cookiecutter

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx',
              'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath',
              'sphinx.ext.ifconfig', 'sphinx.ext.viewcode', 'docs.ccext']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'cookiecutter'
copyright = u'2013, Audrey Roy'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = cookiecutter.__version__
# The full version, including alpha/beta/rc tags.
release = cookiecutter.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'cookiecutterdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'cookiecutter.tex', u'cookiecutter Documentation',
   u'Audrey Roy', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cookiecutter', u'cookiecutter Documentation',
     [u'Audrey Roy'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'cookiecutter', u'cookiecutter Documentation',
   u'Audrey Roy', 'cookiecutter', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'cookiecutter'
epub_author = u'Audrey Roy'
epub_publisher = u'Audrey Roy'
epub_copyright = u'2013, Audrey Roy'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
#epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

# Fix unsupported image types using the PIL.
#epub_fix_images = False

# Scale large images.
#epub_max_image_width = 0

# If 'no', URL addresses will not be shown.
#epub_show_urls = 'inline'

# If false, no index is generated.
#epub_use_index = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = pre_gen_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

print('pre generation hook')
f = open('python_pre.txt', 'w')
f.close()


########NEW FILE########
__FILENAME__ = {{cookiecutter.filename}}
print("This is the contents of {{ cookiecutter.filename }}.py.")


########NEW FILE########
__FILENAME__ = post_gen_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

print('pre generation hook')
f = open('python_post.txt', 'w')
f.close()


########NEW FILE########
__FILENAME__ = pre_gen_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

print('pre generation hook')
f = open('python_pre.txt', 'w')
f.close()


########NEW FILE########
__FILENAME__ = post_gen_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

print('pre generation hook')
f = open('python_post.txt', 'w')
f.close()


########NEW FILE########
__FILENAME__ = pre_gen_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

print('pre generation hook')
f = open('python_pre.txt', 'w')
f.close()


########NEW FILE########
__FILENAME__ = test_config
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_config
-----------

Tests for `cookiecutter.config` module.
"""

import os
import shutil
import sys
import unittest

import yaml

from cookiecutter import config
from cookiecutter.exceptions import ConfigDoesNotExistException, InvalidConfiguration

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestGetConfig(unittest.TestCase):

    def test_get_config(self):
        """ Opening and reading config file """
        conf = config.get_config('tests/test-config/valid-config.yaml')
        expected_conf = {
        	'cookiecutters_dir': '/home/example/some-path-to-templates',
        	'default_context': {
        		"full_name": "Firstname Lastname",
        		"email": "firstname.lastname@gmail.com",
        		"github_username": "example"
        	}
        }
        self.assertEqual(conf, expected_conf)

    def test_get_config_does_not_exist(self):
        """
        Check that `exceptions.ConfigDoesNotExistException` is raised when
        attempting to get a non-existent config file.
        """
        self.assertRaises(
            ConfigDoesNotExistException,
            config.get_config,
            'tests/test-config/this-does-not-exist.yaml'
        )

    def test_invalid_config(self):
        """
        An invalid config file should raise an `InvalidConfiguration` exception.
        """
        self.assertRaises(InvalidConfiguration, config.get_config,
                          "tests/test-config/invalid-config.yaml")


class TestGetConfigWithDefaults(unittest.TestCase):

    def test_get_config_with_defaults(self):
        """ A config file that overrides 1 of 2 defaults """
        
        conf = config.get_config('tests/test-config/valid-partial-config.yaml')
        default_cookiecutters_dir = os.path.expanduser('~/.cookiecutters/')
        expected_conf = {
        	'cookiecutters_dir': default_cookiecutters_dir,
        	'default_context': {
        		"full_name": "Firstname Lastname",
        		"email": "firstname.lastname@gmail.com",
        		"github_username": "example"
        	}
        }
        self.assertEqual(conf, expected_conf)


class TestGetUserConfig(unittest.TestCase):

    def setUp(self):
        self.user_config_path = os.path.expanduser('~/.cookiecutterrc')
        self.user_config_path_backup = os.path.expanduser(
            '~/.cookiecutterrc.backup'
        )

        # If ~/.cookiecutterrc is pre-existing, move it to a temp location
        if os.path.exists(self.user_config_path):
            shutil.copy(self.user_config_path, self.user_config_path_backup)
            os.remove(self.user_config_path)

    def tearDown(self):
        # If it existed, restore ~/.cookiecutterrc
        if os.path.exists(self.user_config_path_backup):
            shutil.copy(self.user_config_path_backup, self.user_config_path)
            os.remove(self.user_config_path_backup)


    def test_get_user_config_valid(self):
        """ Get config from a valid ~/.cookiecutterrc file """
        shutil.copy('tests/test-config/valid-config.yaml', self.user_config_path)
        conf = config.get_user_config()
        expected_conf = {
        	'cookiecutters_dir': '/home/example/some-path-to-templates',
        	'default_context': {
        		"full_name": "Firstname Lastname",
        		"email": "firstname.lastname@gmail.com",
        		"github_username": "example"
        	}
        }
        self.assertEqual(conf, expected_conf)

    def test_get_user_config_invalid(self):
        """ Get config from an invalid ~/.cookiecutterrc file """
        shutil.copy('tests/test-config/invalid-config.yaml', self.user_config_path)
        self.assertRaises(InvalidConfiguration, config.get_user_config)

    def test_get_user_config_nonexistent(self):
        """ Get config from a nonexistent ~/.cookiecutterrc file """
        self.assertEqual(config.get_user_config(), config.DEFAULT_CONFIG)
        



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_examples
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_examples
--------------

Tests for the Cookiecutter example repos.
"""

from __future__ import unicode_literals
import errno
import logging
import os
import shutil
import subprocess
import sys

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import patch
    input_str = 'builtins.input'
    from io import StringIO
else:
    import __builtin__
    from mock import patch
    input_str = '__builtin__.raw_input'
    from cStringIO import StringIO

if sys.version_info[:3] < (2, 7):
    import unittest2 as unittest
else:
    import unittest

try:
    travis = os.environ[u'TRAVIS']
except KeyError:
    travis = False

try:
    no_network = os.environ[u'DISABLE_NETWORK_TESTS']
except KeyError:
    no_network = False

from cookiecutter import config, utils
from tests import force_delete, CookiecutterCleanSystemTestCase


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)


@unittest.skipIf(condition=travis, reason='Works locally with tox but fails on Travis.')
@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub.')
class TestPyPackage(CookiecutterCleanSystemTestCase):


    def tearDown(self):
        if os.path.isdir('cookiecutter-pypackage'):
            shutil.rmtree('cookiecutter-pypackage', onerror=force_delete)
        if os.path.isdir('boilerplate'):
            shutil.rmtree('boilerplate', onerror=force_delete)
        super(TestPyPackage, self).tearDown()

    def test_cookiecutter_pypackage(self):
        """
        Tests that https://github.com/audreyr/cookiecutter-pypackage.git works.
        """

        proc = subprocess.Popen(
            'git clone https://github.com/audreyr/cookiecutter-pypackage.git',
            stdin=subprocess.PIPE,
            shell=True
        )
        proc.wait()

        proc = subprocess.Popen(
            'cookiecutter --no-input cookiecutter-pypackage/',
            stdin=subprocess.PIPE,
            shell=True
        )
        proc.wait()

        self.assertTrue(os.path.isdir('cookiecutter-pypackage'))
        self.assertTrue(os.path.isfile('boilerplate/README.rst'))


@unittest.skipIf(condition=travis, reason='Works locally with tox but fails on Travis.')
@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub.')
class TestJQuery(CookiecutterCleanSystemTestCase):


    def tearDown(self):
        if os.path.isdir('cookiecutter-jquery'):
            shutil.rmtree('cookiecutter-jquery', onerror=force_delete)
        if os.path.isdir('boilerplate'):
            shutil.rmtree('boilerplate', onerror=force_delete)
        super(TestJQuery, self).tearDown()

    def test_cookiecutter_jquery(self):
        """
        Tests that https://github.com/audreyr/cookiecutter-jquery.git works.
        """

        proc = subprocess.Popen(
            'git clone https://github.com/audreyr/cookiecutter-jquery.git',
            stdin=subprocess.PIPE,
            shell=True
        )
        proc.wait()

        proc = subprocess.Popen(
            'cookiecutter --no-input cookiecutter-jquery/',
            stdin=subprocess.PIPE,
            shell=True
        )
        proc.wait()

        self.assertTrue(os.path.isdir('cookiecutter-jquery'))
        self.assertTrue(os.path.isfile('boilerplate/README.md'))


@unittest.skipIf(condition=travis, reason='Works locally with tox but fails on Travis.')
@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub.')
class TestExamplesRepoArg(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        with utils.work_in(config.DEFAULT_CONFIG['cookiecutters_dir']):
            if os.path.isdir('cookiecutter-pypackage'):
                shutil.rmtree('cookiecutter-pypackage', onerror=force_delete)
        if os.path.isdir('boilerplate'):
            shutil.rmtree('boilerplate', onerror=force_delete)
        super(TestExamplesRepoArg, self).tearDown()

    def test_cookiecutter_pypackage_git(self):
        proc = subprocess.Popen(
            'cookiecutter https://github.com/audreyr/cookiecutter-pypackage.git',
            stdin=subprocess.PIPE,
            shell=True
        )

        # Just skip all the prompts
        proc.communicate(input=b'\n\n\n\n\n\n\n\n\n\n\n\n')
        
        self.assertTrue(os.path.isfile('boilerplate/README.rst'))



@unittest.skipIf(condition=travis, reason='Works locally with tox but fails on Travis.')
@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub.')
class TestGitBranch(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        with utils.work_in(config.DEFAULT_CONFIG['cookiecutters_dir']):
            if os.path.isdir('cookiecutter-pypackage'):
                shutil.rmtree('cookiecutter-pypackage', onerror=force_delete)
        if os.path.isdir('boilerplate'):
            shutil.rmtree('boilerplate', onerror=force_delete)
        super(TestGitBranch, self).tearDown()

    def test_branch(self):
        proc = subprocess.Popen(
            'cookiecutter -c console-script https://github.com/audreyr/cookiecutter-pypackage.git',
            stdin=subprocess.PIPE,
            shell=True
        )

        # Just skip all the prompts
        proc.communicate(input=b'\n\n\n\n\n\n\n\n\n\n\n\n')

        self.assertTrue(os.path.isfile('boilerplate/README.rst'))
        self.assertTrue(os.path.isfile('boilerplate/boilerplate/main.py'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_find
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_find
------------

Tests for `cookiecutter.find` module.
"""

import os
import shutil
import unittest

from cookiecutter import find


class TestFindTemplate(unittest.TestCase):

    def test_find_template(self):
        template = find.find_template(repo_dir='tests/fake-repo-pre'.replace("/", os.sep))
        test_dir = 'tests/fake-repo-pre/{{cookiecutter.repo_name}}'.replace("/", os.sep)
        self.assertEqual(template, test_dir)
        test_dir = 'tests/fake-repo-pre/{{cookiecutter.repo_name }}'.replace("/", os.sep)
        self.assertNotEqual(template, test_dir)
        test_dir = 'tests/fake-repo-pre/{{ cookiecutter.repo_name }}'.replace("/", os.sep)
        self.assertNotEqual(template, test_dir)


class TestFindTemplate2(unittest.TestCase):

    def test_find_template(self):
        template = find.find_template(repo_dir='tests/fake-repo-pre2'.replace("/", os.sep))
        test_dir = 'tests/fake-repo-pre2/{{cookiecutter.repo_name}}'.replace("/", os.sep)
        self.assertEqual(template, test_dir)
        test_dir = 'tests/fake-repo-pre2/{{cookiecutter.repo_name }}'.replace("/", os.sep)
        self.assertNotEqual(template, test_dir)
        test_dir = 'tests/fake-repo-pre2/{{ cookiecutter.repo_name }}'.replace("/", os.sep)
        self.assertNotEqual(template, test_dir)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_generate
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_generate
--------------

Tests for `cookiecutter.generate` module.
"""
from __future__ import unicode_literals
import logging
import os
import shutil
import sys
import unittest

from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from jinja2.exceptions import TemplateSyntaxError

from cookiecutter import generate
from cookiecutter import exceptions
from tests import CookiecutterCleanSystemTestCase


PY3 = sys.version > '3'

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

class TestGenerateFile(unittest.TestCase):

    def test_generate_file(self):
        env = Environment()
        env.loader = FileSystemLoader('.')
        infile = 'tests/files/{{generate_file}}.txt'
        generate.generate_file(
            project_dir=".",
            infile=infile,
            context={'generate_file': 'cheese'},
            env=env
        )
        self.assertTrue(os.path.isfile('tests/files/cheese.txt'))
        with open('tests/files/cheese.txt', 'rt') as f:
            generated_text = f.read()
            self.assertEqual(generated_text, 'Testing cheese')

    def test_generate_file_verbose_template_syntax_error(self):
        env = Environment()
        env.loader = FileSystemLoader('.')
        try:
            generate.generate_file(
                project_dir=".",
                infile='tests/files/syntax_error.txt',
                context={'syntax_error': 'syntax_error'},
                env=env
            )
        except TemplateSyntaxError as exception:
            expected = (
                'Missing end of comment tag\n'
                '  File "./tests/files/syntax_error.txt", line 1\n'
                '    I eat {{ syntax_error }} {# this comment is not closed}'
            )
            expected = expected.replace("/", os.sep)
            self.assertEquals(str(exception), expected)
        except exception:
            self.fail('Unexpected exception thrown:', exception)
        else:
            self.fail('TemplateSyntaxError not thrown')

    def tearDown(self):
        if os.path.exists('tests/files/cheese.txt'):
            os.remove('tests/files/cheese.txt')


class TestGenerateFiles(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        if os.path.exists('inputpizzä'):
            shutil.rmtree('inputpizzä')
        if os.path.exists('inputgreen'):
            shutil.rmtree('inputgreen')
        if os.path.exists('inputbinary_files'):
            shutil.rmtree('inputbinary_files')
        if os.path.exists('tests/custom_output_dir'):
            shutil.rmtree('tests/custom_output_dir')
        if os.path.exists('inputpermissions'):
            shutil.rmtree('inputpermissions')
        super(TestGenerateFiles, self).tearDown()

    def test_generate_files_nontemplated_exception(self):
        self.assertRaises(
            exceptions.NonTemplatedInputDirException,
            generate.generate_files,
            context={
                'cookiecutter': {'food': 'pizza'}
            },
            repo_dir='tests/test-generate-files-nontemplated'
        )

    def test_generate_files(self):
        generate.generate_files(
            context={
                'cookiecutter': {'food': 'pizzä'}
            },
            repo_dir='tests/test-generate-files'
        )
        self.assertTrue(os.path.isfile('inputpizzä/simple.txt'))
        simple_text = open('inputpizzä/simple.txt', 'rt').read()
        if PY3:
            self.assertEqual(simple_text, 'I eat pizzä')
        else:
            self.assertEqual(simple_text, 'I eat pizzä'.encode('utf-8'))

    def test_generate_files_binaries(self):
        generate.generate_files(
            context={
                'cookiecutter': {'binary_test': 'binary_files'}
            },
            repo_dir='tests/test-generate-binaries'
        )
        self.assertTrue(os.path.isfile('inputbinary_files/logo.png'))
        self.assertTrue(os.path.isfile('inputbinary_files/.DS_Store'))
        self.assertTrue(os.path.isfile('inputbinary_files/readme.txt'))
        self.assertTrue(
            os.path.isfile('inputbinary_files/some_font.otf')
        )
        self.assertTrue(
            os.path.isfile('inputbinary_files/binary_files/logo.png')
        )
        self.assertTrue(
            os.path.isfile('inputbinary_files/binary_files/.DS_Store')
        )
        self.assertTrue(
            os.path.isfile('inputbinary_files/binary_files/readme.txt')
        )
        self.assertTrue(
            os.path.isfile('inputbinary_files/binary_files/some_font.otf')
        )
        self.assertTrue(
            os.path.isfile('inputbinary_files/binary_files/binary_files/logo.png')
        )

    def test_generate_files_absolute_path(self):
        generate.generate_files(
            context={
                'cookiecutter': {'food': 'pizzä'}
            },
            repo_dir=os.path.abspath('tests/test-generate-files')
        )
        self.assertTrue(os.path.isfile('inputpizzä/simple.txt'))

    def test_generate_files_output_dir(self):
        os.mkdir('tests/custom_output_dir')
        generate.generate_files(
            context={
                'cookiecutter': {'food': 'pizzä'}
            },
            repo_dir=os.path.abspath('tests/test-generate-files'),
            output_dir='tests/custom_output_dir'
        )
        self.assertTrue(os.path.isfile('tests/custom_output_dir/inputpizzä/simple.txt'))

    def test_generate_files_permissions(self):
        """
        simple.txt and script.sh should retain their respective 0o644 and
        0o755 permissions
        """
        generate.generate_files(
            context={
                'cookiecutter': {'permissions': 'permissions'}
            },
            repo_dir='tests/test-generate-files-permissions'
        )

        self.assertTrue(os.path.isfile('inputpermissions/simple.txt'))

        # simple.txt should still be 0o644
        self.assertEquals(
            os.stat('tests/test-generate-files-permissions/input{{cookiecutter.permissions}}/simple.txt').st_mode & 0o777,
            os.stat('inputpermissions/simple.txt').st_mode & 0o777
        )

        self.assertTrue(os.path.isfile('inputpermissions/script.sh'))

        # script.sh should still be 0o755
        self.assertEquals(
            os.stat('tests/test-generate-files-permissions/input{{cookiecutter.permissions}}/script.sh').st_mode & 0o777,
            os.stat('inputpermissions/script.sh').st_mode & 0o777
        )


class TestGenerateContext(CookiecutterCleanSystemTestCase):

    def test_generate_context(self):
        context = generate.generate_context(
            context_file='tests/test-generate-context/test.json'
        )
        self.assertEqual(context, {"test": {"1": 2, "some_key": "some_val"}})

    def test_generate_context_with_default(self):
        context = generate.generate_context(
            context_file='tests/test-generate-context/test.json',
            default_context={"1": 3}
        )
        self.assertEqual(context, {"test": {"1": 3, "some_key": "some_val"}})


class TestOutputFolder(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        if os.path.exists('output_folder'):
            shutil.rmtree('output_folder')
        super(TestOutputFolder, self).tearDown()

    def test_output_folder(self):
        context = generate.generate_context(
            context_file='tests/test-output-folder/cookiecutter.json'
        )
        logging.debug('Context is {0}'.format(context))
        generate.generate_files(
            context=context,
            repo_dir='tests/test-output-folder'
        )

        something = """Hi!
My name is Audrey Greenfeld.
It is 2014."""
        something2 = open('output_folder/something.txt').read()
        self.assertEqual(something, something2)

        in_folder = "The color is green and the letter is D."
        in_folder2 = open('output_folder/folder/in_folder.txt').read()
        self.assertEqual(in_folder, in_folder2)

        self.assertTrue(os.path.isdir('output_folder/im_a.dir'))
        self.assertTrue(os.path.isfile('output_folder/im_a.dir/im_a.file.py'))


class TestHooks(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        if os.path.exists('tests/test-pyhooks/inputpyhooks'):
            shutil.rmtree('tests/test-pyhooks/inputpyhooks')
        if os.path.exists('inputpyhooks'):
            shutil.rmtree('inputpyhooks')
        if os.path.exists('tests/test-shellhooks/inputshellhooks'):
            shutil.rmtree('tests/test-shellhooks/inputshellhooks')
        super(TestHooks, self).tearDown()

    def test_ignore_hooks_dirs(self):
        generate.generate_files(
            context={
                'cookiecutter' : {'pyhooks': 'pyhooks'}
            },
            repo_dir='tests/test-pyhooks/',
            output_dir='tests/test-pyhooks/'
        )
        self.assertFalse(os.path.exists('tests/test-pyhooks/inputpyhooks/hooks'))

    def test_run_python_hooks(self):
        generate.generate_files(
            context={
                'cookiecutter' : {'pyhooks': 'pyhooks'}
            },
            repo_dir='tests/test-pyhooks/'.replace("/", os.sep),
            output_dir='tests/test-pyhooks/'.replace("/", os.sep)
        )
        self.assertTrue(os.path.exists('tests/test-pyhooks/inputpyhooks/python_pre.txt'))
        self.assertTrue(os.path.exists('tests/test-pyhooks/inputpyhooks/python_post.txt'))

    def test_run_python_hooks_cwd(self):
        generate.generate_files(
            context={
                'cookiecutter' : {'pyhooks': 'pyhooks'}
            },
            repo_dir='tests/test-pyhooks/'
        )
        self.assertTrue(os.path.exists('inputpyhooks/python_pre.txt'))
        self.assertTrue(os.path.exists('inputpyhooks/python_post.txt'))

    def test_run_shell_hooks(self):
        generate.generate_files(
            context={
                'cookiecutter' : {'shellhooks': 'shellhooks'}
            },
            repo_dir='tests/test-shellhooks/',
            output_dir='tests/test-shellhooks/'
        )
        self.assertTrue(os.path.exists('tests/test-shellhooks/inputshellhooks/shell_pre.txt'))
        self.assertTrue(os.path.exists('tests/test-shellhooks/inputshellhooks/shell_post.txt'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_hooks
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_hooks
------------

Tests for `cookiecutter.hooks` module.
"""

import sys
import os
import unittest

from cookiecutter import hooks, utils


class TestFindHooks(unittest.TestCase):

    def test_find_hooks(self):
        '''Getting the list of all defined hooks'''
        repo_path = 'tests/test-hooks/'
        with utils.work_in(repo_path):
            self.assertEqual({
                'pre_gen_project': os.path.abspath('hooks/pre_gen_project.py'),
                'post_gen_project': os.path.abspath('hooks/post_gen_project.sh'),
            }, hooks.find_hooks())

    def test_no_hooks(self):
        '''find_hooks should return an empty dict if no hooks folder could be found. '''
        with utils.work_in('tests/fake-repo'):
            self.assertEqual({}, hooks.find_hooks())


class TestExternalHooks(unittest.TestCase):

    repo_path  = os.path.abspath('tests/test-hooks/')
    hooks_path = os.path.abspath('tests/test-hooks/hooks')

    def tearDown(self):
        if os.path.exists('python_pre.txt'):
            os.remove('python_pre.txt')
        if os.path.exists('shell_post.txt'):
            os.remove('shell_post.txt')
        if os.path.exists('tests/shell_post.txt'):
            os.remove('tests/shell_post.txt')
        if os.path.exists('tests/test-hooks/input{{hooks}}/python_pre.txt'):
            os.remove('tests/test-hooks/input{{hooks}}/python_pre.txt')
        if os.path.exists('tests/test-hooks/input{{hooks}}/shell_post.txt'):
            os.remove('tests/test-hooks/input{{hooks}}/shell_post.txt')

    def test_run_hook(self):
        '''execute a hook script, independently of project generation'''
        hooks._run_hook(os.path.join(self.hooks_path, 'post_gen_project.sh'))
        self.assertTrue(os.path.isfile('shell_post.txt'))

    def test_run_hook_cwd(self):
        '''Change directory before running hook'''
        hooks._run_hook(os.path.join(self.hooks_path, 'post_gen_project.sh'), 
                        'tests')
        self.assertTrue(os.path.isfile('tests/shell_post.txt'))
        self.assertFalse('tests' in os.getcwd())
        
    def test_public_run_hook(self):
        '''Execute hook from specified template in specified output directory'''
        tests_dir = os.path.join(self.repo_path, 'input{{hooks}}')
        with utils.work_in(self.repo_path):
            hooks.run_hook('pre_gen_project', tests_dir)
            self.assertTrue(os.path.isfile(os.path.join(tests_dir, 'python_pre.txt')))

            hooks.run_hook('post_gen_project', tests_dir)
            self.assertTrue(os.path.isfile(os.path.join(tests_dir, 'shell_post.txt')))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_main
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_main
---------

Tests for `cookiecutter.main` module.
"""

import logging
import os
import shutil
import sys

from cookiecutter import config, main
from tests import CookiecutterCleanSystemTestCase

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import patch
    input_str = 'builtins.input'
else:
    import __builtin__
    from mock import patch
    input_str = '__builtin__.raw_input'
    from cStringIO import StringIO

try:
    no_network = os.environ[u'DISABLE_NETWORK_TESTS']
except KeyError:
    no_network = False


# Log debug and above to console
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)


class TestCookiecutterLocalNoInput(CookiecutterCleanSystemTestCase):

    def test_cookiecutter(self):
        main.cookiecutter('tests/fake-repo-pre/', no_input=True)
        self.assertTrue(os.path.isdir('tests/fake-repo-pre/{{cookiecutter.repo_name}}'))
        self.assertFalse(os.path.isdir('tests/fake-repo-pre/fake-project'))
        self.assertTrue(os.path.isdir('fake-project'))
        self.assertTrue(os.path.isfile('fake-project/README.rst'))
        self.assertFalse(os.path.exists('fake-project/json/'))

    def test_cookiecutter_no_slash(self):
        main.cookiecutter('tests/fake-repo-pre', no_input=True)
        self.assertTrue(os.path.isdir('tests/fake-repo-pre/{{cookiecutter.repo_name}}'))
        self.assertFalse(os.path.isdir('tests/fake-repo-pre/fake-project'))
        self.assertTrue(os.path.isdir('fake-project'))
        self.assertTrue(os.path.isfile('fake-project/README.rst'))
        self.assertFalse(os.path.exists('fake-project/json/'))

    def tearDown(self):
        if os.path.isdir('fake-project'):
            shutil.rmtree('fake-project')


class TestCookiecutterLocalWithInput(CookiecutterCleanSystemTestCase):

    @patch(input_str, lambda x: '\n')
    def test_cookiecutter_local_with_input(self):
        if not PY3:
            sys.stdin = StringIO("\n\n\n\n\n\n\n\n\n\n\n\n")

        main.cookiecutter('tests/fake-repo-pre/', no_input=False)
        self.assertTrue(os.path.isdir('tests/fake-repo-pre/{{cookiecutter.repo_name}}'))
        self.assertFalse(os.path.isdir('tests/fake-repo-pre/fake-project'))
        self.assertTrue(os.path.isdir('fake-project'))
        self.assertTrue(os.path.isfile('fake-project/README.rst'))
        self.assertFalse(os.path.exists('fake-project/json/'))

    def tearDown(self):
        if os.path.isdir('fake-project'):
            shutil.rmtree('fake-project')


class TestArgParsing(unittest.TestCase):

    def test_parse_cookiecutter_args(self):
        args = main.parse_cookiecutter_args(['project/'])
        self.assertEqual(args.input_dir, 'project/')
        self.assertEqual(args.checkout, None)

    def test_parse_cookiecutter_args_with_branch(self):
        args = main.parse_cookiecutter_args(['project/', '--checkout', 'develop'])
        self.assertEqual(args.input_dir, 'project/')
        self.assertEqual(args.checkout, 'develop')


@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub/Bitbucket.')
class TestCookiecutterRepoArg(CookiecutterCleanSystemTestCase):

    def tearDown(self):
        if os.path.isdir('cookiecutter-pypackage'):
            shutil.rmtree('cookiecutter-pypackage')
        if os.path.isdir('boilerplate'):
            shutil.rmtree('boilerplate')
        if os.path.isdir('cookiecutter-trytonmodule'):
            shutil.rmtree('cookiecutter-trytonmodule')
        if os.path.isdir('module_name'):
            shutil.rmtree('module_name')
        super(TestCookiecutterRepoArg, self).tearDown()

    # HACK: The *args is because:
    # 1. If the lambda has 1 arg named x, I sometimes get this error:
    #    TypeError: <lambda>() missing 1 required positional argument: 'x'
    # 2. If lambda has no args, I unpredictably get this error:
    #    TypeError: <lambda>() takes 0 positional arguments but 1 was given
    # *args is the best of both worlds.
    # But I am not sure why I started getting these errors for no reason.
    # Any help would be appreciated. -- @audreyr
    @patch(input_str, lambda *args: '')
    def test_cookiecutter_git(self):
        if not PY3:
            # Simulate pressing return 10x.
            # HACK: There are only 9 prompts in cookiecutter-pypackage's
            # cookiecutter.json (http://git.io/b-1MVA) but 10 \n chars here.
            # There was an "EOFError: EOF when reading a line" test fail here
            # out of the blue, which an extra \n fixed. 
            # Not sure why. There shouldn't be an extra prompt to delete 
            # the repo, since CookiecutterCleanSystemTestCase ensured that it
            # wasn't present.
            # It's possibly an edge case in CookiecutterCleanSystemTestCase.
            # Improvements to this would be appreciated. -- @audreyr
            sys.stdin = StringIO('\n\n\n\n\n\n\n\n\n\n')
        main.cookiecutter('https://github.com/audreyr/cookiecutter-pypackage.git')
        logging.debug('Current dir is {0}'.format(os.getcwd()))
        clone_dir = os.path.join(os.path.expanduser('~/.cookiecutters'), 'cookiecutter-pypackage')
        self.assertTrue(os.path.exists(clone_dir))
        self.assertTrue(os.path.isdir('boilerplate'))
        self.assertTrue(os.path.isfile('boilerplate/README.rst'))
        self.assertTrue(os.path.exists('boilerplate/setup.py'))

    @patch(input_str, lambda x: '')
    def test_cookiecutter_mercurial(self):
        if not PY3:
            sys.stdin = StringIO('\n\n\n\n\n\n\n\n\n')
        main.cookiecutter('https://bitbucket.org/pokoli/cookiecutter-trytonmodule')
        logging.debug('Current dir is {0}'.format(os.getcwd()))
        clone_dir = os.path.join(os.path.expanduser('~/.cookiecutters'), 'cookiecutter-trytonmodule')
        self.assertTrue(os.path.exists(clone_dir))
        self.assertTrue(os.path.isdir('module_name'))
        self.assertTrue(os.path.isfile('module_name/README'))
        self.assertTrue(os.path.exists('module_name/setup.py'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_prompt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_prompt
--------------

Tests for `cookiecutter.prompt` module.
"""

import sys
import unittest

from cookiecutter import prompt

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import patch
    input_str = 'builtins.input'
else:
    import __builtin__
    from mock import patch
    input_str = '__builtin__.raw_input'
    from cStringIO import StringIO

if sys.version_info[:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestPrompt(unittest.TestCase):

    @patch(input_str, lambda x: 'Audrey Roy')
    def test_prompt_for_config_simple(self):
        context = {"cookiecutter": {"full_name": "Your Name"}}

        if not PY3:
            sys.stdin = StringIO("Audrey Roy")

        cookiecutter_dict = prompt.prompt_for_config(context)
        self.assertEqual(cookiecutter_dict, {"full_name": "Audrey Roy"})

    @patch(input_str, lambda x: 'Pizzä ïs Gööd')
    def test_prompt_for_config_unicode(self):
        context = {"cookiecutter": {"full_name": "Your Name"}}

        if not PY3:
            sys.stdin = StringIO("Pizzä ïs Gööd")

        cookiecutter_dict = prompt.prompt_for_config(context)

        if PY3:
            self.assertEqual(cookiecutter_dict, {"full_name": "Pizzä ïs Gööd"})
        else:
            self.assertEqual(cookiecutter_dict, {"full_name": u"Pizzä ïs Gööd"})

    @patch(input_str, lambda x: 'Pizzä ïs Gööd')
    def test_unicode_prompt_for_config_unicode(self):
        context = {"cookiecutter": {"full_name": u"Řekni či napiš své jméno"}}

        if not PY3:
            sys.stdin = StringIO("Pizzä ïs Gööd")

        cookiecutter_dict = prompt.prompt_for_config(context)

        if PY3:
            self.assertEqual(cookiecutter_dict, {"full_name": "Pizzä ïs Gööd"})
        else:
            self.assertEqual(cookiecutter_dict, {"full_name": u"Pizzä ïs Gööd"})

    @patch(input_str, lambda x: '\n')
    def test_unicode_prompt_for_default_config_unicode(self):
        context = {"cookiecutter": {"full_name": u"Řekni či napiš své jméno"}}

        if not PY3:
            sys.stdin = StringIO("\n")

        cookiecutter_dict = prompt.prompt_for_config(context)

        if PY3:
            self.assertEqual(cookiecutter_dict, {"full_name": "Řekni či napiš své jméno"})
        else:
            self.assertEqual(cookiecutter_dict, {"full_name": u"Řekni či napiš své jméno"})


class TestQueryAnswers(unittest.TestCase):

    @patch(input_str, lambda: 'y')
    def test_query_y(self):
        if not PY3:
            sys.stdin = StringIO('y')
        answer = prompt.query_yes_no("Blah?")
        self.assertTrue(answer)

    @patch(input_str, lambda: 'ye')
    def test_query_ye(self):
        if not PY3:
            sys.stdin = StringIO('ye')
        answer = prompt.query_yes_no("Blah?")
        self.assertTrue(answer)

    @patch(input_str, lambda: 'yes')
    def test_query_yes(self):
        if not PY3:
            sys.stdin = StringIO('yes')
        answer = prompt.query_yes_no("Blah?")
        self.assertTrue(answer)

    @patch(input_str, lambda: 'n')
    def test_query_n(self):
        if not PY3:
            sys.stdin = StringIO('n')
        answer = prompt.query_yes_no("Blah?")
        self.assertFalse(answer)

    @patch(input_str, lambda: 'no')
    def test_query_n(self):
        if not PY3:
            sys.stdin = StringIO('no')
        answer = prompt.query_yes_no("Blah?")
        self.assertFalse(answer)


class TestQueryDefaults(unittest.TestCase):

    @patch(input_str, lambda: 'y')
    def test_query_y_none_default(self):
        if not PY3:
            sys.stdin = StringIO('y')
        answer = prompt.query_yes_no("Blah?", default=None)
        self.assertTrue(answer)

    @patch(input_str, lambda: 'n')
    def test_query_n_none_default(self):
        if not PY3:
            sys.stdin = StringIO('n')
        answer = prompt.query_yes_no("Blah?", default=None)
        self.assertFalse(answer)

    @patch(input_str, lambda: '')
    def test_query_no_default(self):
        if not PY3:
            sys.stdin = StringIO('\n')
        answer = prompt.query_yes_no("Blah?", default='no')
        self.assertFalse(answer)

    @patch(input_str, lambda: 'junk')
    def test_query_bad_default(self):
        if not PY3:
            sys.stdin = StringIO('junk')
        self.assertRaises(ValueError, prompt.query_yes_no, "Blah?", default='yn')

########NEW FILE########
__FILENAME__ = test_utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_utils
------------

Tests for `cookiecutter.utils` module.
"""

import os
import shutil
import sys
import unittest

from cookiecutter import utils


class TestUtils(unittest.TestCase):

    def test_make_sure_path_exists(self):
        self.assertTrue(utils.make_sure_path_exists('/usr/'))
        self.assertTrue(utils.make_sure_path_exists('tests/blah'))
        self.assertTrue(utils.make_sure_path_exists('tests/trailingslash/'))
        self.assertFalse(
            utils.make_sure_path_exists(
                '/this-dir-does-not-exist-and-cant-be-created/'.replace("/", os.sep)
            )
        )
        shutil.rmtree('tests/blah/')
        shutil.rmtree('tests/trailingslash/')

    def test_unicode_open(self):
        """ Test unicode_open(filename, *args, **kwargs). """

        unicode_text = u"""Polish: Ą Ł Ż
Chinese: 倀 倁 倂 倃 倄 倅 倆 倇 倈
Musical Notes: ♬ ♫ ♯"""

        with utils.unicode_open('tests/files/unicode.txt') as f:
            opened_text = f.read()
            if sys.platform.startswith('win'):
                unicode_text = os.linesep.join([s for s in unicode_text.splitlines() if not s.isspace()])
            self.assertEqual(unicode_text, opened_text)

    def test_workin(self):
        cwd = os.getcwd()
        ch_to = 'tests/files'

        class TestException(Exception):
            pass

        def test_work_in():
            with utils.work_in(ch_to):
                test_dir = os.path.join(cwd, ch_to).replace("/", os.sep)
                self.assertEqual(test_dir, os.getcwd())
                raise TestException()

        # Make sure we return to the correct folder
        self.assertEqual(cwd, os.getcwd())

        # Make sure that exceptions are still bubbled up
        self.assertRaises(TestException, test_work_in)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_vcs
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_vcs
------------

Tests for `cookiecutter.vcs` module.
"""

import locale
import logging
import os
import shutil
import subprocess
import sys
import unittest

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import patch
    input_str = 'builtins.input'
else:
    import __builtin__
    from mock import patch
    input_str = '__builtin__.raw_input'
    from cStringIO import StringIO

if sys.version_info[:3] < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from cookiecutter import utils, vcs

try:
    no_network = os.environ[u'DISABLE_NETWORK_TESTS']
except KeyError:
    no_network = False


# Log debug and above to console
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
encoding = locale.getdefaultlocale()[1]


class TestIdentifyRepo(unittest.TestCase):

    def test_identify_git_github(self):
        repo_url = "https://github.com/audreyr/cookiecutter-pypackage.git"
        self.assertEqual(vcs.identify_repo(repo_url), "git")

    def test_identify_git_github_no_extension(self):
        repo_url = "https://github.com/audreyr/cookiecutter-pypackage"
        self.assertEqual(vcs.identify_repo(repo_url), "git")

    def test_identify_git_gitorious(self):
        repo_url = "git@gitorious.org:cookiecutter-gitorious/cookiecutter-gitorious.git"
        self.assertEqual(vcs.identify_repo(repo_url), "git")

    def test_identify_hg_mercurial(self):
        repo_url = "https://audreyr@bitbucket.org/audreyr/cookiecutter-bitbucket"
        self.assertEqual(vcs.identify_repo(repo_url), "hg")


@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub/Bitbucket.')
class TestVCS(unittest.TestCase):

    def test_git_clone(self):
        repo_dir = vcs.clone(
            'https://github.com/audreyr/cookiecutter-pypackage.git'
        )
        self.assertEqual(repo_dir, 'cookiecutter-pypackage')
        self.assertTrue(os.path.isfile('cookiecutter-pypackage/README.rst'))
        if os.path.isdir('cookiecutter-pypackage'):
            shutil.rmtree('cookiecutter-pypackage')

    def test_git_clone_checkout(self):
        repo_dir = vcs.clone(
            'https://github.com/audreyr/cookiecutter-pypackage.git',
            'console-script'
        )
        git_dir = 'cookiecutter-pypackage'
        self.assertEqual(repo_dir, git_dir)
        self.assertTrue(os.path.isfile(os.path.join('cookiecutter-pypackage', 'README.rst')))

        proc = subprocess.Popen(
            ['git', 'symbolic-ref', 'HEAD'],
            cwd=git_dir,
            stdout=subprocess.PIPE
        )
        symbolic_ref = proc.communicate()[0]
        branch = symbolic_ref.decode(encoding).strip().split('/')[-1]
        self.assertEqual('console-script', branch)

        if os.path.isdir(git_dir):
            shutil.rmtree(git_dir)

    def test_git_clone_custom_dir(self):
        os.makedirs("tests/custom_dir1/custom_dir2/")
        repo_dir = vcs.clone(
            repo_url='https://github.com/audreyr/cookiecutter-pypackage.git',
            checkout=None,
            clone_to_dir="tests/custom_dir1/custom_dir2/"
        )
        with utils.work_in("tests/custom_dir1/custom_dir2/"):
            test_dir = 'tests/custom_dir1/custom_dir2/cookiecutter-pypackage'.replace("/", os.sep)
            self.assertEqual(repo_dir, test_dir)
            self.assertTrue(os.path.isfile('cookiecutter-pypackage/README.rst'))
            if os.path.isdir('cookiecutter-pypackage'):
                shutil.rmtree('cookiecutter-pypackage')
        if os.path.isdir('tests/custom_dir1'):
            shutil.rmtree('tests/custom_dir1')

    def test_hg_clone(self):
        repo_dir = vcs.clone(
            'https://bitbucket.org/pokoli/cookiecutter-trytonmodule'
        )
        self.assertEqual(repo_dir, 'cookiecutter-trytonmodule')
        self.assertTrue(os.path.isfile('cookiecutter-trytonmodule/README.rst'))
        if os.path.isdir('cookiecutter-trytonmodule'):
            shutil.rmtree('cookiecutter-trytonmodule')


@unittest.skipIf(condition=no_network, reason='Needs a network connection to GitHub/Bitbucket.')
class TestVCSPrompt(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('cookiecutter-pypackage'):
            shutil.rmtree('cookiecutter-pypackage')
        os.mkdir('cookiecutter-pypackage/')
        if os.path.isdir('cookiecutter-trytonmodule'):
            shutil.rmtree('cookiecutter-trytonmodule')
        os.mkdir('cookiecutter-trytonmodule/')

    @patch(input_str, lambda: 'y')
    def test_git_clone_overwrite(self):
        if not PY3:
            sys.stdin = StringIO('y\n\n')
        repo_dir = vcs.clone(
            'https://github.com/audreyr/cookiecutter-pypackage.git'
        )
        self.assertEqual(repo_dir, 'cookiecutter-pypackage')
        self.assertTrue(os.path.isfile('cookiecutter-pypackage/README.rst'))

    @patch(input_str, lambda: 'n')
    def test_git_clone_cancel(self):
        if not PY3:
            sys.stdin = StringIO('n\n\n')
        self.assertRaises(
            SystemExit,
            vcs.clone,
            'https://github.com/audreyr/cookiecutter-pypackage.git'
        )

    @patch(input_str, lambda: 'y')
    def test_hg_clone_overwrite(self):
        if not PY3:
            sys.stdin = StringIO('y\n\n')
        repo_dir = vcs.clone(
            'https://bitbucket.org/pokoli/cookiecutter-trytonmodule'
        )
        self.assertEqual(repo_dir, 'cookiecutter-trytonmodule')
        self.assertTrue(os.path.isfile('cookiecutter-trytonmodule/README.rst'))

    @patch(input_str, lambda: 'n')
    def test_hg_clone_cancel(self):
        if not PY3:
            sys.stdin = StringIO('n\n\n')
        self.assertRaises(
            SystemExit,
            vcs.clone,
            'https://bitbucket.org/pokoli/cookiecutter-trytonmodule'
        )

    def tearDown(self):
        if os.path.isdir('cookiecutter-pypackage'):
            shutil.rmtree('cookiecutter-pypackage')
        if os.path.isdir('cookiecutter-trytonmodule'):
            shutil.rmtree('cookiecutter-trytonmodule')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
