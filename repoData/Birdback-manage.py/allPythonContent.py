__FILENAME__ = cli
from __future__ import absolute_import

import os
import getpass
from glob import glob
import sys

try:
    raw_input
except NameError:
    raw_input = input

try:
    from collections import OrderedDict
except ImportError:
    from .packages.ordereddict import OrderedDict  # NOQA

__all__ = ('Args', )

STDOUT = sys.stdout.write
NEWLINES = ('\n', '\r', '\r\n')


class Args(object):
    """CLI Argument management."""

    def __init__(self, args=None, no_argv=False):
        if args is None:
            if not no_argv:
                self._args = sys.argv[1:]
            else:
                self._args = []
        else:
            self._args = args

    def __len__(self):
        return len(self._args)

    def __repr__(self):
        return '<args %s>' % (repr(self._args))

    def __getitem__(self, i):
        try:
            return self.all[i]
        except IndexError:
            return None

    def __contains__(self, x):
        return self.first(x) is not None

    def get(self, x):
        """Returns argument at given index, else none."""
        try:
            return self.all[x]
        except IndexError:
            return None

    def get_with(self, x):
        """Returns first argument that contains given string."""
        return self.all[self.first_with(x)]

    def remove(self, x):
        """Removes given arg (or list thereof) from Args object."""

        def _remove(x):
            found = self.first(x)
            if found is not None:
                self._args.pop(found)

        if is_collection(x):
            for item in x:
                _remove(x)
        else:
            _remove(x)

    def pop(self, x):
        """Removes and Returns value at given index, else none."""
        try:
            return self._args.pop(x)
        except IndexError:
            return None

    def any_contain(self, x):
        """Tests if given string is contained in any stored argument."""

        return bool(self.first_with(x))

    def contains(self, x):
        """Tests if given object is in arguments list.
           Accepts strings and lists of strings."""

        return self.__contains__(x)

    def first(self, x):
        """Returns first found index of given value (or list of values)"""

        def _find(x):
            try:
                return self.all.index(str(x))
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found is not None:
                    return found
            return None
        else:
            return _find(x)

    def first_with(self, x):
        """Returns first found index containing value (or list of values)"""

        def _find(x):
            try:
                for arg in self.all:
                    if x in arg:
                        return self.all.index(arg)
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found:
                    return found
            return None
        else:
            return _find(x)

    def first_without(self, x):
        """Returns first found index not containing value (or list of values).
        """

        def _find(x):
            try:
                for arg in self.all:
                    if x not in arg:
                        return self.all.index(arg)
            except ValueError:
                return None

        if is_collection(x):
            for item in x:
                found = _find(item)
                if found:
                    return found
            return None
        else:
            return _find(x)

    def start_with(self, x):
        """Returns all arguments beginning with given string (or list thereof).
        """

        _args = []

        for arg in self.all:
            if is_collection(x):
                for _x in x:
                    if arg.startswith(x):
                        _args.append(arg)
                        break
            else:
                if arg.startswith(x):
                    _args.append(arg)

        return Args(_args, no_argv=True)

    def contains_at(self, x, index):
        """Tests if given [list of] string is at given index."""

        try:
            if is_collection(x):
                for _x in x:
                    if (_x in self.all[index]) or (_x == self.all[index]):
                        return True
                    else:
                        return False
            else:
                return (x in self.all[index])

        except IndexError:
            return False

    def has(self, x):
        """Returns true if argument exists at given index.
           Accepts: integer.
        """

        try:
            self.all[x]
            return True
        except IndexError:
            return False

    def value_after(self, x):
        """Returns value of argument after given found argument
        (or list thereof).
        """

        try:
            try:
                i = self.all.index(x)
            except ValueError:
                return None

            return self.all[i + 1]

        except IndexError:
            return None

    @property
    def grouped(self):
        """Extracts --flag groups from argument list.
           Returns {format: Args, ...}
        """

        collection = OrderedDict(_=Args(no_argv=True))

        _current_group = None

        for arg in self.all:
            if arg.startswith('-'):
                _current_group = arg
                collection[arg] = Args(no_argv=True)
            else:
                if _current_group:
                    collection[_current_group]._args.append(arg)
                else:
                    collection['_']._args.append(arg)

        return collection

    @property
    def last(self):
        """Returns last argument."""

        try:
            return self.all[-1]
        except IndexError:
            return None

    @property
    def all(self):
        """Returns all arguments."""

        return self._args

    def all_with(self, x):
        """Returns all arguments containing given string (or list thereof)"""

        _args = []

        for arg in self.all:
            if is_collection(x):
                for _x in x:
                    if _x in arg:
                        _args.append(arg)
                        break
            else:
                if x in arg:
                    _args.append(arg)

        return Args(_args, no_argv=True)

    def all_without(self, x):
        """Returns all arguments not containing given string (or list thereof).
        """

        _args = []

        for arg in self.all:
            if is_collection(x):
                for _x in x:
                    if _x not in arg:
                        _args.append(arg)
                        break
            else:
                if x not in arg:
                    _args.append(arg)

        return Args(_args, no_argv=True)

    @property
    def flags(self):
        """Returns Arg object including only flagged arguments."""

        return self.start_with('-')

    @property
    def not_flags(self):
        """Returns Arg object excluding flagged arguments."""

        return self.all_without('-')

    @property
    def files(self, absolute=False):
        """Returns an expanded list of all valid paths that were passed in."""

        _paths = []

        for arg in self.all:
            for path in expand_path(arg):
                if os.path.exists(path):
                    if absolute:
                        _paths.append(os.path.abspath(path))
                    else:
                        _paths.append(path)

        return _paths

    @property
    def not_files(self):
        """Returns a list of all arguments that aren't files/globs."""

        _args = []

        for arg in self.all:
            if not len(expand_path(arg)):
                if not os.path.exists(arg):
                    _args.append(arg)

        return Args(_args, no_argv=True)

    @property
    def copy(self):
        """Returns a copy of Args object for temporary manipulation."""

        return Args(self.all)


