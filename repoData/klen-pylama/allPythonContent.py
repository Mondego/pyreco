__FILENAME__ = conf
# -*- coding: utf-8 -*-
import os
import sys
import datetime

from pylama import __version__ as release

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
source_suffix = '.rst'
master_doc = 'index'
project = 'Pylama'
copyright = '%s, Kirill Klenov' % datetime.datetime.now().year
version = '.'.join(release.split('.')[:2])
exclude_patterns = ['_build']
html_use_modindex = False
html_show_sphinx = False
htmlhelp_basename = 'Pylamadoc'
latex_documents = [
    ('index', 'Pylama.tex', 'Pylama Documentation', 'Kirill Klenov', 'manual'),
]
latex_use_modindex = False
latex_use_parts = True
man_pages = [
    ('index', 'Pylama', 'Pylama Documentation', ['Kirill Klenov'], 1)
]
pygments_style = 'tango'
html_theme = 'default'
html_theme_options = {}

# lint_ignore=W0622

########NEW FILE########
__FILENAME__ = dummy
#!/usr/bin/env python
# coding: utf-8
# (c) 2005 Divmod, Inc.  See LICENSE file for details


class Message(object):
    message = ''
    message_args = ()
    def __init__(self, filename, loc, use_column=True):
        self.filename = filename
        self.lineno = loc.lineno
        self.col = getattr(loc, 'col_offset', None) if use_column else None

    def __str__(self):
        return '%s:%s: %s' % (self.filename, self.lineno, self.message % self.message_args)


class UnusedImport(Message):
    message = 'W402 %r imported but unused'

    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class RedefinedWhileUnused(Message):
    message = 'W801 redefinition of unused %r from line %r'

    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)


class ImportShadowedByLoopVar(Message):
    message = 'W403 import %r from line %r shadowed by loop variable'

    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)


class ImportStarUsed(Message):
    message = "W404 'from %s import *' used; unable to detect undefined names"

    def __init__(self, filename, lineno, modname):
        Message.__init__(self, filename, lineno)
        self.message_args = (modname,)


class UndefinedName(Message):
    message = 'W802 undefined name %r'

    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class UndefinedExport(Message):
    message = 'W803 undefined name %r in __all__'

    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class UndefinedLocal(Message):
    message = "W804 local variable %r (defined in enclosing scope on line " \
            "%r) referenced before assignment"

    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)


class DuplicateArgument(Message):
    message = 'W805 duplicate argument %r in function definition'

    def __init__(self, filename, lineno, name):
        Message.__init__(self, filename, lineno)
        self.message_args = (name,)


class RedefinedFunction(Message):
    message = 'W806 redefinition of function %r from line %r'

    def __init__(self, filename, lineno, name, orig_lineno):
        Message.__init__(self, filename, lineno)
        self.message_args = (name, orig_lineno)


class LateFutureImport(Message):
    message = 'W405 future import(s) %r after other statements'

    def __init__(self, filename, lineno, names):
        Message.__init__(self, filename, lineno)
        self.message_args = (names,)


class UnusedVariable(Message):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """

    message = 'W806 local variable %r is assigned to but never used'

    def __init__(self, filename, lineno, names):
        Message.__init__(self, filename, lineno)
        self.message_args = (names,)
        error = 1 # noQa and some comments

########NEW FILE########
__FILENAME__ = config
""" Parse arguments from command line and configuration files. """
import fnmatch
import sys
from os import getcwd, path
from re import compile as re

import logging
from argparse import ArgumentParser

from . import __version__
from .libs.inirama import Namespace
from .lint.extensions import LINTERS


# Setup a logger
LOGGER = logging.getLogger('pylama')
LOGGER.propagate = False
STREAM = logging.StreamHandler(sys.stdout)
LOGGER.addHandler(STREAM)

#: A default checkers
DEFAULT_LINTERS = 'pep8', 'pyflakes', 'mccabe'

CURDIR = getcwd()
DEFAULT_INI_PATH = path.join(CURDIR, 'pylama.ini')


class _Default(object):

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return str(self.value)

    __repr__ = lambda s: "<_Default [%s]>" % s.value


def split_csp_str(s):
    """ Split commaseparated string.

    :returns: list of splitted values

    """
    if isinstance(s, (list, tuple)):
        return s
    return list(set(i for i in s.strip().split(',') if i))


def parse_linters(linters):
    """ Initialize choosen linters.

    :returns: list of inited linters

    """
    result = list()
    for name in split_csp_str(linters):
        linter = LINTERS.get(name)
        if linter:
            result.append((name, linter))
        else:
            logging.warn("Linter `%s` not found.", name)
    return result


PARSER = ArgumentParser(description="Code audit tool for python.")
PARSER.add_argument(
    "path", nargs='?', default=_Default(CURDIR),
    help="Path on file or directory.")

PARSER.add_argument(
    "--verbose", "-v", action='store_true', help="Verbose mode.")

PARSER.add_argument('--version', action='version',
                    version='%(prog)s ' + __version__)

PARSER.add_argument(
    "--format", "-f", default=_Default('pep8'), choices=['pep8', 'pylint'],
    help="Error format.")

PARSER.add_argument(
    "--select", "-s", default=_Default(''), type=split_csp_str,
    help="Select errors and warnings. (comma-separated)")


PARSER.add_argument(
    "--linters", "-l", default=_Default(','.join(DEFAULT_LINTERS)),
    type=parse_linters, help=(
        "Select linters. (comma-separated). Choices are %s."
        % ','.join(s for s in LINTERS.keys())
    ))

PARSER.add_argument(
    "--ignore", "-i", default=_Default(''), type=split_csp_str,
    help="Ignore errors and warnings. (comma-separated)")

PARSER.add_argument(
    "--skip", default=_Default(''),
    type=lambda s: [re(fnmatch.translate(p)) for p in s.split(',') if p],
    help="Skip files by masks (comma-separated, Ex. */messages.py)")

PARSER.add_argument("--report", "-r", help="Filename for report.")
PARSER.add_argument(
    "--hook", action="store_true", help="Install Git (Mercurial) hook.")

PARSER.add_argument(
    "--async", action="store_true",
    help="Enable async mode. Usefull for checking a lot of files. "
    "Dont supported with pylint.")

PARSER.add_argument(
    "--options", "-o", default=_Default(DEFAULT_INI_PATH),
    help="Select configuration file. By default is '<CURDIR>/pylama.ini'")


ACTIONS = dict((a.dest, a) for a in PARSER._actions)


def parse_options(args=None, config=True, **overrides): # noqa
    """ Parse options from command line and configuration files.

    :return argparse.Namespace:

    """
    if args is None:
        args = []

    # Parse args from command string
    options = PARSER.parse_args(args)
    options.file_params = dict()
    options.linter_params = dict()

    # Override options
    for k, v in overrides.items():
        passed_value = getattr(options, k, _Default())
        if isinstance(passed_value, _Default):
            setattr(options, k, _Default(v))

    # Compile options from ini
    if config:
        cfg = get_config(str(options.options))
        for k, v in cfg.default.items():
            LOGGER.info('Find option %s (%s)', k, v)
            passed_value = getattr(options, k, _Default())
            if isinstance(passed_value, _Default):
                setattr(options, k, _Default(v))

        # Parse file related options
        for k, s in cfg.sections.items():
            if k == cfg.default_section:
                continue
            if k in LINTERS:
                options.linter_params[k] = dict(s)
                continue
            mask = re(fnmatch.translate(k))
            options.file_params[mask] = dict(s)
            options.file_params[mask]['lint'] = int(
                options.file_params[mask].get('lint', 1)
            )

    # Postprocess options
    opts = dict(options.__dict__.items())
    for name, value in opts.items():
        if isinstance(value, _Default):
            setattr(options, name, process_value(name, value.value))

    return options


def process_value(name, value):
    """ Compile option value. """
    action = ACTIONS.get(name)
    if not action:
        return value

    if callable(action.type):
        return action.type(value)

    if action.const:
        return bool(int(value))

    return value


def get_config(ini_path=DEFAULT_INI_PATH):
    """ Load configuration from INI.

    :return Namespace:

    """
    config = Namespace()
    config.default_section = 'main'
    config.read(ini_path)

    return config


def setup_logger(options):
    """ Setup logger with options. """
    LOGGER.setLevel(logging.INFO if options.verbose else logging.WARN)
    if options.report:
        LOGGER.removeHandler(STREAM)
        LOGGER.addHandler(logging.FileHandler(options.report, mode='w'))
    LOGGER.info('Try to read configuration from: ' + options.options)

########NEW FILE########
__FILENAME__ = core
""" Pylama's core functionality.

Prepare params, check a modeline and run the checkers.

"""
import re

import logging

from .config import process_value, LOGGER
from .lint.extensions import LINTERS


#: The skip pattern
SKIP_PATTERN = re.compile(r'# *noqa\b', re.I).search

# Parse a modelines
MODELINE_RE = re.compile(
    r'^\s*#\s+(?:pylama:)\s*((?:[\w_]*=[^:\n\s]+:?)+)',
    re.I | re.M)


def run(path, code=None, options=None):
    """ Run a code checkers with given params.

    :return errors: list of dictionaries with error's information

    """
    errors = []
    params = dict(ignore=options.ignore, select=options.select)
    fileconfig = dict()
    for mask in options.file_params:
        if mask.match(path):
            fileconfig.update(options.file_params[mask])

    try:
        with CodeContext(code, path) as ctx:
            code = ctx.code
            params = prepare_params(parse_modeline(code), fileconfig, options)

            if params.get('skip'):
                return errors

            for item in options.linters:

                if not isinstance(item, tuple):
                    item = (item, LINTERS.get(item))

                name, linter = item

                if not linter or not linter.allow(path):
                    continue

                LOGGER.info("Run %s", name)
                meta = options.linter_params.get(name, dict())
                result = linter.run(path, code=code, **meta)
                for e in result:
                    e['linter'] = name
                    e['col'] = e.get('col') or 0
                    e['lnum'] = e.get('lnum') or 0
                    e['type'] = e.get('type') or 'E'
                    e['text'] = "%s [%s]" % (
                        e.get('text', '').strip().split('\n')[0], name)
                    e['filename'] = path or ''
                    errors.append(e)

    except IOError as e:
        LOGGER.debug("IOError %s", e)
        errors.append(dict(
            lnum=0, type='E', col=0, text=str(e), filename=path or ''))

    except SyntaxError as e:
        LOGGER.debug("SyntaxError %s", e)
        errors.append(dict(
            lnum=e.lineno or 0, type='E', col=e.offset or 0,
            text=e.args[0] + ' [%s]' % name, filename=path or ''
        ))

    except Exception as e:
        import traceback
        LOGGER.info(traceback.format_exc())

    errors = [er for er in errors if filter_errors(er, **params)]

    if code and errors:
        errors = filter_skiplines(code, errors)

    return sorted(errors, key=lambda x: x['lnum'])


def parse_modeline(code):
    """ Parse params from file's modeline.

    :return dict: Linter params.

    """
    seek = MODELINE_RE.search(code)
    if seek:
        return dict(v.split('=') for v in seek.group(1).split(':'))

    return dict()


def prepare_params(modeline, fileconfig, options):
    """ Prepare and merge a params from modelines and configs.

    :return dict:

    """
    params = dict(ignore=options.ignore, select=options.select, skip=False)

    for config in filter(None, [modeline, fileconfig]):
        for key in ('ignore', 'select'):
            params[key] += process_value(key, config.get(key, []))
        params['skip'] = bool(int(config.get('skip', False)))

    params['ignore'] = set(params['ignore'])
    params['select'] = set(params['select'])

    return params


def filter_errors(e, select=None, ignore=None, **params):
    """ Filter a erros by select and ignore options.

    :return bool:

    """
    if select:
        for s in select:
            if e['text'].startswith(s):
                return True

    if ignore:
        for s in ignore:
            if e['text'].startswith(s):
                return False

    return True


def filter_skiplines(code, errors):
    """ Filter lines by `noqa`.

    :return list: A filtered errors

    """
    if not errors:
        return errors

    enums = set(er['lnum'] for er in errors)
    removed = set([
        num for num, l in enumerate(code.split('\n'), 1)
        if num in enums and SKIP_PATTERN(l)
    ])

    if removed:
        errors = [er for er in errors if not er['lnum'] in removed]

    return errors


class CodeContext(object):

    """ Read file if code is None. """

    def __init__(self, code, path):
        """ Init context. """
        self.code = code
        self.path = path
        self._file = None

    def __enter__(self):
        """ Open file and read a code. """
        if self.code is None:
            self._file = open(self.path, 'rU')
            self.code = self._file.read()
        return self

    def __exit__(self, t, value, traceback):
        """ Close opened file. """
        if self._file is not None:
            self._file.close()

        if t and LOGGER.level == logging.DEBUG:
            LOGGER.debug(traceback)

########NEW FILE########
__FILENAME__ = hook
""" SCM hooks. Integration with git and mercurial. """
from __future__ import absolute_import

import sys
from os import path as op, chmod
from subprocess import Popen, PIPE

from .main import LOGGER
from .config import parse_options, setup_logger


try:
    from configparser import ConfigParser  # noqa
except ImportError:   # Python 2
    from ConfigParser import ConfigParser


def run(command):
    """ Run a shell command.

    :return str: Stdout

    """
    p = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p.communicate()
    return (p.returncode, [line.strip() for line in stdout.splitlines()],
            [line.strip() for line in stderr.splitlines()])


def git_hook():
    """ Run pylama after git commit. """
    from .main import check_files

    _, files_modified, _ = run("git diff-index --cached --name-only HEAD")

    options = parse_options()
    setup_logger(options)
    check_files([f for f in map(str, files_modified)], options)


def hg_hook(ui, repo, node=None, **kwargs):
    """ Run pylama after mercurial commit. """
    from .main import check_files
    seen = set()
    paths = []
    if len(repo):
        for rev in range(repo[node], len(repo)):
            for file_ in repo[rev].files():
                file_ = op.join(repo.root, file_)
                if file_ in seen or not op.exists(file_):
                    continue
                seen.add(file_)
                paths.append(file_)

    options = parse_options()
    setup_logger(options)
    check_files(paths, options)


def install_git(path):
    """ Install hook in Git repository. """
    hook = op.join(path, 'pre-commit')
    with open(hook, 'w') as fd:
        fd.write("""#!/usr/bin/env python
import sys
from pylama.hook import git_hook

if __name__ == '__main__':
    sys.exit(git_hook())
""")
    chmod(hook, 484)


def install_hg(path):
    """ Install hook in Mercurial repository. """
    hook = op.join(path, 'hgrc')
    if not op.isfile(hook):
        open(hook, 'w+').close()

    c = ConfigParser()
    c.readfp(open(path, 'r'))
    if not c.has_section('hooks'):
        c.add_section('hooks')

    if not c.has_option('hooks', 'commit'):
        c.set('hooks', 'commit', 'python:pylama.hooks.hg_hook')

    if not c.has_option('hooks', 'qrefresh'):
        c.set('hooks', 'qrefresh', 'python:pylama.hooks.hg_hook')

    c.write(open(path, 'w+'))


def install_hook(path):
    """ Auto definition of SCM and hook installation. """
    git = op.join(path, '.git', 'hooks')
    hg = op.join(path, '.hg')
    if op.exists(git):
        install_git(git)
        LOGGER.warn('Git hook has been installed.')

    elif op.exists(hg):
        install_hg(git)
        LOGGER.warn('Mercurial hook has been installed.')

    else:
        LOGGER.error('VCS has not found. Check your path.')
        sys.exit(1)

# lint_ignore=F0401,E1103

########NEW FILE########
__FILENAME__ = importlib
"""Backport of importlib.import_module from 3.x."""
# While not critical (and in no way guaranteed!), it would be nice to keep this
# code compatible with Python 2.3.
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]

########NEW FILE########
__FILENAME__ = inirama
"""
    Inirama is a python module that parses INI files.

    .. _badges:
    .. include:: ../README.rst
        :start-after: .. _badges:
        :end-before: .. _contents:

    .. _description:
    .. include:: ../README.rst
        :start-after: .. _description:
        :end-before: .. _badges:

    :copyright: 2013 by Kirill Klenov.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import unicode_literals, print_function

import io
import re
import logging
from collections import MutableMapping
try:
    from collections import OrderedDict
except ImportError:
    from UserDict import DictMixin

    class OrderedDict(dict, DictMixin):

        null = object()

        def __init__(self, *args, **kwargs):
            self.clear()
            self.update(*args, **kwargs)

        def clear(self):
            self.__map = dict()
            self.__order = list()
            dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            self.__map[key] = len(self.__order)
            self.__order.append(key)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.__map.pop(key)
        self.__order = self.null

    def __iter__(self):
        for key in self.__order:
            if key is not self.null:
                yield key

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems


__version__ = "0.5.1"
__project__ = "Inirama"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "BSD"


NS_LOGGER = logging.getLogger('inirama')


class Scanner(object):

    """ Split a code string on tokens. """

    def __init__(self, source, ignore=None, patterns=None):
        """ Init Scanner instance.

        :param patterns: List of token patterns [(token, regexp)]
        :param ignore: List of ignored tokens

        """
        self.reset(source)
        if patterns:
            self.patterns = []
            for k, r in patterns:
                self.patterns.append((k, re.compile(r)))

        if ignore:
            self.ignore = ignore

    def reset(self, source):
        """ Reset scanner's state.

        :param source: Source for parsing

        """
        self.tokens = []
        self.source = source
        self.pos = 0

    def scan(self):
        """ Scan source and grab tokens. """

        self.pre_scan()

        token = None
        end = len(self.source)

        while self.pos < end:

            best_pat = None
            best_pat_len = 0

            # Check patterns
            for p, regexp in self.patterns:
                m = regexp.match(self.source, self.pos)
                if m:
                    best_pat = p
                    best_pat_len = len(m.group(0))
                    break

            if best_pat is None:
                raise SyntaxError(
                    "SyntaxError[@char {0}: {1}]".format(
                        self.pos, "Bad token."))

            # Ignore patterns
            if best_pat in self.ignore:
                self.pos += best_pat_len
                continue

            # Create token
            token = (
                best_pat,
                self.source[self.pos:self.pos + best_pat_len],
                self.pos,
                self.pos + best_pat_len,
            )

            self.pos = token[-1]
            self.tokens.append(token)

    def pre_scan(self):
        """ Prepare source. """
        pass

    def __repr__(self):
        """ Print the last 5 tokens that have been scanned in.

        :return str:

        """
        return '<Scanner: ' + ','.join(
            "{0}({2}:{3})".format(*t) for t in self.tokens[-5:]) + ">"


