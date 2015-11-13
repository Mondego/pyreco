__FILENAME__ = engine
# -*- coding: utf-8 -*-
import re
import platform

import pep8

from flake8 import __version__
from flake8.util import OrderedSet

_flake8_noqa = re.compile(r'flake8[:=]\s*noqa', re.I).search


def _register_extensions():
    """Register all the extensions."""
    extensions = OrderedSet()
    extensions.add(('pep8', pep8.__version__))
    parser_hooks = []
    options_hooks = []
    try:
        from pkg_resources import iter_entry_points
    except ImportError:
        pass
    else:
        for entry in iter_entry_points('flake8.extension'):
            checker = entry.load()
            pep8.register_check(checker, codes=[entry.name])
            extensions.add((checker.name, checker.version))
            if hasattr(checker, 'add_options'):
                parser_hooks.append(checker.add_options)
            if hasattr(checker, 'parse_options'):
                options_hooks.append(checker.parse_options)
    return extensions, parser_hooks, options_hooks


def get_parser():
    """This returns an instance of optparse.OptionParser with all the
    extensions registered and options set. This wraps ``pep8.get_parser``.
    """
    (extensions, parser_hooks, options_hooks) = _register_extensions()
    details = ', '.join(['%s: %s' % ext for ext in extensions])
    python_version = get_python_version()
    parser = pep8.get_parser('flake8', '%s (%s) %s' % (
        __version__, details, python_version
    ))
    for opt in ('--repeat', '--testsuite', '--doctest'):
        try:
            parser.remove_option(opt)
        except ValueError:
            pass
    parser.add_option('--exit-zero', action='store_true',
                      help="exit with code 0 even if there are errors")
    for parser_hook in parser_hooks:
        parser_hook(parser)
    parser.add_option('--install-hook', default=False, action='store_true',
                      help='Install the appropriate hook for this '
                      'repository.', dest='install_hook')
    return parser, options_hooks


class StyleGuide(pep8.StyleGuide):
    # Backward compatibility pep8 <= 1.4.2
    checker_class = pep8.Checker

    def input_file(self, filename, lines=None, expected=None, line_offset=0):
        """Run all checks on a Python source file."""
        if self.options.verbose:
            print('checking %s' % filename)
        fchecker = self.checker_class(
            filename, lines=lines, options=self.options)
        # Any "# flake8: noqa" line?
        if any(_flake8_noqa(line) for line in fchecker.lines):
            return 0
        return fchecker.check_all(expected=expected, line_offset=line_offset)


def get_style_guide(**kwargs):
    """Parse the options and configure the checker. This returns a sub-class 
    of ``pep8.StyleGuide``."""
    kwargs['parser'], options_hooks = get_parser()
    styleguide = StyleGuide(**kwargs)
    options = styleguide.options
    for options_hook in options_hooks:
        options_hook(options)
    return styleguide


def get_python_version():
    # The implementation isn't all that important.
    try:
        impl = platform.python_implementation() + " "
    except AttributeError:  # Python 2.5
        impl = ''
    return '%s%s on %s' % (impl, platform.python_version(), platform.system())

########NEW FILE########
__FILENAME__ = hooks
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import sys
import stat
from subprocess import Popen, PIPE
import shutil
from tempfile import mkdtemp
try:
    # The 'demandimport' breaks pyflakes and flake8._pyflakes
    from mercurial import demandimport
    demandimport.disable()
except ImportError:
    pass
try:
    from configparser import ConfigParser
except ImportError:   # Python 2
    from ConfigParser import ConfigParser

from flake8.engine import get_parser, get_style_guide
from flake8.main import DEFAULT_CONFIG


def git_hook(complexity=-1, strict=False, ignore=None, lazy=False):
    """This is the function used by the git hook.

    :param int complexity: (optional), any value > 0 enables complexity
        checking with mccabe
    :param bool strict: (optional), if True, this returns the total number of
        errors which will cause the hook to fail
    :param str ignore: (optional), a comma-separated list of errors and
        warnings to ignore
    :param bool lazy: (optional), allows for the instances where you don't add
        the files to the index before running a commit, e.g., git commit -a
    :returns: total number of errors if strict is True, otherwise 0
    """
    gitcmd = "git diff-index --cached --name-only --diff-filter=ACMRTUXB HEAD"
    if lazy:
        # Catch all files, including those not added to the index
        gitcmd = gitcmd.replace('--cached ', '')

    if hasattr(ignore, 'split'):
        ignore = ignore.split(',')

    # Returns the exit code, list of files modified, list of error messages
    _, files_modified, _ = run(gitcmd)

    # We only want to pass ignore and max_complexity if they differ from the
    # defaults so that we don't override a local configuration file
    options = {}
    if ignore:
        options['ignore'] = ignore
    if complexity > -1:
        options['max_complexity'] = complexity

    files_modified = [f for f in files_modified if f.endswith('.py')]

    flake8_style = get_style_guide(
        parse_argv=True,
        config_file=DEFAULT_CONFIG,
        **options
        )

    # Copy staged versions to temporary directory
    tmpdir = mkdtemp()
    files_to_check = []
    try:
        for file_ in files_modified:
            # get the staged version of the file
            gitcmd_getstaged = "git show :%s" % file_
            _, out, _ = run(gitcmd_getstaged, raw_output=True, decode=False)
            # write the staged version to temp dir with its full path to
            # avoid overwriting files with the same name
            dirname, filename = os.path.split(os.path.abspath(file_))
            prefix = os.path.commonprefix([dirname, tmpdir])
            dirname = os.path.relpath(dirname, start=prefix)
            dirname = os.path.join(tmpdir, dirname)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            filename = os.path.join(dirname, filename)
            # write staged version of file to temporary directory
            with open(filename, "wb") as fh:
                fh.write(out)
            files_to_check.append(filename)
        # Run the checks
        report = flake8_style.check_files(files_to_check)
    # remove temporary directory
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if strict:
        return report.total_errors

    return 0


def hg_hook(ui, repo, **kwargs):
    """This is the function executed directly by Mercurial as part of the
    hook. This is never called directly by the user, so the parameters are
    undocumented. If you would like to learn more about them, please feel free
    to read the official Mercurial documentation.
    """
    complexity = ui.config('flake8', 'complexity', default=-1)
    strict = ui.configbool('flake8', 'strict', default=True)
    ignore = ui.config('flake8', 'ignore', default=None)
    config = ui.config('flake8', 'config', default=True)
    if config is True:
        config = DEFAULT_CONFIG

    paths = _get_files(repo, **kwargs)

    # We only want to pass ignore and max_complexity if they differ from the
    # defaults so that we don't override a local configuration file
    options = {}
    if ignore:
        options['ignore'] = ignore
    if complexity > -1:
        options['max_complexity'] = complexity

    flake8_style = get_style_guide(parse_argv=True, config_file=config,
                                   **options)
    report = flake8_style.check_files(paths)

    if strict:
        return report.total_errors

    return 0


