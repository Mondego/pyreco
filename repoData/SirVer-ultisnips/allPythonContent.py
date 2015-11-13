__FILENAME__ = compatibility
#!/usr/bin/env python
# encoding: utf-8

"""
This file contains compatibility code to stay compatible with
as many python versions as possible.
"""

import sys

import vim  # pylint:disable=import-error

if sys.version_info >= (3, 0):
    def _vim_dec(string):
        """Decode 'string' using &encoding."""
        # We don't have the luxury here of failing, everything
        # falls apart if we don't return a bytearray from the
        # passed in string
        return string.decode(vim.eval("&encoding"), "replace")

    def _vim_enc(bytearray):
        """Encode 'string' using &encoding."""
        # We don't have the luxury here of failing, everything
        # falls apart if we don't return a string from the passed
        # in bytearray
        return bytearray.encode(vim.eval("&encoding"), "replace")

    def open_ascii_file(filename, mode):
        """Opens a file in "r" mode."""
        return open(filename, mode, encoding="utf-8")

    def col2byte(line, col):
        """
        Convert a valid column index into a byte index inside
        of vims buffer.
        """
        # We pad the line so that selecting the +1 st column still works.
        pre_chars = (vim.current.buffer[line-1] + "  ")[:col]
        return len(_vim_enc(pre_chars))

    def byte2col(line, nbyte):
        """
        Convert a column into a byteidx suitable for a mark or cursor
        position inside of vim
        """
        line = vim.current.buffer[line-1]
        raw_bytes = _vim_enc(line)[:nbyte]
        return len(_vim_dec(raw_bytes))

    def as_unicode(string):
        """Return 'string' as unicode instance."""
        if isinstance(string, bytes):
            return _vim_dec(string)
        return str(string)

    def as_vimencoding(string):
        """Return 'string' as Vim internal encoding."""
        return string
else:
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    def _vim_dec(string):
        """Decode 'string' using &encoding."""
        try:
            return string.decode(vim.eval("&encoding"))
        except UnicodeDecodeError:
            # At least we tried. There might be some problems down the road now
            return string

    def _vim_enc(string):
        """Encode 'string' using &encoding."""
        try:
            return string.encode(vim.eval("&encoding"))
        except UnicodeEncodeError:
            return string

    def open_ascii_file(filename, mode):
        """Opens a file in "r" mode."""
        return open(filename, mode)

    def col2byte(line, col):
        """
        Convert a valid column index into a byte index inside
        of vims buffer.
        """
        # We pad the line so that selecting the +1 st column still works.
        pre_chars = _vim_dec(vim.current.buffer[line-1] + "  ")[:col]
        return len(_vim_enc(pre_chars))

    def byte2col(line, nbyte):
        """
        Convert a column into a byteidx suitable for a mark or cursor
        position inside of vim
        """
        line = vim.current.buffer[line-1]
        if nbyte >= len(line): # This is beyond end of line
            return nbyte
        return len(_vim_dec(line[:nbyte]))

    def as_unicode(string):
        """Return 'string' as unicode instance."""
        if isinstance(string, str):
            return _vim_dec(string)
        return unicode(string)

    def as_vimencoding(string):
        """Return 'string' as unicode instance."""
        return _vim_enc(string)

########NEW FILE########
__FILENAME__ = debug
#!/usr/bin/env python
# encoding: utf-8

"""Convenience methods that help with debugging. They should never be used in
production code."""

import sys

from UltiSnips.compatibility import as_unicode

DUMP_FILENAME = "/tmp/file.txt" if not sys.platform.lower().startswith("win") \
        else "C:/windows/temp/ultisnips.txt"
with open(DUMP_FILENAME, "w"):
    pass # clears the file

def echo_to_hierarchy(text_object):
    """Outputs the given 'text_object' and its children hierarchically."""
    # pylint:disable=protected-access
    parent = text_object
    while parent._parent:
        parent = parent._parent

    def _do_print(text_object, indent=""):
        """prints recursively."""
        debug(indent + as_unicode(text_object))
        try:
            for child in text_object._children:
                _do_print(child, indent=indent + "  ")
        except AttributeError:
            pass
    _do_print(parent)

def debug(msg):
    """Dumb 'msg' into the debug file."""
    msg = as_unicode(msg)
    with open(DUMP_FILENAME, "ab") as dump_file:
        dump_file.write((msg + '\n').encode("utf-8"))

def print_stack():
    """Dump a stack trace into the debug file."""
    import traceback
    with open(DUMP_FILENAME, "ab") as dump_file:
        traceback.print_stack(file=dump_file)

########NEW FILE########
__FILENAME__ = indent_util
#!/usr/bin/env python
# encoding: utf-8

"""See module doc."""

from UltiSnips import _vim

class IndentUtil(object):
    """Utility class for dealing properly with indentation. """

    def __init__(self):
        self.reset()

    def reset(self):
        """ Gets the spacing properties from Vim. """
        self.shiftwidth = int(_vim.eval("&shiftwidth"))
        self._expandtab = (_vim.eval("&expandtab") == "1")
        self._tabstop = int(_vim.eval("&tabstop"))

    def ntabs_to_proper_indent(self, ntabs):
        """Convert 'ntabs' number of tabs to the proper indent prefix."""
        line_ind = ntabs * self.shiftwidth * " "
        line_ind = self.indent_to_spaces(line_ind)
        line_ind = self.spaces_to_indent(line_ind)
        return line_ind

    def indent_to_spaces(self, indent):
        """ Converts indentation to spaces respecting Vim settings. """
        indent = indent.expandtabs(self._tabstop)
        right = (len(indent) - len(indent.rstrip(" "))) * " "
        indent = indent.replace(" ", "")
        indent = indent.replace('\t', " " * self._tabstop)
        return indent + right

    def spaces_to_indent(self, indent):
        """ Converts spaces to proper indentation respecting Vim settings """
        if not self._expandtab:
            indent = indent.replace(" " * self._tabstop, '\t')
        return indent

########NEW FILE########
__FILENAME__ = position
#!/usr/bin/env python
# encoding: utf-8

"""Represents a Position in a text file: (0 based line index, 0 based column
index) and provides methods for moving them around."""

class Position(object):
    """See module docstring."""

    def __init__(self, line, col):
        self.line = line
        self.col = col

    def move(self, pivot, delta):
        """'pivot' is the position of the first changed character, 'delta' is
        how text after it moved"""
        if self < pivot:
            return
        if delta.line == 0:
            if self.line == pivot.line:
                self.col += delta.col
        elif delta.line > 0:
            if self.line == pivot.line:
                self.col += delta.col - pivot.col
            self.line += delta.line
        else:
            self.line += delta.line
            if self.line == pivot.line:
                self.col += - delta.col + pivot.col

    def delta(self, pos):
        """Returns the difference that the cursor must move to come from 'pos'
        to us."""
        assert isinstance(pos, Position)
        if self.line == pos.line:
            return Position(0, self.col - pos.col)
        else:
            if self > pos:
                return Position(self.line - pos.line, self.col)
            else:
                return Position(self.line - pos.line, pos.col)
        return Position(self.line - pos.line, self.col - pos.col)

    def __add__(self, pos):
        assert isinstance(pos, Position)
        return Position(self.line + pos.line, self.col + pos.col)

    def __sub__(self, pos):
        assert isinstance(pos, Position)
        return Position(self.line - pos.line, self.col - pos.col)

    def __eq__(self, other):
        return (self.line, self.col) == (other.line, other.col)

    def __ne__(self, other):
        return (self.line, self.col) != (other.line, other.col)

    def __lt__(self, other):
        return (self.line, self.col) < (other.line, other.col)

    def __le__(self, other):
        return (self.line, self.col) <= (other.line, other.col)

    def __repr__(self):
        return "(%i,%i)" % (self.line, self.col)

########NEW FILE########
__FILENAME__ = snipmate
#!/usr/bin/env python
# encoding: utf-8

"""A snipMate snippet after parsing."""

from UltiSnips.snippet.definition._base import SnippetDefinition
from UltiSnips.snippet.parsing.snipmate import parse_and_instantiate

class SnipMateSnippetDefinition(SnippetDefinition):
    """See module doc."""

    SNIPMATE_SNIPPET_PRIORITY = -1000

    def __init__(self, trigger, value, description, location):
        SnippetDefinition.__init__(self, self.SNIPMATE_SNIPPET_PRIORITY,
                trigger, value, description, "", {}, location)

    def instantiate(self, snippet_instance, initial_text, indent):
        parse_and_instantiate(snippet_instance, initial_text, indent)

########NEW FILE########
__FILENAME__ = ultisnips
#!/usr/bin/env python
# encoding: utf-8

"""A UltiSnips snippet after parsing."""

from UltiSnips.snippet.definition._base import SnippetDefinition
from UltiSnips.snippet.parsing.ultisnips import parse_and_instantiate

class UltiSnipsSnippetDefinition(SnippetDefinition):
    """See module doc."""

    def instantiate(self, snippet_instance, initial_text, indent):
        return parse_and_instantiate(snippet_instance, initial_text, indent)

########NEW FILE########
__FILENAME__ = _base
#!/usr/bin/env python
# encoding: utf-8

"""Snippet representation after parsing."""

import re

from UltiSnips import _vim
from UltiSnips.compatibility import as_unicode
from UltiSnips.indent_util import IndentUtil
from UltiSnips.text import escape
from UltiSnips.text_objects import SnippetInstance

def _words_for_line(trigger, before, num_words=None):
    """ Gets the final 'num_words' words from 'before'.
    If num_words is None, then use the number of words in
    'trigger'.
    """
    if not len(before):
        return ''

    if num_words is None:
        num_words = len(trigger.split())

    word_list = before.split()
    if len(word_list) <= num_words:
        return before.strip()
    else:
        before_words = before
        for i in range(-1, -(num_words + 1), -1):
            left = before_words.rfind(word_list[i])
            before_words = before_words[:left]
        return before[len(before_words):].strip()

class SnippetDefinition(object):
    """Represents a snippet as parsed from a file."""

    _INDENT = re.compile(r"^[ \t]*")
    _TABS = re.compile(r"^\t*")

    def __init__(self, priority, trigger, value, description,
            options, globals, location):
        self._priority = priority
        self._trigger = as_unicode(trigger)
        self._value = as_unicode(value)
        self._description = as_unicode(description)
        self._opts = options
        self._matched = ""
        self._last_re = None
        self._globals = globals
        self._location = location

        # Make sure that we actually match our trigger in case we are
        # immediately expanded.
        self.matches(self._trigger)

    def __repr__(self):
        return "_SnippetDefinition(%r,%s,%s,%s)" % (
                self._priority, self._trigger, self._description, self._opts)

    def _re_match(self, trigger):
        """ Test if a the current regex trigger matches
        `trigger`. If so, set _last_re and _matched.
        """
        for match in re.finditer(self._trigger, trigger):
            if match.end() != len(trigger):
                continue
            else:
                self._matched = trigger[match.start():match.end()]

            self._last_re = match
            return match
        return False

    def has_option(self, opt):
        """ Check if the named option is set """
        return opt in self._opts

    @property
    def description(self):
        """Descriptive text for this snippet."""
        return ("(%s) %s" % (self._trigger, self._description)).strip()

    @property
    def priority(self):
        """The snippets priority, which defines which snippet will be preferred
        over others with the same trigger."""
        return self._priority

    @property
    def trigger(self):
        """The trigger text for the snippet."""
        return self._trigger

    @property
    def matched(self):
        """The last text that matched this snippet in match() or
        could_match()."""
        return self._matched

    @property
    def location(self):
        """Where this snippet was defined."""
        return self._location

    def matches(self, trigger):
        """Returns True if this snippet matches 'trigger'."""
        # If user supplies both "w" and "i", it should perhaps be an
        # error, but if permitted it seems that "w" should take precedence
        # (since matching at word boundary and within a word == matching at word
        # boundary).
        self._matched = ""

        # Don't expand on whitespace
        if trigger and trigger.rstrip() != trigger:
            return False

        words = _words_for_line(self._trigger, trigger)

        if "r" in self._opts:
            match = self._re_match(trigger)
        elif "w" in self._opts:
            words_len = len(self._trigger)
            words_prefix = words[:-words_len]
            words_suffix = words[-words_len:]
            match = (words_suffix == self._trigger)
            if match and words_prefix:
                # Require a word boundary between prefix and suffix.
                boundary_chars = escape(words_prefix[-1:] + \
                        words_suffix[:1], r'\"')
                match = _vim.eval('"%s" =~# "\\\\v.<."' % boundary_chars) != '0'
        elif "i" in self._opts:
            match = words.endswith(self._trigger)
        else:
            match = (words == self._trigger)

        # By default, we match the whole trigger
        if match and not self._matched:
            self._matched = self._trigger

        # Ensure the match was on a word boundry if needed
        if "b" in self._opts and match:
            text_before = trigger.rstrip()[:-len(self._matched)]
            if text_before.strip(" \t") != '':
                self._matched = ""
                return False
        return match

    def could_match(self, trigger):
        """Return True if this snippet could match the (partial) 'trigger'."""
        self._matched = ""

        # List all on whitespace.
        if trigger and trigger[-1] in (" ", "\t"):
            trigger = ""
        if trigger and trigger.rstrip() is not trigger:
            return False

        words = _words_for_line(self._trigger, trigger)

        if "r" in self._opts:
            # Test for full match only
            match = self._re_match(trigger)
        elif "w" in self._opts:
            # Trim non-empty prefix up to word boundary, if present.
            qwords = escape(words, r'\"')
            words_suffix = _vim.eval(
                    'substitute("%s", "\\\\v^.+<(.+)", "\\\\1", "")' % qwords)
            match = self._trigger.startswith(words_suffix)
            self._matched = words_suffix

            # TODO: list_snippets() function cannot handle partial-trigger
            # matches yet, so for now fail if we trimmed the prefix.
            if words_suffix != words:
                match = False
        elif "i" in self._opts:
            # TODO: It is hard to define when a inword snippet could match,
            # therefore we check only for full-word trigger.
            match = self._trigger.startswith(words)
        else:
            match = self._trigger.startswith(words)

        # By default, we match the words from the trigger
        if match and not self._matched:
            self._matched = words

        # Ensure the match was on a word boundry if needed
        if "b" in self._opts and match:
            text_before = trigger.rstrip()[:-len(self._matched)]
            if text_before.strip(" \t") != '':
                self._matched = ""
                return False

        return match

    def instantiate(self, snippet_instance, initial_text, indent):
        """Parses the content of this snippet and brings the corresponding text
        objects alive inside of Vim."""
        raise NotImplementedError()

    def launch(self, text_before, visual_content, parent, start, end):
        """Launch this snippet, overwriting the text 'start' to 'end' and
        keeping the 'text_before' on the launch line. 'Parent' is the parent
        snippet instance if any."""
        indent = self._INDENT.match(text_before).group(0)
        lines = (self._value + "\n").splitlines()
        ind_util = IndentUtil()

        # Replace leading tabs in the snippet definition via proper indenting
        initial_text = []
        for line_num, line in enumerate(lines):
            if "t" in self._opts:
                tabs = 0
            else:
                tabs = len(self._TABS.match(line).group(0))
            line_ind = ind_util.ntabs_to_proper_indent(tabs)
            if line_num != 0:
                line_ind = indent + line_ind

            initial_text.append(line_ind + line[tabs:])
        initial_text = '\n'.join(initial_text)

        snippet_instance = SnippetInstance(
                self, parent, initial_text, start, end, visual_content,
                last_re=self._last_re, globals=self._globals)
        self.instantiate(snippet_instance, initial_text, indent)

        snippet_instance.update_textobjects()
        return snippet_instance

########NEW FILE########
__FILENAME__ = snipmate
#!/usr/bin/env python
# encoding: utf-8

"""Parses a snipMate snippet definition and launches it into Vim."""

from UltiSnips.snippet.parsing._base import tokenize_snippet_text, finalize
from UltiSnips.snippet.parsing._lexer import EscapeCharToken, \
    VisualToken, TabStopToken, MirrorToken, ShellCodeToken
from UltiSnips.text_objects import EscapedChar, Mirror, VimLCode, Visual

_TOKEN_TO_TEXTOBJECT = {
    EscapeCharToken: EscapedChar,
    VisualToken: Visual,
    ShellCodeToken: VimLCode,  # `` is VimL in snipMate
}

__ALLOWED_TOKENS = [
    EscapeCharToken, VisualToken, TabStopToken, MirrorToken, ShellCodeToken
]

__ALLOWED_TOKENS_IN_TABSTOPS = [
    EscapeCharToken, VisualToken, MirrorToken, ShellCodeToken
]

def _create_mirrors(all_tokens, seen_ts):
    """Now that all tabstops are known, we can create mirrors."""
    for parent, token in all_tokens:
        if isinstance(token, MirrorToken):
            Mirror(parent, seen_ts[token.number], token)

def parse_and_instantiate(parent_to, text, indent):
    """Parses a snippet definition in snipMate format from 'text' assuming the
    current 'indent'. Will instantiate all the objects and link them as
    children to parent_to. Will also put the initial text into Vim."""
    all_tokens, seen_ts = tokenize_snippet_text(parent_to, text, indent,
            __ALLOWED_TOKENS, __ALLOWED_TOKENS_IN_TABSTOPS,
            _TOKEN_TO_TEXTOBJECT)
    _create_mirrors(all_tokens, seen_ts)
    finalize(all_tokens, seen_ts, parent_to)

########NEW FILE########
__FILENAME__ = ultisnips
#!/usr/bin/env python
# encoding: utf-8

"""Parses a UltiSnips snippet definition and launches it into Vim."""

from UltiSnips.snippet.parsing._base import tokenize_snippet_text, finalize
from UltiSnips.snippet.parsing._lexer import EscapeCharToken, \
    VisualToken, TransformationToken, TabStopToken, MirrorToken, \
    PythonCodeToken, VimLCodeToken, ShellCodeToken
from UltiSnips.text_objects import EscapedChar, Mirror, PythonCode, \
        ShellCode, TabStop, Transformation, VimLCode, Visual

_TOKEN_TO_TEXTOBJECT = {
    EscapeCharToken: EscapedChar,
    VisualToken: Visual,
    ShellCodeToken: ShellCode,
    PythonCodeToken: PythonCode,
    VimLCodeToken: VimLCode,
}

__ALLOWED_TOKENS = [
    EscapeCharToken, VisualToken, TransformationToken, TabStopToken,
    MirrorToken, PythonCodeToken, VimLCodeToken, ShellCodeToken
]

def _resolve_ambiguity(all_tokens, seen_ts):
    """$1 could be a Mirror or a TabStop. This figures this out."""
    for parent, token in all_tokens:
        if isinstance(token, MirrorToken):
            if token.number not in seen_ts:
                seen_ts[token.number] = TabStop(parent, token)
            else:
                Mirror(parent, seen_ts[token.number], token)

def _create_transformations(all_tokens, seen_ts):
    """Create the objects that need to know about tabstops."""
    for parent, token in all_tokens:
        if isinstance(token, TransformationToken):
            if token.number not in seen_ts:
                raise RuntimeError(
                    "Tabstop %i is not known but is used by a Transformation"
                    % token.number)
            Transformation(parent, seen_ts[token.number], token)


def parse_and_instantiate(parent_to, text, indent):
    """Parses a snippet definition in UltiSnips format from 'text' assuming the
    current 'indent'. Will instantiate all the objects and link them as
    children to parent_to. Will also put the initial text into Vim."""
    all_tokens, seen_ts = tokenize_snippet_text(parent_to, text, indent,
            __ALLOWED_TOKENS, __ALLOWED_TOKENS, _TOKEN_TO_TEXTOBJECT)
    _resolve_ambiguity(all_tokens, seen_ts)
    _create_transformations(all_tokens, seen_ts)
    finalize(all_tokens, seen_ts, parent_to)

########NEW FILE########
__FILENAME__ = _base
#!/usr/bin/env python
# encoding: utf-8

"""Common functionality of the snippet parsing codes."""

from UltiSnips.position import Position
from UltiSnips.snippet.parsing._lexer import tokenize, TabStopToken
from UltiSnips.text_objects import TabStop

def tokenize_snippet_text(snippet_instance, text, indent,
        allowed_tokens_in_text, allowed_tokens_in_tabstops,
        token_to_textobject):
    """Turns 'text' into a stream of tokens and creates the text objects from
    those tokens that are mentioned in 'token_to_textobject' assuming the
    current 'indent'. The 'allowed_tokens_in_text' define which tokens will be
    recognized in 'text' while 'allowed_tokens_in_tabstops' are the tokens that
    will be recognized in TabStop placeholder text."""
    seen_ts = {}
    all_tokens = []

    def _do_parse(parent, text, allowed_tokens):
        """Recursive function that actually creates the objects."""
        tokens = list(tokenize(text, indent, parent.start, allowed_tokens))
        for token in tokens:
            all_tokens.append((parent, token))
            if isinstance(token, TabStopToken):
                ts = TabStop(parent, token)
                seen_ts[token.number] = ts
                _do_parse(ts, token.initial_text,
                        allowed_tokens_in_tabstops)
            else:
                klass = token_to_textobject.get(token.__class__, None)
                if klass is not None:
                    klass(parent, token)
    _do_parse(snippet_instance, text, allowed_tokens_in_text)
    return all_tokens, seen_ts

def finalize(all_tokens, seen_ts, snippet_instance):
    """Adds a tabstop 0 if non is in 'seen_ts' and brings the text of the
    snippet instance into Vim."""
    if 0 not in seen_ts:
        mark = all_tokens[-1][1].end # Last token is always EndOfText
        m1 = Position(mark.line, mark.col)
        TabStop(snippet_instance, 0, mark, m1)
    snippet_instance.replace_initial_text()

########NEW FILE########
__FILENAME__ = _lexer
#!/usr/bin/env python
# encoding: utf-8

"""
Not really a lexer in the classical sense, but code to convert snippet
definitions into logical units called Tokens.
"""

import string
import re

from UltiSnips.compatibility import as_unicode
from UltiSnips.position import Position
from UltiSnips.text import unescape

class _TextIterator(object):
    """Helper class to make iterating over text easier."""

    def __init__(self, text, offset):
        self._text = as_unicode(text)
        self._line = offset.line
        self._col = offset.col

        self._idx = 0

    def __iter__(self):
        """Iterator interface."""
        return self

    def __next__(self):
        """Returns the next character."""
        if self._idx >= len(self._text):
            raise StopIteration

        rv = self._text[self._idx]
        if self._text[self._idx] in ('\n', '\r\n'):
            self._line += 1
            self._col = 0
        else:
            self._col += 1
        self._idx += 1
        return rv
    next = __next__  # for python2

    def peek(self, count=1):
        """Returns the next 'count' characters without advancing the stream."""
        if count > 1: # This might return '' if nothing is found
            return self._text[self._idx:self._idx + count]
        try:
            return self._text[self._idx]
        except IndexError:
            return None

    @property
    def pos(self):
        """Current position in the text."""
        return Position(self._line, self._col)

def _parse_number(stream):
    """
    Expects the stream to contain a number next, returns the number
    without consuming any more bytes
    """
    rv = ""
    while stream.peek() and stream.peek() in string.digits:
        rv += next(stream)

    return int(rv)

def _parse_till_closing_brace(stream):
    """
    Returns all chars till a non-escaped } is found. Other
    non escaped { are taken into account and skipped over.

    Will also consume the closing }, but not return it
    """
    rv = ""
    in_braces = 1
    while True:
        if EscapeCharToken.starts_here(stream, '{}'):
            rv += next(stream) + next(stream)
        else:
            char = next(stream)
            if char == '{':
                in_braces += 1
            elif char == '}':
                in_braces -= 1
            if in_braces == 0:
                break
            rv += char
    return rv

def _parse_till_unescaped_char(stream, chars):
    """
    Returns all chars till a non-escaped char is found.

    Will also consume the closing char, but and return it as second
    return value
    """
    rv = ""
    while True:
        escaped = False
        for char in chars:
            if EscapeCharToken.starts_here(stream, char):
                rv += next(stream) + next(stream)
                escaped = True
        if not escaped:
            char = next(stream)
            if char in chars:
                break
            rv += char
    return rv, char

class Token(object):
    """Represents a Token as parsed from a snippet definition."""

    def __init__(self, gen, indent):
        self.initial_text = as_unicode("")
        self.start = gen.pos
        self._parse(gen, indent)
        self.end = gen.pos

    def _parse(self, stream, indent):
        """Parses the token from 'stream' with the current 'indent'."""
        pass # Does nothing

class TabStopToken(Token):
    """${1:blub}"""
    CHECK = re.compile(r'^\${\d+[:}]')

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(10)) is not None

    def _parse(self, stream, indent):
        next(stream) # $
        next(stream) # {

        self.number = _parse_number(stream)

        if stream.peek() == ":":
            next(stream)
        self.initial_text = _parse_till_closing_brace(stream)

    def __repr__(self):
        return "TabStopToken(%r,%r,%r,%r)" % (
            self.start, self.end, self.number, self.initial_text
        )

class VisualToken(Token):
    """${VISUAL}"""
    CHECK = re.compile(r"^\${VISUAL[:}/]")

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(10)) is not None

    def _parse(self, stream, indent):
        for _ in range(8): # ${VISUAL
            next(stream)

        if stream.peek() == ":":
            next(stream)
        self.alternative_text, char = _parse_till_unescaped_char(stream, '/}')
        self.alternative_text = unescape(self.alternative_text)

        if char == '/': # Transformation going on
            try:
                self.search = _parse_till_unescaped_char(stream, '/')[0]
                self.replace = _parse_till_unescaped_char(stream, '/')[0]
                self.options = _parse_till_closing_brace(stream)
            except StopIteration:
                raise RuntimeError(
                    "Invalid ${VISUAL} transformation! Forgot to escape a '/'?")
        else:
            self.search = None
            self.replace = None
            self.options = None

    def __repr__(self):
        return "VisualToken(%r,%r)" % (
            self.start, self.end
        )

class TransformationToken(Token):
    """${1/match/replace/options}"""

    CHECK = re.compile(r'^\${\d+\/')

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(10)) is not None

    def _parse(self, stream, indent):
        next(stream) # $
        next(stream) # {

        self.number = _parse_number(stream)

        next(stream) # /

        self.search = _parse_till_unescaped_char(stream, '/')[0]
        self.replace = _parse_till_unescaped_char(stream, '/')[0]
        self.options = _parse_till_closing_brace(stream)

    def __repr__(self):
        return "TransformationToken(%r,%r,%r,%r,%r)" % (
            self.start, self.end, self.number, self.search, self.replace
        )

class MirrorToken(Token):
    """$1"""
    CHECK = re.compile(r'^\$\d+')

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(10)) is not None

    def _parse(self, stream, indent):
        next(stream) # $
        self.number = _parse_number(stream)

    def __repr__(self):
        return "MirrorToken(%r,%r,%r)" % (
            self.start, self.end, self.number
        )

class EscapeCharToken(Token):
    """\\n"""
    @classmethod
    def starts_here(cls, stream, chars=r'{}\$`'):
        """Returns true if this token starts at the current position in
        'stream'."""
        cs = stream.peek(2)
        if len(cs) == 2 and cs[0] == '\\' and cs[1] in chars:
            return True

    def _parse(self, stream, indent):
        next(stream) # \
        self.initial_text = next(stream)

    def __repr__(self):
        return "EscapeCharToken(%r,%r,%r)" % (
            self.start, self.end, self.initial_text
        )

class ShellCodeToken(Token):
    """`! echo "hi"`"""
    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return stream.peek(1) == '`'

    def _parse(self, stream, indent):
        next(stream) # `
        self.code = _parse_till_unescaped_char(stream, '`')[0]

    def __repr__(self):
        return "ShellCodeToken(%r,%r,%r)" % (
            self.start, self.end, self.code
        )

class PythonCodeToken(Token):
    """`!p snip.rv = "Hi"`"""
    CHECK = re.compile(r'^`!p\s')

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(4)) is not None

    def _parse(self, stream, indent):
        for _ in range(3):
            next(stream) # `!p
        if stream.peek() in '\t ':
            next(stream)

        code = _parse_till_unescaped_char(stream, '`')[0]

        # Strip the indent if any
        if len(indent):
            lines = code.splitlines()
            self.code = lines[0] + '\n'
            self.code += '\n'.join([l[len(indent):]
                        for l in lines[1:]])
        else:
            self.code = code
        self.indent = indent

    def __repr__(self):
        return "PythonCodeToken(%r,%r,%r)" % (
            self.start, self.end, self.code
        )

class VimLCodeToken(Token):
    """`!v g:hi`"""
    CHECK = re.compile(r'^`!v\s')

    @classmethod
    def starts_here(cls, stream):
        """Returns true if this token starts at the current position in
        'stream'."""
        return cls.CHECK.match(stream.peek(4)) is not None

    def _parse(self, stream, indent):
        for _ in range(4):
            next(stream) # `!v
        self.code = _parse_till_unescaped_char(stream, '`')[0]

    def __repr__(self):
        return "VimLCodeToken(%r,%r,%r)" % (
            self.start, self.end, self.code
        )

class EndOfTextToken(Token):
    """Appears at the end of the text."""
    def __repr__(self):
        return "EndOfText(%r)" % self.end

def tokenize(text, indent, offset, allowed_tokens):
    """Returns an iterator of tokens of 'text'['offset':] which is assumed to
    have 'indent' as the whitespace of the begging of the lines. Only
    'allowed_tokens' are considered to be valid tokens."""
    stream = _TextIterator(text, offset)
    try:
        while True:
            done_something = False
            for token in allowed_tokens:
                if token.starts_here(stream):
                    yield token(stream, indent)
                    done_something = True
                    break
            if not done_something:
                next(stream)
    except StopIteration:
        yield EndOfTextToken(stream, indent)

########NEW FILE########
__FILENAME__ = added
#!/usr/bin/env python
# encoding: utf-8

"""Handles manually added snippets UltiSnips_Manager.add_snippet()."""

from UltiSnips.snippet.source._base import SnippetSource

class AddedSnippetsSource(SnippetSource):
    """See module docstring."""

    def add_snippet(self, ft, snippet):
        """Adds the given 'snippet' for 'ft'."""
        self._snippets[ft].add_snippet(snippet)

########NEW FILE########
__FILENAME__ = snipmate
#!/usr/bin/env python
# encoding: utf-8

"""Parses snipMate files."""

import os
import glob

from UltiSnips import _vim
from UltiSnips.snippet.definition import SnipMateSnippetDefinition
from UltiSnips.snippet.source.file._base import SnippetFileSource
from UltiSnips.snippet.source.file._common import handle_extends
from UltiSnips.text import LineIterator, head_tail

def _splitall(path):
    """Split 'path' into all its components."""
    # From http://my.safaribooksonline.com/book/programming/
    # python/0596001673/files/pythoncook-chp-4-sect-16
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def snipmate_files_for(ft):
    """Returns all snipMate files we need to look at for 'ft'."""
    if ft == "all":
        ft = "_"
    patterns = [
            "%s.snippets" % ft,
            os.path.join(ft, "*.snippets"),
            os.path.join(ft, "*.snippet"),
            os.path.join(ft, "*/*.snippet"),
    ]
    ret = set()
    for rtp in _vim.eval("&runtimepath").split(','):
        path = os.path.realpath(os.path.expanduser(
                os.path.join(rtp, "snippets")))
        for pattern in patterns:
            for fn in glob.glob(os.path.join(path, pattern)):
                ret.add(fn)
    return ret

def _parse_snippet_file(content, full_filename):
    """Parses 'content' assuming it is a .snippet file and yields events."""
    filename = full_filename[:-len(".snippet")]  # strip extension
    segments = _splitall(filename)
    segments = segments[segments.index("snippets")+1:]
    assert len(segments) in (2, 3)

    trigger = segments[1]
    description = segments[2] if 2 < len(segments) else ""

    # Chomp \n if any.
    if content and content.endswith(os.linesep):
        content = content[:-len(os.linesep)]
    yield "snippet", (SnipMateSnippetDefinition(trigger, content,
        description, full_filename),)

def _parse_snippet(line, lines, filename):
    """Parse a snippet defintions."""
    start_line_index = lines.line_index
    trigger, description = head_tail(line[len("snippet"):].lstrip())
    content = ""
    while True:
        next_line = lines.peek()
        if next_line is None:
            break
        if next_line.strip() and not next_line.startswith('\t'):
            break
        line = next(lines)
        if line[0] == '\t':
            line = line[1:]
        content += line
    content = content[:-1]  # Chomp the last newline
    return "snippet", (SnipMateSnippetDefinition(
        trigger, content, description, "%s:%i" % (filename, start_line_index)),)

def _parse_snippets_file(data, filename):
    """Parse 'data' assuming it is a .snippets file. Yields events in the
    file."""
    lines = LineIterator(data)
    for line in lines:
        if not line.strip():
            continue

        head, tail = head_tail(line)
        if head == "extends":
            yield handle_extends(tail, lines.line_index)
        elif head in "snippet":
            snippet = _parse_snippet(line, lines, filename)
            if snippet is not None:
                yield snippet
        elif head and not head.startswith('#'):
            yield "error", ("Invalid line %r" % line.rstrip(), lines.line_index)

class SnipMateFileSource(SnippetFileSource):
    """Manages all snipMate snippet definitions found in rtp."""
    def _get_all_snippet_files_for(self, ft):
        return snipmate_files_for(ft)

    def _parse_snippet_file(self, filedata, filename):
        if filename.lower().endswith("snippet"):
            for event, data in _parse_snippet_file(filedata, filename):
                yield event, data
        else:
            for event, data in _parse_snippets_file(filedata, filename):
                yield event, data

########NEW FILE########
__FILENAME__ = ultisnips
#!/usr/bin/env python
# encoding: utf-8

"""Parsing of snippet files."""

from collections import defaultdict
import glob
import os

