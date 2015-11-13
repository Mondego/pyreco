__FILENAME__ = async_topic
# -*- coding: utf-8 -*-
'''Implementation for `Vows.async_topic` decorator. (See `core`
module).

'''


# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

import sys

#-------------------------------------------------------------------------------------------------


class VowsAsyncTopic(object):
    #   FIXME: Add Docstring
    def __init__(self, func, args, kw):
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self, callback):
        args = (self.args[0], callback,) + self.args[1:]
        try:
            self.func(*args, **self.kw)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            callback(exc_type, exc_value, exc_traceback)


class VowsAsyncTopicValue(object):
    #   FIXME: Add Docstring
    def __init__(self, args, kw):
        self.args = args
        self.kw = kw
        self.error = None
        if len(self.args) >= 1 and isinstance(self.args[0], Exception):
            self.error = self.args

    def __getitem__(self, attr):
        if type(attr) is int:
            return self.args[attr]

        if attr in self.kw:
            return self.kw[attr]

        raise AttributeError

    def __getattr__(self, attr):
        if attr in self.kw:
            return self.kw[attr]

        if hasattr(self, attr):
            return self.attr

        raise AttributeError

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''PyVows' main entry point.  Contains code for command-line I/O,
running tests, and the almighty `if __name__ == '__main__': main()`.

'''

# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
from __future__ import division, print_function

import argparse
import inspect
import os
from os.path import isfile, split
import sys
import tempfile

try:
    from coverage import coverage
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False

from pyvows.color import yellow, Style, Fore
from pyvows.reporting import VowsDefaultReporter
from pyvows.reporting.xunit import XUnitReporter
from pyvows import version

#-------------------------------------------------------------------------------------------------


class Messages(object):  # pragma: no cover
    '''A simple container for command-line interface strings.'''

    summary = 'Run PyVows tests.'

    path = 'Directory to look for vows recursively. If a file is passed,' + \
        'the file will be the target for vows. (default: %(default)r).'

    pattern = 'Pattern of vows files. (default: %(default)r)'
    verbosity = 'Verbosity. May be specified many times to increase verbosity (default: -vv)'
    cover = 'Show the code coverage of tests. (default: %(default)s)'
    cover_package = 'Verify coverage of %(metavar)s. May be specified many times. (default: all packages)'
    cover_omit = 'Exclude %(metavar)s from coverage. May be specified many times. (default: no files)'
    cover_threshold = 'Coverage below %(metavar)s is considered a failure. (default: %(default)s)'
    cover_report = 'Store coverage report as %(metavar)s. (default: %(default)r)'
    xunit_output = 'Enable XUnit output. (default: %(default)s)'
    xunit_file = 'Store XUnit output as %(metavar)s. (default: %(default)r)'
    exclude = 'Exclude tests and contexts that match regex-pattern %(metavar)s'
    profile = 'Prints the 10 slowest topics. (default: %(default)s)'
    profile_threshold = 'Tests taking longer than %(metavar)s seconds are considered slow. (default: %(default)s)'
    no_color = 'Turn off colorized output. (default: %(default)s)'
    progress = 'Show progress ticks during testing. (default: %(default)s)'
    template = 'Print a PyVows test file template. (Disables testing)'


class Parser(argparse.ArgumentParser):
    def __init__(self, description=Messages.summary, **kwargs):
        super(Parser, self).__init__(
            description=description,
            **kwargs)

        #Easy underlining, if we ever need it in the future
        #uline   = lambda text: '\033[4m{0}\033[24m'.format(text)
        metavar = lambda metavar: '{0}{metavar}{0}'.format(Style.RESET_ALL, metavar=metavar.upper())

        self.add_argument('-p', '--pattern', default='*_vows.py', help=Messages.pattern, metavar=metavar('pattern'))

        ### Filtering
        self.add_argument('-e', '--exclude', action='append', default=[], help=Messages.exclude, metavar=metavar('exclude'))

        ### Coverage
        cover_group = self.add_argument_group('Test Coverage')
        cover_group.add_argument('-c', '--cover', action='store_true', default=False, help=Messages.cover)
        cover_group.add_argument(
            '-l', '--cover-package', action='append', default=[],
            help=Messages.cover_package, metavar=metavar('package')
        )
        cover_group.add_argument(
            '-o', '--cover-omit', action='append', default=[],
            help=Messages.cover_omit, metavar=metavar('file')
        )
        cover_group.add_argument(
            '-t', '--cover-threshold', type=float, default=80.0,
            help=Messages.cover_threshold, metavar=metavar('number')
        )
        cover_group.add_argument(
            '-r', '--cover-report', action='store', default=None,
            help=Messages.cover_report, metavar=metavar('file')
        )

        ### XUnit
        xunit_group = self.add_argument_group('XUnit')
        xunit_group.add_argument('-x', '--xunit-output', action='store_true', default=False, help=Messages.xunit_output)
        xunit_group.add_argument(
            '-f', '--xunit-file', action='store', default='pyvows.xml',
            help=Messages.xunit_file, metavar=metavar('file')
        )

        ### Profiling
        profile_group = self.add_argument_group('Profiling')
        profile_group.add_argument('--profile', action='store_true', dest='profile', default=False, help=Messages.profile)
        profile_group.add_argument(
            '--profile-threshold', type=float, default=0.1,
            help=Messages.profile_threshold, metavar=metavar('num')
        )

        ### Aux/Unconventional
        aux_group = self.add_argument_group('Utility')
        aux_group.add_argument('--template', action='store_true', dest='template', default=False, help=Messages.template)

        ### Misc
        self.add_argument('--no-color', action='store_true', default=False, help=Messages.no_color)
        self.add_argument('--progress', action='store_true', dest='progress', default=False, help=Messages.progress)
        self.add_argument('--version', action='version', version='%(prog)s {0}'.format(version.to_str()))
        self.add_argument('-v', action='append_const', dest='verbosity', const=1, help=Messages.verbosity)

        self.add_argument('path', nargs='?', default=os.curdir, help=Messages.path)


def run(path, pattern, verbosity, show_progress, exclusion_patterns=None):
    #   FIXME: Add Docstring

    # This calls Vows.run(), which then calls VowsRunner.run()

    # needs to be imported here, else the no-color option won't work
    from pyvows.core import Vows

    if exclusion_patterns:
        Vows.exclude(exclusion_patterns)

    Vows.collect(path, pattern)

    on_success = show_progress and VowsDefaultReporter.on_vow_success or None
    on_error = show_progress and VowsDefaultReporter.on_vow_error or None
    result = Vows.run(on_success, on_error)

    return result


def main():
    '''PyVows' runtime implementation.
    '''
    # needs to be imported here, else the no-color option won't work
    from pyvows.reporting import VowsDefaultReporter

    arguments = Parser().parse_args()

    if arguments.template:
        from pyvows.utils import template
        template()
        sys.exit()  # Exit after printing template, since it's
                    # supposed to be redirected from STDOUT by the user

    path, pattern = arguments.path, arguments.pattern
    if path and isfile(path):
        path, pattern = split(path)
    if not path:
        path = os.curdir

    if arguments.no_color:
        for color_name, value in inspect.getmembers(Fore):
            if not color_name.startswith('_'):
                setattr(Fore, color_name, '')

    if arguments.cover and COVERAGE_AVAILABLE:
        cov = coverage(source=arguments.cover_package,
                       omit=arguments.cover_omit)
        cov.erase()
        cov.start()

    prune = arguments.exclude

    verbosity = len(arguments.verbosity) if arguments.verbosity else 2
    result = run(path, pattern, verbosity, arguments.progress, prune)
    reporter = VowsDefaultReporter(result, verbosity)

    # Print test results first
    reporter.pretty_print()

    # Print profile if necessary
    if arguments.profile:
        reporter.print_profile(arguments.profile_threshold)

    # Print coverage if necessary
    if result.successful and arguments.cover:
        # if coverage was requested, but unavailable, warn the user
        if not COVERAGE_AVAILABLE:
            print()
            print(yellow('WARNING: Cover disabled because coverage could not be found.'))
            print(yellow('Make sure it is installed and accessible.'))
            print()

        # otherwise, we're good
        else:
            cov.stop()
            xml = ''

            try:
                with tempfile.NamedTemporaryFile() as tmp:
                    cov.xml_report(outfile=tmp.name)
                    tmp.seek(0)
                    xml = tmp.read()
            except Exception:
                err = sys.exc_info()[1]
                print("Could not run coverage. Error: %s" % err)

            if xml:
                if arguments.cover_report:
                    with open(arguments.cover_report, 'w') as report:
                        report.write(xml)

                arguments.cover_threshold /= 100.0
                reporter.print_coverage(xml, arguments.cover_threshold)

    # Write XUnit if necessary
    if arguments.xunit_output:
        xunit = XUnitReporter(result)
        xunit.write_report(arguments.xunit_file)

    sys.exit(result.errored_tests)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = color
# -*- coding: utf-8 -*-
'''PyVows' support for color-printing to the terminal.

Currently, just a thin wrapper around the (3rd-party) `colorama`
module.

