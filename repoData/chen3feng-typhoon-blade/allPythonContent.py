__FILENAME__ = bootstrap
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
# Author: Feng Chen <phongchen@tencent.com>


"""This is the entry point to load and run blade package.
"""


import sys
import os.path

# Load package from blade.zip or source dir?
# blade_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'blade.zip'))
blade_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src/blade'))
sys.path.insert(0, blade_path)
import blade_main


blade_main.main(blade_path)


########NEW FILE########
__FILENAME__ = argparse
# Author: Steven J. Bethard <steven.bethard@gmail.com>.

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

__version__ = '1.1'
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
            msg = _('unknown parser %r (choices: %s)') % tup
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

    def __init__(self, mode='r', bufsize=-1):
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
                msg = _('argument "-" with mode %r') % self._mode
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, self._mode, self._bufsize)
        except IOError ,e:
            message = _("can't open '%s': %s")
            raise ArgumentTypeError(message % (string, e))

    def __repr__(self):
        args = self._mode, self._bufsize
        args_str = ', '.join(repr(arg) for arg in args if arg != -1)
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
            raise ValueError('unknown action "%s"' % (action_class,))
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            raise ValueError('%r is not callable' % (type_func,))

        # raise an error if the metavar does not match the type
        if hasattr(self, "_get_formatter"):
            try:
                self._get_formatter()._format_args(action, None)
            except TypeError:
                raise ValueError("length of metavar tuple does not match nargs")

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
        self._mutually_exclusive_groups = container._mutually_exclusive_groups

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
            self.error(_('too few arguments'))

        # make sure all required actions were present
        for action in self._actions:
            if action.required:
                if action not in seen_actions:
                    name = _get_action_name(action)
                    self.error(_('argument %s is required') % name)

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
                    self.error(msg % ' '.join(names))

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
        self._print_message(self.format_help(), file)

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
        if message:
            self._print_message(message, _sys.stderr)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        self.exit(2, _('%s: error: %s\n') % (self.prog, message))

########NEW FILE########
__FILENAME__ = binary_runner
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Authors: Huan Yu <huanyu@tencent.com>
#          Feng Chen <phongchen@tencent.com>
#          Yi Wang <yiwang@tencent.com>
#          Chong Peng <michaelpeng@tencent.com>
# Date: October 20, 2011


"""
 This is the TestRunner module which executes the test programs.

"""


import os
import shutil
import subprocess
import sys

import blade
import cc_targets
import console

from blade_util import environ_add_path


class BinaryRunner(object):
    """BinaryRunner. """
    def __init__(self, targets, options, target_database):
        """Init method. """
        self.targets = targets
        self.build_dir = blade.blade.get_build_path()
        self.options = options
        self.run_list = ['cc_binary',
                         'cc_test']
        self.target_database = target_database

    def _executable(self, target):
        """Returns the executable path. """
        return '%s/%s/%s' % (self.build_dir, target.path, target.name)

    def _runfiles_dir(self, target):
        """Returns runfiles dir. """
        return './%s.runfiles' % (self._executable(target))

    def _prepare_run_env(self, target):
        """Prepare the run environment. """
        profile_link_name = os.path.basename(self.build_dir)
        target_dir = os.path.dirname(self._executable(target))
        lib_link = os.path.join(target_dir, profile_link_name)
        if os.path.exists(lib_link):
            os.remove(lib_link)
        os.symlink(os.path.abspath(self.build_dir), lib_link)

    def _get_prebuilt_files(self, target):
        """Get prebuilt files for one target that it depends. """
        file_list = []
        for dep in target.expanded_deps:
            dep_target = self.target_database[dep]
            if dep_target.type == 'prebuilt_cc_library':
                prebuilt_file = dep_target.file_and_link
                if prebuilt_file:
                    file_list.append(prebuilt_file)
        return file_list

    def __check_link_name(self, link_name, link_name_list):
        """check the link name is valid or not. """
        link_name_norm = os.path.normpath(link_name)
        if link_name in link_name_list:
            return 'AMBIGUOUS', None
        long_path = ''
        short_path = ''
        for item in link_name_list:
            item_norm = os.path.normpath(item)
            if len(link_name_norm) >= len(item_norm):
                (long_path, short_path) = (link_name_norm, item_norm)
            else:
                (long_path, short_path) = (item_norm, link_name_norm)
            if long_path.startswith(short_path) and (
                    long_path[len(short_path)] == '/'):
                return 'INCOMPATIBLE', item
        else:
            return 'VALID', None

    def _prepare_env(self, target):
        """Prepare the test environment. """
        shutil.rmtree(self._runfiles_dir(target), ignore_errors=True)
        os.mkdir(self._runfiles_dir(target))
        # add build profile symlink
        profile_link_name = os.path.basename(self.build_dir)
        os.symlink(os.path.abspath(self.build_dir),
                   os.path.join(self._runfiles_dir(target), profile_link_name))

        # add pre build library symlink
        for prebuilt_file in self._get_prebuilt_files(target):
            src = os.path.abspath(prebuilt_file[0])
            dst = os.path.join(self._runfiles_dir(target), prebuilt_file[1])
            if os.path.lexists(dst):
                console.warning('trying to make duplicate prebuilt symlink:\n'
                                '%s -> %s\n'
                                '%s -> %s already exists\n'
                                'skipped, should check duplicate prebuilt '
                                'libraries'
                        % (dst, src, dst, os.path.realpath(dst)))
                continue
            os.symlink(src, dst)

        self._prepare_test_data(target)

    def _prepare_test_data(self, target):
        if 'testdata' not in target.data:
            return
        link_name_list = []
        for i in target.data['testdata']:
            if isinstance(i, tuple):
                data_target = i[0]
                link_name = i[1]
            else:
                data_target = link_name = i
            if '..' in data_target:
                continue
            if link_name.startswith('//'):
                link_name = link_name[2:]
            err_msg, item = self.__check_link_name(link_name, link_name_list)
            if err_msg == 'AMBIGUOUS':
                console.error_exit('Ambiguous testdata of //%s:%s: %s, exit...' % (
                             target.path, target.name, link_name))
            elif err_msg == 'INCOMPATIBLE':
                console.error_exit('%s could not exist with %s in testdata of //%s:%s' % (
                           link_name, item, target.path, target.name))
            link_name_list.append(link_name)
            try:
                os.makedirs(os.path.dirname('%s/%s' % (
                        self._runfiles_dir(target), link_name)))
            except OSError:
                pass

            symlink_name = os.path.abspath('%s/%s' % (
                                self._runfiles_dir(target), link_name))
            symlink_valid = False
            if os.path.lexists(symlink_name):
                if os.path.exists(symlink_name):
                    symlink_valid = True
                    console.warning('%s already existed, could not prepare '
                                    'testdata for //%s:%s' % (
                                        link_name, target.path, target.name))
                else:
                    os.remove(symlink_name)
                    console.warning('%s already existed, but it is a broken '
                                    'symbolic link, blade will remove it and '
                                    'make a new one.' % link_name)
            if data_target.startswith('//'):
                data_target = data_target[2:]
                dest_data_file = os.path.abspath(data_target)
            else:
                dest_data_file = os.path.abspath('%s/%s' % (target.path, data_target))

            if not symlink_valid:
                os.symlink(dest_data_file,
                           '%s/%s' % (self._runfiles_dir(target), link_name))

    def _clean_target(self, target):
        """clean the test target environment. """
        profile_link_name = os.path.basename(self.build_dir)
        profile_link_path = os.path.join(self._runfiles_dir(target), profile_link_name)
        if os.path.exists(profile_link_path):
            os.remove(profile_link_path)

    def _clean_env(self):
        """clean test environment. """
        for target in self.targets.values():
            if target.type != 'cc_test':
                continue
            self._clean_target(target)

    def run_target(self, target_key):
        """Run one single target. """
        target = self.targets[target_key]
        if target.type not in self.run_list:
            console.error_exit('target %s:%s is not a target that could run' % (
                       target_key[0], target_key[1]))
        self._prepare_env(target)
        cmd = [os.path.abspath(self._executable(target))] + self.options.args
        console.info("'%s' will be ran" % cmd)
        sys.stdout.flush()

        run_env = dict(os.environ)
        environ_add_path(run_env, 'LD_LIBRARY_PATH',
                         self._runfiles_dir(target))
        p = subprocess.Popen(cmd, env=run_env, close_fds=True)
        p.wait()
        self._clean_env()
        return p.returncode

########NEW FILE########
__FILENAME__ = blade
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the blade module which mainly holds the global database and
 do the coordination work between classes.

"""


import os

import configparse
import console

from blade_util import relative_path, cpu_count
from dependency_analyzer import analyze_deps
from load_build_files import load_targets
from blade_platform import SconsPlatform
from build_environment import BuildEnvironment
from rules_generator import SconsRulesGenerator
from binary_runner import BinaryRunner
from test_runner import TestRunner


# Global blade manager
blade = None


class Blade(object):
    """Blade. A blade manager class. """
    def __init__(self,
                 command_targets,
                 blade_path,
                 working_dir,
                 build_path,
                 blade_root_dir,
                 blade_options,
                 command):
        """init method.

        """
        self.__command_targets = command_targets
        self.__blade_path = blade_path
        self.__working_dir = working_dir
        self.__build_path = build_path
        self.__root_dir = blade_root_dir
        self.__options = blade_options
        self.__command = command

        # Source dir of current loading BUILD file
        self.__current_source_path = blade_root_dir

        # The direct targets that are used for analyzing
        self.__direct_targets = []

        # All command targets, make sure that all targets specified with ...
        # are all in the list now
        self.__all_command_targets = []

        # Given some targets specified in the command line, Blade will load
        # BUILD files containing these command line targets; global target
        # functions, i.e., cc_libarary, cc_binary and etc, in these BUILD
        # files will register targets into target_database, which then becomes
        # the input to dependency analyzer and SCons rules generator.  It is
        # notable that not all targets in target_database are dependencies of
        # command line targets.
        self.__target_database = {}

        # targets to build after loading the build files.
        self.__build_targets = {}

        # The targets keys list after sorting by topological sorting method.
        # Used to generate build rules in correct order.
        self.__sorted_targets_keys = []

        # Inidcating that whether the deps list is expanded by expander or not
        self.__targets_expanded = False

        self.__scons_platform = SconsPlatform()
        self.build_environment = BuildEnvironment(self.__root_dir)

        self.svn_root_dirs = []

    def _get_normpath_target(self, command_target):
        """returns a tuple (path, name).

        path is a full path from BLADE_ROOT

        """
        target_path = relative_path(self.__working_dir, self.__root_dir)
        path, name = command_target.split(':')
        if target_path != '.':
            if path:
                path = target_path + '/' + path
            else:
                path = target_path
        path = os.path.normpath(path)
        return path, name

    def load_targets(self):
        """Load the targets. """
        console.info('loading BUILDs...')
        if self.__command == 'query':
            working_dir = self.__root_dir

            if '...' not in self.__command_targets:
                new_target_list = []
                for target in self.__command_targets:
                    new_target_list.append('%s:%s' %
                            self._get_normpath_target(target))
                self.__command_targets = new_target_list
        else:
            working_dir = self.__working_dir
        (self.__direct_targets,
         self.__all_command_targets,
         self.__build_targets) = load_targets(self.__command_targets,
                                                  working_dir,
                                                  self.__root_dir,
                                                  self)
        console.info('loading done.')
        return self.__direct_targets, self.__all_command_targets  # For test

    def analyze_targets(self):
        """Expand the targets. """
        console.info('analyzing dependency graph...')
        self.__sorted_targets_keys = analyze_deps(self.__build_targets)
        self.__targets_expanded = True

        console.info('analyzing done.')
        return self.__build_targets  # For test

    def generate_build_rules(self):
        """Generate the constructing rules. """
        console.info('generating build rules...')
        build_rules_generator = SconsRulesGenerator('SConstruct',
                                                    self.__blade_path, self)
        rules_buf = build_rules_generator.generate_scons_script()
        console.info('generating done.')
        return rules_buf

    def generate(self):
        """Generate the build script. """
        self.load_targets()
        self.analyze_targets()
        self.generate_build_rules()

    def run(self, target):
        """Run the target. """
        key = self._get_normpath_target(target)
        runner = BinaryRunner(self.__build_targets,
                              self.__options,
                              self.__target_database)
        return runner.run_target(key)

    def test(self):
        """Run tests. """
        test_runner = TestRunner(self.__build_targets,
                                 self.__options,
                                 self.__target_database,
                                 self.__direct_targets)
        return test_runner.run()

    def query(self, targets):
        """Query the targets. """
        print_deps = getattr(self.__options, 'deps', False)
        print_depended = getattr(self.__options, 'depended', False)
        dot_file = getattr(self.__options, 'output_to_dot', '')
        result_map = self.query_helper(targets)
        if dot_file:
            print_mode = 0
            if print_deps:
                print_mode = 0
            if print_depended:
                print_mode = 1
            dot_file = os.path.join(self.__working_dir, dot_file)
            self.output_dot(result_map, print_mode, dot_file)
        else:
            if print_deps:
                for key in result_map:
                    print '\n'
                    deps = result_map[key][0]
                    console.info('//%s:%s depends on the following targets:' % (
                            key[0], key[1]))
                    for d in deps:
                        print '%s:%s' % (d[0], d[1])
            if print_depended:
                for key in result_map:
                    print '\n'
                    depended_by = result_map[key][1]
                    console.info('//%s:%s is depended by the following targets:' % (
                            key[0], key[1]))
                    depended_by.sort(key=lambda x: x, reverse=False)
                    for d in depended_by:
                        print '%s:%s' % (d[0], d[1])
        return 0

    def print_dot_node(self, output_file, node):
        print >>output_file, '"%s:%s" [label = "%s:%s"]' % (node[0],
                                                            node[1],
                                                            node[0],
                                                            node[1])

    def print_dot_deps(self, output_file, node, target_set):
        targets = self.__build_targets
        deps = targets[node].deps
        for i in deps:
            if not i in target_set:
                continue
            print >>output_file, '"%s:%s" -> "%s:%s"' % (node[0],
                                                         node[1],
                                                         i[0],
                                                         i[1])

    def output_dot(self, result_map, print_mode, dot_file):
        f = open(dot_file, 'w')
        targets = result_map.keys()
        nodes = set(targets)
        for key in targets:
            nodes |= set(result_map[key][print_mode])
        print >>f, 'digraph blade {'
        for i in nodes:
            self.print_dot_node(f, i)
        for i in nodes:
            self.print_dot_deps(f, i, nodes)
        print >>f, '}'
        f.close()

    def query_helper(self, targets):
        """Query the targets helper method. """
        all_targets = self.__build_targets
        query_list = []
        target_path = relative_path(self.__working_dir, self.__root_dir)
        t_path = ''
        for t in targets:
            key = t.split(':')
            if target_path == '.':
                t_path = key[0]
            else:
                t_path = target_path + '/' + key[0]
            t_path = os.path.normpath(t_path)
            query_list.append((t_path, key[1]))
        result_map = {}
        for key in query_list:
            result_map[key] = ([], [])
            deps = all_targets[key].expanded_deps
            deps.sort(key=lambda x: x, reverse=False)
            depended_by = []
            for tkey in all_targets:
                if key in all_targets[tkey].expanded_deps:
                    depended_by.append(tkey)
            depended_by.sort(key=lambda x: x, reverse=False)
            result_map[key] = (list(deps), list(depended_by))
        return result_map

    def get_build_path(self):
        """The current building path. """
        return self.__build_path

    def get_root_dir(self):
        """Return the blade root path. """
        return self.__root_dir

    def set_current_source_path(self, current_source_path):
        """Set the current source path. """
        self.__current_source_path = current_source_path

    def get_current_source_path(self):
        """Get the current source path. """
        return self.__current_source_path

    def get_target_database(self):
        """Get the whole target database that haven't been expanded. """
        return self.__target_database

    def get_direct_targets(self):
        """Return the direct targets. """
        return self.__direct_targets

    def get_build_targets(self):
        """Get all the targets to be build. """
        return self.__build_targets

    def get_options(self):
        """Get the global command options. """
        return self.__options

    def is_expanded(self):
        """Whether the targets are expanded. """
        return self.__targets_expanded

    def register_target(self, target):
        """Register scons targets into the scons targets map.

        It is used to do quick looking.

        """
        target_key = target.key
        # check that whether there is already a key in database
        if target_key in self.__target_database:
            print self.__target_database
            console.error_exit(
                    'target name %s is duplicate in //%s/BUILD' % (
                        target.name, target.path))
        self.__target_database[target_key] = target

    def _is_scons_object_type(self, target_type):
        """The types that shouldn't be registered into blade manager.

        Sholdn't invoke scons_rule method when it is not a scons target which
        could not be registered into blade manager, like system library.

        1. system_library

        """
        return target_type != 'system_library'

    def gen_targets_rules(self):
        """Get the build rules and return to the object who queries this. """
        rules_buf = []
        skip_test_targets = False
        if getattr(self.__options, 'no_test', False):
            skip_test_targets = True
        for k in self.__sorted_targets_keys:
            target = self.__build_targets[k]
            if not self._is_scons_object_type(target.type):
                continue
            scons_object = self.__target_database.get(k, None)
            if not scons_object:
                console.warning('not registered scons object, key %s' % str(k))
                continue
            if skip_test_targets and target.type == 'cc_test':
                continue
            scons_object.scons_rules()
            rules_buf += scons_object.get_rules()
        return rules_buf

    def get_scons_platform(self):
        """Return handle of the platform class. """
        return self.__scons_platform

    def get_sources_keyword_list(self):
        """This keywords list is used to check the source files path.

        Ex, when users specifies warning=no, it could be used to check that
        the source files is under thirdparty or not. If not, it will warn
        users that this flag is used incorrectly.

        """
        keywords = ['thirdparty']
        return keywords

    def tune_parallel_jobs_num(self):
        """Tune the jobs num. """
        user_jobs_num = self.__options.jobs
        jobs_num = 0
        cpu_core_num = cpu_count()
        distcc_enabled = configparse.blade_config.get_config('distcc_config')['enabled']

        if distcc_enabled and self.build_environment.distcc_env_prepared:
            jobs_num = int(1.5 * len(self.build_environment.get_distcc_hosts_list())) + 1
            if jobs_num > 20:
                jobs_num = 20
            if jobs_num and self.__options.jobs != jobs_num:
                self.__options.jobs = jobs_num
        elif self.__options.jobs < 1:
            if cpu_core_num <= 4:
                self.__options.jobs = 2 * cpu_core_num
            else:
                self.__options.jobs = cpu_core_num
                if self.__options.jobs > 8:
                    self.__options.jobs = 8
        if self.__options.jobs != user_jobs_num:
            console.info('tunes the parallel jobs number(-j N) to be %d' % (
                self.__options.jobs))
        return self.__options.jobs

########NEW FILE########
__FILENAME__ = blade_main
# Copyright 2011 Tencent Inc.
#
# Authors: Huan Yu <huanyu@tencent.com>
#          Feng Chen <phongchen@tencent.com>
#          Yi Wang <yiwang@tencent.com>
#          Chong Peng <michaelpeng@tencent.com>

"""
 Blade is a software building system built upon SCons, but restricts
 the generality and flexibility of SCons to prevent unnecessary
 error-prone complexity.  With Blade, users wrote a BUILD file and
 put it in each of the source directory.  In each BUILD file, there
 could be one or more build rules, each has a TARGET NAME, source
 files and dependent targets.  Blade suports the following types of
 build rules:


    cc_binary         -- build an executable binary from C++ source
    cc_library        -- build a library from C++ source
    cc_plugin         -- build a plugin from C++ source
    cc_test           -- build a unittest binary from C++ source
    cc_benchmark      -- build a benchmark binary from C++ source
    gen_rule          -- used to specify a general building rule
    java_jar          -- build java jar from java source files
    lex_yacc_library  -- build a library from lex/yacc source
    proto_library     -- build a library from Protobuf source
    thrift_library    -- build a library from Thrift source
    resource_library  -- build resource library and gen header files
    swig_library      -- build swig library for python and java

 A target may depend on other target(s), where the dependency is
 transitive.  A dependent target is referred by a TARGET ID, which
 has either of the following forms:

   //<source_dir>:<target_name> -- target defined in <source_dir>/BUILD
   :<target_name>               -- target defined in the current BUILD file
   #<target_name>               -- target is a system library, e.g., pthread

 where <source_dir> is an absolute path rooted at the source tree and
 specifying where the BUILD file locates, <target_name> specifies a
 target in the BUILD file, and '//' denotes the root of the source tree.

 Users invoke Blade from the command line to build (or clean, or
 test) one or more rule/targets.  In the command line, a target id
 is specified in either of the following forms:

   <path>:<target_name> -- to build target defined in <path>/BUILD
   <path>               -- to build all targets defined in <path>/BUILD
   <path>/...           -- to build all targets in all BUILD files in
                           <path> and its desendant directories.

 Note that <path> in command line targets is an operating system
 path, which might be a relative path, but <source_dir> in a BUILD
 referring to a dependent target must be an absolute path, rooted at
 '//'.

 For example, the following command line

    blade base mapreduce_lite/... parallel_svm:perf_test

 builds all targets in base/BUILD, all targets in all BUILDs under
 directory mapreduce_lite, and the target perf_test defined in
 parallel_svm/BUILD
"""


import errno
import fcntl
import os
import signal
import subprocess
import sys
import traceback
from string import Template

import blade
import console
import configparse

from blade import Blade
from blade_util import get_cwd
from blade_util import lock_file
from blade_util import unlock_file
from command_args import CmdArguments
from configparse import BladeConfig
from load_build_files import find_blade_root_dir


# Query targets
query_targets = None

# Run target
run_target = None


def is_svn_client(blade_root_dir):
    # We suppose that BLADE_ROOT is under svn root dir now.
    return os.path.exists(os.path.join(blade_root_dir, '.svn'))


# For our opensource projects (toft, thirdparty, foxy etc.), we mkdir a project
# dir , add subdirs are github repos, here we need to fix out the git ROOT for
# each build target
def is_git_client(blade_root_dir, target, working_dir):
    if target.endswith('...'):
        target = target[:-3]
    if os.path.exists(os.path.join(blade_root_dir, '.git')):
        return (True, blade_root_dir, target)
    blade_root_dir = os.path.normpath(blade_root_dir)
    root_dirs = blade_root_dir.split('/')
    full_target = os.path.normpath(os.path.join(working_dir, target))
    dirs = full_target.split('/')
    index = len(root_dirs)
    while index <= len(dirs):
        # Find git repo root dir
        top_dir = '/'.join(dirs[0:index])
        # Get subdir under git repo root
        sub_dir = '/'.join(dirs[index:])
        index += 1
        if (os.path.exists(os.path.join(top_dir, '.git'))):
            return (True, top_dir, sub_dir)
    return (False, None, None)


def _normalize_target_path(target):
    if target.endswith('...'):
        target = target[:-3]
    index = target.find(':')
    if index != -1:
        target = target[index + 1:]
    if target and not target.endswith('/'):
        target = target + '/'
    return target


def _get_opened_files(targets, blade_root_dir, working_dir):
    check_dir = set()
    opened_files = set()
    blade_root_dir = os.path.normpath(blade_root_dir)

    for target in targets:
        target = _normalize_target_path(target)
        d = os.path.dirname(target)
        if d in check_dir:
            return
        check_dir.add(d)
        output = []
        if is_svn_client(blade_root_dir):
            full_target = os.path.normpath(os.path.join(working_dir, d))
            top_dir = full_target[len(blade_root_dir) + 1:]
            output = os.popen('svn st %s' % top_dir).read().split('\n')
        else:
            (is_git, git_root, git_subdir) = is_git_client(blade_root_dir, target, working_dir)
            if is_git:
                os.chdir(git_root)
                status_cmd = 'git status --porcelain %s' % (git_subdir)
                output = os.popen(status_cmd).read().split('\n')
            else:
                console.warning('unknown source client type, NOT svn OR git')
        for f in output:
            seg = f.strip().split(' ')
            if seg[0] != 'M' and seg[0] != 'A':
                continue
            f = seg[len(seg) - 1]
            if f.endswith('.h') or f.endswith('.hpp') or f.endswith('.cc') or f.endswith('.cpp'):
                fullpath = os.path.join(os.getcwd(), f)
                opened_files.add(fullpath)
    return opened_files


def _check_code_style(opened_files):
    if not opened_files:
        return 0
    cpplint = configparse.blade_config.configs['cc_config']['cpplint']
    console.info('Begin to check code style for changed source code')
    p = subprocess.Popen(('%s %s' % (cpplint, ' '.join(opened_files))), shell=True)
    try:
        p.wait()
        if p.returncode:
            if p.returncode == 127:
                msg = ("Can't execute '{0}' to check style, you can config the "
                       "'cpplint' option to be a valid cpplint path in the "
                       "'cc_config' section of blade.conf or BLADE_ROOT, or "
                       "make sure '{0}' command is correct.").format(cpplint)
            else:
                msg = 'Please fixing style warnings before submitting the code!'
            console.warning(msg)
    except KeyboardInterrupt, e:
        console.error(str(e))
        return 1
    return 0