from UltiSnips import _vim
from UltiSnips.snippet.definition import UltiSnipsSnippetDefinition
from UltiSnips.snippet.source.file._base import SnippetFileSource
from UltiSnips.snippet.source.file._common import handle_extends
from UltiSnips.text import LineIterator, head_tail

def find_snippet_files(ft, directory):
    """Returns all matching snippet files for 'ft' in 'directory'."""
    patterns = ["%s.snippets", "%s_*.snippets", os.path.join("%s", "*")]
    ret = set()
    directory = os.path.expanduser(directory)
    for pattern in patterns:
        for fn in glob.glob(os.path.join(directory, pattern % ft)):
            ret.add(os.path.realpath(fn))
    return ret

def find_all_snippet_files(ft):
    """Returns all snippet files matching 'ft' in the given runtime path
    directory."""
    if _vim.eval("exists('b:UltiSnipsSnippetDirectories')") == "1":
        snippet_dirs = _vim.eval("b:UltiSnipsSnippetDirectories")
    else:
        snippet_dirs = _vim.eval("g:UltiSnipsSnippetDirectories")

    patterns = ["%s.snippets", "%s_*.snippets", os.path.join("%s", "*")]
    ret = set()
    for rtp in _vim.eval("&runtimepath").split(','):
        for snippet_dir in snippet_dirs:
            if snippet_dir == "snippets":
                raise RuntimeError(
                    "You have 'snippets' in UltiSnipsSnippetDirectories. This "
                    "directory is reserved for snipMate snippets. Use another "
                    "directory for UltiSnips snippets.")
            pth = os.path.realpath(os.path.expanduser(
                os.path.join(rtp, snippet_dir)))
            for pattern in patterns:
                for fn in glob.glob(os.path.join(pth, pattern % ft)):
                    ret.add(fn)
    return ret

def _handle_snippet_or_global(filename, line, lines, python_globals, priority):
    """Parses the snippet that begins at the current line."""
    start_line_index = lines.line_index
    descr = ""
    opts = ""

    # Ensure this is a snippet
    snip = line.split()[0]

    # Get and strip options if they exist
    remain = line[len(snip):].strip()
    words = remain.split()
    if len(words) > 2:
        # second to last word ends with a quote
        if '"' not in words[-1] and words[-2][-1] == '"':
            opts = words[-1]
            remain = remain[:-len(opts) - 1].rstrip()

    # Get and strip description if it exists
    remain = remain.strip()
    if len(remain.split()) > 1 and remain[-1] == '"':
        left = remain[:-1].rfind('"')
        if left != -1 and left != 0:
            descr, remain = remain[left:], remain[:left]

    # The rest is the trigger
    trig = remain.strip()
    if len(trig.split()) > 1 or "r" in opts:
        if trig[0] != trig[-1]:
            return "error", ("Invalid multiword trigger: '%s'" % trig,
                    lines.line_index)
        trig = trig[1:-1]
    end = "end" + snip
    content = ""

    found_end = False
    for line in lines:
        if line.rstrip() == end:
            content = content[:-1]  # Chomp the last newline
            found_end = True
            break
        content += line

    if not found_end:
        return "error", ("Missing 'endsnippet' for %r" % trig, lines.line_index)

    if snip == "global":
        python_globals[trig].append(content)
    elif snip == "snippet":
        return "snippet", (UltiSnipsSnippetDefinition(priority, trig, content,
            descr, opts, python_globals,
            "%s:%i" % (filename, start_line_index)),)
    else:
        return "error", ("Invalid snippet type: '%s'" % snip, lines.line_index)

def _parse_snippets_file(data, filename):
    """Parse 'data' assuming it is a snippet file. Yields events in the
    file."""

    python_globals = defaultdict(list)
    lines = LineIterator(data)
    current_priority = 0
    for line in lines:
        if not line.strip():
            continue

        head, tail = head_tail(line)
        if head in ("snippet", "global"):
            snippet = _handle_snippet_or_global(filename, line, lines,
                    python_globals, current_priority)
            if snippet is not None:
                yield snippet
        elif head == "extends":
            yield handle_extends(tail, lines.line_index)
        elif head == "clearsnippets":
            yield "clearsnippets", (tail.split(),)
        elif head == "priority":
            try:
                current_priority = int(tail.split()[0])
            except (ValueError, IndexError):
                yield "error", ("Invalid priority %r" % tail, lines.line_index)
        elif head and not head.startswith('#'):
            yield "error", ("Invalid line %r" % line.rstrip(), lines.line_index)

class UltiSnipsFileSource(SnippetFileSource):
    """Manages all snippets definitions found in rtp for ultisnips."""

    def _get_all_snippet_files_for(self, ft):
        return find_all_snippet_files(ft)

    def _parse_snippet_file(self, filedata, filename):
        for event, data in _parse_snippets_file(filedata, filename):
            yield event, data

########NEW FILE########
__FILENAME__ = _base
#!/usr/bin/env python
# encoding: utf-8

"""Code to provide access to UltiSnips files from disk."""

from collections import defaultdict
import hashlib
import os

from UltiSnips import _vim
from UltiSnips import compatibility
from UltiSnips.snippet.source._base import SnippetSource

def _hash_file(path):
    """Returns a hashdigest of 'path'"""
    if not os.path.isfile(path):
        return False
    return hashlib.sha1(open(path, "rb").read()).hexdigest()

class SnippetSyntaxError(RuntimeError):
    """Thrown when a syntax error is found in a file."""
    def __init__(self, filename, line_index, msg):
        RuntimeError.__init__(self, "%s in %s:%d" % (
            msg, filename, line_index))

class SnippetFileSource(SnippetSource):
    """Base class that abstracts away 'extends' info and file hashes."""

    def __init__(self):
        SnippetSource.__init__(self)
        self._files_for_ft = defaultdict(set)
        self._file_hashes = defaultdict(lambda: None)

    def get_snippets(self, filetypes, before, possible):
        for ft in filetypes:
            self._ensure_loaded(ft, set())
        return SnippetSource.get_snippets(self, filetypes, before, possible)

    def _get_all_snippet_files_for(self, ft):
        """Returns a set of all files that define snippets for 'ft'."""
        raise NotImplementedError()

    def _parse_snippet_file(self, filedata, filename):
        """Parses 'filedata' as a snippet file and yields events."""
        raise NotImplementedError()

    def _ensure_loaded(self, ft, already_loaded):
        """Make sure that the snippets for 'ft' and everything it extends are
        loaded."""
        if ft in already_loaded:
            return
        already_loaded.add(ft)

        if self._needs_update(ft):
            self._load_snippets_for(ft)

        for parent in self._snippets[ft].extends:
            self._ensure_loaded(parent, already_loaded)

    def _needs_update(self, ft):
        """Returns true if any files for 'ft' have changed and must be
        reloaded."""
        existing_files = self._get_all_snippet_files_for(ft)
        if existing_files != self._files_for_ft[ft]:
            self._files_for_ft[ft] = existing_files
            return True

        for filename in self._files_for_ft[ft]:
            if _hash_file(filename) != self._file_hashes[filename]:
                return True

        return False

    def _load_snippets_for(self, ft):
        """Load all snippets for the given 'ft'."""
        if ft in self._snippets:
            del self._snippets[ft]
        for fn in self._files_for_ft[ft]:
            self._parse_snippets(ft, fn)
        # Now load for the parents
        for parent_ft in self._snippets[ft].extends:
            if parent_ft not in self._snippets:
                self._load_snippets_for(parent_ft)

    def _parse_snippets(self, ft, filename):
        """Parse the 'filename' for the given 'ft' and watch it for changes in
        the future."""
        self._file_hashes[filename] = _hash_file(filename)
        file_data = compatibility.open_ascii_file(filename, "r").read()
        for event, data in self._parse_snippet_file(file_data, filename):
            if event == "error":
                msg, line_index = data
                filename = _vim.eval("""fnamemodify(%s, ":~:.")""" %
                        _vim.escape(filename))
                raise SnippetSyntaxError(filename, line_index, msg)
            elif event == "clearsnippets":
                triggers, = data
                self._snippets[ft].clear_snippets(triggers)
            elif event == "extends":
                # TODO(sirver): extends information is more global
                # than one snippet source.
                filetypes, = data
                self._add_extending_info(ft, filetypes)
            elif event == "snippet":
                snippet, = data
                self._snippets[ft].add_snippet(snippet)
            else:
                assert False, "Unhandled %s: %r" % (event, data)

    def _add_extending_info(self, ft, parents):
        """Add the list of 'parents' as being extended by the 'ft'."""
        sd = self._snippets[ft]
        for parent in parents:
            if parent in sd.extends:
                continue
            sd.extends.append(parent)

########NEW FILE########
__FILENAME__ = _common
#!/usr/bin/env python
# encoding: utf-8

"""Common code for snipMate and UltiSnips snippet files."""

def handle_extends(tail, line_index):
    """Handles an extends line in a snippet."""
    if tail:
        return "extends", ([p.strip() for p in tail.split(',')],)
    else:
        return "error", ("'extends' without file types", line_index)

########NEW FILE########
__FILENAME__ = _base
#!/usr/bin/env python
# encoding: utf-8

"""Base class for snippet sources."""

from collections import defaultdict

from UltiSnips.snippet.source._snippet_dictionary import SnippetDictionary

class SnippetSource(object):
    """See module docstring."""

    def __init__(self):
        self._snippets = defaultdict(SnippetDictionary)

    def get_snippets(self, filetypes, before, possible):
        """Returns the snippets for all 'filetypes' (in order) and their parents
        matching the text 'before'. If 'possible' is true, a partial match is
        enough. Base classes can override this method to provide means of
        creating snippets on the fly.

        Returns a list of SnippetDefinition s.
        """
        found_snippets = []
        for ft in filetypes:
            found_snippets += self._find_snippets(ft, before, possible)
        return found_snippets

    def _find_snippets(self, ft, trigger, potentially=False, seen=None):
        """Find snippets matching 'trigger' for 'ft'. If 'potentially' is True,
        partial matches are enough."""
        snips = self._snippets.get(ft, None)
        if not snips:
            return []
        if not seen:
            seen = set()
        seen.add(ft)
        parent_results = []
        # TODO(sirver): extends information is not bound to one
        # source. It should be tracked further up.
        for parent_ft in snips.extends:
            if parent_ft not in seen:
                seen.add(parent_ft)
                parent_results += self._find_snippets(parent_ft, trigger,
                        potentially, seen)
        return parent_results + snips.get_matching_snippets(
            trigger, potentially)

########NEW FILE########
__FILENAME__ = _snippet_dictionary
#!/usr/bin/env python
# encoding: utf-8

"""Implements a container for parsed snippets."""

# TODO(sirver): This class should not keep track of extends.
class SnippetDictionary(object):
    """See module docstring."""

    def __init__(self):
        self._snippets = []
        self._extends = []

    def add_snippet(self, snippet):
        """Add 'snippet' to this dictionary."""
        self._snippets.append(snippet)

    def get_matching_snippets(self, trigger, potentially):
        """Returns all snippets matching the given trigger. If 'potentially' is
        true, returns all that could_match()."""
        all_snippets = self._snippets
        if not potentially:
            return [s for s in all_snippets if s.matches(trigger)]
        else:
            return [s for s in all_snippets if s.could_match(trigger)]

    def clear_snippets(self, triggers):
        """Remove all snippets that match each trigger in 'triggers'. When
        'triggers' is None, empties this dictionary completely."""
        if not triggers:
            self._snippets = []
            return
        for trigger in triggers:
            for snippet in self.get_matching_snippets(trigger, False):
                if snippet in self._snippets:
                    self._snippets.remove(snippet)

    @property
    def extends(self):
        """The list of filetypes this filetype extends."""
        return self._extends

########NEW FILE########
__FILENAME__ = snippet_manager
#!/usr/bin/env python
# encoding: utf-8

"""Contains the SnippetManager facade used by all Vim Functions."""

from collections import defaultdict
from functools import wraps
import os
import platform
import traceback

from UltiSnips import _vim
from UltiSnips._diff import diff, guess_edit
from UltiSnips.compatibility import as_unicode
from UltiSnips.position import Position
from UltiSnips.snippet.definition import UltiSnipsSnippetDefinition
from UltiSnips.snippet.source import UltiSnipsFileSource, SnipMateFileSource, \
        find_all_snippet_files, find_snippet_files, AddedSnippetsSource
from UltiSnips.text import escape
from UltiSnips.vim_state import VimState, VisualContentPreserver

def _ask_user(a, formatted):
    """Asks the user using inputlist() and returns the selected element or
    None."""
    try:
        rv = _vim.eval("inputlist(%s)" % _vim.escape(formatted))
        if rv is None or rv == '0':
            return None
        rv = int(rv)
        if rv > len(a):
            rv = len(a)
        return a[rv-1]
    except _vim.error:
        # Likely "invalid expression", but might be translated. We have no way
        # of knowing the exact error, therefore, we ignore all errors silently.
        return None
    except KeyboardInterrupt:
        return None

def _ask_snippets(snippets):
    """ Given a list of snippets, ask the user which one they
    want to use, and return it.
    """
    display = [as_unicode("%i: %s (%s)") % (i+1, escape(s.description, '\\'),
        escape(s.location, '\\')) for i, s in enumerate(snippets)]
    return _ask_user(snippets, display)

def err_to_scratch_buffer(func):
    """Decorator that will catch any Exception that 'func' throws and displays
    it in a new Vim scratch buffer."""
    @wraps(func)
    def wrapper(self, *args, **kwds):
        try:
            return func(self, *args, **kwds)
        except: # pylint: disable=bare-except
            msg = \
"""An error occured. This is either a bug in UltiSnips or a bug in a
snippet definition. If you think this is a bug, please report it to
https://github.com/SirVer/ultisnips/issues/new.

Following is the full stack trace:
"""
            msg += traceback.format_exc()
            # Vim sends no WinLeave msg here.
            self._leaving_buffer()  # pylint:disable=protected-access
            _vim.new_scratch_buffer(msg)
    return wrapper


# TODO(sirver): This class is still too long. It should only contain public
# facing methods, most of the private methods should be moved outside of it.
class SnippetManager(object):
    """The main entry point for all UltiSnips functionality. All Vim functions
    call methods in this class."""

    def __init__(self, expand_trigger, forward_trigger, backward_trigger):
        self.expand_trigger = expand_trigger
        self.forward_trigger = forward_trigger
        self.backward_trigger = backward_trigger
        self._inner_mappings_in_place = False
        self._supertab_keys = None

        self._csnippets = []
        self._buffer_filetypes = defaultdict(lambda: ['all'])

        self._vstate = VimState()
        self._visual_content = VisualContentPreserver()

        self._snippet_sources = []

        self._added_snippets_source = AddedSnippetsSource()
        self.register_snippet_source("ultisnips_files", UltiSnipsFileSource())
        self.register_snippet_source("added", self._added_snippets_source)
        self.register_snippet_source("snipmate_files", SnipMateFileSource())

        self._reinit()

    @err_to_scratch_buffer
    def jump_forwards(self):
        """Jumps to the next tabstop."""
        _vim.command("let g:ulti_jump_forwards_res = 1")
        if not self._jump():
            _vim.command("let g:ulti_jump_forwards_res = 0")
            return self._handle_failure(self.forward_trigger)

    @err_to_scratch_buffer
    def jump_backwards(self):
        """Jumps to the previous tabstop."""
        _vim.command("let g:ulti_jump_backwards_res = 1")
        if not self._jump(True):
            _vim.command("let g:ulti_jump_backwards_res = 0")
            return self._handle_failure(self.backward_trigger)

    @err_to_scratch_buffer
    def expand(self):
        """Try to expand a snippet at the current position."""
        _vim.command("let g:ulti_expand_res = 1")
        if not self._try_expand():
            _vim.command("let g:ulti_expand_res = 0")
            self._handle_failure(self.expand_trigger)

    @err_to_scratch_buffer
    def expand_or_jump(self):
        """
        This function is used for people who wants to have the same trigger for
        expansion and forward jumping. It first tries to expand a snippet, if
        this fails, it tries to jump forward.
        """
        _vim.command('let g:ulti_expand_or_jump_res = 1')
        rv = self._try_expand()
        if not rv:
            _vim.command('let g:ulti_expand_or_jump_res = 2')
            rv = self._jump()
        if not rv:
            _vim.command('let g:ulti_expand_or_jump_res = 0')
            self._handle_failure(self.expand_trigger)

    @err_to_scratch_buffer
    def snippets_in_current_scope(self):
        """Returns the snippets that could be expanded to Vim as a global
        variable."""
        before = _vim.buf.line_till_cursor
        snippets = self._snips(before, True)

        # Sort snippets alphabetically
        snippets.sort(key=lambda x: x.trigger)
        for snip in snippets:
            description = snip.description[snip.description.find(snip.trigger) +
                len(snip.trigger) + 2:]

            key = as_unicode(snip.trigger)
            description = as_unicode(description)

            # remove surrounding "" or '' in snippet description if it exists
            if len(description) > 2:
                if (description[0] == description[-1] and
                        description[0] in "'\""):
                    description = description[1:-1]

            _vim.command(as_unicode(
                "let g:current_ulti_dict['{key}'] = '{val}'").format(
                    key=key.replace("'", "''"),
                    val=description.replace("'", "''")))

    @err_to_scratch_buffer
    def list_snippets(self):
        """Shows the snippets that could be expanded to the User and let her
        select one."""
        before = _vim.buf.line_till_cursor
        snippets = self._snips(before, True)

        if len(snippets) == 0:
            self._handle_failure(self.backward_trigger)
            return True

        # Sort snippets alphabetically
        snippets.sort(key=lambda x: x.trigger)

        if not snippets:
            return True

        snippet = _ask_snippets(snippets)
        if not snippet:
            return True

        self._do_snippet(snippet, before)

        return True

    @err_to_scratch_buffer
    def add_snippet(self, trigger, value, description,
            options, ft="all", priority=0):
        """Add a snippet to the list of known snippets of the given 'ft'."""
        self._added_snippets_source.add_snippet(ft,
                UltiSnipsSnippetDefinition(priority, trigger, value,
                    description, options, {}, "added"))

    @err_to_scratch_buffer
    def expand_anon(self, value, trigger="", description="", options=""):
        """Expand an anonymous snippet right here."""
        before = _vim.buf.line_till_cursor
        snip = UltiSnipsSnippetDefinition(0, trigger, value, description,
                options, {}, "")

        if not trigger or snip.matches(before):
            self._do_snippet(snip, before)
            return True
        else:
            return False

    def register_snippet_source(self, name, snippet_source):
        """Registers a new 'snippet_source' with the given 'name'. The given
        class must be an instance of SnippetSource. This source will be queried
        for snippets."""
        self._snippet_sources.append((name, snippet_source))

    def unregister_snippet_source(self, name):
        """Unregister the source with the given 'name'. Does nothing if it is
        not registered."""
        for index, (source_name, _) in enumerate(self._snippet_sources):
            if name == source_name:
                self._snippet_sources = self._snippet_sources[:index] + \
                        self._snippet_sources[index+1:]
                break

    def reset_buffer_filetypes(self):
        """Reset the filetypes for the current buffer."""
        if _vim.buf.number in self._buffer_filetypes:
            del self._buffer_filetypes[_vim.buf.number]

    def add_buffer_filetypes(self, ft):
        """Checks for changes in the list of snippet files or the contents of
        the snippet files and reloads them if necessary. """
        buf_fts = self._buffer_filetypes[_vim.buf.number]
        idx = -1
        for ft in ft.split("."):
            ft = ft.strip()
            if not ft:
                continue
            try:
                idx = buf_fts.index(ft)
            except ValueError:
                self._buffer_filetypes[_vim.buf.number].insert(idx + 1, ft)
                idx += 1

    @err_to_scratch_buffer
    def _cursor_moved(self):
        """Called whenever the cursor moved."""
        if not self._csnippets and self._inner_mappings_in_place:
            self._unmap_inner_keys()
        self._vstate.remember_position()
        if _vim.eval("mode()") not in 'in':
            return

        if self._ignore_movements:
            self._ignore_movements = False
            return

        if self._csnippets:
            cstart = self._csnippets[0].start.line
            cend = self._csnippets[0].end.line + \
                   self._vstate.diff_in_buffer_length
            ct = _vim.buf[cstart:cend + 1]
            lt = self._vstate.remembered_buffer
            pos = _vim.buf.cursor

            lt_span = [0, len(lt)]
            ct_span = [0, len(ct)]
            initial_line = cstart

            # Cut down on lines searched for changes. Start from behind and
            # remove all equal lines. Then do the same from the front.
            if lt and ct:
                while (lt[lt_span[1]-1] == ct[ct_span[1]-1] and
                        self._vstate.ppos.line < initial_line + lt_span[1]-1 and
                        pos.line < initial_line + ct_span[1]-1 and
                        (lt_span[0] < lt_span[1]) and
                        (ct_span[0] < ct_span[1])):
                    ct_span[1] -= 1
                    lt_span[1] -= 1
                while (lt_span[0] < lt_span[1] and
                       ct_span[0] < ct_span[1] and
                       lt[lt_span[0]] == ct[ct_span[0]] and
                       self._vstate.ppos.line >= initial_line and
                       pos.line >= initial_line):
                    ct_span[0] += 1
                    lt_span[0] += 1
                    initial_line += 1
            ct_span[0] = max(0, ct_span[0] - 1)
            lt_span[0] = max(0, lt_span[0] - 1)
            initial_line = max(cstart, initial_line - 1)

            lt = lt[lt_span[0]:lt_span[1]]
            ct = ct[ct_span[0]:ct_span[1]]

            try:
                rv, es = guess_edit(initial_line, lt, ct, self._vstate)
                if not rv:
                    lt = '\n'.join(lt)
                    ct = '\n'.join(ct)
                    es = diff(lt, ct, initial_line)
                self._csnippets[0].replay_user_edits(es)
            except IndexError:
                # Rather do nothing than throwing an error. It will be correct
                # most of the time
                pass

        self._check_if_still_inside_snippet()
        if self._csnippets:
            self._csnippets[0].update_textobjects()
            self._vstate.remember_buffer(self._csnippets[0])

    def _map_inner_keys(self):
        """Map keys that should only be defined when a snippet is active."""
        if self.expand_trigger != self.forward_trigger:
            _vim.command("inoremap <buffer> <silent> " + self.forward_trigger +
                    " <C-R>=UltiSnips#JumpForwards()<cr>")
            _vim.command("snoremap <buffer> <silent> " + self.forward_trigger +
                    " <Esc>:call UltiSnips#JumpForwards()<cr>")
        _vim.command("inoremap <buffer> <silent> " + self.backward_trigger +
                " <C-R>=UltiSnips#JumpBackwards()<cr>")
        _vim.command("snoremap <buffer> <silent> " + self.backward_trigger +
                " <Esc>:call UltiSnips#JumpBackwards()<cr>")
        self._inner_mappings_in_place = True

    def _unmap_inner_keys(self):
        """Unmap keys that should not be active when no snippet is active."""
        if not self._inner_mappings_in_place:
            return
        try:
            if self.expand_trigger != self.forward_trigger:
                _vim.command("iunmap <buffer> %s" % self.forward_trigger)
                _vim.command("sunmap <buffer> %s" % self.forward_trigger)
            _vim.command("iunmap <buffer> %s" % self.backward_trigger)
            _vim.command("sunmap <buffer> %s" % self.backward_trigger)
            self._inner_mappings_in_place = False
        except _vim.error:
            # This happens when a preview window was opened. This issues
            # CursorMoved, but not BufLeave. We have no way to unmap, until we
            # are back in our buffer
            pass

    @err_to_scratch_buffer
    def _save_last_visual_selection(self):
        """
        This is called when the expand trigger is pressed in visual mode.
        Our job is to remember everything between '< and '> and pass it on to
        ${VISUAL} in case it will be needed.
        """
        self._visual_content.conserve()

    def _leaving_buffer(self):
        """Called when the user switches tabs/windows/buffers. It basically
        means that all snippets must be properly terminated."""
        while len(self._csnippets):
            self._current_snippet_is_done()
        self._reinit()

    def _reinit(self):
        """Resets transient state."""
        self._ctab = None
        self._ignore_movements = False

    def _check_if_still_inside_snippet(self):
        """Checks if the cursor is outside of the current snippet."""
        if self._cs and (
            not self._cs.start <= _vim.buf.cursor <= self._cs.end
        ):
            self._current_snippet_is_done()
            self._reinit()
            self._check_if_still_inside_snippet()

    def _current_snippet_is_done(self):
        """The current snippet should be terminated."""
        self._csnippets.pop()
        if not self._csnippets:
            self._unmap_inner_keys()

    def _jump(self, backwards=False):
        """Helper method that does the actual jump."""
        jumped = False
        if self._cs:
            self._ctab = self._cs.select_next_tab(backwards)
            if self._ctab:
                if self._cs.snippet.has_option("s"):
                    lineno = _vim.buf.cursor.line
                    _vim.buf[lineno] = _vim.buf[lineno].rstrip()
                _vim.select(self._ctab.start, self._ctab.end)
                jumped = True
                if self._ctab.number == 0:
                    self._current_snippet_is_done()
            else:
                # This really shouldn't happen, because a snippet should
                # have been popped when its final tabstop was used.
                # Cleanup by removing current snippet and recursing.
                self._current_snippet_is_done()
                jumped = self._jump(backwards)
        if jumped:
            self._vstate.remember_position()
            self._vstate.remember_unnamed_register(self._ctab.current_text)
            self._ignore_movements = True
        return jumped

    def _leaving_insert_mode(self):
        """Called whenever we leave the insert mode."""
        self._vstate.restore_unnamed_register()

    def _handle_failure(self, trigger):
        """Mainly make sure that we play well with SuperTab."""
        if trigger.lower() == "<tab>":
            feedkey = "\\" + trigger
        elif trigger.lower() == "<s-tab>":
            feedkey = "\\" + trigger
        else:
            feedkey = None
        mode = "n"
        if not self._supertab_keys:
            if _vim.eval("exists('g:SuperTabMappingForward')") != "0":
                self._supertab_keys = (
                    _vim.eval("g:SuperTabMappingForward"),
                    _vim.eval("g:SuperTabMappingBackward"),
                )
            else:
                self._supertab_keys = ['', '']

        for idx, sttrig in enumerate(self._supertab_keys):
            if trigger.lower() == sttrig.lower():
                if idx == 0:
                    feedkey = r"\<Plug>SuperTabForward"
                    mode = "n"
                elif idx == 1:
                    feedkey = r"\<Plug>SuperTabBackward"
                    mode = "p"
                # Use remap mode so SuperTab mappings will be invoked.
                break

        if (feedkey == r"\<Plug>SuperTabForward" or
                feedkey == r"\<Plug>SuperTabBackward"):
            _vim.command("return SuperTab(%s)" % _vim.escape(mode))
        elif feedkey:
            _vim.command("return %s" % _vim.escape(feedkey))

    def _snips(self, before, partial):
        """Returns all the snippets for the given text before the cursor. If
        partial is True, then get also return partial matches. """
        filetypes = self._buffer_filetypes[_vim.buf.number][::-1]
        matching_snippets = defaultdict(list)
        for _, source in self._snippet_sources:
            for snippet in source.get_snippets(filetypes, before, partial):
                matching_snippets[snippet.trigger].append(snippet)
        if not matching_snippets:
            return []

        # Now filter duplicates and only keep the one with the highest
        # priority.
        snippets = []
        for snippets_with_trigger in matching_snippets.values():
            highest_priority = max(s.priority for s in snippets_with_trigger)
            snippets.extend(s for s in snippets_with_trigger
                    if s.priority == highest_priority)

        # For partial matches we are done, but if we want to expand a snippet,
        # we have to go over them again and only keep those with the maximum
        # priority.
        if partial:
            return snippets

        highest_priority = max(s.priority for s in snippets)
        return [s for s in snippets if s.priority == highest_priority]

    def _do_snippet(self, snippet, before):
        """Expands the given snippet, and handles everything
        that needs to be done with it."""
        self._map_inner_keys()

        # Adjust before, maybe the trigger is not the complete word
        text_before = before
        if snippet.matched:
            text_before = before[:-len(snippet.matched)]

        if self._cs:
            start = Position(_vim.buf.cursor.line, len(text_before))
            end = Position(_vim.buf.cursor.line, len(before))

            # It could be that our trigger contains the content of TextObjects
            # in our containing snippet. If this is indeed the case, we have to
            # make sure that those are properly killed. We do this by
            # pretending that the user deleted and retyped the text that our
            # trigger matched.
            edit_actions = [
                ("D", start.line, start.col, snippet.matched),
                ("I", start.line, start.col, snippet.matched),
            ]
            self._csnippets[0].replay_user_edits(edit_actions)

            si = snippet.launch(text_before, self._visual_content,
                    self._cs.find_parent_for_new_to(start), start, end)
        else:
            start = Position(_vim.buf.cursor.line, len(text_before))
            end = Position(_vim.buf.cursor.line, len(before))
            si = snippet.launch(text_before, self._visual_content,
                                None, start, end)

        self._visual_content.reset()
        self._csnippets.append(si)

        si.update_textobjects()

        self._ignore_movements = True
        self._vstate.remember_buffer(self._csnippets[0])

        self._jump()

    def _try_expand(self):
        """Try to expand a snippet in the current place."""
        before = _vim.buf.line_till_cursor
        if not before:
            return False
        snippets = self._snips(before, False)
        if not snippets:
            # No snippet found
            return False
        elif len(snippets) == 1:
            snippet = snippets[0]
        else:
            snippet = _ask_snippets(snippets)
            if not snippet:
                return True
        self._do_snippet(snippet, before)
        return True

    @property
    def _cs(self):
        """The current snippet or None."""
        if not len(self._csnippets):
            return None
        return self._csnippets[-1]

    def _file_to_edit(self, requested_ft, bang):  # pylint: disable=no-self-use
        """Returns a file to be edited for the given requested_ft. If 'bang' is
        empty only private files in g:UltiSnipsSnippetsDir are considered,
        otherwise all files are considered and the user gets to choose.
        """
        # This method is not using self, but is called by UltiSnips.vim and is
        # therefore in this class because it is the facade to Vim.
        potentials = set()

        if _vim.eval("exists('g:UltiSnipsSnippetsDir')") == "1":
            snippet_dir = _vim.eval("g:UltiSnipsSnippetsDir")
        else:
            if platform.system() == "Windows":
                snippet_dir = os.path.join(_vim.eval("$HOME"),
                        "vimfiles", "UltiSnips")
            else:
                snippet_dir = os.path.join(_vim.eval("$HOME"),
                        ".vim", "UltiSnips")

        filetypes = []
        if requested_ft:
            filetypes.append(requested_ft)
        else:
            if bang:
                filetypes.extend(self._buffer_filetypes[_vim.buf.number])
            else:
                filetypes.append(self._buffer_filetypes[_vim.buf.number][0])

        for ft in filetypes:
            potentials.update(find_snippet_files(ft, snippet_dir))
            potentials.add(os.path.join(snippet_dir,
                ft + '.snippets'))
            if bang:
                potentials.update(find_all_snippet_files(ft))

        potentials = set(os.path.realpath(os.path.expanduser(p))
                for p in potentials)

        if len(potentials) > 1:
            files = sorted(potentials)
            formatted = [as_unicode('%i: %s') % (i, escape(fn, '\\')) for
                    i, fn in enumerate(files, 1)]
            file_to_edit = _ask_user(files, formatted)
            if file_to_edit is None:
                return ""
        else:
            file_to_edit = potentials.pop()

        dirname = os.path.dirname(file_to_edit)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        return file_to_edit

########NEW FILE########
__FILENAME__ = test_diff
#!/usr/bin/env python
# encoding: utf-8

# pylint: skip-file

import unittest

from _diff import diff, guess_edit
from position import Position


def transform(a, cmds):
    buf = a.split("\n")

    for cmd in cmds:
        ctype, line, col, char = cmd
        if ctype == "D":
            if char != '\n':
                buf[line] = buf[line][:col] + buf[line][col+len(char):]
            else:
                buf[line] = buf[line] + buf[line+1]
                del buf[line+1]
        elif ctype == "I":
            buf[line] = buf[line][:col] + char + buf[line][col:]
        buf = '\n'.join(buf).split('\n')
    return '\n'.join(buf)


import unittest

# Test Guessing  {{{
class _BaseGuessing(object):
    def runTest(self):
        rv, es = guess_edit(self.initial_line, self.a, self.b, Position(*self.ppos), Position(*self.pos))
        self.assertEqual(rv, True)
        self.assertEqual(self.wanted, es)

class TestGuessing_Noop0(_BaseGuessing, unittest.TestCase):
    a, b = [], []
    initial_line = 0
    ppos, pos = (0, 6), (0, 7)
    wanted = ()

class TestGuessing_InsertOneChar(_BaseGuessing, unittest.TestCase):
    a, b = ["Hello  World"], ["Hello   World"]
    initial_line = 0
    ppos, pos = (0, 6), (0, 7)
    wanted = (
        ("I", 0, 6, " "),
    )
class TestGuessing_InsertOneChar1(_BaseGuessing, unittest.TestCase):
    a, b = ["Hello  World"], ["Hello   World"]
    initial_line = 0
    ppos, pos = (0, 7), (0, 8)
    wanted = (
        ("I", 0, 7, " "),
    )
class TestGuessing_BackspaceOneChar(_BaseGuessing, unittest.TestCase):
    a, b = ["Hello  World"], ["Hello World"]
    initial_line = 0
    ppos, pos = (0, 7), (0, 6)
    wanted = (
        ("D", 0, 6, " "),
    )
class TestGuessing_DeleteOneChar(_BaseGuessing, unittest.TestCase):
    a, b = ["Hello  World"], ["Hello World"]
    initial_line = 0
    ppos, pos = (0, 5), (0, 5)
    wanted = (
        ("D", 0, 5, " "),
    )

# End: Test Guessing  }}}