class INIScanner(Scanner):

    """ Get tokens for INI. """

    patterns = [
        ('SECTION', re.compile(r'\[[^]]+\]')),
        ('IGNORE', re.compile(r'[ \r\t\n]+')),
        ('COMMENT', re.compile(r'[;#].*')),
        ('KEY', re.compile(r'[\w_]+\s*[:=].*'))]

    ignore = ['IGNORE']

    def pre_scan(self):
        """ Prepare string for scaning. """
        escape_re = re.compile(r'\\\n[\t ]+')
        self.source = escape_re.sub('', self.source)


undefined = object()


class Section(MutableMapping):

    """ Representation of INI section. """

    def __init__(self, namespace, *args, **kwargs):
        super(Section, self).__init__(*args, **kwargs)
        self.namespace = namespace
        self.__storage__ = dict()

    def __setitem__(self, name, value):
        value = str(value)
        if value.isdigit():
            value = int(value)

        self.__storage__[name] = value

    def __getitem__(self, name):
        return self.__storage__[name]

    def __delitem__(self, name):
        del self.__storage__[name]

    def __len__(self):
        return len(self.__storage__)

    def __iter__(self):
        return iter(self.__storage__)

    def __repr__(self):
        return "<{0} {1}>".format(self.__class__.__name__, str(dict(self)))

    def iteritems(self):
        """ Impletment iteritems. """
        for key in self.__storage__.keys():
            yield key, self[key]

    items = lambda s: list(s.iteritems())


class InterpolationSection(Section):

    """ INI section with interpolation support. """

    var_re = re.compile('{([^}]+)}')

    def get(self, name, default=None):
        """ Get item by name.

        :return object: value or None if name not exists

        """

        if name in self:
            return self[name]
        return default

    def __interpolate__(self, math):
        try:
            key = math.group(1).strip()
            return self.namespace.default.get(key) or self[key]
        except KeyError:
            return ''

    def __getitem__(self, name):
        value = super(InterpolationSection, self).__getitem__(name)
        sample = undefined
        while sample != value:
            try:
                sample, value = value, self.var_re.sub(
                    self.__interpolate__, value)
            except RuntimeError:
                message = "Interpolation failed: {0}".format(name)
                NS_LOGGER.error(message)
                raise ValueError(message)
        return value


class Namespace(object):

    """ Default class for parsing INI.

    :param **default_items: Default items for default section.

    Usage
    -----

    ::

        from inirama import Namespace

        ns = Namespace()
        ns.read('config.ini')

        print ns['section']['key']

        ns['other']['new'] = 'value'
        ns.write('new_config.ini')

    """

    #: Name of default section (:attr:`~inirama.Namespace.default`)
    default_section = 'DEFAULT'

    #: Dont raise any exception on file reading erorrs
    silent_read = True

    #: Class for generating sections
    section_type = Section

    def __init__(self, **default_items):
        self.sections = OrderedDict()
        for k, v in default_items.items():
            self[self.default_section][k] = v

    @property
    def default(self):
        """ Return default section or empty dict.

        :return :class:`inirama.Section`: section

        """
        return self.sections.get(self.default_section, dict())

    def read(self, *files, **params):
        """ Read and parse INI files.

        :param *files: Files for reading
        :param **params: Params for parsing

        Set `update=False` for prevent values redefinition.

        """
        for f in files:
            try:
                with io.open(f, encoding='utf-8') as ff:
                    NS_LOGGER.info('Read from `{0}`'.format(ff.name))
                    self.parse(ff.read(), **params)
            except (IOError, TypeError, SyntaxError, io.UnsupportedOperation):
                if not self.silent_read:
                    NS_LOGGER.error('Reading error `{0}`'.format(ff.name))
                    raise

    def write(self, f):
        """ Write namespace as INI file.

        :param f: File object or path to file.

        """
        if isinstance(f, str):
            f = io.open(f, 'w', encoding='utf-8')

        if not hasattr(f, 'read'):
            raise AttributeError("Wrong type of file: {0}".format(type(f)))

        NS_LOGGER.info('Write to `{0}`'.format(f.name))
        for section in self.sections.keys():
            f.write('[{0}]\n'.format(section))
            for k, v in self[section].items():
                f.write('{0:15}= {1}\n'.format(k, v))
            f.write('\n')
        f.close()

    def parse(self, source, update=True, **params):
        """ Parse INI source as string.

        :param source: Source of INI
        :param update: Replace alredy defined items

        """
        scanner = INIScanner(source)
        scanner.scan()

        section = self.default_section

        for token in scanner.tokens:
            if token[0] == 'KEY':
                name, value = re.split('[=:]', token[1], 1)
                name, value = name.strip(), value.strip()
                if not update and name in self[section]:
                    continue
                self[section][name] = value

            elif token[0] == 'SECTION':
                section = token[1].strip('[]')

    def __getitem__(self, name):
        """ Look name in self sections.

        :return :class:`inirama.Section`: section

        """
        if name not in self.sections:
            self.sections[name] = self.section_type(self)
        return self.sections[name]

    def __contains__(self, name):
        return name in self.sections

    def __repr__(self):
        return "<Namespace: {0}>".format(self.sections)


class InterpolationNamespace(Namespace):

    """ That implements the interpolation feature.

    ::

        from inirama import InterpolationNamespace

        ns = InterpolationNamespace()
        ns.parse('''
            [main]
            test = value
            foo = bar {test}
            more_deep = wow {foo}
        ''')
        print ns['main']['more_deep']  # wow bar value

    """

    section_type = InterpolationSection

# lint_ignore=W0201,R0924,F0401

########NEW FILE########
__FILENAME__ = extensions
""" Load extensions. """

from os import listdir, path as op


CURDIR = op.dirname(__file__)
LINTERS = dict()
PREFIX = 'pylama_'

try:
    from importlib import import_module
except ImportError:
    from ..libs.importlib import import_module

for p in listdir(CURDIR):
    if p.startswith(PREFIX) and op.isdir(op.join(CURDIR, p)):
        name = p[len(PREFIX):]
        try:
            module = import_module('.lint.%s%s' % (PREFIX, name), 'pylama')
            LINTERS[name] = getattr(module, 'Linter')()
        except ImportError:
            continue

try:
    from pkg_resources import iter_entry_points

    for entry in iter_entry_points('pylama.linter'):
        LINTERS[entry.name] = entry.load()()
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = mccabe
""" Meager code path measurement tool.
    Ned Batchelder
    http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html
    MIT License.
"""
from __future__ import with_statement

import optparse
import sys
from collections import defaultdict
try:
    import ast
    from ast import iter_child_nodes
except ImportError:   # Python 2.5
    from flake8.util import ast, iter_child_nodes

__version__ = '0.2.1'


class ASTVisitor(object):
    """Performs a depth-first walk of the AST."""

    def __init__(self):
        self.node = None
        self._cache = {}

    def default(self, node, *args):
        for child in iter_child_nodes(node):
            self.dispatch(child, *args)

    def dispatch(self, node, *args):
        self.node = node
        klass = node.__class__
        meth = self._cache.get(klass)
        if meth is None:
            className = klass.__name__
            meth = getattr(self.visitor, 'visit' + className, self.default)
            self._cache[klass] = meth
        return meth(node, *args)

    def preorder(self, tree, visitor, *args):
        """Do preorder walk of tree using visitor"""
        self.visitor = visitor
        visitor.visit = self.dispatch
        self.dispatch(tree, *args)  # XXX *args make sense?


class PathNode(object):
    def __init__(self, name, look="circle"):
        self.name = name
        self.look = look

    def to_dot(self):
        print('node [shape=%s,label="%s"] %d;' % (
            self.look, self.name, self.dot_id()))

    def dot_id(self):
        return id(self)


class PathGraph(object):
    def __init__(self, name, entity, lineno):
        self.name = name
        self.entity = entity
        self.lineno = lineno
        self.nodes = defaultdict(list)

    def connect(self, n1, n2):
        self.nodes[n1].append(n2)

    def to_dot(self):
        print('subgraph {')
        for node in self.nodes:
            node.to_dot()
        for node, nexts in self.nodes.items():
            for next in nexts:
                print('%s -- %s;' % (node.dot_id(), next.dot_id()))
        print('}')

    def complexity(self):
        """ Return the McCabe complexity for the graph.
            V-E+2
        """
        num_edges = sum([len(n) for n in self.nodes.values()])
        num_nodes = len(self.nodes)
        return num_edges - num_nodes + 2


class PathGraphingAstVisitor(ASTVisitor):
    """ A visitor for a parsed Abstract Syntax Tree which finds executable
        statements.
    """

    def __init__(self):
        super(PathGraphingAstVisitor, self).__init__()
        self.classname = ""
        self.graphs = {}
        self.reset()

    def reset(self):
        self.graph = None
        self.tail = None

    def dispatch_list(self, node_list):
        for node in node_list:
            self.dispatch(node)

    def visitFunctionDef(self, node):

        if self.classname:
            entity = '%s%s' % (self.classname, node.name)
        else:
            entity = node.name

        name = '%d:1: %r' % (node.lineno, entity)

        if self.graph is not None:
            # closure
            pathnode = self.appendPathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            bottom = PathNode("", look='point')
            self.graph.connect(self.tail, bottom)
            self.graph.connect(pathnode, bottom)
            self.tail = bottom
        else:
            self.graph = PathGraph(name, entity, node.lineno)
            pathnode = PathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            self.graphs["%s%s" % (self.classname, node.name)] = self.graph
            self.reset()

    def visitClassDef(self, node):
        old_classname = self.classname
        self.classname += node.name + "."
        self.dispatch_list(node.body)
        self.classname = old_classname

    def appendPathNode(self, name):
        if not self.tail:
            return
        pathnode = PathNode(name)
        self.graph.connect(self.tail, pathnode)
        self.tail = pathnode
        return pathnode

    def visitSimpleStatement(self, node):
        if node.lineno is None:
            lineno = 0
        else:
            lineno = node.lineno
        name = "Stmt %d" % lineno
        self.appendPathNode(name)

    visitAssert = visitAssign = visitAugAssign = visitDelete = visitPrint = \
        visitRaise = visitYield = visitImport = visitCall = visitSubscript = \
        visitPass = visitContinue = visitBreak = visitGlobal = visitReturn = \
        visitSimpleStatement

    def visitLoop(self, node):
        name = "Loop %d" % node.lineno

        if self.graph is None:
            # global loop
            self.graph = PathGraph(name, name, node.lineno)
            pathnode = PathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            self.graphs["%s%s" % (self.classname, name)] = self.graph
            self.reset()
        else:
            pathnode = self.appendPathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            bottom = PathNode("", look='point')
            self.graph.connect(self.tail, bottom)
            self.graph.connect(pathnode, bottom)
            self.tail = bottom

        # TODO: else clause in node.orelse

    visitFor = visitWhile = visitLoop

    def visitIf(self, node):
        name = "If %d" % node.lineno
        pathnode = self.appendPathNode(name)
        loose_ends = []
        self.dispatch_list(node.body)
        loose_ends.append(self.tail)
        if node.orelse:
            self.tail = pathnode
            self.dispatch_list(node.orelse)
            loose_ends.append(self.tail)
        else:
            loose_ends.append(pathnode)
        if pathnode:
            bottom = PathNode("", look='point')
            for le in loose_ends:
                self.graph.connect(le, bottom)
            self.tail = bottom

    def visitTryExcept(self, node):
        name = "TryExcept %d" % node.lineno
        pathnode = self.appendPathNode(name)
        loose_ends = []
        self.dispatch_list(node.body)
        loose_ends.append(self.tail)
        for handler in node.handlers:
            self.tail = pathnode
            self.dispatch_list(handler.body)
            loose_ends.append(self.tail)
        if pathnode:
            bottom = PathNode("", look='point')
            for le in loose_ends:
                self.graph.connect(le, bottom)
            self.tail = bottom

    def visitWith(self, node):
        name = "With %d" % node.lineno
        self.appendPathNode(name)
        self.dispatch_list(node.body)


class McCabeChecker(object):
    """McCabe cyclomatic complexity checker."""
    name = 'mccabe'
    version = __version__
    _code = 'C901'
    _error_tmpl = "C901 %r is too complex (%d)"
    max_complexity = 0

    def __init__(self, tree, filename):
        self.tree = tree

    @classmethod
    def add_options(cls, parser):
        parser.add_option('--max-complexity', default=-1, action='store',
                          type='int', help="McCabe complexity threshold")
        parser.config_options.append('max-complexity')

    @classmethod
    def parse_options(cls, options):
        cls.max_complexity = options.max_complexity

    def run(self):
        if self.max_complexity < 0:
            return
        visitor = PathGraphingAstVisitor()
        visitor.preorder(self.tree, visitor)
        for graph in visitor.graphs.values():
            if graph.complexity() >= self.max_complexity:
                text = self._error_tmpl % (graph.entity, graph.complexity())
                yield graph.lineno, 0, text, type(self)


def get_code_complexity(code, threshold=7, filename='stdin'):
    try:
        tree = compile(code, filename, "exec", ast.PyCF_ONLY_AST)
    except SyntaxError:
        e = sys.exc_info()[1]
        sys.stderr.write("Unable to parse %s: %s\n" % (filename, e))
        return 0

    complx = []
    McCabeChecker.max_complexity = threshold
    for lineno, offset, text, check in McCabeChecker(tree, filename).run():
        complx.append(dict(
            type=McCabeChecker._code,
            lnum=lineno,
            text=text,
        ))

    return complx


def get_module_complexity(module_path, threshold=7):
    """Returns the complexity of a module"""
    with open(module_path, "rU") as mod:
        code = mod.read()
    return get_code_complexity(code, threshold, filename=module_path)


def main(argv):
    opar = optparse.OptionParser()
    opar.add_option("-d", "--dot", dest="dot",
                    help="output a graphviz dot file", action="store_true")
    opar.add_option("-m", "--min", dest="threshold",
                    help="minimum complexity for output", type="int",
                    default=2)

    options, args = opar.parse_args(argv)

    with open(args[0], "rU") as mod:
        code = mod.read()
    tree = compile(code, args[0], "exec", ast.PyCF_ONLY_AST)
    visitor = PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    if options.dot:
        print('graph {')
        for graph in visitor.graphs.values():
            if graph.complexity() >= options.threshold:
                graph.to_dot()
        print('}')
    else:
        for graph in visitor.graphs.values():
            if graph.complexity() >= options.threshold:
                print(graph.name, graph.complexity())


if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = pep257
#! /usr/bin/env python
"""Static analysis tool for checking docstring conventions and style.

Implemented checks cover PEP257:
http://www.python.org/dev/peps/pep-0257/

Other checks can be added, e.g. NumPy docstring conventions:
https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt

The repository is located at:
http://github.com/GreenSteam/pep257

"""
from __future__ import with_statement

import os
import sys
import tokenize as tk
from itertools import takewhile, dropwhile, chain
from optparse import OptionParser
from re import compile as re


try:
    from StringIO import StringIO
except ImportError:  # Python 3.0 and later
    from io import StringIO


try:
    next
except NameError:  # Python 2.5 and earlier
    nothing = object()

    def next(obj, default=nothing):
        if default == nothing:
            return obj.next()
        else:
            try:
                return obj.next()
            except StopIteration:
                return default


__version__ = '0.3.3-alpha'
__all__ = ('check', 'collect')


humanize = lambda string: re(r'(.)([A-Z]+)').sub(r'\1 \2', string).lower()
is_magic = lambda name: name.startswith('__') and name.endswith('__')
is_ascii = lambda string: all(ord(char) < 128 for char in string)
is_blank = lambda string: not string.strip()
leading_space = lambda string: re('\s*').match(string).group()


class Value(object):

    __init__ = lambda self, *args: vars(self).update(zip(self._fields, args))
    __hash__ = lambda self: hash(repr(self))
    __eq__ = lambda self, other: other and vars(self) == vars(other)

    def __repr__(self):
        args = [vars(self)[field] for field in self._fields]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(map(repr, args)))


class Definition(Value):

    _fields = 'name _source start end docstring children parent'.split()

    _human = property(lambda self: humanize(type(self).__name__))
    kind = property(lambda self: self._human.split()[-1])
    module = property(lambda self: self.parent.module)
    all = property(lambda self: self.module.all)
    _slice = property(lambda self: slice(self.start - 1, self.end))
    source = property(lambda self: ''.join(self._source[self._slice]))
    __iter__ = lambda self: chain([self], *self.children)

    @property
    def _publicity(self):
        return {True: 'public', False: 'private'}[self.is_public]

    def __str__(self):
        return 'in %s %s `%s`' % (self._publicity, self._human, self.name)


class Module(Definition):

    _fields = 'name _source start end docstring children parent _all'.split()
    is_public = True
    _nest = staticmethod(lambda s: {'def': Function, 'class': Class}[s])
    module = property(lambda self: self)
    all = property(lambda self: self._all)
    __str__ = lambda self: 'at module level'


class Function(Definition):

    _nest = staticmethod(lambda s: {'def': NestedFunction,
                                    'class': NestedClass}[s])

    @property
    def is_public(self):
        if self.all is not None:
            return self.name in self.all
        else:  # TODO: are there any magic functions? not methods
            return not self.name.startswith('_') or is_magic(self.name)


class NestedFunction(Function):

    is_public = False


class Method(Function):

    @property
    def is_public(self):
        name_is_public = not self.name.startswith('_') or is_magic(self.name)
        return self.parent.is_public and name_is_public


class Class(Definition):

    _nest = staticmethod(lambda s: {'def': Method, 'class': NestedClass}[s])
    is_public = Function.is_public


class NestedClass(Class):

    is_public = False


class Token(Value):

    _fields = 'kind value start end source'.split()


class TokenStream(object):

    def __init__(self, filelike):
        self._generator = tk.generate_tokens(filelike.readline)
        self.current = Token(*next(self._generator, None))
        self.line = self.current.start[0]

    def move(self):
        previous = self.current
        current = next(self._generator, None)
        self.current = None if current is None else Token(*current)
        self.line = self.current.start[0] if self.current else self.line
        return previous

    def __iter__(self):
        while True:
            if self.current is not None:
                yield self.current
            else:
                return
            self.move()