def _main(blade_path):
    """The main entry of blade. """

    cmd_options = CmdArguments()

    command = cmd_options.get_command()
    targets = cmd_options.get_targets()

    global query_targets
    global run_target
    if command == 'query':
        query_targets = list(targets)
    if command == 'run':
        run_target = targets[0]

    if not targets:
        targets = ['.']
    options = cmd_options.get_options()

    # Set blade_root_dir to the directory which contains the
    # file BLADE_ROOT, is upper than and is closest to the current
    # directory.  Set working_dir to current directory.
    working_dir = get_cwd()
    blade_root_dir = find_blade_root_dir(working_dir)
    os.chdir(blade_root_dir)

    if blade_root_dir != working_dir:
        # This message is required by vim quickfix mode if pwd is changed during
        # the building, DO NOT change the pattern of this message.
        print >>sys.stderr, "Blade: Entering directory `%s'" % blade_root_dir

    # Init global configuration manager
    configparse.blade_config = BladeConfig(blade_root_dir)
    configparse.blade_config.parse()

    # Check code style using cpplint.py
    if command == 'build' or command == 'test':
        opened_files = _get_opened_files(targets, blade_root_dir, working_dir)
        os.chdir(blade_root_dir)
        _check_code_style(opened_files)

    # Init global blade manager.
    
    build_path_format = configparse.blade_config.configs['global_config']['build_path_template']
    s = Template(build_path_format)
    current_building_path = s.substitute(m=options.m, profile=options.profile)

    lock_file_fd = None
    locked_scons = False
    try:
        lock_file_fd = open('.Building.lock', 'w')
        old_fd_flags = fcntl.fcntl(lock_file_fd.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(lock_file_fd.fileno(), fcntl.F_SETFD, old_fd_flags | fcntl.FD_CLOEXEC)

        (locked_scons,
         ret_code) = lock_file(lock_file_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not locked_scons:
            if ret_code == errno.EAGAIN:
                console.error_exit(
                        'There is already an active building in current source '
                        'dir tree. Blade will exit...')
            else:
                console.error_exit('Lock exception, please try it later.')

        if command == 'query' and getattr(options, 'depended', None):
            targets = ['...']
        blade.blade = Blade(targets,
                            blade_path,
                            working_dir,
                            current_building_path,
                            blade_root_dir,
                            options,
                            command)

        # Build the targets
        blade.blade.generate()

        # Flush the printing
        sys.stdout.flush()
        sys.stderr.flush()

        # Tune the jobs num
        if command in ['build', 'run', 'test']:
            options.jobs = blade.blade.tune_parallel_jobs_num()

        # Switch case due to different sub command
        action = {
                 'build': build,
                 'run': run,
                 'test': test,
                 'clean': clean,
                 'query': query
                 }[command](options)
        return action
    finally:
        if (not getattr(options, 'scons_only', False) or
                command == 'clean' or command == 'query'):
            try:
                if locked_scons:
                    os.remove(os.path.join(blade_root_dir, 'SConstruct'))
                    unlock_file(lock_file_fd.fileno())
                if lock_file_fd:
                    lock_file_fd.close()
            except OSError:
                pass
    return 0


def _build(options):
    if options.scons_only:
        return 0

    scons_options = '--duplicate=soft-copy --cache-show'
    scons_options += ' -j %s' % options.jobs
    if options.keep_going:
        scons_options += ' -k'

    p = subprocess.Popen('scons %s' % scons_options, shell=True)
    try:
        p.wait()
        if p.returncode:
            console.error('building failure')
            return p.returncode
    except:  # KeyboardInterrupt
        return 1
    return 0


def build(options):
    return _build(options)


def run(options):
    ret = _build(options)
    if ret:
        return ret
    return blade.blade.run(run_target)


def test(options):
    ret = _build(options)
    if ret:
        return ret
    return blade.blade.test()


def clean(options):
    console.info('cleaning...(hint: please specify --generate-dynamic to '
                 'clean your so)')
    p = subprocess.Popen('scons --duplicate=soft-copy -c -s --cache-show',
                         shell=True)
    p.wait()
    console.info('cleaning done.')
    return p.returncode


def query(options):
    return blade.blade.query(query_targets)


def main(blade_path):
    exit_code = 0
    try:
        exit_code = _main(blade_path)
    except SystemExit, e:
        exit_code = e.code
    except KeyboardInterrupt:
        console.error_exit('keyboard interrupted', -signal.SIGINT)
    except:
        console.error_exit(traceback.format_exc())
    sys.exit(exit_code)

########NEW FILE########
__FILENAME__ = blade_platform
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Chong Peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the blade_platform module which dues with the environment
 variable.

"""


import os
import subprocess

import configparse
from blade_util import var_to_list


class SconsPlatform(object):
    """The scons platform class that it handles and gets the platform info. """
    def __init__(self):
        """Init. """
        self.gcc_version = self._get_gcc_version('gcc')
        self.python_inc = self._get_python_include()
        self.php_inc_list = self._get_php_include()
        self.java_inc_list = self._get_java_include()
        self.nvcc_version = self._get_nvcc_version('nvcc')
        self.cuda_inc_list = self._get_cuda_include()

    @staticmethod
    def _get_gcc_version(compiler):
        """Get the gcc version. """
        p = subprocess.Popen(
            compiler + ' --version',
            env=os.environ,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            version_line = stdout.splitlines(True)[0]
            version = version_line.split()[2]
            return version
        return ''

    @staticmethod
    def _get_nvcc_version(compiler):
        """Get the nvcc version. """
        p = subprocess.Popen(
            compiler + ' --version',
            env=os.environ,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            version_line = stdout.splitlines(True)[-1]
            version = version_line.split()[5]
            return version
        return ''

    @staticmethod
    def _get_python_include():
        """Get the python include dir. """
        p = subprocess.Popen(
            'python-config --includes',
            env=os.environ,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            include_line = stdout.splitlines(True)[0]
            header = include_line.split()[0][2:]
            return header
        return ''

    @staticmethod
    def _get_php_include():
        p = subprocess.Popen(
            'php-config --includes',
            env=os.environ,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            include_line = stdout.splitlines(True)[0]
            headers = include_line.split()
            header_list = ["'%s'" % s[2:] for s in headers]
            return header_list
        return []

    @staticmethod
    def _get_java_include():
        include_list = []
        java_home = os.environ.get('JAVA_HOME', '')
        if java_home:
            include_list.append('%s/include' % java_home)
            include_list.append('%s/include/linux' % java_home)
            return include_list
        p = subprocess.Popen(
            'java -version',
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            version_line = stdout.splitlines(True)[0]
            version = version_line.split()[2]
            version = version.replace('"', '')
            include_list.append('/usr/java/jdk%s/include' % version)
            include_list.append('/usr/java/jdk%s/include/linux' % version)
            return include_list
        return []

    @staticmethod
    def _get_cuda_include():
        include_list = []
        cuda_path = os.environ.get('CUDA_PATH')
        if cuda_path:
            include_list.append('%s/include' % cuda_path)
            include_list.append('%s/samples/common/inc' % cuda_path)
            return include_list
        p = subprocess.Popen(
            'nvcc --version',
            env=os.environ,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            version_line = stdout.splitlines(True)[-1]
            version = version_line.split()[4]
            version = version.replace(',', '')
            if os.path.isdir('/usr/local/cuda-%s' % version):
                include_list.append('/usr/local/cuda-%s/include' % version)
                include_list.append('/usr/local/cuda-%s/samples/common/inc' % version)
                return include_list
        return []

    def get_gcc_version(self):
        """Returns gcc version. """
        return self.gcc_version

    def get_python_include(self):
        """Returns python include. """
        return self.python_inc

    def get_php_include(self):
        """Returns a list of php include. """
        return self.php_inc_list

    def get_java_include(self):
        """Returns a list of java include. """
        return self.java_inc_list

    def get_nvcc_version(self):
        """Returns nvcc version. """
        return self.nvcc_version

    def get_cuda_include(self):
        """Returns a list of cuda include. """
        return self.cuda_inc_list


class CcFlagsManager(object):
    """The CcFlagsManager class.

    This class manages the compile warning flags.

    """
    def __init__(self, options):
        self.options = options
        self.cpp_str = ''

    def _filter_out_invalid_flags(self, flag_list, language=''):
        """filter the unsupported compliation flags. """
        flag_list_var = var_to_list(flag_list)
        xlanguage = ''
        if language:
            xlanguage = '-x' + language

        ret_flag_list = []
        for flag in flag_list_var:
            cmd_str = 'echo "" | %s %s %s >/dev/null 2>&1' % (
                      self.cpp_str, xlanguage, flag)
            if subprocess.call(cmd_str, shell=True) == 0:
                ret_flag_list.append(flag)
        return ret_flag_list

    def set_cpp_str(self, cpp_str):
        """set up the cpp_str. """
        self.cpp_str = cpp_str

    def get_flags_except_warning(self):
        """Get the flags that are not warning flags. """
        flags_except_warning = ['-m%s' % self.options.m, '-mcx16', '-pipe']
        linkflags = ['-m%s' % self.options.m]
        if self.options.profile == 'debug':
            flags_except_warning += ['-ggdb3', '-fstack-protector']
        elif self.options.profile == 'release':
            flags_except_warning += ['-g', '-DNDEBUG']
        flags_except_warning += [
                '-D_FILE_OFFSET_BITS=64',
                '-D__STDC_CONSTANT_MACROS',
                '-D__STDC_FORMAT_MACROS',
                '-D__STDC_LIMIT_MACROS',
        ]

        if getattr(self.options, 'gprof', False):
            flags_except_warning.append('-pg')
            linkflags.append('-pg')

        if getattr(self.options, 'gcov', False):
            if SconsPlatform().gcc_version > '4.1':
                flags_except_warning.append('--coverage')
                linkflags.append('--coverage')
            else:
                flags_except_warning.append('-fprofile-arcs')
                flags_except_warning.append('-ftest-coverage')
                linkflags += ['-Wl,--whole-archive', '-lgcov',
                              '-Wl,--no-whole-archive']

        flags_except_warning = self._filter_out_invalid_flags(
                flags_except_warning)

        return (flags_except_warning, linkflags)

    def get_warning_flags(self):
        """Get the warning flags. """
        cc_config = configparse.blade_config.get_config('cc_config')
        cppflags = cc_config['warnings']
        cxxflags = cc_config['cxx_warnings']
        cflags = cc_config['c_warnings']

        filtered_cppflags = self._filter_out_invalid_flags(cppflags)
        filtered_cxxflags = self._filter_out_invalid_flags(cxxflags, 'c++')
        filtered_cflags = self._filter_out_invalid_flags(cflags, 'c')

        return (filtered_cppflags, filtered_cxxflags, filtered_cflags)

########NEW FILE########
__FILENAME__ = blade_util
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the util module which provides command functions.

"""

import fcntl
import os
import subprocess

import console


try:
    import hashlib as md5
except ImportError:
    import md5


def md5sum_str(user_str):
    """md5sum of basestring. """
    m = md5.md5()
    if not isinstance(user_str, basestring):
        console.error_exit('not a valid basestring type to caculate md5')
    m.update(user_str)
    return m.hexdigest()


def md5sum(obj):
    """caculate md5sum and returns it. """
    return md5sum_str(obj)


def lock_file(fd, flags):
    """lock file. """
    try:
        fcntl.flock(fd, flags)
        return (True, 0)
    except IOError, ex_value:
        return (False, ex_value[0])


def unlock_file(fd):
    """unlock file. """
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return (True, 0)
    except IOError, ex_value:
        return (False, ex_value[0])


def var_to_list(var):
    """change the var to be a list. """
    if isinstance(var, list):
        return var
    if not var:
        return []
    return [var]


def relative_path(a_path, reference_path):
    """_relative_path.

    Get the relative path of a_path by considering reference_path as the
    root directory.  For example, if
    reference_path = '/src/paralgo'
    a_path        = '/src/paralgo/mapreduce_lite/sorted_buffer'
    then
     _relative_path(a_path, reference_path) = 'mapreduce_lite/sorted_buffer'

    """
    if not a_path:
        raise ValueError('no path specified')

    # Count the number of segments shared by reference_path and a_path.
    reference_list = os.path.abspath(reference_path).split(os.path.sep)
    path_list = os.path.abspath(a_path).split(os.path.sep)
    i = 0
    for i in range(min(len(reference_list), len(path_list))):
        # TODO(yiwang): Why use lower here?
        if reference_list[i].lower() != path_list[i].lower():
            break
        else:
            # TODO(yiwnag): Why do not move i+=1 out from the loop?
            i += 1

    rel_list = [os.path.pardir] * (len(reference_list) - i) + path_list[i:]
    if not rel_list:
        return os.path.curdir
    return os.path.join(*rel_list)


def get_cwd():
    """get_cwd

    os.getcwd() doesn't work because it will follow symbol link.
    os.environ.get('PWD') doesn't work because it won't reflect os.chdir().
    So in practice we simply use system('pwd') to get current working directory.

    """
    p = subprocess.Popen(['pwd'], stdout=subprocess.PIPE, shell=True)
    return p.communicate()[0].strip()


def environ_add_path(env, key, path):
    """Add path to PATH link environments, sucn as PATH, LD_LIBRARY_PATH, etc"""
    old = env.get(key)
    if old:
        env[key] = old + ':' + path
    else:
        env[key] = path


def cpu_count():
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except ImportError:
        return int(os.sysconf('SC_NPROCESSORS_ONLN'))

########NEW FILE########
__FILENAME__ = build_environment
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   August 02, 2012


"""
 building environment checking and managing module.

"""


import glob
import math
import os
import subprocess
import time

import console


class BuildEnvironment(object):
    """Managers ccache, distcc, dccc. """
    def __init__(self, blade_root_dir, distcc_hosts_list=None):
        # ccache
        self.blade_root_dir = blade_root_dir
        self.ccache_installed = self._check_ccache_install()

        # distcc
        self.distcc_env_prepared = False
        self.distcc_installed = self._check_distcc_install()
        if distcc_hosts_list:
            self.distcc_host_list = distcc_hosts_list
        else:
            self.distcc_host_list = os.environ.get('DISTCC_HOSTS', '')
        if self.distcc_installed and self.distcc_host_list:
            self.distcc_env_prepared = True
        if self.distcc_installed and not self.distcc_host_list:
            console.warning('DISTCC_HOSTS not set but you have '
                            'distcc installed, will just build locally')
        self.distcc_log_file = os.environ.get('DISTCC_LOG', '')
        if self.distcc_log_file:
            console.info('distcc log: %s' % self.distcc_log_file)

        # dccc
        self.dccc_env_prepared = True
        self.dccc_master = os.environ.get('MASTER_HOSTS', '')
        self.dccc_hosts_list = os.environ.get('DISTLD_HOSTS', '')
        self.dccc_installed = self._check_dccc_install()
        if self.dccc_installed:
            if not self.dccc_master and not self.dccc_hosts_list:
                self.dccc_env_prepared = False
                console.warning('MASTER_HOSTS and DISTLD_HOSTS not set but '
                                'you have dccc installed, will just build '
                                'locally')
        else:
            self.dccc_env_prepared = False

        self.rules_buf = []

    @staticmethod
    def _check_ccache_install():
        """Check ccache is installed or not. """
        try:
            p = subprocess.Popen(
                ['ccache', '-V'],
                env=os.environ,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True)
            (stdout, stderr) = p.communicate()
            if p.returncode == 0:
                version_line = stdout.splitlines(True)[0]
                if version_line and version_line.find('ccache version') != -1:
                    console.info('ccache found')
                    return True
        except OSError:
            pass
        return False

    @staticmethod
    def _check_distcc_install():
        """Check distcc is installed or not. """
        p = subprocess.Popen(
            'distcc --version',
            env={},
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
        (stdout, stderr) = p.communicate()
        if p.returncode == 0:
            version_line = stdout.splitlines(True)[0]
            if version_line and version_line.find('distcc') != -1:
                console.info('distcc found')
                return True

    @staticmethod
    def _check_dccc_install():
        """Check dccc is installed or not. """
        home_dir = os.environ.get('HOME', '')
        if home_dir and os.path.exists(os.path.join(home_dir, 'bin', 'dccc')):
            console.info('dccc found')
            return True
        return False

    def setup_ccache_env(self):
        """Generates ccache rules. """
        if self.ccache_installed:
            self._add_rule('top_env.Append(CCACHE_BASEDIR="%s")' % self.blade_root_dir)

    def setup_distcc_env(self):
        """Generates distcc rules. """
        if self.distcc_installed:
            self._add_rule('top_env.Append(DISTCC_HOSTS="%s")' % self.distcc_host_list)

    def get_distcc_hosts_list(self):
        """Returns the hosts list. """
        return filter(lambda x: x, self.distcc_host_list.split(' '))

    def _add_rule(self, rule):
        """Append to buffer. """
        self.rules_buf.append(rule)

    def get_rules(self):
        """Return the scons rules. """
        return self.rules_buf


class ScacheManager(object):
    """Scons cache manager.

    Scons cache manager, which should be output to scons script.
    It will periodically check the cache folder and purge the files
    with smallest weight. The weight for each file is caculated as
    file_size * exp(-age * log(2) / half_time).

    We should pay attention that this progress will impact large builds
    and we should not reduce the progress interval(the evaluating nodes).

    """
    def __init__(self, cache_path=None, cache_limit=0,
                 cache_life=6 * 60 * 60):
        self.cache_path = cache_path
        self.cache_limit = cache_limit
        self.cache_life = cache_life
        self.exponent_scale = math.log(2) / cache_life
        self.purge_cnt = 0

    def __call__(self, node, *args, **kwargs):
        self.purge(self.get_file_list())

    def cache_remove(self, file_item):
        if not file_item:
            return
        if not os.path.exists(file_item):
            return
        os.remove(file_item)

    def purge(self, file_list):
        self.purge_cnt += 1
        if not file_list:
            return
        map(self.cache_remove, file_list)
        console.info('scons cache purged')

    def get_file_list(self):
        if not self.cache_path:
            return []

        file_stat_list = [(x, os.stat(x)[6:8])
                for x in glob.glob(os.path.join(self.cache_path, '*', '*'))]
        if not file_stat_list:
            return []

        current_time = time.time()
        file_stat_list = [(x[0], x[1][0],
            x[1][0] * math.exp(self.exponent_scale * (x[1][1] - current_time)))
            for x in file_stat_list]

        file_stat_list.sort(key=lambda x: x[2], reverse=True)

        total_sz, start_index = 0, None
        for i, x in enumerate(file_stat_list):
            total_sz += x[1]
            if total_sz >= self.cache_limit:
                start_index = i
                break

        if not start_index:
            return []
        else:
            return [x[0] for x in file_stat_list[start_index:]]

########NEW FILE########
__FILENAME__ = build_rules
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Feng Chen <phongchen@tencent.com>


"""
 Manage symbols can be used in BUILD files.
"""


__build_rules = {}


def register_variable(name, value):
    """Register a variable that accessiable in BUILD file """
    __build_rules[name] = value


def register_function(f):
    """Register a function as a build function that callable in BUILD file """
    register_variable(f.__name__, f)


def get_all():
    """Get the globals dict"""
    return __build_rules

########NEW FILE########
__FILENAME__ = cc_targets
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the cc_target module which is the super class
 of all of the scons cc targets, like cc_library, cc_binary.

"""


import os
import blade
import configparse

import console
import build_rules
from blade_util import var_to_list
from target import Target


class CcTarget(Target):
    """A scons cc target subclass.

    This class is derived from SconsTarget and it is the base class
    of cc_library, cc_binary etc.

    """
    def __init__(self,
                 name,
                 target_type,
                 srcs,
                 deps,
                 warning,
                 defs,
                 incs,
                 export_incs,
                 optimize,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)
        defs = var_to_list(defs)
        incs = var_to_list(incs)
        export_incs = var_to_list(export_incs)
        opt = var_to_list(optimize)
        extra_cppflags = var_to_list(extra_cppflags)
        extra_linkflags = var_to_list(extra_linkflags)

        Target.__init__(self,
                        name,
                        target_type,
                        srcs,
                        deps,
                        blade,
                        kwargs)

        self.data['warning'] = warning
        self.data['defs'] = defs
        self.data['incs'] = incs
        self.data['export_incs'] = export_incs
        self.data['optimize'] = opt
        self.data['extra_cppflags'] = extra_cppflags
        self.data['extra_linkflags'] = extra_linkflags

        self._check_defs()
        self._check_incorrect_no_warning()

    def _check_deprecated_deps(self):
        """check that whether it depends upon a deprecated library. """
        for dep in self.deps:
            target = self.target_database.get(dep, {})
            if target.data.get('deprecated'):
                replaced_targets = target.deps
                replaced_target = ''
                if replaced_targets:
                    replaced_target = replaced_targets[0]
                console.warning('//%s:%s : '
                                '//%s:%s has been deprecated, '
                                'please depends on //%s:%s' % (
                                    self.path, self.name,
                                    target.path, target.name,
                                    replaced_target[0], replaced_target[1]))

    def _prepare_to_generate_rule(self):
        """Should be overridden. """
        self._check_deprecated_deps()
        self._clone_env()

    def _clone_env(self):
        """Select env. """
        env_name = self._env_name()
        warning = self.data.get('warning', '')
        if warning == 'yes':
            self._write_rule('%s = env_with_error.Clone()' % env_name)
        else:
            self._write_rule('%s = env_no_warning.Clone()' % env_name)

    __cxx_keyword_list = frozenset([
        'and', 'and_eq', 'alignas', 'alignof', 'asm', 'auto',
        'bitand', 'bitor', 'bool', 'break', 'case', 'catch',
        'char', 'char16_t', 'char32_t', 'class', 'compl', 'const',
        'constexpr', 'const_cast', 'continue', 'decltype', 'default',
        'delete', 'double', 'dynamic_cast', 'else', 'enum',
        'explicit', 'export', 'extern', 'false', 'float', 'for',
        'friend', 'goto', 'if', 'inline', 'int', 'long', 'mutable',
        'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr',
        'operator', 'or', 'or_eq', 'private', 'protected', 'public',
        'register', 'reinterpret_cast', 'return', 'short', 'signed',
        'sizeof', 'static', 'static_assert', 'static_cast', 'struct',
        'switch', 'template', 'this', 'thread_local', 'throw',
        'true', 'try', 'typedef', 'typeid', 'typename', 'union',
        'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t',
        'while', 'xor', 'xor_eq'])

    def _check_defs(self):
        """_check_defs.

        It will warn if user defines cpp keyword in defs list.

        """
        defs_list = self.data.get('defs', [])
        for macro in defs_list:
            pos = macro.find('=')
            if pos != -1:
                macro = macro[0:pos]
            if macro in CcTarget.__cxx_keyword_list:
                console.warning('DO NOT define c++ keyword %s as macro' % macro)

    def _check_incorrect_no_warning(self):
        """check if warning=no is correctly used or not. """
        warning = self.data.get('warning', 'yes')
        srcs = self.srcs
        if not srcs or warning != 'no':
            return

        keywords_list = self.blade.get_sources_keyword_list()
        for keyword in keywords_list:
            if keyword in self.path:
                return

        illegal_path_list = []
        for keyword in keywords_list:
            illegal_path_list += [s for s in srcs if not keyword in s]

        if illegal_path_list:
            console.warning("//%s:%s : warning='no' is only allowed "
                            "for code in thirdparty." % (
                                self.key[0], self.key[1]))

    def _objs_name(self):
        """_objs_name.

        Concatinating target path, target name to be objs var and returns.

        """
        return 'objs_%s' % self._generate_variable_name(self.path,
                                                        self.name)

    def _prebuilt_cc_library_build_path(self, dynamic=False):
        """Returns the build path of the prebuilt cc library. """
        path = self.path
        name = self.name
        suffix = 'a'
        if dynamic:
            suffix = 'so'
        return os.path.join(self.build_path, path, 'lib%s.%s' % (name, suffix))

    def _prebuilt_cc_library_src_path(self, dynamic=False):
        """Returns the source path of the prebuilt cc library. """
        path = self.path
        name = self.name
        options = self.blade.get_options()
        suffix = 'a'
        if dynamic:
            suffix = 'so'
        return os.path.join(path, 'lib%s_%s' % (options.m, options.profile),
                            'lib%s.%s' % (name, suffix))

    def _setup_cc_flags(self):
        """_setup_cc_flags. """
        env_name = self._env_name()
        flags_from_option, incs_list = self._get_cc_flags()
        if flags_from_option:
            self._write_rule('%s.Append(CPPFLAGS=%s)' % (env_name, flags_from_option))
        if incs_list:
            self._write_rule('%s.Append(CPPPATH=%s)' % (env_name, incs_list))

    def _setup_as_flags(self):
        """_setup_as_flags. """
        env_name = self._env_name()
        as_flags = self._get_as_flags()
        if as_flags:
            self._write_rule('%s.Append(ASFLAGS=%s)' % (env_name, as_flags))

    def _setup_extra_link_flags(self):
        """extra_linkflags. """
        extra_linkflags = self.data.get('extra_linkflags')
        if extra_linkflags:
            self._write_rule('%s.Append(LINKFLAGS=%s)' % (self._env_name(), extra_linkflags))

    def _check_gcc_flag(self, gcc_flag_list):
        options = self.blade.get_options()
        gcc_flags_list_checked = []
        for flag in gcc_flag_list:
            if flag == '-fno-omit-frame-pointer':
                if options.profile != 'release':
                    continue
            gcc_flags_list_checked.append(flag)
        return gcc_flags_list_checked

    def _get_optimize_flags(self):
        """get optimize flags such as -O2"""
        oflags = []
        opt_list = self.data.get('optimize')
        if not opt_list:
            cc_config = configparse.blade_config.get_config('cc_config')
            opt_list = cc_config['optimize']
        if opt_list:
            for flag in opt_list:
                if flag.startswith('-'):
                    oflags.append(flag)
                else:
                    oflags.append('-' + flag)
        else:
            oflags = ['-O2']
        return oflags

    def _get_cc_flags(self):
        """_get_cc_flags.

        Return the cpp flags according to the BUILD file and other configs.

        """
        cpp_flags = []

        # Warnings
        if self.data.get('warning', '') == 'no':
            cpp_flags.append('-w')

        # Defs
        defs = self.data.get('defs', [])
        cpp_flags += [('-D' + macro) for macro in defs]

        # Optimize flags

        if (self.blade.get_options().profile == 'release' or
            self.data.get('always_optimize')):
            cpp_flags += self._get_optimize_flags()

        # Add the compliation flags here
        # 1. -fno-omit-frame-pointer to release
        blade_gcc_flags = ['-fno-omit-frame-pointer']
        blade_gcc_flags_checked = self._check_gcc_flag(blade_gcc_flags)
        cpp_flags += list(set(blade_gcc_flags_checked).difference(set(cpp_flags)))

        cpp_flags += self.data.get('extra_cppflags', [])

        # Incs
        incs = self.data.get('incs', [])
        if not incs:
            incs = self.data.get('export_incs', [])
        new_incs_list = [os.path.join(self.path, inc) for inc in incs]
        new_incs_list += self._export_incs_list()
        # Remove duplicate items in incs list and keep the order
        incs_list = []
        for inc in new_incs_list:
            new_inc = os.path.normpath(inc)
            if new_inc not in incs_list:
                incs_list.append(new_inc)

        return (cpp_flags, incs_list)

    def _get_as_flags(self):
        """_get_as_flags.

        Return the as flags according to the build architecture.

        """
        options = self.blade.get_options()
        as_flags = ["--" + options.m]
        return as_flags


    def _dep_is_library(self, dep):
        """_dep_is_library.

        Returns
        -----------
        True or False: Whether this dep target is library or not.

        Description
        -----------
        Whether this dep target is library or not.

        """
        build_targets = self.blade.get_build_targets()
        target_type = build_targets[dep].type
        return ('library' in target_type or 'plugin' in target_type)

    def _export_incs_list(self):
        """_export_incs_list.
        TODO
        """
        deps = self.expanded_deps
        inc_list = []
        for lib in deps:
            # lib is (path, libname) pair.
            if not lib:
                continue

            if not self._dep_is_library(lib):
                continue

            # system lib
            if lib[0] == '#':
                continue

            target = self.target_database[lib]
            for inc in target.data.get('export_incs', []):
                path = os.path.normpath('%s/%s' % (lib[0], inc))
                inc_list.append(path)

        return inc_list

    def _static_deps_list(self):
        """_static_deps_list.

        Returns
        -----------
        link_all_symbols_lib_list: the libs to link all its symbols into target
        lib_list: the libs list to be statically linked into static library

        Description
        -----------
        It will find the libs needed to be linked into the target statically.

        """
        build_targets = self.blade.get_build_targets()
        deps = self.expanded_deps
        lib_list = []
        link_all_symbols_lib_list = []
        for dep in deps:
            if not self._dep_is_library(dep):
                continue

            # system lib
            if dep[0] == '#':
                lib_name = "'%s'" % dep[1]
            else:
                lib_name = self._generate_variable_name(dep[0], dep[1])

            if build_targets[dep].data.get('link_all_symbols'):
                link_all_symbols_lib_list.append(lib_name)
            else:
                lib_list.append(lib_name)

        return (link_all_symbols_lib_list, lib_list)

    def _dynamic_deps_list(self):
        """_dynamic_deps_list.

        Returns
        -----------
        lib_list: the libs list to be dynamically linked into dynamic library

        Description
        -----------
        It will find the libs needed to be linked into the target dynamically.

        """
        build_targets = self.blade.get_build_targets()
        deps = self.expanded_deps
        lib_list = []
        for lib in deps:
            if not self._dep_is_library(lib):
                continue

            if (build_targets[lib].type == 'cc_library' and
                not build_targets[lib].srcs):
                continue
            # system lib
            if lib[0] == '#':
                lib_name = "'%s'" % lib[1]
            else:
                lib_name = self._generate_variable_name(lib[0],
                                                        lib[1],
                                                        'dynamic')

            lib_list.append(lib_name)

        return lib_list

    def _get_static_deps_lib_list(self):
        """Returns a tuple that needed to write static deps rules. """
        (link_all_symbols_lib_list, lib_list) = self._static_deps_list()
        lib_str = 'LIBS=[%s]' % ','.join(lib_list)
        whole_link_flags = []
        if link_all_symbols_lib_list:
            whole_link_flags = ['"-Wl,--whole-archive"']
            for i in link_all_symbols_lib_list:
                whole_link_flags.append(i)
            whole_link_flags.append('"-Wl,--no-whole-archive"')
        return (link_all_symbols_lib_list, lib_str, ', '.join(whole_link_flags))

    def _get_dynamic_deps_lib_list(self):
        """Returns the libs string. """
        lib_list = self._dynamic_deps_list()
        lib_str = 'LIBS=[]'
        if lib_list:
            lib_str = 'LIBS=[%s]' % ','.join(lib_list)
        return lib_str

    def _prebuilt_cc_library(self, dynamic):
        """prebuilt cc library rules. """
        build_targets = self.blade.get_build_targets()
        prebuilt_target_file = ''
        prebuilt_src_file = ''
        prebuilt_symlink = ''
        allow_only_dynamic = True
        need_static_lib_targets = ['cc_test',
                                   'cc_binary',
                                   'cc_benchmark',
                                   'cc_plugin',
                                   'swig_library']
        for key in build_targets:
            if (self.key in build_targets[key].expanded_deps and
                build_targets[key].type in need_static_lib_targets):
                allow_only_dynamic = False

        var_name = self._generate_variable_name(self.path,
                                                self.name)
        if not allow_only_dynamic:
            self._write_rule(
                    'Command("%s", "%s", Copy("$TARGET", "$SOURCE"))' % (
                             self._prebuilt_cc_library_build_path(),
                             self._prebuilt_cc_library_src_path()))
            self._write_rule('%s = top_env.File("%s")' % (
                             var_name,
                             self._prebuilt_cc_library_build_path()))
        if dynamic:
            prebuilt_target_file = self._prebuilt_cc_library_build_path(dynamic=True)
            prebuilt_src_file = self._prebuilt_cc_library_src_path(dynamic=True)
            self._write_rule(
                    'Command("%s", "%s", Copy("$TARGET", "$SOURCE"))' % (
                     prebuilt_target_file,
                     prebuilt_src_file))
            var_name = self._generate_variable_name(self.path,
                                                    self.name,
                                                    'dynamic')
            self._write_rule('%s = top_env.File("%s")' % (
                        var_name,
                        prebuilt_target_file))
            prebuilt_symlink = os.path.realpath(prebuilt_src_file)
            prebuilt_symlink = os.path.basename(prebuilt_symlink)
            self.file_and_link = (prebuilt_target_file, prebuilt_symlink)
        else:
            self.file_and_link = None

    def _cc_library(self):
        """_cc_library.

        It will output the cc_library rule into the buffer.

        """
        var_name = self._generate_variable_name(self.path, self.name)
        self._write_rule('%s = %s.Library("%s", %s)' % (
                var_name,
                self._env_name(),
                self._target_file_path(),
                self._objs_name()))
        self._write_rule('%s.Depends(%s, %s)' % (
                self._env_name(),
                var_name,
                self._objs_name()))

    def _dynamic_cc_library(self):
        """_dynamic_cc_library.

        It will output the dynamic_cc_library rule into the buffer.

        """
        self._setup_extra_link_flags()

        var_name = self._generate_variable_name(self.path,
                                                self.name,
                                                'dynamic')

        lib_str = self._get_dynamic_deps_lib_list()
        if self.srcs or self.expanded_deps:
            self._write_rule('%s.Append(LINKFLAGS=["-Xlinker", "--no-undefined"])'
                             % self._env_name())
            self._write_rule('%s = %s.SharedLibrary("%s", %s, %s)' % (
                    var_name,
                    self._env_name(),
                    self._target_file_path(),
                    self._objs_name(),
                    lib_str))
            self._write_rule('%s.Depends(%s, %s)' % (
                    self._env_name(),
                    var_name,
                    self._objs_name()))

    def _cc_objects_rules(self):
        """_cc_objects_rules.

        Generate the cc objects rules for the srcs in srcs list.

        """
        target_types = ['cc_library',
                        'cc_binary',
                        'cc_test',
                        'cc_plugin']

        if not self.type in target_types:
            console.error_exit('logic error, type %s err in object rule' % self.type)

        path = self.path
        objs_name = self._objs_name()
        env_name = self._env_name()

        self._setup_cc_flags()
        self._setup_as_flags()

        objs = []
        sources = []
        for src in self.srcs:
            obj = '%s_%s_object' % (self._generate_variable_name(path, src),
                                    self._regular_variable_name(self.name))
            target_path = os.path.join(
                    self.build_path, path, '%s.objs' % self.name, src)
            self._write_rule(
                    '%s = %s.SharedObject(target = "%s" + top_env["OBJSUFFIX"]'
                    ', source = "%s")' % (obj,
                                          env_name,
                                          target_path,
                                          self._target_file_path(path, src)))
            self._write_rule('%s.Depends(%s, "%s")' % (
                             env_name,
                             obj,
                             self._target_file_path(path, src)))
            sources.append(self._target_file_path(path, src))
            objs.append(obj)
        self._write_rule('%s = [%s]' % (objs_name, ','.join(objs)))

        # Generate dependancy to all targets that generate header files
        for dep_name in self.deps:
            dep = self.target_database[dep_name]
            if not dep._generate_header_files():
                continue
            dep_var_name = self._generate_variable_name(dep.path, dep.name)
            self._write_rule('%s.Depends(%s, %s)' % (
                    env_name,
                    objs_name,
                    dep_var_name))
        return sources


class CcLibrary(CcTarget):
    """A cc target subclass.

    This class is derived from SconsTarget and it generates the library
    rules including dynamic library rules accoring to user option.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 warning,
                 defs,
                 incs,
                 export_incs,
                 optimize,
                 always_optimize,
                 prebuilt,
                 link_all_symbols,
                 deprecated,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        CcTarget.__init__(self,
                          name,
                          'cc_library',
                          srcs,
                          deps,
                          warning,
                          defs,
                          incs,
                          export_incs,
                          optimize,
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)
        if prebuilt:
            self.type = 'prebuilt_cc_library'
            self.srcs = []
        self.data['link_all_symbols'] = link_all_symbols
        self.data['always_optimize'] = always_optimize
        self.data['deprecated'] = deprecated

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        options = self.blade.get_options()
        build_dynamic = (getattr(options, 'generate_dynamic', False) or
                         self.data.get('build_dynamic'))

        if self.type == 'prebuilt_cc_library':
            self._prebuilt_cc_library(build_dynamic)
        else:
            self._cc_objects_rules()
            self._cc_library()
            if build_dynamic:
                self._dynamic_cc_library()


def cc_library(name,
               srcs=[],
               deps=[],
               warning='yes',
               defs=[],
               incs=[],
               export_incs=[],
               optimize=[],
               always_optimize=False,
               pre_build=False,
               prebuilt=False,
               link_all_symbols=False,
               deprecated=False,
               extra_cppflags=[],
               extra_linkflags=[],
               **kwargs):
    """cc_library target. """
    target = CcLibrary(name,
                       srcs,
                       deps,
                       warning,
                       defs,
                       incs,
                       export_incs,
                       optimize,
                       always_optimize,
                       prebuilt or pre_build,
                       link_all_symbols,
                       deprecated,
                       extra_cppflags,
                       extra_linkflags,
                       blade.blade,
                       kwargs)
    if pre_build:
        console.warning("//%s:%s: 'pre_build' has been deprecated, "
                        "please use 'prebuilt'" % (target.path,
                                                   target.name))
    blade.blade.register_target(target)


build_rules.register_function(cc_library)


class CcBinary(CcTarget):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget and it generates the cc_binary
    rules according to user options.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 warning,
                 defs,
                 incs,
                 export_incs,
                 optimize,
                 dynamic_link,
                 extra_cppflags,
                 extra_linkflags,
                 export_dynamic,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        CcTarget.__init__(self,
                          name,
                          'cc_binary',
                          srcs,
                          deps,
                          warning,
                          defs,
                          incs,
                          export_incs,
                          optimize,
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)
        self.data['dynamic_link'] = dynamic_link
        self.data['export_dynamic'] = export_dynamic

        cc_binary_config = configparse.blade_config.get_config('cc_binary_config')
        # add extra link library
        link_libs = var_to_list(cc_binary_config['extra_libs'])
        self._add_hardcode_library(link_libs)

    def _cc_binary(self):
        """_cc_binary rules. """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)

        platform = self.blade.get_scons_platform()
        if platform.get_gcc_version() > '4.5':
            link_flag_list = ['-static-libgcc', '-static-libstdc++']
            self._write_rule('%s.Append(LINKFLAGS=%s)' % (env_name, link_flag_list))

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()
        if whole_link_flags:
            self._write_rule(
                    '%s.Append(LINKFLAGS=[%s])' % (env_name, whole_link_flags))

        if self.data.get('export_dynamic'):
            self._write_rule(
                '%s.Append(LINKFLAGS="-rdynamic")' % env_name)

        cc_config = configparse.blade_config.get_config('cc_config')
        linkflags = cc_config['linkflags']
        if linkflags:
            self._write_rule('%s.Append(LINKFLAGS=%s)' % (self._env_name(), linkflags))

        self._setup_extra_link_flags()

        self._write_rule('%s = %s.Program("%s", %s, %s)' % (
            var_name,
            env_name,
            self._target_file_path(),
            self._objs_name(),
            lib_str))
        self._write_rule('%s.Depends(%s, %s)' % (
            env_name,
            var_name,
            self._objs_name()))

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                    env_name, var_name, ', '.join(link_all_symbols_lib_list)))

        self._write_rule('%s.Append(LINKFLAGS=str(version_obj[0]))' % env_name)
        self._write_rule('%s.Requires(%s, version_obj)' % (
                         env_name, var_name))

    def _dynamic_cc_binary(self):
        """_dynamic_cc_binary. """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)
        if self.data.get('export_dynamic'):
            self._write_rule('%s.Append(LINKFLAGS="-rdynamic")' % env_name)

        self._setup_extra_link_flags()

        lib_str = self._get_dynamic_deps_lib_list()
        self._write_rule('%s = %s.Program("%s", %s, %s)' % (
            var_name,
            env_name,
            self._target_file_path(),
            self._objs_name(),
            lib_str))
        self._write_rule('%s.Depends(%s, %s)' % (
            env_name,
            var_name,
            self._objs_name()))
        self._write_rule('%s.Append(LINKFLAGS=str(version_obj[0]))' % env_name)
        self._write_rule('%s.Requires(%s, version_obj)' % (
                         env_name, var_name))

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        self._cc_objects_rules()

        if self.data['dynamic_link']:
            self._dynamic_cc_binary()
        else:
            self._cc_binary()


def cc_binary(name,
              srcs=[],
              deps=[],
              warning='yes',
              defs=[],
              incs=[],
              export_incs=[],
              optimize=[],
              dynamic_link=False,
              extra_cppflags=[],
              extra_linkflags=[],
              export_dynamic=False,
              **kwargs):
    """cc_binary target. """
    cc_binary_target = CcBinary(name,
                                srcs,
                                deps,
                                warning,
                                defs,
                                incs,
                                export_incs,
                                optimize,
                                dynamic_link,
                                extra_cppflags,
                                extra_linkflags,
                                export_dynamic,
                                blade.blade,
                                kwargs)
    blade.blade.register_target(cc_binary_target)


build_rules.register_function(cc_binary)


def cc_benchmark(name, deps=[], **kwargs):
    """cc_benchmark target. """
    cc_config = configparse.blade_config.get_config('cc_config')
    benchmark_libs = cc_config['benchmark_libs']
    benchmark_main_libs = cc_config['benchmark_main_libs']
    deps = var_to_list(deps) + benchmark_libs + benchmark_main_libs
    cc_binary(name=name, deps=deps, **kwargs)


build_rules.register_function(cc_benchmark)


class CcPlugin(CcTarget):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget and it generates the cc_plugin
    rules according to user options.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 warning,
                 defs,
                 incs,
                 export_incs,
                 optimize,
                 prebuilt,
                 prefix,
                 suffix,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cc plugin target.

        """
        CcTarget.__init__(self,
                          name,
                          'cc_plugin',
                          srcs,
                          deps,
                          warning,
                          defs,
                          incs,
                          export_incs,
                          optimize,
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)
        if prebuilt:
            self.type = 'prebuilt_cc_library'
            self.srcs = []
        self.prefix = prefix
        self.suffix = suffix

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path,
                                                self.name,
                                                'dynamic')

        self._cc_objects_rules()
        self._setup_extra_link_flags()

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()
        if whole_link_flags:
            self._write_rule(
                    '%s.Append(LINKFLAGS=[%s])' % (env_name, whole_link_flags))

        if self.prefix is not None:
            self._write_rule(
                    '%s.Replace(SHLIBPREFIX="%s")' % (env_name, self.prefix))

        if self.suffix is not None:
            self._write_rule(
                    '%s.Replace(SHLIBSUFFIX="%s")' % (env_name, self.suffix))

        if self.srcs or self.expanded_deps:
            self._write_rule('%s = %s.SharedLibrary("%s", %s, %s)' % (
                    var_name,
                    env_name,
                    self._target_file_path(),
                    self._objs_name(),
                    lib_str))

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                env_name, var_name, ', '.join(link_all_symbols_lib_list)))


def cc_plugin(name,
              srcs=[],
              deps=[],
              warning='yes',
              defs=[],
              incs=[],
              export_incs=[],
              optimize=[],
              prebuilt=False,
              pre_build=False,
              prefix=None,
              suffix=None,
              extra_cppflags=[],
              extra_linkflags=[],
              **kwargs):
    """cc_plugin target. """
    target = CcPlugin(name,
                      srcs,
                      deps,
                      warning,
                      defs,
                      incs,
                      export_incs,
                      optimize,
                      prebuilt or pre_build,
                      prefix,
                      suffix,
                      extra_cppflags,
                      extra_linkflags,
                      blade.blade,
                      kwargs)
    if pre_build:
        console.warning("//%s:%s: 'pre_build' has been deprecated, "
                        "please use 'prebuilt'" % (target.path,
                                                   target.name))
    blade.blade.register_target(target)


build_rules.register_function(cc_plugin)


# See http://google-perftools.googlecode.com/svn/trunk/doc/heap_checker.html
HEAP_CHECK_VALUES = set([
    '',
    'minimal',
    'normal',
    'strict',
    'draconian',
    'as-is',
    'local',
])


class CcTest(CcBinary):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget and it generates the cc_test
    rules according to user options.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 warning,
                 defs,
                 incs,
                 export_incs,
                 optimize,
                 dynamic_link,
                 testdata,
                 extra_cppflags,
                 extra_linkflags,
                 export_dynamic,
                 always_run,
                 exclusive,
                 heap_check,
                 heap_check_debug,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        cc_test_config = configparse.blade_config.get_config('cc_test_config')
        if dynamic_link is None:
            dynamic_link = cc_test_config['dynamic_link']

        CcBinary.__init__(self,
                          name,
                          srcs,
                          deps,
                          warning,
                          defs,
                          incs,
                          export_incs,
                          optimize,
                          dynamic_link,
                          extra_cppflags,
                          extra_linkflags,
                          export_dynamic,
                          blade,
                          kwargs)
        self.type = 'cc_test'
        self.data['testdata'] = var_to_list(testdata)
        self.data['always_run'] = always_run
        self.data['exclusive'] = exclusive

        gtest_lib = var_to_list(cc_test_config['gtest_libs'])
        gtest_main_lib = var_to_list(cc_test_config['gtest_main_libs'])

        # Hardcode deps rule to thirdparty gtest main lib.
        self._add_hardcode_library(gtest_lib)
        self._add_hardcode_library(gtest_main_lib)

        if heap_check is None:
            heap_check = cc_test_config.get('heap_check', '')
        else:
            if heap_check not in HEAP_CHECK_VALUES:
                console.error_exit('//%s:%s: heap_check can only be in %s' % (
                    self.path, self.name, HEAP_CHECK_VALUES))

        perftools_lib = var_to_list(cc_test_config['gperftools_libs'])
        perftools_debug_lib = var_to_list(cc_test_config['gperftools_debug_libs'])
        if heap_check:
            self.data['heap_check'] = heap_check

            if heap_check_debug:
                perftools_lib_list = perftools_debug_lib
            else:
                perftools_lib_list = perftools_lib

            self._add_hardcode_library(perftools_lib_list)


def cc_test(name,
            srcs=[],
            deps=[],
            warning='yes',
            defs=[],
            incs=[],
            export_incs=[],
            optimize=[],
            dynamic_link=None,
            testdata=[],
            extra_cppflags=[],
            extra_linkflags=[],
            export_dynamic=False,
            always_run=False,
            exclusive=False,
            heap_check=None,
            heap_check_debug=False,
            **kwargs):
    """cc_test target. """
    cc_test_target = CcTest(name,
                            srcs,
                            deps,
                            warning,
                            defs,
                            incs,
                            export_incs,
                            optimize,
                            dynamic_link,
                            testdata,
                            extra_cppflags,
                            extra_linkflags,
                            export_dynamic,
                            always_run,
                            exclusive,
                            heap_check,
                            heap_check_debug,
                            blade.blade,
                            kwargs)
    blade.blade.register_target(cc_test_target)


build_rules.register_function(cc_test)

########NEW FILE########
__FILENAME__ = command_args
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Chong peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the CmdOptions module which parses the users'
 input and provides hint for users.

"""