class _Base(object):
    def runTest(self):
        es = diff(self.a, self.b)
        tr = transform(self.a, es)
        self.assertEqual(self.b, tr)
        self.assertEqual(self.wanted, es)

class TestEmptyString(_Base, unittest.TestCase):
    a, b = "", ""
    wanted = ()

class TestAllMatch(_Base, unittest.TestCase):
    a, b = "abcdef", "abcdef"
    wanted = ()

class TestLotsaNewlines(_Base, unittest.TestCase):
    a, b = "Hello", "Hello\nWorld\nWorld\nWorld"
    wanted = (
        ("I", 0, 5, "\n"),
        ("I", 1, 0, "World"),
        ("I", 1, 5, "\n"),
        ("I", 2, 0, "World"),
        ("I", 2, 5, "\n"),
        ("I", 3, 0, "World"),
    )

class TestCrash(_Base, unittest.TestCase):
    a = 'hallo Blah mitte=sdfdsfsd\nhallo kjsdhfjksdhfkjhsdfkh mittekjshdkfhkhsdfdsf'
    b = 'hallo Blah mitte=sdfdsfsd\nhallo b mittekjshdkfhkhsdfdsf'
    wanted = (
        ("D", 1, 6, "kjsdhfjksdhfkjhsdfkh"),
        ("I", 1, 6, "b"),
    )

class TestRealLife(_Base, unittest.TestCase):
    a = 'hallo End Beginning'
    b = 'hallo End t'
    wanted = (
        ("D", 0, 10, "Beginning"),
        ("I", 0, 10, "t"),
    )

class TestRealLife1(_Base, unittest.TestCase):
    a = 'Vorne hallo Hinten'
    b = 'Vorne hallo  Hinten'
    wanted = (
        ("I", 0, 11, " "),
    )

class TestWithNewline(_Base, unittest.TestCase):
    a = 'First Line\nSecond Line'
    b = 'n'
    wanted = (
        ("D", 0, 0, "First Line"),
        ("D", 0, 0, "\n"),
        ("D", 0, 0, "Second Line"),
        ("I", 0, 0, "n"),
    )


class TestCheapDelete(_Base, unittest.TestCase):
    a = 'Vorne hallo Hinten'
    b = 'Vorne Hinten'
    wanted = (
        ("D", 0, 5, " hallo"),
    )

class TestNoSubstring(_Base, unittest.TestCase):
    a,b = "abc", "def"
    wanted = (
        ("D", 0, 0, "abc"),
        ("I", 0, 0, "def"),
    )

class TestCommonCharacters(_Base, unittest.TestCase):
    a,b = "hasomelongertextbl", "hol"
    wanted = (
        ("D", 0, 1, "asomelongertextb"),
        ("I", 0, 1, "o"),
    )

class TestUltiSnipsProblem(_Base, unittest.TestCase):
    a = "this is it this is it this is it"
    b = "this is it a this is it"
    wanted = (
        ("D", 0, 11, "this is it"),
        ("I", 0, 11, "a"),
    )

class MatchIsTooCheap(_Base, unittest.TestCase):
    a = "stdin.h"
    b = "s"
    wanted = (
        ("D", 0, 1, "tdin.h"),
    )

class MultiLine(_Base, unittest.TestCase):
    a = "hi first line\nsecond line first line\nsecond line world"
    b = "hi first line\nsecond line k world"

    wanted = (
        ("D", 1, 12, "first line"),
        ("D", 1, 12, "\n"),
        ("D", 1, 12, "second line"),
        ("I", 1, 12, "k"),
    )


if __name__ == '__main__':
   unittest.main()
   # k = TestEditScript()
   # unittest.TextTestRunner().run(k)

########NEW FILE########
__FILENAME__ = test_position
#!/usr/bin/env python
# encoding: utf-8

# pylint: skip-file

import unittest

from position import Position

class _MPBase(object):
    def runTest(self):
        obj = Position(*self.obj)
        for pivot, delta, wanted in self.steps:
            obj.move(Position(*pivot), Position(*delta))
            self.assertEqual(Position(*wanted), obj)

class MovePosition_DelSameLine(_MPBase, unittest.TestCase):
    # hello wor*ld -> h*ld -> hl*ld
    obj = (0, 9)
    steps = (
        ((0, 1), (0, -8), (0, 1)),
        ((0, 1), (0, 1), (0, 2)),
    )
class MovePosition_DelSameLine1(_MPBase, unittest.TestCase):
    # hel*lo world -> hel*world -> hel*worl
    obj = (0,3)
    steps = (
        ((0, 4), (0, -3), (0,3)),
        ((0, 8), (0, -1), (0,3)),
    )
class MovePosition_InsSameLine1(_MPBase, unittest.TestCase):
    # hel*lo world -> hel*woresld
    obj = (0, 3)
    steps = (
        ((0, 4), (0, -3), (0, 3)),
        ((0, 6), (0, 2), (0, 3)),
        ((0, 8), (0, -1), (0, 3))
    )
class MovePosition_InsSameLine2(_MPBase, unittest.TestCase):
    # hello wor*ld -> helesdlo wor*ld
    obj = (0, 9)
    steps = (
        ((0, 3), (0, 3), (0, 12)),
    )

class MovePosition_DelSecondLine(_MPBase, unittest.TestCase):
    # hello world. sup   hello world.*a, was
    # *a, was            ach nix
    # ach nix
    obj = (1, 0)
    steps = (
        ((0, 12), (0, -4), (1, 0)),
        ((0, 12), (-1, 0), (0, 12)),
    )
class MovePosition_DelSecondLine1(_MPBase, unittest.TestCase):
    # hello world. sup
    # a, *was
    # ach nix
    # hello world.a*was
    # ach nix
    obj = (1, 3)
    steps = (
        ((0, 12), (0, -4), (1, 3)),
        ((0, 12), (-1, 0), (0, 15)),
        ((0, 12), (0, -3), (0, 12)),
        ((0, 12), (0,  1), (0, 13)),
    )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = text
#!/usr/bin/env python
# encoding: utf-8

"""Utilities to deal with text."""

def unescape(text):
    """Removes '\\' escaping from 'text'."""
    rv = ""
    i = 0
    while i < len(text):
        if i+1 < len(text) and text[i] == '\\':
            rv += text[i+1]
            i += 1
        else:
            rv += text[i]
        i += 1
    return rv

def escape(text, chars):
    """Escapes all characters in 'chars' in text using backspaces."""
    rv = ""
    for char in text:
        if char in chars:
            rv += '\\'
        rv += char
    return rv


def fill_in_whitespace(text):
    """Returns 'text' with escaped whitespace replaced through whitespaces."""
    text = text.replace(r"\n", "\n")
    text = text.replace(r"\t", "\t")
    text = text.replace(r"\r", "\r")
    text = text.replace(r"\a", "\a")
    text = text.replace(r"\b", "\b")
    return text

def head_tail(line):
    """Returns the first word in 'line' and the rest of 'line' or None if the
    line is too short."""
    generator = (t.strip() for t in line.split(None, 1))
    head = next(generator).strip()
    tail = ''
    try:
        tail = next(generator).strip()
    except StopIteration:
        pass
    return head, tail

class LineIterator(object):
    """Convenience class that keeps track of line numbers in files."""

    def __init__(self, text):
        self._line_index = -1
        self._lines = list(text.splitlines(True))

    def __iter__(self):
        return self

    def __next__(self):
        """Returns the next line."""
        if self._line_index + 1 < len(self._lines):
            self._line_index += 1
            return self._lines[self._line_index]
        raise StopIteration()
    next = __next__  # for python2

    @property
    def line_index(self):
        """The 1 based line index in the current file."""
        return self._line_index + 1

    def peek(self):
        """Returns the next line (if there is any, otherwise None) without
        advancing the iterator."""
        try:
            return self._lines[self._line_index + 1]
        except IndexError:
            return None

########NEW FILE########
__FILENAME__ = _base
#!/usr/bin/env python
# encoding: utf-8

"""Base classes for all text objects."""

from UltiSnips import _vim
from UltiSnips.position import Position

def _calc_end(text, start):
    """Calculate the end position of the 'text' starting at 'start."""
    if len(text) == 1:
        new_end = start + Position(0, len(text[0]))
    else:
        new_end = Position(start.line + len(text)-1, len(text[-1]))
    return new_end

def _text_to_vim(start, end, text):
    """Copy the given text to the current buffer, overwriting the span 'start'
    to 'end'."""
    lines = text.split('\n')

    new_end = _calc_end(lines, start)

    before = _vim.buf[start.line][:start.col]
    after = _vim.buf[end.line][end.col:]

    new_lines = []
    if len(lines):
        new_lines.append(before + lines[0])
        new_lines.extend(lines[1:])
        new_lines[-1] += after
    _vim.buf[start.line:end.line + 1] = new_lines

    # Open any folds this might have created
    _vim.buf.cursor = start
    _vim.command("normal! zv")

    return new_end

# These classes use their subclasses a lot and we really do not want to expose
# their functions more globally.
# pylint: disable=protected-access
class TextObject(object):
    """Represents any object in the text that has a span in any ways."""

    def __init__(self, parent, token, end=None,
            initial_text="", tiebreaker=None):
        self._parent = parent

        if end is not None: # Took 4 arguments
            self._start = token
            self._end = end
            self._initial_text = initial_text
        else: # Initialize from token
            self._start = token.start
            self._end = token.end
            self._initial_text = token.initial_text
        self._tiebreaker = tiebreaker or Position(
                self._start.line, self._end.line)
        if parent is not None:
            parent._add_child(self)

    def _move(self, pivot, diff):
        """Move this object by 'diff' while 'pivot' is the point of change."""
        self._start.move(pivot, diff)
        self._end.move(pivot, diff)

    def __lt__(self, other):
        me_tuple = (self.start.line, self.start.col,
                self._tiebreaker.line, self._tiebreaker.col)
        other_tuple = (other._start.line, other._start.col,
                other._tiebreaker.line, other._tiebreaker.col)
        return me_tuple < other_tuple

    def __le__(self, other):
        me_tuple = (self._start.line, self._start.col,
                self._tiebreaker.line, self._tiebreaker.col)
        other_tuple = (other._start.line, other._start.col,
                other._tiebreaker.line, other._tiebreaker.col)
        return me_tuple <= other_tuple

    def __repr__(self):
        ct = ""
        try:
            ct = self.current_text
        except IndexError:
            ct = "<err>"

        return "%s(%r->%r,%r)" % (self.__class__.__name__,
                self._start, self._end, ct)

    @property
    def current_text(self):
        """The current text of this object."""
        if self._start.line == self._end.line:
            return _vim.buf[self._start.line][self._start.col:self._end.col]
        else:
            lines = [_vim.buf[self._start.line][self._start.col:]]
            lines.extend(_vim.buf[self._start.line+1:self._end.line])
            lines.append(_vim.buf[self._end.line][:self._end.col])
            return '\n'.join(lines)

    @property
    def start(self):
        """The start position."""
        return self._start

    @property
    def end(self):
        """The end position."""
        return self._end

    def overwrite(self, gtext=None):
        """Overwrite the text of this object in the Vim Buffer and update its
        length information. If 'gtext' is None use the initial text of this
        object.
        """
        # We explicitly do not want to move our children around here as we
        # either have non or we are replacing text initially which means we do
        # not want to mess with their positions
        if self.current_text == gtext:
            return
        old_end = self._end
        self._end = _text_to_vim(
                self._start, self._end, gtext or self._initial_text)
        if self._parent:
            self._parent._child_has_moved(
                self._parent._children.index(self), min(old_end, self._end),
                self._end.delta(old_end)
            )

    def _update(self, done):
        """Update this object inside the Vim Buffer.

        Return False if you need to be called again for this edit cycle.
        Otherwise return True.
        """
        raise NotImplementedError("Must be implemented by subclasses.")

class EditableTextObject(TextObject):
    """
    This base class represents any object in the text
    that can be changed by the user
    """
    def __init__(self, *args, **kwargs):
        TextObject.__init__(self, *args, **kwargs)
        self._children = []
        self._tabstops = {}

    ##############
    # Properties #
    ##############
    @property
    def children(self):
        """List of all children."""
        return self._children

    @property
    def _editable_children(self):
        """List of all children that are EditableTextObjects"""
        return [child for child in self._children if
                isinstance(child, EditableTextObject)]

    ####################
    # Public Functions #
    ####################
    def find_parent_for_new_to(self, pos):
        """Figure out the parent object for something at 'pos'."""
        for children in self._editable_children:
            if children._start <= pos < children._end:
                return children.find_parent_for_new_to(pos)
        return self

    ###############################
    # Private/Protected functions #
    ###############################
    def _do_edit(self, cmd):
        """Apply the edit 'cmd' to this object."""
        ctype, line, col, text = cmd
        assert ('\n' not in text) or (text == "\n")
        pos = Position(line, col)

        to_kill = set()
        new_cmds = []
        for child in self._children:
            if ctype == "I": # Insertion
                if (child._start < pos <
                        Position(child._end.line, child._end.col) and
                        isinstance(child, NoneditableTextObject)):
                    to_kill.add(child)
                    new_cmds.append(cmd)
                    break
                elif ((child._start <= pos <= child._end) and
                        isinstance(child, EditableTextObject)):
                    child._do_edit(cmd)
                    return
            else: # Deletion
                delend = pos + Position(0, len(text)) if text != "\n" \
                        else Position(line + 1, 0)
                if ((child._start <= pos < child._end) and
                        (child._start < delend <= child._end)):
                    # this edit command is completely for the child
                    if isinstance(child, NoneditableTextObject):
                        to_kill.add(child)
                        new_cmds.append(cmd)
                        break
                    else:
                        child._do_edit(cmd)
                        return
                elif ((pos < child._start and child._end <= delend) or
                        (pos <= child._start and child._end < delend)):
                    # Case: this deletion removes the child
                    to_kill.add(child)
                    new_cmds.append(cmd)
                    break
                elif (pos < child._start and
                        (child._start < delend <= child._end)):
                    # Case: partially for us, partially for the child
                    my_text = text[:(child._start-pos).col]
                    c_text = text[(child._start-pos).col:]
                    new_cmds.append((ctype, line, col, my_text))
                    new_cmds.append((ctype, line, col, c_text))
                    break
                elif (delend >= child._end and (
                        child._start <= pos < child._end)):
                    # Case: partially for us, partially for the child
                    c_text = text[(child._end-pos).col:]
                    my_text = text[:(child._end-pos).col]
                    new_cmds.append((ctype, line, col, c_text))
                    new_cmds.append((ctype, line, col, my_text))
                    break

        for child in to_kill:
            self._del_child(child)
        if len(new_cmds):
            for child in new_cmds:
                self._do_edit(child)
            return

        # We have to handle this ourselves
        delta = Position(1, 0) if text == "\n" else Position(0, len(text))
        if ctype == "D":
             # Makes no sense to delete in empty textobject
            if self._start == self._end:
                return
            delta.line *= -1
            delta.col *= -1
        pivot = Position(line, col)
        idx = -1
        for cidx, child in enumerate(self._children):
            if child._start < pivot <= child._end:
                idx = cidx
        self._child_has_moved(idx, pivot, delta)

    def _move(self, pivot, diff):
        TextObject._move(self, pivot, diff)

        for child in self._children:
            child._move(pivot, diff)

    def _child_has_moved(self, idx, pivot, diff):
        """Called when a the child with 'idx' has moved behind 'pivot' by
        'diff'."""
        self._end.move(pivot, diff)

        for child in self._children[idx+1:]:
            child._move(pivot, diff)

        if self._parent:
            self._parent._child_has_moved(
                self._parent._children.index(self), pivot, diff
            )

    def _get_next_tab(self, number):
        """Returns the next tabstop after 'number'."""
        if not len(self._tabstops.keys()):
            return
        tno_max = max(self._tabstops.keys())

        possible_sol = []
        i = number + 1
        while i <= tno_max:
            if i in self._tabstops:
                possible_sol.append((i, self._tabstops[i]))
                break
            i += 1

        child = [c._get_next_tab(number) for c in self._editable_children]
        child = [c for c in child if c]

        possible_sol += child

        if not len(possible_sol):
            return None

        return min(possible_sol)


    def _get_prev_tab(self, number):
        """Returns the previous tabstop before 'number'."""
        if not len(self._tabstops.keys()):
            return
        tno_min = min(self._tabstops.keys())

        possible_sol = []
        i = number - 1
        while i >= tno_min and i > 0:
            if i in self._tabstops:
                possible_sol.append((i, self._tabstops[i]))
                break
            i -= 1

        child = [c._get_prev_tab(number) for c in self._editable_children]
        child = [c for c in child if c]

        possible_sol += child

        if not len(possible_sol):
            return None

        return max(possible_sol)

    def _get_tabstop(self, requester, number):
        """Returns the tabstop 'number'. 'requester' is the class that is
        interested in this."""
        if number in self._tabstops:
            return self._tabstops[number]
        for child in self._editable_children:
            if child is requester:
                continue
            rv = child._get_tabstop(self, number)
            if rv is not None:
                return rv
        if self._parent and requester is not self._parent:
            return self._parent._get_tabstop(self, number)

    def _update(self, done):
        if all((child in done) for child in self._children):
            assert self not in done
            done.add(self)
        return True

    def _add_child(self, child):
        """Add 'child' as a new child of this text object."""
        self._children.append(child)
        self._children.sort()

    def _del_child(self, child):
        """Delete this 'child'."""
        child._parent = None
        self._children.remove(child)

        # If this is a tabstop, delete it. Might have been deleted already if
        # it was nested.
        try:
            del self._tabstops[child.number]
        except (AttributeError, KeyError):
            pass

class NoneditableTextObject(TextObject):
    """All passive text objects that the user can't edit by hand."""
    def _update(self, done):
        return True

########NEW FILE########
__FILENAME__ = _escaped_char
#!/usr/bin/env python
# encoding: utf-8

"""See module comment."""

from UltiSnips.text_objects._base import NoneditableTextObject

class EscapedChar(NoneditableTextObject):
    r"""
    This class is a escape char like \$. It is handled in a text object to make
    sure that siblings are correctly moved after replacing the text.

    This is a base class without functionality just to mark it in the code.
    """
    pass

########NEW FILE########
__FILENAME__ = _mirror
#!/usr/bin/env python
# encoding: utf-8

"""A Mirror object contains the same text as its related tabstop."""

from UltiSnips.text_objects._base import NoneditableTextObject

class Mirror(NoneditableTextObject):
    """See module docstring."""

    def __init__(self, parent, tabstop, token):
        NoneditableTextObject.__init__(self, parent, token)

        self._ts = tabstop

    def _update(self, done):
        if self._ts.is_killed:
            self.overwrite("")
            self._parent._del_child(self)   # pylint:disable=protected-access
            return True

        if self._ts not in done:
            return False

        self.overwrite(self._get_text())
        return True

    def _get_text(self):
        """Returns the text used for mirroring. Overwritten by base classes."""
        return self._ts.current_text

########NEW FILE########
__FILENAME__ = _python_code
#!/usr/bin/env python
# encoding: utf-8

"""Implements `!p ` interpolation."""

import os
from collections import namedtuple

from UltiSnips import _vim
from UltiSnips.compatibility import as_unicode
from UltiSnips.indent_util import IndentUtil
from UltiSnips.text_objects._base import NoneditableTextObject


class _Tabs(object):
    """Allows access to tabstop content via t[] inside of python code."""
    def __init__(self, to):
        self._to = to

    def __getitem__(self, no):
        ts = self._to._get_tabstop(self._to, int(no))  # pylint:disable=protected-access
        if ts is None:
            return ""
        return ts.current_text

_VisualContent = namedtuple('_VisualContent', ['mode', 'text'])

class SnippetUtil(object):
    """Provides easy access to indentation, etc. This is the 'snip' object in
    python code."""

    def __init__(self, initial_indent, vmode, vtext):
        self._ind = IndentUtil()
        self._visual = _VisualContent(vmode, vtext)
        self._initial_indent = self._ind.indent_to_spaces(initial_indent)
        self._reset("")

    def _reset(self, cur):
        """Gets the snippet ready for another update.
        :cur: the new value for c.
        """
        self._ind.reset()
        self._cur = cur
        self._rv = ""
        self._changed = False
        self.reset_indent()

    def shift(self, amount=1):
        """Shifts the indentation level.
        Note that this uses the shiftwidth because thats what code
        formatters use.

        :amount: the amount by which to shift.
        """
        self.indent += " " * self._ind.shiftwidth * amount

    def unshift(self, amount=1):
        """Unshift the indentation level.
        Note that this uses the shiftwidth because thats what code
        formatters use.

        :amount: the amount by which to unshift.
        """
        by = -self._ind.shiftwidth * amount
        try:
            self.indent = self.indent[:by]
        except IndexError:
            self.indent = ""

    def mkline(self, line="", indent=None):
        """Creates a properly set up line.

        :line: the text to add
        :indent: the indentation to have at the beginning
                 if None, it uses the default amount
        """
        if indent is None:
            indent = self.indent
            # this deals with the fact that the first line is
            # already properly indented
            if '\n' not in self._rv:
                try:
                    indent = indent[len(self._initial_indent):]
                except IndexError:
                    indent = ""
            indent = self._ind.spaces_to_indent(indent)

        return indent + line

    def reset_indent(self):
        """Clears the indentation."""
        self.indent = self._initial_indent

    # Utility methods
    @property
    def fn(self):  # pylint:disable=no-self-use,invalid-name
        """The filename."""
        return _vim.eval('expand("%:t")') or ""

    @property
    def basename(self):  # pylint:disable=no-self-use
        """The filename without extension."""
        return _vim.eval('expand("%:t:r")') or ""

    @property
    def ft(self):  # pylint:disable=invalid-name
        """The filetype."""
        return self.opt("&filetype", "")

    @property
    def rv(self):  # pylint:disable=invalid-name
        """The return value. The text to insert at the location of the
        placeholder."""
        return self._rv

    @rv.setter
    def rv(self, value):  # pylint:disable=invalid-name
        """See getter."""
        self._changed = True
        self._rv = value

    @property
    def _rv_changed(self):
        """True if rv has changed."""
        return self._changed

    @property
    def c(self):  # pylint:disable=invalid-name
        """The current text of the placeholder."""
        return self._cur

    @property
    def v(self):  # pylint:disable=invalid-name
        """Content of visual expansions"""
        return self._visual

    def opt(self, option, default=None):  # pylint:disable=no-self-use
        """Gets a Vim variable."""
        if _vim.eval("exists('%s')" % option) == "1":
            try:
                return _vim.eval(option)
            except _vim.error:
                pass
        return default

    def __add__(self, value):
        """Appends the given line to rv using mkline."""
        self.rv += '\n'  # pylint:disable=invalid-name
        self.rv += self.mkline(value)
        return self

    def __lshift__(self, other):
        """Same as unshift."""
        self.unshift(other)

    def __rshift__(self, other):
        """Same as shift."""
        self.shift(other)


class PythonCode(NoneditableTextObject):
    """See module docstring."""

    def __init__(self, parent, token):

        # Find our containing snippet for snippet local data
        snippet = parent
        while snippet:
            try:
                self._locals = snippet.locals
                text = snippet.visual_content.text
                mode = snippet.visual_content.mode
                break
            except AttributeError:
                snippet = snippet._parent  # pylint:disable=protected-access
        self._snip = SnippetUtil(token.indent, mode, text)

        self._codes = ((
            "import re, os, vim, string, random",
            "\n".join(snippet.globals.get("!p", [])).replace("\r\n", "\n"),
            token.code.replace("\\`", "`")
        ))
        NoneditableTextObject.__init__(self, parent, token)

    def _update(self, done):
        path = _vim.eval('expand("%")') or ""
        ct = self.current_text
        self._locals.update({
            't': _Tabs(self._parent),
            'fn': os.path.basename(path),
            'path': path,
            'cur': ct,
            'res': ct,
            'snip': self._snip,
        })
        self._snip._reset(ct)  # pylint:disable=protected-access

        for code in self._codes:
            exec(code, self._locals)  # pylint:disable=exec-used

        rv = as_unicode(
            self._snip.rv if self._snip._rv_changed  # pylint:disable=protected-access
            else as_unicode(self._locals['res'])
        )

        if ct != rv:
            self.overwrite(rv)
            return False
        return True

########NEW FILE########
__FILENAME__ = _shell_code
#!/usr/bin/env python
# encoding: utf-8

"""Implements `echo hi` shell code interpolation."""

import os
import platform
from subprocess import Popen, PIPE
import stat
import tempfile

from UltiSnips.compatibility import as_unicode
from UltiSnips.text_objects._base import NoneditableTextObject

def _chomp(string):
    """Rather than rstrip(), remove only the last newline and preserve
    purposeful whitespace."""
    if len(string) and string[-1] == '\n':
        string = string[:-1]
    if len(string) and string[-1] == '\r':
        string = string[:-1]
    return string

def _run_shell_command(cmd, tmpdir):
    """Write the code to a temporary file"""
    cmdsuf = ''
    if platform.system() == 'Windows':
        # suffix required to run command on windows
        cmdsuf = '.bat'
        # turn echo off
        cmd = '@echo off\r\n' + cmd
    handle, path = tempfile.mkstemp(text=True, dir=tmpdir, suffix=cmdsuf)
    os.write(handle, cmd.encode("utf-8"))
    os.close(handle)
    os.chmod(path, stat.S_IRWXU)

    # Execute the file and read stdout
    proc = Popen(path, shell=True, stdout=PIPE, stderr=PIPE)
    proc.wait()
    stdout, _ = proc.communicate()
    os.unlink(path)
    return _chomp(as_unicode(stdout))

def _get_tmp():
    """Find an executable tmp directory."""
    userdir = os.path.expanduser("~")
    for testdir in [tempfile.gettempdir(), os.path.join(userdir, '.cache'),
            os.path.join(userdir, '.tmp'), userdir]:
        if (not os.path.exists(testdir) or
                not _run_shell_command('echo success', testdir) == 'success'):
            continue
        return testdir
    return ''

class ShellCode(NoneditableTextObject):
    """See module docstring."""

    def __init__(self, parent, token):
        NoneditableTextObject.__init__(self, parent, token)
        self._code = token.code.replace("\\`", "`")
        self._tmpdir = _get_tmp()

    def _update(self, done):
        if not self._tmpdir:
            output = \
                "Unable to find executable tmp directory, check noexec on /tmp"
        else:
            output = _run_shell_command(self._code, self._tmpdir)
        self.overwrite(output)
        self._parent._del_child(self)  # pylint:disable=protected-access
        return True

########NEW FILE########
__FILENAME__ = _snippet_instance
#!/usr/bin/env python
# encoding: utf-8

"""A Snippet instance is an instance of a Snippet Definition. That is, when the
user expands a snippet, a SnippetInstance is created to keep track of the
corresponding TextObjects. The Snippet itself is also a TextObject. """

from UltiSnips import _vim
from UltiSnips.position import Position
from UltiSnips.text_objects._base import EditableTextObject, \
        NoneditableTextObject

class SnippetInstance(EditableTextObject):
    """See module docstring."""
    # pylint:disable=protected-access

    def __init__(self, snippet, parent, initial_text,
            start, end, visual_content, last_re, globals):
        if start is None:
            start = Position(0, 0)
        if end is None:
            end = Position(0, 0)
        self.snippet = snippet
        self._cts = 0

        self.locals = {"match" : last_re}
        self.globals = globals
        self.visual_content = visual_content

        EditableTextObject.__init__(self, parent, start, end, initial_text)

    def replace_initial_text(self):
        """Puts the initial text of all text elements into Vim."""
        def _place_initial_text(obj):
            """recurses on the children to do the work."""
            obj.overwrite()
            if isinstance(obj, EditableTextObject):
                for child in obj._children:
                    _place_initial_text(child)
        _place_initial_text(self)

    def replay_user_edits(self, cmds):
        """Replay the edits the user has done to keep endings of our
        Text objects in sync with reality"""
        for cmd in cmds:
            self._do_edit(cmd)

    def update_textobjects(self):
        """Update the text objects that should change automagically after
        the users edits have been replayed. This might also move the Cursor
        """
        vc = _VimCursor(self)
        done = set()
        not_done = set()
        def _find_recursive(obj):
            """Finds all text objects and puts them into 'not_done'."""
            if isinstance(obj, EditableTextObject):
                for child in obj._children:
                    _find_recursive(child)
            not_done.add(obj)
        _find_recursive(self)

        counter = 10
        while (done != not_done) and counter:
            # Order matters for python locals!
            for obj in sorted(not_done - done):
                if obj._update(done):
                    done.add(obj)
            counter -= 1
        if not counter:
            raise RuntimeError(
                "The snippets content did not converge: Check for Cyclic "
                "dependencies or random strings in your snippet. You can use "
                "'if not snip.c' to make sure to only expand random output "
                "once.")
        vc.to_vim()
        self._del_child(vc)

    def select_next_tab(self, backwards=False):
        """Selects the next tabstop or the previous if 'backwards' is True."""
        if self._cts is None:
            return

        if backwards:
            cts_bf = self._cts

            res = self._get_prev_tab(self._cts)
            if res is None:
                self._cts = cts_bf
                return self._tabstops.get(self._cts, None)
            self._cts, ts = res
            return ts
        else:
            res = self._get_next_tab(self._cts)
            if res is None:
                self._cts = None
                return self._tabstops.get(0, None)
            else:
                self._cts, ts = res
                return ts

        return self._tabstops[self._cts]

    def _get_tabstop(self, requester, no):
        # SnippetInstances are completely self contained, therefore, we do not
        # need to ask our parent for Tabstops
        cached_parent = self._parent
        self._parent = None
        rv = EditableTextObject._get_tabstop(self, requester, no)
        self._parent = cached_parent
        return rv


class _VimCursor(NoneditableTextObject):
    """Helper class to keep track of the Vim Cursor when text objects expand
    and move."""

    def __init__(self, parent):
        NoneditableTextObject.__init__(
            self, parent, _vim.buf.cursor, _vim.buf.cursor,
            tiebreaker=Position(-1, -1))

    def to_vim(self):
        """Moves the cursor in the Vim to our position."""
        assert self._start == self._end
        _vim.buf.cursor = self._start

########NEW FILE########
__FILENAME__ = _tabstop
#!/usr/bin/env python
# encoding: utf-8

"""This is the most important TextObject. A TabStop is were the cursor
comes to rest when the user taps through the Snippet."""

from UltiSnips.text_objects._base import EditableTextObject

class TabStop(EditableTextObject):
    """See module docstring."""

    def __init__(self, parent, token, start=None, end=None):
        if start is not None:
            self._number = token
            EditableTextObject.__init__(self, parent, start, end)
        else:
            self._number = token.number
            EditableTextObject.__init__(self, parent, token)
        parent._tabstops[self._number] = self  # pylint:disable=protected-access

    @property
    def number(self):
        """The tabstop number."""
        return self._number

    @property
    def is_killed(self):
        """True if this tabstop has been typed over and the user therefore can
        no longer jump to it."""
        return self._parent is None

    def __repr__(self):
        return "TabStop(%s,%r->%r,%r)" % (self.number, self._start,
                self._end, self.current_text)

########NEW FILE########
__FILENAME__ = _transformation
#!/usr/bin/env python
# encoding: utf-8

"""Implements TabStop transformations."""

import re
import sys

from UltiSnips.text import unescape, fill_in_whitespace
from UltiSnips.text_objects._mirror import Mirror

def _find_closing_brace(string, start_pos):
    """Finds the corresponding closing brace after start_pos."""
    bracks_open = 1
    for idx, char in enumerate(string[start_pos:]):
        if char == '(':
            if string[idx+start_pos-1] != '\\':
                bracks_open += 1
        elif char == ')':
            if string[idx+start_pos-1] != '\\':
                bracks_open -= 1
            if not bracks_open:
                return start_pos+idx+1

def _split_conditional(string):
    """Split the given conditional 'string' into its arguments."""
    bracks_open = 0
    args = []
    carg = ""
    for idx, char in enumerate(string):
        if char == '(':
            if string[idx-1] != '\\':
                bracks_open += 1
        elif char == ')':
            if string[idx-1] != '\\':
                bracks_open -= 1
        elif char == ':' and not bracks_open and not string[idx-1] == '\\':
            args.append(carg)
            carg = ""
            continue
        carg += char
    args.append(carg)
    return args

def _replace_conditional(match, string):
    """Replaces a conditional match in a transformation."""
    conditional_match = _CONDITIONAL.search(string)
    while conditional_match:
        start = conditional_match.start()
        end = _find_closing_brace(string, start+4)
        args = _split_conditional(string[start+4:end-1])
        rv = ""
        if match.group(int(conditional_match.group(1))):
            rv = unescape(_replace_conditional(match, args[0]))
        elif len(args) > 1:
            rv = unescape(_replace_conditional(match, args[1]))
        string = string[:start] + rv + string[end:]
        conditional_match = _CONDITIONAL.search(string)
    return string

_ONE_CHAR_CASE_SWITCH = re.compile(r"\\([ul].)", re.DOTALL)
_LONG_CASEFOLDINGS = re.compile(r"\\([UL].*?)\\E", re.DOTALL)
_DOLLAR = re.compile(r"\$(\d+)", re.DOTALL)
_CONDITIONAL = re.compile(r"\(\?(\d+):", re.DOTALL)
class _CleverReplace(object):
    """Mimics TextMates replace syntax."""

    def __init__(self, expression):
        self._expression = expression

    def replace(self, match):
        """Replaces 'match' through the correct replacement string."""
        transformed = self._expression
        # Replace all $? with capture groups
        transformed = _DOLLAR.subn(
                lambda m: match.group(int(m.group(1))), transformed)[0]

        # Replace Case switches
        def _one_char_case_change(match):
            """Replaces one character case changes."""
            if match.group(1)[0] == 'u':
                return match.group(1)[-1].upper()
            else:
                return match.group(1)[-1].lower()
        transformed = _ONE_CHAR_CASE_SWITCH.subn(
                _one_char_case_change, transformed)[0]

        def _multi_char_case_change(match):
            """Replaces multi character case changes."""
            if match.group(1)[0] == 'U':
                return match.group(1)[1:].upper()
            else:
                return match.group(1)[1:].lower()
        transformed = _LONG_CASEFOLDINGS.subn(
                _multi_char_case_change, transformed)[0]
        transformed = _replace_conditional(match, transformed)
        return unescape(fill_in_whitespace(transformed))