class AllError(Exception):

    def __init__(self, message):
        Exception.__init__(
            self, message +
            'That means pep257 cannot decide which definitions are public. '
            'Variable __all__ should be present at most once in each file, '
            "in form `__all__ = ('a_public_function', 'APublicClass', ...)`. "
            'More info on __all__: http://stackoverflow.com/q/44834/. ')


class Parser(object):

    def __call__(self, filelike, filename):
        self.source = filelike.readlines()
        src = ''.join(self.source)
        self.stream = TokenStream(StringIO(src))
        self.filename = filename
        self.all = None
        return self.parse_module()

    current = property(lambda self: self.stream.current)
    line = property(lambda self: self.stream.line)

    def consume(self, kind):
        assert self.stream.move().kind == kind

    def leapfrog(self, kind):
        for token in self.stream:
            if token.kind == kind:
                self.consume(kind)
                return

    def parse_docstring(self):
        for token in self.stream:
            if token.kind in [tk.COMMENT, tk.NEWLINE, tk.NL]:
                continue
            elif token.kind == tk.STRING:
                return token.value
            else:
                return None

    def parse_definitions(self, class_, all=False):
        for token in self.stream:
            if all and token.value == '__all__':
                self.parse_all()
            if token.value in ['def', 'class']:
                yield self.parse_definition(class_._nest(token.value))
            if token.kind == tk.INDENT:
                self.consume(tk.INDENT)
                for definition in self.parse_definitions(class_):
                    yield definition
            if token.kind == tk.DEDENT:
                return

    def parse_all(self):
        assert self.current.value == '__all__'
        self.consume(tk.NAME)
        if self.current.value != '=':
            raise AllError('Could not evaluate contents of __all__. ')
        self.consume(tk.OP)
        if self.current.value not in '([':
            raise AllError('Could not evaluate contents of __all__. ')
        if self.current.value == '[':
            msg = ("%s WARNING: __all__ is defined as a list, this means "
                   "pep257 cannot reliably detect contents of the __all__ "
                   "variable, because it can be mutated. Change __all__ to be "
                   "an (immutable) tuple, to remove this warning. Note, "
                   "pep257 uses __all__ to detect which definitions are "
                   "public, to warn if public definitions are missing "
                   "docstrings. If __all__ is a (mutable) list, pep257 cannot "
                   "reliably assume its contents. pep257 will proceed "
                   "assuming __all__ is not mutated.\n" % self.filename)
            sys.stderr.write(msg)
        self.consume(tk.OP)
        s = '('
        while self.current.kind in (tk.NL, tk.COMMENT):
            self.stream.move()
        if self.current.kind != tk.STRING:
            raise AllError('Could not evaluate contents of __all__. ')
        while self.current.value not in ')]':
            s += self.current.value
            self.stream.move()
        s += ')'
        try:
            self.all = eval(s, {})
        except BaseException:
            raise AllError('Could not evaluate contents of __all__: %s. ' % s)

    def parse_module(self):
        start = self.line
        docstring = self.parse_docstring()
        children = list(self.parse_definitions(Module, all=True))
        assert self.current is None
        end = self.line
        module = Module(self.filename, self.source, start, end,
                        docstring, children, None, self.all)
        for child in module.children:
            child.parent = module
        return module

    def parse_definition(self, class_):
        start = self.line
        self.consume(tk.NAME)
        name = self.current.value
        self.leapfrog(tk.INDENT)
        assert self.current.kind != tk.INDENT
        docstring = self.parse_docstring()
        children = list(self.parse_definitions(class_))
        assert self.current.kind == tk.DEDENT
        end = self.line - 1
        definition = class_(name, self.source, start, end,
                            docstring, children, None)
        for child in definition.children:
            child.parent = definition
        return definition


class Error(object):

    """Error in docstring style."""

    # Options that define how errors are printed:
    explain = False
    source = False

    def __init__(self, message=None, final=False):
        self.message, self.is_final = message, final
        self.definition, self.explanation = [None, None]

    code = property(lambda self: self.message.partition(':')[0])
    filename = property(lambda self: self.definition.module.name)
    line = property(lambda self: self.definition.start)

    @property
    def lines(self):
        source = ''
        lines = self.definition._source[self.definition._slice]
        offset = self.definition.start
        lines_stripped = list(reversed(list(dropwhile(is_blank,
                                                      reversed(lines)))))
        numbers_width = 0
        for n, line in enumerate(lines_stripped):
            numbers_width = max(numbers_width, n + offset)
        numbers_width = len(str(numbers_width))
        numbers_width = 6
        for n, line in enumerate(lines_stripped):
            source += '%*d: %s' % (numbers_width, n + offset, line)
            if n > 5:
                source += '        ...\n'
                break
        return source

    def __str__(self):
        self.explanation = '\n'.join(l for l in self.explanation.split('\n')
                                     if not is_blank(l))
        template = '%(filename)s:%(line)s %(definition)s:\n        %(message)s'
        if self.source and self.explain:
            template += '\n\n%(explanation)s\n\n%(lines)s\n'
        elif self.source and not self.explain:
            template += '\n\n%(lines)s\n'
        elif self.explain and not self.source:
            template += '\n\n%(explanation)s\n\n'
        return template % dict((name, getattr(self, name)) for name in
                               ['filename', 'line', 'definition', 'message',
                                'explanation', 'lines'])

    __repr__ = __str__

    def __lt__(self, other):
        return (self.filename, self.line) < (other.filename, other.line)


def parse_options():
    parser = OptionParser(version=__version__,
                          usage='Usage: pep257 [options] [<file|dir>...]')
    option = parser.add_option
    option('-e', '--explain', action='store_true',
           help='show explanation of each error')
    option('-s', '--source', action='store_true',
           help='show source for each error')
    option('--ignore', metavar='<codes>', default='',
           help='ignore a list comma-separated error codes, '
                'for example: --ignore=D101,D202')
    option('--match', metavar='<pattern>', default='(?!test_).*\.py',
           help="check only files that exactly match <pattern> regular "
                "expression; default is --match='(?!test_).*\.py' which "
                "matches files that don't start with 'test_' but end with "
                "'.py'")
    option('--match-dir', metavar='<pattern>', default='[^\.].*',
           help="search only dirs that exactly match <pattern> regular "
                "expression; default is --match-dir='[^\.].*', which matches "
                "all dirs that don't start with a dot")
    return parser.parse_args()


def collect(names, match=lambda name: True, match_dir=lambda name: True):
    """Walk dir trees under `names` and generate filnames that `match`.

    Example
    -------
    >>> sorted(collect(['non-dir.txt', './'],
    ...                match=lambda name: name.endswith('.py')))
    ['non-dir.txt', './pep257.py', './setup.py', './test_pep257.py']

    """
    for name in names:  # map(expanduser, names):
        if os.path.isdir(name):
            for root, dirs, filenames in os.walk(name):
                for dir in dirs:
                    if not match_dir(dir):
                        dirs.remove(dir)  # do not visit those dirs
                for filename in filenames:
                    if match(filename):
                        yield os.path.join(root, filename)
        else:
            yield name


def check(filenames, ignore=()):
    """Generate PEP 257 errors that exist in `filenames` iterable.

    Skips errors with error-codes defined in `ignore` iterable.

    Example
    -------
    >>> check(['pep257.py'], ignore=['D100'])
    <generator object check at 0x...>

    """
    for filename in filenames:
        try:
            with open(filename) as file:
                source = file.read()
            for error in PEP257Checker().check_source(source, filename):
                code = getattr(error, 'code', None)
                if code is not None and code not in ignore:
                    yield error
        except (EnvironmentError, AllError):
            yield sys.exc_info()[1]
        except tk.TokenError:
            yield SyntaxError('invalid syntax in file %s' % filename)


def main(options, arguments):
    Error.explain = options.explain
    Error.source = options.source
    collected = collect(arguments or ['.'],
                        match=re(options.match + '$').match,
                        match_dir=re(options.match_dir + '$').match)
    code = 0
    for error in check(collected, ignore=options.ignore.split(',')):
        sys.stderr.write('%s\n' % error)
        code = 1
    return code


parse = Parser()


def check_for(kind, terminal=False):
    def decorator(f):
        f._check_for = kind
        f._terminal = terminal
        return f
    return decorator


class PEP257Checker(object):

    """Checker for PEP 257.

    D10x: Missing docstrings
    D20x: Whitespace issues
    D30x: Docstring formatting
    D40x: Docstring content issues

    """

    def check_source(self, source, filename):
        module = parse(StringIO(source), filename)
        for definition in module:
            for check in self.checks:
                terminate = False
                if isinstance(definition, check._check_for):
                    error = check(None, definition, definition.docstring)
                    errors = error if hasattr(error, '__iter__') else [error]
                    for error in errors:
                        if error is not None:
                            partition = check.__doc__.partition('.\n')
                            message, _, explanation = partition
                            if error.message is None:
                                error.message = message
                            error.explanation = explanation
                            error.definition = definition
                            yield error
                            if check._terminal:
                                terminate = True
                                break
                if terminate:
                    break

    @property
    def checks(self):
        all = [check for check in vars(type(self)).values()
               if hasattr(check, '_check_for')]
        return sorted(all, key=lambda check: not check._terminal)

    @check_for(Definition, terminal=True)
    def check_docstring_missing(self, definition, docstring):
        """D10{0,1,2,3}: Public definitions should have docstrings.

        All modules should normally have docstrings.  [...] all functions and
        classes exported by a module should also have docstrings. Public
        methods (including the __init__ constructor) should also have
        docstrings.

        Note: Public (exported) definitions are either those with names listed
              in __all__ variable (if present), or those that do not start
              with a single underscore.

        """
        if (not docstring and definition.is_public or
                docstring and is_blank(eval(docstring))):
            codes = {Module: 'D100', Class: 'D101', NestedClass: 'D101',
                     Method: 'D102', Function: 'D103', NestedFunction: 'D103'}
            return Error('%s: Docstring missing' % codes[type(definition)])

    @check_for(Definition)
    def check_one_liners(self, definition, docstring):
        """D200: One-liner docstrings should fit on one line with quotes.

        The closing quotes are on the same line as the opening quotes.
        This looks better for one-liners.

        """
        if docstring:
            lines = eval(docstring).split('\n')
            if len(lines) > 1:
                non_empty_lines = sum(1 for l in lines if not is_blank(l))
                if non_empty_lines == 1:
                    return Error('D200: One-line docstring should not occupy '
                                 '%s lines' % len(lines))

    @check_for(Function)
    def check_no_blank_before(self, function, docstring):  # def
        """D20{1,2}: No blank lines allowed around function/method docstring.

        There's no blank line either before or after the docstring.

        """
        # NOTE: This does not take comments into account.
        # NOTE: This does not take into account functions with groups of code.
        if docstring:
            before, _, after = function.source.partition(docstring)
            blanks_before = list(map(is_blank, before.split('\n')[:-1]))
            blanks_after = list(map(is_blank, after.split('\n')[1:]))
            blanks_before_count = sum(takewhile(bool, reversed(blanks_before)))
            blanks_after_count = sum(takewhile(bool, blanks_after))
            if blanks_before_count != 0:
                yield Error('D201: No blank lines allowed *before* %s '
                            'docstring, found %s'
                            % (function.kind, blanks_before_count))
            if not all(blanks_after) and blanks_after_count != 0:
                yield Error('D202: No blank lines allowed *after* %s '
                            'docstring, found %s'
                            % (function.kind, blanks_after_count))

    @check_for(Class)
    def check_blank_before_after_class(slef, class_, docstring):
        """D20{3,4}: Class docstring should have 1 blank line around them.

        Insert a blank line before and after all docstrings (one-line or
        multi-line) that document a class -- generally speaking, the class's
        methods are separated from each other by a single blank line, and the
        docstring needs to be offset from the first method by a blank line;
        for symmetry, put a blank line between the class header and the
        docstring.

        """
        # NOTE: this gives flase-positive in this case
        # class Foo:
        #
        #     """Docstring."""
        #
        #
        # # comment here
        # def foo(): pass
        if docstring:
            before, _, after = class_.source.partition(docstring)
            blanks_before = list(map(is_blank, before.split('\n')[:-1]))
            blanks_after = list(map(is_blank, after.split('\n')[1:]))
            blanks_before_count = sum(takewhile(bool, reversed(blanks_before)))
            blanks_after_count = sum(takewhile(bool, blanks_after))
            if blanks_before_count != 1:
                yield Error('D203: Expected 1 blank line *before* class '
                            'docstring, found %s' % blanks_before_count)
            if not all(blanks_after) and blanks_after_count != 1:
                yield Error('D204: Expected 1 blank line *after* class '
                            'docstring, found %s' % blanks_after_count)

    @check_for(Definition)
    def check_blank_after_summary(self, definition, docstring):
        """D205: Blank line missing between one-line summary and description.

        Multi-line docstrings consist of a summary line just like a one-line
        docstring, followed by a blank line, followed by a more elaborate
        description. The summary line may be used by automatic indexing tools;
        it is important that it fits on one line and is separated from the
        rest of the docstring by a blank line.

        """
        if docstring:
            lines = eval(docstring).strip().split('\n')
            if len(lines) > 1 and not is_blank(lines[1]):
                return Error()

    @check_for(Definition)
    def check_indent(self, definition, docstring):
        """D20{6,7,8}: The entire docstring should be indented same as code.

        The entire docstring is indented the same as the quotes at its
        first line.

        """
        if docstring:
            before_docstring, _, _ = definition.source.partition(docstring)
            _, _, indent = before_docstring.rpartition('\n')
            lines = docstring.split('\n')
            if len(lines) > 1:
                lines = lines[1:]  # First line does not need indent.
                indents = [leading_space(l) for l in lines if not is_blank(l)]
                if set(' \t') == set(''.join(indents) + indent):
                    return Error('D206: Docstring indented with both tabs and '
                                 'spaces')
                if (len(indents) > 1 and min(indents[:-1]) > indent
                        or indents[-1] > indent):
                    return Error('D208: Docstring is over-indented')
                if min(indents) < indent:
                    return Error('D207: Docstring is under-indented')

    @check_for(Definition)
    def check_newline_after_last_paragraph(self, definition, docstring):
        """D209: Put multi-line docstring closing quotes on separate line.

        Unless the entire docstring fits on a line, place the closing
        quotes on a line by themselves.

        """
        if docstring:
            lines = [l for l in eval(docstring).split('\n') if not is_blank(l)]
            if len(lines) > 1:
                if docstring.split("\n")[-1].strip() not in ['"""', "'''"]:
                    return Error('D209: Put multi-line docstring closing '
                                 'quotes on separate line')

    @check_for(Definition)
    def check_triple_double_quotes(self, definition, docstring):
        r'''D300: Use """triple double quotes""".

        For consistency, always use """triple double quotes""" around
        docstrings. Use r"""raw triple double quotes""" if you use any
        backslashes in your docstrings. For Unicode docstrings, use
        u"""Unicode triple-quoted strings""".

        Note: Exception to this is made if the docstring contains
              """ quotes in its body.

        '''
        if docstring and '"""' in eval(docstring) and docstring.startswith(
                ("'''", "r'''", "u'''")):
            # Allow ''' quotes if docstring contains """, because otherwise """
            # quotes could not be expressed inside docstring.  Not in PEP 257.
            return
        if docstring and not docstring.startswith(('"""', 'r"""', 'u"""')):
            quotes = "'''" if "'''" in docstring[:4] else "'"
            return Error('D300: Expected """-quotes, got %s-quotes' % quotes)

    @check_for(Definition)
    def check_backslashes(self, definition, docstring):
        r'''D301: Use r""" if any backslashes in a docstring.

        Use r"""raw triple double quotes""" if you use any backslashes
        (\) in your docstrings.

        '''
        # Just check that docstring is raw, check_triple_double_quotes
        # ensures the correct quotes.
        if docstring and '\\' in docstring and not docstring.startswith('r'):
            return Error()

    @check_for(Definition)
    def check_unicode_docstring(self, definition, docstring):
        r'''D302: Use u""" for docstrings with Unicode.

        For Unicode docstrings, use u"""Unicode triple-quoted strings""".

        '''
        # Just check that docstring is unicode, check_triple_double_quotes
        # ensures the correct quotes.
        if docstring and sys.version_info[0] <= 2:
            if not is_ascii(docstring) and not docstring.startswith('u'):
                return Error()

    @check_for(Definition)
    def check_ends_with_period(self, definition, docstring):
        """D400: First line should end with a period.

        The [first line of a] docstring is a phrase ending in a period.

        """
        if docstring:
            summary_line = eval(docstring).strip().split('\n')[0]
            if not summary_line.endswith('.'):
                return Error("D400: First line should end with '.', not %r"
                             % summary_line[-1])

    @check_for(Function)
    def check_imperative_mood(self, function, docstring):  # def context
        """D401: First line should be in imperative mood: 'Do', not 'Does'.

        [Docstring] prescribes the function or method's effect as a command:
        ("Do this", "Return that"), not as a description; e.g. don't write
        "Returns the pathname ...".

        """
        if docstring:
            stripped = eval(docstring).strip()
            if stripped:
                first_word = stripped.split()[0]
                if first_word.endswith('s') and not first_word.endswith('ss'):
                    return Error('D401: First line should be imperative: '
                                 '%r, not %r' % (first_word[:-1], first_word))

    @check_for(Function)
    def check_no_signature(self, function, docstring):  # def context
        """D402: First line should not be function's or method's "signature".

        The one-line docstring should NOT be a "signature" reiterating the
        function/method parameters (which can be obtained by introspection).

        """
        if docstring:
            first_line = eval(docstring).strip().split('\n')[0]
            if function.name + '(' in first_line.replace(' ', ''):
                return Error("D402: First line should not be %s's signature"
                             % function.kind)

    # Somewhat hard to determine if return value is mentioned.
    # @check(Function)
    def SKIP_check_return_type(self, function, docstring):
        """D40x: Return value type should be mentioned.

        [T]he nature of the return value cannot be determined by
        introspection, so it should be mentioned.

        """
        if docstring and function.returns_value:
            if 'return' not in docstring.lower():
                return Error()