import os
import platform
import shlex

import console
from argparse import ArgumentParser


class CmdArguments(object):
    """CmdArguments

    Parses user's input and provides hint.
    blade {command} [options] targets

    """
    def __init__(self):
        """Init the class. """
        (self.options, others) = self._cmd_parse()

        # If '--' in arguments, use all other arguments after it as run
        # arguments
        if '--' in others:
            pos = others.index('--')
            self.targets = others[:pos]
            self.options.args = others[pos + 1:]
        else:
            self.targets = others
            self.options.args = []

        for t in self.targets:
            if t.startswith('-'):
                console.error_exit('unregconized option %s, use blade [action] '
                                   '--help to get all the options' % t)

        command = self.options.command

        # Check the options with different sub command
        actions = {
                  'build': self._check_build_command,
                  'run':   self._check_run_command,
                  'test':  self._check_test_command,
                  'clean': self._check_clean_command,
                  'query': self._check_query_command
                  }
        actions[command]()

    def _check_run_targets(self):
        """check that run command should have only one target. """
        err = False
        targets = []
        if len(self.targets) == 0:
            err = True
        elif self.targets[0].find(':') == -1:
            err = True
        if err:
            console.error_exit('Please specify a single target to run: '
                               'blade run //target_path:target_name (or '
                               'a_path:target_name)')
        if self.options.command == 'run' and len(self.targets) > 1:
            console.warning('run command will only take one target to build and run')
        if self.targets[0].startswith('//'):
            targets.append(self.targets[0][2:])
        else:
            targets.append(self.targets[0])
        self.targets = targets
        if self.options.runargs:
            console.warning('--runargs has been deprecated, please put all run'
                            ' arguments after a "--"')
            self.options.args = shlex.split(self.options.runargs) + self.options.args

    def _check_test_options(self):
        """check that test command options. """
        if self.options.testargs:
            console.warning('--testargs has been deprecated, please put all test'
                            ' arguments after a "--" ')
            self.options.args = shlex.split(self.options.testargs) + self.options.args

    def _check_query_targets(self):
        """check query targets, should have a leaset one target. """
        err = False
        targets = []
        if len(self.targets) == 0:
            err = True
        for target in self.targets:
            if target.find(':') == -1:
                err = True
                break
            if target.startswith('//'):
                targets.append(target[2:])
            else:
                targets.append(target)
        if err:
            console.error_exit('Please specify targets in this way: blade query'
                               ' //target_path:target_name (or path:target_name)')
        self.targets = targets

    def _check_plat_and_profile_options(self):
        """check platform and profile options. """
        if (self.options.profile != 'debug' and
            self.options.profile != 'release'):
            console.error_exit('--profile must be "debug" or "release".')

        if self.options.m is None:
            self.options.m = self._arch_bits()
        else:
            if not (self.options.m == '32' or self.options.m == '64'):
                console.error_exit("--m must be '32' or '64'")

            # TODO(phongchen): cross compile checking
            if self.options.m == '64' and platform.machine() != 'x86_64':
                console.error_exit('Sorry, 64-bit environment is required for '
                                   'building 64-bit targets.')

    def _check_color_options(self):
        """check color options. """
        if self.options.color == 'yes':
            console.color_enabled = True
        elif self.options.color == 'no':
            console.color_enabled = False
        elif self.options.color == 'auto' or self.options.color is None:
            pass
        else:
            console.error_exit('--color can only be yes, no or auto.')

    def _check_clean_options(self):
        """check the clean options. """
        self._check_plat_and_profile_options()
        self._check_color_options()

    def _check_query_options(self):
        """check query action options. """
        if not self.options.deps and not self.options.depended:
            console.error_exit('please specify --deps, --depended or both to '
                               'query target')

    def _check_build_options(self):
        """check the building options. """
        self._check_plat_and_profile_options()
        self._check_color_options()

        if self.options.cache_dir is None:
            self.options.cache_dir = os.environ.get('BLADE_CACHE_DIR')
        if self.options.cache_dir:
            self.options.cache_dir = os.path.expanduser(self.options.cache_dir)

        if self.options.cache_size is None:
            self.options.cache_size = os.environ.get('BLADE_CACHE_SIZE')
        if self.options.cache_size == 'unlimited':
            self.options.cache_size = -1
        if self.options.cache_size is None:
            self.options.cache_size = 2 * 1024 * 1024 * 1024
        else:
            self.options.cache_size = int(self.options.cache_size) * 1024 * 1024 * 1024

    def _check_build_command(self):
        """check build options. """
        self._check_build_options()

    def _check_run_command(self):
        """check run options and the run targets. """
        self._check_build_options()
        self._check_run_targets()

    def _check_test_command(self):
        """check test optios. """
        self._check_build_options()
        self._check_test_options()

    def _check_clean_command(self):
        """check clean options. """
        self._check_clean_options()

    def _check_query_command(self):
        """check query options. """
        self._check_plat_and_profile_options()
        self._check_color_options()
        self._check_query_options()
        self._check_query_targets()

    def __add_plat_profile_arguments(self, parser):
        """Add plat and profile arguments. """
        parser.add_argument('-m',
                            dest='m',
                            help=('Generate code for a 32-bit(-m32) or '
                                  '64-bit(-m64) environment, '
                                  'default is autodetect.'))

        parser.add_argument('-p',
                            '--profile',
                            dest='profile',
                            default='release',
                            help=('Build profile: debug or release, '
                                  'default is release.'))

    def __add_generate_arguments(self, parser):
        """Add generate related arguments. """
        parser.add_argument(
            '--generate-dynamic', dest='generate_dynamic',
            action='store_true', default=False,
            help='Generate dynamic libraries.')

        parser.add_argument(
            '--generate-java', dest='generate_java',
            action='store_true', default=False,
            help='Generate java files for proto_library, thrift_library and '
                 'swig_library.')

        parser.add_argument(
            '--generate-php', dest='generate_php',
            action='store_true', default=False,
            help='Generate php files for proto_library and swig_library.')

    def __add_build_actions_arguments(self, parser):
        """Add build related action arguments. """
        parser.add_argument(
            '--generate-scons-only', dest='scons_only',
            action='store_true', default=False,
            help='Generate scons script for debug purpose.')

        parser.add_argument(
            '-j', '--jobs', dest='jobs', type=int, default=0,
            help=('Specifies the number of jobs (commands) to '
                  'run simultaneously.'))

        parser.add_argument(
            '-k', '--keep-going', dest='keep_going',
            action='store_true', default=False,
            help='Continue as much as possible after an error.')

        parser.add_argument(
            '--verbose', dest='verbose', action='store_true',
            default=False, help='Show all details.')

        parser.add_argument(
            '--no-test', dest='no_test', action='store_true',
            default=False, help='Do not build the test targets.')

    def __add_color_arguments(self, parser):
        """Add color argument. """
        parser.add_argument(
            '--color', dest='color', default='auto',
            help='Enable color: yes, no or auto, default is auto.')

    def __add_cache_arguments(self, parser):
        """Add cache related arguments. """
        parser.add_argument(
            '--cache-dir', dest='cache_dir', type=str,
            help='Specifies location of shared cache directory.')

        parser.add_argument(
            '--cache-size', dest='cache_size', type=str,
            help='Specifies cache size of shared cache directory in Gigabytes.'
                 '"unlimited" for unlimited. ')

    def __add_coverage_arguments(self, parser):
        """Add coverage arguments. """
        parser.add_argument(
            '--gprof', dest='gprof',
            action='store_true', default=False,
            help='Add build options to support GNU gprof.')

        parser.add_argument(
            '--gcov', dest='gcov',
            action='store_true', default=False,
            help='Add build options to support GNU gcov to do coverage test.')

    def _add_query_arguments(self, parser):
        """Add query arguments for parser. """
        self.__add_plat_profile_arguments(parser)
        self.__add_color_arguments(parser)
        parser.add_argument(
            '--deps', dest='deps',
            action='store_true', default=False,
            help='Show all targets that depended by the target being queried.')
        parser.add_argument(
            '--depended', dest='depended',
            action='store_true', default=False,
            help='Show all targets that depened on the target being queried.')
        parser.add_argument(
            '--output-to-dot', dest='output_to_dot', type=str,
            help='The name of file to output query results as dot(graphviz) '
                 'format.')

    def _add_clean_arguments(self, parser):
        """Add clean arguments for parser. """
        self.__add_plat_profile_arguments(parser)
        self.__add_generate_arguments(parser)
        self.__add_color_arguments(parser)

    def _add_test_arguments(self, parser):
        """Add test command arguments. """
        parser.add_argument(
            '--testargs', dest='testargs', type=str,
            help='Command line arguments to be passed to tests.')

        parser.add_argument(
            '--full-test', action='store_true',
            dest='fulltest', default=False,
            help='Enable full test, default is incremental test.')

        parser.add_argument(
            '-t', '--test-jobs', dest='test_jobs', type=int, default=1,
            help=('Specifies the number of tests to run simultaneously.'))

        parser.add_argument(
            '--show-details', action='store_true',
            dest='show_details', default=False,
            help='Shows the test result in detail and provides a file.')

    def _add_run_arguments(self, parser):
        """Add run command arguments. """
        parser.add_argument(
            '--runargs', dest='runargs', type=str,
            help='Command line arguments to be passed to the single run target.')

    def _add_build_arguments(self, parser):
        """Add building arguments for parser. """
        self.__add_plat_profile_arguments(parser)
        self.__add_build_actions_arguments(parser)
        self.__add_color_arguments(parser)
        self.__add_cache_arguments(parser)
        self.__add_generate_arguments(parser)
        self.__add_coverage_arguments(parser)

    def _cmd_parse(self):
        """Add command options, add options whthin this method."""
        blade_cmd_help = 'blade <subcommand> [options...] [targets...]'
        arg_parser = ArgumentParser(prog='blade', description=blade_cmd_help)

        sub_parser = arg_parser.add_subparsers(
            dest='command',
            help='Available subcommands')

        build_parser = sub_parser.add_parser(
            'build',
            help='Build specified targets')

        run_parser = sub_parser.add_parser(
            'run',
            help='Build and runs a single target')

        test_parser = sub_parser.add_parser(
            'test',
            help='Build the specified targets and runs tests')

        clean_parser = sub_parser.add_parser(
            'clean',
            help='Remove all Blade-created output')

        query_parser = sub_parser.add_parser(
            'query',
            help='Execute a dependency graph query')

        self._add_build_arguments(build_parser)
        self._add_build_arguments(run_parser)
        self._add_build_arguments(test_parser)

        self._add_run_arguments(run_parser)
        self._add_test_arguments(test_parser)
        self._add_clean_arguments(clean_parser)
        self._add_query_arguments(query_parser)

        return arg_parser.parse_known_args()

    def _arch_bits(self):
        """Platform arch."""
        if 'x86_64' == platform.machine():
            return '64'
        else:
            return '32'

    def get_command(self):
        """Return blade command. """
        return self.options.command

    def get_options(self):
        """Returns the command options, which should be used by blade manager."""
        return self.options

    def get_targets(self):
        """Returns the targets from command line."""
        return self.targets

########NEW FILE########
__FILENAME__ = configparse
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   January 09, 2012


"""
 This is the configuration parse module which parses
 the BLADE_ROOT as a configuration file.

"""
import os
import sys
import traceback

import console
from blade_util import var_to_list
from cc_targets import HEAP_CHECK_VALUES


# Global config object
blade_config = None


def config_items(**kwargs):
    """Used in config functions for config file, to construct a appended
    items dict, and then make syntax more pretty
    """
    return kwargs


class BladeConfig(object):
    """BladeConfig. A configuration parser class. """
    def __init__(self, current_source_dir):
        self.current_source_dir = current_source_dir
        self.current_file_name = ''
        self.configs = {
            'global_config' : {
                'build_path_template': 'build${m}_${profile}',
            },

            'cc_test_config': {
                'dynamic_link': False,
                'heap_check': '',
                'gperftools_libs': [],
                'gperftools_debug_libs': [],
                'gtest_libs': [],
                'gtest_main_libs': []
            },

            'cc_binary_config': {
                'extra_libs': []
            },

            'distcc_config': {
                'enabled': False
            },

            'link_config': {
                'link_on_tmp': False,
                'enable_dccc': False
            },

            'java_config': {
                'source_version': '',
                'target_version': ''
            },

            'thrift_config': {
                'thrift': 'thrift',
                'thrift_libs': [],
                'thrift_incs': [],
            },

            'proto_library_config': {
                'protoc': 'thirdparty/protobuf/bin/protoc',
                'protobuf_libs': [],
                'protobuf_path': '',
                'protobuf_incs': [],
                'protobuf_php_path': '',
                'protoc_php_plugin': '',
            },

            'cc_config': {
                'extra_incs': [],
                'cppflags': [],
                'cflags': [],
                'cxxflags': [],
                'linkflags': [],
                'c_warnings': [],
                'cxx_warnings': [],
                'warnings': [],
                'cpplint': 'cpplint.py',
                'optimize': [],
                'benchmark_libs': [],
                'benchmark_main_libs': [],
            }
        }

    def _try_parse_file(self, filename):
        """load the configuration file and parse. """
        try:
            self.current_file_name = filename
            if os.path.exists(filename):
                execfile(filename)
        except:
            console.error_exit('Parse error in config file %s, exit...\n%s' %
                       (filename, traceback.format_exc()))

    def parse(self):
        """load the configuration file and parse. """
        self._try_parse_file(os.path.join(os.path.dirname(sys.argv[0]), 'blade.conf'))
        self._try_parse_file(os.path.expanduser('~/.bladerc'))
        self._try_parse_file(os.path.join(self.current_source_dir, 'BLADE_ROOT'))

    def update_config(self, section_name, append, user_config):
        """update config section by name. """
        config = self.configs.get(section_name, {})
        if config:
            if append:
                self._append_config(section_name, config, append)
            self._replace_config(section_name, config, user_config)
        else:
            console.error('%s: %s: unknown config section name' % (
                          self.current_file_name, section_name))

    def _append_config(self, section_name, config, append):
        """Append config section items"""
        if not isinstance(append, dict):
            console.error('%s: %s: append must be a dict' %
                    (self.current_file_name, section_name))
        else:
            for k in append:
                if k in config:
                    if isinstance(config[k], list):
                        config[k] += var_to_list(append[k])
                    else:
                        console.warning('%s: %s: config item %s is not a list' %
                                (self.current_file_name, section_name, k))

                else:
                    console.warning('%s: %s: unknown config item name: %s' %
                            (self.current_file_name, section_name, k))

    def _replace_config(self, section_name, config, user_config):
        """Replace config section items"""
        for k in user_config:
            if k in config:
                if isinstance(config[k], list):
                    user_config[k] = var_to_list(user_config[k])
                else:
                    user_config[k] = user_config[k]
            else:
                console.warning('%s: %s: unknown config item name: %s' %
                        (self.current_file_name, section_name, k))
                del user_config[k]
        config.update(user_config)

    def get_config(self, section_name):
        """get config section, returns default values if not set """
        return self.configs.get(section_name, {})


def cc_test_config(append=None, **kwargs):
    """cc_test_config section. """
    heap_check = kwargs.get('heap_check')
    if heap_check is not None and heap_check not in HEAP_CHECK_VALUES:
        console.error_exit('cc_test_config: heap_check can only be in %s' %
                HEAP_CHECK_VALUES)
    blade_config.update_config('cc_test_config', append, kwargs)


def cc_binary_config(append=None, **kwargs):
    """cc_binary_config section. """
    blade_config.update_config('cc_binary_config', append, kwargs)

def global_config(append=None, **kwargs):
    """global_config section. """
    blade_config.update_config('global_config', append, kwargs)


def distcc_config(append=None, **kwargs):
    """distcc_config. """
    blade_config.update_config('distcc_config', append, kwargs)


def link_config(append=None, **kwargs):
    """link_config. """
    blade_config.update_config('link_config', append, kwargs)


def java_config(append=None, **kwargs):
    """java_config. """
    blade_config.update_config('java_config', append, kwargs)


def proto_library_config(append=None, **kwargs):
    """protoc config. """
    path = kwargs.get('protobuf_include_path')
    if path:
        console.warning(('%s: proto_library_config: protobuf_include_path has '
                         'been renamed to protobuf_incs, and become a list') %
                         blade_config.current_file_name)
        del kwargs['protobuf_include_path']
        if isinstance(path, basestring) and ' ' in path:
            kwargs['protobuf_incs'] = path.split()
        else:
            kwargs['protobuf_incs'] = [path]

    blade_config.update_config('proto_library_config', append, kwargs)


def thrift_library_config(append=None, **kwargs):
    """thrift config. """
    blade_config.update_config('thrift_config', append, kwargs)


def cc_config(append=None, **kwargs):
    """extra cc config, like extra cpp include path splited by space. """
    if 'extra_incs' in kwargs:
        extra_incs = kwargs['extra_incs']
        if isinstance(extra_incs, basestring) and ' ' in extra_incs:
            console.warning('%s: cc_config: extra_incs has been changed to list' %
                    blade_config.current_file_name)
            kwargs['extra_incs'] = extra_incs.split()
    blade_config.update_config('cc_config', append, kwargs)

########NEW FILE########
__FILENAME__ = console
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the util module which provides command functions.

"""


import os
import sys


# Global color enabled or not
color_enabled = (sys.stdout.isatty() and
                 os.environ['TERM'] not in ('emacs', 'dumb'))


# _colors
_colors = {}
_colors['red']    = '\033[1;31m'
_colors['green']  = '\033[1;32m'
_colors['yellow'] = '\033[1;33m'
_colors['blue']   = '\033[1;34m'
_colors['purple'] = '\033[1;35m'
_colors['cyan']   = '\033[1;36m'
_colors['white']  = '\033[1;37m'
_colors['gray']   = '\033[1;38m'
_colors['end']    = '\033[0m'


def colors(name):
    """Return ansi console control sequence from color name"""
    if color_enabled:
        return _colors[name]
    return ''


def error(msg):
    """dump error message. """
    msg = 'Blade(error): ' + msg
    if color_enabled:
        msg = _colors['red'] + msg + _colors['end']
    print >>sys.stderr, msg


def error_exit(msg, code=1):
    """dump error message and exit. """
    error(msg)
    sys.exit(code)


def warning(msg):
    """dump warning message but continue. """
    msg = 'Blade(warning): ' + msg
    if color_enabled:
        msg = _colors['yellow'] + msg + _colors['end']
    print >>sys.stderr, msg


def info(msg, prefix=True):
    """dump info message. """
    if prefix:
        msg = 'Blade(info): ' + msg
    if color_enabled:
        msg = _colors['cyan'] + msg + _colors['end']
    print >>sys.stderr, msg

########NEW FILE########
__FILENAME__ = cu_targets
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: LI Yi <sincereli@tencent.com>
# Created:   September 27, 2013


"""
 This is the cu_target module which is the super class
 of all of the scons cu targets, like cu_library, cu_binary.

"""

import os
import blade

import build_rules
from blade_util import var_to_list
from cc_targets import CcTarget


class CuTarget(CcTarget):
    """A scons cu target subclass.

    This class is derived from SconsCcTarget and it is the base class
    of cu_library, cu_binary etc.

    """
    def __init__(self,
                 name,
                 target_type,
                 srcs,
                 deps,
                 defs,
                 incs,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cu target.

        """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)
        extra_cppflags = var_to_list(extra_cppflags)
        extra_linkflags = var_to_list(extra_linkflags)

        CcTarget.__init__(self,
                          name,
                          target_type,
                          srcs,
                          deps,
                          'yes',
                          defs,
                          incs,
                          [], [],
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)

        self.data['extra_cppflags'] = extra_cppflags
        self.data['extra_linkflags'] = extra_linkflags

    def _get_cu_flags(self):
        """_get_cu_flags.

        Return the nvcc flags according to the BUILD file and other configs.

        """
        nvcc_flags = []

        # Warnings
        if self.data.get('warning', '') == 'no':
            nvcc_flags.append('-w')

        # Defs
        defs = self.data.get('defs', [])
        nvcc_flags += [('-D' + macro) for macro in defs]

        # Optimize flags

        if (self.blade.get_options().profile == 'release' or
            self.data.get('always_optimize')):
            nvcc_flags += self._get_optimize_flags()

        # Incs
        incs = self.data.get('incs', [])
        new_incs_list = [os.path.join(self.path, inc) for inc in incs]
        new_incs_list += self._export_incs_list()
        # Remove duplicate items in incs list and keep the order
        incs_list = []
        for inc in new_incs_list:
            new_inc = os.path.normpath(inc)
            if new_inc not in incs_list:
                incs_list.append(new_inc)

        return (nvcc_flags, incs_list)


    def _cu_objects_rules(self):
        """_cu_library rules. """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)
        flags_from_option, incs_list = self._get_cu_flags()
        incs_string = " -I".join(incs_list)
        flags_string = " ".join(flags_from_option)
        objs = []
        sources = []
        for src in self.srcs:
            obj = '%s_%s_object' % (var_name,
                                    self._regular_variable_name(self.name))
            target_path = os.path.join(
                    self.build_path, self.path, '%s.objs' % self.name, src)
            self._write_rule(
                    '%s = %s.NvccObject(NVCCFLAGS="-I%s %s", target="%s" + top_env["OBJSUFFIX"]'
                    ', source="%s")' % (obj,
                                        env_name,
                                        incs_string,
                                        flags_string,
                                        target_path,
                                        self._target_file_path(self.path, src)))
            self._write_rule('%s.Depends(%s, "%s")' % (
                             env_name,
                             obj,
                             self._target_file_path(self.path, src)))
            sources.append(self._target_file_path(self.path, src))
            objs.append(obj)
        self._write_rule('%s = [%s]' % (self._objs_name(), ','.join(objs)))
        return sources


class CuLibrary(CuTarget):
    """A scons cu target subclass

    This class is derived from SconsCuTarget and it generates the cu_library
    rules according to user options.
    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 defs,
                 incs,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        type = 'cu_library'
        CuTarget.__init__(self,
                          name,
                          type,
                          srcs,
                          deps,
                          defs,
                          incs,
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.
        """
        self._prepare_to_generate_rule()
        self._cu_objects_rules()
        self._cc_library()


def cu_library(name,
               srcs=[],
               deps=[],
               defs=[],
               incs=[],
               extra_cppflags=[],
               extra_linkflags=[],
               **kwargs):
    target = CuLibrary(name,
                       srcs,
                       deps,
                       defs,
                       incs,
                       extra_cppflags,
                       extra_linkflags,
                       blade.blade,
                       kwargs)
    blade.blade.register_target(target)


build_rules.register_function(cu_library)


class CuBinary(CuTarget):
    """A scons cu target subclass

    This class is derived from SconsCuTarget and it generates the cu_binary
    rules according to user options.
    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 defs,
                 incs,
                 extra_cppflags,
                 extra_linkflags,
                 blade,
                 kwargs):
        type = 'cu_binary'
        CuTarget.__init__(self,
                          name,
                          type,
                          srcs,
                          deps,
                          defs,
                          incs,
                          extra_cppflags,
                          extra_linkflags,
                          blade,
                          kwargs)

    def _cc_binary(self):
        """_cc_binary rules. """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)

        platform = self.blade.get_scons_platform()

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()
        if whole_link_flags:
            self._write_rule(
                    '%s.Append(LINKFLAGS=[%s])' % (env_name, whole_link_flags))

        if self.data.get('export_dynamic'):
            self._write_rule(
                '%s.Append(LINKFLAGS="-rdynamic")' % env_name)

        self._setup_extra_link_flags()

        self._write_rule('{0}.Replace('
                       'CC={0}["NVCC"], '
                       'CPP={0}["NVCC"], '
                       'CXX={0}["NVCC"], '
                       'LINK={0}["NVCC"])'.format(env_name))

        self._write_rule('%s = %s.Program("%s", %s, %s)' % (
            var_name,
            env_name,
            self._target_file_path(),
            self._objs_name(),
            lib_str))
        self._write_rule('%s.Depends(%s, %s)' % (
            env_name,
            var_name,
            self._objs_name()))

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                    env_name, var_name, ', '.join(link_all_symbols_lib_list)))

        #self._write_rule('%s.Append(LINKFLAGS=str(version_obj[0]))' % env_name)
        self._write_rule('%s.Requires(%s, version_obj)' % (
                         env_name, var_name))

#    def _cu_binary(self):
#        """_cu_binary rules. """
#        env_name = self._env_name()
#        var_name = self._generate_variable_name(self.path, self.name)
#
#        platform = self.blade.get_scons_platform()
#
#        (link_all_symbols_lib_list,
#         lib_str,
#         whole_link_flags) = self._get_static_deps_lib_list()
#        print "%s, %s, %s" % (env_name, self._objs_name(), self._target_file_path())
#
#        self._write_rule('%s = %s.NvccBinary(NVCCFLAGS="%s", target="%s"' % (
#            var_name,
#            env_name,
#            '',
#            self._target_file_path()))
#        self._write_rule('%s.Depends(%s, %s)' % (
#            env_name,
#            var_name,
#            self._objs_name()))
#        self._generate_target_explict_dependency(var_name)
#
#        if link_all_symbols_lib_list:
#            self._write_rule('%s.Depends(%s, [%s])' % (
#                    env_name, var_name, ', '.join(link_all_symbols_lib_list)))

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.
        """
        self._prepare_to_generate_rule()
        self._cu_objects_rules()
        self._cc_binary()


def cu_binary(name,
              srcs=[],
              deps=[],
              defs=[],
              incs=[],
              extra_cppflags=[],
              extra_linkflags=[],
              **kwargs):
    target = CuBinary(name,
                      srcs,
                      deps,
                      defs,
                      incs,
                      extra_cppflags,
                      extra_linkflags,
                      blade.blade,
                      kwargs)
    blade.blade.register_target(target)


build_rules.register_function(cu_binary)

########NEW FILE########
__FILENAME__ = dependency_analyzer
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng Chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong Peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the dependencies expander module which accepts the targets loaded
 from BUILD files and will find all of the targets needed by the target and
 add extra options according to different target types.

"""


import console


"""
Given the map of related targets, i.e., the subset of target_database
that are dependencies of those targets speicifed in Blade command
line, this utility class expands the 'deps' property of each target
to be all direct and indirect dependencies of that target.

After expanded the dependencies of targets, sort the topologically
and then provide the query interface to users by blade manager.

"""


def analyze_deps(related_targets):
    """analyze the dependency relationship between targets.

    Input: related targets after loading targets from BUILD files.
           {(target_path, target_name) : (target_data), ...}

    Output:the targets that are expanded and the keys sorted
           [all the targets keys] - sorted
           {(target_path, target_name) : (target_data with deps expanded), ...}

    """
    _expand_deps(related_targets)
    keys_list_sorted = _topological_sort(related_targets)

    return keys_list_sorted


def _expand_deps(targets):
    """_expand_deps.

    Find out all the targets that certain target depeneds on them.
    Fill the related options according to different targets.

    """
    deps_map_cache = {}  # Cache expanded target deps to avoid redundant expand
    for target_id in targets:
        target = targets[target_id]
        target.expanded_deps = _find_all_deps(target_id, targets, deps_map_cache)
        # Handle the special case: dependencies of a dynamic_cc_binary
        # must be built as dynamic libraries.
        if target.data.get('dynamic_link'):
            for dep in target.expanded_deps:
                targets[dep].data['build_dynamic'] = True
        elif target.type == 'swig_library':
            for dep in target.expanded_deps:
                if targets[dep].type == 'proto_library':
                    targets[dep].data['generate_php'] = True
        elif target.type == 'py_binary':
            for dep in target.expanded_deps:
                targets[dep].data['generate_python'] = True
        elif target.type == 'java_jar':
            for dep in target.expanded_deps:
                targets[dep].data['generate_java'] = True


def _find_all_deps(target_id, targets, deps_map_cache, root_targets=None):
    """_find_all_deps.

    Return all targets depended by target_id directly and/or indirectly.
    We need the parameter root_target_id to check loopy dependency.

    """
    new_deps_list = deps_map_cache.get(target_id)
    if new_deps_list is not None:
        return new_deps_list

    if root_targets is None:
        root_targets = set()

    root_targets.add(target_id)
    new_deps_list = []

    for d in targets[target_id].expanded_deps:
        # loop dependency
        if d in root_targets:
            err_msg = ''
            for t in root_targets:
                err_msg += '//%s:%s --> ' % (t[0], t[1])
            console.error_exit('loop dependency found: //%s:%s --> [%s]' % (
                       d[0], d[1], err_msg))
        new_deps_piece = [d]
        if d not in targets:
            console.error_exit('Target %s:%s depends on %s:%s, '
                               'but it is missing, exit...' % (
                                   target_id[0], target_id[1],
                                   d[0], d[1]))
        new_deps_piece += _find_all_deps(d, targets, deps_map_cache, root_targets)
        # Append new_deps_piece to new_deps_list, be aware of
        # de-duplication:
        for nd in new_deps_piece:
            if nd in new_deps_list:
                new_deps_list.remove(nd)
            new_deps_list.append(nd)

    deps_map_cache[target_id] = new_deps_list
    root_targets.remove(target_id)

    return new_deps_list


def _topological_sort(pairlist):
    """Sort the targets. """
    numpreds = {}    # elt -> # of predecessors
    successors = {}  # elt -> list of successors
    for second, target in pairlist.items():
        if second not in numpreds:
            numpreds[second] = 0
        deps = target.expanded_deps
        for first in deps:
            # make sure every elt is a key in numpreds
            if first not in numpreds:
                numpreds[first] = 0

            # since first < second, second gains a pred ...
            numpreds[second] = numpreds[second] + 1

            # ... and first gains a succ
            if first in successors:
                successors[first].append(second)
            else:
                successors[first] = [second]

    # suck up everything without a predecessor
    answer = filter(lambda x, numpreds=numpreds: numpreds[x] == 0,
                    numpreds.keys())

    # for everything in answer, knock down the pred count on
    # its successors; note that answer grows *in* the loop
    for x in answer:
        assert numpreds[x] == 0
        del numpreds[x]
        if x in successors:
            for y in successors[x]:
                numpreds[y] = numpreds[y] - 1
                if numpreds[y] == 0:
                    answer.append(y)

    return answer

########NEW FILE########
__FILENAME__ = gen_rule_target
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the scons_gen_rule module which inherits the SconsTarget
 and generates related gen rule rules.

"""


import os

import blade
import build_rules
import java_jar_target
from blade_util import var_to_list
from target import Target


class GenRuleTarget(Target):
    """A scons gen rule target subclass.

    This class is derived from Target.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 outs,
                 cmd,
                 blade,
                 kwargs):
        """Init method.

        Init the gen rule target.

        """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)
        outs = var_to_list(outs)

        Target.__init__(self,
                        name,
                        'gen_rule',
                        srcs,
                        deps,
                        blade,
                        kwargs)

        self.data['outs'] = outs
        self.data['cmd'] = cmd

    def _srcs_list(self, path, srcs):
        """Returns srcs list. """
        return ','.join(['"%s"' % os.path.join(self.build_path, path, src)
            for src in srcs])

    def _generate_header_files(self):
        """Whether this target generates header files during building."""
        # Be conservative: Assume gen_rule always generates header files.
        return True

    def scons_rules(self):
        """scons_rules.

        Description
        -----------
        It outputs the scons rules according to user options.

        """
        self._clone_env()

        # Build java source according to its option
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)

        srcs_str = ''
        if not self.srcs:
            srcs_str = 'time_value'
        else:
            srcs_str = self._srcs_list(self.path, self.srcs)
        cmd = self.data['cmd']
        cmd = cmd.replace('$SRCS', '$SOURCES')
        cmd = cmd.replace('$OUTS', '$TARGETS')
        cmd = cmd.replace('$FIRST_SRC', '$SOURCE')
        cmd = cmd.replace('$FIRST_OUT', '$TARGET')
        cmd = cmd.replace('$BUILD_DIR', self.build_path)
        self._write_rule('%s = %s.Command([%s], [%s], "%s")' % (
                var_name,
                env_name,
                self._srcs_list(self.path, self.data['outs']),
                srcs_str,
                cmd))

        self.var_name = var_name

        targets = self.blade.get_build_targets()
        dep_var_list = []
        dep_skip_list = ['system_library', 'prebuilt_cc_library']
        for i in self.expanded_deps:
            dep_target = targets[i]
            if dep_target.type in dep_skip_list:
                continue
            elif dep_target.type == 'swig_library':
                dep_var_name = self._generate_variable_name(
                        dep_target.path, dep_target.name, 'dynamic_py')
                dep_var_list.append(dep_var_name)
                dep_var_name = self._generate_variable_name(
                        dep_target.path, dep_target.name, 'dynamic_java')
                dep_var_list.append(dep_var_name)
            elif dep_target.type == 'java_jar':
                dep_var_list += dep_target.data.get('java_jars', [])
            else:
                dep_var_name = self._generate_variable_name(
                        dep_target.path, dep_target.name)
                dep_var_list.append(dep_var_name)

        for dep_var_name in dep_var_list:
            self._write_rule('%s.Depends(%s, %s)' % (env_name,
                                                     var_name,
                                                     dep_var_name))


def gen_rule(name,
             srcs=[],
             deps=[],
             outs=[],
             cmd='',
             **kwargs):
    """scons_gen_rule. """
    gen_rule_target = GenRuleTarget(name,
                                    srcs,
                                    deps,
                                    outs,
                                    cmd,
                                    blade.blade,
                                    kwargs)
    blade.blade.register_target(gen_rule_target)


build_rules.register_function(gen_rule)

########NEW FILE########
__FILENAME__ = java_jar_target
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the scons_java_jar module which inherits the SconsTarget
 and generates related java jar rules.

"""


import os
import blade

import build_rules
import console
import configparse

from blade_util import relative_path
from blade_util import var_to_list
from target import Target