# flag used to display only one time the lack of unidecode
UNIDECODE_ALERT_RAISED = False
class TextObjectTransformation(object):
    """Base class for Transformations and ${VISUAL}."""

    def __init__(self, token):
        self._convert_to_ascii = False

        self._find = None
        if token.search is None:
            return

        flags = 0
        self._match_this_many = 1
        if token.options:
            if "g" in token.options:
                self._match_this_many = 0
            if "i" in token.options:
                flags |= re.IGNORECASE
            if "a" in token.options:
                self._convert_to_ascii = True

        self._find = re.compile(token.search, flags | re.DOTALL)
        self._replace = _CleverReplace(token.replace)

    def _transform(self, text):
        """Do the actual transform on the given text."""
        global UNIDECODE_ALERT_RAISED  # pylint:disable=global-statement
        if self._convert_to_ascii:
            try:
                import unidecode
                text = unidecode.unidecode(text)
            except Exception:  # pylint:disable=broad-except
                if UNIDECODE_ALERT_RAISED == False:
                    UNIDECODE_ALERT_RAISED = True
                    sys.stderr.write(
                        "Please install unidecode python package in order to "
                        "be able to make ascii conversions.\n")
        if self._find is None:
            return text
        return self._find.subn(
                self._replace.replace, text, self._match_this_many)[0]

class Transformation(Mirror, TextObjectTransformation):
    """See module docstring."""

    def __init__(self, parent, ts, token):
        Mirror.__init__(self, parent, ts, token)
        TextObjectTransformation.__init__(self, token)

    def _get_text(self):
        return self._transform(self._ts.current_text)

########NEW FILE########
__FILENAME__ = _viml_code
#!/usr/bin/env python
# encoding: utf-8

"""Implements `!v ` VimL interpolation."""

from UltiSnips import _vim
from UltiSnips.text_objects._base import NoneditableTextObject

class VimLCode(NoneditableTextObject):
    """See module docstring."""
    def __init__(self, parent, token):
        self._code = token.code.replace("\\`", "`").strip()

        NoneditableTextObject.__init__(self, parent, token)

    def _update(self, done):
        self.overwrite(_vim.eval(self._code))
        return True

########NEW FILE########
__FILENAME__ = _visual
#!/usr/bin/env python
# encoding: utf-8

"""A ${VISUAL} placeholder that will use the text that was last visually
selected and insert it here. If there was no text visually selected, this will
be the empty string. """

import re
import textwrap

from UltiSnips import _vim
from UltiSnips.indent_util import IndentUtil
from UltiSnips.text_objects._transformation import TextObjectTransformation
from UltiSnips.text_objects._base import NoneditableTextObject

_REPLACE_NON_WS = re.compile(r"[^ \t]")
class Visual(NoneditableTextObject, TextObjectTransformation):
    """See module docstring."""

    def __init__(self, parent, token):
        # Find our containing snippet for visual_content
        snippet = parent
        while snippet:
            try:
                self._text = snippet.visual_content.text
                self._mode = snippet.visual_content.mode
                break
            except AttributeError:
                snippet = snippet._parent  # pylint:disable=protected-access
        if not self._text:
            self._text = token.alternative_text
            self._mode = "v"

        NoneditableTextObject.__init__(self, parent, token)
        TextObjectTransformation.__init__(self, token)

    def _update(self, done):
        if self._mode == "v":  # Normal selection.
            text = self._text
        else:  # Block selection or line selection.
            text_before = _vim.buf[self.start.line][:self.start.col]
            indent = _REPLACE_NON_WS.sub(" ", text_before)
            iu = IndentUtil()
            indent = iu.indent_to_spaces(indent)
            indent = iu.spaces_to_indent(indent)
            text = ""
            for idx, line in enumerate(textwrap.dedent(
                    self._text).splitlines(True)):
                if idx != 0:
                    text += indent
                text += line
            text = text[:-1] # Strip final '\n'

        text = self._transform(text)
        self.overwrite(text)
        self._parent._del_child(self)  # pylint:disable=protected-access

        return True

########NEW FILE########
__FILENAME__ = vim_state
#!/usr/bin/env python
# encoding: utf-8

"""Some classes to conserve Vim's state for comparing over time."""

from collections import deque

from UltiSnips import _vim
from UltiSnips.compatibility import as_unicode, byte2col
from UltiSnips.position import Position

class VimPosition(Position):
    """Represents the current position in the buffer, together with some status
    variables that might change our decisions down the line."""

    def __init__(self):
        pos = _vim.buf.cursor
        self._mode = _vim.eval("mode()")
        Position.__init__(self, pos.line, pos.col)

    @property
    def mode(self):
        """Returns the mode() this position was created."""
        return self._mode

class VimState(object):
    """Caches some state information from Vim to better guess what editing
    tasks the user might have done in the last step."""

    def __init__(self):
        self._poss = deque(maxlen=5)
        self._lvb = None

        self._text_to_expect = None
        self._unnamed_reg_cache = None
        self._unnamed_reg_cached = False

    def remember_unnamed_register(self, text_to_expect):
        """Save the unnamed register. 'text_to_expect' is text that we expect
        to be contained in the register the next time this method is called -
        this could be text from the tabstop that was selected and might have
        been overwritten. We will not cash that then."""
        self._unnamed_reg_cached = True
        unnamed_reg = _vim.eval('@"')
        if unnamed_reg != self._text_to_expect:
            self._unnamed_reg_cache = unnamed_reg
        self._text_to_expect = text_to_expect

    def restore_unnamed_register(self):
        """Restores the unnamed register and forgets what we cached."""
        if not self._unnamed_reg_cached:
            return
        escaped_cache = self._unnamed_reg_cache.replace("'", "''")
        _vim.command("let @\"='%s'" % escaped_cache)
        self._unnamed_reg_cached = False

    def remember_position(self):
        """Remember the current position as a previous pose."""
        self._poss.append(VimPosition())

    def remember_buffer(self, to):
        """Remember the content of the buffer and the position."""
        self._lvb = _vim.buf[to.start.line:to.end.line+1]
        self._lvb_len = len(_vim.buf)
        self.remember_position()

    @property
    def diff_in_buffer_length(self):
        """Returns the difference in the length of the current buffer compared
        to the remembered."""
        return len(_vim.buf) - self._lvb_len

    @property
    def pos(self):
        """The last remembered position."""
        return self._poss[-1]

    @property
    def ppos(self):
        """The second to last remembered position."""
        return self._poss[-2]

    @property
    def remembered_buffer(self):
        """The content of the remembered buffer."""
        return self._lvb[:]

class VisualContentPreserver(object):
    """Saves the current visual selection and the selection mode it was done in
    (e.g. line selection, block selection or regular selection.)"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Forget the preserved state."""
        self._mode = ""
        self._text = as_unicode("")

    def conserve(self):
        """Save the last visual selection ond the mode it was made in."""
        sl, sbyte = map(int,
                (_vim.eval("""line("'<")"""), _vim.eval("""col("'<")""")))
        el, ebyte = map(int,
                (_vim.eval("""line("'>")"""), _vim.eval("""col("'>")""")))
        sc = byte2col(sl, sbyte - 1)
        ec = byte2col(el, ebyte - 1)
        self._mode = _vim.eval("visualmode()")

        _vim_line_with_eol = lambda ln: _vim.buf[ln] + '\n'

        if sl == el:
            text = _vim_line_with_eol(sl-1)[sc:ec+1]
        else:
            text = _vim_line_with_eol(sl-1)[sc:]
            for cl in range(sl, el-1):
                text += _vim_line_with_eol(cl)
            text += _vim_line_with_eol(el-1)[:ec+1]
        self._text = text

    @property
    def text(self):
        """The conserved text."""
        return self._text

    @property
    def mode(self):
        """The conserved visualmode()."""
        return self._mode

########NEW FILE########
__FILENAME__ = _diff
#!/usr/bin/env python
# encoding: utf-8

"""Commands to compare text objects and to guess how to transform from one to
another."""

from collections import defaultdict
import sys

from UltiSnips import _vim
from UltiSnips.position import Position

def is_complete_edit(initial_line, original, wanted, cmds):
    """Returns true if 'original' is changed to 'wanted' with the edit commands
    in 'cmds'. Initial line is to change the line numbers in 'cmds'."""
    buf = original[:]
    for cmd in cmds:
        ctype, line, col, char = cmd
        line -= initial_line
        if ctype == "D":
            if char != '\n':
                buf[line] = buf[line][:col] + buf[line][col+len(char):]
            else:
                if line + 1 < len(buf):
                    buf[line] = buf[line] + buf[line+1]
                    del buf[line+1]
                else:
                    del buf[line]
        elif ctype == "I":
            buf[line] = buf[line][:col] + char + buf[line][col:]
        buf = '\n'.join(buf).split('\n')
    return (len(buf) == len(wanted) and
            all(j == k for j, k in zip(buf, wanted)))

def guess_edit(initial_line, last_text, current_text, vim_state):
    """
    Try to guess what the user might have done by heuristically looking at
    cursor movement, number of changed lines and if they got longer or shorter.
    This will detect most simple movements like insertion, deletion of a line
    or carriage return. 'initial_text' is the index of where the comparison
    starts, 'last_text' is the last text of the snippet, 'current_text' is the
    current text of the snippet and 'vim_state' is the cached vim state.

    Returns (True, edit_cmds) when the edit could be guessed, (False, None)
    otherwise.
    """
    if not len(last_text) and not len(current_text):
        return True, ()
    pos = vim_state.pos
    ppos = vim_state.ppos

    # All text deleted?
    if (len(last_text) and
            (not current_text or
             (len(current_text) == 1 and not current_text[0]))
    ):
        es = []
        if not current_text:
            current_text = ['']
        for i in last_text:
            es.append(("D", initial_line, 0, i))
            es.append(("D", initial_line, 0, "\n"))
        es.pop() # Remove final \n because it is not really removed
        if is_complete_edit(initial_line, last_text, current_text, es):
            return True, es
    if ppos.mode == 'v': # Maybe selectmode?
        sv = list(map(int, _vim.eval("""getpos("'<")""")))
        sv = Position(sv[1]-1, sv[2]-1)
        ev = list(map(int, _vim.eval("""getpos("'>")""")))
        ev = Position(ev[1]-1, ev[2]-1)
        if "exclusive" in _vim.eval("&selection"):
            ppos.col -= 1 # We want to be inclusive, sorry.
            ev.col -= 1
        es = []
        if sv.line == ev.line:
            es.append(("D", sv.line, sv.col,
                last_text[sv.line - initial_line][sv.col:ev.col+1]))
            if sv != pos and sv.line == pos.line:
                es.append(("I", sv.line, sv.col,
                    current_text[sv.line - initial_line][sv.col:pos.col+1]))
        if is_complete_edit(initial_line, last_text, current_text, es):
            return True, es
    if pos.line == ppos.line:
        if len(last_text) == len(current_text): # Movement only in one line
            llen = len(last_text[ppos.line - initial_line])
            clen = len(current_text[pos.line - initial_line])
            if ppos < pos and clen > llen: # maybe only chars have been added
                es = (
                    ("I", ppos.line, ppos.col,
                        current_text[ppos.line - initial_line]
                            [ppos.col:pos.col]),
                )
                if is_complete_edit(initial_line, last_text, current_text, es):
                    return True, es
            if clen < llen:
                if ppos == pos: # 'x' or DEL or dt or something
                    es = (
                        ("D", pos.line, pos.col,
                            last_text[ppos.line - initial_line]
                                [ppos.col:ppos.col + (llen - clen)]),
                    )
                    if is_complete_edit(initial_line, last_text,
                            current_text, es):
                        return True, es
                if pos < ppos: # Backspacing or dT dF?
                    es = (
                        ("D", pos.line, pos.col,
                            last_text[pos.line - initial_line]
                                [pos.col:pos.col + llen - clen]),
                    )
                    if is_complete_edit(initial_line, last_text,
                            current_text, es):
                        return True, es
        elif len(current_text) < len(last_text):
           # where some lines deleted? (dd or so)
            es = []
            for i in range(len(last_text)-len(current_text)):
                es.append(("D", pos.line, 0,
                    last_text[pos.line - initial_line + i]))
                es.append(("D", pos.line, 0, '\n'))
            if is_complete_edit(initial_line, last_text,
                    current_text, es):
                return True, es
    else:
        # Movement in more than one line
        if ppos.line + 1 == pos.line and pos.col == 0: # Carriage return?
            es = (("I", ppos.line, ppos.col, "\n"),)
            if is_complete_edit(initial_line, last_text,
                    current_text, es):
                return True, es
    return False, None

def diff(a, b, sline=0):
    """
    Return a list of deletions and insertions that will turn 'a' into 'b'. This
    is done by traversing an implicit edit graph and searching for the shortest
    route. The basic idea is as follows:

        - Matching a character is free as long as there was no
          deletion/insertion before. Then, matching will be seen as delete +
          insert [1].
        - Deleting one character has the same cost everywhere. Each additional
          character costs only have of the first deletion.
        - Insertion is cheaper the earlier it happens. The first character is
          more expensive that any later [2].

    [1] This is that world -> aolsa will be "D" world + "I" aolsa instead of
        "D" w , "D" rld, "I" a, "I" lsa
    [2] This is that "hello\n\n" -> "hello\n\n\n" will insert a newline after
        hello and not after \n
    """
    d = defaultdict(list)  # pylint:disable=invalid-name
    seen = defaultdict(lambda: sys.maxsize)

    d[0] = [(0, 0, sline, 0, ())]
    cost = 0
    deletion_cost = len(a)+len(b)
    insertion_cost = len(a)+len(b)
    while True:
        while len(d[cost]):
            x, y, line, col, what = d[cost].pop()

            if a[x:] == b[y:]:
                return what

            if x < len(a) and y < len(b) and a[x] == b[y]:
                ncol = col + 1
                nline = line
                if a[x] == '\n':
                    ncol = 0
                    nline += 1
                lcost = cost + 1
                if (what and what[-1][0] == "D" and what[-1][1] == line and
                        what[-1][2] == col and a[x] != '\n'):
                    # Matching directly after a deletion should be as costly as
                    # DELETE + INSERT + a bit
                    lcost = (deletion_cost + insertion_cost)*1.5
                if seen[x+1, y+1] > lcost:
                    d[lcost].append((x+1, y+1, nline, ncol, what))
                    seen[x+1, y+1] = lcost
            if y < len(b): # INSERT
                ncol = col + 1
                nline = line
                if b[y] == '\n':
                    ncol = 0
                    nline += 1
                if (what and what[-1][0] == "I" and what[-1][1] == nline and
                    what[-1][2]+len(what[-1][-1]) == col and b[y] != '\n' and
                    seen[x, y+1] > cost + (insertion_cost + ncol) // 2
                ):
                    seen[x, y+1] = cost + (insertion_cost + ncol) // 2
                    d[cost + (insertion_cost + ncol) // 2].append(
                        (x, y+1, line, ncol, what[:-1] + (
                            ("I", what[-1][1], what[-1][2],
                             what[-1][-1] + b[y]),)
                        )
                    )
                elif seen[x, y+1] > cost + insertion_cost + ncol:
                    seen[x, y+1] = cost + insertion_cost + ncol
                    d[cost + ncol + insertion_cost].append((x, y+1, nline, ncol,
                        what + (("I", line, col, b[y]),))
                    )
            if x < len(a): # DELETE
                if (what and what[-1][0] == "D" and what[-1][1] == line and
                    what[-1][2] == col and a[x] != '\n' and
                    what[-1][-1] != '\n' and
                    seen[x+1, y] > cost + deletion_cost // 2
                ):
                    seen[x+1, y] = cost + deletion_cost // 2
                    d[cost + deletion_cost // 2].append(
                        (x+1, y, line, col, what[:-1] + (
                            ("D", line, col, what[-1][-1] + a[x]),))
                    )
                elif seen[x+1, y] > cost + deletion_cost:
                    seen[x+1, y] = cost + deletion_cost
                    d[cost + deletion_cost].append((x+1, y, line, col, what +
                        (("D", line, col, a[x]),))
                    )
        cost += 1

########NEW FILE########
__FILENAME__ = _vim
#!/usr/bin/env python
# encoding: utf-8

"""Wrapper functionality around the functions we need from Vim."""

import re

import vim  # pylint:disable=import-error
from vim import error  # pylint:disable=import-error,unused-import

from UltiSnips.compatibility import col2byte, byte2col, \
        as_unicode, as_vimencoding
from UltiSnips.position import Position

class VimBuffer(object):
    """Wrapper around the current Vim buffer."""

    def __getitem__(self, idx):
        if isinstance(idx, slice): # Py3
            return self.__getslice__(idx.start, idx.stop)
        rv = vim.current.buffer[idx]
        return as_unicode(rv)

    def __getslice__(self, i, j): # pylint:disable=no-self-use
        rv = vim.current.buffer[i:j]
        return [as_unicode(l) for l in rv]

    def __setitem__(self, idx, text):
        if isinstance(idx, slice): # Py3
            return self.__setslice__(idx.start, idx.stop, text)
        vim.current.buffer[idx] = as_vimencoding(text)

    def __setslice__(self, i, j, text): # pylint:disable=no-self-use
        vim.current.buffer[i:j] = [as_vimencoding(l) for l in text]

    def __len__(self):
        return len(vim.current.buffer)

    @property
    def line_till_cursor(self): # pylint:disable=no-self-use
        """Returns the text before the cursor."""
        # Note: we want byte position here
        _, col = vim.current.window.cursor
        line = vim.current.line
        before = as_unicode(line[:col])
        return before

    @property
    def number(self): # pylint:disable=no-self-use
        """The bufnr() of this buffer."""
        return int(eval("bufnr('%')"))

    @property
    def cursor(self): # pylint:disable=no-self-use
        """
        The current windows cursor. Note that this is 0 based in col and 0
        based in line which is different from Vim's cursor.
        """
        line, nbyte = vim.current.window.cursor
        col = byte2col(line, nbyte)
        return Position(line - 1, col)

    @cursor.setter
    def cursor(self, pos): # pylint:disable=no-self-use
        """See getter."""
        nbyte = col2byte(pos.line + 1, pos.col)
        vim.current.window.cursor = pos.line + 1, nbyte
buf = VimBuffer()  # pylint:disable=invalid-name

def escape(inp):
    """Creates a vim-friendly string from a group of
    dicts, lists and strings."""
    def conv(obj):
        """Convert obj."""
        if isinstance(obj, list):
            rv = as_unicode('[' + ','.join(conv(o) for o in obj) + ']')
        elif isinstance(obj, dict):
            rv = as_unicode('{' + ','.join([
                "%s:%s" % (conv(key), conv(value))
                for key, value in obj.iteritems()]) + '}')
        else:
            rv = as_unicode('"%s"') % as_unicode(obj).replace('"', '\\"')
        return rv
    return conv(inp)

def command(cmd):
    """Wraps vim.command."""
    return as_unicode(vim.command(as_vimencoding(cmd)))

def eval(text):
    """Wraps vim.eval."""
    rv = vim.eval(as_vimencoding(text))
    if not isinstance(rv, (dict, list)):
        return as_unicode(rv)
    return rv

def feedkeys(keys, mode='n'):
    """Wrapper around vim's feedkeys function. Mainly for convenience."""
    command(as_unicode(r'call feedkeys("%s", "%s")') % (keys, mode))

def new_scratch_buffer(text):
    """Create a new scratch buffer with the text given"""
    vim.command("botright new")
    vim.command("set ft=")
    vim.command("set buftype=nofile")

    vim.current.buffer[:] = text.splitlines()

    feedkeys(r"\<Esc>")

def virtual_position(line, col):
    """Runs the position through virtcol() and returns the result."""
    nbytes = col2byte(line, col)
    return line, int(eval('virtcol([%d, %d])' % (line, nbytes)))

def select(start, end):
    """Select the span in Select mode"""
    _unmap_select_mode_mapping()

    selection = eval("&selection")

    col = col2byte(start.line + 1, start.col)
    vim.current.window.cursor = start.line + 1, col

    move_cmd = ""
    if eval("mode()") != 'n':
        move_cmd += r"\<Esc>"

    if start == end:
        # Zero Length Tabstops, use 'i' or 'a'.
        if col == 0 or eval("mode()") not in 'i' and \
                col < len(buf[start.line]):
            move_cmd += "i"
        else:
            move_cmd += "a"
    else:
        # Non zero length, use Visual selection.
        move_cmd += "v"
        if "inclusive" in selection:
            if end.col == 0:
                move_cmd += "%iG$" % end.line
            else:
                move_cmd += "%iG%i|" % virtual_position(end.line + 1, end.col)
        elif "old" in selection:
            move_cmd += "%iG%i|" % virtual_position(end.line + 1, end.col)
        else:
            move_cmd += "%iG%i|" % virtual_position(end.line + 1, end.col + 1)
        move_cmd += "o%iG%i|o\\<c-g>" % virtual_position(
                start.line + 1, start.col + 1)
    feedkeys(_LangMapTranslator().translate(move_cmd))

def _unmap_select_mode_mapping():
    """This function unmaps select mode mappings if so wished by the user.
    Removes select mode mappings that can actually be typed by the user
    (ie, ignores things like <Plug>).
    """
    if int(eval("g:UltiSnipsRemoveSelectModeMappings")):
        ignores = eval("g:UltiSnipsMappingsToIgnore") + ['UltiSnips']

        for option in ("<buffer>", ""):
            # Put all smaps into a var, and then read the var
            command(r"redir => _tmp_smaps | silent smap %s " % option +
                        "| redir END")

            # Check if any mappings where found
            all_maps = list(filter(len, eval(r"_tmp_smaps").splitlines()))
            if len(all_maps) == 1 and all_maps[0][0] not in " sv":
                # "No maps found". String could be localized. Hopefully
                # it doesn't start with any of these letters in any
                # language
                continue

            # Only keep mappings that should not be ignored
            maps = [m for m in all_maps if
                        not any(i in m for i in ignores) and len(m.strip())]

            for map in maps:
                # The first three chars are the modes, that might be listed.
                # We are not interested in them here.
                trig = map[3:].split()[0] if len(map[3:].split()) != 0 else None

                if trig is None:
                    continue

                # The bar separates commands
                if trig[-1] == "|":
                    trig = trig[:-1] + "<Bar>"

                # Special ones
                if trig[0] == "<":
                    add = False
                    # Only allow these
                    for valid in ["Tab", "NL", "CR", "C-Tab", "BS"]:
                        if trig == "<%s>" % valid:
                            add = True
                    if not add:
                        continue

                # UltiSnips remaps <BS>. Keep this around.
                if trig == "<BS>":
                    continue

                # Actually unmap it
                try:
                    command("silent! sunmap %s %s" % (option, trig))
                except:  # pylint:disable=bare-except
                    # Bug 908139: ignore unmaps that fail because of
                    # unprintable characters. This is not ideal because we
                    # will not be able to unmap lhs with any unprintable
                    # character. If the lhs stats with a printable
                    # character this will leak to the user when he tries to
                    # type this character as a first in a selected tabstop.
                    # This case should be rare enough to not bother us
                    # though.
                    pass

class _RealLangMapTranslator(object):
    """This cares for the Vim langmap option and basically reverses the
    mappings. This was the only solution to get UltiSnips to work nicely with
    langmap; other stuff I tried was using inoremap movement commands and
    caching and restoring the langmap option.

    Note that this will not work if the langmap overwrites a character
    completely, for example if 'j' is remapped, but nothing is mapped back to
    'j', then moving one line down is no longer possible and UltiSnips will
    fail.
    """
    _maps = {}
    _SEMICOLONS = re.compile(r"(?<!\\);")
    _COMMA = re.compile(r"(?<!\\),")

    def _create_translation(self, langmap):
        """Create the reverse mapping from 'langmap'."""
        from_chars, to_chars = "", ""
        for char in self._COMMA.split(langmap):
            char = char.replace("\\,", ",")
            res = self._SEMICOLONS.split(char)
            if len(res) > 1:
                from_char, to_char = [a.replace("\\;", ";") for a in res]
                from_chars += from_char
                to_chars += to_char
            else:
                from_chars += char[::2]
                to_chars += char[1::2]
        self._maps[langmap] = (from_chars, to_chars)

    def translate(self, text):
        """Inverse map 'text' through langmap."""
        langmap = eval("&langmap").strip()
        if langmap == "":
            return text
        text = as_unicode(text)
        if langmap not in self._maps:
            self._create_translation(langmap)
        for before, after in zip(*self._maps[langmap]):
            text = text.replace(before, after)
        return text

class _DummyLangMapTranslator(object):
    """If vim hasn't got the langmap compiled in, we never have to do anything.
    Then this class is used. """
    translate = lambda self, s: s

_LangMapTranslator = _RealLangMapTranslator
if not int(eval('has("langmap")')):
    _LangMapTranslator = _DummyLangMapTranslator

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# encoding: utf-8
#
# To execute this test requires two terminals, one for running Vim and one
# for executing the test script. Both terminals should have their current
# working directories set to this directory (the one containing this test.py
# script).
#
# In one terminal, launch a GNU ``screen`` session named ``vim``:
#   $ screen -S vim
#
# Now, from another terminal, launch the testsuite:
#    $ ./test.py
#
# For each test, the test.py script will launch vim with a vimrc, run the test,
# compare the output and exit vim again. The keys are send using screen.
#
# NOTE: The tessuite is not working under Windows right now as I have no access
# to a windows system for fixing it. Volunteers welcome. Here are some comments
# from the last time I got the test suite running under windows.
#
# Under windows, COM's SendKeys is used to send keystrokes to the gvim window.
# Note that Gvim must use english keyboard input (choose in windows registry)
# for this to work properly as SendKeys is a piece of chunk. (i.e. it sends
# <F13> when you send a | symbol while using german key mappings)

# pylint: skip-file

from textwrap import dedent
import os
import platform
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import time
import unittest

try:
    import unidecode
    UNIDECODE_IMPORTED = True
except ImportError:
    UNIDECODE_IMPORTED = False

# Some constants for better reading
BS = '\x7f'
ESC = '\x1b'
ARR_L = '\x1bOD'
ARR_R = '\x1bOC'
ARR_U = '\x1bOA'
ARR_D = '\x1bOB'

# multi-key sequences generating a single key press
SEQUENCES = [ARR_L, ARR_R, ARR_U, ARR_D]

# Defined Constants
JF = "?" # Jump forwards
JB = "+" # Jump backwards
LS = "@" # List snippets
EX = "\t" # EXPAND
EA = "#" # Expand anonymous

COMPL_KW = chr(24)+chr(14)
COMPL_ACCEPT = chr(25)

PYTHON3 = sys.version_info >= (3,0)

def running_on_windows():
    if platform.system() == "Windows":
        return "Does not work on Windows."

def python3():
    if PYTHON3:
        return "Test does not work on python3."

def no_unidecode_available():
    if not UNIDECODE_IMPORTED:
        return "unidecode is not available."

