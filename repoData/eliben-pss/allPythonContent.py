__FILENAME__ = ansi
'''
This module generates ANSI character codes to printing colors to terminals.
See: http://en.wikipedia.org/wiki/ANSI_escape_code
'''

CSI = '\033['

def code_to_chars(code):
    return CSI + str(code) + 'm'

class AnsiCodes(object):
    def __init__(self, codes):
        for name in dir(codes):
            if not name.startswith('_'):
                value = getattr(codes, name)
                setattr(self, name, code_to_chars(value))

class AnsiFore:
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37
    RESET   = 39

class AnsiBack:
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47
    RESET   = 49

class AnsiStyle:
    BRIGHT    = 1
    DIM       = 2
    NORMAL    = 22
    RESET_ALL = 0

Fore = AnsiCodes( AnsiFore )
Back = AnsiCodes( AnsiBack )
Style = AnsiCodes( AnsiStyle )


########NEW FILE########
__FILENAME__ = ansitowin32

import re
import sys

from .ansi import AnsiFore, AnsiBack, AnsiStyle, Style
from .winterm import WinTerm, WinColor, WinStyle
from .win32 import windll


if windll is not None:
    winterm = WinTerm()


def is_a_tty(stream):
    return hasattr(stream, 'isatty') and stream.isatty()


class StreamWrapper(object):
    '''
    Wraps a stream (such as stdout), acting as a transparent proxy for all
    attribute access apart from method 'write()', which is delegated to our
    Converter instance.
    '''
    def __init__(self, wrapped, converter):
        # double-underscore everything to prevent clashes with names of
        # attributes on the wrapped stream object.
        self.__wrapped = wrapped
        self.__convertor = converter

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def write(self, text):
        self.__convertor.write(text)


class AnsiToWin32(object):
    '''
    Implements a 'write()' method which, on Windows, will strip ANSI character
    sequences from the text, and if outputting to a tty, will convert them into
    win32 function calls.
    '''
    ANSI_RE = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')

    def __init__(self, wrapped, convert=None, strip=None, autoreset=False):
        # The wrapped stream (normally sys.stdout or sys.stderr)
        self.wrapped = wrapped

        # should we reset colors to defaults after every .write()
        self.autoreset = autoreset

        # create the proxy wrapping our output stream
        self.stream = StreamWrapper(wrapped, self)

        on_windows = sys.platform.startswith('win')

        # should we strip ANSI sequences from our output?
        if strip is None:
            strip = on_windows
        self.strip = strip

        # should we should convert ANSI sequences into win32 calls?
        if convert is None:
            convert = on_windows and is_a_tty(wrapped)
        self.convert = convert

        # dict of ansi codes to win32 functions and parameters
        self.win32_calls = self.get_win32_calls()

        # are we wrapping stderr?
        self.on_stderr = self.wrapped is sys.stderr


    def should_wrap(self):
        '''
        True if this class is actually needed. If false, then the output
        stream will not be affected, nor will win32 calls be issued, so
        wrapping stdout is not actually required. This will generally be
        False on non-Windows platforms, unless optional functionality like
        autoreset has been requested using kwargs to init()
        '''
        return self.convert or self.strip or self.autoreset


    def get_win32_calls(self):
        if self.convert and winterm:
            return {
                AnsiStyle.RESET_ALL: (winterm.reset_all, ),
                AnsiStyle.BRIGHT: (winterm.style, WinStyle.BRIGHT),
                AnsiStyle.DIM: (winterm.style, WinStyle.NORMAL),
                AnsiStyle.NORMAL: (winterm.style, WinStyle.NORMAL),
                AnsiFore.BLACK: (winterm.fore, WinColor.BLACK),
                AnsiFore.RED: (winterm.fore, WinColor.RED),
                AnsiFore.GREEN: (winterm.fore, WinColor.GREEN),
                AnsiFore.YELLOW: (winterm.fore, WinColor.YELLOW),
                AnsiFore.BLUE: (winterm.fore, WinColor.BLUE),
                AnsiFore.MAGENTA: (winterm.fore, WinColor.MAGENTA),
                AnsiFore.CYAN: (winterm.fore, WinColor.CYAN),
                AnsiFore.WHITE: (winterm.fore, WinColor.GREY),
                AnsiFore.RESET: (winterm.fore, ),
                AnsiBack.BLACK: (winterm.back, WinColor.BLACK),
                AnsiBack.RED: (winterm.back, WinColor.RED),
                AnsiBack.GREEN: (winterm.back, WinColor.GREEN),
                AnsiBack.YELLOW: (winterm.back, WinColor.YELLOW),
                AnsiBack.BLUE: (winterm.back, WinColor.BLUE),
                AnsiBack.MAGENTA: (winterm.back, WinColor.MAGENTA),
                AnsiBack.CYAN: (winterm.back, WinColor.CYAN),
                AnsiBack.WHITE: (winterm.back, WinColor.GREY),
                AnsiBack.RESET: (winterm.back, ),
            }


    def write(self, text):
        if self.strip or self.convert:
            self.write_and_convert(text)
        else:
            self.wrapped.write(text)
            self.wrapped.flush()
        if self.autoreset:
            self.reset_all()


    def reset_all(self):
        if self.convert:
            self.call_win32('m', (0,))
        elif is_a_tty(self.wrapped):
            self.wrapped.write(Style.RESET_ALL)


    def write_and_convert(self, text):
        '''
        Write the given text to our wrapped stream, stripping any ANSI
        sequences from the text, and optionally converting them into win32
        calls.
        '''
        cursor = 0
        for match in self.ANSI_RE.finditer(text):
            start, end = match.span()
            self.write_plain_text(text, cursor, start)
            self.convert_ansi(*match.groups())
            cursor = end
        self.write_plain_text(text, cursor, len(text))


    def write_plain_text(self, text, start, end):
        if start < end:
            self.wrapped.write(text[start:end])
            self.wrapped.flush()


    def convert_ansi(self, paramstring, command):
        if self.convert:
            params = self.extract_params(paramstring)
            self.call_win32(command, params)


    def extract_params(self, paramstring):
        def split(paramstring):
            for p in paramstring.split(';'):
                if p != '':
                    yield int(p)
        return tuple(split(paramstring))


    def call_win32(self, command, params):
        if params == []:
            params = [0]
        if command == 'm':
            for param in params:
                if param in self.win32_calls:
                    func_args = self.win32_calls[param]
                    func = func_args[0]
                    args = func_args[1:]
                    kwargs = dict(on_stderr=self.on_stderr)
                    func(*args, **kwargs)
        elif command in ('H', 'f'): # set cursor position
            func = winterm.set_cursor_position
            func(params, on_stderr=self.on_stderr)
        elif command in ('J'):
            func = winterm.erase_data
            func(params, on_stderr=self.on_stderr)


########NEW FILE########
__FILENAME__ = initialise
import atexit
import sys

from .ansitowin32 import AnsiToWin32


orig_stdout = sys.stdout
orig_stderr = sys.stderr

wrapped_stdout = sys.stdout
wrapped_stderr = sys.stderr

atexit_done = False


def reset_all():
    AnsiToWin32(orig_stdout).reset_all()


def init(autoreset=False, convert=None, strip=None, wrap=True):

    if not wrap and any([autoreset, convert, strip]):
        raise ValueError('wrap=False conflicts with any other arg=True')

    global wrapped_stdout, wrapped_stderr
    sys.stdout = wrapped_stdout = \
        wrap_stream(orig_stdout, convert, strip, autoreset, wrap)
    sys.stderr = wrapped_stderr = \
        wrap_stream(orig_stderr, convert, strip, autoreset, wrap)

    global atexit_done
    if not atexit_done:
        atexit.register(reset_all)
        atexit_done = True


def deinit():
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr


def reinit():
    sys.stdout = wrapped_stdout
    sys.stderr = wrapped_stdout


def wrap_stream(stream, convert, strip, autoreset, wrap):
    if wrap:
        wrapper = AnsiToWin32(stream,
            convert=convert, strip=strip, autoreset=autoreset)
        if wrapper.should_wrap():
            stream = wrapper.stream
    return stream



########NEW FILE########
__FILENAME__ = win32
# from winbase.h
STDOUT = -11
STDERR = -12

try:
    from ctypes import windll
    from ctypes import wintypes
except ImportError:
    windll = None
    SetConsoleTextAttribute = lambda *_: None