class JavaJarTarget(Target):
    """A java jar target subclass.

    This class is derived from Target and generates relates java jar
    rules.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 prebuilt,
                 blade,
                 kwargs):
        """Init method.

        Init the java jar target.

        """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)

        Target.__init__(self,
                        name,
                        'java_jar',
                        srcs,
                        deps,
                        blade,
                        kwargs)

        if prebuilt:
            self.type = 'prebuilt_java_jar'
            self.data['jar_class_path'] = self._prebuilt_java_jar_src_path()
        self.data['java_jars'] = []
        self.java_jar_cmd_list = []
        self.cmd_var_list = []
        self.java_jar_after_dep_source_list = []
        self.targets_dependency_map = {}
        self.java_jar_dep_vars = {}

    def _java_jar_gen_class_root(self, path, name):
        """Gen class root. """
        return os.path.join(self.build_path, path, '%s_classes' % name)

    def _dep_is_jar_to_compile(self, dep):
        """Check the target is java_jar target or not. """
        targets = self.blade.get_build_targets()
        target_type = targets[dep].type
        return ('java_jar' in target_type and 'prebuilt' not in target_type)

    def _java_jar_rules_prepare_dep(self, new_src):
        """Prepare building java jars, make class root and other work. """
        env_name = self._env_name()

        new_dep_source_list = []
        cmd_var = '%s_cmd_dep_var_' % self.name
        dep_cmd_var = ''
        cmd_var_idx = 0
        for dep_src in self.java_jar_dep_source_list:
            dep_dir = relative_path(dep_src[0], dep_src[1])
            new_path = os.path.join(new_src, dep_dir)
            if dep_dir != '.':
                new_dep_source_list.append(new_path)
            cmd_var_id = cmd_var + str(cmd_var_idx)
            if cmd_var_idx == 0:
                dep_cmd_var = cmd_var_id
            if not new_path in self.java_jar_cmd_list:
                self._write_rule('%s = %s.Command("%s", "", [Mkdir("%s")])' % (
                        cmd_var_id,
                        env_name,
                        new_path,
                        new_path))
                self.cmd_var_list.append(cmd_var_id)
                self.java_jar_cmd_list.append(new_path)
                cmd_var_idx += 1
            cmd_var_id = cmd_var + str(cmd_var_idx)
            cmd_var_idx += 1
            cmd = 'cp %s/*.java %s' % (dep_src[0], new_path)
            if dep_dir != '.':
                src_dir = dep_src[0]
            else:
                src_dir = ''
            self._write_rule('%s = %s.Command("%s/dummy_file_%s", "%s", ["%s"])' % (
                    cmd_var_id,
                    env_name,
                    new_path,
                    cmd_var_idx,
                    src_dir,
                    cmd))
            self.cmd_var_list.append(cmd_var_id)

        targets = self.blade.get_build_targets()
        if dep_cmd_var:
            for dep in self.expanded_deps:
                explict_files_depended = targets[dep].data.get('java_sources_explict_dependency')
                if explict_files_depended:
                    self._write_rule('%s.Depends(%s, %s)' % (
                                      env_name,
                                      dep_cmd_var,
                                      explict_files_depended))

        self.java_jar_after_dep_source_list = new_dep_source_list

    def _java_jar_deps_list(self, deps):
        """Returns a jar list string that this targets depends on. """
        jar_list = []
        for jar in deps:
            if not jar:
                continue

            if not self._dep_is_jar_to_compile(jar):
                continue

            jar_name = '%s.jar' % jar[1]
            jar_path = os.path.join(self.build_path, jar[0], jar_name)
            jar_list.append(jar_path)
        return jar_list

    def _java_jar_rules_compile_src(self,
                                    target_source_list,
                                    new_src,
                                    pack_list,
                                    classes_var_list):
        """Compile the java sources. """
        env_name = self._env_name()
        class_root = self._java_jar_gen_class_root(self.path,
                                                   self.name)
        jar_list = self._java_jar_deps_list(self.expanded_deps)
        classpath_list = self.java_classpath_list
        classpath = ':'.join(classpath_list + jar_list)

        new_target_source_list = []
        for src_dir in target_source_list:
            rel_path = relative_path(src_dir, self.path)
            pos = rel_path.find('/')
            package = rel_path[pos + 1:]
            new_src_path = os.path.join(new_src, package)
            new_target_source_list.append(new_src_path)

            cmd_var = '%s_cmd_src_var_' % self.name
            cmd_var_idx = 0
            if not new_src_path in self.java_jar_cmd_list:
                cmd_var_id = cmd_var + str(cmd_var_idx)
                self._write_rule('%s = %s.Command("%s", "", [Mkdir("%s")])' % (
                        cmd_var_id,
                        env_name,
                        new_src_path,
                        new_src_path))
                cmd_var_idx += 1
                self.java_jar_cmd_list.append(new_src_path)
            cmd_var_id = cmd_var + str(cmd_var_idx)
            cmd_var_idx += 1
            cmd = 'cp %s/*.java %s' % (src_dir, new_src_path)
            self._write_rule('%s = %s.Command("%s/dummy_src_file_%s", "%s", ["%s"])' % (
                    cmd_var_id,
                    env_name,
                    new_src_path,
                    cmd_var_idx,
                    src_dir,
                    cmd))
            self.cmd_var_list.append(cmd_var_id)

        new_target_idx = 0
        classes_var = '%s_classes' % (
                self._generate_variable_name(self.path, self.name))

        java_config = configparse.blade_config.get_config('java_config')
        source_version = java_config['source_version']
        target_version = java_config['target_version']
        javac_cmd = 'javac'
        if source_version:
            javac_cmd += ' -source %s' % source_version
        if target_version:
            javac_cmd += ' -target %s' % target_version
        if not classpath:
            javac_class_path = ''
        else:
            javac_class_path = ' -classpath %s' % classpath
        javac_classes_out = ' -d %s' % class_root
        javac_source_path = ' -sourcepath %s' % new_src

        no_dup_source_list = []
        for dep_src in self.java_jar_after_dep_source_list:
            if not dep_src in no_dup_source_list:
                no_dup_source_list.append(dep_src)
        for src in new_target_source_list:
            if not src in no_dup_source_list:
                no_dup_source_list.append(src)

        source_files_list = []
        for src_dir in no_dup_source_list:
            srcs = os.path.join(src_dir, '*.java')
            source_files_list.append(srcs)

        cmd = javac_cmd + javac_class_path + javac_classes_out
        cmd += javac_source_path + ' ' + ' '.join(source_files_list)
        dummy_file = '%s_dummy_file_%s' % (
                self.name, str(new_target_idx))
        new_target_idx += 1
        class_root_dummy = os.path.join(class_root, dummy_file)
        self._write_rule('%s = %s.Command("%s", "", ["%s"])' % (
                classes_var,
                env_name,
                class_root_dummy,
                cmd))

        # Find out the java_jar depends
        targets = self.blade.get_build_targets()
        for dep in self.expanded_deps:
            dep_java_jar_list = targets[dep].data.get('java_jars')
            if dep_java_jar_list:
                self._write_rule('%s.Depends(%s, %s)' % (
                    env_name,
                    classes_var,
                    dep_java_jar_list))

        for cmd in self.cmd_var_list:
            self._write_rule('%s.Depends(%s, %s)' % (
                    env_name,
                    classes_var,
                    cmd))

        self.java_classpath_list.append(class_root)
        classes_var_list.append(classes_var)
        pack_list.append(class_root)

    def _java_jar_rules_make_jar(self, pack_list, classes_var_list):
        """Make the java jar files, pack the files that the target needs. """
        env_name = self._env_name()
        target_base_dir = os.path.join(self.build_path, self.path)

        cmd_jar = '%s_cmd_jar' % self.name
        cmd_var = '%s_cmd_jar_var_' % self.name
        cmd_idx = 0
        cmd_var_id = ''
        cmd_list = []
        targets = self.blade.get_build_targets()
        build_file = os.path.join(self.blade.get_root_dir(), 'BLADE_ROOT')
        for class_path in pack_list:
            # need to place one dummy file into the source folder for user builder
            build_file_dst = os.path.join(class_path, 'BLADE_ROOT')
            if not build_file_dst in self.java_jar_cmd_list:
                self._write_rule('%s = %s.Command("%s", "%s", [Copy("%s", "%s")])' % (
                        cmd_jar,
                        env_name,
                        build_file_dst,
                        build_file,
                        build_file_dst,
                        build_file))
                cmd_list.append(cmd_jar)
                self.java_jar_cmd_list.append(build_file_dst)
            for key in self.expanded_deps:
                f = targets[key].data.get('jar_packing_files')
                if not f:
                    continue
                cmd_var_id = cmd_var + str(cmd_idx)
                f_dst = os.path.join(class_path, os.path.basename(f[0]))
                if not f_dst in self.java_jar_cmd_list:
                    self._write_rule('%s = %s.Command("%s", "%s", \
                            [Copy("$TARGET","$SOURCE")])' % (
                                    cmd_var_id,
                                    env_name,
                                    f_dst,
                                    f[0]))
                    self.java_jar_cmd_list.append(f_dst)
                    cmd_list.append(cmd_var_id)
                    cmd_idx += 1

            rel_path = relative_path(class_path, target_base_dir)
            class_path_name = rel_path.replace('/', '_')
            jar_var = '%s_%s_jar' % (
                self._generate_variable_name(self.path, self.name),
                    class_path_name)
            jar_target = '%s.jar' % self._target_file_path()
            jar_target_object = '%s.jar' % jar_target
            cmd_remove_var = 'cmd_remove_%s' % jar_var
            removed = False
            if (not jar_target in self.java_jar_cmd_list) and (
                os.path.exists(jar_target)):
                self._write_rule('%s = %s.Command("%s", "", [Delete("%s")])' % (
                        cmd_remove_var,
                        env_name,
                        jar_target_object,
                        jar_target))
                removed = True
            self._write_rule('%s = %s.BladeJar(["%s"], "%s")' % (
                    jar_var,
                    env_name,
                    jar_target,
                    build_file_dst))
            self.data['java_jars'].append(jar_target)

            for dep_classes_var in classes_var_list:
                if dep_classes_var:
                    self._write_rule('%s.Depends(%s, %s)' % (
                            env_name, jar_var, dep_classes_var))
            for cmd in cmd_list:
                self._write_rule('%s.Depends(%s, %s)' % (
                        env_name, jar_var, cmd))
            if removed:
                self._write_rule('%s.Depends(%s, %s)' % (
                        env_name, jar_var, cmd_remove_var))

    def _prebuilt_java_jar_build_path(self):
        """The build path for pre build java jar. """
        return os.path.join(self.build_path,
                            self.path,
                            '%s.jar' % self.name)

    def _prebuilt_java_jar_src_path(self):
        """The source path for pre build java jar. """
        return os.path.join(self.path, '%s.jar' % self.name)

    def _prebuilt_java_jar(self):
        """The pre build java jar rules. """
        self._write_rule(
                'Command("%s", "%s", Copy("$TARGET", "$SOURCE"))' % (
                    self._prebuilt_java_jar_build_path(),
                    self._prebuilt_java_jar_src_path()))

    def scons_rules(self):
        """scons_rules.

        Description
        -----------
        It outputs the scons rules according to user options.

        """
        self._clone_env()

        if self.type == 'prebuilt_java_jar':
            self._prebuilt_java_jar()
            return

        env_name = self._env_name()
        class_root = self._java_jar_gen_class_root(self.path,
                                                   self.name)

        targets = self.blade.get_build_targets()

        for key in self.expanded_deps:
            self.cmd_var_list += targets[key].data.get('java_dep_var', [])

        self.java_jar_dep_source_list = []
        for key in self.expanded_deps:
            dep_target = targets[key]
            sources = dep_target.data.get('java_sources')
            if sources:
                self.java_jar_dep_source_list.append(sources)

        self.java_classpath_list = []
        for key in self.expanded_deps:
            class_path = targets[key].data.get('jar_class_path')
            if class_path:
                self.java_classpath_list.append(class_path)

        # make unique
        self.java_jar_dep_source_list = list(set(self.java_jar_dep_source_list))

        if not class_root in self.java_jar_cmd_list:
            self._write_rule('%s.Command("%s", "", [Mkdir("%s")])' % (
                    env_name, class_root, class_root))
            self.java_jar_cmd_list.append(class_root)

        target_source_list = []
        for src_dir in self.srcs:
            java_src = os.path.join(self.path, src_dir)
            if not java_src in target_source_list:
                target_source_list.append(java_src)

        new_src_dir = ''
        src_dir = '%s_src' % self.name
        new_src_dir = os.path.join(self.build_path, self.path, src_dir)
        if not new_src_dir in self.java_jar_cmd_list:
            self._write_rule('%s.Command("%s", "", [Mkdir("%s")])' % (
                    env_name,
                    new_src_dir,
                    new_src_dir))
            self.java_jar_cmd_list.append(new_src_dir)

        pack_list = []
        classes_var_list = []
        if self.java_jar_dep_source_list:
            self._java_jar_rules_prepare_dep(new_src_dir)

        self._java_jar_rules_compile_src(target_source_list,
                                         new_src_dir,
                                         pack_list,
                                         classes_var_list)

        self._java_jar_rules_make_jar(pack_list, classes_var_list)


def java_jar(name,
             srcs=[],
             deps=[],
             prebuilt=False,
             pre_build=False,
             **kwargs):
    """Define java_jar target. """
    target = JavaJarTarget(name,
                           srcs,
                           deps,
                           prebuilt or pre_build,
                           blade.blade,
                           kwargs)
    if pre_build:
        console.warning('//%s:%s: "pre_build" has been deprecated, '
                        'please use "prebuilt"' % (target.path,
                                                   target.name))
    blade.blade.register_target(target)


build_rules.register_function(java_jar)

########NEW FILE########
__FILENAME__ = java_targets
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: CHEN Feng <phongchen@tencent.com>
# Created: Jun 26, 2013


"""
Implement java_library, java_binary and java_test
"""


import os
import blade

import build_rules

from blade_util import var_to_list
from target import Target


class JavaTarget(Target):
    """A java jar target subclass.

    This class is derived from Target and generates relates java jar
    rules.

    """
    def __init__(self,
                 name,
                 type,
                 srcs,
                 deps,
                 prebuilt,
                 blade,
                 kwargs):
        """Init method.

        Init the java jar target.

        """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)

        Target.__init__(self,
                        name,
                        type,
                        srcs,
                        deps,
                        blade,
                        kwargs)

    def _java_jar_gen_class_root(self, path, name):
        """Gen class root. """
        return os.path.join(self.build_path, path, '%s.classes' % name)

    def _dep_is_jar_to_compile(self, dep):
        """Check the target is java_jar target or not. """
        targets = self.blade.get_build_targets()
        target_type = targets[dep].type
        return ('java_jar' in target_type and 'prebuilt' not in target_type)

    def _java_jar_deps_list(self, deps):
        """Returns a jar list string that this targets depends on. """
        jar_list = []
        for jar in deps:
            if not jar:
                continue

            if not self._dep_is_jar_to_compile(jar):
                continue

            jar_name = '%s.jar' % jar[1]
            jar_path = os.path.join(self.build_path, jar[0], jar_name)
            jar_list.append(jar_path)
        return jar_list

    def scons_rules(self):
        """scons_rules.
        Description
        -----------
        It outputs the scons rules according to user options.

        """
        self._generate_classes()
        self._generate_jar()


class JavaLibrary(JavaTarget):
    """JavaLibrary"""
    def __init__(self, name, srcs, deps, prebuilt, **kwargs):
        type = 'java_library'
        if prebuilt:
            type = 'prebuilt_java_library'
        JavaTarget.__init__(self, name, type, srcs, deps, prebuilt, kwargs)


class JavaBinary(JavaTarget):
    """JavaLibrary"""
    def __init__(self, name, srcs, deps, **kwargs):
        type = 'java_binary'
        JavaTarget.__init__(self, name, type, srcs, deps, False, kwargs)


class JavaTest(JavaBinary):
    """JavaLibrary"""
    def __init__(self, name, srcs, deps, **kwargs):
        type = 'java_binary'
        JavaTarget.__init__(self, name, type, srcs, deps, False, kwargs)


def java_library(name,
                 srcs=[],
                 deps=[],
                 prebuilt=False,
                 **kwargs):
    """Define java_jar target. """
    target = JavaLibrary(name,
                         srcs,
                         deps,
                         prebuilt,
                         blade.blade,
                         kwargs)
    blade.blade.register_target(target)


def java_binary(name,
                srcs=[],
                deps=[],
                **kwargs):
    """Define java_jar target. """
    target = JavaBinary(name,
                        srcs,
                        deps,
                        blade.blade,
                        kwargs)
    blade.blade.register_target(target)


def java_test(name,
              srcs=[],
              deps=[],
              **kwargs):
    """Define java_jar target. """
    target = JavaTest(name,
                      srcs,
                      deps,
                      blade.blade,
                      kwargs)
    blade.blade.register_target(target)


build_rules.register_function(java_binary)
build_rules.register_function(java_library)
build_rules.register_function(java_test)

########NEW FILE########
__FILENAME__ = lex_yacc_target
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Feng Chen <phongchen@tencent.com>


"""Define proto_library target
"""


import os
import blade

import console
import build_rules
from cc_targets import CcTarget


class LexYaccLibrary(CcTarget):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget and it generates lex yacc rules.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 recursive,
                 prefix,
                 blade,
                 kwargs):
        """Init method.

        Init the cc lex yacc target

        """
        if len(srcs) != 2:
            raise Exception, ('"srcs" for lex_yacc_library should '
                              'be a pair of (lex_source, yacc_source)')
        CcTarget.__init__(self,
                          name,
                          'lex_yacc_library',
                          srcs,
                          deps,
                          'yes',
                          [], [], [], [], [], [],
                          blade,
                          kwargs)
        self.data['recursive'] = recursive
        self.data['prefix'] = prefix

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        env_name = self._env_name()

        var_name = self._generate_variable_name(self.path, self.name)
        lex_source_file = self._target_file_path(self.path,
                                                 self.srcs[0])
        lex_cc_file = '%s.cc' % lex_source_file

        lex_flags = []
        if self.data.get('recursive'):
            lex_flags.append('-R')
        prefix = self.data.get('prefix')
        if prefix:
            lex_flags.append('-P %s' % prefix)
        self._write_rule(
            'lex_%s = %s.CXXFile(LEXFLAGS=%s, target="%s", source="%s")' % (
                var_name, env_name, lex_flags, lex_cc_file, lex_source_file))
        yacc_source_file = os.path.join(self.build_path,
                                        self.path,
                                        self.srcs[1])
        yacc_cc_file = '%s.cc' % yacc_source_file
        yacc_hh_file = '%s.hh' % yacc_source_file

        yacc_flags = []
        if prefix:
            yacc_flags.append('-p %s' % prefix)

        self._write_rule(
            'yacc_%s = %s.Yacc(YACCFLAGS=%s, target=["%s", "%s"], source="%s")' % (
                var_name, env_name, yacc_flags,
                yacc_cc_file, yacc_hh_file, yacc_source_file))
        self._write_rule('%s.Depends(lex_%s, yacc_%s)' % (env_name,
                                                          var_name, var_name))

        obj_names = []
        obj_name = '%s_object' % self._generate_variable_name(
                    self.path, self.srcs[0] + '.cc')
        obj_names.append(obj_name)
        self._write_rule('%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                         'source="%s")' % (obj_name,
                                             env_name,
                                             lex_cc_file,
                                             lex_cc_file))

        obj_name = '%s_object' % self._generate_variable_name(
                    self.path, self.srcs[1] + '.cc')
        obj_names.append(obj_name)
        self._write_rule('%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                         'source="%s")' % (obj_name,
                                             env_name,
                                             yacc_cc_file,
                                             yacc_cc_file))

        self._write_rule('%s = [%s]' % (self._objs_name(), ','.join(obj_names)))
        self._cc_library()
        options = self.blade.get_options()
        if (getattr(options, 'generate_dynamic', False) or
            self.data.get('build_dynamic', False)):
            self._dynamic_cc_library()


def lex_yacc_library(name,
                     srcs=[],
                     deps=[],
                     recursive=False,
                     prefix=None,
                     **kwargs):
    """lex_yacc_library. """
    target = LexYaccLibrary(name,
                            srcs,
                            deps,
                            recursive,
                            prefix,
                            blade.blade,
                            kwargs)
    blade.blade.register_target(target)


build_rules.register_function(lex_yacc_library)

########NEW FILE########
__FILENAME__ = load_build_files
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng Chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong Peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the CmdOptions module which parses the users'
 input and provides hint for users.

"""


import os
import traceback

import build_rules
import console
from blade_util import relative_path


# import these modules make build functions registered into build_rules
# TODO(chen3feng): Load build modules dynamically to enable extension.
import cc_targets
import cu_targets
import gen_rule_target
import java_jar_target
import java_targets
import lex_yacc_target
import proto_library_target
import py_targets
import resource_library_target
import swig_library_target
import thrift_library


class TargetAttributes(object):
    """Build target attributes
    """
    def __init__(self, options):
        self._options = options

    @property
    def bits(self):
        return int(self._options.m)

    @property
    def arch(self):
        if self._options.m == '32':
            return 'i386'
        else:
            return 'x86_64'

    def is_debug(self):
        return self._options.profile == 'debug'


build_target = None


def _find_dir_depender(dir, blade):
    """_find_dir_depender to find which target depends on the dir.

    """
    target_database = blade.get_target_database()
    for key in target_database:
        for dkey in target_database[key].expanded_deps:
            if dkey[0] == dir:
                return '//%s:%s' % (target_database[key].path,
                                    target_database[key].name)
    return None


def _report_not_exist(source_dir, path, blade):
    """ Report dir or BUILD file does not exist
    """
    depender = _find_dir_depender(source_dir, blade)
    if depender:
        console.error_exit('//%s not found, required by %s, exit...' % (path, depender))
    else:
        console.error_exit('//%s not found, exit...' % path)


def enable_if(cond, true_value, false_value=None):
    """A global function can be called in BUILD to filter srcs/deps by target"""
    if cond:
        ret = true_value
    else:
        ret = false_value
    if ret is None:
        ret = []
    return ret

build_rules.register_function(enable_if)


IGNORE_IF_FAIL = 0
WARN_IF_FAIL = 1
ABORT_IF_FAIL = 2


def _load_build_file(source_dir, action_if_fail, processed_source_dirs, blade):
    """_load_build_file to load the BUILD and place the targets into database.

    Invoked by _load_targets.  Load and execute the BUILD
    file, which is a Python script, in source_dir.  Statements in BUILD
    depends on global variable current_source_dir, and will register build
    target/rules into global variables target_database.  If path/BUILD
    does NOT exsit, take action corresponding to action_if_fail.  The
    parameters processed_source_dirs refers to a set defined in the
    caller and used to avoid duplicated execution of BUILD files.

    """

    # Initialize the build_target at first time, to be used for BUILD file
    # loaded by execfile
    global build_target
    if build_target is None:
        build_target = TargetAttributes(blade.get_options())
        build_rules.register_variable('build_target', build_target)

    source_dir = os.path.normpath(source_dir)
    # TODO(yiwang): the character '#' is a magic value.
    if source_dir in processed_source_dirs or source_dir == '#':
        return
    processed_source_dirs.add(source_dir)

    if not os.path.exists(source_dir):
        _report_not_exist(source_dir, source_dir, blade)

    old_current_source_path = blade.get_current_source_path()
    blade.set_current_source_path(source_dir)
    build_file = os.path.join(source_dir, 'BUILD')
    if os.path.exists(build_file):
        try:
            # The magic here is that a BUILD file is a Python script,
            # which can be loaded and executed by execfile().
            execfile(build_file, build_rules.get_all(), None)
        except SystemExit:
            console.error_exit('%s: fatal error, exit...' % build_file)
        except:
            console.error_exit('Parse error in %s, exit...\n%s' % (
                    build_file, traceback.format_exc()))
    else:
        if action_if_fail == ABORT_IF_FAIL:
            _report_not_exist(source_dir, build_file, blade)

    blade.set_current_source_path(old_current_source_path)


def _find_depender(dkey, blade):
    """_find_depender to find which target depends on the target with dkey.

    """
    target_database = blade.get_target_database()
    for key in target_database:
        if dkey in target_database[key].expanded_deps:
            return '//%s:%s' % (target_database[key].path,
                                target_database[key].name)
    return None


def load_targets(target_ids, working_dir, blade_root_dir, blade):
    """load_targets.

    Parse and load targets, including those specified in command line
    and their direct and indirect dependencies, by loading related BUILD
    files.  Returns a map which contains all these targets.

    """
    target_database = blade.get_target_database()

    # targets specified in command line
    cited_targets = set()
    # cited_targets and all its dependencies
    related_targets = {}
    # source dirs mentioned in command line
    source_dirs = []
    # to prevent duplicated loading of BUILD files
    processed_source_dirs = set()

    direct_targets = []
    all_command_targets = []
    # Parse command line target_ids.  For those in the form of <path>:<target>,
    # record (<path>,<target>) in cited_targets; for the rest (with <path>
    # but without <target>), record <path> into paths.
    for target_id in target_ids:
        if target_id.find(':') == -1:
            source_dir, target_name = target_id, '*'
        else:
            source_dir, target_name = target_id.rsplit(':', 1)

        source_dir = relative_path(os.path.join(working_dir, source_dir),
                                    blade_root_dir)

        if target_name != '*' and target_name != '':
            cited_targets.add((source_dir, target_name))
        elif source_dir.endswith('...'):
            source_dir = source_dir[:-3]
            if not source_dir:
                source_dir = './'
            source_dirs.append((source_dir, WARN_IF_FAIL))
            for root, dirs, files in os.walk(source_dir):
                # Skip over subdirs starting with '.', e.g., .svn.
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for d in dirs:
                    source_dirs.append((os.path.join(root, d), IGNORE_IF_FAIL))
        else:
            source_dirs.append((source_dir, ABORT_IF_FAIL))

    direct_targets = list(cited_targets)

    # Load BUILD files in paths, and add all loaded targets into
    # cited_targets.  Together with above step, we can ensure that all
    # targets mentioned in the command line are now in cited_targets.
    for source_dir, action_if_fail in source_dirs:
        _load_build_file(source_dir,
                         action_if_fail,
                         processed_source_dirs,
                         blade)

    for key in target_database:
        cited_targets.add(key)
    all_command_targets = list(cited_targets)

    # Starting from targets specified in command line, breath-first
    # propagate to load BUILD files containing directly and indirectly
    # dependent targets.  All these targets form related_targets,
    # which is a subset of target_databased created by loading  BUILD files.
    while cited_targets:
        source_dir, target_name = cited_targets.pop()
        target_id = (source_dir, target_name)
        if target_id in related_targets:
            continue

        _load_build_file(source_dir,
                         ABORT_IF_FAIL,
                         processed_source_dirs,
                         blade)

        if target_id not in target_database:
            console.error_exit('%s: target //%s:%s does not exists' % (
                _find_depender(target_id, blade), source_dir, target_name))

        related_targets[target_id] = target_database[target_id]
        for key in related_targets[target_id].expanded_deps:
            if key not in related_targets:
                cited_targets.add(key)

    # Iterating to get svn root dirs
    for path, name in related_targets:
        root_dir = path.split('/')[0].strip()
        if root_dir not in blade.svn_root_dirs and '#' not in root_dir:
            blade.svn_root_dirs.append(root_dir)

    return direct_targets, all_command_targets, related_targets


def find_blade_root_dir(working_dir):
    """find_blade_root_dir to find the dir holds the BLADE_ROOT file.

    The blade_root_dir is the directory which is the closest upper level
    directory of the current working directory, and containing a file
    named BLADE_ROOT.

    """
    blade_root_dir = working_dir
    if blade_root_dir.endswith('/'):
        blade_root_dir = blade_root_dir[:-1]
    while blade_root_dir and blade_root_dir != '/':
        if os.path.isfile(os.path.join(blade_root_dir, 'BLADE_ROOT')):
            break
        blade_root_dir = os.path.dirname(blade_root_dir)
    if not blade_root_dir or blade_root_dir == '/':
        console.error_exit(
                "Can't find the file 'BLADE_ROOT' in this or any upper directory.\n"
                "Blade need this file as a placeholder to locate the root source directory "
                "(aka the directory where you #include start from).\n"
                "You should create it manually at the first time.")
    return blade_root_dir

########NEW FILE########
__FILENAME__ = proto_library_target
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Feng Chen <phongchen@tencent.com>


"""Define proto_library target
"""


import os
import blade

import console
import configparse
import build_rules
from blade_util import var_to_list
from cc_targets import CcTarget


class ProtoLibrary(CcTarget):
    """A scons proto library target subclass.

    This class is derived from SconsCcTarget.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 optimize,
                 deprecated,
                 blade,
                 kwargs):
        """Init method.

        Init the proto target.

        """
        srcs_list = var_to_list(srcs)
        self._check_proto_srcs_name(srcs_list)
        CcTarget.__init__(self,
                          name,
                          'proto_library',
                          srcs,
                          deps,
                          '',
                          [], [], [], optimize, [], [],
                          blade,
                          kwargs)

        proto_config = configparse.blade_config.get_config('proto_library_config')
        protobuf_lib = var_to_list(proto_config['protobuf_libs'])

        # Hardcode deps rule to thirdparty protobuf lib.
        self._add_hardcode_library(protobuf_lib)

        # Link all the symbols by default
        self.data['link_all_symbols'] = True
        self.data['deprecated'] = deprecated
        self.data['java_sources_explict_dependency'] = []
        self.data['python_vars'] = []
        self.data['python_sources'] = []

    def _check_proto_srcs_name(self, srcs_list):
        """_check_proto_srcs_name.

        Checks whether the proto file's name ends with 'proto'.

        """
        err = 0
        for src in srcs_list:
            base_name = os.path.basename(src)
            pos = base_name.rfind('.')
            if pos == -1:
                err = 1
            file_suffix = base_name[pos + 1:]
            if file_suffix != 'proto':
                err = 1
            if err == 1:
                console.error_exit('invalid proto file name %s' % src)

    def _generate_header_files(self):
        """Whether this target generates header files during building."""
        return True

    def _proto_gen_files(self, path, src):
        """_proto_gen_files. """
        proto_name = src[:-6]
        return (self._target_file_path(path, '%s.pb.cc' % proto_name),
                self._target_file_path(path, '%s.pb.h' % proto_name))

    def _proto_gen_php_file(self, path, src):
        """Generate the php file name. """
        proto_name = src[:-6]
        return self._target_file_path(path, '%s.pb.php' % proto_name)

    def _proto_gen_python_file(self, path, src):
        """Generate the python file name. """
        proto_name = src[:-6]
        return self._target_file_path(path, '%s_pb2.py' % proto_name)

    def _get_java_package_name(self, src):
        """Get the java package name from proto file if it is specified. """
        package_name_java = 'java_package'
        package_name = 'package'
        if not os.path.isfile(src):
            return ''
        package_line = ''
        package = ''
        normal_package_line = ''
        for line in open(src):
            line = line.strip()
            if line.startswith('//'):
                continue
            pos = line.find('//')
            if pos != -1:
                line = line[0:pos]
            if package_name_java in line:
                package_line = line
                break
            if line.startswith(package_name):
                normal_package_line = line

        if package_line:
            package = package_line.split('=')[1].strip().strip(r'\'";')
        elif normal_package_line:
            package = normal_package_line.split(' ')[1].strip().strip(';')

        package = package.replace('.', '/')

        return package

    def _proto_java_gen_file(self, path, src, package):
        """Generate the java files name of the proto library. """
        proto_name = src[:-6]
        base_name = os.path.basename(proto_name)
        base_name = ''.join(base_name.title().split('_'))
        base_name = '%s.java' % base_name
        dir_name = os.path.join(path, package)
        proto_name = os.path.join(dir_name, base_name)
        return os.path.join(self.build_path, proto_name)

    def _proto_java_rules(self):
        """Generate scons rules for the java files from proto file. """
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            package_dir = self._get_java_package_name(src_path)
            proto_java_src_package = self._proto_java_gen_file(self.path,
                                                               src,
                                                               package_dir)

            self._write_rule('%s.ProtoJava(["%s"], "%s")' % (
                    self._env_name(),
                    proto_java_src_package,
                    src_path))

            self.data['java_sources'] = (
                     os.path.dirname(proto_java_src_package),
                     os.path.join(self.build_path, self.path),
                     self.name)
            self.data['java_sources_explict_dependency'].append(proto_java_src_package)

    def _proto_php_rules(self):
        """Generate php files. """
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            proto_php_src = self._proto_gen_php_file(self.path, src)
            self._write_rule('%s.ProtoPhp(["%s"], "%s")' % (
                    self._env_name(),
                    proto_php_src,
                    src_path))

    def _proto_python_rules(self):
        """Generate python files. """
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            proto_python_src = self._proto_gen_python_file(self.path, src)
            py_cmd_var = '%s_python' % self._generate_variable_name(
                    self.path, self.name)
            self._write_rule('%s = %s.ProtoPython(["%s"], "%s")' % (
                    py_cmd_var,
                    self._env_name(),
                    proto_python_src,
                    src_path))
            self.data['python_vars'].append(py_cmd_var)
            self.data['python_sources'].append(proto_python_src)

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        # Build java source according to its option
        env_name = self._env_name()

        self.options = self.blade.get_options()
        self.direct_targets = self.blade.get_direct_targets()

        if (getattr(self.options, 'generate_java', False) or
            self.data.get('generate_java') or
            self.key in self.direct_targets):
            self._proto_java_rules()

        if (getattr(self.options, 'generate_php', False) and
            (self.data.get('generate_php') or
             self.key in self.direct_targets)):
            self._proto_php_rules()

        if (getattr(self.options, 'generate_python', False) or
            self.data.get('generate_python') or
            self.key in self.direct_targets):
            self._proto_python_rules()

        self._setup_cc_flags()

        sources = []
        obj_names = []
        for src in self.srcs:
            (proto_src, proto_hdr) = self._proto_gen_files(self.path, src)

            self._write_rule('%s.Proto(["%s", "%s"], "%s")' % (
                    env_name,
                    proto_src,
                    proto_hdr,
                    os.path.join(self.path, src)))
            obj_name = "%s_object" % self._generate_variable_name(
                self.path, src)
            obj_names.append(obj_name)
            self._write_rule(
                '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                'source="%s")' % (obj_name,
                                    env_name,
                                    proto_src,
                                    proto_src))
            sources.append(proto_src)
        self._write_rule('%s = [%s]' % (self._objs_name(), ','.join(obj_names)))
        self._write_rule('%s.Depends(%s, %s)' % (
                         env_name, self._objs_name(), sources))

        self._cc_library()
        options = self.blade.get_options()
        if (getattr(options, 'generate_dynamic', False) or
            self.data.get('build_dynamic', False)):
            self._dynamic_cc_library()


def proto_library(name,
                  srcs=[],
                  deps=[],
                  optimize=[],
                  deprecated=False,
                  **kwargs):
    """proto_library target. """
    proto_library_target = ProtoLibrary(name,
                                        srcs,
                                        deps,
                                        optimize,
                                        deprecated,
                                        blade.blade,
                                        kwargs)
    blade.blade.register_target(proto_library_target)


build_rules.register_function(proto_library)

########NEW FILE########
__FILENAME__ = py_targets
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is python egg target which generates python egg for user.

"""


import os
import blade

import build_rules
import console

from blade_util import var_to_list
from target import Target