'''

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class NoColor(object):
        '''When Python can't import `colorama`, this stand-in class prevents
        other parts of PyVows from throwing errors when attempting to print
        in color.

        '''
        def __getattr__(self, *args, **kwargs):
            return ''

    Fore = NoColor()
    Style = NoColor()

#-------------------------------------------------------------------------------------------------

__all__ = [
    'Fore', 'Style',
    'BLACK', 'BLUE', 'CYAN', 'GREEN', 'RED', 'YELLOW', 'WHITE', 'RESET', 'RESET_ALL',
    'black', 'blue', 'cyan', 'green', 'red', 'yellow', 'white', 'bold', 'dim'
]


#-------------------------------------------------------------------------------------------------
#   Color Constants
#-------------------------------------------------------------------------------------------------
BLACK = Fore.BLACK
BLUE = Fore.BLUE
CYAN = Fore.CYAN
GREEN = Fore.GREEN
RED = Fore.RED
YELLOW = Fore.YELLOW
WHITE = Fore.WHITE
#
BOLD = Style.BRIGHT
DIM = Style.DIM
#
RESET = Fore.RESET
RESET_ALL = Style.RESET_ALL

#-------------------------------------------------------------------------------------------------
#   Functions
#-------------------------------------------------------------------------------------------------
def _colorize(msg, color, reset=True):
    reset = RESET if reset else ''
    return '{COLOR}{0!s}{RESET}'.format(msg, COLOR=color, RESET=reset)


def _bold(msg):
    return '{BOLD}{0!s}{RESET_ALL}'.format(msg, BOLD=BOLD, RESET_ALL=RESET_ALL)


def _dim(msg):
    return '{DIM}{0!s}{RESET_ALL}'.format(msg, DIM=DIM, RESET_ALL=RESET_ALL)


black = lambda msg: _colorize(msg, BLACK)
blue = lambda msg: _colorize(msg, BLUE)
cyan = lambda msg: _colorize(msg, CYAN)
green = lambda msg: _colorize(msg, GREEN)
red = lambda msg: _colorize(msg, RED)
yellow = lambda msg: _colorize(msg, YELLOW)
white = lambda msg: _colorize(msg, WHITE)

bold = lambda msg: _bold(msg)
dim = lambda msg: _dim(msg)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
'''This module is the foundation that allows users to write PyVows-style tests.
'''

# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

import os
import sys
import warnings

import preggy

from pyvows import utils
from pyvows.async_topic import VowsAsyncTopic, VowsAsyncTopicValue
from pyvows.decorators import _batch, async_topic, capture_error
from pyvows.runner import VowsRunner

#-------------------------------------------------------------------------------------------------

expect = preggy.expect 


class Vows(object):
    '''This class contains almost the entire interface for using PyVows.  (The
    `expect` class usually being the only other necessary import.)

        *   Mark test batches with the `Vows.batch` decorator
        *   Build test hierarchies with classes that extend `Vows.Context`
        *   For those who need it, topics with asynchronous code can use the
            `Vows.async_topic` decorator

    Other attributes and methods here are for PyVows' internal use.  They
    aren't necessary for writing tests.

    '''
    suites = dict()
    exclusion_patterns = set()

    
    class Context(object):
        '''Extend this class to create your test classes.  (The convention is to
        write `from pyvows import Vows, expect` in your test module, then extend
        `Vows.Context` in your test classes.  If you really wanted, you could
        also import `Context` directly.  But don't do that.)

            *   `Vows.Context` subclasses expect one method named `topic`.
                It should be the first method in any `Vows.Context` subclass,
                by convention.
            *   Sibling `Context`s run in parallel.
            *   Nested `Context`s run sequentially.

        The `setup` and `teardown` methods aren't typically needed.  But
        they are available if your test suite has extra pre- and
        post-testing work to be done in any given `Context`.
        '''

        def __init__(self, parent=None):
            self.parent = parent
            self.topic_value = None
            self.index = -1
            self.generated_topic = False
            self.ignored_members = set(['topic', 'setup', 'teardown', 'ignore'])
        
        def _get_first_available_topic(self, index=-1):
            if self.topic_value:
                if index > -1 and isinstance(self.topic_value, (list, set, tuple)):
                    return self.topic_value[index]
                else:
                    return self.topic_value
            elif self.parent:
                return self.parent._get_first_available_topic(index)
            return None

        def ignore(self, *args):
            '''Appends `*args` to `ignored_members`.  (Methods listed in
            `ignored_members` are considered "not a test method" by PyVows.)
            '''
            for arg in args:
                self.ignored_members.add(arg)

        def setup(self): pass
        def teardown(self): pass
        
        setup.__doc__    = \
        teardown.__doc__ = \
        '''For use in your PyVows tests.  Define in your `Vows.Context` 
            subclass to define what should happen before that Context's testing begins.

            Remember:
                * sibling Contexts are executed in parallel
                * nested Contexts are executed sequentially
                
        '''

        
    @staticmethod
    def assertion(func):
        return preggy.assertion(func)
    
    @staticmethod
    def create_assertions(func): 
        return preggy.create_assertions(func)
    
    @staticmethod
    def async_topic(topic):
        return async_topic(topic)

    @staticmethod
    def asyncTopic(topic):
        #   FIXME: Add Comment
        warnings.warn('The asyncTopic decorator is deprecated.  ' 
                      'Please use Vows.async_topic instead.',
                      DeprecationWarning,
                      stacklevel=2)
        return async_topic(topic)

    @staticmethod
    def capture_error(topic_func):
        return capture_error(topic_func)

    @staticmethod
    def batch(ctx_class):
        '''Class decorator.  Use on subclasses of `Vows.Context`.

        Test batches in PyVows are the largest unit of tests. The convention
        is to have one test batch per file, and have the batch’s class match
        the file name.

        '''
        suite = ctx_class.__module__.replace('.', os.path.sep)
        suite = os.path.abspath(suite) 
        suite += '.py'
        if suite not in Vows.suites:
            Vows.suites[suite] = set()
        Vows.suites[suite].add(ctx_class)
        _batch(ctx_class)

    @classmethod
    def collect(cls, path, pattern):
        #   FIXME: Add Docstring
        #
        #   *   Only used in `cli.py`
        path = os.path.abspath(path)
        sys.path.insert(0, path)
        files = utils.locate(pattern, path)
        for module_path in files:
            module_name = os.path.splitext(
                module_path.replace(path, '').replace(os.sep, '.').lstrip('.')
            )[0]
            __import__(module_name)
            
    @classmethod
    def exclude(cls, test_name_pattern):
        cls.exclusion_patterns = test_name_pattern

    @classmethod
    def run(cls, on_vow_success, on_vow_error):
        #   FIXME: Add Docstring
        #
        #       *   Used by `run()` in `cli.py`
        #       *   Please add a useful description if you wrote this! :)
        runner = VowsRunner(cls.suites,
                                    cls.Context,
                                    on_vow_success,
                                    on_vow_error,
                                    cls.exclusion_patterns)
        return runner.run()

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
'''This module is the foundation that allows users to write PyVows-style tests.
'''

# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from functools import wraps
import re

from pyvows.async_topic import VowsAsyncTopic

#-------------------------------------------------------------------------------------------------

def _batch(klass):
    # This is underscored-prefixed because the only intended use (via
    # `@Vows.batch`) expands on this core functionality
    def klass_name(*args, **kw):
        klass(*args, **kw)
    return klass_name


def async_topic(topic):
    '''Topic decorator.  Allows PyVows testing of asynchronous topics.

    Use `@Vows.async_topic` on your `topic` method to mark it as
    asynchronous.  This allows PyVows to test topics which use callbacks
    instead of return values.

    '''
    def wrapper(*args, **kw):
        return VowsAsyncTopic(topic, args, kw)
    wrapper._original = topic
    wrapper._wrapper_type = 'async_topic'
    wrapper.__name__ = topic.__name__
    return wrapper

def capture_error(topic_func):
    '''Topic decorator.  Allows any errors raised to become the topic value.

    By default, errors raised in topic functions are reported as
    errors. But sometimes you want the error to be the topic value, in
    which case decorate the topic function with this decorator.'''
    def wrapper(*args, **kw):
        try:
            return topic_func(*args, **kw)
        except Exception as e:
            return e
    wrapper._original = topic_func
    wrapper._wrapper_type = 'capture_error'
    wrapper.__name__ = topic_func.__name__
    return wrapper

#-------------------------------------------------------------------------------------------------

class FunctionWrapper(object):

    '''Function decorator.  Simply calls the decorated function when all
    the wrapped functions have been called.

    '''
    def __init__(self, func):
        self.waiting = 0
        self.func = func

    def wrap(self, method):
        self.waiting += 1

        @wraps(method)
        def wrapper(*args, **kw):
            try:
                ret = method(*args, **kw)
                return ret
            finally:
                self.waiting -= 1
                self()

        wrapper._original = method
        return wrapper

    def __call__(self):
        if self.waiting == 0:
            self.func()

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-
'''This module is the foundation that allows users to write PyVows-style tests.
'''

# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com


class VowsInternalError(Exception):
    '''Raised whenever PyVows internal code does something unexpected.'''

    def __init__(self, *args):
        if not isinstance(args[0], str):
            raise TypeError('VowsInternalError must be instantiated with a string as the first argument')
        if not len(args) >= 2:
            raise IndexError('VowsInternalError must receive at least 2 arguments')
        self.raw_msg = args[0]
        self.args = args[1:]

    def __str__(self):
        msg = self.raw_msg.format(*self.args)
        msg += '''

        Help PyVows fix this issue!  Tell us what happened:

        https://github.com/heynemann/pyvows/issues/new

        '''
        return msg

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
'''Contains the `VowsDefaultReporter` class, which handles output after tests
have been run.
'''

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
from __future__ import division, print_function

import re
import traceback

from pyvows.color import yellow, green, red, bold

__all__ = [
    'PROGRESS_SIZE',
    'V_EXTRA_VERBOSE',
    'V_VERBOSE',
    'V_NORMAL',
    'V_SILENT',
    'ensure_encoded',
    'VowsReporter',
]

PROGRESS_SIZE = 50

# verbosity levels
V_EXTRA_VERBOSE = 4
V_VERBOSE = 3
V_NORMAL = 2
V_SILENT = 1


def ensure_encoded(thing, encoding='utf-8'):
    '''Ensures proper encoding for unicode characters.

    Currently used only for characters `✓` and `✗`.

    '''
    if isinstance(thing, unicode):
        return thing.encode(encoding)
    else:
        return thing


class VowsReporter(object):
    '''Base class for other Reporters to extend.  Contains common attributes
    and methods.
    '''
    #   Should *only* contain attributes and methods that aren't specific
    #   to a particular type of report.

    HONORED = green('✓')
    BROKEN = red('✗')
    TAB = '  '

    def __init__(self, result, verbosity):
        self.result = result
        self.verbosity = verbosity
        self.indent = 1

    #-------------------------------------------------------------------------
    #   String Formatting
    #-------------------------------------------------------------------------
    def camel_split(self, string):
        '''Splits camel-case `string` into separate words.

        Example:

            self.camel_split('SomeCamelCaseString')

        Returns:

            'Some camel case string'

        '''
        return re.sub('((?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z])|(?=[0-9]\b))', ' ', string).strip()

    def under_split(self, string):
        '''Replaces all underscores in `string` with spaces.'''
        return ' '.join(string.split('_'))

    def format_traceback(self, traceback_list):
        '''Adds the current level of indentation to a traceback (so it matches
        the current context's indentation).

        '''

        # TODO:
        #   ...Is this a decorator?  If so, please add a comment or docstring
        #   to make it explicit.
        def _indent(msg):
            if msg.strip().startswith('File'):
                return self.indent_msg(msg)
            return msg

        tb_list = [_indent(tb) for tb in traceback_list]
        return ''.join(tb_list)

    def format_python_constants(self, msg):
        '''Fixes capitalization of Python constants.

        Since developers are used to reading `True`, `False`, and `None`
        as capitalized words, it makes sense to match that capitalization
        in reports.

        '''
        msg = msg.replace('true', 'True')
        msg = msg.replace('false', 'False')
        msg = msg.replace('none', 'None')
        return msg

    def header(self, msg, ruler_character='='):
        '''Returns the string `msg` with a text "ruler".  Also colorizes as
        bright green (when color is available).

        '''
        ruler = ' {0}'.format(len(msg) * ruler_character)

        msg = ' {0}'.format(msg)
        msg = '{0}{ruler}{0}{msg}{0}{ruler}{0}'.format(
            '\n',
            ruler=ruler,
            msg=msg)

        msg = green(bold(msg))

        return msg

    def indent_msg(self, msg, indentation=None):
        '''Returns `msg` with the indentation specified by `indentation`.

        '''
        if indentation is not None:
            indent = self.TAB * indentation
        else:
            indent = self.TAB * self.indent

        return '{indent}{msg}'.format(
            indent=indent,
            msg=msg
        )

    #-------------------------------------------------------------------------
    #   Printing Methods
    #-------------------------------------------------------------------------
    def humanized_print(self, msg, indentation=None):
        '''Passes `msg` through multiple text filters to make the output
        appear more like normal text, then prints it (indented by
        `indentation`).

        '''
        msg = self.under_split(msg)
        msg = self.camel_split(msg)
        msg = msg.replace('  ', ' ')  # normalize spaces if inserted by
                                      # both of the above
        msg = msg.capitalize()
        msg = self.format_python_constants(msg)

        print(self.indent_msg(msg, indentation))

    def print_traceback(self, err_type, err_obj, err_traceback):
        '''Prints a color-formatted traceback with appropriate indentation.'''
        if isinstance(err_obj, AssertionError):
            error_msg = err_obj
        else:
            error_msg = unicode(err_obj)

        print(self.indent_msg(red(error_msg)))

        if self.verbosity >= V_NORMAL:
            traceback_msg = traceback.format_exception(err_type, err_obj, err_traceback)
            traceback_msg = self.format_traceback(traceback_msg)
            traceback_msg = '\n{traceback}'.format(traceback=traceback_msg)
            traceback_msg = self.indent_msg(yellow(traceback_msg))
            print(traceback_msg)

########NEW FILE########
__FILENAME__ = coverage
# -*- coding: utf-8 -*-
'''Contains the `VowsDefaultReporter` class, which handles output after tests
have been run.
'''

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
from __future__ import division, print_function

from xml.etree import ElementTree as etree

from pyvows.color import yellow, blue, dim, white, bold
from pyvows.reporting.common import (
    PROGRESS_SIZE,
    VowsReporter,)


class VowsCoverageReporter(VowsReporter):
    '''A VowsReporter which prints the code coverage of tests.'''

    def get_uncovered_lines(self, uncovered_lines, max_num=3):
        '''Searches for untested lines of code.  Returns a string
        listing the line numbers.

        If the number of uncovered lines is greater than `max_num`, this will
        only explicitly list the first `max_num` uncovered lines, followed
        by ' and ## more' (where '##' is the total number of additional
        uncovered lines.

        '''
        if len(uncovered_lines) > max_num:
            template_str = []
            for i in range(max_num):
                line_num = uncovered_lines[i]
                template_str.append(line_num)
                if i is not (max_num - 1):
                    template_str.append(', ')

            template_str.append(
                ', and {num_more_uncovered:d} more'.format(
                    num_more_uncovered=len(uncovered_lines) - max_num
                ))

            return yellow(''.join(template_str))

        return yellow(', '.join(uncovered_lines))

    def parse_coverage_xml(self, xml):
        '''Reads `xml` for code coverage statistics, and returns the
        dict `result`.
        '''
        _coverage = lambda x: float(x.attrib['line-rate'])

        result = {}
        root = etree.fromstring(xml)
        result['overall'] = _coverage(root)
        result['classes'] = []

        for package in root.findall('.//package'):
            package_name = package.attrib['name']
            for klass in package.findall('.//class'):
                result['classes'].append({
                    'name': '.'.join([package_name, klass.attrib['name']]),
                    'line_rate': _coverage(klass),
                    'uncovered_lines': [line.attrib['number']
                                        for line in klass.find('lines')
                                        if line.attrib['hits'] == '0']
                })

        return result

    #-------------------------------------------------------------------------
    #   Printing (Coverage)
    #-------------------------------------------------------------------------
    def print_coverage(self, xml, cover_threshold):
        '''Prints code coverage statistics for your tests.'''
        print(self.header('Code Coverage'))

        root = self.parse_coverage_xml(xml)
        klasses = sorted(root['classes'], key=lambda klass: klass['line_rate'])
        max_length = max([len(klass['name']) for klass in root['classes']])
        max_coverage = 0

        for klass in klasses:
            coverage = klass['line_rate']

            if coverage < cover_threshold:
                cover_character = VowsReporter.BROKEN
            else:
                cover_character = VowsReporter.HONORED

            if 100.0 < max_coverage < coverage:
                max_coverage = coverage
                if max_coverage == 100.0:
                    print()

            coverage = coverage
            progress = int(coverage * PROGRESS_SIZE)
            offset = None

            if coverage == 0.000:
                offset = 2
            elif 0.000 < coverage < 0.1000:
                offset = 1
            else:
                offset = 0

            if coverage == 0.000 and not klass['uncovered_lines']:
                continue

            print(self.format_class_coverage(
                cover_character=cover_character,
                klass=klass['name'],
                space1=' ' * (max_length - len(klass['name'])),
                progress=progress,
                coverage=coverage,
                space2=' ' * (PROGRESS_SIZE - progress + offset),
                lines=self.get_uncovered_lines(klass['uncovered_lines']),
                cover_threshold=cover_threshold))

        print()

        total_coverage = root['overall']
        cover_character = VowsReporter.HONORED if (total_coverage >= cover_threshold) else VowsReporter.BROKEN
        progress = int(total_coverage * PROGRESS_SIZE)

        print(self.format_overall_coverage(cover_character, max_length, progress, total_coverage))
        print()

    def format_class_coverage(self, cover_character, klass, space1, progress, coverage, space2, lines, cover_threshold):
        '''Accepts coverage data for a class and returns a formatted string (intended for
        humans).
        '''
        #   FIXME:
        #       Doesn't this *actually* print coverage for a module, and not a class?

        # preprocess raw data...
        klass = klass.lstrip('.')
        klass = blue(klass)

        MET_THRESHOLD = coverage >= cover_threshold

        coverage = '{prefix}{coverage:.1%}'.format(
            prefix=' ' if (coverage > 0.000) else '',
            coverage=coverage
        )

        if MET_THRESHOLD:
            coverage = bold(coverage)

        coverage = white(coverage)

        # ...then format
        return ' {0} {klass}{space1}\t{progress}{coverage}{space2} {lines}'.format(
            # TODO:
            #   * remove manual spacing, use .format() alignment
            cover_character,
            klass=klass,
            space1=space1,
            progress=dim('•' * progress),
            coverage=coverage,
            space2=space2,
            lines=lines
        )

    def format_overall_coverage(self, cover_character, max_length, progress, total_coverage):
        '''Accepts overall coverage data and returns a formatted string (intended for
        humans).
        '''

        # preprocess raw data
        overall = blue('OVERALL')
        overall = bold(overall)
        space = ' ' * (max_length - len('OVERALL'))
        total = '{total_coverage:.1%}'.format(total_coverage=total_coverage)
        total = white(bold(total))

        # then format
        return ' {0} {overall}{space}\t{progress} {total}'.format(
            cover_character,
            overall=overall,
            space=space,
            progress='•' * progress,
            total=total)

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-
'''Contains the `VowsDefaultReporter` class, which handles output after tests
have been run.
'''
# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
from __future__ import division

import os

from pyvows.color import yellow, blue, dim, green, white
from pyvows.reporting.common import (
    VowsReporter,)


class VowsProfileReporter(VowsReporter):
    '''A VowsReporter which prints a profile of the 10 slowest topics.'''

    def print_profile(self, threshold):
        '''Prints the 10 slowest topics that took longer than `threshold`
        to test.
        '''

        '''Prints the 10 slowest topics that took longer than
        `threshold` to test.

        '''

        MAX_PATH_SIZE = 40
        topics = self.result.get_worst_topics(number=10, threshold=threshold)

        if topics:
            print(self.header('Slowest Topics'))

            table_header = yellow('  {0}'.format(dim('#')))
            table_header += yellow('  Elapsed     Context File Path                         ')
            table_header += yellow('  Context Name')
            print(table_header)

            for index, topic in enumerate(topics):
                name = self.under_split(topic['context'])
                name = self.camel_split(name)

                topic['path'] = os.path.realpath(topic['path'])
                topic['path'] = '{0!s}'.format(topic['path'])
                topic['path'] = os.path.relpath(topic['path'], os.path.abspath(os.curdir))

                data = {
                    'number': '{number:#2}'.format(number=index + 1),
                    'time': '{time:.05f}s'.format(time=topic['elapsed']),
                    'path': '{path:<{width}}'.format(
                        path=topic['path'][-MAX_PATH_SIZE:],
                        width=MAX_PATH_SIZE),
                    'name': '{name}'.format(name=name),
                }

                for k, v in data.items():
                    if k == 'number':
                        colorized = blue
                    if k == 'time':
                        colorized = green
                    if k == 'path':
                        colorized = lambda x: dim(white(x))
                    if k == 'name':
                        colorized = green

                    data[k] = colorized(v)

                print(
                    ' {number}  {time}{0}{path}{0}{name}'.format(
                        4 * ' ',
                        **data)
                    )

            print()

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
'''Contains the `VowsDefaultReporter` class, which handles output after tests
have been run.
'''
# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
from __future__ import division, print_function

import sys

from pyvows.color import yellow, red, blue
from pyvows.errors import VowsInternalError
from pyvows.reporting.common import (
    ensure_encoded,
    V_EXTRA_VERBOSE,
    V_VERBOSE,
    VowsReporter,)


class VowsTestReporter(VowsReporter):
    '''A VowsReporter which prints test results.'''

    def __init__(self, result, verbosity):
        super(VowsTestReporter, self).__init__(result, verbosity)

    @property
    def status_symbol(self):
        '''Returns the symbol indicating whether all tests passed.'''
        if self.result.successful:
            return VowsReporter.HONORED
        else:
            return VowsReporter.BROKEN

    #-------------------------------------------------------------------------
    #   Class Methods
    #-------------------------------------------------------------------------
    @classmethod
    def on_vow_success(cls, vow):
        #   FIXME: Add Docstring / Comment description
        #
        #       *   Why is `vow` unused?
        sys.stdout.write(VowsReporter.HONORED)

    @classmethod
    def on_vow_error(cls, vow):
        #   FIXME: Add Docstring / Comment description
        #
        #       *   Why is `vow` unused?
        sys.stdout.write(VowsReporter.BROKEN)

    #-------------------------------------------------------------------------
    #   Printing Methods
    #-------------------------------------------------------------------------
    def pretty_print(self):
        '''Prints PyVows test results.'''
        print(self.header('Vows Results'))

        if not self.result.contexts:
            # FIXME:
            #   If no vows are found, how could any be broken?
            print(
                '{indent}{broken} No vows found! » 0 honored • 0 broken (0.0s)'.format(
                    indent=self.TAB * self.indent,
                    broken=VowsReporter.BROKEN)
                )
            return

        if self.verbosity >= V_VERBOSE or self.result.errored_tests:
            print()

        for context in self.result.contexts:
            self.print_context(context['name'], context)

        print('{0}{1} OK » {honored:d} honored • {broken:d} broken ({time:.6f}s)'.format(
            self.TAB * self.indent,
            self.status_symbol,
            honored=self.result.successful_tests,
            broken=self.result.errored_tests,
            time=self.result.elapsed_time))

        print()

    def print_context(self, name, context):
        #   FIXME: Add Docstring
        #
        #       *   Is this only used in certain cases?
        #           *   If so, which?
        self.indent += 1

        if (self.verbosity >= V_VERBOSE or
                not self.result.eval_context(context)):
            self.humanized_print(name)

        def _print_successful_context():
            honored = ensure_encoded(VowsReporter.HONORED)
            topic = ensure_encoded(test['topic'])
            name = ensure_encoded(test['name'])

            if self.verbosity == V_VERBOSE:
                self.humanized_print('{0} {1}'.format(honored, name))
            elif self.verbosity >= V_EXTRA_VERBOSE:
                if test['enumerated']:
                    self.humanized_print('{0} {1} - {2}'.format(honored, topic, name))
                else:
                    self.humanized_print('{0} {1}'.format(honored, name))

        def _print_failed_context():
            ctx = test['context_instance']

            def _print_traceback():
                self.indent += 2
                
                ### NOTE:
                ###     Commented out try/except; potential debugging hinderance
                
                #try:

                traceback_args = (test['error']['type'],
                                  test['error']['value'],
                                  test['error']['traceback'])
                self.print_traceback(*traceback_args)
                
                # except Exception:
                #     # should never occur!
                #     err_msg = '''Unexpected error in PyVows!
                #                  PyVows error occurred in: ({0!s})
                #                  Context was: {1!r}
                # 
                #               '''
                #     # from os.path import abspath
                #     raise VowsInternalError(err_msg, 'pyvows.reporting.test', ctx)

                # print file and line number
                if 'file' in test:
                    file_msg = 'found in {test[file]} at line {test[lineno]}'.format(test=test)
                    print('\n', 
                          self.indent_msg(red(file_msg)), 
                          '\n')

                self.indent -= 2

            self.humanized_print('{0} {test}'.format(
                VowsReporter.BROKEN,
                test=test['name']))

            # print generated topic (if applicable)
            if ctx.generated_topic:
                value = yellow(test['topic'])
                self.humanized_print('')
                self.humanized_print('\tTopic value:')
                self.humanized_print('\t{value}'.format(value=value))
                self.humanized_print('\n' * 2)

            # print traceback
            _print_traceback()

        # Show any error raised by the setup, topic or teardown functions
        if context.get('error', None):
            e = context['error']
            print('\n', self.indent_msg(blue("Error in {0!s}:".format(e.source))))
            self.print_traceback(*e.exc_info)
            print(self.indent_msg(red("Nested tests following this error have not been run.")))

        else:
            for test in context['tests']:
                if test['succeeded']:
                    _print_successful_context()
                else:
                    _print_failed_context()

        # I hereby (re)curse you...!
        for context in context['contexts']:
            self.print_context(context['name'], context)

        self.indent -= 1

########NEW FILE########
__FILENAME__ = xunit
# -*- coding: utf-8 -*-
'''Provides the `XUnitReporter` class, which creates XML reports after testing.
'''


# pyVows testing engine
# https://github.com/{heynemann,truemped}/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
import codecs
from datetime import datetime
import socket
import traceback
from xml.dom.minidom import Document


class XUnitReporter(object):
    '''Turns `VowsResult` objects into XUnit-style reports.'''

    def __init__(self, result):
        self.result_summary = self.summarize_results(result)

    def write_report(self, filename, encoding='utf-8'):
        #   FIXME: Add Docstring
        with codecs.open(filename, 'w', encoding, 'replace') as output_file:
            output_file.write(self.to_xml(encoding))

    def to_xml(self, encoding='utf-8'):
        #   FIXME: Add Docstring
        document = self.create_report_document()
        return document.toxml(encoding=encoding)

    def summarize_results(self, result):
        #   FIXME: Add Docstring
        result_summary = {
            'total': result.successful_tests + result.errored_tests,
            'errors': 0,
            'failures': result.errored_tests,
            'ts': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'hostname': socket.gethostname(),
            'elapsed': result.elapsed_time,
            'contexts': result.contexts
        }
        return result_summary

    def create_report_document(self):
        #   FIXME: Add Docstring
        result_summary = self.result_summary

        document = Document()
        testsuite_node = document.createElement('testsuite')
        testsuite_node.setAttribute('name', 'pyvows')
        testsuite_node.setAttribute('tests', str(result_summary['total']))
        testsuite_node.setAttribute('errors', str(result_summary['errors']))
        testsuite_node.setAttribute('failures', str(result_summary['failures']))
        testsuite_node.setAttribute('timestamp', str(result_summary['ts']))
        testsuite_node.setAttribute('hostname', str(result_summary['hostname']))
        testsuite_node.setAttribute('time', '{elapsed:.3f}'.format(elapsed=result_summary['elapsed']))

        document.appendChild(testsuite_node)

        for context in result_summary['contexts']:
            self.create_test_case_elements(document, testsuite_node, context)

        return document

    def create_test_case_elements(self, document, parent_node, context):
        #   FIXME: Add Docstring
        for test in context['tests']:
            test_stats = {
                'context': context['name'],
                'name': test['name'],
                'taken': 0.0
            }

            testcase_node = document.createElement('testcase')
            testcase_node.setAttribute('classname', str(test_stats['context']))
            testcase_node.setAttribute('name', str(test_stats['name']))
            testcase_node.setAttribute('time', '{time:.3f}'.format(time=test_stats['taken']))
            parent_node.appendChild(testcase_node)

            if not test['succeeded']:
                error = test['error']
                error_msg = traceback.format_exception(
                    error['type'],
                    error['value'],
                    error['traceback']
                )

                if isinstance(test['topic'], Exception):
                    exc_type, exc_value, exc_traceback = test['context_instance'].topic_error
                    error_msg += traceback.format_exception(exc_type, exc_value, exc_traceback)

                error_data = {
                    'errtype': error['type'].__name__,
                    'msg': error['value'],
                    'tb': ''.join(error_msg)
                }

                failure_node = document.createElement('failure')
                failure_node.setAttribute('type', str(error_data['errtype']))
                failure_node.setAttribute('message', str(error_data['msg']))
                failure_text = document.createTextNode(str(error_data['tb']))
                failure_node.appendChild(failure_text)
                testcase_node.appendChild(failure_node)

        for ctx in context['contexts']:
            self.create_test_case_elements(document, parent_node, ctx)

########NEW FILE########
__FILENAME__ = result
# -*- coding: utf-8 -*-
'''Contains `VowsResult` class, which collects the results of
each vow.

'''

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

#-------------------------------------------------------------------------------------------------

class VowsResult(object):
    '''Collects success/failure/total statistics (as well as elapsed
    time) for the outcomes of tests.

    Only one instance of this class is created when PyVows is run.

    '''

    def __init__(self):
        self.contexts = []
        self.elapsed_time = 0.0

    def _count_tests(self, contexts=None, first=True, count_func=lambda test: 1):
        '''Used interally for class properties
        `total_test_count`, `successful_tests`, and `errored_tests`.

        '''
        #   TODO
        #       Reevaluate whether `count_func` should have a default value
        #       (AFAICT the default is never used. It makes more sense
        #       to me if it had no default, or defaulted to `None`.
        test_count = 0

        if first:
            contexts = self.contexts

        for context in contexts:
            test_count += sum([count_func(i) for i in context['tests']])
            test_count += self._count_tests(contexts=context['contexts'],
                                            first=False,
                                            count_func=count_func)

        return test_count

    def _get_topic_times(self, contexts=None):
        '''Returns a dict describing how long testing took for
        each topic in `contexts`.

        '''
        topic_times = []

        if contexts is None:
            contexts = self.contexts

        for context in contexts:
            topic_times.append({
                'context': context['name'],
                'path':    context['filename'],
                'elapsed': context['topic_elapsed']
            })
            ctx_topic_times = self._get_topic_times(context['contexts'])
            topic_times.extend(ctx_topic_times)

        return topic_times

    @property
    def successful(self):
        '''Returns a boolean, indicating whether the current
        `VowsResult` was 100% successful.

        '''
        return self.successful_tests == self.total_test_count

    @property
    def total_test_count(self):
        '''Returns the total number of tests.'''
        return self._count_tests(contexts=None, first=True, count_func=lambda test: 1)

    @property
    def successful_tests(self):
        '''Returns the number of tests that passed.'''
        return self._count_tests(contexts=None, first=True, count_func=lambda test: 1 if test['succeeded'] else 0)

    @property
    def errored_tests(self):
        '''Returns the number of tests that failed.'''
        return self._count_tests(contexts=None, first=True, count_func=lambda test: 0 if test['succeeded'] else 1)

    def eval_context(self, context):
        '''Returns a boolean indicating whether `context` tested
        successfully.

        '''
        succeeded = True

        # Success only if there wasn't an error in setup, topic or teardown
        succeeded = succeeded and (not context.get('error', None))

        # Success only if all subcontexts succeeded
        for context in context['contexts']:
            succeeded = succeeded and self.eval_context(context)

        # Success only if all tests succeeded
        for test in context['tests']:
            succeeded = succeeded and test['succeeded']

        return succeeded

    def get_worst_topics(self, number=10, threshold=0.1):
        '''Returns the top `number` slowest topics which took longer
        than `threshold` to test.

        '''
        times = [
            time for time in self._get_topic_times()
            if time['elapsed'] > 0 and time['elapsed'] >= threshold
        ]
        times.sort(key=lambda x: x['elapsed'], reverse=True)
        return times[:number]

########NEW FILE########
__FILENAME__ = abc
# -*- coding: utf-8 -*-
'''Abstract base class for all PyVows Runner implementations.'''
 
 
# pyvows testing engine
# https://github.com/heynemann/pyvows
 
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
 
import re, sys, time
 
from pyvows.runner.utils import get_code_for, get_file_info_for, get_topics_for
from pyvows.utils import elapsed

#-------------------------------------------------------------------------------------------------

class VowsRunnerABC(object):
     
    def __init__(self, suites, context_class, on_vow_success, on_vow_error, exclusion_patterns):
        self.suites = suites  # a suite is a file with pyvows tests
        self.context_class = context_class
        self.on_vow_success = on_vow_success
        self.on_vow_error = on_vow_error
        self.exclusion_patterns = exclusion_patterns
        if self.exclusion_patterns:
            self.exclusion_patterns = set([re.compile(x) for x in self.exclusion_patterns])
 
    def is_excluded(self, name):
        '''Return whether `name` is in `self.exclusion_patterns`.'''
        for pattern in self.exclusion_patterns:
            if pattern.search(name):
                return True
        return False
         
    def run(self):
        pass
     
    def run_context(self):
        pass
     
    def run_vow(self, tests_collection, topic, ctx_obj, vow, vow_name, enumerated):
        #   FIXME: Add Docstring
 
        start_time = time.time()
        filename, lineno = get_file_info_for(vow._original)
 
        vow_result = {
            'context_instance': ctx_obj,
            'name': vow_name,
            'enumerated': enumerated,
            'result': None,
            'topic': topic,
            'error': None,
            'succeeded': False,
            'file': filename,
            'lineno': lineno,
            'elapsed': 0
        }
 
        try:
            result = vow(ctx_obj, topic)
            vow_result['result'] = result
            vow_result['succeeded'] = True
            if self.on_vow_success:
                self.on_vow_success(vow_result)
 
        except:
            #   FIXME:
            #
            #   Either...
            #       *   Describe why we're catching every exception, or
            #       *   Fix to catch specific kinds of exceptions
            err_type, err_value, err_traceback = sys.exc_info()
            vow_result['error'] = {
                'type': err_type,
                'value': err_value,
                'traceback': err_traceback
            }
            if self.on_vow_error:
                self.on_vow_error(vow_result)
 
        vow_result['elapsed'] = elapsed(start_time)
        tests_collection.append(vow_result)
 
        return vow_result


class VowsTopicError(Exception):
    """Wraps an error in the setup or topic functions."""
    def __init__(self, source, exc_info):
        self.source = source
        self.exc_info = exc_info

########NEW FILE########
__FILENAME__ = gevent
# -*- coding: utf-8 -*-
'''The GEvent implementation of PyVows runner.'''
 
 
# pyvows testing engine
# https://github.com/heynemann/pyvows
 
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
 
from __future__ import absolute_import
 
import inspect
import sys
import time
import re

from gevent.pool import Pool

from pyvows.async_topic import VowsAsyncTopic, VowsAsyncTopicValue
from pyvows.decorators import FunctionWrapper
from pyvows.runner.utils import get_code_for, get_file_info_for, get_topics_for
from pyvows.result import VowsResult
from pyvows.utils import elapsed
from pyvows.runner.abc import VowsRunnerABC, VowsTopicError

#-------------------------------------------------------------------------------------------------

class VowsParallelRunner(VowsRunnerABC):
    #   FIXME: Add Docstring
 
    # Class is called from `pyvows.core:Vows.run()`,
    # which is called from `pyvows.cli.run()`
 
    pool = Pool(1000)
     
    def run(self):
        #   FIXME: Add Docstring
 
        # called from `pyvows.core:Vows.run()`,
        # which is called from `pyvows.cli.run()`
 
        start_time = time.time()
        result = VowsResult()
        for suite, batches in self.suites.items():
            for batch in batches:
                self.pool.spawn(
                    self.run_context, 
                    result.contexts, 
                    ctx_name = batch.__name__, 
                    ctx_obj  = batch(None), 
                    index    = -1, 
                    suite    = suite 
                )
             
        self.pool.join()
        result.elapsed_time = elapsed(start_time)
        return result
     
     
    def run_context(self, ctx_collection, ctx_name=None, ctx_obj=None, index=-1, suite=None):
        #   FIXME: Add Docstring
         
        if self.is_excluded(ctx_name):
            return
 
        #-----------------------------------------------------------------------
        # Local variables and defs
        #-----------------------------------------------------------------------
        ctx_result = {
            'filename': suite or inspect.getsourcefile(ctx_obj.__class__),
            'name': ctx_name,
            'tests': [],
            'contexts': [],
            'topic_elapsed': 0,
            'error': None,
        }
         
        ctx_collection.append(ctx_result)
        ctx_obj.index = index
        ctx_obj.pool = self.pool
        teardown = FunctionWrapper(ctx_obj.teardown)  # Wrapped teardown so it's called at the appropriate time

        def _run_setup_and_topic(ctx_obj, index):
            # Run setup function
            try:
                ctx_obj.setup()
            except Exception as e:
                raise VowsTopicError('setup', sys.exc_info())

            # Find & run topic function
            if not hasattr(ctx_obj, 'topic'): # ctx_obj has no topic
                return ctx_obj._get_first_available_topic(index)

            try:
                topic_func = ctx_obj.topic
                topic_list = get_topics_for(topic_func, ctx_obj)

                start_time = time.time()
                topic = topic_func(*topic_list)
                ctx_result['topic_elapsed'] = elapsed(start_time)
                return topic

            except Exception as e:
                raise VowsTopicError('topic', sys.exc_info())

        def _run_tests(topic):
            def _run_with_topic(topic):
                def _run_vows_and_subcontexts(topic, index=-1, enumerated=False):
                    # methods
                    for vow_name, vow in vows:
                        self._run_vow(
                            ctx_result['tests'],
                            topic,
                            ctx_obj,
                            teardown.wrap(vow),
                            vow_name,
                            enumerated=enumerated)
                 
                    # classes
                    for subctx_name, subctx in subcontexts:
                        # resolve user-defined Context classes
                        if not issubclass(subctx, self.context_class):
                            subctx = type(ctx_name, (subctx, self.context_class), {})
 
                        subctx_obj = subctx(ctx_obj)
                        subctx_obj.pool = self.pool
                        subctx_obj.teardown = teardown.wrap(subctx_obj.teardown)
                     
                        self.pool.spawn(
                            self.run_context,
                            ctx_result['contexts'],
                            ctx_name=subctx_name, 
                            ctx_obj=subctx_obj, 
                            index=index,
                            suite=suite or ctx_result['filename']
                        )

                # setup generated topics if needed
                is_generator = inspect.isgenerator(topic)
                if is_generator:
                    try:
                        ctx_obj.generated_topic = True
                        topic = ctx_obj.topic_value = list(topic)
                    except Exception as e:
                        # Actually getting the values from the generator may raise exception
                        raise VowsTopicError('topic', sys.exc_info())
                else:
                    ctx_obj.topic_value = topic

                if is_generator:
                    for index, topic_value in enumerate(topic):
                        _run_vows_and_subcontexts(topic_value, index=index, enumerated=True)
                else:
                    _run_vows_and_subcontexts(topic)

            special_names = set(['setup', 'teardown', 'topic'])
            if hasattr(ctx_obj, 'ignored_members'):
                special_names.update(ctx_obj.ignored_members)
 
            # remove any special methods from ctx_members
            ctx_members = tuple(filter(
                lambda member: not (member[0] in special_names or member[0].startswith('_')),
                inspect.getmembers(type(ctx_obj))
            ))
            vows        = set((vow_name,vow)       for vow_name, vow       in ctx_members if inspect.ismethod(vow))
            subcontexts = set((subctx_name,subctx) for subctx_name, subctx in ctx_members if inspect.isclass(subctx))
             
            if not isinstance(topic, VowsAsyncTopic):
                _run_with_topic(topic)
            else:
                def handle_callback(*args, **kw):
                    _run_with_topic(VowsAsyncTopicValue(args, kw))
                topic(handle_callback)

        def _run_teardown(topic):
            try:
                teardown()
            except Exception as e:
                raise VowsTopicError('teardown', sys.exc_info())

        #-----------------------------------------------------------------------
        # Begin
        #-----------------------------------------------------------------------
        try:
            topic = _run_setup_and_topic(ctx_obj, index)
            # Only run tests & teardown if setup & topic run without errors
            _run_tests(topic)
            _run_teardown(topic)
        except VowsTopicError as e:
            ctx_obj.topic_error = e   # is this needed still?
            ctx_result['error'] = e


    def _run_vow(self, tests_collection, topic, ctx_obj, vow, vow_name, enumerated=False):
        #   FIXME: Add Docstring
        if self.is_excluded(vow_name):    
            return
        self.pool.spawn(self.run_vow, tests_collection, topic, ctx_obj, vow, vow_name, enumerated)

########NEW FILE########
__FILENAME__ = sequential
# -*- coding: utf-8 -*-
'''This is the slowest of PyVows' runner implementations.  But it's also dependency-free; thus, 
it's a universal fallback.  
 
'''

from pyvows.runner.abc import VowsRunnerABC
from pyvows.runner.utils import get_code_for, get_file_info_for, get_topics_for

#-------------------------------------------------------------------------------------------------

class VowsSequentialRunner(object):
     
    def run(self):
        pass
        #for suite, batches in self.suites.items():
        #    for batch in batches:
        #        self.run_context(batch.__name__, batch(None))
         
    def run_context(self, ctx_name, ctx_instance):
        pass
        # setup
        # teardown
        # topic
        # vows
        # subcontexts
        # teardown
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
'''Utility functions for all implementations of pyvows.runner.
 
'''
import os.path as path

#-------------------------------------------------------------------------------------------------

def get_code_for(obj):
    #   FIXME: Add Comment description
    code = None
    if hasattr(obj, '__code__'):
        code = obj.__code__
    elif hasattr(obj, '__func__'):
        code = obj.__func__.__code__
    return code
 
 
def get_file_info_for(member):
    #   FIXME: Add Docstring
    code = get_code_for(member)
 
    filename = code.co_filename
    lineno = code.co_firstlineno
 
    return filename, lineno
 
 
def get_topics_for(topic_function, ctx_obj):
    #   FIXME: Add Docstring
    if not ctx_obj.parent:
        return []
 
    # check for decorated topic function
    if hasattr(topic_function, '_original'):
        # _wrapper_type is 'async_topic' or 'capture_error'
        async = (getattr(topic_function, '_wrapper_type', None) == 'async_topic')
        topic_function = topic_function._original
    else:
        async = False
 
    code = get_code_for(topic_function)
 
    if not code:
        raise RuntimeError('Function %s does not have a code property')
 
    expected_args = code.co_argcount - 1
 
    # taking the callback argument into consideration
    if async:
        expected_args -= 1
 
    # prepare to create `topics` list
    topics = []
    child = ctx_obj
    context = ctx_obj.parent
 
    # populate `topics` list
    for i in range(expected_args):
        topic = context.topic_value
 
        if context.generated_topic:
            topic = topic[child.index]
 
        topics.append(topic)
 
        if not context.parent:
            break
 
        context = context.parent
        child = child.parent
 
    return topics

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
'''This module is the foundation that allows users to write PyVows-style tests.
'''

# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

import fnmatch
import glob
import os
import time

#-------------------------------------------------------------------------------------------------

elapsed = lambda start_time: float(round(time.time() - start_time, 6))


def locate(pattern, root=os.curdir, recursive=True):
    '''Recursively locates test files when `pyvows` is run from the
    command line.

    '''
    root_path = os.path.abspath(root)

    if recursive:
        return_files = []
        for path, dirs, files in os.walk(root_path):
            for filename in fnmatch.filter(files, pattern):
                return_files.append(os.path.join(path, filename))
        return return_files
    else:
        return glob.glob(os.path.join(root_path, pattern))


def template():
    '''Provides a template containing boilerplate code for new PyVows test
    files. Output is sent to STDOUT, allowing you to redirect it on
    the command line as you wish.

    '''
    from datetime import date
    import sys
    from textwrap import dedent

    from pyvows import version

    TEST_FILE_TEMPLATE = '''\
    # -*- coding: utf-8 -*-
    ##  Generated by PyVows v{version}  ({date})
    ##  http://pyvows.org

    ##  IMPORTS  ##
    ##
    ##  Standard Library
    #
    ##  Third Party
    #
    ##  PyVows Testing
    from pyvows import Vows, expect

    ##  Local Imports
    import


    ##  TESTS  ##
    @Vows.batch
    class PleaseGiveMeAGoodName(Vows.Context):

        def topic(self):
            return # return what you're going to test here

        ##  Now, write some vows for your topic! :)
        def should_do_something(self, topic):
            expect(topic)# <pyvows assertion here>

    '''.format(
        version = version.to_str(),
        date = '{0:%Y/%m/%d}'.format(date.today())
    )

    sys.stdout.write(dedent(TEST_FILE_TEMPLATE))

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
'''PyVows' version number.
'''


# pyVows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

#-------------------------------------------------------------------------------------------------

__version__ = (2, 0, 5)

#-------------------------------------------------------------------------------------------------


def to_str():
    '''Returns a string containing PyVows' version number.'''
    return '.'.join([str(item) for item in __version__])

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Allows the use of `python -m pyvows`.'''

import sys

from pyvows.cli import main

#-------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = assertion_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect

#-----------------------------------------------------------------------------

class NotEmptyContext(Vows.Context):
    def should_not_be_empty(self, topic):
        expect(topic).not_to_be_empty()

class NotErrorContext(Vows.Context):
    def should_not_be_an_error(self, topic):
        expect(topic).not_to_be_an_error()

Vows.NotEmptyContext = NotEmptyContext
Vows.NotErrorContext = NotErrorContext

#-----------------------------------------------------------------------------

@Vows.batch
class Assertion(Vows.Context):
    
    class WhenNotHaveTopic(Vows.Context):
        
        def we_can_see_topic_as_none(self, topic):
            expect(topic).to_be_null()
    
    class WhenUTF8Topic(Vows.Context):
        def topic(self):
            return u"some á é í ó ç"

        def should_not_fail(self, topic):
            expect(topic).to_equal(u'some á é í ó ç')

    class NonErrorContext(Vows.NotErrorContext):
        def topic(self):
            return 42

    class NotEmptyContext(Vows.NotEmptyContext):
        def topic(self):
            return "harmless"

########NEW FILE########
__FILENAME__ = emptiness_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionIsEmpty(Vows.Context):
    class WhenEmpty(Vows.Context):
        class WhenString(Vows.Context):
            def topic(self):
                return ''

            def we_get_an_empty_string(self, topic):
                expect(topic).to_be_empty()

        class WhenList(Vows.Context):
            def topic(self):
                return []

            def we_get_an_empty_list(self, topic):
                expect(topic).to_be_empty()

        class WhenTuple(Vows.Context):
            def topic(self):
                return tuple([])

            def we_get_an_empty_tuple(self, topic):
                expect(topic).to_be_empty()

        class WhenDict(Vows.Context):
            def topic(self):
                return {}

            def we_get_an_empty_dict(self, topic):
                expect(topic).to_be_empty()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect([1]).to_be_empty()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic([1]) to be empty")

    class WhenNotEmpty(Vows.Context):
        class WhenString(Vows.Context):
            def topic(self):
                return 'whatever'

            def we_get_a_not_empty_string(self, topic):
                expect(topic).Not.to_be_empty()

        class WhenList(Vows.Context):
            def topic(self):
                return ['something']

            def we_get_a_not_empty_list(self, topic):
                expect(topic).Not.to_be_empty()

        class WhenTuple(Vows.Context):
            def topic(self):
                return tuple(['something'])

            def we_get_a_not_empty_tuple(self, topic):
                expect(topic).Not.to_be_empty()

        class WhenDict(Vows.Context):
            def topic(self):
                return {"key": "value"}

            def we_get_a_not_empty_dict(self, topic):
                expect(topic).Not.to_be_empty()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect([]).not_to_be_empty()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic([]) not to be empty")

########NEW FILE########
__FILENAME__ = equality_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionEquality(Vows.Context):
    def topic(self):
        return "test"

    class WhenIsEqual(Vows.Context):

        def we_get_test(self, topic):
            expect(topic).to_equal('test')

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(1).to_equal(2)

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic(1) to equal 2")

    class WhenIsNotEqual(Vows.Context):

        def we_do_not_get_else(self, topic):
            expect(topic).Not.to_equal('else')

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(1).not_to_equal(1)

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic(1) not to equal 1")

    class WhenHaveASubClassThatHaveAExtraParamInTopic(Vows.Context):
        def topic(self, last):
            return last

        def we_get_the_last_topic_value_without_modifications(self, topic):
            expect(topic).to_equal('test')

    class WhenSubContextNotHaveTopic(Vows.Context):

        def we_get_the_last_topic(self, topic):
            expect(topic).to_equal('test')

########NEW FILE########
__FILENAME__ = inclusion_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionInclude(Vows.Context):

    class WhenItIsAString(Vows.Context):
        def topic(self):
            return "some big string"

        def we_can_find_some(self, topic):
            expect(topic).to_include('some')

        def we_can_find_big(self, topic):
            expect(topic).to_include('big')

        def we_can_find_string(self, topic):
            expect(topic).to_include('string')

        def we_cant_find_else(self, topic):
            expect(topic).Not.to_include('else')

    class WhenItIsAList(Vows.Context):
        def topic(self):
            return ["some", "big", "string"]

        def we_can_find_some(self, topic):
            expect(topic).to_include('some')

        def we_can_find_big(self, topic):
            expect(topic).to_include('big')

        def we_can_find_string(self, topic):
            expect(topic).to_include('string')

        def we_cant_find_else(self, topic):
            expect(topic).Not.to_include('else')

    class WhenItIsATuple(Vows.Context):
        def topic(self):
            return tuple(["some", "big", "string"])

        def we_can_find_some(self, topic):
            expect(topic).to_include('some')

        def we_can_find_big(self, topic):
            expect(topic).to_include('big')

        def we_can_find_string(self, topic):
            expect(topic).to_include('string')

        def we_cant_find_else(self, topic):
            expect(topic).Not.to_include('else')

    class WhenItIsADict(Vows.Context):
        def topic(self):
            return {"some": 1, "big": 2, "string": 3}

        def we_can_find_some(self, topic):
            expect(topic).to_include('some')

        def we_can_find_big(self, topic):
            expect(topic).to_include('big')

        def we_can_find_string(self, topic):
            expect(topic).to_include('string')

        def we_cant_find_else(self, topic):
            expect(topic).Not.to_include('else')

    class WhenWeGetAnError(Vows.Context):
        @Vows.capture_error
        def topic(self, last):
            expect('a').to_include('b')

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic('a') to include 'b'")

    class WhenWeGetAnErrorOnNot(Vows.Context):
        @Vows.capture_error
        def topic(self, last):
            expect('a').not_to_include('a')

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic('a') not to include 'a'")

########NEW FILE########
__FILENAME__ = length_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionLength(Vows.Context):
    class ToLength(Vows.Context):
        class WithString(Vows.Context):
            def topic(self):
                return "some string"

            def we_can_see_it_has_11_characters(self, topic):
                expect(topic).to_length(11)

        class WithList(Vows.Context):
            def topic(self):
                return ["some", "list"]

            def we_can_see_it_has_2_items(self, topic):
                expect(topic).to_length(2)

        class WithTuple(Vows.Context):
            def topic(self):
                return tuple(["some", "list"])

            def we_can_see_it_has_2_items(self, topic):
                expect(topic).to_length(2)

        class WithDict(Vows.Context):
            def topic(self):
                return {"some": "item", "other": "item"}

            def we_can_see_it_has_2_items(self, topic):
                expect(topic).to_length(2)

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect('a').to_length(2)

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic('a') to have 2 of length, but it has 1")

    class NotToLength(Vows.Context):
        class WhenWeGetAnError(Vows.Context):
            @Vows.capture_error
            def topic(self, last):
                expect('a').not_to_length(1)

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic('a') not to have 1 of length")

########NEW FILE########
__FILENAME__ = like_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionIsLike(Vows.Context):

    class WhenItIsAString(Vows.Context):
        def topic(self):
            return " some StRinG with RanDoM CaSe And  Weird   SpACING   "

        def we_assert_it_is_like_other_string(self, topic):
            expect(topic).to_be_like('some string with random case and weird spacing')

        def we_assert_it_is_not_like_other_string(self, topic):
            expect(topic).Not.to_be_like('some other string')

    class WhenItIsAMultilineString(Vows.Context):
        def topic(self):
            return " some StRinG \nwith RanDoM \nCaSe And  \nWeird   \nSpACING   "

        def we_assert_it_is_like_other_string(self, topic):
            expect(topic).to_be_like('some string with random case and weird spacing')

        def we_assert_it_is_not_like_other_string(self, topic):
            expect(topic).Not.to_be_like('some other string')

    class WhenItIsANumber(Vows.Context):
        def topic(self):
            return 42

        def we_assert_it_is_not_like_a_string(self, topic):
            expect(topic).Not.to_be_like('42')

        def we_assert_it_is_like_42(self, topic):
            expect(topic).to_be_like(42)

        def we_assert_it_is_like_42_float(self, topic):
            expect(topic).to_be_like(42.0)

        def we_assert_it_is_like_42_long(self, topic):
            expect(topic).to_be_like(long(42))

        def we_assert_it_is_not_like_41(self, topic):
            expect(topic).Not.to_be_like(41)

    class WhenItIsAList(Vows.Context):

        class OfNumbers(Vows.Context):
            def topic(self):
                return [1, 2, 3]

            def we_can_compare_to_other_list(self, topic):
                expect(topic).to_be_like([1, 2, 3])

            def we_can_compare_to_a_list_in_different_order(self, topic):
                expect(topic).to_be_like([3, 2, 1])

            def we_can_compare_to_a_tuple_in_different_order(self, topic):
                expect(topic).to_be_like((3, 2, 1))

        class OfStrings(Vows.Context):
            def topic(self):
                return ["some", "string", "list"]

            def we_can_compare_to_other_list_in_different_order(self, topic):
                expect(topic).to_be_like(["list", "some", "string"])

        class OfLists(Vows.Context):

            class WithinList(Vows.Context):
                def topic(self):
                    return [["my", "list"], ["of", "lists"]]

                def we_can_compare_to_other_list_of_lists(self, topic):
                    expect(topic).to_be_like((['lists', 'of'], ['list', 'my']))

            class WithinTuple(Vows.Context):
                def topic(self):
                    return (["my", "list"], ["of", "lists"])

                def we_can_compare_to_other_list_of_lists(self, topic):
                    expect(topic).to_be_like((['lists', 'of'], ['list', 'my']))

        class OfDicts(Vows.Context):

            def topic(self):
                return [{'some': 'key', 'other': 'key'}]

            def we_can_compare_to_other_list_of_dicts(self, topic):
                expect(topic).to_be_like([{'some': 'key', 'other': 'key'}])

            def we_can_compare_to_other_list_of_dicts_out_of_order(self, topic):
                expect(topic).to_be_like([{'other': 'key', 'some': 'key'}])

    class WhenItIsATuple(Vows.Context):

        class OfNumbers(Vows.Context):
            def topic(self):
                return (1, 2, 3)

            def we_can_compare_to_other_tuple(self, topic):
                expect(topic).to_be_like((1, 2, 3))

            def we_can_compare_to_a_tuple_in_different_order(self, topic):
                expect(topic).to_be_like((3, 2, 1))

            def we_can_compare_to_a_list_in_different_order(self, topic):
                expect(topic).to_be_like([3, 2, 1])

    class WhenItIsADict(Vows.Context):

        def topic(self):
            return {'some': 'key', 'other': 'value'}

        def we_can_compare_to_other_dict(self, topic):
            expect(topic).to_be_like({'some': 'key', 'other': 'value'})

        def we_can_compare_to_a_dict_in_other_order(self, topic):
            expect(topic).to_be_like({'other': 'value', 'some': 'key'})

        def we_can_compare_to_a_dict_with_a_key_that_has_value_none(self, topic):
            expect(topic).not_to_be_like({'other': 'value', 'some': None})

        class OfDicts(Vows.Context):

            def topic(self):
                return {
                    'some': {
                        'key': 'value',
                        'key2': 'value2'
                    }
                }

            def we_can_compare_to_nested_dicts(self, topic):
                expect(topic).to_be_like({
                    'some': {
                        'key2': 'value2',
                        'key': 'value'
                    }
                })

    class WhenWeGetAnError(Vows.Context):
        @Vows.capture_error
        def topic(self, last):
            expect('a').to_be_like('b')

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic('a') to be like 'b'")

    class WhenWeGetAnErrorOnNot(Vows.Context):
        @Vows.capture_error
        def topic(self, last):
            expect('a').not_to_be_like('a')

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic('a') not to be like 'a'")

########NEW FILE########
__FILENAME__ = boolean_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionIsTrue(Vows.Context):

    class WhenBoolean(Vows.Context):
        def topic(self):
            return True

        def we_can_assert_it_is_true(self, topic):
            expect(topic).to_be_true()

    class WhenNumber(Vows.Context):
        def topic(self):
            return 1

        def we_can_assert_number_is_true(self, topic):
            expect(topic).to_be_true()

    class WhenString(Vows.Context):
        def topic(self):
            return 'some'

        def we_can_assert_string_is_true(self, topic):
            expect(topic).to_be_true()

    class WhenList(Vows.Context):
        def topic(self):
            return ['some']

        def we_can_assert_list_is_true(self, topic):
            expect(topic).to_be_true()

    class WhenDict(Vows.Context):
        def topic(self):
            return {'some': 'key'}

        def we_can_assert_dict_is_true(self, topic):
            expect(topic).to_be_true()

    class WhenWeGetAnError(Vows.Context):

        @Vows.capture_error
        def topic(self, last):
            expect(False).to_be_true()

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic(False) to be truthy")


@Vows.batch
class AssertionIsFalse(Vows.Context):

    class WhenBoolean(Vows.Context):
        def topic(self):
            return False

        def we_can_assert_it_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenNumber(Vows.Context):
        def topic(self):
            return 0

        def we_can_assert_zero_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenNone(Vows.Context):
        def topic(self):
            return None

        def we_can_assert_none_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenString(Vows.Context):
        def topic(self):
            return ''

        def we_can_assert_empty_string_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenList(Vows.Context):
        def topic(self):
            return []

        def we_can_assert_empty_list_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenDict(Vows.Context):
        def topic(self):
            return {}

        def we_can_assert_empty_dict_is_false(self, topic):
            expect(topic).to_be_false()

    class WhenWeGetAnError(Vows.Context):

        @Vows.capture_error
        def topic(self):
            expect(True).to_be_false()

        def we_get_an_understandable_message(self, topic):
            expect(topic).to_have_an_error_message_of("Expected topic(True) to be falsy")

########NEW FILE########
__FILENAME__ = classes_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


class SomeClass(object):
    pass


class OtherClass(object):
    pass


@Vows.batch
class AssertionIsInstance(Vows.Context):
    def topic(self):
        return SomeClass()

    class WhenIsInstance(Vows.Context):

        def we_get_an_instance_of_someclass(self, topic):
            expect(topic).to_be_instance_of(SomeClass)

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(2).to_be_instance_of(str)

            def we_get_an_understandable_message(self, topic):
                msg = 'Expected topic(2) to be an instance of {0!r}, but it was a {1!r}'.format(str, int)
                expect(topic).to_have_an_error_message_of(msg)

    class WhenIsNotInstance(Vows.Context):

        def we_do_not_get_an_instance_of_otherclass(self, topic):
            expect(topic).Not.to_be_instance_of(OtherClass)

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(2).not_to_be_instance_of(int)

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of(
                    'Expected topic(2) not to be an instance of {0!s}'.format(int))

########NEW FILE########
__FILENAME__ = errors_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionErrors(Vows.Context):
    class NonErrors(Vows.Context):
        def topic(self):
            return 0

        def we_can_see_that_is_not_an_error(self, topic):
            expect(topic).Not.to_be_an_error()
            
    class Errors(Vows.Context):
        def topic(self, error):
            return ValueError('some bogus error')

        def we_can_see_that_is_an_error_class(self, topic):
            expect(topic).to_be_an_error()

        def we_can_see_it_was_a_value_error(self, topic):
            expect(topic).to_be_an_error_like(ValueError)
            
        def we_can_see_that_is_has_error_message_of(self, topic):
            expect(topic).to_have_an_error_message_of('some bogus error')

        class ErrorMessages(Vows.Context):
            @Vows.capture_error 
            def topic(self, last):
                raise Exception('1 does not equal 2')
            
            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of('1 does not equal 2')
                
        class WhenErrorMessagesDoNotMatch(Vows.Context):
            def topic(self, last):
                try:
                    expect(last).to_have_an_error_message_of('some bogus')
                except AssertionError as e:
                    return e

            def we_get_an_understandable_message(self, topic):
                expected_message = "Expected topic({0!r}) to be an error with message {1!r}".format(
                        str(ValueError('some bogus error')),
                        'some bogus'
                        )
                expect(topic).to_have_an_error_message_of(expected_message)
                    
            
        class ToBeAnError(Vows.Context):
            def we_can_see_that_is_an_error_instance(self, topic):
                expect(topic).to_be_an_error()

            class WhenWeGetAnError(Vows.Context):
                @Vows.capture_error
                def topic(self, last):
                    expect(2).to_be_an_error()

                def we_get_an_understandable_message(self, topic):
                    expect(topic).to_have_an_error_message_of("Expected topic(2) to be an error")


        class NotToBeAnError(Vows.Context):
            def topic(self):
                return 2

            def we_can_see_that_is_not_an_error_instance(self, topic):
                expect(topic).not_to_be_an_error()


            class WhenWeGetAnError(Vows.Context):
                def topic(self, last):
                    try:
                        expect(last).to_be_an_error()
                    except AssertionError as e:
                        return e, last
                    
                def we_get_an_understandable_message(self, topic):
                    expect(topic[0]).to_have_an_error_message_of("Expected topic({0}) to be an error".format(topic[1]))

        

    

########NEW FILE########
__FILENAME__ = file_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


#   TEST DATA
STRINGS = {
    'that_are_files': (
        __file__,
        unicode(__file__),
    ),

    'that_are_not_files':   (
        __doc__,
    )
}


#   HELPERS
isafile = lambda topic: expect(topic).to_be_a_file()
isnotafile = lambda topic: expect(topic).not_to_be_a_file()


#   NOW, MAKE YOUR VOWS.

@Vows.batch
class WhenMakingFileAssertions(Vows.Context):
    #   @TODO:  Clean up this repetitive test code
    #
    #           Preferable one of the following:
    #
    #           -   context inheritance
    #               http://pyvows.org/#-context-inheritance
    #
    #           -   generative testing
    #               http://pyvows.org/#-using-generative-testing

    class OnFilesThatDoNotExist(Vows.Context):
        def topic(self):
            for item in STRINGS['that_are_not_files']:
                yield item

        class AssertingThatTheyDo(Vows.Context):
            @Vows.capture_error
            def topic(self, parent_topic):
                return isafile(parent_topic)

            def should_raise_an_error(self, topic):
                expect(topic).to_be_an_error_like(AssertionError)

        class AssertingThatTheyDoNot(Vows.Context):
            @Vows.capture_error
            def topic(self, parent_topic):
                return isnotafile(parent_topic)

            def should_raise_no_errors(self, topic):
                expect(topic).Not.to_be_an_error()

    class OnFilesThatDoExist(Vows.Context):
        def topic(self):
            for item in STRINGS['that_are_files']:
                yield item

        class AssertingTheyAreFiles(Vows.Context):
            @Vows.capture_error
            def topic(self, parent_topic):
                return isafile(parent_topic)

            def should_not_raise_errors(self, topic):
                expect(topic).not_to_be_an_error()

        class AssertingTheyAreNotFiles(Vows.Context):
            @Vows.capture_error
            def topic(self, parent_topic):
                return isnotafile(parent_topic)

            def should_raise_an_error(self, topic):
                expect(topic).to_be_an_error()

        class WhenWeInstantiateThemAsFileObjects(Vows.Context):
            def topic(self, parent_topic):
                f = open(parent_topic)
                return f

            class AssertingTheyAreFiles(Vows.Context):
                @Vows.capture_error
                def topic(self, parent_topic):
                    return isafile(parent_topic)

                def should_not_raise_errors(self, topic):
                    expect(topic).not_to_be_an_error()

            class AssertingTheyAreNotFiles(Vows.Context):
                @Vows.capture_error
                def topic(self, parent_topic):
                    return isnotafile(parent_topic)

                def should_raise_an_error(self, topic):
                    expect(topic).to_be_an_error()

########NEW FILE########
__FILENAME__ = function_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


def a_function():
    pass


@Vows.batch
class AssertionIsFunction(Vows.Context):

    class WhenItIsAFunction(Vows.Context):
        def topic(self):
            def my_func():
                pass
            return my_func

        def we_assert_it_is_a_function(self, topic):
            expect(topic).to_be_a_function()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self):
                expect(4).to_be_a_function()

            def we_get_an_understandable_message(self, topic):
                msg = 'Expected topic(4) to be a function or a method, but it was a {0!s}'.format(int)
                expect(topic).to_have_an_error_message_of(msg)

    class WhenItNotAFunction(Vows.Context):
        def topic(self):
            return 42

        def we_assert_it_is_not_a_function(self, topic):
            expect(topic).Not.to_be_a_function()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self):
                expect(a_function).not_to_be_a_function()

            def we_get_an_understandable_message(self, topic):
                msg = 'Expected topic({0!s}) not to be a function or a method'.format(a_function)
                expect(topic).to_have_an_error_message_of(msg)

########NEW FILE########
__FILENAME__ = nullable_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionIsNull(Vows.Context):

    class WhenItIsNull(Vows.Context):
        def topic(self):
            return None

        def we_get_to_check_for_nullability_in_None(self, topic):
            expect(topic).to_be_null()

        class WhenWeGetAnError(Vows.Context):
            @Vows.capture_error
            def topic(self, last):
                expect(1).to_be_null()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic(1) to be None")

    class WhenItIsNotNull(Vows.Context):
        def topic(self):
            return "something"

        def we_see_string_is_not_null(self, topic):
            expect(topic).not_to_be_null()

        class WhenWeGetAnError(Vows.Context):
            @Vows.capture_error
            def topic(self, last):
                expect(None).not_to_be_null()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic(None) not to be None")

########NEW FILE########
__FILENAME__ = numeric_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionIsNumeric(Vows.Context):

    class WhenItIsANumber(Vows.Context):
        def topic(self):
            return 42

        def we_assert_it_is_numeric(self, topic):
            expect(topic).to_be_numeric()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self):
                expect('s').to_be_numeric()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic('s') to be numeric")

    class WhenItIsNotANumber(Vows.Context):
        def topic(self):
            return 'test'

        def we_assert_it_is_not_numeric(self, topic):
            expect(topic).Not.to_be_numeric()

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self):
                expect(2).not_to_be_numeric()

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of("Expected topic(2) not to be numeric")

########NEW FILE########
__FILENAME__ = regexp_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class AssertionRegexp(Vows.Context):
    def topic(self):
        return "some string"

    class WhenItMatches(Vows.Context):

        def we_assert_it_matches_regexp(self, topic):
            expect(topic).to_match(r'^some.+$')

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(last).to_match(r'^other.+$')

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of(
                    "Expected topic('some string') to match the regular expression '^other.+$'")

    class WhenItDoesntMatches(Vows.Context):

        def we_assert_it_does_not_match_regexp(self, topic):
            expect(topic).Not.to_match(r'^other.+$')

        class WhenWeGetAnError(Vows.Context):

            @Vows.capture_error
            def topic(self, last):
                expect(last).not_to_match(r'^some.+$')

            def we_get_an_understandable_message(self, topic):
                expect(topic).to_have_an_error_message_of(
                    "Expected topic('some string') not to match the regular expression '^some.+$'")

########NEW FILE########
__FILENAME__ = async_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

import time

from pyvows import Vows, expect

#-------------------------------------------------------------------------------------------------

def asyncFunc(pool, callback):
    def async():
        time.sleep(0.1)
        return 10

    def get_value(value):
        callback(value, 20, kwarg=30, kw2=40)
    pool.apply_async(async, callback=get_value)

#-------------------------------------------------------------------------------------------------

@Vows.batch
class AsyncTopic(Vows.Context):
    @Vows.async_topic
    def topic(self, callback):
        asyncFunc(self.pool, callback)

    def should_check_the_first_parameter(self, topic):
        expect(topic[0]).to_equal(10)

    def should_check_the_second_parameter(self, topic):
        expect(topic.args[1]).to_equal(20)

    def should_check_the_kwarg_parameter(self, topic):
        expect(topic.kwarg).to_equal(30)

    def should_check_the_kwarg_parameter_accesing_from_topic_as_dict(self, topic):
        expect(topic['kwarg']).to_equal(30)

    def should_check_the_kw2_parameter(self, topic):
        expect(topic.kw['kw2']).to_equal(40)

    class SyncTopic(Vows.Context):
        def topic(self):
            return 1

        def should_be_1(self, topic):
            expect(topic).to_equal(1)

        class NestedAsyncTest(Vows.Context):
            @Vows.async_topic
            def topic(self, callback, old_topic):
                def cb(*args, **kw):
                    args = (old_topic,) + args
                    return callback(*args, **kw)
                asyncFunc(self.pool, cb)

            def should_be_the_value_of_the_old_topic(self, topic):
                expect(topic.args[0]).to_equal(1)

            class NestedSyncTopic(Vows.Context):
                def topic(self):
                    return 1

                def should_be_1(self, topic):
                    expect(topic).to_equal(1)

########NEW FILE########
__FILENAME__ = 64_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# unbreaking some pyvows

# This file is MIT licensed
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2013 nathan dotz

from pyvows import Vows, expect
from pyvows.result import VowsResult
from pyvows.reporting import VowsTestReporter  # , VowsDefaultReporter


@Vows.batch
class VowsTestReporterExceptions(Vows.Context):

    def topic(self):
        v = VowsTestReporter(VowsResult(), 0)
        v.humanized_print = lambda a: None
        return v

    def should_not_raise_TypeError_on_tests_without_a_topic(self, topic):
        try:
            # Notice that the test dict here has no 'topic' key.
            test = {'name':             'Mock Test Result',
                    'succeeded':        False,
                    'context_instance': Vows.Context(),
                    'error': {'type': '',
                              'value': '',
                              'traceback': ''}
                    }
            context = {'tests': [test],
                       'contexts': []
                       }
            topic.print_context('Derp', context)
        except AssertionError as e:
            expect(e).to_be_an_error_like(AssertionError)
            expect(e).Not.to_be_an_error_like(TypeError)

########NEW FILE########
__FILENAME__ = cli_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com
import argparse

from pyvows import Vows, expect
from pyvows.cli import Parser


mock_args = (
    '--cover',
    '--profile',
)


@Vows.batch
class PyVowsCommandLineInterface(Vows.Context):

    class ArgumentParser(Vows.Context):
        def topic(self):
            # suppress the defaults, or the test breaks :/
            parser = Parser(argument_default=argparse.SUPPRESS)
            return parser

        def we_have_a_parser(self, topic):
            expect(topic).to_be_instance_of(argparse.ArgumentParser)

        def we_dont_get_an_error(self, topic):
            expect(topic).not_to_be_an_error()

        class ParsesCorrectly(Vows.Context):
            def topic(self, parser):
                return parser.parse_args(mock_args)

            def should_contain_cover(self, topic):
                expect(topic).to_include('cover')

            def cover_should_be_true(self, topic):
                expect(topic.cover).to_be_true()

            def profile_should_be_true(self, topic):
                expect(topic.profile).to_be_true()

########NEW FILE########
__FILENAME__ = context_inheritance_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com


from pyvows import Vows, expect


class NotAContextThingy(object):
    alicorns = (u'Celestia', u'Luna', u'Nyx', u'Pluto', u'Lauren Faust')

    def get_alicorns(self):
        return self.alicorns


class BaseContext(Vows.Context):

    # First case: Thingy should be ignored.
    Thingy = None

    def topic(self, ponies):
        self.ignore('Thingy', 'BaseSubcontext')
        return (self.Thingy, ponies)

    # Second case: BaseSubcontext should be ignored.
    class BaseSubcontext(Vows.Context):

        def topic(self, (Thingy, ponies)):
            self.ignore('prepare')
            for pony in ponies:
                yield (Thingy, self.prepare(pony))

        def prepare(self, something):
            raise NotImplementedError

        def pony_has_name(self, topic):
            expect(topic).to_be_true()


@Vows.batch
class PonyVows(Vows.Context):

    def topic(self):
        return ('Nyx', 'Pluto')

    class ActualContext(BaseContext):

        Thingy = NotAContextThingy

        class ActualSubcontext(BaseContext.BaseSubcontext):

            def prepare(self, something):
                return unicode(something)

            def pony_is_alicorn(self, (Thingy, pony)):
                expect(Thingy.alicorns).to_include(pony)

########NEW FILE########
__FILENAME__ = division_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from __future__ import division  # Python 2 division is deprecated
from pyvows import Vows, expect


@Vows.batch
class DivisionTests(Vows.Context):

    class WhenDividing42Per1(Vows.Context):

        def topic(self):
            return 42 / 1

        def WeGetANumber(self, topic):
            expect(topic).to_be_numeric()

        def WeGet42(self, topic):
            expect(topic).to_equal(42)

########NEW FILE########
__FILENAME__ = docstring_vows
# -*- coding: utf-8 -*-

import types

from pyvows import Vows, expect


from pyvows import (
    __init__ as pyvows_init,
    __main__,
    async_topic,
    color,
    cli,
    core,
    runner,
    version)
from pyvows.reporting import (
    __init__ as reporting_init,
    common as reporting_common,
    coverage as reporting_coverage,
    profile as reporting_profile,
    test as reporting_test,
    xunit as reporting_xunit)

PYVOWS_MODULES = (
    # general modules
    pyvows_init,
    __main__,
    async_topic,
    color,
    cli,
    core,
    runner,
    version,
    # reporting
    reporting_init,
    reporting_common,
    reporting_coverage,
    reporting_profile,
    reporting_test,
    reporting_xunit,)


@Vows.assertion
def to_have_a_docstring(topic):
    '''Custom assertion.  Raises a AssertionError if `topic` has no
    docstring.

    '''
    if not hasattr(topic, '__doc__'):
        raise AssertionError('Expected topic({0}) to have a docstring', topic)


@Vows.batch
class EachPyvowsModule(Vows.Context):
    def topic(self):
        for mod in PYVOWS_MODULES:
            if isinstance(mod, types.ModuleType):
                yield mod

    def should_have_a_docstring(self, topic):
        expect(topic).to_have_a_docstring()

########NEW FILE########
__FILENAME__ = errors_in_topic_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2013 Richard Lupton r.lupton@gmail.com

from pyvows import Vows, expect


# These tests demonstrate what happens when the topic function raises
# or returns an exception.

@Vows.batch
class ErrorsInTopicFunction(Vows.Context):

    class WhenTopicRaisesAnException:
        def topic(self):
            return 42 / 0

        def tests_should_not_run(self, topic):
            raise RuntimeError("Should not reach here")

        class SubContext:
            def subcontexts_should_also_not_run(self, topic):
                raise RuntimeError("Should not reach here")

    class WhenTopicRaisesAnExceptionWithCaptureErrorDecorator:
        @Vows.capture_error
        def topic(self):
            return 42 / 0

        def it_is_passed_to_tests_as_normal(self, topic):
            expect(topic).to_be_an_error_like(ZeroDivisionError)

    class WhenTopicReturnsAnException:
        def topic(self):
            try:
                return 42 / 0
            except Exception as e:
                return e

        def it_is_passed_to_tests_as_normal(self, topic):
            expect(topic).to_be_an_error_like(ZeroDivisionError)

########NEW FILE########
__FILENAME__ = filter_vows_to_run_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2013 Nathan Dotz nathan.dotz@gmail.com

from pyvows import Vows, expect
from pyvows import cli

from pyvows.runner import VowsRunner


@Vows.batch
class FilterOutVowsFromCommandLine(Vows.Context):

    class Console(Vows.Context):
        def topic(self):
            return cli

        def should_be_not_error_when_called_with_5_args(self, topic):
            try:
                topic.run(None, None, None, None, None)
            except Exception as e:
                expect(e).Not.to_be_instance_of(TypeError)

        def should_hand_off_exclusions_to_Vows_class(self, topic):

            patterns = ['foo', 'bar', 'baz']
            try:
                topic.run(None, '*_vows.py', 2, False, patterns)
            except Exception:
                expect(Vows.exclusion_patterns).to_equal(patterns)

    # TODO: add vow checking that there is a message about vow matching

    class Core(Vows.Context):

        def topic(self):
            return Vows

        def should_have_exclude_method(self, topic):
            expect(topic.exclude).to_be_a_function()

    class VowsRunner(Vows.Context):

        def topic(self):
            return VowsRunner

        def can_be_initialized_with_6_arguments(self, topic):
            try:
                topic(None, None, None, None, None)
            except Exception as e:
                expect(e).Not.to_be_instance_of(TypeError)

        def removes_appropriate_contexts(self, topic):
            r = topic(None, None, None, None, set(['foo', 'bar']))
            col = []
            r.run_context(col, 'footer', r)
            expect(len(col)).to_equal(0)

        def leaves_unmatched_contexts(self, topic):
            VowsRunner.teardown = None
            r = topic(None, None, None, None, ['foo', 'bar'])
            col = []
            r.run_context(col, 'baz', r)
            expect(len(col)).to_equal(1)
            r.run_context(col, 'bip', r)
            expect(len(col)).to_equal(2)

########NEW FILE########
__FILENAME__ = fruits_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


class Strawberry(object):
    def __init__(self):
        self.color = '#ff0000'

    def isTasty(self):
        return True


class PeeledBanana(object):
    pass


class Banana(object):
    def __init__(self):
        self.color = '#fff333'

    def peel(self):
        return PeeledBanana()


@Vows.batch
class TheGoodThings(Vows.Context):
    class AStrawberry(Vows.Context):
        def topic(self):
            return Strawberry()

        def is_red(self, topic):
            expect(topic.color).to_equal('#ff0000')

        def and_tasty(self, topic):
            expect(topic.isTasty()).to_be_true()

    class ABanana(Vows.Context):
        def topic(self):
            return Banana()

        class WhenPeeled(Vows.Context):
            def topic(self, banana):
                return banana.peel()

            def returns_a_peeled_banana(self, topic):
                expect(topic).to_be_instance_of(PeeledBanana)

########NEW FILE########
__FILENAME__ = generator_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


def get_test_data():
    for i in [1] * 10:
        yield i


@Vows.batch
class GeneratorTests(Vows.Context):
    def topic(self):
        return get_test_data()

    def should_be_numeric(self, topic):
        expect(topic).to_equal(1)

    class SubContext(Vows.Context):
        def topic(self, parent_topic):
            return parent_topic

        def should_be_executed_many_times(self, topic):
            expect(topic).to_equal(1)

        class SubSubContext(Vows.Context):
            def topic(self, parent_topic, outer_topic):
                return outer_topic

            def should_be_executed_many_times(self, topic):
                expect(topic).to_equal(1)

    class GeneratorAgainContext(Vows.Context):
        def topic(self, topic):
            for i in range(10):
                yield topic * 2

        def should_return_topic_times_two(self, topic):
            expect(topic).to_equal(2)


def add(a, b):
    return a + b

a_samples = range(10)
b_samples = range(10)


@Vows.batch
class Add(Vows.Context):
    class ATopic(Vows.Context):
        def topic(self):
            for a in a_samples:
                yield a

        class BTopic(Vows.Context):
            def topic(self, a):
                for b in b_samples:
                    yield b

            class Sum(Vows.Context):
                def topic(self, b, a):
                    yield (add(a, b), a + b)

                def should_be_numeric(self, topic):
                    value, expected = topic
                    expect(value).to_be_numeric()

                def should_equal_to_expected(self, topic):
                    value, expected = topic
                    expect(value).to_equal(expected)

########NEW FILE########
__FILENAME__ = multiple_topic_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class MultipleTopics(Vows.Context):
    class FirstLevel(Vows.Context):
        def topic(self):
            return 'a'

        def is_a(self, topic):
            expect(topic).to_equal('a')

        class SecondLevel(Vows.Context):
            def topic(self, first):
                return (first, 'b')

            def still_a(self, topic):
                expect(topic[0]).to_equal('a')

            def is_b(self, topic):
                expect(topic[1]).to_equal('b')

            class ThirdLevel(Vows.Context):
                def topic(self, second, first):
                    return (first, second[1], 'c')

                def still_a(self, topic):
                    expect(topic[0]).to_equal('a')

                def still_b(self, topic):
                    expect(topic[1]).to_equal('b')

                def is_c(self, topic):
                    expect(topic[2]).to_equal('c')

########NEW FILE########
__FILENAME__ = no_subcontext_extension_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect


@Vows.batch
class ContextClass(Vows.Context):
    entered = False

    def topic(self):
        return 1

    def should_be_working_fine(self, topic):
        expect(topic).to_equal(1)

    def teardown(self):
        # note to readers: 'expect's are not recommended on teardown methods
        expect(self.entered).to_equal(True)

    class SubcontextThatDoesntNeedToExtendAgainFromContext:
        entered = False

        def topic(self):
            return 2

        def should_be_working_fine_too(self, topic):
            self.parent.entered = True
            expect(topic).to_equal(2)

        def teardown(self):
            # note to readers: 'expect's are not recommended on teardown methods
            expect(self.entered).to_equal(True)

        class SubcontextThatDoesntNeedToExtendAgainFromContext:
            def topic(self):
                return 3

            def should_be_working_fine_too(self, topic):
                self.parent.entered = True
                expect(topic).to_equal(3)

########NEW FILE########
__FILENAME__ = error_reporting_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2013 Richard Lupton r.lupton@gmail.com

from pyvows import Vows, expect
from pyvows.reporting import VowsDefaultReporter
from pyvows.runner.abc import VowsTopicError

# These tests check that the reporting, which happens after all tests
# have run, correctly shows the errors raised in topic functions.

@Vows.batch
class ErrorReporting(Vows.Context):

    class TracebackOfTopicError:

        def setup(self):
            # The eval_context() method of the result object is called by
            # the reporter to decide if a context was successful or
            # not. Here we are testing the reporting of errors, so provide
            # a mock result which always says it has failed.
            class MockResult:
                def eval_context(self, context):
                    return False
            self.reporter = VowsDefaultReporter(MockResult(), 0)

            # Patch the print_traceback() method to just record its
            # arguments.
            self.print_traceback_args = None
            def print_traceback(*args):
                self.print_traceback_args = args
            self.reporter.print_traceback = print_traceback

        class AContextWithATopicError:
            def topic(self):
                # Simulate a context whose topic() function raised an error
                mock_exc_info = ('type', 'value', 'traceback')
                context = {
                    'contexts': [],
                    'error': VowsTopicError('topic', mock_exc_info),
                    'filename': '/path/to/vows.py',
                    'name': 'TestContext',
                    'tests': [],
                    'topic_elapsed': 0
                }
                return context

            def reporter_should_call_print_traceback_with_the_exception(self, context):
                self.parent.print_traceback_args = None
                self.parent.reporter.print_context('TestContext', context)
                expect(self.parent.print_traceback_args).to_equal(('type', 'value', 'traceback'))

        class ASuccessfulContext:
            def topic(self):
                # Simulate a context whose topic() didn't raise an error
                context = {
                    'contexts': [],
                    'error': None,
                    'filename': '/path/to/vows.py',
                    'name': 'TestContext',
                    'tests': [],
                    'topic_elapsed': 0
                }
                return context

            def reporter_should_not_call_print_traceback(self, context):
                self.parent.print_traceback_args = None
                self.parent.reporter.print_context('TestContext', context)
                expect(self.parent.print_traceback_args).to_equal(None)

########NEW FILE########
__FILENAME__ = reporting_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect
from pyvows.reporting import VowsDefaultReporter


@Vows.batch
class CoverageXMLParser(Vows.Context):

    def topic(self):
        return VowsDefaultReporter(None, 0)

    def should_be_an_instance_of_class(self, inst):
        expect(inst).to_be_instance_of(VowsDefaultReporter)

    class WhenParseCoverageXMLResult:
        """
            {'overall': 99.0, 'classes': [ {'name': 'pyvows.cli', 'line_rate': 0.0568, 'uncovered_lines':[ 12, 13 ] }, ] }
        """

        def topic(self, default_reporter):
            return default_reporter.parse_coverage_xml('''<?xml version="1.0" ?>
<!DOCTYPE coverage
  SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
<coverage branch-rate="0" line-rate="0.99" timestamp="1331692518922" version="3.5.1">
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.99" name="pyvows">
            <classes>
                <class branch-rate="0" complexity="0" filename="pyvows/cli.py" line-rate="0.568" name="cli">
                    <methods/>
                    <lines>
                        <line hits="0" number="12"/>
                        <line hits="1" number="13"/>
                        <line hits="0" number="14"/>
                    </lines>
                </class>
            </classes>
        </package>
        <package branch-rate="0" complexity="0" line-rate="0.99" name="tests">
            <classes>
                <class branch-rate="0" complexity="0" filename="tests/bla.py" line-rate="0.88" name="bla">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                        <line hits="0" number="2"/>
                        <line hits="0" number="3"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>''')

        def should_return_a_dict(self, result):
            expect(result).to_be_instance_of(dict)

        def should_contain_only_one_package(self, result):
            expect(len(result['classes'])).to_equal(2)

        def should_be_overall_99(self, result):
            expect(result['overall']).to_equal(0.99)

        class TheFirstClass(Vows.Context):

            def topic(self, result):
                return result['classes'][0]

            def should_be_pyvows_cli(self, klass):
                expect(klass['name']).to_equal('pyvows.cli')

            def should_contain_linehate(self, klass):
                expect(klass['line_rate']).to_equal(0.568)

            def should_contain_lines_uncovered(self, klass):
                expect(klass['uncovered_lines']).to_equal(['12', '14'])

        class TheSecondClass(Vows.Context):

            def topic(self, result):
                return result['classes'][1]

            def should_be_pyvowsconsole(self, klass):
                expect(klass['name']).to_equal('tests.bla')

            def should_contain_linehate(self, klass):
                expect(klass['line_rate']).to_equal(0.88)

            def should_contain_lines_uncovered(self, klass):
                expect(klass['uncovered_lines']).to_equal(['2', '3'])

########NEW FILE########
__FILENAME__ = xunit_reporter_vows
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyvows testing engine
# https://github.com/heynemann/pyvows

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 Bernardo Heynemann heynemann@gmail.com

from pyvows import Vows, expect
from pyvows.reporting.xunit import XUnitReporter


class ResultMock():
    pass


@Vows.batch
class XUnitReporterVows(Vows.Context):

    class WhenShowingZeroTests(Vows.Context):
        def topic(self):
            result = ResultMock()
            result.successful_tests = 0
            result.errored_tests = 0
            result.elapsed_time = 0
            result.contexts = []
            reporter = XUnitReporter(result)
            return reporter

        def should_create_xml_header(self, topic):
            expect(topic.to_xml().find('<?xml version="1.0" encoding="utf-8"?>')).to_equal(0)

        def should_have_a_testsuite_node(self, topic):
            expect(topic.to_xml()).to_match(r'.*<testsuite errors="0" failures="0" hostname=".+?" ' +
                                            'name="pyvows" tests="0" time="0\.000" timestamp=".+?"/>')

        class WithDocument(Vows.Context):
            def topic(self, topic):
                return topic.create_report_document()

            def should_have_a_testsuite_node(self, topic):
                expect(topic.firstChild.nodeName).to_equal('testsuite')

    class WhenShowingASuccessfulResult(Vows.Context):
        def topic(self):
            result = ResultMock()
            result.successful_tests = 1
            result.errored_tests = 0
            result.elapsed_time = 0
            result.contexts = [
                {
                    'name': 'Context1',
                    'tests': [
                        {
                            'name': 'Test1',
                            'succeeded': True
                        }
                    ],
                    'contexts': []
                }
            ]
            reporter = XUnitReporter(result)
            return reporter.create_report_document().firstChild.firstChild

        def should_create_a_testcase_node(self, topic):
            expect(topic.nodeName).to_equal('testcase')

        def should_set_classname_for_context(self, topic):
            expect(topic.getAttribute('classname')).to_equal('Context1')

        def should_set_name_for_context(self, topic):
            expect(topic.getAttribute('name')).to_equal('Test1')

########NEW FILE########
__FILENAME__ = utils_vows
# -*- coding: utf-8 -*-
##  Generated by PyVows v2.0.0  (2013/05/25)
##  http://pyvows.org

##  IMPORTS  ##
##
##  Standard Library
#
##  Third Party
#
##  PyVows Testing
from pyvows import Vows, expect

##  Local Imports
#import


##  TESTS  ##
@Vows.batch
class Utils(Vows.Context):

    def topic(self):
        return # return what you're going to test here

    ##  Now, write some vows for your topic! :)
    def should_do_something(self, topic):
        expect(topic)# <pyvows assertion here>


########NEW FILE########
__FILENAME__ = version_vows
# -*- coding: utf-8 -*-

from pyvows import Vows, expect
import pyvows.version as pyvows_version


@Vows.batch
class PyvowsVersionModule(Vows.Context):
    def topic(self):
        return pyvows_version

    def has_a_docstring(self, topic):
        expect(hasattr(topic, '__doc__')).to_be_true()

    class VersionNumber(Vows.Context):
        def topic(self, topic):
            return topic.__version__

        def should_be_a_tuple(self, topic):
            expect(topic).to_be_instance_of(tuple)

        def should_have_length_of_3(self, topic):
            expect(topic).to_length(3)

        def shoud_not_be_empty(self, topic):
            expect(topic).Not.to_be_empty()

        def should_not_be_None(self, topic):
            expect(topic).Not.to_be_null()

    class VersionString(Vows.Context):
        def topic(self, topic):
            return topic.to_str()

        def should_not_be_empty(self, topic):
            expect(topic).Not.to_be_empty()

        def should_not_be_None(self, topic):
            expect(topic).Not.to_be_null()

        def should_be_a_string(self, topic):
            expect(topic).to_be_instance_of(str)

########NEW FILE########