def expand_path(path):
    """Expands directories and globs in given path."""

    paths = []
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)

    if os.path.isdir(path):

        for (dir, dirs, files) in os.walk(path):
            for file in files:
                paths.append(os.path.join(dir, file))
    else:
        paths.extend(glob(path))

    return paths


def is_collection(obj):
    """Tests if an object is a collection. Strings don't count."""

    if isinstance(obj, basestring):
        return False

    return hasattr(obj, '__getitem__')


class Writer(object):
    """WriterUtilized by context managers."""

    shared = dict(indent_level=0, indent_strings=[])

    def __init__(self, indent=0, quote='', indent_char=' '):
        self.indent = indent
        self.indent_char = indent_char
        self.indent_quote = quote
        if self.indent > 0:
            self.indent_string = ''.join((
                str(quote),
                (self.indent_char * (indent - len(self.indent_quote)))
            ))
        else:
            self.indent_string = ''.join((
                ('\x08' * (-1 * (indent - len(self.indent_quote)))),
                str(quote))
            )

        if len(self.indent_string):
            self.shared['indent_strings'].append(self.indent_string)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shared['indent_strings'].pop()

    def __call__(self, s, newline=True, stream=STDOUT):
        if newline:
            s = tsplit(s, NEWLINES)
            s = map(str, s)
            indent = ''.join(self.shared['indent_strings'])

            s = (str('\n' + indent)).join(s)

        _str = ''.join((
            ''.join(self.shared['indent_strings']),
            str(s),
            '\n' if newline else ''
        ))
        stream(_str)


def puts(s='', newline=True, stream=STDOUT):
    """Prints given string to stdout via Writer interface."""
    Writer()(s, newline, stream=stream)


def indent(indent=4, quote=''):
    """Indentation context manager."""
    return Writer(indent=indent, quote=quote)


def tsplit(string, delimiters):
    """Behaves str.split but supports tuples of delimiters."""

    delimiters = tuple(delimiters)
    stack = [string, ]

    for delimiter in delimiters:
        for i, substring in enumerate(stack):
            substack = substring.split(delimiter)
            stack.pop(i)
            for j, _substring in enumerate(substack):
                stack.insert(i + j, _substring)

    return stack


def min_width(string, cols, padding=' '):
    """Returns given string with right padding."""

    stack = tsplit(str(string), NEWLINES)

    for i, substring in enumerate(stack):
        _sub = substring.ljust((cols + 0), padding)
        stack[i] = _sub

    return '\n'.join(stack)


TRUE_CHOICES = ('y', 'yes')
FALSE_CHOICES = ('n', 'no')