if __name__ == '__main__':
    try:
        sys.exit(main(*parse_options()))
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/env python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006-2009 Johann C. Rocholl <johann@rocholl.net>
# Copyright (C) 2009-2014 Florent Xicluna <florent.xicluna@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

r"""
Check Python source code formatting, according to PEP 8.

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://github.com/jcrocholl/pep8

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements
900 syntax error
"""
from __future__ import with_statement

__version__ = '1.5.7a0'

import os
import sys
import re
import time
import inspect
import keyword
import tokenize
from optparse import OptionParser
from fnmatch import fnmatch
try:
    from configparser import RawConfigParser
    from io import TextIOWrapper
except ImportError:
    from ConfigParser import RawConfigParser

DEFAULT_EXCLUDE = '.svn,CVS,.bzr,.hg,.git,__pycache__'
DEFAULT_IGNORE = 'E123,E226,E24'
if sys.platform == 'win32':
    DEFAULT_CONFIG = os.path.expanduser(r'~\.pep8')
else:
    DEFAULT_CONFIG = os.path.join(os.getenv('XDG_CONFIG_HOME') or
                                  os.path.expanduser('~/.config'), 'pep8')
PROJECT_CONFIG = ('setup.cfg', 'tox.ini', '.pep8')
TESTSUITE_PATH = os.path.join(os.path.dirname(__file__), 'testsuite')
MAX_LINE_LENGTH = 79
REPORT_FORMAT = {
    'default': '%(path)s:%(row)d:%(col)d: %(code)s %(text)s',
    'pylint': '%(path)s:%(row)d: [%(code)s] %(text)s',
}

PyCF_ONLY_AST = 1024
SINGLETONS = frozenset(['False', 'None', 'True'])
KEYWORDS = frozenset(keyword.kwlist + ['print']) - SINGLETONS
UNARY_OPERATORS = frozenset(['>>', '**', '*', '+', '-'])
ARITHMETIC_OP = frozenset(['**', '*', '/', '//', '+', '-'])
WS_OPTIONAL_OPERATORS = ARITHMETIC_OP.union(['^', '&', '|', '<<', '>>', '%'])
WS_NEEDED_OPERATORS = frozenset([
    '**=', '*=', '/=', '//=', '+=', '-=', '!=', '<>', '<', '>',
    '%=', '^=', '&=', '|=', '==', '<=', '>=', '<<=', '>>=', '='])
WHITESPACE = frozenset(' \t')
NEWLINE = frozenset([tokenize.NL, tokenize.NEWLINE])
SKIP_TOKENS = NEWLINE.union([tokenize.INDENT, tokenize.DEDENT])
# ERRORTOKEN is triggered by backticks in Python 3
SKIP_COMMENTS = SKIP_TOKENS.union([tokenize.COMMENT, tokenize.ERRORTOKEN])
BENCHMARK_KEYS = ['directories', 'files', 'logical lines', 'physical lines']

INDENT_REGEX = re.compile(r'([ \t]*)')
RAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,')
RERAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,.*,\s*\w+\s*$')
ERRORCODE_REGEX = re.compile(r'\b[A-Z]\d{3}\b')
DOCSTRING_REGEX = re.compile(r'u?r?["\']')
EXTRANEOUS_WHITESPACE_REGEX = re.compile(r'[[({] | []}),;:]')
WHITESPACE_AFTER_COMMA_REGEX = re.compile(r'[,;:]\s*(?:  |\t)')
COMPARE_SINGLETON_REGEX = re.compile(r'([=!]=)\s*(None|False|True)')
COMPARE_NEGATIVE_REGEX = re.compile(r'\b(not)\s+[^[({ ]+\s+(in|is)\s')
COMPARE_TYPE_REGEX = re.compile(r'(?:[=!]=|is(?:\s+not)?)\s*type(?:s.\w+Type'
                                r'|\s*\(\s*([^)]*[^ )])\s*\))')
KEYWORD_REGEX = re.compile(r'(\s*)\b(?:%s)\b(\s*)' % r'|'.join(KEYWORDS))
OPERATOR_REGEX = re.compile(r'(?:[^,\s])(\s*)(?:[-+*/|!<=>%&^]+)(\s*)')
LAMBDA_REGEX = re.compile(r'\blambda\b')
HUNK_REGEX = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*$')

# Work around Python < 2.6 behaviour, which does not generate NL after
# a comment which is on a line by itself.
COMMENT_WITH_NL = tokenize.generate_tokens(['#\n'].pop).send(None)[1] == '#\n'


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    r"""Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!

    Okay: if a == 0:\n        a = 1\n        b = 1
    E101: if a == 0:\n        a = 1\n\tb = 1
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    r"""For new projects, spaces-only are strongly recommended over tabs.

    Okay: if True:\n    return
    W191: if True:\n\treturn
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    if '\t' in indent:
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    r"""Trailing whitespace is superfluous.

    The warning returned varies on whether the line itself is blank, for easier
    filtering for those who want to indent their blank lines.

    Okay: spam(1)\n#
    W291: spam(1) \n#
    W293: class Foo(object):\n    \n    bang = 12
    """
    physical_line = physical_line.rstrip('\n')    # chr(10), newline
    physical_line = physical_line.rstrip('\r')    # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c')  # chr(12), form feed, ^L
    stripped = physical_line.rstrip(' \t\v')
    if physical_line != stripped:
        if stripped:
            return len(stripped), "W291 trailing whitespace"
        else:
            return 0, "W293 blank line contains whitespace"


def trailing_blank_lines(physical_line, lines, line_number, total_lines):
    r"""Trailing blank lines are superfluous.

    Okay: spam(1)
    W391: spam(1)\n

    However the last line should end with a new line (warning W292).
    """
    if line_number == total_lines:
        stripped_last_line = physical_line.rstrip()
        if not stripped_last_line:
            return 0, "W391 blank line at end of file"
        if stripped_last_line == physical_line:
            return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line, max_line_length, multiline):
    r"""Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.

    Reports error E501.
    """
    line = physical_line.rstrip()
    length = len(line)
    if length > max_line_length and not noqa(line):
        # Special case for long URLs in multi-line docstrings or comments,
        # but still report the error when the 72 first chars are whitespaces.
        chunks = line.split()
        if ((len(chunks) == 1 and multiline) or
            (len(chunks) == 2 and chunks[0] == '#')) and \
                len(line) - len(chunks[-1]) < max_line_length - 7:
            return
        if hasattr(line, 'decode'):   # Python 2
            # The line could contain multi-byte characters
            try:
                length = len(line.decode('utf-8'))
            except UnicodeError:
                pass
        if length > max_line_length:
            return (max_line_length, "E501 line too long "
                    "(%d > %d characters)" % (length, max_line_length))


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                blank_before, previous_logical, previous_indent_level):
    r"""Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.

    Okay: def a():\n    pass\n\n\ndef b():\n    pass
    Okay: def a():\n    pass\n\n\n# Foo\n# Bar\n\ndef b():\n    pass

    E301: class Foo:\n    b = 0\n    def bar():\n        pass
    E302: def a():\n    pass\n\ndef b(n):\n    pass
    E303: def a():\n    pass\n\n\n\ndef b(n):\n    pass
    E303: def a():\n\n\n\n    pass
    E304: @decorator\n\ndef a():\n    pass
    """
    if line_number < 3 and not previous_logical:
        return  # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        if blank_lines:
            yield 0, "E304 blank lines found after function decorator"
    elif blank_lines > 2 or (indent_level and blank_lines == 2):
        yield 0, "E303 too many blank lines (%d)" % blank_lines
    elif logical_line.startswith(('def ', 'class ', '@')):
        if indent_level:
            if not (blank_before or previous_indent_level < indent_level or
                    DOCSTRING_REGEX.match(previous_logical)):
                yield 0, "E301 expected 1 blank line, found 0"
        elif blank_before != 2:
            yield 0, "E302 expected 2 blank lines, found %d" % blank_before


def extraneous_whitespace(logical_line):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in these situations:
    - Immediately inside parentheses, brackets or braces.
    - Immediately before a comma, semicolon, or colon.

    Okay: spam(ham[1], {eggs: 2})
    E201: spam( ham[1], {eggs: 2})
    E201: spam(ham[ 1], {eggs: 2})
    E201: spam(ham[1], { eggs: 2})
    E202: spam(ham[1], {eggs: 2} )
    E202: spam(ham[1 ], {eggs: 2})
    E202: spam(ham[1], {eggs: 2 })

    E203: if x == 4: print x, y; x, y = y , x
    E203: if x == 4: print x, y ; x, y = y, x
    E203: if x == 4 : print x, y; x, y = y, x
    """
    line = logical_line
    for match in EXTRANEOUS_WHITESPACE_REGEX.finditer(line):
        text = match.group()
        char = text.strip()
        found = match.start()
        if text == char + ' ':
            # assert char in '([{'
            yield found + 1, "E201 whitespace after '%s'" % char
        elif line[found - 1] != ',':
            code = ('E202' if char in '}])' else 'E203')  # if char in ',;:'
            yield found, "%s whitespace before '%s'" % (code, char)


def whitespace_around_keywords(logical_line):
    r"""Avoid extraneous whitespace around keywords.

    Okay: True and False
    E271: True and  False
    E272: True  and False
    E273: True and\tFalse
    E274: True\tand False
    """
    for match in KEYWORD_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E274 tab before keyword"
        elif len(before) > 1:
            yield match.start(1), "E272 multiple spaces before keyword"

        if '\t' in after:
            yield match.start(2), "E273 tab after keyword"
        elif len(after) > 1:
            yield match.start(2), "E271 multiple spaces after keyword"


def missing_whitespace(logical_line):
    r"""Each comma, semicolon or colon should be followed by whitespace.

    Okay: [a, b]
    Okay: (3,)
    Okay: a[1:4]
    Okay: a[:4]
    Okay: a[1:]
    Okay: a[1:4:2]
    E231: ['a','b']
    E231: foo(bar,baz)
    E231: [{'a':'b'}]
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] not in WHITESPACE:
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']') and \
                    before.rfind('{') < before.rfind('['):
                continue  # Slice syntax, no space required
            if char == ',' and line[index + 1] == ')':
                continue  # Allow tuple with only one element: (3,)
            yield index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    r"""Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.

    Okay: a = 1
    Okay: if a == 0:\n    a = 1
    E111:   a = 1

    Okay: for item in items:\n    pass
    E112: for item in items:\npass

    Okay: a = 1\nb = 2
    E113: a = 1\n    b = 2
    """
    if indent_char == ' ' and indent_level % 4:
        yield 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        yield 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        yield 0, "E113 unexpected indentation"


def continued_indentation(logical_line, tokens, indent_level, hang_closing,
                          indent_char, noqa, verbose):
    r"""Continuation lines indentation.

    Continuation lines should align wrapped elements either vertically
    using Python's implicit line joining inside parentheses, brackets
    and braces, or using a hanging indent.

    When using a hanging indent these considerations should be applied:
    - there should be no arguments on the first line, and
    - further indentation should be used to clearly distinguish itself as a
      continuation line.

    Okay: a = (\n)
    E123: a = (\n    )

    Okay: a = (\n    42)
    E121: a = (\n   42)
    E122: a = (\n42)
    E123: a = (\n    42\n    )
    E124: a = (24,\n     42\n)
    E125: if (\n    b):\n    pass
    E126: a = (\n        42)
    E127: a = (24,\n      42)
    E128: a = (24,\n    42)
    E129: if (a or\n    b):\n    pass
    E131: a = (\n    42\n 24)
    """
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    # indent_next tells us whether the next block is indented; assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line; in turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    valid_hangs = (4,) if indent_char != '\t' else (4, 8)
    # remember how many brackets were opened on each line
    parens = [0] * nrows
    # relative indents of physical lines
    rel_indent = [0] * nrows
    # for each depth, collect a list of opening rows
    open_rows = [[0]]
    # for each depth, memorize the hanging indentation
    hangs = [None]
    # visual indents
    indent_chances = {}
    last_indent = tokens[0][2]
    visual_indent = None
    # for each depth, memorize the visual indent column
    indent = [last_indent[1]]
    if verbose >= 3:
        print(">>> " + tokens[0][4].rstrip())

    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = not last_token_multiline and token_type not in NEWLINE

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = expand_indent(line) - indent_level

            # identify closing bracket
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]
                hanging_indent = hang in valid_hangs
                if hanging_indent:
                    break
            if hangs[depth]:
                hanging_indent = (hang == hangs[depth])
            # is there any chance of visual indent?
            visual_indent = (not close_bracket and hang > 0 and
                             indent_chances.get(start[1]))

            if close_bracket and indent[depth]:
                # closing bracket for visual indent
                if start[1] != indent[depth]:
                    yield (start, "E124 closing bracket does not match "
                           "visual indentation")
            elif close_bracket and not hang:
                # closing bracket matches indentation of opening bracket's line
                if hang_closing:
                    yield start, "E133 closing bracket is missing indentation"
            elif indent[depth] and start[1] < indent[depth]:
                if visual_indent is not True:
                    # visual indent is broken
                    yield (start, "E128 continuation line "
                           "under-indented for visual indent")
            elif hanging_indent or (indent_next and rel_indent[row] == 8):
                # hanging indent is verified
                if close_bracket and not hang_closing:
                    yield (start, "E123 closing bracket does not match "
                           "indentation of opening bracket's line")
                hangs[depth] = hang
            elif visual_indent is True:
                # visual indent is verified
                indent[depth] = start[1]
            elif visual_indent in (text, str):
                # ignore token lined up with matching one from a previous line
                pass
            else:
                # indent is broken
                if hang <= 0:
                    error = "E122", "missing indentation or outdented"
                elif indent[depth]:
                    error = "E127", "over-indented for visual indent"
                elif not close_bracket and hangs[depth]:
                    error = "E131", "unaligned for hanging indent"
                else:
                    hangs[depth] = hang
                    if hang > 4:
                        error = "E126", "over-indented for hanging indent"
                    else:
                        error = "E121", "under-indented for hanging indent"
                yield start, "%s continuation line %s" % error

        # look for visual indenting
        if (parens[row] and token_type not in (tokenize.NL, tokenize.COMMENT)
                and not indent[depth]):
            indent[depth] = start[1]
            indent_chances[start[1]] = True
            if verbose >= 4:
                print("bracket depth %s indent to %s" % (depth, start[1]))
        # deal with implicit string concatenation
        elif (token_type in (tokenize.STRING, tokenize.COMMENT) or
              text in ('u', 'ur', 'b', 'br')):
            indent_chances[start[1]] = str
        # special case for the "if" statement because len("if (") == 4
        elif not indent_chances and not row and not depth and text == 'if':
            indent_chances[end[1] + 1] = True
        elif text == ':' and line[end[1]:].isspace():
            open_rows[depth].append(row)

        # keep track of bracket depth
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                hangs.append(None)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                parens[row] += 1
                if verbose >= 4:
                    print("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth]))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                hangs.pop()
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                del open_rows[depth + 1:]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if start[1] not in indent_chances:
                # allow to line up tokens
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]

    if indent_next and expand_indent(line) == indent_level + 4:
        pos = (start[0], indent[0] + 4)
        if visual_indent:
            code = "E129 visually indented line"
        else:
            code = "E125 continuation line"
        yield pos, "%s with same indent as next logical line" % code