class PythonBinaryTarget(Target):
    """A python egg target subclass.

    This class is derived from SconsTarget and generates python egg package.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 prebuilt,
                 blade,
                 kwargs):
        """Init method. """
        srcs = var_to_list(srcs)
        deps = var_to_list(deps)

        Target.__init__(self,
                        name,
                        'py_binary',
                        srcs,
                        deps,
                        blade,
                        kwargs)

        if prebuilt:
            self.type = 'prebuilt_py_binary'

    def scons_rules(self):
        """scons_rules.

        Description
        -----------
        It outputs the scons rules according to user options.

        """
        self._clone_env()

        if self.type == 'prebuilt_py_binary':
            return

        env_name = self._env_name()

        setup_file = os.path.join(self.path, 'setup.py')
        python_package = os.path.join(self.path, self.name)
        init_file = os.path.join(python_package, '__init__.py')

        binary_files = []
        if os.path.exists(setup_file):
            binary_files.append(setup_file)

        if not os.path.exists(init_file):
            console.error_exit('The __init__.py not existed in %s' % python_package)
        binary_files.append(init_file)

        dep_var_list = []
        self.targets = self.blade.get_build_targets()
        for dep in self.expanded_deps:
            binary_files += targets[dep].data.get('python_sources', [])
            dep_var_list += targets[dep].data.get('python_vars', [])

        target_egg_file = '%s.egg' % self._target_file_path()
        python_binary_var = '%s_python_binary_var' % (
            self._generate_variable_name(self.path, self.name))
        self._write_rule('%s = %s.PythonBinary(["%s"], %s)' % (
                          python_binary_var,
                          env_name,
                          target_egg_file,
                          binary_files))
        for var in dep_var_list:
            self._write_rule('%s.Depends(%s, %s)' % (
                             env_name, python_binary_var, var))


def py_binary(name,
              srcs=[],
              deps=[],
              prebuilt=False,
              **kwargs):
    """python binary - aka, python egg. """
    target = PythonBinaryTarget(name,
                                srcs,
                                deps,
                                prebuilt,
                                blade.blade,
                                kwargs)
    blade.blade.register_target(target)


build_rules.register_function(py_binary)

########NEW FILE########
__FILENAME__ = resource_library_target
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Feng Chen <phongchen@tencent.com>


"""Define resource_library target
"""


import os
import blade

import build_rules
import java_jar_target
import py_targets
from cc_targets import CcTarget


class ResourceLibrary(CcTarget):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget and it is the scons class
    to generate resource library rules.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 optimize,
                 extra_cppflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        CcTarget.__init__(self,
                          name,
                          'resource_library',
                          srcs,
                          deps,
                          '',
                          [],
                          [],
                          [],
                          optimize,
                          extra_cppflags,
                          [],
                          blade,
                          kwargs)

    def _generate_header_files(self):
        """Whether this target generates header files during building."""
        return True

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        env_name = self._env_name()
        (out_dir, res_file_name) = self._resource_library_rules_helper()

        self.data['res_srcs'] = []
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            src_base = os.path.basename(src_path)
            src_base_name = '%s.c' % self._regular_variable_name(src_base)
            new_src_path = os.path.join(out_dir, src_base_name)
            cmd_bld = '%s_bld' % self._regular_variable_name(new_src_path)
            self._write_rule('%s = %s.ResourceFile("%s", "%s")' % (
                         cmd_bld, env_name, new_src_path, src_path))
            self.data['res_srcs'].append(new_src_path)

        self._resource_library_rules_objects()

        self._cc_library()

        options = self.blade.get_options()
        if (getattr(options, 'generate_dynamic', False) or
            self.data.get('build_dynamic')):
            self._dynamic_cc_library()

    def _resource_library_rules_objects(self):
        """Generate resource library object rules.  """
        env_name = self._env_name()
        objs_name = self._objs_name()

        self._setup_cc_flags()

        objs = []
        res_srcs = self.data['res_srcs']
        res_objects = {}
        path = self.path
        for src in res_srcs:
            base_src_name = self._regular_variable_name(os.path.basename(src))
            src_name = base_src_name + '_' + self.name + '_res'
            if src_name not in res_objects:
                res_objects[src_name] = (
                        '%s_%s_object' % (
                                base_src_name,
                                self._regular_variable_name(self.name)))
                target_path = os.path.join(self.build_path,
                                           path,
                                           '%s.objs' % self.name,
                                           base_src_name)
                self._write_rule(
                        '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"]'
                        ', source="%s")' % (res_objects[src_name],
                                              env_name,
                                              target_path,
                                              src))
            objs.append(res_objects[src_name])
        self._write_rule('%s = [%s]' % (objs_name, ','.join(objs)))

    def _resource_library_rules_helper(self):
        """The helper method to generate scons resource rules, mainly applies builder.  """
        env_name = self._env_name()
        out_dir = os.path.join(self.build_path, self.path)
        res_name = self._regular_variable_name(self.name)
        res_file_name = res_name
        res_file_header = res_file_name + '.h'
        res_header_path = os.path.join(out_dir, res_file_header)

        src_list = []
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            src_list.append(src_path)

        cmd_bld = '%s_header_cmd_bld' % res_name
        self._write_rule('%s = %s.ResourceHeader("%s", %s)' % (
                     cmd_bld, env_name, res_header_path, src_list))

        return (out_dir, res_file_name)


def resource_library(name,
                     srcs=[],
                     deps=[],
                     optimize=[],
                     extra_cppflags=[],
                     **kwargs):
    """scons_resource_library. """
    target = ResourceLibrary(name,
                             srcs,
                             deps,
                             optimize,
                             extra_cppflags,
                             blade.blade,
                             kwargs)
    blade.blade.register_target(target)


build_rules.register_function(resource_library)

########NEW FILE########
__FILENAME__ = rules_generator
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng Chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong Peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the scons rules genearator module which invokes all
 the builder objects or scons objects to generate scons rules.

"""


import os
import socket
import subprocess
import string
import time

import configparse
import console

from blade_platform import CcFlagsManager


def _incs_list_to_string(incs):
    """ Convert incs list to string
    ['thirdparty', 'include'] -> -I thirdparty -I include
    """
    return ' '.join(['-I ' + path for path in incs])


class SconsFileHeaderGenerator(object):
    """SconsFileHeaderGenerator class"""
    def __init__(self, options, build_dir, gcc_version,
                 python_inc, cuda_inc, build_environment, svn_roots):
        """Init method. """
        self.rules_buf = []
        self.options = options
        self.build_dir = build_dir
        self.gcc_version = gcc_version
        self.python_inc = python_inc
        self.cuda_inc = cuda_inc
        self.build_environment = build_environment
        self.ccflags_manager = CcFlagsManager(options)
        self.env_list = ['env_with_error', 'env_no_warning']

        self.svn_roots = svn_roots
        self.svn_info_map = {}

        self.version_cpp_compile_template = string.Template("""
env_version = Environment(ENV = os.environ)
env_version.Append(SHCXXCOMSTR = '%s$updateinfo%s' % (colors('cyan'), colors('end')))
env_version.Append(CPPFLAGS = '-m$m')
version_obj = env_version.SharedObject('$filename')
""")
        self.blade_config = configparse.blade_config
        self.distcc_enabled = self.blade_config.get_config(
                              'distcc_config').get('enabled', False)
        self.dccc_enabled = self.blade_config.get_config(
                              'link_config').get('enable_dccc', False)

    def _add_rule(self, rule):
        """Append one rule to buffer. """
        self.rules_buf.append('%s\n' % rule)

    def _append_prefix_to_building_var(
                self,
                prefix='',
                building_var='',
                condition=False):
        """A helper method: append prefix to building var if condition is True."""
        if condition:
            return '%s %s' % (prefix, building_var)
        else:
            return building_var

    def _get_version_info(self):
        """Gets svn root dir info. """
        for root_dir in self.svn_roots:
            lc_all_env = os.environ
            lc_all_env['LC_ALL'] = 'POSIX'
            root_dir_realpath = os.path.realpath(root_dir)
            svn_working_dir = os.path.dirname(root_dir_realpath)
            svn_dir = os.path.basename(root_dir_realpath)

            if not os.path.exists('%s/.svn' % root_dir):
                console.warning('"%s" is not under version control' % root_dir)
                continue

            p = subprocess.Popen('svn info %s' % svn_dir,
                                 env=lc_all_env,
                                 cwd='%s' % svn_working_dir,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
            std_out, std_err = p.communicate()
            if p.returncode:
                console.warning('failed to get version control info in %s' % root_dir)
            else:
                self.svn_info_map[root_dir] = std_out.replace('\n', '\\n\\\n')

    def generate_version_file(self):
        """Generate version information files. """
        self._get_version_info()
        svn_info_len = len(self.svn_info_map)

        if not os.path.exists(self.build_dir):
            os.makedirs(self.build_dir)
        version_cpp = open('%s/version.cpp' % self.build_dir, 'w')

        print >>version_cpp, '/* This file was generated by blade */'
        print >>version_cpp, 'extern "C" {'
        print >>version_cpp, 'namespace binary_version {'
        print >>version_cpp, 'extern const int kSvnInfoCount = %d;' % svn_info_len

        svn_info_array = '{'
        for idx in range(svn_info_len):
            key_with_idx = self.svn_info_map.keys()[idx]
            svn_info_line = '"%s"' % self.svn_info_map[key_with_idx]
            svn_info_array += svn_info_line
            if idx != (svn_info_len - 1):
                svn_info_array += ','
        svn_info_array += '}'

        print >>version_cpp, 'extern const char* const kSvnInfo[%d] = %s;' % (
                svn_info_len, svn_info_array)
        print >>version_cpp, 'extern const char kBuildType[] = "%s";' % self.options.profile
        print >>version_cpp, 'extern const char kBuildTime[] = "%s";' % time.asctime()
        print >>version_cpp, 'extern const char kBuilderName[] = "%s";' % os.getenv('USER')
        print >>version_cpp, (
                'extern const char kHostName[] = "%s";' % socket.gethostname())
        compiler = 'GCC %s' % self.gcc_version
        print >>version_cpp, 'extern const char kCompiler[] = "%s";' % compiler
        print >>version_cpp, '}}'

        version_cpp.close()

        self._add_rule('VariantDir("%s", ".", duplicate=0)' % self.build_dir)
        self._add_rule(self.version_cpp_compile_template.substitute(
            updateinfo='Updating version information',
            m=self.options.m,
            filename='%s/version.cpp' % self.build_dir))

    def generate_imports_functions(self, blade_path):
        """Generates imports and functions. """
        self._add_rule(
            r"""
import sys
sys.path.insert(0, '%s')
""" % blade_path)
        self._add_rule(
            r"""
import os
import subprocess
import signal
import time
import socket
import glob

import blade_util
import console
import scons_helper

from build_environment import ScacheManager
from console import colors
from scons_helper import MakeAction
from scons_helper import create_fast_link_builders
from scons_helper import echospawn
from scons_helper import error_colorize
from scons_helper import generate_python_binary
from scons_helper import generate_resource_file
from scons_helper import generate_resource_header
""")

        if getattr(self.options, 'verbose', False):
            self._add_rule('scons_helper.option_verbose = True')

        self._add_rule((
                """if not os.path.exists('%s'):
    os.mkdir('%s')""") % (self.build_dir, self.build_dir))

    def generate_top_level_env(self):
        """generates top level environment. """
        self._add_rule('os.environ["LC_ALL"] = "C"')
        self._add_rule('top_env = Environment(ENV=os.environ)')

    def generate_compliation_verbose(self):
        """Generates color and verbose message. """
        self._add_rule('top_env.Decider("MD5-timestamp")')
        self._add_rule('console.color_enabled=%s' % console.color_enabled)

        if not getattr(self.options, 'verbose', False):
            self._add_rule('top_env["SPAWN"] = echospawn')

        self._add_rule(
                """
compile_proto_cc_message = '%sCompiling %s$SOURCE%s to cc source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_proto_java_message = '%sCompiling %s$SOURCE%s to java source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_proto_php_message = '%sCompiling %s$SOURCE%s to php source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_proto_python_message = '%sCompiling %s$SOURCE%s to python source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_thrift_cc_message = '%sCompiling %s$SOURCE%s to cc source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_thrift_java_message = '%sCompiling %s$SOURCE%s to java source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_thrift_python_message = '%sCompiling %s$SOURCE%s to python source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_resource_header_message = '%sGenerating resource header %s$TARGET%s%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_resource_message = '%sCompiling %s$SOURCE%s as resource file%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_source_message = '%sCompiling %s$SOURCE%s%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

assembling_source_message = '%sAssembling %s$SOURCE%s%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

link_program_message = '%sLinking Program %s$TARGET%s%s' % \
    (colors('green'), colors('purple'), colors('green'), colors('end'))

link_library_message = '%sCreating Static Library %s$TARGET%s%s' % \
    (colors('green'), colors('purple'), colors('green'), colors('end'))

ranlib_library_message = '%sRanlib Library %s$TARGET%s%s' % \
    (colors('green'), colors('purple'), colors('green'), colors('end')) \

link_shared_library_message = '%sLinking Shared Library %s$TARGET%s%s' % \
    (colors('green'), colors('purple'), colors('green'), colors('end'))

compile_java_jar_message = '%sGenerating java jar %s$TARGET%s%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_python_binary_message = '%sGenerating python binary %s$TARGET%s%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_yacc_message = '%sYacc %s$SOURCE%s to $TARGET%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_swig_python_message = '%sCompiling %s$SOURCE%s to python source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_swig_java_message = '%sCompiling %s$SOURCE%s to java source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))

compile_swig_php_message = '%sCompiling %s$SOURCE%s to php source%s' % \
    (colors('cyan'), colors('purple'), colors('cyan'), colors('end'))
""")

        if not getattr(self.options, 'verbose', False):
            self._add_rule(
                    r"""
top_env.Append(
    CXXCOMSTR = compile_source_message,
    CCCOMSTR = compile_source_message,
    ASCOMSTR = assembling_source_message,
    SHCCCOMSTR = compile_source_message,
    SHCXXCOMSTR = compile_source_message,
    ARCOMSTR = link_library_message,
    RANLIBCOMSTR = ranlib_library_message,
    SHLINKCOMSTR = link_shared_library_message,
    LINKCOMSTR = link_program_message,
    JAVACCOMSTR = compile_source_message
)""")

    def _generate_fast_link_builders(self):
        """Generates fast link builders if it is specified in blade bash. """
        link_config = configparse.blade_config.get_config('link_config')
        enable_dccc = link_config['enable_dccc']
        if link_config['link_on_tmp']:
            if (not enable_dccc) or (
                    enable_dccc and not self.build_environment.dccc_env_prepared):
                self._add_rule('create_fast_link_builders(top_env)')

    def generate_builders(self):
        """Generates common builders. """
        # Generates builders specified in blade bash at first
        self._generate_fast_link_builders()

        proto_config = configparse.blade_config.get_config('proto_library_config')
        protoc_bin = proto_config['protoc']
        protobuf_path = proto_config['protobuf_path']

        protobuf_incs_str = _incs_list_to_string(proto_config['protobuf_incs'])
        protobuf_php_path = proto_config['protobuf_php_path']
        protoc_php_plugin = proto_config['protoc_php_plugin']
        # Genreates common builders now
        builder_list = []
        self._add_rule('time_value = Value("%s")' % time.asctime())
        self._add_rule(
            'proto_bld = Builder(action = MakeAction("%s --proto_path=. -I. %s'
            ' -I=`dirname $SOURCE` --cpp_out=%s $SOURCE", '
            'compile_proto_cc_message))' % (
                    protoc_bin, protobuf_incs_str, self.build_dir))
        builder_list.append('BUILDERS = {"Proto" : proto_bld}')

        self._add_rule(
            'proto_java_bld = Builder(action = MakeAction("%s --proto_path=. '
            '--proto_path=%s --java_out=%s/`dirname $SOURCE` $SOURCE", '
            'compile_proto_java_message))' % (
                    protoc_bin, protobuf_path, self.build_dir))
        builder_list.append('BUILDERS = {"ProtoJava" : proto_java_bld}')

        self._add_rule(
            'proto_php_bld = Builder(action = MakeAction("%s '
            '--proto_path=. --plugin=protoc-gen-php=%s '
            '-I. %s -I%s -I=`dirname $SOURCE` '
            '--php_out=%s/`dirname $SOURCE` '
            '$SOURCE", compile_proto_php_message))' % (
                    protoc_bin, protoc_php_plugin, protobuf_incs_str,
                    protobuf_php_path, self.build_dir))
        builder_list.append('BUILDERS = {"ProtoPhp" : proto_php_bld}')

        self._add_rule(
            'proto_python_bld = Builder(action = MakeAction("%s '
            '--proto_path=. '
            '-I. %s -I=`dirname $SOURCE` '
            '--python_out=%s '
            '$SOURCE", compile_proto_python_message))' % (
                    protoc_bin, protobuf_incs_str, self.build_dir))
        builder_list.append('BUILDERS = {"ProtoPython" : proto_python_bld}')

        # Generate thrift library builders.
        thrift_config = configparse.blade_config.get_config('thrift_config')
        thrift_incs_str = _incs_list_to_string(thrift_config['thrift_incs'])
        thrift_bin = thrift_config['thrift']
        if thrift_bin.startswith('//'):
            thrift_bin = thrift_bin.replace('//', self.build_dir + '/')
            thrift_bin = thrift_bin.replace(':', '/')

        # Genreates common builders now
        self._add_rule(
            'thrift_bld = Builder(action = MakeAction("%s '
            '--gen cpp:include_prefix,pure_enums -I . %s -I `dirname $SOURCE` '
            '-out %s/`dirname $SOURCE` $SOURCE", compile_thrift_cc_message))' % (
                    thrift_bin, thrift_incs_str, self.build_dir))
        builder_list.append('BUILDERS = {"Thrift" : thrift_bld}')

        self._add_rule(
            'thrift_java_bld = Builder(action = MakeAction("%s '
            '--gen java -I . %s -I `dirname $SOURCE` -out %s/`dirname $SOURCE` '
            '$SOURCE", compile_thrift_java_message))' % (
                    thrift_bin, thrift_incs_str, self.build_dir))
        builder_list.append('BUILDERS = {"ThriftJava" : thrift_java_bld}')

        self._add_rule(
            'thrift_python_bld = Builder(action = MakeAction("%s '
            '--gen py -I . %s -I `dirname $SOURCE` -out %s/`dirname $SOURCE` '
            '$SOURCE", compile_thrift_python_message))' % (
                    thrift_bin, thrift_incs_str, self.build_dir))
        builder_list.append('BUILDERS = {"ThriftPython" : thrift_python_bld}')

        self._add_rule(
                     r"""
blade_jar_bld = Builder(action = MakeAction('jar cf $TARGET -C `dirname $SOURCE` .',
    compile_java_jar_message))

yacc_bld = Builder(action = MakeAction('bison $YACCFLAGS -d -o $TARGET $SOURCE',
    compile_yacc_message))

resource_header_bld = Builder(action = MakeAction(generate_resource_header,
    compile_resource_header_message))

resource_file_bld = Builder(action = MakeAction(generate_resource_file,
    compile_resource_message))

python_binary_bld = Builder(action = MakeAction(generate_python_binary,
    compile_python_binary_message))
""")
        builder_list.append('BUILDERS = {"BladeJar" : blade_jar_bld}')
        builder_list.append('BUILDERS = {"Yacc" : yacc_bld}')
        builder_list.append('BUILDERS = {"ResourceHeader" : resource_header_bld}')
        builder_list.append('BUILDERS = {"ResourceFile" : resource_file_bld}')
        builder_list.append('BUILDERS = {"PythonBinary" : python_binary_bld}')

        for builder in builder_list:
            self._add_rule('top_env.Append(%s)' % builder)

    def generate_compliation_flags(self):
        """Generates compliation flags. """
        toolchain_dir = os.environ.get('TOOLCHAIN_DIR', '')
        if toolchain_dir and not toolchain_dir.endswith('/'):
            toolchain_dir += '/'
        cpp_str = toolchain_dir + os.environ.get('CPP', 'cpp')
        cc_str = toolchain_dir + os.environ.get('CC', 'gcc')
        cxx_str = toolchain_dir + os.environ.get('CXX', 'g++')
        nvcc_str = toolchain_dir + os.environ.get('NVCC', 'nvcc')
        ld_str = toolchain_dir + os.environ.get('LD', 'g++')
        console.info('CPP=%s' % cpp_str)
        console.info('CC=%s' % cc_str)
        console.info('CXX=%s' % cxx_str)
        console.info('NVCC=%s' % nvcc_str)
        console.info('LD=%s' % ld_str)

        self.ccflags_manager.set_cpp_str(cpp_str)

        # To modify CC, CXX, LD according to the building environment and
        # project configuration
        build_with_distcc = (self.distcc_enabled and
                             self.build_environment.distcc_env_prepared)
        cc_str = self._append_prefix_to_building_var(
                         prefix='distcc',
                         building_var=cc_str,
                         condition=build_with_distcc)

        cxx_str = self._append_prefix_to_building_var(
                         prefix='distcc',
                         building_var=cxx_str,
                         condition=build_with_distcc)

        build_with_ccache = self.build_environment.ccache_installed
        cc_str = self._append_prefix_to_building_var(
                         prefix='ccache',
                         building_var=cc_str,
                         condition=build_with_ccache)

        cxx_str = self._append_prefix_to_building_var(
                         prefix='ccache',
                         building_var=cxx_str,
                         condition=build_with_ccache)

        build_with_dccc = (self.dccc_enabled and
                           self.build_environment.dccc_env_prepared)
        ld_str = self._append_prefix_to_building_var(
                        prefix='dccc',
                        building_var=ld_str,
                        condition=build_with_dccc)

        cc_env_str = 'CC="%s", CXX="%s"' % (cc_str, cxx_str)
        ld_env_str = 'LINK="%s"' % ld_str
        nvcc_env_str = 'NVCC="%s"' % nvcc_str

        cc_config = configparse.blade_config.get_config('cc_config')
        extra_incs = cc_config['extra_incs']
        extra_incs_str = ', '.join(['"%s"' % inc for inc in extra_incs])
        if not extra_incs_str:
            extra_incs_str = '""'

        (cppflags_except_warning, linkflags) = self.ccflags_manager.get_flags_except_warning()

        builder_list = []
        cuda_incs_str = ' '.join(['-I%s' % inc for inc in self.cuda_inc])
        self._add_rule(
            'nvcc_object_bld = Builder(action = MakeAction("%s -ccbin g++ %s '
            '$NVCCFLAGS -o $TARGET -c $SOURCE", compile_source_message))' % (
                    nvcc_str, cuda_incs_str))
        builder_list.append('BUILDERS = {"NvccObject" : nvcc_object_bld}')

        self._add_rule(
            'nvcc_binary_bld = Builder(action = MakeAction("%s %s '
            '$NVCCFLAGS -o $TARGET ", link_program_message))' % (
                    nvcc_str, cuda_incs_str))
        builder_list.append('BUILDERS = {"NvccBinary" : nvcc_binary_bld}')

        for builder in builder_list:
            self._add_rule('top_env.Append(%s)' % builder)

        self._add_rule('top_env.Replace(%s, %s, '
                       'CPPPATH=[%s, "%s", "%s"], '
                       'CPPFLAGS=%s, CFLAGS=%s, CXXFLAGS=%s, '
                       '%s, LINKFLAGS=%s)' %
                       (cc_env_str, nvcc_env_str,
                        extra_incs_str, self.build_dir, self.python_inc,
                        cc_config['cppflags'] + cppflags_except_warning,
                        cc_config['cflags'],
                        cc_config['cxxflags'],
                        ld_env_str, linkflags))

        self._setup_cache()

        if build_with_distcc:
            self.build_environment.setup_distcc_env()

        for rule in self.build_environment.get_rules():
            self._add_rule(rule)

        self._setup_warnings()

    def _setup_warnings(self):
        for env in self.env_list:
            self._add_rule('%s = top_env.Clone()' % env)

        (warnings, cxx_warnings, c_warnings) = self.ccflags_manager.get_warning_flags()
        self._add_rule('%s.Append(CPPFLAGS=%s, CFLAGS=%s, CXXFLAGS=%s)' % (
            self.env_list[0],
            warnings, c_warnings, cxx_warnings))

    def _setup_cache(self):
        if self.build_environment.ccache_installed:
            self.build_environment.setup_ccache_env()
        else:
            cache_dir = os.path.expanduser('~/.bladescache')
            cache_size = 4 * 1024 * 1024 * 1024
            if hasattr(self.options, 'cache_dir'):
                if not self.options.cache_dir:
                    return
                cache_dir = self.options.cache_dir
            else:
                console.info('using default cache dir: %s' % cache_dir)

            if hasattr(self.options, 'cache_size') and (self.options.cache_size != -1):
                cache_size = self.options.cache_size

            self._add_rule('CacheDir("%s")' % cache_dir)
            self._add_rule('scache_manager = ScacheManager("%s", cache_limit=%d)' % (
                        cache_dir, cache_size))
            self._add_rule('Progress(scache_manager, interval=100)')

            self._add_rule('console.info("using cache directory %s")' % cache_dir)
            self._add_rule('console.info("scache size %d")' % cache_size)

    def generate(self, blade_path):
        """Generates all rules. """
        self.generate_imports_functions(blade_path)
        self.generate_top_level_env()
        self.generate_compliation_verbose()
        self.generate_version_file()
        self.generate_builders()
        self.generate_compliation_flags()
        return self.rules_buf


class SconsRulesGenerator(object):
    """The main class to generate scons rules and outputs rules to SConstruct. """
    def __init__(self, scons_path, blade_path, blade):
        """Init method. """
        self.scons_path = scons_path
        self.blade_path = blade_path
        self.blade = blade
        self.scons_platform = self.blade.get_scons_platform()

        build_dir = self.blade.get_build_path()
        options = self.blade.get_options()
        gcc_version = self.scons_platform.get_gcc_version()
        python_inc = self.scons_platform.get_python_include()
        cuda_inc = self.scons_platform.get_cuda_include()

        self.scons_file_header_generator = SconsFileHeaderGenerator(
                options,
                build_dir,
                gcc_version,
                python_inc,
                cuda_inc,
                self.blade.build_environment,
                self.blade.svn_root_dirs)
        try:
            os.remove('blade-bin')
        except os.error:
            pass
        os.symlink(os.path.abspath(build_dir), 'blade-bin')

    def generate_scons_script(self):
        """Generates SConstruct script. """
        rules_buf = self.scons_file_header_generator.generate(self.blade_path)
        rules_buf += self.blade.gen_targets_rules()

        # Write to SConstruct
        self.scons_file_fd = open(self.scons_path, 'w')
        self.scons_file_fd.writelines(rules_buf)
        self.scons_file_fd.close()
        return rules_buf

########NEW FILE########
__FILENAME__ = scons_helper
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Huan Yu <huanyu@tencent.com>
#         Feng Chen <phongchen@tencent.com>
#         Yi Wang <yiwang@tencent.com>
#         Chong Peng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the scons rules helper module which should be
 imported by Scons script

"""


import os
import shutil
import signal
import string
import subprocess
import sys
import tempfile

import SCons
import SCons.Action
import SCons.Builder
import SCons.Scanner
import SCons.Scanner.Prog

import console


# option_verbose to indicate print verbose or not
option_verbose = False


# linking tmp dir
linking_tmp_dir = ''


def generate_python_binary(target, source, env):
    setup_file = ''
    if not str(source[0]).endswith('setup.py'):
        console.warning('setup.py not existed to generate target %s, '
                        'blade will generate a default one for you' %
                        str(target[0]))
    else:
        setup_file = str(source[0])
    init_file = ''
    source_index = 2
    if not setup_file:
        source_index = 1
        init_file = str(source[0])
    else:
        init_file = str(source[1])

    init_file_dir = os.path.dirname(init_file)

    dep_source_list = []
    for s in source[source_index:]:
        dep_source_list.append(str(s))

    target_file = str(target[0])
    target_file_dir_list = target_file.split('/')
    target_profile = target_file_dir_list[0]
    target_dir = '/'.join(target_file_dir_list[0:-1])

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if setup_file:
        shutil.copyfile(setup_file, os.path.join(target_dir, 'setup.py'))
    else:
        target_name = os.path.basename(init_file_dir)
        if not target_name:
            console.error_exit('invalid package for target %s' % str(target[0]))
        # generate default setup.py for user
        setup_str = """
#!/usr/bin/env python
# This file was generated by blade

from setuptools import find_packages, setup


setup(
      name='%s',
      version='0.1.0',
      packages=find_packages(),
      zip_safe=True
)
""" % target_name
        default_setup_file = open(os.path.join(target_dir, 'setup.py'), 'w')
        default_setup_file.write(setup_str)
        default_setup_file.close()

    package_dir = os.path.join(target_profile, init_file_dir)
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir, ignore_errors=True)

    cmd = 'cp -r %s %s' % (init_file_dir, target_dir)
    p = subprocess.Popen(
            cmd,
            env={},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
    std_out, std_err = p.communicate()
    if p.returncode:
        console.info(std_out)
        console.info(std_err)
        console.error_exit('failed to copy source files from %s to %s' % (
                   init_file_dir, target_dir))
        return p.returncode

    # copy file to package_dir
    for f in dep_source_list:
        dep_file_basename = os.path.basename(f)
        dep_file_dir = os.path.dirname(f)
        sub_dir = ''
        sub_dir_list = dep_file_dir.split('/')
        if len(sub_dir_list) > 1:
            sub_dir = '/'.join(dep_file_dir.split('/')[1:])
        if sub_dir:
            package_sub_dir = os.path.join(package_dir, sub_dir)
            if not os.path.exists(package_sub_dir):
                os.makedirs(package_sub_dir)
            sub_init_file = os.path.join(package_sub_dir, '__init__.py')
            if not os.path.exists(sub_init_file):
                sub_f = open(sub_init_file, 'w')
                sub_f.close()
            shutil.copyfile(f, os.path.join(package_sub_dir, dep_file_basename))

    make_egg_cmd = 'python setup.py bdist_egg'
    p = subprocess.Popen(
            make_egg_cmd,
            env={},
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
    std_out, std_err = p.communicate()
    if p.returncode:
        console.info(std_out)
        console.info(std_err)
        console.error_exit('failed to generate python binary in %s' % target_dir)
        return p.returncode
    return 0


def generate_resource_header(target, source, env):
    res_header_path = str(target[0])

    if not os.path.exists(os.path.dirname(res_header_path)):
        os.mkdir(os.path.dirname(res_header_path))
    f = open(res_header_path, 'w')

    print >>f, '// This file was automatically generated by blade'
    print >>f, '#ifdef __cplusplus\nextern "C" {\n#endif\n'
    for s in source:
        var_name = str(s)
        for i in [',', '-', '/', '.', '+']:
            var_name = var_name.replace(i, '_')
        print >>f, 'extern const char RESOURCE_%s[%d];' % (var_name, s.get_size())
    print >>f, '\n#ifdef __cplusplus\n}\n#endif\n'
    f.close()


def generate_resource_file(target, source, env):
    src_path = str(source[0])
    new_src_path = str(target[0])
    cmd = 'xxd -i %s | sed "s/unsigned char /const char RESOURCE_/g" > %s' % (
           src_path, new_src_path)
    p = subprocess.Popen(
            cmd,
            env={},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True)
    std_out, std_err = p.communicate()
    if p.returncode:
        console.info(std_out)
        console.info(std_err)
        console.error_exit('failed to generate resource file')
    return p.returncode


def MakeAction(cmd, cmdstr):
    global option_verbose
    if option_verbose:
        return SCons.Action.Action(cmd)
    else:
        return SCons.Action.Action(cmd, cmdstr)


_ERRORS = [': error:', ': fatal error:', ': undefined reference to',
           ': cannot find ', ': ld returned 1 exit status']
_WARNINGS = [': warning:', ': note: ']


def error_colorize(message):
    colored_message = []
    for t in message.splitlines(True):
        color = 'cyan'

        # For clang column indicator, such as '^~~~~~'
        if t.strip().startswith('^'):
            color = 'green'
        else:
            for w in _WARNINGS:
                if w in t:
                    color = 'yellow'
                    break
            for w in _ERRORS:
                if w in t:
                    color = 'red'
                    break

        colored_message.append(console.colors(color))
        colored_message.append(t)
        colored_message.append(console.colors('end'))
    return ''.join(colored_message)


def echospawn(sh, escape, cmd, args, env):
    # convert env from unicode strings
    asciienv = {}
    for key, value in env.iteritems():
        asciienv[key] = str(value)

    cmdline = ' '.join(args)
    p = subprocess.Popen(
        cmdline,
        env=asciienv,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
        universal_newlines=True)
    (stdout, stderr) = p.communicate()

    if p.returncode:
        if p.returncode != -signal.SIGINT:
            # Error
            sys.stdout.write(error_colorize(stdout))
            sys.stderr.write(error_colorize(stderr))
    else:
        if stderr:
            # Only warnings
            sys.stdout.write(error_colorize(stdout))
            sys.stderr.write(error_colorize(stderr))
        else:
            sys.stdout.write(stdout)

    return p.returncode


def _blade_action_postfunc(closing_message):
    """To do post jobs if blade's own actions failed to build. """
    console.info(closing_message)
    # Remember to write the dblite incase of re-linking once fail to
    # build last time. We should elaborate a way to avoid rebuilding
    # after failure of our own builders or actions.
    SCons.SConsign.write()


def _fast_link_helper(target, source, env, link_com):
    """fast link helper function. """
    target_file = str(target[0])
    prefix_str = 'blade_%s' % target_file.replace('/', '_').replace('.', '_')
    fd, temporary_file = tempfile.mkstemp(suffix='xianxian',
                                          prefix=prefix_str,
                                          dir=linking_tmp_dir)
    os.close(fd)

    sources = []
    for s in source:
        sources.append(str(s))

    link_com_str = link_com.substitute(
                   FL_TARGET=temporary_file,
                   FL_SOURCE=' '.join(sources))
    p = subprocess.Popen(
                        link_com_str,
                        env=os.environ,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                        universal_newlines=True)
    std_out, std_err = p.communicate()
    if std_out:
        print std_out
    if std_err:
        print std_err
    if p.returncode == 0:
        shutil.move(temporary_file, target_file)
        if not os.path.exists(target_file):
            console.warning('failed to genreate %s in link on tmpfs mode' % target_file)
    else:
        _blade_action_postfunc('failed while fast linking')
        return p.returncode


def fast_link_sharelib_action(target, source, env):
    # $SHLINK -o $TARGET $SHLINKFLAGS $__RPATH $SOURCES $_LIBDIRFLAGS $_LIBFLAGS
    link_com = string.Template('%s -o $FL_TARGET %s %s $FL_SOURCE %s %s' % (
                env.subst('$SHLINK'),
                env.subst('$SHLINKFLAGS'),
                env.subst('$__RPATH'),
                env.subst('$_LIBDIRFLAGS'),
                env.subst('$_LIBFLAGS')))
    return _fast_link_helper(target, source, env, link_com)


def fast_link_prog_action(target, source, env):
    # $LINK -o $TARGET $LINKFLAGS $__RPATH $SOURCES $_LIBDIRFLAGS $_LIBFLAGS
    link_com = string.Template('%s -o $FL_TARGET %s %s $FL_SOURCE %s %s' % (
                env.subst('$LINK'),
                env.subst('$LINKFLAGS'),
                env.subst('$__RPATH'),
                env.subst('$_LIBDIRFLAGS'),
                env.subst('$_LIBFLAGS')))
    return _fast_link_helper(target, source, env, link_com)


def create_fast_link_prog_builder(env):
    """
       This is the function to create blade fast link
       program builder. It will overwrite the program
       builder of top level env if user specifies an
       option to apply fast link method that they want
       to place the blade output to distributed file
       system to advoid the random read write of linker
       largely degrades building performance.
    """
    new_link_action = MakeAction(fast_link_prog_action, '$LINKCOMSTR')
    program = SCons.Builder.Builder(action=new_link_action,
                                    emitter='$PROGEMITTER',
                                    prefix='$PROGPREFIX',
                                    suffix='$PROGSUFFIX',
                                    src_suffix='$OBJSUFFIX',
                                    src_builder='Object',
                                    target_scanner=SCons.Scanner.Prog.ProgramScanner())
    env['BUILDERS']['Program'] = program


def create_fast_link_sharelib_builder(env):
    """
       This is the function to create blade fast link
       sharelib builder. It will overwrite the sharelib
       builder of top level env if user specifies an
       option to apply fast link method that they want
       to place the blade output to distributed file
       system to advoid the random read write of linker
       largely degrades building performance.
    """
    new_link_actions = []
    new_link_actions.append(SCons.Defaults.SharedCheck)
    new_link_actions.append(MakeAction(fast_link_sharelib_action, '$SHLINKCOMSTR'))

    sharedlib = SCons.Builder.Builder(action=new_link_actions,
                                      emitter='$SHLIBEMITTER',
                                      prefix='$SHLIBPREFIX',
                                      suffix='$SHLIBSUFFIX',
                                      target_scanner=SCons.Scanner.Prog.ProgramScanner(),
                                      src_suffix='$SHOBJSUFFIX',
                                      src_builder='SharedObject')
    env['BUILDERS']['SharedLibrary'] = sharedlib


def create_fast_link_builders(env):
    """Creates fast link builders - Program and  SharedLibrary. """
    # Check requirement
    acquire_temp_place = "df | grep tmpfs | awk '{print $5, $6}'"
    p = subprocess.Popen(
                        acquire_temp_place,
                        env=os.environ,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True,
                        universal_newlines=True)
    std_out, std_err = p.communicate()

    # Do not try to overwrite builder with error
    if p.returncode:
        console.warning('you have link on tmp enabled, but it is not fullfilled to make it.')
        return

    # No tmpfs to do fastlink, will not overwrite the builder
    if not std_out:
        console.warning('you have link on tmp enabled, but there is no tmpfs to make it.')
        return

    # Use the first one
    global linking_tmp_dir
    usage, linking_tmp_dir = tuple(std_out.splitlines(False)[0].split())

    # Do not try to do that if there is no memory space left
    usage = int(usage.replace('%', ''))
    if usage > 90:
        console.warning('you have link on tmp enabled, '
                        'but there is not enough space on %s to make it.' %
                        linking_tmp_dir)
        return

    console.info('building in link on tmpfs mode')

    create_fast_link_sharelib_builder(env)
    create_fast_link_prog_builder(env)

########NEW FILE########
__FILENAME__ = swig_library_target
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Feng Chen <phongchen@tencent.com>


"""Define swig_library target
"""


import os
import blade

import console
import build_rules
import java_jar_target
import py_targets
from cc_targets import CcTarget


class SwigLibrary(CcTarget):
    """A scons cc target subclass.

    This class is derived from SconsCCTarget.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 warning,
                 java_package,
                 java_lib_packed,
                 optimize,
                 extra_swigflags,
                 blade,
                 kwargs):
        """Init method.

        Init the cc target.

        """
        CcTarget.__init__(self,
                          name,
                          'swig_library',
                          srcs,
                          deps,
                          warning,
                          [], [], [], optimize, extra_swigflags, [],
                          blade,
                          kwargs)
        self.data['cpperraswarn'] = warning
        self.data['java_package'] = java_package
        self.data['java_lib_packed'] = java_lib_packed
        self.data['java_dep_var'] = []
        self.data['java_sources_explict_dependency'] = []
        self.data['python_vars'] = []
        self.data['python_sources'] = []

        scons_platform = self.blade.get_scons_platform()
        self.php_inc_list = scons_platform.get_php_include()
        self.options = self.blade.get_options()

    def _pyswig_gen_python_file(self, path, src):
        """Generate swig python file for python. """
        swig_name = src[:-2]
        return os.path.join(self.build_path, path, '%s.py' % swig_name)

    def _pyswig_gen_file(self, path, src):
        """Generate swig cxx files for python. """
        swig_name = src[:-2]
        return os.path.join(self.build_path, path, '%s_pywrap.cxx' % swig_name)

    def _javaswig_gen_file(self, path, src):
        """Generate swig cxx files for java. """
        swig_name = src[:-2]
        return os.path.join(self.build_path, path, '%s_javawrap.cxx' % swig_name)

    def _phpswig_gen_file(self, path, src):
        """Generate swig cxx files for php. """
        swig_name = src[:-2]
        return os.path.join(self.build_path, path, '%s_phpwrap.cxx' % swig_name)

    def _swig_extract_dependency_files(self, src):
        dep = []
        for line in open(src):
            if line.startswith('#include') or line.startswith('%include'):
                line = line.split(' ')[1].strip("""'"\r\n""")
                if not ('<' in line or line in dep):
                    dep.append(line)
        return [i for i in dep if os.path.exists(i)]

    def _swig_library_rules_py(self):
        """_swig_library_rules_py.
        """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path,
                                                self.name,
                                                'dynamic_py')

        obj_names_py = []
        flag_list = []
        warning = self.data.get('cpperraswarn', '')
        flag_list.append(('cpperraswarn', warning))
        pyswig_flags = ''
        for flag in flag_list:
            if flag[0] == 'cpperraswarn':
                if flag[1] == 'yes':
                    pyswig_flags += ' -cpperraswarn'

        builder_name = '%s_bld' % var_name
        builder_alias = '%s_bld_alias' % var_name
        swig_bld_cmd = 'swig -python -threads %s -c++ -I%s -o $TARGET $SOURCE' % (
                pyswig_flags, self.build_path)

        self._write_rule('%s = Builder(action=MakeAction("%s", '
                         'compile_swig_python_message))' % (
                             builder_name, swig_bld_cmd))
        self._write_rule('%s.Append(BUILDERS={"%s" : %s})' % (
                env_name, builder_alias, builder_name))

        self._setup_cc_flags()

        dep_files = []
        dep_files_map = {}
        for src in self.srcs:
            pyswig_src = self._pyswig_gen_file(self.path, src)
            self._write_rule('%s.%s(["%s"], "%s")' % (
                    env_name,
                    builder_alias,
                    pyswig_src,
                    os.path.join(self.path, src)))
            self.data['python_sources'].append(
                    self._pyswig_gen_python_file(self.path, src))
            obj_name_py = '%s_object' % self._generate_variable_name(
                self.path, src, 'python')
            obj_names_py.append(obj_name_py)

            self._write_rule(
                '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                'source="%s")' % (obj_name_py,
                                    env_name,
                                    pyswig_src,
                                    pyswig_src))
            self.data['python_vars'].append(obj_name_py)
            dep_files = self._swig_extract_dependency_files(
                                os.path.join(self.path, src))
            self._write_rule('%s.Depends("%s", %s)' % (
                             env_name,
                             pyswig_src,
                             dep_files))
            dep_files_map[os.path.join(self.path, src)] = dep_files

        objs_name = self._objs_name()
        objs_name_py = '%s_py' % objs_name
        self._write_rule('%s = [%s]' % (objs_name_py, ','.join(obj_names_py)))

        target_path = self._target_file_path()
        target_lib = os.path.basename(target_path)
        if not target_lib.startswith('_'):
            target_lib = '_%s' % target_lib
        target_path_py = os.path.join(os.path.dirname(target_path), target_lib)

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()
        if whole_link_flags:
            self._write_rule(
                    '%s.Append(LINKFLAGS=[%s])' % (env_name, whole_link_flags))

        if self.srcs or self.expanded_deps:
            self._write_rule('%s = %s.SharedLibrary("%s", %s, %s, SHLIBPREFIX = "")'
                    % (var_name,
                       env_name,
                       target_path_py,
                       objs_name_py,
                       lib_str))
            self.data['python_sources'].append('%s.so' % target_path_py)
            self.data['python_vars'].append(var_name)

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                env_name, var_name, ', '.join(link_all_symbols_lib_list)))

        return dep_files_map

    def _swig_library_rules_java(self, dep_files_map):
        """_swig_library_rules_java. """
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path,
                                                self.name,
                                                'dynamic_java')

        # Append -fno-strict-aliasing flag to cxxflags and cppflags
        self._write_rule('%s.Append(CPPFLAGS = ["-fno-strict-aliasing"])' % env_name)
        build_jar = self.data.get('generate_java')

        flag_list = []
        flag_list.append(('cpperraswarn', self.data.get('cpperraswarn', '')))
        flag_list.append(('package', self.data.get('java_package', '')))
        java_lib_packed = self.data.get('java_lib_packed', False)
        flag_list.append(('java_lib_packed', java_lib_packed))
        javaswig_flags = ''
        depend_outdir = False
        out_dir = os.path.join(self.build_path, self.path)
        for flag in flag_list:
            if flag[0] == 'cpperraswarn':
                if flag[1] == 'yes':
                    javaswig_flags += ' -cpperraswarn'
            if flag[0] == 'java_lib_packed':
                if flag[1]:
                    java_lib_packed = True
            if flag[0] == 'package':
                if flag[1]:
                    javaswig_flags += ' -package %s' % flag[1]
                    package_dir = flag[1].replace('.', '/')
                    out_dir = os.path.join(self.build_path,
                                           self.path, package_dir)
                    out_dir_dummy = os.path.join(out_dir, 'dummy_file')
                    javaswig_flags += ' -outdir %s' % out_dir
                    swig_outdir_cmd = '%s_swig_out_cmd_var' % var_name
                    if not os.path.exists(out_dir):
                        depend_outdir = True
                        self._write_rule('%s = %s.Command("%s", "", [Mkdir("%s")])' % (
                                swig_outdir_cmd,
                                env_name,
                                out_dir_dummy,
                                out_dir))
                        self.data['java_dep_var'].append(swig_outdir_cmd)
                    if build_jar:
                        self.data['java_sources'] = (
                                out_dir,
                                os.path.join(self.build_path, self.path),
                                self.name)

        builder_name = '%s_bld' % var_name
        builder_alias = '%s_bld_alias' % var_name
        swig_bld_cmd = 'swig -java %s -c++ -I%s -o $TARGET $SOURCE' % (
                       javaswig_flags, self.build_path)
        self._write_rule('%s = Builder(action=MakeAction("%s", '
                         'compile_swig_java_message))' % (
                             builder_name, swig_bld_cmd))
        self._write_rule('%s.Append(BUILDERS={"%s" : %s})' % (
                env_name, builder_alias, builder_name))
        self._swig_library_rules_java_helper(depend_outdir, build_jar,
                                             java_lib_packed, out_dir,
                                             builder_alias, dep_files_map)

    def _swig_library_rules_java_helper(self,
                                        dep_outdir,
                                        java_build_jar,
                                        lib_packed,
                                        out_dir,
                                        builder_alias,
                                        dep_files_map):
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path,
                                                self.name,
                                                'dynamic_java')
        depend_outdir = dep_outdir
        build_jar = java_build_jar
        java_lib_packed = lib_packed
        env_name = self._env_name()
        out_dir_dummy = os.path.join(out_dir, 'dummy_file')
        obj_names_java = []

        scons_platform = self.blade.get_scons_platform()
        java_includes = scons_platform.get_java_include()
        if java_includes:
            self._write_rule('%s.Append(CPPPATH=%s)' % (env_name, java_includes))

        dep_files = []
        for src in self.srcs:
            javaswig_src = self._javaswig_gen_file(self.path, src)
            src_basename = os.path.basename(src)
            javaswig_var = '%s_%s' % (
                    var_name, self._regular_variable_name(src_basename))
            self._write_rule('%s = %s.%s(["%s"], "%s")' % (
                    javaswig_var,
                    env_name,
                    builder_alias,
                    javaswig_src,
                    os.path.join(self.path, src)))
            self.data['java_sources_explict_dependency'].append(javaswig_src)
            if depend_outdir:
                self._write_rule('%s.Depends(%s, "%s")' % (
                        env_name,
                        javaswig_var,
                        out_dir_dummy))
            self.data['java_dep_var'].append(javaswig_var)

            obj_name_java = '%s_object' % self._generate_variable_name(
                    self.path, src, 'dynamic_java')
            obj_names_java.append(obj_name_java)

            self._write_rule(
                    '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                    'source="%s")' % (
                            obj_name_java,
                            env_name,
                            javaswig_src,
                            javaswig_src))

            dep_key = os.path.join(self.path, src)
            if dep_key in dep_files_map:
                dep_files = dep_files_map[dep_key]
            else:
                dep_files = self._swig_extract_dependency_files(dep_key)
            self._write_rule('%s.Depends("%s", %s)' % (
                             env_name,
                             javaswig_src,
                             dep_files))

        objs_name = self._objs_name()
        objs_name_java = '%s_dynamic_java' % objs_name
        self._write_rule('%s = [%s]' % (objs_name_java,
                                        ','.join(obj_names_java)))

        target_path_java = '%s_java' % self._target_file_path()

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()

        if self.srcs or self.expanded_deps:
            self._write_rule('%s = %s.SharedLibrary("%s", %s, %s)' % (
                    var_name,
                    env_name,
                    target_path_java,
                    objs_name_java,
                    lib_str))

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                env_name, var_name, ', '.join(link_all_symbols_lib_list)))

        if build_jar and java_lib_packed:
            lib_dir = os.path.dirname(target_path_java)
            lib_name = os.path.basename(target_path_java)
            lib_name = 'lib%s.so' % lib_name
            self.data['jar_packing_file'] = (
                    os.path.join(lib_dir, lib_name), self.name)

    def _swig_library_rules_php(self, dep_files_map):
        env_name = self._env_name()
        var_name = self._generate_variable_name(self.path, self.name)
        obj_names_php = []

        flag_list = []
        warning = self.data.get('cpperraswarn', '')
        flag_list.append(('cpperraswarn', warning))
        self.phpswig_flags = ''
        phpswig_flags = ''
        for flag in flag_list:
            if flag[0] == 'cpperraswarn':
                if flag[1] == 'yes':
                    phpswig_flags += ' -cpperraswarn'
        self.phpswig_flags = phpswig_flags

        builder_name = '%s_php_bld' % self._regular_variable_name(self.name)
        builder_alias = '%s_php_bld_alias' % self._regular_variable_name(self.name)
        swig_bld_cmd = 'swig -php %s -c++ -I%s -o $TARGET $SOURCE' % (
                       phpswig_flags, self.build_path)

        self._write_rule('%s = Builder(action=MakeAction("%s", '
                         'compile_swig_php_message))' % (
                             builder_name, swig_bld_cmd))
        self._write_rule('%s.Append(BUILDERS={"%s" : %s})' % (
                          env_name, builder_alias, builder_name))

        if self.php_inc_list:
            self._write_rule('%s.Append(CPPPATH=%s)' % (env_name, self.php_inc_list))

        dep_files = []
        dep_files_map = {}
        for src in self.srcs:
            phpswig_src = self._phpswig_gen_file(self.path, src)
            self._write_rule('%s.%s(["%s"], "%s")' % (
                    env_name,
                    builder_alias,
                    phpswig_src,
                    os.path.join(self.path, src)))
            obj_name_php = '%s_object' % self._generate_variable_name(
                self.path, src, 'php')
            obj_names_php.append(obj_name_php)

            self._write_rule(
                '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                'source="%s")' % (obj_name_php,
                                  env_name,
                                  phpswig_src,
                                  phpswig_src))

            dep_key = os.path.join(self.path, src)
            if dep_key in dep_files_map:
                dep_files = dep_files_map[dep_key]
            else:
                dep_files = self._swig_extract_dependency_files(dep_key)
            self._write_rule('%s.Depends("%s", %s)' % (
                             env_name,
                             phpswig_src,
                             dep_files))

        objs_name = self._objs_name()
        objs_name_php = '%s_php' % objs_name

        self._write_rule('%s = [%s]' % (objs_name_php, ','.join(obj_names_php)))

        target_path = self._target_file_path(self.path, self.name)
        target_lib = os.path.basename(target_path)
        target_path_php = os.path.join(os.path.dirname(target_path), target_lib)

        (link_all_symbols_lib_list,
         lib_str,
         whole_link_flags) = self._get_static_deps_lib_list()

        if self.srcs or self.expanded_deps:
            self._write_rule('%s = %s.SharedLibrary("%s", %s, %s, SHLIBPREFIX="")' % (
                    var_name,
                    env_name,
                    target_path_php,
                    objs_name_php,
                    lib_str))

        if link_all_symbols_lib_list:
            self._write_rule('%s.Depends(%s, [%s])' % (
                env_name, var_name, ', '.join(link_all_symbols_lib_list)))

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        dep_files_map = {}
        dep_files_map = self._swig_library_rules_py()
        if (getattr(self.options, 'generate_java', False) or
            self.data.get('generate_java')):
            self._swig_library_rules_java(dep_files_map)
        if getattr(self.options, 'generate_php', False):
            if not self.php_inc_list:
                console.error_exit('failed to build //%s:%s, please install php modules' % (
                           self.path, self.name))
            else:
                self._swig_library_rules_php(dep_files_map)