def run(command, raw_output=False, decode=True):
    p = Popen(command.split(), stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p.communicate()
    # On python 3, subprocess.Popen returns bytes objects which expect
    # endswith to be given a bytes object or a tuple of bytes but not native
    # string objects. This is simply less mysterious than using b'.py' in the
    # endswith method. That should work but might still fail horribly.
    if hasattr(stdout, 'decode'):
        if decode:
            stdout = stdout.decode()
    if hasattr(stderr, 'decode'):
        if decode:
            stderr = stderr.decode()
    if not raw_output:
        stdout = [line.strip() for line in stdout.splitlines()]
        stderr = [line.strip() for line in stderr.splitlines()]
    return (p.returncode, stdout, stderr)


def _get_files(repo, **kwargs):
    seen = set()
    for rev in range(repo[kwargs['node']], len(repo)):
        for file_ in repo[rev].files():
            file_ = os.path.join(repo.root, file_)
            if file_ in seen or not os.path.exists(file_):
                continue
            seen.add(file_)
            if file_.endswith('.py'):
                yield file_


def find_vcs():
    _, git_dir, _ = run('git rev-parse --git-dir')
    if git_dir and os.path.isdir(git_dir[0]):
        if not os.path.isdir(os.path.join(git_dir[0], 'hooks')):
            os.mkdir(os.path.join(git_dir[0], 'hooks'))
        return os.path.join(git_dir[0], 'hooks', 'pre-commit')
    _, hg_dir, _ = run('hg root')
    if hg_dir and os.path.isdir(hg_dir[0]):
        return os.path.join(hg_dir[0], '.hg', 'hgrc')
    return ''


git_hook_file = """#!/usr/bin/env python
import sys
import os
from flake8.hooks import git_hook

COMPLEXITY = os.getenv('FLAKE8_COMPLEXITY', 10)
STRICT = os.getenv('FLAKE8_STRICT', False)
IGNORE = os.getenv('FLAKE8_IGNORE')
LAZY = os.getenv('FLAKE8_LAZY', False)


if __name__ == '__main__':
    sys.exit(git_hook(
        complexity=COMPLEXITY,
        strict=STRICT,
        ignore=IGNORE,
        lazy=LAZY,
        ))
"""


def _install_hg_hook(path):
    if not os.path.isfile(path):
        # Make the file so we can avoid IOError's
        open(path, 'w+').close()

    c = ConfigParser()
    c.readfp(open(path, 'r'))
    if not c.has_section('hooks'):
        c.add_section('hooks')

    if not c.has_option('hooks', 'commit'):
        c.set('hooks', 'commit', 'python:flake8.hooks.hg_hook')

    if not c.has_option('hooks', 'qrefresh'):
        c.set('hooks', 'qrefresh', 'python:flake8.hooks.hg_hook')

    if not c.has_section('flake8'):
        c.add_section('flake8')

    if not c.has_option('flake8', 'complexity'):
        c.set('flake8', 'complexity', str(os.getenv('FLAKE8_COMPLEXITY', 10)))

    if not c.has_option('flake8', 'strict'):
        c.set('flake8', 'strict', os.getenv('FLAKE8_STRICT', False))

    if not c.has_option('flake8', 'ignore'):
        c.set('flake8', 'ignore', os.getenv('FLAKE8_IGNORE'))

    if not c.has_option('flake8', 'lazy'):
        c.set('flake8', 'lazy', os.getenv('FLAKE8_LAZY', False))

    c.write(open(path, 'w+'))


def install_hook():
    vcs = find_vcs()

    if not vcs:
        p = get_parser()[0]
        sys.stderr.write('Error: could not find either a git or mercurial '
                         'directory. Please re-run this in a proper '
                         'repository.')
        p.print_help()
        sys.exit(1)

    status = 0
    if 'git' in vcs:
        with open(vcs, 'w+') as fd:
            fd.write(git_hook_file)
        # rwxr--r--
        os.chmod(vcs, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    elif 'hg' in vcs:
        _install_hg_hook(vcs)
    else:
        status = 1

    sys.exit(status)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
import os
import sys

import setuptools

from flake8.engine import get_parser, get_style_guide
from flake8.util import is_flag, flag_on

if sys.platform.startswith('win'):
    DEFAULT_CONFIG = os.path.expanduser(r'~\.flake8')
else:
    DEFAULT_CONFIG = os.path.join(
        os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
        'flake8'
    )

EXTRA_IGNORE = ['.tox']


def main():
    """Parse options and run checks on Python source."""
    # Prepare
    flake8_style = get_style_guide(parse_argv=True, config_file=DEFAULT_CONFIG)
    options = flake8_style.options

    if options.install_hook:
        from flake8.hooks import install_hook
        install_hook()

    # Run the checkers
    report = flake8_style.check_files()

    exit_code = print_report(report, flake8_style)
    raise SystemExit(exit_code > 0)


def print_report(report, flake8_style):
    # Print the final report
    options = flake8_style.options
    if options.statistics:
        report.print_statistics()
    if options.benchmark:
        report.print_benchmark()
    if report.total_errors:
        if options.count:
            sys.stderr.write(str(report.total_errors) + '\n')
        if not options.exit_zero:
            return 1
    return 0


def check_file(path, ignore=(), complexity=-1):
    """Checks a file using pep8 and pyflakes by default and mccabe
    optionally.

    :param str path: path to the file to be checked
    :param tuple ignore: (optional), error and warning codes to be ignored
    :param int complexity: (optional), enables the mccabe check for values > 0
    """
    ignore = set(ignore).union(EXTRA_IGNORE)
    flake8_style = get_style_guide(
        config_file=DEFAULT_CONFIG, ignore=ignore, max_complexity=complexity)
    return flake8_style.input_file(path)


def check_code(code, ignore=(), complexity=-1):
    """Checks code using pep8 and pyflakes by default and mccabe optionally.

    :param str code: code to be checked
    :param tuple ignore: (optional), error and warning codes to be ignored
    :param int complexity: (optional), enables the mccabe check for values > 0
    """
    ignore = set(ignore).union(EXTRA_IGNORE)
    flake8_style = get_style_guide(
        config_file=DEFAULT_CONFIG, ignore=ignore, max_complexity=complexity)
    return flake8_style.input_file(None, lines=code.splitlines(True))


class Flake8Command(setuptools.Command):
    """The :class:`Flake8Command` class is used by setuptools to perform
    checks on registered modules.
    """

    description = "Run flake8 on modules registered in setuptools"
    user_options = []

    def initialize_options(self):
        self.option_to_cmds = {}
        parser = get_parser()[0]
        for opt in parser.option_list:
            cmd_name = opt._long_opts[0][2:]
            option_name = cmd_name.replace('-', '_')
            self.option_to_cmds[option_name] = cmd_name
            setattr(self, option_name, None)

    def finalize_options(self):
        self.options_dict = {}
        for (option_name, cmd_name) in self.option_to_cmds.items():
            if option_name in ['help', 'verbose']:
                continue
            value = getattr(self, option_name)
            if value is None:
                continue
            if is_flag(value):
                value = flag_on(value)
            self.options_dict[option_name] = value

    def distribution_files(self):
        if self.distribution.packages:
            package_dirs = self.distribution.package_dir or {}
            for package in self.distribution.packages:
                pkg_dir = package
                if package in package_dirs:
                    pkg_dir = package_dirs[package]
                elif '' in package_dirs:
                    pkg_dir = package_dirs[''] + os.path.sep + pkg_dir
                yield pkg_dir.replace('.', os.path.sep)

        if self.distribution.py_modules:
            for filename in self.distribution.py_modules:
                yield "%s.py" % filename

    def run(self):
        flake8_style = get_style_guide(config_file=DEFAULT_CONFIG,
                                       **self.options_dict)
        paths = self.distribution_files()
        report = flake8_style.check_files(paths)
        exit_code = print_report(report, flake8_style)
        raise SystemExit(exit_code > 0)

########NEW FILE########
__FILENAME__ = run

"""
Implementation of the command-line I{flake8} tool.
"""
from flake8.hooks import git_hook, hg_hook                      # noqa
from flake8.main import check_code, check_file, Flake8Command   # noqa
from flake8.main import main


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_engine
from flake8 import engine, util, __version__
import pep8
import unittest
import mock


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.patches = {}

    def tearDown(self):
        assert len(self.patches.items()) == 0

    def start_patch(self, patch):
        self.patches[patch] = mock.patch(patch)
        return self.patches[patch].start()

    def stop_patches(self):
        patches = self.patches.copy()
        for k, v in patches.items():
            v.stop()
            del(self.patches[k])

    def test_get_style_guide(self):
        with mock.patch('flake8.engine._register_extensions') as reg_ext:
            reg_ext.return_value = ([], [], [])
            g = engine.get_style_guide()
            self.assertTrue(isinstance(g, engine.StyleGuide))
            reg_ext.assert_called_once_with()

    def test_get_style_guide_kwargs(self):
        m = mock.Mock()
        with mock.patch('flake8.engine.StyleGuide') as StyleGuide:
            with mock.patch('flake8.engine.get_parser') as get_parser:
                get_parser.return_value = (m, [])
                engine.get_style_guide(foo='bar')
                get_parser.assert_called_once_with()
            StyleGuide.assert_called_once_with(**{'parser': m, 'foo': 'bar'})

    def test_register_extensions(self):
        with mock.patch('pep8.register_check') as register_check:
            registered_extensions = engine._register_extensions()
            self.assertTrue(isinstance(registered_extensions[0], util.OrderedSet))
            self.assertTrue(len(registered_extensions[0]) > 0)
            for i in registered_extensions[1:]:
                self.assertTrue(isinstance(i, list))
            register_check.assert_called()

    def test_get_parser(self):
        # setup
        re = self.start_patch('flake8.engine._register_extensions')
        gpv = self.start_patch('flake8.engine.get_python_version')
        pgp = self.start_patch('pep8.get_parser')
        m = mock.Mock()
        re.return_value = ([('pyflakes', '0.7'), ('mccabe', '0.2')], [], [])
        gpv.return_value = 'Python Version'
        pgp.return_value = m
        # actual call we're testing
        parser, hooks = engine.get_parser()
        # assertions
        re.assert_called()
        gpv.assert_called()
        pgp.assert_called_once_with(
            'flake8',
            '%s (pyflakes: 0.7, mccabe: 0.2) Python Version' % __version__
            )
        m.remove_option.assert_called()
        m.add_option.assert_called()
        self.assertEqual(parser, m)
        self.assertEqual(hooks, [])
        # clean-up
        self.stop_patches()

    def test_get_python_version(self):
        self.assertTrue('on' in engine.get_python_version())
        # Silly test but it will provide 100% test coverage
        # Also we can never be sure (without reconstructing the string
        # ourselves) what system we may be testing on.

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_flakes
# -*- coding: utf-8 -*-
import sys

from unittest import TestCase
from pyflakes.api import check


class FlakesTestReporter(object):
    def __init__(self):
        self.messages = []
        self.flakes = self.messages.append

    def unexpectedError(self, filename, msg):
        self.flakes('[unexpectedError] %s: %s' % (filename, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):
        self.flakes('[syntaxError] %s:%d: %s' % (filename, lineno, msg))


code0 = """
try:
    pass
except ValueError, err:
    print(err)
"""

code1 = """
try:
    pass
except ValueError as err:
    print(err)
"""

code2 = """
try:
    pass
except ValueError:
    print("err")

try:
    pass
except ValueError:
    print("err")
"""

code3 = """
try:
    pass
except (ImportError, ValueError):
    print("err")
"""

code_from_import_exception = """
from foo import SomeException
try:
    pass
except SomeException:
    print("err")
"""

code_import_exception = """
import foo.SomeException
try:
    pass
except foo.SomeException:
    print("err")
"""


class TestFlake(TestCase):

    def test_exception(self):
        codes = [code1, code2, code3]
        if sys.version_info < (2, 6):
            codes[0] = code0
        elif sys.version_info < (3,):
            codes.insert(0, code0)
        for code in codes:
            reporter = FlakesTestReporter()
            warnings = check(code, '(stdin)', reporter)
            self.assertFalse(reporter.messages)
            self.assertEqual(warnings, 0)

    def test_from_import_exception_in_scope(self):
        reporter = FlakesTestReporter()
        warnings = check(code_from_import_exception, '(stdin)', reporter)
        self.assertFalse(reporter.messages)
        self.assertEqual(warnings, 0)

    def test_import_exception_in_scope(self):
        reporter = FlakesTestReporter()
        warnings = check(code_import_exception, '(stdin)', reporter)
        self.assertFalse(reporter.messages)
        self.assertEqual(warnings, 0)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

try:
    import ast
    iter_child_nodes = ast.iter_child_nodes
except ImportError:   # Python 2.5
    import _ast as ast

    if 'decorator_list' not in ast.ClassDef._fields:
        # Patch the missing attribute 'decorator_list'
        ast.ClassDef.decorator_list = ()
        ast.FunctionDef.decorator_list = property(lambda s: s.decorators)

    def iter_child_nodes(node):
        """
        Yield all direct child nodes of *node*, that is, all fields that
        are nodes and all items of fields that are lists of nodes.
        """
        if not node._fields:
            return
        for name in node._fields:
            field = getattr(node, name, None)
            if isinstance(field, ast.AST):
                yield field
            elif isinstance(field, list):
                for item in field:
                    if isinstance(item, ast.AST):
                        yield item


class OrderedSet(list):
    """List without duplicates."""
    __slots__ = ()

    def add(self, value):
        if value not in self:
            self.append(value)


def is_flag(val):
    """Guess if the value could be an on/off toggle"""
    val = str(val)
    return val.upper() in ('1', '0', 'F', 'T', 'TRUE', 'FALSE', 'ON', 'OFF')


def flag_on(val):
    """Return true if flag is on"""
    return str(val).upper() in ('1', 'T', 'TRUE', 'ON')

########NEW FILE########
__FILENAME__ = _pyflakes
# -*- coding: utf-8 -*-
import pyflakes
import pyflakes.checker


def patch_pyflakes():
    """Add error codes to Pyflakes messages."""
    codes = dict([line.split()[::-1] for line in (
        'F401 UnusedImport',
        'F402 ImportShadowedByLoopVar',
        'F403 ImportStarUsed',
        'F404 LateFutureImport',
        'F810 Redefined',               # XXX Obsolete?
        'F811 RedefinedWhileUnused',
        'F812 RedefinedInListComp',
        'F821 UndefinedName',
        'F822 UndefinedExport',
        'F823 UndefinedLocal',
        'F831 DuplicateArgument',
        'F841 UnusedVariable',
    )])

    for name, obj in vars(pyflakes.messages).items():
        if name[0].isupper() and obj.message:
            obj.flake8_msg = '%s %s' % (codes.get(name, 'F999'), obj.message)
patch_pyflakes()


class FlakesChecker(pyflakes.checker.Checker):
    """Subclass the Pyflakes checker to conform with the flake8 API."""
    name = 'pyflakes'
    version = pyflakes.__version__

    @classmethod
    def add_options(cls, parser):
        parser.add_option('--builtins',
                          help="define more built-ins, comma separated")
        parser.config_options.append('builtins')

    @classmethod
    def parse_options(cls, options):
        if options.builtins:
            cls.builtIns = cls.builtIns.union(options.builtins.split(','))

    def run(self):
        for m in self.messages:
            col = getattr(m, 'col', 0)
            yield m.lineno, col, (m.flake8_msg % m.message_args), m.__class__

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
        complx.append('%s:%d:1: %s' % (filename, lineno, text))

    if len(complx) == 0:
        return 0
    print('\n'.join(complx))
    return len(complx)


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
__FILENAME__ = pep8
#!/usr/bin/env python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006-2009 Johann C. Rocholl <johann@rocholl.net>
# Copyright (C) 2009-2013 Florent Xicluna <florent.xicluna@gmail.com>
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
Check Python source code formatting, according to PEP 8:
http://www.python.org/dev/peps/pep-0008/

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
__version__ = '1.4.6'

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
SKIP_TOKENS = frozenset([tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                         tokenize.INDENT, tokenize.DEDENT])
BENCHMARK_KEYS = ['directories', 'files', 'logical lines', 'physical lines']

INDENT_REGEX = re.compile(r'([ \t]*)')
RAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,')
RERAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,\s*\w+\s*,\s*\w+')
ERRORCODE_REGEX = re.compile(r'\b[A-Z]\d{3}\b')
DOCSTRING_REGEX = re.compile(r'u?r?["\']')
EXTRANEOUS_WHITESPACE_REGEX = re.compile(r'[[({] | []}),;:]')
WHITESPACE_AFTER_COMMA_REGEX = re.compile(r'[,;:]\s*(?:  |\t)')
COMPARE_SINGLETON_REGEX = re.compile(r'([=!]=)\s*(None|False|True)')
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
    r"""
    Never mix tabs and spaces.

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
    r"""
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.

    Okay: if True:\n    return
    W191: if True:\n\treturn
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    if '\t' in indent:
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    r"""
    JCR: Trailing whitespace is superfluous.
    FBM: Except when it occurs as part of a blank line (i.e. the line is
         nothing but whitespace). According to Python docs[1] a line with only
         whitespace is considered a blank line, and is to be ignored. However,
         matching a blank line to its indentation level avoids mistakenly
         terminating a multi-line statement (e.g. class declaration) when
         pasting code into the standard Python interpreter.

         [1] http://docs.python.org/reference/lexical_analysis.html#blank-lines

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


def trailing_blank_lines(physical_line, lines, line_number):
    r"""
    JCR: Trailing blank lines are superfluous.

    Okay: spam(1)
    W391: spam(1)\n
    """
    if not physical_line.rstrip() and line_number == len(lines):
        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    """
    JCR: The last line should have a newline.

    Reports warning W292.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line, max_line_length):
    """
    Limit all lines to a maximum of 79 characters.

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
                previous_logical, previous_indent_level):
    r"""
    Separate top-level function and class definitions with two blank lines.

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
            if not (blank_lines or previous_indent_level < indent_level or
                    DOCSTRING_REGEX.match(previous_logical)):
                yield 0, "E301 expected 1 blank line, found 0"
        elif blank_lines != 2:
            yield 0, "E302 expected 2 blank lines, found %d" % blank_lines


def extraneous_whitespace(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

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
    r"""
    Avoid extraneous whitespace around keywords.

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
    """
    JCR: Each comma, semicolon or colon should be followed by whitespace.

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
    r"""
    Use 4 spaces per indentation level.

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
                          noqa, verbose):
    r"""
    Continuation lines should align wrapped elements either vertically using
    Python's implicit line joining inside parentheses, brackets and braces, or
    using a hanging indent.

    When using a hanging indent the following considerations should be applied:

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
    E125: if (a or\n    b):\n    pass
    E126: a = (\n        42)
    E127: a = (24,\n      42)
    E128: a = (24,\n    42)
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
    # remember how many brackets were opened on each line
    parens = [0] * nrows
    # relative indents of physical lines
    rel_indent = [0] * nrows
    # visual indents
    indent_chances = {}
    last_indent = tokens[0][2]
    indent = [last_indent[1]]
    if verbose >= 3:
        print(">>> " + tokens[0][4].rstrip())

    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = (not last_token_multiline and
                       token_type not in (tokenize.NL, tokenize.NEWLINE))

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = expand_indent(line) - indent_level

            if depth:
                # a bracket expression in a continuation line.
                # find the line that it was opened on
                for open_row in range(row - 1, -1, -1):
                    if parens[open_row]:
                        break
            else:
                # an unbracketed continuation line (ie, backslash)
                open_row = 0
            hang = rel_indent[row] - rel_indent[open_row]
            close_bracket = (token_type == tokenize.OP and text in ']})')
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
            elif visual_indent is True:
                # visual indent is verified
                if not indent[depth]:
                    indent[depth] = start[1]
            elif visual_indent in (text, str):
                # ignore token lined up with matching one from a previous line
                pass
            elif indent[depth] and start[1] < indent[depth]:
                # visual indent is broken
                yield (start, "E128 continuation line "
                       "under-indented for visual indent")
            elif hang == 4 or (indent_next and rel_indent[row] == 8):
                # hanging indent is verified
                if close_bracket and not hang_closing:
                    yield (start, "E123 closing bracket does not match "
                           "indentation of opening bracket's line")
            else:
                # indent is broken
                if hang <= 0:
                    error = "E122", "missing indentation or outdented"
                elif indent[depth]:
                    error = "E127", "over-indented for visual indent"
                elif hang % 4:
                    error = "E121", "indentation is not a multiple of four"
                else:
                    error = "E126", "over-indented for hanging indent"
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

        # keep track of bracket depth
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                parens[row] += 1
                if verbose >= 4:
                    print("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth]))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        rel_indent[row] = rel_indent[idx]
                        break
            assert len(indent) == depth + 1
            if start[1] not in indent_chances:
                # allow to line up tokens
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])

    if indent_next and expand_indent(line) == indent_level + 4:
        yield (last_indent, "E125 continuation line does not distinguish "
               "itself from next logical line")


def whitespace_before_parameters(logical_line, tokens):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.

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
    r"""
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

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
    r"""
    - Always surround these binary operators with a single space on
      either side: assignment (=), augmented assignment (+=, -= etc.),
      comparisons (==, <, >, !=, <>, <=, >=, in, not in, is, is not),
      Booleans (and, or, not).

    - Use spaces around arithmetic operators.

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
        if token_type in (tokenize.NL, tokenize.NEWLINE, tokenize.ERRORTOKEN):
            # ERRORTOKEN is triggered by backticks in Python 3
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
                if prev_type == tokenize.OP:
                    binary_usage = (prev_text in '}])')
                elif prev_type == tokenize.NAME:
                    binary_usage = (prev_text not in KEYWORDS)
                else:
                    binary_usage = (prev_type not in SKIP_TOKENS)

                if binary_usage:
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
    r"""
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

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
    """
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


def whitespace_before_inline_comment(logical_line, tokens):
    """
    Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.  Inline
    comments should be separated by at least two spaces from the statement.
    They should start with a # and a single space.

    Okay: x = x + 1  # Increment x
    Okay: x = x + 1    # Increment x
    E261: x = x + 1 # Increment x
    E262: x = x + 1  #Increment x
    E262: x = x + 1  #  Increment x
    """
    prev_end = (0, 0)
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            if not line[:start[1]].strip():
                continue
            if prev_end[0] == start[0] and start[1] < prev_end[1] + 2:
                yield (prev_end,
                       "E261 at least two spaces before inline comment")
            symbol, sp, comment = text.partition(' ')
            if symbol not in ('#', '#:') or comment[:1].isspace():
                yield start, "E262 inline comment should start with '# '"
        elif token_type != tokenize.NL:
            prev_end = end


def imports_on_separate_lines(logical_line):
    r"""
    Imports should usually be on separate lines.

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
    r"""
    Compound statements (multiple statements on the same line) are
    generally discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements. Also
    avoid folding such long lines!

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
    r"""
    Avoid explicit line join between brackets.

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
    """
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


def comparison_type(logical_line):
    """
    Object type comparisons should always use isinstance() instead of
    comparing types directly.

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


def python_3000_has_key(logical_line):
    r"""
    The {}.has_key() method is removed in the Python 3.
    Use the 'in' operation instead.

    Okay: if "alph" in d:\n    print d["alph"]
    W601: assert d.has_key('alph')
    """
    pos = logical_line.find('.has_key(')
    if pos > -1:
        yield pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    """
    When raising an exception, use "raise ValueError('message')"
    instead of the older form "raise ValueError, 'message'".

    The paren-using form is preferred because when the exception arguments
    are long or include string formatting, you don't need to use line
    continuation characters thanks to the containing parentheses.  The older
    form is removed in Python 3.

    Okay: raise DummyError("Message")
    W602: raise DummyError, "Message"
    """
    match = RAISE_COMMA_REGEX.match(logical_line)
    if match and not RERAISE_COMMA_REGEX.match(logical_line):
        yield match.end() - 1, "W602 deprecated form of raising exception"


def python_3000_not_equal(logical_line):
    """
    != can also be written <>, but this is an obsolete usage kept for
    backwards compatibility only. New code should always use !=.
    The older syntax is removed in Python 3.

    Okay: if a != 'no':
    W603: if a <> 'no':
    """
    pos = logical_line.find('<>')
    if pos > -1:
        yield pos, "W603 '<>' is deprecated, use '!='"


def python_3000_backticks(logical_line):
    """
    Backticks are removed in Python 3.
    Use repr() instead.

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
        f = open(filename)
        try:
            return f.readlines()
        finally:
            f.close()
    isidentifier = re.compile(r'[a-zA-Z_]\w*').match
    stdin_get_value = sys.stdin.read
else:
    # Python 3
    def readlines(filename):
        f = open(filename, 'rb')
        try:
            coding, lines = tokenize.detect_encoding(f.readline)
            f = TextIOWrapper(f, coding, line_buffering=True)
            return [l.decode(coding) for l in lines] + f.readlines()
        except (LookupError, SyntaxError, UnicodeError):
            f.close()
            # Fall back if files are improperly declared
            f = open(filename, encoding='latin-1')
            return f.readlines()
        finally:
            f.close()
    isidentifier = str.isidentifier

    def stdin_get_value():
        return TextIOWrapper(sys.stdin.buffer, errors='ignore').read()
readlines.__doc__ = "    Read the source code."
noqa = re.compile(r'# no(?:qa|pep8)\b', re.I).search


def expand_indent(line):
    r"""
    Return the amount of indentation.
    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\t')
    8
    >>> expand_indent('    \t')
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
    """
    Replace contents with 'xxx' to prevent syntax matching.

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
            row, nrows = [int(g or '1') for g in hunk_match.groups()]
            rv[path].update(range(row, row + nrows))
        elif line[:3] == '+++':
            path = line[4:].split('\t', 1)[0]
            if path[:2] == 'b/':
                path = path[2:]
            rv[path] = set()
    return dict([(os.path.join(parent, path), rows)
                 for (path, rows) in rv.items()
                 if rows and filename_match(path, patterns)])


def filename_match(filename, patterns, default=True):
    """
    Check if patterns contains a pattern that matches filename.
    If patterns is unspecified, this always returns True.
    """
    if not patterns:
        return default
    return any(fnmatch(filename, pattern) for pattern in patterns)


##############################################################################
# Framework to run all checks
##############################################################################


_checks = {'physical_line': {}, 'logical_line': {}, 'tree': {}}


def register_check(check, codes=None):
    """
    Register a new check object.
    """
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
    """
    Register all globally visible functions where the first argument name
    is 'physical_line' or 'logical_line'.
    """
    mod = inspect.getmodule(register_check)
    for (name, function) in inspect.getmembers(mod, inspect.isfunction):
        register_check(function)
init_checks_registry()


class Checker(object):
    """
    Load a Python source file, tokenize it, check coding style.
    """

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
                exc_type, exc = sys.exc_info()[:2]
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
        exc_type, exc = sys.exc_info()[:2]
        if len(exc.args) > 1:
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
        else:
            offset = (1, 0)
        self.report_error(offset[0], offset[1] or 0,
                          'E901 %s: %s' % (exc_type.__name__, exc.args[0]),
                          self.report_invalid_syntax)
    report_invalid_syntax.__doc__ = "    Check if the syntax is valid."

    def readline(self):
        """
        Get the next line from the input buffer.
        """
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        return self.lines[self.line_number - 1]

    def readline_check_physical(self):
        """
        Check and return the next physical line. This method can be
        used to feed tokenize.generate_tokens.
        """
        line = self.readline()
        if line:
            self.check_physical(line)
        return line

    def run_check(self, check, argument_names):
        """
        Run a check plugin.
        """
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """
        Run all physical checks on a raw input line.
        """
        self.physical_line = line
        if self.indent_char is None and line[:1] in WHITESPACE:
            self.indent_char = line[0]
        for name, check, argument_names in self._physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                self.report_error(self.line_number, offset, text, check)

    def build_tokens_line(self):
        """
        Build a logical line from tokens.
        """
        self.mapping = []
        logical = []
        comments = []
        length = 0
        previous = None
        for token in self.tokens:
            token_type, text = token[0:2]
            if token_type == tokenize.COMMENT:
                comments.append(text)
                continue
            if token_type in SKIP_TOKENS:
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                end_row, end = previous[3]
                start_row, start = token[2]
                if end_row != start_row:    # different row
                    prev_text = self.lines[end_row - 1][end - 1]
                    if prev_text == ',' or (prev_text not in '{[('
                                            and text not in '}])'):
                        logical.append(' ')
                        length += 1
                elif end != start:  # different column
                    fill = self.lines[end_row - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            self.mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        self.noqa = comments and noqa(''.join(comments))
        # With Python 2, if the line ends with '\r\r\n' the assertion fails
        # assert self.logical_line.strip() == self.logical_line

    def check_logical(self):
        """
        Build a line from tokens and run all logical checks on it.
        """
        self.build_tokens_line()
        self.report.increment_logical_line()
        first_line = self.lines[self.mapping[0][1][2][0] - 1]
        indent = first_line[:self.mapping[0][1][2][1]]
        self.previous_indent_level = self.indent_level
        self.indent_level = expand_indent(indent)
        if self.verbose >= 2:
            print(self.logical_line[:80].rstrip())
        for name, check, argument_names in self._logical_checks:
            if self.verbose >= 4:
                print('   ' + name)
            for result in self.run_check(check, argument_names):
                offset, text = result
                if isinstance(offset, tuple):
                    orig_number, orig_offset = offset
                else:
                    for token_offset, token in self.mapping:
                        if offset >= token_offset:
                            orig_number = token[2][0]
                            orig_offset = (token[2][1] + offset - token_offset)
                self.report_error(orig_number, orig_offset, text, check)
        self.previous_logical = self.logical_line

    def check_ast(self):
        try:
            tree = compile(''.join(self.lines), '', 'exec', PyCF_ONLY_AST)
        except (SyntaxError, TypeError):
            return self.report_invalid_syntax()
        for name, cls, _ in self._ast_checks:
            checker = cls(tree, self.filename)
            for lineno, offset, text, check in checker.run():
                if not noqa(self.lines[lineno - 1]):
                    self.report_error(lineno, offset, text, check)

    def generate_tokens(self):
        if self._io_error:
            self.report_error(1, 0, 'E902 %s' % self._io_error, readlines)
        tokengen = tokenize.generate_tokens(self.readline_check_physical)
        try:
            for token in tokengen:
                yield token
        except (SyntaxError, tokenize.TokenError):
            self.report_invalid_syntax()

    def check_all(self, expected=None, line_offset=0):
        """
        Run all checks on the input file.
        """
        self.report.init_file(self.filename, self.lines, expected, line_offset)
        if self._ast_checks:
            self.check_ast()
        self.line_number = 0
        self.indent_char = None
        self.indent_level = 0
        self.previous_logical = ''
        self.tokens = []
        self.blank_lines = blank_lines_before_comment = 0
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
                if token_type == tokenize.NEWLINE:
                    if self.blank_lines < blank_lines_before_comment:
                        self.blank_lines = blank_lines_before_comment
                    self.check_logical()
                    self.tokens = []
                    self.blank_lines = blank_lines_before_comment = 0
                elif token_type == tokenize.NL:
                    if len(self.tokens) == 1:
                        # The physical line contains only this token.
                        self.blank_lines += 1
                    self.tokens = []
                elif token_type == tokenize.COMMENT and len(self.tokens) == 1:
                    if blank_lines_before_comment < self.blank_lines:
                        blank_lines_before_comment = self.blank_lines
                    self.blank_lines = 0
                    if COMMENT_WITH_NL:
                        # The comment also ends a physical line
                        self.tokens = []
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
        """
        Get statistics for message codes that start with the prefix.

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
                print(' ' * offset + '^')
            if self._show_pep8 and doc:
                print(doc.lstrip('\n').rstrip())
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
        options, self.paths = process_options(
            parse_argv=parse_argv, config_file=config_file, parser=parser)
        if args or kwargs:
            # build options from dict
            options_dict = dict(*args, **kwargs)
            options.__dict__.update(options_dict)
            if 'paths' in options_dict:
                self.paths = options_dict['paths']

        self.runner = self.input_file
        self.options = options

        if not options.reporter:
            options.reporter = BaseReport if options.quiet else StandardReport

        for index, value in enumerate(options.exclude):
            options.exclude[index] = value.rstrip('/')
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
        """
        Check if options.exclude contains a pattern that matches filename.
        """
        if not self.options.exclude:
            return False
        basename = os.path.basename(filename)
        if filename_match(basename, self.options.exclude):
            return True
        if parent:
            filename = os.path.join(parent, filename)
        return filename_match(filename, self.options.exclude)

    def ignore_code(self, code):
        """
        Check if the error code should be ignored.

        If 'options.select' contains a prefix of the error code,
        return False.  Else, if 'options.ignore' contains a prefix of
        the error code, return True.
        """
        return (code.startswith(self.options.ignore) and
                not code.startswith(self.options.select))

    def get_checks(self, argument_name):
        """
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

    parent = tail = args and os.path.abspath(os.path.commonprefix(args))
    while tail:
        if config.read([os.path.join(parent, fn) for fn in PROJECT_CONFIG]):
            if options.verbose:
                print('local configuration: in %s' % parent)
            break
        parent, tail = os.path.split(parent)

    pep8_section = parser.prog
    if config.has_section(pep8_section):
        option_list = dict([(o.dest, o.type or o.action)
                            for o in parser.option_list])

        # First, read the default values
        new_options, _ = parser.parse_args([])

        # Second, parse the configuration
        for opt in config.options(pep8_section):
            if options.verbose > 1:
                print("  %s = %s" % (opt, config.get(pep8_section, opt)))
            if opt.replace('_', '-') not in parser.config_options:
                print("Unknown option: '%s'\n  not in [%s]" %
                      (opt, ' '.join(parser.config_options)))
                sys.exit(1)
            normalized_opt = opt.replace('-', '_')
            opt_type = option_list[normalized_opt]
            if opt_type in ('int', 'count'):
                value = config.getint(pep8_section, opt)
            elif opt_type == 'string':
                value = config.get(pep8_section, opt)
            else:
                assert opt_type in ('store_true', 'store_false')
                value = config.getboolean(pep8_section, opt)
            setattr(new_options, normalized_opt, value)

        # Third, overwrite with the command-line options
        options, _ = parser.parse_args(arglist, values=new_options)
    options.doctest = options.testsuite = False
    return options


def process_options(arglist=None, parse_argv=False, config_file=None,
                    parser=None):
    """Process options passed either via arglist or via command line args."""
    if not arglist and not parse_argv:
        # Don't read the command line if the module is used as a library.
        arglist = []
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
    options, args = parser.parse_args(arglist)
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
    options.exclude = options.exclude.split(',')
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
__FILENAME__ = api
"""
API for the command-line I{pyflakes} tool.
"""
from __future__ import with_statement

import sys
import os
import _ast
from optparse import OptionParser

from pyflakes import checker, __version__
from pyflakes import reporter as modReporter

__all__ = ['check', 'checkPath', 'checkRecursive', 'iterSourceCode', 'main']


def check(codeString, filename, reporter=None):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @param reporter: A L{Reporter} instance, where errors and warnings will be
        reported.

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    if reporter is None:
        reporter = modReporter._makeDefaultReporter()
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError:
        value = sys.exc_info()[1]
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            reporter.unexpectedError(filename, 'problem decoding source')
        else:
            reporter.syntaxError(filename, msg, lineno, offset, text)
        return 1
    except Exception:
        reporter.unexpectedError(filename, 'problem decoding source')
        return 1
    # Okay, it's syntactically valid.  Now check it.
    w = checker.Checker(tree, filename)
    w.messages.sort(key=lambda m: m.lineno)
    for warning in w.messages:
        reporter.flake(warning)
    return len(w.messages)


def checkPath(filename, reporter=None):
    """
    Check the given path, printing out any warnings detected.

    @param reporter: A L{Reporter} instance, where errors and warnings will be
        reported.

    @return: the number of warnings printed
    """
    if reporter is None:
        reporter = modReporter._makeDefaultReporter()
    try:
        with open(filename, 'U') as f:
            codestr = f.read() + '\n'
    except UnicodeError:
        reporter.unexpectedError(filename, 'problem decoding source')
        return 1
    except IOError:
        msg = sys.exc_info()[1]
        reporter.unexpectedError(filename, msg.args[1])
        return 1
    return check(codestr, filename, reporter)


def iterSourceCode(paths):
    """
    Iterate over all Python source files in C{paths}.

    @param paths: A list of paths.  Directories will be recursed into and
        any .py files found will be yielded.  Any non-directories will be
        yielded as-is.
    """
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.py'):
                        yield os.path.join(dirpath, filename)
        else:
            yield path


def checkRecursive(paths, reporter):
    """
    Recursively check all source files in C{paths}.

    @param paths: A list of paths to Python source files and directories
        containing Python source files.
    @param reporter: A L{Reporter} where all of the warnings and errors
        will be reported to.
    @return: The number of warnings found.
    """
    warnings = 0
    for sourcePath in iterSourceCode(paths):
        warnings += checkPath(sourcePath, reporter)
    return warnings


def main(prog=None):
    parser = OptionParser(prog=prog, version=__version__)
    __, args = parser.parse_args()
    reporter = modReporter._makeDefaultReporter()
    if args:
        warnings = checkRecursive(args, reporter)
    else:
        warnings = check(sys.stdin.read(), '<stdin>', reporter)
    raise SystemExit(warnings > 0)

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
try:
    builtin_vars = dir(__import__('builtins'))
    PY2 = False
except ImportError:
    builtin_vars = dir(__import__('__builtin__'))
    PY2 = True

try:
    import ast
    iter_child_nodes = ast.iter_child_nodes
except ImportError:     # Python 2.5
    import _ast as ast

    if 'decorator_list' not in ast.ClassDef._fields:
        # Patch the missing attribute 'decorator_list'
        ast.ClassDef.decorator_list = ()
        ast.FunctionDef.decorator_list = property(lambda s: s.decorators)

    def iter_child_nodes(node):
        """
        Yield all direct child nodes of *node*, that is, all fields that
        are nodes and all items of fields that are lists of nodes.
        """
        for name in node._fields:
            field = getattr(node, name, None)
            if isinstance(field, ast.AST):
                yield field
            elif isinstance(field, list):
                for item in field:
                    yield item
# Python >= 3.3 uses ast.Try instead of (ast.TryExcept + ast.TryFinally)
if hasattr(ast, 'Try'):
    ast_TryExcept = ast.Try
    ast_TryFinally = ()
else:
    ast_TryExcept = ast.TryExcept
    ast_TryFinally = ast.TryFinally

from pyflakes import messages


if PY2:
    def getNodeType(node_class):
        # workaround str.upper() which is locale-dependent
        return str(unicode(node_class.__name__).upper())
else:
    def getNodeType(node_class):
        return node_class.__name__.upper()


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


class Importation(Binding):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """
    def __init__(self, name, source):
        self.fullName = name
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)


class Argument(Binding):
    """
    Represents binding a name as an argument.
    """


class Definition(Binding):
    """
    A binding that defines a function or a class.
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
    def names(self):
        """
        Return a list of the names referenced by this binding.
        """
        names = []
        if isinstance(self.source, ast.List):
            for node in self.source.elts:
                if isinstance(node, ast.Str):
                    names.append(node.s)
        return names


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
    withDoctest = ('PYFLAKES_NODOCTEST' not in os.environ)

    builtIns = set(builtin_vars).union(_MAGIC_GLOBALS)
    _customBuiltIns = os.environ.get('PYFLAKES_BUILTINS')
    if _customBuiltIns:
        builtIns.update(_customBuiltIns.split(','))
    del _customBuiltIns

    def __init__(self, tree, filename='(none)', builtins=None):
        self._nodeHandlers = {}
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.deadScopes = []
        self.messages = []
        self.filename = filename
        if builtins:
            self.builtIns = self.builtIns.union(builtins)
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
            export = isinstance(scope.get('__all__'), ExportBinding)
            if export:
                all = scope['__all__'].names()
                if not scope.importStarred and \
                   os.path.basename(self.filename) != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = set(all) - set(scope)
                    for name in undefined:
                        self.report(messages.UndefinedExport,
                                    scope['__all__'].source, name)
            else:
                all = []

            # Look for imported names that aren't used.
            for importation in scope.values():
                if isinstance(importation, Importation):
                    if not importation.used and importation.name not in all:
                        self.report(messages.UnusedImport,
                                    importation.source, importation.name)

    def pushScope(self, scopeClass=FunctionScope):
        self.scopeStack.append(scopeClass())

    def pushFunctionScope(self):    # XXX Deprecated
        self.pushScope(FunctionScope)

    def pushClassScope(self):       # XXX Deprecated
        self.pushScope(ClassScope)

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def hasParent(self, node, kind):
        while hasattr(node, 'parent'):
            node = node.parent
            if isinstance(node, kind):
                return True

    def getCommonAncestor(self, lnode, rnode, stop=None):
        if not stop:
            stop = self.root
        if lnode is rnode:
            return lnode
        if stop in (lnode, rnode):
            return stop

        if not hasattr(lnode, 'parent') or not hasattr(rnode, 'parent'):
            return
        if (lnode.level > rnode.level):
            return self.getCommonAncestor(lnode.parent, rnode, stop)
        if (rnode.level > lnode.level):
            return self.getCommonAncestor(lnode, rnode.parent, stop)
        return self.getCommonAncestor(lnode.parent, rnode.parent, stop)

    def descendantOf(self, node, ancestors, stop=None):
        for a in ancestors:
            if self.getCommonAncestor(node, a, stop) not in (stop, None):
                return True
        return False

    def onFork(self, parent, lnode, rnode, items):
        return (self.descendantOf(lnode, items, parent) ^
                self.descendantOf(rnode, items, parent))

    def differentForks(self, lnode, rnode):
        """True, if lnode and rnode are located on different forks of IF/TRY"""
        ancestor = self.getCommonAncestor(lnode, rnode)
        if isinstance(ancestor, ast.If):
            for fork in (ancestor.body, ancestor.orelse):
                if self.onFork(ancestor, lnode, rnode, fork):
                    return True
        elif isinstance(ancestor, ast_TryExcept):
            body = ancestor.body + ancestor.orelse
            for fork in [body] + [[hdl] for hdl in ancestor.handlers]:
                if self.onFork(ancestor, lnode, rnode, fork):
                    return True
        elif isinstance(ancestor, ast_TryFinally):
            if self.onFork(ancestor, lnode, rnode, ancestor.body):
                return True
        return False

    def addBinding(self, node, value, reportRedef=True):
        """
        Called when a binding is altered.

        - `node` is the statement responsible for the change
        - `value` is the optional new value, a Binding instance, associated
          with the binding; if None, the binding is deleted if it exists.
        - if `reportRedef` is True (default), rebinding while unused will be
          reported.
        """
        redefinedWhileUnused = False
        if not isinstance(self.scope, ClassScope):
            for scope in self.scopeStack[::-1]:
                existing = scope.get(value.name)
                if (isinstance(existing, Importation)
                        and not existing.used
                        and (not isinstance(value, Importation) or
                             value.fullName == existing.fullName)
                        and reportRedef
                        and not self.differentForks(node, existing.source)):
                    redefinedWhileUnused = True
                    self.report(messages.RedefinedWhileUnused,
                                node, value.name, existing.source)

        existing = self.scope.get(value.name)
        if not redefinedWhileUnused and self.hasParent(value.source, ast.ListComp):
            if (existing and reportRedef
                    and not self.hasParent(existing.source, (ast.For, ast.ListComp))
                    and not self.differentForks(node, existing.source)):
                self.report(messages.RedefinedInListComp,
                            node, value.name, existing.source)

        if (isinstance(existing, Definition)
                and not existing.used
                and not self.differentForks(node, existing.source)):
            self.report(messages.RedefinedWhileUnused,
                        node, value.name, existing.source)
        else:
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

        parent = getattr(node, 'parent', None)
        if isinstance(parent, (ast.For, ast.comprehension, ast.Tuple, ast.List)):
            binding = Binding(name, node)
        elif (parent is not None and name == '__all__' and
              isinstance(self.scope, ModuleScope)):
            binding = ExportBinding(name, parent.value)
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

    def handleChildren(self, tree):
        for node in iter_child_nodes(tree):
            self.handleNode(node, tree)

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
        node.level = self.nodeDepth
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
            docstring, node_lineno = self.getDocstring(node.body[0])
            if not docstring:
                return
            examples = self._getDoctestExamples(docstring)
        except (ValueError, IndexError):
            # e.g. line 6 of the docstring for <string> has inconsistent
            # leading whitespace: ...
            return
        node_offset = self.offset or (0, 0)
        self.pushScope()
        for example in examples:
            try:
                tree = compile(example.source, "<doctest>", "exec", ast.PyCF_ONLY_AST)
            except SyntaxError:
                e = sys.exc_info()[1]
                position = (node_lineno + example.lineno + e.lineno,
                            example.indent + 4 + e.offset)
                self.report(messages.DoctestSyntaxError, node, position)
            else:
                self.offset = (node_offset[0] + node_lineno + example.lineno,
                               node_offset[1] + example.indent + 4)
                self.handleChildren(tree)
                self.offset = node_offset
        self.popScope()

    def ignore(self, node):
        pass

    # "stmt" type nodes
    RETURN = DELETE = PRINT = WHILE = IF = WITH = WITHITEM = RAISE = \
        TRYFINALLY = ASSERT = EXEC = EXPR = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = BINOP = UNARYOP = IFEXP = DICT = SET = YIELD = YIELDFROM = \
        COMPARE = CALL = REPR = ATTRIBUTE = SUBSCRIPT = LIST = TUPLE = \
        STARRED = handleChildren

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
    COMPREHENSION = KEYWORD = handleChildren

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(node.names)

    NONLOCAL = GLOBAL

    def LISTCOMP(self, node):
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)

    def GENERATOREXP(self, node):
        self.pushScope(GeneratorScope)
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)
        self.popScope()

    SETCOMP = GENERATOREXP

    def DICTCOMP(self, node):
        self.pushScope(GeneratorScope)
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.key, node)
        self.handleNode(node.value, node)
        self.popScope()

    def FOR(self, node):
        """
        Process bindings for loop variables.
        """
        vars = []

        def collectLoopVars(n):
            if isinstance(n, ast.Name):
                vars.append(n.id)
            elif isinstance(n, ast.expr_context):
                return
            else:
                for c in iter_child_nodes(n):
                    collectLoopVars(c)

        collectLoopVars(node.target)
        for varn in vars:
            if (isinstance(self.scope.get(varn), Importation)
                    # unused ones will get an unused import warning
                    and self.scope[varn].used):
                self.report(messages.ImportShadowedByLoopVar,
                            node, varn, self.scope[varn].source)

        self.handleChildren(node)

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

    def FUNCTIONDEF(self, node):
        for deco in node.decorator_list:
            self.handleNode(deco, node)
        self.addBinding(node, FunctionDefinition(node.name, node))
        self.LAMBDA(node)
        if self.withDoctest:
            self.deferFunction(lambda: self.handleDoctests(node))

    def LAMBDA(self, node):
        args = []

        if PY2:
            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        if arg.id in args:
                            self.report(messages.DuplicateArgument,
                                        node, arg.id)
                        args.append(arg.id)
            addArgs(node.args.args)
            defaults = node.args.defaults
        else:
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.arg in args:
                    self.report(messages.DuplicateArgument,
                                node, arg.arg)
                args.append(arg.arg)
                self.handleNode(arg.annotation, node)
            if hasattr(node, 'returns'):    # Only for FunctionDefs
                for annotation in (node.args.varargannotation,
                                   node.args.kwargannotation, node.returns):
                    self.handleNode(annotation, node)
            defaults = node.args.defaults + node.args.kw_defaults

        # vararg/kwarg identifiers are not Name nodes
        for wildcard in (node.args.vararg, node.args.kwarg):
            if not wildcard:
                continue
            if wildcard in args:
                self.report(messages.DuplicateArgument, node, wildcard)
            args.append(wildcard)
        for default in defaults:
            self.handleNode(default, node)

        def runFunction():

            self.pushScope()
            for name in args:
                self.addBinding(node, Argument(name, node), reportRedef=False)
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

    def ASSIGN(self, node):
        self.handleNode(node.value, node)
        for target in node.targets:
            self.handleNode(target, node)

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
        for child in iter_child_nodes(node):
            if child not in node.body:
                self.handleNode(child, node)

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

