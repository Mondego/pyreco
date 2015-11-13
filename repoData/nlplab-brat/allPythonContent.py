__FILENAME__ = config_template
# This configuration file specifies the global setup of the brat
# server. It is recommended that you use the installation script
# instead of editing this file directly. To do this, run the following
# command in the brat directory:
#
#     ./install.sh
#
# if you wish to configure the server manually, you will first need to
# make sure that this file appears as config.py in the brat server
# root directory. If this file is currently named config_template.py,
# you can do this as follows:
#
#     cp config_template.py config.py
#
# you will then need to edit config.py, minimally replacing all 
# instances of the string CHANGE_ME with their appropriate values.
# Please note that these values MUST appear in quotes, e.g. as in
#
# ADMIN_CONTACT_EMAIL = 'admin@example.com'



# Contact email for users to use if the software encounters errors
ADMIN_CONTACT_EMAIL = CHANGE_ME

# Directories required by the brat server:
#
#     BASE_DIR: directory in which the server is installed
#     DATA_DIR: directory containing texts and annotations
#     WORK_DIR: directory that the server uses for temporary files
#
BASE_DIR = CHANGE_ME
DATA_DIR = CHANGE_ME
WORK_DIR = CHANGE_ME

# If you have installed brat as suggested in the installation
# instructions, you can set up BASE_DIR, DATA_DIR and WORK_DIR by
# removing the three lines above and deleting the initial '#'
# character from the following four lines:

#from os.path import dirname, join
#BASE_DIR = dirname(__file__)
#DATA_DIR = join(BASE_DIR, 'data')
#WORK_DIR = join(BASE_DIR, 'work')

# To allow editing, include at least one USERNAME:PASSWORD pair below.
# The format is the following:
#
#     'USERNAME': 'PASSWORD',
#
# For example, user `editor` and password `annotate`:
#
#     'editor': 'annotate',

USER_PASSWORD = {
#     (add USERNAME:PASSWORD pairs below this line.)
}





########## ADVANCED CONFIGURATION OPTIONS ##########

# The following options control advanced aspects of the brat server
# setup.  It is not necessary to edit these in a basic brat server
# installation.


### MAX_SEARCH_RESULT_NUMBER
# It may be a good idea to limit the max number of results to a search
# as very high numbers can be demanding of both server and clients.
# (unlimited if not defined or <= 0)

MAX_SEARCH_RESULT_NUMBER = 1000


### DEBUG
# Set to True to enable additional debug output

DEBUG = False

### TUTORIALS
# Unauthorised users can create tutorials (but not edit without a login)
TUTORIALS = False

### LOG_LEVEL
# If you are a developer you may want to turn on extensive server
# logging by enabling LOG_LEVEL = LL_DEBUG

LL_DEBUG, LL_INFO, LL_WARNING, LL_ERROR, LL_CRITICAL = range(5)
LOG_LEVEL = LL_WARNING
#LOG_LEVEL = LL_DEBUG

### BACKUP_DIR
# Define to enable backups

# from os.path import join
#BACKUP_DIR = join(WORK_DIR, 'backup')

try:
    assert DATA_DIR != BACKUP_DIR, 'DATA_DIR cannot equal BACKUP_DIR'
except NameError:
    pass # BACKUP_DIR most likely not defined


### SVG_CONVERSION_COMMANDS
# If export to formats other than SVG is needed, the server must have
# a software capable of conversion like inkscape set up, and the
# following must be defined.
# (SETUP NOTE: at least Inkscape 0.46 requires the directory
# ".gnome2/" in the apache home directory and will crash if it doesn't
# exist.)

#SVG_CONVERSION_COMMANDS = [
#    ('png', 'inkscape --export-area-drawing --without-gui --file=%s --export-png=%s'),
#    ('pdf', 'inkscape --export-area-drawing --without-gui --file=%s --export-pdf=%s'),
#    ('eps', 'inkscape --export-area-drawing --without-gui --file=%s --export-eps=%s'),
#]

########NEW FILE########
__FILENAME__ = altnamedtuple
from operator import itemgetter as _itemgetter
from keyword import iskeyword as _iskeyword
import sys as _sys

# namedtyple implementation for older pythons, from
# http://code.activestate.com/recipes/500261/

def namedtuple(typename, field_names, verbose=False, rename=False):
    """Returns a new subclass of tuple with named fields.

    >>> Point = namedtuple('Point', 'x y')
    >>> Point.__doc__                   # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> Point(**d)                      # convert from a dictionary
    Point(x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    Point(x=100, y=22)

    """

    # Parse and validate the field names.  Validation serves two purposes,
    # generating informative error messages and preventing template injection attacks.
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
    field_names = tuple(map(str, field_names))
    if rename:
        names = list(field_names)
        seen = set()
        for i, name in enumerate(names):
            if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                or not name or name[0].isdigit() or name.startswith('_')
                or name in seen):
                    names[i] = '_%d' % i
            seen.add(name)
        field_names = tuple(names)
    for name in (typename,) + field_names:
        if not min(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with a number: %r' % name)
    seen_names = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError('Field names cannot start with an underscore: %r' % name)
        if name in seen_names:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen_names.add(name)

    # Create and fill-in the class template
    numfields = len(field_names)
    argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
    for i, name in enumerate(field_names):
        template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
    if verbose:
        print template

    # Execute the template string in a temporary namespace
    namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                     _property=property, _tuple=tuple)
    try:
        exec template in namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    try:
        result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return result






if __name__ == '__main__':
    # verify that instances can be pickled
    from cPickle import loads, dumps
    Point = namedtuple('Point', 'x, y', True)
    p = Point(x=10, y=20)
    assert p == loads(dumps(p, -1))

    # test and demonstrate ability to override methods
    class Point(namedtuple('Point', 'x y')):
        @property
        def hypot(self):
            return (self.x ** 2 + self.y ** 2) ** 0.5
        def __str__(self):
            return 'Point: x=%6.3f y=%6.3f hypot=%6.3f' % (self.x, self.y, self.hypot)

    for p in Point(3,4), Point(14,5), Point(9./7,6):
        print p

    class Point(namedtuple('Point', 'x y')):
        'Point class with optimized _make() and _replace() without error-checking'
        _make = classmethod(tuple.__new__)
        def _replace(self, _map=map, **kwds):
            return self._make(_map(kwds.get, ('x', 'y'), self))

    print Point(11, 22)._replace(x=100)

    import doctest
    TestResults = namedtuple('TestResults', 'failed attempted')
    print TestResults(*doctest.testmod())

########NEW FILE########
__FILENAME__ = argparse
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Copyright © 2006-2009 Steven J. Bethard <steven.bethard@gmail.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

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
    'Namespace',
    'Action',
    'FileType',
    'HelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'ArgumentDefaultsHelpFormatter',
]


import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

try:
    _set = set
except NameError:
    from sets import Set as _set

try:
    _basestring = basestring
except NameError:
    _basestring = str

try:
    _sorted = sorted
except NameError:

    def _sorted(iterable, reverse=False):
        result = list(iterable)
        result.sort()
        if reverse:
            result.reverse()
        return result


def _callable(obj):
    return hasattr(obj, '__call__') or hasattr(obj, '__bases__')

# silence Python 2.6 buggy warnings about Exception.message
if _sys.version_info[:2] == (2, 6):
    import warnings
    warnings.filterwarnings(
        action='ignore',
        message='BaseException.message has been deprecated as of Python 2.6',
        category=DeprecationWarning,
        module='argparse')


SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'

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
        return _sorted(self.__dict__.items())

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
        group_actions = _set()
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
                        inserts[start] = '['
                        inserts[end] = ']'
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
        for i in _sorted(inserts, reverse=True):
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
                 help=None):
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
        parser.parse_args(arg_strings, namespace)


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
        if self.add_help:
            self.add_argument(
                '-h', '--help', action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                '-v', '--version', action='version', default=SUPPRESS,
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
                        if isinstance(action.default, _basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            return self._parse_known_args(args, namespace)
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
        seen_actions = _set()
        seen_non_default_actions = _set()

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
            if isinstance(value, _basestring):
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
__FILENAME__ = annlog
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Annotation operation logging mechanism.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Author:     Sampo Pyysalo       <smp is s u-tokyo ac jp>
Version:    2011-11-22
'''

import logging
from session import get_session
from message import Messager
from inspect import getargspec
from os.path import isabs
from os.path import join as path_join

from config import DATA_DIR
from projectconfig import options_get_annlogfile

def real_directory(directory, rel_to=DATA_DIR):
    assert isabs(directory), 'directory "%s" is not absolute' % directory
    return path_join(rel_to, directory[1:])

def annotation_logging_active(directory):
    """
    Returns true if annotation logging is being performed for the
    given directory, false otherwise.
    """
    return ann_logger(directory) is not None

def ann_logger(directory):
    """
    Lazy initializer for the annotation logger. Returns None if
    annotation logging is not configured for the given directory and a
    logger otherwise.
    """
    if ann_logger.__logger == False:
        # not initialized
        annlogfile = options_get_annlogfile(directory)
        if annlogfile == '<NONE>':
            # not configured
            ann_logger.__logger = None
        else:
            # initialize
            try:
                l = logging.getLogger('annotation')
                l.setLevel(logging.INFO)
                handler = logging.FileHandler(annlogfile)
                handler.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s\t%(message)s')
                handler.setFormatter(formatter)
                l.addHandler(handler)
                ann_logger.__logger = l
            except IOError, e:
                Messager.error("""Error: failed to initialize annotation log %s: %s.
Edit action not logged.
Please check the Annotation-log logfile setting in tools.conf""" % (annlogfile, e))
                logging.error("Failed to initialize annotation log %s: %s" % 
                              (annlogfile, e))
                ann_logger.__logger = None                
                
    return ann_logger.__logger
ann_logger.__logger = False

# local abbrev; can't have literal tabs in log fields
def _detab(s):
    return unicode(s).replace('\t', '\\t')

def log_annotation(collection, document, status, action, args):
    """
    Logs an annotation operation of type action in the given document
    of the given collection. Status is an arbitrary string marking the
    status of processing the request and args a dictionary giving
    the arguments of the action.
    """

    real_dir = real_directory(collection)

    l = ann_logger(real_dir)

    if not l:
        return False

    try:
        user = get_session()['user']
    except KeyError:
        user = 'anonymous'

    # avoid redundant logging (assuming first two args are
    # collection and document)
    # TODO: get rid of the assumption, parse the actual args
    other_args = args[2:]

    # special case for "log only" action: don't redundantly
    # record the uninformative action name, but treat the
    # first argument as the 'action'.
    if action == 'logAnnotatorAction':
        action = other_args[0]
        other_args = other_args[1:]

    l.info('%s\t%s\t%s\t%s\t%s\t%s' % (_detab(user), _detab(collection), 
                                       _detab(document), _detab(status), 
                                       _detab(action),
                                       '\t'.join([_detab(unicode(a)) for a in other_args])))

########NEW FILE########
__FILENAME__ = annotation
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

from __future__ import with_statement

'''
Functionality related to the annotation file format.

Author:     Pontus Stenetorp   <pontus is s u-tokyo ac jp>
Version:    2011-01-25
'''

# TODO: Major re-work, cleaning up and conforming with new server paradigm

from logging import info as log_info
from codecs import open as codecs_open
from functools import partial
from itertools import chain, takewhile
from os import close as os_close, utime
from time import time
from os.path import join as path_join
from os.path import basename, splitext
from re import match as re_match
from re import compile as re_compile

from common import ProtocolError
from filelock import file_lock
from message import Messager


### Constants
# The only suffix we allow to write to, which is the joined annotation file
JOINED_ANN_FILE_SUFF = 'ann'
# These file suffixes indicate partial annotations that can not be written to
# since they depend on multiple files for completeness
PARTIAL_ANN_FILE_SUFF = ['a1', 'a2', 'co', 'rel']
KNOWN_FILE_SUFF = [JOINED_ANN_FILE_SUFF]+PARTIAL_ANN_FILE_SUFF
TEXT_FILE_SUFFIX = 'txt'
# String used to catenate texts of discontinuous annotations in reference text
DISCONT_SEP = ' '
###

# If True, use BioNLP Shared Task 2013 compatibilty mode, allowing
# normalization annotations to be parsed using the BioNLP Shared Task
# 2013 format in addition to the brat format and allowing relations to
# reference event triggers. NOTE: Alternate format supported only for
# reading normalization annotations, not for creating new ones. Don't
# change this setting unless you are sure you know what you are doing.
BIONLP_ST_2013_COMPATIBILITY = True
BIONLP_ST_2013_NORMALIZATION_RES = [
    (re_compile(r'^(Reference) Annotation:(\S+) Referent:(\S+)'), r'\1 \2 \3'),
    (re_compile(r'^(Reference) Referent:(\S+) Annotation:(\S+)'), r'\1 \3 \2'),
    ]

class AnnotationLineSyntaxError(Exception):
    def __init__(self, line, line_num, filepath):
        self.line = line
        self.line_num = line_num
        self.filepath = filepath

    def __str__(self):
        u'Syntax error on line %d: "%s"' % (self.line_num, self.line)


class IdedAnnotationLineSyntaxError(AnnotationLineSyntaxError):
    def __init__(self, id, line, line_num, filepath):
        AnnotationLineSyntaxError.__init__(self, line, line_num, filepath)
        self.id = id

    def __str__(self):
        u'Syntax error on line %d (id %s): "%s"' % (self.line_num, self.id, self.line)


class AnnotationNotFoundError(Exception):
    def __init__(self, id):
        self.id = id

    def __str__(self):
        return u'Could not find an annotation with id: %s' % (self.id, )


class AnnotationFileNotFoundError(ProtocolError):
    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        return u'Could not find any annotations for %s' % (self.fn, )

    def json(self, json_dic):
        json_dic['exception'] = 'annotationFileNotFound'
        return json_dic


class AnnotationCollectionNotFoundError(ProtocolError):
    def __init__(self, cn):
        self.cn = cn

    def __str__(self):
        return u'Error accessing collection %s' % (self.cn, )

    def json(self, json_dic):
        # TODO: more specific error?
        json_dic['exception'] = 'annotationCollectionNotFound'
        return json_dic
   

class EventWithoutTriggerError(ProtocolError):
    def __init__(self, event):
        self.event = event

    def __str__(self):
        return u'Event "%s" lacks a trigger' % (self.event, )

    def json(self, json_dic):
        json_dic['exception'] = 'eventWithoutTrigger'
        return json_dic
   

class EventWithNonTriggerError(ProtocolError):
    def __init__(self, event, non_trigger):
        self.event = event
        self.non_trigger = non_trigger

    def __str__(self):
        return u'Non-trigger "%s" used by "%s" as trigger' % (
                self.non_trigger, self.event, )

    def json(self, json_dic):
        json_dic['exception'] = 'eventWithNonTrigger'
        return json_dic


class TriggerReferenceError(ProtocolError):
    def __init__(self, trigger, referencer):
        self.trigger = trigger
        self.referencer = referencer

    def __str__(self):
        return u'Trigger "%s" referenced by non-event "%s"' % (self.trigger,
                self.referencer, )

    def json(self, json_dic):
        json_dic['exception'] = 'triggerReference'
        return json_dic


class AnnotationTextFileNotFoundError(AnnotationFileNotFoundError):
    def __str__(self):
        return u'Could not read text file for %s' % (self.fn, )


class AnnotationsIsReadOnlyError(ProtocolError):
    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        # No extra message; the client is doing a fine job of reporting this
        #return u'Annotations read-only for %s' % (self.fn, )
        return ''

    def json(self, json_dic):
        json_dic['exception'] = 'annotationIsReadOnly'
        return json_dic


class DuplicateAnnotationIdError(AnnotationLineSyntaxError):
    def __init__(self, id, line, line_num, filepath):
        AnnotationLineSyntaxError.__init__(self, line, line_num, filepath)
        self.id = id

    def __str__(self):
        return (u'Duplicate id: %s on line %d (id %s): "%s"'
                ) % (self.id, self.line_num, self.id, self.line)


class InvalidIdError(Exception):
    def __init__(self, id):
        self.id = id

    def __str__(self):
        return u'Invalid id: %s' % (self.id, )


class DependingAnnotationDeleteError(Exception):
    def __init__(self, target, dependants):
        self.target = target
        self.dependants = dependants

    def __str__(self):
        return u'%s can not be deleted due to depending annotations %s' % (
                unicode(self.target).rstrip(), ",".join([unicode(d).rstrip() for d in self.dependants]))

    def html_error_str(self, response=None):
        return u'''Annotation:
        %s
        Has depending annotations attached to it:
        %s''' % (unicode(self.target).rstrip(), ",".join([unicode(d).rstrip() for d in self.dependants]))


class SpanOffsetOverlapError(ProtocolError):
    def __init__(self, offsets):
        self.offsets = offsets

    def __str__(self):
        return u'The offsets [%s] overlap' % (', '.join(unicode(e)
            for e in self.offsets, ))

    def json(self, json_dic):
        json_dic['exception'] = 'spanOffsetOverlapError'
        return json_dic


# Open function that enforces strict, utf-8, and universal newlines for reading
# TODO: Could have another wrapping layer raising an appropriate ProtocolError
def open_textfile(filename, mode='rU'):
    # enforce universal newline support ('U') in read modes
    if len(mode) != 0 and mode[0] == 'r' and 'U' not in mode:
        mode = mode + 'U'
    return codecs_open(filename, mode, encoding='utf8', errors='strict')

def __split_annotation_id(id):
    m = re_match(r'^([A-Za-z]+|#[A-Za-z]*)([0-9]+)(.*?)$', id)
    if m is None:
        raise InvalidIdError(id)
    pre, num_str, suf = m.groups()
    return pre, num_str, suf

def annotation_id_prefix(id):
    pre = ''.join(c for c in takewhile(lambda x : not x.isdigit(), id))
    if not pre:
        raise InvalidIdError(id)
    return pre

def annotation_id_number(id):
    return __split_annotation_id(id)[1]

def is_valid_id(id):
    # special case: '*' is acceptable as an "ID"
    if id == '*':
        return True

    try:
        # currently accepting any ID that can be split.
        # TODO: consider further constraints 
        __split_annotation_id(id)[1]
        return True
    except InvalidIdError:
        return False


class Annotations(object):
    """
    Basic annotation storage. Not concerned with conformity of
    annotations to text; can be created without access to the
    text file to which the annotations apply.
    """

    def get_document(self):
        return self._document
    
    def _select_input_files(self, document):
        """
        Given a document name (path), returns a list of the names of
        specific annotation files relevant do the document, or the
        empty list if none found. For example, given "1000", may
        return ["1000.a1", "1000.a2"]. May set self._read_only flag to
        True.
        """

        from os.path import isfile
        from os import access, W_OK

        try:
            # Do we have a valid suffix? If so, it is probably best to the file
            suff = document[document.rindex('.') + 1:]
            if suff == JOINED_ANN_FILE_SUFF:
                # It is a joined file, let's load it
                input_files = [document]
                # Do we lack write permissions?
                if not access(document, W_OK):
                    #TODO: Should raise an exception or warning
                    self._read_only = True
            elif suff in PARTIAL_ANN_FILE_SUFF:
                # It is only a partial annotation, we will most likely fail
                # but we will try opening it
                input_files = [document]
                self._read_only = True
            else:
                input_files = []
        except ValueError:
            # The document lacked a suffix
            input_files = []

        if not input_files:
            # Our first attempts at finding the input by checking suffixes
            # failed, so we try to attach know suffixes to the path.
            sugg_path = document + '.' + JOINED_ANN_FILE_SUFF
            if isfile(sugg_path):
                # We found a joined file by adding the joined suffix
                input_files = [sugg_path]
                # Do we lack write permissions?
                if not access(sugg_path, W_OK):
                    #TODO: Should raise an exception or warning
                    self._read_only = True
            else:
                # Our last shot, we go for as many partial files as possible
                input_files = [sugg_path for sugg_path in 
                        (document + '.' + suff
                            for suff in PARTIAL_ANN_FILE_SUFF)
                        if isfile(sugg_path)]
                self._read_only = True

        return input_files
            
    #TODO: DOC!
    def __init__(self, document, read_only=False):
        # this decides which parsing function is invoked by annotation
        # ID prefix (first letter)
        self._parse_function_by_id_prefix = {
            'T': self._parse_textbound_annotation,
            'M': self._parse_modifier_annotation,
            'A': self._parse_attribute_annotation,
            'N': self._parse_normalization_annotation,
            'R': self._parse_relation_annotation,
            '*': self._parse_equiv_annotation,
            'E': self._parse_event_annotation,
            '#': self._parse_comment_annotation,
            }

        #TODO: DOC!
        #TODO: Incorparate file locking! Is the destructor called upon inter crash?
        from collections import defaultdict
        from os.path import basename, getmtime, getctime
        #from fileinput import FileInput, hook_encoded

        # we should remember this
        self._document = document

        self.failed_lines = []
        self.externally_referenced_triggers = set()

        ### Here be dragons, these objects need constant updating and syncing
        # Annotation for each line of the file
        self._lines = []
        # Mapping between annotation objects and which line they occur on
        # Range: [0, inf.) unlike [1, inf.) which is common for files
        self._line_by_ann = {}
        # Maximum id number used for each id prefix, to speed up id generation
        #XXX: This is effectively broken by the introduction of id suffixes
        self._max_id_num_by_prefix = defaultdict(lambda : 1)
        # Annotation by id, not includid non-ided annotations 
        self._ann_by_id = {}
        ###

        ## We use some heuristics to find the appropriate annotation files
        self._read_only = read_only
        input_files = self._select_input_files(document)

        if not input_files:
            with open('{}.{}'.format(document, JOINED_ANN_FILE_SUFF), 'w'):
                pass

            input_files = self._select_input_files(document)
            if not input_files:
                raise AnnotationFileNotFoundError(document)

        # We then try to open the files we got using the heuristics
        #self._file_input = FileInput(openhook=hook_encoded('utf-8'))
        self._input_files = input_files

        # Finally, parse the given annotation file
        try:
            self._parse_ann_file()
        
            # Sanity checking that can only be done post-parse
            self._sanity()
        except UnicodeDecodeError:
            Messager.error('Encoding error reading annotation file: '
                    'nonstandard encoding or binary?', -1)
            # TODO: more specific exception
            raise AnnotationFileNotFoundError(document)

        #XXX: Hack to get the timestamps after parsing
        if (len(self._input_files) == 1 and
                self._input_files[0].endswith(JOINED_ANN_FILE_SUFF)):
            self.ann_mtime = getmtime(self._input_files[0])
            self.ann_ctime = getctime(self._input_files[0])
        else:
            # We don't have a single file, just set to epoch for now
            self.ann_mtime = -1
            self.ann_ctime = -1

    def _sanity(self):
        # Beware, we ONLY do format checking, leave your semantics hat at home

        # Check that referenced IDs are defined
        for ann in self:
            for rid in chain(*ann.get_deps()):
                try:
                    self.get_ann_by_id(rid)
                except AnnotationNotFoundError:
                    # TODO: do more than just send a message for this error?
                    Messager.error('ID '+rid+' not defined, referenced from annotation '+str(ann))

        # Check that each event has a trigger
        for e_ann in self.get_events():
            try:
                tr_ann = self.get_ann_by_id(e_ann.trigger)

                # If the annotation is not text-bound or of different type
                if (not isinstance(tr_ann, TextBoundAnnotation) or
                        tr_ann.type != e_ann.type):
                    raise EventWithNonTriggerError(e_ann, tr_ann)
            except AnnotationNotFoundError:
                raise EventWithoutTriggerError(e_ann)

        # Check that every trigger is only referenced by events

        # Create a map for non-event references
        referenced_to_referencer = {}
        for non_e_ann in (a for a in self
                if not isinstance(a, EventAnnotation)
                and isinstance(a, IdedAnnotation)):
            for ref in chain(*non_e_ann.get_deps()):
                try:
                    referenced_to_referencer[ref].add(non_e_ann.id)
                except KeyError:
                    referenced_to_referencer[ref] = set((non_e_ann.id, ))

        # Ensure that no non-event references a trigger
        for tr_ann in self.get_triggers():
            if tr_ann.id in referenced_to_referencer:
                conflict_ann_ids = referenced_to_referencer[tr_ann.id]
                if BIONLP_ST_2013_COMPATIBILITY:
                    # Special-case processing for BioNLP ST 2013: allow
                    # Relations to reference event triggers (#926).
                    remaining_confict_ann_ids = set()
                    for rid in conflict_ann_ids:
                        referencer = self.get_ann_by_id(rid)
                        if not isinstance(referencer, BinaryRelationAnnotation):
                            remaining_confict_ann_ids.add(rid)
                        else:
                            self.externally_referenced_triggers.add(tr_ann.id)
                    conflict_ann_ids = remaining_confict_ann_ids
                # Note: Only reporting one of the conflicts (TODO)
                if conflict_ann_ids:
                    referencer = self.get_ann_by_id(list(conflict_ann_ids)[0])
                    raise TriggerReferenceError(tr_ann, referencer)
        
    def get_events(self):
        return (a for a in self if isinstance(a, EventAnnotation))
    
    def get_attributes(self):
        return (a for a in self if isinstance(a, AttributeAnnotation))

    def get_equivs(self):
        return (a for a in self if isinstance(a, EquivAnnotation))

    def get_textbounds(self):
        return (a for a in self if isinstance(a, TextBoundAnnotation))

    def get_relations(self):
        return (a for a in self if isinstance(a, BinaryRelationAnnotation))

    def get_normalizations(self):
        return (a for a in self if isinstance(a, NormalizationAnnotation))

    def get_entities(self):
        # Entities are textbounds that are not triggers
        triggers = [t for t in self.get_triggers()]
        return (a for a in self if (isinstance(a, TextBoundAnnotation) and
                                    not a in triggers))
    
    def get_oneline_comments(self):
        #XXX: The status exception is for the document status protocol
        #       which is yet to be formalised
        return (a for a in self if isinstance(a, OnelineCommentAnnotation)
                and a.type != 'STATUS')

    def get_statuses(self):
        return (a for a in self if isinstance(a, OnelineCommentAnnotation)
                and a.type == 'STATUS')

    def get_triggers(self):
        # Triggers are text-bounds referenced by events
        # TODO: this omits entity triggers that lack a referencing event
        # (for one reason or another -- brat shouldn't define any.)
        return (self.get_ann_by_id(e.trigger) for e in self.get_events())

    # TODO: getters for other categories of annotations
    #TODO: Remove read and use an internal and external version instead
    def add_annotation(self, ann, read=False):
        #log_info(u'Will add: ' + unicode(ann).rstrip('\n') + ' ' + unicode(type(ann)))
        #TODO: DOC!
        #TODO: Check read only
        if not read and self._read_only:
            raise AnnotationsIsReadOnlyError(self.get_document())

        # Equivs have to be merged with other equivs
        try:
            # Bail as soon as possible for non-equivs
            ann.entities # TODO: what is this?
            merge_cand = ann
            for eq_ann in self.get_equivs():
                try:
                    # Make sure that this Equiv duck quacks
                    eq_ann.entities
                except AttributeError, e:
                    assert False, 'got a non-entity from an entity call'

                # Do we have an entitiy in common with this equiv?
                for ent in merge_cand.entities:
                    if ent in eq_ann.entities:
                        for m_ent in merge_cand.entities:
                            if m_ent not in eq_ann.entities: 
                                eq_ann.entities.append(m_ent)
                        # Don't try to delete ann since it never was added
                        if merge_cand != ann:
                            try:
                                self.del_annotation(merge_cand)
                            except DependingAnnotationDeleteError:
                                assert False, ('Equivs lack ids and should '
                                        'never have dependent annotations')
                        merge_cand = eq_ann
                        # We already merged it all, break to the next ann
                        break

            if merge_cand != ann:
                # The proposed annotation was simply merged, no need to add it
                # Update the modification time
                from time import time
                self.ann_mtime = time()
                return

        except AttributeError:
            #XXX: This can catch a ton more than we want to! Ugly!
            # It was not an Equiv, skip along
            pass

        # Register the object id
        try:
            self._ann_by_id[ann.id] = ann
            pre, num = annotation_id_prefix(ann.id), annotation_id_number(ann.id)
            self._max_id_num_by_prefix[pre] = max(num, self._max_id_num_by_prefix[pre])
        except AttributeError:
            # The annotation simply lacked an id which is fine
            pass

        # Add the annotation as the last line
        self._lines.append(ann)
        self._line_by_ann[ann] = len(self) - 1
        # Update the modification time
        from time import time
        self.ann_mtime = time()

    def del_annotation(self, ann, tracker=None):
        #TODO: Check read only
        #TODO: Flag to allow recursion
        #TODO: Sampo wants to allow delet of direct deps but not indirect, one step
        #TODO: needed to pass tracker to track recursive mods, but use is too
        #      invasive (direct modification of ModificationTracker.deleted)
        #TODO: DOC!
        if self._read_only:
            raise AnnotationsIsReadOnlyError(self.get_document())

        try:
            ann.id
        except AttributeError:
            # If it doesn't have an id, nothing can depend on it
            if tracker is not None:
                tracker.deletion(ann)
            self._atomic_del_annotation(ann)
            # Update the modification time
            from time import time
            self.ann_mtime = time()
            return

        # collect annotations dependending on ann
        ann_deps = []

        for other_ann in self:
            soft_deps, hard_deps = other_ann.get_deps()
            if unicode(ann.id) in soft_deps | hard_deps:
                ann_deps.append(other_ann)
              
        # If all depending are AttributeAnnotations or EquivAnnotations,
        # delete all modifiers recursively (without confirmation) and remove
        # the annotation id from the equivs (and remove the equiv if there is
        # only one id left in the equiv)
        # Note: this assumes AttributeAnnotations cannot have
        # other dependencies depending on them, nor can EquivAnnotations
        if all((False for d in ann_deps if (
            not isinstance(d, AttributeAnnotation)
            and not isinstance(d, EquivAnnotation)
            and not isinstance(d, OnelineCommentAnnotation)
            and not isinstance(d, NormalizationAnnotation)
            ))):

            for d in ann_deps:
                if isinstance(d, AttributeAnnotation):
                    if tracker is not None:
                        tracker.deletion(d)
                    self._atomic_del_annotation(d)
                elif isinstance(d, EquivAnnotation):
                    if len(d.entities) <= 2:
                        # An equiv has to have more than one member
                        self._atomic_del_annotation(d)
                        if tracker is not None:
                            tracker.deletion(d)
                    else:
                        if tracker is not None:
                            before = unicode(d)
                        d.entities.remove(unicode(ann.id))
                        if tracker is not None:
                            tracker.change(before, d)
                elif isinstance(d, OnelineCommentAnnotation):
                    #TODO: Can't anything refer to comments?
                    self._atomic_del_annotation(d)
                    if tracker is not None:
                        tracker.deletion(d)
                elif isinstance(d, NormalizationAnnotation):
                    # Nothing should be able to reference normalizations
                    self._atomic_del_annotation(d)
                    if tracker is not None:
                        tracker.deletion(d)
                else:
                    # all types we allow to be deleted along with
                    # annotations they depend on should have been
                    # covered above.
                    assert False, "INTERNAL ERROR"
            ann_deps = []
            
        if ann_deps:
            raise DependingAnnotationDeleteError(ann, ann_deps)

        if tracker is not None:
            tracker.deletion(ann)
        self._atomic_del_annotation(ann)

    def _atomic_del_annotation(self, ann):
        #TODO: DOC
        # Erase the ann by id shorthand
        try:
            del self._ann_by_id[ann.id]
        except AttributeError:
            # So, we did not have id to erase in the first place
            pass

        ann_line = self._line_by_ann[ann]
        # Erase the main annotation
        del self._lines[ann_line]
        # Erase the ann by line shorthand
        del self._line_by_ann[ann]
        # Update the line shorthand of every annotation after this one
        # to reflect the new self._lines
        for l_num in xrange(ann_line, len(self)):
            self._line_by_ann[self[l_num]] = l_num
        # Update the modification time
        from time import time
        self.ann_mtime = time()
    
    def get_ann_by_id(self, id):
        #TODO: DOC
        try:
            return self._ann_by_id[id]
        except KeyError:
            raise AnnotationNotFoundError(id)

    def get_new_id(self, prefix, suffix=None):
        '''
        Return a new valid unique id for this annotation file for the given
        prefix. No ids are re-used for traceability over time for annotations,
        but this only holds for the lifetime of the annotation object. If the
        annotation file is parsed once again into an annotation object the
        next assigned id will be the maximum seen for a given prefix plus one
        which could have been deleted during a previous annotation session.

        Warning: get_new_id('T') == get_new_id('T')
        Just calling this method does not reserve the id, you need to
        add the annotation with the returned id to the annotation object in
        order to reserve it.

        Argument(s):
        id_pre - an annotation prefix on the format [A-Za-z]+

        Returns:
        An id that is guaranteed to be unique for the lifetime of the
        annotation.
        '''
        #XXX: We have changed this one radically!
        #XXX: Stupid and linear
        if suffix is None:
            suffix = ''
        #XXX: Arbitary constant!
        for suggestion in (prefix + unicode(i) + suffix for i in xrange(1, 2**15)):
            # This is getting more complicated by the minute, two checks since
            # the developers no longer know when it is an id or string.
            if suggestion not in self._ann_by_id:
                return suggestion

    # XXX: This syntax is subject to change
    def _parse_attribute_annotation(self, id, data, data_tail, input_file_path):
        match = re_match(r'(.+?) (.+?) (.+?)$', data)
        if match is None:
            # Is it an old format without value?
            match = re_match(r'(.+?) (.+?)$', data)

            if match is None:
                raise IdedAnnotationLineSyntaxError(id, self.ann_line,
                        self.ann_line_num + 1, input_file_path)
                
            _type, target = match.groups()
            value = True
        else:
            _type, target, value = match.groups()

        # Verify that the ID is indeed valid
        try:
            annotation_id_number(target)
        except InvalidIdError:
            raise IdedAnnotationLineSyntaxError(id, self.ann_line,
                    self.ann_line_num + 1, input_file_path)

        return AttributeAnnotation(target, id, _type, '', value, source_id=input_file_path)

    def _parse_event_annotation(self, id, data, data_tail, input_file_path):
        #XXX: A bit nasty, we require a single space
        try:
            type_delim = data.index(' ')
            type_trigger, type_trigger_tail = (data[:type_delim], data[type_delim:])
        except ValueError:
            type_trigger = data.rstrip('\r\n')
            type_trigger_tail = None

        try:
            type, trigger = type_trigger.split(':')
        except ValueError:
            # TODO: consider accepting events without triggers, e.g.
            # BioNLP ST 2011 Bacteria task
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        if type_trigger_tail is not None:
            args = [tuple(arg.split(':')) for arg in type_trigger_tail.split()]
        else:
            args = []

        return EventAnnotation(trigger, args, id, type, data_tail, source_id=input_file_path)


    def _parse_relation_annotation(self, id, data, data_tail, input_file_path):
        try:
            type_delim = data.index(' ')
            type, type_tail = (data[:type_delim], data[type_delim:])
        except ValueError:
            # cannot have a relation with just a type (contra event)
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)
            
        try:
            args = [tuple(arg.split(':')) for arg in type_tail.split()]
        except ValueError:
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        if len(args) != 2:
            Messager.error('Error parsing relation: must have exactly two arguments')
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        if args[0][0] == args[1][0]:
            Messager.error('Error parsing relation: arguments must not be identical')
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        return BinaryRelationAnnotation(id, type,
                                        args[0][0], args[0][1],
                                        args[1][0], args[1][1],
                                        data_tail, source_id=input_file_path)

    def _parse_equiv_annotation(self, dummy, data, data_tail, input_file_path):
        # NOTE: first dummy argument to have a uniform signature with other
        # parse_* functions
        # TODO: this will split on any space, which is likely not correct
        try:
            type, type_tail = data.split(None, 1)
        except ValueError:
            # no space: Equiv without arguments?
            raise AnnotationLineSyntaxError(self.ann_line, self.ann_line_num+1, input_file_path)
        equivs = type_tail.split(None)
        return EquivAnnotation(type, equivs, data_tail, source_id=input_file_path)

    # Parse an old modifier annotation for back-wards compability
    def _parse_modifier_annotation(self, id, data, data_tail, input_file_path):
        type, target = data.split()
        return AttributeAnnotation(target, id, type, data_tail, True, source_id=input_file_path)

    def _split_textbound_data(self, id, data, input_file_path):
        try:
            # first space-separated string is type
            type, rest = data.split(' ', 1)

            # rest should be semicolon-separated list of "START END"
            # pairs, where START and END are integers
            spans = []
            for span_str in rest.split(';'):
                start_str, end_str = span_str.split(' ', 2)

                # ignore trailing whitespace
                end_str = end_str.rstrip()

                if any((c.isspace() for c in end_str)):
                    Messager.error('Error parsing textbound "%s\t%s". (Using space instead of tab?)' % (id, data))
                    raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

                start, end = (int(start_str), int(end_str))
                spans.append((start, end))

        except:
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        return type, spans

    def _parse_textbound_annotation(self, _id, data, data_tail, input_file_path):
        _type, spans = self._split_textbound_data(_id, data, input_file_path)
        return TextBoundAnnotation(spans, _id, _type, data_tail, source_id=input_file_path)

    def _parse_normalization_annotation(self, _id, data, data_tail, input_file_path):
        # special-case processing for BioNLP ST 2013 variant of
        # normalization format
        if BIONLP_ST_2013_COMPATIBILITY:
            for r, s in BIONLP_ST_2013_NORMALIZATION_RES:
                d = r.sub(s, data, count=1)
                if d != data:
                    data = d
                    break
            
        match = re_match(r'(\S+) (\S+) (\S+?):(\S+)', data)
        if match is None:
            raise IdedAnnotationLineSyntaxError(_id, self.ann_line, self.ann_line_num + 1, input_file_path)
        _type, target, refdb, refid = match.groups()

        return NormalizationAnnotation(_id, _type, target, refdb, refid, data_tail, source_id=input_file_path)

    def _parse_comment_annotation(self, _id, data, data_tail, input_file_path):
        try:
            _type, target = data.split()
        except ValueError:
            raise IdedAnnotationLineSyntaxError(_id, self.ann_line, self.ann_line_num+1, input_file_path)
        return OnelineCommentAnnotation(target, _id, _type, data_tail, source_id=input_file_path)
    
    def _parse_ann_file(self):
        self.ann_line_num = -1
        for input_file_path in self._input_files:
            with open_textfile(input_file_path) as input_file:
                #for self.ann_line_num, self.ann_line in enumerate(self._file_input):
                for self.ann_line in input_file:
                    self.ann_line_num += 1
                    try:
                        # ID processing
                        try:
                            id, id_tail = self.ann_line.split('\t', 1)
                        except ValueError:
                            raise AnnotationLineSyntaxError(self.ann_line, self.ann_line_num+1, input_file_path)

                        pre = annotation_id_prefix(id)

                        if id in self._ann_by_id and pre != '*':
                            raise DuplicateAnnotationIdError(id,
                                    self.ann_line, self.ann_line_num+1,
                                    input_file_path)

                        # if the ID is not valid, need to fail with
                        # AnnotationLineSyntaxError (not
                        # IdedAnnotationLineSyntaxError).
                        if not is_valid_id(id):
                            raise AnnotationLineSyntaxError(self.ann_line, self.ann_line_num+1, input_file_path)

                        # Cases for lines
                        try:
                            data_delim = id_tail.index('\t')
                            data, data_tail = (id_tail[:data_delim],
                                    id_tail[data_delim:])
                        except ValueError:
                            data = id_tail
                            # No tail at all, although it should have a \t
                            data_tail = ''

                        new_ann = None

                        #log_info('Will evaluate prefix: ' + pre)

                        assert len(pre) >= 1, "INTERNAL ERROR"
                        pre_first = pre[0]

                        try:
                            parse_func = self._parse_function_by_id_prefix[pre_first]
                            new_ann = parse_func(id, data, data_tail, input_file_path)
                        except KeyError:
                            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

                        assert new_ann is not None, "INTERNAL ERROR"
                        self.add_annotation(new_ann, read=True)
                    except IdedAnnotationLineSyntaxError, e:
                        # Could parse an ID but not the whole line; add UnparsedIdedAnnotation
                        self.add_annotation(UnparsedIdedAnnotation(e.id,
                            e.line, source_id=e.filepath), read=True)
                        self.failed_lines.append(e.line_num - 1)

                    except AnnotationLineSyntaxError, e:
                        # We could not parse even an ID on the line, just add it as an unknown annotation
                        self.add_annotation(UnknownAnnotation(e.line,
                            source_id=e.filepath), read=True)
                        # NOTE: For access we start at line 0, not 1 as in here
                        self.failed_lines.append(e.line_num - 1)

    def __str__(self):
        s = u'\n'.join(unicode(ann).rstrip(u'\r\n') for ann in self)
        if not s:
            return u''
        else:
            return s if s[-1] == u'\n' else s + u'\n'

    def __it__(self):
        for ann in self._lines:
            yield ann

    def __getitem__(self, val):
        try:
            # First, try to use it as a slice object
            return self._lines[val.start, val.stop, val.step]
        except AttributeError:
            # It appears not to be a slice object, try it as an index
            return self._lines[val]

    def __len__(self):
        return len(self._lines)

    def __enter__(self):
        # No need to do any handling here, the constructor handles that
        return self
    
    def __exit__(self, type, value, traceback):
        #self._file_input.close()
        if not self._read_only:
            assert len(self._input_files) == 1, 'more than one valid outfile'

            # We are hitting the disk a lot more than we should here, what we
            # should have is a modification flag in the object but we can't
            # due to how we change the annotations.
            
            out_str = unicode(self)
            with open_textfile(self._input_files[0], 'r') as old_ann_file:
                old_str = old_ann_file.read()

            # Was it changed?
            if out_str == old_str:
                # Then just return
                return

            from config import WORK_DIR
            
            # Protect the write so we don't corrupt the file
            with file_lock(path_join(WORK_DIR,
                    str(hash(self._input_files[0].replace('/', '_')))
                        + '.lock')
                    ) as lock_file:
                #from tempfile import NamedTemporaryFile
                from tempfile import mkstemp
                # TODO: XXX: Is copyfile really atomic?
                from shutil import copyfile
                # XXX: NamedTemporaryFile only supports encoding for Python 3
                #       so we hack around it.
                #with NamedTemporaryFile('w', suffix='.ann') as tmp_file:
                # Grab the filename, but discard the handle
                tmp_fh, tmp_fname = mkstemp(suffix='.ann')
                os_close(tmp_fh)
                try:
                    with open_textfile(tmp_fname, 'w') as tmp_file:
                        #XXX: Temporary hack to make sure we don't write corrupted
                        #       files, but the client will already have the version
                        #       at this stage leading to potential problems upon
                        #       the next change to the file.
                        tmp_file.write(out_str)
                        tmp_file.flush()

                        try:
                            with Annotations(tmp_file.name) as ann:
                                # Move the temporary file onto the old file
                                copyfile(tmp_file.name, self._input_files[0])
                                # As a matter of convention we adjust the modified
                                # time of the data dir when we write to it. This
                                # helps us to make back-ups
                                now = time()
                                #XXX: Disabled for now!
                                #utime(DATA_DIR, (now, now))
                        except Exception, e:
                            Messager.error('ERROR writing changes: generated annotations cannot be read back in!\n(This is almost certainly a system error, please contact the developers.)\n%s' % e, -1)
                            raise
                finally:
                    try:
                        from os import remove
                        remove(tmp_fname)
                    except Exception, e:
                        Messager.error("Error removing temporary file '%s'" % tmp_fname)
            return

    def __in__(self, other):
        #XXX: You should do this one!
        pass


class TextAnnotations(Annotations):
    """
    Text-bound annotation storage. Extends Annotations in assuming
    access to text text to which the annotations apply and verifying
    the correctness of text-bound annotations against the text.
    """
    def __init__(self, document, read_only=False):
        # First read the text or the Annotations can't verify the annotations
        if document.endswith('.txt'):
            textfile_path = document
        else:
            # Do we have a known extension?
            _, file_ext = splitext(document)
            if not file_ext or not file_ext in KNOWN_FILE_SUFF:
                textfile_path = document
            else:
                textfile_path = document[:len(document) - len(file_ext)]

        self._document_text = self._read_document_text(textfile_path)
        
        Annotations.__init__(self, document, read_only)

    def _parse_textbound_annotation(self, id, data, data_tail, input_file_path):
        type, spans = self._split_textbound_data(id, data, input_file_path)

        # Verify spans
        seen_spans = []
        for start, end in spans:
            if start > end:
                Messager.error('Text-bound annotation start > end.')
                raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)
            if start < 0:
                Messager.error('Text-bound annotation start < 0.')
                raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)
            if end > len(self._document_text):
                Messager.error('Text-bound annotation offset exceeds text length.')
                raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

            for ostart, oend in seen_spans:
                if end >= ostart and start < oend:
                    Messager.error('Text-bound annotation spans overlap')
                    raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

            seen_spans.append((start,end))

        # first part is text, second connecting separators
        spanlen = sum([end-start for start, end in spans]) + (len(spans)-1)*len(DISCONT_SEP)

        # Require tail to be either empty or to begin with the text
        # corresponding to the catenation of the start:end spans. 
        # If the tail is empty, force a fill with the corresponding text.
        if data_tail.strip() == '' and spanlen > 0:
            Messager.error(u"Text-bound annotation missing text (expected format 'ID\\tTYPE START END\\tTEXT'). Filling from reference text. NOTE: This changes annotations on disk unless read-only.")
            text = "".join([self._document_text[start:end] for start, end in spans])

        elif data_tail[0] != '\t':
            Messager.error('Text-bound annotation missing tab before text (expected format "ID\\tTYPE START END\\tTEXT").')
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        elif spanlen > len(data_tail)-1: # -1 for tab
            Messager.error('Text-bound annotation text "%s" shorter than marked span(s) %s' % (data_tail[1:], str(spans)))
            raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        else:
            text = data_tail[1:spanlen+1] # shift 1 for tab
            data_tail = data_tail[spanlen+1:]

            spantexts = [self._document_text[start:end] for start, end in spans]
            reftext = DISCONT_SEP.join(spantexts)

            if text != reftext:
                # just in case someone has been running an old version of
                # discont that catenated spans without DISCONT_SEP
                oldstylereftext = ''.join(spantexts)
                if text[:len(oldstylereftext)] == oldstylereftext:
                    Messager.warning(u'NOTE: replacing old-style (pre-1.3) discontinuous annotation text span with new-style one, i.e. adding space to "%s" in .ann' % text[:len(oldstylereftext)], -1)
                    text = reftext
                    data_tail = ''
                else:
                    # unanticipated mismatch
                    Messager.error((u'Text-bound annotation text "%s" does not '
                                    u'match marked span(s) %s text "%s" in document') % (
                            text, str(spans), reftext.replace('\n','\\n')))
                    raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

            if data_tail != '' and not data_tail[0].isspace():
                Messager.error(u'Text-bound annotation text "%s" not separated from rest of line ("%s") by space!' % (text, data_tail))
                raise IdedAnnotationLineSyntaxError(id, self.ann_line, self.ann_line_num+1, input_file_path)

        return TextBoundAnnotationWithText(spans, id, type, text, data_tail, source_id=input_file_path)

    def get_document_text(self):
        return self._document_text

    def _read_document_text(self, document):
        # TODO: this is too naive; document may be e.g. "PMID.a1",
        # in which case the reasonable text file name guess is
        # "PMID.txt", not "PMID.a1.txt"
        textfn = document + '.' + TEXT_FILE_SUFFIX
        try:
            with open_textfile(textfn, 'r') as f:
                return f.read()
        except IOError:
            Messager.error('Error reading document text from %s' % textfn)
        raise AnnotationTextFileNotFoundError(document)

class Annotation(object):
    """
    Base class for all annotations.
    """
    def __init__(self, tail, source_id=None):
        self.tail = tail
        self.source_id = source_id

    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        return u'%s("%s")' % (unicode(self.__class__), unicode(self))
    
    def get_deps(self):
        return (set(), set())

class UnknownAnnotation(Annotation):
    """
    Represents a line of annotation that could not be parsed.
    These are not discarded, but rather passed through unmodified.
    """
    def __init__(self, line, source_id=None):
        Annotation.__init__(self, line, source_id=source_id)

    def __str__(self):
        return self.tail

class UnparsedIdedAnnotation(Annotation):
    """
    Represents an annotation for which an ID could be read but the
    rest of the line could not be parsed. This is separate from
    UnknownAnnotation to allow IDs for unparsed annotations to be
    "reserved".
    """
    # duck-type instead of inheriting from IdedAnnotation as
    # that inherits from TypedAnnotation and we have no type
    def __init__(self, id, line, source_id=None):
        # (this actually is the whole line, not just the id tail,
        # although Annotation will assign it to self.tail)
        Annotation.__init__(self, line, source_id=source_id)
        self.id = id

    def __str__(self):
        return unicode(self.tail)

class TypedAnnotation(Annotation):
    """
    Base class for all annotations with a type.
    """
    def __init__(self, type, tail, source_id=None):
        Annotation.__init__(self, tail, source_id=source_id)
        self.type = type

    def __str__(self):
        raise NotImplementedError

class IdedAnnotation(TypedAnnotation):
    """
    Base class for all annotations with an ID.
    """
    def __init__(self, id, type, tail, source_id=None):
        TypedAnnotation.__init__(self, type, tail, source_id=source_id)
        self.id = id

    def reference_id(self):
        """Returns a list that uniquely identifies this annotation within its document."""
        return [self.id]

    def reference_text(self):
        """Returns a human-readable string that identifies this annotation within its document."""
        return str(self.reference_id()[0])

    def __str__(self):
        raise NotImplementedError

def split_role(r):
    """
    Given a string R that may be suffixed with a number, returns a
    tuple (ROLE, NUM) where ROLE+NUM == R and NUM is the maximal
    suffix of R consisting only of digits.
    """
    i=len(r)
    while i>1 and r[i-1].isdigit():
        i -= 1
    return r[:i],r[i:]

class EventAnnotation(IdedAnnotation):
    """
    Represents an event annotation. Events are typed annotations that
    are associated with a specific text expression stating the event
    (TRIGGER, identifying a TextBoundAnnotation) and have an arbitrary
    number of arguments, each of which is represented as a ROLE:PARTID
    pair, where ROLE is a string identifying the role (e.g. "Theme",
    "Cause") and PARTID the ID of another annotation participating in
    the event.

    Represented in standoff as

    ID\tTYPE:TRIGGER [ROLE1:PART1 ROLE2:PART2 ...]
    """
    def __init__(self, trigger, args, id, type, tail, source_id=None):
        IdedAnnotation.__init__(self, id, type, tail, source_id=source_id)
        self.trigger = trigger
        self.args = args

    def add_argument(self, role, argid):
        # split into "main" role label and possible numeric suffix
        role, rnum = split_role(role)
        if rnum != '':
            # if given a role with an explicit numeric suffix,
            # use the role as given (assume number is part of
            # role label).
            pass
        else:
            # find next free numeric suffix.

            # for each argument role in existing roles, determine the
            # role numbers already used
            rnums = {}
            for r, aid in self.args:
                rb, rn = split_role(r)
                if rb not in rnums:
                    rnums[rb] = {}
                rnums[rb][rn] = True

            # find the first available free number for the current role,
            # using the convention that the empty number suffix stands for 1
            rnum = ''
            while role in rnums and rnum in rnums[role]:
                if rnum == '':
                    rnum = '2'
                else:
                    rnum = str(int(rnum)+1)

        # role+rnum is available, add
        self.args.append((role+rnum, argid))

    def __str__(self):
        return u'%s\t%s:%s %s%s' % (
                self.id,
                self.type,
                self.trigger,
                ' '.join([':'.join(map(str, arg_tup))
                    for arg_tup in self.args]),
                self.tail
                )

    def get_deps(self):
        soft_deps, hard_deps = IdedAnnotation.get_deps(self)
        hard_deps.add(self.trigger)
        arg_ids = [arg_tup[1] for arg_tup in self.args]
        # TODO: verify this logic, it's not entirely clear it's right
        if len(arg_ids) > 1:
            for arg in arg_ids:
                soft_deps.add(arg)
        else:
            for arg in arg_ids:
                hard_deps.add(arg)
        return (soft_deps, hard_deps)


class EquivAnnotation(TypedAnnotation):
    """
    Represents an equivalence group annotation. Equivs define a set of
    other annotations (normally TextBoundAnnotation) to be equivalent.

    Represented in standoff as
    
    *\tTYPE ID1 ID2 [...]

    Where "*" is the literal asterisk character.
    """
    def __init__(self, type, entities, tail, source_id=None):
        TypedAnnotation.__init__(self, type, tail, source_id=source_id)
        self.entities = entities

    def __in__(self, other):
        return other in self.entities

    def __str__(self):
        return u'*\t%s %s%s' % (
                self.type,
                ' '.join([unicode(e) for e in self.entities]),
                self.tail
                )

    def get_deps(self):
        soft_deps, hard_deps = TypedAnnotation.get_deps(self)
        if len(self.entities) > 2:
            for ent in self.entities:
                soft_deps.add(ent)
        else:
            for ent in self.entities:
                hard_deps.add(ent)
        return (soft_deps, hard_deps)

    def reference_id(self):
        if self.entities:
            return ['equiv', self.type, self.entities[0]]
        else:
            return ['equiv', self.type, self.entities]

    def reference_text(self):
        return '('+','.join([unicode(e) for e in self.entities])+')'

class AttributeAnnotation(IdedAnnotation):
    def __init__(self, target, id, type, tail, value, source_id=None):
        IdedAnnotation.__init__(self, id, type, tail, source_id=source_id)
        self.target = target
        self.value = value
        
    def __str__(self):
        return u'%s\t%s %s%s%s' % (
                self.id,
                self.type,
                self.target,
                # We hack in old modifiers with this trick using bools
                ' ' + unicode(self.value) if self.value != True else '',
                self.tail,
                )

    def get_deps(self):
        soft_deps, hard_deps = IdedAnnotation.get_deps(self)
        hard_deps.add(self.target)
        return (soft_deps, hard_deps)

    def reference_id(self):
        # TODO: can't currently ID modifier in isolation; return
        # reference to modified instead
        return [self.target]

class NormalizationAnnotation(IdedAnnotation):
    def __init__(self, _id, _type, target, refdb, refid, tail, source_id=None):
        IdedAnnotation.__init__(self, _id, _type, tail, source_id=source_id)
        self.target = target
        self.refdb = refdb
        self.refid = refid
        # "human-readable" text of referenced ID (optional)
        self.reftext = tail.lstrip('\t').rstrip('\n')

    def __str__(self):
        return u'%s\t%s %s %s:%s%s' % (
                self.id,
                self.type,
                self.target,
                self.refdb,
                self.refid,
                self.tail,
                )

    def get_deps(self):
        soft_deps, hard_deps = IdedAnnotation.get_deps(self)
        hard_deps.add(self.target)
        return (soft_deps, hard_deps)

    def reference_id(self):
        # TODO: can't currently ID normalization in isolation; return
        # reference to target instead
        return [self.target]

class OnelineCommentAnnotation(IdedAnnotation):
    def __init__(self, target, id, type, tail, source_id=None):
        IdedAnnotation.__init__(self, id, type, tail, source_id=source_id)
        self.target = target
        
    def __str__(self):
        return u'%s\t%s %s%s' % (
                self.id,
                self.type,
                self.target,
                self.tail
                )

    def get_text(self):
        # TODO: will this always hold? Wouldn't it be better to parse
        # further rather than just assuming the whole tail is the text?
        return self.tail.strip()

    def get_deps(self):
        soft_deps, hard_deps = IdedAnnotation.get_deps(self)
        hard_deps.add(self.target)
        return (soft_deps, hard_deps)


class TextBoundAnnotation(IdedAnnotation):
    """
    Represents a text-bound annotation. Text-bound annotations
    identify a specific span of text and assign it a type.  This base
    class does not assume ability to access text; use
    TextBoundAnnotationWithText for that.

    Represented in standoff as
    
    ID\tTYPE START END

    Where START and END are positive integer offsets identifying the
    span of the annotation in text. Discontinuous annotations can be
    represented as

    ID\tTYPE START1 END1;START2 END2;...

    with multiple START END pairs separated by semicolons.
    """

    def __init__(self, spans, id, type, tail, source_id=None):
        # Note: if present, the text goes into tail
        IdedAnnotation.__init__(self, id, type, tail, source_id=source_id)
        self.spans = spans

    # TODO: temp hack while building support for discontinuous
    # annotations; remove once done
    def get_start(self):
        Messager.warning('TextBoundAnnotation.start access')
        return self.spans[0][0]
    def get_end(self):
        Messager.warning('TextBoundAnnotation.end access')
        return self.spans[-1][1]
    start = property(get_start)
    end = property(get_end)
    # end hack

    def first_start(self):
        """
        Return the first (min) start offset in the annotation spans.
        """
        return min([start for start, end in self.spans])

    def last_end(self):
        """
        Return the last (max) end offset in the annotation spans.
        """
        return max([end for start, end in self.spans])

    def get_text(self):
        # If you're seeing this exception, you probably need a
        # TextBoundAnnotationWithText. The underlying issue may be
        # that you're creating an Annotations object instead of
        # TextAnnotations.
        raise NotImplementedError

    def same_span(self, other):
        """
        Determine if a given other TextBoundAnnotation has the same
        span as this one. Returns True if each (start, end) span of
        the other annotation is equivalent with at least one span of
        this annotation, False otherwise.
        """
        return set(self.spans) == set(other.spans)

    def contains(self, other):
        """
        Determine if a given other TextBoundAnnotation is contained in
        this one. Returns True if each (start, end) span of the other
        annotation is inside (or equivalent with) at least one span
        of this annotation, False otherwise.
        """
        for o_start, o_end in other.spans:
            contained = False
            for s_start, s_end in self.spans:
                if o_start >= s_start and o_end <= s_end:
                    contained = True
                    break
            if not contained:
                return False
        return True

    def __str__(self):
        return u'%s\t%s %s%s' % (
                self.id,
                self.type,
                ';'.join(['%d %d' % (start, end) for start, end in self.spans]),
                self.tail
                )

class TextBoundAnnotationWithText(TextBoundAnnotation):
    """
    Represents a text-bound annotation. Text-bound annotations
    identify a specific span of text and assign it a type.  This class
    assume that the referenced text is included in the annotation.

    Represented in standoff as

    ID\tTYPE START END\tTEXT

    Where START and END are positive integer offsets identifying the
    span of the annotation in text and TEXT is the corresponding text.
    Discontinuous annotations can be represented as

    ID\tTYPE START1 END1;START2 END2;...

    with multiple START END pairs separated by semicolons.
    """
    def __init__(self, spans, id, type, text, text_tail="", source_id=None):
        IdedAnnotation.__init__(self, id, type, '\t'+text+text_tail, source_id=source_id)
        self.spans = spans
        self.text = text
        self.text_tail = text_tail

    # TODO: temp hack while building support for discontinuous
    # annotations; remove once done
    def get_start(self):
        Messager.warning('TextBoundAnnotationWithText.start access')
        return self.spans[0][0]
    def get_end(self):
        Messager.warning('TextBoundAnnotationWithText.end access')
        return self.spans[-1][1]
    start = property(get_start)
    end = property(get_end)
    # end hack

    def get_text(self):
        return self.text

    def __str__(self):
        #log_info('TextBoundAnnotationWithText: __str__: "%s"' % self.text)
        return u'%s\t%s %s\t%s%s' % (
                self.id,
                self.type,
                ';'.join(['%d %d' % (start, end) for start, end in self.spans]),
                self.text,
                self.text_tail
                )

class BinaryRelationAnnotation(IdedAnnotation):
    """
    Represents a typed binary relation annotation. Relations are
    assumed not to be symmetric (i.e are "directed"); for equivalence
    relations, EquivAnnotation is likely to be more appropriate.
    Unlike events, relations are not associated with text expressions
    (triggers) stating them.

    Represented in standoff as

    ID\tTYPE ARG1:ID1 ARG2:ID2

    Where ARG1 and ARG2 are arbitrary (but not identical) labels.
    """
    def __init__(self, id, type, arg1l, arg1, arg2l, arg2, tail, source_id=None):
        IdedAnnotation.__init__(self, id, type, tail, source_id=source_id)
        self.arg1l = arg1l
        self.arg1  = arg1
        self.arg2l = arg2l
        self.arg2  = arg2

    def __str__(self):
        return u'%s\t%s %s:%s %s:%s%s' % (
            self.id,
            self.type,
            self.arg1l,
            self.arg1,
            self.arg2l,
            self.arg2,
            self.tail
            )
    
    def get_deps(self):
        soft_deps, hard_deps = IdedAnnotation.get_deps(self)
        hard_deps.add(self.arg1)
        hard_deps.add(self.arg2)
        return soft_deps, hard_deps

if __name__ == '__main__':
    from sys import stderr, argv
    for ann_path_i, ann_path in enumerate(argv[1:]):
        print >> stderr, ("%s.) '%s' " % (ann_path_i, ann_path, )
                ).ljust(80, '#')
        try:
            with Annotations(ann_path) as anns:
                for ann in anns:
                    print >> stderr, unicode(ann).rstrip('\n')
        except ImportError:
            # Will try to load the config, probably not available
            pass

########NEW FILE########
__FILENAME__ = annotator
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Annotator functionality, editing and retrieving status.

Author:     Pontus Stenetorp
Version:    2011-04-22
'''

# XXX: This module is messy, re-factor to be done

from __future__ import with_statement

from os.path import join as path_join
from os.path import split as path_split
from re import compile as re_compile

from annotation import (OnelineCommentAnnotation, TEXT_FILE_SUFFIX,
        TextAnnotations, DependingAnnotationDeleteError, TextBoundAnnotation,
        EventAnnotation, EquivAnnotation, open_textfile,
        AnnotationsIsReadOnlyError, AttributeAnnotation, 
        NormalizationAnnotation, SpanOffsetOverlapError, DISCONT_SEP)
from common import ProtocolError, ProtocolArgumentError
try:
    from config import DEBUG
except ImportError:
    DEBUG = False
from document import real_directory
from jsonwrap import loads as json_loads, dumps as json_dumps
from message import Messager
from projectconfig import ProjectConfiguration, ENTITY_CATEGORY, EVENT_CATEGORY, RELATION_CATEGORY, UNKNOWN_CATEGORY

### Constants
MUL_NL_REGEX = re_compile(r'\n+')
###

#TODO: Couldn't we incorporate this nicely into the Annotations class?
#TODO: Yes, it is even gimped compared to what it should do when not. This
#       has been a long pending goal for refactoring.
class ModificationTracker(object):
    def __init__(self):
        self.__added = []
        self.__changed = []
        self.__deleted = []

    def __len__(self):
        return len(self.__added) + len(self.__changed) + len(self.__deleted)

    def addition(self, added):
        self.__added.append(added)

    def deletion(self, deleted):
        self.__deleted.append(deleted)

    def change(self, before, after):
        self.__changed.append((before, after))

    def json_response(self, response=None):
        if response is None:
            response = {}

        # debugging
        if DEBUG:
            msg_str = ''
            if self.__added:
                msg_str += ('Added the following line(s):\n'
                        + '\n'.join([unicode(a).rstrip() for a in self.__added]))
            if self.__changed:
                changed_strs = []
                for before, after in self.__changed:
                    changed_strs.append('\t%s\n\tInto:\n\t%s' % (unicode(before).rstrip(), unicode(after).rstrip()))
                msg_str += ('Changed the following line(s):\n'
                        + '\n'.join([unicode(a).rstrip() for a in changed_strs]))
            if self.__deleted:
                msg_str += ('Deleted the following line(s):\n'
                        + '\n'.join([unicode(a).rstrip() for a in self.__deleted]))
            if msg_str:
                Messager.info(msg_str, duration=3*len(self))
            else:
                Messager.info('No changes made')

        # highlighting
        response['edited'] = []
        # TODO: implement cleanly, e.g. add a highlightid() method to Annotation classes
        for a in self.__added:
            try:
                response['edited'].append(a.reference_id())
            except AttributeError:
                pass # not all implement reference_id()
        for b,a in self.__changed:
            # can't mark "before" since it's stopped existing
            try:
                response['edited'].append(a.reference_id())
            except AttributeError:
                pass # not all implement reference_id()

        # unique, preserve order
        seen = set()
        uniqued = []
        for i in response['edited']:
            s = str(i)
            if s not in seen:
                uniqued.append(i)
                seen.add(s)
        response['edited'] = uniqued

        return response

# TODO: revive the "unconfirmed annotation" functionality;
# the following currently unused bit may help
# def confirm_span(docdir, docname, span_id):
#     document = path_join(docdir, docname)

#     txt_file_path = document + '.' + TEXT_FILE_SUFFIX

#     with TextAnnotations(document) as ann_obj:
#         mods = ModificationTracker()

#         # find AnnotationUnconfirmed comments that refer
#         # to the span and remove them
#         # TODO: error checking
#         for ann in ann_obj.get_oneline_comments():
#             if ann.type == "AnnotationUnconfirmed" and ann.target == span_id:
#                 ann_obj.del_annotation(ann, mods)

#         mods_json = mods.json_response()
#         # save a roundtrip and send the annotations also
#         j_dic = _json_from_ann(ann_obj)
#         mods_json['annotations'] = j_dic
#         add_messages_to_json(mods_json)
#         print dumps(mods_json)

def _json_from_ann(ann_obj):
    # Returns json with ann_obj contents and the relevant text.  Used
    # for saving a round-trip when modifying annotations by attaching
    # the latest annotation data into the response to the edit
    # request.
    j_dic = {}
    txt_file_path = ann_obj.get_document() + '.' + TEXT_FILE_SUFFIX
    from document import (_enrich_json_with_data, _enrich_json_with_base,
            _enrich_json_with_text)
    _enrich_json_with_base(j_dic)
    # avoid reading text file if the given ann_obj already holds it
    try:
        doctext = ann_obj.get_document_text()
    except AttributeError:
        # no such luck
        doctext = None
    _enrich_json_with_text(j_dic, txt_file_path, doctext)
    _enrich_json_with_data(j_dic, ann_obj)
    return j_dic

from logging import info as log_info
from annotation import TextBoundAnnotation, TextBoundAnnotationWithText
from copy import deepcopy

def _offsets_equal(o1, o2):
    """
    Given two lists of (start, end) integer offset sets, returns
    whether they identify the same sets of characters.
    """
    # TODO: full implementation; current doesn't check for special
    # cases such as dup or overlapping (start, end) pairs in a single
    # set.

    # short-circuit (expected to be the most common case)
    if o1 == o2:
        return True
    return sorted(o1) == sorted(o2)

def _text_for_offsets(text, offsets):
    """
    Given a text and a list of (start, end) integer offsets, returns
    the (catenated) text corresponding to those offsets, joined
    appropriately for use in a TextBoundAnnotation(WithText).
    """
    try:
        return DISCONT_SEP.join(text[s:e] for s,e in offsets)
    except Exception:
        Messager.error('_text_for_offsets: failed to get text for given offsets (%s)' % str(offsets))
        raise ProtocolArgumentError

def _edit_span(ann_obj, mods, id, offsets, projectconf, attributes, type,
        undo_resp={}):
    #TODO: Handle failure to find!
    ann = ann_obj.get_ann_by_id(id)

    if isinstance(ann, EventAnnotation):
        # We should actually modify the trigger
        tb_ann = ann_obj.get_ann_by_id(ann.trigger)
        e_ann = ann
        undo_resp['id'] = e_ann.id
        ann_category = EVENT_CATEGORY
    else:
        tb_ann = ann
        e_ann = None
        undo_resp['id'] = tb_ann.id
        ann_category = ENTITY_CATEGORY

    # Store away what we need to restore the old annotation
    undo_resp['action'] = 'mod_tb'
    undo_resp['offsets'] = tb_ann.spans[:]
    undo_resp['type'] = tb_ann.type

    if not _offsets_equal(tb_ann.spans, offsets):
        if not isinstance(tb_ann, TextBoundAnnotation):
            # TODO XXX: the following comment is no longer valid 
            # (possibly related code also) since the introduction of
            # TextBoundAnnotationWithText. Check.

            # This scenario has been discussed and changing the span inevitably
            # leads to the text span being out of sync since we can't for sure
            # determine where in the data format the text (if at all) it is
            # stored. For now we will fail loudly here.
            error_msg = ('unable to change the span of an existing annotation'
                    '(annotation: %s)' % repr(tb_ann))
            Messager.error(error_msg)
            # Not sure if we only get an internal server error or the data
            # will actually reach the client to be displayed.
            assert False, error_msg
        else:
            # TODO: Log modification too?
            before = unicode(tb_ann)
            #log_info('Will alter span of: "%s"' % str(to_edit_span).rstrip('\n'))
            tb_ann.spans = offsets[:]
            tb_ann.text = _text_for_offsets(ann_obj._document_text, tb_ann.spans)
            #log_info('Span altered')
            mods.change(before, tb_ann)

    if ann.type != type:
        if ann_category != projectconf.type_category(type):
            # Can't convert event to entity etc. (The client should protect
            # against this in any case.)
            # TODO: Raise some sort of protocol error
            Messager.error("Cannot convert %s (%s) into %s (%s)"
                    % (ann.type, projectconf.type_category(ann.type),
                        type, projectconf.type_category(type)),
                           duration=10)
            pass
        else:
            before = unicode(ann)
            ann.type = type

            # Try to propagate the type change
            try:
                #XXX: We don't take into consideration other anns with the
                # same trigger here!
                ann_trig = ann_obj.get_ann_by_id(ann.trigger)
                if ann_trig.type != ann.type:
                    # At this stage we need to determine if someone else
                    # is using the same trigger
                    if any((event_ann
                        for event_ann in ann_obj.get_events()
                        if (event_ann.trigger == ann.trigger
                                and event_ann != ann))):
                        # Someone else is using it, create a new one
                        from copy import copy
                        # A shallow copy should be enough
                        new_ann_trig = copy(ann_trig)
                        # It needs a new id
                        new_ann_trig.id = ann_obj.get_new_id('T')
                        # And we will change the type
                        new_ann_trig.type = ann.type
                        # Update the old annotation to use this trigger
                        ann.trigger = unicode(new_ann_trig.id)
                        ann_obj.add_annotation(new_ann_trig)
                        mods.addition(new_ann_trig)
                    else:
                        # Okay, we own the current trigger, but does an
                        # identical to our sought one already exist?
                        found = None
                        for tb_ann in ann_obj.get_textbounds():
                            if (_offsets_equal(tb_ann.spans, ann_trig.spans) and
                                tb_ann.type == ann.type):
                                found = tb_ann
                                break

                        if found is None:
                            # Just change the trigger type since we are the
                            # only users
                            before = unicode(ann_trig)
                            ann_trig.type = ann.type
                            mods.change(before, ann_trig)
                        else:
                            # Attach the new trigger THEN delete
                            # or the dep will hit you
                            ann.trigger = unicode(found.id)
                            ann_obj.del_annotation(ann_trig)
                            mods.deletion(ann_trig)
            except AttributeError:
                # It was most likely a TextBound entity
                pass

            # Finally remember the change
            mods.change(before, ann)
    return tb_ann, e_ann

def __create_span(ann_obj, mods, type, offsets, txt_file_path,
        projectconf, attributes):
    # For event types, reuse trigger if a matching one exists.
    found = None
    if projectconf.is_event_type(type):
        for tb_ann in ann_obj.get_textbounds():
            try:
                if (_offsets_equal(tb_ann.spans, offsets)
                    and tb_ann.type == type):
                    found = tb_ann
                    break
            except AttributeError:
                # Not a trigger then
                pass
        
    if found is None:
        # Get a new ID
        new_id = ann_obj.get_new_id('T') #XXX: Cons
        # Get the text span
        with open_textfile(txt_file_path, 'r') as txt_file:
            text = txt_file.read()
            text_span = _text_for_offsets(text, offsets)

        # The below code resolves cases where there are newlines in the
        #   offsets by creating discontinuous annotations for each span
        #   separated by newlines. For most cases it preserves the offsets.
        seg_offsets = []
        for o_start, o_end in offsets:
            pos = o_start
            for text_seg in text_span.split('\n'):
                if not text_seg and o_start != o_end:
                    # Double new-line, skip ahead
                    pos += 1
                    continue
                start = pos
                end = start + len(text_seg)

                # For the next iteration the position is after the newline.
                pos = end + 1

                # Adjust the offsets to compensate for any potential leading
                #   and trailing whitespace.
                start += len(text_seg) - len(text_seg.lstrip())
                end -= len(text_seg) - len(text_seg.rstrip())

                # If there is any segment left, add it to the offsets.
                if start != end:
                    seg_offsets.append((start, end, ))

        # if we're dealing with a null-span
        if not seg_offsets:
            seg_offsets = offsets

        ann_text = DISCONT_SEP.join((text[start:end]
            for start, end in seg_offsets))
        ann = TextBoundAnnotationWithText(seg_offsets, new_id, type, ann_text)
        ann_obj.add_annotation(ann)
        mods.addition(ann)
    else:
        ann = found

    if ann is not None:
        if projectconf.is_physical_entity_type(type):
            # TODO: alert that negation / speculation are ignored if set
            event = None
        else:
            # Create the event also
            new_event_id = ann_obj.get_new_id('E') #XXX: Cons
            event = EventAnnotation(ann.id, [], unicode(new_event_id), type, '')
            ann_obj.add_annotation(event)
            mods.addition(event)
    else:
        # We got a newline in the span, don't take any action
        event = None

    return ann, event

def _set_attributes(ann_obj, ann, attributes, mods, undo_resp={}):
    # Find existing attributes (if any)
    existing_attr_anns = set((a for a in ann_obj.get_attributes()
            if a.target == ann.id))

    #log_info('ATTR: %s' %(existing_attr_anns, ))

    # Note the existing annotations for undo
    undo_resp['attributes'] = json_dumps(dict([(e.type, e.value)
        for e in existing_attr_anns]))

    for existing_attr_ann in existing_attr_anns:
        if existing_attr_ann.type not in attributes:
            # Delete attributes that were un-set existed previously
            ann_obj.del_annotation(existing_attr_ann)
            mods.deletion(existing_attr_ann)
        else:
            # If the value of the attribute is different, alter it
            new_value = attributes[existing_attr_ann.type]
            #log_info('ATTR: "%s" "%s"' % (new_value, existing_attr_ann.value))
            if existing_attr_ann.value != new_value:
                before = unicode(existing_attr_ann)
                existing_attr_ann.value = new_value
                mods.change(before, existing_attr_ann)

    # The remaining annotations are new and should be created
    for attr_type, attr_val in attributes.iteritems():
        if attr_type not in set((a.type for a in existing_attr_anns)):
            new_attr = AttributeAnnotation(ann.id, ann_obj.get_new_id('A'),
                    attr_type, '', attr_val)
            ann_obj.add_annotation(new_attr)
            mods.addition(new_attr)

def _json_offsets_to_list(offsets):
    try:
        offsets = json_loads(offsets)
    except Exception:
        Messager.error('create_span: protocol argument error: expected offsets as JSON, but failed to parse "%s"' % str(offsets))
        raise ProtocolArgumentError
    try:
        offsets = [(int(s),int(e)) for s,e in offsets]
    except Exception:
        Messager.error('create_span: protocol argument error: expected offsets as list of int pairs, received "%s"' % str(offsets))
        raise ProtocolArgumentError
    return offsets

#TODO: unshadow Python internals like "type" and "id"
def create_span(collection, document, offsets, type, attributes=None,
                normalizations=None, id=None, comment=None):
    # offsets should be JSON string corresponding to a list of (start,
    # end) pairs; convert once at this interface
    offsets = _json_offsets_to_list(offsets)

    return _create_span(collection, document, offsets, type, attributes,
                        normalizations, id, comment)

def _set_normalizations(ann_obj, ann, normalizations, mods, undo_resp={}):
    # Find existing normalizations (if any)
    existing_norm_anns = set((a for a in ann_obj.get_normalizations()
            if a.target == ann.id))

    # Note the existing annotations for undo
    undo_resp['normalizations'] = json_dumps([(n.refdb, n.refid, n.reftext)
                                              for n in existing_norm_anns])

    # Organize into dictionaries for easier access
    old_norms = dict([((n.refdb,n.refid),n) for n in existing_norm_anns])
    new_norms = dict([((n[0],n[1]), n[2]) for n in normalizations])

    #Messager.info("Old norms: "+str(old_norms))
    #Messager.info("New norms: "+str(new_norms))

    # sanity check
    for refdb, refid, refstr in normalizations:
        # TODO: less aggressive failure
        assert refdb is not None and refdb.strip() != '', "Error: client sent empty norm DB"
        assert refid is not None and refid.strip() != '', "Error: client sent empty norm ID"
        # (the reference string is allwed to be empty)

    # Process deletions and updates of existing normalizations
    for old_norm_id, old_norm in old_norms.items():
        if old_norm_id not in new_norms:
            # Delete IDs that were referenced previously but not anymore
            ann_obj.del_annotation(old_norm)
            mods.deletion(old_norm)
        else:
            # If the text value of the normalizations is different, update
            # (this shouldn't happen on a stable norm DB, but anyway)
            new_reftext = new_norms[old_norm_id]
            if old_norm.reftext != new_reftext:
                old = unicode(old_norm)
                old_norm.reftext = new_reftext
                mods.change(old, old_norm)

    # Process new normalizations
    for new_norm_id, new_reftext in new_norms.items():
        if new_norm_id not in old_norms:
            new_id = ann_obj.get_new_id('N')
            # TODO: avoid magic string value
            norm_type = u'Reference'
            new_norm = NormalizationAnnotation(new_id, norm_type,
                                               ann.id, new_norm_id[0],
                                               new_norm_id[1],
                                               u'\t'+new_reftext)
            ann_obj.add_annotation(new_norm)
            mods.addition(new_norm)

# helper for _create methods
def _parse_attributes(attributes):
    if attributes is None:
        _attributes = {}
    else:
        try:
            _attributes =  json_loads(attributes)
        except ValueError:
            # Failed to parse, warn the client
            Messager.warning((u'Unable to parse attributes string "%s" for '
                    u'"createSpan", ignoring attributes for request and '
                    u'assuming no attributes set') % (attributes, ))
            _attributes = {}

        ### XXX: Hack since the client is sending back False and True as values...
        # These are __not__ to be sent, they violate the protocol
        for _del in [k for k, v in _attributes.items() if v == False]:
            del _attributes[_del]

        # These are to be old-style modifiers without values
        for _revalue in [k for k, v in _attributes.items() if v == True]:
            _attributes[_revalue] = True
        ###
    return _attributes

# helper for _create_span
def _parse_span_normalizations(normalizations):
    if normalizations is None:
        _normalizations = {}
    else:
        try:
            _normalizations = json_loads(normalizations)
        except ValueError:
            # Failed to parse, warn the client
            Messager.warning((u'Unable to parse normalizations string "%s" for '
                    u'"createSpan", ignoring normalizations for request and '
                    u'assuming no normalizations set') % (normalizations, ))
            _normalizations = {}

    return _normalizations

# Helper for _create functions
def _set_comments(ann_obj, ann, comment, mods, undo_resp={}):
    # We are only interested in id;ed comments
    try:
        ann.id
    except AttributeError:
        return None

    # Check if there is already an annotation comment
    for com_ann in ann_obj.get_oneline_comments():
        if (com_ann.type == 'AnnotatorNotes'
                and com_ann.target == ann.id):
            found = com_ann

            # Note the comment in the undo
            undo_resp['comment'] = found.tail[1:]
            break
    else:
        found = None

    if comment:
        if found is not None:
            # Change the comment
            # XXX: Note the ugly tab, it is for parsing the tail
            before = unicode(found)
            found.tail = u'\t' + comment
            mods.change(before, found)
        else:
            # Create a new comment
            new_comment = OnelineCommentAnnotation(
                    ann.id, ann_obj.get_new_id('#'),
                    # XXX: Note the ugly tab
                    u'AnnotatorNotes', u'\t' + comment)
            ann_obj.add_annotation(new_comment)
            mods.addition(new_comment)
    else:
        # We are to erase the annotation
        if found is not None:
            ann_obj.del_annotation(found)
            mods.deletion(found)

# Sanity check, a span can't overlap itself
def _offset_overlaps(offsets):
    for i in xrange(len(offsets)):
        i_start, i_end = offsets[i]
        for j in xrange(i + 1, len(offsets)):
            j_start, j_end = offsets[j]
            if (
                    # i overlapping or in j
                    (j_start <= i_start < j_end) or (j_start < i_end < j_end)
                    or
                    # j overlapping or in i
                    (i_start <= j_start < i_end) or (i_start < j_end < i_end)
                    ):
                return True
    # No overlap detected
    return False

#TODO: ONLY determine what action to take! Delegate to Annotations!
def _create_span(collection, document, offsets, _type, attributes=None,
                 normalizations=None, _id=None, comment=None):

    if _offset_overlaps(offsets):
        raise SpanOffsetOverlapError(offsets)

    directory = collection
    undo_resp = {}

    _attributes = _parse_attributes(attributes)
    _normalizations = _parse_span_normalizations(normalizations)

    #log_info('ATTR: %s' %(_attributes, ))

    real_dir = real_directory(directory)
    document = path_join(real_dir, document)

    projectconf = ProjectConfiguration(real_dir)

    txt_file_path = document + '.' + TEXT_FILE_SUFFIX

    working_directory = path_split(document)[0]

    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        mods = ModificationTracker()

        if _id is not None:
            # We are to edit an existing annotation
            tb_ann, e_ann = _edit_span(ann_obj, mods, _id, offsets, projectconf,
                    _attributes, _type, undo_resp=undo_resp)
        else:
            # We are to create a new annotation
            tb_ann, e_ann = __create_span(ann_obj, mods, _type, offsets, txt_file_path,
                    projectconf, _attributes)

            undo_resp['action'] = 'add_tb'
            if e_ann is not None:
                undo_resp['id'] = e_ann.id
            else:
                undo_resp['id'] = tb_ann.id

        # Determine which annotation attributes, normalizations,
        # comments etc. should be attached to. If there's an event,
        # attach to that; otherwise attach to the textbound.
        if e_ann is not None:
            # Assign to the event, not the trigger
            target_ann = e_ann
        else:
            target_ann = tb_ann

        # Set attributes
        _set_attributes(ann_obj, target_ann, _attributes, mods,
                        undo_resp=undo_resp)

        # Set normalizations
        _set_normalizations(ann_obj, target_ann, _normalizations, mods,
                            undo_resp=undo_resp)

        # Set comments
        if tb_ann is not None:
            _set_comments(ann_obj, target_ann, comment, mods,
                          undo_resp=undo_resp)

        if tb_ann is not None:
            mods_json = mods.json_response()
        else:
            # Hack, probably we had a new-line in the span
            mods_json = {}
            Messager.error('Text span contained new-line, rejected', duration=3)

        if undo_resp:
            mods_json['undo'] = json_dumps(undo_resp)
        mods_json['annotations'] = _json_from_ann(ann_obj)
        return mods_json

from annotation import BinaryRelationAnnotation

def _create_equiv(ann_obj, projectconf, mods, origin, target, type, attributes,
                  old_type, old_target):

    # due to legacy representation choices for Equivs (i.e. no
    # unique ID), support for attributes for Equivs would need
    # some extra work. Getting the easy non-Equiv case first.
    if attributes is not None:
        Messager.warning('_create_equiv: attributes for Equiv annotation not supported yet, please tell the devs if you need this feature (mention "issue #799").')
        attributes = None

    ann = None

    if old_type is None:
        # new annotation

        # sanity
        assert old_target is None, '_create_equiv: incoherent args: old_type is None, old_target is not None (client/protocol error?)'

        ann = EquivAnnotation(type, [unicode(origin.id), 
                                     unicode(target.id)], '')
        ann_obj.add_annotation(ann)
        mods.addition(ann)

        # TODO: attributes
        assert attributes is None, "INTERNAL ERROR" # see above
    else:
        # change to existing Equiv annotation. Other than the no-op
        # case, this remains TODO.
        assert projectconf.is_equiv_type(old_type), 'attempting to change equiv relation to non-equiv relation, operation not supported'

        # sanity
        assert old_target is not None, '_create_equiv: incoherent args: old_type is not None, old_target is None (client/protocol error?)'

        if old_type != type:
            Messager.warning('_create_equiv: equiv type change not supported yet, please tell the devs if you need this feature (mention "issue #798").')

        if old_target != target.id:
            Messager.warning('_create_equiv: equiv reselect not supported yet, please tell the devs if you need this feature (mention "issue #797").')

        # TODO: attributes
        assert attributes is None, "INTERNAL ERROR" # see above

    return ann

def _create_relation(ann_obj, projectconf, mods, origin, target, type,
                     attributes, old_type, old_target, undo_resp={}):
    attributes = _parse_attributes(attributes)

    if old_type is not None or old_target is not None:
        assert type in projectconf.get_relation_types(), (
                ('attempting to convert relation to non-relation "%s" ' % (target.type, )) +
                ('(legit types: %s)' % (unicode(projectconf.get_relation_types()), )))

        sought_target = (old_target
                if old_target is not None else target.id)
        sought_type = (old_type
                if old_type is not None else type)
        sought_origin = origin.id

        # We are to change the type, target, and/or attributes
        found = None
        for ann in ann_obj.get_relations():
            if (ann.arg1 == sought_origin and ann.arg2 == sought_target and 
                ann.type == sought_type):
                found = ann
                break

        if found is None:
            # TODO: better response
            Messager.error('_create_relation: failed to identify target relation (type %s, target %s) (deleted?)' % (str(old_type), str(old_target)))
        elif found.arg2 == target.id and found.type == type:
            # no changes to type or target
            pass
        else:
            # type and/or target changed, mark.
            before = unicode(found)
            found.arg2 = target.id
            found.type = type
            mods.change(before, found)

        target_ann = found
    else:
        # Create a new annotation
        new_id = ann_obj.get_new_id('R')
        # TODO: do we need to support different relation arg labels
        # depending on participant types? This doesn't.         
        rels = projectconf.get_relations_by_type(type) 
        rel = rels[0] if rels else None
        assert rel is not None and len(rel.arg_list) == 2
        a1l, a2l = rel.arg_list
        ann = BinaryRelationAnnotation(new_id, type, a1l, origin.id, a2l, target.id, '\t')
        mods.addition(ann)
        ann_obj.add_annotation(ann)

        target_ann = ann

    # process attributes
    if target_ann is not None:
        _set_attributes(ann_obj, ann, attributes, mods, undo_resp)
    elif attributes != None:
        Messager.error('_create_relation: cannot set arguments: failed to identify target relation (type %s, target %s) (deleted?)' % (str(old_type), str(old_target)))        

    return target_ann

def _create_argument(ann_obj, projectconf, mods, origin, target, type,
                     attributes, old_type, old_target):
    try:
        arg_tup = (type, unicode(target.id))

        # Is this an addition or an update?
        if old_type is None and old_target is None:
            if arg_tup not in origin.args:
                before = unicode(origin)
                origin.add_argument(type, unicode(target.id))
                mods.change(before, origin)
            else:
                # It already existed as an arg, we were called to do nothing...
                pass
        else:
            # Construct how the old arg would have looked like
            old_arg_tup = (type if old_type is None else old_type,
                    target if old_target is None else old_target)

            if old_arg_tup in origin.args and arg_tup not in origin.args:
                before = unicode(origin)
                origin.args.remove(old_arg_tup)
                origin.add_argument(type, unicode(target.id))
                mods.change(before, origin)
            else:
                # Collision etc. don't do anything
                pass
    except AttributeError:
        # The annotation did not have args, it was most likely an entity
        # thus we need to create a new Event...
        new_id = ann_obj.get_new_id('E')
        ann = EventAnnotation(
                    origin.id,
                    [arg_tup],
                    new_id,
                    origin.type,
                    ''
                    )
        ann_obj.add_annotation(ann)
        mods.addition(ann)

    # No addressing mechanism for arguments at the moment
    return None

def reverse_arc(collection, document, origin, target, type, attributes=None):
    directory = collection
    #undo_resp = {} # TODO
    real_dir = real_directory(directory)
    #mods = ModificationTracker() # TODO
    projectconf = ProjectConfiguration(real_dir)
    document = path_join(real_dir, document)
    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        if projectconf.is_equiv_type(type):
            Messager.warning('Cannot reverse Equiv arc')
        elif not projectconf.is_relation_type(type):
            Messager.warning('Can only reverse configured binary relations')
        else:
            # OK to reverse
            found = None
            # TODO: more sensible lookup
            for ann in ann_obj.get_relations():
                if (ann.arg1 == origin and ann.arg2 == target and
                    ann.type == type):
                    found = ann
                    break
            if found is None:
                Messager.error('reverse_arc: failed to identify target relation (from %s to %s, type %s) (deleted?)' % (str(origin), str(target), str(type)))
            else:
                # found it; just adjust this
                found.arg1, found.arg2 = found.arg2, found.arg1
                # TODO: modification tracker

        json_response = {}
        json_response['annotations'] = _json_from_ann(ann_obj)
        return json_response

# TODO: undo support
def create_arc(collection, document, origin, target, type, attributes=None,
        old_type=None, old_target=None, comment=None):
    directory = collection
    undo_resp = {}

    real_dir = real_directory(directory)

    mods = ModificationTracker()

    projectconf = ProjectConfiguration(real_dir)

    document = path_join(real_dir, document)

    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        # TODO: make consistent across the different editing
        # functions, integrate ann_obj initialization and checks
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        origin = ann_obj.get_ann_by_id(origin) 
        target = ann_obj.get_ann_by_id(target)

        # if there is a previous annotation and the arcs aren't in
        # the same category (e.g. relation vs. event arg), process
        # as delete + create instead of update.
        if old_type is not None and (
            projectconf.is_relation_type(old_type) != 
            projectconf.is_relation_type(type) or
            projectconf.is_equiv_type(old_type) !=
            projectconf.is_equiv_type(type)):
            _delete_arc_with_ann(origin.id, old_target, old_type, mods, 
                                 ann_obj, projectconf)
            old_target, old_type = None, None

        if projectconf.is_equiv_type(type):
            ann =_create_equiv(ann_obj, projectconf, mods, origin, target, 
                               type, attributes, old_type, old_target)

        elif projectconf.is_relation_type(type):
            ann = _create_relation(ann_obj, projectconf, mods, origin, target, 
                                   type, attributes, old_type, old_target)
        else:
            ann = _create_argument(ann_obj, projectconf, mods, origin, target,
                                   type, attributes, old_type, old_target)

        # process comments
        if ann is not None:
            _set_comments(ann_obj, ann, comment, mods,
                          undo_resp=undo_resp)
        elif comment is not None:
            Messager.warning('create_arc: non-empty comment for None annotation (unsupported type for comment?)')
            

        mods_json = mods.json_response()
        mods_json['annotations'] = _json_from_ann(ann_obj)
        return mods_json

# helper for delete_arc
def _delete_arc_equiv(origin, target, type_, mods, ann_obj):
    # TODO: this is slow, we should have a better accessor
    for eq_ann in ann_obj.get_equivs():
        # We don't assume that the ids only occur in one Equiv, we
        # keep on going since the data "could" be corrupted
        if (unicode(origin) in eq_ann.entities and 
            unicode(target) in eq_ann.entities and
            type_ == eq_ann.type):
            before = unicode(eq_ann)
            eq_ann.entities.remove(unicode(origin))
            eq_ann.entities.remove(unicode(target))
            mods.change(before, eq_ann)

        if len(eq_ann.entities) < 2:
            # We need to delete this one
            try:
                ann_obj.del_annotation(eq_ann)
                mods.deletion(eq_ann)
            except DependingAnnotationDeleteError, e:
                #TODO: This should never happen, dep on equiv
                raise

    # TODO: warn on failure to delete?

# helper for delete_arc
def _delete_arc_nonequiv_rel(origin, target, type_, mods, ann_obj):
    # TODO: this is slow, we should have a better accessor
    for ann in ann_obj.get_relations():
        if ann.type == type_ and ann.arg1 == origin and ann.arg2 == target:
            ann_obj.del_annotation(ann)
            mods.deletion(ann)

    # TODO: warn on failure to delete?

# helper for delete_arc
def _delete_arc_event_arg(origin, target, type_, mods, ann_obj):
    event_ann = ann_obj.get_ann_by_id(origin)
    # Try if it is an event
    arg_tup = (type_, unicode(target))
    if arg_tup in event_ann.args:
        before = unicode(event_ann)
        event_ann.args.remove(arg_tup)
        mods.change(before, event_ann)
    else:
        # What we were to remove did not even exist in the first place
        # TODO: warn on failure to delete?
        pass

def _delete_arc_with_ann(origin, target, type_, mods, ann_obj, projectconf):
    origin_ann = ann_obj.get_ann_by_id(origin)

    # specifics of delete determined by arc type (equiv relation,
    # other relation, event argument)
    if projectconf.is_relation_type(type_):
        if projectconf.is_equiv_type(type_):
            _delete_arc_equiv(origin, target, type_, mods, ann_obj)
        else:
            _delete_arc_nonequiv_rel(origin, target, type_, mods, ann_obj)
    elif projectconf.is_event_type(origin_ann.type):
        _delete_arc_event_arg(origin, target, type_, mods, ann_obj)
    else:
        Messager.error('Unknown annotation types for delete')

def delete_arc(collection, document, origin, target, type):
    directory = collection

    real_dir = real_directory(directory)

    mods = ModificationTracker()

    projectconf = ProjectConfiguration(real_dir)

    document = path_join(real_dir, document)

    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        _delete_arc_with_ann(origin, target, type, mods, ann_obj, projectconf)

        mods_json = mods.json_response()
        mods_json['annotations'] = _json_from_ann(ann_obj)
        return mods_json

    # TODO: error handling?

#TODO: ONLY determine what action to take! Delegate to Annotations!
def delete_span(collection, document, id):
    directory = collection

    real_dir = real_directory(directory)

    document = path_join(real_dir, document)
    
    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        mods = ModificationTracker()
        
        #TODO: Handle a failure to find it
        #XXX: Slow, O(2N)
        ann = ann_obj.get_ann_by_id(id)
        try:
            # Note: need to pass the tracker to del_annotation to track
            # recursive deletes. TODO: make usage consistent.
            ann_obj.del_annotation(ann, mods)
            try:
                trig = ann_obj.get_ann_by_id(ann.trigger)
                try:
                    ann_obj.del_annotation(trig, mods)
                except DependingAnnotationDeleteError:
                    # Someone else depended on that trigger
                    pass
            except AttributeError:
                pass
        except DependingAnnotationDeleteError, e:
            Messager.error(e.html_error_str())
            return {
                    'exception': True,
                    }

        mods_json = mods.json_response()
        mods_json['annotations'] = _json_from_ann(ann_obj)
        return mods_json

class AnnotationSplitError(ProtocolError):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

    def json(self, json_dic):
        json_dic['exception'] = 'annotationSplitError'
        Messager.error(self.message)
        return json_dic

def split_span(collection, document, args, id):
    directory = collection

    real_dir = real_directory(directory)
    document = path_join(real_dir, document)
    # TODO don't know how to pass an array directly, so doing extra catenate and split
    tosplit_args = json_loads(args)
    
    with TextAnnotations(document) as ann_obj:
        # bail as quick as possible if read-only 
        if ann_obj._read_only:
            raise AnnotationsIsReadOnlyError(ann_obj.get_document())

        mods = ModificationTracker()
        
        ann = ann_obj.get_ann_by_id(id)

        # currently only allowing splits for events
        if not isinstance(ann, EventAnnotation):
            raise AnnotationSplitError("Cannot split an annotation of type %s" % ann.type)

        # group event arguments into ones that will be split on and
        # ones that will not, placing the former into a dict keyed by
        # the argument without trailing numbers (e.g. "Theme1" ->
        # "Theme") and the latter in a straight list.
        split_args = {}
        nonsplit_args = []
        import re
        for arg, aid in ann.args:
            m = re.match(r'^(.*?)\d*$', arg)
            if m:
                arg = m.group(1)
            if arg in tosplit_args:
                if arg not in split_args:
                    split_args[arg] = []
                split_args[arg].append(aid)
            else:
                nonsplit_args.append((arg, aid))

        # verify that split is possible
        for a in tosplit_args:
            acount = len(split_args.get(a,[]))
            if acount < 2:
                raise AnnotationSplitError("Cannot split %s on %s: only %d %s arguments (need two or more)" % (ann.id, a, acount, a))

        # create all combinations of the args on which to split
        argument_combos = [[]]
        for a in tosplit_args:
            new_combos = []
            for aid in split_args[a]:
                for c in argument_combos:
                    new_combos.append(c + [(a, aid)])
            argument_combos = new_combos

        # create the new events (first combo will use the existing event)
        from copy import deepcopy
        new_events = []
        for i, arg_combo in enumerate(argument_combos):
            # tweak args
            if i == 0:
                ann.args = nonsplit_args[:] + arg_combo
            else:
                newann = deepcopy(ann)
                newann.id = ann_obj.get_new_id("E") # TODO: avoid hard-coding ID prefix
                newann.args = nonsplit_args[:] + arg_combo
                ann_obj.add_annotation(newann)
                new_events.append(newann)
                mods.addition(newann)

        # then, go through all the annotations referencing the original
        # event, and create appropriate copies
        for a in ann_obj:
            soft_deps, hard_deps = a.get_deps()
            refs = soft_deps | hard_deps
            if ann.id in refs:
                # Referenced; make duplicates appropriately

                if isinstance(a, EventAnnotation):
                    # go through args and make copies for referencing
                    new_args = []
                    for arg, aid in a.args:
                        if aid == ann.id:
                            for newe in new_events:
                                new_args.append((arg, newe.id))
                    a.args.extend(new_args)

                elif isinstance(a, AttributeAnnotation):
                    for newe in new_events:
                        newmod = deepcopy(a)
                        newmod.target = newe.id
                        newmod.id = ann_obj.get_new_id("A") # TODO: avoid hard-coding ID prefix
                        ann_obj.add_annotation(newmod)
                        mods.addition(newmod)

                elif isinstance(a, BinaryRelationAnnotation):
                    # TODO
                    raise AnnotationSplitError("Cannot adjust annotation referencing split: not implemented for relations! (WARNING: annotations may be in inconsistent state, please reload!) (Please complain to the developers to fix this!)")

                elif isinstance(a, OnelineCommentAnnotation):
                    for newe in new_events:
                        newcomm = deepcopy(a)
                        newcomm.target = newe.id
                        newcomm.id = ann_obj.get_new_id("#") # TODO: avoid hard-coding ID prefix
                        ann_obj.add_annotation(newcomm)
                        mods.addition(newcomm)
                elif isinstance(a, NormalizationAnnotation):
                    for newe in new_events:
                        newnorm = deepcopy(a)
                        newnorm.target = newe.id
                        newnorm.id = ann_obj.get_new_id("N") # TODO: avoid hard-coding ID prefix
                        ann_obj.add_annotation(newnorm)
                        mods.addition(newnorm)
                else:
                    raise AnnotationSplitError("Cannot adjust annotation referencing split: not implemented for %s! (Please complain to the lazy developers to fix this!)" % a.__class__)

        mods_json = mods.json_response()
        mods_json['annotations'] = _json_from_ann(ann_obj)
        return mods_json

def set_status(directory, document, status=None):
    real_dir = real_directory(directory) 

    with TextAnnotations(path_join(real_dir, document)) as ann:
        # Erase all old status annotations
        for status in ann.get_statuses():
            ann.del_annotation(status)
        
        if status is not None:
            # XXX: This could work, not sure if it can induce an id collision
            new_status_id = ann.get_new_id('#')
            ann.add_annotation(OnelineCommentAnnotation(
                new_status, new_status_id, 'STATUS', ''
                ))

    json_dic = {
            'status': new_status
            }
    return json_dic

def get_status(directory, document):
    with TextAnnotations(path_join(real_directory, document),
            read_only=True) as ann:

        # XXX: Assume the last one is correct if we have more
        #       than one (which is a violation of protocol anyway)
        statuses = [c for c in ann.get_statuses()]
        if statuses:
            status = statuses[-1].target
        else:
            status = None

    json_dic = {
            'status': status
            }
    return json_dic

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Authentication and authorization mechanisms.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
            Illes Solt          <solt tmit bme hu>
Version:    2011-04-21
'''

from hashlib import sha512
from os.path import dirname, join as path_join, isdir

try:
    from os.path import relpath
except ImportError:
    # relpath new to python 2.6; use our implementation if not found
    from common import relpath
from common import ProtocolError
from config import USER_PASSWORD, DATA_DIR
from message import Messager
from session import get_session, invalidate_session
from projectconfig import ProjectConfiguration


# To raise if the authority to carry out an operation is lacking
class NotAuthorisedError(ProtocolError):
    def __init__(self, attempted_action):
        self.attempted_action = attempted_action

    def __str__(self):
        return 'Login required to perform "%s"' % self.attempted_action

    def json(self, json_dic):
        json_dic['exception'] = 'notAuthorised'
        return json_dic


# File/data access denial
class AccessDeniedError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Access Denied'

    def json(self, json_dic):
        json_dic['exception'] = 'accessDenied'
        # TODO: Client should be responsible here
        Messager.error('Access Denied')
        return json_dic


class InvalidAuthError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Incorrect login and/or password'

    def json(self, json_dic):
        json_dic['exception'] = 'invalidAuth'
        return json_dic


def _is_authenticated(user, password):
    # TODO: Replace with a database back-end
    return (user in USER_PASSWORD and
            password == USER_PASSWORD[user])
            #password == _password_hash(USER_PASSWORD[user]))

def _password_hash(password):
    return sha512(password).hexdigest()

def login(user, password):
    if not _is_authenticated(user, password):
        raise InvalidAuthError

    get_session()['user'] = user
    Messager.info('Hello!')
    return {}

def logout():
    try:
        del get_session()['user']
    except KeyError:
        # Already deleted, let it slide
        pass
    # TODO: Really send this message?
    Messager.info('Bye!')
    return {}

def whoami():
    json_dic = {}
    try:
        json_dic['user'] = get_session().get('user')
    except KeyError:
        # TODO: Really send this message?
        Messager.error('Not logged in!', duration=3)
    return json_dic

def allowed_to_read(real_path):
    data_path = path_join('/', relpath(real_path, DATA_DIR))
    # add trailing slash to directories, required to comply to robots.txt
    if isdir(real_path):
        data_path = '%s/' % ( data_path )
        
    real_dir = dirname(real_path)
    robotparser = ProjectConfiguration(real_dir).get_access_control()
    if robotparser is None:
        return True # default allow

    try:
        user = get_session().get('user')
    except KeyError:
        user = None

    if user is None:
        user = 'guest'

    #display_message('Path: %s, dir: %s, user: %s, ' % (data_path, real_dir, user), type='error', duration=-1)

    return robotparser.can_fetch(user, data_path)

# TODO: Unittesting

########NEW FILE########
__FILENAME__ = backup
#!/usr/bin/env python

from __future__ import with_statement

'''
Back-up mechanisms for the data directory.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-02-22
'''

#XXX: We can potentially miss a change within the same second as the back-up,
#       we need to share a mutex with the rest of the system somehow
#XXX: Does not check the return values of the external calls
#XXX: File/directory permissions must be checked
#XXX: The check for the latest data ASSUMES that the data dir has not been
#       changed, if it has been changed it will not do a back-up although
#       there is no existing back-up

from os.path import getmtime, isfile, dirname, abspath, basename
from os.path import join as join_path
from shlex import split as split_shlex
from datetime import datetime, timedelta
from os import listdir, walk
from subprocess import Popen, PIPE

from filelock import file_lock, PID_WARN

from config import BACKUP_DIR, DATA_DIR

### Constants
#TODO: Move to a config
MIN_INTERVAL = timedelta(days=1)
CHECKSUM_FILENAME = 'CHECKSUM'
TAR_GZ_SUFFIX = 'tar.gz'
###

def _datetime_mtime(path):
    return datetime.fromtimestamp(getmtime(path))

def _safe_dirname(path):
    # This handles the case of a trailing slash for the dir path
    return basename(path) or dirname(dirname(path))

# NOTE: Finds the younges file in a directory structure, currently not in use
#       due to performance problems
'''
def _youngest_file(dir):
    youngest = dir
    y_mtime = _datetime_mtime(dir)
    for root, _, files in walk(dir):
        for file_path in (join_path(root, f) for f in files):
            f_mtime = _datetime_mtime(file_path)
            if f_mtime > y_mtime:
                youngest = file_path
                y_mtime = f_mtime
    return youngest, y_mtime
'''

def _youngest_backup(dir):
    backups = [(_datetime_mtime(f), f)
            for f in (join_path(dir, p) for p in listdir(dir))
            if isfile(f) and f.endswith('.' + TAR_GZ_SUFFIX)]
    if not backups:
        # We found no backups
        return None, None
    backups.sort()
    # Flip the order since the path should be first and mtime second
    return backups[0][::-1]

def backup(min_interval=MIN_INTERVAL, backup_dir=BACKUP_DIR, data_dir=DATA_DIR):
    if backup_dir is None:
        return

    #XXX: The timeout is arbitary but dependant on the back-up, should we start
    #       with a sane default and then refer to how long the last back-up
    #       took?  
    backup_lock = join_path(DATA_DIR, '.backup.lock')
    with file_lock(backup_lock, pid_policy=PID_WARN, timeout=60):
        _backup(min_interval, backup_dir, data_dir)

def _backup(min_interval=MIN_INTERVAL, backup_dir=BACKUP_DIR, data_dir=DATA_DIR):
    b_file, b_mtime = _youngest_backup(backup_dir)
    y_mtime = _datetime_mtime(DATA_DIR)
    #_, y_mtime = _youngest_file(data_dir)
    # If we have a back-up arch and no file has changed since the back-up or
    #       the delay has not expired, return
    if b_file is not None and (y_mtime <= b_mtime
            or (y_mtime - b_mtime) < min_interval):
        return

    # Here we do use UTC
    backup_filename = (_safe_dirname(data_dir) + '-'
            + datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            + '.' + TAR_GZ_SUFFIX)
    backup_path = abspath(join_path(backup_dir, backup_filename))
    data_dir_parent = join_path(data_dir, '../')

    #TODO: Check the exit signals!
    cmd = 'tar -c -z -f %s -C %s %s' % (backup_path,
        data_dir_parent, _safe_dirname(data_dir))
    tar_p = Popen(split_shlex(cmd))
    tar_p.wait()

    checksum_base = join_path(backup_dir, CHECKSUM_FILENAME)
    with open(checksum_base + '.' + 'MD5', 'a') as md5_file:
        # *NIX could have used m5sum instead
        md5_cmd = 'md5sum %s' % (backup_filename)
        md5_p = Popen(split_shlex(md5_cmd), stdout=md5_file, cwd=backup_dir)
        md5_p.wait()

    with open(checksum_base + '.' + 'SHA256', 'a') as sha256_file:
        sha256_cmd = 'shasum -a 256 %s' % (backup_filename)
        sha256_p = Popen(split_shlex(sha256_cmd), stdout=sha256_file, cwd=backup_dir)
        sha256_p.wait()

if __name__ == '__main__':
    from unittest import TestCase
    from tempfile import mkdtemp
    from shutil import rmtree
    from time import sleep
    
    def _backups(dir):
        return len([f for f in listdir(dir)
            if f.endswith('.' + TAR_GZ_SUFFIX)])

    #TODO: Use a wrapped back-up, as it is now it is easy to mess up the paths
    class BackupTest(TestCase):
        dummy_filename = 'dummy'

        def setUp(self):
            self.tmp_dir = mkdtemp()
            self.data_dir = mkdtemp()
            self.dummy_path = join_path(self.data_dir,
                    BackupTest.dummy_filename)
            with open(self.dummy_path, 'w') as _:
                pass

        def tearDown(self):
            rmtree(self.tmp_dir)
            rmtree(self.data_dir)

        def test_empty(self):
            backup(backup_dir=self.tmp_dir, data_dir=self.data_dir)
            self.assertTrue(_backups(self.tmp_dir),
                    'no back-up was created upon empty backup dir')

        def test_delay(self):
            backup(backup_dir=self.tmp_dir, data_dir=self.data_dir)
            backup(min_interval=timedelta(days=365),
                    backup_dir=self.tmp_dir, data_dir=self.data_dir)
            self.assertTrue(_backups(self.tmp_dir) == 1,
                    'additional backup created although delay had not expired')

        def test_no_change(self):
            backup(backup_dir=self.tmp_dir, data_dir=self.data_dir)
            sleep(3)
            backup(min_interval=timedelta(seconds=1),
                    backup_dir=self.tmp_dir, data_dir=self.data_dir)
            self.assertTrue(_backups(self.tmp_dir) == 1,
                    'additional back-up created although no file changed')

        def test_expired_delay(self):
            backup(backup_dir=self.tmp_dir, data_dir=self.data_dir)
            sleep(3)
            with open(self.dummy_path, 'w') as dummy_file:
                dummy_file.write('This is a change for a change')
            sleep(3)
            backup(min_interval=timedelta(seconds=1),
                    backup_dir=self.tmp_dir, data_dir=self.data_dir)
            self.assertTrue(_backups(self.tmp_dir) == 2,
                    'no additional back-up was created after delay expired')

    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = bratlex
#!/usr/bin/env python

'''
Tokenisation for the brat stand-off format.

Example, test tokenisation on a collection:

    find . -name '*.ann' | parallel cat | ./bratlex.py

Author:  Pontus Stenetorp    <pontus stenetorp se>
Version: 2011-07-11
'''

try:
    import ply.lex as lex
except ImportError:
    # We need to add ply to path
    from sys import path as sys_path
    from os.path import join as path_join
    from os.path import dirname

    sys_path.append(path_join(dirname(__file__), '../lib/ply-3.4'))

    import ply.lex as lex

tokens = (
        # Primitives
        'COLON',
        'NEWLINE',
        'SPACE',
        'TAB',
        'WILDCARD',

        # Identifiers
        'COMMENT_ID',
        'EVENT_ID',
        'MODIFIER_ID',
        'RELATION_ID',
        'TEXT_BOUND_ID',

        # Values
        'INTEGER',
        'TYPE',

        # Special-case for freetext
        'FREETEXT',
        )

states = (
        ('freetext', 'exclusive'),
        )

t_COLON     = r':'
t_SPACE     = r'\ '
t_WILDCARD  = r'\*'

def t_COMMENT_ID(t):
    r'\#[0-9]+'
    return t

def t_EVENT_ID(t):
    r'E[0-9]+'
    return t

def t_MODIFIER_ID(t):
    r'M[0-9]+'
    return t

def t_RELATION_ID(t):
    r'R[0-9]+'
    return t

def t_TEXT_BOUND_ID(t):
    r'T[0-9]+'
    return t

def t_NEWLINE(t):
    r'\n'
    # Increment the lexers line-count
    t.lexer.lineno += 1
    # Reset the count of tabs on this line
    t.lexer.line_tab_count = 0
    return t

def t_TAB(t):
    r'\t'
    # Increment the number of tabs we have soon on this line
    t.lexer.line_tab_count += 1
    if t.lexer.line_tab_count == 2:
        t.lexer.begin('freetext')
    return t


def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value) 
    return t

def t_TYPE(t):
    r'[A-Z][A-Za-z_-]*'
    return t

def t_freetext_FREETEXT(t):
    r'[^\n\t]+'
    return t

def t_freetext_TAB(t):
    r'\t'
    # End freetext mode INITAL
    t.lexer.begin('INITIAL')
    return t

def t_freetext_NEWLINE(t):
    r'\n'
    # Increment the lexers line-count
    t.lexer.lineno += 1
    # Reset the count of tabs on this line
    t.lexer.line_tab_count = 0
    # End freetext mode INITAL
    t.lexer.begin('INITIAL')
    return t

# Error handling rule
def t_error(t):
    print "Illegal character '%s'" % t.value[0]
    raise Exception
    t.lexer.skip(1)

def t_freetext_error(t):
    return t_error(t)

lexer = lex.lex()
lexer.line_tab_count = 0

if __name__ == '__main__':
    from sys import stdin
    for line in stdin:
        lexer.input(line)

        for tok in lexer:
            pass
            print tok

########NEW FILE########
__FILENAME__ = bratyacc
#!/usr/bin/env python

'''
Grammar for the brat stand-off format.

Example, test grammar on a collection:

    find . -name '*.ann' | parallel cat | ./bratyacc.py

Author:   Pontus Stenetorp    <pontus stenetorp se>
Version:  2011-07-11
'''

try:
    import ply.yacc as yacc
except ImportError:
    # We need to add ply to path
    from sys import path as sys_path
    from os.path import join as path_join
    from os.path import dirname

    sys_path.append(path_join(dirname(__file__), '../lib/ply-3.4'))

    import ply.yacc as yacc

from bratlex import tokens

# TODO: Recurse all the way to a file
# TODO: Comment annotation

def p_annotation_line(p):
    '''
    annotation_line : annotation NEWLINE
    '''
    p[0] = '%s\n' % (p[1], )
    return p

# TODO: Ugly newline
def p_annotation(p):
    '''
    annotation  : textbound
                | event
                | modifier
                | equiv
                | relation
                | comment
    '''
    p[0] = p[1]
    return p

# TODO: What do we really call these?
def p_equiv(p):
    '''
    equiv : equiv_core SPACE equiv_members
    '''
    p[0] = '%s %s' % (p[1], p[3], )
    return p

def p_equiv_core(p):
    '''
    equiv_core : WILDCARD TAB TYPE
    '''
    p[0] = '*\t%s' % (p[3], )
    return p

def p_equiv_members(p):
    '''
    equiv_members   : equiv_member SPACE equiv_members
                    | equiv_member
    '''
    p[0] = '%s' % (p[1], )
    try:
        p[0] += ' %s' % (p[3], )
    except IndexError:
        # We did not have any more members
        pass
    return p

def p_equiv_member(p):
    '''
    equiv_member : id
    '''
    p[0] = '%s' % (p[1], )
    return p

def p_textbound(p):
    '''
    textbound   :  textbound_freetext
                |  textbound_core
    '''
    p[0] = p[1]
    return p

def p_textbound_core(p):
    '''
    textbound_core : TEXT_BOUND_ID TAB TYPE SPACE INTEGER SPACE INTEGER
    '''
    p[0] = '%s\t%s %d %d' % (p[1], p[3], p[5], p[7], )
    return p

def p_textbound_freetext(p):
    '''
    textbound_freetext : textbound_core TAB FREETEXT
    '''
    p[0] = '%s\t%s' % (p[1], p[3], )
    return p

def p_comment(p):
    '''
    comment : COMMENT_ID TAB TYPE SPACE id
    '''
    p[0] = '%s\t%s %s' % (p[1], p[3], p[5])
    return p

def p_event(p):
    '''
    event   : event_core SPACE event_arguments
            | event_core SPACE
            | event_core
    '''
    p[0] = p[1]
    try:
        p[0] += p[2]
    except IndexError:
        pass
    try:
        p[0] += p[3]
    except IndexError:
        pass
    return p

def p_event_core(p):
    '''
    event_core : EVENT_ID TAB TYPE COLON id
    '''
    p[0] = '%s\t%s:%s' % (p[1], p[3], p[5], )
    return p

def p_event_arguments(p):
    '''
    event_arguments : event_argument SPACE event_arguments
                    | event_argument
    '''
    p[0] = '%s' % (p[1], )
    try:
        p[0] += ' ' + p[3]
    except IndexError:
        pass
    return p

def p_event_argument(p):
    '''
    event_argument : argument COLON id
    '''
    p[0] = '%s:%s' % (p[1], p[3], )
    return p

def p_modifier(p):
    '''
    modifier : MODIFIER_ID TAB TYPE SPACE id
    '''
    p[0] = '%s\t%s %s' % (p[1], p[3], p[5], )
    return p

def p_relation(p):
    '''
    relation : RELATION_ID TAB TYPE SPACE argument COLON id SPACE argument COLON id
    '''
    # TODO: Should probably require only one of each argument type
    p[0] = '%s\t%s %s:%s %s:%s' % (p[1], p[3], p[5], p[7], p[9], p[11], )
    return p

def p_argument(p):
    '''
    argument    : TYPE
                | TYPE INTEGER
    '''
    p[0] = p[1]
    try:
        p[0] += str(p[2])
    except IndexError:
        pass
    return p

# Generic id
def p_id(p):
    '''
    id  : TEXT_BOUND_ID
        | EVENT_ID
        | RELATION_ID
        | MODIFIER_ID
        | COMMENT_ID
    '''
    p[0] = p[1]
    return p

def p_error(p):
    print 'Syntax error in input! "%s"'  % (str(p), )
    raise Exception

parser = yacc.yacc()

if __name__ == '__main__':
    from sys import stdin
    for line in stdin:
        print 'Input: "%s"' % line.rstrip('\n')
        result = parser.parse(line)
        assert result == line, ('"%s" != "%s"' % (result, line)
                ).replace('\n', '\\n')
        print result,

########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Functionality shared between server components.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-04-21
'''


class ProtocolError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        # TODO: just adding __str__ to ProtocolError, not all
        # currently support it, so falling back on this assumption
        # about how to make a (nearly) human-readable string. Once
        # __str__ added to all ProtocolErrors, raise
        # NotImplementedError instead.
        return 'ProtocolError: %s (TODO: __str__() method)' % self.__class__

    def json(self, json_dic):
        raise NotImplementedError, 'abstract method'

class ProtocolArgumentError(ProtocolError):
    def json(self, json_dic):
        json_dic['exception'] = 'protocolArgumentError'

# If received by ajax.cgi, no JSON will be sent
# XXX: This is an ugly hack to circumvent protocol flaws
class NoPrintJSONError(Exception):
    def __init__(self, hdrs, data):
        self.hdrs = hdrs
        self.data = data

class NotImplementedError(ProtocolError):
    def json(self, json_dic):
        json_dic['exception'] = 'notImplemented'

class CollectionNotAccessibleError(ProtocolError):
    def json(self, json_dic):
        json_dic['exception'] = 'collectionNotAccessible'

    def __str__(self):
        return 'Error: collection not accessible'

# TODO: We have issues using this in relation to our inspection
#       in dispatch, can we make it work?
# Wrapper to send a deprecation warning to the client if debug is set
def deprecated_action(func):
    try:
        from config import DEBUG
    except ImportError:
        DEBUG = False
    from functools import wraps
    from message import Messager

    @wraps(func)
    def wrapper(*args, **kwds):
        if DEBUG:
            Messager.warning(('Client sent "%s" action '
                              'which is marked as deprecated') % func.__name__,)
        return func(*args, **kwds)
    return wrapper

# relpath is not included in python 2.5; alternative implementation from
# BareNecessities package, License: MIT, Author: James Gardner
# TODO: remove need for relpath instead
def relpath(path, start):
    """Return a relative version of a path"""
    from os.path import abspath, sep, pardir, commonprefix
    from os.path import join as path_join
    if not path:
        raise ValueError("no path specified")
    start_list = abspath(start).split(sep)
    path_list = abspath(path).split(sep)
    # Work out how much of the filepath is shared by start and path.
    i = len(commonprefix([start_list, path_list]))
    rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return path
    return path_join(*rel_list)

########NEW FILE########
__FILENAME__ = convert
'''
Conversion services, we may want to move these out later on.

Author:     Pontus Stenetorp    <pontus stenetorp>
Version:    2012-06-26
'''

from __future__ import with_statement

from os.path import join as path_join
from shutil import rmtree
from tempfile import mkdtemp

from annotation import open_textfile, Annotations
from common import ProtocolError
from document import _document_json_dict
from stanford import (
        basic_dep as stanford_basic_dep,
        collapsed_ccproc_dep as stanford_collapsed_ccproc_dep,
        collapsed_dep as stanford_collapsed_dep,
        coref as stanford_coref,
        ner as stanford_ner,
        pos as stanford_pos,
        text as stanford_text,
        token_offsets as stanford_token_offsets,
        sentence_offsets as stanford_sentence_offsets
        )

### Constants
CONV_BY_SRC = {
        'stanford-pos': (stanford_text, stanford_pos, ),
        'stanford-ner': (stanford_text, stanford_ner, ),
        'stanford-coref': (stanford_text, stanford_coref, ),
        'stanford-basic_dep': (stanford_text, stanford_basic_dep, ),
        'stanford-collapsed_dep': (stanford_text, stanford_collapsed_dep, ),
        'stanford-collapsed_ccproc_dep': (stanford_text, stanford_collapsed_ccproc_dep, ),
        }
###


class InvalidSrcFormat(ProtocolError):
    def json(self, json_dic):
        json_dic['exception'] = 'InvalidSrcFormat'
        return json_dic


def convert(data, src):
    # Fail early if we don't have a converter
    try:
        conv_text, conv_ann = CONV_BY_SRC[src]
    except KeyError:
        raise InvalidSrcFormat

    # Note: Due to a lack of refactoring we need to write to disk to read
    #   annotions, once this is fixed, the below code needs some clean-up
    tmp_dir = None
    try:
        tmp_dir = mkdtemp()
        doc_base = path_join(tmp_dir, 'tmp')
        with open_textfile(doc_base + '.txt', 'w') as txt_file:
            txt_file.write(conv_text(data))
        with open(doc_base + '.ann', 'w'):
            pass

        with Annotations(doc_base) as ann_obj:
            for ann in conv_ann(data):
                ann_obj.add_annotation(ann)

        json_dic = _document_json_dict(doc_base)
        # Note: Blank the comments, they rarely do anything good but whine
        #   about configuration when we use the tool solely for visualisation
        #   purposes
        json_dic['comments'] = []

        # Note: This is an ugly hack... we want to ride along with the
        #   Stanford tokenisation and sentence splits when returning their
        #   output rather than relying on the ones generated by brat.
        if src.startswith('stanford-'):
            json_dic['token_offsets'] = stanford_token_offsets(data)
            json_dic['sentence_offsets'] = stanford_sentence_offsets(data)

        return json_dic
    finally:
        if tmp_dir is not None:
            rmtree(tmp_dir)

########NEW FILE########
__FILENAME__ = ptbesc
#!/usr/bin/env python

'''
Penn TreeBank escaping.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-09-12
'''

### Constants
# From: To
PTB_ESCAPES = {
        u'(': u'-LRB-',
        u')': u'-RRB-',
        u'[': u'-LSB-',
        u']': u'-RSB-',
        u'{': u'-LCB-',
        u'}': u'-RCB-',
        u'/': u'\/',
        u'*': u'\*',
    }
###

def escape(s):
    r = s
    for _from, to in PTB_ESCAPES.iteritems():
        r = r.replace(_from, to)
    return r

def unescape(s):
    r = s
    for _from, to in PTB_ESCAPES.iteritems():
        r = r.replace(to, _from)
    return r

def main(args):
    from argparse import ArgumentParser
    from sys import stdin, stdout

    # TODO: Doc!
    argparser = ArgumentParser()
    argparser.add_argument('-u', '--unescape', action='store_true')
    argp = argparser.parse_args(args[1:])

    for line in (l.rstrip('\n') for l in stdin):
        if argp.unescape:
            r = unescape(line)
        else:
            r = escape(line)
        stdout.write(r)
        stdout.write('\n')

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))


########NEW FILE########
__FILENAME__ = stanford
#!/usr/bin/env python

'''
Conversion scripts related to Stanford tools.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-06-26
'''

# TODO: Currently pretty much every single call re-parses the XML, optimise?
# TODO: We could potentially put the lemma into a comment

from __future__ import with_statement

from collections import defaultdict
from itertools import chain
from sys import argv, path as sys_path, stderr, stdout
from os.path import dirname, join as path_join
from xml.etree import ElementTree

from ptbesc import unescape as ptb_unescape

try:
    from collections import namedtuple
except ImportError:
    sys_path.append(path_join(dirname(__file__), '..', '..', 'lib'))
    from altnamedtuple import namedtuple

try:
    from annotation import (BinaryRelationAnnotation, EquivAnnotation,
            TextBoundAnnotation)
except ImportError:
    sys_path.append(path_join(dirname(__file__), '..'))
    from annotation import (BinaryRelationAnnotation, EquivAnnotation,
            TextBoundAnnotation)

Token = namedtuple('Token', ('word', 'lemma', 'start', 'end', 'pos', 'ner', ))

def _escape_pos_tags(pos):
    pos_res = pos
    for _from, to in (
            ("'", '__SINGLEQUOTE__', ),
            ('"', '__DOUBLEQUOTE__', ),
            ('$', '__DOLLAR__', ),
            (',', '__COMMA__', ),
            ('.', '__DOT__', ),
            (':', '__COLON__', ),
            ('`', '__BACKTICK__', ),
            ):
        pos_res = pos_res.replace(_from, to)
    return pos_res

def _token_by_ids(soup):
    token_by_ids = defaultdict(dict)

    for sent_e in _find_sentences_element(soup).getiterator('sentence'):
        sent_id = int(sent_e.get('id'))
        for tok_e in sent_e.getiterator('token'):
            tok_id = int(tok_e.get('id'))
            tok_word = unicode(tok_e.find('word').text)
            tok_lemma = unicode(tok_e.find('lemma').text)
            tok_start = int(tok_e.find('CharacterOffsetBegin').text)
            tok_end = int(tok_e.find('CharacterOffsetEnd').text)
            tok_pos = unicode(tok_e.find('POS').text)
            tok_ner = unicode(tok_e.find('NER').text)

            token_by_ids[sent_id][tok_id] = Token(
                    word=tok_word,
                    lemma=tok_lemma,
                    start=tok_start,
                    end=tok_end,
                    # Escape the PoS since brat dislike $ and .
                    pos=_escape_pos_tags(tok_pos),
                    ner=tok_ner
                    )

    return token_by_ids

def _tok_it(token_by_ids):
    for s_id in sorted(k for k in token_by_ids):
        for t_id in sorted(k for k in token_by_ids[s_id]):
            yield s_id, t_id, token_by_ids[s_id][t_id]

def _soup(xml):
    return ElementTree.fromstring(xml.encode('utf-8'))

def token_offsets(xml):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)
    return [(tok.start, tok.end) for _, _, tok in _tok_it(token_by_ids)]

def sentence_offsets(xml):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)
    sent_min_max = defaultdict(lambda : (2**32, -1, ))
    for s_id, _, tok in _tok_it(token_by_ids):
        s_entry = sent_min_max[s_id]
        sent_min_max[s_id] = (min(tok.start, s_entry[0]), max(tok.end, s_entry[1]), )
    return sorted((s_start, s_end) for s_start, s_end in sent_min_max.itervalues())

def text(xml):
    # It would be nice to have access to the original text, but this actually
    # isn't a part of the XML. Constructing it isn't that easy either, you
    # would have to assume that each "missing" character is a space, but you
    # don't really have any guarantee that this is the case...
    
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)

    # Get the presumed length of the text
    max_offset = -1
    for _, _, tok in _tok_it(token_by_ids):
        max_offset = max(max_offset, tok.end)
    
    # Then re-construct what we believe the text to be
    text = list(' ' * max_offset)
    for _, _, tok in _tok_it(token_by_ids):
        # Also unescape any PTB escapes in the text while we are at it
        # Note: Since Stanford actually doesn't do all the escapings properly
        # this will sometimes fail! Hint: Try "*/\*".
        unesc_word = ptb_unescape(tok.word)
        text[tok.start:len(unesc_word)] = unesc_word

    return u''.join(text)

def _pos(xml, start_id=1):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)

    curr_id = start_id
    for s_id, t_id, tok in _tok_it(token_by_ids):
        yield s_id, t_id, TextBoundAnnotation(((tok.start, tok.end, ), ),
                'T%s' % curr_id, tok.pos, '')
        curr_id += 1

def pos(xml, start_id=1):
    return (a for _, _, a in _pos(xml, start_id=start_id))

def ner(xml, start_id=1):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)

    # Stanford only has Inside and Outside tags, so conversion is easy
    nes = []
    last_ne_tok = None
    prev_tok = None
    for _, _, tok in _tok_it(token_by_ids):
        if tok.ner != 'O':
            if last_ne_tok is None:
                # Start of an NE from nothing
                last_ne_tok = tok
            elif tok.ner != last_ne_tok.ner:
                # Change in NE type
                nes.append((last_ne_tok.start, prev_tok.end, last_ne_tok.ner, ))
                last_ne_tok = tok
            else:
                # Continuation of the last NE, move along
                pass
        elif last_ne_tok is not None:
            # NE ended
            nes.append((last_ne_tok.start, prev_tok.end, last_ne_tok.ner, ))
            last_ne_tok = None
        prev_tok = tok
    else:
        # Do we need to terminate the last named entity?
        if last_ne_tok is not None:
            nes.append((last_ne_tok.start, prev_tok.end, last_ne_tok.ner, ))

    curr_id = start_id
    for start, end, _type in nes:
        yield TextBoundAnnotation(((start, end), ), 'T%s' % curr_id, _type, '')
        curr_id += 1
       
def coref(xml, start_id=1):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)
    
    docs_e = soup.findall('document')
    assert len(docs_e) == 1
    docs_e = docs_e[0]
    # Despite the name, this element contains conferences (note the "s")
    corefs_e = docs_e.findall('coreference')
    if not corefs_e:
        # No coreferences to process
        raise StopIteration
    assert len(corefs_e) == 1
    corefs_e = corefs_e[0]

    curr_id = start_id
    for coref_e in corefs_e:
        if corefs_e.tag != 'coreference':
            # To be on the safe side
            continue

        # This tag is now a full corference chain
        chain = []
        for mention_e in coref_e.getiterator('mention'):
            # Note: There is a "representative" attribute signalling the most
            #   "suitable" mention, we are currently not using this
            # Note: We don't use the head information for each mention
            sentence_id = int(mention_e.find('sentence').text)
            start_tok_id = int(mention_e.find('start').text)
            end_tok_id = int(mention_e.find('end').text) - 1

            mention_id = 'T%s' % (curr_id, )
            chain.append(mention_id)
            curr_id += 1
            yield TextBoundAnnotation(
                    ((token_by_ids[sentence_id][start_tok_id].start,
                    token_by_ids[sentence_id][end_tok_id].end), ),
                    mention_id, 'Mention', '')

        yield EquivAnnotation('Coreference', chain, '')

def _find_sentences_element(soup):
    # Find the right portion of the XML and do some limited sanity checking
    docs_e = soup.findall('document')
    assert len(docs_e) == 1
    docs_e = docs_e[0]
    sents_e = docs_e.findall('sentences')
    assert len(sents_e) == 1
    sents_e = sents_e[0]

    return sents_e

def _dep(xml, source_element='basic-dependencies'):
    soup = _soup(xml)
    token_by_ids = _token_by_ids(soup)

    ann_by_ids = defaultdict(dict)
    for s_id, t_id, ann in _pos(xml):
        ann_by_ids[s_id][t_id] = ann
        yield ann

    curr_rel_id = 1
    for sent_e in _find_sentences_element(soup).getiterator('sentence'):
        sent_id = int(sent_e.get('id'))

        # Attempt to find dependencies as distinctly named elements as they
        #   were stored in the Stanford XML format prior to 2013.
        deps_e = sent_e.findall(source_element)
        if len(deps_e) == 0:
            # Perhaps we are processing output following the newer standard,
            #   check for the same identifier but as a type attribute for
            #   general "dependencies" elements.
            deps_e = list(e for e in sent_e.getiterator('dependencies')
                    if e.attrib['type'] == source_element)
        assert len(deps_e) == 1
        deps_e = deps_e[0]
        
        for dep_e in deps_e:
            if dep_e.tag != 'dep':
                # To be on the safe side
                continue

            dep_type = dep_e.get('type')
            assert dep_type is not None

            if dep_type == 'root':
                # Skip dependencies to the root node, this behaviour conforms
                #   with how we treated the pre-2013 format.
                continue
            
            gov_tok_id = int(dep_e.find('governor').get('idx'))
            dep_tok_id = int(dep_e.find('dependent').get('idx'))

            yield BinaryRelationAnnotation(
                    'R%s' % curr_rel_id, dep_type,
                    'Governor', ann_by_ids[sent_id][gov_tok_id].id,
                    'Dependent', ann_by_ids[sent_id][dep_tok_id].id,
                    ''
                    )
            curr_rel_id += 1

def basic_dep(xml):
    return _dep(xml)
    
def collapsed_dep(xml):
    return _dep(xml, source_element='collapsed-dependencies')

def collapsed_ccproc_dep(xml):
    return _dep(xml, source_element='collapsed-ccprocessed-dependencies')

if __name__ == '__main__':
    STANFORD_XML = '''<?xml version="1.0" encoding="UTF-8"?>
    <?xml-stylesheet href="CoreNLP-to-HTML.xsl" type="text/xsl"?>
    <root>
      <document>
        <sentences>
          <sentence id="1">
            <tokens>
              <token id="1">
                <word>Stanford</word>
                <lemma>Stanford</lemma>
                <CharacterOffsetBegin>0</CharacterOffsetBegin>
                <CharacterOffsetEnd>8</CharacterOffsetEnd>
                <POS>NNP</POS>
                <NER>ORGANIZATION</NER>
              </token>
              <token id="2">
                <word>University</word>
                <lemma>University</lemma>
                <CharacterOffsetBegin>9</CharacterOffsetBegin>
                <CharacterOffsetEnd>19</CharacterOffsetEnd>
                <POS>NNP</POS>
                <NER>ORGANIZATION</NER>
              </token>
              <token id="3">
                <word>is</word>
                <lemma>be</lemma>
                <CharacterOffsetBegin>20</CharacterOffsetBegin>
                <CharacterOffsetEnd>22</CharacterOffsetEnd>
                <POS>VBZ</POS>
                <NER>O</NER>
              </token>
              <token id="4">
                <word>located</word>
                <lemma>located</lemma>
                <CharacterOffsetBegin>23</CharacterOffsetBegin>
                <CharacterOffsetEnd>30</CharacterOffsetEnd>
                <POS>JJ</POS>
                <NER>O</NER>
              </token>
              <token id="5">
                <word>in</word>
                <lemma>in</lemma>
                <CharacterOffsetBegin>31</CharacterOffsetBegin>
                <CharacterOffsetEnd>33</CharacterOffsetEnd>
                <POS>IN</POS>
                <NER>O</NER>
              </token>
              <token id="6">
                <word>California</word>
                <lemma>California</lemma>
                <CharacterOffsetBegin>34</CharacterOffsetBegin>
                <CharacterOffsetEnd>44</CharacterOffsetEnd>
                <POS>NNP</POS>
                <NER>LOCATION</NER>
              </token>
              <token id="7">
                <word>.</word>
                <lemma>.</lemma>
                <CharacterOffsetBegin>44</CharacterOffsetBegin>
                <CharacterOffsetEnd>45</CharacterOffsetEnd>
                <POS>.</POS>
                <NER>O</NER>
              </token>
            </tokens>
            <parse>(ROOT (S (NP (NNP Stanford) (NNP University)) (VP (VBZ is) (ADJP (JJ located) (PP (IN in) (NP (NNP California))))) (. .))) </parse>
            <basic-dependencies>
              <dep type="nn">
                <governor idx="2">University</governor>
                <dependent idx="1">Stanford</dependent>
              </dep>
              <dep type="nsubj">
                <governor idx="4">located</governor>
                <dependent idx="2">University</dependent>
              </dep>
              <dep type="cop">
                <governor idx="4">located</governor>
                <dependent idx="3">is</dependent>
              </dep>
              <dep type="prep">
                <governor idx="4">located</governor>
                <dependent idx="5">in</dependent>
              </dep>
              <dep type="pobj">
                <governor idx="5">in</governor>
                <dependent idx="6">California</dependent>
              </dep>
            </basic-dependencies>
            <collapsed-dependencies>
              <dep type="nn">
                <governor idx="2">University</governor>
                <dependent idx="1">Stanford</dependent>
              </dep>
              <dep type="nsubj">
                <governor idx="4">located</governor>
                <dependent idx="2">University</dependent>
              </dep>
              <dep type="cop">
                <governor idx="4">located</governor>
                <dependent idx="3">is</dependent>
              </dep>
              <dep type="prep_in">
                <governor idx="4">located</governor>
                <dependent idx="6">California</dependent>
              </dep>
            </collapsed-dependencies>
            <collapsed-ccprocessed-dependencies>
              <dep type="nn">
                <governor idx="2">University</governor>
                <dependent idx="1">Stanford</dependent>
              </dep>
              <dep type="nsubj">
                <governor idx="4">located</governor>
                <dependent idx="2">University</dependent>
              </dep>
              <dep type="cop">
                <governor idx="4">located</governor>
                <dependent idx="3">is</dependent>
              </dep>
              <dep type="prep_in">
                <governor idx="4">located</governor>
                <dependent idx="6">California</dependent>
              </dep>
            </collapsed-ccprocessed-dependencies>
          </sentence>
          <sentence id="2">
            <tokens>
              <token id="1">
                <word>It</word>
                <lemma>it</lemma>
                <CharacterOffsetBegin>46</CharacterOffsetBegin>
                <CharacterOffsetEnd>48</CharacterOffsetEnd>
                <POS>PRP</POS>
                <NER>O</NER>
              </token>
              <token id="2">
                <word>is</word>
                <lemma>be</lemma>
                <CharacterOffsetBegin>49</CharacterOffsetBegin>
                <CharacterOffsetEnd>51</CharacterOffsetEnd>
                <POS>VBZ</POS>
                <NER>O</NER>
              </token>
              <token id="3">
                <word>a</word>
                <lemma>a</lemma>
                <CharacterOffsetBegin>52</CharacterOffsetBegin>
                <CharacterOffsetEnd>53</CharacterOffsetEnd>
                <POS>DT</POS>
                <NER>O</NER>
              </token>
              <token id="4">
                <word>great</word>
                <lemma>great</lemma>
                <CharacterOffsetBegin>54</CharacterOffsetBegin>
                <CharacterOffsetEnd>59</CharacterOffsetEnd>
                <POS>JJ</POS>
                <NER>O</NER>
              </token>
              <token id="5">
                <word>university</word>
                <lemma>university</lemma>
                <CharacterOffsetBegin>60</CharacterOffsetBegin>
                <CharacterOffsetEnd>70</CharacterOffsetEnd>
                <POS>NN</POS>
                <NER>O</NER>
              </token>
              <token id="6">
                <word>.</word>
                <lemma>.</lemma>
                <CharacterOffsetBegin>70</CharacterOffsetBegin>
                <CharacterOffsetEnd>71</CharacterOffsetEnd>
                <POS>.</POS>
                <NER>O</NER>
              </token>
            </tokens>
            <parse>(ROOT (S (NP (PRP It)) (VP (VBZ is) (NP (DT a) (JJ great) (NN university))) (. .))) </parse>
            <basic-dependencies>
              <dep type="nsubj">
                <governor idx="5">university</governor>
                <dependent idx="1">It</dependent>
              </dep>
              <dep type="cop">
                <governor idx="5">university</governor>
                <dependent idx="2">is</dependent>
              </dep>
              <dep type="det">
                <governor idx="5">university</governor>
                <dependent idx="3">a</dependent>
              </dep>
              <dep type="amod">
                <governor idx="5">university</governor>
                <dependent idx="4">great</dependent>
              </dep>
            </basic-dependencies>
            <collapsed-dependencies>
              <dep type="nsubj">
                <governor idx="5">university</governor>
                <dependent idx="1">It</dependent>
              </dep>
              <dep type="cop">
                <governor idx="5">university</governor>
                <dependent idx="2">is</dependent>
              </dep>
              <dep type="det">
                <governor idx="5">university</governor>
                <dependent idx="3">a</dependent>
              </dep>
              <dep type="amod">
                <governor idx="5">university</governor>
                <dependent idx="4">great</dependent>
              </dep>
            </collapsed-dependencies>
            <collapsed-ccprocessed-dependencies>
              <dep type="nsubj">
                <governor idx="5">university</governor>
                <dependent idx="1">It</dependent>
              </dep>
              <dep type="cop">
                <governor idx="5">university</governor>
                <dependent idx="2">is</dependent>
              </dep>
              <dep type="det">
                <governor idx="5">university</governor>
                <dependent idx="3">a</dependent>
              </dep>
              <dep type="amod">
                <governor idx="5">university</governor>
                <dependent idx="4">great</dependent>
              </dep>
            </collapsed-ccprocessed-dependencies>
          </sentence>
        </sentences>
        <coreference>
          <coreference>
            <mention representative="true">
              <sentence>1</sentence>
              <start>1</start>
              <end>3</end>
              <head>2</head>
            </mention>
            <mention>
              <sentence>2</sentence>
              <start>1</start>
              <end>2</end>
              <head>1</head>
            </mention>
            <mention>
              <sentence>2</sentence>
              <start>3</start>
              <end>6</end>
              <head>5</head>
            </mention>
          </coreference>
        </coreference>
      </document>
    </root>
    '''

    def _test_xml(xml_string):
        stdout.write('Text:\n')
        stdout.write(text(xml_string).encode('utf-8'))
        stdout.write('\n')

        stdout.write('\n')
        stdout.write('Part-of-speech:\n')
        for ann in pos(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Named Entity Recoginiton:\n')
        for ann in ner(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Co-reference:\n')
        for ann in coref(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Basic dependencies:\n')
        for ann in basic_dep(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Basic dependencies:\n')
        for ann in basic_dep(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Collapsed dependencies:\n')
        for ann in collapsed_dep(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Collapsed CC-processed dependencies:\n')
        for ann in collapsed_ccproc_dep(xml_string):
            stdout.write(unicode(ann))
            stdout.write('\n')

        stdout.write('\n')
        stdout.write('Token boundaries:\n')
        stdout.write(unicode(token_offsets(xml_string)))
        stdout.write('\n')

        stdout.write('\n')
        stdout.write('Sentence boundaries:\n')
        stdout.write(unicode(sentence_offsets(xml_string)))
        stdout.write('\n')

    if len(argv) < 2:
        xml_strings = (('<string>', STANFORD_XML), )
    else:
        def _xml_gen():
            for xml_path in argv[1:]:
                with open(xml_path, 'r') as xml_file:
                    # We assume UTF-8 here, otherwise ElemenTree will bork
                    yield (xml_path, xml_file.read().decode('utf-8'))
        xml_strings = _xml_gen()

    for xml_source, xml_string in xml_strings:
        try:
            print >> stderr, xml_source
            _test_xml(xml_string)
        except:
            print >> stderr, 'Crashed on:', xml_source
            raise

########NEW FILE########
__FILENAME__ = delete
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Deletion functionality.
'''

from __future__ import with_statement

from os.path import join as path_join
from message import Messager

def delete_document(collection, document):
    Messager.error("Document deletion not supported in this version.")
    return {}

def delete_collection(collection):
    Messager.error("Collection deletion not supported in this version.")
    return {}
     

########NEW FILE########
__FILENAME__ = dispatch
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Server request dispatching mechanism.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-04-21
'''

from os.path import abspath, normpath
from os.path import join as path_join

from annotator import create_arc, delete_arc, reverse_arc
from annotator import create_span, delete_span
from annotator import split_span
from auth import login, logout, whoami, NotAuthorisedError
from common import ProtocolError
from config import DATA_DIR
from convert.convert import convert
from docimport import save_import
from document import (get_directory_information, get_document,
        get_document_timestamp, get_configuration)
from download import download_file, download_collection
from inspect import getargspec
from itertools import izip
from jsonwrap import dumps
from logging import info as log_info
from annlog import log_annotation
from message import Messager
from svg import store_svg, retrieve_stored
from session import get_session, load_conf, save_conf
from search import search_text, search_entity, search_event, search_relation, search_note
from predict import suggest_span_types
from undo import undo
from tag import tag
from delete import delete_document, delete_collection
from norm import norm_get_name, norm_search, norm_get_data

# no-op function that can be invoked by client to log a user action
def logging_no_op(collection, document, log):
    # need to return a dictionary
    return {}

### Constants
# Function call-backs
DISPATCHER = {
        'getCollectionInformation': get_directory_information,
        'getDocument': get_document,
        'getDocumentTimestamp': get_document_timestamp,
        'importDocument': save_import,

        'storeSVG': store_svg,
        'retrieveStored': retrieve_stored,
        'downloadFile': download_file,
        'downloadCollection': download_collection,

        'login': login,
        'logout': logout,
        'whoami': whoami,

        'createSpan': create_span,
        'deleteSpan': delete_span,
        'splitSpan' : split_span,

        'createArc': create_arc,
        'reverseArc': reverse_arc,
        'deleteArc': delete_arc,

        # NOTE: search actions are redundant to allow different
        # permissions for single-document and whole-collection search.
        'searchTextInDocument'     : search_text,
        'searchEntityInDocument'   : search_entity,
        'searchEventInDocument'    : search_event,
        'searchRelationInDocument' : search_relation,
        'searchNoteInDocument'     : search_note,
        'searchTextInCollection'     : search_text,
        'searchEntityInCollection'   : search_entity,
        'searchEventInCollection'    : search_event,
        'searchRelationInCollection' : search_relation,
        'searchNoteInCollection'     : search_note,

        'suggestSpanTypes': suggest_span_types,

        'logAnnotatorAction': logging_no_op,

        'saveConf': save_conf,
        'loadConf': load_conf,

        'undo': undo,
        'tag': tag,

        'deleteDocument': delete_document,
        'deleteCollection': delete_collection,

        # normalization support
        'normGetName': norm_get_name,
        'normSearch': norm_search,
        'normData' : norm_get_data,

        # Visualisation support
        'getConfiguration': get_configuration,
        'convert': convert,
       }

# Actions that correspond to annotation functionality
ANNOTATION_ACTION = set((
        'createArc',
        'deleteArc',
        'createSpan',
        'deleteSpan',
        'splitSpan',
        'suggestSpanTypes',
        'undo',
        ))

# Actions that will be logged as annotator actions (if so configured)
LOGGED_ANNOTATOR_ACTION = ANNOTATION_ACTION | set((
        'getDocument',
        'logAnnotatorAction',
        ))

# Actions that require authentication
REQUIRES_AUTHENTICATION = ANNOTATION_ACTION | set((
        # Document functionality
        'importDocument',
        
        # Search functionality in whole collection (heavy on the CPU/disk ATM)
        'searchTextInCollection',
        'searchEntityInCollection',
        'searchEventInCollection',
        'searchRelationInCollection',
        'searchNoteInCollection',

        'tag',
        ))

# Sanity check
for req_action in REQUIRES_AUTHENTICATION:
    assert req_action in DISPATCHER, (
            'INTERNAL ERROR: undefined action in REQUIRES_AUTHENTICATION set')
###


class NoActionError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Client sent no action for request'

    def json(self, json_dic):
        json_dic['exception'] = 'noAction'
        return json_dic


class InvalidActionError(ProtocolError):
    def __init__(self, attempted_action):
        self.attempted_action = attempted_action

    def __str__(self):
        return 'Client sent an invalid action "%s"' % self.attempted_action

    def json(self, json_dic):
        json_dic['exception'] = 'invalidAction',
        return json_dic


class InvalidActionArgsError(ProtocolError):
    def __init__(self, attempted_action, missing_arg):
        self.attempted_action = attempted_action
        self.missing_arg = missing_arg

    def __str__(self):
        return 'Client did not supply argument "%s" for action "%s"' % (self.missing_arg, self.attempted_action)

    def json(self, json_dic):
        json_dic['exception'] = 'invalidActionArgs',
        return json_dic


class DirectorySecurityError(ProtocolError):
    def __init__(self, requested):
        self.requested = requested

    def __str__(self):
        return 'Client sent request for bad directory: ' + self.requested

    def json(self, json_dic):
        json_dic['exception'] = 'directorySecurity',
        return json_dic


class ProtocolVersionMismatchError(ProtocolError):
    def __init__(self, was, correct):
        self.was = was
        self.correct = correct

    def __str__(self):
        return '\n'.join((
            ('Client-server mismatch, please reload the page to update your '
                'client. If this does not work, please contact your '
                'administrator'),
            ('Client sent request with version "%s", server is using version '
                '%s') % (self.was, self.correct, ),
            ))

    def json(self, json_dic):
        json_dic['exception'] = 'protocolVersionMismatch',
        return json_dic


def _directory_is_safe(dir_path):
    # TODO: Make this less naive
    if not dir_path.startswith('/'):
        # We only accept absolute paths in the data directory
        return False

    # Make a simple test that the directory is inside the data directory
    return abspath(path_join(DATA_DIR, dir_path[1:])
            ).startswith(normpath(DATA_DIR))

def dispatch(http_args, client_ip, client_hostname):
    action = http_args['action']

    log_info('dispatcher handling action: %s' % (action, ));

    # Verify that we don't have a protocol version mismatch
    PROTOCOL_VERSION = 1
    try:
        protocol_version = int(http_args['protocol'])
        if protocol_version != PROTOCOL_VERSION:
            raise ProtocolVersionMismatchError(protocol_version,
                    PROTOCOL_VERSION)
    except TypeError:
        raise ProtocolVersionMismatchError('None', PROTOCOL_VERSION)
    except ValueError:
        raise ProtocolVersionMismatchError(http_args['protocol'],
                PROTOCOL_VERSION)
    
    # Was an action supplied?
    if action is None:
        raise NoActionError

    # If we got a directory (collection), check it for security
    if http_args['collection'] is not None:
        if not _directory_is_safe(http_args['collection']):
            raise DirectorySecurityError(http_args['collection'])

    # Make sure that we are authenticated if we are to do certain actions
    if action in REQUIRES_AUTHENTICATION:
        try:
            user = get_session()['user']
        except KeyError:
            user = None
        if user is None:
            log_info('Authorization failure for "%s" with hostname "%s"'
                     % (client_ip, client_hostname))
            raise NotAuthorisedError(action)

    # Fetch the action function for this action (if any)
    try:
        action_function = DISPATCHER[action]
    except KeyError:
        log_info('Invalid action "%s"' % action)
        raise InvalidActionError(action)

    # Determine what arguments the action function expects
    args, varargs, keywords, defaults = getargspec(action_function)
    # We will not allow this for now, there is most likely no need for it
    assert varargs is None, 'no varargs for action functions'
    assert keywords is None, 'no keywords for action functions'

    # XXX: Quick hack
    if defaults is None:
        defaults = []

    # These arguments already has default values
    default_val_by_arg = {}
    for arg, default_val in izip(args[-len(defaults):], defaults):
        default_val_by_arg[arg] = default_val

    action_args = []
    for arg_name in args:
        arg_val = http_args[arg_name]

        # The client failed to provide this argument
        if arg_val is None:
            try:
                arg_val = default_val_by_arg[arg_name]
            except KeyError:
                raise InvalidActionArgsError(action, arg_name)

        action_args.append(arg_val)

    log_info('dispatcher will call %s(%s)' % (action,
        ', '.join((repr(a) for a in action_args)), ))

    # Log annotation actions separately (if so configured)
    if action in LOGGED_ANNOTATOR_ACTION:
        log_annotation(http_args['collection'],
                       http_args['document'],
                       'START', action, action_args)

    # TODO: log_annotation for exceptions?

    json_dic = action_function(*action_args)

    # Log annotation actions separately (if so configured)
    if action in LOGGED_ANNOTATOR_ACTION:
        log_annotation(http_args['collection'],
                        http_args['document'],
                       'FINISH', action, action_args)

    # Assign which action that was performed to the json_dic
    json_dic['action'] = action
    # Return the protocol version for symmetry
    json_dic['protocol'] = PROTOCOL_VERSION
    return json_dic

########NEW FILE########
__FILENAME__ = docimport
#!/usr/bin/env python

from __future__ import with_statement

'''
Simple interface to for importing files into the data directory.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-02-21
'''

from annotation import open_textfile
from common import ProtocolError
from config import DATA_DIR
from document import real_directory
from annotation import JOINED_ANN_FILE_SUFF, TEXT_FILE_SUFFIX
from os.path import join as join_path
from os.path import isdir, isfile
from os import access, W_OK

### Constants
DEFAULT_IMPORT_DIR = 'import'
###


class InvalidDirError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'Invalid directory'

    def json(self, json_dic):
        json_dic['exception'] = 'invalidDirError'
        return json_dic


class FileExistsError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'File exists: %s' % self.path

    def json(self, json_dic):
        json_dic['exception'] = 'fileExistsError'
        return json_dic


class NoWritePermissionError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'No write permission to %s' % self.path

    def json(self, json_dic):
        json_dic['exception'] = 'noWritePermissionError'
        return json_dic


#TODO: Chop this function up
def save_import(text, docid, collection=None):
    '''
    TODO: DOC:
    '''

    directory = collection

    if directory is None:
        dir_path = DATA_DIR
    else:
        #XXX: These "security" measures can surely be fooled
        if (directory.count('../') or directory == '..'):
            raise InvalidDirError(directory)

        dir_path = real_directory(directory)

    # Is the directory a directory and are we allowed to write?
    if not isdir(dir_path):
        raise InvalidDirError(dir_path)
    if not access(dir_path, W_OK):
        raise NoWritePermissionError(dir_path)

    base_path = join_path(dir_path, docid)
    txt_path = base_path + '.' + TEXT_FILE_SUFFIX
    ann_path = base_path + '.' + JOINED_ANN_FILE_SUFF

    # Before we proceed, verify that we are not overwriting
    for path in (txt_path, ann_path):
        if isfile(path):
            raise FileExistsError(path)

    # Make sure we have a valid POSIX text file, i.e. that the
    # file ends in a newline.
    if text != "" and text[-1] != '\n':
        text = text + '\n'

    with open_textfile(txt_path, 'w') as txt_file:
        txt_file.write(text)

    # Touch the ann file so that we can edit the file later
    with open(ann_path, 'w') as _:
        pass

    return { 'document': docid }

if __name__ == '__main__':
    # TODO: Update these to conform with the new API
    '''
    from unittest import TestCase
    from tempfile import mkdtemp
    from shutil import rmtree
    from os import mkdir


    class SaveImportTest(TestCase):
        test_text = 'This is not a drill, this is a drill *BRRR!*'
        test_dir = 'test'
        test_filename = 'test'

        def setUp(self):
            self.tmpdir = mkdtemp()
            mkdir(join_path(self.tmpdir, SaveImportTest.test_dir))
            mkdir(join_path(self.tmpdir, DEFAULT_IMPORT_DIR))

        def tearDown(self):
            rmtree(self.tmpdir)

        def test_import(self):
            save_import(SaveImportTest.test_text, SaveImportTest.test_filename,
                    relative_dir=SaveImportTest.test_dir,
                    directory=self.tmpdir)
        
        def test_default_import_dir(self):
            save_import(SaveImportTest.test_text, SaveImportTest.test_filename,
                    directory=self.tmpdir)
   

    import unittest
    unittest.main()
    '''

########NEW FILE########
__FILENAME__ = document
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# XXX: This module along with stats and annotator is pretty much pure chaos

from __future__ import with_statement

'''
Document handling functionality.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
            Illes Solt          <solt tmit bme hu>
Version:    2011-04-21
'''

from os import listdir
from os.path import abspath, dirname, isabs, isdir, normpath, getmtime
from os.path import join as path_join
from re import match,sub
from errno import ENOENT, EACCES

from annotation import (TextAnnotations, TEXT_FILE_SUFFIX,
        AnnotationFileNotFoundError, 
        AnnotationCollectionNotFoundError,
        JOINED_ANN_FILE_SUFF,
        open_textfile,
        BIONLP_ST_2013_COMPATIBILITY)
from common import ProtocolError, CollectionNotAccessibleError
from config import BASE_DIR, DATA_DIR
from projectconfig import (ProjectConfiguration, SEPARATOR_STR, 
        SPAN_DRAWING_ATTRIBUTES, ARC_DRAWING_ATTRIBUTES,
        VISUAL_SPAN_DEFAULT, VISUAL_ARC_DEFAULT, 
        ATTR_DRAWING_ATTRIBUTES, VISUAL_ATTR_DEFAULT,
        SPECIAL_RELATION_TYPES, 
        options_get_validation, options_get_tokenization,
        options_get_ssplitter, get_annotation_config_section_labels,
        visual_options_get_arc_bundle)
from stats import get_statistics
from message import Messager
from auth import allowed_to_read, AccessDeniedError
from annlog import annotation_logging_active

from itertools import chain

def _fill_type_configuration(nodes, project_conf, hotkey_by_type, all_connections=None):
    # all_connections is an optimization to reduce invocations of
    # projectconfig methods such as arc_types_from_to.
    if all_connections is None:
        all_connections = project_conf.all_connections()

    items = []
    for node in nodes:
        if node == SEPARATOR_STR:
            items.append(None)
        else:
            item = {}
            _type = node.storage_form() 

            # This isn't really a great place to put this, but we need
            # to block these magic values from getting to the client.
            # TODO: resolve cleanly, preferably by not storing this with
            # other relations at all.
            if _type in SPECIAL_RELATION_TYPES:
                continue

            item['name'] = project_conf.preferred_display_form(_type)
            item['type'] = _type
            item['unused'] = node.unused
            item['labels'] = project_conf.get_labels_by_type(_type)
            item['attributes'] = project_conf.attributes_for(_type)
            item['normalizations'] = node.normalizations()

            span_drawing_conf = project_conf.get_drawing_config_by_type(_type) 
            if span_drawing_conf is None:
                span_drawing_conf = project_conf.get_drawing_config_by_type(VISUAL_SPAN_DEFAULT)
            if span_drawing_conf is None:
                span_drawing_conf = {}
            for k in SPAN_DRAWING_ATTRIBUTES:
                if k in span_drawing_conf:
                    item[k] = span_drawing_conf[k]
            
            try:
                item['hotkey'] = hotkey_by_type[_type]
            except KeyError:
                pass

            arcs = []

            # Note: for client, relations are represented as "arcs"
            # attached to "spans" corresponding to entity annotations.

            # To avoid redundant entries, fill each type at most once.
            filled_arc_type = {}

            for arc in chain(project_conf.relation_types_from(_type), node.arg_list):
                if arc in filled_arc_type:
                    continue
                filled_arc_type[arc] = True

                curr_arc = {}
                curr_arc['type'] = arc

                arc_labels = project_conf.get_labels_by_type(arc)
                curr_arc['labels'] = arc_labels if arc_labels is not None else [arc]

                try:
                    curr_arc['hotkey'] = hotkey_by_type[arc]
                except KeyError:
                    pass
                
                arc_drawing_conf = project_conf.get_drawing_config_by_type(arc)
                if arc_drawing_conf is None:
                    arc_drawing_conf = project_conf.get_drawing_config_by_type(VISUAL_ARC_DEFAULT)
                if arc_drawing_conf is None:
                    arc_drawing_conf = {}
                for k in ARC_DRAWING_ATTRIBUTES:
                    if k in arc_drawing_conf:
                        curr_arc[k] = arc_drawing_conf[k]                    

                # Client needs also possible arc 'targets',
                # defined as the set of types (entity or event) that
                # the arc can connect to

                # This bit doesn't make sense for relations, which are
                # already "arcs" (see comment above).
                # TODO: determine if this should be an error: relation
                # config should now go through _fill_relation_configuration
                # instead.
                if project_conf.is_relation_type(_type):
                    targets = []
                else:
                    targets = []

                    if arc in all_connections[_type]:
                        targets = all_connections[_type][arc]

                    # TODO: this code remains here to allow for further checking of the
                    # new all_connections() functionality. Comment out to activate
                    # verification of the new implementation (above) against the old one
                    # (below, commented out).
#                     check_targets = []
#                     for ttype in project_conf.get_entity_types() + project_conf.get_event_types():
#                         if arc in project_conf.arc_types_from_to(_type, ttype):
#                             check_targets.append(ttype)

#                     if targets == check_targets:
#                         Messager.info("CHECKS OUT!")
#                     elif sorted(targets) == sorted(check_targets):
#                         Messager.warning("Different sort order for %s -> %s:\n%s\n%s" % (_type, arc, str(targets), str(check_targets)), 10)
#                     else:
#                         Messager.error("Mismatch for %s -> %s:\n%s\n%s" % (_type, arc, str(sorted(targets)), str(sorted(check_targets))), -1)

                curr_arc['targets'] = targets

                arcs.append(curr_arc)
                    
            # If we found any arcs, attach them
            if arcs:
                item['arcs'] = arcs

            item['children'] = _fill_type_configuration(node.children,
                    project_conf, hotkey_by_type, all_connections)
            items.append(item)
    return items

# TODO: duplicates part of _fill_type_configuration
def _fill_relation_configuration(nodes, project_conf, hotkey_by_type):
    items = []
    for node in nodes:
        if node == SEPARATOR_STR:
            items.append(None)
        else:
            item = {}
            _type = node.storage_form() 

            if _type in SPECIAL_RELATION_TYPES:
                continue

            item['name'] = project_conf.preferred_display_form(_type)
            item['type'] = _type
            item['unused'] = node.unused
            item['labels'] = project_conf.get_labels_by_type(_type)
            item['attributes'] = project_conf.attributes_for(_type)

            # TODO: avoid magic value
            item['properties'] = {}
            if '<REL-TYPE>' in node.special_arguments:
                for special_argument in node.special_arguments['<REL-TYPE>']:
                    item['properties'][special_argument] = True

            arc_drawing_conf = project_conf.get_drawing_config_by_type(_type)
            if arc_drawing_conf is None:
                arc_drawing_conf = project_conf.get_drawing_config_by_type(VISUAL_ARC_DEFAULT)
            if arc_drawing_conf is None:
                arc_drawing_conf = {}
            for k in ARC_DRAWING_ATTRIBUTES:
                if k in arc_drawing_conf:
                    item[k] = arc_drawing_conf[k]                    
            
            try:
                item['hotkey'] = hotkey_by_type[_type]
            except KeyError:
                pass

            # minimal info on argument types to allow differentiation of e.g.
            # "Equiv(Protein, Protein)" and "Equiv(Organism, Organism)"
            args = []
            for arg in node.arg_list:
                curr_arg = {}
                curr_arg['role'] = arg
                # TODO: special type (e.g. "<ENTITY>") expansion via projectconf
                curr_arg['targets'] = node.arguments[arg]

                args.append(curr_arg)

            item['args'] = args

            item['children'] = _fill_relation_configuration(node.children,
                    project_conf, hotkey_by_type)
            items.append(item)
    return items


# TODO: this may not be a good spot for this
def _fill_attribute_configuration(nodes, project_conf):
    items = []
    for node in nodes:
        if node == SEPARATOR_STR:
            continue
        else:
            item = {}
            _type = node.storage_form() 
            item['name'] = project_conf.preferred_display_form(_type)
            item['type'] = _type
            item['unused'] = node.unused
            item['labels'] = project_conf.get_labels_by_type(_type)

            attr_drawing_conf = project_conf.get_drawing_config_by_type(_type)
            if attr_drawing_conf is None:
                attr_drawing_conf = project_conf.get_drawing_config_by_type(VISUAL_ATTR_DEFAULT)
            if attr_drawing_conf is None:
                attr_drawing_conf = {}

            # Check if the possible values for the argument are specified
            # TODO: avoid magic strings
            if "Value" in node.arguments:
                args = node.arguments["Value"]
            else:
                # no "Value" defined; assume binary.
                args = []

            # Check if a default value is specified for the attribute
            if '<DEFAULT>' in node.special_arguments:
                try:
                    item['default'] = node.special_arguments['<DEFAULT>'][0]
                except IndexError:
                    Messager.warning("Config error: empty <DEFAULT> for %s" % item['name'])
                    pass

            if len(args) == 0:
                # binary; use drawing config directly
                item['values'] = { _type : {} }
                for k in ATTR_DRAWING_ATTRIBUTES:
                    if k in attr_drawing_conf:
                        # protect against error from binary attribute
                        # having multi-valued visual config (#698)
                        if isinstance(attr_drawing_conf[k], list):
                            Messager.warning("Visual config error: expected single value for %s binary attribute '%s' config, found %d. Visuals may be wrong." % (_type, k, len(attr_drawing_conf[k])))
                            # fall back on the first just to have something.
                            item['values'][_type][k] = attr_drawing_conf[k][0]
                        else:
                            item['values'][_type][k] = attr_drawing_conf[k]
            else:
                # has normal arguments, use these as possible values.
                # (this is quite terrible all around, sorry.)
                item['values'] = {}
                for i, v in enumerate(args):
                    item['values'][v] = {}
                    # match up annotation config with drawing config by
                    # position in list of alternative values so that e.g.
                    # "Values:L1|L2|L3" can have the visual config
                    # "glyph:[1]|[2]|[3]". If only a single value is
                    # defined, apply to all.
                    for k in ATTR_DRAWING_ATTRIBUTES:
                        if k in attr_drawing_conf:
                            # (sorry about this)
                            if isinstance(attr_drawing_conf[k], list):
                                # sufficiently many specified?
                                if len(attr_drawing_conf[k]) > i:
                                    item['values'][v][k] = attr_drawing_conf[k][i]
                                else:
                                    Messager.warning("Visual config error: expected %d values for %s attribute '%s' config, found only %d. Visuals may be wrong." % (len(args), v, k, len(attr_drawing_conf[k])))
                            else:
                                # single value (presumably), apply to all
                                item['values'][v][k] = attr_drawing_conf[k]

                    # if no drawing attribute was defined, fall back to
                    # using a glyph derived from the attribute value
                    if len([k for k in ATTR_DRAWING_ATTRIBUTES if
                            k in item['values'][v]]) == 0:
                        item['values'][v]['glyph'] = '['+v+']'

            items.append(item)
    return items

def _fill_visual_configuration(types, project_conf):
    # similar to _fill_type_configuration, but for types for which
    # full annotation configuration was not found but some visual
    # configuration can be filled.

    # TODO: duplicates parts of _fill_type_configuration; combine?
    items = []
    for _type in types:
        item = {}
        item['name'] = project_conf.preferred_display_form(_type)
        item['type'] = _type
        item['unused'] = True
        item['labels'] = project_conf.get_labels_by_type(_type)

        drawing_conf = project_conf.get_drawing_config_by_type(_type) 
        # not sure if this is a good default, but let's try
        if drawing_conf is None:
            drawing_conf = project_conf.get_drawing_config_by_type(VISUAL_SPAN_DEFAULT)
        if drawing_conf is None:
            drawing_conf = {}
        # just plug in everything found, whether for a span or arc
        for k in chain(SPAN_DRAWING_ATTRIBUTES, ARC_DRAWING_ATTRIBUTES):
            if k in drawing_conf:
                item[k] = drawing_conf[k]

        # TODO: anything else?

        items.append(item)

    return items

# TODO: this is not a good spot for this
def get_base_types(directory):
    project_conf = ProjectConfiguration(directory)

    keymap = project_conf.get_kb_shortcuts()
    hotkey_by_type = dict((v, k) for k, v in keymap.iteritems())

    # fill config for nodes for which annotation is configured

    # calculate once only (this can get heavy)
    all_connections = project_conf.all_connections()
    
    event_hierarchy = project_conf.get_event_type_hierarchy()
    event_types = _fill_type_configuration(event_hierarchy,
            project_conf, hotkey_by_type, all_connections)

    entity_hierarchy = project_conf.get_entity_type_hierarchy()
    entity_types = _fill_type_configuration(entity_hierarchy,
            project_conf, hotkey_by_type, all_connections)

    relation_hierarchy = project_conf.get_relation_type_hierarchy()
    relation_types = _fill_relation_configuration(relation_hierarchy,
            project_conf, hotkey_by_type)

    # make visual config available also for nodes for which there is
    # no annotation config. Note that defaults (SPAN_DEFAULT etc.)
    # are included via get_drawing_types() if defined.
    unconfigured = [l for l in (project_conf.get_labels().keys() +
                                project_conf.get_drawing_types()) if 
                    not project_conf.is_configured_type(l)]
    unconf_types = _fill_visual_configuration(unconfigured, project_conf)

    return event_types, entity_types, relation_types, unconf_types

def get_attribute_types(directory):
    project_conf = ProjectConfiguration(directory)

    entity_attribute_hierarchy = project_conf.get_entity_attribute_type_hierarchy()
    entity_attribute_types = _fill_attribute_configuration(entity_attribute_hierarchy, project_conf)
    
    relation_attribute_hierarchy = project_conf.get_relation_attribute_type_hierarchy()
    relation_attribute_types = _fill_attribute_configuration(relation_attribute_hierarchy, project_conf)

    event_attribute_hierarchy = project_conf.get_event_attribute_type_hierarchy()
    event_attribute_types = _fill_attribute_configuration(event_attribute_hierarchy, project_conf)

    return entity_attribute_types, relation_attribute_types, event_attribute_types

def get_search_config(directory):
    return ProjectConfiguration(directory).get_search_config()

def get_disambiguator_config(directory):
    return ProjectConfiguration(directory).get_disambiguator_config()

def get_normalization_config(directory):
    return ProjectConfiguration(directory).get_normalization_config()

def get_annotator_config(directory):
    # TODO: "annotator" is a very confusing term for a web service
    # that does automatic annotation in the context of a tool
    # where most annotators are expected to be human. Rethink.
    return ProjectConfiguration(directory).get_annotator_config()

def assert_allowed_to_read(doc_path):
    if not allowed_to_read(doc_path):
        raise AccessDeniedError # Permission denied by access control

def real_directory(directory, rel_to=DATA_DIR):
    assert isabs(directory), 'directory "%s" is not absolute' % directory
    return path_join(rel_to, directory[1:])

def relative_directory(directory):
    # inverse of real_directory
    assert isabs(directory), 'directory "%s" is not absolute' % directory
    assert directory.startswith(DATA_DIR), 'directory "%s" not under DATA_DIR'
    return directory[len(DATA_DIR):]

def _is_hidden(file_name):
    return file_name.startswith('hidden_') or file_name.startswith('.')

def _listdir(directory):
    #return listdir(directory)
    try:
        assert_allowed_to_read(directory)
        return [f for f in listdir(directory) if not _is_hidden(f)
                and allowed_to_read(path_join(directory, f))]
    except OSError, e:
        Messager.error("Error listing %s: %s" % (directory, e))
        raise AnnotationCollectionNotFoundError(directory)
    
def _getmtime(file_path):
    '''
    Internal wrapper of getmtime that handles access denied and invalid paths
    according to our specification.

    Arguments:

    file_path - path to the file to get the modification time for
    '''

    try:
        return getmtime(file_path)
    except OSError, e:
        if e.errno in (EACCES, ENOENT):
            # The file did not exist or permission denied, we use -1 to
            #   indicate this since mtime > 0 is an actual time.
            return -1
        else:
            # We are unable to handle this exception, pass it one
            raise


class InvalidConfiguration(ProtocolError):
    def json(self, json_dic):
        json_dic['exception'] = 'invalidConfiguration'
        return json_dic


# TODO: Is this what we would call the configuration? It is minimal.
def get_configuration(name):
    # TODO: Rip out this path somewhere
    config_dir = path_join(BASE_DIR, 'configurations')
    for conf_name in listdir(config_dir):
        if conf_name == name:
            config_path = path_join(config_dir, conf_name)
            break
    else:
        raise InvalidConfiguration

    return _inject_annotation_type_conf(config_path)

def _inject_annotation_type_conf(dir_path, json_dic=None):
    if json_dic is None:
        json_dic = {}

    (event_types, entity_types, rel_types,
            unconf_types) = get_base_types(dir_path)
    (entity_attr_types, rel_attr_types,
            event_attr_types) = get_attribute_types(dir_path)

    json_dic['event_types'] = event_types
    json_dic['entity_types'] = entity_types
    json_dic['relation_types'] = rel_types
    json_dic['event_attribute_types'] = event_attr_types
    json_dic['relation_attribute_types'] = rel_attr_types
    json_dic['entity_attribute_types'] = entity_attr_types
    json_dic['unconfigured_types'] = unconf_types

    # inject annotation category aliases (e.g. "entities" -> "spans")
    # used in config (#903).
    section_labels = get_annotation_config_section_labels(dir_path)
    json_dic['ui_names'] = {}
    for c in ['entities', 'relations', 'events', 'attributes']:
        json_dic['ui_names'][c] = section_labels.get(c,c)

    # inject general visual options (currently just arc bundling) (#949)
    visual_options = {}
    visual_options['arc_bundle'] = visual_options_get_arc_bundle(dir_path)
    json_dic['visual_options'] = visual_options

    return json_dic

# TODO: This is not the prettiest of functions
def get_directory_information(collection):
    directory = collection

    real_dir = real_directory(directory)
    
    assert_allowed_to_read(real_dir)
    
    # Get the document names
    base_names = [fn[0:-4] for fn in _listdir(real_dir)
            if fn.endswith('txt')]

    doclist = base_names[:]
    doclist_header = [("Document", "string")]

    # Then get the modification times
    doclist_with_time = []
    for file_name in doclist:
        file_path = path_join(DATA_DIR, real_dir,
            file_name + "." + JOINED_ANN_FILE_SUFF)
        doclist_with_time.append([file_name, _getmtime(file_path)])
    doclist = doclist_with_time
    doclist_header.append(("Modified", "time"))

    try:
        stats_types, doc_stats = get_statistics(real_dir, base_names)
    except OSError:
        # something like missing access permissions?
        raise CollectionNotAccessibleError
                
    doclist = [doclist[i] + doc_stats[i] for i in range(len(doclist))]
    doclist_header += stats_types

    dirlist = [dir for dir in _listdir(real_dir)
            if isdir(path_join(real_dir, dir))]
    # just in case, and for generality
    dirlist = [[dir] for dir in dirlist]

    # check whether at root, ignoring e.g. possible trailing slashes
    if normpath(real_dir) != normpath(DATA_DIR):
        parent = abspath(path_join(real_dir, '..'))[len(DATA_DIR) + 1:]
        # to get consistent processing client-side, add explicitly to list
        dirlist.append([".."])
    else:
        parent = None

    # combine document and directory lists, adding a column
    # differentiating files from directories and an unused column (can
    # point to a specific annotation) required by the protocol.  The
    # values filled here for the first are "c" for "collection"
    # (i.e. directory) and "d" for "document".
    combolist = []
    for i in dirlist:
        combolist.append(["c", None]+i)
    for i in doclist:
        combolist.append(["d", None]+i)

    # plug in the search config too
    search_config = get_search_config(real_dir)

    # ... and the disambiguator config ... this is getting a bit much
    disambiguator_config = get_disambiguator_config(real_dir)

    # ... and the normalization config (TODO: rethink)
    normalization_config = get_normalization_config(real_dir)

    # read in README (if any) to send as a description of the
    # collection
    try:
        with open_textfile(path_join(real_dir, "README")) as txt_file:
            readme_text = txt_file.read()
    except IOError:
        readme_text = None

    # fill in a flag for whether annotator logging is active so that
    # the client knows whether to invoke timing actions
    ann_logging = annotation_logging_active(real_dir)

    # fill in NER services, if any
    ner_taggers = get_annotator_config(real_dir)

    return _inject_annotation_type_conf(real_dir, json_dic={
            'items': combolist,
            'header' : doclist_header,
            'parent': parent,
            'messages': [],
            'description': readme_text,
            'search_config': search_config,
            'disambiguator_config' : disambiguator_config,
            'normalization_config' : normalization_config,
            'annotation_logging': ann_logging,
            'ner_taggers': ner_taggers,
            })

class UnableToReadTextFile(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'Unable to read text file %s' % self.path

    def json(self, json_dic):
        json_dic['exception'] = 'unableToReadTextFile'
        return json_dic

class IsDirectoryError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return ''

    def json(self, json_dic):
        json_dic['exception'] = 'isDirectoryError'
        return json_dic

#TODO: All this enrichment isn't a good idea, at some point we need an object
def _enrich_json_with_text(j_dic, txt_file_path, raw_text=None):
    if raw_text is not None:
        # looks like somebody read this already; nice
        text = raw_text
    else:
        # need to read raw text
        try:
            with open_textfile(txt_file_path, 'r') as txt_file:
                text = txt_file.read()
        except IOError:
            raise UnableToReadTextFile(txt_file_path)
        except UnicodeDecodeError:
            Messager.error('Error reading text file: nonstandard encoding or binary?', -1)
            raise UnableToReadTextFile(txt_file_path)

    j_dic['text'] = text
    
    from logging import info as log_info

    tokeniser = options_get_tokenization(dirname(txt_file_path))

    # First, generate tokenisation
    if tokeniser == 'mecab':
        from tokenise import jp_token_boundary_gen
        tok_offset_gen = jp_token_boundary_gen
    elif tokeniser == 'whitespace':
        from tokenise import whitespace_token_boundary_gen
        tok_offset_gen = whitespace_token_boundary_gen
    elif tokeniser == 'ptblike':
        from tokenise import gtb_token_boundary_gen
        tok_offset_gen = gtb_token_boundary_gen
    else:
        Messager.warning('Unrecognized tokenisation option '
                ', reverting to whitespace tokenisation.')
        from tokenise import whitespace_token_boundary_gen
        tok_offset_gen = whitespace_token_boundary_gen
    j_dic['token_offsets'] = [o for o in tok_offset_gen(text)]

    ssplitter = options_get_ssplitter(dirname(txt_file_path))
    if ssplitter == 'newline':
        from ssplit import newline_sentence_boundary_gen
        ss_offset_gen = newline_sentence_boundary_gen
    elif ssplitter == 'regex':
        from ssplit import regex_sentence_boundary_gen
        ss_offset_gen = regex_sentence_boundary_gen
    else:
        Messager.warning('Unrecognized sentence splitting option '
                ', reverting to newline sentence splitting.')
        from ssplit import newline_sentence_boundary_gen
        ss_offset_gen = newline_sentence_boundary_gen
    j_dic['sentence_offsets'] = [o for o in ss_offset_gen(text)]

    return True

def _enrich_json_with_data(j_dic, ann_obj):
    # TODO: figure out if there's a reason for all the unicode()
    # invocations here; remove if not.

    # We collect trigger ids to be able to link the textbound later on
    trigger_ids = set()
    for event_ann in ann_obj.get_events():
        trigger_ids.add(event_ann.trigger)
        j_dic['events'].append(
                [unicode(event_ann.id), unicode(event_ann.trigger), event_ann.args]
                )

    for rel_ann in ann_obj.get_relations():
        j_dic['relations'].append(
            [unicode(rel_ann.id), unicode(rel_ann.type), 
             [(rel_ann.arg1l, rel_ann.arg1),
              (rel_ann.arg2l, rel_ann.arg2)]]
            )

    for tb_ann in ann_obj.get_textbounds():
        #j_tb = [unicode(tb_ann.id), tb_ann.type, tb_ann.start, tb_ann.end]
        j_tb = [unicode(tb_ann.id), tb_ann.type, tb_ann.spans]

        # If we spotted it in the previous pass as a trigger for an
        # event or if the type is known to be an event type, we add it
        # as a json trigger.
        # TODO: proper handling of disconnected triggers. Currently
        # these will be erroneously passed as 'entities'
        if unicode(tb_ann.id) in trigger_ids:
            j_dic['triggers'].append(j_tb)
            # special case for BioNLP ST 2013 format: send triggers
            # also as entities for those triggers that are referenced
            # from annotations other than events (#926).
            if BIONLP_ST_2013_COMPATIBILITY:
                if tb_ann.id in ann_obj.externally_referenced_triggers:
                    try:
                        j_dic['entities'].append(j_tb)
                    except KeyError:
                        j_dic['entities'] = [j_tb, ]
        else: 
            try:
                j_dic['entities'].append(j_tb)
            except KeyError:
                j_dic['entities'] = [j_tb, ]


    for eq_ann in ann_obj.get_equivs():
        j_dic['equivs'].append(
                (['*', eq_ann.type]
                    + [e for e in eq_ann.entities])
                )

    for att_ann in ann_obj.get_attributes():
        j_dic['attributes'].append(
                [unicode(att_ann.id), unicode(att_ann.type), unicode(att_ann.target), att_ann.value]
                )

    for norm_ann in ann_obj.get_normalizations():
        j_dic['normalizations'].append(
                [unicode(norm_ann.id), unicode(norm_ann.type), 
                 unicode(norm_ann.target), unicode(norm_ann.refdb), 
                 unicode(norm_ann.refid), unicode(norm_ann.reftext)]
                )

    for com_ann in ann_obj.get_oneline_comments():
        comment = [unicode(com_ann.target), unicode(com_ann.type),
                com_ann.tail.strip()]
        try:
            j_dic['comments'].append(comment)
        except KeyError:
            j_dic['comments'] = [comment, ]

    if ann_obj.failed_lines:
        error_msg = 'Unable to parse the following line(s):\n%s' % (
                '\n'.join(
                [('%s: %s' % (
                            # The line number is off by one
                            unicode(line_num + 1),
                            unicode(ann_obj[line_num])
                            )).strip()
                 for line_num in ann_obj.failed_lines])
                )
        Messager.error(error_msg, duration=len(ann_obj.failed_lines) * 3)

    j_dic['mtime'] = ann_obj.ann_mtime
    j_dic['ctime'] = ann_obj.ann_ctime

    try:
        # XXX avoid digging the directory from the ann_obj
        import os
        docdir = os.path.dirname(ann_obj._document)
        if options_get_validation(docdir) in ('all', 'full', ):
            from verify_annotations import verify_annotation
            projectconf = ProjectConfiguration(docdir)
            issues = verify_annotation(ann_obj, projectconf)
        else:
            issues = []
    except Exception, e:
        # TODO add an issue about the failure?
        issues = []
        Messager.error('Error: verify_annotation() failed: %s' % e, -1)

    for i in issues:
        issue = (unicode(i.ann_id), i.type, i.description)
        try:
            j_dic['comments'].append(issue)
        except:
            j_dic['comments'] = [issue, ]

    # Attach the source files for the annotations and text
    from os.path import splitext
    from annotation import TEXT_FILE_SUFFIX
    ann_files = [splitext(p)[1][1:] for p in ann_obj._input_files]
    ann_files.append(TEXT_FILE_SUFFIX)
    ann_files = [p for p in set(ann_files)]
    ann_files.sort()
    j_dic['source_files'] = ann_files

def _enrich_json_with_base(j_dic):
    # TODO: Make the names here and the ones in the Annotations object conform

    # TODO: "from offset" of what? Commented this out, remove once
    # sure that nothing is actually using this.
#     # This is the from offset
#     j_dic['offset'] = 0

    for d in (
        'entities',
        'events',
        'relations',
        'triggers',
        'modifications',
        'attributes',
        'equivs',
        'normalizations',
        'comments',
        ):
        j_dic[d] = []

def _document_json_dict(document):
    #TODO: DOC!

    # pointing at directory instead of document?
    if isdir(document):
        raise IsDirectoryError(document)

    j_dic = {}
    _enrich_json_with_base(j_dic)

    #TODO: We don't check if the files exist, let's be more error friendly
    # Read in the textual data to make it ready to push
    _enrich_json_with_text(j_dic, document + '.' + TEXT_FILE_SUFFIX)

    with TextAnnotations(document) as ann_obj:
        # Note: At this stage the sentence offsets can conflict with the
        #   annotations, we thus merge any sentence offsets that lie within
        #   annotations
        # XXX: ~O(tb_ann * sentence_breaks), can be optimised
        # XXX: The merge strategy can lead to unforeseen consequences if two
        #   sentences are not adjacent (the format allows for this:
        #   S_1: [0, 10], S_2: [15, 20])
        s_breaks = j_dic['sentence_offsets']
        for tb_ann in ann_obj.get_textbounds():
            s_i = 0
            while s_i < len(s_breaks):
                s_start, s_end = s_breaks[s_i]
                # Does any subspan of the annotation strech over the
                # end of the sentence?
                found_spanning = False
                for tb_start, tb_end in tb_ann.spans:
                    if tb_start < s_end and tb_end > s_end:
                        found_spanning = True
                        break
                if found_spanning:
                    # Merge this sentence and the next sentence
                    s_breaks[s_i] = (s_start, s_breaks[s_i + 1][1])
                    del s_breaks[s_i + 1]
                else:
                    s_i += 1
        
        _enrich_json_with_data(j_dic, ann_obj)

    return j_dic

def get_document(collection, document):
    directory = collection
    real_dir = real_directory(directory)
    doc_path = path_join(real_dir, document)
    return _document_json_dict(doc_path)

def get_document_timestamp(collection, document):
    directory = collection
    real_dir = real_directory(directory)
    assert_allowed_to_read(real_dir)
    doc_path = path_join(real_dir, document)
    ann_path = doc_path + '.' + JOINED_ANN_FILE_SUFF
    mtime = _getmtime(ann_path)

    return {
            'mtime': mtime,
            }

########NEW FILE########
__FILENAME__ = download
'''
Serves annotation related files for downloads.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-10-03
'''

from __future__ import with_statement

from os import close as os_close, remove
from os.path import join as path_join, dirname, basename, normpath
from tempfile import mkstemp

from document import real_directory
from annotation import open_textfile
from common import NoPrintJSONError
from subprocess import Popen

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def download_file(document, collection, extension):
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, extension)
    fpath = path_join(real_dir, fname)

    hdrs = [('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Disposition',
                'inline; filename=%s' % fname)]
    with open_textfile(fpath, 'r') as txt_file:
        data = txt_file.read().encode('utf-8')
    raise NoPrintJSONError(hdrs, data)

def find_in_directory_tree(directory, filename):
    # TODO: DRY; partial dup of projectconfig.py:__read_first_in_directory_tree
    try:
        from config import BASE_DIR
    except ImportError:
        BASE_DIR = "/"
    from os.path import split, join, exists

    depth = 0
    directory, BASE_DIR = normpath(directory), normpath(BASE_DIR)
    while BASE_DIR in directory:
        if exists(join(directory, filename)):
            return (directory, depth)
        directory = split(directory)[0]
        depth += 1
    return (None, None)

def download_collection(collection, include_conf=False):
    directory = collection
    real_dir = real_directory(directory)
    dir_name = basename(dirname(real_dir))
    fname = '%s.%s' % (dir_name, 'tar.gz')

    confs = ['annotation.conf', 'visual.conf', 'tools.conf',
             'kb_shortcuts.conf']

    try:
        include_conf = int(include_conf)
    except ValueError:
        pass

    tmp_file_path = None
    try:
        tmp_file_fh, tmp_file_path = mkstemp()
        os_close(tmp_file_fh)

        tar_cmd_split = ['tar', '--exclude=.stats_cache']
        conf_names = []
        if not include_conf:
            tar_cmd_split.extend(['--exclude=%s' % c for c in confs])
        else:
            # also include configs from parent directories.
            for cname in confs:
                cdir, depth = find_in_directory_tree(real_dir, cname)
                if depth is not None and depth > 0:
                    relpath = path_join(dir_name, *['..' for _ in range(depth)])
                    conf_names.append(path_join(relpath, cname))
            if conf_names:
                # replace pathname components ending in ".." with target
                # directory name so that .confs in parent directories appear
                # in the target directory in the tar.
                tar_cmd_split.extend(['--absolute-names', '--transform',
                                      's|.*\\.\\.|%s|' %dir_name])

        tar_cmd_split.extend(['-c', '-z', '-f', tmp_file_path, dir_name])
        tar_cmd_split.extend(conf_names)
        tar_p = Popen(tar_cmd_split, cwd=path_join(real_dir, '..'))
        tar_p.wait()

        hdrs = [('Content-Type', 'application/octet-stream'), #'application/x-tgz'),
                ('Content-Disposition', 'inline; filename=%s' % fname)]
        with open(tmp_file_path, 'rb') as tmp_file:
            tar_data = tmp_file.read()

        raise NoPrintJSONError(hdrs, tar_data)
    finally:
        if tmp_file_path is not None:
            remove(tmp_file_path)

########NEW FILE########
__FILENAME__ = filelock
#!/usr/bin/env python

from __future__ import with_statement

'''
Provides a stylish pythonic file-lock:

>>>    with('file.lock'):
...        pass

Inspired by: http://code.activestate.com/recipes/576572/

Is *NIX specific due to being forced to use ps (suggestions on how to avoid
this are welcome).

But with added timeout and PID check to spice it all up and avoid stale
lock-files. Also includes a few unittests.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2009-12-26
'''

'''
Copyright (c) 2009, 2011, Pontus Stenetorp <pontus stenetorp se>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
'''

'''
Copyright (C) 2008 by Aaron Gallagher

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

from contextlib import contextmanager
from errno import EEXIST
from os import (remove, read, fsync, open, close, write, getpid,
        O_CREAT, O_EXCL, O_RDWR, O_RDONLY)
from subprocess import Popen, PIPE
from time import time, sleep
from sys import stderr

### Constants
# Disallow ignoring a lock-file although the PID is inactive
PID_DISALLOW = 1
# Ignore a lock-file if the noted PID is not running, but warn to stderr
PID_WARN = 2
# Ignore a lock-file if the noted PID is not running
PID_ALLOW = 3
###


class FileLockTimeoutError(Exception):
    '''
    Raised if a file-lock can not be acquired before the timeout is reached.
    '''
    def __init__(self, timeout):
        self.timeout = timeout

    def __str__(self):
        return 'Timed out when trying to acquire lock, waited (%d)s' % (
                self.timeout)


def _pid_exists(pid):
    '''
    Returns True if the given PID is a currently existing process id.

    Arguments:
    pid - Process id (PID) to check if it exists on the system
    '''
    # Not elegant, but it seems that it is the only way
    ps = Popen("ps %d | awk '{{print $1}}'" % (pid, ),
            shell=True, stdout=PIPE)
    ps.wait()
    return str(pid) in ps.stdout.read().split('\n')

@contextmanager
def file_lock(path, wait=0.1, timeout=1,
        pid_policy=PID_DISALLOW, err_output=stderr):
    '''
    Use the given path for a lock-file containing the PID of the process.
    If another lock request for the same file is requested, different policies
    can be set to determine how to handle it.

    Arguments:
    path - Path where to place the lock-file or where it is in place
    
    Keyword arguments:
    wait - Time to wait between attempts to lock the file
    timeout - Duration to attempt to lock the file until a timeout exception
        is raised
    pid_policy - A PID policy as found in the module, valid are PID_DISALLOW,
        PID_WARN and PID_ALLOW
    err_output - Where to print warning messages, for testing purposes
    '''
    start_time = time()
    while True:
        if time() - start_time > timeout:
            raise FileLockTimeoutError(timeout)
        try:
            fd = open(path, O_CREAT | O_EXCL | O_RDWR)
            write(fd, str(getpid()))
            fsync(fd)
            break
        except OSError, e:
            if e.errno == EEXIST:
                if pid_policy == PID_DISALLOW:
                    pass # Standard, just do nothing
                elif pid_policy == PID_WARN or pid_policy == PID_ALLOW:
                    fd = open(path, O_RDONLY)
                    pid = int(read(fd, 255))
                    close(fd)
                    if not _pid_exists(pid):
                        # Stale lock-file
                        if pid_policy == PID_WARN:
                            print >> err_output, (
                                    "Stale lock-file '%s', deleting" % (
                                        path))
                        remove(path)
                        continue
                else:
                    assert False, 'Invalid pid_policy argument'
            else:
                raise
        sleep(wait)
    try:
        yield fd
    finally:
        close(fd)
        remove(path)

if __name__ == '__main__':
    from unittest import TestCase
    import unittest

    from multiprocessing import Process
    from os import rmdir
    from os.path import join, isfile
    from tempfile import mkdtemp

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


    class TestFileLock(TestCase):
        def setUp(self):
            self._temp_dir = mkdtemp()
            self._lock_file_path = join(self._temp_dir, 'lock.file')

        def tearDown(self):
            try:
                remove(self._lock_file_path)
            except OSError:
                pass # It just didn't exist
            rmdir(self._temp_dir)

        def test_with(self):
            '''
            Tests do-with functionallity
            '''
            with file_lock(self._lock_file_path):
                sleep(1)
            sleep(0.1) # Make sure the remove is in effect
            self.assertFalse(isfile(self._lock_file_path))

        def test_exception(self):
            '''
            Tests if the lock-file does not remain if an exception occurs.
            '''
            try:
                with file_lock(self._lock_file_path):
                    raise Exception('Breaking out')
            except Exception:
                pass

            self.assertFalse(isfile(self._lock_file_path))

        def test_timeout(self):
            '''
            Test if a timeout is reached.
            '''
            # Use an impossible timeout
            try:
                with file_lock(self._lock_file_path, timeout=-1):
                    pass
                self.assertTrue(False, 'Should not reach this point')
            except FileLockTimeoutError:
                pass

        def test_lock(self):
            '''
            Test if a lock is indeed in place.
            '''
            def process_task(path):
                with file_lock(path):
                    sleep(1)
                return 0

            process = Process(target=process_task,
                    args=[self._lock_file_path])
            process.start()
            sleep(0.5) # Make sure it reaches the disk
            self.assertTrue(isfile(self._lock_file_path))
            sleep(1)

        def _fake_crash_other_process(self):
            '''
            Helper method to emulate a forced computer shutdown that leaves a
            lock-file intact.

            In theory the PID can have ended up being re-used at a later point
            but the likelihood of this can be considered to be low.
            '''
            def process_task(path):
                fd = open(path, O_CREAT | O_RDWR)
                try:
                    write(fd, str(getpid()))
                finally:
                    close(fd)
                return 0

            process = Process(target=process_task,
                    args=[self._lock_file_path])
            process.start()
            while process.is_alive():
                sleep(0.1)
            return process.pid

        def test_crash(self):
            '''
            Test that the fake crash mechanism is working.
            '''
            pid = self._fake_crash_other_process()
            self.assertTrue(isfile(self._lock_file_path))
            self.assertTrue(pid == int(
                read(open(self._lock_file_path, O_RDONLY), 255)))#XXX: Close

        ###
        def test_pid_disallow(self):
            '''
            Test if stale-lock files are respected if disallow policy is set.
            '''
            self._fake_crash_other_process()
            try:
                with file_lock(self._lock_file_path, pid_policy=PID_DISALLOW):
                    self.assertTrue(False, 'Should not reach this point')
            except FileLockTimeoutError:
                pass

        def test_pid_warn(self):
            '''
            Test if a stale lock-filk causes a warning to stderr and then is
            ignored if the warn policy is set.
            '''
            self._fake_crash_other_process()
            err_output = StringIO()
            try:
                with file_lock(self._lock_file_path, pid_policy=PID_WARN,
                        err_output=err_output):
                    pass
            except FileLockTimeoutError:
                self.assertTrue(False, 'Should not reach this point')
            err_output.seek(0)
            self.assertTrue(err_output.read(), 'No output although warn set')

        def test_pid_allow(self):
            '''
            Test if a stale lock-file is ignored and un-reported if the allow
            policy has been set.
            '''
            self._fake_crash_other_process()
            err_output = StringIO()
            try:
                with file_lock(self._lock_file_path, pid_policy=PID_ALLOW,
                        err_output=err_output):
                    pass
            except FileLockTimeoutError:
                self.assertTrue(False, 'Should not reach this point')
            err_output.seek(0)
            self.assertFalse(err_output.read(), 'Output although allow set')


    unittest.main()

########NEW FILE########
__FILENAME__ = gtbtokenize
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Implements a GENIA Treebank - like tokenization. 

# This is a python translation of my GTB-tokenize.pl, which in turn
# draws in part on Robert MacIntyre's 1995 PTB tokenizer,
# (http://www.cis.upenn.edu/~treebank/tokenizer.sed) and Yoshimasa
# Tsuruoka's GENIA tagger tokenization (tokenize.cpp;
# www-tsujii.is.s.u-tokyo.ac.jp/GENIA/tagger)

# by Sampo Pyysalo, 2011. Licensed under the MIT license.
# http://www.opensource.org/licenses/mit-license.php

# NOTE: intended differences to GTB tokenization:
# - Does not break "protein(s)" -> "protein ( s )"

from __future__ import with_statement

import re

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"
DEBUG_GTB_TOKENIZATION = False

# Penn treebank bracket escapes (others excluded)
PTB_ESCAPES = [('(', '-LRB-'),
               (')', '-RRB-'),
               ('[', '-LSB-'),
               (']', '-RSB-'),
               ('{', '-LCB-'),
               ('}', '-RCB-'),
               ]

def PTB_escape(s):
    for u, e in PTB_ESCAPES:
        s = s.replace(u, e)
    return s

def PTB_unescape(s):
    for u, e in PTB_ESCAPES:
        s = s.replace(e, u)
    return s

# processing in three stages: "initial" regexs run first, then
# "repeated" run as long as there are changes, and then "final"
# run. As the tokenize() function itself is trivial, comments relating
# to regexes given with the re.compiles.

__initial, __repeated, __final = [], [], []

# separate but do not break ellipsis
__initial.append((re.compile(r'\.\.\.'), r' ... '))

# To avoid breaking names of chemicals, protein complexes and similar,
# only add space to related special chars if there's already space on
# at least one side.
__initial.append((re.compile(r'([,;:@#]) '), r' \1 '))
__initial.append((re.compile(r' ([,;:@#])'), r' \1 '))

# always separated
__initial.append((re.compile(r'\$'), r' $ '))
__initial.append((re.compile(r'\%'), r' % '))
__initial.append((re.compile(r'\&'), r' & '))

# separate punctuation followed by space even if there's closing
# brackets or quotes in between, but only sentence-final for
# periods (don't break e.g. "E. coli").
__initial.append((re.compile(r'([,:;])([\[\]\)\}\>\"\']* +)'), r' \1\2'))
__initial.append((re.compile(r'(\.+)([\[\]\)\}\>\"\']* +)$'), r' \1\2'))

# these always
__initial.append((re.compile(r'\?'), ' ? '))
__initial.append((re.compile(r'\!'), ' ! '))

# separate greater than and less than signs, avoiding breaking
# "arrows" (e.g. "-->", ">>") and compound operators (e.g. "</=")
__initial.append((re.compile(r'((?:=\/)?<+(?:\/=|--+>?)?)'), r' \1 '))
__initial.append((re.compile(r'((?:<?--+|=\/)?>+(?:\/=)?)'), r' \1 '))

# separate dashes, not breaking up "arrows"
__initial.append((re.compile(r'(<?--+\>?)'), r' \1 '))

# Parens only separated when there's space around a balanced
# bracketing. This aims to avoid splitting e.g. beta-(1,3)-glucan,
# CD34(+), CD8(-)CD3(-).

# Previously had a proper recursive implementation for this, but it
# was much too slow for large-scale use. The following is
# comparatively fast but a bit of a hack:

# First "protect" token-internal brackets by replacing them with
# their PTB escapes. "Token-internal" brackets are defined as
# matching brackets of which at least one has no space on either
# side. To match GTB tokenization for cases like "interleukin
# (IL)-mediated", and "p65(RelA)/p50", treat following dashes and
# slashes as space.  Nested brackets are resolved inside-out;
# to get this right, add a heuristic considering boundary
# brackets as "space".

# (First a special case (rareish): "protect" cases with dashes after
# paranthesized expressions that cannot be abbreviations to avoid
# breaking up e.g. "(+)-pentazocine". Here, "cannot be abbreviations"
# is taken as "contains no uppercase charater".)
__initial.append((re.compile(r'\(([^ A-Z()\[\]{}]+)\)-'), r'-LRB-\1-RRB--'))

# These are repeated until there's no more change (per above comment)
__repeated.append((re.compile(r'(?<![ (\[{])\(([^ ()\[\]{}]*)\)'), r'-LRB-\1-RRB-'))
__repeated.append((re.compile(r'\(([^ ()\[\]{}]*)\)(?![ )\]}\/-])'), r'-LRB-\1-RRB-'))
__repeated.append((re.compile(r'(?<![ (\[{])\[([^ ()\[\]{}]*)\]'), r'-LSB-\1-RSB-'))
__repeated.append((re.compile(r'\[([^ ()\[\]{}]*)\](?![ )\]}\/-])'), r'-LSB-\1-RSB-'))
__repeated.append((re.compile(r'(?<![ (\[{])\{([^ ()\[\]{}]*)\}'), r'-LCB-\1-RCB-'))
__repeated.append((re.compile(r'\{([^ ()\[\]{}]*)\}(?![ )\]}\/-])'), r'-LCB-\1-RCB-'))

# Remaining brackets are not token-internal and should be
# separated.
__final.append((re.compile(r'\('), r' -LRB- '))
__final.append((re.compile(r'\)'), r' -RRB- '))
__final.append((re.compile(r'\['), r' -LSB- '))
__final.append((re.compile(r'\]'), r' -RSB- '))
__final.append((re.compile(r'\{'), r' -LCB- '))
__final.append((re.compile(r'\}'), r' -RCB- '))

# initial single quotes always separated
__final.append((re.compile(r' (\'+)'), r' \1 '))
# final with the exception of 3' and 5' (rough heuristic)
__final.append((re.compile(r'(?<![35\'])(\'+) '), r' \1 '))

# This more frequently disagreed than agreed with GTB
#     # Separate slashes preceded by space (can arise from
#     # e.g. splitting "p65(RelA)/p50"
#     __final.append((re.compile(r' \/'), r' \/ '))

# Standard from PTB (TODO: pack)
__final.append((re.compile(r'\'s '), ' \'s '))
__final.append((re.compile(r'\'S '), ' \'S '))
__final.append((re.compile(r'\'m '), ' \'m '))
__final.append((re.compile(r'\'M '), ' \'M '))
__final.append((re.compile(r'\'d '), ' \'d '))
__final.append((re.compile(r'\'D '), ' \'D '))
__final.append((re.compile(r'\'ll '), ' \'ll '))
__final.append((re.compile(r'\'re '), ' \'re '))
__final.append((re.compile(r'\'ve '), ' \'ve '))
__final.append((re.compile(r'n\'t '), ' n\'t '))
__final.append((re.compile(r'\'LL '), ' \'LL '))
__final.append((re.compile(r'\'RE '), ' \'RE '))
__final.append((re.compile(r'\'VE '), ' \'VE '))
__final.append((re.compile(r'N\'T '), ' N\'T '))

__final.append((re.compile(r' Cannot '), ' Can not '))
__final.append((re.compile(r' cannot '), ' can not '))
__final.append((re.compile(r' D\'ye '), ' D\' ye '))
__final.append((re.compile(r' d\'ye '), ' d\' ye '))
__final.append((re.compile(r' Gimme '), ' Gim me '))
__final.append((re.compile(r' gimme '), ' gim me '))
__final.append((re.compile(r' Gonna '), ' Gon na '))
__final.append((re.compile(r' gonna '), ' gon na '))
__final.append((re.compile(r' Gotta '), ' Got ta '))
__final.append((re.compile(r' gotta '), ' got ta '))
__final.append((re.compile(r' Lemme '), ' Lem me '))
__final.append((re.compile(r' lemme '), ' lem me '))
__final.append((re.compile(r' More\'n '), ' More \'n '))
__final.append((re.compile(r' more\'n '), ' more \'n '))
__final.append((re.compile(r'\'Tis '), ' \'T is '))
__final.append((re.compile(r'\'tis '), ' \'t is '))
__final.append((re.compile(r'\'Twas '), ' \'T was '))
__final.append((re.compile(r'\'twas '), ' \'t was '))
__final.append((re.compile(r' Wanna '), ' Wan na '))
__final.append((re.compile(r' wanna '), ' wan na '))

# clean up possible extra space
__final.append((re.compile(r'  +'), r' '))

def _tokenize(s):
    """
    Tokenizer core. Performs GTP-like tokenization, using PTB escapes
    for brackets (but not quotes). Assumes given string has initial
    and terminating space. You probably want to use tokenize() instead
    of this function.
    """

    # see re.complies for comments
    for r, t in __initial:
        s = r.sub(t, s)

    while True:
        o = s
        for r, t in __repeated:
            s = r.sub(t, s)
        if o == s: break

    for r, t in __final:
        s = r.sub(t, s)

    return s

def tokenize(s, ptb_escaping=False, use_single_quotes_only=False,
             escape_token_internal_parens=False):
    """
    Tokenizes the given string with a GTB-like tokenization. Input
    will adjusted by removing surrounding space, if any. Arguments
    hopefully self-explanatory.
    """

    if DEBUG_GTB_TOKENIZATION:
        orig = s

    # Core tokenization needs starting and ending space and no newline;
    # store to return string ending similarly
    # TODO: this isn't this difficult ... rewrite nicely
    s = re.sub(r'^', ' ', s)
    m = re.match(r'^((?:.+|\n)*?) *(\n*)$', s)
    assert m, "INTERNAL ERROR on '%s'" % s # should always match
    s, s_end = m.groups()    
    s = re.sub(r'$', ' ', s)

    if ptb_escaping:
        if use_single_quotes_only:
            # special case for McCCJ: escape into single quotes. 
            s = re.sub(r'([ \(\[\{\<])\"', r'\1 '+"' ", s)
        else:
            # standard PTB quote escaping
            s = re.sub(r'([ \(\[\{\<])\"', r'\1 `` ', s)
    else:
        # no escaping, just separate
        s = re.sub(r'([ \(\[\{\<])\"', r'\1 " ', s)

    s = _tokenize(s)

    # as above (not quite sure why this is after primary tokenization...)
    if ptb_escaping:
        if use_single_quotes_only:
            s = s.replace('"', " ' ")
        else:
            s = s.replace('"', " '' ")
    else:
        s = s.replace('"', ' " ')

    if not ptb_escaping:
        if not escape_token_internal_parens:
            # standard unescape for PTB escapes introduced in core
            # tokenization
            s = PTB_unescape(s)
        else:
            # only unescape if a space can be matched on both
            # sides of the bracket.
            s = re.sub(r'(?<= )-LRB-(?= )', '(', s)
            s = re.sub(r'(?<= )-RRB-(?= )', ')', s)
            s = re.sub(r'(?<= )-LSB-(?= )', '[', s)
            s = re.sub(r'(?<= )-RSB-(?= )', ']', s)
            s = re.sub(r'(?<= )-LCB-(?= )', '{', s)
            s = re.sub(r'(?<= )-RCB-(?= )', '}', s)

    # Clean up added space (well, maybe other also)
    s = re.sub(r'  +', ' ', s)
    s = re.sub(r'^ +', '', s)
    s = re.sub(r' +$', '', s)

    # Only do final comparison in debug mode.
    if DEBUG_GTB_TOKENIZATION:
        # revised must match original when whitespace, quotes (etc.)
        # and escapes are ignored
        # TODO: clean this up
        r1 = PTB_unescape(orig.replace(' ', '').replace('\n','').replace("'",'').replace('"','').replace('``',''))
        r2 = PTB_unescape(s.replace(' ', '').replace('\n','').replace("'",'').replace('"','').replace('``',''))
        if r1 != r2:
            print >> sys.stderr, "tokenize(): error: text mismatch (returning original):\nORIG: '%s'\nNEW:  '%s'" % (orig, s)
            s = orig

    return s+s_end

def __argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Perform GENIA Treebank-like text tokenization.")
    ap.add_argument("-ptb", default=False, action="store_true", help="Use Penn Treebank escapes")
    ap.add_argument("-mccc", default=False, action="store_true", help="Special processing for McClosky-Charniak-Johnson parser input")
    ap.add_argument("-sp", default=False, action="store_true", help="Special processing for Stanford parser+PTBEscapingProcessor input. (not necessary for Stanford Parser version 1.6.5 and newer)")
    ap.add_argument("files", metavar="FILE", nargs="*", help="Files to tokenize.")
    return ap


def main(argv):
    import sys
    import codecs

    arg = __argparser().parse_args(argv[1:])

    # sorry, the special cases are a bit of a mess
    ptb_escaping, use_single_quotes_only, escape_token_internal_parens = False, False, False
    if arg.ptb: 
        ptb_escaping = True
    if arg.mccc:
        ptb_escaping = True 
        # current version of McCCJ has trouble with double quotes
        use_single_quotes_only = True
    if arg.sp:
        # current version of Stanford parser PTBEscapingProcessor
        # doesn't correctly escape word-internal parentheses
        escape_token_internal_parens = True
    
    # for testing, read stdin if no args
    if len(arg.files) == 0:
        arg.files.append('/dev/stdin')

    for fn in arg.files:
        try:
            with codecs.open(fn, encoding=INPUT_ENCODING) as f:
                for l in f:
                    t = tokenize(l, ptb_escaping=ptb_escaping,
                                 use_single_quotes_only=use_single_quotes_only,
                                 escape_token_internal_parens=escape_token_internal_parens)
                    sys.stdout.write(t.encode(OUTPUT_ENCODING))
        except Exception, e:
            print >> sys.stderr, "Failed to read", fn, ":", e
            
if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = jsonwrap
'''
json wrapper to be used instead of a direct call.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-04-21
'''

# use ultrajson if set up
try:
    from sys import path as sys_path
    from os.path import join as path_join
    from os.path import dirname

    sys_path.append(path_join(dirname(__file__),
                              '../lib/ujson'))

    from ujson import dumps as _lib_dumps
    from ujson import loads as _lib_loads

    # ultrajson doesn't have encoding
    lib_dumps = _lib_dumps
    lib_loads = _lib_loads

except ImportError, e:

    # fall back to native json if available
    try:
        from json import dumps as _lib_dumps
        from json import loads as _lib_loads

    except ImportError:
        # We are on an older Python, use our included lib
        from sys import path as sys_path
        from os.path import join as path_join
        from os.path import dirname

        sys_path.append(path_join(dirname(__file__),
                                  '../lib/simplejson-2.1.5'))

        from simplejson import dumps as _lib_dumps
        from simplejson import loads as _lib_loads

    # Wrap the loads and dumps to expect utf-8
    from functools import partial
    lib_dumps = partial(_lib_dumps, encoding='utf-8')#, ensure_ascii=False)
    lib_loads = partial(_lib_loads, encoding='utf-8')#, ensure_ascii=False)

#ensure_ascii[, check_circular[, allow_nan[, cls[, indent[, separators[, encoding

def dumps(dic):
    # ultrajson has neither sort_keys nor indent
#     return lib_dumps(dic, sort_keys=True, indent=2)
    return lib_dumps(dic)

def loads(s):
    return lib_loads(s)

# TODO: Unittest that tries the import, encoding etc.

########NEW FILE########
__FILENAME__ = mecab
#!/usr/bin/env python
# -*- coding: utf-8 -*-`

'''
MeCab wrapper for brat

http://mecab.sourceforge.net/

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-05-17
'''

from os.path import dirname
from os.path import join as path_join
from re import compile as re_compile
from re import DOTALL

### Constants
# TODO: EXTERNAL_DIR_PATH really should be specified elsewhere
EXTERNAL_DIR_PATH = path_join(dirname(__file__), '..', '..', 'external')
MECAB_PYTHON_PATH = path_join(EXTERNAL_DIR_PATH, 'mecab-python-0.98')

WAKATI_REGEX = re_compile(r'(\S.*?)(?:(?:(?<!\s)\s|$))', DOTALL)
###

try:
    import MeCab as mecab
except ImportError:
    # We probably haven't added the path yet
    from sys import path as sys_path
    sys_path.append(MECAB_PYTHON_PATH)
    import MeCab as mecab

# Boundaries are on the form: [start, end]
def token_offsets_gen(text):
    # Parse in Wakati format
    tagger = mecab.Tagger('-O wakati')

    # Parse into Wakati format, MeCab only takes utf-8
    parse = tagger.parse(text.encode('utf-8'))

    # Remember to decode or you WILL get the number of bytes
    parse = parse.decode('utf-8')

    # Wakati inserts spaces, but only after non-space tokens.
    # We find these iteratively and then allow additional spaces to be treated
    # as seperate tokens.

    # XXX: MeCab rapes newlines by removing them, we need to align ourselves
    last_end = 0
    for tok in (m.group(1) for m in WAKATI_REGEX.finditer(parse)):
        start = text.find(tok, last_end)
        end = start + len(tok)
        yield [start, end]
        last_end = end

if __name__ == '__main__':
    # Minor test: Is it a duck? Maybe?
    sentence = u'鴨かも？'
    token_offsets = [t for t in token_offsets_gen(sentence)]
    segmented = [sentence[start:end + 1] for start, end in token_offsets]
    print '\t'.join((sentence, unicode(token_offsets), '|'.join(segmented)))

########NEW FILE########
__FILENAME__ = message
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Wrapper for safely importing Messager with a fallback that will
get _something_ to the user even if Messager itself breaks.
'''

try:
    from realmessage import Messager
except:
    from sosmessage import SosMessager as Messager

########NEW FILE########
__FILENAME__ = norm
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Normalization support.
'''

import normdb
import simstringdb
import sdistance
from datetime import datetime
from message import Messager

from normdb import string_norm_form
from document import real_directory
from projectconfig import ProjectConfiguration

# whether to display alignment scores in search result table
DISPLAY_SEARCH_SCORES = False

# maximum alignment score (tsuruoka_local)
MAX_SCORE = 1000

# maximum alignment score (tsuruoka_local) difference allowed between
# the score for a string s and the best known score before excluding s
# from consideration
MAX_DIFF_TO_BEST_SCORE = 200

# maximum number of search results to return
MAX_SEARCH_RESULT_NUMBER = 1000

NORM_LOOKUP_DEBUG = True

REPORT_LOOKUP_TIMINGS = False

# debugging
def _check_DB_version(database):
    # TODO; not implemented yet for new-style SQL DBs.
    pass

def _report_timings(dbname, start, msg=None):
    delta = datetime.now() - start
    strdelta = str(delta).replace('0:00:0','') # take out zero min & hour
    queries = normdb.get_query_count(dbname)
    normdb.reset_query_count(dbname)
    Messager.info("Processed " + str(queries) + " queries in " + strdelta +
                  (msg if msg is not None else ""))

def _get_db_path(database, collection):
    if collection is None:
        # TODO: default to WORK_DIR config?
        return None
    else:
        try:
            conf_dir = real_directory(collection)
            projectconf = ProjectConfiguration(conf_dir)
            norm_conf = projectconf.get_normalization_config()
            for entry in norm_conf:
                dbname, dbpath = entry[0], entry[3]
                if dbname == database:                    
                    return dbpath
            # not found in config.
            Messager.warning('DB '+database+' not defined in config for '+
                             collection+', falling back on default.')
            return None
        except Exception:
            # whatever goes wrong, just warn and fall back on the default.
            Messager.warning('Failed to get DB path from config for '+
                             collection+', falling back on default.')
            return None

def norm_get_name(database, key, collection=None):
    if NORM_LOOKUP_DEBUG:
        _check_DB_version(database)
    if REPORT_LOOKUP_TIMINGS:
        lookup_start = datetime.now()

    dbpath = _get_db_path(database, collection)
    if dbpath is None:
        # full path not configured, fall back on name as default
        dbpath = database

    try:
        data = normdb.data_by_id(dbpath, key)
    except normdb.dbNotFoundError, e:
        Messager.warning(str(e))
        data = None

    # just grab the first one (sorry, this is a bit opaque)
    if data is not None:
        value = data[0][0][1]
    else:
        value = None

    if REPORT_LOOKUP_TIMINGS:
        _report_timings(database, lookup_start)

    # echo request for sync
    json_dic = {
        'database' : database,
        'key' : key,
        'value' : value
        }
    return json_dic

def norm_get_data(database, key, collection=None):
    if NORM_LOOKUP_DEBUG:
        _check_DB_version(database)
    if REPORT_LOOKUP_TIMINGS:
        lookup_start = datetime.now()

    dbpath = _get_db_path(database, collection)
    if dbpath is None:
        # full path not configured, fall back on name as default
        dbpath = database

    try:
        data = normdb.data_by_id(dbpath, key)
    except normdb.dbNotFoundError, e:
        Messager.warning(str(e))
        data = None

    if data is None:
        Messager.warning("Failed to get data for " + database + ":" + key)

    if REPORT_LOOKUP_TIMINGS:
        _report_timings(database, lookup_start)

    # echo request for sync
    json_dic = {
        'database' : database,
        'key' : key,
        'value' : data
        }
    return json_dic    

# TODO: deprecated, confirm unnecessary and remove.
# def norm_get_ids(database, name, collection=None):
#     if NORM_LOOKUP_DEBUG:
#         _check_DB_version(database)
#     if REPORT_LOOKUP_TIMINGS:
#         lookup_start = datetime.now()
#
#     dbpath = _get_db_path(database, collection)
#     if dbpath is None:
#         # full path not configured, fall back on name as default
#         dbpath = database
#
#     keys = normdb.ids_by_name(dbpath, name)
#
#     if REPORT_LOOKUP_TIMINGS:
#         _report_timings(database, lookup_start)
#
#     # echo request for sync
#     json_dic = {
#         'database' : database,
#         'value' : name,
#         'keys' : keys,
#         }
#     return json_dic

def _format_datas(datas, scores=None, matched=None):
    # helper for norm_search(), formats data from DB into a table
    # for client, sort by scores if given.

    if scores is None:
        scores = {}
    if matched is None:
        matched = {}

    # chop off all but the first two groups of label:value pairs for
    # each key; latter ones are assumed to be additional information
    # not intended for display of search results. 
    # TODO: avoid the unnecessary queries for this information.
    cropped = {}
    for key in datas:
        cropped[key] = datas[key][:2]
    datas = cropped

    # organize into a table format with separate header and data
    # (this matches the collection browser data format)
    unique_labels = []
    seen_label = {}
    for key in datas:
        # check for dups within each entry
        seen_label_for_key = {}
        for i, group in enumerate(datas[key]):
            for label, value in group:
                if label not in seen_label:
                    # store with group index to sort all labels by
                    # group idx first
                    unique_labels.append((i, label))
                seen_label[label] = True
                if label in seen_label_for_key:
                    # too noisy, and not really harmful now that matching
                    # values are preferred for repeated labels.
#                     Messager.warning("Repeated label (%s) in normalization data not supported" % label)
                    pass
                seen_label_for_key[label] = True

    # sort unique labels by group index (should be otherwise stable,
    # holds since python 2.3), and flatten
    unique_labels.sort(lambda a,b: cmp(a[0],b[0]))
    unique_labels = [a[1] for a in unique_labels]

    # ID is first field, and datatype is "string" for all labels
    header = [(label, "string") for label in ["ID"] + unique_labels]

    if DISPLAY_SEARCH_SCORES:
        header += [("score", "int")]

    # construct items, sorted by score first, ID second (latter for stability)
    sorted_keys = sorted(datas.keys(), lambda a,b: cmp((scores.get(b,0),b),
                                                       (scores.get(a,0),a)))

    items = []
    for key in sorted_keys:
        # make dict for lookup. In case of duplicates (e.g. multiple
        # "synonym" entries), prefer ones that were matched.
        # TODO: prefer more exact matches when multiple found.
        data_dict = {}
        for group in datas[key]:
            for label, value in group:
                if label not in data_dict or (value in matched and
                                              data_dict[label] not in matched):
                    data_dict[label] = value
        # construct item
        item = [str(key)]
        for label in unique_labels:
            if label in data_dict:
                item.append(data_dict[label])
            else:
                item.append('')
        
        if DISPLAY_SEARCH_SCORES:
            item += [str(scores.get(key))]

        items.append(item)

    return header, items

def _norm_filter_score(score, best_score=MAX_SCORE):
    return score < best_score - MAX_DIFF_TO_BEST_SCORE

# TODO: get rid of arbitrary max_cost default constant
def _norm_score(substring, name, max_cost=500):
    # returns an integer score representing the similarity of the given
    # substring to the given name (larger is better).
    cache = _norm_score.__cache
    if (substring, name) not in cache:
        cost = sdistance.tsuruoka_local(substring, name, max_cost=max_cost)
        # debugging
        #Messager.info('%s --- %s: %d (max %d)' % (substring, name, cost, max_cost))
        score = MAX_SCORE - cost
        cache[(substring, name)] = score
    # TODO: should we avoid exceeding max_cost? Cached values might.
    return cache[(substring, name)]
_norm_score.__cache = {}

def _norm_search_name_attr(database, name, attr,
                           matched, score_by_id, score_by_str,
                           best_score=0, exactmatch=False,
                           threshold=simstringdb.DEFAULT_THRESHOLD):
    # helper for norm_search, searches for matches where given name
    # appears either in full or as an approximate substring of a full
    # name (if exactmatch is False) in given DB. If attr is not None,
    # requires its value to appear as an attribute of the entry with
    # the matched name. Updates matched, score_by_id, and
    # score_by_str, returns best_score.

    # If there are no strict substring matches for a given attribute
    # in the simstring DB, we can be sure that no query can succeed,
    # and can fail early.
    # TODO: this would be more effective (as would some other things)
    # if the attributes were in a separate simstring DB from the
    # names.
    if attr is not None:
        utfattr = attr.encode('UTF-8')
        normattr = string_norm_form(utfattr)
        if not simstringdb.ssdb_supstring_exists(normattr, database, 1.0):
            # debugging
            #Messager.info('Early norm search fail on "%s"' % attr)
            return best_score

    if exactmatch:
        # only candidate string is given name
        strs = [name]
        ss_norm_score = { string_norm_form(name): 1.0 }
    else:
        # expand to substrings using simstring
        # simstring requires UTF-8
        utfname = name.encode('UTF-8')
        normname = string_norm_form(utfname)
        str_scores = simstringdb.ssdb_supstring_lookup(normname, database,
                                                       threshold, True)
        strs = [s[0] for s in str_scores]
        ss_norm_score = dict(str_scores)

        # TODO: recreate this older filter; watch out for which name to use!
#         # filter to strings not already considered
#         strs = [s for s in strs if (normname, s) not in score_by_str]

    # look up IDs
    if attr is None:
        id_names = normdb.ids_by_names(database, strs, False, True)
    else:
        id_names = normdb.ids_by_names_attr(database, strs, attr, False, True)

    # sort by simstring (n-gram overlap) score to prioritize likely
    # good hits.
    # TODO: this doesn't seem to be having a very significant effect.
    # consider removing as unnecessary complication (ss_norm_score also).
    id_name_scores = [(i, n, ss_norm_score[string_norm_form(n)]) 
                      for i, n in id_names]
    id_name_scores.sort(lambda a,b: cmp(b[2],a[2]))
    id_names = [(i, n) for i, n, s in id_name_scores]

    # update matches and scores
    for i, n in id_names:
        if n not in matched:
            matched[n] = set()
        matched[n].add(i)

        max_cost = MAX_SCORE - best_score + MAX_DIFF_TO_BEST_SCORE + 1
        if (name, n) not in score_by_str:
            # TODO: decide whether to use normalized or unnormalized strings
            # for scoring here.
            #score_by_str[(name, n)] = _norm_score(name, n, max_cost)
            score_by_str[(name, n)] = _norm_score(string_norm_form(name), string_norm_form(n), max_cost)
        score = score_by_str[(name, n)]
        best_score = max(score, best_score)

        score_by_id[i] = max(score_by_id.get(i, -1),
                             score_by_str[(name, n)])

        # stop if max count reached
        if len(score_by_id) > MAX_SEARCH_RESULT_NUMBER:
            Messager.info('Note: more than %d search results, only retrieving top matches' % MAX_SEARCH_RESULT_NUMBER)
            break

    return best_score

def _norm_search_impl(database, name, collection=None, exactmatch=False):
    if NORM_LOOKUP_DEBUG:
        _check_DB_version(database)
    if REPORT_LOOKUP_TIMINGS:
        lookup_start = datetime.now()

    dbpath = _get_db_path(database, collection)
    if dbpath is None:
        # full path not configured, fall back on name as default
        dbpath = database

    # maintain map from searched names to matching IDs and scores for
    # ranking
    matched = {}
    score_by_id = {}
    score_by_str = {}

    # look up hits where name appears in full
    best_score = _norm_search_name_attr(dbpath, name, None,
                                        matched, score_by_id, score_by_str,
                                        0, exactmatch)

    # if there are no hits and we only have a simple candidate string,
    # look up with a low threshold
    if best_score == 0 and len(name.split()) == 1:
        best_score = _norm_search_name_attr(dbpath, name, None,
                                            matched, score_by_id, score_by_str,
                                            0, exactmatch, 0.5)

    # if there are no good hits, also consider only part of the input
    # as name and the rest as an attribute.
    # TODO: reconsider arbitrary cutoff
    if best_score < 900 and not exactmatch:
        parts = name.split()        

        # prioritize having the attribute after the name
        for i in range(len(parts)-1, 0, -1):
            # TODO: this early termination is sub-optimal: it's not
            # possible to know in advance which way of splitting the
            # query into parts yields best results. Reconsider.
            if len(score_by_id) > MAX_SEARCH_RESULT_NUMBER:
                break

            start = ' '.join(parts[:i])
            end   = ' '.join(parts[i:])            

            # query both ways (start is name, end is attr and vice versa)
            best_score = _norm_search_name_attr(dbpath, start, end,
                                                matched, score_by_id, 
                                                score_by_str,
                                                best_score, exactmatch)
            best_score = _norm_search_name_attr(dbpath, end, start,
                                                matched, score_by_id, 
                                                score_by_str,
                                                best_score, exactmatch)

    # flatten to single set of IDs
    ids = reduce(set.union, matched.values(), set())

    # filter ids that now (after all queries complete) fail
    # TODO: are we sure that this is a good idea?
    ids = set([i for i in ids 
               if not _norm_filter_score(score_by_id[i], best_score)])

    # TODO: avoid unnecessary queries: datas_by_ids queries for names,
    # attributes and infos, but _format_datas only uses the first two.
    datas = normdb.datas_by_ids(dbpath, ids)
    
    header, items = _format_datas(datas, score_by_id, matched)

    if REPORT_LOOKUP_TIMINGS:
        _report_timings(database, lookup_start, 
                        ", retrieved " + str(len(items)) + " items")
                        
    # echo request for sync
    json_dic = {
        'database' : database,
        'query'    : name,
        'header'   : header,
        'items'    : items,
        }
    return json_dic

def norm_search(database, name, collection=None, exactmatch=False):
    try:
        return _norm_search_impl(database, name, collection, exactmatch)
    except simstringdb.ssdbNotFoundError, e:
        Messager.warning(str(e))
        return { 
            'database' : database,
            'query' : name,
            'header' : [],
            'items' : []
            }

def _test():
    # test
    test_cases = {
        'UniProt' : {
            'Runx3' : 'Q64131',
            'Runx3 mouse' : 'Q64131',
            'Runx1' : 'Q03347',
            'Runx1 mouse' : 'Q03347',
            'Eomes' : 'O54839',
            'Eomes mouse' : 'O54839',
            'granzyme B' : 'P04187',
            'granzyme B mouse' : 'P04187',
            'INF-gamma' : 'P01580',
            'INF-gamma mouse' : 'P01580',
            'IL-2' : 'P04351',
            'IL-2 mouse' : 'P04351',
            'T-bet' : 'Q9JKD8',
            'T-bet mouse' : 'Q9JKD8',
            'GATA-1' : 'P15976',
            'GATA-1 human' : 'P15976',
            'Interleukin-10' : 'P22301',
            'Interleukin-10 human' : 'P22301',
            'Interleukin-12' : 'P29459',
            'Interleukin-12 human' : 'P29459',
            'interferon-gamma' : 'P01579',
            'interferon-gamma human' : 'P01579',
            'interferon gamma human' : 'P01579',
            'Fas ligand' : 'P48023',
            'Fas ligand human' : 'P48023',
            'IkappaB-alpha' : 'P25963',
            'IkappaB-alpha human' : 'P25963',
            'transforming growth factor (TGF)-beta1' : 'P01137',
            'transforming growth factor (TGF)-beta1 human' : 'P01137',
            'transforming growth factor beta1 human' : 'P01137',
            'tumor necrosis factor alpha' : 'P01375',
            'tumor necrosis factor alpha human' : 'P01375',
            'Epstein-Barr virus latent membrane protein LMP1' : 'Q1HVB3',
            'TATA box binding protein' : 'P20226',
            'TATA box binding protein human' : 'P20226',
            'HIV protease' : '??????', # TODO
            'human immunodeficiency virus type 1 (HIV) protease' : '??????', # TODO
            }
        }

    overall_start = datetime.now()
    query_count, hit_count = 0, 0
    misses = []
    for DB in test_cases:
        for query in test_cases[DB]:
            target = test_cases[DB][query]
            start = datetime.now()
            results = norm_search(DB, query)
            delta = datetime.now() - start
            found = False
            found_rank = -1
            for rank, item in enumerate(results['items']):
                id_ = item[0]
                if id_ == target:
                    found = True
                    found_rank = rank+1
                    break
            strdelta = str(delta).replace('0:00:0','').replace('0:00:','')
            print "%s: '%s' <- '%s' rank %d/%d (%s sec)" % ('  ok' if found 
                                                            else 'MISS',
                                                            target, query, 
                                                            found_rank,
                                                            len(results['items']),
                                                            strdelta)
            query_count += 1
            if found:
                hit_count += 1
            else:
                misses.append((query, target))

    if len(misses) != 0:
        print
        print "MISSED:"
        for query, target in misses:
            print "%s '%s'" % (target, query)

    delta = datetime.now() - overall_start
    strdelta = str(delta).replace('0:00:0','').replace('0:00:','')
    print
    print "Found %d / %d in %s" % (hit_count, query_count, strdelta)

def _profile_test():
    # runs _test() with profiling, storing results in "norm.profile".
    # To see a profile, run e.g.
    # python -c 'import pstats; pstats.Stats("norm.profile").strip_dirs().sort_stats("time").print_stats()' | less
    import cProfile
    import os.path
    cProfile.run('_test()', 'norm.profile')

if __name__ == '__main__':
    _test() # normal
    #_profile_test() # profiled

########NEW FILE########
__FILENAME__ = normdb
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Functionality for normalization SQL database access.
'''

import sys
from os.path import join as path_join, exists, sep as path_sep
import sqlite3 as sqlite

try:
    from config import BASE_DIR, WORK_DIR
except ImportError:
    # for CLI use; assume we're in brat server/src/ and config is in root
    from sys import path as sys_path
    from os.path import dirname
    sys_path.append(path_join(dirname(__file__), '../..'))
    from config import BASE_DIR, WORK_DIR

# Filename extension used for DB file.
DB_FILENAME_EXTENSION = 'db'

# Names of tables with information on each entry
TYPE_TABLES = ["names", "attributes", "infos"]

# Names of tables that must have some value for an entry
NON_EMPTY_TABLES = set(["names"])

# Maximum number of variables in one SQL query (TODO: get from lib!)
MAX_SQL_VARIABLE_COUNT = 999

__query_count = {}

class dbNotFoundError(Exception):
    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        return u'Database file "%s" not found' % self.fn

# Normalizes a given string for search. Used to implement
# case-insensitivity and similar in search.
# NOTE: this is a different sense of "normalization" than that
# implemented by a normalization DB as a whole: this just applies to
# single strings.
# NOTE2: it is critically important that this function is performed
# identically during DB initialization and actual lookup.
# TODO: enforce a single implementation.
def string_norm_form(s):
    return s.lower().strip().replace('-', ' ')

def __db_path(db):
    '''
    Given a DB name/path, returns the path for the file that is
    expected to contain the DB.
    '''
    # Assume we have a path relative to the brat root if the value
    # contains a separator, name only otherwise. 
    # TODO: better treatment of name / path ambiguity, this doesn't
    # allow e.g. DBs to be located in brat root
    if path_sep in db:
        base = BASE_DIR
    else:
        base = WORK_DIR
    return path_join(base, db+'.'+DB_FILENAME_EXTENSION)

def reset_query_count(dbname):
    global __query_count
    __query_count[dbname] = 0

def get_query_count(dbname):
    global __query_count
    return __query_count.get(dbname, 0)

def __increment_query_count(dbname):
    global __query_count
    __query_count[dbname] = __query_count.get(dbname, 0) + 1

def _get_connection_cursor(dbname):
    # helper for DB access functions
    dbfn = __db_path(dbname)

    # open DB
    if not exists(dbfn):
        raise dbNotFoundError(dbfn)
    connection = sqlite.connect(dbfn)
    cursor = connection.cursor()

    return connection, cursor

def _execute_fetchall(cursor, command, args, dbname):
    # helper for DB access functions
    cursor.execute(command, args)
    __increment_query_count(dbname)
    return cursor.fetchall()

def data_by_id(dbname, id_):
    '''
    Given a DB name and an entity id, returns all the information
    contained in the DB for the id.
    '''
    connection, cursor = _get_connection_cursor(dbname)

    # select separately from names, attributes and infos    
    responses = {}
    for table in TYPE_TABLES:
        command = '''
SELECT L.text, N.value
FROM entities E
JOIN %s N
  ON E.id = N.entity_id
JOIN labels L
  ON L.id = N.label_id
WHERE E.uid=?''' % table
        responses[table] = _execute_fetchall(cursor, command, (id_, ), dbname)

        # short-circuit on missing or incomplete entry
        if table in NON_EMPTY_TABLES and len(responses[table]) == 0:
            break

    cursor.close()

    # empty or incomplete?
    for t in NON_EMPTY_TABLES:
        if len(responses[t]) == 0:
            return None

    # has content, format and return
    combined = []
    for t in TYPE_TABLES:
        combined.append(responses[t])
    return combined

def ids_by_name(dbname, name, exactmatch=False, return_match=False):
    return ids_by_names(dbname, [name], exactmatch, return_match)

def ids_by_names(dbname, names, exactmatch=False, return_match=False):
    if len(names) < MAX_SQL_VARIABLE_COUNT:
        return _ids_by_names(dbname, names, exactmatch, return_match)
    else:
        # break up into several queries
        result = []
        i = 0
        while i < len(names):
            n = names[i:i+MAX_SQL_VARIABLE_COUNT]
            r = _ids_by_names(dbname, n, exactmatch, return_match)
            result.extend(r)
            i += MAX_SQL_VARIABLE_COUNT
        return result

def _ids_by_names(dbname, names, exactmatch=False, return_match=False):
    '''
    Given a DB name and a list of entity names, returns the ids of all
    entities having one of the given names. Uses exact string lookup
    if exactmatch is True, otherwise performs normalized string lookup
    (case-insensitive etc.). If return_match is True, returns pairs of
    (id, matched name), otherwise returns only ids.
    '''
    connection, cursor = _get_connection_cursor(dbname)

    if not return_match:
        command = 'SELECT E.uid'
    else:
        command = 'SELECT E.uid, N.value'

    command += '''
FROM entities E
JOIN names N
  ON E.id = N.entity_id
'''
    if exactmatch:
        command += 'WHERE N.value IN (%s)' % ','.join(['?' for n in names])
    else:
        command += 'WHERE N.normvalue IN (%s)' % ','.join(['?' for n in names])
        names = [string_norm_form(n) for n in names]

    responses = _execute_fetchall(cursor, command, names, dbname)

    cursor.close()

    if not return_match:
        return [r[0] for r in responses]
    else:
        return [(r[0],r[1]) for r in responses]

def ids_by_name_attr(dbname, name, attr, exactmatch=False, return_match=False):
    return ids_by_names_attr(dbname, [name], attr, exactmatch, return_match)

def ids_by_names_attr(dbname, names, attr, exactmatch=False, 
                      return_match=False):
    if len(names) < MAX_SQL_VARIABLE_COUNT-1:
        return _ids_by_names_attr(dbname, names, attr, exactmatch, return_match)
    else:
        # break up
        result = []
        i = 0
        while i < len(names):
            # -1 for attr
            n = names[i:i+MAX_SQL_VARIABLE_COUNT-1]
            r = _ids_by_names_attr(dbname, n, attr, exactmatch, return_match)
            result.extend(r)
            i += MAX_SQL_VARIABLE_COUNT-1
        return result
            
def _ids_by_names_attr(dbname, names, attr, exactmatch=False, 
                       return_match=False):
    '''
    Given a DB name, a list of entity names, and an attribute text,
    returns the ids of all entities having one of the given names and
    an attribute matching the given attribute. Uses exact string
    lookup if exactmatch is True, otherwise performs normalized string
    lookup (case-insensitive etc.). If return_match is True, returns
    pairs of (id, matched name), otherwise returns only names.
    '''
    connection, cursor = _get_connection_cursor(dbname)

    if not return_match:
        command = 'SELECT E.uid'
    else:
        command = 'SELECT E.uid, N.value'

    command += '''
FROM entities E
JOIN names N
  ON E.id = N.entity_id
JOIN attributes A
  ON E.id = A.entity_id
'''
    if exactmatch:
        command += 'WHERE N.value IN (%s) AND A.value=?' % ','.join(['?' for n in names])
    else:
        # NOTE: using 'LIKE', not '=' here
        command += 'WHERE N.normvalue IN (%s) AND A.normvalue LIKE ?' % ','.join(['?' for n in names])
        attr = '%'+string_norm_form(attr)+'%'
        names = [string_norm_form(n) for n in names]

    responses = _execute_fetchall(cursor, command, names + [attr], dbname)

    cursor.close()

    if not return_match:
        return [r[0] for r in responses]
    else:
        return [(r[0],r[1]) for r in responses]

def datas_by_ids(dbname, ids):
    if len(ids) < MAX_SQL_VARIABLE_COUNT:
        return _datas_by_ids(dbname, ids)
    else:
        # break up
        datas = {}
        i = 0
        ids = list(ids)
        while i < len(ids):
            ids_ = ids[i:i+MAX_SQL_VARIABLE_COUNT]
            r = _datas_by_ids(dbname, ids_)
            for k in r:
                datas[k] = r[k]
            i += MAX_SQL_VARIABLE_COUNT
        return datas

def _datas_by_ids(dbname, ids):
    '''
    Given a DB name and a list of entity ids, returns all the
    information contained in the DB for the ids.
    '''
    connection, cursor = _get_connection_cursor(dbname)

    # select separately from names, attributes and infos    
    responses = {}
    for table in TYPE_TABLES:
        command = '''
SELECT E.uid, L.text, N.value
FROM entities E
JOIN %s N
  ON E.id = N.entity_id
JOIN labels L
  ON L.id = N.label_id
WHERE E.uid IN (%s)''' % (table, ','.join(['?' for i in ids]))
        response = _execute_fetchall(cursor, command, list(ids), dbname)

        # group by ID first
        for id_, label, value in response:
            if id_ not in responses:
                responses[id_] = {}
            if table not in responses[id_]:
                responses[id_][table] = []
            responses[id_][table].append([label, value])

        # short-circuit on missing or incomplete entry
        if (table in NON_EMPTY_TABLES and
            len([i for i in responses if responses[i][table] == 0]) != 0):
            return None

    cursor.close()

    # empty or incomplete?
    for id_ in responses:
        for t in NON_EMPTY_TABLES:
            if len(responses[id_][t]) == 0:
                return None

    # has expected content, format and return
    datas = {}
    for id_ in responses:
        datas[id_] = []
        for t in TYPE_TABLES:
            datas[id_].append(responses[id_].get(t,[]))
    return datas

def datas_by_name(dbname, name, exactmatch=False):
    # TODO: optimize
    datas = {}
    for id_ in ids_by_name(dbname, name, exactmatch):
        datas[id_] = data_by_id(dbname, id_)
    return datas

if __name__ == "__main__":
    # test
    if len(sys.argv) > 1:
        dbname = sys.argv[1]
    else:
        dbname = "FMA"
    if len(sys.argv) > 2:
        id_ = sys.argv[2]
    else:
        id_ = "10883"
    print data_by_id(dbname, id_)
    print ids_by_name(dbname, 'Pleural branch of left sixth posterior intercostal artery')
    print datas_by_name(dbname, 'Pleural branch of left sixth posterior intercostal artery')

########NEW FILE########
__FILENAME__ = predict
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Prediction for annotation types.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Author:     Sampo Pyysalo       <smp is s u-tokyo ac jp>
Version:    2011-11-17
'''

### Constants
CUT_OFF = 0.95
# In seconds
QUERY_TIMEOUT = 30
###

from urllib import urlencode, quote_plus
from urllib2 import urlopen, HTTPError, URLError

from annlog import log_annotation
from document import real_directory
from common import ProtocolError
from jsonwrap import loads
from projectconfig import ProjectConfiguration

# TODO: Reduce the SimSem coupling

class SimSemConnectionNotConfiguredError(ProtocolError):
    def __str__(self):
        return ('The SimSem connection has not been configured, '
                'please contact the administrator')

    def json(self, json_dic):
        json_dic['exception'] = 'simSemConnectionNotConfiguredError'


class SimSemConnectionError(ProtocolError):
    def __str__(self):
        return ('The SimSem connection returned an error or timed out, '
                'please contact the administrator')

    def json(self, json_dic):
        json_dic['exception'] = 'simSemConnectionError'


class UnknownModelError(ProtocolError):
    def __str__(self):
        return ('The client provided model not mentioned in `tools.conf`')

    def json(self, json_dic):
        json_dic['exception'] = 'unknownModelError'


def suggest_span_types(collection, document, start, end, text, model):

    pconf = ProjectConfiguration(real_directory(collection))
    for _, _, model_str, model_url in pconf.get_disambiguator_config():
        if model_str == model:
            break
    else:
        # We were unable to find a matching model
        raise SimSemConnectionNotConfiguredError

    try:
        quoted_text = quote_plus(text)
        resp = urlopen(model_url % quoted_text, None, QUERY_TIMEOUT)
    except URLError:
        # TODO: Could give more details
        raise SimSemConnectionError
    
    json = loads(resp.read())

    preds = json['result'][text.decode('utf-8')]

    selected_preds = []
    conf_sum = 0
    for cat, conf in preds:
        selected_preds.append((cat, conf, ))
        conf_sum += conf
        if conf_sum >= CUT_OFF:
            break

    log_annotation(collection, document, 'DONE', 'suggestion',
            [None, None, text, ] + [selected_preds, ])

    # array so that server can control presentation order in UI
    # independently from scores if needed
    return { 'types': selected_preds,
             'collection': collection, # echo for reference
             'document': document,
             'start': start,
             'end': end,
             'text': text,
             }

if __name__ == '__main__':
    from config import DATA_DIR
    print suggest_span_types(DATA_DIR, 'dummy', -1, -1, 'proposición', 'ner_spanish')

########NEW FILE########
__FILENAME__ = projectconfig
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:


'''
Per-project configuration functionality for
Brat Rapid Annotation Tool (brat)

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Author:     Sampo Pyysalo       <smp is s u-tokyo ac jp>
Author:     Illes Solt          <solt tmit bme hu>
Version:    2011-08-15
'''

import re
import robotparser # TODO reduce scope
import urlparse # TODO reduce scope
import sys

from annotation import open_textfile
from message import Messager

ENTITY_CATEGORY, EVENT_CATEGORY, RELATION_CATEGORY, UNKNOWN_CATEGORY = xrange(4)

class InvalidProjectConfigException(Exception):
    pass

# names of files in which various configs are found
__access_control_filename     = 'acl.conf'
__annotation_config_filename  = 'annotation.conf'
__visual_config_filename      = 'visual.conf'
__tools_config_filename       = 'tools.conf'
__kb_shortcut_filename        = 'kb_shortcuts.conf'

# annotation config section name constants
ENTITY_SECTION    = "entities"
RELATION_SECTION  = "relations"
EVENT_SECTION     = "events"
ATTRIBUTE_SECTION = "attributes"

# aliases for config section names
SECTION_ALIAS = {
    "spans" : ENTITY_SECTION,
}

__expected_annotation_sections = (ENTITY_SECTION, RELATION_SECTION, EVENT_SECTION, ATTRIBUTE_SECTION)
__optional_annotation_sections = []

# visual config section name constants
OPTIONS_SECTION    = "options"
LABEL_SECTION     = "labels"
DRAWING_SECTION   = "drawing"

__expected_visual_sections = (OPTIONS_SECTION, LABEL_SECTION, DRAWING_SECTION)
__optional_visual_sections = [OPTIONS_SECTION]

# tools config section name constants
SEARCH_SECTION     = "search"
ANNOTATORS_SECTION = "annotators"
DISAMBIGUATORS_SECTION = "disambiguators"
NORMALIZATION_SECTION = "normalization"

__expected_tools_sections = (OPTIONS_SECTION, SEARCH_SECTION, ANNOTATORS_SECTION, DISAMBIGUATORS_SECTION, NORMALIZATION_SECTION)
__optional_tools_sections = (OPTIONS_SECTION, SEARCH_SECTION, ANNOTATORS_SECTION, DISAMBIGUATORS_SECTION, NORMALIZATION_SECTION)

# special relation types for marking which spans can overlap
# ENTITY_NESTING_TYPE used up to version 1.3, now deprecated
ENTITY_NESTING_TYPE = "ENTITY-NESTING"
# TEXTBOUND_OVERLAP_TYPE used from version 1.3 onward
TEXTBOUND_OVERLAP_TYPE = "<OVERLAP>"
SPECIAL_RELATION_TYPES = set([ENTITY_NESTING_TYPE,
                              TEXTBOUND_OVERLAP_TYPE])
OVERLAP_TYPE_ARG = '<OVL-TYPE>'

# visual config default value names
VISUAL_SPAN_DEFAULT = "SPAN_DEFAULT"
VISUAL_ARC_DEFAULT  = "ARC_DEFAULT"
VISUAL_ATTR_DEFAULT = "ATTRIBUTE_DEFAULT"

# visual config attribute name lists
SPAN_DRAWING_ATTRIBUTES = ['fgColor', 'bgColor', 'borderColor']
ARC_DRAWING_ATTRIBUTES  = ['color', 'dashArray', 'arrowHead', 'labelArrow']
ATTR_DRAWING_ATTRIBUTES  = ['glyphColor', 'box', 'dashArray', 'glyph', 'position']

# fallback defaults if config files not found
__default_configuration = """
[entities]
Protein

[relations]
Equiv	Arg1:Protein, Arg2:Protein, <REL-TYPE>:symmetric-transitive

[events]
Protein_binding|GO:0005515	Theme+:Protein
Gene_expression|GO:0010467	Theme:Protein

[attributes]
Negation	Arg:<EVENT>
Speculation	Arg:<EVENT>
"""

__default_visual = """
[labels]
Protein | Protein | Pro | P
Protein_binding | Protein binding | Binding | Bind
Gene_expression | Gene expression | Expression | Exp
Theme | Theme | Th

[drawing]
Protein	bgColor:#7fa2ff
SPAN_DEFAULT	fgColor:black, bgColor:lightgreen, borderColor:black
ARC_DEFAULT	color:black
ATTRIBUTE_DEFAULT	glyph:*
"""

__default_tools = """
[search]
google     <URL>:http://www.google.com/search?q=%s
"""

__default_kb_shortcuts = """
P	Protein
"""

__default_access_control = """
User-agent: *
Allow: /
Disallow: /hidden/

User-agent: guest
Disallow: /confidential/
"""

# Reserved strings with special meanings in configuration.
reserved_config_name   = ["ANY", "ENTITY", "RELATION", "EVENT", "NONE", "EMPTY", "REL-TYPE", "URL", "URLBASE", "GLYPH-POS", "DEFAULT", "NORM", "OVERLAP", "OVL-TYPE", "INHERIT"]
# TODO: "GLYPH-POS" is no longer used, warn if encountered and
# recommend to use "position" instead.
reserved_config_string = ["<%s>" % n for n in reserved_config_name]

# Magic string to use to represent a separator in a config
SEPARATOR_STR = "SEPARATOR"

def normalize_to_storage_form(t):
    """
    Given a label, returns a form of the term that can be used for
    disk storage. For example, space can be replaced with underscores
    to allow use with space-separated formats.
    """
    if t not in normalize_to_storage_form.__cache:
        # conservative implementation: replace any space with
        # underscore, replace unicode accented characters with
        # non-accented equivalents, remove others, and finally replace
        # all characters not in [a-zA-Z0-9_-] with underscores.

        import re
        import unicodedata

        n = t.replace(" ", "_")
        if isinstance(n, unicode):
            ascii = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore')
        n  = re.sub(r'[^a-zA-Z0-9_-]', '_', n)

        normalize_to_storage_form.__cache[t] = n

    return normalize_to_storage_form.__cache[t]
normalize_to_storage_form.__cache = {}

class TypeHierarchyNode:
    """
    Represents a node in a simple (possibly flat) hierarchy. 

    Each node is associated with a set of terms, one of which (the
    storage_form) matches the way in which the type denoted by the
    node is referenced to in data stored on disk and in client-server
    communications. This term is guaranteed to be in "storage form" as
    defined by normalize_to_storage_form().

    Each node may be associated with one or more "arguments", which
    are (multivalued) key:value pairs. These determine various characteristics 
    of the node, but their interpretation depends on the hierarchy the
    node occupies: for example, for events the arguments correspond to
    event arguments.
    """
    def __init__(self, terms, args=[]):
        self.terms, self.args = terms, args

        if len(terms) == 0 or len([t for t in terms if t == ""]) != 0:
            Messager.debug("Empty term in configuration", duration=-1)
            raise InvalidProjectConfigException

        # unused if any of the terms marked with "!"
        self.unused = False
        for i in range(len(self.terms)):
            if self.terms[i][0] == "!":
                self.terms[i]= self.terms[i][1:]
                self.unused = True
        self.children = []

        # The first of the listed terms is used as the primary term for
        # storage (excepting for "special" config-only types). Due to
        # format restrictions, this form must not have e.g. space or
        # various special characters.
        if self.terms[0] not in SPECIAL_RELATION_TYPES:
            self.__primary_term = normalize_to_storage_form(self.terms[0])
        else:
            self.__primary_term = self.terms[0]
        # TODO: this might not be the ideal place to put this warning
        if self.__primary_term != self.terms[0]:
            Messager.warning("Note: in configuration, term '%s' is not appropriate for storage (should match '^[a-zA-Z0-9_-]*$'), using '%s' instead. (Revise configuration file to get rid of this message. Terms other than the first are not subject to this restriction.)" % (self.terms[0], self.__primary_term), -1)
            self.terms[0] = self.__primary_term

        # TODO: cleaner and more localized parsing
        self.arguments = {}
        self.special_arguments = {}
        self.arg_list = []
        self.arg_min_count = {}
        self.arg_max_count = {}
        self.keys_by_type = {}
        for a in self.args:
            a = a.strip()
            m = re.match(r'^(\S*?):(\S*)$', a)
            if not m:
                Messager.warning("Project configuration: Failed to parse argument '%s' (args: %s)" % (a, args), 5)
                raise InvalidProjectConfigException
            key, atypes = m.groups()

            # special case (sorry): if the key is a reserved config
            # string (e.g. "<REL-TYPE>" or "<URL>"), parse differently
            # and store separately
            if key in reserved_config_string:
                if key is self.special_arguments:
                    Messager.warning("Project configuration: error parsing: %s argument '%s' appears multiple times." % key, 5)
                    raise InvalidProjectConfigException
                # special case in special case: relation type specifications
                # are split by hyphens, nothing else is.
                # (really sorry about this.)
                if key == "<REL-TYPE>":
                    self.special_arguments[key] = atypes.split("-")
                else:
                    self.special_arguments[key] = [atypes]
                # NOTE: skip the rest of processing -- don't add in normal args
                continue

            # Parse "repetition" modifiers. These are regex-like:
            # - Arg      : mandatory argument, exactly one
            # - Arg?     : optional argument, at most one
            # - Arg*     : optional argument, any number
            # - Arg+     : mandatory argument, one or more
            # - Arg{N}   : mandatory, exactly N
            # - Arg{N-M} : mandatory, between N and M

            m = re.match(r'^(\S+?)(\{\S+\}|\?|\*|\+|)$', key)
            if not m:
                Messager.warning("Project configuration: error parsing argument '%s'." % key, 5)
                raise InvalidProjectConfigException
            key, rep = m.groups()

            if rep == '':
                # exactly one
                minimum_count = 1
                maximum_count = 1
            elif rep == '?':
                # zero or one
                minimum_count = 0
                maximum_count = 1
            elif rep == '*':
                # any number
                minimum_count = 0
                maximum_count = sys.maxint
            elif rep == '+':
                # one or more
                minimum_count = 1
                maximum_count = sys.maxint
            else:
                # exact number or range constraint
                assert '{' in rep and '}' in rep, "INTERNAL ERROR"
                m = re.match(r'\{(\d+)(?:-(\d+))?\}$', rep)
                if not m:
                    Messager.warning("Project configuration: error parsing range '%s' in argument '%s' (syntax is '{MIN-MAX}')." % (rep, key+rep), 5)
                    raise InvalidProjectConfigException
                n1, n2 = m.groups()
                n1 = int(n1)
                if n2 is None:
                    # exact number
                    if n1 == 0:
                        Messager.warning("Project configuration: cannot have exactly 0 repetitions of argument '%s'." % (key+rep), 5)
                        raise InvalidProjectConfigException
                    minimum_count = n1
                    maximum_count = n1
                else:
                    # range
                    n2 = int(n2)
                    if n1 > n2:
                        Messager.warning("Project configuration: invalid range %d-%d for argument '%s'." % (n1, n2, key+rep), 5)
                        raise InvalidProjectConfigException
                    minimum_count = n1
                    maximum_count = n2

            # format / config sanity: an argument whose label ends
            # with a digit label cannot be repeated, as this would
            # introduce ambiguity into parsing. (For example, the
            # second "Theme" is "Theme2", and the second "Arg1" would
            # be "Arg12".)
            if maximum_count > 1 and key[-1].isdigit():
                Messager.warning("Project configuration: error parsing: arguments ending with a digit cannot be repeated: '%s'" % (key+rep), 5)
                raise InvalidProjectConfigException

            if key in self.arguments:
                Messager.warning("Project configuration: error parsing: %s argument '%s' appears multiple times." % key, 5)
                raise InvalidProjectConfigException

            assert (key not in self.arg_min_count and 
                    key not in self.arg_max_count), "INTERNAL ERROR"
            self.arg_min_count[key] = minimum_count
            self.arg_max_count[key] = maximum_count

            self.arg_list.append(key)
            
            for atype in atypes.split("|"):
                if atype.strip() == "":
                    Messager.warning("Project configuration: error parsing: empty type for argument '%s'." % a, 5)
                    raise InvalidProjectConfigException

                # Check disabled; need to support arbitrary UTF values 
                # for visual.conf. TODO: add this check for other configs.
                # TODO: consider checking for similar for appropriate confs.
#                 if atype not in reserved_config_string and normalize_to_storage_form(atype) != atype:
#                     Messager.warning("Project configuration: '%s' is not a valid argument (should match '^[a-zA-Z0-9_-]*$')" % atype, 5)
#                     raise InvalidProjectConfigException

                if key not in self.arguments:
                    self.arguments[key] = []
                self.arguments[key].append(atype)

                if atype not in self.keys_by_type:
                    self.keys_by_type[atype] = []
                self.keys_by_type[atype].append(key)

    def argument_minimum_count(self, arg):
        """
        Returns the minumum number of times the given argument is
        required to appear for this type.
        """
        return self.arg_min_count.get(arg, 0)

    def argument_maximum_count(self, arg):
        """
        Returns the maximum number of times the given argument is
        allowed to appear for this type.
        """
        return self.arg_max_count.get(arg, 0)

    def mandatory_arguments(self):
        """
        Returns the arguments that must appear at least once for
        this type.
        """
        return [a for a in self.arg_list if self.arg_min_count[a] > 0]

    def multiple_allowed_arguments(self):
        """
        Returns the arguments that may appear multiple times for this
        type.
        """
        return [a for a in self.arg_list if self.arg_max_count[a] > 1]
        
    def storage_form(self):
        """
        Returns the form of the term used for storage serverside.
        """
        return self.__primary_term

    def normalizations(self):
        """
        Returns the normalizations applicable to this node, if any.
        """
        return self.special_arguments.get('<NORM>', [])

def __require_tab_separator(section):
    """    
    Given a section name, returns True iff in that section of the
    project config only tab separators should be permitted.
    This exception initially introduced to allow slighlty different
    syntax for the [labels] section than others.
    """
    return section == "labels"    

def __read_term_hierarchy(input, section=None):
    root_nodes    = []
    last_node_at_depth = {}
    last_args_at_depth = {}

    macros = {}
    for l in input:
        # skip empties and lines starting with '#'
        if l.strip() == '' or re.match(r'^\s*#', l):
            continue

        # interpret lines of only hyphens as separators
        # for display
        if re.match(r'^\s*-+\s*$', l):
            # TODO: proper placeholder and placing
            root_nodes.append(SEPARATOR_STR)
            continue

        # interpret lines of the format <STR1>=STR2 as "macro"
        # definitions, defining <STR1> as a placeholder that should be
        # replaced with STR2 whevever it occurs.
        m = re.match(r'^<([a-zA-Z_-]+)>=\s*(.*?)\s*$', l)
        if m:
            name, value = m.groups()
            if name in reserved_config_name:
                Messager.error("Cannot redefine <%s> in configuration, it is a reserved name." % name)
                # TODO: proper exception
                assert False
            else:
                macros["<%s>" % name] = value
            continue

        # macro expansion
        for n in macros:
            l = l.replace(n, macros[n])

        # check for undefined macros
        for m in re.finditer(r'(<.*?>)', l):
            s = m.group(1)
            assert s in reserved_config_string, "Error: undefined macro %s in configuration. (Note that macros are section-specific.)" % s

        # choose strict tab-only separator or looser any-space
        # separator matching depending on section
        if __require_tab_separator(section):
            m = re.match(r'^(\s*)([^\t]+)(?:\t(.*))?$', l)
        else:
            m = re.match(r'^(\s*)(\S+)(?:\s+(.*))?$', l)
        assert m, "Error parsing line: '%s'" % l
        indent, terms, args = m.groups()
        terms = [t.strip() for t in terms.split("|") if t.strip() != ""]
        if args is None or args.strip() == "":
            args = []
        else:
            args = [a.strip() for a in args.split(",") if a.strip() != ""]

        # older configs allowed space in term strings, splitting those
        # from arguments by space. Trying to parse one of these in the
        # new way will result in a crash from space in arguments.
        # The following is a workaround for the transition.
        if len([x for x in args if re.search('\s', x)]) and '\t' in l:
            # re-parse in the old way (dups from above)
            m = re.match(r'^(\s*)([^\t]+)(?:\t(.*))?$', l)
            assert m, "Error parsing line: '%s'" % l
            indent, terms, args = m.groups()
            terms = [t.strip() for t in terms.split("|") if t.strip() != ""]
            if args is None or args.strip() == "":
                args = []
            else:
                args = [a.strip() for a in args.split(",") if a.strip() != ""]
            # issue a warning
            Messager.warning("Space in term name(s) (%s) on line \"%s\" in config. This feature is deprecated and support will be removed in future versions. Please revise your configuration." % (",".join(['"%s"' % x for x in terms if " " in x]), l), 20)

        # depth in the ontology corresponds to the number of
        # spaces in the initial indent.
        depth = len(indent)

        # expand <INHERIT> into parent arguments
        expanded_args = []
        for a in args:
            if a != '<INHERIT>':
                expanded_args.append(a)
            else:
                assert depth-1 in last_args_at_depth, \
                    "Error no parent for '%s'" % l
                expanded_args.extend(last_args_at_depth[depth-1])
        # TODO: remove, debugging
#         if expanded_args != args:
#             Messager.info('expand: %s --> %s' % (str(args), str(expanded_args)))
        args = expanded_args

        n = TypeHierarchyNode(terms, args)
        if depth == 0:
            # root level, no children assignments
            root_nodes.append(n)
        else:
            # assign as child of last node at the depth of the parent
            assert depth-1 in last_node_at_depth, \
                "Error: no parent for '%s'" % l
            last_node_at_depth[depth-1].children.append(n)
        last_node_at_depth[depth] = n
        last_args_at_depth[depth] = args

    return root_nodes

def __read_or_default(filename, default):
    try:
        f = open_textfile(filename, 'r')
        r = f.read()
        f.close()
        return r
    except:
        # TODO: specific exception handling and reporting
        return default

def __parse_kb_shortcuts(shortcutstr, default, source):
    try:
        shortcuts = {}
        for l in shortcutstr.split("\n"):
            l = l.strip()
            if l == "" or l[:1] == "#":
                continue
            key, type = re.split(r'[ \t]+', l)
            if key in shortcuts:
                Messager.warning("Project configuration: keyboard shortcut for '%s' defined multiple times. Ignoring all but first ('%s')" % (key, shortcuts[key]))
            else:
                shortcuts[key] = type
    except:
        # TODO: specific exception handling
        Messager.warning("Project configuration: error parsing keyboard shortcuts from %s. Configuration may be wrong." % source, 5)
        shortcuts = default
    return shortcuts
    
def __parse_access_control(acstr, source):
    try:
        parser = robotparser.RobotFileParser()
        parser.parse(acstr.split("\n"))
    except:
        # TODO: specific exception handling
        display_message("Project configuration: error parsing access control rules from %s. Configuration may be wrong." % source, "warning", 5)
        parser = None
    return parser
    

def get_config_path(directory):
    return __read_first_in_directory_tree(directory, __annotation_config_filename)[1]

def __read_first_in_directory_tree(directory, filename):
    # config will not be available command-line invocations;
    # in these cases search whole tree
    try:
        from config import BASE_DIR
    except:
        BASE_DIR = "/"
    from os.path import split, join

    source, result = None, None

    # check from the given directory and parents, but not above BASE_DIR
    if directory is not None:
        # TODO: this check may fail; consider "foo//bar/data"
        while BASE_DIR in directory:
            source = join(directory, filename)
            result = __read_or_default(source, None)
            if result is not None:
                break
            directory = split(directory)[0]

    return (result, source)

def __parse_configs(configstr, source, expected_sections, optional_sections):
    # top-level config structure is a set of term hierarchies
    # separated by lines consisting of "[SECTION]" where SECTION is
    # e.g.  "entities", "relations", etc.

    # start by splitting config file lines by section, also storing
    # the label (default name or alias) used for each section.

    section = "general"
    section_lines = { section: [] }
    section_labels = {}
    for ln, l in enumerate(configstr.split("\n")):
        m = re.match(r'^\s*\[(.*)\]\s*$', l)
        if m:
            section = m.group(1)

            # map and store section name/alias (e.g. "spans" -> "entities")
            section_name = SECTION_ALIAS.get(section, section)
            section_labels[section_name] = section
            section = section_name

            if section not in expected_sections:
                Messager.warning("Project configuration: unexpected section [%s] in %s. Ignoring contents." % (section, source), 5)
            if section not in section_lines:
                section_lines[section] = []
        else:
            section_lines[section].append(l)

    # attempt to parse lines in each section as a term hierarchy
    configs = {}
    for s, sl in section_lines.items():
        try:
            configs[s] = __read_term_hierarchy(sl, s)
        except Exception, e:
            Messager.warning("Project configuration: error parsing section [%s] in %s: %s" % (s, source, str(e)), 5)
            raise

    # verify that expected sections are present; replace with empty if not.
    for s in expected_sections:
        if s not in configs:
            if s not in optional_sections:
                Messager.warning("Project configuration: missing section [%s] in %s. Configuration may be wrong." % (s, source), 5)
            configs[s] = []

    return (configs, section_labels)
            
def get_configs(directory, filename, defaultstr, minconf, sections, optional_sections):
    if (directory, filename) not in get_configs.__cache:
        configstr, source =  __read_first_in_directory_tree(directory, filename)

        if configstr is None:
            # didn't get one; try default dir and fall back to the default
            configstr = __read_or_default(filename, defaultstr)
            if configstr == defaultstr:                
                Messager.info("Project configuration: no configuration file (%s) found, using default." % filename, 5)
                source = "[default]"
            else:
                source = filename

        # try to parse what was found, fall back to minimal config
        try: 
            configs, section_labels = __parse_configs(configstr, source, sections, optional_sections)        
        except:
            Messager.warning("Project configuration: Falling back to minimal default. Configuration is likely wrong.", 5)
            configs = minconf
            section_labels = dict(map(lambda a: (a,a), sections))

        # very, very special case processing: if we have a type
        # "Equiv" defined in a "relations" section that doesn't
        # specify a "<REL-TYPE>", automatically fill "symmetric" and
        # "transitive". This is to support older configurations that
        # rely on the type "Equiv" to identify the relation as an
        # equivalence.
        if 'relations' in configs:
            for r in configs['relations']:
                if r == SEPARATOR_STR:
                    continue
                if (r.storage_form() == "Equiv" and 
                    "<REL-TYPE>" not in r.special_arguments):
                    # this was way too much noise; will only add in after
                    # at least most configs are revised.
#                     Messager.warning('Note: "Equiv" defined in config without "<REL-TYPE>"; assuming symmetric and transitive. Consider revising config to add "<REL-TYPE>:symmetric-transitive" to definition.')
                    r.special_arguments["<REL-TYPE>"] = ["symmetric", "transitive"]

        get_configs.__cache[(directory, filename)] = (configs, section_labels)

    return get_configs.__cache[(directory, filename)]
get_configs.__cache = {}

def __get_access_control(directory, filename, default_rules):

    acstr, source = __read_first_in_directory_tree(directory, filename)

    if acstr is None:
        acstr = default_rules # TODO read or default isntead of default
        if acstr == default_rules:
            source = "[default rules]"
        else:
            source = filename
    ac_oracle = __parse_access_control(acstr, source)
    return ac_oracle


def __get_kb_shortcuts(directory, filename, default_shortcuts, min_shortcuts):

    shortcutstr, source = __read_first_in_directory_tree(directory, filename)

    if shortcutstr is None:
        shortcutstr = __read_or_default(filename, default_shortcuts)
        if shortcutstr == default_shortcuts:
            source = "[default kb_shortcuts]"
        else:
            source = filename

    kb_shortcuts = __parse_kb_shortcuts(shortcutstr, min_shortcuts, source)
    return kb_shortcuts

# final fallback for configuration; a minimal known-good config
__minimal_configuration = {
    ENTITY_SECTION    : [TypeHierarchyNode(["Protein"])],
    RELATION_SECTION  : [TypeHierarchyNode(["Equiv"], ["Arg1:Protein", "Arg2:Protein", "<REL-TYPE>:symmetric-transitive"])],
    EVENT_SECTION     : [TypeHierarchyNode(["Event"], ["Theme:Protein"])],
    ATTRIBUTE_SECTION : [TypeHierarchyNode(["Negation"], ["Arg:<EVENT>"])],
    }

def get_annotation_configs(directory):
    return get_configs(directory, 
                       __annotation_config_filename, 
                       __default_configuration,
                       __minimal_configuration,
                       __expected_annotation_sections,
                       __optional_annotation_sections)

# final fallback for visual configuration; minimal known-good config
__minimal_visual = {
    LABEL_SECTION     : [TypeHierarchyNode(["Protein", "Pro", "P"]),
                         TypeHierarchyNode(["Equiv", "Eq"]),
                         TypeHierarchyNode(["Event", "Ev"])],
    DRAWING_SECTION   : [TypeHierarchyNode([VISUAL_SPAN_DEFAULT], ["fgColor:black", "bgColor:white"]),
                         TypeHierarchyNode([VISUAL_ARC_DEFAULT], ["color:black"]),
                         TypeHierarchyNode([VISUAL_ATTR_DEFAULT], ["glyph:*"])],
    }

def get_visual_configs(directory):
    return get_configs(directory,
                       __visual_config_filename,
                       __default_visual,
                       __minimal_visual,
                       __expected_visual_sections,
                       __optional_visual_sections)

# final fallback for tools configuration; minimal known-good config
__minimal_tools = {
    OPTIONS_SECTION    : [],
    SEARCH_SECTION     : [TypeHierarchyNode(["google"], ["<URL>:http://www.google.com/search?q=%s"])],
    ANNOTATORS_SECTION : [],
    DISAMBIGUATORS_SECTION : [],
    NORMALIZATION_SECTION : [],
    }

def get_tools_configs(directory):
    return get_configs(directory,
                       __tools_config_filename,
                       __default_tools,
                       __minimal_tools,
                       __expected_tools_sections,
                       __optional_tools_sections)

def get_entity_type_hierarchy(directory):    
    return get_annotation_configs(directory)[0][ENTITY_SECTION]

def get_relation_type_hierarchy(directory):    
    return get_annotation_configs(directory)[0][RELATION_SECTION]

def get_event_type_hierarchy(directory):    
    return get_annotation_configs(directory)[0][EVENT_SECTION]

def get_attribute_type_hierarchy(directory):    
    return get_annotation_configs(directory)[0][ATTRIBUTE_SECTION]

def get_annotation_config_section_labels(directory):
    return get_annotation_configs(directory)[1]

# TODO: too much caching?
def get_labels(directory):
    cache = get_labels.__cache
    if directory not in cache:
        l = {}
        for t in get_visual_configs(directory)[0][LABEL_SECTION]:
            if t.storage_form() in l:
                Messager.warning("In configuration, labels for '%s' defined more than once. Only using the last set." % t.storage_form(), -1)
            # first is storage for, rest are labels.
            l[t.storage_form()] = t.terms[1:]
        cache[directory] = l
    return cache[directory]
get_labels.__cache = {}

# TODO: too much caching?
def get_drawing_types(directory):
    cache = get_drawing_types.__cache
    if directory not in cache:
        l = set()
        for n in get_drawing_config(directory):
            l.add(n.storage_form())
        cache[directory] = list(l)
    return cache[directory]
get_drawing_types.__cache = {}

def get_option_config(directory):
    return get_tools_configs(directory)[0][OPTIONS_SECTION]

def get_drawing_config(directory):
    return get_visual_configs(directory)[0][DRAWING_SECTION]

def get_visual_option_config(directory):
    return get_visual_configs(directory)[0][OPTIONS_SECTION]

def get_visual_config_section_labels(directory):
    return get_visual_configs(directory)[1]

def get_search_config(directory):
    return get_tools_configs(directory)[0][SEARCH_SECTION]

def get_annotator_config(directory):
    return get_tools_configs(directory)[0][ANNOTATORS_SECTION]

def get_disambiguator_config(directory):
    return get_tools_configs(directory)[0][DISAMBIGUATORS_SECTION]

def get_normalization_config(directory):
    return get_tools_configs(directory)[0][NORMALIZATION_SECTION]

def get_tools_config_section_labels(directory):
    return get_tools_configs(directory)[1]

def get_access_control(directory):
    cache = get_access_control.__cache
    if directory not in cache:
        a = __get_access_control(directory,
                         __access_control_filename,
                         __default_access_control)
        cache[directory] = a

    return cache[directory]
get_access_control.__cache = {}

def get_kb_shortcuts(directory):
    cache = get_kb_shortcuts.__cache
    if directory not in cache:
        a = __get_kb_shortcuts(directory,
                                __kb_shortcut_filename,
                                __default_kb_shortcuts,
                               { "P" : "Positive_regulation" })
        cache[directory] = a

    return cache[directory]
get_kb_shortcuts.__cache = {}

def __collect_type_list(node, collected):
    if node == SEPARATOR_STR:
        return collected

    collected.append(node)

    for c in node.children:
        __collect_type_list(c, collected)

    return collected

def __type_hierarchy_to_list(hierarchy):
    root_nodes = hierarchy
    types = []
    for n in root_nodes:
        __collect_type_list(n, types)
    return types

# TODO: it's not clear it makes sense for all of these methods to have
# their own caches; this seems a bit like a case of premature
# optimization to me. Consider simplifying.

def get_entity_type_list(directory):
    cache = get_entity_type_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_entity_type_hierarchy(directory))
    return cache[directory]
get_entity_type_list.__cache = {}

def get_event_type_list(directory):
    cache = get_event_type_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_event_type_hierarchy(directory))
    return cache[directory]
get_event_type_list.__cache = {}

def get_relation_type_list(directory):
    cache = get_relation_type_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_relation_type_hierarchy(directory))
    return cache[directory]
get_relation_type_list.__cache = {}

def get_attribute_type_list(directory):
    cache = get_attribute_type_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_attribute_type_hierarchy(directory))
    return cache[directory]
get_attribute_type_list.__cache = {}    

def get_search_config_list(directory):
    cache = get_search_config_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_search_config(directory))
    return cache[directory]
get_search_config_list.__cache = {}    

def get_annotator_config_list(directory):
    cache = get_annotator_config_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_annotator_config(directory))
    return cache[directory]
get_annotator_config_list.__cache = {}    

def get_disambiguator_config_list(directory):
    cache = get_disambiguator_config_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_disambiguator_config(directory))
    return cache[directory]
get_disambiguator_config_list.__cache = {}    

def get_normalization_config_list(directory):
    cache = get_normalization_config_list.__cache
    if directory not in cache:
        cache[directory] = __type_hierarchy_to_list(get_normalization_config(directory))
    return cache[directory]
get_normalization_config_list.__cache = {}    

def get_node_by_storage_form(directory, term):
    cache = get_node_by_storage_form.__cache
    if directory not in cache:
        d = {}
        for e in get_entity_type_list(directory) + get_event_type_list(directory):
            t = e.storage_form()
            if t in d:
                Messager.warning("Project configuration: term %s appears multiple times, only using last. Configuration may be wrong." % t, 5)
            d[t] = e
        cache[directory] = d

    return cache[directory].get(term, None)
get_node_by_storage_form.__cache = {}

def _get_option_by_storage_form(directory, term, config, cache):
    if directory not in cache:
        d = {}
        for n in config:
            t = n.storage_form()
            if t in d:
                Messager.warning("Project configuration: %s appears multiple times, only using last. Configuration may be wrong." % t, 5)
            d[t] = {}
            for a in n.arguments:
                if len(n.arguments[a]) != 1:
                    Messager.warning("Project configuration: %s key %s has multiple values, only using first. Configuration may be wrong." % (t, a), 5)
                d[t][a] = n.arguments[a][0]

        cache[directory] = d

    return cache[directory].get(term, None)

def get_option_config_by_storage_form(directory, term):
    cache = get_option_config_by_storage_form.__cache
    config = get_option_config(directory)
    return _get_option_by_storage_form(directory, term, config, cache)
get_option_config_by_storage_form.__cache = {}    

def get_visual_option_config_by_storage_form(directory, term):
    cache = get_visual_option_config_by_storage_form.__cache
    config = get_visual_option_config(directory)
    return _get_option_by_storage_form(directory, term, config, cache)
get_visual_option_config_by_storage_form.__cache = {}    

# access for settings for specific options in tools.conf
# TODO: avoid fixed string values here, define vars earlier

def options_get_validation(directory):
    v = get_option_config_by_storage_form(directory, 'Validation')
    return 'none' if v is None else v.get('validate', 'none')        

def options_get_tokenization(directory):
    v = get_option_config_by_storage_form(directory, 'Tokens')
    return 'whitespace' if v is None else v.get('tokenizer', 'whitespace')

def options_get_ssplitter(directory):
    v = get_option_config_by_storage_form(directory, 'Sentences')
    return 'regex' if v is None else v.get('splitter', 'regex')

def options_get_annlogfile(directory):
    v = get_option_config_by_storage_form(directory, 'Annotation-log')
    return '<NONE>' if v is None else v.get('logfile', '<NONE>')

# access for settings for specific options in visual.conf

def visual_options_get_arc_bundle(directory):
    v = get_visual_option_config_by_storage_form(directory, 'Arcs')
    return 'none' if v is None else v.get('bundle', 'none')

def get_drawing_config_by_storage_form(directory, term):
    cache = get_drawing_config_by_storage_form.__cache
    if directory not in cache:
        d = {}
        for n in get_drawing_config(directory):
            t = n.storage_form()
            if t in d:
                Messager.warning("Project configuration: term %s appears multiple times, only using last. Configuration may be wrong." % t, 5)
            d[t] = {}
            for a in n.arguments:
                # attribute drawing can be specified with multiple
                # values (multi-valued attributes), other parts of
                # drawing config should have single values only.
                if len(n.arguments[a]) != 1:
                    if a in ATTR_DRAWING_ATTRIBUTES:
                        # use multi-valued directly
                        d[t][a] = n.arguments[a]
                    else:
                        # warn and pass
                        Messager.warning("Project configuration: expected single value for %s argument %s, got '%s'. Configuration may be wrong." % (t, a, "|".join(n.arguments[a])))
                else:
                    d[t][a] = n.arguments[a][0]

        # TODO: hack to get around inability to have commas in values;
        # fix original issue instead
        for t in d:
            for k in d[t]:
                # sorry about this
                if not isinstance(d[t][k], list):
                    d[t][k] = d[t][k].replace("-", ",")
                else:
                    for i in range(len(d[t][k])):
                        d[t][k][i] = d[t][k][i].replace("-", ",")
                
        default_keys = [VISUAL_SPAN_DEFAULT, 
                        VISUAL_ARC_DEFAULT,
                        VISUAL_ATTR_DEFAULT]
        for default_dict in [d.get(dk, {}) for dk in default_keys]:
            for k in default_dict:
                for t in d:
                    d[t][k] = d[t].get(k, default_dict[k])

        # Kind of a special case: recognize <NONE> as "deleting" an
        # attribute (prevents default propagation) and <EMPTY> as
        # specifying that a value should be the empty string
        # (can't be written as such directly).
        for t in d:
            todelete = [k for k in d[t] if d[t][k] == '<NONE>']
            for k in todelete:
                del d[t][k]

            for k in d[t]:
                if d[t][k] == '<EMPTY>':
                    d[t][k] = ''

        cache[directory] = d

    return cache[directory].get(term, None)
get_drawing_config_by_storage_form.__cache = {}    

def __directory_relations_by_arg_num(directory, num, atype, include_special=False):
    assert num >= 0 and num < 2, "INTERNAL ERROR"

    rels = []

    entity_types = set([t.storage_form() 
                        for t in get_entity_type_list(directory)])
    event_types = set([t.storage_form() 
                       for t in get_event_type_list(directory)])

    for r in get_relation_type_list(directory):
        # "Special" nesting relations ignored unless specifically
        # requested
        if r.storage_form() in SPECIAL_RELATION_TYPES and not include_special:
            continue

        if len(r.arg_list) != 2:
            # Don't complain about argument constraints for unused relations
            if not r.unused:
                Messager.warning("Relation type %s has %d arguments in configuration (%s; expected 2). Please fix configuration." % (r.storage_form(), len(r.arg_list), ",".join(r.arg_list)))
        else:
            types = r.arguments[r.arg_list[num]]
            for type_ in types:
                # TODO: there has to be a better way
                if (type_ == atype or
                    type_ == "<ANY>" or
                    atype == "<ANY>" or
                    (type_ in entity_types and atype == "<ENTITY>") or
                    (type_ in event_types and atype == "<EVENT>") or
                    (atype in entity_types and type_ == "<ENTITY>") or
                    (atype in event_types and type_ == "<EVENT>")):
                    rels.append(r)
                    # TODO: why not break here?

    return rels

def get_relations_by_arg1(directory, atype, include_special=False):
    cache = get_relations_by_arg1.__cache
    cache[directory] = cache.get(directory, {})
    if (atype, include_special) not in cache[directory]:
        cache[directory][(atype, include_special)] = __directory_relations_by_arg_num(directory, 0, atype, include_special)
    return cache[directory][(atype, include_special)]
get_relations_by_arg1.__cache = {}

def get_relations_by_arg2(directory, atype, include_special=False):
    cache = get_relations_by_arg2.__cache
    cache[directory] = cache.get(directory, {})
    if (atype, include_special) not in cache[directory]:
        cache[directory][(atype, include_special)] = __directory_relations_by_arg_num(directory, 1, atype, include_special)
    return cache[directory][(atype, include_special)]
get_relations_by_arg2.__cache = {}

def get_relations_by_storage_form(directory, rtype, include_special=False):
    cache = get_relations_by_storage_form.__cache
    cache[directory] = cache.get(directory, {})
    if include_special not in cache[directory]:
        cache[directory][include_special] = {}
        for r in get_relation_type_list(directory):
            if (r.storage_form() in SPECIAL_RELATION_TYPES and 
                not include_special):
                continue
            if r.unused:
                continue
            if r.storage_form() not in cache[directory][include_special]:
                cache[directory][include_special][r.storage_form()] = []
            cache[directory][include_special][r.storage_form()].append(r)
    return cache[directory][include_special].get(rtype, [])
get_relations_by_storage_form.__cache = {}

def get_labels_by_storage_form(directory, term):
    cache = get_labels_by_storage_form.__cache
    if directory not in cache:
        cache[directory] = {}
        for l, labels in get_labels(directory).items():
            # recognize <EMPTY> as specifying that a label should
            # be the empty string
            labels = [lab if lab != '<EMPTY>' else ' ' for lab in labels]
            cache[directory][l] = labels
    return cache[directory].get(term, None)
get_labels_by_storage_form.__cache = {}

# fallback for missing or partial config: these are highly likely to
# be entity (as opposed to an event or relation) types.
# TODO: remove this workaround once the configs stabilize.
very_likely_physical_entity_types = [
    'Protein',
    'Entity',
    'Organism',
    'Chemical',
    'Two-component-system',
    'Regulon-operon',
    # for more PTM annotation
    'Protein_family_or_group',
    'DNA_domain_or_region',
    'Protein_domain_or_region',
    'Amino_acid_monomer',
    'Carbohydrate',
    # for AZ corpus
    'Cell_type',
    'Drug_or_compound',
    'Gene_or_gene_product',
    'Tissue',
    #'Not_sure',
    #'Other',
    'Other_pharmaceutical_agent',
    ]

# helper; doesn't really belong here
# TODO: shouldn't we have an utils.py or something for stuff like this? 
def unique_preserve_order(iterable):
    seen = set()
    uniqued = []
    for i in iterable:
        if i not in seen:
            seen.add(i)
            uniqued.append(i)
    return uniqued

class ProjectConfiguration(object):
    def __init__(self, directory):
        # debugging (note: latter test for windows paths)
        if directory[:1] != "/" and not re.search(r'^[a-zA-Z]:\\', directory):
            Messager.debug("Project config received relative directory ('%s'), configuration may not be found." % directory, duration=-1)
        self.directory = directory

    def mandatory_arguments(self, atype):
        """
        Returns the mandatory argument types that must be present for
        an annotation of the given type.
        """
        node = get_node_by_storage_form(self.directory, atype)
        if node is None:
            Messager.warning("Project configuration: unknown event type %s. Configuration may be wrong." % atype)
            return []
        return node.mandatory_arguments()

    def multiple_allowed_arguments(self, atype):
        """
        Returns the argument types that are allowed to be filled more
        than once for an annotation of the given type.
        """
        node = get_node_by_storage_form(self.directory, atype)
        if node is None:
            Messager.warning("Project configuration: unknown event type %s. Configuration may be wrong." % atype)
            return []
        return node.multiple_allowed_arguments()

    def argument_maximum_count(self, atype, arg):
        """
        Returns the maximum number of times that the given argument is
        allowed to be filled for an annotation of the given type.
        """
        node = get_node_by_storage_form(self.directory, atype)
        if node is None:
            Messager.warning("Project configuration: unknown event type %s. Configuration may be wrong." % atype)
            return 0
        return node.argument_maximum_count(arg)

    def argument_minimum_count(self, atype, arg):
        """
        Returns the minimum number of times that the given argument is
        allowed to be filled for an annotation of the given type.
        """
        node = get_node_by_storage_form(self.directory, atype)
        if node is None:
            Messager.warning("Project configuration: unknown event type %s. Configuration may be wrong." % atype)
            return 0
        return node.argument_minimum_count(arg)

    def arc_types_from(self, from_ann):
        return self.arc_types_from_to(from_ann)

    def relation_types_from(self, from_ann, include_special=False):
        """
        Returns the possible relation types that can have an
        annotation of the given type as their arg1.
        """
        return [r.storage_form() for r in get_relations_by_arg1(self.directory, from_ann, include_special)]

    def relation_types_to(self, to_ann, include_special=False):
        """
        Returns the possible relation types that can have an
        annotation of the given type as their arg2.
        """
        return [r.storage_form() for r in get_relations_by_arg2(self.directory, to_ann, include_special)]

    def relation_types_from_to(self, from_ann, to_ann, include_special=False):
        """
        Returns the possible relation types that can have the
        given arg1 and arg2.
        """
        types = []

        t1r = get_relations_by_arg1(self.directory, from_ann, include_special)
        t2r = get_relations_by_arg2(self.directory, to_ann, include_special)

        for r in t1r:
            if r in t2r:
                types.append(r.storage_form())

        return types

    def overlap_types(self, inner, outer):
        """
        Returns the set of annotation overlap types that have been
        configured for the given pair of annotations.
        """
        # TODO: this is O(NM) for relation counts N and M and goes
        # past much of the implemented caching. Might become a
        # bottleneck for annotations with large type systems.
        t1r = get_relations_by_arg1(self.directory, inner, True)
        t2r = get_relations_by_arg2(self.directory, outer, True)

        types = []
        for r in (s for s in t1r if s.storage_form() in SPECIAL_RELATION_TYPES):
            if r in t2r:
                types.append(r)

        # new-style overlap configuration ("<OVERLAP>") takes precedence
        # over old-style configuration ("ENTITY-NESTING").
        ovl_types = set()

        ovl = [r for r in types if r.storage_form() == TEXTBOUND_OVERLAP_TYPE]
        nst = [r for r in types if r.storage_form() == ENTITY_NESTING_TYPE]

        if ovl:
            if nst:
                Messager.warning('Warning: both '+TEXTBOUND_OVERLAP_TYPE+
                                 ' and '+ENTITY_NESTING_TYPE+' defined for '+
                                 '('+inner+','+outer+') in config. '+
                                 'Ignoring latter.')
            for r in ovl:
                if OVERLAP_TYPE_ARG not in r.special_arguments:
                    Messager.warning('Warning: missing '+OVERLAP_TYPE_ARG+
                                     ' for '+TEXTBOUND_OVERLAP_TYPE+
                                     ', ignoring specification.')
                    continue
                for val in r.special_arguments[OVERLAP_TYPE_ARG]:
                    ovl_types |= set(val.split('|'))
        elif nst:
            # translate into new-style configuration
            ovl_types = set(['contain'])
        else:
            ovl_types = set()

        undefined_types = [t for t in ovl_types if 
                           t not in ('contain', 'equal', 'cross', '<ANY>')]
        if undefined_types:
            Messager.warning('Undefined '+OVERLAP_TYPE_ARG+' value(s) '+
                             str(undefined_types)+' for '+
                             '('+inner+','+outer+') in config. ')
        return ovl_types

    def span_can_contain(self, inner, outer):
        """
        Returns True if the configuration allows the span of an
        annotation of type inner to (properly) contain an annotation
        of type outer, False otherwise.
        """
        ovl_types = self.overlap_types(inner, outer)
        if 'contain' in ovl_types or '<ANY>' in ovl_types:
            return True
        ovl_types = self.overlap_types(outer, inner)
        if '<ANY>' in ovl_types:
            return True
        return False

    def spans_can_be_equal(self, t1, t2):
        """
        Returns True if the configuration allows the spans of
        annotations of type t1 and t2 to be equal, False otherwise.
        """
        ovl_types = self.overlap_types(t1, t2)
        if 'equal' in ovl_types or '<ANY>' in ovl_types:
            return True
        ovl_types = self.overlap_types(t2, t1)
        if 'equal' in ovl_types or '<ANY>' in ovl_types:
            return True
        return False

    def spans_can_cross(self, t1, t2):
        """
        Returns True if the configuration allows the spans of
        annotations of type t1 and t2 to cross, False otherwise.
        """
        ovl_types = self.overlap_types(t1, t2)
        if 'cross' in ovl_types or '<ANY>' in ovl_types:
            return True
        ovl_types = self.overlap_types(t2, t1)
        if 'cross' in ovl_types or '<ANY>' in ovl_types:
            return True
        return False

    def all_connections(self, include_special=False):
        """
        Returns a dict of dicts of lists, outer dict keyed by
        entity/event type, inner dicts by role/relation type, and
        lists containing entity/event types, representing all possible
        connections between annotations. This function is provided to
        optimize access to the entire annotation configuration for
        passing it to the client and should never be used to check for
        individual connections. The caller must not change the
        contents of the returned collection.
        """

        # TODO: are these uniques really necessary?
        entity_types = unique_preserve_order(self.get_entity_types())
        event_types = unique_preserve_order(self.get_event_types())
        all_types =  unique_preserve_order(entity_types + event_types)

        connections = {}

        # TODO: it might be possible to avoid copies like
        # entity_types[:] and all_types[:] here. Consider the
        # possibility.

        for t1 in all_types:
            assert t1 not in connections, "INTERNAL ERROR"
            connections[t1] = {}

            processed_as_relation = {}

            # relations

            rels = get_relations_by_arg1(self.directory, t1, include_special)
            
            for r in rels:
                a = r.storage_form()

                conns = connections[t1].get(a, [])

                # magic number "1" is for 2nd argument
                args = r.arguments[r.arg_list[1]]

                if "<ANY>" in args:
                    connections[t1][a] = all_types[:]
                else:
                    for t2 in args:
                        if t2 == "<ENTITY>":
                            conns.extend(entity_types)
                        elif t2 == "<EVENT>":
                            conns.extend(event_types)
                        else:
                            conns.append(t2)
                    connections[t1][a] = unique_preserve_order(conns)

                processed_as_relation[a] = True

            # event arguments

            n1 = get_node_by_storage_form(self.directory, t1)
                        
            for a, args in n1.arguments.items():
                if a in processed_as_relation:
                    Messager.warning("Project configuration: %s appears both as role and relation. Configuration may be wrong." % a)
                    # won't try to resolve
                    continue

                assert a not in connections[t1], "INTERNAL ERROR"

                # TODO: dedup w/above
                if "<ANY>" in args:
                    connections[t1][a] = all_types[:]
                else:
                    conns = []
                    for t2 in args:
                        if t2 == "<EVENT>":
                            conns.extend(event_types)
                        elif t2 == "<ENTITY>":
                            conns.extend(entity_types)
                        else:
                            conns.append(t2)
                    connections[t1][a] = unique_preserve_order(conns)

        return connections

    def arc_types_from_to(self, from_ann, to_ann="<ANY>", include_special=False):
        """
        Returns the possible arc types that can connect an annotation
        of type from_ann to an annotation of type to_ann.
        If to_ann has the value \"<ANY>\", returns all possible arc types.
        """

        from_node = get_node_by_storage_form(self.directory, from_ann)

        if from_node is None:
            Messager.warning("Project configuration: unknown textbound/event type %s. Configuration may be wrong." % from_ann)
            return []

        if to_ann == "<ANY>":
            relations_from = get_relations_by_arg1(self.directory, from_ann, include_special)
            # TODO: consider using from_node.arg_list instead of .arguments for order
            return unique_preserve_order([role for role in from_node.arguments] + [r.storage_form() for r in relations_from])

        # specific hits
        types = from_node.keys_by_type.get(to_ann, [])

        if "<ANY>" in from_node.keys_by_type:
            types += from_node.keys_by_type["<ANY>"]

        # generic arguments
        if self.is_event_type(to_ann) and '<EVENT>' in from_node.keys_by_type:
            types += from_node.keys_by_type['<EVENT>']
        if self.is_physical_entity_type(to_ann) and '<ENTITY>' in from_node.keys_by_type:
            types += from_node.keys_by_type['<ENTITY>']

        # relations
        types.extend(self.relation_types_from_to(from_ann, to_ann))

        return unique_preserve_order(types)

    def attributes_for(self, ann_type):
        """
        Returs a list of the possible attribute types for an
        annotation of the given type.
        """
        attrs = []
        for attr in get_attribute_type_list(self.directory):
            if attr == SEPARATOR_STR:
                continue
            
            if 'Arg' not in attr.arguments:
                Messager.warning("Project configuration: config error: attribute '%s' lacks 'Arg:' specification." % attr.storage_form())
                continue

            types = attr.arguments['Arg']

            if ((ann_type in types) or ('<ANY>' in types) or
                (self.is_event_type(ann_type) and '<EVENT>' in types) or
                (self.is_physical_entity_type(ann_type) and '<ENTITY>' in types)
                or
                (self.is_relation_type(ann_type) and '<RELATION>' in types)):
                attrs.append(attr.storage_form())

        return attrs

    def get_labels(self):
        return get_labels(self.directory)

    def get_kb_shortcuts(self):
        return get_kb_shortcuts(self.directory)

    def get_access_control(self):
        return get_access_control(self.directory)

    def get_attribute_types(self):
        return [t.storage_form() for t in get_attribute_type_list(self.directory)]

    def get_event_types(self):
        return [t.storage_form() for t in get_event_type_list(self.directory)]

    def get_relation_types(self):
        return [t.storage_form() for t in get_relation_type_list(self.directory)]

    def get_equiv_types(self):
        # equivalence relations are those relations that are symmetric
        # and transitive, i.e. that have "symmetric" and "transitive"
        # in their "<REL-TYPE>" special argument values.
        return [t.storage_form() for t in get_relation_type_list(self.directory)
                if "<REL-TYPE>" in t.special_arguments and
                "symmetric" in t.special_arguments["<REL-TYPE>"] and
                "transitive" in t.special_arguments["<REL-TYPE>"]]

    def get_relations_by_type(self, _type):
        return get_relations_by_storage_form(self.directory, _type)

    def get_labels_by_type(self, _type):
        return get_labels_by_storage_form(self.directory, _type)

    def get_drawing_types(self):
        return get_drawing_types(self.directory)
    
    def get_drawing_config_by_type(self, _type):
        return get_drawing_config_by_storage_form(self.directory, _type)

    def get_search_config(self):
        search_config = []
        for r in get_search_config_list(self.directory):
            if '<URL>' not in r.special_arguments:
                Messager.warning('Project configuration: config error: missing <URL> specification for %s search.' % r.storage_form())
            else:
                search_config.append((r.storage_form(), r.special_arguments['<URL>'][0]))
        return search_config

    def _get_tool_config(self, tool_list):
        tool_config = []
        for r in tool_list:
            if '<URL>' not in r.special_arguments:
                Messager.warning('Project configuration: config error: missing <URL> specification for %s.' % r.storage_form())
                continue
            if 'tool' not in r.arguments:
                Messager.warning('Project configuration: config error: missing tool name ("tool") for %s.' % r.storage_form())
                continue
            if 'model' not in r.arguments:
                Messager.warning('Project configuration: config error: missing model name ("model") for %s.' % r.storage_form())
                continue
            tool_config.append((r.storage_form(),
                                r.arguments['tool'][0],
                                r.arguments['model'][0],
                                r.special_arguments['<URL>'][0]))
        return tool_config

    def get_disambiguator_config(self):
        tool_list = get_disambiguator_config_list(self.directory)
        return self._get_tool_config(tool_list)

    def get_annotator_config(self):
        # TODO: "annotator" is a very confusing term for a web service
        # that does automatic annotation in the context of a tool
        # where most annotators are expected to be human. Rethink.
        tool_list = get_annotator_config_list(self.directory)
        return self._get_tool_config(tool_list)

    def get_normalization_config(self):
        norm_list = get_normalization_config_list(self.directory)
        norm_config = []
        for n in norm_list:
            if 'DB' not in n.arguments:
                # optional, server looks in default location if None
                n.arguments['DB'] = [None]
            if '<URL>' not in n.special_arguments:
                Messager.warning('Project configuration: config error: missing <URL> specification for %s.' % n.storage_form())
                continue
            if '<URLBASE>' not in n.special_arguments:
                # now optional, client skips link generation if None
                n.special_arguments['<URLBASE>'] = [None]
            norm_config.append((n.storage_form(),
                                n.special_arguments['<URL>'][0],
                                n.special_arguments['<URLBASE>'][0],
                                n.arguments['DB'][0]))
        return norm_config
        
    def get_entity_types(self):
        return [t.storage_form() for t in get_entity_type_list(self.directory)]

    def get_entity_type_hierarchy(self):
        return get_entity_type_hierarchy(self.directory)

    def get_relation_type_hierarchy(self):
        return get_relation_type_hierarchy(self.directory)

    def get_event_type_hierarchy(self):
        return get_event_type_hierarchy(self.directory)

    def get_attribute_type_hierarchy(self):
        return get_attribute_type_hierarchy(self.directory)

    def _get_filtered_attribute_type_hierarchy(self, types):
        from copy import deepcopy
        # TODO: This doesn't property implement recursive traversal
        # and filtering, instead only checking the topmost nodes.
        filtered = []
        for t in self.get_attribute_type_hierarchy():
            if t.storage_form() in types:
                filtered.append(deepcopy(t))
        return filtered

    def attributes_for_types(self, types):
        """
        Returns list containing the attribute types that are
        applicable to at least one of the given annotation types.
        """
        # list to preserve order, dict for lookup
        attribute_list = []
        seen = {}
        for t in types:
            for a in self.attributes_for(t):
                if a not in seen:
                    attribute_list.append(a)
                    seen[a] = True
        return attribute_list

    def get_entity_attribute_type_hierarchy(self):
        """
        Returns the attribute type hierarchy filtered to include
        only attributes that apply to at least one entity.
        """
        attr_types = self.attributes_for_types(self.get_entity_types())
        return self._get_filtered_attribute_type_hierarchy(attr_types)

    def get_relation_attribute_type_hierarchy(self):
        """
        Returns the attribute type hierarchy filtered to include
        only attributes that apply to at least one relation.
        """        
        attr_types = self.attributes_for_types(self.get_relation_types())
        return self._get_filtered_attribute_type_hierarchy(attr_types)

    def get_event_attribute_type_hierarchy(self):
        """
        Returns the attribute type hierarchy filtered to include
        only attributes that apply to at least one event.
        """
        attr_types = self.attributes_for_types(self.get_event_types())
        return self._get_filtered_attribute_type_hierarchy(attr_types)

    def preferred_display_form(self, t):
        """
        Given a storage form label, returns the preferred display form
        as defined by the label configuration (labels.conf)
        """
        labels = get_labels_by_storage_form(self.directory, t)
        if labels is None or len(labels) < 1:
            return t
        else:
            return labels[0]

    def is_physical_entity_type(self, t):
        if t in self.get_entity_types() or t in self.get_event_types():
            return t in self.get_entity_types()
        # TODO: remove this temporary hack
        if t in very_likely_physical_entity_types:
            return True
        return t in self.get_entity_types()

    def is_event_type(self, t):
        return t in self.get_event_types()

    def is_relation_type(self, t):
        return t in self.get_relation_types()

    def is_equiv_type(self, t):
        return t in self.get_equiv_types()

    def is_configured_type(self, t):
        return (t in self.get_entity_types() or
                t in self.get_event_types() or
                t in self.get_relation_types())

    def type_category(self, t):
        """
        Returns the category of the given type t.
        The categories can be compared for equivalence but offer
        no other interface.
        """
        if self.is_physical_entity_type(t):
            return ENTITY_CATEGORY
        elif self.is_event_type(t):
            return EVENT_CATEGORY
        elif self.is_relation_type(t):
            return RELATION_CATEGORY
        else:
            # TODO: others
            return UNKNOWN_CATEGORY

########NEW FILE########
__FILENAME__ = realmessage
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Server-to-client messaging-related functionality
for Brat Rapid Annotation Tool (brat)

NOTE: This module is used by ajax.cgi prior to verifying that the Python
version is new enough to run with all our other modules. Thus this module has
to be kept as backwards compatible as possible and this over-rides any
requirements on style otherwise imposed on the project.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Author:     Sampo Pyysalo       <smp is s u-tokyo ac jp>
Version:    2011-05-31
'''

import re

# for cleaning up control chars from a string, from 
# http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
# allow tab (9) and [unix] newline (10)
__control_chars = ''.join(map(unichr, range(0,9) + range(11,32) + range(127,160)))
__control_char_re = re.compile('[%s]' % re.escape(__control_chars))
def remove_control_chars(s):
    return __control_char_re.sub('', s)

class Messager:
    __pending_messages = []

    def info(msg, duration=3, escaped=False):
        Messager.__message(msg, 'comment', duration, escaped)
    # decorator syntax only since python 2.4, staticmethod() since 2.2
    info = staticmethod(info)

    def warning(msg, duration=3, escaped=False):
        Messager.__message(msg, 'warning', duration, escaped)
    warning = staticmethod(warning)

    def error(msg, duration=3, escaped=False):
        Messager.__message(msg, 'error', duration, escaped)
    error = staticmethod(error)

    def debug(msg, duration=3, escaped=False):
        Messager.__message(msg, 'debug', duration, escaped)
    debug = staticmethod(debug)    

    def output(o):
        for m, c, d in Messager.__pending_messages:
            print >> o, c, ":", m
    output = staticmethod(output)

    def output_json(json_dict):
        try:
            return Messager.__output_json(json_dict)
        except Exception, e:
            # TODO: do we want to always give the exception?
            json_dict['messages'] = [['Messager error adding messages to json (internal error in message.py, please contact administrator): %s' % str(e),'error', -1]]
            return json_dict
    output_json = staticmethod(output_json)

    def __output_json(json_dict):
        # protect against non-unicode inputs
        convertable_messages = []
        for m in Messager.__pending_messages:
            try:
                encoded = m[0].encode('utf-8')
                convertable_messages.append(m)
            except UnicodeDecodeError:
                convertable_messages.append((u'[ERROR: MESSAGE THAT CANNOT BE ENCODED AS UTF-8 OMITTED]', 'error', 5))
        Messager.__pending_messages = convertable_messages

        # clean up messages by removing possible control characters
        # that may cause trouble clientside
        cleaned_messages = []
        for s, t, r in Messager.__pending_messages:
            cs = remove_control_chars(s)
            if cs != s:
                s = cs + u'[NOTE: SOME NONPRINTABLE CHARACTERS REMOVED FROM MESSAGE]'
            cleaned_messages.append((s,t,r))
        Messager.__pending_messages = cleaned_messages
        
        # to avoid crowding the interface, combine messages with identical content
        msgcount = {}
        for m in Messager.__pending_messages:
            msgcount[m] = msgcount.get(m, 0) + 1

        merged_messages = []
        for m in Messager.__pending_messages:
            if m in msgcount:
                count = msgcount[m]
                del msgcount[m]
                s, t, r = m
                if count > 1:
                    s = s + '<br/><b>[message repeated %d times]</b>' % count
                merged_messages.append((s,t,r))

        if 'messages' not in json_dict:
            json_dict['messages'] = []
        json_dict['messages'] += merged_messages
        Messager.__pending_messages = []
        return json_dict
    __output_json = staticmethod(__output_json)

    def __escape(msg):
        from cgi import escape
        return escape(msg).replace('\n', '\n<br/>\n')
    __escape = staticmethod(__escape)

    def __message(msg, type, duration, escaped):
        if not isinstance(msg, str) and not isinstance(msg, unicode):
            msg = str(msg)
        if not escaped:
            msg = Messager.__escape(msg)
        Messager.__pending_messages.append((msg, type, duration))
    __message = staticmethod(__message)

if __name__ == '__main__':
    # Try out Unicode, that is always fun
    Messager.warning(u'Hello 世界！')
    json_dic = {}
    Messager.output_json(json_dic)
    print json_dic

########NEW FILE########
__FILENAME__ = sdistance
#!/usr/bin/env python

'''
Various string distance measures.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-08-09
'''

from string import digits, lowercase
from sys import maxint

DIGITS = set(digits)
LOWERCASE = set(lowercase)
TSURUOKA_2004_INS_CHEAP = set((' ', '-', ))
TSURUOKA_2004_DEL_CHEAP = TSURUOKA_2004_INS_CHEAP
TSURUOKA_2004_REPL_CHEAP = set([(a, b) for a in DIGITS for b in DIGITS] +
                               [(a, a.upper()) for a in LOWERCASE] +
                               [(a.upper(), a) for a in LOWERCASE] +
                               [(' ', '-'), ('-', '_')])
# Testing; not sure number replacements should be cheap.
NONNUM_T2004_REPL_CHEAP = set([(a, a.upper()) for a in LOWERCASE] +
                              [(a.upper(), a) for a in LOWERCASE] +
                              [(' ', '-'), ('-', '_')])

TSURUOKA_INS  = dict([(c, 10) for c in TSURUOKA_2004_INS_CHEAP])
TSURUOKA_DEL  = dict([(c, 10) for c in TSURUOKA_2004_DEL_CHEAP])
#TSURUOKA_REPL = dict([(c, 10) for c in TSURUOKA_2004_REPL_CHEAP])
TSURUOKA_REPL = dict([(c, 10) for c in NONNUM_T2004_REPL_CHEAP])

def tsuruoka(a, b):
    # Special case for empties
    if len(a) == 0 or len(b) == 0:
        return 100*max(len(a),len(b))

    # Initialise the first column
    prev_min_col = [0]
    for b_c in b:
        prev_min_col.append(prev_min_col[-1] + TSURUOKA_INS.get(b_c, 100))
    curr_min_col = prev_min_col

    for a_c in a:
        curr_min_col = [prev_min_col[0] + TSURUOKA_DEL.get(a_c, 100)]

        for b_i, b_c in enumerate(b):
            if b_c == a_c:
                curr_min_col.append(prev_min_col[b_i])
            else:
                curr_min_col.append(min(
                    prev_min_col[b_i + 1] + TSURUOKA_DEL.get(a_c, 100),
                    curr_min_col[-1] + TSURUOKA_INS.get(b_c, 100),
                    prev_min_col[b_i] + TSURUOKA_REPL.get((a_c, b_c), 50)
                        ))
        
        prev_min_col = curr_min_col

    return curr_min_col[-1]

def tsuruoka_local(a, b, edge_insert_cost=1, max_cost=maxint):
    # Variant of the tsuruoka metric for local (substring) alignment:
    # penalizes initial or final insertion for a by a different
    # (normally small or zero) cost than middle insertion.
    # If the current cost at any point exceeds max_cost, returns 
    # max_cost, which may allow early return.

    # Special cases for empties
    if len(a) == 0:
        return len(b)*edge_insert_cost
    if len(b) == 0:
        return 100*len(b)

    # Shortcut: strict containment
    if a in b:
        cost = (len(b)-len(a)) * edge_insert_cost
        return cost if cost < max_cost else max_cost

    # Initialise the first column. Any sequence of initial inserts
    # have edge_insert_cost.
    prev_min_col = [0]
    for b_c in b:
        prev_min_col.append(prev_min_col[-1] + edge_insert_cost)
    curr_min_col = prev_min_col

    for a_c in a:
        curr_min_col = [prev_min_col[0] + TSURUOKA_DEL.get(a_c, 100)]

        for b_i, b_c in enumerate(b):
            if b_c == a_c:
                curr_min_col.append(prev_min_col[b_i])
            else:
                curr_min_col.append(min(
                    prev_min_col[b_i + 1] + TSURUOKA_DEL.get(a_c, 100),
                    curr_min_col[-1] + TSURUOKA_INS.get(b_c, 100),
                    prev_min_col[b_i] + TSURUOKA_REPL.get((a_c, b_c), 50)
                        ))

        # early return
        if min(curr_min_col) >= max_cost:
            return max_cost
        
        prev_min_col = curr_min_col

    # Any number of trailing inserts have edge_insert_cost
    min_cost = curr_min_col[-1]
    for i in range(len(curr_min_col)):
        cost = curr_min_col[i] + edge_insert_cost * (len(curr_min_col)-i-1)
        min_cost = min(min_cost, cost)

    if min_cost < max_cost:
        return min_cost
    else:
        return max_cost

def tsuruoka_norm(a, b):
    return 1 - (tsuruoka(a,b) / (max(len(a),len(b)) * 100.))

def levenshtein(a, b):
    # Special case for empties
    if len(a) == 0 or len(b) == 0:
        return max(len(a),len(b))

    # Initialise the first column
    prev_min_col = [0]
    for b_c in b:
        prev_min_col.append(prev_min_col[-1] + 1)
    curr_min_col = prev_min_col

    for a_c in a:
        curr_min_col = [prev_min_col[0] + 1]

        for b_i, b_c in enumerate(b):
            if b_c == a_c:
                curr_min_col.append(prev_min_col[b_i])
            else:
                curr_min_col.append(min(
                    prev_min_col[b_i + 1] + 1,
                    curr_min_col[-1] + 1,
                    prev_min_col[b_i] + 1
                        ))
        
        prev_min_col = curr_min_col

    return curr_min_col[-1]

if __name__ == '__main__':
    for a, b in (('kitten', 'sitting'), ('Saturday', 'Sunday'), ('Caps', 'caps'), ('', 'bar'), ('dog', 'dog'), ('dog', '___dog__'), ('dog', '__d_o_g__')):
        print 'levenshtein', a, b, levenshtein(a,b)
        print 'tsuruoka', a, b, tsuruoka(a,b)
        print 'tsuruoka_local', a, b, tsuruoka_local(a,b)
        print 'tsuruoka_norm', a, b, tsuruoka_norm(a,b)

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Search-related functionality for BioNLP Shared Task - style
# annotations.

from __future__ import with_statement

import re
import annotation

from message import Messager

### Constants
DEFAULT_EMPTY_STRING = "***"
REPORT_SEARCH_TIMINGS = False
DEFAULT_RE_FLAGS = re.UNICODE
###

if REPORT_SEARCH_TIMINGS:
    from sys import stderr
    from datetime import datetime

# Search result number may be restricted to limit server load and
# communication issues for searches in large collections that (perhaps
# unintentionally) result in very large numbers of hits
try:
    from config import MAX_SEARCH_RESULT_NUMBER
except ImportError:
    # unlimited
    MAX_SEARCH_RESULT_NUMBER = -1

# TODO: nested_types restriction not consistently enforced in
# searches.

class SearchMatchSet(object):
    """
    Represents a set of matches to a search. Each match is represented
    as an (ann_obj, ann) pair, where ann_obj is an Annotations object
    an ann an Annotation belonging to the corresponding ann_obj.
    """

    def __init__(self, criterion, matches=None):
        if matches is None:
            matches = []
        self.criterion = criterion
        self.__matches = matches

    def add_match(self, ann_obj, ann):
        self.__matches.append((ann_obj, ann))

    def sort_matches(self):
        # sort by document name
        self.__matches.sort(lambda a,b: cmp(a[0].get_document(),b[0].get_document()))

    def limit_to(self, num):
        # don't limit to less than one match
        if len(self.__matches) > num and num > 0:
            self.__matches = self.__matches[:num]
            return True
        else:
            return False

    # TODO: would be better with an iterator
    def get_matches(self):
        return self.__matches

    def __len__(self):
        return len(self.__matches)

class TextMatch(object):
    """
    Represents a text span matching a query.
    """
    def __init__(self, start, end, text, sentence=None):
        self.start = start
        self.end = end
        self.text = text
        self.sentence = sentence

    def first_start(self):
        # mimic first_start() for TextBoundAnnotation
        return self.start

    def last_end(self):
        # mimic last_end() for TextBoundAnnotation
        return self.end
        
    def reference_id(self):
        # mimic reference_id for annotations
        # this is the form expected by client Util.param()
        return [self.start, self.end]

    def reference_text(self):
        return "%s-%s" % (self.start, self.end)

    def get_text(self):
        return self.text

    def __str__(self):
        # Format like textbound, but w/o ID or type
        return u'%d %d\t%s' % (self.start, self.end, self.text)

# Note search matches need to combine aspects of the note with aspects
# of the annotation it's attached to, so we'll represent such matches
# with this separate class.
class NoteMatch(object):
    """
    Represents a note (comment) matching a query.
    """
    def __init__(self, note, ann, start=0, end=0):
        self.note  = note
        self.ann   = ann
        self.start = start
        self.end   = end

        # for format_results
        self.text  = note.get_text()
        try:
            self.type  = ann.type
        except AttributeError:
            # nevermind
            pass

    def first_start(self):
        return self.start

    def last_end(self):
        return self.end

    def reference_id(self):
        # return reference to annotation that the note is attached to
        # (not the note itself)
        return self.ann.reference_id()

    def reference_text(self):
        # as above
        return self.ann.reference_text()

    def get_text(self):
        return self.note.get_text()

    def __str__(self):
        assert False, "INTERNAL ERROR: not implemented"

def __filenames_to_annotations(filenames):
    """
    Given file names, returns corresponding Annotations objects.
    """
    
    # TODO: error output should be done via messager to allow
    # both command-line and GUI invocations

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    anns = []
    for fn in filenames:
        try:
            # remove suffixes for Annotations to prompt parsing of all
            # annotation files.
            nosuff_fn = fn.replace(".ann","").replace(".a1","").replace(".a2","").replace(".rel","")
            ann_obj = annotation.TextAnnotations(nosuff_fn, read_only=True)
            anns.append(ann_obj)
        except annotation.AnnotationFileNotFoundError:
            print >> sys.stderr, "%s:\tFailed: file not found" % fn
        except annotation.AnnotationNotFoundError, e:
            print >> sys.stderr, "%s:\tFailed: %s" % (fn, e)

    if len(anns) != len(filenames):
        print >> sys.stderr, "Note: only checking %d/%d given files" % (len(anns), len(filenames))

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "filenames_to_annotations: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return anns

def __directory_to_annotations(directory):
    """
    Given a directory, returns Annotations objects for contained files.
    """
    # TODO: put this shared functionality in a more reasonable place
    from document import real_directory,_listdir
    from os.path import join as path_join

    real_dir = real_directory(directory)
    # Get the document names
    base_names = [fn[0:-4] for fn in _listdir(real_dir) if fn.endswith('txt')]

    filenames = [path_join(real_dir, bn) for bn in base_names]

    return __filenames_to_annotations(filenames)

def __document_to_annotations(directory, document):
    """
    Given a directory and a document, returns an Annotations object
    for the file.
    """
    # TODO: put this shared functionality in a more reasonable place
    from document import real_directory
    from os.path import join as path_join

    real_dir = real_directory(directory)
    filenames = [path_join(real_dir, document)]

    return __filenames_to_annotations(filenames)

def __doc_or_dir_to_annotations(directory, document, scope):
    """
    Given a directory, a document, and a scope specification
    with the value "collection" or "document" selecting between
    the two, returns Annotations object for either the specific
    document identified (scope=="document") or all documents in
    the given directory (scope=="collection").
    """

    # TODO: lots of magic values here; try to avoid this

    if scope == "collection":
        return __directory_to_annotations(directory)
    elif scope == "document":
        # NOTE: "/NO-DOCUMENT/" is a workaround for a brat
        # client-server comm issue (issue #513).
        if document == "" or document == "/NO-DOCUMENT/":
            Messager.warning('No document selected for search in document.')
            return []
        else:
            return __document_to_annotations(directory, document)
    else:
        Messager.error('Unrecognized search scope specification %s' % scope)
        return []

def _get_text_type_ann_map(ann_objs, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Helper function for search. Given annotations, returns a
    dict-of-dicts, outer key annotation text, inner type, values
    annotation objects.
    """

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types
    nested_types   = [] if nested_types is None else nested_types

    text_type_ann_map = {}
    for ann_obj in ann_objs:
        for t in ann_obj.get_textbounds():
            if t.type in ignore_types:
                continue
            if restrict_types != [] and t.type not in restrict_types:
                continue

            if t.text not in text_type_ann_map:
                text_type_ann_map[t.text] = {}
            if t.type not in text_type_ann_map[t.text]:
                text_type_ann_map[t.text][t.type] = []
            text_type_ann_map[t.text][t.type].append((ann_obj,t))

    return text_type_ann_map

def _get_offset_ann_map(ann_objs, restrict_types=None, ignore_types=None):
    """
    Helper function for search. Given annotations, returns a dict
    mapping offsets in text into the set of annotations spanning each
    offset.
    """

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types

    offset_ann_map = {}
    for ann_obj in ann_objs:
        for t in ann_obj.get_textbounds():
            if t.type in ignore_types:
                continue
            if restrict_types != [] and t.type not in restrict_types:
                continue

            for t_start, t_end in t.spans:
                for o in range(t_start, t_end):
                    if o not in offset_ann_map:
                        offset_ann_map[o] = set()
                    offset_ann_map[o].add(t)

    return offset_ann_map

def eq_text_neq_type_spans(ann_objs, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for annotated spans that match in string content but
    disagree in type in given Annotations objects.
    """

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types
    nested_types   = [] if nested_types is None else nested_types

    # TODO: nested_types constraints not applied

    matches = SearchMatchSet("Text marked with different types")

    text_type_ann_map = _get_text_type_ann_map(ann_objs, restrict_types, ignore_types, nested_types)
    
    for text in text_type_ann_map:
        if len(text_type_ann_map[text]) < 2:
            # all matching texts have same type, OK
            continue

        types = text_type_ann_map[text].keys()
        # avoiding any() etc. to be compatible with python 2.4
        if restrict_types != [] and len([t for t in types if t in restrict_types]) == 0:
            # Does not involve any of the types restricted do
            continue

        # debugging
        #print >> sys.stderr, "Text marked with %d different types:\t%s\t: %s" % (len(text_type_ann_map[text]), text, ", ".join(["%s (%d occ.)" % (type, len(text_type_ann_map[text][type])) for type in text_type_ann_map[text]]))
        for type in text_type_ann_map[text]:
            for ann_obj, ann in text_type_ann_map[text][type]:
                # debugging
                #print >> sys.stderr, "\t%s %s" % (ann.source_id, ann)
                matches.add_match(ann_obj, ann)

    return matches

def _get_offset_sentence_map(s):
    """
    Helper, sentence-splits and returns a mapping from character
    offsets to sentence number.
    """
    from ssplit import regex_sentence_boundary_gen

    m = {} # TODO: why is this a dict and not an array?
    sprev, snum = 0, 1 # note: sentences indexed from 1
    for sstart, send in regex_sentence_boundary_gen(s):
        # if there are extra newlines (i.e. more than one) in between
        # the previous end and the current start, those need to be
        # added to the sentence number
        snum += max(0,len([nl for nl in s[sprev:sstart] if nl == "\n"]) - 1)
        for o in range(sprev, send):
            m[o] = snum
        sprev = send
        snum += 1
    return m

def _split_and_tokenize(s):
    """
    Helper, sentence-splits and tokenizes, returns array comparable to
    what you would get from re.split(r'(\s+)', s).
    """
    from ssplit import regex_sentence_boundary_gen
    from tokenise import gtb_token_boundary_gen

    tokens = []

    sprev = 0
    for sstart, send in regex_sentence_boundary_gen(s):
        if sprev != sstart:
            # between-sentence space
            tokens.append(s[sprev:sstart])
        stext = s[sstart:send]
        tprev, tend = 0, 0
        for tstart, tend in gtb_token_boundary_gen(stext):
            if tprev != tstart:
                # between-token space
                tokens.append(s[sstart+tprev:sstart+tstart])
            tokens.append(s[sstart+tstart:sstart+tend])
            tprev = tend

        if tend != len(stext):
            # sentence-final space
            tokens.append(stext[tend:])

        sprev = send

    if sprev != len(s):
        # document-final space
        tokens.append(s[sprev:])

    assert "".join(tokens) == s, "INTERNAL ERROR\n'%s'\n'%s'" % ("".join(tokens),s)

    return tokens

def _split_tokens_more(tokens):
    """
    Search-specific extra tokenization.
    More aggressive than the general visualization-oriented tokenization.
    """
    pre_nonalnum_RE = re.compile(r'^(\W+)(.+)$', flags=DEFAULT_RE_FLAGS)
    post_nonalnum_RE = re.compile(r'^(.+?)(\W+)$', flags=DEFAULT_RE_FLAGS)

    new_tokens = []
    for t in tokens:
        m = pre_nonalnum_RE.match(t)
        if m:
            pre, t = m.groups()
            new_tokens.append(pre)
        m = post_nonalnum_RE.match(t)
        if m:
            t, post = m.groups()
            new_tokens.append(t)
            new_tokens.append(post)
        else:
            new_tokens.append(t)

    # sanity
    assert ''.join(tokens) == ''.join(new_tokens), "INTERNAL ERROR"
    return new_tokens
        
def eq_text_partially_marked(ann_objs, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for spans that match in string content but are not all
    marked.
    """

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types
    nested_types   = [] if nested_types is None else nested_types

    # TODO: check that constraints are properly applied

    matches = SearchMatchSet("Text marked partially")

    text_type_ann_map = _get_text_type_ann_map(ann_objs, restrict_types, ignore_types, nested_types)

    max_length_tagged = max([len(s) for s in text_type_ann_map]+[0])

    # TODO: faster and less hacky way to detect missing annotations
    text_untagged_map = {}
    for ann_obj in ann_objs:
        doctext = ann_obj.get_document_text()

        # TODO: proper tokenization.
        # NOTE: this will include space.
        #tokens = re.split(r'(\s+)', doctext)
        try:
            tokens = _split_and_tokenize(doctext)
            tokens = _split_tokens_more(tokens)
        except:
            # TODO: proper error handling
            print >> sys.stderr, "ERROR: failed tokenization in %s, skipping" % ann_obj._input_files[0]
            continue

        # document-specific map
        offset_ann_map = _get_offset_ann_map([ann_obj])

        # this one too
        sentence_num = _get_offset_sentence_map(doctext)

        start_offset = 0
        for start in range(len(tokens)):
            for end in range(start, len(tokens)):
                s = "".join(tokens[start:end])                
                end_offset = start_offset + len(s)

                if len(s) > max_length_tagged:
                    # can't hit longer strings, none tagged
                    break

                if s not in text_type_ann_map:
                    # consistently untagged
                    continue

                # Some matching is tagged; this is considered
                # inconsistent (for this check) if the current span
                # has no fully covering tagging. Note that type
                # matching is not considered here.
                start_spanning = offset_ann_map.get(start_offset, set())
                end_spanning = offset_ann_map.get(end_offset-1, set()) # NOTE: -1 needed, see _get_offset_ann_map()
                if len(start_spanning & end_spanning) == 0:
                    if s not in text_untagged_map:
                        text_untagged_map[s] = []
                    text_untagged_map[s].append((ann_obj, start_offset, end_offset, s, sentence_num[start_offset]))

            start_offset += len(tokens[start])

    # form match objects, grouping by text
    for text in text_untagged_map:
        assert text in text_type_ann_map, "INTERNAL ERROR"

        # collect tagged and untagged cases for "compressing" output
        # in cases where one is much more common than the other
        tagged   = []
        untagged = []

        for type_ in text_type_ann_map[text]:
            for ann_obj, ann in text_type_ann_map[text][type_]:
                #matches.add_match(ann_obj, ann)
                tagged.append((ann_obj, ann))

        for ann_obj, start, end, s, snum in text_untagged_map[text]:
            # TODO: need a clean, standard way of identifying a text span
            # that does not involve an annotation; this is a bit of a hack
            tm = TextMatch(start, end, s, snum)
            #matches.add_match(ann_obj, tm)
            untagged.append((ann_obj, tm))

        # decide how to output depending on relative frequency
        freq_ratio_cutoff = 3
        cutoff_limit = 5

        if (len(tagged) > freq_ratio_cutoff * len(untagged) and 
            len(tagged) > cutoff_limit):
            # cut off all but cutoff_limit from tagged
            for ann_obj, m in tagged[:cutoff_limit]:
                matches.add_match(ann_obj, m)
            for ann_obj, m in untagged:
                matches.add_match(ann_obj, m)
            print "(note: omitting %d instances of tagged '%s')" % (len(tagged)-cutoff_limit, text.encode('utf-8'))
        elif (len(untagged) > freq_ratio_cutoff * len(tagged) and
              len(untagged) > cutoff_limit):
            # cut off all but cutoff_limit from tagged
            for ann_obj, m in tagged:
                matches.add_match(ann_obj, m)
            for ann_obj, m in untagged[:cutoff_limit]:
                matches.add_match(ann_obj, m)
            print "(note: omitting %d instances of untagged '%s')" % (len(untagged)-cutoff_limit, text.encode('utf-8'))
        else:
            # include all
            for ann_obj, m in tagged + untagged:
                matches.add_match(ann_obj, m)
            
    
    return matches

def check_type_consistency(ann_objs, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for inconsistent types in given Annotations
    objects.  Returns a list of SearchMatchSet objects, one for each
    checked criterion that generated matches for the search.
    """

    match_sets = []

    m = eq_text_neq_type_spans(ann_objs, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types)
    if len(m) != 0:
        match_sets.append(m)

    return match_sets


def check_missing_consistency(ann_objs, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for potentially missing annotations in given Annotations
    objects.  Returns a list of SearchMatchSet objects, one for each
    checked criterion that generated matches for the search.
    """

    match_sets = []

    m = eq_text_partially_marked(ann_objs, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types)
    if len(m) != 0:
        match_sets.append(m)

    return match_sets

def _get_match_regex(text, text_match="word", match_case=False,
                     whole_string=False):
    """
    Helper for the various search_anns_for_ functions.
    """

    regex_flags = DEFAULT_RE_FLAGS
    if not match_case:
        regex_flags = regex_flags | re.IGNORECASE

    if text is None:
        text = ''
    # interpret special value standing in for empty string (#924)
    if text == DEFAULT_EMPTY_STRING:
        text = ''

    if text_match == "word":
        # full word match: require word boundaries or, optionally,
        # whole string boundaries
        if whole_string:
            return re.compile(r'^'+re.escape(text)+r'$', regex_flags)
        else:
            return re.compile(r'\b'+re.escape(text)+r'\b', regex_flags)
    elif text_match == "substring":
        # any substring match, as text (nonoverlapping matches)
        return re.compile(re.escape(text), regex_flags)
    elif text_match == "regex":
        try:
            return re.compile(text, regex_flags)
        except: # whatever (sre_constants.error, other?)
            Messager.warning('Given string "%s" is not a valid regular expression.' % text)
            return None        
    else:
        Messager.error('Unrecognized search match specification "%s"' % text_match)
        return None    

def search_anns_for_textbound(ann_objs, text, restrict_types=None, 
                              ignore_types=None, nested_types=None, 
                              text_match="word", match_case=False,
                              entities_only=False):
    """
    Searches for the given text in the Textbound annotations in the
    given Annotations objects.  Returns a SearchMatchSet object.
    """

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types
    nested_types   = [] if nested_types is None else nested_types

    description = "Textbounds containing text '%s'" % text
    if restrict_types != []:
        description = description + ' (of type %s)' % (",".join(restrict_types))
    if nested_types != []:
        description = description + ' (nesting annotation of type %s)' % (",".join(nested_types))
    matches = SearchMatchSet(description)

    # compile a regular expression according to arguments for matching
    match_regex = _get_match_regex(text, text_match, match_case)

    if match_regex is None:
        # something went wrong, return empty
        return matches

    for ann_obj in ann_objs:
        # collect per-document (ann_obj) for sorting
        ann_matches = []

        if entities_only:
            candidates = ann_obj.get_textbounds()
        else:
            candidates = ann_obj.get_entities()

        for t in candidates:
            if t.type in ignore_types:
                continue
            if restrict_types != [] and t.type not in restrict_types:
                continue
            if (text != None and text != "" and 
                text != DEFAULT_EMPTY_STRING and not match_regex.search(t.get_text())):
                continue
            if nested_types != []:
                # TODO: massively inefficient
                nested = [x for x in ann_obj.get_textbounds() 
                          if x != t and t.contains(x)]
                if len([x for x in nested if x.type in nested_types]) == 0:
                    continue

            ann_matches.append(t)

        # sort by start offset
        ann_matches.sort(lambda a,b: cmp((a.first_start(),-a.last_end()),
                                         (b.first_start(),-b.last_end())))

        # add to overall collection
        for t in ann_matches:
            matches.add_match(ann_obj, t)    

        # MAX_SEARCH_RESULT_NUMBER <= 0 --> no limit
        if len(matches) > MAX_SEARCH_RESULT_NUMBER and MAX_SEARCH_RESULT_NUMBER > 0:
            Messager.warning('Search result limit (%d) exceeded, stopping search.' % MAX_SEARCH_RESULT_NUMBER)
            break

    matches.limit_to(MAX_SEARCH_RESULT_NUMBER)

    # sort by document name for output
    matches.sort_matches()

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "search_anns_for_textbound: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return matches

def search_anns_for_note(ann_objs, text, category,
                         restrict_types=None, ignore_types=None,
                         text_match="word", match_case=False):
    """
    Searches for the given text in the comment annotations in the
    given Annotations objects.  Returns a SearchMatchSet object.
    """

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types

    if category is not None:
        description = "Comments on %s containing text '%s'" % (category, text)
    else:
        description = "Comments containing text '%s'" % text
    if restrict_types != []:
        description = description + ' (of type %s)' % (",".join(restrict_types))
    matches = SearchMatchSet(description)

    # compile a regular expression according to arguments for matching
    match_regex = _get_match_regex(text, text_match, match_case)

    if match_regex is None:
        # something went wrong, return empty
        return matches

    for ann_obj in ann_objs:
        # collect per-document (ann_obj) for sorting
        ann_matches = []

        candidates = ann_obj.get_oneline_comments()

        for n in candidates:
            a = ann_obj.get_ann_by_id(n.target)

            if a.type in ignore_types:
                continue
            if restrict_types != [] and a.type not in restrict_types:
                continue
            if (text != None and text != "" and 
                text != DEFAULT_EMPTY_STRING and not match_regex.search(n.get_text())):
                continue

            ann_matches.append(NoteMatch(n,a))

        ann_matches.sort(lambda a,b: cmp((a.first_start(),-a.last_end()),
                                         (b.first_start(),-b.last_end())))

        # add to overall collection
        for t in ann_matches:
            matches.add_match(ann_obj, t)    

        # MAX_SEARCH_RESULT_NUMBER <= 0 --> no limit
        if len(matches) > MAX_SEARCH_RESULT_NUMBER and MAX_SEARCH_RESULT_NUMBER > 0:
            Messager.warning('Search result limit (%d) exceeded, stopping search.' % MAX_SEARCH_RESULT_NUMBER)
            break

    matches.limit_to(MAX_SEARCH_RESULT_NUMBER)

    # sort by document name for output
    matches.sort_matches()

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "search_anns_for_textbound: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return matches

def search_anns_for_relation(ann_objs, arg1, arg1type, arg2, arg2type, 
                             restrict_types=None, ignore_types=None, 
                             text_match="word", match_case=False):
    """
    Searches the given Annotations objects for relation annotations
    matching the given specification. Returns a SearchMatchSet object.
    """

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types

    # TODO: include args in description
    description = "Relations"
    if restrict_types != []:
        description = description + ' (of type %s)' % (",".join(restrict_types))
    matches = SearchMatchSet(description)

    # compile regular expressions according to arguments for matching
    arg1_match_regex, arg2_match_regex = None, None
    if arg1 is not None:
        arg1_match_regex = _get_match_regex(arg1, text_match, match_case)
    if arg2 is not None:
        arg2_match_regex = _get_match_regex(arg2, text_match, match_case)

    if ((arg1 is not None and arg1_match_regex is None) or
        (arg2 is not None and arg2_match_regex is None)):
        # something went wrong, return empty
        return matches
    
    for ann_obj in ann_objs:
        # collect per-document (ann_obj) for sorting
        ann_matches = []
        
        # binary relations and equivs need to be treated separately due
        # to different structure (not a great design there)
        for r in ann_obj.get_relations():
            if r.type in ignore_types:
                continue
            if restrict_types != [] and r.type not in restrict_types:
                continue

            # argument constraints
            if arg1 is not None or arg1type is not None:
                arg1ent = ann_obj.get_ann_by_id(r.arg1)
                if arg1 is not None and not arg1_match_regex.search(arg1ent.get_text()):
                    continue
                if arg1type is not None and arg1type != arg1ent.type:
                    continue
            if arg2 is not None or arg2type is not None:
                arg2ent = ann_obj.get_ann_by_id(r.arg2)
                if arg2 is not None and not arg2_match_regex.search(arg2ent.get_text()):
                    continue
                if arg2type is not None and arg2type != arg2ent.type:
                    continue
                
            ann_matches.append(r)

        for r in ann_obj.get_equivs():
            if r.type in ignore_types:
                continue
            if restrict_types != [] and r.type not in restrict_types:
                continue

            # argument constraints. This differs from that for non-equiv
            # for relations as equivs are symmetric, so the arg1-arg2
            # distinction can be ignored.

            # TODO: this can match the same thing twice, which most
            # likely isn't what a user expects: for example, having
            # 'Protein' for both arg1type and arg2type can still match
            # an equiv between 'Protein' and 'Gene'.
            match_found = False
            for arg, argtype, arg_match_regex in ((arg1, arg1type, arg1_match_regex), 
                                                  (arg2, arg2type, arg2_match_regex)):
                match_found = False
                for aeid in r.entities:
                    argent = ann_obj.get_ann_by_id(aeid)
                    if arg is not None and not arg_match_regex.search(argent.get_text()):
                        continue
                    if argtype is not None and argtype != argent.type:
                        continue
                    match_found = True
                    break
                if not match_found:
                    break
            if not match_found:
                continue

            ann_matches.append(r)

        # TODO: sort, e.g. by offset of participant occurring first
        #ann_matches.sort(lambda a,b: cmp(???))

        # add to overall collection
        for r in ann_matches:
            matches.add_match(ann_obj, r)

        # MAX_SEARCH_RESULT_NUMBER <= 0 --> no limit
        if len(matches) > MAX_SEARCH_RESULT_NUMBER and MAX_SEARCH_RESULT_NUMBER > 0:
            Messager.warning('Search result limit (%d) exceeded, stopping search.' % MAX_SEARCH_RESULT_NUMBER)
            break

    matches.limit_to(MAX_SEARCH_RESULT_NUMBER)

    # sort by document name for output
    matches.sort_matches()

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "search_anns_for_relation: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return matches

def search_anns_for_event(ann_objs, trigger_text, args, 
                          restrict_types=None, ignore_types=None, 
                          text_match="word", match_case=False):
    """
    Searches the given Annotations objects for Event annotations
    matching the given specification. Returns a SearchMatchSet object.
    """

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types

    # TODO: include args in description
    description = "Event triggered by text containing '%s'" % trigger_text
    if restrict_types != []:
        description = description + ' (of type %s)' % (",".join(restrict_types))
    matches = SearchMatchSet(description)

    # compile a regular expression according to arguments for matching
    if trigger_text is not None:
        trigger_match_regex = _get_match_regex(trigger_text, text_match, match_case)

        if trigger_match_regex is None:
            # something went wrong, return empty
            return matches
    
    for ann_obj in ann_objs:
        # collect per-document (ann_obj) for sorting
        ann_matches = []

        for e in ann_obj.get_events():
            if e.type in ignore_types:
                continue
            if restrict_types != [] and e.type not in restrict_types:
                continue

            try:
                t_ann = ann_obj.get_ann_by_id(e.trigger)
            except:
                # TODO: specific exception
                Messager.error('Failed to retrieve trigger annotation %s, skipping event %s in search' % (e.trigger, e.id))            

            # TODO: make options for "text included" vs. "text matches"
            if (trigger_text != None and trigger_text != "" and 
                trigger_text != DEFAULT_EMPTY_STRING and 
                not trigger_match_regex.search(t_ann.text)):
                continue

            # interpret unconstrained (all blank values) argument
            # "constraints" as no constraint
            arg_constraints = []
            for arg in args:
                if arg['role'] != '' or arg['type'] != '' or arg['text'] != '':
                    arg_constraints.append(arg)
            args = arg_constraints

            # argument constraints, if any
            if len(args) > 0:
                missing_match = False
                for arg in args:
                    for s in ('role', 'type', 'text'):
                        assert s in arg, "Error: missing mandatory field '%s' in event search" % s
                    found_match = False
                    for role, aid in e.args:

                        if arg['role'] is not None and arg['role'] != '' and arg['role'] != role:
                            # mismatch on role
                            continue

                        arg_ent = ann_obj.get_ann_by_id(aid)
                        if (arg['type'] is not None and arg['type'] != '' and 
                            arg['type'] != arg_ent.type):
                            # mismatch on type
                            continue

                        if (arg['text'] is not None and arg['text'] != ''):
                            # TODO: it would be better to pre-compile regexs for
                            # all arguments with text constraints
                            match_regex = _get_match_regex(arg['text'], text_match, match_case)
                            if match_regex is None:
                                return matches
                            # TODO: there has to be a better way ...
                            if isinstance(arg_ent, annotation.EventAnnotation):
                                # compare against trigger text
                                text_ent = ann_obj.get_ann_by_id(ann_ent.trigger)
                            else:
                                # compare against entity text
                                text_ent = arg_ent
                            if not match_regex.search(text_ent.get_text()):
                                # mismatch on text
                                continue

                        found_match = True
                        break
                    if not found_match:
                        missing_match = True
                        break
                if missing_match:
                    continue

            ann_matches.append((t_ann, e))

        # sort by trigger start offset
        ann_matches.sort(lambda a,b: cmp((a[0].first_start(),-a[0].last_end()),
                                         (b[0].first_start(),-b[0].last_end())))

        # add to overall collection
        for t_obj, e in ann_matches:
            matches.add_match(ann_obj, e)

        # MAX_SEARCH_RESULT_NUMBER <= 0 --> no limit
        if len(matches) > MAX_SEARCH_RESULT_NUMBER and MAX_SEARCH_RESULT_NUMBER > 0:
            Messager.warning('Search result limit (%d) exceeded, stopping search.' % MAX_SEARCH_RESULT_NUMBER)
            break

    matches.limit_to(MAX_SEARCH_RESULT_NUMBER)

    # sort by document name for output
    matches.sort_matches()

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "search_anns_for_event: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return matches

def search_anns_for_text(ann_objs, text, 
                         restrict_types=None, ignore_types=None, nested_types=None, 
                         text_match="word", match_case=False):
    """
    Searches for the given text in the document texts of the given
    Annotations objects.  Returns a SearchMatchSet object.
    """

    global REPORT_SEARCH_TIMINGS
    if REPORT_SEARCH_TIMINGS:
        process_start = datetime.now()

    # treat None and empty list uniformly
    restrict_types = [] if restrict_types is None else restrict_types
    ignore_types   = [] if ignore_types is None else ignore_types
    nested_types   = [] if nested_types is None else nested_types

    description = "Text matching '%s'" % text
    if restrict_types != []:
        description = description + ' (embedded in %s)' % (",".join(restrict_types))
    if ignore_types != []:
        description = description + ' (not embedded in %s)' % ",".join(ignore_types)    
    matches = SearchMatchSet(description)

    # compile a regular expression according to arguments for matching
    match_regex = _get_match_regex(text, text_match, match_case)

    if match_regex is None:
        # something went wrong, return empty
        return matches

    # main search loop
    for ann_obj in ann_objs:
        doctext = ann_obj.get_document_text()

        for m in match_regex.finditer(doctext):
            # only need to care about embedding annotations if there's
            # some annotation-based restriction
            #if restrict_types == [] and ignore_types == []:
            # TODO: _extremely_ naive and slow way to find embedding
            # annotations.  Use some reasonable data structure
            # instead.
            embedding = []
            # if there are no type restrictions, we can skip this bit
            if restrict_types != [] or ignore_types != []:
                for t in ann_obj.get_textbounds():
                    if t.contains(m):
                        embedding.append(t)

            # Note interpretation of ignore_types here: if the text
            # span is embedded in one or more of the ignore_types or
            # the ignore_types include the special value "ANY", the
            # match is ignored.
            if len([e for e in embedding if e.type in ignore_types or "ANY" in ignore_types]) != 0:
                continue

            if restrict_types != [] and len([e for e in embedding if e.type in restrict_types]) == 0:
                continue

            # TODO: need a clean, standard way of identifying a text span
            # that does not involve an annotation; this is a bit of a hack
            tm = TextMatch(m.start(), m.end(), m.group())
            matches.add_match(ann_obj, tm)

        # MAX_SEARCH_RESULT_NUMBER <= 0 --> no limit
        if len(matches) > MAX_SEARCH_RESULT_NUMBER and MAX_SEARCH_RESULT_NUMBER > 0:
            Messager.warning('Search result limit (%d) exceeded, stopping search.' % MAX_SEARCH_RESULT_NUMBER)
            break

    matches.limit_to(MAX_SEARCH_RESULT_NUMBER)

    if REPORT_SEARCH_TIMINGS:
        process_delta = datetime.now() - process_start
        print >> stderr, "search_anns_for_text: processed in", str(process_delta.seconds)+"."+str(process_delta.microseconds/10000), "seconds"

    return matches

def _get_arg_n(ann_obj, ann, n):
    # helper for format_results, normalizes over BinaryRelationAnnotation
    # arg1, arg2 and EquivAnnotation entities[0], entities[1], ...
    # return None if argument n is not available for any reason.

    try:
        return ann_obj.get_ann_by_id(ann.entities[n]) # Equiv?
    except annotation.AnnotationNotFoundError:
        return None
    except IndexError:
        return None
    except AttributeError:
        pass # not Equiv

    try:
        if n == 0:
            return ann_obj.get_ann_by_id(ann.arg1)
        elif n == 1:
            return ann_obj.get_ann_by_id(ann.arg2)
        else:
            return None
    except AttributeError:
        return None

def format_results(matches, concordancing=False, context_length=50,
                   include_argument_text=False, include_argument_type=False):
    """
    Given matches to a search (a SearchMatchSet), formats the results
    for the client, returning a dictionary with the results in the
    expected format.
    """
    # decided to give filename only, remove this bit if the decision
    # sticks
#     from document import relative_directory
    from os.path import basename

    # sanity
    if concordancing:
        try:
            context_length = int(context_length)
            assert context_length > 0, "format_results: invalid context length ('%s')" % str(context_length)
        except:
            # whatever goes wrong ...
            Messager.warning('Context length should be an integer larger than zero.')
            return {}            

    # the search response format is built similarly to that of the
    # directory listing.

    response = {}

    # fill in header for search result browser
    response['header'] = [('Document', 'string'), 
                          ('Annotation', 'string')]

    # determine which additional fields can be shown; depends on the
    # type of the results

    # TODO: this is much uglier than necessary, revise
    include_type = True
    try:
        for ann_obj, ann in matches.get_matches():
            ann.type
    except AttributeError:
        include_type = False

    include_text = True
    try:
        for ann_obj, ann in matches.get_matches():
            ann.text
    except AttributeError:
        include_text = False

    include_trigger_text = True
    try:
        for ann_obj, ann in matches.get_matches():
            ann.trigger
    except AttributeError:
        include_trigger_text = False

    include_context = False
    if include_text and concordancing:
        include_context = True
        try:
            for ann_obj, ann in matches.get_matches():
                ann.first_start()
                ann.last_end()
        except AttributeError:
            include_context = False

    include_trigger_context = False
    if include_trigger_text and concordancing and not include_context:
        include_trigger_context = True
        try:
            for ann_obj, ann in matches.get_matches():
                trigger = ann_obj.get_ann_by_id(ann.trigger)
                trigger.first_start()
                trigger.last_end()
        except AttributeError:
            include_trigger_context = False

    if include_argument_text:
        try:
            for ann_obj, ann in matches.get_matches():
                _get_arg_n(ann_obj, ann, 0).text
                _get_arg_n(ann_obj, ann, 1).text
        except AttributeError:
            include_argument_text = False

    if include_argument_type:
        try:
            for ann_obj, ann in matches.get_matches():
                _get_arg_n(ann_obj, ann, 0).type
                _get_arg_n(ann_obj, ann, 1).type
        except AttributeError:
            include_argument_type = False

    # extend header fields in order of data fields
    if include_type:
        response['header'].append(('Type', 'string'))

    if include_context or include_trigger_context:
        # right-aligned string
        response['header'].append(('Left context', 'string-reverse'))

    if include_text:
        # center-align text when concordancing, default otherwise
        if include_context or include_trigger_context:
            response['header'].append(('Text', 'string-center'))
        else:
            response['header'].append(('Text', 'string'))

    if include_trigger_text:
        response['header'].append(('Trigger text', 'string'))

    if include_context or include_trigger_context:
        response['header'].append(('Right context', 'string'))

    if include_argument_type:
        response['header'].append(('Arg1 type', 'string'))
        response['header'].append(('Arg2 type', 'string'))

    if include_argument_text:
        response['header'].append(('Arg1 text', 'string'))
        response['header'].append(('Arg2 text', 'string'))

    # gather sets of reference IDs by document to highlight
    # all matches in a document at once
    matches_by_doc = {}
    for ann_obj, ann in matches.get_matches():
        docid = basename(ann_obj.get_document())

        if docid not in matches_by_doc:
            matches_by_doc[docid] = []

        matches_by_doc[docid].append(ann.reference_id())

    # fill in content
    items = []
    for ann_obj, ann in matches.get_matches():
        # First value ("a") signals that the item points to a specific
        # annotation, not a collection (directory) or document.
        # second entry is non-listed "pointer" to annotation
        docid = basename(ann_obj.get_document())

        # matches in the same doc other than the focus match
        other_matches = [rid for rid in matches_by_doc[docid] 
                         if rid != ann.reference_id()]

        items.append(["a", { 'matchfocus' : [ann.reference_id()],
                             'match' : other_matches,
                             }, 
                      docid, ann.reference_text()])

        if include_type:
            items[-1].append(ann.type)

        if include_context:
            context_ann = ann
        elif include_trigger_context:
            context_ann = ann_obj.get_ann_by_id(ann.trigger)
        else:
            context_ann = None

        if context_ann is not None:
            # left context
            start = max(context_ann.first_start() - context_length, 0)
            doctext = ann_obj.get_document_text()
            items[-1].append(doctext[start:context_ann.first_start()])

        if include_text:
            items[-1].append(ann.text)

        if include_trigger_text:
            try:
                items[-1].append(ann_obj.get_ann_by_id(ann.trigger).text)
            except:
                # TODO: specific exception
                items[-1].append("(ERROR)")

        if context_ann is not None:
            # right context
            end = min(context_ann.last_end() + context_length, 
                      len(ann_obj.get_document_text()))
            doctext = ann_obj.get_document_text()
            items[-1].append(doctext[context_ann.last_end():end])

        if include_argument_type:
            items[-1].append(_get_arg_n(ann_obj, ann, 0).type)
            items[-1].append(_get_arg_n(ann_obj, ann, 1).type)

        if include_argument_text:
            items[-1].append(_get_arg_n(ann_obj, ann, 0).text)
            items[-1].append(_get_arg_n(ann_obj, ann, 1).text)

    response['items'] = items
    return response

### brat interface functions ###

def _to_bool(s):
    """
    Given a bool or a string representing a boolean value sent over
    JSON, returns the corresponding bool.
    """
    if s is True or s is False:
        return s
    elif s == "true":
        return True
    elif s == "false":
        return False
    else:
        assert False, "Error: '%s' is not bool or JSON boolean" % str(s)

def search_text(collection, document, scope="collection",
                concordancing="false", context_length=50,
                text_match="word", match_case="false",
                text=""):

    directory = collection

    # Interpret JSON booleans
    concordancing = _to_bool(concordancing)
    match_case = _to_bool(match_case)

    ann_objs = __doc_or_dir_to_annotations(directory, document, scope)    

    matches = search_anns_for_text(ann_objs, text, 
                                   text_match=text_match, 
                                   match_case=match_case)
        
    results = format_results(matches, concordancing, context_length)
    results['collection'] = directory
    
    return results

def search_entity(collection, document, scope="collection",
                  concordancing="false", context_length=50,
                  text_match="word", match_case="false",
                  type=None, text=DEFAULT_EMPTY_STRING):

    directory = collection

    # Interpret JSON booleans
    concordancing = _to_bool(concordancing)
    match_case = _to_bool(match_case)

    ann_objs = __doc_or_dir_to_annotations(directory, document, scope)

    restrict_types = []
    if type is not None and type != "":
        restrict_types.append(type)

    matches = search_anns_for_textbound(ann_objs, text, 
                                        restrict_types=restrict_types, 
                                        text_match=text_match,
                                        match_case=match_case)
        
    results = format_results(matches, concordancing, context_length)
    results['collection'] = directory
    
    return results

def search_note(collection, document, scope="collection",
                concordancing="false", context_length=50,
                text_match="word", match_case="false",
                category=None, type=None, text=DEFAULT_EMPTY_STRING):

    directory = collection

    # Interpret JSON booleans
    concordancing = _to_bool(concordancing)
    match_case = _to_bool(match_case)

    ann_objs = __doc_or_dir_to_annotations(directory, document, scope)

    restrict_types = []
    if type is not None and type != "":
        restrict_types.append(type)

    matches = search_anns_for_note(ann_objs, text, category,
                                   restrict_types=restrict_types, 
                                   text_match=text_match,
                                   match_case=match_case)
        
    results = format_results(matches, concordancing, context_length)
    results['collection'] = directory
    
    return results

def search_event(collection, document, scope="collection",
                 concordancing="false", context_length=50,
                 text_match="word", match_case="false",
                 type=None, trigger=DEFAULT_EMPTY_STRING, args={}):

    directory = collection

    # Interpret JSON booleans
    concordancing = _to_bool(concordancing)
    match_case = _to_bool(match_case)

    ann_objs = __doc_or_dir_to_annotations(directory, document, scope)

    restrict_types = []
    if type is not None and type != "":
        restrict_types.append(type)

    # to get around lack of JSON object parsing in dispatcher, parse
    # args here. 
    # TODO: parse JSON in dispatcher; this is far from the right place to do this..
    from jsonwrap import loads
    args = loads(args)

    matches = search_anns_for_event(ann_objs, trigger, args, 
                                    restrict_types=restrict_types,
                                    text_match=text_match, 
                                    match_case=match_case)

    results = format_results(matches, concordancing, context_length)
    results['collection'] = directory
    
    return results

def search_relation(collection, document, scope="collection", 
                    concordancing="false", context_length=50,
                    text_match="word", match_case="false",
                    type=None, arg1=None, arg1type=None, 
                    arg2=None, arg2type=None,
                    show_text=False, show_type=False):

    directory = collection

    # Interpret JSON booleans
    concordancing = _to_bool(concordancing)
    match_case = _to_bool(match_case)
    show_text = _to_bool(show_text)
    show_type = _to_bool(show_type)
    
    ann_objs = __doc_or_dir_to_annotations(directory, document, scope)

    restrict_types = []
    if type is not None and type != "":
        restrict_types.append(type)

    matches = search_anns_for_relation(ann_objs, arg1, arg1type,
                                       arg2, arg2type,
                                       restrict_types=restrict_types,
                                       text_match=text_match,
                                       match_case=match_case)

    results = format_results(matches, concordancing, context_length,
                             show_text, show_type)
    results['collection'] = directory
    
    return results

### filename list interface functions (e.g. command line) ###

def search_files_for_text(filenames, text, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for the given text in the given set of files.
    """
    anns = __filenames_to_annotations(filenames)
    return search_anns_for_text(anns, text, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types)

def search_files_for_textbound(filenames, text, restrict_types=None, ignore_types=None, nested_types=None, entities_only=False):
    """
    Searches for the given text in textbound annotations in the given
    set of files.
    """
    anns = __filenames_to_annotations(filenames)
    return search_anns_for_textbound(anns, text, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types, entities_only=entities_only)

# TODO: filename list interface functions for event and relation search

def check_files_type_consistency(filenames, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for inconsistent annotations in the given set of files.
    """
    anns = __filenames_to_annotations(filenames)
    return check_type_consistency(anns, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types)

def check_files_missing_consistency(filenames, restrict_types=None, ignore_types=None, nested_types=None):
    """
    Searches for potentially missing annotations in the given set of files.
    """
    anns = __filenames_to_annotations(filenames)
    return check_missing_consistency(anns, restrict_types=restrict_types, ignore_types=ignore_types, nested_types=nested_types)

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Search BioNLP Shared Task annotations.")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("-ct", "--consistency-types", default=False, action="store_true", help="Search for inconsistently typed annotations.")
    ap.add_argument("-cm", "--consistency-missing", default=False, action="store_true", help="Search for potentially missing annotations.")
    ap.add_argument("-t", "--text", metavar="TEXT", help="Search for matching text.")
    ap.add_argument("-b", "--textbound", metavar="TEXT", help="Search for textbound matching text.")
    ap.add_argument("-e", "--entity", metavar="TEXT", help="Search for entity matching text.")
    ap.add_argument("-r", "--restrict", metavar="TYPE", nargs="+", help="Restrict to given types.")
    ap.add_argument("-i", "--ignore", metavar="TYPE", nargs="+", help="Ignore given types.")
    ap.add_argument("-n", "--nested", metavar="TYPE", nargs="+", help="Require type to be nested.")
    ap.add_argument("files", metavar="FILE", nargs="+", help="Files to verify.")
    return ap

def main(argv=None):
    import sys
    import os
    import urllib

    # ignore search result number limits on command-line invocations
    global MAX_SEARCH_RESULT_NUMBER
    MAX_SEARCH_RESULT_NUMBER = -1

    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    # TODO: allow multiple searches
    if arg.textbound is not None:
        matches = [search_files_for_textbound(arg.files, arg.textbound,
                                              restrict_types=arg.restrict,
                                              ignore_types=arg.ignore,
                                              nested_types=arg.nested)]
    elif arg.entity is not None:
        matches = [search_files_for_textbound(arg.files, arg.textbound,
                                              restrict_types=arg.restrict,
                                              ignore_types=arg.ignore,
                                              nested_types=arg.nested,
                                              entities_only=True)]
    elif arg.text is not None:
        matches = [search_files_for_text(arg.files, arg.text,
                                         restrict_types=arg.restrict,
                                         ignore_types=arg.ignore,
                                         nested_types=arg.nested)]
    elif arg.consistency_types:
        matches = check_files_type_consistency(arg.files,
                                               restrict_types=arg.restrict,
                                               ignore_types=arg.ignore,
                                               nested_types=arg.nested)
    elif arg.consistency_missing:
        matches = check_files_missing_consistency(arg.files,
                                                  restrict_types=arg.restrict,
                                                  ignore_types=arg.ignore,
                                                  nested_types=arg.nested)
    else:
        print >> sys.stderr, "Please specify action (-h for help)"
        return 1

    # guessing at the likely URL
    import getpass
    username = getpass.getuser()

    for m in matches:
        print m.criterion
        for ann_obj, ann in m.get_matches():
            # TODO: get rid of specific URL hack and similar
            baseurl='http://127.0.0.1/~%s/brat/#/' % username
            # sorry about this
            if isinstance(ann, TextMatch):
                annp = "%s~%s" % (ann.reference_id()[0], ann.reference_id()[1])
            else:
                annp = ann.reference_id()[0]
            anns = unicode(ann).rstrip()
            annloc = ann_obj.get_document().replace("data/","")
            outs = u"\t%s%s?focus=%s (%s)" % (baseurl, annloc, annp, anns)
            print outs.encode('utf-8')

if __name__ == "__main__":
    import sys

    # on command-line invocations, don't limit the number of results
    # as the user has direct control over the system.
    MAX_SEARCH_RESULT_NUMBER = -1

    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; -*- 
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Main entry for the brat server, ensures integrity, handles dispatch and
processes potential exceptions before returning them to be sent as responses.

NOTE(S):

* Defer imports until failures can be catched
* Stay compatible with Python 2.3 until we verify the Python version

Author:     Pontus Stenetorp   <pontus is s u-tokyo ac jp>
Version:    2011-09-29
'''

# Standard library version
from os.path import abspath
from os.path import join as path_join
from sys import version_info, stderr
from time import time
from thread import allocate_lock

### Constants
# This handling of version_info is strictly for backwards compability
PY_VER_STR = '%d.%d.%d-%s-%d' % tuple(version_info)
REQUIRED_PY_VERSION = (2, 5, 0, 'alpha', 1)
REQUIRED_PY_VERSION_STR = '%d.%d.%d-%s-%d' % tuple(REQUIRED_PY_VERSION)
JSON_HDR = ('Content-Type', 'application/json')
CONF_FNAME = 'config.py'
CONF_TEMPLATE_FNAME = 'config_template.py'
CONFIG_CHECK_LOCK = allocate_lock()
###


class PermissionError(Exception):
    def json(self, json_dic):
        json_dic['exception'] = 'permissionError'

class ConfigurationError(Exception):
    def json(self, json_dic):
        json_dic['exception'] = 'configurationError'


# TODO: Possibly check configurations too
# TODO: Extend to check __everything__?
def _permission_check():
    from os import access, R_OK, W_OK
    from config import DATA_DIR, WORK_DIR
    from jsonwrap import dumps
    from message import Messager

    if not access(WORK_DIR, R_OK | W_OK):
        Messager.error((('Work dir: "%s" is not read-able and ' % WORK_DIR) +
                'write-able by the server'), duration=-1)
        raise PermissionError
    
    if not access(DATA_DIR, R_OK):
        Messager.error((('Data dir: "%s" is not read-able ' % DATA_DIR) +
                'by the server'), duration=-1)
        raise PermissionError


# Error message template functions
def _miss_var_msg(var):
    return ('Missing variable "%s" in %s, make sure that you have '
            'not made any errors to your configurations and to start over '
            'copy the template file %s to %s in your '
            'installation directory and edit it to suit your environment'
            ) % (var, CONF_FNAME, CONF_TEMPLATE_FNAME, CONF_FNAME)

def _miss_config_msg():
    return ('Missing file %s in the installation dir. If this is a new '
            'installation, copy the template file %s to %s in '
            'your installation directory ("cp %s %s") and edit '
            'it to suit your environment.'
            ) % (CONF_FNAME, CONF_TEMPLATE_FNAME, CONF_FNAME, 
                CONF_TEMPLATE_FNAME, CONF_FNAME)

# Check for existance and sanity of the configuration
def _config_check():
    from message import Messager
    
    from sys import path
    from copy import deepcopy
    from os.path import dirname
    # Reset the path to force config.py to be in the root (could be hacked
    #       using __init__.py, but we can be monkey-patched anyway)
    orig_path = deepcopy(path)

    try:
        # Can't you empty in O(1) instead of O(N)?
        while path:
            path.pop()
        path.append(path_join(abspath(dirname(__file__)), '../..'))
        # Check if we have a config, otherwise whine
        try:
            import config
            del config
        except ImportError, e:
            path.extend(orig_path)
            # "Prettiest" way to check specific failure
            if e.message == 'No module named config':
                Messager.error(_miss_config_msg(), duration=-1)
            else:
                Messager.error(_get_stack_trace(), duration=-1)
            raise ConfigurationError
        # Try importing the config entries we need
        try:
            from config import DEBUG
        except ImportError:
            path.extend(orig_path)
            Messager.error(_miss_var_msg('DEBUG'), duration=-1)
            raise ConfigurationError
        try:
            from config import ADMIN_CONTACT_EMAIL
        except ImportError:
            path.extend(orig_path)
            Messager.error(_miss_var_msg('ADMIN_CONTACT_EMAIL'), duration=-1)
            raise ConfigurationError
    finally:
        # Remove our entry to the path
        while path:
            path.pop()
        # Then restore it
        path.extend(orig_path)

# Convert internal log level to `logging` log level
def _convert_log_level(log_level):
    import config
    import logging
    if log_level == config.LL_DEBUG:
        return logging.DEBUG
    elif log_level == config.LL_INFO:
        return logging.INFO
    elif log_level == config.LL_WARNING:
        return logging.WARNING
    elif log_level == config.LL_ERROR:
        return logging.ERROR
    elif log_level == config.LL_CRITICAL:
        return logging.CRITICAL
    else:
        assert False, 'Should not happen'


class DefaultNoneDict(dict):
    def __missing__(self, key):
        return None


def _safe_serve(params, client_ip, client_hostname, cookie_data):
    # Note: Only logging imports here
    from config import WORK_DIR
    from logging import basicConfig as log_basic_config

    # Enable logging
    try:
        from config import LOG_LEVEL
        log_level = _convert_log_level(LOG_LEVEL)
    except ImportError:
        from logging import WARNING as LOG_LEVEL_WARNING
        log_level = LOG_LEVEL_WARNING
    log_basic_config(filename=path_join(WORK_DIR, 'server.log'),
            level=log_level)

    # Do the necessary imports after enabling the logging, order critical
    try:
        from common import ProtocolError, ProtocolArgumentError, NoPrintJSONError
        from dispatch import dispatch
        from jsonwrap import dumps
        from message import Messager
        from session import get_session, init_session, close_session, NoSessionError, SessionStoreError
    except ImportError:
        # Note: Heisenbug trap for #612, remove after resolved
        from logging import critical as log_critical
        from sys import path as sys_path
        log_critical('Heisenbug trap reports: ' + str(sys_path))
        raise

    init_session(client_ip, cookie_data=cookie_data)
    response_is_JSON = True
    try:
        # Unpack the arguments into something less obscure than the
        #   Python FieldStorage object (part dictonary, part list, part FUBAR)
        http_args = DefaultNoneDict()
        for k in params:
            # Also take the opportunity to convert Strings into Unicode,
            #   according to HTTP they should be UTF-8
            try:
                http_args[k] = unicode(params.getvalue(k), encoding='utf-8')
            except TypeError:
                Messager.error('protocol argument error: expected string argument %s, got %s' % (k, type(params.getvalue(k))))
                raise ProtocolArgumentError

        # Dispatch the request
        json_dic = dispatch(http_args, client_ip, client_hostname)
    except ProtocolError, e:
        # Internal error, only reported to client not to log
        json_dic = {}
        e.json(json_dic)

        # Add a human-readable version of the error
        err_str = str(e)
        if err_str != '':
            Messager.error(err_str, duration=-1)
    except NoPrintJSONError, e:
        # Terrible hack to serve other things than JSON
        response_data = (e.hdrs, e.data)
        response_is_JSON = False

    # Get the potential cookie headers and close the session (if any)
    try:
        cookie_hdrs = get_session().cookie.hdrs()
        close_session()
    except SessionStoreError:
        Messager.error("Failed to store cookie (missing write permission to brat work directory)?", -1)
    except NoSessionError:
        cookie_hdrs = None

    if response_is_JSON:
        response_data = ((JSON_HDR, ), dumps(Messager.output_json(json_dic)))

    return (cookie_hdrs, response_data)

# Programmatically access the stack-trace
def _get_stack_trace():
    from traceback import print_exc
    
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    # Getting the stack-trace requires a small trick
    buf = StringIO()
    print_exc(file=buf)
    buf.seek(0)
    return buf.read()

# Encapsulate an interpreter crash
def _server_crash(cookie_hdrs, e):
    from config import ADMIN_CONTACT_EMAIL, DEBUG
    from jsonwrap import dumps
    from message import Messager

    stack_trace = _get_stack_trace()

    if DEBUG:
        # Send back the stack-trace as json
        error_msg = '\n'.join(('Server Python crash, stack-trace is:\n',
            stack_trace))
        Messager.error(error_msg, duration=-1)
    else:
        # Give the user an error message
        # Use the current time since epoch as an id for later log look-up
        error_msg = ('The server encountered a serious error, '
                'please contact the administrators at %s '
                'and give the id #%d'
                ) % (ADMIN_CONTACT_EMAIL, int(time()))
        Messager.error(error_msg, duration=-1)

    # Print to stderr so that the exception is logged by the webserver
    print >> stderr, stack_trace

    json_dic = {
            'exception': 'serverCrash',
            }
    return (cookie_hdrs, ((JSON_HDR, ), dumps(Messager.output_json(json_dic))))

# Serve the client request
def serve(params, client_ip, client_hostname, cookie_data):
    # The session relies on the config, wait-for-it
    cookie_hdrs = None

    # Do we have a Python version compatibly with our libs?
    if (version_info[0] != REQUIRED_PY_VERSION[0] or
            version_info < REQUIRED_PY_VERSION):
        # Bail with hand-writen JSON, this is very fragile to protocol changes
        return cookie_hdrs, ((JSON_HDR, ),
                ('''
{
  "messages": [
    [
      "Incompatible Python version (%s), %s or above is supported",
      "error",
      -1
    ]
  ]
}
                ''' % (PY_VER_STR, REQUIRED_PY_VERSION_STR)).strip())

    # We can now safely use json and Messager
    from jsonwrap import dumps
    from message import Messager
    
    try:
        # We need to lock here since flup uses threads for each request and
        # can thus manipulate each other's global variables
        try:
            CONFIG_CHECK_LOCK.acquire()
            _config_check()
        finally:
            CONFIG_CHECK_LOCK.release()
    except ConfigurationError, e:
        json_dic = {}
        e.json(json_dic)
        return cookie_hdrs, ((JSON_HDR, ), dumps(Messager.output_json(json_dic)))
    # We can now safely read the config
    from config import DEBUG

    try:
        _permission_check()
    except PermissionError, e:
        json_dic = {}
        e.json(json_dic)
        return cookie_hdrs, ((JSON_HDR, ), dumps(Messager.output_json(json_dic)))

    try:
        # Safe region, can throw any exception, has verified installation
        return _safe_serve(params, client_ip, client_hostname, cookie_data)
    except BaseException, e:
        # Handle the server crash
        return _server_crash(cookie_hdrs, e)

########NEW FILE########
__FILENAME__ = session
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Session handling class.

Note: New modified version using pickle instead of shelve.

Author:     Goran Topic         <goran is s u-tokyo ac jp>
Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-03-11
'''

from __future__ import with_statement

from Cookie import CookieError, SimpleCookie
from atexit import register as atexit_register
from datetime import datetime, timedelta
from hashlib import sha224
from os import close as os_close, makedirs, remove
from os.path import exists, dirname, join as path_join, isfile
from shutil import copy
from shutil import move
from tempfile import mkstemp

try:
    from cPickle import dump as pickle_dump, load as pickle_load
except ImportError:
    from pickle import dump as pickle_dump, load as pickle_load

from config import WORK_DIR

### Constants
CURRENT_SESSION = None
SESSION_COOKIE_KEY = 'sid'
# Where we store our session data files
SESSIONS_DIR=path_join(WORK_DIR, 'sessions')
EXPIRATION_DELTA = timedelta(days=30)
###


# Raised if a session is requested although not initialised
class NoSessionError(Exception):
    pass

# Raised if a session could not be stored on close
class SessionStoreError(Exception):
    pass

class SessionCookie(SimpleCookie):
    def __init__(self, sid=None):
        if sid is not None:
            self[SESSION_COOKIE_KEY] = sid

    def set_expired(self):
        self[SESSION_COOKIE_KEY]['expires'] = 0

    def set_sid(self, sid):
        self[SESSION_COOKIE_KEY] = sid

    def get_sid(self):
        return self[SESSION_COOKIE_KEY].value

    def hdrs(self):
        # TODO: can probably be done better
        hdrs = [('Cache-Control', 'no-store, no-cache, must-revalidate')]
        for cookie_line in self.output(header='Set-Cookie:',
                sep='\n').split('\n'):
            hdrs.append(tuple(cookie_line.split(': ', 1)))
        return tuple(hdrs)

    @classmethod
    def load(cls, cookie_data):
        cookie = SessionCookie()
        SimpleCookie.load(cookie, cookie_data)
        return cookie
    # TODO: Weave the headers into __str__


class Session(dict):
    def __init__(self, cookie):
        self.cookie = cookie
        sid = self.cookie.get_sid()
        self.init_cookie(sid)

    def init_cookie(self, sid):
        # Clear the cookie and set its defaults
        self.cookie.clear()

        self.cookie[SESSION_COOKIE_KEY] = sid
        self.cookie[SESSION_COOKIE_KEY]['path'] = ''
        self.cookie[SESSION_COOKIE_KEY]['domain'] = ''
        self.cookie[SESSION_COOKIE_KEY]['expires'] = (
                datetime.utcnow() + EXPIRATION_DELTA
                ).strftime('%a, %d %b %Y %H:%M:%S')
        # Protect against cookie-stealing JavaScript
        try:
            # Note: This will not work for Python 2.5 and older
            self.cookie[SESSION_COOKIE_KEY]['httponly'] = True
        except CookieError:
            pass

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def get_sid(self):
        return self.cookie.get_sid()

    def __str__(self):
        return 'Session(sid="%s", cookie="%s",  dict="%s")' % (
                self.get_sid(), self.cookie, dict.__str__(self), )


def get_session_pickle_path(sid):
    return path_join(SESSIONS_DIR, '%s.pickle' % (sid, ))

def init_session(remote_address, cookie_data=None):
    if cookie_data is not None:
        cookie = SessionCookie.load(cookie_data)
    else:
        cookie = None
 
    # Default sid for the session
    sid = sha224('%s-%s' % (remote_address, datetime.utcnow())).hexdigest()
    if cookie is None:
        cookie = SessionCookie(sid)
    else:
        try:
            cookie.get_sid()
        except KeyError:
            # For some reason the cookie did not contain a SID, set to default
            cookie.set_sid(sid)

    # Set the session singleton (there can be only one!)
    global CURRENT_SESSION
    ppath = get_session_pickle_path(cookie.get_sid())
    if isfile(ppath):
        # Load our old session data and initialise the cookie
        try:
            with open(ppath, 'rb') as session_pickle:
                CURRENT_SESSION = pickle_load(session_pickle)
            CURRENT_SESSION.init_cookie(CURRENT_SESSION.get_sid())
        except Exception, e:
            # On any error, just create a new session
            CURRENT_SESSION = Session(cookie)            
    else:
        # Create a new session
        CURRENT_SESSION = Session(cookie)

def get_session():
    if CURRENT_SESSION is None:
        raise NoSessionError
    return CURRENT_SESSION

def invalidate_session():
    global CURRENT_SESSION
    if CURRENT_SESSION is None:
        return

    # Set expired and remove from disk
    CURRENT_SESSION.cookie.set_expired()
    ppath = get_session_pickle_path(CURRENT_SESSION.get_sid())
    if isfile(ppath):
        remove(ppath)

def close_session():
    # Do we have a session to save in the first place?
    if CURRENT_SESSION is None:
        return

    try:
        makedirs(SESSIONS_DIR)
    except OSError, e:
        if e.errno == 17:
            # Already exists
            pass
        else:
            raise

    # Write to a temporary file and move it in place, for safety
    tmp_file_path = None
    try:
        tmp_file_fh, tmp_file_path = mkstemp()
        os_close(tmp_file_fh)

        with open(tmp_file_path, 'wb') as tmp_file:
            pickle_dump(CURRENT_SESSION, tmp_file)
        copy(tmp_file_path, get_session_pickle_path(CURRENT_SESSION.get_sid()))
    except IOError:
        # failed store: no permissions?
        raise SessionStoreError
    finally:
        if tmp_file_path is not None:
            remove(tmp_file_path)

def save_conf(config):
    get_session()['conf'] = config
    return {}
    
def load_conf():
    try:
        return {
                'config': get_session()['conf'],
                }
    except KeyError:
        return {}


if __name__ == '__main__':
    # Some simple sanity checks
    try:
        get_session()
        assert False
    except NoSessionError:
        pass

    # New "fresh" cookie session check
    init_session('127.0.0.1')
    
    try:
        session = get_session()
        session['foo'] = 'bar'
    except NoSessionError:
        assert False

    # Pickle check
    init_session('127.0.0.1')
    tmp_file_path = None
    try:
        tmp_file_fh, tmp_file_path = mkstemp()
        os_close(tmp_file_fh)
        session = get_session()
        session['foo'] = 'bar'
        with open(tmp_file_path, 'wb') as tmp_file:
            pickle_dump(session, tmp_file)
        del session

        with open(tmp_file_path, 'rb') as tmp_file:
            session = pickle_load(tmp_file)
            assert session['foo'] == 'bar'
    finally:
        if tmp_file_path is not None:
            remove(tmp_file_path)

########NEW FILE########
__FILENAME__ = simstringdb
#!/usr/bin/env python

import glob
import os
import sys

from common import ProtocolError
from message import Messager
from os.path import join as path_join, sep as path_sep

try:
    from config import BASE_DIR, WORK_DIR
except ImportError:
    # for CLI use; assume we're in brat server/src/ and config is in root
    from sys import path as sys_path
    from os.path import dirname
    sys_path.append(path_join(dirname(__file__), '../..'))
    from config import BASE_DIR, WORK_DIR

# Filename extension used for DB file.
SS_DB_FILENAME_EXTENSION = 'ss.db'

# Default similarity measure
DEFAULT_SIMILARITY_MEASURE = 'cosine'

# Default similarity threshold
DEFAULT_THRESHOLD = 0.7

# Length of n-grams in simstring DBs
DEFAULT_NGRAM_LENGTH = 3

# Whether to include marks for begins and ends of strings
DEFAULT_INCLUDE_MARKS = False

SIMSTRING_MISSING_ERROR = '''Error: failed to import the simstring library.
This library is required for approximate string matching DB lookup.
Please install simstring and its Python bindings from
http://www.chokkan.org/software/simstring/'''

class NoSimStringError(ProtocolError):
    def __str__(self):
        return (u'No SimString bindings found, please install them from: '
                u'http://www.chokkan.org/software/simstring/')

    def json(self, json_dic):
        json_dic['exception'] = 'noSimStringError'

class ssdbNotFoundError(Exception):
    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        return u'Simstring database file "%s" not found' % self.fn

# Note: The only reason we use a function call for this is to delay the import
def __set_db_measure(db, measure):
    try:
        import simstring
    except ImportError:
        Messager.error(SIMSTRING_MISSING_ERROR, duration=-1)
        raise NoSimStringError

    ss_measure_by_str = {
            'cosine': simstring.cosine,
            'overlap': simstring.overlap,
            }
    db.measure = ss_measure_by_str[measure]

def __ssdb_path(db):
    '''
    Given a simstring DB name/path, returns the path for the file that
    is expected to contain the simstring DB.
    '''
    # Assume we have a path relative to the brat root if the value
    # contains a separator, name only otherwise. 
    # TODO: better treatment of name / path ambiguity, this doesn't
    # allow e.g. DBs to be located in brat root
    if path_sep in db:
        base = BASE_DIR
    else:
        base = WORK_DIR
    return path_join(base, db+'.'+SS_DB_FILENAME_EXTENSION)

def ssdb_build(strs, dbname, ngram_length=DEFAULT_NGRAM_LENGTH,
               include_marks=DEFAULT_INCLUDE_MARKS):
    '''
    Given a list of strings, a DB name, and simstring options, builds
    a simstring DB for the strings.
    '''
    try:
        import simstring
    except ImportError:
        Messager.error(SIMSTRING_MISSING_ERROR, duration=-1)
        raise NoSimStringError

    dbfn = __ssdb_path(dbname)
    try:
        # only library defaults (n=3, no marks) supported just now (TODO)
        assert ngram_length == 3, "Error: unsupported n-gram length"
        assert include_marks == False, "Error: begin/end marks not supported"
        db = simstring.writer(dbfn)
        for s in strs:
            db.insert(s)
        db.close()
    except:
        print >> sys.stderr, "Error building simstring DB"
        raise

    return dbfn

def ssdb_delete(dbname):
    '''
    Given a DB name, deletes all files associated with the simstring
    DB.
    '''

    dbfn = __ssdb_path(dbname)
    os.remove(dbfn)
    for fn in glob.glob(dbfn+'.*.cdb'):
        os.remove(fn)

def ssdb_open(dbname):
    '''
    Given a DB name, opens it as a simstring DB and returns the handle.
    The caller is responsible for invoking close() on the handle.
    '''
    try:
        import simstring
    except ImportError:
        Messager.error(SIMSTRING_MISSING_ERROR, duration=-1)
        raise NoSimStringError

    try:
        return simstring.reader(__ssdb_path(dbname))
    except IOError:
        Messager.error('Failed to open simstring DB %s' % dbname)
        raise ssdbNotFoundError(dbname)

def ssdb_lookup(s, dbname, measure=DEFAULT_SIMILARITY_MEASURE, 
                threshold=DEFAULT_THRESHOLD):
    '''
    Given a string and a DB name, returns the strings matching in the
    associated simstring DB.
    '''
    db = ssdb_open(dbname)

    __set_db_measure(db, measure)
    db.threshold = threshold

    result = db.retrieve(s)
    db.close()

    # assume simstring DBs always contain UTF-8 - encoded strings
    result = [r.decode('UTF-8') for r in result]

    return result

def ngrams(s, out=None, n=DEFAULT_NGRAM_LENGTH, be=DEFAULT_INCLUDE_MARKS):
    '''
    Extracts n-grams from the given string s and adds them into the
    given set out (or a new set if None). Returns the set. If be is
    True, affixes begin and end markers to strings.
    '''

    if out is None:
        out = set()

    # implementation mirroring ngrams() in ngram.h in simstring-1.0
    # distribution.

    mark = '\x01'
    src = ''
    if be:
        # affix begin/end marks
        for i in range(n-1):
            src += mark
        src += s
        for i in range(n-1):
            src += mark
    elif len(s) < n:
        # pad strings shorter than n
        src = s
        for i in range(n-len(s)):
            src += mark
    else:
        src = s

    # count n-grams
    stat = {}
    for i in range(len(src)-n+1):
        ngram = src[i:i+n]
        stat[ngram] = stat.get(ngram, 0) + 1

    # convert into a set
    for ngram, count in stat.items():
        out.add(ngram)
        # add ngram affixed with number if it appears more than once
        for i in range(1, count):
            out.add(ngram+str(i+1))

    return out

def ssdb_supstring_lookup(s, dbname, threshold=DEFAULT_THRESHOLD,
                          with_score=False):
    '''
    Given a string s and a DB name, returns the strings in the
    associated simstring DB that likely contain s as an (approximate)
    substring. If with_score is True, returns pairs of (str,score)
    where score is the fraction of n-grams in s that are also found in
    the matched string.
    '''
    try:
        import simstring
    except ImportError:
        Messager.error(SIMSTRING_MISSING_ERROR, duration=-1)
        raise NoSimStringError

    db = ssdb_open(dbname.encode('UTF-8'))

    __set_db_measure(db, 'overlap')
    db.threshold = threshold

    result = db.retrieve(s)
    db.close()

    # assume simstring DBs always contain UTF-8 - encoded strings
    result = [r.decode('UTF-8') for r in result]

    # The simstring overlap measure is symmetric and thus does not
    # differentiate between substring and superstring matches.
    # Replicate a small bit of the simstring functionality (mostly the
    # ngrams() function) to filter to substrings only.
    s_ngrams = ngrams(s)
    filtered = []
    for r in result:
        if s in r:
            # avoid calculation: simple containment => score=1
            if with_score:
                filtered.append((r,1.0))
            else:
                filtered.append(r)
        else:
            r_ngrams = ngrams(r)
            overlap = s_ngrams & r_ngrams
            if len(overlap) >= len(s_ngrams) * threshold:
                if with_score:
                    filtered.append((r, 1.0*len(overlap)/len(s_ngrams)))
                else:
                    filtered.append(r)

    return filtered

def ssdb_supstring_exists(s, dbname, threshold=DEFAULT_THRESHOLD):
    '''
    Given a string s and a DB name, returns whether at least one
    string in the associated simstring DB likely contains s as an
    (approximate) substring.
    '''
    try:
        import simstring
    except ImportError:
        Messager.error(SIMSTRING_MISSING_ERROR, duration=-1)
        raise NoSimStringError

    if threshold == 1.0:
        # optimized (not hugely, though) for this common case
        db = ssdb_open(dbname.encode('UTF-8'))

        __set_db_measure(db, 'overlap')
        db.threshold = threshold

        result = db.retrieve(s)
        db.close()

        # assume simstring DBs always contain UTF-8 - encoded strings
        result = [r.decode('UTF-8') for r in result]

        for r in result:
            if s in r:
                return True
        return False
    else:
        # naive implementation for everything else
        return len(ssdb_supstring_lookup(s, dbname, threshold)) != 0

if __name__ == "__main__":
    # test
    dbname = "TEMP-TEST-DB"
#     strings = [
#         "Cellular tumor antigen p53",
#         "Nucleoporin NUP53",
#         "Tumor protein p53-inducible nuclear protein 2",
#         "p53-induced protein with a death domain",
#         "TP53-regulating kinase",
#         "Tumor suppressor p53-binding protein 1",
#         "p53 apoptosis effector related to PMP-22",
#         "p53 and DNA damage-regulated protein 1",
#         "Tumor protein p53-inducible protein 11",
#         "TP53RK-binding protein",
#         "TP53-regulated inhibitor of apoptosis 1",
#         "Apoptosis-stimulating of p53 protein 2",
#         "Tumor protein p53-inducible nuclear protein 1",
#         "TP53-target gene 1 protein",
#         "Accessory gland protein Acp53Ea",
#         "p53-regulated apoptosis-inducing protein 1",
#         "Tumor protein p53-inducible protein 13",
#         "TP53-target gene 3 protein",
#         "Apoptosis-stimulating of p53 protein 1",
#         "Ribosome biogenesis protein NOP53",
#         ]
    strings = [
        "0",
        "01",
        "012",
        "0123",
        "01234",
        "-12345",
        "012345",
        ]
    print 'strings:', strings
    ssdb_build(strings, dbname)
    for t in ['0', '012', '012345', '0123456', '0123456789']:
        print 'lookup for', t
        for s in ssdb_supstring_lookup(t, dbname):
            print s, 'contains', t, '(threshold %f)' % DEFAULT_THRESHOLD
    ssdb_delete(dbname)
    

########NEW FILE########
__FILENAME__ = sosmessage
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Dummy Messager that can replace the real one in case it goes down.
Doesn't actually send any messages other than letting the user
know of the problem.
Use e.g. as

    try:
        from message import Messager
    except:
        from sosmessage import Messager
'''

class SosMessager:
    def output_json(json_dict):
        json_dict['messages'] = [['HELP: messager down! (internal error in message.py, please contact administrator)','error', -1]]
        return json_dict
    output_json = staticmethod(output_json)

    def output(o):
        print >> o, 'HELP: messager down! (internal error in message.py, please contact administrator)'
    output = staticmethod(output)

    def info(msg, duration=3, escaped=False): pass
    info = staticmethod(info)

    def warning(msg, duration=3, escaped=False): pass
    warning = staticmethod(warning)

    def error(msg, duration=3, escaped=False): pass
    error = staticmethod(error)

    def debug(msg, duration=3, escaped=False): pass
    debug = staticmethod(debug)

########NEW FILE########
__FILENAME__ = ssplit
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

'''
Primitive sentence splitting using Sampo Pyysalo's GeniaSS sentence split
refiner. Also a primitive Japanese sentence splitter without refinement.

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-05-09
'''

from re import compile as re_compile
from re import DOTALL, VERBOSE
from os.path import join as path_join
from os.path import dirname
from subprocess import Popen, PIPE
from shlex import split as shlex_split

### Constants
# Reasonably well-behaved sentence end regular expression
SENTENCE_END_REGEX = re_compile(ur'''
        # Require a leading non-whitespace character for the sentence
        \S
        # Then, anything goes, but don't be greedy
        .*?
        # Anchor the sentence at...
        (:?
            # One (or multiple) terminal character(s)
            #   followed by one (or multiple) whitespace
            (:?(\.|!|\?|。|！|？)+(?=\s+))
        | # Or...
            # Newlines, to respect file formatting
            (:?(?=\n+))
        | # Or...
            # End-of-file, excluding whitespaces before it
            (:?(?=\s*$))
        )
    ''', DOTALL | VERBOSE)
# Only newlines can end a sentence to preserve pre-processed formatting
SENTENCE_END_NEWLINE_REGEX = re_compile(ur'''
        # Require a leading non-whitespace character for the sentence
        \S
        # Then, anything goes, but don't be greedy
        .*?
        # Anchor the sentence at...
        (:?
            # One (or multiple) newlines
            (:?(?=\n+))
        | # Or...
            # End-of-file, excluding whitespaces before it
            (:?(?=\s*$))
        )
    ''', DOTALL | VERBOSE)
###

def _refine_split(offsets, original_text):
    # Postprocessor expects newlines, so add. Also, replace
    # sentence-internal newlines with spaces not to confuse it.
    new_text = '\n'.join((original_text[o[0]:o[1]].replace('\n', ' ')
            for o in offsets))

    from sspostproc import refine_split
    output = refine_split(new_text)

    # Align the texts and see where our offsets don't match
    old_offsets = offsets[::-1]
    # Protect against edge case of single-line docs missing
    #   sentence-terminal newline
    if len(old_offsets) == 0:
        old_offsets.append((0, len(original_text), ))
    new_offsets = []
    for refined_sentence in output.split('\n'):
        new_offset = old_offsets.pop()
        # Merge the offsets if we have received a corrected split
        while new_offset[1] - new_offset[0] < len(refined_sentence) - 1:
            _, next_end = old_offsets.pop()
            new_offset = (new_offset[0], next_end)
        new_offsets.append(new_offset)

    # Protect against missing document-final newline causing the last
    #   sentence to fall out of offset scope
    if len(new_offsets) != 0 and new_offsets[-1][1] != len(original_text)-1:
        start = new_offsets[-1][1]+1
        while start < len(original_text) and original_text[start].isspace():
            start += 1
        if start < len(original_text)-1:
            new_offsets.append((start, len(original_text)-1))

    # Finally, inject new-lines from the original document as to respect the
    #   original formatting where it is made explicit.
    last_newline = -1
    while True:
        try:
            orig_newline = original_text.index('\n', last_newline + 1)
        except ValueError:
            # No more newlines
            break

        for o_start, o_end in new_offsets:
            if o_start <= orig_newline < o_end:
                # We need to split the existing offsets in two
                new_offsets.remove((o_start, o_end))
                new_offsets.extend(((o_start, orig_newline, ),
                        (orig_newline + 1, o_end), ))
                break
            elif o_end == orig_newline:
                # We have already respected this newline
                break
        else:
            # Stand-alone "null" sentence, just insert it
            new_offsets.append((orig_newline, orig_newline, ))

        last_newline = orig_newline

    new_offsets.sort()
    return new_offsets

def _sentence_boundary_gen(text, regex):
    for match in regex.finditer(text):
        yield match.span()

def regex_sentence_boundary_gen(text):
    for o in _refine_split([_o for _o in _sentence_boundary_gen(
                text, SENTENCE_END_REGEX)], text):
        yield o

def newline_sentence_boundary_gen(text):
    for o in _sentence_boundary_gen(text, SENTENCE_END_NEWLINE_REGEX):
        yield o

if __name__ == '__main__':
    from sys import argv

    from annotation import open_textfile

    def _text_by_offsets_gen(text, offsets):
        for start, end in offsets:
            yield text[start:end]

    if len(argv) > 1:
        try:
            for txt_file_path in argv[1:]:
                print
                print '### Splitting:', txt_file_path
                with open_textfile(txt_file_path, 'r') as txt_file:
                    text = txt_file.read()
                print '# Original text:'
                print text.replace('\n', '\\n')
                offsets = [o for o in newline_sentence_boundary_gen(text)]
                print '# Offsets:'
                print offsets
                print '# Sentences:'
                for sentence in _text_by_offsets_gen(text, offsets):
                    # These should only be allowed when coming from original
                    #   explicit newlines.
                    #assert sentence, 'blank sentences disallowed'
                    #assert not sentence[0].isspace(), (
                    #        'sentence may not start with white-space "%s"' % sentence)
                    print '"%s"' % sentence.replace('\n', '\\n')
        except IOError:
            pass # Most likely a broken pipe
    else:
        sentence = 'This is a short sentence.\nthis is another one.'
        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in en_sentence_boundary_gen(sentence)]
        last_end = 0
        for start, end in ret:
            if last_end != start:
                print 'DROPPED: "%s"' % sentence[last_end:start]
            print 'SENTENCE: "%s"' % sentence[start:end]
            last_end = end
        print ret

        sentence = u'　変しん！　両になった。うそ！　かも　'
        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in jp_sentence_boundary_gen(sentence)]
        ans = [(1, 5), (6, 12), (12, 15), (16, 18)]
        assert ret == ans, '%s != %s' % (ret, ans)
        print 'Succesful!'

        sentence = ' One of these days Jimmy, one of these days. Boom! Kaboom '
        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in en_sentence_boundary_gen(sentence)]
        ans = [(1, 44), (45, 50), (51, 57)]
        assert ret == ans, '%s != %s' % (ret, ans)
        print 'Succesful!'

########NEW FILE########
__FILENAME__ = sspostproc
#!/usr/bin/env python

# Python version of geniass-postproc.pl. Originally developed as a
# heuristic postprocessor for the geniass sentence splitter, drawing
# in part on Yoshimasa Tsuruoka's medss.pl.

from __future__ import with_statement

import re

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"
DEBUG_SS_POSTPROCESSING = False

__initial = []

# TODO: some cases that heuristics could be improved on
# - no split inside matched quotes
# - "quoted." New sentence
# - 1 mg .\nkg(-1) .

# breaks sometimes missing after "?", "safe" cases
__initial.append((re.compile(r'\b([a-z]+\?) ([A-Z][a-z]+)\b'), r'\1\n\2'))
# breaks sometimes missing after "." separated with extra space, "safe" cases
__initial.append((re.compile(r'\b([a-z]+ \.) ([A-Z][a-z]+)\b'), r'\1\n\2'))

# join breaks creating lines that only contain sentence-ending punctuation
__initial.append((re.compile(r'\n([.!?]+)\n'), r' \1\n'))

# no breaks inside parens/brackets. (To protect against cases where a
# pair of locally mismatched parentheses in different parts of a large
# document happen to match, limit size of intervening context. As this
# is not an issue in cases where there are no interveining brackets,
# allow an unlimited length match in those cases.)

__repeated = []

# unlimited length for no intevening parens/brackets
__repeated.append((re.compile(r'(\([^\[\]\(\)]*)\n([^\[\]\(\)]*\))'),r'\1 \2'))
__repeated.append((re.compile(r'(\[[^\[\]\(\)]*)\n([^\[\]\(\)]*\])'),r'\1 \2'))
# standard mismatched with possible intervening
__repeated.append((re.compile(r'(\([^\(\)]{0,250})\n([^\(\)]{0,250}\))'), r'\1 \2'))
__repeated.append((re.compile(r'(\[[^\[\]]{0,250})\n([^\[\]]{0,250}\])'), r'\1 \2'))
# nesting to depth one
__repeated.append((re.compile(r'(\((?:[^\(\)]|\([^\(\)]*\)){0,250})\n((?:[^\(\)]|\([^\(\)]*\)){0,250}\))'), r'\1 \2'))
__repeated.append((re.compile(r'(\[(?:[^\[\]]|\[[^\[\]]*\]){0,250})\n((?:[^\[\]]|\[[^\[\]]*\]){0,250}\])'), r'\1 \2'))

__final = []

# no break after periods followed by a non-uppercase "normal word"
# (i.e. token with only lowercase alpha and dashes, with a minimum
# length of initial lowercase alpha).
__final.append((re.compile(r'\.\n([a-z]{3}[a-z-]{0,}[ \.\:\,\;])'), r'. \1'))

# no break in likely species names with abbreviated genus (e.g.
# "S. cerevisiae"). Differs from above in being more liberal about
# separation from following text.
__final.append((re.compile(r'\b([A-Z]\.)\n([a-z]{3,})\b'), r'\1 \2'))

# no break in likely person names with abbreviated middle name
# (e.g. "Anton P. Chekhov", "A. P. Chekhov"). Note: Won't do
# "A. Chekhov" as it yields too many false positives.
__final.append((re.compile(r'\b((?:[A-Z]\.|[A-Z][a-z]{3,}) [A-Z]\.)\n([A-Z][a-z]{3,})\b'), r'\1 \2'))

# no break before CC ..
__final.append((re.compile(r'\n((?:and|or|but|nor|yet) )'), r' \1'))

# or IN. (this is nothing like a "complete" list...)
__final.append((re.compile(r'\n((?:of|in|by|as|on|at|to|via|for|with|that|than|from|into|upon|after|while|during|within|through|between|whereas|whether) )'), r' \1'))

# no sentence breaks in the middle of specific abbreviations
__final.append((re.compile(r'\b(e\.)\n(g\.)'), r'\1 \2'))
__final.append((re.compile(r'\b(i\.)\n(e\.)'), r'\1 \2'))
__final.append((re.compile(r'\b(i\.)\n(v\.)'), r'\1 \2'))

# no sentence break after specific abbreviations
__final.append((re.compile(r'\b(e\. ?g\.|i\. ?e\.|i\. ?v\.|vs\.|cf\.|Dr\.|Mr\.|Ms\.|Mrs\.)\n'), r'\1 '))

# or others taking a number after the abbrev
__final.append((re.compile(r'\b([Aa]pprox\.|[Nn]o\.|[Ff]igs?\.)\n(\d+)'), r'\1 \2'))

# no break before comma (e.g. Smith, A., Black, B., ...)
__final.append((re.compile(r'(\.\s*)\n(\s*,)'), r'\1 \2'))

def refine_split(s):
    """
    Given a string with sentence splits as newlines, attempts to
    heuristically improve the splitting. Heuristics tuned for geniass
    sentence splitting errors.
    """

    if DEBUG_SS_POSTPROCESSING:
        orig = s

    for r, t in __initial:
        s = r.sub(t, s)

    for r, t in __repeated:
        while True:
            n = r.sub(t, s)
            if n == s: break
            s = n

    for r, t in __final:
        s = r.sub(t, s)

    # Only do final comparison in debug mode.
    if DEBUG_SS_POSTPROCESSING:
        # revised must match original when differences in space<->newline
        # substitutions are ignored
        r1 = orig.replace('\n', ' ')
        r2 = s.replace('\n', ' ')
        if r1 != r2:
            print >> sys.stderr, "refine_split(): error: text mismatch (returning original):\nORIG: '%s'\nNEW:  '%s'" % (orig, s)
            s = orig

    return s

if __name__ == "__main__":
    import sys
    import codecs

    # for testing, read stdin if no args
    if len(sys.argv) == 1:
        sys.argv.append('/dev/stdin')

    for fn in sys.argv[1:]:
        try:
            with codecs.open(fn, encoding=INPUT_ENCODING) as f:
                s = "".join(f.read())
                sys.stdout.write(refine_split(s).encode(OUTPUT_ENCODING))
        except Exception, e:
            print >> sys.stderr, "Failed to read", fn, ":", e
            

########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

from __future__ import with_statement

'''
Annotation statistics generation.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-04-21
'''

from cPickle import UnpicklingError
from cPickle import dump as pickle_dump
from cPickle import load as pickle_load
from logging import info as log_info
from os import listdir
from os.path import isfile, getmtime
from os.path import join as path_join

from annotation import Annotations, open_textfile
from config import DATA_DIR, BASE_DIR
from message import Messager
from projectconfig import get_config_path, options_get_validation

### Constants
STATS_CACHE_FILE_NAME = '.stats_cache'
###

def get_stat_cache_by_dir(directory):
    return path_join(directory, STATS_CACHE_FILE_NAME)

# TODO: Move this to a util module
def get_config_py_path():
    return path_join(BASE_DIR, 'config.py')

# TODO: Quick hack, prettify and use some sort of csv format
def get_statistics(directory, base_names, use_cache=True):
    # Check if we have a cache of the costly satistics generation
    # Also, only use it if no file is newer than the cache itself
    cache_file_path = get_stat_cache_by_dir(directory)

    try:
        cache_mtime = getmtime(cache_file_path);
    except OSError, e:
        if e.errno == 2:
            cache_mtime = -1;
        else:
            raise

    try:
        if (not isfile(cache_file_path)
                # Has config.py been changed?
                or getmtime(get_config_py_path()) > cache_mtime
                # Any file has changed in the dir since the cache was generated
                or any(True for f in listdir(directory)
                    if (getmtime(path_join(directory, f)) > cache_mtime
                    # Ignore hidden files
                    and not f.startswith('.')))
                # The configuration is newer than the cache
                or getmtime(get_config_path(directory)) > cache_mtime):
            generate = True
            docstats = []
        else:
            generate = False
            try:
                with open(cache_file_path, 'rb') as cache_file:
                    docstats = pickle_load(cache_file)
                if len(docstats) != len(base_names):
                    Messager.warning('Stats cache %s was incomplete; regenerating' % cache_file_path)
                    generate = True
                    docstats = []
            except UnpicklingError:
                # Corrupt data, re-generate
                Messager.warning('Stats cache %s was corrupted; regenerating' % cache_file_path, -1)
                generate = True
            except EOFError:
                # Corrupt data, re-generate
                generate = True
    except OSError, e:
        Messager.warning('Failed checking file modification times for stats cache check; regenerating')
        generate = True

    if not use_cache:
        generate = True

    # "header" and types
    stat_types = [("Entities", "int"), ("Relations", "int"), ("Events", "int")]

    if options_get_validation(directory) != 'none':
        stat_types.append(("Issues", "int"))
            
    if generate:
        # Generate the document statistics from scratch
        from annotation import JOINED_ANN_FILE_SUFF
        log_info('generating statistics for "%s"' % directory)
        docstats = []
        for docname in base_names:
            try:
                with Annotations(path_join(directory, docname), 
                        read_only=True) as ann_obj:
                    tb_count = len([a for a in ann_obj.get_entities()])
                    rel_count = (len([a for a in ann_obj.get_relations()]) +
                                 len([a for a in ann_obj.get_equivs()]))
                    event_count = len([a for a in ann_obj.get_events()])


                    if options_get_validation(directory) == 'none':
                        docstats.append([tb_count, rel_count, event_count])
                    else:
                        # verify and include verification issue count
                        try:
                            from projectconfig import ProjectConfiguration
                            projectconf = ProjectConfiguration(directory)
                            from verify_annotations import verify_annotation
                            issues = verify_annotation(ann_obj, projectconf)
                            issue_count = len(issues)
                        except:
                            # TODO: error reporting
                            issue_count = -1
                        docstats.append([tb_count, rel_count, event_count, issue_count])
            except Exception, e:
                log_info('Received "%s" when trying to generate stats' % e)
                # Pass exceptions silently, just marking stats missing
                docstats.append([-1] * len(stat_types))

        # Cache the statistics
        try:
            with open(cache_file_path, 'wb') as cache_file:
                pickle_dump(docstats, cache_file)
        except IOError, e:
            Messager.warning("Could not write statistics cache file to directory %s: %s" % (directory, e))

    return stat_types, docstats

# TODO: Testing!

########NEW FILE########
__FILENAME__ = svg
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
SVG saving and storage functionality.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Author:     Goran Topic         <goran is s u-tokyo ac jp>
Version:    2011-04-22
'''

# TODO: Can we verify somehow that what we are getting is actually an svg?
# TODO: Limits to size? Or inherent from HTTP?

from __future__ import with_statement

from os.path import join as path_join
from os.path import isfile, exists
from os import makedirs, mkdir

from annotator import open_textfile
from common import ProtocolError, NoPrintJSONError
from config import BASE_DIR, WORK_DIR
from document import real_directory
from message import Messager
from session import get_session

### Constants
SVG_DIR = path_join(WORK_DIR, 'svg')
CSS_PATH = path_join(BASE_DIR, 'static/style-vis.css')
FONT_DIR = path_join(BASE_DIR, 'static', 'fonts')
SVG_FONTS = (
        path_join(FONT_DIR, 'Liberation_Sans-Regular.svg'),
        path_join(FONT_DIR, 'PT_Sans-Caption-Web-Regular.svg'),
        )
SVG_SUFFIX='svg'
PNG_SUFFIX='png'
PDF_SUFFIX='pdf'
EPS_SUFFIX='eps'
# Maintain a mirror of the data directory where we keep the latest stored svg
#   for each document. Incurs some disk write overhead.
SVG_STORE_DIR = path_join(WORK_DIR, 'svg_store')
SVG_STORE = False
###


class UnknownSVGVersionError(ProtocolError):
    def __init__(self, unknown_version):
        self.unknown_version = unknown_version

    def __str__(self):
        return 'Version "%s" is not a valid version' % self.unknown_version

    def json(self, json_dic):
        json_dic['exception'] = 'unknownSVGVersion'
        return json_dic


class NoSVGError(ProtocolError):
    def __init__(self, version):
        self.version = version

    def __str__(self):
        return 'Stored document with version "%s" does not exist' % (self.version, )

    def json(self, json_dic):
        json_dic['exception'] = 'noSVG'
        return json_dic


class CorruptSVGError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Corrupt SVG'

    def json(self, json_dic):
        json_dic['exception'] = 'corruptSVG'
        return json_dic

def _save_svg(collection, document, svg):
    svg_path = _svg_path()

    with open_textfile(svg_path, 'w') as svg_file:
        svg_hdr = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
                '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
                '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">')
        defs = svg.find('</defs>')

        with open_textfile(CSS_PATH, 'r') as css_file:
            css = css_file.read()

        if defs != -1:
            css = '<style type="text/css"><![CDATA[' + css + ']]></style>'
            font_data = []
            for font_path in SVG_FONTS:
                with open_textfile(font_path, 'r') as font_file:
                    font_data.append(font_file.read().strip())
            fonts = '\n'.join(font_data)
            svg = (svg_hdr + '\n' + svg[:defs] + '\n' + fonts + '\n' + css
                    + '\n' + svg[defs:])
            svg_file.write(svg)

            # Create a copy in the svg store?
            if SVG_STORE:
                real_dir = real_directory(collection, rel_to=SVG_STORE_DIR)
                if not exists(real_dir):
                    makedirs(real_dir)
                svg_store_path = path_join(real_dir, document + '.svg')
                with open_textfile(svg_store_path, 'w') as svg_store_file:
                    svg_store_file.write(svg)

        else:
            # TODO: @amadanmath: When does this actually happen?
            raise CorruptSVGError


def _stored_path():
    # Create the SVG_DIR if necessary
    if not exists(SVG_DIR):
        mkdir(SVG_DIR)

    return path_join(SVG_DIR, get_session().get_sid())

def _svg_path():
    return _stored_path()+'.'+SVG_SUFFIX

def store_svg(collection, document, svg):
    stored = []

    _save_svg(collection, document, svg)
    stored.append({'name': 'svg', 'suffix': SVG_SUFFIX})

    # attempt conversions from SVG to other formats
    try:
        from config import SVG_CONVERSION_COMMANDS
    except ImportError:
        SVG_CONVERSION_COMMANDS = []

    for format, command in SVG_CONVERSION_COMMANDS:
        try:
            from os import system

            svgfn = _svg_path()
            # TODO: assuming format name matches suffix; generalize
            outfn = svgfn.replace('.'+SVG_SUFFIX, '.'+format)
            cmd = command % (svgfn, outfn)

            import logging
            logging.error(cmd)

            retval = system(cmd)

            # TODO: this check may not work on all architectures.
            # consider rather checking is the intended output file
            # exists (don't forget to delete a possible old one
            # with the same name, though).
#             if retval != 0:
#                 stored.append({'name': format, 'suffix': format})
#             else:
#                 Messager.warning("Failed conversion to %s" % format)
            # I'm getting weird return values from inkscape; will
            # just assume everything's OK ...
            # TODO: check return value, react appropriately
            stored.append({'name': format, 'suffix': format})
            
        except: # whatever
            Messager.warning("Failed conversion to %s" % format)
            # no luck, but doesn't matter
            pass

    return { 'stored' : stored }

def retrieve_stored(document, suffix):
    stored_path = _stored_path()+'.'+suffix

    if not isfile(stored_path):
        # @ninjin: not sure what 'version' was supposed to be returned
        # here, but none was defined, so returning that
#         raise NoSVGError(version)
        raise NoSVGError('None')

    filename = document+'.'+suffix

    # sorry, quick hack to get the content-type right
    # TODO: send this with initial 'stored' response instead of
    # guessing on suffix
    if suffix == SVG_SUFFIX:
        content_type = 'image/svg+xml'
    elif suffix == PNG_SUFFIX:
        content_type = 'image/png'
    elif suffix == PDF_SUFFIX:
        content_type = 'application/pdf'
    elif suffix == EPS_SUFFIX:
        content_type = 'application/postscript'
    else:
        Messager.error('Unknown suffix "%s"; cannot determine Content-Type' % suffix)
        # TODO: reasonable backoff value
        content_type = None

    # Bail out with a hack since we violated the protocol
    hdrs = [('Content-Type', content_type),
            ('Content-Disposition', 'inline; filename=' + filename)]

    with open(stored_path, 'rb') as stored_file:
        data = stored_file.read()

    raise NoPrintJSONError(hdrs, data)

########NEW FILE########
__FILENAME__ = tag
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Functionality for invoking tagging services.

Author:     Pontus Stenetorp
Version:    2011-04-22
'''

from __future__ import with_statement

from httplib import HTTPConnection
from os.path import join as path_join
from socket import error as SocketError
from urlparse import urlparse

from annotation import TextAnnotations, TextBoundAnnotationWithText
from annotator import _json_from_ann, ModificationTracker
from common import ProtocolError
from document import real_directory
from jsonwrap import loads
from message import Messager
from projectconfig import ProjectConfiguration

### Constants
QUERY_TIMEOUT = 30
###


class UnknownTaggerError(ProtocolError):
    def __init__(self, tagger):
        self.tagger = tagger

    def __str__(self):
        return ('Tagging request received for '
                'an unknown tagger "%s"') % self.tagger

    def json(self, json_dic):
        json_dic['exception'] = 'unknownTaggerError'


class InvalidConnectionSchemeError(ProtocolError):
    def __init__(self, tagger, scheme):
        self.tagger = tagger
        self.scheme = scheme

    def __str__(self):
        return ('The tagger "%s" uses the unsupported scheme "%s"'
                ' "%s"') % (self.tagger, self.scheme, )

    def json(self, json_dic):
        json_dic['exception'] = 'unknownTaggerError'


class InvalidTaggerResponseError(ProtocolError):
    def __init__(self, tagger, response):
        self.tagger = tagger
        self.response = response

    def __str__(self):
        return (('The tagger "%s" returned an invalid JSON response, please '
            'contact the tagger service mantainer. Response: "%s"')
            % (self.tagger, self.response, ))

    def json(self, json_dic):
        json_dic['exception'] = 'unknownTaggerError'


class TaggerConnectionError(ProtocolError):
    def __init__(self, tagger, error):
        self.tagger = tagger
        self.error = error

    def __str__(self):
        return ('Tagger service %s returned the error: "%s"'
                % (self.tagger, self.error, ))

    def json(self, json_dic):
        json_dic['exception'] = 'taggerConnectionError'


def tag(collection, document, tagger):
    pconf = ProjectConfiguration(real_directory(collection))
    for tagger_token, _, _, tagger_service_url in pconf.get_annotator_config():
        if tagger == tagger_token:
            break
    else:
        raise UnknownTaggerError(tagger)

    doc_path = path_join(real_directory(collection), document)

    with TextAnnotations(path_join(real_directory(collection),
            document)) as ann_obj:

        url_soup = urlparse(tagger_service_url)

        if url_soup.scheme == 'http':
            Connection = HTTPConnection
        elif url_soup.scheme == 'https':
            # Delayed HTTPS import since it relies on SSL which is commonly
            #   missing if you roll your own Python, for once we should not
            #   fail early since tagging is currently an edge case and we
            #   can't allow it to bring down the whole server.
            from httplib import HTTPSConnection
            Connection = HTTPSConnection
        else:
            raise InvalidConnectionSchemeError(tagger_token, url_soup.scheme)

        conn = None
        try:
            conn = Connection(url_soup.netloc)
            req_headers = {
                    'Content-type': 'text/plain; charset=utf-8',
                    'Accept': 'application/json',
                    }
            # Build a new service URL since the request method doesn't accept
            #   a parameters argument
            service_url = url_soup.path + (
                    '?' + url_soup.query if url_soup.query else '')
            try:
                data = ann_obj.get_document_text().encode('utf-8')
                req_headers['Content-length'] = len(data)
                # Note: Trout slapping for anyone sending Unicode objects here
                conn.request('POST',
                        # As per: http://bugs.python.org/issue11898
                        # Force the url to be an ascii string
                        str(service_url),
                        data,
                        headers=req_headers)
            except SocketError, e:
                raise TaggerConnectionError(tagger_token, e)
            resp = conn.getresponse()

            # Did the request succeed?
            if resp.status != 200:
                raise TaggerConnectionError(tagger_token,
                        '%s %s' % (resp.status, resp.reason))
            # Finally, we can read the response data
            resp_data = resp.read()
        finally:
            if conn is not None:
                conn.close()

        try:
            json_resp = loads(resp_data)
        except ValueError:
            raise InvalidTaggerResponseError(tagger_token, resp_data)

        mods = ModificationTracker()

        for ann_data in json_resp.itervalues():
            assert 'offsets' in ann_data, 'Tagger response lacks offsets'
            offsets = ann_data['offsets']
            assert 'type' in ann_data, 'Tagger response lacks type'
            _type = ann_data['type']
            assert 'texts' in ann_data, 'Tagger response lacks texts'
            texts = ann_data['texts']

            # sanity
            assert len(offsets) != 0, 'Tagger response has empty offsets'
            assert len(texts) == len(offsets), 'Tagger response has different numbers of offsets and texts'

            start, end = offsets[0]
            text = texts[0]

            _id = ann_obj.get_new_id('T')

            tb = TextBoundAnnotationWithText(offsets, _id, _type, text, " " + ' '.join(texts[1:]))

            mods.addition(tb)
            ann_obj.add_annotation(tb)

        mod_resp = mods.json_response()
        mod_resp['annotations'] = _json_from_ann(ann_obj)
        return mod_resp

if __name__ == '__main__':
    # Silly test, but helps
    tag('/BioNLP-ST_2011_ID_devel', 'PMC1874608-01-INTRODUCTION', 'random')

########NEW FILE########
__FILENAME__ = tokenise
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

'''
Tokenisation related functionality.

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-05-23
'''

from os.path import join as path_join
from os.path import dirname
from subprocess import Popen, PIPE
from shlex import split as shlex_split

def _token_boundaries_by_alignment(tokens, original_text):
    curr_pos = 0
    for tok in tokens:
        start_pos = original_text.index(tok, curr_pos)
        # TODO: Check if we fail to find the token!
        end_pos = start_pos + len(tok)
        yield (start_pos, end_pos)
        curr_pos = end_pos

def jp_token_boundary_gen(text):
    try:
        from mecab import token_offsets_gen
        for o in token_offsets_gen(text):
            yield o
    except ImportError:
        from message import Messager
        Messager.error('Failed to import MeCab, '
                       'falling back on whitespace tokenization. '
                       'Please check configuration and/or server setup.')
        for o in whitespace_token_boundary_gen(text):
            yield o

def gtb_token_boundary_gen(text):
    from gtbtokenize import tokenize
    tokens = tokenize(text).split()
    for o in _token_boundaries_by_alignment(tokens, text):
        yield o

def whitespace_token_boundary_gen(text):
    tokens = text.split()
    for o in _token_boundaries_by_alignment(tokens, text):
        yield o

if __name__ == '__main__':
    from sys import argv

    from annotation import open_textfile

    def _text_by_offsets_gen(text, offsets):
        for start, end in offsets:
            yield text[start:end]

    if len(argv) == 1:
        argv.append('/dev/stdin')

    try:
        for txt_file_path in argv[1:]:
            print
            print '### Tokenising:', txt_file_path
            with open(txt_file_path, 'r') as txt_file:
                text = txt_file.read()
                print text
            print '# Original text:'
            print text.replace('\n', '\\n')
            #offsets = [o for o in jp_token_boundary_gen(text)]
            #offsets = [o for o in whitespace_token_boundary_gen(text)]
            offsets = [o for o in gtb_token_boundary_gen(text)]
            print '# Offsets:'
            print offsets
            print '# Tokens:'
            for tok in _text_by_offsets_gen(text, offsets):
                assert tok, 'blank tokens disallowed'
                assert not tok[0].isspace() and not tok[-1].isspace(), (
                        'tokens may not start or end with white-space "%s"' % tok)
                print '"%s"' % tok
    except IOError:
        raise

########NEW FILE########
__FILENAME__ = undo
#!/usr/bin/env python

'''
Annotation undo functionality.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-11-30
'''

from __future__ import with_statement

from os.path import join as path_join

from annotator import delete_span, create_span
from annotation import TextAnnotations
from common import ProtocolError
from jsonwrap import loads as json_loads


class CorruptUndoTokenError(ProtocolError):
    def __str__(self):
        return 'Undo token corrupted, unable to process'

    def json(self, json_dic):
        json_dic['exception'] = 'corruptUndoTokenError'


class InvalidUndoTokenError(ProtocolError):
    def __init__(self, attrib):
        self.attrib = attrib

    def __str__(self):
        return 'Undo token missing %s' % self.attrib

    def json(self, json_dic):
        json_dic['exception'] = 'invalidUndoTokenError'


class NonUndoableActionError(ProtocolError):
    def __str__(self):
        return 'Unable to undo the given action'

    def json(self, json_dic):
        json_dic['exception'] = 'nonUndoableActionError'


def undo(collection, document, token):
    try:
        token = json_loads(token)
    except ValueError:
        raise CorruptUndoTokenError
    try:
        action = token['action']
    except KeyError:
        raise InvalidTokenError('action')

    if action == 'add_tb':
        # Undo an addition
        return delete_span(collection, document, token['id'])
    if action == 'mod_tb':
        # Undo a modification
        # TODO: We do not handle attributes and comments
        return create_span(collection, document, token['start'], token['end'],
                token['type'], id=token['id'], attributes=token['attributes'],
                comment=token['comment'] if 'comment' in token else None)
    else:
        raise NonUndoableActionError
    assert False, 'should have returned prior to this point'

if __name__ == '__main__':
    # XXX: Path to...
    pass

########NEW FILE########
__FILENAME__ = verify_annotations
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Verification of BioNLP Shared Task - style annotations.

from __future__ import with_statement

import annotation

from projectconfig import ProjectConfiguration

# Issue types. Values should match with annotation interface.
AnnotationError = "AnnotationError"
AnnotationWarning = "AnnotationWarning"
AnnotationIncomplete = "AnnotationIncomplete"

class AnnotationIssue:
    """
    Represents an issue noted in verification of annotations.
    """

    _next_id_idx = 1

    def __init__(self, ann_id, type, description=""):
        self.id = "#%d" % AnnotationIssue._next_id_idx
        AnnotationIssue._next_id_idx += 1
        self.ann_id, self.type, self.description = ann_id, type, description
        if self.description is None:
            self.description = ""

    def human_readable_str(self):
        return "%s: %s\t%s" % (self.ann_id, self.type, self.description)

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id, self.type, self.ann_id, self.description)

def event_nonum_args(e):
    """
    Given an EventAnnotatation, returns its arguments without trailing
    numbers (e.g. "Theme1" -> "Theme").
    """
    from re import match as re_match

    nna = {}
    for arg, aid in e.args:
        m = re_match(r'^(.*?)\d*$', arg)
        if m:
            arg = m.group(1)
        if arg not in nna:
            nna[arg] = []
        nna[arg].append(aid)
    return nna

def event_nonum_arg_count(e):
    """
    Given an EventAnnotation, returns a dictionary containing for each
    of its argument without trailing numbers (e.g. "Theme1" ->
    "Theme") the number of times the argument appears.
    """
    from re import match as re_match

    nnc = {}
    for arg, aid in e.args:
        m = re_match(r'^(.*?)\d*$', arg)
        if m:
            arg = m.group(1)
        nnc[arg] = nnc.get(arg, 0) + 1
    return nnc

def check_textbound_overlap(anns):
    """
    Checks for overlap between the given TextBoundAnnotations.
    Returns a list of pairs of overlapping annotations.
    """
    overlapping = []

    for a1 in anns:
        for a2 in anns:
            if a1 is a2:
                continue
            if (a2.first_start() < a1.last_end() and
                a2.last_end() > a1.first_start()):
                overlapping.append((a1,a2))

    return overlapping

def verify_equivs(ann_obj, projectconf):
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    for eq in ann_obj.get_equivs():
        # get the equivalent annotations
        equiv_anns = [ann_obj.get_ann_by_id(eid) for eid in eq.entities]

        # all pairs of entity types in the Equiv group must be allowed
        # to have an Equiv. Create type-level pairs to avoid N^2
        # search where N=entities.
        eq_type = {}
        for e in equiv_anns:
            eq_type[e.type] = True
        type_pairs = []
        for t1 in eq_type:
            for t2 in eq_type:
                type_pairs.append((t1,t2))

        # do avoid marking both (a1,a2) and (a2,a1), remember what's
        # already included
        marked = {}

        for t1, t2 in type_pairs:
            reltypes = projectconf.relation_types_from_to(t1, t2)
            # TODO: this is too convoluted; use projectconf directly
            equiv_type_found = False
            for rt in reltypes:
                if projectconf.is_equiv_type(rt):
                    equiv_type_found = True
            if not equiv_type_found:
                # Avoid redundant output
                if (t2,t1) in marked:
                    continue
                # TODO: mark this error on the Eq relation, not the entities
                for e in equiv_anns:
                    issues.append(AnnotationIssue(e.id, AnnotationError, "Equivalence relation %s not allowed between %s and %s" % (eq.type, disp(t1), disp(t2))))
                marked[(t1,t2)] = True

    return issues

def verify_entity_overlap(ann_obj, projectconf):
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    # check for overlap between physical entities
    physical_entities = [a for a in ann_obj.get_textbounds() if projectconf.is_physical_entity_type(a.type)]
    overlapping = check_textbound_overlap(physical_entities)
    for a1, a2 in overlapping:
        if a1.same_span(a2):
            if not projectconf.spans_can_be_equal(a1.type, a2.type):
                issues.append(AnnotationIssue(a1.id, AnnotationError, "Error: %s cannot have identical span with %s %s" % (disp(a1.type), disp(a2.type), a2.id)))            
        elif a2.contains(a1):
            if not projectconf.span_can_contain(a1.type, a2.type):
                issues.append(AnnotationIssue(a1.id, AnnotationError, "Error: %s cannot be contained in %s (%s)" % (disp(a1.type), disp(a2.type), a2.id)))
        elif a1.contains(a2):
            if not projectconf.span_can_contain(a2.type, a1.type):
                issues.append(AnnotationIssue(a1.id, AnnotationError, "Error: %s cannot contain %s (%s)" % (disp(a1.type), disp(a2.type), a2.id)))
        else:
            if not projectconf.spans_can_cross(a1.type, a2.type):
                issues.append(AnnotationIssue(a1.id, AnnotationError, "Error: annotation cannot have crossing span with %s" % a2.id))
    
    # TODO: generalize to other cases
    return issues

def verify_annotation_types(ann_obj, projectconf):
    issues = []

    event_types = projectconf.get_event_types()
    textbound_types = event_types + projectconf.get_entity_types()
    relation_types = projectconf.get_relation_types()

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    for e in ann_obj.get_events():
        if e.type not in event_types:
            issues.append(AnnotationIssue(e.id, AnnotationError, "Error: %s is not a known event type (check configuration?)" % disp(e.type)))

    for t in ann_obj.get_textbounds():
        if t.type not in textbound_types:
            issues.append(AnnotationIssue(t.id, AnnotationError, "Error: %s is not a known textbound type (check configuration?)" % disp(t.type)))

    for r in ann_obj.get_relations():
        if r.type not in relation_types:
            issues.append(AnnotationIssue(r.id, AnnotationError, "Error: %s is not a known relation type (check configuration?)" % disp(r.type)))

    return issues

def verify_triggers(ann_obj, projectconf):
    issues = []

    events_by_trigger = {}

    for e in ann_obj.get_events():
        if e.trigger not in events_by_trigger:
            events_by_trigger[e.trigger] = []
        events_by_trigger[e.trigger].append(e)

    trigger_by_span_and_type = {}

    for t in ann_obj.get_textbounds():
        if not projectconf.is_event_type(t.type):
            continue

        if t.id not in events_by_trigger:
            issues.append(AnnotationIssue(t.id, AnnotationIncomplete, "Warning: trigger %s is not referenced from any event" % t.id))

        spt = tuple(set(t.spans))+(t.type,)
        if spt not in trigger_by_span_and_type:
            trigger_by_span_and_type[spt] = []
        trigger_by_span_and_type[spt].append(t)

    for spt in trigger_by_span_and_type:
        trigs = trigger_by_span_and_type[spt]
        if len(trigs) < 2:
            continue
        for t in trigs:
            # We currently need to attach these to events if there are
            # any; issues attached to triggers referenced from events
            # don't get shown. TODO: revise once this is fixed.
            if t.id in events_by_trigger:
                issues.append(AnnotationIssue(events_by_trigger[t.id][0].id, AnnotationWarning, "Warning: triggers %s have identical span and type (harmless but unnecessary duplication)" % ",".join([x.id for x in trigs])))
            else:
                issues.append(AnnotationIssue(t.id, AnnotationWarning, "Warning: triggers %s have identical span and type (harmless but unnecessary duplication)" % ",".join([x.id for x in trigs])))

    return issues

def _relation_labels_match(rel, rel_conf):
    if len(rel_conf.arg_list) != 2:
        # likely misconfigured relation, can't match
        return False
    return (rel.arg1l == rel_conf.arg_list[0] and
            rel.arg2l == rel_conf.arg_list[1])

def verify_relations(ann_obj, projectconf):
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    # TODO: rethink this function.
    for r in ann_obj.get_relations():
        a1 = ann_obj.get_ann_by_id(r.arg1)
        a2 = ann_obj.get_ann_by_id(r.arg2)
        match_found = False

        # check for argument order a1, a2
        if r.type in projectconf.relation_types_from_to(a1.type, a2.type):
            # found for argument order a1, a2; check labels
            conf_rels = projectconf.get_relations_by_type(r.type)
            if any(c for c in conf_rels if _relation_labels_match(r, c)):
                match_found = True
        if match_found:
            continue

        # no match for argument order a1, a2; try a2, a1
        # temp inversion for check
        r.arg1, r.arg2, r.arg1l, r.arg2l = r.arg2, r.arg1, r.arg2l, r.arg1l
        if r.type in projectconf.relation_types_from_to(a2.type, a1.type):
            conf_rels = projectconf.get_relations_by_type(r.type)
            if any(c for c in conf_rels if _relation_labels_match(r, c)):
                match_found = True
        r.arg1, r.arg2, r.arg1l, r.arg2l = r.arg2, r.arg1, r.arg2l, r.arg1l
        if match_found:
            continue            

        # not found for either argument order
        issues.append(AnnotationIssue(r.id, AnnotationError, "Error: %s relation %s:%s %s:%s not allowed" % (disp(r.type), r.arg1l, disp(a1.type), r.arg2l, disp(a2.type))))

    return issues

def verify_missing_arguments(ann_obj, projectconf):
    """
    Checks for events having too few mandatory arguments.
    """
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)
    
    for e in ann_obj.get_events():
        nonum_arg_counts = event_nonum_arg_count(e)
        for m in projectconf.mandatory_arguments(e.type):
            c = nonum_arg_counts.get(m, 0)
            amin = projectconf.argument_minimum_count(e.type, m)
            amax = projectconf.argument_maximum_count(e.type, m)
            if c < amin:
                # insufficient, pick appropriate string and add issue
                if amin == 1:
                    countstr = "one %s argument " % disp(m)
                else:
                    countstr = "%d %s arguments " % (amin, disp(m))
                if amin == amax:
                    countstr = "exactly " + countstr
                else:
                    countstr = "at least " + countstr
                issues.append(AnnotationIssue(e.id, AnnotationIncomplete, 
                                              "Incomplete: " + countstr + "required for event"))

    return issues

def verify_disallowed_arguments(ann_obj, projectconf):
    """
    Checks for events with arguments they are not allowed to
    have.
    """
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    for e in ann_obj.get_events():
        allowed = projectconf.arc_types_from(e.type)
        eargs = event_nonum_args(e)
        for a in eargs:
            if a not in allowed:
                issues.append(AnnotationIssue(e.id, AnnotationError, "Error: %s cannot take a %s argument" % (disp(e.type), disp(a))))
            else:
                for rid in eargs[a]:
                    r = ann_obj.get_ann_by_id(rid)
                    if a not in projectconf.arc_types_from_to(e.type, r.type):
                        issues.append(AnnotationIssue(e.id, AnnotationError, "Error: %s argument %s cannot be of type %s" % (disp(e.type), disp(a), disp(r.type))))

    return issues

def verify_extra_arguments(ann_obj, projectconf):
    """
    Checks for events with excessively many allowed arguments.
    """
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    for e in ann_obj.get_events():
        nonum_arg_counts = event_nonum_arg_count(e)
        multiple_allowed = projectconf.multiple_allowed_arguments(e.type)
        for a in [m for m in nonum_arg_counts if nonum_arg_counts[m] > 1]:
            amax = projectconf.argument_maximum_count(e.type, a)
            if a not in multiple_allowed:
                issues.append(AnnotationIssue(e.id, AnnotationError, "Error: %s cannot take multiple %s arguments" % (disp(e.type), disp(a))))
            elif nonum_arg_counts[a] > amax:
                issues.append(AnnotationIssue(e.id, AnnotationError, "Error: %s can take at most %d %s arguments" % (disp(e.type), amax, disp(a))))
    
    return issues

def verify_attributes(ann_obj, projectconf):
    """
    Checks for instances of attributes attached to annotations that
    are not allowed to have them.
    """
    issues = []

    # shortcut
    def disp(s):
        return projectconf.preferred_display_form(s)

    for a in ann_obj.get_attributes():
        tid = a.target
        t = ann_obj.get_ann_by_id(tid)
        allowed = projectconf.attributes_for(t.type)
        
        if a.type not in allowed:
            issues.append(AnnotationIssue(t.id, AnnotationError, "Error: %s cannot take a %s attribute" % (disp(t.type), disp(a.type))))

    return issues

def verify_annotation(ann_obj, projectconf):
    """
    Verifies the correctness of a given AnnotationFile.
    Returns a list of AnnotationIssues.
    """
    issues = []

    issues += verify_annotation_types(ann_obj, projectconf)

    issues += verify_equivs(ann_obj, projectconf)

    issues += verify_entity_overlap(ann_obj, projectconf)

    issues += verify_triggers(ann_obj, projectconf)

    issues += verify_relations(ann_obj, projectconf)

    issues += verify_missing_arguments(ann_obj, projectconf)

    issues += verify_disallowed_arguments(ann_obj, projectconf)

    issues += verify_extra_arguments(ann_obj, projectconf)

    issues += verify_attributes(ann_obj, projectconf)
    
    return issues

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Verify BioNLP Shared Task annotations.")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("files", metavar="FILE", nargs="+", help="Files to verify.")
    return ap

def main(argv=None):
    import sys
    import os

    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    for fn in arg.files:
        try:
            projectconf = ProjectConfiguration(os.path.dirname(fn))
            # remove ".a2" or ".rel" suffixes for Annotations to prompt
            # parsing of .a1 also.
            # (TODO: temporarily removing .ann also to work around a
            # bug in TextAnnotations, but this should not be necessary.)
            nosuff_fn = fn.replace(".a2","").replace(".rel","").replace(".ann","")
            with annotation.TextAnnotations(nosuff_fn) as ann_obj:
                issues = verify_annotation(ann_obj, projectconf)
                for i in issues:
                    print "%s:\t%s" % (fn, i.human_readable_str())
        except annotation.AnnotationFileNotFoundError:
            print >> sys.stderr, "%s:\tFailed check: file not found" % fn
        except annotation.AnnotationNotFoundError, e:
            print >> sys.stderr, "%s:\tFailed check: %s" % (fn, e)

    if arg.verbose:
        print >> sys.stderr, "Check complete."

if __name__ == "__main__":
    import sys
    sys.exit(main())

########NEW FILE########
__FILENAME__ = standalone
#!/usr/bin/env python

# Minimal standalone brat server based on SimpleHTTPRequestHandler.

# Run as apache, e.g. as
#
#     APACHE_USER=`./apache-user.sh`
#     sudo -u $APACHE_USER python standalone.py

import sys
import os

from posixpath import normpath
from urllib import unquote

from cgi import FieldStorage
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ForkingMixIn
import socket

# brat imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'server/src'))
from server import serve

# pre-import everything possible (TODO: prune unnecessary)
import annlog
import annotation
import annotator
import auth
import common
import delete
import dispatch
import docimport
import document
import download
import filelock
import gtbtokenize
import jsonwrap
import message
import normdb
import norm
import predict
import projectconfig
import realmessage
import sdistance
import search
import server
import session
import simstringdb
import sosmessage
import ssplit
import sspostproc
import stats
import svg
import tag
import tokenise
import undo
import verify_annotations

_VERBOSE_HANDLER = False
_DEFAULT_SERVER_ADDR = ''
_DEFAULT_SERVER_PORT = 8001

_PERMISSIONS = """
Allow: /ajax.cgi
Disallow: *.py
Disallow: *.cgi
Disallow: /.htaccess
Disallow: *.py~  # no emacs backups
Disallow: *.cgi~
Disallow: /.htaccess~
Allow: /
"""

class PermissionParseError(Exception):
    def __init__(self, linenum, line, message=None):
        self.linenum = linenum
        self.line = line
        self.message = ' (%s)' % message if message is not None else ''
    
    def __str__(self):
        return 'line %d%s: %s' % (self.linenum, self.message, self.line)

class PathPattern(object):
    def __init__(self, path):
        self.path = path
        self.plen = len(path)

    def match(self, s):
        # Require prefix match and separator/end.
        return s[:self.plen] == self.path and (self.path[-1] == '/' or
                                               s[self.plen:] == '' or 
                                               s[self.plen] == '/')

class ExtensionPattern(object):
    def __init__(self, ext):
        self.ext = ext

    def match(self, s):
        return os.path.splitext(s)[1] == self.ext

class PathPermissions(object):
    """Implements path permission checking with a robots.txt-like syntax."""

    def __init__(self, default_allow=False):
        self._entries = []
        self.default_allow = default_allow

    def allow(self, path):
        # First match wins
        for pattern, allow in self._entries:
            if pattern.match(path):
                return allow
        return self.default_allow
    
    def parse(self, lines):
        # Syntax: "DIRECTIVE : PATTERN" where
        # DIRECTIVE is either "Disallow:" or "Allow:" and
        # PATTERN either has the form "*.EXT" or "/PATH".
        # Strings starting with "#" and empty lines are ignored.

        for ln, l in enumerate(lines):            
            i = l.find('#')
            if i != -1:
                l = l[:i]
            l = l.strip()

            if not l:
                continue

            i = l.find(':')
            if i == -1:
                raise PermissionParseError(ln, lines[ln], 'missing colon')

            directive = l[:i].strip().lower()
            pattern = l[i+1:].strip()

            if directive == 'allow':
                allow = True
            elif directive == 'disallow':
                allow = False
            else:
                raise PermissionParseError(ln, lines[ln], 'unrecognized directive')
            
            if pattern.startswith('/'):
                patt = PathPattern(pattern)
            elif pattern.startswith('*.'):
                patt = ExtensionPattern(pattern[1:])
            else:
                raise PermissionParseError(ln, lines[ln], 'unrecognized pattern')

            self._entries.append((patt, allow))

        return self

class BratHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Minimal handler for brat server."""

    permissions = PathPermissions().parse(_PERMISSIONS.split('\n'))

    def log_request(self, code='-', size='-'):
        if _VERBOSE_HANDLER:
            SimpleHTTPRequestHandler.log_request(self, code, size)
        else:
            # just ignore logging
            pass

    def is_brat(self):
        # minimal cleanup
        path = self.path
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]

        if path == '/ajax.cgi':
            return True
        else:
            return False    

    def run_brat_direct(self):
        """Execute brat server directly."""

        remote_addr = self.client_address[0]
        remote_host = self.address_string()
        cookie_data = ', '.join(filter(None, self.headers.getheaders('cookie')))

        query_string = ''
        i = self.path.find('?')
        if i != -1:
            query_string = self.path[i+1:]
            
        saved = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout = self.rfile, self.wfile

        # set env to get FieldStorage to read params
        env = {}
        env['REQUEST_METHOD'] = self.command
        content_length = self.headers.getheader('content-length')
        if content_length:
            env['CONTENT_LENGTH'] = content_length
        if query_string:
            env['QUERY_STRING'] = query_string
        os.environ.update(env)
        params = FieldStorage()

        # Call main server
        cookie_hdrs, response_data = serve(params, remote_addr, remote_host,
                                           cookie_data)

        sys.stdin, sys.stdout, sys.stderr = saved

        # Package and send response
        if cookie_hdrs is not None:
            response_hdrs = [hdr for hdr in cookie_hdrs]
        else:
            response_hdrs = []
        response_hdrs.extend(response_data[0])

        self.send_response(200)
        self.wfile.write('\n'.join('%s: %s' % (k, v) for k, v in response_hdrs))
        self.wfile.write('\n')
        self.wfile.write('\n')
        # Hack to support binary data and general Unicode for SVGs and JSON
        if isinstance(response_data[1], unicode):
            self.wfile.write(response_data[1].encode('utf-8'))
        else:
            self.wfile.write(response_data[1])
        return 0

    def allow_path(self):
        """Test whether to allow a request for self.path."""

        # Cleanup in part following SimpleHTTPServer.translate_path()
        path = self.path
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = unquote(path)
        path = normpath(path)
        parts = path.split('/')
        parts = filter(None, parts)
        if '..' in parts:
            return False
        path = '/'+'/'.join(parts)

        return self.permissions.allow(path)

    def list_directory(self, path):
        """Override SimpleHTTPRequestHandler.list_directory()"""
        # TODO: permissions for directory listings
        self.send_error(403)

    def do_POST(self):
        """Serve a POST request. Only implemented for brat server."""

        if self.is_brat():
            self.run_brat_direct()
        else:
            self.send_error(501, "Can only POST to brat")

    def do_GET(self):
        """Serve a GET request."""
        if not self.allow_path():
            self.send_error(403)
        elif self.is_brat():
            self.run_brat_direct()
        else:
            SimpleHTTPRequestHandler.do_GET(self)

    def do_HEAD(self):
        """Serve a HEAD request."""
        if not self.allow_path():
            self.send_error(403)
        else:
            SimpleHTTPRequestHandler.do_HEAD(self)
       
class BratServer(ForkingMixIn, HTTPServer):
    def __init__(self, server_address):
        HTTPServer.__init__(self, server_address, BratHTTPRequestHandler)

def main(argv):
    # warn if root/admin
    try:
        if os.getuid() == 0:
            print >> sys.stderr, """
! WARNING: running as root. The brat standalone server is experimental   !
! and may be a security risk. It is recommend to run the standalone      !
! server as a non-root user with write permissions to the brat work/ and !
! data/ directories (e.g. apache if brat is set up using standard        !
! installation).                                                         !
"""
    except AttributeError:
        # not on UNIX
        print >> sys.stderr, """
Warning: could not determine user. Note that the brat standalone
server is experimental and should not be run as administrator.
"""

    if len(argv) > 1:
        try:
            port = int(argv[1])
        except ValueError:
            print >> sys.stderr, "Failed to parse", argv[1], "as port number."
            return 1
    else:
        port = _DEFAULT_SERVER_PORT

    try:
        server = BratServer((_DEFAULT_SERVER_ADDR, port))
        print >> sys.stderr, "Serving brat at http://%s:%d" % server.server_address
        server.serve_forever()
    except KeyboardInterrupt:
        # normal exit
        pass
    except socket.error, why:
        print >> sys.stderr, "Error binding to port", port, ":", why[1]
    except Exception, e:
        print >> sys.stderr, "Server error", e
        raise
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = testserver
#!/usr/bin/env python

'''
Run brat using the built-in Python CGI server for testing purposes.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-07-01
'''

from BaseHTTPServer import HTTPServer, test as simple_http_server_test
from CGIHTTPServer import CGIHTTPRequestHandler
# Note: It is a terrible idea to import the function below, but we don't have
#   a choice if we want to emulate the super-class is_cgi method.
from CGIHTTPServer import _url_collapse_path_split
from sys import stderr
from urlparse import urlparse

# Note: The only reason that we sub-class in order to pull is the stupid
#   is_cgi method that assumes the usage of specific CGI directories, I simply
#   refuse to play along with this kind of non-sense.
class BRATCGIHTTPRequestHandler(CGIHTTPRequestHandler):
    def is_cgi(self):
        # Having a CGI suffix is really a big hint of being a CGI script.
        if urlparse(self.path).path.endswith('.cgi'):
            self.cgi_info = _url_collapse_path_split(self.path)
            return True
        else:
            return CGIHTTPRequestHandler.is_cgi(self)

def main(args):
    # BaseHTTPServer will look for the port in argv[1] or default to 8000
    try:
        try:
            port = int(args[1])
        except ValueError:
            raise TypeError
    except TypeError:
        print >> stderr, '%s is not a valid port number' % args[1]
        return -1
    except IndexError:
        port = 8000
    print >> stderr, 'WARNING: This server is for testing purposes only!'
    print >> stderr, ('    You can also use it for trying out brat before '
            'deploying on a "real" web server such as Apache.')
    print >> stderr, ('    Using this web server to run brat on an open '
            'network is a security risk!')
    print >> stderr
    print >> stderr, 'You can access the test server on:'
    print >> stderr
    print >> stderr, '    http://localhost:%s/' % port
    print >> stderr
    simple_http_server_test(BRATCGIHTTPRequestHandler, HTTPServer)

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = anncut
#!/usr/bin/env python

# Remove portions of text from annotated files.

# Note: not comprehensively tested, use with caution.

from __future__ import with_statement

import sys
import re

try:
    import argparse
except ImportError:
    from os.path import basename
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(join_path(basename(__file__), '../server/lib'))
    import argparse


class ArgumentError(Exception):
    def __init__(self, s):
        self.errstr = s

    def __str__(self):
        return 'Argument error: %s' % (self.errstr)

def argparser():
    ap=argparse.ArgumentParser(description="Remove portions of text from annotated files.")
    ap.add_argument("-c", "--characters", metavar="[LIST]", default=None,
                    help="Select only these characters")
    ap.add_argument("--complement", default=False, action="store_true",
                    help="Complement the selected spans of text")
    ap.add_argument("file", metavar="FILE", nargs=1, 
                    help="Annotation file")
    return ap
                    
class Annotation(object):
    def __init__(self, id_, type_):
        self.id_ = id_
        self.type_ = type_

    def in_range(self, _):
        # assume not text-bound: in any range
        return True

    def remap(self, _):
        # assume not text-bound: no-op
        return None

class Textbound(Annotation):
    def __init__(self, id_, type_, offsets, text):
        Annotation.__init__(self, id_, type_)
        self.text = text

        self.offsets = []
        if ';' in offsets:
            # not tested w/discont, so better not to try
            raise NotImplementedError('Discontinuous annotations not supported')
        assert len(offsets) == 2, "Data format error"
        self.offsets.append((int(offsets[0]), int(offsets[1])))

    def in_range(self, selection):
        for start, end in self.offsets:
            if not selection.in_range(start, end):
                return False
        return True

    def remap(self, selection):
        remapped = []
        for start, end in self.offsets:
            remapped.append(selection.remap(start, end))
        self.offsets = remapped

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, 
                                  ';'.join(['%d %d' % (s, e)
                                            for s, e in self.offsets]),
                                  self.text)
class ArgAnnotation(Annotation):
    def __init__(self, id_, type_, args):
        Annotation.__init__(self, id_, type_)
        self.args = args

class Relation(ArgAnnotation):
    def __init__(self, id_, type_, args):
        ArgAnnotation.__init__(self, id_, type_, args)

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.args))

class Event(ArgAnnotation):
    def __init__(self, id_, type_, trigger, args):
        ArgAnnotation.__init__(self, id_, type_, args)
        self.trigger = trigger

    def __str__(self):
        return "%s\t%s:%s %s" % (self.id_, self.type_, self.trigger, 
                                 ' '.join(self.args))

class Attribute(Annotation):
    def __init__(self, id_, type_, target, value):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.value = value

    def __str__(self):
        return "%s\t%s %s%s" % (self.id_, self.type_, self.target, 
                                '' if self.value is None else ' '+self.value)

class Normalization(Annotation):
    def __init__(self, id_, type_, target, ref, reftext):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.ref = ref
        self.reftext = reftext

    def __str__(self):
        return "%s\t%s %s %s\t%s" % (self.id_, self.type_, self.target,
                                     self.ref, self.reftext)

class Equiv(Annotation):
    def __init__(self, id_, type_, targets):
        Annotation.__init__(self, id_, type_)
        self.targets = targets

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.targets))

class Note(Annotation):
    def __init__(self, id_, type_, target, text):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.text = text

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, self.target, self.text)

def parse_textbound(fields):
    id_, type_offsets, text = fields
    type_offsets = type_offsets.split(' ')
    type_, offsets = type_offsets[0], type_offsets[1:]
    return Textbound(id_, type_, offsets, text)

def parse_relation(fields):
    # allow a variant where the two initial TAB-separated fields are
    # followed by an extra tab
    if len(fields) == 3 and not fields[2]:
        fields = fields[:2]
    id_, type_args = fields
    type_args = type_args.split(' ')
    type_, args = type_args[0], type_args[1:]
    return Relation(id_, type_, args)

def parse_event(fields):
    id_, type_trigger_args = fields
    type_trigger_args = type_trigger_args.split(' ')
    type_trigger, args = type_trigger_args[0], type_trigger_args[1:]
    type_, trigger = type_trigger.split(':')
    return Event(id_, type_, trigger, args)

def parse_attribute(fields):
    id_, type_target_value = fields
    type_target_value = type_target_value.split(' ')
    if len(type_target_value) == 3:
        type_, target, value = type_target_value
    else:
        type_, target = type_target_value
        value = None
    return Attribute(id_, type_, target, value)

def parse_normalization(fields):
    id_, type_target_ref, reftext = fields
    type_, target, ref = type_target_ref.split(' ')
    return Normalization(id_, type_, target, ref, reftext)

def parse_note(fields):
    id_, type_target, text = fields
    type_, target = type_target.split(' ')
    return Note(id_, type_, target, text)

def parse_equiv(fields):
    id_, type_targets = fields
    type_targets = type_targets.split(' ')
    type_, targets = type_targets[0], type_targets[1:]
    return Equiv(id_, type_, targets)

parse_func = {
    'T': parse_textbound,
    'R': parse_relation,
    'E': parse_event,
    'N': parse_normalization,
    'M': parse_attribute,
    'A': parse_attribute,
    '#': parse_note,
    '*': parse_equiv,
    }

def parse(l, ln):
    assert len(l) and l[0] in parse_func, "Error on line %d: %s" % (ln, l)
    try:
        return parse_func[l[0]](l.split('\t'))
    except Exception:
        assert False, "Error on line %d: %s" % (ln, l)

def process(fn, selection):
    with open(fn, "rU") as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

        annotations = []
        for i, l in enumerate(lines):
            annotations.append(parse(l, i+1))

    for a in annotations:
        if not a.in_range(selection):
            # deletes TODO
            raise NotImplementedError('Deletion of annotations TODO')
        else:
            a.remap(selection)

    for a in annotations:
        print a

class Selection(object):
    def __init__(self, options):
        self.complement = options.complement

        if options.characters is None:
            raise ArgumentError('Please specify the charaters')

        self.ranges = []
        for range in options.characters.split(','):
            try:
                start, end = range.split('-')
                start, end = int(start), int(end)
                assert start >= end and start >= 1

                # adjust range: CLI arguments are counted from 1 and
                # inclusive of the character at the end offset,
                # internal processing is 0-based and exclusive of the
                # character at the end offset. (end is not changed as
                # these two cancel each other out.)
                start -= 1

                self.ranges.append((start, end))
            except Exception:
                raise ArgumentError('Invalid range "%s"' % range)

        self.ranges.sort()

        # initialize offset map up to end of given ranges
        self.offset_map = {}
        o, m = 0, 0
        if not self.complement:
            for start, end in self.ranges:
                while o < start:
                    self.offset_map[o] = None
                    o += 1
                while o < end:
                    self.offset_map[o] = m
                    o += 1
                    m += 1
        else:
            for start, end in self.ranges:
                while o < start:
                    self.offset_map[o] = m
                    o += 1
                    m += 1
                while o < end:
                    self.offset_map[o] = None
                    o += 1

        self.max_offset = o
        self.max_mapped = m

        # debugging
        # print >> sys.stderr, self.offset_map

    def in_range(self, start, end):
        for rs, re in self.ranges:
            if start >= rs and start < re:
                if end >= rs and end < re:
                    return not self.complement
                else:
                    raise NotImplementedError('Annotations partially included in range not supported')
        return self.complement

    def remap_single(self, offset):
        assert offset >= 0, "INTERNAL ERROR"
        if offset < self.max_offset:
            assert offset in self.offset_map, "INTERNAL ERROR"
            o = self.offset_map[offset]
            assert o is not None, "Error: remap for excluded offset %d" % offset
            return o
        else:
            assert self.complement, "Error: remap for excluded offset %d" % offset
            # all after max_offset included, so 1-to-1 mapping past that
            return self.max_mapped + (offset-self.max_offset)

    def remap(self, start, end):
        # end-exclusive to end-inclusive
        end -= 1

        start, end = self.remap_single(start), self.remap_single(end)

        # end-inclusive to end-exclusive
        end += 1

        return (start, end)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    try:
        selection = Selection(arg)
    except Exception, e:
        print >> sys.stderr, e
        argparser().print_help()
        return 1        

    for fn in arg.file:
        process(fn, selection)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = anneval
#!/usr/bin/env python

'''
Parse an annotation log and extract annotation statistics.

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-11-25
'''

from argparse import ArgumentParser

### Constants
ARGPARSER = ArgumentParser()#XXX:
ARGPARSER.add_argument('ann_log', nargs='+')
###

from collections import namedtuple
from datetime import datetime
from sys import stderr

# TODO: Some arguments left out
LogLine = namedtuple('LogLine', ('time', 'user', 'collection', 'document',
        'state', 'action', 'line_no'))

def _parse_log_iter(log):
    for line_no, line in enumerate((l.rstrip('\n') for l in log)):
        date_stamp, time_stamp, user, collection, document, state, action = line.split()[:7]
        dtime = datetime.strptime('%s %s' % (date_stamp, time_stamp, ),
                '%Y-%m-%d %H:%M:%S,%f')
        yield LogLine(
                time=dtime,
                user=user,
                collection=collection,
                document=document,
                state=state,
                action=action,
                line_no=line_no,
                )
        
Action = namedtuple('Action', ('start', 'end', 'action'))

# TODO: Give actions and sub actions
def _action_iter(log_lines):
    start_by_action = {}
    for log_line in log_lines:
        #print >> stderr, log_line
        if log_line.state == 'START':
            start_by_action[log_line.action] = log_line
        elif log_line.state == 'FINISH':
            start_line = start_by_action[log_line.action]
            del start_by_action[log_line.action]
            yield Action(start=start_line, end=log_line,
                    action=log_line.action)

# TODO: Log summary object

def main(args):
    argp = ARGPARSER.parse_args(args[1:])
    
    for ann_log_path in argp.ann_log:
        with open(ann_log_path, 'r') as ann_log:
            log_lines = []
            for log_line in _parse_log_iter(ann_log):
                assert log_line.state in set(('START', 'FINISH',) ), 'unknown logged state'
                log_lines.append(log_line)

        clock_time = log_lines[-1].time - log_lines[0].time
        print >> stderr, 'Clock time:', clock_time
        from datetime import timedelta
        ann_time = timedelta()
        last_span_selected = None
        for action in _action_iter(log_lines):
            if (action.action == 'spanSelected'
                    or action.action == 'spanEditSelected'
                    or action.action == 'suggestSpanTypes'):
                last_span_selected = action

            if action.action == 'createSpan':
                ann_time = ann_time + (action.end.time - last_span_selected.start.time)
                last_span_selected = None
            #print action
        ann_port_of_clock = float(ann_time.seconds) / clock_time.seconds
        print >> stderr, 'Annotation time: %s (portion of clock time: %.1f%%)' % (
                ann_time, ann_port_of_clock * 100, )

'''
Ordinary sequence:
    * spanSelected
    * createSpan
'''

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = anntoconll
#!/usr/bin/env python

# Convert text and standoff annotations into CoNLL format.

from __future__ import with_statement

import sys
import re
import os

from collections import namedtuple
from os import path
from subprocess import Popen, PIPE
from cStringIO import StringIO

# assume script in brat tools/ directory, extend path to find sentencesplit.py
sys.path.append(os.path.join(os.path.dirname(__file__), '../server/src'))
sys.path.append('.')
from sentencesplit import sentencebreaks_to_newlines

options = None

EMPTY_LINE_RE = re.compile(r'^\s*$')
CONLL_LINE_RE = re.compile(r'^\S+\t\d+\t\d+.')

class FormatError(Exception):
    pass

def argparser():
    import argparse
    
    ap=argparse.ArgumentParser(description='Convert text and standoff ' +
                               'annotations into CoNLL format.')
    ap.add_argument('-a', '--annsuffix', default="ann",
                    help='Standoff annotation file suffix (default "ann")')
    ap.add_argument('-c', '--singleclass', default=None,
                    help='Use given single class for annotations')
    ap.add_argument('-n', '--nosplit', default=False, action='store_true', 
                    help='No sentence splitting')
    ap.add_argument('-o', '--outsuffix', default="conll",
                    help='Suffix to add to output files (default "conll")')
    ap.add_argument('-v', '--verbose', default=False, action='store_true', 
                    help='Verbose output')    
    ap.add_argument('text', metavar='TEXT', nargs='+', 
                    help='Text files ("-" for STDIN)')
    return ap

def read_sentence(f):
    """Return lines for one sentence from the CoNLL-formatted file.
    Sentences are delimited by empty lines.
    """

    lines = []
    for l in f:
        lines.append(l)
        if EMPTY_LINE_RE.match(l):
            break
        if not CONLL_LINE_RE.search(l):
            raise FormatError('Line not in CoNLL format: "%s"' % l.rstrip('\n'))
    return lines

def strip_labels(lines):
    """Given CoNLL-format lines, strip the label (first TAB-separated
    field) from each non-empty line. Return list of labels and list
    of lines without labels. Returned list of labels contains None
    for each empty line in the input.
    """

    labels, stripped = [], []

    labels = []
    for l in lines:
        if EMPTY_LINE_RE.match(l):
            labels.append(None)
            stripped.append(l)
        else:
            fields = l.split('\t')
            labels.append(fields[0])
            stripped.append('\t'.join(fields[1:]))

    return labels, stripped

def attach_labels(labels, lines):
    """Given a list of labels and CoNLL-format lines, affix
    TAB-separated label to each non-empty line. Returns list of lines
    with attached labels.
    """

    assert len(labels) == len(lines), "Number of labels (%d) does not match number of lines (%d)" % (len(labels), len(lines))

    attached = []
    for label, line in zip(labels, lines):
        empty = EMPTY_LINE_RE.match(line)
        assert (label is None and empty) or (label is not None and not empty)

        if empty:
            attached.append(line)
        else:
            attached.append('%s\t%s' % (label, line))

    return attached

# NERsuite tokenization: any alnum sequence is preserved as a single
# token, while any non-alnum character is separated into a
# single-character token. TODO: non-ASCII alnum.
TOKENIZATION_REGEX = re.compile(r'([0-9a-zA-Z]+|[^0-9a-zA-Z])')

NEWLINE_TERM_REGEX = re.compile(r'(.*?\n)')

def text_to_conll(f):
    """Convert plain text into CoNLL format."""
    global options

    if options.nosplit:
        sentences = f.readlines()
    else:
        sentences = []
        for l in f:
            l = sentencebreaks_to_newlines(l)
            sentences.extend([s for s in NEWLINE_TERM_REGEX.split(l) if s])

    lines = []

    offset = 0
    for s in sentences:
        nonspace_token_seen = False

        tokens = [t for t in TOKENIZATION_REGEX.split(s) if t]

        for t in tokens:
            if not t.isspace():
                lines.append(['O', offset, offset+len(t), t])
                nonspace_token_seen = True
            offset += len(t)

        # sentences delimited by empty lines
        if nonspace_token_seen:
            lines.append([])

    # add labels (other than 'O') from standoff annotation if specified
    if options.annsuffix:
        lines = relabel(lines, get_annotations(f.name))

    lines = [[l[0], str(l[1]), str(l[2]), l[3]] if l else l for l in lines]
    return StringIO('\n'.join(('\t'.join(l) for l in lines)))

def relabel(lines, annotations):
    global options

    # TODO: this could be done more neatly/efficiently
    offset_label = {}

    for tb in annotations:
        for i in range(tb.start, tb.end):
            if i in offset_label:
                print >> sys.stderr, "Warning: overlapping annotations"
            offset_label[i] = tb

    prev_label = None
    for i, l in enumerate(lines):
        if not l:
            prev_label = None
            continue
        tag, start, end, token = l

        # TODO: warn for multiple, detailed info for non-initial
        label = None
        for o in range(start, end):
            if o in offset_label:
                if o != start:
                    print >> sys.stderr, 'Warning: annotation-token boundary mismatch: "%s" --- "%s"' % (token, offset_label[o].text)
                label = offset_label[o].type
                break

        if label is not None:
            if label == prev_label:
                tag = 'I-'+label
            else:
                tag = 'B-'+label
        prev_label = label

        lines[i] = [tag, start, end, token]

    # optional single-classing
    if options.singleclass:
        for l in lines:
            if l and l[0] != 'O':
                l[0] = l[0][:2]+options.singleclass

    return lines

def process(f):
    return text_to_conll(f)

def process_files(files):
    global options

    nersuite_proc = []

    try:
        for fn in files:
            try:
                if fn == '-':
                    lines = process(sys.stdin)
                else:
                    with open(fn, 'rU') as f:
                        lines = process(f)

                # TODO: better error handling
                if lines is None:
                    raise FormatError

                if fn == '-' or not options.outsuffix:
                    sys.stdout.write(''.join(lines))
                else:
                    ofn = path.splitext(fn)[0]+options.outsuffix
                    with open(ofn, 'wt') as of:
                        of.write(''.join(lines))

            except:
                # TODO: error processing
                raise
    except Exception, e:
        for p in nersuite_proc:
            p.kill()
        if not isinstance(e, FormatError):
            raise

########## start standoff processing

TEXTBOUND_LINE_RE = re.compile(r'^T\d+\t')

Textbound = namedtuple('Textbound', 'start end type text')

def parse_textbounds(f):
    """Parse textbound annotations in input, returning a list of
    Textbound.
    """

    textbounds = []

    for l in f:
        l = l.rstrip('\n')

        if not TEXTBOUND_LINE_RE.search(l):
            continue

        id_, type_offsets, text = l.split('\t')
        type_, start, end = type_offsets.split()
        start, end = int(start), int(end)

        textbounds.append(Textbound(start, end, type_, text))

    return textbounds

def eliminate_overlaps(textbounds):
    eliminate = {}

    # TODO: avoid O(n^2) overlap check
    for t1 in textbounds:
        for t2 in textbounds:
            if t1 is t2:
                continue
            if t2.start >= t1.end or t2.end <= t1.start:
                continue
            # eliminate shorter
            if t1.end-t1.start > t2.end-t2.start:
                print >> sys.stderr, "Eliminate %s due to overlap with %s" % (t2, t1)
                eliminate[t2] = True
            else:
                print >> sys.stderr, "Eliminate %s due to overlap with %s" % (t1, t2)
                eliminate[t1] = True

    return [t for t in textbounds if not t in eliminate]

def get_annotations(fn):
    global options

    annfn = path.splitext(fn)[0]+options.annsuffix
    
    with open(annfn, 'rU') as f:
        textbounds = parse_textbounds(f)

    textbounds = eliminate_overlaps(textbounds)

    return textbounds

########## end standoff processing

def main(argv=None):
    if argv is None:
        argv = sys.argv

    global options
    options = argparser().parse_args(argv[1:])

    # make sure we have a dot in the suffixes, if any
    if options.outsuffix and options.outsuffix[0] != '.':
        options.outsuffix = '.'+options.outsuffix
    if options.annsuffix and options.annsuffix[0] != '.':
        options.annsuffix = '.'+options.annsuffix

    process_files(options.text)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = aziitostandoff
#!/usr/bin/env python

import sys
import re
try:
    import cElementTree as ET
except:
    import xml.etree.cElementTree as ET

# tags of elements to exclude from standoff output
EXCLUDED_TAGS = [
    "SURNAME",
    "AUTHOR",
    "REFERENCE",
    "AUTHORLIST",
    "JOURNAL",
    "YEAR",
    "P",
    "TITLE",
    "DIV",
    "HEADER",
    "FIGURE",
    "XREF",
    "CURRENT_SURNAME",
    "CURRENT_AUTHOR",
    "FOOTNOTE",
    "DATE",
    "TABLE",
    "CURRENT_NAME",
    "EQN",
    "EQ-S",
    "ISSUE",
    "REFERENCELIST",
    "PAPER",
    "METADATA",
    "FILENO",
    "FIGURELIST",
    "CURRENT_TITLE",
    "CURRENT_AUTHORLIST",
    "BODY",
    "ABSTRACT",
    "FOOTNOTELIST",
    "TABLELIST",
    "ACKNOWLEDGMENTS",
    "REF",
]
EXCLUDED_TAG = { t:True for t in EXCLUDED_TAGS }

# string to use to indicate elided text in output
ELIDED_TEXT_STRING = "[[[...]]]"

# maximum length of text strings printed without elision
MAXIMUM_TEXT_DISPLAY_LENGTH = 1000

# c-style string escaping for just newline, tab and backslash.
# (s.encode('string_escape') does too much for utf-8)
def c_escape(s):
    return s.replace('\\', '\\\\').replace('\t','\\t').replace('\n','\\n')

def strip_ns(tag):
    # remove namespace spec from tag, if any
    return tag if tag[0] != '{' else re.sub(r'\{.*?\}', '', tag)

class Standoff:
    def __init__(self, sid, element, start, end, text):
        self.sid     = sid
        self.element = element
        self.start   = start
        self.end     = end
        self.text    = text

    def strip(self):
        while self.start < self.end and self.text[0].isspace():
            self.start += 1
            self.text = self.text[1:]
        while self.start < self.end and self.text[-1].isspace():
            self.end -= 1
            self.text = self.text[:-1]

    def compress_text(self, l):
        if len(self.text) >= l:
            el = len(ELIDED_TEXT_STRING)
            sl = (l-el)/2
            self.text = (self.text[:sl]+ELIDED_TEXT_STRING+self.text[-(l-sl-el):])
    def tag(self):
        return strip_ns(self.element.tag)

    def attrib(self):
        # remove namespace specs from attribute names, if any
        attrib = {}
        for a in self.element.attrib:
            if a[0] == "{":
                an = re.sub(r'\{.*?\}', '', a)
            else:
                an = a
            attrib[an] = self.element.attrib[a]
        return attrib

    def __str__(self):
        return "X%d\t%s %d %d\t%s\t%s" % \
            (self.sid, self.tag(), self.start, self.end, 
             c_escape(self.text.encode("utf-8")),
             " ".join(['%s="%s"' % (k.encode("utf-8"), v.encode("utf-8"))
                       for k,v in self.attrib().items()]))

def txt(s):
    return s if s is not None else ""

next_free_so_id = 1

def text_and_standoffs(e, curroff=0, standoffs=None):
    global next_free_so_id

    if standoffs == None:
        standoffs = []
    startoff = curroff
    # to keep standoffs in element occurrence order, append
    # a placeholder before recursing
    so = Standoff(next_free_so_id, e, 0, 0, "")
    next_free_so_id += 1
    standoffs.append(so)
    setext, dummy = subelem_text_and_standoffs(e, curroff+len(txt(e.text)), standoffs)
    text = txt(e.text) + setext
    curroff += len(text)
    so.start = startoff
    so.end   = curroff
    so.text  = text
    return (text, standoffs)

def subelem_text_and_standoffs(e, curroff, standoffs):
    startoff = curroff
    text = ""
    for s in e:
        stext, dummy = text_and_standoffs(s, curroff, standoffs)
        text += stext
        text += txt(s.tail)
        curroff = startoff + len(text)
    return (text, standoffs)

NORM_SPACE_REGEX = re.compile(r'\s+')

def normalize_space(e, tags=None):
    if tags is None or strip_ns(e.tag) in tags:
        if e.text is not None:
            n = NORM_SPACE_REGEX.sub(' ', e.text)
            e.text = n
        if e.tail is not None:
            n = NORM_SPACE_REGEX.sub(' ', e.tail)
            e.tail = n
        if strip_ns(e.tag) in ('S', 'A-S'):
            e.tail = e.tail + '\n' if e.tail else '\n'
            
    for c in e:
        normalize_space(c)

def generate_id(prefix):
    if prefix not in generate_id._next:
        generate_id._next[prefix] = 1
    id_ = prefix+str(generate_id._next[prefix])
    generate_id._next[prefix] += 1
    return id_
generate_id._next = {}

def convert_s(s):
    sostrings = []

    tid = generate_id('T')
    type_ = s.attrib()['AZ'] if 'AZ' in s.attrib() else 'UNDEF'
    sostrings.append('%s\t%s %d %d\t%s' % \
                         (tid, type_, s.start, s.end, s.text.encode("utf-8")))
    return sostrings

convert_function = {
    "S" : convert_s,
    "A-S" : convert_s,
}

def main(argv=[]):
    if len(argv) != 4:
        print >> sys.stderr, "Usage:", argv[0], "IN-XML OUT-TEXT OUT-SO"
        return -1

    in_fn, out_txt_fn, out_so_fn = argv[1:]

    # "-" for STDIN / STDOUT
    if in_fn == "-":
        in_fn = "/dev/stdin"
    if out_txt_fn == "-":
        out_txt_fn = "/dev/stdout"
    if out_so_fn == "-":
        out_so_fn = "/dev/stdout"

    tree = ET.parse(in_fn)
    root = tree.getroot()

    # normalize space in target elements
    normalize_space(root, ['S', 'A-S'])

    text, standoffs = text_and_standoffs(root)

    # eliminate extra space
    for s in standoffs:
        s.strip()

    # filter
    standoffs = [s for s in standoffs if not s.tag() in EXCLUDED_TAG]

    # convert selected elements
    converted = []
    for s in standoffs:
        if s.tag() in convert_function:
            converted.extend(convert_function[s.tag()](s))
        else:
            converted.append(s)
    standoffs = converted

    for so in standoffs:
        try:
            so.compress_text(MAXIMUM_TEXT_DISPLAY_LENGTH)
        except AttributeError:
            pass

    # open output files 
    out_txt = open(out_txt_fn, "wt")
    out_so  = open(out_so_fn, "wt")

    out_txt.write(text.encode("utf-8"))
    for so in standoffs:
        print >> out_so, so

    out_txt.close()
    out_so.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = backup
#!/usr/bin/env python

'''
Make a data back-up into the work directory.

This script is a quick hack until we come up with something better.

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-05-11
'''

from datetime import datetime
from os import mkdir, remove
from os.path import dirname, exists, basename
from os.path import join as path_join
from shlex import split as shlex_split
from subprocess import Popen
from sys import path as sys_path
from sys import stderr as sys_stderr

sys_path.append(path_join(dirname(__file__), '..'))

from config import WORK_DIR, DATA_DIR

### Constants
TOOL_BACKUP_DIR = path_join(WORK_DIR, 'bckup_tool')
###

def _safe_dirname(path):
    # Handles the case of a trailing slash for the dir path
    return basename(path) or dirname(dirname(path))

def main(args):
    if not exists(TOOL_BACKUP_DIR):
        mkdir(TOOL_BACKUP_DIR)

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M%SZ')
    backup_path = path_join(TOOL_BACKUP_DIR, '%s-%s.tar.gz' % (
        _safe_dirname(DATA_DIR), timestamp))
    data_dir_parent = path_join(DATA_DIR, '..')

    tar_cmd = 'tar -c -z -f %s -C %s %s' % (backup_path, data_dir_parent,
            _safe_dirname(DATA_DIR))
    tar_p = Popen(shlex_split(tar_cmd))
    tar_p.wait()

    if tar_p.returncode != 0:
        # We failed, remove the back-up and exit
        remove(backup_path)
        return -1
    else:
        return 0

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = BC2GMtoStandoff
#!/usr/bin/env python

# Converts the BioCreative 2 Gene Mention task data into brat-flavored
# standoff format.

from __future__ import with_statement

import sys
import re
import os

def char_offsets(text, start, end, ttext):
    # Given a text and a tagged span marked by start and end offsets
    # ignoring space (plus tagged text for reference), returns the
    # character-based offsets for the marked span. This is necessary
    # as BC2 data has offsets that ignore space. Note also that input
    # offsets are assumed inclusive of last char (ala BC2), but return
    # offsets are exclusive of last (ala BioNLP ST/brat).

    # scan to start offset
    idx, nospcidx = 0,0
    while True:
        while idx < len(text) and text[idx].isspace():
            idx += 1
        assert idx < len(text), "Error in data"
        if nospcidx == start:
            break
        nospcidx += 1
        idx += 1

    char_start = idx

    # scan to end offset
    while nospcidx < end:
        nospcidx += 1
        idx += 1
        while idx < len(text) and text[idx].isspace():
            idx += 1
        
    char_end = idx+1

    # special case allowing for slight adjustment for known error in
    # BC2 data
    if (text[char_start:char_end] == '/translation upstream factor' and
        ttext                     == 'translation upstream factor'):
        print >> sys.stderr, "NOTE: applying special-case fix ..."
        char_start += 1

    # sanity
    ref_text = text[char_start:char_end]
    assert ref_text == ttext, "Mismatch: '%s' vs '%s' [%d:%d] (%s %d-%d)" % (ttext, ref_text, char_start, char_end, text, start, end)

    return char_start, char_end

def main(argv):
    if len(argv) != 4:
        print >> sys.stderr, "Usage:", argv[0], "BC2TEXT BC2TAGS OUTPUT-DIR"
        return 1

    textfn, tagfn, outdir = argv[1:]

    # read in tags, store by sentence ID
    tags = {}
    with open(tagfn, 'rU') as tagf:
        for l in tagf:
            l = l.rstrip('\n')
            m = re.match(r'^([^\|]+)\|(\d+) (\d+)\|(.*)$', l)
            assert m, "Format error in %s: %s" % (tagfn, l)
            sid, start, end, text = m.groups()
            start, end = int(start), int(end)

            if sid not in tags:
                tags[sid] = []
            tags[sid].append((start, end, text))

    # read in sentences, store by sentence ID
    texts = {}
    with open(textfn, 'rU') as textf:
        for l in textf:
            l = l.rstrip('\n')
            m = re.match(r'(\S+) (.*)$', l)
            assert m, "Format error in %s: %s" % (textfn, l)
            sid, text = m.groups()

            assert sid not in texts, "Error: duplicate ID %s" % sid
            texts[sid] = text

    # combine tags with sentences, converting offsets into
    # character-based ones. (BC2 data offsets ignore space)
    offsets = {}
    for sid in texts:
        offsets[sid] = []
        for start, end, ttext in tags.get(sid,[]):
            soff, eoff = char_offsets(texts[sid], start, end, ttext)
            offsets[sid].append((soff, eoff))

    # output one .txt and one .a1 file per sentence
    for sid in texts:
        with open(os.path.join(outdir, sid+".txt"), 'w') as txtf:
            print >> txtf, texts[sid]
        with open(os.path.join(outdir, sid+".ann"), 'w') as annf:
            tidx = 1
            for soff, eoff in offsets[sid]:
                print >> annf, "T%d\tGENE %d %d\t%s" % (tidx, soff, eoff, texts[sid][soff:eoff])
                tidx += 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = biocontext2standoff
#!/usr/bin/env python

import sys
import re
import os

options = None

DEFAULT_INPUT = 'entities-anatomy.csv'

# Document ID format in BioContext data
BIOCONTEXT_ID_RE = re.compile(r'^([0-9]+|PMC[0-9]+\.[0-9]+\.[0-9])+$')

def argparser():
    import argparse
    
    ap=argparse.ArgumentParser(description='Convert BioContext data ' +
                               'into brat-flavored standoff.')
    ap.add_argument('-d', '--directory', default=None,
                    help='Output directory (default output to STDOUT)')
    ap.add_argument('-e', '--entitytype', default='Anatomical_entity',
                    help='Type to assign to annotations.')
    ap.add_argument('-f', '--file', default=DEFAULT_INPUT,
                    help='BioContext data (default "'+DEFAULT_INPUT+'")')
    ap.add_argument('-n', '--no-norm', default=False, action='store_true',
                    help='Do not output normalization annotations')
    ap.add_argument('-o', '--outsuffix', default='ann',
                    help='Suffix to add to output files (default "ann")')
    ap.add_argument('-v', '--verbose', default=False, action='store_true', 
                    help='Verbose output')    
    ap.add_argument('id', metavar='ID/FILE', nargs='+', 
                    help='IDs of documents for which to extract annotations.')
    return ap

def read_ids(fn):
    ids = set()
    with open(fn, 'rU') as f:
        for l in f:
            l = l.rstrip('\n')
            if not BIOCONTEXT_ID_RE.match(l):
                print >> sys.stderr, 'Warning: ID %s not in expected format' % l
            ids.add(l)
    return ids

def get_ids(items):
    """Given a list of either document IDs in BioContext format or
    names of files containing one ID per line, return the combined set
    of IDs."""

    combined = set()    
    for item in items:
        if BIOCONTEXT_ID_RE.match(item):
            combined.add(item)
        else:
            # assume name of file containing IDs
            combined |= read_ids(item)
    return combined

def convert_line(l, converted):
    try:
        doc_id, id_, eid, start, end, text, group = l.split('\t')
        if id_ == 'NULL':
            return 0
        start, end = int(start), int(end)
    except:
        print >> sys.stderr, 'Format error: %s' % l
        raise

    # textbound annotation
    converted.append('T%s\t%s %d %d\t%s' % (id_, options.entitytype,
                                            start, end, text))

    # normalization (grounding) annotation
    if not options.no_norm:
        converted.append('N%s\tReference T%s %s' % (id_, id_, eid))

def output_(out, ann):
    for a in ann:
        print >> out, a

def output(id_, ann, append):
    if not options.directory:
        output(sys.stdout, ann)
    else:
        fn = os.path.join(options.directory, id_+'.'+options.outsuffix)
        with open(fn, 'a' if append else 'w') as f:
            output_(f, ann)

def process_(f, ids):
    ann, current, processed = [], None, set()

    for l in f:
        l = l.strip()
        id_ = l.split('\t')[0]
        if id_ == current:
            if id_ in ids:
                convert_line(l, ann)
        else:
            # new document
            if current in ids:
                output(current, ann, current in processed)
                ann = []
                processed.add(current)
            if id_ in ids:
                if id_ in processed and options.verbose:
                    print >> sys.stderr, 'Warning: %s split' % id_
                convert_line(l, ann)
            current = id_
            # short-circuit after processing last
            if ids == processed:
                break

    if ann:
        output(current, ann, current in processed)

    for id_ in ids - processed:
        print >> sys.stderr, 'Warning: id %s not found' % id_

def process(fn, ids):
    try:
        with open(fn, 'rU') as f:
            # first line should be header; skip and confirm
            header = f.readline()
            if not header.startswith('doc_id\tid'):
                print >> sys.stderr, 'Warning: %s missing header' % fn
            process_(f, ids)
    except IOError, e:
        print >> sys.stderr, e, '(try -f argument?)'

def main(argv=None):
    global options

    if argv is None:
        argv = sys.argv

    options = argparser().parse_args(argv[1:])

    ids = get_ids(options.id)

    process(options.file, ids)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = BIOtoStandoff
#!/usr/bin/env python

# Script to convert a column-based BIO-formatted entity-tagged file
# into standoff with reference to the original text.

from __future__ import with_statement

import sys
import re
import os
import codecs

class taggedEntity:
    def __init__(self, startOff, endOff, eType, idNum, fullText):
        self.startOff = startOff
        self.endOff   = endOff  
        self.eType    = eType   
        self.idNum    = idNum   
        self.fullText = fullText

        self.eText = fullText[startOff:endOff]

    def __str__(self):
        return "T%d\t%s %d %d\t%s" % (self.idNum, self.eType, self.startOff, 
                                      self.endOff, self.eText)

    def check(self):
        # sanity checks: the string should not contain newlines and
        # should be minimal wrt surrounding whitespace
        assert "\n" not in self.eText, \
            "ERROR: newline in entity: '%s'" % self.eText
        assert self.eText == self.eText.strip(), \
            "ERROR: entity contains extra whitespace: '%s'" % self.eText

def BIO_to_standoff(BIOtext, reftext, tokenidx=2, tagidx=-1):
    BIOlines = BIOtext.split('\n')
    return BIO_lines_to_standoff(BIOlines, reftext, tokenidx, tagidx)

next_free_id_idx = 1

def BIO_lines_to_standoff(BIOlines, reftext, tokenidx=2, tagidx=-1):
    global next_free_id_idx

    taggedTokens = []

    ri, bi = 0, 0
    while(ri < len(reftext)):
        if bi >= len(BIOlines):
            print >> sys.stderr, "Warning: received BIO didn't cover given text"
            break

        BIOline = BIOlines[bi]

        if re.match(r'^\s*$', BIOline):
            # the BIO has an empty line (sentence split); skip
            bi += 1
        else:
            # assume tagged token in BIO. Parse and verify
            fields = BIOline.split('\t')

            try:
                tokentext = fields[tokenidx]
            except:
                print >> sys.stderr, "Error: failed to get token text " \
                    "(field %d) on line: %s" % (tokenidx, BIOline)
                raise

            try:
                tag = fields[tagidx]
            except:
                print >> sys.stderr, "Error: failed to get token text " \
                    "(field %d) on line: %s" % (tagidx, BIOline)
                raise

            m = re.match(r'^([BIO])((?:-[A-Za-z0-9_-]+)?)$', tag)
            assert m, "ERROR: failed to parse tag '%s'" % tag
            ttag, ttype = m.groups()

            # strip off starting "-" from tagged type
            if len(ttype) > 0 and ttype[0] == "-":
                ttype = ttype[1:]

            # sanity check
            assert ((ttype == "" and ttag == "O") or
                    (ttype != "" and ttag in ("B","I"))), \
                    "Error: tag/type mismatch %s" % tag

            # go to the next token on reference; skip whitespace
            while ri < len(reftext) and reftext[ri].isspace():
                ri += 1

            # verify that the text matches the original
            assert reftext[ri:ri+len(tokentext)] == tokentext, \
                "ERROR: text mismatch: reference '%s' tagged '%s'" % \
                (reftext[ri:ri+len(tokentext)].encode("UTF-8"), 
                 tokentext.encode("UTF-8"))

            # store tagged token as (begin, end, tag, tagtype) tuple.
            taggedTokens.append((ri, ri+len(tokentext), ttag, ttype))
            
            # skip the processed token
            ri += len(tokentext)
            bi += 1

            # ... and skip whitespace on reference
            while ri < len(reftext) and reftext[ri].isspace():
                ri += 1
            
    # if the remaining part either the reference or the tagged
    # contains nonspace characters, something's wrong
    if (len([c for c in reftext[ri:] if not c.isspace()]) != 0 or
        len([c for c in BIOlines[bi:] if not re.match(r'^\s*$', c)]) != 0):
        assert False, "ERROR: failed alignment: '%s' remains in reference, " \
            "'%s' in tagged" % (reftext[ri:], BIOlines[bi:])

    standoff_entities = []

    # cleanup for tagger errors where an entity begins with a
    # "I" tag instead of a "B" tag
    revisedTagged = []
    prevTag = None
    for startoff, endoff, ttag, ttype in taggedTokens:
        if prevTag == "O" and ttag == "I":
            print >> sys.stderr, "Note: rewriting \"I\" -> \"B\" after \"O\""
            ttag = "B"
        revisedTagged.append((startoff, endoff, ttag, ttype))
        prevTag = ttag
    taggedTokens = revisedTagged

    # cleanup for tagger errors where an entity switches type
    # without a "B" tag at the boundary
    revisedTagged = []
    prevTag, prevType = None, None
    for startoff, endoff, ttag, ttype in taggedTokens:
        if prevTag in ("B", "I") and ttag == "I" and prevType != ttype:
            print >> sys.stderr, "Note: rewriting \"I\" -> \"B\" at type switch"
            ttag = "B"
        revisedTagged.append((startoff, endoff, ttag, ttype))
        prevTag, prevType = ttag, ttype
    taggedTokens = revisedTagged    

    prevTag, prevEnd = "O", 0
    currType, currStart = None, None
    for startoff, endoff, ttag, ttype in taggedTokens:

        if prevTag != "O" and ttag != "I":
            # previous entity does not continue into this tag; output
            assert currType is not None and currStart is not None, \
                "ERROR in %s" % fn
            
            standoff_entities.append(taggedEntity(currStart, prevEnd, currType, 
                                                  next_free_id_idx, reftext))

            next_free_id_idx += 1

            # reset current entity
            currType, currStart = None, None

        elif prevTag != "O":
            # previous entity continues ; just check sanity
            assert ttag == "I", "ERROR in %s" % fn
            assert currType == ttype, "ERROR: entity of type '%s' continues " \
                "as type '%s'" % (currType, ttype)
            
        if ttag == "B":
            # new entity starts
            currType, currStart = ttype, startoff
            
        prevTag, prevEnd = ttag, endoff

    # if there's an open entity after all tokens have been processed,
    # we need to output it separately
    if prevTag != "O":
        standoff_entities.append(taggedEntity(currStart, prevEnd, currType,
                                              next_free_id_idx, reftext))
        next_free_id_idx += 1

    for e in standoff_entities:
        e.check()

    return standoff_entities


RANGE_RE = re.compile(r'^(-?\d+)-(-?\d+)$')

def parse_indices(idxstr):
    # parse strings of forms like "4,5" and "6,8-11", return list of
    # indices.
    indices = []
    for i in idxstr.split(','):
        if not RANGE_RE.match(i):
            indices.append(int(i))
        else:
            start, end = RANGE_RE.match(i).groups()
            for j in range(int(start), int(end)):
                indices.append(j)
    return indices

def main(argv):
    if len(argv) < 3 or len(argv) > 5:
        print >> sys.stderr, "Usage:", argv[0], "TEXTFILE BIOFILE [TOKENIDX [BIOIDX]]"
        return 1
    textfn, biofn = argv[1], argv[2]

    tokenIdx = None
    if len(argv) >= 4:
        tokenIdx = int(argv[3])
    bioIdx = None
    if len(argv) >= 5:
        bioIdx = argv[4]

    with open(textfn, 'rU') as textf:
        text = textf.read()
    with open(biofn, 'rU') as biof:
        bio = biof.read()

    if tokenIdx is None:
        so = BIO_to_standoff(bio, text)
    elif bioIdx is None:
        so = BIO_to_standoff(bio, text, tokenIdx)
    else:
        try:
            indices = parse_indices(bioIdx)
        except:
            print >> sys.stderr, 'Error: failed to parse indices "%s"' % bioIdx
            return 1
        so = []
        for i in indices:
            so.extend(BIO_to_standoff(bio, text, tokenIdx, i))

    for s in so:
        print s

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = catann
#!/usr/bin/env python

# Given a set of brat-flavored standoff .ann files, catenates them
# into a single .ann file (with reference to the corresponding .txt
# files) so that the resulting .ann applies for the simple catenation
# of the .txt files.

from __future__ import with_statement

import sys
import re
import os
import codecs

def parse_id(l):
    m = re.match(r'^((\S)(\S*))', l)
    assert m, "Failed to parse ID: %s" % l
    return m.groups()

def parse_key_value(kv):
    m = re.match(r'^(\S+):(\S+)$', kv)
    assert m, "Failed to parse key-value pair: %s" % kv
    return m.groups()

def join_key_value(k, v):
    return "%s:%s" % (k, v)

def remap_key_values(kvs, idmap):
    remapped = []
    for kv in kvs:
        k, v = parse_key_value(kv)
        v = idmap.get(v, v)
        remapped.append(join_key_value(k, v))
    return remapped

def remap_relation_idrefs(l, idmap):
    fields = l.split('\t')
    assert len(fields) >= 2, "format error"

    type_args = fields[1].split(" ")
    assert len(type_args) >= 3, "format error"

    args = type_args[1:]
    args = remap_key_values(args, idmap)

    fields[1] = " ".join(type_args[:1]+args)
    return '\t'.join(fields)

def remap_event_idrefs(l, idmap):
    fields = l.split('\t')
    assert len(fields) >= 2, "format error"

    type_args = fields[1].split(" ")
    type_args = remap_key_values(type_args, idmap)

    fields[1] = " ".join(type_args)
    return '\t'.join(fields)

def remap_attrib_idrefs(l, idmap):
    fields = l.split('\t')
    assert len(fields) >= 2, "format error"

    type_args = fields[1].split(" ")
    assert len(type_args) >= 2, "format error"

    args = type_args[1:]
    args = [idmap.get(a,a) for a in args]

    fields[1] = " ".join(type_args[:1]+args)
    return '\t'.join(fields)

def remap_note_idrefs(l, idmap):
    # format matches attrib in relevant parts
    return remap_attrib_idrefs(l, idmap)

def remap_equiv_idrefs(l, idmap):
    fields = l.split('\t')
    assert len(fields) >= 2, "format error"

    type_args = fields[1].split(" ")
    assert len(type_args) >= 3, "format error"

    args = type_args[1:]
    args = [idmap.get(a,a) for a in args]

    fields[1] = " ".join(type_args[:1]+args)
    return '\t'.join(fields)

def main(argv):
    filenames = argv[1:]

    # read in the .ann files and the corresponding .txt files for each
    anns = []
    texts = []
    for fn in filenames:
        assert re.search(r'\.ann$', fn), 'Error: argument %s not a .ann file.' % fn
        txtfn = re.sub(r'\.ann$', '.txt', fn)

        with codecs.open(fn, 'r', encoding='utf-8') as annf:
            anns.append(annf.readlines())

        with codecs.open(txtfn, 'r', encoding='utf-8') as txtf:
            texts.append(txtf.read())

    # process each .ann in turn, keeping track of the "base" offset
    # from (conceptual) catenation of the texts.
    baseoff = 0
    for i in range(len(anns)):
        # first, revise textbound annotation offsets by the base
        for j in range(len(anns[i])):
            l = anns[i][j]
            # see http://brat.nlplab.org/standoff.html for format
            if not l or l[0] != 'T':
                continue
            m = re.match(r'^(T\d+\t\S+) (\d+ \d+(?:;\d+ \d+)*)(\t.*\n?)', l)
            assert m, 'failed to parse "%s"' % l
            begin, offsets, end = m.groups()

            new_offsets = []
            for offset in offsets.split(';'):
                startoff, endoff = offset.split(' ')
                startoff = int(startoff) + baseoff
                endoff   = int(endoff) + baseoff
                new_offsets.append('%d %d' % (startoff, endoff))
            offsets = ';'.join(new_offsets)

            anns[i][j] = "%s %s%s" % (begin, offsets, end)

        baseoff += len(texts[i])

    # determine the full set of IDs currently in use in any of the
    # .anns
    reserved_id = {}
    for i in range(len(anns)):
        for l in anns[i]:
            aid, idchar, idseq = parse_id(l)
            reserved_id[aid] = (idchar, idseq)

    # use that to determine the next free "sequential" ID for each
    # initial character in use in IDs.
    idchars = set([aid[0] for aid in reserved_id])
    next_free_seq = {}
    for c in idchars:
        maxseq = 1
        for aid in [a for a in reserved_id if a[0] == c]:
            idchar, idseq = reserved_id[aid]
            try:
                idseq = int(idseq)
                maxseq = max(idseq, maxseq)
            except ValueError:
                # non-int ID tail; harmless here
                pass
        next_free_seq[c] = maxseq + 1

    # next, remap IDs: process each .ann in turn, keeping track of
    # which IDs are in use, and assign the next free ID in case of
    # collisions from catenation. Also, remap ID references
    # accordingly.
    reserved = {}
    for i in range(len(anns)):
        idmap = {}
        for j in range(len(anns[i])):
            l = anns[i][j]
            aid, idchar, idseq = parse_id(l)

            # special case: '*' IDs don't need to be unique, leave as is
            if aid == '*':
                continue

            if aid not in reserved:
                reserved[aid] = True
            else:
                newid = "%s%d" % (idchar, next_free_seq[idchar])
                next_free_seq[idchar] += 1

                assert aid not in idmap
                idmap[aid] = newid

                l = "\t".join([newid]+l.split('\t')[1:])
                reserved[newid] = True

            anns[i][j] = l

        # id mapping complete, next remap ID references
        for j in range(len(anns[i])):
            l = anns[i][j].rstrip()
            tail = anns[i][j][len(l):]
            aid, idchar, idseq = parse_id(l)

            if idchar == "T":
                # textbound; can't refer to anything
                pass
            elif idchar == "R":
                # relation
                l = remap_relation_idrefs(l, idmap)
            elif idchar == "E":
                # event
                l = remap_event_idrefs(l, idmap)
            elif idchar == "M" or idchar == "A":
                # attribute
                l = remap_attrib_idrefs(l, idmap)
            elif idchar == "*":
                # equiv
                l = remap_equiv_idrefs(l, idmap)
            elif idchar == "#":
                # note
                l = remap_note_idrefs(l, idmap)
            else:
                # ???
                print >> sys.stderr, "Warning: unrecognized annotation, cannot remap ID references: %s" % l

            anns[i][j] = l+tail
                
    # output
    for i in range(len(anns)):
        for l in anns[i]:
            sys.stdout.write(l.encode('utf-8'))

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = checkann
#!/usr/bin/env python

# Check that text-bound annotations in .ann file align with the
# corresponding .txt file.

import sys
import re
import codecs

from collections import namedtuple
from os.path import basename

Textbound = namedtuple('Textbound', 'id type start end text')

TEXTBOUND_RE = re.compile(r'^([A-Z]\d+)\t(\S+) (\d+) (\d+)\t(.*)$')

class FormatError(Exception):
    pass

def txt_for_ann(fn):
    tfn = re.sub(r'\.ann$', '.txt', fn)
    if tfn == fn:
        raise FormatError
    return tfn

def parse_textbound(s):
    m = TEXTBOUND_RE.match(s)
    if not m:
        raise FormatError
    id_, type_, start, end, text = m.groups()
    start, end = int(start), int(end)
    return Textbound(id_, type_, start, end, text)

def process(fn):
    textbounds = []

    with codecs.open(fn, 'rU', encoding='utf8', errors='strict') as f:
        for l in f:
            l = l.rstrip('\n')

            if not l or l.isspace():
                continue

            if l[0] != 'T':
                continue # assume not a textbound annotation
            else:
                textbounds.append(parse_textbound(l))

    # debugging
#    print >> sys.stderr, '%s: %d textbounds' % (basename(fn), len(textbounds))

    with codecs.open(txt_for_ann(fn), 'rU', encoding='utf8',
                     errors='strict') as f:
        text = f.read()

    for id_, type_, start, end, ttext in textbounds:
        try:
            assert text[start:end] == ttext
        except:
            print 'Mismatch in %s: %s %d %d' % (basename(fn), id_, start, end)
            print '     reference: %s' % \
                ttext.encode('utf-8').replace('\n', '\\n')
            print '     document : %s' % \
                text[start:end].encode('utf-8').replace('\n', '\\n')


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print >> sys.stderr, 'Usage:', argv[0], 'FILE [FILE [...]]'
        return 1

    for fn in argv[1:]:
        process(fn)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = colourise
#!/usr/bin/env python

'''
Generate a set of colours for a given set of input labels.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-06-28
'''

# TODO: With some frequency information this could be done even more
#   intelligently, attempting to use the space optimally by keeping frequent
#   labels apart? Ultimately, we need some sort of desired distance measure.

from argparse import ArgumentParser, FileType
from colorsys import hls_to_rgb, rgb_to_hls
from sys import stdin, stdout

def _argparser():
    argparser = ArgumentParser()
    argparser.add_argument('-i', '--input', type=FileType('r'), default=stdin)
    argparser.add_argument('-o', '--output', type=FileType('w'), default=stdout)
    argparser.add_argument('-c', '--visual-conf', action='store_true')
    return argparser

def main(args):
    argp = _argparser().parse_args(args[1:])
    lbls = [l.rstrip('\n') for l in argp.input]
    # Note: Do some testing before allowing too big an input
    assert len(lbls) <= 100, 'currently not supporting more than a hundred'

    hue, lightness, saturation = rgb_to_hls(1.0, 0.0, 0.0)
    # Gently bump the lightness to produce softer colours
    lightness += 0.05
    hue_step = 1.0 / len(lbls)

    for lbl in lbls:
        hex_output = '#{:02x}{:02x}{:02x}'.format(*[int(255 * e)
            for e in hls_to_rgb(hue, lightness, saturation)])

        if argp.visual_conf:
            argp.output.write('{}\tbgColor:{}'.format(lbl, hex_output))
        else:
            argp.output.write(hex_output)
        argp.output.write('\n')

        hue += hue_step
    return 0

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = conll00tostandoff
#!/usr/bin/env python

# Script to convert a CoNLL 2000-flavored BIO-formatted entity-tagged
# file into BioNLP ST-flavored standoff and a reconstruction of the
# original text.

from __future__ import with_statement

import sys
import re
import os
import codecs

INPUT_ENCODING = "ASCII"
OUTPUT_ENCODING = "UTF-8"

output_directory = None

def unescape_PTB(s):
    # Returns the given string with Penn treebank escape sequences
    # replaced with the escaped text.
    return s.replace("-LRB-", "(").replace("-RRB-", ")").replace("-LSB-", "[").replace("-RSB-", "]").replace("-LCB-", "{").replace("-RCB-", "}").replace('``', '"'). replace("''", '"').replace('\\/', '/')

def quote(s):
    return s in ('"', )

def space(t1, t2, quote_count = None):
    # Helper for reconstructing sentence text. Given the text of two
    # consecutive tokens, returns a heuristic estimate of whether a
    # space character should be placed between them.

    if re.match(r'^[\($]$', t1):
        return False
    if re.match(r'^[.,;%\)\?\!]$', t2):
        return False
    if quote(t1) and quote_count is not None and quote_count % 2 == 1:
        return False
    if quote(t2) and quote_count is not None and quote_count % 2 == 1:
        return False
    return True

def tagstr(start, end, ttype, idnum, text):
    # sanity checks
    assert '\n' not in text, "ERROR: newline in entity '%s'" % (text)
    assert text == text.strip(), "ERROR: tagged span contains extra whitespace: '%s'" % (text)
    return "T%d\t%s %d %d\t%s" % (idnum, ttype, start, end, text)

def output(infn, docnum, sentences):
    global output_directory

    if output_directory is None:
        txtout = sys.stdout
        soout = sys.stdout
    else:
        outfn = os.path.join(output_directory, os.path.basename(infn)+'-doc-'+str(docnum))
        txtout = codecs.open(outfn+'.txt', 'wt', encoding=OUTPUT_ENCODING)
        soout = codecs.open(outfn+'.ann', 'wt', encoding=OUTPUT_ENCODING)

    offset, idnum = 0, 1

    doctext = ""

    for si, sentence in enumerate(sentences):

        prev_token = None
        prev_tag = "O"
        curr_start, curr_type = None, None
        quote_count = 0

        for token, ttag, ttype in sentence:

            if curr_type is not None and (ttag != "I" or ttype != curr_type):
                # a previously started tagged sequence does not
                # continue into this position.
                print >> soout, tagstr(curr_start, offset, curr_type, idnum, doctext[curr_start:offset])
                idnum += 1
                curr_start, curr_type = None, None

            if prev_token is not None and space(prev_token, token, quote_count):
                doctext = doctext + ' '
                offset += 1

            if curr_type is None and ttag != "O":
                # a new tagged sequence begins here
                curr_start, curr_type = offset, ttype

            doctext = doctext + token
            offset += len(token)

            if quote(token):
                quote_count += 1

            prev_token = token
            prev_tag = ttag
        
        # leftovers?
        if curr_type is not None:
            print >> soout, tagstr(curr_start, offset, curr_type, idnum, doctext[curr_start:offset])
            idnum += 1

        if si+1 != len(sentences):
            doctext = doctext + '\n'        
            offset += 1
            
    print >> txtout, doctext

def process(fn):
    docnum = 1
    sentences = []

    with codecs.open(fn, encoding=INPUT_ENCODING) as f:

        # store (token, BIO-tag, type) triples for sentence
        current = []

        lines = f.readlines()

        for ln, l in enumerate(lines):
            l = l.strip()

            if re.match(r'^\s*$', l):
                # blank lines separate sentences
                if len(current) > 0:
                    sentences.append(current)
                current = []

                # completely arbitrary division into documents
                if len(sentences) >= 10:
                    output(fn, docnum, sentences)
                    sentences = []
                    docnum += 1

                continue

            # Assume it's a normal line. The format for spanish is
            # is word and BIO tag separated by space, and for dutch
            # word, POS and BIO tag separated by space. Try both.
            m = re.match(r'^(\S+)\s(\S+)$', l)
            if not m:
                m = re.match(r'^(\S+)\s\S+\s(\S+)$', l)
            assert m, "Error parsing line %d: %s" % (ln+1, l)
            token, tag = m.groups()

            # parse tag
            m = re.match(r'^([BIO])((?:-[A-Za-z_]+)?)$', tag)
            assert m, "ERROR: failed to parse tag '%s' in %s" % (tag, fn)
            ttag, ttype = m.groups()
            if len(ttype) > 0 and ttype[0] == "-":
                ttype = ttype[1:]

            token = unescape_PTB(token)

            current.append((token, ttag, ttype))

        # process leftovers, if any
        if len(current) > 0:
            sentences.append(current)
        if len(sentences) > 0:
            output(fn, docnum, sentences)

def main(argv):
    global output_directory


    # Take an optional "-o" arg specifying an output directory for the results
    output_directory = None
    filenames = argv[1:]
    if len(argv) > 2 and argv[1] == "-o":
        output_directory = argv[2]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[3:]

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            print >> sys.stderr, "Error processing %s: %s" % (fn, e)
            fail_count += 1

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conll02tostandoff
#!/usr/bin/env python

# Script to convert a CoNLL 2002-flavored BIO-formatted entity-tagged
# file into BioNLP ST-flavored standoff and a reconstruction of the
# original text.

from __future__ import with_statement

import sys
import re
import os
import codecs

INPUT_ENCODING = "Latin-1"
OUTPUT_ENCODING = "UTF-8"

output_directory = None

def quote(s):
    return s in ('"', )

def space(t1, t2, quote_count = None):
    # Helper for reconstructing sentence text. Given the text of two
    # consecutive tokens, returns a heuristic estimate of whether a
    # space character should be placed between them.

    if re.match(r'^[\(]$', t1):
        return False
    if re.match(r'^[.,\)\?\!]$', t2):
        return False
    if quote(t1) and quote_count is not None and quote_count % 2 == 1:
        return False
    if quote(t2) and quote_count is not None and quote_count % 2 == 1:
        return False
    return True

def tagstr(start, end, ttype, idnum, text):
    # sanity checks
    assert '\n' not in text, "ERROR: newline in entity '%s'" % (text)
    assert text == text.strip(), "ERROR: tagged span contains extra whitespace: '%s'" % (text)
    return "T%d\t%s %d %d\t%s" % (idnum, ttype, start, end, text)

def output(infn, docnum, sentences):
    global output_directory

    if output_directory is None:
        txtout = sys.stdout
        soout = sys.stdout
    else:
        outfn = os.path.join(output_directory, os.path.basename(infn)+'-doc-'+str(docnum))
        txtout = codecs.open(outfn+'.txt', 'wt', encoding=OUTPUT_ENCODING)
        soout = codecs.open(outfn+'.ann', 'wt', encoding=OUTPUT_ENCODING)

    offset, idnum = 0, 1

    doctext = ""

    for si, sentence in enumerate(sentences):

        prev_token = None
        prev_tag = "O"
        curr_start, curr_type = None, None
        quote_count = 0

        for token, ttag, ttype in sentence:

            if curr_type is not None and (ttag != "I" or ttype != curr_type):
                # a previously started tagged sequence does not
                # continue into this position.
                print >> soout, tagstr(curr_start, offset, curr_type, idnum, doctext[curr_start:offset])
                idnum += 1
                curr_start, curr_type = None, None

            if prev_token is not None and space(prev_token, token, quote_count):
                doctext = doctext + ' '
                offset += 1

            if curr_type is None and ttag != "O":
                # a new tagged sequence begins here
                curr_start, curr_type = offset, ttype

            doctext = doctext + token
            offset += len(token)

            if quote(token):
                quote_count += 1

            prev_token = token
            prev_tag = ttag
        
        # leftovers?
        if curr_type is not None:
            print >> soout, tagstr(curr_start, offset, curr_type, idnum, doctext[curr_start:offset])
            idnum += 1

        if si+1 != len(sentences):
            doctext = doctext + '\n'        
            offset += 1
            
    print >> txtout, doctext

def process(fn):
    docnum = 1
    sentences = []

    with codecs.open(fn, encoding=INPUT_ENCODING) as f:

        # store (token, BIO-tag, type) triples for sentence
        current = []

        lines = f.readlines()

        for ln, l in enumerate(lines):
            l = l.strip()

            if re.match(r'^\s*$', l):
                # blank lines separate sentences
                if len(current) > 0:
                    sentences.append(current)
                current = []
                continue
            elif (re.match(r'^===*\s+O\s*$', l) or
                  re.match(r'^-DOCSTART-', l)):
                # special character sequence separating documents
                if len(sentences) > 0:
                    output(fn, docnum, sentences)
                sentences = []
                docnum += 1
                continue

            if (ln + 2 < len(lines) and 
                re.match(r'^\s*$', lines[ln+1]) and
                re.match(r'^-+\s+O\s*$', lines[ln+2])):
                # heuristic match for likely doc before current line
                if len(sentences) > 0:
                    output(fn, docnum, sentences)
                sentences = []
                docnum += 1
                # go on to process current normally

            # Assume it's a normal line. The format for spanish is
            # is word and BIO tag separated by space, and for dutch
            # word, POS and BIO tag separated by space. Try both.
            m = re.match(r'^(\S+)\s(\S+)$', l)
            if not m:
                m = re.match(r'^(\S+)\s\S+\s(\S+)$', l)
            assert m, "Error parsing line %d: %s" % (ln+1, l)
            token, tag = m.groups()

            # parse tag
            m = re.match(r'^([BIO])((?:-[A-Za-z_]+)?)$', tag)
            assert m, "ERROR: failed to parse tag '%s' in %s" % (tag, fn)
            ttag, ttype = m.groups()
            if len(ttype) > 0 and ttype[0] == "-":
                ttype = ttype[1:]

            current.append((token, ttag, ttype))

        # process leftovers, if any
        if len(current) > 0:
            sentences.append(current)
        if len(sentences) > 0:
            output(fn, docnum, sentences)

def main(argv):
    global output_directory


    # Take an optional "-o" arg specifying an output directory for the results
    output_directory = None
    filenames = argv[1:]
    if len(argv) > 2 and argv[1] == "-o":
        output_directory = argv[2]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[3:]

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            print >> sys.stderr, "Error processing %s: %s" % (fn, e)
            fail_count += 1

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conll09tostandoff
#!/usr/bin/env python

# Convert CoNLL 2009 format file into brat-flavored standoff and a
# reconstruction of the original text.

from __future__ import with_statement

import sys
import re
import os
import codecs

# maximum number of sentences to include in single output document
# (if None, doesn't split into documents)
MAX_DOC_SENTENCES = 10

# whether to output an explicit root note
OUTPUT_ROOT = True
# the string to use to represent the root node
ROOT_STR = 'ROOT'
ROOT_POS = 'ROOT'
ROOT_FEAT = ''

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"

# fields of interest in input data; full list: ID FORM LEMMA PLEMMA
# POS PPOS FEAT PFEAT HEAD PHEAD DEPREL PDEPREL FILLPRED PRED APREDs
# (http://ufal.mff.cuni.cz/conll2009-st/task-description.html)

F_ID, F_FORM, F_LEMMA, F_POS, F_FEAT, F_HEAD, F_DEPREL, F_FILLPRED, F_PRED, F_APRED1 = range(10)

output_directory = None

# rewrites for characters appearing in CoNLL-X types that cannot be
# directly used in identifiers in brat-flavored standoff
charmap = {
    '<' : '_lt_',
    '>' : '_gt_',
    '+' : '_plus_',
    '?' : '_question_',
    '&' : '_amp_',
    ':' : '_colon_',
    '.' : '_period_',
    '!' : '_exclamation_',
}

def maptype(s):
    return "".join([charmap.get(c,c) for c in s])

def tokstr(start, end, ttype, idnum, text):
    # sanity checks
    assert '\n' not in text, "ERROR: newline in entity '%s'" % (text)
    assert text == text.strip(), "ERROR: tagged span contains extra whitespace: '%s'" % (text)
    return "T%d\t%s %d %d\t%s" % (idnum, maptype(ttype), start, end, text)

def featstr(lemma, feats, idnum):
    return "#%d\tData T%d\tLemma: %s, Feats: %s" % (idnum, idnum, lemma, feats)

def depstr(depid, headid, rel, idnum):
    return "R%d\t%s Arg1:T%d Arg2:T%d" % (idnum, maptype(rel), headid, depid)

def output(infn, docnum, sentences):
    global output_directory

    if output_directory is None:
        txtout = codecs.getwriter(OUTPUT_ENCODING)(sys.stdout)
        soout = codecs.getwriter(OUTPUT_ENCODING)(sys.stdout)
    else:
        # add doc numbering if there is a sentence count limit,
        # implying multiple outputs per input
        if MAX_DOC_SENTENCES:
            outfnbase = os.path.basename(infn)+'-doc-'+str(docnum)
        else:
            outfnbase = os.path.basename(infn)
        outfn = os.path.join(output_directory, outfnbase)
        txtout = codecs.open(outfn+'.txt', 'wt', encoding=OUTPUT_ENCODING)
        soout = codecs.open(outfn+'.ann', 'wt', encoding=OUTPUT_ENCODING)

    offset, idnum, ridnum = 0, 1, 1

    doctext = ""

    for si, sentence in enumerate(sentences):
        tokens, deps = sentence

        # store mapping from per-sentence token sequence IDs to
        # document-unique token IDs
        idmap = {}

        # output tokens
        prev_form = None

        if OUTPUT_ROOT:
            # add an explicit root node with seq ID 0 (zero)
            tokens[0] = (ROOT_STR, ROOT_STR, ROOT_POS, ROOT_FEAT)

        for id_ in tokens:

            form, lemma, pos, feat = tokens[id_]

            if prev_form is not None:
                doctext = doctext + ' '
                offset += 1

            # output a token annotation
            print >> soout, tokstr(offset, offset+len(form), pos, idnum, form)
            print >> soout, featstr(lemma, feat, idnum)
            assert id_ not in idmap, "Error in data: dup ID"
            idmap[id_] = idnum
            idnum += 1

            doctext = doctext + form
            offset += len(form)
            
            prev_form = form

        # output dependencies
        for head in deps:
            for dep in deps[head]:
                for rel in deps[head][dep]:
                    # if root is not added, skip deps to the root (idx 0)
                    if not OUTPUT_ROOT and head == 0:
                        continue
                    
                    print >> soout, depstr(idmap[dep], idmap[head], rel, ridnum)
                    ridnum += 1
        
        if si+1 != len(sentences):
            doctext = doctext + '\n'        
            offset += 1
            
    print >> txtout, doctext

def read_sentences(fn):
    """Read sentences in CoNLL format.

    Return list of sentences, each represented as list of fields.
    """
    # original author: @fginter
    sentences=[[]]
    with codecs.open(fn, 'rU', INPUT_ENCODING) as f:
        for line in f:
            line=line.rstrip()
            if not line:
                continue
            # igore lines starting with "#" as comments
            if line and line[0] == "#":
                continue
            cols=line.split(u'\t')
            # break sentences on token index instead of blank line;
            # the latter isn't reliably written by all generators
            if cols[0] == u'1' and sentences[-1]:
                sentences.append([])
            sentences[-1].append(cols)
    return sentences

def resolve_format(sentences, options):
    fields = {}

    # TODO: identify CoNLL format variant by heuristics on the sentences

    # CoNLL'09 field structure, using gold instead of predicted (e.g.
    # POS instead of PPOS).
    fields[F_ID] = 0
    fields[F_FORM] = 1
    fields[F_LEMMA] = 2
    # PLEMMA = 3
    fields[F_POS] = 4
    # PPOS = 5
    fields[F_FEAT] = 6
    # PFEAT = 7
    fields[F_HEAD] = 8
    # PHEAD = 9
    fields[F_DEPREL] = 10
    # PDEPREL = 11
    fields[F_FILLPRED] = 12
    fields[F_PRED] = 13
    fields[F_APRED1] = 14

    return fields

def mark_dependencies(dependency, head, dependent, deprel):
    if head not in dependency:
        dependency[head] = {}
    if dependent not in dependency[head]:
        dependency[head][dependent] = []
    dependency[head][dependent].append(deprel)
    return dependency

def process_sentence(sentence, fieldmap):
    # dependencies represented as dict of dicts of lists of dep types
    # dependency[head][dependent] = [type1, type2, ...]
    dependency = {}
    # tokens represented as dict indexed by ID, values (form, lemma,
    # POS, feat)
    token = {}

    for fields in sentence:
        id_ = int(fields[fieldmap[F_ID]])
        form = fields[fieldmap[F_FORM]]
        lemma = fields[fieldmap[F_LEMMA]]
        pos = fields[fieldmap[F_POS]]
        feat = fields[fieldmap[F_FEAT]]
        try:
            head = int(fields[fieldmap[F_HEAD]])
        except ValueError:
            assert fields[fieldmap[F_HEAD]] == 'ROOT', \
                'error: unexpected head: %s' % fields[fieldmap[F_HEAD]]
            head = 0
        deprel = fields[fieldmap[F_DEPREL]]
        #fillpred = fields[fieldmap[F_FILLPRED]]
        #pred = fields[fieldmap[F_PRED]]
        #apreds = fields[fieldmap[F_APRED1]:]

        mark_dependencies(dependency, head, id_, deprel)
        assert id_ not in token
        token[id_] = (form, lemma, pos, feat)

    return token, dependency
        
def process(fn, options=None):
    docnum = 1
    sentences = read_sentences(fn)

    fieldmap = resolve_format(sentences, options)
    processed = []

    for i, sentence in enumerate(sentences):
        token, dependency = process_sentence(sentence, fieldmap)
        processed.append((token, dependency))

        # limit sentences per output "document"
        if MAX_DOC_SENTENCES and len(processed) >= MAX_DOC_SENTENCES:
            output(fn, docnum, processed)
            processed = []
            docnum += 1

def main(argv):
    global output_directory

    # Take an optional "-o" arg specifying an output directory for the results
    output_directory = None
    filenames = argv[1:]
    if len(argv) > 2 and argv[1] == "-o":
        output_directory = argv[2]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[3:]

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            m = unicode(e).encode(OUTPUT_ENCODING)
            raise
            #print >> sys.stderr, "Error processing %s: %s" % (fn, m)
            #fail_count += 1

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conll2standoff
#!/usr/bin/env python

# Script to convert a CoNLL-flavored BIO-formatted entity-tagged file
# into BioNLP ST-flavored standoff with reference to the original
# text.

import sys
import re
import os
import codecs

try:
    import psyco
    psyco.full()
except:
    pass

# what to do if an error in the tag sequence (e.g. "O I-T1" or "B-T1
# I-T2") is encountered: recover/discard the erroneously tagged 
# sequence, or abord the entire process
# TODO: add a command-line option for this
SEQUENCE_ERROR_RECOVER, SEQUENCE_ERROR_DISCARD, SEQUENCE_ERROR_FAIL = range(3)

SEQUENCE_ERROR_PROCESSING = SEQUENCE_ERROR_RECOVER

# TODO: get rid of globals

# output goes to stdout by default
out = sys.stdout
reference_directory = None
output_directory = None

def reference_text_filename(fn):
    # Tries to determine the name of the reference text file
    # for the given CoNLL output file.

    fnbase = os.path.basename(fn)
    reffn = os.path.join(reference_directory, fnbase)

    # if the file doesn't exist, try replacing the last dot-separated
    # suffix in the filename with .txt
    if not os.path.exists(reffn):
        reffn = re.sub(r'(.*)\..*', r'\1.txt', reffn)

    return reffn

def output_filename(fn):
    if output_directory is None:
        return None

    reffn = reference_text_filename(fn)
    return os.path.join(output_directory, os.path.basename(reffn).replace(".txt",".a1"))

def process(fn):
    global out

    reffn = reference_text_filename(fn)

    try:
        #reffile = open(reffn)
        reffile = codecs.open(reffn, "rt", "UTF-8")
    except:
        print >> sys.stderr, "ERROR: failed to open reference file %s" % reffn
        raise
    reftext = reffile.read()
    reffile.close()

    # ... and the tagged file
    try:
        #tagfile = open(fn)
        tagfile = codecs.open(fn, "rt", "UTF-8")
    except:
        print >> sys.stderr, "ERROR: failed to open file %s" % fn
        raise
    tagtext = tagfile.read()
    tagfile.close()

    # if an output directory is specified, write a file with an
    # appropriate name there
    if output_directory is not None:
        outfn = output_filename(fn)
        #out = codecs.open(outfn, "wt", "UTF-8")
        out = open(outfn, "wt")

    # parse CoNLL-X-flavored tab-separated BIO, storing boundaries and
    # tagged tokens. The format is one token per line, with the
    # following tab-separated fields:
    #
    #     START END TOKEN LEMMA POS CHUNK TAG
    #
    # where we're only interested in the start and end offsets
    # (START,END), the token text (TOKEN) for verification, and the
    # NER tags (TAG).  Additionally, sentence boundaries are marked by
    # blank lines in the input.

    taggedTokens = []
    for ln, l in enumerate(tagtext.split('\n')):
        if l.strip() == '':
            # skip blank lines (sentence boundary markers)
            continue

        fields = l.split('\t')
        assert len(fields) == 7, "Error: expected 7 tab-separated fields on line %d in %s, found %d: %s" % (ln+1, fn, len(fields), l.encode("UTF-8"))

        start, end, ttext = fields[0:3]
        tag = fields[6]
        start, end = int(start), int(end)

        # parse tag
        m = re.match(r'^([BIO])((?:-[A-Za-z_]+)?)$', tag)
        assert m, "ERROR: failed to parse tag '%s' in %s" % (tag, fn)
        ttag, ttype = m.groups()

        # strip off starting "-" from tagged type
        if len(ttype) > 0 and ttype[0] == "-":
            ttype = ttype[1:]

        # sanity check
        assert ((ttype == "" and ttag == "O") or
                (ttype != "" and ttag in ("B","I"))), "Error: tag format '%s' in %s" % (tag, fn)

        # verify that the text matches the original
        assert reftext[start:end] == ttext, "ERROR: text mismatch for %s on line %d: reference '%s' tagged '%s': %s" % (fn, ln+1, reftext[start:end].encode("UTF-8"), ttext.encode("UTF-8"), l.encode("UTF-8"))

        # store tagged token as (begin, end, tag, tagtype) tuple.
        taggedTokens.append((start, end, ttag, ttype))

    # transform input text from CoNLL-X flavored tabbed BIO format to
    # inline-tagged BIO format for processing (this is a bit
    # convoluted, sorry; this script written as a modification of an
    # inline-format BIO conversion script).

    ### Output for entities ###

    # returns a string containing annotation in the output format
    # for an Entity with the given properties.
    def entityStr(startOff, endOff, eType, idNum, fullText):
        # sanity checks: the string should not contain newlines and
        # should be minimal wrt surrounding whitespace
        eText = fullText[startOff:endOff]
        assert "\n" not in eText, "ERROR: newline in entity in %s: '%s'" % (fn, eText)
        assert eText == eText.strip(), "ERROR: entity contains extra whitespace in %s: '%s'" % (fn, eText)
        return "T%d\t%s %d %d\t%s" % (idNum, eType, startOff, endOff, eText)

    idIdx = 1
    prevTag, prevEnd = "O", 0
    currType, currStart = None, None
    for startoff, endoff, ttag, ttype in taggedTokens:

        # special case for surviving format errors in input: if the
        # type sequence changes without a "B" tag, change the tag
        # to allow some output (assumed to be preferable to complete
        # failure.)
        if prevTag != "O" and ttag == "I" and currType != ttype:
            if SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_RECOVER:
                # reinterpret as the missing "B" tag.
                ttag = "B"
            elif SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_DISCARD:
                ttag = "O"
            else:
                assert SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_FAIL
                pass # will fail on later check

        # similarly if an "I" tag occurs after an "O" tag
        if prevTag == "O" and ttag == "I":
            if SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_RECOVER:
                ttag = "B"            
            elif SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_DISCARD:
                ttag = "O"
            else:
                assert SEQUENCE_ERROR_PROCESSING == SEQUENCE_ERROR_FAIL
                pass # will fail on later check

        if prevTag != "O" and ttag != "I":
            # previous entity does not continue into this tag; output
            assert currType is not None and currStart is not None, "ERROR at %s (%d-%d) in %s" % (reftext[startoff:endoff], startoff, endoff, fn)
            
            print >> out, entityStr(currStart, prevEnd, currType, idIdx, reftext).encode("UTF-8")

            idIdx += 1

            # reset current entity
            currType, currStart = None, None

        elif prevTag != "O":
            # previous entity continues ; just check sanity
            assert ttag == "I", "ERROR in %s" % fn
            assert currType == ttype, "ERROR: entity of type '%s' continues as type '%s' in %s" % (currType, ttype, fn)
            
        if ttag == "B":
            # new entity starts
            currType, currStart = ttype, startoff
            
        prevTag, prevEnd = ttag, endoff

    # if there's an open entity after all tokens have been processed,
    # we need to output it separately
    if prevTag != "O":
        print >> out, entityStr(currStart, prevEnd, currType, idIdx, reftext).encode("UTF-8")

    if output_directory is not None:
        # we've opened a specific output for this
        out.close()

def main(argv):
    global reference_directory, output_directory


    # (clumsy arg parsing, sorry)

    # Take a mandatory "-d" arg that tells us where to find the original,
    # unsegmented and untagged reference files.

    if len(argv) < 3 or argv[1] != "-d":
        print >> sys.stderr, "USAGE:", argv[0], "-d REF-DIR [-o OUT-DIR] (FILES|DIR)"
        return 1

    reference_directory = argv[2]

    # Take an optional "-o" arg specifying an output directory for the results

    output_directory = None
    filenames = argv[3:]
    if len(argv) > 4 and argv[3] == "-o":
        output_directory = argv[4]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[5:]


    # special case: if we only have a single file in input and it specifies
    # a directory, process all files in that directory
    input_directory = None
    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        input_directory = filenames[0]
        filenames = [os.path.join(input_directory, fn) for fn in os.listdir(input_directory)]
        print >> sys.stderr, "Processing %d files in %s ..." % (len(filenames), input_directory)

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            print >> sys.stderr, "Error processing %s: %s" % (fn, e)
            fail_count += 1

            # if we're storing output on disk, remove the output file
            # to avoid having partially-written data
            ofn = output_filename(fn)
            try:
                os.remove(ofn)
            except:
                # never mind if that fails
                pass

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conllXtostandoff
#!/usr/bin/env python

# Script to convert a CoNLL X (2006) tabbed dependency tree format
# file into BioNLP ST-flavored standoff and a reconstruction of the
# original text.

from __future__ import with_statement

import sys
import re
import os
import codecs

# maximum number of sentences to include in single output document
# (if None, doesn't split into documents)
MAX_DOC_SENTENCES = 10

# whether to output an explicit root note
OUTPUT_ROOT = True
# the string to use to represent the root node
ROOT_STR = 'ROOT'

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"

output_directory = None

# rewrites for characters appearing in CoNLL-X types that cannot be
# directly used in identifiers in brat-flavored standoff
charmap = {
    '<' : '_lt_',
    '>' : '_gt_',
    '+' : '_plus_',
    '?' : '_question_',
    '&' : '_amp_',
    ':' : '_colon_',
    '.' : '_period_',
    '!' : '_exclamation_',
}

def maptype(s):
    return "".join([charmap.get(c,c) for c in s])

def tokstr(start, end, ttype, idnum, text):
    # sanity checks
    assert '\n' not in text, "ERROR: newline in entity '%s'" % (text)
    assert text == text.strip(), "ERROR: tagged span contains extra whitespace: '%s'" % (text)
    return "T%d\t%s %d %d\t%s" % (idnum, maptype(ttype), start, end, text)

def depstr(depid, headid, rel, idnum):
    return "R%d\t%s Arg1:T%d Arg2:T%d" % (idnum, maptype(rel), headid, depid)

def output(infn, docnum, sentences):
    global output_directory

    if output_directory is None:
        txtout = sys.stdout
        soout = sys.stdout
    else:
        # add doc numbering if there is a sentence count limit,
        # implying multiple outputs per input
        if MAX_DOC_SENTENCES:
            outfnbase = os.path.basename(infn)+'-doc-'+str(docnum)
        else:
            outfnbase = os.path.basename(infn)
        outfn = os.path.join(output_directory, outfnbase)
        txtout = codecs.open(outfn+'.txt', 'wt', encoding=OUTPUT_ENCODING)
        soout = codecs.open(outfn+'.ann', 'wt', encoding=OUTPUT_ENCODING)

    offset, idnum, ridnum = 0, 1, 1

    doctext = ""

    for si, sentence in enumerate(sentences):
        tokens, deps = sentence

        # store mapping from per-sentence token sequence IDs to
        # document-unique token IDs
        idmap = {}

        # output tokens
        prev_form = None

        if OUTPUT_ROOT:
            # add an explicit root node with seq ID 0 (zero)
            tokens = [('0', ROOT_STR, ROOT_STR)] + tokens

        for ID, form, POS in tokens:

            if prev_form is not None:
                doctext = doctext + ' '
                offset += 1

            # output a token annotation
            print >> soout, tokstr(offset, offset+len(form), POS, idnum, form)
            assert ID not in idmap, "Error in data: dup ID"
            idmap[ID] = idnum
            idnum += 1

            doctext = doctext + form
            offset += len(form)
            
            prev_form = form

        # output dependencies
        for dep, head, rel in deps:

            # if root is not added, skip deps to the root (idx 0)
            if not OUTPUT_ROOT and head == '0':
                continue

            print >> soout, depstr(idmap[dep], idmap[head], rel, ridnum)
            ridnum += 1
        
        if si+1 != len(sentences):
            doctext = doctext + '\n'        
            offset += 1
            
    print >> txtout, doctext

def process(fn):
    docnum = 1
    sentences = []

    with codecs.open(fn, encoding=INPUT_ENCODING) as f:

        tokens, deps = [], []

        lines = f.readlines()

        for ln, l in enumerate(lines):
            l = l.strip()

            # igore lines starting with "#" as comments
            if len(l) > 0 and l[0] == "#":
                continue

            if re.match(r'^\s*$', l):
                # blank lines separate sentences
                if len(tokens) > 0:
                    sentences.append((tokens, deps))
                tokens, deps = [], []

                # limit sentences per output "document"
                if MAX_DOC_SENTENCES and len(sentences) >= MAX_DOC_SENTENCES:
                    output(fn, docnum, sentences)
                    sentences = []
                    docnum += 1

                continue

            # Assume it's a normal line. The format is tab-separated,
            # with ten fields, of which the following are used here
            # (from http://ilk.uvt.nl/conll/):
            # 1 ID     Token counter, starting at 1 for each new sentence.
            # 2 FORM   Word form or punctuation symbol.
            # 5 POSTAG Fine-grained part-of-speech tag
            # 7 HEAD   Head of the current token
            # 8 DEPREL Dependency relation to the HEAD.
            fields = l.split('\t')

            assert len(fields) == 10, "Format error on line %d in %s: expected 10 fields, got %d: %s" % (ln, fn, len(fields), l)

            ID, form, POS = fields[0], fields[1], fields[4]
            head, rel = fields[6], fields[7]

            tokens.append((ID, form, POS))
            # allow value "_" for HEAD to indicate no dependency
            if head != "_":
                deps.append((ID, head, rel))

        # process leftovers, if any
        if len(tokens) > 0:
            sentences.append((tokens, deps))
        if len(sentences) > 0:
            output(fn, docnum, sentences)

def main(argv):
    global output_directory

    # Take an optional "-o" arg specifying an output directory for the results
    output_directory = None
    filenames = argv[1:]
    if len(argv) > 2 and argv[1] == "-o":
        output_directory = argv[2]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[3:]

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            m = unicode(e).encode(OUTPUT_ENCODING)
            print >> sys.stderr, "Error processing %s: %s" % (fn, m)
            fail_count += 1

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = convert-EntrezGene
#!/usr/bin/evn python

# Script for converting Entrez Gene data into the brat normalization
# DB input format (http://brat.nlplab.org/normalization.html).

# The script expects as input the gene_info file available from the
# NCBI FTP site (ftp://ftp.ncbi.nih.gov/gene/DATA/).

# The gene_info file format is TAB-separated and contains the following
# fields (with mapping in output):

# 1:  tax_id: info:Taxonomy id
# 2:  GeneID: primary identifier
# 3:  Symbol: name:Symbol
# 4:  LocusTag: name:Locus 
# 5:  Synonyms: name:Synonym
# 6:  dbXrefs: (not included in output)
# 7:  chromosome: info:Chromosome
# 8:  map_location: (not included in output)
# 9:  description: info:Description
# 10: type_of_gene: info:Gene type
# 11: Symbol_from_nomenclature_authority: name:Symbol (if different from Symbol)
# 12: Full_name_from_nomenclature_authority: name:Full name
# 13: Nomenclature_status: (not included in output)
# 14: Other_designations: name:Other (if not "hypothetical protein")
# 15: Modification_date: (not  included in output)

# Multiple values for e.g. synonyms are separated by "|" in the input,
# and each such value is mapped to a separate entry in the output.
# Empty fields have the value "-" and are not included in the output.

from __future__ import with_statement

import sys
import re
import codecs

INPUT_ENCODING = "UTF-8"

# Field labels in output (mostly following Entrez Gene web interface labels)
TAX_ID_LABEL = 'Organism'
GENE_ID_LABEL = 'Gene ID'
SYMBOL_LABEL = 'Symbol'
LOCUS_LABEL = 'Locus'
SYNONYM_LABEL = 'Also known as'
CHROMOSOME_LABEL = 'Chromosome'
DESCRIPTION_LABEL = 'Description'
GENE_TYPE_LABEL = 'Gene type'
SYMBOL_AUTHORITY_LABEL = 'Official symbol'
FULL_NAME_AUTHORITY_LABEL = 'Official full name'
OTHER_DESIGNATION_LABEL = 'Name'

# Order in output (mostly following Entrez Gene web interface labels)
OUTPUT_LABEL_ORDER = [
    SYMBOL_AUTHORITY_LABEL,
    SYMBOL_LABEL,
    FULL_NAME_AUTHORITY_LABEL,
    GENE_TYPE_LABEL,
    TAX_ID_LABEL,
    SYNONYM_LABEL,
    OTHER_DESIGNATION_LABEL,
    LOCUS_LABEL,
    CHROMOSOME_LABEL,
    DESCRIPTION_LABEL,
]

# Values to filter out
FILTER_LIST = [
#    ('info', DESCRIPTION_LABEL, 'hypothetical protein'),
]

def process_tax_id(val, record):
    assert re.match(r'^[0-9]+$', val)
    record.append(('info', TAX_ID_LABEL, val))

def process_gene_id(val, record):
    assert re.match(r'^[0-9]+$', val)
    record.append(('key', GENE_ID_LABEL, val))

def process_symbol(val, record):
    assert val != '-'
    for v in val.split('|'):
        assert re.match(r'^\S(?:.*\S)?$', v)
        record.append(('name', SYMBOL_LABEL, v))

def process_locus(val, record):
    if val != '-':
        assert re.match(r'^[^\s|]+$', val)
        record.append(('name', LOCUS_LABEL, val))

def process_synonyms(val, record):
    if val != '-':
        for v in val.split('|'):
            assert re.match(r'^\S(?:.*\S)?$', v)
            record.append(('name', SYNONYM_LABEL, v))

def process_chromosome(val, record):
    if val != '-':
        assert re.match(r'^\S(?:.*\S)?$', val)
        record.append(('info', CHROMOSOME_LABEL, val))

def process_description(val, record):
    if val != '-':
        record.append(('info', DESCRIPTION_LABEL, val))        

def process_gene_type(val, record):
    if val != '-':
        record.append(('info', GENE_TYPE_LABEL, val))        

def process_symbol_authority(val, record):
    if val != '-':
        record.append(('name', SYMBOL_AUTHORITY_LABEL, val))

def process_full_name_authority(val, record):
    if val != '-':
        record.append(('name', FULL_NAME_AUTHORITY_LABEL, val))

def process_other_designations(val, record):
    if val != '-':
        for v in val.split('|'):
            assert re.match(r'^\S(?:.*\S)?$', v)
            record.append(('name', OTHER_DESIGNATION_LABEL, v))

field_processor = [
    process_tax_id,
    process_gene_id,
    process_symbol,
    process_locus,
    process_synonyms,
    None, # dbXrefs
    process_chromosome,
    None, # map_location
    process_description,
    process_gene_type,
    process_symbol_authority,
    process_full_name_authority,
    None, # Nomenclature_status
    process_other_designations,
    None, # Modification_date
]

output_priority = {}
for i, l in enumerate(OUTPUT_LABEL_ORDER):
    output_priority[l] = output_priority.get(l, i)

filter = set(FILTER_LIST)

def process_line(l):
    fields = l.split('\t')
    assert len(fields) == 15

    record = []
    for i, f in enumerate(fields):
        if field_processor[i] is not None:
            try:
                field_processor[i](f, record)
            except:
                print >> sys.stderr, "Error processing field %d: '%s'" % (i+1,f)
                raise

    # record key (primary ID) processed separately
    keys = [r for r in record if r[0] == 'key']
    assert len(keys) == 1
    key = keys[0]
    record = [r for r in record if r[0] != 'key']

    record.sort(lambda a, b: cmp(output_priority[a[1]],
                                 output_priority[b[1]]))

    filtered = []
    for r in record:
        if r not in filter:
            filtered.append(r)
    record = filtered

    seen = set()
    uniqued = []
    for r in record:
        if (r[0],r[2]) not in seen:
            seen.add((r[0],r[2]))
            uniqued.append(r)
    record = uniqued

    print '\t'.join([key[2]]+[':'.join(r) for r in record])

def process(fn):
    with codecs.open(fn, encoding=INPUT_ENCODING) as f:
        for ln, l in enumerate(f):
            l = l.rstrip('\r\n')

            # skip comments (lines beginning with '#')
            if l and l[0] == '#':
                continue

            try:
                process_line(l)
            except Exception, e:
                print >> sys.stderr, "Error processing line %d: %s" % (ln, l)
                raise
            
def main(argv):
    if len(argv) < 2:
        print >> sys.stderr, "Usage:", argv[0], "GENE-INFO-FILE"
        return 1

    fn = argv[1]
    process(fn)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = convert-NCBI-disease
#!/usr/bin/env python

# Special-purpose script for converting the NCBI disease corpus into a
# format recognized by brat.

# The NCBI disease corpus is distributed in a line-oriented format, each
# consisting of tab-separated triples (PMID, title, text). Annotations
# are inline in pseudo-XML, e.g.

#     <category="SpecificDisease">breast cancer</category>

# Note that the texts are tokenized. This script does not attempt to
# recover the original texts but instead keep the tokenization.

from __future__ import with_statement

import sys
import os
import re
import codecs

INPUT_ENCODING = "UTF-8"
OUTPUT_ENCODING = "UTF-8"

ENTITY_TYPE = "Disease"
ATTR_TYPE = "Category"
FILE_PREFIX = "PMID-"

output_directory = None

def output(docid, text, anns):
    global output_directory

    if output_directory is None:
        txtout = sys.stdout
        soout = sys.stdout
    else:
        # add doc numbering if there is a sentence count limit,
        # implying multiple outputs per input
        outfn = os.path.join(output_directory, FILE_PREFIX+docid)
        txtout = codecs.open(outfn+'.txt', 'wt', encoding=OUTPUT_ENCODING)
        soout = codecs.open(outfn+'.ann', 'wt', encoding=OUTPUT_ENCODING)

    txtout.write(text)
    idseq = 1
    for start, end, type_, text in anns:
        # write type as separate attribute
        print >> soout, "T%d\t%s %d %d\t%s" % (idseq, ENTITY_TYPE, start, end,
                                               text)
        print >> soout, "A%d\t%s T%d %s" % (idseq, ATTR_TYPE, idseq, type_)
        idseq += 1

    if output_directory is not None:
        txtout.close()
        soout.close()

def parse(s):
    text, anns = "", []
    # tweak text: remove space around annotations and strip space
    s = re.sub(r'(<category[^<>]*>)( +)', r'\2\1', s)
    s = re.sub(r'( +)(<\/category>)', r'\2\1', s)
    rest = s.strip()
    while True:
        m = re.match(r'^(.*?)<category="([^"]+)">(.*?)</category>(.*)$', rest)
        if not m:
            break
        pre, type_, tagged, rest = m.groups()
        text += pre
        anns.append((len(text), len(text)+len(tagged), type_, tagged))
        text += tagged
    text += rest
    return text, anns

def process(fn):
    docnum = 1
    sentences = []

    with codecs.open(fn, encoding=INPUT_ENCODING) as f:
        for l in f:
            l = l.strip('\n\r')
            try:
                PMID, title, body = l.split('\t', 2)
            except ValueError:
                assert False, "Expected three TAB-separated fields, got '%s'" %l
            # In a few cases, the body text contains tabs (probably by
            # error). Replace these with space.
            body = body.replace('\t', ' ')
            t_text, t_anns = parse(title)
            b_text, b_anns = parse(body)
            # combine
            t_text += '\n'
            b_text += '\n'
            text = t_text + b_text
            anns = t_anns + [(a[0]+len(t_text),a[1]+len(t_text),a[2],a[3]) 
                             for a in b_anns]
            output(PMID, text, anns)

def main(argv):
    global output_directory

    # Take an optional "-o" arg specifying an output directory
    output_directory = None
    filenames = argv[1:]
    if len(argv) > 2 and argv[1] == "-o":
        output_directory = argv[2]
        print >> sys.stderr, "Writing output to %s" % output_directory
        filenames = argv[3:]

    fail_count = 0
    for fn in filenames:
        try:
            process(fn)
        except Exception, e:
            print >> sys.stderr, "Error processing %s: %s" % (fn, e)
            fail_count += 1

    if fail_count > 0:
        print >> sys.stderr, """
##############################################################################
#
# WARNING: error in processing %d/%d files, output is incomplete!
#
##############################################################################
""" % (fail_count, len(filenames))

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = convert-NCBITaxon
#!/usr/bin/env python

# Special-purpose script for converting the NCBI taxonomy data dump
# into the brat normalization DB input format
# (http://brat.nlplab.org/normalization.html).

# The script expects as input the names.dmp file available from
# the NCBI FTP site (ftp://ftp.ncbi.nih.gov/pub/taxonomy/).
# As of late 2012, the following commands could be used to get
# this file (and a number of other related ones):
#
#     wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz
#     tar xvzf taxdump.tar.gz

# The names.dmp contains four fields per line, separated by pipe
# characters ("|"): tax_id, name_txt, unique name, and name class.
# This script discards the "unique name" field (which has values such
# as "Drosophila <fruit fly, genus>"), groups the others by tax_id,
# and filters likely irrelevance names by name class.

# Note that this script is not optimized in any way takes some minutes
# to run on the full NCBI taxonomy data.

from __future__ import with_statement

import sys
import re
import codecs

INPUT_ENCODING = "UTF-8"

# Name classes to discard from the data (unless they are the only that
# remain). These are discarded to avoid crowding the interface with a
# large number of irrelevant (e.g. "misspelling"), redundant
# (e.g. "blast name") or rarely used names (e.g. "type material").
DISCARD_NAME_CLASS = [
    "misspelling",
    "misnomer",
    "type material",
    "includes",
    "in-part",
    "authority",
    "teleomorph",
    "genbank anamorph",
    "anamorph",
    "blast name",
]

# Mapping between source data name classes and categories in output.
# Note that this excludes initial character capitalization, which is
# performed for by default as the last stage of processing.
NAME_CLASS_MAP = {
    "genbank common name" : "common name",
    "genbank synonym" : "synonym",
    "equivalent name" : "synonym",
    "acronym" : "synonym",
    "genbank acronym" : "synonym",
    "genbank anamorph" : "anamorph",
}

# Sort order of names for output.
NAME_ORDER_BY_CLASS = [
    "scientific name",
    "common name",
    "synonym",
] + DISCARD_NAME_CLASS

def main(argv):
    if len(argv) < 2:
        print >> sys.stderr, "Usage:", argv[0], "names.dmp"
        return 1

    namesfn = argv[1]

    # read in names.dmp, store name_txt and name class by tax_id
    names_by_tax_id = {}
    with codecs.open(namesfn, encoding=INPUT_ENCODING) as f:
        for i, l in enumerate(f):
            l = l.strip('\n\r')
            
            fields = l.split('|')

            assert len(fields) >= 4, "Format error on line %d: %s" % (i+1, l)
            fields = [t.strip() for t in fields]
            tax_id, name_txt, name_class = fields[0], fields[1], fields[3]

            if tax_id not in names_by_tax_id:
                names_by_tax_id[tax_id] = []
            names_by_tax_id[tax_id].append((name_txt, name_class))

    # filter names by class
    for tax_id in names_by_tax_id:
        for dnc in DISCARD_NAME_CLASS:            
            filtered = [(t, c) for t, c in names_by_tax_id[tax_id] if c != dnc]
            if filtered:
                names_by_tax_id[tax_id] = filtered
            else:
                print "emptied", tax_id, names_by_tax_id[tax_id]

    # map classes for remaining names
    for tax_id in names_by_tax_id:
        mapped = []
        for t, c in names_by_tax_id[tax_id]:
            mapped.append((t, NAME_CLASS_MAP.get(c,c)))
        names_by_tax_id[tax_id] = mapped

    # sort for output
    nc_rank = dict((b,a) for a,b in enumerate(NAME_ORDER_BY_CLASS))
    for tax_id in names_by_tax_id:
        names_by_tax_id[tax_id].sort(lambda a, b: cmp(nc_rank[a[1]],
                                                      nc_rank[b[1]]))

    # output in numerical order by taxonomy ID.
    for tax_id in sorted(names_by_tax_id, lambda a, b: cmp(int(a),int(b))):
        sys.stdout.write(tax_id)
        for t, c in names_by_tax_id[tax_id]:
            c = c[0].upper()+c[1:]
            sys.stdout.write("\tname:%s:%s" % (c, t))
        sys.stdout.write("\n")

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = corenlp
#!/usr/bin/env python

'''
Using pexpect to interact with CoreNLP.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-04-18
'''

from os import listdir
from os.path import isdir, join as path_join
from re import compile as re_compile, match

# I am not a huge fan of pexpect, but it will get the job done
from pexpect import spawn

### Constants
SENTENCE_OUTPUT_REGEX = re_compile(r'Sentence #[0-9]+ \([0-9]+ tokens\):')
OUTPUT_TOKEN_REGEX = re_compile(
    r' CharacterOffsetBegin=(?P<start>[0-9]+).*'
    r' CharacterOffsetEnd=(?P<end>[0-9]+).*'
    r' NamedEntityTag=(?P<type>[^ \]]+)'
    )
###

# Handle the interaction and hold the CoreNLP tagging process
class CoreNLPTagger(object):
    def __init__(self, core_nlp_path, mem='1024m'):
        assert isdir(core_nlp_path)
        # Try locating the JAR;s we need
        jar_paths = []
        for jar_regex in (
                '^stanford-corenlp-[0-9]{4}-[0-9]{2}-[0-9]{2}\.jar$',
                '^stanford-corenlp-[0-9]{4}-[0-9]{2}-[0-9]{2}-models\.jar$',
                '^joda-time\.jar$',
                '^xom\.jar$',
                ):
            for fname in listdir(core_nlp_path):
                if match(jar_regex, fname):
                    jar_paths.append(path_join(core_nlp_path, fname))
                    break
            else:
                assert False, 'could not locate any jar on the form "%s"' % jar_regex

        # Then hook up the CoreNLP process
        corenlp_cmd = ' '.join(('java -Xmx%s' % mem,
                '-cp %s' % ':'.join(jar_paths),
                'edu.stanford.nlp.pipeline.StanfordCoreNLP',
                '-annotators tokenize,ssplit,pos,lemma,ner',
                ))

        # Spawn the process
        self._core_nlp_process = spawn(corenlp_cmd, timeout=600)
        # Wait for the models to load, this is not overly fast
        self._core_nlp_process.expect('Entering interactive shell.')

    def __del__(self):
        # If our child process is still around, kill it
        if self._core_nlp_process.isalive():
            self._core_nlp_process.terminate()

    def tag(self, text):
        self._core_nlp_process.sendline(
                # Newlines are not healthy at this stage, remove them, they
                #   won't affect the offsets
                text.replace('\n', ' ')
                )

        # We can expect CoreNLP to be fairly fast, but let's cut it some slack
        #   half a second per "token" with a start-up of one second
        output_timeout = 1 + int(len(text.split()) * 0.5)
        # Make sure the data was actually seen by CoreNLP
        self._core_nlp_process.expect(SENTENCE_OUTPUT_REGEX,
                timeout=output_timeout)
        # Wait or the final results to arrive
        self._core_nlp_process.expect('NLP>', timeout=output_timeout)

        annotations = {}
        def _add_ann(start, end, _type):
            annotations[len(annotations)] = {
                    'type': _type,
                    'offsets': ((start, end), ),
                    'texts': ((text[start:end]), ),
                    }

        # Collect the NER spans, CoreNLP appears to be using only a BO tag-set
        #   so parsing it is piece of cake
        for sent_output in (d.strip() for i, d in enumerate(
                self._core_nlp_process.before.rstrip().split('\r\n'))
                if (i + 1) % 3 == 0):
            ann_start = None
            last_end = None
            ann_type = None
            for output_token in sent_output.split('] ['):
                #print ann_start, last_end, ann_type

                #print output_token #XXX:
                m = OUTPUT_TOKEN_REGEX.search(output_token)
                assert m is not None, 'failed to parse output'
                #print m.groupdict() #XXX:

                gdic = m.groupdict()
                start = int(gdic['start'])
                end = int(gdic['end'])
                _type = gdic['type']

                # Have we exited an annotation or changed type?
                if ((_type == 'O' or ann_type != _type)
                        and ann_start is not None):
                    _add_ann(ann_start, last_end, ann_type)
                    ann_start = None
                    ann_type = None
                elif _type != 'O' and ann_start is None:
                    ann_start = start
                    ann_type = _type
                last_end = end
            # Did we end with a remaining annotation?
            if ann_start is not None:
                _add_ann(ann_start, last_end, ann_type)

        return annotations

if __name__ == '__main__':
    # XXX: Hard-coded for testing
    tagger = CoreNLPTagger('stanford-corenlp-2012-04-09')
    print tagger.tag('Just a test, like the ones they do at IBM.\n'
            'Or Microsoft for that matter.')

########NEW FILE########
__FILENAME__ = corenlptaggerservice
#!/usr/bin/env python

'''
Simple tagger service using CoreNLP.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-04-18
'''

from argparse import ArgumentParser
from cgi import FieldStorage
from os.path import dirname, join as path_join

from corenlp import CoreNLPTagger

try:
    from json import dumps
except ImportError:
    # likely old Python; try to fall back on ujson in brat distrib
    from sys import path as sys_path
    sys_path.append(path_join(dirname(__file__), '../../server/lib/ujson'))
    from ujson import dumps

from sys import stderr
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

### Constants
ARGPARSER = ArgumentParser(description='XXX')#XXX:
ARGPARSER.add_argument('-p', '--port', type=int, default=47111,
        help='port to run the HTTP service on (default: 47111)')
TAGGER = None
#XXX: Hard-coded!
CORENLP_PATH = path_join(dirname(__file__), 'stanford-corenlp-2012-04-09')
###


class CoreNLPTaggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        print >> stderr, 'Received request'
        field_storage = FieldStorage(
                headers=self.headers,
                environ={
                    'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
                    },
                fp=self.rfile)

        global TAGGER
        json_dic = TAGGER.tag(field_storage.value)

        # Write the response
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(dumps(json_dic))
        print >> stderr, ('Generated %d annotations' % len(json_dic))

    def log_message(self, format, *args):
        return # Too much noise from the default implementation

def main(args):
    argp = ARGPARSER.parse_args(args[1:])

    print >> stderr, "WARNING: Don't use this in a production environment!"

    print >> stderr, 'Starting CoreNLP process (this takes a while)...',
    global TAGGER
    TAGGER = CoreNLPTagger(CORENLP_PATH)
    print >> stderr, 'Done!'

    server_class = HTTPServer
    httpd = server_class(('localhost', argp.port), CoreNLPTaggerHandler)
    print >> stderr, 'CoreNLP tagger service started'
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print >> stderr, 'CoreNLP tagger service stopped'

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = coresctostandoff
#!/usr/bin/env python

import sys
import re
try:
    import cElementTree as ET
except:
    import xml.etree.cElementTree as ET

# tags of elements to exclude from standoff output
# (not used now; anything not explicitly converted is excluded)
EXCLUDED_TAGS = [
#     "SP",
#     "IT",
#     "SB",
#     "REF",
#     "P",
#     "B",
#     "TITLE",
#     "PAPER",
#     "HEADER",
#     "DIV",
#     "BODY",
#     "ABSTRACT",
#     "THEAD",
#     "TGROUP",
#     "TBODY",
#     "SUP",
#     "EQN",
#     "ENTRY",
#     "XREF",
#     "ROW",
#     "EQ-S",

#     "text",
#     "datasection",
#     "s",
#     "mode2",
]
EXCLUDED_TAG = { t:True for t in EXCLUDED_TAGS }

# string to use to indicate elided text in output
ELIDED_TEXT_STRING = "[[[...]]]"

# maximum length of text strings printed without elision
MAXIMUM_TEXT_DISPLAY_LENGTH = 1000

# c-style string escaping for just newline, tab and backslash.
# (s.encode('string_escape') does too much for utf-8)
def c_escape(s):
    return s.replace('\\', '\\\\').replace('\t','\\t').replace('\n','\\n')

def strip_ns(tag):
    # remove namespace spec from tag, if any
    return tag if tag[0] != '{' else re.sub(r'\{.*?\}', '', tag)

class Standoff:
    def __init__(self, sid, element, start, end, text):
        self.sid     = sid
        self.element = element
        self.start   = start
        self.end     = end
        self.text    = text

    def compress_text(self, l):
        if len(self.text) >= l:
            el = len(ELIDED_TEXT_STRING)
            sl = (l-el)/2
            self.text = (self.text[:sl]+ELIDED_TEXT_STRING+self.text[-(l-sl-el):])
    def tag(self):
        return strip_ns(self.element.tag)

    def attrib(self):
        # remove namespace specs from attribute names, if any
        attrib = {}
        for a in self.element.attrib:
            if a[0] == "{":
                an = re.sub(r'\{.*?\}', '', a)
            else:
                an = a
            attrib[an] = self.element.attrib[a]
        return attrib

    def __str__(self):
        return "X%d\t%s %d %d\t%s\t%s" % \
            (self.sid, self.tag(), self.start, self.end, 
             c_escape(self.text.encode("utf-8")),
             " ".join(['%s="%s"' % (k.encode("utf-8"), v.encode("utf-8"))
                       for k,v in self.attrib().items()]))

def txt(s):
    return s if s is not None else ""

next_free_so_id = 1

def text_and_standoffs(e, curroff=0, standoffs=None):
    global next_free_so_id

    if standoffs == None:
        standoffs = []
    startoff = curroff
    # to keep standoffs in element occurrence order, append
    # a placeholder before recursing
    so = Standoff(next_free_so_id, e, 0, 0, "")
    next_free_so_id += 1
    standoffs.append(so)
    setext, dummy = subelem_text_and_standoffs(e, curroff+len(txt(e.text)), standoffs)
    text = txt(e.text) + setext
    curroff += len(text)
    so.start = startoff
    so.end   = curroff
    so.text  = text
    return (text, standoffs)

def subelem_text_and_standoffs(e, curroff, standoffs):
    startoff = curroff
    text = ""
    for s in e:
        stext, dummy = text_and_standoffs(s, curroff, standoffs)
        text += stext
        text += txt(s.tail)
        curroff = startoff + len(text)
    return (text, standoffs)

def empty_elements(e, tags=None):
    if tags is None or strip_ns(e.tag) in tags:
        e.clear()
    for c in e:
        empty_elements(c, tags)

def add_space(e):
    if strip_ns(e.tag) in ('title', ):
        e.tail = (e.tail if e.tail is not None else '') + '\n'
    for c in e:
        add_space(c)

def convert_coresc1(s):
    sostrings = []

    # create a textbound of the type specified by the "type"
    # attribute.

    tid = "T%d" % convert_coresc1._idseq
    sostrings.append('%s\t%s %d %d\t%s' % \
                         (tid, s.attrib()['type'], s.start, s.end, 
                          s.text.encode('utf-8')))

    # TODO: consider converting "advantage" and "novelty" attributes

    convert_coresc1._idseq += 1

    return sostrings
convert_coresc1._idseq = 1

convert_function = {
    'CoreSc1' : convert_coresc1,
    'annotationART' : convert_coresc1,
}

def main(argv=[]):
    if len(argv) != 4:
        print >> sys.stderr, "Usage:", argv[0], "IN-XML OUT-TEXT OUT-SO"
        return -1

    in_fn, out_txt_fn, out_so_fn = argv[1:]

    # "-" for STDIN / STDOUT
    if in_fn == "-":
        in_fn = "/dev/stdin"
    if out_txt_fn == "-":
        out_txt_fn = "/dev/stdout"
    if out_so_fn == "-":
        out_so_fn = "/dev/stdout"

    tree = ET.parse(in_fn)
    root = tree.getroot()

    # remove unannotated, (primarily) non-content elements
    empty_elements(root, set(['article-categories', 
                              'copyright-statement', 'license', 
                              'copyright-holder', 'copyright-year',
                              'journal-meta', 'article-id',
                              'back', 
                              'fig', 'table-wrap', 
                              'contrib-group',
                              'aff', 'author-notes',
                              'pub-date', 
                              'volume', 'issue', 
                              'fpage', 'lpage', 
                              'history'
                              ]))

    add_space(root)
    

    text, standoffs = text_and_standoffs(root)

    # filter
    standoffs = [s for s in standoffs if not s.tag() in EXCLUDED_TAG]

    # convert selected elements
    converted = []
    for s in standoffs:
        if s.tag() in convert_function:
            converted.extend(convert_function[s.tag()](s))
#         else:
#             converted.append(s)
    standoffs = converted

    for so in standoffs:
        try:
            so.compress_text(MAXIMUM_TEXT_DISPLAY_LENGTH)
        except AttributeError:
            pass

    # open output files 
    out_txt = open(out_txt_fn, "wt")
    out_so  = open(out_so_fn, "wt")

    out_txt.write(text.encode("utf-8"))
    for so in standoffs:
        print >> out_so, so

    out_txt.close()
    out_so.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = diff_and_mark
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:


# Preamble {{{
from __future__ import with_statement

'''
Mark the differences between two annotation files, creating a diff annotation
'''

try:
    import annotation
except ImportError:
    import os.path
    from sys import path as sys_path
    # Guessing that we might be in the brat tools/ directory ...
    sys_path.append(os.path.join(os.path.dirname(__file__), '../server/src'))
    import annotation

try:
    import argparse
except ImportError:
    import os.path
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(os.path.join(os.path.dirname(__file__), '../server/lib'))
    import argparse

# this seems to be necessary for annotations to find its config
sys_path.append(os.path.join(os.path.dirname(__file__), '..'))
# }}}




class Mapping: # {{{
    def __init__(self):
        self.first_by_second = dict()
        self.second_by_first = dict()
        self.only_in_second = []
    def add(self, first, second, is_clone=False):
        self.first_by_second[second] = first
        self.second_by_first[first] = second
        if is_clone:
            self.only_in_second.append(second)
    def get_second(self, first):
        return self.second_by_first[first] if first in self.second_by_first else None
    def get_first(self, second):
        return self.first_by_second[second] if second in self.first_by_second else None
    def is_only_in_second(self, second):
        return second in self.only_in_second
    def is_only_in_first(self, first):
        return first in self.second_by_first
# }}}


class AnnotationDiff: # {{{
    def __init__(self, first, second, result): # {{{
        self.first = first
        self.second = second
        self.result = result
        self.mapping = Mapping()
        self.first_textbounds = dict((textbound.id, textbound) for textbound in first.get_textbounds())
    # }}}

    def diff(self): # {{{
        # self.second_triggers = [t for t in self.second.get_triggers()]

        self.diff_entities()
        self.diff_triggers()
        self.diff_events()
        self.diff_oneline_comments()
        self.diff_equivs()
        self.diff_normalizations()
        self.diff_attributes()
        self.diff_relations()
    # }}}


    # Utilities for adding marks {{{
    def add_mark(self, type, target, reason):
        comment = annotation.OnelineCommentAnnotation(
                target,
                self.result.get_new_id('#'),
                type,
                "\t" + reason)
        self.result.add_annotation(comment)

    def add_missing(self, target, reason):
        self.add_mark('MissingAnnotation', target, reason)

    def add_added(self, target, reason):
        self.add_mark('AddedAnnotation', target, reason)

    def add_changed(self, target, reason):
        self.add_mark('ChangedAnnotation', target, reason)
    # }}}


    # Entities {{{
    def find_entity(self, haystack, needle):
        for entity in haystack.get_entities():
            if entity.same_span(needle) and entity.type == needle.type:
                return entity
        return None

    def diff_entities(self):
        found_first_ids = set()

        for entity in self.second.get_entities():
            found_first = self.find_entity(self.first, entity)
            if found_first is None:
                self.add_added(entity.id, 'Added entity')
            else:
                found_first_ids.add(found_first.id)
                self.mapping.add(found_first.id, entity.id)
        import copy
        for entity in self.first.get_entities():
            if not entity.id in found_first_ids:
                clone = copy.copy(entity)
                clone.id = self.result.get_new_id('T')
                self.result.add_annotation(clone)
                self.mapping.add(entity.id, clone.id, True)
                self.add_missing(clone.id, 'Missing entity')
    # }}}


    # Triggers {{{
    def find_trigger(self, haystack, needle):
        for trigger in haystack.get_triggers():
            if trigger.same_span(needle) and trigger.type == needle.type:
                return trigger
        return None

    def diff_triggers(self):
        found_first_ids = set()

        for trigger in self.second.get_triggers():
            found_first = self.find_trigger(self.first, trigger)
            if found_first:
                found_first_ids.add(found_first.id)
                self.mapping.add(found_first.id, trigger.id)
                # no `else`; the comments are handled by diff_events();
        import copy
        for trigger in self.first.get_triggers():
            if not trigger.id in found_first_ids:
                clone = copy.copy(trigger)
                clone.id = self.result.get_new_id('T')
                self.result.add_annotation(clone)
                self.mapping.add(trigger.id, clone.id, True)
    # }}}
    

    # Events {{{
    #
    # Events are a problem, since there can be multiple events for the
    # same trigger which are only distinguished by their arguments.
    # An additional problem is that arguments can also be events, so we
    # don't necessarily know the mapping of the arguments.
    # Thus, when comparing events-as-arguments, we compare only their
    # triggers.
    def trigger_or_self(self, target, triggers):
        try:
            return triggers[target]
        except KeyError:
            return target

    def find_closest_events(self, second_event, found_events_dict, first_triggers, second_triggers):
        second_args = dict((role, self.trigger_or_self(target, second_triggers)) for (role, target) in second_event.args)
        second_roles = set(second_args.keys())

        for first_event in self.first.get_events():
            if self.mapping.get_second(first_event.trigger) == second_event.trigger and first_event.type == second_event.type:
                first_args = dict((role, self.mapping.get_second(self.trigger_or_self(target, first_triggers))) for (role, target) in first_event.args)
                first_roles = set(first_args.keys())
                
                only_first = set(role for role in first_roles if first_args.get(role) != second_args.get(role))
                only_second = set(role for role in second_roles if first_args.get(role) != second_args.get(role))

                match = (first_event.id, first_args, second_args, only_first, only_second)
                score = len(only_first) + len(only_second)

                # XXX this is horrible; what's more Pythonic way?
                try:
                    found_events_dict[score]
                except KeyError:
                    found_events_dict[score] = dict()
                try:
                    found_events_dict[score][second_event.id]
                except KeyError:
                    found_events_dict[score][second_event.id] = []
                found_events_dict[score][second_event.id].append(match)

    def diff_events(self):
        second_triggers = dict((event.id, event.trigger) for event in self.second.get_events())
        first_triggers = dict((event.id, event.trigger) for event in self.first.get_events())

        found_first_ids = set()
        found_second_ids = set()

        found_events_dict = dict()

        # first pass, collect exact matches
        for event in self.second.get_events():
            self.find_closest_events(event, found_events_dict, first_triggers, second_triggers)

        # XXX Pythonize
        for score in sorted(found_events_dict.keys()):
            for second_event_id in found_events_dict[score]:
                if not second_event_id in found_second_ids:
                    for match in found_events_dict[score][second_event_id]:
                        first_event_id, first_args, second_args, only_first, only_second = match

                        if not first_event_id in found_first_ids:
                            found_first_ids.add(first_event_id)
                            found_second_ids.add(second_event_id)
                            self.mapping.add(first_event_id, second_event_id)
                            for role in only_first:
                                first_text = self.first_textbounds[self.mapping.get_first(first_args[role])].get_text()
                                if role in only_second:
                                    self.add_changed(second_event_id, 'Changed role %s (from %s "%s")' % (role, first_args[role], first_text))
                                else:
                                    self.add_changed(second_event_id, 'Missing role %s (%s "%s")' % (role, first_args[role], first_text))
                            for role in only_second - only_first:
                                self.add_changed(second_event_id, 'Added role %s' % role)

        for event in self.second.get_events():
            if not event.id in found_second_ids:
                self.add_added(event.id, 'Added event')

        for event in self.first.get_events():
            if not event.id in found_first_ids:
                import copy
                clone = copy.copy(event)
                clone.id = self.result.get_new_id('E')
                clone.trigger = self.mapping.get_second(event.trigger)
                clone.args = [(role, self.mapping.get_second(trigger)) for (role, trigger) in clone.args]
                self.result.add_annotation(clone)
                self.mapping.add(event.id, clone.id, True)
                self.add_missing(clone.id, 'Missing event')
    # }}}
    

    # Attributes {{{
    def find_attribute(self, haystack, needle, target):
        for attribute in haystack.get_attributes():
            if attribute.target == target and attribute.type == needle.type:
                return attribute
        return None

    def has_attribute(self, haystack, needle, target):
        return (self.find_attribute(haystack, needle, target) is not None)

    def diff_attributes(self):
        for attribute in self.second.get_attributes():
            target_in_first = self.mapping.get_first(attribute.target)
            found_first = self.find_attribute(self.first, attribute, target_in_first)
            if found_first is None:
                if target_in_first:
                    self.add_changed(attribute.target, 'Added attribute %s' % attribute.type)
            elif found_first.value != attribute.value:
                self.add_changed(attribute.target, 'Changed attribute %s (from %s)' % (attribute.type, found_first.value))
        for attribute in self.first.get_attributes():
            target_in_second = self.mapping.get_second(attribute.target)
            if self.mapping.is_only_in_first(attribute.target):
                # clone the attribute, since the event was cloned too;
                # no need to note it's missing, since the whole event is
                # missing
                import copy
                clone = copy.copy(attribute)
                clone.id = self.result.get_new_id('A')
                clone.target = target_in_second
                self.result.add_annotation(clone)
            else:
                if not self.has_attribute(self.second, attribute, target_in_second) and target_in_second:
                    self.add_changed(attribute.target, 'Missing attribute %s (%s)' % (attribute.type, attribute.value))
    # }}}
    

    # One-line Comments {{{
    def has_oneline_comment(self, haystack, needle, target):
        for oneline_comment in haystack.get_oneline_comments():
            if oneline_comment.target == target and oneline_comment.get_text() == needle.get_text():
                return True
        return False

    def diff_oneline_comments(self):
        for oneline_comment in self.second.get_oneline_comments():
            target_in_first = self.mapping.get_first(oneline_comment.target)
            if not self.has_oneline_comment(self.first, oneline_comment, target_in_first):
                self.add_changed(oneline_comment.target, 'Added %s: "%s"' % (oneline_comment.type, oneline_comment.get_text()))
        for oneline_comment in self.first.get_oneline_comments():
            target_in_second = self.mapping.get_second(oneline_comment.target)
            if not self.has_oneline_comment(self.second, oneline_comment, target_in_second):
                self.add_changed(target_in_second, 'Missing %s: "%s"' % (oneline_comment.type, oneline_comment.get_text()))
    # }}}


    # Equivs {{{
    def diff_equivs(self):
        # first we find out for each entity how they map between equiv
        # groups in the first vs. second (like, "T1 is group 2 in second,
        # but its corresponding entity in first is group 3": `"T1": [3, 2]`)
        correspondence_map = dict()
        second_equivs = [equiv.entities for equiv in self.second.get_equivs()]
        for equiv_group, equiv in enumerate(second_equivs):
            for entity in equiv:
                correspondence_map[entity] = [None, equiv_group]
        first_equivs = [equiv.entities for equiv in self.first.get_equivs()]
        for equiv_group, equiv in enumerate(first_equivs):
            for first_entity in equiv:
                entity = self.mapping.get_second(first_entity)
                if entity in correspondence_map:
                    correspondence_map[entity][0] = equiv_group
                else:
                    correspondence_map[entity] = [equiv_group, None]

        correspondence_hist = dict()
        for entity in correspondence_map.keys():
            key = "%s-%s" % tuple(correspondence_map[entity])
            if key not in correspondence_hist:
                correspondence_hist[key] = [1, correspondence_map[entity], [entity]]
            else:
                correspondence_hist[key][0] += 1
                correspondence_hist[key][2].append(entity)

        seen = []
        import operator
        sorted_hist = sorted(correspondence_hist.iteritems(), key=operator.itemgetter(1))
        for key, equiv_item in sorted_hist:
            count, correspondence_pair, entities = equiv_item
            first_group, second_group = correspondence_pair
            for entity in entities:
                if first_group is None:
                    self.add_changed(entity, 'Added to equiv')
                elif second_group is None:
                    rest = ["%s (%s)" % (self.mapping.get_second(other), self.first_textbounds[other].get_text()) for other in first_equivs[first_group] if other != entity]
                    self.add_changed(entity, 'Missing from equiv with %s' % ', '.join(rest))
                elif entity in seen:
                    rest = ["%s (%s)" % (self.mapping.get_second(other), self.first_textbounds[other].get_text()) for other in first_equivs[first_group] if other != entity]
                    self.add_changed(entity, 'Changed from equiv %s' % ', '.join(rest))
                else:
                    seen.append(entity)
    # }}}
    
    
    # Relations {{{
    def diff_relations(self):
        first_relations = dict(((self.mapping.get_second(relation.arg1), self.mapping.get_second(relation.arg2), relation.type), relation.id) for relation in self.first.get_relations())
        second_relations = dict(((relation.arg1, relation.arg2, relation.type), relation.id) for relation in self.second.get_relations())
        first_relations_set = set(first_relations)
        second_relations_set = set(second_relations)

        for relation in second_relations_set - first_relations_set:
            source, target, relation_type = relation
            self.add_changed(source, 'Added relation %s to %s' % (relation_type, target))
        for relation in first_relations_set - second_relations_set:
            source, target, relation_type = relation
            first_text = self.first_textbounds[self.mapping.get_first(target)].get_text()
            self.add_changed(source, 'Missing relation %s to %s "%s"' % (relation_type, target, first_text))
    # }}}
    

    # Normalizations {{{
    def has_normalization(self, haystack, needle, target):
        for normalization in haystack.get_normalizations():
            if normalization.target == target and normalization.refdb == needle.refdb and normalization.refid == needle.refid:
                return True
        return False

    def diff_normalizations(self):
        for normalization in self.second.get_normalizations():
            target_in_first = self.mapping.get_first(normalization.target)
            if not self.has_normalization(self.first, normalization, target_in_first):
                self.add_changed(normalization.target, 'Added normalization %s:%s "%s"' % (normalization.refdb, normalization.refid, normalization.reftext))
        for normalization in self.first.get_normalizations():
            target_in_second = self.mapping.get_second(normalization.target)
            if not self.has_normalization(self.second, normalization, target_in_second):
                self.add_changed(target_in_second, 'Missing normalization %s:%s "%s"' % (normalization.refdb, normalization.refid, normalization.reftext))
    # }}}
# }}}


# Diff invocation {{{
KNOWN_FILE_SUFF = [annotation.TEXT_FILE_SUFFIX] + annotation.KNOWN_FILE_SUFF
EXTENSIONS_RE = '\\.(%s)$' % '|'.join(KNOWN_FILE_SUFF)
def name_without_extension(file_name):
    import re
    return re.sub(EXTENSIONS_RE, '', file_name)

def copy_annotations(original_name, new_name):
    import shutil
    for extension in KNOWN_FILE_SUFF:
        try:
            shutil.copyfile('%s.%s' % (original_name, extension), '%s.%s' % (new_name, extension))
        except IOError, e:
            pass # that extension file does not exist
    return annotation.TextAnnotations(new_name)

def delete_annotations(name):
    bare_name = name_without_extension(name)
    for extension in KNOWN_FILE_SUFF:
        try:
            os.remove('%s.%s' % (name, extension))
        except OSError, e:
            pass # that extension file does not exist

def diff_files(first_name, second_name, result_name):
    first_bare = name_without_extension(first_name)
    second_bare = name_without_extension(second_name)
    result_bare = name_without_extension(result_name)

    first = annotation.TextAnnotations(first_bare)
    second = annotation.TextAnnotations(second_bare)
    result = copy_annotations(second_bare, result_bare)

    with result:
        AnnotationDiff(first, second, result).diff()

def is_dir(name):
    import os.path
    if os.path.exists(name):
        return os.path.isdir(name)
    else:
        bare_name = name_without_extension(name)
        for ext in annotation.KNOWN_FILE_SUFF:
            if os.path.isfile('%s.%s' % (bare_name, ext)):
                return False
        return None

def add_files(files, dir_or_file, errors):
    import glob
    import re
    is_a_dir = is_dir(dir_or_file)

    if is_a_dir is None:
        errors.append('Error: no annotation files found in %s' % dir_or_file)
    elif not is_a_dir:
        files.append(dir_or_file)
    else:
        subfiles = glob.glob(os.path.join(dir_or_file, '*'))
        matching_subfiles = [subfile for subfile in subfiles if re.search(EXTENSIONS_RE, subfile)]
        bare_subfiles = set([name_without_extension(subfile) for subfile in matching_subfiles])
        found = False
        for subfile in bare_subfiles:
            if is_dir(subfile) == False:
                files.append(subfile)
                found = True
        if not found:
            errors.append('Error: no annotation files found in %s' % dir_or_file)

def diff_files_and_dirs(firsts, second, result, force=False, verbose=False):
    import os.path
    errors = []
    fatal_errors = []
    second_dir = is_dir(second)
    result_dir = is_dir(result)
    single_first = len(firsts) == 1 and is_dir(firsts[0]) == False

    first_files = []
    for first in firsts:
        add_files(first_files, first, errors)

    if first_files == []:
        fatal_errors.append('Error: no annotation files found in %s' % ', '.join(firsts))
    if second_dir is None:
        fatal_errors.append('Error: no annotation files found in %s' % second)
    if not single_first and len(first_files) > 1 and result_dir is False:
        fatal_errors.append('Error: result of comparison of multiple files doesn\'t fit in %s' % result)
    errors.extend(fatal_errors)

    if fatal_errors == []:

        if not single_first and second_dir and result_dir is None:
            os.mkdir(result)
            result_dir = True

        for first_name in first_files:
            basename = os.path.basename(first_name)

            if verbose:
                print "Comparing", basename

            if second_dir:
                second_name = os.path.join(second, basename)
                if is_dir(second_name) != False:
                    errors.append('Error: No annotation files found corresponding to %s' % second_name)
                    continue
            else:
                second_name = second

            result_name = os.path.join(result, basename) if result_dir else result
            real_result_dir = is_dir(result_name)
            if real_result_dir == True:
                errors.append('Error: %s is a directory' % result_name)
                continue

            if real_result_dir == False:
                if force:
                    delete_annotations(result_name)
                else:
                    errors.append('Error: %s already exists (use --force to overwrite)' % result_name)
                    continue

            diff_files(first_name, second_name, result_name)

    if errors != []:
        sys.stderr.write("\n".join(errors) + "\n")
        exit(1)
# }}}







# Command-line invocation {{{
def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Diff two annotation files, creating a diff annotation file")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("firsts", metavar="<first>", nargs="+", help="Original (or gold standard) directories/files")
    ap.add_argument("second", metavar="<second>", help="Changed (or tested) directory/file")
    ap.add_argument("result", metavar="<result>", help="Output file/directory")
    ap.add_argument("-f", "--force", action="store_true", help="Force overwrite")
    return ap

def main(argv=None):
    if argv is None:
        argv = sys.argv
    args = argparser().parse_args(argv[1:])

    diff_files_and_dirs(args.firsts, args.second, args.result, args.force, args.verbose)

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
# }}}

########NEW FILE########
__FILENAME__ = discsegtostandoff
#!/usr/bin/env python

import sys
import re
try:
    import cElementTree as ET
except:
    import xml.etree.cElementTree as ET

# tags of elements to exclude from standoff output
EXCLUDED_TAGS = [
    "PAPER",
    "s",
]
EXCLUDED_TAG = { t:True for t in EXCLUDED_TAGS }

# string to use to indicate elided text in output
ELIDED_TEXT_STRING = "[[[...]]]"

# maximum length of text strings printed without elision
MAXIMUM_TEXT_DISPLAY_LENGTH = 1000

# c-style string escaping for just newline, tab and backslash.
# (s.encode('string_escape') does too much for utf-8)
def c_escape(s):
    return s.replace('\\', '\\\\').replace('\t','\\t').replace('\n','\\n')

def strip_ns(tag):
    # remove namespace spec from tag, if any
    return tag if tag[0] != '{' else re.sub(r'\{.*?\}', '', tag)

class Standoff:
    def __init__(self, sid, element, start, end, text):
        self.sid     = sid
        self.element = element
        self.start   = start
        self.end     = end
        self.text    = text

    def strip(self):
        while self.start < self.end and self.text[0].isspace():
            self.start += 1
            self.text = self.text[1:]
        while self.start < self.end and self.text[-1].isspace():
            self.end -= 1
            self.text = self.text[:-1]

    def compress_text(self, l):
        if len(self.text) >= l:
            el = len(ELIDED_TEXT_STRING)
            sl = (l-el)/2
            self.text = (self.text[:sl]+ELIDED_TEXT_STRING+self.text[-(l-sl-el):])
    def tag(self):
        return strip_ns(self.element.tag)

    def attrib(self):
        # remove namespace specs from attribute names, if any
        attrib = {}
        for a in self.element.attrib:
            if a[0] == "{":
                an = re.sub(r'\{.*?\}', '', a)
            else:
                an = a
            attrib[an] = self.element.attrib[a]
        return attrib

    def __str__(self):
        return "X%d\t%s %d %d\t%s\t%s" % \
            (self.sid, self.tag(), self.start, self.end, 
             c_escape(self.text.encode("utf-8")),
             " ".join(['%s="%s"' % (k.encode("utf-8"), v.encode("utf-8"))
                       for k,v in self.attrib().items()]))

def txt(s):
    return s if s is not None else ""

next_free_so_id = 1

def text_and_standoffs(e, curroff=0, standoffs=None):
    global next_free_so_id

    if standoffs == None:
        standoffs = []
    startoff = curroff
    # to keep standoffs in element occurrence order, append
    # a placeholder before recursing
    so = Standoff(next_free_so_id, e, 0, 0, "")
    next_free_so_id += 1
    standoffs.append(so)
    setext, _ = subelem_text_and_standoffs(e, curroff+len(txt(e.text)), 
                                           standoffs)
    text = txt(e.text) + setext
    curroff += len(text)
    so.start = startoff
    so.end   = curroff
    so.text  = text
    return (text, standoffs)

def subelem_text_and_standoffs(e, curroff, standoffs):
    startoff = curroff
    text = ""
    for s in e:
        stext, dummy = text_and_standoffs(s, curroff, standoffs)
        text += stext
        text += txt(s.tail)
        curroff = startoff + len(text)
    return (text, standoffs)

NORM_SPACE_REGEX = re.compile(r'\s+')

def normalize_space(e, tags=None):
    # eliminate document-initial space
    if strip_ns(e.tag) == 'PAPER':
        assert e.text == '' or e.text.isspace()
        e.text = ''
    if tags is None or strip_ns(e.tag) in tags:
        if e.text is not None:
            n = NORM_SPACE_REGEX.sub(' ', e.text)
            e.text = n
        if e.tail is not None:
            n = NORM_SPACE_REGEX.sub(' ', e.tail)
            e.tail = n
            
    for c in e:
        normalize_space(c)

def add_newlines(e):
    if (strip_ns(e.tag) == 'segment' and 
        e.attrib.get('segtype').strip() == 'Header'):
        assert e.tail == '' or e.tail.isspace(), 'unexpected content in tail'
        e.text = '\n' + (e.text if e.text is not None else '')
        e.tail = '\n'
    for c in e:
        add_newlines(c)

def generate_id(prefix):
    if prefix not in generate_id._next:
        generate_id._next[prefix] = 1
    id_ = prefix+str(generate_id._next[prefix])
    generate_id._next[prefix] += 1
    return id_
generate_id._next = {}

def convert_segment(s):
    sostrings = []

    # ignore empties
    if s.start == s.end:
        return []

    # first attempt:
#     # segment maps to "segment" textbound, with "section" and
#     # "segtype" attributes as attributes of this textbound.

#     tid = generate_id("T")
#     sostrings.append('%s\t%s %d %d\t%s' % \
#                          (tid, s.tag(), s.start, s.end, s.text.encode('utf-8')))

#     aid = generate_id("A")
#     sostrings.append('%s\tsection %s %s' % \
#                          (aid, tid, s.attrib()['section'].strip()))

#     aid = generate_id("A")
#     sostrings.append('%s\tsegtype %s %s' % \
#                          (aid, tid, s.attrib()['segtype'].strip()))

    # second attempt:

    # create a textbound of the type specified by the "type"
    # attribute.

    tid = generate_id('T')
    sostrings.append('%s\t%s %d %d\t%s' % \
                         (tid, s.attrib()['segtype'].strip(), s.start, s.end, 
                          s.text.encode('utf-8')))

    return sostrings

convert_function = {
    "segment" : convert_segment,
}

def main(argv=[]):
    if len(argv) != 4:
        print >> sys.stderr, "Usage:", argv[0], "IN-XML OUT-TEXT OUT-SO"
        return -1

    in_fn, out_txt_fn, out_so_fn = argv[1:]

    # "-" for STDIN / STDOUT
    if in_fn == "-":
        in_fn = "/dev/stdin"
    if out_txt_fn == "-":
        out_txt_fn = "/dev/stdout"
    if out_so_fn == "-":
        out_so_fn = "/dev/stdout"

    tree = ET.parse(in_fn)
    root = tree.getroot()

    # normalize space in target elements
    normalize_space(root, ['segment'])
    add_newlines(root)

    text, standoffs = text_and_standoffs(root)

    # eliminate extra space
    for s in standoffs:
        s.strip()

    # filter
    standoffs = [s for s in standoffs if not s.tag() in EXCLUDED_TAG]

    # convert selected elements
    converted = []
    for s in standoffs:
        if s.tag() in convert_function:
            converted.extend(convert_function[s.tag()](s))
        else:
            converted.append(s)
    standoffs = converted

    for so in standoffs:
        try:
            so.compress_text(MAXIMUM_TEXT_DISPLAY_LENGTH)
        except AttributeError:
            pass

    # open output files 
    out_txt = open(out_txt_fn, "wt")
    out_so  = open(out_so_fn, "wt")

    out_txt.write(text.encode("utf-8"))
    for so in standoffs:
        print >> out_so, so

    out_txt.close()
    out_so.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = ent2event
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Special-purpose script for rewriting a specific entity annotation
# type as an event. Can be useful if an annotation project has started
# out representing an annotation of type T as an entity and later
# decides that T should rather be an event.

# Usage example:

#     python tools/ent2event.py Core_Angiogenesis_Term Angiogenesis-1.4.1/*.ann


from __future__ import with_statement

import sys
import re
try:
    import annotation
except ImportError:
    import os.path
    from sys import path as sys_path
    # Guessing that we might be in the brat tools/ directory ...
    sys_path.append(os.path.join(os.path.dirname(__file__), '../server/src'))
    import annotation

# this seems to be necessary for annotations to find its config
sys_path.append(os.path.join(os.path.dirname(__file__), '..'))
    
options = None

def ent2event(anntype, fn):
    global options

    mapped = 0

    try:
        # remove possible .ann suffix to make TextAnnotations happy.
        nosuff_fn = fn.replace(".ann","")

        with annotation.TextAnnotations(nosuff_fn) as ann_obj:

            for ann in ann_obj.get_entities():
                if ann.type != anntype:
                    # not targeted
                    continue

                # map the entity annotation ann into an event.

                # first, create a new event annotation of the
                # same type for which ann is the trigger
                new_id = ann_obj.get_new_id('E')
                eann = annotation.EventAnnotation(ann.id, [], new_id, ann.type, '')            

                # next, process existing event annotations, remapping ID
                # references to the source annotation into references to
                # the new annotation
                for e in ann_obj.get_events():
                    for i in range(0, len(e.args)):
                        role, argid = e.args[i]
                        if argid == ann.id:
                            # need to remap
                            argid = new_id
                            e.args[i] = role, argid
                for c in ann_obj.get_oneline_comments():
                    if c.target == ann.id:
                        # need to remap
                        c.target = new_id

                # finally, add in the new event annotation
                ann_obj.add_annotation(eann)

                mapped += 1

            if options.verbose:
                print >> sys.stderr, mapped, 'mapped in', fn

    except annotation.AnnotationFileNotFoundError:
        print >> sys.stderr, "%s:\tFailed: file not found" % fn
    except annotation.AnnotationNotFoundError, e:
        print >> sys.stderr, "%s:\tFailed: %s" % (fn, e)

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Rewrite entity annotations of a given type as events.")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("type", metavar="TYPE", help="Type to rewrite.")
    ap.add_argument("files", metavar="FILE", nargs="+", help="File to process.")
    return ap

def main(argv=None):
    global options

    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    options = arg

    for fn in arg.files:
        ent2event(arg.type, fn)

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = generate-static
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

# Generates a web pages linking to visualizations of each document in
# a BioNLP ST 2011 Shared Task dataset.

import sys
import os

try:
    import argparse
except ImportError:
    from os.path import basename
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(join_path(basename(__file__), '../server/lib'))
    import argparse

# Filename extensions that should be considered in selecting files to
# process.
known_filename_extensions = [".txt", ".a1", ".a2"]


def argparser():
    ap=argparse.ArgumentParser(description="Generate web page linking to visualizations of BioNLP ST documents.")
    ap.add_argument("-v", "--visualizer", default="visualizer.xhtml", metavar="URL", help="Visualization script")
    ap.add_argument("-s", "--staticdir", default="static", metavar="DIR", help="Directory containing static visualizations")
    ap.add_argument("-d", "--dataset", default=None, metavar="NAME", help="Dataset name (derived from directory by default.)")
    ap.add_argument("directory", help="Directory containing ST documents.")
    ap.add_argument("prefix", metavar="URL", help="URL prefix to prepend to links")
    return ap


def files_to_process(dir):

    try:
        toprocess = []
        for fn in os.listdir(dir):
            fp = os.path.join(dir, fn)
            if os.path.isdir(fp):
                print >> sys.stderr, "Skipping directory %s" % fn
            elif os.path.splitext(fn)[1] not in known_filename_extensions:
                print >> sys.stderr, "Skipping %s: unrecognized suffix" % fn
            else:
                toprocess.append(fp)
    except OSError, e:
        print >> sys.stderr, "Error processing %s: %s" % (dir, e)

    return toprocess

def print_links(files, arg, out=sys.stdout):
    # group by filename root (filename without extension)
    grouped = {}
    for fn in files:
        root, ext = os.path.splitext(fn)
        if root not in grouped:
            grouped[root] = []
        grouped[root].append(ext)

    # output in sort order
    sorted = grouped.keys()
    sorted.sort()

    print >> out, "<table>"

    for root in sorted:
        path, fn = os.path.split(root)

        print >> out, "<tr>"
        print >> out, "  <td>%s</td>" % fn

        # dynamic visualization
        print >> out, "  <td><a href=\"%s\">dynamic</a></td>" % (arg.prefix+arg.visualizer+"#"+arg.dataset+"/"+fn)

        # static visualizations
        print >> out, "  <td><a href=\"%s\">svg</a></td>" % (arg.prefix+arg.staticdir+"/svg/"+arg.dataset+"/"+fn+".svg")
        print >> out, "  <td><a href=\"%s\">png</a></td>" % (arg.prefix+arg.staticdir+"/png/"+arg.dataset+"/"+fn+".png")

        # data files
        for ext in known_filename_extensions:
            if ext in grouped[root]:
                print >> out, "  <td><a href=\"%s\">%s</a></td>" % (arg.prefix+root+ext, ext[1:])
            else:
                # missing
                print >> out, "  <td>-</td>"

        print >> out, "</tr>"

    print >> out, "</table>"

def main(argv=None):
    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    # derive dataset name from directory if not separately specified
    if arg.dataset is None:
        dir = arg.directory
        # strip trailing separators
        while dir[-1] == os.sep:
            dir = dir[:-1]
        arg.dataset = os.path.split(dir)[1]
        print >> sys.stderr, "Assuming dataset name '%s', visualizations in %s" % (arg.dataset, os.path.join(arg.staticdir,arg.dataset))

    try:
        files = files_to_process(arg.directory)
        if files is None or len(files) == 0:
            print >> sys.stderr, "No files found"
            return 1
        print_header()
        print_links(files, arg)
        print_footer()
    except:
        print >> sys.stderr, "Error processing %s" % arg.directory
        raise
    return 0

def print_header(out=sys.stdout):
    print >> out, """<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN' 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <link rel="stylesheet" href="bionlp-st-11.css" type="text/css" />
    <meta http-equiv="Content-Type" content="text/html;charset=iso-8859-1"/>
    <title>BioNLP Shared Task 2011 - Data Visualization</title>
  </head>
<body>
  <div id="sites-chrome-everything" style="direction: ltr">
    <div id="sites-chrome-page-wrapper">

      <div id="sites-chrome-page-wrapper-inside">
	<div xmlns="http://www.w3.org/1999/xhtml" id="sites-chrome-header-wrapper">
	  <table id="sites-chrome-header" class="sites-layout-hbox" cellspacing="0">
	    <tr class="sites-header-primary-row">
	      <td id="sites-header-title">
		<div class="sites-header-cell-buffer-wrapper">
		  <h2>
		    <a href="https://sites.google.com/site/bionlpst/" dir="ltr">BioNLP Shared Task</a>

		  </h2>
		</div>
	      </td>
	    </tr>
	  </table>  
	</div> 
	<div id="sites-chrome-main-wrapper">
	  <div id="sites-chrome-main-wrapper-inside">
	    <table id="sites-chrome-main" class="sites-layout-hbox" cellspacing="0">
	      <tr>

		<td id="sites-canvas-wrapper">
		  <div id="sites-canvas">
		    <div xmlns="http://www.w3.org/1999/xhtml" id="title-crumbs" style="">
		    </div>
		    <h3 xmlns="http://www.w3.org/1999/xhtml" id="sites-page-title-header" style="" align="left">
		      <span id="sites-page-title" dir="ltr">BioNLP Shared Task 2011 Downloads</span>
		    </h3>
		    <div id="sites-canvas-main" class="sites-canvas-main">

		      <div id="sites-canvas-main-content">





			<!-- ##################################################################### -->
			<div id="main">
"""

def print_footer(out=sys.stdout):
    print >> out, """		      </div> 		      
		    </div>
		  </div>
		</td>
	      </tr>
	    </table>
	  </div>
	</div>
      </div>
    </div>
  </div>
</body>
</html>"""

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = idnorm
#!/usr/bin/env python

# "Normalizes" IDs in brat-flavored standoff so that the first "T" ID
# is "T1", the second "T2", and so on, for all ID prefixes.

from __future__ import with_statement

import sys
import re

DEBUG = True

class Annotation(object):
    def __init__(self, id_, type_):
        self.id_ = id_
        self.type_ = type_

    def map_ids(self, idmap):
        self.id_ = idmap[self.id_]

class Textbound(Annotation):
    def __init__(self, id_, type_, offsets, text):
        Annotation.__init__(self, id_, type_)
        self.offsets = offsets
        self.text = text

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, 
                                  ' '.join(self.offsets), self.text)
class ArgAnnotation(Annotation):
    def __init__(self, id_, type_, args):
        Annotation.__init__(self, id_, type_)
        self.args = args

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)
        mapped = []
        for arg in self.args:
            key, value = arg.split(':') 
            value = idmap[value]
            mapped.append("%s:%s" % (key, value))
        self.args = mapped

class Relation(ArgAnnotation):
    def __init__(self, id_, type_, args):
        ArgAnnotation.__init__(self, id_, type_, args)

    def map_ids(self, idmap):
        ArgAnnotation.map_ids(self, idmap)

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.args))

class Event(ArgAnnotation):
    def __init__(self, id_, type_, trigger, args):
        ArgAnnotation.__init__(self, id_, type_, args)
        self.trigger = trigger

    def map_ids(self, idmap):
        ArgAnnotation.map_ids(self, idmap)
        self.trigger = idmap[self.trigger]

    def __str__(self):
        return "%s\t%s:%s %s" % (self.id_, self.type_, self.trigger, 
                                 ' '.join(self.args))

class Attribute(Annotation):
    def __init__(self, id_, type_, target, value):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.value = value

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)
        self.target = idmap[self.target]

    def __str__(self):
        return "%s\t%s %s%s" % (self.id_, self.type_, self.target, 
                                '' if self.value is None else ' '+self.value)

class Normalization(Annotation):
    def __init__(self, id_, type_, target, ref, reftext):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.ref = ref
        self.reftext = reftext

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)
        self.target = idmap[self.target]

    def __str__(self):
        return "%s\t%s %s %s\t%s" % (self.id_, self.type_, self.target,
                                     self.ref, self.reftext)

class Equiv(Annotation):
    def __init__(self, id_, type_, targets):
        Annotation.__init__(self, id_, type_)
        self.targets = targets

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)
        self.targets = [idmap[target] for target in self.targets]

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.targets))

class Note(Annotation):
    def __init__(self, id_, type_, target, text):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.text = text

    def map_ids(self, idmap):
        Annotation.map_ids(self, idmap)
        self.target = idmap[self.target]

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, self.target, self.text)

def parse_textbound(fields):
    id_, type_offsets, text = fields
    type_offsets = type_offsets.split(' ')
    type_, offsets = type_offsets[0], type_offsets[1:]
    return Textbound(id_, type_, offsets, text)

def parse_relation(fields):
    id_, type_args = fields
    type_args = type_args.split(' ')
    type_, args = type_args[0], type_args[1:]
    return Relation(id_, type_, args)

def parse_event(fields):
    id_, type_trigger_args = fields
    type_trigger_args = type_trigger_args.split(' ')
    type_trigger, args = type_trigger_args[0], type_trigger_args[1:]
    type_, trigger = type_trigger.split(':')
    # remove empty "arguments"
    args = [a for a in args if a]
    return Event(id_, type_, trigger, args)

def parse_attribute(fields):
    id_, type_target_value = fields
    type_target_value = type_target_value.split(' ')
    if len(type_target_value) == 3:
        type_, target, value = type_target_value
    else:
        type_, target = type_target_value
        value = None
    return Attribute(id_, type_, target, value)

def parse_normalization(fields):
    id_, type_target_ref, reftext = fields
    type_, target, ref = type_target_ref.split(' ')
    return Normalization(id_, type_, target, ref, reftext)

def parse_note(fields):
    id_, type_target, text = fields
    type_, target = type_target.split(' ')
    return Note(id_, type_, target, text)

def parse_equiv(fields):
    id_, type_targets = fields
    type_targets = type_targets.split(' ')
    type_, targets = type_targets[0], type_targets[1:]
    return Equiv(id_, type_, targets)

parse_func = {
    'T': parse_textbound,
    'R': parse_relation,
    'E': parse_event,
    'N': parse_normalization,
    'M': parse_attribute,
    'A': parse_attribute,
    '#': parse_note,
    '*': parse_equiv,
    }

def parse(l, ln):
    assert len(l) and l[0] in parse_func, "Error on line %d: %s" % (ln, l)
    try:
        return parse_func[l[0]](l.split('\t'))
    except Exception:
        assert False, "Error on line %d: %s" % (ln, l)

def process(fn):
    idmap = {}

    with open(fn, "rU") as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

        annotations = []
        for i, l in enumerate(lines):
            annotations.append(parse(l, i+1))

        if DEBUG:
            for i, a in enumerate(annotations):
                assert lines[i] == str(a), ("Cross-check failed:\n  "+
                                            '"%s"' % lines[i] + " !=\n  "+
                                            '"%s"' % str(a))

        idmap = {}
        next_free = {}
        # special case: ID '*' maps to itself
        idmap['*'] = '*'
        for i, a in enumerate(annotations):
            if a.id_ == '*':
                continue
            assert a.id_ not in idmap, "Dup ID on line %d: %s" % (i, l)
            prefix = a.id_[0]
            seq = next_free.get(prefix, 1)
            idmap[a.id_] = prefix+str(seq)
            next_free[prefix] = seq+1

        for i, a in enumerate(annotations):
            a.map_ids(idmap)
            print(a)        

def main(argv):
    if len(argv) < 2:
        print >> sys.stderr, "Usage:", argv[0], "FILE [FILE ...]"
        return 1

    for fn in argv[1:]:
        process(fn)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = malt2connlX
#!/usr/bin/env python

'''
Convert Malt dependencies to CoNLL-X dependencies.

Usage:

    cat *.malt | ./malt2connlX.py > output.conll

NOTE: Beware of nasty Windows newlines:

    dos2unix *.malt

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-12-05
'''

from sys import stdin, stdout
from re import compile as _compile
from codecs import open as _open

### Constants
MALT_REGEX = _compile(ur'^(?P<token>.*?)\t(?P<pos>[^\t]+)\t'
        ur'(?P<head>[^\t]+)\t(?P<rel>[^\t]+)$')
# NOTE: My interpretation from reversing the format by example
OUTPUT_LINE = u'{token_num}\t{token}\t_\t{pos}\t{pos}\t_\t{head}\t{rel}\t_\t_'
###

def main(args):
    token_cnt = 0
    for line in (l.decode('utf-8').rstrip('\n') for l in stdin):
        if not line:
            # Done with the sentence
            token_cnt = 0
            stdout.write('\n')
            continue
        else:
            token_cnt += 1

        m = MALT_REGEX.match(line)
        assert m is not None, 'parse error (sorry...)'
        g_dic = m.groupdict()
        output = OUTPUT_LINE.format(
                token_num=token_cnt,
                token=g_dic['token'],
                pos=g_dic['pos'],
                head=g_dic['head'],
                rel=g_dic['rel']
                )
        stdout.write(output.encode('utf-8'))
        stdout.write('\n')

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = merge
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

from __future__ import with_statement

'''
Merge BioNLP Shared Task annotation format into a single annotation file.

find data -name '*.a1' -o -name '*.a2' -o -name '*.rel' -o -name '*.co' \
    | ./merge.py

Author:     Pontus Stenetorp
Version:    2011-01-17
'''

from collections import defaultdict
from os.path import join as join_path
from os.path import split as split_path
from shlex import split as shlex_split
from sys import stderr, stdin
from subprocess import Popen, PIPE

try:
    from argparse import ArgumentParser
except ImportError:
    from os.path import basename
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(join_path(basename(__file__), '../server/lib'))
    from argparse import ArgumentParser

### Constants
#TODO: Add to options?
UNMERGED_SUFFIXES=['a1', 'a2', 'co', 'rel']
#TODO: Add to options?
MERGED_SUFFIX='ann'
ARGPARSER = ArgumentParser(description=("Merge BioNLP'11 ST annotations "
    'into a single file, reads paths from stdin'))
ARGPARSER.add_argument('-w', '--no-warn', action='store_true',
        help='suppress warnings')
#ARGPARSER.add_argument('-d', '--debug', action='store_true',
#        help='activate additional debug output')
###

def keynat(string):
    '''
    http://code.activestate.com/recipes/285264-natural-string-sorting/
    '''
    it = type(1)
    r = []
    for c in string:
        if c.isdigit():
            d = int(c)
            if r and type( r[-1] ) == it:
                r[-1] = r[-1] * 10 + d
            else: 
                r.append(d)
        else:
            r.append(c.lower())
    return r

def main(args):
    argp = ARGPARSER.parse_args(args[1:])
    # ID is the stem of a file
    id_to_ann_files = defaultdict(list)
    # Index all ID;s before we merge so that we can do a little magic
    for file_path in (l.strip() for l in stdin):
        if not any((file_path.endswith(suff) for suff in UNMERGED_SUFFIXES)):
            if not argp.no_warn:
                import sys
                print >> sys.stderr, (
                        'WARNING: invalid file suffix for %s, ignoring'
                        ) % (file_path, )
            continue
        
        dirname, basename = split_path(file_path)
        id = join_path(dirname, basename.split('.')[0])
        id_to_ann_files[id].append(file_path)

    for id, ann_files in id_to_ann_files.iteritems():
        #XXX: Check if output file exists
        lines = []
        for ann_file_path in ann_files:
            with open(ann_file_path, 'r') as ann_file:
                for line in ann_file:
                    lines.append(line)

        with open(id + '.' + MERGED_SUFFIX, 'w') as merged_ann_file:
            for line in lines:
                merged_ann_file.write(line)

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = metamaptaggerservice
#!/usr/bin/env python

'''
An example of a tagging service using metamap.
'''

from argparse import ArgumentParser

from os.path import join as path_join
from os.path import dirname

try:
    from json import dumps
except ImportError:
    # likely old Python; try to fall back on ujson in brat distrib
    from sys import path as sys_path
    sys_path.append(path_join(dirname(__file__), '../server/lib/ujson'))
    from ujson import dumps

from subprocess import PIPE, Popen

from random import choice, randint
from sys import stderr
from urlparse import urlparse
try:
    from urlparse import parse_qs
except ImportError:
    # old Python again?
    from cgi import parse_qs
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import re

# use the brat sentence splitter
from sentencesplit import sentencebreaks_to_newlines

# use this MetaMap output converter
from MetaMaptoStandoff import MetaMap_lines_to_standoff

### Constants
METAMAP_SCRIPT   = path_join(dirname(__file__), './metamap_tag.sh')
METAMAP_COMMAND  = [METAMAP_SCRIPT]

ARGPARSER = ArgumentParser(description='An example HTTP tagging service using MetaMap')
ARGPARSER.add_argument('-p', '--port', type=int, default=47111,
        help='port to run the HTTP service on (default: 47111)')
###

def run_tagger(cmd):
    # runs the tagger identified by the given command.
    try:
        tagger_process = Popen(cmd, stdin=PIPE, stdout=PIPE, bufsize=1)
        return tagger_process
    except Exception, e:
        print >> stderr, "Error running '%s':" % cmd, e
        raise    

def _apply_tagger_to_sentence(text):
    # can afford to restart this on each invocation
    tagger_process = run_tagger(METAMAP_COMMAND)

    print >> tagger_process.stdin, text
    tagger_process.stdin.close()
    tagger_process.wait()

    response_lines = []

    for l in tagger_process.stdout:
        l = l.rstrip('\n')
        response_lines.append(l)
        
    try:
        tagged_entities = MetaMap_lines_to_standoff(response_lines, text)
    except:
        # if anything goes wrong, bail out
        print >> stderr, "Warning: MetaMap-to-standoff conversion failed for output:\n'%s'" % '\n'.join(response_lines)
        raise
        #return {}

    # MetaMap won't echo matched text, so get this separately
    for t in tagged_entities:
        t.eText = text[t.startOff:t.endOff]

    return tagged_entities

def _apply_tagger(text):
    # MetaMap isn't too happy with large outputs, so process a
    # sentence per invocation

    try:
        splittext = sentencebreaks_to_newlines(text)
    except:
        # if anything goes wrong, just go with the
        # original text instead
        print >> stderr, "Warning: sentence splitting failed for input:\n'%s'" % text
        splittext = text

    sentences = splittext.split('\n')
    all_tagged = []
    baseoffset = 0
    for s in sentences:
        tagged = _apply_tagger_to_sentence(s)

        # adjust offsets
        for t in tagged:
            t.startOff += baseoffset
            t.endOff += baseoffset

        all_tagged.extend(tagged)
        baseoffset += len(s)+1

    anns = {}

    idseq = 1
    for t in all_tagged:
        anns["T%d" % idseq] = {
            'type': t.eType,
            'offsets': ((t.startOff, t.endOff), ),
            'texts': (t.eText, ),
            }
        idseq += 1

    return anns
        

class MetaMapTaggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Get our query
        query = parse_qs(urlparse(self.path).query)

        try:
            json_dic = _apply_tagger(query['text'][0])
        except KeyError:
            # We weren't given any text to tag, such is life, return nothing
            json_dic = {}

        # Write the response
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(dumps(json_dic))
        print >> stderr, ('Generated %d annotations' % len(json_dic))

    def log_message(self, format, *args):
        return # Too much noise from the default implementation

def main(args):
    argp = ARGPARSER.parse_args(args[1:])

    print >> stderr, 'Starting MetaMap ...'

    server_class = HTTPServer
    httpd = server_class(('localhost', argp.port), MetaMapTaggerHandler)

    print >> stderr, 'MetaMap tagger service started'
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print >> stderr, 'MetaMap tagger service stopped'

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = MetaMaptoStandoff
#!/usr/bin/env python

# Script to convert MetaMap "fielded" ("-N" argument) output into
# standoff with reference to the original text.

import sys
import re
import os
import codecs

# Regex for the "signature" of a metamap "fielded" output line
FIELDED_OUTPUT_RE = re.compile(r'^\d+\|')

class taggedEntity:
    def __init__(self, startOff, endOff, eType, idNum):
        self.startOff = startOff
        self.endOff   = endOff  
        self.eType    = eType   
        self.idNum    = idNum   

    def __str__(self):
        return "T%d\t%s %d %d" % (self.idNum, self.eType, self.startOff, self.endOff)

def MetaMap_lines_to_standoff(metamap_lines, reftext=None):
    tagged = []
    idseq = 1
    for l in metamap_lines:
        l = l.rstrip('\n')

        # silently skip lines that don't match the expected format        
        if not FIELDED_OUTPUT_RE.match(l):
            continue
        
        # format is pipe-separated ("|") fields, the ones of interest
        # are in the following indices:
        # 3: preferred text form
        # 4: CUI
        # 5: semantic type (MetaMap code)
        # 8: start offset and length of match
        fields = l.split('|')

        if len(fields) < 9:
            print >> sys.stderr, "Note: skipping unparseable MetaMap output line: %s" % l
            continue

        ctext, CUI, semtype, offset = fields[3], fields[4], fields[5], fields[8]

        # strip surrounding brackets from semantic type
        semtype = semtype.replace('[','').replace(']','')

        # parse length; note that this will only pick the of multiple
        # discontinuous spans if they occur (simple heuristic for the
        # head)
        m = re.match(r'^(?:\d+:\d+,)*(\d+):(\d+)$', offset)
        start, length = m.groups()
        start, length = int(start), int(length)

        tagged.append(taggedEntity(start, start+length, semtype, idseq))
        idseq += 1


    print >> sys.stderr, "MetaMaptoStandoff: returning %s tagged spans" % len(tagged)

    return tagged

if __name__ == "__main__":
    lines = [l for l in sys.stdin]
    standoff = MetaMap_lines_to_standoff(lines)
    for s in standoff:
        print s


########NEW FILE########
__FILENAME__ = nersuitetaggerservice
#!/usr/bin/env python

'''
An example of a tagging service using NER suite.
'''

from argparse import ArgumentParser

from os.path import join as path_join
from os.path import dirname

try:
    from json import dumps
except ImportError:
    # likely old Python; try to fall back on ujson in brat distrib
    from sys import path as sys_path
    sys_path.append(path_join(dirname(__file__), '../server/lib/ujson'))
    from ujson import dumps

from subprocess import PIPE, Popen

from random import choice, randint
from sys import stderr
from urlparse import urlparse
try:
    from urlparse import parse_qs
except ImportError:
    # old Python again?
    from cgi import parse_qs
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import re

# use the brat sentence splitter
from sentencesplit import sentencebreaks_to_newlines

# and use this hack for converting BIO to standoff
from BIOtoStandoff import BIO_lines_to_standoff

### Constants
DOCUMENT_BOUNDARY = 'END-DOCUMENT'
NERSUITE_SCRIPT   = path_join(dirname(__file__), './nersuite_tag.sh')
NERSUITE_COMMAND  = [NERSUITE_SCRIPT, '-multidoc', DOCUMENT_BOUNDARY]

ARGPARSER = ArgumentParser(description='An example HTTP tagging service using NERsuite')
ARGPARSER.add_argument('-p', '--port', type=int, default=47111,
        help='port to run the HTTP service on (default: 47111)')
###

### Globals
tagger_process = None

def run_tagger(cmd):
    # runs the tagger identified by the given command.
    global tagger_process
    try:
        tagger_process = Popen(cmd, stdin=PIPE, stdout=PIPE, bufsize=1)
    except Exception, e:
        print >> stderr, "Error running '%s':" % cmd, e
        raise

def _apply_tagger(text):
    global tagger_process, tagger_queue

    # the tagger expects a sentence per line, so do basic splitting
    try:
        splittext = sentencebreaks_to_newlines(text)
    except:
        # if anything goes wrong, just go with the
        # original text instead
        print >> stderr, "Warning: sentence splitting failed for input:\n'%s'" % text
        splittext = text

    print >> tagger_process.stdin, splittext
    print >> tagger_process.stdin, DOCUMENT_BOUNDARY
    tagger_process.stdin.flush()

    response_lines = []
    while True:
        l = tagger_process.stdout.readline()
        l = l.rstrip('\n')
        
        if l == DOCUMENT_BOUNDARY:
            break

        response_lines.append(l)
        
    try:
        tagged_entities = BIO_lines_to_standoff(response_lines, text)
    except:
        # if anything goes wrong, bail out
        print >> stderr, "Warning: BIO-to-standoff conversion failed for BIO:\n'%s'" % '\n'.join(response_lines)
        return {}

    anns = {}

    for t in tagged_entities:
        anns["T%d" % t.idNum] = {
            'type': t.eType,
            'offsets': ((t.startOff, t.endOff), ),
            'texts': (t.eText, ),
            }

    return anns

class NERsuiteTaggerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Get our query
        query = parse_qs(urlparse(self.path).query)

        try:
            json_dic = _apply_tagger(query['text'][0])
        except KeyError:
            # We weren't given any text to tag, such is life, return nothing
            json_dic = {}

        # Write the response
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(dumps(json_dic))
        print >> stderr, ('Generated %d annotations' % len(json_dic))

    def log_message(self, format, *args):
        return # Too much noise from the default implementation

def main(args):
    argp = ARGPARSER.parse_args(args[1:])

    print >> stderr, 'Starting NERsuite ...'
    run_tagger(NERSUITE_COMMAND)

    server_class = HTTPServer
    httpd = server_class(('localhost', argp.port), NERsuiteTaggerHandler)

    print >> stderr, 'NERsuite tagger service started'
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print >> stderr, 'NERsuite tagger service stopped'

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = norm_db_init
#!/usr/bin/env python

# Creates SQL and simstring DBs for brat normalization support.

# Each line in the input file should have the following format:

# ID<TAB>TYPE1:LABEL1:STRING1<TAB>TYPE2:LABEL2:STRING2[...]

# Where the ID is the unique ID normalized to, and the
# TYPE:LABEL:STRING triplets provide various information associated
# with the ID.

# Each TYPE must be one of the following:

# - "name": STRING is name or alias
# - "attr": STRING is non-name attribute
# - "info": STRING is non-searchable additional information

# Each LABEL provides a human-readable label for the STRING. LABEL
# values are not used for querying.

# For example, for normalization to the UniProt protein DB the input
# could contain lines such as the following:

# P01258  name:Protein:Calcitonin      attr:Organism:Human
# P01257  name:Protein:Calcitonin      attr:Organism:Rat

# In search, each query string must match at least part of some "name"
# field to retrieve an ID. Parts of query strings not matching a name
# are used to query "attr" fields, allowing these to be used to
# differentiate between ambiguous names. Thus, for the above example,
# a search for "Human Calcitonin" would match P01258 but not P01257.
# Fields with TYPE "info" are not used for querying.

from __future__ import with_statement

import sys
import codecs
from datetime import datetime
from os.path import dirname, basename, splitext, join

import sqlite3 as sqlite

try:
    import simstring
except ImportError:
    errorstr = """
    Error: failed to import the simstring library.
    This library is required for approximate string matching DB lookup.
    Please install simstring and its python bindings from 
    http://www.chokkan.org/software/simstring/
"""
    print >> sys.stderr, errorstr
    sys.exit(1)

# Default encoding for input text
DEFAULT_INPUT_ENCODING = 'UTF-8'

# Normalization DB version lookup string and value (for compatibility
# checks)
NORM_DB_STRING = 'NORM_DB_VERSION'
NORM_DB_VERSION = '1.0.1'

# Default filename extension of the SQL database
SQL_DB_FILENAME_EXTENSION = 'db'

# Filename extension used for simstring database file.
SS_DB_FILENAME_EXTENSION = 'ss.db'

# Length of n-grams in simstring DBs
DEFAULT_NGRAM_LENGTH = 3

# Whether to include marks for begins and ends of strings
DEFAULT_INCLUDE_MARKS = False

# Maximum number of "error" lines to output
MAX_ERROR_LINES = 100

# Supported TYPE values
TYPE_VALUES = ["name", "attr", "info"]

# Which SQL DB table to enter type into
TABLE_FOR_TYPE = {
    "name" : "names",
    "attr" : "attributes",
    "info" : "infos",
}

# Whether SQL table includes a normalized string form
TABLE_HAS_NORMVALUE = {
    "names" : True,
    "attributes" : True,
    "infos" : False,
}

# sanity
assert set(TYPE_VALUES) == set(TABLE_FOR_TYPE.keys())
assert set(TABLE_FOR_TYPE.values()) == set(TABLE_HAS_NORMVALUE.keys())

# SQL for creating tables and indices
CREATE_TABLE_COMMANDS = [
"""
CREATE TABLE entities (
  id INTEGER PRIMARY KEY,
  uid VARCHAR(255) UNIQUE
);
""",
"""
CREATE TABLE labels (
  id INTEGER PRIMARY KEY,
  text VARCHAR(255)
);
""",
"""
CREATE TABLE names (
  id INTEGER PRIMARY KEY,
  entity_id INTEGER REFERENCES entities (id),
  label_id INTEGER REFERENCES labels (id),
  value VARCHAR(255),
  normvalue VARCHAR(255)
);
""",
"""
CREATE TABLE attributes (
  id INTEGER PRIMARY KEY,
  entity_id INTEGER REFERENCES entities (id),
  label_id INTEGER REFERENCES labels (id),
  value VARCHAR(255),
  normvalue VARCHAR(255)
);
""",
"""
CREATE TABLE infos (
  id INTEGER PRIMARY KEY,
  entity_id INTEGER REFERENCES entities (id),
  label_id INTEGER REFERENCES labels (id),
  value VARCHAR(255)
);
""",
]
CREATE_INDEX_COMMANDS = [
"CREATE INDEX entities_uid ON entities (uid);",
"CREATE INDEX names_value ON names (value);",
"CREATE INDEX names_normvalue ON names (normvalue);",
"CREATE INDEX names_entity_id ON names (entity_id);",
"CREATE INDEX attributes_value ON attributes (value);",
"CREATE INDEX attributes_normvalue ON attributes (normvalue);",
"CREATE INDEX attributes_entity_id ON attributes (entity_id);",
#"CREATE INDEX infos_value ON infos (value);", # unnecessary, not searchable
"CREATE INDEX infos_entity_id ON infos (entity_id);",
]

# SQL for selecting strings to be inserted into the simstring DB for
# approximate search
SELECT_SIMSTRING_STRINGS_COMMAND = """
SELECT DISTINCT(normvalue) FROM names
UNION 
SELECT DISTINCT(normvalue) from attributes;
"""

# Normalizes a given string for search. Used to implement
# case-insensitivity and similar in search.
# NOTE: this is a different sense of "normalization" than that
# implemented by a normalization DB as a whole: this just applies to
# single strings.
# NOTE2: it is critically important that this function is performed
# identically during DB initialization and actual lookup.
# TODO: enforce a single implementation.
def string_norm_form(s):
    return s.lower().strip().replace('-', ' ')

def default_db_dir():
    # Returns the default directory into which to store the created DBs.
    # This is taken from the brat configuration, config.py.

    # (Guessing we're in the brat tools/ directory...)
    sys.path.append(join(dirname(__file__), '..'))
    try:
        from config import WORK_DIR
        return WORK_DIR
    except ImportError:
        print >> sys.stderr, "Warning: failed to determine brat work directory, using current instead."
        return "."

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Create normalization DBs for given file")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output")
    ap.add_argument("-d", "--database", default=None, help="Base name of databases to create (default by input file name in brat work directory)")
    ap.add_argument("-e", "--encoding", default=DEFAULT_INPUT_ENCODING, help="Input text encoding (default "+DEFAULT_INPUT_ENCODING+")")
    ap.add_argument("file", metavar="FILE", help="Normalization data")
    return ap

def sqldb_filename(dbname):
    '''
    Given a DB name, returns the name of the file that is expected to
    contain the SQL DB.
    '''
    return join(default_db_dir(), dbname+'.'+SQL_DB_FILENAME_EXTENSION)

def ssdb_filename(dbname):
    '''
    Given a DB name, returns the  name of the file that is expected to
    contain the simstring DB.
    '''
    return join(default_db_dir(), dbname+'.'+SS_DB_FILENAME_EXTENSION)

def main(argv):
    arg = argparser().parse_args(argv[1:])

    # only simstring library default supported at the moment (TODO)
    assert DEFAULT_NGRAM_LENGTH == 3, "Error: unsupported n-gram length"
    assert DEFAULT_INCLUDE_MARKS == False, "Error: begin/end marks not supported"

    infn = arg.file

    if arg.database is None:
        # default database file name
        bn = splitext(basename(infn))[0]
        sqldbfn = sqldb_filename(bn)
        ssdbfn = ssdb_filename(bn)
    else:
        sqldbfn = arg.database+'.'+SQL_DB_FILENAME_EXTENSION
        ssdbfn = arg.database+'.'+SS_DB_FILENAME_EXTENSION

    if arg.verbose:
        print >> sys.stderr, "Storing SQL DB as %s and" % sqldbfn
        print >> sys.stderr, "  simstring DB as %s" % ssdbfn
    start_time = datetime.now()

    import_count, duplicate_count, error_count, simstring_count = 0, 0, 0, 0

    with codecs.open(infn, 'rU', encoding=arg.encoding) as inf:        

        # create SQL DB
        try:
            connection = sqlite.connect(sqldbfn)
        except sqlite.OperationalError, e:
            print >> sys.stderr, "Error connecting to DB %s:" % sqldbfn, e
            return 1
        cursor = connection.cursor()

        # create SQL tables
        if arg.verbose:
            print >> sys.stderr, "Creating tables ...",

        for command in CREATE_TABLE_COMMANDS:
            try:
                cursor.execute(command)
            except sqlite.OperationalError, e:
                print >> sys.stderr, "Error creating %s:" % sqldbfn, e, "(DB exists?)"
                return 1

        # import data
        if arg.verbose:
            print >> sys.stderr, "done."
            print >> sys.stderr, "Importing data ...",

        next_eid = 1
        label_id = {}
        next_lid = 1
        next_pid = dict([(t,1) for t in TYPE_VALUES])

        for i, l in enumerate(inf):
            l = l.rstrip('\n')

            # parse line into ID and TYPE:LABEL:STRING triples
            try:
                id_, rest = l.split('\t', 1)
            except ValueError:
                if error_count < MAX_ERROR_LINES:
                    print >> sys.stderr, "Error: skipping line %d: expected tab-separated fields, got '%s'" % (i+1, l)
                elif error_count == MAX_ERROR_LINES:
                    print >> sys.stderr, "(Too many errors; suppressing further error messages)"
                error_count += 1
                continue

            # parse TYPE:LABEL:STRING triples
            try:
                triples = []
                for triple in rest.split('\t'):
                    type_, label, string = triple.split(':', 2)
                    if type_ not in TYPE_VALUES:
                        print >> sys.stderr, "Unknown TYPE %s" % type_
                    triples.append((type_, label, string))
            except ValueError:
                if error_count < MAX_ERROR_LINES:
                    print >> sys.stderr, "Error: skipping line %d: expected tab-separated TYPE:LABEL:STRING triples, got '%s'" % (i+1, rest)
                elif error_count == MAX_ERROR_LINES:
                    print >> sys.stderr, "(Too many errors; suppressing further error messages)"
                error_count += 1
                continue

            # insert entity
            eid = next_eid
            next_eid += 1
            try:
                cursor.execute("INSERT into entities VALUES (?, ?)", (eid, id_))
            except sqlite.IntegrityError, e:
                if error_count < MAX_ERROR_LINES:
                    print >> sys.stderr, "Error inserting %s (skipping): %s" % (id_, e)
                elif error_count == MAX_ERROR_LINES:
                    print >> sys.stderr, "(Too many errors; suppressing further error messages)"
                error_count += 1
                continue

            # insert new labels (if any)
            labels = set([l for t,l,s in triples])
            new_labels = [l for l in labels if l not in label_id]
            for label in new_labels:
                lid = next_lid
                next_lid += 1
                cursor.execute("INSERT into labels VALUES (?, ?)", (lid, label))
                label_id[label] = lid

            # insert associated strings
            for type_, label, string in triples:
                table = TABLE_FOR_TYPE[type_]
                pid = next_pid[type_]
                next_pid[type_] += 1
                lid = label_id[label] # TODO
                if TABLE_HAS_NORMVALUE[table]:
                    normstring = string_norm_form(string)
                    cursor.execute("INSERT into %s VALUES (?, ?, ?, ?, ?)" % table,
                                   (pid, eid, lid, string, normstring))
                else:
                    cursor.execute("INSERT into %s VALUES (?, ?, ?, ?)" % table,
                                   (pid, eid, lid, string))

            import_count += 1

            if arg.verbose and (i+1)%10000 == 0:
                print >> sys.stderr, '.',

        if arg.verbose:
            print >> sys.stderr, "done."

        # create SQL indices
        if arg.verbose:
            print >> sys.stderr, "Creating indices ...",

        for command in CREATE_INDEX_COMMANDS:
            try:
                cursor.execute(command)
            except sqlite.OperationalError, e:
                print >> sys.stderr, "Error creating index", e
                return 1

        if arg.verbose:
            print >> sys.stderr, "done."

        # wrap up SQL table creation
        connection.commit()

        # create simstring DB
        if arg.verbose:
            print >> sys.stderr, "Creating simstring DB ...",
        
        try:
            ssdb = simstring.writer(ssdbfn)
            for row in cursor.execute(SELECT_SIMSTRING_STRINGS_COMMAND):
                # encode as UTF-8 for simstring
                s = row[0].encode('utf-8')
                ssdb.insert(s)
                simstring_count += 1
            ssdb.close()
        except:
            print >> sys.stderr, "Error building simstring DB"
            raise

        if arg.verbose:
            print >> sys.stderr, "done."

        cursor.close()

    # done
    delta = datetime.now() - start_time

    if arg.verbose:
        print >> sys.stderr
        print >> sys.stderr, "Done in:", str(delta.seconds)+"."+str(delta.microseconds/10000), "seconds"
    
    print "Done, imported %d entries (%d strings), skipped %d duplicate keys, skipped %d invalid lines" % (import_count, simstring_count, duplicate_count, error_count)

    return 0
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = norm_db_lookup
#!/usr/bin/env python

# Test script for lookup in a normalization SQL DB, intended for
# DB testing.

# TODO: duplicates parts of primary norm DB implementation, dedup.

import sys
import os.path
import sqlite3 as sqlite

TYPE_TABLES = ["names", "attributes", "infos"]
NON_EMPTY_TABLES = set(["names"])

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Print results of lookup in normalization SQL DB for keys read from STDIN.")
    ap.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output.")
    ap.add_argument("-np", "--no-prompt", default=False, action="store_true", help="No prompt.")
    ap.add_argument("database", metavar="DATABASE", help="Name of database to read")
    return ap

def string_norm_form(s):
    return s.lower().strip().replace('-', ' ')

def datas_by_ids(cursor, ids):
    # select separately from names, attributes and infos    
    responses = {}
    for table in TYPE_TABLES:
        command = '''
SELECT E.uid, L.text, N.value
FROM entities E
JOIN %s N
  ON E.id = N.entity_id
JOIN labels L
  ON L.id = N.label_id
WHERE E.uid IN (%s)''' % (table, ','.join(['?' for i in ids]))

        cursor.execute(command, list(ids))
        response = cursor.fetchall()

        # group by ID first
        for id_, label, value in response:
            if id_ not in responses:
                responses[id_] = {}
            if table not in responses[id_]:
                responses[id_][table] = []
            responses[id_][table].append([label, value])

        # short-circuit on missing or incomplete entry
        if (table in NON_EMPTY_TABLES and
            len([i for i in responses if responses[i][table] == 0]) != 0):
            return None

    # empty or incomplete?
    for id_ in responses:
        for t in NON_EMPTY_TABLES:
            if len(responses[id_][t]) == 0:
                return None

    # has expected content, format and return
    datas = {}
    for id_ in responses:
        datas[id_] = []
        for t in TYPE_TABLES:
            datas[id_].append(responses[id_].get(t,[]))
    return datas

def ids_by_name(cursor, name, exactmatch=False, return_match=False):
    return ids_by_names(cursor, [name], exactmatch, return_match)

def ids_by_names(cursor, names, exactmatch=False, return_match=False):
    if not return_match:
        command = 'SELECT E.uid'
    else:
        command = 'SELECT E.uid, N.value'

    command += '''
FROM entities E
JOIN names N
  ON E.id = N.entity_id
'''
    if exactmatch:
        command += 'WHERE N.value IN (%s)' % ','.join(['?' for n in names])
    else:
        command += 'WHERE N.normvalue IN (%s)' % ','.join(['?' for n in names])
        names = [string_norm_form(n) for n in names]

    cursor.execute(command, names)
    responses = cursor.fetchall()

    if not return_match:
        return [r[0] for r in responses]
    else:
        return [(r[0],r[1]) for r in responses]

def main(argv):
    arg = argparser().parse_args(argv[1:])

    # try a couple of alternative locations based on the given DB
    # name: name as path, name as filename in work dir, and name as
    # filename without suffix in work dir
    dbn = arg.database
    dbpaths = [dbn, os.path.join('work', dbn), os.path.join('work', dbn)+'.db']

    dbfn = None
    for p in dbpaths:
        if os.path.exists(p):
            dbfn = p
            break
    if dbfn is None:
        print >> sys.stderr, "Error: %s: no such file" % dbfn
        return 1
    
    try:
        connection = sqlite.connect(dbfn)
    except sqlite.OperationalError, e:
        print >> sys.stderr, "Error connecting to DB %s:" % dbfn, e
        return 1
    cursor = connection.cursor()

    while True:
        if not arg.no_prompt:
            print ">>> ",
        l = sys.stdin.readline()
        if not l:
            break

        l = l.rstrip()

        try:
            r = ids_by_name(cursor, l)
            if len(r) != 0:
                d = datas_by_ids(cursor, r)
                for i in d:
                    print i+'\t', '\t'.join([' '.join(["%s:%s" % (k,v) for k,v in a]) for a in d[i]])
            elif l == '':
                print "(Use Ctrl-D to exit)"
            else:
                print "(no record found for '%s')" % l
        except Exception, e:
            print >> sys.stderr, "Unexpected error", e
            return 1
    return 0
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = oboextract
#!/usr/bin/env python

# Basic support for extracting data from .obo ontology files.
# Adapted from readobo.py in sols.

# TODO: replace with a proper lib.

import sys
import re
from string import lowercase

options = None

def case_normalize_initial(s):
    # to avoid lowercasing first letter of e.g. abbrevs, require two
    # lowercase letters after initial capital.
    if re.match(r'^[A-Z][a-z]{2,}', s):
        # lowercase first letter
        return s[0].lower()+s[1:]
    else:
        return s

def case_normalize_all_words(s):
    return " ".join([case_normalize_initial(w) for w in s.split(" ")])

class Term:
    def __init__(self, tid, name, synonyms=None, defs=None, 
                 is_a=None, part_of=None):
        self.tid      = tid
        self.name     = name
        self.synonyms = synonyms if synonyms is not None else []
        self.defs     = defs     if defs     is not None else []
        self.is_a     = is_a     if is_a     is not None else []
        self.part_of  = part_of  if part_of  is not None else []

        self.parents  = []
        self.children = []

        # part_of "parents" and "children"
        self.objects    = []
        self.components = []

        self.cleanup()

    def obo_idspace(self):
        # returns the "id space" part of the ID identifying the ontology.
        if ":" in self.tid:
            # standard format: sequence prior to first colon.
            # Special case: if all lowercased, uppercase in order to get
            # e.g. "sao" match the OBO foundry convention.
            s = self.tid[:self.tid.index(":")]
            if len([c for c in s if c in lowercase]) == len(s):
                return s.upper()
            else:
                return s
        else:
            # nonstandard, try to guess
            m = re.match(r'^(.[A-Za-z_]+)', self.tid)
            #print >> sys.stderr, "Warning: returning %s for id space of nonstandard ID %s" % (m.group(1), self.tid)
            return m.group(1)

    def resolve_references(self, term_by_id, term_by_name=None):
        # is_a
        for ptid, pname in self.is_a:
            if ptid not in term_by_id:
                print >> sys.stderr, "Warning: is_a term '%s' not found, ignoring" % ptid
                continue
            parent = term_by_id[ptid]
            # name is not required information; check if included
            # and mapping defined (may be undef for dup names)
            if pname is not None and term_by_name is not None and term_by_name[pname] is not None:
                assert parent == term_by_name[pname]
            if self in parent.children:
                print >> sys.stderr, "Warning: dup is-a parent %s for %s, ignoring" % (ptid, str(self))
            else:
                self.parents.append(parent)
                parent.children.append(self)

        # part_of
        for prel, ptid, pname in self.part_of:
            if ptid not in term_by_id:
                print >> sys.stderr, "Error: part_of term '%s' not found, ignoring" % ptid
                continue
            pobject = term_by_id[ptid]
            # same as above for name
            if pname is not None and term_by_name is not None and term_by_name[pname] is not None:
                assert pobject == term_by_name[pname]
            if self in pobject.components:
                print >> sys.stderr, "Warning: dup part-of parent %s for %s, ignoring" % (ptid, str(self))
            else:
                self.objects.append((prel, pobject))
                pobject.components.append((prel, self))

    def _case_normalize(self, cn_func):
        self.name = cn_func(self.name)
        for i in range(len(self.synonyms)):
            self.synonyms[i] = (cn_func(self.synonyms[i][0]), self.synonyms[i][1])
        for i in range(len(self.is_a)):
            if self.is_a[i][1] is not None:
                self.is_a[i] = (self.is_a[i][0], cn_func(self.is_a[i][1]))

    def case_normalize_initial(self):
        # case-normalize initial character
        global case_normalize_initial
        self._case_normalize(case_normalize_initial)

    def case_normalize_all_words(self):
        # case-normalize initial characters of all words
        global case_normalize_all_words
        self._case_normalize(case_normalize_all_words)

    def cleanup(self):
        # some OBO ontologies have extra "." at the end of synonyms
        for i, s in enumerate(self.synonyms):
            if s[-1] == ".":
                # only remove period if preceded by "normal word"
                if re.search(r'\b[a-z]{2,}\.$', s):
                    c = s[:-1]
                    print >> sys.stderr, "Note: cleanup: '%s' -> '%s'" % (s, c)
                    self.synonyms[i] = c

    def __str__(self):
        return "%s (%s)" % (self.name, self.tid)

def parse_obo(f, limit_prefixes=None, include_nameless=False):
    all_terms = []
    term_by_id = {}

    # first non-space block is ontology info
    skip_block = True
    tid, prefix, name, synonyms, definitions, is_a, part_of, obsolete = None, None, None, [], [], [], [], False
    for ln, l in enumerate(f):
        # don't attempt a full parse, simply match the fields we require
        if l.strip() == "[Term]":
            assert tid is None
            assert name is None
            assert is_a == []
            skip_block = False
        if l.strip() == "[Typedef]":
            skip_block = True
        elif re.match(r'^id:.*', l) and not skip_block:
            assert tid is None, str(ln)+' '+tid
            # remove comments, if any
            l = re.sub(r'\s*\!.*', '', l)

            # Note: do loose ID matching to allow nonstandard cases
            # such as "CS01" and similar in EHDAA2 ... actually, do
            # allow pretty much any ID since there's stuff like
            # UBERON:FMA_7196-MA_0000141-MIAA_0000085-XAO_0000328-ZFA_0000436
            # out there.
            #m = re.match(r'^id: (([A-Z]{2,}[a-z0-9_]*):\d+)\s*$', l)
            m = re.match(r'^id: (([A-Za-z](?:\S*(?=:)|[A-Za-z_]*)):?\S+)\s*$', l)
            if m is None:
                print >> sys.stderr, "line %d: failed to match id, ignoring: %s" % (ln, l.rstrip())
                tid, prefix, name, synonyms, is_a, part_of, obsolete = None, None, None, [], [], [], False
                skip_block = True
            else:
                tid, prefix = m.groups()
        elif re.match(r'^name:.*', l) and not skip_block:
            assert tid is not None
            assert name is None
            m = re.match(r'^name: (.*?)\s*$', l)
            assert m is not None
            name = m.group(1)
        elif re.match(r'^is_a:.*', l) and not skip_block:
            assert tid is not None
            #assert name is not None
            # the comment (string after "!") is not required.
            # curlies allowed for UBERON, which has stuff like
            # "is_a: UBERON:0000161 {source="FMA"} ! orifice"
            # multiple comments allowed for UBERON and VAO
            m = re.match(r'^is_a: (\S+) *(?:\{[^{}]*\} *)?(?:\!.*?)?\! *(.*?)\s*$', l)
            if m:
                is_a.append(m.groups())
            else:
                m = re.match(r'^is_a: (\S+)\s*$', l)
                if m is not None:
                    is_a.append((m.group(1), None))
                else:
                    print >> sys.stderr, "Error: failed to parse '%s'; ignoring is_a" % l
        elif re.match(r'^relationship:\s*\S*part_of', l) and not skip_block:
            assert tid is not None
            assert name is not None
            # strip 'OBO_REL:' if present (used at least in HAO, TAO
            # and VAO). Comment not required, but use to check if present.
            m = re.match(r'^relationship: +(?:OBO_REL:)?(\S+) +(\S+) *(?:\{[^{}]*\} *)?\! *(.*?)\s*$', l)
            if m:
                part_of.append(m.groups())
            else:
                m = re.match(r'^relationship: +(?:OBO_REL:)?(\S+) +(\S+)\s*$', l)
                if m is not None:
                    part_of.append((m.group(1), m.group(2), None))
                else:
                    print >> sys.stderr, "Error: failed to parse '%s'; ignoring part_of" % l
        elif re.match(r'^synonym:.*', l) and not skip_block:
            assert tid is not None
            assert name is not None
            # more permissive, there's strange stuff out there
            #m = re.match(r'^synonym: "([^"]*)" ([A-Za-z_ ]*?) *\[.*\]\s*$', l)
            m = re.match(r'^synonym: "(.*)" ([A-Za-z_ ]*?) *\[.*\]\s*$', l)
            assert m is not None, "Error: failed to parse '%s'" % l
            synstr, syntype = m.groups()
            if synstr == "":
                print >> sys.stderr, "Note: ignoring empty synonym on line %d: %s" % (ln, l.strip())
            else:
                synonyms.append((synstr,syntype))
        elif re.match(r'^def:.*', l) and not skip_block:
            assert tid is not None
            assert name is not None
            m = re.match(r'^def: "(.*)" *\[.*\]\s*$', l)
            assert m is not None, "Error: failed to parse '%s'" % l
            definition = m.group(1)
            if definition == "":
                print >> sys.stderr, "Note: ignoring empty def on line %d: %s" % (ln, l.strip())
            else:
                definitions.append(definition)
        elif re.match(r'^is_obsolete:', l):
            m = re.match(r'^is_obsolete:\s*true', l)
            if m:
                obsolete = True
        elif re.match(r'^\s*$', l):
            # if everything's blank, there's just a sequence of blanks;
            # skip.
            if (tid is None and prefix is None and name is None and
                synonyms == [] and definitions == [] and 
                is_a == [] and part_of == []):
                #print >> sys.stderr, "Note: extra blank line %d" % ln
                continue

            # field end
            if (obsolete or
                (limit_prefixes is not None and prefix not in limit_prefixes)):
                #print >> sys.stderr, "Note: skip %s : %s" % (tid, name)
                tid, prefix, name, synonyms, definitions, is_a, part_of, obsolete = None, None, None, [], [], [], [], False
            elif not skip_block:
                assert tid is not None, "line %d: no ID for '%s'!" % (ln, name)
                if name is None and not include_nameless:
                    print >> sys.stderr, "Note: ignoring term without name (%s) on line %d" % (tid, ln)
                else:
                    if tid not in term_by_id:
                        t = Term(tid, name, synonyms, definitions, 
                                 is_a, part_of)
                        all_terms.append(t)
                        term_by_id[tid] = t
                    else:
                        print >> sys.stderr, "Error: duplicate ID '%s'; discarding all but first definition" % tid
                tid, prefix, name, synonyms, definitions, is_a, part_of, obsolete = None, None, None, [], [], [], [], False
            else:
                pass
        else:
            # just silently skip everything else
            pass

    assert tid is None
    assert name is None
    assert is_a == []
    
    return all_terms, term_by_id

def argparser():
    import argparse

    ap=argparse.ArgumentParser(description="Extract terms from OBO ontology.")
    ap.add_argument("-l", "--limit", default=None, metavar="PREFIX", help="Limit processing to given ontology prefix or prefixes (multiple separated by \"|\").")
    ap.add_argument("-d", "--depth", default=None, metavar="INT", help="Limit extraction to given depth from initial nodes.")
    ap.add_argument("-nc", "--no-case-normalization", default=False, action="store_true", help="Skip heuristic case normalization of ontology terms.")
    ap.add_argument("-nm", "--no-multiple-inheritance", default=False, action="store_true", help="Exclude subtrees involving multiple inheritance.")
    ap.add_argument("-ns", "--no-synonyms", default=False, action="store_true", help="Do not extract synonyms.")
    ap.add_argument("-nd", "--no-definitions", default=False, action="store_true", help="Do not extract definitions.")
    ap.add_argument("-e", "--exclude", default=[], metavar="TERM", nargs="+", help="Exclude subtrees rooted at given TERMs.")
    ap.add_argument("-s", "--separate-children", default=[], default=False, action="store_true", help="Separate subontologies found as children of the given term.")
    ap.add_argument("file", metavar="OBO-FILE", help="Source ontology.")
    ap.add_argument("-p", "--separate-parents", default=[], default=False, action="store_true", help="Separate subontologies of parents of the given terms.")
    ap.add_argument("terms", default=[], metavar="TERM", nargs="*", help="Root terms from which to extract.")
    return ap

multiple_parent_skip_count = 0

def get_subtree_terms(root, collection=None, depth=0):
    global options
    global multiple_parent_skip_count

    if collection is None:
        collection = []

    if root.traversed or root.excluded:
        return False

    if options.depth is not None and depth > options.depth:
        return False

    if options.no_multiple_inheritance and len(root.parents) > 1:
        # don't make too much noise about this
        if multiple_parent_skip_count < 10:
            print >> sys.stderr, "Note: not traversing subtree at %s %s: %d parents" % (root.tid, root.name, len(root.parents))
        elif multiple_parent_skip_count == 10:
            print >> sys.stderr, "(further 'not traversing subtree; multiple parents' notes suppressed)"
        multiple_parent_skip_count += 1
        return False

    root.traversed = True

#     collection.append([root.name, root.tid, "name"])
    collection.append(root)
#     if not options.no_synonyms:
#         for synstr, syntype in root.synonyms:
#             collection.append([synstr, root.tid, "synonym "+syntype])
    for child in root.children:
        get_subtree_terms(child, collection, depth+1)
    return collection

def exclude_subtree(root):
    if root.traversed:
        return False
    root.traversed = True
    root.excluded = True
    for child in root.children:
        exclude_subtree(child)

def main(argv=None):
    global options

    arg = argparser().parse_args(argv[1:])
    options = arg

    if arg.depth is not None:
        arg.depth = int(arg.depth)
        assert arg.depth > 0, "Depth limit cannot be less than or equal to zero"

    limit_prefix = arg.limit
    if limit_prefix is None:
        limit_prefixes = None
    else:
        limit_prefixes = limit_prefix.split("|")

    fn = arg.file

    if not arg.no_case_normalization:
        for i in range(len(arg.terms)):
            # we'll have to guess here
            arg.terms[i] = case_normalize_initial(arg.terms[i])

    f = open(fn)
    all_terms, term_by_id = parse_obo(f, limit_prefixes)
    # resolve references, e.g. the is_a ID list into parent and child
    # object references
    for t in all_terms:
        t.resolve_references(term_by_id)

    if not arg.no_case_normalization:
        for t in all_terms:
            # FMA systematically capitalizes initial letter; WBbt has
            # a mix of capitalization conventions; SAO capitalizes all
            # words.
            if t.obo_idspace() in ("FMA", "WBbt"):
                t.case_normalize_initial()
            elif t.obo_idspace() == "SAO":
                t.case_normalize_all_words()

    print >> sys.stderr, "OK, parsed %d (non-obsolete) terms." % len(all_terms)

    term_by_name = {}
    for t in all_terms:
        if t.name not in term_by_name:
            term_by_name[t.name] = t
        else:
            print >> sys.stderr, "Warning: duplicate name '%s'; no name->ID mapping possible" % t.name
            # mark unavailable by name
            term_by_name[t.name] = None

    for rootterm in arg.terms:
        # we'll allow this for the "separate parents" setting        
        assert arg.separate_parents or rootterm in term_by_name, "Error: given term '%s' not found (or obsolete) in ontology!" % rootterm

    # mark children and parents
    for t in all_terms:
        t.children = []
        t.parents  = []
    for t in all_terms:
        for ptid, pname in t.is_a:
            if ptid not in term_by_id:
                print >> sys.stderr, "Error: is_a term '%s' not found, removing" % ptid
                continue
            parent = term_by_id[ptid]
            # name is not required information; check if included
            # and mapping defined (may be undef for dup names)
            if pname is not None and pname in term_by_name and term_by_name[pname] is not None:
                if parent != term_by_name[pname]:
                    print >> sys.stderr, "Warning: given parent name '%s' mismatches parent term name (via ID) '%s'" % (parent.name, pname)
            if t in parent.children:
                print >> sys.stderr, "Warning: ignoring dup parent %s for %s" % (ptid, str(t))
            else:
                t.parents.append(parent)
                parent.children.append(t)

    for t in all_terms:
        t.traversed = False
        t.excluded  = False

    for excludeterm in arg.exclude:
        assert excludeterm in term_by_name, "Error: exclude term '%s' not found (or obsolete) in ontology!" % excludeterm
        exclude_subtree(term_by_name[excludeterm])
        
    for t in all_terms:
        t.traversed = False

    rootterms = []
    if not arg.separate_parents:
        # normal processing
        for t in arg.terms:
            if t not in term_by_name:
                print >> sys.stderr, "Error: given term '%s' not found!" % t
                return 1
            else:
                rootterms.append(term_by_name[t])

        # if no terms are given, just extract from all roots.
        if len(rootterms) == 0:
            for t in all_terms:
                if len(t.parents) == 0:
                    rootterms.append(t)
            #print >> sys.stderr, "Extracting from %d root terms (%s)" % (len(rootterms), ", ".join(rootterms))
            print >> sys.stderr, "Extracting from %d root terms." % len(rootterms)

    else:
        assert not arg.separate_children, "Incompatible arguments"
        # identify new rootterms as the unique set of parents of the given terms. 
        # to simplify call structure for extraction from multiple ontologies.
        unique_parents = {}
        for t in arg.terms:
            # allow missing
            if t in term_by_name:
                for p in term_by_name[t].parents:
                    unique_parents[p] = True
        assert len(unique_parents) != 0, "Failed to find any of given terms"

        # mark the parents as excluded to avoid redundant traversal
        for p in unique_parents:
            p.excluded = True

        # set rootterms and use the existing "separate children"
        # mechanism to trigger traversal
        rootterms = [p for p in unique_parents]
        # make the extraction order stable for better diffs
        rootterms.sort(lambda a,b: cmp(a.name,b.name))
        arg.separate_children = True

        # debugging
        print >> sys.stderr, "Splitting at the following:", ",".join(rootterms)

    for rootterm in rootterms:
        if not arg.separate_children:
            # normal, just print out everything from the root term as one
            # block
#             for n, tid, ntype in get_subtree_terms(rootterm):
#                 print "%s\t%s\t%s" % (n, tid, ntype)
            for t in get_subtree_terms(rootterm):
                strs = []
                strs.append("name:Name:"+t.name)
                if not arg.no_synonyms:
                    for synstr, syntype in t.synonyms:
                        # never mind synonym type
                        #strs.append("name:synonym-"+syntype+':'+synstr)
                        strs.append("name:Synonym:"+synstr)
                if not arg.no_definitions:
                    for d in t.defs:
                        strs.append("info:Definition:"+d)
                # don't include ontology prefix in ID
                id_ = t.tid.replace(t.obo_idspace()+':', '', 1) 
                print id_ + '\t' + '\t'.join(strs)
#                 print "%s\t%s\t%s" % (n, tid, ntype)
        else:
            # separate the children of the root term in output
            for c in rootterm.children:
                stt = []
                get_subtree_terms(c, stt)
            for n, tid, ntype in stt:
                    print "%s\t%s\t%s\t%s" % (c.name, n, tid, ntype)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = offlinearize
#!/usr/bin/env python

'''
Generate the offline_data directory contents.
HACKY and NOT OFFLINE, but needed for testing at least.
TODO: rewrite properly, without going through the net.

Usage:      tools/offlinearize <url-to-top-collection>

TODO behaviour:
* Start with root collection and recurse
* Put the result of getCollectionInformation into
  offline_data/**/collection.js
* Put the result of getDocument into
  offline_data/**/*.data.js
* Prefix the contents of each file with "jsonp="
* Remove the need for the command-line argument :)

Author:     Goran Topic <amadan mad scientist com>
Version:    2011-10-07
'''

import sys
from urlparse import urlparse, urljoin
from os.path import dirname, join as joinpath
from os import makedirs
from urllib import urlopen
from simplejson import loads

try:
    base_url = sys.argv[1]
    url = urlparse(base_url)
except:
    print sys.argv[1]
    print "Syntax: %s <url>" % sys.argv[0]
    sys.exit(1)

this_dir = dirname(sys.argv[0])
datadir = joinpath(this_dir, '../offline_data')

coll_and_doc = url.fragment
coll = dirname(coll_and_doc)[1:]

def convert_coll(coll):
    if coll == '':
        ajax_coll = '/'
    else:
        ajax_coll = '/%s/' % coll

    coll_query_url = urljoin(base_url, 'ajax.cgi?action=getCollectionInformation&collection=%s' % ajax_coll)
    coll_dir = joinpath(datadir, coll)
    try:
        makedirs(coll_dir)
    except:
        pass # hopefully because it exists; TODO: check the error value?

    print ajax_coll
    conn = urlopen(coll_query_url)
    jsonp = conn.read()
    conn.close
    with open(joinpath(coll_dir, 'collection.js'), 'w') as f:
        f.write("jsonp=")
        f.write(jsonp)

    coll_data = loads(jsonp)
    for item in coll_data['items']:
        if item[0] == 'd':
            doc = item[2]
            print "  %s" % doc
            doc_query_url = urljoin(base_url, 'ajax.cgi?action=getDocument&collection=%s&document=%s' % (ajax_coll, doc))

            conn = urlopen(doc_query_url)
            jsonp = conn.read()
            conn.close
            with open(joinpath(coll_dir, '%s.data.js' % doc), 'w') as f:
                f.write("jsonp=")
                f.write(jsonp)
        elif item[0] == 'c' and item[2] != '..':
            convert_coll(item[2])

convert_coll(coll)

########NEW FILE########
__FILENAME__ = pubdic_tagger
#!/usr/bin/env python

'''
Dictionary-based NER tagging server using PubDictionaries.
This code is based on that of randomtagger.py

Author:     Han-Cheol Cho
(Author of the original script:	Pontus Stenetorp)
Version:    2014-04-05
'''

from argparse import ArgumentParser
from cgi import FieldStorage

try:
	from json import dumps
except ImportError:
	# likely old Python; try to fall back on ujson in brat distrib
	from sys import path as sys_path
	from os.path import join as path_join
	from os.path import dirname
	sys_path.append(path_join(dirname(__file__), '../server/lib/ujson'))
	from ujson import dumps

from random import choice, randint
from sys import stderr
from urlparse import urlparse
try:
	from urlparse import parse_qs
except ImportError:
	# old Python again?
	from cgi import parse_qs
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import json
import urllib
import urllib2
import base64



### Constants
ARGPARSER = ArgumentParser(description='An example HTTP tagging service, '
				'tagging Confuse-a-Cat **AND** Dead-parrot mentions!')
ARGPARSER.add_argument('-p', '--port', type=int, default=56789,
				help='port to run the HTTP service on (default: 56789)')
###


#
# 1. Use PubDictionaries's ID (email) and password to use both uploaded dictionary and 
#   modified information (disabled and added entries).
# 2. Use "" for both variables to use only originally uploaded dictionary.
# 3. PubDictionaries does not provide any encryption yet!!
#
def build_headers(email="", password=""):
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'Authorization': b'Basic ' + base64.b64encode(email + b':' + password),
	}
	return headers

def build_data(text):
	return json.dumps({'text': text}).encode('utf-8')

def convert_for_brat(pubdic_result, text):
	anns = {}
	for idx, entity in enumerate(pubdic_result):
		ann_id = 'T%d' % idx
		anns[ann_id] = {
			'type': entity['obj'],     # ID of an entry
			'offsets': ((entity['begin'], entity['end']), ),
			'texts': (text[entity['begin']:entity['end']], ),
			# Use entity['dictionary_name'] to distinguish the dictionary of this entry
			#   when you use an annotator url of multiple dictionaries.
		}
	return anns


class RandomTaggerHandler(BaseHTTPRequestHandler):
	def do_POST(self):
		field_storage = FieldStorage(
			headers=self.headers,
			environ={
					'REQUEST_METHOD':'POST',
					'CONTENT_TYPE':self.headers['Content-type'],
					},
			fp=self.rfile)

			# Do your random tagging magic
		try:
			# Prepare the request header and data
			headers = build_headers("", "")     # email and password of PubDictionaries
			text    = field_storage.value.decode('utf-8')     # For "ann['texts']" in format conversion
			data    = build_data(text)
			
			# Make a request and retrieve the result
			annotator_url = "http://pubdictionaries.dbcls.jp:80/dictionaries/EntrezGene%20-%20Homo%20Sapiens/text_annotation?matching_method=approximate&max_tokens=6&min_tokens=1&threshold=0.8&top_n=0"
			request = urllib2.Request(annotator_url, data=data, headers=headers)
			
			f   = urllib2.urlopen(request)
			res = f.read()
			f.close()

			# Format the result for BRAT
			json_dic = convert_for_brat(json.loads(res), text)

		except KeyError:
			# We weren't given any text to tag, such is life, return nothing
			json_dic = {}

		# Write the response
		self.send_response(200)
		self.send_header('Content-type', 'application/json; charset=utf-8')
		self.end_headers()

		self.wfile.write(dumps(json_dic))
		print >> stderr, ('Generated %d annotations' % len(json_dic))

	def log_message(self, format, *args):
		return # Too much noise from the default implementation


def main(args):
		argp = ARGPARSER.parse_args(args[1:])

		server_class = HTTPServer
		httpd = server_class(('localhost', argp.port), RandomTaggerHandler)

		print >> stderr, 'PubDictionary NER tagger service started on port %s' % (argp.port)
		try:
				httpd.serve_forever()
		except KeyboardInterrupt:
				pass
		httpd.server_close()
		print >> stderr, 'PubDictionary tagger service stopped'


if __name__ == '__main__':
		from sys import argv
		exit(main(argv))




########NEW FILE########
__FILENAME__ = randomtaggerservice
#!/usr/bin/env python

'''
An example of a tagging service.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-03-05
'''

from argparse import ArgumentParser
from cgi import FieldStorage

try:
    from json import dumps
except ImportError:
    # likely old Python; try to fall back on ujson in brat distrib
    from sys import path as sys_path
    from os.path import join as path_join
    from os.path import dirname
    sys_path.append(path_join(dirname(__file__), '../server/lib/ujson'))
    from ujson import dumps

from random import choice, randint
from sys import stderr
from urlparse import urlparse
try:
    from urlparse import parse_qs
except ImportError:
    # old Python again?
    from cgi import parse_qs
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

### Constants
ARGPARSER = ArgumentParser(description='An example HTTP tagging service, '
        'tagging Confuse-a-Cat **AND** Dead-parrot mentions!')
ARGPARSER.add_argument('-p', '--port', type=int, default=47111,
        help='port to run the HTTP service on (default: 47111)')
###

def _random_span(text):
    # A random span not starting or ending with spaces or including a new-line
    attempt = 1
    while True:
        start = randint(0, len(text))
        end = randint(start + 3, start + 25)

        # Did we violate any constraints?
        if (
                # We landed outside the text!
                end > len(text) or
                # We contain a newline!
                '\n' in text[start:end] or
                # We have a leading or trailing space!
                (text[start:end][-1] == ' ' or text[start:end][0] == ' ')
                ):
            # Well, try again then...?
            if attempt >= 100:
                # Bail, we failed too many times
                return None, None, None
            attempt += 1
            continue
        else:
            # Well done, we got one!
            return start, end, text[start:end]

def _random_tagger(text):
    # Generate some annotations
    anns = {}
    if not text:
        # We got no text, bail
        return anns

    num_anns = randint(1, len(text) / 100)
    for ann_num in xrange(num_anns):
        ann_id = 'T%d' % ann_num
        # Annotation type
        _type = choice(('Confuse-a-Cat', 'Dead-parrot', ))
        start, end, span_text = _random_span(text)
        if start is None:
            # Random failed, continue to the next annotation
            continue
        anns[ann_id] = {
                'type': _type,
                'offsets': ((start, end), ),
                'texts': (span_text, ),
                }
    return anns

class RandomTaggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        field_storage = FieldStorage(
                headers=self.headers,
                environ={
                    'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-type'],
                    },
                fp=self.rfile)

        # Do your random tagging magic
        try:
            json_dic = _random_tagger(field_storage.value.decode('utf-8'))
        except KeyError:
            # We weren't given any text to tag, such is life, return nothing
            json_dic = {}

        # Write the response
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(dumps(json_dic))
        print >> stderr, ('Generated %d random annotations' % len(json_dic))

    def log_message(self, format, *args):
        return # Too much noise from the default implementation

def main(args):
    argp = ARGPARSER.parse_args(args[1:])

    server_class = HTTPServer
    httpd = server_class(('localhost', argp.port), RandomTaggerHandler)
    print >> stderr, 'Random tagger service started on port %s' % (argp.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print >> stderr, 'Random tagger service stopped'

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = respace
#!/usr/bin/env python

# Script to revise the whitespace content of a PMC NXML file for text
# content extraction.

from __future__ import with_statement

import sys
import os
import re
import codecs

# TODO: switch to lxml
try:
    import xml.etree.ElementTree as ET
except ImportError: 
    import cElementTree as ET

# TODO: the model of "space wrap" is unnecessarily crude in many
# cases. For example, for <issue> we would ideally want to have
# "<issue>1</issue><title>Foo</title>" spaced as "1 Foo" but
# "<issue>1</issue>: <page>100</page>" spaced as "1: 100".  This could
# be addressed by differentiating between things that should be
# wrapped by space in all cases and ones where it's only needed
# at non-word-boundaries (\b).

# tag to use for inserted elements
INSERTED_ELEMENT_TAG = "n2t-spc"

INPUT_ENCODING="UTF-8"
OUTPUT_ENCODING="UTF-8"

# command-line options
options = None

newline_wrap_element = set([
        "CURRENT_TITLE",

        "CURRENT_AUTHORLIST",

        "ABSTRACT",
        "P",

        "TABLE",
        "FIGURE",

        "HEADER",

        "REFERENCE",

        "article-title",
        "abstract",
        "title",
        "sec",
        "p",
        "contrib",   # contributor (author list)
        "aff",       # affiliation
        "pub-date",  # publication date
        "copyright-statement",
        "table",
        "table-wrap",
        "figure",
        "fig",       # figure (alternate)
        "tr",        # table row
        "kwd-group", # keyword group
        ])

space_wrap_element = set([
        "AUTHOR",
        "SURNAME",

        "CURRENT_AUTHOR",
        "CURRENT_SURNAME",

        "TITLE",
        "JOURNAL",

        "YEAR",

        # author lists
        "surname",
        "given-names",
        "email",
        # citation details
        "volume",
        "issue",
        "year",
        "month",
        "day",
        "fpage",
        "lpage",
        "pub-id",
        "copyright-year",
        # journal meta
        "journal-id",
        "journal-title",
        "issn",
        "publisher-name",
        # article meta
        "article-id",
        "kwd",  # keyword
        # miscellaneous
        "label",
        "th",
        "td",
        ])

# strip anything that we're wrapping; this is a bit unnecessarily
# aggressive in cases but guarantees normalization
strip_element = newline_wrap_element | space_wrap_element

class Standoff:
    def __init__(self, element, start, end):
        self.element = element
        self.start   = start
        self.end     = end

def txt(s):
    return s if s is not None else ""

def text_and_standoffs(e):
    strings, standoffs = [], []
    _text_and_standoffs(e, 0, strings, standoffs)
    text = "".join(strings)
    return text, standoffs
    
def _text_and_standoffs(e, curroff, strings, standoffs):
    startoff = curroff
    # to keep standoffs in element occurrence order, append
    # a placeholder before recursing
    so = Standoff(e, 0, 0)
    standoffs.append(so)
    if e.text is not None and e.text != "":
        strings.append(e.text)
        curroff += len(e.text)
    curroff = _subelem_text_and_standoffs(e, curroff, strings, standoffs)
    so.start = startoff
    so.end   = curroff
    return curroff

def _subelem_text_and_standoffs(e, curroff, strings, standoffs):
    startoff = curroff
    for s in e:
        curroff = _text_and_standoffs(s, curroff, strings, standoffs)
        if s.tail is not None and s.tail != "":
            strings.append(s.tail)
            curroff += len(s.tail)
    return curroff

def preceding_space(pos, text, rewritten={}):
    while pos > 0:
        pos -= 1
        if pos not in rewritten: 
            # no rewrite, check normally
            return text[pos].isspace()           
        elif rewritten[pos] is not None:
            # refer to rewritten instead of original
            return rewritten[pos].isspace()
        else:
            # character deleted, ignore position
            pass
    # accept start of text
    return True

def following_space(pos, text, rewritten={}):
    while pos < len(text):
        if pos not in rewritten: 
            # no rewrite, check normally
            return text[pos].isspace()           
        elif rewritten[pos] is not None:
            # refer to rewritten instead of original
            return rewritten[pos].isspace()
        else:
            # character deleted, ignore position
            pass
        pos += 1
    # accept end of text
    return True

def preceding_linebreak(pos, text, rewritten={}):
    if pos >= len(text):
        return True    
    while pos > 0:
        pos -= 1
        c = rewritten.get(pos, text[pos])
        if c == "\n":
            return True
        elif c is not None and not c.isspace():
            return False
        else:
            # space or deleted, check further
            pass
    return True

def following_linebreak(pos, text, rewritten={}):
    while pos < len(text):
        c = rewritten.get(pos, text[pos])
        if c == "\n":
            return True
        elif c is not None and not c.isspace():
            return False
        else:
            # space or deleted, check further
            pass
        pos += 1
    return True

def index_in_parent(e, p):
    """
    Returns the index of the given element in its parent element e.
    """
    index = None
    for i in range(len(p)):
        if p[i] == e:
            index = i
            break
    assert i is not None, "index_in_parent: error: not parent and child"
    return i

def space_normalize(root, text=None, standoffs=None):
    """
    Eliminates multiple consequtive spaces and normalizes newlines
    (and other space) into regular space.
    """

    if text is None or standoffs is None:
        text, standoffs = text_and_standoffs(root)

    # TODO: this is crude and destructive; improve!
    for so in standoffs:
        e = so.element
        if e.text is not None and e.text != "":
            e.text = re.sub(r'\s+', ' ', e.text)
        if e.tail is not None and e.tail != "":
            e.tail = re.sub(r'\s+', ' ', e.tail)

def strip_elements(root, elements_to_strip=set(), text=None, standoffs=None):
    """
    Removes initial and terminal space from elements that either have
    surrounding space or belong to given set of elements to strip.
    """

    if text is None or standoffs is None:
        text, standoffs = text_and_standoffs(root)

    # during processing, keep note at which offsets spaces have
    # been eliminated.
    rewritten = {}
    
    for so in standoffs:
        e = so.element

        # don't remove expressly inserted space
        if e.tag == INSERTED_ELEMENT_TAG:
            continue
        
        # if the element contains initial space and is either marked
        # for space stripping or preceded by space, remove the initial
        # space.
        if ((e.text is not None and e.text != "" and e.text[0].isspace()) and
            (element_in_set(e, elements_to_strip) or 
             preceding_space(so.start, text, rewritten))):
            l = 0
            while l < len(e.text) and e.text[l].isspace():
                l += 1
            space, end = e.text[:l], e.text[l:]
            for i in range(l):
                assert so.start+i not in rewritten, "ERROR: dup remove at %d"  % (so.start+i)
                rewritten[so.start+i] = None
            e.text = end

        # element-final space is in e.text only if the element has no
        # children; if it does, the element-final space is found in
        # the tail of the last child.
        if len(e) == 0:
            if ((e.text is not None and e.text != "" and e.text[-1].isspace()) and
                (element_in_set(e, elements_to_strip) or 
                 following_space(so.end, text, rewritten))):
                l = 0
                while l < len(e.text) and e.text[-l-1].isspace():
                    l += 1
                start, space = e.text[:-l], e.text[-l:]
                for i in range(l):
                    o = so.end-i-1
                    assert o not in rewritten, "ERROR: dup remove"
                    rewritten[o] = None
                e.text = start
                    
        else:
            c = e[-1]
            if ((c.tail is not None and c.tail != "" and c.tail[-1].isspace()) and
                (element_in_set(e, elements_to_strip) or 
                 following_space(so.end, text, rewritten))):
                l = 0
                while l < len(c.tail) and c.tail[-l-1].isspace():
                    l += 1
                start, space = c.tail[:-l], c.tail[-l:]
                for i in range(l):
                    o = so.end-i-1
                    assert o not in rewritten, "ERROR: dup remove"
                    rewritten[o] = None
                c.tail = start

def trim_tails(root):
    """
    Trims the beginning of the tail of elements where it is preceded
    by space.
    """

    # This function is primarily necessary to cover the special case
    # of empty elements preceded and followed by space, as the
    # consecutive spaces created by such elements are not accessible
    # to the normal text content-stripping functionality.

    # work with standoffs for reference
    text, standoffs = text_and_standoffs(root)

    for so in standoffs:
        e = so.element

        if (e.tail is not None and e.tail != "" and e.tail[0].isspace() and
            preceding_space(so.end, text)):
            l = 0
            while l < len(e.tail) and e.tail[l].isspace():
                l += 1
            space, end = e.tail[:l], e.tail[l:]
            e.tail = end

def reduce_space(root, elements_to_strip=set()):
    """
    Performs space-removing normalizations.
    """

    # convert tree into text and standoffs for reference
    text, standoffs = text_and_standoffs(root)

    strip_elements(root, elements_to_strip, text, standoffs)

    trim_tails(root)

    space_normalize(root, text, standoffs)

def element_in_set(e, s):
    # strip namespaces for lookup
    if e.tag[0] == "{":
        tag = re.sub(r'\{.*?\}', '', e.tag)
    else:
        tag = e.tag
    return tag in s

def process(fn):
    global strip_element
    global options

    # ugly hack for testing: allow "-" for "/dev/stdin"
    if fn == "-":
        fn = "/dev/stdin"

    try:
        tree = ET.parse(fn)
    except:
        print >> sys.stderr, "Error parsing %s" % fn
        raise

    root = tree.getroot()

    ########## space normalization and stripping ##########

    reduce_space(root, strip_element)

    ########## additional space ##########

    # convert tree into text and standoffs
    text, standoffs = text_and_standoffs(root)

    # traverse standoffs and mark each position before which a space
    # or a newline should be assured. Values are (pos, early), where
    # pos is the offset where the break should be placed, and early
    # determines whether to select the first or the last among
    # multiple alternative tags before/after which to place the break.
    respace = {}
    for so in standoffs:
        e = so.element
        if element_in_set(e, newline_wrap_element):
            # "late" newline gets priority
            if not (so.start in respace and (respace[so.start][0] == "\n" and
                                             respace[so.start][1] == False)):
                respace[so.start] = ("\n", True)
            respace[so.end] = ("\n", False)
        elif element_in_set(e, space_wrap_element):
            # newlines and "late" get priority
            if not (so.start in respace and (respace[so.start][0] == "\n" or
                                             respace[so.start][1] == False)):
                respace[so.start] = (" ", True)
            if not (so.end in respace and respace[so.end][0] == "\n"):
                respace[so.end] = (" ", False)

    # next, filter respace to remove markers where the necessary space
    # is already present in the text.

    # to allow the filter to take into account linebreaks that will be
    # introduced as part of the processing, maintain rewritten
    # positions separately. (live updating of the text would be too
    # expensive computationally.) As the processing is left-to-right,
    # it's enough to use this for preceding positions and to mark
    # inserts as appearing "before" the place where space is required.
    rewritten = {}

    filtered = {}
    for pos in sorted(respace.keys()):
        if respace[pos][0] == " ":
            # unnecessary if initial, terminal, or preceded/followed
            # by a space
            if not (preceding_space(pos, text, rewritten) or
                    following_space(pos, text, rewritten)):
                filtered[pos] = respace[pos]
                rewritten[pos-1] = " "
        else:
            assert respace[pos][0] == "\n", "INTERNAL ERROR"
            # unnecessary if there's either a preceding or following
            # newline connected by space
            if not (preceding_linebreak(pos, text, rewritten) or 
                    following_linebreak(pos, text, rewritten)):
                filtered[pos] = respace[pos]                
                rewritten[pos-1] = "\n"
    respace = filtered

    # for reference, create a map from elements to their parents in the tree.
    parent_map = {}
    for parent in root.getiterator():
        for child in parent:
            parent_map[child] = parent

    # for reference, create a map from positions to standoffs ending
    # at each.
    # TODO: avoid indexing everything; this is only required for
    # standoffs ending at respace positions
    end_map = {}
    for so in standoffs:
        if so.end not in end_map:
            end_map[so.end] = []
        end_map[so.end].append(so)

    # traverse standoffs again, adding the new elements as needed.
    for so in standoffs:

        if so.start in respace and respace[so.start][1] == True:
            # Early space needed here. The current node can be assumed
            # to be the first to "discover" this, so it's appropriate
            # to add space before the current node.  We can further
            # assume the current node has a parent (adding space
            # before the root is meaningless), so we can add the space
            # node as the preceding child in the parent.

            e = so.element
            assert e in parent_map, "INTERNAL ERROR: add space before root?"
            p = parent_map[e]
            i = index_in_parent(e, p)

            rse = ET.Element(INSERTED_ELEMENT_TAG)
            rse.text = respace[so.start][0]
            p.insert(i, rse)

            # done, clear
            del respace[so.start]

        if so.end in respace and respace[so.end][1] == False:
            # Late space needed here. Add after the current node iff
            # it's the first of the nodes with the longest span ending
            # here (i.e. the outermost).
            maxlen = max([s.end-s.start for s in end_map[so.end]])
            if so.end-so.start != maxlen:
                continue
            longest = [s for s in end_map[so.end] if s.end-s.start == maxlen]
            if so != longest[0]:
                continue

            # OK to add.
            e = so.element
            assert e in parent_map, "INTERNAL ERROR: add space after root?"
            p = parent_map[e]
            i = index_in_parent(e, p)

            rse = ET.Element(INSERTED_ELEMENT_TAG)
            rse.text = respace[so.end][0]
            p.insert(i+1, rse)
            # need to relocate tail
            rse.tail = e.tail
            e.tail = ""

            # done, clear
            del respace[so.end]

    assert len(respace) == 0, "INTERNAL ERROR: failed to insert %s" % str(respace)

    # re-process to clear out consequtive space potentially introduced
    # in previous processing.
    strip_elements(root)
    trim_tails(root)

    # all done, output

    if options.stdout:
        tree.write(sys.stdout, encoding=OUTPUT_ENCODING)
        return True

    if options is not None and options.directory is not None:
        output_dir = options.directory
    else:
        output_dir = ""

    output_fn = os.path.join(output_dir, os.path.basename(fn))

    # TODO: better checking of path identify to protect against
    # clobbering.
    if output_fn == fn and not options.overwrite:
        print >> sys.stderr, 'respace: skipping output for %s: file would overwrite input (consider -d and -o options)' % fn
    else:
        # OK to write output_fn
        try:
            with open(output_fn, 'w') as of:
                tree.write(of, encoding=OUTPUT_ENCODING)
        except IOError, ex:
            print >> sys.stderr, 'respace: failed write: %s' % ex
                
    return True


def argparser():
    import argparse
    ap=argparse.ArgumentParser(description='Revise whitespace content of a PMC NXML file for text extraction.')
    ap.add_argument('-d', '--directory', default=None, metavar='DIR', help='output directory')
    ap.add_argument('-o', '--overwrite', default=False, action='store_true', help='allow output to overwrite input files')
    ap.add_argument('-s', '--stdout', default=False, action='store_true', help='output to stdout')
    ap.add_argument('file', nargs='+', help='input PubMed Central NXML file')
    return ap

def main(argv):
    global options

    options = argparser().parse_args(argv[1:])

    for fn in options.file:
        process(fn)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = sentencesplit
#!/usr/bin/env python

'''
Basic sentence splitter using brat segmentation to add newlines to
input text at likely sentence boundaries.
'''

import sys
from os.path import join as path_join
from os.path import dirname

# Assuming this script is found in the brat tools/ directory ...
from sys import path as sys_path
sys_path.append(path_join(dirname(__file__), '../server/src'))
# import brat sentence boundary generator
from ssplit import regex_sentence_boundary_gen

def _text_by_offsets_gen(text, offsets):
    for start, end in offsets:
        yield text[start:end]

def _normspace(s):
    import re
    return re.sub(r'\s', ' ', s)

def sentencebreaks_to_newlines(text):
    offsets = [o for o in regex_sentence_boundary_gen(text)]

    # break into sentences
    sentences = [s for s in _text_by_offsets_gen(text, offsets)]

    # join up, adding a newline for space where possible
    orig_parts = []
    new_parts = []

    sentnum = len(sentences)
    for i in range(sentnum):
        sent = sentences[i]
        orig_parts.append(sent)
        new_parts.append(sent)

        if i < sentnum-1:
            orig_parts.append(text[offsets[i][1]:offsets[i+1][0]])

            if (offsets[i][1] < offsets[i+1][0] and
                text[offsets[i][1]].isspace()):
                # intervening space; can add newline
                new_parts.append('\n'+text[offsets[i][1]+1:offsets[i+1][0]])
            else:
                new_parts.append(text[offsets[i][1]:offsets[i+1][0]])

    if len(offsets) and offsets[-1][1] < len(text):
        orig_parts.append(text[offsets[-1][1]:])
        new_parts.append(text[offsets[-1][1]:])

    # sanity check
    assert text == ''.join(orig_parts), "INTERNAL ERROR:\n    '%s'\nvs\n    '%s'" % (text, ''.join(orig_parts))

    splittext = ''.join(new_parts)

    # sanity
    assert len(text) == len(splittext), "INTERNAL ERROR"
    assert _normspace(text) == _normspace(splittext), "INTERNAL ERROR:\n    '%s'\nvs\n    '%s'" % (_normspace(text), _normspace(splittext))

    return splittext

def main(argv):
    while True:        
        text = sys.stdin.readline()
        if len(text) == 0:
            break
        sys.stdout.write(sentencebreaks_to_newlines(text))

if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = troubleshooting
#!/usr/bin/env python

'''
Attempt to diagnose common problems with the brat server by using HTTP.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2012-05-22
'''

from httplib import HTTPConnection, HTTPSConnection
from httplib import FORBIDDEN, MOVED_PERMANENTLY, NOT_FOUND, OK, TEMPORARY_REDIRECT
from sys import stderr
from urlparse import urlparse

### Constants
CONNECTION_BY_SCHEME = {
        'http': HTTPConnection,
        'https': HTTPSConnection,
        }
###

# Handle the horridness of Pythons httplib with redirects and moves
def _request_wrap(conn, method, url, body=None,
        headers=None):
    depth = 0
    curr_conn = conn
    curr_url = url
    while depth < 100: # 100 is a nice arbitary number
        curr_conn.request(method, curr_url, body,
                headers=headers if headers is not None else {})
        res = curr_conn.getresponse()
        if res.status not in (MOVED_PERMANENTLY, TEMPORARY_REDIRECT, ):
            return res
        res.read() # Empty the results
        res_headers = dict(res.getheaders())
        url_soup = urlparse(res_headers['location'])
        # Note: Could give us a "weird" scheme, but fuck it... can't be arsed
        # to think of all the crap http can potentially throw at us
        try:
            curr_conn = CONNECTION_BY_SCHEME[url_soup.scheme](url_soup.netloc)
        except KeyError:
            assert False, 'redirected to unknown scheme, dying'
        curr_url = url_soup.path
        depth += 1
    assert False, 'redirects and moves lead us astray, dying'

def main(args):
    # Old-style argument handling for portability
    if len(args) != 2:
        print >> stderr, 'Usage: %s url_to_brat_installation' % (args[0], )
        return -1
    brat_url = args[1]
    url_soup = urlparse(brat_url)

    if url_soup.scheme:
        try:
            Connection = CONNECTION_BY_SCHEME[url_soup.scheme.split(':')[0]]
        except KeyError:
            print >> stderr, ('ERROR: Unknown url scheme %s, try http or '
                    'https') % url_soup.scheme
            return -1
    else:
        # Not a well-formed url, we'll try to guess the user intention
        path_soup = url_soup.path.split('/')
        assumed_netloc = path_soup[0]
        assumed_path = '/' + '/'.join(path_soup[1:])
        print >> stderr, ('WARNING: No url scheme given, assuming scheme: '
                '"http", netloc: "%s" and path: "%s"'
                ) % (assumed_netloc, assumed_path, )
        url_soup = url_soup._replace(scheme='http', netloc=assumed_netloc,
                path=assumed_path)
        Connection = HTTPConnection

    # Check if we can load the base url
    conn = Connection(url_soup.netloc)
    res = _request_wrap(conn, 'HEAD', url_soup.path)
    if res.status != OK:
        print >> stderr, ('Unable to load "%s", please check the url.'
                ) % (brat_url, )
        print >> stderr, ('Does the url you provdide point to your brat '
                'installation?')
        return -1
    res.read() # Dump the data so that we can make another request

    # Do we have an ajax.cgi?
    ajax_cgi_path = url_soup.path + '/ajax.cgi'
    ajax_cgi_url = url_soup._replace(path=ajax_cgi_path).geturl()
    res = _request_wrap(conn, 'HEAD', ajax_cgi_path)
    if res.status == FORBIDDEN:
        print >> stderr, ('Received forbidden (403) when trying to access '
                '"%s"') % (ajax_cgi_url, )
        print ('Have you perhaps forgotten to enable execution of CGI in '
                ' your web server configuration?')
        return -1
    elif res.status != OK:
        print >> stderr, ('Unable to load "%s", please check your url. Does '
                'it point to your brat installation?') % (ajax_cgi_url, )
        return -1
    # Verify that we actually got json data back
    res_headers = dict(res.getheaders())
    try:
        content_type = res_headers['content-type']
    except KeyError:
        content_type = None

    if content_type != 'application/json':
        print >> stderr, ('Didn\'t receive json data when accessing "%s"%s.'
                ) % (ajax_cgi_url,
                        ', instead we received %s' % content_type
                            if content_type is not None else '')
        print >> stderr, ('Have you perhaps forgotten to add a handler for '
                'CGI in your web server configuration?')
        return -1

    # Doctor says, this seems okay
    print 'Congratulations! Your brat server appears to be ready to run.'
    print ('However, there is the possibility that there are further errors, '
            'but at least the server should be capable of communicating '
            'these errors to the client.')
    return 0

if __name__ == '__main__':
    from sys import argv
    exit(main(argv))

########NEW FILE########
__FILENAME__ = unmerge
#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

from __future__ import with_statement

'''
Split merged BioNLP Shared Task annotations into separate files.

Author:     Sampo Pyysalo
Version:    2011-02-24
'''

import sys
import re

try:
    import argparse
except ImportError:
    from os.path import basename
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(join_path(basename(__file__), '../server/lib'))
    import argparse

# if True, performs extra checking to assure that the input and output
# contain the same data. This costs a bit of execution time.
DEBUG=True

class ArgumentError(Exception):
    def __init__(self, s):
        self.errstr = s

    def __str__(self):
        return 'Argument error: %s' % (self.errstr)

class SyntaxError(Exception):
    def __init__(self, line, errstr=None, line_num=None):
        self.line = line
        self.errstr = errstr
        self.line_num = str(line_num) if line_num is not None else "(undefined)"

    def __str__(self):
        return 'Syntax error on line %s ("%s")%s' % (self.line_num, self.line, ": "+self.errstr if self.errstr is not None else "")

class ProcessingError(Exception):
    pass

class Annotation(object):
    # Special value to use as the type for comment annotations.
    COMMENT_TYPE = "<COMMENT>"

    _typere = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*)\b')

    @staticmethod
    def _parse_type(s):
        '''
        Attempts to parse the given line as a BioNLP ST - flavoured
        standoff annotation, returning its type.
        '''
        if not s or s[0].isspace():
            raise SyntaxError(s, "ID missing")
        if s[0].isalnum() or s[0] == '*':
            # Possible "standard" ID. Assume type can be found
            # in second TAB-separated field.
            fields = s.split("\t")
            if len(fields) < 2:
                raise SyntaxError(s, "No TAB in annotation")
            m = Annotation._typere.search(fields[1])
            if not m:
                raise SyntaxError(s, "Failed to parse type in \"%s\"" % fields[1])
            return m.group(1)
            
        elif s[0] == '#':
            # comment; any structure allowed. return special type
            return Annotation.COMMENT_TYPE
        else:
            raise SyntaxError(s, "Unrecognized ID")

    def __init__(self, s):
        self.ann_string = s
        self.type = Annotation._parse_type(s)

    def __str__(self):
        return self.ann_string

def argparser():
    ap=argparse.ArgumentParser(description="Split merged BioNLP ST annotations into separate files.")
    ap.add_argument("-a1", "--a1types", default="Protein", metavar="TYPE[,TYPE...]", help="Annotation types to place into .a1 file")
    ap.add_argument("-a2", "--a2types", default="[OTHER]", metavar="TYPE[,TYPE...]", help="Annotation types to place into .a2 file")
    ap.add_argument("-d", "--directory", default=None, metavar="DIR", help="Output directory")
    # TODO: don't clobber existing files
    #ap.add_argument("-f", "--force", default=False, action="store_true", help="Force generation even if output files exist")
    ap.add_argument("-s", "--skipempty", default=False, action="store_true", help="Skip output for empty split files")
    ap.add_argument("-i", "--idrewrite", default=False, action="store_true", help="Rewrite IDs following BioNLP ST conventions")
    ap.add_argument("files", nargs='+', help="Files in merged BioNLP ST-flavored standoff")
    return ap

def parse_annotations(annlines, fn="(unknown)"):
    annotations = []
    for ln, l in enumerate(annlines):
        if not l.strip():
            print >> sys.stderr, "Warning: ignoring empty line %d in %s" % (ln, fn)
            continue
        try:
            annotations.append(Annotation(l))
        except SyntaxError, e:
            raise SyntaxError(l, e.errstr, ln)
    return annotations

DEFAULT_TYPE = "<DEFAULT>"

def split_annotations(annotations, typemap):
    """
    Returns the given annotations split into N collections
    as specified by the given type mapping. Returns a dict
    of lists keyed by the type map keys, containing the
    annotations.
    """
    d = {}

    for a in annotations:
        if a.type in typemap:
            t = a.type
        elif DEFAULT_TYPE in typemap:
            t = DEFAULT_TYPE
        else:
            raise ArgumentError("Don't know where to place annotation of type '%s'" % a.type)
        s = typemap[t]

        if s not in d:
            d[s] = []
        d[s].append(a)
        
    return d

def type_mapping(arg):
    """
    Generates a mapping from types to filename suffixes
    based on the given arguments.
    """
    m = {}
    # just support .a1 and .a2 now
    for suff, typestr in (("a1", arg.a1types),
                          ("a2", arg.a2types)):
        for ts in typestr.split(","):
            # default arg
            t = ts if ts != "[OTHER]" else DEFAULT_TYPE
            if t in m:
                raise ArgumentError("Split for '%s' ambiguous (%s or %s); check arguments." % (ts, m[t], suff))
            m[t] = suff
    return m

def output_file_name(fn, directory, suff):
    import os.path

    dir, base = os.path.split(fn)
    root, ext = os.path.splitext(base)    

    if not directory:
        # default to directory of file
        directory = dir

    return os.path.join(directory, root+"."+suff)

def annotation_lines(annotations):
    return [str(a) for a in annotations]

def write_annotation_lines(fn, lines):
    with open(fn, 'wt') as f:
        for l in lines:
            f.write(l)

def read_annotation_lines(fn):
    with open(fn) as f:
        return f.readlines()

def verify_split(origlines, splitlines):
    orig = origlines[:]
    split = []
    for k in splitlines:
        split.extend(splitlines[k])

    orig.sort()
    split.sort()

    orig_only = []
    split_only = []
    oi, si = 0, 0
    while oi < len(orig) and si < len(split):
        if orig[oi] == split[si]:
            oi += 1
            si += 1
        elif orig[oi] < split[si]:
            orig_only.append(orig[oi])
            oi += 1
        else:
            assert split[si] < orig[si]
            split_only.append(split[si])
            si += 1
    while oi < len(orig):
        orig_only.append(orig[oi])
        oi += 1
    while si < len(split):
        split_only.append(split[si])
        si += 1

    difference_found = False
    for l in split_only:
        print >> sys.stderr, "Split error: split contains extra line '%s'" % l
        difference_found = True
    for l in orig_only:
        # allow blank lines to be removed
        if l.strip() == "":
            continue
        print >> sys.stderr, "Split error: split is missing line '%s'" % l
        difference_found = True

    if difference_found:
        raise ProcessingError

def process_file(fn, typemap, directory, mandatory):
    annlines = read_annotation_lines(fn)
    annotations = parse_annotations(annlines)

    splitann = split_annotations(annotations, typemap)

    # always write these, even if they will be empty
    for t in mandatory:
        splitann[t] = splitann.get(t, [])

    splitlines = {}
    for suff in splitann:
        splitlines[suff] = annotation_lines(splitann[suff])

    if DEBUG:
        verify_split(annlines, splitlines)

    for suff in splitann:
        ofn = output_file_name(fn, directory, suff)
        write_annotation_lines(ofn, splitlines[suff])

def main(argv=None):
    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    try:
        typemap = type_mapping(arg)
    except ArgumentError, e:
        print >> sys.stderr, e
        return 2

    if arg.skipempty: 
        mandatory_outputs = []
    else:
        mandatory_outputs = ["a1", "a2"]

    for fn in arg.files:
        try:
            process_file(fn, typemap, arg.directory, mandatory_outputs)
        except IOError, e:
            print >> sys.stderr, "Error: failed %s, skip processing (%s)" % (fn, e)            
        except SyntaxError, e:
            print >> sys.stderr, "Error: failed %s, skip processing (%s)" % (fn, e)            
        except:
            print >> sys.stderr, "Fatal: unexpected error processing %s" % fn
            raise

    return 0

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