else:
    from ctypes import (
        byref, Structure, c_char, c_short, c_uint32, c_ushort, POINTER
    )

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", wintypes._COORD),
            ("dwCursorPosition", wintypes._COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", wintypes.SMALL_RECT),
            ("dwMaximumWindowSize", wintypes._COORD),
        ]
        def __str__(self):
            return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
                self.dwSize.Y, self.dwSize.X
                , self.dwCursorPosition.Y, self.dwCursorPosition.X
                , self.wAttributes
                , self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right
                , self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X
            )

    _GetStdHandle = windll.kernel32.GetStdHandle
    _GetStdHandle.argtypes = [
        wintypes.DWORD,
    ]
    _GetStdHandle.restype = wintypes.HANDLE

    _GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    _GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    _GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    _SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    _SetConsoleTextAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
    ]
    _SetConsoleTextAttribute.restype = wintypes.BOOL

    _SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
    _SetConsoleCursorPosition.argtypes = [
        wintypes.HANDLE,
        wintypes._COORD,
    ]
    _SetConsoleCursorPosition.restype = wintypes.BOOL

    _FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
    _FillConsoleOutputCharacterA.argtypes = [
        wintypes.HANDLE,
        c_char,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputCharacterA.restype = wintypes.BOOL

    _FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
    _FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputAttribute.restype = wintypes.BOOL

    handles = {
        STDOUT: _GetStdHandle(STDOUT),
        STDERR: _GetStdHandle(STDERR),
    }

    def GetConsoleScreenBufferInfo(stream_id=STDOUT):
        handle = handles[stream_id]
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = _GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        return csbi

    def SetConsoleTextAttribute(stream_id, attrs):
        handle = handles[stream_id]
        return _SetConsoleTextAttribute(handle, attrs)

    def SetConsoleCursorPosition(stream_id, position):
        position = wintypes._COORD(*position)
        # If the position is out of range, do nothing.
        if position.Y <= 0 or position.X <= 0:
            return
        # Adjust for Windows' SetConsoleCursorPosition:
        #    1. being 0-based, while ANSI is 1-based.
        #    2. expecting (x,y), while ANSI uses (y,x).
        adjusted_position = wintypes._COORD(position.Y - 1, position.X - 1)
        # Adjust for viewport's scroll position
        sr = GetConsoleScreenBufferInfo(STDOUT).srWindow
        adjusted_position.Y += sr.Top
        adjusted_position.X += sr.Left
        # Resume normal processing
        handle = handles[stream_id]
        return _SetConsoleCursorPosition(handle, adjusted_position)

    def FillConsoleOutputCharacter(stream_id, char, length, start):
        handle = handles[stream_id]
        char = c_char(char)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = _FillConsoleOutputCharacterA(
            handle, char, length, start, byref(num_written))
        return num_written.value

    def FillConsoleOutputAttribute(stream_id, attr, length, start):
        ''' FillConsoleOutputAttribute( hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten )'''
        handle = handles[stream_id]
        attribute = wintypes.WORD(attr)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        return _FillConsoleOutputAttribute(
            handle, attribute, length, start, byref(num_written))

########NEW FILE########
__FILENAME__ = winterm

from . import win32


# from wincon.h
class WinColor(object):
    BLACK   = 0
    BLUE    = 1
    GREEN   = 2
    CYAN    = 3
    RED     = 4
    MAGENTA = 5
    YELLOW  = 6
    GREY    = 7

# from wincon.h
class WinStyle(object):
    NORMAL = 0x00 # dim text, dim background
    BRIGHT = 0x08 # bright text, dim background


class WinTerm(object):

    def __init__(self):
        self._default = win32.GetConsoleScreenBufferInfo(win32.STDOUT).wAttributes
        self.set_attrs(self._default)
        self._default_fore = self._fore
        self._default_back = self._back
        self._default_style = self._style

    def get_attrs(self):
        return self._fore + self._back * 16 + self._style

    def set_attrs(self, value):
        self._fore = value & 7
        self._back = (value >> 4) & 7
        self._style = value & WinStyle.BRIGHT

    def reset_all(self, on_stderr=None):
        self.set_attrs(self._default)
        self.set_console(attrs=self._default)

    def fore(self, fore=None, on_stderr=False):
        if fore is None:
            fore = self._default_fore
        self._fore = fore
        self.set_console(on_stderr=on_stderr)

    def back(self, back=None, on_stderr=False):
        if back is None:
            back = self._default_back
        self._back = back
        self.set_console(on_stderr=on_stderr)

    def style(self, style=None, on_stderr=False):
        if style is None:
            style = self._default_style
        self._style = style
        self.set_console(on_stderr=on_stderr)

    def set_console(self, attrs=None, on_stderr=False):
        if attrs is None:
            attrs = self.get_attrs()
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleTextAttribute(handle, attrs)

    def set_cursor_position(self, position=None, on_stderr=False):
        if position is None:
            #I'm not currently tracking the position, so there is no default.
            #position = self.get_position()
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleCursorPosition(handle, position)

    def erase_data(self, mode=0, on_stderr=False):
        # 0 (or None) should clear from the cursor to the end of the screen.
        # 1 should clear from the cursor to the beginning of the screen.
        # 2 should clear the entire screen. (And maybe move cursor to (1,1)?)
        #
        # At the moment, I only support mode 2. From looking at the API, it 
        #    should be possible to calculate a different number of bytes to clear, 
        #    and to do so relative to the cursor position.
        if mode[0] not in (2,):
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        # here's where we'll home the cursor
        coord_screen = win32.COORD(0,0) 
        csbi = win32.GetConsoleScreenBufferInfo(handle)
        # get the number of character cells in the current buffer
        dw_con_size = csbi.dwSize.X * csbi.dwSize.Y
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(handle, ord(' '), dw_con_size, coord_screen)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(handle, self.get_attrs(), dw_con_size, coord_screen );
        # put the cursor at (0, 0)
        win32.SetConsoleCursorPosition(handle, (coord_screen.X, coord_screen.Y))

########NEW FILE########
__FILENAME__ = contentmatcher
#-------------------------------------------------------------------------------
# pss: contentmatcher.py
#
# ContentMatcher class that matches the contents of a file according to a given
# pattern.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import re
import sys

from .py3compat import tostring
from .matchresult import MatchResult


class ContentMatcher(object):
    def __init__(self,
                 pattern,
                 ignore_case=False,
                 invert_match=False,
                 whole_words=False,
                 literal_pattern=False,
                 max_match_count=sys.maxsize):
        """ Create a new ContentMatcher for matching the pattern in files.
            The parameters are the "matching rules".

            When created, the match_file method can be called multiple times
            for various files.

            pattern:
                The pattern (regular expression) to match, as a string or bytes
                object (should match the stream passed to the match method).

            ignore_case:
                If True, the pattern will ignore case when matching

            invert_match:
                Only non-matching lines will be returned. Note that in this
                case 'matching_column_ranges' of the match results will be
                empty

            whole_words:
                Force the pattern to match only whole words

            literal_pattern:
                Quote all special regex chars in the pattern - the pattern
                should match literally

            max_match_count:
                Maximal amount of matches to report for a search
        """
        self.regex = self._create_regex(pattern,
                            ignore_case=ignore_case,
                            whole_words=whole_words,
                            literal_pattern=literal_pattern)
        if invert_match:
            self.match_file = self.inverted_matcher
        else:
            self.match_file = self.matcher
        self.max_match_count = max_match_count

        # Cache frequently used attributes for faster access
        self._finditer = self.regex.finditer
        self._search = self.regex.search

        # Optimize a common case: searching for a simple non-regex string.
        # In this case, we don't need regex matching - using str.find is
        # faster.
        self._findstr = None
        if (    not ignore_case and not whole_words and
                self._pattern_is_simple(pattern)):
            self._findstr = pattern
            self._findstrlen = len(self._findstr)

    def matcher(self, fileobj, max_match_count=sys.maxsize):
        """ Perform matching in the file according to the matching rules. Yield
            MatchResult objects.

            fileobj is a file-like object, being read from the beginning.
            max_match_count: can be set for each file individually.
        """
        nmatch = 0
        max_match_count = min(max_match_count, self.max_match_count)
        for lineno, line in enumerate(fileobj, 1):
            # Iterate over all matches of the pattern in the line,
            # noting each matching column range.
            if self._findstr:
                # Make the common case faster: there's no match in this line, so
                # bail out ASAP.
                i = line.find(self._findstr, 0)
                if i == -1:
                    continue
                col_ranges = []
                while i >= 0:
                    startnext = i + self._findstrlen
                    col_ranges.append((i, startnext))
                    i = line.find(self._findstr, startnext)
            else:
                col_ranges = [mo.span() for mo in self._finditer(line) if mo]
            if col_ranges:
                yield MatchResult(line, lineno, col_ranges)
                nmatch += 1
                if nmatch >= max_match_count:
                    break

    def inverted_matcher(self, fileobj, max_match_count=sys.maxsize):
        """ Perform inverted matching in the file according to the matching
            rules. Yield MatchResult objects.

            fileobj is a file-like object, being read from the beginning.
            max_match_count: can be set for each file individually.
        """
        nmatch = 0
        max_match_count = min(max_match_count, self.max_match_count)
        for lineno, line in enumerate(fileobj, 1):
            # Invert match: only return lines that don't match the
            # pattern anywhere
            if not self._search(line):
                yield MatchResult(line, lineno, [])
                nmatch += 1
                if nmatch >= max_match_count:
                    break

    def _pattern_is_simple(self, pattern):
        """ A "simple" pattern that can be matched with str.find and doesn't
            require a regex engine.
        """
        return bool(re.match('[\w_]+$', tostring(pattern)))

    def _create_regex(self,
            pattern,
            ignore_case=False,
            whole_words=False,
            literal_pattern=False):
        """ Utility for creating the compiled regex from pattern and options.
        """
        if literal_pattern:
            pattern = re.escape(pattern)
        if whole_words:
            b = r'\b' if isinstance(pattern, str) else br'\b'
            pattern = b + pattern + b
        regex = re.compile(pattern, re.I if ignore_case else 0)
        return regex


if __name__ == '__main__':
    pass


########NEW FILE########
__FILENAME__ = defaultpssoutputformatter
#-------------------------------------------------------------------------------
# pss: outputformatter.py
#
# DefaultPssOutputFormatter - the default output formatter used by pss.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys

from .outputformatter import OutputFormatter
from .py3compat import tostring
from .utils import decode_colorama_color
from . import colorama


class DefaultPssOutputFormatter(OutputFormatter):
    """ The default output formatter used by pss.

        do_colors: Should colors be used?

        match_color_str/filename_color_str:
            Color strings in the format expected by decode_colorama_color
            for matches and filenames. If None, default colors will be used.
    """
    def __init__(self,
            do_colors=True,
            match_color_str=None,
            filename_color_str=None,
            lineno_color_str=None,
            do_heading=True,
            prefix_filename_to_file_matches=True,
            show_column_of_first_match=False,
            stream=None):
        self.do_colors = do_colors
        self.prefix_filename_to_file_matches = prefix_filename_to_file_matches
        self.do_heading = do_heading
        self.inline_filename = (True if prefix_filename_to_file_matches and not do_heading
                                else False)
        self.show_column_of_first_match = show_column_of_first_match

        self.style_match = (decode_colorama_color(match_color_str) or
                            colorama.Fore.BLACK + colorama.Back.YELLOW)
        self.style_filename = (decode_colorama_color(filename_color_str) or
                               colorama.Fore.MAGENTA + colorama.Style.BRIGHT)
        self.style_lineno = (decode_colorama_color(lineno_color_str) or
                             colorama.Fore.WHITE)

        colorama.init()

        # It's important to take sys.stdout after the call to colorama.init(),
        # because colorama.init() assigns a wrapped stream to sys.stdout and
        # we need this wrapped stream to have colors
        #
        self.stream = stream or sys.stdout

    def start_matches_in_file(self, filename):
        if self.prefix_filename_to_file_matches and self.do_heading:
            self._emit_colored(filename, self.style_filename)
            self._emitline()

    def end_matches_in_file(self, filename):
        self._emitline()

    def matching_line(self, matchresult, filename):
        if self.inline_filename:
            self._emit_colored('%s' % filename, self.style_filename)
            self._emit(':')
        self._emit_colored('%s' % matchresult.matching_lineno, self.style_lineno)
        self._emit(':')
        first_match_range = matchresult.matching_column_ranges[0]
        if self.show_column_of_first_match:
            self._emit('%s:' % first_match_range[0])

        # Emit the chunk before the first matching chunk
        line = matchresult.matching_line
        self._emit(line[:first_match_range[0]])
        # Now emit the matching chunks (colored), along with the non-matching
        # chunks that come after them
        for i, (match_start, match_end) in enumerate(
                matchresult.matching_column_ranges):
            self._emit_colored(line[match_start:match_end], self.style_match)
            if i == len(matchresult.matching_column_ranges) - 1:
                chunk = line[match_end:]
            else:
                next_start = matchresult.matching_column_ranges[i + 1][0]
                chunk = line[match_end:next_start]
            self._emit(chunk)

    def context_line(self, line, lineno, filename):
        if self.inline_filename:
            self._emit_colored('%s' % filename, self.style_filename)
            self._emit('-')
        self._emit_colored('%s' % lineno, self.style_lineno)
        self._emit('-')
        if self.show_column_of_first_match:
            self._emit('1-')
        self._emit(line)

    def context_separator(self):
        self._emitline('--')

    def found_filename(self, filename):
        self._emitline(filename)

    def binary_file_matches(self, msg):
        self._emitline(msg)

    def _emit(self, str):
        """ Write the string to the stream.
        """
        self.stream.write(tostring(str))

    def _emit_colored(self, str, style):
        """ Emit the given string with the given colorama style.
        """
        if self.do_colors:
            self._emit(style)
        self._emit(str)
        if self.do_colors:
            self._emit(colorama.Style.RESET_ALL)

    def _emitline(self, line=''):
        self._emit(line + '\n')



########NEW FILE########
__FILENAME__ = driver
#-------------------------------------------------------------------------------
# pss: driver.py
#
# Top-level functions and data used to execute pss.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import collections
import os
import re
import sys

from .filefinder import FileFinder
from .contentmatcher import ContentMatcher
from .matchresult import MatchResult
from .defaultpssoutputformatter import DefaultPssOutputFormatter
from .utils import istextfile
from .py3compat import str2bytes

TypeSpec = collections.namedtuple('TypeSpec', ['extensions', 'patterns'])

TYPE_MAP = {
    'actionscript':
        TypeSpec(['.as', '.mxml'], []),
    'ada':
        TypeSpec(['.ada', '.adb', '.ads'], []),
    'batch':
        TypeSpec(['.bat', '.cmd'], []),
    'asm':
        TypeSpec(['.asm', '.s', '.S'], []),
    'cc':
        TypeSpec(['.c', '.h', '.xs'], []),
    'cfg':
        TypeSpec(['.cfg', '.conf', '.config'], []),
    'cfmx':
        TypeSpec(['.cfc', '.cfm', '.cfml'], []),
    'cmake':
        TypeSpec(['.cmake'], ['CMake(Lists|Funcs).txt']),
    'cpp':
        TypeSpec(['.cpp', '.cc', '.cxx', '.m', '.hpp', '.hh', '.h', '.hxx'], []),
    'csharp':
        TypeSpec(['.cs'], []),
    'css':
        TypeSpec(['.css', '.less'], []),
    'cuda':
        TypeSpec(['.cu'], []),
    'cython':
        TypeSpec(['.pyx', '.pxd', '.pyxbld'], []),
    'elisp':
        TypeSpec(['.el', '.elisp'], []),
    'erlang':
        TypeSpec(['.erl', '.hrl'], []),
    'fortran':
        TypeSpec(['.f', '.f77', '.f90', '.F90', '.f95', '.F95', '.f03', '.for', '.ftn', '.fpp'], []),
    'go':
        TypeSpec(['.go'], []),
    'haskell':
        TypeSpec(['.hs', '.lhs'], []),
    'hh':
        TypeSpec(['.h'], []),
    'html':
        TypeSpec(['.htm', '.html', '.shtml', '.xhtml'], []),
    'inc':
        TypeSpec(['.inc', '.inl'], []),
    'java':
        TypeSpec(['.java', '.properties'], []),
    'js':
        TypeSpec(['.js'], []),
    'json':
        TypeSpec(['.json'], []),
    'jsp':
        TypeSpec(['.jsp'], []),
    'lisp':
        TypeSpec(['.lisp', '.lsp', '.cl'], []),
    'llvm':
        TypeSpec(['.ll'], []),
    'lua':
        TypeSpec(['.lua'], []),
    'make':
        TypeSpec(['.mk'], ['[Mm]akefile']),
    'mason':
        TypeSpec(['.mas', '.mthml', '.mpl', '.mtxt'], []),
    'objc':
        TypeSpec(['.m', '.h'], []),
    'objcpp':
        TypeSpec(['.mm', '.h'], []),
    'ocaml':
        TypeSpec(['.ml', '.mli'], []),
    'opencl':
        TypeSpec(['.cl'], []),
    'parrot':
        TypeSpec(['.pir', '.pasm', '.pmc', '.ops', '.pod', '.pg', '.tg'], []),
    'perl':
        TypeSpec(['.pl', '.pm', '.pod', '.t'], []),
    'php':
        TypeSpec(['.php', '.phpt', '.php3', '.php4', '.php5', '.phtml'], []),
    'plone':
        TypeSpec(['.pt', '.cpt', '.metadata', '.cpy', '.py'], []),
    'py':
        TypeSpec(['.py', '.pyw'], []),
    'python':
        TypeSpec(['.py', '.pyw'], []),
    'rake':
        TypeSpec([], ['[Rr]akefile']),
    'rst':
        TypeSpec(['.rst', '.rest'], []),
    'rb':
        TypeSpec(['.rb'], []),
    'ruby':
        TypeSpec(['.rb', '.rhtml', '.rjs', '.rxml', '.erb', '.rake', '.haml'], []),
    'scala':
        TypeSpec(['.scala'], []),
    'scheme':
        TypeSpec(['.scm', '.ss'], []),
    'scons':
        TypeSpec(['.scons'], ['SConstruct']),
    'shell':
        TypeSpec(['.sh', '.bash', '.csh', '.tcsh', '.ksh', '.zsh'], []),
    'smalltalk':
        TypeSpec(['.st'], []),
    'sql':
        TypeSpec(['.sql', '.ctl'], []),
    'tablegen':
        TypeSpec(['.td'], []),
    'tcl':
        TypeSpec(['.tck', '.itcl', '.itk'], []),
    'td':  # short-name for --tablegen
        TypeSpec(['.td'], []),
    'tex':
        TypeSpec(['.tex', '.cls', '.sty'], []),
    'tt':
        TypeSpec(['.tt', '.tt2', '.ttml'], []),
    'txt':
        TypeSpec(['.txt', '.text'], []),
    'vb':
        TypeSpec(['.bas', '.cls', '.frm', '.ctl', '.vb', '.resx'], []),
    'vim':
        TypeSpec(['.vim'], []),
    'withoutext':
        TypeSpec([''], []),
    'xml':
        TypeSpec(['.xml', '.dtd', '.xslt', '.ent'], []),
    'yaml':
        TypeSpec(['.yaml', '.yml'], []),
}

IGNORED_DIRS = set([
    'blib', '_build', '.bzr', '.cdv', 'cover_db', '__pycache__',
    'CVS', '_darcs', '~.dep', '~.dot', '.git', '.hg', '~.nib',
    '.pc', '~.plst', 'RCS', 'SCCS', '_sgbak', '.svn', '.tox',
    '.metadata', '.cover'])

IGNORED_FILE_PATTERNS = set([r'~$', r'#.+#$', r'[._].*\.swp$', r'core\.\d+$'])


class PssOnlyFindFilesOption:
    """ Option to specify how to "only find files"
    """
    ALL_FILES, FILES_WITH_MATCHES, FILES_WITHOUT_MATCHES = range(3)


def pss_run(roots,
        pattern=None,
        output_formatter=None,
        only_find_files=False,
        only_find_files_option=PssOnlyFindFilesOption.ALL_FILES,
        search_all_types=False,
        search_all_files_and_dirs=False,
        add_ignored_dirs=[],
        remove_ignored_dirs=[],
        recurse=True,
        textonly=False,
        type_pattern=None, # for -G and -g
        include_types=[],  # empty means all known types are included
        exclude_types=[],
        ignore_case=False,
        smart_case=False,
        invert_match=False,
        whole_words=False,
        literal_pattern=False,
        max_match_count=sys.maxsize,
        do_colors=True,
        match_color_str=None,
        filename_color_str=None,
        lineno_color_str=None,
        do_break=True,
        do_heading=True,
        prefix_filename_to_file_matches=True,
        show_column_of_first_match=False,
        ncontext_before=0,
        ncontext_after=0,
        ):
    """ The main pss invocation function - handles all PSS logic.
        For documentation of options, see the --help output of the pss script,
        and study how its command-line arguments are parsed and passed to
        this function. Besides, most options are passed verbatim to submodules
        and documented there. I don't like to repeat myself too much :-)
    """
    # Set up a default output formatter, if none is provided
    #
    if output_formatter is None:
        output_formatter = DefaultPssOutputFormatter(
            do_colors=do_colors,
            match_color_str=match_color_str,
            filename_color_str=filename_color_str,
            lineno_color_str=lineno_color_str,
            do_heading=do_heading,
            prefix_filename_to_file_matches=prefix_filename_to_file_matches,
            show_column_of_first_match=show_column_of_first_match)

    # Set up the FileFinder
    #
    if search_all_files_and_dirs:
        ignore_dirs = set()
    else:
        # gotta love set arithmetic
        ignore_dirs = ((IGNORED_DIRS | set(add_ignored_dirs))
                        - set(remove_ignored_dirs))

    search_extensions = set()
    ignore_extensions = set()
    search_patterns = set()
    ignore_patterns = set()
    filter_include_patterns = set()
    filter_exclude_patterns = set()

    if not search_all_files_and_dirs and not search_all_types:
        filter_exclude_patterns = IGNORED_FILE_PATTERNS

        for typ in (include_types or TYPE_MAP):
            search_extensions.update(TYPE_MAP[typ].extensions)
            search_patterns.update(TYPE_MAP[typ].patterns)

        for typ in exclude_types:
            ignore_extensions.update(TYPE_MAP[typ].extensions)
            ignore_patterns.update(TYPE_MAP[typ].patterns)
    else:
        # all files are searched
        pass

    # type_pattern (-g/-G) is an AND filter to the search criteria
    if type_pattern is not None:
        filter_include_patterns.add(type_pattern)

    filefinder = FileFinder(
            roots=roots,
            recurse=recurse,
            find_only_text_files=textonly,
            ignore_dirs=ignore_dirs,
            search_extensions=search_extensions,
            ignore_extensions=ignore_extensions,
            search_patterns=search_patterns,
            ignore_patterns=ignore_patterns,
            filter_include_patterns=filter_include_patterns,
            filter_exclude_patterns=filter_exclude_patterns)

    # Set up the content matcher
    #

    if pattern is None:
        pattern = b''
    else:
        pattern = str2bytes(pattern)

    if (    not ignore_case and
            (smart_case and not _pattern_has_uppercase(pattern))):
        ignore_case = True

    matcher = ContentMatcher(
            pattern=pattern,
            ignore_case=ignore_case,
            invert_match=invert_match,
            whole_words=whole_words,
            literal_pattern=literal_pattern,
            max_match_count=max_match_count)

    # All systems go...
    #
    for filepath in filefinder.files():
        # If only_find_files is requested and no special option provided,
        # this is kind of 'find -name'
        if (    only_find_files and
                only_find_files_option == PssOnlyFindFilesOption.ALL_FILES):
            output_formatter.found_filename(filepath)
            continue
        # The main path: do matching inside the file.
        # Some files appear to be binary - they are not of a known file type
        # and the heuristic istextfile says they're binary. For these files
        # we try to find a single match and then simply report they're binary
        # files with a match. For other files, we let ContentMatcher do its
        # full work.
        #
        try:
            with open(filepath, 'rb') as fileobj:
                if not istextfile(fileobj):
                    # istextfile does some reading on fileobj, so rewind it
                    fileobj.seek(0)
                    matches = list(matcher.match_file(fileobj, max_match_count=1))
                    if matches:
                        output_formatter.binary_file_matches(
                                'Binary file %s matches\n' % filepath)
                    continue
                # istextfile does some reading on fileobj, so rewind it
                fileobj.seek(0)

                # If only files are to be found either with or without matches...
                if only_find_files:
                    matches = list(matcher.match_file(fileobj, max_match_count=1))
                    found = (
                        (   matches and
                            only_find_files_option == PssOnlyFindFilesOption.FILES_WITH_MATCHES)
                        or
                        (   not matches and
                            only_find_files_option == PssOnlyFindFilesOption.FILES_WITHOUT_MATCHES))
                    if found:
                        output_formatter.found_filename(filepath)
                    continue

                # This is the "normal path" when we examine and display the
                # matches inside the file.
                matches = list(matcher.match_file(fileobj))
                if not matches:
                    # Nothing to see here... move along
                    continue
                output_formatter.start_matches_in_file(filepath)
                if ncontext_before > 0 or ncontext_after > 0:
                    # If context lines should be printed, we have to read in the
                    # file line by line, marking which lines belong to context,
                    # which are matches, and which aren't interesting.
                    # _build_match_context_dict is used to create a dictionary
                    # that tells us for each line what category it belongs to
                    #
                    fileobj.seek(0)
                    match_context_dict = _build_match_context_dict(
                            matches, ncontext_before, ncontext_after)
                    # For being able to correctly emit context separators between
                    # non-adjacent chunks of context, these flags are maintained:
                    #   prev_was_blank: the previous line was blank
                    #   had_context: we already had some context printed before
                    #
                    prev_was_blank = False
                    had_context = False
                    for n, line in enumerate(fileobj, 1):
                        # Find out whether this line is a match, context or
                        # neither, and act accordingly
                        result, match = match_context_dict.get(n, (None, None))
                        if result is None:
                            prev_was_blank = True
                            continue
                        elif result == LINE_MATCH:
                            output_formatter.matching_line(match, filepath)
                        elif result == LINE_CONTEXT:
                            if prev_was_blank and had_context:
                                output_formatter.context_separator()
                            output_formatter.context_line(line, n, filepath)
                            had_context = True
                        prev_was_blank = False
                else:
                    # just show the matches without considering context
                    for match in matches:
                        output_formatter.matching_line(match, filepath)

                if do_break:
                    output_formatter.end_matches_in_file(filepath)
        except (OSError, IOError):
            # There was a problem opening or reading the file, so ignore it.
            pass

def _pattern_has_uppercase(pattern):
    """ Check whether the given regex pattern has uppercase letters to match
    """
    # Somewhat rough - check for uppercase chars not following an escape
    # char (which may mean valid regex flags like \A or \B)
    skipnext = False
    for c in pattern:
        if skipnext:
            skipnext = False
            continue
        elif c == '\\':
            skipnext = True
        else:
            if c >= 'A' and c <= 'Z':
                return True
    return False


LINE_MATCH, LINE_CONTEXT = range(2)


def _build_match_context_dict(matches, ncontext_before, ncontext_after):
    """ Given a list of MatchResult objects and number of context lines before
        and after a match, build a dictionary that maps line numbers to
        (line_kind, data) pairs. line_kind is either LINE_MATCH or LINE_CONTEXT
        and data holds the match object for LINE_MATCH.
    """
    d = {}
    for match in matches:
        # Take care to give LINE_MATCH entries priority over LINE_CONTEXT
        lineno = match.matching_lineno
        d[lineno] = LINE_MATCH, match

        context_start = lineno - ncontext_before
        context_end = lineno + ncontext_after
        for ncontext in range(context_start, context_end + 1):
            if ncontext not in d:
                d[ncontext] = LINE_CONTEXT, None
    return d



########NEW FILE########
__FILENAME__ = filefinder
#-------------------------------------------------------------------------------
# pss: filefinder.py
#
# FileFinder class that finds files recursively according to various rules.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import re

from .utils import istextfile


class FileFinder(object):
    def __init__(self,
            roots,
            recurse=True,
            ignore_dirs=[],
            find_only_text_files=False,
            search_extensions=[],
            ignore_extensions=[],
            search_patterns=[],
            ignore_patterns=[],
            filter_include_patterns=[],
            filter_exclude_patterns=[]):
        """ Create a new FileFinder. The parameters are the "search rules"
            that dictate which files are found.

            roots:
                Root files/directories from which the search will start

            recurse:
                Should I recurse into sub-directories?

            ignore_dirs:
                Iterable of directory names that will be ignored during the
                search

            find_only_text_files:
                If True, uses a heuristic to determine which files are text
                and which are binary, and ignores the binary files.
                Warning: this option makes FileFinder actually open the files
                and read a portion from them, so it is quite slow.

            search_extensions:
            search_patterns:
                We look for either known extensions (sequences of strings) or
                matching patterns (sequence of regexes).
                If neither of these is specified, all extensions & patterns can
                be found (assuming they're not filtered out by other criteria).
                If either is specified, then the file name should match either
                one of the extensions or one of the patterns.

            ignore_extensions:
            ignore_patterns:
                Extensions and patterns to ignore. Take precedence over search_
                parameters.

            filter_include_patterns:
                Filtering: applied as logical AND with the search criteria.
                If non-empty, only files with names matching these pattens will
                be found. If empty, no pattern restriction is applied.

            filter_exclude_patterns:
                Files with names matching these patterns will never be found.
                Overrides all include rules.
        """
        # Prepare internal data structures from the parameters
        self.roots = roots
        self.recurse = recurse
        self.search_extensions = set(search_extensions)
        self.ignore_extensions = set(ignore_extensions)
        self.search_pattern = self._merge_regex_patterns(search_patterns)
        self.ignore_pattern = self._merge_regex_patterns(ignore_patterns)
        self.filter_include_pattern = self._merge_regex_patterns(
                                                filter_include_patterns)
        self.filter_exclude_pattern = self._merge_regex_patterns(
                                                filter_exclude_patterns)

        # Distinguish between dirs (like "foo") and paths (like "foo/bar")
        # to ignore.
        self.ignore_dirs = set()
        self.ignore_paths = set()
        for d in ignore_dirs:
            if os.sep in d:
                self.ignore_paths.add(d)
            else:
                self.ignore_dirs.add(d)

        self.find_only_text_files = find_only_text_files

    def files(self):
        """ Generate files according to the search rules. Yield
            paths to files one by one.
        """
        for root in self.roots:
            if os.path.isfile(root):
                if self._file_is_found(root):
                    yield root
            else: # dir
                for dirpath, subdirs, files in os.walk(root):
                    if self._should_ignore_dir(dirpath):
                        # This dir should be ignored, so remove all its subdirs
                        # from the walk and go to next dir.
                        del subdirs[:]
                        continue
                    for filename in files:
                        fullpath = os.path.join(dirpath, filename)
                        if (    self._file_is_found(fullpath) and
                                os.path.exists(fullpath)):
                            yield fullpath
                    if not self.recurse:
                        break

    def _merge_regex_patterns(self, patterns):
        """ patterns is a sequence of strings describing regexes. Merge
            them into a single compiled regex.
        """
        if len(patterns) == 0:
            return None
        one_pattern = '|'.join('(?:{0})'.format(p) for p in patterns)
        return re.compile(one_pattern)

    def _should_ignore_dir(self, dirpath):
        """ Should the given directory be ignored?
        """
        if os.path.split(dirpath)[1] in self.ignore_dirs:
            return True
        elif len(self.ignore_paths) > 0:
            # If we have paths to ignore, things are more difficult...
            for ignored_path in self.ignore_paths:
                found_i = dirpath.rfind(ignored_path)
                if (found_i == 0 or (
                    found_i > 0 and dirpath[found_i - 1] == os.sep)
                    ):
                    return True
        return False

    def _file_is_found(self, filename):
        """ Should this file be "found" according to the search rules?
        """
        # Tries to eliminate the file by all the given search rules. If the
        # file survives until the end, it's found
        root, ext = os.path.splitext(filename)

        # The ignores take precedence.
        if (ext in self.ignore_extensions or
            self.ignore_pattern and self.ignore_pattern.search(filename)
            ):
            return False

        # Try to find a match either in search_extensions OR search_pattern.
        # If neither is specified, we have a match by definition.
        have_match = False
        if not self.search_extensions and not self.search_pattern:
            # Both empty: means all extensions and patterns are interesting.
            have_match = True
        if self.search_extensions and ext in self.search_extensions:
            have_match = True
        if self.search_pattern and self.search_pattern.search(filename):
           have_match = True

        if not have_match:
            return False

        # Now onto filters. Only files matches that don't trigger the exclude
        # filters and do trigger the include filters (if any exists) go through.
        if (self.filter_exclude_pattern and
            self.filter_exclude_pattern.search(filename)
            ):
            return False

        if (self.filter_include_pattern and
            not self.filter_include_pattern.search(filename)
            ):
            return False

        # If find_only_text_files, open the file and try to determine whether
        # it's text or binary.
        if self.find_only_text_files:
            try:
                with open(filename, 'rb') as f:
                    if not istextfile(f):
                        return False
            except OSError:
                # If there's a problem opening or reading the file, we
                # don't need it.
                return False

        return True


if __name__ == '__main__':
    import sys
    ff = FileFinder(sys.argv[1:], ignore_dirs=[], recurse=True)
    print(list(ff.files()))


########NEW FILE########
__FILENAME__ = matchresult
#-------------------------------------------------------------------------------
# pss: matchresult.py
#
# MatchResult - represents a single match result from a file.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple


# matching_line:
#   The line that matched the pattern
#
# matching_lineno:
#   Line number of the matching line
#
# matching_column_ranges:
#   A list of pairs. Its length is the amount of matches for the pattern in the
#   line. Each pair of column numbers specifies the exact range in the line
#   that matched the pattern. The range is right-open like all ranges in
#   Python.
#   I.e. range (2, 5) means columns 2,3,4 matched
#
MatchResult = namedtuple('MatchResult', ' '.join([
                'matching_line',
                'matching_lineno',
                'matching_column_ranges']))


########NEW FILE########
__FILENAME__ = outputformatter
#-------------------------------------------------------------------------------
# pss: outputformatter.py
#
# OutputFormatter interface.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys


class OutputFormatter(object):
    """ This is an abstract interface, to be implemented by output formatting
        classes. Individual methods that must be implemented are documented
        below. Note that some have default implementations (i.e. do not raise
        NotImplementedError)

        The pss driver expects an object adhering to this interface to do its
        output.
    """
    def start_matches_in_file(self, filename):
        """ Called when a sequences of matches from some file is about to be
            output. filename is the name of the file in which the matches were
            found.
        """
        raise NotImplementedError()

    def end_matches_in_file(self, filename):
        """ Called when the matches for a file have finished.
        """
        pass

    def matching_line(self, matchresult, filename):
        """ Called to emit a matching line, with a matchresult.MatchResult
            object.
        """
        raise NotImplementedError()

    def context_line(self, line, lineno, filename):
        """ Called to emit a context line.
        """
        pass

    def context_separator(self):
        """ Called to emit a "context separator" - line between non-adjacent
            context lines.
        """
        pass

    def binary_file_matches(self, msg):
        """ Called to emit a simple message inside the matches for some file.
        """
        raise NotImplementedError()

    def found_filename(self, filename):
        """ Called to emit a found filename when pss runs in file finding mode
            instead of line finding mode (emitting only the found files and not
            matching their contents).
        """
        raise NotImplementedError()


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    of = OutputFormatter()
    of.start_matches_in_file('f')


########NEW FILE########
__FILENAME__ = pss
#-------------------------------------------------------------------------------
# pss: pss.py
#
# Top-level script. Run without arguments or with -h to see usage help.
# To actually run it, import and invoke 'main' from a runnable script
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import os, sys
import optparse


from psslib import __version__
from psslib.driver import (pss_run, TYPE_MAP,
        IGNORED_DIRS, IGNORED_FILE_PATTERNS, PssOnlyFindFilesOption)


def main(argv=sys.argv, output_formatter=None):
    """ Main pss

        argv:
            Program arguments, similar to sys.argv

        output_formatter:
            An OutputFormatter object to emit output to. Set to None for
            the default.
    """
    options, args, optparser = parse_cmdline(argv[1:])

    # Handle the various "only find files" options.
    #
    only_find_files = False
    only_find_files_option = PssOnlyFindFilesOption.ALL_FILES
    search_pattern_expected = True

    if options.find_files:
        only_find_files = True
        search_pattern_expected = False
    elif options.find_files_matching_pattern is not None:
        only_find_files = True
        search_pattern_expected = False
        options.type_pattern = options.find_files_matching_pattern
    elif options.find_files_with_matches:
        only_find_files = True
        only_find_files_option = PssOnlyFindFilesOption.FILES_WITH_MATCHES
    elif options.find_files_without_matches:
        only_find_files = True
        only_find_files_option = PssOnlyFindFilesOption.FILES_WITHOUT_MATCHES

    # The --match option sets the pattern explicitly, so it's not expected
    # as an argument.
    if options.match:
        search_pattern_expected = False

    # Handle the various --help options, or just print help if pss is called
    # without arguments.
    if options.help_types:
        print_help_types()
        sys.exit(0)
    elif options.show_type_list:
        show_type_list()
        sys.exit(0)
    elif (len(args) == 0 and search_pattern_expected) or options.help:
        optparser.print_help()
        print(DESCRIPTION_AFTER_USAGE)
        sys.exit(0)

    # Unpack args. If roots are not specified, the current directory is the
    # only root. If no search pattern is expected, the whole of 'args' is roots.
    #
    if not search_pattern_expected:
        pattern = options.match or None
        roots = args
    else:
        pattern = args[0]
        roots = args[1:]
    if len(roots) == 0:
        roots = ['.']

    # Partition the type list to included types (--<type>) and excluded types
    # (--no<type>)
    #
    include_types = []
    exclude_types = []
    for typ in getattr(options, 'typelist', []):
        if typ.startswith('no'):
            exclude_types.append(typ[2:])
        else:
            include_types.append(typ)

    # If the context option is specified, it overrides both after-context
    # and before-context
    #
    ncontext_before = options.before_context
    ncontext_after = options.after_context
    if options.context is not None:
        ncontext_before = ncontext_after = options.context

    add_ignored_dirs = _splice_comma_names(options.ignored_dirs or [])
    remove_ignored_dirs = _splice_comma_names(options.noignored_dirs or [])

    # Finally, invoke pss_run with the default output formatter
    #
    try:
        pss_run(roots=roots,
                pattern=pattern,
                output_formatter=output_formatter,
                only_find_files=only_find_files,
                only_find_files_option=only_find_files_option,
                search_all_types=options.all_types,
                search_all_files_and_dirs=options.unrestricted,
                add_ignored_dirs=add_ignored_dirs,
                remove_ignored_dirs=remove_ignored_dirs,
                recurse=options.recurse,
                textonly=options.textonly,
                type_pattern=options.type_pattern,
                include_types=include_types,
                exclude_types=exclude_types,
                ignore_case=options.ignore_case,
                smart_case=options.smart_case,
                invert_match=options.invert_match,
                whole_words=options.word_regexp,
                literal_pattern=options.literal,
                max_match_count=options.max_count,
                do_colors=options.do_colors,
                match_color_str=options.color_match,
                filename_color_str=options.color_filename,
                lineno_color_str=options.color_lineno,
                do_break=options.do_break,
                do_heading=options.do_heading,
                prefix_filename_to_file_matches=options.prefix_filename,
                show_column_of_first_match=options.show_column,
                ncontext_before=ncontext_before,
                ncontext_after=ncontext_after)
    except KeyboardInterrupt:
        print('<<interrupted - exiting>>')
        sys.exit(0)


DESCRIPTION = r'''
Search for the pattern in each source file, starting with the
current directory and its sub-directories, recursively. If
[files] are specified, only these files/directories are searched.

Only files with known extensions are searched, and this can be
configured by providing --<type> options. For example, --python
will search all Python files, and "--lisp --scheme" will search
all Lisp and all Scheme files. By default, all known file types
are searched.

Run with --help-types for more help on how to select file types.
'''.lstrip()


def _ignored_dirs_as_string():
    s = ['    ']
    for i, dir in enumerate(IGNORED_DIRS):
        s.append('%-9s' % dir)
        if i % 4 == 3:
            s.append('\n    ')
    return ' '.join(s)


DESCRIPTION_AFTER_USAGE = r'''
By default, the following directories and everything below them is
ignored:

%s

To manually control which directories are ignored, use the --ignore-dir
and --noignore-dir options. Specify --unrestricted if you don't want any
directory to be ignored.

Additionally, files matching these (regexp) patterns are ignored:

      %s

pss version %s
''' % ( _ignored_dirs_as_string(),
        '\n      '.join(IGNORED_FILE_PATTERNS),
        __version__,)


def parse_cmdline(cmdline_args):
    """ Parse the list of command-line options and arguments and return a
        triple: options, args, parser -- the first two being the result of
        OptionParser.parse_args, and the third the parser object itself.`
    """
    optparser = optparse.OptionParser(
        usage='usage: %prog [options] <pattern> [files]',
        description=DESCRIPTION,
        prog='pss',
        add_help_option=False,  # -h is a real option
        version='pss %s' % __version__)

    optparser.add_option('--help-types',
        action='store_true', dest='help_types',
        help='Display supported file types')
    optparser.add_option('--help',
        action='store_true', dest='help',
        help='Display this information')

    # This option is for internal usage by the bash completer, so we're hiding
    # it from the --help output
    optparser.add_option('--show-type-list',
        action='store_true', dest='show_type_list',
        help=optparse.SUPPRESS_HELP)

    group_searching = optparse.OptionGroup(optparser, 'Searching')
    group_searching.add_option('-i', '--ignore-case',
        action='store_true', dest='ignore_case', default=False,
        help='Ignore case distinctions in the pattern')
    group_searching.add_option('--smart-case',
        action='store_true', dest='smart_case', default=False,
        help='Ignore case distinctions in the pattern, only if the pattern '
        'contains no upper case. Ignored if -i is specified')
    group_searching.add_option('-v', '--invert-match',
        action='store_true', dest='invert_match', default=False,
        help='Invert match: show non-matching lines')
    group_searching.add_option('-w', '--word-regexp',
        action='store_true', dest='word_regexp', default=False,
        help='Force the pattern to match only whole words')
    group_searching.add_option('-Q', '--literal',
        action='store_true', dest='literal', default=False,
        help='Quote all metacharacters; the pattern is literal')
    optparser.add_option_group(group_searching)

    group_output = optparse.OptionGroup(optparser, 'Search output')
    group_output.add_option('--match',
        action='store', dest='match', metavar='PATTERN',
        help='Specify the search pattern explicitly')
    group_output.add_option('-m', '--max-count',
        action='store', dest='max_count', metavar='NUM', default=sys.maxsize,
        type='int', help='Stop searching in each file after NUM matches')
    group_output.add_option('-H', '--with-filename',
        action='store_true', dest='prefix_filename', default=True,
        help=' '.join(r'''Print the filename before matches (default). If
        --noheading is specified, the filename will be prepended to each
        matching line. Otherwise it is printed once for all the matches
        in the file.'''.split()))
    group_output.add_option('-h', '--no-filename',
        action='store_false', dest='prefix_filename',
        help='Suppress printing the filename before matches')
    group_output.add_option('--column',
        action='store_true', dest='show_column',
        help='Show the column number of the first match')
    group_output.add_option('-A', '--after-context',
        action='store', dest='after_context', metavar='NUM', default=0,
        type='int', help='Print NUM lines of context after each match')
    group_output.add_option('-B', '--before-context',
        action='store', dest='before_context', metavar='NUM', default=0,
        type='int', help='Print NUM lines of context before each match')
    group_output.add_option('-C', '--context',
        action='store', dest='context', metavar='NUM', type='int',
        help='Print NUM lines of context before and after each match')
    group_output.add_option('--color',
        action='store_true', dest='do_colors', default=sys.stdout.isatty(),
        help='Highlight the matching text')
    group_output.add_option('--nocolor',
        action='store_false', dest='do_colors',
        help='Do not highlight the matching text (this is the default when output is redirected)')
    group_output.add_option('--color-match', metavar='FORE,BACK,STYLE',
        action='store', dest='color_match',
        help='Set the color for matches')
    group_output.add_option('--color-filename', metavar='FORE,BACK,STYLE',
        action='store', dest='color_filename',
        help='Set the color for emitted filenames')
    group_output.add_option('--color-lineno', metavar='FORE,BACK,STYLE',
        action='store', dest='color_lineno',
        help='Set the color for line numbers')
    group_output.add_option('--nobreak',
        action='store_false', dest='do_break', default=sys.stdout.isatty(),
        help='Print no break between results from different files')
    group_output.add_option('--noheading',
        action='store_false', dest='do_heading', default=sys.stdout.isatty(),
        help="Print no file name heading above each file's results")
    optparser.add_option_group(group_output)

    group_filefinding = optparse.OptionGroup(optparser, 'File finding')
    group_filefinding.add_option('-f',
        action='store_true', dest='find_files',
        help='Only print the names of found files. The pattern must not be specified')
    group_filefinding.add_option('-g',
        action='store', dest='find_files_matching_pattern', metavar='REGEX',
        help='Same as -f, but only print files matching REGEX')
    group_filefinding.add_option('-l', '--files-with-matches',
        action='store_true', dest='find_files_with_matches',
        help='Only print the names of found files that have matches for the pattern')
    group_filefinding.add_option('-L', '--files-without-matches',
        action='store_true', dest='find_files_without_matches',
        help='Only print the names of found files that have no matches for the pattern')
    optparser.add_option_group(group_filefinding)

    group_inclusion = optparse.OptionGroup(optparser, 'File inclusion/exclusion')
    group_inclusion.add_option('-a', '--all-types',
        action='store_true', dest='all_types',
        help='All file types are searched')
    group_inclusion.add_option('-u', '--unrestricted',
        action='store_true', dest='unrestricted',
        help='All files are searched, including those in ignored directories')
    group_inclusion.add_option('--ignore-dir',
        action='append', dest='ignored_dirs', metavar='name',
        help='Add directory to the list of ignored dirs')
    group_inclusion.add_option('--noignore-dir',
        action='append', dest='noignored_dirs', metavar='name',
        help='Remove directory from the list of ignored dirs')
    group_inclusion.add_option('-r', '-R', '--recurse',
        action='store_true', dest='recurse', default=True,
        help='Recurse into subdirectories (default)')
    group_inclusion.add_option('-n', '--no-recurse',
        action='store_false', dest='recurse',
        help='Do not recurse into subdirectories')
    group_inclusion.add_option('-t', '--textonly', '--nobinary',
        action='store_true', dest='textonly', default=False,
        help='''Restrict the search to only textual files.
        Warning: with this option the search is likely to run much slower''')
    group_inclusion.add_option('-G',
        action='store', dest='type_pattern', metavar='REGEX',
        help='Only search files that match REGEX')
    optparser.add_option_group(group_inclusion)

    # Parsing --<type> and --no<type> options for all supported types is
    # done with a callback action. The callback function stores a list
    # of all type options in the typelist attribute of the options.
    #
    def type_option_callback(option, opt_str, value, parser):
        optname = opt_str.lstrip('-')
        if hasattr(parser.values, 'typelist'):
            parser.values.typelist.append(optname)
        else:
            parser.values.typelist = [optname]

    for t in TYPE_MAP:
        optparser.add_option('--' + t,
            help=optparse.SUPPRESS_HELP,
            action='callback',
            callback=type_option_callback)
        optparser.add_option('--no' + t,
            help=optparse.SUPPRESS_HELP,
            action='callback',
            callback=type_option_callback)

    options, args = optparser.parse_args(cmdline_args)
    return options, args, optparser


HELP_TYPES_PREAMBLE = r'''
The following types are supported.  Each type enables searching
in several file extensions or name regexps.  --<type> includes
the type in search and --no<type> excludes it.
'''.lstrip()


def print_help_types():
    print(HELP_TYPES_PREAMBLE)

    for typ in sorted(TYPE_MAP):
        typestr = '--[no]%s' % typ
        print('    %-21s' % typestr, end='')
        print(' '.join(TYPE_MAP[typ].extensions + TYPE_MAP[typ].patterns))
    print()


def show_type_list():
    print(' '.join(('--%s' % typ) for typ in TYPE_MAP))


def _splice_comma_names(namelist):
    """ Given a list of names, some of the names can be comma-separated lists.
        Return a new list of single names (names in comma-separated lists are
        spliced into the list).
    """
    newlist = []
    for name in namelist:
        if ',' in name:
            newlist.extend(name.split(','))
        else:
            newlist.append(name)
    return newlist



########NEW FILE########
__FILENAME__ = py3compat
#-------------------------------------------------------------------------------
# pss: py3compat.py
#
# Some Python2&3 compatibility code
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys
PY3 = sys.version_info[0] == 3


identity_func = lambda x: x

# str2bytes -- converts a given string (which we know not to contain
# unicode chars) to bytes.
#
# bytes2str -- converts a bytes object to a string
#
# int2byte -- takes an integer in the 8-bit range and returns
# a single-character byte object in py3 / a single-character string
# in py2.
#
if PY3:
    def str2bytes(s):
        return s.encode('latin1')
    def int2byte(i):
        return bytes((i,))
    def bytes2str(b):
        return b.decode('utf-8')
else:
    str2bytes = identity_func
    int2byte = chr
    bytes2str = identity_func


def tostring(b):
    """ Convert the given bytes or string object to string
    """
    if isinstance(b, bytes):
        return bytes2str(b)
    else:
        return b


########NEW FILE########
__FILENAME__ = utils
#-------------------------------------------------------------------------------
# pss: utils.py
#
# Some miscellaneous utilities for pss.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .py3compat import int2byte
from . import colorama


_text_characters = (
        b''.join(int2byte(i) for i in range(32, 127)) +
        b'\n\r\t\f\b')

def istextfile(fileobj, blocksize=512):
    """ Uses heuristics to guess whether the given file is text or binary,
        by reading a single block of bytes from the file.
        If more than 30% of the chars in the block are non-text, or there
        are NUL ('\x00') bytes in the block, assume this is a binary file.
    """
    block = fileobj.read(blocksize)
    if b'\x00' in block:
        # Files with null bytes are binary
        return False
    elif not block:
        # An empty file is considered a valid text file
        return True

    # Use translate's 'deletechars' argument to efficiently remove all
    # occurrences of _text_characters from the block
    nontext = block.translate(None, _text_characters)
    return float(len(nontext)) / len(block) <= 0.30


def decode_colorama_color(color_str):
    """ Decode a Colorama color encoded in a string in the following format:
        FORE,BACK,STYLE

        FORE: foreground color (one of colorama.Fore)
        BACK: background color (one of colorama.Back)
        STYLE: style (one of colorama.Style)

        For example, for CYAN text on GREEN background with a DIM style
        (pretty, aye?) the input should be: CYAN,GREEN,DIM

        BACK and STYLE are optional. If STYLE is not specified, the default is
        colorama.Style.NORMAL. If BACK is not specified, the default is
        colorama.Back.BLACK.

        Return the colorama color, or None if there's a problem decoding.
    """
    if not color_str:
        return None

    # Split the input and add defaults. After this, parts is a 3-element list
    parts = color_str.split(',')
    if len(parts) == 1:
        parts.append('RESET')
    if len(parts) == 2:
        parts.append('NORMAL')

    try:
        c_fore = getattr(colorama.Fore, parts[0])
        c_back = getattr(colorama.Back, parts[1])
        c_style = getattr(colorama.Style, parts[2])
        return c_fore + c_back + c_style
    except AttributeError:
        return None




########NEW FILE########
__FILENAME__ = pss
#!/usr/bin/env python
from psslib.pss import main; main()


########NEW FILE########
__FILENAME__ = all_tests
#!/usr/bin/env python

import unittest

suite = unittest.TestLoader().loadTestsFromNames([
    'test_filefinder',
    'test_contentmatcher',
    'test_driver',
    'test_pssmain'
])
unittest.TextTestRunner(verbosity=1).run(suite)



########NEW FILE########
__FILENAME__ = f

########NEW FILE########
__FILENAME__ = test_contentmatcher
try:
    from cStringIO import StringIO
except ImportError:
    # python 3
    from io import StringIO

import os
import pprint
import sys
import unittest

sys.path.extend(['.', '..'])
from psslib.contentmatcher import ContentMatcher, MatchResult


text1 = r'''some line vector<int>
another line here
this has line and then 'line' again
and here we have none vector <int>
Uppercase Line yes?
         line start
many lines and linen too! even a spline yess
'''

text2 = r'''creampie
apple pie and plum pie
pierre is $\k jkm
dptr .*n and again some pie
'''


class TestContentMatcher(unittest.TestCase):
    def num_matches(self, pattern, text, **kwargs):
        """ Number of matching lines for the pattern in the text. kwargs are
            passed to ContentMatcher.
        """
        cm = ContentMatcher(pattern, **kwargs)
        return len(list(cm.match_file(StringIO(text))))

    def assertMatches(self, cm, text, exp_matches):
        # exp_matches is a list of pairs: lineno, list of column ranges
        matches = list(cm.match_file(StringIO(text)))
        self.assertEqual(len(matches), len(exp_matches))
        textlines = text.split('\n')
        for n, exp_match in enumerate(exp_matches):
            exp_matchresult = MatchResult(
                    textlines[exp_match[0] - 1] + '\n',
                    exp_match[0],
                    exp_match[1])
            self.assertEqual(exp_matchresult, matches[n])

    def test_defaults(self):
        cm = ContentMatcher('line')
        self.assertMatches(cm, text1, [
                (1, [(5, 9)]),
                (2, [(8, 12)]),
                (3, [(9, 13), (24, 28)]),
                (6, [(9, 13)]),
                (7, [(5, 9), (15, 19), (35, 39)])])

        cm = ContentMatcher('Line')
        self.assertMatches(cm, text1, [(5, [(10, 14)])])

        cm = ContentMatcher('L[ix]ne')
        self.assertMatches(cm, text1, [(5, [(10, 14)])])

        cm = ContentMatcher('upper')
        self.assertMatches(cm, text1, [])

    def test_regex_match(self):
        # literal "yes?" matches once
        self.assertEqual(self.num_matches(r'yes\?', text1), 1)
        # regex matching ye(s|) - twice
        self.assertEqual(self.num_matches(r'yes?', text1), 2)

        self.assertEqual(self.num_matches(r'vector', text1), 2)
        self.assertEqual(self.num_matches(r'vector *<', text1), 2)
        self.assertEqual(self.num_matches(r'vector +<', text1), 1)

    def test_id_regex_match_detailed(self):
        t1 = 'some line with id_4 and vec8f too'
        self.assertEqual(self.num_matches(r'id_4', t1), 1)
        self.assertEqual(self.num_matches(r'8f', t1), 1)
        self.assertEqual(self.num_matches(r'[0-9]f', t1), 1)

        self.assertEqual(self.num_matches('8F', t1, ignore_case=True), 1)
        self.assertEqual(self.num_matches('84', t1, ignore_case=True), 0)
        self.assertEqual(self.num_matches('84', t1, invert_match=True), 1)

    def test_ignore_case(self):
        cm = ContentMatcher('upper', ignore_case=True)
        self.assertMatches(cm, text1, [(5, [(0, 5)])])

    def test_invert_match(self):
        cm = ContentMatcher('line', invert_match=True)
        self.assertMatches(cm, text1, [(4, []), (5, [])])

        cm = ContentMatcher('line', invert_match=True, ignore_case=True)
        self.assertMatches(cm, text1, [(4, [])])

    def test_max_count(self):
        cm = ContentMatcher('line', max_match_count=1)
        self.assertMatches(cm, text1, [(1, [(5, 9)])])

        cm = ContentMatcher('line', max_match_count=2)
        self.assertMatches(cm, text1,
                [(1, [(5, 9)]), (2, [(8, 12)])])

        cm = ContentMatcher('a', max_match_count=1)
        self.assertMatches(cm, text1,
                [(2, [(0, 1)])])

    def test_whole_words(self):
        cm = ContentMatcher('pie', whole_words=True)
        self.assertMatches(cm, text2, [
                (2, [(6, 9), (19, 22)]),
                (4, [(24, 27)])])

        cm = ContentMatcher('.*n', literal_pattern=True)
        self.assertMatches(cm, text2, [(4, [(5, 8)])])

        cm = ContentMatcher(r'$\k', literal_pattern=True)
        self.assertMatches(cm, text2, [(3, [(10, 13)])])

        cm = ContentMatcher(r'$\k', literal_pattern=False)
        self.assertMatches(cm, text2, [])


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()




########NEW FILE########
__FILENAME__ = test_driver
import os, sys
import unittest

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from psslib.driver import pss_run
from test.utils import path_to_testdir, MockOutputFormatter


class TestDriver(unittest.TestCase):
    # Just basic sanity tests for pss_run
    # Do all the heavy testing in test_pssmain.py, because it also testse the
    # cmdline argument parsing and combination logic.
    #
    testdir1 = path_to_testdir('testdir1')

    def setUp(self):
        self.of = MockOutputFormatter('testdir1')

    def test_basic(self):
        pss_run(
            roots=[self.testdir1],
            pattern='abc',
            output_formatter=self.of,
            include_types=['cc'])

        self.assertEqual(sorted(self.of.output),
                sorted(self._gen_outputs_in_file(
                    'testdir1/filea.c', [('MATCH', (2, [(4, 7)]))]) +
                self._gen_outputs_in_file(
                    'testdir1/filea.h', [('MATCH', (1, [(8, 11)]))])))

    def _gen_outputs_in_file(self, filename, outputs):
        """ Helper method for constructing a list of output pairs in the format
            of MockOutputFormatter, delimited from both ends with START_MATCHES
            and END_MATCHES for the given filename.
        """
        seq = []
        seq.append(('START_MATCHES', os.path.normpath(filename)))
        seq.extend(outputs)
        seq.append(('END_MATCHES', os.path.normpath(filename)))
        return seq


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filefinder
import os
import sys
import unittest

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from psslib.filefinder import FileFinder
from test.utils import path_to_testdir, path_relative_to_dir, filter_out_path


class TestFileFinder(unittest.TestCase):
    testdir_simple = path_to_testdir('simple_filefinder')

    all_c_files = [
            'simple_filefinder/.bzr/hgc.c',
            'simple_filefinder/a.c',
            'simple_filefinder/anothersubdir/a.c',
            'simple_filefinder/partialignored/thisoneisignored/notfound.c',
            'simple_filefinder/partialignored/found.c',
            'simple_filefinder/c.c']

    all_cpp_files = [
            'simple_filefinder/.bzr/ttc.cpp',
            'simple_filefinder/anothersubdir/CVS/r.cpp',
            'simple_filefinder/anothersubdir/deep/t.cpp',
            'simple_filefinder/anothersubdir/deep/tt.cpp',
            'simple_filefinder/b.cpp',
            'simple_filefinder/truesubdir/gc.cpp',
            'simple_filefinder/truesubdir/r.cpp']

    c_and_cpp_files = sorted(all_c_files + all_cpp_files)

    def _find_files(self, roots, **kwargs):
        """ Utility method for running FileFinder with the provided arguments.
            Return a sorted list of found files. The file names are processed
            to make path relative to the simple_filefinder dir.
        """
        ff = FileFinder(roots, **kwargs)
        return sorted(list(path_relative_to_dir(path, 'simple_filefinder')
                                for path in ff.files()
                                if not filter_out_path(path)))

    def assertPathsEqual(self, first, second):
        """ Compare lists of paths together, normalizing them for portability
            and sorting.
        """
        self.assertEqual(
                list(sorted(map(os.path.normpath, first))),
                list(sorted(map(os.path.normpath, second))))

    def test_extensions(self):
        # just the .c files
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.c']),
                self.all_c_files)

        # just the .cpp files
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.cpp']),
                self.all_cpp_files)

        # both .c and .cpp files
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.cpp', '.c']),
                self.c_and_cpp_files)

        # search both .c and .cpp, but ask to ignore .c
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.cpp', '.c'],
                    ignore_extensions=['.c']),
                self.all_cpp_files)

    def test_no_recurse(self):
        # .c files from root without recursing
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    recurse=False,
                    search_extensions=['.c']),
                [   'simple_filefinder/a.c',
                    'simple_filefinder/c.c'])

    def test_text_only(self):
        # all .F90 files
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.F90'],
                    find_only_text_files=False),
                [   'simple_filefinder/truesubdir/bin1.F90',
                    'simple_filefinder/truesubdir/txt1.F90',
                    'simple_filefinder/truesubdir/txt2.F90'])

        # text .F90 files
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.F90'],
                    find_only_text_files=True),
                [   'simple_filefinder/truesubdir/txt1.F90',
                    'simple_filefinder/truesubdir/txt2.F90'])

    def test_ignore_dirs(self):
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    search_extensions=['.c'],
                    ignore_dirs=['anothersubdir', '.bzr',
                                 os.path.join('partialignored',
                                              'thisoneisignored')]),
                [   'simple_filefinder/a.c',
                    'simple_filefinder/c.c',
                    'simple_filefinder/partialignored/found.c'])

    def test_file_patterns(self):
        # search ignoring known extensions on purpose, to get a small amount of
        # results
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    ignore_extensions=['.c', '.cpp', '.F90', '.scala', '.bonkers'],
                    filter_exclude_patterns=['~$']),
                ['simple_filefinder/#z.c#'])

        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    ignore_extensions=['.c', '.cpp', '.F90', '.scala', '.bonkers'],
                    filter_exclude_patterns=['~$', '#.+#$']),
                [])

        # use search_patterns
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    filter_exclude_patterns=['~$', '#.+#$'],
                    search_patterns=[r't[^./\\]*\.cp']),
                [   'simple_filefinder/.bzr/ttc.cpp',
                    'simple_filefinder/anothersubdir/deep/t.cpp',
                    'simple_filefinder/anothersubdir/deep/tt.cpp'])

        # mix search patterns with extensions
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    ignore_dirs=['CVS'],
                    search_patterns=[r'\.bonkers$'],
                    search_extensions=['.scala']),
                ['simple_filefinder/truesubdir/btesxt.bonkers',
                 'simple_filefinder/truesubdir/sbin.scala',
                 'simple_filefinder/truesubdir/stext.scala'])

        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    ignore_dirs=['CVS'],
                    search_patterns=[r'\.bonkers$', r'r\.cp'],
                    search_extensions=['.scala']),
                ['simple_filefinder/truesubdir/btesxt.bonkers',
                 'simple_filefinder/truesubdir/r.cpp',
                 'simple_filefinder/truesubdir/sbin.scala',
                 'simple_filefinder/truesubdir/stext.scala'])

        # now also add include filtering
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    ignore_dirs=['CVS'],
                    filter_include_patterns=[r'a$'],
                    search_patterns=[r'\.bonkers$', r'r\.cp'],
                    search_extensions=['.scala']),
                ['simple_filefinder/truesubdir/sbin.scala',
                 'simple_filefinder/truesubdir/stext.scala'])

        # use search_patterns and filter_exclude_patterns together
        # exclude file names with at least 3 alphanumeric chars before
        # the dot
        self.assertPathsEqual(
                self._find_files(
                    [self.testdir_simple],
                    filter_exclude_patterns=['~$', '#.+#$', '\w{3}\.'],
                    search_patterns=[r't[^./\\]*\.c']),
                [   'simple_filefinder/anothersubdir/deep/t.cpp',
                    'simple_filefinder/anothersubdir/deep/tt.cpp'])