def process_value(value, empty=False, type=str, default=None, allowed=None,
        true_choices=TRUE_CHOICES, false_choices=FALSE_CHOICES):
    """Process prompted value.

    :param str value: The value to process.
    :param bool empty: Allow empty value.
    :param type type: The expected type.
    :param mixed default: The default value.
    :param tuple allowed: The allowed values.
    :param tuple true_choices: The accpeted values for True.
    :param tuple false_choices: The accepted values for False.
    """
    if allowed is not None and value not in allowed:
        raise Exception('Invalid input')

    if type is bool:
        if value in true_choices:
            return True
        if value in false_choices:
            return False
    if value in ('', '\n'):
        if default is not None:
            return default
        if empty:
            return None
        raise Exception('Invalid input')

    return type(value)


def prompt(message, empty=False, hidden=False, type=str, default=None,
        allowed=None, true_choices=TRUE_CHOICES, false_choices=FALSE_CHOICES,
        max_attempt=3, confirm=False):
    """Prompt user for value.

    :param str message: The prompt message.
    :param bool empty: Allow empty value.
    :param bool hidden: Hide user input.
    :param type type: The expected type.
    :param mixed default: The default value.
    :param tuple allowed: The allowed values.
    :param tuple true_choices: The accpeted values for True.
    :param tuple false_choices: The accepted values for False.
    :param int max_attempt: How many times the user is prompted back in case
        of invalid input.
    :param bool confirm: Enforce confirmation.
    """
    from manager import Error

    if allowed is not None and empty:
        allowed = allowed + ('', '\n')

    if type is bool:
        allowed = true_choices + false_choices

    if allowed is not None:
        message = "%s [%s]" % (message, ", ".join(allowed))

    if default is not None:
        message = "%s (default: %s) " % (message, default)

    handler = raw_input
    if hidden:
        handler = getpass.getpass

    attempt = 0

    while attempt < max_attempt:
        try:
            value = process_value(
                handler("%s : " % message),
                empty=empty,
                type=type,
                default=default,
                allowed=allowed,
                true_choices=true_choices,
                false_choices=false_choices,
            )
            break
        except:
            attempt = attempt + 1

            if attempt == max_attempt:
                raise Error('Invalid input')

    if confirm:
        confirmation = prompt("%s (again)" % message, empty=empty,
            hidden=hidden, type=type, default=default, allowed=allowed,
            true_choices=true_choices, false_choices=false_choices,
            max_attempt=max_attempt)

        if value != confirmation:
            raise Error('Values do not match')

    return value


class Colored(object):
    def __init__(self, color, string):
        self.color = color
        self.string = string

    def __len__(self):
        return len(self.string)

    def __str__(self):
        if sys.stdout.isatty():
            return "%s%s\033[0m" % (self.color, self.string)
        return self.string

    def __eq__(self, other):
        return self.string == other


def blue(string):
    return Colored('\033[94m', string)


def green(string):
    return Colored('\033[92m', string)


def red(string):
    return Colored('\033[91m', string)

########NEW FILE########
__FILENAME__ = nosetests
# -*- coding: utf-8 -*-
from nose.core import run_exit
from nose.tools import nottest


@nottest
def test(argv):
    """Run nosetests.

    Usage::

        from manager import Manager
        from manager.ext.nosetests import test
        manager = Manager()
        manager.command(test, capture_all=True)

    """
    argv = [''] + argv
    all_ = '--all-modules'
    if not all_ in argv:
        argv.append(all_)
    log_level = '--logging-level'
    if not log_level in argv:
        argv = argv + ['--logging-level', 'WARN']
    run_exit(argv=argv)

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
import os
import imp
import sys

from manager import cli, puts


def main():
    try:
        sys.path.append(os.getcwd())
        imp.load_source('manage_file', os.path.join(os.getcwd(), 'manage.py'))
    except IOError as exc:
        return puts(cli.red(exc))

    from manage_file import manager

    manager.main()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import os
import sys
import unittest
import re

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO  # NOQA

from manager import Arg, Command, Error, Manager, PromptedArg, puts
from manager.cli import process_value, prompt, TRUE_CHOICES, FALSE_CHOICES


manager = Manager()