########NEW FILE########
__FILENAME__ = reporter
"""
Provide the Reporter class.
"""

import sys


class Reporter(object):
    """
    Formats the results of pyflakes checks to users.
    """

    def __init__(self, warningStream, errorStream):
        """
        Construct a L{Reporter}.

        @param warningStream: A file-like object where warnings will be
            written to.  The stream's C{write} method must accept unicode.
            C{sys.stdout} is a good value.
        @param errorStream: A file-like object where error output will be
            written to.  The stream's C{write} method must accept unicode.
            C{sys.stderr} is a good value.
        """
        self._stdout = warningStream
        self._stderr = errorStream

    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process C{filename}.

        @param filename: The path to a file that we could not process.
        @ptype filename: C{unicode}
        @param msg: A message explaining the problem.
        @ptype msg: C{unicode}
        """
        self._stderr.write("%s: %s\n" % (filename, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax errror in C{filename}.

        @param filename: The path to the file with the syntax error.
        @ptype filename: C{unicode}
        @param msg: An explanation of the syntax error.
        @ptype msg: C{unicode}
        @param lineno: The line number where the syntax error occurred.
        @ptype lineno: C{int}
        @param offset: The column on which the syntax error occurred.
        @ptype offset: C{int}
        @param text: The source code containing the syntax error.
        @ptype text: C{unicode}
        """
        line = text.splitlines()[-1]
        if offset is not None:
            offset = offset - (len(text) - len(line))
        self._stderr.write('%s:%d: %s\n' % (filename, lineno, msg))
        self._stderr.write(line)
        self._stderr.write('\n')
        if offset is not None:
            self._stderr.write(" " * (offset + 1) + "^\n")

    def flake(self, message):
        """
        pyflakes found something wrong with the code.

        @param: A L{pyflakes.messages.Message}.
        """
        self._stdout.write(str(message))
        self._stdout.write('\n')