def whitespace_before_parameters(logical_line, tokens):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in the following situations:
    - before the open parenthesis that starts the argument list of a
      function call.
    - before the open parenthesis that starts an indexing or slicing.

    Okay: spam(1)
    E211: spam (1)

    Okay: dict['key'] = list[index]
    E211: dict ['key'] = list[index]
    E211: dict['key'] = list [index]
    """
    prev_type, prev_text, __, prev_end, __ = tokens[0]
    for index in range(1, len(tokens)):
        token_type, text, start, end, __ = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            (prev_type == tokenize.NAME or prev_text in '}])') and
            # Syntax "class A (B):" is allowed, but avoid it
            (index < 2 or tokens[index - 2][1] != 'class') and
                # Allow "return (a.foo for a in range(5))"
                not keyword.iskeyword(prev_text)):
            yield prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    r"""Avoid extraneous whitespace around an operator.

    Okay: a = 12 + 3
    E221: a = 4  + 5
    E222: a = 4 +  5
    E223: a = 4\t+ 5
    E224: a = 4 +\t5
    """
    for match in OPERATOR_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E223 tab before operator"
        elif len(before) > 1:
            yield match.start(1), "E221 multiple spaces before operator"

        if '\t' in after:
            yield match.start(2), "E224 tab after operator"
        elif len(after) > 1:
            yield match.start(2), "E222 multiple spaces after operator"


def missing_whitespace_around_operator(logical_line, tokens):
    r"""Surround operators with a single space on either side.

    - Always surround these binary operators with a single space on
      either side: assignment (=), augmented assignment (+=, -= etc.),
      comparisons (==, <, >, !=, <=, >=, in, not in, is, is not),
      Booleans (and, or, not).

    - If operators with different priorities are used, consider adding
      whitespace around the operators with the lowest priorities.

    Okay: i = i + 1
    Okay: submitted += 1
    Okay: x = x * 2 - 1
    Okay: hypot2 = x * x + y * y
    Okay: c = (a + b) * (a - b)
    Okay: foo(bar, key='word', *args, **kwargs)
    Okay: alpha[:-i]

    E225: i=i+1
    E225: submitted +=1
    E225: x = x /2 - 1
    E225: z = x **y
    E226: c = (a+b) * (a-b)
    E226: hypot2 = x*x + y*y
    E227: c = a|b
    E228: msg = fmt%(errno, errmsg)
    """
    parens = 0
    need_space = False
    prev_type = tokenize.OP
    prev_text = prev_end = None
    for token_type, text, start, end, line in tokens:
        if token_type in SKIP_COMMENTS:
            continue
        if text in ('(', 'lambda'):
            parens += 1
        elif text == ')':
            parens -= 1
        if need_space:
            if start != prev_end:
                # Found a (probably) needed space
                if need_space is not True and not need_space[1]:
                    yield (need_space[0],
                           "E225 missing whitespace around operator")
                need_space = False
            elif text == '>' and prev_text in ('<', '-'):
                # Tolerate the "<>" operator, even if running Python 3
                # Deal with Python 3's annotated return value "->"
                pass
            else:
                if need_space is True or need_space[1]:
                    # A needed trailing space was not found
                    yield prev_end, "E225 missing whitespace around operator"
                else:
                    code, optype = 'E226', 'arithmetic'
                    if prev_text == '%':
                        code, optype = 'E228', 'modulo'
                    elif prev_text not in ARITHMETIC_OP:
                        code, optype = 'E227', 'bitwise or shift'
                    yield (need_space[0], "%s missing whitespace "
                           "around %s operator" % (code, optype))
                need_space = False
        elif token_type == tokenize.OP and prev_end is not None:
            if text == '=' and parens:
                # Allow keyword args or defaults: foo(bar=None).
                pass
            elif text in WS_NEEDED_OPERATORS:
                need_space = True
            elif text in UNARY_OPERATORS:
                # Check if the operator is being used as a binary operator
                # Allow unary operators: -123, -x, +1.
                # Allow argument unpacking: foo(*args, **kwargs).
                if (prev_text in '}])' if prev_type == tokenize.OP
                        else prev_text not in KEYWORDS):
                    need_space = None
            elif text in WS_OPTIONAL_OPERATORS:
                need_space = None

            if need_space is None:
                # Surrounding space is optional, but ensure that
                # trailing space matches opening space
                need_space = (prev_end, start != prev_end)
            elif need_space and start == prev_end:
                # A needed opening space was not found
                yield prev_end, "E225 missing whitespace around operator"
                need_space = False
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_comma(logical_line):
    r"""Avoid extraneous whitespace after a comma or a colon.

    Note: these checks are disabled by default

    Okay: a = (1, 2)
    E241: a = (1,  2)
    E242: a = (1,\t2)
    """
    line = logical_line
    for m in WHITESPACE_AFTER_COMMA_REGEX.finditer(line):
        found = m.start() + 1
        if '\t' in m.group():
            yield found, "E242 tab after '%s'" % m.group()[0]
        else:
            yield found, "E241 multiple spaces after '%s'" % m.group()[0]


def whitespace_around_named_parameter_equals(logical_line, tokens):
    r"""Don't use spaces around the '=' sign in function arguments.

    Don't use spaces around the '=' sign when used to indicate a
    keyword argument or a default parameter value.

    Okay: def complex(real, imag=0.0):
    Okay: return magic(r=real, i=imag)
    Okay: boolean(a == b)
    Okay: boolean(a != b)
    Okay: boolean(a <= b)
    Okay: boolean(a >= b)

    E251: def complex(real, imag = 0.0):
    E251: return magic(r = real, i = imag)
    """
    parens = 0
    no_space = False
    prev_end = None
    message = "E251 unexpected spaces around keyword / parameter equals"
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.NL:
            continue
        if no_space:
            no_space = False
            if start != prev_end:
                yield (prev_end, message)
        elif token_type == tokenize.OP:
            if text == '(':
                parens += 1
            elif text == ')':
                parens -= 1
            elif parens and text == '=':
                no_space = True
                if start != prev_end:
                    yield (prev_end, message)
        prev_end = end


def whitespace_before_comment(logical_line, tokens):
    r"""Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.  Inline
    comments should be separated by at least two spaces from the statement.
    They should start with a # and a single space.

    Each line of a block comment starts with a # and a single space
    (unless it is indented text inside the comment).

    Okay: x = x + 1  # Increment x
    Okay: x = x + 1    # Increment x
    Okay: # Block comment
    E261: x = x + 1 # Increment x
    E262: x = x + 1  #Increment x
    E262: x = x + 1  #  Increment x
    E265: #Block comment
    """
    prev_end = (0, 0)
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            inline_comment = line[:start[1]].strip()
            if inline_comment:
                if prev_end[0] == start[0] and start[1] < prev_end[1] + 2:
                    yield (prev_end,
                           "E261 at least two spaces before inline comment")
            symbol, sp, comment = text.partition(' ')
            bad_prefix = symbol not in ('#', '#:')
            if inline_comment:
                if bad_prefix or comment[:1].isspace():
                    yield start, "E262 inline comment should start with '# '"
            elif bad_prefix:
                if text.rstrip('#') and (start[0] > 1 or symbol[1] != '!'):
                    yield start, "E265 block comment should start with '# '"
        elif token_type != tokenize.NL:
            prev_end = end


def imports_on_separate_lines(logical_line):
    r"""Imports should usually be on separate lines.

    Okay: import os\nimport sys
    E401: import sys, os

    Okay: from subprocess import Popen, PIPE
    Okay: from myclas import MyClass
    Okay: from foo.bar.yourclass import YourClass
    Okay: import myclass
    Okay: import foo.bar.yourclass
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if -1 < found and ';' not in line[:found]:
            yield found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    r"""Compound statements (on the same line) are generally discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements.
    Also avoid folding such long lines!

    Okay: if foo == 'blah':\n    do_blah_thing()
    Okay: do_one()
    Okay: do_two()
    Okay: do_three()

    E701: if foo == 'blah': do_blah_thing()
    E701: for x in lst: total += x
    E701: while t < 10: t = delay()
    E701: if foo == 'blah': do_blah_thing()
    E701: else: do_non_blah_thing()
    E701: try: something()
    E701: finally: cleanup()
    E701: if foo == 'blah': one(); two(); three()

    E702: do_one(); do_two(); do_three()
    E703: do_four();  # useless semicolon
    """
    line = logical_line
    last_char = len(line) - 1
    found = line.find(':')
    while -1 < found < last_char:
        before = line[:found]
        if (before.count('{') <= before.count('}') and  # {'a': 1} (dict)
            before.count('[') <= before.count(']') and  # [1:2] (slice)
            before.count('(') <= before.count(')') and  # (Python 3 annotation)
                not LAMBDA_REGEX.search(before)):       # lambda x: x
            yield found, "E701 multiple statements on one line (colon)"
        found = line.find(':', found + 1)
    found = line.find(';')
    while -1 < found:
        if found < last_char:
            yield found, "E702 multiple statements on one line (semicolon)"
        else:
            yield found, "E703 statement ends with a semicolon"
        found = line.find(';', found + 1)


def explicit_line_join(logical_line, tokens):
    r"""Avoid explicit line join between brackets.

    The preferred way of wrapping long lines is by using Python's implied line
    continuation inside parentheses, brackets and braces.  Long lines can be
    broken over multiple lines by wrapping expressions in parentheses.  These
    should be used in preference to using a backslash for line continuation.

    E502: aaa = [123, \\n       123]
    E502: aaa = ("bbb " \\n       "ccc")

    Okay: aaa = [123,\n       123]
    Okay: aaa = ("bbb "\n       "ccc")
    Okay: aaa = "bbb " \\n    "ccc"
    """
    prev_start = prev_end = parens = 0
    for token_type, text, start, end, line in tokens:
        if start[0] != prev_start and parens and backslash:
            yield backslash, "E502 the backslash is redundant between brackets"
        if end[0] != prev_end:
            if line.rstrip('\r\n').endswith('\\'):
                backslash = (end[0], len(line.splitlines()[-1]) - 1)
            else:
                backslash = None
            prev_start = prev_end = end[0]
        else:
            prev_start = start[0]
        if token_type == tokenize.OP:
            if text in '([{':
                parens += 1
            elif text in ')]}':
                parens -= 1


def comparison_to_singleton(logical_line, noqa):
    r"""Comparison to singletons should use "is" or "is not".

    Comparisons to singletons like None should always be done
    with "is" or "is not", never the equality operators.

    Okay: if arg is not None:
    E711: if arg != None:
    E712: if arg == True:

    Also, beware of writing if x when you really mean if x is not None --
    e.g. when testing whether a variable or argument that defaults to None was
    set to some other value.  The other value might have a type (such as a
    container) that could be false in a boolean context!
    """
    match = not noqa and COMPARE_SINGLETON_REGEX.search(logical_line)
    if match:
        same = (match.group(1) == '==')
        singleton = match.group(2)
        msg = "'if cond is %s:'" % (('' if same else 'not ') + singleton)
        if singleton in ('None',):
            code = 'E711'
        else:
            code = 'E712'
            nonzero = ((singleton == 'True' and same) or
                       (singleton == 'False' and not same))
            msg += " or 'if %scond:'" % ('' if nonzero else 'not ')
        yield match.start(1), ("%s comparison to %s should be %s" %
                               (code, singleton, msg))


def comparison_negative(logical_line):
    r"""Negative comparison should be done using "not in" and "is not".

    Okay: if x not in y:\n    pass
    Okay: assert (X in Y or X is Z)
    Okay: if not (X in Y):\n    pass
    Okay: zz = x is not y
    E713: Z = not X in Y
    E713: if not X.B in Y:\n    pass
    E714: if not X is Y:\n    pass
    E714: Z = not X.B is Y
    """
    match = COMPARE_NEGATIVE_REGEX.search(logical_line)
    if match:
        pos = match.start(1)
        if match.group(2) == 'in':
            yield pos, "E713 test for membership should be 'not in'"
        else:
            yield pos, "E714 test for object identity should be 'is not'"


def comparison_type(logical_line):
    r"""Object type comparisons should always use isinstance().

    Do not compare types directly.

    Okay: if isinstance(obj, int):
    E721: if type(obj) is type(1):

    When checking if an object is a string, keep in mind that it might be a
    unicode string too! In Python 2.3, str and unicode have a common base
    class, basestring, so you can do:

    Okay: if isinstance(obj, basestring):
    Okay: if type(a1) is type(b1):
    """
    match = COMPARE_TYPE_REGEX.search(logical_line)
    if match:
        inst = match.group(1)
        if inst and isidentifier(inst) and inst not in SINGLETONS:
            return  # Allow comparison for types which are not obvious
        yield match.start(), "E721 do not compare types, use 'isinstance()'"


def python_3000_has_key(logical_line, noqa):
    r"""The {}.has_key() method is removed in Python 3: use the 'in' operator.

    Okay: if "alph" in d:\n    print d["alph"]
    W601: assert d.has_key('alph')
    """
    pos = logical_line.find('.has_key(')
    if pos > -1 and not noqa:
        yield pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    r"""When raising an exception, use "raise ValueError('message')".

    The older form is removed in Python 3.

    Okay: raise DummyError("Message")
    W602: raise DummyError, "Message"
    """
    match = RAISE_COMMA_REGEX.match(logical_line)
    if match and not RERAISE_COMMA_REGEX.match(logical_line):
        yield match.end() - 1, "W602 deprecated form of raising exception"


def python_3000_not_equal(logical_line):
    r"""New code should always use != instead of <>.

    The older syntax is removed in Python 3.

    Okay: if a != 'no':
    W603: if a <> 'no':
    """
    pos = logical_line.find('<>')
    if pos > -1:
        yield pos, "W603 '<>' is deprecated, use '!='"


def python_3000_backticks(logical_line):
    r"""Backticks are removed in Python 3: use repr() instead.

    Okay: val = repr(1 + 2)
    W604: val = `1 + 2`
    """
    pos = logical_line.find('`')
    if pos > -1:
        yield pos, "W604 backticks are deprecated, use 'repr()'"


##############################################################################
# Helper functions
##############################################################################


if '' == ''.encode():
    # Python 2: implicit encoding.
    def readlines(filename):
        """Read the source code."""
        with open(filename) as f:
            return f.readlines()
    isidentifier = re.compile(r'[a-zA-Z_]\w*').match
    stdin_get_value = sys.stdin.read
else:
    # Python 3
    def readlines(filename):
        """Read the source code."""
        try:
            with open(filename, 'rb') as f:
                (coding, lines) = tokenize.detect_encoding(f.readline)
                f = TextIOWrapper(f, coding, line_buffering=True)
                return [l.decode(coding) for l in lines] + f.readlines()
        except (LookupError, SyntaxError, UnicodeError):
            # Fall back if file encoding is improperly declared
            with open(filename, encoding='latin-1') as f:
                return f.readlines()
    isidentifier = str.isidentifier

    def stdin_get_value():
        return TextIOWrapper(sys.stdin.buffer, errors='ignore').read()
noqa = re.compile(r'# no(?:qa|pep8)\b', re.I).search


def expand_indent(line):
    r"""Return the amount of indentation.

    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\t')
    8
    >>> expand_indent('       \t')
    8
    >>> expand_indent('        \t')
    16
    """
    if '\t' not in line:
        return len(line) - len(line.lstrip())
    result = 0
    for char in line:
        if char == '\t':
            result = result // 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


def mute_string(text):
    """Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    # String modifiers (e.g. u or r)
    start = text.index(text[-1]) + 1
    end = len(text) - 1
    # Triple quotes
    if text[-3:] in ('"""', "'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


def parse_udiff(diff, patterns=None, parent='.'):
    """Return a dictionary of matching lines."""
    # For each file of the diff, the entry key is the filename,
    # and the value is a set of row numbers to consider.
    rv = {}
    path = nrows = None
    for line in diff.splitlines():
        if nrows:
            if line[:1] != '-':
                nrows -= 1
            continue
        if line[:3] == '@@ ':
            hunk_match = HUNK_REGEX.match(line)
            (row, nrows) = [int(g or '1') for g in hunk_match.groups()]
            rv[path].update(range(row, row + nrows))
        elif line[:3] == '+++':
            path = line[4:].split('\t', 1)[0]
            if path[:2] == 'b/':
                path = path[2:]
            rv[path] = set()
    return dict([(os.path.join(parent, path), rows)
                 for (path, rows) in rv.items()
                 if rows and filename_match(path, patterns)])


def normalize_paths(value, parent=os.curdir):
    """Parse a comma-separated list of paths.

    Return a list of absolute paths.
    """
    if not value or isinstance(value, list):
        return value
    paths = []
    for path in value.split(','):
        if '/' in path:
            path = os.path.abspath(os.path.join(parent, path))
        paths.append(path.rstrip('/'))
    return paths


def filename_match(filename, patterns, default=True):
    """Check if patterns contains a pattern that matches filename.

    If patterns is unspecified, this always returns True.
    """
    if not patterns:
        return default
    return any(fnmatch(filename, pattern) for pattern in patterns)


if COMMENT_WITH_NL:
    def _is_eol_token(token):
        return (token[0] in NEWLINE or
                (token[0] == tokenize.COMMENT and token[1] == token[4]))
else:
    def _is_eol_token(token):
        return token[0] in NEWLINE


##############################################################################
# Framework to run all checks
##############################################################################


_checks = {'physical_line': {}, 'logical_line': {}, 'tree': {}}


def register_check(check, codes=None):
    """Register a new check object."""
    def _add_check(check, kind, codes, args):
        if check in _checks[kind]:
            _checks[kind][check][0].extend(codes or [])
        else:
            _checks[kind][check] = (codes or [''], args)
    if inspect.isfunction(check):
        args = inspect.getargspec(check)[0]
        if args and args[0] in ('physical_line', 'logical_line'):
            if codes is None:
                codes = ERRORCODE_REGEX.findall(check.__doc__ or '')
            _add_check(check, args[0], codes, args)
    elif inspect.isclass(check):
        if inspect.getargspec(check.__init__)[0][:2] == ['self', 'tree']:
            _add_check(check, 'tree', codes, None)


def init_checks_registry():
    """Register all globally visible functions.

    The first argument name is either 'physical_line' or 'logical_line'.
    """
    mod = inspect.getmodule(register_check)
    for (name, function) in inspect.getmembers(mod, inspect.isfunction):
        register_check(function)
init_checks_registry()


