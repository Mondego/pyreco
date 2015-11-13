__FILENAME__ = completers
# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

import os
import sys
import subprocess

def _wrapcall(*args, **kargs):
    try:
        return subprocess.check_output(*args,**kargs).decode().splitlines()
    except AttributeError:
        return _wrapcall_2_6(*args, **kargs)
    except subprocess.CalledProcessError:
        return []

def _wrapcall_2_6(*args, **kargs):
    try:
        # no check_output in 2.6,
        if 'stdout' in kargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(
            stdout=subprocess.PIPE, *args, **kargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kargs.get("args")
            if cmd is None:
                cmd = args[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output.decode().splitlines()
    except subprocess.CalledProcessError:
        return []


class ChoicesCompleter(object):
    def __init__(self, choices=[]):
        self.choices = choices

    def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

def EnvironCompleter(prefix, **kwargs):
    return (v for v in os.environ if v.startswith(prefix))

class FilesCompleter(object):
    'File completer class, optionally takes a list of allowed extensions'
    def __init__(self,allowednames=(),directories=True):
        # Fix if someone passes in a string instead of a list
        if type(allowednames) is str:
            allowednames = [allowednames]

        self.allowednames = [x.lstrip('*').lstrip('.') for x in allowednames]
        self.directories = directories

    def __call__(self, prefix, **kwargs):
        completion = []
        if self.allowednames:
            if self.directories:
                files = _wrapcall(['bash','-c',
                    "compgen -A directory -- '{p}'".format(p=prefix)])
                completion += [ f + '/' for f in files]
            for x in self.allowednames:
                completion += _wrapcall(['bash', '-c',
                    "compgen -A file -X '!*.{0}' -- '{p}'".format(x,p=prefix)])
        else:
            completion += _wrapcall(['bash', '-c',
                "compgen -A file -- '{p}'".format(p=prefix)])

            anticomp = _wrapcall(['bash', '-c',
                "compgen -A directory -- '{p}'".format(p=prefix)])

            completion = list( set(completion) - set(anticomp))

            if self.directories:
                completion += [f + '/' for f in anticomp]
        return completion


########NEW FILE########
__FILENAME__ = my_argparse
# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

from argparse import ArgumentParser, ArgumentError, SUPPRESS
from argparse import OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, REMAINDER, PARSER
from argparse import _get_action_name, _

def action_is_satisfied(action):
    ''' Returns False if the parse would raise an error if no more arguments are given to this action, True otherwise.
    '''
    num_consumed_args = getattr(action, 'num_consumed_args', 0)

    if action.nargs == ONE_OR_MORE and num_consumed_args < 1:
        return False
    else:
        if action.nargs is None:
            action.nargs = 1
        try:
            return num_consumed_args == action.nargs
        except:
            return True

def action_is_open(action):
    ''' Returns True if action could consume more arguments (i.e., its pattern is open).
    '''
    return action.nargs in [ZERO_OR_MORE, ONE_OR_MORE, PARSER, REMAINDER]

class IntrospectiveArgumentParser(ArgumentParser):
    ''' The following is a verbatim copy of ArgumentParser._parse_known_args (Python 2.7.3),
    except for the lines that contain the string "Added by argcomplete".
    '''
    def _parse_known_args(self, arg_strings, namespace):
        self.active_actions = [] # Added by argcomplete
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
                    self.active_actions = [action] # Added by argcomplete
                    action.num_consumed_args = 0 # Added by argcomplete
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]

                    # Begin added by argcomplete
                    # If the pattern is not open (e.g. no + at the end), remove the action from active actions (since
                    # it wouldn't be able to consume any more args)
                    if not action_is_open(action):
                        self.active_actions.remove(action)
                    elif action.nargs == OPTIONAL and len(args) == 1:
                        self.active_actions.remove(action)
                    action.num_consumed_args = len(args)
                    # End added by argcomplete

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
                if arg_count > 0: # Added by argcomplete
                    self.active_actions = [action] # Added by argcomplete
                else: # Added by argcomplete
                    self.active_actions.append(action) # Added by argcomplete
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                action.num_consumed_args = len(args)
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
            self.active_actions.append(positionals[0]) # Added by argcomplete
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

########NEW FILE########
__FILENAME__ = my_shlex
# -*- coding: utf-8 -*-

# This copy of shlex.py is distributed with argcomplete.
# It incorporates changes proposed in http://bugs.python.org/issue1521950 and changes to allow it to match Unicode
# word characters.

"""A lexical analyzer class for simple shell-like syntaxes."""

# Module and documentation by Eric S. Raymond, 21 Dec 1998
# Input stacking and error message cleanup added by ESR, March 2000
# push_source() and pop_source() made explicit by ESR, January 2001.
# Posix compliance, split(), string arguments, and
# iterator interface by Gustavo Niemeyer, April 2003.
# changes to tokenize more like Posix shells by Vinay Sajip, January 2012.

import os.path, sys, re
from collections import deque

# Note: cStringIO is not compatible with Unicode
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    basestring
except NameError:
    basestring = str

__all__ = ["shlex", "split"]

class UnicodeWordchars:
    ''' A replacement for shlex.wordchars that also matches (__contains__) any Unicode wordchars.
    '''
    def __init__(self, wordchars):
        self.wordchars = wordchars
        self.uw_regex = re.compile('\w', flags=re.UNICODE)

    def __contains__(self, c):
        return c in self.wordchars or self.uw_regex.match(c)

class shlex:
    "A lexical analyzer class for simple shell-like syntaxes."
    def __init__(self, instream=None, infile=None, posix=False, punctuation_chars=False):
        if isinstance(instream, basestring):
            instream = StringIO(instream)
        if instream is not None:
            self.instream = instream
            self.infile = infile
        else:
            self.instream = sys.stdin
            self.infile = None
        self.posix = posix
        if posix:
            self.eof = None
        else:
            self.eof = ''
        self.commenters = '#'
        self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        self.whitespace = ' \t\r\n'
        self.whitespace_split = False
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        self.state = ' '
        self.pushback = deque()
        self.lineno = 1
        self.debug = 0
        self.token = ''
        self.filestack = deque()
        self.source = None

        if not punctuation_chars:
            punctuation_chars = ''
        elif punctuation_chars is True:
            punctuation_chars = '();<>|&'
        self.punctuation_chars = punctuation_chars
        if punctuation_chars:
            # _pushback_chars is a push back queue used by lookahead logic
            self._pushback_chars = deque()
            # these chars added because allowed in file names, args, wildcards
            self.wordchars += '~-./*?=:@'
            #remove any punctuation chars from wordchars
            self.wordchars = ''.join(c for c in self.wordchars if c not in
                                     self.punctuation_chars)
            for c in punctuation_chars:
                if c in self.wordchars:
                    self.wordchars.remove(c)

        if self.posix:
            self.wordchars = UnicodeWordchars(self.wordchars)

        self.first_colon_pos = None

    def push_token(self, tok):
        "Push a token onto the stack popped by the get_token method"
        self.pushback.appendleft(tok)

    def push_source(self, newstream, newfile=None):
        "Push an input source onto the lexer's input source stack."
        if isinstance(newstream, basestring):
            newstream = StringIO(newstream)
        self.filestack.appendleft((self.infile, self.instream, self.lineno))
        self.infile = newfile
        self.instream = newstream
        self.lineno = 1

    def pop_source(self):
        "Pop the input source stack."
        self.instream.close()
        (self.infile, self.instream, self.lineno) = self.filestack.popleft()
        self.state = ' '

    def get_token(self):
        "Get a token from the input stream (or from stack if it's nonempty)"
        if self.pushback:
            tok = self.pushback.popleft()
            return tok
        # No pushback.  Get a token.
        raw = self.read_token()
        # Handle inclusions
        if self.source is not None:
            while raw == self.source:
                spec = self.sourcehook(self.read_token())
                if spec:
                    (newfile, newstream) = spec
                    self.push_source(newstream, newfile)
                raw = self.get_token()
        # Maybe we got EOF instead?
        while raw == self.eof:
            if not self.filestack:
                return self.eof
            else:
                self.pop_source()
                raw = self.get_token()
        # Neither inclusion nor EOF
        return raw

    def read_token(self):
        quoted = False
        escapedstate = ' '
        while True:
            if self.punctuation_chars and self._pushback_chars:
                nextchar = self._pushback_chars.pop()
            else:
                nextchar = self.instream.read(1)
            if nextchar == '\n':
                self.lineno += 1
            if self.state is None:
                self.token = ''        # past end of file
                break
            elif self.state == ' ':
                if not nextchar:
                    self.state = None  # end of file
                    break
                elif nextchar in self.whitespace:
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno += 1
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.wordchars:
                    self.token = nextchar
                    self.state = 'a'
                elif nextchar in self.punctuation_chars:
                    self.token = nextchar
                    self.state = 'c'
                elif nextchar in self.quotes:
                    if not self.posix:
                        self.token = nextchar
                    self.state = nextchar
                elif self.whitespace_split:
                    self.token = nextchar
                    self.state = 'a'
                else:
                    self.token = nextchar
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
            elif self.state in self.quotes:
                quoted = True
                if not nextchar:      # end of file
                    # XXX what error should be raised here?
                    raise ValueError("No closing quotation")
                if nextchar == self.state:
                    if not self.posix:
                        self.token += nextchar
                        self.state = ' '
                        break
                    else:
                        self.state = 'a'
                elif (self.posix and nextchar in self.escape and self.state
                      in self.escapedquotes):
                    escapedstate = self.state
                    self.state = nextchar
                else:
                    self.token += nextchar
            elif self.state in self.escape:
                if not nextchar:      # end of file
                    # XXX what error should be raised here?
                    raise ValueError("No escaped character")
                # In posix shells, only the quote itself or the escape
                # character may be escaped within quotes.
                if (escapedstate in self.quotes and
                        nextchar != self.state and nextchar != escapedstate):
                    self.token += self.state
                self.token += nextchar
                self.state = escapedstate
            elif self.state in ('a', 'c'):
                if not nextchar:
                    self.state = None   # end of file
                    break
                elif nextchar in self.whitespace:
                    self.state = ' '
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno += 1
                    if self.posix:
                        self.state = ' '
                        if self.token or (self.posix and quoted):
                            break   # emit current token
                        else:
                            continue
                elif self.posix and nextchar in self.quotes:
                    self.state = nextchar
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif self.state == 'c':
                    if nextchar in self.punctuation_chars:
                        self.token += nextchar
                    else:
                        if nextchar not in self.whitespace:
                            self._pushback_chars.append(nextchar)
                        self.state = ' '
                        break
                elif (nextchar in self.wordchars or nextchar in self.quotes
                      or self.whitespace_split):
                    self.token += nextchar
                    if nextchar == ':':
                        self.first_colon_pos = len(self.token)-1
                else:
                    if self.punctuation_chars:
                        self._pushback_chars.append(nextchar)
                    else:
                        self.pushback.appendleft(nextchar)
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    else:
                        continue
        result = self.token
        self.token = ''
        if self.posix and not quoted and result == '':
            result = None
        return result

    def sourcehook(self, newfile):
        "Hook called on a filename to be sourced."
        if newfile[0] == '"':
            newfile = newfile[1:-1]
        # This implements cpp-like semantics for relative-path inclusion.
        if isinstance(self.infile, basestring) and not os.path.isabs(newfile):
            newfile = os.path.join(os.path.dirname(self.infile), newfile)
        return (newfile, open(newfile, "r"))

    def error_leader(self, infile=None, lineno=None):
        "Emit a C-compiler-like, Emacs-friendly error-message leader."
        if infile is None:
            infile = self.infile
        if lineno is None:
            lineno = self.lineno
        return "\"%s\", line %d: " % (infile, lineno)

    def __iter__(self):
        return self

    def next(self):
        token = self.get_token()
        if token == self.eof:
            raise StopIteration
        return token

def split(s, comments=False, posix=True, punctuation_chars=False):
    lex = shlex(s, posix=posix, punctuation_chars=punctuation_chars)
    lex.whitespace_split = True
    if not comments:
        lex.commenters = ''
    return list(lex)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# argcomplete documentation build configuration file, created by
# sphinx-quickstart on Tue Nov 20 21:14:36 2012.
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
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'argcomplete'
copyright = u'2012, Andrey Kislyuk'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
#version = '0.1.3'
# The full version, including alpha/beta/rc tags.
#release = '0.1.3'

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
html_static_path = ['_static']

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
htmlhelp_basename = 'argcompletedoc'


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
  ('index', 'argcomplete.tex', u'argcomplete Documentation',
   u'Andrey Kislyuk', 'manual'),
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
    ('index', 'argcomplete', u'argcomplete Documentation',
     [u'Andrey Kislyuk'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'argcomplete', u'argcomplete Documentation',
   u'Andrey Kislyuk', 'argcomplete', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = describe_github_user
#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
import argcomplete, argparse, requests, pprint

def github_org_members(prefix, parsed_args, **kwargs):
    resource = "https://api.github.com/orgs/{org}/members".format(org=parsed_args.organization)
    return (member['login'] for member in requests.get(resource).json() if member['login'].startswith(prefix))

parser = argparse.ArgumentParser()
parser.add_argument("--organization", help="GitHub organization")
parser.add_argument("--member", help="GitHub member").completer = github_org_members

argcomplete.autocomplete(parser)
args = parser.parse_args()

pprint.pprint(requests.get("https://api.github.com/users/{m}".format(m=args.member)).json())

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, shutil

python2 = True if sys.version_info < (3, 0) else False

if python2:
    # Try to reset default encoding to a sane value
    # Note: This is incompatible with pypy
    import platform
    if platform.python_implementation() != "PyPy":
        try:
            import locale
            reload(sys).setdefaultencoding(locale.getdefaultlocale()[1])
        except:
            pass

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from tempfile import TemporaryFile, mkdtemp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from argcomplete import *

IFS = '\013'

class TempDir(object):
    """temporary directory for testing FilesCompletion

    usage:
    with TempDir(prefix="temp_fc") as t:
        print('tempdir', t)
        # you are not chdir-ed to the temporary directory
        # everything created here will be deleted
    """
    def __init__(self, suffix="", prefix='tmpdir', dir=None):
        self.tmp_dir = mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self.old_dir = os.getcwd()

    def __enter__(self):
        os.chdir(self.tmp_dir)
        return self.tmp_dir

    def __exit__(self, *err):
        os.chdir(self.old_dir)
        shutil.rmtree(self.tmp_dir)


class TestArgcomplete(unittest.TestCase):
    def setUp(self):
        os.environ['_ARGCOMPLETE'] = "yes"
        os.environ['_ARC_DEBUG'] = "yes"
        os.environ['IFS'] = IFS

    def tearDown(self):
        pass

    def run_completer(self, parser, command, point=None, **kwargs):
        if python2:
            command = unicode(command)
        if point is None:
            if python2:
                point = str(len(command))
            else:
                # Adjust point for wide chars
                point = str(len(command.encode(locale.getpreferredencoding())))
        with TemporaryFile() as t:
            #os.environ['COMP_LINE'] = command.encode(locale.getpreferredencoding())
            os.environ['COMP_LINE'] = command
            os.environ['COMP_POINT'] = point
            os.environ['_ARGCOMPLETE_COMP_WORDBREAKS'] = '"\'@><=;|&(:'
            self.assertRaises(SystemExit, autocomplete, parser, output_stream=t,
                              exit_method=sys.exit, **kwargs)
            t.seek(0)
            return t.read().decode(locale.getpreferredencoding()).split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        assert(set(completions) == set(['-h', '--help', '--foo', '--bar']))

    def test_choices(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('--ship', choices=['submarine', 'speedboat'])
            return parser

        expected_outputs = (("prog ", ['--ship', '-h', '--help']),
            ("prog --shi", ['--ship']),
            ("prog --ship ", ['submarine', 'speedboat']),
            ("prog --ship s", ['submarine', 'speedboat']),
            ("prog --ship su", ['submarine']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_action_activation(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        expected_outputs = (("prog ", ['bus', 'car', '-h', '--help']),
            ("prog bu", ['bus']),
            ("prog bus ", ['apple', 'orange', '-h', '--help']),
            ("prog bus appl", ['apple']),
            ("prog bus apple ", ['-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_action_activation_with_subparser(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(title='subcommands', metavar='subcommand')
            subparser_build = subparsers.add_parser('build')
            subparser_build.add_argument('var', choices=['bus', 'car'])
            subparser_build.add_argument('--profile', nargs=1)
            return parser

        expected_outputs = (("prog ", ['build', '-h', '--help']),
            ("prog bu", ['build']),
            ("prog build ", ['bus', 'car', '--profile', '-h', '--help']),
            ("prog build ca", ['car']),
            ("prog build car ", ['--profile', '-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_completers(self):
        def c_url(prefix, parsed_args, **kwargs):
            return [ "http://url1", "http://url2" ]

        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument("--url").completer = c_url
            parser.add_argument("--email", nargs=3, choices=['a@b.c', 'a@b.d', 'ab@c.d', 'bcd@e.f', 'bce@f.g'])
            return parser

        expected_outputs = (("prog --url ", ['http\\://url1', 'http\\://url2']),
            ("prog --url \"", ['"http://url1', '"http://url2']),
            ("prog --url \"http://url1\" --email ", ['a\\@b.c', 'a\\@b.d', 'ab\\@c.d', 'bcd\\@e.f', 'bce\\@f.g']),
            ("prog --url \"http://url1\" --email a", ['a\\@b.c', 'a\\@b.d', 'ab\\@c.d']),
            ("prog --url \"http://url1\" --email \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"ab@c.d\" ", ['--url', '--email', '-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_file_completion(self):
        # setup and teardown should probably be in class
        from argcomplete.completers import FilesCompleter
        with TempDir(prefix='test_dir_fc', dir='.') as t:
            fc = FilesCompleter()
            os.makedirs(os.path.join('abcdef', 'klm'))
            self.assertEqual(fc('a'), ['abcdef/'])
            os.makedirs(os.path.join('abcaha', 'klm'))
            with open('abcxyz', 'w') as fp:
                fp.write('test')
            self.assertEqual(set(fc('a')), set(['abcdef/', 'abcaha/', 'abcxyz']))

    def test_subparsers(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument("--age", type=int)
            sub = parser.add_subparsers()
            eggs = sub.add_parser("eggs")
            eggs.add_argument("type", choices=['on a boat', 'with a goat', 'in the rain', 'on a train'])
            spam = sub.add_parser("spam")
            spam.add_argument("type", choices=['ham', 'iberico'])
            return parser

        expected_outputs = (("prog ", ['--help', 'eggs', '-h', 'spam', '--age']),
            ("prog --age 1 eggs", ['eggs']),
            ("prog --age 2 eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs \"on a", ['\"on a train', '\"on a boat']),
            ("prog eggs on\\ a", ['on a train', 'on a boat']),
            ("prog spam ", ['iberico', 'ham', '--help', '-h']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=['-h'])), set(output) - set(['-h']))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=['-h', '--help'])),
                             set(output) - set(['-h', '--help']))

    @unittest.skipIf(python2 and sys.getdefaultencoding() != locale.getdefaultlocale()[1],
        "Skip for python 2 due to its text encoding deficiencies")
    def test_non_ascii(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument(u'--книга', choices=[u'Трудно быть богом',
                                                     u'Парень из преисподней',
                                                     u'Понедельник начинается в субботу'])
            return parser

        expected_outputs = (("prog ", [u'--книга', '-h', '--help']),
            (u"prog --книга ", [u'Трудно быть богом', u'Парень из преисподней', u'Понедельник начинается в субботу']),
            (u"prog --книга П", [u'Парень из преисподней', u'Понедельник начинается в субботу']),
            (u"prog --книга Пу", ['']),
            )

        for cmd, output in expected_outputs:
            if python2:
                output = [o.decode(locale.getpreferredencoding()) for o in output]
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_custom_validator(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        expected_outputs = (("prog ", ['-h', '--help']),
            ("prog bu", ['']),
            ("prog bus ", ['-h', '--help']),
            ("prog bus appl", ['']),
            ("prog bus apple ", ['-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=lambda x,y: False) ), set(output))

    def test_different_validators(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        validators = (
                lambda x,y: False,
                lambda x,y: True,
                lambda x,y: x.startswith(y),
        )

        expected_outputs = (("prog ", ['-h', '--help'], validators[0]),
            ("prog ", ['bus', 'car', '-h', '--help'], validators[1]),
            ("prog bu", ['bus'], validators[1]),
            ("prog bus ", ['apple', 'orange', '-h', '--help'], validators[1]),
            ("prog bus appl", ['apple'], validators[2]),
            ("prog bus cappl", [''], validators[2]),
            ("prog bus pple ", ['-h', '--help'], validators[2]),
            )

        for cmd, output, validator in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=validator) ), set(output))
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