def _makeDefaultReporter():
    """
    Make a reporter that can be used when no reporter is specified.
    """
    return Reporter(sys.stdout, sys.stderr)

########NEW FILE########
__FILENAME__ = pyflakes
"""
Implementation of the command-line I{pyflakes} tool.
"""
from __future__ import absolute_import

# For backward compatibility
from pyflakes.api import check, checkPath, checkRecursive, iterSourceCode, main

########NEW FILE########
__FILENAME__ = harness

import sys
import textwrap
import unittest

from pyflakes import checker

__all__ = ['TestCase', 'skip', 'skipIf']

if sys.version_info < (2, 7):
    skip = lambda why: (lambda func: 'skip')  # not callable
    skipIf = lambda cond, why: (skip(why) if cond else lambda func: func)
else:
    skip = unittest.skip
    skipIf = unittest.skipIf
PyCF_ONLY_AST = 1024


class TestCase(unittest.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        tree = compile(textwrap.dedent(input), "<test>", "exec", PyCF_ONLY_AST)
        w = checker.Checker(tree, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assertEqual(outputs, expectedOutputs, '''\
for input:
%s
expected outputs:
%r
but got:
%s''' % (input, expectedOutputs, '\n'.join([str(o) for o in w.messages])))
        return w

    if sys.version_info < (2, 7):

        def assertIs(self, expr1, expr2, msg=None):
            if expr1 is not expr2:
                self.fail(msg or '%r is not %r' % (expr1, expr2))

########NEW FILE########
__FILENAME__ = test_api
"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import os
import sys
import shutil
import subprocess
import tempfile

from pyflakes.messages import UnusedImport
from pyflakes.reporter import Reporter
from pyflakes.api import (
    checkPath,
    checkRecursive,
    iterSourceCode,
)
from pyflakes.test.harness import TestCase, skipIf

if sys.version_info < (3,):
    from cStringIO import StringIO
else:
    from io import StringIO
    unichr = chr


def withStderrTo(stderr, f, *args, **kwargs):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f(*args, **kwargs)
    finally:
        sys.stderr = outer


class Node(object):
    """
    Mock an AST node.
    """
    def __init__(self, lineno, col_offset=0):
        self.lineno = lineno
        self.col_offset = col_offset


class LoggingReporter(object):
    """
    Implementation of Reporter that just appends any error to a list.
    """

    def __init__(self, log):
        """
        Construct a C{LoggingReporter}.

        @param log: A list to append log messages to.
        """
        self.log = log

    def flake(self, message):
        self.log.append(('flake', str(message)))

    def unexpectedError(self, filename, message):
        self.log.append(('unexpectedError', filename, message))

    def syntaxError(self, filename, msg, lineno, offset, line):
        self.log.append(('syntaxError', filename, msg, lineno, offset, line))


class TestIterSourceCode(TestCase):
    """
    Tests for L{iterSourceCode}.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def makeEmptyFile(self, *parts):
        assert parts
        fpath = os.path.join(self.tempdir, *parts)
        fd = open(fpath, 'a')
        fd.close()
        return fpath

    def test_emptyDirectory(self):
        """
        There are no Python files in an empty directory.
        """
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_singleFile(self):
        """
        If the directory contains one Python file, C{iterSourceCode} will find
        it.
        """
        childpath = self.makeEmptyFile('foo.py')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [childpath])

    def test_onlyPythonSource(self):
        """
        Files that are not Python source files are not included.
        """
        self.makeEmptyFile('foo.pyc')
        self.assertEqual(list(iterSourceCode([self.tempdir])), [])

    def test_recurses(self):
        """
        If the Python files are hidden deep down in child directories, we will
        find them.
        """
        os.mkdir(os.path.join(self.tempdir, 'foo'))
        apath = self.makeEmptyFile('foo', 'a.py')
        os.mkdir(os.path.join(self.tempdir, 'bar'))
        bpath = self.makeEmptyFile('bar', 'b.py')
        cpath = self.makeEmptyFile('c.py')
        self.assertEqual(
            sorted(iterSourceCode([self.tempdir])),
            sorted([apath, bpath, cpath]))

    def test_multipleDirectories(self):
        """
        L{iterSourceCode} can be given multiple directories.  It will recurse
        into each of them.
        """
        foopath = os.path.join(self.tempdir, 'foo')
        barpath = os.path.join(self.tempdir, 'bar')
        os.mkdir(foopath)
        apath = self.makeEmptyFile('foo', 'a.py')
        os.mkdir(barpath)
        bpath = self.makeEmptyFile('bar', 'b.py')
        self.assertEqual(
            sorted(iterSourceCode([foopath, barpath])),
            sorted([apath, bpath]))

    def test_explicitFiles(self):
        """
        If one of the paths given to L{iterSourceCode} is not a directory but
        a file, it will include that in its output.
        """
        epath = self.makeEmptyFile('e.py')
        self.assertEqual(list(iterSourceCode([epath])),
                         [epath])


class TestReporter(TestCase):
    """
    Tests for L{Reporter}.
    """

    def test_syntaxError(self):
        """
        C{syntaxError} reports that there was a syntax error in the source
        file.  It reports to the error stream and includes the filename, line
        number, error message, actual line of source and a caret pointing to
        where the error is.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, 4, 'bad line of source')
        self.assertEqual(
            ("foo.py:3: a problem\n"
             "bad line of source\n"
             "     ^\n"),
            err.getvalue())

    def test_syntaxErrorNoOffset(self):
        """
        C{syntaxError} doesn't include a caret pointing to the error if
        C{offset} is passed as C{None}.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, None,
                             'bad line of source')
        self.assertEqual(
            ("foo.py:3: a problem\n"
             "bad line of source\n"),
            err.getvalue())

    def test_multiLineSyntaxError(self):
        """
        If there's a multi-line syntax error, then we only report the last
        line.  The offset is adjusted so that it is relative to the start of
        the last line.
        """
        err = StringIO()
        lines = [
            'bad line of source',
            'more bad lines of source',
        ]
        reporter = Reporter(None, err)
        reporter.syntaxError('foo.py', 'a problem', 3, len(lines[0]) + 5,
                             '\n'.join(lines))
        self.assertEqual(
            ("foo.py:3: a problem\n" +
             lines[-1] + "\n" +
             "     ^\n"),
            err.getvalue())

    def test_unexpectedError(self):
        """
        C{unexpectedError} reports an error processing a source file.
        """
        err = StringIO()
        reporter = Reporter(None, err)
        reporter.unexpectedError('source.py', 'error message')
        self.assertEqual('source.py: error message\n', err.getvalue())

    def test_flake(self):
        """
        C{flake} reports a code warning from Pyflakes.  It is exactly the
        str() of a L{pyflakes.messages.Message}.
        """
        out = StringIO()
        reporter = Reporter(out, None)
        message = UnusedImport('foo.py', Node(42), 'bar')
        reporter.flake(message)
        self.assertEqual(out.getvalue(), "%s\n" % (message,))


class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """

    def makeTempFile(self, content):
        """
        Make a temporary file containing C{content} and return a path to it.
        """
        _, fpath = tempfile.mkstemp()
        if not hasattr(content, 'decode'):
            content = content.encode('ascii')
        fd = open(fpath, 'wb')
        fd.write(content)
        fd.close()
        return fpath

    def assertHasErrors(self, path, errorList):
        """
        Assert that C{path} causes errors.

        @param path: A path to a file to check.
        @param errorList: A list of errors expected to be printed to stderr.
        """
        err = StringIO()
        count = withStderrTo(err, checkPath, path)
        self.assertEqual(
            (count, err.getvalue()), (len(errorList), ''.join(errorList)))

    def getErrors(self, path):
        """
        Get any warnings or errors reported by pyflakes for the file at C{path}.

        @param path: The path to a Python file on disk that pyflakes will check.
        @return: C{(count, log)}, where C{count} is the number of warnings or
            errors generated, and log is a list of those warnings, presented
            as structured data.  See L{LoggingReporter} for more details.
        """
        log = []
        reporter = LoggingReporter(log)
        count = checkPath(path, reporter)
        return count, log

    def test_legacyScript(self):
        from pyflakes.scripts import pyflakes as script_pyflakes
        self.assertIs(script_pyflakes.checkPath, checkPath)

    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = self.makeTempFile("def foo():\n\tpass\n\t")
        self.assertHasErrors(fName, [])

    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        count, errors = self.getErrors('extremo')
        self.assertEqual(count, 1)
        self.assertEqual(
            errors,
            [('unexpectedError', 'extremo', 'No such file or directory')])

    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        def evaluate(source):
            exec(source)
        try:
            evaluate(source)
        except SyntaxError:
            e = sys.exc_info()[1]
            self.assertTrue(e.text.count('\n') > 1)
        else:
            self.fail()

        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:8: invalid syntax
    '''quux'''
           ^
""" % (sourcePath,)])

    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        sourcePath = self.makeTempFile("def foo(")
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: unexpected EOF while parsing
def foo(
         ^
""" % (sourcePath,)])

    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        sourcePath = self.makeTempFile(source)
        last_line = '        ^\n' if sys.version_info >= (3, 2) else ''
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: non-default argument follows default argument
def foo(bar=baz, bax):
%s""" % (sourcePath, last_line)])

    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        sourcePath = self.makeTempFile(source)
        last_line = '             ^\n' if sys.version_info >= (3, 2) else ''
        self.assertHasErrors(
            sourcePath,
            ["""\
%s:1: non-keyword arg after keyword arg
foo(bar=baz, bax)
%s""" % (sourcePath, last_line)])

    def test_invalidEscape(self):
        """
        The invalid escape syntax raises ValueError in Python 2
        """
        ver = sys.version_info
        # ValueError: invalid \x escape
        sourcePath = self.makeTempFile(r"foo = '\xyz'")
        if ver < (3,):
            decoding_error = "%s: problem decoding source\n" % (sourcePath,)
        else:
            last_line = '       ^\n' if ver >= (3, 2) else ''
            # Column has been "fixed" since 3.2.4 and 3.3.1
            col = 1 if ver >= (3, 3, 1) or ((3, 2, 4) <= ver < (3, 3)) else 2
            decoding_error = """\
%s:1: (unicode error) 'unicodeescape' codec can't decode bytes \
in position 0-%d: truncated \\xXX escape
foo = '\\xyz'
%s""" % (sourcePath, col, last_line)
        self.assertHasErrors(
            sourcePath, [decoding_error])

    def test_permissionDenied(self):
        """
        If the source file is not readable, this is reported on standard
        error.
        """
        sourcePath = self.makeTempFile('')
        os.chmod(sourcePath, 0)
        count, errors = self.getErrors(sourcePath)
        self.assertEqual(count, 1)
        self.assertEqual(
            errors,
            [('unexpectedError', sourcePath, "Permission denied")])

    def test_pyflakesWarning(self):
        """
        If the source file has a pyflakes warning, this is reported as a
        'flake'.
        """
        sourcePath = self.makeTempFile("import foo")
        count, errors = self.getErrors(sourcePath)
        self.assertEqual(count, 1)
        self.assertEqual(
            errors, [('flake', str(UnusedImport(sourcePath, Node(1), 'foo')))])

    @skipIf(sys.version_info >= (3,), "not relevant")
    def test_misencodedFileUTF8(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = unichr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-8')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["%s: problem decoding source\n" % (sourcePath,)])

    def test_misencodedFileUTF16(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        SNOWMAN = unichr(0x2603)
        source = ("""\