class Checker(object):
    """Load a Python source file, tokenize it, check coding style."""

    def __init__(self, filename=None, lines=None,
                 options=None, report=None, **kwargs):
        if options is None:
            options = StyleGuide(kwargs).options
        else:
            assert not kwargs
        self._io_error = None
        self._physical_checks = options.physical_checks
        self._logical_checks = options.logical_checks
        self._ast_checks = options.ast_checks
        self.max_line_length = options.max_line_length
        self.multiline = False  # in a multiline string?
        self.hang_closing = options.hang_closing
        self.verbose = options.verbose
        self.filename = filename
        if filename is None:
            self.filename = 'stdin'
            self.lines = lines or []
        elif filename == '-':
            self.filename = 'stdin'
            self.lines = stdin_get_value().splitlines(True)
        elif lines is None:
            try:
                self.lines = readlines(filename)
            except IOError:
                (exc_type, exc) = sys.exc_info()[:2]
                self._io_error = '%s: %s' % (exc_type.__name__, exc)
                self.lines = []
        else:
            self.lines = lines
        if self.lines:
            ord0 = ord(self.lines[0][0])
            if ord0 in (0xef, 0xfeff):  # Strip the UTF-8 BOM
                if ord0 == 0xfeff:
                    self.lines[0] = self.lines[0][1:]
                elif self.lines[0][:3] == '\xef\xbb\xbf':
                    self.lines[0] = self.lines[0][3:]
        self.report = report or options.report
        self.report_error = self.report.error

    def report_invalid_syntax(self):
        """Check if the syntax is valid."""
        (exc_type, exc) = sys.exc_info()[:2]
        if len(exc.args) > 1:
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
        else:
            offset = (1, 0)
        self.report_error(offset[0], offset[1] or 0,
                          'E901 %s: %s' % (exc_type.__name__, exc.args[0]),
                          self.report_invalid_syntax)

    def readline(self):
        """Get the next line from the input buffer."""
        if self.line_number >= self.total_lines:
            return ''
        line = self.lines[self.line_number]
        self.line_number += 1
        if self.indent_char is None and line[:1] in WHITESPACE:
            self.indent_char = line[0]
        return line

    def run_check(self, check, argument_names):
        """Run a check plugin."""
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """Run all physical checks on a raw input line."""
        self.physical_line = line
        for name, check, argument_names in self._physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                (offset, text) = result
                self.report_error(self.line_number, offset, text, check)
                if text[:4] == 'E101':
                    self.indent_char = line[0]

    def build_tokens_line(self):
        """Build a logical line from tokens."""
        logical = []
        comments = []
        length = 0
        prev_row = prev_col = mapping = None
        for token_type, text, start, end, line in self.tokens:
            if token_type in SKIP_TOKENS:
                continue
            if not mapping:
                mapping = [(0, start)]
            if token_type == tokenize.COMMENT:
                comments.append(text)
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if prev_row:
                (start_row, start_col) = start
                if prev_row != start_row:    # different row
                    prev_text = self.lines[prev_row - 1][prev_col - 1]
                    if prev_text == ',' or (prev_text not in '{[('
                                            and text not in '}])'):
                        text = ' ' + text
                elif prev_col != start_col:  # different column
                    text = line[prev_col:start_col] + text
            logical.append(text)
            length += len(text)
            mapping.append((length, end))
            (prev_row, prev_col) = end
        self.logical_line = ''.join(logical)
        self.noqa = comments and noqa(''.join(comments))
        return mapping

    def check_logical(self):
        """Build a line from tokens and run all logical checks on it."""
        self.report.increment_logical_line()
        mapping = self.build_tokens_line()
        (start_row, start_col) = mapping[0][1]
        start_line = self.lines[start_row - 1]
        self.indent_level = expand_indent(start_line[:start_col])
        if self.blank_before < self.blank_lines:
            self.blank_before = self.blank_lines
        if self.verbose >= 2:
            print(self.logical_line[:80].rstrip())
        for name, check, argument_names in self._logical_checks:
            if self.verbose >= 4:
                print('   ' + name)
            for offset, text in self.run_check(check, argument_names) or ():
                if not isinstance(offset, tuple):
                    for token_offset, pos in mapping:
                        if offset <= token_offset:
                            break
                    offset = (pos[0], pos[1] + offset - token_offset)
                self.report_error(offset[0], offset[1], text, check)
        if self.logical_line:
            self.previous_indent_level = self.indent_level
            self.previous_logical = self.logical_line
        self.blank_lines = 0
        self.tokens = []

    def check_ast(self):
        """Build the file's AST and run all AST checks."""
        try:
            tree = compile(''.join(self.lines), '', 'exec', PyCF_ONLY_AST)
        except (SyntaxError, TypeError):
            return self.report_invalid_syntax()
        for name, cls, __ in self._ast_checks:
            checker = cls(tree, self.filename)
            for lineno, offset, text, check in checker.run():
                if not self.lines or not noqa(self.lines[lineno - 1]):
                    self.report_error(lineno, offset, text, check)

    def generate_tokens(self):
        """Tokenize the file, run physical line checks and yield tokens."""
        if self._io_error:
            self.report_error(1, 0, 'E902 %s' % self._io_error, readlines)
        tokengen = tokenize.generate_tokens(self.readline)
        try:
            for token in tokengen:
                self.maybe_check_physical(token)
                yield token
        except (SyntaxError, tokenize.TokenError):
            self.report_invalid_syntax()

    def maybe_check_physical(self, token):
        """If appropriate (based on token), check current physical line(s)."""
        # Called after every token, but act only on end of line.
        if _is_eol_token(token):
            # Obviously, a newline token ends a single physical line.
            self.check_physical(token[4])
        elif token[0] == tokenize.STRING and '\n' in token[1]:
            # Less obviously, a string that contains newlines is a
            # multiline string, either triple-quoted or with internal
            # newlines backslash-escaped. Check every physical line in the
            # string *except* for the last one: its newline is outside of
            # the multiline string, so we consider it a regular physical
            # line, and will check it like any other physical line.
            #
            # Subtleties:
            # - we don't *completely* ignore the last line; if it contains
            #   the magical "# noqa" comment, we disable all physical
            #   checks for the entire multiline string
            # - have to wind self.line_number back because initially it
            #   points to the last line of the string, and we want
            #   check_physical() to give accurate feedback
            if noqa(token[4]):
                return
            self.multiline = True
            self.line_number = token[2][0]
            for line in token[1].split('\n')[:-1]:
                self.check_physical(line + '\n')
                self.line_number += 1
            self.multiline = False

    def check_all(self, expected=None, line_offset=0):
        """Run all checks on the input file."""
        self.report.init_file(self.filename, self.lines, expected, line_offset)
        self.total_lines = len(self.lines)
        if self._ast_checks:
            self.check_ast()
        self.line_number = 0
        self.indent_char = None
        self.indent_level = self.previous_indent_level = 0
        self.previous_logical = ''
        self.tokens = []
        self.blank_lines = self.blank_before = 0
        parens = 0
        for token in self.generate_tokens():
            self.tokens.append(token)
            token_type, text = token[0:2]
            if self.verbose >= 3:
                if token[2][0] == token[3][0]:
                    pos = '[%s:%s]' % (token[2][1] or '', token[3][1])
                else:
                    pos = 'l.%s' % token[3][0]
                print('l.%s\t%s\t%s\t%r' %
                      (token[2][0], pos, tokenize.tok_name[token[0]], text))
            if token_type == tokenize.OP:
                if text in '([{':
                    parens += 1
                elif text in '}])':
                    parens -= 1
            elif not parens:
                if token_type in NEWLINE:
                    if token_type == tokenize.NEWLINE:
                        self.check_logical()
                        self.blank_before = 0
                    elif len(self.tokens) == 1:
                        # The physical line contains only this token.
                        self.blank_lines += 1
                        del self.tokens[0]
                    else:
                        self.check_logical()
                elif COMMENT_WITH_NL and token_type == tokenize.COMMENT:
                    if len(self.tokens) == 1:
                        # The comment also ends a physical line
                        token = list(token)
                        token[1] = text.rstrip('\r\n')
                        token[3] = (token[2][0], token[2][1] + len(token[1]))
                        self.tokens = [tuple(token)]
                        self.check_logical()
        if len(self.tokens) > 1 and (token_type == tokenize.ENDMARKER and
                                     self.tokens[-2][0] not in SKIP_TOKENS):
            self.tokens.pop()
            self.check_physical(self.tokens[-1][4])
            self.check_logical()
        return self.report.get_file_results()


class BaseReport(object):
    """Collect the results of the checks."""

    print_filename = False

    def __init__(self, options):
        self._benchmark_keys = options.benchmark_keys
        self._ignore_code = options.ignore_code
        # Results
        self.elapsed = 0
        self.total_errors = 0
        self.counters = dict.fromkeys(self._benchmark_keys, 0)
        self.messages = {}

    def start(self):
        """Start the timer."""
        self._start_time = time.time()

    def stop(self):
        """Stop the timer."""
        self.elapsed = time.time() - self._start_time

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self.filename = filename
        self.lines = lines
        self.expected = expected or ()
        self.line_offset = line_offset
        self.file_errors = 0
        self.counters['files'] += 1
        self.counters['physical lines'] += len(lines)

    def increment_logical_line(self):
        """Signal a new logical line."""
        self.counters['logical lines'] += 1

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = text[:4]
        if self._ignore_code(code):
            return
        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1
            self.messages[code] = text[5:]
        # Don't care about expected errors or warnings
        if code in self.expected:
            return
        if self.print_filename and not self.file_errors:
            print(self.filename)
        self.file_errors += 1
        self.total_errors += 1
        return code

    def get_file_results(self):
        """Return the count of errors and warnings for this file."""
        return self.file_errors

    def get_count(self, prefix=''):
        """Return the total count of errors and warnings."""
        return sum([self.counters[key]
                    for key in self.messages if key.startswith(prefix)])

    def get_statistics(self, prefix=''):
        """Get statistics for message codes that start with the prefix.

        prefix='' matches all errors and warnings
        prefix='E' matches all errors
        prefix='W' matches all warnings
        prefix='E4' matches all errors that have to do with imports
        """
        return ['%-7s %s %s' % (self.counters[key], key, self.messages[key])
                for key in sorted(self.messages) if key.startswith(prefix)]

    def print_statistics(self, prefix=''):
        """Print overall statistics (number of errors and warnings)."""
        for line in self.get_statistics(prefix):
            print(line)

    def print_benchmark(self):
        """Print benchmark numbers."""
        print('%-7.2f %s' % (self.elapsed, 'seconds elapsed'))
        if self.elapsed:
            for key in self._benchmark_keys:
                print('%-7d %s per second (%d total)' %
                      (self.counters[key] / self.elapsed, key,
                       self.counters[key]))


class FileReport(BaseReport):
    """Collect the results of the checks and print only the filenames."""
    print_filename = True


class StandardReport(BaseReport):
    """Collect and print the results of the checks."""

    def __init__(self, options):
        super(StandardReport, self).__init__(options)
        self._fmt = REPORT_FORMAT.get(options.format.lower(),
                                      options.format)
        self._repeat = options.repeat
        self._show_source = options.show_source
        self._show_pep8 = options.show_pep8

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self._deferred_print = []
        return super(StandardReport, self).init_file(
            filename, lines, expected, line_offset)

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = super(StandardReport, self).error(line_number, offset,
                                                 text, check)
        if code and (self.counters[code] == 1 or self._repeat):
            self._deferred_print.append(
                (line_number, offset, code, text[5:], check.__doc__))
        return code

    def get_file_results(self):
        """Print the result and return the overall count for this file."""
        self._deferred_print.sort()
        for line_number, offset, code, text, doc in self._deferred_print:
            print(self._fmt % {
                'path': self.filename,
                'row': self.line_offset + line_number, 'col': offset + 1,
                'code': code, 'text': text,
            })
            if self._show_source:
                if line_number > len(self.lines):
                    line = ''
                else:
                    line = self.lines[line_number - 1]
                print(line.rstrip())
                print(re.sub(r'\S', ' ', line[:offset]) + '^')
            if self._show_pep8 and doc:
                print('    ' + doc.strip())
        return self.file_errors


class DiffReport(StandardReport):
    """Collect and print the results for the changed lines only."""

    def __init__(self, options):
        super(DiffReport, self).__init__(options)
        self._selected = options.selected_lines

    def error(self, line_number, offset, text, check):
        if line_number not in self._selected[self.filename]:
            return
        return super(DiffReport, self).error(line_number, offset, text, check)


class StyleGuide(object):
    """Initialize a PEP-8 instance with few options."""

    def __init__(self, *args, **kwargs):
        # build options from the command line
        self.checker_class = kwargs.pop('checker_class', Checker)
        parse_argv = kwargs.pop('parse_argv', False)
        config_file = kwargs.pop('config_file', None)
        parser = kwargs.pop('parser', None)
        # build options from dict
        options_dict = dict(*args, **kwargs)
        arglist = None if parse_argv else options_dict.get('paths', None)
        options, self.paths = process_options(
            arglist, parse_argv, config_file, parser)
        if options_dict:
            options.__dict__.update(options_dict)
            if 'paths' in options_dict:
                self.paths = options_dict['paths']

        self.runner = self.input_file
        self.options = options

        if not options.reporter:
            options.reporter = BaseReport if options.quiet else StandardReport

        options.select = tuple(options.select or ())
        if not (options.select or options.ignore or
                options.testsuite or options.doctest) and DEFAULT_IGNORE:
            # The default choice: ignore controversial checks
            options.ignore = tuple(DEFAULT_IGNORE.split(','))
        else:
            # Ignore all checks which are not explicitly selected
            options.ignore = ('',) if options.select else tuple(options.ignore)
        options.benchmark_keys = BENCHMARK_KEYS[:]
        options.ignore_code = self.ignore_code
        options.physical_checks = self.get_checks('physical_line')
        options.logical_checks = self.get_checks('logical_line')
        options.ast_checks = self.get_checks('tree')
        self.init_report()

    def init_report(self, reporter=None):
        """Initialize the report instance."""
        self.options.report = (reporter or self.options.reporter)(self.options)
        return self.options.report

    def check_files(self, paths=None):
        """Run all checks on the paths."""
        if paths is None:
            paths = self.paths
        report = self.options.report
        runner = self.runner
        report.start()
        try:
            for path in paths:
                if os.path.isdir(path):
                    self.input_dir(path)
                elif not self.excluded(path):
                    runner(path)
        except KeyboardInterrupt:
            print('... stopped')
        report.stop()
        return report

    def input_file(self, filename, lines=None, expected=None, line_offset=0):
        """Run all checks on a Python source file."""
        if self.options.verbose:
            print('checking %s' % filename)
        fchecker = self.checker_class(
            filename, lines=lines, options=self.options)
        return fchecker.check_all(expected=expected, line_offset=line_offset)

    def input_dir(self, dirname):
        """Check all files in this directory and all subdirectories."""
        dirname = dirname.rstrip('/')
        if self.excluded(dirname):
            return 0
        counters = self.options.report.counters
        verbose = self.options.verbose
        filepatterns = self.options.filename
        runner = self.runner
        for root, dirs, files in os.walk(dirname):
            if verbose:
                print('directory ' + root)
            counters['directories'] += 1
            for subdir in sorted(dirs):
                if self.excluded(subdir, root):
                    dirs.remove(subdir)
            for filename in sorted(files):
                # contain a pattern that matches?
                if ((filename_match(filename, filepatterns) and
                     not self.excluded(filename, root))):
                    runner(os.path.join(root, filename))

    def excluded(self, filename, parent=None):
        """Check if the file should be excluded.

        Check if 'options.exclude' contains a pattern that matches filename.
        """
        if not self.options.exclude:
            return False
        basename = os.path.basename(filename)
        if filename_match(basename, self.options.exclude):
            return True
        if parent:
            filename = os.path.join(parent, filename)
        filename = os.path.abspath(filename)
        return filename_match(filename, self.options.exclude)

    def ignore_code(self, code):
        """Check if the error code should be ignored.

        If 'options.select' contains a prefix of the error code,
        return False.  Else, if 'options.ignore' contains a prefix of
        the error code, return True.
        """
        if len(code) < 4 and any(s.startswith(code)
                                 for s in self.options.select):
            return False
        return (code.startswith(self.options.ignore) and
                not code.startswith(self.options.select))

    def get_checks(self, argument_name):
        """Get all the checks for this category.

        Find all globally visible functions where the first argument name
        starts with argument_name and which contain selected tests.
        """
        checks = []
        for check, attrs in _checks[argument_name].items():
            (codes, args) = attrs
            if any(not (code and self.ignore_code(code)) for code in codes):
                checks.append((check.__name__, check, args))
        return sorted(checks)


def get_parser(prog='pep8', version=__version__):
    parser = OptionParser(prog=prog, version=version,
                          usage="%prog [options] input ...")
    parser.config_options = [
        'exclude', 'filename', 'select', 'ignore', 'max-line-length',
        'hang-closing', 'count', 'format', 'quiet', 'show-pep8',
        'show-source', 'statistics', 'verbose']
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('-r', '--repeat', default=True, action='store_true',
                      help="(obsolete) show all occurrences of the same error")
    parser.add_option('--first', action='store_false', dest='repeat',
                      help="show first occurrence of each error")
    parser.add_option('--exclude', metavar='patterns', default=DEFAULT_EXCLUDE,
                      help="exclude files or directories which match these "
                           "comma separated patterns (default: %default)")
    parser.add_option('--filename', metavar='patterns', default='*.py',
                      help="when parsing directories, only check filenames "
                           "matching these comma separated patterns "
                           "(default: %default)")
    parser.add_option('--select', metavar='errors', default='',
                      help="select errors and warnings (e.g. E,W6)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error "
                           "(implies --first)")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--count', action='store_true',
                      help="print total number of errors and warnings "
                           "to standard error and set exit code to 1 if "
                           "total is not null")
    parser.add_option('--max-line-length', type='int', metavar='n',
                      default=MAX_LINE_LENGTH,
                      help="set maximum allowed line length "
                           "(default: %default)")
    parser.add_option('--hang-closing', action='store_true',
                      help="hang closing bracket instead of matching "
                           "indentation of opening bracket's line")
    parser.add_option('--format', metavar='format', default='default',
                      help="set the error format [default|pylint|<custom>]")
    parser.add_option('--diff', action='store_true',
                      help="report only lines changed according to the "
                           "unified diff received on STDIN")
    group = parser.add_option_group("Testing Options")
    if os.path.exists(TESTSUITE_PATH):
        group.add_option('--testsuite', metavar='dir',
                         help="run regression tests from dir")
        group.add_option('--doctest', action='store_true',
                         help="run doctest on myself")
    group.add_option('--benchmark', action='store_true',
                     help="measure processing speed")
    return parser


def read_config(options, args, arglist, parser):
    """Read both user configuration and local configuration."""
    config = RawConfigParser()

    user_conf = options.config
    if user_conf and os.path.isfile(user_conf):
        if options.verbose:
            print('user configuration: %s' % user_conf)
        config.read(user_conf)

    local_dir = os.curdir
    parent = tail = args and os.path.abspath(os.path.commonprefix(args))
    while tail:
        if config.read([os.path.join(parent, fn) for fn in PROJECT_CONFIG]):
            local_dir = parent
            if options.verbose:
                print('local configuration: in %s' % parent)
            break
        (parent, tail) = os.path.split(parent)

    pep8_section = parser.prog
    if config.has_section(pep8_section):
        option_list = dict([(o.dest, o.type or o.action)
                            for o in parser.option_list])

        # First, read the default values
        (new_options, __) = parser.parse_args([])

        # Second, parse the configuration
        for opt in config.options(pep8_section):
            if opt.replace('_', '-') not in parser.config_options:
                print("  unknown option '%s' ignored" % opt)
                continue
            if options.verbose > 1:
                print("  %s = %s" % (opt, config.get(pep8_section, opt)))
            normalized_opt = opt.replace('-', '_')
            opt_type = option_list[normalized_opt]
            if opt_type in ('int', 'count'):
                value = config.getint(pep8_section, opt)
            elif opt_type == 'string':
                value = config.get(pep8_section, opt)
                if normalized_opt == 'exclude':
                    value = normalize_paths(value, local_dir)
            else:
                assert opt_type in ('store_true', 'store_false')
                value = config.getboolean(pep8_section, opt)
            setattr(new_options, normalized_opt, value)

        # Third, overwrite with the command-line options
        (options, __) = parser.parse_args(arglist, values=new_options)
    options.doctest = options.testsuite = False
    return options