def swig_library(name,
                 srcs=[],
                 deps=[],
                 warning='',
                 java_package='',
                 java_lib_packed=False,
                 optimize=[],
                 extra_swigflags=[],
                 **kwargs):
    """swig_library target. """
    target = SwigLibrary(name,
                         srcs,
                         deps,
                         warning,
                         java_package,
                         java_lib_packed,
                         optimize,
                         extra_swigflags,
                         blade.blade,
                         kwargs)
    blade.blade.register_target(target)


build_rules.register_function(swig_library)

########NEW FILE########
__FILENAME__ = target
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the target module which is the super class
 of all of the scons targets.

"""


import os
import string

import console
from blade_util import var_to_list


class Target(object):
    """Abstract target class.

    This class should be derived by subclass like CcLibrary CcBinary
    targets, etc.

    """
    def __init__(self,
                 name,
                 target_type,
                 srcs,
                 deps,
                 blade,
                 kwargs):
        """Init method.

        Init the target.

        """
        self.blade = blade
        self.build_path = self.blade.get_build_path()
        current_source_path = self.blade.get_current_source_path()
        self.target_database = self.blade.get_target_database()

        self.key = (current_source_path, name)
        self.fullname = '%s:%s' % self.key
        self.name = name
        self.path = current_source_path
        self.type = target_type
        self.srcs = srcs
        self.deps = []
        self.expanded_deps = []
        self.data = {}

        self._check_name()
        self._check_kwargs(kwargs)
        self._check_srcs()
        self._check_deps_in_build_file(deps)
        self._init_target_deps(deps)
        self.scons_rule_buf = []
        self.__cached_generate_header_files = None

    def _clone_env(self):
        """Clone target's environment. """
        self._write_rule('%s = top_env.Clone()' % self._env_name())

    def _prepare_to_generate_rule(self):
        """Should be overridden. """
        console.error_exit('_prepare_to_generate_rule should be overridden in subclasses')

    def _check_name(self):
        if '/' in self.name:
            console.error_exit('//%s:%s: Invalid target name, should not contain dir part.' % (
                self.path, self.name))

    def _check_kwargs(self, kwargs):
        if kwargs:
            console.warning('//%s:%s: unrecognized options %s' % (
                    self.path, self.name, kwargs))

    # Keep the relationship of all src -> target.
    # Used by build rules to ensure that a source file occurres in
    # exactly one target(only library target).
    __src_target_map = {}

    def _check_srcs(self):
        """Check source files.
        Description
        -----------
        It will warn if one file belongs to two different targets.

        """
        allow_dup_src_type_list = ['cc_binary', 'cc_test']
        for s in self.srcs:
            if '..' in s or s.startswith('/'):
                raise Exception, (
                    'Invalid source file path: %s. '
                    'can only be relative path, and must in current directory or '
                    'subdirectories') % s

            src_key = os.path.normpath('%s/%s' % (self.path, s))
            src_value = '%s %s:%s' % (
                    self.type, self.path, self.name)
            if src_key in Target.__src_target_map:
                value_existed = Target.__src_target_map[src_key]
                  # May insert multiple time in test because of not unloading module
                if (value_existed != src_value and
                    not (value_existed.split(': ')[0] in allow_dup_src_type_list and
                         self.type in allow_dup_src_type_list)):
                    # Just warn here, not raising exception
                    console.warning('Source file %s belongs to both %s and %s' % (
                            s, Target.__src_target_map[src_key], src_value))
            Target.__src_target_map[src_key] = src_value

    def _add_hardcode_library(self, hardcode_dep_list):
        """Add hardcode dep list to key's deps. """
        for dep in hardcode_dep_list:
            dkey = self._convert_string_to_target_helper(dep)
            if dkey[0] == '#':
                self._add_system_library(dkey, dep)
            if dkey not in self.expanded_deps:
                self.expanded_deps.append(dkey)

    def _add_system_library(self, key, name):
        """Add system library entry to database. """
        if key not in self.target_database:
            lib = SystemLibrary(name, self.blade)
            self.blade.register_target(lib)

    def _init_target_deps(self, deps):
        """Init the target deps.

        Parameters
        -----------
        deps: the deps list in BUILD file.

        Description
        -----------
        Add target into target database and init the deps list.

        """
        for d in deps:
            if d[0] == ':':
                # Depend on library in current directory
                dkey = (os.path.normpath(self.path), d[1:])
            elif d.startswith('//'):
                # Depend on library in remote directory
                if not ':' in d:
                    raise Exception, 'Wrong format in %s:%s' % (
                            self.path, self.name)
                (path, lib) = d[2:].rsplit(':', 1)
                dkey = (os.path.normpath(path), lib)
            elif d.startswith('#'):
                # System libaray, they don't have entry in BUILD so we need
                # to add deps manually.
                dkey = ('#', d[1:])
                self._add_system_library(dkey, d)
            else:
                # Depend on library in relative subdirectory
                if not ':' in d:
                    raise Exception, 'Wrong format in %s:%s' % (
                            self.path, self.name)
                (path, lib) = d.rsplit(':', 1)
                if '..' in path:
                    raise Exception, "Don't use '..' in path"
                dkey = (os.path.normpath('%s/%s' % (
                                          self.path, path)), lib)

            if dkey not in self.expanded_deps:
                self.expanded_deps.append(dkey)

            if dkey not in self.deps:
                self.deps.append(dkey)

    def _check_deps_in_build_file(self, deps):
        """_check_deps_in_build_file.

        Parameters
        -----------
        name: the target's name
        deps: the deps list in BUILD file

        Description
        -----------
        Checks that whether users' build file is consistent with
        blade's rule.

        """
        name = self.name
        for dep in deps:
            if not (dep.startswith(':') or dep.startswith('#') or
                    dep.startswith('//') or dep.startswith('./')):
                console.error_exit('%s/%s: Invalid dep in %s.' % (
                    self.path, name, dep))
            if dep.count(':') > 1:
                console.error_exit('%s/%s: Invalid dep %s, missing \',\' between 2 deps?' %
                            (self.path, name, dep))

    def _check_deprecated_deps(self):
        """check that whether it depends upon deprecated target.

        It should be overridden in subclass.

        """
        pass

    def _regular_variable_name(self, var):
        """_regular_variable_name.

        Parameters
        -----------
        var: the variable to be modified

        Returns
        -----------
        s: the variable modified

        Description
        -----------
        Replace the chars that scons doesn't regconize.

        """
        return var.translate(string.maketrans(',-/.+*', '______'))

    def _generate_variable_name(self, path='', name='', suffix=''):
        """_generate_variable_name.

        Parameters
        -----------
        path: the target's path
        name: the target's name
        suffix: the suffix to be appened to the variable

        Returns
        -----------
        The variable that contains target path, target name and suffix

        Description
        -----------
        Concatinating target path, target name and suffix and returns.

        """
        suffix_str = ''
        if suffix:
            suffix_str = '_suFFix_%s' % suffix
        return 'v_%s_mAgIc_%s%s' % (self._regular_variable_name(path),
                                    self._regular_variable_name(name),
                                    suffix_str)

    def _env_name(self):
        """_env_name.

        Returns
        -----------
        The environment variable

        Description
        -----------
        Concatinating target path, target name to be environment var and returns.

        """
        return 'env_%s' % self._generate_variable_name(self.path,
                                                       self.name)

    def __fill_path_name(self, path, name):
        """fill the path and name to make them not None. """
        if not path:
            path = self.path
        if not name:
            name = self.name
        return path, name

    def _target_file_path(self, path='', name=''):
        """_target_file_path.

        Parameters
        -----------
        path: the target's path
        name: the target's name

        Returns
        -----------
        The target's path below building path

        Description
        -----------
        Concatinating building path, target path and target name to be full
        file path.

        """
        new_path, new_name = self.__fill_path_name(path, name)
        return os.path.join(self.build_path, new_path, new_name)

    def __generate_header_files(self):
        for dkey in self.deps:
            dep = self.target_database[dkey]
            if dep._generate_header_files():
                return True
        return False

    def _generate_header_files(self):
        """Whether this target generates header files during building."""
        if self.__cached_generate_header_files is None:
            self.__cached_generate_header_files = self.__generate_header_files()
        return self.__cached_generate_header_files

    def _write_rule(self, rule):
        """_write_rule.

        Parameters
        -----------
        rule: the rule generated by certain target

        Description
        -----------
        Append the rule to the buffer at first.

        """
        self.scons_rule_buf.append('%s\n' % rule)

    def scons_rules(self):
        """scons_rules.

        This method should be impolemented in subclass.

        """
        console.error_exit('%s: should be subclassing' % self.type)

    def get_rules(self):
        """get_rules.

        Returns
        -----------
        The scons rules buffer

        Description
        -----------
        Returns the buffer.

        """
        return self.scons_rule_buf

    def _convert_string_to_target_helper(self, target_string):
        """
        Converting a string like thirdparty/gtest:gtest to tuple
        (target_path, target_name)
        """
        bad_format = False
        if target_string:
            if target_string.startswith('#'):
                return ('#', target_string[1:])
            elif target_string.find(':') != -1:
                path, name = target_string.split(':')
                path = path.strip()
                if path.startswith('//'):
                    path = path[2:]
                return (path, name.strip())
            else:
                bad_format = True
        else:
            bad_format = True

        if bad_format:
            console.error_exit('invalid target lib format: %s, '
                               'should be #lib_name or lib_path:lib_name' %
                               target_string)


class SystemLibrary(Target):
    def __init__(self, name, blade):
        name = name[1:]
        Target.__init__(self, name, 'system_library', [], [], blade, {})
        self.key = ('#', name)
        self.fullname = '%s:%s' % self.key
        self.path = '#'

########NEW FILE########
__FILENAME__ = test_runner
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Authors: Huan Yu <huanyu@tencent.com>
#          Feng Chen <phongchen@tencent.com>
#          Yi Wang <yiwang@tencent.com>
#          Chong Peng <michaelpeng@tencent.com>
# Date: October 20, 2011


"""
 This is the TestRunner module which executes the test programs.

"""


import os
import sys
import time

import binary_runner
import console

from blade_util import environ_add_path
from blade_util import md5sum
from test_scheduler import TestScheduler


def _get_ignore_set():
    """ """
    ignore_env_vars = [
            # shell variables
            'PWD', 'OLDPWD', 'SHLVL', 'LC_ALL', 'TST_HACK_BASH_SESSION_ID',
            # CI variables
            'BUILD_URL', 'BUILD_TAG', 'SVN_REVISION',
            'BUILD_ID', 'EXECUTOR_NUMBER', 'START_USER',
            'EXECUTOR_NUMBER', 'NODE_NAME', 'NODE_LABELS',
            'IF_PKG', 'BUILD_NUMBER', 'HUDSON_COOKIE',
            # ssh variables
            'SSH_CLIENT', 'SSH2_CLIENT',
            # vim variables
            'VIM', 'MYVIMRC', 'VIMRUNTIME']

    for i in range(30):
        ignore_env_vars.append('SVN_REVISION_%d' % i)

    return frozenset(ignore_env_vars)


env_ignore_set = _get_ignore_set()


def _diff_env(a, b):
    """Return difference of two environments dict"""
    seta = set([(k, a[k]) for k in a])
    setb = set([(k, b[k]) for k in b])
    return (dict(seta - setb), dict(setb - seta))


class TestRunner(binary_runner.BinaryRunner):
    """TestRunner. """
    def __init__(self, targets, options, target_database, direct_targets):
        """Init method. """
        binary_runner.BinaryRunner.__init__(self, targets, options, target_database)
        self.direct_targets = direct_targets
        self.inctest_md5_file = '.blade.test.stamp'
        self.tests_detail_file = './blade_tests_detail'
        self.inctest_run_list = []
        self.last_test_stamp = {}
        self.last_test_stamp['md5'] = {}
        self.test_stamp = {}
        self.test_stamp['md5'] = {}
        self.valid_inctest_time_interval = 86400
        self.tests_run_map = {}
        self.run_all_reason = ''
        self.title_str = '=' * 13
        self.skipped_tests = []
        if not self.options.fulltest:
            if os.path.exists(self.inctest_md5_file):
                try:
                    self.last_test_stamp = eval(open(self.inctest_md5_file).read())
                except (IOError, SyntaxError):
                    console.warning('error loading incremental test history, will run full test')
                    self.run_all_reason = 'NO_HISTORY'

        self.test_stamp['testarg'] = md5sum(str(self.options.args))
        env_keys = os.environ.keys()
        env_keys = list(set(env_keys).difference(env_ignore_set))
        env_keys.sort()
        last_test_stamp = {}
        for env_key in env_keys:
            last_test_stamp[env_key] = os.environ[env_key]
        self.test_stamp['env'] = last_test_stamp
        self.test_stamp['inctest_time'] = time.time()

        if not self.options.fulltest:
            if self.test_stamp['testarg'] != (
                    self.last_test_stamp.get('testarg', None)):
                self.run_all_reason = 'ARGUMENT'
                console.info('all tests will run due to test arguments changed')

            new_env = self.test_stamp['env']
            old_env = self.last_test_stamp.get('env', {})
            if isinstance(old_env, str):  # For old test record
                old_env = {}
            if new_env != old_env:
                self.run_all_reason = 'ENVIRONMENT'
                console.info('all tests will run due to test environments changed:')
                (new, old) = _diff_env(new_env, old_env)
                if new:
                    console.info('new environments: %s' % new)
                if old:
                    console.info('old environments: %s' % old)

            this_time = int(round(self.test_stamp['inctest_time']))
            last_time = int(round(self.last_test_stamp.get('inctest_time', 0)))
            interval = this_time - last_time

            if interval >= self.valid_inctest_time_interval or interval < 0:
                self.run_all_reason = 'STALE'
                console.info('all tests will run due to all passed tests are invalid now')
        else:
            self.run_all_reason = 'FULLTEST'

    def _get_test_target_md5sum(self, target):
        """Get test target md5sum. """
        related_file_list = []
        related_file_data_list = []
        test_file_name = os.path.abspath(self._executable(target))
        if os.path.exists(test_file_name):
            related_file_list.append(test_file_name)

        if target.data['dynamic_link']:
            target_key = (target.path, target.name)
            for dep in self.target_database[target_key].expanded_deps:
                dep_target = self.target_database[dep]
                if 'cc_library' in dep_target.type:
                    lib_name = 'lib%s.so' % dep_target.name
                    lib_path = os.path.join(self.build_dir,
                                            dep_target.path,
                                            lib_name)
                    abs_lib_path = os.path.abspath(lib_path)
                    if os.path.exists(abs_lib_path):
                        related_file_list.append(abs_lib_path)

        for i in target.data['testdata']:
            if isinstance(i, tuple):
                data_target = i[0]
            else:
                data_target = i
            if '..' in data_target:
                continue
            if data_target.startswith('//'):
                data_target = data_target[2:]
                data_target_path = os.path.abspath(data_target)
            else:
                data_target_path = os.path.abspath('%s/%s' % (
                                                   target.path, data_target))
            if os.path.exists(data_target_path):
                related_file_data_list.append(data_target_path)

        related_file_list.sort()
        related_file_data_list.sort()

        test_target_str = ''
        test_target_data_str = ''
        for f in related_file_list:
            mtime = os.path.getmtime(f)
            ctime = os.path.getctime(f)
            test_target_str += str(mtime) + str(ctime)

        for f in related_file_data_list:
            mtime = os.path.getmtime(f)
            ctime = os.path.getctime(f)
            test_target_data_str += str(mtime) + str(ctime)

        return md5sum(test_target_str), md5sum(test_target_data_str)

    def _generate_inctest_run_list(self):
        """Get incremental test run list. """
        for target in self.targets.values():
            if target.type != 'cc_test':
                continue
            target_key = (target.path, target.name)
            test_file_name = os.path.abspath(self._executable(target))
            self.test_stamp['md5'][test_file_name] = self._get_test_target_md5sum(target)
            if self.run_all_reason:
                self.tests_run_map[target_key] = {
                        'runfile': test_file_name,
                        'result': '',
                        'reason': self.run_all_reason,
                        'costtime': 0}
                continue

            if target_key in self.direct_targets:
                self.inctest_run_list.append(target)
                self.tests_run_map[target_key] = {
                        'runfile': test_file_name,
                        'result': '',
                        'reason': 'EXPLICIT',
                        'costtime': 0}
                continue

            old_md5sum = self.last_test_stamp['md5'].get(test_file_name, None)
            new_md5sum = self.test_stamp['md5'][test_file_name]
            if new_md5sum != old_md5sum:
                self.inctest_run_list.append(target)
                reason = ''
                if isinstance(old_md5sum, tuple):
                    if old_md5sum == (0, 0):
                        reason = 'LAST_FAILED'
                    else:
                        if new_md5sum[0] != old_md5sum[0]:
                            reason = 'BINARY'
                        else:
                            reason = 'TESTDATA'
                else:
                    reason = 'STALE'
                self.tests_run_map[target_key] = {
                        'runfile': test_file_name,
                        'result': '',
                        'reason': reason,
                        'costtime': 0}

        # Append old md5sum that not existed into new
        old_keys = set(self.last_test_stamp['md5'].keys())
        new_keys = set(self.test_stamp['md5'].keys())
        diff_keys = old_keys.difference(new_keys)
        for key in list(diff_keys):
            self.test_stamp['md5'][key] = self.last_test_stamp['md5'][key]

    def _check_inctest_md5sum_file(self):
        """check the md5sum file size, remove it when it is too large.
           It is 2G by default.
        """
        if os.path.exists(self.inctest_md5_file):
            if os.path.getsize(self.inctest_md5_file) > 2 * 1024 * 1024 * 1024:
                console.warning('Will remove the md5sum file for incremental '
                                'test for it is oversized')
                os.remove(self.inctest_md5_file)

    def _write_test_history(self):
        """write md5sum to file. """
        f = open(self.inctest_md5_file, 'w')
        print >> f, str(self.test_stamp)
        f.close()
        self._check_inctest_md5sum_file()

    def _write_tests_detail_map(self):
        """write the tests detail map for further use. """
        f = open(self.tests_detail_file, 'w')
        print >> f, str(self.tests_run_map)
        f.close()

    def _show_tests_detail(self):
        """show the tests detail after scheduling them. """
        sort_buf = []
        for key in self.tests_run_map:
            costtime = self.tests_run_map.get(key, {}).get('costtime', 0)
            sort_buf.append((key, costtime))
        sort_buf.sort(key=lambda x: x[1])

        if self.tests_run_map:
            console.info('%s Testing detail %s' % (self.title_str, self.title_str))
        for key, costtime in sort_buf:
            reason = self.tests_run_map.get(key, {}).get('reason', 'UNKNOWN')
            result = self.tests_run_map.get(key, {}).get('result',
                                                         'INTERRUPTED')
            if 'SIG' in result:
                result = 'with %s' % result
            console.info('%s:%s triggered by %s, exit(%s), cost %.2f s' % (
                         key[0], key[1], reason, result, costtime), prefix=False)

    def _finish_tests(self):
        """finish some work before return from runner. """
        self._write_test_history()
        if self.options.show_details:
            self._write_tests_detail_map()
            if not self.run_all_reason:
                self._show_skipped_tests_detail()
                self._show_skipped_tests_summary()
            self._show_tests_detail()
        elif not self.run_all_reason:
            self._show_skipped_tests_summary()

    def _show_skipped_tests_detail(self):
        """show tests skipped. """
        if not self.skipped_tests:
            return
        self.skipped_tests.sort()
        console.info('skipped tests')
        for target_key in self.skipped_tests:
            print '%s:%s' % (target_key[0], target_key[1])

    def _show_skipped_tests_summary(self):
        """show tests skipped summary. """
        console.info('%d tests skipped when doing incremental test' % len(self.skipped_tests))
        console.info('to run all tests, please specify --full-test argument')

    def run(self):
        """Run all the cc_test target programs. """
        failed_targets = []
        self._generate_inctest_run_list()
        tests_run_list = []
        for target in self.targets.values():
            if target.type != 'cc_test':
                continue
            if (not self.run_all_reason) and target not in self.inctest_run_list:
                if not target.data.get('always_run'):
                    self.skipped_tests.append((target.path, target.name))
                    continue
            self._prepare_env(target)
            cmd = [os.path.abspath(self._executable(target))]
            cmd += self.options.args

            sys.stdout.flush()  # make sure output before scons if redirected

            test_env = dict(os.environ)
            environ_add_path(test_env, 'LD_LIBRARY_PATH', self._runfiles_dir(target))
            if console.color_enabled:
                test_env['GTEST_COLOR'] = 'yes'
            else:
                test_env['GTEST_COLOR'] = 'no'
            test_env['GTEST_OUTPUT'] = 'xml'
            test_env['HEAPCHECK'] = target.data.get('heap_check', '')
            tests_run_list.append((target,
                                   self._runfiles_dir(target),
                                   test_env,
                                   cmd))
        concurrent_jobs = 0
        concurrent_jobs = self.options.test_jobs
        scheduler = TestScheduler(tests_run_list,
                                  concurrent_jobs,
                                  self.tests_run_map)
        scheduler.schedule_jobs()

        self._clean_env()
        console.info('%s Testing Summary %s' % (self.title_str, self.title_str))
        console.info('Run %d test targets' % scheduler.num_of_run_tests)

        failed_targets = scheduler.failed_targets
        if failed_targets:
            console.error('%d tests failed:' % len(failed_targets))
            for target in failed_targets:
                print '%s:%s, exit code: %s' % (
                    target.path, target.name, target.data['test_exit_code'])
                test_file_name = os.path.abspath(self._executable(target))
                # Do not skip failed test by default
                if test_file_name in self.test_stamp['md5']:
                    self.test_stamp['md5'][test_file_name] = (0, 0)
            console.info('%d tests passed' % (
                scheduler.num_of_run_tests - len(failed_targets)))
            self._finish_tests()
            return 1
        else:
            console.info('All tests passed!')
            self._finish_tests()
            return 0