# coding: ascii
x = "%s"
""" % SNOWMAN).encode('utf-16')
        sourcePath = self.makeTempFile(source)
        self.assertHasErrors(
            sourcePath, ["%s: problem decoding source\n" % (sourcePath,)])

    def test_checkRecursive(self):
        """
        L{checkRecursive} descends into each directory, finding Python files
        and reporting problems.
        """
        tempdir = tempfile.mkdtemp()
        os.mkdir(os.path.join(tempdir, 'foo'))
        file1 = os.path.join(tempdir, 'foo', 'bar.py')
        fd = open(file1, 'wb')
        fd.write("import baz\n".encode('ascii'))
        fd.close()
        file2 = os.path.join(tempdir, 'baz.py')
        fd = open(file2, 'wb')
        fd.write("import contraband".encode('ascii'))
        fd.close()
        log = []
        reporter = LoggingReporter(log)
        warnings = checkRecursive([tempdir], reporter)
        self.assertEqual(warnings, 2)
        self.assertEqual(
            sorted(log),
            sorted([('flake', str(UnusedImport(file1, Node(1), 'baz'))),
                    ('flake',
                     str(UnusedImport(file2, Node(1), 'contraband')))]))


class IntegrationTests(TestCase):
    """
    Tests of the pyflakes script that actually spawn the script.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.tempfilepath = os.path.join(self.tempdir, 'temp')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def getPyflakesBinary(self):
        """
        Return the path to the pyflakes binary.
        """
        import pyflakes
        package_dir = os.path.dirname(pyflakes.__file__)
        return os.path.join(package_dir, '..', 'bin', 'pyflakes')

    def runPyflakes(self, paths, stdin=None):
        """
        Launch a subprocess running C{pyflakes}.

        @param args: Command-line arguments to pass to pyflakes.
        @param kwargs: Options passed on to C{subprocess.Popen}.
        @return: C{(returncode, stdout, stderr)} of the completed pyflakes
            process.
        """
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(sys.path)
        command = [sys.executable, self.getPyflakesBinary()]
        command.extend(paths)
        if stdin:
            p = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate(stdin)
        else:
            p = subprocess.Popen(command, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = p.communicate()
        rv = p.wait()
        if sys.version_info >= (3,):
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
        return (stdout, stderr, rv)

    def test_goodFile(self):
        """
        When a Python source file is all good, the return code is zero and no
        messages are printed to either stdout or stderr.
        """
        fd = open(self.tempfilepath, 'a')
        fd.close()
        d = self.runPyflakes([self.tempfilepath])
        self.assertEqual(d, ('', '', 0))

    def test_fileWithFlakes(self):
        """
        When a Python source file has warnings, the return code is non-zero
        and the warnings are printed to stdout.
        """
        fd = open(self.tempfilepath, 'wb')
        fd.write("import contraband\n".encode('ascii'))
        fd.close()
        d = self.runPyflakes([self.tempfilepath])
        expected = UnusedImport(self.tempfilepath, Node(1), 'contraband')
        self.assertEqual(d, ("%s\n" % expected, '', 1))

    def test_errors(self):
        """
        When pyflakes finds errors with the files it's given, (if they don't
        exist, say), then the return code is non-zero and the errors are
        printed to stderr.
        """
        d = self.runPyflakes([self.tempfilepath])
        error_msg = '%s: No such file or directory\n' % (self.tempfilepath,)
        self.assertEqual(d, ('', error_msg, 1))

    def test_readFromStdin(self):
        """
        If no arguments are passed to C{pyflakes} then it reads from stdin.
        """
        d = self.runPyflakes([], stdin='import contraband'.encode('ascii'))
        expected = UnusedImport('<stdin>', Node(1), 'contraband')
        self.assertEqual(d, ("%s\n" % expected, '', 1))

########NEW FILE########
__FILENAME__ = test_doctests
import textwrap

from pyflakes import messages as m
from pyflakes.test.test_other import Test as TestOther
from pyflakes.test.test_imports import Test as TestImports
from pyflakes.test.test_undefined_names import Test as TestUndefinedNames
from pyflakes.test.harness import skip


class Test(TestOther, TestImports, TestUndefinedNames):

    def doctestify(self, input):
        lines = []
        for line in textwrap.dedent(input).splitlines():
            if line.strip() == '':
                pass
            elif (line.startswith(' ') or
                  line.startswith('except:') or
                  line.startswith('except ') or
                  line.startswith('finally:') or
                  line.startswith('else:') or
                  line.startswith('elif ')):
                line = "... %s" % line
            else:
                line = ">>> %s" % line
            lines.append(line)
        doctestificator = textwrap.dedent('''\
            def doctest_something():
                """
                   %s
                """
            ''')
        return doctestificator % "\n       ".join(lines)

    def flakes(self, input, *args, **kw):
        return super(Test, self).flakes(self.doctestify(input),
                                        *args, **kw)

    def test_doubleNestingReportsClosestName(self):
        """
        Lines in doctest are a bit different so we can't use the test
        from TestUndefinedNames
        """
        exc = super(Test, self).flakes('''
        def doctest_stuff():
            """
                >>> def a():
                ...     x = 1
                ...     def b():
                ...         x = 2 # line 7 in the file
                ...         def c():
                ...             x
                ...             x = 3
                ...             return x
                ...         return x
                ...     return x

            """
        ''', m.UndefinedLocal).messages[0]
        self.assertEqual(exc.message_args, ('x', 7))

    def test_futureImport(self):
        """XXX This test can't work in a doctest"""

    def test_importBeforeDoctest(self):
        super(Test, self).flakes("""
        import foo

        def doctest_stuff():
            '''
                >>> foo
            '''
        """)

    @skip("todo")
    def test_importBeforeAndInDoctest(self):
        super(Test, self).flakes('''
        import foo

        def doctest_stuff():
            """
                >>> import foo
                >>> foo
            """

        foo
        ''', m.Redefined)

    def test_importInDoctestAndAfter(self):
        super(Test, self).flakes('''
        def doctest_stuff():
            """
                >>> import foo
                >>> foo
            """

        import foo
        foo()
        ''')

    def test_offsetInDoctests(self):
        exc = super(Test, self).flakes('''

        def doctest_stuff():
            """
                >>> x # line 5
            """

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 12)

    def test_offsetInLambdasInDoctests(self):
        exc = super(Test, self).flakes('''

        def doctest_stuff():
            """
                >>> lambda: x # line 5
            """

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 20)

    def test_offsetAfterDoctests(self):
        exc = super(Test, self).flakes('''

        def doctest_stuff():
            """
                >>> x = 5
            """

        x

        ''', m.UndefinedName).messages[0]
        self.assertEqual(exc.lineno, 8)
        self.assertEqual(exc.col, 0)

    def test_syntaxErrorInDoctest(self):
        exceptions = super(Test, self).flakes(
            '''
            def doctest_stuff():
                """
                    >>> from # line 4
                    >>>     fortytwo = 42
                    >>> except Exception:
                """
            ''',
            m.DoctestSyntaxError,
            m.DoctestSyntaxError,
            m.DoctestSyntaxError).messages
        exc = exceptions[0]
        self.assertEqual(exc.lineno, 4)
        self.assertEqual(exc.col, 26)
        exc = exceptions[1]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 16)
        exc = exceptions[2]
        self.assertEqual(exc.lineno, 6)
        self.assertEqual(exc.col, 18)

    def test_indentationErrorInDoctest(self):
        exc = super(Test, self).flakes('''
        def doctest_stuff():
            """
                >>> if True:
                ... pass
            """
        ''', m.DoctestSyntaxError).messages[0]
        self.assertEqual(exc.lineno, 5)
        self.assertEqual(exc.col, 16)

    def test_offsetWithMultiLineArgs(self):
        (exc1, exc2) = super(Test, self).flakes(
            '''
            def doctest_stuff(arg1,
                              arg2,
                              arg3):
                """
                    >>> assert
                    >>> this
                """
            ''',
            m.DoctestSyntaxError,
            m.UndefinedName).messages
        self.assertEqual(exc1.lineno, 6)
        self.assertEqual(exc1.col, 19)
        self.assertEqual(exc2.lineno, 7)
        self.assertEqual(exc2.col, 12)

    def test_doctestCanReferToFunction(self):
        super(Test, self).flakes("""
        def foo():
            '''
                >>> foo
            '''
        """)

    def test_doctestCanReferToClass(self):
        super(Test, self).flakes("""
        class Foo():
            '''
                >>> Foo
            '''
            def bar(self):
                '''
                    >>> Foo
                '''
        """)

########NEW FILE########
__FILENAME__ = test_imports

from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skip, skipIf