def is_process_running(pid):
    """Returns true if a process with pid is running, false otherwise."""
    # from http://stackoverflow.com/questions/568271/how-to-check-if-there-exists-a-process-with-a-given-pid
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def silent_call(cmd):
    """Calls 'cmd' and returns the exit value."""
    return subprocess.call(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def create_directory(dirname):
    """Creates 'dirname' and its parents if it does not exist."""
    try:
        os.makedirs(dirname)
    except OSError:
        pass

def plugin_cache_dir():
    """The directory that we check out our bundles to."""
    return os.path.join(tempfile.gettempdir(), "UltiSnips_test_vim_plugins")

def clone_plugin(plugin):
    """Clone the given plugin into our plugin directory."""
    dirname = os.path.join(plugin_cache_dir(), os.path.basename(plugin))
    print("Cloning %s -> %s" % (plugin, dirname))
    if os.path.exists(dirname):
        print("Skip cloning of %s. Already there." % plugin)
        return
    create_directory(dirname)
    subprocess.call(["git", "clone", "--recursive",
        "--depth", "1", "https://github.com/%s" % plugin, dirname])

    if plugin == "Valloric/YouCompleteMe":
        ## CLUTCH: this plugin needs something extra.
        subprocess.call(os.path.join(dirname, "./install.sh"), cwd=dirname)

def setup_other_plugins(all_plugins):
    """Creates /tmp/UltiSnips_test_vim_plugins and clones all plugins into this."""
    clone_plugin("tpope/vim-pathogen")
    for plugin in all_plugins:
        clone_plugin(plugin)

def read_text_file(filename):
    """Reads the contens of a text file."""
    if PYTHON3:
        return open(filename,"r", encoding="utf-8").read()
    else:
        return open(filename,"r").read()

def random_string(n):
    return ''.join(random.choice(string.ascii_lowercase) for x in range(n))

class VimInterface(object):
    def get_buffer_data(self):
        handle, fn = tempfile.mkstemp(prefix="UltiSnips_Test",suffix=".txt")
        os.close(handle)
        os.unlink(fn)

        self.send(ESC + ":w! %s\n" % fn)

        # Read the output, chop the trailing newline
        tries = 50
        while tries:
            if os.path.exists(fn):
                return read_text_file(fn)[:-1]
            time.sleep(.01)
            tries -= 1

class VimInterfaceScreen(VimInterface):
    def __init__(self, session):
        self.session = session
        self.need_screen_escapes = 0
        self.detect_parsing()

    def send(self, s):
        if self.need_screen_escapes:
            # escape characters that are special to some versions of screen
            repl = lambda m: '\\' + m.group(0)
            s = re.sub( r"[$^#\\']", repl, s )

        if PYTHON3:
            s = s.encode("utf-8")

        while True:
            rv = 0
            if len(s) > 30:
                rv |= silent_call(["screen", "-x", self.session, "-X", "register", "S", s])
                rv |= silent_call(["screen", "-x", self.session, "-X", "paste", "S"])
            else:
                rv |= silent_call(["screen", "-x", self.session, "-X", "stuff", s])
            if not rv: break
            time.sleep(.2)

    def detect_parsing(self):
        self.send(""" vim -u NONE\r\n""")  # Space to exclude from shell history
        time.sleep(1)

        # Send a string where the interpretation will depend on version of screen
        string = "$TERM"
        self.send("i" + string + ESC)
        output = self.get_buffer_data()
        # If the output doesn't match the input, need to do additional escaping
        if output != string:
            self.need_screen_escapes = 1
        self.send(ESC + ":q!\n")

class VimInterfaceTmux(VimInterface):
    def __init__(self, session):
        self.session = session
        self._check_version()

    def send(self, s):
        # I did not find any documentation on what needs escaping when sending
        # to tmux, but it seems like this is all that is needed for now.
        s = s.replace(';', r'\;')

        if PYTHON3:
            s = s.encode("utf-8")
        silent_call(["tmux", "send-keys", "-t", self.session, "-l", s])

    def _check_version(self):
        stdout, _ = subprocess.Popen(["tmux", "-V"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if PYTHON3:
            stdout = stdout.decode("utf-8")
        m = re.match(r"tmux (\d+).(\d+)", stdout)
        if not m or not (int(m.group(1)), int(m.group(2))) >= (1, 9):
            raise RuntimeError("Need at least tmux 1.9, you have %s." % stdout.strip())

class VimInterfaceWindows(VimInterface):
    BRACES = re.compile("([}{])")
    WIN_ESCAPES = ["+", "^", "%", "~", "[", "]", "<", ">", "(", ")"]
    WIN_REPLACES = [
            (BS, "{BS}"),
            (ARR_L, "{LEFT}"),
            (ARR_R, "{RIGHT}"),
            (ARR_U, "{UP}"),
            (ARR_D, "{DOWN}"),
            ("\t", "{TAB}"),
            ("\n", "~"),
            (ESC, "{ESC}"),

            # On my system ` waits for a second keystroke, so `+SPACE = "`".  On
            # most systems, `+Space = "` ". I work around this, by sending the host
            # ` as `+_+BS. Awkward, but the only way I found to get this working.
            ("`", "`_{BS}"),
            ("´", "´_{BS}"),
            ("{^}", "{^}_{BS}"),
    ]

    def __init__(self):
        self.seq_buf = []
        # import windows specific modules
        import win32com.client, win32gui
        self.win32gui = win32gui
        self.shell = win32com.client.Dispatch("WScript.Shell")

    def is_focused(self, title=None):
        cur_title = self.win32gui.GetWindowText(self.win32gui.GetForegroundWindow())
        if (title or "- GVIM") in cur_title:
            return True
        return False

    def focus(self, title=None):
        if not self.shell.AppActivate(title or "- GVIM"):
            raise Exception("Failed to switch to GVim window")
        time.sleep(1)

    def convert_keys(self, keys):
        keys = self.BRACES.sub(r"{\1}", keys)
        for k in self.WIN_ESCAPES:
            keys = keys.replace(k, "{%s}" % k)
        for f, r in self.WIN_REPLACES:
            keys = keys.replace(f, r)
        return keys

    def send(self, keys):
        self.seq_buf.append(keys)
        seq = "".join(self.seq_buf)

        for f in SEQUENCES:
            if f.startswith(seq) and f != seq:
                return
        self.seq_buf = []

        seq = self.convert_keys(seq)

        if not self.is_focused():
            time.sleep(2)
            self.focus()
        if not self.is_focused():
            # This is the only way I can find to stop test execution
            raise KeyboardInterrupt("Failed to focus GVIM")

        self.shell.SendKeys(seq)

def create_temp_file(prefix, suffix, content):
    """Create a file in a temporary place with the given 'prefix'
    and the given 'suffix' containing 'content'. The file is never
    deleted. Returns the name of the temporary file."""
    with tempfile.NamedTemporaryFile(
        prefix=prefix, suffix=suffix, delete=False
    ) as temporary_file:
        if PYTHON3:
            s = s.encode("utf-8")
        temporary_file.write(content)
        temporary_file.close()
        return temporary_file.name

class _VimTest(unittest.TestCase):
    snippets = ()
    files = {}
    text_before = " --- some text before --- \n\n"
    text_after =  "\n\n --- some text after --- "
    expected_error = ""
    wanted = ""
    keys = ""
    sleeptime = 0.00
    output = ""
    plugins = []
    # Skip this test for the given reason or None for not skipping it.
    skip_if = lambda self: None
    version = None  # Will be set to vim --version output

    def runTest(self):
        # Only checks the output. All work is done in setUp().
        wanted = self.text_before + self.wanted + self.text_after
        if self.expected_error:
            self.assertRegexpMatches(self.output, self.expected_error)
            return
        for i in range(self.retries):
            if self.output != wanted:
                # Redo this, but slower
                self.sleeptime += 0.02
                self.tearDown()
                self.setUp()
        self.assertEqual(self.output, wanted)

    def _extra_options_pre_init(self, vim_config):
        """Adds extra lines to the vim_config list."""

    def _extra_options_post_init(self, vim_config):
        """Adds extra lines to the vim_config list."""

    def _before_test(self):
        """Send these keys before the test runs. Used for buffer local
        variables and other options."""
        return ""

    def _create_file(self, file_path, content):
        """Creates a file in the runtimepath that is created for this test.
        Returns the absolute path to the file."""
        abs_path = os.path.join(self._temporary_directory, *file_path.split("/"))
        create_directory(os.path.dirname(abs_path))

        content = dedent(content + "\n")
        if PYTHON3:
            with open(abs_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(content)
        else:
            with open(abs_path, "w") as file_handle:
                file_handle.write(content)
        return abs_path

    def _link_file(self, source, relative_destination):
        """Creates a link from 'source' to the 'relative_destination' in our temp dir."""
        absdir = os.path.join(self._temporary_directory, relative_destination)
        create_directory(absdir)
        os.symlink(source, os.path.join(absdir, os.path.basename(source)))

    def setUp(self):
        if not _VimTest.version:
            _VimTest.version, _ = subprocess.Popen(["vim", "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            if PYTHON3:
                _VimTest.version = _VimTest.version.decode("utf-8")

        if self.plugins and not self.test_plugins:
            return self.skipTest("Not testing integration with other plugins.")
        reason_for_skipping = self.skip_if()
        if reason_for_skipping is not None:
            return self.skipTest(reason_for_skipping)

        self._temporary_directory = tempfile.mkdtemp(prefix="UltiSnips_Test")

        vim_config = []
        vim_config.append('set nocompatible')
        vim_config.append('set runtimepath=$VIMRUNTIME,.,%s' % self._temporary_directory)

        if self.plugins:
            self._link_file(os.path.join(plugin_cache_dir(), "vim-pathogen", "autoload"), ".")
            for plugin in self.plugins:
                self._link_file(os.path.join(plugin_cache_dir(), os.path.basename(plugin)), "bundle")
            vim_config.append("execute pathogen#infect()")

        # Vim parameters.
        vim_config.append('syntax on')
        vim_config.append('filetype plugin indent on')
        vim_config.append('set clipboard=""')
        vim_config.append('set encoding=utf-8')
        vim_config.append('set fileencoding=utf-8')
        vim_config.append('set buftype=nofile')
        vim_config.append('set shortmess=at')
        vim_config.append('let g:UltiSnipsExpandTrigger="<tab>"')
        vim_config.append('let g:UltiSnipsJumpForwardTrigger="?"')
        vim_config.append('let g:UltiSnipsJumpBackwardTrigger="+"')
        vim_config.append('let g:UltiSnipsListSnippets="@"')
        vim_config.append('let g:UltiSnipsUsePythonVersion="%i"' % (3 if PYTHON3 else 2))
        vim_config.append('let g:UltiSnipsSnippetDirectories=["us"]')

        self._extra_options_pre_init(vim_config)

        # Now activate UltiSnips.
        vim_config.append('call UltiSnips#bootstrap#Bootstrap()')

        self._extra_options_post_init(vim_config)

        # Finally, add the snippets and some configuration for the test.
        vim_config.append("%s << EOF" % ("py3" if PYTHON3 else "py"))

        if len(self.snippets) and not isinstance(self.snippets[0],tuple):
            self.snippets = ( self.snippets, )
        for s in self.snippets:
            sv, content = s[:2]
            description = ""
            options = ""
            priority = 0
            if len(s) > 2:
                description = s[2]
            if len(s) > 3:
                options = s[3]
            if len(s) > 4:
                priority = s[4]
            vim_config.append("UltiSnips_Manager.add_snippet(%r, %r, %r, %r, priority=%i)" % (
                    sv, content, description, options, priority))

        # fill buffer with default text and place cursor in between.
        prefilled_text = (self.text_before + self.text_after).splitlines()
        vim_config.append("vim.current.buffer[:] = %r\n" % prefilled_text)
        vim_config.append("vim.current.window.cursor = (max(len(vim.current.buffer)//2, 1), 0)")

        # Create a file to signalize to the test runner that we are done with starting Vim.
        vim_pid_file = os.path.join(self._temporary_directory, "vim.pid")
        done_file = os.path.join(self._temporary_directory, "loading_done")
        vim_config.append("with open('%s', 'w') as pid_file: pid_file.write(vim.eval('getpid()'))" %
                vim_pid_file)
        vim_config.append("with open('%s', 'w') as done_file: pass" % done_file)

        # End of python stuff.
        vim_config.append("EOF")

        for name, content in self.files.items():
            self._create_file(name, content)

        # Now launch Vim.
        self._create_file("vim_config.vim", os.linesep.join(vim_config))
        # Note the shell to exclude it from shell history.
        self.vim.send(""" vim -u %s\r\n""" % os.path.join(
            self._temporary_directory, "vim_config.vim"))
        while True:
            if os.path.exists(done_file):
                self._vim_pid = int(open(vim_pid_file, "r").read())
                break
            time.sleep(.01)

        self._before_test()

        if not self.interrupt:
            # Go into insert mode and type the keys but leave Vim some time to
            # react.
            for c in 'i' + self.keys:
                self.vim.send(c)
                time.sleep(self.sleeptime)
            self.output = self.vim.get_buffer_data()

    def tearDown(self):
        if self.interrupt:
            print("Working directory: %s" % (self._temporary_directory))
            return
        shutil.rmtree(self._temporary_directory)
        self.vim.send(3*ESC + ":qa!\n")
        while is_process_running(self._vim_pid):
            time.sleep(.05)

###########################################################################
#                            BEGINNING OF TEST                            #
###########################################################################
# Snippet Definition Parsing  {{{#
class ParseSnippets_SimpleSnippet(_VimTest):
    files = { "us/all.snippets": r"""
        snippet testsnip "Test Snippet" b!
        This is a test snippet!
        endsnippet
        """}
    keys = "testsnip" + EX
    wanted = "This is a test snippet!"

class ParseSnippets_MissingEndSnippet(_VimTest):
    files = { "us/all.snippets": r"""
        snippet testsnip "Test Snippet" b!
        This is a test snippet!
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = r"Missing 'endsnippet' for 'testsnip' in \S+:4"

class ParseSnippets_UnknownDirective(_VimTest):
    files = { "us/all.snippets": r"""
        unknown directive
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = r"Invalid line 'unknown directive' in \S+:2"

class ParseSnippets_InvalidPriorityLine(_VimTest):
    files = { "us/all.snippets": r"""
        priority - 50
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = r"Invalid priority '- 50' in \S+:2"

class ParseSnippets_InvalidPriorityLine1(_VimTest):
    files = { "us/all.snippets": r"""
        priority
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = r"Invalid priority '' in \S+:2"

class ParseSnippets_ExtendsWithoutFiletype(_VimTest):
    files = { "us/all.snippets": r"""
        extends
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX
    expected_error = r"'extends' without file types in \S+:2"

class ParseSnippets_ClearAll(_VimTest):
    files = { "us/all.snippets": r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        clearsnippets
        """}
    keys = "testsnip" + EX
    wanted = "testsnip" + EX

class ParseSnippets_ClearOne(_VimTest):
    files = { "us/all.snippets": r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        snippet toclear "Snippet to clear"
        Do not expand.
        endsnippet

        clearsnippets toclear
        """}
    keys = "toclear" + EX + "\n" + "testsnip" + EX
    wanted = "toclear" + EX + "\n" + "This is a test."

class ParseSnippets_ClearTwo(_VimTest):
    files = { "us/all.snippets": r"""
        snippet testsnip "Test snippet"
        This is a test.
        endsnippet

        snippet toclear "Snippet to clear"
        Do not expand.
        endsnippet

        clearsnippets testsnip toclear
        """}
    keys = "toclear" + EX + "\n" + "testsnip" + EX
    wanted = "toclear" + EX + "\n" + "testsnip" + EX


class _ParseSnippets_MultiWord(_VimTest):
    files = { "us/all.snippets": r"""
        snippet /test snip/
        This is a test.
        endsnippet

        snippet !snip test! "Another snippet"
        This is another test.
        endsnippet

        snippet "snippet test" "Another snippet" b
        This is yet another test.
        endsnippet
        """}
class ParseSnippets_MultiWord_Simple(_ParseSnippets_MultiWord):
    keys = "test snip" + EX
    wanted = "This is a test."
class ParseSnippets_MultiWord_Description(_ParseSnippets_MultiWord):
    keys = "snip test" + EX
    wanted = "This is another test."
class ParseSnippets_MultiWord_Description_Option(_ParseSnippets_MultiWord):
    keys = "snippet test" + EX
    wanted = "This is yet another test."

class _ParseSnippets_MultiWord_RE(_VimTest):
    files = { "us/all.snippets": r"""
        snippet /[d-f]+/ "" r
        az test
        endsnippet

        snippet !^(foo|bar)$! "" r
        foo-bar test
        endsnippet

        snippet "(test ?)+" "" r
        re-test
        endsnippet
        """}
class ParseSnippets_MultiWord_RE1(_ParseSnippets_MultiWord_RE):
    keys = "abc def" + EX
    wanted = "abc az test"
class ParseSnippets_MultiWord_RE2(_ParseSnippets_MultiWord_RE):
    keys = "foo" + EX + " bar" + EX + "\nbar" + EX
    wanted = "foo-bar test bar\t\nfoo-bar test"
class ParseSnippets_MultiWord_RE3(_ParseSnippets_MultiWord_RE):
    keys = "test test test" + EX
    wanted = "re-test"

class ParseSnippets_MultiWord_Quotes(_VimTest):
    files = { "us/all.snippets": r"""
        snippet "test snip"
        This is a test.
        endsnippet
        """}
    keys = "test snip" + EX
    wanted = "This is a test."
class ParseSnippets_MultiWord_WithQuotes(_VimTest):
    files = { "us/all.snippets": r"""
        snippet !"test snip"!
        This is a test.
        endsnippet
        """}
    keys = '"test snip"' + EX
    wanted = "This is a test."

class ParseSnippets_MultiWord_NoContainer(_VimTest):
    files = { "us/all.snippets": r"""
        snippet test snip
        This is a test.
        endsnippet
        """}
    keys = "test snip" + EX
    wanted = keys
    expected_error = "Invalid multiword trigger: 'test snip' in \S+:2"

class ParseSnippets_MultiWord_UnmatchedContainer(_VimTest):
    files = { "us/all.snippets": r"""
        snippet !inv snip/
        This is a test.
        endsnippet
        """}
    keys = "inv snip" + EX
    wanted = keys
    expected_error = "Invalid multiword trigger: '!inv snip/' in \S+:2"

class ParseSnippets_Global_Python(_VimTest):
    files = { "us/all.snippets": r"""
        global !p
        def tex(ins):
            return "a " + ins + " b"
        endglobal

        snippet ab
        x `!p snip.rv = tex("bob")` y
        endsnippet

        snippet ac
        x `!p snip.rv = tex("jon")` y
        endsnippet
        """}
    keys = "ab" + EX + "\nac" + EX
    wanted = "x a bob b y\nx a jon b y"

class ParseSnippets_Global_Local_Python(_VimTest):
    files = { "us/all.snippets": r"""
global !p
def tex(ins):
    return "a " + ins + " b"
endglobal

snippet ab
x `!p first = tex("bob")
snip.rv = "first"` `!p snip.rv = first` y
endsnippet
        """}
    keys = "ab" + EX
    wanted = "x first a bob b y"
# End: Snippet Definition Parsing  #}}}

# Simple Expands  {{{#
class _SimpleExpands(_VimTest):
    snippets = ("hallo", "Hallo Welt!")

class SimpleExpand_ExpectCorrectResult(_SimpleExpands):
    keys = "hallo" + EX
    wanted = "Hallo Welt!"
class SimpleExpandTwice_ExpectCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + '\nhallo' + EX
    wanted = "Hallo Welt!\nHallo Welt!"

class SimpleExpandNewLineAndBackspae_ExpectCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + "\nHallo Welt!\n\n\b\b\b\b\b"
    wanted = "Hallo Welt!\nHallo We"
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set backspace=eol,start")

class SimpleExpandTypeAfterExpand_ExpectCorrectResult(_SimpleExpands):
    keys = "hallo" + EX + "and again"
    wanted = "Hallo Welt!and again"

class SimpleExpandTypeAndDelete_ExpectCorrectResult(_SimpleExpands):
    keys = "na du hallo" + EX + "and again\b\b\b\b\bblub"
    wanted = "na du Hallo Welt!and blub"

class DoNotExpandAfterSpace_ExpectCorrectResult(_SimpleExpands):
    keys = "hallo " + EX
    wanted = "hallo " + EX

class ExitSnippetModeAfterTabstopZero(_VimTest):
    snippets = ("test", "SimpleText")
    keys = "test" + EX + EX
    wanted = "SimpleText" + EX

class ExpandInTheMiddleOfLine_ExpectCorrectResult(_SimpleExpands):
    keys = "Wie hallo gehts" + ESC + "bhi" + EX
    wanted = "Wie Hallo Welt! gehts"
class MultilineExpand_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt!\nUnd Wie gehts")
    keys = "Wie hallo gehts" + ESC + "bhi" + EX
    wanted = "Wie Hallo Welt!\nUnd Wie gehts gehts"
class MultilineExpandTestTyping_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt!\nUnd Wie gehts")
    wanted = "Wie Hallo Welt!\nUnd Wie gehtsHuiui! gehts"
    keys = "Wie hallo gehts" + ESC + "bhi" + EX + "Huiui!"
class SimpleExpandEndingWithNewline_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo Welt\n")
    keys = "hallo" + EX + "\nAnd more"
    wanted = "Hallo Welt\n\nAnd more"


# End: Simple Expands  #}}}
# TabStop Tests  {{{#
class TabStopSimpleReplace_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${0:End} ${1:Beginning}")
    keys = "hallo" + EX + "na" + JF + "Du Nase"
    wanted = "hallo Du Nase na"
class TabStopSimpleReplaceZeroLengthTabstops_ExpectCorrectResult(_VimTest):
    snippets = ("test", r":latex:\`$1\`$0")
    keys = "test" + EX + "Hello" + JF + "World"
    wanted = ":latex:`Hello`World"
class TabStopSimpleReplaceReversed_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${1:End} ${0:Beginning}")
    keys = "hallo" + EX + "na" + JF + "Du Nase"
    wanted = "hallo na Du Nase"
class TabStopSimpleReplaceSurrounded_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${0:End} a small feed")
    keys = "hallo" + EX + "Nase"
    wanted = "hallo Nase a small feed"
class TabStopSimpleReplaceSurrounded1_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0 a small feed")
    keys = "hallo" + EX + "Nase"
    wanted = "hallo Nase a small feed"
class TabStop_Exit_ExpectCorrectResult(_VimTest):
    snippets = ("echo", "$0 run")
    keys = "echo" + EX + "test"
    wanted = "test run"

class TabStopNoReplace_ExpectCorrectResult(_VimTest):
    snippets = ("echo", "echo ${1:Hallo}")
    keys = "echo" + EX
    wanted = "echo Hallo"

class TabStop_EscapingCharsBackticks(_VimTest):
    snippets = ("test", r"snip \` literal")
    keys = "test" + EX
    wanted = "snip ` literal"
class TabStop_EscapingCharsDollars(_VimTest):
    snippets = ("test", r"snip \$0 $$0 end")
    keys = "test" + EX + "hi"
    wanted = "snip $0 $hi end"
class TabStop_EscapingCharsDollars1(_VimTest):
    snippets = ("test", r"a\${1:literal}")
    keys = "test" + EX
    wanted = "a${1:literal}"
class TabStop_EscapingCharsDollars_BeginningOfLine(_VimTest):
    snippets = ("test", "\n\\${1:literal}")
    keys = "test" + EX
    wanted = "\n${1:literal}"
class TabStop_EscapingCharsDollars_BeginningOfDefinitionText(_VimTest):
    snippets = ("test", "\\${1:literal}")
    keys = "test" + EX
    wanted = "${1:literal}"
class TabStop_EscapingChars_Backslash(_VimTest):
    snippets = ("test", r"This \ is a backslash!")
    keys = "test" + EX
    wanted = "This \\ is a backslash!"
class TabStop_EscapingChars_Backslash2(_VimTest):
    snippets = ("test", r"This is a backslash \\ done")
    keys = "test" + EX
    wanted = r"This is a backslash \ done"
class TabStop_EscapingChars_Backslash3(_VimTest):
    snippets = ("test", r"These are two backslashes \\\\ done")
    keys = "test" + EX
    wanted = r"These are two backslashes \\ done"
class TabStop_EscapingChars_Backslash4(_VimTest):
    # Test for bug 746446
    snippets = ("test", r"\\$1{$2}")
    keys = "test" + EX + "hello" + JF + "world"
    wanted = r"\hello{world}"
class TabStop_EscapingChars_RealLife(_VimTest):
    snippets = ("test", r"usage: \`basename \$0\` ${1:args}")
    keys = "test" + EX + "[ -u -v -d ]"
    wanted = "usage: `basename $0` [ -u -v -d ]"

class TabStopEscapingWhenSelected_ECR(_VimTest):
    snippets = ("test", "snip ${1:default}")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip default"
class TabStopEscapingWhenSelectedSingleCharTS_ECR(_VimTest):
    snippets = ("test", "snip ${1:i}")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip i"
class TabStopEscapingWhenSelectedNoCharTS_ECR(_VimTest):
    snippets = ("test", "snip $1")
    keys = "test" + EX + ESC + "0ihi"
    wanted = "hisnip "

class TabStopWithOneChar_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "nothing ${1:i} hups")
    keys = "hallo" + EX + "ship"
    wanted = "nothing ship hups"

class TabStopTestJumping_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${2:End} mitte ${1:Beginning}")
    keys = "hallo" + EX + JF + "Test" + JF + "Hi"
    wanted = "hallo Test mitte BeginningHi"
class TabStopTestJumping2_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $2 $1")
    keys = "hallo" + EX + JF + "Test" + JF + "Hi"
    wanted = "hallo Test Hi"
class TabStopTestJumpingRLExampleWithZeroTab_ExpectCorrectResult(_VimTest):
    snippets = ("test", "each_byte { |${1:byte}| $0 }")
    keys = "test" + EX + JF + "Blah"
    wanted = "each_byte { |byte| Blah }"

class TabStopTestJumpingDontJumpToEndIfThereIsTabZero_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0 $1")
    keys = "hallo" + EX + "Test" + JF + "Hi" + JF + JF + "du"
    wanted = "hallo Hi" + 2*JF + "du Test"

class TabStopTestBackwardJumping_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo ${2:End} mitte${1:Beginning}")
    keys = "hallo" + EX + "Somelengthy Text" + JF + "Hi" + JB + \
            "Lets replace it again" + JF + "Blah" + JF + JB*2 + JF
    wanted = "hallo Blah mitteLets replace it again" + JB*2 + JF
class TabStopTestBackwardJumping2_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $2 $1")
    keys = "hallo" + EX + "Somelengthy Text" + JF + "Hi" + JB + \
            "Lets replace it again" + JF + "Blah" + JF + JB*2 + JF
    wanted = "hallo Blah Lets replace it again" + JB*2 + JF

class TabStopTestMultilineExpand_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "hallo $0\nnice $1 work\n$3 $2\nSeem to work")
    keys ="test hallo World" + ESC + "02f i" + EX + "world" + JF + "try" + \
            JF + "test" + JF + "one more" + JF
    wanted = "test hallo one more" + JF + "\nnice world work\n" \
            "test try\nSeem to work World"

class TabStop_TSInDefaultTextRLExample_OverwriteNone_ECR(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX
    wanted = """<div id="some_id">\n  \n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteFirst_NoJumpBack(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + " blah" + JF + "Hallo"
    wanted = """<div blah>\n  Hallo\n</div>"""
class TabStop_TSInDefaultTextRLExample_DeleteFirst(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + BS + JF + "Hallo"
    wanted = """<div>\n  Hallo\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteFirstJumpBack(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3  $0\n</div>""")
    keys = "test" + EX + "Hi" + JF + "Hallo" + JB + "SomethingElse" + JF + \
            "Nupl" + JF + "Nox"
    wanted = """<divSomethingElse>\n  Nupl  Nox\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecond(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End"
    wanted = """<div id="no">\n  End\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecondTabBack(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3 $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End" + JB + "yes" + JF + "Begin" \
            + JF + "Hi"
    wanted = """<div id="yes">\n  Begin Hi\n</div>"""
class TabStop_TSInDefaultTextRLExample_OverwriteSecondTabBackTwice(_VimTest):
    snippets = ("test", """<div${1: id="${2:some_id}"}>\n  $3 $0\n</div>""")
    keys = "test" + EX + JF + "no" + JF + "End" + JB + "yes" + JB + \
            " allaway" + JF + "Third" + JF + "Last"
    wanted = """<div allaway>\n  Third Last\n</div>"""

class TabStop_TSInDefaultText_ZeroLengthNested_OverwriteSecond(_VimTest):
    snippets = ("test", """h${1:a$2b}l""")
    keys = "test" + EX + JF + "ups" + JF + "End"
    wanted = """haupsblEnd"""
class TabStop_TSInDefaultText_ZeroLengthNested_OverwriteFirst(_VimTest):
    snippets = ("test", """h${1:a$2b}l""")
    keys = "test" + EX + "ups" + JF + "End"
    wanted = """hupslEnd"""
class TabStop_TSInDefaultText_ZeroLengthNested_OverwriteSecondJumpBackOverwrite(_VimTest):
    snippets = ("test", """h${1:a$2b}l""")
    keys = "test" + EX + JF + "longertext" + JB + "overwrite" + JF + "End"
    wanted = """hoverwritelEnd"""
class TabStop_TSInDefaultText_ZeroLengthNested_OverwriteSecondJumpBackAndForward0(_VimTest):
    snippets = ("test", """h${1:a$2b}l""")
    keys = "test" + EX + JF + "longertext" + JB + JF + "overwrite" + JF + "End"
    wanted = """haoverwriteblEnd"""
class TabStop_TSInDefaultText_ZeroLengthNested_OverwriteSecondJumpBackAndForward1(_VimTest):
    snippets = ("test", """h${1:a$2b}l""")
    keys = "test" + EX + JF + "longertext" + JB + JF + JF + "End"
    wanted = """halongertextblEnd"""

class TabStop_TSInDefaultNested_OverwriteOneJumpBackToOther(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + "Hallo" + JF + "Ende"
    wanted = "hi this Hallo Ende"
class TabStop_TSInDefaultNested_OverwriteOneJumpToThird(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + JF + "Hallo" + JF + "Ende"
    wanted = "hi this second Hallo Ende"
class TabStop_TSInDefaultNested_OverwriteOneJumpAround(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second ${3:third}}} $4")
    keys = "test" + EX + JF + JF + "Hallo" + JB+JB + "Blah" + JF + "Ende"
    wanted = "hi Blah Ende"

class TabStop_TSInDefault_MirrorsOutside_DoNothing(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX
    wanted = "hi this second second"
class TabStop_TSInDefault_MirrorsOutside_OverwriteSecond(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX + JF + "Hallo"
    wanted = "hi this Hallo Hallo"
class TabStop_TSInDefault_MirrorsOutside_Overwrite0(_VimTest):
    snippets = ("test", "hi ${1:this ${2:second}} $2")
    keys = "test" + EX + "Hallo"
    wanted = "hi Hallo "
class TabStop_TSInDefault_MirrorsOutside_Overwrite1(_VimTest):
    snippets = ("test", "$1: ${1:'${2:second}'} $2")
    keys = "test" + EX + "Hallo"
    wanted = "Hallo: Hallo "
class TabStop_TSInDefault_MirrorsOutside_OverwriteSecond1(_VimTest):
    snippets = ("test", "$1: ${1:'${2:second}'} $2")
    keys = "test" + EX + JF + "Hallo"
    wanted = "'Hallo': 'Hallo' Hallo"
class TabStop_TSInDefault_MirrorsOutside_OverwriteFirstSwitchNumbers(_VimTest):
    snippets = ("test", "$2: ${2:'${1:second}'} $1")
    keys = "test" + EX + "Hallo"
    wanted = "'Hallo': 'Hallo' Hallo"
class TabStop_TSInDefault_MirrorsOutside_OverwriteFirst_RLExample(_VimTest):
    snippets = ("test", """`!p snip.rv = t[1].split('/')[-1].lower().strip("'")` = require(${1:'${2:sys}'})""")
    keys = "test" + EX + "WORLD" + JF + "End"
    wanted = "world = require(WORLD)End"
class TabStop_TSInDefault_MirrorsOutside_OverwriteSecond_RLExample(_VimTest):
    snippets = ("test", """`!p snip.rv = t[1].split('/')[-1].lower().strip("'")` = require(${1:'${2:sys}'})""")
    keys = "test" + EX + JF + "WORLD" + JF + "End"
    wanted = "world = require('WORLD')End"

class TabStop_Multiline_Leave(_VimTest):
    snippets = ("test", "hi ${1:first line\nsecond line} world" )
    keys = "test" + EX
    wanted = "hi first line\nsecond line world"
class TabStop_Multiline_Overwrite(_VimTest):
    snippets = ("test", "hi ${1:first line\nsecond line} world" )
    keys = "test" + EX + "Nothing"
    wanted = "hi Nothing world"
class TabStop_Multiline_MirrorInFront_Leave(_VimTest):
    snippets = ("test", "hi $1 ${1:first line\nsecond line} world" )
    keys = "test" + EX
    wanted = "hi first line\nsecond line first line\nsecond line world"
class TabStop_Multiline_MirrorInFront_Overwrite(_VimTest):
    snippets = ("test", "hi $1 ${1:first line\nsecond line} world" )
    keys = "test" + EX + "Nothing"
    wanted = "hi Nothing Nothing world"
class TabStop_Multiline_DelFirstOverwriteSecond_Overwrite(_VimTest):
    snippets = ("test", "hi $1 $2 ${1:first line\nsecond line} ${2:Hi} world" )
    keys = "test" + EX + BS + JF + "Nothing"
    wanted = "hi  Nothing  Nothing world"

class TabStopNavigatingInInsertModeSimple_ExpectCorrectResult(_VimTest):
    snippets = ("hallo", "Hallo ${1:WELT} ups")
    keys = "hallo" + EX + "haselnut" + 2*ARR_L + "hips" + JF + "end"
    wanted = "Hallo haselnhipsut upsend"
# End: TabStop Tests  #}}}
# ShellCode Interpolation  {{{#
class TabStop_Shell_SimpleExample(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", "hi `echo hallo` you!")
    keys = "test" + EX + "and more"
    wanted = "hi hallo you!and more"
class TabStop_Shell_WithUmlauts(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", "hi `echo höüäh` you!")
    keys = "test" + EX + "and more"
    wanted = "hi höüäh you!and more"
class TabStop_Shell_TextInNextLine(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", "hi `echo hallo`\nWeiter")
    keys = "test" + EX + "and more"
    wanted = "hi hallo\nWeiterand more"
class TabStop_Shell_InDefValue_Leave(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", "Hallo ${1:now `echo fromecho`} end")
    keys = "test" + EX + JF + "and more"
    wanted = "Hallo now fromecho endand more"
class TabStop_Shell_InDefValue_Overwrite(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", "Hallo ${1:now `echo fromecho`} end")
    keys = "test" + EX + "overwrite" + JF + "and more"
    wanted = "Hallo overwrite endand more"
class TabStop_Shell_TestEscapedChars_Overwrite(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", r"""`echo \`echo "\\$hi"\``""")
    keys = "test" + EX
    wanted = "$hi"
class TabStop_Shell_TestEscapedCharsAndShellVars_Overwrite(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", r"""`hi="blah"; echo \`echo "$hi"\``""")
    keys = "test" + EX
    wanted = "blah"

class TabStop_Shell_ShebangPython(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = ("test", """Hallo ${1:now `#!/usr/bin/env python
print "Hallo Welt"
`} end""")
    keys = "test" + EX + JF + "and more"
    wanted = "Hallo now Hallo Welt endand more"
# End: ShellCode Interpolation  #}}}
# VimScript Interpolation  {{{#
class TabStop_VimScriptInterpolation_SimpleExample(_VimTest):
    snippets = ("test", """hi `!v indent(".")` End""")
    keys = "    test" + EX
    wanted = "    hi 4 End"
# End: VimScript Interpolation  #}}}
# PythonCode Interpolation  {{{#
# Deprecated Implementation  {{{#
class PythonCodeOld_SimpleExample(_VimTest):
    snippets = ("test", """hi `!p res = "Hallo"` End""")
    keys = "test" + EX
    wanted = "hi Hallo End"
class PythonCodeOld_ReferencePlaceholderAfter(_VimTest):
    snippets = ("test", """${1:hi} `!p res = t[1]+".blah"` End""")
    keys = "test" + EX + "ho"
    wanted = "ho ho.blah End"
class PythonCodeOld_ReferencePlaceholderBefore(_VimTest):
    snippets = ("test", """`!p res = len(t[1])*"#"`\n${1:some text}""")
    keys = "test" + EX + "Hallo Welt"
    wanted = "##########\nHallo Welt"
class PythonCodeOld_TransformedBeforeMultiLine(_VimTest):
    snippets = ("test", """${1/.+/egal/m} ${1:`!p
res = "Hallo"`} End""")
    keys = "test" + EX
    wanted = "egal Hallo End"
class PythonCodeOld_IndentedMultiline(_VimTest):
    snippets = ("test", """start `!p a = 1
b = 2
if b > a:
    res = "b isbigger a"
else:
    res = "a isbigger b"` end""")
    keys = "    test" + EX
    wanted = "    start b isbigger a end"
# End: Deprecated Implementation  #}}}
# New Implementation  {{{#
class PythonCode_UseNewOverOld(_VimTest):
    snippets = ("test", """hi `!p res = "Old"
snip.rv = "New"` End""")
    keys = "test" + EX
    wanted = "hi New End"

class PythonCode_SimpleExample(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo"` End""")
    keys = "test" + EX
    wanted = "hi Hallo End"

class PythonCode_SimpleExample_ReturnValueIsEmptyString(_VimTest):
    snippets = ("test", """hi`!p snip.rv = ""`End""")
    keys = "test" + EX
    wanted = "hiEnd"

class PythonCode_ReferencePlaceholder(_VimTest):
    snippets = ("test", """${1:hi} `!p snip.rv = t[1]+".blah"` End""")
    keys = "test" + EX + "ho"
    wanted = "ho ho.blah End"

class PythonCode_ReferencePlaceholderBefore(_VimTest):
    snippets = ("test", """`!p snip.rv = len(t[1])*"#"`\n${1:some text}""")
    keys = "test" + EX + "Hallo Welt"
    wanted = "##########\nHallo Welt"
class PythonCode_TransformedBeforeMultiLine(_VimTest):
    snippets = ("test", """${1/.+/egal/m} ${1:`!p
snip.rv = "Hallo"`} End""")
    keys = "test" + EX
    wanted = "egal Hallo End"
class PythonCode_MultilineIndented(_VimTest):
    snippets = ("test", """start `!p a = 1
b = 2
if b > a:
    snip.rv = "b isbigger a"
else:
    snip.rv = "a isbigger b"` end""")
    keys = "    test" + EX
    wanted = "    start b isbigger a end"

class PythonCode_SimpleAppend(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo1"
snip += "Hallo2"` End""")
    keys = "test" + EX
    wanted = "hi Hallo1\nHallo2 End"

class PythonCode_MultiAppend(_VimTest):
    snippets = ("test", """hi `!p snip.rv = "Hallo1"
snip += "Hallo2"
snip += "Hallo3"` End""")
    keys = "test" + EX
    wanted = "hi Hallo1\nHallo2\nHallo3 End"

class PythonCode_MultiAppendSimpleIndent(_VimTest):
    snippets = ("test", """hi
`!p snip.rv="Hallo1"
snip += "Hallo2"
snip += "Hallo3"`
End""")
    keys = """
    test""" + EX
    wanted = """
    hi
    Hallo1
    Hallo2
    Hallo3
    End"""

class PythonCode_SimpleMkline(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="Hallo1\n"
snip.rv += snip.mkline("Hallo2") + "\n"
snip.rv += snip.mkline("Hallo3")`
End""")
    keys = """
    test""" + EX
    wanted = """
    hi
    Hallo1
    Hallo2
    Hallo3
    End"""

class PythonCode_MultiAppendShift(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1"
snip += "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 3
snip += "i3"`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
	i1
		i2
i0
			i3
	End"""

class PythonCode_MultiAppendShiftMethods(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1\n"
snip.rv += snip.mkline("i1\n")
snip.shift(1)
snip.rv += snip.mkline("i2\n")
snip.unshift(2)
snip.rv += snip.mkline("i0\n")
snip.shift(3)
snip.rv += snip.mkline("i3")`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
	i1
		i2
i0
			i3
	End"""


class PythonCode_ResetIndent(_VimTest):
    snippets = ("test", r"""hi
`!p snip.rv="i1"
snip >> 1
snip += "i2"
snip.reset_indent()
snip += "i1"
snip << 1
snip += "i0"
snip.reset_indent()
snip += "i1"`
End""")
    keys = """
	test""" + EX
    wanted = """
	hi
	i1
		i2
	i1
i0
	i1
	End"""

class PythonCode_IndentEtSw(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set expandtab")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """   test""" + EX
    wanted = """   hi
   i1
      i2
i0
   i1
   End"""

class PythonCode_IndentEtSwOffset(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set expandtab")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """    test""" + EX
    wanted = """    hi
    i1
       i2
 i0
    i1
    End"""

class PythonCode_IndentNoetSwTs(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set ts=4")
    snippets = ("test", r"""hi
`!p snip.rv = "i1"
snip >> 1
snip += "i2"
snip << 2
snip += "i0"
snip >> 1
snip += "i1"
`
End""")
    keys = """   test""" + EX
    wanted = """   hi
   i1
\t  i2
i0
   i1
   End"""

# Test using 'opt'
class PythonCode_OptExists(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append('let g:UStest="yes"')
    snippets = ("test", r"""hi `!p snip.rv = snip.opt("g:UStest") or "no"` End""")
    keys = """test""" + EX
    wanted = """hi yes End"""

class PythonCode_OptNoExists(_VimTest):
    snippets = ("test", r"""hi `!p snip.rv = snip.opt("g:UStest") or "no"` End""")
    keys = """test""" + EX
    wanted = """hi no End"""

class PythonCode_IndentProblem(_VimTest):
    # A test case which is likely related to bug 719649
    snippets = ("test", r"""hi `!p
snip.rv = "World"
` End""")
    keys = " " * 8 + "test" + EX  # < 8 works.
    wanted = """        hi World End"""

class PythonCode_TrickyReferences(_VimTest):
    snippets = ("test", r"""${2:${1/.+/egal/}} ${1:$3} ${3:`!p snip.rv = "hi"`}""")
    keys = "ups test" + EX
    wanted = "ups egal hi hi"
# locals
class PythonCode_Locals(_VimTest):
    snippets = ("test", r"""hi `!p a = "test"
snip.rv = "nothing"` `!p snip.rv = a
` End""")
    keys = """test""" + EX
    wanted = """hi nothing test End"""

class PythonCode_LongerTextThanSource_Chars(_VimTest):
    snippets = ("test", r"""hi`!p snip.rv = "a" * 100`end""")
    keys = """test""" + EX + "ups"
    wanted = "hi" + 100*"a" + "endups"

class PythonCode_LongerTextThanSource_MultiLine(_VimTest):
    snippets = ("test", r"""hi`!p snip.rv = "a" * 100 + '\n'*100 + "a"*100`end""")
    keys = """test""" + EX + "ups"
    wanted = "hi" + 100*"a" + 100*"\n" + 100*"a" + "endups"

class PythonCode_AccessKilledTabstop_OverwriteSecond(_VimTest):
    snippets = ("test", r"`!p snip.rv = t[2].upper()`${1:h${2:welt}o}`!p snip.rv = t[2].upper()`")
    keys = "test" + EX + JF + "okay"
    wanted = "OKAYhokayoOKAY"
class PythonCode_AccessKilledTabstop_OverwriteFirst(_VimTest):
    snippets = ("test", r"`!p snip.rv = t[2].upper()`${1:h${2:welt}o}`!p snip.rv = t[2].upper()`")
    keys = "test" + EX + "aaa"
    wanted = "aaa"

class PythonVisual_NoVisualSelection_Ignore(_VimTest):
    snippets = ("test", "h`!p snip.rv = snip.v.mode + snip.v.text`b")
    keys = "test" + EX + "abc"
    wanted = "hbabc"
class PythonVisual_SelectOneWord(_VimTest):
    snippets = ("test", "h`!p snip.rv = snip.v.mode + snip.v.text`b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hvblablubb"
class PythonVisual_LineSelect_Simple(_VimTest):
    snippets = ("test", "h`!p snip.rv = snip.v.mode + snip.v.text`b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "hVhello\nnice\nworld\nb"

# Tests for https://bugs.launchpad.net/bugs/1259349
class Python_WeirdScoping_Error(_VimTest):
    snippets = ("test", "h`!p import re; snip.rv = '%i' % len([re.search for i in 'aiiia'])`b")
    keys = "test" + EX
    wanted = "h5b"
# End: New Implementation  #}}}
# End: PythonCode Interpolation  #}}}
# Mirrors  {{{#
class TextTabStopTextAfterTab_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 Hinten\n$1")
    keys = "test" + EX + "hallo"
    wanted = "hallo Hinten\nhallo"
class TextTabStopTextBeforeTab_ExpectCorrectResult(_VimTest):
    snippets = ("test", "Vorne $1\n$1")
    keys = "test" + EX + "hallo"
    wanted = "Vorne hallo\nhallo"
class TextTabStopTextSurroundedTab_ExpectCorrectResult(_VimTest):
    snippets = ("test", "Vorne $1 Hinten\n$1")
    keys = "test" + EX + "hallo test"
    wanted = "Vorne hallo test Hinten\nhallo test"

class TextTabStopTextBeforeMirror_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\nVorne $1")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nVorne hallo"
class TextTabStopAfterMirror_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1 Hinten")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nhallo Hinten"
class TextTabStopSurroundMirror_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\nVorne $1 Hinten")
    keys = "test" + EX + "hallo welt"
    wanted = "hallo welt\nVorne hallo welt Hinten"
class TextTabStopAllSurrounded_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ObenVorne $1 ObenHinten\nVorne $1 Hinten")
    keys = "test" + EX + "hallo welt"
    wanted = "ObenVorne hallo welt ObenHinten\nVorne hallo welt Hinten"

class MirrorBeforeTabstopLeave_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1:this is it} $1")
    keys = "test" + EX
    wanted = "this is it this is it this is it"
class MirrorBeforeTabstopOverwrite_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1:this is it} $1")
    keys = "test" + EX + "a"
    wanted = "a a a"

class TextTabStopSimpleMirrorMultiline_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo"
    wanted = "hallo\nhallo"
class SimpleMirrorMultilineMany_ExpectCorrectResult(_VimTest):
    snippets = ("test", "    $1\n$1\na$1b\n$1\ntest $1 mich")
    keys = "test" + EX + "hallo"
    wanted = "    hallo\nhallo\nahallob\nhallo\ntest hallo mich"
class MultilineTabStopSimpleMirrorMultiline_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n\n$1\n\n$1")
    keys = "test" + EX + "hallo Du\nHi"
    wanted = "hallo Du\nHi\n\nhallo Du\nHi\n\nhallo Du\nHi"
class MultilineTabStopSimpleMirrorMultiline1_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1\n$1")
    keys = "test" + EX + "hallo Du\nHi"
    wanted = "hallo Du\nHi\nhallo Du\nHi\nhallo Du\nHi"
class MultilineTabStopSimpleMirrorDeleteInLine_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1\n$1")
    keys = "test" + EX + "hallo Du\nHi\b\bAch Blah"
    wanted = "hallo Du\nAch Blah\nhallo Du\nAch Blah\nhallo Du\nAch Blah"
class TextTabStopSimpleMirrorMultilineMirrorInFront_ECR(_VimTest):
    snippets = ("test", "$1\n${1:sometext}")
    keys = "test" + EX + "hallo\nagain"
    wanted = "hallo\nagain\nhallo\nagain"

class SimpleMirrorDelete_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo\b\b"
    wanted = "hal\nhal"

class SimpleMirrorSameLine_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 $1")
    keys = "test" + EX + "hallo"
    wanted = "hallo hallo"
class SimpleMirrorSameLine_InText_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 $1")
    keys = "ups test blah" + ESC + "02f i" + EX + "hallo"
    wanted = "ups hallo hallo blah"
class SimpleMirrorSameLineBeforeTabDefVal_ECR(_VimTest):
    snippets = ("test", "$1 ${1:replace me}")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo foo hallo foo"
class SimpleMirrorSameLineBeforeTabDefVal_DelB4Typing_ECR(_VimTest):
    snippets = ("test", "$1 ${1:replace me}")
    keys = "test" + EX + BS + "hallo foo"
    wanted = "hallo foo hallo foo"
class SimpleMirrorSameLineMany_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 $1 $1 $1")
    keys = "test" + EX + "hallo du"
    wanted = "hallo du hallo du hallo du hallo du"
class SimpleMirrorSameLineManyMultiline_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 $1 $1 $1")
    keys = "test" + EX + "hallo du\nwie gehts"
    wanted = "hallo du\nwie gehts hallo du\nwie gehts hallo du\nwie gehts" \
            " hallo du\nwie gehts"
class SimpleMirrorDeleteSomeEnterSome_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1\n$1")
    keys = "test" + EX + "hallo\b\bhups"
    wanted = "halhups\nhalhups"

class SimpleTabstopWithDefaultSimpelType_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:defa}\n$1")
    keys = "test" + EX + "world"
    wanted = "ha world\nworld"
class SimpleTabstopWithDefaultComplexType_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:default value} $1\nanother: $1 mirror")
    keys = "test" + EX + "world"
    wanted = "ha world world\nanother: world mirror"
class SimpleTabstopWithDefaultSimpelKeep_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:defa}\n$1")
    keys = "test" + EX
    wanted = "ha defa\ndefa"
class SimpleTabstopWithDefaultComplexKeep_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:default value} $1\nanother: $1 mirror")
    keys = "test" + EX
    wanted = "ha default value default value\nanother: default value mirror"

class TabstopWithMirrorManyFromAll_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $5 ${1:blub} $4 $0 ${2:$1.h} $1 $3 ${4:More}")
    keys = "test" + EX + "hi" + JF + "hu" + JF + "hub" + JF + "hulla" + \
            JF + "blah" + JF + "end"
    wanted = "ha blah hi hulla end hu hi hub hulla"
class TabstopWithMirrorInDefaultNoType_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:blub} ${2:$1.h}")
    keys = "test" + EX
    wanted = "ha blub blub.h"
class TabstopWithMirrorInDefaultNoType1_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha ${1:blub} ${2:$1}")
    keys = "test" + EX
    wanted = "ha blub blub"
class TabstopWithMirrorInDefaultTwiceAndExtra_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1.h $1.c}\ntest $1")
    keys = "test" + EX + "stdin"
    wanted = "ha stdin stdin.h stdin.c\ntest stdin"
class TabstopWithMirrorInDefaultMultipleLeave_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:snip} ${3:$1.h $2}")
    keys = "test" + EX + "stdin"
    wanted = "ha stdin snip stdin.h snip"
class TabstopWithMirrorInDefaultMultipleOverwrite_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:snip} ${3:$1.h $2}")
    keys = "test" + EX + "stdin" + JF + "do snap"
    wanted = "ha stdin do snap stdin.h do snap"
class TabstopWithMirrorInDefaultOverwrite_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1.h}")
    keys = "test" + EX + "stdin" + JF + "overwritten"
    wanted = "ha stdin overwritten"
class TabstopWithMirrorInDefaultOverwrite1_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1}")
    keys = "test" + EX + "stdin" + JF + "overwritten"
    wanted = "ha stdin overwritten"
class TabstopWithMirrorInDefaultNoOverwrite1_ExpectCorrectResult(_VimTest):
    snippets = ("test", "ha $1 ${2:$1}")
    keys = "test" + EX + "stdin" + JF + JF + "end"
    wanted = "ha stdin stdinend"

class MirrorRealLifeExample_ExpectCorrectResult(_VimTest):
    snippets = (
        ("for", "for(size_t ${2:i} = 0; $2 < ${1:count}; ${3:++$2})" \
         "\n{\n\t${0:/* code */}\n}"),
    )
    keys ="for" + EX + "100" + JF + "avar\b\b\b\ba_variable" + JF + \
            "a_variable *= 2" + JF + "// do nothing"
    wanted = """for(size_t a_variable = 0; a_variable < 100; a_variable *= 2)
{
\t// do nothing
}"""

class Mirror_TestKill_InsertBefore_NoKill(_VimTest):
    snippets = "test", "$1 $1_"
    keys = "hallo test" + EX + "auch" + ESC + "wihi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noauch hinoauch_end"
class Mirror_TestKill_InsertAfter_NoKill(_VimTest):
    snippets = "test", "$1 $1_"
    keys = "hallo test" + EX + "auch" + ESC + "eiab" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noauch noauchab_end"
class Mirror_TestKill_InsertBeginning_Kill(_VimTest):
    snippets = "test", "$1 $1_"
    keys = "hallo test" + EX + "auch" + ESC + "wahi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noauch ahiuch_end"
class Mirror_TestKill_InsertEnd_Kill(_VimTest):
    snippets = "test", "$1 $1_"
    keys = "hallo test" + EX + "auch" + ESC + "ehihi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noauch auchih_end"
class Mirror_TestKillTabstop_Kill(_VimTest):
    snippets = "test", "welt${1:welt${2:welt}welt} $2"
    keys = "hallo test" + EX + "elt"
    wanted = "hallo weltelt "

# End: Mirrors  #}}}
# Transformations  {{{#
class Transformation_SimpleCase_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/foo/batzl/}")
    keys = "test" + EX + "hallo foo boy"
    wanted = "hallo foo boy hallo batzl boy"
class Transformation_SimpleCaseNoTransform_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/foo/batzl/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo hallo"
class Transformation_SimpleCaseTransformInFront_ExpectCorrectResult(_VimTest):
    snippets = ("test", "${1/foo/batzl/} $1")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo batzl hallo foo"
class Transformation_SimpleCaseTransformInFrontDefVal_ECR(_VimTest):
    snippets = ("test", "${1/foo/batzl/} ${1:replace me}")
    keys = "test" + EX + "hallo foo"
    wanted = "hallo batzl hallo foo"
class Transformation_MultipleTransformations_ECR(_VimTest):
    snippets = ("test", "${1:Some Text}${1/.+/\\U$0\E/}\n${1/.+/\L$0\E/}")
    keys = "test" + EX + "SomE tExt "
    wanted = "SomE tExt SOME TEXT \nsome text "
class Transformation_TabIsAtEndAndDeleted_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1:some}")
    keys = "hallo test" + EX + "some\b\b\b\b\b"
    wanted = "hallo "
class Transformation_TabIsAtEndAndDeleted1_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1:some}")
    keys = "hallo test" + EX + "some\b\b\b\bmore"
    wanted = "hallo is somethingmore"
class Transformation_TabIsAtEndNoTextLeave_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1}")
    keys = "hallo test" + EX
    wanted = "hallo "
class Transformation_TabIsAtEndNoTextType_ECR(_VimTest):
    snippets = ("test", "${1/.+/is something/}${1}")
    keys = "hallo test" + EX + "b"
    wanted = "hallo is somethingb"
class Transformation_InsideTabLeaveAtDefault_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:${1/.+/(?0:defined $0)/}}")
    keys = "test" + EX + "sometext" + JF
    wanted = "sometext defined sometext"
class Transformation_InsideTabOvertype_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:${1/.+/(?0:defined $0)/}}")
    keys = "test" + EX + "sometext" + JF + "overwrite"
    wanted = "sometext overwrite"


class Transformation_Backreference_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/([ab])oo/$1ull/}")
    keys = "test" + EX + "foo boo aoo"
    wanted = "foo boo aoo foo bull aoo"
class Transformation_BackreferenceTwice_ExpectCorrectResult(_VimTest):
    snippets = ("test", r"$1 ${1/(dead) (par[^ ]*)/this $2 is a bit $1/}")
    keys = "test" + EX + "dead parrot"
    wanted = "dead parrot this parrot is a bit dead"

class Transformation_CleverTransformUpercaseChar_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.)/\\u$1/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo Hallo"
class Transformation_CleverTransformLowercaseChar_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\l$1/}")
    keys = "test" + EX + "Hallo"
    wanted = "Hallo hallo"
class Transformation_CleverTransformLongUpper_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\\U$1\E/}")
    keys = "test" + EX + "hallo"
    wanted = "hallo HALLO"
class Transformation_CleverTransformLongLower_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(.*)/\L$1\E/}")
    keys = "test" + EX + "HALLO"
    wanted = "HALLO hallo"

class Transformation_SimpleCaseAsciiResult(_VimTest):
    skip_if = lambda self: no_unidecode_available()
    snippets = ("ascii", "$1 ${1/(.*)/$1/a}")
    keys = "ascii" + EX + "éèàçôïÉÈÀÇÔÏ€"
    wanted = "éèàçôïÉÈÀÇÔÏ€ eeacoiEEACOIEU"
class Transformation_LowerCaseAsciiResult(_VimTest):
    skip_if = lambda self: no_unidecode_available()
    snippets = ("ascii", "$1 ${1/(.*)/\L$1\E/a}")
    keys = "ascii" + EX + "éèàçôïÉÈÀÇÔÏ€"
    wanted = "éèàçôïÉÈÀÇÔÏ€ eeacoieeacoieu"

class Transformation_ConditionalInsertionSimple_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(^a).*/(?0:began with an a)/}")
    keys = "test" + EX + "a some more text"
    wanted = "a some more text began with an a"
class Transformation_CIBothDefinedNegative_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(?:(^a)|(^b)).*/(?1:yes:no)/}")
    keys = "test" + EX + "b some"
    wanted = "b some no"
class Transformation_CIBothDefinedPositive_ExpectCorrectResult(_VimTest):
    snippets = ("test", "$1 ${1/(?:(^a)|(^b)).*/(?1:yes:no)/}")
    keys = "test" + EX + "a some"
    wanted = "a some yes"
class Transformation_ConditionalInsertRWEllipsis_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/(\w+(?:\W+\w+){,7})\W*(.+)?/$1(?2:...)/}")
    keys = "test" + EX + "a b  c d e f ghhh h oha"
    wanted = "a b  c d e f ghhh h oha a b  c d e f ghhh h..."
class Transformation_ConditionalInConditional_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/^.*?(-)?(>)?$/(?2::(?1:>:.))/}")
    keys = "test" + EX + "hallo" + ESC + "$a\n" + \
           "test" + EX + "hallo-" + ESC + "$a\n" + \
           "test" + EX + "hallo->"
    wanted = "hallo .\nhallo- >\nhallo-> "

class Transformation_CINewlines_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */\n/}")
    keys = "test" + EX + "test, hallo"
    wanted = "test, hallo test\nhallo"
class Transformation_CITabstop_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */\t/}")
    keys = "test" + EX + "test, hallo"
    wanted = "test, hallo test\thallo"
class Transformation_CIEscapedParensinReplace_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/hal((?:lo)|(?:ul))/(?1:ha\($1\))/}")
    keys = "test" + EX + "test, halul"
    wanted = "test, halul test, ha(ul)"

class Transformation_OptionIgnoreCase_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/test/blah/i}")
    keys = "test" + EX + "TEST"
    wanted = "TEST blah"
class Transformation_OptionReplaceGlobal_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */-/g}")
    keys = "test" + EX + "a, nice, building"
    wanted = "a, nice, building a-nice-building"
class Transformation_OptionReplaceGlobalMatchInReplace_ECR(_VimTest):
    snippets = ("test", r"$1 ${1/, */, /g}")
    keys = "test" + EX + "a, nice,   building"
    wanted = "a, nice,   building a, nice, building"
class TransformationUsingBackspaceToDeleteDefaultValueInFirstTab_ECR(_VimTest):
     snippets = ("test", "snip ${1/.+/(?0:m1)/} ${2/.+/(?0:m2)/} "
                 "${1:default} ${2:def}")
     keys = "test" + EX + BS + JF + "hi"
     wanted = "snip  m2  hi"
class TransformationUsingBackspaceToDeleteDefaultValueInSecondTab_ECR(_VimTest):
     snippets = ("test", "snip ${1/.+/(?0:m1)/} ${2/.+/(?0:m2)/} "
                 "${1:default} ${2:def}")
     keys = "test" + EX + "hi" + JF + BS
     wanted = "snip m1  hi "
class TransformationUsingBackspaceToDeleteDefaultValueTypeSomethingThen_ECR(_VimTest):
     snippets = ("test", "snip ${1/.+/(?0:matched)/} ${1:default}")
     keys = "test" + EX + BS + "hallo"
     wanted = "snip matched hallo"
class TransformationUsingBackspaceToDeleteDefaultValue_ECR(_VimTest):
     snippets = ("test", "snip ${1/.+/(?0:matched)/} ${1:default}")
     keys = "test" + EX + BS
     wanted = "snip  "
class Transformation_TestKill_InsertBefore_NoKill(_VimTest):
    snippets = "test", r"$1 ${1/.*/\L$0$0\E/}_"
    keys = "hallo test" + EX + "AUCH" + ESC + "wihi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noAUCH hinoauchnoauch_end"
class Transformation_TestKill_InsertAfter_NoKill(_VimTest):
    snippets = "test", r"$1 ${1/.*/\L$0$0\E/}_"
    keys = "hallo test" + EX + "AUCH" + ESC + "eiab" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noAUCH noauchnoauchab_end"
class Transformation_TestKill_InsertBeginning_Kill(_VimTest):
    snippets = "test", r"$1 ${1/.*/\L$0$0\E/}_"
    keys = "hallo test" + EX + "AUCH" + ESC + "wahi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noAUCH ahiuchauch_end"
class Transformation_TestKill_InsertEnd_Kill(_VimTest):
    snippets = "test", r"$1 ${1/.*/\L$0$0\E/}_"
    keys = "hallo test" + EX + "AUCH" + ESC + "ehihi" + ESC + "bb" + "ino" + JF + "end"
    wanted = "hallo noAUCH auchauchih_end"
# End: Transformations  #}}}
# ${VISUAL}  {{{#
class Visual_NoVisualSelection_Ignore(_VimTest):
    snippets = ("test", "h${VISUAL}b")
    keys = "test" + EX + "abc"
    wanted = "hbabc"
class Visual_SelectOneWord(_VimTest):
    snippets = ("test", "h${VISUAL}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hblablubb"
class Visual_SelectOneWord_ProblemAfterTab(_VimTest):
    snippets = ("test", "h${VISUAL}b", "", "i")
    keys = "\tblablub" + ESC + "5hv3l" + EX + "test" + EX
    wanted = "\tbhlablbub"
class VisualWithDefault_ExpandWithoutVisual(_VimTest):
    snippets = ("test", "h${VISUAL:world}b")
    keys = "test" + EX + "hi"
    wanted = "hworldbhi"
class VisualWithDefaultWithSlashes_ExpandWithoutVisual(_VimTest):
    snippets = ("test", r"h${VISUAL:\/\/ body}b")
    keys = "test" + EX + "hi"
    wanted = "h// bodybhi"
class VisualWithDefault_ExpandWithVisual(_VimTest):
    snippets = ("test", "h${VISUAL:world}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hblablubb"

class Visual_ExpandTwice(_VimTest):
    snippets = ("test", "h${VISUAL}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX + "\ntest" + EX
    wanted = "hblablubb\nhb"

class Visual_SelectOneWord_TwiceVisual(_VimTest):
    snippets = ("test", "h${VISUAL}b${VISUAL}a")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hblablubbblabluba"
class Visual_SelectOneWord_Inword(_VimTest):
    snippets = ("test", "h${VISUAL}b", "Description", "i")
    keys = "blablub" + ESC + "0lv4l" + EX + "test" + EX
    wanted = "bhlablubb"
class Visual_SelectOneWord_TillEndOfLine(_VimTest):
    snippets = ("test", "h${VISUAL}b", "Description", "i")
    keys = "blablub" + ESC + "0v$" + EX + "test" + EX + ESC + "o"
    wanted = "hblablub\nb"
class Visual_SelectOneWordWithTabstop_TillEndOfLine(_VimTest):
    snippets = ("test", "h${2:ahh}${VISUAL}${1:ups}b", "Description", "i")
    keys = "blablub" + ESC + "0v$" + EX + "test" + EX + "mmm" + JF + "n" + JF + "done" + ESC + "o"
    wanted = "hnblablub\nmmmbdone"
class Visual_InDefaultText_SelectOneWord_NoOverwrite(_VimTest):
    snippets = ("test", "h${1:${VISUAL}}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX + JF + "hello"
    wanted = "hblablubbhello"
class Visual_InDefaultText_SelectOneWord(_VimTest):
    snippets = ("test", "h${1:${VISUAL}}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX + "hello"
    wanted = "hhellob"

class Visual_CrossOneLine(_VimTest):
    snippets = ("test", "h${VISUAL}b")
    keys = "bla blub\n  helloi" + ESC + "0k4lvjll" + EX + "test" + EX
    wanted = "bla hblub\n  hellobi"

class Visual_LineSelect_Simple(_VimTest):
    snippets = ("test", "h${VISUAL}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "hhello\n nice\n worldb"
class Visual_InDefaultText_LineSelect_NoOverwrite(_VimTest):
    snippets = ("test", "h${1:bef${VISUAL}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + JF + "hi"
    wanted = "hbefhello\n    nice\n    worldaftbhi"
class Visual_InDefaultText_LineSelect_Overwrite(_VimTest):
    snippets = ("test", "h${1:bef${VISUAL}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + "jup" + JF + "hi"
    wanted = "hjupbhi"
class Visual_LineSelect_CheckIndentSimple(_VimTest):
    snippets = ("test", "beg\n\t${VISUAL}\nend")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "beg\n\thello\n\tnice\n\tworld\nend"
class Visual_LineSelect_CheckIndentTwice(_VimTest):
    snippets = ("test", "beg\n\t${VISUAL}\nend")
    keys = "    hello\n    nice\n\tworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "beg\n\t    hello\n\t    nice\n\t\tworld\nend"
class Visual_InDefaultText_IndentSpacesToTabstop_NoOverwrite(_VimTest):
    snippets = ("test", "h${1:beforea${VISUAL}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + JF + "hi"
    wanted = "hbeforeahello\n\tnice\n\tworldaftbhi"
class Visual_InDefaultText_IndentSpacesToTabstop_Overwrite(_VimTest):
    snippets = ("test", "h${1:beforea${VISUAL}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + "ups" + JF + "hi"
    wanted = "hupsbhi"
class Visual_InDefaultText_IndentSpacesToTabstop_NoOverwrite1(_VimTest):
    snippets = ("test", "h${1:beforeaaa${VISUAL}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + JF + "hi"
    wanted = "hbeforeaaahello\n\t  nice\n\t  worldaftbhi"
class Visual_InDefaultText_IndentBeforeTabstop_NoOverwrite(_VimTest):
    snippets = ("test", "hello\n\t ${1:${VISUAL}}\nend")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + JF + "hi"
    wanted = "hello\n\t hello\n\t nice\n\t world\nendhi"

class Visual_LineSelect_WithTabStop(_VimTest):
    snippets = ("test", "beg\n\t${VISUAL}\n\t${1:here_we_go}\nend")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + "super" + JF + "done"
    wanted = "beg\n\thello\n\tnice\n\tworld\n\tsuper\nenddone"
class Visual_LineSelect_CheckIndentWithTS_NoOverwrite(_VimTest):
    snippets = ("test", "beg\n\t${0:${VISUAL}}\nend")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "beg\n\thello\n\tnice\n\tworld\nend"
class Visual_LineSelect_DedentLine(_VimTest):
    snippets = ("if", "if {\n\t${VISUAL}$0\n}")
    keys = "if" + EX + "one\n\ttwo\n\tthree" + ESC + ARR_U*2 + "V" + ARR_D + EX + "\tif" + EX
    wanted = "if {\n\tif {\n\t\tone\n\t\ttwo\n\t}\n\tthree\n}"

class VisualTransformation_SelectOneWord(_VimTest):
    snippets = ("test", r"h${VISUAL/./\U$0\E/g}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hBLABLUBb"
class VisualTransformationWithDefault_ExpandWithoutVisual(_VimTest):
    snippets = ("test", r"h${VISUAL:world/./\U$0\E/g}b")
    keys = "test" + EX + "hi"
    wanted = "hWORLDbhi"
class VisualTransformationWithDefault_ExpandWithVisual(_VimTest):
    snippets = ("test", r"h${VISUAL:world/./\U$0\E/g}b")
    keys = "blablub" + ESC + "0v6l" + EX + "test" + EX
    wanted = "hBLABLUBb"
class VisualTransformation_LineSelect_Simple(_VimTest):
    snippets = ("test", r"h${VISUAL/./\U$0\E/g}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX
    wanted = "hHELLO\n NICE\n WORLDb"
class VisualTransformation_InDefaultText_LineSelect_NoOverwrite(_VimTest):
    snippets = ("test", r"h${1:bef${VISUAL/./\U$0\E/g}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + JF + "hi"
    wanted = "hbefHELLO\n    NICE\n    WORLDaftbhi"
class VisualTransformation_InDefaultText_LineSelect_Overwrite(_VimTest):
    snippets = ("test", r"h${1:bef${VISUAL/./\U$0\E/g}aft}b")
    keys = "hello\nnice\nworld" + ESC + "Vkk" + EX + "test" + EX + "jup" + JF + "hi"
    wanted = "hjupbhi"

# End: ${VISUAL}  #}}}

# Recursive (Nested) Snippets  {{{#
class RecTabStops_SimpleCase_ExpectCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + "world" + JF + "ups" + JF + "end"
    wanted = "[ [ hello  world ]ups  end ]"
class RecTabStops_SimpleCaseLeaveSecondSecond_ExpectCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + "world" + JF + JF + JF + "end"
    wanted = "[ [ hello  world ]  sec ]end"
class RecTabStops_SimpleCaseLeaveFirstSecond_ExpectCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "m" + EX + "hello" + JF + JF + JF + "world" + JF + "end"
    wanted = "[ [ hello  sec ]  world ]end"

class RecTabStops_InnerWOTabStop_ECR(_VimTest):
    snippets = (
        ("m1", "Just some Text"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "hi" + JF + "two" + JF + "end"
    wanted = "[ Just some Texthi  two ]end"
class RecTabStops_InnerWOTabStopTwiceDirectly_ECR(_VimTest):
    snippets = (
        ("m1", "JST"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + " m1" + EX + "hi" + JF + "two" + JF + "end"
    wanted = "[ JST JSThi  two ]end"
class RecTabStops_InnerWOTabStopTwice_ECR(_VimTest):
    snippets = (
        ("m1", "JST"),
        ("m", "[ ${1:first}  ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + JF + "m1" + EX + "hi" + JF + "end"
    wanted = "[ JST  JSThi ]end"
class RecTabStops_OuterOnlyWithZeroTS_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B"
class RecTabStops_OuterOnlyWithZero_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B"
class RecTabStops_ExpandedInZeroTS_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m1" + EX + "CD" + JF + "DE"
    wanted = "A C CD D DE E B hi"
class RecTabStops_ExpandedInZeroTSTwice_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m" + EX + "again" + JF + "m1" + \
            EX + "CD" + JF + "DE"
    wanted = "A A C CD D DE E B again B hi"
class RecTabStops_ExpandedInZeroTSSecondTime_ECR(_VimTest):
    snippets = (
        ("m", "A $0 B $1"),
        ("m1", "C $1 D $0 E"),
    )
    keys = "m" + EX + "hi" + JF + "m" + EX + "m1" + EX + "CD" + JF + "DE" + JF + "AB"
    wanted = "A A AB B C CD D DE E B hi"
class RecTabsStops_TypeInZero_ECR(_VimTest):
    snippets = (
        ("v", r"\vec{$1}", "Vector", "w"),
        ("frac", r"\frac{${1:one}}${0:zero}{${2:two}}", "Fractio", "w"),
    )
    keys = "v" + EX + "frac" + EX + "a" + JF + "b" + JF + "frac" + EX + "aa" + JF + JF + "cc" + JF + \
            "hello frac" + EX + JF + JF + "world"
    wanted = r"\vec{\frac{a}\frac{aa}cc{two}{b}}hello \frac{one}world{two}"
class RecTabsStops_TypeInZero2_ECR(_VimTest):
    snippets = (
        ("m", r"_${0:explicit zero}", "snip", "i"),
    )
    keys = "m" + EX + "hello m" + EX + "world m" + EX + "end"
    wanted = r"_hello _world _end"
class RecTabsStops_BackspaceZero_ECR(_VimTest):
    snippets = (
        ("m", r"${1:one}${0:explicit zero}${2:two}", "snip", "i"),
    )
    keys = "m" + EX + JF + JF + BS + "m" + EX
    wanted = r"oneoneexplicit zerotwotwo"


class RecTabStops_MirrorInnerSnippet_ECR(_VimTest):
    snippets = (
        ("m", "[ $1 $2 ] $1"),
        ("m1", "ASnip $1 ASnip $2 ASnip"),
    )
    keys = "m" + EX + "m1" + EX + "Hallo" + JF + "Hi" + JF + "endone" + JF + "two" + JF + "totalend"
    wanted = "[ ASnip Hallo ASnip Hi ASnipendone two ] ASnip Hallo ASnip Hi ASnipendonetotalend"

class RecTabStops_NotAtBeginningOfTS_ExpectCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello m" + EX + "hi" + JF + "two" + JF + "ups" + JF + "three" + \
            JF + "end"
    wanted = "[ hello [ hi  two ]ups  three ]end"
class RecTabStops_InNewlineInTabstop_ExpectCorrectResult(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello\nm" + EX + "hi" + JF + "two" + JF + "ups" + JF + "three" + \
            JF + "end"
    wanted = "[ hello\n[ hi  two ]ups  three ]end"
class RecTabStops_InNewlineInTabstopNotAtBeginOfLine_ECR(_VimTest):
    snippets = ("m", "[ ${1:first}  ${2:sec} ]")
    keys = "m" + EX + "hello\nhello again m" + EX + "hi" + JF + "two" + \
            JF + "ups" + JF + "three" + JF + "end"
    wanted = "[ hello\nhello again [ hi  two ]ups  three ]end"

class RecTabStops_InNewlineMultiline_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "m" + EX
    wanted = "M START\nM START\n\nM END\nM END"
class RecTabStops_InNewlineManualIndent_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "    m" + EX + "hi"
    wanted = "M START\n    M START\n    hi\n    M END\nM END"
class RecTabStops_InNewlineManualIndentTextInFront_ECR(_VimTest):
    snippets = ("m", "M START\n$0\nM END")
    keys = "m" + EX + "    hallo m" + EX + "hi"
    wanted = "M START\n    hallo M START\n    hi\n    M END\nM END"
class RecTabStops_InNewlineMultilineWithIndent_ECR(_VimTest):
    snippets = ("m", "M START\n    $0\nM END")
    keys = "m" + EX + "m" + EX + "hi"
    wanted = "M START\n    M START\n        hi\n    M END\nM END"
class RecTabStops_InNewlineMultilineWithNonZeroTS_ECR(_VimTest):
    snippets = ("m", "M START\n    $1\nM END -> $0")
    keys = "m" + EX + "m" + EX + "hi" + JF + "hallo" + JF + "end"
    wanted = "M START\n    M START\n        hi\n    M END -> hallo\n" \
        "M END -> end"

class RecTabStops_BarelyNotLeavingInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "a" + 3*ARR_L + JF + "hallo" + \
            JF + "ups" + JF + "world" + JF + "end"
    wanted = "[ [ a hallo ]ups world ]end"
class RecTabStops_LeavingInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "a" + 4*ARR_L + JF + "hallo" + \
            JF + "world"
    wanted = "[ [ a sec ] hallo ]world"
class RecTabStops_LeavingInnerInner_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "m" + EX + "a" + 4*ARR_L + JF + "hallo" + \
            JF + "ups" + JF + "world" + JF + "end"
    wanted = "[ [ [ a sec ] hallo ]ups world ]end"
class RecTabStops_LeavingInnerInnerTwo_ECR(_VimTest):
    snippets = (
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m" + EX + "m" + EX + "a" + 6*ARR_L + JF + "hallo" + \
            JF + "end"
    wanted = "[ [ [ a sec ] sec ] hallo ]end"


class RecTabStops_ZeroTSisNothingSpecial_ECR(_VimTest):
    snippets = (
        ("m1", "[ ${1:first} $0 ${2:sec} ]"),
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "one" + JF + "two" + \
            JF + "three" + JF + "four" + JF + "end"
    wanted = "[ [ one three two ] four ]end"
class RecTabStops_MirroredZeroTS_ECR(_VimTest):
    snippets = (
        ("m1", "[ ${1:first} ${0:Year, some default text} $0 ${2:sec} ]"),
        ("m", "[ ${1:first} ${2:sec} ]"),
    )
    keys = "m" + EX + "m1" + EX + "one" + JF + "two" + \
            JF + "three" + JF + "four" + JF + "end"
    wanted = "[ [ one three three two ] four ]end"
class RecTabStops_ChildTriggerContainsParentTextObjects(_VimTest):
    # https://bugs.launchpad.net/bugs/1191617
    files = { "us/all.snippets": r"""
global !p
def complete(t, opts):
 if t:
   opts = [ q[len(t):] for q in opts if q.startswith(t) ]
 if len(opts) == 0:
   return ''
 return opts[0] if len(opts) == 1 else "(" + '|'.join(opts) + ')'
def autocomplete_options(t, string, attr=None):
   return complete(t[1], [opt for opt in attr if opt not in string])
endglobal
snippet /form_for(.*){([^|]*)/ "form_for html options" rw!
`!p
auto = autocomplete_options(t, match.group(2), attr=["id: ", "class: ", "title:  "])
snip.rv = "form_for" + match.group(1) + "{"`$1`!p if (snip.c != auto) : snip.rv=auto`
endsnippet
"""}
    keys = "form_for user, namespace: some_namespace, html: {i" + EX + "i" + EX
    wanted = "form_for user, namespace: some_namespace, html: {(id: |class: |title:  )d: "
# End: Recursive (Nested) Snippets  #}}}
# List Snippets  {{{#
class _ListAllSnippets(_VimTest):
    snippets = ( ("testblah", "BLAAH", "Say BLAH"),
                 ("test", "TEST ONE", "Say tst one"),
                 ("aloha", "OHEEEE",   "Say OHEE"),
               )

class ListAllAvailable_NothingTyped_ExpectCorrectResult(_ListAllSnippets):
    keys = "" + LS + "3\n"
    wanted = "BLAAH"
class ListAllAvailable_SpaceInFront_ExpectCorrectResult(_ListAllSnippets):
    keys = " " + LS + "3\n"
    wanted = " BLAAH"
class ListAllAvailable_BraceInFront_ExpectCorrectResult(_ListAllSnippets):
    keys = "} " + LS + "3\n"
    wanted = "} BLAAH"
class ListAllAvailable_testtyped_ExpectCorrectResult(_ListAllSnippets):
    keys = "hallo test" + LS + "2\n"
    wanted = "hallo BLAAH"
class ListAllAvailable_testtypedSecondOpt_ExpectCorrectResult(_ListAllSnippets):
    keys = "hallo test" + LS + "1\n"
    wanted = "hallo TEST ONE"

class ListAllAvailable_NonDefined_NoExpectionShouldBeRaised(_ListAllSnippets):
    keys = "hallo qualle" + LS + "Hi"
    wanted = "hallo qualleHi"
# End: List Snippets  #}}}
# Selecting Between Same Triggers  {{{#
class _MultipleMatches(_VimTest):
    snippets = ( ("test", "Case1", "This is Case 1"),
                 ("test", "Case2", "This is Case 2") )
class Multiple_SimpleCaseSelectFirst_ECR(_MultipleMatches):
    keys = "test" + EX + "1\n"
    wanted = "Case1"
class Multiple_SimpleCaseSelectSecond_ECR(_MultipleMatches):
    keys = "test" + EX + "2\n"
    wanted = "Case2"
class Multiple_SimpleCaseSelectTooHigh_ESelectLast(_MultipleMatches):
    keys = "test" + EX + "5\n"
    wanted = "Case2"
class Multiple_SimpleCaseSelectZero_EEscape(_MultipleMatches):
    keys = "test" + EX + "0\n" + "hi"
    wanted = "testhi"
class Multiple_SimpleCaseEscapeOut_ECR(_MultipleMatches):
    keys = "test" + EX + ESC + "hi"
    wanted = "testhi"
class Multiple_ManySnippetsOneTrigger_ECR(_VimTest):
    # Snippet definition {{{#
    snippets = (
        ("test", "Case1", "This is Case 1"),
        ("test", "Case2", "This is Case 2"),
        ("test", "Case3", "This is Case 3"),
        ("test", "Case4", "This is Case 4"),
        ("test", "Case5", "This is Case 5"),
        ("test", "Case6", "This is Case 6"),
        ("test", "Case7", "This is Case 7"),
        ("test", "Case8", "This is Case 8"),
        ("test", "Case9", "This is Case 9"),
        ("test", "Case10", "This is Case 10"),
        ("test", "Case11", "This is Case 11"),
        ("test", "Case12", "This is Case 12"),
        ("test", "Case13", "This is Case 13"),
        ("test", "Case14", "This is Case 14"),
        ("test", "Case15", "This is Case 15"),
        ("test", "Case16", "This is Case 16"),
        ("test", "Case17", "This is Case 17"),
        ("test", "Case18", "This is Case 18"),
        ("test", "Case19", "This is Case 19"),
        ("test", "Case20", "This is Case 20"),
        ("test", "Case21", "This is Case 21"),
        ("test", "Case22", "This is Case 22"),
        ("test", "Case23", "This is Case 23"),
        ("test", "Case24", "This is Case 24"),
        ("test", "Case25", "This is Case 25"),
        ("test", "Case26", "This is Case 26"),
        ("test", "Case27", "This is Case 27"),
        ("test", "Case28", "This is Case 28"),
        ("test", "Case29", "This is Case 29"),
    ) #}}}
    keys = "test" + EX + " " + ESC + ESC + "ahi"
    wanted = "testhi"
# End: Selecting Between Same Triggers  #}}}
# Snippet Priority  {{{#
class SnippetPriorities_MultiWordTriggerOverwriteExisting(_VimTest):
    snippets = (
     ("test me", "${1:Hallo}", "Types Hallo"),
     ("test me", "${1:World}", "Types World"),
     ("test me", "We overwrite", "Overwrite the two", "", 1),
    )
    keys = "test me" + EX
    wanted = "We overwrite"
class SnippetPriorities_DoNotCareAboutNonMatchings(_VimTest):
    snippets = (
     ("test1", "Hallo", "Types Hallo"),
     ("test2", "We overwrite", "Overwrite the two", "", 1),
    )
    keys = "test1" + EX
    wanted = "Hallo"
class SnippetPriorities_OverwriteExisting(_VimTest):
    snippets = (
     ("test", "${1:Hallo}", "Types Hallo"),
     ("test", "${1:World}", "Types World"),
     ("test", "We overwrite", "Overwrite the two", "", 1),
    )
    keys = "test" + EX
    wanted = "We overwrite"
class SnippetPriorities_OverwriteTwice_ECR(_VimTest):
    snippets = (
        ("test", "${1:Hallo}", "Types Hallo"),
        ("test", "${1:World}", "Types World"),
        ("test", "We overwrite", "Overwrite the two", "", 1),
        ("test", "again", "Overwrite again", "", 2),
    )
    keys = "test" + EX
    wanted = "again"
class SnippetPriorities_OverwriteThenChoose_ECR(_VimTest):
    snippets = (
        ("test", "${1:Hallo}", "Types Hallo"),
        ("test", "${1:World}", "Types World"),
        ("test", "We overwrite", "Overwrite the two", "", 1),
        ("test", "No overwrite", "Not overwritten", "", 1),
    )
    keys = "test" + EX + "1\n\n" + "test" + EX + "2\n"
    wanted = "We overwrite\nNo overwrite"
class SnippetPriorities_AddedHasHigherThanFile(_VimTest):
    files = { "us/all.snippets": r"""
        snippet test "Test Snippet" b
        This is a test snippet
        endsnippet
        """}
    snippets = (
        ("test", "We overwrite", "Overwrite the two", "", 1),
    )
    keys = "test" + EX
    wanted = "We overwrite"
class SnippetPriorities_FileHasHigherThanAdded(_VimTest):
    files = { "us/all.snippets": r"""
        snippet test "Test Snippet" b
        This is a test snippet
        endsnippet
        """}
    snippets = (
        ("test", "We do not overwrite", "Overwrite the two", "", -1),
    )
    keys = "test" + EX
    wanted = "This is a test snippet"
class SnippetPriorities_FileHasHigherThanAdded(_VimTest):
    files = { "us/all.snippets": r"""
        priority -3
        snippet test "Test Snippet" b
        This is a test snippet
        endsnippet
        """}
    snippets = (
        ("test", "We overwrite", "Overwrite the two", "", -5),
    )
    keys = "test" + EX
    wanted = "This is a test snippet"
# End: Snippet Priority  #}}}


# Snippet Options  {{{#
class SnippetOptions_OnlyExpandWhenWSInFront_Expand(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_OnlyExpandWhenWSInFront_Expand2(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "   test" + EX
    wanted = "   Expand me!"
class SnippetOptions_OnlyExpandWhenWSInFront_DontExpand(_VimTest):
    snippets = ("test", "Expand me!", "", "b")
    keys = "a test" + EX
    wanted = "a test" + EX
class SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWO(_VimTest):
    snippets = (
        ("test", "Expand me!", "", "b"),
        ("test", "not at beginning", "", ""),
    )
    keys = "a test" + EX
    wanted = "a not at beginning"
class SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWOChoose(_VimTest):
    snippets = (
        ("test", "Expand me!", "", "b"),
        ("test", "not at beginning", "", ""),
    )
    keys = "  test" + EX + "1\n"
    wanted = "  Expand me!"


class SnippetOptions_ExpandInwordSnippets_SimpleExpand(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "atest" + EX
    wanted = "aExpand me!"
class SnippetOptions_ExpandInwordSnippets_ExpandSingle(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "$test" + EX
    wanted = "$Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand2(_VimTest):
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "-test" + EX
    wanted = "-Expand me!"
class SnippetOptions_ExpandInwordSnippetsWithOtherChars_Expand3(_VimTest):
    skip_if = lambda self: running_on_windows()
    snippets = (("test", "Expand me!", "", "i"), )
    keys = "ßßtest" + EX
    wanted = "ßßExpand me!"

class _SnippetOptions_ExpandWordSnippets(_VimTest):
    snippets = (("test", "Expand me!", "", "w"), )
class SnippetOptions_ExpandWordSnippets_NormalExpand(
        _SnippetOptions_ExpandWordSnippets):
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_ExpandWordSnippets_NoExpand(
    _SnippetOptions_ExpandWordSnippets):
    keys = "atest" + EX
    wanted = "atest" + EX
class SnippetOptions_ExpandWordSnippets_ExpandSuffix(
    _SnippetOptions_ExpandWordSnippets):
    keys = "a-test" + EX
    wanted = "a-Expand me!"
class SnippetOptions_ExpandWordSnippets_ExpandSuffix2(
    _SnippetOptions_ExpandWordSnippets):
    keys = "a(test" + EX
    wanted = "a(Expand me!"
class SnippetOptions_ExpandWordSnippets_ExpandSuffix3(
    _SnippetOptions_ExpandWordSnippets):
    keys = "[[test" + EX
    wanted = "[[Expand me!"

class _No_Tab_Expand(_VimTest):
    snippets = ("test", "\t\tExpand\tme!\t", "", "t")
class No_Tab_Expand_Simple(_No_Tab_Expand):
    keys = "test" + EX
    wanted = "\t\tExpand\tme!\t"
class No_Tab_Expand_Leading_Spaces(_No_Tab_Expand):
    keys = "  test" + EX
    wanted = "  \t\tExpand\tme!\t"
class No_Tab_Expand_Leading_Tabs(_No_Tab_Expand):
    keys = "\ttest" + EX
    wanted = "\t\t\tExpand\tme!\t"
class No_Tab_Expand_No_TS(_No_Tab_Expand):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set sts=3")
    keys = "test" + EX
    wanted = "\t\tExpand\tme!\t"
class No_Tab_Expand_ET(_No_Tab_Expand):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set expandtab")
    keys = "test" + EX
    wanted = "\t\tExpand\tme!\t"
class No_Tab_Expand_ET_Leading_Spaces(_No_Tab_Expand):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set expandtab")
    keys = "  test" + EX
    wanted = "  \t\tExpand\tme!\t"
class No_Tab_Expand_ET_SW(_No_Tab_Expand):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=8")
        vim_config.append("set expandtab")
    keys = "test" + EX
    wanted = "\t\tExpand\tme!\t"
class No_Tab_Expand_ET_SW_TS(_No_Tab_Expand):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set sts=3")
        vim_config.append("set ts=3")
        vim_config.append("set expandtab")
    keys = "test" + EX
    wanted = "\t\tExpand\tme!\t"

class _TabExpand_RealWorld(object):
    snippets = ("hi",
r"""hi
`!p snip.rv="i1\n"
snip.rv += snip.mkline("i1\n")
snip.shift(1)
snip.rv += snip.mkline("i2\n")
snip.unshift(2)
snip.rv += snip.mkline("i0\n")
snip.shift(3)
snip.rv += snip.mkline("i3")`
snip.rv = repr(snip.rv)
End""")

class No_Tab_Expand_RealWorld(_TabExpand_RealWorld,_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set noexpandtab")
    keys = "\t\thi" + EX
    wanted = """\t\thi
\t\ti1
\t\ti1
\t\t\ti2
\ti0
\t\t\t\ti3
\t\tsnip.rv = repr(snip.rv)
\t\tEnd"""


class SnippetOptions_Regex_Expand(_VimTest):
    snippets = ("(test)", "Expand me!", "", "r")
    keys = "test" + EX
    wanted = "Expand me!"
class SnippetOptions_Regex_Multiple(_VimTest):
    snippets = ("(test *)+", "Expand me!", "", "r")
    keys = "test test test" + EX
    wanted = "Expand me!"

class _Regex_Self(_VimTest):
    snippets = ("((?<=\W)|^)(\.)", "self.", "", "r")
class SnippetOptions_Regex_Self_Start(_Regex_Self):
    keys = "." + EX
    wanted = "self."
class SnippetOptions_Regex_Self_Space(_Regex_Self):
    keys = " ." + EX
    wanted = " self."
class SnippetOptions_Regex_Self_TextAfter(_Regex_Self):
    keys = " .a" + EX
    wanted = " .a" + EX
class SnippetOptions_Regex_Self_TextBefore(_Regex_Self):
    keys = "a." + EX
    wanted = "a." + EX
class SnippetOptions_Regex_PythonBlockMatch(_VimTest):
    snippets = (r"([abc]+)([def]+)", r"""`!p m = match
snip.rv += m.group(2)
snip.rv += m.group(1)
`""", "", "r")
    keys = "test cabfed" + EX
    wanted = "test fedcab"
class SnippetOptions_Regex_PythonBlockNoMatch(_VimTest):
    snippets = (r"cabfed", r"""`!p snip.rv =  match or "No match"`""")
    keys = "test cabfed" + EX
    wanted = "test No match"
# Tests for Bug #691575
class SnippetOptions_Regex_SameLine_Long_End(_VimTest):
    snippets = ("(test.*)", "Expand me!", "", "r")
    keys = "test test abc" + EX
    wanted = "Expand me!"
class SnippetOptions_Regex_SameLine_Long_Start(_VimTest):
    snippets = ("(.*test)", "Expand me!", "", "r")
    keys = "abc test test" + EX
    wanted = "Expand me!"
class SnippetOptions_Regex_SameLine_Simple(_VimTest):
    snippets = ("(test)", "Expand me!", "", "r")
    keys = "abc test test" + EX
    wanted = "abc test Expand me!"


class MultiWordSnippet_Simple(_VimTest):
    snippets = ("test me", "Expand me!")
    keys = "test me" + EX
    wanted = "Expand me!"
class MultiWord_SnippetOptions_OnlyExpandWhenWSInFront_Expand(_VimTest):
    snippets = ("test it", "Expand me!", "", "b")
    keys = "test it" + EX
    wanted = "Expand me!"
class MultiWord_SnippetOptions_OnlyExpandWhenWSInFront_Expand2(_VimTest):
    snippets = ("test it", "Expand me!", "", "b")
    keys = "   test it" + EX
    wanted = "   Expand me!"
class MultiWord_SnippetOptions_OnlyExpandWhenWSInFront_DontExpand(_VimTest):
    snippets = ("test it", "Expand me!", "", "b")
    keys = "a test it" + EX
    wanted = "a test it" + EX
class MultiWord_SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWO(_VimTest):
    snippets = (
        ("test it", "Expand me!", "", "b"),
        ("test it", "not at beginning", "", ""),
    )
    keys = "a test it" + EX
    wanted = "a not at beginning"
class MultiWord_SnippetOptions_OnlyExpandWhenWSInFront_OneWithOneWOChoose(_VimTest):
    snippets = (
        ("test it", "Expand me!", "", "b"),
        ("test it", "not at beginning", "", ""),
    )
    keys = "  test it" + EX + "1\n"
    wanted = "  Expand me!"

class MultiWord_SnippetOptions_ExpandInwordSnippets_SimpleExpand(_VimTest):
    snippets = (("test it", "Expand me!", "", "i"), )
    keys = "atest it" + EX
    wanted = "aExpand me!"
class MultiWord_SnippetOptions_ExpandInwordSnippets_ExpandSingle(_VimTest):
    snippets = (("test it", "Expand me!", "", "i"), )
    keys = "test it" + EX
    wanted = "Expand me!"

class _MultiWord_SnippetOptions_ExpandWordSnippets(_VimTest):
    snippets = (("test it", "Expand me!", "", "w"), )
class MultiWord_SnippetOptions_ExpandWordSnippets_NormalExpand(
        _MultiWord_SnippetOptions_ExpandWordSnippets):
    keys = "test it" + EX
    wanted = "Expand me!"
class MultiWord_SnippetOptions_ExpandWordSnippets_NoExpand(
    _MultiWord_SnippetOptions_ExpandWordSnippets):
    keys = "atest it" + EX
    wanted = "atest it" + EX
class MultiWord_SnippetOptions_ExpandWordSnippets_ExpandSuffix(
    _MultiWord_SnippetOptions_ExpandWordSnippets):
    keys = "a-test it" + EX
    wanted = "a-Expand me!"
# Snippet Options  #}}}

# Anonymous Expansion  {{{#
class _AnonBase(_VimTest):
    args = ""
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("inoremap <silent> %s <C-R>=UltiSnips#Anon(%s)<cr>"
                % (EA, self.args))

class Anon_NoTrigger_Simple(_AnonBase):
    args = '"simple expand"'
    keys = "abc" + EA
    wanted = "abcsimple expand"

class Anon_NoTrigger_AfterSpace(_AnonBase):
    args = '"simple expand"'
    keys = "abc " + EA
    wanted = "abc simple expand"

class Anon_NoTrigger_BeginningOfLine(_AnonBase):
    args = r"':latex:\`$1\`$0'"
    keys = EA + "Hello" + JF + "World"
    wanted = ":latex:`Hello`World"
class Anon_NoTrigger_FirstCharOfLine(_AnonBase):
    args = r"':latex:\`$1\`$0'"
    keys = " " + EA + "Hello" + JF + "World"
    wanted = " :latex:`Hello`World"

class Anon_NoTrigger_Multi(_AnonBase):
    args = '"simple $1 expand $1 $0"'
    keys = "abc" + EA + "123" + JF + "456"
    wanted = "abcsimple 123 expand 123 456"

class Anon_Trigger_Multi(_AnonBase):
    args = '"simple $1 expand $1 $0", "abc"'
    keys = "123 abc" + EA + "123" + JF + "456"
    wanted = "123 simple 123 expand 123 456"

class Anon_Trigger_Simple(_AnonBase):
    args = '"simple expand", "abc"'
    keys = "abc" + EA
    wanted = "simple expand"

class Anon_Trigger_Twice(_AnonBase):
    args = '"simple expand", "abc"'
    keys = "abc" + EA + "\nabc" + EX
    wanted = "simple expand\nabc" + EX

class Anon_Trigger_Opts(_AnonBase):
    args = '"simple expand", ".*abc", "desc", "r"'
    keys = "blah blah abc" + EA
    wanted = "simple expand"
# End: Anonymous Expansion  #}}}
# AddSnippet Function  {{{#
class _AddFuncBase(_VimTest):
    args = ""
    def _extra_options_pre_init(self, vim_config):
        vim_config.append(":call UltiSnips#AddSnippetWithPriority(%s)" %
                self.args)

class AddFunc_Simple(_AddFuncBase):
    args = '"test", "simple expand", "desc", "", "all", 0'
    keys = "abc test" + EX
    wanted = "abc simple expand"

class AddFunc_Opt(_AddFuncBase):
    args = '".*test", "simple expand", "desc", "r", "all", 0'
    keys = "abc test" + EX
    wanted = "simple expand"
# End: AddSnippet Function  #}}}

# ExpandTab  {{{#
class _ExpandTabs(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set sw=3")
        vim_config.append("set expandtab")

class RecTabStopsWithExpandtab_SimpleExample_ECR(_ExpandTabs):
    snippets = ("m", "\tBlaahblah \t\t  ")
    keys = "m" + EX
    wanted = "   Blaahblah \t\t  "

class RecTabStopsWithExpandtab_SpecialIndentProblem_ECR(_ExpandTabs):
    # Windows indents the Something line after pressing return, though it
    # shouldn't because it contains a manual indent. All other vim versions do
    # not do this. Windows vim does not interpret the changes made by :py as
    # changes made 'manually', while the other vim version seem to do so. Since
    # the fault is not with UltiSnips, we simply skip this test on windows
    # completely.
    skip_if = lambda self: running_on_windows()
    snippets = (
        ("m1", "Something"),
        ("m", "\t$0"),
    )
    keys = "m" + EX + "m1" + EX + '\nHallo'
    wanted = "   Something\n        Hallo"
    def _extra_options_pre_init(self, vim_config):
        _ExpandTabs._extra_options_pre_init(self, vim_config)
        vim_config.append("set indentkeys=o,O,*<Return>,<>>,{,}")
        vim_config.append("set indentexpr=8")
# End: ExpandTab  #}}}
# Proper Indenting  {{{#
class ProperIndenting_SimpleCase_ECR(_VimTest):
    snippets = ("test", "for\n    blah")
    keys = "    test" + EX + "Hui"
    wanted = "    for\n        blahHui"
class ProperIndenting_SingleLineNoReindenting_ECR(_VimTest):
    snippets = ("test", "hui")
    keys = "    test" + EX + "blah"
    wanted = "    huiblah"
class ProperIndenting_AutoIndentAndNewline_ECR(_VimTest):
    snippets = ("test", "hui")
    keys = "    test" + EX + "\n"+ "blah"
    wanted = "    hui\n    blah"
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set autoindent")
# Test for bug 1073816
class ProperIndenting_FirstLineInFile_ECR(_VimTest):
    text_before = ""
    text_after = ""
    files = { "us/all.snippets": r"""
global !p
def complete(t, opts):
  if t:
    opts = [ m[len(t):] for m in opts if m.startswith(t) ]
  if len(opts) == 1:
    return opts[0]
  elif len(opts) > 1:
    return "(" + "|".join(opts) + ")"
  else:
    return ""
endglobal

snippet '^#?inc' "#include <>" !r
#include <$1`!p snip.rv = complete(t[1], ['cassert', 'cstdio', 'cstdlib', 'cstring', 'fstream', 'iostream', 'sstream'])`>
endsnippet
        """}
    keys = "inc" + EX + "foo"
    wanted = "#include <foo>"
class ProperIndenting_FirstLineInFileComplete_ECR(ProperIndenting_FirstLineInFile_ECR):
    keys = "inc" + EX + "cstdl"
    wanted = "#include <cstdlib>"
# End: Proper Indenting  #}}}
# Format options tests  {{{#
class _FormatoptionsBase(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set tw=20")
        vim_config.append("set fo=lrqntc")

class FOSimple_Break_ExpectCorrectResult(_FormatoptionsBase):
    snippets = ("test", "${1:longer expand}\n$1\n$0", "", "f")
    keys = "test" + EX + "This is a longer text that should wrap as formatoptions are  enabled" + JF + "end"
    wanted = "This is a longer\ntext that should\nwrap as\nformatoptions are\nenabled\n" + \
        "This is a longer\ntext that should\nwrap as\nformatoptions are\nenabled\n" + "end"


class FOTextBeforeAndAfter_ExpectCorrectResult(_FormatoptionsBase):
    snippets = ("test", "Before${1:longer expand}After\nstart$1end")
    keys = "test" + EX + "This is a longer text that should wrap"
    wanted = \
"""BeforeThis is a
longer text that
should wrapAfter
startThis is a
longer text that
should wrapend"""


# Tests for https://bugs.launchpad.net/bugs/719998
class FOTextAfter_ExpectCorrectResult(_FormatoptionsBase):
    snippets = ("test", "${1:longer expand}after\nstart$1end")
    keys = ("test" + EX + "This is a longer snippet that should wrap properly "
            "and the mirror below should work as well")
    wanted = \
"""This is a longer
snippet that should
wrap properly and
the mirror below
should work as wellafter
startThis is a longer
snippet that should
wrap properly and
the mirror below
should work as wellend"""

class FOWrapOnLongWord_ExpectCorrectResult(_FormatoptionsBase):
    snippets = ("test", "${1:longer expand}after\nstart$1end")
    keys = ("test" + EX + "This is a longersnippet that should wrap properly")
    wanted = \
"""This is a
longersnippet that
should wrap properlyafter
startThis is a
longersnippet that
should wrap properlyend"""
# End: Format options tests  #}}}
# Langmap Handling  {{{#
# Test for bug 501727 #
class TestNonEmptyLangmap_ExpectCorrectResult(_VimTest):
    snippets = ("testme",
"""my snipped ${1:some_default}
and a mirror: $1
$2...$3
$0""")
    keys = "testme" + EX + "hi1" + JF + "hi2" + JF + "hi3" + JF + "hi4"
    wanted ="""my snipped hi1
and a mirror: hi1
hi2...hi3
hi4"""
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set langmap=dj,rk,nl,ln,jd,kr,DJ,RK,NL,LN,JD,KR")

# Test for https://bugs.launchpad.net/bugs/501727 #
class TestNonEmptyLangmapWithSemi_ExpectCorrectResult(_VimTest):
    snippets = ("testme",
"""my snipped ${1:some_default}
and a mirror: $1
$2...$3
$0""")
    keys = "testme" + EX + "hi;" + JF + "hi2" + JF + "hi3" + JF + "hi4" + ESC + ";Hello"
    wanted ="""my snipped hi;
and a mirror: hi;
hi2...hi3
hi4Hello"""

    def _before_test(self):
        self.vim.send(":set langmap=\\\\;;A\n")

# Test for bug 871357 #
class TestLangmapWithUtf8_ExpectCorrectResult(_VimTest):
    skip_if = lambda self: running_on_windows()  # SendKeys can't send UTF characters
    snippets = ("testme",
"""my snipped ${1:some_default}
and a mirror: $1
$2...$3
$0""")
    keys = "testme" + EX + "hi1" + JF + "hi2" + JF + "hi3" + JF + "hi4"
    wanted ="""my snipped hi1
and a mirror: hi1
hi2...hi3
hi4"""

    def _before_test(self):
        self.vim.send(":set langmap=йq,цw,уe,кr,еt,нy,гu,шi,щo,зp,х[,ъ],фa,ыs,вd,аf,пg,рh,оj,лk,дl,ж\\;,э',яz,чx,сc,мv,иb,тn,ьm,ю.,ё',ЙQ,ЦW,УE,КR,ЕT,НY,ГU,ШI,ЩO,ЗP,Х\{,Ъ\},ФA,ЫS,ВD,АF,ПG,РH,ОJ,ЛK,ДL,Ж\:,Э\",ЯZ,ЧX,СC,МV,ИB,ТN,ЬM,Б\<,Ю\>\n")

# End: Langmap Handling  #}}}
# Unmap SelectMode Mappings  {{{#
# Test for bug 427298 #
class _SelectModeMappings(_VimTest):
    snippets = ("test", "${1:World}")
    keys = "test" + EX + "Hello"
    wanted = "Hello"
    maps = ("", "")
    buffer_maps = ("", "")
    do_unmapping = True
    ignores = []

    def _extra_options_pre_init(self, vim_config):
        vim_config.append(":let g:UltiSnipsRemoveSelectModeMappings=%i" % int(self.do_unmapping))
        vim_config.append(":let g:UltiSnipsMappingsToIgnore=%s" % repr(self.ignores))

        if not isinstance(self.maps[0], tuple):
            self.maps = (self.maps,)
        if not isinstance(self.buffer_maps[0], tuple):
            self.buffer_maps = (self.buffer_maps,)

        for key, m in self.maps:
            if not len(key): continue
            vim_config.append(":smap %s %s" % (key,m))
        for key, m in self.buffer_maps:
            if not len(key): continue
            vim_config.append(":smap <buffer> %s %s" % (key,m))

class SelectModeMappings_RemoveBeforeSelecting_ECR(_SelectModeMappings):
    maps = ("H", "x")
    wanted = "Hello"
class SelectModeMappings_DisableRemoveBeforeSelecting_ECR(_SelectModeMappings):
    do_unmapping = False
    maps = ("H", "x")
    wanted = "xello"
class SelectModeMappings_IgnoreMappings_ECR(_SelectModeMappings):
    ignores = ["e"]
    maps = ("H", "x"), ("e", "l")
    wanted = "Hello"
class SelectModeMappings_IgnoreMappings1_ECR(_SelectModeMappings):
    ignores = ["H"]
    maps = ("H", "x"), ("e", "l")
    wanted = "xello"
class SelectModeMappings_IgnoreMappings2_ECR(_SelectModeMappings):
    ignores = ["e", "H"]
    maps = ("e", "l"), ("H", "x")
    wanted = "xello"
class SelectModeMappings_BufferLocalMappings_ECR(_SelectModeMappings):
    buffer_maps = ("H", "blah")
    wanted = "Hello"

# End: Unmap SelectMode Mappings  #}}}
# Folding Interaction  {{{#
class FoldingEnabled_SnippetWithFold_ExpectNoFolding(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set foldlevel=0")
        vim_config.append("set foldmethod=marker")
    snippets = ("test", r"""Hello {{{
${1:Welt} }}}""")
    keys = "test" + EX + "Ball"
    wanted = """Hello {{{
Ball }}}"""
class FoldOverwrite_Simple_ECR(_VimTest):
    snippets = ("fold",
"""# ${1:Description}  `!p snip.rv = vim.eval("&foldmarker").split(",")[0]`

# End: $1  `!p snip.rv = vim.eval("&foldmarker").split(",")[1]`""")
    keys = "fold" + EX + "hi"
    wanted = "# hi  {{{\n\n# End: hi  }}}"
class Fold_DeleteMiddleLine_ECR(_VimTest):
    snippets = ("fold",
"""# ${1:Description}  `!p snip.rv = vim.eval("&foldmarker").split(",")[0]`


# End: $1  `!p snip.rv = vim.eval("&foldmarker").split(",")[1]`""")
    keys = "fold" + EX + "hi" + ESC + "jdd"
    wanted = "# hi  {{{\n\n# End: hi  }}}"

class PerlSyntaxFold(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set foldlevel=0")
        vim_config.append("syntax enable")
        vim_config.append("set foldmethod=syntax")
        vim_config.append("let g:perl_fold = 1")
        vim_config.append("so $VIMRUNTIME/syntax/perl.vim")
    snippets = ("test", r"""package ${1:`!v printf('c%02d', 3)`};
${0}
1;""")
    keys = "test" + EX + JF + "sub junk {}"
    wanted = "package c03;\nsub junk {}\n1;"
# End: Folding Interaction  #}}}
# Trailing whitespace {{{#
class RemoveTrailingWhitespace(_VimTest):
    snippets = ("test", """Hello\t ${1:default}\n$2""", "", "s")
    wanted = """Hello\nGoodbye"""
    keys = "test" + EX + BS + JF + "Goodbye"
class LeaveTrailingWhitespace(_VimTest):
    snippets = ("test", """Hello \t ${1:default}\n$2""")
    wanted = """Hello \t \nGoodbye"""
    keys = "test" + EX + BS + JF + "Goodbye"
# End: Trailing whitespace #}}}

# Cursor Movement  {{{#
class CursorMovement_Multiline_ECR(_VimTest):
    snippets = ("test", r"$1 ${1:a tab}")
    keys = "test" + EX + "this is something\nvery nice\nnot" + JF + "more text"
    wanted = "this is something\nvery nice\nnot " \
            "this is something\nvery nice\nnotmore text"
class CursorMovement_BS_InEditMode(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set backspace=eol,indent,start")
    snippets = ("<trh", "<tr>\n\t<th>$1</th>\n\t$2\n</tr>\n$3")
    keys = "<trh" + EX + "blah" + JF + BS + BS + JF + "end"
    wanted = "<tr>\n\t<th>blah</th>\n</tr>\nend"
# End: Cursor Movement  #}}}
# Insert Mode Moving  {{{#
class IMMoving_CursorsKeys_ECR(_VimTest):
    snippets = ("test", "${1:Some}")
    keys = "test" + EX + "text" + 3*ARR_U + 6*ARR_D
    wanted = "text"
class IMMoving_AcceptInputWhenMoved_ECR(_VimTest):
    snippets = ("test", r"$1 ${1:a tab}")
    keys = "test" + EX + "this" + 2*ARR_L + "hallo\nwelt"
    wanted = "thhallo\nweltis thhallo\nweltis"
class IMMoving_NoExiting_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:a tab} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 7*ARR_L + \
            JF + "hallo"
    wanted = "hello tab hallo tab this"
class IMMoving_NoExitingEventAtEnd_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:a tab} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + JF + "hallo"
    wanted = "hello tab hallo tab this"
class IMMoving_ExitWhenOutsideRight_ECR(_VimTest):
    snippets = ("test", r"$1 ${2:blub} ${1:Tab}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + ARR_R + JF + "hallo"
    wanted = "hello tab blub tab " + JF + "hallothis"
class IMMoving_NotExitingWhenBarelyOutsideLeft_ECR(_VimTest):
    snippets = ("test", r"${1:Hi} ${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 3*ARR_L + \
            JF + "hallo"
    wanted = "hello tab hallo this"
class IMMoving_ExitWhenOutsideLeft_ECR(_VimTest):
    snippets = ("test", r"${1:Hi} ${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 4*ARR_L + \
            JF + "hallo"
    wanted = "hello" + JF + "hallo tab blub this"
class IMMoving_ExitWhenOutsideAbove_ECR(_VimTest):
    snippets = ("test", "${1:Hi}\n${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 1*ARR_U + "\n" + JF + \
            "hallo"
    wanted = JF + "hallo\nhello tab\nblub this"
class IMMoving_ExitWhenOutsideBelow_ECR(_VimTest):
    snippets = ("test", "${1:Hi}\n${2:blub}")
    keys = "hello test this" + ESC + "02f i" + EX + "tab" + 2*ARR_D + JF + \
            "testhallo\n"
    wanted = "hello tab\nblub this\n" + JF + "testhallo"
# End: Insert Mode Moving  #}}}
# Undo of Snippet insertion  {{{#
class Undo_RemoveMultilineSnippet(_VimTest):
    snippets = ("test", "Hello\naaa ${1} bbb\nWorld")
    keys = "test" + EX + ESC + "u" + "inothing"
    wanted = "nothing"
class Undo_RemoveEditInTabstop(_VimTest):
    snippets = ("test", "$1 Hello\naaa ${1} bbb\nWorld")
    keys = "hello test" + EX + "upsi" + ESC + "hh" + "iabcdef" + ESC + "u"
    wanted = "hello upsi Hello\naaa upsi bbb\nWorld"
class Undo_RemoveWholeSnippet(_VimTest):
    snippets = ("test", "Hello\n${1:Hello}World")
    keys = "first line\n\n\n\n\n\nthird line" + \
            ESC + "3k0itest" + EX + ESC + "uiupsy"
    wanted = "first line\n\n\nupsy\n\n\nthird line"
class JumpForward_DefSnippet(_VimTest):
    snippets = ("test", "${1}\n`!p snip.rv = '\\n'.join(t[1].split())`\n\n${0:pass}")
    keys = "test" + EX + "a b c" + JF + "shallnot"
    wanted = "a b c\na\nb\nc\n\nshallnot"
class DeleteSnippetInsertion0(_VimTest):
    snippets = ("test", "${1:hello} $1")
    keys = "test" + EX + ESC + "Vkx" + "i\nworld\n"
    wanted = "world"
class DeleteSnippetInsertion1(_VimTest):
    snippets = ("test", r"$1${1/(.*)/(?0::.)/}")
    keys = "test" + EX + ESC + "u" + "i" + JF + "\t"
    wanted = "\t"
# End: Undo of Snippet insertion  #}}}
# Tab Completion of Words  {{{#
class Completion_SimpleExample_ECR(_VimTest):
    snippets = ("test", "$1 ${1:blah}")
    keys = "superkallifragilistik\ntest" + EX + "sup" + COMPL_KW + \
            COMPL_ACCEPT + " some more"
    wanted = "superkallifragilistik\nsuperkallifragilistik some more " \
            "superkallifragilistik some more"

# We need >2 different words with identical starts to create the
# popup-menu:
COMPLETION_OPTIONS = "completion1\ncompletion2\n"

class Completion_ForwardsJumpWithoutCOMPL_ACCEPT(_VimTest):
    # completions should not be truncated when JF is activated without having
    # pressed COMPL_ACCEPT (Bug #598903)
    snippets = ("test", "$1 $2")
    keys = COMPLETION_OPTIONS + "test" + EX + "com" + COMPL_KW + JF + "foo"
    wanted = COMPLETION_OPTIONS + "completion1 foo"

class Completion_BackwardsJumpWithoutCOMPL_ACCEPT(_VimTest):
    # completions should not be truncated when JB is activated without having
    # pressed COMPL_ACCEPT (Bug #598903)
    snippets = ("test", "$1 $2")
    keys = COMPLETION_OPTIONS + "test" + EX + "foo" + JF + "com" + COMPL_KW + \
           JB + "foo"
    wanted = COMPLETION_OPTIONS + "foo completion1"
# End: Tab Completion of Words  #}}}
# Pressing BS in TabStop  {{{#
# Test for Bug #774917
class Backspace_TabStop_Zero(_VimTest):
    snippets = ("test", "A${1:C} ${0:DDD}", "This is Case 1")
    keys = "test" + EX + "A" + JF + BS + "BBB"
    wanted = "AA BBB"

class Backspace_TabStop_NotZero(_VimTest):
    snippets = ("test", "A${1:C} ${2:DDD}", "This is Case 1")
    keys = "test" + EX + "A" + JF + BS + "BBB"
    wanted = "AA BBB"
# End: Pressing BS in TabStop  #}}}
# Newline in default text {{{#
# Tests for bug 616315 #
class TrailingNewline_TabStop_NLInsideStuffBehind(_VimTest):
    snippets = ("test", r"""
x${1:
}<-behind1
$2<-behind2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj<-behind1
k<-behind2"""

class TrailingNewline_TabStop_JustNL(_VimTest):
    snippets = ("test", r"""
x${1:
}
$2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k"""

class TrailingNewline_TabStop_EndNL(_VimTest):
    snippets = ("test", r"""
x${1:a
}
$2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k"""

class TrailingNewline_TabStop_StartNL(_VimTest):
    snippets = ("test", r"""
x${1:
a}
$2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k"""

class TrailingNewline_TabStop_EndStartNL(_VimTest):
    snippets = ("test", r"""
x${1:
a
}
$2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k"""

class TrailingNewline_TabStop_NotEndStartNL(_VimTest):
    snippets = ("test", r"""
x${1:a
a}
$2""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k"""

class TrailingNewline_TabStop_ExtraNL_ECR(_VimTest):
    snippets = ("test", r"""
x${1:a
a}
$2
""")
    keys = "test" + EX + "j" + JF + "k"
    wanted = """
xj
k
"""

class _MultiLineDefault(_VimTest):
    snippets = ("test", r"""
x${1:a
b
c
d
e
f}
$2""")

class MultiLineDefault_Jump(_MultiLineDefault):
    keys = "test" + EX + JF + "y"
    wanted = """
xa
b
c
d
e
f
y"""

class MultiLineDefault_Type(_MultiLineDefault):
    keys = "test" + EX + "z" + JF + "y"
    wanted = """
xz
y"""

class MultiLineDefault_BS(_MultiLineDefault):
    keys = "test" + EX + BS + JF + "y"
    wanted = """
x
y"""



# End: Newline in default text  #}}}
# Quotes in Snippets  {{{#
# Test for Bug #774917
def _snip_quote(qt):
    return (
            ("te" + qt + "st", "Expand me" + qt + "!", "test: "+qt),
            ("te", "Bad", ""),
            )

class Snippet_With_SingleQuote(_VimTest):
    snippets = _snip_quote("'")
    keys = "te'st" + EX
    wanted = "Expand me'!"

class Snippet_With_SingleQuote_List(_VimTest):
    snippets = _snip_quote("'")
    keys = "te" + LS + "2\n"
    wanted = "Expand me'!"

class Snippet_With_DoubleQuote(_VimTest):
    snippets = _snip_quote('"')
    keys = 'te"st' + EX
    wanted = "Expand me\"!"

class Snippet_With_DoubleQuote_List(_VimTest):
    snippets = _snip_quote('"')
    keys = "te" + LS + "2\n"
    wanted = "Expand me\"!"
# End: Quotes in Snippets  #}}}
# Umlauts and Special Chars  {{{#
class _UmlautsBase(_VimTest):
    skip_if = lambda self: running_on_windows()  # SendKeys can't send UTF characters

class Snippet_With_Umlauts_List(_UmlautsBase):
    snippets = _snip_quote('ü')
    keys = 'te' + LS + "2\n"
    wanted = "Expand meü!"

class Snippet_With_Umlauts(_UmlautsBase):
    snippets = _snip_quote('ü')
    keys = 'teüst' + EX
    wanted = "Expand meü!"

class Snippet_With_Umlauts_TypeOn(_UmlautsBase):
    snippets = ('ül', 'üüüüüßßßß')
    keys = 'te ül' + EX + "more text"
    wanted = "te üüüüüßßßßmore text"
class Snippet_With_Umlauts_OverwriteFirst(_UmlautsBase):
    snippets = ('ül', 'üü ${1:world} üü ${2:hello}ßß\nüüüü')
    keys = 'te ül' + EX + "more text" + JF + JF + "end"
    wanted = "te üü more text üü helloßß\nüüüüend"
class Snippet_With_Umlauts_OverwriteSecond(_UmlautsBase):
    snippets = ('ül', 'üü ${1:world} üü ${2:hello}ßß\nüüüü')
    keys = 'te ül' + EX + JF + "more text" + JF + "end"
    wanted = "te üü world üü more textßß\nüüüüend"
class Snippet_With_Umlauts_OverwriteNone(_UmlautsBase):
    snippets = ('ül', 'üü ${1:world} üü ${2:hello}ßß\nüüüü')
    keys = 'te ül' + EX + JF + JF + "end"
    wanted = "te üü world üü helloßß\nüüüüend"
class Snippet_With_Umlauts_Mirrors(_UmlautsBase):
    snippets = ('ül', 'üü ${1:world} üü $1')
    keys = 'te ül' + EX + "hello"
    wanted = "te üü hello üü hello"
class Snippet_With_Umlauts_Python(_UmlautsBase):
    snippets = ('ül', 'üü ${1:world} üü `!p snip.rv = len(t[1])*"a"`')
    keys = 'te ül' + EX + "hüüll"
    wanted = "te üü hüüll üü aaaaa"
# End: Umlauts and Special Chars  #}}}
# Exclusive Selection  {{{#
class _ES_Base(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set selection=exclusive")
class ExclusiveSelection_SimpleTabstop_Test(_ES_Base):
    snippets = ("test", "h${1:blah}w $1")
    keys = "test" + EX + "ui" + JF
    wanted = "huiw ui"

class ExclusiveSelection_RealWorldCase_Test(_ES_Base):
    snippets = ("for",
"""for ($${1:i} = ${2:0}; $$1 < ${3:count}; $$1${4:++}) {
	${5:// code}
}""")
    keys = "for" + EX + "k" + JF
    wanted = """for ($k = 0; $k < count; $k++) {
	// code
}"""
# End: Exclusive Selection  #}}}

# Old Selection {{{#
class _OS_Base(_VimTest):
    def _extra_options_pre_init(self, vim_config):
        vim_config.append("set selection=old")
class OldSelection_SimpleTabstop_Test(_OS_Base):
    snippets =("test", "h${1:blah}w $1")
    keys = "test" + EX + "ui" + JF
    wanted = "huiw ui"

class OldSelection_RealWorldCase_Test(_OS_Base):
    snippets = ("for",
"""for ($${1:i} = ${2:0}; $$1 < ${3:count}; $$1${4:++}) {
	${5:// code}
}""")
    keys = "for" + EX + "k" + JF
    wanted = """for ($k = 0; $k < count; $k++) {
	// code
}"""
# End: Old Selection #}}}

# Normal mode editing  {{{#
# Test for bug #927844
class DeleteLastTwoLinesInSnippet(_VimTest):
    snippets = ("test", "$1hello\nnice\nworld")
    keys = "test" + EX + ESC + "j2dd"
    wanted = "hello"
class DeleteCurrentTabStop1_JumpBack(_VimTest):
    snippets = ("test", "${1:hi}\nend")
    keys = "test" + EX + ESC + "ddi" + JB
    wanted = "end"
class DeleteCurrentTabStop2_JumpBack(_VimTest):
    snippets = ("test", "${1:hi}\n${2:world}\nend")
    keys = "test" + EX + JF + ESC + "ddi" + JB + "hello"
    wanted = "hello\nend"
class DeleteCurrentTabStop3_JumpAround(_VimTest):
    snippets = ("test", "${1:hi}\n${2:world}\nend")
    keys = "test" + EX + JF + ESC + "ddkji" + JB + "hello" + JF + "world"
    wanted = "hello\nendworld"

# End: Normal mode editing  #}}}
# Test for bug 1251994  {{{#
class Bug1251994(_VimTest):
    snippets = ("test", "${2:#2} ${1:#1};$0")
    keys = "  test" + EX + "hello" + JF + "world" + JF + "blub"
    wanted = "  world hello;blub"
# End: 1251994  #}}}
# Test for https://github.com/SirVer/ultisnips/issues/157 (virtualedit) {{{#
class VirtualEdit(_VimTest):
    snippets = ("pd", "padding: ${1:0}px")
    keys = "\t\t\tpd" + EX + "2"
    wanted = "\t\t\tpadding: 2px"

    def _extra_options_pre_init(self, vim_config):
        vim_config.append('set virtualedit=all')
        vim_config.append('set noexpandtab')
# End: 1251994  #}}}
# Test for Github Pull Request #134 - Retain unnamed register {{{#
class RetainsTheUnnamedRegister(_VimTest):
    snippets = ("test", "${1:hello} ${2:world} ${0}")
    keys = "yank" + ESC + "by4lea test" + EX + "HELLO" + JF + JF + ESC + "p"
    wanted = "yank HELLO world yank"
class RetainsTheUnnamedRegister_ButOnlyOnce(_VimTest):
    snippets = ("test", "${1:hello} ${2:world} ${0}")
    keys = "blahfasel" + ESC + "v" + 4*ARR_L + "xotest" + EX + ESC + ARR_U + "v0xo" + ESC + "p"
    wanted = "\nblah\nhello world "
# End: Github Pull Request # 134 #}}}
# snipMate support  {{{#
class snipMate_SimpleSnippet(_VimTest):
    files = { "snippets/_.snippets": """
snippet hello
\tThis is a test snippet
\t# With a comment"""}
    keys = "hello" + EX
    wanted = "This is a test snippet\n# With a comment"
class snipMate_OtherFiletype(_VimTest):
    files = { "snippets/blubi.snippets": """
snippet hello
\tworked"""}
    keys = "hello" + EX + ESC + ":set ft=blubi\nohello" + EX
    wanted = "hello" + EX + "\nworked"
class snipMate_MultiMatches(_VimTest):
    files = { "snippets/_.snippets": """
snippet hello The first snippet."
\tone
snippet hello The second snippet.
\ttwo"""}
    keys = "hello" + EX + "2\n"
    wanted = "two"
class snipMate_SimpleSnippetSubDirectory(_VimTest):
    files = { "snippets/_/blub.snippets": """
snippet hello
\tThis is a test snippet"""}
    keys = "hello" + EX
    wanted = "This is a test snippet"
class snipMate_SimpleSnippetInSnippetFile(_VimTest):
    files = {
        "snippets/_/hello.snippet": """This is a stand alone snippet""",
        "snippets/_/hello1.snippet": """This is two stand alone snippet""",
        "snippets/_/hello2/this_is_my_cool_snippet.snippet": """Three""",
    }
    keys = "hello" + EX + "\nhello1" + EX + "\nhello2" + EX
    wanted = "This is a stand alone snippet\nThis is two stand alone snippet\nThree"
class snipMate_Interpolation(_VimTest):
    files = { "snippets/_.snippets": """
snippet test
\tla`printf('c%02d', 3)`lu"""}
    keys = "test" + EX
    wanted = "lac03lu"
class snipMate_InterpolationWithSystem(_VimTest):
    files = { "snippets/_.snippets": """
snippet test
\tla`system('echo -ne öäü')`lu"""}
    keys = "test" + EX
    wanted = "laöäülu"
class snipMate_TestMirrors(_VimTest):
    files = { "snippets/_.snippets": """
snippet for
\tfor (${2:i}; $2 < ${1:count}; $1++) {
\t\t${4}
\t}"""}
    keys = "for" + EX + "blub" + JF + "j" + JF + "hi"
    wanted = "for (j; j < blub; blub++) {\n\thi\n}"
class snipMate_TestMirrorsInPlaceholders(_VimTest):
    files = { "snippets/_.snippets": """
snippet opt
\t<option value="${1:option}">${2:$1}</option>"""}
    keys = "opt" + EX + "some" + JF + JF + "ende"
    wanted = """<option value="some">some</option>ende"""
class snipMate_TestMirrorsInPlaceholders_Overwrite(_VimTest):
    files = { "snippets/_.snippets": """
snippet opt
\t<option value="${1:option}">${2:$1}</option>"""}
    keys = "opt" + EX + "some" + JF + "not" + JF + "ende"
    wanted = """<option value="some">not</option>ende"""
class snipMate_Visual_Simple(_VimTest):
    files = { "snippets/_.snippets": """
snippet v
\th${VISUAL}b"""}
    keys = "blablub" + ESC + "0v6l" + EX + "v" + EX
    wanted = "hblablubb"
class snipMate_NoNestedTabstops(_VimTest):
    files = { "snippets/_.snippets": """
snippet test
\th$${1:${2:blub}}$$"""}
    keys = "test" + EX + JF + "hi"
    wanted = "h$${2:blub}$$hi"
class snipMate_Extends(_VimTest):
    files = { "snippets/a.snippets": """
extends b
snippet test
\tblub""", "snippets/b.snippets": """
snippet test1
\tblah"""
}
    keys = ESC + ":set ft=a\n" + "itest1" + EX
    wanted = "blah"
class snipMate_EmptyLinesContinueSnippets(_VimTest):
    files = { "snippets/_.snippets": """
snippet test
\tblub

\tblah

snippet test1
\ta"""
}
    keys = "test" + EX
    wanted = "blub\n\nblah\n"
class snipMate_OverwrittenByRegExpTrigger(_VimTest):
    files = { "snippets/_.snippets": """
snippet def
\tsnipmate
""",
    "us/all.snippets": r"""
snippet "(de)?f" "blub" r
ultisnips
endsnippet
""" }
    keys = "def" + EX
    wanted = "ultisnips"
# End: snipMate support  #}}}
# SnippetsInCurrentScope  {{{#
class VerifyVimDict1(_VimTest):
    """check:
    correct type (4 means vim dictionary)
    correct length of dictionary (in this case we have on element if the use same prefix, dictionary should have 1 element)
    correct description (including the apostrophe)
    if the prefix is mismatched no resulting dict should have 0 elements
    """

    snippets = ('testâ', 'abc123ά', '123\'êabc')
    keys = ('test=(type(UltiSnips#SnippetsInCurrentScope()) . len(UltiSnips#SnippetsInCurrentScope()) . ' +
       'UltiSnips#SnippetsInCurrentScope()["testâ"]' + ')\n' +
       '=len(UltiSnips#SnippetsInCurrentScope())\n')

    wanted = 'test41123\'êabc0'

class VerifyVimDict2(_VimTest):
    """check:
    can use " in trigger
    """

    snippets = ('te"stâ', 'abc123ά', '123êabc')
    akey = "'te{}stâ'".format('"')
    keys = ('te"=(UltiSnips#SnippetsInCurrentScope()[{}]'.format(akey) + ')\n')
    wanted = 'te"123êabc'

class VerifyVimDict3(_VimTest):
    """check:
    can use ' in trigger
    """

    snippets = ("te'stâ", 'abc123ά', '123êabc')
    akey = '"te{}stâ"'.format("'")
    keys = ("te'=(UltiSnips#SnippetsInCurrentScope()[{}]".format(akey) + ')\n')
    wanted = "te'123êabc"
# End: SnippetsInCurrentScope  #}}}
# Snippet Source  {{{#
class AddNewSnippetSource(_VimTest):
    keys = ( "blumba" + EX + ESC +
      ":%(python)s UltiSnips_Manager.register_snippet_source(" +
          "'temp', MySnippetSource())\n" +
      "oblumba" + EX + ESC +
      ":%(python)s UltiSnips_Manager.unregister_snippet_source('temp')\n" +
      "oblumba" + EX ) % { 'python': 'py3' if PYTHON3 else 'py' }
    wanted = (
      "blumba" + EX + "\n" +
      "this is a dynamic snippet" + "\n" +
      "blumba" + EX
    )

    def _extra_options_post_init(self, vim_config):
        self._create_file("snippet_source.py","""
from UltiSnips.snippet.source import SnippetSource
from UltiSnips.snippet.definition import UltiSnipsSnippetDefinition

class MySnippetSource(SnippetSource):
  def get_snippets(self, filetypes, before, possible):
    if before.endswith('blumba'):
      return [
          UltiSnipsSnippetDefinition(
              -100, "blumba", "this is a dynamic snippet", "", "", {}, "blub")
        ]
    return []
""")
        pyfile = 'py3file' if PYTHON3 else 'pyfile'
        vim_config.append("%s %s" % (pyfile, os.path.join(
            self._temporary_directory, "snippet_source.py")))
# End: Snippet Source  #}}}

# Plugin: YouCompleteMe  {{{#
class Plugin_YouCompleteMe_IntegrationTest(_VimTest):
    def skip_if(self):
        r = python3()
        if r:
            return r
        if "7.4" not in self.version:
            return "Needs Vim 7.4."
    plugins = ["Valloric/YouCompleteMe"]
    snippets = ("superlongtrigger", "Hello")
    keys = "superlo\ty"
    wanted = "Hello"

    def _extra_options_pre_init(self, vim_config):
        # Not sure why, but I need to make a new tab for this to work.
        vim_config.append('let g:UltiSnipsExpandTrigger="y"')
        vim_config.append('tabnew')

    def _before_test(self):
        self.vim.send(":set ft=python\n")
        # Give ycm a chance to catch up.
        time.sleep(1)
# End: Plugin: YouCompleteMe  #}}}
# Plugin: Neocomplete {{{#
class Plugin_Neocomplete_BugTest(_VimTest):
    # Test for https://github.com/SirVer/ultisnips/issues/228
    def skip_if(self):
        if "+lua" not in self.version:
            return "Needs +lua"
    plugins = ["Shougo/neocomplete.vim"]
    snippets = ("t", "Hello", "", "w")
    keys = "iab\\ t" + EX
    wanted = "iab\\ Hello"

    def _extra_options_pre_init(self, vim_config):
        vim_config.append(r'set iskeyword+=\\ ')
        vim_config.append('let g:neocomplete#enable_at_startup = 1')
        vim_config.append('let g:neocomplete#enable_smart_case = 1')
        vim_config.append('let g:neocomplete#enable_camel_case = 1')
        vim_config.append('let g:neocomplete#enable_auto_delimiter = 1')
        vim_config.append('let g:neocomplete#enable_refresh_always = 1')
# End: Plugin: Neocomplete  #}}}
# Plugin: unite {{{#
class Plugin_unite_BugTest(_VimTest):
    plugins = ["Shougo/unite.vim"]
    snippets = ("t", "Hello", "", "w")
    keys = "iab\\ t=UltiSnipsCallUnite()\n"
    wanted = "iab\\ Hello "

    def _extra_options_pre_init(self, vim_config):
        vim_config.append(r'set iskeyword+=\\ ')
        vim_config.append('function! UltiSnipsCallUnite()')
        vim_config.append('  Unite -start-insert -winheight=100 -immediately -no-empty ultisnips')
        vim_config.append('  return ""')
        vim_config.append('endfunction')
# End: Plugin: unite  #}}}
# Plugin: Supertab {{{#
class Plugin_SuperTab_SimpleTest(_VimTest):
    plugins = ["ervandew/supertab"]
    snippets = ("long", "Hello", "", "w")
    keys = ( "longtextlongtext\n" +
        "longt" + EX + "\n" +  # Should complete word
        "long" + EX )  # Should expand
    wanted = "longtextlongtext\nlongtextlongtext\nHello"

    def _before_test(self):
        # Make sure that UltiSnips has the keymap
        self.vim.send(":call UltiSnips#map_keys#MapKeys()\n")

    def _extra_options_post_init(self, vim_config):
        assert EX == "\t"  # Otherwise this test needs changing.
        vim_config.append('let g:SuperTabDefaultCompletionType = "<c-p>"')
        vim_config.append('let g:SuperTabRetainCompletionDuration = "insert"')
        vim_config.append('let g:SuperTabLongestHighlight = 1')
        vim_config.append('let g:SuperTabCrMapping = 0')
# End: Plugin: Supertab   #}}}

###########################################################################
#                               END OF TEST                               #
###########################################################################


if __name__ == '__main__':
    import sys
    import optparse

    def parse_args():
        p = optparse.OptionParser("%prog [OPTIONS] <test case names to run>")

        p.set_defaults(session="vim", interrupt=False,
                verbose=False, interface="screen", retries=4, plugins=False)

        p.add_option("-v", "--verbose", dest="verbose", action="store_true",
            help="print name of tests as they are executed")
        p.add_option("--clone-plugins", action="store_true",
            help="Only clones dependant plugins and exits the test runner.")
        p.add_option("--plugins", action="store_true",
            help="Run integration tests with other Vim plugins.")
        p.add_option("--interface", type=str,
                help="interface to vim to use on Mac and or Linux [screen|tmux].")
        p.add_option("-s", "--session", dest="session",  metavar="SESSION",
            help="session parameters for the terminal multiplexer SESSION [%default]")
        p.add_option("-i", "--interrupt", dest="interrupt",
            action="store_true",
            help="Stop after defining the snippet. This allows the user " \
             "to interactively test the snippet in vim. You must give " \
             "exactly one test case on the cmdline. The test will always fail."
        )
        p.add_option("-r", "--retries", dest="retries", type=int,
                help="How often should each test be retried before it is "
                "considered failed. Works around flakyness in the terminal "
                "multiplexer and race conditions in writing to the file system.")

        o, args = p.parse_args()
        if o.interface not in ("screen", "tmux"):
            p.error("--interface must be [screen|tmux].")

        return o, args

    def main():
        options,selected_tests = parse_args()

        test_loader = unittest.TestLoader()
        all_test_suites = test_loader.loadTestsFromModule(__import__("test"))

        vim = None
        if not options.clone_plugins:
            if platform.system() == "Windows":
                raise RuntimeError("TODO: TestSuite is broken under windows. Volunteers wanted!.")
                # vim = VimInterfaceWindows()
                vim.focus()
            else:
                if options.interface == "screen":
                    vim = VimInterfaceScreen(options.session)
                elif options.interface == "tmux":
                    vim = VimInterfaceTmux(options.session)

        suite = unittest.TestSuite()
        all_other_plugins = set()
        for s in all_test_suites:
            for test in s:
                test.interrupt = options.interrupt
                test.retries = options.retries
                test.test_plugins = options.plugins
                test.vim = vim
                all_other_plugins.update(test.plugins)

                if len(selected_tests):
                    id = test.id().split('.')[1]
                    if not any([ id.startswith(t) for t in selected_tests ]):
                        continue
                suite.addTest(test)

        if options.plugins or options.clone_plugins:
            setup_other_plugins(all_other_plugins)
            if options.clone_plugins:
                return

        if options.verbose:
            v = 2
        else:
            v = 1
        res = unittest.TextTestRunner(verbosity=v).run(suite)

    main()

# vim:fileencoding=utf-8:foldmarker={{{#,#}}}:

########NEW FILE########
__FILENAME__ = get_tm_snippets
#!/usr/bin/env python
# encoding: utf-8

import urllib
import re
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError
import htmlentitydefs
import os
import glob


_UNESCAPE = re.compile(ur'&\w+?;', re.UNICODE)
def unescape(s):
    if s is None:
        return ""
    def fixup(m):
        ent = m.group(0)[1:-1]
        return unichr(htmlentitydefs.name2codepoint[ent])
    try:
        return _UNESCAPE.sub(fixup,s)
    except:
        print "unescape failed: %s" % repr(s)
        raise

class UnknownVariable(Exception):
    pass

class UnsupportedVariableExpression(Exception):
    pass

def replace_vars(m):
    """ Replace vars in 'content' portion.
    :m: match object
    :returns: string"""
    var = m.group(1)
    default = m.group(2)

    if not re.match(r'\w+$', var):
        raise UnsupportedVariableExpression(var)

    translate_vars = {
            'TM_PHP_OPEN_TAG_WITH_ECHO': 'g:UltiSnipsOpenTagWithEcho',
            'TM_PHP_OPEN_TAG': 'g:UltiSnipsOpenTag',
            'PHPDOC_AUTHOR': 'g:snips_author',
            }
    # TODO: TM_SELECTED_TEXT/([\t ]*).*/$1/m

    if var in translate_vars:
        newvar = translate_vars[var]
    else:
        # TODO: this could be autogenerated
        raise UnknownVariable(var)

    return "`!v exists('%s') ? %s : '%s'`" % (newvar, newvar, default)

def parse_content(c):
    try:
        data = ElementTree.fromstring(c)[0]

        rv = {}
        for k,v in zip(data[::2], data[1::2]):
            rv[k.text] = unescape(v.text)

        if re.search( r'\$\{\D', rv["content"] ):
            rv["content"] = re.sub(r'\$\{([^\d}][^}:]*)(?::([^}]*))?\}', replace_vars, rv["content"])

        return rv
    except (ExpatError, ElementTree.ParseError) as detail:
        print "   Syntax Error: %s" % (detail,)
        print c
        return None
    except UnknownVariable as detail:
        print "   Unknown variable: %s" % (detail,)
        return None
    except UnsupportedVariableExpression as detail:
        print "   Unsupported variable expression: %s" % (detail,)
        return None

def fetch_snippets_from_svn(name):
    base_url = "http://svn.textmate.org/trunk/Bundles/" + name + ".tmbundle/"
    snippet_idx = base_url + "Snippets/"

    idx_list = urllib.urlopen(snippet_idx).read()


    rv = []
    for link in re.findall("<li>(.*?)</li>", idx_list):
        m = re.match(r'<a\s*href="(.*)"\s*>(.*)</a>', link)
        link, name = m.groups()
        if name == "..":
            continue

        name = unescape(name.rsplit('.', 1)[0]) # remove Extension
        print "Fetching data for Snippet '%s'" % name
        content = urllib.urlopen(snippet_idx + link).read()

        cont = parse_content(content)
        if cont:
            rv.append((name, cont))

    return rv

def fetch_snippets_from_dir(path):
    """ Fetch snippets from a given path"""

    rv = []
    for filename in glob.glob(os.path.join(path, '*.tmSnippet')):
        print "Reading file %s" % filename
        f = open(filename)
        content = f.read()

        cont = parse_content(content)
        if cont:
            name = os.path.splitext(os.path.basename(filename))[0]
            rv.append((name, cont))
    return rv

def write_snippets(snip_descr, f):

    for name, d in snip_descr:
        if "tabTrigger" not in d:
            continue

        if "content" not in d or d["content"] is None:
            print "SKIP: %s (no content)" % (d,)
            continue

        f.write('snippet %s "%s"\n' % (d["tabTrigger"], name))
        f.write(d["content"].encode("utf-8") + "\n")
        f.write("endsnippet\n\n")



if __name__ == '__main__':
    import sys

    bundle = sys.argv[1]

    if os.path.isdir(bundle):
        name = sys.argv[2]
        rv = fetch_snippets_from_dir(bundle)
    else:
        rv = fetch_snippets_from_svn(bundle)
        name = bundle.lower()

    write_snippets(rv, open("tm_" + name + ".snippets","w"))


########NEW FILE########