#------------------------------------------------------------------------------
if __name__ == '__main__':
    #print(path_to_testdir('simple_filefinder'))

    #print(path_relative_to_dir('a/b/c/d.c', 'g'))
    unittest.main()



########NEW FILE########
__FILENAME__ = test_pssmain
#-------------------------------------------------------------------------------
# pss: test/test_pssmain.py
#
# Test the main() function of pss
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import unittest

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from psslib.pss import main
from test.utils import (
        path_to_testdir, MockOutputFormatter, filter_out_path)


class TestPssMain(unittest.TestCase):
    testdir1 = path_to_testdir('testdir1')
    testdir2 = path_to_testdir('testdir2')
    test_types = path_to_testdir('test_types')
    of = None

    def setUp(self):
        self.of = MockOutputFormatter('testdir1')

    def test_basic(self):
        self._run_main(['abc', '--cc'])
        self.assertEqual(sorted(self.of.output),
                sorted(self._gen_outputs_in_file(
                    'testdir1/filea.c', [('MATCH', (2, [(4, 7)]))]) +
                self._gen_outputs_in_file(
                    'testdir1/filea.h', [('MATCH', (1, [(8, 11)]))])))

    def test_two_matches(self):
        self._run_main(['abc', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('MATCH', (4, [(18, 21)])),
                        ('MATCH', (14, [(15, 18)]))]))

    def test_whole_words(self):
        # without whole word matching
        of = MockOutputFormatter('testdir1')
        self._run_main(['xaxo', '--ada'], output_formatter=of)
        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/wholewords.adb',
                    [   ('MATCH', (1, [(5, 9)])),
                        ('MATCH', (2, [(4, 8)]))]))

        # now with whole word matching
        of = MockOutputFormatter('testdir1')
        self._run_main(['xaxo', '--ada', '-w'], output_formatter=of)
        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/wholewords.adb',
                    [('MATCH', (1, [(5, 9)]))]))

    def test_no_break(self):
        # same test as above but with --nobreak
        self._run_main(['abc', '--ada', '--nobreak'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('MATCH', (4, [(18, 21)])),
                        ('MATCH', (14, [(15, 18)]))],
                    add_end=False))

    def test_context_separate(self):
        # context set to +/-3, so it's not "merged" between the two matches
        # and stays separate, with a context separator
        self._run_main(['abc', '-C', '3', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('CONTEXT', 1), ('CONTEXT', 2), ('CONTEXT', 3),
                        ('MATCH', (4, [(18, 21)])),
                        ('CONTEXT', 5), ('CONTEXT', 6), ('CONTEXT', 7),
                        ('CONTEXT_SEP', None),
                        ('CONTEXT', 11), ('CONTEXT', 12), ('CONTEXT', 13),
                        ('MATCH', (14, [(15, 18)])),
                        ('CONTEXT', 15), ('CONTEXT', 16), ('CONTEXT', 17),
                        ]))

    def test_context_merged(self):
        # context set to +/-6, so it's merged between matches
        self._run_main(['abc', '-C', '6', '--ada'])
        self.assertEqual(self.of.output,
                self._gen_outputs_in_file(
                    'testdir1/subdir1/someada.adb',
                    [   ('CONTEXT', 1), ('CONTEXT', 2), ('CONTEXT', 3),
                        ('MATCH', (4, [(18, 21)])),
                        ('CONTEXT', 5), ('CONTEXT', 6), ('CONTEXT', 7),
                        ('CONTEXT', 8), ('CONTEXT', 9), ('CONTEXT', 10),
                        ('CONTEXT', 11), ('CONTEXT', 12), ('CONTEXT', 13),
                        ('MATCH', (14, [(15, 18)])),
                        ('CONTEXT', 15), ('CONTEXT', 16), ('CONTEXT', 17),
                        ('CONTEXT', 18), ('CONTEXT', 19), ('CONTEXT', 20),
                        ]))

    def test_ignored_dirs(self):
        rootdir = path_to_testdir('ignored_dirs')

        # no dirs ignored
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(['def', '--xml'], dir=rootdir, output_formatter=of)

        # Comparing as sorted because on different systems the files
        # returned in a different order
        #
        self.assertEqual(sorted(of.output),
                sorted(self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir1/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir2/file.xml', [('MATCH', (1, [(3, 6)]))])))

        # both dir1 and dir2 ignored
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(
            ['def', '--xml', '--ignore-dir=dir1', '--ignore-dir=dir2'],
            dir=rootdir,
            output_formatter=of)

        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]))

        # both dir1 and dir2 ignored in the same --ignore-dir list
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(
            ['def', '--xml', '--ignore-dir=dir1,dir2'],
            dir=rootdir,
            output_formatter=of)

        self.assertEqual(of.output,
                self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]))

        # dir1 ignored (dir2 also appears in remove_ignored_dirs)
        of = MockOutputFormatter('ignored_dirs')
        self._run_main(
            ['def', '--xml', '--ignore-dir=dir1', '--ignore-dir=dir2',
                '--noignore-dir=dir2'],
            dir=rootdir,
            output_formatter=of)

        self.assertEqual(sorted(of.output),
                sorted(self._gen_outputs_in_file(
                    'ignored_dirs/file.xml', [('MATCH', (1, [(3, 6)]))]) +
                self._gen_outputs_in_file(
                    'ignored_dirs/dir2/file.xml', [('MATCH', (1, [(3, 6)]))])))

    def test_only_find_files_f(self):
        self._run_main(['--cc', '-f'])
        self.assertFoundFiles(self.of,
                ['testdir1/filea.c', 'testdir1/filea.h',
                'testdir1/subdir1/filey.c', 'testdir1/subdir1/filez.c'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['--make', '-f'])
        self.assertFoundFiles(self.of,
                ['testdir1/Makefile', 'testdir1/subdir1/Makefile', 'testdir1/zappos.mk'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['--cmake', '-f'])
        self.assertFoundFiles(self.of,
                [   'testdir1/CMakeLists.txt',
                    'testdir1/subdir1/CMakeFuncs.txt',
                    'testdir1/subdir1/joe.cmake',
                    'testdir1/subdir1/joe2.cmake'])

        self.of = MockOutputFormatter('testdir2')
        self._run_main(['--txt', '-f'], dir=self.testdir2)
        self.assertFoundFiles(self.of,
                ['testdir2/sometext.txt', 'testdir2/othertext.txt'])

        self.of = MockOutputFormatter('testdir2')
        self._run_main(['--withoutext', '-f'], dir=self.testdir2)
        self.assertFoundFiles(self.of,
                ['testdir2/somescript'])

        # try some option mix-n-matching

        # just a pattern type
        self.of = MockOutputFormatter('test_types')
        self._run_main(['--scons', '-f'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                ['test_types/a.scons', 'test_types/SConstruct'])

        # pattern type + extension type
        self.of = MockOutputFormatter('test_types')
        self._run_main(['--scons', '--lua', '-f'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                ['test_types/a.scons', 'test_types/SConstruct',
                 'test_types/a.lua'])

        # as before, with include filter
        self.of = MockOutputFormatter('test_types')
        self._run_main(['--scons', '--lua', '-g', 'lua'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                ['test_types/a.lua'])

        # all known types
        self.of = MockOutputFormatter('test_types')
        self._run_main(['-f'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                [   'test_types/a.scons',
                    'test_types/SConstruct',
                    'test_types/a.lua',
                    'test_types/a.js',
                    'test_types/a.java',
                    'test_types/a.bat',
                    'test_types/a.cmd',
                    ])

        # all known types with extension type exclusion
        self.of = MockOutputFormatter('test_types')
        self._run_main(['-f', '--nobatch', '--nojava'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                [   'test_types/a.scons',
                    'test_types/SConstruct',
                    'test_types/a.lua',
                    'test_types/a.js',
                    ])

        # all known types with pattern type exclusion
        self.of = MockOutputFormatter('test_types')
        self._run_main(['-f', '--noscons'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                [   'test_types/a.java',
                    'test_types/a.lua',
                    'test_types/a.bat',
                    'test_types/a.cmd',
                    'test_types/a.js',
                    ])

        # all known types with pattern type exclusion and filter inclusion
        self.of = MockOutputFormatter('test_types')
        self._run_main(['-g', '(lua|java)', '--noscons'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                [   'test_types/a.java',
                    'test_types/a.lua',
                    ])

        # all known types with extension and pattern type exclusion
        self.of = MockOutputFormatter('test_types')
        self._run_main(['-f', '--noscons', '--nojs'], dir=self.test_types)
        self.assertFoundFiles(self.of,
                [   'test_types/a.java',
                    'test_types/a.lua',
                    'test_types/a.bat',
                    'test_types/a.cmd',
                    ])

    def test_only_find_files_g(self):
        self._run_main(['--cc', '-g', r'.*y\.'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/filey.c'])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['-g', r'\.qqq'])
        self.assertFoundFiles(self.of, [])

        self.of = MockOutputFormatter('testdir1')
        self._run_main(['-a', '-g', r'\.qqq'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/ppp.qqq'])

    def test_only_find_files_l(self):
        self._run_main(['--cc', 'abc', '-l'])
        self.assertFoundFiles(self.of,
                ['testdir1/filea.c', 'testdir1/filea.h'])

    def test_only_find_files_L(self):
        self._run_main(['--cc', 'abc', '-L'])
        self.assertFoundFiles(self.of,
                ['testdir1/subdir1/filey.c', 'testdir1/subdir1/filez.c'])

    def test_binary_matches(self):
        self._run_main(['-G', 'zb', 'cde'])

        binary_match = self.of.output[-1]
        self.assertEqual(binary_match[0], 'BINARY_MATCH')
        self.assertTrue(binary_match[1].find('zb.erl') > 0)

    def test_weird_chars(self):
        # .rb files have some weird characters in them - this is a sanity
        # test that shows that pss won't crash while decoding these files
        #
        self._run_main(['ttt', '--ruby'])

    def test_include_types(self):
        rootdir = path_to_testdir('test_types')
        def outputs(filename):
            return self._gen_outputs_in_file(
                        filename,
                        [('MATCH', (1, [(0, 3)]))])

        # include only js and java
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc', '--js', '--java'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.java') +
                outputs('test_types/a.js')))

        # include js and scons
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc', '--js', '--scons'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.js') +
                outputs('test_types/a.scons')))

        # empty include_types - so include all known types
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.java') +
                outputs('test_types/a.scons') +
                outputs('test_types/a.js') +
                outputs('test_types/a.lua') +
                outputs('test_types/a.cmd') +
                outputs('test_types/a.bat')))

        # empty include_types, but some are excluded
        of = MockOutputFormatter('test_types')
        self._run_main(
            ['abc', '--nojs', '--nojava', '--nobatch', '--noscons'],
            output_formatter=of,
            dir=rootdir)

        self.assertEqual(sorted(of.output), sorted(
                outputs('test_types/a.lua')))

    def test_basic_match_option(self):
        self._run_main(['--cc', '--match=abc'])
        self.assertEqual(sorted(self.of.output),
                sorted(self._gen_outputs_in_file(
                    'testdir1/filea.c', [('MATCH', (2, [(4, 7)]))]) +
                self._gen_outputs_in_file(
                    'testdir1/filea.h', [('MATCH', (1, [(8, 11)]))])))

    def _run_main(self, args, dir=None, output_formatter=None):
        main(
            argv=[''] + args + [dir or self.testdir1],
            output_formatter=output_formatter or self.of)

    def _gen_outputs_in_file(self, filename, outputs, add_end=True):
        """ Helper method for constructing a list of output pairs in the format
            of MockOutputFormatter, delimited from both ends with START_MATCHES
            and END_MATCHES for the given filename.
        """
        seq = []
        seq.append(('START_MATCHES', os.path.normpath(filename)))
        seq.extend(outputs)
        if add_end:
            seq.append(('END_MATCHES', os.path.normpath(filename)))
        return seq

    def _build_found_list(self, filenames):
        """ Helper for only_find_files methods
        """
        return sorted(
            ('FOUND_FILENAME', os.path.normpath(f)) for f in filenames)

    def assertFoundFiles(self, output_formatter, expected_list):
        self.assertEqual(sorted(e for e in output_formatter.output
                                  if not filter_out_path(e[1])),
            self._build_found_list(expected_list))


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = utils
#-------------------------------------------------------------------------------
# pss: test/utils.py
#
# Utilities for unit-testing of pss
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import platform

from psslib.outputformatter import OutputFormatter


def path_to_testdir(testdir_name):
    """ Given a name of a test directory, find its full path.
    """
    testdir_root = os.path.split(__file__)[0]
    return os.path.join(testdir_root, 'testdirs', testdir_name)


def path_relative_to_dir(path, dir):
    """ Given a path and some dir (that should be part of the path), return
        only the part of the path relative to the dir. For example:

        path_relative_to_dir('a/b/c/file.c', 'c') ==> 'c/file.c'

        Assume dir actually is part of path. Otherwise, raise RuntimeError
    """
    partial_path_elems = []
    while True:
        head, tail = os.path.split(path)
        partial_path_elems.append(tail)
        if tail == dir:
            break
        elif not head:
            print(path)
            print(dir)
            raise RuntimeError('no dir in path')
        path = head
    return os.path.join(*reversed(partial_path_elems))


def filter_out_path(path):
    """ Some paths have to be filtered out to successully compare to pss's
        output.
    """
    if 'file_bad_symlink' in path and platform.system() == 'Windows':
        return True
    return False


class MockOutputFormatter(OutputFormatter):
    """ A mock output formatter to be used in tests. Stores all output emitted
        to it in a list of pairs (output_type, data)
    """
    def __init__(self, basepath):
        self.basepath = basepath
        self.output = []

    def start_matches_in_file(self, filename):
        relpath = path_relative_to_dir(filename, self.basepath)
        self.output.append(
            ('START_MATCHES', os.path.normpath(relpath)))

    def end_matches_in_file(self, filename):
        relpath = path_relative_to_dir(filename, self.basepath)
        self.output.append(
            ('END_MATCHES', os.path.normpath(relpath)))

    def matching_line(self, matchresult, filename):
        self.output.append(('MATCH',
            (matchresult.matching_lineno, matchresult.matching_column_ranges)))

    def context_line(self, line, lineno, filename):
        self.output.append(('CONTEXT', lineno))

    def context_separator(self):
        self.output.append(('CONTEXT_SEP', None))

    def binary_file_matches(self, msg):
        self.output.append(('BINARY_MATCH', msg))

    def found_filename(self, filename):
        relpath = path_relative_to_dir(filename, self.basepath)
        self.output.append((
            'FOUND_FILENAME', os.path.normpath(relpath)))


########NEW FILE########
__FILENAME__ = z
#!/usr/bin/env python

import sys

from psslib.defaultpssoutputformatter import DefaultPssOutputFormatter
from psslib.matchresult import MatchResult
from psslib.contentmatcher import ContentMatcher
from psslib.driver import pss_run
from psslib.utils import istextfile

with open('psslib/__pycache__/outputformatter.cpython-33.pyc', 'rb') as f:
    print istextfile(f)
    f.seek(0)

    cm = ContentMatcher('imp')
    matches = cm.match_file(f)
    print(list(matches))


########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# Used for direct invocation of this directory by python, without actually
# having to install pss

from psslib.pss import main; main()


########NEW FILE########