class StdOut(StringIO):
    def __init__(self, stdin, prompts=None):
        StringIO.__init__(self)
        self.stdin = stdin
        self.prompts = prompts or {}

    def write(self, message):
        for key, value in self.prompts:
            if re.search(key, message):
                self.stdin.truncate(0)
                self.stdin.write(value)
                self.stdin.seek(0)
                return

        StringIO.write(self, message)


class capture(object):
    """Captures the std output.
    """
    def __init__(self, prompts=None):
        self.prompts = prompts

    def __enter__(self):
        self._stdout = sys.stdout
        self._stdin = sys.stdin
        sys.stdin = StringIO()
        sys.stdout = StdOut(sys.stdin, prompts=self.prompts)
        return sys.stdout

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout
        sys.stdin = self._stdin


class ClassBased(manager.Command):
    def run(self, name, capitalyze=False):
        if capitalyze:
            return name.upper()
        return name


@manager.command
def simple_command(name, capitalyze=False):
    if capitalyze:
        return name.upper()
    return name


@manager.command(namespace='my_namespace')
def namespaced(name):
    """namespaced command"""

    return name


@manager.command
def raises():
    raise Error('No way dude!')


class ArgTest(unittest.TestCase):
    def test_kwargs_required(self):
        kwargs = Arg('name', required=True).kwargs
        self.assertNotIn('required', kwargs)

    def test_kwargs_bool_false(self):
        kwargs = Arg('name', default=False, type=bool).kwargs
        self.assertNotIn('type', kwargs)
        self.assertEqual(kwargs['action'], 'store_true')


class CommandTest(unittest.TestCase):
    def test_registration(self):
        class MyCommand(manager.Command):
            pass

        self.assertIn('my_command', manager.commands)
        del manager.commands['my_command']

    def test_capture_usage(self):
        sys.argv[0] = 'manage.py'
        with capture() as c:
            manager.main(args=[])

        self.assertMultiLineEqual(
            c.getvalue(),
            """\
usage: manage.py [<namespace>.]<command> [<args>]

positional arguments:
  command     the command to run

optional arguments:
  -h, --help  show this help message and exit

available commands:
  class_based              no description
  raises                   no description
  simple_command           no description
  
  [my_namespace]
    namespaced             namespaced command
"""
        )

    def test_get_argument_existing(self):
        command = manager.commands['class_based']
        arg = command.get_argument('capitalyze')
        self.assertTrue(arg is not None)

    def test_get_argument_not_existing(self):
        command = manager.commands['class_based']
        self.assertRaises(Exception, command.get_argument, 'invalid')

    def test_inspect_class_based(self):
        args = manager.commands['class_based'].args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0].name, 'name')
        self.assertTrue(args[0].required)
        self.assertTrue(args[0].default is None)
        self.assertEqual(args[1].name, 'capitalyze')
        self.assertFalse(args[1].required)
        self.assertEqual(args[1].default, False)

    def test_inspect_function_based(self):
        args = manager.commands['simple_command'].args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0].name, 'name')
        self.assertTrue(args[0].required)
        self.assertTrue(args[0].default is None)
        self.assertEqual(args[1].name, 'capitalyze')
        self.assertFalse(args[1].required)
        self.assertEqual(args[1].default, False)

    def test_inspect_not_typed_optional_argument(self):
        new_manager = Manager()

        @new_manager.command
        def new_command(first_arg=None):
            return first_arg

        with capture() as c:
            new_manager.commands['new_command'].parse(['--first-arg', 'test'])

        self.assertNotIn(c.getvalue(), 'ERROR')

    def test_inspect_boolean_true(self):
        new_manager = Manager()

        @new_manager.command
        def new_command(arg=True):
            return 'true' if arg else 'false'

        with capture() as c:
            new_command.parse(['--no-arg'])

        self.assertIn('false', c.getvalue())

    def test_inspect_boolean_false(self):
        new_manager = Manager()

        @new_manager.command
        def new_command(arg=False):
            return 'true' if arg else 'false'

        with capture() as c:
            new_command.parse(['--arg'])

        self.assertIn('true', c.getvalue())

    def test_path_root(self):
        self.assertEqual(
            manager.commands['simple_command'].path,
            'simple_command'
        )

    def test_path_namespace(self):
        self.assertEqual(
            manager.commands['my_namespace.namespaced'].path,
            'my_namespace.namespaced'
        )

    def test_add_argument_existsing(self):
        command = Command(run=lambda new_argument: new_argument)
        self.assertEqual(len(command.args), 1)
        arg = Arg('new_argument', help='argument help')
        self.assertRaises(Exception, command.add_argument, arg)

    def test_capture_all(self):
        command = Command(run=lambda argv: argv, capture_all=True)
        self.assertEqual(len(command.args), 0)


