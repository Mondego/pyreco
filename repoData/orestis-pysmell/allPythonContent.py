__FILENAME__ = argparse
# -*- coding: utf-8 -*-

# Copyright © 2006 Steven J. Bethard <steven.bethard@gmail.com>.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the 3-clause BSD
# license. No warranty expressed or implied.
# For details, see the accompanying file LICENSE.txt.

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

* handles both optional and positional arguments
* produces highly informative usage messages
* supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file:

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

    ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    HelpFormatter, RawDescriptionHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default, while
        RawDescriptionHelpFormatter tells the parser not to perform any
        line-wrapping on description text.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '0.9.0'

import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = '==PARSER=='

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format:
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
            item_help = join(func(*args) for func, args in self.items)
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
            invocation_length = max(len(s) for s in invocations)
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
        help = self._root_section.format_help() % dict(prog=self._prog)
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join(part
                       for part in part_strings
                       if part and part is not SUPPRESS)

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if no optionals or positionals are available, usage is just prog
        if usage is None and not actions:
            usage = '%(prog)s'

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            usage = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # determine width of "usage: PROG" and width of text
            prefix_width = len(prefix) + len(usage) + 1
            prefix_indent = self._current_indent + prefix_width
            text_width = self._width - self._current_indent

            # put them on one line if they're short enough
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            if prefix_width + len(action_usage) + 1 < text_width:
                usage = '%s %s' % (usage, action_usage)

            # if they're long, wrap optionals and positionals individually
            else:
                optional_usage = format(optionals, groups)
                positional_usage = format(positionals, groups)
                indent = ' ' * prefix_indent

                # usage is made of PROG, optionals and positionals
                parts = [usage, ' ']

                # options always get added right after PROG
                if optional_usage:
                    parts.append(_textwrap.fill(
                        optional_usage, text_width,
                        initial_indent=indent,
                        subsequent_indent=indent).lstrip())

                # if there were options, put arguments on the next line
                # otherwise, start them right after PROG
                if positional_usage:
                    part = _textwrap.fill(
                        positional_usage, text_width,
                        initial_indent=indent,
                        subsequent_indent=indent).lstrip()
                    if optional_usage:
                        part = '\n' + indent + part
                    parts.append(part)
                usage = ''.join(parts)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # find group indices and identify actions in groups
        group_actions = set()
        inserts = {}
        for group in groups:
            start = actions.index(group._group_actions[0])
            if start != -1:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        inserts[start] = '['
                        inserts[end] = ']'
                    else:
                        inserts[start] = '('
                        inserts[end] = ')'
                    for i in xrange(start + 1, end):
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
        text = ' '.join(item for item in parts if item is not None)

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
            return self._format_metavar(action, action.dest)

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

    def _format_metavar(self, action, default_metavar):
        if action.metavar is not None:
            name = action.metavar
        elif action.choices is not None:
            choice_strs = (str(choice) for choice in action.choices)
            name = '{%s}' % ','.join(choice_strs)
        else:
            name = default_metavar
        return name

    def _format_args(self, action, default_metavar):
        name = self._format_metavar(action, default_metavar)
        if action.nargs is None:
            result = name
        elif action.nargs == OPTIONAL:
            result = '[%s]' % name
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % (name, name)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % (name, name)
        elif action.nargs is PARSER:
            result = '%s ...' % name
        else:
            result = ' '.join([name] * action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name, value in params.items():
            if value is SUPPRESS:
                del params[name]
        if params.get('choices') is not None:
            choices_str = ', '.join(str(c) for c in params['choices'])
            params['choices'] = choices_str
        return action.help % params

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

class RawDescriptionHelpFormatter(HelpFormatter):

    def _fill_text(self, text, width, indent):
        return ''.join(indent + line for line in text.splitlines(True))

class RawTextHelpFormatter(RawDescriptionHelpFormatter):

    def _split_lines(self, text, width):
        return text.splitlines()

# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    if argument.option_strings:
        return  '/'.join(argument.option_strings)
    elif argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    elif argument.dest not in (None, SUPPRESS):
        return argument.dest
    else:
        return None

class ArgumentError(Exception):
    """ArgumentError(message, argument)

    Raised whenever there was an error creating or using an argument
    (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name =  _get_action_name(argument)
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)

# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Action(*strings, **options)

    Action objects hold the information necessary to convert a
    set of command-line arguments (possibly including an initial option
    string) into the desired Python object(s).

    Keyword Arguments:

    option_strings -- A list of command-line option strings which
        should be associated with this action.

    dest -- The name of the attribute to hold the created object(s)

    nargs -- The number of command-line arguments that should be consumed.
        By default, one argument will be consumed and a single value will
        be produced.  Other values include:
            * N (an integer) consumes N arguments (and produces a list)
            * '?' consumes zero or one arguments
            * '*' consumes zero or more arguments (and produces a list)
            * '+' consumes one or more arguments (and produces a list)
        Note that the difference between the default and nargs=1 is that
        with the default, a single value will be produced, while with
        nargs=1, a list containing a single value will be produced.

    const -- The value to be produced if the option is specified and the
        option uses an action that takes no values.

    default -- The value to be produced if the option is not specified.

    type -- The type which the command-line arguments should be converted
        to, should be one of 'string', 'int', 'float', 'complex' or a
        callable object that accepts a single string argument. If None,
        'string' is assumed.

    choices -- A container of values that should be allowed. If not None,
        after a command-line argument has been converted to the appropriate
        type, an exception will be raised if it is not a member of this
        collection.

    required -- True if the action must always be specified at the command
        line. This is only meaningful for optional command-line arguments.

    help -- The help string describing the argument.

    metavar -- The name to be used for the option's argument with the help
        string. If None, the 'dest' value will be used as the name.
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
            'metavar'
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
            raise ValueError('nargs must be > 0')
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
            raise ValueError('nargs must be > 0')
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
        _ensure_value(namespace, self.dest, []).append(values)

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
        _ensure_value(namespace, self.dest, []).append(self.const)

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
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_version()
        parser.exit()

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
        parser.parse_args(arg_strings, namespace)


# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
    mode -- A string indicating how the file is to be opened. Accepts the
        same values as the builtin open() function.
    bufsize -- The file's desired buffer size. Accepts the same values as
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
        args_str = ', '.join(repr(arg) for arg in args if arg is not None)
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):

    def __init__(self, **kwargs):
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)


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
        self._negative_number_matcher = _re.compile(r'^-\d+|-\d*.\d+$')

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
    # Namespace default settings methods
    # ==================================

    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

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
        action = action_class(**kwargs)
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
            # error on one-or-fewer-character option strings
            if len(option_string) < 2:
                msg = _('invalid option string %r: '
                        'must be at least two characters long')
                raise ValueError(msg % option_string)

            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = _('invalid option string %r: '
                        'must start with a character %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # error on strings that are all prefix characters
            if not (set(option_string) - set(self.prefix_chars)):
                msg = _('invalid option string %r: '
                        'must contain characters other than %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
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
        conflict_string = ', '.join(option_string
                                    for option_string, action
                                    in conflicting_actions)
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
        self._has_negative_number_optionals = container._has_negative_number_optionals

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

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):

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
        self.add_help = add_help

        self._has_subparsers = False

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # add help and version arguments if necessary
        # (using explicit default to override global argument_default)
        if self.add_help:
            self.add_argument(
                '-h', '--help', action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                '-v', '--version', action='version', default=SUPPRESS,
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
        if self._has_subparsers:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

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
        self._positionals._add_action(action)
        self._has_subparsers = True

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
        for dest, value in self._defaults.iteritems():
            if not hasattr(namespace, dest):
                setattr(namespace, dest, value)

        # parse the arguments and exit if there are any errors
        try:
            return self._parse_args(args, namespace)
        except ArgumentError, err:
            self.error(str(err))

    def _parse_args(self, arg_strings, namespace):
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

                # if we found no optional action, raise an error
                if action is None:
                    self.error(_('no such option: %s') % option_string)

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
                        for char in self.prefix_chars:
                            option_string = char + explicit_arg[0]
                            explicit_arg = explicit_arg[1:] or None
                            optionals_map = self._option_string_actions
                            if option_string in optionals_map:
                                action = optionals_map[option_string]
                                break
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
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = min(
                index
                for index in option_string_indices
                if index >= start_index)
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
            # at the index of an option string, there were unparseable
            # arguments
            if start_index not in option_string_indices:
                msg = _('extra arguments found: %s')
                extras = arg_strings[start_index:next_option_string_index]
                self.error(msg % ' '.join(extras))

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were too
        # many supplied
        if stop_index != len(arg_strings):
            extras = arg_strings[stop_index:]
            self.error(_('extra arguments found: %s') % ' '.join(extras))

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

        # return the updated namespace
        return namespace

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None:_('expected one argument'),
                OPTIONAL:_('expected at most one argument'),
                ONE_OR_MORE:_('expected at least one argument')
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
        for i in xrange(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join(self._get_nargs_pattern(action)
                              for action in actions_slice)
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend(len(string) for string in match.groups())
                break

        # return the list of arg string counts
        return result

    def _parse_optional(self, arg_string):
        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if it's just dashes, it was meant to be positional
        if not arg_string.strip('-'):
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join(opt_str for _, opt_str, _ in option_tuples)
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

        # allow one argument followed by any number of options or arguments
        elif nargs is PARSER:
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
        if action.nargs is not PARSER:
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

        # PARSER arguments convert all values, but check only the first
        elif action.nargs is PARSER:
            value = list(self._get_value(action, v) for v in arg_strings)
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = list(self._get_value(action, v) for v in arg_strings)
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # TypeErrors or ValueErrors indicate errors
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
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================

    def print_usage(self, file=None):
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        self._print_message(self.format_help(), file)

    def print_version(self, file=None):
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
            _sys.stderr.write(message)
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
__FILENAME__ = codefinder
# codefinder.py
# Statically analyze python code
# Copyright (C) 2008 Orestis Markou
# All rights reserved
# E-mail: orestis@orestis.gr

# http://orestis.gr

# Released subject to the BSD License 

import os
import sys
import __builtin__
import compiler

from compiler import ast

class ModuleDict(dict):
    def __init__(self):
        self._modules = {'CLASSES': {}, 'FUNCTIONS': [], 'CONSTANTS': [], 'POINTERS': {}, 'HIERARCHY': []}

    def enterModule(self, module):
        self.currentModule = module
        self['HIERARCHY'].append(module)

    def exitModule(self):
        self.currentModule = None

    def currentClass(self, klass):
        fullClass = "%s.%s" % (self.currentModule, klass)
        return self['CLASSES'][fullClass]

    def enterClass(self, klass, bases, docstring):
        fullClass = "%s.%s" % (self.currentModule, klass)
        self['CLASSES'][fullClass] = {}
        self['CLASSES'][fullClass]['methods'] = []
        self['CLASSES'][fullClass]['properties'] = []
        self['CLASSES'][fullClass]['constructor'] = []
        self['CLASSES'][fullClass]['bases'] = bases
        self['CLASSES'][fullClass]['docstring'] = docstring

    def addMethod(self, klass, method, args, docstring):
        if (method, args, docstring) not in self.currentClass(klass)['methods']:
            self.currentClass(klass)['methods'].append((method, args, docstring))

    def addPointer(self, name, pointer):
        self['POINTERS'][name] = pointer

    def addFunction(self, function, args, docstring):
        fullFunction = "%s.%s" % (self.currentModule, function)
        self['FUNCTIONS'].append((fullFunction, args, docstring))

    def addProperty(self, klass, prop):
        if klass is not None:
            if prop not in self.currentClass(klass)['properties']:
                self.currentClass(klass)['properties'].append(prop)
        else:
            fullProp = "%s.%s" % (self.currentModule, prop)
            self['CONSTANTS'].append(fullProp)

    def setConstructor(self, klass, args):
        fullClass = "%s.%s" % (self.currentModule, klass)
        self['CLASSES'][fullClass]['constructor'] = args

    def update(self, other):
        if other:
            self['CONSTANTS'].extend(other['CONSTANTS'])
            self['FUNCTIONS'].extend(other['FUNCTIONS'])
            self['HIERARCHY'].extend(other['HIERARCHY'])
            self['CLASSES'].update(other['CLASSES'])
            self['POINTERS'].update(other['POINTERS'])

    def keys(self):
        return self._modules.keys()

    def values(self):
        return self._modules.values()

    def items(self):
        return self._modules.items()

    def iteritems(self):
        return self._modules.iteritems()

    def __getitem__(self, item):
        return self._modules[item]

    def __len__(self):
        return len(self.keys())

    def __eq__(self, other):
        return ((isinstance(other, ModuleDict) and other._modules == self._modules) or
               (isinstance(other, dict) and other == self._modules))
              

    def __ne__(self, other):
        return not self == other


def VisitChildren(fun):
    def decorated(self, *args, **kwargs):
        fun(self, *args, **kwargs)
        self.handleChildren(args[0])
    return decorated


class BaseVisitor(object):
    def __init__(self):
        self.scope = []
        self.imports = {}


    def handleChildren(self, node):
        for c in node.getChildNodes():
            self.visit(c)

    @VisitChildren
    def visitFrom(self, node):
        for name in node.names:
            asName = name[1] or name[0]
            self.imports[asName] = "%s.%s" % (node.modname, name[0])

    @VisitChildren
    def visitImport(self, node):
        for name in node.names:
            asName = name[1] or name[0]
            self.imports[asName] = name[0]

    def qualify(self, name, curModule):
        if hasattr(__builtin__, name):
            return name
        if name in self.imports:
            return self.imports[name]
        for imp in self.imports:
            if name.startswith(imp):
                actual = self.imports[imp]
                return "%s%s" % (actual, name[len(imp):])
        if curModule:
            return '%s.%s' % (curModule, name)
        else:
            return name

class CodeFinder(BaseVisitor):
    def __init__(self):
        BaseVisitor.__init__(self)
        self.modules = ModuleDict()
        self.module = '__module__'
        self.__package = '__package__'
        self.path = '__path__'

    
    def __setPackage(self, package):
        if package:
            self.__package = package + '.'
        else:
            self.__package = ''

    package = property(lambda s: s.__package, __setPackage)

    @property
    def inClass(self):
        return (len(self.scope) > 0 and (isinstance(self.scope[-1], ast.Class)
                    or self.inClassFunction))

    @property
    def inClassFunction(self):
        return (len(self.scope) == 2 and 
                isinstance(self.scope[-1], ast.Function) and
                isinstance(self.scope[-2], ast.Class))

    def enterScope(self, node):
        self.scope.append(node)

    def exitScope(self):
        self.scope.pop()

    @property
    def currentClass(self):
        if self.inClassFunction:
            return self.scope[-2].name
        elif self.inClass:
            return self.scope[-1].name
        return None

    def visitModule(self, node):
        if self.module == '__init__':
            self.modules.enterModule('%s' % self.package[:-1]) # remove dot
        else:
            self.modules.enterModule('%s%s' % (self.package, self.module))
        self.visit(node.node)
        self.modules.exitModule()

    @VisitChildren
    def visitGetattr(self, node):
        if self.inClass:
            if isinstance(node.expr, ast.Name):
                if node.expr.name == 'self':
                    pass
            elif isinstance(node.expr, ast.CallFunc):
                pass

    @VisitChildren
    def visitAssAttr(self, node):
        if self.inClassFunction:
            if isinstance(node.expr, ast.Name):
                if node.expr.name == 'self':
                    self.modules.addProperty(self.currentClass, node.attrname)

    @VisitChildren
    def visitAssName(self, node):
        if self.inClass and len(self.scope) == 1:
            self.modules.addProperty(self.currentClass, node.name)
        elif len(self.scope) == 0:
            self.modules.addProperty(None, node.name)

    def visitFrom(self, node):
        BaseVisitor.visitFrom(self, node)
        for name in node.names:
            asName = name[1] or name[0]
            imported = name[0]
            if self.isRelativeImport(node.modname):
                imported = "%s%s.%s" % (self.package, node.modname, imported)
            else:
                imported = "%s.%s" % (node.modname, imported)
            self.modules.addPointer("%s.%s" % (self.modules.currentModule, asName), imported)

    def visitImport(self, node):
        BaseVisitor.visitImport(self, node)
        for name in node.names:
            asName = name[1] or name[0]
            imported = name[0]
            if self.isRelativeImport(imported):
                imported = "%s%s" % (self.package, imported)
            self.modules.addPointer("%s.%s" % (self.modules.currentModule, asName), imported)

    def isRelativeImport(self, imported):
        pathToImport = os.path.join(self.path, *imported.split('.'))
        return os.path.exists(pathToImport) or os.path.exists(pathToImport + '.py')
        
    def visitClass(self, klass):
        self.enterScope(klass)
        if len(self.scope) == 1:
            bases = [self.qualify(getName(b), self.modules.currentModule) for b in klass.bases]
            self.modules.enterClass(klass.name, bases, klass.doc or '')
        self.visit(klass.code)
        self.exitScope()

    def visitFunction(self, func):
        self.enterScope(func)
        if self.inClassFunction:
            if func.name != '__init__':
                if func.decorators and 'property' in [getName(n) for n in func.decorators]:
                    self.modules.addProperty(self.currentClass, func.name)
                else:
                    self.modules.addMethod(self.currentClass, func.name,
                                    getFuncArgs(func), func.doc or "")
            else:
                self.modules.setConstructor(self.currentClass, getFuncArgs(func))
        elif len(self.scope) == 1:
            self.modules.addFunction(func.name, getFuncArgs(func,
                                inClass=False), func.doc or "")

        self.visit(func.code)
        self.exitScope()


def getNameTwo(template, left, right, leftJ='', rightJ=''):
    return template % (leftJ.join(map(getName, left)),
                        rightJ.join(map(getName, right)))

MATHNODES = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mul: '*',
    ast.Power: '**',
    ast.Div: '/',
    ast.Mod: '%',
}

def getNameMath(node):
    return '%s%s%s' % (getName(node.left), MATHNODES[node.__class__], getName(node.right))


def getName(node):
    if node is None: return ''
    if isinstance(node, (basestring, int, long, float)):
        return str(node)
    if isinstance(node, (ast.Class, ast.Name, ast.Function)):
        return node.name
    if isinstance(node, ast.Dict):
        pairs = ['%s: %s' % pair for pair in [(getName(first), getName(second))
                        for (first, second) in node.items]]
        return '{%s}' % ', '.join(pairs)
    if isinstance(node, ast.CallFunc):
        notArgs = [n for n in node.getChildNodes() if n not in node.args]
        return getNameTwo('%s(%s)', notArgs, node.args, rightJ=', ')
    if isinstance(node, ast.Const):
        try:
            float(node.value)
            return str(node.value)
        except:
            return repr(str(node.value))
    if isinstance(node, ast.LeftShift):
        return getNameTwo('%s<<%s', node.left, node.right)
    if isinstance(node, ast.RightShift):
        return getNameTwo('%s>>%s', node.left, node.right)
    if isinstance(node, (ast.Mul, ast.Add, ast.Sub, ast.Power, ast.Div, ast.Mod)):
        return getNameMath(node)
    if isinstance(node, ast.Bitor):
        return '|'.join(map(getName, node.nodes))
    if isinstance(node, ast.UnarySub):
        return '-%s' % ''.join(map(getName, ast.flatten(node)))
    if isinstance(node, ast.List):
        return '[%s]' % ', '.join(map(getName, ast.flatten(node)))
    if isinstance(node, ast.Tuple):
        return '(%s)' % ', '.join(map(getName, ast.flatten(node)))
    if isinstance(node, ast.Lambda):
        return 'lambda %s: %s' % (', '.join(map(getName, node.argnames)), getName(node.code))
    if isinstance(node, ast.Getattr):
        return '.'.join(map(getName, ast.flatten(node)))
    if isinstance(node, ast.Compare):
        rhs = node.asList()[-1]
        return '%s %r' % (' '.join(map(getName, node.getChildren()[:-1])), rhs.value)
    if isinstance(node, ast.Slice):
        children = node.getChildren()
        slices = children[2:]
        formSlices = []
        for sl in slices:
            if sl is None:
                formSlices.append('')
            else:
                formSlices.append(getName(sl))
        sliceStr = ':'.join(formSlices)
        return '%s[%s]' % (getName(children[0]), sliceStr)
    if isinstance(node, ast.Not):
        return "not %s" % ''.join(map(getName, ast.flatten(node)))
    if isinstance(node, ast.Or):
        return " or ".join(map(getName, node.nodes))
    if isinstance(node, ast.And):
        return " and ".join(map(getName, node.nodes))
    if isinstance(node, ast.Keyword):
        return "%s=%s" % (node.name, getName(node.expr))
    return repr(node)


def argToStr(arg):
    if isinstance(arg, tuple):
        if len(arg) == 1:
            return '(%s,)' % argToStr(arg[0])
        return '(%s)' % ', '.join(argToStr(elem) for elem in arg)
    return arg
            

def getFuncArgs(func, inClass=True):
    args = map(argToStr, func.argnames[:])
    if func.kwargs and func.varargs:
        args[-1] = '**' + args[-1]
        args[-2] = '*' + args[-2]
    elif func.kwargs:
        args[-1] = '**' + args[-1]
    elif func.varargs:
        args[-1] = '*' + args[-1]

    if inClass:
        args = args[1:]

    offset = bool(func.varargs) + bool(func.kwargs) + 1
    for default in reversed(func.defaults):
        name = getName(default)
        if isinstance(default, ast.Const):
            name = repr(default.value)
        args[-offset] = args[-offset] + "=" + name
        offset += 1

    return args


def getClassDict(path, codeFinder=None):
    tree = compiler.parseFile(path)
    if codeFinder is None:
        codeFinder = CodeFinder()
    compiler.walk(tree, codeFinder)
    return codeFinder.modules


def findRootPackageList(directory, filename):
    "should walk up the tree until there is no __init__.py"
    isPackage = lambda path: os.path.exists(os.path.join(path, '__init__.py'))
    if not isPackage(directory):
        return []
    packages = []
    while directory and isPackage(directory):
        directory, tail = os.path.split(directory)
        if tail:
            packages.append(tail)
    packages.reverse()
    return packages


def findPackage(path):
    packages = findRootPackageList(path, "")
    package = '.'.join(packages)
    return package


def processFile(f, path):
    """f is the the filename, path is the relative path in the project, root is
    the topmost package"""
    codeFinder = CodeFinder()

    package = findPackage(path)
    codeFinder.package = package
    codeFinder.module = f[:-3]
    codeFinder.path = path
    try:
        assert os.path.isabs(path), "path should be absolute"
        modules = getClassDict(os.path.join(path, f), codeFinder)
        return modules
    except Exception, e:
        print '-=#=- '* 10
        print 'EXCEPTION in', os.path.join(path, f)
        print e
        print '-=#=- '* 10
        return None


def analyzeFile(fullPath, tree):
    if tree is None:
        return None
    codeFinder = CodeFinder()
    absPath, filename = os.path.split(fullPath)
    codeFinder.module = filename[:-3]
    codeFinder.path = absPath
    package = findPackage(absPath)
    codeFinder.package = package
    compiler.walk(tree, codeFinder)
    return codeFinder.modules
        

class SelfInferer(BaseVisitor):
    def __init__(self):
        BaseVisitor.__init__(self)
        self.classRanges = []
        self.lastlineno = 1

    def __getattr__(self, _):
        return self.handleChildren

    def handleChildren(self, node):
        self.lastlineno = node.lineno
        BaseVisitor.handleChildren(self, node)


    def visitClass(self, klassNode):
        self.visit(klassNode.code)
        nestedStart, nestedEnd = None, None
        for klass, _, start, end in self.classRanges:
            if start > klassNode.lineno and end < self.lastlineno:
                nestedStart, nestedEnd = start, end
            
        bases = [self.qualify(getName(b), None) for b in klassNode.bases]
        if nestedStart == nestedEnd == None:
            self.classRanges.append((klassNode.name, bases, klassNode.lineno, self.lastlineno))
        else:
            start, end = klassNode.lineno, self.lastlineno
            self.classRanges.append((klassNode.name, bases, start, nestedStart-1))
            self.classRanges.append((klassNode.name, bases, nestedEnd+1, end))
        self.lastlineno = klassNode.lineno


def getSafeTree(source, lineNo):
    source = source.replace('\r\n', '\n')
    try:
        tree = compiler.parse(source)
    except:
        sourceLines = source.splitlines()
        line = sourceLines[lineNo-1]
        unindented = line.lstrip()
        indentation = len(line) - len(unindented)
        whitespace = ' '
        if line.startswith('\t'):
            whitespace = '\t'
        sourceLines[lineNo-1] = '%spass' % (whitespace * indentation)

        replacedSource = '\n'.join(sourceLines)
        try:
            tree = compiler.parse(replacedSource)
        except SyntaxError, e:
            print >> sys.stderr, e.args
            return None

    return tree

class NameVisitor(BaseVisitor):
    def __init__(self):
        BaseVisitor.__init__(self)
        self.names = {}
        self.klasses = []
        self.lastlineno = 1


    def handleChildren(self, node):
        self.lastlineno = node.lineno
        BaseVisitor.handleChildren(self, node)


    @VisitChildren
    def visitAssign(self, node):
        assNode = node.nodes[0]
        name = None
        if isinstance(assNode, ast.AssName):
            name = assNode.name
        elif isinstance(assNode, ast.AssAttr):
            name = assNode.attrname
        self.names[name] = getName(node.expr)

    @VisitChildren
    def visitClass(self, node):
        self.klasses.append(node.name)


def getNames(tree):
    if tree is None:
        return None
    inferer = NameVisitor()
    compiler.walk(tree, inferer)
    names = inferer.names
    names.update(inferer.imports)
    return names, inferer.klasses
    


def getImports(tree):
    if tree is None:
        return None
    inferer = BaseVisitor()
    compiler.walk(tree, inferer)

    return inferer.imports


def getClassAndParents(tree, lineNo):
    if tree is None:
        return None, []

    inferer = SelfInferer()
    compiler.walk(tree, inferer)
    classRanges = inferer.classRanges
    classRanges.sort(sortClassRanges)
    
    for klass, parents, start, end in classRanges:
        if lineNo >= start:
            return klass, parents
    return None, []

def sortClassRanges(a, b):
    return b[2] - a[2]


########NEW FILE########
__FILENAME__ = emacshelper
from pysmell import idehelper
from re import split


def _uniquify(l):
    found = set()
    for item in l:
        if item not in found:
            yield item
        found.add(item)


def get_completions(fullPath, origSource, lineNo, origCol, matcher):
    """arguments: fullPath, origSource, lineNo, origCol, matcher

When visiting the file at fullPath, with edited source origSource, find a list 
of possible completion strings for the symbol located at origCol on orgLineNo using 
matching mode matcher"""
    PYSMELLDICT = idehelper.findPYSMELLDICT(fullPath)
    if not PYSMELLDICT:
        return
    origLine = origSource.splitlines()[lineNo - 1]
    base = split("[,.\-+/|\[\]]", origLine[:origCol].strip())[-1]
    options = idehelper.detectCompletionType(fullPath, origSource, lineNo, origCol, base, PYSMELLDICT)
    completions = [completion['word'] for completion in idehelper.findCompletions(base, PYSMELLDICT, options, matcher)]
    completions = list(_uniquify(completions))
    return completions




        

########NEW FILE########
__FILENAME__ = idehelper
# idehelper.py
# Copyright (C) 2008 Orestis Markou
# All rights reserved
# E-mail: orestis@orestis.gr

# http://orestis.gr

# Released subject to the BSD License 

import __builtin__
import os, re
import fnmatch
from dircache import listdir

from pysmell.codefinder import findRootPackageList, getImports, getNames, getClassAndParents, analyzeFile, getSafeTree
from pysmell.matchers import MATCHERS

def findBase(line, col):
    index = col
    # col points at the end of the completed string
    # so col-1 is the last character of base
    while index > 0:
        index -= 1
        if line[index] in '. ':
            index += 1
            break
    return index #this is zero based :S
    

def updatePySmellDict(master, partial):
    for key, value in partial.items():
        if isinstance(value, dict):
            master.setdefault(key, {}).update(value)
        elif isinstance(value, list):
            master.setdefault(key, []).extend(value)


def tryReadPYSMELLDICT(directory, filename, dictToUpdate):
    if os.path.exists(os.path.join(directory, filename)):
        tagsFile = open(os.path.join(directory, filename), 'r')
        try:
            updatePySmellDict(dictToUpdate, eval(tagsFile.read()))
        finally:
            tagsFile.close()
    

def findPYSMELLDICT(filename):
    pathParts = _getPathParts(filename)[:-1]
    PYSMELLDICT = {}
    while pathParts:
        directory = os.path.join(*pathParts)
        for tagsfile in fnmatch.filter(listdir(directory), 'PYSMELLTAGS.*'):
            tryReadPYSMELLDICT(directory, tagsfile, PYSMELLDICT)
        tagsPath = os.path.join(directory, 'PYSMELLTAGS')
        if os.path.exists(tagsPath):
            tryReadPYSMELLDICT(directory, 'PYSMELLTAGS', PYSMELLDICT)
            break
        pathParts.pop()
    else:
        return None
    return PYSMELLDICT
            

def _getPathParts(path):
    "given a full path, return its components without the extension"
    head, tail = os.path.split(path[:-3])
    pathParts = [tail]
    while head and tail:
        head, tail = os.path.split(head)
        if tail:
            pathParts.append(tail)
    if head:
        pathParts.append(head)
    pathParts.reverse()
    return pathParts


def debug(vim, msg):
    if vim is None: return
    if int(vim.eval('g:pysmell_debug')):
        debBuffer = None
        for b in vim.buffers:
            if b.name.endswith('DEBUG'):
                debBuffer = b
        debBuffer.append(msg)


def inferModule(chain, AST, lineNo):
    imports = getImports(AST)
    fullModuleParts = []
    valid = False
    for part in chain.split('.'):
        if part in imports:
            fullModuleParts.append(imports[part])
            valid = True
        else:
            fullModuleParts.append(part)
    if valid:
        return '.'.join(fullModuleParts)
    return None
    

funcCellRE = re.compile(r'(.+)\(.*\)')
def inferInstance(fullPath, AST, lineNo, var, PYSMELLDICT):
    names, klasses = getNames(AST)
    assignment = names.get(var, None)
    klass = None
    parents = []
    if assignment:
        possibleMatch = funcCellRE.match(assignment)
        if possibleMatch:
            klass = possibleMatch.groups(1)[0]
            if klass in klasses:
                path, filename = os.path.split(fullPath)
                packages = findRootPackageList(path, filename)
                if packages:
                    packagesStr = (".".join(packages)) + "."
                else:
                    packagesStr = ""
                klass = "%s%s.%s" % (packagesStr, filename[:-3], klass)
            else:
                klass = _qualify(names.get(klass, klass), PYSMELLDICT)
            parents = PYSMELLDICT['CLASSES'].get(klass, {'bases': []})['bases']

    return klass, parents


def _qualify(thing, PYSMELLDICT):
    if thing in PYSMELLDICT['POINTERS']:
        return PYSMELLDICT['POINTERS'][thing]
    else:
        for pointer in PYSMELLDICT['POINTERS']:
            if pointer.endswith('*') and thing.startswith(pointer[:-2]):
                return '%s.%s' % (PYSMELLDICT['POINTERS'][pointer][:-2], thing.split('.', 1)[-1])
    return thing

def inferClass(fullPath, AST, origLineNo, PYSMELLDICT, vim=None):
    klass, parents = getClassAndParents(AST, origLineNo)

    # replace POINTERS with their full reference
    for index, parent in enumerate(parents[:]):
        parents[index] = _qualify(parent, PYSMELLDICT)

    pathParts = _getPathParts(fullPath)
    fullKlass = klass
    while pathParts:
        fullKlass = "%s.%s" % (pathParts.pop(), fullKlass)
        if fullKlass in PYSMELLDICT['CLASSES'].keys():
            break
    else:
        # we don't know about this class, look in the file system
        path, filename = os.path.split(fullPath)
        packages = findRootPackageList(path, filename)
        if packages:
            packagesStr = (".".join(packages)) + "."
        else:
            packagesStr = ""
        fullKlass = "%s%s.%s" % (packagesStr, filename[:-3], klass)
        
    return fullKlass, parents


DELIMITERS = " ()[]{}'\"<>,/-=+*:%^|!@`;"

def getChain(line):
    "get the last chain of property accesses, ie some.thing.other.bother"
    chain = []
    for c in reversed(line):
        if c in DELIMITERS:
            break
        chain.append(c)
    return ''.join(reversed(chain))


class Types(object):
    TOPLEVEL = 'TOPLEVEL'
    FUNCTION = 'FUNCTION'
    METHOD = 'METHOD'
    MODULE = 'MODULE'
    INSTANCE = 'INSTANCE'


class CompletionOptions(object):
    def __init__(self, compType, **kwargs):
        self.compType = compType
        self.extra = kwargs

    def __getattr__(self, item):
        return self.extra[item]
        
    def __eq__(self, other):
        return (isinstance(other, CompletionOptions)
                and self.compType == other.compType and self.extra == other.extra)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return repr(self.compType) + 'with extra: ' + repr(self.extra)
        

def detectCompletionType(fullPath, origSource, lineNo, origCol, base, PYSMELLDICT, update=True):
    """
    Return a CompletionOptions instance describing the type of the completion, along with extra parameters.
    
    args: fullPath -> The full path and filename of the file that is edited
          origSource -> The source of the edited file (it's probably not saved)
          lineNo -> The line number the cursor is in, 1-based
          origCol -> The column number the cursor is in, 0-based
          base -> The string that will be replaced when the completion is inserted
          PYSMELLDICT -> The loaded PYSMELLDICT

    Note that Vim deletes the "base" when a completion is requested so extra trickery must be performed to get it from the source.

    """
    AST = getSafeTree(origSource, lineNo)
    if update:
        currentDict = analyzeFile(fullPath, AST)
        if currentDict is not None:
            updatePySmellDict(PYSMELLDICT, currentDict)
    origLineText = origSource.splitlines()[lineNo - 1] # lineNo is 1 based
    leftSide, rightSide = origLineText[:origCol], origLineText[origCol:]
    leftSideStripped = leftSide.lstrip()

    isImportCompletion = (leftSideStripped.startswith("from ") or leftSideStripped.startswith("import "))
    if isImportCompletion:
        module = leftSideStripped.split(" ")[1]
        if "." in module and " import " not in leftSideStripped:
            module, _ = module.rsplit(".", 1)
        showMembers = False
        if " import " in leftSide:
            showMembers = True
        return CompletionOptions(Types.MODULE, module=module, showMembers=showMembers)

    isAttrLookup = "." in leftSide and not isImportCompletion
    isArgCompletion = base.endswith('(') and leftSide.endswith(base)

    if isArgCompletion:
        rindex = None
        if rightSide.startswith(')'):
            rindex = -1
        funcName = None
        lindex = leftSide.rfind('.') + 1 #rfind will return -1, so with +1 it will be zero
        funcName = leftSide[lindex:-1].lstrip()
        if isAttrLookup:
            return CompletionOptions(Types.METHOD, parents=[], klass=None, name=funcName, rindex=rindex)
        else:
            return CompletionOptions(Types.FUNCTION, name=funcName, rindex=rindex)

    if isAttrLookup and AST is not None:
        var = leftSideStripped[:leftSideStripped.rindex('.')]
        isClassLookup = var == 'self'
        if isClassLookup:
            klass, parents = inferClass(fullPath, AST, lineNo, PYSMELLDICT)
            return CompletionOptions(Types.INSTANCE, klass=klass, parents=parents)
        else:
            chain = getChain(leftSideStripped) # strip dot
            if base and chain.endswith(base):
                chain = chain[:-len(base)]
            if chain.endswith('.'):
                chain = chain[:-1]
            possibleModule = inferModule(chain, AST, lineNo)
            if possibleModule is not None:
                return CompletionOptions(Types.MODULE, module=possibleModule, showMembers=True)
        klass, parents = inferInstance(fullPath, AST, lineNo, var, PYSMELLDICT)
        return CompletionOptions(Types.INSTANCE, klass=klass, parents=parents)
        

    return CompletionOptions(Types.TOPLEVEL)



def findCompletions(base, PYSMELLDICT, options, matcher=None):
    doesMatch = MATCHERS[matcher](base)
    compType = options.compType

    if compType is Types.MODULE:
        completions = _createModuleCompletions(PYSMELLDICT, options.module, options.showMembers)
    elif compType is Types.INSTANCE:
        completions = _createInstanceCompletionList(PYSMELLDICT, options.klass, options.parents)
    elif compType is Types.METHOD:
        completions = _createInstanceCompletionList(PYSMELLDICT, options.klass, options.parents)
        doesMatch = lambda word: word == options.name
    elif compType is Types.FUNCTION:
        completions = [_getCompForFunction(func, 'f') for func in PYSMELLDICT['FUNCTIONS']]
        doesMatch = lambda word: word == options.name
    elif compType is Types.TOPLEVEL:
        completions = _createTopLevelCompletionList(PYSMELLDICT)
        
    if base:
        filteredCompletions = [comp for comp in completions if doesMatch(comp['word'])]
    else:
        filteredCompletions = completions

    filteredCompletions.sort(sortCompletions)

    if filteredCompletions and compType in (Types.METHOD, Types.FUNCTION):
        #return the arg list instead
        oldComp = filteredCompletions[0]
        if oldComp['word'] == options.name:
            oldComp['word'] = oldComp['abbr'][:options.rindex]
    return filteredCompletions


def _createInstanceCompletionList(PYSMELLDICT, klass, parents):
    completions = []
    if klass: #if we know the class
        completions.extend(getCompletionsForClass(klass, parents, PYSMELLDICT))
    else: #just put everything
        for klass, klassDict in PYSMELLDICT['CLASSES'].items():
            addCompletionsForClass(klass, klassDict, completions)
    return completions


def _createTopLevelCompletionList(PYSMELLDICT):
    completions = []
    completions.extend(_getCompForConstant(word) for word in PYSMELLDICT['CONSTANTS'])
    completions.extend(_getCompForFunction(func, 'f') for func in PYSMELLDICT['FUNCTIONS'])
    completions.extend(_getCompForConstructor(klass, klassDict) for (klass, klassDict) in PYSMELLDICT['CLASSES'].items())
    return completions


def _createModuleCompletions(PYSMELLDICT, module, completeModuleMembers):
    completions = []
    splitModules = set()
    for reference in PYSMELLDICT['HIERARCHY']:
        if not reference.startswith(module): continue
        if reference == module: continue

        # like zip, but pad with None
        for mod, ref in map(None, module.split('.'), reference.split('.')):
            if mod != ref:
                splitModules.add(ref)
                break

    if completeModuleMembers:
        members = _createTopLevelCompletionList(PYSMELLDICT)
        completions.extend(comp for comp in members if comp["menu"] == module and not comp["word"].startswith("_"))
        pointers = []
        for pointer in PYSMELLDICT['POINTERS']:
            if pointer.startswith(module) and '.' not in pointer[len(module)+1:]:
                basename = pointer[len(module)+1:]
                if pointer.endswith(".*"):
                    otherModule = PYSMELLDICT['POINTERS'][pointer][:-2] # remove .*
                    completions.extend(_createModuleCompletions(PYSMELLDICT, otherModule, True))
                else:
                    splitModules.add(basename)
                
                
    completions.extend(dict(word=name, kind="t", dup="1") for name in splitModules)
    return completions


def getCompletionsForClass(klass, parents, PYSMELLDICT):
        klassDict = PYSMELLDICT['CLASSES'].get(klass, None)
        completions = []
        ancestorList = []
        nonBuiltinParents = [p for p in parents if not hasattr(__builtin__, p)]
        if klassDict is None and not nonBuiltinParents:
            return completions
        elif klassDict is None and nonBuiltinParents:
            for anc in nonBuiltinParents:
                _findAllParents(anc, PYSMELLDICT['CLASSES'], ancestorList)
                ancDict = PYSMELLDICT['CLASSES'].get(anc, None)
                if ancDict is None: continue
                addCompletionsForClass(anc, ancDict, completions)
            for anc in ancestorList:
                ancDict = PYSMELLDICT['CLASSES'].get(anc, None)
                if ancDict is None: continue
                addCompletionsForClass(anc, ancDict, completions)
            return completions
            
        _findAllParents(klass, PYSMELLDICT['CLASSES'], ancestorList)
        addCompletionsForClass(klass, klassDict, completions)
        for anc in ancestorList:
            ancDict = PYSMELLDICT['CLASSES'].get(anc, None)
            if ancDict is None: continue
            addCompletionsForClass(anc, ancDict, completions)
        return completions


def addCompletionsForClass(klass, klassDict, completions):
    module, klassName = klass.rsplit('.', 1)
    completions.extend([dict(word=prop, kind='m', dup='1', menu='%s:%s' %
                    (module, klassName)) for prop in klassDict['properties']])
    completions.extend([_getCompForFunction(func, 'm', module='%s:%s' % (module,
                klassName)) for func in klassDict['methods']])


def _findAllParents(klass, classesDICT, ancList):
    klassDict = classesDICT.get(klass, None)
    if klassDict is None: return
    for anc in klassDict['bases']:
        if hasattr(__builtin__, anc): continue
        ancList.append(anc)
        _findAllParents(anc, classesDICT, ancList)


def _getCompForConstant(word):
    module, const = word.rsplit('.', 1)
    return dict(word=const, kind='d', menu=module, dup='1')


def _getCompForFunction(func, kind, module=None):
    if module is None:
        module, funcName = func[0].rsplit('.', 1)
    else:
        funcName = func[0]
    return dict(word=funcName, kind=kind, menu=module, dup='1',
                            abbr='%s(%s)' % (funcName, _argsList(func[1])))

def _getCompForConstructor(klass, klassDict):
    module, klassName = klass.rsplit('.', 1)
    return dict(word=klassName, kind='t', menu=module, dup='1', abbr='%s(%s)' % (klassName, _argsList(klassDict['constructor'])))

def _argsList(l):
     return ', '.join([str(arg) for arg in l])

def sortCompletions(comp1, comp2):
    word1, word2 = comp1['word'], comp2['word']
    return _sortCompletions(word1, word2)

def _sortCompletions(word1, word2):
    if word1.startswith('_'):
        return _sortCompletions(word1[1:], word2) + 2
    if word2.startswith('_'):
        return _sortCompletions(word1, word2[1:]) - 2
    return cmp(word1, word2)

########NEW FILE########
__FILENAME__ = matchers
# matchers.py
# Original author: Krzysiek Goj
# Copyright (C) 2008 Orestis Markou
# All rights reserved
# E-mail: orestis@orestis.gr

# http://orestis.gr

# Released subject to the BSD License 

import re
try:
    all
except:
     def all(iterable):
         for element in iterable:
             if not element:
                 return False
         return True

def matchCaseInsensitively(base):
    return lambda comp: comp.lower().startswith(base.lower())

def matchCaseSensitively(base):
    return lambda comp: comp.startswith(base)

def camelGroups(word):
    groups = []
    rest = word
    while rest:
        i, limit = 0, len(rest)
        while i < limit:
            suspect = rest[1:i+1]
            if i and not (suspect.islower() and suspect.isalnum()):
                break
            i += 1
        part, rest = rest[:i], rest[i:]
        groups.append(part)
    return groups

def matchCamelCasedPrecise(base):
    baseGr = camelGroups(base)
    baseLen = len(baseGr)
    def check(comp):
        compGr = camelGroups(comp)
        return baseLen <= len(compGr) and all(matchCaseSensitively(bg)(cg) for bg, cg in zip(baseGr, compGr))
    return check

def matchCamelCased(base):
    baseGr = camelGroups(base)
    baseLen = len(baseGr)
    def check(comp):
        compGr = camelGroups(comp)
        return baseLen <= len(compGr) and all(matchCaseInsensitively(bg)(cg) for bg, cg in zip(baseGr, compGr))
    return check

def matchSmartass(base):
    rev_base_letters = list(reversed(base.lower()))
    def check(comp):
        stack = rev_base_letters[:]
        for group in camelGroups(comp):
            lowered = group.lower()
            while True:
                if lowered and stack:
                    if lowered.startswith(stack[-1]):
                        stack.pop()
                    lowered = lowered[1:]
                else:
                    break
        return not stack
    return check

def matchFuzzyCS(base):
    regex = re.compile('.*'.join([] + list(base) + []))
    return lambda comp: bool(regex.match(comp))

def matchFuzzyCI(base):
    regex = re.compile('.*'.join([] + list(base) + []), re.IGNORECASE)
    return lambda comp: bool(regex.match(comp))


class MatchDict(object):
    _MATCHERS = {
        'case-sensitive': matchCaseSensitively,
        'case-insensitive': matchCaseInsensitively,
        'camel-case': matchCamelCased,
        'camel-case-sensitive': matchCamelCasedPrecise,
        'smartass': matchSmartass,
        'fuzzy-ci': matchFuzzyCI,
        'fuzzy-cs': matchFuzzyCS,
    }

    def __getitem__(self, item):
        return self._MATCHERS.get(item, matchCaseInsensitively)

MATCHERS = MatchDict()

########NEW FILE########
__FILENAME__ = tags
#!/usr/bin/env python
# pysmell.py
# Statically analyze python code and generate PYSMELLTAGS file
# Copyright (C) 2008 Orestis Markou
# All rights reserved
# E-mail: orestis@orestis.gr

# http://orestis.gr

# Released subject to the BSD License 

import os
import sys
from textwrap import dedent
from pprint import pprint

from pysmell.codefinder import ModuleDict, processFile
from pysmell.idehelper import findRootPackageList

from pysmell import argparse
 
version = __import__('pysmell').__version__

source = """
class Aclass(object):
    def do_stuff(self):
        a = 1
        print a
        self.bar = 42

    def do_other_stuff(self):
        self.bar().do_stuff()
        self.baz.do_stuff()

def test(aname):
    aname.do_stuff()
    aname.do_other_stuff()
"""


def generateClassTag(modules, output):
    p = os.path.abspath(output)
    f = open(p, 'w')
    pprint(modules, f, width=100)
    f.close()


def process(filesOrDirectories, excluded, inputDict=None, verbose=False):
    """
    Visit every package in ``filesOrDirectories`` and return a ModuleDict for everything,
    that can be used to generate a PYSMELLTAGS file.

    filesOrDirectories: list of paths to process. They can either be directories or files.
                        Directories can either be packages or they can contain packages.

    excluded: list of directories to exclude (eg. ['test', '.svn'])

    inputDict: a ModuleDict instance to update with any new or updated python
               namespaces.

    verbose: flag that turns on verbose logging (print what is going on).

    returns: The generated ModuleDict instance for the directories provided in
             ``filesOrDirectories``.
    """
    modules = ModuleDict()
    if inputDict:
        modules.update(inputDict)
    for rootPackage in filesOrDirectories:
        if os.path.isdir(rootPackage):
            for path, dirs, files in os.walk(rootPackage):
                for exc in excluded:
                    if exc in dirs:
                        if verbose:
                            print 'removing', exc, 'in', path
                        dirs.remove(exc)
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    #path here is relative, make it absolute
                    absPath = os.path.abspath(path)
                    if verbose:
                        print 'processing', absPath, f
                    newmodules = processFile(f, absPath)
                    modules.update(newmodules)
        else: # single file
            filename = rootPackage
            absPath, filename = os.path.split(filename)
            if not absPath:
                absPath = os.path.abspath(".")
            else:
                absPath = os.path.abspath(absPath)
                
            #path here is absolute
            if verbose:
                print 'processing', absPath, filename
            newmodules = processFile(filename, absPath)
            modules.update(newmodules)
            
    return modules


def main():
    description = dedent("""\
        Generate a PYSMELLTAGS file with information about the
        Python code contained in the specified packages (recursively). This file is
        then used to provide autocompletion for various IDEs and editors that
        support it. """)
    parser = argparse.ArgumentParser(description=description, version=version, prog='pysmell')
    parser.add_argument('fileList', metavar='package', type=str, nargs='+',
        help='The packages to be analysed.')
    parser.add_argument('-x', '--exclude', metavar='package', nargs='*', type=str, default=[],
        help=dedent("""Will not analyze files in directories that match the
        argument. Useful for excluding tests or version control directories."""))
    parser.add_argument('-o', '--output', default='PYSMELLTAGS',
        help="File to write the tags to")
    parser.add_argument('-i', '--input',
        help="Preexisting tags file to update")
    parser.add_argument('-t', '--timing', action='store_true',
        help="Will print timing information")
    parser.add_argument('-d', '--debug', action='store_true',
        help="Verbose mode; useful for debugging")
    args = parser.parse_args()
    fileList = args.fileList
    excluded = args.exclude
    timing = args.timing
    output = args.output
    verbose = args.debug
    inputFile = args.input
    if inputFile:
        try:
            inputDict = eval(file(inputFile).read())
        except:
            print >> sys.stderr, "Could not process %s - is it a PYSMELLTAGS file?" % inputFile
            sys.exit(3)
    else:
        inputDict = None


    if timing:
        import time
        start = time.clock()
    if verbose:
        print 'processing', fileList
        print 'ignoring', excluded
    modules = process(fileList, excluded, inputDict=inputDict, verbose=verbose)
    generateClassTag(modules, output)
    if timing:
        took = time.clock() - start
        print 'took %f seconds' % took


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = textmate
import os
import sys
from pysmell import idehelper
from pysmell import tags as tags_module
from pysmell import tm_dialog


#tm_support_path = os.environ['TM_SUPPORT_PATH'] + '/lib'
#if tm_support_path not in sys.path:
    #sys.path.insert(0, tm_support_path)


def write(word):
    sys.stdout.write(word)


def tags(projectDir):
    args = ['pysmell', projectDir, '-o', os.path.join(projectDir, 'PYSMELLTAGS')]
    sys.argv = args
    tags_module.main()
    write('PYSMELLTAGS created in %s' % projectDir)

TOOLTIP = 206

def main():
    cur_file = os.environ.get("TM_FILEPATH")
    line_no = int(os.environ.get("TM_LINE_NUMBER"))
    cur_col = int(os.environ.get("TM_LINE_INDEX"))
    result = _main(cur_file, line_no, cur_col)
    if result is not None:
        sys.exit(result)

def _main(cur_file, line_no, cur_col):
    if not cur_file:
        write('No filename - is the file saved?')
        return TOOLTIP
    source = sys.stdin.read()

    PYSMELLDICT = idehelper.findPYSMELLDICT(cur_file)
    if PYSMELLDICT is None:
        write('No PYSMELLTAGS found - you have to generate one.')
        return TOOLTIP
    line = source.splitlines()[line_no - 1]
    index = idehelper.findBase(line, cur_col)
    base = line[index:cur_col]

    options = idehelper.detectCompletionType(cur_file, source, line_no, cur_col, base, PYSMELLDICT)
    completions = idehelper.findCompletions(base, PYSMELLDICT, options)

    if not completions:
        write('No completions found')
        return TOOLTIP
    if len(completions) == 1:
        new_word = completions[0]['word']
        write(new_word[len(base):])
    elif len(completions) > 1:
        dialogTuples = [
            (
              "%s - %s" % (comp.get('abbr', comp['word']), comp.get('menu', '')),
              index)
            for index, comp in enumerate(completions)
        ]
        try:
            compIndex = tm_dialog.menu(dialogTuples)
        except Exception, e:
            import traceback
            write(traceback.format_exc(e))
            return TOOLTIP
        if compIndex is not None:
            write(completions[compIndex]['word'][len(base):])


########NEW FILE########
__FILENAME__ = tm_dialog
from types import NoneType
import sys
import os
import subprocess

tm_support_path = os.environ['TM_SUPPORT_PATH'] + '/lib'
if tm_support_path not in sys.path:
    sys.path.insert(0, tm_support_path)

from tm_helpers import to_plist, from_plist

dialog = os.environ["DIALOG"]
try:
    all
except:
    def all(items):
        for item in items:
            if not item:
                return False
        return True

def item(val):
    if isinstance(val, basestring):
        return {"title": val}
    if isinstance(val, tuple):
        return {"title": val[0]}
    elif val is None:
        return {"separator": 1}

def all_are_instance(it, typ):
    return all([isinstance(i, typ) for i in it])

def menu(options):
    """ Accepts a list and causes TextMate to show an inline menu.
    
    If options is a list of strings, will return the selected index.
    
    If options is a list of (key, value) tuples, will display "key" and 
    return "value". Note that we don't use dicts, so that key-value options
    can be ordered. If you want to use a dict, try dict.items().
    
    In either input case, a list item with value `None` causes tm_dialog to
    display a separator for that index.
    """
    hashed_options = False
    if not options:
        return None
    menu = dict(menuItems=[item(thing) for thing in options])
    if all_are_instance(options, (tuple, NoneType)):
        hashed_options = True
    plist = to_plist(menu)
    proc = subprocess.Popen([dialog, '-u'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    proc.stdin.write(plist)
    output, _ = proc.communicate()
    result = from_plist(output)
    if not 'selectedIndex' in result:
        return None
    index = int(result['selectedIndex'])
    if hashed_options:
        return options[index][1]
    return options[index]

########NEW FILE########
__FILENAME__ = vimhelper
# vimhelper.py
# Copyright (C) 2008 Orestis Markou
# All rights reserved
# E-mail: orestis@orestis.gr

# http://orestis.gr

# Released subject to the BSD License 
def findWord(vim, origCol, origLine):
    # vim moves the cursor and deletes the text by the time we are called
    # so we need the original position and the original line...
    index = origCol
    while index > 0:
        index -= 1
        if origLine[index] == ' ':
            index +=1
            break
    cword = origLine[index:origCol]
    return cword

    

########NEW FILE########
__FILENAME__ = ModuleA
def TopLevelFunction(arg1, arg2):
    class InnerClassB(object):
        def anotherMethod(self, c):
            pass
    return 'something'

CONSTANT = 123

class ClassA(object):
    classPropertyA = 4
    classPropertyB = 5

    def __init__(self):
        self.propertyA = 1
        self.propertyB = 2


    @property
    def propertyC(self):
        return 3

    def methodA(self, argA, argB, *args, **kwargs):
        self.propertyD = 4
        class InnerClass(object):
            def innerClassMethod(self):
                self.aHiddenProperty = 'dont bother with inner classes'
                pass
        def innerFunction(sth, sthelse):
            return 'result'
        return 'A'


class ChildClassA(ClassA, object):
    'a class docstring, imagine that'
    def __init__(self, conArg):
        self.extraProperty = 45

    def extraMethod(self):
        "i have a docstring"
        pass

########NEW FILE########
__FILENAME__ = ModuleC
NESTED = True

########NEW FILE########
__FILENAME__ = standalone
NOPACKAGE = 'Cool'

########NEW FILE########
__FILENAME__ = test_codefinder
import os
import unittest
from textwrap import dedent
import compiler
from pprint import pformat

from pysmell.codefinder import CodeFinder, getClassAndParents, getNames, ModuleDict, findPackage, analyzeFile, getSafeTree
from pysmell.codefinder import argToStr

class ModuleDictTest(unittest.TestCase):
    def testUpdate(self):
        total = ModuleDict()
        total.enterModule('mod1')
        total.enterClass('cls1', [], 'doc1')
        total.enterModule('mod2')
        total.enterClass('cls2', [], 'doc2')

        self.assertEquals(pformat(total), pformat(total._modules))

        md1 = ModuleDict()
        md1.enterModule('mod1')
        md1.enterClass('cls1', [], 'doc1')

        md2 = ModuleDict()
        md2.enterModule('mod2')
        md2.enterClass('cls2', [], 'doc2')

        md3 = ModuleDict()
        md3.update(md1)
        self.assertEquals(pformat(md3), pformat(md1))
        md3.update(md2)
        self.assertEquals(pformat(md3), pformat(total))
        md3.update(None)
        self.assertEquals(pformat(md3), pformat(total))

    def testAddPointer(self):
        md = ModuleDict()
        md.addPointer('something', 'other')
        self.assertEquals(md['POINTERS'], {'something': 'other'})


class CodeFinderTest(unittest.TestCase):

    def getModule(self, source):
        tree = compiler.parse(dedent(source))
        codeFinder = CodeFinder()
        codeFinder.module = 'TestModule'
        codeFinder.package = 'TestPackage'
        compiler.walk(tree, codeFinder)
        try:
            return eval(pformat(codeFinder.modules))
        except:
            print 'EXCEPTION WHEN EVALING:'
            print pformat(codeFinder.modules)
            print '=-' * 20
            raise


    def testOnlyPackage(self):
        source = """
        class A(object):
            pass
        """
        tree = compiler.parse(dedent(source))
        codeFinder = CodeFinder()
        codeFinder.package = 'TestPackage'
        codeFinder.module = '__init__'
        compiler.walk(tree, codeFinder)
        expected = {'CLASSES': {'TestPackage.A': dict(docstring='', bases=['object'], constructor=[], methods=[], properties=[])},
            'FUNCTIONS': [], 'CONSTANTS': [], 'POINTERS': {}, 'HIERARCHY': ['TestPackage']}
        actual = eval(pformat(codeFinder.modules))
        self.assertEquals(actual, expected)


    def assertClasses(self, moduleDict, expected):
        self.assertEquals(moduleDict['CLASSES'], expected)


    def testSimpleClass(self):
        out = self.getModule("""
        class A(object):
            pass
        """)
        expected = {'TestPackage.TestModule.A': dict(bases=['object'], properties=[], methods=[], constructor=[], docstring='')}
        self.assertClasses(out, expected)


    def testClassParent(self):
        out = self.getModule("""
        class Parent(list):
            pass
        class A(Parent):
            pass
        """)
        expected = {'TestPackage.TestModule.A': dict(bases=['TestPackage.TestModule.Parent'], properties=[], methods=[], constructor=[], docstring=''), 'TestPackage.TestModule.Parent': dict(bases=['list'], properties=[], methods=[], constructor=[], docstring='')}
        self.assertClasses(out, expected)


    def testAdvancedDefaultArguments(self):
        out = self.getModule("""
        def function(a=1, b=2, c=None, d=4, e='string', f=Name, g={}):
            pass
        """)
        expected = ('TestPackage.TestModule.function', ['a=1', 'b=2', 'c=None', 'd=4', "e='string'", 'f=Name', 'g={}'], '')
        self.assertEquals(out['FUNCTIONS'], [expected])


    def testOldStyleDecoratorProperties(self):
        out = self.getModule("""
        class A:
            def __a(self):
                pass
            a = property(__a)
        """)
        expected = {'TestPackage.TestModule.A': dict(bases=[], properties=['a'], methods=[('__a', [], '')], constructor=[], docstring='')}
        self.assertClasses(out, expected)


    def assertNamesIsHandled(self, name):
        try:
            from sourcecodegen.generation import ModuleSourceCodeGenerator
            tree = compiler.parse(name)
            source = ModuleSourceCodeGenerator(tree).getSourceCode()[:-1] #strip newline
            if source != name:
                print 'pycodegen: %s != %s' % (source, name)
        except ImportError:
            pass
        out = self.getModule("""
        def f(a=%s):
            pass
        """ % name)
        self.assertEquals(out['FUNCTIONS'], [('TestPackage.TestModule.f', ['a=%s' % name], '')])


    def testNames(self):
        self.assertNamesIsHandled('A.B.C(1)')
        self.assertNamesIsHandled('A.B.C()')
        self.assertNamesIsHandled('A.B.C')
        self.assertNamesIsHandled('{a: b, c: d}')
        self.assertNamesIsHandled('(a, b, c)')
        self.assertNamesIsHandled('[a, b, c]')
        self.assertNamesIsHandled('lambda a: (c, b)')
        self.assertNamesIsHandled("name[1:]")
        self.assertNamesIsHandled("name[1:2]")
        self.assertNamesIsHandled("lambda name: name[:1] != '_'")
        self.assertNamesIsHandled("-180")
        self.assertNamesIsHandled("not x.ishidden()")
        self.assertNamesIsHandled("'='+repr(v)")
        self.assertNamesIsHandled("1L")
        self.assertNamesIsHandled("1123.001")
        self.assertNamesIsHandled("Some(opts=None)")
        self.assertNamesIsHandled("s%s")
        self.assertNamesIsHandled("s|s|b")
        self.assertNamesIsHandled("s-s")
        self.assertNamesIsHandled("''")
        self.assertNamesIsHandled("'123'")
        self.assertNamesIsHandled("a or b")
        self.assertNamesIsHandled("a and b")
        self.assertNamesIsHandled("10*180")
        self.assertNamesIsHandled("10/180")
        self.assertNamesIsHandled("10**180")
        self.assertNamesIsHandled("10>>180")
        self.assertNamesIsHandled("10<<180")
        

    def testClassProperties(self):
        out = self.getModule("""
        class A(object):
            classprop = 1
            def __init__(self):
                self.plainprop = 2
                self.plainprop = 3
            @property
            def methodProp(self):
                pass
        """)
        expectedProps = ['classprop', 'plainprop', 'methodProp']
        self.assertEquals(out['CLASSES']['TestPackage.TestModule.A']['properties'], expectedProps)


    def testClassMethods(self):
        out = self.getModule("""
        class A(object):
            def method(self):
                'random docstring'
                pass
            def methodArgs(self, arg1, arg2):
                pass
            def methodTuple(self, (x, y)):
                pass
            def methodDefaultArgs(self, arg1, arg2=None):
                pass
            def methodStar(self, arg1, *args):
                pass
            def methodKW(self, arg1, **kwargs):
                pass
            def methodAll(self, arg1, *args, **kwargs):
                pass
            def methodReallyAll(self, arg1, arg2='a string', *args, **kwargs):
                pass
        """)
        expectedMethods = [('method', [], 'random docstring'),
                           ('methodArgs', ['arg1', 'arg2'], ''),
                           ('methodTuple', ['(x, y)'], ''),
                           ('methodDefaultArgs', ['arg1', 'arg2=None'], ''),
                           ('methodStar', ['arg1', '*args'], ''),
                           ('methodKW', ['arg1', '**kwargs'], ''),
                           ('methodAll', ['arg1', '*args', '**kwargs'], ''),
                           ('methodReallyAll', ['arg1', "arg2='a string'", '*args', '**kwargs'], ''),
                           ]
        self.assertEquals(out['CLASSES']['TestPackage.TestModule.A']['methods'], expectedMethods)


    def testTopLevelFunctions(self):
        out = self.getModule("""
        def TopFunction1(arg1, arg2=True, **spinach):
            'random docstring'
        def TopFunction2(arg1, arg2=False):
            'random docstring2'
        """)
        expectedFunctions = [('TestPackage.TestModule.TopFunction1', ['arg1', 'arg2=True', '**spinach'], 'random docstring'),
                             ('TestPackage.TestModule.TopFunction2', ['arg1', 'arg2=False'], 'random docstring2')]
        self.assertEquals(out['FUNCTIONS'], expectedFunctions)


    def testNestedStuff(self):
        out = self.getModule("""
        class A(object):
            def level1(self):
                class Level2(object):
                    pass
                def level2():
                    pass
                pass
            class InnerClass(object):
                def innerMethod(self):
                    pass
        """)
        self.assertEquals(len(out['CLASSES'].keys()), 1, 'should not count inner classes')
        self.assertEquals(out['CLASSES']['TestPackage.TestModule.A']['methods'], [('level1', [], '')])
        self.assertEquals(out['FUNCTIONS'], [])


    def testModuleConstants(self):
        out = self.getModule("""
        CONSTANT = 1
        """)
        self.assertEquals(out['CONSTANTS'], ['TestPackage.TestModule.CONSTANT'])


    def testArgToStr(self):
        self.assertEquals(argToStr('stuff'), 'stuff')
        self.assertEquals(argToStr(('ala', 'ma', 'kota')), '(ala, ma, kota)')
        self.assertEquals(argToStr((('x1', 'y1'), ('x2', 'y2'))), '((x1, y1), (x2, y2))')
        self.assertEquals(argToStr(('ala',)), '(ala,)')


    def testTrickyBases(self):
        "understand imports and generate the correct bases"
        out = self.getModule("""
            from TestPackage.AnotherModule import AnotherClass as Nyer
            from TestPackage.AnotherModule import AClass
            class A(Nyer, AClass):
                pass
        """)
        self.assertEquals(out['CLASSES']['TestPackage.TestModule.A'],
                        dict(constructor=[], methods=[], properties=[], docstring='',
                        bases=['TestPackage.AnotherModule.AnotherClass', 'TestPackage.AnotherModule.AClass'])
        )

    def testAbsoluteImports(self):
        "understand imports and generate the correct bases"
        out = self.getModule("""
            import TestPackage.AnotherModule
            import TestPackage as Hmer
            class A(TestPackage.AnotherModule.AClass, Hmer.AnotherModule.AnotherClass):
                pass
        """)
        self.assertEquals(out['CLASSES']['TestPackage.TestModule.A'],
                        dict(constructor=[], methods=[], properties=[], docstring='',
                        bases=['TestPackage.AnotherModule.AClass', 'TestPackage.AnotherModule.AnotherClass'])
        )

    def testImportedNames(self):
        out = self.getModule("""
            from somewhere.something import other as mother
            import somewhere.something as thing
        """)
        self.assertEquals(out['POINTERS'],
            {
                'TestPackage.TestModule.mother': 'somewhere.something.other',
                'TestPackage.TestModule.thing': 'somewhere.something',
            }
        )

    
    def testRelativeImports(self):
        import pysmell.codefinder
        oldExists = pysmell.codefinder.os.path.exists
        # monkeypatch relative.py into the path somewhere
        paths = []
        def mockExists(path):
            paths.append(path)
            return True

        pysmell.codefinder.os.path.exists = mockExists

        try:
            out = self.getModule("""
                import relative    
                from relative.removed import brother as bro
            """)
            self.assertEquals(out['POINTERS'],
                {
                    'TestPackage.TestModule.relative': 'TestPackage.relative',
                    'TestPackage.TestModule.bro': 'TestPackage.relative.removed.brother'
                }
            )
            expectedPaths = [
                os.path.join('__path__', 'relative'),
                os.path.join('__path__', 'relative', 'removed'),
            ]
            self.assertEquals(paths, expectedPaths)
        finally:
            pysmell.codefinder.os.path.exists = oldExists


    def testHierarchy(self):
        class MockNode(object):
            node = 1
        node = MockNode()
        codeFinder = CodeFinder()
        codeFinder.visit = lambda _: None

        codeFinder.package = 'TestPackage'
        codeFinder.module = '__init__'
        codeFinder.visitModule(node)

        codeFinder.module = 'Modulo'
        codeFinder.visitModule(node)

        codeFinder.package = 'TestPackage.Another'
        codeFinder.module = '__init__'
        codeFinder.visitModule(node)

        codeFinder.module = 'Moduli'
        codeFinder.visitModule(node)

        expected = [
            'TestPackage',
            'TestPackage.Modulo',
            'TestPackage.Another',
            'TestPackage.Another.Moduli',
        ]
        self.assertEquals(codeFinder.modules['HIERARCHY'], expected)
        

        

class InferencingTest(unittest.TestCase):
    def testInferSelfSimple(self):
        source = dedent("""\
            import something
            class AClass(object):
            \tdef amethod(self, other):
            \t\tother.do_something()
            \t\tself.

            \tdef another(self):
            \t\tpass
        """)
        klass, parents = getClassAndParents(getSafeTree(source, 5), 5)
        self.assertEquals(klass, 'AClass')
        self.assertEquals(parents, ['object'])


    def testInferParents(self):
        source = dedent("""\
            import something
            from something import father as stepfather
            class AClass(something.mother, stepfather):
                def amethod(self, other):
                    other.do_something()
                    self.

                def another(self):
                    pass
        """)
        klass, parents = getClassAndParents(getSafeTree(source, 6), 6)
        self.assertEquals(klass, 'AClass')
        self.assertEquals(parents, ['something.mother', 'something.father'])


    def testInferParentsTricky(self):
        source = dedent("""\
            from something.this import other as another
            class AClass(another.bother):
                def amethod(self, other):
                    other.do_something()
                    self.

                def another(self):
                    pass""")
        klass, parents = getClassAndParents(getSafeTree(source, 5), 5)
        self.assertEquals(klass, 'AClass')
        self.assertEquals(parents, ['something.this.other.bother'])


    def testInferSelfMultipleClasses(self):
        
        source = dedent("""\
            import something
            class AClass(object):
                def amethod(self, other):
                    other.do_something()
                    class Sneak(object):
                        def sth(self):
                            class EvenSneakier(object):
                                pass
                            pass
                    pass

                def another(self):
                    pass



            class BClass(object):
                def newmethod(self, something):
                    wibble = [i for i in self.a]
                    pass

                def newerMethod(self, somethingelse):
                    if Bugger:
                        self.ass
        """)
        
        self.assertEquals(getClassAndParents(getSafeTree(source, 1), 1)[0], None, 'no class yet!')
        for line in range(2, 5):
            klass, _ = getClassAndParents(getSafeTree(source, line), line)
            self.assertEquals(klass, 'AClass', 'wrong class %s in line %d' % (klass, line))

        for line in range(5, 7):
            klass, _ = getClassAndParents(getSafeTree(source, line), line)
            self.assertEquals(klass, 'Sneak', 'wrong class %s in line %d' % (klass, line))

        for line in range(7, 9):
            klass, _ = getClassAndParents(getSafeTree(source, line), line)
            self.assertEquals(klass, 'EvenSneakier', 'wrong class %s in line %d' % (klass, line))

        line = 9
        klass, _ = getClassAndParents(getSafeTree(source, line), line)
        self.assertEquals(klass, 'Sneak', 'wrong class %s in line %d' % (klass, line))

        for line in range(10, 17):
            klass, _ = getClassAndParents(getSafeTree(source, line), line)
            self.assertEquals(klass, 'AClass', 'wrong class %s in line %d' % (klass, line))

        for line in range(17, 51):
            klass, _ = getClassAndParents(getSafeTree(source, line), line)
            self.assertEquals(klass, 'BClass', 'wrong class %s in line %d' % (klass, line))


    def testGetNames(self):
        source = dedent("""\
            from something import Class

            a = Class()

            class D(object):
                pass

        """).replace('\n', '\r\n')

        expectedNames = {'Class': 'something.Class', 'a': 'Class()'}
        self.assertEquals(getNames(getSafeTree(source, 3)), (expectedNames, ['D']))


    def testAnalyzeFile(self):
        path = os.path.abspath('File.py')
        source = dedent("""\
            CONSTANT = 1
        """)
        expectedDict = ModuleDict()
        expectedDict.enterModule('File')
        expectedDict.addProperty(None, 'CONSTANT')
        outDict = analyzeFile(path, getSafeTree(source, 1))
        self.assertEquals(outDict, expectedDict, '%r != %r' % (outDict._modules, expectedDict._modules))

    

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_completions
import unittest
from textwrap import dedent
import os

from pysmell.idehelper import findCompletions, CompletionOptions, Types


def compMeth(name, klass):
    return dict(word=name, abbr='%s()' % name, kind='m', menu='Module:%s' % klass, dup='1')
def compFunc(name, args=''):
    return dict(word=name, abbr='%s(%s)' % (name, args), kind='f', menu='Module', dup='1')
def compConst(name):
    return dict(word=name, kind='d', menu='Module', dup='1')
def compProp(name, klass):
    return dict(word=name, kind='m', menu='Module:%s' % klass, dup='1')
def compClass(name):
    return dict(word=name, abbr='%s()' % name,  kind='t', menu='Module', dup='1')

class CompletionTest(unittest.TestCase):
    def setUp(self):
        self.pysmelldict = {
                'CONSTANTS' : ['Module.aconstant', 'Module.bconst'],
                'FUNCTIONS' : [('Module.a', [], ''), ('Module.arg', [], ''), ('Module.b', ['arg1', 'arg2'], '')],
                'CLASSES' : {
                    'Module.aClass': {
                        'constructor': [],
                        'bases': ['object', 'ForeignModule.alien'],
                        'properties': ['aprop', 'bprop'],
                        'methods': [('am', [], ''), ('bm', [], ())]
                    },
                    'Module.bClass': {
                        'constructor': [],
                        'bases': ['Module.aClass'],
                        'properties': ['cprop', 'dprop'],
                        'methods': [('cm', [], ''), ('dm', [], ())]
                    }
                },
                'HIERARCHY' : ['Module'],
                'POINTERS': {}
            }
        self.nestedDict = {
                'CONSTANTS' : [],
                'FUNCTIONS' : [],
                'CLASSES' : {
                    'Nested.Package.Module.Class': {
                        'constructor': [],
                        'bases': [],
                        'properties': ['cprop'],
                        'methods': []
                    }
                    
                },
                'HIERARCHY' : ['Nested.Package.Module'],
                'POINTERS' : {'Nested.Package.Module.Something': 'dontcare'},
        }
        self.complicatedDict = {
                'CONSTANTS' : ['A.CONST_A', 'B.CONST_B', 'B._HIDDEN', 'C.CONST_C'],
                'FUNCTIONS' : [],
                'CLASSES' : {},
                'HIERARCHY' : ['A', 'B', 'C'],
                'POINTERS' : {
                    'A.*': 'B.*',
                    'A.THING': 'C.CONST_C',
                },
        }


    def testCompletions(self):
        options = CompletionOptions(Types.TOPLEVEL)
        compls = findCompletions('b', self.pysmelldict, options)
        expected = [compFunc('b', 'arg1, arg2'), compClass('bClass'), compConst('bconst')]
        self.assertEquals(compls, expected)


    def testCompleteMembers(self):
        options = CompletionOptions(Types.INSTANCE, klass=None, parents=[])
        compls = findCompletions('a', self.pysmelldict, options)
        expected = [compMeth('am', 'aClass'), compProp('aprop', 'aClass')]
        self.assertEquals(compls, expected)


    def testCompleteArgumentListsPropRightParen(self):
        options = CompletionOptions(Types.METHOD, klass=None, parents=[], name='bm', rindex=-1)
        compls = findCompletions('bm(', self.pysmelldict, options)
        orig = compMeth('bm', 'aClass')
        orig['word'] = orig['abbr'][:-1]
        self.assertEquals(compls, [orig])

        
    def testCompleteArgumentListsProp(self):
        options = CompletionOptions(Types.METHOD, klass=None, parents=[], name='bm', rindex=None)
        compls = findCompletions('bm(', self.pysmelldict, options)
        orig = compMeth('bm', 'aClass')
        orig['word'] = orig['abbr']
        self.assertEquals(compls, [orig])
        

    def testCompleteArgumentListsRightParen(self):
        options = CompletionOptions(Types.FUNCTION, klass=None, parents=[], name='b', rindex=-1)
        compls = findCompletions('b(', self.pysmelldict, options)
        orig = compFunc('b', 'arg1, arg2')
        orig['word'] = orig['abbr'][:-1]
        self.assertEquals(compls, [orig])


    def testCompleteArgumentLists(self):
        options = CompletionOptions(Types.FUNCTION, klass=None, parents=[], name='b', rindex=None)
        compls = findCompletions('b(', self.pysmelldict, options)
        orig = compFunc('b', 'arg1, arg2')
        orig['word'] = orig['abbr']
        self.assertEquals(compls, [orig])


    def testCompleteWithSelfInfer(self):
        options = CompletionOptions(Types.INSTANCE, klass='Module.aClass', parents=[])
        compls = findCompletions('', self.pysmelldict, options)
        expected = [compMeth('am', 'aClass'), compProp('aprop', 'aClass'),
                    compMeth('bm', 'aClass'), compProp('bprop', 'aClass')]
        self.assertEquals(compls, expected)


    def testCompletionsWithPackages(self):
        options = CompletionOptions(Types.INSTANCE, klass='Nested.Package.Module.Class', parents=[])
        compls = findCompletions('', self.nestedDict, options)
        expected = [dict(word='cprop', kind='m', menu='Nested.Package.Module:Class', dup='1')]
        self.assertEquals(compls, expected)


    def testKnowAboutClassHierarchies(self):
        options = CompletionOptions(Types.INSTANCE, klass='Module.bClass', parents=[]) #possible error - why no parents
        compls = findCompletions('', self.pysmelldict, options)
        expected = [compMeth('am', 'aClass'), compProp('aprop', 'aClass'),
                    compMeth('bm', 'aClass'), compProp('bprop', 'aClass'),
                    compMeth('cm', 'bClass'), compProp('cprop', 'bClass'),
                    compMeth('dm', 'bClass'), compProp('dprop', 'bClass')]
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.INSTANCE, klass='Module.cClass', parents=['Module.bClass'])
        compls = findCompletions('', self.pysmelldict, options)
        expected = [compMeth('am', 'aClass'), compProp('aprop', 'aClass'),
                    compMeth('bm', 'aClass'), compProp('bprop', 'aClass'),
                    compMeth('cm', 'bClass'), compProp('cprop', 'bClass'),
                    compMeth('dm', 'bClass'), compProp('dprop', 'bClass')]
        self.assertEquals(compls, expected)


    def testModuleCompletion(self):
        options = CompletionOptions(Types.MODULE, module="Ne", showMembers=False)
        expected = [dict(word='Nested', kind='t', dup='1')]
        compls = findCompletions('Ne', self.nestedDict, options)
        self.assertEquals(compls, expected)
        
        options = CompletionOptions(Types.MODULE, module="Nested", showMembers=False)
        expected = [dict(word='Package', kind='t', dup='1')]
        compls = findCompletions('P', self.nestedDict, options)
        self.assertEquals(compls, expected)
        
        options = CompletionOptions(Types.MODULE, module="Nested.Package", showMembers=False)
        expected = [dict(word='Module', kind='t', dup='1')]
        compls = findCompletions('', self.nestedDict, options)
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.MODULE, module="Mo", showMembers=False)
        expected = [dict(word='Module', kind='t', dup='1')]
        compls = findCompletions('Mo', self.pysmelldict, options)
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.MODULE, module="Module", showMembers=False)
        expected = []
        compls = findCompletions('', self.pysmelldict, options)
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.MODULE, module="Nested.Package", showMembers=True)
        expected = [dict(word='Module', kind='t', dup='1')]
        compls = findCompletions('', self.nestedDict, options)
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        expected = [
            dict(word='Class', dup="1", kind="t", menu="Nested.Package.Module", abbr="Class()"),
            dict(word='Something', dup="1", kind="t"),
        ]
        compls = findCompletions('', self.nestedDict, options)
        self.assertEquals(compls, expected)

        options = CompletionOptions(Types.MODULE, module="A", showMembers=True)
        expected = [
            dict(word='CONST_A', kind='d', dup='1', menu='A'),
            dict(word='CONST_B', kind='d', dup='1', menu='B'),
            dict(word='THING', kind='t', dup='1')
        ]
        compls = findCompletions('', self.complicatedDict, options)
        self.assertEquals(compls, expected)




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_emacs

import os.path
from subprocess import Popen, PIPE
import sys
import unittest

emacs_test = os.path.join("Tests", "test_emacs.el")


class EmacsTest(unittest.TestCase):
    def testEmacsFunctionally(self):
        if sys.platform == 'win32':
            return
        try:
            pysmell_file = os.path.join("TestData", "PYSMELLTAGS")
            if (os.path.isfile(pysmell_file)):
                os.remove(pysmell_file)
            self.assertTrue(os.path.isfile(emacs_test), "Could not find emacs functional test")
            user = os.environ.get('USER', os.environ.get('username'))
            proc = Popen(["emacs",  "--batch", "--load", emacs_test, '--funcall', 'run-all-tests', '-u', user], stdout=PIPE, stderr=PIPE)
            result = proc.wait()

            if result != 0:
                msg = proc.stdout.read()
                self.fail(msg)
        finally:
            if (os.path.isfile(pysmell_file)):
                os.remove(pysmell_file)

if __name__ == "__main__":
    unittest.main()
            
            

    

########NEW FILE########
__FILENAME__ = test_idehelper
import copy
import os
import unittest
from textwrap import dedent

from pysmell.idehelper import (inferClass, detectCompletionType,
    CompletionOptions, findPYSMELLDICT, Types, findBase, getSafeTree)

NESTEDDICT = {
        'CONSTANTS' : [],
        'FUNCTIONS' : [],
        'CLASSES' : {
            'Nested.Package.Module.Class': {
                'constructor': [],
                'bases': [],
                'properties': ['cprop'],
                'methods': []
            }
            
        },
        'POINTERS' : {
            'Another.Thing': 'Nested.Package.Module.Class',
            'Star.*': 'Nested.Package.Module.*',
        
        },
        'HIERARCHY' : ['Nested.Package.Module'],
}


class IDEHelperTest(unittest.TestCase):
    def testFindPYSMELLDICT(self):
        # include everything that starts with PYSMELLTAGS
        if os.path.exists('PYSMELLTAGS'):
            os.remove('PYSMELLTAGS')
        import pysmell.idehelper
        oldTryReadPSD = pysmell.idehelper.tryReadPYSMELLDICT
        oldListDir = pysmell.idehelper.listdir
        TRPArgs = []
        def mockTRP(direct, fname, dictToUpdate):
            TRPArgs.append((direct, fname))
            dictToUpdate.update({'PYSMELLTAGS.django': {'django': True}}.get(fname, {}))

        listdirs = []
        def mockListDir(dirname):
            listdirs.append(dirname)
            return {'random': ['something'],
                    os.path.join('random', 'dirA'): ['PYSMELLTAGS.django'],
                }.get(dirname, [])

        pysmell.idehelper.tryReadPYSMELLDICT = mockTRP
        pysmell.idehelper.listdir = mockListDir
        try:
            self.assertEquals(findPYSMELLDICT(os.path.join('a', 'random', 'path', 'andfile')), None, 'should not find PYSMELLTAGS')
            self.assertEquals(listdirs,
                [os.path.join('a', 'random', 'path'),
                 os.path.join('a', 'random'),
                 'a'], # two '' because of root again
                'did not list dirs correctly: %s' % listdirs)
            self.assertEquals(TRPArgs, [], 'did not read tags correctly')

            listdirs = []
            TRPArgs = []

            tags = findPYSMELLDICT(os.path.join('random', 'dirA', 'file'))
            self.assertEquals(tags, None, 'should not find pysmelltags')
            self.assertEquals(listdirs,
                [os.path.join('random', 'dirA'), 'random'],
                'did not list dirs correctly: %s' % listdirs)
            self.assertEquals(TRPArgs,
                [(os.path.join('random', 'dirA'), 'PYSMELLTAGS.django')],
                'did not read tags correctly: %s' % TRPArgs)

        finally:
            pysmell.idehelper.tryReadPYSMELLDICT = oldTryReadPSD
            pysmell.idehelper.listdir = oldListDir


    def testInferClassAbsolute(self):
        source = dedent("""\
            class Class(object):
                def sth(self):
                    self.
        
        """)
        pathParts = ["DevFolder", "BlahBlah", "Nested", "Package", "Module.py"]
        if os.name == 'posix':
            pathParts.insert(0, "/")
        else:
            pathParts.insert(0, "C:")
        absPath = os.path.join(*pathParts)
        inferred, _ = inferClass(absPath, getSafeTree(source, 3), 3, NESTEDDICT, None)
        self.assertEquals(inferred, 'Nested.Package.Module.Class')


    def testInferClassRelative(self):
        source = dedent("""\
            class Class(object):
                def sth(self):
                    self.
        
        """)
        pathParts = ["Nested", "Package", "Module.py"]
        relPath = os.path.join(*pathParts)
        inferred, _ = inferClass(relPath, getSafeTree(source, 3), 3, NESTEDDICT, None)
        self.assertEquals(inferred, 'Nested.Package.Module.Class')


    def testInferClassYouDontKnowAbout(self):
        source = dedent("""\
            class NewClass(object):
                def sth(self):
                    self.
        
        """)
        pathParts = ['TestData', 'PackageB', 'NewModule.py'] # TestData/PackageB contains an __init__.py file
        relPath = os.path.join(*pathParts)
        inferred, parents = inferClass(relPath, getSafeTree(source, 3), 3, NESTEDDICT, None)
        self.assertEquals(inferred, 'PackageB.NewModule.NewClass')
        self.assertEquals(parents, ['object'])

        cwd = os.getcwd()
        pathParts = [cwd, 'TestData', 'PackageB', 'NewModule.py'] # TestData/PackageB contains an __init__.py file
        absPath = os.path.join(*pathParts)
        inferred, parents = inferClass(absPath, getSafeTree(source, 3), 3, NESTEDDICT, None)
        self.assertEquals(inferred, 'PackageB.NewModule.NewClass')
        self.assertEquals(parents, ['object'])


    def testInferUnknownClassParents(self):
        source = dedent("""\
            from Nested.Package.Module import Class
            class Other(Class):
                def sth(self):
                    self.
        
        """)
        klass, parents = inferClass(os.path.join('TestData', 'PackageA', 'Module.py'),
            getSafeTree(source, 4), 4, NESTEDDICT)
        self.assertEquals(klass, 'PackageA.Module.Other')
        self.assertEquals(parents, ['Nested.Package.Module.Class'])


    def testInferClassParentsWithPointers(self):
        source = dedent("""\
            from Another import Thing
            class Bother(Thing):
                def sth(self):
                    self.
        
        """)
        klass, parents = inferClass(os.path.join('TestData', 'PackageA', 'Module.py'),
            getSafeTree(source, 4), 4, NESTEDDICT)
        self.assertEquals(klass, 'PackageA.Module.Bother')
        self.assertEquals(parents, ['Nested.Package.Module.Class'])
        
        
    def testInferClassParentsWithPointersToStar(self):
        source = dedent("""\
            from Star import Class
            class Bother(Class):
                def sth(self):
                    self.
        
        """)
        klass, parents = inferClass(os.path.join('TestData', 'PackageA', 'Module.py'),
            getSafeTree(source, 4), 4, NESTEDDICT)
        self.assertEquals(klass, 'PackageA.Module.Bother')
        self.assertEquals(parents, ['Nested.Package.Module.Class'])


class DetectOptionsTest(unittest.TestCase):
    def setUp(self):
        self.pysmelldict = {
                'CONSTANTS' : ['Module.aconstant', 'Module.bconst'],
                'FUNCTIONS' : [('Module.a', [], ''), ('Module.arg', [], ''), ('Module.b', ['arg1', 'arg2'], '')],
                'CLASSES' : {
                    'Module.aClass': {
                        'constructor': [],
                        'bases': ['object', 'ForeignModule.alien'],
                        'properties': ['aprop', 'bprop'],
                        'methods': [('am', [], ''), ('bm', [], ())]
                    },
                    'Module.bClass': {
                        'constructor': [],
                        'bases': ['Module.aClass'],
                        'properties': ['cprop', 'dprop'],
                        'methods': [('cm', [], ''), ('dm', [], ())]
                    },
                },
                'POINTERS' : {},
                'HIERARCHY' : ['Module'],
            }
    

    def testDetectGlobalLookup(self):
        options = detectCompletionType('path', 'b', 1, 1, 'b', self.pysmelldict)
        expected = CompletionOptions(Types.TOPLEVEL)
        self.assertEquals(options, expected)


    def testDetectAttrLookup(self):
        line = 'somethign.a'
        options = detectCompletionType('path', line, 1, len(line), 'a', self.pysmelldict)
        expected = CompletionOptions(Types.INSTANCE, klass=None, parents=[])
        self.assertEquals(options, expected)


    def testDetectCompleteArgumentListMethodClosingParen(self):
        line = 'salf.bm()'
        options = detectCompletionType('path', line, 1, len(line) - 1, 'bm(', self.pysmelldict)
        expected = CompletionOptions(Types.METHOD, klass=None, parents=[], name='bm', rindex=-1)
        self.assertEquals(options, expected)


    def testDetectCompleteArgumentListMethod(self):
        line = 'salf.bm('
        options = detectCompletionType('path', line, 1, len(line), 'bm(', self.pysmelldict)
        expected = CompletionOptions(Types.METHOD, klass=None, parents=[], name='bm', rindex = None)
        self.assertEquals(options, expected)


    def testDetectCompleteArgumentListFunctionClosingParen(self):
        source = dedent("""\
            def a():
              b()
        """)
        line = '  b()'
        options = detectCompletionType('path', source, 2, len(line) - 1, 'b(', self.pysmelldict)
        expected = CompletionOptions(Types.FUNCTION, name='b', rindex=-1)# module?
        self.assertEquals(options, expected)

    
    def testDetectCompleteArgumentListFunction(self):
        source = dedent("""\
            def a():
              b(
        """)
        line = '  b('
        options = detectCompletionType('path', source, 2, len(line), 'b(', self.pysmelldict)
        expected = CompletionOptions(Types.FUNCTION, name='b', rindex=None)
        self.assertEquals(options, expected)


    def testDetectSimpleClass(self):
        source = dedent("""\
            class aClass(object):
                def sth(self):
                    self.
        
        """)
        line = "%sself." % (' ' * 8)
        options = detectCompletionType('Module.py', source, 3, len(line), '', self.pysmelldict)
        expected = CompletionOptions(Types.INSTANCE, klass='Module.aClass', parents=['object'])
        self.assertEquals(options, expected)



    def testInferShouldUpdatePYSMELLDICT(self):
        source = dedent("""\
            from Nested.Package.Module import Class
            class FreshClass(Class):
                something = 1
                def sth(self):
                    self.
        
        """)
        line = "%sself." % (' ' * 8)
        copiedDict = copy.deepcopy(self.pysmelldict)
        assert copiedDict == self.pysmelldict
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'),
            source, 5, len(line), '', copiedDict)
        expected = CompletionOptions(Types.INSTANCE, klass='PackageA.Module.FreshClass', parents=['Nested.Package.Module.Class'])
        self.assertEquals(options, expected) #sanity
        klass = copiedDict['CLASSES']['PackageA.Module.FreshClass']
        self.assertEquals(klass['bases'], ['Nested.Package.Module.Class'])
        self.assertEquals(klass['properties'], ['something'])
        self.assertEquals(klass['methods'], [('sth', [], "")])



    def testDetectDeepClass(self):
        source = dedent("""\
            class Class(object):
                def sth(self):
                    self.
        
        """)
        line = "%sself." % (' ' * 8)
        options = detectCompletionType(os.path.join('Nested', 'Package', 'Module.py'), source,
                            3, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.INSTANCE, klass='Nested.Package.Module.Class', parents=['object'])
        self.assertEquals(options, expected)


    def testDetectParentsOfUnknownClass(self):
        source = dedent("""\
            from Nested.Package.Module import Class
            class Other(Class):
                def sth(self):
                    self.
        
        """)
        line = "%sself." % (' ' * 8)
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                            4, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.INSTANCE, klass='PackageA.Module.Other', parents=['Nested.Package.Module.Class'])
        self.assertEquals(options, expected)
        

    def testDetectModuleCompletionInitial(self):
        source = dedent("""\
            from Nested.Package.Mo
            
        """)
        line = "from Nested.Package.Mo"
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                        1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module='Nested.Package', showMembers=False)
        self.assertEquals(options, expected)
        
        source = dedent("""\
            from Module.
            
        """)
        line = "from Module."
        options = detectCompletionType('Module.py', source, 1, len(line), '', self.pysmelldict)
        expected = CompletionOptions(Types.MODULE, module='Module', showMembers=False)
        self.assertEquals(options, expected)
        
        source = dedent("""\
            from Mo
            
        """)
        line = "from Mo"
        options = detectCompletionType('Module.py', source, 1, len(line), '', self.pysmelldict)
        expected = CompletionOptions(Types.MODULE, module='Mo', showMembers=False)
        self.assertEquals(options, expected)
        

    def testDetectModuleCompletionTwo(self):
        source = dedent("""\
            from Nested.Package import 
            
        """)
        line = "from Nested.Package import "
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package", showMembers=True)
        self.assertEquals(options, expected)

        source = dedent("""\
            from Nested import 
            
        """)
        line = "from Nested import "
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested", showMembers=True)
        self.assertEquals(options, expected)

        source = dedent("""\
            from Nested import Pack
            
        """)
        line = "from Nested import Pack"
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested", showMembers=True)
        self.assertEquals(options, expected)


    def testModuleCompletionThree(self):
        source = dedent("""\
            import Nested.Package.
            
        """)
        line = "import Nested.Package."
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package", showMembers=False)
        self.assertEquals(options, expected)

        source = dedent("""\
            import Ne
            
        """)
        line = "import Ne"
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            1, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Ne", showMembers=False)
        self.assertEquals(options, expected)


    def testDetectModuleAttrLookup(self):
        source = dedent("""\
            from Nested.Package import Module as mod

            mod.
        """)
        line = "mod."
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            3, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        self.assertEquals(options, expected)


    def testDetectModuleAttrLookupWithBase(self):
        source = dedent("""\
            from Nested.Package import Module as mod

            func(mod.some, arg)
        """)
        line = "func(mod.some"
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            3, len(line), 'some', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        self.assertEquals(options, expected)


    def testDetectModuleAttrLookupWithBase2(self):
        print '--------'
        source = dedent("""\
            from Nested.Package import Module as mod

            class Some(object):
                def init(self):
                    self.func(mod.EVT_, self.something)
        """)
        line = "%sself.func(mod.EVT_" % (" " * 8)
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            5, len(line), 'EVT_', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        self.assertEquals(options, expected)


    def testDetectModuleAttrLookup2(self):
        source = dedent("""\
            from Nested.Package import Module

            Module.
        """)
        line = "Module."
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            3, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        self.assertEquals(options, expected)


    def testDetectModuleAttrLookup3(self):
        source = dedent("""\
            from Nested import Package

            funct(Package.Module., arg)
        """)
        line = "funct(Package.Module."
        options = detectCompletionType(os.path.join('TestData', 'PackageA', 'Module.py'), source,
                                            3, len(line), '', NESTEDDICT, update=False)
        expected = CompletionOptions(Types.MODULE, module="Nested.Package.Module", showMembers=True)
        self.assertEquals(options, expected)




    def testDetectClassCreation(self):
        source = dedent("""\
            from Module import aClass

            thing = aClass()
            thing.
        """)
        line = "thing."
        options = detectCompletionType('apath', source,
                                            4, len(line), '', self.pysmelldict)
        expected = CompletionOptions(Types.INSTANCE, klass='Module.aClass', parents=['object', 'ForeignModule.alien'])
        self.assertEquals(options, expected)


    def testDetectClassCreationLocal(self):
        source = dedent("""\
            class aClass(object):
                pass

            thing = aClass()
            thing.
        """)
        line = "thing."
        options = detectCompletionType(os.path.abspath('Module.py'), source,
                                            5, len(line), '', self.pysmelldict)
        expected = CompletionOptions(Types.INSTANCE, klass='Module.aClass', parents=['object'])
        self.assertEquals(options, expected)




class FindBaseTest(unittest.TestCase):

    def testThem(self):
        index = findBase('bbbb', 2)
        self.assertEquals(index, 0)
        index = findBase('a.bbbb(', 7)
        self.assertEquals(index, 2)
        index = findBase('bbbb(', 5)
        self.assertEquals(index, 0)
        index = findBase('    bbbb', 6)
        self.assertEquals(index, 4)
        index = findBase('hehe.bbbb', 7)
        self.assertEquals(index, 5)
        index = findBase('    hehe.bbbb', 11)
        self.assertEquals(index, 9)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_matchers
import unittest
from pysmell.matchers import (matchCaseSensitively, matchCaseInsensitively,
        matchCamelCased, matchSmartass, matchFuzzyCS, matchFuzzyCI, camelGroups)

class MatcherTest(unittest.TestCase):
    def testCamelGroups(self):
        def assertCamelGroups(word, groups):
            self.assertEquals(list(camelGroups(word)), groups.split())
        assertCamelGroups('alaMaKota', 'ala Ma Kota')
        assertCamelGroups('AlaMaKota', 'Ala Ma Kota')
        assertCamelGroups('isHTML', 'is H T M L')
        assertCamelGroups('ala_ma_kota', 'ala _ma _kota')

    def testMatchers(self):
        def assertMatches(base, word):
            msg = "should complete %r for %r with %s" % (base, word, testedFunction.__name__)
            uncurried = testedFunction(base)
            self.assertTrue(uncurried(word), msg +  "for the first time")
            self.assertTrue(uncurried(word), msg + "for the second time")
        def assertDoesntMatch(base, word):
            msg = "shouldn't complete %r for %r with %s" % (base, word, testedFunction.__name__)
            uncurried = testedFunction(base)
            self.assertFalse(uncurried(word), msg +  "for the first time")
            self.assertFalse(uncurried(word), msg + "for the second time")
        def assertStandardMatches():
            assertMatches('Ala', 'Ala')
            assertMatches('Ala', 'AlaMaKota')
            assertMatches('ala_ma_kota', 'ala_ma_kota')
            assertMatches('', 'AlaMaKota')
            assertDoesntMatch('piernik', 'wiatrak')
        def assertCamelMatches():
            assertMatches('AMK', 'AlaMaKota')
            assertMatches('aM', 'alaMaKota')
            assertMatches('aMK', 'alaMaKota')
            assertMatches('aMaKo', 'alaMaKota')
            assertMatches('alMaK', 'alaMaKota')
            assertMatches('a_ma_ko', 'ala_ma_kota')
            assertDoesntMatch('aleMbiK', 'alaMaKota')
            assertDoesntMatch('alaMaKotaIPsaIRybki', 'alaMaKota')

        testedFunction = matchCaseSensitively
        assertStandardMatches()
        assertDoesntMatch('ala', 'Alamakota')
        assertDoesntMatch('ala', 'Ala')

        testedFunction = matchCaseInsensitively
        assertStandardMatches()
        assertMatches('ala', 'Alamakota')
        assertMatches('ala', 'Ala')
        
        testedFunction = matchCamelCased
        assertStandardMatches()
        assertCamelMatches()
        assertMatches('aMK', 'alaMaKota')
        assertDoesntMatch('almako', 'ala_ma_kota')
        assertDoesntMatch('almako', 'alaMaKota')
        assertDoesntMatch('alkoma', 'alaMaKota')

        testedFunction = matchSmartass
        assertStandardMatches()
        assertCamelMatches()
        assertMatches('amk', 'alaMaKota')
        assertMatches('AMK', 'alaMaKota')
        assertMatches('almako', 'ala_ma_kota')
        assertMatches('almako', 'alaMaKota')
        assertDoesntMatch('alkoma', 'alaMaKota')

        testedFunction = matchFuzzyCS
        assertStandardMatches()
        assertCamelMatches()
        assertMatches('aMK', 'alaMaKota')
        assertMatches('aaMKa', 'alaMaKota')
        assertDoesntMatch('almako', 'alaMaKota')
        assertDoesntMatch('amk', 'alaMaKota')
        assertDoesntMatch('alkoma', 'alaMaKota')

        testedFunction = matchFuzzyCI
        assertStandardMatches()
        assertCamelMatches()
        assertMatches('aMK', 'alaMaKota')
        assertMatches('aaMKa', 'alaMaKota')
        assertMatches('almako', 'alaMaKota')
        assertMatches('amk', 'alaMaKota')
        assertDoesntMatch('alkoma', 'alaMaKota')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tags
import unittest
from textwrap import dedent
import subprocess
import os
from pysmell import idehelper
from pysmell.codefinder import ModuleDict
from pysmell import tags

class ProducesFile(object):
    def __init__(self, *files):
        self.files = files
    def __call__(self, func):
        def patched(*args, **kw):
            for f in self.files:
                if os.path.exists(f):
                    os.remove(f)
            try:
                return func(*args, **kw)
            finally:
                for f in self.files:
                    if os.path.exists(f):
                        os.remove(f)
        patched.__name__ = func.__name__
        return patched


class FunctionalTest(unittest.TestCase):
    def setUp(self):
        self.packageA = {
            'CONSTANTS': [
                'PackageA.SneakyConstant',
                'PackageA.ModuleA.CONSTANT',
                'PackageA.NestedPackage.EvenMore.ModuleC.NESTED',
            ],
            'FUNCTIONS': [
                ('PackageA.SneakyFunction', [], ""),
                ('PackageA.ModuleA.TopLevelFunction', ['arg1', 'arg2'], ""),
            ],
            'CLASSES': {
                'PackageA.ModuleA.ClassA': {
                    'bases': ['object'],
                    'docstring': '',
                    'constructor': [],
                    'properties': ['classPropertyA', 'classPropertyB', 'propertyA', 'propertyB', 'propertyC', 'propertyD'],
                    'methods': [('methodA', ['argA', 'argB', '*args', '**kwargs'], '')]
                },
                'PackageA.ModuleA.ChildClassA': {
                    'bases': ['PackageA.ModuleA.ClassA', 'object'],
                    'docstring': 'a class docstring, imagine that',
                    'constructor': ['conArg'],
                    'properties': ['extraProperty'],
                    'methods': [('extraMethod', [], 'i have a docstring')],
                },
                'PackageA.SneakyClass': {
                    'bases': [],
                    'docstring': '',
                    'constructor': [],
                    'properties': [],
                    'methods': []
                },
            },
            'POINTERS': {
                'PackageA.NESTED': 'PackageA.NestedPackage.EvenMore.ModuleC.NESTED',
                'PackageA.MC': 'PackageA.NestedPackage.EvenMore.ModuleC',
                'PackageA.RelImport': 'PackageA.NestedPackage',
                'PackageA.RelMC': 'PackageA.NestedPackage.EvenMore.ModuleC',
            
            },
            'HIERARCHY': [
                'PackageA',
                'PackageA.ModuleA',
                'PackageA.NestedPackage',
                'PackageA.NestedPackage.EvenMore',
                'PackageA.NestedPackage.EvenMore.ModuleC',
            ]
        }
        
        self.packageB = {
            'CONSTANTS': ['PackageB.SneakyConstant'],
            'FUNCTIONS': [('PackageB.SneakyFunction', [], "")],
            'CLASSES':{
                'PackageB.SneakyClass': {
                    'bases': [],
                    'docstring': '',
                    'constructor': [],
                    'properties': [],
                    'methods': []
                }
            },
            'POINTERS': {},
            'HIERARCHY': ['PackageB']
        }

    def assertDictsEqual(self, actualDict, expectedDict):
        self.assertEquals(len(actualDict.keys()), len(expectedDict.keys()),
            "dicts don't have equal number of keys: %r != %r" % (actualDict.keys(), expectedDict.keys()))
        self.assertEquals(set(actualDict.keys()), set(expectedDict.keys()), "dicts don't have equal keys")
        for key, value in actualDict.items():
            if isinstance(value, dict):
                self.assertTrue(isinstance(expectedDict[key], dict), "incompatible types found for key %s" % key)
                self.assertDictsEqual(value, expectedDict[key])
            elif isinstance(value, list):
                self.assertTrue(isinstance(expectedDict[key], list), "incompatible types found for key %s" % key)
                self.assertEquals(sorted(value), sorted(expectedDict[key]), 'wrong sorted(list) for key %s:\n%r != %r' % (key, value, expectedDict[key]))
            else:
                self.assertEquals(value, expectedDict[key], "wrong value for key %s: %s" % (key, value))


    @ProducesFile('TestData/PYSMELLTAGS')
    def testMultiPackage(self):
        subprocess.call(["pysmell", "PackageA", "PackageB"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PYSMELLTAGS').read())
        expectedDict = {}
        expectedDict.update(self.packageA)
        expectedDict['CLASSES'].update(self.packageB['CLASSES'])
        expectedDict['CONSTANTS'].extend(self.packageB['CONSTANTS'])
        expectedDict['FUNCTIONS'].extend(self.packageB['FUNCTIONS'])
        expectedDict['HIERARCHY'].extend(self.packageB['HIERARCHY'])
        self.assertDictsEqual(PYSMELLDICT, expectedDict)



    @ProducesFile('TestData/PYSMELLTAGS')
    def testUpdateDict(self):
        subprocess.call(["pysmell", "PackageA"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        subprocess.call(["pysmell", "PackageB", "-i", "PYSMELLTAGS"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PYSMELLTAGS').read())
        expectedDict = {}
        expectedDict.update(self.packageA)
        expectedDict['CLASSES'].update(self.packageB['CLASSES'])
        expectedDict['CONSTANTS'].extend(self.packageB['CONSTANTS'])
        expectedDict['FUNCTIONS'].extend(self.packageB['FUNCTIONS'])
        expectedDict['HIERARCHY'].extend(self.packageB['HIERARCHY'])
        self.assertDictsEqual(PYSMELLDICT, expectedDict)



    @ProducesFile('TestData/PYSMELLTAGS')
    def testPackageA(self):
        subprocess.call(["pysmell", "PackageA"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PYSMELLTAGS').read())
        expectedDict = self.packageA
        self.assertDictsEqual(PYSMELLDICT, expectedDict)

        foundDict = idehelper.findPYSMELLDICT(os.path.join('TestData', 'PackageA', 'something'))
        self.assertDictsEqual(foundDict, expectedDict)


    @ProducesFile('TestData/PYSMELLTAGS')
    def testPackageB(self):
        subprocess.call(["pysmell", "PackageB"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PYSMELLTAGS').read())
        expectedDict = self.packageB
        self.assertDictsEqual(PYSMELLDICT, expectedDict)


    @ProducesFile('TestData/PackageA/PYSMELLTAGS')
    def testPackageDot(self):
        subprocess.call(["pysmell", "."], cwd='TestData/PackageA')
        self.assertTrue(os.path.exists('TestData/PackageA/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PackageA/PYSMELLTAGS').read())
        expectedDict = self.packageA
        self.assertDictsEqual(PYSMELLDICT, expectedDict)


    @ProducesFile('TestData/PYSMELLTAGS')
    def testAllPackages(self):
        subprocess.call(["pysmell", "."], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/PYSMELLTAGS'))
        PYSMELLDICT = eval(open('TestData/PYSMELLTAGS').read())
        expectedDict = {}
        expectedDict.update(self.packageA)
        expectedDict['CLASSES'].update(self.packageB['CLASSES'])
        expectedDict['CONSTANTS'].extend(self.packageB['CONSTANTS'])
        expectedDict['CONSTANTS'].append('standalone.NOPACKAGE')
        expectedDict['FUNCTIONS'].extend(self.packageB['FUNCTIONS'])
        expectedDict['HIERARCHY'].extend(self.packageB['HIERARCHY'])
        expectedDict['HIERARCHY'].append('standalone')
        self.assertDictsEqual(PYSMELLDICT, expectedDict)

    
    @ProducesFile('TestData/PackageA/NestedPackage/EvenMore/PYSMELLTAGS')
    def testSingleFile(self):
        "should recurse up until it doesn't find __init__.py"
        path = 'TestData/PackageA/NestedPackage/EvenMore/'
        subprocess.call(["pysmell", "ModuleC.py"], cwd=path)
        self.assertTrue(os.path.exists('%sPYSMELLTAGS' % path ))
        PYSMELLDICT = eval(open('%sPYSMELLTAGS' % path).read())
        expectedDict = {
            'FUNCTIONS': [],
            'CONSTANTS': ['PackageA.NestedPackage.EvenMore.ModuleC.NESTED'],
            'CLASSES': {},
            'POINTERS': {},
            'HIERARCHY': ['PackageA.NestedPackage.EvenMore.ModuleC'],
                        
        }
        self.assertDictsEqual(PYSMELLDICT, expectedDict)


    @ProducesFile("TestData/PYSMELLTAGS")
    def testSingleFilesWithPaths(self):
        path = 'TestData'
        pysmell = os.path.join(path, 'PYSMELLTAGS')
        subprocess.call(["pysmell", os.path.join("PackageA", "NestedPackage", "EvenMore", "ModuleC.py")], cwd=path)
        self.assertTrue(os.path.exists(pysmell))
        PYSMELLDICT = eval(open(pysmell).read())
        expectedDict = {
            'FUNCTIONS': [],
            'CONSTANTS': ['PackageA.NestedPackage.EvenMore.ModuleC.NESTED'],
            'CLASSES': {},
            'POINTERS': {},
            'HIERARCHY': ['PackageA.NestedPackage.EvenMore.ModuleC'],
                        
        }
        self.assertDictsEqual(PYSMELLDICT, expectedDict)


    @ProducesFile('TestData/OUTPUTREDIR', 'TestData/OUTPUTREDIR2')
    def testOutputRedirect(self):
        subprocess.call(["pysmell", "PackageA", "-o",
            "OUTPUTREDIR"], cwd='TestData')
        self.assertTrue(os.path.exists('TestData/OUTPUTREDIR'))
        PYSMELLDICT = eval(open('TestData/OUTPUTREDIR').read())
        expectedDict = self.packageA
        self.assertDictsEqual(PYSMELLDICT, expectedDict)

        absPath = os.path.join(os.getcwd(), 'TestData', 'OUTPUTREDIR2')
        subprocess.call(["pysmell", "PackageA", "-o", absPath], cwd='TestData')
        self.assertTrue(os.path.exists(absPath))
        PYSMELLDICT = eval(open(absPath).read())
        expectedDict = self.packageA
        self.assertDictsEqual(PYSMELLDICT, expectedDict)


    def testNoArgs(self):
        proc = subprocess.Popen(["pysmell"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        stderr = proc.stderr.read()
        expected = dedent("""\
        usage: pysmell [-h] [-v] [-x [package [package ...]]] [-o OUTPUT] [-i INPUT]
                       [-t] [-d]
                       package [package ...]
        pysmell: error: too few arguments
        """)
        self.assertEquals(stderr.replace('\r\n', '\n'), expected)


    def DONTtestDunderAll(self):
        self.fail("when doing 'from place import *', do not bring in everything"
        "in the pointers but look for __all__ in the module and add only"
        "these.")


    def testOptionalOutput(self):
        modules = tags.process(['TestData/PackageA'], [], verbose=True)
        self.assertTrue(isinstance(modules, ModuleDict), 'did not return modules')
        self.assertDictsEqual(modules, self.packageA)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_vim

import os.path
import time
from subprocess import Popen, PIPE, call
import sys
import unittest
from pysmell.vimhelper import findWord

vim_test = os.path.join("Tests", "test_vim.vim")


class MockVim(object):
    class _current(object):
        class _window(object):
            cursor = (-1, -1)
        buffer = []
        window = _window()
    current = _current()
    command = lambda _, __:Non
    def eval(*_):
        pass

class VimHelperTest(unittest.TestCase):

    def setUp(self):
        import pysmell.vimhelper
        pysmell.vimhelper.vim = self.vim = MockVim()

    def testFindBaseName(self):
        self.vim.current.buffer = ['aaaa', 'bbbb', 'cccc']
        self.vim.current.window.cursor =(2, 2)
        word = findWord(self.vim, 2, 'bbbb')
        self.assertEquals(word, 'bb')

    def testFindBaseMethodCall(self):
        self.vim.current.buffer = ['aaaa', 'a.bbbb(', 'cccc']
        self.vim.current.window.cursor =(2, 7)
        word = findWord(self.vim, 7, 'a.bbbb(')
        self.assertEquals(word, 'a.bbbb(')

    def testFindBaseFuncCall(self):
        self.vim.current.buffer = ['aaaa', 'bbbb(', 'cccc']
        self.vim.current.window.cursor =(2, 5)
        word = findWord(self.vim, 5, 'bbbb(')
        self.assertEquals(word, 'bbbb(')

    def testFindBaseNameIndent(self):
        self.vim.current.buffer = ['aaaa', '    bbbb', 'cccc']
        self.vim.current.window.cursor =(2, 6)
        word = findWord(self.vim, 6, '    bbbb')
        self.assertEquals(word, 'bb')

    def testFindBaseProp(self):
        self.vim.current.buffer = ['aaaa', 'hehe.bbbb', 'cccc']
        self.vim.current.window.cursor =(2, 7)
        word = findWord(self.vim, 7, 'hehe.bbbb')
        self.assertEquals(word, 'hehe.bb')

    def testFindBasePropIndent(self):
        self.vim.current.buffer = ['aaaa', '    hehe.bbbb', 'cccc']
        self.vim.current.window.cursor =(2, 11)
        word = findWord(self.vim, 11, '    hehe.bbbb')
        self.assertEquals(word, 'hehe.bb')

class VimTest(unittest.TestCase):
    def testVimFunctionally(self):
        if sys.platform == 'win32':
            return
        try:
            pysmell_file = os.path.join("TestData", "PYSMELLTAGS")
            if os.path.exists(pysmell_file):
                os.remove(pysmell_file)
            call(["pysmell", "."], cwd="TestData")
            self.assertTrue(os.path.exists(pysmell_file))
            test_file = os.path.join("TestData", "test.py")
            if os.path.exists(test_file):
                os.remove(test_file)

            self.assertTrue(os.path.isfile(vim_test), "Could not find vim functional test")
            proc = Popen(["vim", "-u", "NONE", "-s", vim_test], stdout=PIPE, stderr=PIPE)
            WAITFOR = 4
            while WAITFOR >= 0:
                result = proc.poll()
                if result is not None:
                    break
                time.sleep(1)
                WAITFOR -= 1
            else:
                try:
                    import win32api
                    win32api.TerminateProcess(int(proc._handle), -1)
                except:
                    import signal
                    os.kill(proc.pid, signal.SIGTERM)
                self.fail("TIMED OUT WAITING FOR VIM.Stdout was:\n" + proc.stdout.read())
            test_output = open(test_file, 'r').read()
            if result != 0:
                msg = proc.stdout.read()
                msg += open('vimtest.out', 'r').read()
                self.fail(msg)
            self.assertTrue("o.classPropertyA" in test_output, "did not complete correctly. Test output is:\n %s" % test_output)

        finally:
            if (os.path.isfile(pysmell_file)):
                os.remove(pysmell_file)
            if os.path.exists('vimtest.out'):
                os.remove('vimtest.out')
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()
            
            

    

########NEW FILE########