class Test(TestCase):

    def test_unusedImport(self):
        self.flakes('import fu, bar', m.UnusedImport, m.UnusedImport)
        self.flakes('from baz import fu, bar', m.UnusedImport, m.UnusedImport)

    def test_aliasedImport(self):
        self.flakes('import fu as FU, bar as FU',
                    m.RedefinedWhileUnused, m.UnusedImport)
        self.flakes('from moo import fu as FU, bar as FU',
                    m.RedefinedWhileUnused, m.UnusedImport)

    def test_usedImport(self):
        self.flakes('import fu; print(fu)')
        self.flakes('from baz import fu; print(fu)')
        self.flakes('import fu; del fu')

    def test_redefinedWhileUnused(self):
        self.flakes('import fu; fu = 3', m.RedefinedWhileUnused)
        self.flakes('import fu; fu, bar = 3', m.RedefinedWhileUnused)
        self.flakes('import fu; [fu, bar] = 3', m.RedefinedWhileUnused)

    def test_redefinedIf(self):
        """
        Test that importing a module twice within an if
        block does raise a warning.
        """
        self.flakes('''
        i = 2
        if i==1:
            import os
            import os
        os.path''', m.RedefinedWhileUnused)

    def test_redefinedIfElse(self):
        """
        Test that importing a module twice in if
        and else blocks does not raise a warning.
        """
        self.flakes('''
        i = 2
        if i==1:
            import os
        else:
            import os
        os.path''')

    def test_redefinedTry(self):
        """
        Test that importing a module twice in an try block
        does raise a warning.
        """
        self.flakes('''
        try:
            import os
            import os
        except:
            pass
        os.path''', m.RedefinedWhileUnused)

    def test_redefinedTryExcept(self):
        """
        Test that importing a module twice in an try
        and except block does not raise a warning.
        """
        self.flakes('''
        try:
            import os
        except:
            import os
        os.path''')

    def test_redefinedTryNested(self):
        """
        Test that importing a module twice using a nested
        try/except and if blocks does not issue a warning.
        """
        self.flakes('''
        try:
            if True:
                if True:
                    import os
        except:
            import os
        os.path''')

    def test_redefinedTryExceptMulti(self):
        self.flakes("""
        try:
            from aa import mixer
        except AttributeError:
            from bb import mixer
        except RuntimeError:
            from cc import mixer
        except:
            from dd import mixer
        mixer(123)
        """)

    def test_redefinedTryElse(self):
        self.flakes("""
        try:
            from aa import mixer
        except ImportError:
            pass
        else:
            from bb import mixer
        mixer(123)
        """, m.RedefinedWhileUnused)

    def test_redefinedTryExceptElse(self):
        self.flakes("""
        try:
            import funca
        except ImportError:
            from bb import funca
            from bb import funcb
        else:
            from bbb import funcb
        print(funca, funcb)
        """)

    def test_redefinedTryExceptFinally(self):
        self.flakes("""
        try:
            from aa import a
        except ImportError:
            from bb import a
        finally:
            a = 42
        print(a)
        """)

    def test_redefinedTryExceptElseFinally(self):
        self.flakes("""
        try:
            import b
        except ImportError:
            b = Ellipsis
            from bb import a
        else:
            from aa import a
        finally:
            a = 42
        print(a, b)
        """)

    def test_redefinedByFunction(self):
        self.flakes('''
        import fu
        def fu():
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedInNestedFunction(self):
        """
        Test that shadowing a global name with a nested function definition
        generates a warning.
        """
        self.flakes('''
        import fu
        def bar():
            def baz():
                def fu():
                    pass
        ''', m.RedefinedWhileUnused, m.UnusedImport)

    def test_redefinedByClass(self):
        self.flakes('''
        import fu
        class fu:
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedBySubclass(self):
        """
        If an imported name is redefined by a class statement which also uses
        that name in the bases list, no warning is emitted.
        """
        self.flakes('''
        from fu import bar
        class bar(bar):
            pass
        ''')

    def test_redefinedInClass(self):
        """
        Test that shadowing a global with a class attribute does not produce a
        warning.
        """
        self.flakes('''
        import fu
        class bar:
            fu = 1
        print(fu)
        ''')

    def test_usedInFunction(self):
        self.flakes('''
        import fu
        def fun():
            print(fu)
        ''')

    def test_shadowedByParameter(self):
        self.flakes('''
        import fu
        def fun(fu):
            print(fu)
        ''', m.UnusedImport)

        self.flakes('''
        import fu
        def fun(fu):
            print(fu)
        print(fu)
        ''')

    def test_newAssignment(self):
        self.flakes('fu = None')

    def test_usedInGetattr(self):
        self.flakes('import fu; fu.bar.baz')
        self.flakes('import fu; "bar".fu.baz', m.UnusedImport)

    def test_usedInSlice(self):
        self.flakes('import fu; print(fu.bar[1:])')

    def test_usedInIfBody(self):
        self.flakes('''
        import fu
        if True: print(fu)
        ''')

    def test_usedInIfConditional(self):
        self.flakes('''
        import fu
        if fu: pass
        ''')

    def test_usedInElifConditional(self):
        self.flakes('''
        import fu
        if False: pass
        elif fu: pass
        ''')

    def test_usedInElse(self):
        self.flakes('''
        import fu
        if False: pass
        else: print(fu)
        ''')

    def test_usedInCall(self):
        self.flakes('import fu; fu.bar()')

    def test_usedInClass(self):
        self.flakes('''
        import fu
        class bar:
            bar = fu
        ''')

    def test_usedInClassBase(self):
        self.flakes('''
        import fu
        class bar(object, fu.baz):
            pass
        ''')

    def test_notUsedInNestedScope(self):
        self.flakes('''
        import fu
        def bleh():
            pass
        print(fu)
        ''')

    def test_usedInFor(self):
        self.flakes('''
        import fu
        for bar in range(9):
            print(fu)
        ''')

    def test_usedInForElse(self):
        self.flakes('''
        import fu
        for bar in range(10):
            pass
        else:
            print(fu)
        ''')

    def test_redefinedByFor(self):
        self.flakes('''
        import fu
        for fu in range(2):
            pass
        ''', m.RedefinedWhileUnused)

    def test_shadowedByFor(self):
        """
        Test that shadowing a global name with a for loop variable generates a
        warning.
        """
        self.flakes('''
        import fu
        fu.bar()
        for fu in ():
            pass
        ''', m.ImportShadowedByLoopVar)

    def test_shadowedByForDeep(self):
        """
        Test that shadowing a global name with a for loop variable nested in a
        tuple unpack generates a warning.
        """
        self.flakes('''
        import fu
        fu.bar()
        for (x, y, z, (a, b, c, (fu,))) in ():
            pass
        ''', m.ImportShadowedByLoopVar)

    def test_usedInReturn(self):
        self.flakes('''
        import fu
        def fun():
            return fu
        ''')

    def test_usedInOperators(self):
        self.flakes('import fu; 3 + fu.bar')
        self.flakes('import fu; 3 % fu.bar')
        self.flakes('import fu; 3 - fu.bar')
        self.flakes('import fu; 3 * fu.bar')
        self.flakes('import fu; 3 ** fu.bar')
        self.flakes('import fu; 3 / fu.bar')
        self.flakes('import fu; 3 // fu.bar')
        self.flakes('import fu; -fu.bar')
        self.flakes('import fu; ~fu.bar')
        self.flakes('import fu; 1 == fu.bar')
        self.flakes('import fu; 1 | fu.bar')
        self.flakes('import fu; 1 & fu.bar')
        self.flakes('import fu; 1 ^ fu.bar')
        self.flakes('import fu; 1 >> fu.bar')
        self.flakes('import fu; 1 << fu.bar')

    def test_usedInAssert(self):
        self.flakes('import fu; assert fu.bar')

    def test_usedInSubscript(self):
        self.flakes('import fu; fu.bar[1]')

    def test_usedInLogic(self):
        self.flakes('import fu; fu and False')
        self.flakes('import fu; fu or False')
        self.flakes('import fu; not fu.bar')

    def test_usedInList(self):
        self.flakes('import fu; [fu]')

    def test_usedInTuple(self):
        self.flakes('import fu; (fu,)')

    def test_usedInTry(self):
        self.flakes('''
        import fu
        try: fu
        except: pass
        ''')

    def test_usedInExcept(self):
        self.flakes('''
        import fu
        try: fu
        except: pass
        ''')

    def test_redefinedByExcept(self):
        as_exc = ', ' if version_info < (2, 6) else ' as '
        self.flakes('''
        import fu
        try: pass
        except Exception%sfu: pass
        ''' % as_exc, m.RedefinedWhileUnused)

    def test_usedInRaise(self):
        self.flakes('''
        import fu
        raise fu.bar
        ''')

    def test_usedInYield(self):
        self.flakes('''
        import fu
        def gen():
            yield fu
        ''')

    def test_usedInDict(self):
        self.flakes('import fu; {fu:None}')
        self.flakes('import fu; {1:fu}')

    def test_usedInParameterDefault(self):
        self.flakes('''
        import fu
        def f(bar=fu):
            pass
        ''')

    def test_usedInAttributeAssign(self):
        self.flakes('import fu; fu.bar = 1')

    def test_usedInKeywordArg(self):
        self.flakes('import fu; fu.bar(stuff=fu)')

    def test_usedInAssignment(self):
        self.flakes('import fu; bar=fu')
        self.flakes('import fu; n=0; n+=fu')

    def test_usedInListComp(self):
        self.flakes('import fu; [fu for _ in range(1)]')
        self.flakes('import fu; [1 for _ in range(1) if fu]')

    def test_redefinedByListComp(self):
        self.flakes('import fu; [1 for fu in range(1)]', m.RedefinedWhileUnused)

    def test_usedInTryFinally(self):
        self.flakes('''
        import fu
        try: pass
        finally: fu
        ''')

        self.flakes('''
        import fu
        try: fu
        finally: pass
        ''')

    def test_usedInWhile(self):
        self.flakes('''
        import fu
        while 0:
            fu
        ''')

        self.flakes('''
        import fu
        while fu: pass
        ''')

    def test_usedInGlobal(self):
        self.flakes('''
        import fu
        def f(): global fu
        ''', m.UnusedImport)

    @skipIf(version_info >= (3,), 'deprecated syntax')
    def test_usedInBackquote(self):
        self.flakes('import fu; `fu`')

    def test_usedInExec(self):
        if version_info < (3,):
            exec_stmt = 'exec "print 1" in fu.bar'
        else:
            exec_stmt = 'exec("print(1)", fu.bar)'
        self.flakes('import fu; %s' % exec_stmt)

    def test_usedInLambda(self):
        self.flakes('import fu; lambda: fu')

    def test_shadowedByLambda(self):
        self.flakes('import fu; lambda fu: fu', m.UnusedImport)

    def test_usedInSliceObj(self):
        self.flakes('import fu; "meow"[::fu]')

    def test_unusedInNestedScope(self):
        self.flakes('''
        def bar():
            import fu
        fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_methodsDontUseClassScope(self):
        self.flakes('''
        class bar:
            import fu
            def fun(self):
                fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_nestedFunctionsNestScope(self):
        self.flakes('''
        def a():
            def b():
                fu
            import fu
        ''')

    def test_nestedClassAndFunctionScope(self):
        self.flakes('''
        def a():
            import fu
            class b:
                def c(self):
                    print(fu)
        ''')

    def test_importStar(self):
        self.flakes('from fu import *', m.ImportStarUsed)

    def test_packageImport(self):
        """
        If a dotted name is imported and used, no warning is reported.
        """
        self.flakes('''
        import fu.bar
        fu.bar
        ''')

    def test_unusedPackageImport(self):
        """
        If a dotted name is imported and not used, an unused import warning is
        reported.
        """
        self.flakes('import fu.bar', m.UnusedImport)

    def test_duplicateSubmoduleImport(self):
        """
        If a submodule of a package is imported twice, an unused import warning
        and a redefined while unused warning are reported.
        """
        self.flakes('''
        import fu.bar, fu.bar
        fu.bar
        ''', m.RedefinedWhileUnused)
        self.flakes('''
        import fu.bar
        import fu.bar
        fu.bar
        ''', m.RedefinedWhileUnused)

    def test_differentSubmoduleImport(self):
        """
        If two different submodules of a package are imported, no duplicate
        import warning is reported for the package.
        """
        self.flakes('''
        import fu.bar, fu.baz
        fu.bar, fu.baz
        ''')
        self.flakes('''
        import fu.bar
        import fu.baz
        fu.bar, fu.baz
        ''')

    def test_assignRHSFirst(self):
        self.flakes('import fu; fu = fu')
        self.flakes('import fu; fu, bar = fu')
        self.flakes('import fu; [fu, bar] = fu')
        self.flakes('import fu; fu += fu')

    def test_tryingMultipleImports(self):
        self.flakes('''
        try:
            import fu
        except ImportError:
            import bar as fu
        fu
        ''')

    def test_nonGlobalDoesNotRedefine(self):
        self.flakes('''
        import fu
        def a():
            fu = 3
            return fu
        fu
        ''')

    def test_functionsRunLater(self):
        self.flakes('''
        def a():
            fu
        import fu
        ''')

    def test_functionNamesAreBoundNow(self):
        self.flakes('''
        import fu
        def fu():
            fu
        fu
        ''', m.RedefinedWhileUnused)

    def test_ignoreNonImportRedefinitions(self):
        self.flakes('a = 1; a = 2')

    @skip("todo")
    def test_importingForImportError(self):
        self.flakes('''
        try:
            import fu
        except ImportError:
            pass
        ''')

    @skip("todo: requires evaluating attribute access")
    def test_importedInClass(self):
        """Imports in class scope can be used through self."""
        self.flakes('''
        class c:
            import i
            def __init__(self):
                self.i
        ''')

    def test_futureImport(self):
        """__future__ is special."""
        self.flakes('from __future__ import division')
        self.flakes('''
        "docstring is allowed before future import"
        from __future__ import division
        ''')

    def test_futureImportFirst(self):
        """
        __future__ imports must come before anything else.
        """
        self.flakes('''
        x = 5
        from __future__ import division
        ''', m.LateFutureImport)
        self.flakes('''
        from foo import bar
        from __future__ import division
        bar
        ''', m.LateFutureImport)


class TestSpecialAll(TestCase):
    """
    Tests for suppression of unused import warnings by C{__all__}.
    """
    def test_ignoredInFunction(self):
        """
        An C{__all__} definition does not suppress unused import warnings in a
        function scope.
        """
        self.flakes('''
        def foo():
            import bar
            __all__ = ["bar"]
        ''', m.UnusedImport, m.UnusedVariable)

    def test_ignoredInClass(self):
        """
        An C{__all__} definition does not suppress unused import warnings in a
        class scope.
        """
        self.flakes('''
        class foo:
            import bar
            __all__ = ["bar"]
        ''', m.UnusedImport)

    def test_warningSuppressed(self):
        """
        If a name is imported and unused but is named in C{__all__}, no warning
        is reported.
        """
        self.flakes('''
        import foo
        __all__ = ["foo"]
        ''')

    def test_unrecognizable(self):
        """
        If C{__all__} is defined in a way that can't be recognized statically,
        it is ignored.
        """
        self.flakes('''
        import foo
        __all__ = ["f" + "oo"]
        ''', m.UnusedImport)
        self.flakes('''
        import foo
        __all__ = [] + ["foo"]
        ''', m.UnusedImport)

    def test_unboundExported(self):
        """
        If C{__all__} includes a name which is not bound, a warning is emitted.
        """
        self.flakes('''
        __all__ = ["foo"]
        ''', m.UndefinedExport)

        # Skip this in __init__.py though, since the rules there are a little
        # different.
        for filename in ["foo/__init__.py", "__init__.py"]:
            self.flakes('''
            __all__ = ["foo"]
            ''', filename=filename)

    def test_importStarExported(self):
        """
        Do not report undefined if import * is used
        """
        self.flakes('''
        from foolib import *
        __all__ = ["foo"]
        ''', m.ImportStarUsed)

    def test_usedInGenExp(self):
        """
        Using a global in a generator expression results in no warnings.
        """
        self.flakes('import fu; (fu for _ in range(1))')
        self.flakes('import fu; (1 for _ in range(1) if fu)')

    def test_redefinedByGenExp(self):
        """
        Re-using a global name as the loop variable for a generator
        expression results in a redefinition warning.
        """
        self.flakes('import fu; (1 for fu in range(1))',
                    m.RedefinedWhileUnused, m.UnusedImport)

    def test_usedAsDecorator(self):
        """
        Using a global name in a decorator statement results in no warnings,
        but using an undefined name in a decorator statement results in an
        undefined name warning.
        """
        self.flakes('''
        from interior import decorate
        @decorate
        def f():
            return "hello"
        ''')

        self.flakes('''
        from interior import decorate
        @decorate('value')
        def f():
            return "hello"
        ''')

        self.flakes('''
        @decorate
        def f():
            return "hello"
        ''', m.UndefinedName)


class Python26Tests(TestCase):
    """
    Tests for checking of syntax which is valid in PYthon 2.6 and newer.
    """

    @skipIf(version_info < (2, 6), "Python >= 2.6 only")
    def test_usedAsClassDecorator(self):
        """
        Using an imported name as a class decorator results in no warnings,
        but using an undefined name as a class decorator results in an
        undefined name warning.
        """
        self.flakes('''
        from interior import decorate
        @decorate
        class foo:
            pass
        ''')

        self.flakes('''
        from interior import decorate
        @decorate("foo")
        class bar:
            pass
        ''')

        self.flakes('''
        @decorate
        class foo:
            pass
        ''', m.UndefinedName)

########NEW FILE########
__FILENAME__ = test_other
"""
Tests for various Pyflakes behavior.
"""

from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skip, skipIf


class Test(TestCase):

    def test_duplicateArgs(self):
        self.flakes('def fu(bar, bar): pass', m.DuplicateArgument)

    @skip("todo: this requires finding all assignments in the function body first")
    def test_localReferencedBeforeAssignment(self):
        self.flakes('''
        a = 1
        def f():
            a; a=1
        f()
        ''', m.UndefinedName)

    def test_redefinedInListComp(self):
        """
        Test that shadowing a variable in a list comprehension raises
        a warning.
        """
        self.flakes('''
        a = 1
        [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        class A:
            a = 1
            [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        def f():
            a = 1
            [1 for a, b in [(1, 2)]]
        ''', m.RedefinedInListComp)
        self.flakes('''
        [1 for a, b in [(1, 2)]]
        [1 for a, b in [(1, 2)]]
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        [1 for a, b in [(1, 2)]]
        ''')

    def test_redefinedInGenerator(self):
        """
        Test that reusing a variable in a generator does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        (1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        class A:
            a = 1
            list(1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        def f():
            a = 1
            (1 for a, b in [(1, 2)])
        ''', m.UnusedVariable)
        self.flakes('''
        (1 for a, b in [(1, 2)])
        (1 for a, b in [(1, 2)])
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        (1 for a, b in [(1, 2)])
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_redefinedInSetComprehension(self):
        """
        Test that reusing a variable in a set comprehension does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        class A:
            a = 1
            {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        def f():
            a = 1
            {1 for a, b in [(1, 2)]}
        ''', m.UnusedVariable)
        self.flakes('''
        {1 for a, b in [(1, 2)]}
        {1 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        {1 for a, b in [(1, 2)]}
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_redefinedInDictComprehension(self):
        """
        Test that reusing a variable in a dict comprehension does not raise
        a warning.
        """
        self.flakes('''
        a = 1
        {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        class A:
            a = 1
            {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        def f():
            a = 1
            {1: 42 for a, b in [(1, 2)]}
        ''', m.UnusedVariable)
        self.flakes('''
        {1: 42 for a, b in [(1, 2)]}
        {1: 42 for a, b in [(1, 2)]}
        ''')
        self.flakes('''
        for a, b in [(1, 2)]:
            pass
        {1: 42 for a, b in [(1, 2)]}
        ''')

    def test_redefinedFunction(self):
        """
        Test that shadowing a function definition with another one raises a
        warning.
        """
        self.flakes('''
        def a(): pass
        def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedClassFunction(self):
        """
        Test that shadowing a function definition in a class suite with another
        one raises a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedIfElseFunction(self):
        """
        Test that shadowing a function definition twice in an if
        and else block does not raise a warning.
        """
        self.flakes('''
        if True:
            def a(): pass
        else:
            def a(): pass
        ''')

    def test_redefinedIfFunction(self):
        """
        Test that shadowing a function definition within an if block
        raises a warning.
        """
        self.flakes('''
        if True:
            def a(): pass
            def a(): pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedTryExceptFunction(self):
        """
        Test that shadowing a function definition twice in try
        and except block does not raise a warning.
        """
        self.flakes('''
        try:
            def a(): pass
        except:
            def a(): pass
        ''')

    def test_redefinedTryFunction(self):
        """
        Test that shadowing a function definition within a try block
        raises a warning.
        """
        self.flakes('''
        try:
            def a(): pass
            def a(): pass
        except:
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedIfElseInListComp(self):
        """
        Test that shadowing a variable in a list comprehension in
        an if and else block does not raise a warning.
        """
        self.flakes('''
        if False:
            a = 1
        else:
            [a for a in '12']
        ''')

    def test_redefinedElseInListComp(self):
        """
        Test that shadowing a variable in a list comprehension in
        an else (or if) block raises a warning.
        """
        self.flakes('''
        if False:
            pass
        else:
            a = 1
            [a for a in '12']
        ''', m.RedefinedInListComp)

    def test_functionDecorator(self):
        """
        Test that shadowing a function definition with a decorated version of
        that function does not raise a warning.
        """
        self.flakes('''
        from somewhere import somedecorator

        def a(): pass
        a = somedecorator(a)
        ''')

    def test_classFunctionDecorator(self):
        """
        Test that shadowing a function definition in a class suite with a
        decorated version of that function does not raise a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            a = classmethod(a)
        ''')

    @skipIf(version_info < (2, 6), "Python >= 2.6 only")
    def test_modernProperty(self):
        self.flakes("""
        class A:
            @property
            def t(self):
                pass
            @t.setter
            def t(self, value):
                pass
            @t.deleter
            def t(self):
                pass
        """)

    def test_unaryPlus(self):
        """Don't die on unary +."""
        self.flakes('+1')

    def test_undefinedBaseClass(self):
        """
        If a name in the base list of a class definition is undefined, a
        warning is emitted.
        """
        self.flakes('''
        class foo(foo):
            pass
        ''', m.UndefinedName)

    def test_classNameUndefinedInClassBody(self):
        """
        If a class name is used in the body of that class's definition and
        the name is not already defined, a warning is emitted.
        """
        self.flakes('''
        class foo:
            foo
        ''', m.UndefinedName)

    def test_classNameDefinedPreviously(self):
        """
        If a class name is used in the body of that class's definition and
        the name was previously defined in some other way, no warning is
        emitted.
        """
        self.flakes('''
        foo = None
        class foo:
            foo
        ''')

    def test_classRedefinition(self):
        """
        If a class is defined twice in the same module, a warning is emitted.
        """
        self.flakes('''
        class Foo:
            pass
        class Foo:
            pass
        ''', m.RedefinedWhileUnused)

    def test_functionRedefinedAsClass(self):
        """
        If a function is redefined as a class, a warning is emitted.
        """
        self.flakes('''
        def Foo():
            pass
        class Foo:
            pass
        ''', m.RedefinedWhileUnused)

    def test_classRedefinedAsFunction(self):
        """
        If a class is redefined as a function, a warning is emitted.
        """
        self.flakes('''
        class Foo:
            pass
        def Foo():
            pass
        ''', m.RedefinedWhileUnused)

    @skip("todo: Too hard to make this warn but other cases stay silent")
    def test_doubleAssignment(self):
        """
        If a variable is re-assigned to without being used, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        x = 20
        ''', m.RedefinedWhileUnused)

    def test_doubleAssignmentConditionally(self):
        """
        If a variable is re-assigned within a conditional, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        if True:
            x = 20
        ''')

    def test_doubleAssignmentWithUse(self):
        """
        If a variable is re-assigned to after being used, no warning is
        emitted.
        """
        self.flakes('''
        x = 10
        y = x * 2
        x = 20
        ''')

    def test_comparison(self):
        """
        If a defined name is used on either side of any of the six comparison
        operators, no warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x < y
        x <= y
        x == y
        x != y
        x >= y
        x > y
        ''')

    def test_identity(self):
        """
        If a defined name is used on either side of an identity test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x is y
        x is not y
        ''')

    def test_containment(self):
        """
        If a defined name is used on either side of a containment test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x in y
        x not in y
        ''')

    def test_loopControl(self):
        """
        break and continue statements are supported.
        """
        self.flakes('''
        for x in [1, 2]:
            break
        ''')
        self.flakes('''
        for x in [1, 2]:
            continue
        ''')

    def test_ellipsis(self):
        """
        Ellipsis in a slice is supported.
        """
        self.flakes('''
        [1, 2][...]
        ''')

    def test_extendedSlice(self):
        """
        Extended slices are supported.
        """
        self.flakes('''
        x = 3
        [1, 2][x,:]
        ''')

    def test_varAugmentedAssignment(self):
        """
        Augmented assignment of a variable is supported.
        We don't care about var refs.
        """
        self.flakes('''
        foo = 0
        foo += 1
        ''')

    def test_attrAugmentedAssignment(self):
        """
        Augmented assignment of attributes is supported.
        We don't care about attr refs.
        """
        self.flakes('''
        foo = None
        foo.bar += foo.baz
        ''')


class TestUnusedAssignment(TestCase):
    """
    Tests for warning about unused assignments.
    """

    def test_unusedVariable(self):
        """
        Warn when a variable in a function is assigned a value that's never
        used.
        """
        self.flakes('''
        def a():
            b = 1
        ''', m.UnusedVariable)

    def test_unusedVariableAsLocals(self):
        """
        Using locals() it is perfectly valid to have unused variables
        """
        self.flakes('''
        def a():
            b = 1
            return locals()
        ''')

    def test_unusedVariableNoLocals(self):
        """
        Using locals() in wrong scope should not matter
        """
        self.flakes('''
        def a():
            locals()
            def a():
                b = 1
                return
        ''', m.UnusedVariable)

    def test_assignToGlobal(self):
        """
        Assigning to a global and then not using that global is perfectly
        acceptable. Do not mistake it for an unused local variable.
        """
        self.flakes('''
        b = 0
        def a():
            global b
            b = 1
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_assignToNonlocal(self):
        """
        Assigning to a nonlocal and then not using that binding is perfectly
        acceptable. Do not mistake it for an unused local variable.
        """
        self.flakes('''
        b = b'0'
        def a():
            nonlocal b
            b = b'1'
        ''')

    def test_assignToMember(self):
        """
        Assigning to a member of another object and then not using that member
        variable is perfectly acceptable. Do not mistake it for an unused
        local variable.
        """
        # XXX: Adding this test didn't generate a failure. Maybe not
        # necessary?
        self.flakes('''
        class b:
            pass
        def a():
            b.foo = 1
        ''')

    def test_assignInForLoop(self):
        """
        Don't warn when a variable in a for loop is assigned to but not used.
        """
        self.flakes('''
        def f():
            for i in range(10):
                pass
        ''')

    def test_assignInListComprehension(self):
        """
        Don't warn when a variable in a list comprehension is
        assigned to but not used.
        """
        self.flakes('''
        def f():
            [None for i in range(10)]
        ''')

    def test_generatorExpression(self):
        """
        Don't warn when a variable in a generator expression is
        assigned to but not used.
        """
        self.flakes('''
        def f():
            (None for i in range(10))
        ''')

    def test_assignmentInsideLoop(self):
        """
        Don't warn when a variable assignment occurs lexically after its use.
        """
        self.flakes('''
        def f():
            x = None
            for i in range(10):
                if i > 2:
                    return x
                x = i * 2
        ''')

    def test_tupleUnpacking(self):
        """
        Don't warn when a variable included in tuple unpacking is unused. It's
        very common for variables in a tuple unpacking assignment to be unused
        in good Python code, so warning will only create false positives.
        """
        self.flakes('''
        def f():
            (x, y) = 1, 2
        ''')

    def test_listUnpacking(self):
        """
        Don't warn when a variable included in list unpacking is unused.
        """
        self.flakes('''
        def f():
            [x, y] = [1, 2]
        ''')

    def test_closedOver(self):
        """
        Don't warn when the assignment is used in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                return foo
            return bar
        ''')

    def test_doubleClosedOver(self):
        """
        Don't warn when the assignment is used in an inner function, even if
        that inner function itself is in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                def baz():
                    return foo
            return bar
        ''')

    def test_tracebackhideSpecialVariable(self):
        """
        Do not warn about unused local variable __tracebackhide__, which is
        a special variable for py.test.
        """
        self.flakes("""
            def helper():
                __tracebackhide__ = True
        """)

    def test_ifexp(self):
        """
        Test C{foo if bar else baz} statements.
        """
        self.flakes("a = 'moo' if True else 'oink'")
        self.flakes("a = foo if True else 'oink'", m.UndefinedName)
        self.flakes("a = 'moo' if True else bar", m.UndefinedName)

    def test_withStatementNoNames(self):
        """
        No warnings are emitted for using inside or after a nameless C{with}
        statement a name defined beforehand.
        """
        self.flakes('''
        from __future__ import with_statement
        bar = None
        with open("foo"):
            bar
        bar
        ''')

    def test_withStatementSingleName(self):
        """
        No warnings are emitted for using a name defined by a C{with} statement
        within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            bar
        bar
        ''')

    def test_withStatementAttributeName(self):
        """
        No warnings are emitted for using an attribute as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo.bar:
            pass
        ''')

    def test_withStatementSubscript(self):
        """
        No warnings are emitted for using a subscript as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[0]:
            pass
        ''')

    def test_withStatementSubscriptUndefined(self):
        """
        An undefined name warning is emitted if the subscript used as the
        target of a C{with} statement is not defined.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[bar]:
            pass
        ''', m.UndefinedName)

    def test_withStatementTupleNames(self):
        """
        No warnings are emitted for using any of the tuple of names defined by
        a C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as (bar, baz):
            bar, baz
        bar, baz
        ''')

    def test_withStatementListNames(self):
        """
        No warnings are emitted for using any of the list of names defined by a
        C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as [bar, baz]:
            bar, baz
        bar, baz
        ''')

    def test_withStatementComplicatedTarget(self):
        """
        If the target of a C{with} statement uses any or all of the valid forms
        for that part of the grammar (See
        U{http://docs.python.org/reference/compound_stmts.html#the-with-statement}),
        the names involved are checked both for definedness and any bindings
        created are respected in the suite of the statement and afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        c = d = e = g = h = i = None
        with open('foo') as [(a, b), c[d], e.f, g[h:i]]:
            a, b, c, d, e, g, h, i
        a, b, c, d, e, g, h, i
        ''')

    def test_withStatementSingleNameUndefined(self):
        """
        An undefined name warning is emitted if the name first defined by a
        C{with} statement is used before the C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        bar
        with open('foo') as bar:
            pass
        ''', m.UndefinedName)

    def test_withStatementTupleNamesUndefined(self):
        """
        An undefined name warning is emitted if a name first defined by a the
        tuple-unpacking form of the C{with} statement is used before the
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        baz
        with open('foo') as (bar, baz):
            pass
        ''', m.UndefinedName)

    def test_withStatementSingleNameRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by the name defined by a C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as bar:
            pass
        ''', m.RedefinedWhileUnused)

    def test_withStatementTupleNamesRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by one of the names defined by the tuple-unpacking form of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as (bar, baz):
            pass
        ''', m.RedefinedWhileUnused)

    def test_withStatementUndefinedInside(self):
        """
        An undefined name warning is emitted if a name is used inside the
        body of a C{with} statement without first being bound.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz
        ''', m.UndefinedName)

    def test_withStatementNameDefinedInBody(self):
        """
        A name defined in the body of a C{with} statement can be used after
        the body ends without warning.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz = 10
        baz
        ''')

    def test_withStatementUndefinedInExpression(self):
        """
        An undefined name warning is emitted if a name in the I{test}
        expression of a C{with} statement is undefined.
        """
        self.flakes('''
        from __future__ import with_statement
        with bar as baz:
            pass
        ''', m.UndefinedName)

        self.flakes('''
        from __future__ import with_statement
        with bar as bar:
            pass
        ''', m.UndefinedName)

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_dictComprehension(self):
        """
        Dict comprehensions are properly handled.
        """
        self.flakes('''
        a = {1: x for x in range(10)}
        ''')

    @skipIf(version_info < (2, 7), "Python >= 2.7 only")
    def test_setComprehensionAndLiteral(self):
        """
        Set comprehensions are properly handled.
        """
        self.flakes('''
        a = {1, 2, 3}
        b = {x for x in range(10)}
        ''')

    def test_exceptionUsedInExcept(self):
        as_exc = ', ' if version_info < (2, 6) else ' as '
        self.flakes('''
        try: pass
        except Exception%se: e
        ''' % as_exc)

        self.flakes('''
        def download_review():
            try: pass
            except Exception%se: e
        ''' % as_exc)

    def test_exceptWithoutNameInFunction(self):
        """
        Don't issue false warning when an unnamed exception is used.
        Previously, there would be a false warning, but only when the
        try..except was in a function
        """
        self.flakes('''
        import tokenize
        def foo():
            try: pass
            except tokenize.TokenError: pass
        ''')

    def test_exceptWithoutNameInFunctionTuple(self):
        """
        Don't issue false warning when an unnamed exception is used.
        This example catches a tuple of exception types.
        """
        self.flakes('''
        import tokenize
        def foo():
            try: pass
            except (tokenize.TokenError, IndentationError): pass
        ''')

    def test_augmentedAssignmentImportedFunctionCall(self):
        """
        Consider a function that is called on the right part of an
        augassign operation to be used.
        """
        self.flakes('''
        from foo import bar
        baz = 0
        baz += bar()
        ''')

    @skipIf(version_info < (3, 3), 'new in Python 3.3')
    def test_yieldFromUndefined(self):
        """
        Test C{yield from} statement
        """
        self.flakes('''
        def bar():
            yield from foo()
        ''', m.UndefinedName)

########NEW FILE########
__FILENAME__ = test_undefined_names

from _ast import PyCF_ONLY_AST
from sys import version_info

from pyflakes import messages as m, checker
from pyflakes.test.harness import TestCase, skip, skipIf


class Test(TestCase):
    def test_undefined(self):
        self.flakes('bar', m.UndefinedName)

    def test_definedInListComp(self):
        self.flakes('[a for a in range(10) if a]')

    def test_functionsNeedGlobalScope(self):
        self.flakes('''
        class a:
            def b():
                fu
        fu = 1
        ''')

    def test_builtins(self):
        self.flakes('range(10)')

    def test_builtinWindowsError(self):
        """
        C{WindowsError} is sometimes a builtin name, so no warning is emitted
        for using it.
        """
        self.flakes('WindowsError')

    def test_magicGlobalsFile(self):
        """
        Use of the C{__file__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__file__')

    def test_magicGlobalsBuiltins(self):
        """
        Use of the C{__builtins__} magic global should not emit an undefined
        name warning.
        """
        self.flakes('__builtins__')

    def test_magicGlobalsName(self):
        """
        Use of the C{__name__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__name__')

    def test_magicGlobalsPath(self):
        """
        Use of the C{__path__} magic global should not emit an undefined name
        warning, if you refer to it from a file called __init__.py.
        """
        self.flakes('__path__', m.UndefinedName)
        self.flakes('__path__', filename='package/__init__.py')

    def test_globalImportStar(self):
        """Can't find undefined names with import *."""
        self.flakes('from fu import *; bar', m.ImportStarUsed)

    def test_localImportStar(self):
        """
        A local import * still allows undefined names to be found
        in upper scopes.
        """
        self.flakes('''
        def a():
            from fu import *
        bar
        ''', m.ImportStarUsed, m.UndefinedName)

    @skipIf(version_info >= (3,), 'obsolete syntax')
    def test_unpackedParameter(self):
        """Unpacked function parameters create bindings."""
        self.flakes('''
        def a((bar, baz)):
            bar; baz
        ''')

    @skip("todo")
    def test_definedByGlobal(self):
        """
        "global" can make an otherwise undefined name in another function
        defined.
        """
        self.flakes('''
        def a(): global fu; fu = 1
        def b(): fu
        ''')

    def test_globalInGlobalScope(self):
        """
        A global statement in the global scope is ignored.
        """
        self.flakes('''
        global x
        def foo():
            print(x)
        ''', m.UndefinedName)

    def test_del(self):
        """Del deletes bindings."""
        self.flakes('a = 1; del a; a', m.UndefinedName)

    def test_delGlobal(self):
        """Del a global binding from a function."""
        self.flakes('''
        a = 1
        def f():
            global a
            del a
        a
        ''')

    def test_delUndefined(self):
        """Del an undefined name."""
        self.flakes('del a', m.UndefinedName)

    def test_globalFromNestedScope(self):
        """Global names are available from nested scopes."""
        self.flakes('''
        a = 1
        def b():
            def c():
                a
        ''')

    def test_laterRedefinedGlobalFromNestedScope(self):
        """
        Test that referencing a local name that shadows a global, before it is
        defined, generates a warning.
        """
        self.flakes('''
        a = 1
        def fun():
            a
            a = 2
            return a
        ''', m.UndefinedLocal)

    def test_laterRedefinedGlobalFromNestedScope2(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global declared in an enclosing scope, before it is defined, generates
        a warning.
        """
        self.flakes('''
            a = 1
            def fun():
                global a
                def fun2():
                    a
                    a = 2
                    return a
        ''', m.UndefinedLocal)

    def test_intermediateClassScopeIgnored(self):
        """
        If a name defined in an enclosing scope is shadowed by a local variable
        and the name is used locally before it is bound, an unbound local
        warning is emitted, even if there is a class scope between the enclosing
        scope and the local scope.
        """
        self.flakes('''
        def f():
            x = 1
            class g:
                def h(self):
                    a = x
                    x = None
                    print(x, a)
            print(x)
        ''', m.UndefinedLocal)

    def test_doubleNestingReportsClosestName(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        variable declared in two different outer scopes before it is defined
        in the innermost scope generates an UnboundLocal warning which
        refers to the nearest shadowed name.
        """
        exc = self.flakes('''
            def a():
                x = 1
                def b():
                    x = 2 # line 5
                    def c():
                        x
                        x = 3
                        return x
                    return x
                return x
        ''', m.UndefinedLocal).messages[0]
        self.assertEqual(exc.message_args, ('x', 5))

    def test_laterRedefinedGlobalFromNestedScope3(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global, before it is defined, generates a warning.
        """
        self.flakes('''
            def fun():
                a = 1
                def fun2():
                    a
                    a = 1
                    return a
                return a
        ''', m.UndefinedLocal)

    def test_undefinedAugmentedAssignment(self):
        self.flakes(
            '''
            def f(seq):
                a = 0
                seq[a] += 1
                seq[b] /= 2
                c[0] *= 2
                a -= 3
                d += 4
                e[any] = 5
            ''',
            m.UndefinedName,    # b
            m.UndefinedName,    # c
            m.UndefinedName, m.UnusedVariable,  # d
            m.UndefinedName,    # e
        )

    def test_nestedClass(self):
        """Nested classes can access enclosing scope."""
        self.flakes('''
        def f(foo):
            class C:
                bar = foo
                def f(self):
                    return foo
            return C()

        f(123).f()
        ''')

    def test_badNestedClass(self):
        """Free variables in nested classes must bind at class creation."""
        self.flakes('''
        def f():
            class C:
                bar = foo
            foo = 456
            return foo
        f()
        ''', m.UndefinedName)

    def test_definedAsStarArgs(self):
        """Star and double-star arg names are defined."""
        self.flakes('''
        def f(a, *b, **c):
            print(a, b, c)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_definedAsStarUnpack(self):
        """Star names in unpack are defined."""
        self.flakes('''
        a, *b = range(10)
        print(a, b)
        ''')
        self.flakes('''
        *a, b = range(10)
        print(a, b)
        ''')
        self.flakes('''
        a, *b, c = range(10)
        print(a, b, c)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_keywordOnlyArgs(self):
        """Keyword-only arg names are defined."""
        self.flakes('''
        def f(*, a, b=None):
            print(a, b)
        ''')

        self.flakes('''
        import default_b
        def f(*, a, b=default_b):
            print(a, b)
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_keywordOnlyArgsUndefined(self):
        """Typo in kwonly name."""
        self.flakes('''
        def f(*, a, b=default_c):
            print(a, b)
        ''', m.UndefinedName)

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_annotationUndefined(self):
        """Undefined annotations."""
        self.flakes('''
        from abc import note1, note2, note3, note4, note5
        def func(a: note1, *args: note2,
                 b: note3=12, **kw: note4) -> note5: pass
        ''')

        self.flakes('''
        def func():
            d = e = 42
            def func(a: {1, d}) -> (lambda c: e): pass
        ''')

    @skipIf(version_info < (3,), 'new in Python 3')
    def test_metaClassUndefined(self):
        self.flakes('''
        from abc import ABCMeta
        class A(metaclass=ABCMeta): pass
        ''')

    def test_definedInGenExp(self):
        """
        Using the loop variable of a generator expression results in no
        warnings.
        """
        self.flakes('(a for a in %srange(10) if a)' %
                    ('x' if version_info < (3,) else ''))

    def test_undefinedWithErrorHandler(self):
        """
        Some compatibility code checks explicitly for NameError.
        It should not trigger warnings.
        """
        self.flakes('''
        try:
            socket_map
        except NameError:
            socket_map = {}
        ''')
        self.flakes('''
        try:
            _memoryview.contiguous
        except (NameError, AttributeError):
            raise RuntimeError("Python >= 3.3 is required")
        ''')
        # If NameError is not explicitly handled, generate a warning
        self.flakes('''
        try:
            socket_map
        except:
            socket_map = {}
        ''', m.UndefinedName)
        self.flakes('''
        try:
            socket_map
        except Exception:
            socket_map = {}
        ''', m.UndefinedName)

    def test_definedInClass(self):
        """
        Defined name for generator expressions and dict/set comprehension.
        """
        self.flakes('''
        class A:
            T = range(10)

            Z = (x for x in T)
            L = [x for x in T]
            B = dict((i, str(i)) for i in T)
        ''')

        if version_info >= (2, 7):
            self.flakes('''
            class A:
                T = range(10)

                X = {x for x in T}
                Y = {x:x for x in T}
            ''')


class NameTests(TestCase):
    """
    Tests for some extra cases of name handling.
    """
    def test_impossibleContext(self):
        """
        A Name node with an unrecognized context results in a RuntimeError being
        raised.
        """
        tree = compile("x = 10", "<test>", "exec", PyCF_ONLY_AST)
        # Make it into something unrecognizable.
        tree.body[0].targets[0].ctx = object()
        self.assertRaises(RuntimeError, checker.Checker, tree)

########NEW FILE########
__FILENAME__ = __main__
from pyflakes.api import main

# python -m pyflakes (with Python >= 2.7)
if __name__ == '__main__':
    main(prog='pyflakes')

########NEW FILE########
__FILENAME__ = Flake8Lint
# -*- coding: utf-8 -*-
"""
Flake8Lint: Sublime Text 2 plugin.
Check Python files with flake8 (PEP8, pyflake and mccabe)
"""
import os
import sys
from fnmatch import fnmatch

import sublime
import sublime_plugin

try:
    from .lint import lint, lint_external, skip_file, load_flake8_config
except (ValueError, SystemError):
    from lint import lint, lint_external, skip_file, load_flake8_config  # noqa


settings = None
debug_enabled = False
PROJECT_SETTINGS_KEYS = (
    'python_interpreter', 'builtins', 'pyflakes', 'pep8', 'complexity',
    'pep8_max_line_length', 'select', 'ignore', 'ignore_files',
    'use_flake8_global_config', 'use_flake8_project_config',
)
FLAKE8_SETTINGS_KEYS = (
    'ignore', 'select', 'ignore_files', 'pep8_max_line_length'
)

ERRORS_IN_VIEWS = {}
FLAKE_DIR = os.path.dirname(os.path.abspath(__file__))


def debug(msg):
    """
    Print debug info to ST python console if debug is enabled.
    """
    if not debug_enabled:
        return
    print("[Flake8Lint DEBUG] {0}".format(msg))


def plugin_loaded():
    """
    Callback for 'plugin was loaded' event.
    Load settings.
    """
    global settings
    global debug_enabled
    settings = sublime.load_settings("Flake8Lint.sublime-settings")
    if settings.get('debug', False):
        debug_enabled = True
        debug("plugin was loaded")


# Backwards compatibility with Sublime 2
# sublime.version isn't available at module import time in Sublime 3
if sys.version_info[0] == 2:
    plugin_loaded()


def skip_line(line):
    """
    Check if we need to skip line check.
    Line must ends with '# noqa' or '# NOQA' comment.
    """
    def _noqa(line):
        return line.strip().lower().endswith('# noqa')
    skip = _noqa(line)
    if not skip:
        i = line.rfind(' #')
        skip = _noqa(line[:i]) if i > 0 else False
    if skip:
        debug("skip line '{0}'".format(line))
    return skip


def get_current_line(view):
    """
    Get current line (line under cursor).
    """
    # get view selection (exit if no selection)
    view_selection = view.sel()
    if not view_selection:
        return None

    point = view_selection[0].end()
    position = view.rowcol(point)
    return position[0]


def clear_statusbar(view):
    """
    Clear status bar flake8 error.
    """
    view.erase_status('flake8-tip')


def update_statusbar(view):
    """
    Update status bar with error.
    """
    # get view errors (exit if no errors found)
    view_errors = ERRORS_IN_VIEWS.get(view.id())
    if view_errors is None:
        return

    # get view selection (exit if no selection)
    view_selection = view.sel()
    if not view_selection:
        return

    current_line = get_current_line(view)
    if current_line is None:
        return

    if current_line in view_errors:
        # there is an error on current line
        errors = view_errors[current_line]
        view.set_status('flake8-tip', 'flake8: %s' % ' / '.join(errors))
    else:
        # no errors - clear statusbar
        clear_statusbar(view)


def get_view_settings(view):
    """
    Returns dict with view settings.

    Settings are taken from (see README for more info):
    - ST plugin settings (global, user, project)
    - flake8 settings (global, project)
    """
    result_settings = {}

    # get settings from global (user) plugin settings
    view_settings = view.settings().get('flake8lint') or {}
    for param in PROJECT_SETTINGS_KEYS:
        if param in view_settings:
            result_settings[param] = view_settings.get(param)
        elif settings.has(param):
            result_settings[param] = settings.get(param)

    global_config = result_settings.get('use_flake8_global_config', False)
    project_config = result_settings.get('use_flake8_project_config', False)

    if global_config or project_config:
        filename = os.path.abspath(view.file_name())

        flake8_config = load_flake8_config(filename, global_config,
                                           project_config)
        for param in FLAKE8_SETTINGS_KEYS:
            if param in flake8_config:
                result_settings[param] = flake8_config.get(param)

    return result_settings


def filename_match(filename, patterns):
    """
    Returns True if filename is matched with patterns.
    """
    for path_part in filename.split(os.path.sep):
        if any(fnmatch(path_part, pattern) for pattern in patterns):
            return True
    return False


class Flake8NextErrorCommand(sublime_plugin.TextCommand):
    """
    Jump to next lint error command.
    """
    def run(self, edit):
        """
        Jump to next lint error.
        """
        debug("jump to next lint error")

        view_errors = ERRORS_IN_VIEWS.get(self.view.id())
        if not view_errors:
            debug("no view errors found")
            return

        # get view selection (exit if no selection)
        view_selection = self.view.sel()
        if not view_selection:
            return

        current_line = get_current_line(self.view)
        if current_line is None:
            return

        next_line = None
        for i, error_line in enumerate(sorted(view_errors.keys())):
            if i == 0:
                next_line = error_line
            if error_line > current_line:
                next_line = error_line
                break

        debug("jump to line {0}".format(next_line))

        point = self.view.text_point(next_line, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point)


class Flake8LintCommand(sublime_plugin.TextCommand):
    """
    Do flake8 lint on current file.
    """
    def run(self, edit):
        """
        Run flake8 lint.
        """
        debug("run flake8 lint")
        # check if active view contains file
        filename = self.view.file_name()
        if not filename:
            debug("skip view: filename is empty")
            return

        filename = os.path.abspath(filename)

        # check only Python files
        if not self.view.match_selector(0, 'source.python'):
            debug("skip file: view source type is not 'python'")
            return

        # skip file check if 'noqa' for whole file is set
        if skip_file(filename):
            debug("skip file: 'noqa' is set")
            return

        # we need to always clear regions. three situations here:
        # - we need to clear regions with fixed previous errors
        # - is user will turn off 'highlight' in settings and then run lint
        # - user adds file with errors to 'ignore_files' list
        self.view.erase_regions('flake8-errors')

        # we need to always erase status too. same situations.
        self.view.erase_status('flake8-tip')

        # get view settings
        view_settings = get_view_settings(self.view)

        # skip files by pattern
        patterns = view_settings.get('ignore_files')
        debug("ignore file patterns: {0}".format(patterns))
        if patterns:
            # add file basename to check list
            paths = [os.path.basename(filename)]

            # add file relative paths to check list
            for folder in sublime.active_window().folders():
                folder_name = folder.rstrip(os.path.sep) + os.path.sep
                if filename.startswith(folder_name):
                    paths.append(filename[len(folder_name):])

            try:
                if any(filename_match(path, patterns) for path in set(paths)):
                    message = "File '{0}' lint was skipped by 'ignore' setting"
                    print(message.format(filename))
                    return
            except (TypeError, ValueError):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "'ignore_files' option is not a list of file masks"
                )

        # save file if dirty
        if self.view.is_dirty():
            debug("save file before lint, because view is 'dirty'")
            self.view.run_command('save')

        # try to get interpreter
        interpreter = view_settings.get('python_interpreter', 'auto')
        debug("python interpreter: {0}".format(interpreter))

        if not interpreter or interpreter == 'internal':
            # if interpreter is Sublime Text 2 internal python - lint file
            debug("interpreter is internal")
            self.errors_list = lint(filename, view_settings)
        else:
            # else - check interpreter
            debug("interpreter is external")
            if interpreter == 'auto':
                if os.name == 'nt':
                    interpreter = 'pythonw'
                else:
                    interpreter = 'python'
                debug("guess interpreter: '{0}'".format(interpreter))
            elif not os.path.exists(interpreter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "python interpreter '%s' is not found" % interpreter
                )

            # build linter path for Packages Manager installation
            linter = os.path.join(FLAKE_DIR, 'lint.py')
            debug("linter file: {0}".format(linter))

            # build linter path for installation from git
            if not os.path.exists(linter):
                linter = os.path.join(
                    sublime.packages_path(), 'Python Flake8 Lint', 'lint.py')
                debug("linter is not exists, try this: {0}".format(linter))

            if not os.path.exists(linter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "sorry, can't find correct plugin path"
                )

            # and lint file in subprocess
            debug("interpreter is external")
            self.errors_list = lint_external(filename, view_settings,
                                             interpreter, linter)

        debug("lint errors found: {0}".format(len(self.errors_list)))
        # show errors
        if self.errors_list:
            self.show_errors(view_settings)
        elif settings.get('report_on_success', False):
            sublime.message_dialog('Flake8 Lint: SUCCESS')

    def show_errors(self, view_settings):
        """
        Show all errors.
        """
        debug("show flake8 lint errors")
        errors_to_show = []

        # get error report settings
        select = view_settings.get('select') or []
        ignore = view_settings.get('ignore') or []
        is_highlight = settings.get('highlight', False)
        is_popup = settings.get('popup', True)

        mark = settings.get('gutter_marks', '')
        if mark not in ('', 'dot', 'circle', 'bookmark', 'cross'):
            mark = ''

        debug("'select' setting: {0}".format(select))
        debug("'ignore' setting: {0}".format(ignore))
        debug("'is_highlight' setting: {0}".format(is_highlight))
        debug("'is_popup' setting: {0}".format(is_popup))

        regions = []
        view_errors = {}
        errors_list_filtered = []

        for e in self.errors_list:
            debug("error to show: {0}".format(e))
            current_line = e[0] - 1
            error_text = e[2]

            # get error line
            text_point = self.view.text_point(current_line, 0)
            line = self.view.full_line(text_point)
            full_line_text = self.view.substr(line)
            line_text = full_line_text.strip()

            # skip line if 'noqa' defined
            if skip_line(line_text):
                debug("skip error due to 'noqa' comment")
                continue

            # parse error line to get error code
            code, _ = error_text.split(' ', 1)

            # check if user has a setting for select only errors to show
            if select and not [c for c in select if code.startswith(c)]:
                debug("error does not fit in 'select' settings")
                continue

            # check if user has a setting for ignore some errors
            if ignore and [c for c in ignore if code.startswith(c)]:
                debug("error does fit in 'ignore' settings")
                continue

            # build error text
            error = [error_text, u'{0}: {1}'.format(current_line + 1,
                                                    line_text)]
            # skip if this error is already found (with pep8 or flake8)
            if error in errors_to_show:
                debug("skip error: already shown")
                continue
            errors_to_show.append(error)

            # build line error message
            if is_popup:
                errors_list_filtered.append(e)

            # prepare errors regions
            if is_highlight or mark:
                # prepare line
                line_text = full_line_text.rstrip('\r\n')
                line_length = len(line_text)

                # calculate error highlight start and end positions
                start = text_point + line_length - len(line_text.lstrip())
                end = text_point + line_length

                # small tricks
                if code == 'E501':
                    # too long lines: highlight only the rest of line
                    start = text_point + e[1]
                # TODO: add another tricks like 'E303 too many blank lines'

                regions.append(sublime.Region(start, end))

            # save errors for each line in view to special dict
            view_errors.setdefault(current_line, []).append(error_text)

        # renew errors list with selected and ignored errors
        self.errors_list = errors_list_filtered
        # save errors dict
        ERRORS_IN_VIEWS[self.view.id()] = view_errors

        # highlight error regions if defined
        if is_highlight:
            debug("highlight errors in view (regions)")
            self.view.add_regions('flake8-errors', regions,
                                  'invalid.deprecated', mark,
                                  sublime.DRAW_OUTLINED)
        elif mark:
            debug("highlight errors in view (marks)")
            self.view.add_regions('flake8-errors', regions,
                                  'invalid.deprecated', mark,
                                  sublime.HIDDEN)

        if is_popup:
            debug("show popup window with errors")
            # view errors window
            window = self.view.window()
            window.show_quick_panel(errors_to_show, self.error_selected)

    def error_selected(self, item_selected):
        """
        Error was selected - go to error.
        """
        if item_selected == -1:
            debug("close errors popup window")
            return
        debug("error was selected from popup window: scroll to line")

        # reset selection
        selection = self.view.sel()
        selection.clear()

        # get error region
        error = self.errors_list[item_selected]
        region_begin = self.view.text_point(error[0] - 1, error[1])

        # go to error
        selection.add(sublime.Region(region_begin, region_begin))
        self.view.show_at_center(region_begin)
        update_statusbar(self.view)


class Flake8LintBackground(sublime_plugin.EventListener):
    """
    Listen to Siblime Text 2 events.
    """
    def __init__(self, *args, **kwargs):
        super(Flake8LintBackground, self).__init__(*args, **kwargs)
        self._last_selected_line = None

    def _view_is_preview(self, view):
        """
        Returns True if view is in preview mode (e.g. "Goto Anything").
        """
        window_views = (window_view.id()
                        for window_view in sublime.active_window().views())
        return bool(view.id() not in window_views)

    def _lintOnLoad(self, view, retry=False):
        """
        Some code to lint file on load.
        """
        debug("try to lint file on load")
        if not retry:  # first run - wait a little bit
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 100)
            return

        if view.is_loading():  # view is still running - wait again
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 100)
            return

        if view.window() is None:  # view window is not initialized - wait...
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 100)
            return

        if view.window().active_view().id() != view.id():
            debug("view is not active anymore, forget about lint")
            return  # not active anymore, don't lint it!

        if self._view_is_preview(view):
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 300)
            return  # wait before view will became normal

        view.run_command("flake8_lint")

    def on_load(self, view):
        """
        Do lint on file load.
        """
        if view.is_scratch():
            debug("skip lint because view is scratch")
            return  # do not lint scratch views

        if settings.get('lint_on_load', False):
            debug("run lint by 'on_load' hook")
            self._lintOnLoad(view)
        else:
            debug("skip lint by 'on_load' hook due to plugin settings")

    def on_post_save(self, view):
        """
        Do lint on file save.
        """
        if view.is_scratch():
            debug("skip lint because view is scratch")
            return  # do not lint scratch views

        if settings.get('lint_on_save', True):
            debug("run lint by 'on_post_save' hook")
            view.run_command('flake8_lint')
        else:
            debug("skip lint by 'on_post_save' hook due to plugin settings")

    def on_selection_modified(self, view):
        """
        Selection was modified: update status bar.
        """
        if view.is_scratch():
            return  # do not lint scratch views

        current_line = get_current_line(view)

        if current_line is None:
            if self._last_selected_line is not None:  # line was selected
                self._last_selected_line = None
                clear_statusbar(view)

        elif current_line != self._last_selected_line:  # line was changed
            self._last_selected_line = current_line
            debug("update statusbar")
            update_statusbar(view)

########NEW FILE########
__FILENAME__ = lint
# -*- coding: utf-8 -*-
"""
Flake8 lint worker.
"""
from __future__ import print_function
import os
import sys

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

# Add 'contrib' to sys.path to simulate installation of package 'flake8'
# and it's dependencies: 'pyflake', 'pep8' and 'mccabe'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'contrib'))


import pyflakes.api
import mccabe
import pep8
from pep8 import readlines
from flake8.engine import _flake8_noqa

# Monkey-patching is a big evil (don't do this),
# but hardcode is a much more bigger evil. Hate hardcore!
try:
    from .monkey_patching import get_code_complexity
except (ValueError, SystemError):
    from monkey_patching import get_code_complexity
mccabe.get_code_complexity = get_code_complexity

from flake8._pyflakes import patch_pyflakes
patch_pyflakes()


if sys.platform.startswith('win'):
    DEFAULT_CONFIG_FILE = os.path.expanduser(r'~\.flake8')
else:
    DEFAULT_CONFIG_FILE = os.path.join(
        os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
        'flake8'
    )
CONFIG_FILES = ('setup.cfg', 'tox.ini', '.pep8')


def skip_file(path):
    """
    Returns True if line with special commit is found in path:
    # flake8 : noqa
    """
    try:
        return _flake8_noqa(''.join(readlines(path))) is not None
    except (OSError, IOError):
        return True


class Pep8Report(pep8.BaseReport):
    """
    Collect all check results.
    """
    def __init__(self, options):
        """
        Initialize reporter.
        """
        super(Pep8Report, self).__init__(options)
        # errors "collection"
        self.errors = []

    def error(self, line_number, offset, text, check):
        """
        Get error and save it into errors collection.
        """
        code = super(Pep8Report, self).error(line_number, offset, text, check)
        if code:
            self.errors.append((self.line_offset + line_number, offset, text))
        return code


class FlakesReporter(object):
    """
    Formats the results of pyflakes to the linter.
    Example at 'pyflakes.reporter.Reporter' class.
    """
    def __init__(self):
        """
        Construct a Reporter.
        """
        # errors "collection"
        self.errors = []

    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process filename.
        """
        self.errors.append((0, 0, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax errror in filename.
        """
        line = text.splitlines()[-1]
        if offset is not None:
            offset = offset - (len(text) - len(line))
            self.errors.append((lineno, offset, msg))
        else:
            self.errors.append((lineno, 0, msg))

    def flake(self, msg):
        """
        Pyflakes found something wrong with the code.
        """
        # unused import has no col attr, seems buggy... this fixes it
        col = getattr(msg, 'col', 0)
        self.errors.append(
            (msg.lineno, col, msg.flake8_msg % msg.message_args)
        )


def load_flake8_config(filename, global_config=False, project_config=False):
    """
    Returns flake8 settings from config file.

    More info: http://flake8.readthedocs.org/en/latest/config.html
    """
    parser = RawConfigParser()

    # check global config
    if global_config and os.path.isfile(DEFAULT_CONFIG_FILE):
        parser.read(DEFAULT_CONFIG_FILE)

    # search config in filename dir and all parent dirs
    if project_config:
        parent = tail = os.path.abspath(filename)
        while tail:
            if parser.read([os.path.join(parent, fn) for fn in CONFIG_FILES]):
                break
            parent, tail = os.path.split(parent)

    result = {}
    if parser.has_section('flake8'):
        options = (
            ('ignore', 'ignore', 'list'),
            ('select', 'select', 'list'),
            ('exclude', 'ignore_files', 'list'),
            ('max_line_length', 'pep8_max_line_length', 'int')
        )
        for config, plugin, option_type in options:
            if parser.has_option('flake8', config):
                if option_type == 'list':
                    option_value = parser.get('flake8', config).strip()
                    if option_value:
                        result[plugin] = option_value.split(',')
                elif option_type == 'int':
                    option_value = parser.get('flake8', config).strip()
                    if option_value:
                        result[plugin] = parser.getint('flake8', config)
    return result


def lint(filename, settings):
    """
    Run flake8 lint with internal interpreter.
    """
    # check if active view contains file
    if not filename or not os.path.exists(filename):
        return

    # place for warnings =)
    warnings = []

    # lint with pyflakes
    if settings.get('pyflakes', True):
        builtins = settings.get('builtins')
        if builtins:  # builtins is extended
            # some magic (ok, ok, monkey-patching) goes here
            old_builtins = pyflakes.checker.Checker.builtIns
            pyflakes.checker.Checker.builtIns = old_builtins.union(builtins)

        flakes_reporter = FlakesReporter()
        pyflakes.api.checkPath(filename, flakes_reporter)
        warnings.extend(flakes_reporter.errors)

    # lint with pep8
    if settings.get('pep8', True):
        pep8style = pep8.StyleGuide(
            reporter=Pep8Report,
            ignore=['DIRTY-HACK'],  # PEP8 error will never starts like this
            max_line_length=settings.get('pep8_max_line_length')
        )
        pep8style.input_file(filename)
        warnings.extend(pep8style.options.report.errors)

    # check complexity
    try:
        complexity = int(settings.get('complexity', -1))
    except (TypeError, ValueError):
        complexity = -1

    if complexity > -1:
        warnings.extend(mccabe.get_module_complexity(filename, complexity))

    return warnings


def lint_external(filename, settings, interpreter, linter):
    """
    Run flake8 lint with external interpreter.
    """
    import subprocess

    # check if active view contains file
    if not filename or not os.path.exists(filename):
        return

    # first argument is interpreter
    arguments = [interpreter, linter]

    # do we need to run pyflake lint
    if settings.get('pyflakes', True):
        arguments.append('--pyflakes')
        builtins = settings.get('builtins')
        if builtins:
            arguments.append('--builtins')
            arguments.append(','.join(builtins))

    # do we need to run pep8 lint
    if settings.get('pep8', True):
        arguments.append('--pep8')
        max_line_length = settings.get('pep8_max_line_length', 79)
        arguments.append('--pep8-max-line-length')
        arguments.append(str(max_line_length))

    # do we need to run complexity check
    complexity = settings.get('complexity', -1)
    arguments.extend(('--complexity', str(complexity)))

    # last argument is script to check filename
    arguments.append(filename)

    # place for warnings =)
    warnings = []

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # run subprocess
    proc = subprocess.Popen(arguments, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=startupinfo)

    # parse STDOUT for warnings and errors
    for line in proc.stdout:
        line = line.decode('utf-8').strip()
        warning = line.split(':', 2)
        if len(warning) == 3:
            try:
                warnings.append((int(warning[0]), int(warning[1]), warning[2]))
            except (TypeError, ValueError):
                print("Flake8Lint ERROR: {0}".format(line))
        else:
            print("Flake8Lint ERROR: {0}".format(line))

    # and return them =)
    return warnings


if __name__ == "__main__":
    import argparse

    # parse arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument('--pyflakes', action='store_true',
                        help="run pyflakes lint")
    parser.add_argument('--builtins', help="python builtins extend")
    parser.add_argument('--pep8', action='store_true',
                        help="run pep8 lint")
    parser.add_argument('--complexity', type=int, help="check complexity")
    parser.add_argument('--pep8-max-line-length', type=int, default=79,
                        help="pep8 max line length")

    settings = parser.parse_args().__dict__
    filename = settings.pop('filename')

    if settings.get('builtins'):
        settings['builtins'] = settings['builtins'].split(',')

    # run lint and print errors
    for warning in lint(filename, settings):
        try:
            print("%d:%d:%s" % warning)
        except Exception:
            print(warning)
        sys.stdout.flush()

########NEW FILE########
__FILENAME__ = monkey_patching
# -*- coding: utf-8 -*-
"""
Flake8 linters monkey-patching.
"""
try:
    import ast
except ImportError:   # Python 2.5
    from flake8.util import ast
from mccabe import McCabeChecker


def get_code_complexity(code, threshold=7, filename='stdin'):
    """
    This is a monkey-patch for flake8.pyflakes.check.
    Return array of errors instead of print them into STDERR.
    """
    try:
        tree = compile(code, filename, "exec", ast.PyCF_ONLY_AST)
    except SyntaxError:
        # return [(value.lineno, value.offset, value.args[0])]
        # be silent when error, or else syntax errors are reported twice
        return []

    complexity = []
    McCabeChecker.max_complexity = threshold
    for lineno, offset, text, check in McCabeChecker(tree, filename).run():
        complexity.append((lineno, offset, text))
    return complexity

########NEW FILE########