def process_options(arglist=None, parse_argv=False, config_file=None,
                    parser=None):
    """Process options passed either via arglist or via command line args."""
    if not parser:
        parser = get_parser()
    if not parser.has_option('--config'):
        if config_file is True:
            config_file = DEFAULT_CONFIG
        group = parser.add_option_group("Configuration", description=(
            "The project options are read from the [%s] section of the "
            "tox.ini file or the setup.cfg file located in any parent folder "
            "of the path(s) being processed.  Allowed options are: %s." %
            (parser.prog, ', '.join(parser.config_options))))
        group.add_option('--config', metavar='path', default=config_file,
                         help="user config file location (default: %default)")
    # Don't read the command line if the module is used as a library.
    if not arglist and not parse_argv:
        arglist = []
    # If parse_argv is True and arglist is None, arguments are
    # parsed from the command line (sys.argv)
    (options, args) = parser.parse_args(arglist)
    options.reporter = None

    if options.ensure_value('testsuite', False):
        args.append(options.testsuite)
    elif not options.ensure_value('doctest', False):
        if parse_argv and not args:
            if options.diff or any(os.path.exists(name)
                                   for name in PROJECT_CONFIG):
                args = ['.']
            else:
                parser.error('input not specified')
        options = read_config(options, args, arglist, parser)
        options.reporter = parse_argv and options.quiet == 1 and FileReport

    options.filename = options.filename and options.filename.split(',')
    options.exclude = normalize_paths(options.exclude)
    options.select = options.select and options.select.split(',')
    options.ignore = options.ignore and options.ignore.split(',')

    if options.diff:
        options.reporter = DiffReport
        stdin = stdin_get_value()
        options.selected_lines = parse_udiff(stdin, options.filename, args[0])
        args = sorted(options.selected_lines)

    return options, args


def _main():
    """Parse options and run checks on Python source."""
    import signal

    # Handle "Broken pipe" gracefully
    try:
        signal.signal(signal.SIGPIPE, lambda signum, frame: sys.exit(1))
    except AttributeError:
        pass    # not supported on Windows

    pep8style = StyleGuide(parse_argv=True, config_file=True)
    options = pep8style.options
    if options.doctest or options.testsuite:
        from testsuite.support import run_tests
        report = run_tests(pep8style)
    else:
        report = pep8style.check_files()
    if options.statistics:
        report.print_statistics()
    if options.benchmark:
        report.print_benchmark()
    if options.testsuite and not options.quiet:
        report.print_results()
    if report.total_errors:
        if options.count:
            sys.stderr.write(str(report.total_errors) + '\n')
        sys.exit(1)

if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = checker
"""
Main module.

Implement the central Checker class.
Also, it models the Bindings and Scopes.
"""
import doctest
import os
import sys

PY2 = sys.version_info < (3, 0)
PY32 = sys.version_info < (3, 3)    # Python 2.5 to 3.2
PY33 = sys.version_info < (3, 4)    # Python 2.5 to 3.3
builtin_vars = dir(__import__('__builtin__' if PY2 else 'builtins'))

try:
    import ast
except ImportError:     # Python 2.5
    import _ast as ast

    if 'decorator_list' not in ast.ClassDef._fields:
        # Patch the missing attribute 'decorator_list'
        ast.ClassDef.decorator_list = ()
        ast.FunctionDef.decorator_list = property(lambda s: s.decorators)

from pyflakes import messages


if PY2:
    def getNodeType(node_class):
        # workaround str.upper() which is locale-dependent
        return str(unicode(node_class.__name__).upper())
else:
    def getNodeType(node_class):
        return node_class.__name__.upper()

# Python >= 3.3 uses ast.Try instead of (ast.TryExcept + ast.TryFinally)
if PY32:
    def getAlternatives(n):
        if isinstance(n, (ast.If, ast.TryFinally)):
            return [n.body]
        if isinstance(n, ast.TryExcept):
            return [n.body + n.orelse] + [[hdl] for hdl in n.handlers]
else:
    def getAlternatives(n):
        if isinstance(n, ast.If):
            return [n.body]
        if isinstance(n, ast.Try):
            return [n.body + n.orelse] + [[hdl] for hdl in n.handlers]


class _FieldsOrder(dict):
    """Fix order of AST node fields."""

    def _get_fields(self, node_class):
        # handle iter before target, and generators before element
        fields = node_class._fields
        if 'iter' in fields:
            key_first = 'iter'.find
        elif 'generators' in fields:
            key_first = 'generators'.find
        else:
            key_first = 'value'.find
        return tuple(sorted(fields, key=key_first, reverse=True))

    def __missing__(self, node_class):
        self[node_class] = fields = self._get_fields(node_class)
        return fields


def iter_child_nodes(node, omit=None, _fields_order=_FieldsOrder()):
    """
    Yield all direct child nodes of *node*, that is, all fields that
    are nodes and all items of fields that are lists of nodes.
    """
    for name in _fields_order[node.__class__]:
        if name == omit:
            continue
        field = getattr(node, name, None)
        if isinstance(field, ast.AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                yield item


class Binding(object):
    """
    Represents the binding of a value to a name.

    The checker uses this to keep track of which names have been bound and
    which names have not. See L{Assignment} for a special type of binding that
    is checked with stricter rules.

    @ivar used: pair of (L{Scope}, line-number) indicating the scope and
                line number that this binding was last used
    """

    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s object %r from line %r at 0x%x>' % (self.__class__.__name__,
                                                        self.name,
                                                        self.source.lineno,
                                                        id(self))

    def redefines(self, other):
        return isinstance(other, Definition) and self.name == other.name


class Definition(Binding):
    """
    A binding that defines a function or a class.
    """


class Importation(Definition):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """

    def __init__(self, name, source):
        self.fullName = name
        self.redefined = []
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)

    def redefines(self, other):
        if isinstance(other, Importation):
            return self.fullName == other.fullName
        return isinstance(other, Definition) and self.name == other.name


class Argument(Binding):
    """
    Represents binding a name as an argument.
    """


class Assignment(Binding):
    """
    Represents binding a name with an explicit assignment.

    The checker will raise warnings for any Assignment that isn't used. Also,
    the checker does not consider assignments in tuple/list unpacking to be
    Assignments, rather it treats them as simple Bindings.
    """


class FunctionDefinition(Definition):
    pass


class ClassDefinition(Definition):
    pass


class ExportBinding(Binding):
    """
    A binding created by an C{__all__} assignment.  If the names in the list
    can be determined statically, they will be treated as names for export and
    additional checking applied to them.

    The only C{__all__} assignment that can be recognized is one which takes
    the value of a literal list containing literal strings.  For example::

        __all__ = ["foo", "bar"]

    Names which are imported and not otherwise used but appear in the value of
    C{__all__} will not have an unused import warning reported for them.
    """

    def __init__(self, name, source, scope):
        if '__all__' in scope and isinstance(source, ast.AugAssign):
            self.names = list(scope['__all__'].names)
        else:
            self.names = []
        if isinstance(source.value, (ast.List, ast.Tuple)):
            for node in source.value.elts:
                if isinstance(node, ast.Str):
                    self.names.append(node.s)
        super(ExportBinding, self).__init__(name, source)


class Scope(dict):
    importStarred = False       # set to True when import * is found

    def __repr__(self):
        scope_cls = self.__class__.__name__
        return '<%s at 0x%x %s>' % (scope_cls, id(self), dict.__repr__(self))


class ClassScope(Scope):
    pass


class FunctionScope(Scope):
    """
    I represent a name scope for a function.

    @ivar globals: Names declared 'global' in this function.
    """
    usesLocals = False
    alwaysUsed = set(['__tracebackhide__',
                      '__traceback_info__', '__traceback_supplement__'])

    def __init__(self):
        super(FunctionScope, self).__init__()
        # Simplify: manage the special locals as globals
        self.globals = self.alwaysUsed.copy()
        self.returnValue = None     # First non-empty return
        self.isGenerator = False    # Detect a generator

    def unusedAssignments(self):
        """
        Return a generator for the assignments which have not been used.
        """
        for name, binding in self.items():
            if (not binding.used and name not in self.globals
                    and not self.usesLocals
                    and isinstance(binding, Assignment)):
                yield name, binding


class GeneratorScope(Scope):
    pass


class ModuleScope(Scope):
    pass


# Globally defined names which are not attributes of the builtins module, or
# are only present on some platforms.
_MAGIC_GLOBALS = ['__file__', '__builtins__', 'WindowsError']


def getNodeName(node):
    # Returns node.id, or node.name, or None
    if hasattr(node, 'id'):     # One of the many nodes with an id
        return node.id
    if hasattr(node, 'name'):   # a ExceptHandler node
        return node.name


class Checker(object):
    """
    I check the cleanliness and sanity of Python code.

    @ivar _deferredFunctions: Tracking list used by L{deferFunction}.  Elements
        of the list are two-tuples.  The first element is the callable passed
        to L{deferFunction}.  The second element is a copy of the scope stack
        at the time L{deferFunction} was called.

    @ivar _deferredAssignments: Similar to C{_deferredFunctions}, but for
        callables which are deferred assignment checks.
    """

    nodeDepth = 0
    offset = None
    traceTree = False

    builtIns = set(builtin_vars).union(_MAGIC_GLOBALS)
    _customBuiltIns = os.environ.get('PYFLAKES_BUILTINS')
    if _customBuiltIns:
        builtIns.update(_customBuiltIns.split(','))
    del _customBuiltIns

    def __init__(self, tree, filename='(none)', builtins=None,
                 withDoctest='PYFLAKES_DOCTEST' in os.environ):
        self._nodeHandlers = {}
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.deadScopes = []
        self.messages = []
        self.filename = filename
        if builtins:
            self.builtIns = self.builtIns.union(builtins)
        self.withDoctest = withDoctest
        self.scopeStack = [ModuleScope()]
        self.exceptHandlers = [()]
        self.futuresAllowed = True
        self.root = tree
        self.handleChildren(tree)
        self.runDeferred(self._deferredFunctions)
        # Set _deferredFunctions to None so that deferFunction will fail
        # noisily if called after we've run through the deferred functions.
        self._deferredFunctions = None
        self.runDeferred(self._deferredAssignments)
        # Set _deferredAssignments to None so that deferAssignment will fail
        # noisily if called after we've run through the deferred assignments.
        self._deferredAssignments = None
        del self.scopeStack[1:]
        self.popScope()
        self.checkDeadScopes()

    def deferFunction(self, callable):
        """
        Schedule a function handler to be called just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        """
        self._deferredFunctions.append((callable, self.scopeStack[:], self.offset))

    def deferAssignment(self, callable):
        """
        Schedule an assignment handler to be called just after deferred
        function handlers.
        """
        self._deferredAssignments.append((callable, self.scopeStack[:], self.offset))

    def runDeferred(self, deferred):
        """
        Run the callables in C{deferred} using their associated scope stack.
        """
        for handler, scope, offset in deferred:
            self.scopeStack = scope
            self.offset = offset
            handler()

    @property
    def scope(self):
        return self.scopeStack[-1]

    def popScope(self):
        self.deadScopes.append(self.scopeStack.pop())

    def checkDeadScopes(self):
        """
        Look at scopes which have been fully examined and report names in them
        which were imported but unused.
        """
        for scope in self.deadScopes:
            if isinstance(scope.get('__all__'), ExportBinding):
                all_names = set(scope['__all__'].names)
                if not scope.importStarred and \
                   os.path.basename(self.filename) != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = all_names.difference(scope)
                    for name in undefined:
                        self.report(messages.UndefinedExport,
                                    scope['__all__'].source, name)
            else:
                all_names = []

            # Look for imported names that aren't used.
            for value in scope.values():
                if isinstance(value, Importation):
                    used = value.used or value.name in all_names
                    if not used:
                        messg = messages.UnusedImport
                        self.report(messg, value.source, value.name)
                    for node in value.redefined:
                        if isinstance(self.getParent(node), ast.For):
                            messg = messages.ImportShadowedByLoopVar
                        elif used:
                            continue
                        else:
                            messg = messages.RedefinedWhileUnused
                        self.report(messg, node, value.name, value.source)

    def pushScope(self, scopeClass=FunctionScope):
        self.scopeStack.append(scopeClass())

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def getParent(self, node):
        # Lookup the first parent which is not Tuple, List or Starred
        while True:
            node = node.parent
            if not hasattr(node, 'elts') and not hasattr(node, 'ctx'):
                return node

    def getCommonAncestor(self, lnode, rnode, stop):
        if stop in (lnode, rnode) or not (hasattr(lnode, 'parent') and
                                          hasattr(rnode, 'parent')):
            return None
        if lnode is rnode:
            return lnode

        if (lnode.depth > rnode.depth):
            return self.getCommonAncestor(lnode.parent, rnode, stop)
        if (lnode.depth < rnode.depth):
            return self.getCommonAncestor(lnode, rnode.parent, stop)
        return self.getCommonAncestor(lnode.parent, rnode.parent, stop)

    def descendantOf(self, node, ancestors, stop):
        for a in ancestors:
            if self.getCommonAncestor(node, a, stop):
                return True
        return False

    def differentForks(self, lnode, rnode):
        """True, if lnode and rnode are located on different forks of IF/TRY"""
        ancestor = self.getCommonAncestor(lnode, rnode, self.root)
        parts = getAlternatives(ancestor)
        if parts:
            for items in parts:
                if self.descendantOf(lnode, items, ancestor) ^ \
                   self.descendantOf(rnode, items, ancestor):
                    return True
        return False

    def addBinding(self, node, value):
        """
        Called when a binding is altered.

        - `node` is the statement responsible for the change
        - `value` is the new value, a Binding instance
        """
        # assert value.source in (node, node.parent):
        for scope in self.scopeStack[::-1]:
            if value.name in scope:
                break
        existing = scope.get(value.name)

        if existing and not self.differentForks(node, existing.source):

            parent_stmt = self.getParent(value.source)
            if isinstance(existing, Importation) and isinstance(parent_stmt, ast.For):
                self.report(messages.ImportShadowedByLoopVar,
                            node, value.name, existing.source)

            elif scope is self.scope:
                if (isinstance(parent_stmt, ast.comprehension) and
                        not isinstance(self.getParent(existing.source),
                                       (ast.For, ast.comprehension))):
                    self.report(messages.RedefinedInListComp,
                                node, value.name, existing.source)
                elif not existing.used and value.redefines(existing):
                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, existing.source)

            elif isinstance(existing, Importation) and value.redefines(existing):
                existing.redefined.append(node)

        self.scope[value.name] = value

    def getNodeHandler(self, node_class):
        try:
            return self._nodeHandlers[node_class]
        except KeyError:
            nodeType = getNodeType(node_class)
        self._nodeHandlers[node_class] = handler = getattr(self, nodeType)
        return handler

    def handleNodeLoad(self, node):
        name = getNodeName(node)
        if not name:
            return
        # try local scope
        try:
            self.scope[name].used = (self.scope, node)
        except KeyError:
            pass
        else:
            return

        scopes = [scope for scope in self.scopeStack[:-1]
                  if isinstance(scope, (FunctionScope, ModuleScope))]
        if isinstance(self.scope, GeneratorScope) and scopes[-1] != self.scopeStack[-2]:
            scopes.append(self.scopeStack[-2])

        # try enclosing function scopes and global scope
        importStarred = self.scope.importStarred
        for scope in reversed(scopes):
            importStarred = importStarred or scope.importStarred
            try:
                scope[name].used = (self.scope, node)
            except KeyError:
                pass
            else:
                return

        # look in the built-ins
        if importStarred or name in self.builtIns:
            return
        if name == '__path__' and os.path.basename(self.filename) == '__init__.py':
            # the special name __path__ is valid only in packages
            return

        # protected with a NameError handler?
        if 'NameError' not in self.exceptHandlers[-1]:
            self.report(messages.UndefinedName, node, name)

    def handleNodeStore(self, node):
        name = getNodeName(node)
        if not name:
            return
        # if the name hasn't already been defined in the current scope
        if isinstance(self.scope, FunctionScope) and name not in self.scope:
            # for each function or module scope above us
            for scope in self.scopeStack[:-1]:
                if not isinstance(scope, (FunctionScope, ModuleScope)):
                    continue
                # if the name was defined in that scope, and the name has
                # been accessed already in the current scope, and hasn't
                # been declared global
                used = name in scope and scope[name].used
                if used and used[0] is self.scope and name not in self.scope.globals:
                    # then it's probably a mistake
                    self.report(messages.UndefinedLocal,
                                scope[name].used[1], name, scope[name].source)
                    break

        parent_stmt = self.getParent(node)
        if isinstance(parent_stmt, (ast.For, ast.comprehension)) or (
                parent_stmt != node.parent and
                not self.isLiteralTupleUnpacking(parent_stmt)):
            binding = Binding(name, node)
        elif name == '__all__' and isinstance(self.scope, ModuleScope):
            binding = ExportBinding(name, node.parent, self.scope)
        else:
            binding = Assignment(name, node)
        if name in self.scope:
            binding.used = self.scope[name].used
        self.addBinding(node, binding)

    def handleNodeDelete(self, node):
        name = getNodeName(node)
        if not name:
            return
        if isinstance(self.scope, FunctionScope) and name in self.scope.globals:
            self.scope.globals.remove(name)
        else:
            try:
                del self.scope[name]
            except KeyError:
                self.report(messages.UndefinedName, node, name)

    def handleChildren(self, tree, omit=None):
        for node in iter_child_nodes(tree, omit=omit):
            self.handleNode(node, tree)

    def isLiteralTupleUnpacking(self, node):
        if isinstance(node, ast.Assign):
            for child in node.targets + [node.value]:
                if not hasattr(child, 'elts'):
                    return False
            return True

    def isDocstring(self, node):
        """
        Determine if the given node is a docstring, as long as it is at the
        correct place in the node tree.
        """
        return isinstance(node, ast.Str) or (isinstance(node, ast.Expr) and
                                             isinstance(node.value, ast.Str))

    def getDocstring(self, node):
        if isinstance(node, ast.Expr):
            node = node.value
        if not isinstance(node, ast.Str):
            return (None, None)
        # Computed incorrectly if the docstring has backslash
        doctest_lineno = node.lineno - node.s.count('\n') - 1
        return (node.s, doctest_lineno)

    def handleNode(self, node, parent):
        if node is None:
            return
        if self.offset and getattr(node, 'lineno', None) is not None:
            node.lineno += self.offset[0]
            node.col_offset += self.offset[1]
        if self.traceTree:
            print('  ' * self.nodeDepth + node.__class__.__name__)
        if self.futuresAllowed and not (isinstance(node, ast.ImportFrom) or
                                        self.isDocstring(node)):
            self.futuresAllowed = False
        self.nodeDepth += 1
        node.depth = self.nodeDepth
        node.parent = parent
        try:
            handler = self.getNodeHandler(node.__class__)
            handler(node)
        finally:
            self.nodeDepth -= 1
        if self.traceTree:
            print('  ' * self.nodeDepth + 'end ' + node.__class__.__name__)

    _getDoctestExamples = doctest.DocTestParser().get_examples

    def handleDoctests(self, node):
        try:
            (docstring, node_lineno) = self.getDocstring(node.body[0])
            examples = docstring and self._getDoctestExamples(docstring)
        except (ValueError, IndexError):
            # e.g. line 6 of the docstring for <string> has inconsistent
            # leading whitespace: ...
            return
        if not examples:
            return
        node_offset = self.offset or (0, 0)
        self.pushScope()
        underscore_in_builtins = '_' in self.builtIns
        if not underscore_in_builtins:
            self.builtIns.add('_')
        for example in examples:
            try:
                tree = compile(example.source, "<doctest>", "exec", ast.PyCF_ONLY_AST)
            except SyntaxError:
                e = sys.exc_info()[1]
                position = (node_lineno + example.lineno + e.lineno,
                            example.indent + 4 + (e.offset or 0))
                self.report(messages.DoctestSyntaxError, node, position)
            else:
                self.offset = (node_offset[0] + node_lineno + example.lineno,
                               node_offset[1] + example.indent + 4)
                self.handleChildren(tree)
                self.offset = node_offset
        if not underscore_in_builtins:
            self.builtIns.remove('_')
        self.popScope()

    def ignore(self, node):
        pass

    # "stmt" type nodes
    DELETE = PRINT = FOR = WHILE = IF = WITH = WITHITEM = RAISE = \
        TRYFINALLY = ASSERT = EXEC = EXPR = ASSIGN = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = BINOP = UNARYOP = IFEXP = DICT = SET = \
        COMPARE = CALL = REPR = ATTRIBUTE = SUBSCRIPT = LIST = TUPLE = \
        STARRED = NAMECONSTANT = handleChildren

    NUM = STR = BYTES = ELLIPSIS = ignore

    # "slice" type nodes
    SLICE = EXTSLICE = INDEX = handleChildren

    # expression contexts are node instances too, though being constants
    LOAD = STORE = DEL = AUGLOAD = AUGSTORE = PARAM = ignore

    # same for operators
    AND = OR = ADD = SUB = MULT = DIV = MOD = POW = LSHIFT = RSHIFT = \
        BITOR = BITXOR = BITAND = FLOORDIV = INVERT = NOT = UADD = USUB = \
        EQ = NOTEQ = LT = LTE = GT = GTE = IS = ISNOT = IN = NOTIN = ignore

    # additional node types
    LISTCOMP = COMPREHENSION = KEYWORD = handleChildren

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(node.names)

    NONLOCAL = GLOBAL

    def GENERATOREXP(self, node):
        self.pushScope(GeneratorScope)
        self.handleChildren(node)
        self.popScope()

    DICTCOMP = SETCOMP = GENERATOREXP

    def NAME(self, node):
        """
        Handle occurrence of Name (which can be a load/store/delete access.)
        """
        # Locate the name in locals / function / globals scopes.
        if isinstance(node.ctx, (ast.Load, ast.AugLoad)):
            self.handleNodeLoad(node)
            if (node.id == 'locals' and isinstance(self.scope, FunctionScope)
                    and isinstance(node.parent, ast.Call)):
                # we are doing locals() call in current scope
                self.scope.usesLocals = True
        elif isinstance(node.ctx, (ast.Store, ast.AugStore)):
            self.handleNodeStore(node)
        elif isinstance(node.ctx, ast.Del):
            self.handleNodeDelete(node)
        else:
            # must be a Param context -- this only happens for names in function
            # arguments, but these aren't dispatched through here
            raise RuntimeError("Got impossible expression context: %r" % (node.ctx,))

    def RETURN(self, node):
        if (
            node.value and
            hasattr(self.scope, 'returnValue') and
            not self.scope.returnValue
        ):
            self.scope.returnValue = node.value
        self.handleNode(node.value, node)

    def YIELD(self, node):
        self.scope.isGenerator = True
        self.handleNode(node.value, node)

    YIELDFROM = YIELD

    def FUNCTIONDEF(self, node):
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        self.LAMBDA(node)
        self.addBinding(node, FunctionDefinition(node.name, node))
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))

    def LAMBDA(self, node):
        args = []
        annotations = []

        if PY2:
            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        args.append(arg.id)
            addArgs(node.args.args)
            defaults = node.args.defaults
        else:
            for arg in node.args.args + node.args.kwonlyargs:
                args.append(arg.arg)
                annotations.append(arg.annotation)
            defaults = node.args.defaults + node.args.kw_defaults

        # Only for Python3 FunctionDefs
        is_py3_func = hasattr(node, 'returns')

        for arg_name in ('vararg', 'kwarg'):
            wildcard = getattr(node.args, arg_name)
            if not wildcard:
                continue
            args.append(wildcard if PY33 else wildcard.arg)
            if is_py3_func:
                if PY33:  # Python 2.5 to 3.3
                    argannotation = arg_name + 'annotation'
                    annotations.append(getattr(node.args, argannotation))
                else:     # Python >= 3.4
                    annotations.append(wildcard.annotation)

        if is_py3_func:
            annotations.append(node.returns)

        if len(set(args)) < len(args):
            for (idx, arg) in enumerate(args):
                if arg in args[:idx]:
                    self.report(messages.DuplicateArgument, node, arg)

        for child in annotations + defaults:
            if child:
                self.handleNode(child, node)

        def runFunction():

            self.pushScope()
            for name in args:
                self.addBinding(node, Argument(name, node))
            if isinstance(node.body, list):
                # case for FunctionDefs
                for stmt in node.body:
                    self.handleNode(stmt, node)
            else:
                # case for Lambdas
                self.handleNode(node.body, node)

            def checkUnusedAssignments():
                """
                Check to see if any assignments have not been used.
                """
                for name, binding in self.scope.unusedAssignments():
                    self.report(messages.UnusedVariable, binding.source, name)
            self.deferAssignment(checkUnusedAssignments)

            if PY32:
                def checkReturnWithArgumentInsideGenerator():
                    """
                    Check to see if there is any return statement with
                    arguments but the function is a generator.
                    """
                    if self.scope.isGenerator and self.scope.returnValue:
                        self.report(messages.ReturnWithArgsInsideGenerator,
                                    self.scope.returnValue)
                self.deferAssignment(checkReturnWithArgumentInsideGenerator)
            self.popScope()

        self.deferFunction(runFunction)

    def CLASSDEF(self, node):
        """
        Check names used in a class definition, including its decorators, base
        classes, and the body of its definition.  Additionally, add its name to
        the current scope.
        """
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        for baseNode in node.bases:
            self.handleNode(baseNode, node)
        if not PY2:
            for keywordNode in node.keywords:
                self.handleNode(keywordNode, node)
        self.pushScope(ClassScope)
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))
        for stmt in node.body:
            self.handleNode(stmt, node)
        self.popScope()
        self.addBinding(node, ClassDefinition(node.name, node))

    def AUGASSIGN(self, node):
        self.handleNodeLoad(node.target)
        self.handleNode(node.value, node)
        self.handleNode(node.target, node)

    def IMPORT(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            importation = Importation(name, node)
            self.addBinding(node, importation)

    def IMPORTFROM(self, node):
        if node.module == '__future__':
            if not self.futuresAllowed:
                self.report(messages.LateFutureImport,
                            node, [n.name for n in node.names])
        else:
            self.futuresAllowed = False

        for alias in node.names:
            if alias.name == '*':
                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node, node.module)
                continue
            name = alias.asname or alias.name
            importation = Importation(name, node)
            if node.module == '__future__':
                importation.used = (self.scope, node)
            self.addBinding(node, importation)

    def TRY(self, node):
        handler_names = []
        # List the exception handlers
        for handler in node.handlers:
            if isinstance(handler.type, ast.Tuple):
                for exc_type in handler.type.elts:
                    handler_names.append(getNodeName(exc_type))
            elif handler.type:
                handler_names.append(getNodeName(handler.type))
        # Memorize the except handlers and process the body
        self.exceptHandlers.append(handler_names)
        for child in node.body:
            self.handleNode(child, node)
        self.exceptHandlers.pop()
        # Process the other nodes: "except:", "else:", "finally:"
        self.handleChildren(node, omit='body')

    TRYEXCEPT = TRY

    def EXCEPTHANDLER(self, node):
        # 3.x: in addition to handling children, we must handle the name of
        # the exception, which is not a Name node, but a simple string.
        if isinstance(node.name, str):
            self.handleNodeStore(node)
        self.handleChildren(node)

########NEW FILE########
__FILENAME__ = messages
"""
Provide the class Message and its subclasses.
"""


class Message(object):
    message = ''
    message_args = ()

    def __init__(self, filename, loc):
        self.filename = filename
        self.lineno = loc.lineno
        self.col = getattr(loc, 'col_offset', 0)

    def __str__(self):
        return '%s:%s: %s' % (self.filename, self.lineno,
                              self.message % self.message_args)


class UnusedImport(Message):
    message = '%r imported but unused'

    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)


class RedefinedWhileUnused(Message):
    message = 'redefinition of unused %r from line %r'

    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class RedefinedInListComp(Message):
    message = 'list comprehension redefines %r from line %r'

    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class ImportShadowedByLoopVar(Message):
    message = 'import %r from line %r shadowed by loop variable'

    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class ImportStarUsed(Message):
    message = "'from %s import *' used; unable to detect undefined names"

    def __init__(self, filename, loc, modname):
        Message.__init__(self, filename, loc)
        self.message_args = (modname,)


class UndefinedName(Message):
    message = 'undefined name %r'

    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)


class DoctestSyntaxError(Message):
    message = 'syntax error in doctest'

    def __init__(self, filename, loc, position=None):
        Message.__init__(self, filename, loc)
        if position:
            (self.lineno, self.col) = position
        self.message_args = ()


class UndefinedExport(Message):
    message = 'undefined name %r in __all__'

    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)


class UndefinedLocal(Message):
    message = ('local variable %r (defined in enclosing scope on line %r) '
               'referenced before assignment')

    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class DuplicateArgument(Message):
    message = 'duplicate argument %r in function definition'

    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)


class Redefined(Message):
    message = 'redefinition of %r from line %r'

    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class LateFutureImport(Message):
    message = 'future import(s) %r after other statements'

    def __init__(self, filename, loc, names):
        Message.__init__(self, filename, loc)
        self.message_args = (names,)


class UnusedVariable(Message):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """
    message = 'local variable %r is assigned to but never used'

    def __init__(self, filename, loc, names):
        Message.__init__(self, filename, loc)
        self.message_args = (names,)