class ManagerTest(unittest.TestCase):
    def test_command_decorator(self):
        self.assertIn('simple_command', manager.commands)
        self.assertEqual(len(manager.commands['simple_command'].args), 2)

    def test_command_decorator_kwargs(self):
        self.assertIn('my_namespace.namespaced', manager.commands)
        self.assertEqual(
            len(manager.commands['my_namespace.namespaced'].args),
            1
        )

    def test_command_decorator_doc(self):
        self.assertEqual(
            manager.commands['my_namespace.namespaced'].description,
            'namespaced command'
        )

    def test_base_command(self):
        class ExtendedCommand(Command):
            attribute = 'value'

        new_manager = Manager(base_command=ExtendedCommand)

        @new_manager.command
        def my_command():
            return True

        self.assertTrue(hasattr(my_command, 'attribute'))

    def test_arg_decorator(self):
        @manager.arg('first_arg', help='first help')
        @manager.arg('second_arg', help='second help')
        @manager.command
        def new_command(first_arg, second_arg):
            return first_arg

        command = manager.commands['new_command']
        self.assertEqual(command.args[0].help, 'first help')
        self.assertEqual(command.args[1].help, 'second help')

    def test_prompt_decorator(self):
        @manager.prompt('password', hidden=True)
        @manager.command
        def connect(username, password):
            return password

        self.assertTrue(isinstance(connect.args[1], PromptedArg))

    def test_arg_preserve_inspected(self):
        @manager.arg('first_arg', shortcut='f')
        @manager.command
        def new_command(first_arg=False):
            return first_arg

        command = manager.commands['new_command']
        arg, position = command.get_argument('first_arg')
        self.assertEqual(arg.shortcut, 'f')
        self.assertEqual(arg.kwargs['action'], 'store_true')
        self.assertEqual(arg.kwargs['default'], False)

    def test_arg_with_shortcut(self):
        @manager.arg('first_arg', shortcut='f')
        @manager.command
        def new_command(first_arg=None):
            return first_arg

        command = manager.commands['new_command']
        expected = 'test'

        with capture() as c:
            command.parse(['-f', expected])

        self.assertEqual(c.getvalue(), '%s\n' % expected)

    def test_arg_extra_arg(self):
        @manager.arg('second_arg')
        @manager.command
        def new_command(first_arg, **kwargs):
            return 'second_arg' in kwargs

        command = manager.commands['new_command']
        with capture() as c:
            command.parse(['first', '--second-arg', 'second value'])

        self.assertEqual(c.getvalue(), 'OK\n')

    def test_merge(self):
        new_manager = Manager()
        new_manager.add_command(Command(name='new_command'))
        manager.merge(new_manager)
        self.assertIn('new_command', manager.commands)

    def test_merge_namespace(self):
        new_manager = Manager()
        new_manager.add_command(Command(name='new_command'))
        manager.merge(new_manager, namespace='new_namespace')
        self.assertIn('new_namespace.new_command', manager.commands)

    def test_parse_error(self):
        with capture() as c:
            try:
                manager.commands['raises'].parse(list())
            except SystemExit:
                pass
        self.assertEqual(c.getvalue(), 'No way dude!\n')

    def test_parse_false(self):
        @manager.command
        def new_command(**kwargs):
            return False

        with capture():
            self.assertRaises(
                SystemExit,
                manager.commands['new_command'].parse, list()
            )

    def test_parse_env_simple(self):
        env = "key=value"
        self.assertEqual(manager.parse_env(env), dict(key='value'))

    def test_parse_env_quote(self):
        env = "key='value'"
        self.assertEqual(manager.parse_env(env), dict(key='value'))

    def test_parse_env_double_quote(self):
        env = 'key="value"'
        self.assertEqual(manager.parse_env(env), dict(key='value'))

    def test_parse_env_multiline(self):
        env = """key="value"
another_key=another value"""
        self.assertEqual(
            manager.parse_env(env), dict(
                key='value',
                another_key='another value'
            )
        )

    def test_env(self):
        new_manager = Manager()

        @new_manager.env('REQUIRED')
        @new_manager.env('OPTIONAL', value='bar')
        def throwaway(required=None, optional=None):
            return required, optional
        self.assertEqual(len(new_manager.env_vars['throwaway']), 2)
        if 'REQUIRED' in os.environ:
            del os.environ['REQUIRED']
        self.assertRaises(KeyError, throwaway)
        os.environ['REQUIRED'] = 'foo'
        req, opt = throwaway()
        self.assertEqual(req, 'foo')
        self.assertEqual(opt, 'bar')