########NEW FILE########
__FILENAME__ = test_scheduler
# Copyright (c) 2012 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   February 29, 2012


"""
 This is a thread module for blade which is used to spawn
 threads to finish some kind of work.

"""


import Queue
import subprocess
import sys
import threading
import time
import traceback

import blade_util
import console


signal_map = {-1: 'SIGHUP', -2: 'SIGINT', -3: 'SIGQUIT',
              -4: 'SIGILL', -5: 'SIGTRAP', -6: 'SIGABRT',
              -7: 'SIGBUS', -8: 'SIGFPE', -9: 'SIGKILL',
              -10: 'SIGUSR1', -11: 'SIGSEGV', -12: 'SIGUSR2',
              -13: 'SIGPIPE', -14: 'SIGALRM', -15: 'SIGTERM',
              -17: 'SIGCHLD', -18: 'SIGCONT', -19: 'SIGSTOP',
              -20: 'SIGTSTP', -21: 'SIGTTIN', -22: 'SIGTTOU',
              -23: 'SIGURG', -24: 'SIGXCPU', -25: 'SIGXFSZ',
              -26: 'SIGVTALRM', -27: 'SIGPROF', -28: 'SIGWINCH',
              -29: 'SIGIO', -30: 'SIGPWR', -31: 'SIGSYS'}


class WorkerThread(threading.Thread):
    def __init__(self, worker_args, proc_func, args):
        """Init methods for this thread. """
        threading.Thread.__init__(self)
        self.worker_args = worker_args
        self.func_args = args
        self.job_handler = proc_func
        self.thread_id = int(self.worker_args)
        self.start_working_time = time.time()
        self.end_working_time = None
        self.ret = None
        console.info('blade test executor %d starts to work' % self.thread_id)

    def __process(self):
        """Private handler to handle one job. """
        console.info('blade worker %d starts to process' % self.thread_id)
        console.info('blade worker %d finish' % self.thread_id)
        return

    def get_return(self):
        """returns worker result to caller. """
        return self.ret

    def run(self):
        """executes and runs here. """
        try:
            if self.job_handler:
                self.ret = self.job_handler(*self.func_args)
                self.end_working_time = time.time()
                return True
            else:
                self.__process()
                return True
        except:
            (ErrorType, ErrorValue, ErrorTB) = sys.exc_info()
            print sys.exc_info()
            traceback.print_exc(ErrorTB)


class TestScheduler(object):
    """TestScheduler. """
    def __init__(self, tests_list, jobs, tests_run_map):
        """init method. """
        self.tests_list = tests_list
        self.jobs = jobs
        self.tests_run_map = tests_run_map
        self.tests_run_map_lock = threading.Lock()
        self.worker_threads = []
        self.cpu_core_num = blade_util.cpu_count()
        self.num_of_tests = len(self.tests_list)
        self.max_worker_threads = 16
        self.threads = []
        self.tests_stdout_map = {}
        self.failed_targets = []
        self.failed_targets_lock = threading.Lock()
        self.tests_stdout_lock = threading.Lock()
        self.num_of_run_tests = 0
        self.num_of_run_tests_lock = threading.Lock()
        self.job_queue = Queue.Queue(0)
        self.exclusive_job_queue = Queue.Queue(0)

    def __get_workers_num(self):
        """get the number of thread workers. """
        max_workers = max([self.cpu_core_num, self.max_worker_threads])
        if max_workers == 0:
            max_workers = self.max_worker_threads

        if self.jobs <= 1:
            return 1
        elif self.jobs > max_workers:
            self.jobs = max_workers

        if self.num_of_tests <= self.jobs:
            return self.num_of_tests
        else:
            return self.jobs

        return 1

    def __get_result(self, returncode):
        """translate result from returncode. """
        result = 'SUCCESS'
        if returncode:
            result = signal_map.get(returncode, 'FAILED')
            result = '%s:%s' % (result, returncode)
        return result

    def _run_job_redirect(self, job):
        """run job, redirect the output. """
        (target, run_dir, test_env, cmd) = job
        test_name = '%s:%s' % (target.path, target.name)

        console.info('Running %s' % cmd)
        p = subprocess.Popen(cmd,
                             env=test_env,
                             cwd=run_dir,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             close_fds=True)

        (stdoutdata, stderrdata) = p.communicate()
        result = self.__get_result(p.returncode)
        console.info('Output of %s:\n%s\n%s finished: %s\n' % (test_name,
                stdoutdata, test_name, result))

        return p.returncode

    def _run_job(self, job):
        """run job, do not redirect the output. """
        (target, run_dir, test_env, cmd) = job
        console.info('Running %s' % cmd)
        p = subprocess.Popen(cmd, env=test_env, cwd=run_dir, close_fds=True)
        p.wait()
        result = self.__get_result(p.returncode)
        console.info('%s/%s finished : %s\n' % (
             target.path, target.name, result))

        return p.returncode

    def _process_command(self, job_queue, redirect):
        """process routine.

        Each test is a tuple (target, run_dir, env, cmd)

        """
        while not job_queue.empty():
            job = job_queue.get()
            target = job[0]
            target_key = '%s:%s' % (target.path, target.name)
            start_time = time.time()

            try:
                if redirect:
                    returncode = self._run_job_redirect(job)
                else:
                    returncode = self._run_job(job)
            except OSError, e:
                console.error('%s: Create test process error: %s' %
                              (target_key, str(e)))
                returncode = 255

            costtime = time.time() - start_time

            if returncode:
                target.data['test_exit_code'] = returncode
                self.failed_targets_lock.acquire()
                self.failed_targets.append(target)
                self.failed_targets_lock.release()

            self.tests_run_map_lock.acquire()
            run_item_map = self.tests_run_map.get(target.key, {})
            if run_item_map:
                run_item_map['result'] = self.__get_result(returncode)
                run_item_map['costtime'] = costtime
            self.tests_run_map_lock.release()

            self.num_of_run_tests_lock.acquire()
            self.num_of_run_tests += 1
            self.num_of_run_tests_lock.release()
        return True

    def print_summary(self):
        """print the summary output of tests. """
        console.info('There are %d tests scheduled to run by scheduler' % (len(self.tests_list)))

    def _join_thread(self, t):
        """Join thread and keep signal awareable"""
        # The Thread.join without timeout will block signals, which makes
        # blade can't be terminated by Ctrl-C
        while t.isAlive():
            t.join(1)

    def schedule_jobs(self):
        """scheduler. """
        if self.num_of_tests <= 0:
            return True

        num_of_workers = self.__get_workers_num()
        console.info('spawn %d worker(s) to run tests' % num_of_workers)

        for i in self.tests_list:
            target = i[0]
            if target.data.get('exclusive'):
                self.exclusive_job_queue.put(i)
            else:
                self.job_queue.put(i)

        test_arg = [self.job_queue, num_of_workers > 1]
        for i in range(num_of_workers):
            t = WorkerThread((i), self._process_command, args=test_arg)
            t.start()
            self.threads.append(t)
        for t in self.threads:
            self._join_thread(t)

        if not self.exclusive_job_queue.empty():
            console.info('spawn 1 worker to run exclusive tests')
            test_arg = [self.exclusive_job_queue, False]
            last_t = WorkerThread((num_of_workers), self._process_command, args=test_arg)
            last_t.start()
            self._join_thread(last_t)

        self.print_summary()
        return True

########NEW FILE########
__FILENAME__ = thrift_helper
# Copyright (c) 2012 iQIYI Inc.
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Jingxu Chen <chenjingxu@qiyi.com>
#         Feng Chen <chen3feng@gmail.com>
# Date:   October 13, 2012


"""
 A helper class to get the files generated from thrift IDL files.

"""


import os
import re

import console


class ThriftHelper(object):
    def __init__(self, path):
        self.path = path
        if not os.path.isfile(path):
            console.error_exit('%s is not a valid file.' % path)

        self.thrift_name = os.path.basename(path)[0:-7]

        # Package name for each language.
        self.package_name = {}
        # Set to true if there is at least one const definition in the
        # thrift file.
        self.has_constants = False
        self.enums = []
        self.structs = []
        self.exceptions = []
        self.services = []

        # Parse the thrift IDL file.
        self._parse_file()

    def _parse_file(self):
        for line in open(self.path):
            line = line.strip()
            if line.startswith('//') or line.startswith('#'):
                continue
            pos = line.find('//')
            if pos != -1:
                line = line[0:pos]
            pos = line.find('#')
            if pos != -1:
                line = line[0:pos]

            matched = re.match('^namespace ([0-9_a-zA-Z]+) ([0-9_a-zA-Z.]+)', line)
            if matched:
                lang, package = matched.groups()
                self.package_name[lang] = package
                continue

            matched = re.match('(const|struct|service|enum|exception) ([0-9_a-zA-Z]+)', line)
            if not matched:
                continue

            kw, name = matched.groups()
            if kw == 'const':
                self.has_constants = True
            elif kw == 'struct':
                self.structs.append(name)
            elif kw == 'service':
                self.services.append(name)
            elif kw == 'enum':
                self.enums.append(name)
            elif kw == 'exception':
                self.exceptions.append(name)

        if self.has_constants or self.structs or self.enums or \
           self.exceptions or self.services:
            return
        else:
            console.error_exit('%s is an empty thrift file.' % self.path)

    def get_generated_cpp_files(self):
        files = ['%s_constants.cpp' % self.thrift_name,
                 '%s_constants.h' % self.thrift_name,
                 '%s_types.cpp' % self.thrift_name,
                 '%s_types.h' % self.thrift_name]
        for service in self.services:
            files.append('%s.cpp' % service)
            files.append('%s.h' % service)

        return files

    def get_generated_java_files(self):
        java_package = ''
        if 'java' in self.package_name:
            java_package = self.package_name['java']
        base_path = os.path.join(*java_package.split('.'))

        files = []
        if self.has_constants:
            files.append('Constants.java')

        for enum in self.enums:
            files.append('%s.java' % enum)

        for struct in self.structs:
            files.append('%s.java' % struct)

        for exception in self.exceptions:
            files.append('%s.java' % exception)

        for service in self.services:
            files.append('%s.java' % service)

        files = [os.path.join(base_path, f) for f in files]
        return files

    def get_generated_py_files(self):
        py_package = self.thrift_name
        if 'py' in self.package_name:
            py_package = self.package_name['py']
        base_path = os.path.join(*py_package.split('.'))

        files = ['constants.py', 'ttypes.py']
        for service in self.services:
            files.append('%s.py' % service)

        files = [os.path.join(base_path, f) for f in files]
        return files

########NEW FILE########
__FILENAME__ = thrift_library
# Copyright (c) 2012 iQIYI Inc.
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: Jingxu Chen <chenjingxu@qiyi.com>
#         Feng Chen <chen3feng@gmail.com>
# Date:   October 13, 2012


"""
 A helper class to get the files generated from thrift IDL files.

"""


import os

import blade
import configparse
import console

import build_rules
import java_jar_target
import py_targets

from blade_util import var_to_list
from cc_targets import CcTarget
from thrift_helper import ThriftHelper


class ThriftLibrary(CcTarget):
    """A scons thrift library target subclass.

    This class is derived from CcTarget.

    """
    def __init__(self,
                 name,
                 srcs,
                 deps,
                 optimize,
                 deprecated,
                 blade,
                 kwargs):
        """Init method.

        Init the thrift target.

        """
        srcs = var_to_list(srcs)
        self._check_thrift_srcs_name(srcs)
        CcTarget.__init__(self,
                          name,
                          'thrift_library',
                          srcs,
                          deps,
                          '',
                          [], [], [], optimize, [], [],
                          blade,
                          kwargs)
        self.data['python_vars'] = []
        self.data['python_sources'] = []

        thrift_config = configparse.blade_config.get_config('thrift_config')
        thrift_lib = var_to_list(thrift_config['thrift_libs'])
        thrift_bin = thrift_config['thrift']
        if thrift_bin.startswith("//"):
            dkey = self._convert_string_to_target_helper(thrift_bin)
            if dkey not in self.expanded_deps:
                self.expanded_deps.append(dkey)
            if dkey not in self.deps:
                self.deps.append(dkey)


        # Hardcode deps rule to thrift libraries.
        self._add_hardcode_library(thrift_lib)

        # Link all the symbols by default
        self.data['link_all_symbols'] = True
        self.data['deprecated'] = deprecated
        self.data['java_sources_explict_dependency'] = []

        # For each thrift file initialize a ThriftHelper, which will be used
        # to get the source files generated from thrift file.
        self.thrift_helpers = {}
        for src in srcs:
            self.thrift_helpers[src] = ThriftHelper(
                    os.path.join(self.path, src))

    def _check_thrift_srcs_name(self, srcs):
        """_check_thrift_srcs_name.

        Checks whether the thrift file's name ends with 'thrift'.

        """
        error = 0
        for src in srcs:
            base_name = os.path.basename(src)
            pos = base_name.rfind('.')
            if pos == -1:
                console.error('invalid thrift file name %s' % src)
                error += 1
            file_suffix = base_name[pos + 1:]
            if file_suffix != 'thrift':
                console.error('invalid thrift file name %s' % src)
                error += 1
        if error > 0:
            console.error_exit('invalid thrift file names found.')

    def _generate_header_files(self):
        """Whether this target generates header files during building."""
        return True

    def _thrift_gen_cpp_files(self, path, src):
        """_thrift_gen_cpp_files.

        Get the c++ files generated from thrift file.

        """

        return [self._target_file_path(path, f)
                for f in self.thrift_helpers[src].get_generated_cpp_files()]

    def _thrift_gen_py_files(self, path, src):
        """_thrift_gen_py_files.

        Get the python files generated from thrift file.

        """

        return [self._target_file_path(path, f)
                for f in self.thrift_helpers[src].get_generated_py_files()]

    def _thrift_gen_java_files(self, path, src):
        """_thrift_gen_java_files.

        Get the java files generated from thrift file.

        """

        return [self._target_file_path(path, f)
                for f in self.thrift_helpers[src].get_generated_java_files()]

    def _thrift_java_rules(self):
        """_thrift_java_rules.

        Generate scons rules for the java files from thrift file.

        """

        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            thrift_java_src_files = self._thrift_gen_java_files(self.path,
                                                                src)

            self._write_rule('%s.ThriftJava(%s, "%s")' % (
                    self._env_name(),
                    str(thrift_java_src_files),
                    src_path))

            self.data['java_sources'] = (
                     os.path.dirname(thrift_java_src_files[0]),
                     os.path.join(self.build_path, self.path),
                     self.name)

            self.data['java_sources_explict_dependency'] += thrift_java_src_files

    def _thrift_python_rules(self):
        """_thrift_python_rules.

        Generate python files.

        """
        for src in self.srcs:
            src_path = os.path.join(self.path, src)
            thrift_py_src_files = self._thrift_gen_py_files(self.path, src)
            py_cmd_var = '%s_python' % self._generate_variable_name(
                    self.path, self.name)
            self._write_rule('%s = %s.ThriftPython(%s, "%s")' % (
                    py_cmd_var,
                    self._env_name(),
                    str(thrift_py_src_files),
                    src_path))
            self.data['python_vars'].append(py_cmd_var)
            self.data['python_sources'] += thrift_py_src_files

    def scons_rules(self):
        """scons_rules.

        It outputs the scons rules according to user options.

        """
        self._prepare_to_generate_rule()

        # Build java source according to its option
        env_name = self._env_name()

        self.options = self.blade.get_options()
        self.direct_targets = self.blade.get_direct_targets()

        if (getattr(self.options, 'generate_java', False) or
            self.data.get('generate_java') or
            self.key in self.direct_targets):
            self._thrift_java_rules()

        if (getattr(self.options, 'generate_python', False) or
            self.data.get('generate_python') or
            self.key in self.direct_targets):
            self._thrift_python_rules()

        self._setup_cc_flags()

        sources = []
        obj_names = []
        for src in self.srcs:
            thrift_cpp_files = self._thrift_gen_cpp_files(self.path, src)
            thrift_cpp_src_files = [f for f in thrift_cpp_files if f.endswith('.cpp')]

            self._write_rule('%s.Thrift(%s, "%s")' % (
                    env_name,
                    str(thrift_cpp_files),
                    os.path.join(self.path, src)))

            for thrift_cpp_src in thrift_cpp_src_files:
                obj_name = '%s_object' % self._generate_variable_name(
                    self.path, thrift_cpp_src)
                obj_names.append(obj_name)
                self._write_rule(
                    '%s = %s.SharedObject(target="%s" + top_env["OBJSUFFIX"], '
                    'source="%s")' % (obj_name,
                                      env_name,
                                      thrift_cpp_src,
                                      thrift_cpp_src))
                sources.append(thrift_cpp_src)

        self._write_rule('%s = [%s]' % (self._objs_name(), ','.join(obj_names)))
        self._write_rule('%s.Depends(%s, %s)' % (
                         env_name, self._objs_name(), sources))

        self._cc_library()
        options = self.blade.get_options()
        if (getattr(options, 'generate_dynamic', False) or
            self.data.get('build_dynamic')):
            self._dynamic_cc_library()


def thrift_library(name,
                   srcs=[],
                   deps=[],
                   optimize=[],
                   deprecated=False,
                   **kwargs):
    """thrift_library target. """
    thrift_library_target = ThriftLibrary(name,
                                          srcs,
                                          deps,
                                          optimize,
                                          deprecated,
                                          blade.blade,
                                          kwargs)
    blade.blade.register_target(thrift_library_target)


build_rules.register_function(thrift_library)

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python


"""About main entry

Main entry is placed to __main__.py, cause we need to pack
the python sources to a zip ball and invoke the blade through
command line in this way: python blade.zip

"""


import sys
from blade_main import main


if __name__ == '__main__':
    main(sys.argv[0])

########NEW FILE########
__FILENAME__ = blade_main_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the main test module for all targets.

"""


import os
import sys
import unittest

sys.path.append('..')
from cc_binary_test import TestCcBinary
from cc_library_test import TestCcLibrary
from cc_plugin_test import TestCcPlugin
from cc_test_test import TestCcTest
from gen_rule_test import TestGenRule
from java_jar_test import TestJavaJar
from lex_yacc_test import TestLexYacc
from load_builds_test import TestLoadBuilds
from proto_library_test import TestProtoLibrary
from prebuild_cc_library_test import TestPrebuildCcLibrary
from query_target_test import TestQuery
from resource_library_test import TestResourceLibrary
from swig_library_test import TestSwigLibrary
from target_dependency_test import TestDepsAnalyzing

from html_test_runner import HTMLTestRunner
from test_target_test import TestTestRunner


def _main():
    """main method. """
    suite_test = unittest.TestSuite()
    suite_test.addTests([
        unittest.defaultTestLoader.loadTestsFromTestCase(TestCcLibrary),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestCcBinary),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestCcPlugin),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestCcTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestGenRule),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestJavaJar),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLexYacc),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestLoadBuilds),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestProtoLibrary),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestResourceLibrary),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestSwigLibrary),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestDepsAnalyzing),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestQuery),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestTestRunner),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestPrebuildCcLibrary)
        ])

    generate_html = len(sys.argv) > 1 and sys.argv[1].startswith('html')
    if generate_html:
        runner = HTMLTestRunner(title='Blade unit test report')
        runner.run(suite_test)
    else:
        runner = unittest.TextTestRunner()
        runner.run(suite_test)

if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = blade_test
# Copyright (c) 2013 Tencent Inc.
# All rights reserved.
#
# Author: CHEN Feng <phongchen@tencent.com>
# Date:   October 20, 2011

"""
 This is the main test module for all targets.
"""

import os
import subprocess
import sys
import unittest

sys.path.append('..')
import blade.blade
import blade.configparse
from blade.blade import Blade
from blade.configparse import BladeConfig
from blade.argparse import Namespace


class TargetTest(unittest.TestCase):
    """base class Test """
    def doSetUp(self, path, target='...', full_targets=None,
                command='build', generate_php=True, **kwargs):
        """setup method. """
        self.command = 'build'
        if full_targets:
            self.targets = full_targets
        else:
            self.targets = ['%s/%s' % (path, target)]
        self.target_path = path
        self.cur_dir = os.getcwd()
        os.chdir('./testdata')
        self.blade_path = '../../blade'
        self.working_dir = '.'
        self.current_building_path = 'build64_release'
        self.current_source_dir = '.'
        options = {
                'm': '64',
                'profile': 'release',
                'generate_dynamic': True,
                'generate_java': True,
                'generate_php': generate_php,
                'verbose': True
                }
        options.update(kwargs)
        self.options = Namespace(**options)
        self.direct_targets = []
        self.all_command_targets = []
        self.related_targets = {}

        # Init global configuration manager
        blade.configparse.blade_config = BladeConfig(self.current_source_dir)
        blade.configparse.blade_config.parse()

        blade.blade.blade = Blade(self.targets,
                                  self.blade_path,
                                  self.working_dir,
                                  self.current_building_path,
                                  self.current_source_dir,
                                  self.options,
                                  self.command)
        self.blade = blade.blade.blade
        (self.direct_targets,
         self.all_command_targets) = self.blade.load_targets()
        self.blade.analyze_targets()
        self.all_targets = self.blade.get_build_targets()
        self.scons_output_file = 'scons_output.txt'

    def tearDown(self):
        """tear down method. """
        try:
            os.remove('./SConstruct')
            os.remove(self.scons_output_file)
        except OSError:
            pass

        os.chdir(self.cur_dir)

    def testLoadBuildsNotNone(self):
        """Test direct targets and all command targets are not none. """
        self.assertEqual(self.direct_targets, [])
        self.assertTrue(self.all_command_targets)

    def dryRun(self):
        # We can use pipe to capture stdout, but keep the output file make it
        # easy debugging.
        p = subprocess.Popen('scons --dry-run > %s' % self.scons_output_file,
                             shell=True)
        try:
            p.wait()
            self.scons_output = open(self.scons_output_file)
            return p.returncode == 0
        except:
            print >>sys.stderr, 'Failed while dry running:\n%s' % sys.exc_info()
        return False

    def _assertCxxCommonFlags(self, cmdline):
        self.assertTrue('-g' in cmdline)
        self.assertTrue('-fPIC' in cmdline, cmdline)

    def _assertCxxWarningFlags(self, cmdline):
        self.assertTrue('-Wall -Wextra' in cmdline)
        self.assertTrue('-Wframe-larger-than=69632' in cmdline)
        self.assertTrue('-Werror=overloaded-virtual' in cmdline)

    def _assertCxxNoWarningFlags(self, cmdline):
        self.assertTrue('-Wall -Wextra' not in cmdline)
        self.assertTrue('-Wframe-larger-than=69632' not in cmdline)
        self.assertTrue('-Werror=overloaded-virtual' not in cmdline)

    def assertCxxFlags(self, cmdline):
        self._assertCxxCommonFlags(cmdline)
        self._assertCxxWarningFlags(cmdline)

    def assertNoWarningCxxFlags(self, cmdline):
        self._assertCxxCommonFlags(cmdline)
        self._assertCxxNoWarningFlags(cmdline)

    def assertLinkFlags(self, cmdline):
        self.assertTrue('-static-libgcc -static-libstdc++' in cmdline)

    def assertStaticLinkFlags(self, cmdline):
        self.assertTrue('-shared' not in cmdline)

    def assertDynamicLinkFlags(self, cmdline):
        self.assertTrue('-shared' in cmdline)


def run(class_name):
    suite_test = unittest.TestSuite()
    suite_test.addTests(
            [unittest.defaultTestLoader.loadTestsFromTestCase(class_name)])
    runner = unittest.TextTestRunner()
    runner.run(suite_test)

########NEW FILE########
__FILENAME__ = cc_binary_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for cc_binary target.

"""


import blade_test


class TestCcBinary(blade_test.TargetTest):
    """Test cc_binary """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_cc_binary')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        cc_library_string = (self.target_path, 'string_main_prog')

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(cc_library_string in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''
        com_string_line = ''
        string_main_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'string_main.cpp.o -c' in line:
                com_string_line = line
            if 'string_main_prog' in line:
                string_main_depends_libs = line

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)
        self.assertCxxFlags(com_string_line)

        self.assertLinkFlags(string_main_depends_libs)
        self.assertTrue('liblowercase.a' in string_main_depends_libs)
        self.assertTrue('libuppercase.a' in string_main_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestCcBinary)

########NEW FILE########
__FILENAME__ = cc_library_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for cc_library target.

"""


import blade_test


class TestCcLibrary(blade_test.TargetTest):
    """Test cc_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_cc_library')

    def testGenerateRules(self):
        """Test that rules are generated correctly.

        Scons can use the rules for dry running.

        """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        cc_library_string = (self.target_path, 'blade_string')

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(cc_library_string in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''
        com_string_line = ''
        string_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'blade_string.cpp.o -c' in line:
                com_string_line = line
            if 'libblade_string.so' in line:
                string_depends_libs = line

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)
        self.assertNoWarningCxxFlags(com_string_line)
        self.assertTrue('-DNDEBUG -D_FILE_OFFSET_BITS=64' in com_string_line)
        self.assertTrue('-DBLADE_STR_DEF -O2' in com_string_line)
        self.assertTrue('-w' in com_string_line)
        self.assertTrue('-m64' in com_string_line)

        self.assertDynamicLinkFlags(string_depends_libs)

        self.assertTrue('liblowercase.so' in string_depends_libs)
        self.assertTrue('libuppercase.so' in string_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestCcLibrary)

########NEW FILE########
__FILENAME__ = cc_plugin_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for cc_plugin target.

"""


import blade_test


class TestCcPlugin(blade_test.TargetTest):
    """Test cc_plugin """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_cc_plugin')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        cc_library_string = (self.target_path, 'string_plugin')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(cc_library_string in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''
        com_string_line = ''
        string_main_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'string_plugin.cpp.o -c' in line:
                com_string_line = line
            if 'libstring_plugin.so' in line:
                string_plugin_depends_libs = line

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)
        self.assertCxxFlags(com_string_line)

        self.assertDynamicLinkFlags(string_plugin_depends_libs)
        self.assertTrue('-Wl,-Bsymbolic' in string_plugin_depends_libs)
        self.assertTrue('liblowercase.a' in string_plugin_depends_libs)
        self.assertTrue('libuppercase.a' in string_plugin_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestCcPlugin)

########NEW FILE########
__FILENAME__ = cc_test_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for cc_test target.

"""


import blade_test


class TestCcTest(blade_test.TargetTest):
    """Test cc_test """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_cc_test')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        cc_library_string = (self.target_path, 'string_test_main')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(cc_library_string in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''
        com_string_line = ''
        string_main_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'string_test.cpp.o -c' in line:
                com_string_line = line
            if 'string_test_main' in line:
                string_main_depends_libs = line

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)
        self.assertCxxFlags(com_string_line)

        self.assertLinkFlags(string_main_depends_libs)
        self.assertTrue('liblowercase.a' in string_main_depends_libs)
        self.assertTrue('libuppercase.a' in string_main_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestCcTest)

########NEW FILE########
__FILENAME__ = gen_rule_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for cc_gen_rule target.

"""


import blade_test


class TestGenRule(blade_test.TargetTest):
    """Test gen_rule """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_gen_rule')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        gen_rule = (self.target_path, 'process_media')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(gen_rule in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''

        lower_so_index = 0
        gen_rule_index = 0
        upper_so_index = 0
        index = 0

        for line in self.scons_output:
            index += 1
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'echo' in line:
                gen_rule_index = index
            if 'liblowercase.so -m64' in line:
                lower_so_index = index
            if 'libuppercase.so -m64' in line:
                upper_so_index = index

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)

        self.assertTrue(gen_rule_index > lower_so_index)
        self.assertTrue(upper_so_index, gen_rule_index)


if __name__ == '__main__':
    blade_test.run(TestGenRule)

########NEW FILE########
__FILENAME__ = html_test_runner
"""

 Copyright (c) 2011 Tencent Inc.
 All rights reserved.

 Author: Michaelpeng <michaelpeng@tencent.com>
 Date:   October 20, 2011

 A TestRunner for use with the Python unit testing framework. It
 generates a HTML report to show the result at a glance.

----------------------------------

The simplest way to use this is to invoke its main method. E.g.

    import unittest
    import HTMLTestRunner

    ... define your tests ...

    if __name__ == '__main__':
        HTMLTestRunner.main()


For more customization options, instantiates a HTMLTestRunner object.
HTMLTestRunner is a counterpart to unittest's TextTestRunner. E.g.

    # output to a file
    fp = file('my_report.html', 'wb')
    runner = HTMLTestRunner.HTMLTestRunner(
                stream=fp,
                title='My unit test',
                description='This demonstrates the report output by HTMLTestRunner.'
                )

    # Use an external stylesheet.
    # See the Template_mixin class for more customizable options
    runner.STYLESHEET_TMPL = '<link rel="stylesheet" href="my_stylesheet.css" type="text/css">'

    # run the test
    runner.run(my_test_suite)
"""

__version__ = "0.1"


import datetime
import StringIO
import sys
import time
import unittest
from xml.sax import saxutils


# ------------------------------------------------------------------------
# The redirectors below are used to capture output during testing. Output
# sent to sys.stdout and sys.stderr are automatically captured. However
# in some cases sys.stdout is already cached before HTMLTestRunner is
# invoked (e.g. calling logging.basicConfig). In order to capture those
# output, use the redirectors for the cached stream.
#
# e.g.
#   >>> logging.basicConfig(stream=HTMLTestRunner.stdout_redirector)
#   >>>

class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """
    def __init__(self, fp):
        self.fp = fp

    def write(self, s):
        self.fp.write(s)

    def writelines(self, lines):
        self.fp.writelines(lines)

    def flush(self):
        self.fp.flush()

stdout_redirector = OutputRedirector(sys.stdout)
stderr_redirector = OutputRedirector(sys.stderr)



# ----------------------------------------------------------------------
# Template

class Template_mixin(object):
    """
    Define a HTML template for report customerization and generation.

    Overall structure of an HTML report

    HTML
    +------------------------+
    |<html>                  |
    |  <head>                |
    |                        |
    |   STYLESHEET           |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |  </head>               |
    |                        |
    |  <body>                |
    |                        |
    |   HEADING              |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |   REPORT               |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |   ENDING               |
    |   +----------------+   |
    |   |                |   |
    |   +----------------+   |
    |                        |
    |  </body>               |
    |</html>                 |
    +------------------------+
    """

    STATUS = {
    0: 'pass',
    1: 'fail',
    2: 'error',
    }

    DEFAULT_TITLE = 'Unit Test Report'
    DEFAULT_DESCRIPTION = ''

    # ------------------------------------------------------------------------
    # HTML Template

    HTML_TMPL = r"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>%(title)s</title>
    <meta name="generator" content="%(generator)s"/>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    %(stylesheet)s
</head>
<body>
<script language="javascript" type="text/javascript"><!--
output_list = Array();

/* level - 0:Summary; 1:Failed; 2:All */
function showCase(level) {
    trs = document.getElementsByTagName("tr");
    for (var i = 0; i < trs.length; i++) {
        tr = trs[i];
        id = tr.id;
        if (id.substr(0,2) == 'ft') {
            if (level < 1) {
                tr.className = 'hiddenRow';
            }
            else {
                tr.className = '';
            }
        }
        if (id.substr(0,2) == 'pt') {
            if (level > 1) {
                tr.className = '';
            }
            else {
                tr.className = 'hiddenRow';
            }
        }
    }
}


function showClassDetail(cid, count) {
    var id_list = Array(count);
    var toHide = 1;
    for (var i = 0; i < count; i++) {
        tid0 = 't' + cid.substr(1) + '.' + (i+1);
        tid = 'f' + tid0;
        tr = document.getElementById(tid);
        if (!tr) {
            tid = 'p' + tid0;
            tr = document.getElementById(tid);
        }
        id_list[i] = tid;
        if (tr.className) {
            toHide = 0;
        }
    }
    for (var i = 0; i < count; i++) {
        tid = id_list[i];
        if (toHide) {
            document.getElementById('div_'+tid).style.display = 'none'
            document.getElementById(tid).className = 'hiddenRow';
        }
        else {
            document.getElementById(tid).className = '';
        }
    }
}


function showTestDetail(div_id){
    var details_div = document.getElementById(div_id)
    var displayState = details_div.style.display
    // alert(displayState)
    if (displayState != 'block' ) {
        displayState = 'block'
        details_div.style.display = 'block'
    }
    else {
        details_div.style.display = 'none'
    }
}