class ReturnWithArgsInsideGenerator(Message):
    """
    Indicates a return statement with arguments inside a generator.
    """
    message = '\'return\' with argument inside generator'

########NEW FILE########
__FILENAME__ = main
""" Pylama's shell support. """
from __future__ import absolute_import, with_statement

import sys
from os import walk, path as op

from .config import parse_options, CURDIR, setup_logger
from .core import LOGGER


def shell(args=None, error=True):
    """ Endpoint for console.

    Parse a command arguments, configuration files and run a checkers.

    :return list: list of errors
    :raise SystemExit:

    """
    if args is None:
        args = sys.argv[1:]

    options = parse_options(args)
    setup_logger(options)
    LOGGER.info(options)

    # Install VSC hook
    if options.hook:
        from .hook import install_hook
        return install_hook(options.path)

    paths = [options.path]

    if op.isdir(options.path):
        paths = []
        for root, _, files in walk(options.path):
            paths += [op.relpath(op.join(root, f), CURDIR) for f in files]

    return check_files(paths, options, error=error)


def check_files(paths, options, rootpath=None, error=True):
    """ Check files.

    :return list: list of errors
    :raise SystemExit:

    """
    from .tasks import async_check_files

    if rootpath is None:
        rootpath = CURDIR

    pattern = "%(rel)s:%(lnum)s:%(col)s: %(text)s"
    if options.format == 'pylint':
        pattern = "%(rel)s:%(lnum)s: [%(type)s] %(text)s"

    work_paths = []
    for path in paths:

        if not any(l.allow(path) for _, l in options.linters):
            continue

        if not op.exists(path):
            continue

        if options.skip and any(p.match(path) for p in options.skip):
            LOGGER.info('Skip path: %s', path)
            continue
        work_paths.append(path)

    errors = async_check_files(work_paths, options, rootpath=rootpath)

    for er in errors:
        LOGGER.warning(pattern, er)

    if error:
        sys.exit(int(bool(errors)))

    return errors


if __name__ == '__main__':
    shell()

########NEW FILE########
__FILENAME__ = tasks
""" Async code checking. """
import logging
import threading
from os import path as op
try:
    import Queue
except ImportError:
    import queue as Queue

from .core import run


try:
    import multiprocessing

    CPU_COUNT = multiprocessing.cpu_count()

except (ImportError, NotImplementedError):
    CPU_COUNT = 1

LOGGER = logging.getLogger('pylama')


class Worker(threading.Thread):

    """ Get tasks from queue and run. """

    def __init__(self, path_queue, result_queue):
        """ Init worker. """
        threading.Thread.__init__(self)
        self.path_queue = path_queue
        self.result_queue = result_queue

    def run(self):
        """ Run tasks from queue. """
        while True:
            path, params = self.path_queue.get()
            errors = check_path(path, **params)
            self.result_queue.put(errors)
            self.path_queue.task_done()


def async_check_files(paths, options, rootpath=None):
    """ Check paths.

    :return list: list of errors

    """
    errors = []

    # Disable async if pylint enabled
    async = options.async and 'pylint' not in options.linters

    if not async:
        for path in paths:
            errors += check_path(path, options=options, rootpath=rootpath)
        return errors

    LOGGER.info('Async code checking is enabled.')
    path_queue = Queue.Queue()
    result_queue = Queue.Queue()

    for _ in range(CPU_COUNT):
        worker = Worker(path_queue, result_queue)
        worker.setDaemon(True)
        worker.start()

    for path in paths:
        path_queue.put((path, dict(options=options, rootpath=rootpath)))

    path_queue.join()

    while True:
        try:
            errors += result_queue.get(False)
        except Queue.Empty:
            break

    return errors


def check_path(path, options=None, rootpath=None, code=None, **meta):
    """ Check path.

    :return list: list of errors

    """
    LOGGER.info("Parse file: %s", path)

    rootpath = rootpath or '.'
    errors = []
    for error in run(path, code, options):
        try:
            error['rel'] = op.relpath(error['filename'], rootpath)
            error['col'] = error.get('col', 1)
            errors.append(error)
        except KeyError:
            continue
    return errors

########NEW FILE########
__FILENAME__ = tests
import pytest

from pylama.config import parse_options, get_config
from pylama.core import filter_errors, parse_modeline, prepare_params, run
from pylama.hook import git_hook, hg_hook
from pylama.lint.extensions import LINTERS
from pylama.main import shell, check_files
from pylama.tasks import check_path, async_check_files


def test_filters():

    assert filter_errors(dict(text='E'), select=['E'], ignore=['E101'])
    assert not filter_errors(dict(text='W'), select=['W100'], ignore=['W'])


def test_modeline():

    code = """
        bla bla bla

        # pylama: ignore=W12,E14:select=R:skip=0
    """

    params = parse_modeline(code)
    assert params == dict(ignore='W12,E14', select='R', skip='0')


def test_prepare_params():

    p1 = dict(ignore='W', select='R01', skip='0')
    p2 = dict(ignore='E34,R45', select='E')
    options = parse_options(ignore=['D'], config=False)
    params = prepare_params(p1, p2, options)
    assert params == {
        'ignore': set(['R45', 'E34', 'W', 'D']), 'select': set(['R01', 'E']),
        'skip': False}


def test_mccabe():
    mccabe = LINTERS.get('mccabe')
    errors = mccabe.run('dummy.py', '')
    assert errors == []


def test_pyflakes():
    options = parse_options(linters=['pyflakes'], config=False)
    assert options.linters
    errors = run('dummy.py', code="""
import sys

def test():
    unused = 1
""", options=options)
    assert len(errors) == 2


def test_pep8():
    options = parse_options(linters=['pep8'], config=False)
    errors = run('dummy.py', options=options)
    assert len(errors) == 3

    options.linter_params['pep8'] = dict(max_line_length=60)
    errors = run('dummy.py', options=options)
    assert len(errors) == 11


def test_pep257():
    options = parse_options(linters=['pep257'])
    errors = run('dummy.py', options=options)
    assert errors


def test_linters_params():
    options = parse_options(linters='mccabe', config=False)
    options.linter_params['mccabe'] = dict(complexity=2)
    errors = run('dummy.py', options=options)
    assert len(errors) == 13

    options.linter_params['mccabe'] = dict(complexity=20)
    errors = run('dummy.py', options=options)
    assert not errors


def test_ignore_select():
    options = parse_options()
    options.ignore = ['E301', 'D102']
    errors = run('dummy.py', options=options)
    assert len(errors) == 17

    options.ignore = ['E3', 'D']
    errors = run('dummy.py', options=options)
    assert len(errors) == 2

    options.ignore = ['E3', 'D']
    options.select = ['E301']
    errors = run('dummy.py', options=options)
    assert len(errors) == 3
    assert errors[0]['col']


def test_checkpath():
    options = parse_options(linters=['pep8'])
    errors = check_path('dummy.py', options)
    assert errors
    assert errors[0]['rel'] == 'dummy.py'


def test_async():
    options = parse_options(async=True, linters=['pep8'])
    errors = async_check_files(['dummy.py'], options)
    assert errors


def test_shell():
    errors = shell('-o dummy dummy.py'.split(), error=False)
    assert errors

    options = parse_options()
    errors = check_files(['dummy.py'], options=options, error=False)
    assert errors

    errors = shell(['unknown.py'], error=False)
    assert not errors


def test_git_hook():
    with pytest.raises(SystemExit):
        git_hook()


def test_hg_hook():
    with pytest.raises(SystemExit):
        hg_hook(None, dict())


def test_config():
    config = get_config()
    assert config

    options = parse_options()
    assert options
    assert options.skip
    assert not options.verbose
    assert options.path == 'pylama'

    options = parse_options(['-l', 'pep257,pep8', '-i', 'E'])
    linters, _ = zip(*options.linters)
    assert set(linters) == set(['pep257', 'pep8'])
    assert options.ignore == ['E']

    options = parse_options('-o dummy dummy.py'.split())
    linters, _ = zip(*options.linters)
    assert set(linters) == set(['pep8', 'mccabe', 'pyflakes'])
    assert options.skip == []

########NEW FILE########