class PutsTest(unittest.TestCase):
    def test_none(self):
        with capture() as c:
            puts(None)

        self.assertEqual(c.getvalue(), '')

    def test_empty(self):
        with capture() as c:
            puts('')

        self.assertEqual(c.getvalue(), '\n')

    def test_list_strip_carriage_returns(self):
        with capture() as c:
            puts(['first line\n', 'second line\n'])

        self.assertEqual(len(c.getvalue().splitlines()), 2)

    def test_dict(self):
        with capture() as c:
            puts({
                'key': 'value',
                'nonetype': None,
                'nested': {'deep': 'value'},
            })

        self.assertEqual(len(c.getvalue().splitlines()), 3)

    def test_true(self):
        with capture() as c:
            puts(True)

        self.assertEqual(c.getvalue(), 'OK\n')

    def test_false(self):
        with capture() as c:
            puts(False)

        self.assertEqual(c.getvalue(), 'FAILED\n')


BOOL_CHOICES = TRUE_CHOICES + FALSE_CHOICES


class PromptTest(unittest.TestCase):
    def test_process_value_boolean_empty(self):
        self.assertRaises(Exception, process_value, '', type=bool,
            allowed=BOOL_CHOICES)

    def test_process_value_boolean_true(self):
        self.assertEqual(True, process_value('y', type=bool,
            allowed=BOOL_CHOICES))

    def test_process_value_boolean_false(self):
        self.assertEqual(False, process_value('no', type=bool,
            allowed=BOOL_CHOICES))

    def test_process_value_valid_choice(self):
        value = process_value('first', allowed=('first', 'second'))
        self.assertEqual(value, 'first')

    def test_process_value_invalid_choice(self):
        self.assertRaises(Exception, process_value, 'third',
            allowed=('first', 'second'))

    def test_process_value_default(self):
        value = process_value('', default='default value')
        self.assertEqual(value, 'default value')

    def test_string(self):
        with capture(prompts=[('Simple prompt', 'simple value')]) as c:
            value = prompt('Simple prompt')

        self.assertEqual(value, 'simple value')

    def test_string_empty_allowed(self):
        name = 'Simple prompt'
        with capture(prompts=[(name, '\n')]) as c:
            value = prompt(name, empty=True)

        self.assertEqual(value, None)

    def test_string_empty_disallowed(self):
        name = 'Simple prompt'
        with capture(prompts=[(name, '')]) as c:
            self.assertRaises(Error, prompt, name)

    def test_string_default(self):
        name = 'Simple prompt'
        with capture(prompts=[(name, '\n')]) as c:
            value = prompt(name, default='default value')

        self.assertEqual(value, 'default value')

    def test_boolean_empty(self):
        name = 'Bool prompt'
        with capture(prompts=[(name, '\n')]) as c:
            self.assertRaises(Error, prompt, name, type=bool)

    def test_boolean_yes(self):
        name = 'Bool prompt'
        with capture(prompts=[(name, 'yes')]) as c:
            value = prompt(name, type=bool)

        self.assertEqual(value, True)

    def test_boolean_no(self):
        name = 'Bool prompt'
        with capture(prompts=[(name, 'n')]) as c:
            value = prompt(name, type=bool)

        self.assertEqual(value, False)

    def test_confirm_match(self):
        name, expected = 'Simple prompt', 'expected'
        with capture(prompts=[('%s \(again\)' % name, expected),
                (name, expected)]) as c:
            value = prompt(name, confirm=True)

        self.assertEqual(value, expected)

    def test_confirm_not_match(self):
        name, expected = 'Simple prompt', 'expected'
        with capture(prompts=[('%s \(again\)' % name, 'wrong value'),
                (name, expected)]) as c:
            self.assertRaises(Error, prompt, name, confirm=True)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