function html_escape(s) {
    s = s.replace(/&/g,'&amp;');
    s = s.replace(/</g,'&lt;');
    s = s.replace(/>/g,'&gt;');
    return s;
}

/* obsoleted by detail in <div>
function showOutput(id, name) {
    var w = window.open("", //url
                    name,
                    "resizable,scrollbars,status,width=800,height=450");
    d = w.document;
    d.write("<pre>");
    d.write(html_escape(output_list[id]));
    d.write("\n");
    d.write("<a href='javascript:window.close()'>close</a>\n");
    d.write("</pre>\n");
    d.close();
}
*/
--></script>

%(heading)s
%(report)s
%(ending)s

</body>
</html>
"""
    # variables: (title, generator, stylesheet, heading, report, ending)


    # ------------------------------------------------------------------------
    # Stylesheet
    #
    # alternatively use a <link> for external style sheet, e.g.
    #   <link rel="stylesheet" href="$url" type="text/css">

    STYLESHEET_TMPL = """
<style type="text/css" media="screen">
body        { font-family: verdana, arial, helvetica, sans-serif; font-size: 80%; }
table       { font-size: 100%; }
pre         { }

/* -- heading ---------------------------------------------------------------------- */
h1 {
    font-size: 16pt;
    color: gray;
}
.heading {
    margin-top: 0ex;
    margin-bottom: 1ex;
}

.heading .attribute {
    margin-top: 1ex;
    margin-bottom: 0;
}

.heading .description {
    margin-top: 4ex;
    margin-bottom: 6ex;
}

/* -- css div popup ------------------------------------------------------------------------ */
a.popup_link {
}

a.popup_link:hover {
    color: red;
}

.popup_window {
    display: none;
    position: relative;
    left: 0px;
    top: 0px;
    /*border: solid #627173 1px; */
    padding: 10px;
    background-color: #E6E6D6;
    font-family: "Lucida Console", "Courier New", Courier, monospace;
    text-align: left;
    font-size: 8pt;
    width: 500px;
}

}
/* -- report ------------------------------------------------------------------------ */
#show_detail_line {
    margin-top: 3ex;
    margin-bottom: 1ex;
}
#result_table {
    width: 80%;
    border-collapse: collapse;
    border: 1px solid #777;
}
#header_row {
    font-weight: bold;
    color: white;
    background-color: #777;
}
#result_table td {
    border: 1px solid #777;
    padding: 2px;
}
#total_row  { font-weight: bold; }
.passClass  { background-color: #6c6; }
.failClass  { background-color: #c60; }
.errorClass { background-color: #c00; }
.passCase   { color: #6c6; }
.failCase   { color: #c60; font-weight: bold; }
.errorCase  { color: #c00; font-weight: bold; }
.hiddenRow  { display: none; }
.testcase   { margin-left: 2em; }


/* -- ending ---------------------------------------------------------------------- */
#ending {
}

</style>
"""



    # ------------------------------------------------------------------------
    # Heading
    #

    HEADING_TMPL = """<div class='heading'>
<h1>%(title)s</h1>
%(parameters)s
<p class='description'>%(description)s</p>
</div>

""" # variables: (title, parameters, description)

    HEADING_ATTRIBUTE_TMPL = """<p class='attribute'><strong>%(name)s:</strong> %(value)s</p>
""" # variables: (name, value)



    # ------------------------------------------------------------------------
    # Report
    #

    REPORT_TMPL = """
<p id='show_detail_line'>Show
<a href='javascript:showCase(0)'>Summary</a>
<a href='javascript:showCase(1)'>Failed</a>
<a href='javascript:showCase(2)'>All</a>
</p>
<table id='result_table'>
<colgroup>
<col align='left' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
</colgroup>
<tr id='header_row'>
    <td>Test Group/Test case</td>
    <td>Count</td>
    <td>Pass</td>
    <td>Fail</td>
    <td>Error</td>
    <td>View</td>
</tr>
%(test_list)s
<tr id='total_row'>
    <td>Total</td>
    <td>%(count)s</td>
    <td>%(Pass)s</td>
    <td>%(fail)s</td>
    <td>%(error)s</td>
    <td>&nbsp;</td>
</tr>
</table>
""" # variables: (test_list, count, Pass, fail, error)

    REPORT_CLASS_TMPL = r"""
<tr class='%(style)s'>
    <td>%(desc)s</td>
    <td>%(count)s</td>
    <td>%(Pass)s</td>
    <td>%(fail)s</td>
    <td>%(error)s</td>
    <td><a href="javascript:showClassDetail('%(cid)s',%(count)s)">Detail</a></td>
</tr>
""" # variables: (style, desc, count, Pass, fail, error, cid)


    REPORT_TEST_WITH_OUTPUT_TMPL = r"""
<tr id='%(tid)s' class='%(Class)s'>
    <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
    <td colspan='5' align='center'>

    <!--css div popup start-->
    <a class="popup_link" onfocus='this.blur();' href="javascript:showTestDetail('div_%(tid)s')" >
        %(status)s</a>

    <div id='div_%(tid)s' class="popup_window">
        <div style='text-align: right; color:red;cursor:pointer'>
        <a onfocus='this.blur();' onclick="document.getElementById('div_%(tid)s').style.display = 'none' " >
           [x]</a>
        </div>
        <pre>
        %(script)s
        </pre>
    </div>
    <!--css div popup end-->

    </td>
</tr>
""" # variables: (tid, Class, style, desc, status)


    REPORT_TEST_NO_OUTPUT_TMPL = r"""
<tr id='%(tid)s' class='%(Class)s'>
    <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
    <td colspan='5' align='center'>%(status)s</td>
</tr>
""" # variables: (tid, Class, style, desc, status)


    REPORT_TEST_OUTPUT_TMPL = r"""
%(id)s: %(output)s
""" # variables: (id, output)



    # ------------------------------------------------------------------------
    # ENDING
    #

    ENDING_TMPL = """<div id='ending'>&nbsp;</div>"""

# -------------------- The end of the Template class -------------------


TestResult = unittest.TestResult

class _TestResult(TestResult):
    # note: _TestResult is a pure representation of results.
    # It lacks the output and reporting ability compares to unittest._TextTestResult.

    def __init__(self, verbosity=1):
        TestResult.__init__(self)
        self.stdout0 = None
        self.stderr0 = None
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.verbosity = verbosity

        # result is a list of result in 4 tuple
        # (
        #   result code (0: success; 1: fail; 2: error),
        #   TestCase object,
        #   Test output (byte string),
        #   stack trace,
        # )
        self.result = []


    def startTest(self, test):
        TestResult.startTest(self, test)
        # just one buffer for both stdout and stderr
        self.outputBuffer = StringIO.StringIO()
        stdout_redirector.fp = self.outputBuffer
        stderr_redirector.fp = self.outputBuffer
        self.stdout0 = sys.stdout
        self.stderr0 = sys.stderr
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector


    def complete_output(self):
        """
        Disconnect output redirection and return buffer.
        Safe to call multiple times.
        """
        if self.stdout0:
            sys.stdout = self.stdout0
            sys.stderr = self.stderr0
            self.stdout0 = None
            self.stderr0 = None
        return self.outputBuffer.getvalue()


    def stopTest(self, test):
        # Usually one of addSuccess, addError or addFailure would have been called.
        # But there are some path in unittest that would bypass this.
        # We must disconnect stdout in stopTest(), which is guaranteed to be called.
        self.complete_output()


    def addSuccess(self, test):
        self.success_count += 1
        TestResult.addSuccess(self, test)
        output = self.complete_output()
        self.result.append((0, test, output, ''))
        if self.verbosity > 1:
            sys.stderr.write('ok ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('.')

    def addError(self, test, err):
        self.error_count += 1
        TestResult.addError(self, test, err)
        _, _exc_str = self.errors[-1]
        output = self.complete_output()
        self.result.append((2, test, output, _exc_str))
        if self.verbosity > 1:
            sys.stderr.write('E  ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('E')

    def addFailure(self, test, err):
        self.failure_count += 1
        TestResult.addFailure(self, test, err)
        _, _exc_str = self.failures[-1]
        output = self.complete_output()
        self.result.append((1, test, output, _exc_str))
        if self.verbosity > 1:
            sys.stderr.write('F  ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('F')


class HTMLTestRunner(Template_mixin):
    """
    """
    def __init__(self, stream=sys.stdout, verbosity=1, title=None, description=None):
        self.stream = stream
        self.verbosity = verbosity
        if title is None:
            self.title = self.DEFAULT_TITLE
        else:
            self.title = title
        if description is None:
            self.description = self.DEFAULT_DESCRIPTION
        else:
            self.description = description

        self.startTime = datetime.datetime.now()


    def run(self, test):
        "Run the given test case or test suite."
        result = _TestResult(self.verbosity)
        test(result)
        self.stopTime = datetime.datetime.now()
        self.generateReport(test, result)
        print >>sys.stderr, '\nTime Elapsed: %s' % (self.stopTime-self.startTime)
        return result


    def sortResult(self, result_list):
        # unittest does not seems to run in any particular order.
        # Here at least we want to group them together by class.
        rmap = {}
        classes = []
        for n,t,o,e in result_list:
            cls = t.__class__
            if not rmap.has_key(cls):
                rmap[cls] = []
                classes.append(cls)
            rmap[cls].append((n,t,o,e))
        r = [(cls, rmap[cls]) for cls in classes]
        return r


    def getReportAttributes(self, result):
        """
        Return report attributes as a list of (name, value).
        Override this to add custom attributes.
        """
        startTime = str(self.startTime)[:19]
        duration = str(self.stopTime - self.startTime)
        status = []
        if result.success_count: status.append('Pass %s'    % result.success_count)
        if result.failure_count: status.append('Failure %s' % result.failure_count)
        if result.error_count:   status.append('Error %s'   % result.error_count  )
        if status:
            status = ' '.join(status)
        else:
            status = 'none'
        return [
            ('Start Time', startTime),
            ('Duration', duration),
            ('Status', status),
        ]


    def generateReport(self, test, result):
        report_attrs = self.getReportAttributes(result)
        generator = 'HTMLTestRunner %s' % __version__
        stylesheet = self._generate_stylesheet()
        heading = self._generate_heading(report_attrs)
        report = self._generate_report(result)
        ending = self._generate_ending()
        output = self.HTML_TMPL % dict(
            title = saxutils.escape(self.title),
            generator = generator,
            stylesheet = stylesheet,
            heading = heading,
            report = report,
            ending = ending,
        )
        self.stream.write(output.encode('utf8'))


    def _generate_stylesheet(self):
        return self.STYLESHEET_TMPL


    def _generate_heading(self, report_attrs):
        a_lines = []
        for name, value in report_attrs:
            line = self.HEADING_ATTRIBUTE_TMPL % dict(
                    name = saxutils.escape(name),
                    value = saxutils.escape(value),
                )
            a_lines.append(line)
        heading = self.HEADING_TMPL % dict(
            title = saxutils.escape(self.title),
            parameters = ''.join(a_lines),
            description = saxutils.escape(self.description),
        )
        return heading


    def _generate_report(self, result):
        rows = []
        sortedResult = self.sortResult(result.result)
        for cid, (cls, cls_results) in enumerate(sortedResult):
            # subtotal for a class
            np = nf = ne = 0
            for n,t,o,e in cls_results:
                if n == 0: np += 1
                elif n == 1: nf += 1
                else: ne += 1

            # format class description
            if cls.__module__ == "__main__":
                name = cls.__name__
            else:
                name = "%s.%s" % (cls.__module__, cls.__name__)
            doc = cls.__doc__ and cls.__doc__.split("\n")[0] or ""
            desc = doc and '%s: %s' % (name, doc) or name

            row = self.REPORT_CLASS_TMPL % dict(
                style = ne > 0 and 'errorClass' or nf > 0 and 'failClass' or 'passClass',
                desc = desc,
                count = np+nf+ne,
                Pass = np,
                fail = nf,
                error = ne,
                cid = 'c%s' % (cid+1),
            )
            rows.append(row)

            for tid, (n,t,o,e) in enumerate(cls_results):
                self._generate_report_test(rows, cid, tid, n, t, o, e)

        report = self.REPORT_TMPL % dict(
            test_list = ''.join(rows),
            count = str(result.success_count+result.failure_count+result.error_count),
            Pass = str(result.success_count),
            fail = str(result.failure_count),
            error = str(result.error_count),
        )
        return report


    def _generate_report_test(self, rows, cid, tid, n, t, o, e):
        # e.g. 'pt1.1', 'ft1.1', etc
        has_output = bool(o or e)
        tid = (n == 0 and 'p' or 'f') + 't%s.%s' % (cid+1,tid+1)
        name = t.id().split('.')[-1]
        doc = t.shortDescription() or ""
        desc = doc and ('%s: %s' % (name, doc)) or name
        tmpl = has_output and self.REPORT_TEST_WITH_OUTPUT_TMPL or self.REPORT_TEST_NO_OUTPUT_TMPL

        # o and e should be byte string because they are collected from stdout and stderr?
        if isinstance(o,str):
            # TODO: some problem with 'string_escape': it escape \n and mess up formating
            # uo = unicode(o.encode('string_escape'))
            uo = o.decode('latin-1')
        else:
            uo = o
        if isinstance(e,str):
            # TODO: some problem with 'string_escape': it escape \n and mess up formating
            # ue = unicode(e.encode('string_escape'))
            ue = e.decode('latin-1')
        else:
            ue = e

        script = self.REPORT_TEST_OUTPUT_TMPL % dict(
            id = tid,
            output = saxutils.escape(uo+ue),
        )

        row = tmpl % dict(
            tid = tid,
            Class = (n == 0 and 'hiddenRow' or 'none'),
            style = n == 2 and 'errorCase' or (n == 1 and 'failCase' or 'none'),
            desc = desc,
            script = script,
            status = self.STATUS[n],
        )
        rows.append(row)
        if not has_output:
            return

    def _generate_ending(self):
        return self.ENDING_TMPL


##############################################################################
# Facilities for running tests from the command line
##############################################################################

# Note: Reuse unittest.TestProgram to launch test. In the future we may
# build our own launcher to support more specific command line
# parameters like test title, CSS, etc.
class TestProgram(unittest.TestProgram):
    """
    A variation of the unittest.TestProgram. Please refer to the base
    class for command line parameters.
    """
    def runTests(self):
        # Pick HTMLTestRunner as the default test runner.
        # base class's testRunner parameter is not useful because it means
        # we have to instantiate HTMLTestRunner before we know self.verbosity.
        if self.testRunner is None:
            self.testRunner = HTMLTestRunner(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)

main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)

########NEW FILE########
__FILENAME__ = java_jar_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for java_jar target.

"""


import blade_test


class TestJavaJar(blade_test.TargetTest):
    """Test java_jar """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_java_jar/java', ':poppy_java_client',
                     generate_php=False)
        self.upper_target_path = 'test_java_jar'

    def testLoadBuildsNotNone(self):
        """Test direct targets and all command targets are not none. """
        pass

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        swig_library = (self.upper_target_path, 'poppy_client')
        java_client = (self.target_path, 'poppy_java_client')
        proto_library = (self.upper_target_path, 'rpc_option_proto')
        self.command_file = 'cmds.tmp'

        self.assertTrue(swig_library in self.all_targets.keys())
        self.assertTrue(java_client in self.all_targets.keys())
        self.assertTrue(proto_library in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_proto_cpp_option = ''
        com_proto_java_option = ''
        com_proto_cpp_meta = ''
        com_proto_java_meta = ''

        com_proto_option_cc = ''
        com_proto_meta_cc = ''

        com_swig_python = ''
        com_swig_java = ''
        com_swig_python_cxx = ''
        com_swig_java_cxx = ''

        swig_python_so = ''
        swig_java_so = ''

        java_com_line = ''
        java_so_line = ''
        jar_line = ''

        java_com_idx = 0
        java_so_idx = 0
        jar_idx = 0
        index = 0

        for line in self.scons_output:
            index += 1
            if 'protobuf/bin/protoc' in line:
                if 'cpp_out' in line:
                    if 'rpc_option.proto' in line:
                        com_proto_cpp_option = line
                    elif 'rpc_meta_info.proto' in line:
                        com_proto_cpp_meta = line
                if 'java_out' in line:
                    if 'rpc_option.proto' in line:
                        com_proto_java_option = line
                    elif 'rpc_meta_info.proto' in line:
                        com_proto_java_meta = line

            if 'rpc_option.pb.cc.o -c' in line:
                com_proto_option_cc = line
            if 'rpc_meta_info.pb.cc.o -c' in line:
                com_proto_meta_cc = line
            if 'swig -python' in line:
                com_swig_python = line
            if 'swig -java' in line:
                com_swig_java = line
            if 'poppy_client_pywrap.cxx.o -c' in line:
                com_swig_python_cxx = line
            if 'poppy_client_javawrap.cxx.o -c' in line:
                com_swig_java_cxx = line
            if 'javac -classpath' in line:
                java_com_line = line
                java_com_idx = index
            if 'libpoppy_client_java.so -m64' in line:
                java_so_line = line
                java_so_idx = index
            if 'jar cf' in line:
                jar_line = line
                jar_idx = index

        self.assertTrue(com_proto_cpp_option)
        self.assertTrue(com_proto_cpp_meta)
        self.assertTrue(com_proto_java_option)
        self.assertTrue(com_proto_java_meta)

        self.assertTrue('-fPIC' in com_proto_option_cc)
        self.assertTrue('-Wall -Wextra' not in com_proto_option_cc)
        self.assertTrue('-Wframe-larger-than=' not in com_proto_option_cc)
        self.assertTrue('-Werror=overloaded-virtual' not in com_proto_option_cc)

        self.assertTrue('-fPIC' in com_proto_meta_cc)

        self.assertTrue('poppy_client_pywrap.cxx' in com_swig_python)
        self.assertTrue('poppy_client_javawrap.cxx' in com_swig_java)

        self.assertTrue('-fno-omit-frame-pointer' in com_swig_python_cxx)
        self.assertTrue('-mcx16 -pipe -g' in com_swig_python_cxx)
        self.assertTrue('-DNDEBUG -D_FILE_OFFSET_BITS' in com_swig_python_cxx)

        self.assertTrue('-fno-omit-frame-pointer' in com_swig_java_cxx)
        self.assertTrue('-mcx16 -pipe -g' in com_swig_java_cxx)
        self.assertTrue('-DNDEBUG -D_FILE_OFFSET_BITS' in com_swig_java_cxx)

        self.assertTrue(java_com_line)
        self.assertTrue(java_so_line)
        self.assertTrue(jar_line)

        self.assertTrue('test_java_jar/java/lib/junit.jar' in java_com_line)
        self.assertTrue('com/soso/poppy/swig/*.java' in java_com_line)
        self.assertTrue('com/soso/poppy/*.java' in java_com_line)

        whole_archive = ('--whole-archive build64_release/test_java_jar/'
                         'librpc_meta_info_proto.a build64_release/test_java_jar/'
                         'librpc_option_proto.a -Wl,--no-whole-archive')
        self.assertTrue(whole_archive in java_so_line)
        self.assertTrue(jar_idx > java_com_idx)
        self.assertTrue(jar_idx > java_so_idx)


if __name__ == '__main__':
    blade_test.run(TestJavaJar)

########NEW FILE########
__FILENAME__ = lex_yacc_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for lex_yacc_library target.

"""


import blade_test


class TestLexYacc(blade_test.TargetTest):
    """Test lex_yacc """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_lex_yacc')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        lex_yacc_library = (self.target_path, 'parser')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(lex_yacc_library in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_bison_line = ''
        com_flex_line = ''
        com_ll_static_line = ''
        com_yy_static_line = ''
        lex_yacc_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'bison -d -o' in line:
                com_bison_line = line
            if 'flex -R -t' in line:
                com_flex_line = line
            if 'line_parser.ll.cc.o -c' in line:
                com_ll_static_line = line
            if 'line_parser.yy.cc.o -c' in line:
                com_yy_static_line = line
            if 'libparser.so' in line:
                lex_yacc_depends_libs = line

        self.assertCxxFlags(com_lower_line)

        self.assertTrue('line_parser.yy.cc' in com_bison_line)
        self.assertTrue('line_parser.ll.cc' in com_flex_line)

        self.assertCxxFlags(com_ll_static_line)
        self.assertCxxFlags(com_yy_static_line)

        self.assertTrue('liblowercase.so' in lex_yacc_depends_libs)
        self.assertTrue('line_parser.ll.cc.o' in lex_yacc_depends_libs)
        self.assertTrue('line_parser.yy.cc.o' in lex_yacc_depends_libs)
        self.assertDynamicLinkFlags(lex_yacc_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestLexYacc)

########NEW FILE########
__FILENAME__ = load_builds_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the TestLoadBuilds module which tests the loading
 function of blade.

"""


import blade_test


class TestLoadBuilds(blade_test.TargetTest):
    """Test load builds. """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_loadbuilds')

    def testAllCommandTargets(self):
        """Test that all targets in the test project BUILD files

           are in the all command targets list.

        """
        proto_library = (self.target_path, 'rpc_meta_info_proto')
        cc_library = (self.target_path, 'poppy')
        static_resource = (self.target_path, 'static_resource')
        cc_test = (self.target_path, 'rpc_channel_test')
        swig_library = (self.target_path, 'poppy_client')
        lex_yacc_library = (self.target_path, 'parser')
        cc_plugin = (self.target_path, 'meter_business')
        gen_rule = (self.target_path, 'search_service_echo')
        java_jar = (self.target_path, 'poppy_java_client')
        cc_binary = (self.target_path, 'echoserver')

        target_list = []
        l = target_list
        l.append(proto_library)
        l.append(cc_library)
        l.append(static_resource)
        l.append(cc_test)
        l.append(swig_library)
        l.append(lex_yacc_library)
        l.append(cc_plugin)
        l.append(gen_rule)
        l.append(java_jar)
        l.append(cc_binary)

        target_count = 0
        for target in target_list:
            if target in self.all_command_targets:
                target_count += 1
            else:
                self.fail(msg='(%s, %s) not in all command targets, failed' % (
                        target[0], target[1]))
                break

        self.assertEqual(target_count, 10)

if __name__ == '__main__':
    blade_test.run(TestLoadBuilds)

########NEW FILE########
__FILENAME__ = prebuild_cc_library_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for prebuild_cc_library target.

"""


import blade_test


class TestPrebuildCcLibrary(blade_test.TargetTest):
    """Test cc_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_prebuild_cc_library')

    def testGenerateRules(self):
        """Test that rules are generated correctly.

        Scons can use the rules for dry running.

        """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        copy_lower_line = ''
        com_upper_line = ''
        upper_depends_libs = ''
        for line in self.scons_output:
            if 'Copy' in line:
                copy_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'libuppercase.so -m64' in line:
                upper_depends_libs = line

        self.assertTrue('test_prebuild_cc_library/liblowercase.so' in copy_lower_line)
        self.assertTrue('lib64_release/liblowercase.so' in copy_lower_line)

        self.assertTrue('-Wall -Wextra' in com_upper_line)
        self.assertTrue('-Wframe-larger-than=69632' in com_upper_line)
        self.assertTrue('-Werror=overloaded-virtual' in com_upper_line)

        self.assertTrue(upper_depends_libs)
        self.assertTrue('libuppercase.so -m64' in upper_depends_libs)
        self.assertTrue('liblowercase.so' in upper_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestPrebuildCcLibrary)

########NEW FILE########
__FILENAME__ = proto_library_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# This is the test module for proto_library target.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


import os
import sys
import blade_test


class TestProtoLibrary(blade_test.TargetTest):
    """Test proto_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_proto_library')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        proto_library_option = (self.target_path, 'rpc_option_proto')
        proto_library_meta = (self.target_path, 'rpc_option_proto')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(proto_library_option in self.all_targets.keys())
        self.assertTrue(proto_library_meta in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_proto_cpp_option = ''
        com_proto_java_option = ''
        com_proto_cpp_meta = ''
        com_proto_java_meta = ''

        com_proto_option_cc = ''
        com_proto_meta_cc = ''
        meta_depends_libs = ''
        lower_depends_libs = ''

        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'protobuf/bin/protoc' in line:
                if 'cpp_out' in line:
                    if 'rpc_option.proto' in line:
                        com_proto_cpp_option = line
                    elif 'rpc_meta_info.proto' in line:
                        com_proto_cpp_meta = line
                if 'java_out' in line:
                    if 'rpc_option.proto' in line:
                        com_proto_java_option = line
                    elif 'rpc_meta_info.proto' in line:
                        com_proto_java_meta = line

            if 'rpc_option.pb.cc.o -c' in line:
                com_proto_option_cc = line
            if 'rpc_meta_info.pb.cc.o -c' in line:
                com_proto_meta_cc = line
            if 'librpc_meta_info_proto.so -m64' in line:
                meta_depends_libs = line
            if 'liblowercase.so -m64' in line:
                lower_depends_libs = line

        self.assertCxxFlags(com_lower_line)

        self.assertTrue(com_proto_cpp_option)
        self.assertTrue(com_proto_cpp_meta)
        self.assertTrue(com_proto_java_option)
        self.assertTrue(com_proto_java_meta)

        self.assertNoWarningCxxFlags(com_proto_option_cc)
        self.assertNoWarningCxxFlags(com_proto_meta_cc)

        self.assertTrue(meta_depends_libs)
        self.assertTrue('librpc_option_proto.so' in meta_depends_libs)

        self.assertTrue('liblowercase.so' in lower_depends_libs)
        self.assertTrue('librpc_meta_info_proto.so' in lower_depends_libs)
        self.assertTrue('librpc_option_proto.so' in lower_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestProtoLibrary)

########NEW FILE########
__FILENAME__ = query_target_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module to test query function of blade.

"""


import blade_test


class TestQuery(blade_test.TargetTest):
    """Test cc_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_query', full_targets=['...'], command='query')
        self.query_targets = ['test_query:poppy']
        self.all_targets = self.blade.get_build_targets()

    def testQueryCorrectly(self):
        """Test query targets dependency relationship correctly. """
        self.assertTrue(self.all_targets)
        result_map = {}
        result_map = self.blade.query_helper(self.query_targets)
        all_targets = self.blade.get_build_targets()
        query_key = ('test_query', 'poppy')
        self.assertTrue(query_key in result_map.keys())
        deps = result_map.get(query_key, [])[0]
        depended_by = result_map.get(query_key, [])[1]

        self.assertTrue(deps)
        self.assertTrue(depended_by)

        dep_one_key = ('test_query', 'rpc_meta_info_proto')
        dep_second_key = ('test_query', 'static_resource')
        self.assertTrue(dep_one_key in deps)
        self.assertTrue(dep_second_key in deps)

        depended_one_key = ('test_query', 'poppy_client')
        depended_second_key = ('test_query', 'poppy_mock')
        self.assertTrue(depended_one_key in depended_by)
        self.assertTrue(depended_second_key in depended_by)


if __name__ == '__main__':
    blade_test.run(TestQuery)

########NEW FILE########
__FILENAME__ = resource_library_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for resource_library target.

"""


import blade_test


class TestResourceLibrary(blade_test.TargetTest):
    """Test resource_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_resource_library')

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        resource_library = (self.target_path, 'static_resource')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(resource_library in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_forms_line = ''
        com_poppy_line = ''
        static_so_line = ''
        lower_depends_libs = ''
        gen_forms_line = ''
        gen_poppy_line = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'forms_js_c.o -c' in line:
                com_forms_line = line
            if 'poppy_html_c.o -c' in line:
                com_poppy_line = line
            if 'libstatic_resource.so -m64' in line:
                static_so_line = line
            if 'liblowercase.so -m64' in line:
                lower_depends_libs = line
            if 'generate_resource_file' in line:
                if 'forms.js' in line:
                    gen_forms_line = line
                elif 'poppy.html' in line:
                    gen_poppy_line = line

        self.assertTrue(gen_forms_line)
        self.assertTrue(gen_poppy_line)

        self.assertCxxFlags(com_lower_line)
        self.assertNoWarningCxxFlags(com_forms_line)
        self.assertNoWarningCxxFlags(com_poppy_line)

        self.assertTrue('forms_js_c.o' in static_so_line)
        self.assertTrue('poppy_html_c.o' in static_so_line)

        self.assertDynamicLinkFlags(lower_depends_libs)
        self.assertTrue('libstatic_resource.so' in lower_depends_libs)


if __name__ == '__main__':
    blade_test.run(TestResourceLibrary)

########NEW FILE########
__FILENAME__ = swig_library_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module for swig_library target.

"""


import blade_test


class TestSwigLibrary(blade_test.TargetTest):
    """Test swig_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_swig_library', generate_php=False)

    def testGenerateRules(self):
        """Test that rules are generated correctly. """
        self.all_targets = self.blade.analyze_targets()
        self.rules_buf = self.blade.generate_build_rules()

        cc_library_lower = (self.target_path, 'lowercase')
        poppy_client = (self.target_path, 'poppy_client')
        self.command_file = 'cmds.tmp'

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(poppy_client in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''

        com_swig_python = ''
        com_swig_java = ''
        com_swig_python_cxx = ''
        com_swig_java_cxx = ''

        swig_python_so = ''
        swig_java_so = ''

        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'swig -python' in line:
                com_swig_python = line
            if 'swig -java' in line:
                com_swig_java = line
            if 'poppy_client_pywrap.cxx.o -c' in line:
                com_swig_python_cxx = line
            if 'poppy_client_javawrap.cxx.o -c' in line:
                com_swig_java_cxx = line
            if '_poppy_client.so -m64' in line:
                swig_python_so = line
            if 'libpoppy_client_java.so -m64' in line:
                swig_java_so = line

        self.assertCxxFlags(com_lower_line)

        self.assertTrue('poppy_client_pywrap.cxx' in com_swig_python)
        self.assertTrue('poppy_client_javawrap.cxx' in com_swig_java)

        self.assertCxxFlags(com_swig_python_cxx)
        self.assertCxxFlags(com_swig_java_cxx)

        self.assertDynamicLinkFlags(swig_python_so)
        self.assertDynamicLinkFlags(swig_java_so)


if __name__ == '__main__':
    blade_test.run(TestSwigLibrary)

########NEW FILE########
__FILENAME__ = target_dependency_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the Target dependency analyzing test module
 which tests the dependency analyzing module of blade.

"""


import os
import blade_test


class TestDepsAnalyzing(blade_test.TargetTest):
    """Test dependency analyzing. """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_dependency')

    def testExpandedTargets(self):
        """Test that all targets dependency relationship are

        populated correctly.

        """
        self.assertTrue(self.blade.is_expanded())
        self.assertTrue(self.all_targets)

        system_lib = ('#', 'pthread')
        proto_lib_option = (self.target_path, 'rpc_option_proto')
        proto_lib_meta = (self.target_path, 'rpc_meta_info_proto')
        cc_library_poppy = (self.target_path, 'poppy')
        cc_lib_poppy_mock = (self.target_path, 'poppy_mock')
        static_resource = (self.target_path, 'static_resource')
        cc_test = (self.target_path, 'rpc_channel_test')
        swig_library = (self.target_path, 'poppy_client')
        lex_yacc_library = (self.target_path, 'parser')
        cc_plugin = (self.target_path, 'meter_business')
        gen_rule = (self.target_path, 'search_service_echo')
        java_jar = (os.path.join(self.target_path, 'java'),
                    'poppy_java_client')
        cc_binary = (self.target_path, 'echoserver')
        cc_lib_prebuild = (self.target_path, 'poppy_swig_wrap')
        java_jar_prebuild = (os.path.join(self.target_path, 'java', 'lib'),
                             'protobuf-java')

        self.assertTrue(cc_library_poppy in self.all_targets.keys())

        poppy_deps = self.all_targets[cc_library_poppy].expanded_deps
        poppy_mock_deps = self.all_targets[cc_lib_poppy_mock].expanded_deps
        self.assertTrue(poppy_deps)
        self.assertTrue(poppy_mock_deps)

        self.assertTrue(proto_lib_option in poppy_deps)
        self.assertTrue(proto_lib_meta in poppy_deps)
        self.assertTrue(static_resource in poppy_deps)
        self.assertTrue(system_lib in poppy_deps)
        self.assertTrue(cc_library_poppy in poppy_mock_deps)
        self.assertTrue(proto_lib_meta in poppy_mock_deps)

        poppy_client_deps = self.all_targets[swig_library].expanded_deps
        self.assertTrue(poppy_client_deps)
        self.assertTrue(cc_library_poppy in poppy_client_deps)
        self.assertTrue(cc_lib_prebuild  in poppy_client_deps)

        self.assertTrue(java_jar in self.all_targets)
        java_jar_deps = self.all_targets[java_jar].expanded_deps
        self.assertTrue(java_jar_deps)

        self.assertTrue(proto_lib_option in java_jar_deps)
        self.assertTrue(proto_lib_meta in java_jar_deps)
        self.assertTrue(java_jar_prebuild in java_jar_deps)
        self.assertTrue(cc_library_poppy not in java_jar_deps)


if __name__ == '__main__':
    blade_test.run(TestDepsAnalyzing)

########NEW FILE########
__FILENAME__ = test_target_test
# Copyright (c) 2011 Tencent Inc.
# All rights reserved.
#
# Author: Michaelpeng <michaelpeng@tencent.com>
# Date:   October 20, 2011


"""
 This is the test module to test TestRunner function of blade.

"""


import os
import blade_test


class TestTestRunner(blade_test.TargetTest):
    """Test cc_library """
    def setUp(self):
        """setup method. """
        self.doSetUp('test_test_runner', ':string_test_main',
                     fulltest=False, args='', test_jobs=1, show_details=True)

    def testLoadBuildsNotNone(self):
        """Test direct targets and all command targets are not none. """
        self.assertTrue(self.direct_targets)
        self.assertTrue(self.all_command_targets)

    def testTestRunnerCorrectly(self):
        """Test query targets dependency relationship correctly. """
        self.assertTrue(self.all_targets)
        self.rules_buf = self.blade.generate_build_rules()
        test_env_dir = './build%s_%s/test_test_runner' % (
                self.options.m, self.options.profile)
        if not os.path.exists(test_env_dir):
            os.mkdir(test_env_dir)

        cc_library_lower = (self.target_path, 'lowercase')
        cc_library_upper = (self.target_path, 'uppercase')
        cc_library_string = (self.target_path, 'string_test_main')

        self.assertTrue(cc_library_lower in self.all_targets.keys())
        self.assertTrue(cc_library_upper in self.all_targets.keys())
        self.assertTrue(cc_library_string in self.all_targets.keys())

        self.assertTrue(self.dryRun())

        com_lower_line = ''
        com_upper_line = ''
        com_string_line = ''
        string_main_depends_libs = ''
        for line in self.scons_output:
            if 'plowercase.cpp.o -c' in line:
                com_lower_line = line
            if 'puppercase.cpp.o -c' in line:
                com_upper_line = line
            if 'string_test.cpp.o -c' in line:
                com_string_line = line
            if 'string_test_main' in line:
                string_main_depends_libs = line

        self.assertCxxFlags(com_lower_line)
        self.assertCxxFlags(com_upper_line)
        self.assertCxxFlags(com_string_line)

        self.assertLinkFlags(string_main_depends_libs)
        self.assertTrue('liblowercase.a' in string_main_depends_libs)
        ret_code = self.blade.test()
        self.assertEqual(ret_code, 1)


if __name__ == '__main__':
    blade_test.run(TestTestRunner)

########NEW FILE########
